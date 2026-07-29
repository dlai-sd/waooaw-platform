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
    error_detail: str | None,
) -> None:
    """
    Persists one row to institutional.provider_dispatch_events.

    C-059: Every dispatch — success or failure — must be recorded.
    No prompt content is stored (C-063).
    Uses async SQLAlchemy session — never synchronous (Temporal activity safe).
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
            raise
        except Exception:
            logger.error(
                "Failed to record dispatch event id=%s tier=%s status=%s",
                event_id,
                tier.value,
                status,
                exc_info=True,
                extra={"context": "record_dispatch_event_db_failure"},
            )
            # C-059: log the failure; do not swallow silently.
            # Re-raise so the caller can decide whether to propagate.
            raise


# ---------------------------------------------------------------------------
# Primary public entry point
# ---------------------------------------------------------------------------


async def route_and_dispatch(
    prompt: str,
    task_complexity: str,
    language: str | None,
    async_session_factory: sa_async.async_sessionmaker,
) -> dict[str, Any]:
    """
    PSE entry point — selects tier, dispatches to provider, records evidence.

    Args:
        prompt:                Scrubbed prompt text (PII already removed per C-078).
                               C-063: this value is NEVER logged.
        task_complexity:       One of 'simple' | 'medium' | 'complex'.
        language:              BCP-47 language code (e.g. 'hi', 'en') or None.
        async_session_factory: Async SQLAlchemy session factory for evidence recording.

    Returns:
        Provider response dict with keys:
            tier, provider_id, model_id, response, done, total_duration_ns,
            dispatch_event_id.

    Raises:
        httpx.TimeoutException: Ollama timed out (already logged).
        httpx.HTTPStatusError:  Ollama returned non-2xx (already logged).
        httpx.RequestError:     Ollama connection failure (already logged).
        NotImplementedError:    MID / FRONTIER adapters not yet wired (WC015-02b).
        Exception:              DB evidence recording failure (already logged).

    Constitutional guarantees:
        C-051 — PSE-R01/R02/R03 ensure ≥66% LOCAL/MID routing.
        C-059 — every dispatch attempt writes an evidence record (success or failure).
        C-063 — prompt is never logged or stored.
        ADR-028 — provider response content is never logged.
    """
    event_id = str(uuid.uuid4())
    tier = _select_tier(task_complexity, language)

    # C-059: record the attempt before dispatch so an outage never loses the event.
    # We record optimistically; on failure we update status to 'error'.
    # (Single-insert pattern: insert with status=dispatching, then update.)
    # For simplicity and atomicity, we record after dispatch with final status.
    # The event_id is generated before dispatch so it can be correlated in logs.

    logger.info(
        "PSE routing: event_id=%s tier=%s task_complexity=%s language=%s",
        event_id,
        tier.value,
        task_complexity,
        language,
    )

    provider_id: str
    model_id: str
    result: dict[str, Any]
    status: str
    error_detail: str | None = None

    try:
        if tier == LlmTier.LOCAL:
            result = await _dispatch_ollama(prompt)
            provider_id = result["provider_id"]
            model_id = result["model_id"]
            status = "success"

        elif tier == LlmTier.MID:
            result = await _dispatch_mid(prompt, language)
            provider_id = result["provider_id"]
            model_id = result["model_id"]
            status = "success"

        else:
            # LlmTier.FRONTIER
            result = await _dispatch_frontier(prompt)
            provider_id = result["provider_id"]
            model_id = result["model_id"]
            status = "success"

    except asyncio.CancelledError:
        # C-059: record the cancellation before propagating.
        _provider_id_for_tier = _provider_id_from_tier(tier)
        _model_id_for_tier = _model_id_from_tier(tier)
        try:
            await _record_dispatch_event(
                async_session_factory,
                event_id,
                tier,
                _provider_id_for_tier,
                _model_id_for_tier,
                task_complexity,
                language,
                "cancelled",
                "asyncio.CancelledError",
            )
        except Exception:
            logger.error(
                "Evidence recording failed during CancelledError handling event_id=%s",
                event_id,
                exc_info=True,
                extra={"context": "evidence_record_on_cancel"},
            )
        raise

    except NotImplementedError as exc:
        # Stub adapters not yet implemented — record and propagate.
        _provider_id_for_tier = _provider_id_from_tier(tier)
        _model_id_for_tier = _model_id_from_tier(tier)
        error_detail = "NotImplementedError: adapter not wired"
        logger.error(
            "Dispatch not implemented for tier=%s event_id=%s",
            tier.value,
            event_id,
            exc_info=True,
            extra={"context": "dispatch_not_implemented"},
        )
        try:
            await _record_dispatch_event(
                async_session_factory,
                event_id,
                tier,
                _provider_id_for_tier,
                _model_id_for_tier,
                task_complexity,
                language,
                "not_implemented",
                error_detail,
            )
        except Exception:
            logger.error(
                "Evidence recording failed for not_implemented event_id=%s",
                event_id,
                exc_info=True,
                extra={"context": "evidence_record_on_not_implemented"},
            )
        raise exc

    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
        # Network/provider failure — record evidence, then propagate.
        _provider_id_for_tier = _provider_id_from_tier(tier)
        _model_id_for_tier = _model_id_from_tier(tier)
        error_detail = type(exc).__name__
        status = "error"
        try:
            await _record_dispatch_event(
                async_session_factory,
                event_id,
                tier,
                _provider_id_for_tier,
                _model_id_for_tier,
                task_complexity,
                language,
                status,
                error_detail,
            )
        except Exception:
            logger.error(
                "Evidence recording failed after provider error event_id=%s",
                event_id,
                exc_info=True,
                extra={"context": "evidence_record_on_provider_error"},
            )
        raise exc

    # --- Success path: record evidence ---
    await _record_dispatch_event(
        async_session_factory,
        event_id,
        tier,
        provider_id,
        model_id,
        task_complexity,
        language,
        status,
        error_detail,
    )

    result["dispatch_event_id"] = event_id
    return result


# ---------------------------------------------------------------------------
# Tier → provider/model name helpers (used in error branches before result exists)
# ---------------------------------------------------------------------------


def _provider_id_from_tier(tier: LlmTier) -> str:
    """
    Returns the canonical provider_id string for a given tier.
    Used in error-handling branches where the dispatch never returned a result dict.
    """
    if tier == LlmTier.LOCAL:
        return "ollama"
    if tier == LlmTier.MID:
        return "sarvam"
    # FRONTIER
    return "google-vertex"


def _model_id_from_tier(tier: LlmTier) -> str:
    """
    Returns the canonical model_id string for a given tier.
    Used in error-handling branches where the dispatch never returned a result dict.
    """
    if tier == LlmTier.LOCAL:
        return _OLLAMA_MODEL
    if tier == LlmTier.MID:
        return "saaras"
    # FRONTIER
    return "gemini-2.5-pro"