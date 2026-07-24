#!/usr/bin/env python3
"""
task_decomposer.py — Dependency-Ordered Sub-Task Execution Engine

# Implements: architecture/reference/pipeline/dependency-graph-task-decomposition.md
#             architecture/reference/pipeline/wc-spec-reader.md (IB-022 Phase 2a)
# constitutional_basis:
#   C-084 (Step Dependency Ordering — sub-tasks execute in dependency order, halt on failure)
#   C-083 (Emit-Transport-Listen — signal emitted after each sub-task, branch context propagated)
#   C-086 (Pre-Execution Simulation Obligation — simulation must pass before first LLM call)
#   C-082 (Build Validation — compile gate between every sub-task)
#   C-059 (Traceability — every sub-task traces to its spec via wc_task_id)
#   C-032 (Implementation may not create architecture — decomposition authorized by sprint-task-decomposition.md)
# office: Platform IT Expert (Implementation hat)
# IB: IB-021 / WC-019, IB-022

Implements ADR-030 Amendment 1: sub-task decomposition replaces single-LLM-call
for multi-layer tasks.

Implements ADR-030 Amendment 2 (IB-022): SubTaskDef.wc_task_id links to PMO Work
Contract. _build_effective_check() assembles constitutional_check from:
  1. PMO WC spec (via WCSpecReader)
  2. output_files list
  3. prior task preservation (not_regenerate_from ∩ completed)
  4. STACK_BEHAVIORAL_RULES (EA-approved floor rules per stack)
  5. constitutional_check delta (task-specific override)
Backward compatible: SubTaskDef without wc_task_id uses constitutional_check only.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).parent.parent


# ══════════════════════════════════════════════════════════════════════════════
# Stack Behavioral Rules (IB-022)
# EA-approved floor rules per technology stack.
# Changes to this dict require Enterprise Architect review (C-032).
# These rules apply to every LLM subtask on the given stack.
# ══════════════════════════════════════════════════════════════════════════════

STACK_BEHAVIORAL_RULES: dict[str, list[str]] = {
    "dotnet": [
        "ActionParameters is JSON-encoded — use ctx.GetParameter(\"key\"), NEVER TryGetValue().",
        "TenantId comes from gRPC metadata: context.RequestHeaders.GetValue(\"x-tenant-id\") ?? \"\".",
        "All using directives MUST precede the namespace declaration (proto namespace collision risk).",
        "PROTO NAMESPACE: using Waooaw.ConstitutionalEngine.Grpc; on files referencing gRPC types.",
        "C-059 header required on every .cs file: // Implements: <spec> and // constitutional_basis: <claims>.",
    ],
    "python": [
        "No synchronous DB calls from Temporal activities — use async/await throughout.",
        "Every FastAPI endpoint must call CE.ValidateAction before execution (C-023).",
        "PII must not appear in any log statement (C-063).",
        "C-059 header required: # Implements: <spec> and # constitutional_basis: <claims>.",
    ],
    "typescript": [
        "JWT stored in httpOnly cookie ONLY — never localStorage or sessionStorage.",
        "All API mutations require CE.ValidateAction call before execution (C-023).",
        "Emergency Stop button must be rendered on every authenticated page (C-001).",
        "C-059 header required: // Implements: <spec> and // constitutional_basis: <claims>.",
    ],
    "terraform": [
        "All outputs must be named and described — they become PTR terraform_output entries.",
        "No secrets in Terraform state — use Azure Key Vault references (ADR-014).",
        "C-059 header required on every .tf file: # Implements: <spec> and # constitutional_basis: <claims>.",
    ],
    "mixed": [],  # No stack-specific rules — use constitutional_check delta
}


# ── Sub-task definition ────────────────────────────────────────────────────────

@dataclass
class SubTaskDef:
    """
    Declares one unit of work within a sprint task.

    type='deterministic': template_fn() called — no LLM, guaranteed namespace.
    type='llm': execute_with_llm() called — Claude generates business logic.

    C-084: depends_on list enforced before execution begins.
    C-083: signal emitted after compile gate passes.

    IB-022: wc_task_id links to PMO Work Contract for constitutional requirements.
    constitutional_check is now a delta/override — primary content comes from WC spec.
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
    model_hint: str = "reasoning"
    max_tokens: int = 10000

    # IB-022: WC-spec-driven constitutional check assembly
    wc_task_id: str = ""                       # "WC012-02" → auto-loads PMO spec
    output_files: list[str] = field(default_factory=list)  # files this subtask MUST produce
    not_regenerate_from: list[str] = field(default_factory=list)  # prior subtask IDs
    stack: str = "dotnet"                      # selects STACK_BEHAVIORAL_RULES entry

    # DELTA: task-specific override / additions (primary if wc_task_id empty)
    constitutional_check: str = ""


# ── Effective constitutional check assembly (IB-022) ──────────────────────────

def _build_effective_check(st: SubTaskDef, completed: list[str]) -> str:
    """
    Assemble the effective constitutional_check for an LLM subtask.

    # Implements: architecture/reference/pipeline/wc-spec-reader.md §_build_effective_check()
    # constitutional_basis: C-059 (traceability), C-032 (spec before code), DP-009 (API First)

    Assembly order:
      1. PMO constitutional requirements (auto-loaded from WC spec)
      2. Output file list
      3. Prior task preservation (not_regenerate_from ∩ completed)
      4. Stack behavioral rules (EA-approved floor)
      5. Task-specific delta (constitutional_check field)

    Graceful: if WC spec not found, falls back to delta only. Never blocks execution.
    PTR type contracts are appended AFTER this output by execute_subtask_chain.
    """
    parts: list[str] = []

    # 1. PMO constitutional requirements
    if st.wc_task_id:
        try:
            from wc_spec_reader import get_task
            wc_spec = get_task(st.wc_task_id)
            if wc_spec:
                pmo_section = (
                    f"CONSTITUTIONAL REQUIREMENTS "
                    f"(PMO: {wc_spec.task_id} — {wc_spec.title}):\n"
                )
                if wc_spec.scope:
                    pmo_section += f"Scope: {wc_spec.scope}\n"
                if wc_spec.constitutional_check:
                    pmo_section += wc_spec.constitutional_check
                if wc_spec.cct_gate:
                    pmo_section += f"\nCCT gate: {wc_spec.cct_gate}"
                parts.append(pmo_section.strip())
        except Exception as _wc_err:
            print(f"  WCSpecReader: skipped ({_wc_err})")

    # 2. Output file boundaries
    if st.output_files:
        files_section = "Implement ONLY these files:\n" + "\n".join(
            f"  {f}" for f in st.output_files
        )
        parts.append(files_section)

    # 3. Prior task preservation
    preserved = [t for t in st.not_regenerate_from if t in completed]
    if preserved:
        parts.append(
            f"Do NOT regenerate files from prior subtasks: {', '.join(preserved)}"
        )

    # 4. Stack behavioral rules (EA floor)
    rules = STACK_BEHAVIORAL_RULES.get(st.stack, [])
    if rules:
        rules_section = "STACK RULES (non-negotiable):\n" + "\n".join(
            f"  {r}" for r in rules
        )
        parts.append(rules_section)

    # 5. Task-specific delta
    if st.constitutional_check:
        parts.append(st.constitutional_check)

    return "\n\n".join(filter(None, parts))


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
    infra_error_tasks: list,
    dry_run: bool = False,
) -> bool:
    """
    Execute sub-tasks in dependency order with compile gates between each.

    C-084: halts on first failure — no downstream sub-tasks called.
    C-083: emits signal after each sub-task, refreshes branch context.
    C-082: compile gate after every sub-task.
    Backward compatible: called only when task has 'subtasks' key.
    """
    # Lazy import to avoid circular dependency at module load time.
    # The runner is always loaded before this function is called.
    _scripts = str(REPO_ROOT / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)  # only insert once
    from autonomous_sprint_runner import execute_with_llm, get_branch_context, git

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

            # IB-022: assemble constitutional_check from WC spec + stack rules + delta
            effective_check = _build_effective_check(st, completed)

            # C-085 / DP-009: inject PTR type contracts into constitutional_check
            # so the LLM sees compiled property names, not spec prose that may have drifted.
            try:
                from platform_type_registry import build_ptr_prompt_block, load_ptr
                ptr = load_ptr()
                if ptr:
                    all_type_names = [
                        t
                        for task_entry in ptr.get("tasks", {}).values()
                        for t in task_entry.get("types", {}).keys()
                    ]
                    ptr_block = build_ptr_prompt_block(all_type_names, ptr=ptr)
                    if ptr_block:
                        effective_check = effective_check + ptr_block
                        print(f"  PTR: injected {len(all_type_names)} compiled type(s) into prompt (C-085/DP-009)")
            except Exception as _ptr_err:
                print(f"  PTR injection skipped: {_ptr_err}")

            success = execute_with_llm(
                st.id,
                st.description,
                spec_with_context,
                effective_check,
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

        # C-083 Emit: extract compiled types → write to PTR for downstream subtasks.
        # Best-effort — never blocks sprint execution.
        try:
            from platform_type_registry import update_ptr_from_task
            src_files = [
                str(f.relative_to(REPO_ROOT))
                for f in (REPO_ROOT / "src").rglob("*")
                if f.is_file() and f.suffix in (".cs", ".proto", ".py", ".ts", ".tsx", ".tf")
            ]
            if src_files:
                update_ptr_from_task(st.id, src_files)
        except Exception as _ptr_err:
            print(f"  PTR update skipped: {_ptr_err}")

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
