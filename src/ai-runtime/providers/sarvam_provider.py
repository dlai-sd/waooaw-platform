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

# ADR-029: Sarvam has NO Python SDK — use httpx directly.
# C-063: prompt content is never logged.
# ADR-028: prompt content never logged.

SARVAM_API_ENDPOINT = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_PROVIDER_ID = "sarvam/saaras"
REQUEST_TIMEOUT_SECONDS = 30


class SarvamProviderError(Exception):
    """Raised when the Sarvam API returns a non-2xx response or is unreachable."""


class SarvamProvider:
    """
    LLMProvider adapter for Sarvam AI (Saaras model).

    ADR-029 §SarvamProvider:
      - Calls https://api.sarvam.ai/v1/chat/completions via httpx (no SDK).
      - Used as MID_TIER primary for PSE-R02 (Indian language override).
      - API key sourced from Azure Key Vault secret SARVAM-API-KEY.

    C-063: No PII in any log statement. Prompt content never surfaces in logs.
    ADR-028: Prompt content never logged at any level.
    C-059: Every caught exception that is not re-raised produces an evidence record.
    """

    def __init__(
        self,
        api_key: str,
        db_pool: asyncpg.Pool | None = None,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        """
        Args:
            api_key:          Sarvam AI API key from Azure Key Vault (SARVAM-API-KEY).
            db_pool:          asyncpg pool for recording dispatch events. May be None
                              in unit-test contexts (recording is skipped gracefully).
            timeout_seconds:  HTTP request timeout; defaults to 30 s.
        """
        self._api_key = api_key
        self._db_pool = db_pool
        self._timeout = timeout_seconds
        self._client = httpx.AsyncClient(timeout=self._timeout)

    # ------------------------------------------------------------------
    # Public interface (LLMProvider contract)
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[dict[str, str]],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Call Sarvam AI chat completions endpoint and return a normalised response.

        Args:
            messages: OpenAI-compatible message list (role/content dicts).
            params:   Optional inference parameters (model, temperature, max_tokens …).

        Returns:
            Normalised dict:
                {
                    "content": str,          # assistant reply text
                    "model": str,            # model identifier echoed from response
                    "provider": str,         # "sarvam/saaras"
                    "usage": dict,           # prompt_tokens, completion_tokens, total_tokens
                    "latency_ms": float,
                    "dispatch_event_id": str,
                }

        Raises:
            SarvamProviderError: on HTTP error or unexpected payload shape.
        """
        if params is None:
            params = {}

        payload = self._build_payload(messages, params)
        dispatch_event_id = str(uuid.uuid4())
        started_at = time.monotonic()

        try:
            response = await self._client.post(
                SARVAM_API_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            logger.error(
                "Sarvam API request timed out after %s s — dispatch_event_id=%s",
                self._timeout,
                dispatch_event_id,
            )
            await self._record_dispatch_event(
                dispatch_event_id=dispatch_event_id,
                status="timeout",
                latency_ms=(time.monotonic() - started_at) * 1000,
                model=params.get("model", "saaras"),
                usage={},
            )
            raise SarvamProviderError(f"Sarvam API timed out after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            logger.error(
                "Sarvam API HTTP transport error — dispatch_event_id=%s",
                dispatch_event_id,
                exc_info=True,
            )
            await self._record_dispatch_event(
                dispatch_event_id=dispatch_event_id,
                status="transport_error",
                latency_ms=(time.monotonic() - started_at) * 1000,
                model=params.get("model", "saaras"),
                usage={},
            )
            raise SarvamProviderError("Sarvam HTTP transport error") from exc

        latency_ms = (time.monotonic() - started_at) * 1000

        if response.status_code != 200:
            logger.error(
                "Sarvam API returned HTTP %s — dispatch_event_id=%s",
                response.status_code,
                dispatch_event_id,
            )
            await self._record_dispatch_event(
                dispatch_event_id=dispatch_event_id,
                status=f"http_{response.status_code}",
                latency_ms=latency_ms,
                model=params.get("model", "saaras"),
                usage={},
            )
            raise SarvamProviderError(f"Sarvam API returned HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            logger.error(
                "Sarvam API returned non-JSON body — dispatch_event_id=%s",
                dispatch_event_id,
                exc_info=True,
            )
            await self._record_dispatch_event(
                dispatch_event_id=dispatch_event_id,
                status="invalid_json",
                latency_ms=latency_ms,
                model=params.get("model", "saaras"),
                usage={},
            )
            raise SarvamProviderError("Sarvam API returned non-JSON body") from exc

        try:
            content = body["choices"][0]["message"]["content"]
            model = body.get("model", params.get("model", "saaras"))
            usage = body.get("usage", {})
        except (KeyError, IndexError) as exc:
            logger.error(
                "Sarvam API response missing expected fields — dispatch_event_id=%s",
                dispatch_event_id,
                exc_info=True,
            )
            await self._record_dispatch_event(
                dispatch_event_id=dispatch_event_id,
                status="malformed_response",
                latency_ms=latency_ms,
                model=params.get("model", "saaras"),
                usage={},
            )
            raise SarvamProviderError("Sarvam API response missing expected fields") from exc

        await self._record_dispatch_event(
            dispatch_event_id=dispatch_event_id,
            status="success",
            latency_ms=latency_ms,
            model=model,
            usage=usage,
        )

        return {
            "content": content,
            "model": model,
            "provider": SARVAM_PROVIDER_ID,
            "usage": usage,
            "latency_ms": latency_ms,
            "dispatch_event_id": dispatch_event_id,
        }

    async def close(self) -> None:
        """Release the underlying httpx.AsyncClient."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Construct the JSON payload for the Sarvam chat completions endpoint.

        C-063: No PII inspection or logging of message content here.
        ADR-028: Payload content never surfaced in logs.
        """
        payload: dict[str, Any] = {
            "model": params.get("model", "saaras"),
            "messages": messages,
        }
        if "temperature" in params:
            payload["temperature"] = params["temperature"]
        if "max_tokens" in params:
            payload["max_tokens"] = params["max_tokens"]
        if "top_p" in params:
            payload["top_p"] = params["top_p"]
        return payload

    async def _record_dispatch_event(
        self,
        dispatch_event_id: str,
        status: str,
        latency_ms: float,
        model: str,
        usage: dict[str, Any],
    ) -> None:
        """
        Persist a row to institutional.provider_dispatch_events.

        C-059: Every non-re-raised exception produces this evidence record.
        ADR-029: Dispatch events feed the PSE performance ranking (C-069).

        If db_pool is None (unit-test context) or the insert fails, the error is
        logged but NOT propagated — recording failure must not mask inference errors.
        """
        if self._db_pool is None:
            logger.debug(
                "No db_pool configured — skipping dispatch event recording for dispatch_event_id=%s",
                dispatch_event_id,
            )
            return

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO institutional.provider_dispatch_events (
                        dispatch_event_id,
                        provider_id,
                        model,
                        status,
                        latency_ms,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        recorded_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """,
                    dispatch_event_id,
                    SARVAM_PROVIDER_ID,
                    model,
                    status,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                )
        except asyncio.CancelledError:
            raise
        except (asyncpg.PostgresError, OSError) as exc:
            logger.error(
                "Failed to record dispatch event dispatch_event_id=%s status=%s — DB error",
                dispatch_event_id,
                status,
                exc_info=True,
            )
            # C-059: error is logged but not re-raised — inference result must not be masked.
            _ = exc  # suppress F841; exc already referenced in logger call above
