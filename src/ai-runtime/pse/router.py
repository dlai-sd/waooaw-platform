# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer,§1 LLM Gateway
# constitutional_basis: C-023, C-051, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import sqlalchemy.ext.asyncio as sa_async
from sqlalchemy import text

from pse.tiers import LlmTier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OLLAMA_BASE_URL = "http://ollama:11434"
_OLLAMA_GENERATE_PATH = "/api/generate"
_OLLAMA_MODEL = "llama3.2:3b"

_OLLAMA_TIMEOUT_SECONDS = 30

_DB_INSERT_DISPATCH_EVENT = text(
    """
    INSERT INTO institutional.provider_dispatch_events
        (id, tier, provider_id, model_id, routed_at, task_complexity, language, status, error_detail)
    VALUES
        (:id, :tier, :provider_id, :model_id, :routed_at, :task_complexity, :language, :status, :error_detail)
    """
)

# ---------------------------------------------------------------------------
# PSE Routing logic
# ---------------------------------------------------------------------------


def _select_tier(task_complexity: str, language: str | None) -> LlmTier:
    """
    PSE rule engine — stateless, deterministic.

    PSE-R01: task_complexity=simple  → LOCAL
    PSE-R02: task_complexity=medium AND language=indic → MID
    PSE-R03: task_complexity=complex → FRONTIER
    Default: LOCAL (ensures C-051 ≥66% LOCAL/MID)
    """
    complexity = (task_complexity or "simple").strip().lower()

    _INDIC_LANGUAGES = {"hi", "mr", "te", "ta", "kn", "pa", "bn", "gu"}
    lang_code = (language or "").strip().lower()

    if complexity == "simple":
        return LlmTier.LOCAL
    if complexity == "medium":
        if lang_code in _INDIC_LANGUAGES:
            return LlmTier.MID
        return LlmTier.LOCAL
    if complexity == "complex":
        return LlmTier.FRONTIER
    # Fallback — unknown complexity routes LOCAL to preserve C-051
    logger.warning("Unknown task_complexity value, defaulting to LOCAL tier")
    return LlmTier.LOCAL


# ---------------------------------------------------------------------------
# Ollama (LOCAL tier) dispatch
# ---------------------------------------------------------------------------


async def _dispatch_ollama(prompt: str) -> dict[str, Any]:
    """
    Calls the Ollama docker-compose service for LOCAL tier inference.

    C-063: prompt content is never logged.
    ADR-028: prompt content never logged.
    """
    url = f"{_OLLAMA_BASE_URL}{_OLLAMA_GENERATE_PATH}"
    payload = {
        "model": _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException:
            logger.error(
                "Ollama request timed out after %s seconds",
                _OLLAMA_TIMEOUT_SECONDS,
                exc_info=True,
                extra={"context": "ollama_dispatch_timeout"},
            )
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama returned HTTP error status=%s",
                exc.response.status_code,
                exc_info=True,
                extra={"context": "ollama_dispatch_http_error"},
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Ollama connection error: %s",
                type(exc).__name__,
                exc_info=True,
                extra={"context": "ollama_dispatch_connection_error"},
            )
            raise

    data = response.json()
    # ADR-028 / C-063: never log response content
    return {
        "tier": LlmTier.LOCAL.value,
        "provider_id": "ollama",
        "model_id": _OLLAMA_MODEL,
        "response": data.get("response", ""),
        "done": data.get("done", False),
        "total_duration_ns": data.get("total_duration"),
    }


# ---------------------------------------------------------------------------
# Stub dispatchers for MID and FRONTIER
# (full implementations are in their respective provider adapter files)
# ---------------------------------------------------------------------------


async def _dispatch_mid(prompt: str, language: str | None) -> dict[str, Any]:
    """
    MID_TIER dispatch stub — Sarvam (indic) or Gemini 2.0 Flash.
    Full implementation lives in pse/providers/sarvam_provider.py and
    pse/providers/vertex_provider.py.  Raises NotImplementedError until
    those adapters are wired in (WC015-02b scope).
    C-063: prompt is not logged here.
    """
    raise NotImplementedError(
        "MID_TIER provider dispatch not yet implemented in this adapter scope (WC015-02b)"
    )


async def _dispatch_frontier(prompt: str) -> dict[str, Any]:
    """
    FRONTIER dispatch stub — Gemini 2.5 Pro / Anthropic.
    Full implementation lives in pse/providers/vertex_provider.py.
    Raises NotImplementedError until that adapter is wired in (WC015-02b scope).
    C-063: prompt is not logged here.
    """
    raise NotImplementedError(
        "FRONTIER provider dispatch not yet implemented in this adapter scope (WC015-02b)"
    )


# ---------------------------------------------------------------------------
# Evidence recording — institutional.provider_dispatch_events
# ---------------------------------------------------------------------------


async def _record_dispatch_event(
    async_session_factory: sa_async.async_sessionmaker,
    event_id: str,
    tier: LlmTier,
    provider_id: str,
    model_id: str,
    task_complexity: str,
    language: str | None,
    status: str,
    error_detail: str | None = None,
) -> None:
    """
    Records a provider dispatch event to institutional.provider_dispatch_events.

    C-059: every dispatch (success or failure) must produce an evidence record.
    C-063: no PII written — only metadata (tier, provider, model, status).
    """
    async with async_session_factory() as session:
        try:
            await session.execute(
                _DB_INSERT_DISPATCH_EVENT,
                {
                    "id": event_id,
                    "tier": tier.value,
                    "provider_id": provider_id,
                    "model_id": model_id,
                    "routed_at": datetime.now(timezone.utc),
                    "task_complexity": task_complexity,
                    "language": language,
                    "status": status,
                    "error_detail": error_detail,
                },
            )
            await session.commit()
        except asyncio.CancelledError:
            await session.rollback()
            raise
        except (ValueError, KeyError, sa_async.exc.SQLAlchemyError):
            await session.rollback()
            logger.error(
                "Failed to record provider dispatch event id=%s status=%s",
                event_id,
                status,
                exc_info=True,
                extra={"context": "record_dispatch_event", "event_id": event_id},
            )
            # C-059: log evidence of evidence-recording failure — do not re-raise
            # so as not to mask the original dispatch result from the caller.


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def route_and_dispatch(
    prompt: str,
    task_complexity: str,
    language: str | None,
    async_session_factory: sa_async.async_sessionmaker,
) -> dict[str, Any]:
    """
    PSE Router — selects tier, dispatches to provider, records evidence.

    Args:
        prompt:                Sanitised (PII-free) prompt text.  C-063 requires
                               the caller to have scrubbed PII before reaching here.
        task_complexity:       "simple" | "medium" | "complex"
        language:              BCP-47 language code or None (e.g. "hi", "en")
        async_session_factory: SQLAlchemy async session factory for evidence writes.

    Returns:
        dict containing tier, provider_id, model_id, response text, and metadata.

    Raises:
        NotImplementedError: MID / FRONTIER tiers not yet wired (WC015-02b).
        httpx.RequestError / httpx.HTTPStatusError: Ollama transport failures.
    """
    event_id = str(uuid.uuid4())
    tier = _select_tier(task_complexity, language)

    logger.info(
        "PSE routing decision event_id=%s tier=%s complexity=%s",
        event_id,
        tier.value,
        task_complexity,
        # C-063: language code is metadata, not PII — safe to log
    )

    provider_id: str
    model_id: str
    result: dict[str, Any]

    try:
        if tier == LlmTier.LOCAL:
            provider_id = "ollama"
            model_id = _OLLAMA_MODEL
            result = await _dispatch_ollama(prompt)

        elif tier == LlmTier.MID:
            _INDIC_LANGUAGES = {"hi", "mr", "te", "ta", "kn", "pa", "bn", "gu"}
            lang_code = (language or "").strip().lower()
            provider_id = "sarvam" if lang_code in _INDIC_LANGUAGES else "google-gemini-flash"
            model_id = "saaras" if provider_id == "sarvam" else "gemini-2.0-flash"
            result = await _dispatch_mid(prompt, language)

        else:
            # FRONTIER
            provider_id = "google-gemini-pro"
            model_id = "gemini-2.5-pro"
            result = await _dispatch_frontier(prompt)

    except asyncio.CancelledError:
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id if "provider_id" in dir() else "unknown",
            model_id if "model_id" in dir() else "unknown",
            task_complexity,
            language,
            status="cancelled",
            error_detail="CancelledError",
        )
        raise

    except NotImplementedError as exc:
        provider_id_safe = provider_id if "provider_id" in locals() else "unknown"
        model_id_safe = model_id if "model_id" in locals() else "unknown"
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id_safe,
            model_id_safe,
            task_complexity,
            language,
            status="not_implemented",
            error_detail=str(exc),
        )
        logger.error(
            "Provider dispatch not implemented event_id=%s tier=%s",
            event_id,
            tier.value,
            exc_info=True,
            extra={"context": "route_and_dispatch", "event_id": event_id},
        )
        raise

    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
        provider_id_safe = provider_id if "provider_id" in locals() else "unknown"
        model_id_safe = model_id if "model_id" in locals() else "unknown"
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id_safe,
            model_id_safe,
            task_complexity,
            language,
            status="error",
            error_detail=type(exc).__name__,
        )
        raise

    # Success path — record evidence
    await _record_dispatch_event(
        async_session_factory,
        event_id,
        tier,
        provider_id,
        model_id,
        task_complexity,
        language,
        status="success",
        error_detail=None,
    )

    result["event_id"] = event_id
    return result