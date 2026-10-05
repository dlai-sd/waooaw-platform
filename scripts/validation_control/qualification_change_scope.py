#!/usr/bin/env python3
"""Select expensive qualification work from the exact changed-file manifest."""

from __future__ import annotations

import argparse
import fnmatch
from dataclasses import dataclass
from pathlib import Path


SHARED_PATTERNS = (
    "architecture/reference/dockerfiles/**",
    "docker-compose*.yml",
    "pyproject.toml",
    "requirements*.txt",
    "scripts/validation_control/**",
    "validation/**",
)
DOTNET_MUTATION_PATTERNS = (
    "src/constitutional-engine/**",
    "tests/constitutional-engine.Tests/**",
)
PYTHON_MUTATION_PATTERNS = (
    "src/ai-runtime/**",
    "src/trust-layer/**",
    "tests/ai-runtime/**",
    "tests/trust-layer/**",
)
DOTNET_INTEGRATION_PATTERNS = (
    "architecture/reference/proto/**",
    "infrastructure/postgres/**",
    "src/business-platform/**",
    "tests/business-platform.Tests/**",
)
RELEASE_LANE_PATTERNS = {
    "tests": (
        "release/goal006/**",
        "tests/pipeline/test_goal006_*.py",
        "tests/pipeline/test_billing_ce_validator.py",
        "tests/pipeline/test_wc091_environment_readiness.py",
        "tests/test_wc012_dry_run.py",
    ),
    "postgres": (
        "infrastructure/postgres/**",
        "src/billing-engine/**",
        "tests/billing-engine/**",
        "scripts/test-wc059-postgres.sh",
    ),
    "demo_data": (
        "release/goal006/**",
        "scripts/run_wc091_demo_data_verification.sh",
        "tests/pipeline/test_wc091_environment_readiness.py",
    ),
    "simulator": (
        "infrastructure/recovery/**",
        "release/goal006/**",
        "scripts/goal006_release_simulator.py",
    ),
    "azure": (
        "infrastructure/azure/**",
        "release/goal006/**",
        "scripts/goal006_runner_execution.py",
        "scripts/goal006_verify_deployment.sh",
        "scripts/run_goal006_local_azure_verification.sh",
        "tests/fixtures/goal006_azure_emulator.py",
    ),
}
KNOWN_TOP_LEVELS = {
    ".github",
    "adr",
    "architecture",
    "avd",
    "blockers",
    "constitution",
    "goals",
    "infrastructure",
    "knowledge",
    "legal",
    "pmo",
    "prototypes",
    "release",
    "reviews",
    "scripts",
    "security",
    "simulation",
    "sprint-context",
    "src",
    "standards",
    "strategy",
    "tests",
    "web",
    "work-contracts",
}


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


@dataclass(frozen=True)
class QualificationScope:
    mutation_dotnet: bool
    mutation_python: bool
    integration_dotnet: bool
    release_lanes: tuple[str, ...]
    broadened: bool


def full_scope() -> QualificationScope:
    return QualificationScope(
        mutation_dotnet=True,
        mutation_python=True,
        integration_dotnet=True,
        release_lanes=tuple(RELEASE_LANE_PATTERNS),
        broadened=True,
    )


def scope_for_changes(changed_files: tuple[str, ...]) -> QualificationScope:
    if not changed_files or any(matches(path, SHARED_PATTERNS) for path in changed_files):
        return full_scope()
    if any("/" not in path or path.split("/", 1)[0] not in KNOWN_TOP_LEVELS for path in changed_files):
        return full_scope()
    return QualificationScope(
        mutation_dotnet=any(matches(path, DOTNET_MUTATION_PATTERNS) for path in changed_files),
        mutation_python=any(matches(path, PYTHON_MUTATION_PATTERNS) for path in changed_files),
        integration_dotnet=any(matches(path, DOTNET_INTEGRATION_PATTERNS) for path in changed_files),
        release_lanes=tuple(
            lane for lane, patterns in RELEASE_LANE_PATTERNS.items() if any(matches(path, patterns) for path in changed_files)
        ),
        broadened=False,
    )


def read_changed_files(path: str) -> tuple[str, ...]:
    if not path:
        return ()
    manifest = Path(path)
    if not manifest.is_file():
        return ()
    return tuple(line.strip() for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip())


def shell_output(gate: str, scope: QualificationScope) -> str:
    if gate == "release-qualification":
        selected = set(scope.release_lanes)
        lines = [f"RELEASE_SCOPE_BROADENED={'true' if scope.broadened else 'false'}"]
        lines.extend(f"RELEASE_RUN_{lane.upper()}={'true' if lane in selected else 'false'}" for lane in RELEASE_LANE_PATTERNS)
        return "\n".join(lines)
    applicable = {
        "mutation:dotnet": scope.mutation_dotnet,
        "mutation:python": scope.mutation_python,
        "integration:dotnet": scope.integration_dotnet,
    }[gate]
    return f"QUALIFICATION_GATE_APPLICABLE={'true' if applicable else 'false'}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        required=True,
        choices=("mutation:dotnet", "mutation:python", "integration:dotnet", "release-qualification"),
    )
    parser.add_argument("--changed-files", default="")
    arguments = parser.parse_args()
    scope = scope_for_changes(read_changed_files(arguments.changed_files))
    print(shell_output(arguments.gate, scope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
