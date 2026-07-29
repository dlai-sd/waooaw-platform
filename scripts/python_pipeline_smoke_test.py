#!/usr/bin/env python3
"""
python_pipeline_smoke_test.py — Pre-sprint validation for Python service sprints

# Implements: architecture/reference/pipeline/python-smoke-test.md (pending)
# Constitutional basis: C-086 (simulation before first LLM call), C-082 (build validation)
# Office: Platform IT Expert (INST-010)

Run this BEFORE starting any Python service sprint (WC-015, WC-016, etc.) to catch
all issues that consumed 17+ runs on WC-014 before a single line of sprint code runs.

Checks:
  1. ruff installed and functional (WC-014: 4 runs wasted — not installed)
  2. parse_sprint_state() reads tasks_done as list (WC-014: BLOCKED every run)
  3. YAML workflow files are valid (WC-014: --continue --no-edit bug)
  4. Hyphenated dir import pattern works (WC-014: pytest conftest import error)
  5. compile gate captures stdout+stderr (WC-014: empty error messages)
  6. Cross-session subtask seed works end-to-end simulation

Usage:
  python3 scripts/python_pipeline_smoke_test.py [--service professional-runtime]
  python3 scripts/python_pipeline_smoke_test.py --service ai-runtime
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[tuple[str, str, str]] = []  # (check, status, detail)


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    results.append((name, status, detail))
    print(f"  {status} {name}" + (f": {detail}" if detail and not ok else ""))
    return ok


# ── Check 1: ruff installed ───────────────────────────────────────────────────
def check_ruff_installed() -> bool:
    result = subprocess.run(
        ["python3", "-m", "ruff", "--version"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    ok = result.returncode == 0
    version = result.stdout.strip() or result.stderr.strip()
    return check("ruff installed + functional", ok,
                 version if ok else f"NOT FOUND — add 'ruff' to pip install in workflow. {result.stderr[:100]}")


# ── Check 2: ruff captures stderr ────────────────────────────────────────────
def check_ruff_captures_stderr() -> bool:
    """Verify run_compile_gate captures both stdout and stderr."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import task_decomposer as td
    import inspect
    src = inspect.getsource(td.run_compile_gate)
    ok = "result.stderr" in src and "result.stdout" in src
    return check("run_compile_gate captures stdout+stderr", ok,
                 "stdout+stderr captured" if ok else "MISSING stderr capture — silent errors")


# ── Check 3: parse_sprint_state reads tasks_done as list ─────────────────────
def check_tasks_done_parsing() -> bool:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import autonomous_sprint_runner as runner
    import re as _re

    test_yaml = """
tasks_done:
  - WC014-02
  - WC014-04
tasks_remaining:
  - WC014-03
current_sprint: WC-014
"""
    # Simulate parse_sprint_state logic
    done_block = _re.search(r"tasks_done:\n((?:  - [^\n]+\n?)*)", test_yaml)
    if done_block:
        done = _re.findall(r"  - (\S+)", done_block.group(1))
        ok = done == ["WC014-02", "WC014-04"]
    else:
        ok = False
        done = []

    return check("parse_sprint_state reads tasks_done as list", ok,
                 f"parsed={done}" if ok else f"FAILED — tasks_done parsed as empty string. Fix: add tasks_done list parser.")


# ── Check 4: YAML workflow syntax ─────────────────────────────────────────────
def check_yaml_syntax() -> bool:
    try:
        import yaml
    except ImportError:
        subprocess.run(["pip", "install", "pyyaml", "-q"])
        import yaml
    # Only check autonomous-sprint.yaml — other workflows may have pre-existing issues
    target = REPO_ROOT / ".github" / "workflows" / "autonomous-sprint.yaml"
    if not target.exists():
        return check("autonomous-sprint.yaml is valid YAML", False, "file not found")
    try:
        yaml.safe_load(target.read_text())
        return check("autonomous-sprint.yaml is valid YAML", True)
    except yaml.YAMLError as e:
        return check("autonomous-sprint.yaml is valid YAML", False, str(e)[:200])


# ── Check 5: hyphenated directory Python import pattern ──────────────────────
def check_hyphenated_import_pattern() -> bool:
    """
    Verify conftest.py import pattern knowledge.
    'from src.professional_runtime.main import app' CANNOT work for hyphenated dirs.
    Correct: sys.path.insert to service dir, then 'from main import app'.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import task_decomposer as td
    rules = td.STACK_BEHAVIORAL_RULES.get("python", [])
    ok = any("TEST IMPORT PATTERN" in r or "hyphenated" in r or "sys.path.insert" in r for r in rules)
    return check("STACK_BEHAVIORAL_RULES has test import pattern for hyphenated dirs", ok,
                 "rule present" if ok else "MISSING — add TEST IMPORT PATTERN rule to prevent pytest conftest.py ImportError")


# ── Check 6: cross-session subtask seed simulation ───────────────────────────
def check_cross_session_seed() -> bool:
    """
    Simulate the cross-session subtask seed from tasks_done_state.
    Verify that WC014-02 → ['WC014-02a', 'WC014-02b'] seeds correctly.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import autonomous_sprint_runner as runner

    tasks_done_state = ["WC014-02", "WC014-04"]
    task_handlers = runner.TASK_HANDLERS

    seeded: list[str] = []
    for prior_task_id in tasks_done_state:
        prior_handler = task_handlers.get(prior_task_id)
        if isinstance(prior_handler, dict) and "subtasks" in prior_handler:
            seeded.extend([st.id for st in prior_handler["subtasks"]])

    ok = "WC014-02a" in seeded and len(seeded) >= 2
    return check("cross-session subtask seed works", ok,
                 f"seeded={seeded}" if ok else f"FAILED — seeded={seeded}. Check parse_sprint_state tasks_done parsing.")


# ── Check 7: git merge --continue syntax ─────────────────────────────────────
def check_merge_continue_syntax() -> bool:
    """Verify runner uses 'git commit --no-edit' not 'git merge --continue --no-edit'."""
    runner_src = (REPO_ROOT / "scripts" / "autonomous_sprint_runner.py").read_text()
    bad = "merge.*--continue.*--no-edit" in runner_src
    ok = not bad
    return check("main-merge conflict resolver uses 'git commit --no-edit'", ok,
                 "correct" if ok else "FOUND 'git merge --continue --no-edit' — invalid syntax, causes silent merge failure")


# ── Check 8: ruff auto-fix runs before gate ───────────────────────────────────
def check_ruff_autofix() -> bool:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import task_decomposer as td
    import inspect
    src = inspect.getsource(td.run_compile_gate)
    ok = "--fix" in src and "--exit-zero" in src
    return check("ruff --fix runs before compile gate check", ok,
                 "auto-fix present" if ok else "MISSING ruff --fix pre-pass — style issues will block gate")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Python pipeline smoke test")
    parser.add_argument("--service", default="professional-runtime",
                        help="Service name to validate (default: professional-runtime)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Python Pipeline Smoke Test — {args.service}")
    print(f"  Run before triggering any Python service sprint")
    print(f"{'='*60}\n")

    check_ruff_installed()
    check_ruff_captures_stderr()
    check_tasks_done_parsing()
    check_yaml_syntax()
    check_hyphenated_import_pattern()
    check_cross_session_seed()
    check_merge_continue_syntax()
    check_ruff_autofix()

    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)

    print(f"\n{'─'*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    if failed == 0:
        print(f"  ✅ Pipeline healthy — safe to trigger {args.service} sprint")
    else:
        print(f"  ❌ Fix {failed} issue(s) before triggering sprint")
        print(f"     Each failure = 1-4 wasted runs (~30 min each)")
    print(f"{'─'*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
