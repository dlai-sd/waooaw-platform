"""Offline contracts for GOAL-006 P2-WC03 Terraform foundations."""

from __future__ import annotations

import re
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import goal006_live_inventory  # noqa: E402

PHASE2_ROOT = REPO_ROOT / "infrastructure" / "terraform" / "phase2"
ENVIRONMENTS = ("demo", "uat", "prod")
PRIVATE_MEMBERS = ("constitutional-engine", "ai-runtime", "billing-engine")
PUBLIC_CANDIDATES = ("web", "business-platform", "professional-runtime")


def read_contract(relative_path: str) -> str:
    path = PHASE2_ROOT / relative_path
    assert path.is_file(), f"missing P2-WC03 contract: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def test_live_inventory_requires_pinned_keycloak_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(goal006_live_inventory, "validate_registry_manifest", lambda manifest: [])
    images = {
        member: f"ghcr.io/dlai-sd/{member}@sha256:{'a' * 64}"
        for member in goal006_live_inventory.RELEASE_MEMBERS
    }
    inventory = [
        {"name": f"ca-demo-{member}", "image": image, "provisioningState": "Succeeded"}
        for member, image in images.items()
    ]
    inventory.append(
        {
            "name": "ca-demo-keycloak",
            "image": goal006_live_inventory.KEYCLOAK_IMAGE,
            "provisioningState": "Succeeded",
        }
    )

    assert goal006_live_inventory.validate_inventory("demo", {"images": images}, inventory) == []
    assert "LIVE_MEMBERSHIP_INVALID" in goal006_live_inventory.validate_inventory(
        "demo", {"images": images}, inventory[:-1]
    )


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_environment_roots_have_isolated_state_and_oidc(environment: str) -> None:
    foundation = read_contract(f"environments/{environment}/foundation/main.tf")
    workload = read_contract(f"environments/{environment}/workload/main.tf")

    assert f'key = "goal006/{environment}/foundation.tfstate"' in foundation
    assert f'key = "goal006/{environment}/workload.tfstate"' in workload
    assert re.search(rf'key\s*=\s*"goal006/{environment}/foundation.tfstate"', workload)
    for backend_field in ("resource_group_name", "storage_account_name", "container_name"):
        assert backend_field in workload
    assert "use_oidc             = true" in workload
    assert "use_azuread_auth     = true" in workload
    assert re.search(rf'environment\s*=\s*"{environment}"', foundation)
    assert re.search(r'source\s*=\s*"../../../modules/foundation"', foundation)
    assert 'source = "../../../modules/workload"' in workload
    for contract in (foundation, workload):
        assert re.search(r"use_oidc\s*=\s*true", contract)
        assert re.search(r"use_cli\s*=\s*false", contract)
        assert re.search(r'resource_provider_registrations\s*=\s*"none"', contract)
        assert "client_secret" not in contract.lower()


def test_foundation_and_workload_have_distinct_owners() -> None:
    assert not list((PHASE2_ROOT / "modules" / "environment").glob("*.tf"))
    for environment in ENVIRONMENTS:
        foundation = read_contract(f"environments/{environment}/foundation/main.tf")
        workload = read_contract(f"environments/{environment}/workload/main.tf")
        assert 'module "workload"' not in foundation
        assert 'module "foundation"' not in workload
        assert 'data "terraform_remote_state" "foundation"' in workload


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_workload_roots_use_current_secret_and_ingress_contract(environment: str) -> None:
    workload = read_contract(f"environments/{environment}/workload/main.tf")
    variables = read_contract(f"environments/{environment}/workload/variables.tf")

    for field in (
        "container_app_environment_default_domain",
        "verification_principal_id",
        "key_vault_secret_uris",
        "key_vault_secret_resource_ids",
        "founder_ipv4_cidr",
    ):
        assert re.search(rf"{field}\s*=\s*", workload)
        if field in {"key_vault_secret_uris", "key_vault_secret_resource_ids", "founder_ipv4_cidr"}:
            assert f'variable "{field}"' in variables
    assert "key_vault_secret_ids" not in f"{workload}\n{variables}"


def test_workloads_use_exact_six_digests_and_multiple_revision_mode() -> None:
    contract = read_contract("modules/workload/main.tf")
    variables = read_contract("modules/workload/variables.tf")

    assert re.search(r'revision_mode\s*=\s*"Multiple"', contract)
    assert "@sha256:" in variables
    assert ":latest" not in f"{contract}\n{variables}"
    assert "setequals(" not in f"{contract}\n{variables}"
    for member in (*PRIVATE_MEMBERS, *PUBLIC_CANDIDATES):
        assert f'"{member}"' in contract


def test_private_boundaries_and_key_vault_references_are_explicit() -> None:
    contract = read_contract("modules/workload/main.tf")

    for member in PRIVATE_MEMBERS:
        assert re.search(rf'"{member}"\s*=\s*false', contract)
    for member in PUBLIC_CANDIDATES:
        assert re.search(rf'"{member}"\s*=\s*true', contract)
    assert "key_vault_secret_id" in contract
    assert "secret_value" not in contract
    assert "var.key_vault_secret_uris[local.credential_member[each.key]]" in contract
    assert "var.key_vault_secret_resource_ids[local.credential_member[each.key]]" in contract
    assert "KEYCLOAK_CLIENT_SECRET" in contract
    assert "NEXTAUTH_SECRET" in contract
    assert "OPS_AUTH_TOKEN" in contract
    assert 'key_vault_secret_uris["business-platform"]' in contract
    assert '"ai-runtime"            = "professional-runtime"' in contract
    assert "BP_BASE_URL" in contract
    assert "ca-${var.environment}-constitutional-engine:80" in contract
    assert 'resource "azurerm_container_app_job" "verification"' in contract
    assert 'role_definition_name = "Container Apps Jobs Operator"' in contract


def test_internal_verification_bypasses_founder_restricted_public_ingress() -> None:
    contract = read_contract("modules/workload/main.tf")
    verification_job = contract.split(
        'resource "azurerm_container_app_job" "verification"', 1
    )[1]

    assert 'web               = "http://ca-${var.environment}-web"' in contract
    assert 'keycloak          = "http://ca-${var.environment}-keycloak"' in contract
    assert 'probe web "${local.verification_urls.web}/"' in verification_job
    assert 'probe business-platform "${local.verification_urls.business_platform}/health/ready"' in verification_job
    assert 'probe keycloak "${local.verification_urls.keycloak}/realms/waooaw/.well-known/openid-configuration"' in verification_job
    assert "local.service_urls.web" not in verification_job
    assert "local.service_urls.keycloak" not in verification_job


def test_each_release_member_has_its_own_identity_and_secret_scope() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert 'resource "azurerm_user_assigned_identity" "member"' in contract
    assert 'resource "azurerm_role_assignment" "member_secret"' in contract
    assert "azurerm_user_assigned_identity.member[each.key].id" in contract
    assert "scope                = var.key_vault_secret_resource_ids[local.credential_member[each.key]]" in contract
    assert 'resource "azurerm_role_assignment" "professional_runtime_bp_secret"' in contract
    assert "runtime_identity_id" not in contract
    assert "runtime_identity_client_id" not in contract


def test_deployment_identity_is_environment_scoped_for_resources_and_rbac() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert contract.count("scope                = azurerm_resource_group.environment.id") == 3
    assert 'role_definition_name = "Contributor"' in contract
    assert 'role_definition_name = "Role Based Access Control Administrator"' in contract
    assert "azurerm_user_assigned_identity.deployment.principal_id" in contract
    assert 'output "deployment_client_id"' in contract
    assert 'role_definition_name = "Key Vault Secrets Officer"' in contract
    assert 'scope                = azurerm_key_vault.environment.id' in contract
    assert 'output "deployment_identity_id"' in contract
    assert 'role_definition_name = "Reader"' in contract
    assert "azurerm_user_assigned_identity.verification.principal_id" in contract
    assert 'output "verification_client_id"' in contract


@pytest.mark.parametrize("environment", ("demo", "uat"))
def test_environment_foundation_roots_expose_identity_client_ids(environment: str) -> None:
    contract = read_contract(f"environments/{environment}/foundation/main.tf")

    assert re.search(r'output "deployment_client_id"\s*{\s*value\s*=\s*module\.foundation\.deployment_client_id', contract)
    assert re.search(r'output "verification_client_id"\s*{\s*value\s*=\s*module\.foundation\.verification_client_id', contract)
    if environment == "demo":
        assert re.search(r'output "deployment_identity_id"\s*{\s*value\s*=\s*module\.foundation\.deployment_identity_id', contract)


def test_disabled_lease_removes_all_disposable_workload_resources() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert "active_members = var.workload_enabled ? local.release_members : toset([])" in contract
    assert contract.count("for_each = local.active_members") == 3
    assert "var.workload_enabled ? local.minimum_replicas" not in contract


def test_enabled_workloads_require_verified_public_ghcr_packages() -> None:
    contract = read_contract("modules/workload/main.tf")
    variables = read_contract("modules/workload/variables.tf")

    assert 'variable "ghcr_packages_public"' in variables
    assert re.search(r'variable "ghcr_packages_public"\s*{[^}]*default\s*=\s*false', variables, re.DOTALL)
    assert "!var.workload_enabled || var.ghcr_packages_public" in contract
    assert "allow anonymous digest pulls" in contract
    for environment in ENVIRONMENTS:
        root = read_contract(f"environments/{environment}/workload/main.tf")
        root_variables = read_contract(f"environments/{environment}/workload/variables.tf")
        assert re.search(r"ghcr_packages_public\s*=\s*var\.ghcr_packages_public", root)
        assert re.search(
            r'variable "ghcr_packages_public"\s*{[^}]*default\s*=\s*false',
            root_variables,
            re.DOTALL,
        )


def test_foundation_is_private_isolated_and_environment_scoped() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert 'name     = "${local.name}-rg"' in contract
    assert 'name     = "rg-${local.name}"' not in contract
    for cidr in ("10.60.0.0/16", "10.61.0.0/16", "10.62.0.0/16"):
        assert cidr in contract
    assert 'subject             = "repo:${var.repository_id}:environment:${var.repository_environment}"' in contract
    assert 'subject             = "repo:${var.repository_id}:environment:${var.repository_environment}-verification"' in contract
    assert "public_network_access_enabled = false" in contract
    assert 'default_action = "Deny"' in contract
    assert 'subresource_names              = ["vault"]' in contract
    assert contract.count("azurerm_subnet_network_security_group_association") == 2
    assert "internal_load_balancer_enabled = !var.external_environment" in contract
    assert 'name                = "privatelink.vaultcore.azure.net"' in contract
    assert 'private_dns_zone_group {' in contract
    assert "private_dns_zone_ids = [azurerm_private_dns_zone.key_vault.id]" in contract


def test_container_app_environment_ignores_unconfigurable_force_new_drift() -> None:
    contract = read_contract("modules/foundation/main.tf")

    environment = re.search(
        r'resource "azurerm_container_app_environment" "environment" \{(?P<body>.*?)\n\}',
        contract,
        re.DOTALL,
    )
    assert environment is not None
    assert "ignore_changes = [infrastructure_resource_group_name]" in environment.group("body")
    assert "infrastructure_resource_group_name =" not in environment.group("body")


def test_each_environment_persists_container_app_logs() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert 'resource "azurerm_log_analytics_workspace" "environment"' in contract
    assert 'name                = coalesce(var.log_analytics_workspace_name, "law-${local.name}")' in contract
    assert "retention_in_days   = 30" in contract
    assert "log_analytics_workspace_id     = azurerm_log_analytics_workspace.environment.id" in contract
    assert 'output "log_analytics_workspace_id"' in contract


def test_demo_adopts_existing_validation_workspace_without_cleanup_debt() -> None:
    demo = read_contract("environments/demo/foundation/main.tf")

    assert "to = module.foundation.azurerm_log_analytics_workspace.environment" in demo
    assert "workspaces/law-waooaw-demo-validation" in demo
    assert 'log_analytics_workspace_name = "law-waooaw-demo-validation"' in demo


def test_verification_emits_structured_probe_results() -> None:
    contract = read_contract("modules/workload/main.tf")
    verification_job = contract.split(
        'resource "azurerm_container_app_job" "verification"', 1
    )[1]

    assert "probe_result name=$name status=succeeded" in verification_job
    assert "probe_attempt name=$name status=failed" in verification_job
    assert "http_code=$http_code" in verification_job
    assert "curl_exit=$curl_exit" in verification_job


def test_post_deploy_verification_retains_each_container_log() -> None:
    workflow = (REPO_ROOT / ".github/workflows/post-deploy-verify.yaml").read_text(
        encoding="utf-8"
    )

    assert "capture_functional_evidence()" in workflow
    assert "for container in http-probes constitutional-health" in workflow
    assert 'functional-$container.log' in workflow
    assert "functional-http-probes.log" in workflow
    assert "functional-constitutional-health.log" in workflow
    assert "Failed|Stopped)" in workflow
    assert "verification timed out with status" in workflow


def test_demo_review_ingress_is_founder_restricted_and_other_environments_remain_private() -> None:
    demo = read_contract("environments/demo/foundation/main.tf")
    uat = read_contract("environments/uat/foundation/main.tf")
    prod = read_contract("environments/prod/foundation/main.tf")
    workload = read_contract("modules/workload/main.tf")
    demo_workload = read_contract("environments/demo/workload/main.tf")

    assert re.search(r"external_environment\s*=\s*true", demo)
    assert "external_environment" not in uat
    assert "external_environment" not in prod
    assert 'name             = "founder-review"' in workload
    assert "ip_address_range = ip_security_restriction.value" in workload
    assert re.search(r"founder_ipv4_cidr\s*=\s*var\.founder_ipv4_cidr", demo_workload)
    assert re.search(r"max_replicas\s*=\s*1", demo_workload)
    assert 'output "web_url"' in demo_workload


def test_network_egress_is_explicitly_fail_closed() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert contract.count('name                       = "deny-unapproved-egress"') == 2
    assert contract.count('priority                   = 4096') == 2
    assert contract.count('direction                  = "Outbound"') == 5
    assert contract.count('access                     = "Deny"') == 2
    assert 'destination_address_prefix = "VirtualNetwork"' in contract
    assert 'destination_address_prefix = "168.63.129.16/32"' in contract
    assert 'destination_port_range     = "443"' in contract
    assert 'destination_address_prefix = "Internet"' in contract


def test_scale_contract_is_bounded_and_defaults_to_zero() -> None:
    contract = read_contract("modules/workload/variables.tf")
    prod_root = read_contract("environments/prod/workload/main.tf")
    prod_variables = read_contract("environments/prod/workload/variables.tf")

    assert contract.count("default = 0") == 2
    assert "var.max_replicas > 0 && var.max_replicas <= 10" in contract
    uat_root = read_contract("environments/uat/workload/main.tf")
    assert re.search(r"ce_min_replicas\s*=\s*0", uat_root)
    assert re.search(r"pr_min_replicas\s*=\s*0", uat_root)
    assert re.search(r"ce_min_replicas\s*=\s*var\.ce_min_replicas", prod_root)
    assert re.search(r"pr_min_replicas\s*=\s*var\.pr_min_replicas", prod_root)
    assert prod_variables.count("requires an accepted positive owner value") == 2


def test_jit_break_glass_requires_separation_expiry_and_evidence() -> None:
    contract = read_contract("modules/access-control/main.tf")

    required_terms = (
        "approver_principal_id",
        "executor_principal_id",
        "requested_scope",
        "incident_id",
        "reason",
        "expires_at",
        "revoked_at",
        "evidence_digest",
    )
    for term in required_terms:
        assert term in contract
    assert "approver_principal_id != var.executor_principal_id" in contract
    assert 'var.activation_state == "ACTIVE"' in contract
    assert "var.revoked_at == null" in contract
    assert "timecmp(var.expires_at, timestamp()) > 0" in contract
    assert "var.activation_state != \"REVOKED\" || var.revoked_at != null" in contract
    assert 'output "authority_enabled"' in contract


def test_lease_lifecycle_preserves_foundation_and_prohibits_production() -> None:
    contract = read_contract("modules/lifecycle/main.tf")
    variables = read_contract("modules/lifecycle/variables.tf")

    for term in ("manifest_digest", "owner_principal_id", "expires_at", "cost_centre", "evidence_digest"):
        assert term in contract
    assert "protected_foundation_id" in contract
    assert 'contains(["demo", "uat"], var.environment)' in variables
    assert "timecmp(var.expires_at, plantimestamp()) > 0" in contract
    assert "timecmp(var.expires_at, timestamp())" not in contract
    assert 'output "workload_enabled"' in contract

    for environment in ("demo", "uat"):
        workload = read_contract(f"environments/{environment}/workload/main.tf")
        assert 'module "lease"' in workload
        assert re.search(r"workload_enabled\s*=\s*module\.lease\.workload_enabled", workload)
    assert 'module "lease"' not in read_contract("environments/prod/workload/main.tf")


def test_lease_reconciliation_is_manual_demo_plan_only_until_activation() -> None:
    workflow = (REPO_ROOT / ".github/workflows/reconcile-workload-leases.yaml").read_text(encoding="utf-8")
    validator = (REPO_ROOT / "scripts/goal006_lease_reconciliation.py").read_text(encoding="utf-8")

    assert "schedule:" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "environment: demo" in workflow
    assert "environment: uat" not in workflow
    assert "environment: prod" not in workflow
    assert "WAOOAW_PLATFORM_DEPLOYMENT_CLIENT_ID" not in workflow
    assert "lease_reconciliation_inputs" in workflow
    assert "reconciliation-plan.json" in workflow
    assert "terraform apply" not in workflow
    assert "PRODUCTION_RECONCILIATION_PROHIBITED" in validator
    assert "DISPOSABLE_PREFIXES" in validator


def test_demo_credential_seeder_passes_shell_flags_as_container_arguments() -> None:
    workflow = (REPO_ROOT / ".github/workflows/deploy-environment.yaml").read_text(encoding="utf-8")

    assert "--command /bin/sh -c" not in workflow
    assert "seeder_script='set -eu;" in workflow
    assert 'args: ["-c", $script]' in workflow
    assert "--yaml secret-seeder-job-definition.json" in workflow
    assert "seeder_args=$(jq" not in workflow


def test_local_rehearsal_is_offline_pinned_and_covers_the_full_goal006_path() -> None:
    rehearsal = (REPO_ROOT / "scripts/run_goal006_local_rehearsal.sh").read_text(encoding="utf-8")

    assert "azure/login" not in rehearsal
    assert "az login --" not in rehearsal
    assert "az containerapp job create" in rehearsal
    assert "Please run 'az login'" in rehearsal
    assert "hashicorp/terraform:1.9.8" in rehearsal
    assert "for environment in demo uat prod" in rehearsal
    assert "for root in foundation workload" in rehearsal
    assert "terraform plan: lease-controlled workload membership" in rehearsal
    assert "for_each = module.lease.workload_enabled" in rehearsal
    assert "rhysd/actionlint:1.7.7" in rehearsal
    assert "pytest tests/pipeline/test_goal006_*.py" in rehearsal


def test_oidc_policy_requires_exact_governed_refs_and_workflows() -> None:
    policy = json.loads(read_contract("policies/oidc-trust-policy.json"))

    assert policy["repository"] == "dlai-sd/waooaw-platform"
    assert policy["allowed_environments"] == ["demo", "uat", "prod"]
    assert policy["allowed_verification_environments"] == [
        "demo-verification",
        "uat-verification",
        "prod-verification",
    ]
    assert policy["allowed_refs"] == ["refs/heads/main"]
    assert policy["allowed_workflows"] == [".github/workflows/deploy-demo.yaml@refs/heads/main"]
    assert policy["subject_claim_template"] == ["repo", "environment"]
    assert policy["wildcards_allowed"] is False
    assert all("*" not in value for value in (*policy["allowed_refs"], *policy["allowed_workflows"]))
    assert policy["workflow_allowlist_enforcement"] == (
        "exact_github_workflow_ref_guard_before_oidc_login_plus_protected_main_only_environments"
    )
    assert policy["credential_enforcement"] == "exact_repository_environment_subject_without_wildcards"

    foundation = read_contract("modules/foundation/main.tf")
    variables = read_contract("modules/foundation/variables.tf")
    assert "for_each = var.repository_workflows" not in foundation
    assert "environment:${var.repository_environment}" in foundation
    assert "environment:${var.repository_environment}-verification" in foundation
    assert "repository_ref" not in variables
    assert "repository_workflows" not in variables


def test_deployment_workflow_pins_accepted_terraform_version() -> None:
    workflow = (REPO_ROOT / ".github/workflows/deploy-environment.yaml").read_text(encoding="utf-8")

    assert "hashicorp/setup-terraform" not in workflow
    assert 'test "$(command -v terraform)" = "/usr/local/bin/terraform"' in workflow
    assert 'test "$(terraform version -json | jq -r \'.terraform_version\')" = "1.9.8"' in workflow
    assert "docker/setup-buildx-action" not in workflow
    assert '--evidence-directory "$evidence"' in workflow
    assert 'gh attestation verify "oci://$image"' in workflow
    assert "https://ghcr.io/v2/$repository/manifests/$expected_digest" in workflow
    assert "https://mcr.microsoft.com/v2/$repository/manifests/$expected_digest" in workflow
    assert workflow.count('test "$actual_digest" = "$expected_digest"') == 2
    assert "--ghcr-packages-public-verified" in workflow
    assert workflow.index("https://ghcr.io/v2/") < workflow.index("--ghcr-packages-public-verified")
    assert workflow.count('-backend-config="use_oidc=true"') == 2
    assert workflow.count('-backend-config="use_azuread_auth=true"') == 2
    assert "Enforce current Demo-only authorization" in workflow
    assert 'EXPECTED_CALLER_WORKFLOW_REF: ${{ github.repository }}/.github/workflows/deploy-demo.yaml@refs/heads/main' in workflow
    assert 'test "$TARGET_ENVIRONMENT" = "demo"' in workflow
    assert 'case "$APPLY_REQUESTED" in true|false)' in workflow
    assert workflow.index("Enforce current Demo-only authorization") < workflow.index("azure/login@v2")
    assert "Reject stale release before cloud access" in workflow
    assert 'timeframe:"Custom"' in workflow.replace(" ", "")
    assert "Verify bootstrap RBAC and required Azure providers" in workflow
    assert "Microsoft.Network" in workflow
    assert 'require_role "Cost Management Reader"' not in workflow
    assert "Storage Account Contributor" in workflow
    assert "Storage Blob Data Contributor" in workflow
    assert workflow.count("Role Based Access Control Administrator") == 2
    assert "bootstrap-role-assignments.json" in workflow
    assert "subscription-budget.json" in workflow
    assert "actual-cost.json" in workflow
    assert "forecast-cost.json" in workflow
    assert "Exact role topology is independently validated by goal006_bootstrap_oidc.py" in workflow
    assert "self-enumeration cannot see subscription assignments" in workflow
    assert "Bootstrap identity must not have Owner" not in workflow
    assert workflow.index("Verify bootstrap RBAC and required Azure providers") < workflow.index(
        "Verify subscription budget"
    )
    assert workflow.index("Verify bootstrap RBAC and required Azure providers") < workflow.index(
        "Download Demo configuration with OIDC"
    )
    assert "Open temporary state firewall rule" not in workflow
    assert "Close state firewall rule" not in workflow
    assert "network-rule add" not in workflow
    assert "network-rule remove" not in workflow
    assert workflow.index("Verify subscription budget") < workflow.index("Enforce workload cost boundary")
    assert workflow.index("Download Demo configuration with OIDC") < workflow.index(
        "Enforce workload cost boundary"
    )
    assert "WAOOAW_PLATFORM_" not in workflow
    assert "CONFIG_CONTAINER: deployment-config" in workflow
    assert "CONFIG_BLOB: demo/workload-configuration.json" in workflow
    assert "scripts/goal006_storage_download.py" in workflow
    assert "configuration-download-attempts.jsonl" in workflow
    assert "Capture configuration storage diagnostics" in workflow
    assert "if: failure() && steps.configuration.outcome == 'failure'" in workflow
    assert "configuration-storage-diagnostics.json" in workflow
    assert "configuration-container-diagnostics.json" in workflow
    assert "runner_rule_present" not in workflow
    assert "firewall-cleanup.json" not in workflow
    assert 'manifest_digest="sha256:$(sha256sum registry-release-manifest.json' in workflow
    assert "'.manifest_digest = $manifest_digest'" in workflow
    assert "terraform state show \"$resource_address\"" in workflow
    assert "scripts/goal006_execution_gate.py" in workflow
    assert '--execution "$APPLY_REQUESTED"' in workflow
    assert '--state-adopted "$state_adopted"' in workflow
    assert workflow.index("scripts/goal006_execution_gate.py") < workflow.index("terraform import")
    assert "terraform import -input=false -lock-timeout=5m" in workflow
    assert "waooaw-platform-bootstrap" in workflow
    assert "az storage container show" not in workflow
    assert workflow.count('gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main"') == 1
    assert workflow.count("https://api.github.com/repos/$GITHUB_REPOSITORY/git/ref/heads/main") == 3
    assert workflow.count("terraform apply -input=false -auto-approve") == 2
    assert "mcr.microsoft.com/azure-cli@sha256:" in workflow
    assert "https://mcr.microsoft.com/v2/$repository/manifests/$expected_digest" in workflow
    assert workflow.index("https://mcr.microsoft.com/v2/") > workflow.index(
        "Create private digest-pinned credential seeder"
    )
    assert "Create private digest-pinned credential seeder" in workflow
    assert "Run private credential seeder" in workflow
    assert 'args: ["-c", $script]' in workflow
    assert "--yaml secret-seeder-job-definition.json" in workflow
    assert "seeder_args=$(jq" not in workflow
    assert "capture_seeder_evidence()" in workflow
    assert "secret-seeder-job.json" in workflow
    assert "secret-seeder-console.log" in workflow
    assert workflow.index("capture_seeder_evidence()") < workflow.index("Delete private credential seeder")
    assert workflow.count("if: inputs.apply") == 8
    assert "Delete private credential seeder" in workflow
    assert "if: always() && steps.foundation.outcome == 'success'" in workflow
    assert "--key-vault-id '${{ steps.foundation.outputs.key_vault_id }}'" in workflow
    assert workflow.index("terraform apply -input=false -auto-approve foundation.tfplan") < workflow.index(
        "Create private digest-pinned credential seeder"
    )
    assert workflow.index("Run private credential seeder") < workflow.index("Terraform workload plan")
    assert "Roll back disposable Demo workload after apply failure" in workflow
    assert "if: failure() && steps.workload.outcome == 'failure'" in workflow
    assert "terraform destroy -input=false -auto-approve -lock-timeout=5m" in workflow
    assert workflow.index("Terraform workload apply") < workflow.index("Roll back disposable Demo workload after apply failure")
    assert workflow.index("Roll back disposable Demo workload after apply failure") < workflow.index(
        "Delete private credential seeder"
    )
    assert "set -x" not in workflow
    assert "resource_group_record=$(az group show" in workflow
    assert 'tags["managed-by"] == "waooaw-platform-bootstrap"' in workflow
    assert "[?location==" not in workflow
    for apply_command in (
        "terraform apply -input=false -auto-approve foundation.tfplan",
        "terraform apply -input=false -auto-approve workload.tfplan",
    ):
        apply_index = workflow.index(apply_command)
        assert workflow.rfind('test \'${{ inputs.release_sha }}\' = "$latest_main_sha"', 0, apply_index) != -1


def test_deployment_identities_verify_the_active_subscription() -> None:
    deployment = (REPO_ROOT / ".github/workflows/deploy-environment.yaml").read_text(encoding="utf-8")
    verification = (REPO_ROOT / ".github/workflows/post-deploy-verify.yaml").read_text(encoding="utf-8")

    subscription_check = 'test "$(az account show --query id -o tsv)" = "$ARM_SUBSCRIPTION_ID"'
    assert deployment.count(subscription_check) == 2
    assert verification.count(subscription_check) == 1


def test_release_attestation_has_one_bounded_fail_closed_retry() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")

    assert workflow.count("uses: actions/attest-build-provenance@v2") == 3
    assert "id: image-attestation-primary" in workflow
    assert "id: image-attestation-retry" in workflow
    assert "continue-on-error: true" in workflow
    assert "steps.image-attestation-primary.outcome == 'failure'" in workflow
    assert "Back off after transient attestation failure" in workflow
    assert "Retry published image attestation" in workflow
    assert "No successful image attestation bundle was produced" in workflow
    assert "echo \"bundle-path=$bundle_path\"" in workflow
    assert "steps.image-attestation.outputs.bundle-path" in workflow


def test_oidc_workflows_do_not_depend_on_github_platform_identifiers() -> None:
    workflows = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            ".github/workflows/deploy-environment.yaml",
            ".github/workflows/post-deploy-verify.yaml",
            ".github/workflows/reconcile-workload-leases.yaml",
        )
    )
    for variable in (
        "WAOOAW_PLATFORM_AZURE_SUBSCRIPTION_ID",
        "WAOOAW_PLATFORM_AZURE_TENANT_ID",
        "WAOOAW_PLATFORM_BOOTSTRAP_CLIENT_ID",
        "WAOOAW_PLATFORM_TFSTATE_CONTAINER",
        "WAOOAW_PLATFORM_TFSTATE_RESOURCE_GROUP",
        "WAOOAW_PLATFORM_TFSTATE_STORAGE_ACCOUNT",
        "WAOOAW_PLATFORM_TFSTATE_STORAGE_ACCOUNT_ID",
        "WAOOAW_PLATFORM_WORKLOAD_CONFIGURATION",
        "WAOOAW_PLATFORM_DEPLOYMENT_CLIENT_ID",
    ):
        assert variable not in workflows


def test_founder_demo_is_the_only_authorized_deployment_path() -> None:
    demo = (REPO_ROOT / ".github/workflows/deploy-demo.yaml").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github/workflows/promote.yaml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in demo
    assert "Trusted-main exact-six release workflow run ID" not in demo
    assert "Trusted-main exact-six release commit SHA" not in demo
    assert "${{ inputs.release_run_id }}" not in demo
    assert "${{ inputs.release_sha }}" not in demo
    assert "dlai-sd|yk-dlaisd" in demo
    assert '*) echo "Unauthorized Demo dispatcher" >&2; exit 1 ;;' in demo
    assert 'test "$DISPATCH_REF" = "refs/heads/main"' in demo
    assert "actions/workflows/ci.yaml/runs?branch=main&event=push&status=success" in demo
    assert 'artifact_name="goal006-exact-six-release-$latest_main_sha"' in demo
    assert 'test -n "$release_run_id"' in demo
    assert 'test -n "$artifact_id"' in demo
    assert "release_run_id: ${{ fromJSON(needs.authorize-demo.outputs.release_run_id) }}" in demo
    assert "release_sha: ${{ needs.authorize-demo.outputs.release_sha }}" in demo
    assert "environment: demo" in demo
    assert "default: plan" in demo
    assert "- plan" in demo
    assert "- apply" in demo
    assert "case \"$EXECUTION_MODE\" in plan|apply)" in demo
    assert "apply: ${{ inputs.execution == 'apply' }}" in demo
    assert "cost_controls:" in demo
    assert "default: enforce" in demo
    assert "suppress-for-pipeline-build" in demo
    assert 'case "$COST_CONTROLS" in enforce|suppress-for-pipeline-build)' in demo
    assert "enforce_cost_controls: ${{ inputs.cost_controls == 'enforce' }}" in demo
    assert demo.count("if: inputs.execution == 'apply'") == 2
    assert "verification_client_id: ${{ needs.deploy-demo.outputs.verification_client_id }}" in demo
    assert "web_url: ${{ needs.deploy-demo.outputs.web_url }}" in demo
    assert "environment: uat" not in demo
    assert "environment: prod" not in demo
    assert "UAT remains prohibited until explicit Founder acceptance" in workflow
    assert "exit 1" in workflow
    assert "uses: ./.github/workflows/deploy-environment.yaml" not in workflow

    verification = (REPO_ROOT / ".github/workflows/post-deploy-verify.yaml").read_text(encoding="utf-8")
    assert "Reject stale release before independent verification" in verification
    assert 'test "$RELEASE_SHA" = "$latest_main_sha"' in verification
    assert verification.index("Reject stale release before independent verification") < verification.index(
        "azure/login@v2"
    )
    assert "ARM_CLIENT_ID: ${{ inputs.verification_client_id }}" in verification
    assert "WAOOAW_PLATFORM_VERIFICATION_CLIENT_ID" not in verification
    assert 'test "$TARGET_ENVIRONMENT" = "demo"' in verification
    assert "Verify returned Web URL binds to the deployed revision" in verification
    assert "Verify active healthy revisions" in verification
    assert "Run internal functional verification" in verification
    assert "functional-verification.json" in verification

    delivery_surfaces = [
        REPO_ROOT / ".github/workflows/deploy-environment.yaml",
        REPO_ROOT / ".github/workflows/post-deploy-verify.yaml",
        REPO_ROOT / ".github/workflows/promote.yaml",
        REPO_ROOT / ".github/workflows/reconcile-workload-leases.yaml",
        REPO_ROOT / "scripts/build_goal006_release_images.sh",
    ]
    for path in delivery_surfaces:
        assert "GOAL006_" not in path.read_text(encoding="utf-8"), path.relative_to(REPO_ROOT)


def test_edge_and_break_glass_policies_are_fail_closed() -> None:
    edge = json.loads(read_contract("policies/edge-policy.json"))
    break_glass = json.loads(read_contract("policies/break-glass-authority.json"))

    assert edge["product_selection"] == "UNRESOLVED_PROTECTED_DECISION"
    assert edge["emergency_stop"] == {
        "challenge_exempt": True,
        "quota_exempt": True,
        "commercial_limit_exempt": True,
        "latency_floor_milliseconds": 250,
    }
    assert "direct-container-endpoint" in edge["blocking_controls"]
    assert break_glass["constraints"]["approval_separate_from_execution"] is True
    assert break_glass["constraints"]["automatic_expiry"] is True
    assert break_glass["production_actors"] == "UNRESOLVED_FOUNDER_DECISION"


def test_phase2_surface_contains_no_provider_execution_or_secret_values() -> None:
    contracts = list(PHASE2_ROOT.rglob("*.tf"))
    assert contracts

    forbidden = (
        "az login",
        "ARM_CLIENT_SECRET",
        "AZURE_CREDENTIALS",
        'default = "password"',
        'default = "secret"',
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in contracts)
    for token in forbidden:
        assert token.lower() not in combined.lower()