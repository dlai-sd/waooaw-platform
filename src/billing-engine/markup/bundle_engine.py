# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from temporalio import activity, workflow

from markup.models import (
    ThreadEntry,
    BundleProfile,
    THREAD_CATALOG,
    COST_FLOOR_MAP,
    AgentType,
    BundleTier,
)

logger = logging.getLogger(__name__)


class BundleEngine:
    """Core engine for bundle pricing derivation and validation."""

    def get_thread_entry(self, agent_type: str, bundle_tier: str) -> Optional[ThreadEntry]:
        """Retrieve a ThreadEntry for the given agent_type and bundle_tier."""
        match = next(
            (
                e
                for e in THREAD_CATALOG
                if e["agent_type"] == agent_type.lower()
                and e["bundle_tier"] == bundle_tier.lower()
            ),
            None,
        )
        if match is None:
            return None
        return ThreadEntry(
            thread_id=match["thread_id"],
            agent_type=match["agent_type"],
            bundle_tier=match["bundle_tier"],
            description=match["description"],
            cost_floor=match["cost_floor"],
            markup_pct=match["markup_pct"],
        )

    def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        base_cost: Optional[Decimal] = None,
    ) -> BundleProfile:
        """Derive a final price for the given agent/tier combination."""
        key = (agent_type.lower(), bundle_tier.lower())
        cost_floor = COST_FLOOR_MAP.get(key)
        if cost_floor is None:
            raise ValueError(
                f"No cost floor found for agent_type={agent_type} bundle_tier={bundle_tier}"
            )

        thread_entry = self.get_thread_entry(agent_type, bundle_tier)
        markup_pct = thread_entry.markup_pct if thread_entry else Decimal("0.20")

        effective_base = base_cost if base_cost is not None else cost_floor
        raw_derived = effective_base * (Decimal("1") + markup_pct)
        final_price = max(raw_derived, cost_floor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        profile_id = f"profile-{agent_type.lower()}-{bundle_tier.lower()}"
        return BundleProfile(
            profile_id=profile_id,
            agent_type=agent_type.lower(),
            bundle_tier=bundle_tier.lower(),
            cost_floor=cost_floor,
            markup_pct=markup_pct,
            derived_price=final_price,
            base_cost=effective_base,
        )

    def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price: Decimal,
    ) -> tuple[bool, list[str]]:
        """Validate that a proposed price meets the cost floor."""
        errors: list[str] = []
        key = (agent_type.lower(), bundle_tier.lower())
        cost_floor = COST_FLOOR_MAP.get(key)
        if cost_floor is None:
            raise ValueError(
                f"No cost floor found for agent_type={agent_type} bundle_tier={bundle_tier}"
            )
        if proposed_price < cost_floor:
            errors.append(
                f"proposed_price {proposed_price} is below cost floor {cost_floor} "
                f"for agent_type={agent_type} bundle_tier={bundle_tier}"
            )
        return len(errors) == 0, errors

    def list_threads(self) -> list[ThreadEntry]:
        """Return all available thread entries."""
        return [
            ThreadEntry(
                thread_id=entry["thread_id"],
                agent_type=entry["agent_type"],
                bundle_tier=entry["bundle_tier"],
                description=entry["description"],
                cost_floor=entry["cost_floor"],
                markup_pct=entry["markup_pct"],
            )
            for entry in THREAD_CATALOG
        ]


@activity.defn
async def derive_bundle_price_activity(
    agent_type: str,
    bundle_tier: str,
    base_cost_str: Optional[str] = None,
) -> dict:
    """Temporal activity: derive bundle price for agent_type/bundle_tier."""
    engine = BundleEngine()
    base_cost = Decimal(base_cost_str) if base_cost_str is not None else None
    profile = engine.derive_price(agent_type, bundle_tier, base_cost)
    return {
        "profile_id": profile.profile_id,
        "agent_type": profile.agent_type,
        "bundle_tier": profile.bundle_tier,
        "cost_floor": str(profile.cost_floor),
        "markup_pct": str(profile.markup_pct),
        "derived_price": str(profile.derived_price),
        "base_cost": str(profile.base_cost),
    }


@activity.defn
async def validate_bundle_price_activity(
    agent_type: str,
    bundle_tier: str,
    proposed_price_str: str,
) -> dict:
    """Temporal activity: validate a proposed price against the cost floor."""
    engine = BundleEngine()
    proposed_price = Decimal(proposed_price_str)
    valid, errors = engine.validate_price(agent_type, bundle_tier, proposed_price)
    return {"valid": valid, "errors": errors}


@activity.defn
async def list_thread_catalog_activity() -> dict:
    """Temporal activity: list all thread catalog entries."""
    engine = BundleEngine()
    threads = engine.list_threads()
    return {
        "threads": [
            {
                "thread_id": t.thread_id,
                "agent_type": t.agent_type,
                "bundle_tier": t.bundle_tier,
                "description": t.description,
                "cost_floor": str(t.cost_floor),
                "markup_pct": str(t.markup_pct),
            }
            for t in threads
        ],
        "count": len(threads),
    }


@workflow.defn
class BundlePricingWorkflow:
    """Temporal workflow: orchestrate bundle pricing derivation."""

    @workflow.run
    async def run(
        self,
        agent_type: str,
        bundle_tier: str,
        base_cost_str: Optional[str] = None,
    ) -> dict:
        result: dict = await workflow.execute_activity(
            derive_bundle_price_activity,
            args=[agent_type, bundle_tier, base_cost_str],
            start_to_close_timeout=__import__("datetime").timedelta(seconds=30),
        )
        return result


@workflow.defn
class BundleValidationWorkflow:
    """Temporal workflow: orchestrate bundle price validation."""

    @workflow.run
    async def run(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_str: str,
    ) -> dict:
        result: dict = await workflow.execute_activity(
            validate_bundle_price_activity,
            args=[agent_type, bundle_tier, proposed_price_str],
            start_to_close_timeout=__import__("datetime").timedelta(seconds=30),
        )
        return result