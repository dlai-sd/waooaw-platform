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
    assert f'key = "goal006/{environment}/foundation.tfstate"' in workload
    assert re.search(rf'environment\s*=\s*"{environment}"', foundation)
    assert 'source                 = "../../../modules/foundation"' in foundation
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
    assert "for_each = local.release_members" in contract
    assert "azurerm_user_assigned_identity.member[each.key].id" in contract
    assert "scope                = var.key_vault_secret_ids[each.key]" in contract
    assert "runtime_identity_id" not in contract
    assert "runtime_identity_client_id" not in contract


def test_foundation_is_private_isolated_and_environment_scoped() -> None:
    contract = read_contract("modules/foundation/main.tf")

    for cidr in ("10.60.0.0/16", "10.61.0.0/16", "10.62.0.0/16"):
        assert cidr in contract
    assert re.search(
        r'subject\s*=\s*"repo:\$\{var\.repository_id\}:environment:\$\{var\.repository_environment\}"',
        contract,
    )
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


def test_oidc_policy_requires_exact_governed_refs_and_workflows() -> None:
    policy = json.loads(read_contract("policies/oidc-trust-policy.json"))

    assert policy["repository"] == "dlai-sd/waooaw-platform"
    assert policy["allowed_environments"] == ["demo", "uat", "prod"]
    assert policy["allowed_refs"] == ["refs/heads/main"]
    assert policy["allowed_workflows"] == [
        ".github/workflows/promote.yaml",
        ".github/workflows/post-deploy-verify.yaml",
    ]
    assert policy["wildcards_allowed"] is False
    assert all("*" not in value for value in (*policy["allowed_refs"], *policy["allowed_workflows"]))
    assert policy["enforcement_stage"] == "P2-WC06_WORKFLOW_GATE"


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