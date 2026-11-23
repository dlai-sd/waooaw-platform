# Implements: adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 2; work-contracts/WC-159-synthetic-tenant-support.md WC159-R011, WC159-R012
# Constitutional basis: C-059 (Implementation Traceability), C-065 (Separation of Duties)
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION = ROOT / "infrastructure/terraform/phase2/modules/foundation"
FRAGMENT = ROOT / "infrastructure/keycloak/acceptance-provisioner.realm-fragment.json"
PROFILE = ROOT / "validation/acceptance/environments/demo.yaml"


def _foundation() -> str:
    return (FOUNDATION / "main.tf").read_text(encoding="utf-8")


def test_acceptance_identity_is_federated_to_main_only_and_off_by_default() -> None:
    main = _foundation()
    variables = (FOUNDATION / "variables.tf").read_text(encoding="utf-8")
    block = main.split('resource "azurerm_federated_identity_credential" "acceptance"', 1)[1].split("\n}\n", 1)[0]
    assert 'subject             = "repo:${var.repository_id}:ref:refs/heads/main"' in block
    assert "count               = var.acceptance_enabled ? 1 : 0" in block
    enabled = variables.split('variable "acceptance_enabled"', 1)[1].split("\n}\n", 1)[0]
    assert "default     = false" in enabled
    assert 'contains(["demo", "uat"], var.environment)' in enabled


def test_acceptance_identity_holds_only_read_roles_on_exact_scopes() -> None:
    main = _foundation()
    assignments = main.split('resource "azurerm_role_assignment" ')[1:]
    own = [block.split("\n}\n", 1)[0] for block in assignments if "azurerm_user_assigned_identity.acceptance[0].principal_id" in block]
    roles = [re.search(r'role_definition_name = "([^"]+)"', block).group(1) for block in own]  # type: ignore[union-attr]
    assert sorted(roles) == ["Key Vault Secrets User", "Monitoring Reader", "Reader"]
    reader = next(block for block in own if "acceptance_secret_reader" in block)
    assert 'scope                = "${var.acceptance_vault_enabled ? azurerm_key_vault.acceptance[0].id : azurerm_key_vault.environment.id}/secrets/${each.value}"' in reader
    for forbidden in ("Contributor", "Owner", "User Access Administrator", "Officer", "Administrator"):
        assert not any(forbidden in role for role in roles)


def test_environment_roots_list_exactly_the_secrets_the_profile_reads_and_keep_the_identity_off() -> None:
    wanted = sorted(item["name"] for item in yaml.safe_load(PROFILE.read_text(encoding="utf-8"))["secrets"])
    for environment in ("demo", "uat"):
        root = (ROOT / f"infrastructure/terraform/phase2/environments/{environment}/foundation/main.tf").read_text(encoding="utf-8")
        assert "acceptance_enabled = false" in root
        listed = re.search(r"acceptance_secret_names = \[(.*?)\]", root, re.DOTALL)
        assert listed is not None
        assert sorted(re.findall(r'"([^"]+)"', listed.group(1))) == wanted
    prod = (ROOT / "infrastructure/terraform/phase2/environments/prod/foundation/main.tf").read_text(encoding="utf-8")
    assert "acceptance" not in prod


def test_provisioning_client_holds_only_user_management_event_reading_and_the_marker_role() -> None:
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment["environments"] == ["demo", "uat"]
    client = fragment["clients"][0]
    assert client["clientId"] == "waooaw-acceptance-provisioner"
    assert client["serviceAccountsEnabled"] is True
    assert not any(client[flag] for flag in ("publicClient", "standardFlowEnabled", "implicitFlowEnabled", "directAccessGrantsEnabled", "fullScopeAllowed"))
    roles = sorted(mapper["config"]["role"] for mapper in client["protocolMappers"] if mapper["protocolMapper"] == "oidc-hardcoded-role-mapper")
    assert roles == ["acceptance-provisioner", "realm-management.manage-users", "realm-management.view-events"]
    audience = [mapper for mapper in client["protocolMappers"] if mapper["protocolMapper"] == "oidc-audience-mapper"]
    assert audience[0]["config"]["included.client.audience"] == "waooaw-platform"
    account = fragment["serviceAccountUsers"][0]
    assert account["clientRoles"] == {"realm-management": ["manage-users", "view-events"]}
    assert account["realmRoles"] == ["acceptance-provisioner"]
    assert fragment["realm"]["adminEventsEnabled"] is True
    assert [group["name"] for group in fragment["realm"]["groups"]] == ["synthetic"]
    assert "${ACCEPTANCE_PROVISIONER_CLIENT_SECRET}" == client["secret"]


def test_the_realm_role_is_never_a_default_or_customer_requestable_role() -> None:
    realm = json.loads((ROOT / "infrastructure/keycloak/waooaw-realm.json").read_text(encoding="utf-8"))
    assert "acceptance-provisioner" not in json.dumps(realm)


def test_trace_export_is_wired_only_for_three_services_and_stays_off_by_default() -> None:
    workload = ROOT / "infrastructure/terraform/phase2/modules/workload"
    variables = (workload / "variables.tf").read_text(encoding="utf-8")
    declared = variables.split('variable "otlp_endpoint"', 1)[1].split("\n}\n", 1)[0]
    assert "default     = null" in declared
    assert "var.otlp_endpoint == null ||" in declared
    main = (workload / "main.tf").read_text(encoding="utf-8")
    block = main.split('name  = "OTEL_EXPORTER_OTLP_ENDPOINT"', 1)[0].rsplit('dynamic "env"', 1)[1]
    assert 'var.otlp_endpoint != null && contains(["business-platform", "billing-engine", "web"], each.key)' in block
    for environment in ("demo", "uat", "prod"):
        root = (ROOT / f"infrastructure/terraform/phase2/environments/{environment}/workload/main.tf").read_text(encoding="utf-8")
        assert "otlp_endpoint" not in root


def test_the_acceptance_vault_is_separate_off_by_default_and_read_by_the_acceptance_identity_only() -> None:
    main = _foundation()
    variables = (FOUNDATION / "variables.tf").read_text(encoding="utf-8")
    enabled = variables.split('variable "acceptance_vault_enabled"', 1)[1].split("\n}\n", 1)[0]
    assert "default     = false" in enabled
    assert "var.acceptance_enabled" in enabled and 'contains(["demo", "uat"], var.environment)' in enabled
    vault = main.split('resource "azurerm_key_vault" "acceptance"', 1)[1].split("\n}\n", 1)[0]
    assert 'name                          = "kv-${local.name}-acc"' in vault
    assert "enable_rbac_authorization     = true" in vault and "purge_protection_enabled      = true" in vault
    assert "count                         = var.acceptance_vault_enabled ? 1 : 0" in vault
    reader = main.split('resource "azurerm_role_assignment" "acceptance_secret_reader"', 1)[1].split("\n}\n", 1)[0]
    assert "azurerm_key_vault.acceptance[0].id" in reader
    officer = main.split('resource "azurerm_role_assignment" "acceptance_vault_officer"', 1)[1].split("\n}\n", 1)[0]
    assert 'role_definition_name = "Key Vault Secrets Officer"' in officer and "azurerm_key_vault.acceptance[0].id" in officer
    for environment in ("demo", "uat"):
        root = (ROOT / f"infrastructure/terraform/phase2/environments/{environment}/foundation/main.tf").read_text(encoding="utf-8")
        assert "acceptance_vault_enabled         = false" in root
        assert "acceptance_vault_secret_officers = []" in root


def test_the_profile_reads_the_dedicated_vault_the_module_would_create() -> None:
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    assert profile["azure"]["key_vault"] == "kv-waooaw-demo-acc"
    assert profile["azure"]["key_vault"] != "kv-waooaw-demo"


def test_every_profile_secret_is_in_the_runbook_register() -> None:
    runbook = (ROOT / "architecture/reference/runbooks/acceptance-sandbox-setup.md").read_text(encoding="utf-8")
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    for item in profile["secrets"]:
        if item["name"].startswith("acceptance-"):
            assert f"`{item['name']}`" in runbook
