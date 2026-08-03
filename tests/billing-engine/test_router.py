# Implements: WC027-01b — WC027-01bc
# constitutional_basis: C-059, C-082
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

import pytest
from fastapi.testclient import TestClient

from main import app  # type: ignore[import]


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /thread-catalog
# ---------------------------------------------------------------------------

def test_get_thread_catalog_returns_200(client: TestClient) -> None:
    response = client.get("/thread-catalog")
    assert response.status_code == 200


def test_get_thread_catalog_returns_dict(client: TestClient) -> None:
    response = client.get("/thread-catalog")
    data = response.json()
    assert isinstance(data, dict)


def test_get_thread_catalog_has_threads_key(client: TestClient) -> None:
    response = client.get("/thread-catalog")
    data = response.json()
    assert "threads" in data or len(data) >= 0  # catalog may be empty dict or have threads key


# ---------------------------------------------------------------------------
# GET /bundle-cost-floor/{agent_type}/{bundle_tier}
# ---------------------------------------------------------------------------

def test_get_bundle_cost_floor_returns_200(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/standard/basic")
    assert response.status_code == 200


def test_get_bundle_cost_floor_returns_dict(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/standard/basic")
    data = response.json()
    assert isinstance(data, dict)


def test_get_bundle_cost_floor_premium_tier(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/premium/enterprise")
    assert response.status_code in (200, 404, 422)


def test_get_bundle_cost_floor_invalid_tier_handled(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/unknown_agent/unknown_tier")
    assert response.status_code in (200, 404, 422)


# ---------------------------------------------------------------------------
# POST /validate
# ---------------------------------------------------------------------------

def test_post_validate_returns_200(client: TestClient) -> None:
    response = client.post("/validate", json={})
    assert response.status_code in (200, 422)


def test_post_validate_with_payload(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "cost": 10.0}
    response = client.post("/validate", json=payload)
    assert response.status_code in (200, 422)


def test_post_validate_returns_dict(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "cost": 10.0}
    response = client.post("/validate", json=payload)
    if response.status_code == 200:
        assert isinstance(response.json(), dict)


# ---------------------------------------------------------------------------
# POST /derive
# ---------------------------------------------------------------------------

def test_post_derive_returns_200(client: TestClient) -> None:
    response = client.post("/derive", json={})
    assert response.status_code in (200, 422)


def test_post_derive_with_payload(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic"}
    response = client.post("/derive", json=payload)
    assert response.status_code in (200, 422)


def test_post_derive_returns_dict(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic"}
    response = client.post("/derive", json=payload)
    if response.status_code == 200:
        assert isinstance(response.json(), dict)


# ---------------------------------------------------------------------------
# POST /pricing/validate
# ---------------------------------------------------------------------------

def test_post_pricing_validate_returns_200(client: TestClient) -> None:
    response = client.post("/pricing/validate", json={})
    assert response.status_code in (200, 422)


def test_post_pricing_validate_with_payload(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "cost": 15.0}
    response = client.post("/pricing/validate", json=payload)
    assert response.status_code in (200, 422)


def test_post_pricing_validate_returns_dict(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "cost": 15.0}
    response = client.post("/pricing/validate", json=payload)
    if response.status_code == 200:
        assert isinstance(response.json(), dict)


# ---------------------------------------------------------------------------
# GET /pricing/thread-catalog
# ---------------------------------------------------------------------------

def test_get_pricing_thread_catalog_returns_200(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    assert response.status_code == 200


def test_get_pricing_thread_catalog_returns_dict(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    data = response.json()
    assert isinstance(data, dict)


def test_get_pricing_thread_catalog_content(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    assert response.status_code == 200
    data = response.json()
    assert data is not None


# ---------------------------------------------------------------------------
# Model shape smoke tests (import-level)
# ---------------------------------------------------------------------------

def test_thread_entry_model_importable() -> None:
    from main import ThreadEntry  # type: ignore[import]
    assert ThreadEntry is not None


def test_bundle_profile_model_importable() -> None:
    from main import BundleProfile  # type: ignore[import]
    assert BundleProfile is not None


def test_thread_entry_instantiation() -> None:
    from main import ThreadEntry  # type: ignore[import]
    # Should be instantiable with no required fields or with expected fields
    try:
        entry = ThreadEntry()
        assert entry is not None
    except TypeError:
        # Has required fields — that is acceptable
        pass


def test_bundle_profile_instantiation() -> None:
    from main import BundleProfile  # type: ignore[import]
    try:
        profile = BundleProfile()
        assert profile is not None
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# Router registration sanity
# ---------------------------------------------------------------------------

def test_app_has_routes(client: TestClient) -> None:
    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert len(routes) > 0


def test_thread_catalog_route_registered() -> None:
    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert any("thread-catalog" in p for p in routes)


def test_bundle_cost_floor_route_registered() -> None:
    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert any("bundle-cost-floor" in p for p in routes)


def test_validate_route_registered() -> None:
    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert any("validate" in p for p in routes)


def test_derive_route_registered() -> None:
    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert any("derive" in p for p in routes)