# Implements: work-contracts/WC-032-goal005-air-pse-trial-override.md
# Implements: work-contracts/WC-039-trust-layer-s3-ctg-library-air-refactor.md §WC039-06
# constitutional_basis: C-041 (CTG governs every call), C-049, C-059, C-076
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest
import respx
import fakeredis.aioredis

from unittest.mock import AsyncMock, MagicMock, patch

from pse.router import (
    _build_llm_executor,
    _dispatch_frontier,
    _dispatch_mid,
    _dispatch_ollama,
    _make_gateway,
    _record_dispatch_event,
    _select_tier,
    route_and_dispatch,
)
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

    @pytest.mark.parametrize("language", ["hi", "mr", "te", "ta", "kn", "pa", "bn", "gu"])
    def test_each_indic_language_routes_medium_to_mid(self, language: str) -> None:
        assert _select_tier(" medium ", f" {language.upper()} ") == LlmTier.MID

    @pytest.mark.parametrize(
        ("complexity", "language", "expected"),
        [
            (None, None, LlmTier.LOCAL),
            (" SIMPLE ", "HI", LlmTier.LOCAL),
            (" Medium ", " EN ", LlmTier.LOCAL),
            (" COMPLEX ", "HI", LlmTier.FRONTIER),
        ],
    )
    def test_tier_inputs_are_normalized(
        self,
        complexity: str | None,
        language: str | None,
        expected: LlmTier,
    ) -> None:
        assert _select_tier(complexity, language) == expected

    def test_unknown_complexity_logs_exact_fallback(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="pse.router"):
            assert _select_tier("unexpected", "en") == LlmTier.LOCAL
        assert caplog.messages == ["Unknown task_complexity value, defaulting to LOCAL tier"]


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
        """route_and_dispatch sends and records the exact governed request."""
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway()
        event_id = UUID("10000000-0000-0000-0000-000000000001")

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router.uuid.uuid4", return_value=event_id),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as record,
        ):
            result = await route_and_dispatch(
                prompt="hello",
                task_complexity="simple",
                language=None,
                async_session_factory=session_factory,
            )

        assert result == {
            "tier": LlmTier.LOCAL.value,
            "provider_id": "ollama",
            "model_id": "llama3.2:3b",
            "response": "ok",
            "done": True,
            "total_duration_ns": 50,
            "event_id": str(event_id),
        }
        tool_name, arguments, session = mock_gw.call.await_args.args
        assert tool_name == "llm.complete"
        assert arguments == {
            "provider": "ollama",
            "model": "llama3.2:3b",
            "prompt": "hello",
            "language": None,
        }
        assert session.tenant_id == UUID(int=0)
        assert session.agent_id == "pse"
        assert session.contract_id == ""
        assert session.skill_id == "llm.complete"
        assert session.decision_space == ""
        record.assert_awaited_once_with(
            session_factory,
            str(event_id),
            LlmTier.LOCAL,
            "ollama",
            "llama3.2:3b",
            "simple",
            None,
            "success",
            "",
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tier", "language", "provider_id", "model_id"),
        [
            (LlmTier.MID, "hi", "sarvam", "saaras"),
            (LlmTier.MID, "en", "google", "gemini-2.0-flash"),
            (LlmTier.FRONTIER, None, "google", "gemini-2.5-pro"),
        ],
    )
    async def test_dispatch_records_exact_tier_metadata(
        self,
        tier: LlmTier,
        language: str | None,
        provider_id: str,
        model_id: str,
    ) -> None:
        session_factory = _make_session_factory()
        mock_gw = _make_mock_gateway(result={"response": "tier response"})
        event_id = UUID("20000000-0000-0000-0000-000000000002")
        customer_id = "30000000-0000-0000-0000-000000000003"

        with (
            patch("pse.router._select_tier", return_value=tier),
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router.uuid.uuid4", return_value=event_id),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as record,
        ):
            result = await route_and_dispatch(
                prompt="governed prompt",
                task_complexity="controlled",
                language=language,
                async_session_factory=session_factory,
                customer_id=customer_id,
            )

        assert result == {"response": "tier response", "event_id": str(event_id)}
        tool_name, arguments, session = mock_gw.call.await_args.args
        assert tool_name == "llm.complete"
        assert arguments == {
            "provider": provider_id,
            "model": model_id,
            "prompt": "governed prompt",
            "language": language,
        }
        assert session.tenant_id == UUID(customer_id)
        assert session.agent_id == "pse"
        assert session.contract_id == customer_id
        assert session.skill_id == "llm.complete"
        assert session.decision_space == ""
        record.assert_awaited_once_with(
            session_factory,
            str(event_id),
            tier,
            provider_id,
            model_id,
            "controlled",
            language,
            "success",
            "",
        )

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
        route = respx.post("http://ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "hello world", "done": True, "total_duration": 500})
        )
        result = await _dispatch_ollama("test prompt")
        assert result == {
            "tier": "local",
            "provider_id": "ollama",
            "model_id": "llama3.2:3b",
            "response": "hello world",
            "done": True,
            "total_duration_ns": 500,
        }
        assert len(route.calls) == 1
        request = route.calls[0].request
        assert request.method == "POST"
        assert str(request.url) == "http://ollama:11434/api/generate"
        assert json.loads(request.content) == {
            "model": "llama3.2:3b",
            "prompt": "test prompt",
            "stream": False,
        }

    @pytest.mark.asyncio
    @respx.mock
    async def test_missing_optional_response_fields_use_safe_defaults(self) -> None:
        respx.post("http://ollama:11434/api/generate").mock(return_value=httpx.Response(200, json={}))

        result = await _dispatch_ollama("prompt")

        assert result == {
            "tier": "local",
            "provider_id": "ollama",
            "model_id": "llama3.2:3b",
            "response": "",
            "done": False,
            "total_duration_ns": None,
        }

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_raises(self, caplog: pytest.LogCaptureFixture) -> None:
        """Ollama timeout propagates as httpx.TimeoutException."""
        respx.post("http://ollama:11434/api/generate").mock(side_effect=httpx.TimeoutException("timeout"))
        with caplog.at_level(logging.ERROR, logger="pse.router"):
            with pytest.raises(httpx.TimeoutException):
                await _dispatch_ollama("test prompt")
        assert caplog.messages == ["Ollama request timed out after 30 seconds"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_raises(self, caplog: pytest.LogCaptureFixture) -> None:
        """Ollama non-2xx status propagates as httpx.HTTPStatusError."""
        respx.post("http://ollama:11434/api/generate").mock(return_value=httpx.Response(500, text="server error"))
        with caplog.at_level(logging.ERROR, logger="pse.router"):
            with pytest.raises(httpx.HTTPStatusError):
                await _dispatch_ollama("test prompt")
        assert caplog.messages == ["Ollama returned HTTP error status=500"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_error_raises(self, caplog: pytest.LogCaptureFixture) -> None:
        """Connection error propagates as httpx.RequestError."""
        respx.post("http://ollama:11434/api/generate").mock(side_effect=httpx.ConnectError("refused"))
        with caplog.at_level(logging.ERROR, logger="pse.router"):
            with pytest.raises(httpx.RequestError):
                await _dispatch_ollama("test prompt")
        assert caplog.messages == ["Ollama connection error: ConnectError"]


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


class TestCtgHelpers:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("provider", "auth_method", "dispatch", "expected_args"),
        [
            ("ollama", "NONE", "_dispatch_ollama", ("prompt",)),
            ("sarvam", "API_KEY", "_dispatch_mid", ("prompt", "hi")),
            ("google", "API_KEY", "_dispatch_mid", ("prompt", "hi")),
            ("google", "OAUTH2", "_dispatch_frontier", ("prompt",)),
        ],
    )
    async def test_llm_executor_dispatches_exact_provider_contract(
        self,
        provider: str,
        auth_method: str,
        dispatch: str,
        expected_args: tuple[str, ...],
    ) -> None:
        executor = _build_llm_executor()
        config = MagicMock(auth_method=auth_method)
        expected = {"provider": provider, "response": "ok"}

        with patch(f"pse.router.{dispatch}", new=AsyncMock(return_value=expected)) as call:
            result = await executor(
                "llm.complete",
                {"provider": provider, "prompt": "prompt", "language": "hi"},
                "token",
                config,
            )

        assert result == expected
        call.assert_awaited_once_with(*expected_args)

    @pytest.mark.asyncio
    async def test_llm_executor_defaults_missing_arguments(self) -> None:
        executor = _build_llm_executor()

        with patch("pse.router._dispatch_ollama", new=AsyncMock(return_value={"response": "ok"})) as dispatch:
            result = await executor("llm.complete", {}, None, MagicMock(auth_method="NONE"))

        assert result == {"response": "ok"}
        dispatch.assert_awaited_once_with("")

    def test_make_gateway_uses_configured_addresses_and_executor(self) -> None:
        executor = AsyncMock()

        with (
            patch.dict(
                "os.environ",
                {
                    "BP_BASE_URL": "http://bp-test",
                    "OAUTH_VAULT_BASE_URL": "http://vault-test",
                    "CONSTITUTIONAL_ENGINE_ADDRESS": "ce-test:7000",
                },
            ),
            patch("pse.router._build_llm_executor", return_value=executor),
            patch("pse.router.ConstitutionalToolGateway") as gateway,
        ):
            result = _make_gateway()

        assert result is gateway.return_value
        gateway.assert_called_once_with(
            bp_base_url="http://bp-test",
            vault_base_url="http://vault-test",
            ce_address="ce-test:7000",
            executor=executor,
        )


class TestDispatchEvidence:
    @pytest.mark.asyncio
    async def test_record_dispatch_event_persists_exact_parameters(self) -> None:
        session_factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session_factory.return_value.__aenter__.return_value = session
        timestamp = datetime(2026, 9, 10, 12, 30, tzinfo=timezone.utc)

        with patch("pse.router.datetime") as clock:
            clock.now.return_value = timestamp
            await _record_dispatch_event(
                session_factory,
                "event-1",
                LlmTier.MID,
                "sarvam",
                "saaras",
                "medium",
                "hi",
                "success",
                "",
            )

        session_factory.assert_called_once_with()
        session.begin.assert_called_once_with()
        statement, params = session.execute.await_args.args
        assert str(statement) == str(__import__("pse.router", fromlist=["_DB_INSERT_DISPATCH_EVENT"])._DB_INSERT_DISPATCH_EVENT)
        assert params == {
            "id": "event-1",
            "tier": "mid",
            "provider_id": "sarvam",
            "model_id": "saaras",
            "routed_at": timestamp.isoformat(),
            "task_complexity": "medium",
            "language": "hi",
            "status": "success",
            "error_detail": None,
        }

    @pytest.mark.asyncio
    async def test_record_dispatch_event_preserves_error_detail(self) -> None:
        session_factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session_factory.return_value.__aenter__.return_value = session

        await _record_dispatch_event(
            session_factory,
            "event-2",
            LlmTier.LOCAL,
            "ollama",
            "llama3.2:3b",
            "simple",
            None,
            "failed",
            "TimeoutError",
        )

        assert session.execute.await_args.args[1]["error_detail"] == "TimeoutError"

    @pytest.mark.asyncio
    async def test_record_dispatch_event_propagates_failures(self) -> None:
        session_factory = MagicMock(side_effect=RuntimeError("database unavailable"))

        with pytest.raises(RuntimeError, match="database unavailable"):
            await _record_dispatch_event(
                session_factory,
                "event-3",
                LlmTier.FRONTIER,
                "google",
                "gemini-2.5-pro",
                "complex",
                None,
                "failed",
                "RuntimeError",
            )


# ---------------------------------------------------------------------------
# route_and_dispatch error handlers
# C-080 note: error-path tests use _CTG_AVAILABLE=False to isolate fallback path
# ---------------------------------------------------------------------------


class TestRouteAndDispatchErrorHandlers:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tier", "language", "provider_id", "model_id", "dispatch", "dispatch_args"),
        [
            (LlmTier.LOCAL, None, "ollama", "llama3.2:3b", "_dispatch_ollama", ("prompt",)),
            (LlmTier.MID, "hi", "sarvam", "saaras", "_dispatch_mid", ("prompt", "hi")),
            (LlmTier.FRONTIER, None, "google", "gemini-2.5-pro", "_dispatch_frontier", ("prompt",)),
        ],
    )
    async def test_fallback_dispatch_records_exact_provider_contract(
        self,
        tier: LlmTier,
        language: str | None,
        provider_id: str,
        model_id: str,
        dispatch: str,
        dispatch_args: tuple[str, ...],
    ) -> None:
        session_factory = _make_session_factory()
        event_id = UUID("50000000-0000-0000-0000-000000000005")
        provider_result = {"response": "fallback response"}

        with (
            patch("pse.router._CTG_AVAILABLE", False),
            patch("pse.router._select_tier", return_value=tier),
            patch(f"pse.router.{dispatch}", new=AsyncMock(return_value=provider_result)) as provider_call,
            patch("pse.router.uuid.uuid4", return_value=event_id),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as record,
        ):
            result = await route_and_dispatch(
                prompt="prompt",
                task_complexity="controlled",
                language=language,
                async_session_factory=session_factory,
            )

        assert result == {"response": "fallback response", "event_id": str(event_id)}
        provider_call.assert_awaited_once_with(*dispatch_args)
        record.assert_awaited_once_with(
            session_factory,
            str(event_id),
            tier,
            provider_id,
            model_id,
            "controlled",
            language,
            "success",
            "",
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tier", "failure", "expected_status", "expected_detail"),
        [
            (LlmTier.LOCAL, ValueError("bad response"), "failed", "ValueError"),
            (LlmTier.MID, NotImplementedError("not wired"), "not_implemented", "NotImplementedError"),
        ],
    )
    async def test_fallback_failure_records_exact_classification(
        self,
        tier: LlmTier,
        failure: Exception,
        expected_status: str,
        expected_detail: str,
    ) -> None:
        session_factory = _make_session_factory()
        event_id = UUID("60000000-0000-0000-0000-000000000006")
        dispatch = "_dispatch_ollama" if tier == LlmTier.LOCAL else "_dispatch_mid"
        provider_id = "ollama" if tier == LlmTier.LOCAL else "sarvam"
        model_id = "llama3.2:3b" if tier == LlmTier.LOCAL else "saaras"

        with (
            patch("pse.router._CTG_AVAILABLE", False),
            patch("pse.router._select_tier", return_value=tier),
            patch(f"pse.router.{dispatch}", new=AsyncMock(side_effect=failure)),
            patch("pse.router.uuid.uuid4", return_value=event_id),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as record,
        ):
            with pytest.raises(type(failure), match=str(failure)):
                await route_and_dispatch(
                    prompt="prompt",
                    task_complexity="controlled",
                    language="hi" if tier == LlmTier.MID else None,
                    async_session_factory=session_factory,
                )

        record.assert_awaited_once_with(
            session_factory,
            str(event_id),
            tier,
            provider_id,
            model_id,
            "controlled",
            "hi" if tier == LlmTier.MID else None,
            expected_status,
            expected_detail,
        )

    @pytest.mark.asyncio
    async def test_fallback_cancellation_records_exact_evidence(self) -> None:
        session_factory = _make_session_factory()
        event_id = UUID("70000000-0000-0000-0000-000000000007")

        with (
            patch("pse.router._CTG_AVAILABLE", False),
            patch("pse.router._dispatch_ollama", new=AsyncMock(side_effect=asyncio.CancelledError())),
            patch("pse.router.uuid.uuid4", return_value=event_id),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as record,
        ):
            with pytest.raises(asyncio.CancelledError):
                await route_and_dispatch("prompt", "simple", None, session_factory)

        record.assert_awaited_once_with(
            session_factory,
            str(event_id),
            LlmTier.LOCAL,
            "ollama",
            "llama3.2:3b",
            "simple",
            None,
            "cancelled",
            "asyncio.CancelledError",
        )

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
        event_id = UUID("40000000-0000-0000-0000-000000000004")

        with (
            patch("pse.router._make_gateway", return_value=mock_gw),
            patch("pse.router.uuid.uuid4", return_value=event_id),
            patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as mock_record,
        ):
            with pytest.raises(RuntimeError, match="CTG tool error: TIMEOUT"):
                await route_and_dispatch(
                    prompt="simple",
                    task_complexity="simple",
                    language=None,
                    async_session_factory=session_factory,
                )

        mock_record.assert_awaited_once_with(
            session_factory,
            str(event_id),
            LlmTier.LOCAL,
            "ollama",
            "llama3.2:3b",
            "simple",
            None,
            "failed",
            "timed out",
        )
