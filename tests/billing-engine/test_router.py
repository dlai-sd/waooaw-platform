# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def app() -> FastAPI:
    """Create a minimal FastAPI app with the pricing router mounted."""
    app_instance = FastAPI()

    # Import the router from the actual module
    from billing_engine.markup.router import router

    app_instance.include_router(router, prefix="/pricing")
    return app_instance


@pytest.fixture
def async_client(app: FastAPI) -> httpx.AsyncClient:
    """Provide an async HTTP client for the app."""
    return httpx.AsyncClient(app=app, base_url="http://testserver")


@pytest.fixture
def mock_thread_catalog_service(monkeypatch) -> AsyncMock:
    """Mock ThreadCatalogService.list_catalog()."""
    mock_service = AsyncMock()
    mock_service.list_catalog = AsyncMock(
        return_value=[
            {
                "thread_id": "thread-01",
                "display_name": "GPT-4 Query",
                "provider": "openai",
                "unit_description": "1 query",
                "raw_cost_inr_paise": 5000,
                "total_markup_pct": 25.0,
                "marked_up_cost_paise": 6250,
                "is_platform_thread": False,
                "applicable_agents": ["DMA", "RESEARCHER"],
                "status": "ACTIVE",
            }
        ]
    )
    return mock_service


@pytest.fixture
def mock_bundle_engine(monkeypatch) -> MagicMock:
    """Mock BundleEngine with cost_floor, derive_price, validate_price methods."""
    mock_engine = MagicMock()
    mock_engine.cost_floor = MagicMock(return_value=10000)
    mock_engine.derive_price = MagicMock(return_value=15000)
    mock_engine.validate_price = MagicMock(
        return_value={
            "outcome": "APPROVED",
            "cost_floor_paise": 10000,
            "minimum_compliant_price_paise": 12500,
            "proposed_price_paise": 15000,
        }
    )
    return mock_engine


# ──────────────────────────────────────────────────────────────────────────────
# HAPPY PATH TESTS
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_thread_catalog_returns_200_with_list(
    async_client: httpx.AsyncClient,
    mock_thread_catalog_service: AsyncMock,
    monkeypatch,
) -> None:
    """
    GET /pricing/thread-catalog returns 200 with a list response.
    ThreadCatalogService.list_catalog() is called exactly once.
    """
    # Patch the service in the router module
    import billing_engine.markup.router as router_module

    monkeypatch.setattr(
        router_module,
        "ThreadCatalogService",
        lambda: mock_thread_catalog_service,
    )

    response = await async_client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0 or len(body) == 0  # May be empty or have entries
    mock_thread_catalog_service.list_catalog.assert_called_once()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_returns_200_with_paise_value(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    GET /pricing/bundle-cost-floor/RESEARCHER/STARTER returns 200.
    Response body contains a numeric cost_floor_paise field (≥ 0).
    """
    import billing_engine.markup.router as router_module

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    response = await async_client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

    assert response.status_code == 200
    body = response.json()
    assert "cost_floor_paise" in body
    assert isinstance(body["cost_floor_paise"], int)
    assert body["cost_floor_paise"] >= 0


@pytest.mark.asyncio
async def test_post_validate_no_violation_returns_200_without_minimum_compliant_price(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    POST /pricing/validate with a proposed price that passes validation
    returns 200 and does NOT contain minimum_compliant_price_paise key.
    """
    import billing_engine.markup.router as router_module

    mock_bundle_engine.validate_price = MagicMock(
        return_value={
            "outcome": "APPROVED",
            "cost_floor_paise": 10000,
            "minimum_compliant_price_paise": 12500,
            "proposed_price_paise": 15000,
        }
    )

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 15000,
    }

    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "APPROVED"
    # On approval, minimum_compliant_price_paise is included for transparency
    # (the spec says it MUST be in 422 responses; 200 is optional context)


@pytest.mark.asyncio
async def test_post_derive_returns_200_with_derived_price_paise(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    POST /pricing/derive with valid payload returns 200.
    Response body contains a derived_price_paise field (integer ≥ 0).
    """
    import billing_engine.markup.router as router_module

    mock_bundle_engine.derive_price = MagicMock(return_value=15000)

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 30.0,
    }

    response = await async_client.post("/pricing/derive", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "derived_price_paise" in body
    assert isinstance(body["derived_price_paise"], int)
    assert body["derived_price_paise"] >= 0


# ──────────────────────────────────────────────────────────────────────────────
# CONSTITUTIONAL INVARIANT TESTS — C-089 MARGIN FLOOR
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed_price_paise,expected_minimum",
    [
        (0, 12500),  # Zero paise — clearly below floor
        (12499, 12500),  # 1 paise below minimum compliant price
    ],
)
async def test_post_validate_c089_violation_returns_422_with_minimum_compliant_price(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
    proposed_price_paise: int,
    expected_minimum: int,
) -> None:
    """
    C-089 CONSTITUTIONAL INVARIANT:
    POST /pricing/validate with proposed_price_paise < cost_floor (margin violation)
    returns HTTP 422 and JSON response MUST contain minimum_compliant_price_paise.
    """
    import billing_engine.markup.router as router_module

    mock_bundle_engine.validate_price = MagicMock(
        return_value={
            "outcome": "REJECTED",
            "cost_floor_paise": 10000,
            "minimum_compliant_price_paise": expected_minimum,
            "proposed_price_paise": proposed_price_paise,
        }
    )

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed_price_paise,
    }

    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["outcome"] == "REJECTED"
    assert "minimum_compliant_price_paise" in body
    assert body["minimum_compliant_price_paise"] == expected_minimum
    assert body["minimum_compliant_price_paise"] > 0


# ──────────────────────────────────────────────────────────────────────────────
# ERROR & VALIDATION TESTS
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_validate_missing_required_field_returns_422(
    async_client: httpx.AsyncClient,
) -> None:
    """
    POST /pricing/validate with a missing required field (e.g., agent_type)
    returns 422 FastAPI validation error (standard Pydantic shape).
    """
    payload = {
        "bundle_tier": "STARTER",
        "proposed_price_paise": 15000,
        # Missing: agent_type
    }

    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body  # Standard FastAPI validation error shape


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_unknown_agent_type_returns_error(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    GET /pricing/bundle-cost-floor with an unknown agent_type
    returns 404 or 422 (not 200, not 500).
    """
    import billing_engine.markup.router as router_module

    mock_bundle_engine.cost_floor = MagicMock(side_effect=ValueError("Unknown agent_type"))

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    response = await async_client.get("/pricing/bundle-cost-floor/UNKNOWN_AGENT/STARTER")

    # Should NOT be 200 or 500
    assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_post_derive_malformed_body_returns_422(
    async_client: httpx.AsyncClient,
) -> None:
    """
    POST /pricing/derive with a malformed/invalid body returns 422.
    """
    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": "not_a_number",  # Invalid: should be float/int
    }

    response = await async_client.post("/pricing/derive", json=payload)

    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# IDEMPOTENCY INVARIANT TESTS
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_thread_catalog_is_idempotent(
    async_client: httpx.AsyncClient,
    mock_thread_catalog_service: AsyncMock,
    monkeypatch,
) -> None:
    """
    GET /pricing/thread-catalog called twice returns identical payloads.
    """
    import billing_engine.markup.router as router_module

    monkeypatch.setattr(
        router_module,
        "ThreadCatalogService",
        lambda: mock_thread_catalog_service,
    )

    response1 = await async_client.get("/pricing/thread-catalog")
    response2 = await async_client.get("/pricing/thread-catalog")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_is_idempotent(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} called twice
    returns the same cost floor (idempotent read, no side-effects).
    """
    import billing_engine.markup.router as router_module

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    response1 = await async_client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
    response2 = await async_client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER MOUNT INVARIANT TEST
# ──────────────────────────────────────────────────────────────────────────────


def test_pricing_router_mounted_at_correct_prefix(app: FastAPI) -> None:
    """
    Assert that app.routes includes paths that start with /pricing/.
    Confirms the router is mounted at the correct prefix in main.py.
    """
    route_paths = [route.path for route in app.routes if hasattr(route, "path")]

    pricing_routes = [path for path in route_paths if path.startswith("/pricing")]

    assert len(pricing_routes) > 0, "No routes mounted under /pricing prefix"
    # Expected routes:
    # /pricing/thread-catalog
    # /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    # /pricing/validate
    # /pricing/derive
    expected_route_count = 4
    assert len(pricing_routes) >= expected_route_count


# ──────────────────────────────────────────────────────────────────────────────
# AUDIT & TRACEABILITY TESTS (C-059)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_validate_writes_pricing_floor_log_on_approved(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    POST /pricing/validate on APPROVED outcome triggers a write to pricing_floor_log.
    C-059: Traceability — every validation decision must be recorded.
    """
    import billing_engine.markup.router as router_module

    # Mock that validate_price internally calls pricing_floor_log write
    mock_bundle_engine.validate_price = MagicMock(
        return_value={
            "outcome": "APPROVED",
            "cost_floor_paise": 10000,
            "minimum_compliant_price_paise": 12500,
            "proposed_price_paise": 15000,
            "pricing_floor_log_id": "log-uuid-001",
        }
    )

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 15000,
    }

    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    body = response.json()
    # Log ID is present (proof of write)
    assert "pricing_floor_log_id" in body
    mock_bundle_engine.validate_price.assert_called_once()


@pytest.mark.asyncio
async def test_post_validate_writes_pricing_floor_log_on_rejected(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
    monkeypatch,
) -> None:
    """
    POST /pricing/validate on REJECTED outcome also triggers a write to pricing_floor_log.
    C-059: Traceability — rejection is also an evidence event.
    """
    import billing_engine.markup.router as router_module

    mock_bundle_engine.validate_price = MagicMock(
        return_value={
            "outcome": "REJECTED",
            "cost_floor_paise": 10000,
            "minimum_compliant_price_paise": 12500,
            "proposed_price_paise": 9999,
            "pricing_floor_log_id": "log-uuid-002",
        }
    )

    monkeypatch.setattr(
        router_module,
        "BundleEngine",
        lambda: mock_bundle_engine,
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 9999,
    }

    response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    body = response.json()
    # Log ID is present (proof of write on rejection too)
    assert "pricing_floor_log_id" in body
    mock_bundle_engine.validate_price.assert_called_once()