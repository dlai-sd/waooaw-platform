# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from markup.models import PriceValidation, PriceValidationOutcome

logger = logging.getLogger(__name__)

# ── DB engine (shared singleton) ──────────────────────────────────────────────
_engine = None
_async_session: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session


# ── Exceptions ────────────────────────────────────────────────────────────────


class BelowConstitutionalFloorError(Exception):
    """
    Raised when a proposed price violates C-089 (Margin Floor).
    Carries the minimum_compliant_price_paise so callers can surface it.
    """

    def __init__(
        self,
        proposed_price_paise: int,
        minimum_compliant_price_paise: int,
        cost_floor_paise: int,
    ) -> None:
        self.proposed_price_paise = proposed_price_paise
        self.minimum_compliant_price_paise = minimum_compliant_price_paise
        self.cost_floor_paise = cost_floor_paise
        super().__init__(
            "Proposed price %d paise is below the constitutional margin floor "
            "(minimum compliant: %d paise, cost floor: %d paise) — C-089 violation."
            % (proposed_price_paise, minimum_compliant_price_paise, cost_floor_paise)
        )


class BundleProfileNotFoundError(Exception):
    """Raised when no bundle_profile row exists for (agent_type, bundle_tier)."""


# ── BundleEngine ──────────────────────────────────────────────────────────────


class BundleEngine:
    """
    Markup Engine implementation of IMarkupEngine.

    Constitutional obligations:
      C-089 — Never price below cost + minimum margin floor.
      C-059 — Every validate_price() call writes an audit row to pricing_floor_log
               regardless of outcome (APPROVED or REJECTED).
      C-063 — No PII in log statements.
    """

    # ------------------------------------------------------------------
    # Internal DB helpers
    # ------------------------------------------------------------------

    async def _fetch_bundle_profile(
        self, session: AsyncSession, agent_type: str, bundle_tier: str
    ) -> dict:
        """
        Load cost_floor_paise and minimum_margin_pct from bundle_profiles.
        Raises BundleProfileNotFoundError if no matching row.
        """
        result = await session.execute(
            text(
                "SELECT cost_floor_paise, minimum_margin_pct "
                "FROM institutional.bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier "
                "LIMIT 1"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            raise BundleProfileNotFoundError(
                "No bundle profile found for agent_type=%s bundle_tier=%s"
                % (agent_type, bundle_tier)
            )
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
        """
        C-059: Write audit record to pricing_floor_log.
        Called on BOTH APPROVED and REJECTED outcomes.
        Returns the generated log_id.
        """
        log_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)
        await session.execute(
            text(
                "INSERT INTO institutional.pricing_floor_log "
                "(log_id, agent_type, bundle_tier, proposed_price_paise, "
                " cost_floor_paise, minimum_compliant_price_paise, outcome, created_at) "
                "VALUES (:log_id, :agent_type, :bundle_tier, :proposed_price_paise, "
                "        :cost_floor_paise, :minimum_compliant_price_paise, "
                "        :outcome, :created_at)"
            ),
            {
                "log_id": str(log_id),
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "proposed_price_paise": proposed_price_paise,
                "cost_floor_paise": cost_floor_paise,
                "minimum_compliant_price_paise": minimum_compliant_price_paise,
                "outcome": outcome,
                "created_at": now,
            },
        )
        await session.commit()
        return log_id

    # ------------------------------------------------------------------
    # Public interface methods
    # ------------------------------------------------------------------

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Return the pre-computed cost_floor_paise from bundle_profiles.
        Do NOT recompute — the DB value is the authoritative cost floor (ADR-034).

        Returns:
            cost_floor_paise (int): lowest allowable cost basis in INR paise.

        Raises:
            BundleProfileNotFoundError: if (agent_type, bundle_tier) has no profile.
            asyncio.CancelledError: propagated without swallowing.
        """
        try:
            factory = _get_session_factory()
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
            floor: int = profile["cost_floor_paise"]
            logger.info(
                "cost_floor resolved: agent_type=%s bundle_tier=%s floor_paise=%d",
                agent_type,
                bundle_tier,
                floor,
            )
            return floor
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "cost_floor: bundle profile not found for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        Derive a selling price using the margin-on-revenue formula:
            price = floor / (1 - margin / 100)

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Returns:
            derived price in INR paise (int, ceiling-rounded).

        Raises:
            BundleProfileNotFoundError: profile missing.
            ValueError: if effective margin >= 100 (degenerate input).
            asyncio.CancelledError: propagated.
        """
        try:
            factory = _get_session_factory()
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )

            cost_floor_paise: int = profile["cost_floor_paise"]
            effective_margin: float = (
                target_margin_pct
                if target_margin_pct is not None
                else profile["minimum_margin_pct"]
            )

            if effective_margin >= 100.0:
                raise ValueError(
                    "margin_pct=%s is >= 100 — degenerate: price would be infinite."
                    % effective_margin
                )
            if effective_margin < 0.0:
                raise ValueError(
                    "margin_pct=%s is negative — invalid margin." % effective_margin
                )

            # Margin-on-revenue formula.  Ceiling ensures we never go below floor.
            raw_price: float = cost_floor_paise / (1.0 - effective_margin / 100.0)
            derived: int = math.ceil(raw_price)

            logger.info(
                "derive_price: agent_type=%s bundle_tier=%s "
                "margin_pct=%s floor_paise=%d derived_paise=%d",
                agent_type,
                bundle_tier,
                effective_margin,
                cost_floor_paise,
                derived,
            )
            return derived

        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise
        except Exception:
            logger.error(
                "derive_price: unexpected error for agent_type=%s bundle_tier=%s",
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
        """
        Validate whether proposed_price_paise satisfies the C-089 constitutional
        margin floor for the given (agent_type, bundle_tier).

        C-089 enforcement:
            minimum_compliant_price = ceil(cost_floor / (1 - min_margin / 100))
            APPROVED  if proposed_price >= minimum_compliant_price
            REJECTED  if proposed_price <  minimum_compliant_price

        C-059 audit obligation:
            Writes a row to pricing_floor_log on BOTH APPROVED and REJECTED outcomes.

        Returns:
            PriceValidation with outcome, cost_floor_paise,
            minimum_compliant_price_paise, proposed_price_paise.

        Raises:
            BelowConstitutionalFloorError: on REJECTED outcome (C-089).
            BundleProfileNotFoundError: profile missing.
            asyncio.CancelledError: propagated.
        """
        try:
            factory = _get_session_factory()
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )

                cost_floor_paise: int = profile["cost_floor_paise"]
                min_margin_pct: float = profile["minimum_margin_pct"]

                # Compute the minimum price that satisfies C-089.
                if min_margin_pct >= 100.0:
                    raise ValueError(
                        "minimum_margin_pct=%s for agent_type=%s bundle_tier=%s "
                        "is >= 100 — configuration error." % (
                            min_margin_pct, agent_type, bundle_tier
                        )
                    )
                raw_min: float = cost_floor_paise / (1.0 - min_margin_pct / 100.0)
                minimum_compliant_price_paise: int = math.ceil(raw_min)

                if proposed_price_paise >= minimum_compliant_price_paise:
                    outcome = PriceValidationOutcome.APPROVED
                else:
                    outcome = PriceValidationOutcome.REJECTED

                # C-059: write audit record regardless of outcome.
                log_id = await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant_price_paise,
                    outcome.value,
                )

            logger.info(
                "validate_price: agent_type=%s bundle_tier=%s "
                "proposed_paise=%d minimum_compliant_paise=%d outcome=%s log_id=%s",
                agent_type,
                bundle_tier,
                proposed_price_paise,
                minimum_compliant_price_paise,
                outcome.value,
                log_id,
            )

            result = PriceValidation(
                outcome=outcome,
                cost_floor_paise=cost_floor_paise,
                minimum_compliant_price_paise=minimum_compliant_price_paise,
                proposed_price_paise=proposed_price_paise,
            )

            if outcome == PriceValidationOutcome.REJECTED:
                raise BelowConstitutionalFloorError(
                    proposed_price_paise,
                    minimum_compliant_price_paise,
                    cost_floor_paise,
                )

            return result

        except asyncio.CancelledError:
            raise
        except (BelowConstitutionalFloorError, BundleProfileNotFoundError, ValueError):
            raise
        except Exception:
            logger.error(
                "validate_price: unexpected error for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise