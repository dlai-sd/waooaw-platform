# Implements: WC027-01b — FastAPI router for pricing endpoints
# constitutional_basis: C-023, C-059, C-082, C-088, C-089, C-090, C-091
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database import get_db
from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    ThreadEntry,
)
from markup import thread_catalog
from ce_validator import CE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


async def get_bundle_engine(db: AsyncSession = Depends(get_db)) -> BundleEngine:
    """Dependency to provide BundleEngine instance"""
    return BundleEngine(db=db)


@router.get("/thread-catalog", response_model=list[ThreadEntry])
async def get_thread_catalog() -> list[ThreadEntry]:
    """
    GET /thread-catalog
    Delegates to thread_catalog module to return thread definitions.
    C-091: ThreadCatalogService delegation.
    """
    await CE.ValidateAction("pricing.thread_catalog.read")
    catalog = thread_catalog.get_catalog()
    return catalog


@router.get("/bundle-cost-floor/{agent_type}/{bundle_tier}", response_model=dict[str, int])
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> dict[str, int]:
    """
    GET /bundle-cost-floor/{agent_type}/{bundle_tier}
    Returns cost floor in paise for given agent type and bundle tier.
    """
    await CE.ValidateAction("pricing.cost_floor.read")
    cost_floor_paise = await engine.cost_floor(agent_type=agent_type, bundle_tier=bundle_tier)
    return {"cost_floor_paise": cost_floor_paise}


@router.post("/validate", response_model=PriceValidation, status_code=200)
async def validate_price(
    request: PriceValidationRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> PriceValidation:
    """
    POST /validate
    Validates proposed price against margin floor.
    C-023: ValidateAction before execution.
    C-088: Check billing_profiles.status == FOUNDER_AUTHORIZED.
    C-089: Enforce constitutional minimum margin floor.
    Returns 422 with minimum_compliant_price_paise on violation (C-038).
    """
    await CE.ValidateAction("pricing.validate.write")
    
    result = await engine.validate_price(
        agent_type=request.agent_type,
        bundle_tier=request.bundle_tier,
        proposed_price_paise=request.proposed_price_paise,
    )
    
    if result.outcome == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "outcome": result.outcome,
                "cost_floor_paise": result.cost_floor_paise,
                "minimum_compliant_price_paise": result.minimum_compliant_price_paise,
                "proposed_price_paise": result.proposed_price_paise,
            },
        )
    
    return result


@router.post("/derive", response_model=dict[str, int])
async def derive_price(
    request: PriceDeriveRequest,
    engine: BundleEngine = Depends(get_bundle_engine),
) -> dict[str, int]:
    """
    POST /derive
    Derives compliant price using margin-on-revenue formula.
    C-023: ValidateAction before execution.
    """
    await CE.ValidateAction("pricing.derive.read")
    
    derived_price_paise = await engine.derive_price(
        agent_type=request.agent_type,
        bundle_tier=request.bundle_tier,
        target_margin_pct=request.target_margin_pct,
    )
    
    return {"derived_price_paise": derived_price_paise}