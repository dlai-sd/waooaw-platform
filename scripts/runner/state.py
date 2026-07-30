# Implements: scripts/runner/state.py
# constitutional_basis: C-069 (Self-Improvement — monitor signal), C-077 (Cost Ceiling)
# ib_item: IB-009
"""
Shared mutable runtime state for the autonomous sprint runner.

Both llm_codegen.py and task_executor.py write into these structures
during a single run. The main entry-point (autonomous_sprint_runner.py)
reads them at the end to emit the Constitutional Monitor artifact.

Design: module-level singletons (not class instances) so all runner
modules share the exact same object reference when imported.
"""
from __future__ import annotations

import os

# Populated during execution — written to sprint-context/monitor-signal.json
# and uploaded as artifact for the Constitutional Monitor job to consume.
# C-069: Observable state for downstream jobs (self-improvement loop).
_MONITOR_SIGNAL: dict = {
    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "sprint": "",
    "scaffold_task": None,     # task ID of the scaffold (if any) in this run
    "scaffold_failed": False,  # True = downstream spec-gap issues are CASCADE bugs
    "task_results": {},        # per-task: result, error_type, snippet, attempts, issue
    "spec_gap_issues": [],     # GitHub issue numbers opened by flag_spec_gap()
    "overall_result": "UNKNOWN",
    "file_costs": {},          # task_id → ₹ cost — populated by call_llm_via_magiclm
}

# Populated by execute_with_llm() when all 3 attempts are pure API failures.
# main() reads this to distinguish INFRA_ERROR from SPEC_GAP.
_INFRA_ERROR_TASKS: list[str] = []
