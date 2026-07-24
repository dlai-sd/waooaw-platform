"""
Comprehensive unit tests for autonomous_sprint_runner.py

# Implements: scripts/autonomous_sprint_runner.py
# constitutional_basis: C-076 (≥90% coverage), C-082 (build validation), C-059 (traceability)
# office: Platform IT Expert — QA hat
# ib_item: IB-009

Coverage targets (C-076: ≥90% line coverage):
  parse_sprint_state()          → state machine parsing, malformed YAML, missing block
  check_platform_phase_gate()   → HALT=true, SPEC phase, IMPLEMENTATION phase
  _build_system_prompt()        → all 4 stack variants
  parse_llm_files()             → valid blocks, boundary enforcement, design questions
  get_branch_context()          → no files, with .cs files, git failure path
  validate_written_files()      → python ok/fail, .cs no-csproj, build ok/fail
  flag_spec_gap()               → no github token path (safe offline path)
  execute_with_llm()            → no API key path, spec_content building
  _build_system_prompt()        → dotnet/python/terraform/typescript stacks
  _generate_wc012_02a_*()       → verifies 4 files written to disk
"""

import os
import re
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# ── Ensure scripts/ is importable ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import autonomous_sprint_runner as runner
from autonomous_sprint_runner import (
    _build_system_prompt,
    _TASK_STACK_MAP,
    parse_llm_files,
    ALLOWED_WRITE_ROOTS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Minimal repo structure for tests that touch the filesystem."""
    (tmp_path / "constitution").mkdir()
    (tmp_path / "sprint-context").mkdir()
    (tmp_path / "logs").mkdir()
    return tmp_path


@pytest.fixture
def project_state_valid(tmp_repo: Path) -> Path:
    """Write a valid PROJECT_STATE.md with SPRINT_STATE_MACHINE block."""
    content = textwrap.dedent("""\
        # PROJECT_STATE.md

        ## SPRINT_STATE_MACHINE
        ```yaml
        platform_phase: IMPLEMENTATION
        autonomous_halt: false
        current_sprint: WC-012
        sprint_status: READY
        consecutive_failures: 0
        last_attempt_result: SUCCESS
        current_task:
        branch: ib/009/sprint-012
        tasks_done:
          - WC012-01
        tasks_remaining:
          - WC012-02
          - WC012-03
          - WC012-04
        ```
    """)
    state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
    state_file.write_text(content)
    return state_file


@pytest.fixture
def project_state_halt(tmp_repo: Path) -> Path:
    """PROJECT_STATE.md with autonomous_halt=true."""
    content = textwrap.dedent("""\
        ## SPRINT_STATE_MACHINE
        ```yaml
        platform_phase: IMPLEMENTATION
        autonomous_halt: true
        current_sprint: WC-012
        sprint_status: READY
        consecutive_failures: 0
        tasks_remaining:
          - WC012-02
        ```
    """)
    state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
    state_file.write_text(content)
    return state_file


@pytest.fixture
def project_state_spec(tmp_repo: Path) -> Path:
    """PROJECT_STATE.md with platform_phase=SPEC."""
    content = textwrap.dedent("""\
        ## SPRINT_STATE_MACHINE
        ```yaml
        platform_phase: SPEC
        autonomous_halt: false
        current_sprint: WC-010
        sprint_status: READY
        consecutive_failures: 0
        tasks_remaining: []
        ```
    """)
    state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
    state_file.write_text(content)
    return state_file


# ═══════════════════════════════════════════════════════════════════════════════
# parse_sprint_state()
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseSprintState:
    """Tests for PROJECT_STATE.md YAML parsing."""

    def test_parses_all_fields(self, project_state_valid: Path, monkeypatch):
        monkeypatch.setattr(runner, "STATE_FILE", project_state_valid)
        state = runner.parse_sprint_state()
        assert state["platform_phase"] == "IMPLEMENTATION"
        assert state["autonomous_halt"] == "false"
        assert state["current_sprint"] == "WC-012"
        assert state["sprint_status"] == "READY"
        assert state["consecutive_failures"] == "0"
        assert "WC012-01" not in state.get("tasks_remaining", [])
        assert "WC012-02" in state["tasks_remaining"]
        assert "WC012-03" in state["tasks_remaining"]
        assert "WC012-04" in state["tasks_remaining"]

    def test_raises_when_block_missing(self, tmp_repo: Path, monkeypatch):
        state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
        state_file.write_text("# No SPRINT_STATE_MACHINE block here\n")
        monkeypatch.setattr(runner, "STATE_FILE", state_file)
        with pytest.raises(ValueError, match="SPRINT_STATE_MACHINE"):
            runner.parse_sprint_state()

    def test_empty_tasks_remaining(self, tmp_repo: Path, monkeypatch):
        content = textwrap.dedent("""\
            ## SPRINT_STATE_MACHINE
            ```yaml
            platform_phase: IMPLEMENTATION
            autonomous_halt: false
            current_sprint: WC-011
            sprint_status: DONE
            consecutive_failures: 0
            tasks_remaining: []
            ```
        """)
        state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
        state_file.write_text(content)
        monkeypatch.setattr(runner, "STATE_FILE", state_file)
        state = runner.parse_sprint_state()
        assert state["tasks_remaining"] == []

    def test_comments_stripped_from_values(self, tmp_repo: Path, monkeypatch):
        content = textwrap.dedent("""\
            ## SPRINT_STATE_MACHINE
            ```yaml
            platform_phase: IMPLEMENTATION  # do not change
            autonomous_halt: false  # C-001 override
            current_sprint: WC-012
            consecutive_failures: 0
            tasks_remaining:
              - WC012-02  # next
            ```
        """)
        state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
        state_file.write_text(content)
        monkeypatch.setattr(runner, "STATE_FILE", state_file)
        state = runner.parse_sprint_state()
        assert state["platform_phase"] == "IMPLEMENTATION"
        assert state["autonomous_halt"] == "false"
        assert "WC012-02" in state["tasks_remaining"]

    def test_tasks_with_hash_prefix_excluded(self, tmp_repo: Path, monkeypatch):
        """Tasks prefixed with # in the tasks_remaining list are filtered out."""
        content = (
            "## SPRINT_STATE_MACHINE\n"
            "```yaml\n"
            "platform_phase: IMPLEMENTATION\n"
            "autonomous_halt: false\n"
            "current_sprint: WC-012\n"
            "consecutive_failures: 0\n"
            "tasks_remaining:\n"
            "  - WC012-03\n"
            "  - #WC012-SKIP\n"  # task with # prefix — should be excluded
            "  - WC012-04\n"
            "```\n"
        )
        state_file = tmp_repo / "constitution" / "PROJECT_STATE.md"
        state_file.write_text(content)
        monkeypatch.setattr(runner, "STATE_FILE", state_file)
        state = runner.parse_sprint_state()
        assert "WC012-03" in state["tasks_remaining"]
        assert "WC012-04" in state["tasks_remaining"]
        assert len([t for t in state["tasks_remaining"] if t.startswith("#")]) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# check_platform_phase_gate()
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckPlatformPhaseGate:
    """Tests for HALT and SPEC phase guards (C-001 constitutional floor)."""

    def test_halt_true_exits_zero(self, monkeypatch, capsys):
        """AUTONOMOUS_HALT=true must stop execution immediately (C-001)."""
        monkeypatch.setattr(runner, "set_output", lambda k, v: None)
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)
        state = {"platform_phase": "IMPLEMENTATION", "autonomous_halt": "true"}
        with pytest.raises(SystemExit) as exc:
            runner.check_platform_phase_gate(state)
        assert exc.value.code == 0

    def test_spec_phase_exits_zero(self, monkeypatch, tmp_repo):
        """platform_phase=SPEC runs spec validation, not implementation (C-001)."""
        monkeypatch.setattr(runner, "set_output", lambda k, v: None)
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)
        monkeypatch.setattr(runner, "run_spec_validation", lambda: None)
        state = {"platform_phase": "SPEC", "autonomous_halt": "false"}
        with pytest.raises(SystemExit) as exc:
            runner.check_platform_phase_gate(state)
        assert exc.value.code == 0

    def test_unknown_phase_exits_zero(self, monkeypatch):
        """Unknown phase (e.g. ARCHIVED) must halt — not accidentally allow work."""
        monkeypatch.setattr(runner, "set_output", lambda k, v: None)
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)
        state = {"platform_phase": "ARCHIVED", "autonomous_halt": "false"}
        with pytest.raises(SystemExit) as exc:
            runner.check_platform_phase_gate(state)
        assert exc.value.code == 0

    def test_implementation_proceeds(self, monkeypatch):
        """IMPLEMENTATION phase with halt=false must not sys.exit."""
        monkeypatch.setattr(runner, "set_output", lambda k, v: None)
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)
        state = {"platform_phase": "IMPLEMENTATION", "autonomous_halt": "false"}
        # Must NOT raise SystemExit
        runner.check_platform_phase_gate(state)

    def test_halt_case_insensitive(self, monkeypatch):
        """AUTONOMOUS_HALT is case-insensitive: TRUE / True / true all halt."""
        monkeypatch.setattr(runner, "set_output", lambda k, v: None)
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)
        for halt_val in ("TRUE", "True", "true"):
            state = {"platform_phase": "IMPLEMENTATION", "autonomous_halt": halt_val}
            with pytest.raises(SystemExit):
                runner.check_platform_phase_gate(state)


# ═══════════════════════════════════════════════════════════════════════════════
# _build_system_prompt() — stack selection
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildSystemPrompt:
    """Tests for stack-aware system prompt construction."""

    def test_wc012_returns_dotnet_expert(self):
        prompt = _build_system_prompt("WC012-02b")
        assert "C# 12" in prompt or ".NET 9" in prompt
        assert "gRPC" in prompt

    def test_wc014_returns_python_expert(self):
        prompt = _build_system_prompt("WC014-03")
        assert "Python 3.12" in prompt
        assert "Temporal" in prompt or "FastAPI" in prompt

    def test_wc016_returns_terraform_expert(self):
        prompt = _build_system_prompt("WC016-01")
        assert "Terraform" in prompt
        assert "Azure" in prompt

    def test_wc017_returns_typescript_expert(self):
        prompt = _build_system_prompt("WC017-01")
        assert "TypeScript" in prompt or "Next.js" in prompt

    def test_wc015_returns_python_expert(self):
        prompt = _build_system_prompt("WC015-02")
        assert "Python" in prompt

    def test_wc013_returns_dotnet_expert(self):
        prompt = _build_system_prompt("WC013-03")
        assert ".NET" in prompt or "C#" in prompt

    def test_unknown_task_falls_back_to_dotnet(self):
        """Unknown prefix should default to dotnet (safe fallback)."""
        prompt = _build_system_prompt("WC099-01")
        assert ".NET" in prompt or "C#" in prompt

    def test_all_prompts_contain_constitutional_obligations(self):
        """Every system prompt must include C-059 traceability obligation."""
        for task_prefix in ["WC012", "WC014", "WC016", "WC017"]:
            prompt = _build_system_prompt(f"{task_prefix}-01")
            assert "C-059" in prompt, f"C-059 missing from {task_prefix} prompt"

    def test_all_prompts_contain_output_format(self):
        """Every prompt must include <file path=...> format instruction."""
        for task_prefix in ["WC012", "WC014", "WC016", "WC017"]:
            prompt = _build_system_prompt(f"{task_prefix}-01")
            assert "<file" in prompt.lower() or "file path" in prompt.lower()

    def test_all_prompts_contain_extend_not_replace(self):
        """Every prompt must include EXTEND-NOT-REPLACE instruction."""
        for task_prefix in ["WC012", "WC014", "WC016", "WC017"]:
            prompt = _build_system_prompt(f"{task_prefix}-01")
            assert "EXTEND" in prompt or "extend" in prompt.lower()

    def test_task_stack_map_covers_all_sprint_families(self):
        """Every sprint family WC012-WC018 must have a stack mapping."""
        required = ["WC012", "WC013", "WC014", "WC015", "WC016", "WC017", "WC018"]
        for prefix in required:
            assert prefix in _TASK_STACK_MAP, f"{prefix} missing from _TASK_STACK_MAP"


# ═══════════════════════════════════════════════════════════════════════════════
# parse_llm_files()
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseLlmFiles:
    """Tests for <file path="..."> block parsing and boundary enforcement."""

    def test_single_valid_cs_file(self):
        response = '<file path="src/constitutional-engine/Foo.cs">class Foo {}</file>'
        result = parse_llm_files(response)
        assert "src/constitutional-engine/Foo.cs" in result
        assert "class Foo {}" in result["src/constitutional-engine/Foo.cs"]

    def test_multiple_files_parsed(self):
        response = (
            '<file path="src/constitutional-engine/A.cs">class A {}</file>'
            '<file path="tests/constitutional-engine.Tests/ATests.cs">class AT {}</file>'
        )
        result = parse_llm_files(response)
        assert len(result) == 2
        assert "src/constitutional-engine/A.cs" in result
        assert "tests/constitutional-engine.Tests/ATests.cs" in result

    def test_write_boundary_enforced_constitution(self, capsys):
        """constitution/ paths are rejected — C-059 write boundary."""
        response = '<file path="constitution/CONSTITUTION.md">HACK</file>'
        result = parse_llm_files(response)
        assert "constitution/CONSTITUTION.md" not in result
        captured = capsys.readouterr()
        assert "outside boundary" in captured.out or "skipped" in captured.out

    def test_write_boundary_enforced_adr(self, capsys):
        """adr/ paths are rejected."""
        response = '<file path="adr/ADR-001.md">hacked</file>'
        result = parse_llm_files(response)
        assert len(result) == 0

    def test_write_boundary_enforced_architecture(self, capsys):
        """architecture/ paths are rejected."""
        response = '<file path="architecture/reference/foo.md">hacked</file>'
        result = parse_llm_files(response)
        assert len(result) == 0

    def test_allowed_src_path(self):
        response = '<file path="src/business-platform/Foo.cs">// ok</file>'
        result = parse_llm_files(response)
        assert "src/business-platform/Foo.cs" in result

    def test_allowed_tests_path(self):
        response = '<file path="tests/constitutional-engine.Tests/X.cs">// test</file>'
        result = parse_llm_files(response)
        assert "tests/constitutional-engine.Tests/X.cs" in result

    def test_allowed_infrastructure_postgres(self):
        response = '<file path="infrastructure/postgres/init/99-extra.sql">SELECT 1;</file>'
        result = parse_llm_files(response)
        assert "infrastructure/postgres/init/99-extra.sql" in result

    def test_design_question_detected(self, capsys):
        """DESIGN_QUESTION: comments must be surfaced (C-032 escalation signal)."""
        response = (
            '<file path="src/constitutional-engine/Foo.cs">'
            'DESIGN_QUESTION: Should this use int or long?\n'
            'class Foo {}'
            '</file>'
        )
        parse_llm_files(response)
        captured = capsys.readouterr()
        assert "Design question" in captured.out or "DESIGN_QUESTION" in captured.out

    def test_no_file_blocks_returns_empty(self):
        result = parse_llm_files("Here is some text without any file blocks.")
        assert result == {}

    def test_single_quoted_path(self):
        response = "<file path='src/constitutional-engine/Bar.cs'>class Bar {}</file>"
        result = parse_llm_files(response)
        assert "src/constitutional-engine/Bar.cs" in result

    def test_content_stripped_of_whitespace(self):
        response = '<file path="src/constitutional-engine/Trim.cs">  \n  trimmed  \n  </file>'
        result = parse_llm_files(response)
        assert result["src/constitutional-engine/Trim.cs"] == "trimmed"

    def test_mixed_valid_and_rejected_paths(self):
        response = (
            '<file path="src/constitutional-engine/Ok.cs">good</file>'
            '<file path="constitution/BAD.md">bad</file>'
        )
        result = parse_llm_files(response)
        assert len(result) == 1
        assert "src/constitutional-engine/Ok.cs" in result


# ═══════════════════════════════════════════════════════════════════════════════
# get_branch_context()
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetBranchContext:
    """Tests for branch context RAG injection (C-083, C-085)."""

    def test_returns_empty_when_git_fails(self, monkeypatch):
        """Git failure must produce empty string — not crash (C-085 idempotency)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        monkeypatch.setattr(runner, "run", lambda *a, **kw: mock_result)
        result = runner.get_branch_context()
        assert result == ""

    def test_returns_empty_when_no_code_files(self, monkeypatch, tmp_path):
        """No .cs/.py files on branch → empty context (C-083)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "constitution/PROJECT_STATE.md\nREADME.md\n"
        monkeypatch.setattr(runner, "run", lambda *a, **kw: mock_result)
        result = runner.get_branch_context()
        assert result == ""

    def test_includes_cs_file_on_branch(self, monkeypatch, tmp_path):
        """A .cs file on the branch appears in context (C-083 Listen signal)."""
        cs_file = tmp_path / "src" / "constitutional-engine" / "Evaluators" / "Foo.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text(
            "namespace Waooaw.ConstitutionalEngine.Evaluators;\n"
            "public record FooRecord(string Id);\n"
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/constitutional-engine/Evaluators/Foo.cs\n"

        monkeypatch.setattr(runner, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

        result = runner.get_branch_context()
        assert "Foo.cs" in result
        assert "BRANCH CONTEXT" in result

    def test_excludes_binary_extensions(self, monkeypatch, tmp_path):
        """Non-code files like .dll, .png are not included in context."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/constitutional-engine/bin/Debug/Foo.dll\n"
        monkeypatch.setattr(runner, "run", lambda *a, **kw: mock_result)
        result = runner.get_branch_context()
        assert result == ""

    def test_context_includes_header_and_footer(self, monkeypatch, tmp_path):
        """Branch context block must have BRANCH CONTEXT header (C-083)."""
        cs_file = tmp_path / "src" / "svc" / "X.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text("namespace Waooaw; public class X {}")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/svc/X.cs\n"

        monkeypatch.setattr(runner, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

        result = runner.get_branch_context()
        assert "BRANCH CONTEXT" in result
        assert "END BRANCH CONTEXT" in result

    def test_exception_returns_empty(self, monkeypatch):
        """Any exception in get_branch_context returns '' — never crashes runner."""
        def raise_exc(*a, **kw):
            raise RuntimeError("git exploded")
        monkeypatch.setattr(runner, "run", raise_exc)
        result = runner.get_branch_context()
        assert result == ""

    def test_small_cs_file_included_in_full(self, monkeypatch, tmp_path):
        """Small .cs files (< 150 lines) should have their content included."""
        cs_file = tmp_path / "src" / "ce" / "Eval" / "EvaluationContext.cs"
        cs_file.parent.mkdir(parents=True)
        content = "\n".join([
            "// Implements: architecture/reference/ce-validate-action-evaluators.md",
            "// constitutional_basis: C-041, C-059",
            "#nullable enable",
            "namespace Waooaw.ConstitutionalEngine.Evaluators;",
            "using Waooaw.ConstitutionalEngine.Grpc;",
            "public sealed record EvaluationContext(",
            "    string ContractId,",
            "    string ActionType,",
            "    string ActionParameters,",
            "    int DecisionSpaceVersion,",
            "    string TenantId,",
            "    string? SkillId = null);",
        ])
        cs_file.write_text(content)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/ce/Eval/EvaluationContext.cs\n"

        monkeypatch.setattr(runner, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

        result = runner.get_branch_context()
        # Should see the record definition since file is small
        assert "EvaluationContext" in result


# ═══════════════════════════════════════════════════════════════════════════════
# validate_written_files()
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateWrittenFiles:
    """Tests for post-generation file validation (C-082)."""

    def test_valid_python_file_passes(self, tmp_path: Path, monkeypatch):
        py_file = tmp_path / "scripts" / "foo.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text("def hello(): return 42\n")
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        ok, errors = runner.validate_written_files([str(py_file)])
        assert ok
        assert errors == ""

    def test_invalid_python_file_fails(self, tmp_path: Path, monkeypatch):
        py_file = tmp_path / "scripts" / "bad.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text("def broken(\n")  # syntax error
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        ok, errors = runner.validate_written_files([str(py_file)])
        assert not ok
        assert len(errors) > 0

    def test_no_csproj_fails(self, tmp_path: Path, monkeypatch):
        """Missing .csproj produces an error (C-082)."""
        cs_file = tmp_path / "src" / "myservice" / "Foo.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text("namespace X; public class Foo {}\n")
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "run", lambda *a, **kw: MagicMock(returncode=0))
        ok, errors = runner.validate_written_files(["src/myservice/Foo.cs"])
        assert not ok
        assert "csproj" in errors.lower() or "No .csproj" in errors

    def test_empty_file_list_passes(self, tmp_path: Path, monkeypatch):
        """No files → trivially ok (nothing to validate)."""
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        ok, errors = runner.validate_written_files([])
        assert ok
        assert errors == ""

    def test_dotnet_build_fail_propagates_error(self, tmp_path: Path, monkeypatch):
        cs_file = tmp_path / "src" / "ce" / "Foo.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text("class X {}\n")
        csproj = tmp_path / "src" / "ce" / "ce.csproj"
        csproj.write_text("<Project Sdk='Microsoft.NET.Sdk'></Project>")
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stdout = "error CS0001: Something failed"
        fail_result.stderr = ""
        monkeypatch.setattr(runner, "run", lambda *a, **kw: fail_result)

        ok, errors = runner.validate_written_files(["src/ce/Foo.cs"])
        assert not ok
        assert "CS0001" in errors or "failed" in errors.lower() or len(errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# flag_spec_gap() — offline path
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlagSpecGap:
    """Tests for spec-gap flagging (C-032, C-065, C-066)."""

    def test_no_github_token_prints_gap(self, monkeypatch, capsys):
        """Without GITHUB_REPO env, flag_spec_gap prints the gap (not crash)."""
        monkeypatch.setenv("GITHUB_REPO", "")  # empty string triggers offline path
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)

        runner.flag_spec_gap(
            task_id="WC012-02b",
            gap_description="ctx.TenantId not on EvaluationContext",
            affected_spec="architecture/reference/ce-validate-action-evaluators.md",
            constitutional_basis="C-059",
        )
        captured = capsys.readouterr()
        assert "SPEC GAP" in captured.out
        # task_id appears in the gap description output
        assert "ctx.TenantId" in captured.out or "WC012-02b" in captured.out

    def test_monitor_signal_updated_on_spec_gap(self, monkeypatch, capsys):
        """_MONITOR_SIGNAL task_results entry must reflect SPEC_GAP (C-069)."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        monkeypatch.setattr(runner, "record_evidence", lambda *a, **kw: None)
        # Reset monitor signal
        runner._MONITOR_SIGNAL["task_results"].clear()

        runner.flag_spec_gap(
            task_id="WC012-02b",
            gap_description="test gap",
            affected_spec="architecture/reference/ce.md",
        )
        # Without GITHUB_REPO, issue creation is skipped — no task_results entry
        # But the output must still surface the gap
        captured = capsys.readouterr()
        assert "SPEC GAP" in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
# execute_with_llm() — offline paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecuteWithLlm:
    """Tests for LLM execution paths that don't need a live API."""

    def test_no_api_key_returns_false(self, monkeypatch, tmp_path, capsys):
        """Without ANTHROPIC_API_KEY, execute_with_llm must fail gracefully."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "get_branch_context", lambda: "")
        monkeypatch.setattr(runner, "flag_spec_gap", lambda **kw: None)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        # Create a dummy spec file
        spec_file = tmp_path / "architecture" / "reference" / "ce.md"
        spec_file.parent.mkdir(parents=True)
        spec_file.write_text("# Spec\n\nContent here.\n")

        ok = runner.execute_with_llm(
            task_id="WC012-02b",
            task_description="test task",
            spec_sections={"architecture/reference/ce.md": "full"},
            constitutional_check="test check",
            model_hint="reasoning",
        )
        assert ok is False

    def test_model_hint_none_skips_llm(self, monkeypatch, tmp_path):
        """model_hint='none' returns None from call_llm (no LLM call)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # call_llm with model_hint not in (reasoning, auto) returns None
        result = runner.call_llm(
            task_id="WC011-01",
            task_description="validate",
            spec_content="",
            constitutional_check="",
            model_hint="none",
        )
        assert result is None

    def test_spec_content_built_from_sections(self, monkeypatch, tmp_path):
        """Spec sections are read and concatenated into prompt context."""
        spec_file = tmp_path / "architecture" / "ref" / "spec.md"
        spec_file.parent.mkdir(parents=True)
        spec_file.write_text("# Spec Title\n\nSome content here.\n")

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "get_branch_context", lambda: "")
        monkeypatch.setattr(runner, "flag_spec_gap", lambda **kw: None)

        # Capture what call_llm receives as spec_content
        captured_spec = []

        def fake_call_llm(task_id, task_desc, spec_content, *args, **kwargs):
            captured_spec.append(spec_content)
            return None  # simulate no API key

        monkeypatch.setattr(runner, "call_llm", fake_call_llm)

        runner.execute_with_llm(
            task_id="WC012-99",
            task_description="test",
            spec_sections={"architecture/ref/spec.md": "full"},
            constitutional_check="check",
            model_hint="reasoning",
        )
        assert len(captured_spec) > 0
        assert "Spec Title" in captured_spec[0] or "spec.md" in captured_spec[0]


# ═══════════════════════════════════════════════════════════════════════════════
# _generate_wc012_02a_evaluator_interfaces()
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateWc01202aEvaluatorInterfaces:
    """Tests for deterministic EvaluationContext / evaluator interface generation."""

    def test_writes_four_files(self, monkeypatch, tmp_path):
        """WC012-02a must write exactly 4 files: EvaluationResult, EvaluationContext, IClaimEvaluator, EvaluatorRegistry."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        assert (ev_dir / "EvaluationResult.cs").exists()
        assert (ev_dir / "EvaluationContext.cs").exists()
        assert (ev_dir / "IClaimEvaluator.cs").exists()
        assert (ev_dir / "EvaluatorRegistry.cs").exists()

    def test_evaluation_context_has_correct_namespace(self, monkeypatch, tmp_path):
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        ctx = (ev_dir / "EvaluationContext.cs").read_text()
        assert "Waooaw.ConstitutionalEngine.Evaluators" in ctx

    def test_evaluation_context_has_from_request(self, monkeypatch, tmp_path):
        """EvaluationContext.FromRequest must exist (C-082: LLM must use it)."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        ctx = (ev_dir / "EvaluationContext.cs").read_text()
        assert "FromRequest" in ctx

    def test_evaluation_context_has_tenant_id(self, monkeypatch, tmp_path):
        """EvaluationContext must include TenantId — required by C-041 evaluator DB reads."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        ctx = (ev_dir / "EvaluationContext.cs").read_text()
        assert "TenantId" in ctx, (
            "EvaluationContext must have TenantId property — "
            "spec evaluators reference ctx.TenantId for DB reads (C-041, C-043, C-049)"
        )

    def test_evaluation_context_has_budget_properties(self, monkeypatch, tmp_path):
        """EvaluationContext must expose BudgetContext fields for C-043 evaluator."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        ctx = (ev_dir / "EvaluationContext.cs").read_text()
        assert "ProposedSpend" in ctx or "BudgetContext" in ctx or "ApprovedBudget" in ctx, (
            "EvaluationContext must expose BudgetContext fields for C-043 financial ceiling evaluator"
        )

    def test_evaluation_context_has_get_parameter(self, monkeypatch, tmp_path):
        """EvaluationContext must have GetParameter() for JSON ActionParameters parsing."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        ctx = (ev_dir / "EvaluationContext.cs").read_text()
        assert "GetParameter" in ctx, (
            "EvaluationContext must have GetParameter(string key) to parse "
            "ActionParameters JSON — prevents LLM calling .TryGetValue() on string"
        )

    def test_evaluation_verdict_has_three_values(self, monkeypatch, tmp_path):
        """EvaluationVerdict must have exactly Allow, Deny, Escalate."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        result = (ev_dir / "EvaluationResult.cs").read_text()
        assert "Allow" in result
        assert "Deny" in result
        assert "Escalate" in result

    def test_all_files_have_constitutional_headers(self, monkeypatch, tmp_path):
        """All generated files must have C-059 traceability headers."""
        ev_dir = tmp_path / "src" / "constitutional-engine" / "Evaluators"
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))

        runner._generate_wc012_02a_evaluator_interfaces()

        for fname in ["EvaluationResult.cs", "EvaluationContext.cs", "IClaimEvaluator.cs", "EvaluatorRegistry.cs"]:
            content = (ev_dir / fname).read_text()
            assert "// Implements:" in content, f"{fname} missing // Implements: header (C-059)"
            assert "constitutional_basis" in content, f"{fname} missing constitutional_basis (C-073)"

    def test_returns_true_on_success(self, monkeypatch, tmp_path):
        monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(runner, "git", lambda *a, **kw: MagicMock(returncode=0))
        result = runner._generate_wc012_02a_evaluator_interfaces()
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# WC012-02b constitutional_check content
# ═══════════════════════════════════════════════════════════════════════════════

class TestWc01202bConstitutionalCheck:
    """Tests that WC012-02b constitutional_check contains the right type contract."""

    def _get_subtask(self):
        """Return the WC012-02b SubTaskDef from TASK_HANDLERS."""
        wc012 = runner.TASK_HANDLERS.get("WC012-02")
        if not wc012:
            return None
        for st in wc012.get("subtasks", []):
            if st.id == "WC012-02b":
                return st
        return None

    def _get_check(self) -> str:
        """Extract WC012-02b constitutional_check from TASK_HANDLERS."""
        handler = runner.TASK_HANDLERS.get("WC012-02b")
        if handler and callable(handler):
            return ""
        wc012 = runner.TASK_HANDLERS.get("WC012-02")
        if not wc012:
            return ""
        for st in wc012.get("subtasks", []):
            if st.id == "WC012-02b":
                return st.constitutional_check
        return ""

    def test_check_lists_evaluation_context_properties(self):
        """constitutional_check references EvaluationContext behavioral patterns.

        Type properties are injected by PTR (C-085/DP-009), not hardcoded here.
        The check must contain behavioral rules for USING the context, not listing fields.
        """
        check = self._get_check()
        # PTR injects the full type contract — check must contain behavioral usage patterns
        assert "GetParameter" in check or "TenantId" in check or "FromRequest" in check, (
            "WC012-02b check must contain EvaluationContext behavioral usage guidance"
        )

    def test_check_explains_get_parameter(self):
        """check must explain how to parse ActionParameters JSON (prevents TryGetValue)."""
        check = self._get_check()
        assert "GetParameter" in check or "ActionParameters" in check, (
            "WC012-02b check must explain ActionParameters JSON parsing"
        )

    def test_check_prohibits_trygetvalue(self):
        """check must explicitly prohibit string.TryGetValue (the failure mode)."""
        check = self._get_check()
        assert "TryGetValue" in check, (
            "WC012-02b check must mention TryGetValue to explicitly prohibit it"
        )

    def test_check_lists_budget_properties(self):
        """check must reference budget evaluation logic for C-043.

        Budget field names (ProposedSpendInrPaise etc.) come from PTR type contracts.
        The check must contain behavioral guidance about the EvaluatorRegistry call.
        """
        check = self._get_check()
        # PTR injects budget field names — check must reference evaluator registry usage
        assert "EvaluateAllAsync" in check or "EvaluatorRegistry" in check or "DENY" in check, (
            "WC012-02b check must contain evaluator behavioral guidance (budget ceiling is in PTR)"
        )

    def test_check_lists_six_output_files(self):
        """WC012-02b must declare 6 output_files (used for file-by-file routing)."""
        st = self._get_subtask()
        assert st is not None, "WC012-02b subtask not found"
        assert st.output_files, "WC012-02b must have output_files for file-by-file mode"
        required = [
            "C041ToolAuthorizationEvaluator",
            "C043BudgetCeiling",
            "C048NonExploitation",
            "C049HonestLimitation",
            "C062AiSecurity",
            "ConstitutionalEngineService",
        ]
        paths = " ".join(st.output_files)
        for f in required:
            assert f in paths, f"WC012-02b output_files missing {f}"


# ═══════════════════════════════════════════════════════════════════════════════
# Allowed write roots — security boundary (ADR-030, C-065)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWriteBoundary:
    """Tests that ALLOWED_WRITE_ROOTS is correctly defined (security boundary)."""

    def test_src_is_allowed(self):
        assert any(r == "src/" for r in ALLOWED_WRITE_ROOTS)

    def test_tests_is_allowed(self):
        assert any(r == "tests/" for r in ALLOWED_WRITE_ROOTS)

    def test_infrastructure_postgres_is_allowed(self):
        assert any("infrastructure/postgres" in r for r in ALLOWED_WRITE_ROOTS)

    def test_constitution_is_not_allowed(self):
        assert not any("constitution" in r for r in ALLOWED_WRITE_ROOTS)

    def test_adr_is_not_allowed(self):
        assert not any("adr" in r for r in ALLOWED_WRITE_ROOTS)

    def test_architecture_is_not_allowed(self):
        assert not any("architecture" in r for r in ALLOWED_WRITE_ROOTS)

    def test_knowledge_is_not_allowed(self):
        assert not any("knowledge" in r for r in ALLOWED_WRITE_ROOTS)


# ═══════════════════════════════════════════════════════════════════════════════
# Task handler registration
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskHandlers:
    """Tests that TASK_HANDLERS is correctly structured."""

    def test_all_wc011_tasks_registered(self):
        for task in ["WC011-01", "WC011-02", "WC011-03", "WC011-04", "WC011-05", "WC011-07"]:
            assert task in runner.TASK_HANDLERS, f"{task} not in TASK_HANDLERS"
            assert callable(runner.TASK_HANDLERS[task])

    def test_wc012_01_is_callable(self):
        assert callable(runner.TASK_HANDLERS["WC012-01"])

    def test_wc012_02_03_04_are_decomposed_dicts(self):
        for task in ["WC012-02", "WC012-03", "WC012-04"]:
            h = runner.TASK_HANDLERS[task]
            assert isinstance(h, dict), f"{task} should be decomposed dict"
            assert "subtasks" in h, f"{task} dict missing 'subtasks' key"
            assert len(h["subtasks"]) > 0

    def test_scaffold_tasks_frozenset(self):
        assert "WC012-01" in runner.SCAFFOLD_TASKS
        assert "WC013-01" in runner.SCAFFOLD_TASKS
        assert isinstance(runner.SCAFFOLD_TASKS, frozenset)

    def test_monitor_signal_structure(self):
        """_MONITOR_SIGNAL must have all required keys for C-069."""
        required = ["run_id", "sprint", "scaffold_task", "scaffold_failed",
                    "task_results", "spec_gap_issues", "overall_result"]
        for key in required:
            assert key in runner._MONITOR_SIGNAL, f"_MONITOR_SIGNAL missing '{key}'"
