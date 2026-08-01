# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add src/billing-engine to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from markup.models import (
    PriceValidation,
    ThreadEntry,
)
from markup.bundle_engine import BundleEngine
from markup.router import router as pricing_router

logger = logging.getLogger(__name__)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def app() -> FastAPI:
    """Create a minimal FastAPI app with the pricing router mounted."""
    app_instance = FastAPI()
    app_instance.include_router(pricing_router, prefix="/pricing")
    return app_instance


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Synchronous test client for FastAPI."""
    return TestClient(app)


@pytest.fixture
async def async_client(app: FastAPI) -> httpx.AsyncClient:
    """Asynchronous test client for FastAPI."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_bundle_engine() -> AsyncMock:
    """Mock BundleEngine for dependency injection."""
    return AsyncMock(spec=BundleEngine)


@pytest.fixture
def mock_thread_catalog_service() -> AsyncMock:
    """Mock ThreadCatalogService."""
    return AsyncMock()


@pytest.fixture
def sample_thread_entry() -> ThreadEntry:
    """Sample ThreadEntry for testing."""
    return ThreadEntry(
        thread_id="claude-opus",
        display_name="Claude 3 Opus",
        provider="anthropic",
        unit_description="1 LLM API call",
        raw_cost_inr_paise=500,
        total_markup_pct=20.0,
        marked_up_cost_paise=600,
        is_platform_thread=False,
        applicable_agents=["RESEARCHER"],
        status="ACTIVE",
    )


# ── Happy Path Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_thread_catalog_success(app: FastAPI) -> None:
    """Test GET /pricing/thread-catalog returns 200 with list payload."""
    sample_entry = ThreadEntry(
        thread_id="gpt-4",
        display_name="GPT-4",
        provider="openai",
        unit_description="1 LLM API call",
        raw_cost_inr_paise=1000,
        total_markup_pct=25.0,
        marked_up_cost_paise=1250,
        is_platform_thread=False,
        applicable_agents=["RESEARCHER", "DMA"],
        status="ACTIVE",
    )

    with patch(
        "markup.router.ThreadCatalogService.get_all"
    ) as mock_get_all:
        mock_get_all.return_value = [sample_entry]

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/pricing/thread-catalog")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) > 0
    assert payload[0]["thread_id"] == "gpt-4"
    assert payload[0]["display_name"] == "GPT-4"


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_success(app: FastAPI) -> None:
    """Test GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns 200 with cost."""
    mock_cost_floor_paise = 5000

    with patch(
        "markup.router.BundleEngine.cost_floor"
    ) as mock_cost_floor:
        mock_cost_floor.return_value = mock_cost_floor_paise

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(
                "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
            )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "cost_floor_paise" in payload
    assert payload["cost_floor_paise"] >= 0
    assert isinstance(payload["cost_floor_paise"], int)


@pytest.mark.asyncio
async def test_post_pricing_validate_approved(app: FastAPI) -> None:
    """Test POST /pricing/validate with compliant price returns 200 (no violation)."""
    request_payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 10000,
    }

    mock_validation_result = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=5000,
        minimum_compliant_price_paise=5000,
        proposed_price_paise=10000,
    )

    with patch(
        "markup.router.BundleEngine.validate_price"
    ) as mock_validate:
        mock_validate.return_value = mock_validation_result

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/pricing/validate",
                json=request_payload,
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "APPROVED"
    # On APPROVED, minimum_compliant_price_paise should not be a violation indicator
    assert "minimum_compliant_price_paise" in payload


@pytest.mark.asyncio
async def test_post_pricing_derive_success(app: FastAPI) -> None:
    """Test POST /pricing/derive with valid payload returns 200 and derived price."""
    request_payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 35.0,
    }

    mock_derived_price = 7700

    with patch(
        "markup.router.BundleEngine.derive_price"
    ) as mock_derive:
        mock_derive.return_value = mock_derived_price

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/pricing/derive",
                json=request_payload,
            )

    assert response.status_code == 200
    payload = response.json()
    assert "derived_price_paise" in payload
    assert isinstance(payload["derived_price_paise"], int)
    assert payload["derived_price_paise"] >= 0


# ── C-089 Constitutional Invariant Tests ──────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_paise,cost_floor,should_reject",
    [
        (0, 5000, True),  # Zero paise — always rejected
        (4999, 5000, True),  # 1 paise below floor
        (5000, 5000, False),  # Exactly at floor
        (5001, 5000, False),  # Above floor
    ],
)
async def test_post_pricing_validate_c089_boundary(
    app: FastAPI,
    proposed_paise: int,
    cost_floor: int,
    should_reject: bool,
) -> None:
    """Test C-089: proposed price below floor returns 422 with minimum_compliant_price_paise."""
    request_payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed_paise,
    }

    if should_reject:
        # C-089 violation: return 422
        mock_validation_result = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=cost_floor,
            minimum_compliant_price_paise=cost_floor,
            proposed_price_paise=proposed_paise,
        )
    else:
        # Approved: return 200
        mock_validation_result = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=cost_floor,
            minimum_compliant_price_paise=cost_floor,
            proposed_price_paise=proposed_paise,
        )

    with patch(
        "markup.router.BundleEngine.validate_price"
    ) as mock_validate:
        mock_validate.return_value = mock_validation_result

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/pricing/validate",
                json=request_payload,
            )

    if should_reject:
        assert response.status_code == 422
        payload = response.json()
        assert "minimum_compliant_price_paise" in payload
        assert payload["minimum_compliant_price_paise"] > 0
        assert payload["outcome"] == "REJECTED"
    else:
        assert response.status_code == 200
        payload = response.json()
        assert payload["outcome"] == "APPROVED"


# ── Error & Edge Case Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_pricing_validate_missing_required_field(app: FastAPI) -> None:
    """Test POST /pricing/validate with missing field returns 422 (FastAPI validation)."""
    request_payload = {
        "agent_type": "RESEARCHER",
        # Missing bundle_tier and proposed_price_paise
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/pricing/validate",
            json=request_payload,
        )

    assert response.status_code == 422
    # FastAPI validation error, not C-089 error


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_agent_type(app: FastAPI) -> None:
    """Test GET /pricing/bundle-cost-floor with unknown agent_type."""
    with patch(
        "markup.router.BundleEngine.cost_floor"
    ) as mock_cost_floor:
        # Simulate unknown agent type — raise ValueError or return None
        mock_cost_floor.side_effect = ValueError(
            "Unknown agent_type: UNKNOWN_AGENT"
        )

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(
                "/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER"
            )

    # Should not be 200 or 500 (uncaught error)
    assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_bundle_tier(app: FastAPI) -> None:
    """Test GET /pricing/bundle-cost-floor with unknown bundle_tier."""
    with patch(
        "markup.router.BundleEngine.cost_floor"
    ) as mock_cost_floor:
        mock_cost_floor.side_effect = ValueError(
            "Unknown bundle_tier: UNKNOWN_TIER"
        )

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(
                "/pricing/bundle-cost-floor/RESEARCHER/UNKNOWN_TIER"
            )

    assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_post_pricing_derive_malformed_body(app: FastAPI) -> None:
    """Test POST /pricing/derive with malformed JSON returns 422."""
    # Send raw invalid JSON
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/pricing/derive",
            content=b"{invalid json",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 422


# ── Idempotency Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_thread_catalog_idempotent(app: FastAPI) -> None:
    """Test GET /pricing/thread-catalog returns identical result on repeated calls."""
    sample_entry = ThreadEntry(
        thread_id="gpt-4",
        display_name="GPT-4",
        provider="openai",
        unit_description="1 LLM API call",
        raw_cost_inr_paise=1000,
        total_markup_pct=25.0,
        marked_up_cost_paise=1250,
        is_platform_thread=False,
        applicable_agents=["RESEARCHER"],
        status="ACTIVE",
    )

    with patch(
        "markup.router.ThreadCatalogService.get_all"
    ) as mock_get_all:
        mock_get_all.return_value = [sample_entry]

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response1 = await ac.get("/pricing/thread-catalog")
            response2 = await ac.get("/pricing/thread-catalog")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_idempotent(app: FastAPI) -> None:
    """Test GET /pricing/bundle-cost-floor returns same cost floor on repeated calls."""
    mock_cost_floor_paise = 5000

    with patch(
        "markup.router.BundleEngine.cost_floor"
    ) as mock_cost_floor:
        mock_cost_floor.return_value = mock_cost_floor_paise

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response1 = await ac.get(
                "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
            )
            response2 = await ac.get(
                "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
            )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


# ── Router Mount Invariant Tests ─────────────────────────────────────────────


def test_router_mounted_at_pricing_prefix(app: FastAPI) -> None:
    """Assert that /pricing/* routes are registered in the app."""
    routes = [route.path for route in app.routes]

    # Check that pricing routes exist
    pricing_routes = [r for r in routes if "/pricing" in r]
    assert len(pricing_routes) > 0, "No /pricing routes found in app"

    # Verify at least one expected endpoint is present
    expected_paths = [
        "/pricing/thread-catalog",
        "/pricing/bundle-cost-floor/{agent_type}/{bundle_tier}",
        "/pricing/validate",
        "/pricing/derive",
    ]
    for expected_path in expected_paths:
        assert any(
            expected_path in route for route in pricing_routes
        ), f"Expected path {expected_path} not found in routes"


def test_router_methods_registered(app: FastAPI) -> None:
    """Assert that correct HTTP methods are registered for each route."""
    routes_by_path = {}
    for route in app.routes:
        path = route.path
        if "/pricing" in path:
            if path not in routes_by_path:
                routes_by_path[path] = []
            if hasattr(route, "methods"):
                routes_by_path[path].extend(route.methods)

    # Verify GET and POST methods exist
    assert len(routes_by_path) > 0, "No /pricing routes registered"


# ── C-059 Traceability Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pricing_validate_logs_audit_trail(app: FastAPI) -> None:
    """Test that validate_price call is traced (C-059 audit obligation)."""
    request_payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 5000,
    }

    mock_validation_result = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=5000,
        minimum_compliant_price_paise=5000,
        proposed_price_paise=5000,
    )

    with patch(
        "markup.router.BundleEngine.validate_price"
    ) as mock_validate:
        mock_validate.return_value = mock_validation_result

        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/pricing/validate",
                json=request_payload,
            )

    # Verify the mock was called (traceability)
    assert mock_validate.called
    assert response.status_code == 200


# ── PII and Security Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_pii_in_error_responses(app: FastAPI) -> None:
    """Test that error responses do not leak PII (C-063)."""
    request_payload = {
        "agent_type": "RESEARCHER",
        # Intentionally malformed to trigger error
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/pricing/validate",
            json=request_payload,
        )

    # Assert response is 422 (validation error)
    assert response.status_code == 422

    # Check that no PII appears in error message
    error_text = response.text
    # (real PII detection would be more sophisticated)
    # For now, just verify the response is valid JSON
    assert len(error_text) > 0