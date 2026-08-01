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
    return _async_session


# ── Custom exceptions ─────────────────────────────────────────────────────────


class BelowConstitutionalFloorError(ValueError):
    """Raised when proposed_price_paise is below the constitutional margin floor.

    C-089: Platform must never price below cost + minimum margin.
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
        self.minimum_margin_pct = margin_pct
        super().__init__(
            "Proposed price %d paise is below constitutional floor %d paise "
            "(cost_floor=%d, minimum_margin_pct=%.2f%%)",
            proposed,
            minimum_compliant,
            cost_floor,
            margin_pct,
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
        self, session: AsyncSession, agent_type: str, bundle_tier: str
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
            msg = f"No bundle_profile for agent_type={agent_type} bundle_tier={bundle_tier}"
            raise BundleProfileNotFoundError(msg)
        return {
            "cost_floor_paise": int(row.cost_floor_paise),
            "minimum_margin_pct": float(row.minimum_margin_pct),
        }

    async def _write_pricing_floor_log(
        self,
        session: AsyncSession,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        outcome: str,
    ) -> uuid.UUID:
        """Write one row to pricing_floor_log. C-059 audit obligation."""
        log_id = uuid.uuid4()
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

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """Return cost_floor_paise from bundle_profiles.

        Reads the pre-computed value from DB — does NOT recompute.
        Spec: WC027-01a — reads bundle_profiles.cost_floor_paise directly.
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
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """Derive a compliant price using margin-on-revenue formula.

        Formula: price = floor / (1 - margin/100)
        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Returns: price in paise (integer).
        Raises: BundleProfileNotFoundError, ValueError on invalid margin.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise = profile["cost_floor_paise"]
                margin_pct = (
                    target_margin_pct
                    if target_margin_pct is not None
                    else profile["minimum_margin_pct"]
                )

                if margin_pct < 0 or margin_pct >= 100:
                    msg = (
                        f"Invalid margin_pct={margin_pct}: must be in range [0, 100)"
                    )
                    raise ValueError(msg)

                divisor = 1 - (margin_pct / 100)
                if divisor <= 0:
                    msg = (
                        f"Margin {margin_pct}% is too high; divisor would be "
                        f"{divisor}"
                    )
                    raise ValueError(msg)

                derived_price = math.ceil(cost_floor_paise / divisor)
                logger.debug(
                    "derive_price: cost_floor=%d margin=%s%% -> price=%d",
                    cost_floor_paise,
                    margin_pct,
                    derived_price,
                )
                return derived_price
        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise
        except Exception:
            logger.error(
                "derive_price failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """Validate proposed_price against constitutional margin floor.

        C-089: minimum_compliant_price_paise = cost_floor / (1 - min_margin/100)

        Writes to pricing_floor_log on BOTH APPROVED and REJECTED paths.
        C-059: audit trail required for every validation decision.

        Returns: PriceValidation with:
          - outcome: APPROVED or REJECTED
          - cost_floor_paise: from bundle_profiles
          - minimum_compliant_price_paise: floor / (1 - min_margin/100)
          - proposed_price_paise: echoed from input

        Raises: BundleProfileNotFoundError, ValueError on invalid inputs.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                cost_floor_paise = profile["cost_floor_paise"]
                margin_pct = profile["minimum_margin_pct"]

                divisor = 1 - (margin_pct / 100)
                if divisor <= 0:
                    msg = f"Bundle tier has invalid margin {margin_pct}%"
                    raise ValueError(msg)

                minimum_compliant = math.ceil(cost_floor_paise / divisor)

                if proposed_price_paise >= minimum_compliant:
                    outcome = ValidationOutcome.APPROVED
                    logger.debug(
                        "validate_price APPROVED: proposed=%d >= compliant=%d",
                        proposed_price_paise,
                        minimum_compliant,
                    )
                else:
                    outcome = ValidationOutcome.REJECTED
                    logger.debug(
                        "validate_price REJECTED: proposed=%d < compliant=%d",
                        proposed_price_paise,
                        minimum_compliant,
                    )

                await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant,
                    outcome.value,
                )

                return PriceValidation(
                    outcome=outcome,
                    cost_floor_paise=cost_floor_paise,
                    minimum_compliant_price_paise=minimum_compliant,
                    proposed_price_paise=proposed_price_paise,
                )
        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise
        except Exception:
            logger.error(
                "validate_price failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise