# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059, C-063
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from markup.models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    ThreadCatalogResponse,
)
from markup.bundle_engine import BundleEngine
from markup.thread_catalog import ThreadCatalogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


# ── Dependency injection ─────────────────────────────────────────────────────

async def get_bundle_engine(session: AsyncSession = Depends(...)) -> BundleEngine:
    """Inject BundleEngine with database session."""
    return BundleEngine(session=session)


async def get_thread_catalog_service(
    session: AsyncSession = Depends(...),
) -> ThreadCatalogService:
    """Inject ThreadCatalogService with database session."""
    return ThreadCatalogService(session=session)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/thread-catalog",
    response_model=ThreadCatalogResponse,
    status_code=status.HTTP_200_OK,
)
async def get_thread_catalog(
    service: ThreadCatalogService = Depends(get_thread_catalog_service),
) -> ThreadCatalogResponse:
    """
    GET /pricing/thread-catalog
    
    Retrieve the current thread catalog (all active threads with unit costs and markup).
    Implements C-091 (Thread Catalog Sovereignty).
    
    Returns:
        ThreadCatalogResponse with list of ThreadEntry objects.
    """
    try:
        entries = await service.list_all()
        logger.info("thread_catalog retrieved, count=%d", len(entries))
        return ThreadCatalogResponse(threads=entries)
    except Exception as e:
        logger.error(
            "thread_catalog retrieval failed",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread catalog",
        ) from e


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=dict[str, int],
    status_code=status.HTTP_200_OK,
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> dict[str, int]:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    
    Retrieve the cost floor (in INR paise) for a given agent type and bundle tier.
    Implements C-089 (Margin Floor — never price below cost).
    
    Args:
        agent_type: e.g., 'DMA', 'RAG_ASSISTANT'
        bundle_tier: e.g., 'STARTER', 'PROFESSIONAL'
    
    Returns:
        dict with cost_floor_paise (int).
        
    Raises:
        HTTPException(404): if bundle tier not found.
        HTTPException(500): on unexpected error.
    """
    try:
        cost_floor: int = await engine.cost_floor(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
        )
        logger.info(
            "cost_floor retrieved, agent_type=%s, bundle_tier=%s, cost_floor_paise=%d",
            agent_type,
            bundle_tier,
            cost_floor,
        )
        return {"cost_floor_paise": cost_floor}
    except ValueError as e:
        logger.warning(
            "cost_floor lookup failed, agent_type=%s, bundle_tier=%s",
            agent_type,
            bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle tier not found: {agent_type}/{bundle_tier}",
        ) from e
    except Exception as e:
        logger.error(
            "cost_floor retrieval failed",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from e


@router.post(
    "/validate",
    response_model=PriceValidation,
    status_code=status.HTTP_200_OK,
)
async def validate_price(
    request: PriceValidationRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> PriceValidation:
    """
    POST /pricing/validate
    
    Validate a proposed price against the constitutional margin floor.
    Implements C-089 (Margin Floor enforcement), C-059 (audit logging).
    
    Request body:
        {
            "agent_type": "DMA",
            "bundle_tier": "PROFESSIONAL",
            "proposed_price_paise": 500000
        }
    
    Response on success (200):
        {
            "outcome": "APPROVED",
            "cost_floor_paise": 200000,
            "minimum_compliant_price_paise": 250000,
            "proposed_price_paise": 500000,
            "margin_pct": 100.0
        }
    
    Response on C-089 violation (422):
        {
            "outcome": "REJECTED",
            "cost_floor_paise": 200000,
            "minimum_compliant_price_paise": 250000,
            "proposed_price_paise": 50000,
            "margin_pct": -75.0
        }
        with detail: "Price below constitutional minimum margin floor"
    
    Raises:
        HTTPException(422) if proposed price violates C-089 minimum margin.
        HTTPException(404) if bundle tier not found.
        HTTPException(500) on unexpected error.
    """
    try:
        validation: PriceValidation = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )

        if validation.outcome == "APPROVED":
            logger.info(
                "price_validated, agent_type=%s, bundle_tier=%s, proposed=%d, "
                "minimum_compliant=%d, outcome=%s",
                request.agent_type,
                request.bundle_tier,
                request.proposed_price_paise,
                validation.minimum_compliant_price_paise,
                validation.outcome,
            )
            return validation

        # C-089 violation: rejected
        logger.warning(
            "price_validation_rejected, agent_type=%s, bundle_tier=%s, proposed=%d, "
            "minimum_compliant=%d, margin_pct=%s",
            request.agent_type,
            request.bundle_tier,
            request.proposed_price_paise,
            validation.minimum_compliant_price_paise,
            validation.margin_pct,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Price below constitutional minimum margin floor",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "price_validation lookup failed, agent_type=%s, bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle tier not found: {request.agent_type}/{request.bundle_tier}",
        ) from e
    except Exception as e:
        logger.error(
            "price_validation failed",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from e


@router.post(
    "/derive",
    response_model=dict[str, int | float],
    status_code=status.HTTP_200_OK,
)
async def derive_price(
    request: PriceDeriveRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> dict[str, int | float]:
    """
    POST /pricing/derive
    
    Derive a compliant price from cost floor and margin percentage.
    Implements C-089 (Margin Floor enforcement).
    
    Request body:
        {
            "agent_type": "DMA",
            "bundle_tier": "PROFESSIONAL",
            "target_margin_pct": 50.0
        }
    
    Response (200):
        {
            "cost_floor_paise": 200000,
            "target_margin_pct": 50.0,
            "derived_price_paise": 400000
        }
    
    Raises:
        HTTPException(404) if bundle tier not found.
        HTTPException(500) on unexpected error.
    """
    try:
        derived_price: int = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )
        cost_floor: int = await engine.cost_floor(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
        )
        logger.info(
            "price_derived, agent_type=%s, bundle_tier=%s, cost_floor=%d, "
            "target_margin=%s, derived_price=%d",
            request.agent_type,
            request.bundle_tier,
            cost_floor,
            request.target_margin_pct,
            derived_price,
        )
        return {
            "cost_floor_paise": cost_floor,
            "target_margin_pct": request.target_margin_pct,
            "derived_price_paise": derived_price,
        }
    except ValueError as e:
        logger.warning(
            "price_derive lookup failed, agent_type=%s, bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle tier not found: {request.agent_type}/{request.bundle_tier}",
        ) from e
    except Exception as e:
        logger.error(
            "price_derive failed",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from e