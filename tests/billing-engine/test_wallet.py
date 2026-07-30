# Implements: work-contracts/WC-026-wbe-s2-wallet-engine.md WC026-05
# constitutional_basis: C-023, C-059, C-063, C-090
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from collections.abc import AsyncGenerator
from unittest import mock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cache import WalletCacheLayer
from models import BucketReservation, CustomerWallet, WalletBucket
from router import router
from service import WalletService

logger = logging.getLogger(__name__)


@pytest.fixture
def sqlite_engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_engine("sqlite:///:memory:")
    CustomerWallet.__table__.create(engine, checkfirst=True)
    WalletBucket.__table__.create(engine, checkfirst=True)
    BucketReservation.__table__.create(engine, checkfirst=True)
    return engine


@pytest.fixture
def session_factory(sqlite_engine):
    """Create session factory from in-memory engine."""
    return sessionmaker(bind=sqlite_engine)


@pytest.fixture
async def fake_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Create FakeRedis instance for tests."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    await redis.close()


@pytest.fixture
def wallet_service(session_factory, fake_redis):
    """Create WalletService with mocked dependencies."""
    service = WalletService(
        session_factory=session_factory,
        redis=fake_redis,
        logger=logger,
    )
    return service


@pytest.fixture
def wallet_cache(fake_redis):
    """Create WalletCacheLayer with FakeRedis."""
    cache = WalletCacheLayer(redis=fake_redis, ttl_seconds=300, logger=logger)
    return cache


@pytest.fixture
def app(wallet_service, wallet_cache):
    """Create test FastAPI app with wallet router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(
        router,
        prefix="/wallet",
        tags=["wallet"],
        dependencies=[],
    )

    # Inject dependencies into router via app.state
    test_app.state.wallet_service = wallet_service
    test_app.state.wallet_cache = wallet_cache

    return test_app


@pytest.fixture
def test_client(app):
    """Create TestClient from FastAPI app."""
    return TestClient(app)


def populate_test_wallet_sync(session_factory, wallet_id: str):
    """Synchronously populate test wallet with buckets (helper for sync tests)."""
    session = session_factory()
    try:
        wallet = CustomerWallet(
            wallet_id=wallet_id,
            tenant_id="tenant-001",
            billing_profile="standard",
            created_at="2026-01-01T00:00:00Z",
        )
        session.add(wallet)
        session.commit()

        for thread_type in ["gpt-4", "gpt-3.5"]:
            bucket = WalletBucket(
                wallet_id=wallet_id,
                thread_type=thread_type,
                quantity_available=1000,
                quantity_reserved=0,
                quantity_used=0,
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
            session.add(bucket)
        session.commit()
    finally:
        session.close()


class TestWalletCacheLayer:
    """Test WalletCacheLayer (cache hit/miss, invalidation, TTL, concurrency)."""

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, wallet_cache):
        """Test that cache miss returns None."""
        result = await wallet_cache.get_balance_cached(
            wallet_id="wallet-001", thread_type="gpt-4"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self, wallet_cache):
        """Test that cache hit returns previously set value."""
        wallet_id = "wallet-001"
        thread_type = "gpt-4"
        cached_value = 500

        key = f"wallet:{wallet_id}:bucket:{thread_type}"
        await wallet_cache.redis.set(key, str(cached_value), ex=300)

        result = await wallet_cache.get_balance_cached(
            wallet_id=wallet_id, thread_type=thread_type
        )
        assert result == cached_value

    @pytest.mark.asyncio
    async def test_cache_invalidate_wallet(self, wallet_cache):
        """Test that invalidate_wallet clears all bucket keys for a wallet."""
        wallet_id = "wallet-001"

        for thread_type in ["gpt-4", "gpt-3.5"]:
            key = f"wallet:{wallet_id}:bucket:{thread_type}"
            await wallet_cache.redis.set(key, "100", ex=300)

        assert (
            await wallet_cache.redis.get(f"wallet:{wallet_id}:bucket:gpt-4")
        ) is not None
        assert (
            await wallet_cache.redis.get(f"wallet:{wallet_id}:bucket:gpt-3.5")
        ) is not None

        await wallet_cache.invalidate_wallet(wallet_id=wallet_id)

        assert (
            await wallet_cache.redis.get(f"wallet:{wallet_id}:bucket:gpt-4")
        ) is None
        assert (
            await wallet_cache.redis.get(f"wallet:{wallet_id}:bucket:gpt-3.5")
        ) is None

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, wallet_cache):
        """Test that cached values expire after TTL."""
        wallet_id = "wallet-001"
        thread_type = "gpt-4"
        key = f"wallet:{wallet_id}:bucket:{thread_type}"

        await wallet_cache.redis.set(key, "100", ex=1)
        result = await wallet_cache.get_balance_cached(
            wallet_id=wallet_id, thread_type=thread_type
        )
        assert result == 100

        await asyncio.sleep(1.1)
        result = await wallet_cache.get_balance_cached(
            wallet_id=wallet_id, thread_type=thread_type
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, wallet_cache):
        """Test concurrent cache access does not corrupt state."""
        wallet_id = "wallet-001"
        thread_type = "gpt-4"
        key = f"wallet:{wallet_id}:bucket:{thread_type}"

        async def set_and_get(value: int):
            await wallet_cache.redis.set(key, str(value), ex=300)
            return await wallet_cache.get_balance_cached(
                wallet_id=wallet_id, thread_type=thread_type
            )

        results = await asyncio.gather(
            set_and_get(100),
            set_and_get(200),
            set_and_get(300),
        )

        assert all(r is not None for r in results)
        final_value = await wallet_cache.get_balance_cached(
            wallet_id=wallet_id, thread_type=thread_type
        )
        assert final_value is not None


class TestWalletServiceIdempotency:
    """Test WalletService idempotent reserve/release (C-059 traceability)."""

    @pytest.mark.asyncio
    async def test_reserve_idempotent_same_key(self, wallet_service, session_factory):
        """Test reserve with same idempotency_key returns same reservation_id."""
        wallet_id = "wallet-001"
        idempotency_key = "idem-key-001"

        populate_test_wallet_sync(session_factory, wallet_id)

        result_1 = await wallet_service.reserve(
            wallet_id=wallet_id,
            thread_type="gpt-4",
            quantity=100,
            idempotency_key=idempotency_key,
        )

        result_2 = await wallet_service.reserve(
            wallet_id=wallet_id,
            thread_type="gpt-4",
            quantity=100,
            idempotency_key=idempotency_key,
        )

        assert result_1["reservation_id"] == result_2["reservation_id"]
        assert result_1["quantity_reserved"] == result_2["quantity_reserved"]

    @pytest.mark.asyncio
    async def test_reserve_sufficient_funds(self, wallet_service, session_factory):
        """Test reserve succeeds when sufficient funds available."""
        wallet_id = "wallet-001"

        populate_test_wallet_sync(session_factory, wallet_id)

        result = await wallet_service.reserve(
            wallet_id=wallet_id,
            thread_type="gpt-4",
            quantity=100,
            idempotency_key="idem-001",
        )

        assert result["status"] == "reserved"
        assert result["quantity_reserved"] == 100
        assert result["reservation_id"] is not None

    @pytest.mark.asyncio
    async def test_reserve_insufficient_funds(self, wallet_service, session_factory):
        """Test reserve fails when insufficient funds."""
        wallet_id = "wallet-001"

        populate_test_wallet_sync(session_factory, wallet_id)

        result = await wallet_service.reserve(
            wallet_id=wallet_id,
            thread_type="gpt-4",
            quantity=2000,
            idempotency_key="idem-002",
        )

        assert result["status"] == "insufficient_funds"
        assert result["reservation_id"] is None

    @pytest.mark.asyncio
    async def test_release_restores_bucket_quantity(
        self, wallet_service, session_factory
    ):
        """Test release restores bucket quantity."""
        wallet_id = "wallet-001"

        populate_test_wallet_sync(session_factory, wallet_id)

        reserve_result = await wallet_service.reserve(
            wallet_id=wallet_id,
            thread_type="gpt-4",
            quantity=100,
            idempotency_key="idem-003",
        )

        reservation_id = reserve_result["reservation_id"]

        release_result = await wallet_service.release(
            reservation_id=reservation_id, reason="test_release"
        )

        assert release_result["status"] == "released"

        session = session_factory()
        try:
            bucket = (
                session.query(WalletBucket)
                .filter_by(wallet_id=wallet_id, thread_type="gpt-4")
                .first()
            )
            assert bucket.quantity_reserved == 0
        finally:
            session.close()


class TestWalletHttpEndpoints:
    """Test wallet HTTP endpoints (GET /buckets, POST /reserve, POST /release)."""

    def test_get_buckets_200(self, test_client, session_factory):
        """Test GET /wallet/buckets/{wallet_id} returns 200 with bucket list."""
        wallet_id = "wallet-001"
        populate_test_wallet_sync(session_factory, wallet_id)

        response = test_client.get(f"/wallet/buckets/{wallet_id}")

        assert response.status_code == 200
        data = response.json()
        assert "buckets" in data
        assert len(data["buckets"]) == 2

    def test_post_reserve_200(self, test_client, session_factory):
        """Test POST /wallet/reserve returns 200 on success."""
        wallet_id = "wallet-001"
        populate_test_wallet_sync(session_factory, wallet_id)

        payload = {
            "wallet_id": wallet_id,
            "thread_type": "gpt-4",
            "quantity": 100,
            "idempotency_key": "idem-http-001",
        }

        response = test_client.post("/wallet/reserve", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reserved"
        assert data["reservation_id"] is not None

    def test_post_reserve_422_insufficient_funds(
        self, test_client, session_factory
    ):
        """Test POST /wallet/reserve returns 422 when insufficient funds."""
        wallet_id = "wallet-001"
        populate_test_wallet_sync(session_factory, wallet_id)

        payload = {
            "wallet_id": wallet_id,
            "thread_type": "gpt-4",
            "quantity": 5000,
            "idempotency_key": "idem-http-002",
        }

        response = test_client.post("/wallet/reserve", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "insufficient_funds"

    def test_post_release_200(self, test_client, session_factory):
        """Test POST /wallet/release returns 200 on success."""
        wallet_id = "wallet-001"
        populate_test_wallet_sync(session_factory, wallet_id)

        reserve_payload = {
            "wallet_id": wallet_id,
            "thread_type": "gpt-4",
            "quantity": 100,
            "idempotency_key": "idem-http-003",
        }

        reserve_response = test_client.post("/wallet/reserve", json=reserve_payload)
        reservation_id = reserve_response.json()["reservation_id"]

        release_payload = {"reservation_id": reservation_id, "reason": "test"}

        response = test_client.post("/wallet/release", json=release_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "released"


class TestC090GrandfatherInvariant:
    """Test C-090 grandfather pricing invariant (legacy_price within grandfather_until)."""

    @pytest.mark.asyncio
    async def test_grandfather_pricing_active_within_deadline(
        self, wallet_service, session_factory
    ):
        """Test that legacy_price applies when grandfather_until is in future."""
        wallet_id = "wallet-001"
        grandfather_until = date.today() + timedelta(days=30)

        session = session_factory()
        try:
            wallet = CustomerWallet(
                wallet_id=wallet_id,
                tenant_id="tenant-001",
                billing_profile="standard",
                grandfather_until=grandfather_until,
                legacy_price=0.01,
                standard_price=0.02,
                created_at="2026-01-01T00:00:00Z",
            )
            session.add(wallet)
            session.commit()
        finally:
            session.close()

        with mock.patch("service.date") as mock_date:
            mock_date.today.return_value = date.today()

            effective_price = await wallet_service._get_effective_price(
                wallet_id=wallet_id
            )
            assert effective_price == 0.01

    @pytest.mark.asyncio
    async def test_grandfather_pricing_expired_after_deadline(
        self, wallet_service, session_factory
    ):
        """Test that standard_price applies when grandfather_until has passed."""
        wallet_id = "wallet-001"
        grandfather_until = date.today() - timedelta(days=1)

        session = session_factory()
        try:
            wallet = CustomerWallet(
                wallet_id=wallet_id,
                tenant_id="tenant-001",
                billing_profile="standard",
                grandfather_until=grandfather_until,
                legacy_price=0.01,
                standard_price=0.02,
                created_at="2026-01-01T00:00:00Z",
            )
            session.add(wallet)
            session.commit()
        finally:
            session.close()

        with mock.patch("service.date") as mock_date:
            mock_date.today.return_value = date.today()

            effective_price = await wallet_service._get_effective_price(
                wallet_id=wallet_id
            )
            assert effective_price == 0.02

    @pytest.mark.asyncio
    async def test_renew_subscription_updates_grandfather_deadline(
        self, wallet_service, session_factory
    ):
        """Test renew_subscription extends grandfather_until by renewal period."""
        wallet_id = "wallet-001"
        current_deadline = date.today() + timedelta(days=30)

        session = session_factory()
        try:
            wallet = CustomerWallet(
                wallet_id=wallet_id,
                tenant_id="tenant-001",
                billing_profile="standard",
                grandfather_until=current_deadline,
                legacy_price=0.01,
                standard_price=0.02,
                created_at="2026-01-01T00:00:00Z",
            )
            session.add(wallet)
            session.commit()
        finally:
            session.close()

        new_deadline = await wallet_service.renew_subscription(
            wallet_id=wallet_id, subscription_tier="premium"
        )

        assert new_deadline > current_deadline