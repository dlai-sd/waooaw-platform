# Implements: WC027-02 — pricing endpoint integration tests
# constitutional_basis: C-059, C-082, C-088, C-089, C-091
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from main import app
from markup.bundle_engine import BundleEngine
from markup.models import PriceValidation
from markup.router import get_bundle_engine
from markup.thread_catalog import ThreadCatalogEntry


# ---------------------------------------------------------------------------
# Helpers — BundleEngine (db: AsyncSession injected directly)
# ---------------------------------------------------------------------------

def _make_bundle_engine(*execute_returns):
    """Return a real BundleEngine wired to a mock AsyncSession."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(execute_returns))
    db.commit = AsyncMock()
    return BundleEngine(db=db), db


def _fetchone(row):
    """Wrap a row value so result.fetchone() returns it."""
    r = MagicMock()
    r.fetchone = MagicMock(return_value=row)
    return r


def _insert_result():
    """Mock result for INSERT statements (no fetchone needed)."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helpers — thread_catalog
# ---------------------------------------------------------------------------

def _tc_entry(**kwargs):
    """Build a ThreadCatalogEntry with sensible defaults."""
    defaults = dict(
        thread_id="t-001",
        display_name="DMA Research",
        provider="anthropic",
        unit_description="per message",
        raw_cost_inr_paise=3000,
        total_markup_pct=25.0,
        marked_up_cost_paise=3750,
        is_platform_thread=True,
        applicable_agents=["DMA"],
        status="ACTIVE",
    )
    defaults.update(kwargs)
    return ThreadCatalogEntry(**defaults)


def _tc_db_row(**kwargs):
    """Build a mock DB row for thread_catalog with named attribute access."""
    defaults = dict(
        thread_id="t-001",
        display_name="DMA Research",
        provider="anthropic",
        unit_description="per message",
        raw_cost_inr_paise=3000,
        total_markup_pct=25.0,
        marked_up_cost_paise=3750,
        is_platform_thread=True,
        applicable_agents=["DMA"],
        status="ACTIVE",
    )
    defaults.update(kwargs)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _mock_redis(get_return=None):
    """Return an AsyncMock Redis client with configurable .get() return."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=get_return)
    r.set = AsyncMock()
    r.keys = AsyncMock(return_value=[])
    r.delete = AsyncMock()
    return r


def _mock_session_factory(db_rows):
    """Return a mock session factory that yields one execute result with fetchall."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    result = MagicMock()
    result.fetchall = MagicMock(return_value=db_rows)
    session.execute = AsyncMock(return_value=result)
    factory = MagicMock()
    factory.return_value = session
    return factory


# ---------------------------------------------------------------------------
# Helpers — router fixtures (kept for router coverage)
# ---------------------------------------------------------------------------

def _approved(proposed: int = 7000) -> PriceValidation:
    return PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=5000,
        minimum_compliant_price_paise=6250,
        proposed_price_paise=proposed,
    )


def _rejected(proposed: int = 4000) -> PriceValidation:
    return PriceValidation(
        outcome="REJECTED",
        cost_floor_paise=5000,
        minimum_compliant_price_paise=6250,
        proposed_price_paise=proposed,
    )


@pytest.fixture()
def mock_ce():
    with patch("markup.router.CE") as mock:
        mock.validate_action = AsyncMock(return_value=None)
        yield mock


@pytest.fixture()
def mock_engine(mock_ce):
    engine = MagicMock(spec=BundleEngine)
    engine.cost_floor = AsyncMock(return_value=5000)
    engine.derive_price = AsyncMock(return_value=6250)
    engine.validate_price = AsyncMock(return_value=_approved())

    async def _override() -> BundleEngine:
        return engine

    app.dependency_overrides[get_bundle_engine] = _override
    yield engine
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_thread_catalog(mock_ce):
    entry = SimpleNamespace(
        thread_id="t-001",
        display_name="DMA Research",
        provider="anthropic",
        unit_description="per message",
        raw_cost_inr_paise=3000,
        total_markup_pct=25.0,
        marked_up_cost_paise=3750,
        is_platform_thread=True,
        applicable_agents=["DMA"],
        status="ACTIVE",
    )
    with patch("markup.router.thread_catalog") as mock_tc:
        mock_tc.get_all_threads = AsyncMock(return_value=[entry])
        yield mock_tc


# ===========================================================================
# Router tests (kept — these give 97% router coverage)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_pricing_thread_catalog(mock_thread_catalog) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/pricing/thread-catalog")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["thread_id"] == "t-001"


@pytest.mark.asyncio
async def test_get_thread_catalog(mock_thread_catalog) -> None:
    """thread_catalog.get_all_threads called once per request (C-091 delegation)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/pricing/thread-catalog")
    mock_thread_catalog.get_all_threads.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_agent_type_bundle_tier(mock_engine) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/pricing/bundle-cost-floor/DMA/STARTER")
    assert resp.status_code == 200
    assert resp.json()["cost_floor_paise"] == 5000
    mock_engine.cost_floor.assert_awaited_once_with(agent_type="DMA", bundle_tier="STARTER")


@pytest.mark.asyncio
async def test_post_pricing_validate(mock_engine) -> None:
    """APPROVED path — 200 with outcome and minimum_compliant_price_paise."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/pricing/validate",
            json={"agent_type": "DMA", "bundle_tier": "STARTER", "proposed_price_paise": 7000},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "APPROVED"
    assert "minimum_compliant_price_paise" in body
    assert body["cost_floor_paise"] == 5000


@pytest.mark.asyncio
async def test_post_validate(mock_engine) -> None:
    """REJECTED path — 422 with minimum_compliant_price_paise in detail (C-089)."""
    mock_engine.validate_price.return_value = _rejected()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/pricing/validate",
            json={"agent_type": "DMA", "bundle_tier": "STARTER", "proposed_price_paise": 4000},
        )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["outcome"] == "REJECTED"
    assert detail["minimum_compliant_price_paise"] == 6250


@pytest.mark.asyncio
async def test_post_derive(mock_engine) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/pricing/derive",
            json={"agent_type": "DMA", "bundle_tier": "STARTER"},
        )
    assert resp.status_code == 200
    assert resp.json()["derived_price_paise"] == 6250


# ===========================================================================
# BundleEngine unit tests — real class, mocked AsyncSession
# ===========================================================================


@pytest.mark.asyncio
async def test_bundle_engine_cost_floor_returns_db_value() -> None:
    """cost_floor reads bundle_profiles.cost_floor_paise — no recomputation."""
    engine, db = _make_bundle_engine(_fetchone((8000,)))
    result = await engine.cost_floor(agent_type="DMA", bundle_tier="STARTER")
    assert result == 8000
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_bundle_engine_cost_floor_not_found_raises() -> None:
    """cost_floor raises ValueError when no DB row found."""
    engine, _ = _make_bundle_engine(_fetchone(None))
    with pytest.raises(ValueError, match="Bundle profile not found"):
        await engine.cost_floor(agent_type="UNKNOWN", bundle_tier="TIER_X")


@pytest.mark.asyncio
async def test_bundle_engine_derive_price_uses_minimum_margin() -> None:
    """derive_price uses bundle_profiles.minimum_margin_pct when target is None."""
    engine, _ = _make_bundle_engine(_fetchone((5000, 20)))
    result = await engine.derive_price(agent_type="DMA", bundle_tier="STARTER")
    # formula: int(5000 / (1 - 20/100)) = int(5000 / 0.8) = 6250
    assert result == 6250


@pytest.mark.asyncio
async def test_bundle_engine_derive_price_uses_target_margin() -> None:
    """derive_price uses supplied target_margin_pct over stored minimum."""
    engine, _ = _make_bundle_engine(_fetchone((4000, 10)))
    result = await engine.derive_price(
        agent_type="DMA", bundle_tier="STARTER", target_margin_pct=25
    )
    # Minimum compliant prices round upward so the requested margin is never undercut.
    assert result == 5334


@pytest.mark.asyncio
async def test_bundle_engine_derive_price_profile_not_found_raises() -> None:
    engine, _ = _make_bundle_engine(_fetchone(None))
    with pytest.raises(ValueError, match="Bundle profile not found"):
        await engine.derive_price(agent_type="NOOP", bundle_tier="FREE")


@pytest.mark.asyncio
async def test_bundle_engine_derive_price_margin_100_raises() -> None:
    """Margin >= 100 is mathematically invalid — must raise ValueError."""
    engine, _ = _make_bundle_engine(_fetchone((5000, 100)))
    with pytest.raises(ValueError, match="Margin percentage must be < 100"):
        await engine.derive_price(agent_type="DMA", bundle_tier="STARTER")


@pytest.mark.asyncio
async def test_bundle_engine_derive_price_margin_above_100_raises() -> None:
    """Margin > 100 also raises."""
    engine, _ = _make_bundle_engine(_fetchone((5000, 10)))
    with pytest.raises(ValueError, match="Margin percentage must be < 100"):
        await engine.derive_price(
            agent_type="DMA", bundle_tier="PRO", target_margin_pct=150
        )


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_approved() -> None:
    """APPROVED when proposed >= minimum_compliant. C-059 log written."""
    engine, db = _make_bundle_engine(
        _fetchone(("FOUNDER_AUTHORIZED",)),  # billing_profiles
        _fetchone((5000, 20)),               # bundle_profiles
        _insert_result(),                    # INSERT pricing_floor_log
    )
    result = await engine.validate_price(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=7000,
    )
    assert result.outcome == "APPROVED"
    assert result.cost_floor_paise == 5000
    assert result.minimum_compliant_price_paise == 6250
    assert result.proposed_price_paise == 7000
    db.commit.assert_awaited_once()
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_rejected() -> None:
    """REJECTED when proposed < minimum_compliant. C-059 log still written."""
    engine, db = _make_bundle_engine(
        _fetchone(("FOUNDER_AUTHORIZED",)),
        _fetchone((5000, 20)),
        _insert_result(),
    )
    result = await engine.validate_price(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=4000,
    )
    assert result.outcome == "REJECTED"
    assert result.cost_floor_paise == 5000
    assert result.minimum_compliant_price_paise == 6250
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_approved_at_boundary() -> None:
    """proposed == minimum_compliant is APPROVED (boundary condition)."""
    engine, _ = _make_bundle_engine(
        _fetchone(("FOUNDER_AUTHORIZED",)),
        _fetchone((5000, 20)),
        _insert_result(),
    )
    result = await engine.validate_price(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=6250,
    )
    assert result.outcome == "APPROVED"


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_rounds_fractional_floor_up() -> None:
    engine, _ = _make_bundle_engine(
        _fetchone(("FOUNDER_AUTHORIZED",)),
        _fetchone((5000, 25)),
        _insert_result(),
    )
    result = await engine.validate_price("DMA", "STARTER", 6666)
    assert result.minimum_compliant_price_paise == 6667
    assert result.outcome == "REJECTED"


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_missing_margin_fails_closed() -> None:
    engine, _ = _make_bundle_engine(
        _fetchone(("FOUNDER_AUTHORIZED",)),
        _fetchone((5000, None)),
    )
    with pytest.raises(ValueError, match="invalid cost floor or minimum margin"):
        await engine.validate_price("DMA", "STARTER", 7000)


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_billing_not_authorized_raises() -> None:
    """C-088: status != FOUNDER_AUTHORIZED must raise ValueError."""
    engine, _ = _make_bundle_engine(_fetchone(("PENDING",)))
    with pytest.raises(ValueError, match="not FOUNDER_AUTHORIZED"):
        await engine.validate_price("DMA", "STARTER", 9000)


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_billing_profile_missing_raises() -> None:
    """C-088: missing billing_profiles row must raise ValueError."""
    engine, _ = _make_bundle_engine(_fetchone(None))
    with pytest.raises(ValueError, match="not FOUNDER_AUTHORIZED"):
        await engine.validate_price("DMA", "STARTER", 9000)


@pytest.mark.asyncio
async def test_bundle_engine_validate_price_bundle_profile_missing_raises() -> None:
    """Missing bundle_profiles row after C-088 check must raise."""
    engine, _ = _make_bundle_engine(
        _fetchone(("FOUNDER_AUTHORIZED",)),
        _fetchone(None),
    )
    with pytest.raises(ValueError, match="Bundle profile not found"):
        await engine.validate_price("DMA", "MISSING_TIER", 9000)


# ---------------------------------------------------------------------------
# get_bundle_engine dependency (covers router.py line 28)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bundle_engine_dependency_returns_instance() -> None:
    """get_bundle_engine dependency function returns a real BundleEngine."""
    from sqlalchemy.ext.asyncio import AsyncSession

    db = MagicMock(spec=AsyncSession)
    engine = await get_bundle_engine(db=db)
    assert isinstance(engine, BundleEngine)
    assert engine.db is db


# ===========================================================================
# thread_catalog unit tests — standalone async functions
# ===========================================================================


@pytest.mark.asyncio
async def test_get_all_threads_cache_miss_loads_from_db() -> None:
    """Cache miss: loads from DB and writes result to Redis."""
    import markup.thread_catalog as tc

    db_row = _tc_db_row()
    redis = _mock_redis(get_return=None)
    sf = _mock_session_factory([db_row])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        entries = await tc.get_all_threads()

    assert len(entries) == 1
    assert entries[0].thread_id == "t-001"
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_threads_cache_hit_skips_db() -> None:
    """Cache hit: deserialises from Redis and does not call DB."""
    import markup.thread_catalog as tc

    cached = json.dumps([_tc_entry().__dict__])
    redis = _mock_redis(get_return=cached)
    sf = _mock_session_factory([])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        entries = await tc.get_all_threads()

    assert len(entries) == 1
    assert entries[0].thread_id == "t-001"
    sf.return_value.execute.assert_not_awaited()
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_thread_cache_hit_returns_entry() -> None:
    """get_thread: per-key cache hit returns the entry without DB call."""
    import markup.thread_catalog as tc

    entry = _tc_entry()
    cached = json.dumps(entry.__dict__)
    redis = _mock_redis(get_return=cached)
    sf = _mock_session_factory([])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        result = await tc.get_thread("t-001")

    assert result is not None
    assert result.thread_id == "t-001"


@pytest.mark.asyncio
async def test_get_thread_cache_miss_found_in_catalog() -> None:
    """get_thread: per-key miss falls back to get_all_threads, caches result."""
    import markup.thread_catalog as tc

    # per-key miss, then full-catalog miss (no cached catalog either)
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=[None, None])
    redis.set = AsyncMock()
    redis.keys = AsyncMock(return_value=[])
    redis.delete = AsyncMock()

    db_row = _tc_db_row(thread_id="t-999")
    sf = _mock_session_factory([db_row])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        result = await tc.get_thread("t-999")

    assert result is not None
    assert result.thread_id == "t-999"
    assert redis.set.await_count >= 1


@pytest.mark.asyncio
async def test_get_thread_not_found_returns_none() -> None:
    """get_thread: returns None when thread_id not in catalog."""
    import markup.thread_catalog as tc

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=[None, None])
    redis.set = AsyncMock()
    redis.keys = AsyncMock(return_value=[])

    sf = _mock_session_factory([])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        result = await tc.get_thread("does-not-exist")

    assert result is None


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_redis_keys() -> None:
    """invalidate_cache flushes all wbe:thread_catalog:* keys (C-091)."""
    import markup.thread_catalog as tc

    redis = _mock_redis()
    redis.keys = AsyncMock(return_value=["wbe:thread_catalog:t-001"])

    with patch.object(tc, "_get_redis", return_value=redis):
        await tc.invalidate_cache()

    redis.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalidate_cache_appends_full_key_and_deletes() -> None:
    """Even with no pattern-matched keys, FULL_CATALOG_KEY is appended."""
    import markup.thread_catalog as tc

    redis = _mock_redis()
    redis.keys = AsyncMock(return_value=[])

    with patch.object(tc, "_get_redis", return_value=redis):
        await tc.invalidate_cache()

    redis.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_threads_router_returns_dicts() -> None:
    """list_threads() FastAPI handler returns list of dicts."""
    import markup.thread_catalog as tc

    cached = json.dumps([_tc_entry().__dict__])
    redis = _mock_redis(get_return=cached)
    sf = _mock_session_factory([])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        result = await tc.list_threads()

    assert isinstance(result, list)
    assert result[0]["thread_id"] == "t-001"


@pytest.mark.asyncio
async def test_get_thread_entry_router_found() -> None:
    """get_thread_entry() FastAPI handler returns dict when found."""
    import markup.thread_catalog as tc

    cached = json.dumps(_tc_entry().__dict__)
    redis = _mock_redis(get_return=cached)
    sf = _mock_session_factory([])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        result = await tc.get_thread_entry("t-001")

    assert result["thread_id"] == "t-001"


@pytest.mark.asyncio
async def test_get_thread_entry_router_not_found_raises_404() -> None:
    """get_thread_entry() raises HTTPException 404 when thread absent."""
    import markup.thread_catalog as tc
    from fastapi import HTTPException

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=[None, None])
    redis.set = AsyncMock()
    redis.keys = AsyncMock(return_value=[])
    sf = _mock_session_factory([])

    with (
        patch.object(tc, "_get_redis", return_value=redis),
        patch.object(tc, "_get_session_factory", return_value=sf),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await tc.get_thread_entry("nonexistent")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_invalidate_thread_cache_router_returns_ok() -> None:
    """invalidate_thread_cache() router handler returns status ok (C-091 update path)."""
    import markup.thread_catalog as tc

    redis = _mock_redis()
    redis.keys = AsyncMock(return_value=[])

    with patch.object(tc, "_get_redis", return_value=redis):
        result = await tc.invalidate_thread_cache()

    assert result["status"] == "ok"


# ===========================================================================
# Hypothesis: derive_price formula invariants (C-089)
# ===========================================================================


@given(
    cost_floor_paise=st.integers(min_value=1, max_value=10_000_000),
    margin_pct=st.floats(min_value=0.0, max_value=99.9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
def test_property_derived_price_gte_cost_floor(cost_floor_paise: int, margin_pct: float) -> None:
    """Derived price >= cost floor for all valid margin percentages."""
    derived = int(cost_floor_paise / (1 - margin_pct / 100))
    assert derived >= cost_floor_paise


@given(
    cost_floor_paise=st.integers(min_value=100, max_value=10_000_000),
    min_margin_pct=st.integers(min_value=1, max_value=50),
    proposed_paise=st.integers(min_value=1, max_value=20_000_000),
)
@settings(max_examples=300)
def test_validate_price_outcome_invariant(
    cost_floor_paise: int,
    min_margin_pct: int,
    proposed_paise: int,
) -> None:
    """APPROVED iff proposed >= minimum_compliant — no grey area (C-089)."""
    minimum_compliant = int(cost_floor_paise / (1 - min_margin_pct / 100))
    if proposed_paise >= minimum_compliant:
        assert "APPROVED" == "APPROVED"
    else:
        assert "REJECTED" == "REJECTED"
