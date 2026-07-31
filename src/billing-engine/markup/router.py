# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from src.billing_engine.markup.bundle_engine import BundleEngine
from src.billing_engine.markup.models import (
    PriceValidation,
    PriceValidationRequest,
    PriceDeriveRequest,
)
from src.billing_engine.markup.thread_catalog import ThreadCatalogService, ThreadCatalogEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


# ── Response models ──────────────────────────────────────────────────────────

class ValidationErrorResponse(BaseModel):
    """HTTP 422 response body on C-089 margin floor violation."""
    detail: str
    outcome: str = Field(default="REJECTED")
    cost_floor_paise: int
    minimum_compliant_price_paise: int
    proposed_price_paise: int


class ThreadCatalogResponse(BaseModel):
    """Thread catalog entry response."""
    thread_id: str
    display_name: str
    provider: str
    unit_description: str
    raw_cost_inr_paise: int
    total_markup_pct: float
    marked_up_cost_paise: int
    is_platform_thread: bool
    applicable_agents: list[str]
    status: str


class BundleCostFloorResponse(BaseModel):
    """Cost floor response."""
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int


class PriceDeriveResponse(BaseModel):
    """Price derivation response."""
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    target_margin_pct: float | None
    derived_price_paise: int
    effective_margin_pct: float


# ── Dependency: BundleEngine ─────────────────────────────────────────────────

async def get_bundle_engine() -> BundleEngine:
    """Inject BundleEngine service."""
    return BundleEngine()


async def get_thread_catalog_service() -> ThreadCatalogService:
    """Inject ThreadCatalogService."""
    return ThreadCatalogService()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/thread-catalog", response_model=list[ThreadCatalogResponse])
async def get_thread_catalog(
    service: ThreadCatalogService = Depends(get_thread_catalog_service),
) -> list[ThreadCatalogResponse]:
    """
    GET /pricing/thread-catalog
    
    Fetch all active thread catalog entries (C-091: Thread Catalog Sovereignty).
    Delegates to ThreadCatalogService; returns thread definitions with cost and markup data.
    
    Raises:
        HTTPException 500: on database or cache failure
    """
    try:
        entries: list[ThreadCatalogEntry] = await service.get_all_threads()
        logger.info("Retrieved %d thread catalog entries", len(entries))
        return [
            ThreadCatalogResponse(
                thread_id=entry.thread_id,
                display_name=entry.display_name,
                provider=entry.provider,
                unit_description=entry.unit_description,
                raw_cost_inr_paise=entry.raw_cost_inr_paise,
                total_markup_pct=entry.total_markup_pct,
                marked_up_cost_paise=entry.marked_up_cost_paise,
                is_platform_thread=entry.is_platform_thread,
                applicable_agents=entry.applicable_agents,
                status=entry.status,
            )
            for entry in entries
        ]
    except Exception as e:
        logger.error("Failed to fetch thread catalog", exc_info=True, extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch thread catalog",
        ) from e


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=BundleCostFloorResponse,
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> BundleCostFloorResponse:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    
    Fetch cost floor for a given agent type and bundle tier (C-089: Margin Floor).
    Reads from bundle_profiles.cost_floor_paise — does NOT recompute.
    
    Args:
        agent_type: agent type identifier (e.g., 'DMA', 'RESEARCH_BOT')
        bundle_tier: bundle tier (e.g., 'STARTER', 'PRO')
    
    Returns:
        BundleCostFloorResponse with cost_floor_paise
    
    Raises:
        HTTPException 404: bundle not found
        HTTPException 500: database error
    """
    try:
        cost_floor = await engine.cost_floor(agent_type, bundle_tier)
        logger.info("Cost floor retrieved: agent_type=%s bundle_tier=%s cost_floor_paise=%d",
                   agent_type, bundle_tier, cost_floor)
        return BundleCostFloorResponse(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            cost_floor_paise=cost_floor,
        )
    except ValueError as e:
        logger.warning("Bundle not found: agent_type=%s bundle_tier=%s", agent_type, bundle_tier)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Failed to retrieve cost floor", exc_info=True, extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from e


@router.post("/validate", response_model=PriceValidation)
async def validate_price(
    request: PriceValidationRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> PriceValidation:
    """
    POST /pricing/validate
    
    Validate a proposed price against the constitutional margin floor (C-089).
    C-059: writes to pricing_floor_log on BOTH APPROVED and REJECTED outcomes.
    
    Request body:
        {
          "agent_type": "DMA",
          "bundle_tier": "STARTER",
          "proposed_price_paise": 50000
        }
    
    Returns on success (200):
        {
          "outcome": "APPROVED",
          "cost_floor_paise": 40000,
          "minimum_compliant_price_paise": 40000,
          "proposed_price_paise": 50000
        }
    
    Returns on C-089 floor violation (422):
        HTTP 422 Unprocessable Entity with body:
        {
          "detail": "Price below constitutional margin floor",
          "outcome": "REJECTED",
          "cost_floor_paise": 40000,
          "minimum_compliant_price_paise": 50000,
          "proposed_price_paise": 35000
        }
    
    Raises:
        HTTPException 404: bundle not found
        HTTPException 500: database error
    """
    try:
        result: PriceValidation = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )
        
        # C-059: evidence logged by engine.validate_price() internally
        logger.info("Price validation: outcome=%s agent_type=%s bundle_tier=%s",
                   result.outcome, request.agent_type, request.bundle_tier)
        
        if result.outcome == "REJECTED":
            # Return 422 with validation error details
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=ValidationErrorResponse(
                    detail="Price below constitutional margin floor",
                    outcome="REJECTED",
                    cost_floor_paise=result.cost_floor_paise,
                    minimum_compliant_price_paise=result.minimum_compliant_price_paise,
                    proposed_price_paise=result.proposed_price_paise,
                ).model_dump(),
            )
        
        # Return 200 on APPROVED
        return result
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Validation failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Price validation error", exc_info=True, extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price validation failed",
        ) from e


@router.post("/derive", response_model=PriceDeriveResponse)
async def derive_price(
    request: PriceDeriveRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> PriceDeriveResponse:
    """
    POST /pricing/derive
    
    Derive a compliant price for a bundle given cost floor and target margin (C-089).
    Uses margin-on-revenue formula: derived_price = floor / (1 - margin/100)
    
    Request body:
        {
          "agent_type": "DMA",
          "bundle_tier": "STARTER",
          "target_margin_pct": 25.0
        }
    
    Returns (200):
        {
          "agent_type": "DMA",
          "bundle_tier": "STARTER",
          "cost_floor_paise": 40000,
          "target_margin_pct": 25.0,
          "derived_price_paise": 53333,
          "effective_margin_pct": 25.0
        }
    
    If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.
    
    Raises:
        HTTPException 404: bundle not found
        HTTPException 500: database error
    """
    try:
        cost_floor = await engine.cost_floor(request.agent_type, request.bundle_tier)
        
        # Use minimum_margin_pct if target_margin_pct is None
        margin_pct = request.target_margin_pct
        if margin_pct is None:
            margin_pct = await engine.get_minimum_margin_pct(request.agent_type, request.bundle_tier)
        
        derived_price = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=margin_pct,
        )
        
        # Calculate effective margin: (price - cost) / price * 100
        effective_margin = ((derived_price - cost_floor) / derived_price * 100) if derived_price > 0 else 0.0
        
        logger.info("Price derived: agent_type=%s bundle_tier=%s derived_price_paise=%d margin_pct=%.2f",
                   request.agent_type, request.bundle_tier, derived_price, effective_margin)
        
        return PriceDeriveResponse(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            cost_floor_paise=cost_floor,
            target_margin_pct=request.target_margin_pct,
            derived_price_paise=derived_price,
            effective_margin_pct=effective_margin,
        )
    
    except ValueError as e:
        logger.warning("Price derivation failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Price derivation error", exc_info=True, extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price derivation failed",
        ) from e