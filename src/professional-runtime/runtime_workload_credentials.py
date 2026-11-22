"""ADR-046 Amendment 1 credential source: Key Vault or directory delivery with verified in-process swap."""

# Implements: ADR-046 sections 4.1, 4.2, 5.1, 5.2 and 12.2 D4-D6; workload-identity-cloud-issuance-contract.md section 8
# constitutional_basis: C-001, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID

from workload_identity import (
    DELEGATION_SIGNING_OID,
    DelegationKey,
    DelegationKeys,
    RouteGrant,
    ServiceAuthError,
    TrustAnchors,
    certificate_uris,
    extract_peer_identity,
    has_extended_key_usage,
    is_ca_certificate,
    issued_by,
    peer_certificate_trusted,
)

SOURCE_DIRECTORY = "directory"
SOURCE_KEYVAULT = "keyvault"
STATE_READY = "READY"
STATE_UNAVAILABLE = "UNAVAILABLE"
STATE_UNISSUED = "UNISSUED"
SCHEMA_VERSION = "1.1"
TRUST_BUNDLE_SECRET = "wid-trust-bundle"  # noqa: S105
UNISSUED_SENTINEL = "UNISSUED"
VAULT_HOST_SUFFIX = ".vault.azure.net"
VAULT_API_VERSION = "7.4"
IDENTITY_API_VERSION = "2019-08-01"
DEFAULT_REFRESH_SECONDS = 300
MIN_REFRESH_SECONDS = 30
CLOCK_SKEW = timedelta(seconds=60)
MAX_RESPONSE_BYTES = 262_144
TARGET_WORKLOAD = "professional-runtime"

logger = logging.getLogger(__name__)


class CredentialError(RuntimeError):
    """Credential load failure carrying only a stable, secret-free reason code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CredentialSnapshot:
    source: str
    workload: str
    environment: str
    trust_domain: str
    identity_uri: str
    audience: str
    bundle_version: int
    workload_bundle_version: int
    serial: int
    not_after: datetime
    anchors: TrustAnchors
    ca_bundle_pem: str = field(repr=False)
    grants: frozenset[RouteGrant]
    delegation_keys: Mapping[tuple[str, str], DelegationKey]
    tls_key_pem: bytes = field(default=b"", repr=False)
    tls_chain_pem: str = field(default="", repr=False)
    delegation_key_pem: bytes | None = field(default=None, repr=False)
    delegation_cert_pem: str | None = field(default=None, repr=False)
    delegation_key_id: str | None = None
    delegation_activate_after: int = 0

    @property
    def serial_digest(self) -> str:
        return hashlib.sha256(str(self.serial).encode("ascii")).hexdigest()[:16]


@dataclass(frozen=True)
class TrustBundle:
    bundle_version: int
    environment: str
    trust_domain: str
    anchors: TrustAnchors
    manifest: Mapping[str, Any]
    ca_bundle_pem: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _skewed(certificate: x509.Certificate, now: datetime) -> datetime:
    start = certificate.not_valid_before_utc
    return start if now < start <= now + CLOCK_SKEW else now


def _within(certificate: x509.Certificate, now: datetime) -> bool:
    return certificate.not_valid_before_utc <= now < certificate.not_valid_after_utc


def _text(document: Mapping[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise CredentialError("SCHEMA_INVALID")
    return value


def _integer(document: Mapping[str, Any], key: str) -> int:
    value = document.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CredentialError("SCHEMA_INVALID")
    return value


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CredentialError("SCHEMA_INVALID")
    return value


def _document(raw: str) -> Mapping[str, Any]:
    if raw.strip() == UNISSUED_SENTINEL:
        raise CredentialError("UNISSUED")
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise CredentialError("UNISSUED") from exc
    if not isinstance(document, dict) or "schema_version" not in document:
        raise CredentialError("UNISSUED")
    if document["schema_version"] != SCHEMA_VERSION:
        raise CredentialError("SCHEMA_INVALID")
    return document


def _certificates(pem: object) -> list[x509.Certificate]:
    if not isinstance(pem, str) or not pem:
        raise CredentialError("SCHEMA_INVALID")
    try:
        certificates = x509.load_pem_x509_certificates(pem.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialError("SCHEMA_INVALID") from exc
    if not certificates:
        raise CredentialError("SCHEMA_INVALID")
    return certificates


def _one_certificate(pem: object) -> x509.Certificate:
    certificates = _certificates(pem)
    if len(certificates) != 1:
        raise CredentialError("SCHEMA_INVALID")
    return certificates[0]


def _decimal_set(values: object) -> frozenset[int]:
    if not isinstance(values, list):
        raise CredentialError("SCHEMA_INVALID")
    try:
        return frozenset(int(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise CredentialError("SCHEMA_INVALID") from exc


def _text_set(values: object) -> frozenset[str]:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise CredentialError("SCHEMA_INVALID")
    return frozenset(values)


def _epoch(value: object) -> int:
    if value is None:
        return 0
    if not isinstance(value, str):
        raise CredentialError("SCHEMA_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CredentialError("SCHEMA_INVALID") from exc
    if parsed.tzinfo is None:
        raise CredentialError("SCHEMA_INVALID")
    return int(parsed.timestamp())


def _spki(public_key: Any) -> bytes:
    return bytes(public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo))


def _anchors(
    root: x509.Certificate,
    ca_certificates: list[x509.Certificate],
    intermediate: x509.Certificate,
    revoked_serials: frozenset[int],
    revoked_uris: frozenset[str],
    now: datetime,
) -> TrustAnchors:
    roots = [root]
    intermediates = [intermediate]
    for certificate in ca_certificates:
        if certificate in roots or certificate in intermediates or not is_ca_certificate(certificate):
            continue
        if issued_by(certificate, certificate):
            if _within(certificate, now):
                roots.append(certificate)
        else:
            intermediates.append(certificate)
    return TrustAnchors(tuple(roots), tuple(intermediates), revoked_serials, revoked_uris)


def verify_trust_bundle(raw: str, trust_domain: str, environment: str | None, now: datetime) -> TrustBundle:
    """Verify signature, chain, environment and trust domain of the public signed trust bundle."""
    document = _document(raw)
    bundle_version = _integer(document, "bundle_version")
    bundle_environment = _text(document, "environment")
    if _text(document, "trust_domain") != trust_domain:
        raise CredentialError("TRUST_DOMAIN_MISMATCH")
    if environment is not None and bundle_environment != environment:
        raise CredentialError("ENVIRONMENT_MISMATCH")
    manifest = _mapping(document.get("manifest"))
    if manifest.get("environment") != bundle_environment or manifest.get("trust_domain") != trust_domain:
        raise CredentialError("ENVIRONMENT_MISMATCH")

    root = _one_certificate(document.get("root_pem"))
    intermediate = _one_certificate(document.get("intermediate_pem"))
    if not (is_ca_certificate(root) and issued_by(root, root) and _within(root, now)):
        raise CredentialError("TRUST_BUNDLE_CHAIN_INVALID")
    if not (is_ca_certificate(intermediate) and issued_by(intermediate, root) and _within(intermediate, now)):
        raise CredentialError("TRUST_BUNDLE_CHAIN_INVALID")
    public_key = intermediate.public_key()
    signature = document.get("signature")
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(signature, str):
        raise CredentialError("TRUST_BUNDLE_SIGNATURE_INVALID")
    unsigned = {key: value for key, value in document.items() if key != "signature"}
    try:
        public_key.verify(base64.b64decode(signature, validate=True), canonical_json(unsigned), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, binascii.Error, ValueError) as exc:
        raise CredentialError("TRUST_BUNDLE_SIGNATURE_INVALID") from exc

    ca_bundle_pem = _text(document, "ca_bundle_pem")
    anchors = _anchors(
        root,
        _certificates(ca_bundle_pem),
        intermediate,
        _decimal_set(document.get("revoked_serials", [])),
        _text_set(document.get("revoked_identity_uris", [])),
        now,
    )
    return TrustBundle(bundle_version, bundle_environment, trust_domain, anchors, manifest, ca_bundle_pem)


def _workload_record(manifest: Mapping[str, Any], name: str, trust_domain: str) -> Mapping[str, Any]:
    record = _mapping(_mapping(manifest.get("workloads")).get(name))
    identity_uri = record.get("identity_uri")
    if not isinstance(identity_uri, str) or not identity_uri.startswith(f"spiffe://{trust_domain}/workload/"):
        raise CredentialError("MANIFEST_INVALID")
    return record


def grants_for(manifest: Mapping[str, Any], target: str, trust_domain: str) -> frozenset[RouteGrant]:
    workloads = _mapping(manifest.get("workloads"))
    grants = manifest.get("route_grants")
    if not isinstance(grants, list):
        raise CredentialError("MANIFEST_INVALID")
    try:
        return frozenset(
            RouteGrant(
                caller_uri=_workload_record(manifest, grant["caller"], trust_domain)["identity_uri"],
                target_audience=str(workloads[grant["target"]]["audience"]),
                method=str(grant["method"]).upper(),
                route=str(grant["route"]),
                operation=str(grant["operation"]),
                contract_major=int(grant["contract_major"]),
            )
            for grant in grants
            if grant["target"] == target
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CredentialError("MANIFEST_INVALID") from exc


def delegation_key_from_certificate(
    certificate: x509.Certificate,
    identity_uri: str,
    anchors: TrustAnchors,
    activate_after: int,
    now: datetime,
) -> DelegationKey:
    if not has_extended_key_usage(certificate, DELEGATION_SIGNING_OID):
        raise CredentialError("DELEGATION_USAGE_INVALID")
    if not anchors.chains(certificate, _skewed(certificate, now)):
        raise CredentialError("DELEGATION_CHAIN_INVALID")
    if certificate_uris(certificate) != [identity_uri]:
        raise CredentialError("DELEGATION_IDENTITY_MISMATCH")
    public_key = certificate.public_key()
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise CredentialError("DELEGATION_USAGE_INVALID")
    return DelegationKey(public_key, certificate, activate_after)


def _published_delegation_keys(
    manifest: Mapping[str, Any], anchors: TrustAnchors, trust_domain: str, now: datetime
) -> dict[tuple[str, str], DelegationKey]:
    keys: dict[tuple[str, str], DelegationKey] = {}
    for name, record in _mapping(manifest.get("workloads")).items():
        identity_uri = str(_workload_record(manifest, name, trust_domain)["identity_uri"])
        published = record.get("delegation_certificates", [])
        if not isinstance(published, list):
            raise CredentialError("MANIFEST_INVALID")
        for entry in published:
            entry = _mapping(entry)
            certificate = _one_certificate(entry.get("certificate_pem"))
            if anchors.is_revoked(certificate) or certificate.not_valid_after_utc <= now:
                continue
            keys[(identity_uri, _text(entry, "key_id"))] = delegation_key_from_certificate(
                certificate, identity_uri, anchors, _epoch(entry.get("activate_after")), now
            )
    return keys


def _signing_material(
    bundle: Mapping[str, Any], identity_uri: str, anchors: TrustAnchors, now: datetime
) -> tuple[bytes | None, str | None, str | None, int]:
    key_pem = bundle.get("delegation_key_pem")
    if key_pem is None:
        return None, None, None, 0
    certificate_pem = _text(bundle, "delegation_cert_pem")
    key_id = _text(bundle, "delegation_key_id")
    activate_after = _epoch(bundle.get("delegation_activate_after"))
    certificate = _one_certificate(certificate_pem)
    delegation_key_from_certificate(certificate, identity_uri, anchors, activate_after, now)
    try:
        private_key = serialization.load_pem_private_key(str(key_pem).encode("ascii"), None)
    except (ValueError, TypeError) as exc:
        raise CredentialError("DELEGATION_KEY_MISMATCH") from exc
    if _spki(private_key.public_key()) != _spki(certificate.public_key()):
        raise CredentialError("DELEGATION_KEY_MISMATCH")
    return str(key_pem).encode("ascii"), certificate_pem, key_id, activate_after


def build_snapshot(trust: TrustBundle, raw: str, workload: str, now: datetime) -> CredentialSnapshot:
    """Verify one private workload bundle against the verified trust bundle; raise before any swap."""
    bundle = _document(raw)
    if _text(bundle, "environment") != trust.environment or _text(bundle, "workload") != workload:
        raise CredentialError("ENVIRONMENT_MISMATCH")
    record = _workload_record(trust.manifest, workload, trust.trust_domain)
    identity_uri = str(record["identity_uri"])
    if _text(bundle, "identity_uri") != identity_uri:
        raise CredentialError("LEAF_IDENTITY_MISMATCH")
    chain = _certificates(bundle.get("tls_cert_pem"))
    leaf = chain[0]
    anchors = trust.anchors
    if anchors.is_revoked(leaf):
        raise CredentialError("LEAF_REVOKED")
    if not _within(leaf, _skewed(leaf, now)):
        raise CredentialError("LEAF_VALIDITY_INVALID")
    if certificate_uris(leaf) != [identity_uri]:
        raise CredentialError("LEAF_IDENTITY_MISMATCH")
    if not (
        has_extended_key_usage(leaf, ExtendedKeyUsageOID.CLIENT_AUTH)
        and has_extended_key_usage(leaf, ExtendedKeyUsageOID.SERVER_AUTH)
    ):
        raise CredentialError("LEAF_USAGE_INVALID")
    if not anchors.chains(leaf, _skewed(leaf, now)):
        raise CredentialError("LEAF_CHAIN_INVALID")
    key_pem = _text(bundle, "tls_key_pem").encode("ascii")
    try:
        private_key = serialization.load_pem_private_key(key_pem, None)
    except (ValueError, TypeError) as exc:
        raise CredentialError("LEAF_KEY_MISMATCH") from exc
    if _spki(private_key.public_key()) != _spki(leaf.public_key()):
        raise CredentialError("LEAF_KEY_MISMATCH")

    keys = _published_delegation_keys(trust.manifest, anchors, trust.trust_domain, now)
    signing_key, signing_certificate, signing_key_id, signing_activate_after = _signing_material(
        bundle, identity_uri, anchors, now
    )
    return CredentialSnapshot(
        source=SOURCE_KEYVAULT,
        workload=workload,
        environment=trust.environment,
        trust_domain=trust.trust_domain,
        identity_uri=identity_uri,
        audience=str(record.get("audience") or ""),
        bundle_version=trust.bundle_version,
        workload_bundle_version=_integer(bundle, "bundle_version"),
        serial=leaf.serial_number,
        not_after=leaf.not_valid_after_utc,
        anchors=anchors,
        ca_bundle_pem=trust.ca_bundle_pem,
        grants=grants_for(trust.manifest, workload, trust.trust_domain),
        delegation_keys=keys,
        tls_key_pem=key_pem,
        tls_chain_pem="".join(certificate.public_bytes(serialization.Encoding.PEM).decode("ascii") for certificate in chain),
        delegation_key_pem=signing_key,
        delegation_cert_pem=signing_certificate,
        delegation_key_id=signing_key_id,
        delegation_activate_after=signing_activate_after,
    )


def load_directory_snapshot(credentials: Path, workload: str, now: datetime | None = None) -> CredentialSnapshot:
    """Load development and CI credentials exactly as delivered; delegation certificates are chain-checked."""
    current = now or _utcnow()
    manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
    trust_domain = str(manifest["trust_domain"])
    record = _workload_record(manifest, workload, trust_domain)
    ca_certificates = _certificates((credentials / "trust" / "ca-bundle.pem").read_text(encoding="ascii"))
    roots = tuple(c for c in ca_certificates if is_ca_certificate(c) and issued_by(c, c))
    anchors = TrustAnchors(roots, tuple(c for c in ca_certificates if c not in roots))
    keys: dict[tuple[str, str], DelegationKey] = {}
    for name, entry in _mapping(manifest.get("workloads")).items():
        certificate_path = credentials / "workloads" / name / "delegation-cert.pem"
        if "delegation_key_id" not in entry or not certificate_path.is_file():
            continue
        certificate = _one_certificate(certificate_path.read_text(encoding="ascii"))
        if certificate.not_valid_after_utc <= current:
            continue
        identity_uri = str(_workload_record(manifest, name, trust_domain)["identity_uri"])
        keys[(identity_uri, str(entry["delegation_key_id"]))] = delegation_key_from_certificate(
            certificate, identity_uri, anchors, 0, current
        )
    leaf = _certificates((credentials / "workloads" / workload / "tls-cert.pem").read_text(encoding="ascii"))[0]
    return CredentialSnapshot(
        source=SOURCE_DIRECTORY,
        workload=workload,
        environment=str(manifest["environment"]),
        trust_domain=trust_domain,
        identity_uri=str(record["identity_uri"]),
        audience=str(record["audience"]),
        bundle_version=0,
        workload_bundle_version=0,
        serial=leaf.serial_number,
        not_after=leaf.not_valid_after_utc,
        anchors=anchors,
        ca_bundle_pem="".join(c.public_bytes(serialization.Encoding.PEM).decode("ascii") for c in ca_certificates),
        grants=grants_for(manifest, workload, trust_domain),
        delegation_keys=keys,
    )


HttpGet = Callable[[str, Mapping[str, str], float], tuple[int, bytes]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _http_get(url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, bytes]:
    if not url.startswith(("https://", "http://")):
        raise CredentialError("CONFIG_INVALID")
    request = urllib.request.Request(url, headers=dict(headers), method="GET")  # noqa: S310
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return int(response.status), bytes(response.read(MAX_RESPONSE_BYTES + 1))
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise CredentialError("VAULT_UNAVAILABLE") from exc


def validate_vault_url(vault_url: str) -> str:
    """Return the normalized vault origin; only https hosts under .vault.azure.net are accepted."""
    parsed = urllib.parse.urlsplit(vault_url.strip())
    host = parsed.hostname or ""
    name = host.removesuffix(VAULT_HOST_SUFFIX)
    if (
        parsed.scheme != "https"
        or not host.endswith(VAULT_HOST_SUFFIX)
        or not name
        or "." in name
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise CredentialError("CONFIG_INVALID")
    return f"https://{host}"


class KeyVaultSecretReader:
    """Read secrets with the Container Apps managed identity over the Key Vault REST API."""

    def __init__(
        self,
        vault_url: str,
        managed_identity_client_id: str | None,
        environ: Mapping[str, str] | None = None,
        http_get: HttpGet | None = None,
        timeout: float = 10.0,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._vault = validate_vault_url(vault_url)
        self._client_id = managed_identity_client_id
        self._environ = os.environ if environ is None else environ
        self._http_get = http_get or _http_get
        self._timeout = timeout
        self._clock = clock
        self._token: str | None = None
        self._token_expiry = datetime.min.replace(tzinfo=timezone.utc)
        self._lock = threading.Lock()

    def _access_token(self) -> str:
        with self._lock:
            now = self._clock()
            if self._token is not None and now + timedelta(minutes=5) < self._token_expiry:
                return self._token
            endpoint = self._environ.get("IDENTITY_ENDPOINT")
            header = self._environ.get("IDENTITY_HEADER")
            if not endpoint or not header:
                raise CredentialError("IDENTITY_UNAVAILABLE")
            query = {"api-version": IDENTITY_API_VERSION, "resource": "https://vault.azure.net"}
            if self._client_id:
                query["client_id"] = self._client_id
            status, body = self._http_get(
                f"{endpoint}?{urllib.parse.urlencode(query)}", {"X-IDENTITY-HEADER": header}, self._timeout
            )
            if status != 200 or len(body) > MAX_RESPONSE_BYTES:
                raise CredentialError("IDENTITY_UNAVAILABLE")
            try:
                payload = json.loads(body)
                token = payload["access_token"]
                expires = datetime.fromtimestamp(int(payload["expires_on"]), timezone.utc)
            except (KeyError, TypeError, ValueError) as exc:
                raise CredentialError("IDENTITY_UNAVAILABLE") from exc
            if not isinstance(token, str) or not token:
                raise CredentialError("IDENTITY_UNAVAILABLE")
            self._token, self._token_expiry = token, expires
            return token

    def get_secret(self, name: str) -> str:
        token = self._access_token()
        status, body = self._http_get(
            f"{self._vault}/secrets/{urllib.parse.quote(name, safe='-')}?api-version={VAULT_API_VERSION}",
            {"Authorization": f"Bearer {token}"},
            self._timeout,
        )
        if status in (401, 403):
            with self._lock:
                self._token = None
            raise CredentialError("VAULT_DENIED")
        if status == 404:
            raise CredentialError("SECRET_NOT_FOUND")
        if status != 200 or len(body) > MAX_RESPONSE_BYTES:
            raise CredentialError("VAULT_UNAVAILABLE")
        try:
            value = json.loads(body)["value"]
        except (KeyError, TypeError, ValueError) as exc:
            raise CredentialError("VAULT_UNAVAILABLE") from exc
        if not isinstance(value, str):
            raise CredentialError("VAULT_UNAVAILABLE")
        return value


class CredentialHolder:
    """Atomically held credential snapshot with verified refresh, state reporting and fail-closed expiry."""

    def __init__(
        self,
        source: str,
        workload: str,
        trust_domain: str,
        environment: str | None = None,
        reader: KeyVaultSecretReader | None = None,
        refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
        clock: Callable[[], datetime] = _utcnow,
        snapshot: CredentialSnapshot | None = None,
        config_error: str | None = None,
    ) -> None:
        self.source = source
        self.workload = workload
        self.trust_domain = trust_domain
        self.environment = environment
        self.refresh_seconds = max(MIN_REFRESH_SECONDS, refresh_seconds)
        self._reader = reader
        self._clock = clock
        self._snapshot = snapshot
        self._enforce_expiry = source != SOURCE_DIRECTORY
        self._trust_version = 0
        self._bundle_version = 0
        self._last_reason: str | None = config_error
        self._reported_state: str | None = None
        self._subscribers: list[Callable[[CredentialSnapshot], None]] = []
        self._refresh_lock = threading.Lock()

    @classmethod
    def static(cls, snapshot: CredentialSnapshot) -> CredentialHolder:
        return cls(snapshot.source, snapshot.workload, snapshot.trust_domain, snapshot=snapshot)

    @property
    def refreshable(self) -> bool:
        return self._reader is not None

    @property
    def enforced(self) -> bool:
        return self._enforce_expiry

    def current(self) -> CredentialSnapshot | None:
        snapshot = self._snapshot
        if snapshot is None or (self._enforce_expiry and snapshot.not_after <= self._clock()):
            return None
        return snapshot

    def state(self) -> str:
        if self.current() is not None:
            return STATE_READY
        if self._snapshot is None and self._last_reason in (None, "UNISSUED"):
            return STATE_UNISSUED
        return STATE_UNAVAILABLE

    def anchors(self) -> TrustAnchors | None:
        snapshot = self.current()
        return None if snapshot is None else snapshot.anchors

    def grants(self) -> frozenset[RouteGrant]:
        snapshot = self.current()
        return frozenset() if snapshot is None else snapshot.grants

    def delegation_keys(self) -> DelegationKeys:
        snapshot = self.current()
        return {} if snapshot is None else snapshot.delegation_keys

    def audience(self) -> str | None:
        snapshot = self.current()
        return None if snapshot is None else snapshot.audience

    def remaining_seconds(self) -> int:
        snapshot = self._snapshot
        return 0 if snapshot is None else max(0, int((snapshot.not_after - self._clock()).total_seconds()))

    def status(self) -> dict[str, object]:
        snapshot = self._snapshot
        return {
            "source": self.source,
            "state": self.state(),
            "serialDigest": None if snapshot is None else snapshot.serial_digest,
            "notAfter": None if snapshot is None else snapshot.not_after.isoformat(),
            "remainingSeconds": self.remaining_seconds(),
            "bundleVersion": None if snapshot is None else snapshot.bundle_version,
            "lastReason": self._last_reason,
        }

    def subscribe(self, callback: Callable[[CredentialSnapshot], None]) -> None:
        self._subscribers.append(callback)
        snapshot = self.current()
        if snapshot is not None:
            callback(snapshot)

    def _report_state(self) -> None:
        state = self.state()
        if state == self._reported_state:
            return
        log = logger.info if state == STATE_READY else logger.warning
        log(
            "workload_credential state_transition from=%s to=%s source=%s reason=%s",
            self._reported_state,
            state,
            self.source,
            self._last_reason,
        )
        self._reported_state = state

    def _reject(self, reason: str) -> None:
        self._last_reason = reason
        logger.warning("workload_credential refresh_rejected source=%s reason=%s", self.source, reason)

    def refresh_once(self) -> bool:
        """Read, verify and swap; on any failure keep the previous snapshot and never raise."""
        reader = self._reader
        if reader is None:
            self._report_state()
            return False
        with self._refresh_lock:
            try:
                now = self._clock()
                trust = verify_trust_bundle(reader.get_secret(TRUST_BUNDLE_SECRET), self.trust_domain, self.environment, now)
                snapshot = build_snapshot(trust, reader.get_secret(f"wid-bundle-{self.workload}"), self.workload, now)
                if trust.bundle_version < self._trust_version or snapshot.workload_bundle_version < self._bundle_version:
                    raise CredentialError("BUNDLE_VERSION_ROLLBACK")
            except CredentialError as exc:
                self._reject(exc.code)
                self._report_state()
                return False
            except Exception:
                self._reject("REFRESH_FAILED")
                self._report_state()
                return False
            previous = self._snapshot
            self._snapshot = snapshot
            self._trust_version = trust.bundle_version
            self._bundle_version = snapshot.workload_bundle_version
            self._last_reason = None
        if previous is None or previous.serial != snapshot.serial:
            logger.info(
                "workload_credential swapped source=%s serial_digest=%s bundle_version=%s remaining_seconds=%s",
                self.source,
                snapshot.serial_digest,
                snapshot.bundle_version,
                self.remaining_seconds(),
            )
        self._report_state()
        for callback in list(self._subscribers):
            try:
                callback(snapshot)
            except Exception:
                logger.warning("workload_credential subscriber_failed source=%s", self.source)
        return True

    async def run(self, stop: asyncio.Event) -> None:
        """Refresh until stopped; a failed cycle never ends the loop."""
        while not stop.is_set():
            await asyncio.to_thread(self.refresh_once)
            interval = float(self.refresh_seconds if self._snapshot is not None else MIN_REFRESH_SECONDS)
            if self._snapshot is not None and self._enforce_expiry:
                interval = min(interval, max(1.0, self.remaining_seconds() + 1.0))
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=interval)


def authenticate_peer(holder: CredentialHolder, certificate: x509.Certificate, now: datetime | None = None) -> str:
    """Authenticate a TLS peer against the CURRENT trust bundle: chain, validity, client auth, exact URI SAN, revocation."""
    snapshot = holder.current()
    if snapshot is None:
        raise ServiceAuthError("SERVICE_IDENTITY_UNAVAILABLE")
    current = now or _utcnow()
    identity = extract_peer_identity(certificate, snapshot.trust_domain, snapshot.anchors.revoked_serials, current)
    if not peer_certificate_trusted(certificate, snapshot.anchors, current):
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    return identity


_shared_holder: CredentialHolder | None = None


def register_holder(holder: CredentialHolder | None) -> None:
    global _shared_holder
    _shared_holder = holder


def shared_holder() -> CredentialHolder | None:
    return _shared_holder


def credential_holder_from_environment(environ: Mapping[str, str] | None = None) -> CredentialHolder | None:
    """Select the credential source; configuration faults yield an UNAVAILABLE holder, never a crash."""
    env = os.environ if environ is None else environ
    source = env.get("WAOOAW_WID_SOURCE", SOURCE_DIRECTORY).strip().lower() or SOURCE_DIRECTORY
    if source == SOURCE_DIRECTORY:
        path = env.get("WAOOAW_WORKLOAD_CREDENTIALS")
        if not path:
            return None
        return CredentialHolder.static(load_directory_snapshot(Path(path), TARGET_WORKLOAD))
    trust_domain = env.get("WAOOAW_WID_TRUST_DOMAIN", "")
    try:
        if source != SOURCE_KEYVAULT or env.get("WAOOAW_WID_WORKLOAD") != TARGET_WORKLOAD or not trust_domain:
            raise CredentialError("CONFIG_INVALID")
        try:
            refresh_seconds = int(env.get("WAOOAW_WID_REFRESH_SECONDS", DEFAULT_REFRESH_SECONDS))
        except ValueError as exc:
            raise CredentialError("CONFIG_INVALID") from exc
        reader = KeyVaultSecretReader(
            env.get("WAOOAW_WID_VAULT_URL", ""),
            env.get("WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID") or None,
            env,
        )
    except CredentialError as exc:
        logger.error("workload_credential configuration_rejected source=%s reason=%s", source, exc.code)
        return CredentialHolder(source, TARGET_WORKLOAD, trust_domain, config_error=exc.code)
    return CredentialHolder(
        SOURCE_KEYVAULT,
        TARGET_WORKLOAD,
        trust_domain,
        environment=env.get("WAOOAW_WID_ENVIRONMENT") or None,
        reader=reader,
        refresh_seconds=refresh_seconds,
    )
