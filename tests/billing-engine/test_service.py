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
from sqlalchemy.pool import StaticPool

from meter.alert_policy import (
    AGENCY_POLICY,
    CUSTOMER_BUCKET_POLICY,
    PROCUREMENT_POLICY,
    AlertAction,
    AlertScope,
)
from meter.service import (
    MeterService,
    _IST_OFFSET,
    _IST_TZ,
    _current_billing_period_start,
    _is_quiet_hours,
    _now_ist,
)
from skeleton.wbe_interfaces import AlertFired, DailyScanResult, DepletionProjection


@pytest.fixture
async def in_memory_engine():
    """Create an in-memory SQLite engine with StaticPool for test isolation."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE thread_catalog (
                id TEXT PRIMARY KEY,
                thread_type TEXT NOT NULL,
                provider_account_id TEXT NOT NULL
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE provider_accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                balance_paise INTEGER DEFAULT 0
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE platform_cost_ledger (
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
        await conn.exec_driver_sql(
            """
            CREATE TABLE customer_wallets (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL UNIQUE
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE wallet_buckets (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                thread_type TEXT NOT NULL,
                balance_paise INTEGER NOT NULL,
                FOREIGN KEY (wallet_id) REFERENCES customer_wallets (id)
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE agency_sub_wallets (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL UNIQUE,
                quota_paise INTEGER,
                consumed_paise INTEGER DEFAULT 0
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE meter_alert_log (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                bucket_type TEXT NOT NULL,
                threshold_name TEXT NOT NULL,
                pct_consumed REAL NOT NULL,
                scope TEXT NOT NULL,
                fired_at TEXT NOT NULL,
                UNIQUE (customer_id, bucket_type, threshold_name, fired_at)
            )
            """
        )

    yield engine

    await engine.dispose()


@pytest.fixture
async def session_factory(in_memory_engine):
    """Provide async sessionmaker for tests."""
    async_session = async_sessionmaker(
        in_memory_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
async def meter_service(session_factory):
    """Create MeterService instance for testing."""
    return MeterService(session_factory=session_factory, redis_pool=None)


@pytest.fixture
async def test_customer_id():
    """Generate a test customer UUID."""
    return uuid4()


@pytest.fixture
async def test_provider_account_id():
    """Generate a test provider account UUID."""
    return uuid4()


@pytest.fixture
async def setup_test_data(session_factory, test_customer_id, test_provider_account_id):
    """Populate in-memory DB with test data."""
    async with session_factory() as session:
        # Insert provider account
        await session.execute(
            text(
                """
                INSERT INTO provider_accounts (id, name, active, balance_paise)
                VALUES (:id, :name, :active, :balance)
                """
            ).bindparams(
                id=str(test_provider_account_id),
                name="test-provider",
                active=1,
                balance=1000000,
            )
        )

        # Insert thread catalog entry
        await session.execute(
            text(
                """
                INSERT INTO thread_catalog (id, thread_type, provider_account_id)
                VALUES (:id, :thread_type, :provider_id)
                """
            ).bindparams(
                id=str(uuid4()),
                thread_type="GENIE",
                provider_id=str(test_provider_account_id),
            )
        )

        # Insert customer wallet
        wallet_id = str(uuid4())
        await session.execute(
            text(
                """
                INSERT INTO customer_wallets (id, customer_id)
                VALUES (:id, :customer_id)
                """
            ).bindparams(id=wallet_id, customer_id=str(test_customer_id))
        )

        # Insert wallet bucket
        await session.execute(
            text(
                """
                INSERT INTO wallet_buckets (id, wallet_id, thread_type, balance_paise)
                VALUES (:id, :wallet_id, :thread_type, :balance)
                """
            ).bindparams(
                id=str(uuid4()),
                wallet_id=wallet_id,
                thread_type="GENIE",
                balance=100000,
            )
        )

        await session.commit()


# ============================================================================
# Test: record_usage
# ============================================================================


@pytest.mark.asyncio
async def test_record_usage_success(
    meter_service, session_factory, setup_test_data, test_customer_id, test_provider_account_id
):
    """Test record_usage writes to platform_cost_ledger successfully."""
    await setup_test_data

    await meter_service.record_usage(
        customer_id=test_customer_id,
        thread_type="GENIE",
        amount_paise=5000,
    )

    async with session_factory() as session:
        row = await session.execute(
            text(
                """
                SELECT COUNT(*) as cnt
                FROM platform_cost_ledger
                WHERE customer_id = :customer_id
                  AND thread_type = :thread_type
                """
            ).bindparams(
                customer_id=str(test_customer_id),
                thread_type="GENIE",
            )
        )
        result = row.fetchone()
        assert result.cnt == 1


@pytest.mark.asyncio
async def test_record_usage_provider_not_found(
    meter_service, session_factory, test_customer_id
):
    """Test record_usage logs error when provider_account not found."""
    await meter_service.record_usage(
        customer_id=test_customer_id,
        thread_type="NONEXISTENT",
        amount_paise=5000,
    )

    async with session_factory() as session:
        row = await session.execute(
            text(
                """
                SELECT COUNT(*) as cnt
                FROM platform_cost_ledger
                WHERE customer_id = :customer_id
                """
            ).bindparams(customer_id=str(test_customer_id))
        )
        result = row.fetchone()
        assert result.cnt == 0


# ============================================================================
# Test: project_depletion
# ============================================================================


@pytest.mark.asyncio
async def test_project_depletion_success(
    meter_service, session_factory, setup_test_data, test_customer_id, test_provider_account_id
):
    """Test project_depletion computes days_remaining correctly."""
    await setup_test_data

    # Record 70000 paise of usage over 7 days (10000 per day burn rate)
    for _ in range(7):
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=10000,
        )

    result = await meter_service.project_depletion(
        customer_id=test_customer_id,
        thread_type="GENIE",
    )

    assert isinstance(result, DepletionProjection)
    assert result.daily_burn_rate_paise == pytest.approx(10000.0, rel=0.01)
    # balance=100000, daily_burn=10000, so days_remaining = 10
    assert result.days_remaining == pytest.approx(10.0, rel=0.01)


@pytest.mark.asyncio
async def test_project_depletion_no_burn(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test project_depletion when no usage recorded (infinite runway)."""
    await setup_test_data

    result = await meter_service.project_depletion(
        customer_id=test_customer_id,
        thread_type="GENIE",
    )

    assert result.days_remaining == float("inf")
    assert result.projected_empty_date == date(9999, 12, 31)


# ============================================================================
# Test: check_thresholds - Scope 1 (Customer Buckets)
# ============================================================================


@pytest.mark.asyncio
async def test_check_thresholds_scope1_warn_30(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test Scope 1: WARN_30 fires at 70% consumed (30% remaining)."""
    await setup_test_data

    # Consume 70000 out of 100000 paise
    for _ in range(7):
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=10000,
        )

    alerts = await meter_service.check_thresholds(customer_id=test_customer_id)

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "WARN_30"
    assert alerts[0].scope == "CUSTOMER_BUCKET"
    assert alerts[0].pct_consumed == pytest.approx(0.70, rel=0.01)


@pytest.mark.asyncio
async def test_check_thresholds_scope1_deduplication(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test Scope 1: deduplication prevents double-fire within 24h."""
    await setup_test_data

    # First threshold check fires WARN_30
    for _ in range(7):
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=10000,
        )

    alerts_1 = await meter_service.check_thresholds(customer_id=test_customer_id)
    assert len(alerts_1) == 1

    # Second check (within 24h dedup window) should not fire
    alerts_2 = await meter_service.check_thresholds(customer_id=test_customer_id)
    assert len(alerts_2) == 0


@pytest.mark.asyncio
async def test_check_thresholds_scope1_quiet_hours(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test Scope 1: quiet hours suppress NOTIFY actions."""
    await setup_test_data

    for _ in range(7):
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=10000,
        )

    # Mock _now_ist to return a time within quiet hours (23:00-06:00 IST)
    mock_now = datetime(2026, 8, 1, 23, 30, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=mock_now):
        # WARN_30 has bypass_quiet_hours=False, so it should be suppressed
        alerts = await meter_service.check_thresholds(customer_id=test_customer_id)
        assert len(alerts) == 0


@pytest.mark.asyncio
async def test_check_thresholds_scope1_bypass_quiet_hours(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test Scope 1: bypass_quiet_hours=True fires even in quiet hours."""
    await setup_test_data

    # Consume 99% to trigger WARN_10 which has bypass_quiet_hours=True
    for _ in range(7):
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=14100,
        )

    mock_now = datetime(2026, 8, 1, 23, 30, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=mock_now):
        alerts = await meter_service.check_thresholds(customer_id=test_customer_id)
        assert any(a.threshold_name == "WARN_10" for a in alerts)


# ============================================================================
# Test: check_thresholds - Scope 2 (Agency)
# ============================================================================


@pytest.mark.asyncio
async def test_check_thresholds_scope2_agency_success(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test Scope 2: AGENCY threshold fires at correct consumption %."""
    await setup_test_data

    async with session_factory() as session:
        # Insert agency sub-wallet with 100000 paise quota, 80000 consumed
        await session.execute(
            text(
                """
                INSERT INTO agency_sub_wallets
                    (id, customer_id, quota_paise, consumed_paise)
                VALUES (:id, :customer_id, :quota, :consumed)
                """
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(test_customer_id),
                quota=100000,
                consumed=80000,
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id=test_customer_id)

    # 80% consumed should trigger AGENCY_WARN_80
    agency_alerts = [a for a in alerts if a.scope == "AGENCY"]
    assert len(agency_alerts) >= 1
    assert any(a.threshold_name == "AGENCY_WARN_80" for a in agency_alerts)


@pytest.mark.asyncio
async def test_check_thresholds_scope2_agency_null_quota(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test Scope 2: NULL quota produces no alert."""
    await setup_test_data

    async with session_factory() as session:
        # Insert agency sub-wallet with NULL quota
        await session.execute(
            text(
                """
                INSERT INTO agency_sub_wallets
                    (id, customer_id, quota_paise, consumed_paise)
                VALUES (:id, :customer_id, :quota, :consumed)
                """
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(test_customer_id),
                quota=None,
                consumed=0,
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id=test_customer_id)

    agency_alerts = [a for a in alerts if a.scope == "AGENCY"]
    assert len(agency_alerts) == 0


# ============================================================================
# Test: check_thresholds - Scope 3 (Procurement)
# ============================================================================


@pytest.mark.asyncio
async def test_check_thresholds_scope3_procurement_p0(
    meter_service, session_factory, setup_test_data, test_provider_account_id
):
    """Test Scope 3: RUNWAY_P0 fires when <=7 days remaining."""
    await setup_test_data

    async with session_factory() as session:
        # Provider has 100000 paise balance
        # Simulate 14000 paise burned in last 7 days (2000/day) = 50 days remaining
        # We need <=7 days, so we need 14000 balance, 2000/day burn = 7 days
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        await session.execute(
            text(
                """
                UPDATE provider_accounts
                SET balance_paise = 14000
                WHERE id = :id
                """
            ).bindparams(id=str(test_provider_account_id))
        )

        # Insert cost ledger entries to create 7-day burn (14000 total / 7 days = 2000/day)
        for day_offset in range(7):
            recorded_at = now_utc - timedelta(days=day_offset)
            await session.execute(
                text(
                    """
                    INSERT INTO platform_cost_ledger
                        (id, customer_id, thread_type, provider_account_id,
                         marked_up_cost_inr_paise, recorded_at, billing_period_start)
                    VALUES (:id, :cid, :ttype, :pid, :cost, :at, :start)
                    """
                ).bindparams(
                    id=str(uuid4()),
                    cid=str(uuid4()),
                    ttype="GENIE",
                    pid=str(test_provider_account_id),
                    cost=2000,
                    at=recorded_at,
                    start=period_start,
                )
            )

        await session.commit()

    test_customer_id = uuid4()
    alerts = await meter_service.check_thresholds(customer_id=test_customer_id)

    procurement_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    assert any(a.threshold_name == "RUNWAY_P0" for a in procurement_alerts)


@pytest.mark.asyncio
async def test_check_thresholds_scope3_procurement_emergency(
    meter_service, session_factory, setup_test_data, test_provider_account_id
):
    """Test Scope 3: RUNWAY_EMERGENCY fires when <=1 day remaining."""
    await setup_test_data

    async with session_factory() as session:
        # 3000 paise balance, 3000/day burn = 1 day remaining
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        await session.execute(
            text(
                """
                UPDATE provider_accounts
                SET balance_paise = 3000
                WHERE id = :id
                """
            ).bindparams(id=str(test_provider_account_id))
        )

        for day_offset in range(7):
            recorded_at = now_utc - timedelta(days=day_offset)
            await session.execute(
                text(
                    """
                    INSERT INTO platform_cost_ledger
                        (id, customer_id, thread_type, provider_account_id,
                         marked_up_cost_inr_paise, recorded_at, billing_period_start)
                    VALUES (:id, :cid, :ttype, :pid, :cost, :at, :start)
                    """
                ).bindparams(
                    id=str(uuid4()),
                    cid=str(uuid4()),
                    ttype="GENIE",
                    pid=str(test_provider_account_id),
                    cost=3000,
                    at=recorded_at,
                    start=period_start,
                )
            )

        await session.commit()

    test_customer_id = uuid4()
    alerts = await meter_service.check_thresholds(customer_id=test_customer_id)

    procurement_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    assert any(a.threshold_name == "RUNWAY_EMERGENCY" for a in procurement_alerts)


# ============================================================================
# Test: run_daily_scan
# ============================================================================


@pytest.mark.asyncio
async def test_run_daily_scan_success(
    meter_service, session_factory, setup_test_data, test_customer_id
):
    """Test run_daily_scan calls check_thresholds for all active customers."""
    await setup_test_data

    # Consume 70% to trigger WARN_30
    for _ in range(7):
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=10000,
        )

    result = await meter_service.run_daily_scan()

    assert isinstance(result, DailyScanResult)
    assert result.customers_scanned >= 1
    assert result.alerts_sent >= 1


@pytest.mark.asyncio
async def test_run_daily_scan_empty_wallets(meter_service, session_factory):
    """Test run_daily_scan with no active customers."""
    result = await meter_service.run_daily_scan()

    assert result.customers_scanned == 0
    assert result.alerts_sent == 0


# ============================================================================
# Test: CCT-BILLINGLOOP-01 Scenario
# ============================================================================


@pytest.mark.asyncio
async def test_cct_billingloop_01_wallet_zero(
    meter_service, session_factory, test_customer_id
):
    """
    CCT-BILLINGLOOP-01: AD wallet hits zero -> alerts_sent == 1 type AD_WALLET_BELOW_MINIMUM.
    """
    provider_id = uuid4()

    async with session_factory() as session:
        # Setup provider
        await session.execute(
            text(
                """
                INSERT INTO provider_accounts (id, name, active, balance_paise)
                VALUES (:id, :name, :active, :balance)
                """
            ).bindparams(
                id=str(provider_id),
                name="test-provider",
                active=1,
                balance=1000000,
            )
        )

        # Setup thread catalog
        await session.execute(
            text(
                """
                INSERT INTO thread_catalog (id, thread_type, provider_account_id)
                VALUES (:id, :thread_type, :provider_id)
                """
            ).bindparams(
                id=str(uuid4()),
                thread_type="GENIE",
                provider_id=str(provider_id),
            )
        )

        # Setup wallet with zero balance
        wallet_id = str(uuid4())
        await session.execute(
            text(
                """
                INSERT INTO customer_wallets (id, customer_id)
                VALUES (:id, :customer_id)
                """
            ).bindparams(id=wallet_id, customer_id=str(test_customer_id))
        )

        await session.execute(
            text(
                """
                INSERT INTO wallet_buckets (id, wallet_id, thread_type, balance_paise)
                VALUES (:id, :wallet_id, :thread_type, :balance)
                """
            ).bindparams(
                id=str(uuid4()),
                wallet_id=wallet_id,
                thread_type="GENIE",
                balance=0,  # Zero balance
            )
        )

        # Record some usage (100% consumed)
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        await session.execute(
            text(
                """
                INSERT INTO platform_cost_ledger
                    (id, customer_id, thread_type, provider_account_id,
                     marked_up_cost_inr_paise, recorded_at, billing_period_start)
                VALUES (:id, :cid, :ttype, :pid, :cost, :at, :start)
                """
            ).bindparams(
                id=str(uuid4()),
                cid=str(test_customer_id),
                ttype="GENIE",
                pid=str(provider_id),
                cost=1,
                at=now_utc,
                start=period_start,
            )
        )

        await session.commit()

    alerts = await meter_service.check_thresholds(customer_id=test_customer_id)

    # Should fire AD_WALLET_BELOW_MINIMUM (100% consumed triggers it)
    below_min_alerts = [
        a
        for a in alerts
        if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"
        and a.scope == "CUSTOMER_BUCKET"
    ]
    assert len(below_min_alerts) == 1
    assert below_min_alerts[0].pct_consumed == pytest.approx(1.0, rel=0.01)


# ============================================================================
# Test: Helper functions
# ============================================================================


def test_is_quiet_hours_within_window():
    """Test _is_quiet_hours detects times within quiet window (23:00-06:00)."""
    policy = CUSTOMER_BUCKET_POLICY
    # 23:30 IST should be within quiet hours
    time_2330 = datetime(2026, 8, 1, 23, 30, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(policy, time_2330)


def test_is_quiet_hours_outside_window():
    """Test _is_quiet_hours detects times outside quiet window."""
    policy = CUSTOMER_BUCKET_POLICY
    # 12:00 IST should be outside quiet hours
    time_1200 = datetime(2026, 8, 1, 12, 0, 0, tzinfo=_IST_TZ)
    assert not _is_quiet_hours(policy, time_1200)


def test_current_billing_period_start():
    """Test _current_billing_period_start returns first day of month."""
    now_utc = datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    start = _current_billing_period_start(now_utc)
    assert start == date(2026, 8, 1)


@pytest.mark.asyncio
async def test_record_usage_cancelled_error(
    meter_service, session_factory, test_customer_id
):
    """Test record_usage re-raises CancelledError."""
    with patch.object(session_factory, "__call__", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await meter_service.record_usage(
                customer_id=test_customer_id,
                thread_type="GENIE",
                amount_paise=5000,
            )


@pytest.mark.asyncio
async def test_project_depletion_cancelled_error(
    meter_service, session_factory, test_customer_id
):
    """Test project_depletion re-raises CancelledError."""
    with patch.object(session_factory, "__call__", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await meter_service.project_depletion(
                customer_id=test_customer_id,
                thread_type="GENIE",
            )


@pytest.mark.asyncio
async def test_check_thresholds_cancelled_error(
    meter_service, session_factory, test_customer_id
):
    """Test check_thresholds re-raises CancelledError."""
    with patch.object(session_factory, "__call__", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await meter_service.check_thresholds(customer_id=test_customer_id)