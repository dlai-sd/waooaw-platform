# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import asyncio
import logging
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
            "cost_floor_paise": row.cost_floor_paise,
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
        """Write one row to pricing_floor_log. C-059 audit obligation."""
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

        Reads the pre-computed value from DB -- does NOT recompute.
        Spec: WC027-01a -- reads bundle_profiles.cost_floor_paise directly.

        Args:
            agent_type: The agent type (e.g., 'DMA', 'ADVISOR').
            bundle_tier: The bundle tier (e.g., 'FREE', 'PREMIUM').

        Returns:
            The cost floor in paise (integer).

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile row exists.
            asyncio.CancelledError: Propagated without swallowing.
        """
        try:
            factory: sessionmaker[AsyncSession] = _get_session_factory()
            async with factory() as session:
                profile: dict[str, int | float] = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                logger.info(
                    "cost_floor retrieved: agent_type=%s bundle_tier=%s "
                    "cost_floor_paise=%d",
                    agent_type,
                    bundle_tier,
                    profile["cost_floor_paise"],
                )
                return profile["cost_floor_paise"]  # type: ignore[return-value]
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "Bundle profile not found: agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise
        except Exception:
            logger.error(
                "Unexpected error in cost_floor: agent_type=%s bundle_tier=%s",
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
        """Derive selling price using margin-on-revenue formula.

        Formula: price = floor / (1 - margin/100)
        This is margin-on-revenue (margin is a % of selling price).

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Args:
            agent_type: The agent type (e.g., 'DMA').
            bundle_tier: The bundle tier (e.g., 'PREMIUM').
            target_margin_pct: Target margin as percentage. If None, uses DB minimum.

        Returns:
            The derived price in paise (integer, rounded to nearest paise).

        Raises:
            BundleProfileNotFoundError: If bundle_profile row does not exist.
            asyncio.CancelledError: Propagated without swallowing.
        """
        try:
            factory: sessionmaker[AsyncSession] = _get_session_factory()
            async with factory() as session:
                profile: dict[str, int | float] = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise: int = profile["cost_floor_paise"]  # type: ignore[assignment]
                margin_to_use: float = (
                    target_margin_pct
                    if target_margin_pct is not None
                    else profile["minimum_margin_pct"]  # type: ignore[assignment]
                )

                # Margin-on-revenue formula: price = floor / (1 - margin/100)
                if margin_to_use >= 100.0:
                    logger.error(
                        "Invalid margin: agent_type=%s bundle_tier=%s "
                        "margin_pct=%.2f (>= 100)",
                        agent_type,
                        bundle_tier,
                        margin_to_use,
                    )
                    raise ValueError(
                        "Margin must be < 100%%; got %.2f%%" % margin_to_use
                    )

                denominator: float = 1.0 - (margin_to_use / 100.0)
                if denominator <= 0:
                    logger.error(
                        "Invalid denominator after margin calc: agent_type=%s "
                        "bundle_tier=%s margin_pct=%.2f denominator=%.6f",
                        agent_type,
                        bundle_tier,
                        margin_to_use,
                        denominator,
                    )
                    raise ValueError(
                        "Denominator must be > 0; margin=%.2f%% is invalid"
                        % margin_to_use
                    )

                derived_price_float: float = cost_floor_paise / denominator
                derived_price_paise: int = round(derived_price_float)

                logger.info(
                    "derive_price calculated: agent_type=%s bundle_tier=%s "
                    "cost_floor=%d margin_pct=%.2f derived_price=%d",
                    agent_type,
                    bundle_tier,
                    cost_floor_paise,
                    margin_to_use,
                    derived_price_paise,
                )
                return derived_price_paise
        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise
        except Exception:
            logger.error(
                "Unexpected error in derive_price: agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise

    async def validate_price(
        self: BundleEngine,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """Validate proposed price against constitutional margin floor.

        C-089 obligation: Platform must never price below cost + minimum margin.

        Writes to pricing_floor_log on BOTH APPROVED and REJECTED outcomes.
        C-059 audit obligation: every call is recorded.

        Args:
            agent_type: The agent type.
            bundle_tier: The bundle tier.
            proposed_price_paise: The proposed selling price in paise.

        Returns:
            PriceValidation with:
              - outcome: 'APPROVED' or 'REJECTED'
              - cost_floor_paise: cost floor from DB
              - minimum_compliant_price_paise: minimum price to meet margin floor
              - proposed_price_paise: the input value

        Raises:
            BundleProfileNotFoundError: If bundle_profile does not exist.
            asyncio.CancelledError: Propagated without swallowing.
        """
        try:
            factory: sessionmaker[AsyncSession] = _get_session_factory()
            async with factory() as session:
                profile: dict[str, int | float] = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise: int = profile["cost_floor_paise"]  # type: ignore[assignment]
                minimum_margin_pct: float = profile["minimum_margin_pct"]  # type: ignore[assignment]

                # Calculate minimum_compliant_price using margin-on-revenue formula
                denominator: float = 1.0 - (minimum_margin_pct / 100.0)
                minimum_compliant_float: float = cost_floor_paise / denominator
                minimum_compliant_price_paise: int = round(minimum_compliant_float)

                # Determine outcome
                if proposed_price_paise >= minimum_compliant_price_paise:
                    outcome: str = PriceOutcome.APPROVED
                else:
                    outcome = PriceOutcome.REJECTED

                # Write audit log (C-059)
                log_id: uuid.UUID = await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant_price_paise,
                    outcome,
                )

                logger.info(
                    "validate_price completed: agent_type=%s bundle_tier=%s "
                    "proposed=%d minimum_compliant=%d outcome=%s log_id=%s",
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    minimum_compliant_price_paise,
                    outcome,
                    str(log_id),
                )

                return PriceValidation(
                    outcome=outcome,
                    cost_floor_paise=cost_floor_paise,
                    minimum_compliant_price_paise=minimum_compliant_price_paise,
                    proposed_price_paise=proposed_price_paise,
                )
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except Exception:
            logger.error(
                "Unexpected error in validate_price: agent_type=%s bundle_tier=%s "
                "proposed=%d",
                agent_type,
                bundle_tier,
                proposed_price_paise,
                exc_info=True,
            )
            raise