"""WC-102 and WC-104 identity separation and resolution contracts."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.1
# Constitutional basis: C-023, C-059, C-071, C-080

import pytest

from validation_control.identity import (
    candidate_identity,
    evidence_identity,
    resolve_runner_manifest,
    runner_identity,
)


def runner_inputs() -> dict[str, object]:
    return {
        "dockerfile_digest": "sha256:" + "a" * 64,
        "base_image_digest": "sha256:" + "b" * 64,
        "system_packages": ["curl=1.0", "git=2.0"],
        "dependency_manifests": {"requirements-test.txt": "sha256:" + "c" * 64},
        "build_arguments": {"PYTHON_VERSION": "3.12"},
        "platform": "linux/amd64",
        "context_manifest": {"requirements-test.txt": "sha256:" + "c" * 64},
        "runner_schema_version": "wc104-v1",
    }


def test_runner_identity_excludes_source_tests_and_fixtures() -> None:
    inputs = runner_inputs()
    original = runner_identity(inputs)

    assert runner_identity({**inputs, "system_packages": ["curl=2.0", "git=2.0"]}) != original
    with pytest.raises(ValueError, match="application inputs"):
        runner_identity({**inputs, "source": "changed"})


@pytest.mark.parametrize("field", sorted(runner_inputs()))
def test_runner_identity_requires_every_declared_environment_input(field: str) -> None:
    inputs = runner_inputs()
    del inputs[field]

    with pytest.raises(ValueError, match="missing inputs"):
        runner_identity(inputs)


def test_runner_identity_rejects_mutable_base_and_undeclared_inputs() -> None:
    with pytest.raises(ValueError, match="immutable sha256"):
        runner_identity({**runner_inputs(), "base_image_digest": "python:3.12"})
    with pytest.raises(ValueError, match="undeclared inputs"):
        runner_identity({**runner_inputs(), "timestamp": "now"})


def test_registry_resolution_requires_exact_identity_platform_digest_and_provenance() -> None:
    identity = runner_identity(runner_inputs())
    record = {
        "runner_identity": identity,
        "oci_digest": "sha256:" + "d" * 64,
        "platform": "linux/amd64",
        "provenance": {"verified": True},
    }

    def verifier(provenance: dict[str, object]) -> bool:
        return provenance.get("verified") is True

    assert resolve_runner_manifest(identity, "linux/amd64", record, verifier) == {
        "runner_identity": identity,
        "oci_digest": "sha256:" + "d" * 64,
        "platform": "linux/amd64",
    }
    for mutation in (
        {"runner_identity": "sha256:" + "e" * 64},
        {"oci_digest": "runner:latest"},
        {"platform": "linux/arm64"},
        {"provenance": {"verified": False}},
    ):
        assert resolve_runner_manifest(identity, "linux/amd64", {**record, **mutation}, verifier) is None


def test_evidence_identity_invalidates_every_authority_input() -> None:
    inputs = {
        "base_sha": "b" * 40,
        "head_sha": "c" * 40,
        "catalog_version": "wc102-shadow-v1",
        "command_id": "test-web",
        "runner_digest": "sha256:" + "d" * 64,
        "source": "source-digest",
        "tests": "test-digest",
        "fixtures": "fixture-digest",
        "specifications": "spec-digest",
        "environment": {},
    }
    original = evidence_identity(inputs)

    for field in inputs:
        assert evidence_identity({**inputs, field: f"changed-{field}"}) != original


def test_candidate_identity_is_distinct_from_runner_and_evidence() -> None:
    candidate = candidate_identity({"production_dockerfile": "abc", "source": "def"})
    runner = runner_identity(runner_inputs())
    evidence = evidence_identity(
        {
            "base_sha": "b" * 40,
            "head_sha": "c" * 40,
            "catalog_version": "v1",
            "command_id": "test-web",
            "runner_digest": runner,
        }
    )

    assert len({candidate, runner, evidence}) == 3
