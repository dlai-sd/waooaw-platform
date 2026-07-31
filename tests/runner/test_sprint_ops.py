# Implements: tests/runner/test_sprint_ops.py
# constitutional_basis: C-076 (≥90% coverage), C-001 (Human Override), C-059 (Traceability)
"""Tests for runner/sprint_ops.py — parse_sprint_state, check_platform_phase_gate,
run_runner_integrity_checks, update_sprint_state."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from runner.sprint_ops import parse_sprint_state, run_runner_integrity_checks, parse_wc_tasks, update_task_status


# ── Fixtures ──────────────────────────────────────────────────────────────────

_MINIMAL_STATE_FILE = dedent("""\
    # PROJECT_STATE.md
    ## SPRINT_STATE_MACHINE
    ```yaml
    platform_phase: IMPLEMENTATION
    autonomous_halt: false
    current_sprint: WC026
    sprint_status: READY
    tasks_remaining:
      - WC026-01
      - WC026-02
    tasks_done:
      - WC025-01
    consecutive_failures: 0
    ```
    """)


class TestParseSprintState:
    def test_parses_platform_phase(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(_MINIMAL_STATE_FILE)
        monkeypatch.setattr(sp, "STATE_FILE", state_file)
        state = parse_sprint_state()
        assert state["platform_phase"] == "IMPLEMENTATION"

    def test_parses_current_sprint(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(_MINIMAL_STATE_FILE)
        monkeypatch.setattr(sp, "STATE_FILE", state_file)
        state = parse_sprint_state()
        assert state["current_sprint"] == "WC026"

    def test_raises_on_missing_block(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text("# No state machine here\n")
        monkeypatch.setattr(sp, "STATE_FILE", state_file)
        with pytest.raises(ValueError, match="SPRINT_STATE_MACHINE"):
            parse_sprint_state()

    def test_strips_yaml_comments(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        content = dedent("""\
            ## SPRINT_STATE_MACHINE
            ```yaml
            platform_phase: IMPLEMENTATION # currently live
            autonomous_halt: false
            ```
            """)
        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(content)
        monkeypatch.setattr(sp, "STATE_FILE", state_file)
        state = parse_sprint_state()
        assert state["platform_phase"] == "IMPLEMENTATION"


class TestRunRunnerIntegrityChecks:
    """
    Checks run against a synthetic namespace so the real runner is not needed.
    """

    def _make_namespace(self) -> dict:
        from runner.llm_codegen import parse_llm_files, validate_written_files, write_llm_files
        from runner.task_executor import execute_with_llm

        return {
            "parse_llm_files": parse_llm_files,
            "write_llm_files": write_llm_files,
            "validate_written_files": validate_written_files,
            "execute_with_llm": execute_with_llm,
            "TASK_HANDLERS": {"WC012-01": lambda: True},
        }

    def test_passes_with_valid_namespace(self):
        ns = self._make_namespace()
        ok, errors = run_runner_integrity_checks(ns)
        assert ok, f"Expected pass but got errors: {errors}"

    def test_fails_when_parse_llm_files_missing(self):
        ns = self._make_namespace()
        del ns["parse_llm_files"]
        ok, errors = run_runner_integrity_checks(ns)
        assert not ok
        assert any("parse_llm_files" in e for e in errors)

    def test_fails_when_execute_with_llm_missing(self):
        ns = self._make_namespace()
        del ns["execute_with_llm"]
        ok, errors = run_runner_integrity_checks(ns)
        assert not ok

    def test_empty_task_handlers_is_allowed(self):
        """TASK_HANDLERS may be empty at startup — groomer injects entries at runtime."""
        ns = self._make_namespace()
        ns["TASK_HANDLERS"] = {}
        ok, errors = run_runner_integrity_checks(ns)
        assert ok is True
        assert not any("TASK_HANDLERS" in e for e in errors)

    def test_fails_when_task_handlers_not_dict(self):
        ns = self._make_namespace()
        ns["TASK_HANDLERS"] = "not a dict"
        ok, errors = run_runner_integrity_checks(ns)
        assert not ok
        assert any("TASK_HANDLERS" in e for e in errors)

    def test_fails_when_parse_llm_files_not_callable(self):
        ns = self._make_namespace()
        ns["parse_llm_files"] = "not callable"
        ok, errors = run_runner_integrity_checks(ns)
        assert not ok

    def test_boundary_enforcement_tested_in_probe(self):
        """Integrity check runs parse_llm_files probe — constitution/ must be rejected."""
        ns = self._make_namespace()
        ok, errors = run_runner_integrity_checks(ns)
        # Should pass (parse_llm_files correctly blocks constitution/ path)
        assert ok

    def test_empty_namespace_fails(self):
        ok, errors = run_runner_integrity_checks({})
        assert not ok
        assert len(errors) > 0


_WC_FILE_CONTENT = dedent("""\
    # Work Contract 099
    ## Tasks
    | task_id | scope | model_hint | status | completed_at |
    |---|---|---|---|---|
    | WC099-01 | `src/svc/models.py` — models | auto | done | 2026-07-30T10:00Z |
    | WC099-02 | `src/svc/service.py` — service | auto | pending | — |
    | WC099-03 | `tests/svc/test_svc.py` — tests | auto | pending | — |
    """)


class TestParseWcTasks:
    def _write_wc(self, tmp_path, sprint="WC-099"):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        wc_file = wc_dir / f"{sprint}-test.md"
        wc_file.write_text(_WC_FILE_CONTENT)
        return wc_dir

    def test_returns_pending_tasks(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        self._write_wc(tmp_path)
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        result = parse_wc_tasks("WC-099")
        assert result["pending"] == ["WC099-02", "WC099-03"]

    def test_returns_done_tasks(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        self._write_wc(tmp_path)
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        result = parse_wc_tasks("WC-099")
        assert result["done"] == ["WC099-01"]

    def test_failed_status_categorised(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        (wc_dir / "WC-099-test.md").write_text(dedent("""\
            ## Tasks
            | task_id | scope | model_hint | status | completed_at |
            |---|---|---|---|---|
            | WC099-01 | `src/svc/a.py` — a | auto | failed | — |
            """))
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        result = parse_wc_tasks("WC-099")
        assert result["failed"] == ["WC099-01"]
        assert result["pending"] == []

    def test_raises_when_wc_file_missing(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        (tmp_path / "work-contracts").mkdir()
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        with pytest.raises(FileNotFoundError):
            parse_wc_tasks("WC-099")

    def test_scope_with_escaped_pipes_does_not_corrupt_parsing(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        (wc_dir / "WC-099-test.md").write_text(dedent("""\
            ## Tasks
            | task_id | scope | model_hint | status | completed_at |
            |---|---|---|---|---|
            | WC099-01 | `Enum[LOG\\|NOTIFY\\|BLOCK]` — scope | auto | pending | — |
            """))
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        result = parse_wc_tasks("WC-099")
        assert "WC099-01" in result["pending"]


class TestUpdateTaskStatus:
    def _write_wc(self, tmp_path):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        wc_file = wc_dir / "WC-099-test.md"
        wc_file.write_text(_WC_FILE_CONTENT)
        return wc_file

    def test_marks_task_done(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        wc_file = self._write_wc(tmp_path)
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        update_task_status("WC-099", "WC099-02", "done")
        content = wc_file.read_text()
        assert "| WC099-02 |" in content
        assert "| done |" in content
        assert "| pending |" not in content.split("WC099-02")[1].split("\n")[0]

    def test_done_task_gets_timestamp(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        wc_file = self._write_wc(tmp_path)
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        update_task_status("WC-099", "WC099-02", "done")
        content = wc_file.read_text()
        row = [l for l in content.splitlines() if "WC099-02" in l][0]
        assert "2026" in row  # timestamp written

    def test_failed_task_gets_dash_not_timestamp(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        wc_file = self._write_wc(tmp_path)
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        update_task_status("WC-099", "WC099-02", "failed")
        content = wc_file.read_text()
        row = [l for l in content.splitlines() if "WC099-02" in l][0]
        assert "| failed | — |" in row

    def test_other_tasks_unchanged(self, tmp_path, monkeypatch):
        import runner.sprint_ops as sp
        wc_file = self._write_wc(tmp_path)
        monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
        update_task_status("WC-099", "WC099-02", "done")
        result = parse_wc_tasks("WC-099")
        # WC099-01 was already done, WC099-03 still pending
        assert "WC099-01" in result["done"]
        assert "WC099-03" in result["pending"]
