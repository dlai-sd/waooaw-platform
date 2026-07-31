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

# ── DB engine (shared singleton) ─────────────────────────────────────────────
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
    Raised when a proposed price violates the C-089 minimum margin floor.
    Carries minimum_compliant_price_paise so callers can surface it in 422 body.
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
            "Proposed price %d paise is below constitutional minimum %d paise (C-089)"
            % (proposed_price_paise, minimum_compliant_price_paise)
        )


class BundleProfileNotFoundError(Exception):
    """Raised when no bundle_profile row exists for (agent_type, bundle_tier)."""


# ── BundleEngine ──────────────────────────────────────────────────────────────


class BundleEngine:
    """
    Implements IMarkupEngine.

    Constitutional obligations:
      C-089 — Never price below cost (margin floor enforcement).
      C-059 — Every validate_price() call writes to pricing_floor_log
               regardless of outcome (APPROVED or REJECTED).
      C-063 — No PII in logs.
    """

    # ── private helpers ───────────────────────────────────────────────────────

    async def _fetch_bundle_profile(
        self, session: AsyncSession, agent_type: str, bundle_tier: str
    ) -> dict:
        """
        Fetch a single row from billing.bundle_profiles.
        Returns a dict with keys: cost_floor_paise, minimum_margin_pct.
        Raises BundleProfileNotFoundError if not found.
        """
        result = await session.execute(
            text(
                "SELECT cost_floor_paise, minimum_margin_pct "
                "FROM billing.bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier "
                "LIMIT 1"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            raise BundleProfileNotFoundError(
                "No bundle_profile for agent_type=%s bundle_tier=%s"
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
        C-059: Write an immutable audit record to pricing_floor_log.
        Called for BOTH APPROVED and REJECTED outcomes.
        Returns the generated log_id.
        """
        log_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await session.execute(
            text(
                "INSERT INTO billing.pricing_floor_log "
                "  (log_id, agent_type, bundle_tier, proposed_price_paise, "
                "   cost_floor_paise, minimum_compliant_price_paise, outcome, created_at) "
                "VALUES "
                "  (:log_id, :agent_type, :bundle_tier, :proposed_price_paise, "
                "   :cost_floor_paise, :minimum_compliant_price_paise, :outcome, :created_at)"
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

    # ── public API ────────────────────────────────────────────────────────────

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Read bundle_profiles.cost_floor_paise from DB.
        DO NOT recompute — the floor is set by Founder FA and stored.

        Returns: cost floor in INR paise (int).
        Raises:  BundleProfileNotFoundError if row is missing.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)
                return profile["cost_floor_paise"]
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "bundle_profile not found for agent_type=%s bundle_tier=%s",
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
        Result is rounded UP to the nearest paise (ceil) so margin is never under-delivered.

        Returns: derived price in INR paise (int).
        Raises:  BundleProfileNotFoundError, ValueError (invalid margin).
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)

        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "bundle_profile not found for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise

        cost_floor_paise: int = profile["cost_floor_paise"]
        margin_pct: float = (
            target_margin_pct
            if target_margin_pct is not None
            else profile["minimum_margin_pct"]
        )

        if margin_pct < 0 or margin_pct >= 100:
            raise ValueError(
                "margin_pct must be in [0, 100) — received %s" % margin_pct
            )

        divisor = 1.0 - (margin_pct / 100.0)
        derived_float = cost_floor_paise / divisor
        # Ceil ensures margin is never under-delivered due to floating point truncation.
        return math.ceil(derived_float)

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validate a proposed price against the C-089 constitutional margin floor.

        C-089: proposed_price MUST be >= minimum_compliant_price_paise.
        C-059: ALWAYS writes to pricing_floor_log regardless of outcome.

        Returns:
            PriceValidation with outcome APPROVED or REJECTED.
            On REJECTED: also raises BelowConstitutionalFloorError so callers
            can surface minimum_compliant_price_paise in HTTP 422 bodies.

        Raises:
            BundleProfileNotFoundError — if no bundle profile exists.
            BelowConstitutionalFloorError — on REJECTED outcome (C-089).
            asyncio.CancelledError — propagated without swallowing.
        """
        factory = _get_session_factory()

        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)

                cost_floor_paise: int = profile["cost_floor_paise"]
                minimum_margin_pct: float = profile["minimum_margin_pct"]

                # Compute the minimum compliant price using margin-on-revenue formula.
                divisor = 1.0 - (minimum_margin_pct / 100.0)
                minimum_compliant_price_paise: int = math.ceil(cost_floor_paise / divisor)

                # C-089 gate: is the proposed price constitutional?
                if proposed_price_paise >= minimum_compliant_price_paise:
                    outcome = PriceValidationOutcome.APPROVED
                else:
                    outcome = PriceValidationOutcome.REJECTED

                # C-059: write audit record unconditionally (APPROVED and REJECTED both).
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
                    "validate_price outcome=%s log_id=%s agent_type=%s bundle_tier=%s",
                    outcome.value,
                    log_id,
                    agent_type,
                    bundle_tier,
                )

        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "bundle_profile not found during validate_price agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise

        validation_result = PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
        )

        # Raise AFTER constructing result so caller can inspect full context.
        if outcome == PriceValidationOutcome.REJECTED:
            raise BelowConstitutionalFloorError(
                proposed_price_paise,
                minimum_compliant_price_paise,
                cost_floor_paise,
            )

        return validation_result