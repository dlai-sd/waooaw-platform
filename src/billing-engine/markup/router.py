# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-01b
# constitutional_basis: C-023, C-059, C-063, C-088, C-089
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing_engine.markup.bundle_engine import BundleEngine
from src.billing_engine.markup.models import (
    PriceDeriveRequest,
    PriceValidation,
    PriceValidationRequest,
    ThreadCatalogResponse,
)
from src.billing_engine.markup.thread_catalog import ThreadCatalogService
from src.billing_engine.skeleton.wbe_interfaces import IMarkupEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


async def get_bundle_engine(session: AsyncSession) -> IMarkupEngine:
    """Dependency: inject BundleEngine with DB session."""
    return BundleEngine(session=session)


async def get_thread_catalog_service(session: AsyncSession) -> ThreadCatalogService:
    """Dependency: inject ThreadCatalogService with DB session."""
    return ThreadCatalogService(session=session)


@router.get("/thread-catalog", response_model=list[ThreadCatalogResponse])
async def get_thread_catalog(
    service: Annotated[ThreadCatalogService, Depends(get_thread_catalog_service)],
) -> list[ThreadCatalogResponse]:
    """
    GET /pricing/thread-catalog
    Delegates to existing ThreadCatalogService.
    Returns thread catalog with agent_type, bundle_tier, cost, ration metadata.
    Constitutional: C-091 (Thread Catalog).
    """
    logger.info("Fetching thread catalog")
    try:
        catalog = await service.list_all()
        logger.info("Thread catalog fetched: %d entries", len(catalog))
        return catalog
    except Exception as exc:
        logger.error(
            "Thread catalog fetch failed",
            exc_info=True,
            extra={"operation": "get_thread_catalog"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch thread catalog",
        ) from exc


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=dict,
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: Annotated[IMarkupEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    Returns the constitutional cost floor (paise) for a given agent_type + bundle_tier.
    Reads from bundle_profiles.cost_floor_paise (not recomputed).
    Constitutional: C-089 (Margin Floor).
    """
    logger.info(
        "Fetching cost floor: agent_type=%s, bundle_tier=%s",
        agent_type,
        bundle_tier,
    )
    try:
        cost_floor_paise = await engine.derive_bundle_cost_floor(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
        )
        logger.info(
            "Cost floor computed: agent_type=%s, bundle_tier=%s, floor=%d paise",
            agent_type,
            bundle_tier,
            cost_floor_paise,
        )
        return {
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "cost_floor_paise": cost_floor_paise,
        }
    except ValueError as exc:
        logger.warning(
            "Cost floor lookup failed: agent_type=%s, bundle_tier=%s",
            agent_type,
            bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle profile not found",
        ) from exc
    except Exception as exc:
        logger.error(
            "Cost floor computation failed",
            exc_info=True,
            extra={
                "operation": "get_bundle_cost_floor",
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute cost floor",
        ) from exc


@router.post(
    "/validate",
    response_model=PriceValidation,
    status_code=status.HTTP_200_OK,
)
async def validate_price(
    request: PriceValidationRequest,
    engine: Annotated[IMarkupEngine, Depends(get_bundle_engine)],
) -> PriceValidation:
    """
    POST /pricing/validate
    Validates a proposed price against constitutional margin floor (C-089).
    Writes to pricing_floor_log on BOTH APPROVED and REJECTED (C-059, C-090).
    On violation: returns HTTP 422 with minimum_compliant_price_paise in body.

    Constitutional: C-089 (Margin Floor — never price below cost), C-059 (Audit),
    C-090 (Logging obligation).
    """
    logger.info(
        "Price validation requested: agent_type=%s, bundle_tier=%s, proposed=%d paise",
        request.agent_type,
        request.bundle_tier,
        request.proposed_price_paise,
    )
    try:
        validation_result = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )
        if validation_result.outcome == "REJECTED":
            logger.warning(
                "Price validation rejected: agent_type=%s, bundle_tier=%s, proposed=%d, minimum_compliant=%d",
                request.agent_type,
                request.bundle_tier,
                request.proposed_price_paise,
                validation_result.minimum_compliant_price_paise,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "reason": "Below constitutional margin floor",
                    "minimum_compliant_price_paise": validation_result.minimum_compliant_price_paise,
                    "cost_floor_paise": validation_result.cost_floor_paise,
                },
            )
        logger.info(
            "Price validation approved: agent_type=%s, bundle_tier=%s, proposed=%d",
            request.agent_type,
            request.bundle_tier,
            request.proposed_price_paise,
        )
        return validation_result
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "Price validation failed: bundle profile not found",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle profile not found",
        ) from exc
    except Exception as exc:
        logger.error(
            "Price validation error",
            exc_info=True,
            extra={
                "operation": "validate_price",
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from exc


@router.post("/derive", response_model=dict)
async def derive_price(
    request: PriceDeriveRequest,
    engine: Annotated[IMarkupEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    POST /pricing/derive
    Derives a compliant price for a given agent_type + bundle_tier.
    Uses margin-on-revenue formula: floor / (1 - margin/100).
    Falls back to bundle_profiles.minimum_margin_pct if target_margin_pct is None.

    Constitutional: C-089 (Margin Floor), C-090 (Pricing transparency).
    """
    logger.info(
        "Price derivation requested: agent_type=%s, bundle_tier=%s, target_margin=%s%%",
        request.agent_type,
        request.bundle_tier,
        request.target_margin_pct,
    )
    try:
        derived_price_paise = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )
        logger.info(
            "Price derived: agent_type=%s, bundle_tier=%s, derived=%d paise",
            request.agent_type,
            request.bundle_tier,
            derived_price_paise,
        )
        return {
            "agent_type": request.agent_type,
            "bundle_tier": request.bundle_tier,
            "derived_price_paise": derived_price_paise,
            "target_margin_pct": request.target_margin_pct,
        }
    except ValueError as exc:
        logger.warning(
            "Price derivation failed: bundle profile not found",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle profile not found",
        ) from exc
    except Exception as exc:
        logger.error(
            "Price derivation error",
            exc_info=True,
            extra={
                "operation": "derive_price",
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from exc