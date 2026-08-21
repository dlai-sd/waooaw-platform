"""Contracts for protected inactive Demo runner preview and apply."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/runner-environment-delivery.yaml").read_text(
    encoding="utf-8"
)


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