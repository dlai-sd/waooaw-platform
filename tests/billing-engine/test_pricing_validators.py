# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-089, C-091
"""Per-kind pricing validators and the Appendix B.5 error mapping (WC-136 C5-01)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from pricing_support import (  # noqa: E402
    AGENT_TYPE,
    AGENT_VERSION,
    PACKAGE_SUBJECT,
    START,
    FakeReference,
    budget_body,
    dma_declarations,
    dma_package_body,
    grant_body,
    policy_body,
    rate_body,
)

from markup.package_engine import parse_package_body  # noqa: E402
from markup.package_models import Violation  # noqa: E402
from pricing.models import (  # noqa: E402
    PackageComponentNotAvailable,
    PricingBelowFloor,
    PricingCeilingAboveMaximum,
    PricingDraftInvalid,
    PricingKind,
    RecipeThreadNotAuthorized,
    error_for_violations,
)
from pricing.validators import (  # noqa: E402
    SCHEMA_VIOLATION_CODE,
    ValidationContext,
    coupon_discount_paise,
    minimum_margin_of,
    validate_body,
)

COUPON_EXPIRY = "2026-06-01T00:00:00Z"


def coupon_body(**changes):
    body = {
        "code": "WELCOME10",
        "agentType": AGENT_TYPE,
        "agentVersion": AGENT_VERSION,
        "percentOff": 10,
        "expiresAt": COUPON_EXPIRY,
        "reason": "Launch welcome",
        "maxRedemptions": 100,
    }
    body.update(changes)
    return body


def context(**changes) -> ValidationContext:
    values = {
        "reference": FakeReference(),
        "declarations": dma_declarations(),
        "minimum_margin_pct": 55,
        "deploy_maximum_paise": 50000,
        "now": START,
        "coupon_packages": [parse_package_body(dma_package_body())],
    }
    values.update(changes)
    return ValidationContext(**values)


def codes(outcome) -> list[str]:
    return [item.code for item in outcome.violations]


async def test_a_body_that_does_not_fit_its_kind_has_no_subject_and_a_schema_violation() -> None:
    negative = await validate_body(PricingKind.RATE, rate_body(raw=-1), context())
    assert not negative.schema_valid and not negative.valid
    assert negative.body is None and negative.subject_key is None
    assert codes(negative) == [SCHEMA_VIOLATION_CODE]
    assert "rawCostPaise" in negative.violations[0].field
    extra = await validate_body(PricingKind.RATE, {**rate_body(), "bogus": 1}, context())
    assert codes(extra) == [SCHEMA_VIOLATION_CODE]
    overlong = await validate_body(PricingKind.RATE, rate_body(fx=1000), context())
    assert codes(overlong) == [SCHEMA_VIOLATION_CODE]


async def test_rate_needs_a_catalogue_entry_and_reports_the_derived_markup() -> None:
    known = await validate_body(PricingKind.RATE, rate_body(), context())
    assert known.valid and known.subject_key == "thread:llm_pro"
    assert known.derived == {"totalMarkupPct": 33.0, "markedUpCostPaise": 399}
    assert known.body["rawCostPaise"] == 300 and known.body["threadId"] == "llm_pro"
    unknown = await validate_body(PricingKind.RATE, rate_body("never_heard_of"), context())
    assert codes(unknown) == ["RATE_THREAD_UNKNOWN"]
    assert unknown.violations[0].details == {"threadId": "never_heard_of"}


async def test_package_validation_applies_the_package_rules_and_keeps_the_evaluation() -> None:
    outcome = await validate_body(PricingKind.PACKAGE, dma_package_body(), context())
    assert outcome.valid and outcome.subject_key == PACKAGE_SUBJECT
    assert outcome.evaluation is not None and outcome.evaluation.projection.cost_floor_paise == 19778
    broken = dma_package_body()
    broken["components"][1]["priceAllocationPaise"] += 5
    assert codes(await validate_body(PricingKind.PACKAGE, broken, context())) == ["PACKAGE_ALLOCATION_MISMATCH"]
    for_sale = dma_declarations(overrides={"CHANNEL": "DEFAULT_OFF"})
    gated = await validate_body(
        PricingKind.PACKAGE, dma_package_body(), context(declarations=for_sale, require_availability=True)
    )
    assert codes(gated) == ["PACKAGE_COMPONENT_NOT_AVAILABLE"]


async def test_policy_fields_are_checked_and_only_text_annotations_are_tolerated() -> None:
    valid = await validate_body(PricingKind.POLICY, policy_body(), context())
    assert valid.valid and valid.subject_key == "policy:platform"
    assert valid.body["minimumMarginNote"] == "SEED_UNCONFIRMED"
    inverted = await validate_body(PricingKind.POLICY, policy_body(costAlertFraction=0.5), context())
    assert codes(inverted) == ["POLICY_ALERT_ABOVE_TOLERANCE"]
    surprise = await validate_body(PricingKind.POLICY, policy_body(surpriseKnob=3), context())
    assert codes(surprise) == ["POLICY_FIELD_UNKNOWN"]
    for bad in ({"minimumMarginPct": 100}, {"upgradeTiming": "SOMETIME"}, {"changeSizeGuardPercent": 0}):
        assert codes(await validate_body(PricingKind.POLICY, policy_body(**bad), context())) == [SCHEMA_VIOLATION_CODE]


async def test_grant_carries_units_or_paise_and_units_need_catalogue_entries() -> None:
    units = await validate_body(PricingKind.GRANT, grant_body(), context())
    assert units.valid and units.subject_key == "grant:TRIAL|DMA|1.0.0"
    assert units.body["threadUnits"] == {"llm_mid_gemini": 50} and "amountPaise" not in units.body
    paise = grant_body(grantKind="SETUP", amountPaise=2500)
    del paise["threadUnits"]
    assert (await validate_body(PricingKind.GRANT, paise, context())).valid
    both = grant_body(amountPaise=100)
    assert codes(await validate_body(PricingKind.GRANT, both, context())) == [SCHEMA_VIOLATION_CODE]
    neither = grant_body()
    del neither["threadUnits"]
    assert codes(await validate_body(PricingKind.GRANT, neither, context())) == [SCHEMA_VIOLATION_CODE]
    unknown = await validate_body(PricingKind.GRANT, grant_body(threadUnits={"nope": 1}), context())
    assert codes(unknown) == ["GRANT_THREAD_UNKNOWN"]


async def test_environment_ceiling_must_not_exceed_the_deploy_time_maximum() -> None:
    assert (await validate_body(PricingKind.BUDGET, budget_body(50000), context())).valid
    above = await validate_body(PricingKind.BUDGET, budget_body(50001), context())
    assert codes(above) == ["PRICING_CEILING_ABOVE_MAXIMUM"]
    assert above.violations[0].details == {"deployMaximumPaise": 50000}
    missing = await validate_body(PricingKind.BUDGET, budget_body(10), context(deploy_maximum_paise=None))
    assert codes(missing) == ["BUDGET_DEPLOY_MAXIMUM_REQUIRED"]
    acquisition = budget_body(999999, scope="ACQUISITION_TENANT", reference="tenant-a")
    outcome = await validate_body(PricingKind.BUDGET, acquisition, context(deploy_maximum_paise=None))
    assert outcome.valid and outcome.subject_key == "budget:ACQUISITION_TENANT|tenant-a"


def test_coupon_discount_applies_the_cap_and_never_exceeds_the_price() -> None:
    from pricing.models import CouponBody

    percent = CouponBody.model_validate(coupon_body(percentOff=10))
    assert coupon_discount_paise(200000, percent) == 20000
    capped = CouponBody.model_validate(coupon_body(percentOff=50, capPaise=1000))
    assert coupon_discount_paise(200000, capped) == 1000
    amount = CouponBody.model_validate({**coupon_body(amountPaise=500000), "percentOff": None})
    assert coupon_discount_paise(200000, amount) == 200000


async def test_coupon_discount_never_goes_below_the_package_cost_floor() -> None:
    fine = await validate_body(PricingKind.COUPON, coupon_body(), context())
    assert fine.valid and fine.subject_key == "coupon:WELCOME10"
    free = await validate_body(PricingKind.COUPON, coupon_body(percentOff=100), context())
    assert codes(free) == ["PRICING_BELOW_FLOOR"]
    details = free.violations[0].details
    assert details["costFloorPaise"] == 19778 and details["discountedPricePaise"] == 0
    assert details["minimumCompliantPricePaise"] > 0
    amount = coupon_body(amountPaise=195000)
    del amount["percentOff"]
    assert codes(await validate_body(PricingKind.COUPON, amount, context())) == ["PRICING_BELOW_FLOOR"]
    capped = await validate_body(PricingKind.COUPON, coupon_body(percentOff=100, capPaise=1000), context())
    assert capped.valid


async def test_coupon_needs_a_future_expiry_and_an_effective_package_to_verify_the_floor() -> None:
    expired = await validate_body(PricingKind.COUPON, coupon_body(expiresAt="2026-02-01T00:00:00Z"), context())
    assert codes(expired) == ["COUPON_EXPIRED"]
    no_package = await validate_body(PricingKind.COUPON, coupon_body(), context(coupon_packages=[]))
    assert codes(no_package) == ["COUPON_FLOOR_UNVERIFIABLE"]
    both = {**coupon_body(), "amountPaise": 100}
    assert codes(await validate_body(PricingKind.COUPON, both, context())) == [SCHEMA_VIOLATION_CODE]
    naive = coupon_body(expiresAt="2026-06-01T00:00:00")
    assert codes(await validate_body(PricingKind.COUPON, naive, context())) == [SCHEMA_VIOLATION_CODE]


@pytest.mark.parametrize(
    ("body", "expected"),
    [(None, None), ({}, None), ({"minimumMarginPct": "55"}, None), ({"minimumMarginPct": True}, None), ({"minimumMarginPct": 55}, 55.0)],
)
def test_minimum_margin_is_read_only_from_a_numeric_policy_field(body, expected) -> None:
    assert minimum_margin_of(body) == expected


def _violation(code: str, **details) -> Violation:
    return Violation(code=code, field="x", message="m", details=details)


def test_dedicated_appendix_b5_errors_are_used_when_every_violation_shares_the_code() -> None:
    below = error_for_violations([_violation("PRICING_BELOW_FLOOR", minimumCompliantPricePaise=51469)])
    assert isinstance(below, PricingBelowFloor) and below.code == "PRICING_BELOW_FLOOR"
    assert below.status_code == 422 and below.minimum_compliant_price_paise == 51469
    assert isinstance(error_for_violations([_violation("PRICING_CEILING_ABOVE_MAXIMUM")]), PricingCeilingAboveMaximum)
    assert isinstance(error_for_violations([_violation("PACKAGE_COMPONENT_NOT_AVAILABLE")]), PackageComponentNotAvailable)
    assert isinstance(error_for_violations([_violation("RECIPE_THREAD_NOT_AUTHORIZED")]), RecipeThreadNotAuthorized)


def test_mixed_or_other_violations_use_the_generic_draft_invalid_error() -> None:
    mixed = error_for_violations([_violation("PRICING_BELOW_FLOOR"), _violation("PACKAGE_ALLOCATION_MISMATCH")])
    assert type(mixed) is PricingDraftInvalid and mixed.code == "PRICING_DRAFT_INVALID" and mixed.status_code == 422
    assert [item["code"] for item in mixed.details["violations"]] == ["PRICING_BELOW_FLOOR", "PACKAGE_ALLOCATION_MISMATCH"]
    assert type(error_for_violations([_violation("RATE_THREAD_UNKNOWN")])) is PricingDraftInvalid
