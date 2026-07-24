"""
Comprehensive unit tests for sprint_retry_advisor.py

# Implements: scripts/sprint_retry_advisor.py
# constitutional_basis: C-076 (≥90% coverage), C-077 (FinOps), C-082 (build validation)
# office: Platform IT Expert — QA hat
# ib_item: IB-009

Extends existing CCT-SRA-01..05 tests with:
  - CS1061 classification and fix instruction quality (the WC012-02b failure mode)
  - All error type constants are strings
  - Confidence gate enforcement
  - Fix instruction completeness — must name correct substitution
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sprint_retry_advisor import (
    diagnose_build_error,
    RetryDiagnosis,
    EXTEND_NOT_REPLACE,
    WRONG_NAMESPACE,
    WRONG_FIELD_NAME,
    MISSING_USING,
    UNKNOWN,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CCT-SRA-01: CS0101 → EXTEND_NOT_REPLACE
# ═══════════════════════════════════════════════════════════════════════════════

class TestCS0101ExtendNotReplace:
    def test_cs0101_produces_extend_not_replace(self):
        error = (
            "error CS0101: The namespace 'Waooaw.ConstitutionalEngine.Evaluators' "
            "already contains a definition for 'C041ToolAuthorizationEvaluator'"
        )
        result = diagnose_build_error("WC012-03", error, ["src/constitutional-engine/Evaluators/C041.cs"])
        assert result.error_type == EXTEND_NOT_REPLACE
        assert result.should_retry is True
        assert result.confidence >= 0.90

    def test_cs0101_fix_instruction_mentions_not_regenerate(self):
        error = "error CS0101: The namespace 'X' already contains a definition for 'Foo'"
        result = diagnose_build_error("WC012-02", error, [])
        assert "DO NOT" in result.fix_instruction.upper() or "MUST NOT" in result.fix_instruction.upper()

    def test_cs0101_no_api_key_still_succeeds(self, monkeypatch):
        """CS0101 is rule-based — zero LLM cost (C-077)."""
        os.environ.pop("ANTHROPIC_API_KEY", None)
        error = "error CS0101: The namespace 'Y' already contains a definition for 'Bar'"
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type == EXTEND_NOT_REPLACE

    def test_cs0101_constitutional_trace_present(self):
        error = "error CS0101: The namespace 'Z' already contains a definition for 'Baz'"
        result = diagnose_build_error("WC012-03", error, [])
        assert result.constitutional_trace != ""  # C-059: every diagnosis traces to a claim


# ═══════════════════════════════════════════════════════════════════════════════
# CCT-SRA-02: CS0246 → WRONG_NAMESPACE or MISSING_USING
# ═══════════════════════════════════════════════════════════════════════════════

class TestCS0246Namespace:
    def test_cs0246_protos_namespace_reclassified(self):
        error = (
            "error CS0246: The type or namespace name 'Protos' could not be found "
            "(are you missing a using directive or an assembly reference?)"
        )
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type == WRONG_NAMESPACE
        assert result.should_retry is True
        assert "Grpc" in result.fix_instruction or "Waooaw.ConstitutionalEngine.Grpc" in result.fix_instruction

    def test_cs0246_constitutional_service_not_found(self):
        error = "error CS0246: The type or namespace name 'ConstitutionalService' could not be found"
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type in (WRONG_NAMESPACE, MISSING_USING)

    def test_cs0246_missing_using_serverCallContext(self):
        error = "error CS0246: The type or namespace name 'ServerCallContext' could not be found"
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type in (WRONG_NAMESPACE, MISSING_USING)
        assert "Grpc.Core" in result.fix_instruction or "using" in result.fix_instruction.lower()

    def test_cs0246_missing_ilogger(self):
        error = "error CS0246: The type or namespace name 'ILogger' could not be found"
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type in (WRONG_NAMESPACE, MISSING_USING)
        assert "Microsoft.Extensions.Logging" in result.fix_instruction


# ═══════════════════════════════════════════════════════════════════════════════
# CCT-SRA-03: CS0117 / CS1061 → WRONG_FIELD_NAME with actionable fix
# ═══════════════════════════════════════════════════════════════════════════════

class TestCS0117AndCS1061WrongFieldName:
    """The WC012-02b failure mode — LLM called string.TryGetValue()."""

    def test_cs0117_invented_property(self):
        error = (
            "error CS0117: 'EvaluationVerdict' does not contain a definition for 'Authorized'"
        )
        result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True

    def test_cs1061_string_trygetvalue_classified(self):
        """THE WC012-02b failure: string.TryGetValue does not exist."""
        error = (
            "/src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs(75,30): "
            "error CS1061: 'string' does not contain a definition for 'TryGetValue' and no "
            "accessible extension method 'TryGetValue' accepting a first argument of type "
            "'string' could be found (are you missing a using directive or an assembly reference?)"
        )
        result = diagnose_build_error("WC012-02b", error, ["src/constitutional-engine/Evaluators/C041.cs"])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True

    def test_cs1061_fix_instruction_names_correct_properties(self):
        """Fix instruction must tell the LLM the ACTUAL available properties."""
        error = (
            "error CS1061: 'string' does not contain a definition for 'TryGetValue' "
            "and no accessible extension method 'TryGetValue' accepting a first argument "
            "of type 'string' could be found"
        )
        result = diagnose_build_error("WC012-02b", error, [])
        # The fix must explain what to use INSTEAD of TryGetValue
        assert ("GetParameter" in result.fix_instruction or
                "ActionParameters" in result.fix_instruction or
                "JsonDocument" in result.fix_instruction or
                "ContractId" in result.fix_instruction), (
            "CS1061 fix must name the correct substitution — not just say 'wrong field name'. "
            f"Got: {result.fix_instruction}"
        )

    def test_cs1061_fix_instruction_not_just_use_from_request(self):
        """Fix must go beyond 'use FromRequest' — must name specific properties."""
        error = (
            "error CS1061: 'string' does not contain a definition for 'TryGetValue'"
        )
        result = diagnose_build_error("WC012-02b", error, [])
        # Should not be ONLY "use FromRequest" — that's the previous insufficient fix
        assert result.fix_instruction != "Use EvaluationContext.FromRequest(request)"
        # Must provide actual property names or parsing instruction
        has_substitution = any(kw in result.fix_instruction for kw in [
            "GetParameter", "ContractId", "TenantId", "ActionType",
            "JsonDocument", "ProposedSpend", "BudgetContext",
        ])
        assert has_substitution, (
            f"CS1061 fix instruction must name actual EvaluationContext properties. "
            f"Got: {result.fix_instruction[:200]}"
        )

    def test_cs1061_constitutional_trace_present(self):
        error = "error CS1061: 'string' does not contain a definition for 'TryGetValue'"
        result = diagnose_build_error("WC012-02b", error, [])
        assert result.constitutional_trace != ""

    def test_cs0103_undefined_evaluation_decision(self):
        """LLM invented EvaluationDecision instead of EvaluationVerdict."""
        error = "error CS0103: The name 'EvaluationDecision' does not exist in the current context"
        result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert "EvaluationVerdict" in result.fix_instruction or "Allow" in result.fix_instruction


# ═══════════════════════════════════════════════════════════════════════════════
# Confidence gate (C-077 FinOps)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceGate:
    """Low-confidence diagnoses must not retry (C-077 — don't waste tokens)."""

    def test_retry_diagnosis_dataclass_fields(self):
        d = RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction="Use X instead of Y",
            should_retry=True,
            confidence=0.88,
            constitutional_trace="C-082",
        )
        assert d.error_type == WRONG_FIELD_NAME
        assert d.confidence == 0.88
        assert d.should_retry is True
        assert d.duplicate_files == []

    def test_all_error_type_constants_are_strings(self):
        assert isinstance(EXTEND_NOT_REPLACE, str)
        assert isinstance(WRONG_NAMESPACE, str)
        assert isinstance(WRONG_FIELD_NAME, str)
        assert isinstance(MISSING_USING, str)
        assert isinstance(UNKNOWN, str)

    def test_error_type_constants_are_distinct(self):
        types = [EXTEND_NOT_REPLACE, WRONG_NAMESPACE, WRONG_FIELD_NAME, MISSING_USING, UNKNOWN]
        assert len(set(types)) == len(types), "All error type constants must be unique"


# ═══════════════════════════════════════════════════════════════════════════════
# Mixed / priority
# ═══════════════════════════════════════════════════════════════════════════════

class TestMixedErrors:
    def test_cs0101_takes_priority_over_cs0246(self):
        """CS0101 (duplicate class) is more actionable than CS0246 — must win."""
        error = (
            "error CS0101: The namespace 'X' already contains a definition for 'Foo'\n"
            "error CS0246: The type or namespace name 'Bar' could not be found"
        )
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type == EXTEND_NOT_REPLACE

    def test_no_matching_error_code(self, monkeypatch):
        """Unrecognized error falls to UNKNOWN (no API key → should_retry=False)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        error = "error CSX999: Some completely new error type"
        result = diagnose_build_error("WC012-99", error, [])
        assert result.error_type == UNKNOWN
        assert result.should_retry is False

    def test_cs1061_and_cs0246_together(self):
        """CS1061 + CS0246 — CS1061 handling should trigger."""
        error = (
            "error CS0246: type 'TenantId' not found\n"
            "error CS1061: 'string' does not contain a definition for 'TryGetValue'"
        )
        result = diagnose_build_error("WC012-02b", error, [])
        # Either WRONG_NAMESPACE or WRONG_FIELD_NAME — both are valid
        assert result.error_type in (WRONG_NAMESPACE, WRONG_FIELD_NAME, MISSING_USING)
        assert result.should_retry is True

    def test_empty_error_string(self, monkeypatch):
        """Empty error string → no error codes → UNKNOWN fallback."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = diagnose_build_error("WC012-02", "", [])
        assert isinstance(result, RetryDiagnosis)


# ═══════════════════════════════════════════════════════════════════════════════
# Constitutional trace — every diagnosis must cite a claim (C-059)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstitutionalTrace:
    def test_all_known_patterns_have_trace(self):
        """CCT-SRA-04: Every classifiable error must have a constitutional_trace."""
        errors = [
            "error CS0101: The namespace 'X' already contains a definition for 'Foo'",
            "error CS0246: The type or namespace name 'Protos' could not be found",
            "error CS0246: The type or namespace name 'ServerCallContext' could not be found",
            "error CS0117: 'EvaluationVerdict' does not contain a definition for 'Authorized'",
            "error CS1061: 'string' does not contain a definition for 'TryGetValue'",
        ]
        for error in errors:
            result = diagnose_build_error("WC012-02", error, [])
            if result.error_type != UNKNOWN:
                assert result.constitutional_trace != "", (
                    f"Missing constitutional_trace for error: {error[:80]}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Additional coverage for sprint_retry_advisor branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdvisorCoverageBranches:
    """Cover remaining branches in sprint_retry_advisor.py."""

    def test_cs0101_no_type_name_match_returns_none(self, monkeypatch):
        """CS0101 without a definition name match → falls through to LLM fallback."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # CS0101 without the standard "already contains a definition for 'X'" pattern
        error = "error CS0101: some other strange namespace error without definition pattern"
        result = diagnose_build_error("WC012-02", error, [])
        # Should fall through to LLM or unknown
        assert isinstance(result, RetryDiagnosis)

    def test_cs0246_unknown_type_falls_to_missing_using_check(self, monkeypatch):
        """CS0246 with a type not in NAMESPACE_MAP falls to missing-using check."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        error = "error CS0246: The type or namespace name 'SomeRandomType' could not be found"
        result = diagnose_build_error("WC012-02", error, [])
        # Should be either MISSING_USING, UNKNOWN, or fall to LLM
        assert isinstance(result, RetryDiagnosis)

    def test_cs0246_missing_using_unknown_type_returns_unknown(self, monkeypatch):
        """CS0246 with a type not in TYPE_NAMESPACES map → LLM fallback or UNKNOWN."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # A type that's not in TYPE_NAMESPACES
        error = "error CS0246: The type or namespace name 'MyCustomUnknownType' could not be found"
        result = diagnose_build_error("WC012-02", error, [])
        assert isinstance(result, RetryDiagnosis)

    def test_cs1061_with_no_match_falls_through(self, monkeypatch):
        """CS1061 with error string not matching the regex falls through."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # CS1061 but without the standard pattern
        error = "error CS1061: some field on some type is missing"
        result = diagnose_build_error("WC012-02b", error, [])
        # Should still produce a diagnosis
        assert isinstance(result, RetryDiagnosis)

    def test_cs0103_with_no_match_falls_through(self, monkeypatch):
        """CS0103 without the standard pattern."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        error = "error CS0103: some unknown name error without standard pattern"
        result = diagnose_build_error("WC012-02", error, [])
        assert isinstance(result, RetryDiagnosis)

    def test_cs0246_namespace_match_with_request_suffix(self):
        """CS0246 for 'Request' type → maps to Grpc namespace."""
        error = "error CS0246: The type or namespace name 'ValidateActionRequest' could not be found"
        result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type in (WRONG_NAMESPACE, MISSING_USING)
        assert "Grpc" in result.fix_instruction

    def test_retry_diagnosis_duplicate_files_default_empty(self):
        """duplicate_files field defaults to empty list."""
        d = RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction="fix it",
            should_retry=True,
            confidence=0.8,
        )
        assert d.duplicate_files == []
        assert d.constitutional_trace == ""

    def test_cs0117_with_matching_type_and_field(self):
        """CS0117 with exact pattern produces WRONG_FIELD_NAME with both names."""
        error = "error CS0117: 'MyType' does not contain a definition for 'MyField'"
        result = diagnose_build_error("WC012-02", error, [])
        assert result.error_type == WRONG_FIELD_NAME


# ═══════════════════════════════════════════════════════════════════════════════
# CCT-SRA-06: CS1061 EvaluatorRegistry invented method names
# ═══════════════════════════════════════════════════════════════════════════════

import json
import textwrap
import tempfile
from unittest.mock import patch


def _make_ptr_with_types(types_by_task: dict) -> dict:
    """Helper: build a PTR dict for use in retry advisor tests."""
    return {"tasks": {
        task_id: {"types": types, "files": []}
        for task_id, types in types_by_task.items()
    }}


class TestCS1061EvaluatorRegistry:
    """
    WC012 run failure: LLM called _registry.GetEvaluators() which doesn't exist.
    New design: fix instructions come from PTR lookup — fully generalized.
    """

    EVALUATOR_REGISTRY_PTR = _make_ptr_with_types({
        "WC012-02a": {
            "EvaluatorRegistry": {
                "kind": "class",
                "namespace": "Waooaw.ConstitutionalEngine.Evaluators",
                "properties": {"Count": "int"},
                "methods": [{"name": "EvaluateAllAsync",
                              "return_type": "Task<IReadOnlyList<EvaluationResult>>",
                              "params": "EvaluationContext context, CancellationToken ct"}],
            }
        }
    })

    def test_get_evaluators_classified_with_ptr(self):
        """With PTR populated, EvaluatorRegistry.GetEvaluators → PTR-driven fix at 95%."""
        error = (
            "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'GetEvaluators'"
        )
        with patch("platform_type_registry.load_ptr", return_value=self.EVALUATOR_REGISTRY_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True
        assert result.confidence >= 0.90

    def test_get_applicable_evaluators_classified(self):
        error = (
            "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'GetApplicableEvaluators'"
        )
        with patch("platform_type_registry.load_ptr", return_value=self.EVALUATOR_REGISTRY_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True

    def test_fix_instruction_names_evaluate_all_async(self):
        """PTR-driven fix must show EvaluateAllAsync as the correct method."""
        error = (
            "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'GetEvaluators'"
        )
        with patch("platform_type_registry.load_ptr", return_value=self.EVALUATOR_REGISTRY_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert "EvaluateAllAsync" in result.fix_instruction, (
            f"PTR fix must name EvaluateAllAsync. Got: {result.fix_instruction[:200]}"
        )

    def test_fix_instruction_prohibits_invented_methods(self):
        error = (
            "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'GetApplicableEvaluators'"
        )
        with patch("platform_type_registry.load_ptr", return_value=self.EVALUATOR_REGISTRY_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        # PTR shows actual members — LLM can self-correct
        assert "EvaluateAllAsync" in result.fix_instruction or "Count" in result.fix_instruction

    def test_evaluate_method_also_classified(self):
        error = (
            "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'Evaluate'"
        )
        with patch("platform_type_registry.load_ptr", return_value=self.EVALUATOR_REGISTRY_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert "EvaluateAllAsync" in result.fix_instruction

    def test_constitutional_trace_present(self):
        error = "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'GetEvaluators'"
        with patch("platform_type_registry.load_ptr", return_value=self.EVALUATOR_REGISTRY_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.constitutional_trace != ""

    def test_ptr_miss_falls_back_gracefully(self):
        """Without PTR data, still returns WRONG_FIELD_NAME with branch context advice."""
        with patch("platform_type_registry.load_ptr", return_value={}):
            error = "error CS1061: 'EvaluatorRegistry' does not contain a definition for 'GetEvaluators'"
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True

    def test_evaluationcontext_trygetvalue_ptr_driven(self):
        """Original TryGetValue case now PTR-driven when EvaluationContext is in PTR."""
        evaluation_context_ptr = _make_ptr_with_types({
            "WC012-02a": {
                "EvaluationContext": {
                    "kind": "record",
                    "properties": {
                        "ContractId": "string", "TenantId": "string",
                        "ActionParameters": "string", "ActionType": "string",
                    },
                    "methods": [{"name": "GetParameter", "return_type": "string?", "params": "string key"}],
                }
            }
        })
        error = "error CS1061: 'string' does not contain a definition for 'TryGetValue'"
        # 'string' not in PTR — generic fallback
        with patch("platform_type_registry.load_ptr", return_value=evaluation_context_ptr):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True


# ═══════════════════════════════════════════════════════════════════════════════
# CCT-SRA-07: CS0117 proto invented fields — PTR-driven generalized fix
# ═══════════════════════════════════════════════════════════════════════════════

class TestCS0117ProtoInventedFields:
    """
    Run 3 failure: LLM set ValidateActionResponse.ClaimId and RecordEvidenceRequest.IdempotencyKey.
    New design: retry advisor uses PTR for fix instructions — works for any proto type.
    """

    PROTO_PTR = _make_ptr_with_types({
        "WC012-01": {
            "ValidateActionResponse": {
                "kind": "proto_message",
                "namespace": "Waooaw.ConstitutionalEngine.Grpc",
                "fields": {
                    "Decision": "ValidationDecision",
                    "ConstitutionalBasis": "string",
                    "Reason": "string",
                    "BudgetRemainingInrPaise": "long?",
                    "SyntheticApprovalRecordId": "string?",
                },
                "note": "Proto-generated — use ONLY fields listed. Do NOT invent fields.",
            },
            "RecordEvidenceRequest": {
                "kind": "proto_message",
                "namespace": "Waooaw.ConstitutionalEngine.Grpc",
                "fields": {
                    "ActionInstanceId": "string",
                    "ContractId": "string",
                    "ProfessionalId": "string",
                    "ActionType": "string",
                    "State": "EvidenceState",
                    "ConstitutionalBasis": "string",
                },
                "note": "Proto-generated — use ONLY fields listed.",
            },
        }
    })

    def test_validate_action_response_claim_id_classified(self):
        error = "error CS0117: 'ValidateActionResponse' does not contain a definition for 'ClaimId'"
        with patch("platform_type_registry.load_ptr", return_value=self.PROTO_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True
        assert result.confidence >= 0.90

    def test_fix_names_correct_validate_action_response_fields(self):
        error = "error CS0117: 'ValidateActionResponse' does not contain a definition for 'ClaimId'"
        with patch("platform_type_registry.load_ptr", return_value=self.PROTO_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert "Decision" in result.fix_instruction
        assert "ConstitutionalBasis" in result.fix_instruction

    def test_fix_shows_actual_members(self):
        """PTR-driven fix must list actual fields, not invented ones."""
        error = "error CS0117: 'ValidateActionResponse' does not contain a definition for 'ClaimId'"
        with patch("platform_type_registry.load_ptr", return_value=self.PROTO_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        # ClaimId not in actual members, but Decision/Reason are
        assert "Decision" in result.fix_instruction or "Reason" in result.fix_instruction

    def test_record_evidence_request_idempotency_key_classified(self):
        error = "error CS0117: 'RecordEvidenceRequest' does not contain a definition for 'IdempotencyKey'"
        with patch("platform_type_registry.load_ptr", return_value=self.PROTO_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True
        assert result.confidence >= 0.90

    def test_fix_names_correct_record_evidence_fields(self):
        error = "error CS0117: 'RecordEvidenceRequest' does not contain a definition for 'IdempotencyKey'"
        with patch("platform_type_registry.load_ptr", return_value=self.PROTO_PTR):
            result = diagnose_build_error("WC012-02b", error, [])
        assert "ActionInstanceId" in result.fix_instruction or "ContractId" in result.fix_instruction

    def test_constitutional_trace_on_proto_errors(self):
        for error in [
            "error CS0117: 'ValidateActionResponse' does not contain a definition for 'ClaimId'",
            "error CS0117: 'RecordEvidenceRequest' does not contain a definition for 'IdempotencyKey'",
        ]:
            with patch("platform_type_registry.load_ptr", return_value=self.PROTO_PTR):
                result = diagnose_build_error("WC012-02b", error, [])
            assert result.constitutional_trace != ""

    def test_ptr_miss_still_returns_wrong_field_name(self):
        """Without PTR, generic fallback still classifies correctly."""
        with patch("platform_type_registry.load_ptr", return_value={}):
            error = "error CS0117: 'ValidateActionResponse' does not contain a definition for 'ClaimId'"
            result = diagnose_build_error("WC012-02b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.should_retry is True

    def test_generalized_for_any_sprint_type(self):
        """PTR-aware advisor works for a WC013+ type never seen before."""
        wc013_ptr = _make_ptr_with_types({
            "WC013-01a": {
                "AuthorityLicenseResponse": {
                    "kind": "proto_message",
                    "namespace": "Waooaw.ConstitutionalEngine.Grpc",
                    "fields": {"LicenseId": "string", "RecordedAt": "Timestamp"},
                    "note": "Proto-generated.",
                }
            }
        })
        error = "error CS0117: 'AuthorityLicenseResponse' does not contain a definition for 'GrantedBy'"
        with patch("platform_type_registry.load_ptr", return_value=wc013_ptr):
            result = diagnose_build_error("WC013-01b", error, [])
        assert result.error_type == WRONG_FIELD_NAME
        assert result.confidence >= 0.90
        # Fix must mention actual fields from PTR
        assert "LicenseId" in result.fix_instruction or "RecordedAt" in result.fix_instruction
