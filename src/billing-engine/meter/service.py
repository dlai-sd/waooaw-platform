# Implements: <spec-path> §<section>
# Constitutional basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skeleton.wbe_interfaces import (
    AlertFired,
    DailyScanResult,
    DepletionProjection,
    IMeterService,
)
from meter.alert_policy import (
    AGENCY_POLICY,
    CUSTOMER_BUCKET_POLICY,
    PROCUREMENT_POLICY,
    AlertAction,
    ThresholdPolicy,
)

logger = logging.getLogger(__name__)

_IST_OFFSET = timedelta(hours=5, minutes=30)


def _now_ist() -> datetime:
    """Return current time in IST (UTC+5:30)."""
    return datetime.now(timezone.utc).astimezone(
        timezone(_IST_OFFSET)
    )


def _current_billing_period_start(now_utc: datetime) -> date:
    """Returns the first day of the current calendar month (UTC)."""
    return now_utc.date().replace(day=1)


def _is_quiet_hours(policy: ThresholdPolicy, now_ist: datetime) -> bool:
    """Check if current IST time falls within policy quiet hours."""
    hour = now_ist.hour
    start = policy.quiet_hours_start_ist
    end = policy.quiet_hours_end_ist
    # quiet window wraps midnight: e.g. 23 → 6
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


class MeterService(IMeterService):
    """
    Usage Meter + Alert Engine.

    Constitutional: C-043 (budget ceiling), C-049 (honest limitation),
    C-051 (resource transparency), C-059 (traceability), C-063 (no PII in logs).
    SLA: record_usage ≤100ms p99.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_pool: asyncpg.Pool | None = None,
    ) -> None:
        """Initialize MeterService with database session factory and optional Redis pool."""
        self._session_factory = session_factory
        self._redis_pool = redis_pool  # reserved for ADR-034 cache integration

    # ------------------------------------------------------------------
    # IMeterService.record_usage
    # ------------------------------------------------------------------
    async def record_usage(
        self, customer_id: UUID, thread_type: str, amount_paise: int
    ) -> None:
        """
        Record one usage event.

        Steps:
        1. Resolve provider_account_id via thread_catalog → provider_accounts.
        2. Write to platform_cost_ledger with marked_up_cost_inr_paise.
        C-063: customer_id logged only as UUID string (no name/email).
        """
        try:
            async with self._session_factory() as session:
                # 1. Resolve provider_account_id
                row = await session.execute(
                    text(
                        """
                        SELECT pa.id AS provider_account_id
                        FROM   thread_catalog tc
                        JOIN   provider_accounts pa
                               ON pa.id = tc.provider_account_id
                        WHERE  tc.thread_type = :thread_type
                        LIMIT  1
                        """
                    ).bindparams(thread_type=thread_type)
                )
                result_row = row.fetchone()
                if result_row is None:
                    logger.error(
                        "provider_account not found for thread_type=%s — usage not recorded",
                        thread_type,
                    )
                    return

                provider_account_id: UUID = result_row.provider_account_id

                # 2. Write to platform_cost_ledger
                now_utc = datetime.now(timezone.utc)
                await session.execute(
                    text(
                        """
                        INSERT INTO platform_cost_ledger
                            (id, customer_id, thread_type, provider_account_id,
                             marked_up_cost_inr_paise, recorded_at, billing_period_start)
                        VALUES
                            (:id, :customer_id, :thread_type, :provider_account_id,
                             :amount_paise, :recorded_at, :billing_period_start)
                        """
                    ).bindparams(
                        id=uuid4(),
                        customer_id=customer_id,
                        thread_type=thread_type,
                        provider_account_id=provider_account_id,
                        amount_paise=amount_paise,
                        recorded_at=now_utc,
                        billing_period_start=_current_billing_period_start(now_utc),
                    )
                )
                await session.commit()
                logger.info(
                    "record_usage committed customer=%s thread_type=%s paise=%d",
                    customer_id,
                    thread_type,
                    amount_paise,
                )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "record_usage failed customer=%s thread_type=%s",
                customer_id,
                thread_type,
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    # IMeterService.project_depletion
    # ------------------------------------------------------------------
    async def project_depletion(
        self, customer_id: UUID, thread_type: str
    ) -> DepletionProjection:
        """
        7-day rolling average burn rate → days_remaining + projected_empty_date.

        Reads platform_cost_ledger + wallet_buckets.balance_paise.
        C-051: transparent resource projection.
        """
        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                window_start = now_utc - timedelta(days=7)

                # 7d total spend for this customer+thread_type
                spend_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS total_spent
                        FROM   platform_cost_ledger
                        WHERE  customer_id = :customer_id
                               AND thread_type = :thread_type
                               AND recorded_at >= :window_start
                        """
                    ).bindparams(
                        customer_id=customer_id,
                        thread_type=thread_type,
                        window_start=window_start,
                    )
                )
                spend_result = spend_row.fetchone()
                total_spent_7d = spend_result.total_spent if spend_result else 0

                # Current bucket balance
                balance_row = await session.execute(
                    text(
                        """
                        SELECT balance_paise
                        FROM   wallet_buckets
                        WHERE  customer_id = :customer_id
                               AND thread_type = :thread_type
                        """
                    ).bindparams(customer_id=customer_id, thread_type=thread_type)
                )
                balance_result = balance_row.fetchone()
                balance_paise = balance_result.balance_paise if balance_result else 0

                # Daily burn rate
                daily_burn = total_spent_7d / 7.0 if total_spent_7d > 0 else 0.0
                days_remaining = (
                    balance_paise / daily_burn if daily_burn > 0 else float("inf")
                )
                projected_empty_date = (
                    (now_utc + timedelta(days=days_remaining)).date()
                    if daily_burn > 0
                    else date.max
                )

                return DepletionProjection(
                    days_remaining=days_remaining,
                    projected_empty_date=projected_empty_date,
                    daily_burn_rate_paise=daily_burn,
                )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "project_depletion failed customer=%s thread_type=%s",
                customer_id,
                thread_type,
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    # IMeterService.run_daily_scan
    # ------------------------------------------------------------------
    async def run_daily_scan(self) -> DailyScanResult:
        """
        Daily scan at 06:00 IST: fetch all active customers, call check_thresholds,
        fire alerts per policy, and return summary.
        """
        try:
            async with self._session_factory() as session:
                # Fetch all active customers
                customers_row = await session.execute(
                    text(
                        """
                        SELECT DISTINCT customer_id
                        FROM   billing_profiles
                        WHERE  status = 'FOUNDER_AUTHORIZED'
                        """
                    )
                )
                customer_ids = [row.customer_id for row in customers_row.fetchall()]

                alerts_sent = 0
                for customer_id in customer_ids:
                    alerts = await self.check_thresholds(customer_id)
                    alerts_sent += len(alerts)

                return DailyScanResult(
                    customers_scanned=len(customer_ids),
                    alerts_sent=alerts_sent,
                    offers_generated=0,  # Reserved for future: WC-029
                    fa_items_created=0,  # Reserved for future: WC-029
                )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "run_daily_scan failed",
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    # MeterService.check_thresholds (concrete helper, NOT in IMeterService)
    # ------------------------------------------------------------------
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
        """
        Check customer against CUSTOMER_BUCKET_POLICY, AGENCY_POLICY, PROCUREMENT_POLICY.

        Scope 1 (CUSTOMER_BUCKET): per thread_type bucket.
        Scope 2 (AGENCY): agency-wide sub-wallet.
        Scope 3 (PROCUREMENT): WAOOAW procurement runway.

        Returns: list of AlertFired records that were actually sent (deduplicated).

        Computes:
          pct_consumed = SUM(platform_cost_ledger.marked_up_cost_inr_paise
                        WHERE customer_id + current billing_period)
                         / (SUM + wallet_buckets.balance_paise)

        Deduplicates via meter_alert_log (no double-fire within 24h per alert name).
        Respects quiet_hours and bypass_quiet_hours flag.
        """
        alerts_fired: list[AlertFired] = []
        now_utc = datetime.now(timezone.utc)
        now_ist = _now_ist()

        try:
            async with self._session_factory() as session:
                # --- SCOPE 1: CUSTOMER_BUCKET_POLICY ---
                bucket_row = await session.execute(
                    text(
                        """
                        SELECT thread_type, balance_paise
                        FROM   wallet_buckets
                        WHERE  customer_id = :customer_id
                        """
                    ).bindparams(customer_id=customer_id)
                )
                buckets = bucket_row.fetchall()

                for bucket in buckets:
                    thread_type = bucket.thread_type
                    balance_paise = bucket.balance_paise

                    # Spend in current billing period
                    spend_row = await session.execute(
                        text(
                            """
                            SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS spent
                            FROM   platform_cost_ledger
                            WHERE  customer_id = :customer_id
                                   AND thread_type = :thread_type
                                   AND billing_period_start = :period_start
                            """
                        ).bindparams(
                            customer_id=customer_id,
                            thread_type=thread_type,
                            period_start=_current_billing_period_start(now_utc),
                        )
                    )
                    spend_result = spend_row.fetchone()
                    spent = spend_result.spent if spend_result else 0

                    # pct_consumed = spent / (spent + balance)
                    denominator = spent + balance_paise
                    pct_consumed = (
                        (spent / denominator) if denominator > 0 else 0.0
                    )

                    # Check CUSTOMER_BUCKET_POLICY thresholds
                    for rule in CUSTOMER_BUCKET_POLICY.thresholds:
                        if pct_consumed >= rule.consumed_pct_trigger:
                            # Check deduplication window (24h)
                            dup_row = await session.execute(
                                text(
                                    """
                                    SELECT id FROM meter_alert_log
                                    WHERE  customer_id = :customer_id
                                           AND bucket_type = :bucket_type
                                           AND threshold_name = :threshold_name
                                           AND fired_at > :cutoff
                                    LIMIT  1
                                    """
                                ).bindparams(
                                    customer_id=customer_id,
                                    bucket_type=thread_type,
                                    threshold_name=rule.name,
                                    cutoff=now_utc - timedelta(hours=24),
                                )
                            )
                            if dup_row.fetchone() is None:
                                # Not in deduplication window → fire
                                # Check quiet hours (unless bypass_quiet_hours set)
                                should_notify = (
                                    rule.bypass_quiet_hours
                                    or not _is_quiet_hours(
                                        CUSTOMER_BUCKET_POLICY, now_ist
                                    )
                                )

                                if should_notify and rule.action in (
                                    AlertAction.NOTIFY,
                                    AlertAction.FA,
                                ):
                                    alert = AlertFired(
                                        customer_id=customer_id,
                                        bucket_type=thread_type,
                                        threshold_name=rule.name,
                                        pct_consumed=pct_consumed,
                                        scope="CUSTOMER_BUCKET",
                                        fired_at=now_utc,
                                    )
                                    alerts_fired.append(alert)

                                    # Log to meter_alert_log
                                    await session.execute(
                                        text(
                                            """
                                            INSERT INTO meter_alert_log
                                                (id, customer_id, bucket_type,
                                                 threshold_name, pct_consumed, scope, fired_at)
                                            VALUES
                                                (:id, :customer_id, :bucket_type,
                                                 :threshold_name, :pct_consumed, :scope, :fired_at)
                                            """
                                        ).bindparams(
                                            id=uuid4(),
                                            customer_id=customer_id,
                                            bucket_type=thread_type,
                                            threshold_name=rule.name,
                                            pct_consumed=pct_consumed,
                                            scope="CUSTOMER_BUCKET",
                                            fired_at=now_utc,
                                        )
                                    )

                # --- SCOPE 2: AGENCY_POLICY (stub for future WC-029) ---
                # TODO WC-029: agency sub-wallet aggregation
                agency_balance_paise = 0
                agency_spent_paise = 0
                if agency_balance_paise + agency_spent_paise > 0:
                    pct_consumed_agency = agency_spent_paise / (
                        agency_spent_paise + agency_balance_paise
                    )
                    for rule in AGENCY_POLICY.thresholds:
                        if pct_consumed_agency >= rule.consumed_pct_trigger:
                            dup_row = await session.execute(
                                text(
                                    """
                                    SELECT id FROM meter_alert_log
                                    WHERE  customer_id = :customer_id
                                           AND bucket_type = 'AGENCY'
                                           AND threshold_name = :threshold_name
                                           AND fired_at > :cutoff
                                    LIMIT  1
                                    """
                                ).bindparams(
                                    customer_id=customer_id,
                                    threshold_name=rule.name,
                                    cutoff=now_utc - timedelta(hours=24),
                                )
                            )
                            if dup_row.fetchone() is None:
                                should_notify = (
                                    rule.bypass_quiet_hours
                                    or not _is_quiet_hours(AGENCY_POLICY, now_ist)
                                )
                                if should_notify and rule.action in (
                                    AlertAction.NOTIFY,
                                    AlertAction.FA,
                                ):
                                    alert = AlertFired(
                                        customer_id=customer_id,
                                        bucket_type="AGENCY",
                                        threshold_name=rule.name,
                                        pct_consumed=pct_consumed_agency,
                                        scope="AGENCY",
                                        fired_at=now_utc,
                                    )
                                    alerts_fired.append(alert)
                                    await session.execute(
                                        text(
                                            """
                                            INSERT INTO meter_alert_log
                                                (id, customer_id, bucket_type,
                                                 threshold_name, pct_consumed, scope, fired_at)
                                            VALUES
                                                (:id, :customer_id, :bucket_type,
                                                 :threshold_name, :pct_consumed, :scope, :fired_at)
                                            """
                                        ).bindparams(
                                            id=uuid4(),
                                            customer_id=customer_id,
                                            bucket_type="AGENCY",
                                            threshold_name=rule.name,
                                            pct_consumed=pct_consumed_agency,
                                            scope="AGENCY",
                                            fired_at=now_utc,
                                        )
                                    )

                # --- SCOPE 3: PROCUREMENT_POLICY (stub for future WC-029) ---
                # TODO WC-029: provider runway aggregation
                runway_balance_paise = 0
                runway_daily_burn_paise = 0.0
                if runway_balance_paise > 0 and runway_daily_burn_paise > 0:
                    days_remaining = runway_balance_paise / runway_daily_burn_paise
                    # Map days_remaining to threshold levels
                    for rule in PROCUREMENT_POLICY.thresholds:
                        # RUNWAY_P2: ≤30d, RUNWAY_P1: ≤14d, RUNWAY_P0: ≤7d, RUNWAY_CRITICAL: ≤3d, RUNWAY_EMERGENCY: ≤1d
                        threshold_days = {
                            "RUNWAY_P2": 30,
                            "RUNWAY_P1": 14,
                            "RUNWAY_P0": 7,
                            "RUNWAY_CRITICAL": 3,
                            "RUNWAY_EMERGENCY": 1,
                        }.get(rule.name, float("inf"))

                        if days_remaining <= threshold_days:
                            dup_row = await session.execute(
                                text(
                                    """
                                    SELECT id FROM meter_alert_log
                                    WHERE  customer_id = :customer_id
                                           AND bucket_type = 'PROCUREMENT'
                                           AND threshold_name = :threshold_name
                                           AND fired_at > :cutoff
                                    LIMIT  1
                                    """
                                ).bindparams(
                                    customer_id=customer_id,
                                    threshold_name=rule.name,
                                    cutoff=now_utc - timedelta(hours=24),
                                )
                            )
                            if dup_row.fetchone() is None:
                                should_notify = (
                                    rule.bypass_quiet_hours
                                    or not _is_quiet_hours(
                                        PROCUREMENT_POLICY, now_ist
                                    )
                                )
                                if should_notify and rule.action in (
                                    AlertAction.NOTIFY,
                                    AlertAction.FA,
                                ):
                                    alert = AlertFired(
                                        customer_id=customer_id,
                                        bucket_type="PROCUREMENT",
                                        threshold_name=rule.name,
                                        pct_consumed=1.0 - (days_remaining / 30),
                                        scope="PROCUREMENT",
                                        fired_at=now_utc,
                                    )
                                    alerts_fired.append(alert)
                                    await session.execute(
                                        text(
                                            """
                                            INSERT INTO meter_alert_log
                                                (id, customer_id, bucket_type,
                                                 threshold_name, pct_consumed, scope, fired_at)
                                            VALUES
                                                (:id, :customer_id, :bucket_type,
                                                 :threshold_name, :pct_consumed, :scope, :fired_at)
                                            """
                                        ).bindparams(
                                            id=uuid4(),
                                            customer_id=customer_id,
                                            bucket_type="PROCUREMENT",
                                            threshold_name=rule.name,
                                            pct_consumed=1.0 - (days_remaining / 30),
                                            scope="PROCUREMENT",
                                            fired_at=now_utc,
                                        )
                                    )

                await session.commit()
                return alerts_fired

        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "check_thresholds failed customer=%s",
                customer_id,
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise