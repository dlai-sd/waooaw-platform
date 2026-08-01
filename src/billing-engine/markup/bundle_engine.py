# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from markup.models import PriceValidation, ValidationOutcome

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


# ── Custom exceptions ─────────────────────────────────────────────────────────

class BelowConstitutionalFloorError(Exception):
    """
    Raised when proposed_price_paise breaches the C-089 constitutional
    minimum margin floor.  Callers MUST treat this as HTTP 422.
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


# ── BundleProfile DB record ───────────────────────────────────────────────────

class _BundleProfileRow:
    """Thin holder for the DB row — not an ORM model (no ORM needed here)."""

    __slots__ = ("cost_floor_paise", "minimum_margin_pct")

    def __init__(self, cost_floor_paise: int, minimum_margin_pct: float) -> None:
        self.cost_floor_paise = cost_floor_paise
        self.minimum_margin_pct = minimum_margin_pct


# ── BundleEngine ──────────────────────────────────────────────────────────────

class BundleEngine:
    """
    Implements IMarkupEngine.

    Constitutional obligations
    ─────────────────────────
    C-089  Margin Floor: validate_price() enforces minimum_margin_pct.
    C-059  Traceability: every validate_price() call writes to pricing_floor_log
           regardless of outcome (APPROVED or REJECTED).
    C-063  PII: no customer identifiers appear in log statements.
    """

    # ── private helpers ───────────────────────────────────────────────────────

    async def _fetch_bundle_profile(
        self, session: AsyncSession, agent_type: str, bundle_tier: str
    ) -> _BundleProfileRow:
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
                "No bundle_profile for agent_type=%s bundle_tier=%s"
                % (agent_type, bundle_tier)
            )
        return _BundleProfileRow(
            cost_floor_paise=int(row.cost_floor_paise),
            minimum_margin_pct=float(row.minimum_margin_pct),
        )

    async def _write_floor_log(
        self,
        session: AsyncSession,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        outcome: ValidationOutcome,
    ) -> uuid.UUID:
        """
        C-059: persist audit record to pricing_floor_log unconditionally.
        Returns the generated log_id.
        """
        log_id = uuid.uuid4()
        recorded_at = datetime.now(timezone.utc)
        await session.execute(
            text(
                "INSERT INTO institutional.pricing_floor_log "
                "  (log_id, agent_type, bundle_tier, proposed_price_paise, "
                "   cost_floor_paise, minimum_compliant_price_paise, outcome, recorded_at) "
                "VALUES "
                "  (:log_id, :agent_type, :bundle_tier, :proposed_price_paise, "
                "   :cost_floor_paise, :minimum_compliant_price_paise, :outcome, :recorded_at)"
            ),
            {
                "log_id": str(log_id),
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
        return log_id

    # ── public API ────────────────────────────────────────────────────────────

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Return the pre-computed cost_floor_paise for (agent_type, bundle_tier).

        Reads `bundle_profiles.cost_floor_paise` from DB — does NOT recompute.
        Raises BundleProfileNotFoundError if the row is missing.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)
                return profile.cost_floor_paise
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "cost_floor: bundle_profile not found for agent_type=%s bundle_tier=%s",
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
        Derive a price using the margin-on-revenue formula:
            price = floor / (1 - margin / 100)

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.
        Returns the derived price rounded up to the nearest paise (int).

        C-089: the margin used is always >= minimum_margin_pct.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)

            effective_margin = (
                target_margin_pct
                if target_margin_pct is not None
                else profile.minimum_margin_pct
            )

            # C-089: never derive below minimum margin
            if effective_margin < profile.minimum_margin_pct:
                logger.warning(
                    "derive_price: requested margin %.4f < minimum %.4f for "
                    "agent_type=%s bundle_tier=%s — clamping to minimum",
                    effective_margin,
                    profile.minimum_margin_pct,
                    agent_type,
                    bundle_tier,
                )
                effective_margin = profile.minimum_margin_pct

            divisor = 1.0 - (effective_margin / 100.0)
            if divisor <= 0.0:
                raise ValueError(
                    "margin_pct=%s produces non-positive divisor — price is undefined"
                    % effective_margin
                )

            raw_price = profile.cost_floor_paise / divisor
            # Ceiling to nearest paise (never under-price)
            derived = int(raw_price) if raw_price == int(raw_price) else int(raw_price) + 1
            logger.info(
                "derive_price: agent_type=%s bundle_tier=%s margin=%.4f derived=%d paise",
                agent_type,
                bundle_tier,
                effective_margin,
                derived,
            )
            return derived

        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validate proposed_price_paise against the C-089 margin floor.

        C-059: writes one row to pricing_floor_log on BOTH APPROVED and REJECTED.
        C-089: REJECTED if proposed_price_paise < minimum_compliant_price_paise.

        Returns PriceValidation with:
            outcome, cost_floor_paise, minimum_compliant_price_paise, proposed_price_paise.

        Raises BelowConstitutionalFloorError on REJECTED outcome so the router
        can return HTTP 422 with the structured body.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(session, agent_type, bundle_tier)

                # Compute minimum_compliant_price_paise using margin-on-revenue
                divisor = 1.0 - (profile.minimum_margin_pct / 100.0)
                if divisor <= 0.0:
                    raise ValueError(
                        "minimum_margin_pct=%s produces non-positive divisor"
                        % profile.minimum_margin_pct
                    )
                raw_min = profile.cost_floor_paise / divisor
                minimum_compliant_price_paise = (
                    int(raw_min)
                    if raw_min == int(raw_min)
                    else int(raw_min) + 1
                )

                outcome = (
                    ValidationOutcome.APPROVED
                    if proposed_price_paise >= minimum_compliant_price_paise
                    else ValidationOutcome.REJECTED
                )

                # C-059: always write audit record regardless of outcome
                log_id = await self._write_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    profile.cost_floor_paise,
                    minimum_compliant_price_paise,
                    outcome,
                )

            logger.info(
                "validate_price: agent_type=%s bundle_tier=%s outcome=%s log_id=%s",
                agent_type,
                bundle_tier,
                outcome.value,
                log_id,
            )

            result = PriceValidation(
                outcome=outcome,
                cost_floor_paise=profile.cost_floor_paise,
                minimum_compliant_price_paise=minimum_compliant_price_paise,
                proposed_price_paise=proposed_price_paise,
                log_id=log_id,
            )

            if outcome == ValidationOutcome.REJECTED:
                raise BelowConstitutionalFloorError(
                    proposed_price_paise,
                    minimum_compliant_price_paise,
                    profile.cost_floor_paise,
                )

            return result

        except asyncio.CancelledError:
            raise
        except BelowConstitutionalFloorError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "validate_price: bundle_profile not found agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise
        except ValueError as exc:
            logger.error(
                "validate_price: configuration error agent_type=%s bundle_tier=%s — %s",
                agent_type,
                bundle_tier,
                exc,
            )
            raise