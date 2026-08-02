# Implements: WC027 — WC027-01a
# constitutional_basis: C-059, C-082
from __future__ import annotations

import math
import datetime
from typing import Optional

from pydantic import BaseModel, Field
from skeleton.wbe_interfaces import IMarkupEngine, PriceValidation


class ThreadEntry(BaseModel):
    thread_id: str = Field(..., description="Unique identifier for the billing thread")
    agent_type: str = Field(..., description="Type of agent associated with this thread")
    bundle_tier: str = Field(..., description="Bundle tier associated with this thread")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    metadata: Optional[dict] = Field(default=None, description="Optional metadata for the thread")


class BundleProfile(BaseModel):
    agent_type: str = Field(..., description="Type of agent this profile applies to")
    bundle_tier: str = Field(..., description="Bundle tier identifier")
    cost_floor_paise: int = Field(..., ge=0, description="Minimum cost floor in paise")
    minimum_margin_pct: float = Field(..., ge=0.0, le=100.0, description="Minimum required margin percentage")
    description: Optional[str] = Field(default=None, description="Human-readable description of the bundle profile")


class PriceConfig(BaseModel):
    agent_type: str = Field(..., description="Type of agent")
    bundle_tier: str = Field(..., description="Bundle tier")
    target_margin_pct: Optional[float] = Field(default=None, ge=0.0, lt=100.0, description="Target margin percentage")


class PriceValidationRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent")
    bundle_tier: str = Field(..., description="Bundle tier")
    proposed_price_paise: int = Field(..., ge=0, description="Proposed price in paise to validate")


class PriceDeriveRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent")
    bundle_tier: str = Field(..., description="Bundle tier")
    target_margin_pct: Optional[float] = Field(default=None, ge=0.0, lt=100.0, description="Target margin percentage override")


class BundleEngine(IMarkupEngine):
    def __init__(self, db_session):
        self.db = db_session

    def _get_bundle_profile(self, agent_type: str, bundle_tier: str) -> BundleProfile:
        row = (
            self.db.query("bundle_profiles")
            .filter_by(agent_type=agent_type, bundle_tier=bundle_tier)
            .first()
        )
        if row is None:
            raise ValueError(
                f"No bundle profile found for agent_type={agent_type!r}, bundle_tier={bundle_tier!r}"
            )
        return BundleProfile(
            agent_type=row.agent_type,
            bundle_tier=row.bundle_tier,
            cost_floor_paise=row.cost_floor_paise,
            minimum_margin_pct=row.minimum_margin_pct,
            description=getattr(row, "description", None),
        )

    def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        profile = self._get_bundle_profile(agent_type, bundle_tier)
        return profile.cost_floor_paise

    def derive_price(
        self,
        agent_type: str,
        bundle_tier: str,
        target_margin_pct: Optional[float] = None,
    ) -> int:
        profile = self._get_bundle_profile(agent_type, bundle_tier)
        floor = profile.cost_floor_paise
        margin = target_margin_pct if target_margin_pct is not None else profile.minimum_margin_pct
        if margin >= 100.0:
            raise ValueError("margin_pct must be less than 100")
        derived = floor / (1.0 - margin / 100.0)
        return math.ceil(derived)

    def validate_price(
        self,
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
    ) -> PriceValidation:
        profile = self._get_bundle_profile(agent_type, bundle_tier)
        floor = profile.cost_floor_paise
        margin = profile.minimum_margin_pct
        minimum_compliant = math.ceil(floor / (1.0 - margin / 100.0))

        if proposed_price_paise >= minimum_compliant:
            outcome = "APPROVED"
        else:
            outcome = "REJECTED"

        # C-059 audit obligation: write to pricing_floor_log on BOTH APPROVED and REJECTED
        self.db.execute(
            """
            INSERT INTO pricing_floor_log (
                agent_type,
                bundle_tier,
                proposed_price_paise,
                cost_floor_paise,
                minimum_compliant_price_paise,
                outcome,
                logged_at
            ) VALUES (
                :agent_type,
                :bundle_tier,
                :proposed_price_paise,
                :cost_floor_paise,
                :minimum_compliant_price_paise,
                :outcome,
                :logged_at
            )
            """,
            {
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "proposed_price_paise": proposed_price_paise,
                "cost_floor_paise": floor,
                "minimum_compliant_price_paise": minimum_compliant,
                "outcome": outcome,
                "logged_at": datetime.datetime.utcnow().isoformat(),
            },
        )
        self.db.commit()

        return PriceValidation(
            outcome=outcome,
            cost_floor_paise=floor,
            minimum_compliant_price_paise=minimum_compliant,
            proposed_price_paise=proposed_price_paise,
        )