"""Contracts for protected inactive Demo runner preview and apply."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/runner-environment-delivery.yaml").read_text(
    encoding="utf-8"
)
QUALIFICATION_WORKFLOW = Path(
    ".github/workflows/goal006-private-runner-qualification.yaml"
).read_text(encoding="utf-8")


def test_workflow_exposes_only_authorized_demo_environment() -> None:
    assert "          - demo" in WORKFLOW
    assert "          - uat" not in WORKFLOW
    assert "          - prod" not in WORKFLOW
    assert "environment: ${{ inputs.environment }}" in WORKFLOW
    assert "goal006-runner-${{ inputs.environment }}" in WORKFLOW


def test_apply_requires_a_reviewed_preview_run() -> None:
    assert "reviewed_plan_run_id" in WORKFLOW
    assert "Download reviewed plan" in WORKFLOW
    assert "Validate referenced workflow run" in WORKFLOW
    assert "current Azure plan differs from reviewed plan" not in WORKFLOW
    assert "--reviewed-plan" in WORKFLOW


def test_workflow_cannot_mint_or_consume_transition_evidence() -> None:
    assert "evidence_run_id" not in WORKFLOW
    assert "promotion" not in WORKFLOW.lower()
    assert "rollback" not in WORKFLOW.lower()
    assert "operation == 'verify'" not in WORKFLOW
    assert "goal006_runner_deployment.py verify" not in WORKFLOW


def test_legacy_one_step_demo_workflow_is_removed() -> None:
    assert not Path(".github/workflows/bootstrap-demo-runner.yaml").exists()


def test_plan_and_deployment_evidence_are_retained() -> None:
    assert "goal006-runner-plan-${{ inputs.environment }}-${{ github.run_id }}" in WORKFLOW
    assert "goal006-runner-deployment-${{ inputs.environment }}-${{ github.run_id }}" in WORKFLOW
    assert "runner-plan.json" in WORKFLOW
    assert "deployment-record.json" in WORKFLOW


def test_private_qualification_uses_brokers_and_demo_runner_only() -> None:
    assert "RUNNER_BROKER_JOB: goal006-demo-runner-broker" in QUALIFICATION_WORKFLOW
    assert (
        "RUNNER_CLEANUP_BROKER_JOB: goal006-demo-runner-cleanup"
        in QUALIFICATION_WORKFLOW
    )
    assert "runs-on: [self-hosted, goal006-demo-private]" in QUALIFICATION_WORKFLOW
    assert "group: goal006-demo-private" not in QUALIFICATION_WORKFLOW
    assert "goal006-uat" not in QUALIFICATION_WORKFLOW
    assert "goal006-prod" not in QUALIFICATION_WORKFLOW
    assert "if: always()" in QUALIFICATION_WORKFLOW
    assert "needs.start-broker.result == 'success'" not in QUALIFICATION_WORKFLOW
    assert QUALIFICATION_WORKFLOW.count(
        "runner_image=$(jq -er '.parameters.runnerImage.value'"
    ) == 2
    assert QUALIFICATION_WORKFLOW.count("goal006_runner_execution.py") == 2
    assert QUALIFICATION_WORKFLOW.count("--yaml") == 2
    assert "--container-name broker" not in QUALIFICATION_WORKFLOW
    assert "--container-name cleanup-broker" not in QUALIFICATION_WORKFLOW


def test_hosted_qualification_never_signs_or_handles_runner_tokens() -> None:
    assert QUALIFICATION_WORKFLOW.count("runs-on: ubuntu-latest") == 2
    assert "containerapp job start" in QUALIFICATION_WORKFLOW
    assert "/sign?" not in QUALIFICATION_WORKFLOW
    assert "GITHUB_APP_ID" not in QUALIFICATION_WORKFLOW
    assert "GITHUB_APP_INSTALLATION_ID" not in QUALIFICATION_WORKFLOW
    assert "RUNNER_REGISTRATION_TOKEN" not in QUALIFICATION_WORKFLOW
    assert "network-rule add" not in QUALIFICATION_WORKFLOW


def test_cleanup_is_ungated_and_uses_dedicated_identity() -> None:
    cleanup = QUALIFICATION_WORKFLOW.split("  cleanup-private:", 1)[1]

    assert "environment: demo" not in cleanup
    assert "client-id: ${{ env.RUNNER_CLEANUP_CLIENT_ID }}" in cleanup
    assert "client-id: ${{ env.ARM_CLIENT_ID }}" not in cleanup
    assert "RUNNER_CLEANUP_CLIENT_ID: 0cbfdc62-b91f-44ee-ac27-90785b3d2eb5" in QUALIFICATION_WORKFLOW


def test_private_qualification_invokes_available_python_runtime() -> None:
    assert "python3 scripts/goal006_runner_qualification.py" in QUALIFICATION_WORKFLOW
    assert "python scripts/goal006_runner_qualification.py" not in QUALIFICATION_WORKFLOW