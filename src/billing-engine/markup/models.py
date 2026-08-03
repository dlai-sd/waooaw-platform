# Implements: WC027-01a — WC027-01aa
# constitutional_basis: C-059, C-082
from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class AgentType(StrEnum):
    standard = "standard"
    premium = "premium"
    enterprise = "enterprise"


class BundleTier(StrEnum):
    basic = "basic"
    professional = "professional"
    elite = "elite"


class ThreadEntry(BaseModel):
    thread_id: str
    agent_type: str
    bundle_tier: str
    description: str
    cost_floor: Decimal
    markup_pct: Decimal


class BundleProfile(BaseModel):
    profile_id: str
    agent_type: str
    bundle_tier: str
    cost_floor: Decimal
    markup_pct: Decimal
    derived_price: Decimal
    base_cost: Decimal


THREAD_CATALOG: list[dict] = [
    {
        "thread_id": "thread-standard-basic",
        "agent_type": "standard",
        "bundle_tier": "basic",
        "description": "Standard agent, basic bundle tier",
        "cost_floor": Decimal("10.00"),
        "markup_pct": Decimal("0.15"),
    },
    {
        "thread_id": "thread-standard-professional",
        "agent_type": "standard",
        "bundle_tier": "professional",
        "description": "Standard agent, professional bundle tier",
        "cost_floor": Decimal("25.00"),
        "markup_pct": Decimal("0.18"),
    },
    {
        "thread_id": "thread-standard-elite",
        "agent_type": "standard",
        "bundle_tier": "elite",
        "description": "Standard agent, elite bundle tier",
        "cost_floor": Decimal("50.00"),
        "markup_pct": Decimal("0.20"),
    },
    {
        "thread_id": "thread-premium-basic",
        "agent_type": "premium",
        "bundle_tier": "basic",
        "description": "Premium agent, basic bundle tier",
        "cost_floor": Decimal("20.00"),
        "markup_pct": Decimal("0.20"),
    },
    {
        "thread_id": "thread-premium-professional",
        "agent_type": "premium",
        "bundle_tier": "professional",
        "description": "Premium agent, professional bundle tier",
        "cost_floor": Decimal("45.00"),
        "markup_pct": Decimal("0.22"),
    },
    {
        "thread_id": "thread-premium-elite",
        "agent_type": "premium",
        "bundle_tier": "elite",
        "description": "Premium agent, elite bundle tier",
        "cost_floor": Decimal("90.00"),
        "markup_pct": Decimal("0.25"),
    },
    {
        "thread_id": "thread-enterprise-basic",
        "agent_type": "enterprise",
        "bundle_tier": "basic",
        "description": "Enterprise agent, basic bundle tier",
        "cost_floor": Decimal("50.00"),
        "markup_pct": Decimal("0.25"),
    },
    {
        "thread_id": "thread-enterprise-professional",
        "agent_type": "enterprise",
        "bundle_tier": "professional",
        "description": "Enterprise agent, professional bundle tier",
        "cost_floor": Decimal("100.00"),
        "markup_pct": Decimal("0.28"),
    },
    {
        "thread_id": "thread-enterprise-elite",
        "agent_type": "enterprise",
        "bundle_tier": "elite",
        "description": "Enterprise agent, elite bundle tier",
        "cost_floor": Decimal("200.00"),
        "markup_pct": Decimal("0.30"),
    },
]

COST_FLOOR_MAP: dict[tuple[str, str], Decimal] = {
    (entry["agent_type"], entry["bundle_tier"]): entry["cost_floor"]
    for entry in THREAD_CATALOG
}