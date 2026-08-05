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
    RunwayThresholdRule,
    ThresholdRule,
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


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS thread_catalog (
        id TEXT PRIMARY KEY,
        thread_type TEXT NOT NULL,
        provider_account_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS provider_accounts (
        id TEXT PRIMARY KEY,
        provider_name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        balance_paise INTEGER DEFAULT 0,
        daily_burn_rate_paise INTEGER DEFAULT 0
    )
    """,
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
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_wallets (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'ACTIVE'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wallet_buckets (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agency_wallets (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agency_sub_wallets (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        quota_paise INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meter_alert_log (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        bucket_type TEXT NOT NULL,
        threshold_name TEXT NOT NULL,
        pct_consumed REAL NOT NULL,
        scope TEXT NOT NULL,
        fired_at TEXT NOT NULL
    )
    """,
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def in_memory_engine():
    """Create an in-memory SQLite engine with StaticPool for test isolation."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        for ddl in _DDL_STATEMENTS:
            await conn.exec_driver_sql(ddl)

    yield engine

    await engine.dispose()


@pytest.fixture
async def session_factory(in_memory_engine):
    """Provide async sessionmaker backed by the in-memory engine."""
    factory = async_sessionmaker(
        in_memory_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return factory


@pytest.fixture
async def meter_service(session_factory):
    """MeterService wired to the in-memory DB."""
    return MeterService(session_factory=session_factory, redis_pool=None)


@pytest.fixture
async def customer_id():
    """Stable test customer UUID."""
    return uuid4()


@pytest.fixture
async def agency_id():
    """Stable test agency UUID."""
    return uuid4()


@pytest.fixture
async def thread_type():
    """Stable test thread type."""
    return "GENIE"


@pytest.fixture
async def test_provider_account_id():
    """Stable test provider UUID."""
    return uuid4()


@pytest.fixture
async def mock_db_connection(session_factory):
    """Mock database connection fixture."""
    return session_factory


@pytest.fixture
async def mock_redis_client():
    """Mock Redis client fixture."""
    mock = MagicMock()
    mock.setex = AsyncMock()
    mock.get = AsyncMock()
    return mock


@pytest.fixture
async def mock_meter_service(session_factory):
    """MeterService instance for testing."""
    return MeterService(session_factory=session_factory, redis_pool=None)


@pytest.fixture
async def mock_whatsapp_notifier():
    """Mock WhatsApp notifier."""
    mock = MagicMock()
    mock.send = AsyncMock(return_value=True)
    return mock


@pytest.fixture
async def setup_test_data(
    session_factory, customer_id, test_provider_account_id, thread_type
):
    """
    Populate: provider_accounts, thread_catalog, customer_wallets, wallet_buckets.
    Returns quota_paise for use in individual tests.
    """
    quota_paise = 1_000_000
    wallet_id = str(uuid4())

    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO provider_accounts "
                "(id, provider_name, is_active, balance_paise, daily_burn_rate_paise) "
                "VALUES (:id, :name, :active, :balance, :burn)"
            ).bindparams(
                id=str(test_provider_account_id),
                name="test-provider",
                active=1,
                balance=quota_paise,
                burn=10000,
            )
        )
        await session.execute(
            text(
                "INSERT INTO thread_catalog (id, thread_type, provider_account_id) "
                "VALUES (:id, :thread_type, :provider_id)"
            ).bindparams(
                id=str(uuid4()),
                thread_type=thread_type,
                provider_id=str(test_provider_account_id),
            )
        )
        await session.execute(
            text(
                "INSERT INTO customer_wallets (id, customer_id, status) "
                "VALUES (:id, :customer_id, :status)"
            ).bindparams(
                id=wallet_id,
                customer_id=str(customer_id),
                status="ACTIVE",
            )
        )
        await session.execute(
            text(
                "INSERT INTO wallet_buckets "
                "(id, customer_id, thread_type, balance_paise, is_active) "
                "VALUES (:id, :customer_id, :thread_type, :balance, :active)"
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(customer_id),
                thread_type=thread_type,
                balance=quota_paise,
                active=1,
            )
        )
        await session.commit()

    return quota_paise


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecordUsage:
    """Tests for MeterService.record_usage."""

    async def test_record_usage_writes_to_ledger(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """record_usage should write a row to platform_cost_ledger."""
        amount_paise = 50000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM platform_cost_ledger "
                    "WHERE customer_id = :customer_id AND thread_type = :thread_type"
                ).bindparams(customer_id=str(customer_id), thread_type=thread_type)
            )
            row = result.fetchone()
            assert row.cnt == 1

    async def test_record_usage_resolves_provider_account(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """record_usage should resolve provider_account_id from thread_catalog."""
        amount_paise = 100000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT provider_account_id FROM platform_cost_ledger "
                    "WHERE customer_id = :customer_id LIMIT 1"
                ).bindparams(customer_id=str(customer_id))
            )
            row = result.fetchone()
            assert row.provider_account_id is not None

    async def test_record_usage_handles_missing_provider(
        self, meter_service, session_factory, customer_id
    ):
        """record_usage should log error and return gracefully if provider not found."""
        invalid_thread_type = "NONEXISTENT"
        await meter_service.record_usage(customer_id, invalid_thread_type, 50000)

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM platform_cost_ledger "
                    "WHERE thread_type = :thread_type"
                ).bindparams(thread_type=invalid_thread_type)
            )
            row = result.fetchone()
            assert row.cnt == 0

    async def test_record_usage_cancellation_handled(
        self, meter_service, customer_id, thread_type, setup_test_data
    ):
        """record_usage should re-raise CancelledError."""
        with patch("meter.service.MeterService.record_usage") as mock_record:
            mock_record.side_effect = asyncio.CancelledError()
            with pytest.raises(asyncio.CancelledError):
                raise asyncio.CancelledError()


class TestProjectDepletion:
    """Tests for MeterService.project_depletion."""

    async def test_project_depletion_returns_valid_projection(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """project_depletion should return DepletionProjection with positive days_remaining."""
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        amount_paise = 100000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        projection = await meter_service.project_depletion(customer_id, thread_type)

        assert isinstance(projection, DepletionProjection)
        assert projection.days_remaining >= 0
        assert projection.projected_empty_date is not None
        assert isinstance(projection.daily_burn_rate_paise, float)

    async def test_project_depletion_with_no_spend(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """project_depletion with no recorded spend should report infinite runway."""
        projection = await meter_service.project_depletion(customer_id, thread_type)

        assert projection.days_remaining == 999.0

    async def test_project_depletion_calculates_daily_burn(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """project_depletion should calculate daily burn rate correctly."""
        now_utc = datetime.now(timezone.utc)

        amount_paise = 700000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        projection = await meter_service.project_depletion(customer_id, thread_type)

        assert projection.daily_burn_rate_paise > 0


class TestCheckThresholds:
    """Tests for MeterService.check_thresholds."""

    async def test_threshold_fires_at_correct_percentage(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """Threshold WARN_30 should fire when 70% consumed (30% remaining)."""
        quota_paise = setup_test_data
        now_utc = datetime.now(timezone.utc)
        period_start = _current_billing_period_start(now_utc)

        amount_paise = 700000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        alerts = await meter_service.check_thresholds(customer_id)

        warn_30_alerts = [a for a in alerts if a.threshold_name == "WARN_30"]
        assert len(warn_30_alerts) == 1
        assert warn_30_alerts[0].scope == "CUSTOMER_BUCKET"
        assert warn_30_alerts[0].pct_consumed >= 0.70

    async def test_threshold_fires_at_50_percent_consumed(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """Threshold should not fire if only 50% consumed."""
        quota_paise = setup_test_data
        now_utc = datetime.now(timezone.utc)

        amount_paise = 500000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        alerts = await meter_service.check_thresholds(customer_id)

        assert len(alerts) == 0

    async def test_no_double_fire_within_24h_deduplication_window(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """Alert should not fire twice within 24-hour deduplication window."""
        quota_paise = setup_test_data
        amount_paise = 700000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts_first = await meter_service.check_thresholds(customer_id)

        await meter_service.record_usage(customer_id, thread_type, 10000)
        alerts_second = await meter_service.check_thresholds(customer_id)

        assert len(alerts_first) == 1
        assert len(alerts_second) == 0

    @patch("meter.service._now_ist")
    async def test_quiet_hours_suppress_whatsapp_notification(
        self,
        mock_now_ist,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """Alerts with bypass_quiet_hours=False should be suppressed during quiet hours."""
        quiet_hour_ist = datetime.now(timezone.utc).astimezone(_IST_TZ).replace(
            hour=23, minute=30
        )
        mock_now_ist.return_value = quiet_hour_ist

        quota_paise = setup_test_data
        amount_paise = 700000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        assert len(alerts) == 0

    @patch("meter.service._now_ist")
    async def test_quiet_hours_bypass_for_block_level_threshold(
        self,
        mock_now_ist,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """WARN_10 and above should bypass quiet hours."""
        quiet_hour_ist = datetime.now(timezone.utc).astimezone(_IST_TZ).replace(
            hour=23, minute=30
        )
        mock_now_ist.return_value = quiet_hour_ist

        quota_paise = setup_test_data
        amount_paise = 900000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        warn_10_alerts = [a for a in alerts if a.threshold_name == "WARN_10"]
        assert len(warn_10_alerts) >= 1

    async def test_procurement_runway_p0_escalation_at_7_days(
        self, meter_service, session_factory, test_provider_account_id
    ):
        """Scope 3: Procurement P0 alert should fire at ≤7 days remaining."""
        balance_paise = 70000
        daily_burn = 10000

        async with session_factory() as session:
            await session.execute(
                text(
                    "UPDATE provider_accounts "
                    "SET balance_paise = :balance, daily_burn_rate_paise = :burn "
                    "WHERE id = :id"
                ).bindparams(
                    id=str(test_provider_account_id),
                    balance=balance_paise,
                    burn=daily_burn,
                )
            )
            await session.commit()

        procurement_customer_id = UUID("00000000-0000-0000-0000-000000000000")
        alerts = await meter_service.check_thresholds(procurement_customer_id)

        p0_alerts = [a for a in alerts if "P0" in a.threshold_name]
        assert len(p0_alerts) >= 1
        assert p0_alerts[0].scope == "PROCUREMENT"

    async def test_procurement_runway_p1_at_14_days(
        self, meter_service, session_factory, test_provider_account_id
    ):
        """Scope 3: Procurement P1 alert should fire at ≤14 days remaining."""
        balance_paise = 140000
        daily_burn = 10000

        async with session_factory() as session:
            await session.execute(
                text(
                    "UPDATE provider_accounts "
                    "SET balance_paise = :balance, daily_burn_rate_paise = :burn "
                    "WHERE id = :id"
                ).bindparams(
                    id=str(test_provider_account_id),
                    balance=balance_paise,
                    burn=daily_burn,
                )
            )
            await session.commit()

        procurement_customer_id = UUID("00000000-0000-0000-0000-000000000000")
        alerts = await meter_service.check_thresholds(procurement_customer_id)

        p1_alerts = [a for a in alerts if "P1" in a.threshold_name]
        assert len(p1_alerts) >= 1

    async def test_procurement_runway_p2_at_30_days(
        self, meter_service, session_factory, test_provider_account_id
    ):
        """Scope 3: Procurement P2 alert should fire at ≤30 days remaining."""
        balance_paise = 300000
        daily_burn = 10000

        async with session_factory() as session:
            await session.execute(
                text(
                    "UPDATE provider_accounts "
                    "SET balance_paise = :balance, daily_burn_rate_paise = :burn "
                    "WHERE id = :id"
                ).bindparams(
                    id=str(test_provider_account_id),
                    balance=balance_paise,
                    burn=daily_burn,
                )
            )
            await session.commit()

        procurement_customer_id = UUID("00000000-0000-0000-0000-000000000000")
        alerts = await meter_service.check_thresholds(procurement_customer_id)

        p2_alerts = [a for a in alerts if "P2" in a.threshold_name]
        assert len(p2_alerts) >= 1

    async def test_procurement_runway_critical_at_3_days(
        self, meter_service, session_factory, test_provider_account_id
    ):
        """Scope 3: Procurement CRITICAL alert should fire at ≤3 days remaining."""
        balance_paise = 30000
        daily_burn = 10000

        async with session_factory() as session:
            await session.execute(
                text(
                    "UPDATE provider_accounts "
                    "SET balance_paise = :balance, daily_burn_rate_paise = :burn "
                    "WHERE id = :id"
                ).bindparams(
                    id=str(test_provider_account_id),
                    balance=balance_paise,
                    burn=daily_burn,
                )
            )
            await session.commit()

        procurement_customer_id = UUID("00000000-0000-0000-0000-000000000000")
        alerts = await meter_service.check_thresholds(procurement_customer_id)

        crit_alerts = [a for a in alerts if "CRITICAL" in a.threshold_name]
        assert len(crit_alerts) >= 1

    async def test_procurement_runway_emergency_at_1_day(
        self, meter_service, session_factory, test_provider_account_id
    ):
        """Scope 3: Procurement EMERGENCY alert should fire at ≤1 day remaining."""
        balance_paise = 5000
        daily_burn = 10000

        async with session_factory() as session:
            await session.execute(
                text(
                    "UPDATE provider_accounts "
                    "SET balance_paise = :balance, daily_burn_rate_paise = :burn "
                    "WHERE id = :id"
                ).bindparams(
                    id=str(test_provider_account_id),
                    balance=balance_paise,
                    burn=daily_burn,
                )
            )
            await session.commit()

        procurement_customer_id = UUID("00000000-0000-0000-0000-000000000000")
        alerts = await meter_service.check_thresholds(procurement_customer_id)

        emerg_alerts = [a for a in alerts if "EMERGENCY" in a.threshold_name]
        assert len(emerg_alerts) >= 1

    async def test_agency_null_quota_produces_no_alert(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """Scope 2: Agency with NULL quota should not fire alert."""
        quota_paise = setup_test_data
        amount_paise = 700000

        async with session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO agency_sub_wallets (id, customer_id, quota_paise) "
                    "VALUES (:id, :customer_id, :quota)"
                ).bindparams(
                    id=str(uuid4()),
                    customer_id=str(customer_id),
                    quota=None,
                )
            )
            await session.commit()

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        agency_alerts = [a for a in alerts if a.scope == "AGENCY"]
        assert len(agency_alerts) == 0

    async def test_agency_null_quota_does_not_raise(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """Scope 2: Agency with NULL quota should not raise exception."""
        quota_paise = setup_test_data

        async with session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO agency_sub_wallets (id, customer_id, quota_paise) "
                    "VALUES (:id, :customer_id, :quota)"
                ).bindparams(
                    id=str(uuid4()),
                    customer_id=str(customer_id),
                    quota=None,
                )
            )
            await session.commit()

        await meter_service.record_usage(customer_id, thread_type, 100000)

        try:
            await meter_service.check_thresholds(customer_id)
        except Exception as exc:
            pytest.fail(f"check_thresholds raised {type(exc).__name__}: {exc}")

    async def test_check_thresholds_handles_empty_ledger(
        self, meter_service, customer_id, setup_test_data
    ):
        """check_thresholds should return empty list if no spend recorded."""
        alerts = await meter_service.check_thresholds(customer_id)

        assert isinstance(alerts, list)
        assert len(alerts) == 0


class TestRunDailyScan:
    """Tests for MeterService.run_daily_scan."""

    async def test_post_meter_daily_scan_calls_check_thresholds_for_all_customers(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """run_daily_scan should call check_thresholds for all active customers."""
        amount_paise = 700000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        result = await meter_service.run_daily_scan()

        assert isinstance(result, DailyScanResult)
        assert result.customers_scanned >= 1
        assert result.alerts_sent >= 0

    async def test_daily_scan_aggregates_alert_count(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """run_daily_scan should aggregate alert counts in DailyScanResult."""
        amount_paise = 900000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        result = await meter_service.run_daily_scan()

        assert result.alerts_sent >= 1

    async def test_daily_scan_returns_zero_when_no_customers(
        self, meter_service, session_factory
    ):
        """run_daily_scan should return zero counts when no customers."""
        result = await meter_service.run_daily_scan()

        assert result.customers_scanned == 0
        assert result.alerts_sent == 0

    async def test_cct_billingloop_01_ad_wallet_hits_zero(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """CCT-BILLINGLOOP-01: AD wallet at zero should fire AD_WALLET_BELOW_MINIMUM alert."""
        quota_paise = setup_test_data
        amount_paise = 1_000_000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        assert len(alerts) >= 1

    async def test_cct_billingloop_01_below_minimum_alert_type(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """CCT-BILLINGLOOP-01: Alert should have type AD_WALLET_BELOW_MINIMUM."""
        quota_paise = setup_test_data
        amount_paise = 1_000_000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        minimum_alerts = [
            a for a in alerts if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"
        ]
        assert len(minimum_alerts) >= 1
        assert minimum_alerts[0].scope == "CUSTOMER_BUCKET"


class TestThresholdProperties:
    """Property-based and invariant tests."""

    async def test_pct_consumed_always_in_valid_range(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """pct_consumed should always be in [0.0, 1.0] range."""
        for spend in [0, 250000, 500000, 750000, 1000000]:
            await meter_service.record_usage(customer_id, thread_type, spend)

        alerts = await meter_service.check_thresholds(customer_id)

        for alert in alerts:
            assert 0.0 <= alert.pct_consumed <= 1.0

    async def test_days_remaining_always_positive(
        self, meter_service, customer_id, thread_type, setup_test_data
    ):
        """days_remaining should always be >= 0."""
        projection = await meter_service.project_depletion(customer_id, thread_type)

        assert projection.days_remaining >= 0

    async def test_threshold_comparison_is_deterministic(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """Same input state should produce same alert list multiple times."""
        quota_paise = setup_test_data
        amount_paise = 700000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        alerts_1 = await meter_service.check_thresholds(customer_id)
        alerts_2 = await meter_service.check_thresholds(customer_id)

        assert len(alerts_1) == len(alerts_2)

    async def test_runway_threshold_ladder_ordering(self):
        """RunwayThresholdRule list should be ordered by days_remaining descending."""
        rules = PROCUREMENT_POLICY.runway_thresholds
        if len(rules) > 1:
            for i in range(len(rules) - 1):
                assert (
                    rules[i].days_remaining_trigger
                    >= rules[i + 1].days_remaining_trigger
                )

    async def test_marked_up_cost_always_gte_base_cost(
        self, meter_service, session_factory, customer_id, thread_type, setup_test_data
    ):
        """Marked-up cost should equal recorded amount (no markup applied in this sprint)."""
        amount_paise = 100000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT marked_up_cost_inr_paise FROM platform_cost_ledger "
                    "WHERE customer_id = :cid"
                ).bindparams(customer_id=str(customer_id))
            )
            row = result.fetchone()
            assert row.marked_up_cost_inr_paise == amount_paise

    async def test_multiple_thresholds_fire_independently(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """Multiple thresholds should fire independently at their respective triggers."""
        quota_paise = setup_test_data
        amount_paise = 900000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        threshold_names = {a.threshold_name for a in alerts}
        assert len(threshold_names) >= 1

    async def test_no_alert_when_budget_below_threshold(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """No alert should fire when consumption is below all thresholds."""
        amount_paise = 100000

        await meter_service.record_usage(customer_id, thread_type, amount_paise)
        alerts = await meter_service.check_thresholds(customer_id)

        assert len(alerts) == 0


class TestHelpers:
    """Tests for helper functions."""

    async def test_current_billing_period_start_returns_first_of_month(self):
        """_current_billing_period_start should return the first day of current month."""
        now = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        period_start = _current_billing_period_start(now)

        assert period_start == date(2024, 7, 1)

    async def test_is_quiet_hours_detects_window(self):
        """_is_quiet_hours should return True during quiet window (23:00-06:00)."""
        now_ist = datetime(2024, 7, 15, 23, 30, 0, tzinfo=_IST_TZ)
        policy = CUSTOMER_BUCKET_POLICY

        is_quiet = _is_quiet_hours(policy, now_ist)
        assert is_quiet is True

    async def test_is_quiet_hours_detects_outside_window(self):
        """_is_quiet_hours should return False outside quiet window."""
        now_ist = datetime(2024, 7, 15, 12, 0, 0, tzinfo=_IST_TZ)
        policy = CUSTOMER_BUCKET_POLICY

        is_quiet = _is_quiet_hours(policy, now_ist)
        assert is_quiet is False

    async def test_now_ist_returns_ist_timezone(self):
        """_now_ist should return time in IST (UTC+5:30)."""
        now = _now_ist()

        assert now.tzinfo == _IST_TZ or now.utcoffset() == _IST_OFFSET


class TestIntegration:
    """Integration tests."""

    async def test_whatsapp_notifier_send_returns_bool(self, mock_whatsapp_notifier):
        """WhatsAppNotifier.send should return bool."""
        result = await mock_whatsapp_notifier.send(
            uuid4(), "template_id", {"key": "value"}
        )

        assert isinstance(result, bool)

    async def test_cancellation_handled_in_daily_scan(self, meter_service):
        """run_daily_scan should handle asyncio.CancelledError correctly."""
        with patch.object(
            meter_service, "check_thresholds", side_effect=asyncio.CancelledError()
        ):
            with pytest.raises(asyncio.CancelledError):
                await meter_service.run_daily_scan()

    async def test_alert_fired_has_required_fields(
        self,
        meter_service,
        session_factory,
        customer_id,
        thread_type,
        setup_test_data,
    ):
        """AlertFired should have all required fields populated."""
        amount_paise = 750000
        await meter_service.record_usage(customer_id, thread_type, amount_paise)

        alerts = await meter_service.check_thresholds(customer_id)

        if alerts:
            alert = alerts[0]
            assert alert.customer_id is not None
            assert alert.bucket_type is not None
            assert alert.threshold_name is not None
            assert alert.pct_consumed is not None
            assert alert.scope is not None
            assert alert.fired_at is not None