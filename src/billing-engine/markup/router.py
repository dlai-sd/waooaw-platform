# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059, C-063

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, status

from bundle_engine import BundleEngine
from models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
)
from thread_catalog import ThreadCatalogService

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Dependencies ─────────────────────────────────────────────────────────────


def get_bundle_engine() -> BundleEngine:
    """
    Dependency injection: BundleEngine instance.
    In production, this would be singleton-scoped via FastAPI lifespan.
    C-088: Billing Profile gate enforcement happens in BundleEngine.validate_price().
    """
    return BundleEngine()


def get_thread_catalog_service() -> ThreadCatalogService:
    """
    Dependency injection: ThreadCatalogService instance.
    C-091: Thread Catalog Sovereignty — delegates to existing service.
    """
    return ThreadCatalogService()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/thread-catalog", tags=["thread-catalog"])
async def get_thread_catalog(
    catalog_service: Annotated[ThreadCatalogService, Depends(get_thread_catalog_service)],
) -> dict:
    """
    GET /pricing/thread-catalog
    C-091: Returns full thread catalog (display names, providers, unit costs, markup).
    Delegates to ThreadCatalogService.fetch_catalog().
    """
    try:
        entries = await catalog_service.fetch_catalog()
        logger.info("thread_catalog retrieved; count=%d", len(entries))
        return {
            "status": "ok",
            "thread_count": len(entries),
            "entries": [
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
            ],
        }
    except Exception as e:
        logger.error("thread_catalog fetch failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch thread catalog",
        ) from e


@router.get("/bundle-cost-floor/{agent_type}/{bundle_tier}", tags=["markup-pricing"])
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    C-089: Returns the constitutional cost floor for this (agent_type, bundle_tier) pair.
    Reads from bundle_profiles.cost_floor_paise; does NOT recompute.
    """
    try:
        cost_floor_paise = await engine.cost_floor(agent_type, bundle_tier)
        logger.info(
            "cost_floor retrieved; agent_type=%s bundle_tier=%s cost_floor_paise=%d",
            agent_type,
            bundle_tier,
            cost_floor_paise,
        )
        return {
            "status": "ok",
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "cost_floor_paise": cost_floor_paise,
        }
    except ValueError as e:
        logger.error(
            "cost_floor lookup failed; agent_type=%s bundle_tier=%s",
            agent_type,
            bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle tier not found: {bundle_tier}",
        ) from e
    except Exception as e:
        logger.error("cost_floor endpoint error", exc_info=True, extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from e


@router.post("/validate", tags=["markup-pricing"], status_code=status.HTTP_200_OK)
async def validate_price(
    req: PriceValidationRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    POST /pricing/validate
    C-089: Validates proposed price against constitutional margin floor.
    C-038: Returns 422 Unprocessable Entity with minimum_compliant_price_paise on floor violation.
    C-059: Writes to institutional.pricing_floor_log regardless of APPROVED/REJECTED outcome.

    Request body:
      {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 5000
      }

    Response (APPROVED):
      {
        "status": "ok",
        "outcome": "APPROVED",
        "cost_floor_paise": 3000,
        "minimum_compliant_price_paise": 3600,
        "proposed_price_paise": 5000,
        "is_compliant": true
      }

    Response (REJECTED — 422):
      {
        "status": "error",
        "outcome": "REJECTED",
        "cost_floor_paise": 3000,
        "minimum_compliant_price_paise": 3600,
        "proposed_price_paise": 2500,
        "is_compliant": false,
        "detail": "Proposed price below constitutional margin floor"
      }
    """
    try:
        result: PriceValidation = await engine.validate_price(
            req.agent_type,
            req.bundle_tier,
            req.proposed_price_paise,
        )
        logger.info(
            "price validated; agent_type=%s bundle_tier=%s outcome=%s",
            req.agent_type,
            req.bundle_tier,
            result.outcome,
        )

        if result.outcome == "APPROVED":
            return {
                "status": "ok",
                "outcome": "APPROVED",
                "cost_floor_paise": result.cost_floor_paise,
                "minimum_compliant_price_paise": result.minimum_compliant_price_paise,
                "proposed_price_paise": result.proposed_price_paise,
                "is_compliant": True,
            }
        else:
            # outcome == "REJECTED"
            # C-038: 422 response body includes minimum_compliant_price_paise
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "error",
                    "outcome": "REJECTED",
                    "cost_floor_paise": result.cost_floor_paise,
                    "minimum_compliant_price_paise": result.minimum_compliant_price_paise,
                    "proposed_price_paise": result.proposed_price_paise,
                    "is_compliant": False,
                    "message": "Proposed price below constitutional margin floor",
                },
            )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            "price validation lookup failed; agent_type=%s bundle_tier=%s",
            req.agent_type,
            req.bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle tier not found: {req.bundle_tier}",
        ) from e
    except Exception as e:
        logger.error("validate_price endpoint error", exc_info=True, extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from e


@router.post("/derive", tags=["markup-pricing"], status_code=status.HTTP_200_OK)
async def derive_price(
    req: PriceDeriveRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    POST /pricing/derive
    C-089: Derives a compliant price given cost floor and (optional) target margin %.
    Uses margin-on-revenue formula: price = floor / (1 - margin_pct/100).
    If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

    Request body:
      {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "target_margin_pct": 25.0
      }

    Response:
      {
        "status": "ok",
        "cost_floor_paise": 3000,
        "target_margin_pct": 25.0,
        "derived_price_paise": 4000,
        "formula": "price = floor / (1 - margin/100)"
      }
    """
    try:
        derived_price_paise = await engine.derive_price(
            req.agent_type,
            req.bundle_tier,
            req.target_margin_pct,
        )
        cost_floor_paise = await engine.cost_floor(req.agent_type, req.bundle_tier)
        margin_pct = req.target_margin_pct if req.target_margin_pct is not None else 0.0

        logger.info(
            "price derived; agent_type=%s bundle_tier=%s derived_price_paise=%d",
            req.agent_type,
            req.bundle_tier,
            derived_price_paise,
        )
        return {
            "status": "ok",
            "cost_floor_paise": cost_floor_paise,
            "target_margin_pct": margin_pct,
            "derived_price_paise": derived_price_paise,
            "formula": "price = floor / (1 - margin/100)",
        }
    except ValueError as e:
        logger.error(
            "price derivation lookup failed; agent_type=%s bundle_tier=%s",
            req.agent_type,
            req.bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle tier not found: {req.bundle_tier}",
        ) from e
    except Exception as e:
        logger.error("derive_price endpoint error", exc_info=True, extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from e