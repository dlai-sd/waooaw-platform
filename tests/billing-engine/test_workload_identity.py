# Implements: ADR-046 sections 3, 5, 6, and 10
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-076, C-083, C-084, C-085

import base64
import json
from dataclasses import asdict, replace

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from workload_identity import DelegatedContext, DelegatedContextVerifier, ReplayStore, RouteGrant, ServiceAuthError

NOW = 1_800_000_000
BP = "spiffe://waooaw.ci/workload/business-platform"
AUDIENCE = "urn:waooaw:service:billing-engine"
ROUTE = "/internal/v1/relationships/{relationshipId}/commercial-projection"
OPERATION = "getRelationshipCommercialProjection"
DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def context(**changes):
    value = DelegatedContext(
        "1.0", "key-1", BP, AUDIENCE, "GET", ROUTE, OPERATION, 1, "actor", "BP_SESSION",
        "EMPLOYER", "tenant-a", "relationship-a", OPERATION, "relationship-a", DIGEST,
        "read-1", None, {"relationship": "1"}, NOW - 1, NOW - 1, NOW + 59, "envelope-1", "correlation-1")
    return replace(value, **changes)


def token(value, key):
    payload = json.dumps(asdict(value), separators=(",", ":"), sort_keys=True).encode()
    signature = key.sign(payload, ec.ECDSA(hashes.SHA256()))

    def encode(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{encode(payload)}.{encode(signature)}"


def verifier(key):
    return DelegatedContextVerifier(
        frozenset({RouteGrant(BP, AUDIENCE, "GET", ROUTE, OPERATION, 1)}),
        {(BP, "key-1"): key.public_key()}, ReplayStore(), now=lambda: NOW)


def verify(instance, signed, **changes):
    arguments = dict(peer_identity_uri=BP, target_audience=AUDIENCE, method="GET", route=ROUTE,
        operation=OPERATION, contract_major=1, request_digest=DIGEST,
        rebind=lambda value: value.tenant_id == "tenant-a" and value.relationship_id == "relationship-a")
    arguments.update(changes)
    return instance.verify(signed, **arguments)


def test_exact_wbe_binding_succeeds_and_replay_fails() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    instance = verifier(key)
    signed = token(context(), key)
    assert verify(instance, signed).relationship_id == "relationship-a"
    with pytest.raises(ServiceAuthError, match="DELEGATED_CONTEXT_REPLAYED"):
        verify(instance, signed)


@pytest.mark.parametrize("call_change", [
    {"target_audience": "urn:waooaw:service:professional-runtime"},
    {"route": "/internal/v1/relationships/{relationshipId}/commercial-commands"},
    {"method": "POST"},
])
def test_wrong_audience_route_or_method_is_denied(call_change) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHORIZATION_DENIED"):
        verify(verifier(key), token(context(), key), **call_change)


def test_cross_relationship_rebinding_is_denied() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHORIZATION_DENIED"):
        verify(verifier(key), token(context(relationship_id="relationship-b"), key))


def test_expired_envelope_is_denied() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(ServiceAuthError, match="DELEGATED_CONTEXT_EXPIRED"):
        verify(verifier(key), token(context(expires_at=NOW), key))