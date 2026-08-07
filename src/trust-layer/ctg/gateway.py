# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §2
# constitutional_basis: C-041 (every tool call governed), C-059 (traceability),
#                       ADR-014 (no credential in logs), ADR-021 (vault retrieval)
from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx

from .exception_translator import ExceptionTranslator
from .models import (
    ConstitutionalBlockError,
    GatewayResult,
    MCPToolError,
    ProviderConfig,
    SessionContext,
)
from .registry_client import ProviderRegistryClient

logger = logging.getLogger(__name__)

# --- CE client protocol (injectable for tests) --------------------------------


class CEClient(Protocol):  # pragma: no cover
    """Minimal interface for CE.ValidateAction. Real impl uses gRPC stub."""

    async def validate_action(
        self,
        contract_id: str,
        action_type: str,
        agent_id: str,
        dcm_category: str,
        skill_id: str,
    ) -> tuple[str, str]:
        """Return (decision, decision_id). decision ∈ {ALLOW, DENY, ESCALATE}."""
        ...


# --- Audit sink protocol (injectable for tests) --------------------------------


class AuditSinkWriter(Protocol):  # pragma: no cover
    """Writes a single evidence record to audit_sink.evidence_records (ADR-044)."""

    async def write_record(
        self,
        decision_id: str,
        agent_id: str,
        tenant_id: str,
        tool_name: str,
        args_hash: str,
        credential_provider: str,
        vault_alias: str,
        execution_status: str,
    ) -> None:
        ...


# --- Default CE gRPC client (requires generated pb2 stubs at runtime) ---------


class _GrpcCEClient:  # pragma: no cover
    """
    Production CE client. Uses grpc.aio to call CE.ValidateAction.
    Requires constitutional_service_pb2 + _pb2_grpc generated from the .proto.
    Those files are generated at Docker build time (grpcio-tools) — not committed.
    """

    def __init__(self, ce_address: str) -> None:
        self._ce_address = ce_address

    async def validate_action(
        self,
        contract_id: str,
        action_type: str,
        agent_id: str,
        dcm_category: str,
        skill_id: str,
    ) -> tuple[str, str]:
        import grpc
        import grpc.aio

        # Lazy import generated stubs — generated at Docker build time
        from ctg.proto import constitutional_service_pb2 as pb2  # type: ignore[import]
        from ctg.proto import constitutional_service_pb2_grpc as pb2_grpc  # type: ignore[import]

        async with grpc.aio.insecure_channel(self._ce_address) as channel:
            stub = pb2_grpc.ConstitutionalServiceStub(channel)
            request = pb2.ValidateActionRequest(
                contract_id=contract_id,
                action_type=action_type,
                action_parameters=json.dumps({"agent_id": agent_id, "skill_id": skill_id}),
                decision_space_version=1,
            )
            response = await stub.ValidateAction(request)

        decision_name = pb2.ValidationDecision.Name(response.decision)
        # Strip VALIDATION_DECISION_ prefix → ALLOW / DENY / ESCALATE
        decision = decision_name.replace("VALIDATION_DECISION_", "")
        decision_id = getattr(response, "constitutional_basis", f"DEC-{action_type[:8]}")
        return decision, decision_id


# --- Default no-op audit sink (used until ADR-044 migration runs) -------------


class _LoggingAuditSinkWriter:
    """Writes evidence to logger until the real audit_sink Postgres schema is live."""

    async def write_record(
        self,
        decision_id: str,
        agent_id: str,
        tenant_id: str,
        tool_name: str,
        args_hash: str,
        credential_provider: str,
        vault_alias: str,
        execution_status: str,
    ) -> None:
        logger.info(
            "audit_sink decision_id=%s agent_id=%s tool_name=%s args_hash=%s "
            "credential_provider=%s vault_alias=%s status=%s",
            decision_id,
            agent_id,
            tool_name,
            args_hash,
            credential_provider,
            vault_alias,
            execution_status,
            extra={"audit": True},
        )


# --- Tool executor type alias -------------------------------------------------

ToolExecutor = Callable[[str, dict[str, Any], str | None, ProviderConfig], Awaitable[dict[str, Any]]]


# --- Gateway ------------------------------------------------------------------


class ConstitutionalToolGateway:
    """
    Single entry point for all external calls from AI Runtime and Professional Runtime.

    ADR-042 §2 pipeline (steps 1–9):
      1. Fetch ProviderConfig from BP registry (60 s TTL cache)
      2. CE.ValidateAction → ALLOW → continue | DENY → ConstitutionalBlockError
      3. Fetch credential from oauth-vault (in-memory local variable only)
      4. Inject credential at socket boundary via executor
      5. Execute via injected executor (MCP SDK or direct HTTP)
      6. ExceptionTranslator on failure (no token in MCPToolError)
      7. Write evidence record to Audit Sink
      8. Clear credential local variable (goes out of scope)
      9. Return GatewayResult
    """

    def __init__(
        self,
        bp_base_url: str,
        vault_base_url: str,
        ce_address: str | None = None,
        executor: ToolExecutor | None = None,
        *,
        ce_client: CEClient | None = None,
        audit_sink: AuditSinkWriter | None = None,
        internal_jwt: str = "",
    ) -> None:
        self._registry = ProviderRegistryClient(bp_base_url, internal_jwt)
        self._vault_base_url = vault_base_url.rstrip("/")
        self._translator = ExceptionTranslator()
        self._executor = executor
        self._ce: CEClient = ce_client or _GrpcCEClient(
            ce_address or os.getenv("CONSTITUTIONAL_ENGINE_ADDRESS", "constitutional-engine:7000")
        )
        self._audit_sink: AuditSinkWriter = audit_sink or _LoggingAuditSinkWriter()

    async def call(
        self,
        tool_name: str,
        args: dict[str, Any],
        session_ctx: SessionContext,
    ) -> GatewayResult:
        """
        Execute one external tool call through the full constitutional pipeline.

        Raises:
            ConstitutionalBlockError: CE returned DENY or ESCALATE.
        """
        provider_name = args.get("provider", tool_name.split(".")[0])

        # Step 1 — fetch ProviderConfig (60 s TTL cache)
        config = await self._registry.get_config(session_ctx.tenant_id, provider_name)

        # Step 2 — CE.ValidateAction: DENY → raise ConstitutionalBlockError
        decision, decision_id = await self._ce.validate_action(
            contract_id=session_ctx.contract_id,
            action_type=tool_name,
            agent_id=session_ctx.agent_id,
            dcm_category="CONSISTENT_SUFFICIENT",
            skill_id=session_ctx.skill_id,
        )
        if decision in ("DENY", "ESCALATE"):
            logger.warning(
                "CTG CE blocked tool_name=%s decision=%s decision_id=%s",
                tool_name,
                decision,
                decision_id,
            )
            raise ConstitutionalBlockError(decision_id=decision_id, reason=decision)

        # Step 3 — fetch credential from oauth-vault (local variable only — never logged)
        token: str | None = await self._fetch_token(session_ctx.contract_id, provider_name)

        # Steps 4–5 — execute via injected executor (token injected at socket boundary)
        execution_status = "SUCCESS"
        result_data: dict[str, Any] | None = None
        tool_error: MCPToolError | None = None

        try:
            if self._executor is None:
                raise RuntimeError(
                    f"No executor registered for tool_name={tool_name}. "
                    "Caller must inject an executor at gateway construction."
                )
            result_data = await self._executor(tool_name, args, token, config)
        except ConstitutionalBlockError:
            raise
        except Exception as raw_exc:
            # Step 6 — Exception Translator: token never passed in, never in MCPToolError
            tool_error = self._translator.translate(raw_exc, provider_name)
            execution_status = "FAILED"
        finally:
            # Step 8 — clear token reference (structural, not just del)
            token = None  # noqa: F841

        # Step 7 — write evidence record to Audit Sink (C-059 — synchronous, blocking)
        args_hash = "sha256:" + hashlib.sha256(
            json.dumps(args, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        vault_alias = os.getenv("AZURE_KEYVAULT_ALIAS", "waooaw-dev-kv")
        await self._audit_sink.write_record(
            decision_id=decision_id,
            agent_id=session_ctx.agent_id,
            tenant_id=str(session_ctx.tenant_id),
            tool_name=tool_name,
            args_hash=args_hash,
            credential_provider=provider_name,
            vault_alias=vault_alias,
            execution_status=execution_status,
        )

        # Step 9 — return GatewayResult
        return GatewayResult(decision_id=decision_id, result=result_data, error=tool_error)

    async def _fetch_token(self, contract_id: str, provider_name: str) -> str | None:
        """
        Fetches credential from oauth-vault. Returns None for providers with no token
        (e.g. Ollama local inference — no credential needed).
        Token is held only as a local variable in call() — never serialized or logged.
        """
        if not contract_id:
            return None

        url = f"{self._vault_base_url}/tokens/{contract_id}/{provider_name}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
            if response.status_code == 404:
                # No credential stored — provider may not need auth (e.g. ollama)
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error(
                "CTG vault fetch failed provider=%s status=%s",
                provider_name,
                exc.response.status_code,
                extra={"secure": True},
            )
            raise
        except httpx.RequestError:
            logger.error(
                "CTG vault connection failed provider=%s",
                provider_name,
                exc_info=True,
                extra={"secure": True},
            )
            raise
