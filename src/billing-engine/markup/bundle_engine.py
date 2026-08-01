# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import asyncio
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

        Reads the pre-computed value from DB - does NOT recompute.
        Spec: WC027-01a - reads bundle_profiles.cost_floor_paise directly.

        Args:
            agent_type: The agent type (e.g., 'DMA', 'ADVISOR').
            bundle_tier: The bundle tier (e.g., 'FREE', 'PREMIUM').

        Returns:
            The cost floor in paise (integer).

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile row exists.
            asyncio.CancelledError: Propagated without swallowing.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                return profile["cost_floor_paise"]
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except Exception:
            logger.error(
                "cost_floor failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise

    async def derive_price(
        self: BundleEngine,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """Derive price using margin-on-revenue formula: floor / (1 - margin/100).

        Spec: WC027-01a - formula uses margin-on-revenue.
        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Args:
            agent_type: The agent type (e.g., 'DMA', 'ADVISOR').
            bundle_tier: The bundle tier (e.g., 'FREE', 'PREMIUM').
            target_margin_pct: Target margin percentage. If None, use minimum_margin_pct from DB.

        Returns:
            Derived price in paise (integer).

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile row exists.
            asyncio.CancelledError: Propagated without swallowing.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise: int = profile["cost_floor_paise"]
                margin_pct: float = (
                    target_margin_pct
                    if target_margin_pct is not None
                    else profile["minimum_margin_pct"]
                )

                # Formula: price = floor / (1 - margin/100)
                # This ensures: (price - floor) / price = margin / 100
                if margin_pct >= 100.0:
                    logger.error(
                        "derive_price margin_pct >= 100 for agent_type=%s bundle_tier=%s",
                        agent_type,
                        bundle_tier,
                    )
                    raise ValueError("margin_pct must be < 100")

                divisor: float = 1.0 - (margin_pct / 100.0)
                if divisor <= 0.0:
                    logger.error(
                        "derive_price divisor <= 0 for agent_type=%s bundle_tier=%s",
                        agent_type,
                        bundle_tier,
                    )
                    raise ValueError("divisor must be > 0")

                derived_price: float = cost_floor_paise / divisor
                return math.ceil(derived_price)
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except (ValueError, ZeroDivisionError):
            logger.error(
                "derive_price failed for agent_type=%s bundle_tier=%s target_margin_pct=%s",
                agent_type,
                bundle_tier,
                target_margin_pct,
                exc_info=True,
            )
            raise

    async def validate_price(
        self: BundleEngine,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """Validate proposed price against constitutional margin floor (C-089).

        Writes to pricing_floor_log on BOTH APPROVED and REJECTED (C-059 audit).
        Returns minimum_compliant_price_paise in the response.

        Spec: WC027-01a - returns PriceValidation with outcome, cost_floor_paise,
                          minimum_compliant_price_paise, proposed_price_paise.

        Args:
            agent_type: The agent type (e.g., 'DMA', 'ADVISOR').
            bundle_tier: The bundle tier (e.g., 'FREE', 'PREMIUM').
            proposed_price_paise: Proposed price in paise (integer).

        Returns:
            PriceValidation object with outcome and pricing details.

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile row exists.
            asyncio.CancelledError: Propagated without swallowing.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise: int = profile["cost_floor_paise"]
                minimum_margin_pct: float = profile["minimum_margin_pct"]

                # Calculate minimum compliant price: floor / (1 - margin/100)
                divisor: float = 1.0 - (minimum_margin_pct / 100.0)
                if divisor <= 0.0:
                    logger.error(
                        "validate_price divisor <= 0 for agent_type=%s bundle_tier=%s",
                        agent_type,
                        bundle_tier,
                    )
                    raise ValueError("divisor must be > 0")

                minimum_price: float = cost_floor_paise / divisor
                minimum_compliant_price_paise: int = math.ceil(minimum_price)

                # Determine outcome
                if proposed_price_paise >= minimum_compliant_price_paise:
                    outcome: str = "APPROVED"
                else:
                    outcome = "REJECTED"

                # C-059: Write to pricing_floor_log on both APPROVED and REJECTED
                await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant_price_paise,
                    outcome,
                )

                return PriceValidation(
                    outcome=PriceOutcome(outcome),
                    cost_floor_paise=cost_floor_paise,
                    minimum_compliant_price_paise=minimum_compliant_price_paise,
                    proposed_price_paise=proposed_price_paise,
                )
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except (ValueError, ZeroDivisionError):
            logger.error(
                "validate_price failed for agent_type=%s bundle_tier=%s proposed=%d",
                agent_type,
                bundle_tier,
                proposed_price_paise,
                exc_info=True,
            )
            raise