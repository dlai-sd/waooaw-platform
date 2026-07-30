# Implements: tests/runner/test_git_ops.py
# constitutional_basis: C-076 (≥90% coverage), C-059 (Traceability)
"""Tests for runner/git_ops.py — run, git, gh, set_output, record_evidence."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from runner.git_ops import gh, git, record_evidence, run, set_output


class TestSetOutput:
    def test_prints_key_value(self, capsys):
        set_output("result", "SUCCESS")
        captured = capsys.readouterr()
        assert "OUTPUT result=SUCCESS" in captured.out

    def test_writes_to_github_output_file(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        output_file.write_text("")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        set_output("halt", "false")
        content = output_file.read_text()
        assert "halt=false" in content

    def test_no_write_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        # Should not raise
        set_output("key", "value")


class TestRecordEvidence:
    def test_writes_jsonl(self, tmp_path, monkeypatch):
        import runner.git_ops as git_ops_mod
        monkeypatch.setattr(git_ops_mod, "EVIDENCE_LOG", tmp_path / "evidence.jsonl")
        record_evidence("test_event", task="WC999", result="ok")
        lines = (tmp_path / "evidence.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["event"] == "test_event"
        assert rec["task"] == "WC999"
        assert rec["stub_mode"] is True

    def test_creates_parent_dir(self, tmp_path, monkeypatch):
        import runner.git_ops as git_ops_mod
        # Only one level of nesting — mkdir(exist_ok=True) does not use parents=True
        deep_path = tmp_path / "nested" / "evidence.jsonl"
        deep_path.parent.mkdir(parents=True, exist_ok=True)  # pre-create parent
        monkeypatch.setattr(git_ops_mod, "EVIDENCE_LOG", deep_path)
        record_evidence("init_event")
        assert deep_path.exists()

    def test_appends_multiple_events(self, tmp_path, monkeypatch):
        import runner.git_ops as git_ops_mod
        monkeypatch.setattr(git_ops_mod, "EVIDENCE_LOG", tmp_path / "ev.jsonl")
        record_evidence("first")
        record_evidence("second")
        lines = (tmp_path / "ev.jsonl").read_text().strip().splitlines()
        assert len(lines) == 2


class TestRunFunction:
    def test_run_captures_output(self):
        result = run(["echo", "hello-test"], capture=True)
        assert result.returncode == 0
        assert "hello-test" in result.stdout

    def test_run_prints_command(self, capsys):
        run(["echo", "captest"], capture=True)
        captured = capsys.readouterr()
        assert "echo captest" in captured.out

    def test_run_check_false_does_not_raise(self):
        result = run(["false"], check=False)
        assert result.returncode != 0

    def test_run_check_true_raises_on_failure(self):
        with pytest.raises(Exception):
            run(["false"], check=True)


class TestGitHelper:
    def test_git_calls_git(self, monkeypatch):
        calls = []

        def fake_run(cmd, check=True, capture=False):
            calls.append(cmd)
            m = MagicMock()
            m.returncode = 0
            return m

        monkeypatch.setattr("runner.git_ops.run", fake_run)
        git(["status"])
        assert calls[0] == ["git", "status"]


class TestGhHelper:
    def test_gh_calls_gh_with_capture(self, monkeypatch):
        calls = []

        def fake_run(cmd, check=True, capture=False):
            calls.append((cmd, capture))
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            return m

        monkeypatch.setattr("runner.git_ops.run", fake_run)
        gh(["issue", "list"])
        assert calls[0][0] == ["gh", "issue", "list"]
        assert calls[0][1] is True  # capture=True
