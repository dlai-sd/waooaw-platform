#!/usr/bin/env python3
"""Validate that WC-104 preserves the frozen authoritative gate baseline."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md section 6 WC104-R015
# Constitutional basis: C-059, C-065, C-071, C-076, C-080

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "waooaw.authoritative-gate-baseline/v1"
CATALOG_ACTION = "./.github/actions/run-validation-gate"


def workflow_catalog_gates(workflow: dict[str, Any]) -> set[str]:
    gates: set[str] = set()
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return gates
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        matrix = job.get("strategy", {}).get("matrix", {})
        if isinstance(matrix, dict):
            include = matrix.get("include", [])
            if isinstance(include, list):
                gates.update(row["gate"] for row in include if isinstance(row, dict) and isinstance(row.get("gate"), str))
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict) or step.get("uses") != CATALOG_ACTION:
                continue
            gate_id = step.get("with", {}).get("gate-id")
            if isinstance(gate_id, str) and "${{" not in gate_id:
                gates.add(gate_id)
    return gates


def _nested_value(document: dict[str, Any], path: list[str]) -> Any:
    current: Any = document
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def validate_gate_equivalence(repository: Path, baseline: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if baseline.get("schema") != SCHEMA:
        return ["BASELINE_SCHEMA_INVALID"]
    catalog_path = repository / "validation/engineering-validation.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        return ["CATALOG_INVALID"]
    catalog_gates = catalog.get("gates", {})
    workflows = baseline.get("workflows", {})
    if not isinstance(workflows, dict) or not isinstance(catalog_gates, dict):
        return ["BASELINE_INVENTORY_INVALID"]

    for relative, expected in workflows.items():
        if not isinstance(relative, str) or not isinstance(expected, dict):
            violations.append("BASELINE_WORKFLOW_INVALID")
            continue
        workflow = yaml.safe_load((repository / relative).read_text(encoding="utf-8"))
        if not isinstance(workflow, dict):
            violations.append(f"WORKFLOW_INVALID:{relative}")
            continue
        actual_gates = workflow_catalog_gates(workflow)
        expected_gates = set(expected.get("catalog_gates", []))
        for gate_id in sorted(expected_gates - actual_gates):
            violations.append(f"CATALOG_GATE_REMOVED:{relative}:{gate_id}")
        for gate_id in sorted(expected_gates - set(catalog_gates)):
            violations.append(f"CATALOG_GATE_UNDEFINED:{gate_id}")
        jobs = workflow.get("jobs", {})
        actual_jobs = set(jobs) if isinstance(jobs, dict) else set()
        for job_id in sorted(set(expected.get("external_jobs", [])) - actual_jobs):
            violations.append(f"EXTERNAL_GATE_REMOVED:{relative}:{job_id}")

    thresholds = baseline.get("thresholds", {})
    if not isinstance(thresholds, dict):
        violations.append("BASELINE_THRESHOLDS_INVALID")
    else:
        for relative, tokens in thresholds.items():
            content = (repository / relative).read_text(encoding="utf-8")
            for token in tokens if isinstance(tokens, list) else []:
                if token not in content:
                    violations.append(f"THRESHOLD_REDUCED:{relative}:{token}")

    actual_classes = {
        gate.get("evidence_class")
        for gate in catalog_gates.values()
        if isinstance(gate, dict) and isinstance(gate.get("evidence_class"), str)
    }
    for evidence_class in sorted(set(baseline.get("required_evidence_classes", [])) - actual_classes):
        violations.append(f"EVIDENCE_CLASS_REMOVED:{evidence_class}")

    flags = baseline.get("required_catalog_flags", {})
    if not isinstance(flags, dict):
        violations.append("BASELINE_FLAGS_INVALID")
    else:
        for key, expected in flags.items():
            if isinstance(expected, dict):
                for child, child_expected in expected.items():
                    if _nested_value(catalog, [key, child]) != child_expected:
                        violations.append(f"CATALOG_FLAG_CHANGED:{key}.{child}")
            elif catalog.get(key) != expected:
                violations.append(f"CATALOG_FLAG_CHANGED:{key}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("validation/authoritative-gate-baseline.yaml"),
    )
    arguments = parser.parse_args()
    baseline = yaml.safe_load(arguments.baseline.read_text(encoding="utf-8"))
    violations = validate_gate_equivalence(arguments.repository.resolve(), baseline)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
