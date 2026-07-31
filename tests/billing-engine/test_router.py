# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

logger = logging.getLogger(__name__)


@pytest.fixture
async def client():
    """
    FastAPI test client fixture.
    Imports app from main; mounts markup router.
    """
    from main import app
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_thread_catalog_service(monkeypatch):
    """
    Mock ThreadCatalogService to avoid DB/Redis calls.
    """
    mock_svc = AsyncMock()
    mock_svc.list_all = AsyncMock(
        return_value=[
            {
                "thread_id": "thread_001",
                "display_name": "GPT-4 Turbo",
                "provider": "OpenAI",
                "unit_description": "1 API call",
                "raw_cost_inr_paise": 100,
                "total_markup_pct": 25.0,
                "marked_up_cost_paise": 125,
                "is_platform_thread": False,
                "applicable_agents": ["RESEARCHER", "DMA"],
                "status": "ACTIVE",
            }
        ]
    )
    # Patch the service in the router module scope
    monkeypatch.setattr(
        "markup.router.ThreadCatalogService",
        MagicMock(return_value=mock_svc),
    )
    return mock_svc


@pytest.fixture
def mock_bundle_engine(monkeypatch):
    """
    Mock BundleEngine to avoid DB calls.
    """
    mock_engine = AsyncMock()
    mock_engine.cost_floor = AsyncMock(return_value=5000)  # 50 INR in paise
    mock_engine.derive_price = AsyncMock(return_value=7500)  # derived price
    mock_engine.validate_price = AsyncMock(
        return_value={
            "outcome": "APPROVED",
            "cost_floor_paise": 5000,
            "minimum_compliant_price_paise": 5000,
            "proposed_price_paise": 7500,
        }
    )
    monkeypatch.setattr(
        "markup.router.BundleEngine",
        MagicMock(return_value=mock_engine),
    )
    return mock_engine


@pytest.mark.asyncio
async def test_get_thread_catalog_happy_path(client, mock_thread_catalog_service):
    """
    GET /pricing/thread-catalog → 200, response is a list.
    Assert ThreadCatalogService delegate was called.
    """
    response = await client.get("/pricing/thread-catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["thread_id"] == "thread_001"
    mock_thread_catalog_service.list_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_thread_catalog_empty(client, monkeypatch):
    """
    GET /pricing/thread-catalog with empty catalog → 200, empty list.
    """
    mock_svc = AsyncMock()
    mock_svc.list_all = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "markup.router.ThreadCatalogService",
        MagicMock(return_value=mock_svc),
    )
    response = await client.get("/pricing/thread-catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_happy_path(client, mock_bundle_engine):
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} → 200.
    Response contains numeric cost_floor_paise field.
    """
    response = await client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "cost_floor_paise" in data
    assert isinstance(data["cost_floor_paise"], int)
    assert data["cost_floor_paise"] >= 0
    mock_bundle_engine.cost_floor.assert_called_once_with("RESEARCHER", "STARTER")


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_idempotent(client, mock_bundle_engine):
    """
    GET /pricing/bundle-cost-floor called twice → same response.
    Idempotency: read-only, no side-effects.
    """
    response1 = await client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
    response2 = await client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_post_validate_price_approved(client, mock_bundle_engine):
    """
    POST /pricing/validate with valid price → 200, no minimum_compliant_price_paise key.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 7500,
    }
    response = await client.post("/pricing/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "APPROVED"
    # When approved, minimum_compliant_price_paise is optional in response
    assert "cost_floor_paise" in data
    mock_bundle_engine.validate_price.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_price_paise,expected_minimum",
    [
        (0, 5000),  # Zero paise — below floor
        (4999, 5000),  # 1 paise below floor
    ],
)
async def test_post_validate_price_c089_violation(
    client, mock_bundle_engine, proposed_price_paise, expected_minimum
):
    """
    POST /pricing/validate with price below C-089 minimum → 422.
    Response body MUST include minimum_compliant_price_paise.
    """
    # Mock the engine to return REJECTED outcome
    mock_bundle_engine.validate_price = AsyncMock(
        return_value={
            "outcome": "REJECTED",
            "cost_floor_paise": 5000,
            "minimum_compliant_price_paise": expected_minimum,
            "proposed_price_paise": proposed_price_paise,
        }
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed_price_paise,
    }
    response = await client.post("/pricing/validate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "minimum_compliant_price_paise" in data
    assert isinstance(data["minimum_compliant_price_paise"], int)
    assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_validate_price_missing_field(client):
    """
    POST /pricing/validate with missing required field → 422 validation error.
    FastAPI Pydantic error, NOT C-089 shape.
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing bundle_tier and proposed_price_paise
    }
    response = await client.post("/pricing/validate", json=payload)
    assert response.status_code == 422
    # Standard Pydantic validation error, not custom C-089 response


@pytest.mark.asyncio
async def test_post_derive_price_happy_path(client, mock_bundle_engine):
    """
    POST /pricing/derive with valid payload → 200, derived_price_paise field.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 30.0,
    }
    response = await client.post("/pricing/derive", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "derived_price_paise" in data
    assert isinstance(data["derived_price_paise"], int)
    assert data["derived_price_paise"] >= 0
    mock_bundle_engine.derive_price.assert_called_once()


@pytest.mark.asyncio
async def test_post_derive_price_without_target_margin(client, mock_bundle_engine):
    """
    POST /pricing/derive without target_margin_pct → 200.
    Engine uses default margin from bundle_profiles.minimum_margin_pct.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
    }
    response = await client.post("/pricing/derive", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "derived_price_paise" in data
    assert isinstance(data["derived_price_paise"], int)


@pytest.mark.asyncio
async def test_post_derive_price_malformed_body(client):
    """
    POST /pricing/derive with malformed JSON → 422 (or 400).
    """
    # Send invalid JSON structure
    response = await client.post(
        "/pricing/derive",
        json={"invalid_key": "value"},
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_agent_type(client, mock_bundle_engine):
    """
    GET /pricing/bundle-cost-floor with unknown agent_type → 404 or 422.
    Assert status is not 200 or 500.
    """
    # Mock engine to raise ValueError or return None
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown agent_type")
    )

    response = await client.get("/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER")
    assert response.status_code != 200
    assert response.status_code != 500
    assert response.status_code in (404, 422, 400)


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_bundle_tier(client, mock_bundle_engine):
    """
    GET /pricing/bundle-cost-floor with unknown bundle_tier → 404 or 422.
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown bundle_tier")
    )

    response = await client.get("/pricing/bundle-cost-floor/RESEARCHER/UNKNOWN_TIER")
    assert response.status_code != 200
    assert response.status_code != 500
    assert response.status_code in (404, 422, 400)


@pytest.mark.asyncio
async def test_router_mounted_at_pricing_prefix(client):
    """
    Assert /pricing/* routes are mounted correctly in app.routes.
    """
    # Try hitting a known endpoint; if 404, router is not mounted
    response = await client.get("/pricing/thread-catalog")
    # Should either be 200 (success) or 500 (internal error), NOT 404 (not found)
    assert response.status_code != 404, "Pricing router not mounted at /pricing prefix"


@pytest.mark.asyncio
async def test_validate_price_idempotent_inputs(client, mock_bundle_engine):
    """
    POST /pricing/validate called twice with identical payload → identical response.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 7500,
    }
    response1 = await client.post("/pricing/validate", json=payload)
    response2 = await client.post("/pricing/validate", json=payload)
    assert response1.status_code == response2.status_code
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_derive_price_idempotent_inputs(client, mock_bundle_engine):
    """
    POST /pricing/derive called twice with identical payload → identical response.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 30.0,
    }
    response1 = await client.post("/pricing/derive", json=payload)
    response2 = await client.post("/pricing/derive", json=payload)
    assert response1.status_code == response2.status_code
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_validate_price_rejected_outcome(client, mock_bundle_engine):
    """
    POST /pricing/validate with REJECTED outcome → 422, includes minimum_compliant_price_paise.
    C-089 constitutional gate enforcement.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value={
            "outcome": "REJECTED",
            "cost_floor_paise": 10000,
            "minimum_compliant_price_paise": 10000,
            "proposed_price_paise": 5000,
        }
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 5000,
    }
    response = await client.post("/pricing/validate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["outcome"] == "REJECTED"
    assert data["minimum_compliant_price_paise"] == 10000


@pytest.mark.asyncio
async def test_derive_price_margin_on_revenue_formula(client, mock_bundle_engine):
    """
    POST /pricing/derive validates the margin-on-revenue formula.
    Given cost_floor = 5000, margin = 30%, derived = 5000 / (1 - 0.30) ≈ 7143.
    Mock returns this to verify endpoint passes it through correctly.
    """
    # Expected: 5000 / (1 - 0.30) = 5000 / 0.70 ≈ 7143 paise
    expected_derived = 7143
    mock_bundle_engine.derive_price = AsyncMock(return_value=expected_derived)

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 30.0,
    }
    response = await client.post("/pricing/derive", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["derived_price_paise"] == expected_derived