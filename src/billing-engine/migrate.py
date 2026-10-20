"""Apply immutable PostgreSQL migrations through the configured PgBouncer route."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from pathlib import Path

import asyncpg


MIGRATION_ROOT = Path(os.getenv("MIGRATION_ROOT", "/app/migrations"))
MIGRATION_PATTERN = os.getenv("MIGRATION_PATTERN", "*.sql")
MIGRATION_SCHEMA = os.getenv("MIGRATION_SCHEMA", "public")
MIGRATION_OWNER_ROLE = os.getenv("MIGRATION_OWNER_ROLE", "billing_owner")

for name, value in (
    ("MIGRATION_SCHEMA", MIGRATION_SCHEMA),
    ("MIGRATION_OWNER_ROLE", MIGRATION_OWNER_ROLE),
):
    if re.fullmatch(r"[a-z_][a-z0-9_]*", value) is None:
        raise ValueError(f"{name} must be a lowercase PostgreSQL identifier")


def migration_sql(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(
        line for line in lines if line.strip().upper() not in {"BEGIN;", "COMMIT;"}
    )


def migration_files() -> list[tuple[Path, str, str]]:
    return [
        (path, hashlib.sha256(path.read_bytes()).hexdigest(), migration_sql(path))
        for path in sorted(MIGRATION_ROOT.glob(MIGRATION_PATTERN))
    ]


async def apply_migrations() -> None:
    database_url = os.environ["DATABASE_URL"]
    files = await asyncio.to_thread(migration_files)
    connection = await asyncpg.connect(database_url)
    try:
        preflight = await connection.fetchrow(
            """
            SELECT
                session_user AS login_name,
                pg_get_userbyid(namespace.nspowner) AS schema_owner,
                pg_has_role(session_user, $2, 'MEMBER') AS can_assume_owner,
                login.rolsuper,
                login.rolcreatedb,
                login.rolcreaterole,
                login.rolbypassrls
            FROM pg_namespace AS namespace
            CROSS JOIN pg_roles AS login
            WHERE namespace.nspname = $1
              AND login.rolname = session_user
            """,
            MIGRATION_SCHEMA,
            MIGRATION_OWNER_ROLE,
        )
        if preflight is None:
            raise RuntimeError(f"migration schema is not provisioned: {MIGRATION_SCHEMA}")
        if preflight["schema_owner"] != MIGRATION_OWNER_ROLE:
            raise RuntimeError(
                f"migration schema owner mismatch: expected {MIGRATION_OWNER_ROLE}, "
                f"found {preflight['schema_owner']}"
            )
        if not preflight["can_assume_owner"]:
            raise RuntimeError(f"{preflight['login_name']} cannot assume {MIGRATION_OWNER_ROLE}")
        if any(preflight[field] for field in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolbypassrls")):
            raise RuntimeError("migration login has prohibited elevated PostgreSQL attributes")
        await connection.execute(f"SET ROLE {MIGRATION_OWNER_ROLE}")
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS {MIGRATION_SCHEMA}.waooaw_schema_migrations (
                migration_name text PRIMARY KEY,
                migration_sha256 char(64) NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
            )
            """.format(MIGRATION_SCHEMA=MIGRATION_SCHEMA)
        )
        for path, digest, sql in files:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext($1))",
                    f"waooaw-migration:{path.name}",
                )
                existing = await connection.fetchval(
                    """
                    SELECT migration_sha256
                    FROM {MIGRATION_SCHEMA}.waooaw_schema_migrations
                    WHERE migration_name = $1
                    """.format(MIGRATION_SCHEMA=MIGRATION_SCHEMA),
                    path.name,
                )
                if existing is not None:
                    if existing != digest:
                        raise RuntimeError(
                            f"immutable migration digest changed: {path.name}"
                        )
                    continue
                await connection.execute(sql)
                await connection.execute(
                    """
                    INSERT INTO {MIGRATION_SCHEMA}.waooaw_schema_migrations (
                        migration_name,
                        migration_sha256
                    )
                    VALUES ($1, $2)
                    """.format(MIGRATION_SCHEMA=MIGRATION_SCHEMA),
                    path.name,
                    digest,
                )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(apply_migrations())
