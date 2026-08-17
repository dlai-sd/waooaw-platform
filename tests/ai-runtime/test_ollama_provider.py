# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer
# constitutional_basis: C-023, C-059, C-063, C-076
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from providers.ollama_provider import OllamaProvider


def _response(status: int, body: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = body
    if status >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "provider failure",
            request=httpx.Request("POST", "http://ollama:11434/api/generate"),
            response=httpx.Response(status),
        )
    return response


async def test_complete_normalizes_response_and_records_without_logging_prompt() -> None:
    client = AsyncMock()
    client.post.return_value = _response(
        200,
        {"response": "answer", "prompt_eval_count": 7, "eval_count": 3},
    )
    provider = OllamaProvider(client, None)

    result = await provider.complete(
        [
            {"role": "system", "content": "policy"},
            {"role": "assistant", "content": "prior"},
            {"role": "user", "content": "question"},
            {"content": "default-user"},
        ],
        {"model": "local-model", "temperature": 0.2, "max_tokens": 64},
        tenant_id="tenant-a",
        session_id="session-a",
    )

    assert result | {"latency_ms": 0, "dispatch_id": ""} == {
        "content": "answer",
        "model": "local-model",
        "provider": "ollama",
        "input_tokens": 7,
        "output_tokens": 3,
        "latency_ms": 0,
        "dispatch_id": "",
    }
    payload = client.post.await_args.kwargs["json"]
    assert payload["options"] == {"temperature": 0.2, "num_predict": 64}
    assert "[SYSTEM]\npolicy" in payload["prompt"]
    assert "[ASSISTANT]\nprior" in payload["prompt"]
    assert payload["prompt"].count("[USER]") == 2


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (httpx.ReadTimeout("slow"), "TIMEOUT"),
        (_response(503, {}), "HTTP_503"),
    ],
)
async def test_complete_records_provider_failures(failure: object, expected_code: str) -> None:
    client = AsyncMock()
    if isinstance(failure, BaseException):
        client.post.side_effect = failure
    else:
        client.post.return_value = failure
    provider = OllamaProvider(client, None)
    provider._record_dispatch_event = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises((httpx.TimeoutException, httpx.HTTPStatusError)):
        await provider.complete([], {}, tenant_id="tenant-a", session_id="session-a")

    assert provider._record_dispatch_event.await_args.kwargs["error_code"] == expected_code
    assert provider._record_dispatch_event.await_args.kwargs["success"] is False


async def test_complete_propagates_cancellation_without_recording() -> None:
    client = AsyncMock()
    client.post.side_effect = asyncio.CancelledError()
    provider = OllamaProvider(client, None)
    provider._record_dispatch_event = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(asyncio.CancelledError):
        await provider.complete([], {}, tenant_id="tenant-a", session_id="session-a")

    provider._record_dispatch_event.assert_not_awaited()


class _Acquire:
    def __init__(self, connection: AsyncMock) -> None:
        self.connection = connection

    async def __aenter__(self) -> AsyncMock:
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        return None


async def test_dispatch_evidence_write_and_database_failure_are_bounded() -> None:
    connection = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = _Acquire(connection)
    provider = OllamaProvider(AsyncMock(), pool)
    event = {
        "dispatch_id": "dispatch-a",
        "tenant_id": "tenant-a",
        "session_id": "session-a",
        "model": "model-a",
        "tier": "LOCAL",
        "latency_ms": 4.0,
        "input_tokens": 2,
        "output_tokens": 1,
        "success": True,
        "error_code": None,
    }

    await provider._record_dispatch_event(**event)
    connection.execute.assert_awaited_once()

    connection.execute.side_effect = OSError("database unavailable")
    await provider._record_dispatch_event(**event)

    connection.execute.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await provider._record_dispatch_event(**event)
