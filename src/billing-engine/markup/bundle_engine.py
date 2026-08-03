# Implements: WC027-01a — BundleEngine implementing IMarkupEngine
# constitutional_basis: C-059, C-082, C-088, C-089
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.models import PriceValidation

logger = logging.getLogger(__name__)


class BundleEngine:
    """
    BundleEngine implements IMarkupEngine for cost floor calculation,
    price derivation, and C-089 margin validation.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize BundleEngine with database session"""
        self.db = db

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        cost_floor(agent_type, bundle_tier) -> int
        Reads bundle_profiles.cost_floor_paise from DB.
        Do NOT recompute — return stored value.
        """
        query = text(
            """
            SELECT cost_floor_paise
            FROM bundle_profiles
            WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier
            """
        )
        result = await self.db.execute(
            query,
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            logger.error(
                "Bundle profile not found",
                extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            raise ValueError(
                f"Bundle profile not found for agent_type={agent_type}, bundle_tier={bundle_tier}"
            )
        return row[0]

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: int | None = None,
    ) -> int:
        """
        derive_price(agent_type, bundle_tier, target_margin_pct=None) -> int
        Formula: floor / (1 - margin/100) — margin-on-revenue.
        Uses bundle_profiles.minimum_margin_pct if target_margin_pct is None.
        """
        query = text(
            """
            SELECT cost_floor_paise, minimum_margin_pct
            FROM bundle_profiles
            WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier
            """
        )
        result = await self.db.execute(
            query,
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            logger.error(
                "Bundle profile not found",
                extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            raise ValueError(
                f"Bundle profile not found for agent_type={agent_type}, bundle_tier={bundle_tier}"
            )

        cost_floor_paise = row[0]
        minimum_margin_pct = row[1]

        margin_pct = target_margin_pct if target_margin_pct is not None else minimum_margin_pct

        if margin_pct >= 100:
            logger.error(
                "Invalid margin percentage",
                extra={"margin_pct": margin_pct},
            )
            raise ValueError(f"Margin percentage must be < 100, got {margin_pct}")

        derived_price = int(cost_floor_paise / (1 - margin_pct / 100))
        return derived_price

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        validate_price(agent_type, bundle_tier, proposed_price_paise) -> PriceValidation
        C-088: Check billing_profiles.status == FOUNDER_AUTHORIZED before validation.
        C-089: Enforce constitutional minimum margin floor.
        Writes to pricing_floor_log on BOTH APPROVED and REJECTED (C-059 audit).
        Returns minimum_compliant_price_paise in result.
        """
        # C-088: Check billing_profiles.status == FOUNDER_AUTHORIZED
        status_query = text(
            """
            SELECT status
            FROM billing_profiles
            WHERE agent_type = :agent_type
            """
        )
        status_result = await self.db.execute(
            status_query,
            {"agent_type": agent_type},
        )
        status_row = status_result.fetchone()
        if status_row is None or status_row[0] != "FOUNDER_AUTHORIZED":
            logger.error(
                "Billing profile not authorized",
                extra={"agent_type": agent_type},
            )
            raise ValueError(
                f"Billing profile for agent_type={agent_type} is not FOUNDER_AUTHORIZED"
            )

        # Get cost floor and minimum margin
        profile_query = text(
            """
            SELECT cost_floor_paise, minimum_margin_pct
            FROM bundle_profiles
            WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier
            """
        )
        profile_result = await self.db.execute(
            profile_query,
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        profile_row = profile_result.fetchone()
        if profile_row is None:
            logger.error(
                "Bundle profile not found",
                extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            raise ValueError(
                f"Bundle profile not found for agent_type={agent_type}, bundle_tier={bundle_tier}"
            )

        cost_floor_paise = profile_row[0]
        minimum_margin_pct = profile_row[1]

        # C-089: Calculate minimum compliant price using margin-on-revenue formula
        minimum_compliant_price_paise = int(
            cost_floor_paise / (1 - minimum_margin_pct / 100)
        )

        # Determine outcome
        if proposed_price_paise >= minimum_compliant_price_paise:
            outcome = "APPROVED"
        else:
            outcome = "REJECTED"

        # C-059: Write to pricing_floor_log regardless of outcome
        log_query = text(
            """
            INSERT INTO pricing_floor_log
            (agent_type, bundle_tier, proposed_price_paise, cost_floor_paise,
             minimum_margin_pct, minimum_compliant_price_paise, outcome, created_at)
            VALUES (:agent_type, :bundle_tier, :proposed_price_paise, :cost_floor_paise,
                    :minimum_margin_pct, :minimum_compliant_price_paise, :outcome, :created_at)
            """
        )
        await self.db.execute(
            log_query,
            {
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "proposed_price_paise": proposed_price_paise,
                "cost_floor_paise": cost_floor_paise,
                "minimum_margin_pct": minimum_margin_pct,
                "minimum_compliant_price_paise": minimum_compliant_price_paise,
                "outcome": outcome,
                "created_at": datetime.now(timezone.utc),
            },
        )
        await self.db.commit()

        logger.info(
            "Price validation logged",
            extra={
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "outcome": outcome,
            },
        )

        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
        )