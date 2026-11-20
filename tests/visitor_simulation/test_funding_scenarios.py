# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-01
# Constitutional basis: C-048, C-049, C-059, C-063
import copy
import io
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from visitor_simulation.cli import EXIT_GATE_FAILED, EXIT_OK, EXIT_RUN_ABORTED, EXIT_USAGE, Reporter, main
from visitor_simulation.funding_fake import CLASS_HEADER, ROLES_HEADER, SIMULATOR_ROLE
from visitor_simulation.scenario_runner import (
    PACK_SCHEMA,
    Pack,
    ScenarioError,
    _post,
    load_pack,
    pack_path,
    parse_pack,
    run_pack,
    start_fake,
)
from visitor_simulation.scenario_server import ScenarioServer

TRACEABILITY = Path(__file__).resolve().parents[1] / "fixtures/wc136/funding-walkthroughs.yaml"
FIRST = "WT01-anonymous-visitor-acquisition"
VISITOR_STEP = {
    "action": "visitor_turn",
    "actor": "VISITOR",
    "channel": "WHATSAPP",
    "relationshipState": "NONE",
    "purpose": "PRESALES_OR_MARKETPLACE",
    "params": {"lead": "visitor-1", "tenant": "marketplace-a"},
}


@pytest.fixture
def serve():
    servers: list[ScenarioServer] = []

    def start(pack: str, **options: bool) -> ScenarioServer:
        servers.append(start_fake(pack, **options))
        return servers[-1]

    yield start
    for server in servers:
        server.stop()


def _run(serve, pack: Pack, **options):
    server = serve(pack.name)
    return run_pack(pack, server.base_url, **options)


def _failures(report) -> list[str]:
    return [
        f"{scenario['id']} / {step['id']}: {failure}"
        for scenario in report["scenarios"]
        for step in scenario["steps"]
        for failure in step["failures"]
    ]


def _tampered(pack: Pack, **expect_changes) -> Pack:
    first = pack.scenarios[0]
    step = replace(first.steps[0], expect={**first.steps[0].expect, **expect_changes})
    return replace(pack, scenarios=(replace(first, steps=(step, *first.steps[1:])), *pack.scenarios[1:]))


def _cli(*args: str) -> tuple[int, str]:
    stream = io.StringIO()
    return main(list(args), reporter=Reporter(stream)), stream.getvalue()


def test_funding_pack_validates():
    pack = load_pack(pack_path("funding"))
    assert pack.name == "funding"
    assert pack.seed == 136
    assert all(scenario.steps for scenario in pack.scenarios)


def test_funding_pack_passes_against_the_loopback_fake(serve):
    pack = load_pack(pack_path("funding"))
    report = _run(serve, pack)
    assert _failures(report) == []
    assert report["summary"]["passed"] is True
    assert report["summary"]["scenarios"] == len(pack.scenarios)
    assert all(scenario["stepsRun"] == scenario["stepsTotal"] for scenario in report["scenarios"])


def test_same_seed_gives_an_identical_report(serve):
    pack = load_pack(pack_path("funding"))
    assert _run(serve, pack) == _run(serve, pack)
    assert _run(serve, pack, seed=7)["seed"] == 7


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"accountClass": "SUBSCRIPTION"}, "accountClass: expected SUBSCRIPTION, got ACQUISITION"),
        ({"accountClass": "NONE"}, "expected no X-Spend-Account-Class header"),
        ({"walletMovement": {"account": "ACQUISITION", "unit": "PAISE", "delta": -41}}, "walletMovement"),
        ({"walletMovement": "NONE"}, "walletMovement: expected none"),
        ({"customerVisible": {"outcome": "SOMETHING_ELSE"}}, "customerVisible.outcome"),
        ({"customerVisible": {"outcome": "VISITOR_REPLIED", "contains": ["zzz-not-said"]}}, "customerVisible.contains"),
        ({"customerVisible": {"outcome": "VISITOR_REPLIED", "silent": True}}, "customerVisible.silent"),
        ({"fields": {"leadRef": "lead-wrong"}}, "leadRef"),
        ({"status": 403}, "status: expected 403, got 200"),
    ],
)
def test_a_wrong_expectation_fails_the_run(serve, change, message):
    pack = _tampered(load_pack(pack_path("funding")), **change)
    report = _run(serve, pack, only=(FIRST,))
    assert report["summary"]["passed"] is False
    assert report["summary"]["scenariosFailed"] == 1
    assert any(message in failure for failure in _failures(report))


def test_a_failing_step_stops_its_scenario(serve):
    pack = _tampered(load_pack(pack_path("funding")), accountClass="TRIAL")
    scenario = _run(serve, pack, only=(FIRST,))["scenarios"][0]
    assert scenario["stepsRun"] == 1 < scenario["stepsTotal"]


def test_the_header_is_absent_without_the_simulator_role(serve):
    pack = load_pack(pack_path("funding"))
    report = _run(serve, pack, roles=(), only=(FIRST,))
    assert report["summary"]["passed"] is False
    assert any("got None" in failure for failure in _failures(report))


def _first_visitor_turn(base_url: str, roles: str, extra: dict[str, str] | None = None):
    headers = {**({ROLES_HEADER: roles} if roles else {}), **(extra or {})}
    _post(base_url, "/scenario/reset", {"seed": 1}, headers, 5.0)
    return _post(base_url, "/scenario/step", VISITOR_STEP, headers, 5.0)


def test_the_class_header_needs_the_role_and_the_flag(serve):
    on, off = serve("funding"), serve("funding", simulator_headers_enabled=False)
    status, headers, body = _first_visitor_turn(on.base_url, SIMULATOR_ROLE)
    assert (status, headers.get(CLASS_HEADER.lower())) == (200, "ACQUISITION")
    assert body["outcome"] == "VISITOR_REPLIED"
    assert CLASS_HEADER.lower() not in _first_visitor_turn(on.base_url, "")[1]
    assert CLASS_HEADER.lower() not in _first_visitor_turn(on.base_url, "customer,operator")[1]
    assert CLASS_HEADER.lower() not in _first_visitor_turn(off.base_url, SIMULATOR_ROLE)[1]


def test_a_client_supplied_class_header_is_never_echoed(serve):
    headers = _first_visitor_turn(serve("funding").base_url, "", {CLASS_HEADER: "SIMULATION"})[1]
    assert CLASS_HEADER.lower() not in headers


def test_the_fake_refuses_a_declared_state_that_is_not_the_actual_one(serve):
    base_url = serve("funding").base_url
    _post(base_url, "/scenario/reset", {"seed": 1}, {}, 5.0)
    step = {**VISITOR_STEP, "relationshipState": "HIRED"}
    status, headers, body = _post(base_url, "/scenario/step", step, {ROLES_HEADER: SIMULATOR_ROLE}, 5.0)
    assert (status, body["outcome"]) == (409, "SCENARIO_STATE_MISMATCH")
    assert CLASS_HEADER.lower() not in headers


def test_references_follow_the_seed(serve):
    base_url = serve("funding").base_url
    refs = []
    for seed in (1, 1, 2):
        _post(base_url, "/scenario/reset", {"seed": seed}, {}, 5.0)
        refs.append(_post(base_url, "/scenario/step", VISITOR_STEP, {}, 5.0)[2]["leadRef"])
    assert refs[0] == refs[1] != refs[2]


def _raw() -> dict:
    return {
        "schema": PACK_SCHEMA,
        "pack": "funding",
        "seed": 1,
        "scenarios": [
            {
                "id": "X",
                "title": "t",
                "source": "s",
                "steps": [
                    {
                        **{k: v for k, v in VISITOR_STEP.items() if k != "params"},
                        "id": "a",
                        "expect": {
                            "accountClass": "ACQUISITION",
                            "walletMovement": "NONE",
                            "customerVisible": {"outcome": "VISITOR_REPLIED"},
                        },
                    }
                ],
            }
        ],
    }


def _step(raw: dict) -> dict:
    return raw["scenarios"][0]["steps"][0]


MALFORMED = {
    "wrong-schema": lambda raw: raw.update(schema="other/1"),
    "unknown-top-key": lambda raw: raw.update(extra=1),
    "boolean-seed": lambda raw: raw.update(seed=True),
    "no-scenarios": lambda raw: raw.update(scenarios=[]),
    "scenarios-not-a-list": lambda raw: raw.update(scenarios={}),
    "duplicate-scenario": lambda raw: raw["scenarios"].append(copy.deepcopy(raw["scenarios"][0])),
    "empty-steps": lambda raw: raw["scenarios"][0].update(steps=[]),
    "unknown-action": lambda raw: _step(raw).update(action="steal_money"),
    "missing-purpose": lambda raw: _step(raw).pop("purpose"),
    "unknown-channel": lambda raw: _step(raw).update(channel="SMS"),
    "unknown-actor": lambda raw: _step(raw).update(actor="ROBOT"),
    "unknown-class": lambda raw: _step(raw)["expect"].update(accountClass="FREE"),
    "zero-delta": lambda raw: _step(raw)["expect"].update(walletMovement={"account": "TRIAL", "unit": "PAISE", "delta": 0}),
    "bad-movement-unit": lambda raw: _step(raw)["expect"].update(walletMovement={"account": "TRIAL", "unit": "EUR", "delta": 1}),
    "missing-outcome": lambda raw: _step(raw)["expect"].update(customerVisible={"contains": ["x"]}),
    "bad-field-form": lambda raw: _step(raw)["expect"].update(fields={"a": {"$foo": 1}}),
    "empty-fields": lambda raw: _step(raw)["expect"].update(fields={}),
    "status-out-of-range": lambda raw: _step(raw)["expect"].update(status=99),
}


def test_a_minimal_pack_parses():
    assert parse_pack(_raw()).scenarios[0].steps[0].action == "visitor_turn"


@pytest.mark.parametrize("mutate", MALFORMED.values(), ids=MALFORMED.keys())
def test_malformed_packs_are_rejected(mutate):
    raw = _raw()
    mutate(raw)
    with pytest.raises(ScenarioError):
        parse_pack(raw)


def test_a_pricing_step_must_not_carry_funding_keys():
    raw = _raw()
    raw["pack"] = "pricing"
    _step(raw).update(actor="PRICING_ADMIN", action="create_draft", expect={"outcome": "DRAFT_CREATED"})
    with pytest.raises(ScenarioError, match="belong to funding steps"):
        parse_pack(raw)


def test_every_walkthrough_scenario_and_admin_journey_is_traceable_and_every_scenario_is_claimed():
    coverage = yaml.safe_load(TRACEABILITY.read_text(encoding="utf-8"))["coverage"]
    refs = {entry["ref"] for entry in coverage}
    required = {f"walk-through {n}" for n in range(1, 13)} | {f"S{n}" for n in range(1, 15)} | {f"A{n}" for n in range(1, 14)}
    assert required <= refs
    claimed: dict[str, set[str]] = {"funding": set(), "pricing": set()}
    for entry in coverage:
        assert set(entry) <= {"ref", "kind", "funding", "pricing"}
        assert entry["funding" if "funding" in entry else "pricing"], entry["ref"]
        for name in claimed:
            claimed[name].update(entry.get(name, []))
    for name, ids in claimed.items():
        assert ids == {scenario.id for scenario in load_pack(pack_path(name)).scenarios}, name


def test_cli_runs_the_funding_pack_and_writes_the_report(tmp_path):
    code, text = _cli("scenarios", "--pack", "funding", "--output", str(tmp_path))
    assert code == EXIT_OK, text
    report = json.loads((tmp_path / "scenarios-funding-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["passed"] is True
    assert report["target"] == "loopback-fake"


def test_cli_runs_one_scenario(tmp_path):
    code, text = _cli("scenarios", "--pack", "funding", "--only", FIRST, "--output", str(tmp_path))
    assert code == EXIT_OK, text
    assert "1/1 scenarios passed" in text


def test_cli_fails_the_gate_without_the_simulator_role_or_with_the_flag_off(tmp_path):
    assert _cli("scenarios", "--pack", "funding", "--roles", "", "--output", str(tmp_path))[0] == EXIT_GATE_FAILED
    assert _cli("scenarios", "--pack", "funding", "--simulator-headers", "off", "--output", str(tmp_path))[0] == EXIT_GATE_FAILED


@pytest.mark.parametrize(
    "args",
    [
        ("--pack", "funding", "--only", "no-such-scenario"),
        ("--pack", "funding", "--target", "ftp://example.com"),
        ("--pack", "all", "--target", "http://127.0.0.1:9"),
        ("--pack", "funding", "--target", "http://example.com"),
    ],
)
def test_cli_rejects_unusable_arguments(tmp_path, args):
    assert _cli("scenarios", *args, "--output", str(tmp_path))[0] == EXIT_USAGE


def test_cli_aborts_when_the_target_is_unreachable(tmp_path):
    server = start_fake("funding")
    url = server.base_url
    server.stop()
    code, text = _cli("scenarios", "--pack", "funding", "--target", url, "--timeout", "1", "--output", str(tmp_path))
    assert code == EXIT_RUN_ABORTED, text
