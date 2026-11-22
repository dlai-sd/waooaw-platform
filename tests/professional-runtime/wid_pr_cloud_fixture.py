"""Self-contained ADR-046 Amendment 1 cloud credential documents (contract section 8) for Professional Runtime tests."""

# Implements: workload-identity-cloud-issuance-contract.md section 8
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier

DELEGATION_OID = ObjectIdentifier("1.3.6.1.4.1.55555.46.1")
SERVER = ExtendedKeyUsageOID.SERVER_AUTH
CLIENT = ExtendedKeyUsageOID.CLIENT_AUTH
TRUST_DOMAIN = "demo.waooaw.internal"
BP_URI = f"spiffe://{TRUST_DOMAIN}/workload/business-platform"
PR_URI = f"spiffe://{TRUST_DOMAIN}/workload/professional-runtime"
PR_AUDIENCE = "urn:waooaw:service:professional-runtime"
PROJECTION_ROUTE = "/api/v1/internal/relationships/{relationshipId}/workspace-execution"
PROJECTION_OPERATION = "getRelationshipExecutionProjection"
ROUTE_GRANTS: list[dict[str, Any]] = [
    {
        "caller": "business-platform",
        "target": "professional-runtime",
        "method": "GET",
        "route": "/internal/v1/service-link",
        "operation": "probeServiceLink",
        "contract_major": 1,
    },
    {
        "caller": "business-platform",
        "target": "professional-runtime",
        "method": "GET",
        "route": PROJECTION_ROUTE,
        "operation": PROJECTION_OPERATION,
        "contract_major": 1,
    },
    {
        "caller": "professional-runtime",
        "target": "ai-runtime",
        "method": "POST",
        "route": "/internal/v1/conversation-generations",
        "operation": "generateConversation",
        "contract_major": 1,
    },
]


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def pem(*certificates: x509.Certificate) -> str:
    return "".join(item.public_bytes(serialization.Encoding.PEM).decode() for item in certificates)


def key_pem(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


def key_id(key: ec.EllipticCurvePrivateKey) -> str:
    der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest()[:32]


def _ca(subject: str, issuer: x509.Name, key: Any, signer: Any, now: datetime, path_length: int) -> x509.Certificate:
    return (
        x509.CertificateBuilder()
        .subject_name(_name(subject))
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(hours=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=path_length), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
        .sign(signer, hashes.SHA256())
    )


@dataclass
class Cloud:
    """A fake cloud CA: root, intermediate, and the ability to issue leaves and publish signed bundles."""

    now: datetime
    environment: str = "demo"
    trust_domain: str = TRUST_DOMAIN
    root_key: Any = field(default_factory=lambda: ec.generate_private_key(ec.SECP256R1()))
    intermediate_key: Any = field(default_factory=lambda: ec.generate_private_key(ec.SECP256R1()))

    def __post_init__(self) -> None:
        self.root = _ca("WAOOAW root", _name("WAOOAW root"), self.root_key, self.root_key, self.now, 1)
        self.intermediate = _ca("WAOOAW intermediate", self.root.subject, self.intermediate_key, self.root_key, self.now, 0)

    def issue(
        self,
        uri: str,
        usages: list[ObjectIdentifier],
        key: Any = None,
        start: timedelta = timedelta(minutes=-5),
        lifetime: timedelta = timedelta(hours=24),
    ) -> tuple[Any, x509.Certificate]:
        key = key or ec.generate_private_key(ec.SECP256R1())
        certificate = (
            x509.CertificateBuilder()
            .subject_name(_name(uri.rsplit("/", 1)[-1]))
            .issuer_name(self.intermediate.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now + start)
            .not_valid_after(self.now + start + lifetime)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(uri)]), critical=True)
            .add_extension(x509.ExtendedKeyUsage(usages), critical=True)
            .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
            .sign(self.intermediate_key, hashes.SHA256())
        )
        return key, certificate

    def delegation(
        self,
        usages: list[ObjectIdentifier] | None = None,
        activate_after: timedelta | None = None,
        start: timedelta = timedelta(minutes=-5),
        lifetime: timedelta = timedelta(hours=24),
        issuer: Cloud | None = None,
        uri: str = BP_URI,
    ) -> tuple[Any, x509.Certificate, dict[str, Any]]:
        key, certificate = (issuer or self).issue(uri, usages or [DELEGATION_OID], start=start, lifetime=lifetime)
        entry = {
            "key_id": key_id(key),
            "certificate_pem": pem(certificate),
            "not_before": certificate.not_valid_before_utc.isoformat(),
            "not_after": certificate.not_valid_after_utc.isoformat(),
            "activate_after": (self.now + activate_after).isoformat() if activate_after is not None else None,
        }
        return key, certificate, entry

    def trust_bundle(
        self,
        version: int,
        delegations: list[dict[str, Any]],
        *,
        environment: str | None = None,
        trust_domain: str | None = None,
        revoked_serials: list[int] | None = None,
        revoked_uris: list[str] | None = None,
        signing_key: Any = None,
    ) -> dict[str, Any]:
        environment = environment or self.environment
        domain = trust_domain or self.trust_domain
        bundle: dict[str, Any] = {
            "schema_version": "1.1",
            "bundle_version": version,
            "environment": environment,
            "trust_domain": domain,
            "generated_at": self.now.isoformat(),
            "root_pem": pem(self.root),
            "intermediate_pem": pem(self.intermediate),
            "ca_bundle_pem": pem(self.root, self.intermediate),
            "revoked_serials": [str(serial) for serial in revoked_serials or []],
            "revoked_identity_uris": revoked_uris or [],
            "manifest": {
                "schema_version": "1.0",
                "policy_version": "1.1",
                "environment": environment,
                "trust_domain": domain,
                "workloads": {
                    "business-platform": {
                        "identity_uri": BP_URI,
                        "audience": "urn:waooaw:service:business-platform",
                        "delegation_certificates": delegations,
                        "delegation_key_id": delegations[-1]["key_id"] if delegations else None,
                    },
                    "professional-runtime": {"identity_uri": PR_URI, "audience": PR_AUDIENCE},
                    "ai-runtime": {
                        "identity_uri": f"spiffe://{domain}/workload/ai-runtime",
                        "audience": "urn:waooaw:service:ai-runtime",
                    },
                },
                "route_grants": ROUTE_GRANTS,
            },
        }
        return sign(bundle, signing_key or self.intermediate_key)

    def workload_bundle(
        self,
        version: int,
        key: Any,
        certificate: x509.Certificate,
        *,
        environment: str | None = None,
        uri: str = PR_URI,
        workload: str = "professional-runtime",
        chain: list[x509.Certificate] | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": "1.1",
            "bundle_version": version,
            "environment": environment or self.environment,
            "workload": workload,
            "identity_uri": uri,
            "generated_at": self.now.isoformat(),
            "not_after": certificate.not_valid_after_utc.isoformat(),
            "tls_key_pem": key_pem(key),
            "tls_cert_pem": pem(*(chain or [certificate, self.intermediate])),
            "delegation_key_pem": None,
            "delegation_cert_pem": None,
            "delegation_key_id": None,
            "delegation_activate_after": None,
        }


def sign(bundle: dict[str, Any], key: Any) -> dict[str, Any]:
    unsigned = {name: value for name, value in bundle.items() if name != "signature"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return {**unsigned, "signature": base64.b64encode(key.sign(canonical, ec.ECDSA(hashes.SHA256()))).decode()}


def text(document: dict[str, Any]) -> str:
    return json.dumps(document)


@dataclass
class Pair:
    cloud: Cloud
    trust: dict[str, Any]
    bundle: dict[str, Any]
    leaf_key: Any
    leaf: x509.Certificate
    bp_key: Any
    bp_leaf_key: Any
    bp_leaf: x509.Certificate

    @property
    def texts(self) -> tuple[str, str]:
        return text(self.trust), text(self.bundle)


def build_pair(cloud: Cloud, version: int = 100, own_version: int = 100, **options: Any) -> Pair:
    """A valid trust bundle and Professional Runtime bundle; options bend exactly one rule at a time."""
    leaf_key, leaf = cloud.issue(
        options.get("leaf_uri", PR_URI),
        options.get("usages", [SERVER, CLIENT]),
        start=options.get("leaf_start", timedelta(minutes=-5)),
        lifetime=options.get("leaf_lifetime", timedelta(hours=24)),
    )
    bundle_key = ec.generate_private_key(ec.SECP256R1()) if options.get("key_mismatch") else leaf_key
    bp_key, _, entry = cloud.delegation(**options.get("delegation", {}))
    delegations = [entry, *options.get("extra_delegations", [])]
    bp_leaf_key, bp_leaf = cloud.issue(BP_URI, [CLIENT, SERVER])
    trust = cloud.trust_bundle(
        version,
        delegations,
        environment=options.get("trust_environment"),
        trust_domain=options.get("trust_domain"),
        revoked_serials=[leaf.serial_number] if options.get("revoke_leaf") else options.get("revoked_serials"),
        revoked_uris=options.get("revoked_uris"),
    )
    own = cloud.workload_bundle(own_version, bundle_key, leaf, environment=options.get("bundle_environment"))
    return Pair(cloud, trust, own, leaf_key, leaf, bp_key, bp_leaf_key, bp_leaf)


def new_cloud(now: datetime | None = None) -> Cloud:
    return Cloud((now or datetime.now(timezone.utc)).replace(microsecond=0))
