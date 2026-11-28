from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

import pytest

from goal006_deployment_inputs import (
    DATABASE_SECRET_NAMES,
    LEASE_FIELDS,
    add_key_vault_references,
    create_inputs,
    feature_settings_inputs,
    merge_environment_settings,
    whatsapp_monitoring_inputs,
)
from goal006_registry_manifest import RELEASE_MEMBERS


def manifest() -> dict[str, Any]:
    images = {member: f"ghcr.io/dlai-sd/{member}@sha256:{'a' * 64}" for member in RELEASE_MEMBERS}
    return {
        "schema": "waooaw.registry-release/v1",
        "immutable": True,
        "source_commit": "a" * 40,
        "builder_workflow": ".github/workflows/ci.yaml",
        "qualification": {"status": "pass", "github_run_id": "123"},
        "images": images,
        "evidence": {
            member: {
                "scan": {
                    "artifact": f"goal006-scan-{member}",
                    "policy": "fixable-high-critical",
                    "sha256": "b" * 64,
                },
                "sbom": {
                    "artifact": f"goal006-attestation-{member}",
                    "format": "spdx",
                    "oci_subject": images[member],
                    "sha256": "c" * 64,
                },
                "provenance": {
                    "artifact": f"goal006-attestation-{member}",
                    "mode": "max",
                    "oci_subject": images[member],
                    "sha256": "d" * 64,
                },
                "signature": {
                    "artifact": f"goal006-attestation-{member}",
                    "issuer": "github-oidc",
                    "oci_subject": images[member],
                    "sha256": "e" * 64,
                },
            }
            for member in RELEASE_MEMBERS
        },
    }


def configuration(environment: str = "demo") -> dict[str, Any]:
    database_secret_names = {
        principal: secret_name
        for principal, secret_name in DATABASE_SECRET_NAMES.items()
        if environment == "demo" or principal not in {"temporal", "temporal-migration"}
    }
    values: dict[str, Any] = {
        "key_vault_secret_uris": {member: f"https://kv-demo.vault.azure.net/secrets/{member}" for member in RELEASE_MEMBERS},
        "key_vault_secret_resource_ids": {
            member: f"/subscriptions/test/resourceGroups/test/providers/Microsoft.KeyVault/vaults/test/secrets/{member}"
            for member in RELEASE_MEMBERS
        },
        "database_secret_uris": {
            principal: f"https://kv-demo.vault.azure.net/secrets/{secret_name}"
            for principal, secret_name in database_secret_names.items()
        },
        "database_secret_resource_ids": {
            principal: (f"/subscriptions/test/resourceGroups/test/providers/Microsoft.KeyVault/vaults/test/secrets/{secret_name}")
            for principal, secret_name in database_secret_names.items()
        },
        "planned_incremental_monthly_cost_inr": 1000,
        "cumulative_one_time_cost_inr": 1000,
        "dma_admission_content_digest": "sha256:" + "f" * 64,
    }
    values.update({field: f"accepted-{field}" for field in LEASE_FIELDS})
    values["lease_state"] = "ACTIVE"
    values["lease_issued_at"] = "2026-08-23T12:46:35Z"
    values["lease_expires_at"] = "2099-08-27T12:46:35Z"
    return values


def monitoring_configuration() -> dict[str, Any]:
    prefix = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/waooaw-demo-rg/providers/"
    query = Path(__file__).parents[2] / "infrastructure/operations/wc134-whatsapp-monitor.kql"
    return {
        "workspace_id": prefix + "Microsoft.OperationalInsights/workspaces/law-waooaw-demo-validation",
        "action_group_id": prefix + "Microsoft.Insights/actionGroups/approved-demo-receiver",
        "approval_reference": "test:reviewed-monitor-plan",
        "query_digest": "sha256:" + hashlib.sha256(query.read_bytes()).hexdigest(),
        "activation_digest": "d" * 64,
        "release_digest": "sha256:" + "a" * 64,
        "configuration_digest": "sha256:" + "b" * 64,
        "starts_at": "2026-11-07T09:00:00Z",
        "expires_at": "2026-11-07T09:30:00Z",
    }


def test_monitoring_defaults_off_and_preserves_exact_reviewed_tuple() -> None:
    values = configuration()
    assert "whatsapp_monitoring" not in create_inputs("demo", manifest(), values, True)
    values["whatsapp_monitoring"] = monitoring_configuration()
    inputs = create_inputs("demo", manifest(), values, True)
    assert inputs["whatsapp_monitoring"] == values["whatsapp_monitoring"]
    assert "whatsapp_provider" not in inputs


@pytest.mark.parametrize("environment", ["uat", "prod"])
def test_monitoring_does_not_admit_other_environments(environment: str) -> None:
    with pytest.raises(ValueError, match="Demo-only"):
        whatsapp_monitoring_inputs(environment, {"whatsapp_monitoring": monitoring_configuration()}, manifest())


@pytest.mark.parametrize(
    "field,value",
    [
        ("approval_reference", ""),
        ("query_digest", "sha256:" + "0" * 64),
        ("release_digest", "sha256:" + "c" * 64),
        ("configuration_digest", "latest"),
        ("activation_digest", "opaque-activation-reference"),
        ("starts_at", "2026-11-07T09:00:00"),
        ("starts_at", "2026-13-07T09:00:00Z"),
        ("expires_at", "2026-11-07T09:00:00Z"),
        ("workspace_id", "/unrelated/workspace"),
        ("action_group_id", "/unrelated/receiver"),
        ("activation_digest", None),
    ],
)
def test_monitoring_rejects_invalid_plan_before_terraform(field: str, value: Any) -> None:
    monitoring = monitoring_configuration()
    monitoring[field] = value
    with pytest.raises(ValueError):
        whatsapp_monitoring_inputs("demo", {"whatsapp_monitoring": monitoring}, manifest())


def test_monitoring_rejects_unknown_fields_and_cross_subscription_receiver() -> None:
    monitoring = monitoring_configuration()
    monitoring["phone_number"] = "not-an-approved-field"
    with pytest.raises(ValueError, match="closed"):
        whatsapp_monitoring_inputs("demo", {"whatsapp_monitoring": monitoring}, manifest())
    del monitoring["phone_number"]
    monitoring["action_group_id"] = monitoring["action_group_id"].replace(
        "00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"
    )
    with pytest.raises(ValueError, match="subscription/group"):
        whatsapp_monitoring_inputs("demo", {"whatsapp_monitoring": monitoring}, manifest())


@pytest.mark.parametrize(
    "field,value",
    [
        ("starts_at", "2025-11-07T09:00:00Z"),
        ("expires_at", "2100-11-07T09:30:00Z"),
    ],
)
def test_monitoring_window_cannot_extend_workload_lease(field: str, value: str) -> None:
    values = configuration()
    monitoring = monitoring_configuration()
    monitoring[field] = value
    values["whatsapp_monitoring"] = monitoring
    with pytest.raises(ValueError, match="contained"):
        create_inputs("demo", manifest(), values, True)


def test_monitoring_rule_uses_exact_machine_observation_and_existing_receiver() -> None:
    root = Path(__file__).parents[2]
    query = (root / "infrastructure/operations/wc134-whatsapp-monitor.kql").read_text()
    rule = (root / "infrastructure/terraform/phase2/modules/workload/whatsapp-monitoring.tf").read_text()
    entry = (root / "infrastructure/terraform/phase2/environments/demo/workload/main.tf").read_text()
    for field in ("activationDigest", "releaseDigest", "configurationDigest"):
        assert "Observation." + field in query
    assert 'Observation.kind == "HEARTBEAT"' in query
    assert "ObservedAt >= ago(2m) and ObservedAt <= now()" in query
    assert "now() >= StartsAt + 2m and Heartbeats == 0" in query
    assert "now() >= StartsAt and now() < ExpiresAt" in query
    assert "OPERATIONS_HEARTBEAT_MISSING" in query
    assert "var.workload_enabled && var.whatsapp_monitoring != null ? 1 : 0" in rule
    assert "evaluation_frequency" in rule and '"PT5M"' in rule
    assert "action_groups = [var.whatsapp_monitoring.action_group_id]" in rule
    assert 'resource "azurerm_monitor_action_group"' not in rule
    assert "whatsapp_monitoring" in entry
    assert "log_analytics_workspace_id" in entry


@pytest.mark.parametrize("environment", ["demo", "uat"])
def test_nonproduction_inputs_require_lease_and_preserve_exact_tuple(environment: str) -> None:
    inputs = create_inputs(
        environment,
        manifest(),
        configuration(environment),
        True,
        current_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )
    assert set(inputs["image_digests"]) == RELEASE_MEMBERS
    assert inputs["lease_state"] == "ACTIVE"
    assert inputs["ghcr_packages_public"] is True
    assert "whatsapp_provider" not in inputs
    assert "feature_settings" not in inputs and "platform_access" not in inputs


def configured(environment: str, **fields: Any) -> dict[str, Any]:
    values = configuration(environment)
    values.update(fields)
    return values


def test_feature_settings_and_founders_pass_through_unchanged_for_any_environment() -> None:
    settings = {
        "workbench_enabled": True,
        "wallet_authority": "SHADOW",
        "trial_identity_binding_mode": "RECORD",
        "whatsapp_stop_acknowledgement_enabled": True,
    }
    access = {
        "founders": [
            {"email": "founder@example.org", "subject": "a1b2c3d4-e5f6"},
            {"email": "second@example.org", "rebind_on_start": True},
        ]
    }
    for environment in ("demo", "uat", "prod"):
        inputs = create_inputs(
            environment,
            manifest(),
            configured(environment, feature_settings=settings, platform_access=access, ce_min_replicas=1, pr_min_replicas=1),
            True,
            current_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )
        assert inputs["feature_settings"] == settings
        assert inputs["platform_access"] == access


@pytest.mark.parametrize("environment", ["demo", "uat"])
def test_acceptance_synthetic_tenants_setting_is_available_for_demo_and_uat(environment: str) -> None:
    inputs = create_inputs(
        environment,
        manifest(),
        configured(environment, feature_settings={"acceptance_synthetic_tenants_enabled": True}),
        True,
        current_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )
    assert inputs["feature_settings"] == {"acceptance_synthetic_tenants_enabled": True}


@pytest.mark.parametrize("value", [True, False])
def test_acceptance_synthetic_tenants_setting_is_rejected_for_production_before_terraform(value: bool) -> None:
    with pytest.raises(ValueError, match="exist only for Demo and UAT"):
        create_inputs(
            "prod",
            manifest(),
            configured(
                "prod",
                feature_settings={"acceptance_synthetic_tenants_enabled": value},
                ce_min_replicas=1,
                pr_min_replicas=1,
            ),
            True,
            current_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


def test_acceptance_synthetic_tenants_setting_must_be_a_boolean() -> None:
    with pytest.raises(ValueError, match="acceptance_synthetic_tenants_enabled must be a boolean"):
        create_inputs(
            "demo",
            manifest(),
            configured("demo", feature_settings={"acceptance_synthetic_tenants_enabled": "true"}),
            True,
            current_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    "fields",
    [
        {"feature_settings": {"unknown_flag": True}},
        {"feature_settings": {"workbench_enabled": "true"}},
        {"feature_settings": {"wallet_authority": "AUTO"}},
        {"feature_settings": {"trial_identity_binding_mode": "record"}},
        {"feature_settings": ["workbench_enabled"]},
        {"platform_access": {"founders": []}},
        {"platform_access": {"founders": [{"email": "Founder@Example.org"}]}},
        {"platform_access": {"founders": [{"email": "a@example.org"}, {"email": "a@example.org"}]}},
        {"platform_access": {"founders": [{"email": "a@example.org", "subject": "short"}]}},
        {"platform_access": {"founders": [{"email": "a@example.org", "role": "founder"}]}},
        {"platform_access": {"founders": [{"email": "a@example.org", "rebind_on_start": "true"}]}},
        {"platform_access": {"founders": [{"email": "a@example.org", "subject": "a1b2c3d4-e5f6", "rebind_on_start": True}]}},
        {"platform_access": {"admins": [{"email": "a@example.org"}]}},
        {"feature_settings": {"employment_protocol_rollback_epoch": -1}},
        {"feature_settings": {"employment_protocol_rollback_epoch": True}},
        {"feature_settings": {"employment_protocol_enabled": "true"}},
    ],
)
def test_invalid_feature_settings_or_founders_fail_before_terraform(fields: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        create_inputs(
            "demo", manifest(), configured("demo", **fields), True, current_time=datetime(2026, 8, 25, tzinfo=timezone.utc)
        )


def test_wc170_employment_activation_settings_pass_through_for_demo() -> None:
    settings = {
        "employment_protocol_enabled": True,
        "employment_protocol_rollback_epoch": 2,
        "web_conversation_enabled": True,
    }
    inputs = create_inputs(
        "demo",
        manifest(),
        configured("demo", feature_settings=settings),
        True,
        current_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )
    assert inputs["feature_settings"] == settings


SETTINGS_DIR = Path(__file__).resolve().parents[2] / "infrastructure" / "platform-settings"


def test_environment_settings_file_is_the_base_and_the_private_blob_wins_key_by_key() -> None:
    file_settings = {
        "feature_settings": {"workbench_enabled": True, "wallet_authority": "WALLET"},
        "platform_access": {"founders": [{"email": "file@example.org"}]},
    }
    merged = merge_environment_settings({"lease_state": "ACTIVE"}, file_settings)
    assert merged["feature_settings"] == file_settings["feature_settings"]
    assert merged["platform_access"] == file_settings["platform_access"]
    override = {
        "feature_settings": {"wallet_authority": "SHADOW"},
        "platform_access": {"founders": [{"email": "blob@example.org"}]},
    }
    merged = merge_environment_settings(override, file_settings)
    assert merged["feature_settings"] == {"workbench_enabled": True, "wallet_authority": "SHADOW"}
    assert merged["platform_access"] == override["platform_access"]
    assert merge_environment_settings({"lease_state": "ACTIVE"}, {}) == {"lease_state": "ACTIVE"}


@pytest.mark.parametrize("settings", [{"image_digests": {}}, {"feature_settings": {}, "lease_state": "ACTIVE"}, [], "x"])
def test_environment_settings_file_is_closed_to_the_two_setting_groups(settings: Any) -> None:
    with pytest.raises(ValueError):
        merge_environment_settings({}, settings)


@pytest.mark.parametrize("environment", ["demo", "uat", "prod"])
def test_committed_environment_settings_are_valid_for_every_environment(environment: str) -> None:
    import json

    settings = json.loads((SETTINGS_DIR / f"{environment}.json").read_text(encoding="utf-8"))
    feature_settings_inputs(merge_environment_settings({}, settings))


def test_demo_enables_the_workbench_and_names_a_founder() -> None:
    import json

    inputs = feature_settings_inputs(
        merge_environment_settings({}, json.loads((SETTINGS_DIR / "demo.json").read_text(encoding="utf-8")))
    )
    assert inputs["feature_settings"]["workbench_enabled"] is True
    assert inputs["platform_access"]["founders"]


def whatsapp_configuration() -> dict[str, Any]:
    values = add_key_vault_references(
        configuration(),
        "/subscriptions/test/resourceGroups/demo/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo",
        "https://kv-waooaw-demo.vault.azure.net/",
        "demo",
    )
    values["whatsapp_provider"] = {
        "callback_host": "whatsapp-demo.example.com",
        "secret_versions": {
            name: "a" * 32
            for name in (
                "whatsapp-provider-binding",
                "whatsapp-verify-token",
                "whatsapp-app-secret",
                "whatsapp-outbound-authority",
            )
        },
        "authority_reference": "FA:demo-provider",
        "verification_enabled": False,
    }
    return values


def test_whatsapp_deployment_inputs_pin_release_and_remain_registration_only() -> None:
    values = whatsapp_configuration()
    first = create_inputs("demo", manifest(), values, True)
    assert first == create_inputs("demo", manifest(), values, True)
    provider = first["whatsapp_provider"]
    assert provider["release_digest"] == "sha256:" + "a" * 64
    assert provider["configuration_digest"].startswith("sha256:")
    assert provider["catalog_digest"].startswith("sha256:")
    assert provider["verification_enabled"] is False
    assert set(provider) == {
        "callback_host",
        "secret_versions",
        "authority_reference",
        "verification_enabled",
        "release_digest",
        "configuration_digest",
        "catalog_digest",
    }
    values["whatsapp_provider"]["verification_enabled"] = True
    changed = create_inputs("demo", manifest(), values, True)["whatsapp_provider"]
    assert changed["configuration_digest"] != provider["configuration_digest"]
    assert changed["verification_enabled"] is True
    values = whatsapp_configuration()
    values["whatsapp_provider"]["secret_versions"]["whatsapp-phone-subject-hmac"] = "e" * 32
    public = create_inputs("demo", manifest(), values, True)["whatsapp_provider"]
    assert public["secret_versions"]["whatsapp-phone-subject-hmac"] == "e" * 32


@pytest.mark.parametrize("environment", ["uat", "prod"])
def test_whatsapp_configuration_cannot_cross_environments(environment: str) -> None:
    with pytest.raises(ValueError, match="Demo-only"):
        create_inputs(environment, manifest(), whatsapp_configuration(), True)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "media",
        "missing-secret",
        "wrong-version",
        "wrong-host",
        "url-in-host",
        "empty-authority",
        "string-switch",
        "wrong-vault",
    ],
)
def test_invalid_whatsapp_configuration_fails_before_terraform(mutation: str) -> None:
    values = whatsapp_configuration()
    provider = values["whatsapp_provider"]
    if mutation == "unknown":
        provider["dispatch_enabled"] = True
    elif mutation == "media":
        provider["secret_versions"]["whatsapp-media-authority"] = "b" * 32
    elif mutation == "missing-secret":
        del provider["secret_versions"]["whatsapp-app-secret"]
    elif mutation == "wrong-version":
        provider["secret_versions"]["whatsapp-app-secret"] = "latest"
    elif mutation == "wrong-host":
        provider["callback_host"] = "cp.demo.waooaw.com"
    elif mutation == "url-in-host":
        provider["callback_host"] = "https://whatsapp-demo.example.com/webhook"
    elif mutation == "empty-authority":
        provider["authority_reference"] = ""
    elif mutation == "string-switch":
        provider["verification_enabled"] = "false"
    elif mutation == "wrong-vault":
        values["key_vault_secret_uris"]["web"] = "https://kv-uat.vault.azure.net/secrets/web"
    with pytest.raises(ValueError, match="WhatsApp"):
        create_inputs("demo", manifest(), values, True)


def test_expired_nonproduction_lease_is_rejected_before_terraform_inputs() -> None:
    values = configuration()
    values["lease_expires_at"] = "2026-08-25T12:46:35Z"

    with pytest.raises(ValueError, match="deployment lease expired at 2026-08-25T12:46:35Z"):
        create_inputs(
            "demo",
            manifest(),
            values,
            True,
            current_time=datetime(2026, 8, 25, 17, 23, tzinfo=timezone.utc),
        )


def test_anonymous_ghcr_verification_is_required() -> None:
    with pytest.raises(ValueError, match="anonymous digest pulls"):
        create_inputs("demo", manifest(), configuration(), False)


def test_missing_member_or_lease_field_is_rejected() -> None:
    values = configuration()
    del values["key_vault_secret_uris"]["web"]
    with pytest.raises(ValueError, match="exactly the seven"):
        create_inputs("demo", manifest(), values, True)
    values = configuration("uat")
    del values["lease_expires_at"]
    with pytest.raises(ValueError, match="lease_expires_at"):
        create_inputs("uat", manifest(), values, True)


def test_secret_uri_and_rbac_scope_types_are_not_interchangeable() -> None:
    values = configuration()
    values["key_vault_secret_uris"] = values["key_vault_secret_resource_ids"]
    with pytest.raises(ValueError, match="versionless secret URI"):
        create_inputs("demo", manifest(), values, True)


def test_vault_references_are_derived_from_foundation_outputs() -> None:
    values = configuration()
    del values["key_vault_secret_uris"]
    del values["key_vault_secret_resource_ids"]
    values = add_key_vault_references(
        values,
        "/subscriptions/test/resourceGroups/demo/providers/Microsoft.KeyVault/vaults/kv-demo",
        "https://kv-demo.vault.azure.net/",
        "demo",
    )
    inputs = create_inputs("demo", manifest(), values, True)
    assert inputs["key_vault_secret_uris"]["web"] == "https://kv-demo.vault.azure.net/secrets/web"
    assert inputs["key_vault_secret_resource_ids"]["web"].endswith("/vaults/kv-demo/secrets/web")
    assert inputs["key_vault_secret_uris"]["agent-runtime-adapter-digital-marketing"].endswith("/secrets/professional-runtime")


@pytest.mark.parametrize(
    "vault_uri",
    [
        "https://attacker.example/.vault.azure.net/",
        "https://kv-demo.vault.azure.net.attacker.example/",
        "https://user@kv-demo.vault.azure.net/",
        "https://kv-demo.vault.azure.net/?redirect=attacker",
    ],
)
def test_foundation_vault_uri_rejects_spoofed_urls(vault_uri: str) -> None:
    with pytest.raises(ValueError, match="Azure Key Vault URI"):
        add_key_vault_references(
            configuration(),
            "/subscriptions/test/resourceGroups/demo/providers/Microsoft.KeyVault/vaults/kv-demo",
            vault_uri,
        )


def test_runtime_secret_uri_rejects_vault_text_in_path() -> None:
    values = configuration()
    values["key_vault_secret_uris"]["web"] = "https://attacker.example/.vault.azure.net/secrets/web"
    with pytest.raises(ValueError, match="versionless secret URI"):
        create_inputs("demo", manifest(), values, True)


def test_runtime_secret_uri_rejects_versioned_or_nested_paths() -> None:
    values = configuration()
    values["key_vault_secret_uris"]["web"] = "https://kv-demo.vault.azure.net/secrets/web/version"
    with pytest.raises(ValueError, match="versionless secret URI"):
        create_inputs("demo", manifest(), values, True)


def test_invalid_secret_resource_ids_are_rejected() -> None:
    values = configuration()
    values["key_vault_secret_resource_ids"] = values["key_vault_secret_uris"]
    with pytest.raises(ValueError, match="secret resource ID"):
        create_inputs("demo", manifest(), values, True)


def test_production_requires_positive_accepted_replica_values() -> None:
    values = configuration()
    values.update(ce_min_replicas=1, pr_min_replicas=1)
    inputs = create_inputs("prod", manifest(), values, True)
    assert inputs["ce_min_replicas"] == inputs["pr_min_replicas"] == 1
    values["ce_min_replicas"] = 0
    with pytest.raises(ValueError, match="ce_min_replicas"):
        create_inputs("prod", manifest(), values, True)


def test_tampered_manifest_is_rejected_before_input_generation() -> None:
    release = manifest()
    release["images"]["web"] = "ghcr.io/dlai-sd/web:latest"
    with pytest.raises(ValueError, match="invalid release manifest"):
        create_inputs("demo", release, configuration(), True)


def test_missing_or_negative_cost_assumptions_are_rejected() -> None:
    values = configuration()
    del values["planned_incremental_monthly_cost_inr"]
    with pytest.raises(ValueError, match="planned_incremental_monthly_cost_inr"):
        create_inputs("demo", manifest(), values, True)
    values = configuration("uat")
    values["cumulative_one_time_cost_inr"] = -1
    with pytest.raises(ValueError, match="cumulative_one_time_cost_inr"):
        create_inputs("uat", manifest(), values, True)


def test_image_registry_inputs_are_environment_bound_and_keep_canonical_ghcr_digests() -> None:
    server = "acrwaooawdemo2ed118.azurecr.io"
    pull_identity = (
        "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/waooaw-demo-rg/providers/"
        "Microsoft.ManagedIdentity/userAssignedIdentities/id-waooaw-demo-image-pull"
    )
    now = datetime(2026, 8, 25, tzinfo=timezone.utc)
    github = create_inputs("demo", manifest(), configuration(), True, current_time=now)
    assert "image_registry_server" not in github
    azure = create_inputs(
        "demo",
        manifest(),
        configuration(),
        True,
        current_time=now,
        image_registry_server=server,
        image_pull_identity_id=pull_identity,
    )
    assert azure["image_registry_server"] == server
    assert azure["image_pull_identity_id"] == pull_identity
    assert azure["image_digests"] == github["image_digests"]
    for arguments in (
        {"image_registry_server": server},
        {"image_registry_server": "acrwaooawuat2ed118.azurecr.io", "image_pull_identity_id": pull_identity},
        {"image_registry_server": server, "image_pull_identity_id": pull_identity.replace("demo-image", "uat-image")},
    ):
        with pytest.raises(ValueError, match="image"):
            create_inputs("demo", manifest(), configuration(), True, current_time=now, **arguments)


@pytest.mark.parametrize(("environment", "expected"), [("demo", True), ("uat", None), ("prod", None)])
def test_only_demo_enables_synthetic_acceptance_tenants_in_the_committed_settings(
    environment: str, expected: bool | None
) -> None:
    import json

    settings = json.loads((SETTINGS_DIR / f"{environment}.json").read_text(encoding="utf-8"))
    assert settings.get("feature_settings", {}).get("acceptance_synthetic_tenants_enabled") is expected


def test_the_database_principals_the_inputs_script_names_match_the_terraform_validation() -> None:
    # The workload module accepts exactly these principals in Demo; a missing or extra one fails planning after a long apply.
    import re

    variables = (SETTINGS_DIR.parents[1] / "infrastructure/terraform/phase2/modules/workload/variables.tf").read_text(encoding="utf-8")
    block = re.search(r'var\.environment == "demo" \? \[(.*?)\] : \[', variables, re.S)
    assert block is not None
    assert set(re.findall(r'"([a-z-]+)"', block.group(1))) == set(DATABASE_SECRET_NAMES)
