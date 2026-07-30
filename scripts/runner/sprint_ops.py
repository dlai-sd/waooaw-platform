# Implements: scripts/runner/sprint_ops.py
# constitutional_basis: C-001 (Human Override), C-059 (Traceability), C-065 (SDLC Separation)
# ib_item: IB-009
"""
Sprint state operations: parse, gate checks, spec validation, integrity checks.
"""
from __future__ import annotations

import inspect
import re
import sys

from runner.constants import REPO_ROOT, STATE_FILE
from runner.git_ops import record_evidence, run, set_output


def parse_sprint_state() -> dict:
    """Extract SPRINT_STATE_MACHINE YAML block from PROJECT_STATE.md."""
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

    # Parse tasks_remaining list (YAML list format: "  - WC014-02")
    tasks_block = re.search(
        r"tasks_remaining:\n((?:  - [^\n]+\n?)*)",
        match.group(1)
    )
    if tasks_block:
        tasks = re.findall(r"  - (\S+)", tasks_block.group(1))
        state["tasks_remaining"] = [t for t in tasks if not t.startswith("#")]
    else:
        state["tasks_remaining"] = []

    # Parse tasks_done list
    done_block = re.search(
        r"tasks_done:\n((?:  - [^\n]+\n?)*)",
        match.group(1)
    )
    if done_block:
        done = re.findall(r"  - (\S+)", done_block.group(1))
        state["tasks_done"] = [t for t in done if not t.startswith("#")]
    else:
        state["tasks_done"] = []

    return state


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
    if not isinstance(handlers, dict) or len(handlers) == 0:
        errors.append("TASK_HANDLERS missing or empty")

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
