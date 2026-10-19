from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest

from wc124_db_provisioner import (
    APPLICATION_DATABASE,
    APPLICATION_MIGRATION_ROLES,
    KEYCLOAK_DATABASE,
    TEMPORAL_DATABASE,
    TEMPORAL_VISIBILITY_DATABASE,
    application_migration_files,
    authfile_value,
    environment_specs,
    password_from_secret,
    psql,
    run,
    secret_value,
    validate_catalog,
    write_secrets,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text(encoding="utf-8"))
HANDOFF_SQL = (ROOT / "infrastructure/postgres/init/60-wc124-principal-handoff.sql").read_text(encoding="utf-8")


def test_demo_catalog_has_exact_distinct_database_credentials() -> None:
    specs = validate_catalog(CATALOG, "demo")

    assert len(specs) == 17
    assert len({spec.secret_id for spec in specs}) == 17
    assert len({spec.vault_name for spec in specs}) == 17
    assert len({spec.role for spec in specs}) == 17
    assert {spec.database for spec in specs} == {
        APPLICATION_DATABASE,
        KEYCLOAK_DATABASE,
        TEMPORAL_DATABASE,
    }


def test_uat_excludes_demo_temporal_credential() -> None:
    specs = validate_catalog(CATALOG, "uat")

    assert len(specs) == 15
    assert TEMPORAL_DATABASE not in {spec.database for spec in specs}


def test_handoff_covers_every_database_schema_and_owned_type() -> None:
    expected_schemas = {
        "constitutional": "ce_owner",
        "audit_sink": "ce_owner",
        "business": "bp_owner",
        "institutional": "bp_owner",
        "payload_store": "bp_owner",
        "domain_adapter": "bp_owner",
        "professional": "pr_owner",
        "ai_runtime": "air_owner",
        "billing": "billing_owner",
        "identity": "web_session_owner",
        "web_session": "web_session_owner",
        "keycloak": "keycloak_owner",
    }
    for schema, owner in expected_schemas.items():
        assert f"ALTER SCHEMA {schema} OWNER TO {owner};" in HANDOFF_SQL
        assert f"('{schema}', '{owner}')" in HANDOFF_SQL
    assert "t.typtype IN ('e', 'd')" in HANDOFF_SQL
    assert "'ALTER TYPE %I.%I OWNER TO %I'" in HANDOFF_SQL
    assert "('waooaw_application', 'bp_owner')" in HANDOFF_SQL
    assert "('waooaw_keycloak', 'keycloak_owner')" in HANDOFF_SQL
    assert "('waooaw_temporal', 'temporal_owner')" in HANDOFF_SQL
    assert "('waooaw_temporal_visibility', 'temporal_owner')" in HANDOFF_SQL
    assert "'ALTER DATABASE %I OWNER TO %I'" in HANDOFF_SQL


@pytest.mark.parametrize("environment", ["prod", "development", ""])
def test_unsupported_environment_is_rejected(environment: str) -> None:
    with pytest.raises(ValueError, match="demo or uat"):
        environment_specs(environment)


def test_catalog_mapping_drift_is_rejected() -> None:
    catalog = copy.deepcopy(CATALOG)
    entry = next(item for item in catalog["entries"] if item["id"] == "db-ce-runtime")
    entry["principal"] = "shared_runtime"

    with pytest.raises(ValueError, match="mapping is invalid"):
        validate_catalog(catalog, "demo")


def test_catalog_credential_omission_is_rejected() -> None:
    catalog = copy.deepcopy(CATALOG)
    catalog["entries"] = [item for item in catalog["entries"] if item["id"] != "db-bp-runtime"]

    with pytest.raises(ValueError, match="catalog mismatch"):
        validate_catalog(catalog, "demo")


def test_every_secret_value_round_trips_its_password_without_echo_metadata() -> None:
    password = "unique-password-value"
    for spec in environment_specs("demo"):
        value = secret_value(spec, password, "ca-demo-pgbouncer")

        assert password_from_secret(spec, value) == password
        assert spec.role in value if spec.value_format != "password" else value == password


def test_pgbouncer_authfile_contains_the_exact_distinct_credential_set() -> None:
    passwords = {spec.role: f"{spec.role}-password" for spec in environment_specs("demo")}
    value = authfile_value(passwords)

    assert value.count("\n") == 17
    for role, password in passwords.items():
        assert f'"{role}" "{password}"' in value


def test_existing_url_secret_is_updated_to_canonical_host_without_rotating_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = next(spec for spec in environment_specs("demo") if spec.secret_id == "db-billing-migration")
    password = "existing-billing-password"
    records = {
        spec.secret_id: {
            "id": "https://example.vault.azure.net/secrets/db-billing-migration/old-version",
            "value": secret_value(spec, password, "obsolete.internal.example"),
        }
    }
    captured: list[str] = []

    def capture(command: list[str], **_: object) -> str:
        captured.extend(command)
        return json.dumps(
            {"id": "https://example.vault.azure.net/secrets/db-billing-migration/new-version"}
        )

    monkeypatch.setattr("wc124_db_provisioner.run", capture)

    evidence = write_secrets(
        (spec,),
        {spec.role: password},
        records,
        "example",
        "ca-demo-pgbouncer",
        "grant-digest",
    )

    value_index = captured.index("--value") + 1
    assert captured[value_index] == secret_value(spec, password, "ca-demo-pgbouncer")
    assert password_from_secret(spec, captured[value_index]) == password
    assert evidence == [
        {
            "logical_secret_id": spec.secret_id,
            "role": spec.role,
            "database": spec.database,
            "vault_name": "example",
            "version_id": "new-version",
            "status": "updated",
        }
    ]


def test_existing_canonical_url_secret_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = next(spec for spec in environment_specs("demo") if spec.secret_id == "db-billing-migration")
    password = "existing-billing-password"
    existing = secret_value(spec, password, "ca-demo-pgbouncer")

    def unexpected_write(*_: object, **__: object) -> str:
        raise AssertionError("canonical secret must not be rewritten")

    monkeypatch.setattr("wc124_db_provisioner.run", unexpected_write)

    evidence = write_secrets(
        (spec,),
        {spec.role: password},
        {
            spec.secret_id: {
                "id": "https://example.vault.azure.net/secrets/db-billing-migration/current-version",
                "value": existing,
            }
        },
        "example",
        "ca-demo-pgbouncer",
        "grant-digest",
    )

    assert evidence[0]["status"] == "preserved"
    assert evidence[0]["version_id"] == "current-version"


def test_existing_password_secret_is_not_rewritten_for_host_change(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = next(spec for spec in environment_specs("demo") if spec.value_format == "password")
    password = "existing-password"

    def unexpected_write(*_: object, **__: object) -> str:
        raise AssertionError("raw password secret must not be rewritten")

    monkeypatch.setattr("wc124_db_provisioner.run", unexpected_write)

    evidence = write_secrets(
        (spec,),
        {spec.role: password},
        {
            spec.secret_id: {
                "id": f"https://example.vault.azure.net/secrets/{spec.vault_name}/current-version",
                "value": password,
            }
        },
        "example",
        "ca-demo-pgbouncer",
        "grant-digest",
    )

    assert evidence[0]["status"] == "preserved"


def test_principal_handoff_reassigns_schema_objects_to_nologin_owners() -> None:
    sql = (ROOT / "infrastructure/postgres/init/60-wc124-principal-handoff.sql").read_text(encoding="utf-8")

    for owner in (
        "ce_owner",
        "bp_owner",
        "pr_owner",
        "air_owner",
        "billing_owner",
        "web_session_owner",
    ):
        assert owner in sql
    assert "ALTER %s %I.%I OWNER TO %I" in sql
    assert "ALTER %s %s OWNER TO %I" in sql


def test_vendor_databases_use_nologin_owners_and_separate_migrators() -> None:
    source = (ROOT / "scripts/wc124_db_provisioner.py").read_text(encoding="utf-8")

    assert TEMPORAL_VISIBILITY_DATABASE in source
    assert '("keycloak_owner", "keycloak_migrator", "keycloak_runtime")' in source
    assert '"temporal_owner",' in source
    assert "ALTER DEFAULT PRIVILEGES FOR ROLE" in source
    assert "GRANT USAGE ON SCHEMA public" in source
    assert "CREATE EXTENSION IF NOT EXISTS btree_gin" in source


def test_application_migrators_assume_only_their_owner_roles() -> None:
    assert APPLICATION_MIGRATION_ROLES == {
        "ce_migrator": "ce_owner",
        "bp_migrator": "bp_owner",
        "pr_migrator": "pr_owner",
        "air_migrator": "air_owner",
        "billing_migrator": "billing_owner",
        "web_session_migrator": "web_session_owner",
    }


def test_run_preserves_stderr_without_echoing_sensitive_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="root certificate file does not exist")

    monkeypatch.setattr("wc124_db_provisioner.subprocess.run", fail)

    with pytest.raises(RuntimeError, match="psql failed with exit code 2: root certificate") as raised:
        run(["psql", "--password", "top-secret"])

    assert "top-secret" not in str(raised.value)


def test_psql_uses_the_runner_system_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def capture(
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> str:
        captured.update(command=command, env=env, stdin=stdin)
        return ""

    monkeypatch.setattr("wc124_db_provisioner.run", capture)

    psql("state.postgres.database.azure.com", "bootstrap", "application", "access-token", "SELECT 1;")

    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["PGSSLMODE"] == "verify-full"
    assert environment["PGSSLROOTCERT"] == "/etc/ssl/certs/ca-certificates.crt"
    assert environment["PGPASSWORD"] == "access-token"
    assert captured["stdin"] == "SELECT 1;"


def test_application_migrations_exclude_the_legacy_baseline() -> None:
    files = application_migration_files(ROOT / "infrastructure/postgres/init")

    assert [path.name for path in files] == [
        "59-wc124-billing-authority.sql",
        "60-wc124-principal-handoff.sql",
    ]
