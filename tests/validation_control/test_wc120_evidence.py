from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from validation_control import wc120_evidence as evidence

COMMIT = "a" * 40
RUNNER = "sha256:" + "b" * 64


@pytest.mark.parametrize(
    ("report", "counts"),
    [
        (
            "<testsuites><testsuite><testcase/><testcase/><testcase><skipped/></testcase></testsuite></testsuites>",
            {"passed": 2, "failed": 0, "skipped": 1},
        ),
        (
            "<testsuite><testcase/><testcase><error/></testcase><testcase><failure/></testcase></testsuite>",
            {"passed": 1, "failed": 2, "skipped": 0},
        ),
        (
            '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">'
            '<ResultSummary><Counters total="3" passed="1" failed="1"/></ResultSummary></TestRun>',
            {"passed": 1, "failed": 1, "skipped": 1},
        ),
        ("<testsuites/>", {"passed": 0, "failed": 0, "skipped": 0}),
    ],
)
def test_counts_come_from_actual_trx_or_junit_reports(tmp_path: Path, report: str, counts: dict[str, int]) -> None:
    path = tmp_path / "report.xml"
    path.write_text(report)
    assert evidence.report_counts(path) == counts


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_reports_reject_dtds_before_entity_expansion(tmp_path: Path, encoding: str) -> None:
    report = tmp_path / "report.xml"
    report.write_bytes(
        '<?xml version="1.0"?><!DOCTYPE testsuite [<!ENTITY x "expanded">]><testsuite><testcase name="&x;"/></testsuite>'.encode(
            encoding
        )
    )
    with pytest.raises(ValueError, match="DTD"):
        evidence.report_counts(report)


def record_selector(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    report: str = "<testsuite><testcase/></testsuite>",
    supporting: bool = False,
) -> Path:
    monkeypatch.setattr(evidence, "ROOT", root)
    directory = root / "test-results/wc120/CE-FIT-10"
    if supporting:
        directory /= "browser"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.xml").write_text(report)
    (directory / "selector.log").write_text("actual captured execution")
    evidence._record_selector(
        argparse.Namespace(
            ce_fit_id="CE-FIT-10",
            supporting=supporting,
            log=str(directory / "selector.log"),
            report=str(directory / "report.xml"),
            exit_status=0,
            command="runner test",
            node="ExactTestNode",
            started_at="2026-11-02T12:00:00Z",
            source_commit=COMMIT,
            runner_image_digest=RUNNER,
        )
    )
    return directory / "selector-result.json"


@pytest.mark.parametrize(
    "report",
    [
        "<testsuite/>",
        "<testsuite><testcase><skipped/></testcase></testsuite>",
        "<testsuite><testcase><failure/></testcase></testsuite>",
    ],
)
def test_zero_exit_cannot_hide_missing_skipped_or_failed_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    report: str,
) -> None:
    with pytest.raises(SystemExit, match="execute tests"):
        record_selector(tmp_path, monkeypatch, report=report)


def test_browser_evidence_does_not_overwrite_primary_selector(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary = record_selector(tmp_path, monkeypatch)
    before = primary.read_bytes()
    browser = record_selector(tmp_path, monkeypatch, supporting=True)
    assert browser != primary
    assert primary.read_bytes() == before
    assert evidence._qualified_selector(primary, COMMIT, RUNNER)["pass_fail_skip_counts"]["passed"] == 1
    assert evidence._qualified_selector(browser, COMMIT, RUNNER)["pass_fail_skip_counts"]["passed"] == 1


@pytest.mark.parametrize("mutation", ["commit", "count", "runner", "log", "report", "failed", "skipped"])
def test_candidate_rejects_stale_or_altered_selector_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    path = record_selector(tmp_path, monkeypatch)
    result = json.loads(path.read_text())
    if mutation == "commit":
        result["source_commit"] = "c" * 40
    elif mutation == "count":
        result["pass_fail_skip_counts"]["passed"] = 9
    elif mutation in ("failed", "skipped"):
        result["pass_fail_skip_counts"][mutation] = 1
    elif mutation == "runner":
        (path.parent / "runner-image-digest.txt").write_text("sha256:" + "c" * 64)
    elif mutation == "log":
        (path.parent / "selector.log").write_text("changed")
    else:
        (path.parent / "report.xml").write_text("<testsuite><testcase/><testcase/></testsuite>")
    path.write_text(json.dumps(result))
    with pytest.raises(SystemExit):
        evidence._qualified_selector(path, COMMIT, RUNNER)


def test_required_candidate_inputs_cannot_be_substituted_with_absent(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Missing"):
        evidence._required_digest(tmp_path / "missing")


def test_exact_candidate_summary_and_log_are_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    log = tmp_path / "summary.log"
    log.write_text("captured run")
    result = tmp_path / "summary.json"
    record = {"source_commit": COMMIT, "exit_status": 0, "log": log.name, "log_digest": evidence._sha256(log)}
    result.write_text(json.dumps(record))
    assert evidence._load_result(str(result), COMMIT)["result"] == record
    with pytest.raises(SystemExit, match="exact candidate"):
        evidence._load_result(str(result), "c" * 40)
    log.write_text("altered")
    with pytest.raises(SystemExit, match="log changed"):
        evidence._load_result(str(result), COMMIT)


def test_qualification_script_preserves_exact_runner_supply_and_browser_reports() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "scripts/qualify_wc120_candidate.sh").read_text()
    assert 'export WAOOAW_RUNNER_DOTNET_IMAGE="${dotnet_runner_digest}"' in script
    assert 'export WAOOAW_RUNNER_PYTHON_IMAGE="${python_runner_digest}"' in script
    assert 'export WAOOAW_RUNNER_FULL_IMAGE="${browser_runner_digest}"' in script
    assert "--pull never" in script
    assert "--no-build" not in script
    assert "PLAYWRIGHT_JUNIT_OUTPUT_FILE=" in script
    assert "supporting=(--supporting)" in script
    assert '"state": "OFF_SKIPPED"' not in (root / "scripts/validation_control/wc120_evidence.py").read_text()
