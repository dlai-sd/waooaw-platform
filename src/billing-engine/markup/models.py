# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── Request / response models ─────────────────────────────────────────────────


class ThreadEntry(BaseModel):
    """A single entry from the thread catalog."""

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
    """
    Row from bundle_profiles table.
    cost_floor_paise is authoritative — do NOT recompute from thread catalog.
    minimum_margin_pct is the C-089 constitutional floor for this bundle.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0)


class PriceConfig(BaseModel):
    """Pricing configuration used to derive or validate a price."""

    agent_type: str
    bundle_tier: str
    target_margin_pct: float | None = Field(
        default=None,
        description=(
            "Override margin. If None, bundle_profiles.minimum_margin_pct is used."
        ),
    )


class PriceValidationRequest(BaseModel):
    """
    Request body for POST /pricing/validate.
    proposed_price_paise is the price the caller wants to charge.
    C-089: engine will reject if proposed_price < minimum_compliant_price.
    """

    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(..., ge=0)


class PriceDeriveRequest(BaseModel):
    """
    Request body for POST /pricing/derive.
    target_margin_pct is optional; falls back to bundle_profiles.minimum_margin_pct.
    """

    agent_type: str
    bundle_tier: str
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Margin-on-revenue override. None → use DB minimum.",
    )


class PriceValidation(BaseModel):
    """
    Response from validate_price() and POST /pricing/validate.

    Fields
    ------
    outcome                     : APPROVED or REJECTED (C-089 gate result)
    cost_floor_paise            : raw cost floor from bundle_profiles
    minimum_compliant_price_paise: lowest price that satisfies C-089 margin floor
    proposed_price_paise        : the price the caller proposed
    log_id                      : UUID of the pricing_floor_log row written (C-059)
    evaluated_at                : UTC timestamp of the evaluation
    """

    outcome: PriceOutcome
    cost_floor_paise: int
    minimum_compliant_price_paise: int
    proposed_price_paise: int
    log_id: UUID = Field(default_factory=uuid4)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class PriceDeriveResponse(BaseModel):
    """
    Response from derive_price() and POST /pricing/derive.

    Fields
    ------
    derived_price_paise : the calculated price using margin-on-revenue formula
    cost_floor_paise    : raw cost floor from bundle_profiles
    margin_pct          : the margin percentage used in derivation
    evaluated_at        : UTC timestamp of the evaluation
    """

    derived_price_paise: int
    cost_floor_paise: int
    margin_pct: float
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)