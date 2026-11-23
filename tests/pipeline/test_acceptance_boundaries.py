# Implements: validation/acceptance/{agents,rollup.v1,exploratory-policy,promotion-policy}.yaml and reserved/prod.yaml; adr/ADR-056-acceptance-evidence-as-a-promotion-input.md
# Constitutional basis: C-059 (Implementation Traceability), C-065 (Separation of Duties)
from __future__ import annotations

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import acceptance_promotion_evaluator as evaluator  # noqa: E402
import acceptance_static_gates as gates  # noqa: E402


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    for relative in (
        "validation/acceptance",
        ".github/workflows/customer-journey-acceptance.yaml",
        "tests/journey-acceptance",
        str(gates.GOAL_005),
        str(gates.GAP_REGISTER),
        str(gates.DRIVERS),
    ):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    (tmp_path / "work-contracts").mkdir()
    for ledger in (ROOT / "work-contracts").glob("*-requirements.yaml"):
        shutil.copy2(ledger, tmp_path / "work-contracts" / ledger.name)
    return tmp_path


def _edit(path: Path, change) -> None:  # noqa: ANN001
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_the_repository_passes_with_all_boundaries_in_place() -> None:
    assert gates.check(ROOT) == []


def test_a_plan_may_test_only_a_registered_active_agent(repo: Path) -> None:
    plan_path = repo / gates.PLANS / "slice-2-publish.v1.yaml"
    _edit(plan_path, lambda plan: plan.update(agent_under_test="trading-agent"))
    assert any("trading-agent" in v and "RESERVED" in v for v in gates.check(repo))
    _edit(plan_path, lambda plan: plan.update(agent_under_test="unknown-agent"))
    assert any("unknown-agent" in v and "not in agents.yaml" in v for v in gates.check(repo))
    registry = repo / gates.ACCEPTANCE / "agents.yaml"
    _edit(registry, lambda document: document["agents"]["tutor-agent"].pop("reason"))
    assert any("tutor-agent is not active and gives no reason" in v for v in gates.check(repo))


def test_a_spec_may_not_hard_code_an_agent_name(repo: Path) -> None:
    (repo / "tests/journey-acceptance/specs/bad.ts").write_text('const OFFER = /digital marketing/i;\n', encoding="utf-8")
    assert any("hard-codes the agent digital-marketing-agent" in v for v in gates.check(repo))
    (repo / "tests/journey-acceptance/specs/bad.ts").write_text("// digital marketing is only mentioned in a comment\n", encoding="utf-8")
    assert not any("hard-codes" in v for v in gates.check(repo))


def test_compiled_plan_carries_the_agent_the_specs_look_for(repo: Path, tmp_path: Path) -> None:
    import json

    gates.compile_outputs(repo, "slice-3-hire-and-selection", "demo", tmp_path / "out")
    plan = json.loads((tmp_path / "out/plan.json").read_text(encoding="utf-8"))
    assert plan["agent"] == {"id": "digital-marketing-agent", "display_name": "Digital Marketing", "offer_pattern": "digital marketing"}
    assert json.loads((tmp_path / "out/rollup-map.json").read_text(encoding="utf-8"))["requirement"] == "WC107-R019"


def test_production_is_recorded_as_never_runnable(repo: Path) -> None:
    reserved = repo / gates.ACCEPTANCE / "reserved/prod.yaml"
    _edit(reserved, lambda document: document.update(runnable=True))
    assert any("must say runnable: false" in v for v in gates.check(repo))
    _edit(reserved, lambda document: document.update(runnable=False, prerequisites=[]))
    assert any("lists no prerequisites" in v for v in gates.check(repo))
    reserved.unlink()
    assert any("Production boundary is not recorded" in v for v in gates.check(repo))
    shutil.copy2(ROOT / gates.ACCEPTANCE / "reserved/prod.yaml", reserved)
    shutil.copy2(reserved, repo / gates.ENVIRONMENTS / "prod.yaml")
    assert any("also has a runnable profile" in v for v in gates.check(repo))
    (repo / gates.ENVIRONMENTS / "prod.yaml").unlink()
    workflow = repo / gates.WORKFLOW
    workflow.write_text(workflow.read_text(encoding="utf-8").replace("options: [demo]", "options: [demo, prod]"), encoding="utf-8")
    assert any("offers the reserved environment prod" in v for v in gates.check(repo))


def test_the_exploratory_companion_and_promotion_policy_stay_closed(repo: Path) -> None:
    _edit(repo / gates.ACCEPTANCE / "exploratory-policy.yaml", lambda document: document.update(enabled=True))
    assert any("disabled and non-deciding" in v for v in gates.check(repo))
    _edit(repo / gates.ACCEPTANCE / "exploratory-policy.yaml", lambda document: document.update(enabled=False, limits={"max_model_calls_per_run": 3}))
    assert any("non-zero model budget" in v for v in gates.check(repo))
    _edit(repo / gates.ACCEPTANCE / "promotion-policy.yaml", lambda document: document.update(enforced=True))
    assert any("promotion policy is enforced" in v for v in gates.check(repo))


def test_nothing_may_reference_the_promotion_evaluator(repo: Path) -> None:
    (repo / "scripts").mkdir()
    (repo / "scripts/release.sh").write_text("python scripts/acceptance_promotion_evaluator.py --report r.json\n", encoding="utf-8")
    assert any("scripts/release.sh references the promotion evaluator" in v for v in gates.check(repo))
    (repo / "scripts/release.sh").unlink()
    (repo / ".github/workflows/promote.yaml").write_text("steps: [validation/acceptance/promotion-policy.yaml]\n", encoding="utf-8")
    assert any(".github/workflows/promote.yaml references the promotion evaluator" in v for v in gates.check(repo))


def test_the_rollup_names_only_existing_steps_and_explains_empty_journeys(repo: Path) -> None:
    rollup = repo / gates.ACCEPTANCE / "rollup.v1.yaml"
    _edit(rollup, lambda document: document["journeys"][0].update(steps=["S77"]))
    assert any("cites step S77, which is in no plan" in v for v in gates.check(repo))
    _edit(rollup, lambda document: document["journeys"][1].pop("reason"))
    assert any("registration has no steps and no reason" in v for v in gates.check(repo))
    _edit(rollup, lambda document: document.update(devices=["desktop"]))
    assert any("desktop and mobile" in v for v in gates.check(repo))


POLICY = yaml.safe_load((ROOT / "validation/acceptance/promotion-policy.yaml").read_text(encoding="utf-8"))
NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def _report(**changes: object) -> dict:
    report = {
        "verdict": "PASS",
        "candidate": {"finished_at": "2026-11-23T11:00:00Z"},
        "steps": [{"stepId": "S1", "verdict": "PASS"}],
    }
    report.update(changes)
    return report


def test_a_clean_fresh_report_with_a_passing_rollup_is_eligible_but_not_authority() -> None:
    result = evaluator.evaluate(_report(), {"requirement": "WC107-R019", "status": "PASS"}, POLICY, NOW)
    assert result["decision"] == "ELIGIBLE"
    assert result["enforced"] is False
    assert "Founder approval is still required" in result["authority"]


def test_every_policy_rule_gives_its_own_reason() -> None:
    steps = [{"verdict": "NOT-WITNESSED"}, {"verdict": "BLOCKED-BY-FLAG"}, {"verdict": "FLAKY"}]
    stale = {"finished_at": "2026-11-20T11:00:00Z"}
    result = evaluator.evaluate(_report(verdict="FAIL", steps=steps, candidate=stale), {"requirement": "WC107-R019", "status": "OPEN"}, POLICY, NOW)
    assert result["decision"] == "NOT_ELIGIBLE"
    assert len(result["reasons"]) == 6
    assert any("older than the policy allows" in reason for reason in result["reasons"])
    assert evaluator.evaluate(_report(candidate={}), None, POLICY, NOW)["reasons"][-2:] == [
        "the report is missing a finish time or is older than the policy allows",
        "no WC107-R019 rollup was supplied",
    ]


def test_the_evaluator_command_prints_a_decision_and_exits_by_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import json

    report = tmp_path / "report.json"
    report.write_text(json.dumps(_report(candidate={"finished_at": datetime.now(UTC).isoformat()})), encoding="utf-8")
    rollup = tmp_path / "rollup.json"
    rollup.write_text(json.dumps({"requirement": "WC107-R019", "status": "PASS"}), encoding="utf-8")
    policy = ROOT / "validation/acceptance/promotion-policy.yaml"
    assert evaluator.main(["--report", str(report), "--rollup", str(rollup), "--policy", str(policy)]) == 0
    assert '"decision": "ELIGIBLE"' in capsys.readouterr().out
    assert evaluator.main(["--report", str(report), "--policy", str(policy)]) == 1
