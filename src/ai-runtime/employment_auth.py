"""ADR-046 authentication for the AIR employment proposal boundary."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Request

PEER_CERTIFICATE_STATE_KEY = "adr046.peer_certificate_der"  # gitleaks:allow - ASGI scope key, not a credential
MAX_ENVELOPE_LIFETIME_SECONDS = 60


class EmploymentAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteGrant:
    caller_uri: str
    target_audience: str
    method: str
    route: str
    operation: str
    contract_major: int


@dataclass(frozen=True)
class DelegatedContext:
    schema_version: str
    key_id: str
    issuer_uri: str
    target_audience: str
    method: str
    route: str
    operation: str
    contract_major: int
    actor_subject: str
    actor_source: str
    effective_role: str
    tenant_id: str
    relationship_id: str
    purpose: str
    subject_reference: str
    request_digest: str
    command_id: str
    idempotency_key: str | None
    expected_versions: Mapping[str, str]
    issued_at: int
    not_before: int
    expires_at: int
    envelope_id: str
    correlation_id: str


def _decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError as error:
        raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED") from error


def _canonical_context(context: DelegatedContext) -> bytes:
    return json.dumps(asdict(context), ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()


class ReplayStore:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, ...], int] = {}
        self._lock = Lock()

    def consume(self, binding: tuple[str, ...], expires_at: int, now: int) -> None:
        with self._lock:
            self._entries = {key: expiry for key, expiry in self._entries.items() if expiry > now}
            if binding in self._entries:
                raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
            self._entries[binding] = expires_at


class EmploymentWorkloadAuth:
    def __init__(
        self,
        grants: frozenset[RouteGrant],
        public_keys: Mapping[tuple[str, str], ec.EllipticCurvePublicKey],
        trust_domain: str,
        audience: str,
        replay_store: ReplayStore | None = None,
        now: Callable[[], int] | None = None,
    ) -> None:
        self._grants = grants
        self._public_keys = public_keys
        self._replay_store = replay_store or ReplayStore()
        self._now = now or (lambda: int(datetime.now(timezone.utc).timestamp()))
        self.trust_domain = trust_domain
        self.audience = audience

    @classmethod
    def from_credentials(cls, credentials: Path) -> EmploymentWorkloadAuth:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        target = manifest["workloads"]["ai-runtime"]
        caller = manifest["workloads"]["professional-runtime"]
        certificate = x509.load_pem_x509_certificate(
            (credentials / "workloads" / "professional-runtime" / "delegation-cert.pem").read_bytes()
        )
        public_key = certificate.public_key()
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise ValueError("BP delegation certificate must contain an ECDSA public key")
        grants = frozenset(
            RouteGrant(
                caller_uri=manifest["workloads"][grant["caller"]]["identity_uri"],
                target_audience=target["audience"],
                method=grant["method"],
                route=grant["route"],
                operation=grant["operation"],
                contract_major=int(grant["contract_major"]),
            )
            for grant in manifest["route_grants"]
            if grant["target"] == "ai-runtime"
        )
        return cls(
            grants,
            {(caller["identity_uri"], caller["delegation_key_id"]): public_key},
            manifest["trust_domain"],
            target["audience"],
        )

    def authorize(
        self,
        request: Request,
        route: str,
        operation: str,
        request_digest: str,
        relationship_id: str | None,
        idempotency_key: str | None,
    ) -> DelegatedContext:
        certificate_der = request.scope.get("state", {}).get(PEER_CERTIFICATE_STATE_KEY)
        authorization = request.headers.get("Authorization", "")
        if certificate_der is None or not authorization.startswith("Bearer "):
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        try:
            certificate = x509.load_der_x509_certificate(certificate_der)
        except ValueError as error:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED") from error
        peer_identity = self._peer_identity(certificate)
        try:
            payload_part, signature_part = authorization.removeprefix("Bearer ").split(".", maxsplit=1)
            payload = _decode(payload_part)
            context = DelegatedContext(**json.loads(payload))
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED") from error
        if payload != _canonical_context(context):
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        public_key = self._public_keys.get((context.issuer_uri, context.key_id))
        if public_key is None:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        try:
            public_key.verify(_decode(signature_part), payload, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as error:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED") from error
        grant = RouteGrant(peer_identity, self.audience, request.method, route, operation, 1)
        now = self._now()
        correlation_id = request.headers.get("X-Correlation-Id", "")
        exact = (
            grant in self._grants
            and context.schema_version == "1.0"
            and context.issuer_uri == peer_identity
            and context.target_audience == self.audience
            and context.method == request.method
            and context.route == route
            and context.operation == operation
            and context.contract_major == 1
            and context.request_digest == request_digest
            and context.actor_source == "BP_SESSION"
            and (relationship_id is None or context.relationship_id == relationship_id)
            and bool(context.tenant_id)
            and bool(context.actor_subject)
            and context.correlation_id == correlation_id
            and (idempotency_key is None or context.idempotency_key == idempotency_key)
            and context.not_before <= now < context.expires_at
            and context.issued_at <= now
            and 0 < context.expires_at - context.issued_at <= MAX_ENVELOPE_LIFETIME_SECONDS
        )
        if not exact:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        self._replay_store.consume(
            (
                peer_identity,
                self.audience,
                context.envelope_id,
                operation,
                context.tenant_id,
                context.relationship_id,
                request_digest,
            ),
            context.expires_at,
            now,
        )
        return context

    def _peer_identity(self, certificate: x509.Certificate) -> str:
        now = datetime.now(timezone.utc)
        if now < certificate.not_valid_before_utc or now >= certificate.not_valid_after_utc:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        try:
            names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
                x509.UniformResourceIdentifier
            )
        except x509.ExtensionNotFound as error:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED") from error
        prefix = f"spiffe://{self.trust_domain}/workload/"
        if len(names) != 1 or not names[0].startswith(prefix) or "*" in names[0]:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        return names[0]


def request_digest(value: object | None) -> str:
    payload = b"" if value is None else json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()
