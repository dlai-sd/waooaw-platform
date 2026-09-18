from copy import deepcopy
from pathlib import Path

import pytest

from build_evidence import build_input_identity, validate_build_evidence


INPUT_GROUPS = (
    "source",
    "tests",
    "fixtures",
    "dockerfile",
    "dependencies",
    "compose",
    "generated_contracts",
    "specifications",
)


def make_inputs(tmp_path: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for group in INPUT_GROUPS:
        path = tmp_path / f"{group}.txt"
        path.write_text(group, encoding="utf-8")
        groups[group] = [path]
    return groups


def valid_evidence(identity: str) -> dict[str, object]:
    return {
        "schema": "waooaw.build-evidence/v1",
        "status": "PASS",
        "trust_source": "github-actions",
        "repository": "dlai-sd/waooaw-platform",
        "base_sha": "b" * 40,
        "head_sha": "h" * 40,
        "input_identity": identity,
        "input_groups": list(INPUT_GROUPS),
        "image_id": "sha256:" + "a" * 64,
        "registry_digest": "sha256:" + "c" * 64,
        "builder": "buildkit",
        "platform": "linux/amd64",
        "docker_version": "27.0.0",
        "buildkit_version": "v0.16.0",
        "started_at": "2026-09-18T00:00:00+00:00",
        "completed_at": "2026-09-18T00:01:00+00:00",
        "consumers": ["pytest", "trivy"],
        "artifact_refs": ["build-evidence.json"],
        "cache_result": "miss",
        "invalidation_reason": "source_changed",
    }


def test_build_identity_reuse_and_invalidation(tmp_path: Path) -> None:
    inputs = make_inputs(tmp_path)
    metadata = {"build_arguments": {"MODE": "test"}, "platform": "linux/amd64", "gate_version": "v1"}
    identity = build_input_identity(inputs, metadata)

    assert build_input_identity(inputs, metadata) == identity
    for group in INPUT_GROUPS:
        inputs[group][0].write_text("changed", encoding="utf-8")
        assert build_input_identity(inputs, metadata) != identity
        inputs[group][0].write_text(group, encoding="utf-8")
    for key, value in (("build_arguments", {"MODE": "changed"}), ("platform", "linux/arm64"), ("gate_version", "v2")):
        changed_metadata = {**metadata, key: value}
        assert build_input_identity(inputs, changed_metadata) != identity


def test_build_evidence_provenance_and_tamper_detection(tmp_path: Path) -> None:
    identity = build_input_identity(make_inputs(tmp_path), {"gate_version": "v1"})
    evidence = valid_evidence(identity)

    assert validate_build_evidence(evidence, identity) == []
    for field in (
        "repository",
        "base_sha",
        "head_sha",
        "input_groups",
        "image_id",
        "builder",
        "platform",
        "started_at",
        "completed_at",
        "consumers",
        "artifact_refs",
        "cache_result",
        "invalidation_reason",
    ):
        damaged = deepcopy(evidence)
        damaged[field] = ""
        assert validate_build_evidence(damaged, identity), field


@pytest.mark.parametrize("status", ["FAIL", "CANCELLED", "STALE"])
def test_reuse_manifest_negative_matrix(tmp_path: Path, status: str) -> None:
    identity = build_input_identity(make_inputs(tmp_path), {"gate_version": "v1"})
    evidence = valid_evidence(identity)
    evidence["status"] = status

    assert any("STATUS_INVALID" in violation for violation in validate_build_evidence(evidence, identity))


def test_mutable_tag_and_identity_mismatch_fail(tmp_path: Path) -> None:
    identity = build_input_identity(make_inputs(tmp_path), {"gate_version": "v1"})
    evidence = valid_evidence(identity)
    evidence["image_id"] = "waooaw/test-runner:latest"
    evidence["registry_digest"] = ""

    violations = validate_build_evidence(evidence, "f" * 64)

    assert any("INPUT_IDENTITY_MISMATCH" in violation for violation in violations)
    assert any("IMAGE_ID_MUTABLE" in violation for violation in violations)


def test_base_image_freshness_invalidation_is_recorded(tmp_path: Path) -> None:
    identity = build_input_identity(make_inputs(tmp_path), {"base_image_freshness": "2026-09-18"})
    evidence = valid_evidence(identity)
    evidence["cache_result"] = "forced-rebuild"
    evidence["invalidation_reason"] = "base_image_freshness"

    assert validate_build_evidence(evidence, identity) == []


def test_local_exact_image_evidence_cannot_replace_trusted_ci(tmp_path: Path) -> None:
    identity = build_input_identity(make_inputs(tmp_path), {"gate_version": "v1"})
    evidence = valid_evidence(identity)
    evidence["trust_source"] = "local-exact-image"

    assert any("TRUST_SOURCE_INVALID" in violation for violation in validate_build_evidence(evidence, identity))
    assert validate_build_evidence(evidence, identity, frozenset({"local-exact-image"})) == []
