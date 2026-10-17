#!/usr/bin/env python3
"""Finalize WC-124 PostgreSQL authority transfer before removing the Entra bootstrap."""

# ruff: noqa: S608

from __future__ import annotations

import argparse
import json
import os

from wc124_db_provisioner import access_token, azure_login, psql, run, sql_identifier, sql_literal


APPLICATION_DATABASE = "waooaw_application"
DATABASE_OWNERS = {
    "demo": (
        (APPLICATION_DATABASE, "bp_owner"),
        ("waooaw_keycloak", "keycloak_owner"),
        ("waooaw_temporal", "temporal_owner"),
        ("waooaw_temporal_visibility", "temporal_owner"),
    ),
    "uat": (
        (APPLICATION_DATABASE, "bp_owner"),
        ("waooaw_keycloak", "keycloak_owner"),
    ),
}


def query_psql(
    server_fqdn: str,
    user_name: str,
    database: str,
    password: str,
    sql: str,
) -> str:
    environment = dict(os.environ)
    environment["PGPASSWORD"] = password
    environment["PGSSLMODE"] = "verify-full"
    environment["PGSSLROOTCERT"] = "/etc/ssl/certs/ca-certificates.crt"
    return run(
        [
            "psql",
            "--no-psqlrc",
            "--set",
            "ON_ERROR_STOP=1",
            "--tuples-only",
            "--no-align",
            "--host",
            server_fqdn,
            "--port",
            "5432",
            "--username",
            user_name,
            "--dbname",
            database,
        ],
        env=environment,
        stdin=sql,
    )


def read_breakglass_password(vault_name: str) -> str:
    record = json.loads(
        run(
            [
                "az",
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                vault_name,
                "--name",
                "db-server-breakglass-admin",
                "--query",
                "{value:value,enabled:attributes.enabled}",
                "-o",
                "json",
            ]
        )
    )
    if record.get("enabled") is not True or not isinstance(record.get("value"), str) or not record["value"]:
        raise ValueError("sealed PostgreSQL break-glass credential is unavailable")
    return record["value"]


def membership_grants(
    server_fqdn: str,
    bootstrap_name: str,
    bootstrap_token: str,
) -> tuple[tuple[str, str], ...]:
    output = query_psql(
        server_fqdn,
        bootstrap_name,
        APPLICATION_DATABASE,
        bootstrap_token,
        f"""
SELECT granted.rolname || E'\\t' || member.rolname
FROM pg_auth_members membership
JOIN pg_roles granted ON granted.oid = membership.roleid
JOIN pg_roles member ON member.oid = membership.member
WHERE membership.grantor = (
    SELECT oid FROM pg_roles WHERE rolname = {sql_literal(bootstrap_name)}
)
ORDER BY granted.rolname, member.rolname;
""",
    )
    grants: list[tuple[str, str]] = []
    for line in output.splitlines():
        granted_role, member_role = line.split("\t", 1)
        grants.append((granted_role, member_role))
    return tuple(grants)


def finalize_handoff(
    environment: str,
    vault_name: str,
    server_fqdn: str,
    bootstrap_client_id: str,
    bootstrap_name: str,
    provisioner_client_id: str,
) -> dict[str, object]:
    if environment not in DATABASE_OWNERS:
        raise ValueError("environment must be demo or uat")
    expected_bootstrap_name = f"id-waooaw-{environment}-db-bootstrap"
    if bootstrap_name != expected_bootstrap_name:
        raise ValueError(f"bootstrap name must be {expected_bootstrap_name}")

    azure_login(provisioner_client_id)
    administrator_password = read_breakglass_password(vault_name)
    azure_login(bootstrap_client_id)
    bootstrap_token = access_token()
    grants = membership_grants(server_fqdn, bootstrap_name, bootstrap_token)

    administrator_name = "wc124_breakglass_admin"
    quoted_bootstrap = sql_identifier(bootstrap_name)
    psql(
        server_fqdn,
        administrator_name,
        APPLICATION_DATABASE,
        administrator_password,
        f"""
GRANT USAGE, CREATE ON SCHEMA public TO {quoted_bootstrap};
GRANT USAGE, CREATE ON SCHEMA public TO bp_owner;
""",
    )

    revoke_memberships = "\n".join(
        f"REVOKE {sql_identifier(granted)} FROM {sql_identifier(member)};" for granted, member in grants
    )
    for database, expected_owner in DATABASE_OWNERS[environment]:
        transfer_public_function = ""
        if database == APPLICATION_DATABASE:
            transfer_public_function = """
DO $handoff$
BEGIN
    IF to_regprocedure('public.prevent_wc115_append_only_mutation()') IS NOT NULL THEN
        ALTER FUNCTION public.prevent_wc115_append_only_mutation() OWNER TO bp_owner;
    END IF;
END
$handoff$;
"""
        psql(
            server_fqdn,
            bootstrap_name,
            database,
            bootstrap_token,
            f"""
DO $owner$
BEGIN
    IF current_database() <> {sql_literal(database)}
       OR (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database())
          <> {sql_literal(expected_owner)} THEN
        RAISE EXCEPTION 'database owner handoff is incomplete for %', current_database();
    END IF;
END
$owner$;
{transfer_public_function}
{revoke_memberships if database == APPLICATION_DATABASE else ""}
DROP OWNED BY {quoted_bootstrap};
""",
        )

    regrant_memberships = "\n".join(f"GRANT {sql_identifier(granted)} TO {sql_identifier(member)};" for granted, member in grants)
    remaining_dependencies = query_psql(
        server_fqdn,
        administrator_name,
        APPLICATION_DATABASE,
        administrator_password,
        f"""
{regrant_memberships}
REVOKE CREATE ON SCHEMA public FROM bp_owner;
REVOKE USAGE, CREATE ON SCHEMA public FROM {quoted_bootstrap};
SELECT count(*)
FROM pg_shdepend
WHERE refclassid = 'pg_authid'::regclass
  AND refobjid = (
      SELECT oid FROM pg_roles WHERE rolname = {sql_literal(bootstrap_name)}
  );
""",
    ).strip()
    bootstrap_token = ""
    administrator_password = ""
    if remaining_dependencies != "0":
        raise RuntimeError(f"bootstrap authority still has {remaining_dependencies} PostgreSQL dependencies")

    return {
        "schema": "waooaw.wc124-db-handoff/v1",
        "environment": environment,
        "databases_verified": len(DATABASE_OWNERS[environment]),
        "memberships_reissued": len(grants),
        "remaining_bootstrap_dependencies": 0,
        "status": "ready-for-entra-bootstrap-removal",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--vault-name", required=True)
    parser.add_argument("--server-fqdn", required=True)
    parser.add_argument("--bootstrap-client-id", required=True)
    parser.add_argument("--bootstrap-name", required=True)
    parser.add_argument("--provisioner-client-id", required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            finalize_handoff(
                arguments.environment,
                arguments.vault_name,
                arguments.server_fqdn,
                arguments.bootstrap_client_id,
                arguments.bootstrap_name,
                arguments.provisioner_client_id,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
