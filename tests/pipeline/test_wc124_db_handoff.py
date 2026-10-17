from __future__ import annotations

import json

import pytest

import wc124_db_handoff as handoff


def test_demo_handoff_verifies_every_database_and_zero_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logins: list[str] = []
    statements: list[tuple[str, str, str]] = []
    monkeypatch.setattr(handoff, "azure_login", logins.append)
    monkeypatch.setattr(handoff, "read_breakglass_password", lambda _vault: "sealed-password")
    monkeypatch.setattr(handoff, "access_token", lambda: "bootstrap-token")
    monkeypatch.setattr(
        handoff,
        "membership_grants",
        lambda *_args: (("ce_owner", "ce_migrator"), ("bp_owner", "bp_migrator")),
    )
    monkeypatch.setattr(
        handoff,
        "psql",
        lambda _host, user, database, _password, sql: statements.append((user, database, sql)),
    )
    monkeypatch.setattr(
        handoff,
        "query_psql",
        lambda _host, user, database, _password, sql: statements.append((user, database, sql)) or "0\n",
    )

    evidence = handoff.finalize_handoff(
        "demo",
        "kv-waooaw-demo",
        "psql-waooaw-demo-state.postgres.database.azure.com",
        "bootstrap-client",
        "id-waooaw-demo-db-bootstrap",
        "provisioner-client",
    )

    assert logins == ["provisioner-client", "bootstrap-client"]
    assert evidence == {
        "schema": "waooaw.wc124-db-handoff/v1",
        "environment": "demo",
        "databases_verified": 4,
        "memberships_reissued": 2,
        "remaining_bootstrap_dependencies": 0,
        "status": "ready-for-entra-bootstrap-removal",
    }
    bootstrap_databases = {database for user, database, _sql in statements if user == "id-waooaw-demo-db-bootstrap"}
    assert bootstrap_databases == {
        "waooaw_application",
        "waooaw_keycloak",
        "waooaw_temporal",
        "waooaw_temporal_visibility",
    }
    combined_sql = "\n".join(sql for _user, _database, sql in statements)
    assert "ALTER FUNCTION public.prevent_wc115_append_only_mutation() OWNER TO bp_owner" in combined_sql
    assert 'REVOKE "ce_owner" FROM "ce_migrator"' in combined_sql
    assert 'GRANT "ce_owner" TO "ce_migrator"' in combined_sql
    assert 'DROP OWNED BY "id-waooaw-demo-db-bootstrap"' in combined_sql
    assert "REVOKE CREATE ON SCHEMA public FROM bp_owner" in combined_sql
    assert "pg_shdepend" in combined_sql
    assert "sealed-password" not in combined_sql
    assert "bootstrap-token" not in combined_sql


def test_handoff_refuses_to_remove_bootstrap_with_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(handoff, "azure_login", lambda _client_id: None)
    monkeypatch.setattr(handoff, "read_breakglass_password", lambda _vault: "sealed-password")
    monkeypatch.setattr(handoff, "access_token", lambda: "bootstrap-token")
    monkeypatch.setattr(handoff, "membership_grants", lambda *_args: ())
    monkeypatch.setattr(handoff, "psql", lambda *_args: None)
    monkeypatch.setattr(handoff, "query_psql", lambda *_args: "3\n")

    with pytest.raises(RuntimeError, match="still has 3 PostgreSQL dependencies"):
        handoff.finalize_handoff(
            "uat",
            "kv-waooaw-uat",
            "psql-waooaw-uat-state.postgres.database.azure.com",
            "bootstrap-client",
            "id-waooaw-uat-db-bootstrap",
            "provisioner-client",
        )


def test_breakglass_secret_must_be_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        handoff,
        "run",
        lambda *_args, **_kwargs: json.dumps({"value": "sealed-password", "enabled": False}),
    )

    with pytest.raises(ValueError, match="credential is unavailable"):
        handoff.read_breakglass_password("kv-waooaw-demo")


def test_query_uses_system_ca_and_keeps_password_out_of_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> str:
        captured["command"] = command
        captured.update(kwargs)
        return "0\n"

    monkeypatch.setattr(handoff, "run", fake_run)

    assert handoff.query_psql("db.example", "admin", "app", "secret-value", "SELECT 0;") == "0\n"
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["PGSSLROOTCERT"] == "/etc/ssl/certs/ca-certificates.crt"
    assert environment["PGSSLMODE"] == "verify-full"
    assert environment["PGPASSWORD"] == "secret-value"
    assert "secret-value" not in captured["command"]
