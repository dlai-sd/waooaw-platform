# Implements: architecture/reference/components/ai-runtime.md §7 PII Scrubber
# constitutional_basis: C-023, C-059, C-063, C-076
from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from rag import retriever


def test_embed_pipeline_is_cached_and_mean_pools_tokens(caplog: pytest.LogCaptureFixture) -> None:
    retriever._embed_pipeline = None
    pipe = MagicMock(return_value=[[[1.0, 3.0], [3.0, 5.0]]])

    with (
        caplog.at_level(logging.INFO, logger="rag.retriever"),
        patch("rag.retriever.hf_pipeline", return_value=pipe) as factory,
    ):
        assert retriever._embed_text("query") == [2.0, 4.0]
        assert retriever._get_embed_pipeline() is pipe

    factory.assert_called_once_with("feature-extraction", model="ai4bharat/indic-bert")
    pipe.assert_called_once_with("query")
    assert caplog.messages == ["Loading IndicBERT pipeline from HuggingFace: ai4bharat/indic-bert"]


class _Loop:
    def __init__(self, result: list[float] | BaseException) -> None:
        self.result = result

    async def run_in_executor(self, *_args: object) -> list[float]:
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


@pytest.mark.parametrize("query", [None, "", "  "])
async def test_retrieve_validates_query(query: str | None) -> None:
    with pytest.raises(ValueError, match="retrieve_chunks: query must be a non-empty string"):
        await retriever.retrieve_chunks(query, "postgresql://unused")  # type: ignore[arg-type]


@pytest.mark.parametrize("failure", [OSError("model"), RuntimeError("runtime")])
async def test_retrieve_wraps_embedding_failure(
    failure: BaseException,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(logging.ERROR, logger="rag.retriever"),
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop(failure)),
    ):
        with pytest.raises(ValueError, match="Embedding generation failed") as raised:
            await retriever.retrieve_chunks("query", "postgresql://unused")

    assert raised.value.__cause__ is failure
    assert caplog.messages == ["IndicBERT embedding failed"]
    assert caplog.records[0].context == "retrieve_chunks.embed"


async def test_retrieve_propagates_embedding_cancellation() -> None:
    with patch(
        "rag.retriever.asyncio.get_event_loop",
        return_value=_Loop(asyncio.CancelledError()),
    ):
        with pytest.raises(asyncio.CancelledError):
            await retriever.retrieve_chunks("query", "postgresql://unused")


async def test_retrieve_returns_content_and_closes_connection(caplog: pytest.LogCaptureFixture) -> None:
    connection = AsyncMock()
    connection.fetch.return_value = [{"content": "first"}, {"content": "second"}]

    with (
        caplog.at_level(logging.INFO, logger="rag.retriever"),
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop([0.1, 0.2])),
        patch("rag.retriever.asyncpg.connect", new=AsyncMock(return_value=connection)) as connect,
        patch("rag.retriever.register_vector", new=AsyncMock()) as register,
    ):
        chunks = await retriever.retrieve_chunks("query", "postgresql://db", top_k=2)

    assert chunks == ["first", "second"]
    connect.assert_awaited_once_with("postgresql://db")
    register.assert_awaited_once_with(connection)
    assert connection.fetch.await_args.args == (
        "SELECT content FROM professional.agent_prompts ORDER BY embedding <=> $1 LIMIT $2",
        [0.1, 0.2],
        2,
    )
    connection.close.assert_awaited_once()
    assert caplog.messages == ["RAG retrieval returned 2 chunk(s) for query (length=5 chars)"]


async def test_retrieve_propagates_database_and_close_failures_safely(caplog: pytest.LogCaptureFixture) -> None:
    connection = AsyncMock()
    connection.fetch.side_effect = asyncpg.PostgresError("query failed")
    connection.close.side_effect = asyncpg.PostgresError("close failed")

    with (
        caplog.at_level(logging.ERROR, logger="rag.retriever"),
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop([0.1])),
        patch("rag.retriever.asyncpg.connect", new=AsyncMock(return_value=connection)),
        patch("rag.retriever.register_vector", new=AsyncMock()),
    ):
        with pytest.raises(asyncpg.PostgresError, match="query failed"):
            await retriever.retrieve_chunks("query", "postgresql://db")

    connection.close.assert_awaited_once()
    assert caplog.messages == ["pgvector retrieval query failed", "Failed to close asyncpg connection"]
    assert [record.context for record in caplog.records] == ["retrieve_chunks.query", "retrieve_chunks.close"]


async def test_retrieve_returns_rows_when_connection_close_fails(caplog: pytest.LogCaptureFixture) -> None:
    connection = AsyncMock()
    connection.fetch.return_value = [{"content": "result"}]
    connection.close.side_effect = asyncpg.PostgresError("close failed")

    with (
        caplog.at_level(logging.ERROR, logger="rag.retriever"),
        patch("rag.retriever.asyncio.get_event_loop", return_value=_Loop([0.1])),
        patch("rag.retriever.asyncpg.connect", new=AsyncMock(return_value=connection)),
        patch("rag.retriever.register_vector", new=AsyncMock()),
    ):
        assert await retriever.retrieve_chunks("query", "postgresql://db", top_k=1) == ["result"]

    assert caplog.messages[-1] == "Failed to close asyncpg connection"
    assert caplog.records[-1].context == "retrieve_chunks.close"


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
