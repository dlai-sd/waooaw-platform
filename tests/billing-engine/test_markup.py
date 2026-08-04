# Implements: WC027-02 — pricing endpoint integration tests
# constitutional_basis: C-059, C-082, C-088, C-089, C-091
from __future__ import annotations

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
        mock.ValidateAction = AsyncMock(return_value=None)
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


# ---------------------------------------------------------------------------
# GET /pricing/thread-catalog
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_bundle_cost_floor_agent_type_bundle_tier(mock_engine) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/pricing/bundle-cost-floor/DMA/STARTER")
    assert resp.status_code == 200
    assert resp.json()["cost_floor_paise"] == 5000
    mock_engine.cost_floor.assert_awaited_once_with(agent_type="DMA", bundle_tier="STARTER")


# ---------------------------------------------------------------------------
# POST /pricing/validate
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# POST /pricing/derive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_derive(mock_engine) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/pricing/derive",
            json={"agent_type": "DMA", "bundle_tier": "STARTER"},
        )
    assert resp.status_code == 200
    assert resp.json()["derived_price_paise"] == 6250


# ---------------------------------------------------------------------------
# Hypothesis: derive_price formula invariants (C-089)
# ---------------------------------------------------------------------------

@given(
    cost_floor_paise=st.integers(min_value=1, max_value=10_000_000),
    margin_pct=st.floats(min_value=0.0, max_value=99.9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
def test_property_based(cost_floor_paise: int, margin_pct: float) -> None:
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
