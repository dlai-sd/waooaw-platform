# Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §9 F1-F5, F10, F17, F19, F20
# Constitutional basis: C-059 (Implementation Traceability), C-071 (Quality Obligation)
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import acceptance_static_gates as gates  # noqa: E402


def _copy(root: Path, relative: str) -> None:
    source = ROOT / relative
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


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
        _copy(tmp_path, relative)
    (tmp_path / "work-contracts").mkdir()
    for ledger in (ROOT / "work-contracts").glob("*-requirements.yaml"):
        shutil.copy2(ledger, tmp_path / "work-contracts" / ledger.name)
    return tmp_path


def _write_yaml(path: Path, document: object) -> None:
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _plan_path(repo: Path) -> Path:
    return repo / gates.PLANS / "slice-1-discover-to-connect.v1.yaml"


def test_repository_passes_every_static_acceptance_gate() -> None:
    assert gates.check(ROOT) == []


def test_workflow_is_manual_only_report_only_and_holds_no_credential() -> None:
    text = (ROOT / gates.WORKFLOW).read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert set(document[True]) == {"workflow_dispatch"}
    assert document["concurrency"]["group"].endswith("${{ inputs.environment }}")
    assert not [v for v in gates.workflow_violations(ROOT) if v.startswith("F2")]
    assert "${{ secrets." not in text


def test_a_push_trigger_a_secret_and_an_environment_branch_are_each_refused(repo: Path) -> None:
    path = repo / gates.WORKFLOW
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("on:\n  workflow_dispatch:", "on:\n  push:\n    branches: [main]\n  workflow_dispatch:"), encoding="utf-8")
    assert any(v.startswith("F1") and "workflow_dispatch" in v for v in gates.workflow_violations(repo))
    path.write_text(original + "\n      - run: echo ${{ secrets.AZURE_CLIENT_SECRET }}\n", encoding="utf-8")
    assert any(v.startswith("F2") and "AZURE_CLIENT_SECRET" in v for v in gates.workflow_violations(repo))
    path.write_text(original + "\n      - if: inputs.environment == 'demo'\n        run: true\n", encoding="utf-8")
    assert any(v.startswith("F3") for v in gates.workflow_violations(repo))
    path.write_text(original + "\n      - run: echo ${{ vars.PROVIDER_API_KEY }}\n", encoding="utf-8")
    assert any(v.startswith("F2") and "PROVIDER_API_KEY" in v for v in gates.workflow_violations(repo))


def test_the_environment_option_list_must_equal_the_profile_files(repo: Path) -> None:
    shutil.copy2(repo / gates.ENVIRONMENTS / "demo.yaml", repo / gates.ENVIRONMENTS / "uat.yaml")
    assert any(v.startswith("F3") and "uat" in v for v in gates.workflow_violations(repo))


def test_nothing_else_may_depend_on_the_acceptance_workflow(repo: Path) -> None:
    other = repo / ".github/workflows/release.yaml"
    other.write_text("name: x\non: push\njobs:\n  a:\n    uses: ./.github/workflows/customer-journey-acceptance.yaml\n", encoding="utf-8")
    assert any(v.startswith("F17") for v in gates.workflow_violations(repo))
    other.unlink()
    catalog = repo / "validation/required.yaml"
    catalog.write_text("required: [customer-journey-acceptance.yaml]\n", encoding="utf-8")
    assert any(v.startswith("F17") and "required.yaml" in v for v in gates.workflow_violations(repo))


def test_harness_code_may_not_branch_on_an_environment_name(repo: Path) -> None:
    (repo / "tests/journey-acceptance/lib/bad.ts").write_text('if (name === "demo") { run(); }\n', encoding="utf-8")
    assert any(v.startswith("F3") and "bad.ts" in v for v in gates.harness_violations(repo))
    (repo / "tests/journey-acceptance/lib/bad.ts").write_text('const mode = value === "other";\n', encoding="utf-8")
    assert gates.harness_violations(repo) == []


def test_a_claim_with_one_witness_needs_a_listed_exception(repo: Path) -> None:
    plan = yaml.safe_load(_plan_path(repo).read_text(encoding="utf-8"))
    plan["steps"][0]["claims"][0]["witnesses_required"] = ["W1"]
    assert any(v.startswith("F4") for v in gates.plan_violations(plan, gates.known_identifiers(repo)))
    plan["witness_exceptions"] = [{"claim": "S1-C1", "reason": "no customer-reachable route exists for this state"}]
    assert not any(v.startswith("F4") for v in gates.plan_violations(plan, gates.known_identifiers(repo)))


def test_a_step_without_identifiers_or_with_an_unknown_one_is_refused(repo: Path) -> None:
    plan = yaml.safe_load(_plan_path(repo).read_text(encoding="utf-8"))
    plan["steps"][0]["proves"] = {"gaps": ["PG-99"]}
    plan["steps"][1]["proves"] = {}
    violations = gates.plan_violations(plan, gates.known_identifiers(repo))
    assert any("PG-99" in v for v in violations)
    assert any(v.startswith("F5") and "cites no" in v for v in violations)


def test_plan_and_specs_must_agree_in_both_directions(repo: Path) -> None:
    plan = yaml.safe_load(_plan_path(repo).read_text(encoding="utf-8"))
    known = gates.known_identifiers(repo)
    steps = {step["id"] for step in plan["steps"]}
    declarations = [d for d in gates.spec_declarations(repo) if d["step"] in steps]
    assert gates.spec_violations(plan, declarations, known) == []
    missing = [d for d in declarations if d["step"] != "S1"]
    assert "F20 plan step S1 has no spec" in gates.spec_violations(plan, missing, known)
    ghost = [*declarations, {"file": "x.ts", "step": "S99", "covers": []}]
    assert any("S99" in v for v in gates.spec_violations(plan, ghost, known))
    unproven = [*declarations, {"file": "x.ts", "step": "S1", "covers": ["PG-16", "PG-99"]}]
    violations = gates.spec_violations(plan, unproven, known)
    assert any("PG-16" in v and "does not prove" in v for v in violations)
    assert any("PG-99" in v and "does not exist" in v for v in violations)


def test_the_coverage_ratchet_refuses_a_lower_floor_a_removed_cover_and_a_new_deferral(repo: Path) -> None:
    plan = yaml.safe_load(_plan_path(repo).read_text(encoding="utf-8"))
    declarations = gates.spec_declarations(repo)
    live_scope = yaml.safe_load((repo / gates.ACCEPTANCE / "live-scope.yaml").read_text(encoding="utf-8"))
    baseline = yaml.safe_load((repo / gates.ACCEPTANCE / "coverage-baseline.yaml").read_text(encoding="utf-8"))
    assert gates.coverage_violations(plan, declarations, live_scope, baseline, baseline) == []

    # A live-scope identifier without a spec and without a deferral fails the pull request.
    uncovered = {**live_scope, "requirements": [*live_scope["requirements"], "WC107-R002"]}
    assert any("WC107-R002" in v and "no spec" in v for v in gates.coverage_violations(plan, declarations, uncovered, baseline, baseline))

    # Removing specs lowers plan-step coverage and the accepted covered set.
    fewer = [d for d in declarations if d["step"] != "S1"]
    violations = gates.coverage_violations(plan, fewer, live_scope, baseline, baseline)
    assert any("below the floor" in v for v in violations)
    assert any("no longer is" in v for v in violations)

    # Editing the baseline downwards is caught against the base branch's baseline.
    lowered = {**baseline, "plan_step_floor": 0.5, "covered": baseline["covered"][:-1], "deferred": [*baseline["deferred"], "WC107-R002"]}
    violations = gates.coverage_violations(plan, declarations, live_scope, lowered, baseline)
    assert any("lowers the plan-step floor" in v for v in violations)
    assert any("removes" in v for v in violations)
    assert any("adds deferral WC107-R002" in v for v in violations)

    # A deferral must be in scope.
    stray = {**live_scope, "deferred": {**live_scope["deferred"], "PG-98": "not in scope"}}
    assert any("PG-98" in v and "not in the live scope" in v for v in gates.coverage_violations(plan, declarations, stray, baseline, baseline))


def test_a_deferral_not_accepted_in_the_baseline_is_refused(repo: Path) -> None:
    plan = yaml.safe_load(_plan_path(repo).read_text(encoding="utf-8"))
    declarations = gates.spec_declarations(repo)
    live_scope = yaml.safe_load((repo / gates.ACCEPTANCE / "live-scope.yaml").read_text(encoding="utf-8"))
    baseline = yaml.safe_load((repo / gates.ACCEPTANCE / "coverage-baseline.yaml").read_text(encoding="utf-8"))
    baseline["deferred"] = baseline["deferred"][1:]
    assert any("not accepted in coverage-baseline.yaml" in v for v in gates.coverage_violations(plan, declarations, live_scope, baseline, None))


def test_profile_schema_rejects_a_live_provider_and_a_non_synthetic_group(repo: Path) -> None:
    profile = yaml.safe_load((repo / gates.ENVIRONMENTS / "demo.yaml").read_text(encoding="utf-8"))
    profile["sandbox"]["razorpay_key_id_prefix"] = "rzp_live_"
    profile["keycloak"]["synthetic_group"] = "customers"
    violations = gates.schema_violations(profile, repo / gates.ACCEPTANCE / "environment.schema.json", "demo.yaml")
    assert any("razorpay_key_id_prefix" in v for v in violations)
    assert any("synthetic_group" in v for v in violations)


def test_check_reports_a_profile_that_names_an_unknown_journey(repo: Path) -> None:
    profile_path = repo / gates.ENVIRONMENTS / "demo.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["journeys"].append("slice-9")
    _write_yaml(profile_path, profile)
    assert any("slice-9" in v for v in gates.check(repo))


def test_the_committed_sample_report_validates_against_the_report_schema() -> None:
    schema = json.loads((ROOT / gates.ACCEPTANCE / "report.schema.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "tests/journey-acceptance/fixtures/sample-report.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(sample)) == []
    sample["verdict"] = "MAYBE"
    assert list(Draft202012Validator(schema).iter_errors(sample)) != []


def test_compile_writes_plan_and_profile_bound_to_their_digests(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "compiled"
    gates.compile_outputs(repo, "slice-1-discover-to-connect", "demo", out)
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    profile = json.loads((out / "profile.json").read_text(encoding="utf-8"))
    assert plan["planDigest"] == gates.digest(_plan_path(repo))
    assert profile["profile_digest"] == gates.digest(repo / gates.ENVIRONMENTS / "demo.yaml")
    assert "WC107-R009" in plan["liveScope"]
    with pytest.raises(SystemExit, match="no profile"):
        gates.compile_outputs(repo, "slice-1-discover-to-connect", "uat", out)
    profile_path = repo / gates.ENVIRONMENTS / "demo.yaml"
    document = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    document["journeys"] = []
    _write_yaml(profile_path, document)
    with pytest.raises(SystemExit):
        gates.compile_outputs(repo, "slice-1-discover-to-connect", "demo", out)


def test_main_runs_check_and_compile(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert gates.main(["check", "--repository-root", str(repo)]) == 0
    assert "passed" in capsys.readouterr().out
    assert gates.main(["compile", "--repository-root", str(repo), "--journey", "slice-1-discover-to-connect", "--environment", "demo", "--out", str(tmp_path / "o")]) == 0
    (repo / gates.WORKFLOW).write_text("on: push\n", encoding="utf-8")
    assert gates.main(["check", "--repository-root", str(repo)]) == 1
    assert "F1" in capsys.readouterr().err


def test_a_second_plan_may_not_reuse_a_step_id_and_a_spec_may_not_cite_a_step_in_no_plan(repo: Path) -> None:
    duplicate = yaml.safe_load((repo / gates.PLANS / "slice-2-publish.v1.yaml").read_text(encoding="utf-8"))
    duplicate["journey_id"] = "slice-3-copy"
    duplicate["steps"][0]["id"] = "S1"
    _write_yaml(repo / gates.PLANS / "slice-3-copy.v1.yaml", duplicate)
    assert any("S1" in v and "already used" in v for v in gates.check(repo))
    (repo / gates.PLANS / "slice-3-copy.v1.yaml").unlink()
    (repo / "tests/journey-acceptance/specs/ghost.spec.ts").write_text(
        'acceptanceStep("S99", { covers: ["PG-16"] }, async () => ({}));\n', encoding="utf-8"
    )
    assert any("S99" in v and "does not exist" in v for v in gates.check(repo))
