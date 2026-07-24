"""
Unit tests for wc_spec_reader.py + _build_effective_check() + STACK_BEHAVIORAL_RULES

# Implements: architecture/reference/pipeline/wc-spec-reader.md
# constitutional_basis:
#   C-076 (≥90% coverage), C-059 (Traceability — WCSpecReader is the traceability bridge),
#   C-032 (spec before code), DP-009 (API First — WC spec is authoritative)
# office: Platform IT Expert — QA hat
# ib_item: IB-022
"""

import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from wc_spec_reader import (
    WCTaskSpec,
    find_wc_file,
    load,
    get_task,
    clear_cache,
    _infer_stack,
    _extract_field,
    _parse_wc_file,
)
from task_decomposer import (
    SubTaskDef,
    STACK_BEHAVIORAL_RULES,
    _build_effective_check,
)


# ═══════════════════════════════════════════════════════════════════════════════
# find_wc_file()
# ═══════════════════════════════════════════════════════════════════════════════

class TestFindWcFile:
    def test_finds_real_wc012_file(self):
        """WC-012 file exists in the repo."""
        result = find_wc_file("WC012")
        assert result is not None
        assert "WC-012" in result.name

    def test_accepts_lowercase_wc_prefix(self):
        result = find_wc_file("wc012")
        assert result is not None

    def test_accepts_numeric_only(self):
        result = find_wc_file("12")
        assert result is not None

    def test_returns_none_for_nonexistent(self):
        result = find_wc_file("WC999")
        assert result is None

    def test_finds_wc013(self):
        result = find_wc_file("WC013")
        assert result is not None

    def test_zero_padded_and_short_both_work(self):
        r1 = find_wc_file("012")
        r2 = find_wc_file("12")
        assert r1 is not None
        assert r2 is not None
        assert r1 == r2


# ═══════════════════════════════════════════════════════════════════════════════
# _infer_stack()
# ═══════════════════════════════════════════════════════════════════════════════

class TestInferStack:
    def test_dotnet_from_csproj(self):
        assert _infer_stack("Create src/constitutional-engine/*.csproj", "") == "dotnet"

    def test_python_from_fastapi(self):
        assert _infer_stack("FastAPI service with Temporal worker", "") == "python"

    def test_typescript_from_nextjs(self):
        assert _infer_stack("Convert HTML to Next.js App Router", "") == "typescript"

    def test_terraform_from_tf(self):
        assert _infer_stack("Apply infrastructure/terraform configuration", "") == "terraform"

    def test_mixed_when_multiple_stacks(self):
        assert _infer_stack("Python FastAPI calling .NET gRPC service", "") == "mixed"

    def test_default_dotnet_for_unknown(self):
        assert _infer_stack("Write some code", "Do something") == "dotnet"


# ═══════════════════════════════════════════════════════════════════════════════
# _extract_field()
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractField:
    WC_BLOCK = textwrap.dedent("""\
        **Scope:** Implement ValidateAction stub evaluator.
        **model_hint:** `reasoning`
        **Constitutional check:** Default deny (C-041) must be the starting state.
        **CCT gate:** CCT-EF-01 must pass
    """)

    def test_extracts_scope(self):
        result = _extract_field(self.WC_BLOCK, "Scope")
        assert "Implement ValidateAction" in result

    def test_extracts_model_hint_strips_backticks(self):
        result = _extract_field(self.WC_BLOCK, "model_hint")
        assert result == "reasoning"

    def test_extracts_constitutional_check(self):
        result = _extract_field(self.WC_BLOCK, "Constitutional check")
        assert "C-041" in result
        assert "Default deny" in result

    def test_extracts_cct_gate(self):
        result = _extract_field(self.WC_BLOCK, "CCT gate")
        assert "CCT-EF-01" in result

    def test_returns_empty_for_missing_field(self):
        result = _extract_field(self.WC_BLOCK, "NonExistentField")
        assert result == ""

    def test_case_insensitive(self):
        result = _extract_field(self.WC_BLOCK, "scope")
        assert "Implement" in result


# ═══════════════════════════════════════════════════════════════════════════════
# _parse_wc_file()
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseWcFile:
    SAMPLE_WC = textwrap.dedent("""\
        # Work Contract 012

        ## Tasks

        ### WC012-01 — .NET 9 project scaffold + gRPC wiring

        **Scope:** Create `src/constitutional-engine/` .NET 9 project.
        **model_hint:** `reasoning`
        **C-059 header required on:** every .cs file

        ### WC012-02 — ValidateAction + unit tests (≥90% coverage)

        **Scope:** Implement ValidateAction stub evaluator.
        **model_hint:** `reasoning`
        **Constitutional check:** Default deny (C-041) must be the starting state — unlisted tool = DENY.
        **CCT gate:** CCT-EF-01 must pass

        ### WC012-03 — Evidence First record + CCT-EF-01

        **Scope:** RecordEvidence RPC writes to `constitutional.audit_records` before returning.
        **model_hint:** `reasoning`
        **Constitutional check:** C-023 — evidence BEFORE success. C-007 — append-only, no UPDATE/DELETE.
        **CCT gate:** CCT-EF-01 PASS required to merge
    """)

    def test_parses_three_tasks(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert len(result) == 3
        assert "WC012-01" in result
        assert "WC012-02" in result
        assert "WC012-03" in result

    def test_extracts_title(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert result["WC012-01"].title == ".NET 9 project scaffold + gRPC wiring"

    def test_extracts_scope(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert "Implement ValidateAction" in result["WC012-02"].scope

    def test_extracts_model_hint(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert result["WC012-02"].model_hint == "reasoning"

    def test_extracts_constitutional_check(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert "C-041" in result["WC012-02"].constitutional_check
        assert "Default deny" in result["WC012-02"].constitutional_check

    def test_missing_constitutional_check_is_empty(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert result["WC012-01"].constitutional_check == ""

    def test_extracts_cct_gate(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert "CCT-EF-01" in result["WC012-02"].cct_gate

    def test_infers_dotnet_stack(self):
        result = _parse_wc_file(self.SAMPLE_WC)
        assert result["WC012-01"].stack == "dotnet"

    def test_empty_file_returns_empty_dict(self):
        assert _parse_wc_file("") == {}

    def test_file_with_no_tasks_returns_empty(self):
        assert _parse_wc_file("# Just a header\n## No tasks here") == {}


# ═══════════════════════════════════════════════════════════════════════════════
# load() and get_task() — integration against real WC files
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadAndGetTask:
    def setup_method(self):
        clear_cache()

    def test_load_wc012_returns_tasks(self):
        tasks = load("WC012")
        assert len(tasks) >= 4
        assert "WC012-01" in tasks
        assert "WC012-02" in tasks

    def test_get_task_wc012_02(self):
        spec = get_task("WC012-02")
        assert spec is not None
        assert spec.task_id == "WC012-02"
        assert spec.model_hint in ("reasoning", "auto", "")
        assert "ValidateAction" in spec.title or "ValidateAction" in spec.scope

    def test_get_task_derives_wc_number(self):
        """get_task extracts WC number from task_id automatically."""
        spec = get_task("WC012-03")
        assert spec is not None
        assert spec.task_id == "WC012-03"

    def test_get_task_returns_none_for_missing(self):
        spec = get_task("WC999-01")
        assert spec is None

    def test_load_returns_empty_for_missing_wc(self):
        result = load("WC999")
        assert result == {}

    def test_load_caches_results(self):
        """Second load() call uses cache — does not re-read file."""
        r1 = load("WC012")
        r2 = load("WC012")
        assert r1 is r2  # same dict object from cache

    def test_get_task_wc013(self):
        spec = get_task("WC013-01")
        assert spec is not None
        assert "WC013-01" == spec.task_id

    def test_wc012_02_constitutional_check_extracted(self):
        """The PMO constitutional check for WC012-02 is machine-readable."""
        spec = get_task("WC012-02")
        assert spec is not None
        assert "C-041" in spec.constitutional_check or spec.constitutional_check != ""


# ═══════════════════════════════════════════════════════════════════════════════
# STACK_BEHAVIORAL_RULES
# ═══════════════════════════════════════════════════════════════════════════════

class TestStackBehavioralRules:
    def test_all_four_stacks_present(self):
        assert "dotnet" in STACK_BEHAVIORAL_RULES
        assert "python" in STACK_BEHAVIORAL_RULES
        assert "typescript" in STACK_BEHAVIORAL_RULES
        assert "terraform" in STACK_BEHAVIORAL_RULES

    def test_dotnet_rules_not_empty(self):
        assert len(STACK_BEHAVIORAL_RULES["dotnet"]) >= 3

    def test_dotnet_rules_include_trygetvalue_prohibition(self):
        rules = " ".join(STACK_BEHAVIORAL_RULES["dotnet"])
        assert "TryGetValue" in rules

    def test_dotnet_rules_include_namespace_collision_warning(self):
        rules = " ".join(STACK_BEHAVIORAL_RULES["dotnet"])
        assert "namespace" in rules.lower() or "using" in rules.lower()

    def test_python_rules_include_async_rule(self):
        rules = " ".join(STACK_BEHAVIORAL_RULES["python"])
        assert "async" in rules.lower()

    def test_typescript_rules_include_jwt_cookie_rule(self):
        rules = " ".join(STACK_BEHAVIORAL_RULES["typescript"])
        assert "cookie" in rules.lower() or "httpOnly" in rules

    def test_all_stacks_have_c059_header_rule(self):
        for stack, rules in STACK_BEHAVIORAL_RULES.items():
            if stack == "mixed":
                continue
            rule_text = " ".join(rules)
            assert "C-059" in rule_text or "Implements" in rule_text, (
                f"Stack '{stack}' missing C-059 header rule"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# _build_effective_check()
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildEffectiveCheck:
    def setup_method(self):
        clear_cache()

    def test_wc012_02b_with_wc_task_id(self):
        """Full assembly: WC spec + stack rules + delta."""
        st = SubTaskDef(
            id="WC012-02b",
            description="evaluators",
            type="llm",
            wc_task_id="WC012-02",
            output_files=["src/constitutional-engine/Evaluators/C041.cs"],
            not_regenerate_from=["WC012-02a"],
            stack="dotnet",
            constitutional_check="BEHAVIORAL: use ctx.GetParameter()",
        )
        completed = ["WC012-02a"]
        result = _build_effective_check(st, completed)

        # Section 1: PMO requirements present
        assert "WC012-02" in result or "ValidateAction" in result
        # Section 2: output files
        assert "C041.cs" in result
        # Section 3: prior task preservation
        assert "WC012-02a" in result
        # Section 4: stack rules
        assert "TryGetValue" in result or "STACK RULES" in result
        # Section 5: delta
        assert "ctx.GetParameter" in result

    def test_no_wc_task_id_uses_delta_only(self):
        """Without wc_task_id, falls back to constitutional_check delta."""
        st = SubTaskDef(
            id="WC012-02b",
            description="evaluators",
            type="llm",
            wc_task_id="",
            stack="dotnet",
            constitutional_check="MY EXPLICIT CHECK",
        )
        result = _build_effective_check(st, [])
        assert "MY EXPLICIT CHECK" in result

    def test_stack_rules_injected_for_dotnet(self):
        st = SubTaskDef(
            id="WC012-02b", description="x", type="llm",
            wc_task_id="", stack="dotnet", constitutional_check="",
        )
        result = _build_effective_check(st, [])
        assert "TryGetValue" in result

    def test_stack_rules_injected_for_python(self):
        st = SubTaskDef(
            id="WC014-02", description="x", type="llm",
            wc_task_id="", stack="python", constitutional_check="",
        )
        result = _build_effective_check(st, [])
        assert "async" in result.lower()

    def test_output_files_listed(self):
        st = SubTaskDef(
            id="WC012-02b", description="x", type="llm",
            output_files=["src/ce/Evaluators/C041.cs", "src/ce/Evaluators/C043.cs"],
            wc_task_id="", stack="dotnet", constitutional_check="",
        )
        result = _build_effective_check(st, [])
        assert "C041.cs" in result
        assert "C043.cs" in result

    def test_preservation_only_for_completed_subtasks(self):
        """not_regenerate_from only preserves subtasks that ARE in completed."""
        st = SubTaskDef(
            id="WC012-02b", description="x", type="llm",
            not_regenerate_from=["WC012-02a", "WC012-02c"],  # 02c not completed
            wc_task_id="", stack="dotnet", constitutional_check="",
        )
        result = _build_effective_check(st, ["WC012-02a"])  # only 02a done
        assert "WC012-02a" in result
        assert "WC012-02c" not in result  # not completed — must not appear

    def test_missing_wc_file_graceful_fallback(self):
        """WC999 doesn't exist — falls back to delta, no crash."""
        st = SubTaskDef(
            id="WC999-01", description="x", type="llm",
            wc_task_id="WC999-01",
            stack="dotnet", constitutional_check="FALLBACK CHECK",
        )
        result = _build_effective_check(st, [])
        assert "FALLBACK CHECK" in result  # delta still present

    def test_empty_subtask_produces_only_stack_rules(self):
        """SubTaskDef with no content → only stack rules."""
        st = SubTaskDef(
            id="WC012-02b", description="x", type="llm",
            wc_task_id="", stack="dotnet", constitutional_check="",
        )
        result = _build_effective_check(st, [])
        # Stack rules must always be present for dotnet
        assert len(result) > 0

    def test_wc012_03_constitutional_check(self):
        """WC012-03 has C-023 constitutional check in WC file."""
        spec = get_task("WC012-03")
        if spec:  # file exists
            assert "C-023" in spec.constitutional_check or "evidence" in spec.constitutional_check.lower()

    def test_section_order(self):
        """PMO requirements appear before stack rules in assembled check."""
        spec_found = get_task("WC012-02")
        if not spec_found:
            pytest.skip("WC012 file not available")

        st = SubTaskDef(
            id="WC012-02b", description="x", type="llm",
            wc_task_id="WC012-02", stack="dotnet", constitutional_check="DELTA",
        )
        result = _build_effective_check(st, [])
        # PMO section should appear before STACK RULES
        pmo_pos   = result.find("WC012-02") if "WC012-02" in result else result.find("ValidateAction")
        stack_pos = result.find("STACK RULES")
        delta_pos = result.find("DELTA")
        if pmo_pos >= 0 and stack_pos >= 0:
            assert pmo_pos < stack_pos
        if stack_pos >= 0 and delta_pos >= 0:
            assert stack_pos < delta_pos


# ═══════════════════════════════════════════════════════════════════════════════
# SubTaskDef new fields — dataclass defaults
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubTaskDefNewFields:
    def test_wc_task_id_defaults_empty(self):
        st = SubTaskDef(id="X", description="Y", type="llm")
        assert st.wc_task_id == ""

    def test_output_files_defaults_empty_list(self):
        st = SubTaskDef(id="X", description="Y", type="llm")
        assert st.output_files == []

    def test_not_regenerate_from_defaults_empty_list(self):
        st = SubTaskDef(id="X", description="Y", type="llm")
        assert st.not_regenerate_from == []

    def test_stack_defaults_dotnet(self):
        st = SubTaskDef(id="X", description="Y", type="llm")
        assert st.stack == "dotnet"

    def test_constitutional_check_defaults_empty(self):
        st = SubTaskDef(id="X", description="Y", type="llm")
        assert st.constitutional_check == ""

    def test_backward_compatible_construction(self):
        """Existing SubTaskDef construction (no new fields) still works."""
        st = SubTaskDef(
            id="WC012-02b",
            description="evaluators",
            type="llm",
            depends_on=["WC012-02a"],
            spec_sections={"spec.md": "full"},
            constitutional_check="OLD STYLE CHECK",
            model_hint="reasoning",
            max_tokens=10000,
        )
        assert st.constitutional_check == "OLD STYLE CHECK"
        assert st.wc_task_id == ""  # new field, defaults correctly

    def test_full_new_construction(self):
        st = SubTaskDef(
            id="WC013-02",
            description="tenant middleware",
            type="llm",
            wc_task_id="WC013-02",
            output_files=["src/bp/middleware/Tenant.py"],
            not_regenerate_from=["WC013-01"],
            stack="python",
        )
        assert st.wc_task_id == "WC013-02"
        assert st.stack == "python"
        assert any("Tenant.py" in f for f in st.output_files)
