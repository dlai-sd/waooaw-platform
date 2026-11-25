"""ADR-046 workload credential issuance library shared by development, CI and the cloud issuer.

Signing backends differ only by Signer: LocalKeySigner (development, CI, tests) and KeyVaultSigner (cloud).
Test helpers for cloud-style fixtures (FakeKeyVault, LocalKeySigner, no network):

    fixture = build_cloud_fixture(registry_path, "demo", ["business-platform", "billing-engine"], now=None)
    fixture["wid-trust-bundle"], fixture["wid-bundle-billing-engine"]   # JSON strings per contract Section 8
    later = renew_cloud_fixture(fixture, now=fixture_now + timedelta(hours=9))   # same FakeKeyVault, renewed leaves
    fixture.vault                                                        # FakeKeyVault (secrets, set order, sign calls)

New delegation certificates carry activate_after = now + 10 minutes, so pass an earlier `now` when a test needs a
delegation key that is already active. verify_trust_bundle and verify_chain perform X.509 chain verification.
"""

# Implements: ADR-046 sections 3.1, 4.1, 4.2, 7.2, 10.1 and 12.2 (Amendment 1)
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from collections.abc import Callable
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier


REGISTRY_SCHEMA_VERSION = "1.0"
REGISTRY_POLICY_VERSION = "1.1"
BUNDLE_SCHEMA_VERSION = "1.1"
MANIFEST_SCHEMA_VERSION = "1.0"
ROOT_LIFETIME_DAYS = 365
INTERMEDIATE_LIFETIME_DAYS = 90
ROOT_RENEW_DAYS = 60
INTERMEDIATE_RENEW_DAYS = 30
MAX_LEAF_LIFETIME = timedelta(hours=24)
LEAF_RENEW_AFTER = timedelta(hours=8)
DUAL_TRUST = timedelta(days=7)
DELEGATION_ACTIVATION_DELAY = timedelta(minutes=10)
CLOCK_SKEW = timedelta(seconds=60)
MINIMUM_REMAINING = timedelta(hours=4)
DELEGATION_SIGNING_OID = ObjectIdentifier("1.3.6.1.4.1.55555.46.1")

UNISSUED = "UNISSUED"
KEY_ROOT = "wid-root"
KEY_INTERMEDIATE = "wid-intermediate"
SECRET_CA_STATE = "wid-ca-state"  # noqa: S105 - Key Vault object name, not a credential
SECRET_TRUST_BUNDLE = "wid-trust-bundle"  # noqa: S105
BUNDLE_SECRET_PREFIX = "wid-bundle-"  # noqa: S105
DEFAULT_WORKLOADS = ("business-platform", "billing-engine", "professional-runtime")

KEY_VAULT_API_VERSION = "7.4"
KEY_VAULT_RESOURCE = "https://vault.azure.net"
KEY_VAULT_HOST_SUFFIX = ".vault.azure.net"
MAX_SECRET_BYTES = 25 * 1024
_NAME_PATTERN = re.compile(r"^[0-9A-Za-z-]{1,127}$")
_SIGNATURE_ALGORITHM_DER = bytes.fromhex("300a06082a8648ce3d040302")


class IssuanceError(Exception):
    """Raised with a one-line message that never contains key material."""


GROUPED_GRANTS_FORMAT = "grouped-v1"


def group_route_grants(grants: list[dict[str, Any]]) -> dict[str, Any]:
    """Publish route grants grouped by caller and target, with POST and contract major 1 implied (WC-172 B10).

    The trust bundle must fit one Key Vault secret (25 KiB). Repeating the caller, target, method and contract major
    on every grant filled it; grouping keeps every grant and halves their size. Consumers accept this form and the
    plain list of grant objects.
    """
    pairs: dict[str, list[list[Any]]] = {}
    for grant in grants:
        item: list[Any] = [grant["route"], grant["operation"]]
        if grant["method"] != "POST" or int(grant["contract_major"]) != 1:
            item += [grant["method"], int(grant["contract_major"])]
        pairs.setdefault(f"{grant['caller']}>{grant['target']}", []).append(item)
    return {"format": GROUPED_GRANTS_FORMAT, "pairs": pairs}


def expand_route_grants(value: Any) -> list[dict[str, Any]]:
    """The plain list of grant objects, from either published form."""
    if isinstance(value, list):
        return value
    if not isinstance(value, dict) or value.get("format") != GROUPED_GRANTS_FORMAT or not isinstance(value.get("pairs"), dict):
        raise IssuanceError("The route grants are in an unknown form")
    grants: list[dict[str, Any]] = []
    for pair, items in value["pairs"].items():
        caller, target = pair.split(">", 1)
        for item in items:
            grants.append(
                {
                    "caller": caller,
                    "target": target,
                    "method": item[2] if len(item) > 2 else "POST",
                    "route": item[0],
                    "operation": item[1],
                    "contract_major": item[3] if len(item) > 3 else 1,
                }
            )
    return grants


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical_json(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _compact_json(document: dict[str, Any]) -> str:
    return canonical_json(document).decode("ascii")


class Signer(ABC):
    key_ref: str

    @abstractmethod
    def public_key(self) -> ec.EllipticCurvePublicKey:
        """Public key matching the signing key."""

    @abstractmethod
    def sign(self, data: bytes) -> bytes:
        """DER-encoded ECDSA signature (SHA-256) over data."""


class LocalKeySigner(Signer):
    def __init__(self, key: ec.EllipticCurvePrivateKey, key_ref: str = "local") -> None:
        self._key = key
        self.key_ref = key_ref

    def __repr__(self) -> str:
        return f"LocalKeySigner(key_ref={self.key_ref!r})"

    def public_key(self) -> ec.EllipticCurvePublicKey:
        return self._key.public_key()

    def sign(self, data: bytes) -> bytes:
        return self._key.sign(data, ec.ECDSA(hashes.SHA256()))


Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]]
TokenProvider = Callable[[], str]


def urllib_transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - https and vault host validated by callers
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class ManagedIdentityTokenProvider:
    def __init__(
        self,
        client_id: str | None = None,
        environ: dict[str, str] | None = None,
        transport: Transport = urllib_transport,
    ) -> None:
        self._client_id = client_id
        self._environ = os.environ if environ is None else environ
        self._transport = transport
        self._token: str | None = None
        self._expires_at = 0.0

    def __call__(self) -> str:
        if self._token and time.time() < self._expires_at - 120:
            return self._token
        endpoint = self._environ.get("IDENTITY_ENDPOINT")
        header = self._environ.get("IDENTITY_HEADER")
        if not endpoint or not header:
            raise IssuanceError("Managed identity endpoint is not configured")
        query = {"resource": KEY_VAULT_RESOURCE, "api-version": "2019-08-01"}
        if self._client_id:
            query["client_id"] = self._client_id
        try:
            status, raw = self._transport(
                "GET", f"{endpoint}?{urllib.parse.urlencode(query)}", {"X-IDENTITY-HEADER": header}, None
            )
        except OSError:
            raise IssuanceError("Managed identity token request failed: network error") from None
        if status != 200:
            raise IssuanceError(f"Managed identity token request failed with HTTP {status}")
        try:
            payload = json.loads(raw)
            token = str(payload["access_token"])
        except (ValueError, KeyError, TypeError):
            raise IssuanceError("Managed identity token response is invalid") from None
        try:
            self._expires_at = float(payload.get("expires_on", 0))
        except (TypeError, ValueError):
            self._expires_at = time.time() + 300
        self._token = token
        return token


@dataclass(frozen=True)
class KeyRef:
    kid: str
    public_key: ec.EllipticCurvePublicKey


class VaultClient(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        """Latest secret value, or None when the secret does not exist."""

    @abstractmethod
    def set_secret(self, name: str, value: str) -> None:
        """Write a new secret version."""

    @abstractmethod
    def create_key_version(self, name: str) -> KeyRef:
        """Create a new non-exportable key version and return its public part."""

    @abstractmethod
    def get_key_public(self, name_or_kid: str) -> KeyRef:
        """Public key of the current version (name) or of a specific version (kid)."""

    @abstractmethod
    def get_signer(self, kid: str) -> Signer:
        """Signer bound to the key version kid."""


def validate_vault_url(vault_url: str) -> str:
    parsed = urllib.parse.urlsplit(vault_url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not host.endswith(KEY_VAULT_HOST_SUFFIX) or parsed.path not in ("", "/"):
        raise IssuanceError("Vault URL must be https and its host must end with .vault.azure.net")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443):
        raise IssuanceError("Vault URL must be https and its host must end with .vault.azure.net")
    return f"https://{host}"


class KeyVaultSigner(Signer):
    def __init__(self, client: KeyVaultClient, kid: str, public_key: ec.EllipticCurvePublicKey) -> None:
        self._client = client
        self.key_ref = kid
        self._public_key = public_key

    def __repr__(self) -> str:
        return f"KeyVaultSigner(key_ref={self.key_ref!r})"

    def public_key(self) -> ec.EllipticCurvePublicKey:
        return self._public_key

    def sign(self, data: bytes) -> bytes:
        digest = hashlib.sha256(data).digest()
        result = self._client.call("POST", f"{self.key_ref}/sign", {"alg": "ES256", "value": _b64url(digest)})
        try:
            raw = _b64url_decode(str(result["value"]))
        except (KeyError, TypeError, ValueError):
            raise IssuanceError("Key Vault sign response is invalid") from None
        if len(raw) != 64:
            raise IssuanceError("Key Vault sign response has an unexpected length")
        der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        try:
            self._public_key.verify(der, data, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            raise IssuanceError("Key Vault signature does not verify against the key version") from None
        return der


class KeyVaultClient(VaultClient):
    def __init__(
        self,
        vault_url: str,
        token_provider: TokenProvider,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.vault_url = validate_vault_url(vault_url)
        self._host = urllib.parse.urlsplit(self.vault_url).hostname
        self._token_provider = token_provider
        self._transport = transport
        self._sleep = sleep

    def call(
        self, method: str, target: str, payload: dict[str, Any] | None = None, allow_missing: bool = False
    ) -> dict[str, Any]:
        url = target if target.startswith("https://") else f"{self.vault_url}{target}"
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != self._host or parsed.query:
            raise IssuanceError("Refusing a Key Vault request outside the configured vault")
        url = f"{url}?api-version={KEY_VAULT_API_VERSION}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        status, raw = 0, b""
        for attempt in range(3):
            headers = {"Authorization": f"Bearer {self._token_provider()}", "Content-Type": "application/json"}
            try:
                status, raw = self._transport(method, url, headers, body)
            except OSError:
                status, raw = 0, b""
            if status not in (0, 429, 500, 502, 503, 504) or attempt == 2:
                break
            self._sleep(2 ** (attempt + 1))
        if status == 404 and allow_missing:
            return {}
        if not 200 <= status < 300:
            detail = "network error" if status == 0 else f"HTTP {status}{_error_code(raw)}"
            raise IssuanceError(f"Key Vault {method} {parsed.path} failed: {detail}")
        try:
            return json.loads(raw) if raw else {}
        except ValueError:
            raise IssuanceError(f"Key Vault {method} {parsed.path} returned invalid JSON") from None

    def get_secret(self, name: str) -> str | None:
        result = self.call("GET", f"/secrets/{_secret_name(name)}", allow_missing=True)
        return None if not result else str(result.get("value", ""))

    def set_secret(self, name: str, value: str) -> None:
        if len(value.encode("utf-8")) > MAX_SECRET_BYTES:
            raise IssuanceError(f"Secret {name} exceeds the Key Vault size limit")
        self.call("PUT", f"/secrets/{_secret_name(name)}", {"value": value, "contentType": "application/json"})

    def create_key_version(self, name: str) -> KeyRef:
        result = self.call(
            "POST", f"/keys/{_secret_name(name)}/create", {"kty": "EC", "crv": "P-256", "key_ops": ["sign", "verify"]}
        )
        return _key_ref(result)

    def get_key_public(self, name_or_kid: str) -> KeyRef:
        target = name_or_kid if name_or_kid.startswith("https://") else f"/keys/{_secret_name(name_or_kid)}"
        return _key_ref(self.call("GET", target))

    def get_signer(self, kid: str) -> Signer:
        ref = self.get_key_public(kid)
        return KeyVaultSigner(self, ref.kid, ref.public_key)


def _secret_name(name: str) -> str:
    if not _NAME_PATTERN.match(name):
        raise IssuanceError("Invalid Key Vault object name")
    return name


def _error_code(raw: bytes) -> str:
    try:
        code = json.loads(raw)["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return ""
    return f" {code}" if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", code) else ""


def _key_ref(result: dict[str, Any]) -> KeyRef:
    try:
        key = result["key"]
        if key["kty"] not in ("EC", "EC-HSM") or key["crv"] != "P-256":
            raise IssuanceError("Key Vault key must be EC P-256")
        public_key = ec.EllipticCurvePublicNumbers(
            int.from_bytes(_b64url_decode(key["x"]), "big"),
            int.from_bytes(_b64url_decode(key["y"]), "big"),
            ec.SECP256R1(),
        ).public_key()
        return KeyRef(str(key["kid"]), public_key)
    except (KeyError, TypeError, ValueError):
        raise IssuanceError("Key Vault key response is invalid") from None


class FakeKeyVault(VaultClient):
    """In-memory vault for tests: keys never leave it, secrets and sign calls are recorded."""

    def __init__(self, vault_url: str = "https://kv-fake.vault.azure.net") -> None:
        self.vault_url = vault_url
        self.secrets: dict[str, str] = {}
        self.keys: dict[str, list[str]] = {}
        self._private: dict[str, ec.EllipticCurvePrivateKey] = {}
        self.secret_writes: list[str] = []
        self.sign_calls: list[str] = []

    def provision(self, workloads: list[str] | tuple[str, ...]) -> FakeKeyVault:
        for name in (KEY_ROOT, KEY_INTERMEDIATE):
            self.create_key_version(name)
        for name in (SECRET_CA_STATE, SECRET_TRUST_BUNDLE, *(f"{BUNDLE_SECRET_PREFIX}{item}" for item in workloads)):
            self.secrets[name] = UNISSUED
        return self

    def get_secret(self, name: str) -> str | None:
        return self.secrets.get(name)

    def set_secret(self, name: str, value: str) -> None:
        if len(value.encode("utf-8")) > MAX_SECRET_BYTES:
            raise IssuanceError(f"Secret {name} exceeds the Key Vault size limit")
        self.secrets[name] = value
        self.secret_writes.append(name)

    def create_key_version(self, name: str) -> KeyRef:
        kid = f"{self.vault_url}/keys/{name}/{uuid.uuid4().hex}"
        key = ec.generate_private_key(ec.SECP256R1())
        self._private[kid] = key
        self.keys.setdefault(name, []).append(kid)
        return KeyRef(kid, key.public_key())

    def get_key_public(self, name_or_kid: str) -> KeyRef:
        kid = self.keys[name_or_kid][-1] if name_or_kid in self.keys else name_or_kid
        if kid not in self._private:
            raise IssuanceError("Key Vault key was not found")
        return KeyRef(kid, self._private[kid].public_key())

    def get_signer(self, kid: str) -> Signer:
        if kid not in self._private:
            raise IssuanceError("Key Vault key was not found")
        vault = self

        class _Recording(LocalKeySigner):
            def sign(self, data: bytes) -> bytes:
                vault.sign_calls.append(kid)
                return super().sign(data)

        return _Recording(self._private[kid], kid)


def generate_key(curve: ec.EllipticCurve | None = None) -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(curve or ec.SECP256R1())


def private_key_pem(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(
        "ascii"
    )


def certificate_pem(certificate: x509.Certificate) -> str:
    return certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")


def load_certificate(pem: str) -> x509.Certificate:
    try:
        return x509.load_pem_x509_certificate(pem.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        raise IssuanceError("Certificate PEM is invalid") from None


def fingerprint(certificate: x509.Certificate) -> str:
    return certificate.fingerprint(hashes.SHA256()).hex()


def key_id(public_key: Any) -> str:
    der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest()[:32]


def name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def load_registry(path: Path) -> dict[str, Any]:
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION or registry.get("policy_version") != REGISTRY_POLICY_VERSION:
        raise ValueError("Unsupported workload registry version")
    workloads = registry.get("workloads", {})
    grants = registry.get("route_grants", [])
    if not workloads or not grants:
        raise ValueError("Workload registry must declare workloads and route grants")
    for workload_name, workload in workloads.items():
        identity_path = workload.get("identity_path", "")
        audience = workload.get("audience", "")
        if "*" in identity_path or "*" in audience or identity_path.endswith("domain-adapter"):
            raise ValueError(f"Workload {workload_name} uses a wildcard or generic adapter identity")
    for grant in grants:
        if grant.get("caller") not in workloads or grant.get("target") not in workloads:
            raise ValueError("Route grant references an unregistered workload")
        if grant.get("method") not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Route grant method is invalid")
        if not grant.get("operation") or int(grant.get("contract_major", 0)) < 1:
            raise ValueError("Route grant operation and contract major are required")
    for environment_name, settings in registry.get("environments", {}).items():
        if not timedelta(0) < timedelta(hours=int(settings.get("leaf_lifetime_hours", 0))) <= MAX_LEAF_LIFETIME:
            raise ValueError(f"Environment {environment_name} leaf lifetime must be between 1 and 24 hours")
    return registry


def environment_settings(registry: dict[str, Any], environment: str) -> tuple[str, timedelta]:
    settings = registry.get("environments", {}).get(environment)
    if settings is None:
        raise IssuanceError(f"Environment {environment} is not registered")
    return settings["trust_domain"], timedelta(hours=int(settings["leaf_lifetime_hours"]))


def workload_identity_uri(registry: dict[str, Any], environment: str, workload: str) -> str:
    entry = registry["workloads"].get(workload)
    if entry is None:
        raise IssuanceError(f"Workload {workload} is not registered")
    trust_domain, _ = environment_settings(registry, environment)
    return f"spiffe://{trust_domain}/workload/{entry['identity_path']}"


def _der(tag: int, content: bytes) -> bytes:
    size = len(content)
    if size < 0x80:
        length = bytes([size])
    else:
        encoded = size.to_bytes((size.bit_length() + 7) // 8, "big")
        length = bytes([0x80 | len(encoded)]) + encoded
    return bytes([tag]) + length + content


def sign_certificate(builder: x509.CertificateBuilder, signer: Signer) -> x509.Certificate:
    """Sign a builder through a Signer: the to-be-signed bytes are produced locally and signed externally."""
    placeholder = ec.generate_private_key(ec.SECP256R1())
    tbs = builder.sign(placeholder, hashes.SHA256()).tbs_certificate_bytes
    signature = signer.sign(tbs)
    certificate = x509.load_der_x509_certificate(_der(0x30, tbs + _SIGNATURE_ALGORITHM_DER + _der(0x03, b"\x00" + signature)))
    try:
        signer.public_key().verify(certificate.signature, certificate.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        raise IssuanceError("Signer returned an invalid certificate signature") from None
    return certificate


def build_ca_certificate(
    subject: x509.Name,
    issuer: x509.Name,
    public_key: Any,
    issuer_signer: Signer,
    not_before: datetime,
    lifetime: timedelta,
    path_length: int,
) -> x509.Certificate:
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_before + lifetime)
        .add_extension(x509.BasicConstraints(ca=True, path_length=path_length), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_signer.public_key()), critical=False)
    )
    return sign_certificate(builder, issuer_signer)


def build_leaf_certificate(
    identity_uri: str,
    public_key: Any,
    intermediate: x509.Certificate,
    intermediate_signer: Signer,
    usages: list[str],
    not_before: datetime,
    lifetime: timedelta,
) -> x509.Certificate:
    if not timedelta(0) < lifetime <= MAX_LEAF_LIFETIME:
        raise IssuanceError("Leaf lifetime must be positive and must not exceed 24 hours")
    eku = []
    if "client_auth" in usages:
        eku.append(ExtendedKeyUsageOID.CLIENT_AUTH)
    if "server_auth" in usages:
        eku.append(ExtendedKeyUsageOID.SERVER_AUTH)
    if "delegation_signing" in usages:
        eku.append(DELEGATION_SIGNING_OID)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name(identity_uri.rsplit("/", 1)[-1]))
        .issuer_name(intermediate.subject)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_before + lifetime)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(identity_uri)]), critical=False)
        .add_extension(x509.ExtendedKeyUsage(eku), critical=False)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(intermediate_signer.public_key()), critical=False)
    )
    return sign_certificate(builder, intermediate_signer)


@dataclass(frozen=True)
class WorkloadCredential:
    identity_uri: str
    tls_key: ec.EllipticCurvePrivateKey
    tls_certificate: x509.Certificate
    delegation_key: ec.EllipticCurvePrivateKey | None
    delegation_certificate: x509.Certificate | None


def issue_workload_credential(
    registry: dict[str, Any],
    environment: str,
    workload: str,
    tls_key: ec.EllipticCurvePrivateKey,
    intermediate: x509.Certificate,
    intermediate_signer: Signer,
    not_before: datetime,
    lifetime: timedelta,
) -> WorkloadCredential:
    entry = registry["workloads"][workload]
    identity_uri = workload_identity_uri(registry, environment, workload)
    tls_certificate = build_leaf_certificate(
        identity_uri, tls_key.public_key(), intermediate, intermediate_signer, entry["tls_usages"], not_before, lifetime
    )
    delegation_key = delegation_certificate = None
    if entry.get("delegation_signer"):
        delegation_key = generate_key()
        delegation_certificate = build_leaf_certificate(
            identity_uri,
            delegation_key.public_key(),
            intermediate,
            intermediate_signer,
            ["delegation_signing"],
            not_before,
            lifetime,
        )
    return WorkloadCredential(identity_uri, tls_key, tls_certificate, delegation_key, delegation_certificate)


def delegation_entry(certificate: x509.Certificate, activate_after: datetime) -> dict[str, str]:
    return {
        "key_id": key_id(certificate.public_key()),
        "certificate_pem": certificate_pem(certificate),
        "not_before": iso(certificate.not_valid_before_utc),
        "not_after": iso(certificate.not_valid_after_utc),
        "activate_after": iso(activate_after),
    }


def workload_record(
    registry: dict[str, Any], credential: WorkloadCredential, workload: str, delegations: list[dict[str, str]]
) -> dict[str, Any]:
    certificate = credential.tls_certificate
    return {
        "identity_uri": credential.identity_uri,
        "audience": registry["workloads"][workload].get("audience"),
        "tls_certificate_sha256": fingerprint(certificate),
        "tls_serial": str(certificate.serial_number),
        "not_before": certificate.not_valid_before_utc.isoformat(),
        "not_after": certificate.not_valid_after_utc.isoformat(),
        "delegation_certificates": delegations,
        "delegation_key_id": delegations[-1]["key_id"] if delegations else None,
    }


def _signed_by(certificate: x509.Certificate, issuer: x509.Certificate) -> bool:
    if certificate.issuer != issuer.subject or certificate.signature_hash_algorithm is None:
        return False
    try:
        issuer.public_key().verify(
            certificate.signature, certificate.tbs_certificate_bytes, ec.ECDSA(certificate.signature_hash_algorithm)
        )
    except (InvalidSignature, TypeError, ValueError):
        return False
    return True


def _require_ca(certificate: x509.Certificate, intermediates_below: int) -> None:
    try:
        constraints = certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
        usage = certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        raise IssuanceError("CA certificate lacks basic constraints or key usage") from None
    if not constraints.ca or not usage.key_cert_sign:
        raise IssuanceError("Issuer certificate is not a certificate authority")
    if constraints.path_length is not None and intermediates_below > constraints.path_length:
        raise IssuanceError("Certificate chain exceeds the path length constraint")


def _require_valid(certificate: x509.Certificate, now: datetime) -> None:
    if not certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc:
        raise IssuanceError("Certificate is expired or not yet valid")


def verify_chain(
    chain: list[x509.Certificate], roots: list[x509.Certificate], now: datetime, subject_is_ca: bool = False
) -> None:
    """Verify signatures, names, validity, CA constraints and path length of a subject-first chain against trusted roots."""
    if not chain or not roots:
        raise IssuanceError("Certificate chain or trust anchors are missing")
    for certificate in chain:
        _require_valid(certificate, now)
    for index, certificate in enumerate(chain):
        is_last = index + 1 == len(chain)
        candidates = roots if is_last else [chain[index + 1]]
        issuer = next((item for item in candidates if _signed_by(certificate, item)), None)
        if issuer is None:
            raise IssuanceError("Certificate chain does not verify")
        _require_ca(issuer, index)
        if is_last:
            _require_valid(issuer, now)
            if not _signed_by(issuer, issuer):
                raise IssuanceError("Trust anchor is not self-signed")
    try:
        if not subject_is_ca and chain[0].extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise IssuanceError("Leaf certificate must not be a certificate authority")
    except x509.ExtensionNotFound:
        pass  # A leaf without BasicConstraints is not a CA, which is what this check requires.


def next_version(now: datetime, previous: int) -> int:
    return max(int(now.timestamp()), previous + 1)


def _trust_content(bundle: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in bundle.items() if key not in {"generated_at", "bundle_version", "signature"}}


def sign_trust_bundle(document: dict[str, Any], signer: Signer) -> dict[str, Any]:
    unsigned = {key: value for key, value in document.items() if key != "signature"}
    return {**unsigned, "signature": base64.b64encode(signer.sign(canonical_json(unsigned))).decode("ascii")}


def verify_trust_bundle(bundle: dict[str, Any], now: datetime | None = None) -> None:
    now = now or utc_now()
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise IssuanceError("Trust bundle schema is unsupported")
    root = load_certificate(bundle["root_pem"])
    intermediate = load_certificate(bundle["intermediate_pem"])
    verify_chain([intermediate], [root], now, subject_is_ca=True)
    unsigned = {key: value for key, value in bundle.items() if key != "signature"}
    try:
        intermediate.public_key().verify(
            base64.b64decode(bundle["signature"], validate=True), canonical_json(unsigned), ec.ECDSA(hashes.SHA256())
        )
    except (InvalidSignature, KeyError, ValueError, TypeError):
        raise IssuanceError("Trust bundle signature does not verify") from None


def trusted_roots(bundle: dict[str, Any]) -> list[x509.Certificate]:
    return [load_certificate(bundle["root_pem"])] + (
        [load_certificate(bundle["previous_root_pem"])] if bundle.get("previous_root_pem") else []
    )


def read_json_secret(vault: VaultClient, secret: str, strict: bool) -> dict[str, Any] | None:
    value = vault.get_secret(secret)
    if value is None or value.strip() in ("", UNISSUED):
        return None
    try:
        document = json.loads(value)
        if not isinstance(document, dict) or document.get("schema_version") != BUNDLE_SCHEMA_VERSION:
            raise ValueError
    except ValueError:
        if strict:
            raise IssuanceError(f"Secret {secret} is not a valid schema {BUNDLE_SCHEMA_VERSION} document") from None
        return None
    return document


def publish_json_secret(vault: VaultClient, secret: str, document: dict[str, Any]) -> None:
    existing = read_json_secret(vault, secret, strict=False)
    previous = int(existing["bundle_version"]) if existing and "bundle_version" in existing else 0
    if int(document["bundle_version"]) <= previous:
        raise IssuanceError(f"Refusing to publish {secret} version {document['bundle_version']}: existing version is {previous}")
    vault.set_secret(secret, _compact_json(document))


def read_ca_state(vault: VaultClient) -> dict[str, Any] | None:
    state = read_json_secret(vault, SECRET_CA_STATE, strict=True)
    if state is None:
        return None
    for field in ("bundle_version", "root_pem", "root_key_kid", "intermediate_pem", "intermediate_key_kid"):
        if field not in state:
            raise IssuanceError(f"{SECRET_CA_STATE} is missing {field}")
    return state


def read_trust_bundle(vault: VaultClient, environment: str, trust_domain: str) -> dict[str, Any] | None:
    bundle = read_json_secret(vault, SECRET_TRUST_BUNDLE, strict=False)
    if bundle is not None and (bundle.get("environment") != environment or bundle.get("trust_domain") != trust_domain):
        raise IssuanceError(f"{SECRET_TRUST_BUNDLE} belongs to a different environment")
    return bundle


def _ca_pem_bundle(state: dict[str, Any]) -> str:
    parts = [state["root_pem"], state["intermediate_pem"]]
    if state.get("previous_root_pem"):
        parts.append(state["previous_root_pem"])
    return "".join(parts)


def _trust_body(
    registry: dict[str, Any],
    environment: str,
    state: dict[str, Any],
    workloads: dict[str, Any],
    revoked_serials: list[str],
    revoked_uris: list[str],
) -> dict[str, Any]:
    trust_domain, _ = environment_settings(registry, environment)
    body: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "environment": environment,
        "trust_domain": trust_domain,
        "root_pem": state["root_pem"],
        "intermediate_pem": state["intermediate_pem"],
        "ca_bundle_pem": _ca_pem_bundle(state),
        "revoked_serials": sorted(set(revoked_serials), key=int),
        "revoked_identity_uris": sorted(set(revoked_uris)),
        "manifest": {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "policy_version": registry["policy_version"],
            "environment": environment,
            "trust_domain": trust_domain,
            "workloads": workloads,
            "route_grants": group_route_grants(
                [grant for grant in registry["route_grants"] if grant["caller"] in workloads and grant["target"] in workloads]
            ),
        },
    }
    if state.get("previous_root_pem"):
        body["previous_root_pem"] = state["previous_root_pem"]
    return body


def publish_trust_bundle(
    vault: VaultClient,
    registry: dict[str, Any],
    environment: str,
    state: dict[str, Any],
    workloads: dict[str, Any],
    revoked_serials: list[str],
    revoked_uris: list[str],
    existing: dict[str, Any] | None,
    now: datetime,
    force: bool = False,
) -> dict[str, Any] | None:
    """Sign and publish the trust bundle when its content changed; returns the new bundle or None when unchanged."""
    body = _trust_body(registry, environment, state, workloads, revoked_serials, revoked_uris)
    if existing is not None and not force and _trust_content(existing) == body:
        try:
            verify_trust_bundle(existing, now)
            return None
        except IssuanceError:
            pass
    signer = vault.get_signer(state["intermediate_key_kid"])
    version = next_version(now, int(existing["bundle_version"]) if existing else 0)
    bundle = sign_trust_bundle({**body, "bundle_version": version, "generated_at": iso(now)}, signer)
    verify_trust_bundle(bundle, now)
    publish_json_secret(vault, SECRET_TRUST_BUNDLE, bundle)
    return bundle


_ROOT_STATE_KEY = ("root_pem", "root_key_kid")
_INTERMEDIATE_STATE_KEY = ("intermediate_pem", "intermediate_key_kid")


def _check_state_keys(
    vault: VaultClient, state: dict[str, Any], fields: tuple[tuple[str, str], ...] = (_ROOT_STATE_KEY, _INTERMEDIATE_STATE_KEY)
) -> None:
    for pem_field, kid_field in fields:
        certificate = load_certificate(state[pem_field])
        if vault.get_key_public(state[kid_field]).public_key.public_numbers() != certificate.public_key().public_numbers():
            raise IssuanceError(f"{SECRET_CA_STATE} key version does not match its certificate")


def run_ca(vault: VaultClient, registry: dict[str, Any], environment: str, now: datetime) -> dict[str, Any]:
    """Bootstrap or renew the root and intermediate certificates, then publish the signed trust bundle."""
    trust_domain, _ = environment_settings(registry, environment)
    state = read_ca_state(vault)
    actions: list[str] = []
    root_name = name(f"WAOOAW {environment} workload root")
    intermediate_name = name(f"WAOOAW {environment} workload intermediate")
    not_before = now - CLOCK_SKEW
    if state is None:
        root_ref = vault.get_key_public(KEY_ROOT)
        intermediate_ref = vault.get_key_public(KEY_INTERMEDIATE)
        root_signer = vault.get_signer(root_ref.kid)
        root = build_ca_certificate(
            root_name, root_name, root_ref.public_key, root_signer, not_before, timedelta(days=ROOT_LIFETIME_DAYS), 1
        )
        intermediate = build_ca_certificate(
            intermediate_name,
            root.subject,
            intermediate_ref.public_key,
            root_signer,
            not_before,
            timedelta(days=INTERMEDIATE_LIFETIME_DAYS),
            0,
        )
        state = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "bundle_version": next_version(now, 0),
            "root_pem": certificate_pem(root),
            "root_key_kid": root_ref.kid,
            "intermediate_pem": certificate_pem(intermediate),
            "intermediate_key_kid": intermediate_ref.kid,
            "previous_root_pem": None,
            "previous_root_until": None,
        }
        actions.append("bootstrap")
    else:
        _check_state_keys(vault, state)
        root = load_certificate(state["root_pem"])
        intermediate = load_certificate(state["intermediate_pem"])
        renew_root = root.not_valid_after_utc - now <= timedelta(days=ROOT_RENEW_DAYS)
        renew_intermediate = intermediate.not_valid_after_utc - now <= timedelta(days=INTERMEDIATE_RENEW_DAYS)
        if renew_root or renew_intermediate:
            state = dict(state)
            if renew_root:
                root_ref = vault.create_key_version(KEY_ROOT)
                root_signer = vault.get_signer(root_ref.kid)
                new_root = build_ca_certificate(
                    root.subject,
                    root.subject,
                    root_ref.public_key,
                    root_signer,
                    not_before,
                    timedelta(days=ROOT_LIFETIME_DAYS),
                    1,
                )
                state.update(
                    previous_root_pem=state["root_pem"],
                    previous_root_until=iso(now + DUAL_TRUST),
                    root_pem=certificate_pem(new_root),
                    root_key_kid=root_ref.kid,
                )
                root = new_root
                actions.append("renew-root")
            else:
                root_signer = vault.get_signer(state["root_key_kid"])
            if renew_intermediate:
                intermediate_ref = vault.create_key_version(KEY_INTERMEDIATE)
                actions.append("renew-intermediate")
            else:
                intermediate_ref = vault.get_key_public(state["intermediate_key_kid"])
                actions.append("resign-intermediate")
            intermediate = build_ca_certificate(
                intermediate.subject,
                root.subject,
                intermediate_ref.public_key,
                root_signer,
                not_before,
                timedelta(days=INTERMEDIATE_LIFETIME_DAYS),
                0,
            )
            state.update(
                intermediate_pem=certificate_pem(intermediate),
                intermediate_key_kid=intermediate_ref.kid,
            )
        previous_until = state.get("previous_root_until")
        if state.get("previous_root_pem") and (
            not previous_until
            or datetime.fromisoformat(previous_until) <= now
            or load_certificate(state["previous_root_pem"]).not_valid_after_utc <= now
        ):
            state = {**state, "previous_root_pem": None, "previous_root_until": None}
            actions.append("drop-previous-root")
        if actions:
            state["bundle_version"] = next_version(now, int(state["bundle_version"]))
    verify_chain([intermediate], [root], now, subject_is_ca=True)
    if actions:
        publish_json_secret(vault, SECRET_CA_STATE, state)
    existing = read_trust_bundle(vault, environment, trust_domain)
    workloads = _known_workloads(registry, existing)
    published = publish_trust_bundle(
        vault,
        registry,
        environment,
        state,
        workloads,
        existing["revoked_serials"] if existing else [],
        existing["revoked_identity_uris"] if existing else [],
        existing,
        now,
    )
    return {
        "mode": "ca",
        "actions": actions,
        "trust_bundle_version": published["bundle_version"] if published else existing["bundle_version"],
        "trust_bundle_published": published is not None,
    }


def _known_workloads(registry: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    if existing is None:
        return {}
    return {key: value for key, value in existing["manifest"]["workloads"].items() if key in registry["workloads"]}


def parse_workloads(registry: dict[str, Any], value: str | list[str] | None) -> list[str]:
    items = value.split(",") if isinstance(value, str) else list(value or DEFAULT_WORKLOADS)
    names = list(dict.fromkeys(item.strip() for item in items if item.strip()))
    if not names:
        raise IssuanceError("No workloads were requested")
    unknown = [item for item in names if item not in registry["workloads"]]
    if unknown:
        raise IssuanceError(f"Unknown workload in request: {', '.join(unknown)}")
    return names


def _leaf_reason(
    bundle: dict[str, Any] | None,
    record: dict[str, Any] | None,
    state: dict[str, Any],
    identity_uri: str,
    revoked_serials: set[str],
    now: datetime,
    renew_after: timedelta,
) -> str | None:
    if bundle is None:
        return "no-bundle"
    try:
        chain = x509.load_pem_x509_certificates(bundle["tls_cert_pem"].encode("ascii"))
        leaf = chain[0]
        not_after = datetime.fromisoformat(bundle["not_after"])
        issued_at = datetime.fromisoformat(bundle["generated_at"])
    except (KeyError, ValueError, IndexError, TypeError):
        return "invalid-bundle"
    if bundle.get("identity_uri") != identity_uri:
        return "identity-changed"
    if str(leaf.serial_number) in revoked_serials:
        return "revoked-serial"
    if not_after <= now or leaf.not_valid_after_utc <= now:
        return "expired"
    if now - issued_at >= renew_after:
        return "age"
    if len(chain) < 2 or certificate_pem(chain[1]) != state["intermediate_pem"]:
        return "intermediate-changed"
    if record is None or record.get("tls_certificate_sha256") != fingerprint(leaf):
        return "manifest-mismatch"
    return None


def run_leaf(
    vault: VaultClient,
    registry: dict[str, Any],
    environment: str,
    workloads: list[str],
    now: datetime,
    force: bool = False,
) -> dict[str, Any]:
    """Issue short-lived leaves for the requested workloads; trust bundle is published before the workload bundles."""
    trust_domain, lifetime = environment_settings(registry, environment)
    names = parse_workloads(registry, workloads)
    state = read_ca_state(vault)
    if state is None:
        raise IssuanceError(f"{SECRET_CA_STATE} has not been issued; run the ca mode first")
    # The leaf issuer holds no grant on the root key: only the CA rotator may read or use it. The root
    # certificate in the CA state still anchors the chain check below.
    _check_state_keys(vault, state, (_INTERMEDIATE_STATE_KEY,))
    intermediate = load_certificate(state["intermediate_pem"])
    root = load_certificate(state["root_pem"])
    verify_chain([intermediate], [root], now, subject_is_ca=True)
    signer = vault.get_signer(state["intermediate_key_kid"])
    existing = read_trust_bundle(vault, environment, trust_domain)
    revoked_serials = list(existing["revoked_serials"]) if existing else []
    revoked_uris = list(existing["revoked_identity_uris"]) if existing else []
    manifest_workloads = _known_workloads(registry, existing)
    renew_after = min(LEAF_RENEW_AFTER, lifetime / 3)
    rejected: list[str] = []
    pending: list[tuple[str, dict[str, Any]]] = []
    issued: list[str] = []
    skipped: list[str] = []
    for workload in names:
        identity_uri = workload_identity_uri(registry, environment, workload)
        if identity_uri in revoked_uris:
            rejected.append(workload)
            continue
        current = read_json_secret(vault, f"{BUNDLE_SECRET_PREFIX}{workload}", strict=False)
        reason = _leaf_reason(
            current, manifest_workloads.get(workload), state, identity_uri, set(revoked_serials), now, renew_after
        )
        if force and reason is None:
            reason = "forced"
        previous_delegations = [
            item
            for item in (manifest_workloads.get(workload) or {}).get("delegation_certificates", [])
            if datetime.fromisoformat(item["not_after"]) > now
        ]
        if reason is None:
            record = manifest_workloads.get(workload)
            if record is not None and record.get("delegation_certificates") != previous_delegations:
                manifest_workloads[workload] = {**record, "delegation_certificates": previous_delegations}
            skipped.append(workload)
            continue
        credential = issue_workload_credential(
            registry, environment, workload, generate_key(), intermediate, signer, now - CLOCK_SKEW, lifetime
        )
        verify_chain([credential.tls_certificate, intermediate], [root], now)
        delegations = list(previous_delegations)
        activate_after = None
        if credential.delegation_certificate is not None:
            activate_after = now + DELEGATION_ACTIVATION_DELAY
            delegations.append(delegation_entry(credential.delegation_certificate, activate_after))
        manifest_workloads[workload] = workload_record(registry, credential, workload, delegations)
        version = next_version(now, int(current["bundle_version"]) if current and "bundle_version" in current else 0)
        pending.append((workload, _workload_bundle(environment, workload, version, now, credential, state, activate_after)))
        issued.append(f"{workload}:{reason}")
    publish_trust_bundle(vault, registry, environment, state, manifest_workloads, revoked_serials, revoked_uris, existing, now)
    for workload, bundle in pending:
        publish_json_secret(vault, f"{BUNDLE_SECRET_PREFIX}{workload}", bundle)
    if rejected:
        raise IssuanceError(f"Workload is suspended or revoked: {', '.join(rejected)}")
    return {"mode": "leaf", "issued": issued, "unchanged": skipped}


def _workload_bundle(
    environment: str,
    workload: str,
    version: int,
    now: datetime,
    credential: WorkloadCredential,
    state: dict[str, Any],
    activate_after: datetime | None,
) -> dict[str, Any]:
    delegation = credential.delegation_certificate
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_version": version,
        "environment": environment,
        "workload": workload,
        "identity_uri": credential.identity_uri,
        "generated_at": iso(now),
        "not_after": iso(credential.tls_certificate.not_valid_after_utc),
        "tls_key_pem": private_key_pem(credential.tls_key),
        "tls_cert_pem": certificate_pem(credential.tls_certificate) + state["intermediate_pem"],
        "delegation_key_pem": private_key_pem(credential.delegation_key) if credential.delegation_key else None,
        "delegation_cert_pem": certificate_pem(delegation) if delegation else None,
        "delegation_key_id": key_id(delegation.public_key()) if delegation else None,
        "delegation_activate_after": iso(activate_after) if activate_after else None,
    }


def run_revoke(
    vault: VaultClient,
    registry: dict[str, Any],
    environment: str,
    now: datetime,
    serials: list[str] | None = None,
    identity_uris: list[str] | None = None,
    suspend: str | None = None,
    resume: str | None = None,
) -> dict[str, Any]:
    """Add serials or identity URIs to the signed revocation list, suspend or resume a workload, and republish."""
    if not (serials or identity_uris or suspend or resume):
        raise IssuanceError("Nothing to revoke: provide a serial, identity URI, suspend or resume")
    trust_domain, _ = environment_settings(registry, environment)
    state = read_ca_state(vault)
    existing = read_trust_bundle(vault, environment, trust_domain)
    if state is None or existing is None:
        raise IssuanceError("Nothing has been issued yet; there is no trust bundle to revoke from")
    registered = {workload_identity_uri(registry, environment, item): item for item in registry["workloads"]}
    revoked_serials = set(existing["revoked_serials"])
    revoked_uris = set(existing["revoked_identity_uris"])
    for serial in serials or []:
        if not serial.isdigit():
            raise IssuanceError("Serial numbers must be decimal")
        revoked_serials.add(str(int(serial)))
    for uri in identity_uris or []:
        if uri not in registered:
            raise IssuanceError("Identity URI is not a registered workload identity")
        revoked_uris.add(uri)
    workloads = _known_workloads(registry, existing)
    for workload, adding in ((suspend, True), (resume, False)):
        if workload is None:
            continue
        uri = workload_identity_uri(registry, environment, workload)
        if adding:
            revoked_uris.add(uri)
            record = workloads.get(workload)
            if record is not None:
                revoked_serials.add(record["tls_serial"])
                revoked_serials.update(
                    str(load_certificate(item["certificate_pem"]).serial_number) for item in record["delegation_certificates"]
                )
        else:
            revoked_uris.discard(uri)
    bundle = publish_trust_bundle(
        vault, registry, environment, state, workloads, sorted(revoked_serials), sorted(revoked_uris), existing, now, force=True
    )
    return {
        "mode": "revoke",
        "trust_bundle_version": bundle["bundle_version"] if bundle else existing["bundle_version"],
        "revoked_serials": len(revoked_serials),
        "revoked_identity_uris": sorted(revoked_uris),
    }


def run_status(
    vault: VaultClient, registry: dict[str, Any], environment: str, workloads: list[str], now: datetime
) -> tuple[dict[str, Any], bool]:
    """Secret-free summary; the flag is False when anything is missing, invalid or under four hours."""
    trust_domain, _ = environment_settings(registry, environment)
    names = parse_workloads(registry, workloads)
    problems: list[str] = []
    summary: dict[str, Any] = {"environment": environment, "checked_at": iso(now), "workloads": {}}
    state = read_ca_state(vault)
    trust = read_trust_bundle(vault, environment, trust_domain)
    roots: list[x509.Certificate] = []
    if state is None:
        problems.append("ca-state-missing")
    else:
        for field in ("root", "intermediate"):
            certificate = load_certificate(state[f"{field}_pem"])
            summary[field] = {
                "not_after": iso(certificate.not_valid_after_utc),
                "days_left": round((certificate.not_valid_after_utc - now).total_seconds() / 86400, 2),
            }
        summary["previous_root_until"] = state.get("previous_root_until")
    if trust is None:
        problems.append("trust-bundle-missing")
    else:
        try:
            verify_trust_bundle(trust, now)
            roots = trusted_roots(trust)
        except IssuanceError as error:
            problems.append(f"trust-bundle-invalid: {error}")
        summary["trust_bundle"] = {
            "bundle_version": trust["bundle_version"],
            "generated_at": trust["generated_at"],
            "revoked_serials": len(trust["revoked_serials"]),
            "revoked_identity_uris": len(trust["revoked_identity_uris"]),
        }
    for workload in names:
        bundle = read_json_secret(vault, f"{BUNDLE_SECRET_PREFIX}{workload}", strict=False)
        if bundle is None:
            summary["workloads"][workload] = {"state": "missing"}
            problems.append(f"{workload}-bundle-missing")
            continue
        try:
            remaining = datetime.fromisoformat(bundle["not_after"]) - now
        except (KeyError, ValueError, TypeError):
            summary["workloads"][workload] = {"state": "invalid"}
            problems.append(f"{workload}-bundle-invalid")
            continue
        entry = {
            "bundle_version": bundle["bundle_version"],
            "not_after": bundle["not_after"],
            "remaining_seconds": int(remaining.total_seconds()),
        }
        summary["workloads"][workload] = entry
        if remaining < MINIMUM_REMAINING:
            problems.append(f"{workload}-remaining-below-4h")
        if roots:
            try:
                chain = x509.load_pem_x509_certificates(bundle["tls_cert_pem"].encode("ascii"))
                verify_chain(chain, roots, now)
            except (IssuanceError, ValueError):
                problems.append(f"{workload}-chain-invalid")
    summary["problems"] = problems
    return summary, not problems


class CloudFixture(dict):
    """Secret-name to JSON-string mapping with the backing FakeKeyVault and its parameters attached."""

    vault: FakeKeyVault
    registry_path: Path
    environment: str
    workloads: list[str]


def _snapshot(fixture: CloudFixture) -> CloudFixture:
    snapshot = CloudFixture()
    snapshot.vault, snapshot.registry_path = fixture.vault, fixture.registry_path
    snapshot.environment, snapshot.workloads = fixture.environment, fixture.workloads
    for secret in (SECRET_TRUST_BUNDLE, *(f"{BUNDLE_SECRET_PREFIX}{item}" for item in fixture.workloads)):
        snapshot[secret] = fixture.vault.secrets[secret]
    return snapshot


def build_cloud_fixture(
    registry_path: Path, environment: str, workloads: list[str] | None = None, now: datetime | None = None
) -> CloudFixture:
    registry = load_registry(Path(registry_path))
    names = parse_workloads(registry, workloads)
    fixture = CloudFixture()
    fixture.vault = FakeKeyVault().provision(names)
    fixture.registry_path, fixture.environment, fixture.workloads = Path(registry_path), environment, names
    moment = now or utc_now()
    run_ca(fixture.vault, registry, environment, moment)
    run_leaf(fixture.vault, registry, environment, names, moment)
    return _snapshot(fixture)


def renew_cloud_fixture(fixture: CloudFixture, now: datetime) -> CloudFixture:
    """Run ca then leaf again at a later time against the same FakeKeyVault."""
    registry = load_registry(fixture.registry_path)
    run_ca(fixture.vault, registry, fixture.environment, now)
    run_leaf(fixture.vault, registry, fixture.environment, fixture.workloads, now)
    return _snapshot(fixture)
