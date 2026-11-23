"""Fault-injection tests for platform-state derivation and the delivery ledger."""

# Implements: architecture/reference/platform-component-registry.yaml §institutional_state
# Constitutional basis: C-008, C-032, C-059, C-071

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from derive_platform_state import (
    claim_inventory,
    derive,
    ledger_gaps,
    load_ledger,
    merged_pull_requests,
    refresh_ledger,
    render_ledger,
    work_contracts,
)
from sync_platform_state import render_work_contract_index

REPO_ROOT = Path(__file__).resolve().parents[2]


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture
def history(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "a.txt", "a")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "initial")
    git(tmp_path, "checkout", "-q", "-b", "ib/150/guard")
    write(tmp_path, "b.txt", "b")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "fix(pr): guard the listener (WC-150)")
    git(tmp_path, "checkout", "-q", "main")
    git(tmp_path, "merge", "-q", "--no-ff", "ib/150/guard", "-m", "Merge pull request #5 from o/ib/150/guard")
    write(tmp_path, "c.txt", "c")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "fix(infra): repair WC-151 key read (#6)")
    write(tmp_path, "d.txt", "d")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "chore: direct push without a pull request")
    return tmp_path


def test_merged_pull_requests_reads_merge_and_squash_commits(history: Path) -> None:
    entries = merged_pull_requests(history, "main")

    assert [(entry["pr"], entry["wc"]) for entry in entries] == [(6, ["WC-151"]), (5, ["WC-150"])]


def test_ledger_gap_is_detected_until_refreshed(history: Path) -> None:
    (history / "architecture/reference").mkdir(parents=True)
    (history / "architecture/reference/work-contract-delivery-ledger.yaml").write_text(
        render_ledger(merged_pull_requests(history, "main")[1:]), encoding="utf-8"
    )

    assert ledger_gaps(history, "main") == ["#6"]
    assert refresh_ledger(history, "main") is True
    assert ledger_gaps(history, "main") == []
    assert refresh_ledger(history, "main") is False


def test_work_contract_status_formats_and_duplicate_ids(tmp_path: Path) -> None:
    write(tmp_path, "work-contracts/WC-201-first.md", "# WC-201 - First\n\n| Status | DONE. Evidence later |\n")
    write(tmp_path, "work-contracts/WC-202-second.md", "# Work Contract 202 - Second\n\n**Status:** IN PROGRESS\n")
    write(tmp_path, "work-contracts/WC-203-third.md", "# WC-203 Third\n\n- Status: BLOCKED\n")
    write(tmp_path, "work-contracts/WC-204-a-crosswalk.md", "# WC-204 Crosswalk\n")
    write(tmp_path, "work-contracts/WC-204-b-main.md", "# WC-204 - Main\n\n| Status | OPEN |\n")
    write(tmp_path, "work-contracts/WC-201-requirements.yaml", "ignored: true\n")

    records = work_contracts(tmp_path)

    assert sorted(records) == [201, 202, 203, 204]
    assert (records[201]["title"], records[201]["status"]) == ("First", "DONE")
    assert records[202]["status"] == "IN PROGRESS"
    assert records[203]["status"] == "BLOCKED"
    assert (records[204]["title"], records[204]["file"]) == ("Crosswalk", "WC-204-a-crosswalk.md")


def test_proposed_claims_and_missing_numbers_are_gaps(tmp_path: Path) -> None:
    write(tmp_path, "knowledge/claims/C-001.md", "Claim ID: C-001\nStatus:          RATIFIED — 2026-07-24\n")
    write(tmp_path, "knowledge/claims/C-002.md", "Claim ID: C-002\nStatus:          PROPOSED — 2026-07-29\n")
    write(tmp_path, "knowledge/claims/C-004.md", "Claim ID: C-004\nno status line means ratified\n")

    assert claim_inventory(tmp_path) == {"ratified": 2, "gaps": ["C-002", "C-003"]}


def test_work_contract_index_marks_missing_delivery_evidence() -> None:
    facts = {
        "work_contracts": {
            80: {"id": "WC-080", "title": "Before the index", "status": "DONE"},
            90: {"id": "WC-090", "title": "Pipe | title", "status": "OPEN"},
            91: {"id": "WC-091", "title": "Delivered", "status": "IN PROGRESS"},
        },
        "delivered": {91: [{"pr": 7}, {"pr": 8}]},
    }

    rendered = render_work_contract_index(facts)

    assert "WC-080" not in rendered
    assert "Pipe \\| title | OPEN | none recorded |" in rendered
    assert "| WC-091 | Delivered | IN PROGRESS | #7, #8 |" in rendered


def test_repository_ledger_and_facts_are_consistent() -> None:
    facts = derive(REPO_ROOT)

    assert facts["latest_completed_implementation"] is not None
    assert facts["counts"]["recorded"] == len(facts["work_contracts"])
    assert facts["counts"]["adrs"] >= 53
    assert facts["as_of"] == max(entry["date"] for entry in load_ledger(REPO_ROOT))


def test_project_state_stays_within_its_declared_size() -> None:
    lines = (REPO_ROOT / "constitution/PROJECT_STATE.md").read_text(encoding="utf-8").splitlines()

    assert len(lines) < 200


def test_every_adr_file_has_an_index_row() -> None:
    index = (REPO_ROOT / "adr/ADR-INDEX.md").read_text(encoding="utf-8")
    numbers = {path.name[4:7] for path in (REPO_ROOT / "adr").glob("ADR-[0-9][0-9][0-9]-*.md")}

    missing = sorted(number for number in numbers if f"| **{number}** |" not in index)

    assert missing == []
