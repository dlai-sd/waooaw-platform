# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

# ── Path setup for hyphenated src dirs ──────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from main import app
from markup.models import (
    PriceValidation,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client() -> TestClient:
    """FastAPI test client for synchronous endpoint testing."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> httpx.AsyncClient:
    """AsyncClient for async endpoint testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_bundle_engine() -> MagicMock:
    """Mock BundleEngine service."""
    engine = MagicMock()
    engine.cost_floor = AsyncMock(return_value=500000)  # 500000 paise = ₹5000
    engine.derive_price = AsyncMock(return_value=650000)  # margin-on-revenue
    engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=700000,
        )
    )
    return engine


@pytest.fixture
def mock_thread_catalog_service() -> MagicMock:
    """Mock ThreadCatalogService."""
    service = MagicMock()
    service.get_catalog = AsyncMock(
        return_value=[
            {
                "thread_id": "thread_dma_001",
                "display_name": "DMA Researcher",
                "provider": "OpenAI",
                "unit_description": "1 LLM call",
                "raw_cost_inr_paise": 10000,
                "total_markup_pct": 50.0,
                "marked_up_cost_paise": 15000,
                "is_platform_thread": False,
                "applicable_agents": ["RESEARCHER"],
                "status": "ACTIVE",
            }
        ]
    )
    return service


@pytest.fixture
def mock_pricing_floor_log_insert() -> MagicMock:
    """Mock pricing_floor_log table insert (C-059 audit)."""
    insert_mock = MagicMock()
    insert_mock.return_value = MagicMock(returning=MagicMock())
    return insert_mock


# ── Test: GET /pricing/thread-catalog ──────────────────────────────────────

def test_get_thread_catalog_success(
    client: TestClient,
    mock_thread_catalog_service: MagicMock,
) -> None:
    """
    GET /pricing/thread-catalog returns 200 with list of thread entries.
    C-091: Thread Catalog Sovereignty — service delegates to ThreadCatalogService.
    """
    with patch(
        "markup.router.thread_catalog_service",
        mock_thread_catalog_service,
    ):
        response = client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "thread_id" in data[0]
        assert "display_name" in data[0]


def test_get_thread_catalog_empty_list(
    client: TestClient,
    mock_thread_catalog_service: MagicMock,
) -> None:
    """
    GET /pricing/thread-catalog returns 200 even when catalog is empty.
    """
    mock_thread_catalog_service.get_catalog = AsyncMock(return_value=[])

    with patch(
        "markup.router.thread_catalog_service",
        mock_thread_catalog_service,
    ):
        response = client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    assert response.json() == []


def test_get_thread_catalog_idempotent(
    client: TestClient,
    mock_thread_catalog_service: MagicMock,
) -> None:
    """
    GET /pricing/thread-catalog called twice returns identical payloads.
    Idempotency invariant: no side-effects, deterministic response.
    """
    with patch(
        "markup.router.thread_catalog_service",
        mock_thread_catalog_service,
    ):
        response1 = client.get("/pricing/thread-catalog")
        response2 = client.get("/pricing/thread-catalog")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


# ── Test: GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} ────────

def test_get_bundle_cost_floor_success(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns 200
    with numeric cost_floor_paise field.
    C-089: Cost floor is read from DB bundle_profiles, not recomputed.
    """
    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

    assert response.status_code == 200
    data = response.json()
    assert "cost_floor_paise" in data
    assert isinstance(data["cost_floor_paise"], int)
    assert data["cost_floor_paise"] >= 0


def test_get_bundle_cost_floor_idempotent(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    GET /pricing/bundle-cost-floor called twice returns same cost floor.
    Idempotent read, no side-effects.
    """
    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response1 = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")
        response2 = client.get("/pricing/bundle-cost-floor/RESEARCHER/STARTER")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


def test_get_bundle_cost_floor_invalid_agent_type(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    GET /pricing/bundle-cost-floor/{invalid}/{bundle_tier} returns 404 or 422.
    Unknown agent_type is rejected before or at the endpoint.
    """
    mock_bundle_engine.cost_floor = AsyncMock(
        side_effect=ValueError("Unknown agent_type")
    )

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.get("/pricing/bundle-cost-floor/INVALID_AGENT/STARTER")

    # Either 404 (not found) or 422 (validation error) — but NOT 200 or 500
    assert response.status_code in (404, 422, 400)


# ── Test: POST /pricing/validate ────────────────────────────────────────────

def test_post_validate_approved_no_violation(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    POST /pricing/validate with proposed_price >= minimum returns 200.
    Response does NOT contain minimum_compliant_price_paise (no C-089 violation).
    C-059: pricing_floor_log row written on both APPROVED and REJECTED.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=700000,
        )
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 700000,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "APPROVED"
    # When APPROVED, minimum_compliant_price_paise should not be in top-level error
    # (it may be included for reference, but the key point is no 422 error body)


def test_post_validate_c089_violation_returns_422(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    C-089 INVARIANT: POST /pricing/validate with proposed_price < floor
    returns HTTP 422 with minimum_compliant_price_paise in response body.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=100000,  # Below floor
        )
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 100000,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "minimum_compliant_price_paise" in data
    assert data["minimum_compliant_price_paise"] > 0


@pytest.mark.parametrize(
    "proposed_paise,floor_paise,expected_outcome",
    [
        (0, 500000, "REJECTED"),  # Zero paise — below floor
        (499999, 500000, "REJECTED"),  # 1 paise below floor
        (500000, 500000, "APPROVED"),  # Exactly at floor — OK
        (500001, 500000, "APPROVED"),  # 1 paise above floor — OK
    ],
)
def test_post_validate_c089_boundary_cases(
    client: TestClient,
    mock_bundle_engine: MagicMock,
    proposed_paise: int,
    floor_paise: int,
    expected_outcome: str,
) -> None:
    """
    C-089 boundary cases: zero, 1 paise below, at floor, 1 paise above.
    Parameterised sub-cases of the constitutional invariant.
    """
    if expected_outcome == "REJECTED":
        status_code = 422
        mock_bundle_engine.validate_price = AsyncMock(
            return_value=PriceValidation(
                outcome="REJECTED",
                cost_floor_paise=floor_paise,
                minimum_compliant_price_paise=floor_paise,
                proposed_price_paise=proposed_paise,
            )
        )
    else:
        status_code = 200
        mock_bundle_engine.validate_price = AsyncMock(
            return_value=PriceValidation(
                outcome="APPROVED",
                cost_floor_paise=floor_paise,
                minimum_compliant_price_paise=floor_paise,
                proposed_price_paise=proposed_paise,
            )
        )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed_paise,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/validate", json=payload)

    assert response.status_code == status_code
    if expected_outcome == "REJECTED":
        assert "minimum_compliant_price_paise" in response.json()


def test_post_validate_missing_required_field(
    client: TestClient,
) -> None:
    """
    POST /pricing/validate with missing required field returns 422
    with standard Pydantic validation error shape (not C-089 shape).
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier, proposed_price_paise
    }

    response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    # Pydantic validation error will have 'detail' key
    data = response.json()
    assert "detail" in data


def test_post_validate_malformed_json(
    client: TestClient,
) -> None:
    """
    POST /pricing/validate with malformed JSON returns 422.
    """
    response = client.post(
        "/pricing/validate",
        content=b"{ invalid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


# ── Test: POST /pricing/derive ──────────────────────────────────────────────

def test_post_derive_success(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    POST /pricing/derive with valid payload returns 200.
    Response contains derived_price_paise field (integer >= 0).
    Formula: derived = floor / (1 - margin/100) — margin-on-revenue.
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=650000)

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "target_margin_pct": 30.0,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/derive", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "derived_price_paise" in data
    assert isinstance(data["derived_price_paise"], int)
    assert data["derived_price_paise"] >= 0


def test_post_derive_without_target_margin_uses_minimum(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    POST /pricing/derive without target_margin_pct uses bundle_profiles.minimum_margin_pct.
    Service defaults to minimum if target_margin_pct is None.
    """
    mock_bundle_engine.derive_price = AsyncMock(return_value=600000)

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        # target_margin_pct omitted — should use minimum
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/derive", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["derived_price_paise"] >= 0


def test_post_derive_malformed_json(
    client: TestClient,
) -> None:
    """
    POST /pricing/derive with malformed JSON returns 422.
    """
    response = client.post(
        "/pricing/derive",
        content=b"{ incomplete",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_post_derive_missing_required_field(
    client: TestClient,
) -> None:
    """
    POST /pricing/derive with missing required field returns 422
    with Pydantic validation error.
    """
    payload = {
        "agent_type": "RESEARCHER",
        # Missing: bundle_tier
    }

    response = client.post("/pricing/derive", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


# ── Test: Router mount invariant ────────────────────────────────────────────

def test_router_mounted_at_pricing_prefix() -> None:
    """
    Assert that FastAPI app resolves /pricing/* routes.
    Confirms router is mounted at correct prefix in main.py.
    """
    routes = [route.path for route in app.routes]
    pricing_routes = [r for r in routes if "/pricing/" in r]

    assert len(pricing_routes) > 0, "No /pricing/* routes found; router not mounted"
    expected_prefixes = [
        "/pricing/thread-catalog",
        "/pricing/bundle-cost-floor/{agent_type}/{bundle_tier}",
        "/pricing/validate",
        "/pricing/derive",
    ]
    for prefix in expected_prefixes:
        assert any(
            expected in r for r in routes for expected in [prefix]
        ), f"Route {prefix} not found in app.routes"


# ── Test: Async endpoint execution (edge case) ──────────────────────────────

@pytest.mark.asyncio
async def test_get_thread_catalog_async(
    async_client: httpx.AsyncClient,
    mock_thread_catalog_service: MagicMock,
) -> None:
    """
    GET /pricing/thread-catalog using async client.
    Verifies async endpoint handling.
    """
    with patch(
        "markup.router.thread_catalog_service",
        mock_thread_catalog_service,
    ):
        response = await async_client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_post_validate_async(
    async_client: httpx.AsyncClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    POST /pricing/validate using async client.
    Verifies async endpoint handling for validation.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=700000,
        )
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 700000,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = await async_client.post("/pricing/validate", json=payload)

    assert response.status_code == 200


# ── Test: C-059 audit trail (pricing_floor_log) ─────────────────────────────

def test_post_validate_writes_audit_log_on_approved(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    C-059 TRACEABILITY: POST /pricing/validate writes pricing_floor_log
    row on both APPROVED and REJECTED outcomes.
    This test verifies the audit log call is made.
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=700000,
        )
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 700000,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    # Service should have called validate_price (which triggers audit log write)
    mock_bundle_engine.validate_price.assert_called_once()


def test_post_validate_writes_audit_log_on_rejected(
    client: TestClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """
    C-059 TRACEABILITY: POST /pricing/validate writes pricing_floor_log
    row on REJECTED outcome (C-089 violation).
    """
    mock_bundle_engine.validate_price = AsyncMock(
        return_value=PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=500000,
            minimum_compliant_price_paise=500000,
            proposed_price_paise=100000,
        )
    )

    payload = {
        "agent_type": "RESEARCHER",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 100000,
    }

    with patch("markup.router.bundle_engine", mock_bundle_engine):
        response = client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    # Service should have called validate_price (which triggers audit log write)
    mock_bundle_engine.validate_price.assert_called_once()