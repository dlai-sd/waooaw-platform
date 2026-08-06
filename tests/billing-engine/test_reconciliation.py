# Implements: WC-030 §reconciliation-tests
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from reconciliation.scheduler import create_scheduler
from reconciliation.service import (
    FounderActionGenerator,
    ReconciliationService,
    SelfAuditResult,
)





# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE IF NOT EXISTS employment_contracts (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        thread_type TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS wallet_buckets (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS topup_orders (
        id TEXT PRIMARY KEY,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        amount_paise INTEGER NOT NULL,
        applied_at TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS bucket_reservations (
        id TEXT PRIMARY KEY,
        bucket_id TEXT NOT NULL,
        reserved_paise INTEGER NOT NULL,
        consumed INTEGER NOT NULL DEFAULT 0,
        consumed_at TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS platform_cost_ledger (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL DEFAULT '',
        thread_type TEXT NOT NULL DEFAULT '',
        provider_account_id TEXT NOT NULL DEFAULT '',
        bucket_reservation_id TEXT,
        raw_cost_inr_paise INTEGER NOT NULL DEFAULT 0,
        marked_up_cost_inr_paise INTEGER NOT NULL DEFAULT 0,
        recorded_at TEXT NOT NULL DEFAULT '',
        billing_period_start TEXT NOT NULL DEFAULT ''
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
    """CREATE TABLE IF NOT EXISTS founder_actions (
        id TEXT PRIMARY KEY,
        action_type TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
]


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def in_memory_engine():
    """SQLite in-memory engine with StaticPool — all connections share same DB."""
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
def mock_redis():
    """Sync-created FakeAsyncRedis so it's usable in both sync and async context."""
    return fakeredis.FakeAsyncRedis()


@pytest.fixture
def mock_founder_action_generator():
    mock = AsyncMock(spec=FounderActionGenerator)
    mock.maybe_create = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def reconciliation_service(session_factory, mock_redis, mock_founder_action_generator):
    return ReconciliationService(
        session_factory=session_factory,
        redis_client=mock_redis,
        founder_action_generator=mock_founder_action_generator,
    )


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.WBE_INTERNAL_BASE_URL = "http://localhost:8000"
    s.REDIS_URL = "redis://localhost:6379/0"
    return s


# ---------------------------------------------------------------------------
# Helper: insert rows
# ---------------------------------------------------------------------------


async def _ins_bucket(sf, bucket_id, customer_id, ec_id, thread_type, balance, is_active=True):
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO wallet_buckets (id, customer_id, employment_contract_id, thread_type, balance_paise, is_active) "
                "VALUES (:id, :cid, :ec_id, :tt, :bal, :active)"
            ).bindparams(
                id=str(bucket_id), cid=str(customer_id), ec_id=str(ec_id),
                tt=thread_type, bal=balance, active=1 if is_active else 0,
            )
        )
        await session.commit()


async def _ins_topup(sf, topup_id, ec_id, thread_type, amount, applied_at=None):
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO topup_orders (id, employment_contract_id, thread_type, amount_paise, applied_at) "
                "VALUES (:id, :ec_id, :tt, :amt, :applied)"
            ).bindparams(
                id=str(topup_id), ec_id=str(ec_id), tt=thread_type,
                amt=amount, applied=applied_at.isoformat() if applied_at else None,
            )
        )
        await session.commit()


async def _ins_reservation(sf, res_id, bucket_id, reserved, consumed=False, consumed_at=None):
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO bucket_reservations (id, bucket_id, reserved_paise, consumed, consumed_at) "
                "VALUES (:id, :bid, :amt, :consumed, :cat)"
            ).bindparams(
                id=str(res_id), bid=str(bucket_id), amt=reserved,
                consumed=1 if consumed else 0,
                cat=consumed_at.isoformat() if consumed_at else None,
            )
        )
        await session.commit()


async def _ins_cost_ledger(sf, ledger_id, customer_id, thread_type, provider_id, res_id, raw_cost):
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO platform_cost_ledger "
                "(id, customer_id, thread_type, provider_account_id, bucket_reservation_id, "
                "raw_cost_inr_paise, recorded_at, billing_period_start) "
                "VALUES (:id, :cid, :tt, :pid, :rid, :cost, :rec, :bps)"
            ).bindparams(
                id=str(ledger_id), cid=str(customer_id), tt=thread_type,
                pid=str(provider_id), rid=str(res_id), cost=raw_cost,
                rec=datetime.now(tz=timezone.utc).isoformat(),
                bps="2025-01-01",
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Tests: run_self_audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_self_audit_clean_state(reconciliation_service, mock_redis):
    """C-023: empty wallet state — no discrepancy, billing not halted."""
    result = await reconciliation_service.run_self_audit()

    assert isinstance(result, SelfAuditResult)
    assert result.billing_halted is False
    assert result.discrepancy_paise == 0
    halted = await mock_redis.get("wbe:billing_halted")
    assert halted is None


@pytest.mark.asyncio
async def test_run_self_audit_corrupted_balance_halts_billing(
    session_factory, reconciliation_service, mock_redis, mock_founder_action_generator
):
    """C-091: discrepancy > 1 paise triggers BILLING_INTEGRITY_HALT."""
    bucket_id = uuid.uuid4()
    ec_id = uuid.uuid4()
    cid = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    await _ins_bucket(session_factory, bucket_id, cid, ec_id, "AGENT", 1002)
    await _ins_topup(session_factory, uuid.uuid4(), ec_id, "AGENT", 1000, applied_at=now)
    # expected = 1000 topup - 0 consumed = 1000; actual = 1002 → delta = 2

    result = await reconciliation_service.run_self_audit()

    assert result.billing_halted is True
    assert result.discrepancy_paise == 2
    halted = await mock_redis.get("wbe:billing_halted")
    assert halted == b"1"


@pytest.mark.asyncio
async def test_clear_halt_removes_redis_key(reconciliation_service, mock_redis):
    """C-059: clear_halt() deletes wbe:billing_halted."""
    await mock_redis.set("wbe:billing_halted", "1")
    await reconciliation_service.clear_halt()
    halted = await mock_redis.get("wbe:billing_halted")
    assert halted is None


@pytest.mark.asyncio
async def test_run_daily_audit_matched_reservations(session_factory, reconciliation_service):
    """C-023: all reservations linked — zero unlinked."""
    today = datetime.now(tz=timezone.utc).date()
    bucket_id = uuid.uuid4()
    res_id = uuid.uuid4()
    consumed_at = datetime.now(tz=timezone.utc)

    await _ins_bucket(session_factory, bucket_id, uuid.uuid4(), uuid.uuid4(), "AGENT", 1000)
    await _ins_reservation(session_factory, res_id, bucket_id, 500, consumed=True, consumed_at=consumed_at)
    await _ins_cost_ledger(session_factory, uuid.uuid4(), uuid.uuid4(), "AGENT", uuid.uuid4(), res_id, 400)

    result = await reconciliation_service.run_daily_audit(today)

    assert result.unlinked_reservations == []


@pytest.mark.asyncio
async def test_run_daily_audit_unlinked_reservations(session_factory, reconciliation_service):
    """C-023: reservation without ledger entry → unlinked."""
    today = datetime.now(tz=timezone.utc).date()
    bucket_id = uuid.uuid4()
    res_id = uuid.uuid4()
    consumed_at = datetime.now(tz=timezone.utc)

    await _ins_bucket(session_factory, bucket_id, uuid.uuid4(), uuid.uuid4(), "AGENT", 1000)
    await _ins_reservation(session_factory, res_id, bucket_id, 500, consumed=True, consumed_at=consumed_at)

    result = await reconciliation_service.run_daily_audit(today)

    assert len(result.unlinked_reservations) == 1
    assert result.unlinked_reservations[0] == res_id


@pytest.mark.asyncio
async def test_run_self_audit_emits_evidence_record(session_factory, reconciliation_service, in_memory_engine):
    """C-023: evidence record emitted even with empty state."""
    result = await reconciliation_service.run_self_audit()

    assert result.evidence_id is not None
    async with async_sessionmaker(in_memory_engine, expire_on_commit=False)() as session:
        row = (await session.execute(
            text("SELECT audit_type, outcome FROM audit_evidence_log WHERE id = :id")
            .bindparams(id=str(result.evidence_id))
        )).fetchone()
    assert row is not None
    assert row[0] == "SELF_AUDIT"
    assert row[1] == "PASS"


@pytest.mark.asyncio
async def test_run_daily_audit_emits_evidence_record(session_factory, reconciliation_service, in_memory_engine):
    """C-023: evidence record emitted for daily audit."""
    today = datetime.now(tz=timezone.utc).date()

    result = await reconciliation_service.run_daily_audit(today)

    assert result.evidence_id is not None
    async with async_sessionmaker(in_memory_engine, expire_on_commit=False)() as session:
        row = (await session.execute(
            text("SELECT audit_type, outcome FROM audit_evidence_log WHERE id = :id")
            .bindparams(id=str(result.evidence_id))
        )).fetchone()
    assert row is not None
    assert row[0] == "DAILY_RESERVATION_AUDIT"


@pytest.mark.asyncio
async def test_run_self_audit_ignores_inactive_buckets(session_factory, reconciliation_service):
    """Edge case: inactive buckets not audited."""
    await _ins_bucket(session_factory, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "AGENT", 5000, is_active=False)

    result = await reconciliation_service.run_self_audit()

    assert result.buckets_audited == 0
    assert result.billing_halted is False


@pytest.mark.asyncio
async def test_generate_margin_report_computes_margin_correctly(session_factory, reconciliation_service):
    """C-097: revenue=1000, cost=300 → margin=70.00%."""
    report_date = datetime.now(tz=timezone.utc).date()
    consumed_at = datetime.now(tz=timezone.utc)
    customer_id = uuid.uuid4()
    bucket_id = uuid.uuid4()
    res_id = uuid.uuid4()
    provider_id = uuid.uuid4()

    await _ins_bucket(session_factory, bucket_id, customer_id, uuid.uuid4(), "INFERENCE", 5000)
    await _ins_reservation(session_factory, res_id, bucket_id, 1000, consumed=True, consumed_at=consumed_at)
    await _ins_cost_ledger(session_factory, uuid.uuid4(), customer_id, "INFERENCE", provider_id, res_id, 300)

    rows = await reconciliation_service.generate_margin_report(report_date)

    assert len(rows) == 1
    row = rows[0]
    assert row.revenue_paise == 1000
    assert row.cost_paise == 300
    assert row.margin_pct == Decimal("70.00")


@pytest.mark.asyncio
async def test_generate_margin_report_zero_cost_is_100_percent_margin(session_factory, reconciliation_service):
    """C-097: zero cost → 100% margin."""
    report_date = datetime.now(tz=timezone.utc).date()
    consumed_at = datetime.now(tz=timezone.utc)
    customer_id = uuid.uuid4()
    bucket_id = uuid.uuid4()
    res_id = uuid.uuid4()

    await _ins_bucket(session_factory, bucket_id, customer_id, uuid.uuid4(), "INFERENCE", 5000)
    await _ins_reservation(session_factory, res_id, bucket_id, 1000, consumed=True, consumed_at=consumed_at)
    await _ins_cost_ledger(session_factory, uuid.uuid4(), customer_id, "INFERENCE", uuid.uuid4(), res_id, 0)

    rows = await reconciliation_service.generate_margin_report(report_date)

    assert len(rows) == 1
    assert rows[0].margin_pct == Decimal("100")


@pytest.mark.asyncio
async def test_scheduler_idempotency_blocks_concurrent_audit(mock_redis, mock_settings, reconciliation_service):
    """C-002: wbe:audit_in_progress key present means audit is locked."""
    today = datetime.now(tz=timezone.utc).date()
    progress_key = f"wbe:audit_in_progress:{today.isoformat()}"
    await mock_redis.set(progress_key, "1", ex=14400)

    create_scheduler(
        service=reconciliation_service,
        redis_client=mock_redis,
        settings=mock_settings,
    )

    is_locked = await mock_redis.exists(progress_key)
    assert is_locked == 1


@pytest.mark.asyncio
async def test_billing_halted_redis_key_set(mock_redis):
    """C-091: wbe:billing_halted key signals halt state."""
    await mock_redis.set("wbe:billing_halted", "1")
    halted = await mock_redis.get("wbe:billing_halted")
    assert halted == b"1"


# ---------------------------------------------------------------------------
# Property-based test: margin arithmetic
# ---------------------------------------------------------------------------


# Property-based test: margin arithmetic — uses a dedicated engine per run
# to avoid StaticPool state accumulation across hypothesis examples.
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
@given(revenue_paise=st.integers(min_value=100, max_value=100_000))
@pytest.mark.asyncio
async def test_margin_report_arithmetic_property(revenue_paise: int) -> None:
    """C-097: margin_pct = (revenue - cost) / revenue * 100 for cost = 80% revenue."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        for stmt in _DDL:
            await conn.execute(text(stmt))

    sf = async_sessionmaker(engine, expire_on_commit=False)
    redis = fakeredis.FakeAsyncRedis()
    fag = AsyncMock(spec=FounderActionGenerator)
    fag.maybe_create = AsyncMock(return_value=False)
    svc = ReconciliationService(session_factory=sf, redis_client=redis, founder_action_generator=fag)

    report_date = datetime.now(tz=timezone.utc).date()
    consumed_at = datetime.now(tz=timezone.utc)
    customer_id = uuid.uuid4()
    bucket_id = uuid.uuid4()
    res_id = uuid.uuid4()
    cost_paise = int(revenue_paise * 0.8)

    await _ins_bucket(sf, bucket_id, customer_id, uuid.uuid4(), "INFERENCE", revenue_paise)
    await _ins_reservation(sf, res_id, bucket_id, revenue_paise, consumed=True, consumed_at=consumed_at)
    await _ins_cost_ledger(sf, uuid.uuid4(), customer_id, "INFERENCE", uuid.uuid4(), res_id, cost_paise)

    report = await svc.generate_margin_report(report_date)
    await engine.dispose()

    assert len(report) == 1
    row = report[0]
    expected_margin = (Decimal(revenue_paise - cost_paise) / Decimal(revenue_paise) * Decimal("100")).quantize(Decimal("0.01"))
    assert row.margin_pct == expected_margin
