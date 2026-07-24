"""
Tests for sprint_retry_advisor.py — CCT-SRA-01 through CCT-SRA-05

# Implements: architecture/reference/pipeline/sprint-retry-advisor.md
# constitutional_basis: C-076 (≥90% coverage), C-082 (build validation), C-059 (traceability)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from scripts.sprint_retry_advisor import (
    diagnose_build_error,
    EXTEND_NOT_REPLACE, WRONG_NAMESPACE, WRONG_FIELD_NAME, MISSING_USING, UNKNOWN
)

import pytest


# ─── CCT-SRA-01: CS0101 → EXTEND_NOT_REPLACE ──────────────────────────────────

def test_cct_sra_01_cs0101_duplicate_class():
    """CCT-SRA-01: CS0101 produces EXTEND_NOT_REPLACE with file name and DO NOT regenerate."""
    error = (
        "error CS0101: The namespace 'Waooaw.ConstitutionalEngine.Evaluators' "
        "already contains a definition for 'C041ToolAuthorizationEvaluator' "
        "[/src/constitutional-engine/constitutional-engine.csproj]"
    )
    written = ["src/constitutional-engine/Evaluators/C041_ToolAuthorizationEvaluator.cs"]

    result = diagnose_build_error("WC012-03", error, written)

    assert result.error_type == EXTEND_NOT_REPLACE
    assert result.should_retry is True
    assert result.confidence >= 0.90
    assert "DO NOT" in result.fix_instruction.upper() or "MUST NOT" in result.fix_instruction.upper()
    assert "C041" in result.fix_instruction or "duplicate" in result.fix_instruction.lower()
    assert result.constitutional_trace != ""  # CCT-SRA-04: must cite a claim


def test_cct_sra_01_no_llm_for_cs0101():
    """CCT-SRA-05: CS0101 is classified by rule — no LLM call needed."""
    error = "error CS0101: The namespace 'Waooaw.ConstitutionalEngine.Data' already contains a definition for 'EvidenceRecord'"
    # If this were to call the LLM, it would fail without an API key in test env
    # The fact that it returns a result without raising means rule-based path was taken
    os.environ.pop("ANTHROPIC_API_KEY", None)  # ensure no API key
    result = diagnose_build_error("WC012-03", error, [])
    assert result.error_type == EXTEND_NOT_REPLACE
    assert result.should_retry is True  # rule-based, no API needed


# ─── CCT-SRA-02: CS0246 + wrong namespace → WRONG_NAMESPACE ──────────────────

def test_cct_sra_02_wrong_namespace_protos():
    """CCT-SRA-02: CS0246 with Protos namespace → WRONG_NAMESPACE with correct Grpc namespace."""
    error = (
        "error CS0246: The type or namespace name 'Protos' does not exist in the "
        "namespace 'Waooaw.ConstitutionalEngine' (are you missing an assembly reference?)"
    )

    result = diagnose_build_error("WC012-03", error, [])

    assert result.error_type == WRONG_NAMESPACE
    assert result.should_retry is True
    assert "Waooaw.ConstitutionalEngine.Grpc" in result.fix_instruction
    assert result.confidence >= 0.85


def test_cct_sra_02_constitutional_service_not_found():
    """CS0246 for ConstitutionalService → also WRONG_NAMESPACE (lives in Grpc)."""
    error = (
        "error CS0246: The type or namespace name 'ConstitutionalService' could not "
        "be found (are you missing a using directive or an assembly reference?)"
    )

    result = diagnose_build_error("WC012-03", error, [])

    assert result.error_type == WRONG_NAMESPACE
    assert "Grpc" in result.fix_instruction


# ─── CS0117: wrong field name → WRONG_FIELD_NAME ─────────────────────────────

def test_wrong_field_name_invented_property():
    """CS0117: Claude invented a property name → WRONG_FIELD_NAME with empty constructor advice."""
    error = (
        "error CS0117: 'EmergencyStopResponse' does not contain a definition for 'StopConfirmed'"
    )

    result = diagnose_build_error("WC012-04", error, [])

    assert result.error_type == WRONG_FIELD_NAME
    assert result.should_retry is True
    assert "constructor" in result.fix_instruction.lower() or "empty" in result.fix_instruction.lower()


# ─── CCT-SRA-03: UNKNOWN with low confidence → should_retry=False ────────────

def test_cct_sra_03_unknown_no_retry():
    """CCT-SRA-03: Error that matches no known pattern → UNKNOWN → should_retry=False."""
    error = "error CS8370: Feature 'file-scoped namespace' is not available in C# 9.0"

    os.environ.pop("ANTHROPIC_API_KEY", None)  # No API key → LLM path returns confidence=0.0

    result = diagnose_build_error("WC012-02", error, [])

    assert result.error_type == UNKNOWN
    assert result.should_retry is False
    assert result.confidence < 0.6


# ─── CCT-SRA-04: every diagnosis has constitutional_trace ─────────────────────

def test_cct_sra_04_all_known_patterns_have_trace():
    """CCT-SRA-04: Every known classification includes a constitutional_trace."""
    test_cases = [
        ("error CS0101: The namespace 'X' already contains a definition for 'Y'", []),
        ("error CS0246: The type or namespace name 'Protos' does not exist in the namespace 'Waooaw.ConstitutionalEngine'", []),
        ("error CS0117: 'EmergencyStopResponse' does not contain a definition for 'StopConfirmed'", []),
    ]

    os.environ.pop("ANTHROPIC_API_KEY", None)

    for error, files in test_cases:
        result = diagnose_build_error("WC012-TEST", error, files)
        if result.error_type != UNKNOWN:
            assert result.constitutional_trace != "", \
                f"Missing constitutional_trace for error_type={result.error_type}"


# ─── Missing using directive ──────────────────────────────────────────────────

def test_missing_using_grpc_core():
    """CS0246 for ServerCallContext → MISSING_USING with Grpc.Core namespace."""
    error = (
        "error CS0246: The type or namespace name 'ServerCallContext' could not be found "
        "(are you missing a using directive or an assembly reference?)"
    )

    result = diagnose_build_error("WC012-02", error, [])

    assert result.error_type == MISSING_USING
    assert "Grpc.Core" in result.fix_instruction
    assert result.should_retry is True


# ─── Multiple errors in one build output ──────────────────────────────────────

def test_mixed_errors_picks_highest_priority():
    """When both CS0101 and CS0246 appear, CS0101 (most actionable) is prioritized."""
    error = (
        "error CS0101: The namespace 'X' already contains a definition for 'EvidenceRecord'\n"
        "error CS0246: The type 'Protos' does not exist in namespace 'Waooaw.ConstitutionalEngine'"
    )

    result = diagnose_build_error("WC012-03", error, [])

    # CS0101 is checked first — EXTEND_NOT_REPLACE is more specific
    assert result.error_type == EXTEND_NOT_REPLACE
