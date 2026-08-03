# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from temporalio import activity, workflow

from markup.models import AgentType, BundleTier, BundleProfile, ThreadEntry

logger = logging.getLogger(__name__)


class BundleEngine:
    """Core pricing and bundle derivation engine for the billing service."""

    # Markup rates by tier
    _TIER_MARKUP: dict[str, Decimal] = {
        BundleTier.BASIC: Decimal("0.10"),
        BundleTier.PROFESSIONAL: Decimal("0.15"),
        BundleTier.ELITE: Decimal("0.20"),
    }

    # Agent type multipliers
    _AGENT_MULTIPLIER: dict[str, Decimal] = {
        AgentType.STANDARD: Decimal("1.00"),
        AgentType.PREMIUM: Decimal("1.25"),
        AgentType.ENTERPRISE: Decimal("1.75"),
    }

    # Cost floors per (agent_type, bundle_tier)
    _COST_FLOOR: dict[tuple[str, str], Decimal] = {
        ("standard", "basic"): Decimal("9.99"),
        ("standard", "professional"): Decimal("29.99"),
        ("standard", "elite"): Decimal("79.99"),
        ("premium", "basic"): Decimal("19.99"),
        ("premium", "professional"): Decimal("59.99"),
        ("premium", "elite"): Decimal("149.99"),
        ("enterprise", "basic"): Decimal("49.99"),
        ("enterprise", "professional"): Decimal("129.99"),
        ("enterprise", "elite"): Decimal("299.99"),
    }

    def validate_bundle(self, profile: BundleProfile) -> list[str]:
        """Validate a BundleProfile and return a list of validation errors."""
        errors: list[str] = []

        floor_key = (profile.agent_type.lower(), profile.bundle_tier.lower())
        floor = self._COST_FLOOR.get(floor_key)
        if floor is not None and profile.base_price < floor:
            errors.append(
                f"base_price is below the minimum cost floor for "
                f"agent_type={profile.agent_type}, bundle_tier={profile.bundle_tier}"
            )

        if profile.markup_override is not None:
            if not (Decimal("0") <= profile.markup_override <= Decimal("1")):
                errors.append("markup_override must be between 0 and 1 inclusive")

        if not profile.bundle_id or not profile.bundle_id.strip():
            errors.append("bundle_id must not be empty")

        return errors

    def derive_pricing(self, profile: BundleProfile) -> dict[str, Any]:
        """Derive final pricing from a BundleProfile."""
        markup_rate = (
            profile.markup_override
            if profile.markup_override is not None
            else self._TIER_MARKUP.get(profile.bundle_tier, Decimal("0.15"))
        )

        agent_multiplier = self._AGENT_MULTIPLIER.get(profile.agent_type, Decimal("1.00"))
        adjusted_base = profile.base_price * agent_multiplier
        final_price = adjusted_base * (Decimal("1") + markup_rate)
        final_price = final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "bundle_id": profile.bundle_id,
            "agent_type": str(profile.agent_type),
            "bundle_tier": str(profile.bundle_tier),
            "base_price": str(profile.base_price),
            "agent_multiplier": str(agent_multiplier),
            "adjusted_base": str(adjusted_base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "markup_rate": str(markup_rate),
            "final_price": str(final_price),
            "thread_count": len(profile.thread_ids),
        }

    def get_cost_floor(self, agent_type: str, bundle_tier: str) -> Decimal | None:
        """Return the cost floor for a given agent_type and bundle_tier, or None if not defined."""
        key = (agent_type.lower(), bundle_tier.lower())
        return self._COST_FLOOR.get(key)

    def apply_thread_markup(self, thread: ThreadEntry) -> dict[str, Any]:
        """Apply markup to a single ThreadEntry and return pricing details."""
        markup_rate = thread.markup_rate
        final_cost = thread.base_cost * (Decimal("1") + markup_rate)
        final_cost = final_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "thread_id": thread.thread_id,
            "thread_name": thread.thread_name,
            "agent_type": str(thread.agent_type),
            "bundle_tier": str(thread.bundle_tier),
            "base_cost": str(thread.base_cost),
            "markup_rate": str(markup_rate),
            "final_cost": str(final_cost),
            "is_active": thread.is_active,
        }

    def build_bundle_summary(
        self,
        profile: BundleProfile,
        threads: list[ThreadEntry],
    ) -> dict[str, Any]:
        """Build a complete bundle summary combining profile pricing and thread details."""
        errors = self.validate_bundle(profile)
        if errors:
            return {"valid": False, "errors": errors}

        pricing = self.derive_pricing(profile)
        thread_details = [self.apply_thread_markup(t) for t in threads if t.is_active]

        total_thread_cost = sum(
            Decimal(td["final_cost"]) for td in thread_details
        )

        return {
            "valid": True,
            "bundle_pricing": pricing,
            "thread_details": thread_details,
            "total_thread_cost": str(total_thread_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "active_thread_count": len(thread_details),
        }


# ---------------------------------------------------------------------------
# Temporal activity definitions
# ---------------------------------------------------------------------------

@activity.defn(name="validate_bundle_activity")
async def validate_bundle_activity(bundle_data: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity: validate a bundle profile."""
    engine = BundleEngine()
    profile = BundleProfile(**bundle_data)
    errors = engine.validate_bundle(profile)
    # PII must not appear in logs — log only non-PII identifiers
    logger.info("validate_bundle_activity completed for bundle_id=%s", profile.bundle_id)
    return {"valid": len(errors) == 0, "errors": errors}


@activity.defn(name="derive_pricing_activity")
async def derive_pricing_activity(bundle_data: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity: derive pricing for a bundle profile."""
    engine = BundleEngine()
    profile = BundleProfile(**bundle_data)
    errors = engine.validate_bundle(profile)
    if errors:
        return {"success": False, "errors": errors, "pricing": None}
    pricing = engine.derive_pricing(profile)
    logger.info("derive_pricing_activity completed for bundle_id=%s", profile.bundle_id)
    return {"success": True, "errors": [], "pricing": pricing}


@activity.defn(name="build_bundle_summary_activity")
async def build_bundle_summary_activity(
    bundle_data: dict[str, Any],
    threads_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Temporal activity: build a full bundle summary."""
    engine = BundleEngine()
    profile = BundleProfile(**bundle_data)
    threads = [ThreadEntry(**t) for t in threads_data]
    summary = engine.build_bundle_summary(profile, threads)
    logger.info("build_bundle_summary_activity completed for bundle_id=%s", profile.bundle_id)
    return summary


# ---------------------------------------------------------------------------
# Temporal workflow definition
# ---------------------------------------------------------------------------

@workflow.defn(name="BundlePricingWorkflow")
class BundlePricingWorkflow:
    """Temporal workflow that orchestrates bundle validation and pricing derivation."""

    @workflow.run
    async def run(self, bundle_data: dict[str, Any]) -> dict[str, Any]:
        from datetime import timedelta

        validation_result: dict[str, Any] = await workflow.execute_activity(
            validate_bundle_activity,
            bundle_data,
            start_to_close_timeout=timedelta(seconds=30),
        )

        if not validation_result.get("valid"):
            return {
                "success": False,
                "stage": "validation",
                "errors": validation_result.get("errors", []),
                "pricing": None,
            }

        pricing_result: dict[str, Any] = await workflow.execute_activity(
            derive_pricing_activity,
            bundle_data,
            start_to_close_timeout=timedelta(seconds=30),
        )

        if not pricing_result.get("success"):
            return {
                "success": False,
                "stage": "pricing",
                "errors": pricing_result.get("errors", []),
                "pricing": None,
            }

        return {
            "success": True,
            "stage": "complete",
            "errors": [],
            "pricing": pricing_result.get("pricing"),
        }

# Module-level initialization for bundle_engine.py
engine = BundleEngine()

engine = BundleEngine()
