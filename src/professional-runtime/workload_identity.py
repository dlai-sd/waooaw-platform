"""ADR-046 workload identity and delegated-context verification primitives."""

# Implements: ADR-046 sections 3, 5, and 6
# constitutional_basis: C-001, C-023, C-026, C-059, C-063, C-083, C-084, C-085

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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.x509.oid import ExtendedKeyUsageOID, ObjectIdentifier


MAX_ENVELOPE_LIFETIME_SECONDS = 60
PEER_CERTIFICATE_STATE_KEY = "adr046.peer_certificate_der"
DELEGATION_SIGNING_OID = ObjectIdentifier("1.3.6.1.4.1.55555.46.1")


class ServiceAuthError(RuntimeError):
    """Privacy-safe service authentication or authorization failure."""

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


def _encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _decode(payload: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    except ValueError as exc:
        raise ServiceAuthError("DELEGATED_CONTEXT_INVALID") from exc


def _canonical_payload(context: DelegatedContext) -> bytes:
    return json.dumps(
        asdict(context),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


DelegationPrivateKey = Ed25519PrivateKey | ec.EllipticCurvePrivateKey
DelegationPublicKey = Ed25519PublicKey | ec.EllipticCurvePublicKey


def sign_delegated_context(context: DelegatedContext, private_key: DelegationPrivateKey) -> str:
    """Create a deterministic compact envelope using a distinct asymmetric key."""
    payload = _canonical_payload(context)
    signature = (
        private_key.sign(payload)
        if isinstance(private_key, Ed25519PrivateKey)
        else private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
    )
    return f"{_encode(payload)}.{_encode(signature)}"


def extract_peer_identity(
    certificate: x509.Certificate,
    trust_domain: str,
    revoked_serials: frozenset[int] = frozenset(),
    now: datetime | None = None,
) -> str:
    """Extract one exact environment-scoped SPIFFE URI SAN from a TLS-authenticated peer."""
    current = now or datetime.now(timezone.utc)
    if certificate.serial_number in revoked_serials:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    if current < certificate.not_valid_before_utc or current >= certificate.not_valid_after_utc:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    try:
        names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
            x509.UniformResourceIdentifier
        )
    except x509.ExtensionNotFound as exc:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED") from exc
    expected_prefix = f"spiffe://{trust_domain}/workload/"
    if len(names) != 1 or not names[0].startswith(expected_prefix) or "*" in names[0]:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    return names[0]


def certificate_uris(certificate: x509.Certificate) -> list[str]:
    try:
        return certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
            x509.UniformResourceIdentifier
        )
    except x509.ExtensionNotFound:
        return []


def has_extended_key_usage(certificate: x509.Certificate, usage: ObjectIdentifier) -> bool:
    try:
        return usage in certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    except x509.ExtensionNotFound:
        return False


def _within(certificate: x509.Certificate, current: datetime) -> bool:
    return certificate.not_valid_before_utc <= current < certificate.not_valid_after_utc


def is_ca_certificate(certificate: x509.Certificate) -> bool:
    try:
        return certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    except x509.ExtensionNotFound:
        return False


def issued_by(certificate: x509.Certificate, issuer: x509.Certificate) -> bool:
    try:
        certificate.verify_directly_issued_by(issuer)
    except (ValueError, TypeError, InvalidSignature):
        return False
    return True


@dataclass(frozen=True)
class TrustAnchors:
    """Roots and intermediates of the current trust bundle with its revocations."""

    roots: tuple[x509.Certificate, ...]
    intermediates: tuple[x509.Certificate, ...]
    revoked_serials: frozenset[int] = frozenset()
    revoked_identity_uris: frozenset[str] = frozenset()

    def is_revoked(self, certificate: x509.Certificate) -> bool:
        return certificate.serial_number in self.revoked_serials or any(
            uri in self.revoked_identity_uris for uri in certificate_uris(certificate)
        )

    def _intermediate_valid(self, intermediate: x509.Certificate, current: datetime) -> bool:
        return (
            is_ca_certificate(intermediate)
            and _within(intermediate, current)
            and any(is_ca_certificate(root) and _within(root, current) and issued_by(intermediate, root) for root in self.roots)
        )

    def chains(self, certificate: x509.Certificate, current: datetime) -> bool:
        """True when a non-CA certificate is valid now, not revoked and issued by a valid intermediate of these roots."""
        if is_ca_certificate(certificate) or not _within(certificate, current) or self.is_revoked(certificate):
            return False
        return any(
            issued_by(certificate, intermediate) and self._intermediate_valid(intermediate, current)
            for intermediate in self.intermediates
        )


@dataclass(frozen=True)
class DelegationKey:
    public_key: DelegationPublicKey
    certificate: x509.Certificate
    activate_after: int = 0


DelegationKeys = Mapping[tuple[str, str], DelegationPublicKey | DelegationKey]


def delegation_key_usable(entry: DelegationPublicKey | DelegationKey, anchors: TrustAnchors | None, now: int) -> bool:
    if not isinstance(entry, DelegationKey):
        return True
    current = datetime.fromtimestamp(now, timezone.utc)
    return (
        anchors is not None
        and now >= entry.activate_after
        and has_extended_key_usage(entry.certificate, DELEGATION_SIGNING_OID)
        and anchors.chains(entry.certificate, current)
    )


def peer_certificate_trusted(certificate: x509.Certificate, anchors: TrustAnchors, current: datetime) -> bool:
    """Application-level check that the TLS peer chains to the current roots with client authentication."""
    return anchors.chains(certificate, current) and has_extended_key_usage(certificate, ExtendedKeyUsageOID.CLIENT_AUTH)


class ReplayStore:
    """Bounded in-process replay state; production adapters may supply durable storage."""

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
    """Verify ADR-046 route policy and delegated context after TLS authenticates the peer."""

    def __init__(
        self,
        grants: frozenset[RouteGrant] | Callable[[], frozenset[RouteGrant]],
        public_keys: DelegationKeys | Callable[[], DelegationKeys],
        replay_store: ReplayStore,
        now: Callable[[], int] | None = None,
        anchors: Callable[[], TrustAnchors | None] | None = None,
    ) -> None:
        self._grants = grants if callable(grants) else (lambda: grants)
        self._public_keys = public_keys if callable(public_keys) else (lambda: public_keys)
        self._anchors = anchors or (lambda: None)
        self._replay_store = replay_store
        self._now = now or (lambda: int(datetime.now(timezone.utc).timestamp()))

    def authorize_peer(
        self, peer_identity_uri: str, target_audience: str, method: str, route: str, operation: str, contract_major: int
    ) -> None:
        grant = RouteGrant(peer_identity_uri, target_audience, method.upper(), route, operation, contract_major)
        if grant not in self._grants():
            raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")

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
            raw = json.loads(payload)
            context = DelegatedContext(**raw)
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID") from exc
        if payload != _canonical_payload(context):
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")

        now = self._now()
        entry = self._public_keys().get((context.issuer_uri, context.key_id))
        if entry is None or not delegation_key_usable(entry, self._anchors(), now):
            raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
        public_key = entry.public_key if isinstance(entry, DelegationKey) else entry
        try:
            signature = _decode(signature_part)
            if isinstance(public_key, Ed25519PublicKey):
                public_key.verify(signature, payload)
            else:
                public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as exc:
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID") from exc

        self.authorize_peer(peer_identity_uri, target_audience, method, route, operation, contract_major)

        exact_binding = (
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
        if not exact_binding:
            code = "DELEGATED_CONTEXT_EXPIRED" if now >= context.expires_at else "DELEGATED_CONTEXT_INVALID"
            raise ServiceAuthError(code)
        if not rebind(context):
            raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")

        replay_binding = (
            peer_identity_uri,
            target_audience,
            context.envelope_id,
            operation,
            context.tenant_id,
            context.relationship_id,
            request_digest,
        )
        self._replay_store.consume(replay_binding, context.expires_at, now)
        return context
