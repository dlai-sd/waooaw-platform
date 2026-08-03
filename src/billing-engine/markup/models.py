# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class AgentType(StrEnum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class BundleTier(StrEnum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ELITE = "elite"


class ThreadEntry(BaseModel):
    thread_id: str = Field(..., description="Unique identifier for the thread type")
    name: str = Field(..., description="Human-readable thread name")
    agent_type: AgentType = Field(..., description="Agent type classification")
    bundle_tier: BundleTier = Field(..., description="Bundle tier classification")
    base_cost_usd: float = Field(..., ge=0.0, description="Base cost in USD")
    markup_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Markup percentage")
    active: bool = Field(default=True, description="Whether this thread entry is active")
    description: Optional[str] = Field(default=None, description="Optional description")


class BundleProfile(BaseModel):
    bundle_id: str = Field(..., description="Unique bundle identifier")
    agent_type: AgentType = Field(..., description="Agent type for this bundle")
    bundle_tier: BundleTier = Field(..., description="Tier for this bundle")
    cost_floor_usd: float = Field(..., ge=0.0, description="Minimum cost floor in USD")
    cost_ceiling_usd: Optional[float] = Field(default=None, ge=0.0, description="Optional cost ceiling in USD")
    threads: list[ThreadEntry] = Field(default_factory=list, description="Thread entries in this bundle")
    markup_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Bundle-level markup percentage")
    active: bool = Field(default=True, description="Whether this bundle profile is active")