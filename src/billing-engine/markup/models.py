# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    """Constitutional outcome of a price validation against C-089 margin floor."""

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
    outcome                      : APPROVED or REJECTED (C-089 gate result)
    cost_floor_paise             : raw cost floor from bundle_profiles
    minimum_compliant_price_paise: lowest price that satisfies C-089 margin floor
    proposed_price_paise         : the price the caller proposed
    log_id                       : UUID of the pricing_floor_log row written (C-059)
    evaluated_at                 : UTC timestamp of the evaluation
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


# ── Domain exceptions ─────────────────────────────────────────────────────────


class BelowConstitutionalFloorError(ValueError):
    """
    Raised by BundleEngine.validate_price() when proposed_price_paise is below
    the minimum compliant price derived from bundle_profiles.minimum_margin_pct.

    C-089: Margin Floor — the platform MUST never price below cost-plus-minimum-margin.

    Attributes
    ----------
    proposed_price_paise         : price the caller proposed
    minimum_compliant_price_paise: the lowest price that satisfies C-089
    cost_floor_paise             : raw cost floor from bundle_profiles
    log_id                       : UUID of the pricing_floor_log row written for audit (C-059)
    """

    def __init__(
        self,
        proposed_price_paise: int,
        minimum_compliant_price_paise: int,
        cost_floor_paise: int,
        log_id: UUID,
    ) -> None:
        self.proposed_price_paise = proposed_price_paise
        self.minimum_compliant_price_paise = minimum_compliant_price_paise
        self.cost_floor_paise = cost_floor_paise
        self.log_id = log_id
        super().__init__(
            f"Proposed price {proposed_price_paise} paise is below the constitutional "
            f"minimum compliant price {minimum_compliant_price_paise} paise "
            f"(cost floor {cost_floor_paise} paise). "
            f"C-089 violation recorded in pricing_floor_log row {log_id}."
        )


class BundleProfileNotFoundError(KeyError):
    """
    Raised when no bundle_profiles row exists for the given (agent_type, bundle_tier).

    This is a data-integrity signal — bundle profiles must be seeded before pricing
    operations are attempted.
    """

    def __init__(self, agent_type: str, bundle_tier: str) -> None:
        self.agent_type = agent_type
        self.bundle_tier = bundle_tier
        super().__init__(
            f"No bundle_profiles row found for agent_type={agent_type!r}, "
            f"bundle_tier={bundle_tier!r}. "
            "Ensure DB migration and seed data have been applied."
        )