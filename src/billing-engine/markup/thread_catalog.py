# Implements: architecture/reference/billing/wbe-component-spec.md §2.5 Thread Catalog
# constitutional_basis: C-091 (Thread Catalog Sovereignty), C-059, ADR-034

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Redis client (shared singleton) ──────────────────────────────────────────
_redis: Optional[aioredis.Redis] = None

CACHE_KEY_PREFIX = "wbe:thread_catalog:"
FULL_CATALOG_KEY = "wbe:thread_catalog:all"


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


# ── DB engine (shared singleton) ─────────────────────────────────────────────
_engine = None
_async_session: Optional[sessionmaker] = None


def _get_session_factory() -> sessionmaker:
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


# ── Domain model ─────────────────────────────────────────────────────────────

@dataclass
class ThreadCatalogEntry:
    thread_id: str
    display_name: str
    provider: str
    unit_description: str
    raw_cost_inr_paise: int
    total_markup_pct: float
    marked_up_cost_paise: int
    is_platform_thread: bool
    applicable_agents: list[str]
    status: str


# ── DB load ───────────────────────────────────────────────────────────────────

async def _load_from_db() -> list[ThreadCatalogEntry]:
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT thread_id, display_name, provider, unit_description, "
                "raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise, "
                "is_platform_thread, applicable_agents, status "
                "FROM institutional.thread_catalog "
                "WHERE status != 'DEPRECATED' "
                "ORDER BY thread_id"
            )
        )
        rows = result.fetchall()
    return [
        ThreadCatalogEntry(
            thread_id=r.thread_id,
            display_name=r.display_name,
            provider=r.provider,
            unit_description=r.unit_description,
            raw_cost_inr_paise=r.raw_cost_inr_paise,
            total_markup_pct=float(r.total_markup_pct),
            marked_up_cost_paise=r.marked_up_cost_paise,
            is_platform_thread=r.is_platform_thread,
            applicable_agents=list(r.applicable_agents or []),
            status=r.status,
        )
        for r in rows
    ]


# ── Public service layer ──────────────────────────────────────────────────────

async def get_all_threads() -> list[ThreadCatalogEntry]:
    """Load from Redis cache (30s TTL); fall back to DB on miss."""
    redis_client = _get_redis()
    cached = await redis_client.get(FULL_CATALOG_KEY)
    if cached:
        raw = json.loads(cached)
        return [ThreadCatalogEntry(**e) for e in raw]

    entries = await _load_from_db()
    await redis_client.set(
        FULL_CATALOG_KEY,
        json.dumps([e.__dict__ for e in entries]),
        ex=settings.thread_catalog_cache_ttl_seconds,
    )
    return entries


async def get_thread(thread_id: str) -> Optional[ThreadCatalogEntry]:
    """Single-thread lookup via per-key cache."""
    redis_client = _get_redis()
    key = f"{CACHE_KEY_PREFIX}{thread_id}"
    cached = await redis_client.get(key)
    if cached:
        return ThreadCatalogEntry(**json.loads(cached))

    entries = await get_all_threads()
    for e in entries:
        if e.thread_id == thread_id:
            await redis_client.set(
                key,
                json.dumps(e.__dict__),
                ex=settings.thread_catalog_cache_ttl_seconds,
            )
            return e
    return None


async def invalidate_cache() -> None:
    """Flush all thread_catalog keys. Called after catalog update (C-091)."""
    redis_client = _get_redis()
    keys = await redis_client.keys(f"{CACHE_KEY_PREFIX}*")
    keys.append(FULL_CATALOG_KEY)
    if keys:
        await redis_client.delete(*keys)
    logger.info("Thread catalog cache invalidated (%d keys flushed)", len(keys))


# ── FastAPI router ────────────────────────────────────────────────────────────

@router.get("/threads", summary="List all active thread catalog entries (C-091)")
async def list_threads() -> list[dict]:
    entries = await get_all_threads()
    return [e.__dict__ for e in entries]


@router.get("/threads/{thread_id}", summary="Get a single thread entry")
async def get_thread_entry(thread_id: str) -> dict:
    entry = await get_thread(thread_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")
    return entry.__dict__


@router.post("/threads/invalidate-cache", summary="Invalidate Redis cache (C-091 update path)")
async def invalidate_thread_cache() -> dict:
    await invalidate_cache()
    return {"status": "ok", "message": "Thread catalog cache invalidated"}
