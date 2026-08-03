# Implements: WC027-01a — Pydantic models for Markup Engine
# constitutional_basis: C-059, C-089

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
import logging
from datetime import datetime, timezone
from math import floor
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from markup.models import BundleProfile, PriceValidation, PricingOutcome


class PricingOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ThreadEntry(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    description: str = Field(default="", description="Human-readable description")
    base_cost_paise: int = Field(..., ge=0, description="Base cost in paise")
    is_active: bool = Field(default=True, description="Whether this thread entry is active")


class BundleProfile(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    cost_floor_paise: int = Field(..., ge=0, description="Cost floor in paise (read from DB)")
    minimum_margin_pct: float = Field(..., ge=0.0, lt=100.0, description="Minimum margin percentage")


class PriceConfig(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Target margin percentage; uses bundle minimum if None",
    )


class PriceValidationRequest(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    proposed_price_paise: int = Field(..., ge=0, description="Proposed price in paise")


class PriceDeriveRequest(BaseModel):
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    target_margin_pct: float | None = Field(
        default=None,
        ge=0.0,
        lt=100.0,
        description="Target margin percentage; uses bundle minimum if None",
    )


class PriceValidation(BaseModel):
    outcome: PricingOutcome = Field(..., description="APPROVED or REJECTED")
    cost_floor_paise: int = Field(..., ge=0, description="Cost floor in paise")
    minimum_compliant_price_paise: int = Field(
        ..., ge=0, description="Minimum price that satisfies margin floor"
    )
    proposed_price_paise: int = Field(..., ge=0, description="The proposed price that was validated")
    agent_type: str = Field(..., description="Agent type identifier")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    margin_pct_applied: float = Field(..., description="Margin percentage used for validation")

# src/billing-engine/markup/models.py — module-level initialization
# (No module-level initialization required for models.py — it contains only Pydantic classes)
# src/billing-engine/markup/bundle_engine.py — module-level initialization
# Implements: WC027-01a — BundleEngine implementation
# constitutional_basis: C-059, C-089
logger = logging.getLogger(__name__)
class BundleEngine:
    """Implements IMarkupEngine: cost floor calculation, price derivation, C-089 validation."""
    def __init__(self, session: AsyncSession) -> None:
        """Initialize BundleEngine with async database session.
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """Read cost floor from bundle_profiles table.
        Args:
            agent_type: Agent type identifier
            bundle_tier: Bundle tier identifier
        Returns:
            Cost floor in paise
        Raises:
            ValueError: If bundle profile not found
        """
        result = await self.session.execute(
            text(
                "SELECT cost_floor_paise FROM bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if not row:
            logger.error(
                "Bundle profile not found",
                extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            raise ValueError(f"Bundle profile not found for {agent_type}/{bundle_tier}")
        return int(row[0])
    async def derive_price(
        self, agent_type: str, bundle_tier: str, target_margin_pct: float | None = None
    ) -> int:
        """Derive price using margin-on-revenue formula: floor / (1 - margin/100).
        Args:
            agent_type: Agent type identifier
            bundle_tier: Bundle tier identifier
            target_margin_pct: Target margin percentage; uses bundle minimum if None
        Returns:
            Derived price in paise
        Raises:
            ValueError: If bundle profile not found or margin invalid
        """
        result = await self.session.execute(
            text(
                "SELECT cost_floor_paise, minimum_margin_pct FROM bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if not row:
            logger.error(
                "Bundle profile not found for price derivation",
                extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            raise ValueError(f"Bundle profile not found for {agent_type}/{bundle_tier}")
        cost_floor_paise = int(row[0])
        minimum_margin_pct = float(row[1])
        margin_to_use = target_margin_pct if target_margin_pct is not None else minimum_margin_pct
        if margin_to_use >= 100.0:
            logger.error(
                "Invalid margin percentage",
                extra={"margin_pct": margin_to_use, "agent_type": agent_type},
            )
            raise ValueError(f"Margin must be < 100%, got {margin_to_use}")
        derived_price = floor(cost_floor_paise / (1 - margin_to_use / 100))
        logger.info(
            "Price derived",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "margin_pct": margin_to_use,
                "derived_price_paise": derived_price,
            },
        )
        return derived_price
    async def validate_price(
        self, agent_type: str, bundle_tier: str, proposed_price_paise: int
    ) -> PriceValidation:
        """Validate proposed price against cost floor (C-089).
        Writes to pricing_floor_log on both APPROVED and REJECTED outcomes.
        Args:
            agent_type: Agent type identifier
            bundle_tier: Bundle tier identifier
            proposed_price_paise: Proposed price in paise
        Returns:
            PriceValidation with outcome, cost_floor, minimum_compliant_price, margin_applied
        Raises:
            ValueError: If bundle profile not found
        """
        result = await self.session.execute(
            text(
                "SELECT cost_floor_paise, minimum_margin_pct FROM bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if not row:
            logger.error(
                "Bundle profile not found for validation",
                extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            raise ValueError(f"Bundle profile not found for {agent_type}/{bundle_tier}")
        cost_floor_paise = int(row[0])
        minimum_margin_pct = float(row[1])
        minimum_compliant_price = floor(cost_floor_paise / (1 - minimum_margin_pct / 100))
        if proposed_price_paise >= minimum_compliant_price:
            outcome = PricingOutcome.APPROVED
            margin_achieved = (
                (proposed_price_paise - cost_floor_paise) / proposed_price_paise * 100
                if proposed_price_paise > 0
                else 0.0
            )
        else:
            outcome = PricingOutcome.REJECTED
            margin_achieved = minimum_margin_pct
        await self.session.execute(
            text(
                "INSERT INTO pricing_floor_log "
                "(agent_type, bundle_tier, proposed_price_paise, cost_floor_paise, "
                "minimum_compliant_price_paise, outcome, margin_pct_applied, created_at) "
                "VALUES (:agent_type, :bundle_tier, :proposed_price_paise, :cost_floor_paise, "
                ":minimum_compliant_price_paise, :outcome, :margin_pct_applied, :created_at)"
            ),
            {
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "proposed_price_paise": proposed_price_paise,
                "cost_floor_paise": cost_floor_paise,
                "minimum_compliant_price_paise": minimum_compliant_price,
                "outcome": outcome.value,
                "margin_pct_applied": margin_achieved,
                "created_at": datetime.now(timezone.utc),
            },
        )
        await self.session.commit()
        logger.info(
            "Price validation logged",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "outcome": outcome.value,
                "proposed_price_paise": proposed_price_paise,
            },
        )
        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_price,
            proposed_price_paise=proposed_price_paise,
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            margin_pct_applied=margin_achieved,
        )
