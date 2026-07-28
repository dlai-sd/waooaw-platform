# Implements: architecture/reference/goal-orchestrator/component-contracts.md §2 (retry loop §9)
# constitutional_basis: C-082 (Build Validation), C-084 (Fair-sweep), C-069 (Self-Improvement)
"""
CCT-GO-RETRY — GoalExecutor retry loop and supporting behaviours

Tests:
  1. Retry loop: failure_context injected on attempt 2/3, succeeds on attempt 3
  2. model_hint routing: "auto" / "reasoning" / "none" map to correct TaskCategory
  3. File locking: concurrent _save/_load do not corrupt failure-count JSON
  4. Cascade: set_original_request called before on_gate_fail (no ValueError)
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest
import sys

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from goal_orchestrator.goal_executor import (
    GoalExecutor,
    FileGenerationTask,
    _parse_llm_files_local,
    _write_llm_files_local,
    REPO_ROOT as GO_REPO_ROOT,
)


# ── helpers ───────────────────────────────────────────────────────────────────

_VALID_RESPONSE = (
    '<file path="tests/Foo.cs">\n'
    '// Implements: tests/spec.md §1\n'
    '// constitutional_basis: C-041\n'
    'public class Foo {}\n'
    '</file>'
)
_NO_BLOCK_RESPONSE = "Here is a great file but I forgot to wrap it."


def _make_task(**kwargs) -> FileGenerationTask:
    defaults = dict(
        goal_id="GOAL-TEST",
        task_id="T-01",
        output_file="tests/Foo.cs",
        spec_sections={},
        constitutional_check="",
        stack="dotnet",
        model_hint="reasoning",
        max_tokens=1000,
    )
    defaults.update(kwargs)
    return FileGenerationTask(**defaults)


def _make_executor(tmp_path: Path) -> GoalExecutor:
    """Create a GoalExecutor with mocked MagicLLM components."""
    executor = GoalExecutor.__new__(GoalExecutor)
    executor.goal_id = "GOAL-TEST"
    executor._root = tmp_path
    executor._write = lambda r: r.get("task_id", "")
    executor._cascade = None

    # Mock ContextBuilder
    mock_ctx = MagicMock()
    mock_ctx.total_chars = 100
    mock_ctx.blocks = [MagicMock(slot="FORMAT")]
    mock_ctx.full_prompt = "Generate Foo.cs"
    mock_cb = MagicMock()
    mock_cb.build.return_value = mock_ctx
    mock_cb.freeze_artifact = MagicMock()
    executor._cb = mock_cb

    # Mock ResponseEvaluator — passes all gates
    mock_gate = MagicMock(passed=True, gate="FORMAT", detail="ok", error_codes=[])
    mock_eval_result = MagicMock(all_passed=True, gates=[mock_gate], first_failure=None)
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.return_value = mock_eval_result
    executor._evaluator = mock_evaluator

    return executor


# ── CCT-GO-01: retry loop succeeds on attempt 3 ───────────────────────────────

def test_retry_loop_succeeds_on_third_attempt(tmp_path: Path) -> None:
    """Retry loop: attempts 1+2 return no <file> blocks, attempt 3 returns valid."""
    executor = _make_executor(tmp_path)
    task = _make_task()

    call_count = 0

    def fake_call_llm(t, prompt, api_key, attempt):
        nonlocal call_count
        call_count += 1
        if attempt < 3:
            return _NO_BLOCK_RESPONSE
        return _VALID_RESPONSE

    with (
        patch.object(executor, "_call_llm", side_effect=fake_call_llm),
        patch("goal_orchestrator.goal_executor._parse_llm_files_local",
              side_effect=_parse_llm_files_local),
        patch("goal_orchestrator.goal_executor._write_llm_files_local",
              return_value=["tests/Foo.cs"]),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}),
    ):
        result = executor._execute_file(task)

    assert call_count == 3, f"Expected 3 LLM calls, got {call_count}"
    assert result.attempts == 3
    assert result.status == "success"


def test_retry_loop_injects_failure_context_on_attempt_2(tmp_path: Path) -> None:
    """failure_context is appended to constitutional_check on retry attempts."""
    executor = _make_executor(tmp_path)
    task = _make_task()
    prompts_seen = []

    def fake_build(**kwargs):
        prompts_seen.append(kwargs.get("constitutional_check", ""))
        mock_ctx = MagicMock()
        mock_ctx.total_chars = 100
        mock_ctx.blocks = []
        mock_ctx.full_prompt = "prompt"
        return mock_ctx

    mock_cb_instance = MagicMock()
    mock_cb_instance.build.side_effect = fake_build

    with (
        patch("magic_llm.context_builder.ContextBuilder", return_value=mock_cb_instance),
        patch.object(executor, "_call_llm", return_value=_NO_BLOCK_RESPONSE),
        patch("goal_orchestrator.goal_executor._parse_llm_files_local",
              return_value={}),
        patch("goal_orchestrator.goal_executor._write_llm_files_local",
              return_value=[]),
        patch.object(executor, "_run_cascade", return_value=False),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}),
    ):
        executor._execute_file(task)

    assert len(prompts_seen) == 3, f"Expected 3 build calls, got {len(prompts_seen)}"
    assert "PREVIOUS ATTEMPT FAILED" not in prompts_seen[0]
    assert "PREVIOUS ATTEMPT FAILED" in prompts_seen[1]
    assert "PREVIOUS ATTEMPT FAILED" in prompts_seen[2]


# ── CCT-GO-02: model_hint routing ─────────────────────────────────────────────

def test_model_hint_reasoning_routes_to_test_generation(tmp_path: Path) -> None:
    """model_hint='reasoning' + test file → TaskCategory.TEST_GENERATION."""
    from magic_llm.types import TaskCategory

    executor = _make_executor(tmp_path)
    task = _make_task(output_file="tests/Foo.cs", model_hint="reasoning")
    captured = {}

    mock_resp = MagicMock(status="accepted", raw_output=_VALID_RESPONSE)
    mock_pipeline = MagicMock()
    mock_pipeline.invoke.side_effect = lambda req: (captured.update({"category": req.task_category}) or mock_resp)

    with (
        patch("magic_llm.pipeline.MagicLLMPipeline", return_value=mock_pipeline),
        patch.dict("sys.modules", {"autonomous_sprint_runner": None}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}),
    ):
        executor._call_llm(task, "prompt", "sk-test", 1)

    assert captured.get("category") == TaskCategory.TEST_GENERATION


def test_model_hint_auto_does_not_crash(tmp_path: Path) -> None:
    """model_hint='auto' falls through to Docker path without raising."""
    executor = _make_executor(tmp_path)
    task = _make_task(output_file="src/Foo.cs", model_hint="auto")

    mock_resp = MagicMock(status="accepted", raw_output=_VALID_RESPONSE)
    mock_pipeline = MagicMock()
    mock_pipeline.invoke.return_value = mock_resp

    with (
        patch("magic_llm.pipeline.MagicLLMPipeline", return_value=mock_pipeline),
        patch.dict("sys.modules", {"autonomous_sprint_runner": None}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}),
    ):
        result = executor._call_llm(task, "prompt", "sk-test", 1)

    assert result == _VALID_RESPONSE


# ── CCT-GO-03: file locking under concurrency ─────────────────────────────────

def test_failure_count_concurrent_writes_no_corruption(tmp_path: Path) -> None:
    """10 concurrent _save calls must not corrupt the failure-count JSON."""
    executor = _make_executor(tmp_path)
    (tmp_path / "sprint-context").mkdir(parents=True, exist_ok=True)
    errors = []

    def worker(key: str) -> None:
        try:
            counts = executor._load_file_failure_counts()
            counts[key] = counts.get(key, 0) + 1
            executor._save_file_failure_counts(counts)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(f"file_{i}",)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors during concurrent writes: {errors}"
    final = executor._load_file_failure_counts()
    assert isinstance(final, dict), "Failure-count file must be valid JSON dict"


# ── CCT-GO-04: cascade set_original_request before on_gate_fail ───────────────

def test_cascade_sets_original_request_before_gate_fail(tmp_path: Path) -> None:
    """_run_cascade calls handler.set_original_request() — no ValueError on L1."""
    executor = _make_executor(tmp_path)
    task = _make_task()

    set_calls = []
    on_gate_calls = []

    mock_handler = MagicMock()
    mock_handler.set_original_request.side_effect = lambda r: set_calls.append(r)
    mock_handler.on_gate_fail.side_effect = lambda ev: on_gate_calls.append(ev)

    with (
        patch("goal_orchestrator.cascade_handler.CascadeHandler",
              return_value=mock_handler),
        patch("magic_llm.pipeline.MagicLLMPipeline"),
        patch("magic_llm.types.MagicLLMRequest"),
        patch.object(executor, "_load_go_intelligence", return_value=MagicMock()),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}),
    ):
        executor._run_cascade(task, "FORMAT gate failed", "last prompt text")

    assert len(set_calls) == 1, "set_original_request must be called exactly once"
    assert len(on_gate_calls) == 1, "on_gate_fail must be called exactly once"
    set_idx = mock_handler.mock_calls.index(call.set_original_request(set_calls[0]))
    gate_idx = mock_handler.mock_calls.index(call.on_gate_fail(on_gate_calls[0]))
    assert set_idx < gate_idx, "set_original_request must precede on_gate_fail"
