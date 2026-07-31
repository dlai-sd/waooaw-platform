#!/usr/bin/env python3
"""
check_c086_gate.py — C-086 Pre-Execution Simulation Gate

# Implements: architecture/reference/pipeline/dependency-graph-task-decomposition.md §8
# constitutional_basis: C-086 (Pre-Execution Simulation Obligation — RATIFIED 2026-07-24)
# constitutional_basis: C-059 (Traceability)
# office: Platform IT Expert (WC-019)
# IB: IB-021

Called by the pre-flight job in autonomous-sprint.yaml before any LLM call.
Checks that every decomposed sprint task has a SIM-PL-002 simulation with PASS verdict.
Exits 1 (halts pipeline) if any decomposed task lacks a passing simulation.
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Tasks that use callable handlers (legacy path) — no simulation required
LEGACY_TASKS = {
    "WC011-01", "WC011-02", "WC011-03", "WC011-04", "WC011-05", "WC011-07",
    "WC012-01", "WC012-02",
}


def _read_pending_tasks() -> list[str]:
    """Read pending tasks from WC file (source of truth) or FORCE_TASK env var."""
    force = os.environ.get("FORCE_TASK", "").strip()
    if force:
        return [force]

    # Get current sprint from PROJECT_STATE.md
    state = (REPO_ROOT / "constitution" / "PROJECT_STATE.md").read_text()
    sm = re.search(r"## SPRINT_STATE_MACHINE.*?```yaml(.*?)```", state, re.DOTALL)
    if not sm:
        return []
    sprint_match = re.search(r"^current_sprint:\s*(\S+)", sm.group(1), re.MULTILINE)
    if not sprint_match:
        return []
    sprint = sprint_match.group(1).strip()

    # Find WC file and parse pending tasks
    wc_files = list((REPO_ROOT / "work-contracts").glob(f"{sprint}-*.md"))
    if not wc_files:
        return []

    content = wc_files[0].read_text(encoding="utf-8")
    task_id_pat = re.compile(r"^WC\d+-\d+[a-z]?$")
    pending = []
    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            continue
        task_id = cells[1].strip()
        if not task_id_pat.match(task_id):
            continue
        status = cells[-3].strip().lower()
        if status == "pending":
            pending.append(task_id)
    return pending


def main() -> int:
    print("── C-086 Pre-Execution Simulation Gate ──────────────────────")

    tasks = _read_pending_tasks()

    if not tasks:
        print("  ℹ️  No pending tasks — nothing to gate")
        return 0

    sim_dir = REPO_ROOT / "simulation"
    failures = 0

    for task in tasks:
        if task in LEGACY_TASKS:
            print(f"  ✅ {task}: legacy callable handler — no simulation required")
            continue

        # Find matching SIM-PL-002 file (case-insensitive filename search)
        matches = (
            list(sim_dir.glob(f"SIM-PL-002-{task}-*.md")) or
            list(sim_dir.glob(f"SIM-PL-002-{task.lower()}-*.md"))
        )

        if not matches:
            print(f"  ❌ C-086: {task} — no simulation found")
            print(f"     Required: simulation/SIM-PL-002-{task}-*.md with Verdict: PASS")
            print(f"     LLM call for {task} is NOT authorized (C-086).")
            failures += 1
            continue

        content = matches[0].read_text(encoding="utf-8", errors="replace")
        if "Verdict: ✅ PASS" in content or "VERDICT: ✅ PASS" in content:
            print(f"  ✅ C-086: {task} — {matches[0].name}")
        else:
            print(f"  ❌ C-086: {task} — {matches[0].name} has no PASS verdict")
            failures += 1

    if failures > 0:
        print(f"\n  C-086 GATE FAILED: {failures} task(s) need SIM-PL-002 with PASS.")
        print("  No LLM calls authorized until simulations are run and PASS recorded.")
        return 1

    print("  ✅ C-086 gate: all decomposed tasks have simulation PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
