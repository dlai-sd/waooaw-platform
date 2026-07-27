#!/usr/bin/env python3
"""
fail_fast_gate.py

Generic local fail-fast gate for autonomous sprint runs.
Use for any sprint/work contract, then prove with a concrete sprint such as WC-012.

Checks:
- SPRINT_STATE_MACHINE parse + gate sanity
- Work contract resolution for requested sprint
- Required environment variables
- Core toolchain presence
- Runner integrity probe
- Branch freshness on clean start (READY + tasks_done empty)

Exit codes:
  0 = all gates passed
  1 = one or more blocking gates failed
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
PROJECT_STATE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
WC_DIR = REPO_ROOT / "work-contracts"


@dataclass
class GateResult:
    name: str
    passed: bool
    severity: str
    detail: str


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def parse_state() -> dict[str, Any]:
    content = PROJECT_STATE.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```", content, re.DOTALL)
    if not m:
        raise ValueError("SPRINT_STATE_MACHINE block not found")

    state: dict[str, Any] = {}
    def _strip_inline_comment(raw: str) -> str:
        in_single = False
        in_double = False
        out: list[str] = []
        for ch in raw:
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                break
            out.append(ch)
        return "".join(out).rstrip()

    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = _strip_inline_comment(value.strip())
        if value.startswith("[") and value.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in value[1:-1].split(",") if x.strip()]
            state[key] = items
        elif value.lower() in {"true", "false"}:
            state[key] = value.lower() == "true"
        elif value.isdigit():
            state[key] = int(value)
        else:
            state[key] = value.strip('"').strip("'")

    # Parse block list format used by tasks_remaining/tasks_done
    for list_key in ("tasks_remaining", "tasks_done"):
        block = re.search(rf"^{list_key}:\s*\n((?:\s*-\s*\S+\s*\n)+)", m.group(1), re.MULTILINE)
        if block:
            state[list_key] = [x.strip() for x in re.findall(r"-\s*(\S+)", block.group(1))]
        else:
            state.setdefault(list_key, [])

    return state


def find_wc_file(sprint: str) -> Path | None:
    m = re.match(r"^WC-?(\d{1,3})$", sprint.strip(), re.IGNORECASE)
    if not m:
        return None
    n = m.group(1).zfill(3)
    matches = list(WC_DIR.glob(f"WC-{n}-*.md"))
    return matches[0] if matches else None


def check_env(required: list[str]) -> list[GateResult]:
    out: list[GateResult] = []
    for var in required:
        present = bool(os.environ.get(var, "").strip())
        out.append(
            GateResult(
                name=f"env:{var}",
                passed=present,
                severity="BLOCKER",
                detail="present" if present else "missing",
            )
        )
    return out


def check_tools(tools: list[str]) -> list[GateResult]:
    out: list[GateResult] = []
    for tool in tools:
        found = shutil.which(tool) is not None
        out.append(
            GateResult(
                name=f"tool:{tool}",
                passed=found,
                severity="BLOCKER",
                detail="available" if found else "not found on PATH",
            )
        )
    return out


def check_runner_integrity() -> GateResult:
    proc = run([sys.executable, "scripts/runner_integrity_check.py"])
    if proc.returncode == 0:
        return GateResult("runner_integrity", True, "BLOCKER", "PASS")
    detail = (proc.stdout + "\n" + proc.stderr).strip()[:400]
    return GateResult("runner_integrity", False, "BLOCKER", detail)


def check_branch_freshness(state: dict[str, Any], sprint: str) -> GateResult:
    """
    Fail early if this looks like a clean start but sprint branch is stale vs main.
    """
    branch = state.get("branch", f"ib/009/{sprint.lower()}")
    sprint_status = str(state.get("sprint_status", "")).upper()
    tasks_done = state.get("tasks_done", []) or []
    is_clean_start = sprint_status == "READY" and len(tasks_done) == 0

    if not is_clean_start:
        return GateResult("branch_freshness", True, "INFO", "not a clean-start; freshness check skipped")

    fetch_main = run(["git", "fetch", "origin", "main"])
    if fetch_main.returncode != 0:
        return GateResult("branch_freshness", False, "BLOCKER", "cannot fetch origin/main")

    ls_remote = run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch])
    if ls_remote.returncode != 0:
        return GateResult("branch_freshness", True, "INFO", f"remote branch {branch} not present (fresh creation expected)")

    rev_main = run(["git", "rev-parse", "origin/main"])
    if rev_main.returncode != 0:
        return GateResult("branch_freshness", False, "BLOCKER", "cannot resolve origin/main commit")
    main_sha = rev_main.stdout.strip()

    contains = run(["git", "branch", "-r", "--contains", main_sha, f"origin/{branch}"])
    includes_main = contains.returncode == 0 and f"origin/{branch}" in contains.stdout
    if includes_main:
        return GateResult("branch_freshness", True, "BLOCKER", f"origin/{branch} includes latest origin/main")

    return GateResult(
        "branch_freshness",
        False,
        "BLOCKER",
        f"origin/{branch} is stale vs origin/main on clean-start; delete/reset branch before run",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic fail-fast gate for autonomous sprint runs")
    parser.add_argument("--sprint", default="", help="Sprint ID, e.g. WC-012 (defaults to current_sprint in state)")
    parser.add_argument("--work-contract", default="", help="Explicit work contract path")
    parser.add_argument("--require-llm-key", action="store_true", help="Require ANTHROPIC_API_KEY")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    results: list[GateResult] = []

    try:
        state = parse_state()
        results.append(GateResult("state_parse", True, "BLOCKER", "SPRINT_STATE_MACHINE parsed"))
    except Exception as exc:
        results.append(GateResult("state_parse", False, "BLOCKER", str(exc)))
        state = {}

    sprint = args.sprint.strip() or str(state.get("current_sprint", "")).strip()
    if not sprint:
        results.append(GateResult("sprint_selection", False, "BLOCKER", "no sprint provided and current_sprint missing"))
    else:
        results.append(GateResult("sprint_selection", True, "INFO", sprint))

    phase = str(state.get("platform_phase", "")).upper() if state else ""
    halt = bool(state.get("autonomous_halt", True)) if state else True
    if phase != "IMPLEMENTATION":
        results.append(GateResult("platform_phase", False, "BLOCKER", f"platform_phase={phase or 'UNKNOWN'}"))
    else:
        results.append(GateResult("platform_phase", True, "BLOCKER", "IMPLEMENTATION"))

    if halt:
        results.append(GateResult("autonomous_halt", False, "BLOCKER", "autonomous_halt=true"))
    else:
        results.append(GateResult("autonomous_halt", True, "BLOCKER", "autonomous_halt=false"))

    if args.work_contract:
        wc_path = REPO_ROOT / args.work_contract
    else:
        wc_path = find_wc_file(sprint) if sprint else None

    if wc_path and wc_path.exists():
        results.append(GateResult("work_contract", True, "BLOCKER", str(wc_path.relative_to(REPO_ROOT))))
    else:
        results.append(GateResult("work_contract", False, "BLOCKER", f"not found for sprint={sprint}"))

    env_required = ["GITHUB_REPO", "SPRINT"]
    if args.require_llm_key:
        env_required.append("ANTHROPIC_API_KEY")
    results.extend(check_env(env_required))

    results.extend(check_tools(["git", "python3", "dotnet", "gh"]))
    results.append(check_runner_integrity())
    if sprint:
        results.append(check_branch_freshness(state, sprint))

    blockers = [r for r in results if r.severity == "BLOCKER" and not r.passed]

    if args.json:
        print(json.dumps({
            "sprint": sprint,
            "blockers": len(blockers),
            "results": [r.__dict__ for r in results],
        }, indent=2))
    else:
        print("=" * 72)
        print("FAIL-FAST GATE")
        print("=" * 72)
        for r in results:
            mark = "PASS" if r.passed else "FAIL"
            print(f"[{mark}] {r.name:<24} ({r.severity}) {r.detail}")
        print("-" * 72)
        print(f"BLOCKERS: {len(blockers)}")

    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
