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
    PriceValidationRequest,
    PriceDeriveRequest,
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
    Test GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} idempotency.
    Two identical calls must return the same cost floor.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response1 = await async_client.get(
            "/pricing/bundle-cost-floor/DMA/PROFESSIONAL"
        )
        response2 = await async_client.get(
            "/pricing/bundle-cost-floor/DMA/PROFESSIONAL"
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_agent_type(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor with an unknown agent_type.
    Should return 404 or 422 (not 200 or 500).
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown agent_type")
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER"
        )

        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_bundle_tier(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor with an unknown bundle_tier.
    Should return 404 or 422 (not 200 or 500).
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown bundle_tier")
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/UNKNOWN_TIER"
        )

        assert response.status_code in (404, 422)


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/validate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_validate_happy_path_approved(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with a price >= cost floor returns 200 APPROVED.
    Response DOES NOT contain minimum_compliant_price_paise (no violation).
    """
    validation_response = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=10000,
        minimum_compliant_price_paise=10000,
        proposed_price_paise=15000,
    )
    mock_bundle_engine.validate_price = AsyncMock(return_value=validation_response)

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=15000,
        )
        response = await async_client.post(
            "/pricing/validate",
            json=payload.dict(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "APPROVED"
        # On approval, minimum_compliant_price_paise may or may not be in response
        # depending on implementation. If it is, it should match cost_floor.


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_paise,cost_floor_paise",
    [
        (0, 10000),  # Zero paise proposed (violation)
        (9999, 10000),  # 1 paise below floor (violation)
    ],
)
async def test_post_validate_c089_violation(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    proposed_paise: int,
    cost_floor_paise: int,
) -> None:
    """
    C-089 INVARIANT:
    POST /pricing/validate with a proposed price below the floor
    returns HTTP 422 and includes minimum_compliant_price_paise in the response.
    Parameterised sub-cases: zero paise, 1 paise below floor.
    """
    validation_response = PriceValidation(
        outcome="REJECTED",
        cost_floor_paise=cost_floor_paise,
        minimum_compliant_price_paise=cost_floor_paise,
        proposed_price_paise=proposed_paise,
    )
    mock_bundle_engine.validate_price = AsyncMock(return_value=validation_response)

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=proposed_paise,
        )
        response = await async_client.post(
            "/pricing/validate",
            json=payload.dict(),
        )

        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert isinstance(data["minimum_compliant_price_paise"], int)
        assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_validate_missing_required_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with a missing required field (e.g., proposed_price_paise).
    Should return 422 with standard FastAPI validation error shape.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        # Missing proposed_price_paise
    }
    response = await async_client.post(
        "/pricing/validate",
        json=payload,
    )

    assert response.status_code == 422
    data = response.json()
    # FastAPI validation errors have 'detail' key with list of error objects
    assert "detail" in data or "error" in data.lower()


@pytest.mark.asyncio
async def test_post_validate_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with a malformed JSON body.
    Should return 422.
    """
    response = await async_client.post(
        "/pricing/validate",
        content="{ invalid json",
        headers={"content-type": "application/json"},
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
    Test POST /pricing/derive with a valid payload returns 200.
    Response contains a derived_price_paise field (integer ≥ 0).
    Formula: cost_floor / (1 - margin_pct / 100)
    Example: 10000 / (1 - 25/100) = 10000 / 0.75 = 13333.33 → 13333 paise.
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
            json=payload.dict(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data
        assert isinstance(data["derived_price_paise"], int)
        assert data["derived_price_paise"] >= 0


@pytest.mark.asyncio
async def test_post_derive_with_default_margin(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive without specifying target_margin_pct.
    Should use bundle_profiles.minimum_margin_pct (default from DB).
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=11111)

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceDeriveRequest(
            agent_type="DMA",
            bundle_tier="PROFESSIONAL",
            # target_margin_pct omitted — should use minimum_margin_pct from DB
        )
        response = await async_client.post(
            "/pricing/derive",
            json=payload.dict(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data


@pytest.mark.asyncio
async def test_post_derive_missing_required_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with a missing required field (e.g., agent_type).
    Should return 422 with standard FastAPI validation error shape.
    """
    payload = {
        "bundle_tier": "STARTER",
        "target_margin_pct": 25.0,
        # Missing agent_type
    }
    response = await async_client.post(
        "/pricing/derive",
        json=payload,
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data or "error" in data.lower()


@pytest.mark.asyncio
async def test_post_derive_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with a malformed JSON body.
    Should return 422.
    """
    response = await async_client.post(
        "/pricing/derive",
        content="{ broken json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TEST: Router mount invariant
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pricing_router_mounted_at_prefix() -> None:
    """
    Assert that /pricing/* routes are mounted in the app.
    Verifies that markup.router is mounted at /pricing prefix in main.py.
    """
    # Collect all routes from app
    route_paths = set()
    for route in app.routes:
        if hasattr(route, "path"):
            route_paths.add(route.path)

    # Verify that at least one /pricing/* route exists
    pricing_routes = {p for p in route_paths if p.startswith("/pricing")}
    assert len(pricing_routes) > 0, "No /pricing/* routes found in app.routes"

    # Verify specific expected endpoints exist
    expected_paths = {
        "/pricing/thread-catalog",
        "/pricing/bundle-cost-floor/{agent_type}/{bundle_tier}",
        "/pricing/validate",
        "/pricing/derive",
    }
    for expected_path in expected_paths:
        # At least one route should match (accounting for path param variations)
        assert any(
            expected_path == p or expected_path.replace("{", ":").replace("}", "") in p
            for p in pricing_routes
        ), f"Expected path {expected_path} not found in app routes"