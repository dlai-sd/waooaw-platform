# Implements: tests/billing-engine/test_service.py
# constitutional_basis: C-043 (budget ceiling), C-049 (honest limitation),
#                       C-059 (traceability), C-073 (annotations), C-076 (coverage)
# ib_item: IB-009
"""
Manually authored test suite for MeterService + AlertPolicy.
No hypothesis property tests — domain invariants are threshold-specific, not algebraic.
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from meter.alert_policy import (
    AGENCY_POLICY,
    CUSTOMER_BUCKET_POLICY,
    PROCUREMENT_POLICY,
    AlertAction,
    AlertScope,
    RunwayThresholdRule,
    ThresholdPolicy,
    ThresholdRule,
)
from meter.service import (
    MeterService,
    _current_billing_period_start,
    _is_quiet_hours,
    _now_ist,
)

_IST_TZ = timezone(timedelta(hours=5, minutes=30))

_DDL = [
    """CREATE TABLE IF NOT EXISTS thread_catalog (
        id TEXT NOT NULL PRIMARY KEY,
        thread_type TEXT NOT NULL,
        provider_account_id TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS provider_accounts (
        id TEXT NOT NULL PRIMARY KEY,
        provider_name TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        daily_burn_rate_paise INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS platform_cost_ledger (
        id TEXT NOT NULL PRIMARY KEY,
        customer_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        provider_account_id TEXT NOT NULL,
        marked_up_cost_inr_paise INTEGER NOT NULL DEFAULT 0,
        recorded_at TEXT NOT NULL,
        billing_period_start TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS wallet_buckets (
        id TEXT NOT NULL PRIMARY KEY,
        customer_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        available_paise INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS agency_sub_wallets (
        id TEXT NOT NULL PRIMARY KEY,
        customer_id TEXT NOT NULL,
        quota_paise INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS meter_alert_log (
        id TEXT NOT NULL PRIMARY KEY,
        customer_id TEXT NOT NULL,
        bucket_type TEXT NOT NULL,
        threshold_name TEXT NOT NULL,
        pct_consumed REAL NOT NULL DEFAULT 0,
        scope TEXT NOT NULL,
        fired_at TEXT NOT NULL
    )""",
]


@pytest.fixture
async def in_memory_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        for stmt in _DDL:
            await conn.execute(text(stmt))
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(in_memory_engine):
    return async_sessionmaker(in_memory_engine, expire_on_commit=False)


@pytest.fixture
def meter_service(session_factory):
    return MeterService(session_factory, redis_pool=None)


@pytest.fixture
def test_customer_id():
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def test_provider_account_id():
    return UUID("22222222-2222-2222-2222-222222222222")


async def _insert_bucket(sf, customer_id, thread_type, balance_paise, is_active=1):
    async with sf() as s:
        await s.execute(
            text("INSERT INTO wallet_buckets (id, customer_id, thread_type, balance_paise, is_active) "
                 "VALUES (:id, :cid, :tt, :bal, :ia)")
            .bindparams(id=str(uuid4()), cid=str(customer_id), tt=thread_type, bal=balance_paise, ia=is_active)
        )
        await s.commit()


async def _insert_spend(sf, customer_id, thread_type, provider_id, amount_paise):
    now = datetime.now(timezone.utc)
    period = _current_billing_period_start(now)
    async with sf() as s:
        await s.execute(
            text("INSERT INTO platform_cost_ledger "
                 "(id, customer_id, thread_type, provider_account_id, "
                 "marked_up_cost_inr_paise, recorded_at, billing_period_start) "
                 "VALUES (:id, :cid, :tt, :pid, :amt, :rat, :bps)")
            .bindparams(id=str(uuid4()), cid=str(customer_id), tt=thread_type,
                        pid=str(provider_id), amt=amount_paise, rat=now, bps=str(period))
        )
        await s.commit()


async def _insert_thread_catalog(sf, thread_type, provider_account_id):
    async with sf() as s:
        await s.execute(
            text("INSERT INTO thread_catalog (id, thread_type, provider_account_id) "
                 "VALUES (:id, :tt, :pid)")
            .bindparams(id=str(uuid4()), tt=thread_type, pid=str(provider_account_id))
        )
        await s.commit()


async def _insert_provider_account(sf, provider_id, provider_name, balance, burn_rate, is_active=1):
    async with sf() as s:
        await s.execute(
            text("INSERT INTO provider_accounts "
                 "(id, provider_name, balance_paise, daily_burn_rate_paise, is_active) "
                 "VALUES (:id, :name, :bal, :br, :ia)")
            .bindparams(id=str(provider_id), name=provider_name, bal=balance, br=burn_rate, ia=is_active)
        )
        await s.commit()


async def _insert_agency_sub_wallet(sf, customer_id, quota_paise):
    async with sf() as s:
        await s.execute(
            text("INSERT INTO agency_sub_wallets (id, customer_id, quota_paise) "
                 "VALUES (:id, :cid, :q)")
            .bindparams(id=str(uuid4()), cid=str(customer_id), q=quota_paise)
        )
        await s.commit()


async def _insert_alert_log(sf, customer_id, bucket_type, threshold_name, fired_at):
    # fired_at MUST be a datetime object, not .isoformat():
    # SQLAlchemy → 'YYYY-MM-DD HH:MM:SS' (space); .isoformat() → T-separator
    # SQLite string compare: 'T'(84) > ' '(32) → stale rows sort after dedup window
    async with sf() as s:
        await s.execute(
            text("INSERT INTO meter_alert_log "
                 "(id, customer_id, bucket_type, threshold_name, pct_consumed, scope, fired_at) "
                 "VALUES (:id, :cid, :bt, :tn, :pc, :sc, :fa)")
            .bindparams(id=str(uuid4()), cid=str(customer_id), bt=bucket_type,
                        tn=threshold_name, pc=0.75, sc="CUSTOMER_BUCKET", fa=fired_at)
        )
        await s.commit()


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

def test_current_billing_period_start_returns_first_day_of_month():
    dt = datetime(2026, 8, 15, 10, 30, tzinfo=timezone.utc)
    assert _current_billing_period_start(dt) == date(2026, 8, 1)


def test_current_billing_period_start_on_first():
    dt = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    assert _current_billing_period_start(dt) == date(2026, 8, 1)


def test_is_quiet_hours_inside_window():
    now = datetime(2026, 8, 5, 23, 30, tzinfo=_IST_TZ)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, now) is True


def test_is_quiet_hours_outside_window():
    now = datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, now) is False


def test_is_quiet_hours_boundary_start():
    now = datetime(2026, 8, 5, 23, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, now) is True


def test_is_quiet_hours_boundary_end():
    # hour=6 is the END — not quiet (h < 6 is False)
    now = datetime(2026, 8, 5, 6, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, now) is False


def test_is_quiet_hours_early_morning():
    now = datetime(2026, 8, 5, 3, 0, tzinfo=_IST_TZ)
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, now) is True


def test_now_ist_is_ist_offset():
    assert _now_ist().utcoffset() == timedelta(hours=5, minutes=30)


def test_now_ist_is_timezone_aware():
    assert _now_ist().tzinfo is not None


# ---------------------------------------------------------------------------
# MeterService init
# ---------------------------------------------------------------------------

def test_meter_service_init_stores_session_factory(session_factory):
    svc = MeterService(session_factory)
    assert svc._session_factory is session_factory


def test_meter_service_init_redis_pool_none(session_factory):
    svc = MeterService(session_factory, redis_pool=None)
    assert svc._redis_pool is None


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------

async def test_record_usage_happy_path(meter_service, session_factory, test_customer_id, test_provider_account_id):
    await _insert_provider_account(session_factory, test_provider_account_id, "test", 0, 0)
    await _insert_thread_catalog(session_factory, "GENIE", test_provider_account_id)
    await meter_service.record_usage(test_customer_id, "GENIE", 5000)
    async with session_factory() as s:
        row = (await s.execute(
            text("SELECT COUNT(*) AS cnt FROM platform_cost_ledger WHERE customer_id = :cid")
            .bindparams(cid=str(test_customer_id))
        )).fetchone()
    assert row.cnt == 1


async def test_record_usage_unknown_thread_type_logs_and_returns(meter_service, test_customer_id):
    await meter_service.record_usage(test_customer_id, "UNKNOWN_TYPE", 100)


async def test_record_usage_multiple_calls_accumulate(meter_service, session_factory, test_customer_id, test_provider_account_id):
    await _insert_provider_account(session_factory, test_provider_account_id, "test", 0, 0)
    await _insert_thread_catalog(session_factory, "GENIE", test_provider_account_id)
    await meter_service.record_usage(test_customer_id, "GENIE", 1000)
    await meter_service.record_usage(test_customer_id, "GENIE", 2000)
    async with session_factory() as s:
        row = (await s.execute(
            text("SELECT COUNT(*) AS cnt FROM platform_cost_ledger WHERE customer_id = :cid")
            .bindparams(cid=str(test_customer_id))
        )).fetchone()
    assert row.cnt == 2


# ---------------------------------------------------------------------------
# project_depletion
# ---------------------------------------------------------------------------

async def test_project_depletion_no_usage_returns_inf(meter_service, session_factory, test_customer_id):
    await _insert_bucket(session_factory, test_customer_id, "GENIE", 1_000_000)
    result = await meter_service.project_depletion(test_customer_id, "GENIE")
    assert result.days_remaining == 999.0


async def test_project_depletion_with_usage(meter_service, session_factory, test_customer_id, test_provider_account_id):
    # 700K spend over 7 days = 100K/day; 1M balance → 10 days
    await _insert_bucket(session_factory, test_customer_id, "GENIE", 1_000_000)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, 700_000)
    result = await meter_service.project_depletion(test_customer_id, "GENIE")
    assert result.days_remaining == pytest.approx(10.0, rel=0.01)


async def test_project_depletion_returns_depletion_projection_type(meter_service, session_factory, test_customer_id):
    await _insert_bucket(session_factory, test_customer_id, "GENIE", 500_000)
    from meter.service import DepletionProjection
    assert isinstance(await meter_service.project_depletion(test_customer_id, "GENIE"), DepletionProjection)


# ---------------------------------------------------------------------------
# check_thresholds — scope 1
# ---------------------------------------------------------------------------

async def test_check_thresholds_no_consumption_fires_no_alerts(meter_service, session_factory, test_customer_id):
    await _insert_bucket(session_factory, test_customer_id, "GENIE", 1_000_000)
    assert await meter_service.check_thresholds(test_customer_id) == []


async def test_check_thresholds_warn_30_fires_at_70_pct(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.70))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert "WARN_30" in [a.threshold_name for a in alerts]


async def test_check_thresholds_warn_20_and_warn_10_fire_at_correct_pct(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.90))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    names = [a.threshold_name for a in alerts]
    assert "WARN_30" in names
    assert "WARN_20" in names
    assert "WARN_10" in names


async def test_check_thresholds_ad_wallet_below_minimum_at_100_pct(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, quota)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert "AD_WALLET_BELOW_MINIMUM" in [a.threshold_name for a in alerts]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

async def test_no_double_fire_within_24h_deduplication_window(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.72))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        first = await meter_service.check_thresholds(test_customer_id)
        second = await meter_service.check_thresholds(test_customer_id)
    assert any(a.threshold_name == "WARN_30" for a in first)
    assert not any(a.threshold_name == "WARN_30" for a in second)


async def test_alert_fires_again_after_dedup_window_expires(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    now_utc = datetime.now(timezone.utc)
    # Seed a stale alert from 25h ago — outside the 24h dedup window
    await _insert_alert_log(session_factory, test_customer_id, "GENIE", "WARN_30",
                             now_utc - timedelta(hours=25))
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.72))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert "WARN_30" in [a.threshold_name for a in alerts], "WARN_30 must re-fire after dedup window expires"


# ---------------------------------------------------------------------------
# Quiet hours
# ---------------------------------------------------------------------------

async def test_quiet_hours_suppress_notify_alerts(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.72))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 23, 30, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert not any(a.threshold_name == "WARN_30" for a in alerts)


async def test_quiet_hours_do_not_suppress_bypass_true_alerts(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, quota)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 23, 30, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert any(a.threshold_name == "AD_WALLET_BELOW_MINIMUM" for a in alerts)


# ---------------------------------------------------------------------------
# Scope 2 — agency sub-wallet
# ---------------------------------------------------------------------------

async def test_agency_alert_fires_at_50_pct(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_agency_sub_wallet(session_factory, test_customer_id, quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.50))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert "AGENCY_WARN_50" in [a.threshold_name for a in alerts]


async def test_agency_null_quota_produces_no_alert(meter_service, session_factory, test_customer_id, test_provider_account_id):
    await _insert_agency_sub_wallet(session_factory, test_customer_id, None)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, 500_000)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert not any(a.scope == "AGENCY" for a in alerts)


# ---------------------------------------------------------------------------
# Scope 3 — procurement runway
# ---------------------------------------------------------------------------

async def test_procurement_runway_p0_fires_at_7_days(meter_service, session_factory, test_customer_id, test_provider_account_id):
    burn = 100_000
    await _insert_provider_account(session_factory, test_provider_account_id, "anthropic", 7 * burn, burn)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert "RUNWAY_P0" in [a.threshold_name for a in alerts]


async def test_procurement_runway_emergency_fires_at_1_day(meter_service, session_factory, test_customer_id, test_provider_account_id):
    burn = 100_000
    await _insert_provider_account(session_factory, test_provider_account_id, "anthropic", 1 * burn, burn)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert "RUNWAY_EMERGENCY" in [a.threshold_name for a in alerts]


async def test_procurement_no_alert_when_runway_sufficient(meter_service, session_factory, test_customer_id, test_provider_account_id):
    burn = 100_000
    await _insert_provider_account(session_factory, test_provider_account_id, "anthropic", 100 * burn, burn)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    assert not any(a.scope == "PROCUREMENT" for a in alerts)


# ---------------------------------------------------------------------------
# AlertFired fields
# ---------------------------------------------------------------------------

async def test_alert_fired_fields_populated(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.72))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    warn = next(a for a in alerts if a.threshold_name == "WARN_30")
    assert warn.customer_id == test_customer_id
    assert warn.bucket_type == "GENIE"
    assert warn.scope == "CUSTOMER_BUCKET"
    assert warn.pct_consumed == pytest.approx(0.72, rel=0.01)
    assert warn.fired_at is not None


# ---------------------------------------------------------------------------
# run_daily_scan
# ---------------------------------------------------------------------------

async def test_run_daily_scan_returns_daily_scan_result(meter_service):
    from meter.service import DailyScanResult
    assert isinstance(await meter_service.run_daily_scan(), DailyScanResult)


async def test_run_daily_scan_scans_active_customers(meter_service, session_factory):
    cid1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    cid2 = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    await _insert_bucket(session_factory, cid1, "GENIE", 1_000_000, is_active=1)
    await _insert_bucket(session_factory, cid2, "GENIE", 1_000_000, is_active=1)
    result = await meter_service.run_daily_scan()
    assert result.customers_scanned == 2


async def test_run_daily_scan_does_not_scan_inactive_customers(meter_service, session_factory):
    cid_active = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    cid_inactive = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    await _insert_bucket(session_factory, cid_active, "GENIE", 1_000_000, is_active=1)
    await _insert_bucket(session_factory, cid_inactive, "GENIE", 1_000_000, is_active=0)
    result = await meter_service.run_daily_scan()
    assert result.customers_scanned == 1


async def test_run_daily_scan_aggregates_alerts_sent(meter_service, session_factory, test_customer_id, test_provider_account_id):
    quota = 1_000_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota, is_active=1)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, int(quota * 0.72))
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        result = await meter_service.run_daily_scan()
    assert result.customers_scanned == 1
    assert result.alerts_sent >= 1


async def test_run_daily_scan_fa_items_counted_correctly(meter_service, session_factory, test_customer_id, test_provider_account_id):
    # RUNWAY_P0 (<=7 days) has action=FA
    burn = 100_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", 1_000_000, is_active=1)
    await _insert_provider_account(session_factory, test_provider_account_id, "anthropic", 7 * burn, burn)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        result = await meter_service.run_daily_scan()
    assert result.fa_items_created >= 1


# ---------------------------------------------------------------------------
# CCT-BILLINGLOOP-01 (C-043)
# ---------------------------------------------------------------------------

async def test_cct_billingloop_01_ad_wallet_hits_zero(meter_service, session_factory, test_customer_id, test_provider_account_id):
    """C-043: AD_WALLET_BELOW_MINIMUM fires exactly once when balance reaches zero."""
    quota = 500_000
    await _insert_bucket(session_factory, test_customer_id, "GENIE", quota)
    await _insert_spend(session_factory, test_customer_id, "GENIE", test_provider_account_id, quota)
    with patch("meter.service._now_ist", return_value=datetime(2026, 8, 5, 10, 0, tzinfo=_IST_TZ)):
        alerts = await meter_service.check_thresholds(test_customer_id)
    ad_alerts = [a for a in alerts if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"]
    assert len(ad_alerts) == 1


# ---------------------------------------------------------------------------
# Alert policy — structure tests
# ---------------------------------------------------------------------------

def test_customer_bucket_policy_has_warn_30():
    assert "WARN_30" in [r.name for r in CUSTOMER_BUCKET_POLICY.rules]


def test_customer_bucket_policy_has_ad_wallet_below_minimum():
    assert "AD_WALLET_BELOW_MINIMUM" in [r.name for r in CUSTOMER_BUCKET_POLICY.rules]


def test_agency_policy_has_critical_fa_action():
    rule = next(r for r in AGENCY_POLICY.rules if r.name == "AGENCY_CRITICAL")
    assert rule.action == AlertAction.FA


def test_procurement_policy_has_runway_p0():
    assert "RUNWAY_P0" in [r.name for r in PROCUREMENT_POLICY.runway_thresholds]


def test_procurement_policy_has_runway_emergency():
    assert "RUNWAY_EMERGENCY" in [r.name for r in PROCUREMENT_POLICY.runway_thresholds]


def test_procurement_policy_has_runway_p2():
    assert "RUNWAY_P2" in [r.name for r in PROCUREMENT_POLICY.runway_thresholds]


def test_procurement_policy_has_runway_p1():
    assert "RUNWAY_P1" in [r.name for r in PROCUREMENT_POLICY.runway_thresholds]


def test_procurement_policy_has_runway_critical():
    assert "RUNWAY_CRITICAL" in [r.name for r in PROCUREMENT_POLICY.runway_thresholds]


def test_warn_30_trigger_is_70_pct():
    rule = next(r for r in CUSTOMER_BUCKET_POLICY.rules if r.name == "WARN_30")
    assert isinstance(rule, ThresholdRule)
    assert rule.consumed_pct_trigger == pytest.approx(0.70)


def test_ad_wallet_below_minimum_has_block_action():
    rule = next(r for r in CUSTOMER_BUCKET_POLICY.rules if r.name == "AD_WALLET_BELOW_MINIMUM")
    assert rule.action == AlertAction.BLOCK


def test_ad_wallet_below_minimum_bypass_quiet_hours():
    rule = next(r for r in CUSTOMER_BUCKET_POLICY.rules if r.name == "AD_WALLET_BELOW_MINIMUM")
    assert rule.bypass_quiet_hours is True


def test_customer_bucket_policy_scope():
    assert CUSTOMER_BUCKET_POLICY.scope == AlertScope.CUSTOMER_BUCKET


def test_agency_policy_scope():
    assert AGENCY_POLICY.scope == AlertScope.AGENCY


def test_procurement_policy_scope():
    assert PROCUREMENT_POLICY.scope == AlertScope.PROCUREMENT
