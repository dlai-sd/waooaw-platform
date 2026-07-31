# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BundleTier(StrEnum):
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    SCALE = "SCALE"
    ENTERPRISE = "ENTERPRISE"


# ── Domain read models (from DB) ──────────────────────────────────────────────


class ThreadEntry(BaseModel):
    """
    Represents a single row from institutional.thread_catalog.
    Read-only — never written by the Markup Engine.
    """

    thread_id: str
    display_name: str
    provider: str
    unit_description: str
    raw_cost_inr_paise: int = Field(ge=0)
    total_markup_pct: float = Field(ge=0.0)
    marked_up_cost_paise: int = Field(ge=0)
    is_platform_thread: bool
    applicable_agents: list[str]
    status: str


class BundleProfile(BaseModel):
    """
    Represents a single row from institutional.bundle_profiles.
    Stores the pre-computed cost floor and the minimum margin percentage
    mandated by the Founder (C-089).
    cost_floor_paise is authoritative — never recomputed by BundleEngine.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(ge=0, description="Pre-computed DB value — do NOT recompute")
    minimum_margin_pct: float = Field(
        ge=0.0,
        lt=100.0,
        description="Founder-mandated minimum margin percentage (C-089)",
    )

    @field_validator("minimum_margin_pct")
    @classmethod
    def margin_must_be_finite(cls, v: float) -> float:
        if v >= 100.0:
            raise ValueError("minimum_margin_pct must be strictly less than 100")
        return v


class PriceConfig(BaseModel):
    """
    Runtime pricing configuration resolved for a given agent_type + bundle_tier.
    Combines the DB cost floor with any override margin supplied by the caller.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(ge=0)
    minimum_margin_pct: float = Field(ge=0.0, lt=100.0)
    effective_margin_pct: float = Field(
        ge=0.0,
        lt=100.0,
        description="Actual margin used for price derivation (caller override or DB minimum)",
    )


# ── Request models ────────────────────────────────────────────────────────────


class PriceValidationRequest(BaseModel):
    """
    Payload for POST /pricing/validate.
    C-089: proposed_price_paise is compared against the constitutional minimum.
    """

    agent_type: str = Field(min_length=1)
    bundle_tier: str = Field(min_length=1)
    proposed_price_paise: int = Field(
        ge=0,
        description="Proposed retail price in INR paise",
    )


class PriceDeriveRequest(BaseModel):
    """
    Payload for POST /pricing/derive.
    target_margin_pct is optional; if omitted the engine uses
    bundle_profiles.minimum_margin_pct (C-089 floor).
    """

    agent_type: str = Field(min_length=1)
    bundle_tier: str = Field(min_length=1)
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Desired margin-on-revenue percentage. Defaults to DB minimum.",
    )


# ── Response models ───────────────────────────────────────────────────────────


class PriceValidation(BaseModel):
    """
    Response from BundleEngine.validate_price() and POST /pricing/validate.
    C-059: audit fields trace the decision back to a pricing_floor_log row.
    C-089: minimum_compliant_price_paise MUST always be returned so callers
           can correct a rejected submission without a second round-trip.
    """

    outcome: PriceOutcome
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(ge=0)
    cost_floor_paise: int = Field(ge=0)
    minimum_compliant_price_paise: int = Field(
        ge=0,
        description=(
            "Lowest price that satisfies C-089 constitutional margin floor. "
            "Always returned — even on APPROVED — so callers have the reference value."
        ),
    )
    minimum_margin_pct: float = Field(ge=0.0, lt=100.0)
    pricing_floor_log_id: UUID = Field(
        description="FK to pricing_floor_log row written for C-059 audit (both APPROVED and REJECTED)"
    )
    evaluated_at: datetime = Field(
        description="UTC timestamp of the validation decision"
    )

    @property
    def is_compliant(self) -> bool:
        return self.outcome == PriceOutcome.APPROVED


class DerivedPrice(BaseModel):
    """
    Response from BundleEngine.derive_price() and GET /pricing/bundle-cost-floor/{…}.
    Formula: floor / (1 - margin/100)  — margin-on-revenue (not margin-on-cost).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(ge=0)
    effective_margin_pct: float = Field(ge=0.0, lt=100.0)
    derived_price_paise: int = Field(
        ge=0,
        description="ceil(cost_floor_paise / (1 - effective_margin_pct / 100))",
    )


# ── Audit log write model (internal — not exposed via API) ────────────────────


class PricingFloorLogEntry(BaseModel):
    """
    Internal model used by BundleEngine to persist a row to pricing_floor_log.
    Not exposed via FastAPI — used only within bundle_engine.py.
    C-059: both APPROVED and REJECTED outcomes MUST produce a row.
    No PII fields — C-063.
    """

    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(ge=0)
    cost_floor_paise: int = Field(ge=0)
    minimum_compliant_price_paise: int = Field(ge=0)
    minimum_margin_pct: float = Field(ge=0.0, lt=100.0)
    outcome: PriceOutcome
    evaluated_at: datetime