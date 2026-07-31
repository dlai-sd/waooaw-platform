#!/usr/bin/env python3
"""
check_arch_fitness.py — Architectural Fitness Functions (QA Technique #3)

constitutional_basis: C-059 (Traceability), ADR-016 (service language selection)
office: Platform IT Expert
Called by: autonomous-sprint.yaml post-execution job (before PR creation)

Enforces structural invariants on the billing-engine service layer:
  1. No cross-layer imports (billing-engine must not import from ai-runtime or bp)
  2. Each billing-engine sub-package with a service.py has a corresponding test file
  3. No wildcard imports (`from X import *`) in service files
  4. Each sub-package with a service.py also has a models.py (layered structure)

Exit 0 = all fitness functions pass. Exit 1 = structural violation; block PR.
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BILLING_ENGINE_SRC = REPO_ROOT / "src" / "billing-engine"
BILLING_ENGINE_TESTS = REPO_ROOT / "tests" / "billing-engine"

# Forbidden cross-layer import prefixes
FORBIDDEN_CROSS_LAYER = [
    "ai_runtime", "ai-runtime",
    "bp.", "business_platform",
]

# Sub-package directories to exclude from structural checks (infra, not services)
INFRA_DIRS = {"__pycache__", "skeleton", ".venv"}


def _find_service_packages() -> list[Path]:
    """Return billing-engine sub-package dirs that contain a service.py."""
    if not BILLING_ENGINE_SRC.exists():
        return []
    return [
        d for d in BILLING_ENGINE_SRC.iterdir()
        if d.is_dir()
        and d.name not in INFRA_DIRS
        and (d / "service.py").exists()
    ]


def _find_all_py_files() -> list[Path]:
    if not BILLING_ENGINE_SRC.exists():
        return []
    return [
        f for f in BILLING_ENGINE_SRC.rglob("*.py")
        if not any(part in INFRA_DIRS for part in f.parts)
    ]


def _check_cross_layer_imports(py_files: list[Path]) -> list[str]:
    """Return list of violations: billing-engine files that import from forbidden layers."""
    violations = []
    for path in py_files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue  # compile errors are caught by check_import_chain
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                else:
                    names = [node.module or ""]
                for name in names:
                    for forbidden in FORBIDDEN_CROSS_LAYER:
                        if name.startswith(forbidden):
                            violations.append(
                                f"{path.relative_to(REPO_ROOT)}: "
                                f"cross-layer import '{name}' (forbidden: {forbidden})"
                            )
    return violations


def _check_wildcard_imports(py_files: list[Path]) -> list[str]:
    """Return violations: service files with wildcard imports."""
    violations = []
    for path in py_files:
        if path.name not in ("service.py", "models.py", "router.py", "bundle_engine.py"):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}: "
                            f"wildcard import 'from {node.module} import *'"
                        )
    return violations


def _check_test_coverage(packages: list[Path]) -> list[str]:
    """Return violations: service packages that lack a corresponding test file."""
    violations = []
    for pkg in packages:
        test_file = BILLING_ENGINE_TESTS / f"test_{pkg.name}.py"
        if not test_file.exists():
            violations.append(
                f"No test file for service package '{pkg.name}': "
                f"expected {test_file.relative_to(REPO_ROOT)}"
            )
    return violations


def _check_models_present(packages: list[Path]) -> list[str]:
    """Return violations: service packages that have service.py but no models.py."""
    violations = []
    for pkg in packages:
        if not (pkg / "models.py").exists():
            violations.append(
                f"Service package '{pkg.name}' has service.py but no models.py "
                f"(required by layered structure convention)"
            )
    return violations


def main() -> int:
    print("── Architectural Fitness Functions ───────────────────────────")

    if not BILLING_ENGINE_SRC.exists():
        print(f"  ℹ️  {BILLING_ENGINE_SRC} not yet created — skipping (new project)")
        return 0

    py_files = _find_all_py_files()
    packages = _find_service_packages()

    print(f"  Checking {len(py_files)} Python files across {len(packages)} service package(s)")

    all_violations: list[str] = []

    # Rule 1: no cross-layer imports
    cross = _check_cross_layer_imports(py_files)
    if cross:
        for v in cross:
            print(f"  ❌ [cross-layer] {v}")
        all_violations.extend(cross)
    else:
        print("  ✅ No cross-layer imports")

    # Rule 2: no wildcard imports in service files
    wildcards = _check_wildcard_imports(py_files)
    if wildcards:
        for v in wildcards:
            print(f"  ❌ [wildcard] {v}")
        all_violations.extend(wildcards)
    else:
        print("  ✅ No wildcard imports in service files")

    # Rule 3: each service package has a test file
    missing_tests = _check_test_coverage(packages)
    if missing_tests:
        for v in missing_tests:
            print(f"  ❌ [test-coverage] {v}")
        all_violations.extend(missing_tests)
    else:
        print(f"  ✅ All {len(packages)} service package(s) have test files")

    # Rule 4: each service package has models.py
    missing_models = _check_models_present(packages)
    if missing_models:
        for v in missing_models:
            print(f"  ❌ [structure] {v}")
        all_violations.extend(missing_models)
    else:
        print(f"  ✅ All {len(packages)} service package(s) have models.py")

    if all_violations:
        print(f"\n  ❌ Architecture fitness: {len(all_violations)} violation(s) found.")
        print("  Resolve structural issues before creating PR.")
        return 1

    print("  ✅ All architectural fitness functions pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
