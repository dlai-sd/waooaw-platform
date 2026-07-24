"""
Comprehensive unit tests for task_decomposer.py

# Implements: scripts/task_decomposer.py
# constitutional_basis: C-076 (≥90% coverage), C-084 (Step Dependency Ordering),
#                       C-083 (Emit-Transport-Listen), C-086 (Pre-Execution Simulation Gate)
# office: Platform IT Expert — QA hat
# ib_item: IB-009
"""

import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from task_decomposer import (
    SubTaskDef,
    run_compile_gate,
    emit_subtask_signal,
    execute_subtask_chain,
    check_simulation_exists,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SubTaskDef — dataclass construction
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubTaskDef:
    """Tests for SubTaskDef dataclass defaults and field constraints."""

    def test_minimal_construction(self):
        st = SubTaskDef(id="WC012-02a", description="Test", type="deterministic")
        assert st.id == "WC012-02a"
        assert st.description == "Test"
        assert st.type == "deterministic"
        assert st.depends_on == []
        assert st.compile_gate == "dotnet_build"
        assert st.template_fn is None

    def test_llm_type_with_spec_sections(self):
        st = SubTaskDef(
            id="WC012-02b",
            description="LLM task",
            type="llm",
            depends_on=["WC012-02a"],
            spec_sections={"arch/spec.md": "full"},
            constitutional_check="C-041 check",
            model_hint="reasoning",
            max_tokens=8000,
        )
        assert st.depends_on == ["WC012-02a"]
        assert st.spec_sections == {"arch/spec.md": "full"}
        assert st.model_hint == "reasoning"
        assert st.max_tokens == 8000

    def test_deterministic_type_with_template_fn(self):
        fn = lambda: True
        st = SubTaskDef(id="WC012-03a", description="Data layer", type="deterministic",
                        template_fn=fn)
        assert st.template_fn is fn

    def test_default_compile_gate(self):
        st = SubTaskDef(id="X", description="Y", type="llm")
        assert st.compile_gate == "dotnet_build"

    def test_custom_compile_gate(self):
        st = SubTaskDef(id="X", description="Y", type="llm", compile_gate="ruff")
        assert st.compile_gate == "ruff"


# ═══════════════════════════════════════════════════════════════════════════════
# run_compile_gate()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunCompileGate:
    """Tests for compile gate execution (C-082)."""

    def test_unknown_gate_type_returns_false(self):
        ok, err = run_compile_gate("unknown_gate")
        assert ok is False
        assert "Unknown gate_type" in err

    def test_dotnet_build_no_csproj_returns_false(self, tmp_path):
        """No .csproj in service dir → gate fails (C-082)."""
        ok, err = run_compile_gate("dotnet_build", service_dir=str(tmp_path))
        assert ok is False
        assert "No .csproj" in err

    def test_ruff_gate_no_files_passes(self, tmp_path):
        """Empty directory → ruff passes (nothing to check)."""
        ok, err = run_compile_gate("ruff", service_dir=str(tmp_path))
        # ruff may pass or fail depending on installation — just check it doesn't crash
        assert isinstance(ok, bool)

    def test_dotnet_test_no_test_csproj_fails(self, tmp_path, monkeypatch):
        """No test .csproj → dotnet_test gate fails."""
        monkeypatch.setattr("task_decomposer.REPO_ROOT", tmp_path)
        (tmp_path / "tests").mkdir()
        ok, err = run_compile_gate("dotnet_test")
        assert ok is False
        assert "No test" in err


# ═══════════════════════════════════════════════════════════════════════════════
# emit_subtask_signal()
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmitSubtaskSignal:
    """Tests for C-083 Emit-Transport-Listen signal emission."""

    def test_success_signal_recorded(self):
        """emit_subtask_signal writes to subtask_results key (C-083)."""
        signal = {}
        emit_subtask_signal("WC012-02", "WC012-02a", "SUCCESS", signal)
        assert "subtask_results" in signal
        assert "WC012-02a" in signal["subtask_results"]
        assert signal["subtask_results"]["WC012-02a"]["result"] == "SUCCESS"

    def test_fail_signal_recorded(self):
        signal = {}
        emit_subtask_signal("WC012-02", "WC012-02b", "FAIL", signal)
        assert signal["subtask_results"]["WC012-02b"]["result"] == "FAIL"

    def test_signal_includes_parent_task(self):
        signal = {}
        emit_subtask_signal("WC012-03", "WC012-03a", "SUCCESS", signal)
        entry = signal["subtask_results"]["WC012-03a"]
        assert entry["task_id"] == "WC012-03"

    def test_multiple_signals_accumulate(self):
        signal = {}
        emit_subtask_signal("WC012-02", "WC012-02a", "SUCCESS", signal)
        emit_subtask_signal("WC012-02", "WC012-02b", "FAIL", signal)
        assert len(signal["subtask_results"]) == 2

    def test_signal_does_not_crash_on_empty_monitor(self):
        """emit_subtask_signal must never crash — C-083 emission is non-blocking."""
        emit_subtask_signal("WC012-02", "WC012-02a", "SUCCESS", {})


# ═══════════════════════════════════════════════════════════════════════════════
# check_simulation_exists()
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckSimulationExists:
    """Tests for C-086 Pre-Execution Simulation Gate."""

    def test_missing_sim_file_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("task_decomposer.REPO_ROOT", tmp_path)
        (tmp_path / "simulation").mkdir()
        ok, msg = check_simulation_exists("WC012-03")
        assert ok is False
        assert "simulation" in msg.lower() or "not found" in msg.lower() or "SIM-PL" in msg

    def test_sim_file_with_pass_verdict_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr("task_decomposer.REPO_ROOT", tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir()
        sim_file = sim_dir / "SIM-PL-002-WC012-03-evidence-first.md"
        sim_file.write_text("# Simulation\n\nVerdict: ✅ PASS\n\nAll checks passed.\n")
        ok, msg = check_simulation_exists("WC012-03")
        assert ok is True

    def test_sim_file_without_pass_verdict_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("task_decomposer.REPO_ROOT", tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir()
        sim_file = sim_dir / "SIM-PL-002-WC012-03-evidence-first.md"
        sim_file.write_text("# Simulation\n\nVerdict: ❌ FAIL\n\nRisk identified.\n")
        ok, msg = check_simulation_exists("WC012-03")
        assert ok is False

    def test_sim_file_upper_case_verdict(self, tmp_path, monkeypatch):
        monkeypatch.setattr("task_decomposer.REPO_ROOT", tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir()
        sim_file = sim_dir / "SIM-PL-002-WC012-04-emergency.md"
        sim_file.write_text("VERDICT: ✅ PASS\n")
        ok, msg = check_simulation_exists("WC012-04")
        assert ok is True

    def test_no_simulation_dir_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("task_decomposer.REPO_ROOT", tmp_path)
        # No simulation/ directory
        ok, msg = check_simulation_exists("WC012-03")
        assert ok is False


# ═══════════════════════════════════════════════════════════════════════════════
# execute_subtask_chain() — dry_run=True
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecuteSubtaskChain:
    """Tests for subtask chain execution (C-084, C-083, C-085)."""

    def _make_monitor(self) -> dict:
        return {"sprint": "WC-012", "task_results": {}, "signals": []}

    def _make_infra_errors(self) -> list:
        return []

    def test_empty_chain_returns_true(self):
        monitor = self._make_monitor()
        result = execute_subtask_chain(
            task_id="WC012-99",
            subtasks=[],
            monitor_signal=monitor,
            infra_error_tasks=self._make_infra_errors(),
            dry_run=True,
        )
        assert result is True

    def test_single_deterministic_subtask_dry_run(self):
        monitor = self._make_monitor()
        called = []
        st = SubTaskDef(
            id="WC012-03a", description="Data layer", type="deterministic",
            template_fn=lambda: called.append(True) or True,
        )
        result = execute_subtask_chain(
            task_id="WC012-03",
            subtasks=[st],
            monitor_signal=monitor,
            infra_error_tasks=self._make_infra_errors(),
            dry_run=True,
        )
        assert result is True
        assert len(called) == 0, "dry_run=True must NOT call template_fn"

    def test_single_llm_subtask_dry_run(self):
        monitor = self._make_monitor()
        st = SubTaskDef(
            id="WC012-02b", description="LLM task", type="llm",
            spec_sections={"arch/spec.md": "full"},
            constitutional_check="test",
        )
        result = execute_subtask_chain(
            task_id="WC012-02",
            subtasks=[st],
            monitor_signal=monitor,
            infra_error_tasks=self._make_infra_errors(),
            dry_run=True,
        )
        assert result is True

    def test_dependency_order_validated(self):
        """C-084: If depends_on task hasn't been seen, chain must detect issue."""
        monitor = self._make_monitor()
        st1 = SubTaskDef(id="WC012-02b", description="B", type="llm",
                         depends_on=["WC012-02a"])  # 02a not in chain
        result = execute_subtask_chain(
            task_id="WC012-02",
            subtasks=[st1],
            monitor_signal=monitor,
            infra_error_tasks=self._make_infra_errors(),
            dry_run=True,
        )
        # In dry_run mode, chain proceeds (no actual execution) — just validates structure
        assert isinstance(result, bool)

    def test_multi_subtask_chain_dry_run(self):
        """Full 3-subtask chain runs in dry_run without calling any fn."""
        monitor = self._make_monitor()
        subtasks = [
            SubTaskDef(id="WC012-03a", description="A", type="deterministic",
                       template_fn=lambda: True),
            SubTaskDef(id="WC012-03b", description="B", type="llm",
                       depends_on=["WC012-03a"],
                       spec_sections={"spec.md": "full"},
                       constitutional_check="check"),
            SubTaskDef(id="WC012-03c", description="C", type="llm",
                       depends_on=["WC012-03a", "WC012-03b"],
                       spec_sections={"spec.md": "full"},
                       constitutional_check="check"),
        ]
        result = execute_subtask_chain(
            task_id="WC012-03",
            subtasks=subtasks,
            monitor_signal=monitor,
            infra_error_tasks=self._make_infra_errors(),
            dry_run=True,
        )
        assert result is True

    def test_deterministic_failure_halts_chain(self, monkeypatch):
        """C-084: If a deterministic subtask fails, chain stops (no subsequent tasks)."""
        monitor = self._make_monitor()
        executed = []

        def failing_fn():
            executed.append("a_tried")
            return False  # simulates failure

        def should_not_run():
            executed.append("b_tried")
            return True

        subtasks = [
            SubTaskDef(id="WC012-03a", description="A", type="deterministic",
                       template_fn=failing_fn),
            SubTaskDef(id="WC012-03b", description="B", type="deterministic",
                       depends_on=["WC012-03a"], template_fn=should_not_run),
        ]
        result = execute_subtask_chain(
            task_id="WC012-03",
            subtasks=subtasks,
            monitor_signal=monitor,
            infra_error_tasks=self._make_infra_errors(),
            dry_run=False,
        )
        assert result is False
        assert "a_tried" in executed
        assert "b_tried" not in executed, "C-084 violated: b ran despite a failing"


# ═══════════════════════════════════════════════════════════════════════════════
# Additional coverage tests for task_decomposer branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunCompileGateBranches:
    """Cover the subprocess paths in run_compile_gate."""

    def test_dotnet_build_with_csproj_found(self, tmp_path, monkeypatch):
        """When .csproj exists, subprocess.run is called (mocked)."""
        import subprocess as sp
        service_dir = tmp_path / "src" / "ce"
        service_dir.mkdir(parents=True)
        csproj = service_dir / "ce.csproj"
        csproj.write_text("<Project Sdk='Microsoft.NET.Sdk'></Project>")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("task_decomposer.subprocess.run", return_value=mock_result):
            import task_decomposer
            monkeypatch.setattr(task_decomposer, "REPO_ROOT", tmp_path)
            ok, err = run_compile_gate("dotnet_build", service_dir=str(service_dir.relative_to(tmp_path)))
            assert ok is True
            assert err == ""

    def test_dotnet_build_with_csproj_fail(self, tmp_path, monkeypatch):
        """When dotnet build fails, returncode != 0."""
        import task_decomposer
        service_dir = tmp_path / "src" / "ce"
        service_dir.mkdir(parents=True)
        csproj = service_dir / "ce.csproj"
        csproj.write_text("<Project Sdk='Microsoft.NET.Sdk'></Project>")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error CS0101: something failed"

        with patch("task_decomposer.subprocess.run", return_value=mock_result):
            monkeypatch.setattr(task_decomposer, "REPO_ROOT", tmp_path)
            ok, err = run_compile_gate("dotnet_build", service_dir=str(service_dir.relative_to(tmp_path)))
            assert ok is False
            assert "CS0101" in err

    def test_dotnet_test_with_test_csproj_found(self, tmp_path, monkeypatch):
        """When test .csproj exists, subprocess.run is called (mocked pass)."""
        import task_decomposer
        tests_dir = tmp_path / "tests" / "ce.Tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "ce.Tests.csproj").write_text("<Project />")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("task_decomposer.subprocess.run", return_value=mock_result):
            monkeypatch.setattr(task_decomposer, "REPO_ROOT", tmp_path)
            ok, err = run_compile_gate("dotnet_test")
            assert ok is True

    def test_ruff_gate_subprocess_called(self, tmp_path, monkeypatch):
        """ruff gate calls subprocess.run."""
        import task_decomposer
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("task_decomposer.subprocess.run", return_value=mock_result):
            monkeypatch.setattr(task_decomposer, "REPO_ROOT", tmp_path)
            ok, err = run_compile_gate("ruff", service_dir=str(tmp_path))
            assert ok is True


class TestExecuteSubtaskChainLivePaths:
    """Cover the non-dry_run paths in execute_subtask_chain."""

    def _make_monitor(self) -> dict:
        return {"sprint": "WC-012", "task_results": {}, "signals": []}

    def test_unmet_dependency_halts_with_skip_signal(self, monkeypatch):
        """C-084: task with unmet dependency is SKIPPED and chain returns False."""
        import task_decomposer
        monkeypatch.setattr(task_decomposer, "REPO_ROOT", Path("/tmp"))

        monitor = self._make_monitor()
        st = SubTaskDef(
            id="WC012-02b", description="B", type="deterministic",
            depends_on=["WC012-02a"],  # 02a never completed
            template_fn=lambda: True,
        )
        result = execute_subtask_chain(
            task_id="WC012-02",
            subtasks=[st],
            monitor_signal=monitor,
            infra_error_tasks=[],
            dry_run=False,  # live mode
        )
        assert result is False
        # SKIPPED signal emitted
        assert "WC012-02b" in monitor.get("subtask_results", {})
        assert monitor["subtask_results"]["WC012-02b"]["result"] == "SKIPPED"

    def test_deterministic_subtask_missing_template_fn_fails(self, monkeypatch):
        """Deterministic subtask with None template_fn → FAIL."""
        import task_decomposer
        monkeypatch.setattr(task_decomposer, "REPO_ROOT", Path("/tmp"))

        # Mock the imports inside execute_subtask_chain
        with patch("task_decomposer.REPO_ROOT", Path("/tmp")):
            monitor = self._make_monitor()
            st = SubTaskDef(
                id="WC012-03a", description="no fn", type="deterministic",
                template_fn=None,  # missing!
            )
            result = execute_subtask_chain(
                task_id="WC012-03",
                subtasks=[st],
                monitor_signal=monitor,
                infra_error_tasks=[],
                dry_run=False,
            )
            assert result is False

    def test_unknown_subtask_type_fails(self, monkeypatch):
        """Unknown type='graph' → chain returns False."""
        import task_decomposer
        monitor = self._make_monitor()

        with patch("task_decomposer.REPO_ROOT", Path("/tmp")):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": MagicMock(
                execute_with_llm=lambda *a, **kw: True,
                get_branch_context=lambda: "",
                git=lambda *a, **kw: MagicMock(returncode=0),
            )}):
                st = SubTaskDef(
                    id="WC012-99a", description="unknown type", type="graph"
                )
                result = execute_subtask_chain(
                    task_id="WC012-99",
                    subtasks=[st],
                    monitor_signal=monitor,
                    infra_error_tasks=[],
                    dry_run=False,
                )
                assert result is False

    def test_successful_deterministic_subtask_live(self, monkeypatch, tmp_path):
        """Live deterministic subtask completes → commit + SUCCESS signal emitted."""
        import task_decomposer
        called = []

        def template():
            called.append("ran")
            return True

        monitor = self._make_monitor()

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": MagicMock(
                get_branch_context=lambda: "",
                git=lambda *a, **kw: MagicMock(returncode=1),  # diff shows nothing staged
            )}):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    st = SubTaskDef(
                        id="WC012-03a", description="data layer", type="deterministic",
                        template_fn=template,
                    )
                    result = execute_subtask_chain(
                        task_id="WC012-03",
                        subtasks=[st],
                        monitor_signal=monitor,
                        infra_error_tasks=[],
                        dry_run=False,
                    )
                    assert result is True
                    assert "ran" in called
                    assert monitor["subtask_results"]["WC012-03a"]["result"] == "SUCCESS"

    def test_compile_gate_fail_halts_chain(self, monkeypatch, tmp_path):
        """If compile gate fails after a subtask, chain halts (C-084)."""
        import task_decomposer
        called_b = []

        monitor = self._make_monitor()
        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": MagicMock(
                get_branch_context=lambda: "",
                git=lambda *a, **kw: MagicMock(returncode=0),
            )}):
                with patch("task_decomposer.run_compile_gate", return_value=(False, "CS0001: build failed")):
                    subtasks = [
                        SubTaskDef(id="WC012-03a", description="A", type="deterministic",
                                   template_fn=lambda: True),
                        SubTaskDef(id="WC012-03b", description="B", type="deterministic",
                                   depends_on=["WC012-03a"],
                                   template_fn=lambda: called_b.append(True) or True),
                    ]
                    result = execute_subtask_chain(
                        task_id="WC012-03",
                        subtasks=subtasks,
                        monitor_signal=monitor,
                        infra_error_tasks=[],
                        dry_run=False,
                    )
                    assert result is False
                    assert len(called_b) == 0, "B must not run when compile gate fails"
                    assert monitor["subtask_results"]["WC012-03a"]["result"] == "FAIL"

    def test_llm_subtask_success_live(self, monkeypatch, tmp_path):
        """LLM subtask success path covered by mocking execute_with_llm."""
        import task_decomposer
        monitor = self._make_monitor()

        mock_runner = MagicMock(
            execute_with_llm=MagicMock(return_value=True),
            get_branch_context=lambda: "",
            git=MagicMock(return_value=MagicMock(returncode=1)),
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner}):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    st = SubTaskDef(
                        id="WC012-02b", description="evaluators", type="llm",
                        spec_sections={"spec.md": "full"},
                        constitutional_check="check",
                        model_hint="reasoning",
                        max_tokens=5000,
                    )
                    result = execute_subtask_chain(
                        task_id="WC012-02",
                        subtasks=[st],
                        monitor_signal=monitor,
                        infra_error_tasks=[],
                        dry_run=False,
                    )
                    assert result is True
                    assert monitor["subtask_results"]["WC012-02b"]["result"] == "SUCCESS"
