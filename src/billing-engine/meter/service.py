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
    RunwayThresholdRule,
    ThresholdPolicy,
    ThresholdRule,
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
        Project bucket depletion using 7-day rolling average.

        Reads platform_cost_ledger for the last 7 days to compute daily burn rate,
        then divides remaining wallet_buckets.balance_paise by that rate.
        C-049: discloses low balance honestly via projection.
        """
        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                window_start = (now_utc - timedelta(days=_ROLLING_DAYS)).date()

                # 7-day rolling total spend
                spend_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS total_spend
                        FROM   platform_cost_ledger
                        WHERE  customer_id = :customer_id
                          AND  thread_type  = :thread_type
                          AND  DATE(recorded_at) >= :window_start
                        """
                    ).bindparams(
                        customer_id=_sid(customer_id),
                        thread_type=thread_type,
                        window_start=str(window_start),
                    )
                )
                spend_result = spend_row.fetchone()
                total_spend: float = float(spend_result.total_spend) if spend_result else 0.0
                daily_burn: float = total_spend / _ROLLING_DAYS if total_spend > 0 else 0.0

                # Current bucket balance
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
                balance_paise: float = float(balance_result.balance_paise) if balance_result else 0.0

                if daily_burn <= 0.0:
                    # No burn rate - effectively infinite runway; report 999 days
                    days_remaining: float = 999.0
                else:
                    days_remaining = balance_paise / daily_burn

                projected_empty = (now_utc + timedelta(days=days_remaining)).date()

                return DepletionProjection(
                    days_remaining=days_remaining,
                    projected_empty_date=projected_empty,
                    daily_burn_rate_paise=daily_burn,
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
    # MeterService.check_thresholds (concrete helper, not in IMeterService)
    # ------------------------------------------------------------------
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
        """
        Evaluate Scope 1 (customer bucket), Scope 2 (agency), Scope 3 (procurement)
        threshold ladder per §2.3a. Deduplicates via meter_alert_log within 24h window.
        C-043: fires alerts when pct_consumed crosses ladder rungs.
        C-049: honest disclosure of low balance state.
        Returns list of newly-fired AlertFired records (already persisted to meter_alert_log).
        """
        alerts: list[AlertFired] = []
        now_ist = _now_ist()

        try:
            async with self._session_factory() as session:
                alerts = await self._check_scope1_customer(
                    session, customer_id, now_ist, alerts
                )
                alerts = await self._check_scope2_agency(
                    session, customer_id, now_ist, alerts
                )
                alerts = await self._check_scope3_procurement(
                    session, now_ist, alerts
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

        return alerts

    async def _check_scope1_customer(
        self,
        session: AsyncSession,
        customer_id: UUID,
        now_ist: datetime,
        alerts: list[AlertFired],
    ) -> list[AlertFired]:
        """
        Scope 1: per-customer-bucket thresholds.
        pct_consumed = SUM(ledger cost for current period) / wallet_bucket.balance_paise
        """
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        # Get all thread_types active for this customer this period
        types_row = await session.execute(
            text(
                """
                SELECT DISTINCT thread_type,
                       COALESCE(SUM(marked_up_cost_inr_paise), 0) AS period_spend
                FROM   platform_cost_ledger
                WHERE  customer_id = :customer_id
                  AND  billing_period_start = :period_start
                GROUP BY thread_type
                """
            ).bindparams(
                customer_id=_sid(customer_id),
                period_start=str(period_start),
            )
        )
        type_rows = types_row.fetchall()

        for type_row in type_rows:
            thread_type: str = type_row.thread_type
            period_spend: float = float(type_row.period_spend)

            # Get bucket quota (balance_paise is the period quota)
            bucket_row = await session.execute(
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
            bucket_result = bucket_row.fetchone()
            if bucket_result is None or bucket_result.balance_paise <= 0:
                continue

            quota: float = float(bucket_result.balance_paise)
            pct_consumed: float = period_spend / quota

            for rule in CUSTOMER_BUCKET_POLICY.rules:
                # Scope 1 uses ThresholdRule (pct-based), skip RunwayThresholdRule
                if not isinstance(rule, ThresholdRule):
                    continue
                trigger = rule.consumed_pct_trigger
                if pct_consumed < trigger:
                    continue

                # Quiet hours check
                if _is_quiet_hours(CUSTOMER_BUCKET_POLICY, now_ist) and not rule.bypass_quiet_hours:
                    logger.info(
                        "scope1 alert suppressed (quiet hours) customer=%s rule=%s",
                        _sid(customer_id),
                        rule.name,
                    )
                    continue

                # Deduplication check
                already_fired = await self._alert_already_fired(
                    session, customer_id, thread_type, rule.name, now_utc
                )
                if already_fired:
                    continue

                fired = AlertFired(
                    customer_id=customer_id,
                    bucket_type=thread_type,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed,
                    scope="CUSTOMER_BUCKET",
                    fired_at=now_ist,
                )
                await self._persist_alert(session, fired, now_utc)
                alerts.append(fired)
                logger.info(
                    "scope1 alert fired customer=%s thread=%s rule=%s pct=%.3f",
                    _sid(customer_id),
                    thread_type,
                    rule.name,
                    pct_consumed,
                )

        return alerts

    async def _check_scope2_agency(
        self,
        session: AsyncSession,
        customer_id: UUID,
        now_ist: datetime,
        alerts: list[AlertFired],
    ) -> list[AlertFired]:
        """
        Scope 2: agency sub-wallet thresholds.
        Uses agency_sub_wallets table if present; skips gracefully if NULL quota.
        """
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        # Check agency_sub_wallets for this customer
        agency_row = await session.execute(
            text(
                """
                SELECT id, quota_paise
                FROM   agency_sub_wallets
                WHERE  customer_id = :customer_id
                LIMIT  1
                """
            ).bindparams(customer_id=_sid(customer_id))
        )
        agency_result = agency_row.fetchone()

        # NULL quota or missing agency wallet -> no alert (per spec)
        if agency_result is None or agency_result.quota_paise is None:
            return alerts

        quota: float = float(agency_result.quota_paise)
        if quota <= 0:
            return alerts

        # Sum spend for this customer this period across all thread types
        spend_row = await session.execute(
            text(
                """
                SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS period_spend
                FROM   platform_cost_ledger
                WHERE  customer_id = :customer_id
                  AND  billing_period_start = :period_start
                """
            ).bindparams(
                customer_id=_sid(customer_id),
                period_start=str(period_start),
            )
        )
        spend_result = spend_row.fetchone()
        period_spend: float = float(spend_result.period_spend) if spend_result else 0.0
        pct_consumed: float = period_spend / quota

        for rule in AGENCY_POLICY.rules:
            if not isinstance(rule, ThresholdRule):
                continue
            trigger = rule.consumed_pct_trigger
            if pct_consumed < trigger:
                continue

            if _is_quiet_hours(AGENCY_POLICY, now_ist) and not rule.bypass_quiet_hours:
                logger.info(
                    "scope2 alert suppressed (quiet hours) customer=%s rule=%s",
                    _sid(customer_id),
                    rule.name,
                )
                continue

            already_fired = await self._alert_already_fired(
                session, customer_id, "AGENCY", rule.name, now_utc
            )
            if already_fired:
                continue

            fired = AlertFired(
                customer_id=customer_id,
                bucket_type="AGENCY",
                threshold_name=rule.name,
                pct_consumed=pct_consumed,
                scope="AGENCY",
                fired_at=now_ist,
            )
            await self._persist_alert(session, fired, now_utc)
            alerts.append(fired)
            logger.info(
                "scope2 alert fired customer=%s rule=%s pct=%.3f",
                _sid(customer_id),
                rule.name,
                pct_consumed,
            )

        return alerts

    async def _check_scope3_procurement(
        self,
        session: AsyncSession,
        now_ist: datetime,
        alerts: list[AlertFired],
    ) -> list[AlertFired]:
        """
        Scope 3: WAOOAW platform procurement runway thresholds.
        Reads provider_accounts (balance_paise, daily_burn_rate_paise).
        Uses RunwayThresholdRule (days_remaining_trigger) from PROCUREMENT_POLICY.
        Fires global procurement alerts (not per-customer - uses nil UUID sentinel).
        """
        now_utc = datetime.now(timezone.utc)

        # Read all active provider accounts
        providers_row = await session.execute(
            text(
                """
                SELECT id, provider_name, balance_paise, daily_burn_rate_paise
                FROM   provider_accounts
                WHERE  is_active = TRUE
                """
            )
        )
        provider_rows = providers_row.fetchall()

        # Sentinel customer_id for procurement-scope alerts (no specific customer)
        procurement_customer_id = UUID("00000000-0000-0000-0000-000000000000")

        for prow in provider_rows:
            provider_name: str = prow.provider_name
            balance: float = float(prow.balance_paise)
            burn_rate: float = float(prow.daily_burn_rate_paise) if prow.daily_burn_rate_paise else 0.0

            if burn_rate <= 0.0:
                continue

            days_remaining: float = balance / burn_rate

            for rule in PROCUREMENT_POLICY.rules:
                if not isinstance(rule, RunwayThresholdRule):
                    continue
                if days_remaining > rule.days_remaining_trigger:
                    continue

                if _is_quiet_hours(PROCUREMENT_POLICY, now_ist) and not rule.bypass_quiet_hours:
                    logger.info(
                        "scope3 alert suppressed (quiet hours) provider=%s rule=%s",
                        provider_name,
                        rule.name,
                    )
                    continue

                already_fired = await self._alert_already_fired(
                    session, procurement_customer_id, provider_name, rule.name, now_utc
                )
                if already_fired:
                    continue

                # pct_consumed not directly applicable for runway; encode as days_remaining ratio
                pct_consumed_proxy: float = min(1.0, days_remaining / 30.0) if days_remaining > 0 else 1.0

                fired = AlertFired(
                    customer_id=procurement_customer_id,
                    bucket_type=provider_name,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed_proxy,
                    scope="PROCUREMENT",
                    fired_at=now_ist,
                )
                await self._persist_alert(session, fired, now_utc)
                alerts.append(fired)
                logger.info(
                    "scope3 alert fired provider=%s rule=%s days_remaining=%.1f",
                    provider_name,
                    rule.name,
                    days_remaining,
                )

        return alerts

    async def _alert_already_fired(
        self,
        session: AsyncSession,
        customer_id: UUID,
        bucket_type: str,
        threshold_name: str,
        now_utc: datetime,
    ) -> bool:
        """
        Check meter_alert_log for a matching alert fired within the dedup window.
        Returns True if a duplicate exists within _DEDUP_WINDOW_HOURS.
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
                  AND  fired_at        >= :window_start
                """
            ).bindparams(
                customer_id=_sid(customer_id),
                bucket_type=bucket_type,
                threshold_name=threshold_name,
                window_start=window_start,
            )
        )
        dedup_result = dedup_row.fetchone()
        return bool(dedup_result and dedup_result.cnt > 0)

    async def _persist_alert(
        self,
        session: AsyncSession,
        alert: AlertFired,
        now_utc: datetime,
    ) -> None:
        """Persist an AlertFired record to meter_alert_log for deduplication and audit trail."""
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
                fired_at=now_utc,
            )
        )
        await session.commit()

    # ------------------------------------------------------------------
    # IMeterService.run_daily_scan
    # ------------------------------------------------------------------
    async def run_daily_scan(self) -> DailyScanResult:
        """
        Runs at 06:00 IST (invoked by scheduler stub).
        Scans all active customers, calls check_thresholds for each,
        aggregates DailyScanResult.
        C-059: each scan produces an evidence trail via meter_alert_log.
        """
        customers_scanned = 0
        alerts_sent = 0
        offers_generated = 0
        fa_items_created = 0

        try:
            async with self._session_factory() as session:
                # Fetch all active customers from wallet_buckets
                cust_row = await session.execute(
                    text(
                        """
                        SELECT DISTINCT customer_id
                        FROM   wallet_buckets
                        WHERE  is_active = TRUE
                        """
                    )
                )
                customer_rows = cust_row.fetchall()

            for crow in customer_rows:
                cid = UUID(str(crow.customer_id))
                customers_scanned += 1
                try:
                    fired = await self.check_thresholds(cid)
                    alerts_sent += len(fired)
                    # Escalate FA items for BLOCK-action alerts
                    for alert in fired:
                        rule_action = self._resolve_action_for_alert(alert)
                        if rule_action == AlertAction.FA:
                            fa_items_created += 1
                except asyncio.CancelledError:
                    raise
                except (ValueError, RuntimeError, OSError) as exc:
                    logger.error(
                        "run_daily_scan: check_thresholds failed for customer=%s",
                        str(cid),
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
            "run_daily_scan complete scanned=%d alerts=%d fa_items=%d",
            customers_scanned,
            alerts_sent,
            fa_items_created,
        )
        return DailyScanResult(
            customers_scanned=customers_scanned,
            alerts_sent=alerts_sent,
            offers_generated=offers_generated,
            fa_items_created=fa_items_created,
        )

    def _resolve_action_for_alert(self, alert: AlertFired) -> AlertAction:
        """
        Resolve the AlertAction for a fired alert by looking up the matching rule
        in the appropriate policy.
        Returns AlertAction.LOG as default if rule not found.
        """
        if alert.scope == "CUSTOMER_BUCKET":
            policy = CUSTOMER_BUCKET_POLICY
        elif alert.scope == "AGENCY":
            policy = AGENCY_POLICY
        elif alert.scope == "PROCUREMENT":
            policy = PROCUREMENT_POLICY
        else:
            return AlertAction.LOG

        for rule in policy.rules:
            if rule.name == alert.threshold_name:
                return rule.action
        return AlertAction.LOG