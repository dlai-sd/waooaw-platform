# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-02
# Constitutional basis: C-059, C-088, C-089, C-091
"""Pricing simulator and live-margin watch (WC-136 C5-02)."""

from __future__ import annotations

import copy
import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from pricing_support import (  # noqa: E402
    PACKAGE_SUBJECT,
    POLICY_SUBJECT,
    START,
    FakeReference,
    InMemoryPricingRepository,
    dma_declarations,
    dma_package_body,
    make_harness,
    policy_body,
    rate_body,
)

from markup.package_engine import ThreadRate, parse_package_body, project_package  # noqa: E402
from pricing.margin_watch import (  # noqa: E402
    LIVE_MARGIN_JOB_ID,
    LIVE_MARGIN_METRIC,
    recompute,
    register_margin_watch_job,
)
from pricing.models import ActorContext, EffectiveRole, PricingKind, VersionState  # noqa: E402
from pricing.simulator import (  # noqa: E402
    BEST_CASE,
    NEEDS_SECOND_CONFIRMATION_WARNING,
    TYPICAL,
    PersonaProfile,
    SimulationContext,
    day_one_release,
    diff_bodies,
    load_persona_profiles,
    parse_persona_profiles,
    simulate_draft,
    worst_case,
)
from pricing.validators import ValidationContext, canonical_body  # noqa: E402

ADMIN = ActorContext("admin-1", EffectiveRole.PRICING_ADMIN)
HEAVY = PersonaProfile(name="HEAVY", usage_percent_by_component={"CONTENT_POST": 100})


def _context(*, availability="AVAILABLE", reference=None, margin=55, **extra) -> SimulationContext:
    validation = ValidationContext(
        reference=reference or FakeReference(),
        declarations=dma_declarations(availability=availability),
        minimum_margin_pct=margin,
        now=START,
    )
    return SimulationContext(validation=validation, **extra)


def _draft(kind=PricingKind.PACKAGE, body=None, subject=PACKAGE_SUBJECT):
    repository = InMemoryPricingRepository()
    return repository.seed(kind, subject, body if body is not None else dma_package_body(), state=VersionState.DRAFT)


def _canonical_package(**kwargs):
    return canonical_body(parse_package_body(dma_package_body(**kwargs)))


# ---------------------------------------------------------------- package simulation

async def test_a_package_is_simulated_under_best_typical_and_persona_usage() -> None:
    report = await simulate_draft(_draft(), _context(personas=[HEAVY]))
    assert report.kind == "PACKAGE"
    assert report.subject_key == PACKAGE_SUBJECT
    assert report.has_effective_version is False
    assert report.violations == []
    assert report.warnings == []
    assert report.changes == []
    assert report.projection.cost_floor_paise == 19778
    assert report.projection.base_price_paise == 169492
    assert [profile.profile for profile in report.profiles] == [BEST_CASE, TYPICAL, "HEAVY"]
    best, typical, heavy = report.profiles
    assert best.component_units == {"PROACTIVE_MESSAGE": 6, "CONTENT_POST": 6, "CHAT_REPLY": 6, "CHANNEL": 2}
    assert best.total_cost_paise == 7938
    assert best.margin_paise == 169492 - 7938
    assert best.margin_pct == pytest.approx(95.32, abs=0.02)
    assert typical.component_units == {"PROACTIVE_MESSAGE": 18, "CONTENT_POST": 18, "CHAT_REPLY": 18, "CHANNEL": 7}
    assert typical.total_cost_paise == 13858
    assert heavy.component_units == {"PROACTIVE_MESSAGE": 0, "CONTENT_POST": 30, "CHAT_REPLY": 0, "CHANNEL": 0}
    assert heavy.variable_cost_paise == 12000
    assert heavy.infrastructure_share_paise == 5000
    assert heavy.total_cost_paise == 17000


async def test_the_worst_case_is_a_day_one_burst_then_termination_on_day_two() -> None:
    report = await simulate_draft(_draft(), _context())
    worst = report.worst_case
    assert worst.profile == "WORST_CASE"
    assert worst.attempted_units == {"PROACTIVE_MESSAGE": 30, "CONTENT_POST": 30, "CHAT_REPLY": 30, "CHANNEL": 12}
    assert worst.day_one_released_units == {"PROACTIVE_MESSAGE": 1, "CONTENT_POST": 1, "CHAT_REPLY": 1, "CHANNEL": 1}
    assert worst.pacing_limited is True
    assert worst.attempted_cost_paise == 19778
    assert worst.day_one_exposure_paise == 5519
    assert worst.refund_paise == 193333
    assert worst.retained_price_paise == 6667
    assert worst.retained_base_paise == 5650
    assert worst.margin_after_refund_paise == 131


def test_an_upfront_component_is_not_limited_by_pacing() -> None:
    body = parse_package_body(
        {**dma_package_body(), "components": [{**dma_package_body()["components"][0], "cadence": "UPFRONT"}]}
    )
    projection = project_package(body, FakeReference().rates, 55)
    worst = worst_case(body, projection)
    assert worst.day_one_released_units == {"PROACTIVE_MESSAGE": 30}
    assert worst.pacing_limited is False


@pytest.mark.parametrize(
    ("quantity", "cadence", "period", "expected"),
    [(30, "UPFRONT", 30, 30), (30, "SPREAD", 30, 1), (31, "SPREAD", 30, 2), (30, "DAILY", 30, 1), (30, "WEEKLY", 30, 8), (12, "WEEKLY", 30, 3), (9, "WEEKLY", 5, 9)],
)
def test_day_one_release_is_bounded_by_the_cadence(quantity: int, cadence: str, period: int, expected: int) -> None:
    assert day_one_release(quantity, cadence, period) == expected


async def test_a_package_edit_reports_field_and_projection_changes_against_the_effective_version() -> None:
    repository = InMemoryPricingRepository()
    effective = repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, _canonical_package())
    draft = repository.seed(
        PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body(price=210000), state=VersionState.DRAFT
    )
    report = await simulate_draft(draft, _context(effective_version=effective, needs_second_confirmation=False))
    assert report.has_effective_version is True
    assert {change.field for change in report.changes} == {
        "priceInclGstPaise",
        "components[CONTENT_POST].priceAllocationPaise",
    }
    price = next(change for change in report.projection_changes if change.field == "price_incl_gst_paise")
    assert (price.before, price.after) == (200000, 210000)
    assert "cost_floor_paise" not in {change.field for change in report.projection_changes}


async def test_the_second_confirmation_and_sale_readiness_are_warnings_not_violations() -> None:
    report = await simulate_draft(_draft(), _context(availability="DEFAULT_OFF", needs_second_confirmation=True))
    codes = [warning.code for warning in report.warnings]
    assert codes[0] == NEEDS_SECOND_CONFIRMATION_WARNING
    assert codes.count("PACKAGE_COMPONENT_NOT_AVAILABLE") == 4
    assert report.needs_second_confirmation is True
    assert report.violations == []


async def test_a_package_below_the_floor_is_simulated_with_its_violation_and_the_compliant_price() -> None:
    rates = FakeReference().rates
    rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    report = await simulate_draft(_draft(), _context(reference=FakeReference(rates)))
    assert [violation.code for violation in report.violations] == ["PRICING_BELOW_FLOOR"]
    assert report.violations[0].details["minimumCompliantPricePaise"] > 200000
    assert report.projection is not None


async def test_a_body_that_does_not_fit_its_kind_yields_a_report_with_only_violations() -> None:
    draft = _draft(body={"agentType": "DMA"})
    report = await simulate_draft(draft, _context())
    assert report.violations
    assert report.subject_key == PACKAGE_SUBJECT
    assert report.projection is None
    assert report.profiles == []
    assert report.worst_case is None
    assert report.derived == {}


async def test_simulation_never_changes_the_draft_or_writes_state() -> None:
    harness = make_harness()
    created = await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body())
    before = copy.deepcopy(created.version.body)
    snapshot = (dict(harness.repository.versions), list(harness.repository.events))
    await simulate_draft(created.version, _context())
    assert created.version.body == before
    assert (dict(harness.repository.versions), list(harness.repository.events)) == snapshot
    assert harness.repository.profiles == {}
    assert harness.repository.sale_calls == []


async def test_the_service_adds_request_personas_to_the_built_in_profiles() -> None:
    harness = make_harness()
    version_id = (await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body())).version.version_id
    result = await harness.service.simulate(ADMIN, version_id, personas=[HEAVY])
    assert [profile.profile for profile in result.report.profiles] == [BEST_CASE, TYPICAL, "HEAVY"]
    assert result.version.state is VersionState.SIMULATED


# ---------------------------------------------------------------- rate simulation

async def test_a_rate_draft_lists_the_effective_packages_whose_floor_it_would_change() -> None:
    repository = InMemoryPricingRepository()
    package = repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    draft = repository.seed(
        PricingKind.RATE, "thread:llm_pro", rate_body("llm_pro", raw=4000), state=VersionState.DRAFT
    )
    report = await simulate_draft(draft, _context(effective_packages=[package]))
    assert report.derived["markedUpCostPaise"] == 5320
    assert report.derived["totalMarkupPct"] == 33.0
    assert len(report.affected_packages) == 1
    affected = report.affected_packages[0]
    assert affected.version_id == str(package.version_id)
    assert affected.subject_key == PACKAGE_SUBJECT
    assert affected.cost_floor_before_paise == 19778
    assert affected.cost_floor_after_paise == 167378
    assert affected.breaches_cost_floor is False
    assert affected.breaches_minimum_margin is True
    assert affected.margin_pct_after < 2


async def test_a_rate_that_keeps_the_current_cost_affects_no_package() -> None:
    repository = InMemoryPricingRepository()
    package = repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    unchanged = repository.seed(
        PricingKind.RATE,
        "thread:llm_pro",
        rate_body("llm_pro", raw=400, fx=0, ops=0, risk=0),
        state=VersionState.DRAFT,
    )
    report = await simulate_draft(unchanged, _context(effective_packages=[package]))
    assert report.affected_packages == []


async def test_a_rate_that_would_price_a_package_below_its_cost_floor_is_flagged() -> None:
    repository = InMemoryPricingRepository()
    package = repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    draft = repository.seed(
        PricingKind.RATE, "thread:llm_pro", rate_body("llm_pro", raw=40000), state=VersionState.DRAFT
    )
    report = await simulate_draft(draft, _context(effective_packages=[package]))
    assert report.affected_packages[0].breaches_cost_floor is True


# ---------------------------------------------------------------- diff and personas

def test_diff_bodies_flattens_nested_values_and_labels_list_items_by_identity() -> None:
    assert diff_bodies(None, {"a": 1}) == []
    changes = diff_bodies(
        {"a": 1, "b": {"c": 2}, "items": [{"componentId": "X", "quantity": 1}]},
        {"a": 1, "b": {"c": 3}, "d": 4, "items": [{"componentId": "X", "quantity": 2}]},
    )
    assert [(c.field, c.before, c.after) for c in changes] == [
        ("b.c", 2, 3),
        ("d", None, 4),
        ("items[X].quantity", 1, 2),
    ]


def test_persona_profiles_are_read_from_a_usage_profile_document() -> None:
    personas = parse_persona_profiles(
        {"personas": [{"name": "HEAVY", "usagePercentByComponent": {"CONTENT_POST": 100}, "defaultUsagePercent": 10}]}
    )
    assert [(p.name, p.usage_percent_by_component, p.default_usage_percent) for p in personas] == [
        ("HEAVY", {"CONTENT_POST": 100}, 10)
    ]
    with pytest.raises(ValueError):
        parse_persona_profiles({})
    with pytest.raises(ValueError):
        parse_persona_profiles({"personas": [{"name": "X", "defaultUsagePercent": 101}]})


def test_persona_profiles_load_from_a_json_file(tmp_path: Path) -> None:
    path = tmp_path / "usage-profiles.json"
    path.write_text(json.dumps({"personas": [{"name": "LIGHT", "defaultUsagePercent": 5}]}), encoding="utf-8")
    assert [persona.name for persona in load_persona_profiles(path)] == ["LIGHT"]


# ---------------------------------------------------------------- live margin watch

class _Collector:
    def __init__(self) -> None:
        self.reports: list[list] = []

    def report(self, breaches) -> None:
        self.reports.append(list(breaches))


def _watched() -> tuple[InMemoryPricingRepository, FakeReference]:
    repository = InMemoryPricingRepository()
    repository.seed(PricingKind.POLICY, POLICY_SUBJECT, policy_body())
    repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    return repository, FakeReference()


async def test_a_package_within_floor_and_margin_is_not_reported() -> None:
    repository, reference = _watched()
    collector = _Collector()
    assert await recompute(repository=repository, reference=reference, at=START, reporter=collector) == []
    assert collector.reports == [[]]


async def test_a_rate_rise_below_the_cost_floor_is_reported_and_clears_after_repricing() -> None:
    repository, reference = _watched()
    reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    collector = _Collector()
    breaches = await recompute(repository=repository, reference=reference, at=START, reporter=collector)
    assert len(breaches) == 1
    breach = breaches[0]
    assert breach.reason == "BELOW_COST_FLOOR"
    assert (breach.agent_type, breach.agent_version, breach.package_code) == ("DMA", "1.0.0", "STARTER")
    assert breach.subject_key == PACKAGE_SUBJECT
    assert breach.price_incl_gst_paise == 200000
    assert breach.base_price_paise == 169492
    assert breach.cost_floor_paise == 1207778
    assert breach.minimum_margin_pct == 55.0
    assert breach.minimum_compliant_price_paise > 200000
    assert collector.reports == [breaches]

    reference.rates["llm_pro"] = ThreadRate("llm_pro", 400, True)
    assert await recompute(repository=repository, reference=reference, at=START, reporter=collector) == []


async def test_a_package_above_its_floor_but_below_the_minimum_margin_is_reported_separately() -> None:
    repository, reference = _watched()
    reference.rates["llm_pro"] = ThreadRate("llm_pro", 5000, True)
    breaches = await recompute(repository=repository, reference=reference, at=START, reporter=_Collector())
    assert [breach.reason for breach in breaches] == ["BELOW_MINIMUM_MARGIN"]
    assert breaches[0].cost_floor_paise == 157778


async def test_without_a_policy_only_the_cost_floor_is_watched() -> None:
    repository = InMemoryPricingRepository()
    repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    reference = FakeReference()
    reference.rates["llm_pro"] = ThreadRate("llm_pro", 5000, True)
    assert await recompute(repository=repository, reference=reference, at=START, reporter=_Collector()) == []
    reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    breaches = await recompute(repository=repository, reference=reference, at=START, reporter=_Collector())
    assert [breach.minimum_margin_pct for breach in breaches] == [None]


async def test_an_unreadable_package_body_is_skipped_and_the_rest_are_still_watched() -> None:
    repository, reference = _watched()
    repository.seed(PricingKind.PACKAGE, "package:DMA|1.0.0|BAD", {"unexpected": 1})
    reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)
    breaches = await recompute(repository=repository, reference=reference, at=START, reporter=_Collector())
    assert [breach.subject_key for breach in breaches] == [PACKAGE_SUBJECT]


async def test_the_default_reporter_logs_the_breach_metric_event(caplog: pytest.LogCaptureFixture) -> None:
    repository, reference = _watched()
    with caplog.at_level(logging.INFO):
        await recompute(repository=repository, reference=reference, at=START)
    events = [record for record in caplog.records if record.getMessage() == LIVE_MARGIN_METRIC]
    assert len(events) == 1
    assert events[0].breach_count == 0


def test_the_daily_watch_is_registered_once_by_id_on_the_scheduler() -> None:
    scheduler = MagicMock()

    async def job() -> None:
        return None

    register_margin_watch_job(scheduler, job, hour=4, minute=5)
    scheduler.add_job.assert_called_once()
    assert scheduler.add_job.call_args.args[0] is job
    kwargs = scheduler.add_job.call_args.kwargs
    assert kwargs["id"] == LIVE_MARGIN_JOB_ID == "wbe_live_margin_watch"
    assert kwargs["replace_existing"] is True
    fields = {field.name: str(field) for field in kwargs["trigger"].fields}
    assert (fields["hour"], fields["minute"]) == ("4", "5")
