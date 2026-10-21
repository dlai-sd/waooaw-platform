from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from wc124_db_provisioner import (
    APPLICATION_DATABASE,
    APPLICATION_MIGRATION_ROLES,
    INIT_CHAIN_LEDGER_TABLE,
    IDENTITY_POLICY_CONTRACT,
    KEYCLOAK_DATABASE,
    TEMPORAL_DATABASE,
    TEMPORAL_VISIBILITY_DATABASE,
    application_migration_files,
    apply_init_chain,
    authfile_value,
    await_vault_authorization,
    environment_specs,
    execute,
    existing_grant_digest,
    password_from_secret,
    probe_pgbouncer_connectivity,
    psql,
    run,
    secret_value,
    validate_catalog,
    verify_identity_schema,
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
        return json.dumps({"id": "https://example.vault.azure.net/secrets/db-billing-migration/new-version"})

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


def test_existing_credentials_require_one_shared_grant_digest() -> None:
    records = {
        "first": {"tags": {"wc124-grant-digest": "digest-a"}},
        "second": {"tags": {"wc124-grant-digest": "digest-a"}},
    }

    assert existing_grant_digest(records) == "digest-a"

    records["second"] = {"tags": {"wc124-grant-digest": "digest-b"}}
    with pytest.raises(ValueError, match="share one non-empty grant digest"):
        existing_grant_digest(records)


def test_refresh_only_rewrites_urls_without_database_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "secret-catalog.json"
    catalog_path.write_text(json.dumps(CATALOG), encoding="utf-8")
    specs = environment_specs("demo")
    passwords = {spec.role: f"{spec.role}-password" for spec in specs}
    records = {
        spec.secret_id: {
            "id": f"https://example.vault.azure.net/secrets/{spec.vault_name}/version",
            "tags": {
                "wc124-role": spec.role,
                "wc124-database": spec.database,
                "wc124-grant-digest": "shared-grant-digest",
            },
            "value": secret_value(spec, passwords[spec.role], "obsolete.internal.example"),
        }
        for spec in specs
    }
    logins: list[str] = []
    writes: list[tuple[str, str]] = []

    monkeypatch.setattr("wc124_db_provisioner.azure_login", logins.append)
    monkeypatch.setattr("wc124_db_provisioner.await_vault_authorization", lambda _vault: 3)
    monkeypatch.setattr(
        "wc124_db_provisioner.read_credentials",
        lambda *_args, **kwargs: (
            (
                passwords,
                records,
            )
            if kwargs == {"require_existing": True}
            else pytest.fail("refresh must require every existing credential")
        ),
    )
    monkeypatch.setattr(
        "wc124_db_provisioner.write_secrets",
        lambda _specs, _passwords, _records, vault, host, grant: (
            writes.append((host, grant))
            or [
                {
                    "logical_secret_id": "db-billing-migration",
                    "status": "updated",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "wc124_db_provisioner.provision_postgresql",
        lambda *_args, **_kwargs: pytest.fail("refresh must not use database bootstrap authority"),
    )

    result = execute(
        SimpleNamespace(
            catalog=catalog_path,
            environment="demo",
            provisioner_client_id="provisioner-client",
            vault_name="kv-waooaw-demo",
            pgbouncer_host="ca-demo-pgbouncer",
            refresh_existing_urls=True,
        )
    )

    assert logins == ["provisioner-client"]
    assert writes == [("ca-demo-pgbouncer", "shared-grant-digest")]
    assert result["mode"] == "canonical-url-refresh"
    assert result["vault_authorization_attempts"] == 3
    assert result["credentials"][0]["status"] == "updated"


def test_vault_authorization_retries_propagation_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        (
            subprocess.CompletedProcess([], 1, stdout="", stderr="ForbiddenByRbac"),
            subprocess.CompletedProcess([], 1, stdout="", stderr="Forbidden"),
            subprocess.CompletedProcess([], 0, stdout="secret-id\n", stderr=""),
        )
    )
    sleeps: list[float] = []
    monkeypatch.setattr("wc124_db_provisioner.shutil.which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr("wc124_db_provisioner.subprocess.run", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr("wc124_db_provisioner.time.sleep", sleeps.append)

    assert await_vault_authorization("kv-waooaw-demo", attempts=3, delay_seconds=2) == 3
    assert sleeps == [2, 2]


def test_vault_authorization_fails_closed_after_bounded_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wc124_db_provisioner.shutil.which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr(
        "wc124_db_provisioner.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, stdout="", stderr="ForbiddenByRbac"),
    )
    monkeypatch.setattr("wc124_db_provisioner.time.sleep", lambda _delay: None)

    with pytest.raises(RuntimeError, match="did not become effective after 2 attempts"):
        await_vault_authorization("kv-waooaw-demo", attempts=2, delay_seconds=0)


def test_vault_authorization_rejects_unexpected_probe_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wc124_db_provisioner.shutil.which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr(
        "wc124_db_provisioner.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, stdout="", stderr="Network unreachable"),
    )

    with pytest.raises(RuntimeError, match="non-authorization error"):
        await_vault_authorization("kv-waooaw-demo", attempts=2, delay_seconds=0)


def test_pgbouncer_probe_requires_same_environment_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wc124_db_provisioner.socket.getaddrinfo",
        lambda *_args, **_kwargs: pytest.fail("invalid host must fail before DNS"),
    )

    with pytest.raises(ValueError, match="ca-demo-pgbouncer"):
        probe_pgbouncer_connectivity("demo", "stale.internal.example")


def test_pgbouncer_probe_proves_dns_and_tcp(monkeypatch: pytest.MonkeyPatch) -> None:
    connections: list[tuple[tuple[str, int], float]] = []

    class Connection:
        def __enter__(self) -> Connection:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(
        "wc124_db_provisioner.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (2, 1, 6, "", ("100.100.230.37", 5432)),
            (2, 1, 6, "", ("100.100.230.37", 5432)),
        ],
    )
    monkeypatch.setattr(
        "wc124_db_provisioner.socket.create_connection",
        lambda endpoint, timeout: connections.append((endpoint, timeout)) or Connection(),
    )

    evidence = probe_pgbouncer_connectivity("demo", "ca-demo-pgbouncer", timeout_seconds=3)

    assert evidence == {
        "schema": "waooaw.wc124-pgbouncer-connectivity/v1",
        "environment": "demo",
        "host": "ca-demo-pgbouncer",
        "port": 5432,
        "resolved_addresses": ["100.100.230.37"],
        "tcp": "connected",
    }
    assert connections == [(("ca-demo-pgbouncer", 5432), 3)]


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


def test_application_migrations_cover_the_whole_sql_chain_after_the_principal_bootstrap() -> None:
    init_directory = ROOT / "infrastructure/postgres/init"
    files = application_migration_files(init_directory)
    names = [path.name for path in files]

    assert "00-wc124-principal-bootstrap.sql" not in names
    assert names == sorted(names, key=lambda name: name.encode())
    assert names[0] == "01-schemas.sql"
    assert names[-2:] == ["59-wc124-billing-authority.sql", "60-wc124-principal-handoff.sql"]
    assert all(name.endswith(".sql") for name in names)
    assert sorted(path.name for path in init_directory.glob("*.sh")) == [
        "02-users-and-permissions.sh",
        "42-demo-marketplace-admission.sh",
    ]


def test_application_migrations_require_the_principal_bootstrap(tmp_path: Path) -> None:
    (tmp_path / "01-schemas.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(ValueError, match="principal bootstrap file is missing"):
        application_migration_files(tmp_path)


def _ledger_psql(ledger: dict[str, str], calls: list[str]):
    def fake_psql(_server, _bootstrap, _database, _token, sql, *, tuples_only=False):
        calls.append(sql)
        if tuples_only:
            return "".join(f"{name}\t{digest}\n" for name, digest in sorted(ledger.items()))
        if sql.startswith(f"INSERT INTO {INIT_CHAIN_LEDGER_TABLE}"):
            name = sql.split("VALUES ('", 1)[1].split("'", 1)[0]
            digest = sql.split("', '", 1)[1].split("'", 1)[0]
            ledger[name] = digest
        return ""

    return fake_psql


def test_init_chain_ledger_applies_only_changed_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    first = tmp_path / "01-schemas.sql"
    second = tmp_path / "02-tables.sql"
    first.write_text("CREATE SCHEMA IF NOT EXISTS a;", encoding="utf-8")
    second.write_text("CREATE TABLE IF NOT EXISTS a.t (id int);", encoding="utf-8")
    ledger: dict[str, str] = {}
    calls: list[str] = []
    monkeypatch.setattr("wc124_db_provisioner.psql", _ledger_psql(ledger, calls))

    run_one = apply_init_chain("fqdn", "bootstrap", "token", (first, second))
    assert run_one == {"applied": ["01-schemas.sql", "02-tables.sql"], "reapplied": [], "skipped": []}
    assert calls[0].lstrip().startswith("CREATE SCHEMA IF NOT EXISTS wc124_provisioning")
    assert calls.count(first.read_text(encoding="utf-8")) == 1

    calls.clear()
    run_two = apply_init_chain("fqdn", "bootstrap", "token", (first, second))
    assert run_two == {"applied": [], "reapplied": [], "skipped": ["01-schemas.sql", "02-tables.sql"]}
    assert not any(call.startswith("CREATE SCHEMA IF NOT EXISTS a") for call in calls)

    second.write_text("CREATE TABLE IF NOT EXISTS a.t (id int, name text);", encoding="utf-8")
    calls.clear()
    with pytest.raises(ValueError, match=r"init-chain integrity failure.*02-tables\.sql"):
        apply_init_chain("fqdn", "bootstrap", "token", (first, second))
    assert second.read_text(encoding="utf-8") not in calls
    assert first.read_text(encoding="utf-8") not in calls

    run_four = apply_init_chain("fqdn", "bootstrap", "token", (first, second), force=True)
    assert run_four["reapplied"] == ["01-schemas.sql", "02-tables.sql"]


def test_init_chain_ledger_rows_are_written_after_each_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    only = tmp_path / "01-schemas.sql"
    only.write_text("CREATE SCHEMA IF NOT EXISTS a;", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr("wc124_db_provisioner.psql", _ledger_psql({}, calls))

    apply_init_chain("fqdn", "bootstrap", "token", (only,))

    file_index = calls.index(only.read_text(encoding="utf-8"))
    ledger_write = calls[file_index + 1]
    assert ledger_write.startswith(f"INSERT INTO {INIT_CHAIN_LEDGER_TABLE}")
    assert "ON CONFLICT (file_name) DO UPDATE" in ledger_write
    assert "'01-schemas.sql'" in ledger_write


def test_identity_schema_verifier_requires_every_relation_policy_and_forced_rls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = "\n".join(
        "\t".join(
            (
                name,
                "t",
                "t",
                "t",
                "1",
                "1",
                "PERMISSIVE",
                "ALL",
                ",".join(sorted(contract.roles)),
                contract.expression,
                contract.expression,
            )
        )
        for name, contract in sorted(IDENTITY_POLICY_CONTRACT.items())
    )
    monkeypatch.setattr("wc124_db_provisioner.psql", lambda *_args, **_kwargs: rows)

    evidence = verify_identity_schema("fqdn", "bootstrap", "token")

    assert evidence["status"] == "passed"
    assert len(evidence["relations"]) == 6


def test_identity_schema_verifier_fails_when_one_policy_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = "\n".join(
        f"{name}\tt\tt\tt\t{'0' if name == 'memberships' else '1'}\t1\tPERMISSIVE\tALL\t"
        f"business_app\tactor_bindings account_id\tactor_bindings account_id"
        for name in (
            "accounts",
            "actor_bindings",
            "idempotency_ledger",
            "login_methods",
            "memberships",
            "registrations",
        )
    )
    monkeypatch.setattr("wc124_db_provisioner.psql", lambda *_args, **_kwargs: rows)

    with pytest.raises(ValueError, match="memberships"):
        verify_identity_schema("fqdn", "bootstrap", "token")


def test_identity_schema_verifier_rejects_semantically_permissive_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = "\n".join(
        "\t".join(
            (
                name,
                "t",
                "t",
                "t",
                "1",
                "1",
                "PERMISSIVE",
                "ALL",
                ",".join(sorted(contract.roles)),
                f"(true OR {contract.expression})" if name == "memberships" else contract.expression,
                f"(true OR {contract.expression})" if name == "memberships" else contract.expression,
            )
        )
        for name, contract in sorted(IDENTITY_POLICY_CONTRACT.items())
    )
    monkeypatch.setattr("wc124_db_provisioner.psql", lambda *_args, **_kwargs: rows)

    with pytest.raises(ValueError, match="memberships"):
        verify_identity_schema("fqdn", "bootstrap", "token")


def test_identity_schema_verifier_rejects_additional_permissive_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = "\n".join(
        "\t".join(
            (
                name,
                "t",
                "t",
                "t",
                "1",
                "2" if name == "memberships" else "1",
                "PERMISSIVE",
                "ALL",
                ",".join(sorted(contract.roles)),
                contract.expression,
                contract.expression,
            )
        )
        for name, contract in sorted(IDENTITY_POLICY_CONTRACT.items())
    )
    monkeypatch.setattr("wc124_db_provisioner.psql", lambda *_args, **_kwargs: rows)

    with pytest.raises(ValueError, match="memberships"):
        verify_identity_schema("fqdn", "bootstrap", "token")
