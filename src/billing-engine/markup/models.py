# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PriceOutcome(StrEnum):
    """Outcome of price validation against constitutional floor."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BundleTier(StrEnum):
    """Standard billing bundle tiers per agent_type."""

    STARTER = "STARTER"
    GROWTH = "GROWTH"
    SCALE = "SCALE"
    ENTERPRISE = "ENTERPRISE"


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------


class ThreadEntry(BaseModel):
    """A single thread-catalog entry as used by the markup engine."""

    thread_id: str
    display_name: str
    provider: str
    unit_description: str
    raw_cost_inr_paise: int = Field(..., ge=0)
    total_markup_pct: float = Field(..., ge=0.0)
    marked_up_cost_paise: int = Field(..., ge=0)
    is_platform_thread: bool
    applicable_agents: list[str] = Field(default_factory=list)
    status: str

    model_config = {"frozen": True}


class BundleProfile(BaseModel):
    """
    Projection of the ``bundle_profiles`` DB row consumed by BundleEngine.

    ``cost_floor_paise`` is sourced directly from the DB column — the engine
    never recomputes it (C-089 traceability requirement).
    """

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int = Field(..., ge=0)
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0)

    model_config = {"frozen": True}


class PriceConfig(BaseModel):
    """
    Optional caller-supplied pricing parameters for ``derive_price``.

    When ``target_margin_pct`` is omitted the engine falls back to
    ``bundle_profiles.minimum_margin_pct``.
    """

    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Desired margin-on-revenue percentage (0–99.99). "
        "Omit to use the constitutional minimum.",
    )

    @field_validator("target_margin_pct")
    @classmethod
    def _validate_margin(cls, v: float | None) -> float | None:
        if v is not None and v >= 100.0:
            raise ValueError("target_margin_pct must be < 100")
        return v


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class PriceValidationRequest(BaseModel):
    """Payload for ``POST /pricing/validate``."""

    agent_type: str = Field(..., min_length=1)
    bundle_tier: str = Field(..., min_length=1)
    proposed_price_paise: int = Field(..., ge=0)

    model_config = {"frozen": True}


class PriceDeriveRequest(BaseModel):
    """Payload for ``POST /pricing/derive``."""

    agent_type: str = Field(..., min_length=1)
    bundle_tier: str = Field(..., min_length=1)
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Desired margin-on-revenue %. Omit to use constitutional minimum.",
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class PriceValidation(BaseModel):
    """
    Response from ``validate_price`` (and ``POST /pricing/validate``).

    Includes all fields required by Amendment 2 + C-059 audit obligation:
    - ``outcome``                    — APPROVED or REJECTED
    - ``cost_floor_paise``           — raw cost floor from DB
    - ``minimum_compliant_price_paise`` — floor / (1 - min_margin/100), ceiling int
    - ``proposed_price_paise``       — echoed from request
    - ``log_id``                     — UUID of the ``pricing_floor_log`` row written
    - ``evaluated_at``               — UTC timestamp of evaluation
    """

    outcome: PriceOutcome
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int
    cost_floor_paise: int
    minimum_compliant_price_paise: int
    log_id: UUID = Field(default_factory=uuid4)
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    rejection_reason: str | None = None

    model_config = {"frozen": True}


class DerivedPrice(BaseModel):
    """Response from ``derive_price`` (and ``GET /pricing/bundle-cost-floor`` + ``POST /pricing/derive``)."""

    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    applied_margin_pct: float
    derived_price_paise: int

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Exception Types
# ---------------------------------------------------------------------------


class BelowConstitutionalFloorError(ValueError):
    """
    Raised by ``BundleEngine.validate_price`` when ``proposed_price_paise``
    is below ``minimum_compliant_price_paise``.

    C-089: the platform MUST never price below constitutional margin floor.
    """

    def __init__(
        self,
        proposed: int,
        minimum_compliant: int,
        agent_type: str,
        bundle_tier: str,
    ) -> None:
        self.proposed = proposed
        self.minimum_compliant = minimum_compliant
        self.agent_type = agent_type
        self.bundle_tier = bundle_tier
        super().__init__(
            f"Proposed price {proposed} paise is below constitutional minimum "
            f"{minimum_compliant} paise for {agent_type}/{bundle_tier} (C-089)."
        )


class BundleProfileNotFoundError(KeyError):
    """Raised when no ``bundle_profiles`` row matches (agent_type, bundle_tier)."""

    def __init__(self, agent_type: str, bundle_tier: str) -> None:
        self.agent_type = agent_type
        self.bundle_tier = bundle_tier
        super().__init__(
            f"No bundle_profiles entry for {agent_type}/{bundle_tier}."
        )