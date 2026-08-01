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
from markup.models import PriceValidation, ValidationOutcome

logger = logging.getLogger(__name__)

# ── DB engine (shared singleton) ──────────────────────────────────────────────
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


# ── Custom exceptions ─────────────────────────────────────────────────────────


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


# ── BundleEngine ──────────────────────────────────────────────────────────────


class BundleEngine:
    """Implements IMarkupEngine.

    Constitutional obligations:
      C-089 — margin floor enforced in validate_price()
      C-059 — every validate_price() call writes to pricing_floor_log
      C-063 — no PII in any log statement
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

        Reads the pre-computed value from DB — does NOT recompute.
        Spec: WC027-01a — reads bundle_profiles.cost_floor_paise directly.

        Args:
            agent_type: The agent type (e.g., 'DMA', 'ADVISOR').
            bundle_tier: The bundle tier (e.g., 'FREE', 'PREMIUM').

        Returns:
            The cost floor in paise (integer).

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile row exists.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                return int(profile["cost_floor_paise"])
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except (OSError, RuntimeError):
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
        """Derive selling price from cost floor and margin.

        Formula: price = floor / (1 - margin/100)
        This is margin-on-revenue calculation.

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Spec: WC027-01a.
        Constitutional: C-089 (margin floor enforced via cost_floor).

        Args:
            agent_type: The agent type.
            bundle_tier: The bundle tier.
            target_margin_pct: Target margin as a percentage (e.g., 25.0 for 25%).
                              If None, uses the minimum_margin_pct from bundle_profiles.

        Returns:
            The derived price in paise (integer, rounded up).

        Raises:
            BundleProfileNotFoundError: If no matching bundle_profile row exists.
            ValueError: If target_margin_pct >= 100 (would cause division by zero).
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise = int(profile["cost_floor_paise"])
                margin = (
                    float(profile["minimum_margin_pct"])
                    if target_margin_pct is None
                    else target_margin_pct
                )

                if margin >= 100.0:
                    msg = (
                        "target_margin_pct=%s is invalid (must be < 100%%)"
                        % margin
                    )
                    raise ValueError(msg)

                # Formula: price = floor / (1 - margin/100)
                divisor = 1.0 - (margin / 100.0)
                if divisor <= 0.0:
                    msg = (
                        "Margin %.2f%% results in non-positive divisor"
                        % margin
                    )
                    raise ValueError(msg)

                price_float = cost_floor_paise / divisor
                # Round up to nearest paise (ceiling)
                price_paise = math.ceil(price_float)

                logger.info(
                    "derive_price: agent_type=%s bundle_tier=%s "
                    "floor=%d margin=%.2f%% → price=%d",
                    agent_type,
                    bundle_tier,
                    cost_floor_paise,
                    margin,
                    price_paise,
                )

                return price_paise
        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise
        except (OSError, RuntimeError):
            logger.error(
                "derive_price failed for agent_type=%s bundle_tier=%s",
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
        """Validate a proposed price against the constitutional margin floor.

        Spec: WC027-01a.
        Constitutional: C-089 (never price below cost + minimum margin).
        Constitutional: C-059 (audit: write to pricing_floor_log on BOTH outcomes).

        Algorithm:
          1. Fetch bundle_profiles row for (agent_type, bundle_tier).
          2. Calculate minimum_compliant_price_paise = cost_floor / (1 - margin/100).
          3. If proposed_price_paise >= minimum_compliant_price_paise: outcome=APPROVED.
          4. Else: outcome=REJECTED.
          5. Write one row to pricing_floor_log (C-059 audit obligation).
          6. Return PriceValidation with outcome + all fields.

        Args:
            agent_type: The agent type.
            bundle_tier: The bundle tier.
            proposed_price_paise: The proposed selling price in paise.

        Returns:
            PriceValidation object with fields:
              - outcome: ValidationOutcome.APPROVED or REJECTED
              - proposed_price_paise: Echo of input
              - cost_floor_paise: Read from bundle_profiles
              - minimum_compliant_price_paise: Calculated floor / (1 - margin/100)

        Raises:
            BelowConstitutionalFloorError: If proposed price is below the floor
                (caller may catch and convert to HTTP 422).
            BundleProfileNotFoundError: If no matching bundle_profile row exists
                (caller may convert to HTTP 404).
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise = int(profile["cost_floor_paise"])
                margin_pct = float(profile["minimum_margin_pct"])

                # Calculate minimum_compliant_price_paise
                divisor = 1.0 - (margin_pct / 100.0)
                if divisor <= 0.0:
                    msg = (
                        "Invalid margin %.2f%% in bundle_profile "
                        "for agent_type=%s bundle_tier=%s"
                        % (margin_pct, agent_type, bundle_tier)
                    )
                    raise ValueError(msg)

                minimum_compliant = math.ceil(cost_floor_paise / divisor)

                # Determine outcome
                if proposed_price_paise >= minimum_compliant:
                    outcome = ValidationOutcome.APPROVED
                else:
                    outcome = ValidationOutcome.REJECTED

                # Write audit log (C-059)
                await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant,
                    outcome.value,
                )

                logger.info(
                    "validate_price: agent_type=%s bundle_tier=%s "
                    "proposed=%d floor=%d minimum_compliant=%d outcome=%s",
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant,
                    outcome.value,
                )

                result = PriceValidation(
                    outcome=outcome,
                    proposed_price_paise=proposed_price_paise,
                    cost_floor_paise=cost_floor_paise,
                    minimum_compliant_price_paise=minimum_compliant,
                )

                # Raise if below floor (caller may catch and convert to HTTP 422)
                if outcome == ValidationOutcome.REJECTED:
                    raise BelowConstitutionalFloorError(
                        proposed_price_paise,
                        minimum_compliant,
                        cost_floor_paise,
                        margin_pct,
                    )

                return result
        except asyncio.CancelledError:
            raise
        except (
            BelowConstitutionalFloorError,
            BundleProfileNotFoundError,
            ValueError,
        ):
            raise
        except (OSError, RuntimeError):
            logger.error(
                "validate_price failed for agent_type=%s bundle_tier=%s "
                "proposed=%d",
                agent_type,
                bundle_tier,
                proposed_price_paise,
                exc_info=True,
            )
            raise