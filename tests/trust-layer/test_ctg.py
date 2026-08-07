# Implements: work-contracts/WC-039-trust-layer-s3-ctg-library-air-refactor.md
# constitutional_basis: C-041 (every tool call governed), C-059 (traceability),
#                       C-076 (≥90% coverage), ADR-042 (CTG pipeline)
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "trust-layer"))

import hashlib
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ctg.exception_translator import ExceptionTranslator
from ctg.gateway import ConstitutionalToolGateway
from ctg.models import (
    ConstitutionalBlockError,
    GatewayResult,
    MCPToolError,
    ProviderConfig,
    SessionContext,
)
from ctg.registry_client import ProviderRegistryClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_ctx(**kwargs) -> SessionContext:
    defaults = dict(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        agent_id="agt-test",
        contract_id="contract-001",
        skill_id="llm.complete",
        decision_space="",
    )
    defaults.update(kwargs)
    return SessionContext(**defaults)


def _make_provider_config(**kwargs) -> ProviderConfig:
    defaults = dict(
        provider_name="openai",
        auth_method="API_KEY",
        mcp_server_url=None,
        vault_path_key="providers/test/openai",
    )
    defaults.update(kwargs)
    return ProviderConfig(**defaults)


def _make_gateway(
    *,
    ce_client=None,
    audit_sink=None,
    executor=None,
    registry_config: ProviderConfig | None = None,
) -> ConstitutionalToolGateway:
    """Build a gateway with all external dependencies mocked."""
    gw = ConstitutionalToolGateway(
        bp_base_url="http://bp:5003",
        vault_base_url="http://vault:8130",
        ce_client=ce_client,
        audit_sink=audit_sink,
        executor=executor,
    )
    # Replace registry client with a mock that returns registry_config
    mock_registry = AsyncMock()
    mock_registry.get_config.return_value = registry_config or _make_provider_config()
    gw._registry = mock_registry
    return gw


def _make_ce_allow(decision_id: str = "DEC-001") -> AsyncMock:
    ce = AsyncMock()
    ce.validate_action.return_value = ("ALLOW", decision_id)
    return ce


def _make_ce_deny(decision_id: str = "DEC-DENY-001") -> AsyncMock:
    ce = AsyncMock()
    ce.validate_action.return_value = ("DENY", decision_id)
    return ce


def _make_audit_sink() -> AsyncMock:
    sink = AsyncMock()
    sink.write_record = AsyncMock()
    return sink


def _make_executor(return_value: dict | None = None) -> AsyncMock:
    ex = AsyncMock(return_value=return_value or {"response": "ok", "done": True})
    return ex


# ---------------------------------------------------------------------------
# CCT-CTG-01 — CE.ValidateAction called before any external call
# ---------------------------------------------------------------------------

class TestCCTCtg01CeCalledFirst:
    """CCT-CTG-01: CE.ValidateAction is invoked on every gateway.call()."""

    @pytest.mark.asyncio
    async def test_ce_validate_called_with_correct_tool_name(self):
        """CE receives the tool_name as action_type before executor is invoked."""
        ce = _make_ce_allow()
        executor = _make_executor()
        gw = _make_gateway(ce_client=ce, audit_sink=_make_audit_sink(), executor=executor)

        ctx = _make_session_ctx(contract_id="ctr-001", agent_id="agt-001")
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            await gw.call("llm.complete", {"provider": "openai"}, ctx)

        ce.validate_action.assert_called_once()
        call_kwargs = ce.validate_action.call_args
        assert call_kwargs.kwargs["action_type"] == "llm.complete"
        assert call_kwargs.kwargs["agent_id"] == "agt-001"
        assert call_kwargs.kwargs["contract_id"] == "ctr-001"

    @pytest.mark.asyncio
    async def test_executor_not_called_before_ce(self):
        """If CE is slow (awaited), executor has not yet been called."""
        call_order: list[str] = []

        async def _slow_ce_validate(**kwargs):
            call_order.append("CE")
            return ("ALLOW", "DEC-999")

        async def _tracking_executor(tool_name, args, token, config):
            call_order.append("EXEC")
            return {"response": "ok", "done": True}

        ce = MagicMock()
        ce.validate_action = _slow_ce_validate
        gw = _make_gateway(ce_client=ce, audit_sink=_make_audit_sink(), executor=_tracking_executor)

        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            await gw.call("meta.post", {"provider": "meta"}, _make_session_ctx())

        assert call_order.index("CE") < call_order.index("EXEC")

    @pytest.mark.asyncio
    async def test_ce_called_with_dcm_category(self):
        """CE receives dcm_category field — required for DCM routing (C-099)."""
        ce = _make_ce_allow()
        gw = _make_gateway(ce_client=ce, audit_sink=_make_audit_sink(), executor=_make_executor())

        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        call_kwargs = ce.validate_action.call_args.kwargs
        assert "dcm_category" in call_kwargs
        assert call_kwargs["dcm_category"] != ""


# ---------------------------------------------------------------------------
# CCT-CTG-02 — Token absent from MCPToolError on failure
# ---------------------------------------------------------------------------

class TestCCTCtg02TokenAbsentFromError:
    """CCT-CTG-02: token never leaks into caller-visible MCPToolError."""

    @pytest.mark.asyncio
    async def test_exception_containing_token_sanitized(self):
        """
        Inject executor that raises an exception whose message contains the real token.
        Assert MCPToolError.message does NOT contain the token fragment.
        """
        secret_token = "sk-secret-abc123xyz456"

        async def _leaky_executor(tool_name, args, token, config):
            raise RuntimeError(f"Auth header value: Bearer {secret_token}")

        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_leaky_executor,
        )
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=secret_token):
            result = await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        assert result.error is not None
        assert secret_token not in result.error.message
        assert result.result is None

    @pytest.mark.asyncio
    async def test_timeout_error_sanitized(self):
        """httpx.TimeoutException → TIMEOUT code with generic message, no URL fragments."""
        import httpx

        async def _timeout_executor(tool_name, args, token, config):
            raise httpx.ConnectTimeout("Timeout to https://api.openai.com/v1?key=sk-secret")

        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_timeout_executor,
        )
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            result = await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        assert result.error is not None
        assert result.error.code == "TIMEOUT"
        assert "sk-secret" not in result.error.message
        assert "openai.com" not in result.error.message

    @pytest.mark.asyncio
    async def test_constitutional_block_not_swallowed(self):
        """ConstitutionalBlockError propagates unchanged — it contains no credential."""
        ce = _make_ce_deny()
        gw = _make_gateway(ce_client=ce, audit_sink=_make_audit_sink(), executor=_make_executor())

        with pytest.raises(ConstitutionalBlockError) as exc_info:
            await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        assert exc_info.value.decision_id == "DEC-DENY-001"


# ---------------------------------------------------------------------------
# CCT-CTG-03 — Evidence record written after successful call
# ---------------------------------------------------------------------------

class TestCCTCtg03EvidenceRecordWritten:
    """CCT-CTG-03: audit_sink.write_record called with decision_id + args_hash on success."""

    @pytest.mark.asyncio
    async def test_audit_sink_called_on_success(self):
        """Successful gateway call writes exactly one evidence record."""
        audit = _make_audit_sink()
        gw = _make_gateway(
            ce_client=_make_ce_allow("DEC-007"),
            audit_sink=audit,
            executor=_make_executor({"response": "hello", "done": True}),
        )
        args = {"provider": "openai", "prompt": "hello"}
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            result = await gw.call("llm.complete", args, _make_session_ctx())

        audit.write_record.assert_awaited_once()
        call_kwargs = audit.write_record.call_args.kwargs
        assert call_kwargs["decision_id"] == "DEC-007"
        expected_hash = "sha256:" + hashlib.sha256(
            json.dumps(args, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        assert call_kwargs["args_hash"] == expected_hash
        assert result.decision_id == "DEC-007"
        assert result.result == {"response": "hello", "done": True}

    @pytest.mark.asyncio
    async def test_audit_sink_called_on_failure(self):
        """Failed call (executor raises) still writes an evidence record with FAILED status."""
        audit = _make_audit_sink()
        async def _fail(tool_name, args, token, config):
            raise RuntimeError("provider down")

        gw = _make_gateway(
            ce_client=_make_ce_allow("DEC-008"),
            audit_sink=audit,
            executor=_fail,
        )
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            result = await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        audit.write_record.assert_awaited_once()
        call_kwargs = audit.write_record.call_args.kwargs
        assert call_kwargs["execution_status"] == "FAILED"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_audit_sink_fields_never_contain_token(self):
        """vault_alias is a short alias; neither the full URL nor the token appears."""
        audit = _make_audit_sink()
        secret_token = "sk-audit-leak-check"
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=audit,
            executor=_make_executor(),
        )
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=secret_token):
            await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        call_kwargs = audit.write_record.call_args.kwargs
        # vault_alias is a short name, never contains token or full URL
        assert "https://" not in call_kwargs.get("vault_alias", "")
        assert secret_token not in json.dumps(call_kwargs)


# ---------------------------------------------------------------------------
# CCT-CTG-04 — DENY from CE blocks execution; no external call made
# ---------------------------------------------------------------------------

class TestCCTCtg04DenyBlocksExecution:
    """CCT-CTG-04: CE DENY → ConstitutionalBlockError; executor never called."""

    @pytest.mark.asyncio
    async def test_deny_raises_constitutional_block_error(self):
        """CE DENY → ConstitutionalBlockError is raised before executor runs."""
        executor = _make_executor()
        gw = _make_gateway(
            ce_client=_make_ce_deny("DEC-DENY-002"),
            audit_sink=_make_audit_sink(),
            executor=executor,
        )

        with pytest.raises(ConstitutionalBlockError) as exc_info:
            await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        executor.assert_not_called()
        assert exc_info.value.decision_id == "DEC-DENY-002"

    @pytest.mark.asyncio
    async def test_deny_vault_not_called(self):
        """CE DENY → oauth-vault is never queried (no credential fetch before constitutional gate)."""
        gw = _make_gateway(
            ce_client=_make_ce_deny(),
            audit_sink=_make_audit_sink(),
            executor=_make_executor(),
        )
        # _fetch_token is called AFTER CE validation — so on DENY it must NOT be called
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock) as mock_fetch:
            with pytest.raises(ConstitutionalBlockError):
                await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_escalate_also_blocks(self):
        """CE ESCALATE is treated identically to DENY — no external call."""
        ce = AsyncMock()
        ce.validate_action.return_value = ("ESCALATE", "DEC-ESC-001")
        executor = _make_executor()
        gw = _make_gateway(ce_client=ce, audit_sink=_make_audit_sink(), executor=executor)

        with pytest.raises(ConstitutionalBlockError):
            await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())
        executor.assert_not_called()


# ---------------------------------------------------------------------------
# Unit: ExceptionTranslator
# ---------------------------------------------------------------------------

class TestExceptionTranslator:
    """Unit tests for ExceptionTranslator — structural token leakage prevention."""

    def test_timeout_maps_to_timeout_code(self):
        import httpx
        tr = ExceptionTranslator()
        err = tr.translate(httpx.ConnectTimeout("timeout"), "openai")
        assert err.code == "TIMEOUT"
        assert err.retry_eligible is True

    def test_401_maps_to_token_degraded(self):
        import httpx
        import respx

        tr = ExceptionTranslator()
        with respx.mock:
            respx.get("http://test/").mock(return_value=httpx.Response(401))
            resp = httpx.get("http://test/")
        exc = httpx.HTTPStatusError("auth", request=resp.request, response=resp)
        err = tr.translate(exc, "openai")
        assert err.code == "TOKEN_DEGRADED"
        assert err.retry_eligible is True

    def test_500_maps_to_provider_error_retry_true(self):
        import httpx
        import respx

        tr = ExceptionTranslator()
        with respx.mock:
            respx.get("http://test/").mock(return_value=httpx.Response(500))
            resp = httpx.get("http://test/")
        exc = httpx.HTTPStatusError("server error", request=resp.request, response=resp)
        err = tr.translate(exc, "openai")
        assert err.code == "PROVIDER_ERROR"
        assert err.retry_eligible is True

    def test_404_maps_to_provider_error_retry_false(self):
        import httpx
        import respx

        tr = ExceptionTranslator()
        with respx.mock:
            respx.get("http://test/").mock(return_value=httpx.Response(404))
            resp = httpx.get("http://test/")
        exc = httpx.HTTPStatusError("not found", request=resp.request, response=resp)
        err = tr.translate(exc, "openai")
        assert err.code == "PROVIDER_ERROR"
        assert err.retry_eligible is False

    def test_request_error_maps_to_provider_error_retry(self):
        import httpx

        tr = ExceptionTranslator()
        err = tr.translate(httpx.ConnectError("connection refused"), "openai")
        assert err.code == "PROVIDER_ERROR"
        assert err.retry_eligible is True

    def test_unknown_exception_no_credential_in_message(self):
        tr = ExceptionTranslator()
        secret = "sk-ultra-secret-key"
        err = tr.translate(RuntimeError(f"value={secret}"), "openai")
        assert secret not in err.message
        assert err.code == "PROVIDER_ERROR"


# ---------------------------------------------------------------------------
# Unit: ProviderRegistryClient TTL cache
# ---------------------------------------------------------------------------

class TestRegistryClientCache:
    """TTL cache correctness — cache hit avoids HTTP round-trip."""

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_second_http_call(self):
        """Second call within TTL returns cached result without HTTP."""
        import respx, httpx
        import uuid as uuid_mod

        client = ProviderRegistryClient("http://bp:5003", "jwt-token")
        tenant = uuid_mod.UUID("00000000-0000-0000-0000-000000000001")
        payload = {
            "provider_name": "openai",
            "auth_method": "API_KEY",
            "mcp_server_url": None,
            "vault_path_key": "providers/test/openai",
            "scope_set": [],
        }

        with respx.mock:
            route = respx.get("http://bp:5003/api/v1/providers/openai").mock(
                return_value=httpx.Response(200, json=payload)
            )
            await client.get_config(tenant, "openai")
            await client.get_config(tenant, "openai")  # should hit cache

        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_on_different_provider(self):
        """Different provider_name → different cache key → HTTP called for each."""
        import respx, httpx
        import uuid as uuid_mod

        client = ProviderRegistryClient("http://bp:5003", "jwt-token")
        tenant = uuid_mod.UUID("00000000-0000-0000-0000-000000000001")

        def _payload(name: str) -> dict:
            return {"provider_name": name, "auth_method": "API_KEY",
                    "mcp_server_url": None, "vault_path_key": f"p/{name}", "scope_set": []}

        with respx.mock:
            r1 = respx.get("http://bp:5003/api/v1/providers/openai").mock(
                return_value=httpx.Response(200, json=_payload("openai"))
            )
            r2 = respx.get("http://bp:5003/api/v1/providers/anthropic").mock(
                return_value=httpx.Response(200, json=_payload("anthropic"))
            )
            await client.get_config(tenant, "openai")
            await client.get_config(tenant, "anthropic")

        assert r1.call_count == 1
        assert r2.call_count == 1


# ---------------------------------------------------------------------------
# Unit: _LoggingAuditSinkWriter and gateway internals (GAP-001 — EA R-022)
# ---------------------------------------------------------------------------

class TestLoggingAuditSinkWriter:
    """Direct coverage of _LoggingAuditSinkWriter.write_record (default no-op sink)."""

    @pytest.mark.asyncio
    async def test_write_record_does_not_raise(self):
        """Default logging sink writes without error."""
        from ctg.gateway import _LoggingAuditSinkWriter
        sink = _LoggingAuditSinkWriter()
        # Must not raise
        await sink.write_record(
            decision_id="DEC-LOG-001",
            agent_id="agt-test",
            tenant_id="00000000-0000-0000-0000-000000000001",
            tool_name="llm.complete",
            args_hash="sha256:abcdef123456",
            credential_provider="openai",
            vault_alias="waooaw-dev-kv",
            execution_status="SUCCESS",
        )


class TestFetchToken:
    """Coverage for _fetch_token internal vault call paths (GAP-001 — EA R-022)."""

    @pytest.mark.asyncio
    async def test_fetch_token_404_returns_none(self):
        """404 from oauth-vault → None (provider needs no credential, e.g. ollama)."""
        import respx, httpx
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_make_executor(),
        )
        gw._vault_base_url = "http://vault:8130"

        with respx.mock:
            respx.get("http://vault:8130/tokens/contract-001/openai").mock(
                return_value=httpx.Response(404)
            )
            token = await gw._fetch_token("contract-001", "openai")

        assert token is None

    @pytest.mark.asyncio
    async def test_fetch_token_200_returns_value(self):
        """200 from oauth-vault → access_token string."""
        import respx, httpx
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_make_executor(),
        )
        gw._vault_base_url = "http://vault:8130"

        with respx.mock:
            respx.get("http://vault:8130/tokens/ctr-002/meta").mock(
                return_value=httpx.Response(200, json={"access_token": "tok-abc"})
            )
            token = await gw._fetch_token("ctr-002", "meta")

        assert token == "tok-abc"

    @pytest.mark.asyncio
    async def test_fetch_token_empty_contract_returns_none(self):
        """Empty contract_id short-circuits without HTTP."""
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_make_executor(),
        )
        token = await gw._fetch_token("", "openai")
        assert token is None

    @pytest.mark.asyncio
    async def test_fetch_token_non404_status_raises(self):
        """Non-404 HTTPStatusError propagates (e.g. 500 vault error)."""
        import respx, httpx
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_make_executor(),
        )
        gw._vault_base_url = "http://vault:8130"

        with respx.mock:
            respx.get("http://vault:8130/tokens/ctr-003/openai").mock(
                return_value=httpx.Response(500)
            )
            with pytest.raises(httpx.HTTPStatusError):
                await gw._fetch_token("ctr-003", "openai")

    @pytest.mark.asyncio
    async def test_fetch_token_request_error_raises(self):
        """Network failure (RequestError) propagates."""
        import respx, httpx
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=_make_executor(),
        )
        gw._vault_base_url = "http://vault:8130"

        with respx.mock:
            respx.get("http://vault:8130/tokens/ctr-004/openai").mock(
                side_effect=httpx.ConnectError("connection refused")
            )
            with pytest.raises(httpx.ConnectError):
                await gw._fetch_token("ctr-004", "openai")


class TestGatewayNoExecutor:
    """Cover the 'no executor registered' RuntimeError path (GAP-001 — EA R-022)."""

    @pytest.mark.asyncio
    async def test_no_executor_raises_runtime_error(self):
        """Gateway with no executor raises RuntimeError explaining the gap."""
        gw = _make_gateway(
            ce_client=_make_ce_allow(),
            audit_sink=_make_audit_sink(),
            executor=None,  # no executor — gateway not fully wired
        )
        with patch.object(gw, "_fetch_token", new_callable=AsyncMock, return_value=None):
            result = await gw.call("llm.complete", {"provider": "openai"}, _make_session_ctx())

        # No executor → PROVIDER_ERROR via exception translation
        assert result.error is not None
        assert result.error.code == "PROVIDER_ERROR"
