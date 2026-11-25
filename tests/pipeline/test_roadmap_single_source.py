"""Guards the single-roadmap rule (Founder Resolution FR-006, WC-168 R001 and R002).

ROADMAP.md is the only roadmap. These tests fail when a pointer to it disappears, when the current-iteration
line differs between files, when a listed Work Contract or document is missing, or when the iteration table loses
its shape. They do not judge the content of decisions; deviation control still needs the Founder.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "ROADMAP.md"
POINTER_FILES = [
    "README.md",
    "constitution/PROJECT_STATE.md",
    "constitution/AGENT-ENTRY.md",
    "constitution/BOOTSTRAP.md",
    ".github/copilot-instructions.md",
]
CURRENT = re.compile(r"Current iteration[^\n]*?Iteration (\d) \((WC-\d+)\)")
ITERATION_ROW = re.compile(r"^\|\s*(\d)\s*\|\s*(WC-\d+)\s*\|", re.MULTILINE)


def _text(path: str | Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_roadmap_lists_six_iterations_with_consecutive_reserved_work_contracts() -> None:
    rows = ITERATION_ROW.findall(_text(ROADMAP))
    assert [number for number, _ in rows] == ["1", "2", "3", "4", "5", "6"]
    assert [contract for _, contract in rows] == [f"WC-{number}" for number in range(168, 174)]


def test_every_written_iteration_contract_and_ledger_exists() -> None:
    written = {"WC-168", "WC-169", "WC-170", "WC-171", "WC-172"}
    for contract in written:
        assert list((ROOT / "work-contracts").glob(f"{contract}-*.md")), contract
        assert (ROOT / "work-contracts" / f"{contract}-requirements.yaml").exists(), contract


def test_every_entry_point_points_to_the_roadmap() -> None:
    for pointer_file in POINTER_FILES:
        assert "ROADMAP.md" in _text(pointer_file), pointer_file


def test_the_current_iteration_is_the_same_in_the_roadmap_readme_and_project_state() -> None:
    expected = CURRENT.search(_text(ROADMAP))
    assert expected is not None
    for path in ("README.md", "constitution/PROJECT_STATE.md"):
        found = CURRENT.search(_text(path))
        assert found is not None, path
        assert found.groups() == expected.groups(), path


def test_the_deviation_rule_is_stated_where_agents_start() -> None:
    for path in ("README.md", "constitution/AGENT-ENTRY.md", "constitution/BOOTSTRAP.md", ".github/copilot-instructions.md"):
        assert "Founder" in _text(path) and "ROADMAP.md" in _text(path), path
    assert "## 8. Deviation procedure" in _text(ROADMAP)


def test_every_document_the_roadmap_names_exists() -> None:
    named = {token for token in re.findall(r"`([^`\s]+\.(?:md|yaml))`", _text(ROADMAP)) if "/" in token or token == "SPRINT-REGISTRY.md"}
    assert named
    missing = sorted(path for path in named if not (ROOT / path).exists())
    assert missing == []
