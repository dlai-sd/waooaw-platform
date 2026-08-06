# Implements: work-contracts/WC-026-wbe-s2-wallet-engine.md WC026-05
# constitutional_basis: C-023, C-059, C-063, C-090, C-004
# Rewritten for current WalletService API (WC-026 + WC-030 cross-sprint changes)
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from wallet.service import WalletService

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_WALLET_SCHEMA = [
    """CREATE TABLE employment_contracts (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE'
    )""",
    """CREATE TABLE wallet_buckets (
        id TEXT PRIMARY KEY,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE bucket_reservations (
        id TEXT PRIMARY KEY,
        bucket_id TEXT NOT NULL,
        reserved_paise INTEGER NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        consumed INTEGER NOT NULL DEFAULT 0,
        consumed_at TEXT,
        created_at TEXT NOT NULL
    )""",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def in_memory_engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        for stmt in _WALLET_SCHEMA:
            await conn.execute(text(stmt))
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(in_memory_engine):
    return async_sessionmaker(in_memory_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[fakeredis.FakeAsyncRedis]:
    client = fakeredis.FakeAsyncRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
def wallet_service(db_session, fake_redis):
    return WalletService(db=db_session, redis_client=fake_redis)


async def _seed_bucket(session, *, customer_id, thread_type="DMA", balance_paise=10000, is_active=True):
    """Insert employment_contract + wallet_bucket. Returns (contract_id, bucket_id)."""
    contract_id = str(uuid.uuid4())
    bucket_id = str(uuid.uuid4())
    await session.execute(
        text("INSERT INTO employment_contracts (id, customer_id, status) VALUES (:id, :cid, 'ACTIVE')")
        .bindparams(id=contract_id, cid=str(customer_id))
    )
    await session.execute(
        text("""INSERT INTO wallet_buckets
               (id, employment_contract_id, thread_type, balance_paise, is_active, created_at)
               VALUES (:id, :ec, :tt, :bal, :active, :now)""")
        .bindparams(
            id=bucket_id, ec=contract_id, tt=thread_type,
            bal=balance_paise, active=1 if is_active else 0,
            now=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    await session.commit()
    return contract_id, bucket_id


# ---------------------------------------------------------------------------
# C-004: Billing halt enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserve_raises_503_when_billing_halted(wallet_service, fake_redis):
    """C-004: wbe:billing_halted set → reserve() raises HTTP 503 BILLING_INTEGRITY_HALT."""
    await fake_redis.set(b"wbe:billing_halted", b"1")

    with pytest.raises(HTTPException) as exc_info:
        await wallet_service.reserve(
            customer_id=uuid.uuid4(),
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.uuid4(),
            redis_client=fake_redis,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "BILLING_INTEGRITY_HALT"


@pytest.mark.asyncio
async def test_reserve_passes_halt_guard_when_not_halted(db_session, fake_redis):
    """C-004: halt key absent → reserve() passes halt guard (no 503 raised)."""
    svc = WalletService(db=db_session, redis_client=fake_redis)

    try:
        await svc.reserve(
            customer_id=uuid.uuid4(),
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.uuid4(),
            redis_client=fake_redis,
        )
    except HTTPException as exc:
        assert exc.status_code != 503, "Unexpected BILLING_INTEGRITY_HALT — key was not set"
    except Exception:
        pass  # DB-level error is fine — halt guard passed


@pytest.mark.asyncio
async def test_check_billing_halted_raises_503_when_key_set(wallet_service, fake_redis):
    """_check_billing_halted() raises HTTP 503 when Redis key is present."""
    await fake_redis.set(b"wbe:billing_halted", b"1")

    with pytest.raises(HTTPException) as exc_info:
        await wallet_service._check_billing_halted()

    assert exc_info.value.status_code == 503
    assert "BILLING_INTEGRITY_HALT" in exc_info.value.detail["code"]


@pytest.mark.asyncio
async def test_check_billing_halted_passes_when_key_absent(wallet_service):
    """_check_billing_halted() returns normally when Redis key is absent."""
    await wallet_service._check_billing_halted()  # must not raise


@pytest.mark.asyncio
async def test_check_billing_halted_fails_safe_on_redis_error(db_session):
    """_check_billing_halted() raises HTTP 503 (fail-safe) when Redis errors."""
    broken_redis = MagicMock()
    broken_redis.get = AsyncMock(side_effect=OSError("Redis down"))
    svc = WalletService(db=db_session, redis_client=broken_redis)

    with pytest.raises(HTTPException) as exc_info:
        await svc._check_billing_halted()

    assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# get_bucket_balance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_bucket_balance_returns_balance(db_session, fake_redis):
    """get_bucket_balance() returns BucketBalance with correct balance_paise."""
    from wallet.models import BucketBalance

    customer_id = uuid.uuid4()
    await _seed_bucket(db_session, customer_id=customer_id, balance_paise=8000, thread_type="INFERENCE")

    svc = WalletService(db=db_session, redis_client=fake_redis)
    balance = await svc.get_bucket_balance(customer_id=customer_id, thread_type="INFERENCE")

    assert isinstance(balance, BucketBalance)
    assert balance.balance_paise == 8000
    assert balance.thread_type == "INFERENCE"


@pytest.mark.asyncio
async def test_get_bucket_balance_raises_not_found(db_session, fake_redis):
    """get_bucket_balance() raises BucketNotFoundError for unknown customer/thread."""
    from wallet.models import BucketNotFoundError

    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(BucketNotFoundError):
        await svc.get_bucket_balance(customer_id=uuid.uuid4(), thread_type="NONEXISTENT")


@pytest.mark.asyncio
async def test_get_bucket_balance_ignores_inactive_bucket(db_session, fake_redis):
    """get_bucket_balance() raises BucketNotFoundError for inactive (is_active=0) buckets."""
    from wallet.models import BucketNotFoundError

    customer_id = uuid.uuid4()
    await _seed_bucket(db_session, customer_id=customer_id, balance_paise=5000, is_active=False)

    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(BucketNotFoundError):
        await svc.get_bucket_balance(customer_id=customer_id, thread_type="DMA")


@pytest.mark.asyncio
async def test_get_bucket_balance_multiple_buckets_same_customer(db_session, fake_redis):
    """get_bucket_balance() returns the correct bucket for a given thread_type."""
    customer_id = uuid.uuid4()
    await _seed_bucket(db_session, customer_id=customer_id, balance_paise=1000, thread_type="DMA")
    await _seed_bucket(db_session, customer_id=customer_id, balance_paise=2000, thread_type="INFERENCE")

    svc = WalletService(db=db_session, redis_client=fake_redis)

    dma = await svc.get_bucket_balance(customer_id=customer_id, thread_type="DMA")
    inf = await svc.get_bucket_balance(customer_id=customer_id, thread_type="INFERENCE")

    assert dma.balance_paise == 1000
    assert inf.balance_paise == 2000
