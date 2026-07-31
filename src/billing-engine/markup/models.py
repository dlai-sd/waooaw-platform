# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class PriceOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BundleTier(StrEnum):
    STARTER    = "STARTER"
    GROWTH     = "GROWTH"
    SCALE      = "SCALE"
    ENTERPRISE = "ENTERPRISE"


# ── Request models ────────────────────────────────────────────────────────────

class PriceValidationRequest(BaseModel):
    """
    Request body for POST /pricing/validate.
    Constitutional: C-089 — proposed price is checked against margin floor.
    """
    agent_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Agent type key (e.g. 'DMA', 'CMA').",
    )
    bundle_tier: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Bundle tier key (e.g. 'STARTER', 'GROWTH').",
    )
    proposed_price_paise: int = Field(
        ...,
        ge=0,
        description="Proposed retail price in INR paise (must be ≥ minimum compliant price).",
    )

    @field_validator("proposed_price_paise")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("proposed_price_paise must be non-negative")
        return v


class PriceDeriveRequest(BaseModel):
    """
    Request body for POST /pricing/derive.
    If target_margin_pct is omitted, bundle_profiles.minimum_margin_pct is used.
    """
    agent_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Agent type key.",
    )
    bundle_tier: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Bundle tier key.",
    )
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description=(
            "Target margin-on-revenue percentage. "
            "If None, bundle_profiles.minimum_margin_pct is used."
        ),
    )


# ── Domain value objects ──────────────────────────────────────────────────────

class ThreadEntry(BaseModel):
    """
    Lightweight view of institutional.thread_catalog row used inside markup logic.
    Not the full ThreadCatalogEntry — only the fields markup engine needs.
    """
    thread_id: str
    provider: str
    raw_cost_inr_paise: int
    total_markup_pct: float
    marked_up_cost_paise: int
    applicable_agents: list[str]
    status: str


class BundleProfile(BaseModel):
    """
    Row from billing.bundle_profiles.
    cost_floor_paise  — pre-computed by Founder FA process; do NOT recompute.
    minimum_margin_pct — constitutional minimum margin (C-089).
    """
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0)


class PriceConfig(BaseModel):
    """
    Resolved pricing configuration combining BundleProfile with an optional
    override margin.  Used internally by BundleEngine before committing a
    validation or derivation decision.
    """
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    effective_margin_pct: float
    minimum_compliant_price_paise: int = Field(
        ...,
        description="ceil(cost_floor / (1 - margin/100)) — minimum price satisfying C-089.",
    )


# ── Response models ───────────────────────────────────────────────────────────

class PriceValidation(BaseModel):
    """
    Response from BundleEngine.validate_price() and POST /pricing/validate.

    Constitutional obligations:
      C-089 — outcome=REJECTED when proposed < minimum_compliant_price_paise.
      C-059 — every call (APPROVED or REJECTED) is persisted to pricing_floor_log.
    """
    validation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID of the pricing_floor_log row written for this validation.",
    )
    outcome: PriceOutcome
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int
    cost_floor_paise: int = Field(
        ...,
        description="Pre-computed cost floor from bundle_profiles (C-089 basis).",
    )
    minimum_compliant_price_paise: int = Field(
        ...,
        description=(
            "Minimum price that satisfies the constitutional margin floor. "
            "Equals ceil(cost_floor_paise / (1 - minimum_margin_pct / 100)). "
            "Returned on BOTH APPROVED and REJECTED outcomes (C-059 completeness)."
        ),
    )
    margin_pct_at_proposed: float | None = Field(
        default=None,
        description=(
            "Effective margin-on-revenue at proposed_price_paise. "
            "None when proposed_price_paise == 0 (division by zero guard)."
        ),
    )
    minimum_margin_pct: float = Field(
        ...,
        description="Constitutional minimum margin from bundle_profiles.",
    )
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    audit_note: str = Field(
        default="",
        description="Human-readable reason for REJECTED outcome; empty on APPROVED.",
    )


class CostFloorResponse(BaseModel):
    """
    Response for GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}.
    """
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    minimum_margin_pct: float
    minimum_compliant_price_paise: int


class DerivePriceResponse(BaseModel):
    """
    Response for POST /pricing/derive.
    """
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    effective_margin_pct: float
    derived_price_paise: int
    derived_at: datetime = Field(default_factory=datetime.utcnow)