"""WC-109 four-identity manifests and Tier 1 static preflight."""

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from validation_control.execution_contract import static_preflight
from validation_control.identity import (
    candidate_manifest,
    evidence_manifest,
    runner_manifest,
    test_execution_manifest as build_test_execution_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
DIGESTS = ["sha256:" + character * 64 for character in "12345678"]


def runner_inputs() -> dict[str, object]:
    return {
        "dockerfile_digest": DIGESTS[0],
        "base_image_digest": DIGESTS[1],
        "system_packages": ["curl=1.0"],
        "dependency_manifests": {"requirements-test.txt": DIGESTS[2]},
        "build_arguments": {"PYTHON_VERSION": "3.12"},
        "platform": "linux/amd64",
        "context_manifest": [{"path": "scripts\\gate.py", "digest": DIGESTS[3], "mode": 493}],
        "runner_schema_version": "v1",
    }


def execution_inputs() -> dict[str, object]:
    return {
        "mounted_source_identity": DIGESTS[0],
        "runner_digest": DIGESTS[1],
        "command_id": "test-python",
        "policy_version": "v1",
        "environment": {"MODE": "test"},
        "service_identities": {"postgres": DIGESTS[2]},
        "disposable_state_contract": {"database": "reset", "outputs": "isolated"},
        "architecture": "amd64",
        "platform": "linux",
        "test_execution_schema_version": "v1",
    }


def candidate_inputs() -> dict[str, object]:
    return {
        "build_context_manifest": [{"path": "src/app.py", "digest": DIGESTS[0], "mode": 420}],
        "generated_artifacts": {"openapi.json": DIGESTS[1]},
        "dockerfile_frontend_digest": DIGESTS[2],
        "build_arguments": {"VERSION": "1"},
        "base_image_digests": {"runtime": DIGESTS[3]},
        "architecture": "amd64",
        "platform": "linux",
        "candidate_schema_version": "v1",
    }


def evidence_inputs() -> dict[str, object]:
    return {
        "subject_identity": DIGESTS[0],
        "test_execution_identity": DIGESTS[1],
        "runner_digest": DIGESTS[2],
        "command_id": "test-python",
        "policy_version": "v1",
        "environment": {"MODE": "test"},
        "evidence_schema_version": "v1",
        "trust_source": "local-diagnostic",
        "freshness": {"policy": "2026-09-29"},
    }


MANIFEST_CASES = (
    ("runner", runner_manifest, runner_inputs),
    ("test-execution", build_test_execution_manifest, execution_inputs),
    ("candidate", candidate_manifest, candidate_inputs),
    ("evidence", evidence_manifest, evidence_inputs),
)


@pytest.mark.parametrize(("identity_type", "factory", "inputs_factory"), MANIFEST_CASES)
def test_manifest_is_schema_valid_deterministic_and_sensitive_fields_fail(
    identity_type: str,
    factory: object,
    inputs_factory: object,
) -> None:
    inputs = inputs_factory()
    manifest = factory(inputs)
    schema_path = ROOT / f"validation/{identity_type}-identity.schema.json"
    jsonschema.validate(manifest, json.loads(schema_path.read_text(encoding="utf-8")))
    assert factory(deepcopy(inputs)) == manifest
    with pytest.raises(ValueError, match="sensitive field"):
        factory({**inputs, "environment": {"api_token": "fixture-secret"}})


@pytest.mark.parametrize(("identity_type", "factory", "inputs_factory"), MANIFEST_CASES)
def test_every_declared_input_independently_changes_manifest_digest(
    identity_type: str,
    factory: object,
    inputs_factory: object,
) -> None:
    inputs = inputs_factory()
    original = factory(inputs)["digest"]
    for field, value in inputs.items():
        mutated = deepcopy(inputs)
        if isinstance(value, dict):
            mutated[field] = {**value, "mutation": "changed"}
        elif isinstance(value, list):
            mutated[field] = [*value, "changed"]
        else:
            mutated[field] = f"changed-{value}"
        if field in {
            "dockerfile_digest",
            "base_image_digest",
            "mounted_source_identity",
            "runner_digest",
            "dockerfile_frontend_digest",
            "subject_identity",
            "test_execution_identity",
        }:
            mutated[field] = DIGESTS[7]
        assert factory(mutated)["digest"] != original, f"{identity_type}.{field}"


def valid_manifests() -> list[dict[str, object]]:
    return [factory(inputs_factory()) for _, factory, inputs_factory in MANIFEST_CASES]


def valid_execution() -> dict[str, object]:
    return {
        "catalog_valid": True,
        "syntax_valid": True,
        "uid": 1000,
        "gid": 1000,
        "mounts": [{"source": "/workspace", "read_only": True}],
        "permissions_valid": True,
        "output_writable": True,
        "docker_socket_requested": False,
        "docker_socket_allowed": False,
        "workflow_placement": "container",
    }


@pytest.mark.parametrize(
    ("mutation", "first_cause"),
    (
        ({"catalog_valid": False}, "catalog"),
        ({"syntax_valid": False}, "syntax"),
        ({"uid": 0}, "uid"),
        ({"mounts": []}, "mount"),
        ({"permissions_valid": False}, "permission"),
        ({"output_writable": False}, "output"),
        ({"docker_socket_requested": True}, "socket"),
        ({"workflow_placement": "host"}, "workflow-placement"),
    ),
)
def test_tier1_modeled_defects_stop_without_build_or_execution(mutation: dict[str, object], first_cause: str) -> None:
    result = static_preflight(valid_manifests(), {**valid_execution(), **mutation})

    assert result["result"] == "FAIL"
    assert result["first_cause"] == first_cause
    assert result["build_events"] == 0
    assert result["execution_events"] == 0


def test_tier1_accepts_complete_manifests_without_costly_events() -> None:
    result = static_preflight(valid_manifests(), valid_execution())

    assert result == {
        "schema": "waooaw.static-preflight-result/v1",
        "result": "PASS",
        "first_cause": None,
        "violations": [],
        "build_events": 0,
        "execution_events": 0,
    }
