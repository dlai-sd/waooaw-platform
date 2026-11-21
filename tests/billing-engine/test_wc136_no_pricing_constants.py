# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-091
"""Static guard: no prices, margins, rates, grants or ceilings are hard-coded in pricing paths (A16, A19)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/billing-engine"
INIT = ROOT / "infrastructure/postgres/init"
SCANNED = (
    *sorted((SOURCE / "pricing").glob("*.py")),
    SOURCE / "markup/package_models.py",
    SOURCE / "markup/package_engine.py",
)
SQL_FILES = (
    INIT / "99zzzzzzzz-wc136-07-pricing-versions.sql",
    INIT / "99zzzzzzzz-wc136-08-thread-catalogue-pending.sql",
)
MONEY_WORDS = {"paise", "price", "margin", "ceiling", "floor", "grant", "cost", "budget", "gst", "rate", "rates"}
TRIVIAL_VALUES = {0, 1, 100}
# The package body defaults the statutory GST rate to 18 per Appendix A.2; the body field carries the real value.
ALLOWED_NAMES = {"DEFAULT_GST_RATE_PERCENT"}


def _tokens(name: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+", name)}


def _number(node: ast.expr) -> float | None:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _number(node.operand)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    return None


def _target_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def monetary_literals(source: str, label: str) -> list[str]:
    findings: list[str] = []

    def check(name: str | None, value: ast.expr | None) -> None:
        if name is None or value is None or name in ALLOWED_NAMES:
            return
        number = _number(value)
        if number is None or abs(number) in TRIVIAL_VALUES or not _tokens(name) & MONEY_WORDS:
            return
        findings.append(f"{label}:{value.lineno}: {name} = {number}")

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                check(_target_name(target), node.value)
        elif isinstance(node, ast.AnnAssign):
            check(_target_name(node.target), node.value)
        elif isinstance(node, ast.keyword):
            check(node.arg, node.value)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    check(key.value, value)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = [*node.args.posonlyargs, *node.args.args]
            for argument, default in zip(positional[len(positional) - len(node.args.defaults) :], node.args.defaults, strict=True):
                check(argument.arg, default)
            for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True):
                check(argument.arg, default)
    return findings


@pytest.mark.parametrize("path", SCANNED, ids=lambda path: path.name)
def test_pricing_source_has_no_hard_coded_monetary_literals(path: Path) -> None:
    assert monetary_literals(path.read_text(encoding="utf-8"), path.name) == []


def test_the_scan_covers_the_pricing_package() -> None:
    names = {path.name for path in SCANNED}
    assert {"engine.py", "service.py", "validators.py", "simulator.py", "package_engine.py"} <= names


def test_the_guard_flags_hard_coded_prices_margins_rates_and_ceilings() -> None:
    source = (
        "MINIMUM_MARGIN_PCT = 55\n"
        "price_incl_gst_paise: int = 49900\n"
        "def f(ceiling_paise=5000, *, budgetMaximum=0, cost=-250):\n"
        "    return g(raw_cost_paise=120)\n"
        "grant = {'amountPaise': 1000, 'durationDays': 14}\n"
    )
    findings = monetary_literals(source, "sample")
    assert len(findings) == 6
    assert any("MINIMUM_MARGIN_PCT" in line for line in findings)
    assert any("amountPaise" in line for line in findings)
    assert not any("durationDays" in line or "budgetMaximum" in line for line in findings)


def test_the_guard_ignores_structural_constants() -> None:
    source = (
        "limit: int = 100\n"
        "status_code = 503\n"
        "refund = 0\n"
        "step = 1\n"
        "PERCENT_MAXIMUM = 999.99\n"
        "def f(offset=0):\n"
        "    return Field(ge=1, le=100)\n"
    )
    assert monetary_literals(source, "sample") == []


@pytest.mark.parametrize("path", SQL_FILES, ids=lambda path: path.name)
def test_pricing_sql_declares_no_numeric_column_defaults(path: Path) -> None:
    assert not re.search(r"\bDEFAULT\s+-?[1-9]", path.read_text(encoding="utf-8"), re.I)
