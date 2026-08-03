# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone

router = APIRouter()


@router.get('/thread-catalog')
def get_thread_catalog() -> dict:
    """GET /thread-catalog"""
    # [WAOOAW_LOGIC_FILLER_START]
    catalog = [
        ThreadEntry(
            thread_id="standard-gpt4",
            agent_type="gpt4",
            bundle_tier="standard",
            cost_floor=0.02,
            markup_pct=15.0,
            active=True,
        ),
        ThreadEntry(
            thread_id="premium-claude",
            agent_type="claude",
            bundle_tier="premium",
            cost_floor=0.04,
            markup_pct=20.0,
            active=True,
        ),
    ]
    return {"threads": [t.model_dump() for t in catalog]}
    # [WAOOAW_LOGIC_FILLER_END]


@router.get('/bundle-cost-floor/{agent_type}/{bundle_tier}')
def get_bundle_cost_floor_agent_type_bundle_tier(agent_type: str, bundle_tier: str) -> dict:
    """GET /bundle-cost-floor/{agent_type}/{bundle_tier}"""
    # [WAOOAW_LOGIC_FILLER_START]
    cost_floors: dict[tuple[str, str], float] = {
        ("gpt4", "standard"): 0.02,
        ("gpt4", "premium"): 0.035,
        ("claude", "standard"): 0.025,
        ("claude", "premium"): 0.04,
        ("gpt35", "standard"): 0.005,
        ("gpt35", "premium"): 0.01,
    }
    key = (agent_type.lower(), bundle_tier.lower())
    if key not in cost_floors:
        raise HTTPException(
            status_code=404,
            detail=f"No cost floor found for agent_type={agent_type}, bundle_tier={bundle_tier}",
        )
    return {
        "agent_type": agent_type,
        "bundle_tier": bundle_tier,
        "cost_floor": cost_floors[key],
    }
    # [WAOOAW_LOGIC_FILLER_END]


@router.post('/validate')
def post_validate(profile: BundleProfile) -> dict:
    """POST /validate"""
    # [WAOOAW_LOGIC_FILLER_START]
    errors: list[str] = []
    if profile.markup_pct < 0:
        errors.append("markup_pct must be non-negative")
    if profile.markup_pct > 200:
        errors.append("markup_pct must not exceed 200")
    if profile.cost_floor < 0:
        errors.append("cost_floor must be non-negative")
    if not profile.bundle_tier:
        errors.append("bundle_tier is required")
    if not profile.agent_type:
        errors.append("agent_type is required")
    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "errors": []}
    # [WAOOAW_LOGIC_FILLER_END]


@router.post('/derive')
def post_derive(profile: BundleProfile) -> dict:
    """POST /derive"""
    # [WAOOAW_LOGIC_FILLER_START]
    derived_price = profile.cost_floor * (1 + profile.markup_pct / 100.0)
    return {
        "agent_type": profile.agent_type,
        "bundle_tier": profile.bundle_tier,
        "cost_floor": profile.cost_floor,
        "markup_pct": profile.markup_pct,
        "derived_price": round(derived_price, 6),
        "derived_at": datetime.now(timezone.utc).isoformat(),
    }
    # [WAOOAW_LOGIC_FILLER_END]


@router.post('/pricing/validate')
def post_pricing_validate(profile: BundleProfile) -> dict:
    """POST /pricing/validate"""
    # [WAOOAW_LOGIC_FILLER_START]
    errors: list[str] = []
    if profile.markup_pct < 0:
        errors.append("markup_pct must be non-negative")
    if profile.markup_pct > 200:
        errors.append("markup_pct must not exceed 200")
    if profile.cost_floor < 0:
        errors.append("cost_floor must be non-negative")
    if not profile.bundle_tier:
        errors.append("bundle_tier is required")
    if not profile.agent_type:
        errors.append("agent_type is required")
    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "errors": []}
    # [WAOOAW_LOGIC_FILLER_END]


@router.get('/pricing/thread-catalog')
def get_pricing_thread_catalog() -> dict:
    """GET /pricing/thread-catalog"""
    # [WAOOAW_LOGIC_FILLER_START]
    catalog = [
        ThreadEntry(
            thread_id="standard-gpt4",
            agent_type="gpt4",
            bundle_tier="standard",
            cost_floor=0.02,
            markup_pct=15.0,
            active=True,
        ),
        ThreadEntry(
            thread_id="premium-claude",
            agent_type="claude",
            bundle_tier="premium",
            cost_floor=0.04,
            markup_pct=20.0,
            active=True,
        ),
    ]
    return {"threads": [t.model_dump() for t in catalog]}
    # [WAOOAW_LOGIC_FILLER_END]


class ThreadEntry(BaseModel):
    # [WAOOAW_LOGIC_FILLER_START]
    thread_id: str = Field(..., description="Unique identifier for the thread entry")
    agent_type: str = Field(..., description="Type of agent (e.g. gpt4, claude)")
    bundle_tier: str = Field(..., description="Bundle tier (e.g. standard, premium)")
    cost_floor: float = Field(..., ge=0.0, description="Minimum cost floor for this thread")
    markup_pct: float = Field(..., ge=0.0, le=200.0, description="Markup percentage applied")
    active: bool = Field(default=True, description="Whether this thread entry is active")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    # [WAOOAW_LOGIC_FILLER_END]


class BundleProfile(BaseModel):
    # [WAOOAW_LOGIC_FILLER_START]
    agent_type: str = Field(..., description="Type of agent (e.g. gpt4, claude)")
    bundle_tier: str = Field(..., description="Bundle tier (e.g. standard, premium)")
    cost_floor: float = Field(..., ge=0.0, description="Minimum cost floor for this bundle")
    markup_pct: float = Field(..., ge=0.0, le=200.0, description="Markup percentage applied")
    description: str | None = Field(default=None, description="Optional description")
    active: bool = Field(default=True, description="Whether this bundle profile is active")
    # [WAOOAW_LOGIC_FILLER_END]