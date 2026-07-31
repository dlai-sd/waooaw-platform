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
from markup.models import (
    BundleProfile,
    PriceValidation,
    ValidationOutcome,
)
from skeleton.wbe_interfaces import IMarkupEngine

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


# ── Custom exceptions ─────────────────────────────────────────────────────────


class BelowConstitutionalFloorError(Exception):
    """
    Raised when proposed_price_paise is below the constitutional minimum
    margin floor. C-089: we never price below cost + minimum margin.
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
            "Proposed price %d paise is below constitutional floor %d paise "
            "(cost floor: %d paise). C-089 violation."
            % (proposed_price_paise, minimum_compliant_price_paise, cost_floor_paise)
        )


class BundleProfileNotFoundError(Exception):
    """Raised when no bundle_profiles row exists for (agent_type, bundle_tier)."""


# ── BundleEngine ──────────────────────────────────────────────────────────────


class BundleEngine(IMarkupEngine):
    """
    Markup Engine — implements IMarkupEngine.

    Constitutional obligations:
      C-089 — Never price below cost + minimum margin (constitutional floor).
      C-059 — Every validate_price() call writes to pricing_floor_log
               regardless of APPROVED or REJECTED outcome.
      C-063 — No PII in log statements.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_bundle_profile(
        self, session: AsyncSession, agent_type: str, bundle_tier: str
    ) -> BundleProfile:
        """
        Load bundle_profiles row for (agent_type, bundle_tier).
        Raises BundleProfileNotFoundError if absent.
        """
        result = await session.execute(
            text(
                "SELECT agent_type, bundle_tier, cost_floor_paise, "
                "minimum_margin_pct, display_name "
                "FROM billing.bundle_profiles "
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
        return BundleProfile(
            agent_type=row.agent_type,
            bundle_tier=row.bundle_tier,
            cost_floor_paise=row.cost_floor_paise,
            minimum_margin_pct=float(row.minimum_margin_pct),
            display_name=row.display_name,
        )

    def _compute_minimum_compliant_price(
        self, cost_floor_paise: int, minimum_margin_pct: float
    ) -> int:
        """
        C-089 constitutional minimum price.
        Formula: margin-on-revenue → price = floor / (1 - margin/100).
        Returns ceiling integer paise.
        """
        if minimum_margin_pct >= 100.0:
            raise ValueError(
                "minimum_margin_pct must be < 100, got %s" % minimum_margin_pct
            )
        raw = cost_floor_paise / (1.0 - minimum_margin_pct / 100.0)
        # Always ceil — never allow rounding to produce a below-floor price.
        import math

        return math.ceil(raw)

    async def _write_pricing_floor_log(
        self,
        session: AsyncSession,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        outcome: ValidationOutcome,
    ) -> str:
        """
        C-059: Writes one row to pricing_floor_log for every validate_price()
        call — both APPROVED and REJECTED.
        Returns the generated log_id (UUID string).
        """
        log_id = str(uuid.uuid4())
        recorded_at = datetime.now(tz=timezone.utc)
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
        return log_id

    # ------------------------------------------------------------------
    # IMarkupEngine public interface
    # ------------------------------------------------------------------

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Returns cost_floor_paise from bundle_profiles.
        DO NOT recompute — reads the DB value directly (ADR-036, WC027-01a).
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                return profile.cost_floor_paise
        except asyncio.CancelledError:
            raise
        except BundleProfileNotFoundError:
            logger.error(
                "Bundle profile not found for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
            )
            raise
        except (OSError, ValueError):
            logger.error(
                "cost_floor DB read failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
                extra={"context": "cost_floor"},
            )
            raise

    async def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: float | None = None,
    ) -> int:
        """
        Derives a compliant price using margin-on-revenue formula:
            price = floor / (1 - margin/100)

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.
        Returns ceiling integer paise.
        """
        import math

        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )

            margin = (
                target_margin_pct
                if target_margin_pct is not None
                else profile.minimum_margin_pct
            )

            if margin < 0.0 or margin >= 100.0:
                raise ValueError(
                    "target_margin_pct must be in [0, 100), got %s" % margin
                )

            raw = profile.cost_floor_paise / (1.0 - margin / 100.0)
            return math.ceil(raw)

        except asyncio.CancelledError:
            raise
        except (BundleProfileNotFoundError, ValueError):
            raise
        except OSError:
            logger.error(
                "derive_price DB read failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
                extra={"context": "derive_price"},
            )
            raise

    async def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        """
        Validates proposed_price_paise against C-089 constitutional floor.

        C-089: proposed_price_paise MUST be >= minimum_compliant_price_paise.
        C-059: Writes one row to pricing_floor_log on BOTH APPROVED and REJECTED.

        Returns PriceValidation with:
          - outcome: APPROVED | REJECTED
          - cost_floor_paise
          - minimum_compliant_price_paise
          - proposed_price_paise

        Raises BelowConstitutionalFloorError when REJECTED (caller may convert
        to HTTP 422 with minimum_compliant_price_paise in the response body).
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )

                minimum_compliant = self._compute_minimum_compliant_price(
                    profile.cost_floor_paise, profile.minimum_margin_pct
                )

                if proposed_price_paise >= minimum_compliant:
                    outcome = ValidationOutcome.APPROVED
                else:
                    outcome = ValidationOutcome.REJECTED

                # C-059: always write audit log — APPROVED and REJECTED both recorded.
                log_id = await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    profile.cost_floor_paise,
                    minimum_compliant,
                    outcome,
                )

            logger.info(
                "validate_price: outcome=%s agent_type=%s bundle_tier=%s log_id=%s",
                outcome.value,
                agent_type,
                bundle_tier,
                log_id,
            )

            result = PriceValidation(
                outcome=outcome,
                cost_floor_paise=profile.cost_floor_paise,
                minimum_compliant_price_paise=minimum_compliant,
                proposed_price_paise=proposed_price_paise,
            )

            if outcome == ValidationOutcome.REJECTED:
                raise BelowConstitutionalFloorError(
                    proposed_price_paise,
                    minimum_compliant,
                    profile.cost_floor_paise,
                )

            return result

        except asyncio.CancelledError:
            raise
        except BelowConstitutionalFloorError:
            # Re-raise so router converts to HTTP 422 with PriceValidation body.
            raise
        except BundleProfileNotFoundError:
            raise
        except (OSError, ValueError):
            logger.error(
                "validate_price failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
                extra={"context": "validate_price"},
            )
            raise

    # ------------------------------------------------------------------
    # IMarkupEngine — derive_bundle_cost_floor alias (skeleton contract)
    # ------------------------------------------------------------------

    async def derive_bundle_cost_floor(
        self, agent_type: str, bundle_tier: str
    ) -> int:
        """
        Alias satisfying IMarkupEngine.derive_bundle_cost_floor().
        Delegates to cost_floor() — reads bundle_profiles.cost_floor_paise.
        DO NOT recompute (ADR-036, WC027-01a).
        """
        return await self.cost_floor(agent_type, bundle_tier)