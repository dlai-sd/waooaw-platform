"""
Unit tests for check_c086_gate.py

# Implements: scripts/check_c086_gate.py
# constitutional_basis: C-076 (≥90% coverage), C-086 (Pre-Execution Simulation Gate)
# office: Platform IT Expert — QA hat
# ib_item: IB-009
"""

import os
import re
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_c086_gate


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def make_project_state(tasks: list[str], tmp_path: Path) -> Path:
    """Write a minimal PROJECT_STATE.md with the given tasks_remaining."""
    tasks_lines = "\n".join(f"  - {t}" for t in tasks)
    # Do NOT use textwrap.dedent here — the regex in check_c086_gate.main()
    # expects '  - ' (2-space indent) which must be preserved exactly.
    if tasks:
        remaining_block = f"tasks_remaining:\n{tasks_lines}\n"
    else:
        remaining_block = "tasks_remaining: []\n"
    content = (
        "# PROJECT_STATE.md\n"
        "## SPRINT_STATE_MACHINE\n"
        "```yaml\n"
        "platform_phase: IMPLEMENTATION\n"
        "autonomous_halt: false\n"
        + remaining_block +
        "```\n"
    )
    state_file = tmp_path / "constitution" / "PROJECT_STATE.md"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(content)
    return state_file


def make_sim_file(task: str, verdict: str, sim_dir: Path) -> Path:
    """Write a simulation file with the given verdict."""
    sim_file = sim_dir / f"SIM-PL-002-{task}-test.md"
    sim_file.write_text(f"# Simulation for {task}\n\nVerdict: {verdict}\n")
    return sim_file


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestC086Gate:
    def test_no_tasks_remaining_passes(self, tmp_path, monkeypatch, capsys):
        """Empty tasks_remaining → gate passes (nothing to check)."""
        make_project_state([], tmp_path)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0

    def test_legacy_task_skipped(self, tmp_path, monkeypatch, capsys):
        """WC012-01 is a legacy callable handler — gate skips it (passes)."""
        make_project_state(["WC012-01"], tmp_path)
        (tmp_path / "simulation").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0
        out = capsys.readouterr().out
        assert "legacy" in out.lower() or "WC012-01" in out

    def test_legacy_wc012_02_skipped(self, tmp_path, monkeypatch):
        """WC012-02 is also legacy callable — no simulation required."""
        make_project_state(["WC012-02"], tmp_path)
        (tmp_path / "simulation").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0

    def test_decomposed_task_without_simulation_fails(self, tmp_path, monkeypatch, capsys):
        """WC012-03 requires SIM-PL-002 — missing file → gate fails."""
        make_project_state(["WC012-03"], tmp_path)
        (tmp_path / "simulation").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 1
        out = capsys.readouterr().out
        assert "WC012-03" in out

    def test_decomposed_task_with_pass_simulation_passes(self, tmp_path, monkeypatch):
        """WC012-03 with PASS simulation → gate passes."""
        make_project_state(["WC012-03"], tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir(parents=True, exist_ok=True)
        make_sim_file("WC012-03", "✅ PASS", sim_dir)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0

    def test_decomposed_task_with_fail_simulation_fails(self, tmp_path, monkeypatch, capsys):
        """WC012-03 with FAIL verdict → gate fails."""
        make_project_state(["WC012-03"], tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir(parents=True, exist_ok=True)
        make_sim_file("WC012-03", "❌ FAIL", sim_dir)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 1

    def test_multiple_tasks_mixed_result_fails(self, tmp_path, monkeypatch, capsys):
        """One PASS + one missing → gate fails overall."""
        make_project_state(["WC012-03", "WC012-04"], tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir(parents=True, exist_ok=True)
        make_sim_file("WC012-03", "✅ PASS", sim_dir)
        # WC012-04 has no sim file
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 1

    def test_multiple_tasks_all_pass(self, tmp_path, monkeypatch):
        """Both WC012-03 and WC012-04 have PASS → gate passes."""
        make_project_state(["WC012-03", "WC012-04"], tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir(parents=True, exist_ok=True)
        make_sim_file("WC012-03", "✅ PASS", sim_dir)
        make_sim_file("WC012-04", "VERDICT: ✅ PASS", sim_dir)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0

    def test_legacy_and_decomposed_together(self, tmp_path, monkeypatch):
        """Mix of legacy + decomposed tasks — legacy skipped, decomposed checked."""
        make_project_state(["WC012-01", "WC012-03"], tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir(parents=True, exist_ok=True)
        make_sim_file("WC012-03", "✅ PASS", sim_dir)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0

    def test_tasks_block_empty_in_state_file(self, tmp_path, monkeypatch):
        """tasks_remaining block not found → treats as empty → passes."""
        state_file = tmp_path / "constitution" / "PROJECT_STATE.md"
        state_file.parent.mkdir(parents=True)
        state_file.write_text("## SPRINT_STATE_MACHINE\n```yaml\n```\n")
        (tmp_path / "simulation").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(check_c086_gate, "REPO_ROOT", tmp_path)
        result = check_c086_gate.main()
        assert result == 0

    def test_legacy_tasks_set_is_not_empty(self):
        """LEGACY_TASKS must include all WC011 and WC012-01/02 tasks."""
        assert "WC012-01" in check_c086_gate.LEGACY_TASKS
        assert "WC012-02" in check_c086_gate.LEGACY_TASKS
        assert "WC011-01" in check_c086_gate.LEGACY_TASKS
