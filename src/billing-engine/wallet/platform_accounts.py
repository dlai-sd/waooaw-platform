# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Constitutional basis: C-059, C-088, C-089, C-063
"""Platform-owned wallet accounts: ACQUISITION, SETUP_GRANT, TRIAL grants, SIMULATION, PLATFORM_FLOOR.

Every account here is owned by the platform (owner_kind PLATFORM, owner_ref null). Caps and grants
come from the EFFECTIVE versions in institutional.pricing_versions (BUDGET and GRANT kinds).

* ACQUISITION draws on a hierarchical cap: marketplace tenant, then campaign, then lead. The tenant
  cap is mandatory (no EFFECTIVE budget means a zero ceiling); campaign and lead caps apply when a
  version exists for that reference. The environment breaker above these levels is owned by BP.
* SIMULATION has its own cap and never touches ACQUISITION.
* SETUP_GRANT is credited once per relationship; exhaustion is a typed result, not an error.
* PLATFORM_FLOOR is never gated; every use is recorded and counted.

Lots of ACQUISITION and SIMULATION accounts are credited on demand with exactly the amount reserved:
the budget version, not a lot balance, is the spending limit. The caller owns the transaction.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, NoReturn
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from wallet import metrics
from wallet.entity_models import (
    ReservationIdentity,
    WalletAccount,
    WalletCreditReceipt,
    WalletError,
    WalletReservationReceipt,
    as_json_object,
    as_utc,
)
from wallet.ledger import WalletLedger
from wallet.log_safe import log_value

logger = logging.getLogger(__name__)

DEFAULT_CAMPAIGN = "DEFAULT"
GRANT_PAISE_PER_UNIT = 100
DEFAULT_SETUP_GRANT_DAYS = 30
SIMULATOR_ROLE = "visitor-simulator"
SIMULATION_CHANNEL = "SIMULATION"
SETUP_GRANT_EXHAUSTED = "SETUP_GRANT_EXHAUSTED"
ACQUISITION_BUDGET_EXHAUSTED = "ACQUISITION_BUDGET_EXHAUSTED"
SIMULATION_BUDGET_EXHAUSTED = "SIMULATION_BUDGET_EXHAUSTED"

_BUDGET_SCOPE_BY_LEVEL = {
    "TENANT": "ACQUISITION_TENANT",
    "CAMPAIGN": "ACQUISITION_CAMPAIGN",
    "LEAD": "ACQUISITION_LEAD",
    "SIMULATION": "SIMULATION",
}
_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$")
_PHONE_LIKE = re.compile(r"^\+?[0-9]{8,15}$")
_TS = DateTime(timezone=True)

_EFFECTIVE_VERSION = """
    SELECT version_id, body, effective_from
    FROM institutional.pricing_versions
    WHERE kind = :kind AND subject_key = :subject AND state = 'EFFECTIVE'
    ORDER BY version_no DESC
    LIMIT 1
"""
_EXPOSURE = """
    SELECT COALESCE(SUM(CASE WHEN r.state = 'SETTLED' THEN r.actual_paise
                             ELSE r.reserved_paise END), 0) AS exposure
    FROM business.wallet_reservations r
    JOIN business.wallet_accounts a
      ON a.tenant_id = r.tenant_id AND a.account_id = r.account_id
    WHERE r.tenant_id = :tenant AND a.account_class = :account_class
      AND r.state IN ('RESERVED', 'UNKNOWN', 'SETTLED')
      AND r.created_at >= :since
"""
_EXPOSURE_FILTER = {
    "TENANT": "",
    "CAMPAIGN": " AND a.campaign_ref = :reference",
    "LEAD": " AND a.lead_ref = :reference",
    "SIMULATION": " AND a.environment = :reference",
}


@dataclass(frozen=True)
class PlatformGrant:
    """An EFFECTIVE grant version converted to paise (a thread unit is 100 paise of nominal credit)."""

    version_id: UUID
    grant_kind: str
    agent_type: str
    agent_version: str
    paise: int
    duration_days: int | None
    disabled: bool


@dataclass(frozen=True)
class BudgetCap:
    version_id: UUID
    level: str
    reference: str
    maximum_paise: int
    effective_from: datetime | None


@dataclass(frozen=True)
class SetupGrantAccount:
    account: WalletAccount
    lot_id: UUID | None
    credited_paise: int
    created: bool


@dataclass(frozen=True)
class SetupGrantReservation:
    """status is RESERVED, or SETUP_GRANT_EXHAUSTED when the grant cannot cover the call."""

    status: str
    account: WalletAccount
    receipt: WalletReservationReceipt | None


@dataclass(frozen=True)
class FloorUseReceipt:
    use_id: UUID
    account_id: UUID
    recorded: bool


def is_simulated_traffic(*, roles: Iterable[str], channel: str | None) -> bool:
    """Simulation is identified only by server-verified facts, never by a client-supplied field."""
    return SIMULATOR_ROLE in set(roles) or channel == SIMULATION_CHANNEL


def _reference(value: str, name: str) -> str:
    if not _REFERENCE_PATTERN.fullmatch(value) or _PHONE_LIKE.fullmatch(value):
        raise WalletError("WALLET_ACCOUNT_INVALID", name)
    return value


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


def grant_from_body(
    version_id: object, body: Mapping[str, Any], grant_kind: str, agent_type: str, agent_version: str
) -> PlatformGrant:
    amount = body.get("amountPaise", body.get("paise"))
    if amount is None:
        units = body.get("threadUnits", body.get("units")) or {}
        amount = sum(int(value) for value in units.values()) * GRANT_PAISE_PER_UNIT
    duration = body.get("durationDays", body.get("windowDays"))
    return PlatformGrant(
        version_id=UUID(str(version_id)),
        grant_kind=grant_kind,
        agent_type=agent_type,
        agent_version=agent_version,
        paise=int(amount),
        duration_days=int(duration) if duration is not None else None,
        disabled=bool(body.get("disabled", False)),
    )


async def effective_grant(
    session: AsyncSession, grant_kind: str, agent_type: str, agent_version: str
) -> PlatformGrant | None:
    """The EFFECTIVE GRANT version for this exact agent version, or None when none exists."""
    row = (
        await session.execute(
            text(_EFFECTIVE_VERSION),
            {
                "kind": "GRANT",
                "subject": f"grant:{grant_kind}|{agent_type}|{agent_version}",
            },
        )
    ).mappings().one_or_none()
    if row is None:
        return None
    return grant_from_body(
        row["version_id"], as_json_object(row["body"]), grant_kind, agent_type, agent_version
    )


async def effective_budget(session: AsyncSession, level: str, reference: str) -> BudgetCap | None:
    scope = _BUDGET_SCOPE_BY_LEVEL[level]
    row = (
        await session.execute(
            text(_EFFECTIVE_VERSION),
            {"kind": "BUDGET", "subject": f"budget:{scope}|{reference}"},
        )
    ).mappings().one_or_none()
    if row is None:
        return None
    body = as_json_object(row["body"])
    return BudgetCap(
        version_id=UUID(str(row["version_id"])),
        level=level,
        reference=reference,
        maximum_paise=int(body["maximumPaise"]),
        effective_from=as_utc(row["effective_from"]) if row["effective_from"] is not None else None,
    )


class PlatformAccounts:
    def __init__(
        self,
        session: AsyncSession,
        *,
        ledger: WalletLedger | None = None,
        now: Callable[[], datetime] | None = None,
        overrun_tolerance_paise: int = 0,
    ) -> None:
        self._session = session
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._ledger = ledger or WalletLedger(
            session, overrun_tolerance_paise=overrun_tolerance_paise, now=self._now
        )

    @property
    def ledger(self) -> WalletLedger:
        return self._ledger

    # ------------------------------------------------------------------ account keys

    async def open_acquisition_account(
        self, tenant_id: UUID, campaign_ref: str | None = None, lead_ref: str | None = None
    ) -> WalletAccount:
        return await self._ledger.open_account(
            tenant_id,
            "ACQUISITION",
            campaign_ref=_reference(campaign_ref or DEFAULT_CAMPAIGN, "campaign_ref"),
            lead_ref=_reference(lead_ref, "lead_ref") if lead_ref else None,
        )

    async def open_simulation_account(self, tenant_id: UUID, environment: str) -> WalletAccount:
        return await self._ledger.open_account(
            tenant_id, "SIMULATION", environment=_reference(environment, "environment")
        )

    async def open_floor_account(self, tenant_id: UUID, environment: str) -> WalletAccount:
        return await self._ledger.open_account(
            tenant_id, "PLATFORM_FLOOR", environment=_reference(environment, "environment")
        )

    # ------------------------------------------------------------------ ACQUISITION

    async def reserve_acquisition(
        self,
        tenant_id: UUID,
        component_id: str,
        paise: int,
        expires_at: datetime,
        identity: ReservationIdentity,
        idempotency_key: UUID,
        *,
        campaign_ref: str | None = None,
        lead_ref: str | None = None,
    ) -> WalletReservationReceipt:
        """Reserve after checking tenant, campaign and lead caps; refuses naming the exhausted level."""
        campaign = _reference(campaign_ref or DEFAULT_CAMPAIGN, "campaign_ref")
        lead = _reference(lead_ref, "lead_ref") if lead_ref else None
        replay = await self._replay(tenant_id, idempotency_key, "ACQUISITION", component_id, paise)
        if replay is not None:
            return replay
        await self._serialize(f"wallet-cap:{tenant_id}:ACQUISITION")
        levels: list[tuple[str, str, bool]] = [
            ("TENANT", str(tenant_id), True),
            ("CAMPAIGN", campaign, False),
        ]
        if lead is not None:
            levels.append(("LEAD", lead, False))
        for level, reference, mandatory in levels:
            cap = await effective_budget(self._session, level, reference)
            if cap is None:
                if mandatory:
                    self._exhausted(ACQUISITION_BUDGET_EXHAUSTED, level)
                continue
            exposure = await self._exposure(tenant_id, "ACQUISITION", level, reference, cap)
            if exposure + paise > cap.maximum_paise:
                self._exhausted(ACQUISITION_BUDGET_EXHAUSTED, level)
        account = await self.open_acquisition_account(tenant_id, campaign, lead)
        return await self._reserve_on_demand(
            account, "ACQUISITION_BUDGET", component_id, paise, expires_at, identity, idempotency_key
        )

    # ------------------------------------------------------------------ SIMULATION

    async def reserve_simulation(
        self,
        tenant_id: UUID,
        environment: str,
        component_id: str,
        paise: int,
        expires_at: datetime,
        identity: ReservationIdentity,
        idempotency_key: UUID,
    ) -> WalletReservationReceipt:
        """Reserve on the environment's SIMULATION account; its cap is separate from ACQUISITION."""
        environment = _reference(environment, "environment")
        replay = await self._replay(tenant_id, idempotency_key, "SIMULATION", component_id, paise)
        if replay is not None:
            return replay
        await self._serialize(f"wallet-cap:{tenant_id}:SIMULATION:{environment}")
        cap = await effective_budget(self._session, "SIMULATION", environment)
        if cap is None:
            self._exhausted(SIMULATION_BUDGET_EXHAUSTED, "SIMULATION")
        exposure = await self._exposure(tenant_id, "SIMULATION", "SIMULATION", environment, cap)
        if exposure + paise > cap.maximum_paise:
            self._exhausted(SIMULATION_BUDGET_EXHAUSTED, "SIMULATION")
        account = await self.open_simulation_account(tenant_id, environment)
        return await self._reserve_on_demand(
            account, "SIMULATION_BUDGET", component_id, paise, expires_at, identity, idempotency_key
        )

    # ------------------------------------------------------------------ SETUP_GRANT

    async def open_setup_grant(
        self, tenant_id: UUID, relationship_id: UUID, agent_type: str, agent_version: str
    ) -> SetupGrantAccount:
        """Open the relationship's setup-grant account and credit its grant lot once."""
        account = await self._ledger.open_account(
            tenant_id,
            "SETUP_GRANT",
            relationship_id=relationship_id,
            agent_type=agent_type,
            agent_version=agent_version,
        )
        existing = (
            await self._session.execute(
                text(
                    "SELECT lot_id, credited_paise FROM business.wallet_lots "
                    "WHERE tenant_id = :tenant AND account_id = :account "
                    "AND source_kind = 'SETUP_GRANT' ORDER BY created_at, lot_id LIMIT 1"
                ),
                {"tenant": str(tenant_id), "account": str(account.account_id)},
            )
        ).mappings().first()
        if existing is not None:
            return SetupGrantAccount(
                account, UUID(str(existing["lot_id"])), int(existing["credited_paise"]), False
            )
        grant = await effective_grant(
            self._session, "SETUP", account.agent_type or agent_type, account.agent_version or agent_version
        )
        if grant is None or grant.disabled or grant.paise <= 0:
            return SetupGrantAccount(account, None, 0, False)
        now = self._now()
        receipt = await self._ledger.credit(
            account,
            "GRANT",
            grant.paise,
            now,
            now + timedelta(days=grant.duration_days or DEFAULT_SETUP_GRANT_DAYS),
            f"setup-grant:{relationship_id}",
            {"grant": str(grant.version_id)},
            uuid5(NAMESPACE_URL, f"setup-grant:{tenant_id}:{relationship_id}"),
            source_kind="SETUP_GRANT",
        )
        return SetupGrantAccount(account, receipt.lot_id, receipt.credited_paise, True)

    async def reserve_setup_grant(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        agent_type: str,
        agent_version: str,
        component_id: str,
        paise: int,
        expires_at: datetime,
        identity: ReservationIdentity,
        idempotency_key: UUID,
    ) -> SetupGrantReservation:
        """Onboarding draw; exhaustion returns SETUP_GRANT_EXHAUSTED and never falls through silently."""
        opened = await self.open_setup_grant(tenant_id, relationship_id, agent_type, agent_version)
        replay = await self._replay(tenant_id, idempotency_key, "SETUP_GRANT", component_id, paise)
        if replay is not None:
            return SetupGrantReservation("RESERVED", opened.account, replay)
        if opened.lot_id is None:
            metrics.count("wbe.wallet.setup_grant_exhausted", reason="NO_GRANT")
            return SetupGrantReservation(SETUP_GRANT_EXHAUSTED, opened.account, None)
        try:
            receipt = await self._ledger.reserve(
                opened.account, component_id, paise, expires_at, identity, idempotency_key
            )
        except WalletError as error:
            if error.code != "WALLET_INSUFFICIENT":
                raise
            metrics.count("wbe.wallet.setup_grant_exhausted", reason="BALANCE")
            return SetupGrantReservation(SETUP_GRANT_EXHAUSTED, opened.account, None)
        return SetupGrantReservation("RESERVED", opened.account, receipt)

    # ------------------------------------------------------------------ TRIAL

    async def credit_trial_grant(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        agent_type: str,
        agent_version: str,
        trial_id: UUID,
        valid_from: datetime,
        valid_until: datetime,
        *,
        grant: PlatformGrant | None,
        fallback_units: Mapping[str, int] | None = None,
    ) -> WalletCreditReceipt | None:
        """Credit the trial's GRANT lot from the effective grant, else from the settings fallback.

        A disabled grant credits nothing. The lot window is the trial window. Replays are exact.
        """
        if grant is not None:
            paise = 0 if grant.disabled else grant.paise
            pinned: dict[str, object] = {"grant": str(grant.version_id)}
        else:
            paise = sum(int(value) for value in (fallback_units or {}).values()) * GRANT_PAISE_PER_UNIT
            pinned = {"grant": "settings"}
        if paise <= 0:
            return None
        account = await self._ledger.open_account(
            tenant_id,
            "TRIAL",
            relationship_id=relationship_id,
            agent_type=agent_type,
            agent_version=agent_version,
        )
        return await self._ledger.credit(
            account,
            "GRANT",
            paise,
            valid_from,
            valid_until,
            f"trial:{trial_id}",
            pinned,
            uuid5(NAMESPACE_URL, f"trial-grant:{trial_id}"),
            source_kind="TRIAL_GRANT",
        )

    # ------------------------------------------------------------------ PLATFORM_FLOOR

    async def record_floor_use(
        self,
        tenant_id: UUID,
        environment: str,
        purpose: str,
        component_id: str,
        paise: int,
        evidence_id: UUID,
        *,
        invocation_id: UUID | None = None,
        use_id: UUID | None = None,
    ) -> FloorUseReceipt:
        """Record a safety-floor use. It is never gated and succeeds at any balance."""
        if paise < 0 or not purpose or not component_id:
            raise WalletError("WALLET_AMOUNT_INVALID")
        account = await self.open_floor_account(tenant_id, environment)
        recorded_id = use_id or uuid4()
        result = await self._session.execute(
            _stmt(
                """
                INSERT INTO business.wallet_floor_uses
                (tenant_id, environment, use_id, purpose, component_id, amount_paise,
                 invocation_id, evidence_id, occurred_at)
                VALUES (:tenant, :environment, :use, :purpose, :component, :paise,
                        :invocation, :evidence, :now)
                ON CONFLICT (tenant_id, environment, use_id) DO NOTHING
                """,
                "now",
            ),
            {
                "tenant": str(tenant_id),
                "environment": environment,
                "use": str(recorded_id),
                "purpose": purpose,
                "component": component_id,
                "paise": paise,
                "invocation": str(invocation_id) if invocation_id is not None else None,
                "evidence": str(evidence_id),
                "now": self._now(),
            },
        )
        recorded = result.rowcount == 1
        if recorded:
            metrics.count("wbe.wallet.platform_floor_use", environment=environment, purpose=purpose)
            logger.info(
                "platform floor use recorded: environment=%s purpose=%s component=%s paise=%d",
                log_value(environment),
                log_value(purpose),
                log_value(component_id),
                paise,
            )
        return FloorUseReceipt(use_id=recorded_id, account_id=account.account_id, recorded=recorded)

    # ------------------------------------------------------------------ internals

    async def effective_grant(
        self, grant_kind: str, agent_type: str, agent_version: str
    ) -> PlatformGrant | None:
        return await effective_grant(self._session, grant_kind, agent_type, agent_version)

    async def _replay(
        self, tenant_id: UUID, key: UUID, account_class: str, component_id: str, paise: int
    ) -> WalletReservationReceipt | None:
        existing = await self._ledger.get_reservation(tenant_id, key)
        if existing is None:
            return None
        if (
            existing.pinned_account_class != account_class
            or existing.component_id != component_id
            or existing.reserved_paise != paise
        ):
            raise WalletError("WALLET_IDEMPOTENCY_CONFLICT")
        return replace(existing, replayed=True)

    async def _serialize(self, key: str) -> None:
        if self._session.get_bind().dialect.name == "postgresql":
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}
            )

    async def _exposure(
        self, tenant_id: UUID, account_class: str, level: str, reference: str, cap: BudgetCap
    ) -> int:
        parameters: dict[str, Any] = {
            "tenant": str(tenant_id),
            "account_class": account_class,
            "since": cap.effective_from or datetime(1970, 1, 1, tzinfo=timezone.utc),
        }
        if _EXPOSURE_FILTER[level]:
            parameters["reference"] = reference
        value = (
            await self._session.execute(_stmt(_EXPOSURE + _EXPOSURE_FILTER[level], "since"), parameters)
        ).scalar_one()
        return int(value)

    @staticmethod
    def _exhausted(code: str, level: str) -> NoReturn:
        metrics.count("wbe.wallet.budget_exhausted", level=level)
        logger.warning("platform budget exhausted: code=%s level=%s", code, level)
        raise WalletError(code, level)

    async def _reserve_on_demand(
        self,
        account: WalletAccount,
        source_kind: str,
        component_id: str,
        paise: int,
        expires_at: datetime,
        identity: ReservationIdentity,
        idempotency_key: UUID,
    ) -> WalletReservationReceipt:
        now = self._now()
        valid_until = max(as_utc(expires_at), now) + timedelta(days=1)
        await self._ledger.credit(
            account,
            "GRANT",
            paise,
            now,
            valid_until,
            f"{source_kind.lower()}:{idempotency_key}",
            {},
            uuid5(NAMESPACE_URL, f"platform-lot:{idempotency_key}"),
            source_kind=source_kind,
            evidence_id=identity.evidence_id,
        )
        return await self._ledger.reserve(
            account, component_id, paise, expires_at, identity, idempotency_key
        )
