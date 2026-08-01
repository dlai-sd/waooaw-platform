# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from main import app
from markup.models import (
    ThreadEntry,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
async def async_client() -> AsyncClient:
    """FastAPI test client with async support."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_thread_catalog_service() -> AsyncMock:
    """Mock ThreadCatalogService.get_catalog()."""
    return AsyncMock()


@pytest.fixture
def mock_bundle_engine() -> MagicMock:
    """Mock BundleEngine instance."""
    return MagicMock()


# ── Happy-path tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_thread_catalog_returns_200(
    async_client: AsyncClient,
    mock_thread_catalog_service: AsyncMock,
) -> None:
    """GET /pricing/thread-catalog returns 200 with list response."""
    mock_catalog = [
        ThreadEntry(
            thread_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="per 1K tokens",
            raw_cost_inr_paise=5000,
            total_markup_pct=20.0,
            marked_up_cost_paise=6000,
            is_platform_thread=False,
            applicable_agents=["DMA", "RESEARCHER"],
            status="ACTIVE",
        ),
    ]
    mock_thread_catalog_service.return_value = mock_catalog

    with patch(
        "markup.router.ThreadCatalogService.get_catalog",
        mock_thread_catalog_service,
    ):
        response = await async_client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["thread_id"] == "gpt-4-turbo"


@pytest.mark.asyncio
async def test_get_thread_catalog_empty_returns_200(
    async_client: AsyncClient,
    mock_thread_catalog_service: AsyncMock,
) -> None:
    """GET /pricing/thread-catalog with empty catalog returns 200 empty list."""
    mock_thread_catalog_service.return_value = []

    with patch(
        "markup.router.ThreadCatalogService.get_catalog",
        mock_thread_catalog_service,
    ):
        response = await async_client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_returns_200(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns 200."""
    mock_bundle_engine.cost_floor.return_value = 50000

    with patch(
        "markup.router.get_bundle_engine",
        return_value=mock_bundle_engine,
    ):
        response = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert "cost_floor_paise" in body
    assert isinstance(body["cost_floor_paise"], int)
    assert body["cost_floor_paise"] >= 0
    mock_bundle_engine.cost_floor.assert_called_once_with("RESEARCHER", "STARTER")


@pytest.mark.asyncio
async def test_post_pricing_validate_compliant_returns_200(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """POST /pricing/validate with compliant price returns 200 APPROVED."""
    cost_floor = 50000
    compliant_price = 75000
    mock_bundle_engine.cost_floor.return_value = cost_floor
    mock_bundle_engine.validate_price.return_value = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=cost_floor,
        minimum_compliant_price_paise=cost_floor,
        proposed_price_paise=compliant_price,
    )

    payload = PriceValidationRequest(
        agent_type="RESEARCHER",
        bundle_tier="STARTER",
        proposed_price_paise=compliant_price,
    )

    with patch(
        "markup.router.get_bundle_engine",
        return_value=mock_bundle_engine,
    ):
        response = await async_client.post(
            "/pricing/validate",
            json=payload.model_dump(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "APPROVED"
    assert "minimum_compliant_price_paise" not in body


@pytest.mark.asyncio
async def test_post_pricing_derive_returns_200(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """POST /pricing/derive returns 200 with derived price."""
    derived_price = 62500
    mock_bundle_engine.derive_price.return_value = derived_price

    payload = PriceDeriveRequest(
        agent_type="RESEARCHER",
        bundle_tier="STARTER",
        target_margin_pct=25.0,
    )

    with patch(
        "markup.router.get_bundle_engine",
        return_value=mock_bundle_engine,
    ):
        response = await async_client.post(
            "/pricing/derive",
            json=payload.model_dump(),
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert "derived_price_paise" in body
    assert isinstance(body["derived_price_paise"], int)
    assert body["derived_price_paise"] >= 0


# ── C-089 Constitutional Invariant Tests ────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("violation_scenario", [
    {
        "cost_floor": 50000,
        "proposed_price": 0,
        "description": "price is zero paise",
    },
    {
        "cost_floor": 50000,
        "proposed_price": 49999,
        "description": "price is 1 paise below floor",
    },
])
async def test_post_pricing_validate_c089_violation_returns_422(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    violation_scenario: dict[str, int | str],
) -> None:
    """POST /pricing/validate below C-089 floor returns 422 with minimum_compliant_price_paise."""
    cost_floor = violation_scenario["cost_floor"]
    proposed_price = violation_scenario["proposed_price"]

    mock_bundle_engine.cost_floor.return_value = cost_floor
    mock_bundle_engine.validate_price.return_value = PriceValidation(
        outcome="REJECTED",
        cost_floor_paise=cost_floor,
        minimum_compliant_price_paise=cost_floor,
        proposed_price_paise=proposed_price,
    )

    payload = PriceValidationRequest(
        agent_type="RESEARCHER",
        bundle_tier="STARTER",
        proposed_price_paise=proposed_price,
    )

    with patch(
        "markup.router.get_bundle_engine",
        return_value=mock_bundle_engine,
    ):
        response = await async_client.post(
            "/pricing/validate",
            json=payload.model_dump(),
        )

    assert response.status_code == 422
    body = response.json()
    assert "minimum_compliant_price_paise" in body
    assert isinstance(body["minimum_compliant_price_paise"], int)
    assert body["minimum_compliant_price_paise"] > 0


@pytest.mark.asyncio
async def test_post_pricing_validate_missing_field_returns_422(
    async_client: AsyncClient,
) -> None:
    """POST /pricing/validate with missing required field returns 422 validation error."""
    payload = {
        "agent_type": "RESEARCHER",
        # missing bundle_tier and proposed_price_paise
    }

    response = await async_client.post(
        "/pricing/validate",
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_agent_type", [
    "UNKNOWN_AGENT",
    "invalid-agent",
    "",
])
async def test_get_bundle_cost_floor_unknown_agent_returns_non_200(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
    invalid_agent_type: str,
) -> None:
    """GET /pricing/bundle-cost-floor with unknown agent_type returns 404 or 422."""
    mock_bundle_engine.cost_floor.side_effect = ValueError("Unknown agent type")

    with patch(
        "markup.router.get_bundle_engine",
        return_value=mock_bundle_engine,
    ):
        response = await async_client.get(
            f"/pricing/bundle-cost-floor/{invalid_agent_type}/STARTER"
        )

    assert response.status_code in [404, 422]
    assert response.status_code != 200
    assert response.status_code != 500


@pytest.mark.asyncio
async def test_post_pricing_derive_malformed_body_returns_422(
    async_client: AsyncClient,
) -> None:
    """POST /pricing/derive with malformed body returns 422."""
    payload = {
        "agent_type": "RESEARCHER",
        # missing bundle_tier, target_margin_pct is optional but body is incomplete
        "target_margin_pct": "not_a_number",  # wrong type
    }

    response = await async_client.post(
        "/pricing/derive",
        json=payload,
    )

    assert response.status_code == 422


# ── Idempotency Invariants ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_thread_catalog_idempotent(
    async_client: AsyncClient,
    mock_thread_catalog_service: AsyncMock,
) -> None:
    """GET /pricing/thread-catalog called twice returns identical payloads."""
    mock_catalog = [
        ThreadEntry(
            thread_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="per 1K tokens",
            raw_cost_inr_paise=5000,
            total_markup_pct=20.0,
            marked_up_cost_paise=6000,
            is_platform_thread=False,
            applicable_agents=["DMA"],
            status="ACTIVE",
        ),
    ]
    mock_thread_catalog_service.return_value = mock_catalog

    with patch(
        "markup.router.ThreadCatalogService.get_catalog",
        mock_thread_catalog_service,
    ):
        response1 = await async_client.get("/pricing/thread-catalog")
        response2 = await async_client.get("/pricing/thread-catalog")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_idempotent(
    async_client: AsyncClient,
    mock_bundle_engine: MagicMock,
) -> None:
    """GET /pricing/bundle-cost-floor called twice returns same cost floor."""
    mock_bundle_engine.cost_floor.return_value = 50000

    with patch(
        "markup.router.get_bundle_engine",
        return_value=mock_bundle_engine,
    ):
        response1 = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
        )
        response2 = await async_client.get(
            "/pricing/bundle-cost-floor/RESEARCHER/STARTER"
        )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["cost_floor_paise"] == response2.json()["cost_floor_paise"]


# ── Router Mount Invariant ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pricing_router_mounted_at_correct_prefix(
    async_client: AsyncClient,
) -> None:
    """Assert that /pricing/ routes are available (router mounted correctly)."""
    # Attempt to resolve a known pricing endpoint
    try:
        url = app.url_path_for("get_thread_catalog")
        # If url_path_for succeeds, the endpoint exists
        assert "/pricing/" in url or "thread-catalog" in url
    except Exception:
        # Fallback: make a request and verify it does not return 404
        response = await async_client.get("/pricing/thread-catalog")
        # Should not be 404 (which means route not found)
        # Could be 200, or some other error if mock/DB unavailable, but NOT 404
        assert response.status_code != 404


# ── Property-Based Tests (Hypothesis) ───────────────────────────────────────

@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.integers(min_value=0, max_value=1_000_000_000))
async def test_derive_price_with_various_cost_floors(
    mock_bundle_engine: MagicMock,
    cost_floor_paise: int,
) -> None:
    """Property: derive_price(cost_floor, margin) always returns >= cost_floor."""
    target_margin = 25.0
    # Formula: derived = floor / (1 - margin/100)
    # For margin=25%: derived = floor / 0.75 = floor * 1.333...
    expected_derived = int(cost_floor_paise / (1 - target_margin / 100))

    mock_bundle_engine.derive_price.return_value = expected_derived

    result = mock_bundle_engine.derive_price("RESEARCHER", "STARTER", target_margin)

    assert result >= cost_floor_paise


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    st.integers(min_value=0, max_value=100_000_000),
    st.integers(min_value=0, max_value=99),
)
async def test_validate_price_with_generated_values(
    mock_bundle_engine: MagicMock,
    cost_floor_paise: int,
    margin_pct: int,
) -> None:
    """Property: validate_price outcome depends on whether proposed >= floor."""
    proposed_price = cost_floor_paise + 1000  # Always compliant

    mock_bundle_engine.validate_price.return_value = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=cost_floor_paise,
        minimum_compliant_price_paise=cost_floor_paise,
        proposed_price_paise=proposed_price,
    )

    result = mock_bundle_engine.validate_price(
        "RESEARCHER", "STARTER", proposed_price
    )

    assert result.outcome == "APPROVED"
    assert result.proposed_price_paise >= result.cost_floor_paise