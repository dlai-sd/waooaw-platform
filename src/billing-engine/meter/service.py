# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
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
_IST_TZ = timezone(_IST_OFFSET)
_DEDUP_WINDOW_HOURS = 24
_ROLLING_DAYS = 7


def _now_ist() -> datetime:
    """Return current time in IST (UTC+5:30)."""
    return datetime.now(timezone.utc).astimezone(_IST_TZ)


def _current_billing_period_start(now_utc: datetime) -> date:
    """Returns the first day of the current calendar month (UTC)."""
    return now_utc.date().replace(day=1)


def _is_quiet_hours(policy: ThresholdPolicy, now_ist: datetime) -> bool:
    """Check if current IST time falls within policy quiet hours."""
    hour = now_ist.hour
    start = policy.quiet_hours_start_ist
    end = policy.quiet_hours_end_ist
    # quiet window wraps midnight: e.g. 23 -> 6
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


class MeterService(IMeterService):
    """
    Usage Meter + Alert Engine.

    Constitutional: C-043 (budget ceiling), C-049 (honest limitation),
    C-051 (resource transparency), C-059 (traceability), C-063 (no PII in logs).
    SLA: record_usage <=100ms p99.
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
        1. Resolve provider_account_id via thread_catalog -> provider_accounts.
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
                        "provider_account not found for thread_type=%s -- usage not recorded",
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
        except (ValueError, RuntimeError, OSError) as exc:
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
        7-day rolling average burn rate -> days_remaining + projected_empty_date.

        Reads platform_cost_ledger (last 7 days) + wallet_buckets.balance_paise.
        C-051: transparent projection based on observed burn rate.
        """
        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                seven_days_ago = now_utc - timedelta(days=_ROLLING_DAYS)

                # 1. Sum cost over last 7 days
                cost_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) as total_cost
                        FROM   platform_cost_ledger
                        WHERE  customer_id = :customer_id
                               AND thread_type = :thread_type
                               AND recorded_at >= :seven_days_ago
                        """
                    ).bindparams(
                        customer_id=customer_id,
                        thread_type=thread_type,
                        seven_days_ago=seven_days_ago,
                    )
                )
                cost_result = cost_row.fetchone()
                total_cost_7d = cost_result.total_cost if cost_result else 0

                # 2. Get current bucket balance
                balance_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(balance_paise, 0) as balance
                        FROM   wallet_buckets
                        WHERE  customer_id = :customer_id
                               AND thread_type = :thread_type
                        LIMIT  1
                        """
                    ).bindparams(customer_id=customer_id, thread_type=thread_type)
                )
                balance_result = balance_row.fetchone()
                current_balance = balance_result.balance if balance_result else 0

                # 3. Calculate daily burn rate
                daily_burn_rate = total_cost_7d / _ROLLING_DAYS

                # 4. Project days remaining
                if daily_burn_rate <= 0:
                    # No burn observed; assume >999 days remaining
                    days_remaining = 999.0
                    projected_empty = now_utc.date() + timedelta(days=999)
                else:
                    days_remaining = current_balance / daily_burn_rate
                    projected_empty = now_utc.date() + timedelta(days=days_remaining)

                logger.info(
                    "project_depletion customer=%s thread_type=%s days_remaining=%.1f daily_burn_rate=%d",
                    customer_id,
                    thread_type,
                    days_remaining,
                    int(daily_burn_rate),
                )

                return DepletionProjection(
                    days_remaining=days_remaining,
                    projected_empty_date=projected_empty,
                    daily_burn_rate_paise=float(daily_burn_rate),
                )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
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
        Daily scan: 06:00 IST triggers for all active customers.
        Calls check_thresholds per customer, fires alerts, deduplicates.
        """
        try:
            customers_scanned = 0
            alerts_sent = 0
            offers_generated = 0
            fa_items_created = 0

            async with self._session_factory() as session:
                # Fetch all active customers (billing_profiles.status = 'ACTIVE')
                customer_rows = await session.execute(
                    text(
                        """
                        SELECT DISTINCT customer_id
                        FROM   billing_profiles
                        WHERE  status = 'ACTIVE'
                        """
                    )
                )

                customer_ids = [row.customer_id for row in customer_rows]
                customers_scanned = len(customer_ids)

                # For each customer, run check_thresholds
                for cust_id in customer_ids:
                    try:
                        fired_alerts = await self.check_thresholds(cust_id)
                        alerts_sent += len(fired_alerts)
                        logger.info(
                            "run_daily_scan checked customer=%s alerts=%d",
                            cust_id,
                            len(fired_alerts),
                        )
                    except asyncio.CancelledError:
                        raise
                    except (ValueError, RuntimeError, OSError) as exc:
                        logger.error(
                            "check_thresholds failed customer=%s",
                            cust_id,
                            exc_info=True,
                            extra={"context": str(exc)},
                        )
                        # Continue scanning other customers

            logger.info(
                "run_daily_scan completed customers_scanned=%d alerts_sent=%d",
                customers_scanned,
                alerts_sent,
            )

            return DailyScanResult(
                customers_scanned=customers_scanned,
                alerts_sent=alerts_sent,
                offers_generated=offers_generated,
                fa_items_created=fa_items_created,
            )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "run_daily_scan failed",
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    # MeterService.check_thresholds (concrete helper, NOT abstract)
    # ------------------------------------------------------------------
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
        """
        Check thresholds for one customer across 3 scopes:
        - Scope 1: CUSTOMER_BUCKET (per thread_type)
        - Scope 2: AGENCY (agency sub-wallet)
        - Scope 3: PROCUREMENT (provider runway)

        Computes pct_consumed = SUM(platform_cost_ledger.marked_up_cost_inr_paise WHERE
        customer_id + current billing_period) / (consumed + wallet_buckets.balance_paise).

        Fires per §2.3a scope 1+2+3 ladder. Deduplicates via meter_alert_log.
        C-043: budget ceiling enforcement with threshold ladder.
        """
        alerts: list[AlertFired] = []

        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                now_ist = now_utc.astimezone(_IST_TZ)
                billing_period_start = _current_billing_period_start(now_utc)

                # ============================================================
                # SCOPE 1: CUSTOMER_BUCKET (per thread_type)
                # ============================================================
                bucket_rows = await session.execute(
                    text(
                        """
                        SELECT thread_type, balance_paise
                        FROM   wallet_buckets
                        WHERE  customer_id = :customer_id
                        """
                    ).bindparams(customer_id=customer_id)
                )

                for bucket_row in bucket_rows:
                    thread_type = bucket_row.thread_type
                    balance = bucket_row.balance_paise

                    # Get consumed amount from platform_cost_ledger for this period
                    cost_row = await session.execute(
                        text(
                            """
                            SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) as total_cost
                            FROM   platform_cost_ledger
                            WHERE  customer_id = :customer_id
                                   AND thread_type = :thread_type
                                   AND billing_period_start = :billing_period_start
                            """
                        ).bindparams(
                            customer_id=customer_id,
                            thread_type=thread_type,
                            billing_period_start=billing_period_start,
                        )
                    )
                    cost_result = cost_row.fetchone()
                    consumed = cost_result.total_cost if cost_result else 0

                    # Compute pct_consumed
                    total_budget = consumed + balance
                    if total_budget > 0:
                        pct_consumed = consumed / total_budget
                    else:
                        pct_consumed = 0.0

                    # Check thresholds for CUSTOMER_BUCKET scope
                    fired = await self._check_scope_thresholds(
                        session,
                        customer_id=customer_id,
                        bucket_type=thread_type,
                        pct_consumed=pct_consumed,
                        policy=CUSTOMER_BUCKET_POLICY,
                        scope="CUSTOMER_BUCKET",
                        now_ist=now_ist,
                        billing_period_start=billing_period_start,
                    )
                    alerts.extend(fired)

                # ============================================================
                # SCOPE 2: AGENCY (agency sub-wallet)
                # ============================================================
                agency_cost_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) as total_cost
                        FROM   platform_cost_ledger
                        WHERE  customer_id = :customer_id
                               AND billing_period_start = :billing_period_start
                        """
                    ).bindparams(
                        customer_id=customer_id,
                        billing_period_start=billing_period_start,
                    )
                )
                agency_cost_result = agency_cost_row.fetchone()
                agency_consumed = agency_cost_result.total_cost if agency_cost_result else 0

                # Get agency balance (sum of all buckets)
                agency_balance_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(balance_paise), 0) as total_balance
                        FROM   wallet_buckets
                        WHERE  customer_id = :customer_id
                        """
                    ).bindparams(customer_id=customer_id)
                )
                agency_balance_result = agency_balance_row.fetchone()
                agency_balance = (
                    agency_balance_result.total_balance if agency_balance_result else 0
                )

                agency_total = agency_consumed + agency_balance
                if agency_total > 0:
                    agency_pct_consumed = agency_consumed / agency_total
                else:
                    agency_pct_consumed = 0.0

                fired_agency = await self._check_scope_thresholds(
                    session,
                    customer_id=customer_id,
                    bucket_type="AGENCY",
                    pct_consumed=agency_pct_consumed,
                    policy=AGENCY_POLICY,
                    scope="AGENCY",
                    now_ist=now_ist,
                    billing_period_start=billing_period_start,
                )
                alerts.extend(fired_agency)

                # ============================================================
                # SCOPE 3: PROCUREMENT (provider runway)
                # ============================================================
                fired_procurement = await self._check_scope_thresholds(
                    session,
                    customer_id=customer_id,
                    bucket_type="PROCUREMENT",
                    pct_consumed=0.0,  # Not used for procurement; use projection
                    policy=PROCUREMENT_POLICY,
                    scope="PROCUREMENT",
                    now_ist=now_ist,
                    billing_period_start=billing_period_start,
                )
                alerts.extend(fired_procurement)

                logger.info(
                    "check_thresholds completed customer=%s total_alerts=%d",
                    customer_id,
                    len(alerts),
                )

                return alerts

        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "check_thresholds failed customer=%s",
                customer_id,
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    # Helper: _check_scope_thresholds
    # ------------------------------------------------------------------
    async def _check_scope_thresholds(
        self,
        session: AsyncSession,
        customer_id: UUID,
        bucket_type: str,
        pct_consumed: float,
        policy: ThresholdPolicy,
        scope: str,
        now_ist: datetime,
        billing_period_start: date,
    ) -> list[AlertFired]:
        """
        Helper to check thresholds for a single scope.
        Respects quiet_hours and deduplicates via meter_alert_log.
        """
        alerts: list[AlertFired] = []

        try:
            # Check if in quiet hours
            in_quiet = _is_quiet_hours(policy, now_ist)

            # Iterate over threshold rules in policy
            for rule in policy.thresholds:
                # If pct_consumed >= trigger threshold, fire alert
                if pct_consumed >= rule.consumed_pct_trigger:
                    # Check if already fired within dedup window
                    dedup_row = await session.execute(
                        text(
                            """
                            SELECT id FROM meter_alert_log
                            WHERE  customer_id = :customer_id
                                   AND bucket_type = :bucket_type
                                   AND threshold_name = :threshold_name
                                   AND scope = :scope
                                   AND fired_at >= :dedup_cutoff
                            LIMIT  1
                            """
                        ).bindparams(
                            customer_id=customer_id,
                            bucket_type=bucket_type,
                            threshold_name=rule.name,
                            scope=scope,
                            dedup_cutoff=now_ist - timedelta(hours=_DEDUP_WINDOW_HOURS),
                        )
                    )
                    dedup_result = dedup_row.fetchone()

                    if dedup_result is None:
                        # Not deduplicated; fire alert
                        alert = AlertFired(
                            customer_id=customer_id,
                            bucket_type=bucket_type,
                            threshold_name=rule.name,
                            pct_consumed=pct_consumed,
                            scope=scope,
                            fired_at=now_ist,
                        )

                        # Log to meter_alert_log
                        await session.execute(
                            text(
                                """
                                INSERT INTO meter_alert_log
                                    (id, customer_id, bucket_type, threshold_name, scope,
                                     pct_consumed, fired_at, action)
                                VALUES
                                    (:id, :customer_id, :bucket_type, :threshold_name, :scope,
                                     :pct_consumed, :fired_at, :action)
                                """
                            ).bindparams(
                                id=uuid4(),
                                customer_id=customer_id,
                                bucket_type=bucket_type,
                                threshold_name=rule.name,
                                scope=scope,
                                pct_consumed=pct_consumed,
                                fired_at=now_ist,
                                action=rule.action.value,
                            )
                        )
                        await session.commit()

                        # Respect quiet hours + bypass_quiet_hours flag
                        should_notify = (not in_quiet) or rule.bypass_quiet_hours

                        if should_notify and rule.action in (
                            AlertAction.NOTIFY,
                            AlertAction.FA,
                            AlertAction.BLOCK,
                        ):
                            logger.info(
                                "alert fired customer=%s threshold=%s scope=%s action=%s pct=%.1f",
                                customer_id,
                                rule.name,
                                scope,
                                rule.action.value,
                                pct_consumed * 100,
                            )

                        alerts.append(alert)
                    # else: already logged recently, skip

            return alerts

        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "_check_scope_thresholds failed customer=%s scope=%s",
                customer_id,
                scope,
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise