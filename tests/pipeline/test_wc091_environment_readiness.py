# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §§4-5, 9-11
# Constitutional basis: C-023, C-059, C-063, C-080

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import goal006_deployment_credentials, wc091_environment, wc091_readiness, wc091_secret_provision


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


def test_demo_terraform_uses_managed_postgres_and_no_ephemeral_vendor_storage() -> None:
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    demo = (wc091_environment.ROOT / "infrastructure/terraform/phase2/environments/demo/workload/main.tf").read_text()

    assert 'storage_type = "EmptyDir"' not in module
    assert 'path = "/var/lib/postgresql/data"' not in module
    assert 'path = "/opt/keycloak/data"' not in module
    assert "rm -rf /var/lib/postgresql/data/*" not in module
    assert "rm -rf /opt/keycloak/data/*" not in module
    assert 'resource "azurerm_container_app_job" "keycloak_migration"' in module
    assert 'resource "azurerm_container_app_job" "temporal_migration"' in module
    assert "wc091_demo_generation" not in module
    assert "WC091_GENERATION_ID" not in module
    assert "WC091_FIXTURE_DIGEST" not in module
    assert 'name        = "Identity__Hmac__Key"' in module
    assert 'name  = "Identity__Hmac__ActiveVersion"' in module
    assert 'name        = "ChannelContinuity__EnvelopeHmacKey"' in module
    assert 'name        = "Conversation__CursorHmacKey"' in module
    assert "demo_data_generation_id                  = var.manifest_digest" in demo
    assert 'filesha256("../../../../../environment-readiness/demo.rendered.json")' in demo


def test_demo_deployment_provisions_and_orders_every_hmac_secret_dependency() -> None:
    catalog = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    workflow = (wc091_environment.ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    managed_secrets = {
        entry["vaultSecretName"]
        for entry in catalog["entries"]
        if entry.get("provisioner") == "environment-deployment" and "demo" in entry["environments"]
    }
    credentials = set(goal006_deployment_credentials.deployment_credentials(catalog, "demo"))

    assert managed_secrets <= credentials
    assert "identity-event-ingest-hmac" in credentials
    assert "keycloak-client-secret" not in credentials
    assert "goal006_deployment_credentials.py" in workflow
    assert "for name in $CREDENTIAL_NAMES" in workflow
    assert "CREDENTIAL_NAMES: ${{ steps.credential-inventory.outputs.credential_names }}" in workflow
    assert (
        "azurerm_role_assignment.identity_hmac_secret" in module.split('resource "azurerm_container_app" "member"', maxsplit=1)[1]
    )
    assert (
        "azurerm_role_assignment.identity_event_secret"
        in module.split('resource "azurerm_container_app" "member"', maxsplit=1)[1]
    )
    assert (
        "azurerm_role_assignment.continuity_hmac_secret"
        in module.split('resource "azurerm_container_app" "member"', maxsplit=1)[1]
    )
    assert (
        "azurerm_role_assignment.conversation_cursor_secret"
        in module.split('resource "azurerm_container_app" "member"', maxsplit=1)[1]
    )
    assert 'scripts/goal006_keyvault_retry.py"' in workflow


def test_authentication_limiter_secrets_are_managed_for_every_environment() -> None:
    catalog = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    entries = {entry["id"]: entry for entry in catalog["entries"]}
    expected = {
        "auth-abuse-digest-key",
        "auth-abuse-redis-password",
        "auth-abuse-redis-managed-key",
    }

    assert expected <= set(entries)
    for secret_id in ("auth-abuse-digest-key", "auth-abuse-redis-password"):
        entry = entries[secret_id]
        assert entry["source"] == "platform-generated"
        assert entry["provisioner"] == "environment-deployment"
        assert entry["allowedOperations"] == ["get"]
    assert entries["auth-abuse-digest-key"]["environments"] == ["demo", "uat", "prod"]
    assert entries["auth-abuse-redis-password"]["environments"] == ["demo", "uat"]
    assert entries["auth-abuse-redis-managed-key"]["source"] == "external-operator"
    assert entries["auth-abuse-redis-managed-key"]["provisioner"] == "wc123-no-echo-provisioner"
    assert entries["auth-abuse-redis-managed-key"]["environments"] == ["prod"]

    for environment in ("demo", "uat"):
        managed = set(goal006_deployment_credentials.deployment_credentials(catalog, environment))
        assert {"auth-abuse-digest-key", "auth-abuse-redis-password"} <= managed
    prod_managed = set(goal006_deployment_credentials.deployment_credentials(catalog, "prod"))
    prod_external = set(goal006_deployment_credentials.required_external_credentials(catalog, "prod", "disabled"))
    assert "auth-abuse-digest-key" in prod_managed
    assert "auth-abuse-redis-password" not in prod_managed
    assert "auth-abuse-redis-managed-key" in prod_external


def test_external_razorpay_credentials_are_validated_but_not_seeded() -> None:
    catalog = {
        "entries": [
            {
                "vaultSecretName": "razorpay-test-key-id",
                "source": "external-operator",
                "provisioner": "founder-key-vault-admin",
                "environments": ["demo", "uat"],
            },
            {
                "vaultSecretName": "managed-secret",
                "source": "platform-generated",
                "provisioner": "environment-deployment",
                "environments": ["demo"],
            },
        ]
    }

    assert goal006_deployment_credentials.required_external_credentials(catalog, "demo") == ["razorpay-test-key-id"]
    assert "razorpay-test-key-id" not in goal006_deployment_credentials.deployment_credentials(catalog, "demo")
    assert "managed-secret" in goal006_deployment_credentials.deployment_credentials(catalog, "demo")


def test_disabled_whatsapp_does_not_require_provider_or_reserved_media_secrets() -> None:
    catalog = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    required = goal006_deployment_credentials.required_external_credentials(catalog, "demo")
    assert not any(name.startswith("whatsapp-") for name in required)
    assert "razorpay-test-key-secret" in required
    assert "web-session-token-envelope" in required


@pytest.mark.parametrize("verification_enabled", [False, True])
def test_configured_whatsapp_requires_exact_runtime_secrets_not_media(verification_enabled: bool) -> None:
    from test_goal006_deployment_inputs import whatsapp_configuration

    catalog = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    configuration = whatsapp_configuration()
    configuration["whatsapp_provider"]["verification_enabled"] = verification_enabled
    required = goal006_deployment_credentials.required_external_credentials(catalog, "demo", configuration=configuration)
    assert {name for name in required if name.startswith("whatsapp-")} == {
        "whatsapp-provider-binding",
        "whatsapp-verify-token",
        "whatsapp-app-secret",
        "whatsapp-outbound-authority",
    }


@pytest.mark.parametrize("mutation", ["media", "missing", "latest", "nonboolean", "uat"])
def test_credential_selection_rejects_malformed_or_foreign_whatsapp_configuration(mutation: str) -> None:
    from test_goal006_deployment_inputs import whatsapp_configuration

    catalog = json.loads((wc091_environment.ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    configuration = whatsapp_configuration()
    environment = "demo"
    versions = configuration["whatsapp_provider"]["secret_versions"]
    if mutation == "media":
        versions["whatsapp-media-authority"] = "b" * 32
    elif mutation == "missing":
        del versions["whatsapp-app-secret"]
    elif mutation == "latest":
        versions["whatsapp-app-secret"] = "latest"
    elif mutation == "nonboolean":
        configuration["whatsapp_provider"]["verification_enabled"] = "false"
    else:
        environment = "uat"
    with pytest.raises(ValueError):
        goal006_deployment_credentials.required_external_credentials(catalog, environment, configuration=configuration)


def test_credential_inventory_consumes_effective_configuration_and_pinned_versions() -> None:
    workflow = (wc091_environment.ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    inventory = workflow.split("      - name: Check credential inventory", 1)[1].split("      - name:", 1)[0]
    assert "--configuration workload-configuration.json" in inventory
    assert '--version "$version"' in inventory
    assert "attributes.expires" in inventory


@pytest.mark.parametrize(
    ("mode", "expected_success"),
    [
        ("disabled", True),
        ("configured", True),
        ("missing", False),
        ("disabled-secret", False),
        ("expired", False),
        ("no-expiry", False),
        ("future", False),
        ("invalid-start", False),
        ("forbidden", False),
    ],
)
def test_actual_credential_inventory_shell_respects_capability_and_validity(
    tmp_path: Path, mode: str, expected_success: bool
) -> None:
    from test_goal006_deployment_inputs import whatsapp_configuration

    configuration = whatsapp_configuration()
    if mode == "disabled":
        del configuration["whatsapp_provider"]
    (tmp_path / "workload-configuration.json").write_text(json.dumps(configuration))
    for folder in ("scripts", "infrastructure"):
        (tmp_path / folder).symlink_to(wc091_environment.ROOT / folder, target_is_directory=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    az = bin_dir / "az"
    az.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "name = args[args.index('--name') + 1]\n"
        "with open(os.environ['AZ_CALLS'], 'a') as log: log.write(json.dumps(args) + '\\n')\n"
        "mode = os.environ['INVENTORY_MODE']\n"
        "if name.startswith('whatsapp-'):\n"
        "    if name == 'whatsapp-media-authority': sys.exit(99)\n"
        "    assert args[args.index('--version') + 1] == 'a' * 32\n"
        "    if mode in ('missing', 'forbidden'):\n"
        "        print('SecretNotFound' if mode == 'missing' else 'ForbiddenByRbac', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "    print(json.dumps({'enabled': mode != 'disabled-secret',\n"
        "        'expires': None if mode == 'no-expiry' else '2020-01-01T00:00:00Z' if mode == 'expired' else '2099-01-02T00:00:00Z',\n"
        "        'notBefore': '2099-01-01T00:00:00Z' if mode == 'future' else 'bad' if mode == 'invalid-start' else None}))\n"
        "elif '--version' in args: sys.exit(98)\n"
        "elif 'attributes' in ' '.join(args): print(json.dumps({'enabled': True}))\n"
        "else: print(json.dumps({'attributes': {'enabled': True}, 'tags': {}, 'value': 'x' * 32}))\n"
    )
    az.chmod(0o755)
    steps = yaml.safe_load((wc091_environment.ROOT / ".github/workflows/environment-deployment.yaml").read_text())["jobs"][
        "terraform"
    ]["steps"]
    step = next(step for step in steps if step.get("id") == "credential-inventory")
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "KEY_VAULT_NAME": "kv-waooaw-demo",
            "TARGET_ENVIRONMENT": "demo",
            "SEEDER_IMAGE": "test-pinned-seeder",
            "INVENTORY_MODE": mode,
            "GITHUB_OUTPUT": str(tmp_path / "output"),
            "AZ_CALLS": str(tmp_path / "calls.jsonl"),
        },
    )
    assert (result.returncode == 0) == expected_success, result.stderr
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    names = {args[args.index("--name") + 1] for args in calls}
    assert "whatsapp-media-authority" not in names
    if mode == "disabled":
        assert not any(name.startswith("whatsapp-") for name in names)
        assert "razorpay-test-key-secret" in names


def test_demo_deployment_requires_external_razorpay_credentials_before_apply() -> None:
    root = wc091_environment.ROOT
    catalog = json.loads((root / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    workflow = (root / ".github/workflows/environment-deployment.yaml").read_text()
    module = (root / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    expected = {
        "razorpay-test-key-id",
        "razorpay-test-key-secret",
        "razorpay-test-webhook-secret",
    }
    entries = {entry["vaultSecretName"]: entry for entry in catalog["entries"] if entry["vaultSecretName"] in expected}
    member = module.split('resource "azurerm_container_app" "member"', maxsplit=1)[1].split(
        'resource "azurerm_user_assigned_identity" "temporal"', maxsplit=1
    )[0]

    assert set(entries) == expected
    assert all(entry["source"] == "external-operator" for entry in entries.values())
    assert all(entry["provisioner"] == "founder-key-vault-admin" for entry in entries.values())
    assert set(goal006_deployment_credentials.required_external_credentials(catalog, "demo")) >= expected
    assert expected.isdisjoint(goal006_deployment_credentials.deployment_credentials(catalog, "demo"))
    assert "--kind required-external" in workflow
    assert "Required external credential $name is missing" in workflow
    assert workflow.index("external_credential_names=") < workflow.index("Terraform workload plan")
    assert "azurerm_role_assignment.razorpay_secret" in member


def test_wc123_credentials_are_never_created_by_the_generic_seeder() -> None:
    root = wc091_environment.ROOT
    catalog = json.loads((root / "infrastructure/environment-readiness/secret-catalog.json").read_text())
    session_entries = {entry["id"]: entry for entry in catalog["entries"] if entry["id"].startswith("web-session-")}
    external_expected = {
        "web-session-handle-digest",
        "web-session-protocol-digest",
        "web-session-token-envelope",
    }
    oidc_transaction_credentials = external_expected - {"web-session-handle-digest"}
    database_entry = session_entries["web-session-database"]
    external_entries = {secret_id: entry for secret_id, entry in session_entries.items() if secret_id != "web-session-database"}

    assert database_entry["vaultSecretName"] == "web-session-database-url"
    assert database_entry["source"] == "platform-generated"
    assert database_entry["provisioner"] == "wc124-db-provisioner"
    assert {entry["vaultSecretName"] for entry in external_entries.values()} == external_expected
    assert all(entry["source"] == "external-operator" for entry in external_entries.values())
    assert all(entry["provisioner"] == "wc123-no-echo-provisioner" for entry in external_entries.values())
    assert (external_expected | {"web-session-database-url"}).isdisjoint(
        goal006_deployment_credentials.deployment_credentials(catalog, "demo")
    )
    assert (
        set(goal006_deployment_credentials.required_external_credentials(catalog, "demo", "disabled"))
        >= oidc_transaction_credentials
    )
    assert "web-session-database-url" not in (
        goal006_deployment_credentials.required_external_credentials(catalog, "demo", "disabled")
    )
    assert "web-session-handle-digest" not in (
        goal006_deployment_credentials.required_external_credentials(catalog, "demo", "disabled")
    )
    assert set(goal006_deployment_credentials.required_external_credentials(catalog, "demo", "enforced")) >= external_expected


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
    if [ "$name" = "identity-event-ingest-hmac" ]; then
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
        "CREDENTIAL_NAMES": "business-platform identity-event-ingest-hmac",
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
    assert "credential_status name=identity-event-ingest-hmac status=created" in result.stdout
    assert "keyvault secret set --vault-name synthetic-vault --name identity-event-ingest-hmac" in az_log.read_text()


@pytest.mark.parametrize(
    ("apply_log", "inventory", "expected"),
    [
        (
            "Unable to get value using Managed identity for secret identity-hmac-active",
            {"credentials": [{"name": "identity-hmac-active"}]},
            True,
        ),
        (
            (
                'Code: "ContainerAppOperationError"\n'
                "Field 'configuration.secrets' is invalid with details: "
                '\'Invalid value: \\"web-session-database-url\\": Unable to get value using '
                "Managed identity /subscriptions/sub/resourceGroups/rg/providers/"
                "Microsoft.ManagedIdentity/userAssignedIdentities/id-demo-web for secret "
                "web-session-database-url. Error: unable to fetch secret "
                "'web-session-database-url' using Managed identity'"
            ),
            {"credentials": [{"name": "web-session-database-url"}]},
            True,
        ),
        (
            "Unable to get value using Managed identity for secret identity-event-ingest-hmac",
            {"credentials": [{"name": "identity-event-ingest-hmac"}]},
            True,
        ),
        (
            "Unable to get value using Managed identity for secret razorpay-test-key-secret",
            {"credentials": [{"name": "razorpay-test-key-secret", "status": "ready"}]},
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
    plan_path = tmp_path / "workload-plan.json"
    apply_log_path.write_text(apply_log)
    inventory_path.write_text(json.dumps(inventory))
    plan_path.write_text(json.dumps({"planned_values": {"root_module": {}}}))

    result = subprocess.run(
        [
            sys.executable,
            str(wc091_environment.ROOT / "scripts/goal006_keyvault_retry.py"),
            "--apply-log",
            str(apply_log_path),
            "--inventory",
            str(inventory_path),
            "--plan",
            str(plan_path),
        ],
        check=False,
    )

    assert (result.returncode == 0) is expected


def test_keyvault_retry_classifier_covers_exact_planned_container_app_secrets(tmp_path) -> None:
    apply_log_path = tmp_path / "workload-apply.log"
    inventory_path = tmp_path / "credential-inventory.json"
    plan_path = tmp_path / "workload-plan.json"
    inventory_path.write_text(json.dumps({"credentials": []}))
    plan_path.write_text(
        json.dumps(
            {
                "planned_values": {
                    "root_module": {
                        "child_modules": [
                            {
                                "resources": [
                                    {
                                        "type": "azurerm_container_app",
                                        "values": {
                                            "secret": [
                                                {
                                                    "key_vault_secret_id": (
                                                        "https://kv-waooaw-demo.vault.azure.net/secrets/google-client-secret"
                                                    )
                                                }
                                            ]
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        )
    )

    for secret_name, expected in (("google-client-secret", True), ("undeclared-secret", False)):
        apply_log_path.write_text(
            f'Invalid value: "{secret_name}": Unable to get value using Managed identity '
            f"/subscriptions/sub/resourceGroups/rg/providers/Microsoft.ManagedIdentity/"
            f"userAssignedIdentities/id-demo-web for secret {secret_name}"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(wc091_environment.ROOT / "scripts/goal006_keyvault_retry.py"),
                "--apply-log",
                str(apply_log_path),
                "--inventory",
                str(inventory_path),
                "--plan",
                str(plan_path),
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


def test_optional_whatsapp_gates_do_not_make_baseline_ready_or_require_disabled_media() -> None:
    rendered = wc091_environment.validate_and_render("demo")
    optional = [binding for binding in rendered["secretBindings"] if "readinessGate" in binding]
    assert {binding["id"] for binding in optional} == {
        "whatsapp-provider-binding",
        "whatsapp-verify-token",
        "whatsapp-app-secret",
        "whatsapp-outbound-authority",
        "whatsapp-media-authority",
    }
    evidence = {
        "renderDigest": rendered["renderDigest"],
        "secretMetadata": [
            {"id": binding["id"], "enabled": True, "expired": False}
            for binding in rendered["secretBindings"]
            if "readinessGate" not in binding
        ],
    }
    outcomes = wc091_readiness.evaluate(rendered, evidence)
    assert outcomes["CONFIGURATION_READY"] == "PASS"
    assert outcomes["PROVIDER_LOGIN_ACCEPTED"] == "NOT_PROVEN"
    evidence["secretMetadata"] = []
    assert wc091_readiness.evaluate(rendered, evidence)["CONFIGURATION_READY"] == "NOT_PROVEN"


def test_unknown_secret_readiness_gate_fails_closed() -> None:
    rendered = wc091_environment.validate_and_render("demo")
    rendered["secretBindings"][0]["readinessGate"] = "unrecognized"
    evidence = {
        "renderDigest": rendered["renderDigest"],
        "secretMetadata": [{"id": binding["id"], "enabled": True, "expired": False} for binding in rendered["secretBindings"]],
    }
    assert wc091_readiness.evaluate(rendered, evidence)["CONFIGURATION_READY"] == "NOT_PROVEN"

    baseline = next(binding for binding in rendered["secretBindings"] if not binding["id"].startswith("whatsapp-"))
    baseline["readinessGate"] = "demo-whatsapp-provider"
    assert wc091_readiness.evaluate(rendered, evidence)["CONFIGURATION_READY"] == "NOT_PROVEN"


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


def test_whatsapp_secret_upload_sets_validity_and_explicit_new_version(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_az(command, body=None):
        calls.append((command, body))
        if body is None:
            return wc091_secret_provision.subprocess.CompletedProcess(
                command, 0, '{"value":[{"id":"https://vault/secrets/whatsapp-outbound-authority/old"}]}', ""
            )
        return wc091_secret_provision.subprocess.CompletedProcess(
            command, 0, '{"id":"https://kv-waooaw-demo.vault.azure.net/secrets/whatsapp-outbound-authority/new"}', ""
        )

    monkeypatch.setattr(wc091_secret_provision, "_az", fake_az)
    monkeypatch.setattr(wc091_secret_provision.getpass, "getpass", lambda _: "private-test-value")
    result = wc091_secret_provision.provision(
        "whatsapp-outbound-authority",
        "demo",
        "FA-120",
        expires_at="2099-01-02T00:00:00Z",
        not_before="2099-01-01T00:00:00Z",
        new_version=True,
    )
    assert result["status"] == "CREATED"
    assert calls[-1][1]["attributes"] == {"enabled": True, "exp": 4070995200, "nbf": 4070908800}
    assert all("private-test-value" not in argument for command, _ in calls for argument in command)
    assert all("patch" not in command for command, _ in calls)


@pytest.mark.parametrize("expires_at", [None, "2020-01-01T00:00:00Z", "2099-01-01", "bad"])
def test_whatsapp_upload_denies_missing_expired_or_naive_expiry_before_prompt(
    monkeypatch: pytest.MonkeyPatch, expires_at: str | None
) -> None:
    def deny_call(*args, **kwargs):
        pytest.fail("invalid validity must fail before Azure or secret input")

    monkeypatch.setattr(wc091_secret_provision, "_az", deny_call)
    monkeypatch.setattr(wc091_secret_provision.getpass, "getpass", deny_call)
    with pytest.raises(wc091_secret_provision.ProvisioningError):
        wc091_secret_provision.provision("whatsapp-outbound-authority", "demo", "FA-120", expires_at=expires_at, new_version=True)


def test_secret_upload_never_falls_back_to_echoed_input(monkeypatch: pytest.MonkeyPatch) -> None:
    import warnings

    monkeypatch.setattr(
        wc091_secret_provision,
        "_az",
        lambda command, body=None: wc091_secret_provision.subprocess.CompletedProcess(command, 1, "", "SecretNotFound"),
    )

    def fallback(prompt):
        warnings.warn("Cannot control echo on the terminal.", getpass.GetPassWarning, stacklevel=2)
        pytest.fail("echo fallback must be stopped before reading input")

    import getpass

    monkeypatch.setattr(wc091_secret_provision.getpass, "getpass", fallback)
    with pytest.raises(wc091_secret_provision.ProvisioningError, match="terminal"):
        wc091_secret_provision.provision("facebook-login-client", "demo", "FA-120")


@pytest.mark.parametrize("error", ["ForbiddenByRbac", "ForbiddenByFirewall", "404 ResourceNotFound"])
def test_uploader_metadata_failure_never_prompts_or_writes(monkeypatch: pytest.MonkeyPatch, error: str) -> None:
    calls = []

    def fake_az(command, body=None):
        calls.append((command, body))
        return wc091_secret_provision.subprocess.CompletedProcess(command, 1, "", error)

    monkeypatch.setattr(wc091_secret_provision, "_az", fake_az)
    monkeypatch.setattr(wc091_secret_provision.getpass, "getpass", lambda _: pytest.fail("must not prompt"))
    with pytest.raises(wc091_secret_provision.ProvisioningError, match="metadata"):
        wc091_secret_provision.provision("facebook-login-client", "demo", "FA-120")
    assert len(calls) == 1


@pytest.mark.parametrize("source", ["platform-generated", "external-operator"])
def test_uploader_validity_requires_explicit_rotation_for_existing_secret(monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    monkeypatch.setattr(wc091_secret_provision, "_entry", lambda *_: {"source": source, "vaultSecretName": "existing"})
    monkeypatch.setattr(
        wc091_secret_provision,
        "_az",
        lambda command, body=None: wc091_secret_provision.subprocess.CompletedProcess(
            command, 0, '{"value":[{"id":"https://vault/secrets/existing/old"}]}', ""
        ),
    )
    with pytest.raises(wc091_secret_provision.ProvisioningError, match="--new-version"):
        wc091_secret_provision.provision("existing", "demo", "FA-120", expires_at="2099-01-01T00:00:00Z")


def test_reserved_media_secret_cannot_be_provisioned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wc091_secret_provision, "_az", lambda *_, **__: pytest.fail("media must not access vault"))
    with pytest.raises(wc091_secret_provision.ProvisioningError, match="scanner"):
        wc091_secret_provision.provision(
            "whatsapp-media-authority", "demo", "FA-120", expires_at="2099-01-01T00:00:00Z", new_version=True
        )


@pytest.mark.parametrize(
    ("expires_at", "not_before"),
    [
        (None, "2099-01-01T00:00:00Z"),
        ("2099-01-01T00:00:00Z", "2099-01-01T00:00:00Z"),
        ("2099-01-01T00:00:00Z", "2099-01-02T00:00:00Z"),
        ("2099-01-01T00:00:00Z", "bad"),
    ],
)
def test_invalid_validity_window_fails_before_metadata(
    monkeypatch: pytest.MonkeyPatch, expires_at: str | None, not_before: str
) -> None:
    monkeypatch.setattr(wc091_secret_provision, "_az", lambda *_, **__: pytest.fail("invalid validity must not access vault"))
    with pytest.raises(wc091_secret_provision.ProvisioningError):
        wc091_secret_provision.provision("facebook-login-client", "demo", "FA-120", expires_at=expires_at, not_before=not_before)


def test_demo_reset_script_and_runtime_verifier_match_terraform_contract() -> None:
    reset = (wc091_environment.ROOT / "infrastructure/postgres/demo/reset-and-seed.sh").read_text()
    verifier = (wc091_environment.ROOT / "scripts/run_wc091_demo_data_verification.sh").read_text()
    delegated_postgres = (wc091_environment.ROOT / "scripts/test-wc059-postgres.sh").read_text()
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()

    for marker in ("WC091_GENERATION_ID", "WC091_FIXTURE_DIGEST", "wc091_demo_generation"):
        assert marker in reset
        assert marker in verifier
        assert marker not in module
    assert 'rm -rf "${PGDATA:?}"/*' in reset
    assert "docker restart" in verifier
    assert '"priorGenerationReachable": false' in verifier
    assert "docker compose config --format json" in delegated_postgres
    assert ".networks.default.name" in delegated_postgres
    assert "postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685" in delegated_postgres
    assert "postgres:16-alpine" not in delegated_postgres
