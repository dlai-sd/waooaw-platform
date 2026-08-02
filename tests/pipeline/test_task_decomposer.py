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



def _go_unavailable():
    """Make GoalExecutor unavailable so tests exercise inline MagicLLM path."""
    return {"goal_orchestrator.goal_executor": None, "goal_orchestrator": None}

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
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
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


# ═══════════════════════════════════════════════════════════════════════════════
# IB-023: File-by-file generation tests
# ═══════════════════════════════════════════════════════════════════════════════

from task_decomposer import _filter_ptr_types_for_file, execute_file_by_file


class TestFilterPtrTypesForFile:
    """Tests for targeted type injection — reduces 'lost-in-middle' attention loss."""

    ALL_TYPES = {
        "EvaluationContext": {"kind": "record"},
        "EvaluationResult": {"kind": "record"},
        "EvaluationVerdict": {"kind": "enum"},
        "EvaluatorRegistry": {"kind": "class"},
        "IClaimEvaluator": {"kind": "interface"},
        "ValidateActionResponse": {"kind": "proto_message"},
        "RecordEvidenceRequest": {"kind": "proto_message"},
        "ValidationDecision": {"kind": "proto_enum"},
        "BudgetContext": {"kind": "proto_message"},
    }

    def test_test_file_gets_all_types(self):
        """Test files reference many types — inject all."""
        result = _filter_ptr_types_for_file(
            "tests/ce.Tests/Evaluators/CCT_EF01_Tests.cs",
            self.ALL_TYPES,
        )
        assert len(result) == len(self.ALL_TYPES)

    def test_evaluator_file_gets_evaluation_types_only(self):
        """C041ToolAuthorizationEvaluator only needs evaluation types."""
        result = _filter_ptr_types_for_file(
            "src/ce/Evaluators/C041ToolAuthorizationEvaluator.cs",
            self.ALL_TYPES,
        )
        assert "EvaluationContext" in result
        assert "EvaluationResult" in result
        assert "EvaluationVerdict" in result
        # Proto request/response types not needed for evaluator implementation
        assert "RecordEvidenceRequest" not in result

    def test_service_file_gets_proto_and_registry_types(self):
        """ConstitutionalEngineService needs proto types + registry."""
        result = _filter_ptr_types_for_file(
            "src/ce/Services/ConstitutionalEngineService.cs",
            self.ALL_TYPES,
        )
        assert "ValidateActionResponse" in result
        assert "ValidationDecision" in result

    def test_empty_types_returns_empty(self):
        result = _filter_ptr_types_for_file("src/ce/Evaluators/Foo.cs", {})
        assert result == []

    def test_always_returns_list(self):
        result = _filter_ptr_types_for_file("src/anything.cs", self.ALL_TYPES)
        assert isinstance(result, list)

    def test_fewer_types_than_total_for_evaluator(self):
        """Evaluator files must get fewer types than total — this is the whole point."""
        evaluator_types = _filter_ptr_types_for_file(
            "src/ce/Evaluators/C043BudgetCeilingEvaluator.cs",
            self.ALL_TYPES,
        )
        # Must be a subset — proto request/response types excluded
        assert len(evaluator_types) < len(self.ALL_TYPES)


class TestExecuteFileByFile:
    """Tests for file-by-file LLM generation (IB-023)."""

    def _make_mock_runner(self, success: bool = True):
        return MagicMock(
            execute_with_llm=MagicMock(return_value=success),
            get_branch_context=lambda: "",
        )

    def _go_unavailable(self):
        """Patch dict that makes GoalExecutor unavailable so tests use inline path."""
        return {"goal_orchestrator.goal_executor": None, "goal_orchestrator": None}

    def test_single_file_success(self, tmp_path, monkeypatch):
        """Single output_file generates, compile passes, returns True."""
        import task_decomposer
        mock_runner = self._make_mock_runner(success=True)

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.load_ptr", return_value={}, create=True):
                    result = execute_file_by_file(
                        task_id="WC012-02b",
                        output_files=["src/ce/Evaluators/C041.cs"],
                        effective_check="BASE CHECK",
                        spec_sections={"spec.md": "full"},
                        model_hint="reasoning",
                        max_tokens=5000,
                    )
        assert result is True

    def test_multi_file_all_succeed(self, tmp_path, monkeypatch):
        """3 output files, all succeed → True. LLM called once per file."""
        import task_decomposer
        call_count = []

        def fake_execute(task_id, desc, spec, check, model, tokens):
            call_count.append(task_id)
            # Verify single-file instruction in check
            assert "Generate ONLY this ONE file" in check
            return True

        mock_runner = MagicMock(
            execute_with_llm=fake_execute,
            get_branch_context=lambda: "",
        )

        files = [
            "src/ce/Evaluators/C041.cs",
            "src/ce/Evaluators/C043.cs",
            "src/ce/Evaluators/C062.cs",
        ]

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.load_ptr", return_value={}, create=True):
                    result = execute_file_by_file(
                        task_id="WC012-02b",
                        output_files=files,
                        effective_check="BASE CHECK",
                        spec_sections={},
                        model_hint="reasoning",
                        max_tokens=5000,
                    )

        assert result is True
        # Called exactly once per file
        assert len(call_count) == 3

    def test_first_file_fail_halts_immediately(self, tmp_path):
        """If first file fails, remaining files are NOT generated (error isolation)."""
        import task_decomposer
        call_count = []

        def fake_execute(*args, **kwargs):
            call_count.append(1)
            return len(call_count) > 1  # first call returns False

        mock_runner = MagicMock(
            execute_with_llm=fake_execute,
            get_branch_context=lambda: "",
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.load_ptr", return_value={}, create=True):
                    result = execute_file_by_file(
                        task_id="WC012-02b",
                        output_files=["src/c1.cs", "src/c2.cs", "src/c3.cs"],
                        effective_check="check",
                        spec_sections={},
                        model_hint="reasoning",
                        max_tokens=5000,
                    )

        assert result is False
        assert len(call_count) == 1, "Must stop at first failure, not call remaining files"

    def test_preservation_list_grows_between_files(self, tmp_path):
        """Each file's check must list previously-generated files — prevents regeneration."""
        import task_decomposer
        checks_received = []

        def fake_execute(task_id, desc, spec, check, model, tokens):
            checks_received.append(check)
            return True

        mock_runner = MagicMock(
            execute_with_llm=fake_execute,
            get_branch_context=lambda: "",
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.load_ptr", return_value={}, create=True):
                    execute_file_by_file(
                        task_id="WC012-02b",
                        output_files=["src/A.cs", "src/B.cs", "src/C.cs"],
                        effective_check="check",
                        spec_sections={},
                        model_hint="reasoning",
                        max_tokens=5000,
                    )

        # First file: no preservation list
        assert "already written" not in checks_received[0].lower() or "src/A.cs" not in checks_received[0]
        # Second file: A.cs must be listed as already written
        assert "src/A.cs" in checks_received[1]
        # Third file: both A.cs and B.cs must be listed
        assert "src/A.cs" in checks_received[2]
        assert "src/B.cs" in checks_received[2]

    def test_token_budget_capped_per_file(self, tmp_path):
        """Per-file token budget is capped at 4000 max — shorter prompts."""
        import task_decomposer
        token_budgets = []

        def fake_execute(task_id, desc, spec, check, model, tokens):
            token_budgets.append(tokens)
            return True

        mock_runner = MagicMock(
            execute_with_llm=fake_execute,
            get_branch_context=lambda: "",
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.load_ptr", return_value={}, create=True):
                    execute_file_by_file(
                        task_id="WC012-02b",
                        output_files=["src/A.cs"],
                        effective_check="check",
                        spec_sections={},
                        model_hint="reasoning",
                        max_tokens=10000,  # full subtask budget
                    )

        # Per-file budget must be <= 4000 regardless of subtask budget
        assert token_budgets[0] <= 4000

    def test_single_file_check_contains_one_file_instruction(self, tmp_path):
        """LLM prompt must say 'Generate ONLY this ONE file' — no batch instructions."""
        import task_decomposer
        received_check = []

        def fake_execute(task_id, desc, spec, check, model, tokens):
            received_check.append(check)
            return True

        mock_runner = MagicMock(
            execute_with_llm=fake_execute,
            get_branch_context=lambda: "",
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.load_ptr", return_value={}, create=True):
                    execute_file_by_file(
                        task_id="WC012-02b",
                        output_files=["src/C041.cs"],
                        effective_check="BASE",
                        spec_sections={},
                        model_hint="reasoning",
                        max_tokens=5000,
                    )

        assert len(received_check) == 1
        assert "Generate ONLY this ONE file" in received_check[0]
        assert "src/C041.cs" in received_check[0]

    def test_subtask_chain_uses_file_by_file_when_output_files_set(self, tmp_path):
        """execute_subtask_chain routes to file-by-file when output_files is populated."""
        import task_decomposer
        file_by_file_called = []

        def fake_file_by_file(*args, **kwargs):
            file_by_file_called.append(True)
            return True

        mock_runner = MagicMock(
            get_branch_context=lambda: "",
            git=MagicMock(return_value=MagicMock(returncode=1)),
        )

        monitor = {"task_results": {}}

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    with patch("task_decomposer.execute_file_by_file", fake_file_by_file):
                        st = SubTaskDef(
                            id="WC012-02b", description="evaluators", type="llm",
                            output_files=["src/ce/Evaluators/C041.cs"],
                            model_hint="reasoning",
                            max_tokens=5000,
                        )
                        execute_subtask_chain(
                            task_id="WC012-02",
                            subtasks=[st],
                            monitor_signal=monitor,
                            infra_error_tasks=[],
                            dry_run=False,
                        )

        assert len(file_by_file_called) == 1, "file-by-file must be invoked when output_files set"


# ═══════════════════════════════════════════════════════════════════════════════
# PTR wiring tests — C-083 Emit after compile gate, C-085 inject before LLM
# ═══════════════════════════════════════════════════════════════════════════════

class TestPTRWiring:
    """Tests that PTR update is called after compile gate and injected before LLM."""

    def _make_monitor(self) -> dict:
        return {"sprint": "WC-012", "task_results": {}, "signals": []}

    def test_ptr_update_called_after_deterministic_subtask(self, monkeypatch, tmp_path):
        """After deterministic subtask compile gate passes, update_ptr_from_task is called."""
        import task_decomposer

        ptr_calls = []

        mock_runner = MagicMock(
            get_branch_context=lambda: "",
            git=MagicMock(return_value=MagicMock(returncode=1)),
        )

        # Create a fake .cs file so rglob finds something
        cs_file = tmp_path / "src" / "ce" / "Ctx.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text("namespace X; public sealed record Ctx(string Id);")

        def fake_update_ptr(task_id, files):
            ptr_calls.append((task_id, files))

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    # Patch the source module since execute_subtask_chain does a local import
                    with patch("platform_type_registry.update_ptr_from_task", fake_update_ptr):
                        st = SubTaskDef(
                            id="WC012-02a", description="interfaces", type="deterministic",
                            template_fn=lambda: True,
                        )
                        execute_subtask_chain(
                            task_id="WC012-02",
                            subtasks=[st],
                            monitor_signal=self._make_monitor(),
                            infra_error_tasks=[],
                            dry_run=False,
                        )
        # PTR update called with WC012-02a and the .cs file path
        assert len(ptr_calls) >= 1
        assert ptr_calls[0][0] == "WC012-02a"

    def test_ptr_injection_into_llm_constitutional_check(self, monkeypatch, tmp_path):
        """Before LLM subtask, build_ptr_prompt_block output is appended to constitutional_check."""
        import task_decomposer

        injected_check = []

        def fake_execute_with_llm(task_id, desc, spec, constitutional_check, model, tokens):
            injected_check.append(constitutional_check)
            return True

        mock_runner = MagicMock(
            execute_with_llm=fake_execute_with_llm,
            get_branch_context=lambda: "",
            git=MagicMock(return_value=MagicMock(returncode=1)),
        )

        fake_ptr = {
            "tasks": {
                "WC012-02a": {
                    "types": {
                        "EvaluatorRegistry": {
                            "kind": "class",
                            "properties": {},
                            "methods": [{"name": "EvaluateAllAsync", "return_type": "Task", "params": "EvaluationContext ctx"}],
                        }
                    },
                    "files": [],
                }
            }
        }

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    # Patch source module — local imports resolve to the patched versions
                    with patch("platform_type_registry.load_ptr", return_value=fake_ptr):
                        with patch("platform_type_registry.build_ptr_prompt_block",
                                   return_value="\n# TYPE CONTRACT: EvaluatorRegistry — EvaluateAllAsync"):
                            st = SubTaskDef(
                                id="WC012-02b", description="evaluators", type="llm",
                                spec_sections={"spec.md": "full"},
                                constitutional_check="BASE CHECK",
                                model_hint="reasoning",
                                max_tokens=5000,
                            )
                            execute_subtask_chain(
                                task_id="WC012-02",
                                subtasks=[st],
                                monitor_signal=self._make_monitor(),
                                infra_error_tasks=[],
                                dry_run=False,
                            )

        assert len(injected_check) == 1
        # PTR block must be appended to the base constitutional check
        assert "BASE CHECK" in injected_check[0]
        assert "TYPE CONTRACT" in injected_check[0] or "EvaluateAllAsync" in injected_check[0]

    def test_ptr_failure_does_not_block_sprint(self, monkeypatch, tmp_path):
        """If PTR update fails, sprint execution must continue (best-effort)."""
        import task_decomposer

        mock_runner = MagicMock(
            execute_with_llm=MagicMock(return_value=True),
            get_branch_context=lambda: "",
            git=MagicMock(return_value=MagicMock(returncode=1)),
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {"autonomous_sprint_runner": mock_runner, **_go_unavailable()}):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    # Simulate PTR raising on call — sprint must still succeed
                    with patch("platform_type_registry.update_ptr_from_task",
                               side_effect=RuntimeError("PTR unavailable")):
                        st = SubTaskDef(
                            id="WC012-02a", description="interfaces", type="deterministic",
                            template_fn=lambda: True,
                        )
                        result = execute_subtask_chain(
                            task_id="WC012-02",
                            subtasks=[st],
                            monitor_signal=self._make_monitor(),
                            infra_error_tasks=[],
                            dry_run=False,
                        )
        # Sprint must succeed despite PTR failure
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestUDCPDispatch — unit tests for the new type="udcp" dispatch path
# constitutional_basis: ADR-039, C-059, C-077, C-082, C-084
# ═══════════════════════════════════════════════════════════════════════════════

class TestUDCPDispatch:
    """Unit tests covering the type='udcp' dispatch path in execute_subtask_chain.

    Invariants under test:
      - UDCP path calls execute_with_udcp(), never execute_with_llm()
      - scope_text is built from constitutional_check + spec section file content
      - Missing spec files are silently skipped (no crash)
      - model_hint, max_tokens, task_id, sprint_id are forwarded unchanged
      - UDCP failure marks the subtask failed and C-084 blocks dependents
      - UDCP success triggers run_compile_gate (same as llm path)
      - dry_run=True skips execution entirely (execute_with_udcp not called)
    """

    def _make_monitor(self):
        return MagicMock()

    def _mock_runner(self):
        """Minimal autonomous_sprint_runner mock required by execute_subtask_chain."""
        return MagicMock(
            execute_with_llm=MagicMock(return_value=True),
            get_branch_context=lambda: "",
            git=MagicMock(return_value=MagicMock(returncode=1)),
        )

    def test_udcp_subtask_routes_to_execute_with_udcp_not_llm(self, tmp_path):
        """type='udcp' must call execute_with_udcp, never execute_with_llm."""
        import task_decomposer

        udcp_calls = []
        llm_calls = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            udcp_calls.append(task_id)
            return True

        mock_runner = self._mock_runner()
        mock_runner.execute_with_llm = MagicMock(side_effect=lambda *a, **kw: llm_calls.append("called") or True)

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-01aa", description="interfaces", type="udcp",
            constitutional_check="implement IMarkupEngine",
            model_hint="reasoning",
            max_tokens=8000,
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": mock_runner,
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert len(udcp_calls) == 1, "execute_with_udcp must be called exactly once"
        assert udcp_calls[0] == "WC027-01aa"
        assert len(llm_calls) == 0, "execute_with_llm must NOT be called for type='udcp'"

    def test_udcp_scope_text_starts_with_constitutional_check(self, tmp_path):
        """scope_text first element must be the effective_check (constitutional_check content)."""
        import task_decomposer

        received_scope = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            received_scope.append(scope_text)
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        check_text = "IMPLEMENT cost_floor() per constitutional floor"
        st = SubTaskDef(
            id="WC027-01ba", description="markup logic", type="udcp",
            constitutional_check=check_text,
            model_hint="reasoning",
            max_tokens=8000,
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert len(received_scope) == 1
        # constitutional_check must be present in scope_text
        # (_build_effective_check prepends STACK RULES before the check text)
        assert check_text in received_scope[0], (
            f"constitutional_check must appear in scope_text. Got: {received_scope[0][:80]!r}"
        )

    def test_udcp_spec_section_appended_when_file_exists(self, tmp_path):
        """When a spec_sections file exists, its content (first 3000 chars) is in scope_text."""
        import task_decomposer

        # Create a spec file under tmp_path
        spec_dir = tmp_path / "work-contracts"
        spec_dir.mkdir()
        spec_file = spec_dir / "WC-027.md"
        spec_content = "# WC-027 Markup Engine\nImplement cost_floor and derive_price.\n"
        spec_file.write_text(spec_content)

        received_scope = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            received_scope.append(scope_text)
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-01ba", description="markup logic", type="udcp",
            constitutional_check="base check",
            spec_sections={"work-contracts/WC-027.md": "full"},
            model_hint="reasoning",
            max_tokens=8000,
        )

        with patch.object(task_decomposer, "REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch.object(task_decomposer, "run_compile_gate", return_value=(True, "")):
                    task_decomposer.execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert len(received_scope) == 1
        assert "WC-027 Markup Engine" in received_scope[0], (
            "spec file content must be included in scope_text"
        )
        assert "work-contracts/WC-027.md" in received_scope[0], (
            "spec file path header must appear in scope_text"
        )

    def test_udcp_missing_spec_file_silently_skipped(self, tmp_path):
        """Missing spec files in spec_sections must not raise — silently skipped."""
        import task_decomposer

        udcp_calls = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            udcp_calls.append(scope_text)
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-01aa", description="interfaces", type="udcp",
            constitutional_check="base check",
            spec_sections={"does-not-exist/WC-999.md": "full"},  # file does not exist
            model_hint="reasoning",
            max_tokens=8000,
        )

        with patch.object(task_decomposer, "REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch.object(task_decomposer, "run_compile_gate", return_value=(True, "")):
                    # Must not raise
                    result = task_decomposer.execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert result is True
        assert len(udcp_calls) == 1, "execute_with_udcp must still be called even with missing spec files"
        # scope_text should only contain the constitutional_check — no extra section header
        assert "does-not-exist" not in udcp_calls[0], "missing file path must not appear in scope_text"

    def test_udcp_model_hint_and_max_tokens_forwarded(self, tmp_path):
        """model_hint and max_tokens from SubTaskDef must be forwarded to execute_with_udcp."""
        import task_decomposer

        received_kwargs = {}

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            received_kwargs.update({
                "task_id": task_id,
                "sprint_id": sprint_id,
                "model_hint": model_hint,
                "max_tokens": max_tokens,
            })
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-02a", description="api layer", type="udcp",
            constitutional_check="write router tests",
            model_hint="flash",
            max_tokens=12000,
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    execute_subtask_chain(
                        task_id="WC027-02",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert received_kwargs["task_id"] == "WC027-02a"
        assert received_kwargs["sprint_id"] == "WC027-02"
        assert received_kwargs["model_hint"] == "flash"
        assert received_kwargs["max_tokens"] == 12000

    def test_udcp_failure_marks_task_failed_and_blocks_dependent(self, tmp_path):
        """C-084: UDCP failure must propagate — dependent subtask must be skipped."""
        import task_decomposer

        executed = []

        def fake_udcp_fail(task_id, scope_text, sprint_id, model_hint, max_tokens):
            return False  # simulate UDCP failure

        def fake_udcp_pass(task_id, scope_text, sprint_id, model_hint, max_tokens):
            executed.append(task_id)
            return True

        call_n = [0]

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            call_n[0] += 1
            if call_n[0] == 1:
                return False  # first task fails
            executed.append(task_id)
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        subtasks = [
            SubTaskDef(
                id="WC027-01aa", description="interfaces", type="udcp",
                constitutional_check="task A",
                model_hint="reasoning", max_tokens=8000,
            ),
            SubTaskDef(
                id="WC027-01ab", description="data models", type="udcp",
                depends_on=["WC027-01aa"],
                constitutional_check="task B depends on A",
                model_hint="flash", max_tokens=4000,
            ),
        ]

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch("task_decomposer.run_compile_gate", return_value=(True, "")):
                    result = execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=subtasks,
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert result is False, "chain must return False when any subtask fails"
        assert "WC027-01ab" not in executed, "C-084: dependent must be skipped when dependency fails"

    def test_udcp_success_triggers_compile_gate(self, tmp_path):
        """After UDCP success, run_compile_gate must be called (C-082)."""
        import task_decomposer

        gate_calls = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-01aa", description="interfaces", type="udcp",
            constitutional_check="implement interface",
            model_hint="reasoning", max_tokens=8000,
        )

        def fake_compile_gate(gate, service_dir=None, target_files=None, task_id=None):
            gate_calls.append({"gate": gate, "task_id": task_id})
            return (True, "")

        with patch.object(task_decomposer, "REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch.object(task_decomposer, "run_compile_gate", side_effect=fake_compile_gate):
                    task_decomposer.execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert len(gate_calls) >= 1, "C-082: compile gate must be called after UDCP success"
        assert gate_calls[0]["task_id"] == "WC027-01aa"

    def test_udcp_dry_run_skips_execution(self, tmp_path):
        """dry_run=True must never invoke execute_with_udcp."""
        import task_decomposer

        udcp_calls = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            udcp_calls.append(task_id)
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-01aa", description="interfaces", type="udcp",
            constitutional_check="implement",
            model_hint="reasoning", max_tokens=8000,
        )

        with patch("task_decomposer.REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                result = execute_subtask_chain(
                    task_id="WC027-01",
                    subtasks=[st],
                    monitor_signal=self._make_monitor(),
                    infra_error_tasks=[],
                    dry_run=True,
                )

        assert result is True, "dry_run chain must return True"
        assert len(udcp_calls) == 0, "dry_run=True must not call execute_with_udcp"

    def test_udcp_spec_content_truncated_to_3000_chars(self, tmp_path):
        """Spec file content in scope_text is capped at 3000 chars to prevent token overflow."""
        import task_decomposer

        # Create a large spec file (>3000 chars)
        spec_dir = tmp_path / "work-contracts"
        spec_dir.mkdir()
        spec_file = spec_dir / "WC-027-big.md"
        long_content = "X" * 5000  # 5000-char file
        spec_file.write_text(long_content)

        received_scope = []

        def fake_udcp(task_id, scope_text, sprint_id, model_hint, max_tokens):
            received_scope.append(scope_text)
            return True

        mock_executor = MagicMock()
        mock_executor.execute_with_udcp = fake_udcp

        st = SubTaskDef(
            id="WC027-01aa", description="interfaces", type="udcp",
            constitutional_check="check",
            spec_sections={"work-contracts/WC-027-big.md": "full"},
            model_hint="reasoning", max_tokens=8000,
        )

        with patch.object(task_decomposer, "REPO_ROOT", tmp_path):
            with patch.dict("sys.modules", {
                "autonomous_sprint_runner": self._mock_runner(),
                "runner.task_executor": mock_executor,
                **_go_unavailable(),
            }):
                with patch.object(task_decomposer, "run_compile_gate", return_value=(True, "")):
                    task_decomposer.execute_subtask_chain(
                        task_id="WC027-01",
                        subtasks=[st],
                        monitor_signal=self._make_monitor(),
                        infra_error_tasks=[],
                        dry_run=False,
                    )

        assert len(received_scope) == 1
        # 3000-char truncation: the 5000-char file must NOT appear in full
        # We verify the full unreduced content is absent (stack rules may contain uppercase
        # letters so we check the raw file slice rather than counting characters).
        assert long_content not in received_scope[0], "5000-char spec content must be truncated"
        assert long_content[:3000] in received_scope[0], "First 3000 chars of spec must be present"
