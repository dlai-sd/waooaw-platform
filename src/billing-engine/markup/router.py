# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-088, C-089, C-090, C-091, C-038, C-048, C-051
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceDeriveRequest,
    PriceValidationRequest,
    PriceValidation,
    ValidationOutcome,
)
from markup.thread_catalog import ThreadCatalogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])

# Service instances (initialized at startup)
_bundle_engine: BundleEngine | None = None
_thread_catalog_service: ThreadCatalogService | None = None


def _get_bundle_engine() -> BundleEngine:
    """Lazy-initialize BundleEngine singleton."""
    global _bundle_engine
    if _bundle_engine is None:
        _bundle_engine = BundleEngine()
    return _bundle_engine


def _get_thread_catalog_service() -> ThreadCatalogService:
    """Lazy-initialize ThreadCatalogService singleton."""
    global _thread_catalog_service
    if _thread_catalog_service is None:
        _thread_catalog_service = ThreadCatalogService()
    return _thread_catalog_service


@router.get("/thread-catalog")
async def get_thread_catalog() -> dict[str, Any]:
    """
    Delegates to ThreadCatalogService.
    C-091: Return thread definitions from institutional.thread_catalog.
    
    Returns:
        Dictionary with thread_catalog array containing thread entries.
    
    Raises:
        HTTPException: 500 if catalog fetch fails.
    """
    try:
        service = _get_thread_catalog_service()
        catalog = await service.get_full_catalog()
        logger.info("thread_catalog fetched: %d entries", len(catalog))
        return {
            "thread_catalog": [
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
                for entry in catalog
            ]
        }
    except Exception as exc:
        logger.error(
            "Failed to fetch thread catalog",
            exc_info=True,
            extra={"context": "get_thread_catalog"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch thread catalog",
        ) from exc


@router.get("/bundle-cost-floor/{agent_type}/{bundle_tier}")
async def get_bundle_cost_floor(agent_type: str, bundle_tier: str) -> dict[str, Any]:
    """
    C-089: Return cost_floor_paise from bundle_profiles.
    Reads from DB, does NOT recompute.
    
    Args:
        agent_type: Agent type identifier.
        bundle_tier: Bundle tier name.
    
    Returns:
        Dictionary with agent_type, bundle_tier, and cost_floor_paise.
    
    Raises:
        HTTPException: 404 if bundle profile not found, 500 on other errors.
    """
    try:
        engine = _get_bundle_engine()
        cost_floor = await engine.cost_floor(agent_type, bundle_tier)
        logger.info(
            "cost_floor retrieved: agent_type=%s, bundle_tier=%s, cost_floor_paise=%d",
            agent_type,
            bundle_tier,
            cost_floor,
        )
        return {
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "cost_floor_paise": cost_floor,
        }
    except ValueError as exc:
        logger.warning(
            "cost_floor not found: agent_type=%s, bundle_tier=%s",
            agent_type,
            bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle profile not found: {agent_type}/{bundle_tier}",
        ) from exc
    except Exception as exc:
        logger.error(
            "Failed to get cost floor",
            exc_info=True,
            extra={"context": f"{agent_type}/{bundle_tier}"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from exc


@router.post("/validate")
async def validate_price(req: PriceValidationRequest) -> PriceValidation:
    """
    C-089: Validate proposed_price_paise against constitutional margin floor.
    C-059: Write to pricing_floor_log on both APPROVED and REJECTED.
    C-088: Check billing_profiles.status == FOUNDER_AUTHORIZED.
    C-038: Return 422 with minimum_compliant_price_paise on floor violation.

    Args:
        req: PriceValidationRequest with agent_type, bundle_tier, proposed_price_paise.

    Returns:
        PriceValidation with outcome, cost_floor_paise, minimum_compliant_price_paise.

    Raises:
        HTTPException: 422 if below floor (includes minimum_compliant_price_paise),
                      500 on internal error.
    """
    try:
        engine = _get_bundle_engine()
        validation_result = await engine.validate_price(
            agent_type=req.agent_type,
            bundle_tier=req.bundle_tier,
            proposed_price_paise=req.proposed_price_paise,
        )

        if validation_result.outcome == ValidationOutcome.REJECTED:
            logger.warning(
                "price_validation REJECTED: agent_type=%s, bundle_tier=%s, proposed=%d, minimum_compliant=%d",
                req.agent_type,
                req.bundle_tier,
                req.proposed_price_paise,
                validation_result.minimum_compliant_price_paise,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Proposed price is below constitutional margin floor",
                headers={
                    "X-Minimum-Compliant-Price": str(
                        validation_result.minimum_compliant_price_paise
                    ),
                },
            )

        logger.info(
            "price_validation APPROVED: agent_type=%s, bundle_tier=%s, proposed=%d",
            req.agent_type,
            req.bundle_tier,
            req.proposed_price_paise,
        )
        return validation_result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to validate price",
            exc_info=True,
            extra={
                "context": f"{req.agent_type}/{req.bundle_tier}",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from exc


@router.post("/derive")
async def derive_price(req: PriceDeriveRequest) -> dict[str, Any]:
    """
    C-089: Derive compliant price using margin-on-revenue formula.
    Formula: floor / (1 - margin/100)
    Uses bundle_profiles.minimum_margin_pct if target_margin_pct not specified.

    Args:
        req: PriceDeriveRequest with agent_type, bundle_tier, optional target_margin_pct.

    Returns:
        Dictionary with agent_type, bundle_tier, target_margin_pct, derived_price_paise.

    Raises:
        HTTPException: 404 if bundle profile not found, 500 on other errors.
    """
    try:
        engine = _get_bundle_engine()
        derived_price = await engine.derive_price(
            agent_type=req.agent_type,
            bundle_tier=req.bundle_tier,
            target_margin_pct=req.target_margin_pct,
        )

        logger.info(
            "price_derivation complete: agent_type=%s, bundle_tier=%s, margin=%s, derived=%d",
            req.agent_type,
            req.bundle_tier,
            req.target_margin_pct or "default",
            derived_price,
        )
        return {
            "agent_type": req.agent_type,
            "bundle_tier": req.bundle_tier,
            "target_margin_pct": req.target_margin_pct,
            "derived_price_paise": derived_price,
        }

    except ValueError as exc:
        logger.warning(
            "price_derivation failed: agent_type=%s, bundle_tier=%s",
            req.agent_type,
            req.bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle profile not found: {req.agent_type}/{req.bundle_tier}",
        ) from exc
    except Exception as exc:
        logger.error(
            "Failed to derive price",
            exc_info=True,
            extra={
                "context": f"{req.agent_type}/{req.bundle_tier}",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from exc