# Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-6 External-spend authorization and reconciliation
# Constitutional basis: C-059, C-063, C-088, C-089
"""Spend chain: authorize before spend, reserve before dispatch, charge on verified proof, reconcile (WC170-R009).

Sandbox and test mode only: a request for real provider money is refused. The chain is built on the one wallet ledger
(WC-136); it adds no second ledger. The caller owns the transaction, exactly as the ledger does, so a reservation and
the ceiling it counts against commit or roll back together.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

from spend_chain.evidence import EvidenceOwner
from wallet.entity_models import ReservationIdentity, WalletAccount, WalletError, as_utc
from wallet.ledger import WalletLedger

FUNDING_ACCOUNTS = ("PLATFORM", "CUSTOMER")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE = re.compile(r"^[A-Za-z0-9_.:\-]{1,200}$")
_TS = DateTime(timezone=True)
_SECRET = re.compile(r"(?i)(bearer\s|access[_-]?token|secret|password|api[_-]?key|EAA[A-Za-z0-9]{20,})")


class SpendError(ValueError):
    """A typed refusal; ``str(error)`` is the stable code."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SpendAuthorization:
    authorization_id: UUID
    tenant_id: UUID
    relationship_id: UUID
    artifact_id: UUID
    artifact_digest: str
    ceiling_paise: int
    currency: str
    funding_account: str
    window_start: datetime
    window_end: datetime
    status: str
    reserved_paise: int = 0
    replayed: bool = False


@dataclass(frozen=True)
class SpendItem:
    authorization_id: UUID
    work_item_id: UUID
    reservation_id: UUID
    reserved_paise: int
    state: str
    charged_paise: int | None = None
    provider_reference: str | None = None
    replayed: bool = False


@dataclass(frozen=True)
class ReconciliationResult:
    result_id: UUID
    tenant_id: UUID
    relationship_id: UUID
    status: str
    charged_paise: int
    observed_paise: int
    difference_paise: int
    unresolved_items: int


def _stmt(sql: str, *datetime_params: str) -> TextClause:
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


class SpendChain:
    def __init__(
        self,
        session: AsyncSession,
        ledger: WalletLedger,
        *,
        tolerance_paise: int = 0,
        now: Callable[[], datetime] | None = None,
        evidence: EvidenceOwner | None = None,
    ) -> None:
        if tolerance_paise < 0:
            raise SpendError("SPEND_AMOUNT_INVALID")
        self._evidence = evidence
        self._session = session
        self._ledger = ledger
        self._tolerance = tolerance_paise
        self._now = now or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------- authorization (F1)

    async def authorize(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        artifact_id: UUID,
        artifact_digest: str,
        approval_evidence_id: UUID,
        scope_evidence_id: UUID,
        ceiling_paise: int,
        funding_account: str,
        window_start: datetime,
        window_end: datetime,
        idempotency_key: UUID,
        *,
        provider_mode: str = "SANDBOX",
    ) -> SpendAuthorization:
        """Created only for one exact approved and scope-confirmed artifact version. No authorization, no dispatch."""
        if provider_mode != "SANDBOX":
            raise SpendError("SPEND_REAL_MONEY_OUT_OF_SCOPE")
        nil = UUID(int=0)
        if (
            not _DIGEST.match(artifact_digest)
            or nil in (artifact_id, approval_evidence_id, scope_evidence_id)
            or approval_evidence_id == scope_evidence_id
        ):
            raise SpendError("SPEND_ARTIFACT_BINDING_REQUIRED")
        if ceiling_paise <= 0 or funding_account not in FUNDING_ACCOUNTS or as_utc(window_end) <= as_utc(window_start):
            raise SpendError("SPEND_AUTHORIZATION_INVALID")
        if await self.blocked(tenant_id, relationship_id):
            raise SpendError("SPEND_BLOCKED_DISCREPANCY")
        existing = await self._authorization_by_key(tenant_id, idempotency_key)
        request = (relationship_id, artifact_id, artifact_digest, ceiling_paise, funding_account)
        if existing is not None:
            same = request == (
                existing.relationship_id,
                existing.artifact_id,
                existing.artifact_digest,
                existing.ceiling_paise,
                existing.funding_account,
            )
            if not same:
                raise SpendError("SPEND_IDEMPOTENCY_CONFLICT")
            return SpendAuthorization(**{**existing.__dict__, "replayed": True})
        # The caller is signed, but the evidence it names is verified at its owner (WC-170 B5).
        if self._evidence is None:
            raise SpendError("SPEND_EVIDENCE_OWNER_UNAVAILABLE")
        if not await self._evidence.confirm_authorization(
            tenant_id, relationship_id, artifact_id, artifact_digest, approval_evidence_id, scope_evidence_id
        ):
            raise SpendError("SPEND_EVIDENCE_NOT_CONFIRMED")
        authorization_id = uuid5(NAMESPACE_URL, f"spend-authorization:{tenant_id}:{idempotency_key}")
        now = self._now()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.spend_authorizations
                (authorization_id, tenant_id, relationship_id, artifact_id, artifact_digest, approval_evidence_id,
                 scope_evidence_id, ceiling_paise, reserved_paise, currency, funding_account, window_start,
                 window_end, provider_mode, status, idempotency_key, created_at)
                VALUES (:id, :tenant, :relationship, :artifact, :digest, :approval, :scope, :ceiling, 0, 'INR',
                        :funding, :window_start, :window_end, 'SANDBOX', 'ACTIVE', :key, :now)
                """,
                "window_start",
                "window_end",
                "now",
            ),
            {
                "id": str(authorization_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "artifact": str(artifact_id),
                "digest": artifact_digest,
                "approval": str(approval_evidence_id),
                "scope": str(scope_evidence_id),
                "ceiling": ceiling_paise,
                "funding": funding_account,
                "window_start": as_utc(window_start),
                "window_end": as_utc(window_end),
                "key": str(idempotency_key),
                "now": now,
            },
        )
        return SpendAuthorization(
            authorization_id,
            tenant_id,
            relationship_id,
            artifact_id,
            artifact_digest,
            ceiling_paise,
            "INR",
            funding_account,
            as_utc(window_start),
            as_utc(window_end),
            "ACTIVE",
        )

    # ------------------------------------------------------------- reserve (F2, F4)

    async def reserve(
        self,
        tenant_id: UUID,
        authorization_id: UUID,
        work_item_id: UUID,
        paise: int,
        funding_wallet: WalletAccount | None,
        component_id: str,
    ) -> SpendItem:
        """Reserve before dispatch. The ceiling check and the hold are one atomic operation; a replay returns the same hold."""
        if paise <= 0:
            raise SpendError("SPEND_AMOUNT_INVALID")
        authorization = await self._authorization(tenant_id, authorization_id)
        item = await self._item(tenant_id, authorization_id, work_item_id)
        if item is not None:
            if item.reserved_paise != paise:
                raise SpendError("SPEND_IDEMPOTENCY_CONFLICT")
            return SpendItem(**{**item.__dict__, "replayed": True})
        now = self._now()
        if authorization.status != "ACTIVE" or not (authorization.window_start <= now < authorization.window_end):
            raise SpendError("SPEND_AUTHORIZATION_NOT_ACTIVE")
        if await self.blocked(tenant_id, authorization.relationship_id):
            raise SpendError("SPEND_BLOCKED_DISCREPANCY")
        if funding_wallet is None:
            raise SpendError("SPEND_UNFUNDED", "no funding account for this work item")
        if funding_wallet.tenant_id != tenant_id or funding_wallet.owner_kind != authorization.funding_account:
            raise SpendError("SPEND_FUNDING_MISMATCH")
        claimed = await self._session.execute(
            text(
                """
                UPDATE business.spend_authorizations
                SET reserved_paise = reserved_paise + :paise
                WHERE tenant_id = :tenant AND authorization_id = :id AND reserved_paise + :paise <= ceiling_paise
                """
            ),
            {"paise": paise, "tenant": str(tenant_id), "id": str(authorization_id)},
        )
        if claimed.rowcount != 1:
            raise SpendError("SPEND_CEILING_EXCEEDED")
        # The ceiling row is now locked by this transaction: a concurrent request for the same work item that won the
        # race has committed its hold, so replay it instead of holding twice.
        raced = await self._item(tenant_id, authorization_id, work_item_id)
        if raced is not None:
            await self._release_ceiling(tenant_id, authorization_id, paise)
            if raced.reserved_paise != paise:
                raise SpendError("SPEND_IDEMPOTENCY_CONFLICT")
            return SpendItem(**{**raced.__dict__, "replayed": True})
        reservation_id = uuid5(NAMESPACE_URL, f"spend-reservation:{authorization_id}:{work_item_id}")
        try:
            await self._ledger.reserve(
                funding_wallet,
                component_id,
                paise,
                authorization.window_end,
                ReservationIdentity(
                    pinned_versions={"artifactDigest": authorization.artifact_digest},
                    evidence_id=authorization.artifact_id,
                ),
                reservation_id,
            )
        except WalletError as error:
            await self._release_ceiling(tenant_id, authorization_id, paise)
            raise SpendError("SPEND_FUNDING_REFUSED", error.code) from error
        await self._session.execute(
            text(
                """
                INSERT INTO business.spend_items
                (authorization_id, work_item_id, tenant_id, relationship_id, reservation_id, reserved_paise, state, created_at)
                VALUES (:auth, :item, :tenant, :relationship, :reservation, :paise, 'RESERVED', :now)
                """
            ).bindparams(bindparam("now", type_=_TS)),
            {
                "auth": str(authorization_id),
                "item": str(work_item_id),
                "tenant": str(tenant_id),
                "relationship": str(authorization.relationship_id),
                "reservation": str(reservation_id),
                "paise": paise,
                "now": now,
            },
        )
        return SpendItem(authorization_id, work_item_id, reservation_id, paise, "RESERVED")

    async def mark_uncertain(self, tenant_id: UUID, authorization_id: UUID, work_item_id: UUID) -> SpendItem:
        """The dispatch outcome is unknown: the hold stays and reconciliation settles it. It is never released blindly."""
        item = await self._require_item(tenant_id, authorization_id, work_item_id)
        if item.state == "RESERVED":
            await self._set_state(authorization_id, work_item_id, "UNCERTAIN")
        return await self._require_item(tenant_id, authorization_id, work_item_id)

    # ------------------------------------------------------------- charge on proof (F2)

    async def charge(
        self,
        tenant_id: UUID,
        authorization_id: UUID,
        work_item_id: UUID,
        observed_paise: int,
        provider_reference: str,
        verified: bool,
        evidence_id: UUID,
    ) -> SpendItem:
        """A charge is written only after verified provider evidence. The provider's figure is stored as an observation."""
        if not verified or not provider_reference:
            raise SpendError("SPEND_PROOF_REQUIRED")
        if (
            observed_paise <= 0
            or not _REFERENCE.match(provider_reference)
            or _SECRET.search(provider_reference)
            or evidence_id == UUID(int=0)
        ):
            raise SpendError("SPEND_AMOUNT_INVALID")
        item = await self._require_item(tenant_id, authorization_id, work_item_id)
        if item.state == "CHARGED":
            if item.charged_paise != observed_paise or item.provider_reference != provider_reference:
                raise SpendError("SPEND_IDEMPOTENCY_CONFLICT")
            return SpendItem(**{**item.__dict__, "replayed": True})
        if item.state not in ("RESERVED", "UNCERTAIN"):
            raise SpendError("SPEND_ITEM_NOT_CHARGEABLE")
        if self._evidence is None:
            raise SpendError("SPEND_EVIDENCE_OWNER_UNAVAILABLE")
        authorization = await self._authorization(tenant_id, authorization_id)
        if not await self._evidence.confirm_provider_proof(
            tenant_id, authorization.relationship_id, work_item_id, provider_reference, evidence_id
        ):
            raise SpendError("SPEND_EVIDENCE_NOT_CONFIRMED")
        await self._record_observation(tenant_id, authorization_id, work_item_id, observed_paise, provider_reference)
        await self._ledger.settle(tenant_id, item.reservation_id, observed_paise, evidence_id)
        await self._session.execute(
            text(
                """
                UPDATE business.spend_items
                SET state = 'CHARGED', charged_paise = :paise, provider_reference = :reference
                WHERE authorization_id = :auth AND work_item_id = :item
                """
            ),
            {
                "paise": observed_paise,
                "reference": provider_reference,
                "auth": str(authorization_id),
                "item": str(work_item_id),
            },
        )
        return await self._require_item(tenant_id, authorization_id, work_item_id)

    async def observe(
        self,
        tenant_id: UUID,
        authorization_id: UUID,
        work_item_id: UUID,
        observed_paise: int,
        provider_reference: str,
    ) -> None:
        """Record what the provider reports without charging. Reconciliation compares it with what was charged."""
        if observed_paise < 0 or not _REFERENCE.match(provider_reference) or _SECRET.search(provider_reference):
            raise SpendError("SPEND_AMOUNT_INVALID")
        await self._require_item(tenant_id, authorization_id, work_item_id)
        await self._record_observation(tenant_id, authorization_id, work_item_id, observed_paise, provider_reference)

    # ------------------------------------------------------------- reconciliation (F3)

    async def reconcile(self, tenant_id: UUID, relationship_id: UUID) -> ReconciliationResult:
        """MATCHED, WITHIN_TOLERANCE or DISCREPANCY. A discrepancy blocks new spend for the relationship until resolved."""
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                    SELECT i.authorization_id, i.work_item_id, i.state, COALESCE(i.charged_paise, 0) AS charged,
                           (SELECT COALESCE(SUM(o.observed_paise), 0) FROM business.spend_observations o
                            WHERE o.authorization_id = i.authorization_id AND o.work_item_id = i.work_item_id) AS observed
                    FROM business.spend_items i
                    WHERE i.tenant_id = :tenant AND i.relationship_id = :relationship
                    """
                    ),
                    {"tenant": str(tenant_id), "relationship": str(relationship_id)},
                )
            )
            .mappings()
            .all()
        )
        charged = sum(int(row["charged"]) for row in rows)
        observed = sum(int(row["observed"]) for row in rows)
        unresolved = sum(1 for row in rows if row["state"] == "UNCERTAIN" and int(row["observed"]) == 0)
        difference = observed - charged
        # Opposite differences on two items must not cancel: each charged item is compared with its own observations.
        worst = max((abs(int(row["observed"]) - int(row["charged"])) for row in rows if row["state"] == "CHARGED"), default=0)
        if unresolved or abs(difference) > self._tolerance or worst > self._tolerance:
            status = "DISCREPANCY"
        elif difference == 0 and worst == 0:
            status = "MATCHED"
        else:
            status = "WITHIN_TOLERANCE"
        result_id = uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO business.spend_reconciliation_results
                (result_id, tenant_id, relationship_id, status, charged_paise, observed_paise, difference_paise,
                 unresolved_items, created_at)
                VALUES (:id, :tenant, :relationship, :status, :charged, :observed, :difference, :unresolved, :now)
                """
            ).bindparams(bindparam("now", type_=_TS)),
            {
                "id": str(result_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "status": status,
                "charged": charged,
                "observed": observed,
                "difference": difference,
                "unresolved": unresolved,
                "now": self._now(),
            },
        )
        return ReconciliationResult(result_id, tenant_id, relationship_id, status, charged, observed, difference, unresolved)

    async def blocked(self, tenant_id: UUID, relationship_id: UUID) -> bool:
        """True while ANY reconciliation for the relationship is an unresolved DISCREPANCY.

        A later matched result never clears an earlier break: only the Founder's resolution with evidence does.
        """
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT 1 FROM business.spend_reconciliation_results
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND status = 'DISCREPANCY' AND resolved_at IS NULL
                    LIMIT 1
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).first()
        return row is not None

    async def resolve_discrepancy(self, tenant_id: UUID, result_id: UUID, evidence_id: UUID) -> None:
        """The Founder resolves it with evidence; only then may new spend start again."""
        if evidence_id == UUID(int=0):
            raise SpendError("SPEND_EVIDENCE_REQUIRED")
        updated = await self._session.execute(
            text(
                """
                UPDATE business.spend_reconciliation_results
                SET resolved_at = :now, resolution_evidence_id = :evidence
                WHERE tenant_id = :tenant AND result_id = :id AND status = 'DISCREPANCY' AND resolved_at IS NULL
                """
            ).bindparams(bindparam("now", type_=_TS)),
            {"now": self._now(), "evidence": str(evidence_id), "tenant": str(tenant_id), "id": str(result_id)},
        )
        if updated.rowcount != 1:
            raise SpendError("SPEND_RESULT_NOT_RESOLVABLE")

    # ------------------------------------------------------------- reads and helpers

    async def _record_observation(
        self, tenant_id: UUID, authorization_id: UUID, work_item_id: UUID, paise: int, reference: str
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO business.spend_observations
                (observation_id, tenant_id, authorization_id, work_item_id, observed_paise, provider_reference, observed_at)
                VALUES (:id, :tenant, :auth, :item, :paise, :reference, :now)
                ON CONFLICT (authorization_id, work_item_id, provider_reference) DO NOTHING
                """
            ).bindparams(bindparam("now", type_=_TS)),
            {
                "id": str(uuid5(NAMESPACE_URL, f"spend-observation:{authorization_id}:{work_item_id}:{reference}")),
                "tenant": str(tenant_id),
                "auth": str(authorization_id),
                "item": str(work_item_id),
                "paise": paise,
                "reference": reference,
                "now": self._now(),
            },
        )

    async def _release_ceiling(self, tenant_id: UUID, authorization_id: UUID, paise: int) -> None:
        await self._session.execute(
            text(
                "UPDATE business.spend_authorizations SET reserved_paise = reserved_paise - :paise "
                "WHERE tenant_id = :tenant AND authorization_id = :id"
            ),
            {"paise": paise, "tenant": str(tenant_id), "id": str(authorization_id)},
        )

    async def _set_state(self, authorization_id: UUID, work_item_id: UUID, state: str) -> None:
        await self._session.execute(
            text("UPDATE business.spend_items SET state = :state WHERE authorization_id = :auth AND work_item_id = :item"),
            {"state": state, "auth": str(authorization_id), "item": str(work_item_id)},
        )

    async def get_authorization(self, tenant_id: UUID, authorization_id: UUID) -> SpendAuthorization:
        return await self._authorization(tenant_id, authorization_id)

    async def _authorization(self, tenant_id: UUID, authorization_id: UUID) -> SpendAuthorization:
        row = (
            (
                await self._session.execute(
                    text("SELECT * FROM business.spend_authorizations WHERE tenant_id = :tenant AND authorization_id = :id"),
                    {"tenant": str(tenant_id), "id": str(authorization_id)},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise SpendError("SPEND_NOT_AUTHORIZED")
        return _authorization(row)

    async def _authorization_by_key(self, tenant_id: UUID, key: UUID) -> SpendAuthorization | None:
        row = (
            (
                await self._session.execute(
                    text("SELECT * FROM business.spend_authorizations WHERE tenant_id = :tenant AND idempotency_key = :key"),
                    {"tenant": str(tenant_id), "key": str(key)},
                )
            )
            .mappings()
            .first()
        )
        return _authorization(row) if row is not None else None

    async def _item(self, tenant_id: UUID, authorization_id: UUID, work_item_id: UUID) -> SpendItem | None:
        row = (
            (
                await self._session.execute(
                    text(
                        "SELECT * FROM business.spend_items "
                        "WHERE tenant_id = :tenant AND authorization_id = :auth AND work_item_id = :item"
                    ),
                    {"tenant": str(tenant_id), "auth": str(authorization_id), "item": str(work_item_id)},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return SpendItem(
            UUID(str(row["authorization_id"])),
            UUID(str(row["work_item_id"])),
            UUID(str(row["reservation_id"])),
            int(row["reserved_paise"]),
            row["state"],
            int(row["charged_paise"]) if row["charged_paise"] is not None else None,
            row["provider_reference"],
        )

    async def _require_item(self, tenant_id: UUID, authorization_id: UUID, work_item_id: UUID) -> SpendItem:
        item = await self._item(tenant_id, authorization_id, work_item_id)
        if item is None:
            raise SpendError("SPEND_NOT_AUTHORIZED")
        return item


def _authorization(row: Any) -> SpendAuthorization:
    return SpendAuthorization(
        UUID(str(row["authorization_id"])),
        UUID(str(row["tenant_id"])),
        UUID(str(row["relationship_id"])),
        UUID(str(row["artifact_id"])),
        row["artifact_digest"],
        int(row["ceiling_paise"]),
        row["currency"],
        row["funding_account"],
        as_utc(row["window_start"]),
        as_utc(row["window_end"]),
        row["status"],
        int(row["reserved_paise"]),
    )
