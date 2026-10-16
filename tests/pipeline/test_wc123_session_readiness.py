"""WC-123 session environment, secret lifecycle, and readiness contracts."""

# Implements: CSA-AUTH-001 Sections 12.6-12.7; WC-123 AUTH-WC-02
# Constitutional basis: C-023, C-059, C-063, C-080

import copy
import json

import pytest

from scripts import wc091_environment


ROOT = wc091_environment.ROOT
CATALOG_PATH = ROOT / "infrastructure/environment-readiness/secret-catalog.json"
PROFILE_PATH = (
    ROOT / "architecture/reference/components/authentication-authorization-capacity-profile.v1.yaml"
)


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_demo_and_uat_bind_exact_session_authority_modes_and_capacity() -> None:
    expected = {
        "demo": ("DISPOSABLE_RESET", 30),
        "uat": ("PERSISTENT_SANITIZED_RESTORE", 300),
    }

    for environment, (mode, concurrency) in expected.items():
        manifest = load_json(f"infrastructure/identity-config/environments/{environment}.json")
        session = manifest["sessionAuthority"]

        assert session["contractVersion"] == "1.0.0"
        assert session["mode"] == mode
        assert session["schemaVersion"] == 1
        assert session["compatibleDeployVersions"] == ["wc123-auth-session-v1"]
        assert session["cookieName"] == "__Host-waooaw-session"
        assert session["idleTimeoutMinutes"] == 30
        assert session["absoluteLifetimeHours"] == 8
        assert session["refreshLeaseSeconds"] == 15
        assert session["operationalRetentionDays"] == 30
        assert session["protocolRetentionHours"] == 24
        assert session["backupRetentionDays"] == 35
        assert session["rpoMinutes"] == 5
        assert session["rtoMinutes"] == 30
        assert session["databasePoolSize"] == 5
        assert session["globalConcurrency"] == concurrency
        assert set(session["keyVersions"].values()) == {"v1"}


def test_session_secrets_are_closed_world_versioned_and_retirement_guarded() -> None:
    catalog = load_json("infrastructure/environment-readiness/secret-catalog.json")
    entries = {entry["id"]: entry for entry in catalog["entries"]}
    required = {
        "web-session-handle-digest",
        "web-session-protocol-digest",
        "web-session-token-envelope",
        "web-session-database",
        "web-oidc-client",
        "keycloak-lifecycle-writer-client",
    }

    for environment in ("demo", "uat"):
        manifest = load_json(f"infrastructure/identity-config/environments/{environment}.json")
        assert set(manifest["sessionAuthority"]["requiredSecretIds"]) == required
        assert required <= {
            entry["id"] for entry in catalog["entries"] if environment in entry["environments"]
        }

    for secret_id in required - {"web-oidc-client"}:
        entry = entries[secret_id]
        assert 0 < entry["rotationCadenceDays"] <= 90
        assert 0 <= entry["maximumOverlapHours"] <= 24
        assert entry["expiresAfterDays"] > entry["rotationCadenceDays"]
        assert entry["retirementGuard"]
        assert entry["compromiseAction"]
        assert entry["allowedOperations"] == ["get"]

    for secret_id in (
        "web-session-handle-digest",
        "web-session-protocol-digest",
        "web-session-token-envelope",
    ):
        assert entries[secret_id]["principal"] == "web"
    assert entries["web-session-database"]["principal"] == "web"
    assert entries["web-session-database"]["consumers"] == ["web:WEB_SESSION_DATABASE_URL"]


def test_authentication_limiter_secrets_are_not_session_mode_gated() -> None:
    entries = {
        entry["id"]: entry
        for entry in load_json("infrastructure/environment-readiness/secret-catalog.json")["entries"]
    }

    assert entries["auth-abuse-digest-key"]["requiredWhen"] == "web authentication enabled"
    assert entries["auth-abuse-redis-password"]["requiredWhen"] == "web authentication enabled"
    assert entries["auth-abuse-digest-key"]["consumers"] == ["web:AUTH_ABUSE_DIGEST_KEY"]
    assert entries["auth-abuse-redis-password"]["consumers"] == [
        "web:REDIS_PASSWORD",
        "auth-redis:REDIS_PASSWORD",
    ]
    assert entries["auth-abuse-redis-managed-key"]["consumers"] == ["web:REDIS_PASSWORD"]
    assert entries["auth-abuse-redis-managed-key"]["environments"] == ["prod"]


def test_checked_in_demo_and_uat_renders_are_current_and_secret_free() -> None:
    for environment in ("demo", "uat"):
        rendered = load_json(f"infrastructure/environment-readiness/{environment}.rendered.json")

        assert rendered == wc091_environment.validate_and_render(environment)
        serialized = json.dumps(rendered)
        assert "__Host-waooaw-session" in serialized
        assert "SESSION_TOKEN_ENVELOPE_KEYS" in serialized
        assert "clientSecret" not in serialized


def test_missing_session_secret_and_unknown_contract_version_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = wc091_environment._load

    def load_without_required_secret(path):
        value = original(path)
        if path.name == "secret-catalog.json":
            value = copy.deepcopy(value)
            value["entries"] = [
                entry for entry in value["entries"] if entry["id"] != "web-session-token-envelope"
            ]
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_without_required_secret)
    with pytest.raises(wc091_environment.ContractError, match="no declared environment secret"):
        wc091_environment.validate_and_render("demo")

    def load_with_unknown_version(path):
        value = original(path)
        if path.name == "demo.json":
            value = copy.deepcopy(value)
            value["sessionAuthority"]["contractVersion"] = "2.0.0"
        return value

    monkeypatch.setattr(wc091_environment, "_load", load_with_unknown_version)
    with pytest.raises(wc091_environment.ContractError, match="1.0.0"):
        wc091_environment.validate_and_render("demo")
