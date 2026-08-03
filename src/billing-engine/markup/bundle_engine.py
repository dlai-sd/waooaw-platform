# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from markup.models import AgentType, BundleTier, ThreadEntry

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory catalog (replace with DB-backed store as needed)
# ---------------------------------------------------------------------------

_THREAD_CATALOG: list[ThreadEntry] = [
    ThreadEntry(
        thread_id="std-basic-001",
        name="Standard Basic Thread",
        agent_type=AgentType.STANDARD,
        bundle_tier=BundleTier.BASIC,
        base_cost_usd=1.00,
        markup_pct=10.0,
        active=True,
        description="Entry-level standard thread",
    ),
    ThreadEntry(
        thread_id="prem-pro-001",
        name="Premium Professional Thread",
        agent_type=AgentType.PREMIUM,
        bundle_tier=BundleTier.PROFESSIONAL,
        base_cost_usd=5.00,
        markup_pct=15.0,
        active=True,
        description="Professional-grade premium thread",
    ),
    ThreadEntry(
        thread_id="ent-elite-001",
        name="Enterprise Elite Thread",
        agent_type=AgentType.ENTERPRISE,
        bundle_tier=BundleTier.ELITE,
        base_cost_usd=20.00,
        markup_pct=20.0,
        active=True,
        description="Enterprise elite thread",
    ),
]

_COST_FLOORS: dict[tuple[str, str], float] = {
    (AgentType.STANDARD, BundleTier.BASIC): 0.50,
    (AgentType.STANDARD, BundleTier.PROFESSIONAL): 2.00,
    (AgentType.STANDARD, BundleTier.ELITE): 8.00,
    (AgentType.PREMIUM, BundleTier.BASIC): 2.00,
    (AgentType.PREMIUM, BundleTier.PROFESSIONAL): 6.00,
    (AgentType.PREMIUM, BundleTier.ELITE): 15.00,
    (AgentType.ENTERPRISE, BundleTier.BASIC): 5.00,
    (AgentType.ENTERPRISE, BundleTier.PROFESSIONAL): 12.00,
    (AgentType.ENTERPRISE, BundleTier.ELITE): 25.00,
}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ValidateRequest(BaseModel):
    bundle_id: str = Field(..., description="Bundle identifier to validate")
    agent_type: AgentType = Field(..., description="Agent type")
    bundle_tier: BundleTier = Field(..., description="Bundle tier")
    proposed_cost_usd: float = Field(..., ge=0.0, description="Proposed cost in USD")


class ValidateResponse(BaseModel):
    valid: bool
    reason: str | None = None
    cost_floor_usd: float
    proposed_cost_usd: float
    validated_at: datetime


class DeriveRequest(BaseModel):
    agent_type: AgentType = Field(..., description="Agent type")
    bundle_tier: BundleTier = Field(..., description="Bundle tier")
    base_cost_usd: float = Field(..., ge=0.0, description="Base cost before markup")
    markup_pct: float | None = Field(default=None, ge=0.0, le=100.0, description="Override markup percentage")


class DeriveResponse(BaseModel):
    agent_type: AgentType
    bundle_tier: BundleTier
    base_cost_usd: float
    markup_pct: float
    derived_cost_usd: float
    cost_floor_usd: float
    final_cost_usd: float
    derived_at: datetime


# ---------------------------------------------------------------------------
# BundleEngine helper class
# ---------------------------------------------------------------------------


class BundleEngine:
    """Core logic for bundle cost derivation and validation."""

    @staticmethod
    def get_cost_floor(agent_type: AgentType, bundle_tier: BundleTier) -> float:
        key = (agent_type, bundle_tier)
        return _COST_FLOORS.get(key, 0.0)

    @staticmethod
    def derive_cost(
        base_cost_usd: float,
        markup_pct: float,
        cost_floor_usd: float,
    ) -> float:
        derived = base_cost_usd * (1.0 + markup_pct / 100.0)
        return max(derived, cost_floor_usd)

    @staticmethod
    def validate_cost(
        proposed_cost_usd: float,
        cost_floor_usd: float,
    ) -> tuple[bool, str | None]:
        if proposed_cost_usd < cost_floor_usd:
            return (
                False,
                f"Proposed cost {proposed_cost_usd} is below cost floor {cost_floor_usd}",
            )
        return True, None

    @staticmethod
    def get_thread_catalog() -> list[ThreadEntry]:
        return [t for t in _THREAD_CATALOG if t.active]

    @staticmethod
    def get_default_markup_pct(agent_type: AgentType, bundle_tier: BundleTier) -> float:
        for entry in _THREAD_CATALOG:
            if entry.agent_type == agent_type and entry.bundle_tier == bundle_tier and entry.active:
                return entry.markup_pct
        return 10.0


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/thread-catalog")
def get_thread_catalog() -> dict:
    """GET /thread-catalog"""
    catalog = BundleEngine.get_thread_catalog()
    return {
        "threads": [t.model_dump() for t in catalog],
        "count": len(catalog),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/bundle-cost-floor/{agent_type}/{bundle_tier}")
def get_bundle_cost_floor_agent_type_bundle_tier(
    agent_type: AgentType,
    bundle_tier: BundleTier,
) -> dict:
    """GET /bundle-cost-floor/{agent_type}/{bundle_tier}"""
    cost_floor = BundleEngine.get_cost_floor(agent_type, bundle_tier)
    return {
        "agent_type": agent_type,
        "bundle_tier": bundle_tier,
        "cost_floor_usd": cost_floor,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/validate")
def post_validate(request: ValidateRequest) -> dict:
    """POST /validate"""
    cost_floor = BundleEngine.get_cost_floor(request.agent_type, request.bundle_tier)
    valid, reason = BundleEngine.validate_cost(request.proposed_cost_usd, cost_floor)
    response = ValidateResponse(
        valid=valid,
        reason=reason,
        cost_floor_usd=cost_floor,
        proposed_cost_usd=request.proposed_cost_usd,
        validated_at=datetime.now(timezone.utc),
    )
    return response.model_dump()


@router.post("/derive")
def post_derive(request: DeriveRequest) -> dict:
    """POST /derive"""
    cost_floor = BundleEngine.get_cost_floor(request.agent_type, request.bundle_tier)
    markup_pct = (
        request.markup_pct
        if request.markup_pct is not None
        else BundleEngine.get_default_markup_pct(request.agent_type, request.bundle_tier)
    )
    final_cost = BundleEngine.derive_cost(request.base_cost_usd, markup_pct, cost_floor)
    derived_raw = request.base_cost_usd * (1.0 + markup_pct / 100.0)
    response = DeriveResponse(
        agent_type=request.agent_type,
        bundle_tier=request.bundle_tier,
        base_cost_usd=request.base_cost_usd,
        markup_pct=markup_pct,
        derived_cost_usd=derived_raw,
        cost_floor_usd=cost_floor,
        final_cost_usd=final_cost,
        derived_at=datetime.now(timezone.utc),
    )
    return response.model_dump()


@router.post("/pricing/validate")
def post_pricing_validate(request: ValidateRequest) -> dict:
    """POST /pricing/validate"""
    cost_floor = BundleEngine.get_cost_floor(request.agent_type, request.bundle_tier)
    valid, reason = BundleEngine.validate_cost(request.proposed_cost_usd, cost_floor)
    response = ValidateResponse(
        valid=valid,
        reason=reason,
        cost_floor_usd=cost_floor,
        proposed_cost_usd=request.proposed_cost_usd,
        validated_at=datetime.now(timezone.utc),
    )
    return response.model_dump()


@router.get("/pricing/thread-catalog")
def get_pricing_thread_catalog() -> dict:
    """GET /pricing/thread-catalog"""
    catalog = BundleEngine.get_thread_catalog()
    return {
        "threads": [t.model_dump() for t in catalog],
        "count": len(catalog),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }