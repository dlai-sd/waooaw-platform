from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from goal006_deployment_inputs import WHATSAPP_SECRET_NAMES, whatsapp_provider_inputs
from wc120_whatsapp_activation import POLICIES, PREREQUISITES, activation_configuration_digest, activation_settings, main

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
DIGEST = "sha256:" + "a" * 64


def deployment() -> dict:
    config = {
        "key_vault_secret_uris": {"business-platform": "https://kv-waooaw-demo.vault.azure.net/secrets/business-platform"},
        "key_vault_secret_resource_ids": {
            "business-platform": (
                "/subscriptions/test/resourceGroups/demo/providers/Microsoft.KeyVault"
                "/vaults/kv-waooaw-demo/secrets/business-platform"
            )
        },
        "image_digests": {"business-platform": "ghcr.io/dlai-sd/business-platform@" + DIGEST},
        "whatsapp_provider": {
            "callback_host": "whatsapp-demo.example.com",
            "secret_versions": {name: "b" * 32 for name in WHATSAPP_SECRET_NAMES},
            "authority_reference": "FA:provider",
            "verification_enabled": True,
        },
    }
    return {
        **config,
        **whatsapp_provider_inputs("demo", config, {"images": config["image_digests"]}),
    }


def bundle() -> dict:
    provider = deployment()["whatsapp_provider"]
    result = {
        "schema": "waooaw.demo-whatsapp-activation/v1",
        "registration_configuration_digest": provider["configuration_digest"],
        "authority": {
            "Environment": "demo",
            "ReleaseDigest": provider["release_digest"],
            "ConfigurationDigest": provider["configuration_digest"],
            "CatalogDigest": provider["catalog_digest"],
            "RollbackDigest": DIGEST,
            "ActivationReference": "FA:activation",
            "ExternalTrafficReference": "FA:traffic",
            "ConsentReference": "consent:fixture",
            "IncidentOwnerReference": "office:operations",
            "AlertRouteReference": "alert:fixture",
            "TenantId": "12345678-1234-1234-1234-123456789abc",
            "RecipientBindingDigest": "c" * 64,
            "StartsAt": "2026-11-02T12:00:00Z",
            "ExpiresAt": "2026-11-02T12:15:00Z",
            "MaximumMessages": 5,
            "MaximumMessagesPerMinute": 2,
            "MaximumSpendInr": 10,
            "MaximumCostPerMessageInr": 1.25,
            "Revoked": False,
        },
        "binding_digests": {key: "d" * 64 for key in ("AppBindingDigest", "WabaBindingDigest", "RecipientBindingDigest")},
        "policies": {key: "policy:v1" for key in POLICIES},
        "templates": [{"Name": "demo_test", "Version": "v1", "Locale": "en_US", "Category": "UTILITY", "Body": "Hello {{1}}"}],
        "prerequisites": {
            key: {"reference": "receipt:" + key, "digest": DIGEST, "expires_at": "2026-11-02T12:15:00Z"} for key in PREREQUISITES
        },
    }
    result["authority"]["ConfigurationDigest"] = activation_configuration_digest(
        result["registration_configuration_digest"], result["binding_digests"], result["policies"], result["templates"]
    )
    return result


def prepare(value: dict, config: dict | None = None, now: datetime = NOW) -> dict[str, str]:
    raw = json.dumps(value).encode()
    return activation_settings(raw, "sha256:" + hashlib.sha256(raw).hexdigest(), config or deployment(), now)


def test_activation_binds_existing_runtime_options_without_credentials_or_provider_ids() -> None:
    result = prepare(bundle())
    assert result["WhatsAppCapability__ProviderAvailable"] == "true"
    assert result["WhatsAppCapability__Authority__ExternalTrafficReference"] == "FA:traffic"
    assert result["WhatsAppCapability__Authority__MaximumCostPerMessageInr"] == "1.25"
    assert result["WhatsAppCapability__Authority__Revoked"] == "false"
    assert result["WhatsApp__TemplateProjections__0__Body"] == "Hello {{1}}"
    assert result["WhatsApp__ApprovedTemplates__0"] == "demo_test:v1:en_US:UTILITY"
    assert result["Wc120Conversation__InstitutionalPolicyVersion"] == "policy:v1"
    assert result["Wc120Conversation__AppBindingDigest"] == "d" * 64
    assert all(
        result[f"{section}__{flag}"] == "true"
        for section in ("WhatsApp", "Wc120Conversation")
        for flag in ("CallbackAcceptanceEnabled", "DispatchEnabled")
    )
    assert not any(key.startswith("WhatsAppProvider__") for key in result)
    assert not any(word in key for key in result for word in ("PhoneNumber", "AccessToken", "AppSecret", "VerifyToken"))


def test_provisional_admission_is_default_off_and_requires_exact_bundle_permission() -> None:
    document = bundle()
    assert "WhatsAppCapability__Authority__AllowProvisionalOnboarding" not in prepare(document)
    document["authority"]["AllowProvisionalOnboarding"] = True
    raw = json.dumps(document).encode()
    approved = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert (
        activation_settings(raw, approved, deployment(), NOW)["WhatsAppCapability__Authority__AllowProvisionalOnboarding"]
        == "true"
    )
    document["authority"]["AllowProvisionalOnboarding"] = False
    with pytest.raises(ValueError, match="independently approved"):
        activation_settings(json.dumps(document).encode(), approved, deployment(), NOW)
    document["authority"]["AllowProvisionalOnboarding"] = "true"
    with pytest.raises(ValueError, match="boolean"):
        prepare(document)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("Environment", "uat"),
        ("Revoked", True),
        ("Revoked", "false"),
        ("ReleaseDigest", "sha256:" + "f" * 64),
        ("ConfigurationDigest", "sha256:" + "f" * 64),
        ("CatalogDigest", "sha256:" + "f" * 64),
        ("RollbackDigest", "latest"),
        ("ActivationReference", ""),
        ("ExternalTrafficReference", "FA:activation"),
        ("ConsentReference", ""),
        ("AlertRouteReference", ""),
        ("IncidentOwnerReference", ""),
        ("TenantId", "00000000-0000-0000-0000-000000000000"),
        ("RecipientBindingDigest", "recipient"),
        ("StartsAt", "2026-11-02T12:01:00Z"),
        ("ExpiresAt", "2026-11-02T12:00:00Z"),
        ("ExpiresAt", "2026-11-02T12:15:00"),
        ("MaximumMessages", True),
        ("MaximumMessages", 2_147_483_648),
        ("MaximumMessagesPerMinute", 6),
        ("MaximumSpendInr", 0),
        ("MaximumSpendInr", "10"),
        ("MaximumCostPerMessageInr", 11),
        ("MaximumCostPerMessageInr", 0.0000001),
    ],
)
def test_activation_denies_invalid_authority_and_exact_tuple_mismatch(key: str, value: object) -> None:
    document = bundle()
    document["authority"][key] = value
    with pytest.raises(ValueError):
        prepare(document)


@pytest.mark.parametrize("name", sorted(PREREQUISITES))
def test_activation_requires_every_current_readiness_receipt(name: str) -> None:
    document = bundle()
    del document["prerequisites"][name]
    with pytest.raises(ValueError, match="readiness"):
        prepare(document)
    document = bundle()
    document["prerequisites"][name]["expires_at"] = "2026-11-02T12:14:59Z"
    with pytest.raises(ValueError, match="entire activation"):
        prepare(document)


@pytest.mark.parametrize("mutation", ["template", "policy", "binding", "unknown", "duplicate-template"])
def test_activation_denies_incomplete_or_unsupported_configuration(mutation: str) -> None:
    document = bundle()
    if mutation == "template":
        document["templates"][0]["Header"] = "unsupported"
    elif mutation == "policy":
        del document["policies"]["PolicyVersion"]
    elif mutation == "binding":
        document["binding_digests"]["AppBindingDigest"] = ""
    elif mutation == "unknown":
        document["secret"] = "must-not-be-accepted"
    else:
        document["templates"] *= 2
    with pytest.raises(ValueError):
        prepare(document)


def test_activation_denies_self_claimed_approval_and_duplicate_json_fields() -> None:
    raw = json.dumps(bundle()).encode()
    with pytest.raises(ValueError, match="independently approved"):
        activation_settings(raw, DIGEST, deployment(), NOW)
    raw = raw.replace(b'"schema":', b'"schema":"ignored","schema":', 1)
    with pytest.raises(ValueError, match="Duplicate"):
        activation_settings(raw, "sha256:" + hashlib.sha256(raw).hexdigest(), deployment(), NOW)


@pytest.mark.parametrize("section", ["binding_digests", "policies", "templates"])
def test_activation_binds_every_runtime_projection_and_policy_setting(section: str) -> None:
    document = bundle()
    if section == "templates":
        document[section][0]["Body"] = "Changed {{1}}"
    else:
        key = next(iter(document[section]))
        document[section][key] = "f" * 64 if section == "binding_digests" else "policy:v2"
    with pytest.raises(ValueError, match="configuration digest"):
        prepare(document)


@pytest.mark.parametrize("mutation", ["version", "image", "catalog", "unverified", "foreign-vault"])
def test_activation_requires_the_registered_immutable_configuration(mutation: str) -> None:
    config = deepcopy(deployment())
    if mutation == "version":
        config["whatsapp_provider"]["secret_versions"]["whatsapp-app-secret"] = "c" * 32
    elif mutation == "image":
        config["image_digests"]["business-platform"] = "ghcr.io/dlai-sd/business-platform@sha256:" + "e" * 64
    elif mutation == "catalog":
        config["whatsapp_provider"]["catalog_digest"] = DIGEST
    elif mutation == "unverified":
        config["whatsapp_provider"]["verification_enabled"] = False
    else:
        config["key_vault_secret_uris"]["business-platform"] = "https://kv-waooaw-uat.vault.azure.net/secrets/business-platform"
    with pytest.raises(ValueError):
        prepare(bundle(), config)


def test_operator_output_is_private_create_only_and_denials_do_not_echo_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = json.dumps(bundle()).encode()
    bundle_file, deployment_file, output = (tmp_path / name for name in ("bundle.json", "deployment.json", "settings.json"))
    bundle_file.write_bytes(raw)
    deployment_file.write_text(json.dumps(deployment()))

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr("wc120_whatsapp_activation.datetime", FrozenDatetime)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "activation",
            "--bundle",
            str(bundle_file),
            "--deployment-inputs",
            str(deployment_file),
            "--approved-digest",
            "sha256:" + hashlib.sha256(raw).hexdigest(),
            "--output",
            str(output),
        ],
    )
    main()
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_text()) == prepare(bundle())
    with pytest.raises(SystemExit) as denied:
        main()
    assert denied.value.code == 1
    assert "preparation denied" in capsys.readouterr().err
    assert json.loads(output.read_text()) == prepare(bundle())
