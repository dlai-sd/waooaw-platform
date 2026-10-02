# Implements: architecture/reference/components/ai-runtime.md §7 PII Scrubber
# constitutional_basis: C-023, C-059, C-063, C-076
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from rag import retriever


def test_embed_pipeline_is_cached_and_mean_pools_tokens() -> None:
    retriever._embed_pipeline = None
    pipe = MagicMock(return_value=[[[1.0, 3.0], [3.0, 5.0]]])

    with patch("rag.retriever.hf_pipeline", return_value=pipe) as factory:
        assert retriever._embed_text("query") == [2.0, 4.0]
        assert retriever._get_embed_pipeline() is pipe

    factory.assert_called_once_with("feature-extraction", model="ai4bharat/indic-bert")


class _Loop:
    def __init__(self, result: list[float] | BaseException) -> None:
        self.result = result

    async def run_in_executor(self, *_args: object) -> list[float]:
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


async def test_retrieve_validates_query_and_wraps_embedding_failure() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        await retriever.retrieve_chunks("  ", "postgresql://unused")

    with patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop(OSError("model"))):
        with pytest.raises(ValueError, match="Embedding generation failed"):
            await retriever.retrieve_chunks("query", "postgresql://unused")

    with patch(
        "rag.retriever.asyncio.get_event_loop",
        return_value=_Loop(asyncio.CancelledError()),
    ):
        with pytest.raises(asyncio.CancelledError):
            await retriever.retrieve_chunks("query", "postgresql://unused")


async def test_retrieve_returns_content_and_closes_connection() -> None:
    connection = AsyncMock()
    connection.fetch.return_value = [{"content": "first"}, {"content": "second"}]

    with (
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop([0.1, 0.2])),
        patch("rag.retriever.asyncpg.connect", new=AsyncMock(return_value=connection)) as connect,
        patch("rag.retriever.register_vector", new=AsyncMock()) as register,
    ):
        chunks = await retriever.retrieve_chunks("query", "postgresql://db", top_k=2)

    assert chunks == ["first", "second"]
    connect.assert_awaited_once_with("postgresql://db")
    register.assert_awaited_once_with(connection)
    assert connection.fetch.await_args.args[-2:] == ([0.1, 0.2], 2)
    connection.close.assert_awaited_once()


async def test_retrieve_propagates_database_and_close_failures_safely() -> None:
    connection = AsyncMock()
    connection.fetch.side_effect = asyncpg.PostgresError("query failed")
    connection.close.side_effect = asyncpg.PostgresError("close failed")

    with (
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop([0.1])),
        patch("rag.retriever.asyncpg.connect", new=AsyncMock(return_value=connection)),
        patch("rag.retriever.register_vector", new=AsyncMock()),
    ):
        with pytest.raises(asyncpg.PostgresError, match="query failed"):
            await retriever.retrieve_chunks("query", "postgresql://db")

    connection.close.assert_awaited_once()


async def test_retrieve_propagates_cancellation_after_connection() -> None:
    connection = AsyncMock()
    connection.fetch.side_effect = asyncio.CancelledError()

    with (
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop([0.1])),
        patch("rag.retriever.asyncpg.connect", new=AsyncMock(return_value=connection)),
        patch("rag.retriever.register_vector", new=AsyncMock()),
    ):
        with pytest.raises(asyncio.CancelledError):
            await retriever.retrieve_chunks("query", "postgresql://db")

    connection.close.assert_awaited_once()
