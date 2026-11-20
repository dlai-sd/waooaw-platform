# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-02
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Pricing simulator: what a draft would do, computed without writing any state (WC-136 C5-02).

A PACKAGE draft is simulated against the current thread rates with three built-in usage profiles and
any persona from a supplied usage profile file. A RATE draft lists every effective package whose cost
floor would change. Nothing here touches a repository; the caller decides what to persist.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import Field

from markup.package_engine import (
    ThreadRate,
    base_price_paise,
    margin_on_revenue_pct,
    marked_up_rate_paise,
    parse_package_body,
    project_package,
    round_half_up_div,
    sale_readiness_violations,
)
from markup.package_models import CamelModel, PackageBody, PackageProjection, Violation
from pricing.models import PricingKind, PricingVersion, RateBody
from pricing.validators import ValidationContext, validate_body

BEST_CASE = "BEST_CASE"
TYPICAL = "TYPICAL"
WORST_CASE = "WORST_CASE"
BEST_CASE_USAGE_PERCENT = 20
TYPICAL_USAGE_PERCENT = 60
WORST_CASE_TERMINATION_DAY = 2
DAYS_PER_WEEK = 7
SECONDS_PER_DAY = 86400
NEEDS_SECOND_CONFIRMATION_WARNING = "NEEDS_SECOND_CONFIRMATION"


class PersonaProfile(CamelModel):
    """Share of each component a persona uses over one period, in percent."""

    name: str = Field(min_length=1, max_length=100)
    usage_percent_by_component: dict[str, int] = Field(default_factory=dict)
    default_usage_percent: int = Field(default=0, ge=0, le=100)


BUILT_IN_PROFILES: tuple[PersonaProfile, ...] = (
    PersonaProfile(name=BEST_CASE, default_usage_percent=BEST_CASE_USAGE_PERCENT),
    PersonaProfile(name=TYPICAL, default_usage_percent=TYPICAL_USAGE_PERCENT),
)


class FieldChange(CamelModel):
    field: str
    before: Any | None = None
    after: Any | None = None


class ProfileCost(CamelModel):
    profile: str
    component_units: dict[str, int]
    variable_cost_paise: int
    infrastructure_share_paise: int
    total_cost_paise: int
    base_price_paise: int
    margin_paise: int
    margin_pct: float | None


class WorstCase(CamelModel):
    """Everything is attempted on day one, then the customer ends the engagement on day two."""

    profile: str = WORST_CASE
    attempted_units: dict[str, int]
    day_one_released_units: dict[str, int]
    pacing_limited: bool
    attempted_cost_paise: int
    day_one_exposure_paise: int
    refund_paise: int
    retained_price_paise: int
    retained_base_paise: int
    margin_after_refund_paise: int


class AffectedPackage(CamelModel):
    version_id: str
    subject_key: str
    cost_floor_before_paise: int
    cost_floor_after_paise: int
    margin_pct_after: float | None
    breaches_cost_floor: bool
    breaches_minimum_margin: bool


class SimulationReport(CamelModel):
    kind: str
    subject_key: str | None
    has_effective_version: bool
    violations: list[Violation]
    warnings: list[Violation]
    needs_second_confirmation: bool
    changes: list[FieldChange]
    projection: PackageProjection | None = None
    projection_changes: list[FieldChange] = Field(default_factory=list)
    profiles: list[ProfileCost] = Field(default_factory=list)
    worst_case: WorstCase | None = None
    affected_packages: list[AffectedPackage] = Field(default_factory=list)
    derived: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class SimulationContext:
    validation: ValidationContext
    effective_version: PricingVersion | None = None
    effective_packages: Sequence[PricingVersion] = ()
    needs_second_confirmation: bool = False
    personas: Sequence[PersonaProfile] = ()


def parse_persona_profiles(raw: Mapping[str, Any]) -> list[PersonaProfile]:
    """Personas of a usage profile file: ``{"personas": [{"name", "usagePercentByComponent", ...}]}``."""
    personas = raw.get("personas")
    if not isinstance(personas, list):
        raise ValueError("a usage profile file carries a personas list")
    return [PersonaProfile.model_validate(item) for item in personas]


def load_persona_profiles(path: Path) -> list[PersonaProfile]:
    return parse_persona_profiles(json.loads(path.read_text(encoding="utf-8")))


def _flatten(value: Any, prefix: str, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            _flatten(value[key], f"{prefix}.{key}" if prefix else str(key), out)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            label = str(index)
            if isinstance(item, dict):
                label = str(item.get("componentId") or item.get("threadId") or index)
            _flatten(item, f"{prefix}[{label}]", out)
    else:
        out[prefix] = value


def diff_bodies(before: Mapping[str, Any] | None, after: Mapping[str, Any]) -> list[FieldChange]:
    """Field-level differences of two version bodies; empty when there is nothing to compare against."""
    if before is None:
        return []
    flat_before: dict[str, Any] = {}
    flat_after: dict[str, Any] = {}
    _flatten(dict(before), "", flat_before)
    _flatten(dict(after), "", flat_after)
    return [
        FieldChange(field=name, before=flat_before.get(name), after=flat_after.get(name))
        for name in sorted(set(flat_before) | set(flat_after))
        if flat_before.get(name) != flat_after.get(name)
    ]


def _ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def day_one_release(quantity: int, cadence: str, billing_period_days: int) -> int:
    """Units a component releases on its first day: pacing is what bounds day-one exposure."""
    if cadence == "UPFRONT":
        return quantity
    if cadence == "WEEKLY":
        return _ceil_div(quantity, max(1, billing_period_days // DAYS_PER_WEEK))
    return _ceil_div(quantity, billing_period_days)


def _profile_cost(body: PackageBody, projection: PackageProjection, profile: PersonaProfile) -> ProfileCost:
    units: dict[str, int] = {}
    variable = 0
    for component, cost in zip(body.components, projection.component_costs, strict=True):
        percent = profile.usage_percent_by_component.get(component.component_id, profile.default_usage_percent)
        used = round_half_up_div(component.quantity * percent, 100)
        units[component.component_id] = used
        variable += used * cost.unit_cost_paise
    total = variable + body.infrastructure_share_paise
    base = projection.base_price_paise
    return ProfileCost(
        profile=profile.name,
        component_units=units,
        variable_cost_paise=variable,
        infrastructure_share_paise=body.infrastructure_share_paise,
        total_cost_paise=total,
        base_price_paise=base,
        margin_paise=base - total,
        margin_pct=margin_on_revenue_pct(base, total),
    )


def worst_case(body: PackageBody, projection: PackageProjection) -> WorstCase:
    attempted: dict[str, int] = {}
    released: dict[str, int] = {}
    attempted_variable = 0
    released_variable = 0
    refund = 0
    remaining_days = body.billing_period_days - (WORST_CASE_TERMINATION_DAY - 1)
    period_seconds = body.billing_period_days * SECONDS_PER_DAY
    for component, cost in zip(body.components, projection.component_costs, strict=True):
        first_day = min(component.quantity, day_one_release(component.quantity, component.cadence, body.billing_period_days))
        attempted[component.component_id] = component.quantity
        released[component.component_id] = first_day
        attempted_variable += component.quantity * cost.unit_cost_paise
        released_variable += first_day * cost.unit_cost_paise
        refund += round_half_up_div(component.price_allocation_paise * remaining_days * SECONDS_PER_DAY, period_seconds)
    refund = min(refund, projection.price_incl_gst_paise)
    retained_price = projection.price_incl_gst_paise - refund
    retained_base = base_price_paise(retained_price, body.gst_rate_percent)
    exposure = released_variable + body.infrastructure_share_paise
    return WorstCase(
        attempted_units=attempted,
        day_one_released_units=released,
        pacing_limited=any(released[key] < attempted[key] for key in attempted),
        attempted_cost_paise=attempted_variable + body.infrastructure_share_paise,
        day_one_exposure_paise=exposure,
        refund_paise=refund,
        retained_price_paise=retained_price,
        retained_base_paise=retained_base,
        margin_after_refund_paise=retained_base - exposure,
    )


def _projection_changes(before: PackageProjection, after: PackageProjection) -> list[FieldChange]:
    fields = (
        "price_incl_gst_paise",
        "base_price_paise",
        "gst_paise",
        "cost_floor_paise",
        "margin_pct",
        "minimum_compliant_price_paise",
    )
    changes: list[FieldChange] = []
    for name in fields:
        old, new = getattr(before, name), getattr(after, name)
        if old != new:
            changes.append(FieldChange(field=name, before=old, after=new))
    return changes


async def _package_projection_changes(
    context: SimulationContext, after: PackageProjection
) -> list[FieldChange]:
    effective = context.effective_version
    if effective is None:
        return []
    previous = parse_package_body(effective.body)
    thread_ids = sorted({entry.thread_id for item in previous.components for entry in item.recipe})
    reference = context.validation.reference
    rates = dict(await reference.thread_rates(thread_ids))
    rates.update(context.validation.rate_overrides or {})
    return _projection_changes(
        project_package(previous, rates, context.validation.minimum_margin_pct), after
    )


async def _affected_packages(
    rate: RateBody, derived_cost_paise: int, context: SimulationContext
) -> list[AffectedPackage]:
    reference = context.validation.reference
    minimum_margin = context.validation.minimum_margin_pct
    affected: list[AffectedPackage] = []
    for version in context.effective_packages:
        body = parse_package_body(version.body)
        thread_ids = sorted({entry.thread_id for item in body.components for entry in item.recipe})
        if rate.thread_id not in thread_ids:
            continue
        rates = dict(await reference.thread_rates(thread_ids))
        before = project_package(body, rates, minimum_margin)
        rates[rate.thread_id] = ThreadRate(rate.thread_id, derived_cost_paise, True)
        after = project_package(body, rates, minimum_margin)
        if before.cost_floor_paise == after.cost_floor_paise:
            continue
        minimum_base = after.minimum_compliant_base_paise
        affected.append(
            AffectedPackage(
                version_id=str(version.version_id),
                subject_key=version.subject_key,
                cost_floor_before_paise=before.cost_floor_paise,
                cost_floor_after_paise=after.cost_floor_paise,
                margin_pct_after=after.margin_pct,
                breaches_cost_floor=after.base_price_paise < after.cost_floor_paise,
                breaches_minimum_margin=minimum_base is not None and after.base_price_paise < minimum_base,
            )
        )
    return affected


async def simulate_draft(draft: PricingVersion, context: SimulationContext) -> SimulationReport:
    """Simulate a draft. Reads reference data only; never writes state."""
    outcome = await validate_body(draft.kind, draft.body, context.validation)
    warnings: list[Violation] = []
    if context.needs_second_confirmation:
        warnings.append(
            Violation(
                code=NEEDS_SECOND_CONFIRMATION_WARNING,
                field="body",
                message="The change is larger than the change-size guard; submitting needs a second confirmation.",
            )
        )
    report = SimulationReport(
        kind=draft.kind.value,
        subject_key=outcome.subject_key or draft.subject_key,
        has_effective_version=context.effective_version is not None,
        violations=outcome.violations,
        warnings=warnings,
        needs_second_confirmation=context.needs_second_confirmation,
        changes=[] if outcome.body is None else diff_bodies(
            None if context.effective_version is None else context.effective_version.body, outcome.body
        ),
        derived=outcome.derived,
    )
    if outcome.body is None:
        return report
    if draft.kind is PricingKind.PACKAGE and outcome.evaluation is not None:
        body = parse_package_body(outcome.body)
        projection = outcome.evaluation.projection
        declaration = await context.validation.declarations.declaration(body.agent_type, body.agent_version)
        if declaration is not None:
            report.warnings.extend(sale_readiness_violations(body, declaration))
        report.projection = projection
        report.projection_changes = await _package_projection_changes(context, projection)
        report.profiles = [
            _profile_cost(body, projection, profile) for profile in (*BUILT_IN_PROFILES, *context.personas)
        ]
        report.worst_case = worst_case(body, projection)
    elif draft.kind is PricingKind.RATE:
        rate = RateBody.model_validate(outcome.body)
        derived_cost = marked_up_rate_paise(
            rate.raw_cost_paise, rate.fx_buffer_pct, rate.ops_overhead_pct, rate.risk_premium_pct
        )
        report.affected_packages = await _affected_packages(rate, derived_cost, context)
    return report
