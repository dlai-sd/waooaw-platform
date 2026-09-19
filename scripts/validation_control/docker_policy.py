"""Enforce Docker-only, non-root validation workflow policy."""

# Implements: architecture/reference/docker-only-validation-strategy.md §5.7
# Constitutional basis: C-059, C-080

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


PROHIBITED_HOST_COMMANDS = (
    re.compile(r"^(?:python(?:3)? -m )?pytest(?:\s|$)"),
    re.compile(r"^dotnet (?:test|build|restore|list|csharpier|stryker)(?:\s|$)"),
    re.compile(r"^(?:pnpm|npm|npx)(?:\s|$)"),
    re.compile(r"^(?:ruff|mypy|bandit|sqlfluff|mutmut|pip-audit|schemathesis)(?:\s|$)"),
    re.compile(r"^python(?:3)? scripts/(?:seed-prompts|validate_|run_).*"),
)
PROHIBITED_ENVIRONMENT = re.compile(r"(?:python(?:3)? -m venv|virtualenv|\.venv/|/activate(?:\s|$))")
PROHIBITED_INSTALL = re.compile(r"^(?:pip(?:3)? install|python(?:3)? -m pip install|npm install|pnpm install)(?:\s|$)")
VALIDATION_WORKFLOWS = frozenset({"ci.yaml", "code-quality.yaml", "e2e-acceptance-tests.yaml", "integration-tests.yaml"})


def _workflow_commands(document: dict[str, Any]) -> list[tuple[str, str, str]]:
    commands: list[tuple[str, str, str]] = []
    jobs = document.get("jobs", {})
    if not isinstance(jobs, dict):
        return commands
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                commands.append((str(job_name), str(step.get("name", index)), step["run"]))
    return commands


def inspect_workflow(path: Path) -> list[str]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        problem = getattr(error, "problem_mark", None)
        line = problem.line + 1 if problem is not None else 0
        return [f"{path}:{line}: WORKFLOW_YAML_INVALID"]
    if not isinstance(loaded, dict):
        return [f"{path}: workflow root must be a mapping"]
    violations: list[str] = []
    for job, step, command in _workflow_commands(loaded):
        in_container_script = False
        container_command_continues = False
        for line_number, raw_line in enumerate(command.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if in_container_script:
                if line in {"'", '"'}:
                    in_container_script = False
                continue
            if container_command_continues:
                if "--user root" in line:
                    violations.append(f"{path}:{job}:{step}:{line_number}: ROOT_RUNNER_OVERRIDE")
                if re.search(r"\bsh -lc ['\"]$", line):
                    in_container_script = True
                    container_command_continues = False
                elif not line.endswith("\\"):
                    container_command_continues = False
                continue
            if re.match(r"^(?:if\s+)?docker compose\s+", line):
                if "--user root" in line:
                    violations.append(f"{path}:{job}:{step}:{line_number}: ROOT_RUNNER_OVERRIDE")
                if re.search(r"\brun\b.*\bsh -lc ['\"]$", line):
                    in_container_script = True
                elif line.endswith("\\"):
                    container_command_continues = True
                continue
            if line.startswith("docker ") or line.startswith("scripts/verify_runner_image.sh"):
                continue
            if "--user root" in line:
                violations.append(f"{path}:{job}:{step}:{line_number}: ROOT_RUNNER_OVERRIDE")
            if PROHIBITED_ENVIRONMENT.search(line):
                violations.append(f"{path}:{job}:{step}:{line_number}: VIRTUAL_ENVIRONMENT")
            if path.name in VALIDATION_WORKFLOWS and PROHIBITED_INSTALL.search(line):
                violations.append(f"{path}:{job}:{step}:{line_number}: HOST_TEST_INSTALL")
            if any(pattern.search(line) for pattern in PROHIBITED_HOST_COMMANDS):
                violations.append(f"{path}:{job}:{step}:{line_number}: HOST_TEST_COMMAND")
    return violations


def inspect_repository(repository: Path) -> list[str]:
    workflows = sorted((repository / ".github/workflows").glob("*.y*ml"))
    return [violation for workflow in workflows for violation in inspect_workflow(workflow)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    violations = inspect_repository(arguments.repository.resolve())
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1
    print("PASS: Docker-only workflow policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())