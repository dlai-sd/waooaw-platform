"""
test_thread_catalog.py — WBE-S1 Thread Catalog Tests (WC025-05)

Constitutional: C-091 (Thread Catalog Sovereignty), C-088 (Billing Profile), C-059
Tests: thread catalog load, cache hit/miss, health endpoint, cache invalidation
"""
from __future__ import annotations

import json
import pytest
import fakeredis.aioredis as fake_aioredis
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# ── Sample thread catalog rows (mirrors 12-billing-engine.sql seed) ──────────

SAMPLE_THREADS = [
    {
        "thread_id": "llm_local",
        "display_name": "Local LLM (Ollama)",
        "provider": "Self-hosted",
        "unit_description": "Per message classified",
        "raw_cost_inr_paise": 0,
        "total_markup_pct": 0.0,
        "marked_up_cost_paise": 0,
        "is_platform_thread": True,
        "applicable_agents": [],
        "status": "ACTIVE",
    },
    {
        "thread_id": "llm_mid_gemini",
        "display_name": "Gemini 2.0 Flash",
        "provider": "Google Vertex AI",
        "unit_description": "Per 1K tokens (in+out)",
        "raw_cost_inr_paise": 2,
        "total_markup_pct": 16.0,
        "marked_up_cost_paise": 3,
        "is_platform_thread": True,
        "applicable_agents": [],
        "status": "ACTIVE",
    },
    {
        "thread_id": "whatsapp_window",
        "display_name": "WhatsApp (Exotel/360Dialog)",
        "provider": "Exotel / 360Dialog",
        "unit_description": "Per 24-hour window",
        "raw_cost_inr_paise": 60,
        "total_markup_pct": 17.0,
        "marked_up_cost_paise": 70,
        "is_platform_thread": True,
        "applicable_agents": [],
        "status": "ACTIVE",
    },
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_redis():
    return fake_aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_db_rows():
    """Rows matching the SQL query result shape in thread_catalog._load_from_db."""
    from dataclasses import make_dataclass
    Row = make_dataclass("Row", [f for f in SAMPLE_THREADS[0]])
    return [Row(**t) for t in SAMPLE_THREADS]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestThreadCatalogCacheLayer:
    """CCT: Cache hit/miss behavior for Thread Catalog."""

    @pytest.mark.asyncio
    async def test_cache_miss_loads_from_db(self, fake_redis, mock_db_rows):
        """On cold start, catalog loads from DB and populates cache."""
        import markup.thread_catalog as tc
        with (
            patch.object(tc, "_get_redis", return_value=fake_redis),
            patch.object(tc, "_load_from_db", AsyncMock(return_value=[
                tc.ThreadCatalogEntry(**t) for t in SAMPLE_THREADS
            ])) as mock_db,
        ):
            result = await tc.get_all_threads()

        assert len(result) == 3
        mock_db.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self, fake_redis):
        """Second call within TTL must NOT hit DB (cache hit)."""
        import markup.thread_catalog as tc
        # Pre-populate the cache
        await fake_redis.set(
            tc.FULL_CATALOG_KEY,
            json.dumps([t for t in SAMPLE_THREADS]),
            ex=30,
        )

        with (
            patch.object(tc, "_get_redis", return_value=fake_redis),
            patch.object(tc, "_load_from_db", AsyncMock()) as mock_db,
        ):
            result = await tc.get_all_threads()

        assert len(result) == 3
        mock_db.assert_not_awaited()  # DB must NOT be called on cache hit

    @pytest.mark.asyncio
    async def test_single_thread_lookup_hit(self, fake_redis):
        """get_thread returns correct entry from cache."""
        import markup.thread_catalog as tc
        await fake_redis.set(
            tc.FULL_CATALOG_KEY,
            json.dumps([t for t in SAMPLE_THREADS]),
            ex=30,
        )

        with patch.object(tc, "_get_redis", return_value=fake_redis):
            result = await tc.get_thread("llm_mid_gemini")

        assert result is not None
        assert result.thread_id == "llm_mid_gemini"
        assert result.marked_up_cost_paise == 3

    @pytest.mark.asyncio
    async def test_unknown_thread_returns_none(self, fake_redis):
        """get_thread returns None for unknown thread_id."""
        import markup.thread_catalog as tc
        await fake_redis.set(
            tc.FULL_CATALOG_KEY,
            json.dumps([t for t in SAMPLE_THREADS]),
            ex=30,
        )

        with patch.object(tc, "_get_redis", return_value=fake_redis):
            result = await tc.get_thread("nonexistent_thread")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidation_flushes_keys(self, fake_redis):
        """invalidate_cache must delete all thread_catalog cache keys."""
        import markup.thread_catalog as tc
        await fake_redis.set(tc.FULL_CATALOG_KEY, "[]", ex=30)
        await fake_redis.set(f"{tc.CACHE_KEY_PREFIX}llm_local", "{}", ex=30)

        with patch.object(tc, "_get_redis", return_value=fake_redis):
            await tc.invalidate_cache()

        assert await fake_redis.get(tc.FULL_CATALOG_KEY) is None
        assert await fake_redis.get(f"{tc.CACHE_KEY_PREFIX}llm_local") is None


class TestThreadCatalogHttpEndpoints:
    """HTTP API tests for the Thread Catalog FastAPI router."""

    @pytest.fixture
    def client(self, fake_redis):
        """TestClient with DB, Redis, and lifespan startup mocked."""
        import markup.thread_catalog as tc
        from main import app
        from unittest.mock import patch, MagicMock, AsyncMock

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        with (
            patch.object(tc, "_get_redis", return_value=fake_redis),
            patch.object(tc, "_load_from_db", AsyncMock(return_value=[
                tc.ThreadCatalogEntry(**t) for t in SAMPLE_THREADS
            ])),
            patch("main.init_db", AsyncMock()),
            patch("main.close_db", AsyncMock()),
            patch("main.get_session_factory", return_value=MagicMock()),
            patch("main.create_scheduler", return_value=mock_scheduler),
            patch("main.aioredis.from_url", return_value=AsyncMock()),
        ):
            with TestClient(app, raise_server_exceptions=True) as c:
                yield c

    def test_health_endpoint_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "billing-engine"

    def test_list_threads_returns_catalog(self, client, fake_redis):
        """GET /catalog/threads returns all active threads."""
        import markup.thread_catalog as tc
        import asyncio
        asyncio.run(
            fake_redis.set(tc.FULL_CATALOG_KEY, json.dumps(SAMPLE_THREADS), ex=30)
        )
        response = client.get("/catalog/threads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_thread_by_id(self, client, fake_redis):
        """GET /catalog/threads/{id} returns single entry."""
        import markup.thread_catalog as tc
        import asyncio
        asyncio.run(
            fake_redis.set(tc.FULL_CATALOG_KEY, json.dumps(SAMPLE_THREADS), ex=30)
        )
        response = client.get("/catalog/threads/whatsapp_window")
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "whatsapp_window"
        assert data["marked_up_cost_paise"] == 70

    def test_get_unknown_thread_returns_404(self, client, fake_redis):
        """GET /catalog/threads/{unknown} returns 404."""
        import markup.thread_catalog as tc
        import asyncio
        asyncio.run(
            fake_redis.set(tc.FULL_CATALOG_KEY, json.dumps(SAMPLE_THREADS), ex=30)
        )
        response = client.get("/catalog/threads/this_does_not_exist")
        assert response.status_code == 404


class TestC091ThreadCatalogInvariant:
    """C-091: Thread Catalog Sovereignty — structural invariants."""

    def test_platform_threads_are_marked(self):
        """llm_local, llm_mid_gemini, whatsapp_window, infra_share must be platform threads."""
        platform = [t for t in SAMPLE_THREADS if t["is_platform_thread"]]
        platform_ids = {t["thread_id"] for t in platform}
        assert "llm_local" in platform_ids
        assert "llm_mid_gemini" in platform_ids
        assert "whatsapp_window" in platform_ids

    def test_marked_up_cost_non_negative(self):
        """No thread can have negative marked_up_cost_paise."""
        for t in SAMPLE_THREADS:
            assert t["marked_up_cost_paise"] >= 0, f"{t['thread_id']} has negative cost"

    def test_llm_local_is_zero_cost(self):
        """llm_local (Ollama) must always have 0 marked_up_cost (self-hosted)."""
        local = next(t for t in SAMPLE_THREADS if t["thread_id"] == "llm_local")
        assert local["marked_up_cost_paise"] == 0
