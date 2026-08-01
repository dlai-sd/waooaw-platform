# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059, C-088, C-089, C-091

from __future__ import annotations

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
            import json
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
        import json
        await redis_client.setex(
            FULL_CATALOG_KEY,
            3600,
            json.dumps(entries_data),
        )
        logger.info("thread_catalog_cached", extra={"count": len(entries)})
        
        return ThreadCatalogResponse(entries=entries_data)
    
    except Exception as exc:
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
    response_model=dict,
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict:
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
            detail=f"Invalid agent_type or bundle_tier: {exc}",
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
        → below_floor = True
        → HTTP 422 (UNPROCESSABLE_ENTITY) with minimum_compliant_price_paise in body
        → Writes to institutional.pricing_floor_log (C-059)
    - If proposed_price_paise >= minimum_compliant_price_paise:
        → outcome = "APPROVED"
        → below_floor = False
        → HTTP 200 OK
        → Writes to institutional.pricing_floor_log (C-059)
    
    C-088: MUST check billing_profiles.status == FOUNDER_AUTHORIZED before validation.
    
    Returns PriceValidation with fields:
    {
        outcome: "APPROVED" | "REJECTED",
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        minimum_margin_pct: float,
        below_floor: bool,
        validation_id: UUID,
    }
    """
    try:
        result = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )
        
        # Log validation result (C-059)
        logger.info(
            "price_validation_recorded",
            extra={
                "validation_id": str(result.validation_id),
                "outcome": result.outcome,
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        
        # C-089: Return 422 if below floor
        if result.below_floor:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Price below constitutional margin floor",
                    "minimum_compliant_price_paise": result.minimum_compliant_price_paise,
                    "cost_floor_paise": result.cost_floor_paise,
                    "minimum_margin_pct": result.minimum_margin_pct,
                },
            )
        
        return result
    
    except ValueError as exc:
        logger.warning(
            "price_validation_invalid_params",
            extra={
                "error": str(exc),
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid parameters: {exc}",
        ) from exc
    
    except HTTPException:
        raise
    
    except Exception as exc:
        logger.error(
            "price_validation_error",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price validation failed",
        ) from exc


@router.post("/derive", response_model=DerivedPriceResponse)
async def derive_price(
    request: PriceDeriveRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> DerivedPriceResponse:
    """
    C-089, C-051: Derive a compliant price given cost floor and target margin.
    
    Request body: {agent_type, bundle_tier, target_margin_pct?}
    
    Formula (margin-on-revenue):
    - If target_margin_pct is None: use bundle_profiles.minimum_margin_pct
    - derived_price = cost_floor / (1 - target_margin_pct / 100)
    
    Returns: {derived_price_paise: int, target_margin_pct: float, cost_floor_paise: int}
    
    Raises:
    - 422 if invalid agent_type/bundle_tier
    - 422 if target_margin_pct >= 100 (division by zero) or < 0
    - 500 on DB error
    """
    try:
        derived = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )
        
        logger.info(
            "price_derived",
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "derived_price_paise": derived.derived_price_paise,
                "target_margin_pct": derived.target_margin_pct,
            },
        )
        
        return derived
    
    except ValueError as exc:
        logger.warning(
            "price_derive_invalid_params",
            extra={
                "error": str(exc),
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "target_margin_pct": request.target_margin_pct,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid parameters: {exc}",
        ) from exc
    
    except Exception as exc:
        logger.error(
            "price_derive_error",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price derivation failed",
        ) from exc