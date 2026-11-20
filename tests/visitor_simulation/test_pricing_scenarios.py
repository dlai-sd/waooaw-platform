# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-02
# Constitutional basis: C-048, C-049, C-059, C-063, C-088, C-091
import io
import json
from dataclasses import replace

import pytest

from visitor_simulation.cli import EXIT_OK, Reporter, main
from visitor_simulation.pricing_fake import STARTER, PricingFake, base_price_paise, minimum_compliant_price_paise
from visitor_simulation.scenario_runner import Pack, load_pack, pack_path, run_pack, start_fake


@pytest.fixture
def pack() -> Pack:
    return load_pack(pack_path("pricing"))


@pytest.fixture
def base_url():
    server = start_fake("pricing")
    yield server.base_url
    server.stop()


def _failures(report) -> list[str]:
    return [
        f"{scenario['id']} / {step['id']}: {failure}"
        for scenario in report["scenarios"]
        for step in scenario["steps"]
        for failure in step["failures"]
    ]


def _tampered(pack: Pack, scenario_id: str, step_id: str, **expect_changes) -> Pack:
    scenarios = []
    for scenario in pack.scenarios:
        steps = []
        for step in scenario.steps:
            target = scenario.id == scenario_id and step.id == step_id
            steps.append(replace(step, expect={**step.expect, **expect_changes}) if target else step)
        scenarios.append(replace(scenario, steps=tuple(steps)))
    return replace(pack, scenarios=tuple(scenarios))


def _step(fake: PricingFake, action: str, actor: str = "PRICING_ADMIN", **params):
    status, _, payload = fake.handle("POST", "/scenario/step", {}, {"action": action, "actor": actor, "params": params})
    return status, payload


def test_pricing_pack_validates(pack):
    assert pack.name == "pricing"
    assert pack.seed == 136
    assert all(step.channel is None and step.purpose is None for scenario in pack.scenarios for step in scenario.steps)


def test_pricing_pack_exercises_every_pricing_action(pack):
    assert {step.action for scenario in pack.scenarios for step in scenario.steps} == set(PricingFake.action_names())


def test_pricing_pack_passes_against_the_loopback_fake(pack, base_url):
    report = run_pack(pack, base_url)
    assert _failures(report) == []
    assert report["summary"]["passed"] is True
    assert report["summary"]["scenarios"] == len(pack.scenarios)


def test_pricing_pack_does_not_depend_on_the_simulator_role(pack, base_url):
    assert run_pack(pack, base_url, roles=())["summary"]["passed"] is True


def test_same_seed_gives_an_identical_report(pack, base_url):
    assert run_pack(pack, base_url) == run_pack(pack, base_url)


@pytest.mark.parametrize(
    ("scenario_id", "step_id", "change", "message"),
    [
        ("A03-below-floor-refusal", "far-below-floor", {"outcome": "DRAFT_CREATED"}, "outcome: expected DRAFT_CREATED"),
        ("A03-below-floor-refusal", "far-below-floor", {"status": 200}, "status: expected 200, got 422"),
        (
            "A03-below-floor-refusal",
            "far-below-floor",
            {"fields": {"minimumCompliantPricePaise": 51468}},
            "minimumCompliantPricePaise: expected 51468, got 51469",
        ),
        (
            "A05-founder-authorizes-with-step-up",
            "founder-without-step-up",
            {"outcome": "AUTHORIZED", "status": 200},
            "outcome: expected AUTHORIZED",
        ),
        (
            "A04-simulate-margin-and-profiles",
            "simulate",
            {"fields": {"marginPercent": 99.9}},
            "marginPercent: expected 99.9, got 88.4",
        ),
    ],
)
def test_a_wrong_pricing_expectation_fails_the_run(pack, base_url, scenario_id, step_id, change, message):
    report = run_pack(_tampered(pack, scenario_id, step_id, **change), base_url, only=(scenario_id,))
    assert report["summary"]["passed"] is False
    assert any(message in failure for failure in _failures(report))


def test_the_cost_floor_and_minimum_compliant_price_follow_the_engine_rules():
    assert base_price_paise(200000) == 169492
    assert minimum_compliant_price_paise(19628) == 51469
    assert base_price_paise(51469) >= -(-19628 * 100 // 45) > base_price_paise(51468)


def test_authorization_evidence_is_deterministic_per_seed():
    ids = []
    for seed in (5, 5, 6):
        fake = PricingFake()
        fake.reset(seed)
        _step(fake, "create_draft", id="v1", kind="PACKAGE", subject=STARTER, priceInclGstPaise=220000)
        _step(fake, "simulate", id="v1")
        _step(fake, "submit", id="v1")
        ids.append(_step(fake, "authorize", "FOUNDER", id="v1", stepUp=True)[1]["evidenceId"])
    assert ids[0] == ids[1] != ids[2]


def test_malformed_requests_are_refused_not_crashed():
    fake = PricingFake()
    assert fake.handle("POST", "/scenario/step", {}, {"action": "no_such_action", "actor": "FOUNDER", "params": {}})[0] == 400
    assert fake.handle("POST", "/scenario/step", {}, {"action": "create_draft", "actor": "FOUNDER", "params": {}})[0] == 400
    assert fake.handle("POST", "/scenario/reset", {}, {"seed": True})[0] == 400
    assert fake.handle("GET", "/scenario/other", {}, None)[0] == 400


def test_cli_runs_both_packs_and_writes_a_report_for_each(tmp_path):
    stream = io.StringIO()
    code = main(["scenarios", "--pack", "all", "--output", str(tmp_path)], reporter=Reporter(stream))
    assert code == EXIT_OK, stream.getvalue()
    for name in ("funding", "pricing"):
        report = json.loads((tmp_path / f"scenarios-{name}-report.json").read_text(encoding="utf-8"))
        assert report["summary"]["passed"] is True
        assert report["pack"] == name
