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


def test_private_seeder_passes_distinct_shell_arguments_in_structured_definition() -> None:
    private_job = WORKFLOW.split("  terraform:", 1)[1].split("  cleanup-private:", 1)[0]

    assert "seeder_script='set -eu;" in private_job
    assert 'command: ["/bin/sh"]' in private_job
    assert 'args: ["-c", $script]' in private_job
    assert "--yaml secret-seeder-job-definition.json" in private_job
    assert "seeder_args=$(jq" not in private_job
    assert "--args=" not in private_job


def test_private_credential_seeding_preserves_existing_values() -> None:
    seeder = WORKFLOW.split("seeder_script=", 1)[1].split("\n", 1)[0]

    assert "az keyvault secret show" in seeder
    assert 'if az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$name"' in seeder
    assert 'echo "credential_status name=$name status=preserved"' in seeder
    assert 'echo "credential_status name=$name status=created"' in seeder
    assert seeder.index("az keyvault secret show") < seeder.index("/dev/urandom")


def test_workload_plan_safely_adopts_the_live_identity_edge() -> None:
    workload_plan = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Terraform workload apply", 1
    )[0]

    assert "module.workload.azurerm_container_app.identity_edge[0]" in workload_plan
    assert 'if ! terraform state show "$resource_address"' in workload_plan
    assert 'edge_name="ca-${{ inputs.environment }}-identity-edge"' in workload_plan
    assert "az containerapp list" in workload_plan
    assert 'if [ "$edge_count" = "1" ]' in workload_plan
    assert 'elif [ "$edge_count" != "0" ]' in workload_plan
    assert ".properties.managedEnvironmentId == $environment_id" in workload_plan
    assert "nginxinc/nginx-unprivileged@sha256:62a904036bfc0e4a4f2b556e34cbf17bc136b47fde8cdb4628762725f48c5782" in workload_plan
    assert ".properties.configuration.ingress.external == true" in workload_plan
    assert ".properties.configuration.ingress.targetPort == 8080" in workload_plan
    assert '.properties.provisioningState == "Succeeded"' in workload_plan
    assert 'terraform import -input=false -lock-timeout=5m "$resource_address" "$edge_id"' in workload_plan
    assert workload_plan.index("terraform import") < workload_plan.index("terraform plan")
    assert "terraform show -json workload.tfplan > workload-plan.json" in workload_plan
    assert "scripts/goal006_tfplan_policy.py" in workload_plan
    assert WORKFLOW.index("goal006_tfplan_policy.py", WORKFLOW.index("Terraform workload plan")) < WORKFLOW.index(
        "      - name: Terraform workload apply"
    )
    assert "workload/workload-plan.json" in WORKFLOW


def test_identity_edge_state_reconciliation_is_environment_parameterized() -> None:
    workload_plan = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Terraform workload apply", 1
    )[0]

    for environment in ("demo", "uat", "prod"):
        rendered_plan = workload_plan.replace("${{ inputs.environment }}", environment)
        assert f'edge_name="ca-{environment}-identity-edge"' in rendered_plan

    assert 'edge_name="ca-demo-identity-edge"' not in workload_plan


def test_private_seeder_retains_diagnostics_before_deletion() -> None:
    private_job = WORKFLOW.split("  terraform:", 1)[1].split("  cleanup-private:", 1)[0]

    assert "capture_seeder_evidence()" in private_job
    assert "secret-seeder-job-definition.json" in private_job
    assert "secret-seeder-job.json" in private_job
    assert "secret-seeder-execution.json" in private_job
    assert "secret-seeder-console.log" in private_job
    assert "az containerapp job logs show" in private_job
    assert "Failed|Stopped)" in private_job
    assert "Private credential seeder timed out" in private_job
    assert private_job.count("capture_seeder_evidence") == 4
    assert 'cat secret-seeder-console.log >&2' in private_job
    delete_index = private_job.index("Delete private credential seeder")
    assert private_job.rindex("capture_seeder_evidence", 0, delete_index) < delete_index


def test_cost_evidence_is_queried_once_and_reused_by_private_job() -> None:
    assert WORKFLOW.count("CostManagement/query?api-version=2023-11-01") == 1
    assert WORKFLOW.count("CostManagement/forecast?api-version=2023-11-01") == 1
    assert "Download pre-start cost evidence" in WORKFLOW
    assert "goal006-private-runner-prestart-${{ github.run_id }}-${{ github.run_attempt }}" in WORKFLOW
    assert "Enforce workload cost boundary" in WORKFLOW


def test_batch_cost_control_suppresses_every_azure_cost_call_with_evidence() -> None:
    assert "enforce_cost_controls:" in WORKFLOW
    assert WORKFLOW.count("if: inputs.enforce_cost_controls") == 3
    assert "Record batch cost control mode" in WORKFLOW
    assert "cost-control.json" in WORKFLOW
    assert "suppress-for-pipeline-build" in WORKFLOW
    assert "Azure cost and budget calls are suppressed" in WORKFLOW


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