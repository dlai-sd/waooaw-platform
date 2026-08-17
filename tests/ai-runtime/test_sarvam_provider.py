# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer
# constitutional_basis: C-023, C-059, C-063, C-076
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from providers.sarvam_provider import SARVAM_PROVIDER_ID, SarvamProvider, SarvamProviderError


def _response(status: int, body: object = None, *, invalid_json: bool = False) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    if invalid_json:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = body
    return response


async def test_complete_builds_payload_normalizes_response_and_closes() -> None:
    provider = SarvamProvider("secret")
    provider._client = AsyncMock()
    provider._client.post.return_value = _response(
        200,
        {
            "choices": [{"message": {"content": "namaste"}}],
            "model": "saaras-v1",
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        },
    )

    result = await provider.complete(
        [{"role": "user", "content": "hello"}],
        {"temperature": 0.3, "max_tokens": 50, "top_p": 0.8},
    )

    assert result["content"] == "namaste"
    assert result["model"] == "saaras-v1"
    assert result["provider"] == SARVAM_PROVIDER_ID
    payload = provider._client.post.await_args.kwargs["json"]
    assert payload == {
        "model": "saaras",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.3,
        "max_tokens": 50,
        "top_p": 0.8,
    }
    assert provider._client.post.await_args.kwargs["headers"]["Authorization"] == "Bearer secret"
    await provider.close()
    provider._client.aclose.assert_awaited_once()


@pytest.mark.parametrize(
    ("response", "transport_error", "message"),
    [
        (None, httpx.ReadTimeout("slow"), "timed out"),
        (None, httpx.ConnectError("offline"), "transport error"),
        (_response(429, {}), None, "HTTP 429"),
        (_response(200, invalid_json=True), None, "non-JSON"),
        (_response(200, {"choices": []}), None, "missing expected fields"),
    ],
)
async def test_complete_converts_upstream_failures(
    response: MagicMock | None,
    transport_error: Exception | None,
    message: str,
) -> None:
    provider = SarvamProvider("secret", timeout_seconds=0.1)
    provider._client = AsyncMock()
    if transport_error is not None:
        provider._client.post.side_effect = transport_error
    else:
        provider._client.post.return_value = response
    provider._record_dispatch_event = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(SarvamProviderError, match=message):
        await provider.complete([], None)

    provider._record_dispatch_event.assert_awaited_once()


async def test_complete_propagates_cancellation() -> None:
    provider = SarvamProvider("secret")
    provider._client = AsyncMock()
    provider._client.post.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await provider.complete([], {})


class _Acquire:
    def __init__(self, connection: AsyncMock) -> None:
        self.connection = connection

    async def __aenter__(self) -> AsyncMock:
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        return None


async def test_dispatch_event_persists_usage_and_bounds_database_failure() -> None:
    connection = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = _Acquire(connection)
    provider = SarvamProvider("secret", pool)
    usage = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}

    await provider._record_dispatch_event("dispatch-a", "success", 5.0, "saaras", usage)
    assert connection.execute.await_args.args[-3:] == (3, 2, 5)

    connection.execute.side_effect = OSError("database unavailable")
    await provider._record_dispatch_event("dispatch-b", "success", 5.0, "saaras", usage)

    connection.execute.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await provider._record_dispatch_event("dispatch-c", "success", 5.0, "saaras", usage)
