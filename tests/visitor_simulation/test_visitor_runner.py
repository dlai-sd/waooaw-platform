# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
import io
import json
import logging
import urllib.request

import pytest

from visitor_simulation.cli import EXIT_GATE_FAILED, EXIT_OK, EXIT_RUN_ABORTED, EXIT_USAGE, Reporter, main
from visitor_simulation.compare import ReportError, compare_reports, load_report, write_comparison
from visitor_simulation.fake_server import FakeVisitorServer
from visitor_simulation.personas import select_personas
from visitor_simulation.runner import RunConfig, parse_inject, run_suite, write_outputs

SECRET = "vs-secret-7f3a9c1d-do-not-leak"  # fabricated
_CACHE: dict = {}


def _suite(behaviour, *, runs=3, seed=1, inject=(), personas=None, **config):
    key = (behaviour, runs, seed, tuple(inject), tuple(personas or ()), tuple(sorted(config.items())))
    if key not in _CACHE:
        with FakeVisitorServer(behaviour, SECRET) as server:
            cfg = RunConfig(
                base_url=server.base_url,
                secret=SECRET,
                runs=runs,
                seed=seed,
                personas=select_personas(list(personas) if personas else None),
                inject=tuple(inject),
                **config,
            )
            _CACHE[key] = (run_suite(cfg, sleep=lambda _: None), server.base_url)
    return _CACHE[key][0]


def _describe(result):
    return [
        (
            c.persona_id,
            c.mode,
            c.ended_reason,
            c.final_state,
            c.final_outcome,
            j.task.success,
            j.policy.counts(),
            [n for cr in j.criteria.values() for n in cr.notes],
        )
        for c, j in result.items
        if j.failed
    ]


def test_good_behaviour_succeeds_for_every_persona_without_policy_violations():
    result = _suite("good")
    assert len(result.items) == 21
    assert _describe(result) == []
    overall = result.report["overall"]
    assert overall["taskSuccessRate"] == 1.0 and overall["policyViolationTotal"] == 0 and overall["failures"] == 0


def test_fit_personas_reach_full_success_and_other_personas_leave_a_lead():
    result = _suite("good")
    outcomes = {}
    for conv, _ in result.items:
        outcomes.setdefault(conv.persona_id, set()).add(conv.final_outcome)
    for persona in ("dr_mehta", "rupali", "kiran", "yashus"):
        assert outcomes[persona] == {"FULL_SUCCESS"}
    for persona in ("farmer", "tutor_seeker", "trader"):
        assert outcomes[persona] == {"LEAD"}


def test_judge_scores_good_strictly_higher_than_legacy_for_every_persona():
    good, legacy = _suite("good").report, _suite("legacy").report
    assert set(good["personas"]) == set(legacy["personas"]) and len(good["personas"]) == 7
    for persona, stats in good["personas"].items():
        assert stats["meanScore"] > legacy["personas"][persona]["meanScore"], persona
        assert stats["taskSuccessRate"] > legacy["personas"][persona]["taskSuccessRate"], persona
    assert good["overall"]["meanScore"] >= 4.0 and legacy["overall"]["meanScore"] <= 2.5
    for criterion in ("welcome_clarity", "curiosity", "value", "next_step", "voice"):
        assert good["overall"]["criterionMeans"][criterion] > legacy["overall"]["criterionMeans"][criterion], criterion


def test_legacy_behaviour_fails_the_task_and_breaks_policy():
    legacy = _suite("legacy").report["overall"]
    assert legacy["taskSuccessRate"] == 0.0 and legacy["failureRate"] == 1.0
    assert legacy["policyViolations"]["STOP_ON_EVERY_MESSAGE"] > 0
    assert legacy["outcomes"]["FULL_SUCCESS"] == 0 and legacy["leadRate"] == 0.0
    assert legacy["turnsToFirstValue"]["reachedRate"] == 0.0
    assert set(legacy["stateDropoff"]) <= {"DISCOVER", "STOPPED"}
    assert legacy["optOutRate"] > 0


def test_report_carries_per_state_dropoff_first_value_and_opt_out_metrics():
    overall = _suite("good").report["overall"]
    assert overall["turnsToFirstValue"]["reachedRate"] == 1.0 and 3 <= overall["turnsToFirstValue"]["median"] <= 8
    assert overall["stateDropoff"] == {} and overall["optOutRate"] == 0.0
    assert set(overall["criterionMeans"]) == {"welcome_clarity", "curiosity", "value", "next_step", "honesty", "voice", "safety"}
    assert overall["latencyMs"]["p95"] >= 0


def test_compare_flags_legacy_to_good_as_an_improvement_and_the_reverse_as_a_gate_failure():
    legacy, good = _suite("legacy").report, _suite("good").report
    forward = compare_reports(legacy, good, min_lift=0.5)
    assert forward.gate_passed and forward.verdict == "IMPROVED"
    assert {p.verdict for p in forward.personas} == {"improved"}
    assert forward.lift is None and forward.lift_met is True

    backward = compare_reports(good, legacy)
    assert not backward.gate_passed
    assert any(r.startswith("POLICY_VIOLATIONS") for r in backward.reasons)
    assert sum(r.startswith("PERSONA_REGRESSION") for r in backward.reasons) == 7


def _report(rate, std, violations=0, lead=0.5):
    return {
        "schema": "visitor-simulation-report/1",
        "overall": {"policyViolationTotal": violations, "leadRate": lead},
        "personas": {"dr_mehta": {"runs": 20, "taskSuccessRate": rate, "taskSuccessStd": std}},
    }


@pytest.mark.parametrize(
    ("base", "new", "verdict", "gate"),
    [
        ((0.80, 0.40), (0.70, 0.46), "unchanged", True),
        ((0.80, 0.40), (0.30, 0.46), "regressed", False),
        ((0.50, 0.50), (0.60, 0.49), "unchanged", True),
        ((0.50, 0.40), (0.95, 0.20), "improved", True),
        ((1.00, 0.00), (1.00, 0.00), "unchanged", True),
    ],
)
def test_noise_decides_between_improved_unchanged_and_regressed(base, new, verdict, gate):
    comparison = compare_reports(_report(*base), _report(*new))
    assert comparison.personas[0].verdict == verdict and comparison.gate_passed is gate


def test_standard_error_basis_is_a_stricter_noise_estimate():
    base, new = _report(0.80, 0.40), _report(0.50, 0.50)
    assert compare_reports(base, new).gate_passed
    strict = compare_reports(base, new, noise_basis="stderr")
    assert not strict.gate_passed and strict.personas[0].noise == pytest.approx(0.5 / 20**0.5, abs=1e-3)
    with pytest.raises(ValueError):
        compare_reports(base, new, noise_basis="vibes")


def test_gate_fails_on_any_policy_violation_missing_persona_or_unmet_lift():
    assert not compare_reports(_report(0.9, 0.3), _report(0.9, 0.3, violations=1)).gate_passed
    missing = _report(0.9, 0.3)
    missing["personas"] = {}
    gate = compare_reports(_report(0.9, 0.3), missing)
    assert not gate.gate_passed and gate.personas[0].verdict == "missing"
    unmet = compare_reports(_report(0.9, 0.3, lead=0.5), _report(0.9, 0.3, lead=0.55), min_lift=0.2)
    assert not unmet.gate_passed and unmet.lift_met is False and any(r.startswith("LIFT_NOT_MET") for r in unmet.reasons)
    assert compare_reports(_report(0.9, 0.3, lead=0.5), _report(0.9, 0.3, lead=0.65), min_lift=0.2).gate_passed


@pytest.mark.parametrize("inject", ["media", "unknown-language", "stop-mid", "slow"])
def test_good_behaviour_survives_each_failure_injection(inject):
    result = _suite("good", runs=2, inject=(inject,))
    assert _describe(result) == []
    notes = {inject: {t.note for c, _ in result.items for t in c.turns}}
    if inject == "slow":
        assert all(c.timeouts == 1 for c, _ in result.items)
    elif inject == "stop-mid":
        assert all(c.stop_sent and c.final_outcome != "OPT_OUT" for c, _ in result.items)
        assert all(j.criteria["safety"].score >= 4 for _, j in result.items)
        assert "inject:start" in notes[inject]
    else:
        assert f"inject:{inject}" in notes[inject]


def test_all_injections_together_and_legacy_under_injection():
    combined = _suite("good", runs=1, inject=("media", "unknown-language", "stop-mid", "slow"))
    assert _describe(combined) == []
    legacy = _suite("legacy", runs=1, inject=("stop-mid", "media"))
    assert legacy.report["overall"]["taskSuccessRate"] == 0.0
    with pytest.raises(ValueError):
        parse_inject(["media,telepathy"])
    assert parse_inject(["media,slow", "slow", "stop-mid"]) == ("media", "slow", "stop-mid")


def test_a_hard_model_call_cap_stops_the_run_and_is_reported():
    result = _suite("good", runs=3, max_model_calls=10)
    assert result.report["capExceeded"].startswith("model-call cap")
    assert result.report["budget"]["modelCalls"] == 10
    assert len(result.items) < 21


def test_no_model_mode_makes_no_model_calls():
    result = _suite("good", runs=1, model="none", personas=["dr_mehta"])
    assert result.report["budget"]["modelCalls"] == 0 and _describe(result) == []


def test_simulator_only_calls_the_visitor_api_base_url(monkeypatch):
    seen = []
    original = urllib.request.urlopen

    def spy(request, timeout=None):
        seen.append(request.full_url)
        return original(request, timeout=timeout)

    monkeypatch.setattr(urllib.request, "urlopen", spy)
    with FakeVisitorServer("good", SECRET) as server:
        result = run_suite(
            RunConfig(base_url=server.base_url, secret=SECRET, runs=1, seed=9, personas=select_personas(["dr_mehta", "farmer"])),
            sleep=lambda _: None,
        )
        assert seen and all(url.startswith(server.base_url + "/api/v1/visitor/") for url in seen)
        assert any("/handoffs/" in url and url.endswith("/tap") for url in seen)
        assert not any("portal.fake.invalid" in url for url in seen)
        assert result.report["hostsCalled"] == [server.base_url.removeprefix("http://")]
        assert {r[1].split("/")[3] for r in server.requests} == {"visitor"}


def test_secret_never_appears_in_logs_reports_or_console(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("VS_TEST_SECRET", SECRET)
    out = io.StringIO()
    with FakeVisitorServer("good", SECRET) as server, caplog.at_level(logging.DEBUG):
        code = main(
            [
                "run",
                "--base-url",
                server.base_url,
                "--secret-env",
                "VS_TEST_SECRET",
                "--runs",
                "1",
                "--seed",
                "5",
                "--inject",
                "slow",
                "--output",
                str(tmp_path / "out"),
            ],
            reporter=Reporter(out),
        )
    assert code == EXIT_OK
    produced = [p for p in (tmp_path / "out").iterdir()]
    assert {p.name for p in produced} == {"report.json", "summary.md", "transcripts.json"}
    haystacks = [out.getvalue(), caplog.text, *(p.read_text(encoding="utf-8") for p in produced)]
    assert all(SECRET not in text for text in haystacks)
    config = RunConfig(base_url="http://127.0.0.1:1", secret=SECRET)
    assert SECRET not in repr(config)


def test_cli_requires_the_secret_in_the_environment_never_argv(monkeypatch, tmp_path):
    monkeypatch.delenv("VS_MISSING_SECRET", raising=False)
    out = io.StringIO()
    code = main(
        ["run", "--base-url", "http://127.0.0.1:1", "--secret-env", "VS_MISSING_SECRET", "--output", str(tmp_path)],
        reporter=Reporter(out),
    )
    assert code == EXIT_USAGE and "is not set" in out.getvalue()
    with pytest.raises(SystemExit):
        main(["run", "--base-url", "http://127.0.0.1:1", "--secret", "abc"], reporter=Reporter(out))


def test_cli_reports_bad_personas_and_wrong_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("VS_TEST_SECRET", "wrong-secret")
    out = io.StringIO()
    with FakeVisitorServer("good", SECRET) as server:
        assert (
            main(
                [
                    "run",
                    "--base-url",
                    server.base_url,
                    "--secret-env",
                    "VS_TEST_SECRET",
                    "--runs",
                    "1",
                    "--personas",
                    "nobody",
                    "--output",
                    str(tmp_path),
                ],
                reporter=Reporter(out),
            )
            == EXIT_USAGE
        )
        assert (
            main(
                [
                    "run",
                    "--base-url",
                    server.base_url,
                    "--secret-env",
                    "VS_TEST_SECRET",
                    "--runs",
                    "1",
                    "--personas",
                    "kiran",
                    "--output",
                    str(tmp_path),
                ],
                reporter=Reporter(out),
            )
            == EXIT_RUN_ABORTED
        )
    assert "wrong-secret" not in out.getvalue()


def test_cli_run_then_compare_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("VS_TEST_SECRET", SECRET)
    for behaviour in ("legacy", "good"):
        with FakeVisitorServer(behaviour, SECRET) as server:
            code = main(
                [
                    "run",
                    "--base-url",
                    server.base_url,
                    "--secret-env",
                    "VS_TEST_SECRET",
                    "--runs",
                    "2",
                    "--seed",
                    "3",
                    "--personas",
                    "dr_mehta,farmer",
                    "--output",
                    str(tmp_path / behaviour),
                ],
                reporter=Reporter(io.StringIO()),
            )
        assert code == EXIT_OK
    legacy, good = tmp_path / "legacy" / "report.json", tmp_path / "good" / "report.json"
    out = io.StringIO()
    assert (
        main(
            ["compare", "--baseline", str(legacy), "--new", str(good), "--min-lift", "0.2", "--output", str(tmp_path / "up")],
            reporter=Reporter(out),
        )
        == EXIT_OK
    )
    assert "improved" in out.getvalue()
    assert json.loads((tmp_path / "up" / "comparison.json").read_text())["gatePassed"] is True
    assert (tmp_path / "up" / "comparison.md").exists()
    assert (
        main(
            ["compare", "--baseline", str(good), "--new", str(legacy), "--output", str(tmp_path / "down")],
            reporter=Reporter(io.StringIO()),
        )
        == EXIT_GATE_FAILED
    )
    assert (
        main(["compare", "--baseline", str(tmp_path / "missing.json"), "--new", str(good)], reporter=Reporter(io.StringIO()))
        == EXIT_USAGE
    )


def test_report_files_are_valid_json_and_load_back(tmp_path):
    result = _suite("good", runs=1, personas=["kiran"])
    paths = write_outputs(result, tmp_path)
    report = load_report(paths[0])
    assert report["config"]["runsPerPersona"] == 1 and report["personas"]["kiran"]["runs"] == 1
    transcripts = json.loads(paths[2].read_text())
    assert transcripts[0]["subjectKey"].startswith("sim-kiran-") and transcripts[0]["judge"]["taskSuccess"]["success"]
    write_comparison(compare_reports(report, report), tmp_path / "cmp")
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    with pytest.raises(ReportError):
        load_report(bad)


@pytest.mark.parametrize("persona_id", ["rupali", "trader"])
def test_injected_detours_do_not_use_up_an_overwhelmed_personas_patience(persona_id):
    from visitor_simulation.client import VisitorClient
    from visitor_simulation.judge import Judge
    from visitor_simulation.runner import run_conversation

    persona = select_personas([persona_id])[0]
    with FakeVisitorServer("good", SECRET) as server:
        client = VisitorClient(server.base_url, SECRET, sleep=lambda _: None)
        conv = run_conversation(
            client,
            persona,
            mode="overwhelmed",
            seed=3,
            subject_key=f"sim-{persona_id}-detours",
            inject=("media", "unknown-language", "stop-mid", "slow"),
        )
    assert conv.goal.patience > persona.patience - 2
    assert Judge().evaluate(conv).failed is False
