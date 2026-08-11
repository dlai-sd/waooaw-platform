# Implements: ADR-046 sections 3.1, 3.2, 4, 7.2, and 10 items 1, 4, 9, 13, 14
# constitutional_basis: C-026, C-059, C-063, C-076, C-080, C-083, C-084, C-085

from __future__ import annotations

import json
import stat
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID

import scripts.bootstrap_workload_identity as pki_bootstrap
from scripts.bootstrap_workload_identity import DELEGATION_SIGNING_OID, bootstrap


REPO_ROOT = Path(__file__).parents[2]
REGISTRY_PATH = REPO_ROOT / "infrastructure/workload-identity/registry.yaml"
PRIVATE_SPECS = {
    "billing-engine": REPO_ROOT / "architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml",
    "professional-runtime": REPO_ROOT / "architecture/reference/api-specs/professional-runtime.openapi.yaml",
    "domain-adapter-dma": REPO_ROOT / "architecture/reference/api-specs/dma-relationship-outcome-adapter.openapi.yaml",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _operations(path: Path) -> set[tuple[str, str, str, int]]:
    spec = _load_yaml(path)
    major = int(spec["info"]["version"].split(".", maxsplit=1)[0])
    return {
        (method.upper(), route, operation["operationId"], major)
        for route, path_item in spec["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
        and operation.get("x-internal") is True
        and "relationship" in route
    }


def _certificate(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def _public_key_bytes(path: Path) -> bytes:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    return key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _bootstrap(tmp_path: Path, environment: str) -> tuple[Path, dict[str, Any]]:
    output = tmp_path / environment
    return output, bootstrap(REGISTRY_PATH, environment, output)


def _write_registry(tmp_path: Path, registry: dict[str, Any]) -> Path:
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    return path


def test_registry_exactly_matches_private_f4_operations() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    grants_by_target: dict[str, set[tuple[str, str, str, int]]] = {}
    for grant in registry["route_grants"]:
        assert grant["caller"] == "business-platform"
        grants_by_target.setdefault(grant["target"], set()).add(
            (grant["method"], grant["route"], grant["operation"], grant["contract_major"])
        )

    assert grants_by_target == {
        target: _operations(spec_path) for target, spec_path in PRIVATE_SPECS.items()
    }


@pytest.mark.parametrize(
    ("environment", "trust_domain", "maximum_hours"),
    [("development", "waooaw.dev", 24), ("ci", "waooaw.ci", 2)],
)
def test_bootstrap_issues_exact_unique_short_lived_workload_identities(
    tmp_path: Path,
    environment: str,
    trust_domain: str,
    maximum_hours: int,
) -> None:
    output, manifest = _bootstrap(tmp_path, environment)
    registry = _load_yaml(REGISTRY_PATH)
    intermediate = _certificate(output / "trust/intermediate.pem")
    keys: set[bytes] = set()
    serials: set[int] = set()

    assert manifest["trust_domain"] == trust_domain
    assert set(manifest["workloads"]) == set(registry["workloads"])
    for workload_name, workload in registry["workloads"].items():
        workload_dir = output / "workloads" / workload_name
        certificate = _certificate(workload_dir / "tls-cert.pem")
        uri_names = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value.get_values_for_type(x509.UniformResourceIdentifier)
        assert uri_names == [f"spiffe://{trust_domain}/workload/{workload['identity_path']}"]
        assert certificate.issuer == intermediate.subject
        intermediate.public_key().verify(
            certificate.signature,
            certificate.tbs_certificate_bytes,
            ec.ECDSA(certificate.signature_hash_algorithm),
        )
        assert certificate.not_valid_after_utc - certificate.not_valid_before_utc <= timedelta(
            hours=maximum_hours
        )
        assert certificate.serial_number not in serials
        serials.add(certificate.serial_number)
        key_bytes = _public_key_bytes(workload_dir / "tls-key.pem")
        assert key_bytes not in keys
        keys.add(key_bytes)


def test_tls_and_delegation_keys_and_key_usages_are_distinct(tmp_path: Path) -> None:
    output, _ = _bootstrap(tmp_path, "ci")
    bp_dir = output / "workloads/business-platform"
    tls_certificate = _certificate(bp_dir / "tls-cert.pem")
    delegation_certificate = _certificate(bp_dir / "delegation-cert.pem")

    assert _public_key_bytes(bp_dir / "tls-key.pem") != _public_key_bytes(bp_dir / "delegation-key.pem")
    assert set(tls_certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value) == {
        ExtendedKeyUsageOID.CLIENT_AUTH,
        ExtendedKeyUsageOID.SERVER_AUTH,
    }
    assert set(delegation_certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value) == {
        DELEGATION_SIGNING_OID
    }


def test_private_keys_and_manifest_have_restricted_modes_and_no_secret_material(tmp_path: Path) -> None:
    output, manifest = _bootstrap(tmp_path, "ci")

    for private_key in output.rglob("*-key.pem"):
        assert stat.S_IMODE(private_key.stat().st_mode) == 0o600
    assert stat.S_IMODE((output / "manifest.json").stat().st_mode) == 0o600
    manifest_text = json.dumps(manifest).lower()
    assert "private key" not in manifest_text
    assert "signature" not in manifest_text
    assert "tenant_id" not in manifest_text
    assert "relationship_id" not in manifest_text


def test_fresh_bootstraps_do_not_share_roots_or_workload_keys(tmp_path: Path) -> None:
    first, first_manifest = _bootstrap(tmp_path / "first", "ci")
    second, second_manifest = _bootstrap(tmp_path / "second", "ci")

    assert first_manifest["root_fingerprint_sha256"] != second_manifest["root_fingerprint_sha256"]
    assert _public_key_bytes(first / "workloads/business-platform/tls-key.pem") != _public_key_bytes(
        second / "workloads/business-platform/tls-key.pem"
    )


def test_bootstrap_rejects_unregistered_environment_and_nonempty_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="registered development and CI"):
        bootstrap(REGISTRY_PATH, "production", tmp_path / "production")

    output = tmp_path / "existing"
    output.mkdir()
    (output / "credential.pem").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(ValueError, match="must be empty"):
        bootstrap(REGISTRY_PATH, "ci", output)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda registry: registry.update(schema_version="2.0"), "Unsupported"),
        (lambda registry: registry.update(route_grants=[]), "workloads and route grants"),
        (
            lambda registry: registry["workloads"]["domain-adapter-dma"].update(
                identity_path="domain-adapter/*"
            ),
            "wildcard or generic adapter",
        ),
        (
            lambda registry: registry["route_grants"][0].update(target="unknown"),
            "unregistered workload",
        ),
        (lambda registry: registry["route_grants"][0].update(method="TRACE"), "method is invalid"),
        (
            lambda registry: registry["route_grants"][0].update(operation="", contract_major=0),
            "operation and contract major",
        ),
    ],
)
def test_registry_validation_fails_closed(
    tmp_path: Path,
    mutation: Any,
    message: str,
) -> None:
    registry = _load_yaml(REGISTRY_PATH)
    mutation(registry)

    with pytest.raises(ValueError, match=message):
        bootstrap(_write_registry(tmp_path, registry), "ci", tmp_path / "output")


def test_duplicate_generated_workload_key_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_key = ec.generate_private_key(ec.SECP384R1())
    intermediate_key = ec.generate_private_key(ec.SECP384R1())
    duplicate_leaf_key = ec.generate_private_key(ec.SECP256R1())
    keys = iter([root_key, intermediate_key, duplicate_leaf_key, duplicate_leaf_key])
    monkeypatch.setattr(pki_bootstrap, "_generate_ec_key", lambda curve: next(keys))

    with pytest.raises(RuntimeError, match="must be unique"):
        bootstrap(REGISTRY_PATH, "ci", tmp_path / "duplicate")


def test_cli_writes_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "cli"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bootstrap_workload_identity.py",
            "--registry",
            str(REGISTRY_PATH),
            "--environment",
            "ci",
            "--output",
            str(output),
        ],
    )

    assert pki_bootstrap.main() == 0
    assert (output / "manifest.json").is_file()