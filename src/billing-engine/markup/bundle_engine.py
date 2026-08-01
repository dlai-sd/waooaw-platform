# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-089
from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from markup.models import PriceOutcome, PriceValidation

logger = logging.getLogger(__name__)


class BelowConstitutionalFloorError(Exception):
    """Raised when proposed price violates C-089 minimum margin floor."""

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
            "(cost floor %d paise, C-089)"
            % (proposed_price_paise, minimum_compliant_price_paise, cost_floor_paise)
        )


# ── DB engine (shared singleton) ─────────────────────────────────────────────
_engine: object | None = None
_async_session: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    """Create and return the shared AsyncSession factory."""
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session


class BundleEngine:
    """
    Markup Engine implementing IMarkupEngine.

    Constitutional obligations:
      C-089: Never price below cost (margin floor enforced in validate_price).
      C-059: Every validate_price call writes to pricing_floor_log (audit trail).
      C-063: No PII in log statements.
    """

    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        """Initialize BundleEngine with optional session factory override."""
        self._session_factory = session_factory or _get_session_factory()

    # ── Internal DB helpers ──────────────────────────────────────────────────

    async def _fetch_bundle_profile(
        self, agent_type: str, bundle_tier: str
    ) -> dict[str, int | float]:
        """
        Fetch cost_floor_paise and minimum_margin_pct from bundle_profiles.
        Returns dict with keys: cost_floor_paise (int), minimum_margin_pct (float).
        Raises ValueError if no matching profile found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT cost_floor_paise, minimum_margin_pct "
                    "FROM institutional.bundle_profiles "
                    "WHERE agent_type = :agent_type "
                    "  AND bundle_tier = :bundle_tier "
                    "  AND status = 'ACTIVE' "
                    "LIMIT 1"
                ),
                {"agent_type": agent_type, "bundle_tier": bundle_tier},
            )
            row = result.fetchone()

        if row is None:
            raise ValueError(
                "No active bundle profile found for agent_type=%s bundle_tier=%s"
                % (agent_type, bundle_tier)
            )
        return {
            "cost_floor_paise": int(row.cost_floor_paise),
            "minimum_margin_pct": float(row.minimum_margin_pct),
        }

    async def _write_pricing_floor_log(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        minimum_compliant_price_paise: int,
        outcome: str,
        log_id: UUID,
    ) -> None:
        """
        C-059 audit: write one row to pricing_floor_log for every validate_price call,
        regardless of APPROVED or REJECTED outcome.
        """
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO institutional.pricing_floor_log "
                    "(id, agent_type, bundle_tier, proposed_price_paise, "
                    " cost_floor_paise, minimum_compliant_price_paise, "
                    " outcome, created_at) "
                    "VALUES (:id, :agent_type, :bundle_tier, :proposed_price_paise, "
                    "        :cost_floor_paise, :minimum_compliant_price_paise, "
                    "        :outcome, :created_at)"
                ),
                {
                    "id": str(log_id),
                    "agent_type": agent_type,
                    "bundle_tier": bundle_tier,
                    "proposed_price_paise": proposed_price_paise,
                    "cost_floor_paise": cost_floor_paise,
                    "minimum_compliant_price_paise": minimum_compliant_price_paise,
                    "outcome": outcome,
                    "created_at": datetime.now(timezone.utc),
                },
            )
            await session.commit()

    # ── Public API ────────────────────────────────────────────────────────────

    async def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        """
        Return cost_floor_paise from bundle_profiles for the given agent_type
        and bundle_tier. Does NOT recompute — reads the DB column directly.

        Raises ValueError if no active profile found.
        """
        try:
            profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
            return profile["cost_floor_paise"]
        except asyncio.CancelledError:
            raise
        except ValueError:
            raise
        except Exception:
            logger.error(
                "cost_floor DB fetch failed for agent_type=%s bundle_tier=%s",
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
        Derive a compliant price using margin-on-revenue formula:
          price = cost_floor / (1 - margin_pct / 100)

        If target_margin_pct is None, uses bundle_profiles.minimum_margin_pct.

        Returns price in paise (int).
        Raises ValueError if no active profile or invalid margin.
        """
        try:
            profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
            cost_floor_paise = profile["cost_floor_paise"]
            margin_pct = (
                target_margin_pct
                if target_margin_pct is not None
                else profile["minimum_margin_pct"]
            )

            if margin_pct >= 100.0:
                raise ValueError(
                    "margin_pct must be less than 100; got %s", margin_pct
                )
            if margin_pct < 0.0:
                raise ValueError("margin_pct must be non-negative; got %s", margin_pct)

            # Margin-on-revenue: price = floor / (1 - margin/100)
            denominator = 1.0 - (margin_pct / 100.0)
            if denominator <= 0.0:
                raise ValueError(
                    "margin_pct calculation invalid; denominator=%s", denominator
                )

            price_paise = math.ceil(cost_floor_paise / denominator)
            logger.info(
                "derive_price: agent_type=%s bundle_tier=%s "
                "cost_floor=%d margin_pct=%s price=%d",
                agent_type,
                bundle_tier,
                cost_floor_paise,
                margin_pct,
                price_paise,
            )
            return price_paise

        except asyncio.CancelledError:
            raise
        except ValueError:
            raise
        except Exception:
            logger.error(
                "derive_price failed for agent_type=%s bundle_tier=%s margin=%s",
                agent_type,
                bundle_tier,
                target_margin_pct,
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
        Validate proposed price against C-089 margin floor.

        Returns PriceValidation with:
          - outcome: PriceOutcome.APPROVED or REJECTED
          - cost_floor_paise: the cost floor from DB
          - minimum_compliant_price_paise: minimum price allowed (cost_floor using minimum_margin_pct)
          - proposed_price_paise: the input price

        C-059: Writes to pricing_floor_log for BOTH APPROVED and REJECTED outcomes.
        C-089: Rejects prices below minimum_compliant_price_paise.

        Raises ValueError if no active profile found.
        """
        log_id = uuid4()

        try:
            profile = await self._fetch_bundle_profile(agent_type, bundle_tier)
            cost_floor_paise = profile["cost_floor_paise"]
            minimum_margin_pct = profile["minimum_margin_pct"]

            # Compute minimum compliant price using minimum_margin_pct
            # formula: price = cost_floor / (1 - margin / 100)
            denominator = 1.0 - (minimum_margin_pct / 100.0)
            if denominator <= 0.0:
                raise ValueError(
                    "minimum_margin_pct calculation invalid; denominator=%s",
                    denominator,
                )

            minimum_compliant_price_paise = math.ceil(cost_floor_paise / denominator)

            # Determine outcome
            if proposed_price_paise >= minimum_compliant_price_paise:
                outcome = PriceOutcome.APPROVED
            else:
                outcome = PriceOutcome.REJECTED

            # C-059: Write audit log (before returning)
            await self._write_pricing_floor_log(
                agent_type=agent_type,
                bundle_tier=bundle_tier,
                proposed_price_paise=proposed_price_paise,
                cost_floor_paise=cost_floor_paise,
                minimum_compliant_price_paise=minimum_compliant_price_paise,
                outcome=outcome.value,
                log_id=log_id,
            )

            logger.info(
                "validate_price: agent_type=%s bundle_tier=%s "
                "proposed=%d floor=%d compliant=%d outcome=%s log_id=%s",
                agent_type,
                bundle_tier,
                proposed_price_paise,
                cost_floor_paise,
                minimum_compliant_price_paise,
                outcome.value,
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
        except ValueError:
            raise
        except Exception:
            logger.error(
                "validate_price failed for agent_type=%s bundle_tier=%s proposed=%d log_id=%s",
                agent_type,
                bundle_tier,
                proposed_price_paise,
                str(log_id),
                exc_info=True,
                extra={"context": "validate_price"},
            )
            raise