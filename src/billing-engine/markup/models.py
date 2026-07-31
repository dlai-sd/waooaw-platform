# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────


class PriceOutcome(StrEnum):
    """Constitutional price validation outcome (C-089 margin floor enforcement)."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── Request / domain models ───────────────────────────────────────────────────


class ThreadEntry(BaseModel):
    """Represents a single entry from the thread catalog."""

    thread_id: str = Field(..., description="Canonical thread identifier")
    display_name: str = Field(..., description="Human-readable thread name")
    provider: str = Field(..., description="Underlying provider (e.g. openai, ollama)")
    unit_description: str = Field(..., description="What one billing unit represents")
    raw_cost_inr_paise: int = Field(..., ge=0, description="Raw provider cost in INR paise")
    total_markup_pct: float = Field(..., ge=0.0, description="Total markup percentage applied")
    marked_up_cost_paise: int = Field(..., ge=0, description="Post-markup cost in INR paise")
    is_platform_thread: bool = Field(..., description="True if this is a WAOOAW-owned thread")
    applicable_agents: list[str] = Field(
        default_factory=list, description="Agent types this thread applies to"
    )
    status: str = Field(..., description="Thread lifecycle status (ACTIVE, DEPRECATED, …)")


class BundleProfile(BaseModel):
    """
    Mirrors the institutional.bundle_profiles DB row.
    cost_floor_paise is read from DB — never recomputed here (C-089).
    """

    agent_type: str = Field(..., description="Agent type key (e.g. DMA, PA)")
    bundle_tier: str = Field(..., description="Bundle tier label (e.g. STARTER, GROWTH, SCALE)")
    cost_floor_paise: int = Field(
        ..., ge=0, description="Platform cost floor in INR paise (DB authoritative, C-089)"
    )
    minimum_margin_pct: float = Field(
        ..., ge=0.0, lt=100.0, description="Constitutional minimum margin % (C-089)"
    )
    display_name: str = Field(default="", description="Human-readable bundle label")


class PriceConfig(BaseModel):
    """
    Holds all pricing parameters for a given agent_type + bundle_tier combination.
    Used internally by BundleEngine for price derivation.
    Constitutional: C-089 margin floor is enforced via validator.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0)
    target_margin_pct: float | None = Field(
        default=None,
        description="Override margin for derive_price(); falls back to minimum_margin_pct when None",
    )

    @model_validator(mode="after")
    def target_margin_must_not_undercut_minimum(self) -> PriceConfig:
        """C-089: target_margin_pct must not fall below constitutional minimum."""
        if (
            self.target_margin_pct is not None
            and self.target_margin_pct < self.minimum_margin_pct
        ):
            msg = (
                "target_margin_pct (%s) must not be below minimum_margin_pct (%s) — C-089 violation"
                % (self.target_margin_pct, self.minimum_margin_pct)
            )
            raise ValueError(msg)
        return self


# ── API request bodies ────────────────────────────────────────────────────────


class PriceValidationRequest(BaseModel):
    """
    Request body for POST /pricing/validate.
    C-089: validate_price() enforces margin floor against proposed_price_paise.
    """

    agent_type: str = Field(..., description="Agent type to validate pricing for")
    bundle_tier: str = Field(..., description="Bundle tier to validate pricing for")
    proposed_price_paise: int = Field(..., ge=0, description="Price proposed by caller in INR paise")


class PriceDeriveRequest(BaseModel):
    """
    Request body for POST /pricing/derive.
    target_margin_pct is optional; defaults to bundle_profiles.minimum_margin_pct.
    """

    agent_type: str = Field(..., description="Agent type to derive price for")
    bundle_tier: str = Field(..., description="Bundle tier to derive price for")
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Desired margin on revenue; uses DB minimum if omitted",
    )


# ── Response models ───────────────────────────────────────────────────────────


class PriceValidation(BaseModel):
    """
    Response from validate_price() — Amendment 2 corrected contract.
    Includes minimum_compliant_price_paise for both APPROVED and REJECTED outcomes.
    C-059: a pricing_floor_log row MUST be written for BOTH APPROVED and REJECTED.
    C-089: minimum_compliant_price_paise = cost_floor / (1 - minimum_margin_pct / 100).
    """

    validation_id: UUID = Field(default_factory=uuid4, description="Unique ID of this validation event")
    outcome: PriceOutcome = Field(..., description="APPROVED or REJECTED")
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int = Field(..., ge=0)
    cost_floor_paise: int = Field(..., ge=0, description="DB-authoritative cost floor (C-089)")
    minimum_compliant_price_paise: int = Field(
        ...,
        ge=0,
        description="Lowest price satisfying C-089: floor / (1 - minimum_margin_pct/100)",
    )
    minimum_margin_pct: float = Field(..., description="Constitutional minimum margin % from bundle_profiles")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    rejection_reason: str | None = Field(
        default=None,
        description="Human-readable reason when outcome=REJECTED; None when APPROVED",
    )


class CostFloorResponse(BaseModel):
    """
    Response for GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}.
    C-089: cost_floor_paise is DB-authoritative; never recomputed.
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float
    minimum_compliant_price_paise: int = Field(
        ...,
        ge=0,
        description="Precomputed minimum compliant price from cost floor and margin",
    )


class DerivePriceResponse(BaseModel):
    """
    Response for POST /pricing/derive.
    derived_price_paise = cost_floor / (1 - target_margin_pct / 100).
    Uses margin-on-revenue formula (C-089).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    target_margin_pct: float = Field(..., ge=0.0, lt=100.0)
    derived_price_paise: int = Field(..., ge=0, description="Derived price using margin-on-revenue formula")
    derived_at: datetime = Field(default_factory=datetime.utcnow)