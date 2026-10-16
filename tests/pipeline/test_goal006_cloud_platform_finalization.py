"""Contracts for the GOAL-006 cloud platform finalization workflow graph."""

import json
import re
from pathlib import Path


WORKFLOWS = Path(".github/workflows")


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_neutral_deploy_entry_is_the_only_manual_application_entry() -> None:
    deploy = _workflow("deploy.yaml")

    assert "  workflow_dispatch:" in deploy
    assert "      environment:" in deploy
    assert all(f"          - {environment}" in deploy for environment in ("demo", "uat", "prod"))
    assert "      execution:" in deploy
    assert "          - plan" in deploy
    assert "          - apply" in deploy
    assert "          - activate" not in deploy
    assert "          - sleep" not in deploy
    for internal_input in (
        "lifecycle_evidence:",
        "founder_action_authority:",
        "plan_digest:",
        "secret_catalog_digest:",
        "lease_id:",
        "release_tuple:",
    ):
        assert internal_input not in deploy
    assert not (WORKFLOWS / "deploy-demo.yaml").exists()

    engine = _workflow("environment-deployment.yaml")
    assert "  workflow_call:" in engine
    assert "  workflow_dispatch:" not in engine


def test_neutral_entry_delegates_deployment_and_verification() -> None:
    deploy = _workflow("deploy.yaml")

    assert "uses: ./.github/workflows/environment-deployment.yaml" in deploy
    assert "uses: ./.github/workflows/environment-deployment-verification.yaml" in deploy
    assert "terraform " not in deploy
    assert "az " not in deploy


def test_demo_lifecycle_no_longer_depends_on_founder_source_ip() -> None:
    deploy = _workflow("deploy.yaml")

    assert "scripts/goal006_dispatch_inputs.py" in deploy
    assert "access_ipv4" not in deploy
    assert "access_cidr" not in deploy


def test_runner_delivery_supports_each_protected_environment() -> None:
    runner = _workflow("private-runner-infrastructure.yaml")

    assert all(f"          - {environment}" in runner for environment in ("demo", "uat", "prod"))
    assert "case \"$TARGET_ENVIRONMENT\" in demo|uat|prod)" in runner
    assert "environment: ${{ inputs.environment }}" in runner
    assert "goal006-runner-${{ inputs.environment }}" in runner


def test_private_runner_qualification_is_parameterized_diagnostics_only() -> None:
    runner = _workflow("private-runner-infrastructure.yaml")
    qualification = runner.split("  resolve-environment:", 1)[1]

    assert not (WORKFLOWS / "goal006-private-runner-qualification.yaml").exists()
    assert "          - qualify" in runner
    assert "      environment:" in runner
    assert all(f"          - {environment}" in runner for environment in ("demo", "uat", "prod"))
    assert "goal006_environment_config.py" in qualification
    assert "environment: ${{ inputs.environment }}" in qualification
    assert "environment-deployment.yaml" not in qualification
    assert "terraform apply" not in qualification


def test_lease_reconciliation_is_environment_parameterized_and_deletion_only() -> None:
    reconciliation = _workflow("workload-lease-reconciliation.yaml")

    assert "      environment:" in reconciliation
    assert all(f"          - {environment}" in reconciliation for environment in ("demo", "uat", "prod"))
    assert "goal006_environment_config.py" in reconciliation
    assert "environment: ${{ inputs.environment }}" in reconciliation
    assert "--environment '${{ inputs.environment }}'" in reconciliation
    assert "runs-on: [self-hosted, \"${{ needs.resolve-environment.outputs.runner_label }}\"]" in reconciliation
    assert "network-rule add" not in reconciliation
    assert "network-rule remove" not in reconciliation
    assert "terraform apply" not in reconciliation


def test_deny_only_promotion_workflow_is_removed() -> None:
    assert not (WORKFLOWS / "promote.yaml").exists()


def test_promoted_runner_blueprints_use_approved_immutable_repository_inputs() -> None:
    stack_root = Path("infrastructure/deployment-stacks/goal006-runner")
    demo = json.loads((stack_root / "demo.parameters.json").read_text(encoding="utf-8"))["parameters"]

    shared_names = (
        "runnerImage",
        "reconcilerImage",
        "githubAppId",
        "githubAppInstallationId",
        "githubAppKeyName",
        "cleanupFederatedSubject",
    )
    expected_activation = {"uat": "ACTIVE", "prod": "INACTIVE"}
    for environment, activation_state in expected_activation.items():
        parameters = json.loads(
            (stack_root / f"{environment}.parameters.json").read_text(encoding="utf-8")
        )["parameters"]
        assert parameters["activationState"]["value"] == activation_state
        for name in shared_names:
            assert parameters[name]["value"] == demo[name]["value"]
            assert parameters[name]["value"] != "PENDING"
        assert re.fullmatch(r"[0-9a-f]{32}", parameters["githubAppKeyVersion"]["value"])