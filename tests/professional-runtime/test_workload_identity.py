# Implements: ADR-046 sections 3, 5, 6, and 10
# constitutional_basis: C-001, C-023, C-026, C-059, C-063, C-076, C-083, C-084, C-085

from __future__ import annotations

import base64
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.x509.oid import NameOID

from workload_identity import (
    DelegatedContext,
    DelegatedContextVerifier,
    ReplayStore,
    RouteGrant,
    ServiceAuthError,
    extract_peer_identity,
    sign_delegated_context,
)


NOW = 1_800_000_000
TRUST_DOMAIN = "waooaw.ci"
BP_URI = f"spiffe://{TRUST_DOMAIN}/workload/business-platform"
AUDIENCE = "urn:waooaw:service:professional-runtime"
ROUTE = "/api/v1/internal/relationships/{relationshipId}/execution"
OPERATION = "getRelationshipExecution"
DIGEST = "a" * 64


def _context(**overrides: object) -> DelegatedContext:
    base = DelegatedContext(
        schema_version="1.0",
        key_id="delegation-1",
        issuer_uri=BP_URI,
        target_audience=AUDIENCE,
        method="GET",
        route=ROUTE,
        operation=OPERATION,
        contract_major=1,
        actor_subject="actor-opaque",
        actor_source="BP_SESSION",
        effective_role="EMPLOYER",
        tenant_id="tenant-a",
        relationship_id="relationship-a",
        purpose="RELATIONSHIP_EXECUTION_READ",
        subject_reference="relationship-a",
        request_digest=DIGEST,
        command_id="read-1",
        idempotency_key=None,
        expected_versions={"relationship": "7", "execution": "3"},
        issued_at=NOW - 1,
        not_before=NOW - 1,
        expires_at=NOW + 59,
        envelope_id="envelope-1",
        correlation_id="correlation-1",
    )
    return replace(base, **overrides)


def _verifier(private_key: Ed25519PrivateKey) -> DelegatedContextVerifier:
    grant = RouteGrant(BP_URI, AUDIENCE, "GET", ROUTE, OPERATION, 1)
    return DelegatedContextVerifier(
        frozenset({grant}),
        {(BP_URI, "delegation-1"): private_key.public_key()},
        ReplayStore(),
        now=lambda: NOW,
    )


def _verify(
    verifier: DelegatedContextVerifier,
    token: str,
    **overrides: object,
) -> DelegatedContext:
    arguments = {
        "peer_identity_uri": BP_URI,
        "target_audience": AUDIENCE,
        "method": "GET",
        "route": ROUTE,
        "operation": OPERATION,
        "contract_major": 1,
        "request_digest": DIGEST,
        "rebind": lambda context: (
            context.tenant_id == "tenant-a"
            and context.relationship_id == "relationship-a"
            and context.effective_role == "EMPLOYER"
        ),
    }
    arguments.update(overrides)
    return verifier.verify(token, **arguments)


def _certificate(uri: str, *, valid: bool = True) -> x509.Certificate:
    key = generate_private_key(public_exponent=65537, key_size=2048)
    current = datetime.now(timezone.utc)
    start = current - timedelta(minutes=1) if valid else current - timedelta(hours=2)
    end = current + timedelta(hours=1) if valid else current - timedelta(hours=1)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ignored-cn")])
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(end)
        .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(uri)]), critical=True)
        .sign(key, hashes.SHA256())
    )


def test_exact_peer_identity_and_bound_envelope_pass() -> None:
    private_key = Ed25519PrivateKey.generate()
    certificate = _certificate(BP_URI)
    peer_uri = extract_peer_identity(certificate, TRUST_DOMAIN)
    token = sign_delegated_context(_context(), private_key)

    verified = _verify(_verifier(private_key), token, peer_identity_uri=peer_uri)

    assert verified.relationship_id == "relationship-a"


@pytest.mark.parametrize(
    ("context_change", "call_change", "expected_code"),
    [
        ({"issuer_uri": "spiffe://waooaw.ci/workload/other"}, {}, "SERVICE_AUTHENTICATION_FAILED"),
        ({"target_audience": "urn:waooaw:service:billing-engine"}, {}, "DELEGATED_CONTEXT_INVALID"),
        ({"operation": "controlRelationshipExecution"}, {}, "DELEGATED_CONTEXT_INVALID"),
        ({"request_digest": "b" * 64}, {}, "DELEGATED_CONTEXT_INVALID"),
        ({"contract_major": 2}, {}, "DELEGATED_CONTEXT_INVALID"),
        ({"actor_source": "CALLER_HEADER"}, {}, "DELEGATED_CONTEXT_INVALID"),
        ({"expires_at": NOW}, {}, "DELEGATED_CONTEXT_EXPIRED"),
        ({"expires_at": NOW + 61}, {}, "DELEGATED_CONTEXT_INVALID"),
        ({}, {"target_audience": "urn:waooaw:service:billing-engine"}, "SERVICE_AUTHORIZATION_DENIED"),
        ({}, {"method": "POST"}, "SERVICE_AUTHORIZATION_DENIED"),
    ],
)
def test_wrong_binding_fails_closed(
    context_change: dict[str, object],
    call_change: dict[str, object],
    expected_code: str,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    token = sign_delegated_context(_context(**context_change), private_key)

    with pytest.raises(ServiceAuthError) as failure:
        _verify(_verifier(private_key), token, **call_change)

    assert failure.value.code == expected_code


def test_signature_tampering_and_unknown_key_are_privacy_safe() -> None:
    private_key = Ed25519PrivateKey.generate()
    other_key = Ed25519PrivateKey.generate()
    token = sign_delegated_context(_context(), private_key)

    with pytest.raises(ServiceAuthError) as tampered:
        _verify(_verifier(other_key), token)
    assert tampered.value.code == "DELEGATED_CONTEXT_INVALID"

    unknown_key_token = sign_delegated_context(_context(key_id="unknown"), private_key)
    with pytest.raises(ServiceAuthError) as unknown:
        _verify(_verifier(private_key), unknown_key_token)
    assert unknown.value.code == "SERVICE_AUTHENTICATION_FAILED"


def test_signed_noncanonical_payload_is_rejected() -> None:
    private_key = Ed25519PrivateKey.generate()
    payload = json.dumps(_context().__dict__).encode()
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    encoded_signature = base64.urlsafe_b64encode(private_key.sign(payload)).rstrip(b"=").decode()

    with pytest.raises(ServiceAuthError) as failure:
        _verify(_verifier(private_key), f"{encoded_payload}.{encoded_signature}")

    assert failure.value.code == "DELEGATED_CONTEXT_INVALID"


def test_target_rebinding_denies_cross_relationship_without_disclosure() -> None:
    private_key = Ed25519PrivateKey.generate()
    token = sign_delegated_context(_context(relationship_id="relationship-b"), private_key)

    with pytest.raises(ServiceAuthError) as failure:
        _verify(_verifier(private_key), token)

    assert failure.value.code == "SERVICE_AUTHORIZATION_DENIED"
    assert "relationship" not in str(failure.value).lower()


def test_envelope_id_is_single_use_but_fresh_envelope_can_retry() -> None:
    private_key = Ed25519PrivateKey.generate()
    verifier = _verifier(private_key)
    first = sign_delegated_context(_context(), private_key)
    retry = sign_delegated_context(_context(envelope_id="envelope-2"), private_key)

    _verify(verifier, first)
    with pytest.raises(ServiceAuthError) as replay:
        _verify(verifier, first)
    assert replay.value.code == "DELEGATED_CONTEXT_REPLAYED"
    assert _verify(verifier, retry).envelope_id == "envelope-2"


@pytest.mark.parametrize(
    "certificate",
    [
        _certificate("spiffe://waooaw.dev/workload/business-platform"),
        _certificate(f"spiffe://{TRUST_DOMAIN}/workload/*"),
        _certificate(BP_URI, valid=False),
    ],
)
def test_wrong_environment_wildcard_and_expired_certificate_are_rejected(
    certificate: x509.Certificate,
) -> None:
    with pytest.raises(ServiceAuthError) as failure:
        extract_peer_identity(certificate, TRUST_DOMAIN)

    assert failure.value.code == "SERVICE_AUTHENTICATION_FAILED"


def test_revoked_certificate_is_rejected() -> None:
    certificate = _certificate(BP_URI)

    with pytest.raises(ServiceAuthError) as failure:
        extract_peer_identity(certificate, TRUST_DOMAIN, frozenset({certificate.serial_number}))

    assert failure.value.code == "SERVICE_AUTHENTICATION_FAILED"
