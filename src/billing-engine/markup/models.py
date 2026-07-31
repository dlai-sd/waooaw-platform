# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    """Constitutional outcome of price validation against C-089 margin floor."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── Request / domain models ───────────────────────────────────────────────────


class ThreadEntry(BaseModel):
    """A single entry from the institutional.thread_catalog table."""

    thread_id: str
    display_name: str
    provider: str
    unit_description: str
    raw_cost_inr_paise: int = Field(..., ge=0)
    total_markup_pct: float = Field(..., ge=0.0)
    marked_up_cost_paise: int = Field(..., ge=0)
    is_platform_thread: bool
    applicable_agents: list[str]
    status: str


class BundleProfile(BaseModel):
    """
    Row from institutional.bundle_profiles.
    
    Constitutional basis: C-089 (Margin Floor).
    cost_floor_paise is read directly from DB — never recomputed.
    minimum_margin_pct is the constitutional floor below which pricing is forbidden.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, le=100.0)


class PriceConfig(BaseModel):
    """
    Caller-supplied pricing configuration for derive_price().
    
    target_margin_pct overrides bundle_profiles.minimum_margin_pct when provided.
    If omitted, derive_price() falls back to the DB-stored minimum_margin_pct.
    """

    agent_type: str
    bundle_tier: str
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description=(
            "Target margin on revenue (%).  Must be < 100 to avoid division by zero. "
            "If None, bundle_profiles.minimum_margin_pct is used."
        ),
    )


class PriceValidationRequest(BaseModel):
    """
    Payload for POST /pricing/validate.
    
    proposed_price_paise is the caller's proposed selling price in INR paise.
    """

    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(..., ge=0)


class PriceDeriveRequest(BaseModel):
    """
    Payload for POST /pricing/derive.
    
    target_margin_pct is optional — falls back to DB minimum if absent.
    """

    agent_type: str
    bundle_tier: str
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
    )

    @model_validator(mode="after")
    def margin_not_exactly_100(self) -> PriceDeriveRequest:
        """Validate that margin is strictly less than 100 (C-089 division by zero guard)."""
        if self.target_margin_pct is not None and self.target_margin_pct >= 100.0:
            raise ValueError(
                "target_margin_pct must be strictly less than 100 "
                "(division by zero in margin-on-revenue formula)"
            )
        return self


# ── Response models ───────────────────────────────────────────────────────────


class PriceValidation(BaseModel):
    """
    Response from validate_price() / POST /pricing/validate.
    
    Constitutional basis: C-089 (Margin Floor), C-059 (Traceability).

    Fields
    ------
    outcome
        APPROVED — proposed price satisfies C-089 margin floor.
        REJECTED — proposed price violates C-089; minimum_compliant_price_paise
                   indicates the lowest permissible price.
    cost_floor_paise
        Absolute cost floor read from bundle_profiles.  Never recomputed.
    minimum_compliant_price_paise
        Lowest price that satisfies the constitutional margin floor:
            ceil(cost_floor_paise / (1 - minimum_margin_pct / 100))
        Always present — callers must surface this on REJECTED (HTTP 422).
    proposed_price_paise
        Echo of the caller's proposed price for audit correlation.
    log_id
        Primary key of the pricing_floor_log row written for C-059 traceability.
        Present on both APPROVED and REJECTED outcomes.
    evaluated_at
        UTC timestamp of the evaluation (server-assigned).
    """

    outcome: PriceOutcome
    cost_floor_paise: int = Field(..., ge=0)
    minimum_compliant_price_paise: int = Field(..., ge=0)
    proposed_price_paise: int = Field(..., ge=0)
    log_id: UUID
    evaluated_at: datetime


class BundleCostFloorResponse(BaseModel):
    """Response for GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}."""

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, le=100.0)
    minimum_compliant_price_paise: int = Field(..., ge=0)


class DerivedPriceResponse(BaseModel):
    """Response for POST /pricing/derive."""

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    effective_margin_pct: float = Field(..., ge=0.0, lt=100.0)
    derived_price_paise: int = Field(..., ge=0)