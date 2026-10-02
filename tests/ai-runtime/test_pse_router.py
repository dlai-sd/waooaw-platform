# Implements: work-contracts/WC-032-goal005-air-pse-trial-override.md
# Implements: work-contracts/WC-039-trust-layer-s3-ctg-library-air-refactor.md §WC039-06
# constitutional_basis: C-041 (CTG governs every call), C-049, C-059, C-076
from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
import fakeredis.aioredis

from unittest.mock import AsyncMock, MagicMock, patch

from pse.router import route_and_dispatch, _select_tier, _dispatch_ollama, _dispatch_mid, _dispatch_frontier
from pse.tiers import LlmTier

# ctg is importable after pse.router adds src/trust-layer to sys.path on import
from ctg.models import GatewayResult, MCPToolError


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


def _make_mock_gateway(
    result: dict | None = None,
    error: MCPToolError | None = None,
) -> AsyncMock:
    """Return an AsyncMock gateway whose call() returns a GatewayResult."""
    mock_gw = AsyncMock()
    mock_gw.call.return_value = GatewayResult(
        decision_id="DEC-MOCK",
        result=result
        or {
            "tier": LlmTier.LOCAL.value,
            "provider_id": "ollama",
            "model_id": "llama3.2:3b",
            "response": "ok",
            "done": True,
            "total_duration_ns": 50,
        },
        error=error,
    )
    return mock_gw


# ---------------------------------------------------------------------------
# Unit: _select_tier (stateless, no Redis) — UNCHANGED from WC-032
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
# ADR-042 update: tier selection now verified via CTG gateway.call() args
# ---------------------------------------------------------------------------


class TestTrialTierOverride:
    """CCT-TRIAL-02 — PSE must route LOCAL for TRIAL customers (via CTG)."""

    @pytest.mark.asyncio
    async def test_trial_mode_overrides_complex_to_local(self):
        """TRIAL customer with complex task → CTG called with provider=ollama (LOCAL)."""
        redis = await _fake_redis_with_mode(b"TRIAL")
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(
            result={
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "hello",
                "done": True,
                "total_duration_ns": 100,
            }
        )

        with (
            patch("pse.router._select_tier", return_value=LlmTier.FRONTIER),
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            result = await route_and_dispatch(
                prompt="complex query",
                task_complexity="complex",
                language=None,
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=redis,
            )

        # TRIAL override must have forced LOCAL — gateway called with provider=ollama
        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "ollama"
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_validated_trial_entitlement_forces_local_without_redis(self):
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(
            result={
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "hello",
                "done": True,
                "total_duration_ns": 100,
            }
        )

        with (
            patch("pse.router._select_tier", return_value=LlmTier.FRONTIER),
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            result = await route_and_dispatch(
                prompt="complex trial query",
                task_complexity="complex",
                language=None,
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=None,
                trial_entitled=True,
            )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "ollama"
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_validated_trial_local_failure_has_no_paid_fallback(self):
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(error=MCPToolError(code="PROVIDER_ERROR", message="LOCAL unavailable", retry_eligible=True))

        with (
            patch("pse.router._select_tier", return_value=LlmTier.FRONTIER),
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="CTG tool error"):
                await route_and_dispatch(
                    prompt="complex trial query",
                    task_complexity="complex",
                    language=None,
                    async_session_factory=session_factory,
                    trial_entitled=True,
                )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_trial_mode_overrides_medium_indic_to_local(self):
        """TRIAL customer with medium/indic (would be MID) → CTG called with provider=ollama."""
        redis = await _fake_redis_with_mode(b"TRIAL")
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(
            result={
                "tier": LlmTier.LOCAL.value,
                "provider_id": "ollama",
                "model_id": "llama3.2:3b",
                "response": "नमस्ते",
                "done": True,
                "total_duration_ns": 80,
            }
        )

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            result = await route_and_dispatch(
                prompt="नमस्ते",
                task_complexity="medium",
                language="hi",
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=redis,
            )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "ollama"
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_non_trial_mode_uses_configured_tier(self):
        """Customer with mode=ACTIVE → tier selection unchanged (FRONTIER=google for complex)."""
        redis = await _fake_redis_with_mode(b"ACTIVE")
        session_factory = _make_session_factory()
        # FRONTIER provider is google — mock gateway as not-implemented (CTG error path)
        mock_gw = _make_mock_gateway(
            error=MCPToolError(code="PROVIDER_ERROR", message="FRONTIER not wired", retry_eligible=False)
        )
        mock_gw.call.return_value = GatewayResult(
            decision_id="DEC-MOCK",
            error=MCPToolError(code="PROVIDER_ERROR", message="FRONTIER not wired", retry_eligible=False),
        )

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="CTG tool error"):
                await route_and_dispatch(
                    prompt="complex query",
                    task_complexity="complex",
                    language=None,
                    async_session_factory=session_factory,
                    customer_id="cust-001",
                    redis_client=redis,
                )

        # FRONTIER was attempted — gateway called with google provider (not ollama)
        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "google"

    @pytest.mark.asyncio
    async def test_no_redis_key_uses_configured_tier(self):
        """Customer has no mode key in Redis (TTL expiry) → normal tier selection."""
        redis = await _fake_redis_with_mode(None)
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway()

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            result = await route_and_dispatch(
                prompt="simple query",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
                customer_id="cust-001",
                redis_client=redis,
            )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "ollama"
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_no_redis_client_uses_configured_tier(self):
        """No redis_client provided → existing tier selection unchanged (backward compat)."""
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway()

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            result = await route_and_dispatch(
                prompt="simple",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
            )

        mock_gw.call.assert_awaited_once()
        assert result["tier"] == LlmTier.LOCAL.value

    @pytest.mark.asyncio
    async def test_no_customer_id_uses_configured_tier(self):
        """redis_client present but no customer_id → skip Redis lookup, use normal tier."""
        redis = await _fake_redis_with_mode(b"TRIAL")
        session_factory = _make_session_factory()
        # No customer_id → no TRIAL override → complex → FRONTIER = google
        mock_gw = _make_mock_gateway(
            error=MCPToolError(code="PROVIDER_ERROR", message="FRONTIER not wired", retry_eligible=False)
        )
        mock_gw.call.return_value = GatewayResult(
            decision_id="DEC-MOCK",
            error=MCPToolError(code="PROVIDER_ERROR", message="FRONTIER not wired", retry_eligible=False),
        )

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="CTG tool error"):
                await route_and_dispatch(
                    prompt="complex",
                    task_complexity="complex",
                    language=None,
                    async_session_factory=session_factory,
                    redis_client=redis,
                    # customer_id intentionally omitted
                )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "google"


# ---------------------------------------------------------------------------
# Existing behaviour: event_id in result, correct tier metadata
# ---------------------------------------------------------------------------


class TestRouteAndDispatchCore:
    @pytest.mark.asyncio
    async def test_local_dispatch_returns_event_id(self):
        """route_and_dispatch appends event_id to result dict (C-059)."""
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway()

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            result = await route_and_dispatch(
                prompt="hello",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
            )

        assert "event_id" in result

    @pytest.mark.asyncio
    async def test_mid_indic_gateway_called_with_sarvam_provider(self):
        """medium+hi → MID tier → gateway called with provider=sarvam (ADR-042 §3)."""
        session_factory = _make_session_factory()
        # MID+sarvam provider → gateway called with provider=sarvam
        mock_gw = _make_mock_gateway(error=MCPToolError(code="PROVIDER_ERROR", message="mid not wired", retry_eligible=False))
        mock_gw.call.return_value = GatewayResult(
            decision_id="DEC-MOCK",
            error=MCPToolError(code="PROVIDER_ERROR", message="mid not wired", retry_eligible=False),
        )

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="CTG tool error"):
                await route_and_dispatch(
                    prompt="नमस्ते",
                    task_complexity="medium",
                    language="hi",
                    async_session_factory=session_factory,
                )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "sarvam"


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
        respx.post("http://ollama:11434/api/generate").mock(return_value=httpx.Response(500, text="server error"))
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
# route_and_dispatch error handlers
# C-080 note: error-path tests use _CTG_AVAILABLE=False to isolate fallback path
# ---------------------------------------------------------------------------


class TestRouteAndDispatchErrorHandlers:
    @pytest.mark.asyncio
    async def test_mid_non_indic_gateway_called_with_google(self) -> None:
        """MID tier + non-indic language → gateway called with provider=google."""
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(error=MCPToolError(code="PROVIDER_ERROR", message="mid not wired", retry_eligible=False))
        mock_gw.call.return_value = GatewayResult(
            decision_id="DEC-MOCK",
            error=MCPToolError(code="PROVIDER_ERROR", message="mid not wired", retry_eligible=False),
        )

        with (
            patch("pse.router._select_tier", return_value=LlmTier.MID),
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="CTG tool error"):
                await route_and_dispatch(
                    prompt="hello",
                    task_complexity="medium",
                    language="en",
                    async_session_factory=session_factory,
                )

        mock_gw.call.assert_awaited_once()
        assert mock_gw.call.call_args.args[1]["provider"] == "google"

    @pytest.mark.asyncio
    async def test_cancelled_error_records_then_propagates(self) -> None:
        """CancelledError from gateway triggers evidence recording then re-raises."""
        session_factory = _make_session_factory()
        mock_gw = AsyncMock()
        mock_gw.call.side_effect = asyncio.CancelledError()

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record,
        ):
            with pytest.raises(asyncio.CancelledError):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_ctg_error_result_raises_runtime_error(self) -> None:
        """GatewayResult.error ≠ None → route_and_dispatch raises RuntimeError with error code."""
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(error=MCPToolError(code="TIMEOUT", message="timed out", retry_eligible=True))
        mock_gw.call.return_value = GatewayResult(
            decision_id="DEC-MOCK",
            error=MCPToolError(code="TIMEOUT", message="timed out", retry_eligible=True),
        )

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record,
        ):
            with pytest.raises(RuntimeError, match="CTG tool error: TIMEOUT"):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_called_once()
