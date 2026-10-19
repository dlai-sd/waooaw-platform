"""Contracts for private GOAL-006 Demo deployment execution."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
DISPATCH_WORKFLOW = (ROOT / ".github/workflows/deploy.yaml").read_text(encoding="utf-8")
FOUNDATION_MODULE = (ROOT / "infrastructure/terraform/phase2/modules/foundation/main.tf").read_text(encoding="utf-8")


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
    assert WORKFLOW.count("scripts/goal006_ghcr_digest.py") == 2
    assert '--expected-digest "$expected_digest"' in WORKFLOW
    assert "https://mcr.microsoft.com/v2/$repository/manifests/$expected_digest" in WORKFLOW
    assert WORKFLOW.count('test "$actual_digest" = "$expected_digest"') == 2


def test_wc124_live_cli_contracts_match_the_pinned_runner() -> None:
    provisioner = WORKFLOW.split("      - name: Create WC-124 database provisioner", 1)[1].split(
        "      - name: Run WC-124 database provisioner", 1
    )[0]
    handoff = WORKFLOW.split("      - name: Verify WC-124 database credential handoff", 1)[1].split(
        "      - name: Build workload inputs", 1
    )[0]
    authority_handoff = WORKFLOW.split("      - name: Finalize WC-124 PostgreSQL authority handoff", 1)[1].split(
        "      - name: Remove WC-124 Entra bootstrap authority", 1
    )[0]
    bootstrap_removal = WORKFLOW.split("      - name: Remove WC-124 Entra bootstrap authority", 1)[1].split(
        "      - name: Verify WC-124 database credential handoff", 1
    )[0]

    assert '--reference "$release_tag"' in provisioner
    assert "replicaRetryLimit: 1" in provisioner
    assert "az resource wait" in provisioner
    assert "--deleted" in provisioner
    assert "keys(identity.userAssignedIdentities)" in provisioner
    assert 'test "$actual_identities" = "$expected_identities"' in provisioner
    assert "--tail 300" in WORKFLOW
    assert "--tail 500" not in WORKFLOW
    assert "postgres flexible-server microsoft-entra-admin list" in handoff
    assert "postgres flexible-server ad-admin" not in WORKFLOW
    assert 'if [ "$secret_id" = "db-pgbouncer-auth" ]' in handoff
    assert 'expected_role="pgbouncer_auth"' in handoff
    assert '.tags["wc124-role"] // ""' in handoff
    assert "/opt/waooaw/wc124_db_handoff.py" in authority_handoff
    assert 'test "$actual_identities" = "$expected_identities"' in authority_handoff
    assert '"remaining_bootstrap_dependencies": 0' in authority_handoff
    assert '-var="database_bootstrap_admin_enabled=false"' in bootstrap_removal
    assert '-var="database_provisioner_vault_access_enabled=false"' in bootstrap_removal
    assert "microsoft-entra-admin list" in bootstrap_removal


def test_wc124_plan_b_uses_sealed_structured_provider_update() -> None:
    assert 'source  = "Azure/azapi"' in FOUNDATION_MODULE
    assert 'resource "random_password" "postgresql_breakglass_administrator"' in FOUNDATION_MODULE
    assert 'name         = "db-server-breakglass-admin"' in FOUNDATION_MODULE
    assert 'resource "azapi_update_resource" "postgresql_plan_b_authentication"' in FOUNDATION_MODULE
    assert 'type        = "Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01"' in FOUNDATION_MODULE
    assert 'administratorLogin         = "wc124_breakglass_admin"' in FOUNDATION_MODULE
    assert "administratorLoginPassword = random_password.postgresql_breakglass_administrator[0].result" in FOUNDATION_MODULE
    assert 'passwordAuth        = "Enabled"' in FOUNDATION_MODULE
    assert "authentication[0].password_auth_enabled" in FOUNDATION_MODULE


def test_database_transition_state_fails_closed_on_azure_errors() -> None:
    transition = WORKFLOW.split("      - name: Resolve WC-124 database transition state", 1)[1].split(
        "      - name: Terraform foundation plan", 1
    )[0]

    assert "az postgres flexible-server list" in transition
    assert "microsoft-entra-admin list" in transition
    assert "az role assignment list" in transition
    assert "wc124_database_transition.py" in transition
    assert "RECOVERY_HOLD" in transition
    assert "2>/dev/null" not in transition


def test_database_transition_reconciles_revocation_only_after_independent_handoff_verification() -> None:
    foundation_plan = WORKFLOW.split("      - name: Terraform foundation plan", 1)[1].split(
        "      - name: Terraform foundation apply", 1
    )[0]
    recovery = WORKFLOW.split("      - name: Verify interrupted WC-124 handoff before revocation", 1)[1].split(
        "      - name: Remove WC-124 Entra bootstrap authority", 1
    )[0]

    assert "database_provisioner_vault_access_enabled" in foundation_plan
    assert "revocation_verification_required" in WORKFLOW
    assert "--verify-only" in WORKFLOW
    assert '"remaining_bootstrap_dependencies": 0' in recovery
    assert '"remaining_bootstrap_sessions": 0' in recovery
    assert '"status": "verified-after-entra-bootstrap-removal"' in recovery
    assert "provisioner_vault_role_count" in WORKFLOW
    assert 'status: "revocation-verified"' in WORKFLOW
    assert "wc124-bootstrap-revocation-evidence.json" in WORKFLOW
    delete_provisioner = WORKFLOW.split("      - name: Delete WC-124 database provisioner", 1)[1].split(
        "      - name: Retain persistent-state lifecycle execution evidence", 1
    )[0]
    assert "provisioner_required == 'true'" in delete_provisioner
    assert "revocation_verification_required == 'true'" in delete_provisioner
    assert "Reconcile legacy PgBouncer credential metadata" in WORKFLOW
    assert 'test "$current_role" = pgbouncer || {' in WORKFLOW
    assert 'PYTHONPATH="$GITHUB_WORKSPACE/scripts"' in WORKFLOW
    assert "from wc124_db_provisioner import environment_specs, parse_authfile" in WORKFLOW
    assert "az keyvault secret set-attributes" in WORKFLOW
    assert "wc124-pgbouncer-metadata-reconciliation.json" in WORKFLOW
    assert "expected_count=$(jq" in WORKFLOW


def test_pgbouncer_reconciliation_import_executes_with_runner_module_path() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "scripts")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from wc124_db_provisioner import environment_specs, parse_authfile; "
                "assert len(environment_specs('demo')) == 17; "
                "assert parse_authfile('\"role\" \"SCRAM-SHA-256$4096:salt$stored:server\"\\n') == "
                "{'role': 'SCRAM-SHA-256$4096:salt$stored:server'}"
            ),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_wc124_container_app_job_names_fit_azure_limit() -> None:
    workload = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text(encoding="utf-8")
    assert 'name                         = "job-${var.environment}-temporal-migration"' in workload
    assert 'name                         = "job-${var.environment}-keycloak-migration"' in workload
    assert len("job-demo-temporal-migration") <= 32
    assert len("job-demo-keycloak-migration") <= 32


def test_wc124_vendor_job_names_fit_azure_limit() -> None:
    workload = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text(encoding="utf-8")

    assert 'name                         = "job-${var.environment}-temporal-migration"' in workload
    assert 'name                         = "job-${var.environment}-keycloak-migration"' in workload
    assert len("job-demo-temporal-migration") <= 32
    assert len("job-demo-keycloak-migration") <= 32
    migration_step = WORKFLOW.split("      - name: Run vendor schema migrations", 1)[1].split(
        "      - name: Run additive Billing authority migration", 1
    )[0]
    assert 'keycloak|temporal) job_name="job-${TARGET_ENVIRONMENT}-${component}-migration"' in migration_step
    assert 'job_name="job-${TARGET_ENVIRONMENT}-wc124-${component}-migration"' not in migration_step


def test_application_activation_plan_is_policy_and_provenance_bound() -> None:
    plan_step = WORKFLOW.split("      - name: Plan application activation after migration", 1)[1].split(
        "      - name: Apply application activation", 1
    )[0]
    apply_step = WORKFLOW.split("      - name: Apply application activation", 1)[1].split(
        "      - name: Bind Demo Azure-managed TLS certificates", 1
    )[0]

    assert "terraform plan -detailed-exitcode" in plan_step
    assert '0|2) ;;' in plan_step
    assert "--output workload-activation-policy.json" in plan_step
    assert "--plan-binary workload-activation.tfplan" in plan_step
    assert "--output workload-activation-provenance.json" in plan_step
    assert "cmp --silent workload-activation-provenance.json" in apply_step
    assert apply_step.index("cmp --silent") < apply_step.index("terraform apply")


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
    assert "status=invalid-length" in WORKFLOW
    assert 'test "$name" != "conversation-cursor-hmac"' in seeder
    assert 'jq -r ".value | length"' in seeder
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
        "      - name: Terraform dormant workload and migration dependency apply"
    )
    assert "workload/workload-plan.json" in WORKFLOW
    assert "workload/workload-state-before-plan.txt" in WORKFLOW


def test_apply_generates_internal_activation_bundle_after_both_plans() -> None:
    bundle_step = WORKFLOW.split(
        "      - name: Generate internal WC-124 activation bundle",
        1,
    )[1].split(
        "      - name: Terraform dormant workload and migration dependency apply",
        1,
    )[0]

    assert "if: inputs.apply" in bundle_step
    assert "scripts/wc124_deployment_bundle.py" in bundle_step
    assert "--foundation-plan" in bundle_step
    assert "--foundation-plan-binary" in bundle_step
    assert "--foundation-plan-provenance" in bundle_step
    assert "--foundation-policy-result" in bundle_step
    assert "--workload-plan" in bundle_step
    assert "--workload-plan-binary" in bundle_step
    assert "--workload-plan-provenance" in bundle_step
    assert "--workload-policy-result" in bundle_step
    assert "--secret-catalog" in bundle_step
    assert "--dependency-file registry-release-manifest.json" in bundle_step
    assert "--migration-file infrastructure/postgres/init/59-wc124-billing-authority.sql" in bundle_step
    assert '"${schema_arguments[@]}"' in bundle_step
    assert 'test -s "$evidence_file"' in bundle_step
    assert "scripts/wc124_persistent_state_lifecycle.py" in bundle_step
    assert "--action activate" in bundle_step
    assert WORKFLOW.index("Terraform foundation plan") < WORKFLOW.index("Generate internal WC-124 activation bundle")
    assert WORKFLOW.index("Terraform workload plan") < WORKFLOW.index("Generate internal WC-124 activation bundle")
    assert WORKFLOW.index("Generate internal WC-124 activation bundle") < WORKFLOW.index(
        "Terraform dormant workload and migration dependency apply"
    )
    assert "wc124-deployment-activation-bundle.json" in WORKFLOW
    assert "wc124-lifecycle-authorization-record.json" in WORKFLOW


def test_plan_evidence_is_current_exact_run_and_cache_drift_fails_closed() -> None:
    foundation_plan = WORKFLOW.split("      - name: Terraform foundation plan", 1)[1].split(
        "      - name: Terraform foundation apply", 1
    )[0]
    workload_plan = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Generate internal WC-124 activation bundle", 1
    )[0]

    assert "if: inputs.apply || steps.foundation-cache.outputs.cache_hit != 'true'" in foundation_plan
    assert "terraform plan -detailed-exitcode" in foundation_plan
    assert "0) plan_has_changes=false" in foundation_plan
    assert "2) plan_has_changes=true" in foundation_plan
    assert 'test "$CACHE_HIT" = true && test "$plan_has_changes" = true' in foundation_plan
    assert "refusing automatic apply" in foundation_plan
    assert "goal006_plan_provenance.py" in foundation_plan
    assert "--output foundation-plan-policy.json" in foundation_plan
    assert "--policy-result foundation-plan-policy.json" in foundation_plan
    assert '--scope foundation' in foundation_plan
    assert '--release-sha "$RELEASE_SHA"' in foundation_plan
    assert '--workflow-run-id "$GITHUB_RUN_ID"' in foundation_plan
    assert "terraform plan -detailed-exitcode" in workload_plan
    assert "0|2)" in workload_plan
    assert "goal006_plan_provenance.py" in workload_plan
    assert "--output workload-plan-policy.json" in workload_plan
    assert "--policy-result workload-plan-policy.json" in workload_plan
    assert "--scope workload" in workload_plan


def test_identity_edge_state_reconciliation_is_environment_parameterized() -> None:
    workload_plan = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split(
        "      - name: Terraform dormant workload and migration dependency apply", 1
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
    assert "del(.founder_ipv4_cidr)" in initialization
    assert "scripts/goal006_lease.py" in initialization
    assert 'test "$promoted_sha256" = "$verified_sha256"' in initialization
    assert "configuration-promotion.json" in initialization
    assert "default: false" in WORKFLOW.split("initialize_configuration:", 1)[1]
    assert "initialize_configuration: true" not in DISPATCH_WORKFLOW
    assert not (ROOT / ".github/workflows/deploy-demo.yaml").exists()


def test_expired_lease_fails_before_foundation_plan_and_apply_renewal_is_etag_bound() -> None:
    configuration = WORKFLOW.split("      - name: Download environment configuration with OIDC", 1)[1].split(
        "      - name: Capture configuration storage diagnostics", 1
    )[0]

    assert configuration.count("properties.etag") == 3
    assert 'test "$etag_before" = "$etag_after"' in configuration
    assert "REQUESTED_LEASE_EXPIRES_AT" in configuration
    assert "TARGET_ENVIRONMENT" in configuration
    assert 'if test "$TARGET_ENVIRONMENT" = prod' in configuration
    assert 'test -z "$REQUESTED_LEASE_EXPIRES_AT"' in configuration
    assert "REQUESTED_ACCESS_CIDR" not in configuration
    assert ".founder_ipv4_cidr = $access_cidr" not in configuration
    assert '--expires-at "$REQUESTED_LEASE_EXPIRES_AT"' in configuration
    assert "--expires-at '${{ inputs.lease_expires_at }}'" not in configuration
    assert "scripts/goal006_lease.py" in configuration
    assert '--if-match "$etag_after"' in configuration
    assert 'test "$renewed_sha256" = "$verified_sha256"' in configuration
    assert "previous_etag" in configuration
    assert "renewed_etag" in configuration
    assert "configuration-lease-renewal.json" in WORKFLOW
    assert "configuration-lease-validation.json" in WORKFLOW
    assert "configuration-renewal-verification-attempts.jsonl" in WORKFLOW
    assert WORKFLOW.index("configuration-lease-validation.json") < WORKFLOW.index("      - name: Terraform foundation plan")


def test_plan_policy_reports_the_plan_scope() -> None:
    foundation = WORKFLOW.split("      - name: Terraform foundation plan", 1)[1].split(
        "      - name: Terraform foundation apply", 1
    )[0]
    workload = WORKFLOW.split("      - name: Terraform workload plan", 1)[1].split("      - name: Terraform workload apply", 1)[0]

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
    assert private_job.count("capture_seeder_evidence") == 5
    assert "cat secret-seeder-console.log >&2" in private_job
    delete_index = private_job.index("Delete private credential seeder")
    assert private_job.rindex("capture_seeder_evidence", 0, delete_index) < delete_index


def test_job_polling_rejects_empty_and_unknown_statuses() -> None:
    assert WORKFLOW.count("Processing|Running)") == 8
    assert WORKFLOW.count("returned unknown status: ${status:-<empty>}") == 8


def test_provisioner_replacement_waits_for_confirmed_deletion() -> None:
    create_step = WORKFLOW.split("      - name: Create WC-124 database provisioner", 1)[1].split(
        "      - name: Run WC-124 database provisioner", 1
    )[0]

    assert "az containerapp job list" in create_step
    assert "az resource wait" in create_step
    assert "--deleted" in create_step
    assert "--timeout 300" in create_step
    assert "2>/dev/null" not in create_step


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
    assert "cleanup/${{ inputs.environment }}/$GITHUB_RUN_ID/$GITHUB_RUN_ATTEMPT.json" in cleanup
    assert "goal006-private-runner-cleanup-${{ github.run_id }}-${{ github.run_attempt }}" in cleanup
    assert "if: always() && hashFiles('cleanup-record.json') != ''" in cleanup
    assert "Authorize exact break-fix cleanup subject" in WORKFLOW
    assert "repo:${{ github.repository }}:ref:refs/heads/ib/532/wc124-transition-reconciliation" in WORKFLOW
    assert "revoke-break-fix-cleanup-trust:" in cleanup
    assert "Revoke exact break-fix cleanup subject" in cleanup
    assert "environment: ${{ inputs.environment }}" in cleanup


def test_demo_deployment_binds_broker_and_cleanup_to_authorized_control_sha() -> None:
    assert WORKFLOW.count("ref: ${{ inputs.control_sha }}") >= 2
    assert "test '${{ inputs.release_sha }}' = \"$latest_main_sha\"" in WORKFLOW
    assert 'test "$GITHUB_SHA" = \'${{ inputs.control_sha }}\'' in WORKFLOW
    assert "refs/heads/ib/532/wc124-*" in WORKFLOW
