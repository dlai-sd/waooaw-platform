from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from goal006_registry_manifest import RELEASE_MEMBERS, create_registry_manifest, validate_registry_manifest


def digest(value: str) -> str:
    return "sha256:" + value * 64


def write_digests(directory: Path) -> None:
    for index, member in enumerate(sorted(RELEASE_MEMBERS)):
        (directory / f"{member}.digest").write_text(digest(format(index, "x")), encoding="utf-8")


def write_evidence(directory: Path) -> None:
    for member in sorted(RELEASE_MEMBERS):
        (directory / f"trivy-{member}.sarif").write_text(
            '{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"Trivy"}},"results":[]}]}\n',
            encoding="utf-8",
        )
        (directory / f"{member}.sbom.json").write_text(
            '{"linux/amd64":{"SPDX":{"SPDXID":"SPDXRef-DOCUMENT","spdxVersion":"SPDX-2.3",'
            '"documentNamespace":"https://waooaw.test/sbom","packages":[]}}}\n',
            encoding="utf-8",
        )
        (directory / f"{member}.provenance.json").write_text(
            '{"linux/amd64":{"SLSA":{"buildDefinition":{"buildType":"https://mobyproject.org/buildkit@v1"},'
            '"runDetails":{"builder":{"id":"https://github.com/dlai-sd/waooaw-platform/actions/runs/12345/attempts/1"}}}}}\n',
            encoding="utf-8",
        )
        (directory / f"{member}.signature.jsonl").write_text(
            '{"dsseEnvelope":{"payload":"test"},"verificationMaterial":{"certificate":"test"}}\n',
            encoding="utf-8",
        )


def test_create_exact_six_digest_qualified_manifest(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    assert validate_registry_manifest(manifest, evidence_directory=tmp_path) == []
    assert set(manifest["images"]) == RELEASE_MEMBERS
    assert all("@sha256:" in reference for reference in manifest["images"].values())
    assert set(manifest["evidence"]) == RELEASE_MEMBERS


def test_direct_single_platform_spdx_document_is_accepted(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    (tmp_path / "web.sbom.json").write_text(
        '{"SPDX":{"SPDXID":"SPDXRef-DOCUMENT","spdxVersion":"SPDX-2.3",'
        '"documentNamespace":"https://waooaw.test/sbom","packages":[]}}\n',
        encoding="utf-8",
    )
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    assert validate_registry_manifest(manifest, evidence_directory=tmp_path) == []


@pytest.mark.parametrize("payload", ["{}", '{"unrelated":true}', '{"SPDX":{}}'])
def test_direct_spdx_document_still_fails_closed(tmp_path: Path, payload: str) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    (tmp_path / "web.sbom.json").write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid registry SPDX evidence"):
        create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")


def test_missing_or_additional_digest_file_is_rejected(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    (tmp_path / "web.digest").unlink()
    with pytest.raises(ValueError, match="exactly the six"):
        create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")


@pytest.mark.parametrize("value", ["latest", "sha-main", "sha256:1234", "sha256:" + "G" * 64])
def test_mutable_or_invalid_digest_is_rejected(tmp_path: Path, value: str) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    (tmp_path / "web.digest").write_text(value, encoding="utf-8")
    with pytest.raises(ValueError, match="web:IMAGE_REFERENCE_INVALID"):
        create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")


def test_manifest_tampering_is_detected(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    tampered = copy.deepcopy(manifest)
    tampered["images"]["web"] = "ghcr.io/dlai-sd/web:latest"
    assert "web:IMAGE_REFERENCE_INVALID" in validate_registry_manifest(tampered)


def test_manifest_must_match_triggering_source_and_run(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    assert validate_registry_manifest(manifest, "a" * 40, "12345") == []
    violations = validate_registry_manifest(manifest, "b" * 40, "67890")
    assert "SOURCE_COMMIT_MISMATCH" in violations
    assert "QUALIFICATION_RUN_MISMATCH" in violations


def test_manifest_rejects_missing_or_tampered_supply_chain_evidence(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    del manifest["evidence"]["web"]
    assert "EVIDENCE_MEMBERSHIP_INVALID" in validate_registry_manifest(manifest)

    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    manifest["evidence"]["web"]["scan"]["sha256"] = "0" * 63
    assert "web:SCAN_EVIDENCE_INVALID" in validate_registry_manifest(manifest)

    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    manifest["evidence"]["web"]["sbom"]["sha256"] = "0" * 63
    manifest["evidence"]["web"]["provenance"]["artifact"] = "self-declared"
    violations = validate_registry_manifest(manifest)
    assert "web:SBOM_EVIDENCE_INVALID" in violations
    assert "web:PROVENANCE_EVIDENCE_INVALID" in violations


def test_missing_registry_attestation_content_is_rejected(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    (tmp_path / "web.sbom.json").unlink()
    with pytest.raises(ValueError, match="exactly six registry SBOM, provenance and signature files"):
        create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")


def test_invalid_or_mismatched_evidence_content_is_rejected(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    (tmp_path / "web.sbom.json").write_text('{"unrelated":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid registry SPDX evidence"):
        create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")

    write_evidence(tmp_path)
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    (tmp_path / "web.provenance.json").write_text('{}\n', encoding="utf-8")
    assert "web:PROVENANCE_CONTENT_MISMATCH" in validate_registry_manifest(
        manifest, evidence_directory=tmp_path
    )


def test_cli_verification_fails_closed_on_tampering(tmp_path: Path) -> None:
    write_digests(tmp_path)
    write_evidence(tmp_path)
    manifest = create_registry_manifest(tmp_path, tmp_path, "a" * 40, "12345")
    manifest["images"]["web"] = "ghcr.io/dlai-sd/web:latest"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/goal006_registry_manifest.py", "--verify-manifest", str(manifest_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "web:IMAGE_REFERENCE_INVALID" in result.stdout