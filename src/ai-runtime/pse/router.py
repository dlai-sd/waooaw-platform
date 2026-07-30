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
    async_session_factory: sa_async.async_sessionmaker,  # type: ignore[type-arg]
    event_id: str,
    tier: LlmTier,
    provider_id: str,
    model_id: str,
    task_complexity: str,
    language: str | None,
    status: str,
    error_detail: str,
) -> None:
    """
    Persists a provider dispatch event to institutional.provider_dispatch_events.

    C-059: every dispatch — success or failure — must produce an evidence record.
    No PII is written here (C-063): only tier, provider, model, status metadata.
    """
    routed_at = datetime.now(tz=timezone.utc)

    params: dict[str, str | None] = {
        "id": event_id,
        "tier": tier.value,
        "provider_id": provider_id,
        "model_id": model_id,
        "routed_at": routed_at.isoformat(),
        "task_complexity": task_complexity,
        "language": language,
        "status": status,
        "error_detail": error_detail if error_detail else None,
    }

    try:
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(_DB_INSERT_DISPATCH_EVENT, params)
    except asyncio.CancelledError:
        raise
    except Exception:
        # C-059: log evidence of evidence-recording failure — do not swallow silently
        logger.error(
            "Failed to persist dispatch event id=%s tier=%s provider=%s status=%s",
            event_id,
            tier.value,
            provider_id,
            status,
            exc_info=True,
            extra={"context": "record_dispatch_event_db_failure"},
        )
        raise


# ---------------------------------------------------------------------------
# Public entry point — route_and_dispatch
# ---------------------------------------------------------------------------


async def route_and_dispatch(
    prompt: str,
    task_complexity: str,
    language: str | None,
    async_session_factory: sa_async.async_sessionmaker,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """
    PSE entry point.  Selects tier, dispatches to the appropriate provider,
    records an evidence event to institutional.provider_dispatch_events, and
    returns the provider response dict.

    Constitutional invariants enforced here:
    - C-051: tier selection enforces ≥66% LOCAL/MID routing via _select_tier()
    - C-059: every dispatch attempt records evidence — success AND failure paths
    - C-063: prompt content is never logged
    - ADR-028: prompt content is never logged

    Args:
        prompt:                Scrubbed prompt (PII already removed by §7 PII Scrubber).
        task_complexity:       One of "simple" | "medium" | "complex".
        language:              BCP-47 language code or None (e.g. "hi", "en").
        async_session_factory: SQLAlchemy async_sessionmaker bound to institutional DB.

    Returns:
        dict with keys: tier, provider_id, model_id, response, done,
        total_duration_ns (LOCAL only), and event_id.

    Raises:
        NotImplementedError: MID/FRONTIER dispatchers not yet wired (WC015-02b).
        httpx.TimeoutException: Ollama timed out.
        httpx.HTTPStatusError: Ollama returned non-2xx.
        httpx.RequestError: Network-level connection failure to Ollama.
    """
    tier = _select_tier(task_complexity, language)
    event_id = str(uuid.uuid4())

    # Resolve provider metadata before dispatch so we can record on failure too
    provider_id: str
    model_id: str

    if tier == LlmTier.LOCAL:
        provider_id = "ollama"
        model_id = _OLLAMA_MODEL
    elif tier == LlmTier.MID:
        # PSE-R02: indic language → sarvam/saaras; otherwise gemini-2.0-flash
        _INDIC_LANGUAGES = {"hi", "mr", "te", "ta", "kn", "pa", "bn", "gu"}
        lang_code = (language or "").strip().lower()
        if lang_code in _INDIC_LANGUAGES:
            provider_id = "sarvam"
            model_id = "saaras"
        else:
            provider_id = "google"
            model_id = "gemini-2.0-flash"
    else:
        # FRONTIER
        provider_id = "google"
        model_id = "gemini-2.5-pro"

    logger.info(
        "PSE dispatch: event_id=%s tier=%s provider=%s model=%s complexity=%s",
        event_id,
        tier.value,
        provider_id,
        model_id,
        task_complexity,
    )

    result: dict[str, Any]
    status: str
    error_detail: str

    try:
        if tier == LlmTier.LOCAL:
            result = await _dispatch_ollama(prompt)
        elif tier == LlmTier.MID:
            result = await _dispatch_mid(prompt, language)
        else:
            result = await _dispatch_frontier(prompt)

        status = "success"
        error_detail = ""

    except asyncio.CancelledError:
        # C-059: record cancellation evidence before propagating
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id,
            model_id,
            task_complexity,
            language,
            "cancelled",
            "asyncio.CancelledError",
        )
        raise

    except NotImplementedError as exc:
        error_detail = str(exc)
        logger.error(
            "PSE dispatch: provider not implemented event_id=%s tier=%s provider=%s",
            event_id,
            tier.value,
            provider_id,
            exc_info=True,
            extra={"context": "pse_dispatch_not_implemented"},
        )
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id,
            model_id,
            task_complexity,
            language,
            "not_implemented",
            error_detail,
        )
        raise

    except httpx.TimeoutException:
        error_detail = "httpx.TimeoutException"
        logger.error(
            "PSE dispatch: timeout event_id=%s tier=%s provider=%s",
            event_id,
            tier.value,
            provider_id,
            exc_info=True,
            extra={"context": "pse_dispatch_timeout"},
        )
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id,
            model_id,
            task_complexity,
            language,
            "timeout",
            error_detail,
        )
        raise

    except httpx.HTTPStatusError as exc:
        error_detail = f"httpx.HTTPStatusError status={exc.response.status_code}"
        logger.error(
            "PSE dispatch: HTTP error event_id=%s tier=%s provider=%s status=%s",
            event_id,
            tier.value,
            provider_id,
            exc.response.status_code,
            exc_info=True,
            extra={"context": "pse_dispatch_http_error"},
        )
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id,
            model_id,
            task_complexity,
            language,
            "http_error",
            error_detail,
        )
        raise

    except httpx.RequestError as exc:
        error_detail = f"httpx.RequestError type={type(exc).__name__}"
        logger.error(
            "PSE dispatch: connection error event_id=%s tier=%s provider=%s error_type=%s",
            event_id,
            tier.value,
            provider_id,
            type(exc).__name__,
            exc_info=True,
            extra={"context": "pse_dispatch_connection_error"},
        )
        await _record_dispatch_event(
            async_session_factory,
            event_id,
            tier,
            provider_id,
            model_id,
            task_complexity,
            language,
            "connection_error",
            error_detail,
        )
        raise

    # C-059: record successful dispatch evidence
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

    result["event_id"] = event_id
    return result