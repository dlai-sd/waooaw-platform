#!/usr/bin/env python3
# # Implements: adr/ADR-037-sprint-environment-contract-validation.md
# Constitutional basis: C-032 (spec/code drift), C-086 (pre-execution gate), C-077 (dev cost ceiling)
"""
Environment Contract Validator — pre-sprint dependency gate.

Scans all imports in tests/ and validates each non-stdlib module is importable
in the current CI environment. Exits 1 on any gap, halting the sprint before
any LLM token is spent.
"""

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"


def _collect_local_modules() -> set[str]:
    """Module names that exist as files or packages within this repo.

    These are resolvable by conftest.py sys.path injection — not PyPI packages.
    Excluding them prevents false-positive failures on local scripts/service files.
    """
    local: set[str] = set()
    for root in [REPO_ROOT / "scripts", REPO_ROOT / "src", REPO_ROOT]:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if py.stem not in ("__init__", "__main__"):
                local.add(py.stem)
        for init in root.rglob("__init__.py"):
            local.add(init.parent.name)
    return local


def collect_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                modules.add(node.module.split(".")[0])
    return modules


def check_importable(name: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        capture_output=True,
        timeout=15,
    )
    return result.returncode == 0


def main() -> int:
    py_files = list(TESTS_DIR.rglob("*.py"))
    if not py_files:
        print("  env_validator: no test files found — skipping")
        return 0

    print(f"\n── Environment Contract Validator (ADR-037) ────────────────────────────")
    print(f"  Scanning {len(py_files)} test file(s)...")

    all_modules: set[str] = set()
    for f in py_files:
        all_modules.update(collect_imports(f))

    # sys.stdlib_module_names available from Python 3.10+
    stdlib: set[str] = sys.stdlib_module_names  # type: ignore[attr-defined]
    local_modules = _collect_local_modules()
    third_party = sorted(
        m for m in all_modules
        if m not in stdlib and m not in local_modules and m
    )

    gaps: list[str] = []
    for module in third_party:
        ok = check_importable(module)
        print(f"  {'✅' if ok else '❌'} {module}")
        if not ok:
            gaps.append(module)

    if gaps:
        print(f"\n  ❌ CRITICAL: {len(gaps)} module(s) not importable: {gaps}")
        print(f"  Add missing packages to requirements-test.txt and re-run.")
        print(f"  Constitutional: C-032 (spec/code drift), C-086 (pre-execution gate)")
        return 1

    print(f"\n  ✅ Environment contract valid — {len(third_party)} module(s) verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
