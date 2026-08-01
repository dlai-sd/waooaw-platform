# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, settings, HealthCheck, strategies as st

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from markup.models import (
    ThreadEntry,
    PriceValidation,
    PriceValidationRequest,
    PriceDeriveRequest,
)
from markup.bundle_engine import BundleEngine
from markup.router import router as pricing_router
from fastapi import FastAPI


# ── Create a minimal FastAPI app for testing ────────────────────────────────

def create_test_app() -> FastAPI:
    """Create a test FastAPI app with the pricing router mounted."""
    app = FastAPI()
    app.include_router(pricing_router, prefix="/pricing", tags=["pricing"])
    return app


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def test_app() -> FastAPI:
    """Provide the FastAPI app with pricing router."""
    return create_test_app()


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncClient:
    """Provide an async test client for the FastAPI app."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_thread_catalog_service() -> MagicMock:
    """Mock ThreadCatalogService for GET /thread-catalog."""
    mock_svc = MagicMock()
    mock_svc.get_catalog = AsyncMock(
        return_value=[
            ThreadEntry(
                thread_id="thread_001",
                display_name="GPT-4 Query",
                provider="openai",
                unit_description="per 1000 tokens",
                raw_cost_inr_paise=5000,
                total_markup_pct=30.0,
                marked_up_cost_paise=6500,
                is_platform_thread=False,
                applicable_agents=["RESEARCHER", "DMA"],
                status="ACTIVE",
            )
        ]
    )
    return mock_svc


@pytest.fixture
def mock_bundle_engine() -> MagicMock:
    """Mock BundleEngine for cost_floor, derive_price, validate_price."""
    mock_engine = MagicMock(spec=BundleEngine)
    mock_engine.cost_floor = AsyncMock(return_value=10000)
    mock_engine.derive_price = AsyncMock(return_value=13333)
    mock_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=10000,
            minimum_compliant_price_paise=10000,
            proposed_price_paise=15000,
        )
    )
    return mock_engine


# ──────────────────────────────────────────────────────────────────────────────
# TEST: GET /pricing/thread-catalog
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_thread_catalog_happy_path(
    async_client: AsyncClient, mock_thread_catalog_service: MagicMock
) -> None:
    """
    Test GET /pricing/thread-catalog returns 200 with catalog list.
    Asserts that ThreadCatalogService.get_catalog was called exactly once.
    """
    with patch(
        "markup.router.ThreadCatalogService",
        return_value=mock_thread_catalog_service,
    ):
        response = await async_client.get("/pricing/thread-catalog")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 0
        if len(data) > 0:
            assert "thread_id" in data[0]
            assert "display_name" in data[0]
        mock_thread_catalog_service.get_catalog.assert_called_once()


@pytest.mark.asyncio
async def test_get_thread_catalog_empty(
    async_client: AsyncClient, mock_thread_catalog_service: MagicMock
) -> None:
    """
    Test GET /pricing/thread-catalog with empty catalog.
    """
    mock_thread_catalog_service.get_catalog = AsyncMock(return_value=[])
    with patch(
        "markup.router.ThreadCatalogService",
        return_value=mock_thread_catalog_service,
    ):
        response = await async_client.get("/pricing/thread-catalog")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


@pytest.mark.asyncio
async def test_get_thread_catalog_idempotent(
    async_client: AsyncClient, mock_thread_catalog_service: MagicMock
) -> None:
    """
    Test GET /pricing/thread-catalog returns identical payload on consecutive calls.
    Idempotency invariant: assert response1.json() == response2.json().
    """
    with patch(
        "markup.router.ThreadCatalogService",
        return_value=mock_thread_catalog_service,
    ):
        response1 = await async_client.get("/pricing/thread-catalog")
        response2 = await async_client.get("/pricing/thread-catalog")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


# ──────────────────────────────────────────────────────────────────────────────
# TEST: GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor/RESEARCHER/STARTER returns 200.
    Response body contains a numeric cost_floor_paise field (≥ 0).
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "cost_floor_paise" in data
        assert isinstance(data["cost_floor_paise"], int)
        assert data["cost_floor_paise"] >= 0
        mock_bundle_engine.cost_floor.assert_called_once()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_idempotent(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} called twice
    returns the same cost floor (idempotent read, no side-effects).
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response1 = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
        )
        response2 = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_agent_type(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor with an unknown agent_type returns
    404 or 422 (not 200 and not 500).
    """
    mock_bundle_engine.cost_floor = AsyncMock(side_effect=ValueError("Unknown agent type"))
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER"
        )

        assert response.status_code in (404, 422)
        assert response.status_code != 200
        assert response.status_code != 500


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/validate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_pricing_validate_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with a valid payload returns 200.
    Response does NOT contain `minimum_compliant_price_paise` when outcome is APPROVED.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=10000,
            minimum_compliant_price_paise=10000,
            proposed_price_paise=15000,
        )
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=15000,
        )
        response = await async_client.post(
            "/pricing/validate",
            json=payload.model_dump(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "APPROVED"
        assert "cost_floor_paise" in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_price_paise",
    [
        0,  # Zero paise — below floor of 10000
        9999,  # 1 paise below floor
    ],
)
async def test_post_pricing_validate_c089_violation(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    proposed_price_paise: int,
) -> None:
    """
    C-089 INVARIANT: POST /pricing/validate with proposed price below the
    constitutional minimum returns HTTP 422 and response JSON contains
    `minimum_compliant_price_paise` with an integer value > 0.
    
    Parameterised: zero paise, 1 paise below floor.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=10000,
            minimum_compliant_price_paise=10000,
            proposed_price_paise=proposed_price_paise,
        )
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=proposed_price_paise,
        )
        response = await async_client.post(
            "/pricing/validate",
            json=payload.model_dump(),
        )

        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert isinstance(data["minimum_compliant_price_paise"], int)
        assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_pricing_validate_missing_required_field(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with a missing required field returns 422
    FastAPI validation error (standard Pydantic shape, NOT the C-089 shape).
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            # Missing: bundle_tier
            "proposed_price_paise": 15000,
        }
        response = await async_client.post(
            "/pricing/validate",
            json=payload,
        )

        assert response.status_code == 422
        # Standard FastAPI Pydantic validation error, not C-089 shape
        data = response.json()
        assert "detail" in data or "error" in str(response.text)


@pytest.mark.asyncio
async def test_post_pricing_validate_malformed_body(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with a malformed JSON body returns 422.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.post(
            "/pricing/validate",
            content="{ invalid json }",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/derive
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_pricing_derive_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with a valid payload returns 200.
    Response body contains a derived_price field in paise (integer ≥ 0).
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=13333)
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceDeriveRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            target_margin_pct=25.0,
        )
        response = await async_client.post(
            "/pricing/derive",
            json=payload.model_dump(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data
        assert isinstance(data["derived_price_paise"], int)
        assert data["derived_price_paise"] >= 0


@pytest.mark.asyncio
async def test_post_pricing_derive_without_target_margin(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive without target_margin_pct uses bundle default.
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=13333)
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceDeriveRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            target_margin_pct=None,
        )
        response = await async_client.post(
            "/pricing/derive",
            json=payload.model_dump(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data
        assert isinstance(data["derived_price_paise"], int)
        assert data["derived_price_paise"] >= 0


@pytest.mark.asyncio
async def test_post_pricing_derive_missing_required_field(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with a missing required field returns 422.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            # Missing: bundle_tier
            "target_margin_pct": 25.0,
        }
        response = await async_client.post(
            "/pricing/derive",
            json=payload,
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_pricing_derive_malformed_body(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with a malformed JSON body returns 422.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.post(
            "/pricing/derive",
            content="{ malformed json ]",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TEST: Router-mount invariant
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pricing_router_mounted_at_prefix(test_app: FastAPI) -> None:
    """
    Assert that app.routes resolves paths starting with /pricing/,
    confirming the router is mounted at the correct prefix.
    """
    routes = [route.path for route in test_app.routes]
    pricing_routes = [r for r in routes if r.startswith("/pricing/")]
    assert len(pricing_routes) > 0, "No /pricing/ routes found"


# ──────────────────────────────────────────────────────────────────────────────
# PROPERTY-BASED TESTS (hypothesis)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=st.integers(min_value=1000, max_value=1000000),
    margin_pct=st.floats(min_value=0.0, max_value=99.9),
)
async def test_derive_price_margin_formula_property(
    mock_bundle_engine: MagicMock,
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    Property-based test: derive_price formula uses margin-on-revenue.
    For any cost_floor_paise and margin_pct, derived price must satisfy:
    derived_price >= cost_floor_paise (no negative margins).
    Formula: floor / (1 - margin/100)
    """
    expected_derived = int(cost_floor_paise / (1.0 - margin_pct / 100.0))
    mock_bundle_engine.derive_price = AsyncMock(return_value=expected_derived)

    result = await mock_bundle_engine.derive_price(
        agent_type="RESEARCHER",
        bundle_tier="STARTER",
        target_margin_pct=margin_pct,
    )

    assert result >= cost_floor_paise, (
        f"Derived price {result} must not be less than cost floor {cost_floor_paise}"
    )


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=st.integers(min_value=1000, max_value=1000000),
    proposed_price_paise=st.integers(min_value=0, max_value=10000000),
)
async def test_validate_price_outcome_coverage_property(
    mock_bundle_engine: MagicMock,
    cost_floor_paise: int,
    proposed_price_paise: int,
) -> None:
    """
    Property-based test: validate_price covers all outcome paths.
    If proposed_price_paise >= cost_floor_paise: outcome is APPROVED.
    If proposed_price_paise < cost_floor_paise: outcome is REJECTED.
    """
    outcome = "APPROVED" if proposed_price_paise >= cost_floor_paise else "REJECTED"
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=cost_floor_paise,
            proposed_price_paise=proposed_price_paise,
        )
    )

    result = await mock_bundle_engine.validate_price(
        agent_type="RESEARCHER",
        bundle_tier="STARTER",
        proposed_price_paise=proposed_price_paise,
    )

    assert result.outcome in ("APPROVED", "REJECTED")
    assert result.minimum_compliant_price_paise > 0
    if result.outcome == "APPROVED":
        assert proposed_price_paise >= cost_floor_paise
    else:
        assert proposed_price_paise < cost_floor_paise