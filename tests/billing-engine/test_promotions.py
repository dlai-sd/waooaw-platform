# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
# constitutional_basis: C-088 (CCT-COUPON-01 discount cap), C-089 (cost floor), C-059 (CCT-REFERRAL-01 idempotency)
from __future__ import annotations

import ast
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent))

from main import app  # noqa: E402
from promotions import coupon_versions  # noqa: E402
from promotions.coupon_versions import CouponError, quote_coupon, redeem_coupon  # noqa: E402
from promotions.models import CouponValidation, DiscountResult, ReferralStatus  # noqa: E402
from promotions.router import _get_promotions_service  # noqa: E402
from promotions.service import PromotionsService  # noqa: E402
from pricing.models import PricingKind  # noqa: E402
from pricing_support import (  # noqa: E402
    AGENT_TYPE,
    AGENT_VERSION,
    DMA_PRICE,
    PACKAGE_SUBJECT,
    START,
    FakeReference,
    make_harness,
    dma_package_body,
)


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
        agent_version TEXT,
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
    agent_version: str | None = None,
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
                "(coupon_id, code, discount_pct, bonus_credits, agent_type, agent_version, min_tier, "
                "max_uses, uses_count, valid_from, valid_until, active) "
                "VALUES (:cid, :code, :disc, '{}', :at, :av, :tier, :max_uses, :uses, :vf, :vu, :active)"
            ).bindparams(
                cid=str(cid),
                code=code,
                disc=discount_pct,
                at=agent_type,
                av=agent_version,
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
async def test_validate_coupon_without_expiry_or_use_limit_remains_valid(
    promotions_service,
    session_factory,
    mock_settings,
):
    mock_settings.MAX_DISCOUNT_PCT = 100
    await _ins_coupon(
        session_factory,
        code="DEMO100",
        discount_pct=100,
        max_uses=None,
        valid_until=None,
    )

    result = await promotions_service.validate_coupon(
        "DEMO100",
        uuid.uuid4(),
        "DIGITAL_MARKETING_LOCAL_SERVICE",
        "STANDARD",
    )

    assert result.valid is True
    assert result.discount_pct == 100
    assert result.expires_at is None
    assert result.error_code is None


@pytest.mark.asyncio
async def test_validate_commercial_preview_coupon_reads_global_coupon_registry(
    promotions_service,
    session_factory,
):
    await _ins_coupon(session_factory, code="PREVIEW25", discount_pct=25)

    result = await promotions_service.validate_commercial_preview_coupon(
        "PREVIEW25",
        "TUTOR",
        "1.0.0",
    )

    assert result.valid is True
    assert result.discount_pct == 25


@pytest.mark.asyncio
async def test_validate_commercial_preview_coupon_rejects_tier_restricted_coupon(
    promotions_service,
    session_factory,
):
    await _ins_coupon(session_factory, code="TIER25", discount_pct=25, min_tier="PRO")

    result = await promotions_service.validate_commercial_preview_coupon(
        "TIER25",
        "TUTOR",
        "1.0.0",
    )

    assert result.valid is False
    assert result.error_code == "COUPON_TIER_MISMATCH"


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
async def test_validate_coupon_agent_version_mismatch(promotions_service, session_factory):
    await _ins_coupon(
        session_factory,
        code="DMA100",
        agent_type="DMA",
        agent_version="1.0.0",
    )

    result = await promotions_service.validate_coupon(
        "DMA100",
        uuid.uuid4(),
        "DMA",
        "STANDARD",
        agent_version="2.0.0",
    )

    assert result.valid is False
    assert result.error_code == "COUPON_VERSION_MISMATCH"


@pytest.mark.asyncio
async def test_demo_coupon_matches_canonical_marketplace_professional(
    promotions_service,
    session_factory,
    mock_settings,
):
    mock_settings.MAX_DISCOUNT_PCT = 100
    await _ins_coupon(
        session_factory,
        code="DEMO100",
        discount_pct=100,
        agent_type="DIGITAL_MARKETING_LOCAL_SERVICE",
        agent_version="1.0.0",
    )

    result = await promotions_service.validate_coupon(
        "DEMO100",
        uuid.uuid4(),
        "DIGITAL_MARKETING_LOCAL_SERVICE",
        "STANDARD",
        agent_version="1.0.0",
    )

    assert result.valid is True
    assert result.discount_pct == 100


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
async def test_cct_referral_01_credit_fires_on_apply_discount(promotions_service, session_factory):
    """CCT-REFERRAL-01: apply_discount with PENDING referral → credit_status=CREDITED."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REF10", discount_pct=10)
    await _ins_referral(
        session_factory, referrer_id=referrer_id, referee_id=referee_id, coupon_id=coupon_id, credit_amount_paise=300
    )
    await _ins_wallet_bucket(session_factory, customer_id=referrer_id, balance_paise=1000)

    result = await promotions_service.apply_discount(
        coupon_id=coupon_id,
        customer_id=referee_id,
        original_price_paise=1000,
    )

    assert result.referral_credited is True

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT credit_status FROM referral_records WHERE referee_customer_id = :cid").bindparams(cid=str(referee_id))
        )
        assert row.fetchone()[0] == "CREDITED"


@pytest.mark.asyncio
async def test_cct_referral_01_referrer_wallet_never_credited(promotions_service, session_factory):
    """WC-136 C5-07: a referral reward is goodwill, so the referrer's wallet balance never changes."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REF20", discount_pct=10)
    await _ins_referral(
        session_factory, referrer_id=referrer_id, referee_id=referee_id, coupon_id=coupon_id, credit_amount_paise=300
    )
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
        assert row.fetchone()[0] == 1000  # goodwill is never wallet credit


@pytest.mark.asyncio
async def test_cct_referral_01_no_duplicate_credit_idempotent(promotions_service, session_factory):
    """CCT-REFERRAL-01: the status moves to CREDITED once (idempotent) and the wallet is untouched."""
    referrer_id = uuid.uuid4()
    referee_id = uuid.uuid4()
    coupon_id = await _ins_coupon(session_factory, code="REF30", discount_pct=10)
    referral_id = await _ins_referral(
        session_factory, referrer_id=referrer_id, referee_id=referee_id, coupon_id=coupon_id, credit_amount_paise=300
    )
    bucket_id = await _ins_wallet_bucket(session_factory, customer_id=referrer_id, balance_paise=1000)

    # First credit
    await promotions_service.credit_referrer(referral_id)

    # Second credit (idempotent — should not double-credit)
    await promotions_service.credit_referrer(referral_id)

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT balance_paise FROM wallet_buckets WHERE id = :bid").bindparams(bid=str(bucket_id))
        )
        assert row.fetchone()[0] == 1000  # unchanged: no wallet credit on any call


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
    referral_id = await _ins_referral(
        session_factory, referrer_id=referrer_id, referee_id=referee_id, coupon_id=coupon_id, credit_amount_paise=200
    )
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
    await _ins_referral(
        session_factory,
        referrer_id=referrer_id,
        referee_id=referee_id,
        coupon_id=coupon_id,
        credit_amount_paise=100,
        credit_status="CREDITED",
    )

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
    svc.validate_coupon = AsyncMock(return_value=CouponValidation(valid=True, discount_pct=10, bonus_credits={}, expires_at=None))
    svc.apply_discount = AsyncMock(
        return_value=DiscountResult(discounted_price_paise=900, discount_amount_paise=100, referral_credited=False)
    )
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
            resp = await c.post(
                "/promotions/validate-coupon",
                json={
                    "coupon_code": "LAUNCH10",
                    "customer_id": str(uuid.uuid4()),
                    "agent_type": "DMA",
                    "agent_version": "1.0.0",
                    "subscription_tier": "STANDARD",
                },
            )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["discount_pct"] == 10


@pytest.mark.asyncio
async def test_router_validate_coupon_invalid_returns_200_with_error():
    mock_svc = MagicMock()
    mock_svc.validate_coupon = AsyncMock(
        return_value=CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=None, error_code="COUPON_EXPIRED")
    )
    app.dependency_overrides[_get_promotions_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/promotions/validate-coupon",
                json={
                    "coupon_code": "OLD",
                    "customer_id": str(uuid.uuid4()),
                    "agent_type": "DMA",
                    "agent_version": "1.0.0",
                    "subscription_tier": "STANDARD",
                },
            )
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
            resp = await c.post(
                "/promotions/apply-discount",
                json={
                    "coupon_id": str(uuid.uuid4()),
                    "customer_id": str(uuid.uuid4()),
                    "original_price_paise": 1000,
                },
            )
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


# ---------------------------------------------------------------------------
# WC-136 C5-07: goodwill coupons are versioned discounts, never wallet credit
# ---------------------------------------------------------------------------

from markup.package_engine import ThreadRate  # noqa: E402

COUPON_CODE = "GOODWILL50"


class _Result:
    def __init__(self, rows=(), rowcount=1, scalar=None):
        self._rows = list(rows)
        self.rowcount = rowcount
        self._scalar = scalar

    def scalar_one(self):
        return self._scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self._rows[0] if self._rows else None


class _RedemptionSession:
    """Answers the four statements the coupon module issues against business.coupon_version_redemptions."""

    def __init__(self):
        self.rows: list[dict] = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        if "pg_advisory_xact_lock" in sql:
            return _Result()
        if "count(*)" in sql:
            return _Result(scalar=sum(1 for row in self.rows if row["version_id"] == params["version"]))
        if "INSERT INTO business.coupon_version_redemptions" in sql:
            key = (params["version"], params["relationship"], params["event"], params["period"])
            if any((r["version_id"], r["relationship_id"], r["event"], r["period_start"]) == key for r in self.rows):
                return _Result(rowcount=0)
            self.rows.append(
                {
                    "redemption_id": params["redemption"],
                    "version_id": params["version"],
                    "coupon_code": params["code"],
                    "relationship_id": params["relationship"],
                    "event": params["event"],
                    "period_start": params["period"],
                    "price_incl_gst_paise": params["price"],
                    "discount_paise": params["discount"],
                    "reason": params["reason"],
                    "idempotency_key": params["key"],
                    "redeemed_at": params["at"],
                }
            )
            return _Result()
        if "WHERE idempotency_key" in sql:
            return _Result(rows=[row for row in self.rows if row["idempotency_key"] == params["key"]])
        raise AssertionError(f"unexpected statement: {sql}")


def _coupon_body(**changes):
    body = {
        "code": COUPON_CODE,
        "agentType": AGENT_TYPE,
        "agentVersion": AGENT_VERSION,
        "percentOff": 50,
        "expiresAt": (START + timedelta(days=30)).isoformat(),
        "reason": "Goodwill after a delayed first post",
        "maxRedemptions": 2,
    }
    body.update(changes)
    return body


@pytest.fixture
def coupon_world(monkeypatch):
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    harness.repository.seed(PricingKind.COUPON, f"coupon:{COUPON_CODE}", _coupon_body())
    session = _RedemptionSession()
    monkeypatch.setattr(coupon_versions, "SqlPricingRepository", lambda _session: harness.repository)
    monkeypatch.setattr(coupon_versions, "SqlPackageReferenceData", lambda _session: harness.reference)
    return harness, session


def _quote_args(**changes):
    args = dict(
        code=COUPON_CODE,
        agent_type=AGENT_TYPE,
        agent_version=AGENT_VERSION,
        price_incl_gst_paise=DMA_PRICE,
        event="HIRE",
        at=START,
    )
    args.update(changes)
    return args


def _redeem_args(**changes):
    args = dict(
        code=COUPON_CODE,
        agent_type=AGENT_TYPE,
        agent_version=AGENT_VERSION,
        tenant_id=uuid.uuid4(),
        relationship_id=uuid.uuid4(),
        event="RENEWAL",
        period_start=START,
        price_incl_gst_paise=DMA_PRICE,
        idempotency_key=uuid.uuid4(),
        at=START,
    )
    args.update(changes)
    return args


async def test_coupon_quote_discounts_the_package_price_and_writes_nothing(coupon_world):
    _, session = coupon_world

    quote = await quote_coupon(session, **_quote_args())

    assert (quote.discount_paise, quote.discounted_price_paise) == (DMA_PRICE // 2, DMA_PRICE // 2)
    assert quote.reason == "Goodwill after a delayed first post"
    assert session.rows == []


async def test_coupon_below_cost_floor_is_refused_at_redemption(coupon_world):
    harness, session = coupon_world
    harness.repository.seed(PricingKind.COUPON, f"coupon:{COUPON_CODE}", _coupon_body(percentOff=95))

    with pytest.raises(CouponError) as refused:
        await redeem_coupon(session, **_redeem_args())

    assert (refused.value.code, refused.value.status_code) == ("PRICING_BELOW_FLOOR", 422)
    assert session.rows == []


async def test_coupon_floor_is_rechecked_against_the_rates_in_force(coupon_world):
    harness, session = coupon_world
    assert (await quote_coupon(session, **_quote_args())).discount_paise > 0
    harness.reference.rates["llm_pro"] = ThreadRate("llm_pro", 3000, True)

    with pytest.raises(CouponError) as refused:
        await quote_coupon(session, **_quote_args())

    assert refused.value.code == "PRICING_BELOW_FLOOR"


async def test_coupon_without_a_matching_package_cannot_prove_the_floor(coupon_world):
    _, session = coupon_world

    with pytest.raises(CouponError) as refused:
        await quote_coupon(session, **_quote_args(price_incl_gst_paise=DMA_PRICE + 1))

    assert refused.value.code == "COUPON_FLOOR_UNVERIFIABLE"


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"code": "UNKNOWN1"}, "COUPON_NOT_FOUND"),
        ({"event": "TOPUP"}, "COUPON_EVENT_NOT_ALLOWED"),
        ({"agent_type": "OTHER"}, "COUPON_AGENT_MISMATCH"),
        ({"agent_version": "9.9.9"}, "COUPON_VERSION_MISMATCH"),
        ({"at": START + timedelta(days=31)}, "COUPON_EXPIRED"),
    ],
)
async def test_coupon_refusals_carry_stable_codes(coupon_world, changes, code):
    _, session = coupon_world
    with pytest.raises(CouponError) as refused:
        await quote_coupon(session, **_quote_args(**changes))
    assert refused.value.code == code


async def test_coupon_redemption_is_recorded_with_its_reason_and_capped(coupon_world):
    _, session = coupon_world

    first = await redeem_coupon(session, **_redeem_args())
    await redeem_coupon(session, **_redeem_args())

    assert first.replayed is False
    assert first.event == "RENEWAL"
    assert [row["reason"] for row in session.rows] == ["Goodwill after a delayed first post"] * 2
    assert all(row["discount_paise"] == DMA_PRICE // 2 for row in session.rows)
    with pytest.raises(CouponError) as used:
        await redeem_coupon(session, **_redeem_args())
    assert used.value.code == "COUPON_USED"


async def test_coupon_redemption_replays_by_key_and_refuses_a_second_use_in_the_period(coupon_world):
    _, session = coupon_world
    args = _redeem_args()

    first = await redeem_coupon(session, **args)
    again = await redeem_coupon(session, **args)

    assert again.replayed is True
    assert again.redemption_id == first.redemption_id
    assert len(session.rows) == 1
    with pytest.raises(CouponError) as same_period:
        await redeem_coupon(session, **{**args, "idempotency_key": uuid.uuid4()})
    assert same_period.value.code == "COUPON_ALREADY_REDEEMED"
    with pytest.raises(CouponError) as conflict:
        await redeem_coupon(session, **{**args, "event": "HIRE"})
    assert conflict.value.code == "COUPON_IDEMPOTENCY_CONFLICT"


def test_the_only_wallet_credit_paths_are_ledger_credit_and_trial_grant():
    wallet = Path(__file__).resolve().parents[2] / "src" / "billing-engine" / "wallet"
    credit_like = re.compile(r"credit|top_?up|bonus|goodwill|adjust|refund|gift|deposit|support")
    found: set[str] = set()
    lot_writers: set[str] = set()
    for source in sorted(wallet.glob("*.py")):
        text_ = source.read_text(encoding="utf-8")
        if "INSERT INTO business.wallet_lots" in text_:
            lot_writers.add(source.name)
        for node in ast.walk(ast.parse(text_)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and credit_like.search(node.name):
                found.add(node.name)

    from wallet.entity_models import LOT_KINDS

    assert found == {"credit", "credit_trial_grant"}
    assert lot_writers == {"ledger.py"}
    assert LOT_KINDS == ("PERIOD_CREDIT", "TOPUP_CREDIT", "GRANT")
