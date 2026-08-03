# Implements: WC027-01a — Pydantic models for Markup Engine
# constitutional_basis: C-059, C-089

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PricingOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ThreadEntry(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    description: str = Field(default="", description="Human-readable description")
    base_cost_paise: int = Field(..., ge=0, description="Base cost in paise")
    is_active: bool = Field(default=True, description="Whether this thread entry is active")


class BundleProfile(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    cost_floor_paise: int = Field(..., ge=0, description="Cost floor in paise (read from DB)")
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0, description="Minimum margin percentage")


class PriceConfig(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Target margin percentage; uses bundle minimum if None",
    )


class PriceValidationRequest(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    proposed_price_paise: int = Field(..., ge=0, description="Proposed price in paise")


class PriceDeriveRequest(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Target margin percentage; uses bundle minimum if None",
    )


class PriceValidation(BaseModel):
    outcome: PricingOutcome = Field(..., description="APPROVED or REJECTED")
    cost_floor_paise: int = Field(..., ge=0, description="Cost floor in paise")
    minimum_compliant_price_paise: int = Field(
        ..., ge=0, description="Minimum price that satisfies margin floor"
    )
    proposed_price_paise: int = Field(..., ge=0, description="The proposed price that was validated")
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    margin_pct_applied: float = Field(..., description="Margin percentage used for validation")