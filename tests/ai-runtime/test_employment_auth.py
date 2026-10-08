from __future__ import annotations

import base64
import json
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509.oid import NameOID
from starlette.requests import Request

from employment_auth import (
    PEER_CERTIFICATE_STATE_KEY,
    DelegatedContext,
    EmploymentAuthError,
    EmploymentWorkloadAuth,
    ReplayStore,
    RouteGrant,
    request_digest,
)
from scripts.bootstrap_workload_identity import bootstrap


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _certificate(
    key: ec.EllipticCurvePrivateKey,
    identity: str,
) -> x509.Certificate:
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "professional-runtime")])
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(minutes=5))
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(identity)]),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )


def _request(certificate: x509.Certificate, token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/internal/v1/employment-patch-proposals",
            "headers": [
                (b"authorization", f"Bearer {token}".encode()),
                (b"x-correlation-id", b"00000000-0000-0000-0000-000000000007"),
            ],
            "state": {PEER_CERTIFICATE_STATE_KEY: certificate.public_bytes(serialization.Encoding.DER)},
        }
    )


def test_signed_air_envelope_is_exactly_bound_and_single_use() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    identity = "spiffe://waooaw.test/workload/professional-runtime"
    audience = "urn:waooaw:service:ai-runtime"
    route = "/internal/v1/employment-patch-proposals"
    digest = request_digest({"relationshipRef": "relationship-1"})
    now = int(datetime.now(timezone.utc).timestamp())
    context = DelegatedContext(
        schema_version="1.0",
        key_id="pr-key",
        issuer_uri=identity,
        target_audience=audience,
        method="POST",
        route=route,
        operation="proposeEmploymentPatch",
        contract_major=1,
        actor_subject="customer-1",
        actor_source="BP_SESSION",
        effective_role="CUSTOMER",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
        purpose="EMPLOYMENT_PATCH_PROPOSAL",
        subject_reference="subject-1",
        request_digest=digest,
        command_id="command-1",
        idempotency_key="00000000-0000-0000-0000-000000000009",
        expected_versions={},
        issued_at=now,
        not_before=now,
        expires_at=now + 60,
        envelope_id="00000000-0000-0000-0000-000000000008",
        correlation_id="00000000-0000-0000-0000-000000000007",
    )
    payload = json.dumps(
        asdict(context),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    token = f"{_encode(payload)}.{_encode(key.sign(payload, ec.ECDSA(hashes.SHA256())))}"
    certificate = _certificate(key, identity)
    auth = EmploymentWorkloadAuth(
        frozenset(
            {
                RouteGrant(
                    identity,
                    audience,
                    "POST",
                    route,
                    "proposeEmploymentPatch",
                    1,
                )
            }
        ),
        {(identity, "pr-key"): key.public_key()},
        "waooaw.test",
        audience,
        now=lambda: now,
    )

    accepted = auth.authorize(
        _request(certificate, token),
        route,
        "proposeEmploymentPatch",
        digest,
        "relationship-1",
        context.idempotency_key,
    )
    assert accepted.tenant_id == context.tenant_id

    with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
        auth.authorize(
            _request(certificate, token),
            route,
            "proposeEmploymentPatch",
            digest,
            "relationship-1",
            context.idempotency_key,
        )


@pytest.mark.parametrize(
    ("authorization", "state"),
    [
        ("", {}),
        ("Basic invalid", {}),
        (
            "Bearer invalid",
            {PEER_CERTIFICATE_STATE_KEY: b"invalid-certificate"},
        ),
    ],
)
def test_air_auth_rejects_missing_or_malformed_transport(
    authorization: str,
    state: dict[str, bytes],
) -> None:
    auth = EmploymentWorkloadAuth(
        frozenset(),
        {},
        "waooaw.test",
        "urn:waooaw:service:ai-runtime",
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/internal/v1/employment-patch-proposals",
            "headers": [(b"authorization", authorization.encode())],
            "state": state,
        }
    )
    with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
        auth.authorize(
            request,
            "/internal/v1/employment-patch-proposals",
            "proposeEmploymentPatch",
            "a" * 64,
            "relationship-1",
            None,
        )


def test_auth_loads_exact_pr_to_air_grants_from_generated_credentials(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[2]
    credentials = tmp_path / "credentials"
    manifest = bootstrap(
        repository / "infrastructure/workload-identity/registry.yaml",
        "ci",
        credentials,
    )
    auth = EmploymentWorkloadAuth.from_credentials(credentials)
    caller = manifest["workloads"]["professional-runtime"]
    target = manifest["workloads"]["ai-runtime"]
    private_key = load_pem_private_key(
        (credentials / "workloads" / "professional-runtime" / "delegation-key.pem").read_bytes(),
        password=None,
    )
    assert isinstance(private_key, ec.EllipticCurvePrivateKey)
    certificate = x509.load_pem_x509_certificate(
        (credentials / "workloads" / "professional-runtime" / "tls-cert.pem").read_bytes()
    )
    now = int(datetime.now(timezone.utc).timestamp())
    digest = request_digest(None)
    context = DelegatedContext(
        schema_version="1.0",
        key_id=caller["delegation_key_id"],
        issuer_uri=caller["identity_uri"],
        target_audience=target["audience"],
        method="GET",
        route="/internal/v1/employment-patch-proposals/{proposalId}",
        operation="getEmploymentPatchProposal",
        contract_major=1,
        actor_subject="customer-1",
        actor_source="BP_SESSION",
        effective_role="CUSTOMER",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
        purpose="EMPLOYMENT_PATCH_RECONCILIATION",
        subject_reference="subject-1",
        request_digest=digest,
        command_id="command-1",
        idempotency_key=None,
        expected_versions={},
        issued_at=now,
        not_before=now,
        expires_at=now + 60,
        envelope_id="00000000-0000-0000-0000-000000000008",
        correlation_id="00000000-0000-0000-0000-000000000007",
    )
    payload = json.dumps(
        asdict(context),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    token = f"{_encode(payload)}.{_encode(private_key.sign(payload, ec.ECDSA(hashes.SHA256())))}"
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/internal/v1/employment-patch-proposals/{context.command_id}",
            "headers": [
                (b"authorization", f"Bearer {token}".encode()),
                (b"x-correlation-id", context.correlation_id.encode()),
            ],
            "state": {PEER_CERTIFICATE_STATE_KEY: certificate.public_bytes(serialization.Encoding.DER)},
        }
    )
    accepted = auth.authorize(
        request,
        context.route,
        context.operation,
        digest,
        None,
        None,
    )
    assert accepted.issuer_uri == caller["identity_uri"]


@pytest.mark.parametrize(
    "change",
    [
        {"target_audience": "wrong-audience"},
        {"method": "GET"},
        {"route": "/wrong"},
        {"operation": "wrongOperation"},
        {"contract_major": 2},
        {"request_digest": "f" * 64},
        {"actor_source": "CALLER_SUPPLIED"},
        {"relationship_id": "relationship-2"},
        {"tenant_id": ""},
        {"actor_subject": ""},
        {"correlation_id": "00000000-0000-0000-0000-000000000099"},
        {"idempotency_key": "00000000-0000-0000-0000-000000000099"},
        {"issued_at": 2_000_000_000, "not_before": 2_000_000_000},
        {"expires_at": 1_700_000_061},
    ],
)
def test_air_envelope_rejects_every_exact_binding_mutation(
    change: dict[str, object],
) -> None:
    now = 1_700_000_000
    key = ec.generate_private_key(ec.SECP256R1())
    identity = "spiffe://waooaw.test/workload/professional-runtime"
    audience = "urn:waooaw:service:ai-runtime"
    route = "/internal/v1/employment-patch-proposals"
    digest = request_digest({"relationshipRef": "relationship-1"})
    context = replace(
        DelegatedContext(
            schema_version="1.0",
            key_id="pr-key",
            issuer_uri=identity,
            target_audience=audience,
            method="POST",
            route=route,
            operation="proposeEmploymentPatch",
            contract_major=1,
            actor_subject="customer-1",
            actor_source="BP_SESSION",
            effective_role="CUSTOMER",
            tenant_id="00000000-0000-0000-0000-000000000001",
            relationship_id="relationship-1",
            purpose="EMPLOYMENT_PATCH_PROPOSAL",
            subject_reference="subject-1",
            request_digest=digest,
            command_id="command-1",
            idempotency_key="00000000-0000-0000-0000-000000000009",
            expected_versions={},
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id="00000000-0000-0000-0000-000000000008",
            correlation_id="00000000-0000-0000-0000-000000000007",
        ),
        **change,
    )
    payload = json.dumps(
        asdict(context),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    token = f"{_encode(payload)}.{_encode(key.sign(payload, ec.ECDSA(hashes.SHA256())))}"
    auth = EmploymentWorkloadAuth(
        frozenset(
            {
                RouteGrant(
                    identity,
                    audience,
                    "POST",
                    route,
                    "proposeEmploymentPatch",
                    1,
                )
            }
        ),
        {(identity, "pr-key"): key.public_key()},
        "waooaw.test",
        audience,
        now=lambda: now,
    )

    with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
        auth.authorize(
            _request(_certificate(key, identity), token),
            route,
            "proposeEmploymentPatch",
            digest,
            "relationship-1",
            "00000000-0000-0000-0000-000000000009",
        )


@pytest.mark.parametrize("failure", ["NON_CANONICAL", "UNKNOWN_KEY", "BAD_SIGNATURE"])
def test_air_envelope_rejects_invalid_signature_identity_and_encoding(
    failure: str,
) -> None:
    now = int(datetime.now(timezone.utc).timestamp())
    key = ec.generate_private_key(ec.SECP256R1())
    other_key = ec.generate_private_key(ec.SECP256R1())
    identity = "spiffe://waooaw.test/workload/professional-runtime"
    audience = "urn:waooaw:service:ai-runtime"
    route = "/internal/v1/employment-patch-proposals"
    digest = request_digest(None)
    context = DelegatedContext(
        schema_version="1.0",
        key_id="unknown" if failure == "UNKNOWN_KEY" else "pr-key",
        issuer_uri=identity,
        target_audience=audience,
        method="POST",
        route=route,
        operation="proposeEmploymentPatch",
        contract_major=1,
        actor_subject="customer-1",
        actor_source="BP_SESSION",
        effective_role="CUSTOMER",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
        purpose="EMPLOYMENT_PATCH_PROPOSAL",
        subject_reference="subject-1",
        request_digest=digest,
        command_id="command-1",
        idempotency_key=None,
        expected_versions={},
        issued_at=now,
        not_before=now,
        expires_at=now + 60,
        envelope_id="00000000-0000-0000-0000-000000000008",
        correlation_id="00000000-0000-0000-0000-000000000007",
    )
    payload = json.dumps(
        asdict(context),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=failure != "NON_CANONICAL",
    ).encode()
    signing_key = other_key if failure == "BAD_SIGNATURE" else key
    token = f"{_encode(payload)}.{_encode(signing_key.sign(payload, ec.ECDSA(hashes.SHA256())))}"
    auth = EmploymentWorkloadAuth(
        frozenset(
            {
                RouteGrant(
                    identity,
                    audience,
                    "POST",
                    route,
                    "proposeEmploymentPatch",
                    1,
                )
            }
        ),
        {(identity, "pr-key"): key.public_key()},
        "waooaw.test",
        audience,
        now=lambda: now,
    )

    with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
        auth.authorize(
            _request(_certificate(key, identity), token),
            route,
            "proposeEmploymentPatch",
            digest,
            "relationship-1",
            None,
        )


def test_air_peer_identity_rejects_missing_and_ambiguous_uri_sans() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "professional-runtime")])
    base = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(minutes=5))
    )
    without_san = base.sign(key, hashes.SHA256())
    ambiguous = base.add_extension(
        x509.SubjectAlternativeName(
            [
                x509.UniformResourceIdentifier("spiffe://waooaw.test/workload/professional-runtime"),
                x509.UniformResourceIdentifier("spiffe://waooaw.test/workload/other"),
            ]
        ),
        critical=True,
    ).sign(key, hashes.SHA256())
    auth = EmploymentWorkloadAuth(
        frozenset(),
        {},
        "waooaw.test",
        "urn:waooaw:service:ai-runtime",
    )

    for certificate in (without_san, ambiguous):
        with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
            auth._peer_identity(certificate)


def test_air_peer_identity_rejects_expired_and_wildcard_certificates() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "professional-runtime")])

    def certificate(
        not_before: datetime,
        not_after: datetime,
        identity: str,
    ) -> x509.Certificate:
        return (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .add_extension(
                x509.SubjectAlternativeName([x509.UniformResourceIdentifier(identity)]),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )

    invalid = (
        certificate(
            now - timedelta(minutes=5),
            now - timedelta(minutes=1),
            "spiffe://waooaw.test/workload/professional-runtime",
        ),
        certificate(
            now + timedelta(minutes=1),
            now + timedelta(minutes=5),
            "spiffe://waooaw.test/workload/professional-runtime",
        ),
        certificate(
            now - timedelta(minutes=1),
            now + timedelta(minutes=5),
            "spiffe://waooaw.test/workload/*",
        ),
    )
    auth = EmploymentWorkloadAuth(
        frozenset(),
        {},
        "waooaw.test",
        "urn:waooaw:service:ai-runtime",
    )
    for item in invalid:
        with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
            auth._peer_identity(item)


def test_replay_store_expires_old_entries_but_preserves_live_denial() -> None:
    replay = ReplayStore()
    replay.consume(("expired",), expires_at=2, now=1)
    replay.consume(("replacement",), expires_at=4, now=3)
    replay.consume(("expired",), expires_at=5, now=3)

    with pytest.raises(EmploymentAuthError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
        replay.consume(("replacement",), expires_at=5, now=3)
