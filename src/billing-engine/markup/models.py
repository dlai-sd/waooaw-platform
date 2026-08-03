# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from enum import StrEnum
from decimal import Decimal
from fastapi import FastAPI

router = APIRouter()


@router.get('/thread-catalog')
def get_thread_catalog() -> dict:
    """GET /thread-catalog"""
    # [WAOOAW_LOGIC_FILLER_START]
    catalog = [entry.model_dump() for entry in _default_thread_catalog()]
    return {"threads": catalog}
    # [WAOOAW_LOGIC_FILLER_END]


@router.get('/bundle-cost-floor/{agent_type}/{bundle_tier}')
def get_bundle_cost_floor_agent_type_bundle_tier(agent_type: str, bundle_tier: str) -> dict:
    """GET /bundle-cost-floor/{agent_type}/{bundle_tier}"""
    # [WAOOAW_LOGIC_FILLER_START]
    floor = _compute_cost_floor(agent_type=agent_type, bundle_tier=bundle_tier)
    return {"agent_type": agent_type, "bundle_tier": bundle_tier, "cost_floor": floor}
    # [WAOOAW_LOGIC_FILLER_END]


@router.post('/validate')
def post_validate(payload: BundleProfile) -> dict:
    """POST /validate"""
    # [WAOOAW_LOGIC_FILLER_START]
    errors = _validate_bundle_profile(payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return {"valid": True, "bundle_tier": payload.bundle_tier}
    # [WAOOAW_LOGIC_FILLER_END]


@router.post('/derive')
def post_derive(payload: BundleProfile) -> dict:
    """POST /derive"""
    # [WAOOAW_LOGIC_FILLER_START]
    errors = _validate_bundle_profile(payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    derived = _derive_pricing(payload)
    return derived
    # [WAOOAW_LOGIC_FILLER_END]


@router.post('/pricing/validate')
def post_pricing_validate(payload: BundleProfile) -> dict:
    """POST /pricing/validate"""
    # [WAOOAW_LOGIC_FILLER_START]
    errors = _validate_bundle_profile(payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return {"valid": True, "pricing_tier": payload.bundle_tier, "agent_type": payload.agent_type}
    # [WAOOAW_LOGIC_FILLER_END]


@router.get('/pricing/thread-catalog')
def get_pricing_thread_catalog() -> dict:
    """GET /pricing/thread-catalog"""
    # [WAOOAW_LOGIC_FILLER_START]
    catalog = [entry.model_dump() for entry in _default_thread_catalog()]
    return {"pricing_threads": catalog}
    # [WAOOAW_LOGIC_FILLER_END]


class AgentType(StrEnum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class BundleTier(StrEnum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ELITE = "elite"


class ThreadEntry(BaseModel):
    # [WAOOAW_LOGIC_FILLER_START]
    thread_id: str = Field(..., description="Unique identifier for the thread")
    thread_name: str = Field(..., description="Display name of the thread")
    agent_type: AgentType = Field(..., description="Type of agent associated with this thread")
    bundle_tier: BundleTier = Field(..., description="Bundle tier for this thread")
    base_cost: Decimal = Field(..., ge=Decimal("0"), description="Base cost in USD")
    markup_rate: Decimal = Field(default=Decimal("0.15"), ge=Decimal("0"), le=Decimal("1"), description="Markup rate as a fraction")
    is_active: bool = Field(default=True, description="Whether this thread is currently active")
    description: str | None = Field(default=None, description="Optional description of the thread")
    # [WAOOAW_LOGIC_FILLER_END]


class BundleProfile(BaseModel):
    # [WAOOAW_LOGIC_FILLER_START]
    bundle_id: str = Field(..., description="Unique identifier for the bundle")
    agent_type: AgentType = Field(..., description="Type of agent for this bundle")
    bundle_tier: BundleTier = Field(..., description="Tier level of the bundle")
    thread_ids: list[str] = Field(default_factory=list, description="List of thread IDs included in this bundle")
    base_price: Decimal = Field(..., ge=Decimal("0"), description="Base price of the bundle in USD")
    markup_override: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("1"), description="Optional markup override")
    is_active: bool = Field(default=True, description="Whether this bundle is currently active")
    metadata: dict | None = Field(default=None, description="Additional metadata for the bundle")
    # [WAOOAW_LOGIC_FILLER_END]


# ---------------------------------------------------------------------------
# Internal helpers (not exported as routes)
# ---------------------------------------------------------------------------

_COST_FLOOR_TABLE: dict[tuple[str, str], Decimal] = {
    ("standard", "basic"): Decimal("9.99"),
    ("standard", "professional"): Decimal("29.99"),
    ("standard", "elite"): Decimal("79.99"),
    ("premium", "basic"): Decimal("19.99"),
    ("premium", "professional"): Decimal("59.99"),
    ("premium", "elite"): Decimal("149.99"),
    ("enterprise", "basic"): Decimal("49.99"),
    ("enterprise", "professional"): Decimal("129.99"),
    ("enterprise", "elite"): Decimal("299.99"),
}


def _compute_cost_floor(agent_type: str, bundle_tier: str) -> Decimal:
    key = (agent_type.lower(), bundle_tier.lower())
    floor = _COST_FLOOR_TABLE.get(key)
    if floor is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cost floor defined for agent_type={agent_type!r}, bundle_tier={bundle_tier!r}",
        )
    return floor


def _default_thread_catalog() -> list[ThreadEntry]:
    return [
        ThreadEntry(
            thread_id="thread-std-basic-001",
            thread_name="Standard Basic Thread",
            agent_type=AgentType.STANDARD,
            bundle_tier=BundleTier.BASIC,
            base_cost=Decimal("9.99"),
            markup_rate=Decimal("0.10"),
        ),
        ThreadEntry(
            thread_id="thread-std-pro-001",
            thread_name="Standard Professional Thread",
            agent_type=AgentType.STANDARD,
            bundle_tier=BundleTier.PROFESSIONAL,
            base_cost=Decimal("29.99"),
            markup_rate=Decimal("0.12"),
        ),
        ThreadEntry(
            thread_id="thread-prem-elite-001",
            thread_name="Premium Elite Thread",
            agent_type=AgentType.PREMIUM,
            bundle_tier=BundleTier.ELITE,
            base_cost=Decimal("149.99"),
            markup_rate=Decimal("0.15"),
        ),
        ThreadEntry(
            thread_id="thread-ent-elite-001",
            thread_name="Enterprise Elite Thread",
            agent_type=AgentType.ENTERPRISE,
            bundle_tier=BundleTier.ELITE,
            base_cost=Decimal("299.99"),
            markup_rate=Decimal("0.20"),
        ),
    ]


def _validate_bundle_profile(profile: BundleProfile) -> list[str]:
    errors: list[str] = []
    floor = _COST_FLOOR_TABLE.get((profile.agent_type.lower(), profile.bundle_tier.lower()))
    if floor is not None and profile.base_price < floor:
        errors.append(
            f"base_price {profile.base_price} is below the cost floor {floor} "
            f"for agent_type={profile.agent_type}, bundle_tier={profile.bundle_tier}"
        )
    if profile.markup_override is not None:
        if profile.markup_override < Decimal("0") or profile.markup_override > Decimal("1"):
            errors.append("markup_override must be between 0 and 1 inclusive")
    return errors


def _derive_pricing(profile: BundleProfile) -> dict:
    markup_rate = profile.markup_override if profile.markup_override is not None else Decimal("0.15")
    final_price = profile.base_price * (Decimal("1") + markup_rate)
    return {
        "bundle_id": profile.bundle_id,
        "agent_type": profile.agent_type,
        "bundle_tier": profile.bundle_tier,
        "base_price": str(profile.base_price),
        "markup_rate": str(markup_rate),
        "final_price": str(final_price.quantize(Decimal("0.01"))),
        "thread_count": len(profile.thread_ids),
    }

app = FastAPI(title="billing-engine-markup")
app.include_router(router, prefix="/markup", tags=["markup"])
