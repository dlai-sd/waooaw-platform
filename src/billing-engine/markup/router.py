# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-049, C-051, C-059, C-089, C-091

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends, status

from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    PriceDerivationResponse,
)
from markup.thread_catalog import _load_from_db, ThreadCatalogEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


# Dependency: instantiate BundleEngine
async def get_bundle_engine() -> BundleEngine:
    """Dependency injection for BundleEngine."""
    return BundleEngine()


@router.get(
    "/thread-catalog",
    response_model=list[dict[str, Any]],
    summary="Get thread catalog",
    description="Retrieve the full thread catalog with cost and markup details.",
)
async def get_thread_catalog() -> list[dict[str, Any]]:
    """
    GET /pricing/thread-catalog
    Delegates to ThreadCatalogService; returns thread definitions.
    C-091: Thread Catalog Sovereignty.
    """
    try:
        entries: list[ThreadCatalogEntry] = await _load_from_db()
        return [
            {
                "thread_id": entry.thread_id,
                "display_name": entry.display_name,
                "provider": entry.provider,
                "unit_description": entry.unit_description,
                "raw_cost_inr_paise": entry.raw_cost_inr_paise,
                "total_markup_pct": entry.total_markup_pct,
                "marked_up_cost_paise": entry.marked_up_cost_paise,
                "is_platform_thread": entry.is_platform_thread,
                "applicable_agents": entry.applicable_agents,
                "status": entry.status,
            }
            for entry in entries
        ]
    except Exception as e:
        logger.error(
            "Failed to load thread catalog",
            exc_info=True,
            extra={"endpoint": "get_thread_catalog"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load thread catalog",
        ) from e


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=dict[str, Any],
    summary="Get bundle cost floor",
    description="Retrieve the cost floor for a given agent type and bundle tier.",
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> dict[str, Any]:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    Returns the cost floor in paise.
    C-089: Margin Floor — reads from bundle_profiles.cost_floor_paise.
    """
    try:
        cost_floor_paise: int = engine.cost_floor(agent_type, bundle_tier)
        return {
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "cost_floor_paise": cost_floor_paise,
        }
    except ValueError as e:
        logger.error(
            "Bundle tier or agent type not found",
            exc_info=True,
            extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Failed to retrieve bundle cost floor",
            exc_info=True,
            extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bundle cost floor",
        ) from e


@router.post(
    "/validate",
    response_model=PriceValidation,
    summary="Validate price against constitutional floor",
    description="Validate a proposed price against the minimum compliant price derived from cost floor and margin floor. Returns 422 with minimum_compliant_price_paise on C-089 violation.",
    responses={
        200: {
            "description": "Price validation approved",
            "model": PriceValidation,
        },
        422: {
            "description": "Price below constitutional floor — includes minimum_compliant_price_paise",
            "model": PriceValidation,
        },
    },
)
async def validate_price(
    request: PriceValidationRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> PriceValidation:
    """
    POST /pricing/validate
    Validate proposed_price_paise against C-089 margin floor.
    
    C-089: validate_price() MUST enforce constitutional minimum margin floor;
           return PriceValidation with below_floor=True on violation;
           log to institutional.pricing_floor_log regardless (C-059).
    
    C-038: HTTP 422 body includes minimum_compliant_price_paise on C-089 floor violation.
    """
    try:
        validation_result: PriceValidation = engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )

        # C-038: Return 422 on below-floor violation
        if not validation_result.approved:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "outcome": validation_result.outcome,
                    "cost_floor_paise": validation_result.cost_floor_paise,
                    "minimum_compliant_price_paise": validation_result.minimum_compliant_price_paise,
                    "proposed_price_paise": validation_result.proposed_price_paise,
                    "message": "Price is below constitutional margin floor",
                },
            )

        return validation_result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            "Invalid bundle tier or agent type",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Price validation failed",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "proposed_price_paise": request.proposed_price_paise,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price validation failed",
        ) from e


@router.post(
    "/derive",
    response_model=PriceDerivationResponse,
    summary="Derive compliant price from cost floor and target margin",
    description="Derive a pricing recommendation using margin-on-revenue formula: price = cost_floor / (1 - margin_pct/100). Uses bundle_profiles.minimum_margin_pct if target_margin_pct is omitted.",
)
async def derive_price(
    request: PriceDeriveRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> PriceDerivationResponse:
    """
    POST /pricing/derive
    Derive price from cost floor and target margin using margin-on-revenue formula.
    
    C-089: Uses minimum_margin_pct from bundle_profiles if target_margin_pct not provided.
    Formula: derived_price_paise = cost_floor / (1 - margin_pct / 100)
    """
    try:
        derived_price_paise: int = engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )

        return PriceDerivationResponse(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
            derived_price_paise=derived_price_paise,
        )
    except ValueError as e:
        logger.error(
            "Invalid bundle tier or agent type",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Price derivation failed",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "target_margin_pct": request.target_margin_pct,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price derivation failed",
        ) from e