# Implements: WC027-01a — Pydantic models for pricing
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-06
# Constitutional basis: C-059, C-082, C-090
from __future__ import annotations

from pydantic import BaseModel, Field


class ThreadEntry(BaseModel):
    """Thread catalog entry — mirrors institutional.thread_catalog"""
    thread_id: str
    display_name: str
    provider: str
    unit_description: str
    raw_cost_inr_paise: int
    total_markup_pct: float
    marked_up_cost_paise: int
    is_platform_thread: bool
    applicable_agents: list[str]
    status: str


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
    agent_version: str | None = None


class PriceDeriveRequest(BaseModel):
    """Request model for price derivation"""
    agent_type: str
    bundle_tier: str
    target_margin_pct: int | None = None
    agent_version: str | None = None


class PriceValidation(BaseModel):
    """Response model for price validation"""
    outcome: str = Field(..., description="APPROVED or REJECTED")
    cost_floor_paise: int
    minimum_compliant_price_paise: int
    proposed_price_paise: int
