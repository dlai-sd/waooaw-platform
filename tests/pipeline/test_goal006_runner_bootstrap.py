"""Offline contracts for the inactive GOAL-006 Demo runner bootstrap stack."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from scripts.goal006_runner_bootstrap import validate_bootstrap_manifest

REPOSITORY_ROOT = Path(__file__).parents[2]
STACK_ROOT = REPOSITORY_ROOT / "infrastructure/deployment-stacks/goal006-runner"
MANIFEST_PATH = STACK_ROOT / "bootstrap-manifest.json"


def _write_manifest(tmp_path: Path, *, parameter_mutator=None) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    for relative_path in (
        "infrastructure/deployment-stacks/goal006-runner/main.bicep",
        "infrastructure/deployment-stacks/goal006-runner/subscription.bicep",
        "infrastructure/deployment-stacks/goal006-runner/prerequisites.bicep",
        "infrastructure/deployment-stacks/goal006-runner/prerequisites-rg.bicep",
        "infrastructure/deployment-stacks/goal006-runner/demo.parameters.json",
        "infrastructure/deployment-stacks/goal006-runner/demo.prerequisites.parameters.json",
        "infrastructure/deployment-stacks/goal006-runner/cost-estimate.json",
        "architecture/reference/pipeline/github-runner-app-manifest.json",
    ):
        source = REPOSITORY_ROOT / relative_path
        destination = repository / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    parameter_path = repository / "infrastructure/deployment-stacks/goal006-runner/demo.parameters.json"
    if parameter_mutator:
        parameters = json.loads(parameter_path.read_text(encoding="utf-8"))
        parameter_mutator(parameters["parameters"])
        parameter_path.write_text(json.dumps(parameters), encoding="utf-8")
    files = {
        str(path.relative_to(repository)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in repository.rglob("*")
        if path.is_file()
    }
    manifest = {
        "schema_version": 1,
        "blueprint_version": "1.0.0",
        "environment": "demo",
        "activation_state": "INACTIVE",
        "files": files,
    }
    manifest_path = repository / "bootstrap-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return repository, manifest_path


def test_reviewed_bootstrap_manifest_passes() -> None:
    assert validate_bootstrap_manifest(REPOSITORY_ROOT, MANIFEST_PATH) == []


def test_digest_drift_fails_closed(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    template = repository / "infrastructure/deployment-stacks/goal006-runner/main.bicep"
    template.write_text(template.read_text(encoding="utf-8") + "\n// drift\n", encoding="utf-8")
    assert any(
        violation.startswith("DIGEST_MISMATCH:")
        for violation in validate_bootstrap_manifest(repository, manifest_path)
    )


def test_activation_or_mutable_image_fails_closed(tmp_path: Path) -> None:
    def mutate(parameters: dict[str, dict[str, object]]) -> None:
        parameters["activationState"]["value"] = "ACTIVE"
        parameters["runnerImage"]["value"] = "ghcr.io/actions/actions-runner:latest"

    repository, manifest_path = _write_manifest(tmp_path, parameter_mutator=mutate)
    violations = validate_bootstrap_manifest(repository, manifest_path)
    assert "PARAMETER_ACTIVATION_NOT_INACTIVE" in violations
    assert "IMAGE_NOT_IMMUTABLE:runnerImage" in violations


def test_wrong_state_principal_or_overlapping_subnets_fail_closed(tmp_path: Path) -> None:
    def mutate(parameters: dict[str, dict[str, object]]) -> None:
        parameters["stateStorageAccountId"]["value"] = "/wrong"
        parameters["bootstrapPrincipalId"]["value"] = "wrong"
        parameters["privateEndpointSubnetAddressPrefix"]["value"] = "10.70.0.0/28"

    repository, manifest_path = _write_manifest(tmp_path, parameter_mutator=mutate)
    violations = validate_bootstrap_manifest(repository, manifest_path)
    assert "STATE_STORAGE_ID_INVALID" in violations
    assert "BOOTSTRAP_PRINCIPAL_INVALID" in violations
    assert "NETWORK_BOUNDARY_INVALID" in violations


def test_manifest_metadata_cannot_activate_stack(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = deepcopy(manifest)
    changed["activation_state"] = "ACTIVE"
    manifest_path.write_text(json.dumps(changed), encoding="utf-8")
    assert "ACTIVATION_NOT_INACTIVE" in validate_bootstrap_manifest(repository, manifest_path)


def test_unreviewed_cost_estimate_fails_closed(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    estimate_path = repository / "infrastructure/deployment-stacks/goal006-runner/cost-estimate.json"
    estimate = json.loads(estimate_path.read_text(encoding="utf-8"))
    estimate["planned_incremental_monthly_cost_inr"] = 999
    estimate_path.write_text(json.dumps(estimate), encoding="utf-8")
    assert "COST_ESTIMATE_INVALID" in validate_bootstrap_manifest(repository, manifest_path)