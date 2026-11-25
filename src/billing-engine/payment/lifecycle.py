# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R002, WC172-R003, WC172-R004, WC172-R005
# Constitutional basis: C-059, C-038, C-088, C-089, C-090, C-091, C-063
"""Period credit and lifecycle of a relationship's package (WC-136 C4-10, WC-172 D1 to D5).

Hire and renewal credit a PERIOD_CREDIT lot sized from the package recipes at the pinned thread rates and
open the period's component units. Pause, terminate, upgrade and downgrade follow the effective POLICY
version; with no POLICY version a RENEW or TERMINATE is BLOCKED, never defaulted. The monthly fee is
pro-rated (C-038) and refunded only as a billing adjustment (ADR-026); wallet credit is never refunded and
the unspent credit of a terminated period lapses. An immediate upgrade records its pro-rated fee difference
as an UPGRADE_FEE billing adjustment that the sweep turns into a provider order. A captured renewal payment
credits the next period's lot (``LifecycleService.renew_paid``); components paused in a period come back with
the next period's whole-package renewal. Services work in the caller's session and never commit.

WC-172 (Founder decisions D1 to D5, ``payment.lifecycle_policy``): a pause is a FEE_CREDIT applied to the next
renewal, never a card refund, and lasts at most 30 days; a termination ends service at the paid period end with
no mid-period refund unless a documented service failure is cited; a renewal keeps the pinned (locked) price and
a catalogue price change reaches it only after notice and acknowledgement (``payment.price_protection``).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_engine import ThreadRate, parse_package_body, project_package
from markup.package_models import PackageBody
from meter.component_units import ComponentUnitService
from payment.lifecycle_policy import export_available_until, paused_fee_credit_paise, pause_window_end, service_ends_at
from payment.price_protection import PriceProtection
from payment.prorata import (
    prorated_component_quantity,
    refund_fee_paise,
    remaining_seconds,
    upgrade_fee_difference_paise,
)
from pricing.models import PolicyBody, PricingKind
from pricing.repository import SqlPricingRepository
from promotions.coupon_versions import CouponError, redeem_coupon
from wallet.entity_models import as_utc
from wallet.ledger import WalletLedger

logger = logging.getLogger(__name__)

POLICY_SUBJECT_KEY: Final = "policy:platform"
_TS = DateTime(timezone=True)

POLICY_ABSENT: Final = "POLICY_ABSENT"
NO_ACTIVE_PERIOD: Final = "NO_ACTIVE_PERIOD"
PACKAGE_UNKNOWN: Final = "TARGET_PACKAGE_UNKNOWN"
PACKAGE_UNCHANGED: Final = "TARGET_PACKAGE_UNCHANGED"
NOT_AN_UPGRADE: Final = "TARGET_PACKAGE_NOT_DEARER"
NOT_A_DOWNGRADE: Final = "TARGET_PACKAGE_NOT_CHEAPER"
COMPONENT_NOT_IN_PACKAGE: Final = "COMPONENT_NOT_IN_PACKAGE"
RELATIONSHIP_TERMINATED: Final = "RELATIONSHIP_TERMINATED"
RENEWAL_AMOUNT_MISMATCH: Final = "RENEWAL_AMOUNT_MISMATCH"
CHARGE_MISMATCH: Final = "CHARGE_MISMATCH"
UPGRADE_FEE: Final = "UPGRADE_FEE"
FEE_REFUND: Final = "FEE_REFUND"
FEE_CREDIT: Final = "FEE_CREDIT"
RELATIONSHIP_TERMINATING: Final = "RELATIONSHIP_TERMINATING"
_RENEWABLE_STATUSES: Final = frozenset({"ACTIVE", "PAUSED", "SUSPENDED", "LAPSED"})


class LifecycleError(ValueError):
    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


class RateSource(Protocol):
    async def thread_rates(self, thread_ids: Sequence[str]) -> dict[str, ThreadRate]: ...


class RefundClient(Protocol):
    async def create_refund(self, payment_id: str, amount_paise: int, notes: Mapping[str, str]) -> str: ...


class OrderClient(Protocol):
    async def create_order(self, amount_paise: int, notes: dict[str, str]) -> dict: ...


class PackageSource(Protocol):
    async def by_version(self, version_id: UUID) -> ResolvedPackage | None: ...

    async def for_relationship(self, tenant_id: UUID, relationship_id: UUID) -> ResolvedPackage | None: ...

    async def by_code(
        self, agent_type: str, agent_version: str, package_code: str, at: datetime
    ) -> ResolvedPackage | None: ...


PolicySource = Callable[[datetime], Awaitable["PolicyBody | None"]]


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


@dataclass(frozen=True)
class ResolvedPackage:
    version_id: UUID
    body: PackageBody


@dataclass(frozen=True)
class RelationshipPeriod:
    tenant_id: UUID
    relationship_id: UUID
    period_start: datetime
    period_end: datetime
    package_version_id: UUID
    fee_paid_paise: int
    status: str
    paused_component_ids: tuple[str, ...]
    refunded_fee_paise: int
    scheduled_package_version_id: UUID | None
    grace_until: datetime | None
    payment_reference: str | None = None


@dataclass(frozen=True)
class LifecycleOutcome:
    status: str
    effective_at: datetime | None = None
    prorated_fee_difference_paise: int | None = None
    refund_fee_paise: int | None = None
    blocked_reason: str | None = None
    credit_fee_paise: int | None = None
    export_available_until: datetime | None = None


@dataclass(frozen=True)
class RenewalQuote:
    package_version_id: UUID
    starts_at: datetime
    price_paise: int
    credit_paise: int
    amount_due_paise: int


class PackageResolver:
    """Finds the package version a relationship was accepted on, or a for-sale package by its code."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlPricingRepository(session)

    async def by_version(self, version_id: UUID) -> ResolvedPackage | None:
        version = await self._repository.get(version_id)
        if version is None or version.kind is not PricingKind.PACKAGE:
            return None
        return ResolvedPackage(version.version_id, parse_package_body(version.body))

    async def for_relationship(self, tenant_id: UUID, relationship_id: UUID) -> ResolvedPackage | None:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT p.package_version_id
                    FROM business.relationship_commercial_authorities a
                    JOIN institutional.bundle_profiles p ON p.id = a.bundle_profile_id
                    WHERE a.tenant_id = :tenant AND a.relationship_id = :relationship
                      AND p.package_version_id IS NOT NULL
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).first()
        return None if row is None else await self.by_version(UUID(str(row[0])))

    async def by_code(
        self, agent_type: str, agent_version: str, package_code: str, at: datetime
    ) -> ResolvedPackage | None:
        version = await self._repository.effective_at(
            PricingKind.PACKAGE, f"package:{agent_type}|{agent_version}|{package_code}", at
        )
        return None if version is None else ResolvedPackage(version.version_id, parse_package_body(version.body))


async def effective_policy(session: AsyncSession, at: datetime) -> PolicyBody | None:
    version = await SqlPricingRepository(session).effective_at(PricingKind.POLICY, POLICY_SUBJECT_KEY, at)
    return None if version is None else PolicyBody.model_validate(version.body)


def period_credit_paise(package: PackageBody, rates: Mapping[str, ThreadRate]) -> int:
    """The wallet value of one period: what the recipes of every component cost at the pinned rates."""
    projection = project_package(package, rates, None)
    return sum(item.total_cost_paise for item in projection.component_costs)


def _recipe_threads(package: PackageBody) -> list[str]:
    return sorted({entry.thread_id for component in package.components for entry in component.recipe})


class PeriodStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, period: RelationshipPeriod, at: datetime) -> None:
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.relationship_periods
                (tenant_id, relationship_id, period_start, period_end, package_version_id, fee_paid_paise,
                 status, paused_component_ids, refunded_fee_paise, scheduled_package_version_id,
                 grace_until, updated_at, payment_reference)
                VALUES (:tenant, :relationship, :start, :end, :package, :fee, :status, :paused, 0, NULL,
                        NULL, :at, :payment_reference)
                ON CONFLICT DO NOTHING
                """,
                "start",
                "end",
                "at",
            ),
            {
                "tenant": str(period.tenant_id),
                "relationship": str(period.relationship_id),
                "start": as_utc(period.period_start),
                "end": as_utc(period.period_end),
                "package": str(period.package_version_id),
                "fee": period.fee_paid_paise,
                "status": period.status,
                "paused": json.dumps(list(period.paused_component_ids)),
                "at": as_utc(at),
                "payment_reference": period.payment_reference,
            },
        )

    async def starting_at(self, tenant_id: UUID, relationship_id: UUID, period_start: datetime) -> RelationshipPeriod | None:
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT * FROM business.relationship_periods
                    WHERE tenant_id = :tenant AND relationship_id = :relationship AND period_start = :start
                    """,
                    "start",
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id), "start": as_utc(period_start)},
            )
        ).mappings().all()
        return None if not rows else self._period(rows[0])

    async def by_payment(self, tenant_id: UUID, relationship_id: UUID, payment_reference: str) -> RelationshipPeriod | None:
        """The period a captured payment already paid for, so a replayed capture renews nothing twice."""
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT * FROM business.relationship_periods
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND payment_reference = :reference
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id), "reference": payment_reference},
            )
        ).mappings().all()
        return None if not rows else self._period(rows[0])

    async def current(self, tenant_id: UUID, relationship_id: UUID, at: datetime) -> RelationshipPeriod | None:
        """The period in force at ``at``; failing that, the latest one (a lapsed relationship)."""
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT * FROM business.relationship_periods
                    WHERE tenant_id = :tenant AND relationship_id = :relationship AND period_start <= :at
                    ORDER BY period_start DESC LIMIT 1
                    """,
                    "at",
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id), "at": as_utc(at)},
            )
        ).mappings().all()
        return None if not rows else self._period(rows[0])

    async def update(
        self,
        period: RelationshipPeriod,
        at: datetime,
        *,
        status: str | None = None,
        package_version_id: UUID | None = None,
        fee_paid_paise: int | None = None,
        paused_component_ids: Sequence[str] | None = None,
        refunded_fee_paise: int | None = None,
        scheduled_package_version_id: UUID | None = None,
        grace_until: datetime | None = None,
        clear_scheduled: bool = False,
        clear_grace: bool = False,
    ) -> None:
        await self._session.execute(
            _stmt(
                """
                UPDATE business.relationship_periods SET
                    status = :status, package_version_id = :package, fee_paid_paise = :fee,
                    paused_component_ids = :paused, refunded_fee_paise = :refunded,
                    scheduled_package_version_id = :scheduled, grace_until = :grace, updated_at = :at
                WHERE tenant_id = :tenant AND relationship_id = :relationship AND period_start = :start
                """,
                "start",
                "at",
                "grace",
            ),
            {
                "tenant": str(period.tenant_id),
                "relationship": str(period.relationship_id),
                "start": period.period_start,
                "status": status or period.status,
                "package": str(package_version_id or period.package_version_id),
                "fee": period.fee_paid_paise if fee_paid_paise is None else fee_paid_paise,
                "paused": json.dumps(
                    list(period.paused_component_ids if paused_component_ids is None else paused_component_ids)
                ),
                "refunded": period.refunded_fee_paise if refunded_fee_paise is None else refunded_fee_paise,
                "scheduled": None
                if clear_scheduled
                else str(scheduled_package_version_id or period.scheduled_package_version_id or "") or None,
                "grace": None if clear_grace else (grace_until or period.grace_until),
                "at": as_utc(at),
            },
        )

    async def due_for_suspension(self, at: datetime) -> list[RelationshipPeriod]:
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT * FROM business.relationship_periods
                    WHERE status = 'ACTIVE' AND grace_until IS NOT NULL AND grace_until <= :at
                    """,
                    "at",
                ),
                {"at": as_utc(at)},
            )
        ).mappings().all()
        return [self._period(row) for row in rows]

    @staticmethod
    def _period(row: Mapping[str, object]) -> RelationshipPeriod:
        scheduled = row["scheduled_package_version_id"]
        grace = row["grace_until"]
        return RelationshipPeriod(
            tenant_id=UUID(str(row["tenant_id"])),
            relationship_id=UUID(str(row["relationship_id"])),
            period_start=as_utc(row["period_start"]),
            period_end=as_utc(row["period_end"]),
            package_version_id=UUID(str(row["package_version_id"])),
            fee_paid_paise=int(row["fee_paid_paise"]),
            status=str(row["status"]),
            paused_component_ids=tuple(json.loads(row["paused_component_ids"]) if isinstance(
                row["paused_component_ids"], (str, bytes)) else row["paused_component_ids"] or ()),
            refunded_fee_paise=int(row["refunded_fee_paise"]),
            scheduled_package_version_id=None if not scheduled else UUID(str(scheduled)),
            grace_until=None if grace is None else as_utc(grace),
            payment_reference=row.get("payment_reference"),
        )


class PeriodMarks:
    """A pause end and a termination date kept beside the period they belong to (D1, D2)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set(
        self,
        period: RelationshipPeriod,
        at: datetime,
        *,
        pause_ends_at: datetime | None = None,
        terminates_at: datetime | None = None,
        service_failure_evidence_id: UUID | None = None,
    ) -> None:
        current = await self.get(period)
        pause = pause_ends_at or current.get("pause_ends_at")
        terminates = terminates_at or current.get("terminates_at")
        evidence = service_failure_evidence_id or current.get("service_failure_evidence_id")
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.relationship_period_marks
                (tenant_id, relationship_id, period_start, pause_ends_at, terminates_at,
                 service_failure_evidence_id, updated_at)
                VALUES (:tenant, :relationship, :start, :pause, :terminates, :evidence, :at)
                ON CONFLICT (tenant_id, relationship_id, period_start) DO UPDATE SET
                    pause_ends_at = excluded.pause_ends_at, terminates_at = excluded.terminates_at,
                    service_failure_evidence_id = excluded.service_failure_evidence_id,
                    updated_at = excluded.updated_at
                """,
                "start",
                "pause",
                "terminates",
                "at",
            ),
            {
                "tenant": str(period.tenant_id),
                "relationship": str(period.relationship_id),
                "start": as_utc(period.period_start),
                "pause": None if pause is None else as_utc(pause),
                "terminates": None if terminates is None else as_utc(terminates),
                "evidence": None if evidence is None else str(evidence),
                "at": as_utc(at),
            },
        )

    async def get(self, period: RelationshipPeriod) -> dict[str, object]:
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT pause_ends_at, terminates_at, service_failure_evidence_id
                    FROM business.relationship_period_marks
                    WHERE tenant_id = :tenant AND relationship_id = :relationship AND period_start = :start
                    """,
                    "start",
                ),
                {
                    "tenant": str(period.tenant_id),
                    "relationship": str(period.relationship_id),
                    "start": as_utc(period.period_start),
                },
            )
        ).mappings().all()
        return dict(rows[0]) if rows else {}

    async def terminates_at(self, period: RelationshipPeriod) -> datetime | None:
        value = (await self.get(period)).get("terminates_at")
        return None if value is None else as_utc(value)

    async def clear_pause(self, period: RelationshipPeriod, at: datetime) -> None:
        await self._session.execute(
            _stmt(
                """
                UPDATE business.relationship_period_marks SET pause_ends_at = NULL, updated_at = :at
                WHERE tenant_id = :tenant AND relationship_id = :relationship AND period_start = :start
                """,
                "start",
                "at",
            ),
            {
                "tenant": str(period.tenant_id),
                "relationship": str(period.relationship_id),
                "start": as_utc(period.period_start),
                "at": as_utc(at),
            },
        )

    async def due(self, column: str, at: datetime) -> list[tuple[UUID, UUID, datetime]]:
        """(tenant, relationship, period_start) whose pause end or termination date has been reached."""
        if column not in {"pause_ends_at", "terminates_at"}:
            raise ValueError(column)
        rows = (
            await self._session.execute(
                _stmt(
                    f"""
                    SELECT tenant_id, relationship_id, period_start FROM business.relationship_period_marks
                    WHERE {column} IS NOT NULL AND {column} <= :at
                    """,
                    "at",
                ),
                {"at": as_utc(at)},
            )
        ).mappings().all()
        return [(UUID(str(r["tenant_id"])), UUID(str(r["relationship_id"])), as_utc(r["period_start"])) for r in rows]


class BillingAdjustments:
    """Fee refunds are billing adjustments dispatched to the payment provider, never wallet entries."""

    def __init__(self, session: AsyncSession, *, now: Callable[[], datetime] | None = None) -> None:
        self._session = session
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def record_fee_refund(
        self, tenant_id: UUID, relationship_id: UUID, command_id: UUID, amount_paise: int
    ) -> UUID | None:
        if amount_paise <= 0:
            return None
        payment = (
            await self._session.execute(
                text(
                    """
                    SELECT razorpay_payment_id FROM payment_intents
                    WHERE tenant_id = :tenant AND relationship_id = :relationship AND status = 'ACTIVATED'
                    ORDER BY activated_at DESC LIMIT 1
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).first()
        reference = None if payment is None else payment[0]
        adjustment_id = uuid5(NAMESPACE_URL, f"fee-refund:{command_id}")
        now = self._now()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.billing_adjustments
                (adjustment_id, tenant_id, relationship_id, command_id, adjustment_kind, amount_paise,
                 payment_reference, status, created_at, updated_at)
                VALUES (:id, :tenant, :relationship, :command, 'FEE_REFUND', :amount, :reference, :status,
                        :now, :now)
                ON CONFLICT DO NOTHING
                """,
                "now",
            ),
            {
                "id": str(adjustment_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "command": str(command_id),
                "amount": amount_paise,
                "reference": reference,
                "status": "NOT_PAYABLE" if reference is None else "PENDING_PROVIDER",
                "now": now,
            },
        )
        return adjustment_id

    async def record_upgrade_charge(
        self, tenant_id: UUID, relationship_id: UUID, command_id: UUID, amount_paise: int
    ) -> UUID | None:
        """The pro-rated fee difference of an immediate upgrade, to be collected through a provider order."""
        if amount_paise <= 0:
            return None
        adjustment_id = uuid5(NAMESPACE_URL, f"upgrade-fee:{command_id}")
        now = self._now()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.billing_adjustments
                (adjustment_id, tenant_id, relationship_id, command_id, adjustment_kind, amount_paise,
                 payment_reference, status, created_at, updated_at)
                VALUES (:id, :tenant, :relationship, :command, 'UPGRADE_FEE', :amount, NULL, 'PENDING_PROVIDER',
                        :now, :now)
                ON CONFLICT DO NOTHING
                """,
                "now",
            ),
            {
                "id": str(adjustment_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "command": str(command_id),
                "amount": amount_paise,
                "now": now,
            },
        )
        return adjustment_id

    async def record_fee_credit(
        self, tenant_id: UUID, relationship_id: UUID, command_id: UUID, amount_paise: int
    ) -> UUID | None:
        """The unused days of a pause, credited to the next renewal and never refunded to the card (D1)."""
        if amount_paise <= 0:
            return None
        adjustment_id = uuid5(NAMESPACE_URL, f"fee-credit:{command_id}")
        now = self._now()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.billing_adjustments
                (adjustment_id, tenant_id, relationship_id, command_id, adjustment_kind, amount_paise,
                 remaining_paise, payment_reference, status, created_at, updated_at)
                VALUES (:id, :tenant, :relationship, :command, 'FEE_CREDIT', :amount, :amount, NULL, 'AVAILABLE',
                        :now, :now)
                ON CONFLICT DO NOTHING
                """,
                "now",
            ),
            {
                "id": str(adjustment_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "command": str(command_id),
                "amount": amount_paise,
                "now": now,
            },
        )
        return adjustment_id

    async def available_credit_paise(self, tenant_id: UUID, relationship_id: UUID) -> int:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(remaining_paise), 0) FROM business.billing_adjustments
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND adjustment_kind = 'FEE_CREDIT' AND status = 'AVAILABLE'
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).first()
        return int(row[0] or 0)

    async def apply_credit(
        self, tenant_id: UUID, relationship_id: UUID, amount_paise: int, payment_reference: str
    ) -> int:
        """Use available credit, oldest first, against a renewal; returns the paise applied."""
        if amount_paise <= 0:
            return 0
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT adjustment_id, remaining_paise FROM business.billing_adjustments
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND adjustment_kind = 'FEE_CREDIT' AND status = 'AVAILABLE'
                    ORDER BY created_at, adjustment_id
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).mappings().all()
        left = amount_paise
        for row in rows:
            if left <= 0:
                break
            take = min(left, int(row["remaining_paise"]))
            remaining = int(row["remaining_paise"]) - take
            await self._session.execute(
                _stmt(
                    """
                    UPDATE business.billing_adjustments
                    SET remaining_paise = :remaining, status = :status,
                        payment_reference = COALESCE(:reference, payment_reference), updated_at = :now
                    WHERE adjustment_id = :id
                    """,
                    "now",
                ),
                {
                    "remaining": remaining,
                    "status": "APPLIED" if remaining == 0 else "AVAILABLE",
                    "reference": payment_reference if remaining == 0 else None,
                    "now": self._now(),
                    "id": str(row["adjustment_id"]),
                },
            )
            left -= take
        return amount_paise - left

    async def collect_pending(self, client: OrderClient, limit: int) -> int:
        """Open a provider order for each upgrade fee not yet collected; a failure stays retryable."""
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT adjustment_id, tenant_id, relationship_id, amount_paise
                    FROM business.billing_adjustments
                    WHERE adjustment_kind = 'UPGRADE_FEE' AND status IN ('PENDING_PROVIDER', 'FAILED_RETRYABLE')
                    ORDER BY created_at LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings().all()
        opened = 0
        for row in rows:
            try:
                order = await client.create_order(
                    int(row["amount_paise"]),
                    {
                        "checkout_kind": UPGRADE_FEE,
                        "adjustment_id": str(row["adjustment_id"]),
                        "tenant_id": str(row["tenant_id"]),
                        "relationship_id": str(row["relationship_id"]),
                    },
                )
                provider_reference, status = str(order["id"]), "ORDER_CREATED"
                opened += 1
            except Exception:
                logger.warning("billing_adjustment order=failed adjustment=%s", row["adjustment_id"])
                provider_reference, status = None, "FAILED_RETRYABLE"
            await self._session.execute(
                _stmt(
                    """
                    UPDATE business.billing_adjustments
                    SET status = :status, provider_reference = :reference, updated_at = :now
                    WHERE adjustment_id = :id
                    """,
                    "now",
                ),
                {"status": status, "reference": provider_reference, "now": self._now(), "id": str(row["adjustment_id"])},
            )
        return opened

    async def mark_charge_captured(self, adjustment_id: UUID, payment_reference: str, amount_paise: int) -> bool:
        """Record the capture of an upgrade fee; a capture that differs from the fee is refused, a replay is a no-op."""
        row = (
            await self._session.execute(
                text(
                    "SELECT amount_paise, status FROM business.billing_adjustments "
                    "WHERE adjustment_id = :id AND adjustment_kind = 'UPGRADE_FEE'"
                ),
                {"id": str(adjustment_id)},
            )
        ).first()
        if row is None or int(row[0]) != amount_paise:
            raise LifecycleError(CHARGE_MISMATCH)
        if row[1] == "COLLECTED":
            return False
        await self._session.execute(
            _stmt(
                """
                UPDATE business.billing_adjustments
                SET status = 'COLLECTED', payment_reference = :reference, updated_at = :now
                WHERE adjustment_id = :id
                """,
                "now",
            ),
            {"reference": payment_reference, "now": self._now(), "id": str(adjustment_id)},
        )
        return True

    async def dispatch_pending(self, client: RefundClient, limit: int) -> int:
        """Send open refunds to the provider; a provider failure leaves the row retryable."""
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT adjustment_id, tenant_id, relationship_id, command_id, amount_paise, payment_reference
                    FROM business.billing_adjustments
                    WHERE adjustment_kind = 'FEE_REFUND' AND status IN ('PENDING_PROVIDER', 'FAILED_RETRYABLE')
                      AND payment_reference IS NOT NULL
                    ORDER BY created_at LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings().all()
        dispatched = 0
        for row in rows:
            try:
                provider_reference = await client.create_refund(
                    str(row["payment_reference"]),
                    int(row["amount_paise"]),
                    {"adjustment_id": str(row["adjustment_id"]), "kind": "pro_rata_fee"},
                )
                status = "DISPATCHED"
                dispatched += 1
            except Exception:
                logger.warning("billing_adjustment dispatch=failed adjustment=%s", row["adjustment_id"])
                provider_reference, status = None, "FAILED_RETRYABLE"
            await self._session.execute(
                _stmt(
                    """
                    UPDATE business.billing_adjustments
                    SET status = :status, provider_reference = :reference, updated_at = :now
                    WHERE adjustment_id = :id
                    """,
                    "now",
                ),
                {"status": status, "reference": provider_reference, "now": self._now(), "id": str(row["adjustment_id"])},
            )
        return dispatched


class PeriodCreditService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        rates: RateSource,
        overrun_tolerance_paise: int = 0,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._rates = rates
        self._ledger = WalletLedger(session, overrun_tolerance_paise=overrun_tolerance_paise, now=now)
        self._periods = PeriodStore(session)
        self._units = ComponentUnitService(session, now=now)
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def start_period(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        customer_id: UUID,
        package: ResolvedPackage,
        period_start: datetime,
        fee_paid_paise: int,
        evidence_id: UUID,
        payment_reference: str | None = None,
    ) -> RelationshipPeriod:
        """Credit the period's wallet lot, open its component units and record the period.

        A renewal also lapses the previous lot: unspent credit never rolls over. Replaying the same period
        credits nothing twice (the lot idempotency key is derived from the period).
        """
        start = as_utc(period_start)
        end = start + timedelta(days=package.body.billing_period_days)
        rates = await self._rates.thread_rates(_recipe_threads(package.body))
        account = await self._ledger.open_account(
            tenant_id, "SUBSCRIPTION", owner_ref=customer_id, relationship_id=relationship_id
        )
        await self._ledger.expire(account, start)
        paise = period_credit_paise(package.body, rates)
        if paise > 0:
            await self._ledger.credit(
                account,
                "PERIOD_CREDIT",
                paise,
                start,
                end,
                f"period:{start.isoformat()}",
                {
                    "package": str(package.version_id),
                    "rates": {thread_id: rate.marked_up_cost_paise for thread_id, rate in sorted(rates.items())},
                },
                uuid5(NAMESPACE_URL, f"period-credit:{tenant_id}:{relationship_id}:{start.isoformat()}"),
                source_kind="PACKAGE_PERIOD",
                evidence_id=evidence_id,
            )
        period = RelationshipPeriod(
            tenant_id, relationship_id, start, end, package.version_id, fee_paid_paise, "ACTIVE", (), 0, None, None,
            payment_reference,
        )
        await self._periods.insert(period, self._now())
        await self._units.open_period(
            tenant_id, relationship_id, relationship_id, package.version_id, package.body, start, end
        )
        return period


class LifecycleService:
    """Executes the lifecycle commands of a relationship against its stored period and the POLICY."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        rates: RateSource,
        packages: PackageSource | None = None,
        policy: PolicySource | None = None,
        now: Callable[[], datetime] | None = None,
        overrun_tolerance_paise: int = 0,
    ) -> None:
        self._session = session
        self._rates = rates
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._periods = PeriodStore(session)
        self._packages = packages or PackageResolver(session)
        self._policy = policy or (lambda at: effective_policy(session, at))
        self._adjustments = BillingAdjustments(session, now=self._now)
        self._marks = PeriodMarks(session)
        self._protection = PriceProtection(session, now=self._now)
        self._ledger = WalletLedger(session, overrun_tolerance_paise=overrun_tolerance_paise, now=self._now)
        self._units = ComponentUnitService(session, now=self._now)

    async def execute(
        self,
        command_kind: str,
        tenant_id: UUID,
        relationship_id: UUID,
        command_id: UUID,
        *,
        component_ids: Sequence[str] | None = None,
        target_package_code: str | None = None,
        service_failure_evidence_id: UUID | None = None,
    ) -> LifecycleOutcome:
        at = self._now()
        policy = await self._policy(at)
        if command_kind in {"RENEW_RELATIONSHIP", "TERMINATE_RELATIONSHIP"} and policy is None:
            return LifecycleOutcome("BLOCKED", blocked_reason=POLICY_ABSENT)
        period = await self._periods.current(tenant_id, relationship_id, at)
        if period is None:
            return LifecycleOutcome("UNAVAILABLE", blocked_reason=NO_ACTIVE_PERIOD)
        try:
            if command_kind == "PAUSE_RELATIONSHIP":
                return await self._pause(period, component_ids, command_id, at)
            if command_kind == "RESUME_RELATIONSHIP":
                return await self._resume(period, component_ids, at)
            if command_kind == "TERMINATE_RELATIONSHIP":
                return await self._terminate(period, command_id, at, service_failure_evidence_id)
            if command_kind == "RENEW_RELATIONSHIP":
                return await self._renew_command(period)
            if command_kind in {"UPGRADE_PACKAGE", "DOWNGRADE_PACKAGE"}:
                return await self._change_package(
                    command_kind, period, target_package_code, policy, command_id, at
                )
        except LifecycleError as error:
            return LifecycleOutcome("REJECTED", blocked_reason=error.code)
        return LifecycleOutcome("REJECTED", blocked_reason="COMMAND_NOT_LIFECYCLE")

    async def record_payment_failure(self, tenant_id: UUID, relationship_id: UUID) -> datetime:
        """A failed renewal payment starts the grace period; its length comes from the POLICY only."""
        at = self._now()
        policy = await self._policy(at)
        if policy is None:
            raise LifecycleError(POLICY_ABSENT)
        period = await self._periods.current(tenant_id, relationship_id, at)
        if period is None:
            raise LifecycleError(NO_ACTIVE_PERIOD)
        grace_until = as_utc(max(at, period.period_end)) + timedelta(days=policy.payment_grace_days)
        await self._periods.update(period, at, grace_until=grace_until)
        return grace_until

    async def suspend_expired_grace(self) -> int:
        """Move relationships whose grace ended without payment to SUSPENDED; their credit lapses."""
        at = self._now()
        due = await self._periods.due_for_suspension(at)
        for period in due:
            await self._periods.update(period, at, status="SUSPENDED")
            account = await self._ledger.find_account(
                period.tenant_id, "SUBSCRIPTION", relationship_id=period.relationship_id
            )
            if account is not None:
                await self._ledger.expire(account, period.period_end)
        return len(due)

    async def _renewal_terms(
        self, period: RelationshipPeriod, policy: PolicyBody, at: datetime
    ) -> tuple[ResolvedPackage, datetime]:
        """The package a renewal uses and when its period starts. The package is the one scheduled at renewal (a
        downgrade) or else the locked one; a catalogue price change applies only once noticed and acknowledged."""
        in_grace = period.status in {"ACTIVE", "PAUSED"} and at <= period.period_end + timedelta(
            days=policy.payment_grace_days
        )
        start = as_utc(period.period_end if in_grace else at)
        version_id = period.scheduled_package_version_id
        if version_id is None:
            version_id = await self._protection.applicable_version(
                period.tenant_id, period.relationship_id, period.package_version_id, start
            )
        package = await self._packages.by_version(version_id or period.package_version_id)
        if package is None:
            raise LifecycleError(PACKAGE_UNKNOWN)
        return package, start

    async def renewal_quote(self, tenant_id: UUID, relationship_id: UUID) -> RenewalQuote:
        """What the next renewal costs: the locked price less any pause credit (D1, D3). Nothing is written."""
        at = self._now()
        policy = await self._policy(at)
        if policy is None:
            raise LifecycleError(POLICY_ABSENT)
        period = await self._periods.current(tenant_id, relationship_id, at)
        if period is None:
            raise LifecycleError(NO_ACTIVE_PERIOD)
        if period.status == "TERMINATED":
            raise LifecycleError(RELATIONSHIP_TERMINATED)
        if await self._marks.terminates_at(period) is not None:
            raise LifecycleError(RELATIONSHIP_TERMINATING)
        package, start = await self._renewal_terms(period, policy, at)
        price = package.body.price_incl_gst_paise
        credit = min(price, await self._adjustments.available_credit_paise(tenant_id, relationship_id))
        return RenewalQuote(package.version_id, start, price, credit, price - credit)

    async def renew_from_credit(
        self, tenant_id: UUID, relationship_id: UUID, customer_id: UUID, *, authority: str
    ) -> RelationshipPeriod | None:
        """A renewal the pause credit pays in full needs no provider payment; it is recorded under a reference
        derived from the period so a replay renews nothing twice."""
        current = await self._periods.current(tenant_id, relationship_id, self._now())
        if current is not None and (current.payment_reference or "").startswith(f"credit:{relationship_id}:"):
            return current
        quote = await self.renewal_quote(tenant_id, relationship_id)
        if quote.amount_due_paise != 0:
            raise LifecycleError(RENEWAL_AMOUNT_MISMATCH)
        reference = f"credit:{relationship_id}:{quote.starts_at.isoformat()}"
        return await self.renew_paid(
            tenant_id,
            relationship_id,
            customer_id,
            payment_reference=reference,
            fee_paid_paise=0,
            evidence_id=uuid5(NAMESPACE_URL, f"waooaw:credit-renewal:{reference}"),
            authority=authority,
        )

    async def resume_expired_pauses(self) -> int:
        """A pause lasts at most 30 days: the paused components come back when its window ends (D1)."""
        at = self._now()
        resumed = 0
        for tenant_id, relationship_id, period_start in await self._marks.due("pause_ends_at", at):
            period = await self._periods.starting_at(tenant_id, relationship_id, period_start)
            if period is None:
                continue
            await self._marks.clear_pause(period, at)
            if period.paused_component_ids and period.status in {"ACTIVE", "PAUSED"}:
                await self._periods.update(
                    period, at, status="ACTIVE" if period.status == "PAUSED" else None, paused_component_ids=[]
                )
                resumed += 1
        return resumed

    async def finalize_terminations(self) -> int:
        """Service ends at the paid period end: a termination reaching its date becomes TERMINATED (D2)."""
        at = self._now()
        ended = 0
        for tenant_id, relationship_id, period_start in await self._marks.due("terminates_at", at):
            period = await self._periods.starting_at(tenant_id, relationship_id, period_start)
            if period is None or period.status == "TERMINATED":
                continue
            await self._periods.update(period, at, status="TERMINATED", clear_scheduled=True, clear_grace=True)
            account = await self._ledger.find_account(
                period.tenant_id, "SUBSCRIPTION", relationship_id=period.relationship_id
            )
            if account is not None:
                await self._ledger.expire(account, period.period_end)
            ended += 1
        return ended

    async def _package(self, period: RelationshipPeriod) -> ResolvedPackage:
        package = await self._packages.by_version(period.package_version_id)
        if package is None:
            raise LifecycleError(PACKAGE_UNKNOWN)
        return package

    async def _pause(
        self, period: RelationshipPeriod, component_ids: Sequence[str] | None, command_id: UUID, at: datetime
    ) -> LifecycleOutcome:
        if period.status != "ACTIVE":
            raise LifecycleError(NO_ACTIVE_PERIOD)
        package = await self._package(period)
        every = {component.component_id for component in package.body.components}
        chosen = set(every) if not component_ids else set(component_ids)
        if chosen - every:
            raise LifecycleError(COMPONENT_NOT_IN_PACKAGE)
        fresh = chosen - set(period.paused_component_ids)
        credit = 0
        if fresh:
            credit = min(
                paused_fee_credit_paise(
                    package.body, period.fee_paid_paise, fresh, period.period_start, period.period_end, at
                ),
                period.fee_paid_paise - period.refunded_fee_paise,
            )
        paused = sorted(set(period.paused_component_ids) | chosen)
        await self._periods.update(
            period,
            at,
            status="PAUSED" if set(paused) == every else None,
            paused_component_ids=paused,
            refunded_fee_paise=period.refunded_fee_paise + credit,
        )
        pause_ends_at = pause_window_end(period.period_end, at)
        await self._marks.set(period, at, pause_ends_at=pause_ends_at)
        await self._adjustments.record_fee_credit(period.tenant_id, period.relationship_id, command_id, credit)
        return LifecycleOutcome("COMPLETED", effective_at=at, credit_fee_paise=credit)

    async def _renew_command(self, period: RelationshipPeriod) -> LifecycleOutcome:
        """A renewal takes effect when the next period's payment is captured (``renew_paid``).

        Until then the command is PENDING for the end of the current period; once the next period exists it is
        COMPLETED. A terminated relationship cannot renew.
        """
        if period.status == "TERMINATED":
            raise LifecycleError(RELATIONSHIP_TERMINATED)
        if await self._marks.terminates_at(period) is not None:
            raise LifecycleError(RELATIONSHIP_TERMINATING)
        upcoming = await self._periods.starting_at(period.tenant_id, period.relationship_id, period.period_end)
        if upcoming is not None:
            return LifecycleOutcome("COMPLETED", effective_at=upcoming.period_start)
        return LifecycleOutcome("PENDING", effective_at=period.period_end)

    async def renew_paid(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        customer_id: UUID,
        *,
        payment_reference: str,
        fee_paid_paise: int,
        evidence_id: UUID,
        authority: str,
        coupon_code: str | None = None,
        redeem: Callable[..., Awaitable[object]] = redeem_coupon,
    ) -> RelationshipPeriod | None:
        """Start the next period for a captured renewal payment and credit its wallet lot.

        The package is the one scheduled at renewal (a downgrade) or else the one the period runs on, so the
        customer keeps the pinned version (C-090). A coupon is redeemed for the renewal and the captured amount
        must equal the price after it. The previous period lapses, grace is cleared and its unspent credit
        lapses with the new lot's start; a replayed capture returns the period it already paid for. Returns
        None in LEGACY wallet mode.
        """
        if authority == "LEGACY":
            return None
        replay = await self._periods.by_payment(tenant_id, relationship_id, payment_reference)
        if replay is not None:
            return replay
        at = self._now()
        policy = await self._policy(at)
        if policy is None:
            raise LifecycleError(POLICY_ABSENT)
        period = await self._periods.current(tenant_id, relationship_id, at)
        if period is None:
            raise LifecycleError(NO_ACTIVE_PERIOD)
        if period.status == "TERMINATED":
            raise LifecycleError(RELATIONSHIP_TERMINATED)
        if period.status not in _RENEWABLE_STATUSES:
            raise LifecycleError(NO_ACTIVE_PERIOD)
        if await self._marks.terminates_at(period) is not None:
            raise LifecycleError(RELATIONSHIP_TERMINATING)
        package, start = await self._renewal_terms(period, policy, at)
        price = package.body.price_incl_gst_paise
        if coupon_code:
            try:
                redemption = await redeem(
                    self._session,
                    code=coupon_code,
                    agent_type=package.body.agent_type,
                    agent_version=package.body.agent_version,
                    tenant_id=tenant_id,
                    relationship_id=relationship_id,
                    event="RENEWAL",
                    period_start=start,
                    price_incl_gst_paise=price,
                    idempotency_key=uuid5(NAMESPACE_URL, f"coupon-renewal:{tenant_id}:{relationship_id}:{payment_reference}"),
                    at=at,
                )
            except CouponError as error:
                raise LifecycleError(error.code) from error
            price = redemption.quote.discounted_price_paise
        credit = min(price, await self._adjustments.available_credit_paise(tenant_id, relationship_id))
        if fee_paid_paise != price - credit:
            raise LifecycleError(RENEWAL_AMOUNT_MISMATCH)
        await self._adjustments.apply_credit(tenant_id, relationship_id, credit, payment_reference)
        renewed = await PeriodCreditService(
            self._session, rates=self._rates, now=self._now
        ).start_period(
            tenant_id, relationship_id, customer_id, package, start, fee_paid_paise, evidence_id, payment_reference
        )
        await self._periods.update(
            period, at, status="LAPSED" if start <= as_utc(at) else None, clear_scheduled=True, clear_grace=True
        )
        return renewed

    async def _resume(
        self, period: RelationshipPeriod, component_ids: Sequence[str] | None, at: datetime
    ) -> LifecycleOutcome:
        if not period.paused_component_ids and period.status != "PAUSED":
            return LifecycleOutcome("COMPLETED", effective_at=at)
        # The paused days were credited when the pause began, so the components come back when the pause window
        # ends (at most 30 days, or the period end) and a renewal bills the whole package again.
        marked = (await self._marks.get(period)).get("pause_ends_at")
        return LifecycleOutcome("PENDING", effective_at=as_utc(marked) if marked else period.period_end)

    async def _terminate(
        self,
        period: RelationshipPeriod,
        command_id: UUID,
        at: datetime,
        service_failure_evidence_id: UUID | None = None,
    ) -> LifecycleOutcome:
        """Service ends at the paid period end with no mid-period refund (D2). A documented service failure, cited
        by its evidence id, ends service now and refunds the unused fee pro rata."""
        if period.status == "TERMINATED":
            return LifecycleOutcome("COMPLETED", effective_at=at, refund_fee_paise=0)
        if service_failure_evidence_id is not None and service_failure_evidence_id != UUID(int=0):
            package = await self._package(period)
            owed = refund_fee_paise(
                package.body, period.fee_paid_paise, None, period.period_start, period.period_end, at
            )
            refund = max(0, min(owed - period.refunded_fee_paise, period.fee_paid_paise - period.refunded_fee_paise))
            await self._periods.update(
                period, at, status="TERMINATED", refunded_fee_paise=period.refunded_fee_paise + refund,
                clear_scheduled=True, clear_grace=True,
            )
            await self._marks.set(
                period, at, terminates_at=at, service_failure_evidence_id=service_failure_evidence_id
            )
            await self._adjustments.record_fee_refund(period.tenant_id, period.relationship_id, command_id, refund)
            account = await self._ledger.find_account(
                period.tenant_id, "SUBSCRIPTION", relationship_id=period.relationship_id
            )
            if account is not None:
                await self._ledger.expire(account, period.period_end)
            return LifecycleOutcome(
                "COMPLETED", effective_at=at, refund_fee_paise=refund, export_available_until=export_available_until(at)
            )
        ends_at = service_ends_at(period.period_end)
        await self._marks.set(period, at, terminates_at=ends_at)
        await self._periods.update(period, at, clear_scheduled=True, clear_grace=True)
        return LifecycleOutcome(
            "PENDING", effective_at=ends_at, refund_fee_paise=0, export_available_until=export_available_until(ends_at)
        )

    async def _change_package(
        self,
        command_kind: str,
        period: RelationshipPeriod,
        target_code: str | None,
        policy: PolicyBody | None,
        command_id: UUID,
        at: datetime,
    ) -> LifecycleOutcome:
        if policy is None:
            return LifecycleOutcome("BLOCKED", blocked_reason=POLICY_ABSENT)
        if period.status != "ACTIVE":
            raise LifecycleError(NO_ACTIVE_PERIOD)
        current = await self._package(period)
        if not target_code:
            raise LifecycleError(PACKAGE_UNKNOWN)
        target = await self._packages.by_code(current.body.agent_type, current.body.agent_version, target_code, at)
        if target is None:
            raise LifecycleError(PACKAGE_UNKNOWN)
        if target.version_id == current.version_id:
            raise LifecycleError(PACKAGE_UNCHANGED)
        upgrade = command_kind == "UPGRADE_PACKAGE"
        dearer = target.body.price_incl_gst_paise > current.body.price_incl_gst_paise
        if upgrade and not dearer:
            raise LifecycleError(NOT_AN_UPGRADE)
        if not upgrade and dearer:
            raise LifecycleError(NOT_A_DOWNGRADE)
        timing = policy.upgrade_timing if upgrade else policy.downgrade_timing
        if timing == "AT_RENEWAL":
            await self._periods.update(period, at, scheduled_package_version_id=target.version_id)
            return LifecycleOutcome("PENDING", effective_at=period.period_end)
        difference = (
            upgrade_fee_difference_paise(
                current.body.price_incl_gst_paise, target.body.price_incl_gst_paise,
                period.period_start, period.period_end, at,
            )
            if upgrade
            else 0
        )
        await self._apply_package(period, current, target, difference, at)
        if upgrade:
            await self._adjustments.record_upgrade_charge(period.tenant_id, period.relationship_id, command_id, difference)
        return LifecycleOutcome(
            "COMPLETED", effective_at=at, prorated_fee_difference_paise=difference if upgrade else None
        )

    async def _apply_package(
        self,
        period: RelationshipPeriod,
        current: ResolvedPackage,
        target: ResolvedPackage,
        fee_difference_paise: int,
        at: datetime,
    ) -> None:
        """Switch the period to ``target``: new components for the unelapsed remainder and, on an upgrade,
        a pro-rated PERIOD_CREDIT lot for the extra recipe cost."""
        rates = await self._rates.thread_rates(sorted(set(_recipe_threads(current.body)) | set(_recipe_threads(target.body))))
        remaining = remaining_seconds(period.period_start, period.period_end, at)
        whole = int((period.period_end - period.period_start).total_seconds())
        extra = max(0, period_credit_paise(target.body, rates) - period_credit_paise(current.body, rates))
        lot_paise = (2 * extra * remaining + whole) // (2 * whole) if whole else 0
        account = await self._ledger.find_account(
            period.tenant_id, "SUBSCRIPTION", relationship_id=period.relationship_id
        )
        if lot_paise > 0 and account is not None:
            await self._ledger.credit(
                account,
                "PERIOD_CREDIT",
                lot_paise,
                at,
                period.period_end,
                f"upgrade:{target.version_id}:{as_utc(at).isoformat()}",
                {"package": str(target.version_id)},
                uuid5(NAMESPACE_URL, f"upgrade-credit:{period.relationship_id}:{target.version_id}:{period.period_start}"),
                source_kind="PACKAGE_PERIOD",
                evidence_id=uuid4(),
            )
        resized = target.body.model_copy(
            update={
                "components": [
                    component.model_copy(
                        update={
                            "quantity": prorated_component_quantity(
                                component.quantity, period.period_start, period.period_end, at
                            )
                        }
                    )
                    for component in target.body.components
                ]
            }
        )
        await self._units.open_period(
            period.tenant_id, period.relationship_id, period.relationship_id, target.version_id, resized,
            as_utc(at), period.period_end,
        )
        await self._periods.update(
            period, at,
            package_version_id=target.version_id,
            fee_paid_paise=period.fee_paid_paise + fee_difference_paise,
            clear_scheduled=True,
        )


async def credit_paid_period(
    session: AsyncSession,
    *,
    rates: RateSource,
    tenant_id: UUID,
    relationship_id: UUID,
    customer_id: UUID,
    period_start: datetime,
    evidence_id: UUID,
    authority: str,
    now: Callable[[], datetime] | None = None,
    coupon_code: str | None = None,
    redeem: Callable[..., Awaitable[object]] = redeem_coupon,
    packages: PackageSource | None = None,
) -> RelationshipPeriod | None:
    """Credit a hire or renewal period when the wallet is the authority and a package version is pinned.

    Returns None, writing nothing, in LEGACY mode or for a relationship accepted outside a package version.
    A versioned goodwill coupon is redeemed for the hire (C5-07) and the fee paid is the price after it; a
    code that is not a versioned coupon (the legacy demo registry) or that can no longer be redeemed leaves
    the fee at the package price and is logged, never turned into wallet credit.
    """
    if authority == "LEGACY":
        return None
    package = await (packages or PackageResolver(session)).for_relationship(tenant_id, relationship_id)
    if package is None:
        return None
    fee_paid = package.body.price_incl_gst_paise
    if coupon_code:
        try:
            redemption = await redeem(
                session,
                code=coupon_code,
                agent_type=package.body.agent_type,
                agent_version=package.body.agent_version,
                tenant_id=tenant_id,
                relationship_id=relationship_id,
                event="HIRE",
                period_start=as_utc(period_start),
                price_incl_gst_paise=fee_paid,
                idempotency_key=uuid5(NAMESPACE_URL, f"coupon-hire:{tenant_id}:{relationship_id}:{coupon_code}"),
                at=(now or (lambda: datetime.now(timezone.utc)))(),
            )
            fee_paid = redemption.quote.discounted_price_paise
        except CouponError as error:
            logger.warning("hire coupon not redeemed code=%s reason=%s", coupon_code, error.code)
    return await PeriodCreditService(session, rates=rates, now=now).start_period(
        tenant_id, relationship_id, customer_id, package, period_start, fee_paid, evidence_id,
    )
