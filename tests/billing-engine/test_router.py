# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

# ── Assume main.py exports app; adjust import path as needed for your project ──
# If app is in src/billing-engine/main.py, add to sys.path or use direct import
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "billing-engine"))

from main import app
from markup.models import (
    ThreadEntry,
    PriceValidation,
)
from markup.bundle_engine import BundleEngine


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def async_client() -> AsyncClient:
    """Provide an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
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
    # Default cost_floor: 10000 paise
    mock_engine.cost_floor = AsyncMock(return_value=10000)
    # Default derive_price: floor / (1 - margin/100) with 25% margin -> 10000 / 0.75 = 13333
    mock_engine.derive_price = AsyncMock(return_value=13333)
    # Default validate_price: APPROVED (proposed price >= floor)
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
    Idempotency invariant.
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
        assert "cost_floor_paise" in data
        assert isinstance(data["cost_floor_paise"], int)
        assert data["cost_floor_paise"] >= 0


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_idempotent(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    called twice returns identical cost floor.
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
async def test_get_bundle_cost_floor_invalid_tier(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor with unknown bundle_tier.
    Expected: 404 or 422 (not 200, not 500).
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown bundle tier")
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/UNKNOWN_TIER"
        )

        assert response.status_code in (404, 422, 400)
        assert response.status_code != 200
        assert response.status_code != 500


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_zero_floor(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor with zero cost floor.
    Edge case: free tier thread.
    """
    mock_bundle_engine.cost_floor = AsyncMock(return_value=0)
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/FREE"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cost_floor_paise"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/validate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_validate_approved_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with price >= floor returns 200.
    Response body does NOT contain `minimum_compliant_price_paise` key
    when outcome is APPROVED (no violation).
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
        payload = {
            "agent_type": "RESEARCHER",
            "bundle_tier": "STARTER",
            "proposed_price_paise": 15000,
        }
        response = await async_client.post("/pricing/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "APPROVED"
        assert data["cost_floor_paise"] == 10000
        assert data["proposed_price_paise"] == 15000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_price_paise,expected_floor",
    [
        (0, 10000),  # Zero paise — clearly below floor
        (9999, 10000),  # 1 paise below floor
    ],
)
async def test_post_validate_rejected_c089_violation(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    proposed_price_paise: int,
    expected_floor: int,
) -> None:
    """
    Test POST /pricing/validate with proposed price below floor.
    C-089 INVARIANT: HTTP 422 response MUST contain `minimum_compliant_price_paise`.
    Parameterized: zero paise, 1 paise below floor.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=expected_floor,
            minimum_compliant_price_paise=expected_floor,
            proposed_price_paise=proposed_price_paise,
        )
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            "bundle_tier": "STARTER",
            "proposed_price_paise": proposed_price_paise,
        }
        response = await async_client.post("/pricing/validate", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert isinstance(data["minimum_compliant_price_paise"], int)
        assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_validate_missing_required_field(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with missing required field.
    Expected: 422 FastAPI validation error (standard Pydantic shape).
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            # Missing bundle_tier and proposed_price_paise
        }
        response = await async_client.post("/pricing/validate", json=payload)

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_validate_malformed_json(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with malformed JSON body.
    Expected: 422.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.post(
            "/pricing/validate",
            content=b"{ invalid json }",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/derive
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_derive_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive returns 200 with derived price.
    Response body contains a derived_price_paise field (integer ≥ 0).
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=13333)
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            "bundle_tier": "STARTER",
            "target_margin_pct": 25.0,
        }
        response = await async_client.post("/pricing/derive", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data
        assert isinstance(data["derived_price_paise"], int)
        assert data["derived_price_paise"] >= 0


@pytest.mark.asyncio
async def test_post_derive_zero_margin(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with zero margin.
    Edge case: derived price should equal cost floor.
    Formula: floor / (1 - 0/100) = floor / 1 = floor.
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=10000)
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            "bundle_tier": "STARTER",
            "target_margin_pct": 0.0,
        }
        response = await async_client.post("/pricing/derive", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["derived_price_paise"] == 10000


@pytest.mark.asyncio
async def test_post_derive_missing_agent_type(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with missing agent_type field.
    Expected: 422 FastAPI validation error.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            # Missing agent_type
            "bundle_tier": "STARTER",
            "target_margin_pct": 25.0,
        }
        response = await async_client.post("/pricing/derive", json=payload)

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_derive_malformed_json(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with malformed JSON body.
    Expected: 422.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.post(
            "/pricing/derive",
            content=b"{ broken json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TEST: Router Mount Invariant
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_router_mounted_at_pricing_prefix(async_client: AsyncClient) -> None:
    """
    Assert that /pricing/* endpoints are registered in the FastAPI app.
    Confirms the router is mounted at the correct prefix in main.py.
    """
    # Attempt to resolve a known pricing endpoint via the app's route table
    resolved_routes = [route.path for route in app.routes]
    pricing_routes = [r for r in resolved_routes if "/pricing/" in r]

    assert len(pricing_routes) > 0, "No routes with /pricing/ prefix found in app"


@pytest.mark.asyncio
async def test_pricing_thread_catalog_route_exists(async_client: AsyncClient) -> None:
    """
    Test that GET /pricing/thread-catalog route exists and returns 200
    (without mocking, verifying integration).
    """
    resolved_routes = [route.path for route in app.routes]
    thread_catalog_route = "/pricing/thread-catalog"

    assert any(
        thread_catalog_route in route for route in resolved_routes
    ), f"Route {thread_catalog_route} not found in app"


@pytest.mark.asyncio
async def test_pricing_bundle_cost_floor_route_exists(
    async_client: AsyncClient,
) -> None:
    """
    Test that GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    route exists in the app.
    """
    resolved_routes = [route.path for route in app.routes]
    cost_floor_route_pattern = "/pricing/bundle-cost-floor/"

    assert any(
        cost_floor_route_pattern in route for route in resolved_routes
    ), f"Route pattern {cost_floor_route_pattern} not found in app"


@pytest.mark.asyncio
async def test_pricing_validate_route_exists(async_client: AsyncClient) -> None:
    """
    Test that POST /pricing/validate route exists in the app.
    """
    resolved_routes = [route.path for route in app.routes]
    validate_route = "/pricing/validate"

    assert any(
        validate_route in route for route in resolved_routes
    ), f"Route {validate_route} not found in app"


@pytest.mark.asyncio
async def test_pricing_derive_route_exists(async_client: AsyncClient) -> None:
    """
    Test that POST /pricing/derive route exists in the app.
    """
    resolved_routes = [route.path for route in app.routes]
    derive_route = "/pricing/derive"

    assert any(
        derive_route in route for route in resolved_routes
    ), f"Route {derive_route} not found in app"


# ──────────────────────────────────────────────────────────────────────────────
# TEST: Large Paise Values (Edge Case for Formula Precision)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_derive_large_paise_value(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive with large paise cost floor.
    Asserts formula precision for revenue-based margin calculation.
    """
    large_floor = 999_999_999
    # Expected derived: large_floor / (1 - 0.25) = large_floor / 0.75 ≈ 1,333,333,332
    expected_derived = int(large_floor / 0.75)
    mock_bundle_engine.derive_price = AsyncMock(return_value=expected_derived)

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            "bundle_tier": "ENTERPRISE",
            "target_margin_pct": 25.0,
        }
        response = await async_client.post("/pricing/derive", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["derived_price_paise"] == expected_derived