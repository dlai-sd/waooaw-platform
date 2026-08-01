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
                return int(profile["cost_floor_paise"])
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except (OSError, RuntimeError) as exc:
            logger.error(
                "cost_floor failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise RuntimeError(
                "cost_floor DB lookup failed"
            ) from exc

    async def derive_bundle_cost_floor(
        self, agent_type: str, bundle_tier: str
    ) -> int:
        """Alias surface required by IMarkupEngine skeleton.

        Delegates to cost_floor() — reads bundle_profiles.cost_floor_paise.
        Does NOT recompute the floor (ADR-036, WC027-01a).
        """
        return await self.cost_floor(agent_type, bundle_tier)

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """Derive the minimum compliant selling price using margin-on-revenue.

        Formula: price = floor / (1 - margin / 100)
        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Returns the price rounded UP to the nearest paise (math.ceil) so that
        the effective margin is always ≥ the requested margin (C-089).
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except (OSError, RuntimeError) as exc:
            logger.error(
                "derive_price: DB lookup failed agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise RuntimeError("derive_price DB lookup failed") from exc

        cost_floor_paise: int = int(profile["cost_floor_paise"])
        margin_pct: float = (
            target_margin_pct
            if target_margin_pct is not None
            else float(profile["minimum_margin_pct"])
        )

        if margin_pct < 0.0 or margin_pct >= 100.0:
            raise ValueError(
                "margin_pct must be in [0, 100); got %s" % margin_pct
            )

        divisor = 1.0 - (margin_pct / 100.0)
        # Guard against floating-point underflow near 100 %
        if divisor <= 0.0:
            raise ValueError(
                "margin_pct=%s produces non-positive divisor; cannot derive price"
                % margin_pct
            )

        raw_price = cost_floor_paise / divisor
        # Ceil so the realised margin is always ≥ requested margin (C-089)
        derived = math.ceil(raw_price)

        logger.debug(
            "derive_price agent_type=%s bundle_tier=%s "
            "cost_floor=%d margin_pct=%.4f derived=%d",
            agent_type,
            bundle_tier,
            cost_floor_paise,
            margin_pct,
            derived,
        )
        return derived

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """Validate proposed_price_paise against the constitutional margin floor.

        C-089: price MUST be ≥ floor / (1 - minimum_margin_pct / 100).
        C-059: writes to pricing_floor_log on BOTH APPROVED and REJECTED outcomes.

        Returns a PriceValidation with:
          outcome                    — APPROVED | REJECTED
          cost_floor_paise           — pre-computed floor from bundle_profiles
          minimum_compliant_price_paise — ceil(floor / (1 - min_margin/100))
          proposed_price_paise       — echo of the caller's input
        """
        factory = _get_session_factory()

        # ── 1. Load bundle profile ────────────────────────────────────────
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            raise
        except (OSError, RuntimeError) as exc:
            logger.error(
                "validate_price: profile fetch failed agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise RuntimeError("validate_price DB lookup failed") from exc

        cost_floor_paise: int = int(profile["cost_floor_paise"])
        minimum_margin_pct: float = float(profile["minimum_margin_pct"])

        # ── 2. Compute minimum compliant price (margin-on-revenue, ceil) ──
        divisor = 1.0 - (minimum_margin_pct / 100.0)
        if divisor <= 0.0:
            raise ValueError(
                "minimum_margin_pct=%s produces non-positive divisor "
                "for agent_type=%s bundle_tier=%s"
                % (minimum_margin_pct, agent_type, bundle_tier)
            )
        minimum_compliant_price_paise: int = math.ceil(cost_floor_paise / divisor)

        # ── 3. Determine outcome ──────────────────────────────────────────
        if proposed_price_paise >= minimum_compliant_price_paise:
            outcome = ValidationOutcome.APPROVED
        else:
            outcome = ValidationOutcome.REJECTED

        # ── 4. Write audit log (C-059 — BOTH outcomes) ───────────────────
        try:
            async with factory() as log_session:
                log_id = await self._write_pricing_floor_log(
                    log_session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    cost_floor_paise,
                    minimum_compliant_price_paise,
                    outcome.value,
                )
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as exc:
            # C-059: audit write failure is a constitutional violation — do not
            # silently swallow; re-raise so the caller can surface the failure.
            logger.error(
                "validate_price: pricing_floor_log write failed "
                "agent_type=%s bundle_tier=%s outcome=%s",
                agent_type,
                bundle_tier,
                outcome.value,
                exc_info=True,
            )
            raise RuntimeError(
                "C-059 audit write to pricing_floor_log failed"
            ) from exc

        logger.info(
            "validate_price outcome=%s agent_type=%s bundle_tier=%s "
            "proposed=%d floor=%d minimum_compliant=%d log_id=%s",
            outcome.value,
            agent_type,
            bundle_tier,
            proposed_price_paise,
            cost_floor_paise,
            minimum_compliant_price_paise,
            log_id,
        )

        # ── 5. Raise on REJECTED (C-089 constitutional enforcement) ──────
        if outcome == ValidationOutcome.REJECTED:
            raise BelowConstitutionalFloorError(
                proposed=proposed_price_paise,
                minimum_compliant=minimum_compliant_price_paise,
                cost_floor=cost_floor_paise,
                margin_pct=minimum_margin_pct,
            )

        # ── 6. Return validated result ────────────────────────────────────
        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=cost_floor_paise,
            minimum_compliant_price_paise=minimum_compliant_price_paise,
            proposed_price_paise=proposed_price_paise,
        )