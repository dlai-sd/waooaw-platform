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
                        id=_sid(uuid4()),
                        customer_id=_sid(customer_id),
                        thread_type=thread_type,
                        provider_account_id=_sid(provider_account_id),
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

        Computes daily_burn_rate from platform_cost_ledger over the last
        _ROLLING_DAYS days, then divides available balance by that rate.
        C-049: days_remaining surfaced to caller for honest limitation disclosure.
        """
        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                window_start = now_utc - timedelta(days=_ROLLING_DAYS)

                # Sum usage over rolling 7-day window
                burn_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS total_paise
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
                total_paise: int = burn_result.total_paise if burn_result else 0

                daily_burn: float = (
                    total_paise / _ROLLING_DAYS if _ROLLING_DAYS > 0 else 0.0
                )

                # Fetch current available balance from wallet_buckets
                balance_row = await session.execute(
                    text(
                        """
                        SELECT wb.available_paise
                        FROM   wallet_buckets wb
                        JOIN   customer_wallets cw ON cw.id = wb.wallet_id
                        WHERE  cw.customer_id = :customer_id
                          AND  wb.thread_type  = :thread_type
                        LIMIT  1
                        """
                    ).bindparams(
                        customer_id=_sid(customer_id),
                        thread_type=thread_type,
                    )
                )
                balance_result = balance_row.fetchone()
                available_paise: int = (
                    balance_result.available_paise if balance_result else 0
                )

                if daily_burn <= 0:
                    # No recent burn -- bucket effectively unlimited for projection
                    days_remaining = float("inf")
                    projected_empty = now_utc.date() + timedelta(days=3650)
                else:
                    days_remaining = available_paise / daily_burn
                    projected_empty = now_utc.date() + timedelta(days=days_remaining)

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
    # MeterService.check_thresholds  (concrete helper, NOT in IMeterService)
    # ------------------------------------------------------------------
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
        """
        Fire threshold alerts per §2.3a scope 1+2+3 ladder.

        Scope 1 - CUSTOMER_BUCKET: per thread_type bucket consumption vs quota.
        Scope 2 - AGENCY: agency sub-wallet aggregate (if agency_id present).
        Scope 3 - PROCUREMENT: platform provider runway days remaining.

        Deduplicates via meter_alert_log within _DEDUP_WINDOW_HOURS.
        Respects quiet_hours_ist per ThresholdPolicy (bypass_quiet_hours flag
        on individual ThresholdRule overrides the policy-level quiet window).
        C-043: pct_consumed = SUM(ledger) / wallet_buckets.balance_paise (quota).
        """
        fired: list[AlertFired] = []
        now_ist = _now_ist()
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        try:
            async with self._session_factory() as session:
                # --- Scope 1: CUSTOMER_BUCKET per thread_type ---
                bucket_rows = await session.execute(
                    text(
                        """
                        SELECT wb.thread_type,
                               wb.balance_paise AS quota_paise
                        FROM   wallet_buckets wb
                        JOIN   customer_wallets cw ON cw.id = wb.wallet_id
                        WHERE  cw.customer_id = :customer_id
                        """
                    ).bindparams(customer_id=_sid(customer_id))
                )
                buckets = bucket_rows.fetchall()

                for bucket in buckets:
                    thread_type: str = bucket.thread_type
                    quota_paise: int = bucket.quota_paise

                    if quota_paise <= 0:
                        # No quota configured - nothing to threshold against
                        continue

                    # Sum consumed paise in current billing period
                    consumed_row = await session.execute(
                        text(
                            """
                            SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS consumed
                            FROM   platform_cost_ledger
                            WHERE  customer_id          = :customer_id
                              AND  thread_type          = :thread_type
                              AND  billing_period_start = :period_start
                            """
                        ).bindparams(
                            customer_id=_sid(customer_id),
                            thread_type=thread_type,
                            period_start=period_start,
                        )
                    )
                    consumed_result = consumed_row.fetchone()
                    consumed_paise: int = (
                        consumed_result.consumed if consumed_result else 0
                    )

                    pct_consumed: float = consumed_paise / quota_paise

                    scope_fired = await self._evaluate_policy(
                        session=session,
                        policy=CUSTOMER_BUCKET_POLICY,
                        customer_id=customer_id,
                        bucket_type=thread_type,
                        scope="CUSTOMER_BUCKET",
                        pct_consumed=pct_consumed,
                        now_ist=now_ist,
                        now_utc=now_utc,
                    )
                    fired.extend(scope_fired)

                # --- Scope 2: AGENCY sub-wallet ---
                agency_row = await session.execute(
                    text(
                        """
                        SELECT aw.id          AS agency_wallet_id,
                               aw.balance_paise AS quota_paise
                        FROM   agency_wallets aw
                        JOIN   agency_customers ac
                               ON ac.agency_wallet_id = aw.id
                        WHERE  ac.customer_id = :customer_id
                        LIMIT  1
                        """
                    ).bindparams(customer_id=_sid(customer_id))
                )
                agency_result = agency_row.fetchone()

                if agency_result is not None:
                    agency_quota: int = agency_result.quota_paise
                    if agency_quota > 0:
                        agency_wallet_id = agency_result.agency_wallet_id
                        agency_consumed_row = await session.execute(
                            text(
                                """
                                SELECT COALESCE(SUM(pcl.marked_up_cost_inr_paise), 0)
                                       AS consumed
                                FROM   platform_cost_ledger pcl
                                JOIN   agency_customers ac
                                       ON ac.customer_id = pcl.customer_id
                                WHERE  ac.agency_wallet_id  = :agency_wallet_id
                                  AND  pcl.billing_period_start = :period_start
                                """
                            ).bindparams(
                                agency_wallet_id=_sid(agency_wallet_id),
                                period_start=period_start,
                            )
                        )
                        agency_consumed_result = agency_consumed_row.fetchone()
                        agency_consumed: int = (
                            agency_consumed_result.consumed
                            if agency_consumed_result
                            else 0
                        )
                        agency_pct: float = agency_consumed / agency_quota

                        agency_fired = await self._evaluate_policy(
                            session=session,
                            policy=AGENCY_POLICY,
                            customer_id=customer_id,
                            bucket_type="AGENCY",
                            scope="AGENCY",
                            pct_consumed=agency_pct,
                            now_ist=now_ist,
                            now_utc=now_utc,
                        )
                        fired.extend(agency_fired)

                # --- Scope 3: PROCUREMENT runway ---
                # Procurement thresholds are days-based; pct_consumed is
                # expressed as (1 - days_remaining/30) normalised to [0,1]
                # so that RUNWAY_P2 at <=30d maps to pct>=0.0,
                # RUNWAY_P1 at <=14d maps to pct>=0.533, etc.
                # The ThresholdRule.consumed_pct_trigger stores the days trigger
                # directly -- we compare days_remaining instead.
                procurement_fired = await self._evaluate_procurement_scope(
                    session=session,
                    customer_id=customer_id,
                    now_ist=now_ist,
                    now_utc=now_utc,
                )
                fired.extend(procurement_fired)

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
    # Internal: evaluate a ThresholdPolicy for a given pct_consumed
    # ------------------------------------------------------------------
    async def _evaluate_policy(
        self,
        session: AsyncSession,
        policy: ThresholdPolicy,
        customer_id: UUID,
        bucket_type: str,
        scope: str,
        pct_consumed: float,
        now_ist: datetime,
        now_utc: datetime,
    ) -> list[AlertFired]:
        """
        Walk the threshold ladder for a policy and fire rules where triggered.

        Deduplicates via meter_alert_log within _DEDUP_WINDOW_HOURS.
        """
        results: list[AlertFired] = []
        quiet = _is_quiet_hours(policy, now_ist)

        for rule in policy.thresholds:
            if pct_consumed < rule.consumed_pct_trigger:
                continue  # not yet triggered

            # Suppress NOTIFY-class alerts during quiet hours unless bypassed
            if (
                quiet
                and not rule.bypass_quiet_hours
                and rule.action == AlertAction.NOTIFY
            ):
                logger.info(
                    "quiet hours suppressed alert rule=%s customer=%s",
                    rule.name,
                    _sid(customer_id),
                )
                continue

            # Deduplication: check meter_alert_log for recent fire
            dedup_window = now_utc - timedelta(hours=_DEDUP_WINDOW_HOURS)
            dedup_row = await session.execute(
                text(
                    """
                    SELECT id FROM meter_alert_log
                    WHERE  customer_id     = :customer_id
                      AND  bucket_type     = :bucket_type
                      AND  threshold_name  = :threshold_name
                      AND  fired_at        >= :dedup_window
                    LIMIT  1
                    """
                ).bindparams(
                    customer_id=_sid(customer_id),
                    bucket_type=bucket_type,
                    threshold_name=rule.name,
                    dedup_window=dedup_window,
                )
            )
            if dedup_row.fetchone() is not None:
                logger.info(
                    "dedup suppressed alert rule=%s customer=%s",
                    rule.name,
                    _sid(customer_id),
                )
                continue

            # Fire the alert - write evidence record to meter_alert_log
            alert_id = uuid4()
            await session.execute(
                text(
                    """
                    INSERT INTO meter_alert_log
                        (id, customer_id, bucket_type, threshold_name,
                         pct_consumed, scope, action, fired_at)
                    VALUES
                        (:id, :customer_id, :bucket_type, :threshold_name,
                         :pct_consumed, :scope, :action, :fired_at)
                    """
                ).bindparams(
                    id=_sid(alert_id),
                    customer_id=_sid(customer_id),
                    bucket_type=bucket_type,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed,
                    scope=scope,
                    action=rule.action.value,
                    fired_at=now_utc,
                )
            )
            await session.commit()

            alert = AlertFired(
                customer_id=customer_id,
                bucket_type=bucket_type,
                threshold_name=rule.name,
                pct_consumed=pct_consumed,
                scope=scope,
                fired_at=now_ist,
            )
            results.append(alert)
            logger.info(
                "alert fired rule=%s scope=%s customer=%s pct_consumed=%.3f",
                rule.name,
                scope,
                _sid(customer_id),
                pct_consumed,
            )

        return results

    # ------------------------------------------------------------------
    # Internal: evaluate Scope 3 PROCUREMENT runway per provider
    # ------------------------------------------------------------------
    async def _evaluate_procurement_scope(
        self,
        session: AsyncSession,
        customer_id: UUID,
        now_ist: datetime,
        now_utc: datetime,
    ) -> list[AlertFired]:
        """
        Evaluate PROCUREMENT scope runway thresholds.

        Procurement runway rules use days_remaining directly; the
        consumed_pct_trigger on ThresholdRule is interpreted as the
        maximum days_remaining that triggers the rule (i.e. the rule
        fires when days_remaining <= consumed_pct_trigger).

        Provider rows come from provider_runway_view (or provider_accounts
        + rolling ledger aggregation).
        """
        results: list[AlertFired] = []
        quiet = _is_quiet_hours(PROCUREMENT_POLICY, now_ist)

        # Fetch per-provider runway from the platform view
        runway_rows = await session.execute(
            text(
                """
                SELECT provider_name,
                       days_remaining
                FROM   provider_runway_view
                """
            )
        )
        providers = runway_rows.fetchall()

        for provider in providers:
            provider_name: str = provider.provider_name
            days_remaining: float = float(provider.days_remaining)

            for rule in PROCUREMENT_POLICY.thresholds:
                # For procurement, consumed_pct_trigger stores the days threshold
                if days_remaining > rule.consumed_pct_trigger:
                    continue  # runway still sufficient

                if (
                    quiet
                    and not rule.bypass_quiet_hours
                    and rule.action == AlertAction.NOTIFY
                ):
                    logger.info(
                        "quiet hours suppressed procurement alert rule=%s provider=%s",
                        rule.name,
                        provider_name,
                    )
                    continue

                # Deduplication
                dedup_window = now_utc - timedelta(hours=_DEDUP_WINDOW_HOURS)
                dedup_row = await session.execute(
                    text(
                        """
                        SELECT id FROM meter_alert_log
                        WHERE  customer_id     = :customer_id
                          AND  bucket_type     = :bucket_type
                          AND  threshold_name  = :threshold_name
                          AND  fired_at        >= :dedup_window
                        LIMIT  1
                        """
                    ).bindparams(
                        customer_id=_sid(customer_id),
                        bucket_type=provider_name,
                        threshold_name=rule.name,
                        dedup_window=dedup_window,
                    )
                )
                if dedup_row.fetchone() is not None:
                    continue

                alert_id = uuid4()
                await session.execute(
                    text(
                        """
                        INSERT INTO meter_alert_log
                            (id, customer_id, bucket_type, threshold_name,
                             pct_consumed, scope, action, fired_at)
                        VALUES
                            (:id, :customer_id, :bucket_type, :threshold_name,
                             :pct_consumed, :scope, :action, :fired_at)
                        """
                    ).bindparams(
                        id=_sid(alert_id),
                        customer_id=_sid(customer_id),
                        bucket_type=provider_name,
                        threshold_name=rule.name,
                        pct_consumed=days_remaining,
                        scope="PROCUREMENT",
                        action=rule.action.value,
                        fired_at=now_utc,
                    )
                )
                await session.commit()

                alert = AlertFired(
                    customer_id=customer_id,
                    bucket_type=provider_name,
                    threshold_name=rule.name,
                    pct_consumed=days_remaining,
                    scope="PROCUREMENT",
                    fired_at=now_ist,
                )
                results.append(alert)
                logger.info(
                    "procurement alert fired rule=%s provider=%s days_remaining=%.1f",
                    rule.name,
                    provider_name,
                    days_remaining,
                )

        return results

    # ------------------------------------------------------------------
    # IMeterService.run_daily_scan
    # ------------------------------------------------------------------
    async def run_daily_scan(self) -> DailyScanResult:
        """
        Daily scan entry point - runs at 06:00 IST via scheduler stub.

        Fetches all active customers from customer_wallets and calls
        check_thresholds for each. Aggregates counts for DailyScanResult.
        C-059: evidence of scan logged with customer count.
        """
        result = DailyScanResult(
            customers_scanned=0,
            alerts_sent=0,
            offers_generated=0,
            fa_items_created=0,
        )

        try:
            async with self._session_factory() as session:
                customers_row = await session.execute(
                    text(
                        """
                        SELECT DISTINCT cw.customer_id
                        FROM   customer_wallets cw
                        WHERE  cw.status = 'ACTIVE'
                        """
                    )
                )
                customers = customers_row.fetchall()

            for row in customers:
                cid: UUID = UUID(str(row.customer_id))
                try:
                    alerts = await self.check_thresholds(cid)
                    result.customers_scanned += 1
                    result.alerts_sent += len(alerts)

                    # Count FA-level alerts (action == FA)
                    for alert in alerts:
                        # Determine FA count from policy lookup
                        policy_map = {
                            "CUSTOMER_BUCKET": CUSTOMER_BUCKET_POLICY,
                            "AGENCY": AGENCY_POLICY,
                            "PROCUREMENT": PROCUREMENT_POLICY,
                        }
                        pol = policy_map.get(alert.scope)
                        if pol is not None:
                            for rule in pol.thresholds:
                                if (
                                    rule.name == alert.threshold_name
                                    and rule.action == AlertAction.FA
                                ):
                                    result.fa_items_created += 1

                except asyncio.CancelledError:
                    raise
                except (ValueError, RuntimeError, OSError):
                    logger.error(
                        "run_daily_scan check_thresholds failed customer=%s",
                        _sid(cid),
                        exc_info=True,
                        extra={"context": "daily_scan_loop"},
                    )
                    # Continue scanning remaining customers - C-059 error logged above

        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "run_daily_scan failed at customer fetch stage",
                exc_info=True,
                extra={"context": str(exc)},
            )
            raise

        logger.info(
            "run_daily_scan complete customers_scanned=%d alerts_sent=%d fa_items=%d",
            result.customers_scanned,
            result.alerts_sent,
            result.fa_items_created,
        )
        return result