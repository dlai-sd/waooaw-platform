# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-03
# constitutional_basis: C-088 (CCT-COUPON-01 discount cap), C-059 (CCT-REFERRAL-01 idempotency)
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from promotions.models import CouponValidation, DiscountResult, ReferralStatus
from promotions.router import _get_promotions_service
from promotions.service import PromotionsService


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE IF NOT EXISTS coupon_codes (
        coupon_id TEXT PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        discount_pct INTEGER NOT NULL DEFAULT 0,
        bonus_credits TEXT NOT NULL DEFAULT '{}',
        agent_type TEXT,
        min_tier TEXT,
        max_uses INTEGER,
        uses_count INTEGER NOT NULL DEFAULT 0,
        valid_from TEXT NOT NULL,
        valid_until TEXT,
        created_by TEXT NOT NULL DEFAULT 'founder',
        active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS referral_records (
        referral_id TEXT PRIMARY KEY,
        referrer_customer_id TEXT NOT NULL,
        referee_customer_id TEXT NOT NULL,
        coupon_id TEXT,
        referred_at TEXT NOT NULL,
        credit_status TEXT NOT NULL DEFAULT 'PENDING',
        credit_amount_paise INTEGER,
        credited_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS wallet_buckets (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
async def mock_redis():
    client = fakeredis.FakeAsyncRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.fixture
def mock_settings():
    return MagicMock(MAX_DISCOUNT_PCT=50)


@pytest.fixture
def promotions_service(session_factory, mock_redis, mock_settings):
    return PromotionsService(
        session_factory=session_factory,
        redis_client=mock_redis,
        settings=mock_settings,
    )


# ---------------------------------------------------------------------------
# Helpers: seed test data
# ---------------------------------------------------------------------------

async def _ins_coupon(
    sf,
    *,
    code: str = "LAUNCH10",
    discount_pct: int = 10,
    agent_type: str | None = None,
    min_tier: str | None = None,
    max_uses: int | None = None,
    uses_count: int = 0,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    active: bool = True,
    coupon_id: uuid.UUID | None = None,
) -> uuid.UUID:
    cid = coupon_id or uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO coupon_codes "
                "(coupon_id, code, discount_pct, bonus_credits, agent_type, min_tier, "
                "max_uses, uses_count, valid_from, valid_until, active) "
                "VALUES (:cid, :code, :disc, '{}', :at, :tier, :max_uses, :uses, :vf, :vu, :active)"
            ).bindparams(
                cid=str(cid),
                code=code,
                disc=discount_pct,
                at=agent_type,
                tier=min_tier,
                max_uses=max_uses,
                uses=uses_count,
                vf=(valid_from or now).isoformat(),
                vu=valid_until.isoformat() if valid_until else None,
                active=1 if active else 0,
            )
        )
        await session.commit()
    return cid


async def _ins_referral(
    sf,
    *,
    referrer_id: uuid.UUID,
    referee_id: uuid.UUID,
    coupon_id: uuid.UUID,
    credit_amount_paise: int = 500,
    credit_status: str = "PENDING",
) -> uuid.UUID:
    rid = uuid.uuid4()
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO referral_records "
                "(referral_id, referrer_customer_id, referee_customer_id, coupon_id, "
                "referred_at, credit_status, credit_amount_paise) "
                "VALUES (:rid, :referrer, :referee, :cid, :now, :status, :amount)"
            ).bindparams(
                rid=str(rid),
                referrer=str(referrer_id),
                referee=str(referee_id),
                cid=str(coupon_id),
                now=datetime.now(tz=timezone.utc).isoformat(),
                status=credit_status,
                amount=credit_amount_paise,
            )
        )
        await session.commit()
    return rid


async def _ins_wallet_bucket(sf, *, customer_id: uuid.UUID, balance_paise: int = 1000) -> uuid.UUID:
    bid = uuid.uuid4()
    async with sf() as session:
        await session.execute(
            text(
                "INSERT INTO wallet_buckets (id, customer_id, employment_contract_id, thread_type, balance_paise) "
                "VALUES (:id, :cid, :ec_id, 'llm_cloud', :bal)"
            ).bindparams(id=str(bid), cid=str(customer_id), ec_id=str(uuid.uuid4()), bal=balance_paise)
        )
        await session.commit()
    return bid


# ---------------------------------------------------------------------------
# validate_coupon
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_coupon_valid_returns_discount_pct(promotions_service, session_factory):
    """validate_coupon('LAUNCH10', ...) → CouponValidation(valid=True, discount_pct=10)."""
    await _ins_coupon(session_factory, code="LAUNCH10", discount_pct=10)

    result = await promotions_service.validate_coupon("LAUNCH10", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is True
    assert result.discount_pct == 10
    assert result.error_code is None


@pytest.mark.asyncio
async def test_validate_coupon_not_found(promotions_service):
    result = await promotions_service.validate_coupon("NOSUCHCODE", uuid.uuid4(), "DMA", "STANDARD")
    assert result.valid is False
    assert result.error_code == "COUPON_NOT_FOUND"


@pytest.mark.asyncio
async def test_validate_coupon_expired_by_valid_until(promotions_service, session_factory):
    """COUPON_EXPIRED when valid_until is in the past."""
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await _ins_coupon(session_factory, code="EXPIRED10", valid_until=past)

    result = await promotions_service.validate_coupon("EXPIRED10", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is False
    assert result.error_code == "COUPON_EXPIRED"


@pytest.mark.asyncio
async def test_validate_coupon_expired_by_valid_from_in_future(promotions_service, session_factory):
    """COUPON_EXPIRED when valid_from is in the future."""
    future = datetime.now(tz=timezone.utc) + timedelta(days=2)
    await _ins_coupon(session_factory, code="FUTURE10", valid_from=future)

    result = await promotions_service.validate_coupon("FUTURE10", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is False
    assert result.error_code == "COUPON_EXPIRED"


@pytest.mark.asyncio
async def test_validate_coupon_used_returns_coupon_used(promotions_service, session_factory):
    """COUPON_USED when uses_count >= max_uses."""
    await _ins_coupon(session_factory, code="MAXED10", max_uses=2, uses_count=2)

    result = await promotions_service.validate_coupon("MAXED10", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is False
    assert result.error_code == "COUPON_USED"


@pytest.mark.asyncio
async def test_validate_coupon_agent_mismatch(promotions_service, session_factory):
    """COUPON_AGENT_MISMATCH when coupon is restricted to a different agent_type."""
    await _ins_coupon(session_factory, code="DPA10", agent_type="DPA")

    result = await promotions_service.validate_coupon("DPA10", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is False
    assert result.error_code == "COUPON_AGENT_MISMATCH"


@pytest.mark.asyncio
async def test_validate_coupon_tier_mismatch(promotions_service, session_factory):
    """COUPON_TIER_MISMATCH when coupon requires a different tier."""
    await _ins_coupon(session_factory, code="PRO10", min_tier="PRO")

    result = await promotions_service.validate_coupon("PRO10", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is False
    assert result.error_code == "COUPON_TIER_MISMATCH"


# ---------------------------------------------------------------------------
# CCT-COUPON-01 — Discount cap enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cct_coupon_01_50pct_discount_applied(promotions_service, session_factory):
    """CCT-COUPON-01: 50% coupon on 1000p → discounted_price=500p, uses_count incremented."""
    coupon_id = await _ins_coupon(session_factory, code="HALF50", discount_pct=50)
    customer_id = uuid.uuid4()

    result = await promotions_service.apply_discount(
        coupon_id=coupon_id,
        customer_id=customer_id,
        original_price_paise=1000,
    )

    assert result.discounted_price_paise == 500
    assert result.discount_amount_paise == 500

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT uses_count FROM coupon_codes WHERE coupon_id = :cid").bindparams(cid=str(coupon_id))
        )
        assert row.fetchone()[0] == 1


@pytest.mark.asyncio
async def test_cct_coupon_01_discount_exceeds_cap_returns_error(promotions_service, session_factory):
    """CCT-COUPON-01: discount_pct > MAX_DISCOUNT_PCT → DISCOUNT_EXCEEDS_CAP."""
    await _ins_coupon(session_factory, code="BIG80", discount_pct=80)  # 80 > MAX_DISCOUNT_PCT=50

    result = await promotions_service.validate_coupon("BIG80", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is False
    assert result.error_code == "DISCOUNT_EXCEEDS_CAP"


@pytest.mark.asyncio
async def test_apply_discount_coupon_not_found_raises_404(promotions_service):
    """apply_discount on unknown coupon_id → 404."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await promotions_service.apply_discount(uuid.uuid4(), uuid.uuid4(), 1000)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_apply_discount_coupon_used_raises_409(promotions_service, session_factory):
    """apply_discount on exhausted coupon → 409."""
    from fastapi import HTTPException

    coupon_id = await _ins_coupon(session_factory, code="USED5", max_uses=1, uses_count=1)

    with pytest.raises(HTTPException) as exc_info:
        await promotions_service.apply_discount(coupon_id, uuid.uuid4(), 1000)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# CCT-REFERRAL-01 — Referral credit on conversion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cct_referral_01_credit_fires_on_apply_discount(
    promotions_service, session_factory
):
    """CCT-REFERRAL-01: apply_discount with PENDING referral → credit_status=CREDITED."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REF10", discount_pct=10)
    await _ins_referral(session_factory, referrer_id=referrer_id, referee_id=referee_id,
                        coupon_id=coupon_id, credit_amount_paise=300)
    await _ins_wallet_bucket(session_factory, customer_id=referrer_id, balance_paise=1000)

    result = await promotions_service.apply_discount(
        coupon_id=coupon_id,
        customer_id=referee_id,
        original_price_paise=1000,
    )

    assert result.referral_credited is True

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT credit_status FROM referral_records WHERE referee_customer_id = :cid")
            .bindparams(cid=str(referee_id))
        )
        assert row.fetchone()[0] == "CREDITED"


@pytest.mark.asyncio
async def test_cct_referral_01_referrer_wallet_credited(
    promotions_service, session_factory
):
    """CCT-REFERRAL-01: referrer's wallet balance increases by credit_amount_paise."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REF20", discount_pct=10)
    await _ins_referral(session_factory, referrer_id=referrer_id, referee_id=referee_id,
                        coupon_id=coupon_id, credit_amount_paise=300)
    bucket_id = await _ins_wallet_bucket(session_factory, customer_id=referrer_id, balance_paise=1000)

    await promotions_service.apply_discount(
        coupon_id=coupon_id,
        customer_id=referee_id,
        original_price_paise=1000,
    )

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT balance_paise FROM wallet_buckets WHERE id = :bid").bindparams(bid=str(bucket_id))
        )
        assert row.fetchone()[0] == 1300  # 1000 + 300 credit


@pytest.mark.asyncio
async def test_cct_referral_01_no_duplicate_credit_idempotent(
    promotions_service, session_factory
):
    """CCT-REFERRAL-01: credit fires only once per referral pair (idempotent)."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REF30", discount_pct=10)
    referral_id = await _ins_referral(session_factory, referrer_id=referrer_id, referee_id=referee_id,
                                       coupon_id=coupon_id, credit_amount_paise=300)
    bucket_id = await _ins_wallet_bucket(session_factory, customer_id=referrer_id, balance_paise=1000)

    # First credit
    await promotions_service.credit_referrer(referral_id)

    # Second credit (idempotent — should not double-credit)
    await promotions_service.credit_referrer(referral_id)

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT balance_paise FROM wallet_buckets WHERE id = :bid").bindparams(bid=str(bucket_id))
        )
        assert row.fetchone()[0] == 1300  # still 1000 + 300, NOT 1600


@pytest.mark.asyncio
async def test_apply_discount_no_referral_returns_false(promotions_service, session_factory):
    """apply_discount with no referral record → referral_credited=False."""
    coupon_id = await _ins_coupon(session_factory, code="NOREF10", discount_pct=10)

    result = await promotions_service.apply_discount(
        coupon_id=coupon_id,
        customer_id=uuid.uuid4(),
        original_price_paise=500,
    )

    assert result.referral_credited is False


# ---------------------------------------------------------------------------
# credit_referrer standalone
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_credit_referrer_standalone_idempotent(promotions_service, session_factory):
    """credit_referrer() directly: second call is no-op."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="STDALONE", discount_pct=5)
    referral_id = await _ins_referral(session_factory, referrer_id=referrer_id, referee_id=referee_id,
                                       coupon_id=coupon_id, credit_amount_paise=200)
    await _ins_wallet_bucket(session_factory, customer_id=referrer_id, balance_paise=500)

    await promotions_service.credit_referrer(referral_id)
    await promotions_service.credit_referrer(referral_id)  # must not raise or double-credit

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT credit_status FROM referral_records WHERE referral_id = :id").bindparams(id=str(referral_id))
        )
        assert row.fetchone()[0] == "CREDITED"


# ---------------------------------------------------------------------------
# get_referral_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_referral_status_returns_referrals(promotions_service, session_factory):
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REFSTAT10")
    await _ins_referral(session_factory, referrer_id=referrer_id, referee_id=referee_id,
                        coupon_id=coupon_id, credit_amount_paise=100, credit_status="CREDITED")

    status = await promotions_service.get_referral_status(referrer_id)

    assert len(status.referrals) == 1
    assert status.referrals[0].credit_status == "CREDITED"
    assert status.total_credits_paise == 100


@pytest.mark.asyncio
async def test_get_referral_status_empty_for_unknown_customer(promotions_service):
    status = await promotions_service.get_referral_status(uuid.uuid4())
    assert status.referrals == []
    assert status.total_credits_paise == 0


# ---------------------------------------------------------------------------
# validate_coupon: agent_type=None (all agents) and min_tier=None (all tiers)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_coupon_no_agent_restriction_matches_all(promotions_service, session_factory):
    """coupon.agent_type is None → matches any agent_type."""
    await _ins_coupon(session_factory, code="UNIVERSAL", discount_pct=5, agent_type=None)

    result = await promotions_service.validate_coupon("UNIVERSAL", uuid.uuid4(), "DCA", "STANDARD")

    assert result.valid is True


@pytest.mark.asyncio
async def test_validate_coupon_max_uses_none_is_unlimited(promotions_service, session_factory):
    """max_uses=None means unlimited uses."""
    await _ins_coupon(session_factory, code="UNLIMITED", discount_pct=5, max_uses=None, uses_count=9999)

    result = await promotions_service.validate_coupon("UNLIMITED", uuid.uuid4(), "DMA", "STANDARD")

    assert result.valid is True


# ---------------------------------------------------------------------------
# Router-level tests (FastAPI dependency overrides)
# ---------------------------------------------------------------------------


def _make_mock_promotions_service():
    svc = MagicMock()
    svc.validate_coupon = AsyncMock(return_value=CouponValidation(
        valid=True, discount_pct=10, bonus_credits={}, expires_at=None
    ))
    svc.apply_discount = AsyncMock(return_value=DiscountResult(
        discounted_price_paise=900, discount_amount_paise=100, referral_credited=False
    ))
    svc.get_referral_status = AsyncMock(return_value=ReferralStatus(referrals=[], total_credits_paise=0))
    return svc


def _clear_overrides():
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_router_validate_coupon_returns_200():
    mock_svc = _make_mock_promotions_service()
    app.dependency_overrides[_get_promotions_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/promotions/validate-coupon", json={
                "coupon_code": "LAUNCH10",
                "customer_id": str(uuid.uuid4()),
                "agent_type": "DMA",
                "subscription_tier": "STANDARD",
            })
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["discount_pct"] == 10


@pytest.mark.asyncio
async def test_router_validate_coupon_invalid_returns_200_with_error():
    mock_svc = MagicMock()
    mock_svc.validate_coupon = AsyncMock(return_value=CouponValidation(
        valid=False, discount_pct=0, bonus_credits={}, expires_at=None, error_code="COUPON_EXPIRED"
    ))
    app.dependency_overrides[_get_promotions_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/promotions/validate-coupon", json={
                "coupon_code": "OLD",
                "customer_id": str(uuid.uuid4()),
                "agent_type": "DMA",
                "subscription_tier": "STANDARD",
            })
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json()["error_code"] == "COUPON_EXPIRED"


@pytest.mark.asyncio
async def test_router_apply_discount_returns_200():
    mock_svc = _make_mock_promotions_service()
    app.dependency_overrides[_get_promotions_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/promotions/apply-discount", json={
                "coupon_id": str(uuid.uuid4()),
                "customer_id": str(uuid.uuid4()),
                "original_price_paise": 1000,
            })
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["discounted_price_paise"] == 900


@pytest.mark.asyncio
async def test_router_referral_status_returns_200():
    mock_svc = _make_mock_promotions_service()
    app.dependency_overrides[_get_promotions_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/promotions/referral-status/{uuid.uuid4()}")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json()["total_credits_paise"] == 0
