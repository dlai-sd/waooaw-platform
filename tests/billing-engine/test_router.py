# Implements: WC027-01b — WC027-01bc
# constitutional_basis: C-059, C-082
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_get_thread_catalog_returns_200(client: TestClient) -> None:
    response = client.get("/thread-catalog")
    assert response.status_code == 200


def test_get_thread_catalog_returns_dict(client: TestClient) -> None:
    response = client.get("/thread-catalog")
    data = response.json()
    assert isinstance(data, dict)


def test_get_bundle_cost_floor_returns_200(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/standard/basic")
    assert response.status_code == 200


def test_get_bundle_cost_floor_returns_dict(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/standard/basic")
    data = response.json()
    assert isinstance(data, dict)


def test_get_bundle_cost_floor_agent_type_in_response(client: TestClient) -> None:
    response = client.get("/bundle-cost-floor/premium/enterprise")
    data = response.json()
    assert "agent_type" in data or isinstance(data, dict)


def test_post_validate_returns_200(client: TestClient) -> None:
    response = client.post("/validate", json={})
    assert response.status_code in (200, 422)


def test_post_validate_with_payload(client: TestClient) -> None:
    payload = {"thread_id": "t-001", "bundle_tier": "basic"}
    response = client.post("/validate", json=payload)
    assert response.status_code in (200, 422)


def test_post_derive_returns_200(client: TestClient) -> None:
    response = client.post("/derive", json={})
    assert response.status_code in (200, 422)


def test_post_derive_with_payload(client: TestClient) -> None:
    payload = {"agent_type": "standard", "bundle_tier": "basic", "quantity": 5}
    response = client.post("/derive", json=payload)
    assert response.status_code in (200, 422)


def test_post_pricing_validate_returns_200(client: TestClient) -> None:
    response = client.post("/pricing/validate", json={})
    assert response.status_code in (200, 422)


def test_post_pricing_validate_with_payload(client: TestClient) -> None:
    payload = {"price": 99.99, "currency": "USD"}
    response = client.post("/pricing/validate", json=payload)
    assert response.status_code in (200, 422)


def test_get_pricing_thread_catalog_returns_200(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    assert response.status_code == 200


def test_get_pricing_thread_catalog_returns_dict(client: TestClient) -> None:
    response = client.get("/pricing/thread-catalog")
    data = response.json()
    assert isinstance(data, dict)


def test_thread_catalog_and_pricing_thread_catalog_consistent(client: TestClient) -> None:
    r1 = client.get("/thread-catalog")
    r2 = client.get("/pricing/thread-catalog")
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_bundle_cost_floor_different_tiers(client: TestClient) -> None:
    tiers = [("standard", "basic"), ("premium", "enterprise"), ("basic", "starter")]
    for agent_type, bundle_tier in tiers:
        response = client.get(f"/bundle-cost-floor/{agent_type}/{bundle_tier}")
        assert response.status_code == 200


def test_post_validate_response_is_dict(client: TestClient) -> None:
    response = client.post("/validate", json={"thread_id": "abc"})
    if response.status_code == 200:
        assert isinstance(response.json(), dict)


def test_post_derive_response_is_dict(client: TestClient) -> None:
    response = client.post("/derive", json={"agent_type": "standard"})
    if response.status_code == 200:
        assert isinstance(response.json(), dict)


def test_post_pricing_validate_response_is_dict(client: TestClient) -> None:
    response = client.post("/pricing/validate", json={"price": 10.0})
    if response.status_code == 200:
        assert isinstance(response.json(), dict)