# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from temporalio import activity, workflow

from markup.models import BundleProfile, ThreadEntry

logger = logging.getLogger(__name__)


class BundleEngine:
    """Core engine for bundle pricing derivation and validation."""

    def __init__(self, default_markup_pct: float = 15.0) -> None:
        self.default_markup_pct = default_markup_pct
        self._cost_floors: dict[tuple[str, str], float] = {
            ("gpt4", "standard"): 0.02,
            ("gpt4", "premium"): 0.035,
            ("claude", "standard"): 0.025,
            ("claude", "premium"): 0.04,
            ("gpt35", "standard"): 0.005,
            ("gpt35", "premium"): 0.01,
        }

    def get_cost_floor(self, agent_type: str, bundle_tier: str) -> Optional[float]:
        """Return the cost floor for a given agent_type and bundle_tier."""
        key = (agent_type.lower(), bundle_tier.lower())
        return self._cost_floors.get(key)

    def derive_price(self, profile: BundleProfile) -> float:
        """Derive the final price from a BundleProfile."""
        return round(profile.cost_floor * (1 + profile.markup_pct / 100.0), 6)

    def validate_profile(self, profile: BundleProfile) -> list[str]:
        """Validate a BundleProfile and return a list of error messages."""
        errors: list[str] = []
        if profile.markup_pct < 0:
            errors.append("markup_pct must be non-negative")
        if profile.markup_pct > 200:
            errors.append("markup_pct must not exceed 200")
        if profile.cost_floor < 0:
            errors.append("cost_floor must be non-negative")
        if not profile.bundle_tier:
            errors.append("bundle_tier is required")
        if not profile.agent_type:
            errors.append("agent_type is required")
        return errors

    def build_thread_catalog(self) -> list[ThreadEntry]:
        """Build the full thread catalog from known cost floors."""
        entries: list[ThreadEntry] = []
        for (agent_type, bundle_tier), cost_floor in self._cost_floors.items():
            thread_id = f"{bundle_tier}-{agent_type}"
            entries.append(
                ThreadEntry(
                    thread_id=thread_id,
                    agent_type=agent_type,
                    bundle_tier=bundle_tier,
                    cost_floor=cost_floor,
                    markup_pct=self.default_markup_pct,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return entries

    def derive_from_catalog(self, agent_type: str, bundle_tier: str) -> Optional[dict]:
        """Derive pricing for a specific agent_type/bundle_tier from the catalog."""
        cost_floor = self.get_cost_floor(agent_type, bundle_tier)
        if cost_floor is None:
            return None
        profile = BundleProfile(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            cost_floor=cost_floor,
            markup_pct=self.default_markup_pct,
        )
        derived_price = self.derive_price(profile)
        return {
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "cost_floor": cost_floor,
            "markup_pct": self.default_markup_pct,
            "derived_price": derived_price,
            "derived_at": datetime.now(timezone.utc).isoformat(),
        }


@activity.defn
async def derive_bundle_price_activity(
    agent_type: str,
    bundle_tier: str,
    markup_pct: float = 15.0,
) -> dict:
    """Temporal activity: derive bundle price for a given agent/tier."""
    engine = BundleEngine(default_markup_pct=markup_pct)
    cost_floor = engine.get_cost_floor(agent_type, bundle_tier)
    if cost_floor is None:
        raise ValueError(
            f"No cost floor found for agent_type={agent_type}, bundle_tier={bundle_tier}"
        )
    profile = BundleProfile(
        agent_type=agent_type,
        bundle_tier=bundle_tier,
        cost_floor=cost_floor,
        markup_pct=markup_pct,
    )
    errors = engine.validate_profile(profile)
    if errors:
        raise ValueError(f"Bundle profile validation failed: {errors}")
    derived_price = engine.derive_price(profile)
    return {
        "agent_type": agent_type,
        "bundle_tier": bundle_tier,
        "cost_floor": cost_floor,
        "markup_pct": markup_pct,
        "derived_price": derived_price,
        "derived_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn
async def validate_bundle_profile_activity(
    agent_type: str,
    bundle_tier: str,
    cost_floor: float,
    markup_pct: float,
) -> dict:
    """Temporal activity: validate a bundle profile."""
    engine = BundleEngine()
    profile = BundleProfile(
        agent_type=agent_type,
        bundle_tier=bundle_tier,
        cost_floor=cost_floor,
        markup_pct=markup_pct,
    )
    errors = engine.validate_profile(profile)
    return {"valid": len(errors) == 0, "errors": errors}


@activity.defn
async def get_thread_catalog_activity() -> list[dict]:
    """Temporal activity: retrieve the full thread catalog."""
    engine = BundleEngine()
    catalog = engine.build_thread_catalog()
    return [entry.model_dump() for entry in catalog]