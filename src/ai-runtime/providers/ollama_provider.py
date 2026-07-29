# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer,§1 LLM Gateway
# constitutional_basis: C-023, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

import asyncpg
import httpx

logger = logging.getLogger(__name__)

_OLLAMA_BASE_URL = "http://ollama:11434"
_OLLAMA_GENERATE_ENDPOINT = f"{_OLLAMA_BASE_URL}/api/generate"
_DEFAULT_MODEL = "llama3.2:3b"
_REQUEST_TIMEOUT_SECONDS = 120


class OllamaProvider:
    """
    Provider Abstraction Layer implementation for self-hosted Ollama.

    Constitutional obligations:
    - C-063: PII must never appear in any log statement — prompt content is NEVER logged.
    - ADR-028: Prompt content never logged, even at DEBUG level.
    - ADR-029: LOCAL tier primary provider; no fallback (LOCAL outage → queue).
    - C-059: Every dispatch is recorded to institutional.provider_dispatch_events.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        db_pool: asyncpg.Pool | None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._http_client = http_client
        self._db_pool = db_pool
        self._model = model

    async def complete(
        self,
        messages: list[dict[str, str]],
        params: dict[str, Any],
        *,
        tenant_id: str,
        session_id: str,
        tier: str = "LOCAL",
    ) -> dict[str, Any]:
        """
        Send a completion request to Ollama and return the response.

        Args:
            messages:   Conversation history — content is NEVER logged (C-063, ADR-028).
            params:     Model parameters (temperature, max_tokens, etc.).
            tenant_id:  Tenant identifier for dispatch event recording.
            session_id: Session identifier for dispatch event recording.
            tier:       LLM tier — should be 'LOCAL' for Ollama.

        Returns:
            dict with keys: 'content' (str), 'model' (str), 'provider' (str),
            'input_tokens' (int), 'output_tokens' (int), 'latency_ms' (float).

        Raises:
            httpx.TimeoutException: If Ollama does not respond within the timeout.
            httpx.HTTPStatusError: If Ollama returns a non-2xx status code.
            asyncio.CancelledError: Propagated — never swallowed.
        """
        dispatch_id = str(uuid.uuid4())
        model = params.get("model", self._model)
        prompt = self._build_prompt(messages)

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.get("temperature", 0.7),
                "num_predict": params.get("max_tokens", 512),
            },
        }

        logger.info(
            "OllamaProvider dispatch starting — dispatch_id=%s model=%s tier=%s tenant_id=%s session_id=%s",
            dispatch_id,
            model,
            tier,
            tenant_id,
            session_id,
        )

        started_at = time.monotonic()
        success = False
        error_code: str | None = None
        response_text = ""
        input_tokens = 0
        output_tokens = 0

        try:
            response = await self._http_client.post(
                _OLLAMA_GENERATE_ENDPOINT,
                json=payload,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            body = response.json()
            response_text = body.get("response", "")
            input_tokens = body.get("prompt_eval_count", 0)
            output_tokens = body.get("eval_count", 0)
            success = True

        except asyncio.CancelledError:
            logger.warning(
                "OllamaProvider dispatch cancelled — dispatch_id=%s",
                dispatch_id,
            )
            raise

        except httpx.TimeoutException:
            error_code = "TIMEOUT"
            logger.error(
                "OllamaProvider timeout — dispatch_id=%s model=%s timeout_seconds=%s",
                dispatch_id,
                model,
                _REQUEST_TIMEOUT_SECONDS,
            )
            await self._record_dispatch_event(
                dispatch_id=dispatch_id,
                tenant_id=tenant_id,
                session_id=session_id,
                model=model,
                tier=tier,
                latency_ms=(time.monotonic() - started_at) * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=False,
                error_code=error_code,
            )
            raise

        except httpx.HTTPStatusError as exc:
            error_code = f"HTTP_{exc.response.status_code}"
            logger.error(
                "OllamaProvider HTTP error — dispatch_id=%s status=%s",
                dispatch_id,
                exc.response.status_code,
            )
            await self._record_dispatch_event(
                dispatch_id=dispatch_id,
                tenant_id=tenant_id,
                session_id=session_id,
                model=model,
                tier=tier,
                latency_ms=(time.monotonic() - started_at) * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=False,
                error_code=error_code,
            )
            raise

        latency_ms = (time.monotonic() - started_at) * 1000

        await self._record_dispatch_event(
            dispatch_id=dispatch_id,
            tenant_id=tenant_id,
            session_id=session_id,
            model=model,
            tier=tier,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success,
            error_code=error_code,
        )

        logger.info(
            "OllamaProvider dispatch complete — dispatch_id=%s latency_ms=%.1f input_tokens=%s output_tokens=%s",
            dispatch_id,
            latency_ms,
            input_tokens,
            output_tokens,
        )

        return {
            "content": response_text,
            "model": model,
            "provider": "ollama",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "dispatch_id": dispatch_id,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(messages: list[dict[str, str]]) -> str:
        """
        Convert a list of chat messages to a single prompt string for Ollama.

        Ollama /api/generate expects a flat prompt, not a messages array.
        Content is NEVER logged anywhere in this method (C-063, ADR-028).
        """
        parts: list[str] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM]\n{content}\n[/SYSTEM]")
            elif role == "assistant":
                parts.append(f"[ASSISTANT]\n{content}\n[/ASSISTANT]")
            else:
                parts.append(f"[USER]\n{content}\n[/USER]")
        return "\n\n".join(parts)

    async def _record_dispatch_event(
        self,
        *,
        dispatch_id: str,
        tenant_id: str,
        session_id: str,
        model: str,
        tier: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        error_code: str | None,
    ) -> None:
        """
        Persist a dispatch event to institutional.provider_dispatch_events (C-059).

        If the DB pool is unavailable, the error is logged and the exception is
        NOT re-raised — a failed audit write must not prevent the caller from
        receiving the LLM response. The evidence gap is itself logged as an
        error so that the observability pipeline can alert (C-059 compliance).
        """
        if self._db_pool is None:
            logger.error(
                "OllamaProvider cannot record dispatch event — db_pool is None. "
                "dispatch_id=%s tenant_id=%s session_id=%s success=%s error_code=%s "
                "(C-059 evidence gap — operator must investigate)",
                dispatch_id,
                tenant_id,
                session_id,
                success,
                error_code,
            )
            return

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO institutional.provider_dispatch_events (
                        dispatch_id,
                        tenant_id,
                        session_id,
                        provider,
                        model,
                        tier,
                        latency_ms,
                        input_tokens,
                        output_tokens,
                        success,
                        error_code,
                        dispatched_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW()
                    )
                    """,
                    dispatch_id,
                    tenant_id,
                    session_id,
                    "ollama",
                    model,
                    tier,
                    latency_ms,
                    input_tokens,
                    output_tokens,
                    success,
                    error_code,
                )

        except asyncio.CancelledError:
            raise

        except (asyncpg.PostgresError, OSError) as exc:
            logger.error(
                "OllamaProvider failed to record dispatch event — dispatch_id=%s "
                "tenant_id=%s session_id=%s success=%s "
                "(C-059 evidence gap — DB write failed)",
                dispatch_id,
                tenant_id,
                session_id,
                success,
                exc_info=True,
                extra={"context": {"dispatch_id": dispatch_id, "error": str(exc)}},
            )
            # Evidence gap — do not re-raise; LLM response must be returned to caller.
            # The logged error is the C-059 evidence record for this gap.