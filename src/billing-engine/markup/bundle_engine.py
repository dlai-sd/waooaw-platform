# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from markup.models import PriceOutcome, PriceValidation

logger = logging.getLogger(__name__)

# -- DB engine (shared singleton) ---------------------------------------------
_engine: Any = None
_async_session: sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> sessionmaker[AsyncSession]:
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session  # type: ignore[return-value]


# -- Custom exceptions --------------------------------------------------------


class BelowConstitutionalFloorError(ValueError):
    """Raised when proposed_price_paise is below the constitutional margin floor.

    C-089: Platform must never price below cost + minimum margin.
    """

    def __init__(
        self: BelowConstitutionalFloorError,
        proposed: int,
        minimum_compliant: int,
        cost_floor: int,
        margin_pct: float,
    ) -> None:
        self.proposed_price_paise: int = proposed
        self.minimum_compliant_price_paise: int = minimum_compliant
        self.cost_floor_paise: int = cost_floor
        self.minimum_margin_pct: float = margin_pct
        super().__init__(
            "Proposed price %d paise is below constitutional floor %d paise "
            "(cost_floor=%d, minimum_margin_pct=%.2f%%)"
            % (proposed, minimum_compliant, cost_floor, margin_pct)
        )


class BundleProfileNotFoundError(ValueError):
    """Raised when no bundle_profile row exists for (agent_type, bundle_tier)."""

    pass


# -- BundleEngine -------------------------------------------------------------


class BundleEngine:
    """Implements IMarkupEngine.

    Constitutional obligations:
      C-089 -- margin floor enforced in validate_price()
      C-059 -- every validate_price() call writes to pricing_floor_log
      C-063 -- no PII in any log statement
    """

    # ------------------------------------------------------------------
    # Internal DB helpers
    # ------------------------------------------------------------------

    async def _fetch_bundle_profile(
        self: BundleEngine,
        session: AsyncSession,
        agent_type: str,
        bundle_tier: str,
    ) -> dict[str, int | float]:
        """Return the bundle_profiles row for (agent_type, bundle_tier).

        Raises BundleProfileNotFoundError if missing.
        """
        result = await session.execute(
            text(
                "SELECT cost_floor_paise, minimum_margin_pct "
                "FROM institutional.bundle_profiles "
                "WHERE agent_type = :agent_type "
                "  AND bundle_tier = :bundle_tier "
                "LIMIT 1"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            msg = (
                "No bundle_profile for agent_type=%s bundle_tier=%s"
                % (agent_type, bundle_tier)
            )
            raise BundleProfileNotFoundError(msg)
        return {
            "cost_floor_paise": int(row.cost_floor_paise),
            "minimum_margin_pct": float(row.minimum_margin_pct),
        }

    async def _write_pricing_floor_log(
        self: BundleEngine,
        session: AsyncSession,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        outcome: str,
    ) -> uuid.UUID:
        """Write one row to pricing_floor_log. C-059 audit obligation.

        Args:
            session: Database session.
            agent_type: The agent type.
            bundle_tier: The bundle tier.
            proposed_price_paise: Proposed price in paise.
            cost_floor_paise: Cost floor in paise.
            minimum_compliant_price_paise: Minimum compliant price in paise.
            outcome: Outcome (APPROVED or REJECTED).

        Returns:
            The log record UUID.
        """
        log_id: uuid.UUID = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO institutional.pricing_floor_log "
                "(id, agent_type, bundle_tier, proposed_price_paise, "
                " cost_floor_paise, minimum_compliant_price_paise, "
                " outcome, created_at) "
                "VALUES (:id, :agent_type, :bundle_tier, :proposed, "
                "        :floor, :minimum_compliant, :outcome, :created_at)"
            ),
            {
                "id": str(log_id),
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "proposed": proposed_price_paise,
                "floor": cost_floor_paise,
                "minimum_compliant": minimum_compliant_price_paise,
                "outcome": outcome,
                "created_at": datetime.now(timezone.utc),
            },
        )
        await session.commit()
        return log_id

    # ------------------------------------------------------------------
    # IMarkupEngine surface
    # ------------------------------------------------------------------

    async def cost_floor(
        self: BundleEngine, agent_type: str, bundle_tier: str
    ) -> int:
        """Return cost_floor_paise from bundle_profiles.

        Reads the pre-computed value from DB — does NOT recompute.
        Spec: WC027-01a — reads bundle_profiles.cost_floor_paise

        Args:
            agent_type: The agent type.
            bundle_tier: The bundle tier.

        Returns:
            Cost floor in paise.

        Raises:
            BundleProfileNotFoundError: If no matching row exists.
        """
        factory = _get_session_factory()
        async with factory() as session:
            profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)
        cost_floor_paise: int = profile["cost_floor_paise"]
        logger.debug(
            "cost_floor lookup: agent_type=%s bundle_tier=%s floor=%d",
            agent_type,
            bundle_tier,
            cost_floor_paise,
        )
        return cost_floor_paise

    async def derive_price(
        self: BundleEngine,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """Derive a compliant price using margin-on-revenue formula.

        Formula: price = floor / (1 - margin/100)
        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Args:
            agent_type: The agent type.
            bundle_tier: The bundle tier.
            target_margin_pct: Target margin percentage (optional).

        Returns:
            Derived price in paise.

        Raises:
            BundleProfileNotFoundError: If no matching row exists.
        """
        factory = _get_session_factory()
        async with factory() as session:
            profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)

        cost_floor_paise: int = profile["cost_floor_paise"]
        minimum_margin_pct: float = profile["minimum_margin_pct"]

        # Use provided margin or fall back to minimum
        margin_pct: float = (
            target_margin_pct if target_margin_pct is not None else minimum_margin_pct
        )

        # Margin-on-revenue formula: price = cost / (1 - margin/100)
        # Handle edge case where margin >= 100
        if margin_pct >= 100.0:
            logger.warning(
                "derive_price: margin_pct=%.2f >= 100; clamping to 99.99",
                margin_pct,
            )
            margin_pct = 99.99

        denominator: float = 1.0 - (margin_pct / 100.0)
        if denominator <= 0.0:
            logger.error(
                "derive_price: invalid margin_pct=%.2f results in non-positive denominator",
                margin_pct,
            )
            denominator = 0.0001

        derived_paise: float = cost_floor_paise / denominator
        derived_paise_int: int = math.ceil(derived_paise)

        logger.debug(
            "derive_price: agent_type=%s bundle_tier=%s cost_floor=%d margin=%.2f "
            "derived=%d",
            agent_type,
            bundle_tier,
            cost_floor_paise,
            margin_pct,
            derived_paise_int,
        )
        return derived_paise_int

    async def validate_price(
        self: BundleEngine,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """Validate proposed price against constitutional margin floor (C-089).

        Writes to pricing_floor_log on BOTH APPROVED and REJECTED (C-059).

        Args:
            agent_type: The agent type.
            bundle_tier: The bundle tier.
            proposed_price_paise: The proposed price in paise.

        Returns:
            PriceValidation with outcome, cost_floor, minimum_compliant_price_paise,
            and proposed_price_paise.

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile exists.
        """
        factory = _get_session_factory()
        async with factory() as session:
            profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)

        cost_floor_paise: int = profile["cost_floor_paise"]
        minimum_margin_pct: float = profile["minimum_margin_pct"]

        # Calculate minimum compliant price using margin-on-revenue formula
        margin_divisor: float = 1.0 - (minimum_margin_pct / 100.0)
        if margin_divisor <= 0.0:
            margin_divisor = 0.0001
        minimum_compliant_paise: float = cost_floor_paise / margin_divisor
        minimum_compliant_paise_int: int = math.ceil(minimum_compliant_paise)

        # Determine outcome
        is_approved: bool = proposed_price_paise >= minimum_compliant_paise_int
        outcome: str = PriceOutcome.APPROVED if is_approved else PriceOutcome.REJECTED

        # Write audit log (C-059) — BOTH paths
        async with factory() as session:
            log_id: uuid.UUID = await self._write_pricing_floor_log(
                session,
                agent_type,
                bundle_tier,
                proposed_price_paise,
                cost_floor_paise,
                minimum_compliant_paise_int,
                outcome,
            )

        logger.info(
            "validate_price: outcome=%s agent_type=%s bundle_tier=%s "
            "proposed=%d minimum_compliant=%d cost_floor=%d",
            outcome,
            agent_type,
            bundle_tier,
            proposed_price_paise,
            minimum_compliant_paise_int,
            cost_floor_paise,
        )

        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_paise_int,
            proposed_price_paise=proposed_price_paise,
            log_id=str(log_id),
        )