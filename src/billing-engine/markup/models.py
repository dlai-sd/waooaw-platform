# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-01a
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PriceOutcome(StrEnum):
    """Constitutional outcome of price validation (C-089 margin floor gate)."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Thread Catalog models
# ---------------------------------------------------------------------------


class ThreadEntry(BaseModel):
    """A single entry from the thread catalog."""

    thread_type: str = Field(..., description="Canonical thread-type identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str | None = Field(None, description="Optional description")
    unit_cost_paise: int = Field(
        ..., ge=0, description="Raw unit cost in INR paise (provider cost)"
    )
    is_active: bool = Field(True, description="Whether thread type is currently offered")


# ---------------------------------------------------------------------------
# Bundle Profile model
# ---------------------------------------------------------------------------


class BundleProfile(BaseModel):
    """
    Mirrors institutional.bundle_profiles DB row.
    cost_floor_paise is READ from DB — never recomputed here (C-089).
    minimum_margin_pct enforces the constitutional margin floor per C-089.
    """

    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(
        ..., description="Bundle tier (e.g. STARTER, PRO, ENTERPRISE)"
    )
    cost_floor_paise: int = Field(
        ..., ge=0, description="Pre-computed cost floor in INR paise — read from DB"
    )
    minimum_margin_pct: float = Field(
        ..., ge=0.0, lt=100.0, description="Minimum constitutional margin percentage"
    )

    @field_validator("minimum_margin_pct")
    @classmethod
    def margin_must_allow_finite_price(cls, v: float) -> float:
        if v >= 100.0:
            raise ValueError("minimum_margin_pct must be < 100 to produce a finite price")
        return v


# ---------------------------------------------------------------------------
# Price Config model
# ---------------------------------------------------------------------------


class PriceConfig(BaseModel):
    """
    Configuration object passed to pricing operations.
    target_margin_pct: if None, the engine uses bundle_profiles.minimum_margin_pct.
    """

    agent_type: str
    bundle_tier: str
    target_margin_pct: float | None = Field(
        None,
        ge=0.0,
        lt=100.0,
        description=(
            "Override margin %; if omitted the constitutional minimum from "
            "bundle_profiles is used"
        ),
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class PriceValidationRequest(BaseModel):
    """Request body for POST /pricing/validate."""

    agent_type: str = Field(..., min_length=1)
    bundle_tier: str = Field(..., min_length=1)
    proposed_price_paise: int = Field(
        ..., ge=0, description="Proposed selling price in INR paise"
    )
    idempotency_key: UUID = Field(
        default_factory=uuid4,
        description="Client-supplied idempotency key; auto-generated if omitted",
    )

    @field_validator("proposed_price_paise")
    @classmethod
    def price_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("proposed_price_paise must be ≥ 0")
        return v


class PriceDeriveRequest(BaseModel):
    """Request body for POST /pricing/derive."""

    agent_type: str = Field(..., min_length=1)
    bundle_tier: str = Field(..., min_length=1)
    target_margin_pct: float | None = Field(
        None,
        ge=0.0,
        lt=100.0,
        description=(
            "Optional override margin %; if omitted, bundle_profiles.minimum_margin_pct "
            "is used (C-089 constitutional floor)"
        ),
    )

    @model_validator(mode="after")
    def target_margin_must_allow_finite_price(self) -> PriceDeriveRequest:
        if self.target_margin_pct is not None and self.target_margin_pct >= 100.0:
            raise ValueError("target_margin_pct must be < 100")
        return self


# ---------------------------------------------------------------------------
# Response / result models
# ---------------------------------------------------------------------------


class PriceValidation(BaseModel):
    """
    Response from validate_price / POST /pricing/validate.

    Constitutional outcome of price validation against C-089 margin floor.
    Writes to pricing_floor_log on BOTH APPROVED and REJECTED outcomes (C-059).

    Fields
    ------
    outcome                           : APPROVED or REJECTED (PriceOutcome enum)
    cost_floor_paise                  : raw cost floor read from bundle_profiles
    constitutional_minimum_margin_pct : minimum_margin_pct from bundle_profiles (C-089)
    minimum_compliant_price_paise     : floor / (1 - margin/100) — the constitutional minimum
                                        derived from cost_floor_paise and margin_pct
    proposed_price_paise              : the price that was validated (from request)
    below_floor                       : True when proposed < minimum_compliant_price_paise
    margin_pct                        : effective margin % of proposed price on revenue;
                                        None when proposed_price_paise == 0 (zero-div avoidance)
    log_id                            : UUID of the pricing_floor_log record written (C-059 audit)
    logged_at                         : timestamp when audit record was created
    """

    outcome: PriceOutcome = Field(..., description="APPROVED or REJECTED")
    cost_floor_paise: int = Field(
        ..., ge=0, description="Cost floor in INR paise from bundle_profiles"
    )
    constitutional_minimum_margin_pct: float = Field(
        ..., description="Minimum margin % (C-089) from bundle_profiles"
    )
    minimum_compliant_price_paise: int = Field(
        ..., ge=0, description="Constitutional minimum derived from cost floor and margin"
    )
    proposed_price_paise: int = Field(
        ..., ge=0, description="The proposed price that was validated"
    )
    below_floor: bool = Field(
        ..., description="True if proposed < minimum_compliant_price_paise"
    )
    margin_pct: float | None = Field(
        None, description="Effective margin % of proposed price on revenue"
    )
    log_id: UUID = Field(
        ..., description="UUID of pricing_floor_log record (C-059 audit trail)"
    )
    logged_at: datetime = Field(
        ..., description="Timestamp when audit record was created"
    )


class PriceDeriveResponse(BaseModel):
    """
    Response from derive_price / POST /pricing/derive.

    Derived price using formula: floor / (1 - margin/100) where margin is
    either target_margin_pct or bundle_profiles.minimum_margin_pct (C-089).
    """

    agent_type: str = Field(..., description="Agent type from request")
    bundle_tier: str = Field(..., description="Bundle tier from request")
    cost_floor_paise: int = Field(
        ..., ge=0, description="Cost floor in INR paise from bundle_profiles"
    )
    margin_pct: float = Field(
        ..., description="Effective margin % used in derivation (requested or constitutional)"
    )
    derived_price_paise: int = Field(
        ..., ge=0, description="Derived selling price using margin-on-revenue formula"
    )