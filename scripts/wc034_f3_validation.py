#!/usr/bin/env python3
"""Deterministic C-080 validation and evidence packaging for WC034-12."""

# Implements: work-contracts/WC-034-goal005-webportal-founder-admin.md §WC034-12
# Constitutional basis: C-059 (Implementation Traceability), C-065 (SDLC Separation), C-076 (Coverage), C-080 (Docker Test Isolation)

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_EVIDENCE_ROOT = REPO_ROOT / "web" / "test-results"
ACCEPTANCE_IDS = [
    "UX-CONV-01", "UX-CONV-02", "UX-CONV-03", "UX-CONV-04", "UX-CONV-05",
    "UX-CONV-06", "UX-CONV-07", "CCT-UX-HO-01", "CCT-UX-HO-02", "CCT-UX-HO-03",
    "CCT-UX-EF-01", "CCT-UX-EF-02", "UX-PWA-03", "UX-RES-01",
]


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]
    acceptance_ids: tuple[str, ...] = ()


DOCKER = ("docker", "compose")
MULTI_STACK = (*DOCKER, "--profile", "test", "run", "--rm", "test-runner")
PYTHON = (*DOCKER, "--profile", "test-python", "run", "--rm", "test-runner-python")

CHECKS = {
    "bp": Check(
        "BP conversation unit and coverage",
        (*MULTI_STACK, "dotnet", "test", "tests/business-platform.Tests/business-platform.Tests.csproj", "--filter", "FullyQualifiedName~Conversation", "--collect:XPlat Code Coverage"),
        ("CCT-UX-EF-01", "CCT-UX-EF-02", "CCT-UX-HO-02", "CCT-UX-HO-03"),
    ),
    "pr": Check(
        "PR conversation unit and coverage",
        (
            *PYTHON,
            "pytest",
            "tests/professional-runtime/",
            "-q",
            "--cov=professional_runtime_main",
            "--cov=constitutional_gateway",
            "--cov=routers.conversation_execution",
            "--cov=routers.conversation_models",
            "--cov=routers.emergency_stop",
            "--cov=workflows.conversation_execution_workflow",
            "--cov-report=term-missing",
        ),
        ("UX-CONV-03", "UX-CONV-04", "CCT-UX-HO-02"),
    ),
    "web-coverage": Check(
        "Web unit coverage",
        (*MULTI_STACK, "pnpm", "--dir", "web", "test:coverage"),
        tuple(ACCEPTANCE_IDS),
    ),
    "web-lint": Check("Web lint", (*MULTI_STACK, "pnpm", "--dir", "web", "lint")),
    "web-build": Check("Web production build", (*MULTI_STACK, "pnpm", "--dir", "web", "build")),
    "static": Check(
        "WC034 F3 constitutional static contracts",
        (*PYTHON, "pytest", "tests/constitutional/test_wc034_f3_cross_stack_contract.py", "-q"),
        ("CCT-UX-HO-02", "CCT-UX-EF-01", "CCT-UX-EF-02"),
    ),
    "browser": Check(
        "Fixture-backed Chromium compact and expanded acceptance",
        (*MULTI_STACK, "pnpm", "--dir", "web", "exec", "playwright", "test", "tests/e2e/f3-conversation-acceptance.spec.ts", "--project=chromium-expanded", "--project=chromium-compact-360"),
        tuple(ACCEPTANCE_IDS),
    ),
}


def parse_counts(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in ("passed", "failed", "skipped"):
        matches = re.findall(rf"(\d+)\s+{label}", output, flags=re.IGNORECASE)
        if matches:
            counts[label] = int(matches[-1])
    vstest = re.search(
        r"Failed:\s*(\d+),\s*Passed:\s*(\d+),\s*Skipped:\s*(\d+),\s*Total:\s*(\d+)",
        output,
        flags=re.IGNORECASE,
    )
    if vstest:
        counts.update(
            failed=int(vstest.group(1)),
            passed=int(vstest.group(2)),
            skipped=int(vstest.group(3)),
            total=int(vstest.group(4)),
        )
    jest = re.search(r"Tests:\s+(?:(\d+) failed,\s+)?(\d+) passed,\s+(\d+) total", output)
    if jest:
        counts.update(failed=int(jest.group(1) or 0), passed=int(jest.group(2)), total=int(jest.group(3)))
    return counts


def run_check(key: str, check: Check, dry_run: bool) -> dict[str, object]:
    result: dict[str, object] = {
        "key": key,
        "name": check.name,
        "command": list(check.command),
        "acceptance_ids": list(check.acceptance_ids),
        "fixture_backed": key == "browser",
        "live_service_integration": False,
    }
    if dry_run:
        result["status"] = "DRY_RUN"
        return result

    started = time.monotonic()
    # Every argv tuple comes from immutable CHECKS; selection never accepts executable or argument input.
    completed = subprocess.run(  # noqa: S603
        check.command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    combined = f"{completed.stdout}\n{completed.stderr}".strip()
    result.update(
        status="PASS" if completed.returncode == 0 else "FAIL",
        return_code=completed.returncode,
        duration_seconds=round(time.monotonic() - started, 3),
        counts=parse_counts(combined),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    return result


def evidence_path(value: str) -> Path:
    path = (REPO_ROOT / value).resolve()
    if not path.is_relative_to(GENERATED_EVIDENCE_ROOT.resolve()):
        raise argparse.ArgumentTypeError("--output must be below ignored web/test-results/")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--select", nargs="+", choices=CHECKS, default=list(CHECKS), help="Run only named checks.")
    parser.add_argument("--dry-run", action="store_true", help="Print the exact safe command plan without executing it.")
    parser.add_argument("--output", type=evidence_path, help="Optionally write JSON below ignored web/test-results/.")
    args = parser.parse_args()

    selected = list(dict.fromkeys(args.select))
    report = {
        "schema_version": "1.0",
        "work_contract_task": "WC034-12",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safe_mode": {"deployment": False, "provider_activation": False, "external_triggers": False},
        "browser_evidence": "fixture-backed production-build integration; not live BP/PR deployment integration",
        "acceptance_ids": ACCEPTANCE_IDS,
        "results": [run_check(key, CHECKS[key], args.dry_run) for key in selected],
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{rendered}\n", encoding="utf-8")

    return 1 if any(result.get("status") == "FAIL" for result in report["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())