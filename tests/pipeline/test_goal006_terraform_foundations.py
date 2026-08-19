"""Offline contracts for GOAL-006 P2-WC03 Terraform foundations."""

from __future__ import annotations

import re
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
PHASE2_ROOT = REPO_ROOT / "infrastructure" / "terraform" / "phase2"
ENVIRONMENTS = ("demo", "uat", "prod")
PRIVATE_MEMBERS = ("constitutional-engine", "ai-runtime", "billing-engine")
PUBLIC_CANDIDATES = ("web", "business-platform", "professional-runtime")


def read_contract(relative_path: str) -> str:
    path = PHASE2_ROOT / relative_path
    assert path.is_file(), f"missing P2-WC03 contract: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


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
        assert "client_secret" not in contract.lower()


def test_foundation_and_workload_have_distinct_owners() -> None:
    assert not list((PHASE2_ROOT / "modules" / "environment").glob("*.tf"))
    for environment in ENVIRONMENTS:
        foundation = read_contract(f"environments/{environment}/foundation/main.tf")
        workload = read_contract(f"environments/{environment}/workload/main.tf")
        assert 'module "workload"' not in foundation
        assert 'module "foundation"' not in workload
        assert 'data "terraform_remote_state" "foundation"' in workload


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


def test_each_release_member_has_its_own_identity_and_secret_scope() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert 'resource "azurerm_user_assigned_identity" "member"' in contract
    assert 'resource "azurerm_role_assignment" "member_secret"' in contract
    assert "azurerm_user_assigned_identity.member[each.key].id" in contract
    assert "scope                = var.key_vault_secret_ids[each.key]" in contract
    assert "runtime_identity_id" not in contract
    assert "runtime_identity_client_id" not in contract


def test_deployment_identity_is_environment_scoped_for_resources_and_rbac() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert contract.count("scope                = azurerm_resource_group.environment.id") == 3
    assert 'role_definition_name = "Contributor"' in contract
    assert 'role_definition_name = "Role Based Access Control Administrator"' in contract
    assert "azurerm_user_assigned_identity.deployment.principal_id" in contract
    assert 'output "deployment_client_id"' in contract
    assert 'role_definition_name = "Reader"' in contract
    assert "azurerm_user_assigned_identity.verification.principal_id" in contract
    assert 'output "verification_client_id"' in contract


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
        assert "ghcr_packages_public         = var.ghcr_packages_public" in root
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
    assert "internal_load_balancer_enabled = true" in contract


def test_network_egress_is_explicitly_fail_closed() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert contract.count('name                       = "deny-unapproved-egress"') == 2
    assert contract.count('priority                   = 4096') == 2
    assert contract.count('direction                  = "Outbound"') == 3
    assert contract.count('access                     = "Deny"') == 2
    assert 'destination_address_prefix = "VirtualNetwork"' in contract
    assert 'destination_address_prefix = "Internet"' not in contract


def test_scale_contract_is_bounded_and_defaults_to_zero() -> None:
    contract = read_contract("modules/workload/variables.tf")
    prod_root = read_contract("environments/prod/workload/main.tf")
    prod_variables = read_contract("environments/prod/workload/variables.tf")

    assert contract.count("default = 0") == 2
    assert "var.max_replicas > 0 && var.max_replicas <= 10" in contract
    uat_root = read_contract("environments/uat/workload/main.tf")
    assert "ce_min_replicas              = 0" in uat_root
    assert "pr_min_replicas              = 0" in uat_root
    assert "ce_min_replicas              = var.ce_min_replicas" in prod_root
    assert "pr_min_replicas              = var.pr_min_replicas" in prod_root
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
    assert "timecmp(var.expires_at, timestamp()) > 0" in contract
    assert 'output "workload_enabled"' in contract

    for environment in ("demo", "uat"):
        workload = read_contract(f"environments/{environment}/workload/main.tf")
        assert 'module "lease"' in workload
        assert "workload_enabled             = module.lease.workload_enabled" in workload
    assert 'module "lease"' not in read_contract("environments/prod/workload/main.tf")


def test_expired_leases_are_reconciled_by_deletion_only_nonproduction_workflow() -> None:
    workflow = (REPO_ROOT / ".github/workflows/reconcile-workload-leases.yaml").read_text(encoding="utf-8")
    validator = (REPO_ROOT / "scripts/goal006_lease_reconciliation.py").read_text(encoding="utf-8")

    assert "cron: '7 * * * *'" in workflow
    assert "environment: [demo, uat]" in workflow
    assert "environment: [demo, uat, prod]" not in workflow
    assert "lease_reconciliation_inputs" in workflow
    assert "reconciliation-plan.json" in workflow
    assert workflow.index("--plan reconciliation-plan.json") < workflow.index("terraform apply")
    assert "PRODUCTION_RECONCILIATION_PROHIBITED" in validator
    assert "DISPOSABLE_PREFIXES" in validator


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
    assert policy["allowed_workflows"] == [".github/workflows/promote.yaml@refs/heads/main"]
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

    assert "hashicorp/setup-terraform@v3" in workflow
    assert "terraform_version: 1.9.8" in workflow
    assert "docker/setup-buildx-action@v3" in workflow
    assert '--evidence-directory "$evidence"' in workflow
    assert 'gh attestation verify "oci://$image"' in workflow
    assert 'docker buildx imagetools inspect "$image"' in workflow
    assert "--ghcr-packages-public-verified" in workflow
    assert workflow.index("docker buildx imagetools inspect") < workflow.index("--ghcr-packages-public-verified")
    assert workflow.count('-backend-config="use_oidc=true"') == 2
    assert workflow.count('-backend-config="use_azuread_auth=true"') == 2
    assert "Enforce caller and Production plan-only boundary" in workflow
    assert 'EXPECTED_CALLER_WORKFLOW_REF: ${{ github.repository }}/.github/workflows/promote.yaml@refs/heads/main' in workflow
    assert '[[ "$TARGET_ENVIRONMENT" == "prod" && "$APPLY_REQUESTED" == "true" ]]' in workflow
    assert workflow.index("Enforce caller and Production plan-only boundary") < workflow.index("azure/login@v2")
    assert "Reject stale release before cloud access" in workflow
    assert workflow.count('gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main"') == 3
    assert workflow.count("terraform apply -input=false -auto-approve") == 2
    for apply_command in (
        "terraform apply -input=false -auto-approve foundation.tfplan",
        "terraform apply -input=false -auto-approve workload.tfplan",
    ):
        apply_index = workflow.index(apply_command)
        assert workflow.rfind('test \'${{ inputs.release_sha }}\' = "$latest_main_sha"', 0, apply_index) != -1


def test_promotion_requires_explicit_readiness_enablement_and_keeps_production_plan_only() -> None:
    workflow = (REPO_ROOT / ".github/workflows/promote.yaml").read_text(encoding="utf-8")

    assert "vars.GOAL006_PROMOTION_ENABLED == 'true'" in workflow
    assert "Reject stale or non-main release" in workflow
    assert 'gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main"' in workflow
    assert 'test "$RELEASE_SHA" = "$latest_main_sha"' in workflow
    assert "cancel-in-progress: true" in workflow
    assert workflow.count('gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main"') == 3
    assert "environment: demo-acceptance" in workflow
    assert "environment: uat-acceptance" in workflow
    assert "GOAL006_DEMO_ACCEPTED_RELEASE_RUN_ID" in workflow
    assert "GOAL006_DEMO_ACCEPTED_RELEASE_SHA" in workflow
    assert "GOAL006_DEMO_ACCEPTANCE_EVIDENCE_SHA256" in workflow
    assert "GOAL006_UAT_ACCEPTED_RELEASE_RUN_ID" in workflow
    assert "GOAL006_UAT_ACCEPTED_RELEASE_SHA" in workflow
    assert "GOAL006_UAT_ACCEPTANCE_EVIDENCE_SHA256" in workflow
    assert "needs: accept-demo" in workflow
    assert "needs: accept-uat" in workflow
    assert "environment: prod" in workflow
    assert "apply: false" in workflow

    verification = (REPO_ROOT / ".github/workflows/post-deploy-verify.yaml").read_text(encoding="utf-8")
    assert "Reject stale release before independent verification" in verification
    assert 'test "$RELEASE_SHA" = "$latest_main_sha"' in verification
    assert verification.index("Reject stale release before independent verification") < verification.index(
        "azure/login@v2"
    )


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