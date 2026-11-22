# Implements: WC-150 R003
# constitutional_basis: C-059, C-076, ADR-046

"""uvicorn creates Config.ssl only inside Config.load(); a private listener must not read it first."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LISTENERS = sorted((ROOT / "src").glob("*/private_server.py"))


def read_before_load(source: str) -> list[str]:
    """Report each main() that reads <name>.ssl before it calls <name>.load()."""
    findings: list[str] = []
    for function in ast.walk(ast.parse(source)):
        if not (isinstance(function, ast.FunctionDef) and function.name == "main"):
            continue
        events: list[tuple[int, int, str, str]] = []
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.attr in {"ssl", "load"}
            ):
                events.append((node.lineno, node.col_offset, node.value.id, node.attr))
        for _, _, name, attribute in sorted(events):
            if attribute == "load":
                break
            findings.append(f"{name}.ssl is read before {name}.load() in main()")
            break
    return findings


def test_every_private_listener_is_covered_by_the_guard() -> None:
    assert {path.parent.name for path in LISTENERS} >= {"ai-runtime", "billing-engine", "professional-runtime"}


@pytest.mark.parametrize("path", LISTENERS, ids=lambda path: path.parent.name)
def test_private_listener_loads_the_uvicorn_config_before_reading_ssl(path: Path) -> None:
    assert read_before_load(path.read_text(encoding="utf-8")) == []


def test_guard_rejects_the_defect_that_stopped_demo() -> None:
    defect = (
        "def main():\n"
        "    config = private_listener_config()\n"
        "    if config.ssl is None:\n"
        "        config.load()\n"
    )
    assert read_before_load(defect) == ["config.ssl is read before config.load() in main()"]


def test_guard_accepts_load_before_the_ssl_read() -> None:
    fixed = (
        "def main():\n"
        "    config = private_listener_config()\n"
        "    config.load()\n"
        "    if config.ssl is None:\n"
        "        raise RuntimeError('tls')\n"
    )
    assert read_before_load(fixed) == []
