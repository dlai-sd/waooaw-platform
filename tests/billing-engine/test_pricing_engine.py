# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Pricing engine state machine, authorization rules, change-size guard and safety operations (WC-136 C5-01)."""

from __future__ import annotations

import sys
from datetime import timedelta
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import DBAPIError

sys.path.insert(0, str(Path(__file__).parent))

from pricing_support import (  # noqa: E402
    AGENT_TYPE,
    AGENT_VERSION,
    PACKAGE_SUBJECT,
    POLICY_SUBJECT,
    PROACTIVE_THREAD,
    START,
    FakeReference,
    budget_body,
    dma_declarations,
    dma_package_body,
    dma_rates,
    grant_body,
    make_harness,
    policy_body,
    rate_body,
)

from markup.package_engine import ThreadRate  # noqa: E402
from pricing.engine import LEGAL_TRANSITIONS, PricingEngine  # noqa: E402
from pricing.models import (  # noqa: E402
    ActorContext,
    EffectiveRole,
    PackageComponentNotAvailable,
    PricingBelowFloor,
    PricingCeilingAboveMaximum,
    PricingDraftInvalid,
    PricingForbidden,
    PricingIllegalTransition,
    PricingKind,
    PricingNeedsSecondConfirmation,
    PricingStepUpRequired,
    PricingUnavailable,
    PricingVersionNotFound,
    VersionState,
    body_digest,
)
from pricing.repository import SqlPricingRepository, translate_database_error  # noqa: E402
from pricing.service import (  # noqa: E402
    ACTION_ACTIVATE_FOR_SALE,
    ACTION_AUTHORIZE,
    SYSTEM_ACTOR,
    CeEvidenceRecorder,
    PricingService,
    requires_second_confirmation,
)

ADMIN = ActorContext("admin-1", EffectiveRole.PRICING_ADMIN)
FOUNDER = ActorContext("founder-1", EffectiveRole.FOUNDER, step_up=True)
FOUNDER_NO_STEP_UP = ActorContext("founder-1", EffectiveRole.FOUNDER)
BUDGET_SUBJECT = "budget:ENVIRONMENT_CEILING|demo"
GRANT_SUBJECT = f"grant:TRIAL|{AGENT_TYPE}|{AGENT_VERSION}"
RATE_SUBJECT = "thread:llm_pro"


def _codes(violations):
    return [item.code for item in violations]


def _states(harness, version_id):
    return [(event.from_state, event.to_state) for event in harness.repository.events if event.version_id == version_id]


async def _draft(harness, body=None, *, kind=PricingKind.PACKAGE, deploy_maximum_paise=None):
    result = await harness.service.create_draft(
        ADMIN, kind, body if body is not None else dma_package_body(), deploy_maximum_paise=deploy_maximum_paise
    )
    return result.version.version_id


async def _simulated(harness, body=None, *, kind=PricingKind.PACKAGE, deploy_maximum_paise=None):
    version_id = await _draft(harness, body, kind=kind, deploy_maximum_paise=deploy_maximum_paise)
    await harness.service.simulate(ADMIN, version_id, deploy_maximum_paise=deploy_maximum_paise)
    return version_id


async def _submitted(harness, body=None, *, kind=PricingKind.PACKAGE, deploy_maximum_paise=None, second=False):
    version_id = await _simulated(harness, body, kind=kind, deploy_maximum_paise=deploy_maximum_paise)
    await harness.service.submit(
        ADMIN, version_id, second_confirmation=second, deploy_maximum_paise=deploy_maximum_paise
    )
    return version_id


async def _effective_package(harness, body=None):
    version_id = await _submitted(harness, body)
    await harness.service.authorize(FOUNDER, version_id)
    return version_id


# ---------------------------------------------------------------- state machine

_EXPECTED_TRANSITIONS = {
    VersionState.DRAFT: {VersionState.SIMULATED, VersionState.DISCARDED},
    VersionState.SIMULATED: {VersionState.SUBMITTED, VersionState.DRAFT, VersionState.DISCARDED},
    VersionState.SUBMITTED: {VersionState.AUTHORIZED, VersionState.DRAFT, VersionState.DISCARDED},
    VersionState.AUTHORIZED: {VersionState.EFFECTIVE},
    VersionState.EFFECTIVE: {VersionState.SUPERSEDED},
    VersionState.SUPERSEDED: set(),
    VersionState.DISCARDED: set(),
}


@pytest.mark.parametrize(("current", "target"), list(product(VersionState, VersionState)))
def test_only_the_appendix_a2_transitions_are_legal(current, target) -> None:
    harness = make_harness()
    version = harness.repository.seed(PricingKind.RATE, RATE_SUBJECT, rate_body(), state=current)
    if target in _EXPECTED_TRANSITIONS[current]:
        PricingEngine.assert_transition(version, target)
    else:
        with pytest.raises(PricingIllegalTransition) as raised:
            PricingEngine.assert_transition(version, target)
        assert raised.value.code == "PRICING_ILLEGAL_TRANSITION"
        assert raised.value.status_code == 409


def test_the_transition_table_matches_the_independent_expectation() -> None:
    assert {state: set(targets) for state, targets in LEGAL_TRANSITIONS.items()} == _EXPECTED_TRANSITIONS


async def test_package_lifecycle_projects_the_profile_and_opens_for_sale_only_on_activation() -> None:
    harness = make_harness()
    created = await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body())
    version_id = created.version.version_id
    assert created.violations == []
    assert created.warnings == []
    assert created.version.state is VersionState.DRAFT
    assert created.version.version_no == 1
    assert created.version.subject_key == PACKAGE_SUBJECT

    simulation = await harness.service.simulate(ADMIN, version_id)
    assert simulation.version.state is VersionState.SIMULATED
    assert simulation.report.projection.cost_floor_paise == 19778

    submitted = await harness.service.submit(ADMIN, version_id)
    assert submitted.state is VersionState.SUBMITTED
    assert submitted.second_confirmed_by is None

    effective = await harness.service.authorize(FOUNDER, version_id)
    assert effective.state is VersionState.EFFECTIVE
    assert effective.authorized_by == "founder-1"
    assert effective.authorized_at == START
    assert effective.effective_from == START
    assert effective.evidence_id is not None
    assert harness.evidence.calls == [
        {"action": ACTION_AUTHORIZE, "actor": "founder-1", "subject": PACKAGE_SUBJECT}
    ]
    assert _states(harness, version_id) == [
        (None, VersionState.DRAFT),
        (VersionState.DRAFT, VersionState.SIMULATED),
        (VersionState.SIMULATED, VersionState.SUBMITTED),
        (VersionState.SUBMITTED, VersionState.AUTHORIZED),
        (VersionState.AUTHORIZED, VersionState.EFFECTIVE),
    ]
    profile = harness.repository.profiles[version_id]
    assert set(profile["threadRations"]) == {"llm_pro", "whatsapp_window", "llm_mid_gemini", PROACTIVE_THREAD}
    assert profile["costFloorPaise"] == 19778
    assert profile["minimumMarginPct"] == 55
    assert version_id not in harness.repository.sale_state

    opened = await harness.service.activate_for_sale(FOUNDER, version_id)
    assert opened.version_id == version_id
    assert harness.repository.sale_state[version_id] is True
    call = harness.repository.sale_calls[-1]
    assert call["direction"] == "NORMAL"
    assert call["reason"].startswith("ACTIVATE_FOR_SALE evidence=")
    assert harness.evidence.calls[-1]["action"] == ACTION_ACTIVATE_FOR_SALE


async def test_simulating_twice_adds_no_second_event_and_never_hides_rule_violations() -> None:
    rates = dma_rates(proactive_authorized=True, proactive_cost=5)
    rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    harness = make_harness(reference=FakeReference(rates))
    created = await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body())
    version_id = created.version.version_id
    assert _codes(created.violations) == ["PRICING_BELOW_FLOOR"]
    first = await harness.service.simulate(ADMIN, version_id)
    second = await harness.service.simulate(ADMIN, version_id)
    assert _codes(first.report.violations) == ["PRICING_BELOW_FLOOR"]
    assert second.version.state is VersionState.SIMULATED
    assert len(_states(harness, version_id)) == 2
    with pytest.raises(PricingBelowFloor) as raised:
        await harness.service.submit(ADMIN, version_id)
    assert raised.value.code == "PRICING_BELOW_FLOOR"
    assert raised.value.minimum_compliant_price_paise > 200000
    assert (await harness.service.get_version(version_id)).state is VersionState.SIMULATED


async def test_editing_returns_the_version_to_draft_and_drops_the_simulation() -> None:
    harness = make_harness()
    version_id = await _simulated(harness)
    before = await harness.service.get_version(version_id)
    edited = await harness.service.update_draft(ADMIN, version_id, dma_package_body(price=210000))
    assert edited.version.state is VersionState.DRAFT
    assert edited.version.body["priceInclGstPaise"] == 210000
    assert edited.version.body_digest == body_digest(edited.version.body)
    assert edited.version.body_digest != before.body_digest
    with pytest.raises(PricingIllegalTransition):
        await harness.service.submit(ADMIN, version_id)


async def test_the_subject_of_a_draft_cannot_change() -> None:
    harness = make_harness()
    version_id = await _draft(harness)
    with pytest.raises(PricingDraftInvalid) as raised:
        await harness.service.update_draft(ADMIN, version_id, dma_package_body(package_code="GROWTH"))
    assert _codes(raised.value.violations) == ["PRICING_SUBJECT_IMMUTABLE"]
    assert (await harness.service.get_version(version_id)).subject_key == PACKAGE_SUBJECT


async def test_withdrawing_a_submitted_version_returns_it_to_draft() -> None:
    harness = make_harness()
    version_id = await _submitted(harness)
    withdrawn = await harness.service.withdraw(ADMIN, version_id, "wrong price")
    assert withdrawn.state is VersionState.DRAFT
    assert withdrawn.second_confirmed_by is None
    again = await harness.service.simulate(ADMIN, version_id)
    assert again.version.state is VersionState.SIMULATED
    assert _states(harness, version_id)[-2:] == [
        (VersionState.SUBMITTED, VersionState.DRAFT),
        (VersionState.DRAFT, VersionState.SIMULATED),
    ]
    assert harness.repository.events[-2].reason == "wrong price"


@pytest.mark.parametrize("stop_at", ["DRAFT", "SIMULATED", "SUBMITTED"])
async def test_a_version_can_be_discarded_until_it_is_authorized(stop_at: str) -> None:
    harness = make_harness()
    if stop_at == "DRAFT":
        version_id = await _draft(harness)
    elif stop_at == "SIMULATED":
        version_id = await _simulated(harness)
    else:
        version_id = await _submitted(harness)
    discarded = await harness.service.discard(ADMIN, version_id, "not needed")
    assert discarded.state is VersionState.DISCARDED
    assert harness.repository.events[-1].reason == "not needed"
    with pytest.raises(PricingIllegalTransition):
        await harness.service.simulate(ADMIN, version_id)


async def test_effective_and_authorized_versions_cannot_be_discarded_or_edited() -> None:
    harness = make_harness()
    effective_id = await _effective_package(harness)
    authorized = harness.repository.seed(
        PricingKind.BUDGET, BUDGET_SUBJECT, budget_body(), state=VersionState.AUTHORIZED
    )
    digest = (await harness.service.get_version(effective_id)).body_digest
    for version_id in (effective_id, authorized.version_id):
        with pytest.raises(PricingIllegalTransition):
            await harness.service.discard(ADMIN, version_id)
    with pytest.raises(PricingIllegalTransition):
        await harness.service.update_draft(ADMIN, effective_id, dma_package_body(price=210000))
    assert (await harness.service.get_version(effective_id)).body_digest == digest
    assert (await harness.service.get_version(effective_id)).state is VersionState.EFFECTIVE


async def test_out_of_order_calls_are_refused_and_roll_back() -> None:
    harness = make_harness()
    draft_id = await _draft(harness)
    with pytest.raises(PricingIllegalTransition):
        await harness.service.submit(ADMIN, draft_id)
    with pytest.raises(PricingIllegalTransition):
        await harness.service.withdraw(ADMIN, draft_id)
    simulated_id = await _simulated(harness, dma_package_body(package_code="GROWTH"))
    with pytest.raises(PricingIllegalTransition):
        await harness.service.authorize(FOUNDER, simulated_id)
    submitted_id = await _submitted(harness, dma_package_body(package_code="PRO"))
    with pytest.raises(PricingIllegalTransition):
        await harness.service.simulate(ADMIN, submitted_id)
    with pytest.raises(PricingIllegalTransition):
        await harness.service.update_draft(ADMIN, submitted_id, dma_package_body(package_code="PRO", price=210000))
    assert harness.evidence.calls == []
    assert harness.repository.rollbacks == 5
    assert (await harness.service.get_version(submitted_id)).state is VersionState.SUBMITTED


async def test_a_body_that_does_not_fit_its_kind_stores_nothing() -> None:
    harness = make_harness()
    with pytest.raises(PricingDraftInvalid):
        await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, {"agentType": AGENT_TYPE})
    assert [v.kind for v in harness.repository.versions.values()] == [PricingKind.POLICY]
    assert harness.repository.rollbacks == 1


# ---------------------------------------------------------------- authorization

async def test_only_a_founder_with_step_up_authorizes_and_no_evidence_is_recorded_otherwise() -> None:
    harness = make_harness()
    version_id = await _submitted(harness)
    with pytest.raises(PricingForbidden) as forbidden:
        await harness.service.authorize(ADMIN, version_id)
    assert forbidden.value.code == "PRICING_FORBIDDEN"
    with pytest.raises(PricingStepUpRequired) as step_up:
        await harness.service.authorize(FOUNDER_NO_STEP_UP, version_id)
    assert step_up.value.code == "PRICING_STEP_UP_REQUIRED"
    assert step_up.value.status_code == 403
    assert harness.evidence.calls == []
    assert (await harness.service.get_version(version_id)).state is VersionState.SUBMITTED
    with pytest.raises(PricingForbidden):
        await harness.service.activate_for_sale(ADMIN, version_id)
    with pytest.raises(PricingStepUpRequired):
        await harness.service.activate_for_sale(FOUNDER_NO_STEP_UP, version_id)


async def test_ce_unavailability_fails_the_authorization_closed() -> None:
    harness = make_harness(evidence_fails=True)
    version_id = await _submitted(harness)
    with pytest.raises(PricingUnavailable) as raised:
        await harness.service.authorize(FOUNDER, version_id)
    assert raised.value.status_code == 503
    assert (await harness.service.get_version(version_id)).state is VersionState.SUBMITTED
    assert version_id not in harness.repository.profiles
    assert harness.repository.rollbacks >= 1


async def test_authorization_validates_again_at_current_rates() -> None:
    harness = make_harness()
    version_id = await _submitted(harness)
    harness.reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    with pytest.raises(PricingBelowFloor) as raised:
        await harness.service.authorize(FOUNDER, version_id)
    assert raised.value.minimum_compliant_price_paise > 200000
    assert harness.evidence.calls == []
    assert (await harness.service.get_version(version_id)).state is VersionState.SUBMITTED


async def test_a_failing_projection_rolls_the_whole_authorization_back() -> None:
    harness = make_harness()
    version_id = await _submitted(harness)

    async def refuse(**_kwargs):
        raise PricingUnavailable("store down")

    harness.repository.project_package_profile = refuse
    with pytest.raises(PricingUnavailable):
        await harness.service.authorize(FOUNDER, version_id)
    assert (await harness.service.get_version(version_id)).state is VersionState.SUBMITTED
    assert _states(harness, version_id)[-1] == (VersionState.SIMULATED, VersionState.SUBMITTED)


async def test_a_package_is_not_opened_for_sale_while_a_component_is_not_available() -> None:
    harness = make_harness(declaration_availability="DEFAULT_OFF")
    version_id = await _simulated(harness)
    simulation = await harness.service.simulate(ADMIN, version_id)
    assert _codes(simulation.report.warnings).count("PACKAGE_COMPONENT_NOT_AVAILABLE") == 4
    await harness.service.submit(ADMIN, version_id)
    await harness.service.authorize(FOUNDER, version_id)
    with pytest.raises(PackageComponentNotAvailable) as raised:
        await harness.service.activate_for_sale(FOUNDER, version_id)
    assert raised.value.code == "PACKAGE_COMPONENT_NOT_AVAILABLE"
    assert len(raised.value.violations) == 4
    assert version_id not in harness.repository.sale_state
    assert [call["action"] for call in harness.evidence.calls] == [ACTION_AUTHORIZE]


async def test_only_an_effective_package_can_be_opened_for_sale() -> None:
    harness = make_harness()
    version_id = await _submitted(harness)
    with pytest.raises(PricingIllegalTransition):
        await harness.service.activate_for_sale(FOUNDER, version_id)
    rate = harness.repository.seed(PricingKind.RATE, RATE_SUBJECT, rate_body())
    with pytest.raises(PricingIllegalTransition):
        await harness.service.activate_for_sale(FOUNDER, rate.version_id)


# ---------------------------------------------------------------- effective dating

async def test_a_future_effective_from_waits_and_the_scheduler_activates_it_and_supersedes_the_old_version() -> None:
    harness = make_harness()
    previous = harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    version_id = await _submitted(harness, dma_package_body(price=210000))
    due = START + timedelta(days=2)
    authorized = await harness.service.authorize(FOUNDER, version_id, effective_from=due)
    assert authorized.state is VersionState.AUTHORIZED
    assert authorized.effective_from == due
    assert version_id in harness.repository.profiles
    assert (await harness.service.effective_version(PricingKind.PACKAGE, PACKAGE_SUBJECT)).version_id == previous.version_id
    assert await harness.service.activate_due() == []

    harness.clock.advance(days=2)
    activated = await harness.service.activate_due()
    assert [v.version_id for v in activated] == [version_id]
    assert activated[0].state is VersionState.EFFECTIVE
    assert activated[0].supersedes == previous.version_id
    assert (await harness.service.get_version(previous.version_id)).state is VersionState.SUPERSEDED
    assert (await harness.service.effective_version(PricingKind.PACKAGE, PACKAGE_SUBJECT)).version_id == version_id
    assert [v.version_id for v in await harness.service.effective_versions(PricingKind.PACKAGE)] == [version_id]
    activation = [event for event in harness.repository.events if event.version_id == version_id][-1]
    assert (activation.from_state, activation.to_state, activation.actor) == (
        VersionState.AUTHORIZED,
        VersionState.EFFECTIVE,
        SYSTEM_ACTOR,
    )


@pytest.mark.parametrize("offset", [timedelta(hours=-1), None])
async def test_effective_from_must_be_a_utc_instant_that_is_not_in_the_past(offset) -> None:
    harness = make_harness()
    version_id = await _submitted(harness)
    moment = START.replace(tzinfo=None) + timedelta(days=1) if offset is None else START + offset
    with pytest.raises(PricingDraftInvalid) as raised:
        await harness.service.authorize(FOUNDER, version_id, effective_from=moment)
    assert _codes(raised.value.violations) == ["PRICING_EFFECTIVE_FROM_INVALID"]
    assert harness.evidence.calls == []


# ---------------------------------------------------------------- change-size guard

async def test_a_change_beyond_the_guard_needs_a_second_confirmation_that_is_recorded() -> None:
    harness = make_harness()
    previous = harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    created = await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body(price=280000))
    version_id = created.version.version_id
    assert created.version.needs_second_confirmation is True
    assert _codes(created.warnings) == ["NEEDS_SECOND_CONFIRMATION"]
    simulation = await harness.service.simulate(ADMIN, version_id)
    assert simulation.report.needs_second_confirmation is True
    assert _codes(simulation.report.warnings)[0] == "NEEDS_SECOND_CONFIRMATION"
    with pytest.raises(PricingNeedsSecondConfirmation) as raised:
        await harness.service.submit(ADMIN, version_id)
    assert raised.value.code == "PRICING_NEEDS_SECOND_CONFIRMATION"
    assert raised.value.status_code == 409
    submitted = await harness.service.submit(ADMIN, version_id, second_confirmation=True)
    assert submitted.second_confirmed_by == "admin-1"
    effective = await harness.service.authorize(FOUNDER, version_id)
    assert effective.supersedes == previous.version_id


async def test_a_change_inside_the_guard_needs_no_second_confirmation() -> None:
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    created = await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body(price=260000))
    assert created.version.needs_second_confirmation is False
    assert created.warnings == []


async def test_a_guard_tightened_after_simulation_is_recomputed_at_submit() -> None:
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    version_id = await _simulated(harness, dma_package_body(price=240000))
    assert (await harness.service.get_version(version_id)).needs_second_confirmation is False
    harness.repository.seed(
        PricingKind.POLICY,
        POLICY_SUBJECT,
        policy_body(changeSizeGuardPercent=10),
        effective_from=START - timedelta(hours=1),
    )
    with pytest.raises(PricingNeedsSecondConfirmation):
        await harness.service.submit(ADMIN, version_id)
    with pytest.raises(PricingNeedsSecondConfirmation):
        await harness.service.submit(ADMIN, version_id, second_confirmation=True)
    resimulated = await harness.service.simulate(ADMIN, version_id)
    assert resimulated.version.needs_second_confirmation is True
    assert resimulated.version.state is VersionState.SIMULATED
    submitted = await harness.service.submit(ADMIN, version_id, second_confirmation=True)
    assert submitted.second_confirmed_by == "admin-1"


async def test_without_a_policy_the_guard_fails_closed() -> None:
    harness = make_harness(with_policy=False)
    created = await harness.service.create_draft(ADMIN, PricingKind.RATE, rate_body())
    assert created.version.needs_second_confirmation is True


def test_the_rate_guard_compares_marked_up_costs() -> None:
    policy = policy_body()
    base = rate_body(raw=300)
    kwargs = {"effective_body": base, "policy_body": policy, "cost_floor_paise": None}
    assert requires_second_confirmation(PricingKind.RATE, rate_body(raw=400), **kwargs) is True
    assert requires_second_confirmation(PricingKind.RATE, rate_body(raw=350), **kwargs) is False
    kwargs["effective_body"] = None
    assert requires_second_confirmation(PricingKind.RATE, rate_body(raw=400), **kwargs) is False


def test_the_budget_guard_is_exclusive_at_the_boundary_and_flags_any_change_from_zero() -> None:
    kwargs = {"policy_body": policy_body(), "cost_floor_paise": None}
    old = budget_body(50000)
    assert requires_second_confirmation(PricingKind.BUDGET, budget_body(65000), effective_body=old, **kwargs) is False
    assert requires_second_confirmation(PricingKind.BUDGET, budget_body(65001), effective_body=old, **kwargs) is True
    assert requires_second_confirmation(PricingKind.BUDGET, budget_body(35000), effective_body=old, **kwargs) is False
    assert requires_second_confirmation(PricingKind.BUDGET, budget_body(34999), effective_body=old, **kwargs) is True
    assert requires_second_confirmation(PricingKind.BUDGET, budget_body(1), effective_body=budget_body(0), **kwargs) is True
    assert requires_second_confirmation(PricingKind.BUDGET, budget_body(0), effective_body=budget_body(0), **kwargs) is False


def test_the_package_guard_flags_a_price_above_the_multiple_of_the_cost_floor() -> None:
    policy = policy_body()
    floor = 19778
    at_limit = {"priceInclGstPaise": 20 * floor}
    above = {"priceInclGstPaise": 20 * floor + 1}
    assert requires_second_confirmation(PricingKind.PACKAGE, at_limit, effective_body=None, policy_body=policy, cost_floor_paise=floor) is False
    assert requires_second_confirmation(PricingKind.PACKAGE, above, effective_body=None, policy_body=policy, cost_floor_paise=floor) is True
    assert requires_second_confirmation(PricingKind.PACKAGE, above, effective_body=None, policy_body=policy, cost_floor_paise=None) is False


@pytest.mark.parametrize("kind", [PricingKind.POLICY, PricingKind.GRANT, PricingKind.COUPON])
def test_only_rates_packages_and_budgets_are_guarded(kind) -> None:
    assert requires_second_confirmation(kind, {}, effective_body=None, policy_body=None, cost_floor_paise=None) is False


@pytest.mark.parametrize("kind", [PricingKind.RATE, PricingKind.PACKAGE, PricingKind.BUDGET])
def test_a_guarded_kind_without_a_readable_policy_needs_confirmation(kind) -> None:
    assert requires_second_confirmation(kind, {}, effective_body=None, policy_body=None, cost_floor_paise=None) is True
    unreadable = {"changeSizeGuardPercent": "30", "priceMultipleGuard": 20}
    assert requires_second_confirmation(kind, {}, effective_body=None, policy_body=unreadable, cost_floor_paise=None) is True


# ---------------------------------------------------------------- ceilings and the minimum margin

async def test_an_environment_ceiling_above_the_deploy_maximum_cannot_be_submitted_or_authorized() -> None:
    harness = make_harness()
    created = await harness.service.create_draft(
        ADMIN, PricingKind.BUDGET, budget_body(60000), deploy_maximum_paise=50000
    )
    assert _codes(created.violations) == ["PRICING_CEILING_ABOVE_MAXIMUM"]
    version_id = created.version.version_id
    await harness.service.simulate(ADMIN, version_id, deploy_maximum_paise=50000)
    with pytest.raises(PricingCeilingAboveMaximum) as raised:
        await harness.service.submit(ADMIN, version_id, deploy_maximum_paise=50000)
    assert raised.value.code == "PRICING_CEILING_ABOVE_MAXIMUM"
    assert raised.value.violations[0].details["deployMaximumPaise"] == 50000


async def test_an_environment_ceiling_is_authorized_only_against_a_supplied_deploy_maximum() -> None:
    harness = make_harness()
    version_id = await _submitted(harness, budget_body(50000), kind=PricingKind.BUDGET, deploy_maximum_paise=50000)
    with pytest.raises(PricingDraftInvalid) as raised:
        await harness.service.authorize(FOUNDER, version_id)
    assert _codes(raised.value.violations) == ["BUDGET_DEPLOY_MAXIMUM_REQUIRED"]
    effective = await harness.service.authorize(FOUNDER, version_id, deploy_maximum_paise=50000)
    assert effective.state is VersionState.EFFECTIVE
    assert effective.subject_key == BUDGET_SUBJECT


async def test_only_the_founder_changes_the_minimum_margin() -> None:
    harness = make_harness()
    with pytest.raises(PricingForbidden):
        await harness.service.create_draft(ADMIN, PricingKind.POLICY, policy_body(minimumMarginPct=40))
    allowed = await harness.service.create_draft(ADMIN, PricingKind.POLICY, policy_body(paymentGraceDays=10))
    assert allowed.version.body["minimumMarginPct"] == 55
    with pytest.raises(PricingForbidden):
        await harness.service.update_draft(ADMIN, allowed.version.version_id, policy_body(minimumMarginPct=45))

    founder_draft = await harness.service.create_draft(FOUNDER, PricingKind.POLICY, policy_body(minimumMarginPct=40))
    version_id = founder_draft.version.version_id
    await harness.service.simulate(FOUNDER, version_id)
    with pytest.raises(PricingForbidden):
        await harness.service.submit(ADMIN, version_id)
    submitted = await harness.service.submit(FOUNDER, version_id)
    assert submitted.state is VersionState.SUBMITTED


async def test_the_first_policy_can_only_be_created_by_the_founder() -> None:
    harness = make_harness(with_policy=False)
    with pytest.raises(PricingForbidden):
        await harness.service.create_draft(ADMIN, PricingKind.POLICY, policy_body())
    created = await harness.service.create_draft(FOUNDER, PricingKind.POLICY, policy_body())
    assert created.version.subject_key == POLICY_SUBJECT


# ---------------------------------------------------------------- rates

async def test_an_effective_rate_calls_the_hook_and_reports_the_live_margin() -> None:
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    reports = []
    service = PricingService(
        repository=harness.repository,
        reference=harness.reference,
        declarations=dma_declarations(),
        evidence=harness.evidence,
        clock=harness.clock,
        on_rate_effective=None,
        breach_reporter=SimpleNamespace(report=reports.append),
    )
    harness.reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    version_id = (await service.create_draft(ADMIN, PricingKind.RATE, rate_body())).version.version_id
    await service.simulate(ADMIN, version_id)
    await service.submit(ADMIN, version_id)
    effective = await service.authorize(FOUNDER, version_id)
    assert effective.state is VersionState.EFFECTIVE
    assert effective.subject_key == RATE_SUBJECT
    assert len(reports) == 1
    assert [breach.reason for breach in reports[0]] == ["BELOW_COST_FLOOR"]


async def test_the_rate_hook_receives_the_effective_version_and_its_failure_is_swallowed() -> None:
    harness = make_harness()
    version_id = (await harness.service.create_draft(ADMIN, PricingKind.RATE, rate_body())).version.version_id
    await harness.service.simulate(ADMIN, version_id)
    await harness.service.submit(ADMIN, version_id)
    effective = await harness.service.authorize(FOUNDER, version_id)
    assert [call.version_id for call in harness.rate_hook_calls] == [effective.version_id]

    async def broken(_version) -> None:
        raise RuntimeError("cache down")

    failing = PricingService(
        repository=harness.repository,
        reference=harness.reference,
        declarations=dma_declarations(),
        evidence=harness.evidence,
        clock=harness.clock,
        on_rate_effective=broken,
    )
    second = (await failing.create_draft(ADMIN, PricingKind.RATE, rate_body(raw=310))).version.version_id
    await failing.simulate(ADMIN, second)
    await failing.submit(ADMIN, second)
    assert (await failing.authorize(FOUNDER, second)).state is VersionState.EFFECTIVE


# ---------------------------------------------------------------- safety operations

async def test_lowering_a_ceiling_takes_effect_at_once_without_ce_and_notifies_the_founder() -> None:
    harness = make_harness()
    previous = harness.repository.seed(PricingKind.BUDGET, BUDGET_SUBJECT, budget_body(50000))
    lowered = await harness.service.lower_ceiling(ADMIN, BUDGET_SUBJECT, 20000, "spend spike")
    assert lowered.state is VersionState.EFFECTIVE
    assert lowered.version_no == 2
    assert lowered.body["maximumPaise"] == 20000
    assert lowered.supersedes == previous.version_id
    assert (await harness.service.get_version(previous.version_id)).state is VersionState.SUPERSEDED
    assert harness.evidence.calls == []
    events = harness.repository.events
    assert [event.direction for event in events[-2:]] == ["SAFETY", "SAFETY"]
    assert events[-1].reason == "LOWER_CEILING: spend spike"
    note = harness.notifier.sent[0]
    assert (note.operation, note.kind, note.subject_key, note.actor_role, note.reason) == (
        "LOWER_CEILING",
        PricingKind.BUDGET,
        BUDGET_SUBJECT,
        "PRICING_ADMIN",
        "spend spike",
    )


@pytest.mark.parametrize("requested", [50000, 60000, -1])
async def test_a_safety_change_can_only_lower_the_ceiling(requested: int) -> None:
    harness = make_harness()
    harness.repository.seed(PricingKind.BUDGET, BUDGET_SUBJECT, budget_body(50000))
    with pytest.raises(PricingDraftInvalid) as raised:
        await harness.service.lower_ceiling(ADMIN, BUDGET_SUBJECT, requested, "x")
    assert _codes(raised.value.violations) == ["SAFETY_NOT_A_REDUCTION"]
    assert harness.notifier.sent == []
    assert len(harness.repository.versions) == 2


async def test_lowering_a_ceiling_that_does_not_exist_is_not_found() -> None:
    harness = make_harness()
    with pytest.raises(PricingVersionNotFound) as raised:
        await harness.service.lower_ceiling(ADMIN, BUDGET_SUBJECT, 1, "x")
    assert raised.value.status_code == 404


async def test_an_authorized_ceiling_that_is_due_becomes_effective_before_it_is_lowered() -> None:
    harness = make_harness()
    authorized = harness.repository.seed(
        PricingKind.BUDGET, BUDGET_SUBJECT, budget_body(50000), state=VersionState.AUTHORIZED
    )
    lowered = await harness.service.lower_ceiling(FOUNDER_NO_STEP_UP, BUDGET_SUBJECT, 10000, "tighten")
    assert lowered.supersedes == authorized.version_id
    assert _states(harness, authorized.version_id) == [
        (VersionState.AUTHORIZED, VersionState.EFFECTIVE),
        (VersionState.EFFECTIVE, VersionState.SUPERSEDED),
    ]
    activation = [event for event in harness.repository.events if event.version_id == authorized.version_id][0]
    assert activation.actor == SYSTEM_ACTOR


async def test_disabling_a_grant_is_immediate_and_idempotent() -> None:
    harness = make_harness()
    previous = harness.repository.seed(PricingKind.GRANT, GRANT_SUBJECT, grant_body())
    disabled = await harness.service.disable_grant(ADMIN, GRANT_SUBJECT, "abuse")
    assert disabled.body["disabled"] is True
    assert disabled.supersedes == previous.version_id
    assert harness.repository.events[-1].reason == "DISABLE_GRANT: abuse"
    assert harness.repository.events[-1].direction == "SAFETY"
    again = await harness.service.disable_grant(ADMIN, GRANT_SUBJECT, "abuse")
    assert again.version_id == disabled.version_id
    assert len(await harness.service.list_versions(subject_key=GRANT_SUBJECT)) == 2
    assert harness.evidence.calls == []


async def test_closing_a_package_stops_new_sales_without_changing_the_price_and_reports_a_blank_reason() -> None:
    harness = make_harness()
    version_id = await _effective_package(harness)
    await harness.service.activate_for_sale(FOUNDER, version_id)
    closed = await harness.service.close_package(ADMIN, version_id, "   ")
    assert closed.state is VersionState.EFFECTIVE
    assert harness.repository.sale_state[version_id] is False
    call = harness.repository.sale_calls[-1]
    assert (call["forSale"], call["direction"], call["reason"]) == (False, "SAFETY", "CLOSE_PACKAGE: no reason given")
    assert harness.notifier.sent[-1].operation == "CLOSE_PACKAGE"
    assert [item["action"] for item in harness.evidence.calls] == [ACTION_AUTHORIZE, ACTION_ACTIVATE_FOR_SALE]


async def test_a_package_that_is_not_effective_cannot_be_closed() -> None:
    harness = make_harness()
    version_id = await _draft(harness)
    with pytest.raises(PricingIllegalTransition):
        await harness.service.close_package(ADMIN, version_id, "x")
    assert harness.repository.sale_calls == []


async def test_a_failing_founder_notification_never_undoes_a_safety_change() -> None:
    harness = make_harness()
    harness.repository.seed(PricingKind.BUDGET, BUDGET_SUBJECT, budget_body(50000))
    harness.notifier.fail = True
    lowered = await harness.service.lower_ceiling(ADMIN, BUDGET_SUBJECT, 100, "urgent")
    assert lowered.body["maximumPaise"] == 100
    assert (await harness.service.effective_version(PricingKind.BUDGET, BUDGET_SUBJECT)).version_id == lowered.version_id


# ---------------------------------------------------------------- reads

async def test_reads_filter_page_and_report_missing_versions() -> None:
    harness = make_harness()
    for code in ("STARTER", "GROWTH", "PRO"):
        await _draft(harness, dma_package_body(package_code=code))
    assert len(await harness.service.list_versions(kind=PricingKind.PACKAGE)) == 3
    assert len(await harness.service.list_versions(kind=PricingKind.PACKAGE, limit=2)) == 2
    assert len(await harness.service.list_versions(kind=PricingKind.PACKAGE, limit=2, offset=2)) == 1
    assert len(await harness.service.list_versions(kind=PricingKind.POLICY)) == 1
    assert await harness.service.list_versions(state=VersionState.SUBMITTED) == []
    missing = uuid4()
    with pytest.raises(PricingVersionNotFound):
        await harness.service.get_version(missing)
    with pytest.raises(PricingVersionNotFound):
        await harness.service.list_events(missing)
    with pytest.raises(PricingVersionNotFound):
        await harness.service.discard(ADMIN, missing)


async def test_events_are_listed_in_order_for_one_version() -> None:
    harness = make_harness()
    version_id = await _simulated(harness)
    events = await harness.service.list_events(version_id)
    assert [(event.from_state, event.to_state) for event in events] == [
        (None, VersionState.DRAFT),
        (VersionState.DRAFT, VersionState.SIMULATED),
    ]


async def test_the_live_margin_lists_packages_in_breach_and_clears_after_repricing() -> None:
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    assert await harness.service.live_margin() == []
    harness.reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    breaches = await harness.service.live_margin()
    assert [breach.reason for breach in breaches] == ["BELOW_COST_FLOOR"]
    harness.reference.rates["llm_pro"] = ThreadRate("llm_pro", 400, True)
    assert await harness.service.live_margin() == []


# ---------------------------------------------------------------- evidence and persistence adapters

async def test_ce_evidence_returns_a_fresh_id_when_the_validator_allows_the_action() -> None:
    fixed = uuid4()
    validate = AsyncMock()
    recorder = CeEvidenceRecorder(validate, new_id=lambda: fixed)
    evidence_id = await recorder.record(action=ACTION_AUTHORIZE, actor_id="founder-1", subject_key="x")
    assert evidence_id == fixed
    validate.assert_awaited_once_with(ACTION_AUTHORIZE)


async def test_ce_evidence_fails_closed_when_the_validator_raises() -> None:
    recorder = CeEvidenceRecorder(AsyncMock(side_effect=RuntimeError("denied")))
    with pytest.raises(PricingUnavailable) as raised:
        await recorder.record(action=ACTION_AUTHORIZE, actor_id="founder-1", subject_key="x")
    assert isinstance(raised.value.__cause__, RuntimeError)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("PRICING_VERSION_NOT_FOUND: missing", PricingVersionNotFound),
        ("PRICING_NEEDS_SECOND_CONFIRMATION: confirm", PricingNeedsSecondConfirmation),
        ("PRICING_DRAFT_INVALID: bad", PricingDraftInvalid),
        ("PRICING_ILLEGAL_TRANSITION: EFFECTIVE to DRAFT", PricingIllegalTransition),
        ("institutional.pricing_versions is immutable", PricingIllegalTransition),
        ("pricing_version_events is append-only", PricingIllegalTransition),
        ("connection refused", PricingUnavailable),
    ],
)
def test_database_errors_map_to_the_appendix_b5_errors(message: str, expected: type) -> None:
    error = DBAPIError("SELECT 1", {}, Exception(message))
    assert type(translate_database_error(error)) is expected


def _row(version_id: UUID, state: str = "DRAFT") -> SimpleNamespace:
    return SimpleNamespace(
        version_id=str(version_id),
        kind="PACKAGE",
        subject_key=PACKAGE_SUBJECT,
        version_no=1,
        state=state,
        body=dma_package_body(),
        body_digest="digest",
        seed=False,
        effective_from=None,
        supersedes=None,
        created_by="admin-1",
        created_at=START,
        authorized_by=None,
        authorized_at=None,
        evidence_id=None,
        needs_second_confirmation=False,
        second_confirmed_by=None,
    )


async def test_the_sql_repository_calls_only_the_owner_function_with_bound_parameters() -> None:
    version_id = uuid4()
    result = MagicMock()
    result.fetchone.return_value = _row(version_id)
    session = AsyncMock()
    session.execute.return_value = result
    repository = SqlPricingRepository(session)
    version = await repository.create_draft(
        version_id=version_id,
        kind=PricingKind.PACKAGE,
        subject_key=PACKAGE_SUBJECT,
        body=dma_package_body(),
        digest="digest",
        actor_id="admin-1",
        needs_second_confirmation=False,
        at=START,
    )
    statement, params = session.execute.await_args.args
    assert "institutional.create_pricing_draft" in str(statement)
    assert params["kind"] == "PACKAGE"
    assert params["version_id"] == str(version_id)
    assert version.version_id == version_id
    assert version.state is VersionState.DRAFT
    await repository.commit()
    session.commit.assert_awaited_once()
    await repository.rollback()
    session.rollback.assert_awaited_once()


async def test_the_sql_repository_translates_owner_function_failures() -> None:
    session = AsyncMock()
    session.execute.side_effect = DBAPIError("SELECT 1", {}, Exception("PRICING_VERSION_NOT_FOUND: nope"))
    repository = SqlPricingRepository(session)
    with pytest.raises(PricingVersionNotFound):
        await repository.get(uuid4())


async def test_the_sql_repository_reads_nothing_when_the_row_is_absent() -> None:
    result = MagicMock()
    result.fetchone.return_value = None
    session = AsyncMock()
    session.execute.return_value = result
    assert await SqlPricingRepository(session).get(uuid4()) is None
    assert await SqlPricingRepository(session).effective_at(PricingKind.RATE, RATE_SUBJECT, START) is None
