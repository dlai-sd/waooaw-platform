# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add src/billing-engine to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceValidation,
    PriceValidationOutcome,
)
from markup.router import router as markup_router
from markup.thread_catalog import ThreadCatalogEntry

logger = logging.getLogger(__name__)


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with the markup router mounted."""
    test_app = FastAPI()
    test_app.include_router(markup_router, prefix="/pricing")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """FastAPI TestClient for synchronous endpoint testing."""
    return TestClient(app)


@pytest.fixture
def async_client(app: FastAPI):
    """Async httpx client for testing."""
    async def _get_client():
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    return _get_client


@pytest.fixture
def mock_bundle_engine() -> AsyncMock:
    """Mock BundleEngine for dependency injection."""
    engine = AsyncMock(spec=BundleEngine)
    engine.cost_floor = AsyncMock(return_value=500000)  # 5000 INR in paise
    engine.derive_price = AsyncMock(return_value=1000000)  # 10000 INR in paise
    engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome=PriceValidationOutcome.APPROVED,
            cost_floor_paise=500000,
            minimum_compliant_price_paise=700000,
            proposed_price_paise=1000000,
        )
    )
    return engine


@pytest.fixture
def mock_thread_catalog_service() -> AsyncMock:
    """Mock ThreadCatalogService for get_all_entries."""
    service = AsyncMock()
    service.get_all_entries = AsyncMock(
        return_value=[
            ThreadCatalogEntry(
                thread_id="thread_001",
                display_name="GPT-4 Thread",
                provider="OpenAI",
                unit_description="per API call",
                raw_cost_inr_paise=100000,
                total_markup_pct=50.0,
                marked_up_cost_paise=150000,
                is_platform_thread=False,
                applicable_agents=["DMA", "RESEARCHER"],
                status="ACTIVE",
            )
        ]
    )
    return service


# ────────────────────────────────────────────────────────────────────────────
# HAPPY-PATH TESTS (one per endpoint)
# ────────────────────────────────────────────────────────────────────────────


def test_get_thread_catalog_200(
    client: TestClient, monkeypatch
) -> None:
    """GET /pricing/thread-catalog returns 200 with list of threads."""
    # Mock the ThreadCatalogService.get_all_entries
    mock_get_entries = AsyncMock(
        return_value=[
            ThreadCatalogEntry(
                thread_id="thread_001",
                display_name="GPT-4",
                provider="OpenAI",
                unit_description="per call",
                raw_cost_inr_paise=100000,
                total_markup_pct=50.0,
                marked_up_cost_paise=150000,
                is_platform_thread=False,
                applicable_agents=["DMA"],
                status="ACTIVE",
            )
        ]
    )

    # Patch at the router module level
    import sys
    mock_service = MagicMock()
    mock_service.get_all_entries = mock_get_entries
    monkeypatch.setitem(sys.modules, "markup.thread_catalog.ThreadCatalogService", mock_service)

    # Make the request
    response = client.get("/pricing/thread-catalog")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "thread_id" in data[0]
        assert "display_name" in data[0]


def test_get_bundle_cost_floor_200(
    client: TestClient, monkeypatch
) -> None:
    """GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns cost floor."""
    mock_engine = AsyncMock(spec=BundleEngine)
    mock_engine.cost_floor = AsyncMock(return_value=500000)

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    response = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

    assert response.status_code == 200
    data = response.json()
    # Expecting a field that represents cost_floor_paise
    assert isinstance(data, dict)
    # The router should return cost_floor_paise in response
    assert "cost_floor_paise" in data or "cost_floor" in data


def test_post_pricing_validate_200_approved(
    client: TestClient, monkeypatch
) -> None:
    """POST /pricing/validate with compliant price returns 200, no minimum_compliant_price_paise."""
    mock_engine = AsyncMock(spec=BundleEngine)
    mock_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome=PriceValidationOutcome.APPROVED,
            cost_floor_paise=500000,
            minimum_compliant_price_paise=700000,
            proposed_price_paise=1000000,
        )
    )

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 1000000,
    }
    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    # On APPROVED, minimum_compliant_price_paise should NOT be in response
    assert "minimum_compliant_price_paise" not in data
    assert data.get("outcome") == "APPROVED"


def test_post_pricing_derive_200(
    client: TestClient, monkeypatch
) -> None:
    """POST /pricing/derive returns 200 with derived price in paise."""
    mock_engine = AsyncMock(spec=BundleEngine)
    mock_engine.derive_price = AsyncMock(return_value=1000000)

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": None,
    }
    response = client.post("/pricing/derive", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "derived_price_paise" in data or "price_paise" in data
    price_value = data.get("derived_price_paise") or data.get("price_paise")
    assert isinstance(price_value, int)
    assert price_value >= 0


# ────────────────────────────────────────────────────────────────────────────
# CONSTITUTIONAL C-089 INVARIANT TESTS
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "proposed_paise,floor_paise,expected_status",
    [
        (1, 500000, 422),  # 1 paise below floor
        (0, 500000, 422),  # Zero paise
    ],
)
def test_post_pricing_validate_c089_violation(
    client: TestClient,
    monkeypatch,
    proposed_paise: int,
    floor_paise: int,
    expected_status: int,
) -> None:
    """
    POST /pricing/validate with price below floor returns 422 with minimum_compliant_price_paise.
    C-089: Margin Floor — never price below cost.
    """
    mock_engine = AsyncMock(spec=BundleEngine)
    minimum_compliant = int(floor_paise / (1 - 0.4))  # 40% margin

    mock_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome=PriceValidationOutcome.REJECTED,
            cost_floor_paise=floor_paise,
            minimum_compliant_price_paise=minimum_compliant,
            proposed_price_paise=proposed_paise,
        )
    )

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed_paise,
    }
    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == expected_status
    data = response.json()
    # C-089 invariant: REJECTED response MUST include minimum_compliant_price_paise
    assert "minimum_compliant_price_paise" in data
    assert isinstance(data["minimum_compliant_price_paise"], int)
    assert data["minimum_compliant_price_paise"] > 0


# ────────────────────────────────────────────────────────────────────────────
# ERROR / VALIDATION FAILURE TESTS
# ────────────────────────────────────────────────────────────────────────────


def test_post_pricing_validate_missing_required_field(
    client: TestClient,
) -> None:
    """POST /pricing/validate with missing required field returns 422."""
    # Missing proposed_price_paise
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
    }
    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    data = response.json()
    # Standard Pydantic validation error shape
    assert "detail" in data


def test_post_pricing_derive_malformed_body(
    client: TestClient,
) -> None:
    """POST /pricing/derive with malformed JSON returns 422."""
    response = client.post(
        "/pricing/derive",
        content="not valid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_get_bundle_cost_floor_unknown_agent_type(
    client: TestClient,
) -> None:
    """GET /pricing/bundle-cost-floor/{unknown_agent}/{tier} returns error (404 or 422)."""
    response = client.get("/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER")

    # Should not be 200 or 500
    assert response.status_code in [404, 422, 400]


def test_get_bundle_cost_floor_unknown_tier(
    client: TestClient,
) -> None:
    """GET /pricing/bundle-cost-floor/{agent}/{unknown_tier} returns error (404 or 422)."""
    response = client.get("/pricing/bundle-cost-floor/RESEARCHER/UNKNOWN_TIER")

    assert response.status_code in [404, 422, 400]


# ────────────────────────────────────────────────────────────────────────────
# IDEMPOTENCY INVARIANTS
# ────────────────────────────────────────────────────────────────────────────


def test_get_thread_catalog_idempotent(
    client: TestClient, monkeypatch
) -> None:
    """GET /pricing/thread-catalog called twice returns identical payload."""
    mock_entries = [
        ThreadCatalogEntry(
            thread_id="thread_001",
            display_name="GPT-4",
            provider="OpenAI",
            unit_description="per call",
            raw_cost_inr_paise=100000,
            total_markup_pct=50.0,
            marked_up_cost_paise=150000,
            is_platform_thread=False,
            applicable_agents=["DMA"],
            status="ACTIVE",
        )
    ]

    mock_get_entries = AsyncMock(return_value=mock_entries)
    mock_service = MagicMock()
    mock_service.get_all_entries = mock_get_entries
    monkeypatch.setitem(
        sys.modules, "markup.thread_catalog.ThreadCatalogService", mock_service
    )

    response1 = client.get("/pricing/thread-catalog")
    response2 = client.get("/pricing/thread-catalog")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


def test_get_bundle_cost_floor_idempotent(
    client: TestClient, monkeypatch
) -> None:
    """GET /pricing/bundle-cost-floor called twice returns same cost floor."""
    mock_engine = AsyncMock(spec=BundleEngine)
    mock_engine.cost_floor = AsyncMock(return_value=500000)

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    response1 = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
    response2 = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


# ────────────────────────────────────────────────────────────────────────────
# ROUTER-MOUNT INVARIANT
# ────────────────────────────────────────────────────────────────────────────


def test_router_mounted_at_pricing_prefix(app: FastAPI) -> None:
    """Assert that /pricing/ routes are registered in the app."""
    route_paths = {route.path for route in app.routes}

    # Check that /pricing routes exist
    pricing_routes = {p for p in route_paths if p.startswith("/pricing")}
    assert len(pricing_routes) > 0, "No /pricing routes found in app"

    # Verify at least the expected endpoints are present
    expected_paths = [
        "/pricing/thread-catalog",
        "/pricing/bundle-cost-floor/{agent_type}/{bundle_tier}",
        "/pricing/validate",
        "/pricing/derive",
    ]
    for expected_path in expected_paths:
        found = any(p == expected_path for p in route_paths)
        assert found, f"Expected route {expected_path} not found in app"


# ────────────────────────────────────────────────────────────────────────────
# ADDITIONAL EDGE CASES
# ────────────────────────────────────────────────────────────────────────────


def test_post_pricing_validate_zero_margin(
    client: TestClient, monkeypatch
) -> None:
    """POST /pricing/validate with zero target margin returns valid result."""
    mock_engine = AsyncMock(spec=BundleEngine)
    mock_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome=PriceValidationOutcome.APPROVED,
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=500000,
        )
    )

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 500000,
    }
    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data.get("outcome") == "APPROVED"


def test_post_pricing_derive_with_explicit_margin(
    client: TestClient, monkeypatch
) -> None:
    """POST /pricing/derive with explicit target_margin_pct uses provided margin."""
    mock_engine = AsyncMock(spec=BundleEngine)
    # formula: floor / (1 - margin/100)
    # floor=500000, margin=35% => 500000 / 0.65 ≈ 769230
    expected_price = 769230
    mock_engine.derive_price = AsyncMock(return_value=expected_price)

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 35.0,
    }
    response = client.post("/pricing/derive", json=payload)

    assert response.status_code == 200
    data = response.json()
    price_value = data.get("derived_price_paise") or data.get("price_paise")
    assert price_value == expected_price


def test_post_pricing_validate_large_paise_values(
    client: TestClient, monkeypatch
) -> None:
    """POST /pricing/validate handles large paise values (e.g., 1 crore INR)."""
    # 1 crore INR = 100,000,000 paise
    large_floor = 100000000
    large_price = 150000000
    large_minimum = 140000000

    mock_engine = AsyncMock(spec=BundleEngine)
    mock_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome=PriceValidationOutcome.APPROVED,
            cost_floor_paise=large_floor,
            minimum_compliant_price_paise=large_minimum,
            proposed_price_paise=large_price,
        )
    )

    monkeypatch.setattr(
        "markup.router.BundleEngine",
        lambda: mock_engine,
        raising=False,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": large_price,
    }
    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data.get("outcome") == "APPROVED"


def test_get_thread_catalog_empty_list(
    client: TestClient, monkeypatch
) -> None:
    """GET /pricing/thread-catalog returns 200 with empty list if no threads."""
    mock_get_entries = AsyncMock(return_value=[])
    mock_service = MagicMock()
    mock_service.get_all_entries = mock_get_entries
    monkeypatch.setitem(
        sys.modules, "markup.thread_catalog.ThreadCatalogService", mock_service
    )

    response = client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0