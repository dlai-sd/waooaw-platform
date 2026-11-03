from __future__ import annotations

import hashlib
import json
import urllib.error
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

import wc133_whatsapp_operations as operations
from test_wc120_whatsapp_activation import bundle
from wc120_whatsapp_activation import activation_configuration_digest

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]
IMAGE = "ghcr.io/dlai-sd/business-platform@sha256:" + "a" * 64


def configuration():
    return {
        "key_vault_secret_uris": {"business-platform": "https://kv-waooaw-demo.vault.azure.net/secrets/business-platform"},
        "key_vault_secret_resource_ids": {
            "business-platform": "/subscriptions/test/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/business-platform"
        },
        "unrelated": {"preserved": True},
        "whatsapp_provider": {
            "callback_host": operations.HOST,
            "secret_versions": {name: "b" * 32 for name in operations.WHATSAPP_SECRET_NAMES},
            "authority_reference": "FA:registration",
            "verification_enabled": True,
        },
    }


def resource():
    return {
        "properties": {
            "configuration": {"ingress": {"customDomains": [{"name": operations.HOST, "bindingType": "SniEnabled"}]}},
            "template": {"containers": [{"image": IMAGE, "env": [{"name": "Unrelated", "value": "keep"}]}]},
            "latestRevisionName": "ready",
            "latestReadyRevisionName": "ready",
        }
    }


def plan(operation="register", doc=None, approved="", config=None, app=None):
    return operations.planned_settings(
        operation,
        json.dumps(doc if doc is not None else configuration()["whatsapp_provider"]).encode(),
        approved,
        config or configuration(),
        app or resource(),
        "client",
        NOW,
    )


def test_registration_is_closed_preserves_configuration_and_explicitly_denies_traffic():
    config = configuration()
    before = deepcopy(config)
    updated, settings = plan(config=config)
    assert config == before
    assert updated["unrelated"] == before["unrelated"]
    assert settings["WhatsApp__VerificationEnabled"] == "true"
    assert settings["WhatsAppProvider__ManagedIdentityClientId"] == "client"
    assert all(settings[key] == value for key, value in operations.STOP.items())
    assert not any(key.startswith("WhatsAppCapability__Authority__") for key in settings)


@pytest.mark.parametrize("field", ["appId", "phoneNumber", "token", "extra"])
def test_registration_rejects_raw_identity_credentials_and_unknown_fields(field):
    doc = configuration()["whatsapp_provider"]
    doc[field] = "not-allowed"
    with pytest.raises(ValueError, match="closed"):
        plan(doc=doc)


@pytest.mark.parametrize("change", ["active", "tls", "host", "version", "verification", "approval"])
def test_registration_preflights_every_gate_before_mutation(change):
    app = resource()
    doc = configuration()["whatsapp_provider"]
    approved = ""
    if change == "active":
        app["properties"]["template"]["containers"][0]["env"].append(
            {"name": "Wc120Conversation__DispatchEnabled", "value": "true"}
        )
    elif change == "tls":
        app["properties"]["configuration"]["ingress"]["customDomains"] = []
    elif change == "host":
        doc["callback_host"] = "api.demo.waooaw.com"
    elif change == "version":
        doc["secret_versions"]["whatsapp-verify-token"] = "latest"
    elif change == "verification":
        doc["verification_enabled"] = False
    else:
        approved = "sha256:" + "a" * 64
    with pytest.raises(ValueError):
        plan(doc=doc, app=app, approved=approved)


def test_activation_reuses_separate_exact_approval_and_never_grants_registration_authority():
    doc = bundle()
    provider = operations.deployment(configuration(), resource())["whatsapp_provider"]
    doc["registration_configuration_digest"] = provider["configuration_digest"]
    doc["authority"]["ConfigurationDigest"] = activation_configuration_digest(
        provider["configuration_digest"],
        doc["binding_digests"],
        doc["policies"],
        doc["templates"],
    )
    with pytest.raises(ValueError, match="independently approved"):
        plan("activate", doc=doc)
    raw = json.dumps(doc).encode()
    approved = "sha256:" + hashlib.sha256(raw).hexdigest()
    _, settings = plan("activate", doc=doc, approved=approved)
    assert settings["WhatsApp__DispatchEnabled"] == "true"
    assert "WhatsAppProvider__Enabled" not in settings
    doc["authority"]["MaximumMessages"] += 1
    with pytest.raises(ValueError, match="independently approved"):
        plan("activate", doc=doc, approved=approved)


@pytest.mark.parametrize("operation", ["stop", "status"])
def test_stop_and_status_require_no_valid_registration_or_activation(operation):
    _, settings = plan(operation, doc={}, config={"unrelated": "preserved"})
    assert settings == (operations.STOP if operation == "stop" else {})
    with pytest.raises(ValueError, match="accepts no"):
        plan(operation, doc={"secret": "rejected"})


def test_stop_preparation_does_not_depend_on_storage(monkeypatch, tmp_path):
    commands = []

    def az(*args):
        commands.append(args)
        if args[:2] == ("identity", "show"):
            return {"clientId": "client", "principalId": "principal"}
        pytest.fail("Stop must not call storage")

    monkeypatch.setattr(operations, "app", resource)
    monkeypatch.setattr(operations, "az", az)
    operations.prepare(tmp_path, "stop", b"{}", "")
    assert not any("storage" in command for command in commands)
    assert json.loads((tmp_path / "plan.json").read_text())["settings"] == operations.STOP
    assert (tmp_path / "plan.json").stat().st_mode & 0o777 == 0o600


def test_persist_backs_up_before_conditional_write_and_checks_readback(monkeypatch, tmp_path):
    before = {"unrelated": "preserved"}
    after = {**before, "whatsapp_provider": configuration()["whatsapp_provider"]}
    operations.private_json(tmp_path / "plan.json", {"operation": "register", "etag": '"old"'})
    operations.private_json(tmp_path / "configuration.before.json", before)
    operations.private_json(tmp_path / "configuration.after.json", after)
    commands = []

    def az(*args):
        commands.append(args)
        if args[:3] == ("storage", "blob", "show"):
            return {"properties": {"etag": '"new"'}}
        if args[:3] == ("storage", "blob", "download"):
            Path(args[args.index("--file") + 1]).write_text(json.dumps(after))
        return {}

    monkeypatch.setattr(operations, "az", az)
    operations.persist(tmp_path, "123-1")
    uploads = [command for command in commands if command[:3] == ("storage", "blob", "upload")]
    assert uploads[0][uploads[0].index("--name") + 1].endswith("/configuration.before.json")
    assert uploads[0][uploads[0].index("--overwrite") + 1] == "false"
    assert uploads[1][uploads[1].index("--if-match") + 1] == '"old"'
    assert json.loads((tmp_path / "configuration.verified.json").read_text()) == after


def test_conditional_storage_conflict_stops_without_an_unconditional_retry(monkeypatch, tmp_path):
    operations.private_json(tmp_path / "plan.json", {"operation": "register", "etag": '"stale"'})
    operations.private_json(tmp_path / "configuration.before.json", {"old": True})
    operations.private_json(tmp_path / "configuration.after.json", {"new": True})
    commands = []

    def az(*args):
        commands.append(args)
        if "--if-match" in args:
            raise RuntimeError("Azure operation failed: storage blob upload")
        return {}

    monkeypatch.setattr(operations, "az", az)
    with pytest.raises(RuntimeError, match="upload"):
        operations.persist(tmp_path, "123-1")
    assert len(commands) == 2
    assert sum("--if-match" in command for command in commands) == 1


@pytest.mark.parametrize("reason", ["disabled", "expired", "not-started", "no-expiry", "absent"])
def test_metadata_validation_never_reads_secret_values(monkeypatch, reason):
    attributes = {"enabled": True, "exp": int(NOW.timestamp()) + 600}
    if reason == "disabled":
        attributes["enabled"] = False
    elif reason == "expired":
        attributes["exp"] = int(NOW.timestamp())
    elif reason == "not-started":
        attributes["nbf"] = int(NOW.timestamp()) + 10
    elif reason == "no-expiry":
        attributes.pop("exp")

    def az(*args):
        url = args[args.index("--url") + 1]
        assert "/versions?" in url
        return {"value": [] if reason == "absent" else [{"id": "https://vault/secret/" + "b" * 32, "attributes": attributes}]}

    monkeypatch.setattr(operations, "az", az)
    with pytest.raises(ValueError):
        operations.validate_versions({"whatsapp-verify-token": "b" * 32}, NOW)


def test_outbound_no_expiry_is_the_only_metadata_exception(monkeypatch):
    monkeypatch.setattr(
        operations,
        "az",
        lambda *args: {"value": [{"id": "https://vault/secret/" + "b" * 32, "attributes": {"enabled": True, "nbf": None}}]},
    )
    operations.validate_versions({"whatsapp-outbound-authority": "b" * 32}, NOW)


def test_callback_probe_uses_tls_and_only_invalid_verification_token(monkeypatch):
    def urlopen(request, **kwargs):
        assert request.full_url.startswith("https://" + operations.HOST)
        assert request.get_method() in ("GET", "POST")
        if request.get_method() == "POST":
            assert request.data == b"{}"
        raise urllib.error.HTTPError(request.full_url, 401 if request.get_method() == "GET" else 503, "expected", {}, None)

    monkeypatch.setattr(operations.urllib.request, "urlopen", urlopen)
    operations.probe_callback("register")
    operations.probe_callback("activate")


def test_callback_unexpected_success_does_not_count_as_verified(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    monkeypatch.setattr(operations.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="invalid verification"):
        operations.probe_callback("status")


def test_provider_workflow_bypasses_terraform_but_retains_existing_runner_cleanup():
    wrapper = yaml.safe_load((ROOT / ".github/workflows/deploy.yaml").read_text())
    engine = yaml.safe_load((ROOT / ".github/workflows/environment-deployment.yaml").read_text())
    jobs = engine["jobs"]
    assert jobs["terraform"]["if"] == "inputs.provider_operation == 'none'"
    assert jobs["provider-operation"]["if"] == "inputs.provider_operation != 'none'"
    assert "provider-operation" in jobs["cleanup-private"]["needs"]
    provider = jobs["provider-operation"]
    assert provider["runs-on"] == jobs["terraform"]["runs-on"]
    assert provider["environment"] == "demo"
    steps = provider["steps"]
    assert any(step.get("if") == "always()" and step["name"] == "Remove private operation files" for step in steps)
    evidence = next(step for step in steps if step.get("name") == "Retain redacted provider evidence only")
    assert evidence["with"]["path"].endswith("/evidence-*.json")
    assert wrapper["jobs"]["deploy"]["with"]["provider_operation"]
    assert wrapper["concurrency"]["group"] == "goal006-${{ inputs.environment || 'demo' }}-deployment"


@pytest.mark.parametrize("configuration_drift", [False, True])
def test_runtime_apply_preserves_unrelated_settings_and_denies_configuration_drift(monkeypatch, tmp_path, configuration_drift):
    current = resource()
    current["properties"]["template"]["containers"][0]["env"].extend(
        [
            {"name": "Database", "secretRef": "existing-secret"},
            {"name": "WhatsApp__TemplateProjections__7__Body", "value": "obsolete"},
        ]
    )
    config = configuration()
    document = json.dumps(config["whatsapp_provider"]).encode()
    _, settings = operations.planned_settings("register", document, "", config, current, "client", NOW)
    operations.private_json(
        tmp_path / "plan.json",
        {
            "operation": "register",
            "image": IMAGE,
            "settings": settings,
            "principal_id": "principal",
            "approved_digest": "",
        },
    )
    operations.private_json(tmp_path / "configuration.after.json", config)
    (tmp_path / "document.raw").write_bytes(document)
    commands = []

    def az(*args):
        commands.append(args)
        if args[:2] == ("identity", "show"):
            return {"clientId": "client", "principalId": "principal"}
        if args[:3] == ("storage", "blob", "show"):
            return {"properties": {"etag": '"current"'}}
        if args[:3] == ("storage", "blob", "download"):
            persisted = deepcopy(config)
            if configuration_drift:
                persisted["concurrent_update"] = True
            Path(args[args.index("--file") + 1]).write_text(json.dumps(persisted))
            return {}
        if args[:3] == ("role", "assignment", "list"):
            return [{"roleDefinitionName": "Key Vault Secrets User"}]
        if args[:2] == ("containerapp", "update"):
            entries = current["properties"]["template"]["containers"][0]["env"]
            entries[:] = [entry for entry in entries if entry["name"] != "WhatsApp__TemplateProjections__7__Body"]
            entries.extend({"name": key, "value": value} for key, value in settings.items())
            return {}
        pytest.fail(f"Unexpected operation class {args[:2]}")

    monkeypatch.setattr(operations, "app", lambda: deepcopy(current))
    monkeypatch.setattr(operations, "az", az)
    monkeypatch.setattr(operations, "validate_versions", lambda *args: None)
    retired = []
    monkeypatch.setattr(operations, "reconcile_revisions", lambda *args, **kwargs: retired.append(kwargs["selected_apps"]))
    if configuration_drift:
        with pytest.raises(RuntimeError, match="configuration changed"):
            operations.apply_settings(tmp_path)
        assert not any(command[:2] == ("containerapp", "update") for command in commands)
        assert retired == []
        return
    operations.apply_settings(tmp_path)
    assert retired == [[operations.APP]]
    update = next(command for command in commands if command[:2] == ("containerapp", "update"))
    assert update[update.index("--remove-env-vars") + 1 :] == ("WhatsApp__TemplateProjections__7__Body",)
    assert "Database" not in update and "Unrelated" not in update
    assert any(
        entry == {"name": "Database", "secretRef": "existing-secret"}
        for entry in current["properties"]["template"]["containers"][0]["env"]
    )


def test_image_drift_denies_apply_before_any_mutation(monkeypatch, tmp_path):
    operations.private_json(tmp_path / "plan.json", {"operation": "stop", "image": IMAGE + "changed"})
    monkeypatch.setattr(operations, "app", resource)
    monkeypatch.setattr(operations, "az", lambda *args: pytest.fail("No mutations are allowed"))
    with pytest.raises(ValueError, match="image changed"):
        operations.apply_settings(tmp_path)


@pytest.mark.parametrize("stuck_replicas", [False, True])
def test_cleanup_targets_only_four_temporary_grants_and_confirms_zero_intake_replicas(monkeypatch, stuck_replicas):
    deleted = set()
    inactive = set()
    commands = []

    def az(*args):
        commands.append(args)
        if args[:2] == ("identity", "show"):
            return {"principalId": "intake-principal"}
        if args[:2] == ("keyvault", "show"):
            return {"id": "/vaults/kv-waooaw-demo"}
        if args[:3] == ("role", "assignment", "list"):
            scope = args[args.index("--scope") + 1]
            assert args[args.index("--assignee") + 1] == "intake-principal"
            return (
                []
                if scope in deleted
                else [
                    {"id": scope, "scope": scope, "roleDefinitionName": "WAOOAW Key Vault Declared Secret Provisioner"},
                    {"id": "unrelated", "scope": "/vaults/other", "roleDefinitionName": "Contributor"},
                ]
            )
        if args[:3] == ("role", "assignment", "delete"):
            deleted.add(args[-1])
        elif args[:3] == ("containerapp", "revision", "list"):
            return [{"name": "intake-revision", "properties": {"active": "intake-revision" not in inactive}}]
        elif args[:3] == ("containerapp", "revision", "deactivate"):
            inactive.add(args[-1])
        elif args[:3] == ("containerapp", "revision", "show"):
            return {"properties": {"active": False, "replicas": 1 if stuck_replicas else 0}}
        elif args[:2] != ("containerapp", "update"):
            pytest.fail(f"Unexpected cleanup operation {args[:3]}")
        return {}

    monkeypatch.setattr(operations, "az", az)
    if stuck_replicas:
        ticks = iter([0, 121])
        monkeypatch.setattr(operations.time, "monotonic", lambda: next(ticks))
        with pytest.raises(RuntimeError, match="still has active replicas"):
            operations.cleanup_intake()
    else:
        operations.cleanup_intake()
    assert deleted == {"/vaults/kv-waooaw-demo/secrets/" + name for name in operations.WHATSAPP_SECRET_NAMES}
    for command in commands:
        if command[0] == "containerapp":
            assert command[command.index("--name") + 1] == "goal006-demo-runner-key-import"


def test_next_deployment_adopts_existing_tls_and_scoped_roles_without_recreation(monkeypatch, tmp_path):
    config = operations.deployment(configuration(), resource())
    operations.private_json(tmp_path / "workload.auto.tfvars.json", config)
    current = resource()
    current["id"] = "/subscriptions/test/resourceGroups/demo/providers/Microsoft.App/containerApps/ca-demo-business-platform"
    monkeypatch.setattr(operations, "app", lambda: current)
    monkeypatch.setattr(operations, "reconcile_revisions", lambda *args, **kwargs: {})

    def az(*args):
        if args[:2] == ("identity", "show"):
            return {"principalId": "bp"}
        scope = args[args.index("--scope") + 1]
        return [
            {"id": scope + "/assignment", "scope": scope, "principalId": "bp", "roleDefinitionName": "Key Vault Secrets User"}
        ]

    calls = []

    def terraform(*args):
        calls.append(args)
        return "" if args[-1] == "list" else "imported"

    monkeypatch.setattr(operations, "az", az)
    monkeypatch.setattr(operations, "terraform", terraform)
    operations.adopt(tmp_path)
    assert len(calls) == 6
    assert any(command[-1].endswith("/customDomainName/" + operations.HOST) for command in calls)
    addresses = {command[-2] for command in calls[1:]}
    monkeypatch.setattr(
        operations, "terraform", lambda *args: "\n".join(addresses) if args[-1] == "list" else pytest.fail("Already managed")
    )
    operations.adopt(tmp_path)


def test_azure_failure_never_exports_cli_output_or_private_inputs(monkeypatch):
    import subprocess

    monkeypatch.setattr(operations.shutil, "which", lambda _: "/usr/bin/az")
    monkeypatch.setattr(
        operations.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "SECRET", "SECRET")
    )
    with pytest.raises(RuntimeError, match="Azure operation failed") as failure:
        operations.az("containerapp", "update", "--name", operations.APP, "--set-env-vars", "key=SECRET")
    assert "SECRET" not in str(failure.value)


@pytest.mark.parametrize("containment_fails", [False, True, "revisions", "not-ready"])
def test_activation_failure_reports_failure_and_confirms_or_escalates_traffic_closure(
    monkeypatch, tmp_path, capsys, containment_fails
):
    import sys

    operations.private_json(tmp_path / "plan.json", {"operation": "activate"})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "operation",
            "apply",
            "--operation",
            "activate",
            "--directory",
            str(tmp_path),
            "--run",
            "123-1",
        ],
    )
    monkeypatch.setattr(operations, "apply_settings", lambda _: (_ for _ in ()).throw(RuntimeError("Revision failed")))
    current = resource()
    current["properties"]["template"]["containers"][0]["env"] = [
        {"name": key, "value": value} for key, value in operations.STOP.items()
    ]
    if containment_fails == "not-ready":
        current["properties"]["latestReadyRevisionName"] = "previous"

    def az(*args):
        assert args[:2] == ("containerapp", "update")
        for key, value in operations.STOP.items():
            assert f"{key}={value}" in args
        if containment_fails is True:
            raise RuntimeError("Closure failed")
        return {}

    def retire(*args, **kwargs):
        assert kwargs["selected_apps"] == [operations.APP]
        if containment_fails == "revisions":
            raise RuntimeError("Old workers still running")
        return {}

    monkeypatch.setattr(operations, "az", az)
    monkeypatch.setattr(operations, "app", lambda: current)
    monkeypatch.setattr(operations, "reconcile_revisions", retire)
    assert operations.main() == 1
    evidence = json.loads((tmp_path / "evidence-apply.json").read_text())
    assert evidence["status"] == "FAILED"
    assert evidence["containment"] == ("UNCONFIRMED_REQUIRES_OPERATOR" if containment_fails else "TRAFFIC_CLOSED")
    assert ("CRITICAL" in capsys.readouterr().out) is bool(containment_fails)


def test_registration_prepare_preserves_existing_numeric_configuration(monkeypatch, tmp_path):
    config = configuration()
    config["pricing"] = {"rate": 1.25}
    monkeypatch.setattr(operations, "app", resource)

    def az(*args):
        if args[:2] == ("identity", "show"):
            return {"clientId": "client", "principalId": "principal"}
        if args[:3] == ("storage", "blob", "show"):
            return {"properties": {"etag": '"old"'}}
        assert args[:3] == ("storage", "blob", "download")
        Path(args[args.index("--file") + 1]).write_text(json.dumps(config))
        return {}

    monkeypatch.setattr(operations, "az", az)
    operations.prepare(tmp_path, "register", json.dumps(config["whatsapp_provider"]).encode(), "")
    assert json.loads((tmp_path / "configuration.after.json").read_text())["pricing"] == {"rate": 1.25}
