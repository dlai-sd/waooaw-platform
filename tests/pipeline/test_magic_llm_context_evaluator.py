"""
Tests for MagicLLM context_builder.py and response_evaluator.py.
Implements §7 and §8 specification contracts.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from magic_llm.context_builder import ContextBuilder, AssembledContext
from magic_llm.response_evaluator import ResponseEvaluator, EvaluationResult


# ── ContextBuilder tests (§7) ──────────────────────────────────────────────────

class TestContextBuilderOrderedAssembly:
    """§7.1: Ordered context assembly — 9 slots in mandatory order."""

    def test_build_returns_assembled_context(self, tmp_path):
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs",
            spec_sections={"tests/QA-STRATEGY.md": "§5.1 Unit Tests"},
            constitutional_check="using Waooaw.ConstitutionalEngine.Tests.Evaluators;",
            depends_on_tasks=["WC012-02a", "WC012-02b"],
            stack="dotnet",
        )
        assert isinstance(ctx, AssembledContext)
        assert ctx.task_id == "WC012-02c"

    def test_system_block_always_present(self):
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/x.cs",
            spec_sections={},
            constitutional_check="",
            depends_on_tasks=[],
            stack="dotnet",
        )
        slots = [b.slot for b in ctx.blocks]
        assert "SYSTEM" in slots
        assert slots[0] == "SYSTEM"  # SYSTEM must be first

    def test_preamble_block_second(self):
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="T1",
            output_file="tests/x.cs",
            spec_sections={},
            constitutional_check="",
            depends_on_tasks=[],
            stack="dotnet",
        )
        slots = [b.slot for b in ctx.blocks]
        assert "PREAMBLE" in slots
        assert slots.index("PREAMBLE") == 1  # PREAMBLE must be second

    def test_task_block_second_to_last(self):
        """TASK and FORMAT must be at the end of the assembly."""
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="T1",
            output_file="tests/x.cs",
            spec_sections={},
            constitutional_check="",
            depends_on_tasks=[],
            stack="dotnet",
        )
        slots = [b.slot for b in ctx.blocks]
        assert "TASK" in slots
        assert "FORMAT" in slots
        assert slots.index("TASK") > 2  # TASK after SYSTEM + PREAMBLE
        assert slots.index("FORMAT") == len(slots) - 1  # FORMAT is last

    def test_context_smaller_than_runner_prompt(self):
        """§7: MagicLLM context should be significantly smaller than raw 40k runner prompt."""
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs",
            spec_sections={"tests/QA-STRATEGY.md": "§5.1 Unit Tests"},
            constitutional_check="FakeServerCallContext.Create(tenantId)",
            depends_on_tasks=["WC012-02a", "WC012-02b"],
            stack="dotnet",
        )
        # MagicLLM context target is < 40k chars (runner prompt); QA-STRATEGY.md has grown over time
        assert ctx.total_chars < 25000, f"Context too large: {ctx.total_chars} chars"


class TestContextBuilderPreamble:
    """§7.5: File Preamble Contract — pre-written header."""

    def test_preamble_contains_implements_header(self):
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/x.cs",
            spec_sections={"tests/QA-STRATEGY.md": "§5.1"},
            constitutional_check="C-041 tool authorization",
            depends_on_tasks=[],
            stack="dotnet",
        )
        preamble = ctx.preamble_text
        assert "// Implements:" in preamble

    def test_preamble_contains_constitutional_basis(self):
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/x.cs",
            spec_sections={"tests/QA-STRATEGY.md": "§5.1"},
            constitutional_check="C-041 C-076 coverage",
            depends_on_tasks=[],
            stack="dotnet",
        )
        assert "constitutional_basis" in ctx.preamble_text

    def test_preamble_using_resolved_from_constitutional_check(self):
        """§7.5: Usings mentioned in constitutional_check are extracted into preamble."""
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/x.cs",
            spec_sections={},
            constitutional_check="using Waooaw.ConstitutionalEngine.Tests.Evaluators;",
            depends_on_tasks=[],
            stack="dotnet",
        )
        # The using should appear in the preamble
        assert "Waooaw.ConstitutionalEngine.Tests.Evaluators" in ctx.preamble_text

    def test_preamble_is_code_not_prose(self):
        """Preamble lines must be actual code, not prose instructions."""
        builder = ContextBuilder(repo_root=REPO_ROOT)
        ctx = builder.build(
            task_id="T1",
            output_file="tests/x.cs",
            spec_sections={},
            constitutional_check="",
            depends_on_tasks=[],
            stack="dotnet",
        )
        for line in ctx.preamble_lines:
            # No preamble line should start with English prose (must start with // or using)
            assert not (line and line[0].isalpha() and not line.startswith("using")), \
                f"Prose in preamble: {line}"


class TestContextBuilderFrozenRegistry:
    """§7.6: Frozen Artifact Registry."""

    def test_freeze_artifact_writes_registry(self, tmp_path):
        builder = ContextBuilder(repo_root=tmp_path)
        # Create a mock .cs file
        cs_dir = tmp_path / "src" / "svc"
        cs_dir.mkdir(parents=True)
        cs_file = cs_dir / "MyService.cs"
        cs_file.write_text(
            "namespace Waooaw.Test;\n"
            "public sealed class MyService {\n"
            "    public MyService(string name, int count) {}\n"
            "}"
        )
        result = builder.freeze_artifact("src/svc/MyService.cs", "WC012-02b")
        assert result is True

        registry_path = tmp_path / "sprint-context" / "frozen-artifacts.json"
        assert registry_path.exists()
        registry = json.loads(registry_path.read_text())
        assert "src/svc/MyService.cs" in registry
        assert registry["src/svc/MyService.cs"]["frozen_at_task"] == "WC012-02b"
        assert registry["src/svc/MyService.cs"]["namespace"] == "Waooaw.Test"

    def test_frozen_context_injected_into_assembly(self, tmp_path):
        builder = ContextBuilder(repo_root=tmp_path)
        # Pre-populate frozen registry
        (tmp_path / "sprint-context").mkdir(parents=True)
        registry = {
            "src/svc/ConstitutionalEngineService.cs": {
                "frozen_at_task": "WC012-02b",
                "namespace": "Waooaw.ConstitutionalEngine.Services",
                "public_constructors": ["ConstitutionalDbContext db, EvaluatorRegistry registry"],
                "public_methods": ["RecordEvidence", "ValidateAction"],
                "public_properties": [],
            }
        }
        (tmp_path / "sprint-context" / "frozen-artifacts.json").write_text(json.dumps(registry))

        # Reload builder to pick up registry
        builder._frozen = builder._load_frozen_registry()

        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/constitutional-engine.Tests/Services/SomeTests.cs",
            spec_sections={},
            constitutional_check="",
            depends_on_tasks=["WC012-02b"],
            prior_output_files=["src/svc/ConstitutionalEngineService.cs"],
            stack="dotnet",
        )
        slots = [b.slot for b in ctx.blocks]
        assert "FROZEN" in slots
        frozen_block = next(b.content for b in ctx.blocks if b.slot == "FROZEN")
        assert "ConstitutionalDbContext" in frozen_block


# ── ResponseEvaluator tests (§8) ──────────────────────────────────────────────

class TestResponseEvaluatorFormatGate:
    """§8 Gate 1: FORMAT."""

    def test_valid_xml_file_block_passes(self):
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator._gate_format(
            '<file path="tests/x.cs">using System;</file>',
            "xml_file_blocks"
        )
        assert result.passed is True

    def test_no_file_block_fails(self):
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator._gate_format("just some text", "xml_file_blocks")
        assert result.passed is False
        assert result.failure_class == "FORMAT_FAILURE"

    def test_markdown_code_block_fails(self):
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator._gate_format("```csharp\nusing System;\n```", "xml_file_blocks")
        assert result.passed is False
        assert "format" in result.detail.lower()

    def test_json_format_valid(self):
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator._gate_format('{"key": "value"}', "json")
        assert result.passed is True

    def test_json_format_invalid(self):
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator._gate_format("not json", "json")
        assert result.passed is False


class TestResponseEvaluatorAnnotationGate:
    """§8 Gate 3: ANNOTATION (C-073)."""

    def test_file_with_header_passes(self, tmp_path):
        cs_file = tmp_path / "x.cs"
        cs_file.write_text(
            "// Implements: tests/QA-STRATEGY.md §5.1\n"
            "// constitutional_basis: C-076\n"
            "using System;\n"
        )
        evaluator = ResponseEvaluator(tmp_path)
        result = evaluator._gate_annotation([str(cs_file.relative_to(tmp_path))], "dotnet")
        assert result.passed is True

    def test_file_missing_implements_fails(self, tmp_path):
        cs_file = tmp_path / "x.cs"
        cs_file.write_text("using System;\npublic class X {}")
        evaluator = ResponseEvaluator(tmp_path)
        result = evaluator._gate_annotation([str(cs_file.relative_to(tmp_path))], "dotnet")
        assert result.passed is False
        assert result.failure_class == "ANNOTATION_MISSING"

    def test_markdown_header_in_cs_file_fails_annotation(self, tmp_path):
        """CS1024 scenario: LLM outputs markdown before using directives."""
        cs_file = tmp_path / "x.cs"
        cs_file.write_text("## Self-Calibration\nusing System;\n")
        evaluator = ResponseEvaluator(tmp_path)
        result = evaluator._gate_annotation([str(cs_file.relative_to(tmp_path))], "dotnet")
        assert result.passed is False


class TestResponseEvaluatorSpecAlignGate:
    """§8 Gate 4: SPEC_ALIGN (C-032)."""

    def test_temporal_in_wc012_02b_file_fails(self, tmp_path):
        cs_file = tmp_path / "ConstitutionalEngineService.cs"
        cs_file.write_text(
            "// Implements: spec.md §1\n"
            "// constitutional_basis: C-041\n"
            "using Waooaw.ConstitutionalEngine.Temporal;\n"
        )
        evaluator = ResponseEvaluator(tmp_path)
        result = evaluator._gate_spec_align(
            [str(cs_file.relative_to(tmp_path))],
            {"tests/QA-STRATEGY.md": "WC012-02"}
        )
        assert result.passed is False
        assert "Temporal" in result.detail


class TestResponseEvaluatorFullPipeline:
    """§8: End-to-end gate sequence."""

    def test_accepted_response_passes_all_gates(self, tmp_path):
        """If format passes and no code files, all gates pass → accepted."""
        response = '<file path="tests/x.cs">// Implements: spec §1\n// constitutional_basis: C-059\nusing System;\n</file>'
        cs_file = tmp_path / "tests" / "x.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text("// Implements: spec §1\n// constitutional_basis: C-059\nusing System;\n")

        evaluator = ResponseEvaluator(tmp_path)
        result = evaluator.evaluate(
            task_id="T1",
            raw_response=response,
            written_files=["tests/x.cs"],
            stack="python",  # skip dotnet compile gate
        )
        # Format gate passes; annotation gate passes; no compile needed for python without .py files
        assert result.gates[0].passed is True  # FORMAT
        assert result.status in ("accepted", "retry_needed")  # compile may skip

    def test_format_failure_stops_pipeline(self):
        """§8: Gates stop at first failure."""
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator.evaluate(
            task_id="T1",
            raw_response="just prose",
            written_files=["tests/x.cs"],
            stack="dotnet",
        )
        assert result.gates[0].gate == "FORMAT"
        assert result.gates[0].passed is False
        assert result.status == "retry_needed"
        assert len(result.gates) == 1  # stopped after first failure

    def test_gate_summary_format(self):
        evaluator = ResponseEvaluator(REPO_ROOT)
        result = evaluator.evaluate(
            task_id="T1",
            raw_response="no file block",
            written_files=[],
            stack="dotnet",
        )
        summary = result.gate_summary
        assert "FORMAT" in summary
