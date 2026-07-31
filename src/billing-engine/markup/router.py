# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceDeriveRequest,
    PriceValidation,
    PriceValidationRequest,
    ThreadCatalogResponse,
)
from markup.thread_catalog import ThreadCatalogService
from shared.db import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


async def get_bundle_engine(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BundleEngine:
    """Dependency: inject BundleEngine with DB session."""
    return BundleEngine(session)


async def get_thread_catalog_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ThreadCatalogService:
    """Dependency: inject ThreadCatalogService with DB session."""
    return ThreadCatalogService(session)


@router.get(
    "/thread-catalog",
    response_model=ThreadCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve thread catalog",
    description="Returns all active thread catalog entries with pricing metadata.",
)
async def get_thread_catalog(
    service: Annotated[ThreadCatalogService, Depends(get_thread_catalog_service)],
) -> ThreadCatalogResponse:
    """
    GET /pricing/thread-catalog
    C-091: Thread Catalog Sovereignty — returns authoritative thread definitions.
    Returns cached catalog from Redis if available; falls back to DB.
    """
    try:
        catalog = await service.get_catalog()
        logger.info("thread_catalog_retrieved count=%s", len(catalog.threads))
        return catalog
    except Exception as exc:
        logger.error(
            "thread_catalog_retrieval_failed",
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread catalog",
        ) from exc


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get bundle cost floor",
    description="Returns the constitutional cost floor for a given agent type and bundle tier.",
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    C-089: Margin Floor — returns cost_floor_paise from bundle_profiles.
    """
    try:
        cost_floor_paise = await engine.cost_floor(agent_type, bundle_tier)
        logger.info(
            "cost_floor_retrieved agent_type=%s bundle_tier=%s cost_floor_paise=%s",
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
            "cost_floor_not_found agent_type=%s bundle_tier=%s",
            agent_type,
            bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle not found: {agent_type}/{bundle_tier}",
        ) from exc
    except Exception as exc:
        logger.error(
            "cost_floor_retrieval_failed agent_type=%s bundle_tier=%s",
            agent_type,
            bundle_tier,
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from exc


@router.post(
    "/validate",
    response_model=PriceValidation,
    status_code=status.HTTP_200_OK,
    summary="Validate proposed price",
    description=(
        "Validates a proposed price against constitutional margin floor. "
        "Returns 200 (APPROVED) or 422 (REJECTED with compliance price)."
    ),
)
async def validate_price(
    request: PriceValidationRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> PriceValidation:
    """
    POST /pricing/validate
    C-089: Margin Floor — validates price >= minimum_compliant_price.
    C-059: Traceability — writes to pricing_floor_log on APPROVED and REJECTED.
    C-038: 422 response includes minimum_compliant_price_paise on violation.

    Request body:
      {
        "agent_type": "dma",
        "bundle_tier": "pro",
        "proposed_price_paise": 50000
      }

    Response 200 (APPROVED):
      {
        "outcome": "APPROVED",
        "agent_type": "dma",
        "bundle_tier": "pro",
        "proposed_price_paise": 50000,
        "cost_floor_paise": 30000,
        "minimum_compliant_price_paise": 37500,
        "below_floor": false
      }

    Response 422 (REJECTED):
      {
        "outcome": "REJECTED",
        "agent_type": "dma",
        "bundle_tier": "pro",
        "proposed_price_paise": 30000,
        "cost_floor_paise": 30000,
        "minimum_compliant_price_paise": 37500,
        "below_floor": true,
        "detail": "Price below constitutional margin floor"
      }
    """
    try:
        validation = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )

        logger.info(
            "price_validation_completed outcome=%s agent_type=%s bundle_tier=%s proposed_paise=%s compliant_paise=%s",
            validation.outcome,
            request.agent_type,
            request.bundle_tier,
            request.proposed_price_paise,
            validation.minimum_compliant_price_paise,
        )

        if validation.below_floor:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Price below constitutional margin floor",
                headers={"X-Minimum-Compliant-Price": str(validation.minimum_compliant_price_paise)},
            )

        return validation
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "price_validation_bundle_not_found agent_type=%s bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle not found: {request.agent_type}/{request.bundle_tier}",
        ) from exc
    except Exception as exc:
        logger.error(
            "price_validation_failed agent_type=%s bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from exc


@router.post(
    "/derive",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Derive compliant price",
    description=(
        "Derives a price for a given agent type and bundle tier, "
        "applying optional target margin or using bundle default margin."
    ),
)
async def derive_price(
    request: PriceDeriveRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict:
    """
    POST /pricing/derive
    C-089: Margin Floor — derives price using margin-on-revenue formula.
    C-059: Traceability — all pricing decisions are logged.

    Request body (target_margin_pct optional):
      {
        "agent_type": "dma",
        "bundle_tier": "pro",
        "target_margin_pct": 25.5
      }

    Response 200:
      {
        "agent_type": "dma",
        "bundle_tier": "pro",
        "cost_floor_paise": 30000,
        "applied_margin_pct": 25.5,
        "derived_price_paise": 40268
      }
    """
    try:
        derived_price_paise = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )

        cost_floor_paise = await engine.cost_floor(
            request.agent_type,
            request.bundle_tier,
        )

        applied_margin_pct = request.target_margin_pct
        if applied_margin_pct is None:
            bundle_profile = await engine._get_bundle_profile(
                request.agent_type,
                request.bundle_tier,
            )
            applied_margin_pct = bundle_profile.minimum_margin_pct

        logger.info(
            "price_derived agent_type=%s bundle_tier=%s cost_floor_paise=%s margin_pct=%s derived_paise=%s",
            request.agent_type,
            request.bundle_tier,
            cost_floor_paise,
            applied_margin_pct,
            derived_price_paise,
        )

        return {
            "agent_type": request.agent_type,
            "bundle_tier": request.bundle_tier,
            "cost_floor_paise": cost_floor_paise,
            "applied_margin_pct": applied_margin_pct,
            "derived_price_paise": derived_price_paise,
        }
    except ValueError as exc:
        logger.warning(
            "price_derivation_bundle_not_found agent_type=%s bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle not found: {request.agent_type}/{request.bundle_tier}",
        ) from exc
    except Exception as exc:
        logger.error(
            "price_derivation_failed agent_type=%s bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from exc