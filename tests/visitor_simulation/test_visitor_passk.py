# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-05
# Constitutional basis: C-048, C-049, C-059, C-063
import io
import json
from types import SimpleNamespace

import pytest

from visitor_simulation.cli import EXIT_OK, EXIT_USAGE, Reporter, main
from visitor_simulation.compare import ReportError, compare_reports, load_report, render_markdown
from visitor_simulation.fake_server import FakeVisitorServer
from visitor_simulation.models import Conversation
from visitor_simulation.personas import PersonaError, load_default_k, select_personas
from visitor_simulation.policy import DEFAULT_CONTENT_PATH, PolicyError, load_protocol_policy
from visitor_simulation.runner import LEGACY_REPORT_SCHEMA, REPORT_SCHEMA, RunConfig, reliability_stats, run_suite

SECRET = "vs-secret-7f3a9c1d-do-not-leak"  # fabricated


def _items(spec):
    """(conversation, judged) pairs: ``spec`` maps a seed to the success of each of its trials."""
    items = []
    for seed, outcomes in spec.items():
        for trial, success in enumerate(outcomes):
            conv = Conversation(persona_id="dr_mehta", seed=seed * 1000 + trial, seed_group=seed, trial=trial)
            items.append((conv, SimpleNamespace(task=SimpleNamespace(success=success))))
    return items


def _run(behaviour, *, runs=2, k=3, seed=1, personas=("dr_mehta", "farmer"), **config):
    with FakeVisitorServer(behaviour, SECRET) as server:
        cfg = RunConfig(
            base_url=server.base_url,
            secret=SECRET,
            runs=runs,
            seed=seed,
            personas=select_personas(list(personas) if personas else None),
            k=k,
            **config,
        )
        return run_suite(cfg, sleep=lambda _: None)


def _groups(result):
    groups = {}
    for conv, judged in result.items:
        groups.setdefault(conv.seed_group, []).append((conv, judged))
    return groups


def test_pass_k_is_the_share_of_seeds_where_all_k_runs_succeed():
    spec = {1: [True, True, True], 2: [True, False, True], 3: [False, False, False], 4: [True, True, True]}
    assert reliability_stats(_items(spec), 3) == {"k": 3, "seeds": 4, "passK": 0.5, "runVariance": 0.5}
    assert reliability_stats(_items({1: [True, True, True], 2: [True, True, True]}), 3)["runVariance"] == 0.0


def test_pass_k_is_stricter_than_the_mean_success_rate():
    stats = reliability_stats(_items({1: [True, True, False], 2: [True, True, True]}), 3)
    assert stats["passK"] == 0.5 and 5 / 6 > stats["passK"]


def test_incomplete_seeds_are_left_out_and_no_seed_gives_no_estimate():
    stats = reliability_stats(_items({1: [True, True, True], 2: [False, False]}), 3)
    assert stats == {"k": 3, "seeds": 1, "passK": 1.0, "runVariance": 0.0}
    assert reliability_stats([], 3) == {"k": 3, "seeds": 0, "passK": None, "runVariance": None}


def test_runs_without_a_seed_group_are_their_own_seed():
    ungrouped = [
        (Conversation(persona_id="dr_mehta", seed=7), SimpleNamespace(task=SimpleNamespace(success=True))),
        (Conversation(persona_id="dr_mehta", seed=8), SimpleNamespace(task=SimpleNamespace(success=False))),
    ]
    assert reliability_stats(ungrouped, 1)["passK"] == 0.5


def test_a_suite_runs_k_independent_trials_per_seed_and_reports_pass_k():
    result = _run("good")
    assert len(result.items) == 12
    groups = _groups(result)
    assert len(groups) == 4 and all(len(runs) == 3 for runs in groups.values())
    for group, runs in groups.items():
        assert sorted(conv.trial for conv, _ in runs) == [0, 1, 2]
        assert len({conv.seed for conv, _ in runs}) == 3
        assert len({conv.mode for conv, _ in runs}) == 1
        assert next(conv.seed for conv, _ in runs if conv.trial == 0) == group
    assert len({conv.subject_key for conv, _ in result.items}) == 12
    assert all(conv.subject_key.endswith(f"-k{conv.trial:02d}") == (conv.trial > 0) for conv, _ in result.items)

    expected = sum(1 for runs in groups.values() if all(judged.task.success for _, judged in runs)) / len(groups)
    overall = result.report["overall"]
    assert overall["k"] == 3 and overall["seeds"] == 4 and overall["passK"] == expected
    assert 0.0 <= overall["runVariance"] <= 0.5
    assert overall["pass1"] == overall["taskSuccessRate"] and overall["passK"] <= overall["pass1"]
    assert {pid: stats["seeds"] for pid, stats in result.report["personas"].items()} == {"dr_mehta": 2, "farmer": 2}


def test_report_names_the_schema_k_and_the_policy_it_was_judged_against():
    result = _run("good", runs=1, k=2, personas=("kiran",))
    policy = load_protocol_policy()
    report = result.report
    assert report["schema"] == REPORT_SCHEMA and REPORT_SCHEMA != LEGACY_REPORT_SCHEMA
    assert report["policyVersion"] == policy.version and report["policyFingerprint"] == policy.fingerprint
    assert report["config"]["k"] == 2 and report["config"]["policyVersion"] == policy.version


def test_a_legacy_product_has_zero_pass_k_and_zero_spread():
    overall = _run("legacy", runs=2, k=2, personas=("dr_mehta",)).report["overall"]
    assert overall["passK"] == 0.0 and overall["runVariance"] == 0.0 and overall["seeds"] == 2 and overall["pass1"] == 0.0


def test_a_cap_leaves_the_interrupted_seed_out_of_pass_k():
    result = _run("good", runs=3, k=3, personas=None, max_model_calls=10)
    assert result.report["capExceeded"].startswith("model-call cap")
    complete = sum(1 for runs in _groups(result).values() if len(runs) == 3)
    assert result.report["overall"].get("seeds", 0) == complete


def test_the_same_seed_gives_the_same_trials():
    def fingerprint(result):
        return [
            (
                conv.seed,
                conv.mode,
                conv.final_state,
                conv.final_outcome,
                tuple((t.visitor_kind, t.visitor_text, t.choice_id) for t in conv.turns),
            )
            for conv, _ in result.items
        ]

    first, second = _run("good", runs=1, k=2, personas=("dr_mehta",)), _run("good", runs=1, k=2, personas=("dr_mehta",))
    assert fingerprint(first) == fingerprint(second)
    assert first.report["overall"]["passK"] == second.report["overall"]["passK"]


def test_k_must_be_at_least_one_and_the_policy_is_read_before_any_request(tmp_path):
    with pytest.raises(ValueError, match="k must be"):
        run_suite(RunConfig(base_url="http://127.0.0.1:1", secret=SECRET, k=0))
    no_protocol = tmp_path / "content.json"
    no_protocol.write_text(json.dumps({"fixed": {}}), encoding="utf-8")
    with pytest.raises(PolicyError):
        run_suite(RunConfig(base_url="http://127.0.0.1:1", secret=SECRET, k=1, content_path=str(no_protocol)))


def test_the_content_file_decides_the_policy_the_report_names(tmp_path):
    content = json.loads(DEFAULT_CONTENT_PATH.read_text(encoding="utf-8"))
    content["protocol"]["version"] = "9.9.9"
    path = tmp_path / "content.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    report = _run("good", runs=1, k=1, personas=("kiran",), content_path=str(path)).report
    assert report["policyVersion"] == "9.9.9" and report["config"]["policyVersion"] == "9.9.9"


def test_default_k_comes_from_the_persona_file_and_must_be_a_positive_integer(tmp_path):
    assert load_default_k() == 3
    path = tmp_path / "personas.yaml"
    path.write_text("reliability:\n  k: 5\npersonas: []\n", encoding="utf-8")
    assert load_default_k(path) == 5
    for body in ("personas: []\n", "reliability:\n  k: 0\n", "reliability:\n  k: true\n", "reliability:\n  k: two\n"):
        path.write_text(body, encoding="utf-8")
        with pytest.raises(PersonaError):
            load_default_k(path)
    assert RunConfig(base_url="http://127.0.0.1:1", secret=SECRET).k == 3


def _report(pass_k, variance, *, k=3, seeds=20, with_pass_k=True, policy="1.0.0"):
    persona = {"runs": 60, "taskSuccessRate": 1.0, "taskSuccessStd": 0.0}
    if with_pass_k:
        persona.update({"passK": pass_k, "runVariance": variance, "k": k, "seeds": seeds})
    return {
        "schema": REPORT_SCHEMA,
        "policyVersion": policy,
        "overall": {"policyViolationTotal": 0, "leadRate": 0.5},
        "personas": {"dr_mehta": persona},
    }


def _codes(messages):
    return {message.split(":", 1)[0] for message in messages}


def test_a_baseline_without_pass_k_only_warns():
    comparison = compare_reports(_report(None, None, with_pass_k=False), _report(0.9, 0.3))
    assert comparison.gate_passed and "PASSK_BASELINE_MISSING" in _codes(comparison.warnings)
    assert comparison.personas[0].pass_k_verdict == "unavailable"
    assert comparison.to_json()["warnings"] == comparison.warnings


def test_pass_k_regression_beyond_noise_fails_the_gate_and_within_noise_does_not():
    regressed = compare_reports(_report(0.9, 0.3), _report(0.2, 0.4))
    assert not regressed.gate_passed and "PASSK_REGRESSION" in _codes(regressed.reasons)
    assert regressed.personas[0].pass_k_verdict == "regressed" and regressed.personas[0].pass_k_delta == pytest.approx(-0.7)
    assert regressed.personas[0].pass_k_noise == pytest.approx(0.4)
    within = compare_reports(_report(0.9, 0.3), _report(0.6, 0.5))
    assert within.gate_passed and within.personas[0].pass_k_verdict == "unchanged"


def test_pass_k_improvement_is_reported_and_identical_reports_pass():
    improved = compare_reports(_report(0.2, 0.4), _report(0.9, 0.3))
    assert improved.gate_passed and improved.verdict == "IMPROVED"
    same = compare_reports(_report(0.9, 0.3), _report(0.9, 0.3))
    assert same.gate_passed and same.verdict == "PASS" and not same.warnings


def test_standard_error_basis_makes_the_pass_k_gate_stricter():
    base, new = _report(0.9, 0.3), _report(0.6, 0.5)
    assert compare_reports(base, new).gate_passed
    strict = compare_reports(base, new, noise_basis="stderr")
    assert not strict.gate_passed and strict.personas[0].pass_k_noise == pytest.approx(0.5 / 20**0.5, abs=1e-3)


def test_a_new_report_without_pass_k_fails_when_the_baseline_has_it():
    comparison = compare_reports(_report(0.9, 0.3), _report(None, None, with_pass_k=False))
    assert not comparison.gate_passed and "PASSK_MISSING" in _codes(comparison.reasons)
    assert comparison.personas[0].pass_k_verdict == "missing"


def test_a_different_k_or_policy_version_warns_and_does_not_gate():
    comparison = compare_reports(_report(0.9, 0.3, k=3), _report(0.1, 0.1, k=5, policy="2.0.0"))
    assert comparison.gate_passed
    assert {"PASSK_K_MISMATCH", "POLICY_VERSION_CHANGED"} <= _codes(comparison.warnings)
    text = render_markdown(comparison)
    assert "## Warnings" in text and "PASSK_K_MISMATCH" in text and "pass^k" in text


def test_load_report_accepts_the_previous_and_the_current_schema(tmp_path):
    for schema in (LEGACY_REPORT_SCHEMA, REPORT_SCHEMA):
        path = tmp_path / "report.json"
        path.write_text(json.dumps({**_report(0.9, 0.3), "schema": schema}), encoding="utf-8")
        assert load_report(path)["schema"] == schema
    path.write_text(json.dumps({**_report(0.9, 0.3), "schema": "visitor-simulation-report/2"}), encoding="utf-8")
    with pytest.raises(ReportError):
        load_report(path)


def test_cli_takes_k_and_rejects_values_below_one(monkeypatch, tmp_path):
    monkeypatch.setenv("VS_TEST_SECRET", SECRET)
    out = io.StringIO()
    rejected = main(
        ["run", "--base-url", "http://127.0.0.1:1", "--secret-env", "VS_TEST_SECRET", "--k", "0", "--output", str(tmp_path)],
        reporter=Reporter(out),
    )
    assert rejected == EXIT_USAGE and "--k" in out.getvalue()
    missing = main(
        [
            "run",
            "--base-url",
            "http://127.0.0.1:1",
            "--secret-env",
            "VS_TEST_SECRET",
            "--content",
            str(tmp_path / "missing.json"),
            "--output",
            str(tmp_path),
        ],
        reporter=Reporter(io.StringIO()),
    )
    assert missing == EXIT_USAGE
    out = io.StringIO()
    with FakeVisitorServer("good", SECRET) as server:
        code = main(
            [
                "run",
                "--base-url",
                server.base_url,
                "--secret-env",
                "VS_TEST_SECRET",
                "--runs",
                "1",
                "--k",
                "2",
                "--personas",
                "kiran",
                "--output",
                str(tmp_path / "out"),
            ],
            reporter=Reporter(out),
        )
    assert code == EXIT_OK and "pass^2:" in out.getvalue()
    report = json.loads((tmp_path / "out" / "report.json").read_text(encoding="utf-8"))
    assert report["config"]["k"] == 2 and report["overall"]["runs"] == 2 and report["overall"]["seeds"] == 1
    assert "pass^2" in (tmp_path / "out" / "summary.md").read_text(encoding="utf-8")
