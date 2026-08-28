"""Contracts for private GOAL-006 Demo deployment execution."""

from pathlib import Path


WORKFLOW = Path(".github/workflows/deploy-environment.yaml").read_text(
    encoding="utf-8"
)
QUALIFICATION_WRAPPER = Path(".github/workflows/deploy-demo.yaml").read_text(
    encoding="utf-8"
)


def test_environment_deployment_uses_qualified_private_runner_lifecycle() -> None:
    assert "  resolve-environment:" in WORKFLOW
    assert "  start-broker:" in WORKFLOW
    assert "needs: resolve-environment" in WORKFLOW
    assert "needs: [resolve-environment, start-broker]" in WORKFLOW
    assert "${{ needs.resolve-environment.outputs.runner_label }}" in WORKFLOW
    assert "goal006-demo-private" not in WORKFLOW
    assert "  cleanup-private:" in WORKFLOW
    assert "needs: [resolve-environment, start-broker, terraform]" in WORKFLOW
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
    assert 'if secret_json=$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$name"' in seeder
    assert "az keyvault secret set-attributes" in seeder
    assert 'goal006-credential-schema="$CREDENTIAL_SCHEMA"' in seeder
    assert 'echo "credential_status name=$name status=preserved"' in seeder
    assert 'echo "credential_status name=$name status=created"' in seeder
    assert seeder.index("az keyvault secret show") < seeder.index("/dev/urandom")


def test_private_credential_seeding_runs_only_for_incomplete_inventory() -> None:
    assert "      - name: Check credential inventory" in WORKFLOW
    assert "credential-inventory.json" in WORKFLOW
    assert WORKFLOW.count("steps.credential-inventory.outputs.seeding_required == 'true'") == 3
    assert "schema-update-required" in WORKFLOW
    assert "SecretNotFound" in WORKFLOW
    assert "is disabled and will not be re-enabled automatically" in WORKFLOW


def test_workload_plan_safely_adopts_the_live_identity_edge() -> None:
    workload_plan = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Terraform workload apply", 1
    )[0]

    assert "module.workload.azurerm_container_app.identity_edge[0]" in workload_plan
    assert "terraform state list > workload-state-before-plan.txt" in workload_plan
    assert 'if ! grep -Fxq "$resource_address" workload-state-before-plan.txt' in workload_plan
    assert 'edge_name="ca-${{ inputs.environment }}-identity-edge"' in workload_plan
    assert "az containerapp list" in workload_plan
    assert 'if [ "$edge_count" = "1" ]' in workload_plan
    assert 'elif [ "$edge_count" != "0" ]' in workload_plan
    assert ".properties.managedEnvironmentId == $environment_id" in workload_plan
    assert "nginxinc/nginx-unprivileged@sha256:62a904036bfc0e4a4f2b556e34cbf17bc136b47fde8cdb4628762725f48c5782" in workload_plan
    assert ".properties.configuration.ingress.external == true" in workload_plan
    assert ".properties.configuration.ingress.targetPort == 8080" in workload_plan
    assert '.properties.provisioningState == "Succeeded"' in workload_plan
    assert "azure_edge_id=$(jq -er" in workload_plan
    assert "scripts/goal006_azure_resource_id.py" in workload_plan
    assert '--container-app-id "$azure_edge_id"' in workload_plan
    assert '--expected-resource-group "$edge_resource_group"' in workload_plan
    assert '--expected-name "$edge_name"' in workload_plan
    assert 'terraform import -input=false -lock-timeout=5m "$resource_address" "$edge_id"' in workload_plan
    assert workload_plan.index("goal006_azure_resource_id.py") < workload_plan.index("terraform import")
    assert workload_plan.index("terraform import") < workload_plan.index("terraform plan")
    assert "terraform show -json workload.tfplan > workload-plan.json" in workload_plan
    assert "scripts/goal006_tfplan_policy.py" in workload_plan
    assert WORKFLOW.index("goal006_tfplan_policy.py", WORKFLOW.index("Terraform workload plan")) < WORKFLOW.index(
        "      - name: Terraform workload apply"
    )
    assert "workload/workload-plan.json" in WORKFLOW
    assert "workload/workload-state-before-plan.txt" in WORKFLOW


def test_identity_edge_state_reconciliation_is_environment_parameterized() -> None:
    workload_plan = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Terraform workload apply", 1
    )[0]

    for environment in ("demo", "uat", "prod"):
        rendered_plan = workload_plan.replace("${{ inputs.environment }}", environment)
        assert f'edge_name="ca-{environment}-identity-edge"' in rendered_plan

    assert 'edge_name="ca-demo-identity-edge"' not in workload_plan


def test_private_workload_inputs_and_temporary_resources_are_environment_scoped() -> None:
    assert "CONFIG_BLOB: ${{ inputs.environment }}/workload-configuration.json" in WORKFLOW
    assert "SEEDER_JOB: goal006-${{ inputs.environment }}-secret-seeder" in WORKFLOW
    assert "CONFIG_BLOB: demo/workload-configuration.json" not in WORKFLOW
    assert "SEEDER_JOB: goal006-secret-seeder" not in WORKFLOW
    assert WORKFLOW.count("set -euo pipefail") >= 2


def test_uat_configuration_initialization_is_explicit_create_only_and_private() -> None:
    initialization = WORKFLOW.split("      - name: Initialize UAT configuration from Demo", 1)[1].split(
        "      - name: Download environment configuration with OIDC", 1
    )[0]

    assert "if: inputs.initialize_configuration" in initialization
    assert 'test "$TARGET_ENVIRONMENT" = uat' in initialization
    assert "source_blob=demo/workload-configuration.json" in initialization
    assert "--overwrite false" in initialization
    assert 'del(.founder_ipv4_cidr)' in initialization
    assert "scripts/goal006_lease.py" in initialization
    assert 'test "$promoted_sha256" = "$verified_sha256"' in initialization
    assert "configuration-promotion.json" in initialization
    assert "default: false" in WORKFLOW.split("initialize_configuration:", 1)[1]
    assert "initialize_configuration: true" in QUALIFICATION_WRAPPER


def test_expired_lease_fails_before_foundation_plan_and_apply_renewal_is_etag_bound() -> None:
    configuration = WORKFLOW.split("      - name: Download environment configuration with OIDC", 1)[1].split(
        "      - name: Capture configuration storage diagnostics", 1
    )[0]

    assert configuration.count("properties.etag") == 3
    assert 'test "$etag_before" = "$etag_after"' in configuration
    assert "REQUESTED_LEASE_EXPIRES_AT" in configuration
    assert "REQUESTED_ACCESS_CIDR" in configuration
    assert "TARGET_ENVIRONMENT" in configuration
    assert 'if test "$TARGET_ENVIRONMENT" = prod' in configuration
    assert 'test -z "$REQUESTED_LEASE_EXPIRES_AT"' in configuration
    assert 'test -z "$REQUESTED_ACCESS_CIDR"' in configuration
    assert 'if test "$TARGET_ENVIRONMENT" = demo' in configuration
    assert '.founder_ipv4_cidr = $access_cidr' in configuration
    assert "--expires-at \"$REQUESTED_LEASE_EXPIRES_AT\"" in configuration
    assert "--expires-at '${{ inputs.lease_expires_at }}'" not in configuration
    assert "scripts/goal006_lease.py" in configuration
    assert '--if-match "$etag_after"' in configuration
    assert 'test "$renewed_sha256" = "$verified_sha256"' in configuration
    assert "previous_etag" in configuration
    assert "renewed_etag" in configuration
    assert "configuration-lease-renewal.json" in WORKFLOW
    assert "configuration-lease-validation.json" in WORKFLOW
    assert "configuration-renewal-verification-attempts.jsonl" in WORKFLOW
    assert WORKFLOW.index("configuration-lease-validation.json") < WORKFLOW.index(
        "      - name: Terraform foundation plan"
    )


def test_plan_policy_reports_the_plan_scope() -> None:
    foundation = WORKFLOW.split("      - name: Terraform foundation plan", 1)[1].split(
        "      - name: Terraform foundation apply", 1
    )[0]
    workload = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Terraform workload apply", 1
    )[0]

    assert "--scope foundation" in foundation
    assert "--scope workload" in workload


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


def test_environment_deployment_cleanup_is_independent_and_retains_evidence() -> None:
    cleanup = WORKFLOW.split("  cleanup-private:", 1)[1]

    assert "client-id: ${{ env.RUNNER_CLEANUP_CLIENT_ID }}" in cleanup
    assert "client-id: ${{ env.ARM_CLIENT_ID }}" not in cleanup
    assert '--private-job-conclusion "$PRIVATE_JOB_CONCLUSION"' in cleanup
    assert '--cleanup-execution-name "$execution"' in cleanup
    assert 'cleanup/${{ inputs.environment }}/$GITHUB_RUN_ID/$GITHUB_RUN_ATTEMPT.json' in cleanup
    assert "goal006-private-runner-cleanup-${{ github.run_id }}-${{ github.run_attempt }}" in cleanup


def test_demo_deployment_binds_broker_and_cleanup_to_release_sha() -> None:
    assert WORKFLOW.count("ref: ${{ inputs.release_sha }}") >= 2
    assert "test '${{ inputs.release_sha }}' = \"$latest_main_sha\"" in WORKFLOW