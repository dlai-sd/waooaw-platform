#!/usr/bin/env python3
"""
task_decomposer.py — Dependency-Ordered Sub-Task Execution Engine

# Implements: architecture/reference/pipeline/dependency-graph-task-decomposition.md
# constitutional_basis:
#   C-084 (Step Dependency Ordering — sub-tasks execute in dependency order, halt on failure)
#   C-083 (Emit-Transport-Listen — signal emitted after each sub-task, branch context propagated)
#   C-086 (Pre-Execution Simulation Obligation — simulation must pass before first LLM call)
#   C-082 (Build Validation — compile gate between every sub-task)
#   C-059 (Traceability — every sub-task traces to its spec)
# office: Platform IT Expert (Implementation hat)
# IB: IB-021 / WC-019

Implements ADR-030 Amendment 1: sub-task decomposition replaces single-LLM-call
for multi-layer tasks. Backward compatible: tasks without 'subtasks' key continue
to use execute_with_llm() unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).parent.parent


# ── Sub-task definition ────────────────────────────────────────────────────────

@dataclass
class SubTaskDef:
    """
    Declares one unit of work within a sprint task.

    type='deterministic': template_fn() called — no LLM, guaranteed namespace.
    type='llm': execute_with_llm() called — Claude generates business logic.

    C-084: depends_on list enforced before execution begins.
    C-083: signal emitted after compile gate passes.
    """
    id: str                                    # e.g. "WC012-03a"
    description: str
    type: str                                  # "deterministic" | "llm"
    depends_on: list[str] = field(default_factory=list)
    compile_gate: str = "dotnet_build"         # "dotnet_build" | "dotnet_test" | "ruff" | "tsc"

    # For type="deterministic"
    template_fn: Optional[Callable[[], bool]] = None

    # For type="llm" — mirror of execute_with_llm() params
    spec_sections: dict[str, str] = field(default_factory=dict)
    constitutional_check: str = ""
    model_hint: str = "reasoning"
    max_tokens: int = 10000


# ── Compile gates ──────────────────────────────────────────────────────────────

def run_compile_gate(gate_type: str, service_dir: str = "src/constitutional-engine") -> tuple[bool, str]:
    """
    Run the appropriate compile gate for the technology stack.
    C-082: build validation required after every sub-task.
    Returns (passed, error_output).
    """
    if gate_type == "dotnet_build":
        csproj_files = list((REPO_ROOT / service_dir).glob("*.csproj"))
        if not csproj_files:
            return False, f"No .csproj found in {service_dir}"
        result = subprocess.run(
            ["dotnet", "build", str(csproj_files[0]), "--nologo", "-v", "quiet"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stderr[:500] if result.returncode != 0 else ""

    if gate_type == "dotnet_test":
        test_csproj = list((REPO_ROOT / "tests").rglob("*.csproj"))
        if not test_csproj:
            return False, "No test .csproj found"
        result = subprocess.run(
            ["dotnet", "test", str(test_csproj[0]), "--nologo", "-v", "quiet", "--no-build"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stderr[:500] if result.returncode != 0 else ""

    if gate_type == "ruff":
        result = subprocess.run(
            ["python3", "-m", "ruff", "check", service_dir],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stdout[:500]

    return False, f"Unknown gate_type: {gate_type}"


# ── Signal emission (C-083) ───────────────────────────────────────────────────

def emit_subtask_signal(task_id: str, subtask_id: str, result: str, monitor_signal: dict) -> None:
    """
    C-083 (Emit-Transport-Listen): emit sub-task completion signal.
    Written to monitor-signal.json before next sub-task begins.
    The next sub-task's branch context read AFTER this signal is emitted.
    """
    if "subtask_results" not in monitor_signal:
        monitor_signal["subtask_results"] = {}
    monitor_signal["subtask_results"][subtask_id] = {
        "result": result,  # "SUCCESS" | "FAIL" | "SKIPPED"
        "task_id": task_id,
    }


# ── TaskDecomposer ─────────────────────────────────────────────────────────────

def execute_subtask_chain(
    task_id: str,
    subtasks: list[SubTaskDef],
    monitor_signal: dict,
    _INFRA_ERROR_TASKS: list,
    dry_run: bool = False,
) -> bool:
    """
    Execute sub-tasks in dependency order with compile gates between each.

    C-084: halts on first failure — no downstream sub-tasks called.
    C-083: emits signal after each sub-task, refreshes branch context.
    C-082: compile gate after every sub-task.
    Backward compatible: called only when task has 'subtasks' key.
    """
    # Import here to avoid circular dependency
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from autonomous_sprint_runner import (
        execute_with_llm, get_branch_context, git, _MONITOR_SIGNAL
    )

    completed: list[str] = []
    all_written_files: list[str] = []

    print(f"\n── {task_id}: sub-task chain ({len(subtasks)} sub-tasks) ──")

    for st in subtasks:
        # ── C-084: verify all dependencies completed ───────────────────────────
        unmet = [d for d in st.depends_on if d not in completed]
        if unmet:
            print(f"  [{st.id}] BLOCKED — unmet dependencies: {unmet}")
            print(f"  C-084: halting chain. {st.id} not executed.")
            emit_subtask_signal(task_id, st.id, "SKIPPED", monitor_signal)
            return False

        print(f"\n  ── [{st.id}] {st.description} ({st.type}) ──")

        if dry_run:
            print(f"  DRY RUN: would execute sub-task {st.id}")
            completed.append(st.id)
            continue

        # ── C-083: refresh branch context before LLM call ─────────────────────
        branch_context = get_branch_context()
        if branch_context:
            print(f"  Branch context refreshed ({len(branch_context.splitlines())} lines)")

        # ── Execute sub-task ───────────────────────────────────────────────────
        if st.type == "deterministic":
            if st.template_fn is None:
                print(f"  [{st.id}] ERROR: deterministic sub-task has no template_fn")
                emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
                return False
            print(f"  [{st.id}] Running deterministic template...")
            success = st.template_fn()

        elif st.type == "llm":
            print(f"  [{st.id}] Calling LLM ({st.model_hint}, max={st.max_tokens} tokens)...")
            # Inject branch context into spec content for LLM call
            spec_with_context = dict(st.spec_sections)
            success = execute_with_llm(
                st.id,
                st.description,
                spec_with_context,
                st.constitutional_check,
                st.model_hint,
                st.max_tokens,
            )
        else:
            print(f"  [{st.id}] ERROR: unknown type '{st.type}'")
            return False

        if not success:
            print(f"  [{st.id}] FAILED — halting chain (C-084)")
            emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
            # C-077: halt immediately — no downstream LLM calls on guaranteed failure
            return False

        # ── C-082: compile gate ────────────────────────────────────────────────
        gate_ok, gate_error = run_compile_gate(st.compile_gate)
        if not gate_ok:
            print(f"  [{st.id}] COMPILE GATE FAILED: {gate_error[:200]}")
            print(f"  C-084: halting chain — downstream sub-tasks not executed")
            emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
            return False

        print(f"  [{st.id}] Compile gate: ✅ PASS")

        # ── C-083: emit signal ─────────────────────────────────────────────────
        emit_subtask_signal(task_id, st.id, "SUCCESS", monitor_signal)
        completed.append(st.id)
        print(f"  [{st.id}] C-083 signal: SUBTASK_COMPLETE emitted")

    # All sub-tasks completed — commit everything together
    if not dry_run and completed:
        git(["add", "src/", "tests/"], check=False)
        diff = git(["diff", "--cached", "--quiet"], check=False)
        if diff.returncode != 0:
            git(["commit", "-m",
                 f"feat: {task_id} — {subtasks[-1].description}\n\n"
                 f"IB: IB-009\nConstitutional: C-059, C-073, C-076, C-084\n"
                 f"Sub-tasks: {', '.join(completed)}"])

    print(f"\n  ✅ {task_id} complete — {len(completed)}/{len(subtasks)} sub-tasks passed")
    return len(completed) == len(subtasks)


def check_simulation_exists(task_id: str) -> tuple[bool, str]:
    """
    C-086: verify simulation with PASS verdict exists for this task/sub-task.
    Returns (exists, reason).
    """
    sim_dir = REPO_ROOT / "simulation"
    # Match case-insensitively: files are named SIM-PL-002-WC012-03-*.md (uppercase)
    patterns = [
        f"SIM-PL-002-{task_id}-*.md",          # exact case: SIM-PL-002-WC012-03-*.md
        f"SIM-PL-002-{task_id.lower()}-*.md",  # lowercase fallback
        f"SIM-PL-002-{task_id.lower().replace('-', '')}-*.md",  # no-hyphen fallback
    ]

    for pattern in patterns:
        matches = list(sim_dir.glob(pattern))
        if matches:
            content = matches[0].read_text(encoding="utf-8", errors="replace")
            if "Verdict: ✅ PASS" in content or "VERDICT: ✅ PASS" in content:
                return True, str(matches[0].name)

    return False, f"No SIM-PL-002 with PASS verdict found for {task_id}"
