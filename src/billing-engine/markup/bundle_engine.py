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
from markup.models import PriceValidation, PriceValidationOutcome
from skeleton.wbe_interfaces import IMarkupEngine, BelowConstitutionalFloorError

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


# ── BundleEngine ─────────────────────────────────────────────────────────────


class BundleEngine(IMarkupEngine):
    """
    Markup Engine — constitutional implementation of IMarkupEngine.

    C-089: Price may never be set below cost floor (minimum margin gate).
    C-059: Every validate_price() call writes to pricing_floor_log regardless of outcome.
    C-063: No PII in any log statement.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_bundle_profile(
        self, session: AsyncSession, agent_type: str, bundle_tier: str
    ) -> dict:
        """
        Fetch bundle profile row from DB.
        Returns dict with keys: cost_floor_paise, minimum_margin_pct.
        Raises ValueError if not found.
        """
        result = await session.execute(
            text(
                "SELECT cost_floor_paise, minimum_margin_pct "
                "FROM institutional.bundle_profiles "
                "WHERE agent_type = :agent_type AND bundle_tier = :bundle_tier "
                "  AND status != 'DEPRECATED' "
                "LIMIT 1"
            ),
            {"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError(
                "bundle_profiles row not found for agent_type=%s bundle_tier=%s",
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
        now = datetime.now(timezone.utc)
        await session.execute(
            text(
                "INSERT INTO institutional.pricing_floor_log "
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

    # ------------------------------------------------------------------
    # IMarkupEngine implementation
    # ------------------------------------------------------------------

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Return the pre-computed cost_floor_paise from bundle_profiles.
        DO NOT recompute — reads the DB column directly (spec WC027-01a).

        Raises:
            ValueError: if bundle_profiles row not found.
            asyncio.CancelledError: propagated without swallowing.
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
        except ValueError:
            logger.error(
                "bundle_profiles lookup failed: agent_type=%s bundle_tier=%s",
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
        Derive minimum viable price using margin-on-revenue formula:
            price = floor / (1 - margin / 100)

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.
        Result is rounded up to nearest paise (ceiling int).

        Raises:
            ValueError: if bundle_profiles row not found or margin >= 100.
            asyncio.CancelledError: propagated without swallowing.
        """
        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                floor_paise = profile["cost_floor_paise"]
                margin_pct = (
                    target_margin_pct
                    if target_margin_pct is not None
                    else profile["minimum_margin_pct"]
                )

                if margin_pct >= 100.0:
                    raise ValueError(
                        "margin_pct must be < 100 to produce a finite price"
                    )

                # Margin-on-revenue formula (spec WC027-01a)
                price_exact = floor_paise / (1.0 - margin_pct / 100.0)

                # Ceiling to nearest paise — never round down (C-089)
                import math
                price_paise = math.ceil(price_exact)

                logger.info(
                    "derive_price: floor=%d margin_pct=%.4f derived=%d",
                    floor_paise,
                    margin_pct,
                    price_paise,
                )
                return price_paise

        except asyncio.CancelledError:
            raise
        except ValueError:
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
        """
        Validate that proposed_price_paise meets the constitutional margin floor (C-089).

        Always writes to pricing_floor_log regardless of outcome (C-059 audit obligation).
        Returns PriceValidation with outcome, cost_floor_paise,
        minimum_compliant_price_paise, and proposed_price_paise.

        Raises:
            BelowConstitutionalFloorError: if proposed price is below minimum compliant price.
            ValueError: if bundle_profiles row not found.
            asyncio.CancelledError: propagated without swallowing.
        """
        import math

        factory = _get_session_factory()
        try:
            async with factory() as session:
                profile = await self._fetch_bundle_profile(
                    session, agent_type, bundle_tier
                )
                floor_paise = profile["cost_floor_paise"]
                minimum_margin_pct = profile["minimum_margin_pct"]

                if minimum_margin_pct >= 100.0:
                    raise ValueError(
                        "minimum_margin_pct must be < 100 to compute a finite floor price"
                    )

                # Minimum compliant price: floor / (1 - min_margin/100), ceiling
                min_price_exact = floor_paise / (1.0 - minimum_margin_pct / 100.0)
                minimum_compliant_price_paise = math.ceil(min_price_exact)

                approved = proposed_price_paise >= minimum_compliant_price_paise
                outcome = (
                    PriceValidationOutcome.APPROVED
                    if approved
                    else PriceValidationOutcome.REJECTED
                )

                # C-059: write audit log on BOTH outcomes
                log_id = await self._write_pricing_floor_log(
                    session,
                    agent_type,
                    bundle_tier,
                    proposed_price_paise,
                    floor_paise,
                    minimum_compliant_price_paise,
                    outcome.value,
                )

                logger.info(
                    "validate_price: outcome=%s log_id=%s proposed=%d min_compliant=%d floor=%d",
                    outcome.value,
                    log_id,
                    proposed_price_paise,
                    minimum_compliant_price_paise,
                    floor_paise,
                )

                if not approved:
                    # C-089: raise constitutional floor error so callers can surface HTTP 422
                    raise BelowConstitutionalFloorError(
                        agent_type=agent_type,
                        bundle_tier=bundle_tier,
                        proposed_price_paise=proposed_price_paise,
                        minimum_compliant_price_paise=minimum_compliant_price_paise,
                        cost_floor_paise=floor_paise,
                        log_id=log_id,
                        validation=PriceValidation(
                            outcome=outcome,
                            cost_floor_paise=floor_paise,
                            minimum_compliant_price_paise=minimum_compliant_price_paise,
                            proposed_price_paise=proposed_price_paise,
                            log_id=log_id,
                        ),
                    )

                return PriceValidation(
                    outcome=outcome,
                    cost_floor_paise=floor_paise,
                    minimum_compliant_price_paise=minimum_compliant_price_paise,
                    proposed_price_paise=proposed_price_paise,
                    log_id=log_id,
                )

        except asyncio.CancelledError:
            raise
        except BelowConstitutionalFloorError:
            # Re-raise — callers (router) translate this to HTTP 422
            raise
        except ValueError:
            logger.error(
                "validate_price failed for agent_type=%s bundle_tier=%s",
                agent_type,
                bundle_tier,
                exc_info=True,
            )
            raise

    async def derive_bundle_cost_floor(
        self, agent_type: str, bundle_tier: str
    ) -> int:
        """
        IMarkupEngine interface alias for cost_floor().
        Delegates to cost_floor() — do NOT recompute.
        """
        return await self.cost_floor(agent_type, bundle_tier)