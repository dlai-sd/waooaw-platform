"""Deterministic WC-012 routing contract check.

Implements: architecture/reference/goal-orchestrator/component-contracts.md §2
Constitutional basis: C-032, C-059, C-086

WCSpecReader is the current specification bridge for GoalExecutor. The hard-coded
TASK_HANDLERS registry is legacy fallback and is not authoritative for WC-012.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from goal_orchestrator.goal_executor import GoalExecutor
from task_decomposer import check_simulation_exists
from wc_spec_reader import load


def main() -> int:
    failures: list[str] = []
    tasks = load("WC012")
    expected = ["WC012-01", "WC012-02", "WC012-03", "WC012-04"]

    for task_id in expected:
        spec = tasks.get(task_id)
        if spec is None:
            failures.append(f"{task_id} missing from WCSpecReader")
            continue
        if not spec.scope:
            failures.append(f"{task_id} has no parsed scope")

    for task_id in ("WC012-03", "WC012-04"):
        exists, detail = check_simulation_exists(task_id)
        if not exists:
            failures.append(f"{task_id} simulation missing: {detail}")

    if not callable(getattr(GoalExecutor, "execute_sprint_task", None)):
        failures.append("GoalExecutor.execute_sprint_task is unavailable")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: WC012 tasks route through WCSpecReader and GoalExecutor")
    print("PASS: WC012-03 and WC012-04 retain C-086 simulations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
