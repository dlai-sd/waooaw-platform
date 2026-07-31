# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-02
# constitutional_basis: C-023, C-059, C-063, C-088, C-089
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from billing_engine.config import Settings
from billing_engine.db import get_db_session
from billing_engine.markup.engine import BundleEngine
from billing_engine.markup.thread_catalog import ThreadCatalogService
from billing_engine.pricing.models import (
    BucketBalance,
    PacingMode,
    PriceDeriveRequest,
    PriceValidation,
    PriceValidationRequest,
    ThreadEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


async def get_bundle_engine(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends()],
) -> BundleEngine:
    """Dependency: inject BundleEngine with DB session."""
    return BundleEngine(session, settings, logger)


async def get_thread_catalog_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ThreadCatalogService:
    """Dependency: inject ThreadCatalogService with DB session."""
    return ThreadCatalogService(session, logger)


@router.get("/thread-catalog")
async def get_thread_catalog(
    catalog_svc: Annotated[ThreadCatalogService, Depends(get_thread_catalog_service)],
) -> list[ThreadEntry]:
    """
    GET /pricing/thread-catalog
    
    Returns all thread catalog entries (agent types × bundle tiers).
    Constitutional: C-091 (Thread Catalog structure).
    """
    try:
        entries = await catalog_svc.get_all_threads()
        logger.info("thread_catalog_retrieved entries_count=%d", len(entries))
        return entries
    except (ValueError, KeyError) as exc:
        logger.error(
            "thread_catalog_retrieval_failed",
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Thread catalog retrieval failed",
        ) from exc


@router.get("/bundle-cost-floor/{agent_type}/{bundle_tier}")
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict[str, int]:
    """
    GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
    
    Reads bundle_profiles.cost_floor_paise (no recomputation).
    Returns: {"cost_floor_paise": int}
    Raises: 404 if bundle not found.
    Constitutional: C-089 (Margin Floor).
    """
    try:
        cost_floor = await engine.derive_bundle_cost_floor(agent_type, bundle_tier)
        logger.info(
            "bundle_cost_floor_retrieved agent_type=%s bundle_tier=%s cost_floor_paise=%d",
            agent_type,
            bundle_tier,
            cost_floor,
        )
        return {"cost_floor_paise": cost_floor}
    except ValueError as exc:
        logger.warning(
            "bundle_not_found agent_type=%s bundle_tier=%s",
            agent_type,
            bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle profile not found",
        ) from exc
    except (KeyError, RuntimeError) as exc:
        logger.error(
            "bundle_cost_floor_retrieval_failed",
            exc_info=True,
            extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cost floor retrieval failed",
        ) from exc


@router.post("/validate")
async def validate_price(
    request: PriceValidationRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> PriceValidation:
    """
    POST /pricing/validate
    
    Validates proposed price against C-089 margin floor.
    Formula: minimum_compliant_price = cost_floor / (1 - margin/100)
    
    Returns 200 with outcome=APPROVED if proposed_price >= minimum_compliant_price.
    Returns 422 with outcome=REJECTED if below floor (includes minimum_compliant_price_paise).
    
    Constitutional: C-059 (audit log), C-089 (margin floor), C-063 (no PII logging).
    """
    try:
        validation = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )

        if validation.outcome == "APPROVED":
            logger.info(
                "price_validation_approved agent_type=%s bundle_tier=%s",
                request.agent_type,
                request.bundle_tier,
            )
            return validation

        # outcome == "REJECTED" — return 422 with minimum_compliant_price
        logger.warning(
            "price_validation_rejected agent_type=%s bundle_tier=%s proposed_paise=%d minimum_compliant_paise=%d",
            request.agent_type,
            request.bundle_tier,
            request.proposed_price_paise,
            validation.minimum_compliant_price_paise,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "outcome": validation.outcome,
                "cost_floor_paise": validation.cost_floor_paise,
                "minimum_compliant_price_paise": validation.minimum_compliant_price_paise,
                "constitutional_minimum_margin_pct": validation.constitutional_minimum_margin_pct,
                "message": "Proposed price below constitutional minimum margin floor",
            },
        )

    except ValueError as exc:
        logger.warning(
            "bundle_not_found_on_validate agent_type=%s bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle profile not found",
        ) from exc
    except (KeyError, RuntimeError) as exc:
        logger.error(
            "price_validation_failed",
            exc_info=True,
            extra={"agent_type": request.agent_type, "bundle_tier": request.bundle_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price validation failed",
        ) from exc


@router.post("/derive")
async def derive_price(
    request: PriceDeriveRequest,
    engine: Annotated[BundleEngine, Depends(get_bundle_engine)],
) -> dict[str, int]:
    """
    POST /pricing/derive
    
    Derives compliant price using margin-on-revenue formula:
    derived_price = cost_floor / (1 - margin/100)
    
    If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.
    Returns: {"derived_price_paise": int, "cost_floor_paise": int, "margin_pct": int}
    Constitutional: C-089 (Margin Floor).
    """
    try:
        derived_price = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )
        cost_floor = await engine.derive_bundle_cost_floor(
            request.agent_type, request.bundle_tier
        )
        margin_pct = (
            request.target_margin_pct
            if request.target_margin_pct is not None
            else await engine.get_minimum_margin(
                request.agent_type, request.bundle_tier
            )
        )

        logger.info(
            "price_derived agent_type=%s bundle_tier=%s derived_paise=%d margin_pct=%d",
            request.agent_type,
            request.bundle_tier,
            derived_price,
            margin_pct,
        )
        return {
            "derived_price_paise": derived_price,
            "cost_floor_paise": cost_floor,
            "margin_pct": margin_pct,
        }

    except ValueError as exc:
        logger.warning(
            "bundle_not_found_on_derive agent_type=%s bundle_tier=%s",
            request.agent_type,
            request.bundle_tier,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle profile not found",
        ) from exc
    except (KeyError, RuntimeError, ZeroDivisionError) as exc:
        logger.error(
            "price_derivation_failed",
            exc_info=True,
            extra={"agent_type": request.agent_type, "bundle_tier": request.bundle_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Price derivation failed",
        ) from exc