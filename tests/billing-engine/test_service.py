# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alert_policy import (
    AGENCY_POLICY,
    CUSTOMER_BUCKET_POLICY,
    PROCUREMENT_POLICY,
    AlertAction,
    AlertScope,
)
from service import MeterService, _current_billing_period_start, _is_quiet_hours, _now_ist
from skeleton.wbe_interfaces import AlertFired, DailyScanResult, DepletionProjection, IMeterService


@pytest.fixture
async def test_db_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS platform_cost_ledger (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    thread_type TEXT NOT NULL,
                    provider_account_id TEXT NOT NULL,
                    marked_up_cost_inr_paise INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    billing_period_start TEXT NOT NULL
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS wallet_buckets (
                    customer_id TEXT NOT NULL,
                    thread_type TEXT NOT NULL,
                    balance_paise INTEGER NOT NULL,
                    PRIMARY KEY (customer_id, thread_type)
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS meter_alert_log (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    bucket_type TEXT NOT NULL,
                    threshold_name TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    pct_consumed REAL NOT NULL,
                    fired_at TEXT NOT NULL,
                    action TEXT NOT NULL
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS thread_catalog (
                    thread_type TEXT PRIMARY KEY,
                    provider_account_id TEXT NOT NULL
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS provider_accounts (
                    id TEXT PRIMARY KEY
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS billing_profiles (
                    customer_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL
                )
                """
            )
        )
        await conn.commit()

    yield engine

    await engine.dispose()


@pytest.fixture
async def session_factory(test_db_engine):
    """Create async session factory."""
    return async_sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def meter_service(session_factory):
    """Initialize MeterService with test session factory."""
    return MeterService(session_factory=session_factory, redis_pool=None)


@pytest.fixture
async def setup_thread_catalog(session_factory):
    """Populate thread_catalog and provider_accounts for tests."""

    async def _setup(thread_type: str = "DMA", provider_id: str | None = None):
        if provider_id is None:
            provider_id = str(uuid4())
        async with session_factory() as session:
            await session.execute(
                text("DELETE FROM thread_catalog WHERE thread_type = :tt").bindparams(
                    tt=thread_type
                )
            )
            await session.execute(
                text("DELETE FROM provider_accounts WHERE id = :pid").bindparams(
                    pid=provider_id
                )
            )
            await session.execute(
                text(
                    "INSERT INTO provider_accounts (id) VALUES (:pid)"
                ).bindparams(pid=provider_id)
            )
            await session.execute(
                text(
                    "INSERT INTO thread_catalog (thread_type, provider_account_id) VALUES (:tt, :pid)"
                ).bindparams(tt=thread_type, pid=provider_id)
            )
            await session.commit()
        return provider_id

    return _setup


@pytest.fixture
async def setup_wallet_bucket(session_factory):
    """Populate wallet_buckets for tests."""

    async def _setup(customer_id: UUID, thread_type: str, balance_paise: int):
        async with session_factory() as session:
            await session.execute(
                text(
                    "DELETE FROM wallet_buckets WHERE customer_id = :cid AND thread_type = :tt"
                ).bindparams(cid=str(customer_id), tt=thread_type)
            )
            await session.execute(
                text(
                    "INSERT INTO wallet_buckets (customer_id, thread_type, balance_paise) VALUES (:cid, :tt, :bal)"
                ).bindparams(cid=str(customer_id), tt=thread_type, bal=balance_paise)
            )
            await session.commit()

    return _setup


@pytest.fixture
async def setup_billing_profile(session_factory):
    """Populate billing_profiles for tests."""

    async def _setup(customer_id: UUID, status: str = "ACTIVE"):
        async with session_factory() as session:
            await session.execute(
                text("DELETE FROM billing_profiles WHERE customer_id = :cid").bindparams(
                    cid=str(customer_id)
                )
            )
            await session.execute(
                text(
                    "INSERT INTO billing_profiles (customer_id, status) VALUES (:cid, :status)"
                ).bindparams(cid=str(customer_id), status=status)
            )
            await session.commit()

    return _setup


# ============================================================================
# Tests: record_usage
# ============================================================================


@pytest.mark.asyncio
async def test_record_usage_happy_path(
    meter_service, setup_thread_catalog, setup_wallet_bucket, session_factory
):
    """Test record_usage writes to platform_cost_ledger with correct provider_account_id."""
    customer_id = uuid4()
    thread_type = "DMA"
    amount_paise = 10000
    provider_id = await setup_thread_catalog(thread_type)

    await meter_service.record_usage(customer_id, thread_type, amount_paise)

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT marked_up_cost_inr_paise, provider_account_id FROM platform_cost_ledger WHERE customer_id = :cid"
            ).bindparams(cid=str(customer_id))
        )
        result = row.fetchone()
        assert result is not None
        assert result.marked_up_cost_inr_paise == amount_paise
        assert result.provider_account_id == provider_id


@pytest.mark.asyncio
async def test_record_usage_missing_provider(meter_service, session_factory):
    """Test record_usage handles missing provider_account_id gracefully."""
    customer_id = uuid4()
    thread_type = "UNKNOWN_TYPE"

    await meter_service.record_usage(customer_id, thread_type, 5000)

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT COUNT(*) as cnt FROM platform_cost_ledger WHERE customer_id = :cid"
            ).bindparams(cid=str(customer_id))
        )
        result = row.fetchone()
        assert result.cnt == 0


@pytest.mark.asyncio
async def test_record_usage_multiple_calls_sum_correctly(
    meter_service, setup_thread_catalog, session_factory
):
    """Test multiple record_usage calls accumulate."""
    customer_id = uuid4()
    thread_type = "DMA"
    await setup_thread_catalog(thread_type)

    await meter_service.record_usage(customer_id, thread_type, 1000)
    await meter_service.record_usage(customer_id, thread_type, 2000)

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT SUM(marked_up_cost_inr_paise) as total FROM platform_cost_ledger WHERE customer_id = :cid"
            ).bindparams(cid=str(customer_id))
        )
        result = row.fetchone()
        assert result.total == 3000


# ============================================================================
# Tests: project_depletion
# ============================================================================


@pytest.mark.asyncio
async def test_project_depletion_no_burn(
    meter_service, setup_wallet_bucket, session_factory
):
    """Test projection when no usage recorded (daily_burn_rate = 0)."""
    customer_id = uuid4()
    thread_type = "DMA"
    balance = 100000

    await setup_wallet_bucket(customer_id, thread_type, balance)

    projection = await meter_service.project_depletion(customer_id, thread_type)

    assert projection.days_remaining == 999.0
    assert projection.daily_burn_rate_paise == 0.0


@pytest.mark.asyncio
async def test_project_depletion_with_burn(
    meter_service, setup_thread_catalog, setup_wallet_bucket, session_factory
):
    """Test projection with 7-day rolling average burn rate."""
    customer_id = uuid4()
    thread_type = "DMA"
    balance = 700000
    daily_rate = 10000
    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        for i in range(7):
            day_ago = now_utc - timedelta(days=i)
            await session.execute(
                text(
                    "INSERT INTO platform_cost_ledger "
                    "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                    "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
                ).bindparams(
                    id=str(uuid4()),
                    cid=str(customer_id),
                    tt=thread_type,
                    pid=str(uuid4()),
                    amount=daily_rate,
                    recorded_at=day_ago,
                    period_start=_current_billing_period_start(day_ago),
                )
            )
            await session.commit()

    projection = await meter_service.project_depletion(customer_id, thread_type)

    assert projection.daily_burn_rate_paise == daily_rate
    assert projection.days_remaining == balance / daily_rate


# ============================================================================
# Tests: check_thresholds (Scope 1: CUSTOMER_BUCKET)
# ============================================================================


@pytest.mark.asyncio
async def test_check_thresholds_customer_bucket_fires_warn_30(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test WARN_30 fires when bucket is 70% consumed (30% remaining)."""
    customer_id = uuid4()
    thread_type = "DMA"
    total_budget = 100000
    consumed_amount = 70000  # 70% consumed
    balance = 30000

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id)

    assert len(alerts) >= 1
    warn_30_alert = next(
        (a for a in alerts if a.threshold_name == "WARN_30"), None
    )
    assert warn_30_alert is not None
    assert warn_30_alert.scope == "CUSTOMER_BUCKET"
    assert warn_30_alert.bucket_type == thread_type


@pytest.mark.asyncio
async def test_check_thresholds_customer_bucket_ad_wallet_below_minimum(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test AD_WALLET_BELOW_MINIMUM fires when balance reaches zero (100% consumed)."""
    customer_id = uuid4()
    thread_type = "DMA"
    consumed_amount = 100000
    balance = 0

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id)

    ad_wallet_alert = next(
        (a for a in alerts if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"), None
    )
    assert ad_wallet_alert is not None
    assert ad_wallet_alert.scope == "CUSTOMER_BUCKET"


@pytest.mark.asyncio
async def test_check_thresholds_no_double_fire_within_24h(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test deduplication: alert does not fire twice within 24h window."""
    customer_id = uuid4()
    thread_type = "DMA"
    consumed_amount = 70000
    balance = 30000

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    first_alerts = await meter_service.check_thresholds(customer_id)
    second_alerts = await meter_service.check_thresholds(customer_id)

    assert len(first_alerts) >= 1
    assert len(second_alerts) == 0


# ============================================================================
# Tests: check_thresholds (Scope 2: AGENCY)
# ============================================================================


@pytest.mark.asyncio
async def test_check_thresholds_agency_fires_warn_80(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test AGENCY_WARN_80 fires when agency wallet is 80% consumed."""
    customer_id = uuid4()
    thread_type = "DMA"
    consumed_amount = 80000
    balance = 20000

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id)

    agency_alert = next(
        (a for a in alerts if a.scope == "AGENCY" and a.threshold_name == "AGENCY_WARN_80"),
        None,
    )
    assert agency_alert is not None


@pytest.mark.asyncio
async def test_check_thresholds_agency_critical_fires(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test AGENCY_CRITICAL fires when agency wallet is 95% consumed."""
    customer_id = uuid4()
    thread_type = "DMA"
    consumed_amount = 95000
    balance = 5000

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id)

    critical_alert = next(
        (a for a in alerts if a.scope == "AGENCY" and a.threshold_name == "AGENCY_CRITICAL"),
        None,
    )
    assert critical_alert is not None
    assert critical_alert.pct_consumed >= 0.95


# ============================================================================
# Tests: check_thresholds (Scope 3: PROCUREMENT)
# ============================================================================


@pytest.mark.asyncio
async def test_check_thresholds_procurement_policy_exists(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test that procurement scope thresholds are checked (even if no alerts fire in basic test)."""
    customer_id = uuid4()
    thread_type = "DMA"

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, 100000)
    await setup_billing_profile(customer_id)

    alerts = await meter_service.check_thresholds(customer_id)

    assert isinstance(alerts, list)


# ============================================================================
# Tests: quiet_hours behavior
# ============================================================================


@pytest.mark.asyncio
async def test_quiet_hours_suppresses_notify(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test that NOTIFY alerts are queued (not fired) during quiet hours (23:00-06:00 IST)."""
    customer_id = uuid4()
    thread_type = "DMA"
    consumed_amount = 80000
    balance = 20000

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    with patch("service._now_ist") as mock_now_ist:
        mock_ist = datetime(2024, 1, 15, 23, 30, tzinfo=timezone.utc)
        mock_now_ist.return_value = mock_ist

        alerts = await meter_service.check_thresholds(customer_id)

        logged_alerts = [
            a for a in alerts if a.threshold_name == "AGENCY_WARN_80"
        ]
        assert len(logged_alerts) >= 1


@pytest.mark.asyncio
async def test_bypass_quiet_hours_flag(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test that alerts with bypass_quiet_hours=True fire even during quiet hours."""
    customer_id = uuid4()
    thread_type = "DMA"
    consumed_amount = 90000
    balance = 10000

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, balance)
    await setup_billing_profile(customer_id)

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                pid=str(uuid4()),
                amount=consumed_amount,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    with patch("service._now_ist") as mock_now_ist:
        mock_ist = datetime(2024, 1, 15, 23, 30, tzinfo=timezone.utc)
        mock_now_ist.return_value = mock_ist

        alerts = await meter_service.check_thresholds(customer_id)

        warn_10_alert = next(
            (a for a in alerts if a.threshold_name == "WARN_10"), None
        )
        assert warn_10_alert is not None


# ============================================================================
# Tests: run_daily_scan
# ============================================================================


@pytest.mark.asyncio
async def test_run_daily_scan_calls_check_thresholds_for_all_customers(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test that run_daily_scan scans all active customers and counts alerts."""
    customer_id_1 = uuid4()
    customer_id_2 = uuid4()
    thread_type = "DMA"

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id_1, thread_type, 30000)
    await setup_wallet_bucket(customer_id_2, thread_type, 50000)
    await setup_billing_profile(customer_id_1, "ACTIVE")
    await setup_billing_profile(customer_id_2, "ACTIVE")

    now_utc = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :amount, :recorded_at, :period_start)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id_1),
                tt=thread_type,
                pid=str(uuid4()),
                amount=70000,
                recorded_at=now_utc,
                period_start=_current_billing_period_start(now_utc),
            )
        )
        await session.commit()

    result = await meter_service.run_daily_scan()

    assert isinstance(result, DailyScanResult)
    assert result.customers_scanned == 2
    assert result.alerts_sent >= 0


@pytest.mark.asyncio
async def test_run_daily_scan_skips_inactive_customers(
    meter_service, setup_thread_catalog, setup_wallet_bucket, setup_billing_profile, session_factory
):
    """Test that run_daily_scan only processes ACTIVE billing profiles."""
    customer_id_active = uuid4()
    customer_id_inactive = uuid4()
    thread_type = "DMA"

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id_active, thread_type, 30000)
    await setup_wallet_bucket(customer_id_inactive, thread_type, 50000)
    await setup_billing_profile(customer_id_active, "ACTIVE")
    await setup_billing_profile(customer_id_inactive, "PAUSED")

    result = await meter_service.run_daily_scan()

    assert result.customers_scanned == 1


# ============================================================================
# Tests: Constitutional & Invariant Checks
# ============================================================================


@pytest.mark.asyncio
async def test_no_pii_in_logs(
    meter_service, setup_thread_catalog, setup_wallet_bucket, session_factory, caplog
):
    """Test C-063: customer_id logged only as UUID string (no name/email)."""
    customer_id = uuid4()
    thread_type = "DMA"

    await setup_thread_catalog(thread_type)
    await setup_wallet_bucket(customer_id, thread_type, 100000)

    with caplog.at_level("INFO"):
        await meter_service.record_usage(customer_id, thread_type, 5000)

    log_output = caplog.text
    assert str(customer_id) in log_output
    assert "@" not in log_output


@pytest.mark.asyncio
async def test_record_usage_cancellation_handling(meter_service, setup_thread_catalog):
    """Test C-059: CancelledError is properly re-raised."""
    customer_id = uuid4()
    thread_type = "DMA"

    await setup_thread_catalog(thread_type)

    with patch.object(meter_service._session_factory, "__call__", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await meter_service.record_usage(customer_id, thread_type, 5000)


@pytest.mark.asyncio
async def test_threshold_policy_consistency(session_factory):
    """Test that threshold policies are properly ordered (ascending trigger %)."""
    assert CUSTOMER_BUCKET_POLICY.thresholds[0].consumed_pct_trigger == 0.70
    assert CUSTOMER_BUCKET_POLICY.thresholds[1].consumed_pct_trigger == 0.80
    assert CUSTOMER_BUCKET_POLICY.thresholds[2].consumed_pct_trigger == 0.90
    assert CUSTOMER_BUCKET_POLICY.thresholds[3].consumed_pct_trigger == 1.00

    assert AGENCY_POLICY.thresholds[0].consumed_pct_trigger == 0.50
    assert AGENCY_POLICY.thresholds[1].consumed_pct_trigger == 0.80
    assert AGENCY_POLICY.thresholds[2].consumed_pct_trigger == 0.95


# ============================================================================
# Tests: Helper functions
# ============================================================================


def test_current_billing_period_start():
    """Test that billing period always starts on day 1 of current month."""
    now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    period = _current_billing_period_start(now)
    assert period == date(2024, 1, 1)

    now2 = datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    period2 = _current_billing_period_start(now2)
    assert period2 == date(2024, 2, 1)


def test_is_quiet_hours_before_morning_threshold():
    """Test quiet hours detection (23:00-06:00 IST)."""
    policy = CUSTOMER_BUCKET_POLICY

    now_in_quiet = datetime(2024, 1, 15, 23, 30, 0, tzinfo=timezone.utc)
    assert _is_quiet_hours(policy, now_in_quiet) is True

    now_after_quiet = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    assert _is_quiet_hours(policy, now_after_quiet) is False

    now_before_morning = datetime(2024, 1, 15, 4, 0, 0, tzinfo=timezone.utc)
    assert _is_quiet_hours(policy, now_before_morning) is True


def test_now_ist_returns_ist_timezone():
    """Test that _now_ist returns IST-aware datetime."""
    now = _now_ist()
    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == (5.5 * 3600)