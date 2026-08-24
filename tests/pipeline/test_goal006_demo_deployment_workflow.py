"""Contracts for private GOAL-006 Demo deployment execution."""

from pathlib import Path


WORKFLOW = Path(".github/workflows/deploy-environment.yaml").read_text(
    encoding="utf-8"
)


def test_demo_deployment_uses_qualified_private_runner_lifecycle() -> None:
    assert "  start-broker:" in WORKFLOW
    assert "needs: start-broker" in WORKFLOW
    assert "runs-on: [self-hosted, goal006-demo-private]" in WORKFLOW
    assert "  cleanup-private:" in WORKFLOW
    assert "needs: [start-broker, terraform]" in WORKFLOW
    assert "if: always()" in WORKFLOW
    assert WORKFLOW.count("goal006_runner_execution.py broker") == 1
    assert WORKFLOW.count("goal006_runner_execution.py cleanup") == 1
    assert WORKFLOW.count("goal006_runner_execution.py pointer") == 1


def test_demo_deployment_never_opens_public_storage_access() -> None:
    assert "Open temporary state firewall rule" not in WORKFLOW
    assert "Close state firewall rule" not in WORKFLOW
    assert "network-rule add" not in WORKFLOW
    assert "network-rule remove" not in WORKFLOW
    assert "RUNNER_IP" not in WORKFLOW
    assert "api.ipify.org" not in WORKFLOW


def test_private_runner_steps_do_not_require_a_docker_daemon() -> None:
    assert "docker/setup-buildx-action" not in WORKFLOW
    assert "docker buildx" not in WORKFLOW
    assert "https://ghcr.io/v2/$repository/manifests/$expected_digest" in WORKFLOW
    assert "https://mcr.microsoft.com/v2/$repository/manifests/$expected_digest" in WORKFLOW
    assert WORKFLOW.count('test "$actual_digest" = "$expected_digest"') == 2


def test_private_job_uses_only_live_runner_commands() -> None:
    private_job = WORKFLOW.split("  terraform:", 1)[1].split("  cleanup-private:", 1)[0]

    assert "python3 " in private_job
    assert "python " not in private_job
    assert "gh api" not in private_job
    assert "gh attestation" not in private_job
    assert "https://api.github.com/repos/$GITHUB_REPOSITORY/git/ref/heads/main" in private_job


def test_private_job_uses_pinned_native_terraform_without_node_wrapper() -> None:
    private_job = WORKFLOW.split("  terraform:", 1)[1].split("  cleanup-private:", 1)[0]

    assert "hashicorp/setup-terraform" not in private_job
    assert 'test "$(command -v terraform)" = "/usr/local/bin/terraform"' in private_job
    assert 'test "$(terraform version -json | jq -r \'.terraform_version\')" = "1.9.8"' in private_job


def test_cost_evidence_is_queried_once_and_reused_by_private_job() -> None:
    assert WORKFLOW.count("CostManagement/query?api-version=2023-11-01") == 1
    assert WORKFLOW.count("CostManagement/forecast?api-version=2023-11-01") == 1
    assert "Download pre-start cost evidence" in WORKFLOW
    assert "goal006-private-runner-prestart-${{ github.run_id }}-${{ github.run_attempt }}" in WORKFLOW
    assert "Enforce workload cost boundary" in WORKFLOW


def test_demo_deployment_cleanup_is_independent_and_retains_evidence() -> None:
    cleanup = WORKFLOW.split("  cleanup-private:", 1)[1]

    assert "client-id: ${{ env.RUNNER_CLEANUP_CLIENT_ID }}" in cleanup
    assert "client-id: ${{ env.ARM_CLIENT_ID }}" not in cleanup
    assert '--private-job-conclusion "$PRIVATE_JOB_CONCLUSION"' in cleanup
    assert '--cleanup-execution-name "$execution"' in cleanup
    assert 'cleanup/demo/$GITHUB_RUN_ID/$GITHUB_RUN_ATTEMPT.json' in cleanup
    assert "goal006-private-runner-cleanup-${{ github.run_id }}-${{ github.run_attempt }}" in cleanup


def test_demo_deployment_binds_broker_and_cleanup_to_release_sha() -> None:
    assert WORKFLOW.count("ref: ${{ inputs.release_sha }}") >= 2
    assert "test '${{ inputs.release_sha }}' = \"$latest_main_sha\"" in WORKFLOW