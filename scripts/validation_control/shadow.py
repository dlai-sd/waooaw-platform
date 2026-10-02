"""Compare WC-102 Shadow selections with authoritative full-validation outcomes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validation_policy import classify_paths, compare_shadow  # noqa: E402


GITHUB_RESULTS = {
    "success": "PASS",
    "failure": "FAIL",
    "cancelled": "CANCELLED",
    "skipped": "BLOCKED",
}


def build_hosted_execution_plan(
    catalog: dict[str, Any],
    selection: dict[str, Any],
) -> dict[str, Any]:
    selected_gates = selection.get("selected_gates")
    if not isinstance(selected_gates, list) or not all(isinstance(gate, str) for gate in selected_gates):
        raise ValueError("selection selected_gates must be a string list")
    mode = catalog.get("mode")
    if mode == "shadow":
        if selection.get("authoritative") is not False or selection.get("mode") != "shadow":
            raise ValueError("Shadow execution requires a non-authoritative Shadow selection")
        execution = classify_paths(
            catalog,
            [],
            base_sha=str(selection.get("base_sha", "")),
            head_sha=str(selection.get("head_sha", "")),
            event="push",
        )
    elif mode == "enforced":
        if selection.get("authoritative") is not True:
            raise ValueError("enforced execution requires an authoritative selection")
        execution = selection
    else:
        raise ValueError(f"unsupported catalog mode: {mode}")

    return {
        "schema": "waooaw.wc109-hosted-execution-plan/v1",
        "catalog_mode": mode,
        "base_sha": selection.get("base_sha"),
        "head_sha": selection.get("head_sha"),
        "shadow_selected_gates": selected_gates,
        "execution_gates": execution["selected_gates"],
        "required_runners": execution["required_runners"],
        "service_build_matrix": execution["service_build_matrix"],
        "dotnet_test_matrix": execution["dotnet_test_matrix"],
        "python_test_matrix": execution["python_test_matrix"],
        "dotnet_quality_matrix": execution["dotnet_quality_matrix"],
        "python_quality_matrix": execution["python_quality_matrix"],
        "release_required": "release-qualification" in execution["selected_gates"],
        "full_ci_authoritative": True,
        "selective_enforcement": mode == "enforced",
    }


def build_shadow_record(
    change_class: str,
    selection: dict[str, Any],
    full_gate_results: dict[str, str],
) -> dict[str, Any]:
    selected_gates = selection.get("selected_gates")
    if not isinstance(selected_gates, list) or not all(isinstance(gate, str) for gate in selected_gates):
        raise ValueError("selection selected_gates must be a string list")
    if selection.get("authoritative") is not False or selection.get("mode") != "shadow":
        raise ValueError("shadow comparison requires a non-authoritative Shadow selection")
    allowed_results = {"PASS", "FAIL", "BLOCKED", "CANCELLED"}
    if not full_gate_results or any(result not in allowed_results for result in full_gate_results.values()):
        raise ValueError("full gate results must contain supported authoritative outcomes")

    failed_gates = sorted(gate for gate, result in full_gate_results.items() if result != "PASS")
    comparison = compare_shadow(selected_gates, failed_gates)
    return {
        "schema": "waooaw.wc102-shadow-comparison/v1",
        "change_class": change_class,
        "base_sha": selection.get("base_sha"),
        "head_sha": selection.get("head_sha"),
        "selected_gates": selected_gates,
        "full_gate_results": full_gate_results,
        "false_negatives": comparison["false_negatives"],
        "passed": comparison["passed"],
        "authoritative_source": "full-validation",
        "selective_enforcement": False,
    }


def build_hosted_shadow_record(
    change_class: str,
    selection: dict[str, Any],
    execution_root: Path,
    external_results: dict[str, str],
    expected_gates: list[str],
    head_sha: str,
) -> dict[str, Any]:
    if len(head_sha) != 40 or any(character not in "0123456789abcdef" for character in head_sha):
        raise ValueError("head_sha must be a full hexadecimal commit")
    if not expected_gates or len(expected_gates) != len(set(expected_gates)):
        raise ValueError("expected_gates must be a nonempty unique list")
    results: dict[str, str] = {}
    evidence_files: dict[str, str] = {}
    for path in sorted(execution_root.rglob("wc109-execution.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        gate_id = record.get("gate_id")
        if gate_id not in expected_gates or record.get("head_sha") != head_sha:
            continue
        result = record.get("result")
        if result not in {"PASS", "FAIL", "BLOCKED", "CANCELLED"}:
            raise ValueError(f"unsupported execution result for {gate_id}: {result}")
        if gate_id in results and results[gate_id] != result:
            raise ValueError(f"conflicting exact-head results for {gate_id}")
        results[gate_id] = result
        evidence_files[gate_id] = str(path)

    for gate_id, github_result in external_results.items():
        if gate_id not in expected_gates:
            raise ValueError(f"unexpected external gate result: {gate_id}")
        normalized = GITHUB_RESULTS.get(github_result)
        if normalized is None:
            raise ValueError(f"unsupported GitHub job result for {gate_id}: {github_result}")
        if gate_id in results and results[gate_id] != normalized:
            raise ValueError(f"conflicting catalog and external results for {gate_id}")
        results[gate_id] = normalized

    missing = sorted(set(expected_gates) - set(results))
    results.update({gate_id: "BLOCKED" for gate_id in missing})
    record = build_shadow_record(change_class, selection, results)
    record.update(
        {
            "schema": "waooaw.wc109-hosted-shadow-comparison/v1",
            "expected_gates": expected_gates,
            "missing_gate_results": missing,
            "execution_evidence": evidence_files,
            "exact_head": head_sha,
            "passed": record["passed"] and not missing,
            "evidence_disposition": "hosted-shadow",
        }
    )
    return record


def write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--catalog", type=Path, default=Path("validation/engineering-validation.yaml"))
    plan_parser.add_argument("--selection", type=Path, required=True)
    plan_parser.add_argument("--output", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--selection", type=Path, required=True)
    compare_parser.add_argument("--execution-root", type=Path, required=True)
    compare_parser.add_argument("--external-results", type=Path, required=True)
    compare_parser.add_argument("--expected-gate", action="append", required=True)
    compare_parser.add_argument("--head", required=True)
    compare_parser.add_argument("--change-class", required=True)
    compare_parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    if not isinstance(selection, dict):
        raise ValueError("selection root must be a mapping")
    if arguments.command == "plan":
        catalog = yaml.safe_load(arguments.catalog.read_text(encoding="utf-8"))
        if not isinstance(catalog, dict):
            raise ValueError("catalog root must be a mapping")
        result = build_hosted_execution_plan(catalog, selection)
    else:
        external_results = json.loads(arguments.external_results.read_text(encoding="utf-8"))
        if not isinstance(external_results, dict) or not all(
            isinstance(gate, str) and isinstance(result, str) for gate, result in external_results.items()
        ):
            raise ValueError("external results must be a string mapping")
        result = build_hosted_shadow_record(
            arguments.change_class,
            selection,
            arguments.execution_root,
            external_results,
            arguments.expected_gate,
            arguments.head,
        )
    write_json(arguments.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
