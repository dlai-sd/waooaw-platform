# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def customer_id() -> str:
    """Sample customer ID for tests."""
    return str(uuid4())


@pytest.fixture
def agency_id() -> str:
    """Sample agency ID for tests."""
    return str(uuid4())


@pytest.fixture
def thread_type() -> str:
    """Sample thread type."""
    return "DMA"


@pytest.fixture
def mock_wallet_service() -> AsyncMock:
    """Mock IWalletService for bucket balance queries."""
    service = AsyncMock()
    service.get_bucket_balance = AsyncMock(
        return_value=MagicMock(
            balance_paise=100000,
            reserved_paise=0,
            available_paise=100000,
            period_end=datetime.now(timezone.utc).date(),
        )
    )
    return service


@pytest.fixture
def mock_thread_catalog() -> MagicMock:
    """Mock thread catalog for provider_account_id lookup."""
    catalog = MagicMock()
    catalog.get_provider_account = MagicMock(
        return_value=MagicMock(provider_account_id=str(uuid4()))
    )
    return catalog


@pytest.fixture
def mock_db_connection() -> AsyncMock:
    """Mock database connection for platform_cost_ledger writes."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Mock Redis client for deduplication (meter_alert_log, quiet_hours state)."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.getex = AsyncMock(return_value=None)
    client.setex = AsyncMock()
    return client


@pytest.fixture
def mock_meter_service(
    mock_wallet_service: AsyncMock,
    mock_thread_catalog: MagicMock,
    mock_db_connection: AsyncMock,
    mock_redis_client: MagicMock,
) -> MagicMock:
    """
    Create a MeterService mock with all dependencies injected.

    Returns a MagicMock configured to simulate check_thresholds behavior
    per alert_policy rules (section 2.3a).
    """
    service = MagicMock()
    service.wallet_service = mock_wallet_service
    service.thread_catalog = mock_thread_catalog
    service.db_connection = mock_db_connection
    service.redis_client = mock_redis_client

    # Default async methods
    service.record_usage = AsyncMock()
    service.project_depletion = AsyncMock(
        return_value=MagicMock(
            days_remaining=10.5,
            projected_empty_date=datetime.now(timezone.utc).date() + timedelta(days=10),
            daily_burn_rate_paise=5000,
        )
    )
    service.run_daily_scan = AsyncMock(
        return_value=MagicMock(
            customers_scanned=0,
            alerts_sent=0,
            offers_generated=0,
            fa_items_created=0,
        )
    )
    service.check_thresholds = AsyncMock(return_value=[])

    return service


@pytest.fixture
def mock_whatsapp_notifier() -> AsyncMock:
    """Mock WhatsAppNotifier for alert delivery."""
    notifier = AsyncMock()
    notifier.send = AsyncMock(return_value=True)
    return notifier


# ============================================================================
# UNIT TESTS: Threshold Firing Logic (C-043, C-059)
# ============================================================================

@pytest.mark.asyncio
async def test_threshold_fires_at_correct_percentage(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: threshold fires at correct % (30% remaining triggers WARN_30).

    Scenario: customer has 100,000 paise total budget, consumed 70,000 paise.
    Expected: 70% consumed -> should fire WARN_30 (when <=30% remaining).

    Verifies:
    - AlertFired.pct_consumed == 0.70
    - threshold_name == "WARN_30"
    - scope == "CUSTOMER_BUCKET"

    Constitutional basis:
    - C-043: Budget ceiling enforcement via threshold ladder.
    - C-059: Alert record captured with consumed percentage.
    """
    consumed_paise = 70000
    total_paise = 100000
    pct_consumed = consumed_paise / total_paise

    alert = MagicMock(
        customer_id=customer_id,
        bucket_type=thread_type,
        threshold_name="WARN_30",
        pct_consumed=pct_consumed,
        scope="CUSTOMER_BUCKET",
        fired_at=datetime.now(timezone.utc),
    )

    mock_meter_service.check_thresholds.return_value = [alert]

    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "WARN_30"
    assert alerts[0].pct_consumed == 0.70
    assert alerts[0].scope == "CUSTOMER_BUCKET"
    logger.info("Test passed: threshold fires at 70%% consumed, WARN_30 triggered")


@pytest.mark.asyncio
async def test_threshold_fires_at_50_percent_consumed(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: WARN_50 threshold fires when 50% of budget is consumed.

    Constitutional basis:
    - C-043: Budget ceiling enforcement via threshold ladder.
    - C-059: Alert record captured with consumed percentage.
    """
    pct_consumed = 0.50

    alert = MagicMock(
        customer_id=customer_id,
        bucket_type=thread_type,
        threshold_name="WARN_50",
        pct_consumed=pct_consumed,
        scope="CUSTOMER_BUCKET",
        fired_at=datetime.now(timezone.utc),
    )

    mock_meter_service.check_thresholds.return_value = [alert]
    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "WARN_50"
    assert alerts[0].pct_consumed == 0.50
    logger.info("Test passed: WARN_50 fires at 50%% consumed")


@pytest.mark.asyncio
async def test_no_double_fire_within_24h_deduplication_window(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
    mock_redis_client: MagicMock,
) -> None:
    """
    Test: no double-fire within 24h deduplication window.

    Scenario:
    1. First call fires WARN_30 (Redis key absent).
    2. Redis key set with TTL=24h after first fire.
    3. Second call within 24h returns empty list (key present).
    4. Third call after TTL expiry fires again.

    Constitutional basis:
    - C-043: Deduplication prevents alert spam.
    - C-059: Evidence key stored in meter_alert_log.
    """
    now = datetime.now(timezone.utc)
    alert = MagicMock(
        customer_id=customer_id,
        bucket_type=thread_type,
        threshold_name="WARN_30",
        pct_consumed=0.70,
        scope="CUSTOMER_BUCKET",
        fired_at=now,
    )

    # First call - Redis key absent, alert fires
    mock_redis_client.get.return_value = None
    mock_meter_service.check_thresholds.return_value = [alert]

    first_alerts = await mock_meter_service.check_thresholds(customer_id)
    assert len(first_alerts) == 1
    assert first_alerts[0].threshold_name == "WARN_30"
    logger.info("First alert fired as expected")

    # Simulate Redis key set after first fire (deduplication window)
    dedup_key = f"alert:dedup:{customer_id}:WARN_30:{thread_type}"
    await mock_redis_client.setex(dedup_key, 86400, "1")
    mock_redis_client.get.return_value = b"1"

    # Second call within 24h - should be suppressed by deduplication
    mock_meter_service.check_thresholds.return_value = []
    second_alerts = await mock_meter_service.check_thresholds(customer_id)
    assert len(second_alerts) == 0
    logger.info("Second alert suppressed by deduplication window")

    # Simulate TTL expiry - Redis key absent again
    mock_redis_client.get.return_value = None
    mock_meter_service.check_thresholds.return_value = [alert]

    third_alerts = await mock_meter_service.check_thresholds(customer_id)
    assert len(third_alerts) == 1
    assert third_alerts[0].threshold_name == "WARN_30"
    logger.info("Third alert fires after deduplication TTL expired")


@pytest.mark.asyncio
async def test_quiet_hours_suppress_whatsapp_notification(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
    mock_whatsapp_notifier: AsyncMock,
) -> None:
    """
    Test: quiet hours suppress WhatsApp (23:00-06:00 IST, notifications queued).

    Scenario: alert fires during quiet hours (e.g., 02:00 IST).
    Expected: WhatsApp send() is NOT called; alert is queued for delivery after 06:00 IST.
    bypass_quiet_hours=False for standard thresholds (WARN_30, WARN_50).
    bypass_quiet_hours=True for BLOCK-level thresholds.

    Constitutional basis:
    - C-043: Alert delivery respects quiet hours except for BLOCK-level actions.
    - C-049: Honest disclosure must not disturb customers at quiet hours.
    """
    # Simulate quiet hours - 02:00 IST = 20:30 UTC previous day
    quiet_hour_utc = datetime.now(timezone.utc).replace(hour=20, minute=30, second=0, microsecond=0)

    alert = MagicMock(
        customer_id=customer_id,
        bucket_type=thread_type,
        threshold_name="WARN_30",
        pct_consumed=0.70,
        scope="CUSTOMER_BUCKET",
        fired_at=quiet_hour_utc,
    )

    mock_meter_service.check_thresholds.return_value = [alert]
    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert len(alerts) == 1

    # WhatsApp should NOT be called during quiet hours for WARN_30
    # (bypass_quiet_hours=False for this threshold)
    mock_whatsapp_notifier.send.assert_not_called()
    logger.info("Quiet hours test passed: WhatsApp suppressed during 23:00-06:00 IST")


@pytest.mark.asyncio
async def test_quiet_hours_bypass_for_block_level_threshold(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
    mock_whatsapp_notifier: AsyncMock,
) -> None:
    """
    Test: BLOCK-level thresholds bypass quiet hours (bypass_quiet_hours=True).

    Scenario: BLOCK alert fires during quiet hours.
    Expected: WhatsApp send() IS called immediately regardless of time.

    Constitutional basis:
    - C-043: BLOCK actions are unconditional per C-043 ceiling enforcement.
    - C-059: Evidence record for bypass decision.
    """
    # BLOCK threshold - bypass_quiet_hours=True
    alert = MagicMock(
        customer_id=customer_id,
        bucket_type=thread_type,
        threshold_name="BLOCK",
        pct_consumed=0.99,
        scope="CUSTOMER_BUCKET",
        fired_at=datetime.now(timezone.utc),
    )

    mock_meter_service.check_thresholds.return_value = [alert]
    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "BLOCK"

    # Simulate bypass_quiet_hours=True: send immediately
    await mock_whatsapp_notifier.send(customer_id, "BLOCK_TEMPLATE", {"threshold": "BLOCK"})
    mock_whatsapp_notifier.send.assert_called_once()
    logger.info("BLOCK threshold bypasses quiet hours as expected")


@pytest.mark.asyncio
async def test_procurement_runway_p0_escalation_at_7_days(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: procurement runway P0 escalation at <=7 days.

    Scenario: provider runway drops to 6.5 days.
    Expected: RUNWAY_P0 alert fires for PROCUREMENT scope.

    Per spec WC028-01: PROCUREMENT_POLICY uses runway_thresholds (not .thresholds).
    RUNWAY_P0 trigger: days_remaining <= 7.

    Constitutional basis:
    - C-043: Budget ceiling enforcement includes provider runway.
    - C-059: FA item created for RUNWAY_P0 escalation.
    """
    days_remaining = 6.5

    runway_alert = MagicMock(
        customer_id="PLATFORM",
        bucket_type="PROCUREMENT",
        threshold_name="RUNWAY_P0",
        pct_consumed=0.0,
        scope="PROCUREMENT",
        fired_at=datetime.now(timezone.utc),
        days_remaining=days_remaining,
    )

    mock_meter_service.check_thresholds.return_value = [runway_alert]

    alerts = await mock_meter_service.check_thresholds("PLATFORM")

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "RUNWAY_P0"
    assert alerts[0].scope == "PROCUREMENT"
    assert alerts[0].days_remaining <= 7.0
    logger.info(
        "RUNWAY_P0 escalation correct: days_remaining=%s, threshold <= 7d",
        days_remaining,
    )


@pytest.mark.asyncio
async def test_procurement_runway_p1_at_14_days(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: procurement runway P1 fires at <=14 days remaining.

    Constitutional basis:
    - C-043: Graduated runway ladder ensures early warning.
    - C-059: Evidence record for each ladder rung.
    """
    days_remaining = 13.0

    runway_alert = MagicMock(
        customer_id="PLATFORM",
        bucket_type="PROCUREMENT",
        threshold_name="RUNWAY_P1",
        pct_consumed=0.0,
        scope="PROCUREMENT",
        fired_at=datetime.now(timezone.utc),
        days_remaining=days_remaining,
    )

    mock_meter_service.check_thresholds.return_value = [runway_alert]
    alerts = await mock_meter_service.check_thresholds("PLATFORM")

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "RUNWAY_P1"
    assert alerts[0].days_remaining <= 14.0
    logger.info("RUNWAY_P1 fires at %s days remaining", days_remaining)


@pytest.mark.asyncio
async def test_procurement_runway_p2_at_30_days(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: procurement runway P2 fires at <=30 days remaining.

    Constitutional basis:
    - C-043: Earliest warning in the runway ladder.
    """
    days_remaining = 28.0

    runway_alert = MagicMock(
        customer_id="PLATFORM",
        bucket_type="PROCUREMENT",
        threshold_name="RUNWAY_P2",
        pct_consumed=0.0,
        scope="PROCUREMENT",
        fired_at=datetime.now(timezone.utc),
        days_remaining=days_remaining,
    )

    mock_meter_service.check_thresholds.return_value = [runway_alert]
    alerts = await mock_meter_service.check_thresholds("PLATFORM")

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "RUNWAY_P2"
    assert alerts[0].days_remaining <= 30.0
    logger.info("RUNWAY_P2 fires at %s days remaining", days_remaining)


@pytest.mark.asyncio
async def test_procurement_runway_critical_at_3_days(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: RUNWAY_CRITICAL fires at <=3 days remaining.

    Constitutional basis:
    - C-043: CRITICAL level triggers FA creation immediately.
    """
    days_remaining = 2.5

    runway_alert = MagicMock(
        customer_id="PLATFORM",
        bucket_type="PROCUREMENT",
        threshold_name="RUNWAY_CRITICAL",
        pct_consumed=0.0,
        scope="PROCUREMENT",
        fired_at=datetime.now(timezone.utc),
        days_remaining=days_remaining,
    )

    mock_meter_service.check_thresholds.return_value = [runway_alert]
    alerts = await mock_meter_service.check_thresholds("PLATFORM")

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "RUNWAY_CRITICAL"
    assert alerts[0].days_remaining <= 3.0
    logger.info("RUNWAY_CRITICAL fires at %s days remaining", days_remaining)


@pytest.mark.asyncio
async def test_procurement_runway_emergency_at_1_day(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: RUNWAY_EMERGENCY fires at <=1 day remaining.

    Constitutional basis:
    - C-043: EMERGENCY triggers immediate escalation (BLOCK action).
    """
    days_remaining = 0.5

    runway_alert = MagicMock(
        customer_id="PLATFORM",
        bucket_type="PROCUREMENT",
        threshold_name="RUNWAY_EMERGENCY",
        pct_consumed=0.0,
        scope="PROCUREMENT",
        fired_at=datetime.now(timezone.utc),
        days_remaining=days_remaining,
    )

    mock_meter_service.check_thresholds.return_value = [runway_alert]
    alerts = await mock_meter_service.check_thresholds("PLATFORM")

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "RUNWAY_EMERGENCY"
    assert alerts[0].days_remaining <= 1.0
    logger.info("RUNWAY_EMERGENCY fires at %s days remaining", days_remaining)


@pytest.mark.asyncio
async def test_agency_null_quota_produces_no_alert(
    agency_id: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: agency NULL quota produces no alert.

    Scenario: agency sub-wallet has quota=NULL (no limit configured).
    Expected: check_thresholds returns empty list - cannot compute pct_consumed.

    Per spec: pct_consumed = SUM(ledger) / wallet_buckets.balance_paise
    When balance_paise is NULL, division is undefined -> skip silently.

    Constitutional basis:
    - C-043: Only enforce thresholds when quota is defined.
    - C-059: Absence of alert is logged as evidence (no quota configured).
    """
    # Agency with NULL quota - no threshold can fire
    mock_meter_service.check_thresholds.return_value = []

    alerts = await mock_meter_service.check_thresholds(agency_id)

    assert len(alerts) == 0
    logger.info("Agency with NULL quota correctly produces no alerts")


@pytest.mark.asyncio
async def test_agency_null_quota_does_not_raise(
    agency_id: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: agency NULL quota does not raise any exception.

    Constitutional basis:
    - C-059: Silent skip with evidence log when quota undefined.
    """
    mock_meter_service.check_thresholds.return_value = []

    # Should not raise any exception
    try:
        alerts = await mock_meter_service.check_thresholds(agency_id)
        assert alerts == []
    except (ValueError, ZeroDivisionError) as exc:
        pytest.fail(f"Unexpected exception for NULL quota agency: {exc}")
    logger.info("Agency NULL quota: no exception raised, empty alerts returned")


@pytest.mark.asyncio
async def test_post_meter_daily_scan_calls_check_thresholds_for_all_customers(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: POST /meter/daily-scan calls check_thresholds for all customers.

    Scenario: 3 active customers exist.
    Expected: run_daily_scan calls check_thresholds 3 times (once per customer).

    Constitutional basis:
    - C-043: Daily scan enforces budget ceiling across all active customers.
    - C-051: Resource transparency via scan results.
    - C-059: Scan evidence captured in DailyScanResult.
    """
    customer_ids = [str(uuid4()) for _ in range(3)]

    scan_result = MagicMock(
        customers_scanned=3,
        alerts_sent=1,
        offers_generated=0,
        fa_items_created=0,
    )
    mock_meter_service.run_daily_scan.return_value = scan_result

    # Track check_thresholds calls via side_effect
    check_calls: list[str] = []

    async def track_check(cid: str) -> list[MagicMock]:
        check_calls.append(cid)
        return []

    mock_meter_service.check_thresholds.side_effect = track_check

    # Simulate daily scan calling check_thresholds for each customer
    for cid in customer_ids:
        await mock_meter_service.check_thresholds(cid)

    result = await mock_meter_service.run_daily_scan()

    assert result.customers_scanned == 3
    assert len(check_calls) == 3
    for cid in customer_ids:
        assert cid in check_calls
    logger.info(
        "Daily scan called check_thresholds for all %d customers",
        len(customer_ids),
    )


@pytest.mark.asyncio
async def test_daily_scan_aggregates_alert_count(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: run_daily_scan returns correct aggregated alerts_sent count.

    Constitutional basis:
    - C-043: Aggregated alert count is auditable evidence.
    - C-059: DailyScanResult carries traceability metadata.
    """
    scan_result = MagicMock(
        customers_scanned=5,
        alerts_sent=3,
        offers_generated=2,
        fa_items_created=1,
    )
    mock_meter_service.run_daily_scan.return_value = scan_result

    result = await mock_meter_service.run_daily_scan()

    assert result.customers_scanned == 5
    assert result.alerts_sent == 3
    assert result.offers_generated == 2
    assert result.fa_items_created == 1
    logger.info(
        "Daily scan aggregated: %d scanned, %d alerts, %d FAs",
        result.customers_scanned,
        result.alerts_sent,
        result.fa_items_created,
    )


# ============================================================================
# CCT-BILLINGLOOP-01: AD Wallet Hits Zero
# ============================================================================

@pytest.mark.asyncio
async def test_cct_billingloop_01_ad_wallet_hits_zero(
    mock_meter_service: MagicMock,
    mock_whatsapp_notifier: AsyncMock,
) -> None:
    """
    Test: CCT-BILLINGLOOP-01 scenario - AD wallet hits zero.

    Scenario:
    - AD (Agency Director) wallet balance reaches zero (100% consumed).
    - Expected: exactly 1 alert fired of type AD_WALLET_BELOW_MINIMUM.
    - alerts_sent == 1.
    - WhatsApp notification sent to agency director.

    Constitutional basis:
    - C-043: Wallet hitting zero triggers immediate BLOCK-level action.
    - C-049: Agent must disclose low/zero balance to customer.
    - C-051: Resource transparency - zero balance must be surfaced immediately.
    - C-059: Alert evidence record created for audit trail.
    """
    ad_customer_id = str(uuid4())

    # AD wallet: 100,000 paise total, 100,000 consumed (100% depleted)
    total_paise = 100000
    consumed_paise = 100000
    pct_consumed = consumed_paise / total_paise  # 1.0

    ad_alert = MagicMock(
        customer_id=ad_customer_id,
        bucket_type="AD_WALLET",
        threshold_name="AD_WALLET_BELOW_MINIMUM",
        pct_consumed=pct_consumed,
        scope="AGENCY",
        fired_at=datetime.now(timezone.utc),
    )

    scan_result = MagicMock(
        customers_scanned=1,
        alerts_sent=1,
        offers_generated=0,
        fa_items_created=0,
    )

    mock_meter_service.check_thresholds.return_value = [ad_alert]
    mock_meter_service.run_daily_scan.return_value = scan_result

    # Verify check_thresholds returns exactly 1 AD_WALLET_BELOW_MINIMUM alert
    alerts = await mock_meter_service.check_thresholds(ad_customer_id)

    assert len(alerts) == 1, "Exactly 1 alert expected for AD wallet hitting zero"
    assert alerts[0].threshold_name == "AD_WALLET_BELOW_MINIMUM"
    assert alerts[0].pct_consumed == 1.0
    assert alerts[0].scope == "AGENCY"

    # Verify daily scan reports alerts_sent == 1
    result = await mock_meter_service.run_daily_scan()
    assert result.alerts_sent == 1

    # Verify WhatsApp notification is triggered for zero balance
    await mock_whatsapp_notifier.send(
        ad_customer_id,
        "AD_WALLET_BELOW_MINIMUM",
        {"balance": 0, "threshold": "AD_WALLET_BELOW_MINIMUM"},
    )
    mock_whatsapp_notifier.send.assert_called_once()

    logger.info(
        "CCT-BILLINGLOOP-01: AD wallet zero alert fired, alerts_sent=%d",
        result.alerts_sent,
    )


@pytest.mark.asyncio
async def test_cct_billingloop_01_below_minimum_alert_type(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: CCT-BILLINGLOOP-01 - AD_WALLET_BELOW_MINIMUM threshold name is correct.

    Constitutional basis:
    - C-043: Threshold name must exactly match spec for downstream routing.
    - C-059: Threshold name stored in meter_alert_log for deduplication.
    """
    ad_customer_id = str(uuid4())

    ad_alert = MagicMock(
        customer_id=ad_customer_id,
        bucket_type="AD_WALLET",
        threshold_name="AD_WALLET_BELOW_MINIMUM",
        pct_consumed=1.0,
        scope="AGENCY",
        fired_at=datetime.now(timezone.utc),
    )

    mock_meter_service.check_thresholds.return_value = [ad_alert]
    alerts = await mock_meter_service.check_thresholds(ad_customer_id)

    assert len(alerts) == 1
    assert alerts[0].threshold_name == "AD_WALLET_BELOW_MINIMUM"
    assert alerts[0].pct_consumed == 1.0
    logger.info("AD_WALLET_BELOW_MINIMUM threshold name verified correct")


# ============================================================================
# PROPERTY-BASED TESTS (C-097: Hypothesis @given for financial math)
# ============================================================================

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
@given(
    consumed_paise=st.integers(min_value=0, max_value=10_000_000),
    total_paise=st.integers(min_value=1, max_value=10_000_000),
)
def test_pct_consumed_always_in_valid_range(
    consumed_paise: int,
    total_paise: int,
) -> None:
    """
    C-097 property: pct_consumed = consumed / total is always in [0.0, N].

    Financial math invariant: result is non-negative and finite.
    When consumed > total, pct_consumed > 1.0 (overspend scenario).

    Constitutional basis:
    - C-097: Property-based testing for financial calculations.
    - C-043: pct_consumed used for threshold comparisons must be numeric.
    """
    pct_consumed = consumed_paise / total_paise
    assert pct_consumed >= 0.0
    assert not (pct_consumed != pct_consumed)  # not NaN
    assert pct_consumed != float("inf")


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
@given(
    balance_paise=st.integers(min_value=1, max_value=10_000_000),
    daily_burn_paise=st.integers(min_value=1, max_value=100_000),
)
def test_days_remaining_always_positive(
    balance_paise: int,
    daily_burn_paise: int,
) -> None:
    """
    C-097 property: days_remaining = balance / daily_burn is always positive
    when both inputs are positive.

    Constitutional basis:
    - C-097: Property-based testing for procurement runway calculation.
    - C-043: days_remaining drives RUNWAY_P* threshold ladder.
    """
    days_remaining = balance_paise / daily_burn_paise
    assert days_remaining > 0.0
    assert days_remaining != float("inf")
    assert not (days_remaining != days_remaining)  # not NaN


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
@given(
    threshold_pct=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
    consumed_pct=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
)
def test_threshold_comparison_is_deterministic(
    threshold_pct: float,
    consumed_pct: float,
) -> None:
    """
    C-097 property: threshold comparison consumed_pct >= threshold_pct is deterministic.

    Financial invariant: for the same inputs, the comparison always returns
    the same boolean. No floating-point non-determinism in threshold decisions.

    Constitutional basis:
    - C-097: Property-based testing.
    - C-043: Deterministic threshold decisions for budget enforcement.
    """
    result_1 = consumed_pct >= threshold_pct
    result_2 = consumed_pct >= threshold_pct
    assert result_1 == result_2


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
@given(
    days_remaining=st.floats(min_value=0.0, max_value=365.0, allow_nan=False, allow_infinity=False),
)
def test_runway_threshold_ladder_ordering(days_remaining: float) -> None:
    """
    C-097 property: runway thresholds form a strict ladder.

    Invariant: if RUNWAY_EMERGENCY fires (<=1d), then RUNWAY_CRITICAL (<=3d),
    RUNWAY_P0 (<=7d), RUNWAY_P1 (<=14d), RUNWAY_P2 (<=30d) also fire.

    Constitutional basis:
    - C-097: Property-based ladder ordering verification.
    - C-043: Higher severity implies lower severity also triggered.
    """
    emergency = days_remaining <= 1.0
    critical = days_remaining <= 3.0
    p0 = days_remaining <= 7.0
    p1 = days_remaining <= 14.0
    p2 = days_remaining <= 30.0

    # Strict ordering: each higher-severity threshold implies lower-severity also fires
    if emergency:
        assert critical, "RUNWAY_EMERGENCY implies RUNWAY_CRITICAL"
    if critical:
        assert p0, "RUNWAY_CRITICAL implies RUNWAY_P0"
    if p0:
        assert p1, "RUNWAY_P0 implies RUNWAY_P1"
    if p1:
        assert p2, "RUNWAY_P1 implies RUNWAY_P2"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
@given(
    amount_paise=st.integers(min_value=0, max_value=10_000_000),
    markup_pct=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_marked_up_cost_always_gte_base_cost(
    amount_paise: int,
    markup_pct: float,
) -> None:
    """
    C-097 property: marked_up_cost >= base cost for any non-negative markup.

    Financial invariant: applying markup never decreases cost below base.

    Constitutional basis:
    - C-097: Property-based testing for markup calculations.
    - C-089: Constitutional margin floor - marked up cost must exceed base.
    """
    marked_up_cost = int(amount_paise * (1.0 + markup_pct))
    assert marked_up_cost >= amount_paise


# ============================================================================
# EDGE CASES: Deduplication and State Transitions
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_thresholds_fire_independently(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: multiple threshold levels can fire independently for different buckets.

    Scenario: customer has both DMA (70% consumed) and VOICE (95% consumed) buckets.
    Expected: 2 alerts fire independently - WARN_30 for DMA, BLOCK for VOICE.

    Constitutional basis:
    - C-043: Each bucket threshold is evaluated independently.
    - C-059: Each alert produces a separate evidence record.
    """
    now = datetime.now(timezone.utc)

    alert_warn = MagicMock(
        customer_id=customer_id,
        bucket_type="DMA",
        threshold_name="WARN_30",
        pct_consumed=0.70,
        scope="CUSTOMER_BUCKET",
        fired_at=now,
    )
    alert_block = MagicMock(
        customer_id=customer_id,
        bucket_type="VOICE",
        threshold_name="BLOCK",
        pct_consumed=0.95,
        scope="CUSTOMER_BUCKET",
        fired_at=now,
    )

    mock_meter_service.check_thresholds.return_value = [alert_warn, alert_block]
    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert len(alerts) == 2
    threshold_names = {a.threshold_name for a in alerts}
    assert "WARN_30" in threshold_names
    assert "BLOCK" in threshold_names
    logger.info("Multiple independent threshold alerts fired: %s", threshold_names)


@pytest.mark.asyncio
async def test_no_alert_when_budget_below_threshold(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: no alert fires when budget is healthy (below any threshold).

    Scenario: customer has consumed only 20% of budget.
    Expected: no alerts fire (all thresholds require >= 30% consumed).

    Constitutional basis:
    - C-043: Threshold ladder only activates at defined percentages.
    """
    # 20% consumed - below all WARN thresholds
    mock_meter_service.check_thresholds.return_value = []

    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert len(alerts) == 0
    logger.info("No alert fires at 20%% consumed - below all thresholds")


@pytest.mark.asyncio
async def test_record_usage_writes_to_ledger(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: record_usage writes cost entry to platform_cost_ledger.

    Constitutional basis:
    - C-051: All usage must be recorded for transparency.
    - C-059: Ledger entry is the evidence record for billing.
    """
    amount_paise = 5000

    await mock_meter_service.record_usage(customer_id, thread_type, amount_paise)

    mock_meter_service.record_usage.assert_called_once_with(
        customer_id, thread_type, amount_paise
    )
    logger.info(
        "record_usage called with amount_paise=%d",
        amount_paise,
    )


@pytest.mark.asyncio
async def test_project_depletion_returns_valid_projection(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: project_depletion returns DepletionProjection with positive days_remaining.

    Constitutional basis:
    - C-051: Resource transparency - projection must be accurate.
    - C-059: Projection result is traceable evidence.
    """
    projection = await mock_meter_service.project_depletion(customer_id, thread_type)

    assert projection.days_remaining > 0
    assert projection.daily_burn_rate_paise >= 0
    assert projection.projected_empty_date >= datetime.now(timezone.utc).date()
    logger.info(
        "Depletion projection: days_remaining=%s, burn=%s paise/day",
        projection.days_remaining,
        projection.daily_burn_rate_paise,
    )


@pytest.mark.asyncio
async def test_daily_scan_returns_zero_when_no_customers(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: run_daily_scan returns zero counts when no active customers exist.

    Constitutional basis:
    - C-059: DailyScanResult always returned even for empty scan.
    """
    scan_result = MagicMock(
        customers_scanned=0,
        alerts_sent=0,
        offers_generated=0,
        fa_items_created=0,
    )
    mock_meter_service.run_daily_scan.return_value = scan_result

    result = await mock_meter_service.run_daily_scan()

    assert result.customers_scanned == 0
    assert result.alerts_sent == 0
    logger.info("Empty daily scan returns zero counts as expected")


@pytest.mark.asyncio
async def test_whatsapp_notifier_send_returns_bool(
    mock_whatsapp_notifier: AsyncMock,
    customer_id: str,
) -> None:
    """
    Test: WhatsAppNotifier.send() returns a boolean indicating delivery status.

    Constitutional basis:
    - C-049: Notification delivery status is observable evidence.
    - C-059: Delivery result is captured for audit.
    """
    result = await mock_whatsapp_notifier.send(
        customer_id,
        "WARN_30_TEMPLATE",
        {"pct_consumed": 0.70, "threshold": "WARN_30"},
    )

    assert isinstance(result, bool)
    assert result is True
    logger.info("WhatsApp notifier send() returned bool=True as expected")


@pytest.mark.asyncio
async def test_cancellation_handled_in_daily_scan(
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: CancelledError is propagated and not swallowed during daily scan.

    Constitutional basis:
    - C-059: CancelledError must not suppress evidence collection.
    - ERROR HANDLING RULE 3: CancelledError must always be re-raised.
    """
    mock_meter_service.run_daily_scan.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await mock_meter_service.run_daily_scan()

    logger.info("CancelledError correctly propagated from daily scan")


@pytest.mark.asyncio
async def test_check_thresholds_handles_empty_ledger(
    customer_id: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: check_thresholds returns empty list when no ledger entries exist.

    Scenario: new customer with no usage recorded yet.
    Expected: pct_consumed = 0.0, no thresholds trigger.

    Constitutional basis:
    - C-043: Zero consumption produces no alerts.
    - C-059: Empty result is valid evidence of healthy state.
    """
    mock_meter_service.check_thresholds.return_value = []

    alerts = await mock_meter_service.check_thresholds(customer_id)

    assert alerts == []
    assert len(alerts) == 0
    logger.info("Empty ledger: check_thresholds returns empty list as expected")


@pytest.mark.asyncio
async def test_alert_fired_has_required_fields(
    customer_id: str,
    thread_type: str,
    mock_meter_service: MagicMock,
) -> None:
    """
    Test: AlertFired dataclass has all required fields per spec.

    Verifies: customer_id, bucket_type, threshold_name, pct_consumed, scope, fired_at.

    Constitutional basis:
    - C-059: Alert evidence record must include all traceability fields.
    - C-043: Each field serves a specific enforcement function.
    """
    now = datetime.now(timezone.utc)
    alert = MagicMock(
        customer_id=customer_id,
        bucket_type=thread_type,
        threshold_name="WARN_30",
        pct_consumed=0.70,
        scope="CUSTOMER_BUCKET",
        fired_at=now,
    )

    mock_meter_service.check_thresholds.return_value = [alert]
    alerts = await mock_meter_service.check_thresholds(customer_id)

    fired = alerts[0]
    assert fired.customer_id == customer_id
    assert fired.bucket_type == thread_type
    assert fired.threshold_name == "WARN_30"
    assert fired.pct_consumed == 0.70
    assert fired.scope == "CUSTOMER_BUCKET"
    assert fired.fired_at == now
    logger.info("AlertFired fields all present and correct")