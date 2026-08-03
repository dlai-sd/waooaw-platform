# Implements: WC027-01a — BundleEngine implementing IMarkupEngine
# constitutional_basis: C-059, C-089

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.models import PriceValidation, PricingOutcome

logger = logging.getLogger(__name__)


class BelowConstitutionalFloorError(Exception):
    """Raised when a proposed price violates the constitutional minimum margin floor (C-089)."""

    def __init__(self, message: str, validation: PriceValidation) -> None:
        super().__init__(message)
        self.validation = validation


class BundleEngine:
    """
    Implements IMarkupEngine for bundle cost floor calculation, price derivation,
    and price validation with C-089 margin gate and C-059 audit logging.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Read cost_floor_paise from bundle_profiles for the given agent_type and bundle_tier.
        Does NOT recompute — reads the stored value directly (ADR-036).
        """
        result = await self._db.execute(
            text(
                "SELECT cost_floor_paise FROM bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError(
                f"No bundle profile found for agent_type={agent_type!r}, bundle_tier={bundle_tier!r}"
            )
        return int(row[0])

    async def _minimum_margin_pct(self, agent_type: str, bundle_tier: str) -> float:
        """Read minimum_margin_pct from bundle_profiles."""
        result = await self._db.execute(
            text(
                "SELECT minimum_margin_pct FROM bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError(
                f"No bundle profile found for agent_type={agent_type!r}, bundle_tier={bundle_tier!r}"
            )
        return float(row[0])

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        Derive price using margin-on-revenue formula: floor / (1 - margin/100).
        Uses bundle_profiles.minimum_margin_pct if target_margin_pct is None.
        Returns price in paise (int), floored per margin formula convention.
        """
        floor = await self.cost_floor(agent_type, bundle_tier)

        if target_margin_pct is None:
            margin = await self._minimum_margin_pct(agent_type, bundle_tier)
        else:
            margin = target_margin_pct

        if margin < 0.0 or margin >= 100.0:
            raise ValueError("margin_pct must be in [0, 100)")

        # Margin-on-revenue formula: floor / (1 - margin/100), floored to int
        price = math.floor(floor / (1.0 - margin / 100.0))
        return price

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validate proposed_price_paise against the constitutional minimum margin floor (C-089).
        Writes an audit row to pricing_floor_log on BOTH APPROVED and REJECTED outcomes (C-059).
        Raises BelowConstitutionalFloorError if the price is below the minimum compliant price.
        """
        floor = await self.cost_floor(agent_type, bundle_tier)
        margin = await self._minimum_margin_pct(agent_type, bundle_tier)

        # Minimum compliant price using margin-on-revenue formula
        minimum_compliant_price_paise = math.floor(floor / (1.0 - margin / 100.0))

        if proposed_price_paise >= minimum_compliant_price_paise:
            outcome = PricingOutcome.APPROVED
        else:
            outcome = PricingOutcome.REJECTED

        validation = PriceValidation(
            outcome=outcome,
            cost_floor_paise=floor,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            margin_pct_applied=margin,
        )

        # C-059: write audit record for BOTH outcomes — PII must not appear in log
        await self._write_floor_log(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            proposed_price_paise=proposed_price_paise,
            cost_floor_paise=floor,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            margin_pct_applied=margin,
            outcome=outcome,
        )

        if outcome == PricingOutcome.REJECTED:
            raise BelowConstitutionalFloorError(
                "Proposed price is below the constitutional minimum margin floor (C-089)",
                validation,
            )

        return validation

    async def _write_floor_log(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        margin_pct_applied: float,
        outcome: PricingOutcome,
    ) -> None:
        """
        Write an audit row to pricing_floor_log (C-059).
        No PII is logged here (C-063).
        """
        now = datetime.now(timezone.utc)
        await self._db.execute(
            text(
                "INSERT INTO pricing_floor_log "
                "(agent_type, bundle_tier, proposed_price_paise, cost_floor_paise, "
                "minimum_compliant_price_paise, margin_pct_applied, outcome, logged_at) "
                "VALUES "
                "(:agent_type, :bundle_tier, :proposed_price_paise, :cost_floor_paise, "
                ":minimum_compliant_price_paise, :margin_pct_applied, :outcome, :logged_at)"
            ),
            {
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "proposed_price_paise": proposed_price_paise,
                "cost_floor_paise": cost_floor_paise,
                "minimum_compliant_price_paise": minimum_compliant_price_paise,
                "margin_pct_applied": margin_pct_applied,
                "outcome": str(outcome),
                "logged_at": now,
            },
        )
        await self._db.commit()
        logger.info(
            "pricing_floor_log written: outcome=%s agent_type=%s bundle_tier=%s",
            outcome,
            agent_type,
            bundle_tier,
        )