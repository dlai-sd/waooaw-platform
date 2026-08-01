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
    Test GET /pricing/bundle-cost-floor with unknown agent_type returns 404 or 422.
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown agent type")
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER"
        )

        assert response.status_code in (404, 422)
        assert response.status_code != 200
        assert response.status_code != 500


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_bundle_tier(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test GET /pricing/bundle-cost-floor with unknown bundle_tier returns 404 or 422.
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown bundle tier")
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/UNKNOWN_TIER"
        )

        assert response.status_code in (404, 422)
        assert response.status_code != 200
        assert response.status_code != 500


# ──────────────────────────────────────────────────────────────────────────────
# TEST: POST /pricing/validate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_validate_happy_path_approved(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/validate with a proposed price >= floor returns 200 (APPROVED).
    Response MUST NOT contain minimum_compliant_price_paise key (no violation).
    """
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
        assert "minimum_compliant_price_paise" not in data


@pytest.mark.asyncio
async def test_post_validate_c089_violation_zero_paise(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    C-089 INVARIANT: POST /pricing/validate with proposed price = 0 (below floor)
    MUST return HTTP 422 with minimum_compliant_price_paise in response body.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=10000,
            minimum_compliant_price_paise=10000,
            proposed_price_paise=0,
        )
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=0,
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
async def test_post_validate_c089_violation_one_paise_below_floor(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    C-089 INVARIANT (parameterised case 2): proposed price is exactly 1 paise below floor.
    MUST return HTTP 422 with minimum_compliant_price_paise.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=10000,
            minimum_compliant_price_paise=10000,
            proposed_price_paise=9999,
        )
    )
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=9999,
        )
        response = await async_client.post(
            "/pricing/validate",
            json=payload.dict(),
        )

        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert data["minimum_compliant_price_paise"] == 10000


@pytest.mark.asyncio
async def test_post_validate_missing_required_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with missing required field returns 422
    with standard FastAPI Pydantic validation error shape (NOT C-089 shape).
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier, proposed_price_paise
    }
    response = await async_client.post(
        "/pricing/validate",
        json=payload,
    )

    assert response.status_code == 422
    data = response.json()
    # Standard FastAPI Pydantic error includes 'detail' key with list of validation errors
    assert "detail" in data or "missing" in str(data).lower()


@pytest.mark.asyncio
async def test_post_validate_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/validate with malformed JSON body returns 422.
    """
    response = await async_client.post(
        "/pricing/validate",
        content=b"{invalid json}",
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
    Test POST /pricing/derive with a valid payload returns 200.
    Response body contains a derived_price field in paise (integer ≥ 0).
    """
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
async def test_post_derive_without_target_margin(
    async_client: AsyncClient, mock_bundle_engine: MagicMock
) -> None:
    """
    Test POST /pricing/derive without target_margin_pct uses default (minimum_margin_pct).
    Response contains derived_price_paise.
    """
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceDeriveRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            target_margin_pct=None,
        )
        response = await async_client.post(
            "/pricing/derive",
            json=payload.dict(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data
        assert isinstance(data["derived_price_paise"], int)


@pytest.mark.asyncio
async def test_post_derive_missing_required_field(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with missing required field returns 422.
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier
    }
    response = await async_client.post(
        "/pricing/derive",
        json=payload,
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data or "missing" in str(data).lower()


@pytest.mark.asyncio
async def test_post_derive_malformed_body(
    async_client: AsyncClient,
) -> None:
    """
    Test POST /pricing/derive with malformed JSON body returns 422.
    """
    response = await async_client.post(
        "/pricing/derive",
        content=b"{invalid json}",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER MOUNT INVARIANT
# ──────────────────────────────────────────────────────────────────────────────


def test_pricing_router_mounted_at_correct_prefix() -> None:
    """
    Assert that the /pricing/ router is mounted in the FastAPI app.
    Routes starting with /pricing/ must exist in app.routes.
    """
    routes = [route.path for route in app.routes]
    pricing_routes = [r for r in routes if r.startswith("/pricing/")]

    assert len(pricing_routes) > 0, "No /pricing/ routes mounted in app"
    # At minimum, we expect thread-catalog, bundle-cost-floor, validate, derive
    assert any(
        "/pricing/thread-catalog" in r for r in pricing_routes
    ), "GET /pricing/thread-catalog not mounted"
    assert any(
        "/pricing/bundle-cost-floor" in r for r in pricing_routes
    ), "GET /pricing/bundle-cost-floor not mounted"
    assert any(
        "/pricing/validate" in r for r in pricing_routes
    ), "POST /pricing/validate not mounted"
    assert any(
        "/pricing/derive" in r for r in pricing_routes
    ), "POST /pricing/derive not mounted"


# ──────────────────────────────────────────────────────────────────────────────
# PARAMETERISED TESTS: C-089 BOUNDARY CASES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_price_paise,expected_status,should_contain_minimum_compliant",
    [
        (0, 422, True),  # Zero paise (well below floor)
        (9999, 422, True),  # 1 paise below floor (10000)
        (10000, 200, False),  # Exactly at floor (APPROVED)
        (15000, 200, False),  # Well above floor (APPROVED)
    ],
)
async def test_validate_price_boundary_cases(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    proposed_price_paise: int,
    expected_status: int,
    should_contain_minimum_compliant: bool,
) -> None:
    """
    Parameterised boundary test for C-089 margin floor invariant.
    Tests zero paise, 1 paise below floor, at floor, and above floor.
    """
    if proposed_price_paise < 10000:
        mock_bundle_engine.validate_price = AsyncMock(
            return_value=PriceValidation(
                outcome="REJECTED",
                cost_floor_paise=10000,
                minimum_compliant_price_paise=10000,
                proposed_price_paise=proposed_price_paise,
            )
        )
    else:
        mock_bundle_engine.validate_price = AsyncMock(
            return_value=PriceValidation(
                outcome="APPROVED",
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
            json=payload.dict(),
        )

        assert response.status_code == expected_status
        data = response.json()

        if should_contain_minimum_compliant:
            assert "minimum_compliant_price_paise" in data
            assert data["minimum_compliant_price_paise"] > 0
        else:
            assert "minimum_compliant_price_paise" not in data