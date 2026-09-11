# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §§4-5, 9-11
# Constitutional basis: C-023, C-059, C-063, C-080

import copy
import json
import os
import re
import subprocess
import sys

import pytest

from scripts import wc091_environment, wc091_readiness, wc091_secret_provision


def test_demo_render_is_deterministic_secret_free_and_environment_bound() -> None:
    first = wc091_environment.validate_and_render("demo")
    second = wc091_environment.validate_and_render("demo")

    assert first == second
    assert first["renderDigest"].startswith("sha256:")
    assert first["configuration"]["environment"] == "demo"
    assert all(binding["reference"].startswith("kv://kv-waooaw-demo/secrets/") for binding in first["secretBindings"])
    assert "clientSecret" not in json.dumps(first)


def test_checked_in_demo_render_is_current_and_consumed_by_terraform() -> None:
    rendered = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/demo.rendered.json").read_text())
    identity_module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/identity.tf").read_text()

    assert rendered == wc091_environment.validate_and_render("demo")
    assert "environment-readiness/demo.rendered.json" in identity_module


def test_unknown_manifest_field_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    original = wc091_environment._load

    def load_with_unknown(path):
        value = original(path)
        if path.name == "demo.json":
            value = copy.deepcopy(value)
            value["unexpected"] = True
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_with_unknown)
    with pytest.raises(wc091_environment.ContractError, match="Additional properties"):
        wc091_environment.validate_and_render("demo")


def test_unknown_nested_manifest_field_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    original = wc091_environment._load

    def load_with_unknown(path):
        value = original(path)
        if path.name == "demo.json":
            value = copy.deepcopy(value)
            value["keycloak"]["unexpected"] = True
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_with_unknown)
    with pytest.raises(wc091_environment.ContractError, match="Additional properties"):
        wc091_environment.validate_and_render("demo")


def test_prod_manifest_rejects_demo_host(monkeypatch: pytest.MonkeyPatch) -> None:
    original = wc091_environment._load

    def load_with_demo_host(path):
        value = original(path)
        if path.name == "prod.json":
            value = copy.deepcopy(value)
            value["origins"]["api"] = "https://api.demo.waooaw.com"
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_with_demo_host)
    with pytest.raises(wc091_environment.ContractError, match="another environment"):
        wc091_environment.validate_and_render("prod")


def test_enabled_provider_requires_declared_environment_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    original = wc091_environment._load

    def load_with_unknown_reference(path):
        value = original(path)
        if path.name == "demo.json":
            value = copy.deepcopy(value)
            value["providers"][0]["secretReference"] = "kv://kv-waooaw-demo/secrets/undeclared"
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_with_unknown_reference)
    with pytest.raises(wc091_environment.ContractError, match="no declared environment secret"):
        wc091_environment.validate_and_render("demo")


def test_catalog_rejects_duplicate_secret_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    original = wc091_environment._load

    def load_with_duplicate(path):
        value = original(path)
        if path.name == "secret-catalog.json":
            value = copy.deepcopy(value)
            value["entries"].append(copy.deepcopy(value["entries"][0]))
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_with_duplicate)
    with pytest.raises(wc091_environment.ContractError, match="must be unique"):
        wc091_environment.validate_and_render("demo")


def test_demo_terraform_uses_generation_fenced_emptydir_storage() -> None:
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    demo = (wc091_environment.ROOT / "infrastructure/terraform/phase2/environments/demo/workload/main.tf").read_text()

    assert module.count('storage_type = "EmptyDir"') == 3
    assert 'path = "/var/lib/postgresql/data"' in module
    assert 'path = "/opt/keycloak/data"' in module
    assert module.count("rm -rf /var/lib/postgresql/data/*") == 2
    assert "rm -rf /opt/keycloak/data/*" in module
    assert "wc091_demo_generation" in module
    assert "WC091_GENERATION_ID" in module
    assert "WC091_FIXTURE_DIGEST" in module
    assert 'name        = "Identity__Hmac__Key"' in module
    assert 'name  = "Identity__Hmac__ActiveVersion"' in module
    assert "demo_data_generation_id                  = var.manifest_digest" in demo
    assert 'filesha256("../../../../../environment-readiness/demo.rendered.json")' in demo


def test_demo_deployment_provisions_and_orders_every_hmac_secret_dependency() -> None:
    catalog = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    workflow = (wc091_environment.ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    hmac_secret = next(entry["vaultSecretName"] for entry in catalog["entries"] if entry["id"] == "identity-hmac-active")
    inventory = re.search(r'^\s*credential_names="([^"]+)"$', workflow, re.MULTILINE)
    seeder = re.search(r"seeder_script='.*?for name in ([^;]+); do", workflow)

    assert inventory is not None and hmac_secret in inventory.group(1).split()
    assert seeder is not None and hmac_secret in seeder.group(1).split()
    assert (
        "azurerm_role_assignment.identity_hmac_secret" in module.split('resource "azurerm_container_app" "member"', maxsplit=1)[1]
    )
    assert 'scripts/goal006_keyvault_retry.py"' in workflow


def test_private_deployment_seeder_creates_missing_hmac_secret(tmp_path) -> None:
    workflow = (wc091_environment.ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    seeder = re.search(r"^\s*seeder_script='(.*)'$", workflow, re.MULTILINE)
    assert seeder is not None

    fake_az = tmp_path / "az"
    fake_az.write_text(
        """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_AZ_LOG"
name=
previous=
for argument in "$@"; do
    if [ "$previous" = "--name" ]; then name=$argument; fi
    previous=$argument
done
if [ "$1" = "login" ]; then exit 0; fi
if [ "$1 $2 $3" = "keyvault secret show" ]; then
    if [ "$name" = "identity-hmac-active" ]; then
        echo SecretNotFound >&2
        exit 3
    fi
    printf '%s\\n' '{"attributes":{"enabled":true}}'
    exit 0
fi
exit 0
"""
    )
    fake_az.chmod(0o755)
    fake_jq = tmp_path / "jq"
    fake_jq.write_text("#!/bin/sh\ncat >/dev/null\nprintf 'true\\n'\n")
    fake_jq.chmod(0o755)
    az_log = tmp_path / "az.log"
    environment = os.environ | {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_AZ_LOG": str(az_log),
        "AZURE_CLIENT_ID": "synthetic-client",
        "CREDENTIAL_SCHEMA": "synthetic-schema",
        "KEY_VAULT_NAME": "synthetic-vault",
    }

    result = subprocess.run(
        ["/bin/sh", "-c", seeder.group(1)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert "credential_status name=business-platform status=preserved" in result.stdout
    assert "credential_status name=identity-hmac-active status=created" in result.stdout
    assert "keyvault secret set --vault-name synthetic-vault --name identity-hmac-active" in az_log.read_text()


@pytest.mark.parametrize(
    ("apply_log", "inventory", "expected"),
    [
        (
            "Unable to get value using Managed identity for secret identity-hmac-active",
            {"credentials": [{"name": "identity-hmac-active"}]},
            True,
        ),
        (
            "Unable to get value using Managed identity for secret undeclared-secret",
            {"credentials": [{"name": "identity-hmac-active"}]},
            False,
        ),
        (
            "Updating ca-demo-web: Unable to get value using Managed identity for secret undeclared-secret",
            {"credentials": [{"name": "web"}]},
            False,
        ),
        (
            "Terraform provider failed while updating identity-hmac-active",
            {"credentials": [{"name": "identity-hmac-active"}]},
            False,
        ),
        ("Unable to get value using Managed identity", {"credentials": "invalid"}, False),
    ],
)
def test_keyvault_retry_classifier_fails_closed(tmp_path, apply_log: str, inventory: object, expected: bool) -> None:
    apply_log_path = tmp_path / "workload-apply.log"
    inventory_path = tmp_path / "credential-inventory.json"
    apply_log_path.write_text(apply_log)
    inventory_path.write_text(json.dumps(inventory))

    result = subprocess.run(
        [
            sys.executable,
            str(wc091_environment.ROOT / "scripts/goal006_keyvault_retry.py"),
            "--apply-log",
            str(apply_log_path),
            "--inventory",
            str(inventory_path),
        ],
        check=False,
    )

    assert (result.returncode == 0) is expected


def test_readiness_outcomes_are_independent_and_missing_evidence_is_not_proven() -> None:
    rendered = wc091_environment.validate_and_render("demo")
    metadata = [{"id": binding["id"], "enabled": True, "expired": False} for binding in rendered["secretBindings"]]
    evidence = {
        "renderDigest": rendered["renderDigest"],
        "secretMetadata": metadata,
        "demoGenerations": [
            {"generationId": "generation-1", "fixtureDigest": "fixture-a", "priorGenerationReachable": False},
            {"generationId": "generation-2", "fixtureDigest": "fixture-a", "priorGenerationReachable": False},
        ],
        "providerRedirect": {"verified": True},
    }

    result = wc091_readiness.evaluate(rendered, evidence)

    assert result == {
        "CONFIGURATION_READY": "PASS",
        "PROVIDER_REDIRECT_READY": "PASS",
        "PROVIDER_LOGIN_ACCEPTED": "NOT_PROVEN",
        "DATA_CONTINUITY_READY": "PASS",
    }


def test_secret_provisioning_preserves_existing_version_without_reading_value(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_az(command, body=None):
        calls.append((command, body))
        return wc091_secret_provision.subprocess.CompletedProcess(
            command, 0, '{"value":[{"id":"https://vault/secrets/demo-founder-bootstrap/version-1"}]}', ""
        )

    monkeypatch.setattr(wc091_secret_provision, "_az", fake_az)
    result = wc091_secret_provision.provision("demo-founder-bootstrap", "demo", "FA-091")

    assert result == {"id": "demo-founder-bootstrap", "version": "version-1", "status": "PRESERVED"}
    assert len(calls) == 1
    assert calls[0][1] is None
    assert "/versions?" in calls[0][0][3]


def test_external_secret_value_uses_stdin_body_not_command_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_az(command, body=None):
        calls.append((command, body))
        if len(calls) == 1:
            return wc091_secret_provision.subprocess.CompletedProcess(command, 1, "", "SecretNotFound 404")
        return wc091_secret_provision.subprocess.CompletedProcess(
            command, 0, '{"id":"https://vault/secrets/meta-login-client-secret/version-2"}', ""
        )

    monkeypatch.setattr(wc091_secret_provision, "_az", fake_az)
    monkeypatch.setattr(wc091_secret_provision.getpass, "getpass", lambda _: "not-logged-secret")
    result = wc091_secret_provision.provision("facebook-login-client", "demo", "FA-091")

    assert result["status"] == "CREATED"
    assert all("not-logged-secret" not in argument for call, _ in calls for argument in call)
    assert calls[1][1] == {"value": "not-logged-secret"}


def test_az_secret_body_is_read_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return wc091_secret_provision.subprocess.CompletedProcess(command, 0, "{}", "")

    monkeypatch.setattr(wc091_secret_provision.shutil, "which", lambda _: "/usr/bin/az")
    monkeypatch.setattr(wc091_secret_provision.subprocess, "run", fake_run)
    wc091_secret_provision._az(["--method", "put", "--url", "https://vault.invalid"], {"value": "secret"})

    assert captured["command"][-2:] == ["--body", "@/dev/stdin"]
    assert "secret" not in captured["command"]
    assert json.loads(captured["input"]) == {"value": "secret"}


def test_demo_reset_script_and_runtime_verifier_match_terraform_contract() -> None:
    reset = (wc091_environment.ROOT / "infrastructure/postgres/demo/reset-and-seed.sh").read_text()
    verifier = (wc091_environment.ROOT / "scripts/run_wc091_demo_data_verification.sh").read_text()
    delegated_postgres = (wc091_environment.ROOT / "scripts/test-wc059-postgres.sh").read_text()
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()

    for marker in ("WC091_GENERATION_ID", "WC091_FIXTURE_DIGEST", "wc091_demo_generation"):
        assert marker in reset
        assert marker in verifier
        assert marker in module
    assert 'rm -rf "${PGDATA:?}"/*' in reset
    assert "docker restart" in verifier
    assert '"priorGenerationReachable": false' in verifier
    assert "postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685" in delegated_postgres
    assert "postgres:16-alpine" not in delegated_postgres
