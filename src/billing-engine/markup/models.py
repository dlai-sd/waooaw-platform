# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-01a
# constitutional_basis: C-023, C-048, C-051, C-059, C-063
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PriceOutcome(StrEnum):
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
    """

    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier (e.g. STARTER, PRO, ENTERPRISE)")
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
    def target_margin_must_allow_finite_price(self) -> "PriceDeriveRequest":
        if self.target_margin_pct is not None and self.target_margin_pct >= 100.0:
            raise ValueError("target_margin_pct must be < 100")
        return self


# ---------------------------------------------------------------------------
# Response / result models
# ---------------------------------------------------------------------------


class PriceValidation(BaseModel):
    """
    Response from validate_price / POST /pricing/validate.

    Fields
    ------
    outcome                           : APPROVED or REJECTED
    cost_floor_paise                  : raw cost floor read from bundle_profiles
    constitutional_minimum_margin_pct : minimum_margin_pct from bundle_profiles
    minimum_compliant_price_paise     : floor / (1 - margin/100) — the constitutional minimum
    proposed_price_paise              : the price that was validated
    below_floor                       : True when proposed < minimum_compliant_price_paise
    margin_pct                        : effective margin of proposed price on revenue (may be
                                        None when proposed_price_paise == 0 to avoid zero-div)
    log_id                            : UUID of the pricing_floor_log row written (C-059)
    evaluated_at                      : UTC timestamp of evaluation
    """

    outcome: PriceOutcome
    cost_floor_paise: int
    constitutional_minimum_margin_pct: float
    minimum_compliant_price_paise: int
    proposed_price_paise: int
    below_floor: bool
    margin_pct: float | None = Field(
        None,
        description=(
            "Effective margin % of proposed price on revenue; "
            "None when proposed_price_paise is 0"
        ),
    )
    log_id: UUID = Field(
        ...,
        description="UUID of the pricing_floor_log row written for C-059 audit",
    )
    evaluated_at: datetime = Field(
        ...,
        description="UTC timestamp at which the validation was evaluated",
    )


# ---------------------------------------------------------------------------
# Derive result model
# ---------------------------------------------------------------------------


class PriceDeriveResult(BaseModel):
    """
    Response from derive_price / POST /pricing/derive.

    Fields
    ------
    agent_type           : as supplied
    bundle_tier          : as supplied
    cost_floor_paise     : raw cost floor read from bundle_profiles (C-089)
    applied_margin_pct   : margin actually used (override or constitutional minimum)
    derived_price_paise  : floor / (1 - margin/100) — margin-on-revenue formula
    is_constitutional_minimum : True when target_margin_pct was None and the
                                constitutional minimum was applied
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    applied_margin_pct: float
    derived_price_paise: int
    is_constitutional_minimum: bool = Field(
        ...,
        description=(
            "True when no target_margin_pct override was supplied and the "
            "bundle_profiles.minimum_margin_pct was used"
        ),
    )


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BelowConstitutionalFloorError(ValueError):
    """
    Raised by validate_price when proposed_price_paise is below the
    constitutional minimum compliant price (C-089 margin floor violation).

    Attributes
    ----------
    proposed_price_paise          : the price submitted for validation
    minimum_compliant_price_paise : the C-089 constitutional minimum
    cost_floor_paise              : underlying cost floor from bundle_profiles
    constitutional_minimum_margin_pct : minimum margin from bundle_profiles
    """

    def __init__(
        self,
        proposed_price_paise: int,
        minimum_compliant_price_paise: int,
        cost_floor_paise: int,
        constitutional_minimum_margin_pct: float,
    ) -> None:
        self.proposed_price_paise = proposed_price_paise
        self.minimum_compliant_price_paise = minimum_compliant_price_paise
        self.cost_floor_paise = cost_floor_paise
        self.constitutional_minimum_margin_pct = constitutional_minimum_margin_pct
        super().__init__(
            f"Proposed price {proposed_price_paise} paise is below the "
            f"constitutional minimum of {minimum_compliant_price_paise} paise "
            f"(C-089 margin floor: {constitutional_minimum_margin_pct}%)"
        )


class BundleProfileNotFoundError(KeyError):
    """
    Raised when no bundle_profiles row exists for the requested
    (agent_type, bundle_tier) combination.
    """

    def __init__(self, agent_type: str, bundle_tier: str) -> None:
        self.agent_type = agent_type
        self.bundle_tier = bundle_tier
        # Avoid logging PII — agent_type/bundle_tier are structural, not PII (C-063)
        super().__init__(
            f"No bundle profile found for agent_type={agent_type!r}, "
            f"bundle_tier={bundle_tier!r}"
        )