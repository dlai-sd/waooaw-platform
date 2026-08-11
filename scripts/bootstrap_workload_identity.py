#!/usr/bin/env python3
"""Generate fresh ADR-046 development or CI workload credentials."""

# Implements: ADR-046 sections 3.1, 4.1, 4.2, 7.2, and 10.1
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier


ROOT_LIFETIME_DAYS = 365
INTERMEDIATE_LIFETIME_DAYS = 90
DELEGATION_SIGNING_OID = ObjectIdentifier("1.3.6.1.4.1.55555.46.1")


def _generate_ec_key(curve: ec.EllipticCurve) -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(curve)


def _load_registry(path: Path) -> dict[str, Any]:
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "1.0" or registry.get("policy_version") != "1.0":
        raise ValueError("Unsupported workload registry version")
    workloads = registry.get("workloads", {})
    grants = registry.get("route_grants", [])
    if not workloads or not grants:
        raise ValueError("Workload registry must declare workloads and route grants")
    for name, workload in workloads.items():
        identity_path = workload.get("identity_path", "")
        audience = workload.get("audience", "")
        if "*" in identity_path or "*" in audience or identity_path.endswith("domain-adapter"):
            raise ValueError(f"Workload {name} uses a wildcard or generic adapter identity")
    for grant in grants:
        if grant.get("caller") not in workloads or grant.get("target") not in workloads:
            raise ValueError("Route grant references an unregistered workload")
        if grant.get("method") not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Route grant method is invalid")
        if not grant.get("operation") or int(grant.get("contract_major", 0)) < 1:
            raise ValueError("Route grant operation and contract major are required")
    return registry


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _write_private_key(path: Path, key: Any) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def _write_certificate(
    path: Path, certificate: x509.Certificate, chain: tuple[x509.Certificate, ...] = ()
) -> None:
    path.write_bytes(b"".join(
        value.public_bytes(serialization.Encoding.PEM) for value in (certificate, *chain)
    ))
    path.chmod(0o644)


def _fingerprint(certificate: x509.Certificate) -> str:
    return certificate.fingerprint(hashes.SHA256()).hex()


def _ca_certificate(
    subject: x509.Name,
    issuer: x509.Name,
    public_key: Any,
    issuer_key: Any,
    now: datetime,
    lifetime: timedelta,
    path_length: int,
) -> x509.Certificate:
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + lifetime)
        .add_extension(x509.BasicConstraints(ca=True, path_length=path_length), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .sign(issuer_key, hashes.SHA256())
    )


def _leaf_certificate(
    identity_uri: str,
    public_key: Any,
    intermediate: x509.Certificate,
    intermediate_key: Any,
    usages: list[str],
    now: datetime,
    lifetime: timedelta,
) -> x509.Certificate:
    eku = []
    if "client_auth" in usages:
        eku.append(ExtendedKeyUsageOID.CLIENT_AUTH)
    if "server_auth" in usages:
        eku.append(ExtendedKeyUsageOID.SERVER_AUTH)
    if "delegation_signing" in usages:
        eku.append(DELEGATION_SIGNING_OID)
    return (
        x509.CertificateBuilder()
        .subject_name(_name(identity_uri.rsplit("/", 1)[-1]))
        .issuer_name(intermediate.subject)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + lifetime)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(identity_uri)]), critical=True)
        .add_extension(x509.ExtendedKeyUsage(eku), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, False, False, False, False),
            critical=True,
        )
        .sign(intermediate_key, hashes.SHA256())
    )


def bootstrap(registry_path: Path, environment: str, output: Path) -> dict[str, Any]:
    registry = _load_registry(registry_path)
    environment_config = registry.get("environments", {}).get(environment)
    if environment_config is None or environment not in {"development", "ci"}:
        raise ValueError("Only registered development and CI environments may use the local bootstrap")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    output.mkdir(parents=True, mode=0o700, exist_ok=True)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    trust_domain = environment_config["trust_domain"]
    leaf_lifetime = timedelta(hours=int(environment_config["leaf_lifetime_hours"]))

    root_key = _generate_ec_key(ec.SECP384R1())
    root_name = _name(f"WAOOAW {environment} ephemeral root")
    root = _ca_certificate(
        root_name, root_name, root_key.public_key(), root_key, now, timedelta(days=ROOT_LIFETIME_DAYS), 1
    )
    intermediate_key = _generate_ec_key(ec.SECP384R1())
    intermediate = _ca_certificate(
        _name(f"WAOOAW {environment} workload intermediate"),
        root.subject,
        intermediate_key.public_key(),
        root_key,
        now,
        timedelta(days=INTERMEDIATE_LIFETIME_DAYS),
        0,
    )

    trust = output / "trust"
    trust.mkdir(mode=0o700)
    _write_private_key(trust / "root-key.pem", root_key)
    _write_certificate(trust / "root.pem", root)
    _write_private_key(trust / "intermediate-key.pem", intermediate_key)
    _write_certificate(trust / "intermediate.pem", intermediate)
    _write_certificate(trust / "ca-bundle.pem", root, (intermediate,))

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "policy_version": registry["policy_version"],
        "environment": environment,
        "trust_domain": trust_domain,
        "generated_at": now.isoformat(),
        "root_fingerprint_sha256": _fingerprint(root),
        "intermediate_fingerprint_sha256": _fingerprint(intermediate),
        "workloads": {},
        "route_grants": registry["route_grants"],
    }
    public_keys: set[bytes] = set()
    for workload_name, workload in registry["workloads"].items():
        workload_dir = output / "workloads" / workload_name
        workload_dir.mkdir(parents=True, mode=0o700)
        identity_uri = f"spiffe://{trust_domain}/workload/{workload['identity_path']}"
        tls_key = _generate_ec_key(ec.SECP256R1())
        tls_certificate = _leaf_certificate(
            identity_uri,
            tls_key.public_key(),
            intermediate,
            intermediate_key,
            workload["tls_usages"],
            now,
            leaf_lifetime,
        )
        public_bytes = tls_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if public_bytes in public_keys:
            raise RuntimeError("Workload keys must be unique")
        public_keys.add(public_bytes)
        _write_private_key(workload_dir / "tls-key.pem", tls_key)
        _write_certificate(workload_dir / "tls-cert.pem", tls_certificate, (intermediate,))
        record = {
            "identity_uri": identity_uri,
            "audience": workload.get("audience"),
            "tls_certificate_sha256": _fingerprint(tls_certificate),
            "tls_serial": str(tls_certificate.serial_number),
            "not_before": tls_certificate.not_valid_before_utc.isoformat(),
            "not_after": tls_certificate.not_valid_after_utc.isoformat(),
        }
        if workload.get("delegation_signer"):
            delegation_key = ec.generate_private_key(ec.SECP256R1())
            delegation_certificate = _leaf_certificate(
                identity_uri,
                delegation_key.public_key(),
                intermediate,
                intermediate_key,
                ["delegation_signing"],
                now,
                leaf_lifetime,
            )
            _write_private_key(workload_dir / "delegation-key.pem", delegation_key)
            _write_certificate(workload_dir / "delegation-cert.pem", delegation_certificate)
            record["delegation_certificate_sha256"] = _fingerprint(delegation_certificate)
            record["delegation_key_id"] = hashlib.sha256(
                delegation_key.public_key().public_bytes(
                    serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
                )
            ).hexdigest()[:32]
        manifest["workloads"][workload_name] = record

    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--environment", choices=("development", "ci"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    bootstrap(args.registry, args.environment, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())