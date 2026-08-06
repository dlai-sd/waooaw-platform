# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from meter.service import (
    MeterService,
)
from reconciliation.service import (
    BILLING_HALTED_KEY,
    DailyAuditResult,
    FounderActionGenerator,
    ReconciliationService,
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
        bucket_reservation_id TEXT,
        marked_up_cost_inr_paise INTEGER NOT NULL DEFAULT 0,
        raw_cost_inr_paise INTEGER NOT NULL DEFAULT 0,
        recorded_at TEXT NOT NULL,
        billing_period_start TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS wallet_buckets (
        id TEXT NOT NULL PRIMARY KEY,
        customer_id TEXT NOT NULL,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        available_paise INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS bucket_reservations (
        id TEXT NOT NULL PRIMARY KEY,
        bucket_id TEXT NOT NULL,
        reserved_paise INTEGER NOT NULL,
        consumed INTEGER NOT NULL DEFAULT 0,
        consumed_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS topup_orders (
        id TEXT NOT NULL PRIMARY KEY,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        amount_paise INTEGER NOT NULL,
        applied_at TEXT
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
    """CREATE TABLE IF NOT EXISTS audit_evidence_log (
        id TEXT NOT NULL PRIMARY KEY,
        audit_type TEXT NOT NULL,
        audit_date TEXT NOT NULL,
        total_checked INTEGER NOT NULL,
        unlinked_count INTEGER NOT NULL,
        outcome TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
]


@pytest.fixture
async def in_memory_engine():
    """SQLite in-memory engine with StaticPool for test isolation."""
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
    """Async session factory for in-memory DB."""
    return async_sessionmaker(in_memory_engine, expire_on_commit=False)


@pytest.fixture
def meter_service(session_factory):
    """MeterService instance for tests."""
    return MeterService(session_factory, redis_pool=None)


@pytest.fixture
async def mock_redis():
    """Mock Redis client (not real Redis)."""
    mock = AsyncMock(spec=aioredis.Redis)
    mock.set = AsyncMock()
    mock.get = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
async def mock_founder_action_generator():
    """Mock FounderActionGenerator."""
    mock = AsyncMock(spec=FounderActionGenerator)
    mock.maybe_create = AsyncMock(return_value=False)
    return mock


@pytest.fixture
async def reconciliation_service(session_factory, mock_redis, mock_founder_action_generator):
    """ReconciliationService instance for tests."""
    return ReconciliationService(
        session_factory=session_factory,
        redis_client=mock_redis,
        founder_action_generator=mock_founder_action_generator,
    )


@pytest.fixture
def test_customer_id():
    """Standard test customer UUID."""
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def test_provider_account_id():
    """Standard test provider account UUID."""
    return UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def test_employment_contract_id():
    """Standard test employment contract UUID."""
    return UUID("33333333-3333-3333-3333-333333333333")


# ============================================================================
# Helper functions for test data insertion
# ============================================================================


async def _insert_bucket(
    sf: async_sessionmaker,
    bucket_id: UUID,
    customer_id: UUID,
    employment_contract_id: UUID,
    thread_type: str,
    balance_paise: int,
    is_active: bool = True,
) -> None:
    """Insert a wallet_bucket row into test DB."""
    async with sf() as session:
        await session.execute(
            text(
                """
                INSERT INTO wallet_buckets
                    (id, customer_id, employment_contract_id, thread_type, balance_paise, is_active)
                VALUES
                    (:id, :customer_id, :ec_id, :thread_type, :balance_paise, :is_active)
                """
            ).bindparams(
                id=str(bucket_id),
                customer_id=str(customer_id),
                ec_id=str(employment_contract_id),
                thread_type=thread_type,
                balance_paise=balance_paise,
                is_active=1 if is_active else 0,
            )
        )
        await session.commit()


async def _insert_topup_order(
    sf: async_sessionmaker,
    topup_id: UUID,
    employment_contract_id: UUID,
    thread_type: str,
    amount_paise: int,
    applied_at: datetime | None = None,
) -> None:
    """Insert a topup_order row into test DB."""
    async with sf() as session:
        await session.execute(
            text(
                """
                INSERT INTO topup_orders
                    (id, employment_contract_id, thread_type, amount_paise, applied_at)
                VALUES
                    (:id, :ec_id, :thread_type, :amount_paise, :applied_at)
                """
            ).bindparams(
                id=str(topup_id),
                ec_id=str(employment_contract_id),
                thread_type=thread_type,
                amount_paise=amount_paise,
                applied_at=applied_at.isoformat() if applied_at else None,
            )
        )
        await session.commit()


async def _insert_bucket_reservation(
    sf: async_sessionmaker,
    res_id: UUID,
    bucket_id: UUID,
    reserved_paise: int,
    consumed: bool = False,
    consumed_at: datetime | None = None,
) -> None:
    """Insert a bucket_reservation row into test DB."""
    async with sf() as session:
        await session.execute(
            text(
                """
                INSERT INTO bucket_reservations
                    (id, bucket_id, reserved_paise, consumed, consumed_at)
                VALUES
                    (:id, :bucket_id, :reserved_paise, :consumed, :consumed_at)
                """
            ).bindparams(
                id=str(res_id),
                bucket_id=str(bucket_id),
                reserved_paise=reserved_paise,
                consumed=1 if consumed else 0,
                consumed_at=consumed_at.isoformat() if consumed_at else None,
            )
        )
        await session.commit()


async def _insert_cost_ledger_entry(
    sf: async_sessionmaker,
    ledger_id: UUID,
    customer_id: UUID,
    thread_type: str,
    provider_account_id: UUID,
    bucket_reservation_id: UUID | None = None,
    marked_up_cost_inr_paise: int = 0,
    raw_cost_inr_paise: int = 0,
    recorded_at: datetime | None = None,
    billing_period_start: str = "2025-01-01",
) -> None:
    """Insert a platform_cost_ledger row into test DB."""
    async with sf() as session:
        await session.execute(
            text(
                """
                INSERT INTO platform_cost_ledger
                    (id, customer_id, thread_type, provider_account_id, bucket_reservation_id,
                     marked_up_cost_inr_paise, raw_cost_inr_paise, recorded_at, billing_period_start)
                VALUES
                    (:id, :customer_id, :thread_type, :provider_account_id, :bucket_reservation_id,
                     :marked_up_cost, :raw_cost, :recorded_at, :billing_period_start)
                """
            ).bindparams(
                id=str(ledger_id),
                customer_id=str(customer_id),
                thread_type=thread_type,
                provider_account_id=str(provider_account_id),
                bucket_reservation_id=str(bucket_reservation_id) if bucket_reservation_id else None,
                marked_up_cost=marked_up_cost_inr_paise,
                raw_cost=raw_cost_inr_paise,
                recorded_at=(recorded_at or datetime.now(timezone.utc)).isoformat(),
                billing_period_start=billing_period_start,
            )
        )
        await session.commit()


# ============================================================================
# Tests for run_daily_audit
# ============================================================================


@pytest.mark.asyncio
async def test_run_daily_audit_clean_pass(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    test_provider_account_id: UUID,
) -> None:
    """
    Happy path: consumed reservations have matching cost ledger entries.
    Expected: zero unlinked, evidence_id logged, PASS outcome.
    """
    bucket_id = uuid4()
    res_id = uuid4()
    ledger_id = uuid4()
    audit_date = date(2025, 1, 15)
    consumed_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    # Setup: create bucket, reservation, and cost ledger entry
    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=True,
        consumed_at=consumed_at,
    )
    await _insert_cost_ledger_entry(
        session_factory,
        ledger_id,
        test_customer_id,
        "INFERENCE",
        test_provider_account_id,
        bucket_reservation_id=res_id,
        raw_cost_inr_paise=500,
    )

    # Execute
    result = await reconciliation_service.run_daily_audit(audit_date)

    # Assert
    assert isinstance(result, DailyAuditResult)
    assert result.audit_date == audit_date
    assert result.total_consumed_reservations == 1
    assert result.unlinked_reservations == []
    assert result.evidence_id is not None


@pytest.mark.asyncio
async def test_run_daily_audit_detects_unlinked(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    Error path: consumed reservation has NO matching cost ledger entry.
    Expected: res_id flagged in unlinked_reservations, evidence outcome=FAIL_UNLINKED.
    """
    bucket_id = uuid4()
    res_id = uuid4()
    audit_date = date(2025, 1, 15)
    consumed_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    # Setup: create bucket and reservation, but NO cost ledger
    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=True,
        consumed_at=consumed_at,
    )

    # Execute
    result = await reconciliation_service.run_daily_audit(audit_date)

    # Assert
    assert result.total_consumed_reservations == 1
    assert len(result.unlinked_reservations) == 1
    assert result.unlinked_reservations[0] == res_id


@pytest.mark.asyncio
async def test_run_daily_audit_ignores_unconsumed(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    Edge case: unconsumed reservations are NOT audited.
    Expected: total_consumed_reservations=0 (only consumed=True counts).
    """
    bucket_id = uuid4()
    res_id = uuid4()
    audit_date = date(2025, 1, 15)

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=False,
    )

    result = await reconciliation_service.run_daily_audit(audit_date)

    assert result.total_consumed_reservations == 0
    assert result.unlinked_reservations == []


# ============================================================================
# Tests for run_self_audit
# ============================================================================


@pytest.mark.asyncio
async def test_run_self_audit_clean_pass(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    mock_redis: AsyncMock,
) -> None:
    """
    Happy path: balance matches expected (topups - consumed).
    Expected: billing_halted=False, no Redis halt set, no FA created.
    """
    bucket_id = uuid4()
    topup_id = uuid4()
    res_id = uuid4()

    # Setup: topup 10000 paise, consume 3000 paise, balance should be 7000
    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=7000,
    )
    topup_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    await _insert_topup_order(
        session_factory,
        topup_id,
        test_employment_contract_id,
        "INFERENCE",
        amount_paise=10000,
        applied_at=topup_at,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=3000,
        consumed=True,
    )

    result = await reconciliation_service.run_self_audit()

    assert result.billing_halted is False
    assert result.founder_action_created is False
    assert result.buckets_audited == 1
    assert result.discrepancy_paise == 0
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_run_self_audit_detects_discrepancy_halts_billing(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    mock_redis: AsyncMock,
    mock_founder_action_generator: AsyncMock,
) -> None:
    """
    Error path: balance does NOT match expected by > 1 paise.
    Setup: topup 10000, consumed 3000, EXPECTED 7000, ACTUAL 7002 (+2 paise corruption).
    Expected: billing_halted=True, Redis wbe:billing_halted set, FA created.
    """
    bucket_id = uuid4()
    topup_id = uuid4()
    res_id = uuid4()

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=7002,  # Corrupted: should be 7000
    )
    topup_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    await _insert_topup_order(
        session_factory,
        topup_id,
        test_employment_contract_id,
        "INFERENCE",
        amount_paise=10000,
        applied_at=topup_at,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=3000,
        consumed=True,
    )

    # Configure mocks
    mock_redis.set = AsyncMock()
    mock_founder_action_generator.maybe_create = AsyncMock(return_value=True)

    result = await reconciliation_service.run_self_audit()

    assert result.billing_halted is True
    assert result.founder_action_created is True
    assert result.discrepancy_paise == 2
    assert result.buckets_audited == 1
    mock_redis.set.assert_called_once_with(BILLING_HALTED_KEY, "1")
    mock_founder_action_generator.maybe_create.assert_called_once()


@pytest.mark.asyncio
async def test_run_self_audit_ignores_inactive_buckets(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    Edge case: inactive buckets are NOT audited.
    Expected: buckets_audited=0, no halt triggered.
    """
    bucket_id = uuid4()

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
        is_active=False,
    )

    result = await reconciliation_service.run_self_audit()

    assert result.buckets_audited == 0
    assert result.billing_halted is False


@pytest.mark.asyncio
async def test_run_self_audit_handles_zero_topups(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    Edge case: bucket with zero topups (expected=0 - consumed).
    If balance=0 and consumed=0, expected=0, discrepancy=0, pass.
    """
    bucket_id = uuid4()

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=0,
    )

    result = await reconciliation_service.run_self_audit()

    assert result.buckets_audited == 1
    assert result.billing_halted is False
    assert result.discrepancy_paise == 0


# ============================================================================
# Tests for generate_margin_report
# ============================================================================


@pytest.mark.asyncio
async def test_generate_margin_report_computes_margin_correctly(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    test_provider_account_id: UUID,
) -> None:
    """
    Happy path: margin_pct = (revenue - cost) / revenue * 100.
    revenue=1000, cost=300 => margin = (1000-300)/1000*100 = 70%.
    """
    bucket_id = uuid4()
    res_id = uuid4()
    ledger_id = uuid4()
    report_date = date(2025, 1, 15)
    consumed_at = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=True,
        consumed_at=consumed_at,
    )
    await _insert_cost_ledger_entry(
        session_factory,
        ledger_id,
        test_customer_id,
        "INFERENCE",
        test_provider_account_id,
        bucket_reservation_id=res_id,
        raw_cost_inr_paise=300,
    )

    rows = await reconciliation_service.generate_margin_report(report_date)

    assert len(rows) == 1
    row = rows[0]
    assert row.customer_id == test_customer_id
    assert row.thread_type == "INFERENCE"
    assert row.revenue_paise == 1000
    assert row.cost_paise == 300
    # margin_pct = (1000 - 300) / 1000 * 100 = 70.00
    assert row.margin_pct == 70


@pytest.mark.asyncio
async def test_generate_margin_report_handles_zero_cost(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    test_provider_account_id: UUID,
) -> None:
    """
    Edge case: zero cost => 100% margin.
    """
    bucket_id = uuid4()
    res_id = uuid4()
    ledger_id = uuid4()
    report_date = date(2025, 1, 15)
    consumed_at = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=True,
        consumed_at=consumed_at,
    )
    await _insert_cost_ledger_entry(
        session_factory,
        ledger_id,
        test_customer_id,
        "INFERENCE",
        test_provider_account_id,
        bucket_reservation_id=res_id,
        raw_cost_inr_paise=0,
    )

    rows = await reconciliation_service.generate_margin_report(report_date)

    assert len(rows) == 1
    assert rows[0].margin_pct == 100


@pytest.mark.asyncio
async def test_generate_margin_report_ignores_unconsumed_reservations(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    Edge case: unconsumed reservations are NOT included in report.
    """
    bucket_id = uuid4()
    res_id = uuid4()
    report_date = date(2025, 1, 15)

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=False,
    )

    rows = await reconciliation_service.generate_margin_report(report_date)

    assert len(rows) == 0


@pytest.mark.asyncio
async def test_generate_margin_report_groups_by_customer_and_thread_type(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    test_provider_account_id: UUID,
) -> None:
    """
    Aggregation: two reservations for same customer+thread should combine.
    """
    bucket_id = uuid4()
    res_id_1 = uuid4()
    res_id_2 = uuid4()
    ledger_id_1 = uuid4()
    ledger_id_2 = uuid4()
    report_date = date(2025, 1, 15)
    consumed_at = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    # Reservation 1: 1000 paise, cost 300
    await _insert_bucket_reservation(
        session_factory,
        res_id_1,
        bucket_id,
        reserved_paise=1000,
        consumed=True,
        consumed_at=consumed_at,
    )
    await _insert_cost_ledger_entry(
        session_factory,
        ledger_id_1,
        test_customer_id,
        "INFERENCE",
        test_provider_account_id,
        bucket_reservation_id=res_id_1,
        raw_cost_inr_paise=300,
    )
    # Reservation 2: 500 paise, cost 150
    await _insert_bucket_reservation(
        session_factory,
        res_id_2,
        bucket_id,
        reserved_paise=500,
        consumed=True,
        consumed_at=consumed_at,
    )
    await _insert_cost_ledger_entry(
        session_factory,
        ledger_id_2,
        test_customer_id,
        "INFERENCE",
        test_provider_account_id,
        bucket_reservation_id=res_id_2,
        raw_cost_inr_paise=150,
    )

    rows = await reconciliation_service.generate_margin_report(report_date)

    assert len(rows) == 1
    row = rows[0]
    assert row.revenue_paise == 1500  # 1000 + 500
    assert row.cost_paise == 450  # 300 + 150
    # margin = (1500 - 450) / 1500 * 100 = 70.00
    assert row.margin_pct == 70


# ============================================================================
# Tests for clear_halt
# ============================================================================


@pytest.mark.asyncio
async def test_clear_halt_deletes_redis_key(
    reconciliation_service: ReconciliationService,
    mock_redis: AsyncMock,
) -> None:
    """
    Happy path: clear_halt() deletes BILLING_HALTED_KEY from Redis.
    """
    mock_redis.delete = AsyncMock()

    await reconciliation_service.clear_halt()

    mock_redis.delete.assert_called_once_with(BILLING_HALTED_KEY)


@pytest.mark.asyncio
async def test_clear_halt_idempotent(
    reconciliation_service: ReconciliationService,
    mock_redis: AsyncMock,
) -> None:
    """
    Edge case: calling clear_halt() twice is safe (delete is idempotent).
    """
    mock_redis.delete = AsyncMock()

    await reconciliation_service.clear_halt()
    await reconciliation_service.clear_halt()

    assert mock_redis.delete.call_count == 2


# ============================================================================
# Constitutional Tests (C-023, C-059, C-063)
# ============================================================================


@pytest.mark.asyncio
async def test_run_daily_audit_emits_evidence_record(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    C-023: every audit emits an evidence record regardless of outcome.
    Verify audit_evidence_log row is created with correct outcome.
    """
    bucket_id = uuid4()
    res_id = uuid4()
    audit_date = date(2025, 1, 15)
    consumed_at = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )
    await _insert_bucket_reservation(
        session_factory,
        res_id,
        bucket_id,
        reserved_paise=1000,
        consumed=True,
        consumed_at=consumed_at,
    )

    result = await reconciliation_service.run_daily_audit(audit_date)

    # Verify evidence record exists
    async with session_factory() as session:
        evidence = await session.execute(
            text(
                """
                SELECT id, audit_type, outcome
                FROM audit_evidence_log
                WHERE id = :id
                """
            ).bindparams(id=str(result.evidence_id))
        )
        evidence_row = evidence.fetchone()
        assert evidence_row is not None
        assert evidence_row[1] == "DAILY_RESERVATION_AUDIT"
        assert evidence_row[2] == "FAIL_UNLINKED"  # unlinked because no cost ledger


@pytest.mark.asyncio
async def test_run_self_audit_emits_evidence_record(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
) -> None:
    """
    C-023: run_self_audit emits evidence record.
    """
    bucket_id = uuid4()

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=0,
    )

    result = await reconciliation_service.run_self_audit()

    async with session_factory() as session:
        evidence = await session.execute(
            text(
                """
                SELECT id, audit_type, outcome
                FROM audit_evidence_log
                WHERE id = :id
                """
            ).bindparams(id=str(result.evidence_id))
        )
        evidence_row = evidence.fetchone()
        assert evidence_row is not None
        assert evidence_row[1] == "SELF_AUDIT"
        assert evidence_row[2] == "PASS"


@pytest.mark.asyncio
async def test_run_self_audit_no_pii_in_logs(
    reconciliation_service: ReconciliationService,
    session_factory: async_sessionmaker,
    test_customer_id: UUID,
    test_employment_contract_id: UUID,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    C-063: no PII in log statements.
    Verify customer_id and employment_contract_id are logged as UUIDs,
    not as identifiable strings (e.g., no email, name, etc.).
    """
    bucket_id = uuid4()

    await _insert_bucket(
        session_factory,
        bucket_id,
        test_customer_id,
        test_employment_contract_id,
        "INFERENCE",
        balance_paise=5000,
    )

    with caplog.at_level("INFO"):
        await reconciliation_service.run_self_audit()

    # Assert that no PII-like patterns appear in logs
    for record in caplog.records:
        # UUIDs are OK; customer names, emails, etc. are not
        assert "@" not in record.message  # No email
        assert ".com" not in record.message  # No domain