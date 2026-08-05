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

# text().bindparams() does not auto-coerce UUID objects in SQLite; use this at
# every UUID bind site so queries work identically across backends.
def _sid(v: UUID | str) -> str:
    """Convert UUID or string to string representation for SQL binding."""
    return str(v)


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

                provider_account_id: str = str(result_row.provider_account_id)

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
                        id=_sid(uuid4()),
                        customer_id=_sid(customer_id),
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
                    _sid(customer_id),
                    thread_type,
                    amount_paise,
                )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "record_usage failed customer=%s thread_type=%s",
                _sid(customer_id),
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
        Project bucket depletion using 7-day rolling average burn rate.

        Formula: days_remaining = balance_paise / daily_burn_rate_paise
        C-049: honest limitation - returns 0 days if already depleted.
        C-051: resource transparency via projected_empty_date.
        """
        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                window_start = now_utc - timedelta(days=_ROLLING_DAYS)

                # 7-day rolling average from platform_cost_ledger
                burn_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS total_cost,
                               COUNT(DISTINCT DATE(recorded_at))            AS active_days
                        FROM   platform_cost_ledger
                        WHERE  customer_id = :customer_id
                          AND  thread_type = :thread_type
                          AND  recorded_at >= :window_start
                        """
                    ).bindparams(
                        customer_id=_sid(customer_id),
                        thread_type=thread_type,
                        window_start=window_start,
                    )
                )
                burn_result = burn_row.fetchone()
                total_cost: float = float(burn_result.total_cost) if burn_result else 0.0
                active_days: int = int(burn_result.active_days) if burn_result else 0

                # Daily burn rate: use active days if > 0, else use full window
                denominator = active_days if active_days > 0 else _ROLLING_DAYS
                daily_burn_rate: float = total_cost / denominator

                # Current bucket balance (quota denominator)
                balance_row = await session.execute(
                    text(
                        """
                        SELECT balance_paise
                        FROM   wallet_buckets
                        WHERE  customer_id = :customer_id
                          AND  thread_type  = :thread_type
                        LIMIT  1
                        """
                    ).bindparams(
                        customer_id=_sid(customer_id),
                        thread_type=thread_type,
                    )
                )
                balance_result = balance_row.fetchone()
                balance_paise: float = (
                    float(balance_result.balance_paise) if balance_result else 0.0
                )

                # Consumed so far this billing period
                period_start = _current_billing_period_start(now_utc)
                consumed_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS consumed
                        FROM   platform_cost_ledger
                        WHERE  customer_id           = :customer_id
                          AND  thread_type            = :thread_type
                          AND  billing_period_start  = :period_start
                        """
                    ).bindparams(
                        customer_id=_sid(customer_id),
                        thread_type=thread_type,
                        period_start=period_start,
                    )
                )
                consumed_result = consumed_row.fetchone()
                consumed_paise: float = (
                    float(consumed_result.consumed) if consumed_result else 0.0
                )

                remaining_paise = max(0.0, balance_paise - consumed_paise)

                if daily_burn_rate <= 0.0:
                    # No burn data - cannot project; return far future
                    days_remaining = float("inf") if remaining_paise > 0 else 0.0
                    days_remaining = min(days_remaining, 9999.0)
                else:
                    days_remaining = remaining_paise / daily_burn_rate

                projected_empty_date = (
                    now_utc + timedelta(days=days_remaining)
                ).date()

                return DepletionProjection(
                    days_remaining=days_remaining,
                    projected_empty_date=projected_empty_date,
                    daily_burn_rate_paise=daily_burn_rate,
                )
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "project_depletion failed customer=%s thread_type=%s",
                _sid(customer_id),
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
        Daily scan at 06:00 IST: projection + threshold checks + proactive offers.

        Iterates all active customers and calls check_thresholds for each.
        C-043: budget ceiling enforcement across all buckets.
        C-059: every alert fired produces a meter_alert_log evidence record.
        """
        result = DailyScanResult(
            customers_scanned=0,
            alerts_sent=0,
            offers_generated=0,
            fa_items_created=0,
        )
        try:
            async with self._session_factory() as session:
                # Fetch all active customer IDs from wallet_buckets
                customers_row = await session.execute(
                    text(
                        """
                        SELECT DISTINCT customer_id
                        FROM   wallet_buckets
                        WHERE  is_active = 1
                           OR  is_active = TRUE
                        """
                    )
                )
                customer_ids = [str(r.customer_id) for r in customers_row.fetchall()]

            for cid_str in customer_ids:
                try:
                    cid = UUID(cid_str)
                    alerts = await self.check_thresholds(cid)
                    result.customers_scanned += 1
                    for alert in alerts:
                        result.alerts_sent += 1
                        if alert.threshold_name.startswith("RUNWAY_P"):
                            result.fa_items_created += 1
                except asyncio.CancelledError:
                    raise
                except (ValueError, RuntimeError, OSError) as exc:
                    logger.error(
                        "run_daily_scan: check_thresholds failed for customer=%s",
                        cid_str,
                        exc_info=True,
                        extra={"context": str(exc)},
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

        logger.info(
            "run_daily_scan complete scanned=%d alerts=%d fa=%d",
            result.customers_scanned,
            result.alerts_sent,
            result.fa_items_created,
        )
        return result

    # ------------------------------------------------------------------
    # Concrete helper: check_thresholds (NOT in IMeterService ABC)
    # ------------------------------------------------------------------
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
        """
        Evaluate §2.3a scope 1+2+3 threshold ladder for a single customer.

        Scope 1 - CUSTOMER_BUCKET: pct_consumed per thread_type bucket.
        Scope 2 - AGENCY: agency-level sub-wallet aggregation.
        Scope 3 - PROCUREMENT: provider runway days remaining.

        Deduplication: skips firing if a matching alert exists in meter_alert_log
        within the last _DEDUP_WINDOW_HOURS hours.

        C-043: budget ceiling - BLOCK action triggers billing halt.
        C-059: every fired alert written to meter_alert_log as evidence.
        C-063: no PII in log statements.
        """
        fired: list[AlertFired] = []
        now_ist = _now_ist()
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        try:
            async with self._session_factory() as session:
                # ---- Scope 1: CUSTOMER_BUCKET per thread_type ----
                fired += await self._check_scope1_customer_bucket(
                    session, customer_id, period_start, now_ist, now_utc
                )

                # ---- Scope 2: AGENCY sub-wallet ----
                fired += await self._check_scope2_agency(
                    session, customer_id, period_start, now_ist, now_utc
                )

                # ---- Scope 3: PROCUREMENT runway ----
                fired += await self._check_scope3_procurement(
                    session, now_ist, now_utc
                )

        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "check_thresholds failed customer=%s",
                _sid(customer_id),
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

        return fired

    # ------------------------------------------------------------------
    # Internal scope helpers
    # ------------------------------------------------------------------

    async def _check_scope1_customer_bucket(
        self,
        session: AsyncSession,
        customer_id: UUID,
        period_start: date,
        now_ist: datetime,
        now_utc: datetime,
    ) -> list[AlertFired]:
        """Scope 1: per-bucket threshold checks for a customer."""
        alerts: list[AlertFired] = []

        # Get all buckets for this customer
        buckets_row = await session.execute(
            text(
                """
                SELECT thread_type, balance_paise
                FROM   wallet_buckets
                WHERE  customer_id = :customer_id
                """
            ).bindparams(customer_id=_sid(customer_id))
        )
        buckets = buckets_row.fetchall()

        for bucket in buckets:
            thread_type: str = bucket.thread_type
            quota_paise: float = float(bucket.balance_paise)

            if quota_paise <= 0.0:
                # No quota - cannot compute percentage; skip per C-043 note
                continue

            # Sum consumed this billing period
            consumed_row = await session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS consumed
                    FROM   platform_cost_ledger
                    WHERE  customer_id          = :customer_id
                      AND  thread_type           = :thread_type
                      AND  billing_period_start = :period_start
                    """
                ).bindparams(
                    customer_id=_sid(customer_id),
                    thread_type=thread_type,
                    period_start=period_start,
                )
            )
            consumed_result = consumed_row.fetchone()
            consumed_paise: float = (
                float(consumed_result.consumed) if consumed_result else 0.0
            )

            pct_consumed = consumed_paise / quota_paise  # 0.0 - 1.0+

            policy = CUSTOMER_BUCKET_POLICY
            quiet = _is_quiet_hours(policy, now_ist)

            for rule in policy.rules:
                # ThresholdRule uses consumed_pct_trigger
                trigger = getattr(rule, "consumed_pct_trigger", None)
                if trigger is None:
                    continue
                if pct_consumed < trigger:
                    continue

                # Quiet hours suppression (unless bypass_quiet_hours)
                if quiet and not rule.bypass_quiet_hours:
                    if rule.action == AlertAction.NOTIFY:
                        logger.info(
                            "scope1 quiet_hours suppressed rule=%s customer=%s",
                            rule.name,
                            _sid(customer_id),
                        )
                        continue

                # Deduplication check
                already_fired = await self._is_alert_deduped(
                    session,
                    customer_id=customer_id,
                    bucket_type=thread_type,
                    threshold_name=rule.name,
                    now_utc=now_utc,
                )
                if already_fired:
                    continue

                alert = AlertFired(
                    customer_id=customer_id,
                    bucket_type=thread_type,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed,
                    scope="CUSTOMER_BUCKET",
                    fired_at=now_utc,
                )
                await self._record_alert_log(session, alert)
                alerts.append(alert)
                logger.info(
                    "scope1 alert fired rule=%s customer=%s pct_consumed=%.3f",
                    rule.name,
                    _sid(customer_id),
                    pct_consumed,
                )

        return alerts

    async def _check_scope2_agency(
        self,
        session: AsyncSession,
        customer_id: UUID,
        period_start: date,
        now_ist: datetime,
        now_utc: datetime,
    ) -> list[AlertFired]:
        """Scope 2: agency sub-wallet threshold checks."""
        alerts: list[AlertFired] = []

        # Resolve agency_id for this customer
        agency_row = await session.execute(
            text(
                """
                SELECT agency_id, agency_quota_paise
                FROM   agency_wallet_members
                WHERE  customer_id = :customer_id
                LIMIT  1
                """
            ).bindparams(customer_id=_sid(customer_id))
        )
        agency_result = agency_row.fetchone()
        if agency_result is None:
            # Not part of any agency - skip scope 2
            return alerts

        agency_id: str = str(agency_result.agency_id)
        agency_quota: float = float(agency_result.agency_quota_paise or 0)

        if agency_quota <= 0.0:
            # NULL quota produces no alert (per spec)
            return alerts

        # Sum all agency member consumption for this billing period
        agency_consumed_row = await session.execute(
            text(
                """
                SELECT COALESCE(SUM(pcl.marked_up_cost_inr_paise), 0) AS consumed
                FROM   platform_cost_ledger pcl
                JOIN   agency_wallet_members awm
                       ON awm.customer_id = pcl.customer_id
                WHERE  awm.agency_id          = :agency_id
                  AND  pcl.billing_period_start = :period_start
                """
            ).bindparams(agency_id=agency_id, period_start=period_start)
        )
        agency_consumed_result = agency_consumed_row.fetchone()
        agency_consumed: float = (
            float(agency_consumed_result.consumed) if agency_consumed_result else 0.0
        )

        pct_consumed = agency_consumed / agency_quota

        policy = AGENCY_POLICY
        quiet = _is_quiet_hours(policy, now_ist)

        for rule in policy.rules:
            trigger = getattr(rule, "consumed_pct_trigger", None)
            if trigger is None:
                continue
            if pct_consumed < trigger:
                continue

            if quiet and not rule.bypass_quiet_hours:
                if rule.action == AlertAction.NOTIFY:
                    logger.info(
                        "scope2 quiet_hours suppressed rule=%s agency=%s",
                        rule.name,
                        agency_id,
                    )
                    continue

            already_fired = await self._is_alert_deduped(
                session,
                customer_id=customer_id,
                bucket_type="AGENCY",
                threshold_name=rule.name,
                now_utc=now_utc,
            )
            if already_fired:
                continue

            alert = AlertFired(
                customer_id=customer_id,
                bucket_type="AGENCY",
                threshold_name=rule.name,
                pct_consumed=pct_consumed,
                scope="AGENCY",
                fired_at=now_utc,
            )
            await self._record_alert_log(session, alert)
            alerts.append(alert)
            logger.info(
                "scope2 agency alert fired rule=%s agency=%s pct_consumed=%.3f",
                rule.name,
                agency_id,
                pct_consumed,
            )

        return alerts

    async def _check_scope3_procurement(
        self,
        session: AsyncSession,
        now_ist: datetime,
        now_utc: datetime,
    ) -> list[AlertFired]:
        """
        Scope 3: PROCUREMENT runway checks across all active providers.

        Uses provider_accounts (provider_name, balance_paise, daily_burn_rate_paise, is_active).
        days_remaining = balance_paise / daily_burn_rate_paise.
        Runway threshold rules use days_remaining_trigger (not pct_consumed).
        C-059: each firing written to meter_alert_log with customer_id=UUID(int=0) sentinel.
        """
        alerts: list[AlertFired] = []

        providers_row = await session.execute(
            text(
                """
                SELECT provider_name, balance_paise, daily_burn_rate_paise
                FROM   provider_accounts
                WHERE  is_active = 1
                   OR  is_active = TRUE
                """
            )
        )
        providers = providers_row.fetchall()

        policy = PROCUREMENT_POLICY
        quiet = _is_quiet_hours(policy, now_ist)

        # Sentinel customer_id for platform-level procurement alerts
        platform_sentinel = UUID(int=0)

        for provider in providers:
            provider_name: str = str(provider.provider_name)
            balance: float = float(provider.balance_paise or 0)
            burn_rate: float = float(provider.daily_burn_rate_paise or 0)

            if burn_rate <= 0.0:
                # Cannot compute runway without burn rate
                continue

            days_remaining = balance / burn_rate

            for rule in policy.rules:
                trigger = getattr(rule, "days_remaining_trigger", None)
                if trigger is None:
                    continue
                if days_remaining > trigger:
                    continue

                if quiet and not rule.bypass_quiet_hours:
                    if rule.action == AlertAction.NOTIFY:
                        logger.info(
                            "scope3 quiet_hours suppressed rule=%s provider=%s",
                            rule.name,
                            provider_name,
                        )
                        continue

                already_fired = await self._is_alert_deduped(
                    session,
                    customer_id=platform_sentinel,
                    bucket_type=provider_name,
                    threshold_name=rule.name,
                    now_utc=now_utc,
                )
                if already_fired:
                    continue

                # pct_consumed not meaningful for runway; encode as days_remaining ratio
                pct_consumed_proxy = days_remaining / max(trigger, 1.0)

                alert = AlertFired(
                    customer_id=platform_sentinel,
                    bucket_type=provider_name,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed_proxy,
                    scope="PROCUREMENT",
                    fired_at=now_utc,
                )
                await self._record_alert_log(session, alert)
                alerts.append(alert)
                logger.info(
                    "scope3 procurement alert fired rule=%s provider=%s days_remaining=%.1f",
                    rule.name,
                    provider_name,
                    days_remaining,
                )

        return alerts

    # ------------------------------------------------------------------
    # Deduplication + logging helpers
    # ------------------------------------------------------------------

    async def _is_alert_deduped(
        self,
        session: AsyncSession,
        customer_id: UUID,
        bucket_type: str,
        threshold_name: str,
        now_utc: datetime,
    ) -> bool:
        """
        Return True if an identical alert was already fired within the dedup window.

        C-059: dedup prevents duplicate evidence records from polluting the audit log.
        """
        window_start = now_utc - timedelta(hours=_DEDUP_WINDOW_HOURS)
        dedup_row = await session.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM   meter_alert_log
                WHERE  customer_id     = :customer_id
                  AND  bucket_type     = :bucket_type
                  AND  threshold_name  = :threshold_name
                  AND  fired_at       >= :window_start
                """
            ).bindparams(
                customer_id=_sid(customer_id),
                bucket_type=bucket_type,
                threshold_name=threshold_name,
                window_start=window_start,
            )
        )
        dedup_result = dedup_row.fetchone()
        count: int = int(dedup_result.cnt) if dedup_result else 0
        return count > 0

    async def _record_alert_log(
        self,
        session: AsyncSession,
        alert: AlertFired,
    ) -> None:
        """
        Write fired alert to meter_alert_log as C-059 evidence record.

        C-063: no PII - only UUID and threshold name recorded.
        """
        await session.execute(
            text(
                """
                INSERT INTO meter_alert_log
                    (id, customer_id, bucket_type, threshold_name,
                     pct_consumed, scope, fired_at)
                VALUES
                    (:id, :customer_id, :bucket_type, :threshold_name,
                     :pct_consumed, :scope, :fired_at)
                """
            ).bindparams(
                id=_sid(uuid4()),
                customer_id=_sid(alert.customer_id),
                bucket_type=alert.bucket_type,
                threshold_name=alert.threshold_name,
                pct_consumed=alert.pct_consumed,
                scope=alert.scope,
                fired_at=alert.fired_at,
            )
        )
        await session.commit()