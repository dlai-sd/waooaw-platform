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
    assert "evaluation_frequency" in rule and '"PT1M"' in rule
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
