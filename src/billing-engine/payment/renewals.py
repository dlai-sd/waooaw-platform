# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R016
# Constitutional basis: C-023, C-059, C-063
"""Recurring billing after activation: open each renewal, pay it from credit when credit covers it, and start grace.

Activation (``PaidActivationService``) starts the first period. This sweep looks at every relationship whose period is
about to end without a successor: a renewal the pause credit pays in full is recorded without the provider, any other
renewal opens one Razorpay order whose capture ``complete_captured_payment`` turns into the next period, and a renewal
still unpaid when its period ends starts the grace period the POLICY defines (suspension follows in the lifecycle
sweep). Cancel, stop and refund stay lifecycle commands; a terminating relationship is never renewed. Every step is
recorded in ``renewal_collections`` and is safe to repeat.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from invoicing.hooks import payer_of
from markup.package_engine import SqlPackageReferenceData
from payment.lifecycle import LifecycleError, LifecycleService, OrderClient, PeriodStore
from payment.razorpay_client import RazorpayClient
from wallet import mirror
from wallet.entity_models import as_utc

logger = logging.getLogger(__name__)
_TS = DateTime(timezone=True)

RENEWAL = "RENEWAL"
_LEAD_DAYS = 3
_BATCH = 50


@dataclass(frozen=True)
class RenewalSweepReport:
    ordered: int
    from_credit: int
    grace_started: int


def _stmt(sql: str, *datetime_params: str) -> TextClause:
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


LifecycleFactory = Callable[[AsyncSession, Callable[[], datetime]], LifecycleService]


def _sql_lifecycle(session: AsyncSession, clock: Callable[[], datetime]) -> LifecycleService:
    return LifecycleService(session, rates=SqlPackageReferenceData(session), now=clock)


async def start_grace_once(
    session: AsyncSession,
    tenant_id: UUID,
    relationship_id: UUID,
    *,
    now: Callable[[], datetime] | None = None,
    lifecycle_factory: LifecycleFactory = _sql_lifecycle,
) -> str:
    """Start the grace period of a failed renewal unless it already started, so a replay never extends it."""
    clock = now or (lambda: datetime.now(timezone.utc))
    period = await PeriodStore(session).current(tenant_id, relationship_id, clock())
    if period is None or period.grace_until is not None or period.status not in {"ACTIVE", "PAUSED"}:
        return "NOT_APPLICABLE"
    try:
        await lifecycle_factory(session, clock).record_payment_failure(tenant_id, relationship_id)
    except LifecycleError:
        await session.rollback()
        return "NOT_APPLICABLE"
    await session.commit()
    return "GRACE_STARTED"


async def _due_periods(session: AsyncSession, horizon: datetime) -> list[dict]:
    rows = (
        (
            await session.execute(
                _stmt(
                    """
                SELECT p.tenant_id, p.relationship_id, p.period_start, p.period_end FROM business.relationship_periods p
                WHERE p.status IN ('ACTIVE', 'PAUSED') AND p.period_end <= :horizon
                  AND NOT EXISTS (
                    SELECT 1 FROM business.relationship_periods n
                    WHERE n.tenant_id = p.tenant_id AND n.relationship_id = p.relationship_id
                      AND n.period_start > p.period_start)
                ORDER BY p.period_end LIMIT :limit
                """,
                    "horizon",
                ),
                {"horizon": as_utc(horizon), "limit": _BATCH},
            )
        )
        .mappings()
        .all()
    )
    return [
        {
            "tenant": UUID(str(row["tenant_id"])),
            "relationship": UUID(str(row["relationship_id"])),
            "start": as_utc(row["period_start"]),
            "end": as_utc(row["period_end"]),
        }
        for row in rows
    ]


async def _collection_status(session: AsyncSession, due: dict) -> str | None:
    row = (
        await session.execute(
            _stmt(
                "SELECT status FROM business.renewal_collections WHERE tenant_id = :tenant "
                "AND relationship_id = :relationship AND period_start = :start",
                "start",
            ),
            {"tenant": str(due["tenant"]), "relationship": str(due["relationship"]), "start": due["start"]},
        )
    ).first()
    return None if row is None else str(row[0])


async def _record(session: AsyncSession, due: dict, status: str, order_id: str | None, amount_paise: int, now: datetime) -> None:
    await session.execute(
        _stmt(
            """
            INSERT INTO business.renewal_collections
            (tenant_id, relationship_id, period_start, order_id, amount_paise, status, created_at, updated_at)
            VALUES (:tenant, :relationship, :start, :order, :amount, :status, :now, :now)
            ON CONFLICT (tenant_id, relationship_id, period_start) DO UPDATE SET status = :status, updated_at = :now
            """,
            "start",
            "now",
        ),
        {
            "tenant": str(due["tenant"]),
            "relationship": str(due["relationship"]),
            "start": due["start"],
            "order": order_id,
            "amount": amount_paise,
            "status": status,
            "now": as_utc(now),
        },
    )


async def run_renewal_sweep(
    open_session: Callable[[], AsyncSession],
    order_client: OrderClient | None = None,
    *,
    now: Callable[[], datetime] | None = None,
    lead_days: int = _LEAD_DAYS,
    lifecycle_factory: LifecycleFactory = _sql_lifecycle,
) -> RenewalSweepReport:
    """Open renewals that fall due within ``lead_days`` and start grace for those that went unpaid past their period."""
    clock = now or (lambda: datetime.now(timezone.utc))
    authority = mirror.wallet_authority()
    if authority == "LEGACY":
        return RenewalSweepReport(0, 0, 0)
    client = order_client or RazorpayClient()
    ordered = from_credit = grace = 0
    async with open_session() as session:
        dues = await _due_periods(session, clock() + timedelta(days=lead_days))
    for due in dues:
        try:
            async with open_session() as session:
                status = await _collection_status(session, due)
                at = clock()
                if status in {"PAID_FROM_CREDIT", "GRACE_STARTED"}:
                    continue
                if status == "ORDER_CREATED":
                    if due["end"] <= at:
                        await start_grace_once(
                            session, due["tenant"], due["relationship"], now=clock, lifecycle_factory=lifecycle_factory
                        )
                        await _record(session, due, "GRACE_STARTED", None, 0, at)
                        await session.commit()
                        grace += 1
                    continue
                customer_id = await payer_of(session, due["tenant"], due["relationship"])
                if customer_id is None:
                    continue
                lifecycle = lifecycle_factory(session, clock)
                try:
                    quote = await lifecycle.renewal_quote(due["tenant"], due["relationship"])
                except LifecycleError:
                    continue
                if quote.amount_due_paise == 0:
                    await lifecycle.renew_from_credit(due["tenant"], due["relationship"], customer_id, authority=authority)
                    await _record(session, due, "PAID_FROM_CREDIT", None, 0, at)
                    await session.commit()
                    from_credit += 1
                    continue
                order = await client.create_order(
                    quote.amount_due_paise,
                    {
                        "checkout_kind": RENEWAL,
                        "customer_id": str(customer_id),
                        "tenant_id": str(due["tenant"]),
                        "relationship_id": str(due["relationship"]),
                    },
                )
                await _record(session, due, "ORDER_CREATED", str(order["id"]), quote.amount_due_paise, at)
                await session.commit()
                ordered += 1
        except Exception:
            logger.exception("renewal_sweep failed relationship=%s", due["relationship"])
    logger.info("renewal_sweep ordered=%s from_credit=%s grace_started=%s", ordered, from_credit, grace)
    return RenewalSweepReport(ordered, from_credit, grace)
