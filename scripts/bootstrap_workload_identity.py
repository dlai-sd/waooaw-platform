#!/usr/bin/env python3
"""Generate fresh ADR-046 development or CI workload credentials."""

# Implements: ADR-046 sections 3.1, 4.1, 4.2, 7.2, and 10.1
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


sys.path.insert(0, str(Path(__file__).resolve().parent))

from workload_identity_issuance import (
    DELEGATION_SIGNING_OID,
    INTERMEDIATE_LIFETIME_DAYS,
    ROOT_LIFETIME_DAYS,
    LocalKeySigner,
    build_ca_certificate,
    delegation_entry,
    fingerprint,
    issue_workload_credential,
    load_registry,
    name,
    workload_record,
)


__all__ = ["DELEGATION_SIGNING_OID", "bootstrap", "main"]


def _generate_ec_key(curve: ec.EllipticCurve) -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(curve)


def _write_private_key(path: Path, key: Any) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def _write_certificate(path: Path, certificate: x509.Certificate, chain: tuple[x509.Certificate, ...] = ()) -> None:
    path.write_bytes(b"".join(value.public_bytes(serialization.Encoding.PEM) for value in (certificate, *chain)))
    path.chmod(0o644)


def bootstrap(registry_path: Path, environment: str, output: Path) -> dict[str, Any]:
    registry = load_registry(registry_path)
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
    root_signer = LocalKeySigner(root_key, "development-root")
    root_name = name(f"WAOOAW {environment} ephemeral root")
    root = build_ca_certificate(
        root_name, root_name, root_key.public_key(), root_signer, now, timedelta(days=ROOT_LIFETIME_DAYS), 1
    )
    intermediate_key = _generate_ec_key(ec.SECP384R1())
    intermediate_signer = LocalKeySigner(intermediate_key, "development-intermediate")
    intermediate = build_ca_certificate(
        name(f"WAOOAW {environment} workload intermediate"),
        root.subject,
        intermediate_key.public_key(),
        root_signer,
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
        "root_fingerprint_sha256": fingerprint(root),
        "intermediate_fingerprint_sha256": fingerprint(intermediate),
        "workloads": {},
        "route_grants": registry["route_grants"],
    }
    public_keys: set[bytes] = set()
    for workload_name in registry["workloads"]:
        workload_dir = output / "workloads" / workload_name
        workload_dir.mkdir(parents=True, mode=0o700)
        tls_key = _generate_ec_key(ec.SECP256R1())
        public_bytes = tls_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if public_bytes in public_keys:
            raise RuntimeError("Workload keys must be unique")
        public_keys.add(public_bytes)
        credential = issue_workload_credential(
            registry, environment, workload_name, tls_key, intermediate, intermediate_signer, now, leaf_lifetime
        )
        _write_private_key(workload_dir / "tls-key.pem", tls_key)
        _write_certificate(workload_dir / "tls-cert.pem", credential.tls_certificate, (intermediate,))
        delegations = []
        if credential.delegation_key is not None and credential.delegation_certificate is not None:
            delegations.append(delegation_entry(credential.delegation_certificate, now))
            _write_private_key(workload_dir / "delegation-key.pem", credential.delegation_key)
            _write_certificate(workload_dir / "delegation-cert.pem", credential.delegation_certificate)
        record = workload_record(registry, credential, workload_name, delegations)
        if credential.delegation_certificate is not None:
            record["delegation_certificate_sha256"] = fingerprint(credential.delegation_certificate)
        else:
            del record["delegation_key_id"]
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
