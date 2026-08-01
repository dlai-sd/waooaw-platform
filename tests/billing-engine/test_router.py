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
    returns identical response on consecutive calls (idempotent read).
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
    Test GET /pricing/bundle-cost-floor with unknown agent_type returns non-200 status.
    Assert it is either 404 or 422, not 500.
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown agent type")
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER"
        )

        assert response.status_code in (404, 422)
        assert response.status_code != 500


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/validate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_pricing_validate_approved_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with proposed price >= floor returns 200 (APPROVED).
    Response MUST NOT contain 'minimum_compliant_price_paise' key (no violation).
    """
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
        # When APPROVED, minimum_compliant_price_paise should NOT appear
        assert "minimum_compliant_price_paise" not in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_paise,floor_paise,expectation_name",
    [
        (0, 10000, "zero_paise"),
        (9999, 10000, "one_paise_below_floor"),
    ],
)
async def test_post_pricing_validate_rejected_c089_violation(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    proposed_paise: int,
    floor_paise: int,
    expectation_name: str,
) -> None:
    """
    Test POST /pricing/validate with proposed price < floor returns HTTP 422.
    Response JSON MUST contain 'minimum_compliant_price_paise' key with integer > 0.
    C-089 constitutional invariant: no pricing below cost floor.

    Parameterised sub-cases:
      - proposed_paise=0 (zero breach)
      - proposed_paise=floor-1 (boundary: 1 paise below floor)
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=floor_paise,
            minimum_compliant_price_paise=floor_paise,
            proposed_price_paise=proposed_paise,
        )
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = {
            "agent_type": "RESEARCHER",
            "bundle_tier": "STARTER",
            "proposed_price_paise": proposed_paise,
        }
        response = await async_client.post("/pricing/validate", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["outcome"] == "REJECTED"
        assert "minimum_compliant_price_paise" in data
        assert isinstance(data["minimum_compliant_price_paise"], int)
        assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_pricing_validate_missing_required_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with missing required field returns 422
    FastAPI validation error (standard Pydantic shape, not C-089 shape).
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier, proposed_price_paise
    }
    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    # FastAPI validation error shape: 'detail' key with list of errors
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_post_pricing_validate_malformed_json(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with malformed JSON body returns 422.
    """
    response = await async_client.post(
        "/pricing/validate",
        content=b"{invalid json",
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
    Test POST /pricing/derive with valid payload returns 200.
    Response body contains a derived price field (integer ≥ 0, in paise).
    """
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
async def test_post_pricing_derive_missing_required_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with missing required field returns 422.
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier, target_margin_pct (if required)
    }
    response = await async_client.post("/pricing/derive", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_post_pricing_derive_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with malformed JSON body returns 422.
    """
    response = await async_client.post(
        "/pricing/derive",
        content=b"{ bad json }",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER MOUNT INVARIANT
# ──────────────────────────────────────────────────────────────────────────────


def test_pricing_router_mounted_at_correct_prefix() -> None:
    """
    Assert that the /pricing/ router is mounted in the main FastAPI app.
    Check that routes exist for /pricing/thread-catalog, /pricing/bundle-cost-floor, etc.
    """
    route_paths = [route.path for route in app.routes]
    
    # Assert that at least one /pricing/ route exists
    pricing_routes = [path for path in route_paths if "/pricing/" in path]
    assert len(pricing_routes) > 0, "No /pricing/ routes found in app"
    
    # Assert that expected endpoints are present
    expected_paths = [
        "/pricing/thread-catalog",
        "/pricing/bundle-cost-floor/{agent_type}/{bundle_tier}",
        "/pricing/validate",
        "/pricing/derive",
    ]
    for expected_path in expected_paths:
        assert any(
            expected_path in path for path in route_paths
        ), f"Expected path {expected_path} not found in app routes"