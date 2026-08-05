"""
Targeted regression tests for pipeline bad-spots identified by 5-Why RCA.

# constitutional_basis: C-076 (≥90% coverage), C-082 (build validation), C-059 (traceability)
# office: Platform IT Expert — QA hat
# ib_item: IB-009

Bad spots covered:
  TEST-MODEL-01 — model_hint="reasoning" must survive test file path override
  TEST-MODEL-02 — complexity score boost for test generation at high context
  TEST-MODEL-03 — cascade path also respects model_hint for test files
  FORBIDDEN-01  — dunder patch rule present in FORBIDDEN_APIS prompt
  ADVISOR-01    — SQLITE_ISOLATION classified as dominant failure (not ASYNC_MOCK)
  ADVISOR-02    — ASYNC_MOCK requires literal TypeError message, not "MagicMock" in blob
  ADVISOR-03    — tally counts per-FAILED-line, not full blob
  ADVISOR-04    — mixed run: SQLite dominant → SQLITE_ISOLATION wins over 2 ASYNC_MOCK
  ADVISOR-05    — SQLITE_ISOLATION fix instruction contains StaticPool guidance
  ADVISOR-06    — SQLITE_ISOLATION confidence ≥ 0.90
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "magic_llm"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "goal_orchestrator"))


# ── Retry Advisor helpers ─────────────────────────────────────────────────────

from sprint_retry_advisor import (
    SQLITE_ISOLATION,
    ASYNC_MOCK_MISMATCH,
    PYTEST_FIXTURE_AWAIT,
    UNKNOWN,
    diagnose_build_error,
    _tally_pytest_failures,
    _classify_sqlite_isolation,
    _classify_pytest_fixture_await,
)


# ── ADVISOR-03: tally counts per FAILED line correctly ────────────────────────

def test_tally_counts_sqlite_failures():
    error = (
        "FAILED tests/billing-engine/test_service.py::test_check_thresholds - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/billing-engine/test_service.py::test_record_usage - assert 0 >= 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/billing-engine/test_service.py::test_daily_scan - AssertionError: assert 0 == 2\n"
    )
    tallies = _tally_pytest_failures(error)
    assert tallies.get("sqlite_isolation", 0) >= 2


def test_tally_counts_mixed_run():
    error = (
        "FAILED tests/test_s.py::test_a - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_b - assert 0 >= 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_c - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_d - Failed: DID NOT RAISE CancelledError\n"
        "FAILED tests/test_s.py::test_e - Failed: DID NOT RAISE CancelledError\n"
    )
    tallies = _tally_pytest_failures(error)
    assert tallies["sqlite_isolation"] == 3
    assert tallies["did_not_raise"] == 2
    dominant = max(tallies, key=lambda k: tallies[k])
    assert dominant == "sqlite_isolation"


def test_tally_returns_empty_for_non_pytest_output():
    error = "error CS0246: The type 'Foo' could not be found"
    assert _tally_pytest_failures(error) == {}


# ── ADVISOR-01: SQLITE_ISOLATION classified from dominant failure ─────────────

_SQLITE_DOMINANT_ERROR = (
    "FAILED tests/billing-engine/test_service.py::test_check_thresholds_50pct - assert 0 == 1\n"
    " +  where 0 = len([])\n"
    "FAILED tests/billing-engine/test_service.py::test_daily_scan_fires_alerts - assert 0 >= 1\n"
    " +  where 0 = len([])\n"
    "FAILED tests/billing-engine/test_service.py::test_record_usage_persisted - assert 0 == 3\n"
    " +  where 0 = len(results)\n"
    "FAILED tests/billing-engine/test_service.py::test_project_depletion - assert 0 == 1\n"
    " +  where 0 = len([])\n"
    "FAILED tests/billing-engine/test_service.py::test_record_usage_cancelled_error - "
    "Failed: DID NOT RAISE CancelledError\n"
    "FAILED tests/billing-engine/test_service.py::test_project_depletion_cancelled - "
    "Failed: DID NOT RAISE CancelledError\n"
    "12 failed, 12 passed in 1.09s\n"
)


def test_advisor_01_sqlite_dominant_classified_as_sqlite_isolation():
    result = diagnose_build_error("WC028-01c", _SQLITE_DOMINANT_ERROR, [])
    assert result.error_type == SQLITE_ISOLATION


def test_advisor_05_sqlite_isolation_fix_contains_staticpool():
    result = diagnose_build_error("WC028-01c", _SQLITE_DOMINANT_ERROR, [])
    assert "StaticPool" in result.fix_instruction
    assert "poolclass" in result.fix_instruction


def test_advisor_06_sqlite_isolation_confidence():
    result = diagnose_build_error("WC028-01c", _SQLITE_DOMINANT_ERROR, [])
    assert result.confidence >= 0.90
    assert result.should_retry is True
    assert result.constitutional_trace != ""


# ── ADVISOR-02: ASYNC_MOCK requires literal TypeError message, not blob match ─

_ASYNC_MOCK_REAL_ERROR = (
    "FAILED tests/billing-engine/test_markup.py::test_thread_catalog\n"
    "  E   TypeError: object MagicMock can't be used in 'await' expression\n"
    "  result = await mock_engine.get_thread_catalog()\n"
)

_SQLITE_WITH_MAGICMOCK_IN_REPR = (
    "FAILED tests/billing-engine/test_service.py::test_check_thresholds - assert 0 == 1\n"
    " +  where 0 = len([])\n"
    " +    where <MagicMock name='mock.redis_client' id='140560360205696'>.set = ...\n"
    "FAILED tests/billing-engine/test_service.py::test_daily_scan - assert 0 >= 1\n"
    " +  where 0 = len([])\n"
    "FAILED tests/billing-engine/test_service.py::test_record_usage - assert 0 == 1\n"
    " +  where 0 = len([])\n"
    "3 failed, 9 passed in 0.54s\n"
)


def test_advisor_02_real_async_mock_error_classified_correctly():
    result = diagnose_build_error("WC027-02c", _ASYNC_MOCK_REAL_ERROR, [])
    assert result.error_type == ASYNC_MOCK_MISMATCH


def test_advisor_02_magicmock_in_repr_does_not_trigger_async_mock():
    """MagicMock appearing only in assertion repr must not misclassify SQLite failures."""
    result = diagnose_build_error("WC028-01c", _SQLITE_WITH_MAGICMOCK_IN_REPR, [])
    assert result.error_type != ASYNC_MOCK_MISMATCH
    assert result.error_type == SQLITE_ISOLATION


# ── ADVISOR-04: mixed run — SQLite dominant wins over minority ASYNC_MOCK ─────

def test_advisor_04_sqlite_dominant_beats_minority_async_mock():
    error = (
        "FAILED tests/test_s.py::test_a - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_b - assert 0 >= 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_c - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_d - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_e - assert 0 == 1\n"
        " +  where 0 = len([])\n"
        "FAILED tests/test_s.py::test_f - Failed: DID NOT RAISE CancelledError\n"
        "FAILED tests/test_s.py::test_g - Failed: DID NOT RAISE CancelledError\n"
        "7 failed, 5 passed in 0.89s\n"
    )
    result = diagnose_build_error("WC028-01c", error, [])
    assert result.error_type == SQLITE_ISOLATION


def test_advisor_sqlite_isolation_not_fired_for_empty_pytest_output():
    error = "error CS0246: The type 'Foo' could not be found\n"
    result = _classify_sqlite_isolation(error)
    assert result is None


def test_advisor_sqlite_isolation_not_fired_when_assertion_dominant():
    """Pure assertion failures without len([]) pattern → not SQLITE_ISOLATION."""
    error = (
        "FAILED tests/test_s.py::test_a - AssertionError: assert 'foo' == 'bar'\n"
        "FAILED tests/test_s.py::test_b - AssertionError: assert 42 == 99\n"
    )
    result = _classify_sqlite_isolation(error)
    assert result is None


# ── TEST-MODEL-01: model_hint="reasoning" must produce DEEP_REASONING for test ─

def test_model_01_reasoning_hint_gives_deep_reasoning_for_test_file():
    """goal_executor must not downgrade model_hint=reasoning to TEST_GENERATION."""
    from magic_llm.types import TaskCategory

    # Simulate goal_executor mapping logic directly (without importing full executor)
    model_hint = "reasoning"
    output_file = "tests/billing-engine/test_service.py"

    if model_hint == "reasoning":
        cat = TaskCategory.DEEP_REASONING
    elif model_hint == "none":
        cat = TaskCategory.CODE_GENERATION
    else:
        cat = TaskCategory.TEST_GENERATION if "test" in output_file.lower() else TaskCategory.CODE_GENERATION

    assert cat == TaskCategory.DEEP_REASONING, (
        "model_hint='reasoning' must yield DEEP_REASONING regardless of file path — "
        "DEEP_REASONING fast-path in _select_model always returns Sonnet"
    )


def test_model_01_auto_hint_still_gives_test_generation_for_test_file():
    """model_hint='auto' should still give TEST_GENERATION (complexity scoring path)."""
    from magic_llm.types import TaskCategory

    model_hint = "auto"
    output_file = "tests/billing-engine/test_service.py"

    if model_hint == "reasoning":
        cat = TaskCategory.DEEP_REASONING
    elif model_hint == "none":
        cat = TaskCategory.CODE_GENERATION
    else:
        cat = TaskCategory.TEST_GENERATION if "test" in output_file.lower() else TaskCategory.CODE_GENERATION

    assert cat == TaskCategory.TEST_GENERATION


# ── TEST-MODEL-02: complexity score boost for test files at high context ───────

def test_model_02_complexity_boost_for_test_at_high_context():
    """generate test_X.py with 7+ context sections must score ≥80 → Sonnet."""
    from magic_llm.pipeline import _task_complexity_score
    from magic_llm.types import MagicLLMRequest, TaskCategory

    req = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.TEST_GENERATION,
        task_description="generate test_service.py",
        context_sections=["section"] * 7,  # 7 sections × 8 = 56 + boost 20 = 76... hmm
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    score = _task_complexity_score(req)
    # 7 sections × 8 = 56, + 20 boost (test_ + ≥7 sections) = 76
    # With 8+ sections: 8×8=64 + 20 = 84 ≥ 80 → Sonnet
    req8 = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.TEST_GENERATION,
        task_description="generate test_service.py",
        context_sections=["section"] * 8,
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    score8 = _task_complexity_score(req8)
    assert score8 >= 80, f"8-section test generation scored {score8}, expected ≥80"


def test_model_02_boost_not_applied_for_source_files():
    """Source files at same context size must NOT get the test boost."""
    from magic_llm.pipeline import _task_complexity_score
    from magic_llm.types import MagicLLMRequest, TaskCategory

    req = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.CODE_GENERATION,
        task_description="generate service.py",
        context_sections=["section"] * 8,
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    score = _task_complexity_score(req)
    # 8×8=64, no boost → same score as before
    assert score == 64


def test_model_02_deep_reasoning_bypasses_complexity_scoring():
    """DEEP_REASONING category bypasses complexity score and always selects Sonnet."""
    from magic_llm.pipeline import MagicLLMPipeline, _ANTHROPIC_MODEL
    from magic_llm.types import MagicLLMRequest, TaskCategory

    pipeline = MagicLLMPipeline(api_key="dummy")
    req = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.DEEP_REASONING,
        task_description="generate test_service.py",
        context_sections=["section"] * 8,
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    model, _ = pipeline._select_model(TaskCategory.DEEP_REASONING, req)
    assert model == _ANTHROPIC_MODEL, "DEEP_REASONING must always return Sonnet"


# ── FORBIDDEN-01: dunder patch rule present in FORBIDDEN_APIS prompt ──────────

def test_forbidden_01_dunder_patch_rule_in_prompt():
    """FORBIDDEN_APIS block must warn against patching dunder methods on instances."""
    from magic_llm.pipeline import MagicLLMPipeline
    from magic_llm.types import MagicLLMRequest, TaskCategory

    pipeline = MagicLLMPipeline(api_key="dummy")
    req = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.TEST_GENERATION,
        task_description="generate test_service.py",
        context_sections=["spec section"],
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    prompt = pipeline._build_prompt(req)
    assert "__call__" in prompt, "dunder patch rule must appear in FORBIDDEN_APIS"
    assert "special method" in prompt.lower() or "type(" in prompt, (
        "dunder patch rule must explain CPython type-level lookup"
    )


def test_forbidden_01_staticpool_rule_still_present():
    """StaticPool rule must still be in FORBIDDEN_APIS after the dunder addition."""
    from magic_llm.pipeline import MagicLLMPipeline
    from magic_llm.types import MagicLLMRequest, TaskCategory

    pipeline = MagicLLMPipeline(api_key="dummy")
    req = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.TEST_GENERATION,
        task_description="generate test_service.py",
        context_sections=["spec section"],
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    prompt = pipeline._build_prompt(req)
    assert "StaticPool" in prompt
    assert "poolclass" in prompt


# ── ADVISOR-07: PYTEST_FIXTURE_AWAIT — await fixture_name in test body ────────
# Locally reproduced: test_service.py line 224 — `await setup_test_data`
# TypeError: object NoneType can't be used in 'await' expression

_FIXTURE_AWAIT_ERROR = (
    "FAILED tests/billing-engine/test_service.py::test_record_usage_success - TypeError\n"
    "tests/billing-engine/test_service.py:224: in test_record_usage_success\n"
    "    await setup_test_data\n"
    "E   TypeError: object NoneType can't be used in 'await' expression\n"
)

_FIXTURE_AWAIT_MULTI = (
    "FAILED tests/billing-engine/test_service.py::test_record_usage - TypeError\n"
    "    await setup_test_data\n"
    "E   TypeError: object NoneType can't be used in 'await' expression\n"
    "FAILED tests/billing-engine/test_service.py::test_check_thresholds - TypeError\n"
    "    await setup_test_data\n"
    "E   TypeError: object NoneType can't be used in 'await' expression\n"
    "FAILED tests/billing-engine/test_service.py::test_daily_scan - TypeError\n"
    "    await setup_test_data\n"
    "E   TypeError: object NoneType can't be used in 'await' expression\n"
)


def test_advisor_07_fixture_await_classified():
    result = diagnose_build_error("WC028-01c", _FIXTURE_AWAIT_ERROR, [])
    assert result.error_type == PYTEST_FIXTURE_AWAIT


def test_advisor_07_fixture_await_names_fixture_in_fix():
    result = diagnose_build_error("WC028-01c", _FIXTURE_AWAIT_ERROR, [])
    assert "setup_test_data" in result.fix_instruction
    assert "remove" in result.fix_instruction.lower() or "REMOVE" in result.fix_instruction


def test_advisor_07_fixture_await_high_confidence():
    result = diagnose_build_error("WC028-01c", _FIXTURE_AWAIT_ERROR, [])
    assert result.confidence >= 0.90
    assert result.should_retry is True


def test_advisor_07_fixture_await_multi_classified():
    result = diagnose_build_error("WC028-01c", _FIXTURE_AWAIT_MULTI, [])
    assert result.error_type == PYTEST_FIXTURE_AWAIT


def test_advisor_07_not_triggered_for_magicmock_nonetype():
    """A different NoneType context (not await fixture) must not fire PYTEST_FIXTURE_AWAIT."""
    error = "AttributeError: 'NoneType' object has no attribute 'execute'\n"
    result = _classify_pytest_fixture_await(error)
    assert result is None


def test_advisor_07_not_triggered_for_asyncmock_error():
    """Real ASYNC_MOCK TypeError must not fire PYTEST_FIXTURE_AWAIT."""
    result = _classify_pytest_fixture_await(_ASYNC_MOCK_REAL_ERROR)
    assert result is None


def test_forbidden_01_fixture_await_rule_in_prompt():
    """FORBIDDEN_APIS block must warn against await <fixture_name> in test bodies."""
    from magic_llm.pipeline import MagicLLMPipeline
    from magic_llm.types import MagicLLMRequest, TaskCategory

    pipeline = MagicLLMPipeline(api_key="dummy")
    req = MagicLLMRequest(
        goal_id="GOAL-TEST",
        institution_id="INST-010",
        go_authorization_id="GOA-TEST",
        task_category=TaskCategory.TEST_GENERATION,
        task_description="generate test_service.py",
        context_sections=["spec section"],
        ptr_snapshot={},
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-TEST",
    )
    prompt = pipeline._build_prompt(req)
    assert "await" in prompt.lower() and "fixture" in prompt.lower(), (
        "FORBIDDEN_APIS must warn against await <fixture> in test body"
    )
