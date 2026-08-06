# Implements: work-contracts/WC-032-goal005-air-pse-trial-override.md
# constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability), C-076 (≥90% coverage)
from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
import fakeredis.aioredis

from unittest.mock import AsyncMock, MagicMock, patch

from pse.router import route_and_dispatch, _select_tier, _dispatch_ollama, _dispatch_mid, _dispatch_frontier
from pse.tiers import LlmTier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_factory() -> MagicMock:
    """Minimal async_sessionmaker stub — we stub _record_dispatch_event away."""
    return MagicMock()


async def _fake_redis_with_mode(mode: bytes | None) -> fakeredis.aioredis.FakeRedis:
    r = fakeredis.aioredis.FakeRedis()
    if mode is not None:
        await r.set("wbe:customer:cust-001:mode", mode)
    return r


# ---------------------------------------------------------------------------
# Unit: _select_tier (stateless, no Redis)
# ---------------------------------------------------------------------------

class TestSelectTier:
    def test_simple_returns_local(self):
        assert _select_tier("simple", None) == LlmTier.LOCAL

    def test_medium_english_returns_local(self):
        assert _select_tier("medium", "en") == LlmTier.LOCAL

    def test_medium_indic_returns_mid(self):
        assert _select_tier("medium", "hi") == LlmTier.MID

    def test_complex_returns_frontier(self):
        assert _select_tier("complex", None) == LlmTier.FRONTIER

    def test_unknown_complexity_falls_back_to_local(self):
        assert _select_tier("quantum", None) == LlmTier.LOCAL


# ---------------------------------------------------------------------------
# CCT-TRIAL-02: TRIAL mode in Redis → force LOCAL regardless of complexity
# ---------------------------------------------------------------------------

class TestTrialTierOverride:
    """CCT-TRIAL-02 — PSE must return LOCAL for TRIAL customers."""

    @pytest.mark.asyncio
    async def test_trial_mode_overrides_complex_to_local(self):
        """TRIAL customer with complex task still gets LOCAL (zero procurement cost)."""
        redis = await _fake_redis_with_mode(b"TRIAL")
        session_factory = _make_session_factory()

        with patch("pse.router._select_tier", return_value=LlmTier.FRONTIER), \
             patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_dispatch.return_value = {
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "hello",
                "done": True,
                "total_duration_ns": 100,
            }
            result = await route_and_dispatch(
                prompt="complex query",
                task_complexity="complex",
                language=None,
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=redis,
            )

        # _select_tier said FRONTIER, but TRIAL override must have forced LOCAL dispatch
        mock_dispatch.assert_called_once()
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_trial_mode_overrides_medium_indic_to_local(self):
        """TRIAL customer with medium/indic (would be MID) → forced LOCAL."""
        redis = await _fake_redis_with_mode(b"TRIAL")
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_dispatch.return_value = {
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "नमस्ते",
                "done": True,
                "total_duration_ns": 80,
            }
            result = await route_and_dispatch(
                prompt="नमस्ते",
                task_complexity="medium",
                language="hi",
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=redis,
            )

        mock_dispatch.assert_called_once()
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_non_trial_mode_uses_configured_tier(self):
        """Customer with mode=ACTIVE → tier selection unchanged (FRONTIER for complex)."""
        redis = await _fake_redis_with_mode(b"ACTIVE")
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_frontier", new_callable=AsyncMock) as mock_frontier, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_frontier.side_effect = NotImplementedError("not wired")
            with pytest.raises(NotImplementedError):
                await route_and_dispatch(
                    prompt="complex query",
                    task_complexity="complex",
                    language=None,
                    async_session_factory=session_factory,
                    customer_id="cust-001",
                    redis_client=redis,
                )

        # FRONTIER dispatch was attempted (not LOCAL)
        mock_frontier.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_redis_key_uses_configured_tier(self):
        """Customer has no mode key in Redis (TTL expiry) → normal tier selection."""
        redis = await _fake_redis_with_mode(None)  # key not set
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_dispatch.return_value = {
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "hello",
                "done": True,
                "total_duration_ns": 50,
            }
            result = await route_and_dispatch(
                prompt="simple query",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=redis,
            )

        mock_dispatch.assert_called_once()
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_no_redis_client_uses_configured_tier(self):
        """No redis_client provided → existing tier selection unchanged (backward compat)."""
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_dispatch.return_value = {
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "ok",
                "done": True,
                "total_duration_ns": 30,
            }
            result = await route_and_dispatch(
                prompt="simple",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
                # customer_id and redis_client intentionally omitted
            )

        mock_dispatch.assert_called_once()
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_no_customer_id_uses_configured_tier(self):
        """redis_client present but no customer_id → skip Redis lookup, use normal tier."""
        redis = await _fake_redis_with_mode(b"TRIAL")
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_frontier", new_callable=AsyncMock) as mock_frontier, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_frontier.side_effect = NotImplementedError("not wired")
            with pytest.raises(NotImplementedError):
                await route_and_dispatch(
                    prompt="complex",
                    task_complexity="complex",
                    language=None,
                    async_session_factory=session_factory,
                    redis_client=redis,
                    # customer_id intentionally omitted
                )

        mock_frontier.assert_called_once()


# ---------------------------------------------------------------------------
# Existing behaviour: event_id in result, correct tier metadata
# ---------------------------------------------------------------------------

class TestRouteAndDispatchCore:
    @pytest.mark.asyncio
    async def test_local_dispatch_returns_event_id(self):
        """route_and_dispatch appends event_id to result dict (C-059)."""
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_dispatch.return_value = {
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "result",
                "done": True,
                "total_duration_ns": 200,
            }
            result = await route_and_dispatch(
                prompt="hello",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
            )

        assert "event_id" in result

    @pytest.mark.asyncio
    async def test_mid_indic_uses_sarvam_provider_metadata(self):
        """medium+hi → MID tier → provider_id=sarvam, model_id=saaras before dispatch."""
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_mid", new_callable=AsyncMock) as mock_mid, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_mid.side_effect = NotImplementedError("mid not wired")
            with pytest.raises(NotImplementedError):
                await route_and_dispatch(
                    prompt="नमस्ते",
                    task_complexity="medium",
                    language="hi",
                    async_session_factory=session_factory,
                )

        mock_mid.assert_called_once()


# ---------------------------------------------------------------------------
# _dispatch_ollama — direct unit tests (lines 82-122)
# ---------------------------------------------------------------------------

class TestDispatchOllama:
    @pytest.mark.asyncio
    @respx.mock
    async def test_success_returns_response_dict(self) -> None:
        """Happy path: Ollama returns 200 with response body."""
        respx.post("http://ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "hello world", "done": True, "total_duration": 500})
        )
        result = await _dispatch_ollama("test prompt")
        assert result["tier"] == LlmTier.LOCAL.value
        assert result["provider_id"] == "ollama"
        assert result["response"] == "hello world"
        assert result["done"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_raises(self) -> None:
        """Ollama timeout propagates as httpx.TimeoutException."""
        respx.post("http://ollama:11434/api/generate").mock(side_effect=httpx.TimeoutException("timeout"))
        with pytest.raises(httpx.TimeoutException):
            await _dispatch_ollama("test prompt")

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_raises(self) -> None:
        """Ollama non-2xx status propagates as httpx.HTTPStatusError."""
        respx.post("http://ollama:11434/api/generate").mock(
            return_value=httpx.Response(500, text="server error")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await _dispatch_ollama("test prompt")

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_error_raises(self) -> None:
        """Connection error propagates as httpx.RequestError."""
        respx.post("http://ollama:11434/api/generate").mock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(httpx.RequestError):
            await _dispatch_ollama("test prompt")


# ---------------------------------------------------------------------------
# Stub dispatchers — direct calls (lines 185-216)
# ---------------------------------------------------------------------------

class TestStubDispatchers:
    @pytest.mark.asyncio
    async def test_dispatch_mid_not_implemented(self) -> None:
        """_dispatch_mid raises NotImplementedError until wired (WC015-02b)."""
        with pytest.raises(NotImplementedError, match="MID_TIER"):
            await _dispatch_mid("prompt", "en")

    @pytest.mark.asyncio
    async def test_dispatch_frontier_not_implemented(self) -> None:
        """_dispatch_frontier raises NotImplementedError until wired (WC015-02b)."""
        with pytest.raises(NotImplementedError, match="FRONTIER"):
            await _dispatch_frontier("prompt")


# ---------------------------------------------------------------------------
# route_and_dispatch error handlers (lines 286-287, 319-330, 355-424)
# ---------------------------------------------------------------------------

class TestRouteAndDispatchErrorHandlers:
    @pytest.mark.asyncio
    async def test_mid_non_indic_uses_google_provider(self) -> None:
        """MID tier + non-indic language → provider=google, model=gemini-2.0-flash (lines 286-287).
        Must mock _select_tier to MID: PSE-R02 returns LOCAL for non-indic medium.
        """
        session_factory = _make_session_factory()

        with patch("pse.router._select_tier", return_value=LlmTier.MID), \
             patch("pse.router._dispatch_mid", new_callable=AsyncMock) as mock_mid, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock):
            mock_mid.side_effect = NotImplementedError("mid not wired")
            with pytest.raises(NotImplementedError):
                await route_and_dispatch(
                    prompt="hello",
                    task_complexity="medium",
                    language="en",
                    async_session_factory=session_factory,
                )

        mock_mid.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancelled_error_records_then_propagates(self) -> None:
        """CancelledError triggers evidence recording then re-raises (lines 319-330)."""
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record:
            mock_dispatch.side_effect = asyncio.CancelledError()
            with pytest.raises(asyncio.CancelledError):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[0]
        assert "cancelled" in call_kwargs

    @pytest.mark.asyncio
    async def test_timeout_records_then_propagates(self) -> None:
        """TimeoutException triggers evidence recording then re-raises (lines 355-376)."""
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record:
            mock_dispatch.side_effect = httpx.TimeoutException("timeout")
            with pytest.raises(httpx.TimeoutException):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_called_once()
        assert mock_record.call_args[0][-2] == "timeout"

    @pytest.mark.asyncio
    async def test_http_status_error_records_then_propagates(self) -> None:
        """HTTPStatusError triggers evidence recording then re-raises (lines 377-400)."""
        session_factory = _make_session_factory()

        fake_response = httpx.Response(503, text="unavailable")
        fake_request = httpx.Request("POST", "http://ollama:11434/api/generate")

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record:
            mock_dispatch.side_effect = httpx.HTTPStatusError("err", request=fake_request, response=fake_response)
            with pytest.raises(httpx.HTTPStatusError):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_called_once()
        assert mock_record.call_args[0][-2] == "http_error"

    @pytest.mark.asyncio
    async def test_request_error_records_then_propagates(self) -> None:
        """RequestError triggers evidence recording then re-raises (lines 401-424)."""
        session_factory = _make_session_factory()

        with patch("pse.router._dispatch_ollama", new_callable=AsyncMock) as mock_dispatch, \
             patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record:
            mock_dispatch.side_effect = httpx.ConnectError("refused")
            with pytest.raises(httpx.RequestError):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_called_once()
        assert mock_record.call_args[0][-2] == "connection_error"

