# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import sys
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add src/billing-engine to path for imports
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent / "src" / "billing-engine"),
)

from markup.router import router as pricing_router
from markup.models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    ThreadEntry,
)

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with pricing router mounted."""
    test_app = FastAPI()
    test_app.include_router(pricing_router, prefix="/pricing")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_bundle_engine() -> AsyncMock:
    """Mock BundleEngine for dependency injection."""
    engine = AsyncMock()
    engine.cost_floor = MagicMock(return_value=500000)  # 5000 INR in paise
    engine.derive_price = MagicMock(return_value=750000)  # 7500 INR in paise
    engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=600000,
            proposed_price_paise=750000,
        )
    )
    return engine


@pytest.fixture
def mock_thread_catalog_service() -> AsyncMock:
    """Mock ThreadCatalogService for thread catalog endpoint."""
    service = AsyncMock()
    service.get_full_catalog = AsyncMock(
        return_value=[
            ThreadEntry(
                thread_id="gpt-4",
                display_name="GPT-4 (OpenAI)",
                provider="openai",
                unit_description="1 API call",
                raw_cost_inr_paise=100000,
                total_markup_pct=25.0,
                marked_up_cost_paise=125000,
                is_platform_thread=False,
                applicable_agents=["RESEARCHER", "DMA"],
                status="ACTIVE",
            ),
            ThreadEntry(
                thread_id="ollama-llama2",
                display_name="Llama 2 (Local)",
                provider="ollama",
                unit_description="1 inference",
                raw_cost_inr_paise=0,
                total_markup_pct=0.0,
                marked_up_cost_paise=0,
                is_platform_thread=True,
                applicable_agents=["RESEARCHER", "DMA", "AGENT_X"],
                status="ACTIVE",
            ),
        ]
    )
    return service


# ────────────────────────────────────────────────────────────────────────────
# HAPPY-PATH TESTS (one per endpoint)
# ────────────────────────────────────────────────────────────────────────────


def test_get_thread_catalog(
    client: TestClient, mock_thread_catalog_service: AsyncMock
) -> None:
    """Test GET /pricing/thread-catalog returns 200 with list of entries."""
    with patch(
        "markup.router.ThreadCatalogService", return_value=mock_thread_catalog_service
    ):
        response = client.get("/pricing/thread-catalog")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["thread_id"] == "gpt-4"
        assert data[1]["thread_id"] == "ollama-llama2"
        mock_thread_catalog_service.get_full_catalog.assert_called_once()


def test_get_thread_catalog_empty(client: TestClient) -> None:
    """Test GET /pricing/thread-catalog with empty catalog."""
    mock_service = AsyncMock()
    mock_service.get_full_catalog = AsyncMock(return_value=[])

    with patch(
        "markup.router.ThreadCatalogService", return_value=mock_service
    ):
        response = client.get("/pricing/thread-catalog")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


def test_get_bundle_cost_floor(client: TestClient, mock_bundle_engine: AsyncMock) -> None:
    """Test GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns 200 with cost."""
    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

        assert response.status_code == 200
        data = response.json()
        assert "cost_floor_paise" in data
        assert isinstance(data["cost_floor_paise"], int)
        assert data["cost_floor_paise"] >= 0
        mock_bundle_engine.cost_floor.assert_called_once_with("RESEARCHER", "STARTER")


def test_post_pricing_validate_approved(
    client: TestClient, mock_bundle_engine: AsyncMock
) -> None:
    """Test POST /pricing/validate with compliant price returns 200 without minimum_compliant_price_paise."""
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=600000,
            proposed_price_paise=750000,
        )
    )

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=750000,
        )
        response = client.post(
            "/pricing/validate",
            json=payload.model_dump(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "APPROVED"
        # On APPROVED, minimum_compliant_price_paise should NOT be present in response
        assert "minimum_compliant_price_paise" not in data or data.get(
            "minimum_compliant_price_paise"
        ) is None


def test_post_pricing_derive(
    client: TestClient, mock_bundle_engine: AsyncMock
) -> None:
    """Test POST /pricing/derive returns 200 with derived price."""
    mock_bundle_engine.derive_price = MagicMock(return_value=750000)

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceDeriveRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            target_margin_pct=33.33,
        )
        response = client.post(
            "/pricing/derive",
            json=payload.model_dump(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data or "price_paise" in data
        price_field = data.get("derived_price_paise") or data.get("price_paise")
        assert isinstance(price_field, int)
        assert price_field >= 0


# ────────────────────────────────────────────────────────────────────────────
# C-089 CONSTITUTIONAL INVARIANT TESTS
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "proposed_price_paise,floor_paise",
    [
        (0, 500000),  # Zero paise violation
        (499999, 500000),  # 1 paise below floor
    ],
)
def test_post_pricing_validate_c089_violation(
    client: TestClient,
    mock_bundle_engine: AsyncMock,
    proposed_price_paise: int,
    floor_paise: int,
) -> None:
    """Test POST /pricing/validate with price below C-089 floor returns 422 with minimum_compliant_price_paise."""
    minimum_compliant = floor_paise
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=floor_paise,
            minimum_compliant_price_paise=minimum_compliant,
            proposed_price_paise=proposed_price_paise,
        )
    )

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        payload = PriceValidationRequest(
            agent_type="RESEARCHER",
            bundle_tier="STARTER",
            proposed_price_paise=proposed_price_paise,
        )
        response = client.post(
            "/pricing/validate",
            json=payload.model_dump(),
        )

        # C-089: must return 422 and include minimum_compliant_price_paise
        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert isinstance(data["minimum_compliant_price_paise"], int)
        assert data["minimum_compliant_price_paise"] > 0


# ────────────────────────────────────────────────────────────────────────────
# ERROR / VALIDATION TESTS
# ────────────────────────────────────────────────────────────────────────────


def test_post_pricing_validate_missing_required_field(client: TestClient) -> None:
    """Test POST /pricing/validate with missing required field returns 422."""
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier
        "proposed_price_paise": 750000,
    }
    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    # Standard Pydantic validation error, not C-089 shape
    data = response.json()
    assert "detail" in data or "error" in data.get("errors", [{}])[0]


def test_post_pricing_validate_malformed_json(client: TestClient) -> None:
    """Test POST /pricing/validate with malformed JSON returns 422."""
    response = client.post(
        "/pricing/validate",
        content="{invalid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_get_bundle_cost_floor_unknown_agent_type(
    client: TestClient, mock_bundle_engine: AsyncMock
) -> None:
    """Test GET /pricing/bundle-cost-floor with unknown agent_type returns 404 or 422."""
    mock_bundle_engine.cost_floor = MagicMock(
        side_effect=ValueError("Unknown agent type: INVALID_AGENT")
    )

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = client.get("/pricing/bundle-cost-floor/INVALID_AGENT/STARTER")

        # Should not be 200 or 500
        assert response.status_code in (404, 422, 400)


def test_get_bundle_cost_floor_unknown_bundle_tier(
    client: TestClient, mock_bundle_engine: AsyncMock
) -> None:
    """Test GET /pricing/bundle-cost-floor with unknown bundle_tier returns 404 or 422."""
    mock_bundle_engine.cost_floor = MagicMock(
        side_effect=ValueError("Unknown bundle tier: INVALID_TIER")
    )

    with patch("markup.router.BundleEngine", return_value=mock_bundle_engine):
        response = client.get("/pricing/bundle-cost-floor/RESEARCHER/INVALID_TIER")

        # Should not be 200 or 500
        assert response.status_code in (404, 422, 400)


def test_post_pricing_derive_missing_required_field(client: TestClient) -> None:
    """Test POST /pricing/derive with missing required field returns 422."""
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier
        "target_margin_pct": 33.33,
    }
    response = client.post("/pricing/derive", json=payload)

    assert response.status_code == 422


def test_post_pricing_derive_malformed_json(client: TestClient) -> None:
    """Test POST /pricing/derive with malformed JSON returns 422."""
    response = client.post(
        "/pricing/derive",
        content="{broken json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────────
# IDEMPOTENCY INVARIANT TESTS
# ────────────────────────────────────────────────────────────────────────────


def test_get_thread_catalog_idempotent(
    client: TestClient, mock_thread_catalog_service: AsyncMock
) -> None:
    """Test GET /pricing/thread-catalog idempotency — same response on repeated calls."""
    mock_service = AsyncMock()
    mock_service.get_full_catalog = AsyncMock(
        return_value=[
            ThreadEntry(
                thread_id="gpt-4",
                display_name="GPT-4",
                provider="openai",
                unit_description="1 call",
                raw_cost_inr_paise=100000,
                total_markup_pct=25.0,
                marked_up_cost_paise=125000,
                is_platform_thread=False,
                applicable_agents=["RESEARCHER"],
                status="ACTIVE",
            ),
        ]
    )

    with patch("markup.router.ThreadCatalogService", return_value=mock_service):
        response1 = client.get("/pricing/thread-catalog")
        response2 = client.get("/pricing/thread-catalog")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


def test_get_bundle_cost_floor_idempotent(
    client: TestClient, mock_bundle_engine: AsyncMock
) -> None:
    """Test GET /pricing/bundle-cost-floor idempotency — same cost on repeated calls."""
    mock_engine = AsyncMock()
    mock_engine.cost_floor = MagicMock(return_value=500000)

    with patch("markup.router.BundleEngine", return_value=mock_engine):
        response1 = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
        response2 = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


# ────────────────────────────────────────────────────────────────────────────
# ROUTER MOUNT INVARIANT TEST
# ────────────────────────────────────────────────────────────────────────────


def test_pricing_router_mounted_at_correct_prefix(app: FastAPI) -> None:
    """Test that pricing router is mounted at /pricing prefix in app."""
    # Collect all route paths
    route_paths = []
    for route in app.routes:
        if hasattr(route, "path"):
            route_paths.append(route.path)

    # Assert routes start with /pricing
    pricing_routes = [path for path in route_paths if path.startswith("/pricing")]
    assert len(pricing_routes) > 0, "No routes mounted with /pricing prefix"

    # Check for at least the core endpoints
    " ".join(pricing_routes)
    assert any(
        "thread-catalog" in path for path in pricing_routes
    ), "/pricing/thread-catalog not mounted"