#!/usr/bin/env python3
"""Create and validate an exact-six immutable GOAL-006 registry manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

RELEASE_MEMBERS = frozenset(
    {"constitutional-engine", "business-platform", "professional-runtime", "ai-runtime", "web", "billing-engine"}
)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_PATTERN = re.compile(r"^[a-z0-9_.-]+/[a-z0-9_.-]+$")
BUILDER_WORKFLOW = ".github/workflows/ci.yaml"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"invalid JSON evidence: {path.name}") from exc


def _validate_scan(path: Path) -> None:
    document = _read_json(path)
    runs = document.get("runs") if isinstance(document, Mapping) else None
    if (
        document.get("version") != "2.1.0"
        or not isinstance(runs, list)
        or not runs
        or any(run.get("tool", {}).get("driver", {}).get("name") != "Trivy" for run in runs)
        or any(run.get("results") for run in runs)
    ):
        raise ValueError(f"invalid successful Trivy SARIF evidence: {path.name}")


def _validate_sbom(path: Path) -> None:
    document = _read_json(path)
    if not isinstance(document, Mapping) or not document:
        raise ValueError(f"invalid registry SPDX evidence: {path.name}")
    for platform, attestation in document.items():
        spdx = attestation.get("SPDX") if isinstance(attestation, Mapping) else None
        if (
            not str(platform).startswith("linux/")
            or not isinstance(spdx, Mapping)
            or spdx.get("SPDXID") != "SPDXRef-DOCUMENT"
            or spdx.get("spdxVersion") != "SPDX-2.3"
            or not isinstance(spdx.get("documentNamespace"), str)
            or not isinstance(spdx.get("packages"), list)
        ):
            raise ValueError(f"invalid registry SPDX evidence: {path.name}")


def _validate_provenance(path: Path, run_id: str) -> None:
    document = _read_json(path)
    expected_builder = f"https://github.com/dlai-sd/waooaw-platform/actions/runs/{run_id}/"
    if not isinstance(document, Mapping) or not document:
        raise ValueError(f"invalid registry SLSA evidence: {path.name}")
    for platform, attestation in document.items():
        slsa = attestation.get("SLSA") if isinstance(attestation, Mapping) else None
        build_type = slsa.get("buildDefinition", {}).get("buildType") if isinstance(slsa, Mapping) else None
        builder_id = slsa.get("runDetails", {}).get("builder", {}).get("id") if isinstance(slsa, Mapping) else None
        if (
            not str(platform).startswith("linux/")
            or not isinstance(build_type, str)
            or "buildkit" not in build_type.lower()
            or not isinstance(builder_id, str)
            or not builder_id.startswith(expected_builder)
        ):
            raise ValueError(f"invalid registry SLSA evidence: {path.name}")


def _validate_signature_bundle(path: Path) -> None:
    try:
        bundles = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"invalid GitHub attestation bundle: {path.name}") from exc
    if not bundles or any(
        not isinstance(bundle, Mapping)
        or not isinstance(bundle.get("dsseEnvelope"), Mapping)
        or not isinstance(bundle.get("verificationMaterial"), Mapping)
        for bundle in bundles
    ):
        raise ValueError(f"invalid GitHub attestation bundle: {path.name}")


def validate_registry_manifest(
    manifest: Mapping[str, Any],
    expected_source_commit: str | None = None,
    expected_run_id: str | None = None,
    evidence_directory: Path | None = None,
) -> list[str]:
    violations: list[str] = []
    images = manifest.get("images")
    evidence = manifest.get("evidence")
    qualification = manifest.get("qualification")
    if manifest.get("schema") != "waooaw.registry-release/v1" or manifest.get("immutable") is not True:
        violations.append("MANIFEST_NOT_IMMUTABLE")
    if not COMMIT_PATTERN.fullmatch(str(manifest.get("source_commit", ""))):
        violations.append("SOURCE_COMMIT_INVALID")
    elif expected_source_commit is not None and manifest.get("source_commit") != expected_source_commit:
        violations.append("SOURCE_COMMIT_MISMATCH")
    if not isinstance(images, Mapping) or set(images) != RELEASE_MEMBERS:
        violations.append("RELEASE_MEMBERSHIP_INVALID")
    else:
        for member, reference in images.items():
            expected_prefix = f"ghcr.io/dlai-sd/{member}@"
            digest = str(reference).removeprefix(expected_prefix)
            if not str(reference).startswith(expected_prefix) or not DIGEST_PATTERN.fullmatch(digest):
                violations.append(f"{member}:IMAGE_REFERENCE_INVALID")
    if not isinstance(evidence, Mapping) or set(evidence) != RELEASE_MEMBERS:
        violations.append("EVIDENCE_MEMBERSHIP_INVALID")
    elif isinstance(images, Mapping):
        for member, record in evidence.items():
            if not isinstance(record, Mapping):
                violations.append(f"{member}:EVIDENCE_INVALID")
                continue
            image = images.get(member)
            scan = record.get("scan")
            sbom = record.get("sbom")
            provenance = record.get("provenance")
            signature = record.get("signature")
            if (
                not isinstance(scan, Mapping)
                or not HEX_DIGEST_PATTERN.fullmatch(str(scan.get("sha256", "")))
                or scan.get("artifact") != f"goal006-scan-{member}"
                or scan.get("policy") != "fixable-high-critical"
            ):
                violations.append(f"{member}:SCAN_EVIDENCE_INVALID")
            if (
                not isinstance(sbom, Mapping)
                or sbom.get("oci_subject") != image
                or sbom.get("format") != "spdx"
                or sbom.get("artifact") != f"goal006-attestation-{member}"
                or not HEX_DIGEST_PATTERN.fullmatch(str(sbom.get("sha256", "")))
            ):
                violations.append(f"{member}:SBOM_EVIDENCE_INVALID")
            if (
                not isinstance(provenance, Mapping)
                or provenance.get("oci_subject") != image
                or provenance.get("mode") != "max"
                or provenance.get("artifact") != f"goal006-attestation-{member}"
                or not HEX_DIGEST_PATTERN.fullmatch(str(provenance.get("sha256", "")))
            ):
                violations.append(f"{member}:PROVENANCE_EVIDENCE_INVALID")
            if (
                not isinstance(signature, Mapping)
                or signature.get("oci_subject") != image
                or signature.get("artifact") != f"goal006-attestation-{member}"
                or signature.get("issuer") != "github-oidc"
                or not HEX_DIGEST_PATTERN.fullmatch(str(signature.get("sha256", "")))
            ):
                violations.append(f"{member}:SIGNATURE_EVIDENCE_INVALID")
            if evidence_directory is not None:
                files = {
                    "scan": evidence_directory / f"trivy-{member}.sarif",
                    "sbom": evidence_directory / f"{member}.sbom.json",
                    "provenance": evidence_directory / f"{member}.provenance.json",
                    "signature": evidence_directory / f"{member}.signature.jsonl",
                }
                for evidence_type, path in files.items():
                    evidence_record = record.get(evidence_type)
                    if (
                        not path.is_file()
                        or not isinstance(evidence_record, Mapping)
                        or hashlib.sha256(path.read_bytes()).hexdigest() != evidence_record.get("sha256")
                    ):
                        violations.append(f"{member}:{evidence_type.upper()}_CONTENT_MISMATCH")
    if not isinstance(qualification, Mapping) or qualification.get("status") != "pass":
        violations.append("QUALIFICATION_INVALID")
    elif expected_run_id is not None and str(qualification.get("github_run_id")) != expected_run_id:
        violations.append("QUALIFICATION_RUN_MISMATCH")
    if manifest.get("builder_workflow") != BUILDER_WORKFLOW:
        violations.append("BUILDER_INVALID")
    return sorted(violations)


def create_registry_manifest(
    digest_directory: Path, evidence_directory: Path, source_commit: str, run_id: str
) -> dict[str, Any]:
    digest_files = {path.stem: path for path in digest_directory.glob("*.digest")}
    if set(digest_files) != RELEASE_MEMBERS:
        raise ValueError("digest directory must contain exactly the six release-member digest files")
    images = {
        member: f"ghcr.io/dlai-sd/{member}@{digest_files[member].read_text(encoding='utf-8').strip()}"
        for member in sorted(RELEASE_MEMBERS)
    }
    scan_files = {path.stem.removeprefix("trivy-"): path for path in evidence_directory.glob("trivy-*.sarif")}
    if set(scan_files) != RELEASE_MEMBERS:
        raise ValueError("evidence directory must contain exactly the six release-member SARIF files")
    sbom_files = {
        path.name.removesuffix(".sbom.json"): path for path in evidence_directory.glob("*.sbom.json")
    }
    provenance_files = {
        path.name.removesuffix(".provenance.json"): path
        for path in evidence_directory.glob("*.provenance.json")
    }
    signature_files = {
        path.name.removesuffix(".signature.jsonl"): path
        for path in evidence_directory.glob("*.signature.jsonl")
    }
    if (
        set(sbom_files) != RELEASE_MEMBERS
        or set(provenance_files) != RELEASE_MEMBERS
        or set(signature_files) != RELEASE_MEMBERS
    ):
        raise ValueError("evidence directory must contain exactly six registry SBOM, provenance and signature files")
    for member in RELEASE_MEMBERS:
        _validate_scan(scan_files[member])
        _validate_sbom(sbom_files[member])
        _validate_provenance(provenance_files[member], run_id)
        _validate_signature_bundle(signature_files[member])
    evidence = {
        member: {
            "scan": {
                "artifact": f"goal006-scan-{member}",
                "policy": "fixable-high-critical",
                "sha256": hashlib.sha256(scan_files[member].read_bytes()).hexdigest(),
            },
            "sbom": {
                "artifact": f"goal006-attestation-{member}",
                "format": "spdx",
                "oci_subject": images[member],
                "sha256": hashlib.sha256(sbom_files[member].read_bytes()).hexdigest(),
            },
            "provenance": {
                "artifact": f"goal006-attestation-{member}",
                "mode": "max",
                "oci_subject": images[member],
                "sha256": hashlib.sha256(provenance_files[member].read_bytes()).hexdigest(),
            },
            "signature": {
                "artifact": f"goal006-attestation-{member}",
                "issuer": "github-oidc",
                "oci_subject": images[member],
                "sha256": hashlib.sha256(signature_files[member].read_bytes()).hexdigest(),
            },
        }
        for member in sorted(RELEASE_MEMBERS)
    }
    manifest = {
        "schema": "waooaw.registry-release/v1",
        "immutable": True,
        "source_commit": source_commit,
        "builder_workflow": BUILDER_WORKFLOW,
        "qualification": {"status": "pass", "github_run_id": run_id},
        "images": images,
        "evidence": evidence,
    }
    violations = validate_registry_manifest(manifest)
    if violations:
        raise ValueError(", ".join(violations))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("digest_directory", type=Path, nargs="?")
    parser.add_argument("evidence_directory", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--source-commit")
    parser.add_argument("--run-id")
    parser.add_argument("--verify-manifest", type=Path)
    parser.add_argument("--expected-source-commit")
    parser.add_argument("--expected-run-id")
    parser.add_argument("--evidence-directory", type=Path)
    args = parser.parse_args()
    if args.verify_manifest is not None:
        manifest = json.loads(args.verify_manifest.read_text(encoding="utf-8"))
        violations = validate_registry_manifest(
            manifest,
            args.expected_source_commit,
            args.expected_run_id,
            args.evidence_directory,
        )
        print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
        return 0 if not violations else 1
    if None in (args.digest_directory, args.evidence_directory, args.output, args.source_commit, args.run_id):
        parser.error("creation requires digest_directory, evidence_directory, output, --source-commit and --run-id")
    manifest = create_registry_manifest(
        args.digest_directory, args.evidence_directory, args.source_commit, args.run_id
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())