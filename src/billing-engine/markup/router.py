# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059, C-088, C-089, C-091

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from config import settings
from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    DerivedPriceResponse,
    ThreadCatalogResponse,
)
from markup.thread_catalog import (
    _load_from_db,
    _get_redis,
    FULL_CATALOG_KEY,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_bundle_engine() -> BundleEngine:
    """
    Dependency: BundleEngine instance.
    In production, this would be injected from a service container.
    For now, instantiate with settings.
    """
    return BundleEngine(db_url=settings.database_url)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/thread-catalog", response_model=ThreadCatalogResponse)
async def get_thread_catalog() -> ThreadCatalogResponse:
    """
    C-091: Get the thread catalog (thread definitions, raw costs, markups).
    
    Delegates to existing ThreadCatalogService.
    Response shape includes thread_id, display_name, provider, raw_cost_inr_paise,
    total_markup_pct, marked_up_cost_paise, is_platform_thread, applicable_agents, status.
    
    SLA: ≤200ms p99 (Redis cache).
    """
    try:
        redis_client = _get_redis()
        cached = await redis_client.get(FULL_CATALOG_KEY)
        
        if cached:
            entries_data = json.loads(cached)
            logger.info("thread_catalog_cache_hit", extra={"source": "redis"})
            return ThreadCatalogResponse(entries=entries_data)
        
        # Load from DB and cache
        entries = await _load_from_db()
        entries_data = [
            {
                "thread_id": e.thread_id,
                "display_name": e.display_name,
                "provider": e.provider,
                "unit_description": e.unit_description,
                "raw_cost_inr_paise": e.raw_cost_inr_paise,
                "total_markup_pct": e.total_markup_pct,
                "marked_up_cost_paise": e.marked_up_cost_paise,
                "is_platform_thread": e.is_platform_thread,
                "applicable_agents": e.applicable_agents,
                "status": e.status,
            }
            for e in entries
        ]
        
        # Cache for 1 hour (3600 seconds)
        await redis_client.setex(
            FULL_CATALOG_KEY,
            3600,
            json.dumps(entries_data),
        )
        logger.info("thread_catalog_cached", extra={"count": len(entries)})
        
        return ThreadCatalogResponse(entries=entries_data)
    
    except (ValueError, KeyError, TypeError) as exc:
        logger.error(
            "thread_catalog_load_failed",
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load thread catalog",
        ) from exc


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=dict[str, int],
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict[str, int]:
    """
    C-088, C-089: Get the cost floor (minimum price) for a bundle.
    
    Reads bundle_profiles.cost_floor_paise from DB (NOT recomputed).
    Does NOT perform pricing validation — just returns the floor.
    
    Returns: {cost_floor_paise: int}
    Raises: 404 if bundle not found, 422 if invalid agent_type.
    """
    try:
        cost_floor_paise = await engine.cost_floor(agent_type, bundle_tier)
        return {"cost_floor_paise": cost_floor_paise}
    
    except ValueError as exc:
        logger.warning(
            "bundle_cost_floor_invalid_params",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid agent_type or bundle_tier",
        ) from exc
    
    except KeyError as exc:
        logger.warning(
            "bundle_cost_floor_not_found",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        ) from exc
    
    except Exception as exc:
        logger.error(
            "bundle_cost_floor_error",
            exc_info=True,
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from exc


@router.post("/validate", response_model=PriceValidation, status_code=200)
async def validate_price(
    request: PriceValidationRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> PriceValidation:
    """
    C-088, C-089, C-059: Validate proposed price against constitutional margin floor.
    
    Request body: {agent_type, bundle_tier, proposed_price_paise}
    
    Behavior (C-089 margin enforcement):
    - Computes minimum_compliant_price_paise = cost_floor / (1 - minimum_margin_pct/100)
    - If proposed_price_paise < minimum_compliant_price_paise:
        → outcome = "REJECTED"
        → HTTP 200 with outcome=REJECTED, minimum_compliant_price_paise in body
        → Writes to institutional.pricing_floor_log (C-059 audit obligation)
    - If proposed_price_paise >= minimum_compliant_price_paise:
        → outcome = "APPROVED"
        → HTTP 200 with outcome=APPROVED, cost_floor_paise in body
        → Writes to institutional.pricing_floor_log (C-059 audit obligation)
    
    Response always HTTP 200 (not 422). The 422 error case is handled by returning
    outcome=REJECTED with minimum_compliant_price_paise populated.
    
    C-059: Every validation (APPROVED or REJECTED) writes an audit row.
    """
    try:
        result = await engine.validate_price(
            request.agent_type,
            request.bundle_tier,
            request.proposed_price_paise,
        )
        return result
    
    except ValueError as exc:
        logger.warning(
            "validate_price_invalid_params",
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid agent_type or bundle_tier",
        ) from exc
    
    except Exception as exc:
        logger.error(
            "validate_price_error",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from exc


@router.post("/derive", response_model=DerivedPriceResponse, status_code=200)
async def derive_price(
    request: PriceDeriveRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> DerivedPriceResponse:
    """
    C-088, C-089: Derive the recommended price for a bundle given a target margin.
    
    Request body: {agent_type, bundle_tier, target_margin_pct: Optional[float]}
    
    Formula (margin-on-revenue):
      derived_price = cost_floor_paise / (1 - target_margin_pct / 100)
    
    If target_margin_pct is None:
      Uses bundle_profiles.minimum_margin_pct as the default margin.
    
    Returns: {derived_price_paise: int, margin_pct: float, cost_floor_paise: int}
    Raises: 422 if agent_type or bundle_tier invalid.
    """
    try:
        result = await engine.derive_price(
            request.agent_type,
            request.bundle_tier,
            request.target_margin_pct,
        )
        return result
    
    except ValueError as exc:
        logger.warning(
            "derive_price_invalid_params",
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "target_margin_pct": request.target_margin_pct,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid agent_type, bundle_tier, or target_margin_pct",
        ) from exc
    
    except Exception as exc:
        logger.error(
            "derive_price_error",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from exc