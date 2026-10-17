#!/usr/bin/env python3
"""Provision the exact WC-124 PostgreSQL roles and Key Vault credentials without echoing values."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit


PROVISIONER = "wc124-db-provisioner"
APPLICATION_DATABASE = "waooaw_application"
KEYCLOAK_DATABASE = "waooaw_keycloak"
TEMPORAL_DATABASE = "waooaw_temporal"
TEMPORAL_VISIBILITY_DATABASE = "waooaw_temporal_visibility"


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
        check=True,
        capture_output=True,
        text=True,
        input=stdin,
        env=env,
    )
    return completed.stdout


def azure_login(client_id: str) -> None:
    run(["az", "login", "--identity", "--client-id", client_id, "--allow-no-subscriptions", "--output", "none"])


def read_credentials(
    specs: tuple[CredentialSpec, ...],
    vault_name: str,
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
) -> None:
    environment = dict(os.environ)
    environment["PGPASSWORD"] = access_token
    environment["PGSSLMODE"] = "verify-full"
    run(
        [
            "psql",
            "--no-psqlrc",
            "--set",
            "ON_ERROR_STOP=1",
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


def provision_postgresql(
    specs: tuple[CredentialSpec, ...],
    passwords: dict[str, str],
    server_fqdn: str,
    bootstrap_name: str,
    init_directory: Path,
) -> str:
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
    access_token = token_record["accessToken"]
    role_sql = (init_directory / "00-wc124-principal-bootstrap.sql").read_text(encoding="utf-8")
    role_sql += "\n" + "\n".join(
        f"ALTER ROLE {sql_identifier(role)} PASSWORD {sql_literal(password)};" for role, password in sorted(passwords.items())
    )
    psql(server_fqdn, bootstrap_name, APPLICATION_DATABASE, access_token, role_sql)

    application_files = [path for path in sorted(init_directory.glob("*.sql")) if path.name != "00-wc124-principal-bootstrap.sql"]
    for path in application_files:
        psql(
            server_fqdn,
            bootstrap_name,
            APPLICATION_DATABASE,
            access_token,
            path.read_text(encoding="utf-8"),
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
        psql(server_fqdn, bootstrap_name, database, access_token, grants)
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
        psql(server_fqdn, bootstrap_name, database, access_token, vendor_sql)
    del access_token
    return hashlib.sha256(
        b"\0".join(path.read_bytes() for path in [init_directory / "00-wc124-principal-bootstrap.sql", *application_files])
    ).hexdigest()


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
        if record is None:
            if spec.value_format == "authfile":
                value = authfile_value(passwords)
            else:
                value = secret_value(spec, passwords[spec.role], pgbouncer_host)
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
            del value
        evidence.append(
            {
                "logical_secret_id": spec.secret_id,
                "role": spec.role,
                "database": spec.database,
                "vault_name": vault_name,
                "version_id": record["id"].rsplit("/", 1)[-1],
                "status": "preserved" if records[spec.secret_id] is not None else "created",
            }
        )
    return evidence


def execute(arguments: argparse.Namespace) -> dict[str, Any]:
    catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
    specs = validate_catalog(catalog, arguments.environment)
    azure_login(arguments.provisioner_client_id)
    passwords, records = read_credentials(specs, arguments.vault_name)
    azure_login(arguments.bootstrap_client_id)
    grant_digest = provision_postgresql(
        specs,
        passwords,
        arguments.server_fqdn,
        arguments.bootstrap_name,
        arguments.init_directory,
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
        "credentials": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--vault-name")
    parser.add_argument("--server-fqdn")
    parser.add_argument("--pgbouncer-host")
    parser.add_argument("--bootstrap-client-id")
    parser.add_argument("--bootstrap-name")
    parser.add_argument("--provisioner-client-id")
    parser.add_argument("--init-directory", type=Path, default=Path("/opt/waooaw/postgres/init"))
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    try:
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
            required = (
                "vault_name",
                "server_fqdn",
                "pgbouncer_host",
                "bootstrap_client_id",
                "bootstrap_name",
                "provisioner_client_id",
            )
            missing = [name for name in required if not getattr(arguments, name)]
            if missing:
                raise ValueError("missing execution arguments: " + ", ".join(missing))
            result = execute(arguments)
    except (OSError, json.JSONDecodeError, KeyError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        parser.error(str(error))
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
