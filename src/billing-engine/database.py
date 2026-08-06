# Implements: WBE database session factory
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    global _engine, _session_factory
    _engine = create_async_engine(settings.DATABASE_URL, echo=False)
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
