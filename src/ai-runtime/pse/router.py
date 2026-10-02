# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer,§1 LLM Gateway
# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §3 (AIR refactor)
# constitutional_basis: C-023, C-041, C-051, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import sqlalchemy.ext.asyncio as sa_async
from sqlalchemy import text

from pse.tiers import LlmTier

# CTG import — trust-layer is on PYTHONPATH in Docker (PYTHONPATH=/workspace/src/trust-layer)
try:
    import sys
    import pathlib

    _tl = str(pathlib.Path(__file__).parent.parent.parent / "trust-layer")
    if _tl not in sys.path:
        sys.path.insert(0, _tl)
    from ctg.gateway import ConstitutionalToolGateway, ToolExecutor
    from ctg.models import GatewayResult, ProviderConfig, SessionContext

    _CTG_AVAILABLE = True
except ImportError:  # pragma: no cover — CTG available in Docker; local dev may lack it
    _CTG_AVAILABLE = False
    ConstitutionalToolGateway = None  # type: ignore[assignment,misc]
    SessionContext = None  # type: ignore[assignment,misc]

# GAP-002 (EA R-022): fail-fast in IMPLEMENTATION phase — ungoverned fallback is a C-041 violation.
if not _CTG_AVAILABLE and os.getenv("PLATFORM_PHASE") == "IMPLEMENTATION":  # pragma: no cover
    raise ImportError(
        "CTG unavailable in IMPLEMENTATION phase — "
        "ensure src/trust-layer is on PYTHONPATH. "
        "Ungovernated LLM dispatch violates C-041."
    )

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
    raise NotImplementedError("MID_TIER provider dispatch not yet implemented in this adapter scope (WC015-02b)")


async def _dispatch_frontier(prompt: str) -> dict[str, Any]:
    """
    FRONTIER dispatch stub — Gemini 2.5 Pro / Anthropic.
    Full implementation lives in pse/providers/vertex_provider.py.
    Raises NotImplementedError until that adapter is wired in (WC015-02b scope).
    C-063: prompt is not logged here.
    """
    raise NotImplementedError("FRONTIER provider dispatch not yet implemented in this adapter scope (WC015-02b)")


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


def _build_llm_executor() -> ToolExecutor:
    """
    Returns the LLM executor used by CTG for the 'llm.complete' tool.
    CTG calls this with (tool_name, args, token, config); executor does the HTTP call.
    """

    async def _executor(
        tool_name: str,
        args: dict[str, Any],
        token: str | None,
        config: ProviderConfig,
    ) -> dict[str, Any]:
        provider = args.get("provider", "ollama")
        language = args.get("language")
        prompt = args.get("prompt", "")
        if provider == "ollama":
            return await _dispatch_ollama(prompt)
        if provider in ("sarvam", "google") and config.auth_method == "API_KEY":
            return await _dispatch_mid(prompt, language)
        return await _dispatch_frontier(prompt)

    return _executor


def _make_gateway() -> ConstitutionalToolGateway:
    """Factory used by route_and_dispatch. Tests patch this to inject mocks."""
    return ConstitutionalToolGateway(
        bp_base_url=os.getenv("BP_BASE_URL", "http://business-platform:5003"),
        vault_base_url=os.getenv("OAUTH_VAULT_BASE_URL", "http://oauth-vault:8130"),
        ce_address=os.getenv("CONSTITUTIONAL_ENGINE_ADDRESS", "constitutional-engine:7000"),
        executor=_build_llm_executor(),
    )


async def route_and_dispatch(
    prompt: str,
    task_complexity: str,
    language: str | None,
    async_session_factory: sa_async.async_sessionmaker,  # type: ignore[type-arg]
    customer_id: str | None = None,
    redis_client: Any | None = None,
    session_ctx: SessionContext | None = None,
    trial_entitled: bool = False,
) -> dict[str, Any]:
    """
    PSE entry point.  Selects tier, dispatches to the appropriate provider,
    records an evidence event to institutional.provider_dispatch_events, and
    returns the provider response dict.

    Constitutional invariants enforced here:
    - C-049: trial customers are constrained to LOCAL tier (WC-032)
    - C-051: tier selection enforces ≥66% LOCAL/MID routing via _select_tier()
    - C-059: every dispatch attempt records evidence — success AND failure paths
    - C-063: prompt content is never logged
    - ADR-028: prompt content is never logged

    Args:
        prompt:                Scrubbed prompt (PII already removed by §7 PII Scrubber).
        task_complexity:       One of "simple" | "medium" | "complex".
        language:              BCP-47 language code or None (e.g. "hi", "en").
        async_session_factory: SQLAlchemy async_sessionmaker bound to institutional DB.
        customer_id:           Customer UUID string — used for trial mode Redis lookup.
        redis_client:          Async Redis client — shared instance from billing-engine.
        trial_entitled:        WBE-validated relationship trial entitlement. Forces LOCAL
                       without consulting the advisory Redis projection.

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

    # C-049: trial customers must use LOCAL (Ollama) — zero procurement cost
    if trial_entitled:
        tier = LlmTier.LOCAL
    elif redis_client is not None and customer_id is not None:
        customer_mode = await redis_client.get(f"wbe:customer:{customer_id}:mode")
        if customer_mode == b"TRIAL":
            tier = LlmTier.LOCAL
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

    # Build SessionContext for CTG (tenant/contract from session_ctx or platform defaults)
    _ctx: SessionContext | None = session_ctx
    if _ctx is None and _CTG_AVAILABLE:
        try:
            _tenant_id = UUID(customer_id) if customer_id else UUID(int=0)
        except ValueError:
            _tenant_id = UUID(int=0)
        _ctx = SessionContext(
            tenant_id=_tenant_id,
            agent_id="pse",
            contract_id=customer_id or "",
            skill_id="llm.complete",
            decision_space="",
        )

    # ADR-042 §3: CTG pipeline — CE.ValidateAction → oauth-vault → execute → audit_sink
    if _CTG_AVAILABLE and _ctx is not None:
        gw = _make_gateway()
        try:
            gw_result: GatewayResult = await gw.call(
                "llm.complete",
                {
                    "provider": provider_id,
                    "model": model_id,
                    "prompt": prompt,
                    "language": language,
                },
                _ctx,
            )
            if gw_result.error is not None:
                error_detail = gw_result.error.message
                status = "failed"
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
                raise RuntimeError(f"CTG tool error: {gw_result.error.code}")
            result = gw_result.result or {}
            status = "success"
            error_detail = ""
        except asyncio.CancelledError:
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
        except Exception as exc:
            if not isinstance(exc, RuntimeError) or "CTG tool error" not in str(exc):
                error_detail = type(exc).__name__
                status = "failed"
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
            raise
    else:
        # Fallback path when CTG not available (local dev without trust-layer on path)
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
        except Exception as exc:
            error_detail = type(exc).__name__
            status = "not_implemented" if isinstance(exc, NotImplementedError) else "failed"
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
