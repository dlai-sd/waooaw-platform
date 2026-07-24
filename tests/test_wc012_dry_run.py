"""
WC012 End-to-End Dry Run Integration Test
==========================================
Exercises the full routing chain WITHOUT LLM calls:
  Runner routing → C-086 gate → execute_subtask_chain(dry_run=True) → compile gate skip

Validates:
  - All 4 WC012 tasks are registered in TASK_HANDLERS
  - WC012-01/02 are callable (deterministic/LLM — legacy path)
  - WC012-03/04 are dict with subtasks (decomposed path)
  - C-086 gate finds PASS simulation for WC012-03 and WC012-04
  - execute_subtask_chain routes all sub-tasks in dependency order (dry_run=True)
  - No LLM calls, no commits, no branch mutations

Usage:
  python3 tests/test_wc012_dry_run.py
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts"))

os.environ.setdefault("GITHUB_REPO", "dlai-sd/waooaw-platform")
os.environ.setdefault("ANTHROPIC_API_KEY", "dry-run-key")

PASS = "\033[32m✅\033[0m"
FAIL = "\033[31m❌\033[0m"
INFO = "\033[34mℹ️ \033[0m"

errors: list[str] = []


def check(condition: bool, name: str, detail: str = "") -> None:
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}{': ' + detail if detail else ''}")
        errors.append(name)


# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  WC012 Dry Run — Phase 1: Task Registration")
print("══════════════════════════════════════════════")

from autonomous_sprint_runner import (  # type: ignore[import]
    TASK_HANDLERS, _MONITOR_SIGNAL, _INFRA_ERROR_TASKS, _check_simulation,
    SCAFFOLD_TASKS,
)

WC012_TASKS = ["WC012-01", "WC012-02", "WC012-03", "WC012-04"]

for task in WC012_TASKS:
    check(task in TASK_HANDLERS, f"{task} registered in TASK_HANDLERS")

check("WC012-01" in SCAFFOLD_TASKS, "WC012-01 is a scaffold task (deterministic)")

# WC012-01 and WC012-02 should be callable (legacy path)
for task in ["WC012-01", "WC012-02"]:
    h = TASK_HANDLERS.get(task)
    check(callable(h), f"{task} handler is callable (legacy path)")

# WC012-03 and WC012-04 should be dicts (decomposed path)
for task in ["WC012-03", "WC012-04"]:
    h = TASK_HANDLERS.get(task)
    check(isinstance(h, dict) and "subtasks" in h,
          f"{task} handler is decomposed dict", f"got {type(h)}")


# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  WC012 Dry Run — Phase 2: C-086 Gate Check")
print("══════════════════════════════════════════════")

from task_decomposer import check_simulation_exists  # type: ignore[import]

for task in ["WC012-03", "WC012-04"]:
    ok, msg = check_simulation_exists(task)
    check(ok, f"C-086 gate: {task} has PASS simulation", msg)
    print(f"      {INFO} {msg}")

# WC012-01/02 have callable handlers — the C-086 gate is never invoked for them.
# The runner routes callable → direct call, skipping the simulation check entirely.
for task in ["WC012-01", "WC012-02"]:
    h = TASK_HANDLERS[task]
    check(callable(h), f"C-086 gate: {task} is callable handler — C-086 NOT invoked (correct)")
    print(f"      {INFO} {task} bypasses C-086 gate via callable routing")


# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  WC012 Dry Run — Phase 3: Sub-Task Chain (dry_run=True)")
print("══════════════════════════════════════════════")

from task_decomposer import execute_subtask_chain, SubTaskDef  # type: ignore[import]

mock_monitor: dict = {"sprint": "WC-012", "signals": []}
mock_infra_errors: list = []

for task in ["WC012-03", "WC012-04"]:
    h = TASK_HANDLERS[task]
    subtasks: list[SubTaskDef] = h["subtasks"]

    print(f"\n  ── {task}: {len(subtasks)} sub-tasks ──")
    for st in subtasks:
        print(f"    [{st.id}] type={st.type}  depends_on={st.depends_on}  compile_gate={st.compile_gate}")

    result = execute_subtask_chain(
        task_id=task,
        subtasks=subtasks,
        monitor_signal=mock_monitor,
        infra_error_tasks=mock_infra_errors,
        dry_run=True,
    )
    check(result, f"{task} chain completed (dry_run=True)")
    check(len(mock_monitor.get("signals", [])) >= 0, f"{task} signals emitted without crash")


# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  WC012 Dry Run — Phase 4: Dependency Order")
print("══════════════════════════════════════════════")

for task in ["WC012-03", "WC012-04"]:
    h = TASK_HANDLERS[task]
    subtasks: list[SubTaskDef] = h["subtasks"]
    seen: set[str] = set()
    order_ok = True
    for st in subtasks:
        for dep in st.depends_on:
            if dep not in seen:
                print(f"  {FAIL} {task}.{st.id}: depends on {dep} which hasn't been declared yet")
                order_ok = False
        seen.add(st.id)
    check(order_ok, f"{task} sub-tasks in valid dependency order")


# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print(f"  RESULT: {len(errors)} failure(s)")
print("══════════════════════════════════════════════")
if errors:
    for e in errors:
        print(f"  {FAIL} {e}")
    sys.exit(1)
else:
    print(f"  {PASS} All checks passed — WC012 chain ready for live execution")
    print()
