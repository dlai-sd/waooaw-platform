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
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        agreed_price_paise INTEGER NOT NULL DEFAULT 0,
        plan_price_paise INTEGER NOT NULL DEFAULT 0,
        thread_type TEXT NOT NULL DEFAULT 'DMA',
        period_start TEXT,
        renewed_at TEXT
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
async def session_factory_with_billing(in_memory_engine):
    """Extended session factory including billing_profiles, customers, subscriptions."""
    extra = [
        """CREATE TABLE IF NOT EXISTS billing_profiles (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING'
        )""",
        """CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            mode TEXT NOT NULL DEFAULT 'FREE'
        )""",
        """CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            agent_type TEXT NOT NULL,
            bundle_tier TEXT NOT NULL,
            razorpay_order_id TEXT NOT NULL,
            razorpay_payment_id TEXT NOT NULL,
            activated_at TEXT NOT NULL
        )""",
    ]
    async with in_memory_engine.begin() as conn:
        for stmt in extra:
            await conn.execute(text(stmt))
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


async def _seed_reservation(session, *, bucket_id, reserved_paise=1000):
    """Insert a pre-existing reservation row. Returns (res_id, idempotency_key)."""
    res_id = str(uuid.uuid4())
    ikey = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO bucket_reservations"
            " (id, bucket_id, reserved_paise, idempotency_key, consumed, created_at)"
            " VALUES (:id, :bid, :amt, :ikey, 0, :now)"
        ).bindparams(
            id=res_id,
            bid=str(bucket_id),
            amt=reserved_paise,
            ikey=ikey,
            now=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    await session.commit()
    return res_id, ikey


async def _seed_billing_profile(session, customer_id, *, status="FOUNDER_AUTHORIZED"):
    bp_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO billing_profiles (id, customer_id, status)"
            " VALUES (:id, :cid, :status)"
        ).bindparams(id=bp_id, cid=str(customer_id), status=status)
    )
    await session.commit()


async def _seed_customer(session, customer_id):
    await session.execute(
        text("INSERT INTO customers (id, mode) VALUES (:id, 'FREE')").bindparams(
            id=str(customer_id)
        )
    )
    await session.commit()


async def _seed_contract_with_prices(
    session,
    *,
    customer_id,
    agreed_price_paise,
    plan_price_paise,
    thread_type="DMA",
):
    """Insert employment_contract with price columns. Returns contract_id."""
    contract_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO employment_contracts"
            " (id, customer_id, status, agreed_price_paise, plan_price_paise, thread_type)"
            " VALUES (:id, :cid, 'ACTIVE', :agreed, :plan, :tt)"
        ).bindparams(
            id=contract_id,
            cid=str(customer_id),
            agreed=agreed_price_paise,
            plan=plan_price_paise,
            tt=thread_type,
        )
    )
    await session.commit()
    return contract_id


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


# ---------------------------------------------------------------------------
# reserve()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reserve_success_returns_bucket_reservation(db_session, fake_redis):
    """reserve() debits bucket and returns BucketReservation with correct fields."""
    from wallet.models import BucketReservation

    customer_id = uuid.uuid4()
    _, _bucket_id = await _seed_bucket(db_session, customer_id=customer_id, balance_paise=10000)
    idem_key = uuid.uuid4()

    svc = WalletService(db=db_session, redis_client=fake_redis)
    result = await svc.reserve(
        customer_id=customer_id,
        thread_type="DMA",
        amount_paise=3000,
        idempotency_key=idem_key,
        redis_client=fake_redis,
    )

    assert isinstance(result, BucketReservation)
    assert result.reserved_paise == 3000
    assert result.idempotency_key == idem_key

    # Balance must be reduced
    balance = await svc.get_bucket_balance(customer_id=customer_id, thread_type="DMA")
    assert balance.balance_paise == 7000


@pytest.mark.asyncio
async def test_reserve_idempotency_raises_duplicate(db_session, fake_redis):
    """reserve() raises DuplicateReservationError when idempotency_key already used."""
    from wallet.models import DuplicateReservationError

    customer_id = uuid.uuid4()
    _, bucket_id = await _seed_bucket(db_session, customer_id=customer_id, balance_paise=10000)
    _, idem_key = await _seed_reservation(db_session, bucket_id=bucket_id, reserved_paise=1000)

    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(DuplicateReservationError):
        await svc.reserve(
            customer_id=customer_id,
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.UUID(idem_key),
            redis_client=fake_redis,
        )


@pytest.mark.asyncio
async def test_reserve_redis_error_fails_safe_503(db_session):
    """reserve() raises HTTP 503 (fail-safe) when Redis errors during halt check."""
    broken_redis = MagicMock()
    broken_redis.get = AsyncMock(side_effect=OSError("Redis down"))
    svc = WalletService(db=db_session, redis_client=broken_redis)
    with pytest.raises(HTTPException) as exc_info:
        await svc.reserve(
            customer_id=uuid.uuid4(),
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.uuid4(),
            redis_client=broken_redis,
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "BILLING_INTEGRITY_HALT"


@pytest.mark.asyncio
async def test_reserve_insufficient_balance_raises(db_session, fake_redis):
    """reserve() raises InsufficientBalanceError when balance < requested amount."""
    from wallet.models import InsufficientBalanceError

    customer_id = uuid.uuid4()
    await _seed_bucket(db_session, customer_id=customer_id, balance_paise=500)

    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(InsufficientBalanceError):
        await svc.reserve(
            customer_id=customer_id,
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.uuid4(),
            redis_client=fake_redis,
        )


# ---------------------------------------------------------------------------
# release()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_release_consumed_true_marks_reservation(db_session, fake_redis):
    """release(consumed=True) marks reservation consumed without refunding balance."""
    customer_id = uuid.uuid4()
    _, bucket_id = await _seed_bucket(db_session, customer_id=customer_id, balance_paise=5000)
    res_id, _ = await _seed_reservation(db_session, bucket_id=bucket_id, reserved_paise=2000)

    svc = WalletService(db=db_session, redis_client=fake_redis)
    await svc.release(reservation_id=uuid.UUID(res_id), consumed=True)

    # Balance should NOT be restored
    balance = await svc.get_bucket_balance(customer_id=customer_id, thread_type="DMA")
    assert balance.balance_paise == 5000  # unchanged

    # Reservation row should be marked consumed
    row = (await db_session.execute(
        text("SELECT consumed FROM bucket_reservations WHERE id = :id").bindparams(id=res_id)
    )).fetchone()
    assert row is not None
    assert row.consumed in (1, True)


@pytest.mark.asyncio
async def test_release_consumed_false_refunds_balance(db_session, fake_redis):
    """release(consumed=False) deletes reservation and restores bucket balance."""
    customer_id = uuid.uuid4()
    _, bucket_id = await _seed_bucket(db_session, customer_id=customer_id, balance_paise=5000)
    res_id, _ = await _seed_reservation(db_session, bucket_id=bucket_id, reserved_paise=2000)

    svc = WalletService(db=db_session, redis_client=fake_redis)
    await svc.release(reservation_id=uuid.UUID(res_id), consumed=False)

    # Balance should be restored (+2000)
    balance = await svc.get_bucket_balance(customer_id=customer_id, thread_type="DMA")
    assert balance.balance_paise == 7000

    # Reservation row should be deleted
    row = (await db_session.execute(
        text("SELECT id FROM bucket_reservations WHERE id = :id").bindparams(id=res_id)
    )).fetchone()
    assert row is None


@pytest.mark.asyncio
async def test_release_not_found_raises_value_error(db_session, fake_redis):
    """release() raises ValueError when reservation_id does not exist."""
    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(ValueError, match="Reservation not found"):
        await svc.release(reservation_id=uuid.uuid4(), consumed=False)


# ---------------------------------------------------------------------------
# activate_subscription()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_subscription_authorized_returns_result(
    session_factory_with_billing, fake_redis
):
    """activate_subscription() creates subscription and returns result when FOUNDER_AUTHORIZED."""
    from wallet.models import SubscriptionActivationResult

    async with session_factory_with_billing() as session:
        customer_id = uuid.uuid4()
        await _seed_billing_profile(session, customer_id)
        await _seed_customer(session, customer_id)

        svc = WalletService(db=session, redis_client=fake_redis)
        result = await svc.activate_subscription(
            customer_id=customer_id,
            agent_type="DMA",
            bundle_tier="STARTER",
            razorpay_order_id="order_abc123",
            razorpay_payment_id="pay_xyz789",
        )

    assert isinstance(result, SubscriptionActivationResult)
    assert result.agent_type == "DMA"
    assert result.bundle_tier == "STARTER"
    assert result.customer_id == customer_id


@pytest.mark.asyncio
async def test_activate_subscription_not_authorized_raises_403(
    session_factory_with_billing, fake_redis
):
    """activate_subscription() raises HTTP 403 when billing_profiles.status != FOUNDER_AUTHORIZED."""
    async with session_factory_with_billing() as session:
        customer_id = uuid.uuid4()
        await _seed_billing_profile(session, customer_id, status="PENDING")
        await _seed_customer(session, customer_id)

        svc = WalletService(db=session, redis_client=fake_redis)
        with pytest.raises(HTTPException) as exc_info:
            await svc.activate_subscription(
                customer_id=customer_id,
                agent_type="DMA",
                bundle_tier="STARTER",
                razorpay_order_id="order_abc",
                razorpay_payment_id="pay_abc",
            )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "BILLING_PROFILE_NOT_AUTHORIZED"


@pytest.mark.asyncio
async def test_activate_subscription_missing_profile_raises_403(
    session_factory_with_billing, fake_redis
):
    """activate_subscription() raises HTTP 403 when no billing_profiles row exists."""
    async with session_factory_with_billing() as session:
        svc = WalletService(db=session, redis_client=fake_redis)
        with pytest.raises(HTTPException) as exc_info:
            await svc.activate_subscription(
                customer_id=uuid.uuid4(),
                agent_type="DMA",
                bundle_tier="STARTER",
                razorpay_order_id="order_x",
                razorpay_payment_id="pay_x",
            )

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# renew()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_renew_success_updates_contract(db_session, fake_redis):
    """renew() updates period_start/renewed_at and returns RenewalResult."""
    from datetime import date
    from wallet.models import RenewalResult

    customer_id = uuid.uuid4()
    contract_id = await _seed_contract_with_prices(
        db_session,
        customer_id=customer_id,
        agreed_price_paise=6000,
        plan_price_paise=6000,  # equal — no price increase
    )

    svc = WalletService(db=db_session, redis_client=fake_redis)
    new_start = date(2026, 9, 1)
    result = await svc.renew(
        customer_id=customer_id,
        contract_id=uuid.UUID(contract_id),
        new_period_start=new_start,
    )

    assert isinstance(result, RenewalResult)
    assert result.new_period_start == new_start
    assert result.customer_id == customer_id


@pytest.mark.asyncio
async def test_renew_price_increase_raises_422(db_session, fake_redis):
    """renew() raises HTTP 422 when plan_price > agreed_price (C-090 guard)."""
    from datetime import date

    customer_id = uuid.uuid4()
    contract_id = await _seed_contract_with_prices(
        db_session,
        customer_id=customer_id,
        agreed_price_paise=5000,
        plan_price_paise=7000,  # plan > agreed → must be blocked
    )

    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(HTTPException) as exc_info:
        await svc.renew(
            customer_id=customer_id,
            contract_id=uuid.UUID(contract_id),
            new_period_start=date(2026, 9, 1),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "PRICE_INCREASE_WITHOUT_NOTICE"


@pytest.mark.asyncio
async def test_renew_contract_not_found_raises_value_error(db_session, fake_redis):
    """renew() raises ValueError when contract_id does not exist."""
    from datetime import date

    svc = WalletService(db=db_session, redis_client=fake_redis)
    with pytest.raises(ValueError, match="Contract not found"):
        await svc.renew(
            customer_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            new_period_start=date(2026, 9, 1),
        )
