"""Apply immutable PostgreSQL migrations through the configured PgBouncer route."""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg


MIGRATION_ROOT = Path(os.getenv("MIGRATION_ROOT", "/app/migrations"))
MIGRATION_PATTERN = os.getenv("MIGRATION_PATTERN", "*.sql")


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
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS public.waooaw_schema_migrations (
                migration_name text PRIMARY KEY,
                migration_sha256 char(64) NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
            )
            """
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
                    FROM public.waooaw_schema_migrations
                    WHERE migration_name = $1
                    """,
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
                    INSERT INTO public.waooaw_schema_migrations (
                        migration_name,
                        migration_sha256
                    )
                    VALUES ($1, $2)
                    """,
                    path.name,
                    digest,
                )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(apply_migrations())
