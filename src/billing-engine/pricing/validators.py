# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""One validator per pricing kind, each returning machine-readable violations (WC-136 C5-01).

Body shapes (camelCase JSON):

* RATE: threadId, provider?, unit?, rawCostPaise, fxBufferPct, opsOverheadPct, riskPremiumPct
* PACKAGE: see ``markup.package_models.PackageBody``
* POLICY: minimumMarginPct, paymentGraceDays, sunsetNoticeDays, costToleranceFraction, costAlertFraction,
  upgradeTiming, downgradeTiming (IMMEDIATE or AT_RENEWAL), changeSizeGuardPercent, priceMultipleGuard
* GRANT: grantKind (TRIAL or SETUP), agentType, agentVersion, threadUnits or amountPaise, durationDays, disabled
* BUDGET: scope, reference, maximumPaise, perVisitorMessages?, perDayNewSessions?
* COUPON: code, agentType, agentVersion, percentOff or amountPaise, capPaise?, expiresAt, reason, maxRedemptions
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from markup.package_engine import (
    AgentDeclarationSource,
    PackageReferenceData,
    ThreadRate,
    base_price_paise,
    evaluate_package,
    marked_up_rate_paise,
    minimum_compliant_price_paise,
    project_package,
    round_half_up_div,
)
from markup.package_models import PackageBody, PackageEvaluation
from pricing.models import (
    BudgetBody,
    CouponBody,
    GrantBody,
    PolicyBody,
    PricingKind,
    RateBody,
    Violation,
)

SCHEMA_VIOLATION_CODE = "PRICING_BODY_SCHEMA"
ENVIRONMENT_CEILING_SCOPE = "ENVIRONMENT_CEILING"

_BODY_MODELS: dict[PricingKind, type[BaseModel]] = {
    PricingKind.RATE: RateBody,
    PricingKind.PACKAGE: PackageBody,
    PricingKind.POLICY: PolicyBody,
    PricingKind.GRANT: GrantBody,
    PricingKind.BUDGET: BudgetBody,
    PricingKind.COUPON: CouponBody,
}


@dataclass(frozen=True)
class ValidationContext:
    """Everything a validator may consult; validators never write."""

    reference: PackageReferenceData
    declarations: AgentDeclarationSource
    minimum_margin_pct: float | None = None
    deploy_maximum_paise: int | None = None
    require_availability: bool = False
    coupon_packages: Sequence[PackageBody] = ()
    now: datetime | None = None
    rate_overrides: Mapping[str, ThreadRate] | None = None


@dataclass
class ValidationOutcome:
    """``body`` and ``subject_key`` are None when the body does not even fit the schema of its kind."""

    body: dict[str, Any] | None
    subject_key: str | None
    violations: list[Violation] = field(default_factory=list)
    evaluation: PackageEvaluation | None = None
    derived: dict[str, Any] = field(default_factory=dict)

    @property
    def schema_valid(self) -> bool:
        return self.body is not None

    @property
    def valid(self) -> bool:
        return self.body is not None and not self.violations


def schema_violations(error: ValidationError) -> list[Violation]:
    violations: list[Violation] = []
    for item in error.errors(include_url=False, include_context=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "body"
        violations.append(
            Violation(code=SCHEMA_VIOLATION_CODE, field=location, message=str(item["msg"]), details={"type": item["type"]})
        )
    return violations


def parse_body(kind: PricingKind, raw: Mapping[str, Any]) -> tuple[BaseModel | None, list[Violation]]:
    """Schema-only validation of a body; no reference data is consulted."""
    try:
        return _BODY_MODELS[kind].model_validate(dict(raw)), []
    except ValidationError as error:
        return None, schema_violations(error)


def canonical_body(model: BaseModel) -> dict[str, Any]:
    """The stored form of a body: camelCase keys, JSON types, absent optionals omitted."""
    return model.model_dump(by_alias=True, mode="json", exclude_none=True)


def subject_key_for(kind: PricingKind, model: BaseModel) -> str:
    """The stable identity under which versions of one subject are numbered."""
    if isinstance(model, RateBody):
        return f"thread:{model.thread_id}"
    if isinstance(model, PackageBody):
        return f"package:{model.agent_type}|{model.agent_version}|{model.package_code}"
    if isinstance(model, PolicyBody):
        return "policy:platform"
    if isinstance(model, GrantBody):
        return f"grant:{model.grant_kind}|{model.agent_type}|{model.agent_version}"
    if isinstance(model, BudgetBody):
        return f"budget:{model.scope}|{model.reference}"
    if isinstance(model, CouponBody):
        return f"coupon:{model.code}"
    raise ValueError(f"no subject key for kind {kind.value}")


def minimum_margin_of(policy_body: Mapping[str, Any] | None) -> float | None:
    """The minimum margin percentage of a stored POLICY body, or None when it carries none."""
    if policy_body is None:
        return None
    value = policy_body.get("minimumMarginPct")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


async def _validate_rate(model: RateBody, context: ValidationContext, outcome: ValidationOutcome) -> None:
    rates = await context.reference.thread_rates([model.thread_id])
    if model.thread_id not in rates:
        outcome.violations.append(
            Violation(
                code="RATE_THREAD_UNKNOWN",
                field="threadId",
                message=f"The catalogue has no entry {model.thread_id}.",
                details={"threadId": model.thread_id},
            )
        )
    total_pct = model.fx_buffer_pct + model.ops_overhead_pct + model.risk_premium_pct
    outcome.derived = {
        "totalMarkupPct": round(total_pct, 2),
        "markedUpCostPaise": marked_up_rate_paise(
            model.raw_cost_paise, model.fx_buffer_pct, model.ops_overhead_pct, model.risk_premium_pct
        ),
    }


def _validate_policy(model: PolicyBody, outcome: ValidationOutcome) -> None:
    if model.cost_alert_fraction > model.cost_tolerance_fraction:
        outcome.violations.append(
            Violation(
                code="POLICY_ALERT_ABOVE_TOLERANCE",
                field="costAlertFraction",
                message="The cost alert fraction must not exceed the cost tolerance fraction.",
            )
        )
    for key, value in (model.model_extra or {}).items():
        if not isinstance(value, str):
            outcome.violations.append(
                Violation(
                    code="POLICY_FIELD_UNKNOWN",
                    field=key,
                    message=f"{key} is not a policy field; only text annotations are tolerated.",
                )
            )


async def _validate_grant(model: GrantBody, context: ValidationContext, outcome: ValidationOutcome) -> None:
    if not model.thread_units:
        return
    rates = await context.reference.thread_rates(sorted(model.thread_units))
    for thread_id in sorted(model.thread_units):
        if thread_id not in rates:
            outcome.violations.append(
                Violation(
                    code="GRANT_THREAD_UNKNOWN",
                    field=f"threadUnits.{thread_id}",
                    message=f"The catalogue has no entry {thread_id}.",
                    details={"threadId": thread_id},
                )
            )


def _validate_budget(model: BudgetBody, context: ValidationContext, outcome: ValidationOutcome) -> None:
    if model.scope != ENVIRONMENT_CEILING_SCOPE:
        return
    if context.deploy_maximum_paise is None:
        outcome.violations.append(
            Violation(
                code="BUDGET_DEPLOY_MAXIMUM_REQUIRED",
                field="maximumPaise",
                message="The deploy-time maximum was not supplied, so the ceiling cannot be checked.",
            )
        )
    elif model.maximum_paise > context.deploy_maximum_paise:
        outcome.violations.append(
            Violation(
                code="PRICING_CEILING_ABOVE_MAXIMUM",
                field="maximumPaise",
                message="The ceiling is above the deploy-time maximum.",
                details={"deployMaximumPaise": context.deploy_maximum_paise},
            )
        )


def coupon_discount_paise(price_incl_gst_paise: int, model: CouponBody) -> int:
    """Largest discount the coupon can give on one package price (cap applied, never above the price)."""
    if model.percent_off is not None:
        discount = round_half_up_div(price_incl_gst_paise * model.percent_off, 100)
    else:
        discount = model.amount_paise or 0
    if model.cap_paise is not None:
        discount = min(discount, model.cap_paise)
    return min(discount, price_incl_gst_paise)


async def _validate_coupon(model: CouponBody, context: ValidationContext, outcome: ValidationOutcome) -> None:
    if context.now is not None and model.expires_at <= context.now:
        outcome.violations.append(
            Violation(code="COUPON_EXPIRED", field="expiresAt", message="The coupon expiry is not in the future.")
        )
    packages = [
        package
        for package in context.coupon_packages
        if package.agent_type == model.agent_type and package.agent_version == model.agent_version
    ]
    if not packages:
        outcome.violations.append(
            Violation(
                code="COUPON_FLOOR_UNVERIFIABLE",
                field="agentVersion",
                message="No effective package exists for the agent version, so the cost floor cannot be verified.",
                details={"agentType": model.agent_type, "agentVersion": model.agent_version},
            )
        )
        return
    thread_ids = sorted({entry.thread_id for pkg in packages for comp in pkg.components for entry in comp.recipe})
    rates = dict(await context.reference.thread_rates(thread_ids))
    rates.update(context.rate_overrides or {})
    for package in packages:
        floor = project_package(package, rates, None).cost_floor_paise
        discounted = package.price_incl_gst_paise - coupon_discount_paise(package.price_incl_gst_paise, model)
        if base_price_paise(discounted, package.gst_rate_percent) < floor:
            outcome.violations.append(
                Violation(
                    code="PRICING_BELOW_FLOOR",
                    field="percentOff" if model.percent_off is not None else "amountPaise",
                    message=f"The discounted price of package {package.package_code} is below its cost floor.",
                    details={
                        "packageCode": package.package_code,
                        "discountedPricePaise": discounted,
                        "costFloorPaise": floor,
                        "minimumCompliantPricePaise": minimum_compliant_price_paise(floor, 0, package.gst_rate_percent),
                    },
                )
            )


async def validate_body(kind: PricingKind, raw: Mapping[str, Any], context: ValidationContext) -> ValidationOutcome:
    """Validate a body of ``kind``: schema first, then the rules that consult reference data."""
    model, schema_errors = parse_body(kind, raw)
    if model is None:
        return ValidationOutcome(body=None, subject_key=None, violations=schema_errors)
    outcome = ValidationOutcome(body=canonical_body(model), subject_key=subject_key_for(kind, model))
    if isinstance(model, RateBody):
        await _validate_rate(model, context, outcome)
    elif isinstance(model, PackageBody):
        evaluation = await evaluate_package(
            model,
            reference=context.reference,
            declarations=context.declarations,
            minimum_margin_pct=context.minimum_margin_pct,
            require_availability=context.require_availability,
            rate_overrides=context.rate_overrides,
        )
        outcome.evaluation = evaluation
        outcome.violations.extend(evaluation.violations)
    elif isinstance(model, PolicyBody):
        _validate_policy(model, outcome)
    elif isinstance(model, GrantBody):
        await _validate_grant(model, context, outcome)
    elif isinstance(model, BudgetBody):
        _validate_budget(model, context, outcome)
    elif isinstance(model, CouponBody):
        await _validate_coupon(model, context, outcome)
    return outcome
