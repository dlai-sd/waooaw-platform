# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer,§1 LLM Gateway
# constitutional_basis: C-023, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

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
        db_pool: Any | None = None,
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
            raise SarvamProviderError(
                f"Sarvam API timed out after {self._timeout}s"
            ) from exc
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
            raise SarvamProviderError(
                f"Sarvam API returned HTTP {response.status_code}"
            )

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
            raise SarvamProviderError("Sarvam API response is not valid JSON") from exc

        normalised = self._parse_response(body, dispatch_event_id, latency_ms)

        await self._record_dispatch_event(
            dispatch_event_id=dispatch_event_id,
            status="success",
            latency_ms=latency_ms,
            model=normalised["model"],
            usage=normalised["usage"],
        )

        return normalised

    async def close(self) -> None:
        """Release underlying httpx client resources."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_payload(
        messages: list[dict[str, str]],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Construct the JSON payload for Sarvam AI chat completions.

        ADR-028: This method must never log or surface prompt content.
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

    @staticmethod
    def _parse_response(
        body: dict[str, Any],
        dispatch_event_id: str,
        latency_ms: float,
    ) -> dict[str, Any]:
        """
        Normalise Sarvam AI response to the platform's LLMProvider contract shape.

        Raises:
            SarvamProviderError: if the payload is missing expected fields.
        """
        try:
            choice = body["choices"][0]
            content: str = choice["message"]["content"]
            model: str = body.get("model", "saaras")
            usage: dict[str, Any] = body.get(
                "usage",
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(
                "Sarvam response missing expected fields — dispatch_event_id=%s",
                dispatch_event_id,
                exc_info=True,
            )
            raise SarvamProviderError(
                "Unexpected Sarvam response shape"
            ) from exc

        return {
            "content": content,
            "model": model,
            "provider": SARVAM_PROVIDER_ID,
            "usage": usage,
            "latency_ms": latency_ms,
            "dispatch_event_id": dispatch_event_id,
        }

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

        C-059: Every call that touches an external LLM must produce an evidence record,
        including failures.  If the DB pool is unavailable the error is logged but NOT
        re-raised — the caller already received or will raise SarvamProviderError for
        the actual dispatch failure; swallowing the record-write error here is
        intentional and documented as a C-059 evidence gap of last resort.

        ADR-028: prompt_tokens / completion_tokens are stored; prompt TEXT is never stored.
        """
        if self._db_pool is None:
            logger.warning(
                "No DB pool configured — dispatch event not persisted; "
                "dispatch_event_id=%s status=%s",
                dispatch_event_id,
                status,
            )
            return

        sql = """
            INSERT INTO institutional.provider_dispatch_events (
                id,
                provider_id,
                model,
                status,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                recorded_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """
        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    sql,
                    dispatch_event_id,
                    SARVAM_PROVIDER_ID,
                    model,
                    status,
                    latency_ms,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    usage.get("total_tokens", 0),
                )
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as exc:
            # C-059: log the evidence gap; do not re-raise (dispatch result already
            # propagated to caller).
            logger.error(
                "Failed to record dispatch event to DB — "
                "dispatch_event_id=%s status=%s",
                dispatch_event_id,
                status,
                exc_info=True,
                extra={"context": "provider_dispatch_events INSERT"},
            )
            # Evidence gap record — satisfies C-059 requirement to document every
            # swallowed exception.
            logger.warning(
                "C-059 evidence gap: dispatch_event_id=%s was NOT persisted due to: %s",
                dispatch_event_id,
                type(exc).__name__,
            )