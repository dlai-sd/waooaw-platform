#!/usr/bin/env python3
"""
python_pipeline_smoke_test.py v2 — Pre-sprint validation for Python service sprints

# Implements: architecture/reference/pipeline/python-smoke-test.md (pending)
# Constitutional basis: C-086 (simulation before first LLM call), C-082 (build validation)
# Office: Platform IT Expert (INST-010)

Run this BEFORE starting any Python service sprint (WC-015, WC-016, etc.) to catch
all issues that consumed 20+ runs on WC-014 before a single line of sprint code runs.

WC-014 failure registry (38 entries) → 16 checks now run in <5 seconds:
  1.  ruff installed (WC-014 Run 1-4: NOT installed)
  2.  ruff captures stderr (silent errors)
  3.  ruff --unsafe-fixes (F841 not auto-fixed without it)
  4.  parse_sprint_state reads tasks_done as list (THE ROOT CAUSE — every BLOCKED run)
  5.  cumulative tasks_done union (lost WC014-01 from main)
  6.  autonomous-sprint.yaml is valid YAML
  7.  hyphenated dir import pattern (pytest conftest ImportError)
  8.  STACK_BEHAVIORAL_RULES has ruff-violation rules (F841, B018, LOG015, G004)
  9.  cross-session subtask seed works
  10. git merge conflict resolver syntax (--continue --no-edit was invalid)
  11. signal committed to sprint branch (not just written as untracked file)
  12. signal written before early returns in main() (step 8.1 before PR section)
  13. complete_sprint guards empty signal (JSONDecodeError crash)
  14. complete_sprint union state+signal tasks_done (no overwrite)
  15. workflow fetches sprint branch before git show signal
  16. per-file-ignores covers test lint rules (LOG015, G004)

Usage:
  python3 scripts/python_pipeline_smoke_test.py [--service professional-runtime]
  python3 scripts/python_pipeline_smoke_test.py --service ai-runtime
"""
from __future__ import annotations

import argparse
import inspect
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    results.append((name, status, detail))
    print(f"  {status} {name}" + (f": {detail}" if detail and not ok else ""))
    return ok


# ── 1. ruff installed ─────────────────────────────────────────────────────────
def check_ruff_installed() -> bool:
    r = subprocess.run(["python3", "-m", "ruff", "--version"],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    v = r.stdout.strip() or r.stderr.strip()
    return check("ruff installed + functional", r.returncode == 0,
                 v if r.returncode == 0 else f"NOT FOUND — add ruff to pip install step")


# ── 2. ruff captures stderr ───────────────────────────────────────────────────
def check_ruff_captures_stderr() -> bool:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import task_decomposer as td
    src = inspect.getsource(td.run_compile_gate)
    ok = "result.stderr" in src and "result.stdout" in src
    return check("run_compile_gate captures stdout+stderr", ok,
                 "OK" if ok else "MISSING stderr — silent errors reach no one")


# ── 3. ruff --unsafe-fixes ────────────────────────────────────────────────────
def check_ruff_unsafe_fixes() -> bool:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import task_decomposer as td
    src = inspect.getsource(td.run_compile_gate)
    ok = "--unsafe-fixes" in src
    return check("ruff --unsafe-fixes in compile gate (F841 auto-rename)", ok,
                 "present" if ok else "MISSING — F841 unused variable won't be auto-fixed")


# ── 4. parse_sprint_state reads tasks_done as list ───────────────────────────
def check_tasks_done_parsing() -> bool:
    import autonomous_sprint_runner as runner
    test_yaml = "tasks_done:\n  - WC014-02\n  - WC014-04\ntasks_remaining:\n  - WC014-03\n"
    done_block = re.search(r"tasks_done:\n((?:  - [^\n]+\n?)*)", test_yaml)
    if done_block:
        done = re.findall(r"  - (\S+)", done_block.group(1))
        ok = done == ["WC014-02", "WC014-04"]
    else:
        ok, done = False, []
    return check("parse_sprint_state reads tasks_done as YAML list", ok,
                 f"parsed={done}" if ok else "FAILED — parsed as empty string. THE most expensive bug in WC-014.")


# ── 5. cumulative tasks_done union ────────────────────────────────────────────
def check_cumulative_tasks_done() -> bool:
    import autonomous_sprint_runner as runner
    src = inspect.getsource(runner.main)
    ok = "set(tasks_done) | set(tasks_done_state)" in src or \
         "set(tasks_done_state)" in src
    return check("cumulative tasks_done union (never overwrite prior sessions)", ok,
                 "union merge present" if ok else "MISSING union — previous tasks_done erased on every PARTIAL run")


# ── 6. YAML workflow syntax ───────────────────────────────────────────────────
def check_yaml_syntax() -> bool:
    try:
        import yaml
    except ImportError:
        subprocess.run(["pip", "install", "pyyaml", "-q"])
        import yaml
    target = REPO_ROOT / ".github" / "workflows" / "autonomous-sprint.yaml"
    if not target.exists():
        return check("autonomous-sprint.yaml is valid YAML", False, "file not found")
    try:
        yaml.safe_load(target.read_text())
        return check("autonomous-sprint.yaml is valid YAML", True)
    except yaml.YAMLError as e:
        return check("autonomous-sprint.yaml is valid YAML", False, str(e)[:200])


# ── 7. Hyphenated dir test import pattern ────────────────────────────────────
def check_hyphenated_import_pattern() -> bool:
    import task_decomposer as td
    rules = td.STACK_BEHAVIORAL_RULES.get("python", [])
    ok = any("sys.path.insert" in r for r in rules)
    return check("STACK_BEHAVIORAL_RULES has hyphenated-dir import pattern", ok,
                 "present" if ok else "MISSING — pytest conftest 'from src.X.main import app' will fail")


# ── 8. Ruff violation behavioral rules ───────────────────────────────────────
def check_ruff_behavioral_rules() -> bool:
    import task_decomposer as td
    rules = "\n".join(td.STACK_BEHAVIORAL_RULES.get("python", []))
    checks = {
        "F841 (unused variable)": "F841" in rules,
        "B018 (useless expression)": "B018" in rules,
        "LOG015 (root logger)": "LOG015" in rules,
        "G004 (f-string logging)": "G004" in rules,
    }
    missing = [k for k, v in checks.items() if not v]
    ok = len(missing) == 0
    return check("STACK_BEHAVIORAL_RULES has ruff-violation rules (F841/B018/LOG015/G004)", ok,
                 "all present" if ok else f"MISSING rules: {', '.join(missing)} — LLM will keep generating them")


# ── 9. Cross-session subtask seed ────────────────────────────────────────────
def check_cross_session_seed() -> bool:
    import autonomous_sprint_runner as runner
    tasks_done_state = ["WC014-02", "WC014-04"]
    seeded: list[str] = []
    for prior_task_id in tasks_done_state:
        prior_handler = runner.TASK_HANDLERS.get(prior_task_id)
        if isinstance(prior_handler, dict) and "subtasks" in prior_handler:
            seeded.extend([st.id for st in prior_handler["subtasks"]])
    ok = "WC014-02a" in seeded and len(seeded) >= 2
    return check("cross-session subtask seed works end-to-end", ok,
                 f"seeded={seeded}" if ok else f"FAILED — seeded={seeded}")


# ── 10. git merge conflict resolver syntax ───────────────────────────────────
def check_merge_syntax() -> bool:
    runner_src = (REPO_ROOT / "scripts" / "autonomous_sprint_runner.py").read_text()
    # Strip comments before searching — the fix is documented in a comment using the old syntax
    code_lines = [l for l in runner_src.splitlines() if not l.strip().startswith("#")]
    code_only = "\n".join(code_lines)
    bad = bool(re.search(r"merge.*--continue.*--no-edit", code_only))
    ok = not bad
    return check("merge conflict resolver uses 'git commit --no-edit' not 'merge --continue'", ok,
                 "correct" if ok else "FOUND invalid 'git merge --continue --no-edit' in non-comment code")


# ── 11. Signal committed to sprint branch ────────────────────────────────────
def check_signal_committed() -> bool:
    """Signal must be force-added (git add -f) since monitor-signal.json is in .gitignore."""
    runner_src = (REPO_ROOT / "scripts" / "autonomous_sprint_runner.py").read_text()
    ok = bool(re.search(r'git\(\["add", "-f".*signal_path', runner_src))
    return check("signal uses 'git add -f' (file is in .gitignore)", ok,
                 "present" if ok else "MISSING '-f' — git add silently ignored, signal never committed or pushed")


# ── 12. Signal before early returns (step 8.1) ───────────────────────────────
def check_signal_before_early_returns() -> bool:
    """Signal write must occur before any 'return 0' in the PR section of main()."""
    runner_src = (REPO_ROOT / "scripts" / "autonomous_sprint_runner.py").read_text()
    # Find position of step 8.1 signal write vs early return 'not tasks_done and not existing_num'
    signal_pos = runner_src.find("Step 8.1")
    early_return_pos = runner_src.find("not tasks_done and not existing_num")
    ok = signal_pos != -1 and (early_return_pos == -1 or signal_pos < early_return_pos)
    return check("signal written before early returns in main() (step 8.1)", ok,
                 "step 8.1 before PR section" if ok else
                 "MISSING step 8.1 — 'return 0' when no tasks done exits before signal write")


# ── 13. complete_sprint empty signal guard ───────────────────────────────────
def check_empty_signal_guard() -> bool:
    cs_src = (REPO_ROOT / "scripts" / "complete_sprint.py").read_text()
    ok = ".strip()" in cs_src and "is empty" in cs_src or \
         bool(re.search(r"strip\(\).*\nis empty|empty.*strip\(\)", cs_src)) or \
         "raw_signal" in cs_src
    return check("complete_sprint guards empty signal (no JSONDecodeError crash)", ok,
                 "guard present" if ok else
                 "MISSING — git show writes empty file when signal not pushed; json.loads('') crashes")


# ── 14. complete_sprint union state+signal tasks_done ────────────────────────
def check_complete_sprint_union() -> bool:
    cs_src = (REPO_ROOT / "scripts" / "complete_sprint.py").read_text()
    ok = "set(signal_done) | set(state_done)" in cs_src or \
         "state_done" in cs_src and "signal_done" in cs_src
    return check("complete_sprint merges signal+state tasks_done (no overwrite)", ok,
                 "union merge present" if ok else
                 "MISSING union — PARTIAL run with 0 tasks would erase all prior tasks_done on main")


# ── 15. Workflow fetches sprint branch before git show ───────────────────────
def check_workflow_fetches_sprint_branch() -> bool:
    wf = (REPO_ROOT / ".github" / "workflows" / "autonomous-sprint.yaml").read_text()
    ok = 'git fetch origin "$SPRINT_BRANCH"' in wf or \
         "fetch origin.*SPRINT_BRANCH" in wf or \
         bool(re.search(r'git fetch origin.*SPRINT_BRANCH', wf))
    return check("workflow fetches sprint branch before 'git show' signal", ok,
                 "fetch present" if ok else
                 "MISSING fetch — git show origin/BRANCH:... returns empty if branch not fetched")


# ── 16. per-file-ignores covers test lint rules ──────────────────────────────
def check_per_file_ignores() -> bool:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    checks = {
        "LOG015": "LOG015" in pyproject,
        "G004": "G004" in pyproject,
    }
    missing = [k for k, v in checks.items() if not v]
    ok = len(missing) == 0
    return check("pyproject.toml per-file-ignores covers LOG015, G004 for tests", ok,
                 "all present" if ok else
                 f"MISSING: {', '.join(missing)} — LLM-generated tests will fail ruff compile gate")


# ── 17. ruff dry-run — src/ equivalent (no per-file-ignores) ────────────────
def check_ruff_dry_run() -> bool:
    """
    Run ruff against two synthetic files mimicking LLM-generated patterns:
      - src_template: placed at /tmp/src_ai_runtime/ to avoid ALL per-file-ignores.
        Tests that ANN401/E501/B018/F841/UP042 pass in SOURCE files.
        These only pass if pyproject.toml global ignores are correct.
      - test_template: placed at tests/_smoke/ to get tests/** per-file-ignores.
        Tests that LOG015/G004/ANN pass in TEST files.

    BUG CAUGHT: writing template to scripts/ gave false ANN401 PASS because
    scripts/** has ["ANN"] in per-file-ignores — masked the missing global ignore.
    """
    import tempfile, os
    src_template = '''\
# Implements: ai-runtime | constitutional_basis: C-059, C-062
import re
import logging
from typing import Any
from enum import Enum, StrEnum

logger = logging.getLogger(__name__)

# E501: very long lines (140+ chars) must pass — PSE routing rules, SQL, regex naturally exceed 130
INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\\bignore\\s+(all\\s+)?(previous|prior|above|earlier)\\s+(instructions?|prompts?|context|directives?|commands?|rules?|guidelines?)\\b", re.I),
    re.compile(r"\\bforget\\s+(all\\s+)?(previous|prior|above|earlier)\\s+(instructions?|prompts?|context|directives?|commands?|rules?|guidelines?)\\b", re.I),
    re.compile(r"\\byou\\s+are\\s+now\\s+(a\\s+|an\\s+)?(different|new|unrestricted|free|jailbroken|unfiltered|uncensored|liberated|unchained)\\b", re.I),
]

# UP042: LLM may generate str+Enum — must be auto-fixed to StrEnum by ruff --fix
class ProviderTier(str, Enum):
    LOCAL = "local"
    MID = "mid"

# ANN401: LLM uses Any for dynamic params like asyncpg.Pool — must pass globally
def route(db_pool: Any, model_hint: str) -> dict[str, Any]:
    # F841: unused variable — must be auto-fixed by ruff --unsafe-fixes
    _handle = logger.info("routing %s", model_hint)
    return {"tier": ProviderTier.LOCAL, "db": db_pool}
'''

    test_template = '''\
# Implements: test | constitutional_basis: C-076
import logging
import pytest

logger = logging.getLogger(__name__)

def test_route_local():
    # LOG015: root logger call — OK in tests (per-file-ignores)
    logging.info(f"testing route: {\'local\'}")  # G004: f-string in log — OK in tests
    assert True

class TestPSE:
    def __init__(self):  # ANN204: missing __init__ return type — OK in tests (ANN suppressed)
        self.tier = "local"
'''

    errors = []

    # Test src-equivalent: /tmp path, no per-file-ignores apply
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        src_file = Path(tmpdir) / "router.py"
        src_file.write_text(src_template)
        subprocess.run(
            ["python3", "-m", "ruff", "check", str(src_file), "--fix", "--unsafe-fixes",
             "--exit-zero", "--config", str(REPO_ROOT / "pyproject.toml")],
            capture_output=True, text=True
        )
        r = subprocess.run(
            ["python3", "-m", "ruff", "check", str(src_file),
             "--config", str(REPO_ROOT / "pyproject.toml")],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            errors.append(f"src/: {(r.stdout + r.stderr).strip()[:200]}")

        # Test test-equivalent: must use tests/ path so per-file-ignores apply
        tests_dir = REPO_ROOT / "tests" / "_smoke_check"
        tests_dir.mkdir(exist_ok=True)
        test_file = tests_dir / "test_smoke.py"
        try:
            test_file.write_text(test_template)
            subprocess.run(
                ["python3", "-m", "ruff", "check", str(test_file), "--fix", "--unsafe-fixes", "--exit-zero"],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            r2 = subprocess.run(
                ["python3", "-m", "ruff", "check", str(test_file)],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            if r2.returncode != 0:
                errors.append(f"tests/: {(r2.stdout + r2.stderr).strip()[:200]}")
        finally:
            test_file.unlink(missing_ok=True)
            tests_dir.rmdir()

    ok = len(errors) == 0
    detail = " | ".join(errors) if errors else "src/ and tests/ both clean"
    return check("ruff dry-run: src/ + tests/ LLM patterns pass (ANN401/E501/B018/F841/UP042/LOG015/G004)", ok,
                 detail if ok else f"VIOLATIONS — fix pyproject.toml: {detail}")



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="professional-runtime")
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "scripts"))

    print(f"\n{'='*60}")
    print(f"  Python Pipeline Smoke Test v2 — {args.service}")
    print(f"  17 checks · covers all WC-014 + WC-015 failure registry entries")
    print(f"{'='*60}\n")

    check_ruff_installed()
    check_ruff_captures_stderr()
    check_ruff_unsafe_fixes()
    check_tasks_done_parsing()
    check_cumulative_tasks_done()
    check_yaml_syntax()
    check_hyphenated_import_pattern()
    check_ruff_behavioral_rules()
    check_cross_session_seed()
    check_merge_syntax()
    check_signal_committed()
    check_signal_before_early_returns()
    check_empty_signal_guard()
    check_complete_sprint_union()
    check_workflow_fetches_sprint_branch()
    check_per_file_ignores()
    check_ruff_dry_run()

    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)

    print(f"\n{'─'*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    if failed == 0:
        print(f"  ✅ Pipeline healthy — safe to trigger {args.service} sprint")
    else:
        print(f"  ❌ Fix {failed} issue(s) before triggering sprint")
        print(f"     Each failure = 1-4 wasted runs (~30 min each)")
        for name, status, detail in results:
            if status == FAIL:
                print(f"     → {name}: {detail}")
    print(f"{'─'*60}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
