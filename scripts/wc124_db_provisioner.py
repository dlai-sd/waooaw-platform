#!/usr/bin/env python3
"""Provision the exact WC-124 PostgreSQL roles and Key Vault credentials without echoing values."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from cli_errors import fail_cli


PROVISIONER = "wc124-db-provisioner"
APPLICATION_DATABASE = "waooaw_application"
KEYCLOAK_DATABASE = "waooaw_keycloak"
TEMPORAL_DATABASE = "waooaw_temporal"
TEMPORAL_VISIBILITY_DATABASE = "waooaw_temporal_visibility"
DEMO_DATABASES = (
    APPLICATION_DATABASE,
    KEYCLOAK_DATABASE,
    TEMPORAL_DATABASE,
    TEMPORAL_VISIBILITY_DATABASE,
)
PRINCIPAL_BOOTSTRAP_NAME = "00-wc124-principal-bootstrap.sql"
PROVISIONING_SCHEMA = "wc124_provisioning"
INIT_CHAIN_LEDGER_TABLE = f"{PROVISIONING_SCHEMA}.init_chain_ledger"
INIT_CHAIN_LEDGER_SQL = f"""
CREATE SCHEMA IF NOT EXISTS {PROVISIONING_SCHEMA};
REVOKE ALL ON SCHEMA {PROVISIONING_SCHEMA} FROM PUBLIC;
CREATE TABLE IF NOT EXISTS {INIT_CHAIN_LEDGER_TABLE} (
    file_name text PRIMARY KEY,
    sha256 char(64) NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    applied_by text NOT NULL DEFAULT current_user
);
"""
APPLICATION_MIGRATION_ROLES = {
    "ce_migrator": "ce_owner",
    "bp_migrator": "bp_owner",
    "pr_migrator": "pr_owner",
    "air_migrator": "air_owner",
    "billing_migrator": "billing_owner",
    "web_session_migrator": "web_session_owner",
}
REQUIRED_IDENTITY_RELATIONS = (
    "registrations",
    "idempotency_ledger",
    "accounts",
    "login_methods",
    "actor_bindings",
    "memberships",
)
ACTOR_SUBJECT_POLICY_EXPRESSION = (
    "(((actor_issuer)::text = (NULLIF(current_setting('app.identity_issuer'::text, true), "
    "''::text) COLLATE \"C\")) AND ((actor_subject)::text = "
    "(NULLIF(current_setting('app.identity_subject'::text, true), ''::text) COLLATE \"C\")))"
)


@dataclass(frozen=True)
class PolicyContract:
    roles: frozenset[str]
    expression: str


IDENTITY_POLICY_CONTRACT = {
    "accounts": PolicyContract(
        roles=frozenset(("business_app", "identity_resolver_owner")),
        expression=("(EXISTS ( SELECT 1 FROM identity.actor_bindings actor WHERE (actor.account_id = accounts.account_id)))"),
    ),
    "actor_bindings": PolicyContract(
        roles=frozenset(("business_app", "identity_resolver_owner")),
        expression=ACTOR_SUBJECT_POLICY_EXPRESSION,
    ),
    "idempotency_ledger": PolicyContract(
        roles=frozenset(("business_app",)),
        expression=ACTOR_SUBJECT_POLICY_EXPRESSION,
    ),
    "login_methods": PolicyContract(
        roles=frozenset(("business_app", "identity_resolver_owner")),
        expression=(
            "(EXISTS ( SELECT 1 FROM identity.actor_bindings actor WHERE "
            "((actor.account_id = login_methods.account_id) AND "
            "(actor.login_method_id = login_methods.login_method_id))))"
        ),
    ),
    "memberships": PolicyContract(
        roles=frozenset(("business_app", "identity_resolver_owner")),
        expression=("(EXISTS ( SELECT 1 FROM identity.actor_bindings actor WHERE (actor.account_id = memberships.account_id)))"),
    ),
    "registrations": PolicyContract(
        roles=frozenset(("business_app",)),
        expression=ACTOR_SUBJECT_POLICY_EXPRESSION,
    ),
}


@dataclass(frozen=True)
class CredentialSpec:
    secret_id: str
    vault_name: str
    role: str
    database: str
    value_format: str


SPECS = (
    CredentialSpec("db-keycloak-runtime", "db-keycloak-runtime", "keycloak_runtime", KEYCLOAK_DATABASE, "password"),
    CredentialSpec(
        "db-keycloak-migration",
        "db-keycloak-migration",
        "keycloak_migrator",
        KEYCLOAK_DATABASE,
        "password",
    ),
    CredentialSpec(
        "db-temporal-runtime-demo",
        "db-temporal-runtime-demo",
        "temporal_runtime",
        TEMPORAL_DATABASE,
        "password",
    ),
    CredentialSpec(
        "db-temporal-migration-demo",
        "db-temporal-migration-demo",
        "temporal_migrator",
        TEMPORAL_DATABASE,
        "password",
    ),
    CredentialSpec("db-ce-runtime", "db-ce-runtime", "ce_runtime", APPLICATION_DATABASE, "npgsql"),
    CredentialSpec("db-bp-runtime", "db-bp-runtime", "bp_runtime", APPLICATION_DATABASE, "npgsql"),
    CredentialSpec("db-pr-runtime", "db-pr-runtime", "pr_runtime", APPLICATION_DATABASE, "url"),
    CredentialSpec("db-air-runtime", "db-air-runtime", "air_runtime", APPLICATION_DATABASE, "url"),
    CredentialSpec("db-billing-runtime", "db-billing-runtime", "billing_runtime", APPLICATION_DATABASE, "url"),
    CredentialSpec(
        "web-session-database",
        "web-session-database-url",
        "web_session_app",
        APPLICATION_DATABASE,
        "url",
    ),
    CredentialSpec("db-ce-migration", "db-ce-migration", "ce_migrator", APPLICATION_DATABASE, "url"),
    CredentialSpec("db-bp-migration", "db-bp-migration", "bp_migrator", APPLICATION_DATABASE, "url"),
    CredentialSpec("db-pr-migration", "db-pr-migration", "pr_migrator", APPLICATION_DATABASE, "url"),
    CredentialSpec("db-air-migration", "db-air-migration", "air_migrator", APPLICATION_DATABASE, "url"),
    CredentialSpec(
        "db-billing-migration",
        "db-billing-migration",
        "billing_migrator",
        APPLICATION_DATABASE,
        "url",
    ),
    CredentialSpec(
        "db-web-session-migration",
        "db-web-session-migration",
        "web_session_migrator",
        APPLICATION_DATABASE,
        "url",
    ),
    CredentialSpec("db-pgbouncer-auth", "db-pgbouncer-auth", "pgbouncer_auth", APPLICATION_DATABASE, "authfile"),
)


def environment_specs(environment: str) -> tuple[CredentialSpec, ...]:
    if environment not in {"demo", "uat"}:
        raise ValueError("environment must be demo or uat")
    return tuple(
        spec
        for spec in SPECS
        if environment == "demo" or spec.secret_id not in {"db-temporal-runtime-demo", "db-temporal-migration-demo"}
    )


def validate_catalog(catalog: dict[str, Any], environment: str) -> tuple[CredentialSpec, ...]:
    specs = environment_specs(environment)
    entries = {
        entry.get("id"): entry
        for entry in catalog.get("entries", [])
        if isinstance(entry, dict) and entry.get("provisioner") == PROVISIONER and environment in entry.get("environments", [])
    }
    expected = {spec.secret_id for spec in specs}
    if set(entries) != expected:
        missing = sorted(expected - set(entries))
        extra = sorted(set(entries) - expected)
        raise ValueError(f"database credential catalog mismatch; missing={missing}, extra={extra}")
    for spec in specs:
        entry = entries[spec.secret_id]
        expected_catalog_principal = "pgbouncer" if spec.secret_id == "db-pgbouncer-auth" else spec.role  # noqa: S105
        if entry.get("vaultSecretName") != spec.vault_name or entry.get("principal") != expected_catalog_principal:
            raise ValueError(f"database credential catalog mapping is invalid for {spec.secret_id}")
        if entry.get("source") != "platform-generated" or entry.get("allowedOperations") != ["get"]:
            raise ValueError(f"database credential catalog authority is invalid for {spec.secret_id}")
    return specs


def generate_password() -> str:
    return secrets.token_urlsafe(48)


def secret_value(spec: CredentialSpec, password: str, pgbouncer_host: str) -> str:
    if spec.value_format == "password":
        return password
    if spec.value_format == "authfile":
        return f'"{spec.role}" "{password}"\n'
    if spec.value_format == "npgsql":
        return (
            f"Host={pgbouncer_host};Port=5432;Database={spec.database};Username={spec.role};"
            f"Password={password};SSL Mode=Disable;Pooling=true"
        )
    return (
        f"postgresql://{quote(spec.role, safe='')}:{quote(password, safe='')}@"
        f"{pgbouncer_host}:5432/{spec.database}?sslmode=disable"
    )


def parse_authfile(value: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in value.splitlines():
        parts = line.split('" "')
        if len(parts) != 2 or not parts[0].startswith('"') or not parts[1].endswith('"'):
            raise ValueError("PgBouncer auth_file contains an invalid entry")
        role = parts[0][1:]
        if not role or role in entries:
            raise ValueError("PgBouncer auth_file contains an invalid or duplicate role")
        entries[role] = parts[1][:-1]
    return entries


def authfile_value(passwords: dict[str, str]) -> str:
    return "".join(f'"{role}" "{password}"\n' for role, password in sorted(passwords.items()))


def password_from_secret(spec: CredentialSpec, value: str) -> str:
    if spec.value_format == "password":
        if not value:
            raise ValueError(f"{spec.secret_id} is empty")
        return value
    if spec.value_format == "authfile":
        entries = parse_authfile(value)
        if spec.role not in entries:
            raise ValueError(f"{spec.secret_id} is not a PgBouncer auth_file entry")
        return entries[spec.role]
    if spec.value_format == "npgsql":
        fields = dict(part.split("=", 1) for part in value.split(";") if "=" in part)
        password = fields.get("Password")
        if not password:
            raise ValueError(f"{spec.secret_id} has no Password field")
        return password
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.password is None:
        raise ValueError(f"{spec.secret_id} is not a PostgreSQL URL")
    return unquote(parsed.password)


def run(command: list[str], *, env: dict[str, str] | None = None, stdin: str | None = None) -> str:
    completed = subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        text=True,
        input=stdin,
        env=env,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "command returned no diagnostic output"
        raise RuntimeError(f"{Path(command[0]).name} failed with exit code {completed.returncode}: {detail}")
    return completed.stdout


def azure_login(client_id: str) -> None:
    run(["az", "login", "--identity", "--client-id", client_id, "--allow-no-subscriptions", "--output", "none"])


def await_vault_authorization(
    vault_name: str,
    *,
    attempts: int = 12,
    delay_seconds: float = 10,
) -> int:
    az_executable = shutil.which("az")
    if az_executable is None:
        raise RuntimeError("Azure CLI is unavailable for the Key Vault authorization probe")
    for attempt in range(1, attempts + 1):
        result = subprocess.run(  # noqa: S603
            [
                az_executable,
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                vault_name,
                "--name",
                "db-keycloak-runtime",
                "--query",
                "id",
                "--output",
                "tsv",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 or "SecretNotFound" in result.stderr:
            return attempt
        if "Forbidden" not in result.stderr:
            raise RuntimeError("Key Vault authorization probe failed with a non-authorization error")
        if attempt < attempts:
            time.sleep(delay_seconds)
    raise RuntimeError(f"Key Vault data-plane authority did not become effective after {attempts} attempts")


def probe_pgbouncer_connectivity(environment: str, host: str, *, timeout_seconds: float = 5) -> dict[str, Any]:
    expected_host = f"ca-{environment}-pgbouncer"
    if host != expected_host:
        raise ValueError(f"PgBouncer host must be the same-environment service name {expected_host}")
    addresses = sorted({record[4][0] for record in socket.getaddrinfo(host, 5432, type=socket.SOCK_STREAM)})
    if not addresses:
        raise RuntimeError("PgBouncer DNS returned no TCP addresses")
    with socket.create_connection((host, 5432), timeout=timeout_seconds):
        pass
    return {
        "schema": "waooaw.wc124-pgbouncer-connectivity/v1",
        "environment": environment,
        "host": host,
        "port": 5432,
        "resolved_addresses": addresses,
        "tcp": "connected",
    }


def access_token() -> str:
    token_record = json.loads(
        run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "https://ossrdbms-aad.database.windows.net",
                "-o",
                "json",
            ]
        )
    )
    return token_record["accessToken"]


def read_credentials(
    specs: tuple[CredentialSpec, ...],
    vault_name: str,
    *,
    require_existing: bool = False,
) -> tuple[dict[str, str], dict[str, dict[str, Any] | None]]:
    passwords: dict[str, str] = {}
    records: dict[str, dict[str, Any] | None] = {}
    for spec in specs:
        result = subprocess.run(  # noqa: S603
            ["az", "keyvault", "secret", "show", "--vault-name", vault_name, "--name", spec.vault_name, "-o", "json"],  # noqa: S607
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            record = json.loads(result.stdout)
            if record.get("attributes", {}).get("enabled") is not True:
                raise ValueError(f"{spec.secret_id} exists but is disabled")
            tags = record.get("tags") or {}
            if tags.get("wc124-role") != spec.role or tags.get("wc124-database") != spec.database:
                raise ValueError(f"{spec.secret_id} exists with incompatible WC-124 metadata")
            passwords[spec.role] = password_from_secret(spec, record.get("value", ""))
            records[spec.secret_id] = record
        elif "SecretNotFound" in result.stderr:
            if require_existing:
                raise ValueError(f"{spec.secret_id} is missing during canonical URL refresh")
            passwords[spec.role] = generate_password()
            records[spec.secret_id] = None
        else:
            raise RuntimeError(result.stderr.strip() or f"failed to read {spec.secret_id}")
    if len(passwords) != len(specs):
        raise ValueError("database roles must have distinct credentials")
    if len(set(passwords.values())) != len(passwords):
        raise ValueError("database credentials must be distinct")
    auth_spec = next(spec for spec in specs if spec.value_format == "authfile")
    auth_record = records[auth_spec.secret_id]
    if auth_record is not None and parse_authfile(auth_record.get("value", "")) != passwords:
        raise ValueError("db-pgbouncer-auth does not exactly match the database credential set")
    return passwords, records


def existing_grant_digest(records: dict[str, dict[str, Any] | None]) -> str:
    digests = {str((record.get("tags") or {}).get("wc124-grant-digest", "")) for record in records.values() if record is not None}
    if len(digests) != 1 or not next(iter(digests), ""):
        raise ValueError("existing WC-124 credentials must share one non-empty grant digest")
    return digests.pop()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def psql(
    server_fqdn: str,
    bootstrap_name: str,
    database: str,
    access_token: str,
    sql: str,
    *,
    tuples_only: bool = False,
) -> str:
    environment = dict(os.environ)
    environment["PGPASSWORD"] = access_token
    environment["PGSSLMODE"] = "verify-full"
    environment["PGSSLROOTCERT"] = "/etc/ssl/certs/ca-certificates.crt"
    return run(
        [
            "psql",
            "--no-psqlrc",
            "--set",
            "ON_ERROR_STOP=1",
            *(("--tuples-only", "--no-align", "--field-separator=\t") if tuples_only else ()),
            "--host",
            server_fqdn,
            "--port",
            "5432",
            "--username",
            bootstrap_name,
            "--dbname",
            database,
        ],
        env=environment,
        stdin=sql,
    )


def application_migration_files(init_directory: Path) -> tuple[Path, ...]:
    """Return every ``*.sql`` init file after the principal bootstrap in C-locale order.

    Shell init files are local-compose only (legacy LOGIN passwords, preview seeds) and are
    never applied to a managed environment.
    """
    if not (init_directory / PRINCIPAL_BOOTSTRAP_NAME).is_file():
        raise ValueError(f"WC-124 principal bootstrap file is missing: {PRINCIPAL_BOOTSTRAP_NAME}")
    files = tuple(
        sorted(
            (path for path in init_directory.glob("*.sql") if path.name != PRINCIPAL_BOOTSTRAP_NAME),
            key=lambda path: path.name.encode(),
        )
    )
    if not files:
        raise ValueError(f"WC-124 init chain has no application migration files in {init_directory}")
    return files


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reset_demo_databases(
    server_fqdn: str,
    bootstrap_name: str,
    database_access_token: str,
) -> dict[str, Any]:
    for index, database in enumerate(DEMO_DATABASES, start=1):
        print(
            f"[wc124-db-provisioner] phase=demo-reset database={database} progress={index}/{len(DEMO_DATABASES)}",
            file=sys.stderr,
            flush=True,
        )
        quoted_database = sql_identifier(database)
        psql(
            server_fqdn,
            bootstrap_name,
            "postgres",
            database_access_token,
            f"DROP DATABASE IF EXISTS {quoted_database} WITH (FORCE);",
        )
        psql(
            server_fqdn,
            bootstrap_name,
            "postgres",
            database_access_token,
            f"CREATE DATABASE {quoted_database} OWNER {sql_identifier(bootstrap_name)};",
        )
    return {"status": "completed", "databases": list(DEMO_DATABASES)}


def read_init_chain_ledger(
    server_fqdn: str,
    bootstrap_name: str,
    access_token: str,
) -> dict[str, str]:
    psql(server_fqdn, bootstrap_name, APPLICATION_DATABASE, access_token, INIT_CHAIN_LEDGER_SQL)
    rows = psql(
        server_fqdn,
        bootstrap_name,
        APPLICATION_DATABASE,
        access_token,
        f"SELECT file_name, sha256 FROM {INIT_CHAIN_LEDGER_TABLE} ORDER BY file_name;",  # noqa: S608 constant table
        tuples_only=True,
    )
    ledger: dict[str, str] = {}
    for line in rows.splitlines():
        if "\t" in line:
            file_name, digest = line.split("\t", 1)
            ledger[file_name.strip()] = digest.strip()
    return ledger


def apply_init_chain(
    server_fqdn: str,
    bootstrap_name: str,
    access_token: str,
    files: tuple[Path, ...],
    *,
    force: bool = False,
) -> dict[str, list[str]]:
    """Apply new init files and reject changed applied files unless repair is explicit."""
    ledger = read_init_chain_ledger(server_fqdn, bootstrap_name, access_token)
    outcome: dict[str, list[str]] = {"applied": [], "reapplied": [], "skipped": []}
    for path in files:
        digest = file_digest(path)
        recorded = ledger.get(path.name)
        if recorded == digest and not force:
            outcome["skipped"].append(path.name)
            continue
        if recorded and not force:
            raise ValueError(
                f"init-chain integrity failure for already-applied migration {path.name}: "
                "recorded digest differs; use the explicit force-init-chain recovery path only "
                "after migration-specific repair review"
            )
        psql(
            server_fqdn,
            bootstrap_name,
            APPLICATION_DATABASE,
            access_token,
            path.read_text(encoding="utf-8"),
        )
        psql(
            server_fqdn,
            bootstrap_name,
            APPLICATION_DATABASE,
            access_token,
            f"INSERT INTO {INIT_CHAIN_LEDGER_TABLE} (file_name, sha256) VALUES "  # noqa: S608 constant table, quoted literals
            f"({sql_literal(path.name)}, {sql_literal(digest)}) "
            "ON CONFLICT (file_name) DO UPDATE SET sha256 = EXCLUDED.sha256, "
            "applied_at = now(), applied_by = current_user;",
        )
        outcome["reapplied" if recorded else "applied"].append(path.name)
    return outcome


def verify_identity_schema(
    server_fqdn: str,
    bootstrap_name: str,
    access_token: str,
) -> dict[str, Any]:
    relation_values = ", ".join(f"({sql_literal(name)})" for name in REQUIRED_IDENTITY_RELATIONS)
    catalog_sql = f"""
WITH required(relname) AS (VALUES {relation_values})
SELECT required.relname,
       classes.oid IS NOT NULL,
       COALESCE(classes.relrowsecurity, false),
       COALESCE(classes.relforcerowsecurity, false),
       (SELECT count(*) FROM pg_policies
        WHERE schemaname = 'identity' AND tablename = required.relname AND policyname = 'actor_scope'),
       (SELECT count(*) FROM pg_policies
        WHERE schemaname = 'identity' AND tablename = required.relname),
       COALESCE(policy.permissive, ''),
       COALESCE(policy.cmd, ''),
       COALESCE(array_to_string(policy.roles, ','), ''),
       COALESCE(regexp_replace(policy.qual, E'[\\t\\n\\r ]+', ' ', 'g'), ''),
       COALESCE(regexp_replace(policy.with_check, E'[\\t\\n\\r ]+', ' ', 'g'), '')
FROM required
LEFT JOIN pg_namespace AS namespaces ON namespaces.nspname = 'identity'
LEFT JOIN pg_class AS classes ON classes.relnamespace = namespaces.oid
    AND classes.relname = required.relname AND classes.relkind IN ('r', 'p')
LEFT JOIN pg_policies AS policy ON policy.schemaname = 'identity'
    AND policy.tablename = required.relname AND policy.policyname = 'actor_scope'
ORDER BY required.relname;
"""  # noqa: S608 - relation names are fixed constants escaped by sql_literal.
    output = psql(
        server_fqdn,
        bootstrap_name,
        APPLICATION_DATABASE,
        access_token,
        catalog_sql,
        tuples_only=True,
    )
    observed: dict[str, dict[str, Any]] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 11:
            raise ValueError(f"invalid identity catalog evidence row: {line}")
        (
            name,
            exists,
            rls,
            forced_rls,
            actor_scope_count,
            total_policy_count,
            permissive,
            command,
            roles,
            qual,
            with_check,
        ) = fields
        contract = IDENTITY_POLICY_CONTRACT.get(name)
        expected_roles = contract.roles if contract else frozenset()
        expected_expression = contract.expression if contract else None
        policy_definition_valid = (
            actor_scope_count == "1"
            and total_policy_count == "1"
            and permissive == "PERMISSIVE"
            and command == "ALL"
            and set(filter(None, roles.split(","))) == expected_roles
            and qual == expected_expression
            and with_check == expected_expression
        )
        canonical_roles = ",".join(sorted(filter(None, roles.split(","))))
        observed[name] = {
            "exists": exists == "t",
            "rls": rls == "t",
            "forced_rls": forced_rls == "t",
            "actor_scope_policy": policy_definition_valid,
            "policy_definition_sha256": hashlib.sha256(
                "\0".join((permissive, command, canonical_roles, qual, with_check)).encode()
            ).hexdigest(),
        }
    failures = [
        name
        for name in REQUIRED_IDENTITY_RELATIONS
        if name not in observed
        or not all(observed[name][field] for field in ("exists", "rls", "forced_rls", "actor_scope_policy"))
    ]
    if failures:
        raise ValueError("identity schema verification failed for required relations: " + ", ".join(failures))
    return {
        "schema": "identity",
        "required_relations": list(REQUIRED_IDENTITY_RELATIONS),
        "relations": observed,
        "status": "passed",
    }


def expected_identity_policy_digest(name: str) -> str:
    contract = IDENTITY_POLICY_CONTRACT[name]
    roles = ",".join(sorted(contract.roles))
    expression = contract.expression
    return hashlib.sha256("\0".join(("PERMISSIVE", "ALL", roles, expression, expression)).encode()).hexdigest()


def provision_postgresql(
    specs: tuple[CredentialSpec, ...],
    passwords: dict[str, str],
    server_fqdn: str,
    bootstrap_name: str,
    init_directory: Path,
    *,
    force_init_chain: bool = False,
    reset_demo: bool = False,
) -> tuple[str, dict[str, list[str]], dict[str, Any], dict[str, Any] | None]:
    database_access_token = access_token()
    database_reset = reset_demo_databases(server_fqdn, bootstrap_name, database_access_token) if reset_demo else None
    role_sql = (init_directory / PRINCIPAL_BOOTSTRAP_NAME).read_text(encoding="utf-8")
    role_sql += "\n" + "\n".join(
        f"ALTER ROLE {sql_identifier(role)} PASSWORD {sql_literal(password)};" for role, password in sorted(passwords.items())
    )
    psql(server_fqdn, bootstrap_name, APPLICATION_DATABASE, database_access_token, role_sql)

    application_files = application_migration_files(init_directory)
    psql(
        server_fqdn,
        bootstrap_name,
        APPLICATION_DATABASE,
        database_access_token,
        f"GRANT bp_owner TO {sql_identifier(bootstrap_name)};",
    )
    try:
        init_chain = apply_init_chain(
            server_fqdn,
            bootstrap_name,
            database_access_token,
            application_files,
            force=force_init_chain,
        )
    finally:
        psql(
            server_fqdn,
            bootstrap_name,
            APPLICATION_DATABASE,
            database_access_token,
            f"REVOKE bp_owner FROM {sql_identifier(bootstrap_name)};",
        )

    database_roles = {
        APPLICATION_DATABASE: sorted({spec.role for spec in specs if spec.database == APPLICATION_DATABASE}),
        KEYCLOAK_DATABASE: ["keycloak_migrator", "keycloak_runtime"],
    }
    if any(spec.database == TEMPORAL_DATABASE for spec in specs):
        database_roles[TEMPORAL_DATABASE] = ["temporal_migrator", "temporal_runtime"]
        database_roles[TEMPORAL_VISIBILITY_DATABASE] = ["temporal_migrator", "temporal_runtime"]
    for database, roles in database_roles.items():
        grants = (
            f"REVOKE CONNECT ON DATABASE {sql_identifier(database)} FROM PUBLIC;\n"
            f"GRANT CONNECT ON DATABASE {sql_identifier(database)} TO "
            + ", ".join(sql_identifier(role) for role in roles)
            + ";\n"
        )
        psql(server_fqdn, bootstrap_name, database, database_access_token, grants)
    application_owner_sql = "\n".join(
        (
            f"GRANT {sql_identifier(owner)} TO {sql_identifier(migrator)};\n"
            f"ALTER ROLE {sql_identifier(migrator)} IN DATABASE {sql_identifier(APPLICATION_DATABASE)} "
            f"SET role TO {sql_identifier(owner)};"
        )
        for migrator, owner in APPLICATION_MIGRATION_ROLES.items()
    )
    psql(
        server_fqdn,
        bootstrap_name,
        APPLICATION_DATABASE,
        database_access_token,
        application_owner_sql,
    )
    vendor_databases = {
        KEYCLOAK_DATABASE: ("keycloak_owner", "keycloak_migrator", "keycloak_runtime"),
    }
    if TEMPORAL_DATABASE in database_roles:
        vendor_databases[TEMPORAL_DATABASE] = (
            "temporal_owner",
            "temporal_migrator",
            "temporal_runtime",
        )
        vendor_databases[TEMPORAL_VISIBILITY_DATABASE] = (
            "temporal_owner",
            "temporal_migrator",
            "temporal_runtime",
        )
    for database, (owner, migrator, runtime) in vendor_databases.items():
        extension_sql = "CREATE EXTENSION IF NOT EXISTS btree_gin;" if database == TEMPORAL_VISIBILITY_DATABASE else ""
        vendor_sql = f"""
{extension_sql}
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO {sql_identifier(owner)};
GRANT {sql_identifier(owner)} TO {sql_identifier(migrator)};
ALTER ROLE {sql_identifier(migrator)} IN DATABASE {sql_identifier(database)}
    SET role TO {sql_identifier(owner)};
GRANT USAGE ON SCHEMA public TO {sql_identifier(runtime)};
ALTER DEFAULT PRIVILEGES FOR ROLE {sql_identifier(owner)} IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {sql_identifier(runtime)};
ALTER DEFAULT PRIVILEGES FOR ROLE {sql_identifier(owner)} IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {sql_identifier(runtime)};
ALTER DEFAULT PRIVILEGES FOR ROLE {sql_identifier(owner)} IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO {sql_identifier(runtime)};
"""
        psql(server_fqdn, bootstrap_name, database, database_access_token, vendor_sql)
    identity_schema = verify_identity_schema(
        server_fqdn,
        bootstrap_name,
        database_access_token,
    )
    del database_access_token
    grant_digest = hashlib.sha256(
        b"\0".join(path.read_bytes() for path in [init_directory / PRINCIPAL_BOOTSTRAP_NAME, *application_files])
    ).hexdigest()
    return grant_digest, init_chain, identity_schema, database_reset


def write_secrets(
    specs: tuple[CredentialSpec, ...],
    passwords: dict[str, str],
    records: dict[str, dict[str, Any] | None],
    vault_name: str,
    pgbouncer_host: str,
    grant_digest: str,
) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for spec in specs:
        record = records[spec.secret_id]
        status = "preserved"
        value: str | None = None
        if record is None:
            if spec.value_format == "authfile":
                value = authfile_value(passwords)
            else:
                value = secret_value(spec, passwords[spec.role], pgbouncer_host)
            status = "created"
        elif spec.value_format in {"url", "npgsql"}:
            value = secret_value(spec, passwords[spec.role], pgbouncer_host)
            if record.get("value") != value:
                status = "updated"
        if status in {"created", "updated"}:
            assert value is not None
            record = json.loads(
                run(
                    [
                        "az",
                        "keyvault",
                        "secret",
                        "set",
                        "--vault-name",
                        vault_name,
                        "--name",
                        spec.vault_name,
                        "--value",
                        value,
                        "--tags",
                        f"wc124-role={spec.role}",
                        f"wc124-database={spec.database}",
                        f"wc124-grant-digest={grant_digest}",
                        "wc124-provisioner=wc124-db-provisioner",
                        "-o",
                        "json",
                    ]
                )
            )
        if value is not None:
            del value
        evidence.append(
            {
                "logical_secret_id": spec.secret_id,
                "role": spec.role,
                "database": spec.database,
                "vault_name": vault_name,
                "version_id": record["id"].rsplit("/", 1)[-1],
                "status": status,
            }
        )
    return evidence


def execute(arguments: argparse.Namespace) -> dict[str, Any]:
    catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
    specs = validate_catalog(catalog, arguments.environment)
    refresh_only = getattr(arguments, "refresh_existing_urls", False)
    azure_login(arguments.provisioner_client_id)
    authorization_attempts = await_vault_authorization(arguments.vault_name)
    passwords, records = read_credentials(specs, arguments.vault_name, require_existing=refresh_only)
    if refresh_only:
        grant_digest = existing_grant_digest(records)
        evidence = write_secrets(
            specs,
            passwords,
            records,
            arguments.vault_name,
            arguments.pgbouncer_host,
            grant_digest,
        )
        passwords.clear()
        return {
            "schema": "waooaw.wc124-db-provisioning/v1",
            "environment": arguments.environment,
            "grant_digest": grant_digest,
            "password_authentication_ready": True,
            "mode": "canonical-url-refresh",
            "vault_authorization_attempts": authorization_attempts,
            "credentials": evidence,
        }
    azure_login(arguments.bootstrap_client_id)
    reset_demo = getattr(arguments, "reset_demo_databases", False)
    if reset_demo and arguments.environment != "demo":
        raise ValueError("--reset-demo-databases is restricted to the demo environment")
    grant_digest, init_chain, identity_schema, database_reset = provision_postgresql(
        specs,
        passwords,
        arguments.server_fqdn,
        arguments.bootstrap_name,
        arguments.init_directory,
        force_init_chain=getattr(arguments, "force_init_chain", False),
        reset_demo=reset_demo,
    )
    azure_login(arguments.provisioner_client_id)
    evidence = write_secrets(
        specs,
        passwords,
        records,
        arguments.vault_name,
        arguments.pgbouncer_host,
        grant_digest,
    )
    passwords.clear()
    return {
        "schema": "waooaw.wc124-db-provisioning/v1",
        "environment": arguments.environment,
        "grant_digest": grant_digest,
        "password_authentication_ready": True,
        "vault_authorization_attempts": authorization_attempts,
        "database_reset": database_reset,
        "init_chain": {
            "ledger": INIT_CHAIN_LEDGER_TABLE,
            "applied": len(init_chain["applied"]),
            "reapplied": len(init_chain["reapplied"]),
            "skipped": len(init_chain["skipped"]),
            "changed_files": init_chain["applied"] + init_chain["reapplied"],
        },
        "identity_schema": identity_schema,
        "credentials": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--vault-name")
    parser.add_argument("--server-fqdn")
    parser.add_argument("--pgbouncer-host")
    parser.add_argument("--bootstrap-client-id")
    parser.add_argument("--bootstrap-name")
    parser.add_argument("--provisioner-client-id")
    parser.add_argument("--init-directory", type=Path, default=Path("/opt/waooaw/postgres/init"))
    parser.add_argument("--refresh-existing-urls", action="store_true")
    parser.add_argument(
        "--reset-demo-databases",
        action="store_true",
        help="drop and recreate all four demo databases before applying the clean init chain",
    )
    parser.add_argument(
        "--force-init-chain",
        action="store_true",
        help="re-apply every init file regardless of the ledger digest (files are idempotent)",
    )
    parser.add_argument("--network-probe", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.network_probe:
            if not arguments.pgbouncer_host:
                raise ValueError("missing execution arguments: pgbouncer_host")
            result = probe_pgbouncer_connectivity(arguments.environment, arguments.pgbouncer_host)
            json.dump(result, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
            return 0
        if arguments.catalog is None:
            raise ValueError("missing execution arguments: catalog")
        catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
        specs = validate_catalog(catalog, arguments.environment)
        if arguments.validate_only:
            result = {
                "schema": "waooaw.wc124-db-provisioning-plan/v1",
                "environment": arguments.environment,
                "credential_count": len(specs),
                "databases": sorted(
                    {spec.database for spec in specs}
                    | ({TEMPORAL_VISIBILITY_DATABASE} if arguments.environment == "demo" else set())
                ),
                "roles": sorted(spec.role for spec in specs),
            }
        else:
            required = ["vault_name", "pgbouncer_host", "provisioner_client_id"]
            if not arguments.refresh_existing_urls:
                required.extend(("server_fqdn", "bootstrap_client_id", "bootstrap_name"))
            missing = [name for name in required if not getattr(arguments, name)]
            if missing:
                raise ValueError("missing execution arguments: " + ", ".join(missing))
            result = execute(arguments)
    except (OSError, json.JSONDecodeError, KeyError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    else:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
