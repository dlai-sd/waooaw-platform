# Implements: C-096 (Dependency Chain Integrity), C-097 (Property-Based Testing),
#             C-098 (Architectural Fitness Functions)
# constitutional_basis: C-096, C-097, C-098, C-059 (Traceability), C-071 (Quality)
# ib_item: IB-009
# office: Platform IT Expert

"""
CCT-QA-01 — QA Technique Constitutional Compliance Tests

Blocking: Yes — these are post-execution structural invariants.
          CCT-ARCH violations block PR merge once billing-engine is complete.
          CCT-PROP violations block any billing-engine test file from merging
          that covers a financial calculation function without @given tests.

Tests:
  CCT-ARCH-01: No cross-layer imports from billing-engine into ai-runtime or bp
  CCT-ARCH-02: No wildcard imports in billing-engine service files
  CCT-ARCH-03: Each billing-engine service package has a corresponding test file
  CCT-ARCH-04: Each billing-engine service package with service.py has models.py
  CCT-PROP-01: Billing-engine test files covering financial functions use @given
"""

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BILLING_ENGINE_SRC = REPO_ROOT / "src" / "billing-engine"
BILLING_ENGINE_TESTS = REPO_ROOT / "tests" / "billing-engine"

INFRA_DIRS = {"__pycache__", "skeleton", ".venv"}
FORBIDDEN_CROSS_LAYER = ["ai_runtime", "ai-runtime", "bp.", "business_platform"]

# Financial calculation modules that MUST have @given tests when they exist
FINANCIAL_MODULES = {"bundle_engine", "markup", "wallet", "meter", "reconciliation", "procurement"}

# Test files committed before C-097 ratification (2026-07-31) — grandfathered.
# These must be retrofitted in a dedicated sprint before G4 CLEAR.
C097_GRANDFATHERED = {
    "test_wallet.py",          # WC-026 — predates C-097; retrofit in WC-027+ cleanup sprint
    "test_thread_catalog.py",  # WC-025 — predates C-097; retrofit in WC-027+ cleanup sprint
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _billing_py_files() -> list[Path]:
    if not BILLING_ENGINE_SRC.exists():
        return []
    return [
        f for f in BILLING_ENGINE_SRC.rglob("*.py")
        if not any(part in INFRA_DIRS for part in f.parts)
    ]


def _service_packages() -> list[Path]:
    if not BILLING_ENGINE_SRC.exists():
        return []
    return [
        d for d in BILLING_ENGINE_SRC.iterdir()
        if d.is_dir() and d.name not in INFRA_DIRS and (d / "service.py").exists()
    ]


def _parse_imports(path: Path) -> list[tuple[str, int]]:
    """Return (module_name, lineno) for every import in the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name or "", node.lineno))
        elif isinstance(node, ast.ImportFrom):
            results.append((node.module or "", node.lineno))
    return results


def _has_given_decorator(path: Path) -> bool:
    """Return True if the file contains at least one @given(...) decorated test."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Name) and func.id == "given":
                        return True
                    if isinstance(func, ast.Attribute) and func.attr == "given":
                        return True
    return False


def _covers_financial_function(path: Path) -> bool:
    """Return True if this test file imports or references financial calculation functions."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    financial_keywords = [
        "derive_price", "validate_price", "cost_floor",
        "debit", "credit", "wallet", "margin", "paise",
        "reconcile", "threshold",
    ]
    return any(kw in content for kw in financial_keywords)


# ── CCT-ARCH-01 ───────────────────────────────────────────────────────────────

class TestCCTArch01CrossLayerImports:
    """CCT-ARCH-01: billing-engine must not import from ai-runtime or bp."""

    def test_no_cross_layer_imports(self) -> None:
        """C-098 Rule 1: billing-engine files must not import from forbidden layers."""
        if not BILLING_ENGINE_SRC.exists():
            pytest.skip("billing-engine src not yet created")

        violations = []
        for path in _billing_py_files():
            for module_name, lineno in _parse_imports(path):
                for forbidden in FORBIDDEN_CROSS_LAYER:
                    if module_name.startswith(forbidden):
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}:{lineno}: "
                            f"imports '{module_name}' (cross-layer, forbidden: {forbidden})"
                        )

        assert not violations, (
            "CCT-ARCH-01 FAIL: cross-layer imports found (C-098 violation):\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\nBilling-engine must not import from ai-runtime or bp layers."
        )


# ── CCT-ARCH-02 ───────────────────────────────────────────────────────────────

class TestCCTArch02WildcardImports:
    """CCT-ARCH-02: no wildcard imports in billing-engine service files."""

    SERVICE_FILE_NAMES = {"service.py", "models.py", "router.py", "bundle_engine.py"}

    def test_no_wildcard_imports_in_service_files(self) -> None:
        """C-098 Rule 2: 'from X import *' is forbidden in service files."""
        if not BILLING_ENGINE_SRC.exists():
            pytest.skip("billing-engine src not yet created")

        violations = []
        for path in _billing_py_files():
            if path.name not in self.SERVICE_FILE_NAMES:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == "*":
                            violations.append(
                                f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                                f"'from {node.module} import *'"
                            )

        assert not violations, (
            "CCT-ARCH-02 FAIL: wildcard imports found (C-098 violation):\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\nWildcard imports make dependencies opaque. Use explicit imports."
        )


# ── CCT-ARCH-03 ───────────────────────────────────────────────────────────────

class TestCCTArch03TestFileCompleteness:
    """CCT-ARCH-03: every billing-engine service package must have a test file."""

    def test_service_packages_have_test_files(self) -> None:
        """C-098 Rule 3: test file required per service package."""
        if not BILLING_ENGINE_SRC.exists():
            pytest.skip("billing-engine src not yet created")

        packages = _service_packages()
        if not packages:
            pytest.skip("no service packages with service.py yet")

        missing = []
        for pkg in packages:
            test_file = BILLING_ENGINE_TESTS / f"test_{pkg.name}.py"
            if not test_file.exists():
                missing.append(
                    f"tests/billing-engine/test_{pkg.name}.py "
                    f"(for src/billing-engine/{pkg.name}/service.py)"
                )

        assert not missing, (
            "CCT-ARCH-03 FAIL: service packages without test files (C-098 violation):\n"
            + "\n".join(f"  MISSING: {m}" for m in missing)
            + "\nEvery billing-engine service package must have a corresponding test file."
        )


# ── CCT-ARCH-04 ───────────────────────────────────────────────────────────────

class TestCCTArch04ModelsPresent:
    """CCT-ARCH-04: every billing-engine service package must have models.py."""

    def test_service_packages_have_models(self) -> None:
        """C-098 Rule 4: models.py required per service package (separation of concerns)."""
        if not BILLING_ENGINE_SRC.exists():
            pytest.skip("billing-engine src not yet created")

        packages = _service_packages()
        if not packages:
            pytest.skip("no service packages with service.py yet")

        missing = []
        for pkg in packages:
            if not (pkg / "models.py").exists():
                missing.append(f"src/billing-engine/{pkg.name}/models.py")

        assert not missing, (
            "CCT-ARCH-04 FAIL: service packages without models.py (C-098 violation):\n"
            + "\n".join(f"  MISSING: {m}" for m in missing)
            + "\nSeparate Pydantic models from service logic. Add models.py to each service package."
        )


# ── CCT-PROP-01 ───────────────────────────────────────────────────────────────

class TestCCTProp01HypothesisRequired:
    """CCT-PROP-01: billing-engine test files covering financial math must use @given."""

    def test_financial_test_files_use_hypothesis_given(self) -> None:
        """C-097: any test file covering financial calculation must have @given tests."""
        if not BILLING_ENGINE_TESTS.exists():
            pytest.skip("billing-engine tests not yet created")

        violations = []
        for test_file in sorted(BILLING_ENGINE_TESTS.glob("test_*.py")):
            if test_file.name in C097_GRANDFATHERED:
                continue  # pre-C-097 ratification; retrofit required before G4 CLEAR
            # Only check files that cover financial calculation functions
            if not _covers_financial_function(test_file):
                continue
            if not _has_given_decorator(test_file):
                violations.append(str(test_file.relative_to(REPO_ROOT)))

        assert not violations, (
            "CCT-PROP-01 FAIL: financial test files missing @given decorators (C-097 violation):\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\nFinancial calculation test files must include property-based tests.\n"
            + "Add: from hypothesis import given, strategies as st\n"
            + "     @given(st.integers(min_value=100, max_value=1_000_000), ...)\n"
            + "     def test_derive_price_property(...): ..."
        )
