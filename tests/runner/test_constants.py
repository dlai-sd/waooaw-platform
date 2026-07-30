# Implements: tests/runner/test_constants.py
# constitutional_basis: C-076 (≥90% coverage), C-059 (Traceability)
"""Tests for runner/constants.py — REPO_ROOT, ALLOWED_WRITE_ROOTS."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on sys.path for runner package
_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from runner.constants import ALLOWED_WRITE_ROOTS, EVIDENCE_LOG, REPO_ROOT, STATE_FILE


class TestRepoRoot:
    def test_repo_root_is_path(self):
        assert isinstance(REPO_ROOT, Path)

    def test_repo_root_exists(self):
        assert REPO_ROOT.exists()

    def test_repo_root_is_project_root(self):
        # REPO_ROOT should contain constitution/ and scripts/
        assert (REPO_ROOT / "constitution").is_dir()
        assert (REPO_ROOT / "scripts").is_dir()

    def test_state_file_is_under_repo_root(self):
        assert STATE_FILE == REPO_ROOT / "constitution" / "PROJECT_STATE.md"

    def test_evidence_log_is_under_repo_root(self):
        assert EVIDENCE_LOG == REPO_ROOT / "logs" / "bootstrap-evidence.jsonl"


class TestAllowedWriteRoots:
    def test_is_list(self):
        assert isinstance(ALLOWED_WRITE_ROOTS, list)

    def test_contains_src(self):
        assert "src/" in ALLOWED_WRITE_ROOTS

    def test_contains_tests(self):
        assert "tests/" in ALLOWED_WRITE_ROOTS

    def test_no_constitution(self):
        assert not any("constitution" in r for r in ALLOWED_WRITE_ROOTS)

    def test_no_adr(self):
        assert not any("adr" in r for r in ALLOWED_WRITE_ROOTS)

    def test_all_end_with_slash(self):
        for root in ALLOWED_WRITE_ROOTS:
            assert root.endswith("/"), f"{root!r} must end with /"
