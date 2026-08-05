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
        C-051: transparent projection base.
        """
        try:
            async with self._session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                window_start = now_utc - timedelta(days=_ROLLING_DAYS)

                # Sum usage over the rolling 7-day window
                usage_row = await session.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS total_paise
                        FROM   platform_cost_ledger
                        WHERE  customer_id = :customer_id
                          AND  thread_type = :thread_type
                          AND  recorded_at >= :window_start
                        """
                    ).bindparams(
                        customer_id=customer_id,
                        thread_type=thread_type,
                        window_start=window_start,
                    )
                )
                usage_result = usage_row.fetchone()
                total_paise: float = float(usage_result.total_paise if usage_result else 0)
                daily_burn_rate = total_paise / _ROLLING_DAYS

                # Get current bucket balance
                balance_row = await session.execute(
                    text(
                        """
                        SELECT wb.balance_paise
                        FROM   wallet_buckets wb
                        JOIN   customer_wallets cw ON cw.id = wb.wallet_id
                        WHERE  cw.customer_id = :customer_id
                          AND  wb.thread_type  = :thread_type
                        LIMIT  1
                        """
                    ).bindparams(customer_id=customer_id, thread_type=thread_type)
                )
                balance_result = balance_row.fetchone()
                balance_paise: float = float(
                    balance_result.balance_paise if balance_result else 0
                )

                if daily_burn_rate <= 0:
                    # No burn - bucket does not deplete
                    days_remaining = float("inf")
                    projected_empty_date = date(9999, 12, 31)
                else:
                    days_remaining = balance_paise / daily_burn_rate
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
        Daily scan runs at 06:00 IST (scheduler stub).

        Fetches all active customers from wallet_buckets, then calls
        check_thresholds for each. Aggregates alerts_sent + fa_items_created.
        C-059: each scan result is traceable via meter_alert_log.
        """
        result = DailyScanResult(
            customers_scanned=0,
            alerts_sent=0,
            offers_generated=0,
            fa_items_created=0,
        )
        try:
            async with self._session_factory() as session:
                # Fetch all distinct active customer IDs with a wallet bucket
                rows = await session.execute(
                    text(
                        """
                        SELECT DISTINCT cw.customer_id
                        FROM   customer_wallets cw
                        JOIN   wallet_buckets wb ON wb.wallet_id = cw.id
                        WHERE  wb.balance_paise > 0
                        """
                    )
                )
                customer_ids: list[UUID] = [r.customer_id for r in rows.fetchall()]

            result.customers_scanned = len(customer_ids)

            for customer_id in customer_ids:
                try:
                    alerts = await self.check_thresholds(customer_id)
                    for alert in alerts:
                        result.alerts_sent += 1
                        if alert.scope == "PROCUREMENT" and "RUNWAY" in alert.threshold_name:
                            result.fa_items_created += 1
                except asyncio.CancelledError:
                    raise
                except (ValueError, RuntimeError, OSError) as exc:
                    logger.error(
                        "run_daily_scan check_thresholds failed customer=%s",
                        customer_id,
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

        logger.info(
            "run_daily_scan complete scanned=%d alerts=%d fa=%d",
            result.customers_scanned,
            result.alerts_sent,
            result.fa_items_created,
        )
        return result

    # ------------------------------------------------------------------
    # Concrete helper: check_thresholds  (NOT in IMeterService ABC)
    # ------------------------------------------------------------------
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
        """
        Evaluate all three threshold scopes for a customer and fire alerts.

        Scope 1 - CUSTOMER_BUCKET: per thread_type bucket depletion %.
        Scope 2 - AGENCY: sub-wallet aggregate depletion % (NULL quota -> skip).
        Scope 3 - PROCUREMENT: provider runway days remaining.

        Deduplication: alert suppressed if a same (customer_id, threshold_name,
        bucket_type) entry exists in meter_alert_log within _DEDUP_WINDOW_HOURS.
        Quiet hours: suppress NOTIFY action unless bypass_quiet_hours=True.

        C-043: AlertFired structure is the authoritative breach record.
        """
        fired: list[AlertFired] = []
        now_ist = _now_ist()

        try:
            async with self._session_factory() as session:
                # -- Scope 1: Customer bucket thresholds --
                await self._check_scope1_customer_buckets(
                    session, customer_id, now_ist, fired
                )

                # -- Scope 2: Agency sub-wallet thresholds --
                await self._check_scope2_agency(
                    session, customer_id, now_ist, fired
                )

                # -- Scope 3: Procurement runway thresholds --
                await self._check_scope3_procurement(
                    session, customer_id, now_ist, fired
                )

        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            logger.error(
                "check_thresholds failed customer=%s",
                customer_id,
                exc_info=True,
                extra={"context": str(exc)},
            )

        return fired

    # ------------------------------------------------------------------
    # Scope 1 - Customer bucket thresholds
    # ------------------------------------------------------------------
    async def _check_scope1_customer_buckets(
        self,
        session: AsyncSession,
        customer_id: UUID,
        now_ist: datetime,
        fired: list[AlertFired],
    ) -> None:
        """
        Evaluate CUSTOMER_BUCKET_POLICY thresholds for each thread_type bucket.

        pct_consumed = SUM(ledger costs this period) / (consumed + bucket.balance_paise)
        """
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        # Get all bucket balances for this customer
        bucket_rows = await session.execute(
            text(
                """
                SELECT wb.thread_type,
                       wb.balance_paise,
                       COALESCE(
                           (SELECT SUM(pcl.marked_up_cost_inr_paise)
                            FROM   platform_cost_ledger pcl
                            WHERE  pcl.customer_id = :customer_id
                              AND  pcl.thread_type  = wb.thread_type
                              AND  pcl.billing_period_start = :period_start),
                           0
                       ) AS consumed_paise
                FROM   wallet_buckets wb
                JOIN   customer_wallets cw ON cw.id = wb.wallet_id
                WHERE  cw.customer_id = :customer_id
                """
            ).bindparams(customer_id=customer_id, period_start=period_start)
        )
        buckets = bucket_rows.fetchall()

        policy = CUSTOMER_BUCKET_POLICY
        quiet = _is_quiet_hours(policy, now_ist)

        for bucket in buckets:
            thread_type: str = bucket.thread_type
            balance_paise: int = bucket.balance_paise
            consumed_paise: int = bucket.consumed_paise
            total_paise = consumed_paise + balance_paise

            if total_paise <= 0:
                # No quota - nothing to evaluate
                continue

            pct_consumed: float = consumed_paise / total_paise

            for rule in policy.thresholds:
                if pct_consumed < rule.consumed_pct_trigger:
                    continue

                # Quiet hours check
                if quiet and not rule.bypass_quiet_hours:
                    if rule.action == AlertAction.NOTIFY:
                        logger.info(
                            "quiet hours suppressing NOTIFY threshold=%s customer=%s",
                            rule.name,
                            customer_id,
                        )
                        continue

                # Deduplication check
                already_fired = await self._is_deduped(
                    session, customer_id, thread_type, rule.name
                )
                if already_fired:
                    continue

                alert = AlertFired(
                    customer_id=customer_id,
                    bucket_type=thread_type,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed,
                    scope="CUSTOMER_BUCKET",
                    fired_at=datetime.now(timezone.utc),
                )
                await self._record_alert(session, alert)
                fired.append(alert)
                logger.info(
                    "alert fired scope=CUSTOMER_BUCKET threshold=%s customer=%s pct=%.3f",
                    rule.name,
                    customer_id,
                    pct_consumed,
                )

    # ------------------------------------------------------------------
    # Scope 2 - Agency sub-wallet thresholds
    # ------------------------------------------------------------------
    async def _check_scope2_agency(
        self,
        session: AsyncSession,
        customer_id: UUID,
        now_ist: datetime,
        fired: list[AlertFired],
    ) -> None:
        """
        Evaluate AGENCY_POLICY thresholds for the agency sub-wallet aggregate.

        NULL quota -> skip (no alert).
        """
        # Fetch agency sub-wallet quota; NULL means no agency limit configured
        agency_row = await session.execute(
            text(
                """
                SELECT asw.quota_paise,
                       COALESCE(asw.consumed_paise, 0) AS consumed_paise
                FROM   agency_sub_wallets asw
                WHERE  asw.customer_id = :customer_id
                LIMIT  1
                """
            ).bindparams(customer_id=customer_id)
        )
        agency = agency_row.fetchone()

        if agency is None or agency.quota_paise is None:
            # NULL quota - no alert per spec
            return

        quota_paise: int = agency.quota_paise
        consumed_paise: int = agency.consumed_paise

        if quota_paise <= 0:
            return

        total_paise = quota_paise  # quota is the ceiling
        pct_consumed: float = consumed_paise / total_paise

        policy = AGENCY_POLICY
        quiet = _is_quiet_hours(policy, now_ist)

        for rule in policy.thresholds:
            if pct_consumed < rule.consumed_pct_trigger:
                continue

            if quiet and not rule.bypass_quiet_hours:
                if rule.action == AlertAction.NOTIFY:
                    logger.info(
                        "quiet hours suppressing AGENCY NOTIFY threshold=%s customer=%s",
                        rule.name,
                        customer_id,
                    )
                    continue

            already_fired = await self._is_deduped(
                session, customer_id, "AGENCY", rule.name
            )
            if already_fired:
                continue

            alert = AlertFired(
                customer_id=customer_id,
                bucket_type="AGENCY",
                threshold_name=rule.name,
                pct_consumed=pct_consumed,
                scope="AGENCY",
                fired_at=datetime.now(timezone.utc),
            )
            await self._record_alert(session, alert)
            fired.append(alert)
            logger.info(
                "alert fired scope=AGENCY threshold=%s customer=%s pct=%.3f",
                rule.name,
                customer_id,
                pct_consumed,
            )

    # ------------------------------------------------------------------
    # Scope 3 - Procurement runway thresholds
    # ------------------------------------------------------------------
    async def _check_scope3_procurement(
        self,
        session: AsyncSession,
        customer_id: UUID,
        now_ist: datetime,
        fired: list[AlertFired],
    ) -> None:
        """
        Evaluate PROCUREMENT_POLICY thresholds based on provider runway days.

        Runway days = provider_balance_paise / daily_burn_rate (7d rolling avg).
        Threshold names: RUNWAY_P2 (<=30d), RUNWAY_P1 (<=14d), RUNWAY_P0 (<=7d),
        RUNWAY_CRITICAL (<=3d), RUNWAY_EMERGENCY (<=1d).
        C-043: BLOCK action at RUNWAY_EMERGENCY fires even in quiet hours.
        """
        now_utc = datetime.now(timezone.utc)
        window_start = now_utc - timedelta(days=_ROLLING_DAYS)

        # Get all provider accounts with their balances and 7d burn
        provider_rows = await session.execute(
            text(
                """
                SELECT pa.id              AS provider_account_id,
                       pa.name            AS provider_name,
                       pa.balance_paise   AS balance_paise,
                       COALESCE(
                           (SELECT SUM(pcl.marked_up_cost_inr_paise)
                            FROM   platform_cost_ledger pcl
                            WHERE  pcl.provider_account_id = pa.id
                              AND  pcl.recorded_at >= :window_start),
                           0
                       ) AS rolling_cost_paise
                FROM   provider_accounts pa
                WHERE  pa.active = TRUE
                """
            ).bindparams(window_start=window_start)
        )
        providers = provider_rows.fetchall()

        policy = PROCUREMENT_POLICY
        quiet = _is_quiet_hours(policy, now_ist)

        for provider in providers:
            balance_paise: float = float(provider.balance_paise)
            rolling_cost: float = float(provider.rolling_cost_paise)
            daily_burn = rolling_cost / _ROLLING_DAYS if rolling_cost > 0 else 0.0

            if daily_burn <= 0:
                # No burn - runway is infinite; skip
                continue

            days_remaining: float = balance_paise / daily_burn
            bucket_type = f"PROCUREMENT:{provider.provider_name}"

            for rule in policy.thresholds:
                # For PROCUREMENT rules, consumed_pct_trigger stores days threshold
                # We compare days_remaining against the rule's days_threshold attribute
                # The ThresholdRule uses consumed_pct_trigger as days ceiling for runway
                if days_remaining > rule.consumed_pct_trigger:
                    continue

                if quiet and not rule.bypass_quiet_hours:
                    if rule.action == AlertAction.NOTIFY:
                        logger.info(
                            "quiet hours suppressing PROCUREMENT NOTIFY threshold=%s",
                            rule.name,
                        )
                        continue

                already_fired = await self._is_deduped(
                    session, customer_id, bucket_type, rule.name
                )
                if already_fired:
                    continue

                # pct_consumed for procurement = 1 - days_remaining / 30 (normalized)
                pct_consumed = max(0.0, min(1.0, 1.0 - days_remaining / 30.0))
                alert = AlertFired(
                    customer_id=customer_id,
                    bucket_type=bucket_type,
                    threshold_name=rule.name,
                    pct_consumed=pct_consumed,
                    scope="PROCUREMENT",
                    fired_at=datetime.now(timezone.utc),
                )
                await self._record_alert(session, alert)
                fired.append(alert)
                logger.info(
                    "alert fired scope=PROCUREMENT threshold=%s provider=%s days_remaining=%.1f",
                    rule.name,
                    provider.provider_name,
                    days_remaining,
                )

    # ------------------------------------------------------------------
    # Deduplication helpers
    # ------------------------------------------------------------------
    async def _is_deduped(
        self,
        session: AsyncSession,
        customer_id: UUID,
        bucket_type: str,
        threshold_name: str,
    ) -> bool:
        """
        Return True if this (customer_id, bucket_type, threshold_name) was already
        fired within _DEDUP_WINDOW_HOURS.
        C-059: dedup check is non-destructive - only reads meter_alert_log.
        """
        window_start = datetime.now(timezone.utc) - timedelta(hours=_DEDUP_WINDOW_HOURS)
        row = await session.execute(
            text(
                """
                SELECT 1
                FROM   meter_alert_log
                WHERE  customer_id     = :customer_id
                  AND  bucket_type     = :bucket_type
                  AND  threshold_name  = :threshold_name
                  AND  fired_at        >= :window_start
                LIMIT  1
                """
            ).bindparams(
                customer_id=customer_id,
                bucket_type=bucket_type,
                threshold_name=threshold_name,
                window_start=window_start,
            )
        )
        return row.fetchone() is not None

    async def _record_alert(
        self,
        session: AsyncSession,
        alert: AlertFired,
    ) -> None:
        """
        Persist alert to meter_alert_log for deduplication and audit.
        C-059: every fired alert is traceable.
        C-063: no PII written - only UUIDs and enum strings.
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
                ON CONFLICT DO NOTHING
                """
            ).bindparams(
                id=uuid4(),
                customer_id=alert.customer_id,
                bucket_type=alert.bucket_type,
                threshold_name=alert.threshold_name,
                pct_consumed=alert.pct_consumed,
                scope=alert.scope,
                fired_at=alert.fired_at,
            )
        )
        await session.commit()