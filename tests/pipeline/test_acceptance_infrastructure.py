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
    acceptance = main[main.index('resource "azurerm_user_assigned_identity" "acceptance"') :]
    roles = re.findall(r'role_definition_name = "([^"]+)"', acceptance)
    assert sorted(roles) == ["Key Vault Secrets User", "Monitoring Reader", "Reader"]
    reader = acceptance.split('resource "azurerm_role_assignment" "acceptance_secret_reader"', 1)[1].split("\n}\n", 1)[0]
    assert 'scope                = "${azurerm_key_vault.environment.id}/secrets/${each.value}"' in reader
    for forbidden in ("Contributor", "Owner", "User Access Administrator", "Officer", "Administrator"):
        assert forbidden not in acceptance


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
