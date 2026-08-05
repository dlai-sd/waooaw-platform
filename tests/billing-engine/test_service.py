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
    CREATE TABLE IF NOT EXISTS agency_wallet_members (
        id TEXT PRIMARY KEY,
        agency_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        agency_quota_paise INTEGER
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
                "(id, customer_id, thread_type, balance_paise, is_active) "
                "VALUES (:id, :customer_id, :thread_type, :balance, 1)"
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(test_customer_id),
                thread_type="GENIE",
                balance=quota_paise,
            )
        )
        await session.commit()

    return wallet_id, quota_paise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ist_datetime(hour: int, minute: int = 0) -> datetime:
    """Return a timezone-aware datetime at the given IST hour."""
    return datetime.now(timezone.utc).astimezone(_IST_TZ).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


async def _insert_ledger_row(
    session_factory: async_sessionmaker,
    customer_id: UUID,
    thread_type: str,
    provider_account_id: UUID,
    amount_paise: int,
    billing_period_start: date,
    recorded_at: datetime | None = None,
) -> None:
    """Insert a platform_cost_ledger row directly for test setup."""
    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, "
                "marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :customer_id, :thread_type, :provider_account_id, "
                ":amount, :recorded_at, :billing_period_start)"
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(customer_id),
                thread_type=thread_type,
                provider_account_id=str(provider_account_id),
                amount=amount_paise,
                recorded_at=recorded_at.isoformat(),
                billing_period_start=billing_period_start.isoformat(),
            )
        )
        await session.commit()


async def _insert_alert_log_row(
    session_factory: async_sessionmaker,
    customer_id: UUID,
    bucket_type: str,
    threshold_name: str,
    fired_at: datetime,
) -> None:
    """Insert a meter_alert_log row to simulate prior dedup state."""
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO meter_alert_log "
                "(id, customer_id, bucket_type, threshold_name, "
                "pct_consumed, scope, fired_at) "
                "VALUES (:id, :customer_id, :bucket_type, :threshold_name, "
                ":pct_consumed, :scope, :fired_at)"
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(customer_id),
                bucket_type=bucket_type,
                threshold_name=threshold_name,
                pct_consumed=0.75,
                scope="CUSTOMER_BUCKET",
                fired_at=fired_at.isoformat(),
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Tests: alert_policy module
# ---------------------------------------------------------------------------


def test_customer_bucket_policy_scope() -> None:
    """CUSTOMER_BUCKET_POLICY has correct scope and at least one threshold."""
    assert CUSTOMER_BUCKET_POLICY.scope == AlertScope.CUSTOMER_BUCKET
    assert len(CUSTOMER_BUCKET_POLICY.rules) > 0


def test_agency_policy_scope() -> None:
    """AGENCY_POLICY has AGENCY scope."""
    assert AGENCY_POLICY.scope == AlertScope.AGENCY
    assert len(AGENCY_POLICY.rules) > 0


def test_procurement_policy_uses_runway_thresholds() -> None:
    """PROCUREMENT_POLICY populates runway_thresholds, not thresholds."""
    assert len(PROCUREMENT_POLICY.runway_thresholds) > 0
    assert PROCUREMENT_POLICY.rules is PROCUREMENT_POLICY.runway_thresholds


def test_procurement_policy_threshold_names() -> None:
    """Scope 3 threshold names follow the spec ladder."""
    names = {r.name for r in PROCUREMENT_POLICY.rules}
    assert "RUNWAY_P2" in names
    assert "RUNWAY_P1" in names
    assert "RUNWAY_P0" in names
    assert "RUNWAY_CRITICAL" in names
    assert "RUNWAY_EMERGENCY" in names


def test_threshold_policy_rules_returns_thresholds_when_runway_empty() -> None:
    """rules property falls back to .thresholds when runway_thresholds is empty."""
    assert CUSTOMER_BUCKET_POLICY.rules is CUSTOMER_BUCKET_POLICY.thresholds


def test_quiet_hours_detection_during_night() -> None:
    """_is_quiet_hours returns True at 23:30 IST (default 23-06 window)."""
    night_ist = _make_ist_datetime(23, 30)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, night_ist) is True


def test_quiet_hours_detection_during_early_morning() -> None:
    """_is_quiet_hours returns True at 05:00 IST (inside 23-06 window)."""
    early_ist = _make_ist_datetime(5, 0)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, early_ist) is True


def test_quiet_hours_detection_during_day() -> None:
    """_is_quiet_hours returns False at 10:00 IST (outside 23-06 window)."""
    day_ist = _make_ist_datetime(10, 0)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, day_ist) is False


def test_current_billing_period_start() -> None:
    """_current_billing_period_start returns first day of the month."""
    now = datetime(2026, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
    result = _current_billing_period_start(now)
    assert result == date(2026, 7, 1)


def test_now_ist_returns_ist_timezone() -> None:
    """_now_ist returns a datetime with IST offset."""
    result = _now_ist()
    assert result.tzinfo is not None
    assert result.utcoffset() == _IST_OFFSET


# ---------------------------------------------------------------------------
# Tests: record_usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_usage_happy_path(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """record_usage inserts a row into platform_cost_ledger."""
    await meter_service.record_usage(test_customer_id, "GENIE", 5000)

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM platform_cost_ledger "
                "WHERE customer_id = :cid AND marked_up_cost_inr_paise = 5000"
            ).bindparams(cid=str(test_customer_id))
        )
        result = row.fetchone()
    assert result is not None
    assert result.cnt == 1


@pytest.mark.asyncio
async def test_record_usage_unknown_thread_type_does_not_raise(
    meter_service: MeterService,
    test_customer_id: UUID,
    setup_test_data: tuple,
) -> None:
    """record_usage returns silently if thread_type has no provider mapping."""
    # Should not raise - logs error and returns
    await meter_service.record_usage(test_customer_id, "NONEXISTENT_TYPE", 1000)


@pytest.mark.asyncio
async def test_record_usage_writes_billing_period_start(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    setup_test_data: tuple,
) -> None:
    """record_usage sets billing_period_start to the first of the current month."""
    await meter_service.record_usage(test_customer_id, "GENIE", 100)

    now_utc = datetime.now(timezone.utc)
    expected_start = _current_billing_period_start(now_utc).isoformat()

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT billing_period_start FROM platform_cost_ledger "
                "WHERE customer_id = :cid ORDER BY recorded_at DESC LIMIT 1"
            ).bindparams(cid=str(test_customer_id))
        )
        result = row.fetchone()
    assert result is not None
    assert result.billing_period_start == expected_start


# ---------------------------------------------------------------------------
# Tests: project_depletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_depletion_with_burn_data(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """project_depletion returns a DepletionProjection based on 7-day rolling avg."""
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    # Insert 7 days of burn: 10_000 paise/day
    for i in range(7):
        rec_at = now_utc - timedelta(days=i)
        await _insert_ledger_row(
            session_factory,
            test_customer_id,
            "GENIE",
            test_provider_account_id,
            10_000,
            period_start,
            rec_at,
        )

    projection = await meter_service.project_depletion(test_customer_id, "GENIE")
    assert isinstance(projection, DepletionProjection)
    assert projection.daily_burn_rate_paise > 0.0
    assert projection.days_remaining >= 0.0
    assert isinstance(projection.projected_empty_date, date)


@pytest.mark.asyncio
async def test_project_depletion_no_burn_returns_large_days(
    meter_service: MeterService,
    test_customer_id: UUID,
    setup_test_data: tuple,
) -> None:
    """project_depletion with no ledger rows returns 9999 days (honest limitation)."""
    projection = await meter_service.project_depletion(test_customer_id, "GENIE")
    assert projection.days_remaining >= 9999.0


# ---------------------------------------------------------------------------
# Tests: check_thresholds - Scope 1 (CUSTOMER_BUCKET)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_thresholds_no_alerts_below_first_trigger(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """No alerts when consumption is below the first threshold (70%)."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    # 50% consumed - below WARN_30 trigger at 70%
    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.50),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    assert alerts == []


@pytest.mark.asyncio
async def test_check_thresholds_fires_warn_30_at_70_pct(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """WARN_30 fires when 70% of bucket is consumed (30% remaining)."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    # 72% consumed - above WARN_30 trigger at 70%
    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.72),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    names = [a.threshold_name for a in alerts]
    assert "WARN_30" in names


@pytest.mark.asyncio
async def test_check_thresholds_fires_multiple_rules_at_high_consumption(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """At 95% consumed, WARN_30, WARN_20, and WARN_10 should all fire."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.95),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    names = [a.threshold_name for a in alerts]
    assert "WARN_30" in names
    assert "WARN_20" in names
    assert "WARN_10" in names


@pytest.mark.asyncio
async def test_cct_billingloop_01_ad_wallet_zero_fires_alert(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """
    CCT-BILLINGLOOP-01: AD wallet hits zero.
    AD_WALLET_BELOW_MINIMUM fires exactly once, alerts_sent == 1.
    """
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    # 100% consumed - triggers AD_WALLET_BELOW_MINIMUM
    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        quota_paise,
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    below_min = [a for a in alerts if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"]
    assert len(below_min) == 1, f"Expected 1 AD_WALLET_BELOW_MINIMUM alert, got {len(below_min)}"


# ---------------------------------------------------------------------------
# Tests: deduplication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_double_fire_within_dedup_window(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """An alert that already fired in the last 24h must not fire again."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    # Pre-seed the dedup log with WARN_30 fired 1 hour ago
    await _insert_alert_log_row(
        session_factory,
        test_customer_id,
        "GENIE",
        "WARN_30",
        now_utc - timedelta(hours=1),
    )

    # Consume 72% so WARN_30 would trigger
    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.72),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    names = [a.threshold_name for a in alerts]
    assert "WARN_30" not in names, "WARN_30 must not re-fire within the 24h dedup window"


@pytest.mark.asyncio
async def test_alert_fires_after_dedup_window_expires(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """An alert fired > 24h ago should fire again (dedup window expired)."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    # Pre-seed the dedup log with WARN_30 fired 25 hours ago (outside window)
    await _insert_alert_log_row(
        session_factory,
        test_customer_id,
        "GENIE",
        "WARN_30",
        now_utc - timedelta(hours=25),
    )

    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.72),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    names = [a.threshold_name for a in alerts]
    assert "WARN_30" in names, "WARN_30 should re-fire after dedup window expires"


# ---------------------------------------------------------------------------
# Tests: quiet hours suppression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quiet_hours_suppress_notify_alerts(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """
    NOTIFY-action alerts with bypass_quiet_hours=False are suppressed at 23:30 IST.
    WARN_30 has action=NOTIFY and bypass_quiet_hours=False.
    """
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.72),
        period_start,
    )

    # Patch _now_ist to return 23:30 IST (inside quiet hours)
    night_ist = _make_ist_datetime(23, 30)
    with patch("meter.service._now_ist", return_value=night_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = [a.threshold_name for a in alerts]
    assert "WARN_30" not in names, "WARN_30 (NOTIFY) must be suppressed during quiet hours"


@pytest.mark.asyncio
async def test_quiet_hours_do_not_suppress_bypass_true_alerts(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """
    Alerts with bypass_quiet_hours=True fire even at 23:30 IST.
    AD_WALLET_BELOW_MINIMUM has bypass_quiet_hours=True.
    """
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        quota_paise,  # 100% consumed
        period_start,
    )

    night_ist = _make_ist_datetime(23, 30)
    with patch("meter.service._now_ist", return_value=night_ist):
        alerts = await meter_service.check_thresholds(test_customer_id)

    names = [a.threshold_name for a in alerts]
    assert "AD_WALLET_BELOW_MINIMUM" in names, (
        "AD_WALLET_BELOW_MINIMUM (bypass_quiet_hours=True) must fire even during quiet hours"
    )


# ---------------------------------------------------------------------------
# Tests: Scope 2 (AGENCY)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agency_null_quota_produces_no_alert(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """Agency with NULL quota_paise must produce no scope-2 alerts."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)
    agency_id = str(uuid4())

    # Create agency membership with NULL quota
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO agency_wallet_members "
                "(id, agency_id, customer_id, agency_quota_paise) "
                "VALUES (:id, :agency_id, :customer_id, NULL)"
            ).bindparams(
                id=str(uuid4()),
                agency_id=agency_id,
                customer_id=str(test_customer_id),
            )
        )
        await session.commit()

    # Consume 90% of bucket to avoid triggering scope-1 as the concern
    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.60),  # 60% - below AGENCY_WARN_80 but above AGENCY_WARN_50
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    agency_alerts = [a for a in alerts if a.scope == "AGENCY"]
    assert agency_alerts == [], (
        f"Expected no agency alerts with NULL quota, got {agency_alerts}"
    )


@pytest.mark.asyncio
async def test_agency_alert_fires_at_80_pct(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """AGENCY_WARN_80 fires when agency-level consumption exceeds 80% of quota."""
    agency_quota = 500_000
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)
    agency_id = str(uuid4())

    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO agency_wallet_members "
                "(id, agency_id, customer_id, agency_quota_paise) "
                "VALUES (:id, :agency_id, :customer_id, :quota)"
            ).bindparams(
                id=str(uuid4()),
                agency_id=agency_id,
                customer_id=str(test_customer_id),
                quota=agency_quota,
            )
        )
        await session.commit()

    # 85% agency consumption
    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(agency_quota * 0.85),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    agency_alerts = [a for a in alerts if a.scope == "AGENCY"]
    names = [a.threshold_name for a in agency_alerts]
    assert "AGENCY_WARN_80" in names


# ---------------------------------------------------------------------------
# Tests: Scope 3 (PROCUREMENT runway)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_procurement_runway_p0_escalation_at_7_days(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """RUNWAY_P0 fires when provider runway is <= 7 days."""
    # Update provider to have 6 days runway: balance=60000, daily_burn=10000
    async with session_factory() as session:
        await session.execute(
            text(
                "UPDATE provider_accounts "
                "SET balance_paise = 60000, daily_burn_rate_paise = 10000 "
                "WHERE id = :pid"
            ).bindparams(pid=str(test_provider_account_id))
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(test_customer_id)
    procurement_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    names = [a.threshold_name for a in procurement_alerts]
    assert "RUNWAY_P0" in names, (
        f"Expected RUNWAY_P0 with 6d runway, got procurement alert names: {names}"
    )


@pytest.mark.asyncio
async def test_procurement_runway_emergency_at_1_day(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """RUNWAY_EMERGENCY fires when provider runway is <= 1 day."""
    # balance=8000 paise, daily_burn=10000 paise -> 0.8 days remaining
    async with session_factory() as session:
        await session.execute(
            text(
                "UPDATE provider_accounts "
                "SET balance_paise = 8000, daily_burn_rate_paise = 10000 "
                "WHERE id = :pid"
            ).bindparams(pid=str(test_provider_account_id))
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(test_customer_id)
    procurement_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    names = [a.threshold_name for a in procurement_alerts]
    assert "RUNWAY_EMERGENCY" in names


@pytest.mark.asyncio
async def test_procurement_no_alert_when_runway_above_30_days(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """No procurement alert when runway > 30 days."""
    # balance=400_000, daily_burn=10_000 -> 40 days
    async with session_factory() as session:
        await session.execute(
            text(
                "UPDATE provider_accounts "
                "SET balance_paise = 400000, daily_burn_rate_paise = 10000 "
                "WHERE id = :pid"
            ).bindparams(pid=str(test_provider_account_id))
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(test_customer_id)
    procurement_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    assert procurement_alerts == []


# ---------------------------------------------------------------------------
# Tests: run_daily_scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_daily_scan_returns_daily_scan_result(
    meter_service: MeterService,
    setup_test_data: tuple,
) -> None:
    """run_daily_scan returns a DailyScanResult with non-negative counts."""
    result = await meter_service.run_daily_scan()
    assert isinstance(result, DailyScanResult)
    assert result.customers_scanned >= 0
    assert result.alerts_sent >= 0
    assert result.fa_items_created >= 0


@pytest.mark.asyncio
async def test_daily_scan_calls_check_thresholds_for_all_active_customers(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """run_daily_scan scans every active customer (wallet_buckets.is_active=1)."""
    # Add a second active customer
    second_customer = uuid4()
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO wallet_buckets "
                "(id, customer_id, thread_type, balance_paise, is_active) "
                "VALUES (:id, :customer_id, :thread_type, :balance, 1)"
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(second_customer),
                thread_type="GENIE",
                balance=500_000,
            )
        )
        await session.commit()

    result = await meter_service.run_daily_scan()
    # Both test_customer_id and second_customer should be scanned
    assert result.customers_scanned >= 2


@pytest.mark.asyncio
async def test_run_daily_scan_no_customers_returns_zero(
    meter_service: MeterService,
) -> None:
    """run_daily_scan with no active customers returns zeros (empty DB)."""
    result = await meter_service.run_daily_scan()
    assert result.customers_scanned == 0
    assert result.alerts_sent == 0


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_thresholds_missing_customer_returns_empty(
    meter_service: MeterService,
) -> None:
    """check_thresholds with unknown customer_id returns empty list (no buckets)."""
    unknown_id = uuid4()
    alerts = await meter_service.check_thresholds(unknown_id)
    assert alerts == []


@pytest.mark.asyncio
async def test_check_thresholds_zero_quota_bucket_skipped(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
) -> None:
    """Buckets with balance_paise=0 are skipped (division by zero guard)."""
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO wallet_buckets "
                "(id, customer_id, thread_type, balance_paise, is_active) "
                "VALUES (:id, :customer_id, 'ZERO_BUCKET', 0, 1)"
            ).bindparams(
                id=str(uuid4()),
                customer_id=str(test_customer_id),
            )
        )
        await session.commit()

    alerts = await meter_service.check_thresholds(test_customer_id)
    zero_bucket_alerts = [a for a in alerts if a.bucket_type == "ZERO_BUCKET"]
    assert zero_bucket_alerts == []


@pytest.mark.asyncio
async def test_check_thresholds_alert_recorded_in_meter_alert_log(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """Every fired alert must produce a row in meter_alert_log (C-059 evidence)."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.72),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    assert len(alerts) > 0

    async with session_factory() as session:
        row = await session.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM meter_alert_log "
                "WHERE customer_id = :cid"
            ).bindparams(cid=str(test_customer_id))
        )
        result = row.fetchone()
    assert result is not None
    assert result.cnt == len(alerts)


@pytest.mark.asyncio
async def test_procurement_zero_burn_rate_skipped(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """Provider with daily_burn_rate_paise=0 must not trigger division by zero."""
    async with session_factory() as session:
        await session.execute(
            text(
                "UPDATE provider_accounts SET daily_burn_rate_paise = 0 "
                "WHERE id = :pid"
            ).bindparams(pid=str(test_provider_account_id))
        )
        await session.commit()

    # Should not raise
    alerts = await meter_service.check_thresholds(test_customer_id)
    procurement_alerts = [a for a in alerts if a.scope == "PROCUREMENT"]
    assert procurement_alerts == []


@pytest.mark.asyncio
async def test_meter_service_cancellation_propagated() -> None:
    """CancelledError from session_factory propagates out of record_usage."""
    factory = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(side_effect=asyncio.CancelledError())
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm

    svc = MeterService(session_factory=factory)
    with pytest.raises(asyncio.CancelledError):
        await svc.record_usage(uuid4(), "GENIE", 1000)


@pytest.mark.asyncio
async def test_alert_fired_dataclass_fields(
    meter_service: MeterService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_provider_account_id: UUID,
    setup_test_data: tuple,
) -> None:
    """AlertFired instances contain correct customer_id, scope, and fired_at."""
    _, quota_paise = setup_test_data
    now_utc = datetime.now(timezone.utc)
    period_start = _current_billing_period_start(now_utc)

    await _insert_ledger_row(
        session_factory,
        test_customer_id,
        "GENIE",
        test_provider_account_id,
        int(quota_paise * 0.72),
        period_start,
    )

    alerts = await meter_service.check_thresholds(test_customer_id)
    scope1_alerts = [a for a in alerts if a.scope == "CUSTOMER_BUCKET"]
    assert len(scope1_alerts) > 0

    alert = scope1_alerts[0]
    assert alert.customer_id == test_customer_id
    assert alert.bucket_type == "GENIE"
    assert alert.pct_consumed >= 0.70
    assert isinstance(alert.fired_at, datetime)