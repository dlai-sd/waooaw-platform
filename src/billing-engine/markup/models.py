# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── Request / input models ────────────────────────────────────────────────────


class ThreadEntry(BaseModel):
    """
    Represents a single entry from the thread catalog.
    Maps to institutional.thread_catalog rows.
    """

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
    Represents a row from bundle_profiles.
    cost_floor_paise is pre-computed and stored — do NOT recompute.
    minimum_margin_pct is the constitutional floor (C-089).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0)

    @field_validator("minimum_margin_pct")
    @classmethod
    def margin_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("minimum_margin_pct must be non-negative")
        return v


class PriceConfig(BaseModel):
    """
    Configuration snapshot used during price derivation.
    Captures the effective margin and the resulting derived price.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    effective_margin_pct: float = Field(..., ge=0.0, lt=100.0)
    derived_price_paise: int = Field(..., ge=0)


class PriceValidationRequest(BaseModel):
    """
    Request body for POST /pricing/validate.
    proposed_price_paise is the candidate price to check against C-089.
    """

    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(..., ge=0)


class PriceDeriveRequest(BaseModel):
    """
    Request body for POST /pricing/derive.
    target_margin_pct is optional; defaults to bundle_profiles.minimum_margin_pct.
    """

    agent_type: str
    bundle_tier: str
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description=(
            "Target margin-on-revenue percentage. "
            "If omitted, bundle_profiles.minimum_margin_pct is used."
        ),
    )


# ── Response / output models ──────────────────────────────────────────────────


class PriceValidation(BaseModel):
    """
    Response from BundleEngine.validate_price() and POST /pricing/validate.

    Constitutional obligations (C-059, C-089):
    - outcome: APPROVED or REJECTED
    - cost_floor_paise: the DB-stored floor for this bundle
    - minimum_compliant_price_paise: smallest price that satisfies C-089 margin floor
    - proposed_price_paise: the price that was evaluated
    - log_id: UUID of the pricing_floor_log row written for audit traceability
    - evaluated_at: UTC timestamp of the validation event
    """

    log_id: UUID = Field(default_factory=uuid4)
    agent_type: str
    bundle_tier: str
    outcome: PriceOutcome
    proposed_price_paise: int = Field(..., ge=0)
    cost_floor_paise: int = Field(..., ge=0)
    minimum_compliant_price_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    rejection_reason: str | None = None