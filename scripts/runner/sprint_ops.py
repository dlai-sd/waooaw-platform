# Implements: scripts/runner/sprint_ops.py
# constitutional_basis: C-001 (Human Override), C-059 (Traceability), C-065 (SDLC Separation)
# ib_item: IB-009
"""
Sprint state operations: parse, gate checks, spec validation, integrity checks.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from runner.constants import REPO_ROOT, STATE_FILE
from runner.git_ops import record_evidence, run, set_output


def parse_sprint_state() -> dict:
    """
    Extract SPRINT_STATE_MACHINE YAML block from PROJECT_STATE.md.
    Returns only the 5 control-panel fields. Task progress is in the WC file.
    """
    content = STATE_FILE.read_text(encoding="utf-8")
    match = re.search(
        r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```",
        content, re.DOTALL
    )
    if not match:
        raise ValueError("SPRINT_STATE_MACHINE block not found in PROJECT_STATE.md")

    state: dict = {}
    for line in match.group(1).splitlines():
        line = line.split("#")[0].strip()
        if ":" in line:
            k, _, v = line.partition(":")
            state[k.strip()] = v.strip().strip('"').strip("'")

    return state


def _find_wc_file(sprint: str) -> Path:
    """Locate the work-contract markdown file for the given sprint (e.g. 'WC-027')."""
    slug = sprint.replace("-", "").replace("WC", "WC-")  # normalise to WC-027
    # canonical form is already WC-027; handle bare "WC027" too
    if not slug.startswith("WC-"):
        slug = sprint
    matches = list((REPO_ROOT / "work-contracts").glob(f"{slug}-*.md"))
    if not matches:
        raise FileNotFoundError(f"No work-contract file found for sprint {sprint}")
    return matches[0]


def parse_wc_tasks(sprint: str) -> dict[str, list[str]]:
    """
    Parse the task table from the work-contract file for the given sprint.
    Returns {'pending': [...], 'done': [...], 'failed': [...]} lists of task_ids in order.
    The WC file is the single source of truth for task progress.
    """
    wc_file = _find_wc_file(sprint)
    content = wc_file.read_text(encoding="utf-8")

    # Task id pattern: WCxxx-NNa (e.g. WC027-01a, WC028-03)
    task_id_pat = re.compile(r"^WC\d+-\d+[a-z]?$")
    # ADR-041: 7-state task machine — map new statuses to canonical buckets
    known_statuses = {
        "pending", "done", "failed", "in-progress",
        "failed_structural", "failed_transient", "failed_terminal",
        "skipped_cascade", "skipped_idempotent",
    }

    result: dict[str, list[str]] = {"pending": [], "done": [], "failed": []}

    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        # cells[0] is empty (before first |), cells[1] is task_id cell
        if len(cells) < 6:
            continue
        task_id = cells[1].strip()
        if not task_id_pat.match(task_id):
            continue
        # status is second-to-last non-empty cell (cells[-2] is empty after trailing |)
        status = cells[-3].strip().lower()
        if status not in known_statuses:
            status = "pending"
        if status in ("done", "skipped_idempotent"):
            result["done"].append(task_id)
        elif status in ("failed", "failed_structural", "failed_transient",
                        "failed_terminal", "skipped_cascade"):
            result["failed"].append(task_id)
        else:
            # pending, in-progress (container-killed mid-task) → re-runnable
            result["pending"].append(task_id)

    return result


def update_task_status(sprint: str, task_id: str, status: str) -> None:
    """
    Update the status (and completed_at timestamp) for a task row in the WC file.
    The runner calls this after each task completes — it never touches PROJECT_STATE.md.
    """
    wc_file = _find_wc_file(sprint)
    content = wc_file.read_text(encoding="utf-8")

    completed_at = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        if status == "done"
        else "—"
    )

    lines = content.splitlines(keepends=True)
    updated = False
    for i, line in enumerate(lines):
        if not line.startswith(f"| {task_id} ") and f"| {task_id} |" not in line:
            continue
        if not re.match(rf"^\|\s*{re.escape(task_id)}\s*\|", line):
            continue
        # Replace status and completed_at — the last two data cells before trailing |
        # Pattern: match known status values to avoid false matches in scope text
        new_line = re.sub(
            r"\|\s*(?:pending|done|failed|in-progress|failed_structural|"
            r"failed_transient|failed_terminal|skipped_cascade|skipped_idempotent|"
            r"🔲 TODO)\s*\|\s*[^\|]*\s*\|\s*$",
            f"| {status} | {completed_at} |\n",
            line,
        )
        lines[i] = new_line
        updated = True
        break

    if not updated:
        print(f"WARNING: task {task_id} not found in {wc_file.name}", file=sys.stderr)
        return

    wc_file.write_text("".join(lines), encoding="utf-8")
    print(f"✓ {wc_file.name}: {task_id} → {status} ({completed_at})")


def check_platform_phase_gate(state: dict) -> None:
    """
    C-001 / FinOps Gate: Refuse ALL implementation work when platform_phase = SPEC.
    This is a hard stop — not a warning. It prevents self-authorization drift.
    In SPEC phase, offer to run spec validation instead of implementation.
    """
    phase = state.get("platform_phase", "SPEC")
    halt = state.get("autonomous_halt", "true").lower()

    if halt == "true":
        record_evidence("autonomous_halt_active", reason="AUTONOMOUS_HALT=true in PROJECT_STATE.md")
        set_output("halt", "true")
        set_output("result", "SKIPPED")
        print("  HALT: AUTONOMOUS_HALT=true — no execution (C-001 Human Override)")
        sys.exit(0)

    if phase == "SPEC":
        print("  INFO: platform_phase=SPEC — running spec validation mode (no src/ operations)")
        record_evidence("spec_phase_validation_mode", platform_phase=phase)
        run_spec_validation()
        set_output("halt", "false")
        set_output("result", "SPEC_VALIDATION_COMPLETE")
        sys.exit(0)

    if phase != "IMPLEMENTATION":
        record_evidence("platform_phase_gate_blocked", platform_phase=phase,
                        reason=f"platform_phase={phase}, not IMPLEMENTATION.")
        set_output("halt", "true")
        set_output("result", "SKIPPED")
        print(f"  HALT: platform_phase={phase}. Must be IMPLEMENTATION to execute.")
        sys.exit(0)


def run_spec_validation() -> None:
    """
    GAP-SIM-08 fix: SPEC-phase useful work.
    When platform_phase=SPEC, the agent validates spec consistency instead of doing nothing.
    Zero LLM cost — pure Python checks.
    """
    print("\n── SPEC Phase Validation Mode ──────────────────────────────────────")
    issues = []

    # Check 1: SPRINT_STATE_MACHINE health
    try:
        state = parse_sprint_state()
        print(f"  ✓ SPRINT_STATE_MACHINE parseable: phase={state.get('platform_phase')}, "
              f"sprint={state.get('current_sprint')}")
    except Exception as e:
        issues.append(f"SPRINT_STATE_MACHINE parse error: {e}")
        state = {}

    # Check 2: Work contract exists
    sprint = state.get("current_sprint", "")
    wc_paths = list(REPO_ROOT.glob(f"work-contracts/{sprint}*.md")) if sprint else []
    if wc_paths:
        print(f"  ✓ Work contract found: {wc_paths[0].name}")
    else:
        issues.append(f"No work contract found for sprint {sprint}")

    # Check 3: build_sprint_index.py can run without errors
    try:
        result = run([sys.executable, "scripts/build_sprint_index.py", "--dry-run", "--no-copilotignore"],
                    check=False, capture=True)
        if result.returncode == 0 or "token budget" in result.stdout.lower():
            print("  ✓ Sprint index builder: parseable")
        else:
            issues.append(f"Sprint index builder error: {result.stderr[:200]}")
    except Exception as e:
        issues.append(f"Sprint index builder exception: {e}")

    # Check 4: Key spec files exist
    required_specs = [
        "constitution/AGENT-ENTRY.md",
        "adr/ADR-INDEX.md",
        "tests/QA-STRATEGY.md",
        "standards/CODING-STANDARDS.md",
    ]
    for spec in required_specs:
        if (REPO_ROOT / spec).exists():
            print(f"  ✓ Spec exists: {spec}")
        else:
            issues.append(f"Required spec missing: {spec}")

    # Report
    if issues:
        print(f"\n  SPEC VALIDATION: {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"    - {issue}")
        record_evidence("spec_validation_issues", count=len(issues), issues=issues)
    else:
        print("\n  SPEC VALIDATION: All checks passed. Platform ready for implementation when Founder authorizes.")
        record_evidence("spec_validation_passed")

    print("── End Spec Validation ──────────────────────────────────────────────\n")


def update_sprint_state(**kwargs) -> None:
    """Update fields in SPRINT_STATE_MACHINE via sprint_state.py."""
    pairs = []
    for k, v in kwargs.items():
        pairs += [k, f'"{v}"' if " " in str(v) else str(v)]
    run([sys.executable, "scripts/sprint_state.py", "set"] + pairs)


def run_runner_integrity_checks(
    namespace: dict | None = None,
) -> tuple[bool, list[str]]:
    """
    Fail-fast checks for internal runner wiring.

    Catches pipeline bugs (missing helper function definitions) before any
    sprint task execution starts.

    Pass namespace=globals() from the caller (autonomous_sprint_runner.py main())
    so the check inspects the fully-assembled module namespace — not this module's
    own limited globals.
    """
    if namespace is None:
        namespace = {}

    errors: list[str] = []

    required_callables = [
        "parse_llm_files",
        "write_llm_files",
        "validate_written_files",
        "execute_with_llm",
    ]
    for symbol in required_callables:
        candidate = namespace.get(symbol)
        if not callable(candidate):
            errors.append(f"Missing or non-callable symbol: {symbol}")

    execute_fn = namespace.get("execute_with_llm")
    if callable(execute_fn):
        params = list(inspect.signature(execute_fn).parameters.keys())
        required_params = ["task_id", "task_description", "spec_sections", "constitutional_check"]
        missing = [p for p in required_params if p not in params]
        if missing:
            errors.append("execute_with_llm signature mismatch. Missing params: " + ", ".join(missing))

    handlers = namespace.get("TASK_HANDLERS")
    if not isinstance(handlers, dict):
        errors.append("TASK_HANDLERS missing or not a dict")
    # Note: TASK_HANDLERS may be empty at startup — groomer injects entries at runtime.

    parser = namespace.get("parse_llm_files")
    if callable(parser):
        probe = (
            '<file path="src/_integrity_probe.txt">ok</file>'
            '<file path="constitution/should-never-pass.md">blocked</file>'
        )
        parsed = parser(probe)
        if "src/_integrity_probe.txt" not in parsed:
            errors.append("parse_llm_files failed to parse valid probe block")
        if any(path.startswith("constitution/") for path in parsed.keys()):
            errors.append("parse_llm_files boundary enforcement failed for constitution/")

    return len(errors) == 0, errors


# ── ADR-041 P2a: Heartbeat file ────────────────────────────────────────────────

_HEARTBEAT_PATH = REPO_ROOT / "logs" / "run-heartbeat.json"


def write_run_heartbeat(run_id: str, sprint: str) -> None:
    """Write OPEN heartbeat at run start (ADR-041 §6 — container-kill detection).

    Pattern: { status: 'OPEN', run_id, sprint, started_at }
    A heartbeat with status=OPEN on the next run means the prior container
    was killed before CLOSE completed (P2b RESUME detection).
    """
    _HEARTBEAT_PATH.parent.mkdir(exist_ok=True)
    _HEARTBEAT_PATH.write_text(
        json.dumps({
            "status": "OPEN",
            "run_id": run_id,
            "sprint": sprint,
            "started_at": datetime.now(tz=timezone.utc).isoformat(),
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def close_run_heartbeat(run_id: str, sprint: str, result: str) -> None:
    """Write CLOSED heartbeat at run end — signals clean completion.

    Called by complete_sprint.py as the very last step before exit.
    A missing close (status still OPEN) indicates container kill.
    """
    _HEARTBEAT_PATH.parent.mkdir(exist_ok=True)
    _HEARTBEAT_PATH.write_text(
        json.dumps({
            "status": "CLOSED",
            "run_id": run_id,
            "sprint": sprint,
            "result": result,
            "closed_at": datetime.now(tz=timezone.utc).isoformat(),
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_run_heartbeat() -> dict:
    """Return the current heartbeat dict, or {} if no heartbeat file exists."""
    if not _HEARTBEAT_PATH.exists():
        return {}
    try:
        return json.loads(_HEARTBEAT_PATH.read_text(encoding="utf-8").strip())
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
