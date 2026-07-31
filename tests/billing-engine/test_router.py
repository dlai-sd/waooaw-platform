# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01b
# constitutional_basis: C-023, C-027, C-059, C-063, C-089
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

# Add src/billing-engine to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "billing-engine"))

from main import app


@pytest.fixture
async def app_client():
    """Provide an AsyncClient for the FastAPI app using ASGITransport."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_thread_catalog_service():
    """Mock ThreadCatalogService to avoid DB/Redis access."""
    stub_catalog = [
        {"agent_type": "STANDARD", "bundle_tier": "BASIC", "thread_id": "t1"},
        {"agent_type": "PREMIUM", "bundle_tier": "ADVANCED", "thread_id": "t2"},
    ]
    mock_svc = AsyncMock()
    mock_svc.get_catalog = AsyncMock(return_value=stub_catalog)
    return mock_svc, stub_catalog


@pytest.fixture
def mock_bundle_engine():
    """Mock BundleEngine for cost floor and derive operations."""
    mock_engine = MagicMock()
    mock_engine.cost_floor = MagicMock(return_value=10_000)
    mock_engine.derive_price = MagicMock(return_value=12_500)
    mock_engine.validate_price = MagicMock()
    return mock_engine


class TestGetThreadCatalog:
    """Test GET /pricing/thread-catalog endpoint."""

    async def test_get_thread_catalog_success(self, app_client, mock_thread_catalog_service):
        """Test successful retrieval of thread catalog."""
        mock_svc, _stub_catalog = mock_thread_catalog_service
        
        with patch(
            "markup.thread_catalog.ThreadCatalogService",
            return_value=mock_svc
        ):
            response = await app_client.get("/pricing/thread-catalog")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        assert data[0].get("agent_type") in ["STANDARD", "PREMIUM"]
        assert data[0].get("bundle_tier") in ["BASIC", "ADVANCED"]

    async def test_get_thread_catalog_response_shape(self, app_client, mock_thread_catalog_service):
        """Test that response contains required fields."""
        mock_svc, _stub_catalog = mock_thread_catalog_service
        
        with patch(
            "markup.thread_catalog.ThreadCatalogService",
            return_value=mock_svc
        ):
            response = await app_client.get("/pricing/thread-catalog")
        
        assert response.status_code == 200
        data = response.json()
        for entry in data:
            assert "agent_type" in entry
            assert "bundle_tier" in entry


class TestGetBundleCostFloor:
    """Test GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} endpoint."""

    async def test_get_cost_floor_known_pair(self, app_client, mock_bundle_engine):
        """Test cost floor retrieval for known agent_type and bundle_tier."""
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_bundle_engine
        ):
            response = await app_client.get("/pricing/bundle-cost-floor/STANDARD/BASIC")
        
        assert response.status_code == 200
        data = response.json()
        assert "floor_price_paise" in data
        assert isinstance(data["floor_price_paise"], int)
        assert data["floor_price_paise"] > 0

    async def test_get_cost_floor_unknown_pair(self, app_client, mock_bundle_engine):
        """Test cost floor retrieval for unknown pair returns 404."""
        mock_engine = MagicMock()
        mock_engine.cost_floor = MagicMock(side_effect=ValueError("Unknown pair"))
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.get("/pricing/bundle-cost-floor/UNKNOWN_AGENT/NONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert len(data["detail"]) > 0

    async def test_get_cost_floor_path_parameters(self, app_client, mock_bundle_engine):
        """Test that path parameters are forwarded correctly."""
        mock_engine = MagicMock()
        mock_engine.cost_floor = MagicMock(return_value=15_000)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.get("/pricing/bundle-cost-floor/PREMIUM/ADVANCED")
        
        assert response.status_code == 200
        mock_engine.cost_floor.assert_called_once_with("PREMIUM", "ADVANCED")


class TestPostValidate:
    """Test POST /pricing/validate endpoint."""

    async def test_validate_price_above_floor_allowed(self, app_client, mock_bundle_engine):
        """Test that price above floor is approved."""
        floor_paise = 10_000
        proposed_price = 15_000
        
        from markup.models import PriceValidation
        validation_result = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=floor_paise,
            minimum_compliant_price_paise=floor_paise,
            proposed_price_paise=proposed_price
        )
        
        mock_engine = MagicMock()
        mock_engine.validate_price = MagicMock(return_value=validation_result)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.post(
                "/pricing/validate",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "proposed_price_paise": proposed_price
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("outcome") == "APPROVED"
        assert "minimum_compliant_price_paise" not in data or data.get("minimum_compliant_price_paise") is None

    async def test_validate_price_below_floor_rejected_c089(self, app_client, mock_bundle_engine):
        """Test C-089 constitutional violation: price below floor returns 422 with minimum_compliant_price_paise."""
        floor_paise = 10_000
        proposed_price = 5_000
        
        from markup.models import PriceValidation
        validation_result = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=floor_paise,
            minimum_compliant_price_paise=floor_paise,
            proposed_price_paise=proposed_price
        )
        
        mock_engine = MagicMock()
        mock_engine.validate_price = MagicMock(return_value=validation_result)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.post(
                "/pricing/validate",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "proposed_price_paise": proposed_price
                }
            )
        
        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert data["minimum_compliant_price_paise"] == floor_paise
        assert data.get("outcome") == "REJECTED"
        assert "C-089" in data.get("violation_claim", "C-089")

    async def test_validate_missing_required_fields(self, app_client):
        """Test validation with missing required fields returns 422 (schema validation)."""
        response = await app_client.post(
            "/pricing/validate",
            json={}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    async def test_validate_price_at_exact_floor_allowed(self, app_client, mock_bundle_engine):
        """Test that price exactly at floor is approved (inclusive boundary)."""
        floor_paise = 10_000
        proposed_price = 10_000
        
        from markup.models import PriceValidation
        validation_result = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=floor_paise,
            minimum_compliant_price_paise=floor_paise,
            proposed_price_paise=proposed_price
        )
        
        mock_engine = MagicMock()
        mock_engine.validate_price = MagicMock(return_value=validation_result)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.post(
                "/pricing/validate",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "proposed_price_paise": proposed_price
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("outcome") == "APPROVED"


class TestPostDerive:
    """Test POST /pricing/derive endpoint."""

    async def test_derive_price_success(self, app_client, mock_bundle_engine):
        """Test successful price derivation."""
        base_cost = 10_000
        derived_price = 12_500
        
        mock_engine = MagicMock()
        mock_engine.derive_price = MagicMock(return_value=derived_price)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.post(
                "/pricing/derive",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "base_cost_paise": base_cost,
                    "margin_bps": 2500
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "derived_price_paise" in data
        assert isinstance(data["derived_price_paise"], int)
        assert data["derived_price_paise"] >= base_cost

    async def test_derive_price_markup_nonnegative(self, app_client, mock_bundle_engine):
        """Test that derived price includes non-negative markup."""
        base_cost = 10_000
        derived_price = 10_500
        
        mock_engine = MagicMock()
        mock_engine.derive_price = MagicMock(return_value=derived_price)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response = await app_client.post(
                "/pricing/derive",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "base_cost_paise": base_cost,
                    "margin_bps": 500
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["derived_price_paise"] >= base_cost

    async def test_derive_missing_required_fields(self, app_client):
        """Test derivation with missing required fields returns 422."""
        response = await app_client.post(
            "/pricing/derive",
            json={}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    async def test_derive_price_idempotency(self, app_client, mock_bundle_engine):
        """Test that derive price is idempotent (same input → same output)."""
        base_cost = 10_000
        derived_price = 12_500
        
        mock_engine = MagicMock()
        mock_engine.derive_price = MagicMock(return_value=derived_price)
        
        with patch(
            "markup.bundle_engine.BundleEngine",
            return_value=mock_engine
        ):
            response1 = await app_client.post(
                "/pricing/derive",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "base_cost_paise": base_cost,
                    "margin_bps": 2500
                }
            )
            response2 = await app_client.post(
                "/pricing/derive",
                json={
                    "agent_type": "STANDARD",
                    "bundle_tier": "BASIC",
                    "base_cost_paise": base_cost,
                    "margin_bps": 2500
                }
            )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        data1 = response1.json()
        data2 = response2.json()
        assert data1["derived_price_paise"] == data2["derived_price_paise"]


class TestRouterWiring:
    """Test that router is properly mounted in main.py."""

    def test_pricing_routes_exist(self):
        """Test that all required /pricing routes are registered."""
        routes = [route.path for route in app.routes]
        
        assert any("/pricing/thread-catalog" in path for path in routes)
        assert any("/pricing/bundle-cost-floor" in path for path in routes)
        assert any("/pricing/validate" in path for path in routes)
        assert any("/pricing/derive" in path for path in routes)

    def test_pricing_route_methods(self):
        """Test that routes use correct HTTP methods."""
        methods_by_path = {}
        for route in app.routes:
            if "/pricing" in route.path:
                path = route.path
                if hasattr(route, "methods"):
                    methods_by_path[path] = route.methods
        
        # GET routes
        assert any(
            "/pricing/thread-catalog" in path and "GET" in methods
            for path, methods in methods_by_path.items()
        )
        assert any(
            "/pricing/bundle-cost-floor" in path and "GET" in methods
            for path, methods in methods_by_path.items()
        )
        
        # POST routes
        assert any(
            "/pricing/validate" in path and "POST" in methods
            for path, methods in methods_by_path.items()
        )
        assert any(
            "/pricing/derive" in path and "POST" in methods
            for path, methods in methods_by_path.items()
        )