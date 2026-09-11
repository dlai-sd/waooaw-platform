# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §§4-5, 9-11
# Constitutional basis: C-023, C-059, C-063, C-080

import copy
import json

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
    rendered = json.loads(
        (wc091_environment.ROOT / "infrastructure/environment-readiness/demo.rendered.json").read_text()
    )
    identity_module = (
        wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/identity.tf"
    ).read_text()

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
    assert "filesha256(\"../../../../../environment-readiness/demo.rendered.json\")" in demo


def test_readiness_outcomes_are_independent_and_missing_evidence_is_not_proven() -> None:
    rendered = wc091_environment.validate_and_render("demo")
    metadata = [
        {"id": binding["id"], "enabled": True, "expired": False}
        for binding in rendered["secretBindings"]
    ]
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
            command, 0, '{"value":[{"id":"https://vault/secrets/demo-founder-bootstrap/version-1"}]}', "")

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
            command, 0, '{"id":"https://vault/secrets/meta-login-client-secret/version-2"}', "")

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
    module = (wc091_environment.ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()

    for marker in ("WC091_GENERATION_ID", "WC091_FIXTURE_DIGEST", "wc091_demo_generation"):
        assert marker in reset
        assert marker in verifier
        assert marker in module
    assert 'rm -rf "${PGDATA:?}"/*' in reset
    assert "docker restart" in verifier
    assert '"priorGenerationReachable": false' in verifier