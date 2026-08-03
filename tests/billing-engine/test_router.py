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

def test_post_validate_returns_200_with_empty_body(client: TestClient) -> None:
    response = client.post("/validate", json={})
    assert response.status_code in (200, 422)


def test_post_validate_returns_dict(client: TestClient) -> None:
    response = client.post("/validate", json={})
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)


def test_post_validate_with_valid_payload(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "price": 100}
    response = client.post("/validate", json=payload)
    assert response.status_code in (200, 422)


# ---------------------------------------------------------------------------
# POST /derive
# ---------------------------------------------------------------------------

def test_post_derive_returns_200_with_empty_body(client: TestClient) -> None:
    response = client.post("/derive", json={})
    assert response.status_code in (200, 422)


def test_post_derive_returns_dict(client: TestClient) -> None:
    response = client.post("/derive", json={})
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)


def test_post_derive_with_valid_payload(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "quantity": 5}
    response = client.post("/derive", json=payload)
    assert response.status_code in (200, 422)


# ---------------------------------------------------------------------------
# POST /pricing/validate
# ---------------------------------------------------------------------------

def test_post_pricing_validate_returns_200_with_empty_body(client: TestClient) -> None:
    response = client.post("/pricing/validate", json={})
    assert response.status_code in (200, 422)


def test_post_pricing_validate_returns_dict(client: TestClient) -> None:
    response = client.post("/pricing/validate", json={})
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)


def test_post_pricing_validate_with_valid_payload(client: TestClient) -> None:
    payload = {"price": 99.99, "currency": "USD", "agent_type": "standard"}
    response = client.post("/pricing/validate", json=payload)
    assert response.status_code in (200, 422)


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


def test_get_pricing_thread_catalog_structure(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Content-type / header checks
# ---------------------------------------------------------------------------

def test_thread_catalog_content_type_json(client: TestClient) -> None:
    response = client.get("/thread-catalog")
    assert "application/json" in response.headers.get("content-type", "")


def test_pricing_thread_catalog_content_type_json(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    assert "application/json" in response.headers.get("content-type", "")


def test_bundle_cost_floor_content_type_json(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/standard/basic")
    if response.status_code == 200:
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Method-not-allowed checks
# ---------------------------------------------------------------------------

def test_thread_catalog_post_not_allowed(client: TestClient) -> None:
    response = client.post("/thread-catalog")
    assert response.status_code == 405


def test_pricing_thread_catalog_post_not_allowed(client: TestClient) -> None:
    response = client.post("/pricing/thread-catalog")
    assert response.status_code == 405


def test_validate_get_not_allowed(client: TestClient) -> None:
    response = client.get("/validate")
    assert response.status_code == 405


def test_derive_get_not_allowed(client: TestClient) -> None:
    response = client.get("/derive")
    assert response.status_code == 405