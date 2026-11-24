# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-06
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Package projection, cost floor and package rule validation (architecture 6.11.1).

Pure functions compute base price, GST, cost floor, margin on revenue and the minimum compliant price
with integer arithmetic only, so every result is deterministic. ``evaluate_package`` applies the package
rules through two injected ports: thread rates and billing-profile authority, and the agent declaration.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_models import (
    PROACTIVE_MESSAGE_COMPONENT_ID,
    PROACTIVE_MESSAGE_QUANTITY,
    ComponentCost,
    CostLine,
    PackageBody,
    PackageComponent,
    PackageEvaluation,
    PackageProjection,
    SuggestionStatus,
    Violation,
)

BILLING_PROFILE_AUTHORIZED = "FOUNDER_AUTHORIZED"
CATALOGUE_ACTIVE = "ACTIVE"
DAYS_PER_WEEK = 7


@dataclass(frozen=True)
class ThreadRate:
    """A thread catalogue entry as the package engine prices it (marked-up cost per unit)."""

    thread_id: str
    marked_up_cost_paise: int
    authorized: bool


@dataclass(frozen=True)
class DeclaredComponent:
    component_id: str
    kind: str
    availability: str


@dataclass(frozen=True)
class AgentDeclaration:
    """The component vocabulary an agent version declares (architecture 6.11)."""

    agent_type: str
    agent_version: str
    components: Mapping[str, DeclaredComponent] = field(default_factory=dict)


class PackageReferenceData(Protocol):
    async def thread_rates(self, thread_ids: Sequence[str]) -> dict[str, ThreadRate]: ...

    async def billing_profile_authorized(self, agent_type: str) -> bool: ...


class AgentDeclarationSource(Protocol):
    async def declaration(self, agent_type: str, agent_version: str) -> AgentDeclaration | None: ...


class StaticDeclarationSource:
    """Declaration source over a fixed collection (a snapshot supplied by the caller)."""

    def __init__(self, declarations: Iterable[AgentDeclaration]) -> None:
        self._declarations = {(item.agent_type, item.agent_version): item for item in declarations}

    async def declaration(self, agent_type: str, agent_version: str) -> AgentDeclaration | None:
        return self._declarations.get((agent_type, agent_version))


class SqlPackageReferenceData:
    """Reads the thread catalogue and billing profiles (C-088, C-091) with the WBE application role."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def thread_rates(self, thread_ids: Sequence[str]) -> dict[str, ThreadRate]:
        if not thread_ids:
            return {}
        result = await self._session.execute(
            text(
                """
                SELECT thread_id, marked_up_cost_paise, status, founder_authorized_at
                FROM institutional.thread_catalog
                WHERE thread_id = ANY(CAST(:thread_ids AS TEXT[]))
                """
            ),
            {"thread_ids": list(thread_ids)},
        )
        return {
            row.thread_id: ThreadRate(
                thread_id=row.thread_id,
                marked_up_cost_paise=int(row.marked_up_cost_paise),
                authorized=row.status == CATALOGUE_ACTIVE and row.founder_authorized_at is not None,
            )
            for row in result.fetchall()
        }

    async def billing_profile_authorized(self, agent_type: str) -> bool:
        result = await self._session.execute(
            text("SELECT status FROM institutional.billing_profiles WHERE agent_type = :agent_type"),
            {"agent_type": agent_type},
        )
        row = result.fetchone()
        return row is not None and row[0] == BILLING_PROFILE_AUTHORIZED


def round_half_up_div(numerator: int, denominator: int) -> int:
    """Integer division rounding half up; the denominator must be positive."""
    return (2 * numerator + denominator) // (2 * denominator)


def base_price_paise(price_incl_gst_paise: int, gst_rate_percent: int) -> int:
    """Price excluding GST: round(price / (1 + rate/100))."""
    return round_half_up_div(price_incl_gst_paise * 100, 100 + gst_rate_percent)


def marked_up_rate_paise(
    raw_cost_paise: int,
    fx_buffer_pct: Decimal | float | str,
    ops_overhead_pct: Decimal | float | str,
    risk_premium_pct: Decimal | float | str,
) -> int:
    """Catalogue rule: raw cost plus ROUND(raw cost x total markup percentage / 100), half up."""
    total_pct = Decimal(str(fx_buffer_pct)) + Decimal(str(ops_overhead_pct)) + Decimal(str(risk_premium_pct))
    markup = (Decimal(raw_cost_paise) * total_pct / Decimal(100)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return raw_cost_paise + int(markup)


def margin_on_revenue_pct(base_paise: int, cost_floor_paise: int) -> float | None:
    """Margin on revenue in percent with two decimals, or None when there is no revenue."""
    if base_paise <= 0:
        return None
    return round_half_up_div(10000 * (base_paise - cost_floor_paise), base_paise) / 100


def minimum_compliant_base_paise(cost_floor_paise: int, minimum_margin_pct: Decimal | float | str) -> int:
    """ceil(costFloor / (1 - minimumMarginPct/100)) in exact rational arithmetic."""
    margin = Fraction(str(minimum_margin_pct))
    if margin < 0 or margin >= 100:
        raise ValueError("minimum margin percentage must be at least 0 and below 100")
    return math.ceil(Fraction(cost_floor_paise) / (1 - margin / 100))


def minimum_compliant_price_paise(
    cost_floor_paise: int, minimum_margin_pct: Decimal | float | str, gst_rate_percent: int
) -> int:
    """Smallest GST-inclusive price whose base price reaches the minimum compliant base price."""
    needed_base = minimum_compliant_base_paise(cost_floor_paise, minimum_margin_pct)
    price = math.ceil(Fraction(needed_base * (100 + gst_rate_percent), 100))
    while base_price_paise(price, gst_rate_percent) < needed_base:
        price += 1
    while price > 1 and base_price_paise(price - 1, gst_rate_percent) >= needed_base:
        price -= 1
    return price


def cadence_consistent(component: PackageComponent, billing_period_days: int) -> bool:
    """Rule 1: the declared cadence must be able to release the quantity over the period."""
    if component.cadence == "DAILY":
        return component.quantity >= billing_period_days
    if component.cadence == "WEEKLY":
        releases = billing_period_days // DAYS_PER_WEEK
        return releases >= 1 and component.quantity >= releases
    return True


def parse_package_body(raw: Mapping[str, object]) -> PackageBody:
    """Validate a stored or submitted package body; raises pydantic.ValidationError."""
    return PackageBody.model_validate(dict(raw))


def suggested_price_paise(cost_floor_paise: int, target_margin_pct: Decimal | float | str, gst_rate_percent: int) -> int:
    """Price including GST that reaches the target margin, computed exactly and then rounded up to a whole rupee."""
    needed_base = minimum_compliant_base_paise(cost_floor_paise, target_margin_pct)
    exact_price = Fraction(needed_base * (100 + gst_rate_percent), 100)
    return math.ceil(exact_price / 100) * 100


def _suggestion(
    body: PackageBody,
    cost_floor: int,
    minimum_margin_pct: Decimal | float | str | None,
    *,
    incomplete: bool,
) -> tuple[float | None, int | None, SuggestionStatus]:
    """Target margin, suggested price and how far the suggestion can be trusted.

    A margin of zero set on the package is a real target and never falls back to the policy margin.
    """
    target: Decimal | float | str | None = (
        body.target_margin_pct if body.target_margin_pct is not None else minimum_margin_pct
    )
    if target is None or cost_floor <= 0:
        return (None if target is None else float(Decimal(str(target))), None, "UNUSABLE")
    try:
        price = suggested_price_paise(cost_floor, target, body.gst_rate_percent)
    except ValueError:
        return (float(Decimal(str(target))), None, "UNUSABLE")
    return (float(Decimal(str(target))), price, "INCOMPLETE" if incomplete else "COMPLETE")


def project_package(
    body: PackageBody,
    rates: Mapping[str, ThreadRate],
    minimum_margin_pct: Decimal | float | str | None,
) -> PackageProjection:
    """Cost floor, margin and minimum compliant price of a package at the given thread rates.

    A recipe thread without an authorized catalogue entry is listed in ``unauthorized_thread_ids``;
    its known cost counts and an unknown or pending entry counts as zero, which is why the floor of a
    package that still carries pending proactive-message threads excludes those messages. The cost
    lines show an unknown rate as unknown, and a component with no recipe is listed in
    ``uncosted_component_ids``; either makes the suggested price INCOMPLETE rather than final.
    """
    component_costs: list[ComponentCost] = []
    cost_lines: list[CostLine] = []
    uncosted: list[str] = []
    thread_rations: dict[str, int] = {}
    unauthorized: set[str] = set()
    for component in body.components:
        unit_cost = 0
        if not component.recipe:
            uncosted.append(component.component_id)
        for entry in component.recipe:
            rate = rates.get(entry.thread_id)
            if rate is None or not rate.authorized:
                unauthorized.add(entry.thread_id)
            if rate is not None:
                unit_cost += entry.units_per_unit * rate.marked_up_cost_paise
            cost_lines.append(
                CostLine(
                    component_id=component.component_id,
                    thread_id=entry.thread_id,
                    quantity=component.quantity,
                    units_per_unit=entry.units_per_unit,
                    unit_cost_paise=None if rate is None else rate.marked_up_cost_paise,
                    line_cost_paise=(
                        None
                        if rate is None
                        else component.quantity * entry.units_per_unit * rate.marked_up_cost_paise
                    ),
                    authorized=rate is not None and rate.authorized,
                )
            )
            thread_rations[entry.thread_id] = (
                thread_rations.get(entry.thread_id, 0) + component.quantity * entry.units_per_unit
            )
        component_costs.append(
            ComponentCost(
                component_id=component.component_id,
                quantity=component.quantity,
                unit_cost_paise=unit_cost,
                total_cost_paise=component.quantity * unit_cost,
            )
        )
    cost_floor = body.infrastructure_share_paise + sum(item.total_cost_paise for item in component_costs)
    base = base_price_paise(body.price_incl_gst_paise, body.gst_rate_percent)
    minimum_base: int | None = None
    minimum_price: int | None = None
    if minimum_margin_pct is not None:
        minimum_base = minimum_compliant_base_paise(cost_floor, minimum_margin_pct)
        minimum_price = minimum_compliant_price_paise(cost_floor, minimum_margin_pct, body.gst_rate_percent)
    target_margin, suggested_price, suggestion_status = _suggestion(
        body, cost_floor, minimum_margin_pct, incomplete=bool(unauthorized or uncosted)
    )
    return PackageProjection(
        price_incl_gst_paise=body.price_incl_gst_paise,
        base_price_paise=base,
        gst_paise=body.price_incl_gst_paise - base,
        infrastructure_share_paise=body.infrastructure_share_paise,
        cost_floor_paise=cost_floor,
        margin_pct=margin_on_revenue_pct(base, cost_floor),
        minimum_margin_pct=None if minimum_margin_pct is None else float(Decimal(str(minimum_margin_pct))),
        minimum_compliant_base_paise=minimum_base,
        minimum_compliant_price_paise=minimum_price,
        component_costs=component_costs,
        thread_rations=dict(sorted(thread_rations.items())),
        unauthorized_thread_ids=sorted(unauthorized),
        cost_lines=cost_lines,
        uncosted_component_ids=uncosted,
        target_margin_pct=target_margin,
        suggested_price_incl_gst_paise=suggested_price,
        suggestion_status=suggestion_status,
    )


def sale_readiness_violations(body: PackageBody, declaration: AgentDeclaration) -> list[Violation]:
    """A package is sold only when every component is AVAILABLE (PACKAGE_COMPONENT_NOT_AVAILABLE)."""
    violations: list[Violation] = []
    for index, component in enumerate(body.components):
        declared = declaration.components.get(component.component_id)
        availability = "UNAVAILABLE" if declared is None else declared.availability
        if availability != "AVAILABLE":
            violations.append(
                Violation(
                    code="PACKAGE_COMPONENT_NOT_AVAILABLE",
                    field=f"components[{index}].componentId",
                    message=f"Component {component.component_id} is {availability} and cannot be sold yet.",
                    details={"componentId": component.component_id, "availability": availability},
                )
            )
    return violations


def _structure_violations(body: PackageBody) -> list[Violation]:
    violations: list[Violation] = []
    allocated = sum(component.price_allocation_paise for component in body.components)
    if allocated != body.price_incl_gst_paise:
        violations.append(
            Violation(
                code="PACKAGE_ALLOCATION_MISMATCH",
                field="components[].priceAllocationPaise",
                message="Component price allocations must add up exactly to the package price.",
                details={"allocatedPaise": allocated, "pricePaise": body.price_incl_gst_paise},
            )
        )
    seen: set[str] = set()
    for index, component in enumerate(body.components):
        if component.component_id in seen:
            violations.append(
                Violation(
                    code="PACKAGE_COMPONENT_DUPLICATE",
                    field=f"components[{index}].componentId",
                    message=f"Component {component.component_id} appears more than once.",
                    details={"componentId": component.component_id},
                )
            )
        seen.add(component.component_id)
        if not component.recipe:
            violations.append(
                Violation(
                    code="PACKAGE_RECIPE_MISSING",
                    field=f"components[{index}].recipe",
                    message=f"Component {component.component_id} needs at least one recipe thread.",
                    details={"componentId": component.component_id},
                )
            )
        if not cadence_consistent(component, body.billing_period_days):
            violations.append(
                Violation(
                    code="PACKAGE_CADENCE_INCONSISTENT",
                    field=f"components[{index}].cadence",
                    message=(
                        f"Cadence {component.cadence} cannot release quantity {component.quantity} "
                        f"over {body.billing_period_days} days."
                    ),
                    details={
                        "componentId": component.component_id,
                        "cadence": component.cadence,
                        "quantity": component.quantity,
                    },
                )
            )
        if component.kind == "SELECTED" and component.selectable_maximum is None:
            violations.append(
                Violation(
                    code="PACKAGE_SELECTABLE_MAXIMUM_REQUIRED",
                    field=f"components[{index}].selectableMaximum",
                    message=f"Selected component {component.component_id} needs a selectable maximum.",
                    details={"componentId": component.component_id},
                )
            )
        if component.kind != "SELECTED" and component.selectable_maximum is not None:
            violations.append(
                Violation(
                    code="PACKAGE_SELECTABLE_MAXIMUM_NOT_ALLOWED",
                    field=f"components[{index}].selectableMaximum",
                    message=f"Only selected components have a selectable maximum ({component.component_id}).",
                    details={"componentId": component.component_id},
                )
            )
    proactive = [c for c in body.components if c.component_id == PROACTIVE_MESSAGE_COMPONENT_ID]
    if not proactive or any(c.quantity != PROACTIVE_MESSAGE_QUANTITY for c in proactive):
        violations.append(
            Violation(
                code="PACKAGE_PROACTIVE_MESSAGE_REQUIRED",
                field="components[]",
                message=(
                    f"Every package carries {PROACTIVE_MESSAGE_COMPONENT_ID} with quantity "
                    f"{PROACTIVE_MESSAGE_QUANTITY}."
                ),
                details={"requiredQuantity": PROACTIVE_MESSAGE_QUANTITY},
            )
        )
    return violations


def package_shape_violations(body: PackageBody) -> list[Violation]:
    """Rules that need no reference data: allocations, recipes, cadence, selectable maximum, proactive."""
    return _structure_violations(body)


def _recipe_authorization_violations(body: PackageBody, projection: PackageProjection) -> list[Violation]:
    violations: list[Violation] = []
    for index, component in enumerate(body.components):
        for position, entry in enumerate(component.recipe):
            if entry.thread_id in projection.unauthorized_thread_ids:
                violations.append(
                    Violation(
                        code="RECIPE_THREAD_NOT_AUTHORIZED",
                        field=f"components[{index}].recipe[{position}].threadId",
                        message=f"Thread {entry.thread_id} has no active Founder-authorized catalogue entry.",
                        details={"componentId": component.component_id, "threadId": entry.thread_id},
                    )
                )
    return violations


def _declaration_violations(body: PackageBody, declaration: AgentDeclaration | None) -> list[Violation]:
    if declaration is None:
        return [
            Violation(
                code="PACKAGE_DECLARATION_UNAVAILABLE",
                field="agentVersion",
                message="The agent version declaration could not be found.",
                details={"agentType": body.agent_type, "agentVersion": body.agent_version},
            )
        ]
    violations: list[Violation] = []
    for index, component in enumerate(body.components):
        declared = declaration.components.get(component.component_id)
        if declared is None:
            violations.append(
                Violation(
                    code="PACKAGE_COMPONENT_UNKNOWN",
                    field=f"components[{index}].componentId",
                    message=f"Component {component.component_id} is not declared by the agent version.",
                    details={"componentId": component.component_id},
                )
            )
        elif declared.kind != component.kind:
            violations.append(
                Violation(
                    code="PACKAGE_COMPONENT_KIND_MISMATCH",
                    field=f"components[{index}].kind",
                    message=f"Component {component.component_id} is declared as {declared.kind}.",
                    details={"componentId": component.component_id, "declaredKind": declared.kind},
                )
            )
    return violations


async def evaluate_package(
    body: PackageBody,
    *,
    reference: PackageReferenceData,
    declarations: AgentDeclarationSource,
    minimum_margin_pct: Decimal | float | str | None,
    require_availability: bool = False,
    rate_overrides: Mapping[str, ThreadRate] | None = None,
) -> PackageEvaluation:
    """Project a package and apply every rule of architecture 6.11.1.

    ``rate_overrides`` replaces catalogue rates for what-if evaluation (a RATE draft). With
    ``require_availability`` the sale-readiness gate is applied as well.
    """
    thread_ids = sorted({entry.thread_id for component in body.components for entry in component.recipe})
    rates = dict(await reference.thread_rates(thread_ids))
    rates.update(rate_overrides or {})
    projection = project_package(body, rates, minimum_margin_pct)
    violations = _structure_violations(body)
    violations.extend(_recipe_authorization_violations(body, projection))
    if not await reference.billing_profile_authorized(body.agent_type):
        violations.append(
            Violation(
                code="BILLING_PROFILE_NOT_AUTHORIZED",
                field="agentType",
                message=f"Agent type {body.agent_type} has no Founder-authorized billing profile.",
                details={"agentType": body.agent_type},
            )
        )
    declaration = await declarations.declaration(body.agent_type, body.agent_version)
    violations.extend(_declaration_violations(body, declaration))
    if minimum_margin_pct is None:
        violations.append(
            Violation(
                code="PRICING_MARGIN_POLICY_MISSING",
                field="minimumMarginPct",
                message="No effective policy defines the minimum margin, so the floor cannot be enforced.",
            )
        )
    elif (
        projection.minimum_compliant_price_paise is not None
        and body.price_incl_gst_paise < projection.minimum_compliant_price_paise
    ):
        violations.append(
            Violation(
                code="PRICING_BELOW_FLOOR",
                field="priceInclGstPaise",
                message="The price is below the minimum compliant price.",
                details={
                    "minimumCompliantPricePaise": projection.minimum_compliant_price_paise,
                    "costFloorPaise": projection.cost_floor_paise,
                },
            )
        )
    if require_availability and declaration is not None:
        violations.extend(sale_readiness_violations(body, declaration))
    return PackageEvaluation(projection=projection, violations=violations)


def thread_ids_of(bodies: Collection[PackageBody]) -> list[str]:
    """Sorted distinct recipe thread ids across several package bodies."""
    return sorted({e.thread_id for body in bodies for c in body.components for e in c.recipe})
