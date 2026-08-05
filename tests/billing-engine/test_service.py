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
        name TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        balance_paise INTEGER DEFAULT 0
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
        wallet_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL,
        available_paise INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (wallet_id) REFERENCES customer_wallets (id)
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
    CREATE TABLE IF NOT EXISTS agency_customers (
        id TEXT PRIMARY KEY,
        agency_wallet_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        FOREIGN KEY (agency_wallet_id) REFERENCES agency_wallets (id)
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
        action TEXT NOT NULL DEFAULT 'LOG',
        fired_at TEXT NOT NULL
    )
    """,
    # provider_runway_view as a real table for tests
    """
    CREATE TABLE IF NOT EXISTS provider_runway_view (
        provider_name TEXT NOT NULL,
        days_remaining REAL NOT NULL
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
async def test_customer_id():
    """Stable test customer UUID."""
    return uuid4()


@pytest.fixture
async def test_provider_account_id():
    """Stable test provider UUID."""
    return uuid4()


@pytest.fixture
async def setup_test_data(session_factory, test_customer_id, test_provider_account_id):
    """
    Populate: provider_accounts, thread_catalog, customer_wallets, wallet_buckets.
    Returns (wallet_id, quota_paise) for use in individual tests.
    """
    quota_paise = 1_000_000
    wallet_id = str(uuid4())

    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO provider_accounts (id, name, active, balance_paise) "
                "VALUES (:id, :name, :active, :balance)"
            ).bindparams(
                id=str(test_provider_account_id),
                name="test-provider",
                active=1,
                balance=quota_paise,
            )
        )
        await session.execute(
            text(
                "INSERT INTO thread_catalog (id, thread_type, provider_account_id) "
                "VALUES (:id, :thread_type, :provider_id)"
            ).bindparams(
                id=str(uuid4()),
                thread_type="GENIE",
                provider_id=str(test_provider_account_id),
            )
        )
        await session.execute(
            text(
                "INSERT INTO customer_wallets (id, customer_id, status) "
                "VALUES (:id, :customer_id, :status)"
            ).bindparams(
                id=wallet_id,
                customer_id=str(test_customer_id),
                status="ACTIVE",
            )
        )
        await session.execute(
            text(
                "INSERT INTO wallet_buckets "
                "(id, wallet_id, thread_type, balance_paise, available_paise) "
                "VALUES (:id, :wallet_id, :thread_type, :balance, :available)"
            ).bindparams(
                id=str(uuid4()),
                wallet_id=wallet_id,
                thread_type="GENIE",
                balance=quota_paise,
                available=quota_paise,
            )
        )
        await session.commit()

    return wallet_id, quota_paise


# ---------------------------------------------------------------------------
# Helper: insert a ledger row for the current billing period
# ---------------------------------------------------------------------------


async def _insert_ledger(
    session_factory,
    customer_id: UUID,
    thread_type: str,
    provider_account_id: UUID,
    amount_paise: int,
    recorded_at: datetime | None = None,
) -> None:
    now_utc = recorded_at or datetime.now(timezone.utc)
    period_start = now_utc.date().replace(day=1)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, "
                " marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :paid, :amount, :rat, :bps)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(customer_id),
                tt=thread_type,
                paid=str(provider_account_id),
                amount=amount_paise,
                rat=str(now_utc),
                bps=str(period_start),
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Unit tests -- _current_billing_period_start
# ---------------------------------------------------------------------------


def test_current_billing_period_start_returns_first_day_of_month():
    dt = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = _current_billing_period_start(dt)
    assert result == date(2026, 7, 1)


def test_current_billing_period_start_on_first():
    dt = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    result = _current_billing_period_start(dt)
    assert result == date(2026, 8, 1)


# ---------------------------------------------------------------------------
# Unit tests -- _is_quiet_hours
# ---------------------------------------------------------------------------


def test_is_quiet_hours_inside_window():
    """23:30 IST should be quiet hours (23->6 window)."""
    policy = CUSTOMER_BUCKET_POLICY
    now = datetime(2026, 7, 15, 23, 30, tzinfo=_IST_TZ)
    assert _is_quiet_hours(policy, now) is True


def test_is_quiet_hours_outside_window():
    """10:00 IST is not quiet hours."""
    policy = CUSTOMER_BUCKET_POLICY
    now = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(policy, now) is False


def test_is_quiet_hours_boundary_start():
    """23:00 IST is the boundary -- should be quiet."""
    policy = CUSTOMER_BUCKET_POLICY
    now = datetime(2026, 7, 15, 23, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(policy, now) is True


def test_is_quiet_hours_boundary_end():
    """06:00 IST is the end boundary -- should NOT be quiet (hour < 6 only)."""
    policy = CUSTOMER_BUCKET_POLICY
    now = datetime(2026, 7, 15, 6, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(policy, now) is False


def test_is_quiet_hours_early_morning():
    """03:00 IST -- past midnight, still quiet."""
    policy = CUSTOMER_BUCKET_POLICY
    now = datetime(2026, 7, 15, 3, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(policy, now) is True


# ---------------------------------------------------------------------------
# record_usage tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_usage_happy_path(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """record_usage should write one row to platform_cost_ledger."""
    await meter_service.record_usage(
        customer_id=test_customer_id,
        thread_type="GENIE",
        amount_paise=5000,
    )

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM platform_cost_ledger "
                "WHERE customer_id = :cid AND thread_type = :tt"
            ).bindparams(cid=str(test_customer_id), tt="GENIE")
        )
        result = row.fetchone()
    assert result.cnt == 1


@pytest.mark.asyncio
async def test_record_usage_unknown_thread_type_logs_and_returns(
    meter_service, session_factory, test_customer_id, setup_test_data
):
    """record_usage with unknown thread_type must not raise and must not write a row."""
    # Should return without raising -- provider_account not found path
    await meter_service.record_usage(
        customer_id=test_customer_id,
        thread_type="NONEXISTENT_TYPE",
        amount_paise=1000,
    )

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT COUNT(*) AS cnt FROM platform_cost_ledger WHERE thread_type = :tt").bindparams(
                tt="NONEXISTENT_TYPE"
            )
        )
        result = row.fetchone()
    assert result.cnt == 0


@pytest.mark.asyncio
async def test_record_usage_multiple_calls_accumulate(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """Three calls must create three rows."""
    for paise in [1000, 2000, 3000]:
        await meter_service.record_usage(
            customer_id=test_customer_id,
            thread_type="GENIE",
            amount_paise=paise,
        )

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT COALESCE(SUM(marked_up_cost_inr_paise), 0) AS total "
                "FROM platform_cost_ledger WHERE customer_id = :cid"
            ).bindparams(cid=str(test_customer_id))
        )
        result = row.fetchone()
    assert result.total == 6000


# ---------------------------------------------------------------------------
# project_depletion tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_depletion_no_usage_returns_inf(
    meter_service, test_customer_id, setup_test_data
):
    """With zero usage, days_remaining should be infinite."""
    projection = await meter_service.project_depletion(
        customer_id=test_customer_id,
        thread_type="GENIE",
    )
    assert projection.days_remaining == float("inf")
    assert projection.daily_burn_rate_paise == 0.0


@pytest.mark.asyncio
async def test_project_depletion_with_usage(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """With 7 days * 10_000 paise usage the daily burn should equal 10_000."""
    now_utc = datetime.now(timezone.utc)
    for offset in range(7):
        recorded_at = now_utc - timedelta(days=offset)
        await _insert_ledger(
            session_factory,
            test_customer_id,
            "GENIE",
            test_provider_account_id,
            10_000,
            recorded_at=recorded_at,
        )

    projection = await meter_service.project_depletion(
        customer_id=test_customer_id,
        thread_type="GENIE",
    )
    assert projection.daily_burn_rate_paise == pytest.approx(10_000.0, rel=0.01)
    assert projection.days_remaining == pytest.approx(100.0, rel=0.05)  # 1_000_000 / 10_000


@pytest.mark.asyncio
async def test_project_depletion_returns_depletion_projection_type(
    meter_service, test_customer_id, setup_test_data
):
    projection = await meter_service.project_depletion(
        customer_id=test_customer_id,
        thread_type="GENIE",
    )
    assert isinstance(projection, DepletionProjection)


# ---------------------------------------------------------------------------
# check_thresholds -- Scope 1 (CUSTOMER_BUCKET)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_thresholds_no_consumption_fires_no_alerts(
    meter_service, test_customer_id, setup_test_data
):
    """Zero consumption should produce no alerts."""
    alerts = await meter_service.check_thresholds(test_customer_id)
    assert alerts == []


@pytest.mark.asyncio
async def test_check_thresholds_warn_30_fires_at_70_pct(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """
    WARN_30 triggers when consumed >= 70% of quota (30% remaining).
    quota = 1_000_000; 70% consumed = 700_000 paise.
    """
    _wallet_id, quota_paise = setup_test_data
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        700_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    threshold_names = [a.threshold_name for a in alerts]
    assert "WARN_30" in threshold_names


@pytest.mark.asyncio
async def test_check_thresholds_warn_20_and_warn_10_fire_at_correct_pct(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """
    At 90% consumed: WARN_30, WARN_20, WARN_10 should all fire.
    quota = 1_000_000; 90% = 900_000 paise.
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        900_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = {a.threshold_name for a in alerts}
    assert "WARN_30" in names
    assert "WARN_20" in names
    assert "WARN_10" in names


@pytest.mark.asyncio
async def test_check_thresholds_ad_wallet_below_minimum_at_100_pct(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """
    CCT-BILLINGLOOP-01: AD_WALLET_BELOW_MINIMUM fires when consumed >= 100%.
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        1_000_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = {a.threshold_name for a in alerts}
    assert "AD_WALLET_BELOW_MINIMUM" in names


# ---------------------------------------------------------------------------
# check_thresholds -- deduplication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_double_fire_within_24h_deduplication_window(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """Same alert must not fire twice within 24 hours."""
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        700_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        first_alerts = await meter_service.check_thresholds(test_customer_id)
        second_alerts = await meter_service.check_thresholds(test_customer_id)

    first_names = {a.threshold_name for a in first_alerts}
    second_names = {a.threshold_name for a in second_alerts}

    assert "WARN_30" in first_names
    # Second call within 24h must not re-fire WARN_30
    assert "WARN_30" not in second_names


@pytest.mark.asyncio
async def test_alert_fires_again_after_dedup_window(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """
    An alert that was fired 25+ hours ago should fire again (outside dedup window).
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        700_000,
    )

    now_utc = datetime.now(timezone.utc)
    old_fired_at = now_utc - timedelta(hours=26)

    # Pre-seed a stale alert log entry
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO meter_alert_log "
                "(id, customer_id, bucket_type, threshold_name, pct_consumed, scope, action, fired_at) "
                "VALUES (:id, :cid, :bt, :tn, :pct, :scope, :action, :fired_at)"
            ).bindparams(
                id=str(uuid4()),
                cid=str(test_customer_id),
                bt="GENIE",
                tn="WARN_30",
                pct=0.70,
                scope="CUSTOMER_BUCKET",
                action="NOTIFY",
                fired_at=str(old_fired_at),
            )
        )
        await session.commit()

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = {a.threshold_name for a in alerts}
    assert "WARN_30" in names


# ---------------------------------------------------------------------------
# check_thresholds -- quiet hours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quiet_hours_suppress_notify_alerts(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """
    During quiet hours (23:00-06:00 IST), NOTIFY-class alerts without
    bypass_quiet_hours must be suppressed.
    WARN_30 is NOTIFY without bypass -- should be suppressed.
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        700_000,
    )

    # 23:30 IST -- inside quiet window
    quiet_ist = datetime(2026, 7, 15, 23, 30, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=quiet_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = {a.threshold_name for a in alerts}
    # WARN_30 is NOTIFY with bypass_quiet_hours=False -- must be suppressed
    assert "WARN_30" not in names


@pytest.mark.asyncio
async def test_quiet_hours_do_not_suppress_bypass_true_alerts(
    meter_service, session_factory, test_customer_id, test_provider_account_id, setup_test_data
):
    """
    WARN_10 has bypass_quiet_hours=True -- must fire even during quiet hours.
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        900_000,
    )

    quiet_ist = datetime(2026, 7, 15, 23, 30, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=quiet_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = {a.threshold_name for a in alerts}
    assert "WARN_10" in names


# ---------------------------------------------------------------------------
# check_thresholds -- Scope 2 AGENCY
# ---------------------------------------------------------------------------


@pytest.fixture
async def setup_agency_data(session_factory, test_customer_id):
    """Add an agency wallet linked to test_customer_id."""
    agency_wallet_id = str(uuid4())
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO agency_wallets (id, name, balance_paise) "
                "VALUES (:id, :name, :balance)"
            ).bindparams(id=agency_wallet_id, name="test-agency", balance=500_000)
        )
        await session.execute(
            text(
                "INSERT INTO agency_customers (id, agency_wallet_id, customer_id) "
                "VALUES (:id, :awid, :cid)"
            ).bindparams(
                id=str(uuid4()),
                awid=agency_wallet_id,
                cid=str(test_customer_id),
            )
        )
        await session.commit()
    return agency_wallet_id, 500_000


@pytest.mark.asyncio
async def test_agency_alert_fires_at_50_pct(
    meter_service,
    session_factory,
    test_customer_id,
    test_provider_account_id,
    setup_test_data,
    setup_agency_data,
):
    """AGENCY_WARN_50 fires when agency-aggregate consumption >= 50%."""
    _agency_wallet_id, agency_quota = setup_agency_data

    # Insert ledger: 250_000 paise = 50% of 500_000 agency quota
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        250_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = {a.threshold_name for a in alerts}
    assert "AGENCY_WARN_50" in names


@pytest.mark.asyncio
async def test_agency_null_quota_produces_no_alert(
    meter_service,
    session_factory,
    test_customer_id,
    test_provider_account_id,
    setup_test_data,
):
    """
    When no agency_wallet row exists for the customer, no AGENCY-scope alert fires.
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        900_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    agency_alerts = [a for a in alerts if a.scope == "AGENCY"]
    assert agency_alerts == []


# ---------------------------------------------------------------------------
# check_thresholds -- Scope 3 PROCUREMENT
# ---------------------------------------------------------------------------


@pytest.fixture
async def setup_procurement_runway(session_factory):
    """Insert procurement runway rows into provider_runway_view table."""

    async def _setup(provider_name: str, days_remaining: float) -> None:
        async with session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO provider_runway_view (provider_name, days_remaining) "
                    "VALUES (:pn, :dr)"
                ).bindparams(pn=provider_name, dr=days_remaining)
            )
            await session.commit()

    return _setup


@pytest.mark.asyncio
async def test_procurement_runway_p0_fires_at_7_days(
    meter_service,
    test_customer_id,
    setup_test_data,
    setup_procurement_runway,
):
    """RUNWAY_P0 should fire when provider days_remaining <= 7."""
    await setup_procurement_runway("openai", 5.0)

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    proc_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    names = {a.threshold_name for a in proc_alerts}
    assert "RUNWAY_P0" in names


@pytest.mark.asyncio
async def test_procurement_runway_emergency_fires_at_1_day(
    meter_service,
    test_customer_id,
    setup_test_data,
    setup_procurement_runway,
):
    """RUNWAY_EMERGENCY should fire when days_remaining <= 1."""
    await setup_procurement_runway("anthropic", 0.5)

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    proc_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    names = {a.threshold_name for a in proc_alerts}
    assert "RUNWAY_EMERGENCY" in names


@pytest.mark.asyncio
async def test_procurement_no_alert_when_runway_sufficient(
    meter_service,
    test_customer_id,
    setup_test_data,
    setup_procurement_runway,
):
    """No procurement alert when days_remaining > 30."""
    await setup_procurement_runway("google", 90.0)

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    proc_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    assert proc_alerts == []


# ---------------------------------------------------------------------------
# run_daily_scan tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_daily_scan_returns_daily_scan_result(
    meter_service, test_customer_id, setup_test_data
):
    """run_daily_scan must return a DailyScanResult."""
    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        result = await meter_service.run_daily_scan()
    assert isinstance(result, DailyScanResult)


@pytest.mark.asyncio
async def test_run_daily_scan_scans_active_customers(
    meter_service,
    session_factory,
    test_customer_id,
    setup_test_data,
):
    """run_daily_scan must count active customers scanned."""
    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        result = await meter_service.run_daily_scan()
    assert result.customers_scanned >= 1


@pytest.mark.asyncio
async def test_run_daily_scan_does_not_scan_inactive_customers(
    meter_service,
    session_factory,
):
    """Customers with status != ACTIVE must be excluded from scan."""
    inactive_customer_id = str(uuid4())
    inactive_wallet_id = str(uuid4())

    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO customer_wallets (id, customer_id, status) "
                "VALUES (:id, :cid, :status)"
            ).bindparams(
                id=inactive_wallet_id,
                cid=inactive_customer_id,
                status="SUSPENDED",
            )
        )
        await session.commit()

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        result = await meter_service.run_daily_scan()

    # Suspended customer should not appear in scanned count
    assert result.customers_scanned == 0


@pytest.mark.asyncio
async def test_run_daily_scan_aggregates_alerts_sent(
    meter_service,
    session_factory,
    test_customer_id,
    test_provider_account_id,
    setup_test_data,
):
    """run_daily_scan.alerts_sent must equal total AlertFired count."""
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        700_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        result = await meter_service.run_daily_scan()

    assert result.alerts_sent >= 1


@pytest.mark.asyncio
async def test_run_daily_scan_fa_items_counted_correctly(
    meter_service,
    session_factory,
    test_customer_id,
    test_provider_account_id,
    setup_test_data,
    setup_agency_data,
):
    """
    FA-class agency alert (AGENCY_CRITICAL at 95%) must increment fa_items_created.
    """
    _agency_wallet_id, agency_quota = setup_agency_data

    # 95% of 500_000 = 475_000
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        475_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        result = await meter_service.run_daily_scan()

    assert result.fa_items_created >= 1


# ---------------------------------------------------------------------------
# CCT-BILLINGLOOP-01: AD wallet hits zero
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cct_billingloop_01_ad_wallet_hits_zero(
    meter_service,
    session_factory,
    test_customer_id,
    test_provider_account_id,
    setup_test_data,
):
    """
    CCT-BILLINGLOOP-01: When the AD wallet balance reaches zero (100% consumed),
    exactly one AD_WALLET_BELOW_MINIMUM alert must fire.
    """
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        1_000_000,  # 100% of quota
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    ad_wallet_alerts = [a for a in alerts if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"]
    assert len(ad_wallet_alerts) == 1
    assert ad_wallet_alerts[0].scope == "CUSTOMER_BUCKET"


# ---------------------------------------------------------------------------
# AlertFired shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alert_fired_fields_populated(
    meter_service,
    session_factory,
    test_customer_id,
    test_provider_account_id,
    setup_test_data,
):
    """AlertFired objects must have all required fields populated."""
    await _insert_ledger(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        700_000,
    )

    fixed_ist = datetime(2026, 7, 15, 10, 0, tzinfo=_IST_TZ)
    with patch("meter.service._now_ist", return_value=fixed_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    assert len(alerts) >= 1
    for alert in alerts:
        assert alert.customer_id == test_customer_id
        assert alert.bucket_type != ""
        assert alert.threshold_name != ""
        assert alert.scope != ""
        assert isinstance(alert.fired_at, datetime)
        assert 0.0 <= alert.pct_consumed


# ---------------------------------------------------------------------------
# Alert policy singleton sanity checks
# ---------------------------------------------------------------------------


def test_customer_bucket_policy_has_warn_30():
    names = [r.name for r in CUSTOMER_BUCKET_POLICY.thresholds]
    assert "WARN_30" in names


def test_customer_bucket_policy_has_ad_wallet_below_minimum():
    names = [r.name for r in CUSTOMER_BUCKET_POLICY.thresholds]
    assert "AD_WALLET_BELOW_MINIMUM" in names


def test_agency_policy_has_critical_fa_action():
    fa_rules = [r for r in AGENCY_POLICY.thresholds if r.action == AlertAction.FA]
    assert len(fa_rules) >= 1


def test_procurement_policy_has_runway_p0():
    names = [r.name for r in PROCUREMENT_POLICY.thresholds]
    assert "RUNWAY_P0" in names


def test_procurement_policy_has_runway_emergency():
    names = [r.name for r in PROCUREMENT_POLICY.thresholds]
    assert "RUNWAY_EMERGENCY" in names


def test_procurement_policy_has_runway_p2():
    names = [r.name for r in PROCUREMENT_POLICY.thresholds]
    assert "RUNWAY_P2" in names


def test_procurement_policy_has_runway_p1():
    names = [r.name for r in PROCUREMENT_POLICY.thresholds]
    assert "RUNWAY_P1" in names


def test_procurement_policy_has_runway_critical():
    names = [r.name for r in PROCUREMENT_POLICY.thresholds]
    assert "RUNWAY_CRITICAL" in names


def test_warn_30_trigger_is_70_pct():
    """WARN_30 must trigger at 70% consumed (30% remaining)."""
    warn_30 = next(r for r in CUSTOMER_BUCKET_POLICY.thresholds if r.name == "WARN_30")
    assert warn_30.consumed_pct_trigger == pytest.approx(0.70)


def test_ad_wallet_below_minimum_has_block_action():
    rule = next(
        r for r in CUSTOMER_BUCKET_POLICY.thresholds if r.name == "AD_WALLET_BELOW_MINIMUM"
    )
    assert rule.action == AlertAction.BLOCK


def test_ad_wallet_below_minimum_bypass_quiet_hours():
    """AD_WALLET_BELOW_MINIMUM must bypass quiet hours (safety-critical)."""
    rule = next(
        r for r in CUSTOMER_BUCKET_POLICY.thresholds if r.name == "AD_WALLET_BELOW_MINIMUM"
    )
    assert rule.bypass_quiet_hours is True


def test_customer_bucket_policy_scope():
    assert CUSTOMER_BUCKET_POLICY.scope == AlertScope.CUSTOMER_BUCKET


def test_agency_policy_scope():
    assert AGENCY_POLICY.scope == AlertScope.AGENCY


def test_procurement_policy_scope():
    assert PROCUREMENT_POLICY.scope == AlertScope.PROCUREMENT


# ---------------------------------------------------------------------------
# MeterService initialization
# ---------------------------------------------------------------------------


def test_meter_service_init_stores_session_factory(session_factory):
    svc = MeterService(session_factory=session_factory, redis_pool=None)
    assert svc._session_factory is session_factory


def test_meter_service_init_redis_pool_none(session_factory):
    svc = MeterService(session_factory=session_factory, redis_pool=None)
    assert svc._redis_pool is None


# ---------------------------------------------------------------------------
# _now_ist returns IST-aware datetime
# ---------------------------------------------------------------------------


def test_now_ist_is_ist_offset():
    result = _now_ist()
    assert result.utcoffset() == _IST_OFFSET


def test_now_ist_is_timezone_aware():
    result = _now_ist()
    assert result.tzinfo is not None