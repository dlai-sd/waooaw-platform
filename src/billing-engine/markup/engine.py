# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-02
# constitutional_basis: C-023, C-059, C-063, C-088, C-089
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from billing_engine.skeleton.wbe_interfaces import IMarkupEngine
from billing_engine.models import (
    BundleProfile,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    PricingOutcome,
)
from billing_engine.database import PricingFloorLog

logger = logging.getLogger(__name__)


class BelowConstitutionalFloorError(Exception):
    """Raised when proposed price violates C-089 margin floor."""
    pass


class BundleEngine(IMarkupEngine):
    """
    Markup Engine: cost floor calculation, price derivation, C-089 margin gate.
    
    Constitutional:
      C-089: Margin floor — never price below cost + minimum margin (margin-on-revenue).
      C-059: Traceability — all price validations logged to pricing_floor_log.
      C-063: PII protection — no customer identifiers in logs.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize BundleEngine with database session.
        
        Args:
            session: AsyncSession for database access.
        """
        self.session = session

    async def derive_bundle_cost_floor(
        self,
        agent_type: str,
        bundle_tier: str,
    ) -> int:
        """
        Derive cost floor (in INR paise) from bundle_profiles.
        
        Reads institutional.bundle_profiles.cost_floor_paise directly.
        Does NOT recompute — returns stored value.
        
        Args:
            agent_type: Thread catalog agent type (e.g., 'OPENAI_GPT4').
            bundle_tier: Bundle tier (e.g., 'STARTER', 'PRO').
        
        Returns:
            Cost floor in INR paise (int).
        
        Raises:
            ValueError: If bundle profile not found.
        """
        stmt = select(BundleProfile).where(
            (BundleProfile.agent_type == agent_type) &
            (BundleProfile.bundle_tier == bundle_tier)
        )
        result = await self.session.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if profile is None:
            logger.error(
                "Bundle profile not found",
                extra={
                    "agent_type": agent_type,
                    "bundle_tier": bundle_tier,
                }
            )
            raise ValueError(
                f"Bundle profile not found: agent_type={agent_type}, "
                f"bundle_tier={bundle_tier}"
            )
        
        logger.info(
            "Cost floor retrieved from bundle_profiles",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "cost_floor_paise": profile.cost_floor_paise,
            }
        )
        return profile.cost_floor_paise

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: Optional[float] = None,
    ) -> int:
        """
        Derive price using margin-on-revenue formula.
        
        Formula: price = floor / (1 - margin/100)
        
        Uses bundle_profiles.minimum_margin_pct if target_margin_pct is None.
        
        Args:
            agent_type: Thread catalog agent type.
            bundle_tier: Bundle tier.
            target_margin_pct: Target margin percentage (margin-on-revenue).
                              If None, uses minimum_margin_pct from bundle_profiles.
        
        Returns:
            Derived price in INR paise (int).
        
        Raises:
            ValueError: If bundle profile not found or margin >= 100.
        """
        stmt = select(BundleProfile).where(
            (BundleProfile.agent_type == agent_type) &
            (BundleProfile.bundle_tier == bundle_tier)
        )
        result = await self.session.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if profile is None:
            logger.error(
                "Bundle profile not found for price derivation",
                extra={
                    "agent_type": agent_type,
                    "bundle_tier": bundle_tier,
                }
            )
            raise ValueError(
                f"Bundle profile not found: agent_type={agent_type}, "
                f"bundle_tier={bundle_tier}"
            )
        
        cost_floor = profile.cost_floor_paise
        margin = target_margin_pct if target_margin_pct is not None else profile.minimum_margin_pct
        
        if margin >= 100:
            logger.error(
                "Invalid margin percentage for price derivation",
                extra={
                    "agent_type": agent_type,
                    "bundle_tier": bundle_tier,
                    "margin_pct": margin,
                }
            )
            raise ValueError(f"Margin must be < 100%, got {margin}%")
        
        # Margin-on-revenue: price = floor / (1 - margin/100)
        divisor = 1.0 - (margin / 100.0)
        derived_price = int(cost_floor / divisor)
        
        logger.info(
            "Price derived using margin-on-revenue formula",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "cost_floor_paise": cost_floor,
                "margin_pct": margin,
                "derived_price_paise": derived_price,
            }
        )
        return derived_price

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validate proposed price against C-089 margin floor.
        
        Writes to institutional.pricing_floor_log regardless of outcome.
        
        Formula: minimum_compliant_price = floor / (1 - minimum_margin/100)
        
        Args:
            agent_type: Thread catalog agent type.
            bundle_tier: Bundle tier.
            proposed_price_paise: Proposed price in INR paise.
        
        Returns:
            PriceValidation with outcome, cost_floor_paise, 
            minimum_compliant_price_paise, proposed_price_paise.
        
        Raises:
            BelowConstitutionalFloorError: If proposed price < minimum compliant price.
                                          (Caller catches and returns 422.)
        """
        stmt = select(BundleProfile).where(
            (BundleProfile.agent_type == agent_type) &
            (BundleProfile.bundle_tier == bundle_tier)
        )
        result = await self.session.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if profile is None:
            logger.error(
                "Bundle profile not found for price validation",
                extra={
                    "agent_type": agent_type,
                    "bundle_tier": bundle_tier,
                }
            )
            raise ValueError(
                f"Bundle profile not found: agent_type={agent_type}, "
                f"bundle_tier={bundle_tier}"
            )
        
        cost_floor = profile.cost_floor_paise
        minimum_margin_pct = profile.minimum_margin_pct
        
        # Calculate minimum compliant price using margin-on-revenue
        divisor = 1.0 - (minimum_margin_pct / 100.0)
        minimum_compliant_price = int(cost_floor / divisor)
        
        # Determine outcome: APPROVED if proposed >= minimum, else REJECTED
        is_valid = proposed_price_paise >= minimum_compliant_price
        outcome = PricingOutcome.APPROVED if is_valid else PricingOutcome.REJECTED
        
        # Log to pricing_floor_log (C-059 audit obligation)
        log_entry = PricingFloorLog(
            proposed_price_paise=proposed_price_paise,
            cost_floor_paise=cost_floor,
            constitutional_minimum_margin_pct=minimum_margin_pct,
            minimum_compliant_price_paise=minimum_compliant_price,
            outcome=outcome.value,
            validated_at=datetime.utcnow(),
        )
        self.session.add(log_entry)
        await self.session.flush()
        
        logger.info(
            "Price validation logged",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "cost_floor_paise": cost_floor,
                "minimum_margin_pct": minimum_margin_pct,
                "proposed_price_paise": proposed_price_paise,
                "minimum_compliant_price_paise": minimum_compliant_price,
                "outcome": outcome.value,
            }
        )
        
        # Raise exception if below constitutional floor (caller returns 422)
        if not is_valid:
            raise BelowConstitutionalFloorError(
                f"Proposed price {proposed_price_paise} paise is below "
                f"minimum compliant price {minimum_compliant_price} paise "
                f"(C-089 margin floor violation)"
            )
        
        # Return validation result (200 path)
        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor,
            minimum_compliant_price_paise=minimum_compliant_price,
            proposed_price_paise=proposed_price_paise,
            margin_pct=minimum_margin_pct,
        )