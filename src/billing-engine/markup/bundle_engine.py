# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-01a
# constitutional_basis: C-023, C-048, C-051, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

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
        except asyncpg.PostgresError as exc:
            logger.error(
                "DB error fetching bundle profile for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
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
        except asyncpg.PostgresError as exc:
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
    # IMarkupEngine implementation
    # ------------------------------------------------------------------

    async def derive_bundle_cost_floor(
        self, agent_type: str, bundle_tier: str
    ) -> int:
        """
        Return cost_floor_paise as stored in bundle_profiles.
        DO NOT recompute — read the persisted value (spec: WC027-01a).

        Returns:
            cost_floor_paise (int) — floor in INR paise.

        Raises:
            BundleProfileNotFoundError — if (agent_type, bundle_tier) not found.
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        logger.info(
            "cost_floor fetched agent_type=%s bundle_tier=%s floor_paise=%s",
            agent_type,
            bundle_tier,
            profile.cost_floor_paise,
        )
        return profile.cost_floor_paise

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        Derive selling price using margin-on-revenue formula:
            derived_price = cost_floor / (1 - margin / 100)

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Returns:
            Derived price in INR paise (ceiling-rounded to whole paise).

        Raises:
            BundleProfileNotFoundError — if profile row missing.
            ValueError — if effective margin >= 100 (division by zero guard).
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        effective_margin = (
            target_margin_pct
            if target_margin_pct is not None
            else profile.minimum_margin_pct
        )

        if effective_margin >= 100.0:
            raise ValueError(
                "effective_margin_pct must be < 100, got %s" % effective_margin
            )
        if effective_margin < 0.0:
            raise ValueError(
                "effective_margin_pct must be >= 0, got %s" % effective_margin
            )

        divisor = 1.0 - (effective_margin / 100.0)
        raw_price = profile.cost_floor_paise / divisor
        derived_price = math.ceil(raw_price)

        logger.info(
            "derive_price agent_type=%s bundle_tier=%s margin_pct=%s "
            "floor_paise=%s derived_paise=%s",
            agent_type,
            bundle_tier,
            effective_margin,
            profile.cost_floor_paise,
            derived_price,
        )
        return derived_price

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validate a proposed price against the C-089 constitutional margin floor.

        Steps:
          1. Fetch bundle_profiles row.
          2. Compute minimum_compliant_price_paise = ceil(floor / (1 - min_margin/100)).
          3. Determine outcome: APPROVED or REJECTED.
          4. C-059: Write audit row to pricing_floor_log (always — both outcomes).
          5. If REJECTED, raise BelowConstitutionalFloorError (caller converts to 422).
          6. Return PriceValidation.

        Returns:
            PriceValidation — populated with outcome and all audit fields.

        Raises:
            BundleProfileNotFoundError — if profile row missing.
            BelowConstitutionalFloorError — C-089 violation (price below floor).
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)

        divisor = 1.0 - (profile.minimum_margin_pct / 100.0)
        minimum_compliant_price_paise = math.ceil(
            profile.cost_floor_paise / divisor
        )

        approved = proposed_price_paise >= minimum_compliant_price_paise
        outcome = "APPROVED" if approved else "REJECTED"

        # C-059: audit write on BOTH outcomes — mandatory, non-negotiable.
        await self._write_pricing_floor_log(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            proposed_price_paise=proposed_price_paise,
            cost_floor_paise=profile.cost_floor_paise,
            constitutional_minimum_margin_pct=profile.minimum_margin_pct,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            outcome=outcome,
        )

        if not approved:
            logger.warning(
                "C-089 violation: proposed_paise=%s minimum_compliant_paise=%s "
                "agent_type=%s bundle_tier=%s outcome=REJECTED",
                proposed_price_paise,
                minimum_compliant_price_paise,
                agent_type,
                bundle_tier,
            )
            raise BelowConstitutionalFloorError(
                proposed=proposed_price_paise,
                minimum_compliant=minimum_compliant_price_paise,
                cost_floor=profile.cost_floor_paise,
                margin_pct=profile.minimum_margin_pct,
            )

        actual_margin_pct: float | None = None
        if proposed_price_paise > 0:
            actual_margin_pct = (
                (proposed_price_paise - profile.cost_floor_paise)
                / proposed_price_paise
            ) * 100.0

        logger.info(
            "validate_price APPROVED agent_type=%s bundle_tier=%s "
            "proposed_paise=%s margin_pct=%s",
            agent_type,
            bundle_tier,
            proposed_price_paise,
            actual_margin_pct,
        )

        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=profile.cost_floor_paise,
            constitutional_minimum_margin_pct=profile.minimum_margin_pct,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
            below_floor=False,
            margin_pct=actual_margin_pct,
        )