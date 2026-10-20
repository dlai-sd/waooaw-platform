# Implements: WBE database session factory
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


_ASYNCPG_SSL_MODES = {
    "disable": False,
    "allow": "prefer",
    "prefer": "prefer",
    "require": "require",
    "verify-ca": "verify-ca",
    "verify-full": "verify-full",
}


def asyncpg_engine_target(url: str) -> tuple[str, dict[str, Any]]:
    """Translate a provisioned PostgreSQL URL into an asyncpg SQLAlchemy target.

    Provisioned credentials are rendered as plain ``postgresql://...?sslmode=...`` for libpq
    consumers. SQLAlchemy would resolve that scheme to psycopg2 (not shipped here) and asyncpg
    rejects ``sslmode`` as a connect keyword, so the scheme is pinned and ``sslmode`` becomes
    asyncpg's ``ssl``. The route is a transaction-pooling PgBouncer, so server-side prepared
    statements are never cached and no startup parameters are sent.
    """
    parts = urlsplit(url)
    if parts.scheme not in {"postgresql", "postgres", "postgresql+asyncpg"}:
        return url, {}
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    # No server_settings: the transaction-pooling PgBouncer rejects startup parameters such as
    # search_path; the billing_runtime role default (59-wc124-billing-authority.sql) supplies it.
    connect_args: dict[str, Any] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
    sslmode = query.pop("sslmode", None)
    if sslmode is not None:
        if sslmode not in _ASYNCPG_SSL_MODES:
            raise ValueError(f"Unsupported DATABASE_URL sslmode: {sslmode}")
        connect_args["ssl"] = _ASYNCPG_SSL_MODES[sslmode]
    target = urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, urlencode(query), parts.fragment))
    return target, connect_args


async def init_db() -> None:
    global _engine, _session_factory
    database_url, connect_args = asyncpg_engine_target(settings.DATABASE_URL)
    _engine = create_async_engine(database_url, echo=False, connect_args=connect_args)
    # Fail closed at startup: the readiness probe must not report a runtime whose database
    # route is misconfigured, so the route is exercised once before the application serves.
    async with _engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _session_factory


async def close_db() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    async with _session_factory() as session:
        yield session
