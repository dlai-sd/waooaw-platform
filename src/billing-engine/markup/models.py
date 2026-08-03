# Implements: WC027-01a — Pydantic models for pricing
# constitutional_basis: C-059, C-082
from __future__ import annotations

from pydantic import BaseModel, Field


class ThreadEntry(BaseModel):
    """Thread catalog entry"""
    thread_id: str
    thread_name: str
    description: str | None = None
    agent_type: str
    bundle_tier: str


class BundleProfile(BaseModel):
    """Bundle profile configuration"""
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    minimum_margin_pct: int


class PriceConfig(BaseModel):
    """Price configuration"""
    agent_type: str
    bundle_tier: str
    target_margin_pct: int | None = None


class PriceValidationRequest(BaseModel):
    """Request model for price validation"""
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(..., gt=0)


class PriceDeriveRequest(BaseModel):
    """Request model for price derivation"""
    agent_type: str
    bundle_tier: str
    target_margin_pct: int | None = None


class PriceValidation(BaseModel):
    """Response model for price validation"""
    outcome: str = Field(..., description="APPROVED or REJECTED")
    cost_floor_paise: int
    minimum_compliant_price_paise: int
    proposed_price_paise: int

app = FastAPI(title="Billing Engine — Markup Pricing", version="1.0.0")
app.include_router(pricing_router, prefix="/pricing", tags=["pricing"])
