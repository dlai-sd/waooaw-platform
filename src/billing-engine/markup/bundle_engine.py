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
                f"No bundle_profiles row for agent_type={agent_type} bundle_tier={bundle_tier}"
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
    # Public API — IMarkupEngine surface
    # ------------------------------------------------------------------

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Return the cost floor in paise for the given (agent_type, bundle_tier).

        Reads bundle_profiles.cost_floor_paise from the database — does NOT
        recompute the value from any constituent cost inputs.  This is the
        single source of truth mandated by the thread catalog (D-06).

        Raises:
            BundleProfileNotFoundError: no row in bundle_profiles for the pair.
            asyncpg.PostgresError: unrecoverable database error.
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        return profile.cost_floor_paise

    # IMarkupEngine alias expected by skeleton
    async def derive_bundle_cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """Alias satisfying IMarkupEngine.derive_bundle_cost_floor contract."""
        return await self.cost_floor(agent_type, bundle_tier)

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        Derive a compliant selling price in paise.

        Formula (margin-on-revenue, C-048):
            price = floor / (1 - margin / 100)

        where ``margin`` is ``target_margin_pct`` when supplied, otherwise
        ``bundle_profiles.minimum_margin_pct``.

        The result is rounded UP (math.ceil) so that the implied margin never
        falls below the constitutional minimum.

        Raises:
            BundleProfileNotFoundError: no row in bundle_profiles.
            ValueError: target_margin_pct is not in (0, 100).
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)

        if target_margin_pct is not None:
            if not (0.0 < target_margin_pct < 100.0):
                raise ValueError(
                    f"target_margin_pct must be in open interval (0, 100), got {target_margin_pct}"
                )
            margin = target_margin_pct
        else:
            margin = profile.minimum_margin_pct

        # Margin-on-revenue: price = floor / (1 - margin/100)
        price_exact = profile.cost_floor_paise / (1.0 - margin / 100.0)
        return math.ceil(price_exact)

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validate a proposed price against the C-089 constitutional margin floor.

        Behaviour:
          • Fetches bundle profile (cost_floor_paise, minimum_margin_pct).
          • Computes minimum_compliant_price_paise using the margin-on-revenue
            formula (same as derive_price).
          • Writes ONE row to pricing_floor_log regardless of outcome (C-059).
          • Returns a PriceValidation with outcome APPROVED or REJECTED.
          • Raises BelowConstitutionalFloorError on REJECTED so the FastAPI
            router can surface minimum_compliant_price_paise in the 422 body.

        Raises:
            BundleProfileNotFoundError: no row in bundle_profiles.
            BelowConstitutionalFloorError: proposed price violates C-089 floor.
            asyncpg.PostgresError: unrecoverable database error (after logging).
        """
        profile = await self._fetch_bundle_profile(agent_type, bundle_tier)

        margin = profile.minimum_margin_pct
        minimum_compliant_price_paise = math.ceil(
            profile.cost_floor_paise / (1.0 - margin / 100.0)
        )

        approved = proposed_price_paise >= minimum_compliant_price_paise
        outcome = "APPROVED" if approved else "REJECTED"

        # C-059: write audit record unconditionally — BOTH outcomes.
        await self._write_pricing_floor_log(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            proposed_price_paise=proposed_price_paise,
            cost_floor_paise=profile.cost_floor_paise,
            constitutional_minimum_margin_pct=margin,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            outcome=outcome,
        )

        result = PriceValidation(
            outcome=outcome,
            cost_floor_paise=profile.cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
        )

        if not approved:
            # C-089: surface the violation with full context for the caller.
            raise BelowConstitutionalFloorError(
                proposed=proposed_price_paise,
                minimum_compliant=minimum_compliant_price_paise,
                cost_floor=profile.cost_floor_paise,
                margin_pct=margin,
            )

        return result