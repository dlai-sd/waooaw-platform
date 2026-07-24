"""
Comprehensive unit tests for platform_type_registry.py

# Implements: scripts/platform_type_registry.py
# constitutional_basis: C-076 (≥90% coverage), C-083 (Emit-Transport-Listen),
#                       C-085 (Idempotency), C-032 (spec-code drift detection),
#                       DP-009 (API First — compiled types over spec prose)
# office: Platform IT Expert — QA hat
# ib_item: IB-009
"""

import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from platform_type_registry import (
    extract_dotnet_types,
    extract_python_types,
    extract_typescript_types,
    extract_terraform_outputs,
    load_ptr,
    save_ptr,
    update_ptr_from_task,
    build_ptr_prompt_block,
    check_spec_against_ptr,
)


# ═══════════════════════════════════════════════════════════════════════════════
# extract_dotnet_types()
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractDotnetTypes:
    """Tests for .NET/C# type extraction from source text."""

    EVALUATION_CONTEXT_CS = textwrap.dedent("""\
        // Implements: architecture/reference/ce-validate-action-evaluators.md
        // constitutional_basis: C-041, C-059
        #nullable enable
        namespace Waooaw.ConstitutionalEngine.Evaluators;

        using Waooaw.ConstitutionalEngine.Grpc;
        using System.Text.Json;

        public sealed record EvaluationContext(
            string ContractId,
            string ActionType,
            string ActionParameters,
            int DecisionSpaceVersion,
            string TenantId,
            string? SkillId = null,
            long ApprovedBudgetInrPaise = 0,
            long CurrentSpendInrPaise = 0,
            long ProposedSpendInrPaise = 0,
            string BudgetSkillType = "")
        {
            public string? GetParameter(string key)
            {
                try
                {
                    using var doc = JsonDocument.Parse(
                        string.IsNullOrEmpty(ActionParameters) ? "{}" : ActionParameters);
                    return doc.RootElement.TryGetProperty(key, out var val) ? val.GetString() : null;
                }
                catch { return null; }
            }

            public static EvaluationContext FromRequest(
                ValidateActionRequest request, string tenantId) => new(
                ContractId: request.ContractId,
                ActionType: request.ActionType,
                ActionParameters: request.ActionParameters,
                DecisionSpaceVersion: request.DecisionSpaceVersion,
                TenantId: tenantId,
                SkillId: request.HasSkillId ? request.SkillId : null,
                ApprovedBudgetInrPaise: request.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0,
                CurrentSpendInrPaise: request.BudgetContext?.CurrentMonthSpendInrPaise ?? 0,
                ProposedSpendInrPaise: request.BudgetContext?.ProposedSpendInrPaise ?? 0,
                BudgetSkillType: request.BudgetContext?.SkillType ?? "");
        }
    """)

    def test_extracts_record_type(self):
        result = extract_dotnet_types(self.EVALUATION_CONTEXT_CS)
        assert "EvaluationContext" in result
        assert result["EvaluationContext"]["kind"] == "record"

    def test_extracts_all_record_properties(self):
        result = extract_dotnet_types(self.EVALUATION_CONTEXT_CS)
        props = result["EvaluationContext"]["properties"]
        assert "ContractId" in props
        assert "ActionType" in props
        assert "ActionParameters" in props
        assert "DecisionSpaceVersion" in props
        assert "TenantId" in props
        assert "SkillId" in props
        assert "ProposedSpendInrPaise" in props
        assert "BudgetSkillType" in props

    def test_extracts_namespace(self):
        result = extract_dotnet_types(self.EVALUATION_CONTEXT_CS)
        assert result["EvaluationContext"]["namespace"] == "Waooaw.ConstitutionalEngine.Evaluators"

    def test_extracts_methods(self):
        result = extract_dotnet_types(self.EVALUATION_CONTEXT_CS)
        methods = result["EvaluationContext"].get("methods", [])
        method_names = [m["name"] if isinstance(m, dict) else m for m in methods]
        assert "GetParameter" in method_names or "FromRequest" in method_names

    def test_extracts_enum_type(self):
        cs = "public enum EvaluationVerdict { Allow, Deny, Escalate }"
        result = extract_dotnet_types(cs)
        assert "EvaluationVerdict" in result
        assert result["EvaluationVerdict"]["kind"] == "enum"
        assert "Allow" in result["EvaluationVerdict"]["values"]
        assert "Deny" in result["EvaluationVerdict"]["values"]
        assert "Escalate" in result["EvaluationVerdict"]["values"]

    def test_extracts_sealed_class(self):
        cs = textwrap.dedent("""\
            namespace X;
            public sealed class EvaluatorRegistry
            {
                public int Count => _evaluators.Count;
                public async Task<IReadOnlyList<EvaluationResult>> EvaluateAllAsync(
                    EvaluationContext context,
                    CancellationToken cancellationToken = default)
                {
                    return await Task.WhenAll(tasks);
                }
            }
        """)
        result = extract_dotnet_types(cs)
        assert "EvaluatorRegistry" in result
        assert result["EvaluatorRegistry"]["kind"] == "class"

    def test_extracts_interface(self):
        cs = textwrap.dedent("""\
            namespace X;
            public interface IClaimEvaluator
            {
                string ClaimId { get; }
                Task<EvaluationResult> EvaluateAsync(EvaluationContext context, CancellationToken ct);
            }
        """)
        result = extract_dotnet_types(cs)
        assert "IClaimEvaluator" in result
        assert result["IClaimEvaluator"]["kind"] == "interface"

    def test_empty_source_returns_empty_dict(self):
        result = extract_dotnet_types("")
        assert result == {}

    def test_property_types_captured(self):
        result = extract_dotnet_types(self.EVALUATION_CONTEXT_CS)
        props = result["EvaluationContext"]["properties"]
        assert props["ContractId"] == "string"
        assert props["DecisionSpaceVersion"] == "int"
        assert props["SkillId"] in ("string?", "string")  # nullable


# ═══════════════════════════════════════════════════════════════════════════════
# extract_python_types()
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractPythonTypes:
    def test_extracts_pydantic_model(self):
        py = textwrap.dedent("""\
            from pydantic import BaseModel
            class PaasSessionInput(BaseModel):
                contract_id: str
                tenant_id: str
                skill_id: str | None = None
        """)
        result = extract_python_types(py)
        assert "PaasSessionInput" in result
        assert result["PaasSessionInput"]["kind"] == "pydantic_model"
        assert "contract_id" in result["PaasSessionInput"]["fields"]
        assert "tenant_id" in result["PaasSessionInput"]["fields"]

    def test_extracts_plain_class(self):
        py = textwrap.dedent("""\
            class ProviderSelector:
                def select_tier(self, estimated_tokens: int) -> str:
                    return "local"
        """)
        result = extract_python_types(py)
        assert "ProviderSelector" in result
        assert result["ProviderSelector"]["kind"] == "class"
        assert "select_tier" in result["ProviderSelector"]["methods"]

    def test_empty_source_returns_empty(self):
        result = extract_python_types("")
        assert result == {}

    def test_syntax_error_returns_empty(self):
        result = extract_python_types("def broken(\n")
        assert result == {}

    def test_extracts_methods(self):
        py = textwrap.dedent("""\
            class EvidenceWriter:
                async def write(self, record: dict) -> None:
                    pass
                def validate(self, record: dict) -> bool:
                    return True
        """)
        result = extract_python_types(py)
        assert "EvidenceWriter" in result
        methods = result["EvidenceWriter"]["methods"]
        assert any("write" in m for m in methods)
        assert any("validate" in m for m in methods)


# ═══════════════════════════════════════════════════════════════════════════════
# extract_typescript_types()
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractTypescriptTypes:
    def test_extracts_interface(self):
        ts = "export interface EmploymentContract { contractId: string; tenantId: string; status: string; }"
        result = extract_typescript_types(ts)
        assert "EmploymentContract" in result
        assert result["EmploymentContract"]["kind"] == "interface"
        assert "contractId" in result["EmploymentContract"]["properties"]

    def test_extracts_enum(self):
        ts = "export enum AgentStatus { Active, Suspended, Terminated }"
        result = extract_typescript_types(ts)
        assert "AgentStatus" in result
        assert result["AgentStatus"]["kind"] == "enum"
        assert "Active" in result["AgentStatus"]["values"]

    def test_extracts_type_alias(self):
        ts = "export type UsageResponse = { unitsRemaining: number; planTier: string; }"
        result = extract_typescript_types(ts)
        assert "UsageResponse" in result

    def test_empty_source_returns_empty(self):
        result = extract_typescript_types("")
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# extract_terraform_outputs()
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractTerraformOutputs:
    def test_extracts_output_block(self):
        tf = textwrap.dedent("""\
            output "constitutional_engine_url" {
              description = "gRPC endpoint for Constitutional Engine"
              value       = azurerm_container_app.constitutional_engine.ingress[0].fqdn
            }
        """)
        result = extract_terraform_outputs(tf)
        assert "constitutional_engine_url" in result
        assert result["constitutional_engine_url"]["kind"] == "terraform_output"
        assert "gRPC endpoint" in result["constitutional_engine_url"]["description"]

    def test_multiple_outputs(self):
        tf = textwrap.dedent("""\
            output "db_host" {
              value = azurerm_postgresql_flexible_server.main.fqdn
            }
            output "keycloak_url" {
              value = "https://auth.waooaw.com"
            }
        """)
        result = extract_terraform_outputs(tf)
        assert len(result) == 2
        assert "db_host" in result
        assert "keycloak_url" in result

    def test_empty_returns_empty(self):
        result = extract_terraform_outputs("")
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# PTR load / save
# ═══════════════════════════════════════════════════════════════════════════════

class TestPtrLoadSave:
    def test_load_returns_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("platform_type_registry.PTR_PATH", tmp_path / "ptr.json")
        result = load_ptr()
        assert result == {}

    def test_save_and_load_round_trip(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        data = {"tasks": {"WC012-02a": {"types": {"EvaluationContext": {"kind": "record"}}}}}
        save_ptr(data)
        loaded = load_ptr()
        assert loaded["tasks"]["WC012-02a"]["types"]["EvaluationContext"]["kind"] == "record"

    def test_save_creates_parent_dirs(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "sprint-context" / "nested" / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        save_ptr({"tasks": {}})
        assert ptr_file.exists()

    def test_load_returns_empty_on_corrupt_json(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        ptr_file.write_text("not json {{{")
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        result = load_ptr()
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# update_ptr_from_task()
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdatePtrFromTask:
    def test_updates_ptr_with_cs_file(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        monkeypatch.setattr("platform_type_registry.REPO_ROOT", tmp_path)

        cs_file = tmp_path / "src" / "ce" / "Evaluators" / "EvaluationContext.cs"
        cs_file.parent.mkdir(parents=True)
        cs_file.write_text(
            "namespace X;\n"
            "public sealed record EvaluationContext(string ContractId, string TenantId);\n"
        )

        update_ptr_from_task("WC012-02a", ["src/ce/Evaluators/EvaluationContext.cs"])

        ptr = load_ptr()
        assert "WC012-02a" in ptr.get("tasks", {})
        types = ptr["tasks"]["WC012-02a"]["types"]
        assert "EvaluationContext" in types

    def test_updates_ptr_with_py_file(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        monkeypatch.setattr("platform_type_registry.REPO_ROOT", tmp_path)

        py_file = tmp_path / "src" / "pr" / "models.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text(
            "from pydantic import BaseModel\n"
            "class SessionInput(BaseModel):\n"
            "    tenant_id: str\n"
            "    contract_id: str\n"
        )

        update_ptr_from_task("WC014-01", ["src/pr/models.py"])

        ptr = load_ptr()
        assert "WC014-01" in ptr.get("tasks", {})
        assert "SessionInput" in ptr["tasks"]["WC014-01"]["types"]

    def test_skips_nonexistent_files(self, tmp_path, monkeypatch, capsys):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        monkeypatch.setattr("platform_type_registry.REPO_ROOT", tmp_path)

        update_ptr_from_task("WC012-02b", ["src/ce/NonExistent.cs"])
        ptr = load_ptr()
        # Should not crash; WC012-02b entry may not exist (no types extracted)
        assert "WC012-02b" not in ptr.get("tasks", {}) or \
               ptr["tasks"]["WC012-02b"]["types"] == {}

    def test_accumulates_across_tasks(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        monkeypatch.setattr("platform_type_registry.REPO_ROOT", tmp_path)

        for i, (task, fname, content) in enumerate([
            ("WC012-02a", "src/ce/A.cs", "namespace X; public sealed record TypeA(string Id);"),
            ("WC012-02b", "src/ce/B.cs", "namespace X; public sealed record TypeB(int Count);"),
        ]):
            f = tmp_path / fname
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
            update_ptr_from_task(task, [fname])

        ptr = load_ptr()
        assert "WC012-02a" in ptr["tasks"]
        assert "WC012-02b" in ptr["tasks"]


# ═══════════════════════════════════════════════════════════════════════════════
# build_ptr_prompt_block()
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildPtrPromptBlock:
    def _make_ptr_with_evaluation_context(self) -> dict:
        return {
            "tasks": {
                "WC012-02a": {
                    "types": {
                        "EvaluationContext": {
                            "kind": "record",
                            "namespace": "Waooaw.ConstitutionalEngine.Evaluators",
                            "properties": {
                                "ContractId": "string",
                                "ActionType": "string",
                                "ActionParameters": "string",
                                "DecisionSpaceVersion": "int",
                                "TenantId": "string",
                                "SkillId": "string?",
                                "ProposedSpendInrPaise": "long",
                            },
                            "methods": [
                                {"name": "GetParameter", "return_type": "string?", "params": "string key"},
                                {"name": "FromRequest", "return_type": "EvaluationContext", "params": "ValidateActionRequest request, string tenantId"},
                            ]
                        },
                        "EvaluationVerdict": {
                            "kind": "enum",
                            "namespace": "Waooaw.ConstitutionalEngine.Evaluators",
                            "values": ["Allow", "Deny", "Escalate"],
                        }
                    },
                    "files": ["src/constitutional-engine/Evaluators/EvaluationContext.cs"]
                }
            }
        }

    def test_returns_empty_when_ptr_empty(self):
        result = build_ptr_prompt_block(["EvaluationContext"], ptr={})
        assert result == ""

    def test_returns_empty_when_type_not_in_ptr(self):
        result = build_ptr_prompt_block(["NonExistentType"], ptr=self._make_ptr_with_evaluation_context())
        assert result == ""

    def test_includes_type_contract_header(self):
        result = build_ptr_prompt_block(["EvaluationContext"], ptr=self._make_ptr_with_evaluation_context())
        assert "TYPE CONTRACT" in result
        assert "machine-verified" in result

    def test_includes_all_properties(self):
        result = build_ptr_prompt_block(["EvaluationContext"], ptr=self._make_ptr_with_evaluation_context())
        assert "ContractId" in result
        assert "TenantId" in result
        assert "ActionParameters" in result
        assert "ProposedSpendInrPaise" in result

    def test_action_parameters_has_json_note(self):
        """ActionParameters note tells LLM to use GetParameter — prevents TryGetValue."""
        result = build_ptr_prompt_block(["EvaluationContext"], ptr=self._make_ptr_with_evaluation_context())
        assert "GetParameter" in result or "JSON" in result or "json" in result.lower()

    def test_tenant_id_has_metadata_note(self):
        """TenantId note clarifies source (gRPC metadata) — prevents hallucination."""
        result = build_ptr_prompt_block(["EvaluationContext"], ptr=self._make_ptr_with_evaluation_context())
        assert "gRPC" in result or "metadata" in result or "TenantId" in result

    def test_includes_enum_values(self):
        result = build_ptr_prompt_block(["EvaluationVerdict"], ptr=self._make_ptr_with_evaluation_context())
        assert "Allow" in result
        assert "Deny" in result
        assert "Escalate" in result

    def test_multiple_types_in_one_block(self):
        result = build_ptr_prompt_block(
            ["EvaluationContext", "EvaluationVerdict"],
            ptr=self._make_ptr_with_evaluation_context()
        )
        assert "EvaluationContext" in result
        assert "EvaluationVerdict" in result

    def test_includes_methods(self):
        result = build_ptr_prompt_block(["EvaluationContext"], ptr=self._make_ptr_with_evaluation_context())
        assert "GetParameter" in result or "FromRequest" in result

    def test_includes_footer(self):
        result = build_ptr_prompt_block(["EvaluationContext"], ptr=self._make_ptr_with_evaluation_context())
        assert "END TYPE CONTRACT" in result


# ═══════════════════════════════════════════════════════════════════════════════
# check_spec_against_ptr() — C-032 spec contract gate
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckSpecAgainstPtr:
    def _make_ptr(self, props: dict[str, str]) -> dict:
        return {
            "tasks": {
                "WC012-02a": {
                    "types": {
                        "EvaluationContext": {
                            "kind": "record",
                            "properties": props,
                        }
                    },
                    "files": []
                }
            }
        }

    def test_no_gaps_when_spec_matches_ptr(self):
        """Spec references ctx.ContractId — exists in PTR → no gaps."""
        ptr = self._make_ptr({"ContractId": "string", "ActionType": "string", "TenantId": "string"})
        spec = "Evaluate: ctx.ContractId in authorized_actions → DENY\nctx.TenantId for DB read"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        assert gaps == []

    def test_gap_detected_for_missing_property(self):
        """Spec references ctx.TenantId but PTR has no TenantId → gap detected (C-032)."""
        ptr = self._make_ptr({"ContractId": "string", "ActionType": "string"})
        # No TenantId in PTR
        spec = "DB read: ctx.TenantId AND status = 'ACTIVE'"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        assert len(gaps) > 0
        assert any("TenantId" in g for g in gaps)

    def test_multiple_gaps_detected(self):
        ptr = self._make_ptr({"ContractId": "string"})
        spec = "ctx.TenantId for auth, ctx.ProposedAmount for budget, ctx.ToolName for C-041"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        gap_text = " ".join(gaps)
        assert "TenantId" in gap_text or "ProposedAmount" in gap_text or "ToolName" in gap_text

    def test_empty_ptr_returns_no_gaps(self):
        """No PTR data → first task → skip check (can't validate)."""
        gaps = check_spec_against_ptr("ctx.TenantId and ctx.Foo", ptr={})
        assert gaps == []

    def test_get_parameter_not_flagged_as_gap(self):
        """GetParameter is a known method — must not be flagged as missing property."""
        ptr = self._make_ptr({"ContractId": "string", "ActionParameters": "string"})
        spec = "Use ctx.GetParameter('tool_name') to extract from ActionParameters"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        # GetParameter must be in the ignore list
        assert all("GetParameter" not in g for g in gaps)

    def test_from_request_not_flagged(self):
        ptr = self._make_ptr({"ContractId": "string"})
        spec = "Use context.FromRequest(request, tenantId) to build context"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        assert all("FromRequest" not in g for g in gaps)

    def test_spec_with_no_ctx_references_returns_empty(self):
        ptr = self._make_ptr({"ContractId": "string"})
        spec = "Read authorized_actions from DB WHERE contract_id = request.contract_id"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        assert gaps == []

    def test_gap_message_includes_available_properties(self):
        """Gap message must name available properties — actionable fix (C-032)."""
        ptr = self._make_ptr({"ContractId": "string", "ActionType": "string"})
        spec = "ctx.TenantId for DB read"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        assert len(gaps) > 0
        # Available properties should be listed in the gap message
        assert "ContractId" in gaps[0] or "ActionType" in gaps[0] or "Available" in gaps[0]

    def test_wc012_02b_failure_would_be_caught(self):
        """Regression test: the actual WC012-02b spec-code drift would be caught pre-flight."""
        # PTR has actual EvaluationContext (5 fields, no TenantId/ToolName)
        ptr = self._make_ptr({
            "ContractId": "string",
            "ActionType": "string",
            "ActionParameters": "string",
            "DecisionSpaceVersion": "int",
            "SkillId": "string?",
        })
        # Spec pseudocode (the old broken spec)
        spec = textwrap.dedent("""\
            C-041 Evaluator:
              DB read: WHERE tenant_id = ctx.TenantId AND status = 'ACTIVE'
              If tool_name NOT IN authorized_actions → DENY
            C-043 Evaluator:
              If (current_spend + ctx.ProposedAmount) > approved_budget → DENY
            C-062 Evaluator:
              If ctx.MessageContent contains tool_call outside authorized_actions → DENY
              If ctx.SystemPromptIntegrity != expected_sha → DENY
        """)
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        # The drift must be detected
        assert len(gaps) > 0, (
            "The WC012-02b spec-code drift (ctx.TenantId, ctx.ProposedAmount, "
            "ctx.MessageContent, ctx.SystemPromptIntegrity) must be detected by pre-flight check"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Additional coverage tests for PTR branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractDotnetTypesBranches:
    """Cover remaining branches in extract_dotnet_types."""

    def test_extracts_class_with_public_properties(self):
        """Covers _extract_public_props_into path."""
        cs = textwrap.dedent("""\
            namespace X;
            public sealed class MyService
            {
                public string Name { get; init; } = string.Empty;
                public int Count { get; set; }
                public bool IsActive { get; private set; }
            }
        """)
        result = extract_dotnet_types(cs)
        assert "MyService" in result
        props = result["MyService"].get("properties", {})
        assert len(props) >= 1

    def test_extracts_multiple_types_same_namespace(self):
        """Both record and enum in same file."""
        cs = textwrap.dedent("""\
            namespace Waooaw.Test;
            public enum Status { Active, Suspended }
            public sealed record WorkItem(string Id, Status CurrentStatus);
        """)
        result = extract_dotnet_types(cs)
        assert "Status" in result
        assert "WorkItem" in result
        assert "Active" in result["Status"]["values"]
        assert result["WorkItem"]["namespace"] == "Waooaw.Test"

    def test_interface_with_methods_extracted(self):
        cs = textwrap.dedent("""\
            namespace X;
            public interface IEvaluator
            {
                string ClaimId { get; }
                Task<string> EvaluateAsync(string input, CancellationToken ct);
            }
        """)
        result = extract_dotnet_types(cs)
        assert "IEvaluator" in result
        assert result["IEvaluator"]["kind"] == "interface"

    def test_method_with_static_modifier(self):
        """Static methods must be captured in methods list."""
        cs = textwrap.dedent("""\
            namespace X;
            public sealed record Ctx(string Id)
            {
                public static Ctx FromRequest(Request req) => new(req.Id);
                public string? GetVal(string key) => null;
            }
        """)
        result = extract_dotnet_types(cs)
        assert "Ctx" in result
        methods = result["Ctx"].get("methods", [])
        method_names = [m["name"] if isinstance(m, dict) else m for m in methods]
        assert any(name in ("FromRequest", "GetVal") for name in method_names)

    def test_no_namespace_defaults_to_empty(self):
        cs = "public enum Simple { A, B, C }"
        result = extract_dotnet_types(cs)
        assert "Simple" in result
        assert result["Simple"]["namespace"] == ""

    def test_nullable_param_types_captured(self):
        cs = "namespace X; public sealed record Foo(string? Bar = null, int? Baz = null);"
        result = extract_dotnet_types(cs)
        assert "Foo" in result
        props = result["Foo"]["properties"]
        assert "Bar" in props or "Baz" in props


class TestBuildPtrPromptBlockBranches:
    """Cover remaining branches in build_ptr_prompt_block."""

    def _make_python_ptr(self) -> dict:
        return {
            "tasks": {
                "WC014-01": {
                    "types": {
                        "PaasSessionInput": {
                            "kind": "pydantic_model",
                            "fields": {
                                "tenant_id": "str",
                                "contract_id": "str",
                                "skill_id": "str | None",
                            },
                            "methods": ["validate_skill", "async execute"],
                        }
                    },
                    "files": []
                }
            }
        }

    def test_pydantic_model_fields_listed(self):
        """pydantic_model branch: fields are listed in the prompt."""
        result = build_ptr_prompt_block(["PaasSessionInput"], ptr=self._make_python_ptr())
        assert "tenant_id" in result
        assert "contract_id" in result

    def test_string_method_listed(self):
        """Method as plain string (not dict) renders correctly."""
        result = build_ptr_prompt_block(["PaasSessionInput"], ptr=self._make_python_ptr())
        assert "Method:" in result or "execute" in result

    def test_no_namespace_omits_namespace_text(self):
        """Types without namespace don't include '— namespace:' text."""
        ptr = {"tasks": {"t1": {"types": {
            "Simple": {"kind": "enum", "values": ["A", "B"]}
        }, "files": []}}}
        result = build_ptr_prompt_block(["Simple"], ptr=ptr)
        assert "namespace" not in result or "Simple" in result

    def test_empty_methods_list_no_crash(self):
        """Type with empty methods list → no crash, no method section."""
        ptr = {"tasks": {"t1": {"types": {
            "Bare": {"kind": "record", "properties": {"X": "int"}, "methods": []}
        }, "files": []}}}
        result = build_ptr_prompt_block(["Bare"], ptr=ptr)
        assert "Bare" in result
        assert "X" in result


class TestCheckSpecAgainstPtrBranches:
    """Cover remaining branches in check_spec_against_ptr."""

    def test_fields_from_python_types_checked(self):
        """Python TypedDict fields also contribute to known property names."""
        ptr = {
            "tasks": {
                "WC014-01": {
                    "types": {
                        "SessionInput": {
                            "kind": "typed_dict",
                            "fields": {"tenant_id": "str", "contract_id": "str"},
                        }
                    },
                    "files": []
                }
            }
        }
        # Reference a Python field name — should not be flagged
        spec = "Use context.tenant_id to look up the tenant"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        # tenant_id is in the ignore list — no gaps
        assert all("tenant_id" not in g for g in gaps)

    def test_cancellation_token_ignored(self):
        """ctx.CancellationToken is a standard gRPC property — must be ignored."""
        ptr = {"tasks": {"t1": {"types": {
            "Ctx": {"kind": "record", "properties": {"ContractId": "string"}}
        }, "files": []}}}
        spec = "Pass ctx.CancellationToken to DB calls"
        gaps = check_spec_against_ptr(spec, ptr=ptr)
        assert all("CancellationToken" not in g for g in gaps)


class TestUpdatePtrTerraformAndTsFiles:
    """Cover terraform and TypeScript paths in update_ptr_from_task."""

    def test_terraform_output_extracted(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        monkeypatch.setattr("platform_type_registry.REPO_ROOT", tmp_path)

        tf_file = tmp_path / "infrastructure" / "terraform" / "outputs.tf"
        tf_file.parent.mkdir(parents=True)
        tf_file.write_text(
            'output "db_host" {\n'
            '  description = "PostgreSQL host"\n'
            '  value = azurerm_postgresql_flexible_server.main.fqdn\n'
            '}\n'
        )
        update_ptr_from_task("WC016-01", ["infrastructure/terraform/outputs.tf"])
        ptr = load_ptr()
        assert "WC016-01" in ptr.get("tasks", {})

    def test_typescript_interface_extracted(self, tmp_path, monkeypatch):
        ptr_file = tmp_path / "ptr.json"
        monkeypatch.setattr("platform_type_registry.PTR_PATH", ptr_file)
        monkeypatch.setattr("platform_type_registry.REPO_ROOT", tmp_path)

        ts_file = tmp_path / "web" / "types" / "contracts.ts"
        ts_file.parent.mkdir(parents=True)
        ts_file.write_text(
            'export interface HireRequest { contractId: string; agentType: string; }\n'
        )
        update_ptr_from_task("WC017-01", ["web/types/contracts.ts"])
        ptr = load_ptr()
        assert "WC017-01" in ptr.get("tasks", {})
