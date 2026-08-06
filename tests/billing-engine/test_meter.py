# Implements: work-contracts/WC-028-*.md §WC028-03:test_meter.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers: mock AsyncSession with side-effected execute calls
# ---------------------------------------------------------------------------


def _mock_session(*execute_side_effects):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock(side_effect=list(execute_side_effects))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _fetchone_result(row):
    r = MagicMock()
    r.fetchone = MagicMock(return_value=row)
    return r


def _fetchall_result(rows):
    r = MagicMock()
    r.fetchall = MagicMock(return_value=rows)
    return r


def _mock_row(**kwargs):
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _make_service(session):
    from meter.service import MeterService

    sf = MagicMock()
    sf.return_value = session
    return MeterService(session_factory=sf)


# ===========================================================================
# UNIT TESTS: record_usage
# ===========================================================================


@pytest.mark.asyncio
async def test_record_usage_writes_to_platform_cost_ledger() -> None:
    """record_usage: resolves provider then inserts into platform_cost_ledger."""
    customer_id = uuid4()
    provider_row = _mock_row(provider_account_id=uuid4())
    session = _mock_session(
        _fetchone_result(provider_row),
        MagicMock(),
    )
    svc = _make_service(session)
    await svc.record_usage(customer_id, "DMA", 5000)

    assert session.execute.call_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_usage_no_write_when_provider_not_found() -> None:
    """record_usage: thread_catalog lookup returns None → no INSERT."""
    customer_id = uuid4()
    session = _mock_session(_fetchone_result(None))
    svc = _make_service(session)
    await svc.record_usage(customer_id, "UNKNOWN_THREAD", 5000)

    assert session.execute.call_count == 1
    session.commit.assert_not_awaited()


# ===========================================================================
# UNIT TESTS: project_depletion
# ===========================================================================


@pytest.mark.asyncio
async def test_project_depletion_returns_7d_rolling_avg() -> None:
    """project_depletion: 35000 spend / 7d = 5000/day; 50000 balance → 10 days."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchone_result(_mock_row(total_spend=35000)),
        _fetchone_result(_mock_row(balance_paise=50000)),
    )
    svc = _make_service(session)
    result = await svc.project_depletion(customer_id, "DMA")

    assert result.daily_burn_rate_paise == pytest.approx(5000.0)
    assert result.days_remaining == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_project_depletion_no_burn_returns_999_days() -> None:
    """project_depletion: zero spend → days_remaining=999 (infinite runway)."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchone_result(_mock_row(total_spend=0)),
        _fetchone_result(_mock_row(balance_paise=50000)),
    )
    svc = _make_service(session)
    result = await svc.project_depletion(customer_id, "DMA")

    assert result.days_remaining == pytest.approx(999.0)
    assert result.daily_burn_rate_paise == pytest.approx(0.0)


# ===========================================================================
# UNIT TESTS: check_thresholds - Scope 1
# ===========================================================================


@pytest.mark.asyncio
async def test_threshold_fires_at_correct_percentage() -> None:
    """70% consumed (30% remaining) fires WARN_30. C-043."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=70000)]),
        _fetchone_result(_mock_row(balance_paise=100000)),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_30 dedup
        MagicMock(),  # WARN_30 persist
        _fetchone_result(None),  # scope2 skip
        _fetchall_result([]),  # scope3 skip
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "WARN_30" in names
    pct = next(a.pct_consumed for a in alerts if a.threshold_name == "WARN_30")
    assert pct == pytest.approx(0.70)


@pytest.mark.asyncio
async def test_threshold_fires_warn10_at_8_percent_remaining() -> None:
    """92% consumed (8% remaining) fires WARN_10. DoD check."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=92000)]),
        _fetchone_result(_mock_row(balance_paise=100000)),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_30
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_20
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_10
        MagicMock(),
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert "WARN_10" in [a.threshold_name for a in alerts]


@pytest.mark.asyncio
async def test_threshold_fires_at_50_percent_consumed() -> None:
    """50% consumed — lowest trigger is 70%, so no alert fires."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=50000)]),
        _fetchone_result(_mock_row(balance_paise=100000)),
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_no_double_fire_within_24h_deduplication_window() -> None:
    """Second call within 24h → dedup returns cnt=1 → empty list. DoD."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=70000)]),
        _fetchone_result(_mock_row(balance_paise=100000)),
        _fetchone_result(_mock_row(cnt=1)),  # already fired
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_quiet_hours_suppress_whatsapp_notifications() -> None:
    """
    23:15 IST quiet hours: WARN_30 (bypass=False) suppressed,
    WARN_10 (bypass=True) fires. DoD.
    """
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=92000)]),
        _fetchone_result(_mock_row(balance_paise=100000)),
        # Only WARN_10 passes quiet check (bypass_quiet_hours=True)
        _fetchone_result(_mock_row(cnt=0)),  # WARN_10 dedup
        MagicMock(),  # WARN_10 persist
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    quiet_ist = datetime(2026, 8, 1, 23, 15, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=quiet_ist):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "WARN_30" not in names
    assert "WARN_20" not in names
    assert "WARN_10" in names


@pytest.mark.asyncio
async def test_agency_null_quota_produces_no_alert() -> None:
    """agency_sub_wallets.quota_paise=None → no scope2 alert. DoD."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(_mock_row(id=uuid4(), quota_paise=None)),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_agency_missing_wallet_produces_no_alert() -> None:
    """No agency_sub_wallets row → no scope2 alert."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


# ===========================================================================
# UNIT TESTS: check_thresholds - Scope 3 (procurement)
# ===========================================================================


@pytest.mark.asyncio
async def test_procurement_runway_p0_escalation_at_7_days() -> None:
    """5 days remaining → RUNWAY_P2, RUNWAY_P1, RUNWAY_P0 all fire. DoD."""
    customer_id = uuid4()
    provider_row = _mock_row(
        id=uuid4(), provider_name="openai",
        balance_paise=5000, daily_burn_rate_paise=1000,
    )
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(None),
        _fetchall_result([provider_row]),
        _fetchone_result(_mock_row(cnt=0)),  # RUNWAY_P2 dedup
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # RUNWAY_P1 dedup
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # RUNWAY_P0 dedup
        MagicMock(),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "RUNWAY_P0" in names
    assert all(a.scope == "PROCUREMENT" for a in alerts)


@pytest.mark.asyncio
async def test_scope3_skips_provider_with_zero_burn_rate() -> None:
    """Scope3: daily_burn_rate_paise=0 → no division, no alert."""
    customer_id = uuid4()
    provider_row = _mock_row(
        id=uuid4(), provider_name="openai",
        balance_paise=5000, daily_burn_rate_paise=0,
    )
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(None),
        _fetchall_result([provider_row]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_scope3_provider_with_null_burn_rate_is_skipped() -> None:
    """Scope3: daily_burn_rate_paise=None → treated as 0 → no alert."""
    customer_id = uuid4()
    provider_row = _mock_row(
        id=uuid4(), provider_name="anthropic",
        balance_paise=10000, daily_burn_rate_paise=None,
    )
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(None),
        _fetchall_result([provider_row]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


# ===========================================================================
# UNIT TESTS: run_daily_scan
# ===========================================================================


@pytest.mark.asyncio
async def test_post_meter_daily_scan_calls_check_thresholds_for_all_customers() -> None:
    """run_daily_scan scans all customers. DoD."""
    cid1 = uuid4()
    cid2 = uuid4()
    fetch_session = _mock_session(
        _fetchall_result([_mock_row(customer_id=str(cid1)), _mock_row(customer_id=str(cid2))])
    )
    svc = _make_service(fetch_session)

    from skeleton.wbe_interfaces import AlertFired

    async def mock_check(cid):
        if cid == cid1:
            return [AlertFired(
                customer_id=cid1, bucket_type="DMA",
                threshold_name="WARN_30", pct_consumed=0.70,
                scope="CUSTOMER_BUCKET", fired_at=datetime.now(timezone.utc),
            )]
        return []

    svc.check_thresholds = mock_check  # type: ignore[method-assign]
    result = await svc.run_daily_scan()

    assert result.customers_scanned == 2
    assert result.alerts_sent == 1


@pytest.mark.asyncio
async def test_run_daily_scan_returns_zero_when_no_customers() -> None:
    """run_daily_scan: empty wallet_buckets → 0 scanned, 0 alerts."""
    fetch_session = _mock_session(_fetchall_result([]))
    svc = _make_service(fetch_session)

    async def mock_check(cid):
        return []

    svc.check_thresholds = mock_check  # type: ignore[method-assign]
    result = await svc.run_daily_scan()

    assert result.customers_scanned == 0
    assert result.alerts_sent == 0


# ===========================================================================
# CCT-BILLINGLOOP-01: AD wallet hits zero
# ===========================================================================


@pytest.mark.asyncio
async def test_cct_billingloop_01_ad_wallet_hits_zero() -> None:
    """
    CCT-BILLINGLOOP-01: AD wallet consumed 100% → AD_WALLET_BELOW_MINIMUM fires.
    DoD: alerts_sent == 1 type AD_WALLET_BELOW_MINIMUM. C-043, C-049.
    """
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=100000)]),
        _fetchone_result(_mock_row(balance_paise=100000)),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_30
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_20
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # WARN_10
        MagicMock(),
        _fetchone_result(_mock_row(cnt=0)),  # AD_WALLET_BELOW_MINIMUM
        MagicMock(),
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "AD_WALLET_BELOW_MINIMUM" in names
    ad = [a for a in alerts if a.threshold_name == "AD_WALLET_BELOW_MINIMUM"]
    assert len(ad) == 1
    assert ad[0].scope == "CUSTOMER_BUCKET"


# ===========================================================================
# ROUTER TESTS
# ===========================================================================


@pytest.mark.asyncio
async def test_get_usage_status_returns_200() -> None:
    """GET /meter/{customer_id}/status → 200 with UsageStatus. DoD."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from meter.router import get_meter_service

    customer_id = uuid4()
    mock_svc = MagicMock()
    # Router's get_usage_status returns a placeholder UsageStatus without calling svc method
    app.dependency_overrides[get_meter_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/meter/{customer_id}/status")
    finally:
        app.dependency_overrides.pop(get_meter_service, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_id"] == str(customer_id)
    assert "billing_halted" in data


@pytest.mark.asyncio
async def test_post_daily_scan_returns_200() -> None:
    """POST /meter/daily-scan → 200 with DailyScanResult. DoD."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from meter.router import get_meter_service
    from skeleton.wbe_interfaces import DailyScanResult

    mock_svc = MagicMock()
    mock_svc.run_daily_scan = AsyncMock(
        return_value=DailyScanResult(
            customers_scanned=3, alerts_sent=2, offers_generated=0, fa_items_created=1
        )
    )
    app.dependency_overrides[get_meter_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/meter/daily-scan")
    finally:
        app.dependency_overrides.pop(get_meter_service, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["customers_scanned"] == 3
    assert data["alerts_sent"] == 2


@pytest.mark.asyncio
async def test_post_daily_scan_503_when_service_unavailable() -> None:
    """POST /meter/daily-scan → 503 if service dep raises HTTPException."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from meter.router import get_meter_service
    from fastapi import HTTPException, status

    def _unavailable():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    app.dependency_overrides[get_meter_service] = _unavailable
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/meter/daily-scan")
    finally:
        app.dependency_overrides.pop(get_meter_service, None)

    assert resp.status_code == 503


# ===========================================================================
# ALERT POLICY UNIT TESTS
# ===========================================================================


def test_alert_policy_customer_bucket_thresholds() -> None:
    """CUSTOMER_BUCKET_POLICY has correct threshold names."""
    from meter.alert_policy import CUSTOMER_BUCKET_POLICY

    names = [r.name for r in CUSTOMER_BUCKET_POLICY.rules]
    assert "WARN_30" in names
    assert "WARN_10" in names
    assert "AD_WALLET_BELOW_MINIMUM" in names


def test_alert_policy_procurement_uses_runway_thresholds() -> None:
    """PROCUREMENT_POLICY.rules returns RunwayThresholdRule instances."""
    from meter.alert_policy import PROCUREMENT_POLICY, RunwayThresholdRule

    rules = PROCUREMENT_POLICY.rules
    assert all(isinstance(r, RunwayThresholdRule) for r in rules)
    names = [r.name for r in rules]
    assert "RUNWAY_P0" in names
    assert "RUNWAY_EMERGENCY" in names


def test_alert_policy_quiet_hours_wraps_midnight() -> None:
    """_is_quiet_hours: 23:15 → True; noon → False; 05:30 → True."""
    from meter.service import _is_quiet_hours
    from meter.alert_policy import CUSTOMER_BUCKET_POLICY

    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, datetime(2026, 8, 1, 23, 15, tzinfo=timezone.utc)) is True
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)) is False
    assert _is_quiet_hours(CUSTOMER_BUCKET_POLICY, datetime(2026, 8, 1, 5, 30, tzinfo=timezone.utc)) is True


# ===========================================================================
# WHATSAPP NOTIFIER UNIT TEST
# ===========================================================================


@pytest.mark.asyncio
async def test_whatsapp_notifier_send_raises_not_implemented() -> None:
    """WhatsAppNotifier.send() raises NotImplementedError (stub pending ADR-023)."""
    from meter.whatsapp_notifier import WhatsAppNotifier

    notifier = WhatsAppNotifier()
    with pytest.raises(NotImplementedError):
        await notifier.send(uuid4(), "tmpl_001", {"amount": "100"})


# ===========================================================================
# HYPOTHESIS invariants
# ===========================================================================


@given(
    consumed=st.integers(min_value=0, max_value=10**9),
    quota=st.integers(min_value=1, max_value=10**9),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
def test_threshold_percentage_invariant(consumed: int, quota: int) -> None:
    """pct_consumed < 0.70 → no CUSTOMER_BUCKET_POLICY rule fires."""
    from meter.alert_policy import CUSTOMER_BUCKET_POLICY, ThresholdRule

    pct = consumed / quota
    if pct < 0.70:
        fired = sum(
            1 for r in CUSTOMER_BUCKET_POLICY.rules
            if isinstance(r, ThresholdRule) and pct >= r.consumed_pct_trigger
        )
        assert fired == 0


@given(days_remaining=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False))
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
def test_runway_threshold_invariant(days_remaining: float) -> None:
    """RUNWAY_EMERGENCY fires iff days_remaining <= 1.0."""
    from meter.alert_policy import PROCUREMENT_POLICY, RunwayThresholdRule

    for rule in PROCUREMENT_POLICY.rules:
        if isinstance(rule, RunwayThresholdRule) and rule.name == "RUNWAY_EMERGENCY":
            fires = days_remaining <= rule.days_remaining_trigger
            assert fires == (days_remaining <= 1.0)


# ===========================================================================
# ADDITIONAL COVERAGE TESTS
# ===========================================================================


def test_now_ist_returns_ist_time() -> None:
    """_now_ist() returns a datetime with IST UTC offset (+5:30)."""
    from meter.service import _now_ist
    from datetime import timedelta

    result = _now_ist()
    assert result.tzinfo is not None
    # IST = UTC+5:30 = 19800 seconds
    assert result.utcoffset() == timedelta(hours=5, minutes=30)


@pytest.mark.asyncio
async def test_scope1_skips_bucket_with_none_result() -> None:
    """scope1: wallet_buckets returns None for a thread_type → that type is skipped."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=80000)]),
        _fetchone_result(None),  # bucket not found → skip
        _fetchone_result(None),  # scope2
        _fetchall_result([]),  # scope3
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_scope1_skips_bucket_with_zero_balance() -> None:
    """scope1: wallet_buckets.balance_paise=0 → division skipped, no alert."""
    customer_id = uuid4()
    session = _mock_session(
        _fetchall_result([_mock_row(thread_type="DMA", period_spend=80000)]),
        _fetchone_result(_mock_row(balance_paise=0)),
        _fetchone_result(None),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_scope2_agency_alert_fires_at_80_percent() -> None:
    """scope2: 80% consumed fires AGENCY_WARN_80."""
    customer_id = uuid4()
    agency_row = _mock_row(id=uuid4(), quota_paise=100000)
    spend_row = _mock_row(period_spend=80000)
    session = _mock_session(
        _fetchall_result([]),  # scope1 no thread types
        _fetchone_result(agency_row),  # scope2: quota found
        _fetchone_result(spend_row),  # scope2: period spend
        _fetchone_result(_mock_row(cnt=0)),  # AGENCY_WARN_50 dedup
        MagicMock(),  # AGENCY_WARN_50 persist
        _fetchone_result(_mock_row(cnt=0)),  # AGENCY_WARN_80 dedup
        MagicMock(),  # AGENCY_WARN_80 persist
        _fetchall_result([]),  # scope3
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "AGENCY_WARN_80" in names
    assert all(a.scope == "AGENCY" for a in alerts)


@pytest.mark.asyncio
async def test_scope2_agency_zero_quota_skipped() -> None:
    """scope2: quota_paise=0 → skip, no alert."""
    customer_id = uuid4()
    agency_row = _mock_row(id=uuid4(), quota_paise=0)
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(agency_row),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    midday = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=midday):
        alerts = await svc.check_thresholds(customer_id)

    assert alerts == []


@pytest.mark.asyncio
async def test_scope3_quiet_hours_suppress_runway_p2() -> None:
    """scope3: RUNWAY_P2 (bypass=False) suppressed at quiet hours 23:15 IST."""
    customer_id = uuid4()
    # 25 days remaining → triggers RUNWAY_P2 (≤30d) only
    provider_row = _mock_row(
        id=uuid4(), provider_name="openai",
        balance_paise=25000, daily_burn_rate_paise=1000,
    )
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(None),
        _fetchall_result([provider_row]),
        # RUNWAY_P2 is bypass=False → suppressed at quiet hours → no dedup/persist
    )
    svc = _make_service(session)
    quiet_ist = datetime(2026, 8, 1, 23, 15, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=quiet_ist):
        alerts = await svc.check_thresholds(customer_id)

    # RUNWAY_P2 suppressed (bypass=False), no others triggered at 25 days
    names = [a.threshold_name for a in alerts]
    assert "RUNWAY_P2" not in names


@pytest.mark.asyncio
async def test_record_usage_raises_on_runtime_error() -> None:
    """record_usage: execute raises RuntimeError → exception re-raised."""
    customer_id = uuid4()
    session = _mock_session()
    session.execute = AsyncMock(side_effect=RuntimeError("DB error"))
    svc = _make_service(session)

    with pytest.raises(RuntimeError):
        await svc.record_usage(customer_id, "DMA", 5000)


@pytest.mark.asyncio
async def test_project_depletion_raises_on_runtime_error() -> None:
    """project_depletion: execute raises RuntimeError → exception re-raised."""
    customer_id = uuid4()
    session = _mock_session()
    session.execute = AsyncMock(side_effect=RuntimeError("DB error"))
    svc = _make_service(session)

    with pytest.raises(RuntimeError):
        await svc.project_depletion(customer_id, "DMA")


@pytest.mark.asyncio
async def test_check_thresholds_raises_on_runtime_error() -> None:
    """check_thresholds: execute raises RuntimeError → exception re-raised."""
    customer_id = uuid4()
    session = _mock_session()
    session.execute = AsyncMock(side_effect=RuntimeError("DB error"))
    svc = _make_service(session)

    with pytest.raises(RuntimeError):
        await svc.check_thresholds(customer_id)


@pytest.mark.asyncio
async def test_run_daily_scan_fa_items_counted_for_fa_action_alerts() -> None:
    """run_daily_scan: AGENCY_CRITICAL (FA action) alert increments fa_items_created."""
    cid = uuid4()
    fetch_session = _mock_session(_fetchall_result([_mock_row(customer_id=str(cid))]))
    svc = _make_service(fetch_session)

    from skeleton.wbe_interfaces import AlertFired

    # AGENCY_CRITICAL has AlertAction.FA
    fa_alert = AlertFired(
        customer_id=cid,
        bucket_type="AGENCY",
        threshold_name="AGENCY_CRITICAL",
        pct_consumed=0.96,
        scope="AGENCY",
        fired_at=datetime.now(timezone.utc),
    )

    async def mock_check(c):
        return [fa_alert]

    svc.check_thresholds = mock_check  # type: ignore[method-assign]
    result = await svc.run_daily_scan()

    assert result.customers_scanned == 1
    assert result.alerts_sent == 1
    assert result.fa_items_created == 1


@pytest.mark.asyncio
async def test_run_daily_scan_handles_check_thresholds_error_gracefully() -> None:
    """run_daily_scan: check_thresholds RuntimeError is caught; scan continues."""
    cid = uuid4()
    fetch_session = _mock_session(_fetchall_result([_mock_row(customer_id=str(cid))]))
    svc = _make_service(fetch_session)

    async def mock_check_fail(c):
        raise RuntimeError("threshold check failed")

    svc.check_thresholds = mock_check_fail  # type: ignore[method-assign]
    result = await svc.run_daily_scan()

    # Should scan 1 customer but catch the error
    assert result.customers_scanned == 1
    assert result.alerts_sent == 0


@pytest.mark.asyncio
async def test_post_daily_scan_returns_500_on_service_error() -> None:
    """POST /meter/daily-scan → 500 when run_daily_scan raises."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from meter.router import get_meter_service

    mock_svc = MagicMock()
    mock_svc.run_daily_scan = AsyncMock(side_effect=RuntimeError("scan failed"))
    app.dependency_overrides[get_meter_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/meter/daily-scan")
    finally:
        app.dependency_overrides.pop(get_meter_service, None)

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_usage_status_503_when_service_unavailable() -> None:
    """GET /meter/{customer_id}/status → 503 if get_meter_service raises."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from meter.router import get_meter_service
    from fastapi import HTTPException, status

    customer_id = uuid4()

    def _unavailable():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    app.dependency_overrides[get_meter_service] = _unavailable
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/meter/{customer_id}/status")
    finally:
        app.dependency_overrides.pop(get_meter_service, None)

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_scope2_agency_quiet_hours_suppresses_non_bypass_rules() -> None:
    """scope2: AGENCY_WARN_50 (bypass=False) suppressed at 23:15 IST quiet hours."""
    customer_id = uuid4()
    agency_row = _mock_row(id=uuid4(), quota_paise=100000)
    spend_row = _mock_row(period_spend=60000)  # 60% → fires AGENCY_WARN_50 normally
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(agency_row),
        _fetchone_result(spend_row),
        _fetchall_result([]),
    )
    svc = _make_service(session)
    quiet_ist = datetime(2026, 8, 1, 23, 15, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=quiet_ist):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "AGENCY_WARN_50" not in names


@pytest.mark.asyncio
async def test_scope3_runway_emergency_bypasses_quiet_hours() -> None:
    """scope3: RUNWAY_EMERGENCY (bypass=True) fires even at quiet hours."""
    customer_id = uuid4()
    # 0.5 days remaining → fires all 5 rules; RUNWAY_P2/P1 have bypass=False → suppressed
    # RUNWAY_P0, RUNWAY_CRITICAL, RUNWAY_EMERGENCY have bypass=True → fire
    provider_row = _mock_row(
        id=uuid4(), provider_name="openai",
        balance_paise=500, daily_burn_rate_paise=1000,  # 0.5 days
    )
    session = _mock_session(
        _fetchall_result([]),
        _fetchone_result(None),
        _fetchall_result([provider_row]),
        # RUNWAY_P0 fires (bypass=True)
        _fetchone_result(_mock_row(cnt=0)),
        MagicMock(),
        # RUNWAY_CRITICAL fires (bypass=True)
        _fetchone_result(_mock_row(cnt=0)),
        MagicMock(),
        # RUNWAY_EMERGENCY fires (bypass=True)
        _fetchone_result(_mock_row(cnt=0)),
        MagicMock(),
    )
    svc = _make_service(session)
    quiet_ist = datetime(2026, 8, 1, 23, 15, tzinfo=timezone.utc)
    with patch("meter.service._now_ist", return_value=quiet_ist):
        alerts = await svc.check_thresholds(customer_id)

    names = [a.threshold_name for a in alerts]
    assert "RUNWAY_EMERGENCY" in names
    assert "RUNWAY_P2" not in names
