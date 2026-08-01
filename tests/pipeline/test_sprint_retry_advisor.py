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
    EXTEND_NOT_REPLACE, WRONG_NAMESPACE, WRONG_FIELD_NAME, MISSING_USING, UNKNOWN,
    HYPOTHESIS_HEALTH_CHECK, HYPOTHESIS_FIXTURE_PARAM, DATETIME_UTCNOW,
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
    """CS0117: Claude invented a property name → WRONG_FIELD_NAME with actionable fix."""
    error = (
        "error CS0117: 'EmergencyStopResponse' does not contain a definition for 'StopConfirmed'"
    )

    result = diagnose_build_error("WC012-04", error, [])

    assert result.error_type == WRONG_FIELD_NAME
    assert result.should_retry is True
    # PTR-verified path gives class name or property guidance; general path gives constructor/empty advice
    assert (
        "EmergencyStopResponse".lower() in result.fix_instruction.lower()
        or "constructor" in result.fix_instruction.lower()
        or "empty" in result.fix_instruction.lower()
        or "property" in result.fix_instruction.lower()
    )


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


# ─── CCT-SRA-06: HYPOTHESIS_HEALTH_CHECK ─────────────────────────────────────

def test_cct_sra_06_hypothesis_health_check_classified():
    """CCT-SRA-06: hypothesis FailedHealthCheck → HYPOTHESIS_HEALTH_CHECK with fixture guidance."""
    error = (
        "hypothesis.errors.FailedHealthCheck: "
        "'tests/billing-engine/test_markup.py::test_derive_price_formula_correctness_property' "
        "uses a function-scoped fixture 'mock_bundle_engine'. "
        "If you are confident that your test will work correctly even though "
        "the fixture is not reset between generated inputs, you can suppress this "
        "health check with @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])."
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert result.error_type == HYPOTHESIS_HEALTH_CHECK
    assert result.should_retry is True
    assert result.confidence >= 0.90
    assert "suppress_health_check" in result.fix_instruction
    assert result.constitutional_trace != ""


def test_cct_sra_06_hypothesis_fix_mentions_settings_decorator():
    """CCT-SRA-06: fix instruction must tell LLM to use @settings decorator."""
    error = (
        "hypothesis.errors.FailedHealthCheck: test uses a function_scoped_fixture 'mock_engine'. "
        "suppress this health check with @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])"
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert result.error_type == HYPOTHESIS_HEALTH_CHECK
    assert "@settings" in result.fix_instruction or "settings" in result.fix_instruction.lower()
    assert "HealthCheck" in result.fix_instruction


# ─── CCT-SRA-07: DATETIME_UTCNOW ─────────────────────────────────────────────

def test_cct_sra_07_datetime_utcnow_deprecation_classified():
    """CCT-SRA-07: datetime.utcnow() DeprecationWarning → DATETIME_UTCNOW with fix."""
    error = (
        "DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal "
        "in a future version. Use timezone-aware objects to represent datetimes in UTC: "
        "datetime.datetime.now(datetime.UTC). "
        "tests/billing-engine/test_markup.py:80: DeprecationWarning"
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert result.error_type == DATETIME_UTCNOW
    assert result.should_retry is True
    assert result.confidence >= 0.90
    assert "timezone" in result.fix_instruction.lower() or "utc" in result.fix_instruction.lower()
    assert result.constitutional_trace != ""


def test_cct_sra_07_datetime_fix_mentions_replacement():
    """CCT-SRA-07: fix instruction must tell LLM to use datetime.now(timezone.utc)."""
    error = (
        "E   DeprecationWarning: datetime.datetime.utcnow() is deprecated\n"
        "tests/billing-engine/test_markup.py:80: DeprecationWarning"
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert result.error_type == DATETIME_UTCNOW
    fix = result.fix_instruction.lower()
    assert "now" in fix and "utc" in fix  # must reference datetime.now(timezone.utc)


def test_cct_sra_07_dtz003_ruff_classified():
    """CCT-SRA-07: ruff DTZ003 flag on utcnow also classifies as DATETIME_UTCNOW."""
    error = (
        "src/billing-engine/markup/router.py:12:20: DTZ003 Use of `datetime.utcnow()` is not allowed\n"
        "Found 1 error."
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert result.error_type == DATETIME_UTCNOW
    assert result.should_retry is True


# ── CCT-SRA-09: async @given param treated as pytest fixture ──────────────────

def test_cct_sra_09_hypothesis_fixture_param_classified():
    """CCT-SRA-09: fixture 'X' not found when X is a @given param in async test."""
    error = (
        "ERRORS\n"
        "tests/billing-engine/test_markup.py::test_validate_price_property_agent_type_invariant\n"
        "  fixture 'agent_type' not found\n"
        "    available fixtures: tmp_path, tmp_path_factory, tmpdir, tmpdir_factory, "
        "unused_tcp_port, capfd, capsys, mock_bundle_engine\n"
        "    use 'pytest --fixtures [testpath]' for help on them.\n"
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert result.error_type == HYPOTHESIS_FIXTURE_PARAM
    assert result.should_retry is True


def test_cct_sra_09_hypothesis_fixture_param_extracts_name():
    """CCT-SRA-09: fix instruction mentions the missing fixture name."""
    error = (
        "fixture 'agent_type' not found\n"
        "    available fixtures: tmp_path, capfd\n"
        "    use 'pytest --fixtures [testpath]' for help on them.\n"
    )

    result = diagnose_build_error("WC027-02c", error, [])

    assert "agent_type" in result.fix_instruction


def test_cct_sra_09_hypothesis_fixture_param_fix_mentions_async_given():
    """CCT-SRA-09: fix instruction must guide LLM about async @given pattern."""
    error = (
        "fixture 'val' not found\n"
        "    available fixtures: mock_engine\n"
        "    use 'pytest --fixtures [testpath]' for help.\n"
    )

    result = diagnose_build_error("WC027-02c", error, [])

    fix = result.fix_instruction.lower()
    assert "@given" in result.fix_instruction
    assert "async" in fix or "pytestasyncio" in fix.replace("-", "")


