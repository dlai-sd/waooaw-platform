# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    """Pricing validation outcome per C-089 margin floor."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BundleTier(StrEnum):
    """Constitutional bundle tier enumeration (C-088)."""

    STARTER = "STARTER"
    GROWTH = "GROWTH"
    SCALE = "SCALE"
    ENTERPRISE = "ENTERPRISE"


# ── Request models ────────────────────────────────────────────────────────────


class PriceValidationRequest(BaseModel):
    """
    Request payload for POST /pricing/validate (Amendment 2 — corrected contract).

    Constitutional: C-089 (Margin Floor validation).
    """

    agent_type: str = Field(
        ...,
        description="Agent type identifier (e.g. 'DMA', 'PSE').",
        min_length=1,
    )
    bundle_tier: str = Field(
        ...,
        description="Bundle tier identifier (e.g. 'STARTER', 'GROWTH').",
        min_length=1,
    )
    proposed_price_paise: int = Field(
        ...,
        description="Proposed retail price in INR paise (integer, must be > 0).",
        gt=0,
    )

    @field_validator("proposed_price_paise")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        """Validate that proposed price is strictly positive (C-089)."""
        if v <= 0:
            raise ValueError("proposed_price_paise must be a positive integer")
        return v


class PriceDeriveRequest(BaseModel):
    """
    Request payload for POST /pricing/derive.

    Constitutional: C-089 (derives price using minimum margin floor).
    """

    agent_type: str = Field(
        ...,
        description="Agent type identifier.",
        min_length=1,
    )
    bundle_tier: str = Field(
        ...,
        description="Bundle tier identifier.",
        min_length=1,
    )
    target_margin_pct: float | None = Field(
        default=None,
        description=(
            "Desired margin-on-revenue percentage. "
            "If None, uses bundle_profiles.minimum_margin_pct from DB."
        ),
        ge=0.0,
        lt=100.0,
    )


# ── DB / domain value objects ─────────────────────────────────────────────────


class ThreadEntry(BaseModel):
    """
    Represents one row from institutional.thread_catalog.
    Read-only domain value object — not persisted by this service.

    Constitutional: C-091 (Thread Catalog Sovereignty).
    """

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

    model_config = {"frozen": True}


class BundleProfile(BaseModel):
    """
    Represents one row from institutional.bundle_profiles.

    Constitutional: C-089 (cost_floor_paise is pre-computed and stored in DB —
    do NOT recompute). minimum_margin_pct is the constitutional margin floor
    for derive_price().
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(
        ...,
        description="Pre-computed cost floor in INR paise from bundle_profiles table.",
        ge=0,
    )
    minimum_margin_pct: float = Field(
        ...,
        description="Constitutional minimum margin-on-revenue percentage (C-089).",
        ge=0.0,
        lt=100.0,
    )

    model_config = {"frozen": True}


class PriceConfig(BaseModel):
    """
    Runtime pricing configuration snapshot used by BundleEngine.
    Captures the inputs that produced a derived or validated price.

    Constitutional: C-089, C-059 (audit trace).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    minimum_margin_pct: float
    effective_margin_pct: float = Field(
        ...,
        description="Margin actually applied (may equal minimum_margin_pct or target).",
    )
    derived_price_paise: int = Field(
        ...,
        description="Price produced by derive_price() formula.",
    )

    model_config = {"frozen": True}


# ── Response models ───────────────────────────────────────────────────────────


class PriceValidation(BaseModel):
    """
    Response from validate_price() and POST /pricing/validate.

    Constitutional obligations:
      C-089 — outcome reflects whether proposed_price_paise >= minimum_compliant_price_paise.
      C-059 — this response correlates 1:1 with a pricing_floor_log row (log_id).
      Amendment 2 — minimum_compliant_price_paise MUST be present in both APPROVED
                     and REJECTED responses so callers can always self-correct.
      C-063 — rejection_reason must not contain PII.
    """

    log_id: UUID = Field(
        default_factory=uuid4,
        description="Primary key of the pricing_floor_log row written for C-059 audit.",
    )
    outcome: PriceOutcome = Field(
        ...,
        description="APPROVED if proposed_price_paise >= minimum_compliant_price_paise, else REJECTED.",
    )
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(
        ...,
        description="The price submitted for validation — echoed back for caller convenience.",
        gt=0,
    )
    cost_floor_paise: int = Field(
        ...,
        description="Pre-computed cost floor read from bundle_profiles (never recomputed).",
        ge=0,
    )
    minimum_margin_pct: float = Field(
        ...,
        description="Constitutional minimum margin-on-revenue percentage (C-089).",
    )
    minimum_compliant_price_paise: int = Field(
        ...,
        description=(
            "Minimum price that would satisfy C-089: "
            "ceil(cost_floor_paise / (1 - minimum_margin_pct / 100)). "
            "Always present — callers MUST use this to self-correct on REJECTED."
        ),
        ge=0,
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the validation evaluation.",
    )
    rejection_reason: str | None = Field(
        default=None,
        description=(
            "Human-readable rejection reason. Populated only when outcome=REJECTED. "
            "Must NOT contain PII (C-063)."
        ),
    )

    model_config = {"frozen": True}


class PriceDeriveResponse(BaseModel):
    """
    Response from derive_price() and POST /pricing/derive.

    Constitutional: C-089 (derived price always respects minimum margin floor).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(
        ...,
        description="Pre-computed cost floor from bundle_profiles.",
        ge=0,
    )
    minimum_margin_pct: float = Field(
        ...,
        description="Minimum margin-on-revenue percentage (C-089).",
    )
    target_margin_pct: float | None = Field(
        default=None,
        description="Target margin requested, or None (uses minimum).",
    )
    effective_margin_pct: float = Field(
        ...,
        description="Actual margin applied (max of target and minimum).",
    )
    derived_price_paise: int = Field(
        ...,
        description="Derived retail price in INR paise using formula: floor / (1 - margin/100).",
        ge=0,
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of derivation.",
    )

    model_config = {"frozen": True}


class BundleCostFloorResponse(BaseModel):
    """
    Response from GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}.

    Constitutional: C-089 (cost floor is the baseline for margin validation).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(
        ...,
        description="Cost floor in INR paise (pre-computed, never recomputed).",
        ge=0,
    )
    minimum_margin_pct: float = Field(
        ...,
        description="Minimum margin-on-revenue percentage (C-089).",
    )
    queried_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the query.",
    )

    model_config = {"frozen": True}