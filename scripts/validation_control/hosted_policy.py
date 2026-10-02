#!/usr/bin/env python3
"""Reject prohibited host validation execution and selective Shadow enforcement."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml


SCHEMA = "waooaw.wc109-hosted-policy/v1"
GOVERNED_PATHS = (
    ".github/workflows/validation-plan.yaml",
    ".github/workflows/ci.yaml",
    ".github/workflows/code-quality.yaml",
    ".github/workflows/integration-tests.yaml",
    ".github/workflows/e2e-acceptance-tests.yaml",
    ".github/actions/run-validation-gate/action.yml",
    ".github/actions/record-shadow-comparison/action.yml",
)
COMMAND_BOUNDARY = r"(?:^|\n|&&|\|\||;)\s*"
PROHIBITED_COMMANDS = {
    "host-pytest": re.compile(COMMAND_BOUNDARY + r"(?:python\d*(?:\.\d+)?\s+-m\s+)?pytest\b", re.IGNORECASE),
    "host-dotnet-test": re.compile(COMMAND_BOUNDARY + r"dotnet\s+test\b", re.IGNORECASE),
    "host-jest": re.compile(COMMAND_BOUNDARY + r"(?:npx\s+)?jest\b", re.IGNORECASE),
    "host-playwright": re.compile(COMMAND_BOUNDARY + r"(?:npx\s+)?playwright\s+test\b", re.IGNORECASE),
    "host-virtual-environment": re.compile(
        COMMAND_BOUNDARY + r"(?:python\d*(?:\.\d+)?\s+-m\s+venv|virtualenv)\b",
        re.IGNORECASE,
    ),
    "host-package-install": re.compile(
        COMMAND_BOUNDARY
        + r"(?:(?:python\d*(?:\.\d+)?\s+-m\s+)?pip\s+install|npm\s+(?:ci|install)|pnpm\s+install|yarn\s+install)\b",
        re.IGNORECASE,
    ),
}


def _run_commands(value: Any) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "run" and isinstance(child, str):
                commands.append(child)
            else:
                commands.extend(_run_commands(child))
    elif isinstance(value, list):
        for child in value:
            commands.extend(_run_commands(child))
    return commands


def validate_hosted_policy(repository: Path, governed_paths: tuple[str, ...] = GOVERNED_PATHS) -> list[str]:
    violations: list[str] = []
    sources: dict[str, str] = {}
    for relative in governed_paths:
        path = repository / relative
        if not path.is_file():
            violations.append(f"HOSTED_POLICY_INPUT_MISSING:{relative}")
            continue
        source = path.read_text(encoding="utf-8")
        sources[relative] = source
        document = yaml.safe_load(source)
        if not isinstance(document, dict):
            violations.append(f"HOSTED_POLICY_YAML_INVALID:{relative}")
            continue
        for command in _run_commands(document):
            for policy_id, pattern in PROHIBITED_COMMANDS.items():
                if pattern.search(command):
                    violations.append(f"HOSTED_COMMAND_PROHIBITED:{relative}:{policy_id}")

    if governed_paths == GOVERNED_PATHS:
        plan = sources.get(".github/workflows/validation-plan.yaml", "")
        ci = sources.get(".github/workflows/ci.yaml", "")
        quality = sources.get(".github/workflows/code-quality.yaml", "")
        gate_action = sources.get(".github/actions/run-validation-gate/action.yml", "")
        if "hosted-execution-plan.json" not in plan or "execution_gates" not in plan:
            violations.append("HOSTED_FULL_EXECUTION_PLAN_MISSING")
        if "validation-plan.outputs.selected_gates" in ci or "validation-plan.outputs.selected_gates" in quality:
            violations.append("SELECTIVE_SHADOW_ENFORCEMENT_DETECTED")
        if "github.event.pull_request.head.sha" not in ci or "github.event.pull_request.head.sha" not in quality:
            violations.append("HOSTED_EXACT_HEAD_BINDING_MISSING")
        if "wc109-execution.json" not in gate_action or "Retain exact gate execution evidence" not in gate_action:
            violations.append("HOSTED_GATE_EVIDENCE_PUBLICATION_MISSING")
    return violations


def write_result(path: Path, violations: list[str]) -> None:
    result = {"schema": SCHEMA, "passed": not violations, "violations": violations}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    violations = validate_hosted_policy(arguments.repository.resolve())
    write_result(arguments.output, violations)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
