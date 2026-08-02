# Implements: WC027 — WC027-01b
# constitutional_basis: C-059, C-082
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

@router.get('/thread-catalog')
def get_thread_catalog() -> dict:
    """GET /thread-catalog"""
    # [WAOOAW_LOGIC_FILLER_START]
    # Thread catalog data is served by markup.thread_catalog router at /catalog.
    # This endpoint is a convenience alias — delegating to the same data layer.
    from markup.thread_catalog import get_catalog_data
    return get_catalog_data()
    # [WAOOAW_LOGIC_FILLER_END]

@router.get('/bundle-cost-floor/{agent_type}/{bundle_tier}')
def get_bundle_cost_floor_agent_type_bundle_tier(agent_type: str, bundle_tier: str) -> dict:
    """GET /bundle-cost-floor/{agent_type}/{bundle_tier}"""
    # [WAOOAW_LOGIC_FILLER_START]
    from markup.bundle_engine import BundleEngine
    from database import get_db_session
    with get_db_session() as db:
        engine = BundleEngine(db)
        try:
            cost_floor = engine.cost_floor(agent_type, bundle_tier)
        except ValueError:
            raise HTTPException(status_code=404, detail="Bundle profile not found")
    return {"agent_type": agent_type, "bundle_tier": bundle_tier, "cost_floor_paise": cost_floor}
    # [WAOOAW_LOGIC_FILLER_END]

@router.post('/validate')
def post_validate(validation_request: dict) -> dict:
    """POST /validate"""
    # [WAOOAW_LOGIC_FILLER_START]
    from markup.bundle_engine import BundleEngine
    from markup.models import PriceValidationRequest as _Req
    from database import get_db_session
    req = _Req(**validation_request)
    with get_db_session() as db:
        engine = BundleEngine(db)
        result = engine.validate_price(req.agent_type, req.bundle_tier, req.proposed_price_paise)
    if result.outcome == "REJECTED":
        raise HTTPException(
            status_code=422,
            detail={
                "outcome": result.outcome,
                "minimum_compliant_price_paise": result.minimum_compliant_price_paise,
                "cost_floor_paise": result.cost_floor_paise,
            },
        )
    return {"outcome": result.outcome, "cost_floor_paise": result.cost_floor_paise}
    # [WAOOAW_LOGIC_FILLER_END]

@router.post('/derive')
def post_derive(derive_request: dict) -> dict:
    """POST /derive"""
    # [WAOOAW_LOGIC_FILLER_START]
    from markup.bundle_engine import BundleEngine
    from markup.models import PriceDeriveRequest as _Req
    from database import get_db_session
    req = _Req(**derive_request)
    with get_db_session() as db:
        engine = BundleEngine(db)
        derived_price = engine.derive_price(req.agent_type, req.bundle_tier, req.target_margin_pct)
    return {"agent_type": req.agent_type, "bundle_tier": req.bundle_tier, "derived_price_paise": derived_price}
    # [WAOOAW_LOGIC_FILLER_END]

# NOTE: This router is mounted by src/billing-engine/main.py:
#   from markup.router import router as pricing_router
#   app.include_router(pricing_router, prefix="/pricing", tags=["pricing"])
