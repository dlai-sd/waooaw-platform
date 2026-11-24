# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-06
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Typed PACKAGE version body and evaluation results (WC-136 Appendix A.2).

Money is integer paise and is always GST-inclusive for the customer price; the base price and GST
are derived. Field names on the wire are camelCase, exactly as the pricing version body stores them.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

ComponentKind = Literal["COUNTED", "SELECTED", "TIME_ACCESS", "CAPACITY"]
Cadence = Literal["SPREAD", "UPFRONT", "DAILY", "WEEKLY"]
Availability = Literal["AVAILABLE", "DEFAULT_OFF", "UNAVAILABLE"]

DEFAULT_GST_RATE_PERCENT = 18
PROACTIVE_MESSAGE_COMPONENT_ID = "PROACTIVE_MESSAGE"
PROACTIVE_MESSAGE_QUANTITY = 30


class CamelModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=to_camel)


class Violation(CamelModel):
    """One machine-readable reason a draft is not acceptable."""

    code: str
    field: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RecipeEntry(CamelModel):
    thread_id: str = Field(min_length=1, max_length=50)
    units_per_unit: int = Field(gt=0)


class PackageComponent(CamelModel):
    component_id: str = Field(min_length=1, max_length=100)
    kind: ComponentKind
    quantity: int = Field(ge=1)
    cadence: Cadence = "SPREAD"
    selectable_maximum: int | None = Field(default=None, ge=1)
    price_allocation_paise: int = Field(ge=0)
    recipe: list[RecipeEntry] = Field(default_factory=list)
    topup_allowed: bool = False


class PackageBody(CamelModel):
    agent_type: str = Field(min_length=1, max_length=50)
    agent_version: str = Field(min_length=1, max_length=32)
    package_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    display_name: str = Field(min_length=1, max_length=100)
    billing_period_days: int = Field(gt=0, le=366)
    price_incl_gst_paise: int = Field(gt=0)
    gst_rate_percent: int = Field(default=DEFAULT_GST_RATE_PERCENT, ge=0, le=100)
    infrastructure_share_paise: int = Field(ge=0)
    components: list[PackageComponent] = Field(min_length=1)
    description: str | None = Field(default=None, max_length=500)
    target_margin_pct: float | None = Field(default=None, ge=0, lt=100)


class ComponentCost(CamelModel):
    component_id: str
    quantity: int
    unit_cost_paise: int
    total_cost_paise: int


class CostLine(CamelModel):
    """One ingredient line of one component; an unknown rate is None, never zero."""

    component_id: str
    thread_id: str
    quantity: int
    units_per_unit: int
    unit_cost_paise: int | None
    line_cost_paise: int | None
    authorized: bool


SuggestionStatus = Literal["COMPLETE", "INCOMPLETE", "UNUSABLE"]


class PackageProjection(CamelModel):
    """Everything derived from a package body at the current thread rates."""

    price_incl_gst_paise: int
    base_price_paise: int
    gst_paise: int
    infrastructure_share_paise: int
    cost_floor_paise: int
    margin_pct: float | None
    minimum_margin_pct: float | None
    minimum_compliant_base_paise: int | None
    minimum_compliant_price_paise: int | None
    component_costs: list[ComponentCost]
    thread_rations: dict[str, int]
    unauthorized_thread_ids: list[str]
    cost_lines: list[CostLine] = Field(default_factory=list)
    uncosted_component_ids: list[str] = Field(default_factory=list)
    target_margin_pct: float | None = None
    suggested_price_incl_gst_paise: int | None = None
    suggestion_status: SuggestionStatus = "UNUSABLE"


class PackageEvaluation(CamelModel):
    projection: PackageProjection
    violations: list[Violation]

    @property
    def valid(self) -> bool:
        return not self.violations
