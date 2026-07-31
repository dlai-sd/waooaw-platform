# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-01a
# constitutional_basis: C-023, C-048, C-051, C-059, C-063, C-089
from __future__ import annotations

import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone

import asyncpg

from markup.models import BundleProfile, PriceValidation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BundleProfileNotFoundError(Exception):
    """Raised when no bundle_profiles row exists for (agent_type, bundle_tier)."""


class BelowConstitutionalFloorError(Exception):
    """
    C-089: proposed price is below the constitutional minimum compliant price.
    Carries minimum_compliant_price_paise so callers can surface it in 422 bodies.
    """

    def __init__(
        self,
        proposed: int,
        minimum_compliant: int,
        cost_floor: int,
        margin_pct: float,
    ) -> None:
        self.proposed_price_paise = proposed
        self.minimum_compliant_price_paise = minimum_compliant
        self.cost_floor_paise = cost_floor
        self.constitutional_minimum_margin_pct = margin_pct
        super().__init__(
            "Proposed price %d paise is below constitutional minimum %d paise "
            "(C-089 margin floor enforced)"
            % (proposed, minimum_compliant)
        )


# ---------------------------------------------------------------------------
# BundleEngine
# ---------------------------------------------------------------------------


class BundleEngine:
    """
    Implements IMarkupEngine for the Markup Engine sub-system.

    Constitutional obligations:
      C-089 — never price below cost + minimum margin.
      C-059 — every validate_price call (APPROVED or REJECTED) writes to
               pricing_floor_log for full traceability.
      C-048 — non-exploitation: margin derivation uses margin-on-revenue formula.
      C-051 — institutional transparency: audit rows carry full context.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_bundle_profile(
        self, agent_type: str, bundle_tier: str
    ) -> BundleProfile:
        """
        Fetch bundle profile from bundle_profiles table.
        Raises BundleProfileNotFoundError if no row found.
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT agent_type,
                           bundle_tier,
                           cost_floor_paise,
                           minimum_margin_pct
                    FROM   institutional.bundle_profiles
                    WHERE  agent_type  = $1
                    AND    bundle_tier = $2
                    """,
                    agent_type,
                    bundle_tier,
                )
        except asyncio.CancelledError:
            raise
        except asyncpg.PostgresError:
            logger.error(
                "DB error fetching bundle profile for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
                extra={"context": "fetch_bundle_profile"},
            )
            raise

        if row is None:
            raise BundleProfileNotFoundError(
                "No bundle_profiles row for agent_type=%s bundle_tier=%s"
                % (agent_type, bundle_tier)
            )

        return BundleProfile(
            agent_type=row["agent_type"],
            bundle_tier=row["bundle_tier"],
            cost_floor_paise=row["cost_floor_paise"],
            minimum_margin_pct=float(row["minimum_margin_pct"]),
        )

    async def _write_pricing_floor_log(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        constitutional_minimum_margin_pct: float,
        minimum_compliant_price_paise: int,
        outcome: str,
    ) -> None:
        """
        C-059: Write audit record to pricing_floor_log.
        Called on BOTH APPROVED and REJECTED outcomes — no exceptions.
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO institutional.pricing_floor_log (
                        id,
                        agent_type,
                        bundle_tier,
                        proposed_price_paise,
                        cost_floor_paise,
                        constitutional_minimum_margin_pct,
                        minimum_compliant_price_paise,
                        outcome,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    uuid.uuid4(),
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    constitutional_minimum_margin_pct,
                    minimum_compliant_price_paise,
                    outcome,
                    datetime.now(tz=timezone.utc),
                )
        except asyncio.CancelledError:
            raise
        except asyncpg.PostgresError:
            # C-059: failure to write audit log is itself an evidence-worthy error.
            logger.error(
                "AUDIT FAILURE: could not write pricing_floor_log "
                "agent_type=%s bundle_tier=%s outcome=%s",
                agent_type,
                bundle_tier,
                outcome,
                exc_info=True,
                extra={"context": "pricing_floor_log_write"},
            )
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def cost_floor(
        self, agent_type: str, bundle_tier: str
    ) -> int:
        """
        Return cost_floor_paise for (agent_type, bundle_tier).
        Reads directly from bundle_profiles table — does NOT recompute.

        Args:
            agent_type: e.g. 'claude-opus', 'gpt-4'
            bundle_tier: e.g. 'starter', 'professional'

        Returns:
            cost_floor_paise (int)

        Raises:
            BundleProfileNotFoundError: if no bundle profile exists
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        return profile.cost_floor_paise

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        C-048: Derive price using margin-on-revenue formula.
        Formula: price = cost_floor / (1 - margin/100)

        If target_margin_pct is None, use minimum_margin_pct from bundle_profiles.

        Args:
            agent_type: e.g. 'claude-opus'
            bundle_tier: e.g. 'starter'
            target_margin_pct: override margin % (optional)

        Returns:
            Derived price in paise (int)

        Raises:
            BundleProfileNotFoundError: if no bundle profile exists
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        margin_pct = (
            target_margin_pct if target_margin_pct is not None
            else profile.minimum_margin_pct
        )

        cost_floor = profile.cost_floor_paise
        denominator = 1.0 - (margin_pct / 100.0)

        if denominator <= 0:
            logger.error(
                "Invalid margin: margin_pct=%s results in non-positive denominator",
                margin_pct,
                extra={"context": "derive_price"},
            )
            raise ValueError(
                "Margin %s pct results in invalid price derivation" % margin_pct
            )

        derived = cost_floor / denominator
        return math.ceil(derived)

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        C-089: Validate proposed_price against constitutional floor.
        Writes to pricing_floor_log on BOTH APPROVED and REJECTED.

        Formula for minimum_compliant_price:
          minimum_compliant = cost_floor / (1 - minimum_margin / 100)

        Args:
            agent_type: e.g. 'claude-opus'
            bundle_tier: e.g. 'starter'
            proposed_price_paise: candidate price in paise

        Returns:
            PriceValidation with outcome, cost_floor, minimum_compliant_price

        Raises:
            BelowConstitutionalFloorError: if proposed < minimum_compliant
                (exception carries minimum_compliant_price_paise for 422 bodies)
            BundleProfileNotFoundError: if no bundle profile exists
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)

        cost_floor = profile.cost_floor_paise
        margin_pct = profile.minimum_margin_pct
        denominator = 1.0 - (margin_pct / 100.0)

        if denominator <= 0:
            logger.error(
                "Invalid minimum_margin in profile: margin_pct=%s",
                margin_pct,
                extra={"context": "validate_price"},
            )
            raise ValueError(
                "Bundle profile minimum_margin %s pct is invalid" % margin_pct
            )

        minimum_compliant = cost_floor / denominator
        minimum_compliant_int = math.ceil(minimum_compliant)

        if proposed_price_paise < minimum_compliant_int:
            # REJECTED outcome
            outcome = "REJECTED"
            await self._write_pricing_floor_log(
                agent_type=agent_type,
                bundle_tier=bundle_tier,
                proposed_price_paise=proposed_price_paise,
                cost_floor_paise=cost_floor,
                constitutional_minimum_margin_pct=margin_pct,
                minimum_compliant_price_paise=minimum_compliant_int,
                outcome=outcome,
            )
            raise BelowConstitutionalFloorError(
                proposed=proposed_price_paise,
                minimum_compliant=minimum_compliant_int,
                cost_floor=cost_floor,
                margin_pct=margin_pct,
            )

        # APPROVED outcome
        outcome = "APPROVED"
        await self._write_pricing_floor_log(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            proposed_price_paise=proposed_price_paise,
            cost_floor_paise=cost_floor,
            constitutional_minimum_margin_pct=margin_pct,
            minimum_compliant_price_paise=minimum_compliant_int,
            outcome=outcome,
        )

        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor,
            minimum_compliant_price_paise=minimum_compliant_int,
            proposed_price_paise=proposed_price_paise,
        )