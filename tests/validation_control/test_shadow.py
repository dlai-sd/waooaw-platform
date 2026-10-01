"""WC102 Shadow selection comparison contracts."""

from pathlib import Path

import pytest
import yaml

from validation_control.shadow import build_hosted_execution_plan, build_hosted_shadow_record, build_shadow_record
from validation_policy import classify_paths


ROOT = Path(__file__).resolve().parents[2]


def load_catalog() -> dict[str, object]:
    return yaml.safe_load((ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("change_class", "path", "expected_gate"),
    [
        ("web-only", "web/app/page.tsx", "test-web"),
        ("business-platform", "src/business-platform/Program.cs", "test-dotnet:business-platform"),
        ("python-service", "src/professional-runtime/app.py", "test-python:professional-runtime"),
        ("shared-contract", "architecture/reference/proto/constitutional.proto", "spec-lint"),
        ("pipeline-global", ".github/workflows/ci.yaml", "test-python"),
    ],
)
def test_shadow_comparison_covers_representative_change_classes(change_class: str, path: str, expected_gate: str) -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, [path], base_sha="b" * 40, head_sha="c" * 40)
    full_results = {gate: "PASS" for gate in catalog["full_gates"]}
    full_results[expected_gate] = "FAIL"
    if expected_gate not in full_results:
        full_results[expected_gate] = "FAIL"

    record = build_shadow_record(change_class, selection, full_results)

    assert expected_gate in selection["selected_gates"]
    assert record["passed"] is True
    assert record["selective_enforcement"] is False


def test_shadow_comparison_records_omitted_full_ci_failure() -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="c" * 40)

    record = build_shadow_record("web-only", selection, {"test-web": "PASS", "test-dotnet": "FAIL"})

    assert record["passed"] is False
    assert record["false_negatives"] == ["test-dotnet"]


def test_shadow_comparison_rejects_authoritative_selection() -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"])
    selection["authoritative"] = True

    with pytest.raises(ValueError, match="non-authoritative Shadow"):
        build_shadow_record("web-only", selection, {"test-web": "PASS"})


def test_hosted_shadow_preserves_focused_observation_but_executes_full_inventory() -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="c" * 40)

    plan = build_hosted_execution_plan(catalog, selection)

    assert "test-web" in plan["shadow_selected_gates"]
    assert set(plan["execution_gates"]) == set(catalog["full_gates"])
    assert len(plan["service_build_matrix"]) == len(catalog["components"])
    assert {item["gate"] for item in plan["dotnet_test_matrix"]} == {
        "test-dotnet:constitutional-engine",
        "test-dotnet:business-platform",
    }
    assert plan["release_required"] is True
    assert plan["full_ci_authoritative"] is True
    assert plan["selective_enforcement"] is False


def test_hosted_shadow_rejects_authoritative_selection() -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"])
    selection["authoritative"] = True

    with pytest.raises(ValueError, match="non-authoritative Shadow"):
        build_hosted_execution_plan(catalog, selection)


def test_hosted_workflows_execute_plan_instead_of_shadow_selection() -> None:
    validation_plan = (ROOT / ".github/workflows/validation-plan.yaml").read_text(encoding="utf-8")
    ci_workflow = (ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    quality_workflow = (ROOT / ".github/workflows/code-quality.yaml").read_text(encoding="utf-8")

    assert "scripts/validation_control/shadow.py" in validation_plan
    assert "execution_gates:" in validation_plan
    assert "hosted-execution-plan.json" in validation_plan
    assert "validation-plan.outputs.selected_gates" not in ci_workflow
    assert "validation-plan.outputs.selected_gates" not in quality_workflow
    assert "validation-plan.outputs.execution_gates" in ci_workflow
    assert "validation-plan.outputs.execution_gates" in quality_workflow
    assert "record-shadow-comparison" in ci_workflow
    assert "record-shadow-comparison" in quality_workflow
    assert "wc109-shadow-plan-${{ github.run_id }}" in validation_plan


def test_catalog_action_retains_exact_gate_evidence_before_enforcement() -> None:
    action = (ROOT / ".github/actions/run-validation-gate/action.yml").read_text(encoding="utf-8")

    assert "wc109-gate-${GITHUB_JOB}-${artifact_gate}" in action
    assert "${{ steps.gate.outputs.output_directory }}/wc109-execution.json" in action
    assert action.index("Retain exact gate execution evidence") < action.index("Enforce catalog command result")


def test_shadow_comparison_action_executes_analysis_inside_immutable_runner() -> None:
    action = (ROOT / ".github/actions/record-shadow-comparison/action.yml").read_text(encoding="utf-8")

    assert "actions/download-artifact@v4" in action
    assert "./.github/actions/use-validation-runner" in action
    assert "docker compose --profile test run --rm --no-deps test-runner" in action
    assert "python scripts/validation_control/shadow.py compare" in action


def test_hosted_shadow_collects_exact_gate_results_and_external_jobs(tmp_path: Path) -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="c" * 40)
    gate_directory = tmp_path / "gate"
    gate_directory.mkdir()
    (gate_directory / "wc109-execution.json").write_text(
        '{"gate_id":"test-web","head_sha":"' + "c" * 40 + '","result":"PASS"}',
        encoding="utf-8",
    )

    record = build_hosted_shadow_record(
        "ci",
        selection,
        tmp_path,
        {"secrets": "success"},
        ["test-web", "secrets"],
        "c" * 40,
    )

    assert record["passed"] is True
    assert record["missing_gate_results"] == []
    assert record["full_gate_results"] == {"test-web": "PASS", "secrets": "PASS"}


def test_hosted_shadow_fails_closed_for_missing_result(tmp_path: Path) -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="c" * 40)

    record = build_hosted_shadow_record("ci", selection, tmp_path, {}, ["test-web"], "c" * 40)

    assert record["passed"] is False
    assert record["missing_gate_results"] == ["test-web"]


def test_hosted_shadow_records_unselected_exact_head_failure(tmp_path: Path) -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="c" * 40)
    gate_directory = tmp_path / "gate"
    gate_directory.mkdir()
    (gate_directory / "wc109-execution.json").write_text(
        '{"gate_id":"test-dotnet:business-platform","head_sha":"' + "c" * 40 + '","result":"FAIL"}',
        encoding="utf-8",
    )

    record = build_hosted_shadow_record(
        "ci",
        selection,
        tmp_path,
        {},
        ["test-dotnet:business-platform"],
        "c" * 40,
    )

    assert record["passed"] is False
    assert record["false_negatives"] == ["test-dotnet:business-platform"]
