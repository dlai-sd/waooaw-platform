"""Offline contracts for the inactive GOAL-006 Demo runner bootstrap stack."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

from scripts.goal006_runner_bootstrap import validate_bootstrap_manifest

REPOSITORY_ROOT = Path(__file__).parents[2]
STACK_ROOT = REPOSITORY_ROOT / "infrastructure/deployment-stacks/goal006-runner"
MANIFEST_PATH = STACK_ROOT / "bootstrap-manifest.json"


def _write_manifest(
    tmp_path: Path, *, environment: str = "demo", parameter_mutator=None
) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    relative_paths = [
        "infrastructure/deployment-stacks/goal006-runner/main.bicep",
        "infrastructure/deployment-stacks/goal006-runner/subscription.bicep",
        "infrastructure/deployment-stacks/goal006-runner/prerequisites.bicep",
        "infrastructure/deployment-stacks/goal006-runner/prerequisites-rg.bicep",
        "infrastructure/deployment-stacks/goal006-runner/cost-estimate.json",
        "architecture/reference/pipeline/github-runner-app-manifest.json",
    ]
    for item_environment in ("demo", "uat", "prod"):
        relative_paths.extend(
            [
                "infrastructure/deployment-stacks/goal006-runner/"
                f"{item_environment}.parameters.json",
                "infrastructure/deployment-stacks/goal006-runner/"
                f"{item_environment}.prerequisites.parameters.json",
            ]
        )
    for relative_path in relative_paths:
        source = REPOSITORY_ROOT / relative_path
        destination = repository / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    parameter_path = (
        repository
        / "infrastructure/deployment-stacks/goal006-runner"
        / f"{environment}.parameters.json"
    )
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
        "schema_version": 3,
        "blueprint_version": "2.0.0",
        "environments": {
            item_environment: {
            "activation_state": "ACTIVE" if item_environment == "demo" else "INACTIVE",
                "parameters": "infrastructure/deployment-stacks/goal006-runner/"
                f"{item_environment}.parameters.json",
                "prerequisites": "infrastructure/deployment-stacks/goal006-runner/"
                f"{item_environment}.prerequisites.parameters.json",
            }
            for item_environment in ("demo", "uat", "prod")
        },
        "files": files,
    }
    manifest_path = repository / "bootstrap-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return repository, manifest_path


def test_reviewed_bootstrap_manifest_passes() -> None:
    for environment in ("demo", "uat", "prod"):
        assert validate_bootstrap_manifest(REPOSITORY_ROOT, MANIFEST_PATH, environment) == []


def test_digest_drift_fails_closed(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    template = repository / "infrastructure/deployment-stacks/goal006-runner/main.bicep"
    template.write_text(template.read_text(encoding="utf-8") + "\n// drift\n", encoding="utf-8")
    assert any(
        violation.startswith("DIGEST_MISMATCH:")
        for violation in validate_bootstrap_manifest(repository, manifest_path)
    )


def test_invalid_activation_state_and_mutable_image_fails_closed(tmp_path: Path) -> None:
    def mutate(parameters: dict[str, dict[str, object]]) -> None:
        parameters["activationState"]["value"] = "ARMED"
        parameters["runnerImage"]["value"] = "ghcr.io/actions/actions-runner:latest"

    repository, manifest_path = _write_manifest(tmp_path, parameter_mutator=mutate)
    violations = validate_bootstrap_manifest(repository, manifest_path)
    assert "PARAMETER_ACTIVATION_STATE_INVALID" in violations
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


def test_manifest_invalid_activation_state_fails_closed(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = deepcopy(manifest)
    changed["environments"]["demo"]["activation_state"] = "ARMED"
    manifest_path.write_text(json.dumps(changed), encoding="utf-8")
    assert "ACTIVATION_STATE_INVALID" in validate_bootstrap_manifest(
        repository, manifest_path
    )


def test_manifest_and_parameter_activation_must_match(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(
        tmp_path,
        parameter_mutator=lambda parameters: parameters["activationState"].update(
            value="INACTIVE"
        ),
    )

    assert "ACTIVATION_STATE_MISMATCH" in validate_bootstrap_manifest(
        repository, manifest_path
    )


def test_cross_environment_network_overlap_fails_closed(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    uat_path = (
        repository
        / "infrastructure/deployment-stacks/goal006-runner/uat.parameters.json"
    )
    uat = json.loads(uat_path.read_text(encoding="utf-8"))
    uat["parameters"]["runnerVnetAddressPrefix"]["value"] = "10.70.0.0/24"
    uat_path.write_text(json.dumps(uat), encoding="utf-8")

    assert "CROSS_ENVIRONMENT_NETWORK_OVERLAP" in validate_bootstrap_manifest(
        repository, manifest_path
    )


def test_unreviewed_cost_estimate_fails_closed(tmp_path: Path) -> None:
    repository, manifest_path = _write_manifest(tmp_path)
    estimate_path = repository / "infrastructure/deployment-stacks/goal006-runner/cost-estimate.json"
    estimate = json.loads(estimate_path.read_text(encoding="utf-8"))
    estimate["planned_incremental_monthly_cost_inr"] = 999
    estimate_path.write_text(json.dumps(estimate), encoding="utf-8")
    assert "COST_ESTIMATE_INVALID" in validate_bootstrap_manifest(repository, manifest_path)


def test_stack_is_environment_generic_and_uses_valid_private_dns() -> None:
    main = (STACK_ROOT / "main.bicep").read_text(encoding="utf-8")
    subscription = (STACK_ROOT / "subscription.bicep").read_text(encoding="utf-8")
    vault_dns = re.search(
        r"resource vaultPrivateDns[^=]*=\s*\{\s*name:\s*'([^']+)'",
        main,
    )

    for environment in ("demo", "uat", "prod"):
        assert f"  '{environment}'" in main
        assert f"  '{environment}'" in subscription
    assert vault_dns is not None
    assert vault_dns.group(1) == "privatelink.vaultcore.azure.net"
    assert "privatelink${az.environment().suffixes.keyvaultDns}" not in main
    assert "goal006-${environment}-private" in main
    assert "resource brokerIdentity" in main
    assert "resource brokerJob" in main
    assert "resource cleanupBrokerJob" in main
    assert "resource keyImportIdentity" in main
    assert "resource keyImportAccess" in main
    assert "resource keyImportApp" in main
    assert "Microsoft.App/containerApps@2024-03-01" in main
    assert "value: 'github-runner-app-signing'" in main
    assert "minReplicas: 0" in main
    assert "maxReplicas: 1" in main
    assert main.count("replicaTimeout: 300") == 2
    assert "bootstrapKeySignAccess" not in main
    assert "bootstrapSecretAccess" not in main

    resource_names = [
        f"goal006-{environment}-runner-cleanup"
        for environment in ("demo", "uat", "prod")
    ]
    assert all(len(name) <= 32 for name in resource_names)


def test_active_stack_requires_existing_app_identifiers(tmp_path: Path) -> None:
    def mutate(parameters: dict[str, dict[str, object]]) -> None:
        parameters["activationState"]["value"] = "ACTIVE"
        parameters["githubAppId"]["value"] = "PENDING"
        parameters["githubAppInstallationId"]["value"] = "PENDING"
        parameters["githubAppKeyName"]["value"] = "app-key"
        parameters["githubAppKeyVersion"]["value"] = "a" * 32

    repository, manifest_path = _write_manifest(tmp_path, parameter_mutator=mutate)
    violations = validate_bootstrap_manifest(repository, manifest_path)
    assert "GITHUB_APP_KEY_NOT_CONFIGURED" in violations
    assert "RUNNER_IMAGE_NOT_PUBLISHED" not in violations