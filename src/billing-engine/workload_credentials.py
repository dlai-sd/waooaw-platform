"""ADR-046 Amendment 1 workload credential delivery for the Billing Engine: Key Vault source, verification, hot swap."""

# Implements: ADR-046 sections 3, 4.2, 5.1, 6, and 12 (D4, D5, D6); workload-identity-cloud-issuance-contract.md sections 3 and 8
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlsplit

import httpx
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, HTTPException, Request
from workload_identity import (
    DELEGATION_SIGNING_OID,
    PEER_CERTIFICATE_STATE_KEY,
    DelegationKey,
    DelegationKeys,
    RouteGrant,
    ServiceAuthError,
    TrustAnchors,
    certificate_uris,
    extract_peer_identity,
    has_extended_key_usage,
)
from cryptography.x509.oid import ExtendedKeyUsageOID

logger = logging.getLogger(__name__)

SOURCE_DIRECTORY = "directory"
SOURCE_KEYVAULT = "keyvault"
SCHEMA_VERSION = "1.1"
UNISSUED_SENTINEL = "UNISSUED"
TRUST_BUNDLE_SECRET = "wid-trust-bundle"  # noqa: S105
VAULT_API_VERSION = "7.4"
VAULT_RESOURCE = "https://vault.azure.net"
IDENTITY_API_VERSION = "2019-08-01"
DEFAULT_REFRESH_SECONDS = 300
MINIMUM_REFRESH_SECONDS = 30
SERVICE_LINK_ROUTE = "/internal/v1/service-link"
SERVICE_LINK_OPERATION = "probeServiceLink"
STATE_READY = "READY"
STATE_UNAVAILABLE = "UNAVAILABLE"
STATE_UNISSUED = "UNISSUED"


class CredentialRejected(RuntimeError):  # noqa: N818 - public name shared with the loader contract
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Expectation:
    workload: str
    trust_domain: str
    environment: str | None = None


@dataclass(frozen=True)
class CredentialSnapshot:
    source: str
    bundle_version: int
    own_version: int
    environment: str
    trust_domain: str
    identity_uri: str
    audience: str
    not_after: datetime | None
    serial_digest: str
    anchors: TrustAnchors
    delegation_keys: DelegationKeys
    grants: frozenset[RouteGrant]
    ca_bundle_pem: bytes
    tls_chain_pem: bytes
    tls_key_pem: bytes
    digest: str

    def __repr__(self) -> str:
        return f"CredentialSnapshot(source={self.source!r}, bundle_version={self.bundle_version}, serial={self.serial_digest})"


def _instant(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _serial_digest(certificate: x509.Certificate) -> str:
    return hashlib.sha256(str(certificate.serial_number).encode()).hexdigest()[:16]


def _split_authorities(pem: bytes) -> tuple[list[x509.Certificate], list[x509.Certificate]]:
    roots: list[x509.Certificate] = []
    intermediates: list[x509.Certificate] = []
    for certificate in x509.load_pem_x509_certificates(pem):
        try:
            certificate.verify_directly_issued_by(certificate)
            roots.append(certificate)
        except (ValueError, TypeError, InvalidSignature):
            intermediates.append(certificate)
    return roots, intermediates


def _public_der(key: Any) -> bytes:
    return key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def _grants(manifest: Mapping[str, Any], workload: str) -> frozenset[RouteGrant]:
    workloads = manifest["workloads"]
    return frozenset(
        RouteGrant(
            caller_uri=workloads[grant["caller"]]["identity_uri"],
            target_audience=workloads[workload]["audience"],
            method=grant["method"],
            route=grant["route"],
            operation=grant["operation"],
            contract_major=int(grant["contract_major"]),
        )
        for grant in manifest["route_grants"]
        if grant["target"] == workload
    )


def _json_object(text: str) -> dict[str, Any]:
    if text.strip() == UNISSUED_SENTINEL:
        raise CredentialRejected("UNISSUED")
    try:
        value = json.loads(text)
    except ValueError:
        raise CredentialRejected("BUNDLE_INVALID") from None
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise CredentialRejected("BUNDLE_INVALID")
    return value


def _canonical(bundle: Mapping[str, Any]) -> bytes:
    unsigned = {key: value for key, value in bundle.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _version(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CredentialRejected("BUNDLE_INVALID")
    return value


def _verify_authorities(trust: Mapping[str, Any], current: datetime) -> tuple[TrustAnchors, x509.Certificate]:
    root = x509.load_pem_x509_certificate(trust["root_pem"].encode())
    intermediate = x509.load_pem_x509_certificate(trust["intermediate_pem"].encode())
    extra_roots, extra_intermediates = _split_authorities(trust["ca_bundle_pem"].encode())
    roots = (root, *(item for item in extra_roots if item != root))
    anchors = TrustAnchors(
        roots=roots,
        intermediates=(intermediate, *(item for item in extra_intermediates if item != intermediate)),
        revoked_serials=frozenset(int(serial) for serial in trust.get("revoked_serials", [])),
        revoked_identity_uris=frozenset(str(uri) for uri in trust.get("revoked_identity_uris", [])),
    )
    try:
        root.verify_directly_issued_by(root)
        intermediate.verify_directly_issued_by(root)
    except (ValueError, TypeError, InvalidSignature):
        raise CredentialRejected("TRUST_CHAIN_INVALID") from None
    if not all(item.not_valid_before_utc <= current < item.not_valid_after_utc for item in (root, intermediate)):
        raise CredentialRejected("TRUST_CHAIN_INVALID")
    try:
        public_key = intermediate.public_key()
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise CredentialRejected("SIGNATURE_INVALID")
        public_key.verify(base64.b64decode(trust["signature"], validate=True), _canonical(trust), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, TypeError):
        raise CredentialRejected("SIGNATURE_INVALID") from None
    return anchors, intermediate


def _verify_leaf(
    own: Mapping[str, Any], anchors: TrustAnchors, identity_uri: str, current: datetime
) -> tuple[x509.Certificate, bytes]:
    pem = own["tls_cert_pem"].encode()
    leaf = x509.load_pem_x509_certificates(pem)[0]
    if anchors.is_revoked(leaf):
        raise CredentialRejected("LEAF_REVOKED")
    if not leaf.not_valid_before_utc <= current < leaf.not_valid_after_utc:
        raise CredentialRejected("LEAF_NOT_VALID")
    if not anchors.chains(leaf, current):
        raise CredentialRejected("LEAF_CHAIN_INVALID")
    if certificate_uris(leaf) != [identity_uri] or own["identity_uri"] != identity_uri:
        raise CredentialRejected("LEAF_IDENTITY_MISMATCH")
    if not has_extended_key_usage(leaf, ExtendedKeyUsageOID.SERVER_AUTH):
        raise CredentialRejected("LEAF_USAGE_INVALID")
    key = serialization.load_pem_private_key(own["tls_key_pem"].encode(), password=None)
    if _public_der(key.public_key()) != _public_der(leaf.public_key()):
        raise CredentialRejected("KEY_MISMATCH")
    return leaf, pem


def _delegation_keys(
    manifest: Mapping[str, Any], anchors: TrustAnchors, current: datetime
) -> dict[tuple[str, str], DelegationKey]:
    keys: dict[tuple[str, str], DelegationKey] = {}
    for workload in manifest["workloads"].values():
        for entry in workload.get("delegation_certificates", []):
            certificate = x509.load_pem_x509_certificate(entry["certificate_pem"].encode())
            public_key = certificate.public_key()
            if (
                not isinstance(public_key, ec.EllipticCurvePublicKey)
                or not has_extended_key_usage(certificate, DELEGATION_SIGNING_OID)
                or certificate_uris(certificate) != [workload["identity_uri"]]
            ):
                raise CredentialRejected("DELEGATION_INVALID")
            if current >= certificate.not_valid_after_utc or anchors.is_revoked(certificate):
                continue
            if not anchors.chains(certificate, max(current, certificate.not_valid_before_utc)):
                raise CredentialRejected("DELEGATION_INVALID")
            activate_after = entry.get("activate_after")
            key = (workload["identity_uri"], str(entry["key_id"]))
            known = keys.get(key)
            if known is None or known.certificate.not_valid_after_utc < certificate.not_valid_after_utc:
                keys[key] = DelegationKey(
                    public_key, certificate, int(_instant(activate_after).timestamp()) if activate_after else 0
                )
    return keys


def verify_credentials(
    trust_text: str,
    bundle_text: str,
    expectation: Expectation,
    current: datetime,
    last_bundle_version: int = 0,
    last_own_version: int = 0,
) -> CredentialSnapshot:
    trust = _json_object(trust_text)
    own = _json_object(bundle_text)
    try:
        anchors, _ = _verify_authorities(trust, current)
        manifest = trust["manifest"]
        environment = trust["environment"]
        trust_domain = trust["trust_domain"]
        if (
            own["environment"] != environment
            or manifest["environment"] != environment
            or (expectation.environment is not None and environment != expectation.environment)
            or own["workload"] != expectation.workload
        ):
            raise CredentialRejected("ENVIRONMENT_MISMATCH")
        if manifest["trust_domain"] != trust_domain or trust_domain != expectation.trust_domain:
            raise CredentialRejected("TRUST_DOMAIN_MISMATCH")
        bundle_version, own_version = _version(trust["bundle_version"]), _version(own["bundle_version"])
        if bundle_version < last_bundle_version or own_version < last_own_version:
            raise CredentialRejected("VERSION_REGRESSION")
        target = manifest["workloads"][expectation.workload]
        identity_uri = target["identity_uri"]
        if not identity_uri.startswith(f"spiffe://{trust_domain}/workload/"):
            raise CredentialRejected("TRUST_DOMAIN_MISMATCH")
        leaf, chain_pem = _verify_leaf(own, anchors, identity_uri, current)
        keys = _delegation_keys(manifest, anchors, current)
        return CredentialSnapshot(
            source=SOURCE_KEYVAULT,
            bundle_version=bundle_version,
            own_version=own_version,
            environment=environment,
            trust_domain=trust_domain,
            identity_uri=identity_uri,
            audience=target["audience"],
            not_after=leaf.not_valid_after_utc,
            serial_digest=_serial_digest(leaf),
            anchors=anchors,
            delegation_keys=keys,
            grants=_grants(manifest, expectation.workload),
            ca_bundle_pem=trust["ca_bundle_pem"].encode(),
            tls_chain_pem=chain_pem,
            tls_key_pem=own["tls_key_pem"].encode(),
            digest=hashlib.sha256(f"{trust_text}\n{bundle_text}".encode()).hexdigest(),
        )
    except CredentialRejected:
        raise
    except (KeyError, TypeError, ValueError, AttributeError):
        raise CredentialRejected("BUNDLE_INVALID") from None


def load_directory_snapshot(credentials: Path) -> CredentialSnapshot:
    manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
    target = manifest["workloads"]["billing-engine"]
    signer = manifest["workloads"]["business-platform"]
    roots, intermediates = _split_authorities((credentials / "trust" / "ca-bundle.pem").read_bytes())
    anchors = TrustAnchors(tuple(roots), tuple(intermediates))
    certificate = x509.load_pem_x509_certificate(
        (credentials / "workloads" / "business-platform" / "delegation-cert.pem").read_bytes()
    )
    public_key = certificate.public_key()
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("BP delegation certificate must contain an ECDSA public key")
    leaf_path = credentials / "workloads" / "billing-engine" / "tls-cert.pem"
    leaf = x509.load_pem_x509_certificate(leaf_path.read_bytes()) if leaf_path.exists() else None
    return CredentialSnapshot(
        source=SOURCE_DIRECTORY,
        bundle_version=0,
        own_version=0,
        environment=str(manifest.get("environment", "")),
        trust_domain=manifest["trust_domain"],
        identity_uri=target["identity_uri"],
        audience=target["audience"],
        not_after=leaf.not_valid_after_utc if leaf is not None else None,
        serial_digest=_serial_digest(leaf) if leaf is not None else "",
        anchors=anchors,
        delegation_keys={(signer["identity_uri"], signer["delegation_key_id"]): DelegationKey(public_key, certificate)},
        grants=_grants(manifest, "billing-engine"),
        ca_bundle_pem=b"",
        tls_chain_pem=b"",
        tls_key_pem=b"",
        digest="",
    )


class CredentialHolder:
    """Atomic holder of the last verified snapshot; it fails closed once the snapshot passes its not-after."""

    def __init__(self, source: str, now: Callable[[], datetime] | None = None) -> None:
        self.source = source
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lock = Lock()
        self._snapshot: CredentialSnapshot | None = None
        self._reason: str | None = None
        self._logged: str | None = None
        self.last_bundle_version = 0
        self.last_own_version = 0

    @classmethod
    def static(cls, snapshot: CredentialSnapshot, now: Callable[[], datetime] | None = None) -> CredentialHolder:
        holder = cls(snapshot.source, now)
        holder.install(snapshot)
        return holder

    def _live(self, snapshot: CredentialSnapshot | None) -> CredentialSnapshot | None:
        if snapshot is None or (snapshot.not_after is not None and self._now() >= snapshot.not_after):
            return None
        return snapshot

    def _state(self, snapshot: CredentialSnapshot | None) -> str:
        if self._live(snapshot) is not None:
            return STATE_READY
        return STATE_UNISSUED if snapshot is None and self._reason == "UNISSUED" else STATE_UNAVAILABLE

    def _transition(self, state: str, reason: str | None) -> None:
        if state != self._logged:
            logger.warning(
                "workload_credentials state=%s previous=%s source=%s reason=%s", state, self._logged, self.source, reason
            )
            self._logged = state

    def install(self, snapshot: CredentialSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot
            self._reason = None
            self.last_bundle_version = max(self.last_bundle_version, snapshot.bundle_version)
            self.last_own_version = max(self.last_own_version, snapshot.own_version)
            self._transition(self._state(snapshot), None)

    def note_failure(self, reason: str) -> None:
        with self._lock:
            self._reason = reason
            self._transition(self._state(self._snapshot), reason)

    def current(self) -> CredentialSnapshot | None:
        with self._lock:
            snapshot = self._snapshot
            self._transition(self._state(snapshot), self._reason)
        return self._live(snapshot)

    def delegation_keys(self) -> DelegationKeys:
        snapshot = self.current()
        return snapshot.delegation_keys if snapshot is not None else {}

    def grants(self) -> frozenset[RouteGrant]:
        snapshot = self.current()
        return snapshot.grants if snapshot is not None else frozenset()

    def anchors(self) -> TrustAnchors | None:
        snapshot = self.current()
        return snapshot.anchors if snapshot is not None else None

    def validate_peer(self, certificate_der: bytes) -> bool:
        snapshot = self.current()
        if snapshot is None:
            return False
        current = self._now()
        try:
            certificate = x509.load_der_x509_certificate(certificate_der)
            extract_peer_identity(certificate, snapshot.trust_domain, snapshot.anchors.revoked_serials, current)
        except (ValueError, ServiceAuthError):
            return False
        return snapshot.anchors.chains(certificate, current) and has_extended_key_usage(
            certificate, ExtendedKeyUsageOID.CLIENT_AUTH
        )

    def status(self) -> dict[str, Any]:
        with self._lock:
            snapshot = self._snapshot
            state = self._state(snapshot)
            reason = self._reason
            self._transition(state, reason)
        remaining = None
        if snapshot is not None and snapshot.not_after is not None:
            remaining = max(0, int((snapshot.not_after - self._now()).total_seconds()))
        detail: dict[str, Any] = {
            "source": self.source,
            "state": state,
            "serial_digest": snapshot.serial_digest if snapshot is not None else None,
            "not_after": snapshot.not_after.isoformat() if snapshot is not None and snapshot.not_after is not None else None,
            "remaining_seconds": remaining,
            "bundle_version": snapshot.bundle_version if snapshot is not None else None,
        }
        if state != STATE_READY and reason is not None:
            detail["reason"] = reason
        return detail


def parse_vault_url(value: str) -> str:
    parts = urlsplit(value.strip())
    host = parts.hostname or ""
    if (
        parts.scheme != "https"
        or not host.endswith(".vault.azure.net")
        or len(host) == len(".vault.azure.net")
        or parts.username is not None
        or parts.port not in (None, 443)
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("WAOOAW_WID_VAULT_URL must be an https Azure Key Vault URL")
    return f"https://{host}"


def _identity_endpoint(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1", "::1") or parts.query or parts.username:
        raise ValueError("IDENTITY_ENDPOINT must be a loopback http URL")
    return value


class KeyVaultReader:
    def __init__(
        self,
        vault_url: str,
        client_id: str,
        environ: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._vault_url = parse_vault_url(vault_url)
        self._client_id = client_id
        self._environ = os.environ if environ is None else environ
        self._transport = transport
        self._now = now
        self._token: tuple[str, float] | None = None

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=10.0, transport=self._transport, follow_redirects=False)

    def _access_token(self, client: httpx.Client) -> str:
        if self._token is not None and self._token[1] - self._now() > 120:
            return self._token[0]
        endpoint = _identity_endpoint(self._environ.get("IDENTITY_ENDPOINT", ""))
        header = self._environ.get("IDENTITY_HEADER", "")
        if not header:
            raise CredentialRejected("FETCH_FAILED")
        params = {"api-version": IDENTITY_API_VERSION, "resource": VAULT_RESOURCE}
        if self._client_id:
            params["client_id"] = self._client_id
        response = client.get(endpoint, params=params, headers={"X-IDENTITY-HEADER": header})
        response.raise_for_status()
        body = response.json()
        token = body["access_token"]
        try:
            expires = float(body["expires_on"])
        except (KeyError, TypeError, ValueError):
            expires = self._now() + 300
        self._token = (token, expires)
        return token

    def get_secret(self, name: str) -> str:
        with self._client() as client:
            token = self._access_token(client)
            response = client.get(
                f"{self._vault_url}/secrets/{name}",
                params={"api-version": VAULT_API_VERSION},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return str(response.json()["value"])


class CredentialRefresher:
    def __init__(
        self,
        holder: CredentialHolder,
        fetch: Callable[[], tuple[str, str]],
        expectation: Expectation,
        interval_seconds: int = DEFAULT_REFRESH_SECONDS,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._holder = holder
        self._fetch = fetch
        self._expectation = expectation
        self._interval = max(interval_seconds, MINIMUM_REFRESH_SECONDS)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def refresh_once(self) -> str:
        """Fetch, verify and swap; any failure keeps the previous snapshot and returns a reason code."""
        try:
            trust_text, bundle_text = self._fetch()
            digest = hashlib.sha256(f"{trust_text}\n{bundle_text}".encode()).hexdigest()
            installed = self._holder.current()
            if installed is not None and installed.digest == digest:
                return "UNCHANGED"
            snapshot = verify_credentials(
                trust_text,
                bundle_text,
                self._expectation,
                self._now(),
                self._holder.last_bundle_version,
                self._holder.last_own_version,
            )
        except CredentialRejected as rejected:
            reason = rejected.reason
        except Exception as error:  # the refresh must never take the service down
            logger.warning("workload_credentials fetch_error=%s", type(error).__name__)
            reason = "FETCH_FAILED"
        else:
            self._holder.install(snapshot)
            logger.info(
                "workload_credentials decision=accept source=%s bundle_version=%s serial=%s remaining_seconds=%s",
                snapshot.source,
                snapshot.bundle_version,
                snapshot.serial_digest,
                self._holder.status()["remaining_seconds"],
            )
            return "ACCEPTED"
        logger.warning("workload_credentials decision=reject reason=%s", reason)
        self._holder.note_failure(reason)
        return reason

    async def run(self) -> None:
        while True:
            await asyncio.to_thread(self.refresh_once)
            await asyncio.sleep(self._interval if self._holder.current() is not None else MINIMUM_REFRESH_SECONDS)


@dataclass(frozen=True)
class CredentialRuntime:
    holder: CredentialHolder
    refresher: CredentialRefresher | None
    trust_domain: str


_RUNTIME: CredentialRuntime | None = None
_RUNTIME_LOCK = Lock()


def credential_source(environ: Mapping[str, str] | None = None) -> str:
    return (os.environ if environ is None else environ).get("WAOOAW_WID_SOURCE", SOURCE_DIRECTORY).strip() or SOURCE_DIRECTORY


def build_keyvault_runtime(environ: Mapping[str, str]) -> CredentialRuntime:
    holder = CredentialHolder(SOURCE_KEYVAULT)
    trust_domain = environ.get("WAOOAW_WID_TRUST_DOMAIN", "").strip()
    workload = environ.get("WAOOAW_WID_WORKLOAD", "").strip()
    try:
        if not trust_domain or workload != "billing-engine":
            raise ValueError("WAOOAW_WID_TRUST_DOMAIN and WAOOAW_WID_WORKLOAD=billing-engine are required")
        reader = KeyVaultReader(
            environ.get("WAOOAW_WID_VAULT_URL", ""), environ.get("WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID", "").strip(), environ
        )
        interval = int(environ.get("WAOOAW_WID_REFRESH_SECONDS", str(DEFAULT_REFRESH_SECONDS)))
    except ValueError:
        logger.error("workload_credentials decision=reject reason=CONFIG_INVALID")
        holder.note_failure("CONFIG_INVALID")
        return CredentialRuntime(holder, None, trust_domain)
    refresher = CredentialRefresher(
        holder,
        lambda: (reader.get_secret(TRUST_BUNDLE_SECRET), reader.get_secret(f"wid-bundle-{workload}")),
        Expectation(workload, trust_domain, environ.get("WAOOAW_WID_ENVIRONMENT", "").strip() or None),
        interval,
    )
    return CredentialRuntime(holder, refresher, trust_domain)


def keyvault_runtime(environ: Mapping[str, str] | None = None) -> CredentialRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = build_keyvault_runtime(os.environ if environ is None else environ)
        return _RUNTIME


def reset_keyvault_runtime() -> None:
    global _RUNTIME
    with _RUNTIME_LOCK:
        _RUNTIME = None


service_link_router = APIRouter()


@service_link_router.get(SERVICE_LINK_ROUTE)
async def probe_service_link(request: Request) -> dict[str, Any]:
    auth = getattr(request.app.state, "relationship_workload_auth", None)
    certificate_der = request.scope.get("state", {}).get(PEER_CERTIFICATE_STATE_KEY)
    try:
        if auth is None or certificate_der is None:
            raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
        peer = extract_peer_identity(x509.load_der_x509_certificate(certificate_der), auth.trust_domain)
        auth.verifier.authorize_peer(peer, auth.audience, "GET", SERVICE_LINK_ROUTE, SERVICE_LINK_OPERATION, 1)
    except ServiceAuthError as exc:
        logger.warning(
            "service_auth decision=deny target=billing-engine operation=%s reason_class=%s", SERVICE_LINK_OPERATION, exc.code
        )
        raise HTTPException(status_code=401, detail="WBE_SERVICE_LINK_UNAUTHORIZED") from None
    status = auth.holder.status() if auth.holder is not None else {}
    if status.get("state") != STATE_READY or status.get("remaining_seconds") is None:
        raise HTTPException(status_code=503, detail="WBE_SERVICE_LINK_UNAVAILABLE")
    logger.info("service_auth decision=allow target=billing-engine operation=%s policy_version=1.0", SERVICE_LINK_OPERATION)
    return {
        "status": "ok",
        "peer_identity_uri": peer,
        "bundle_version": status["bundle_version"],
        "remaining_seconds": status["remaining_seconds"],
    }
