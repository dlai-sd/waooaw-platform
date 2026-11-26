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
        assert f"acceptance_enabled = {'true' if environment == 'demo' else 'false'}" in root
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
    profile = {attribute["name"]: attribute for attribute in fragment["realm"]["userProfile"]["attributes"]}
    # The only attribute a customer cannot see or edit is the one that becomes the idp claim.
    assert profile["synthetic_idp"]["permissions"] == {"view": ["admin"], "edit": ["admin"]}
    assert profile["synthetic_idp"]["validations"]["options"]["options"] == ["google", "facebook"]
    assert {"username", "email", "firstName", "lastName"} <= set(profile)
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
    uat = (ROOT / "infrastructure/terraform/phase2/environments/uat/foundation/main.tf").read_text(encoding="utf-8")
    assert "acceptance_vault_enabled         = false" in uat
    assert "acceptance_vault_secret_officers = []" in uat
    demo = (ROOT / "infrastructure/terraform/phase2/environments/demo/foundation/main.tf").read_text(encoding="utf-8")
    assert "acceptance_vault_enabled         = true" in demo
    officers = re.search(r"acceptance_vault_secret_officers = \[(.*?)\]", demo, re.DOTALL)
    assert officers is not None
    assert re.fullmatch(r'"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}"', officers.group(1).strip())


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


SEED = ROOT / "scripts/acceptance_seed_secrets.sh"
STUB_DOCKER = """#!/usr/bin/env bash
# Records every call; stdin is saved so a test can prove a value never appears in the arguments.
log="$STUB_DIR/calls.log"
printf '%s\\n' "$*" >> "$log"
case "$*" in
  *"secret show"*) case "$*" in *"$STUB_EXISTING"*) echo id; exit 0 ;; *) exit 1 ;; esac ;;
  *"secret set"*) cat >> "$STUB_DIR/stdin.log"; echo >> "$STUB_DIR/stdin.log" ;;
  *"secret list"*) echo acceptance-meta-app-id ;;
  *) cat > /dev/null ;;
esac
"""


def _run_seed(tmp_path: Path, content: str, *args: str, existing: str = "none-such") -> tuple[int, str, str, Path]:
    import os
    import subprocess

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(STUB_DOCKER, encoding="utf-8")
    docker.chmod(0o755)
    secrets = tmp_path / "secrets.env"
    secrets.write_text(content, encoding="utf-8")
    secrets.chmod(0o600)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "STUB_DIR": str(tmp_path),
        "STUB_EXISTING": existing,
        "ACCEPTANCE_SECRETS_FILE": str(secrets),
        "ACCEPTANCE_AZ_CONFIG": str(tmp_path / "azcfg"),
    }
    done = subprocess.run(["bash", str(SEED), "seed", *args], env=env, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr, secrets, tmp_path


def test_the_seed_script_covers_exactly_the_profile_secrets_except_the_keycloak_one() -> None:
    text = SEED.read_text(encoding="utf-8")
    pairs = re.findall(r"^(ACCEPTANCE_[A-Z_]+)=([a-z0-9-]+)$", text, re.MULTILINE)
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))["secrets"]
    expected = {item["env"]: item["name"] for item in profile if item["name"] != "acceptance-keycloak-provisioner-client-secret"}
    assert dict(pairs) == expected
    assert 'VAULT="${ACCEPTANCE_VAULT:-kv-waooaw-demo-acc}"' in text


def test_the_seed_script_stores_values_through_stdin_only_and_deletes_the_file(tmp_path: Path) -> None:
    secret = "".join(["unit", "-test", "-value", "-123"])
    code, output, secrets, base = _run_seed(tmp_path, f"ACCEPTANCE_META_APP_ID={secret}\nACCEPTANCE_META_APP_SECRET=\n")
    assert code == 0, output
    assert secret not in output
    assert secret not in (base / "calls.log").read_text(encoding="utf-8")
    assert secret in (base / "stdin.log").read_text(encoding="utf-8")
    assert "stored acceptance-meta-app-id" in output and "skip   acceptance-meta-app-secret" in output
    assert not secrets.exists()


def test_the_seed_script_keeps_existing_secrets_unless_told_and_rejects_live_razorpay_keys(tmp_path: Path) -> None:
    code, output, secrets, base = _run_seed(tmp_path, "ACCEPTANCE_META_APP_ID=x\n", existing="acceptance-meta-app-id")
    assert code == 0, output
    assert "exists acceptance-meta-app-id" in output and not (base / "stdin.log").exists()

    other = tmp_path / "live"
    other.mkdir()
    code, output, secrets, base = _run_seed(other, "ACCEPTANCE_RAZORPAY_KEY_ID=" + "rzp_" + "live_x\n")
    assert code == 1 and "rzp_test_" in output
    assert secrets.exists() and not (base / "stdin.log").exists()


def test_the_seed_script_refuses_unknown_keys_and_a_world_readable_file(tmp_path: Path) -> None:
    code, output, secrets, _ = _run_seed(tmp_path, "SOMETHING_ELSE=1\n")
    assert code == 1 and "Unknown key SOMETHING_ELSE" in output and secrets.exists()

    secrets.chmod(0o644)
    import os
    import subprocess

    env = {**os.environ, "ACCEPTANCE_SECRETS_FILE": str(secrets)}
    done = subprocess.run(["bash", str(SEED), "seed"], env=env, capture_output=True, text=True, check=False)
    assert done.returncode == 2 and "readable by others" in done.stderr


def test_the_keycloak_secret_is_generated_unseen_through_stdin_and_kept_when_present(tmp_path: Path) -> None:
    import os
    import subprocess

    def run(base: Path, existing: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        base.mkdir()
        bin_dir = base / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(STUB_DOCKER, encoding="utf-8")
        docker.chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "STUB_DIR": str(base), "STUB_EXISTING": existing}
        return subprocess.run(["bash", str(SEED), "keycloak-secret"], env=env, capture_output=True, text=True, check=False), base

    done, base = run(tmp_path / "new", "none-such")
    assert done.returncode == 0 and "stored acceptance-keycloak-provisioner-client-secret" in done.stdout
    value = (base / "stdin.log").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"[A-Za-z0-9]{48}", value)
    assert value not in done.stdout + done.stderr and value not in (base / "calls.log").read_text(encoding="utf-8")

    done, base = run(tmp_path / "kept", "acceptance-keycloak-provisioner-client-secret")
    assert done.returncode == 0 and "exists acceptance-keycloak-provisioner-client-secret" in done.stdout
    assert not (base / "stdin.log").exists()


WORKLOAD = ROOT / "infrastructure/terraform/phase2/modules/workload"


def test_the_realm_gains_the_provisioning_client_only_when_the_demo_only_flag_is_on() -> None:
    variables = (WORKLOAD / "acceptance-provisioner.tf").read_text(encoding="utf-8")
    assert 'condition     = !var.acceptance_provisioner_enabled || var.environment == "demo"' in variables
    assert "default     = false" in variables.split('variable "acceptance_key_vault_id"', 1)[0]
    assert "acceptance-provisioner.realm-fragment.json" in variables
    main = (WORKLOAD / "main.tf").read_text(encoding="utf-8")
    assert "keycloak_realm = merge({" in main and "}, local.acceptance_provisioner_realm_settings)" in main
    assert "local.acceptance_provisioner_clients)" in main and "local.acceptance_provisioner_users)" in main
    assert "], local.acceptance_provisioner_realm_roles)" in main
    assert "    local.acceptance_provisioner_secret,\n  )" in main
    assert 'replace_secret ACCEPTANCE_PROVISIONER_CLIENT_SECRET \\"$ACCEPTANCE_PROVISIONER_CLIENT_SECRET\\"' in main
    assert 'local.acceptance_provisioner_secret_name = "acceptance-keycloak-provisioner-client-secret"'.replace("local.", "") in variables


def test_the_provisioning_client_secret_is_read_from_the_acceptance_vault_by_the_migration_job_only() -> None:
    variables = (WORKLOAD / "acceptance-provisioner.tf").read_text(encoding="utf-8")
    assert '"${var.acceptance_key_vault_id}/secrets/${local.acceptance_provisioner_secret_name}"' in variables
    for environment in ("uat", "prod"):
        root = (ROOT / f"infrastructure/terraform/phase2/environments/{environment}/workload/main.tf").read_text(encoding="utf-8")
        assert "acceptance_provisioner_enabled" not in root
    demo = (ROOT / "infrastructure/terraform/phase2/environments/demo/workload/main.tf").read_text(encoding="utf-8")
    assert "outputs.acceptance_key_vault_id" in demo and "outputs.acceptance_key_vault_uri" in demo
    assert "  acceptance_provisioner_enabled           = true\n" in demo
