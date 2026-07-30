# Implements: tests/runner/test_state.py
# constitutional_basis: C-076 (≥90% coverage), C-069 (Self-Improvement — monitor signal)
"""Tests for runner/state.py — _MONITOR_SIGNAL, _INFRA_ERROR_TASKS."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from runner import state as runner_state


class TestMonitorSignalStructure:
    def test_is_dict(self):
        assert isinstance(runner_state._MONITOR_SIGNAL, dict)

    def test_has_required_keys(self):
        required = ["run_id", "sprint", "scaffold_task", "scaffold_failed",
                    "task_results", "spec_gap_issues", "overall_result", "file_costs"]
        for key in required:
            assert key in runner_state._MONITOR_SIGNAL, f"Missing key: {key}"

    def test_task_results_is_dict(self):
        assert isinstance(runner_state._MONITOR_SIGNAL["task_results"], dict)

    def test_spec_gap_issues_is_list(self):
        assert isinstance(runner_state._MONITOR_SIGNAL["spec_gap_issues"], list)

    def test_file_costs_is_dict(self):
        assert isinstance(runner_state._MONITOR_SIGNAL["file_costs"], dict)

    def test_scaffold_failed_default_false(self):
        # Should be False initially (not yet set by any task)
        assert runner_state._MONITOR_SIGNAL["scaffold_failed"] is False

    def test_overall_result_default(self):
        assert runner_state._MONITOR_SIGNAL["overall_result"] == "UNKNOWN"


class TestInfraErrorTasks:
    def test_is_list(self):
        assert isinstance(runner_state._INFRA_ERROR_TASKS, list)


class TestMonitorSignalMutable:
    """Confirm _MONITOR_SIGNAL is the same object across imports (singleton)."""

    def test_same_object_identity(self):
        from runner import state as s2
        assert runner_state._MONITOR_SIGNAL is s2._MONITOR_SIGNAL

    def test_mutation_visible_across_imports(self):
        from runner import state as s2
        runner_state._MONITOR_SIGNAL["task_results"]["TEST_KEY"] = "ok"
        assert s2._MONITOR_SIGNAL["task_results"].get("TEST_KEY") == "ok"
        # cleanup
        del runner_state._MONITOR_SIGNAL["task_results"]["TEST_KEY"]
