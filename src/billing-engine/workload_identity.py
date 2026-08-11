"""ADR-046 workload identity verification for the Billing Engine private listener."""

# Implements: ADR-046 sections 3, 5, and 6
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtensionOID

MAX_ENVELOPE_LIFETIME_SECONDS = 60
PEER_CERTIFICATE_STATE_KEY = "adr046.peer_certificate_der"


class ServiceAuthError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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


def _decode(payload: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    except ValueError as exc:
        raise ServiceAuthError("DELEGATED_CONTEXT_INVALID") from exc


def _canonical_payload(context: DelegatedContext) -> bytes:
    return json.dumps(asdict(context), ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()


def extract_peer_identity(
    certificate: x509.Certificate,
    trust_domain: str,
    revoked_serials: frozenset[int] = frozenset(),
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(timezone.utc)
    if certificate.serial_number in revoked_serials:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    if current < certificate.not_valid_before_utc or current >= certificate.not_valid_after_utc:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    try:
        names = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value.get_values_for_type(x509.UniformResourceIdentifier)
    except x509.ExtensionNotFound as exc:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED") from exc
    expected_prefix = f"spiffe://{trust_domain}/workload/"
    if len(names) != 1 or not names[0].startswith(expected_prefix) or "*" in names[0]:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    return names[0]


class ReplayStore:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, ...], int] = {}
        self._lock = Lock()

    def consume(self, binding: tuple[str, ...], expires_at: int, now: int) -> None:
        with self._lock:
            self._entries = {key: expiry for key, expiry in self._entries.items() if expiry > now}
            if binding in self._entries:
                raise ServiceAuthError("DELEGATED_CONTEXT_REPLAYED")
            self._entries[binding] = expires_at


class DelegatedContextVerifier:
    def __init__(
        self,
        grants: frozenset[RouteGrant],
        public_keys: Mapping[tuple[str, str], ec.EllipticCurvePublicKey],
        replay_store: ReplayStore,
        now: Callable[[], int] | None = None,
    ) -> None:
        self._grants = grants
        self._public_keys = public_keys
        self._replay_store = replay_store
        self._now = now or (lambda: int(datetime.now(timezone.utc).timestamp()))

    def verify(
        self,
        token: str,
        peer_identity_uri: str,
        target_audience: str,
        method: str,
        route: str,
        operation: str,
        contract_major: int,
        request_digest: str,
        rebind: Callable[[DelegatedContext], bool],
    ) -> DelegatedContext:
        try:
            payload_part, signature_part = token.split(".", maxsplit=1)
            payload = _decode(payload_part)
            context = DelegatedContext(**json.loads(payload))
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID") from exc
        if payload != _canonical_payload(context):
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        public_key = self._public_keys.get((context.issuer_uri, context.key_id))
        if public_key is None:
            raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
        try:
            public_key.verify(_decode(signature_part), payload, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as exc:
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID") from exc
        grant = RouteGrant(peer_identity_uri, target_audience, method.upper(), route, operation, contract_major)
        if grant not in self._grants:
            raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")
        now = self._now()
        exact = (
            context.schema_version == "1.0"
            and context.issuer_uri == peer_identity_uri
            and context.target_audience == target_audience
            and context.method == method.upper()
            and context.route == route
            and context.operation == operation
            and context.contract_major == contract_major
            and context.request_digest == request_digest
            and context.actor_source == "BP_SESSION"
            and context.not_before <= now < context.expires_at
            and context.issued_at <= now
            and 0 < context.expires_at - context.issued_at <= MAX_ENVELOPE_LIFETIME_SECONDS
        )
        if not exact:
            raise ServiceAuthError(
                "DELEGATED_CONTEXT_EXPIRED" if now >= context.expires_at else "DELEGATED_CONTEXT_INVALID"
            )
        if not rebind(context):
            raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")
        self._replay_store.consume(
            (peer_identity_uri, target_audience, context.envelope_id, operation,
             context.tenant_id, context.relationship_id, request_digest),
            context.expires_at,
            now,
        )
        return context