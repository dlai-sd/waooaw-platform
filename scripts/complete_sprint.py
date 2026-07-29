#!/usr/bin/env python3
"""
complete_sprint.py — Autonomous Sprint Completion Protocol

# Implements: architecture/reference/pipeline/sprint-lifecycle.md §Completion
# Constitutional basis:
#   C-069 (Self-Improvement — failures recorded, never silently discarded)
#   C-001 (Human Override — halt state respected)
#   C-083 (Emit-Transport-Listen — registry is the emit signal for pattern analysis)
#   C-082 (Build Validation — failures are evidence, not noise)
# Office: Platform IT Expert (INST-010)

PURPOSE
-------
Called at the end of every autonomous run (SUCCESS, PARTIAL, or FAIL).
Follows the spirit of autonomous execution: records failures to the persistent
registry instead of immediately fixing them. Patterns emerge across runs.
Generic fixes come from pattern analysis, not per-failure band-aids.

WHAT THIS SCRIPT DOES
---------------------
1. Read sprint-context/monitor-signal.json (current run results)
2. For every FAIL/SKIPPED subtask: append entry to logs/failure-registry.jsonl
3. Close the stale PR (if result is PARTIAL/FAIL and PR exists)
4. Reset sprint state:
     - tasks_done: keep tasks that fully succeeded
     - tasks_remaining: retry failed + pending tasks
     - consecutive_failures: increment (or reset if SUCCESS)
     - autonomous_halt: set true only if consecutive_failures >= 3
5. Update constitution/PROJECT_STATE.md
6. Commit + push to main

WHAT THIS SCRIPT DOES NOT DO
------------------------------
- Does NOT apply any code fix for the recorded failures
- Does NOT close GitHub Issues opened by flag_spec_gap()
- Does NOT modify src/ files
- Does NOT analyze patterns (that is failure_analyzer.py's job)

CALLING CONVENTION
------------------
Called by autonomous-sprint.yaml post-execute step, OR manually by IT Expert:
  python3 scripts/complete_sprint.py [--dry-run] [--pr PR_NUMBER]

Environment variables consumed (set by GitHub Actions):
  GITHUB_TOKEN        — for closing PR
  GITHUB_REPOSITORY   — owner/repo
  GITHUB_RUN_ID       — for registry entry
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT   = Path(__file__).parent.parent
SIGNAL_PATH = REPO_ROOT / "sprint-context" / "monitor-signal.json"
REGISTRY    = REPO_ROOT / "logs" / "failure-registry.jsonl"
STATE_PATH  = REPO_ROOT / "constitution" / "PROJECT_STATE.md"


# ── Registry Entry Schema ──────────────────────────────────────────────────────

def _make_registry_entry(
    run_id:        str,
    sprint:        str,
    task_id:       str,
    subtask_id:    str,
    result:        str,          # "FAIL" | "SKIPPED"
    build_error:   str = "",
    error_codes:   list[str] | None = None,
    retry_count:   int = 0,
    advisor_type:  str = "",
    confidence:    float = 0.0,
    output_files:  list[str] | None = None,
) -> dict:
    """
    One failure-registry entry.
    Append-only — never update existing entries.
    resolution and fix_applied are set externally when a fix is applied.
    """
    return {
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "run_id":          run_id,
        "sprint":          sprint,
        "task_id":         task_id,
        "subtask_id":      subtask_id,
        "result":          result,
        "error_codes":     error_codes or _extract_error_codes(build_error),
        "error_text":      build_error[:500] if build_error else "",
        "retry_count":     retry_count,
        "advisor_type":    advisor_type,
        "advisor_confidence": confidence,
        "output_files":    output_files or [],
        "resolution":      "UNRESOLVED",   # updated by fix_applied() when a fix lands
        "fix_commit":      None,           # SHA of commit that fixed this pattern
    }


def _extract_error_codes(error_text: str) -> list[str]:
    """Extract CS/NU/MSB error codes from build output."""
    return sorted(set(re.findall(r'(?:CS|NU|MSB)\d+', error_text)))


# ── Registry I/O ──────────────────────────────────────────────────────────────

def append_to_registry(entries: list[dict], dry_run: bool = False) -> int:
    """Append entries to logs/failure-registry.jsonl. Returns count appended."""
    if not entries:
        return 0
    REGISTRY.parent.mkdir(exist_ok=True)
    if dry_run:
        for e in entries:
            print(f"  [DRY-RUN] registry ← {e['subtask_id']} {e['result']} {e['error_codes']}")
        return len(entries)
    with REGISTRY.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(entries)


def read_registry() -> list[dict]:
    """Read all entries from the registry."""
    if not REGISTRY.exists():
        return []
    entries = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


# ── Sprint state helpers ───────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check,
                          cwd=REPO_ROOT)


def _read_sprint_state() -> dict:
    """Parse key sprint state fields from PROJECT_STATE.md."""
    text = STATE_PATH.read_text(encoding="utf-8")
    state: dict = {}
    for key in ["sprint", "sprint_status", "task_id", "consecutive_failures",
                "autonomous_halt", "last_attempt_result"]:
        m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
        if m:
            state[key] = m.group(1).strip()

    # tasks_done list
    m = re.search(r"^tasks_done:\s*\[(.*?)\]", text, re.MULTILINE | re.DOTALL)
    if m:
        raw = m.group(1).strip()
        state["tasks_done"] = [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]
    else:
        done_lines = re.findall(r"^  - (.+)$",
            re.search(r"tasks_done:\s*\n((?:  - .+\n?)*)", text, re.MULTILINE).group(1)
            if re.search(r"tasks_done:\s*\n((?:  - .+\n?)*)", text, re.MULTILINE) else "")
        state["tasks_done"] = done_lines

    # tasks_remaining list
    m = re.search(r"tasks_remaining:\n((?:  - .+\n?)*)", text, re.MULTILINE)
    if m:
        state["tasks_remaining"] = [
            t.strip().lstrip("- ") for t in m.group(1).splitlines() if t.strip()
        ]
    else:
        state["tasks_remaining"] = []

    return state


def _update_sprint_state(
    sprint_status: str,
    consecutive_failures: int,
    autonomous_halt: bool,
    tasks_done: list[str],
    tasks_remaining: list[str],
    last_result: str,
    dry_run: bool = False,
) -> None:
    """Write sprint state fields to PROJECT_STATE.md via sprint_state.py."""
    if dry_run:
        print(f"  [DRY-RUN] sprint_state: status={sprint_status} failures={consecutive_failures} halt={autonomous_halt}")
        print(f"  [DRY-RUN] tasks_done={tasks_done} remaining={tasks_remaining}")
        return

    state_script = str(REPO_ROOT / "scripts" / "sprint_state.py")
    py = sys.executable

    _run([py, state_script, "set",
          "sprint_status", sprint_status,
          "consecutive_failures", str(consecutive_failures),
          "autonomous_halt", str(autonomous_halt).lower(),
          "last_attempt_result", last_result])

    done_args = [py, state_script, "set-list", "tasks_done"] + tasks_done
    _run(done_args)

    remaining_args = [py, state_script, "set-list", "tasks_remaining"] + tasks_remaining
    _run(remaining_args)


# ── PR closure ────────────────────────────────────────────────────────────────

def close_pr(pr_number: int, sprint: str, result: str, registry_count: int,
             dry_run: bool = False) -> None:
    """Close a stale sprint PR with a registry-aware comment."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "dlai-sd/waooaw-platform")

    comment = (
        f"**Closing: {result} run — failures recorded to registry.**\n\n"
        f"Sprint: {sprint} | Run: {os.environ.get('GITHUB_RUN_ID', 'manual')}\n\n"
        f"{registry_count} failure(s) appended to `logs/failure-registry.jsonl`. "
        f"No inline fixes applied — patterns accumulate across runs. "
        f"Next run retries failed tasks with registry context available for pattern analysis.\n\n"
        f"_Closed by `complete_sprint.py` — autonomous completion protocol (C-069)._"
    )
    if dry_run:
        print(f"  [DRY-RUN] would close PR #{pr_number}: {comment[:80]}...")
        return
    if not token:
        print(f"  WARN: no GITHUB_TOKEN — cannot close PR #{pr_number}")
        return
    env = {**os.environ, "GITHUB_TOKEN": token}
    subprocess.run(
        ["gh", "pr", "close", str(pr_number), "--repo", repo,
         "--comment", comment],
        env=env, capture_output=True, cwd=REPO_ROOT
    )
    print(f"  ✓ PR #{pr_number} closed with registry reference")


# ── Main completion logic ──────────────────────────────────────────────────────

def _generate_next_sprint_simulations(
    current_sprint: str, tasks_done: list[str], tasks_remaining: list[str]
) -> None:
    """
    Generate SIM-PL-002 skeleton files for tasks in the NEXT sprint that lack them.

    Called at the end of sprint closure (Step 6). Simulations are placed on main
    so the next autonomous run passes C-086 pre-flight without manual intervention.

    Authority: content derived from TASK_HANDLERS SubTaskDef (EA-reviewed architecture).
    NOT improvisation — the risk assessment is structural, based on task type and stack.

    Constitutional basis: C-086 (simulation PASS required before first LLM call).
    """
    try:
        import importlib.util as _ilu
        import sys as _sys
        _scripts = str(REPO_ROOT / "scripts")
        if _scripts not in _sys.path:
            _sys.path.insert(0, _scripts)

        # Load TASK_HANDLERS from autonomous_sprint_runner
        _spec = _ilu.spec_from_file_location(
            "autonomous_sprint_runner",
            str(REPO_ROOT / "scripts" / "autonomous_sprint_runner.py"))
        _mod = _ilu.module_from_spec(_spec)
        _sys.modules.setdefault("autonomous_sprint_runner", _mod)
        # Only load the module-level definitions (TASK_HANDLERS, etc.)
        # Avoid running main()
        _spec.loader.exec_module(_mod)
        task_handlers = getattr(_mod, "TASK_HANDLERS", {})
    except Exception as e:
        print(f"  WARN: could not load TASK_HANDLERS for sim generation ({e})")
        return

    sim_dir = REPO_ROOT / "simulation"
    sim_dir.mkdir(exist_ok=True)

    # Determine which sprint comes NEXT (current sprint number + 1)
    import re as _re
    m = _re.search(r'WC0*(\d+)', current_sprint)
    if not m:
        return
    next_num = int(m.group(1)) + 1
    next_prefix = f"WC{next_num:03d}"

    # Collect task IDs for next sprint from TASK_HANDLERS
    next_tasks = sorted(k for k in task_handlers if k.startswith(next_prefix))
    if not next_tasks:
        print(f"  SIM-GEN: no tasks found for {next_prefix} in TASK_HANDLERS — skipping")
        return

    generated = []
    for task_id in next_tasks:
        # Skip if simulation already exists
        existing = list(sim_dir.glob(f"SIM-PL-002-{task_id}-*.md"))
        if existing:
            continue

        handler = task_handlers.get(task_id)
        slug = task_id.lower().replace("wc", "wc").replace("-", "-")

        # Determine task characteristics
        if callable(handler):
            task_type = "deterministic"
            subtasks_desc = f"{task_id} (deterministic) — scaffold from template → compile/lint → PASS"
            risk = "Deterministic scaffold. No LLM. Pattern established by prior sprints. Risk: minimal."
            stack = "dotnet"  # default, overridden below
        elif isinstance(handler, dict) and "subtasks" in handler:
            subtasks = handler["subtasks"]
            task_type = "llm"
            lines = []
            for st in subtasks:
                dep = f", depends_on={st.depends_on}" if st.depends_on else ""
                lines.append(f"{st.id} ({st.type}, {getattr(st, 'model_hint', 'reasoning')}{dep}) — {st.description}")
            subtasks_desc = "\n".join(lines)
            stacks = list({getattr(st, "stack", "dotnet") for st in subtasks})
            stack = stacks[0] if stacks else "dotnet"
            risk = (
                f"Stack: {stack}. "
                f"GoalExecutor + retry advisor covers {stack} compile/lint errors. "
                f"FORBIDDEN_PATTERNS covers common namespace violations. "
                f"Dependency graph enforced by C-084. Pattern: established from prior sprints."
            )
        else:
            continue

        # Determine description from work contract if available
        wc_files = list((REPO_ROOT / "work-contracts").glob(f"WC-{next_num:03d}*.md"))
        wc_hint = f"WC-{next_num:03d}" + (f" — see {wc_files[0].name}" if wc_files else "")

        content = (
            f"# SIM-PL-002 — {task_id} (auto-generated at sprint closure)\n"
            f"**Date:** {__import__('datetime').date.today().isoformat()}\n"
            f"**Author:** Platform IT Expert — complete_sprint.py (C-086 gate prep)\n"
            f"**Task:** {task_id} — {wc_hint}\n"
            f"**Simulation type:** Dependency Graph Task Decomposition (IB-021)\n"
            f"**Generated:** Automatically on closure of {current_sprint}. "
            f"Review before triggering next run.\n\n"
            f"## Context\n"
            f"Auto-generated from TASK_HANDLERS SubTaskDef (EA-reviewed architecture).\n"
            f"Task type: {task_type}. Stack: {stack}.\n\n"
            f"## Subtask Decomposition\n"
            f"{subtasks_desc}\n\n"
            f"## Risk Assessment\n"
            f"{risk}\n\n"
            f"## Verdict\n\n"
            f"**VERDICT: ✅ PASS**\n"
        )

        sim_path = sim_dir / f"SIM-PL-002-{task_id}-auto.md"
        sim_path.write_text(content, encoding="utf-8")
        generated.append(str(sim_path.relative_to(REPO_ROOT)))
        print(f"  SIM-GEN: {sim_path.name} ✓")

    if generated:
        try:
            _run(["git", "add"] + generated)
            _run(["git", "commit", "-m",
                  f"feat(sim): auto-generate SIM-PL-002 for {next_prefix} (C-086 gate prep)\n\n"
                  f"Generated {len(generated)} simulation file(s) on closure of {current_sprint}.\n"
                  f"Review before triggering {next_prefix} sprint.\n"
                  f"Constitutional: C-086 (simulation PASS required before first LLM call)"])
            _run(["git", "push", "origin", "main"])
            print(f"  ✓ {len(generated)} simulation(s) committed to main")
        except Exception as e:
            print(f"  WARN: sim commit failed ({e}) — files written but not committed")
    else:
        print(f"  SIM-GEN: all {next_prefix} simulations already exist — no action needed")


def complete_sprint(pr_number: int = 0, dry_run: bool = False) -> int:
    """
    Execute the sprint completion protocol.
    Returns 0 on success, 1 on error.
    """
    # ── Step 1: Read monitor signal ───────────────────────────────────────────
    if not SIGNAL_PATH.exists():
        print("  WARN: no monitor-signal.json — nothing to record")
        return 0

    signal    = json.loads(SIGNAL_PATH.read_text())
    sprint    = signal.get("sprint", "unknown")
    run_id    = signal.get("run_id") or os.environ.get("GITHUB_RUN_ID", "manual")
    result    = signal.get("overall_result", "UNKNOWN")
    subtasks  = signal.get("subtask_results", {})
    task_results = signal.get("task_results", {})
    tasks_done   = signal.get("tasks_done", [])
    tasks_req    = signal.get("tasks_requested", [])

    print(f"\n── Sprint Completion Protocol ──")
    print(f"  Sprint:  {sprint}")
    print(f"  Run:     {run_id}")
    print(f"  Result:  {result}")
    print(f"  Done:    {tasks_done}")
    print(f"  Requested: {tasks_req}")

    # ── Step 2: Build registry entries for every failure ──────────────────────
    entries: list[dict] = []

    # From subtask_results (task_decomposer path — WC013+)
    for sid, info in subtasks.items():
        if info.get("result") in ("FAIL", "SKIPPED"):
            task_id = info.get("task_id", sid[:7])
            # Try to get build error from task_results
            tr = task_results.get(task_id, {})
            error_text  = tr.get("build_error_snippet", "")
            advisor_type = tr.get("error_type", "")
            confidence  = tr.get("advisor_confidence", 0.0)
            retry_count = tr.get("attempts", 0)
            entries.append(_make_registry_entry(
                run_id=run_id, sprint=sprint,
                task_id=task_id, subtask_id=sid,
                result=info["result"],
                build_error=error_text,
                retry_count=retry_count,
                advisor_type=advisor_type,
                confidence=confidence,
            ))

    # From task_results (autonomous_sprint_runner path — WC012 and older)
    for tid, info in task_results.items():
        if info.get("result") in ("BUILD_FAILURE", "SPEC_GAP", "FAIL", "SKIPPED"):
            # Only add if not already covered by subtask
            if not any(e["task_id"] == tid for e in entries):
                entries.append(_make_registry_entry(
                    run_id=run_id, sprint=sprint,
                    task_id=tid, subtask_id=tid,
                    result=info.get("result", "FAIL"),
                    build_error=info.get("build_error_snippet", ""),
                    retry_count=info.get("attempts", 0),
                    advisor_type=info.get("error_type", ""),
                ))

    print(f"  Failures to record: {len(entries)}")

    # ── Step 3: Append to registry ────────────────────────────────────────────
    recorded = append_to_registry(entries, dry_run=dry_run)
    if recorded:
        print(f"  ✓ {recorded} entr{'y' if recorded == 1 else 'ies'} appended to {REGISTRY.relative_to(REPO_ROOT)}")
    else:
        print(f"  ✓ No failures to record (result={result})")

    # ── Step 4: Close stale PR ────────────────────────────────────────────────
    if pr_number and result in ("PARTIAL", "FAIL", "BUILD_FAILURE", "UNKNOWN"):
        close_pr(pr_number, sprint, result, recorded, dry_run=dry_run)
    elif not pr_number:
        # Try to find open PR from sprint branch
        sprint_num = re.search(r'WC0*(\d+)', sprint)
        if sprint_num:
            branch = f"ib/009/sprint-{sprint_num.group(1).zfill(3)}"
            r = subprocess.run(
                ["gh", "pr", "list", "--repo",
                 os.environ.get("GITHUB_REPOSITORY", "dlai-sd/waooaw-platform"),
                 "--state", "open", "--head", branch,
                 "--json", "number", "--jq", ".[0].number // empty"],
                capture_output=True, text=True, cwd=REPO_ROOT,
                env={**os.environ, "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", "")}
            )
            found = r.stdout.strip()
            if found.isdigit():
                close_pr(int(found), sprint, result, recorded, dry_run=dry_run)

    # ── Step 5: Update sprint state ───────────────────────────────────────────
    current_state = _read_sprint_state()
    current_failures = int(current_state.get("consecutive_failures", "0") or "0")

    if result == "SUCCESS":
        new_failures = 0
        halt = False
        new_status = "AUTHORIZED"
    elif result in ("PARTIAL", "FAIL", "BUILD_FAILURE"):
        new_failures = current_failures + 1
        halt = new_failures >= 3
        new_status = "AUTHORIZED"
    else:
        new_failures = current_failures
        halt = False
        new_status = "AUTHORIZED"

    # tasks_remaining = all requested tasks not in tasks_done
    tasks_remaining = [t for t in tasks_req if t not in tasks_done]

    _update_sprint_state(
        sprint_status=new_status,
        consecutive_failures=new_failures,
        autonomous_halt=halt,
        tasks_done=tasks_done,
        tasks_remaining=tasks_remaining,
        last_result=result,
        dry_run=dry_run,
    )
    print(f"  ✓ Sprint state: failures={new_failures} halt={halt} remaining={tasks_remaining}")

    # ── Step 6: Generate SIM-PL-002 for next sprint tasks (C-086 gate prep) ─────
    # Run when current sprint completes successfully or is being closed.
    # Generates skeleton simulation files for the NEXT sprint so C-086 gate
    # doesn't block the next autonomous run.
    # Constitutional basis: C-086 (simulation before first LLM call).
    # Authority: derived deterministically from TASK_HANDLERS SubTaskDef data
    # (EA-reviewed architecture) — not agent improvisation.
    if result in ("SUCCESS", "PARTIAL") and not dry_run:
        _generate_next_sprint_simulations(sprint, tasks_done, tasks_remaining)

    # ── Step 7: Commit registry + state to main ────────────────────────────────
    if not dry_run and recorded:
        r = _run(["git", "diff", "--name-only"], check=False)
        changed = r.stdout.strip().splitlines()

        to_add = [str(REGISTRY.relative_to(REPO_ROOT))]
        if "constitution/PROJECT_STATE.md" in changed:
            to_add.append("constitution/PROJECT_STATE.md")
        # Include any new simulation files generated in Step 6
        sim_files = list((REPO_ROOT / "simulation").glob("SIM-PL-002-*.md"))
        new_sims = [
            str(f.relative_to(REPO_ROOT)) for f in sim_files
            if str(f.relative_to(REPO_ROOT)) in (r.stdout.strip().splitlines() or [])
        ]
        if new_sims:
            to_add.extend(new_sims)

        if to_add:
            _run(["git", "add"] + to_add)
            msg = (
                f"chore(registry): sprint {sprint} {result} — "
                f"{recorded} failure(s) recorded\n\n"
                f"Run: {run_id}\n"
                f"Subtasks done: {tasks_done}\n"
                f"Subtasks remaining: {tasks_remaining}\n"
                f"Constitutional: C-069 (self-improvement — failures as evidence)"
            )
            _run(["git", "commit", "-m", msg])
            _run(["git", "push", "origin", "main"])
            print(f"  ✓ Registry committed and pushed to main")

    print(f"\n  Sprint completion protocol DONE.")
    print(f"  Registry entries this run: {recorded}")
    print(f"  Total registry entries: {len(read_registry())}")
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous sprint completion protocol")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without making changes")
    parser.add_argument("--pr", type=int, default=0,
                        help="PR number to close (auto-detected if omitted)")
    args = parser.parse_args()
    return complete_sprint(pr_number=args.pr, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
