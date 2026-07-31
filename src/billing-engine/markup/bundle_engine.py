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
from markup.models import (
    BundleProfile,
    PriceValidation,
    ValidationOutcome,
)

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


# ── Sentinel exceptions ────────────────────────────────────────────────────────


class BelowConstitutionalFloorError(Exception):
    """
    Raised when proposed_price_paise < minimum_compliant_price_paise.
    C-089: Margin Floor — never price below cost + constitutional minimum margin.
    """

    def __init__(
        self,
        proposed: int,
        minimum_compliant: int,
        cost_floor: int,
        margin_floor_pct: float,
    ) -> None:
        self.proposed = proposed
        self.minimum_compliant = minimum_compliant
        self.cost_floor = cost_floor
        self.margin_floor_pct = margin_floor_pct
        super().__init__(
            "Proposed price %d paise is below constitutional minimum %d paise "
            "(cost_floor=%d, margin_floor_pct=%.2f)" % (
                proposed, minimum_compliant, cost_floor, margin_floor_pct
            )
        )


# ── BundleEngine ──────────────────────────────────────────────────────────────


class BundleEngine:
    """
    Implements IMarkupEngine.

    Constitutional obligations:
      C-089 — Margin Floor: validate_price() enforces minimum margin; raises
               BelowConstitutionalFloorError when breached.
      C-059 — Traceability: validate_price() writes to pricing_floor_log on
               BOTH APPROVED and REJECTED outcomes.
      C-063 — No PII in log statements.
    """

    # ------------------------------------------------------------------
    # Internal DB helpers
    # ------------------------------------------------------------------

    async def _fetch_bundle_profile(
        self, agent_type: str, bundle_tier: str
    ) -> BundleProfile:
        """
        Load a single row from billing.bundle_profiles.
        Raises KeyError if no matching row is found.
        """
        factory = _get_session_factory()
        async with factory() as session:
            result = await session.execute(
                text(
                    "SELECT agent_type, bundle_tier, cost_floor_paise, "
                    "minimum_margin_pct "
                    "FROM billing.bundle_profiles "
                    "WHERE agent_type = :agent_type "
                    "AND bundle_tier = :bundle_tier "
                    "LIMIT 1"
                ),
                {"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            row = result.fetchone()

        if row is None:
            raise KeyError(
                "bundle_profiles row not found for agent_type=%s bundle_tier=%s"
                % (agent_type, bundle_tier)
            )

        return BundleProfile(
            agent_type=row.agent_type,
            bundle_tier=row.bundle_tier,
            cost_floor_paise=int(row.cost_floor_paise),
            minimum_margin_pct=float(row.minimum_margin_pct),
        )

    async def _write_floor_log(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        outcome: ValidationOutcome,
    ) -> str:
        """
        C-059: Write an audit row to billing.pricing_floor_log.
        Returns the new log_id (UUID string).
        """
        log_id = str(uuid.uuid4())
        recorded_at = datetime.now(timezone.utc)

        factory = _get_session_factory()
        async with factory() as session:
            await session.execute(
                text(
                    "INSERT INTO billing.pricing_floor_log "
                    "(log_id, agent_type, bundle_tier, proposed_price_paise, "
                    "cost_floor_paise, minimum_compliant_price_paise, outcome, recorded_at) "
                    "VALUES (:log_id, :agent_type, :bundle_tier, :proposed_price_paise, "
                    ":cost_floor_paise, :minimum_compliant_price_paise, :outcome, :recorded_at)"
                ),
                {
                    "log_id": log_id,
                    "agent_type": agent_type,
                    "bundle_tier": bundle_tier,
                    "proposed_price_paise": proposed_price_paise,
                    "cost_floor_paise": cost_floor_paise,
                    "minimum_compliant_price_paise": minimum_compliant_price_paise,
                    "outcome": outcome.value,
                    "recorded_at": recorded_at,
                },
            )
            await session.commit()

        logger.info(
            "pricing_floor_log written: log_id=%s outcome=%s",
            log_id,
            outcome.value,
        )
        return log_id

    # ------------------------------------------------------------------
    # IMarkupEngine public surface
    # ------------------------------------------------------------------

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Return the pre-computed cost_floor_paise from bundle_profiles.
        DO NOT recompute — reads the DB column directly (Amendment 2).

        Raises:
            KeyError: if no bundle_profiles row exists for the given
                      agent_type + bundle_tier combination.
            asyncio.CancelledError: propagated without swallowing.
        """
        try:
            profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        except asyncio.CancelledError:
            raise
        except KeyError:
            logger.error(
                "cost_floor: bundle_profiles row missing for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise

        return profile.cost_floor_paise

    # Alias — IMarkupEngine surface name used by router
    async def derive_bundle_cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        IMarkupEngine surface alias for cost_floor().
        Reads bundle_profiles.cost_floor_paise from DB — does NOT recompute.
        """
        return await self.cost_floor(agent_type, bundle_tier)

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        Derive a compliant price using margin-on-revenue formula:
            price = floor / (1 - margin / 100)

        If target_margin_pct is None, falls back to
        bundle_profiles.minimum_margin_pct (Amendment 2).

        Returns the ceiling integer paise value — never rounds down
        (rounding down would violate C-089 by yielding margin < floor).

        Raises:
            KeyError: bundle_profiles row missing.
            ValueError: target_margin_pct >= 100 (undefined / infinite price).
            asyncio.CancelledError: propagated.
        """
        try:
            profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        except asyncio.CancelledError:
            raise
        except KeyError:
            logger.error(
                "derive_price: bundle_profiles row missing for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise

        margin = target_margin_pct if target_margin_pct is not None else profile.minimum_margin_pct

        if margin >= 100.0:
            raise ValueError(
                "target_margin_pct must be < 100; got %.4f" % margin
            )
        if margin < 0.0:
            raise ValueError(
                "target_margin_pct must be >= 0; got %.4f" % margin
            )

        # Margin-on-revenue: price = floor / (1 - margin/100)
        # math.ceil ensures we never deliver a margin below the stated floor.
        raw = profile.cost_floor_paise / (1.0 - margin / 100.0)
        derived = math.ceil(raw)

        logger.info(
            "derive_price: agent_type=%s bundle_tier=%s margin_pct=%.4f "
            "cost_floor_paise=%d derived_paise=%d",
            agent_type,
            bundle_tier,
            margin,
            profile.cost_floor_paise,
            derived,
        )
        return derived

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        C-089: Validate that proposed_price_paise respects the constitutional
        minimum margin floor.

        C-059: Writes to billing.pricing_floor_log on BOTH APPROVED and
        REJECTED outcomes — no audit-free path.

        Returns PriceValidation with:
            outcome                      — APPROVED | REJECTED
            cost_floor_paise             — raw cost from bundle_profiles
            minimum_compliant_price_paise — price at minimum_margin_pct
            proposed_price_paise         — the price under review

        Raises:
            BelowConstitutionalFloorError — when outcome is REJECTED.
              The audit log row is written BEFORE this exception is raised
              so that C-059 traceability is never bypassed.
            KeyError: bundle_profiles row missing.
            asyncio.CancelledError: propagated.
        """
        try:
            profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
        except asyncio.CancelledError:
            raise
        except KeyError:
            logger.error(
                "validate_price: bundle_profiles row missing for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise

        cost_floor_paise = profile.cost_floor_paise
        minimum_margin_pct = profile.minimum_margin_pct

        # Minimum compliant price at the constitutional margin floor.
        # Use math.ceil — rounding down would violate C-089.
        raw_minimum = cost_floor_paise / (1.0 - minimum_margin_pct / 100.0)
        minimum_compliant_price_paise = math.ceil(raw_minimum)

        if proposed_price_paise >= minimum_compliant_price_paise:
            outcome = ValidationOutcome.APPROVED
        else:
            outcome = ValidationOutcome.REJECTED

        # C-059: audit log written unconditionally — both APPROVED and REJECTED.
        try:
            log_id = await self._write_floor_log(
                agent_type=agent_type,
                bundle_tier=bundle_tier,
                proposed_price_paise=proposed_price_paise,
                cost_floor_paise=cost_floor_paise,
                minimum_compliant_price_paise=minimum_compliant_price_paise,
                outcome=outcome,
            )
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as exc:
            # C-059 compliance: log failure to produce evidence record.
            logger.error(
                "validate_price: CRITICAL — pricing_floor_log write failed; "
                "agent_type=%s bundle_tier=%s outcome=%s error=%s",
                agent_type,
                bundle_tier,
                outcome.value,
                str(exc),
                exc_info=True,
            )
            raise

        logger.info(
            "validate_price: agent_type=%s bundle_tier=%s proposed_paise=%d "
            "minimum_compliant_paise=%d outcome=%s log_id=%s",
            agent_type,
            bundle_tier,
            proposed_price_paise,
            minimum_compliant_price_paise,
            outcome.value,
            log_id,
        )

        validation = PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
        )

        if outcome == ValidationOutcome.REJECTED:
            raise BelowConstitutionalFloorError(
                proposed=proposed_price_paise,
                minimum_compliant=minimum_compliant_price_paise,
                cost_floor=cost_floor_paise,
                margin_floor_pct=minimum_margin_pct,
            )

        return validation