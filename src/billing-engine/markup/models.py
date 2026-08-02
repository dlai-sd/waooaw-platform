# Implements: WC027 — WC027-01a
# constitutional_basis: C-059, C-082
from __future__ import annotations

from pydantic import BaseModel, Field
from skeleton.wbe_interfaces import IMarkupEngine, PriceValidation


class ThreadEntry(BaseModel):
    thread_id: str = Field(..., description="Unique identifier for the billing thread")
    agent_type: str = Field(..., description="Type of agent associated with this thread")
    bundle_tier: str = Field(..., description="Bundle tier assigned to this thread")
    created_at: str = Field(..., description="ISO8601 timestamp of thread creation")
    metadata: dict = Field(default_factory=dict, description="Arbitrary metadata for the thread")


class BundleProfile(BaseModel):
    agent_type: str = Field(..., description="Type of agent this bundle profile applies to")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    cost_floor_paise: int = Field(..., ge=0, description="Minimum cost floor in paise")
    minimum_margin_pct: float = Field(..., ge=0.0, le=100.0, description="Minimum required margin percentage")
    description: str = Field(default="", description="Human-readable description of the bundle profile")


class PriceConfig(BaseModel):
    agent_type: str = Field(..., description="Type of agent")
    bundle_tier: str = Field(..., description="Bundle tier")
    target_margin_pct: float | None = Field(default=None, ge=0.0, le=100.0, description="Target margin percentage; uses bundle minimum if None")


class PriceValidationRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent")
    bundle_tier: str = Field(..., description="Bundle tier")
    proposed_price_paise: int = Field(..., ge=0, description="Proposed price in paise to validate")


class PriceDeriveRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent")
    bundle_tier: str = Field(..., description="Bundle tier")
    target_margin_pct: float | None = Field(default=None, ge=0.0, le=100.0, description="Target margin percentage; uses bundle minimum if None")