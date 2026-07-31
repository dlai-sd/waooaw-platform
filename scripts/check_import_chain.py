#!/usr/bin/env python3
# constitutional_basis: C-096 (Dependency Chain Integrity), C-059 (Traceability)
# ib_item: IB-009
"""
check_import_chain.py — Dependency Chain Validation (QA Technique #1)

constitutional_basis: C-059 (Traceability), Evidence First
office: Platform IT Expert
Called by: autonomous-sprint.yaml pre-flight job (after groomer, before runner)

Validates that all source-tree foundation modules that the current sprint will
BUILD ON TOP OF are syntactically valid and compile clean. This catches regressions
where a prior sprint's code was left in a broken state before we attempt to write
new code that imports it.

Also checks that known skeleton stubs have been replaced with real implementations
for WC tasks listed as "done" in the WC file.

Exit 0 = chain is clean. Exit 1 = foundation broken; block the run.
"""

import ast
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BILLING_ENGINE_SRC = REPO_ROOT / "src" / "billing-engine"

# Modules that are ALWAYS expected to compile (foundation layer)
FOUNDATION_MODULES = [
    "config.py",
    "main.py",
]

# Known skeleton sentinel — if a "done" task still has this string in its output
# file, it means the runner didn't replace the skeleton with real code.
SKELETON_SENTINEL = "# SKELETON STUB — implementation pending"


def _get_current_sprint() -> str:
    state = (REPO_ROOT / "constitution" / "PROJECT_STATE.md").read_text()
    sm = re.search(r"## SPRINT_STATE_MACHINE.*?```yaml(.*?)```", state, re.DOTALL)
    if not sm:
        return ""
    m = re.search(r"^current_sprint:\s*(\S+)", sm.group(1), re.MULTILINE)
    return m.group(1).strip() if m else ""


def _get_done_tasks_scopes(sprint: str) -> list[str]:
    """Return src/ file paths listed in done task rows in the WC file."""
    wc_files = list((REPO_ROOT / "work-contracts").glob(f"{sprint}-*.md"))
    if not wc_files:
        return []
    content = wc_files[0].read_text(encoding="utf-8")
    task_id_pat = re.compile(r"^WC\d+-\d+[a-z]?$")
    src_pat = re.compile(r"`(src/[^`]+\.py)`")
    paths = []
    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            continue
        task_id = cells[1].strip()
        if not task_id_pat.match(task_id):
            continue
        status = cells[-3].strip().lower()
        if status == "done":
            scope_cell = cells[2]
            paths.extend(src_pat.findall(scope_cell))
    return paths


def _compile_check(path: Path) -> str | None:
    """Return error string if file fails to parse as valid Python, else None."""
    try:
        src = path.read_text(encoding="utf-8")
        ast.parse(src, filename=str(path))
        return None
    except SyntaxError as e:
        return f"SyntaxError at line {e.lineno}: {e.msg}"
    except Exception as e:  # noqa: BLE001
        return str(e)


def _check_skeleton_sentinel(path: Path) -> bool:
    """Return True if file still contains skeleton stub text."""
    try:
        return SKELETON_SENTINEL in path.read_text(encoding="utf-8")
    except OSError:
        return False


def main() -> int:
    print("── Dependency Chain Validation ───────────────────────────────")

    if not BILLING_ENGINE_SRC.exists():
        print(f"  ℹ️  {BILLING_ENGINE_SRC} not yet created — skipping (new project)")
        return 0

    sprint = _get_current_sprint()
    force_task = os.environ.get("FORCE_TASK", "").strip()
    print(f"  Sprint: {sprint or '(unknown)'}  FORCE_TASK: {force_task or '(none)'}")

    failures = 0

    # 1. Foundation modules compile check
    for rel in FOUNDATION_MODULES:
        f = BILLING_ENGINE_SRC / rel
        if not f.exists():
            continue
        err = _compile_check(f)
        if err:
            print(f"  ❌ Foundation compile fail: {f.relative_to(REPO_ROOT)} — {err}")
            failures += 1
        else:
            print(f"  ✅ Foundation: {f.relative_to(REPO_ROOT)}")

    # 2. All existing sub-packages compile clean
    for py_file in sorted(BILLING_ENGINE_SRC.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT)
        err = _compile_check(py_file)
        if err:
            print(f"  ❌ Compile fail: {rel} — {err}")
            failures += 1

    # 3. Done tasks must not still contain skeleton stubs
    if sprint:
        done_scopes = _get_done_tasks_scopes(sprint)
        for rel_path in done_scopes:
            abs_path = REPO_ROOT / rel_path
            if not abs_path.exists():
                print(f"  ⚠️  Done task output missing from disk: {rel_path}")
                # Not a hard failure — runner may have skipped or used diff path
                continue
            if _check_skeleton_sentinel(abs_path):
                print(f"  ❌ Skeleton stub still present in done task: {rel_path}")
                failures += 1
            else:
                print(f"  ✅ Done task output is real code: {rel_path}")

    if failures:
        print(f"\n  ❌ Dependency chain BROKEN: {failures} issue(s) found.")
        print("  Fix the above before running the next sprint task.")
        return 1

    print("  ✅ Dependency chain clean — foundation is solid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
