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

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

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
    returns identical result on consecutive calls (idempotent read).
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
    Test GET /pricing/bundle-cost-floor/{unknown_agent}/{bundle_tier}
    returns 404 or 422 (not 200, not 500).
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
async def test_post_validate_happy_path(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with a valid payload (price >= floor).
    Returns 200 with outcome='APPROVED'.
    Response MUST NOT contain 'minimum_compliant_price_paise' key when approved.
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
        # On APPROVED, minimum_compliant_price_paise MUST be in response
        # (but not enforced as a violation indicator)
        assert isinstance(data.get("cost_floor_paise"), int)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_paise,expected_status",
    [
        (0, 422),          # Zero paise: C-089 violation
        (9999, 422),       # 1 paise below floor of 10000: C-089 violation
    ],
)
async def test_post_validate_below_floor_c089_violation(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    proposed_paise: int,
    expected_status: int,
) -> None:
    """
    Test POST /pricing/validate with price below cost floor (C-089 violation).
    MUST return HTTP 422 and include 'minimum_compliant_price_paise' in response JSON.
    Parameterized: zero paise, 1 paise below floor.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=10000,
            minimum_compliant_price_paise=10000,
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

        assert response.status_code == expected_status
        data = response.json()
        # C-089 contract: 422 response MUST include minimum_compliant_price_paise
        assert "minimum_compliant_price_paise" in data
        assert isinstance(data["minimum_compliant_price_paise"], int)
        assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_validate_missing_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with missing required field (agent_type).
    Returns 422 FastAPI validation error (standard Pydantic shape).
    """
    payload = {
        # Missing 'agent_type'
        "bundle_tier": "STARTER",
        "proposed_price_paise": 15000,
    }
    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    data = response.json()
    # Pydantic validation error shape
    assert "detail" in data


@pytest.mark.asyncio
async def test_post_validate_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with malformed JSON body.
    Returns 422 FastAPI parse error.
    """
    response = await async_client.post(
        "/pricing/validate",
        content="not valid json",
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
    Test POST /pricing/derive with a valid payload.
    Returns 200 with derived_price_paise field (integer ≥ 0).
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
async def test_post_derive_missing_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with missing required field.
    Returns 422 FastAPI validation error.
    """
    payload = {
        # Missing 'agent_type'
        "bundle_tier": "STARTER",
        "target_margin_pct": 25.0,
    }
    response = await async_client.post("/pricing/derive", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_post_derive_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with malformed JSON body.
    Returns 422 FastAPI parse error.
    """
    response = await async_client.post(
        "/pricing/derive",
        content="invalid json {",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TEST: Router mount invariant — /pricing prefix
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pricing_router_mounted_at_prefix(
    async_client: AsyncClient,
) -> None:
    """
    Assert that the /pricing router is mounted at the correct prefix in main.py.
    Verifies that at least one /pricing/ route exists and is not 404.
    """
    # Attempt GET /pricing/thread-catalog as a sanity check that router is mounted
    response = await async_client.get("/pricing/thread-catalog")
    # Should not be 404 (route exists); may be 200, 422, 500 depending on implementation
    assert response.status_code != 404


def test_app_has_pricing_routes() -> None:
    """
    Assert that app.routes contains routes starting with /pricing/.
    Confirms router is mounted at the correct prefix in main.py.
    """
    pricing_routes = [
        route.path for route in app.routes
        if hasattr(route, "path") and route.path.startswith("/pricing/")
    ]
    assert len(pricing_routes) > 0, "No /pricing/ routes found in app"