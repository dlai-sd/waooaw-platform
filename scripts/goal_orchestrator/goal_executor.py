#!/usr/bin/env python3
"""
goal_executor.py — Goal Orchestrator Execution Dispatcher

# Implements: architecture/reference/magic-llm/architecture.md §7+§8
#             architecture/reference/goal-orchestrator/component-contracts.md §2
# Constitutional basis:
#   C-059 (Evidence First — every file produced has traceable Goal lineage)
#   C-065 (SDLC Separation — GO dispatches, MagicLLM generates, runner commits)
#   C-082 (Build Validation — compile gate enforced per file)
#   C-084 2.0 (Fair-sweep — failed file's dependents skip, rest continue)
#   C-069 (Self-Improvement — cascade replaces spec-gap issues)
# Office: Goal Orchestrator (INST-013)

This module closes A7 — Goal Orchestrator is now in the execution path.

Design:
  Goal Orchestrator receives a Goal (sprint + task list from Work Contract)
  For each task → reads spec from WCSpecReader (not TASK_HANDLERS)
  For each file in task → ContextBuilder §7 assembles context
  LLM generates → ResponseEvaluator §8 gates output
  On compile failure → CascadeHandler L1→L2→L3 (not spec-gap issue)
  On success → Frozen Artifact Registry updated
  All evidence written to Goal Register (C-059)

The hardcoded TASK_HANDLERS in autonomous_sprint_runner.py remain as
fallback ONLY for deterministic tasks and legacy compatibility.
LLM code generation MUST go through GoalExecutor.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).parent.parent.parent

# Ensure scripts/ is on path
_scripts = str(REPO_ROOT / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)


@dataclass
class FileGenerationTask:
    """One unit of work: generate one file via MagicLLM."""
    goal_id: str
    task_id: str               # e.g. "WC012-02b"
    output_file: str           # repo-relative path
    spec_sections: dict[str, str]
    constitutional_check: str
    stack: str                 # "dotnet" | "python" | "typescript" | "terraform"
    model_hint: str            # "reasoning" | "auto" | "none"
    max_tokens: int
    depends_on_files: list[str] = field(default_factory=list)  # prior frozen artifacts


@dataclass
class FileGenerationResult:
    """Result of one MagicLLM file generation attempt."""
    task: FileGenerationTask
    status: str                # "success" | "failed" | "skipped"
    attempts: int = 0
    final_error: str = ""
    cascade_level_reached: int = 0


class GoalExecutor:
    """
    Goal Orchestrator Execution Dispatcher.

    Connects: Goal → WCSpecReader → ContextBuilder → LLM → ResponseEvaluator
              → CascadeHandler (on failure) → Frozen Registry (on success)

    Replaces the hardcoded TASK_HANDLERS pattern for LLM code generation.

    Usage:
        executor = GoalExecutor(goal_id="GOAL-WC-012")
        results = executor.execute_sprint_task(
            task_id="WC012-02",
            wc_number="012",
            output_files=[...],
            completed_tasks=["WC012-01"],
        )
    """

    def __init__(
        self,
        goal_id: str,
        goal_register_writer: Callable[[dict], str] | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.goal_id = goal_id
        self._root = repo_root or REPO_ROOT
        self._write = goal_register_writer or self._default_writer

        # Load MagicLLM components
        self._cb = self._load_context_builder()
        self._evaluator = self._load_response_evaluator()
        self._cascade = None  # loaded on demand

    # ── Public API ─────────────────────────────────────────────────────────────

    def execute_sprint_task(
        self,
        task_id: str,
        wc_number: str,
        output_files: list[str],
        spec_sections: dict[str, str],
        constitutional_check: str,
        stack: str = "dotnet",
        model_hint: str = "reasoning",
        max_tokens: int = 4000,
        completed_tasks: list[str] | None = None,
    ) -> list[FileGenerationResult]:
        """
        Execute one sprint task via GO→MagicLLM pipeline.
        """
        # P1 Fix 5: GEOM lifecycle label — mark Goal as IN_JOURNEY
        self._update_geom_label("goal:in-journey")

        prior_files = self._collect_prior_files(completed_tasks or [])
        # P1 Fix 4: load per-file failure counts from persistent state
        file_failure_counts = self._load_file_failure_counts()

        results: list[FileGenerationResult] = []
        already_frozen: list[str] = []

        for output_file in output_files:
            # P1 Fix 4: skip if this file has failed 3+ consecutive runs
            file_key = output_file.replace("/", "_")
            prior_failures = file_failure_counts.get(file_key, 0)
            if prior_failures >= 3:
                print(f"  [GO] {Path(output_file).name} — {prior_failures} consecutive run failures → genuine spec-gap")
                results.append(FileGenerationResult(
                    task=FileGenerationTask(
                        goal_id=self.goal_id, task_id=f"{task_id}:{Path(output_file).name}",
                        output_file=output_file, spec_sections=spec_sections,
                        constitutional_check=constitutional_check, stack=stack,
                        model_hint=model_hint, max_tokens=max_tokens,
                    ),
                    status="failed",
                    final_error=f"Skipped: {prior_failures} consecutive run failures — spec-gap required"
                ))
                continue

            task = FileGenerationTask(
                goal_id=self.goal_id,
                task_id=f"{task_id}:{Path(output_file).name}",
                output_file=output_file,
                spec_sections=spec_sections,
                constitutional_check=constitutional_check,
                stack=stack,
                model_hint=model_hint,
                max_tokens=max_tokens,
                depends_on_files=prior_files + already_frozen,
            )

            result = self._execute_file(task)
            results.append(result)

            if result.status == "success":
                if self._cb:
                    self._cb.freeze_artifact(output_file, task_id)
                    already_frozen.append(output_file)
                # P1 Fix 4: reset failure count on success
                file_failure_counts[file_key] = 0
                self._write_evidence("FILE_GENERATED", task, result)
            else:
                # P1 Fix 4: increment failure count
                file_failure_counts[file_key] = prior_failures + 1
                self._write_evidence("FILE_FAILED", task, result)

        # P1 Fix 4: persist updated failure counts
        self._save_file_failure_counts(file_failure_counts)
        return results

    def all_succeeded(self, results: list[FileGenerationResult]) -> bool:
        return all(r.status == "success" for r in results)

    # ── Private: file execution with cascade ───────────────────────────────────

    def _execute_file(self, task: FileGenerationTask) -> FileGenerationResult:
        """
        Generate one file: ContextBuilder → LLM → ResponseEvaluator → Cascade.
        Implements §9 retry loop with CascadeHandler on exhaustion.
        """
        result = FileGenerationResult(task=task, status="failed")

        if not self._cb or not self._evaluator:
            result.final_error = "MagicLLM components unavailable"
            return result

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            result.final_error = "ANTHROPIC_API_KEY not set"
            return result

        # §9 Retry loop: 3 attempts with targeted correction
        failure_context = ""
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            result.attempts = attempt

            # §7.1: Fresh ContextBuilder per attempt (reloads frozen registry)
            try:
                from magic_llm.context_builder import ContextBuilder
                cb = ContextBuilder(self._root)
            except Exception:
                cb = self._cb

            try:
                # Build §7.1 ordered context
                ctx = cb.build(
                    task_id=task.task_id,
                    output_file=task.output_file,
                    spec_sections=task.spec_sections,
                    constitutional_check=(
                        task.constitutional_check +
                        (f"\n\nPREVIOUS ATTEMPT FAILED:\n{failure_context}" if failure_context else "")
                    ),
                    depends_on_tasks=[],
                    prior_output_files=task.depends_on_files,
                    stack=task.stack,
                )
                print(f"\n  [GO] {task.task_id} attempt {attempt}/{max_attempts} "
                      f"— {ctx.total_chars:,} chars ({len(ctx.blocks)} slots)")

                # LLM invocation
                response = self._call_llm(task, ctx.full_prompt, api_key, attempt)
                if not response:
                    failure_context = "LLM returned no response."
                    continue

                # Parse + pre-compile self-review before write
                from autonomous_sprint_runner import parse_llm_files, write_llm_files
                files_parsed = parse_llm_files(response)
                if not files_parsed:
                    failure_context = "No <file> blocks in response."
                    continue

                try:
                    from codegen_self_review import pre_compile_review
                    from ptr_assembler import get_assembler as _pga
                    files_parsed = pre_compile_review(files_parsed, api_key, _pga().build_using_map())
                except Exception:
                    pass

                written = write_llm_files(files_parsed)

                # §8 ResponseEvaluator — 5 gates
                eval_result = self._evaluator.evaluate(
                    task_id=task.task_id,
                    raw_response=response,
                    written_files=written,
                    stack=task.stack,
                    spec_sections=task.spec_sections,
                )

                for gate in eval_result.gates:
                    mark = "✅" if gate.passed else "❌"
                    print(f"  {mark} [{task.task_id}] Gate {gate.gate}: {gate.detail[:80]}")

                if eval_result.all_passed:
                    result.status = "success"
                    print(f"  ✅ [GO] {task.task_id} — generated via Goal Orchestrator")
                    return result

                # Classify failure for next attempt context
                failure = eval_result.first_failure
                failure_context = self._classify_and_fix(
                    failure, written, task.task_id
                )

            except Exception as exc:
                failure_context = f"Exception: {exc}"
                print(f"  [GO] attempt {attempt} error: {exc}")

        # All attempts exhausted — route to Cascade (not spec-gap issue)
        result.final_error = failure_context
        cascade_resolved = self._run_cascade(task, failure_context)
        if cascade_resolved:
            result.status = "success"
            result.cascade_level_reached = 1
        else:
            result.status = "failed"
            print(f"  [GO] {task.task_id} — exhausted retries + cascade. BUILD_FAILURE (not spec-gap).")

        return result

    # ── Private: cascade (C-069 — not spec-gap) ───────────────────────────────

    def _run_cascade(self, task: FileGenerationTask, failure_evidence: str) -> bool:
        """
        Route to CascadeHandler instead of creating spec-gap issue.
        L1 → L2 → L3 → Founder (last resort, not first escalation).
        Returns True if cascade resolved the failure.
        """
        try:
            from goal_orchestrator.cascade_handler import CascadeHandler, CascadeContext, CascadeState
            from magic_llm.pipeline import MagicLLMPipeline

            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            ctx_go = CascadeContext(
                goal_id=self.goal_id,
                gate_step=8,  # EEM Step 08 — code generation
            )
            pipeline = MagicLLMPipeline(
                goal_register_writer=self._write,
                api_key=api_key,
            )
            handler = CascadeHandler(
                context=ctx_go,
                goal_register_writer=self._write,
                magic_llm=pipeline,
                go_intelligence=self._load_go_intelligence(pipeline),
            )
            state = handler.on_gate_fail({"failure": failure_evidence, "task": task.task_id})
            return state.name == "RESOLVED"
        except Exception as e:
            print(f"  [GO] Cascade unavailable ({e}) — BUILD_FAILURE logged")
            return False

    # ── Private: LLM invocation ────────────────────────────────────────────────

    def _call_llm(self, task: FileGenerationTask, prompt: str, api_key: str, attempt: int) -> str | None:
        """Invoke LLM via MagicLLM bridge or direct API."""
        try:
            from autonomous_sprint_runner import call_llm_via_magiclm
            return call_llm_via_magiclm(
                task.task_id, f"Generate {Path(task.output_file).name}",
                prompt, "", task.model_hint, task.max_tokens, attempt=attempt,
            )
        except Exception as e:
            print(f"  [GO] LLM call failed: {e}")
            return None

    def _classify_and_fix(self, failure: Any, written: list[str], task_id: str) -> str:
        """Classify compile failure and return targeted fix context for next attempt.
        P1: advisor module loaded ONCE per GoalExecutor instance (not per-retry).
        """
        if not failure or not failure.error_codes:
            return f"Gate {failure.gate if failure else 'UNKNOWN'} failed: {getattr(failure, 'detail', '')[:300]}"
        try:
            # P1 fix: use cached advisor module (loaded at init if available)
            advisor = getattr(self, "_advisor_module", None)
            if advisor is None:
                import importlib.util as _ilu
                _s = _ilu.spec_from_file_location("sprint_retry_advisor",
                     str(self._root / "scripts" / "sprint_retry_advisor.py"))
                _m = _ilu.module_from_spec(_s)
                _s.loader.exec_module(_m)
                self._advisor_module = _m
                advisor = _m
            diagnosis = advisor.diagnose_build_error(task_id, failure.detail, written, [])
            if diagnosis.should_retry and diagnosis.confidence >= 0.3:
                return (
                    f"COMPILE FAILED ({','.join(failure.error_codes)}):\n"
                    f"{failure.detail[:300]}\n\n"
                    f"TARGETED FIX ({diagnosis.error_type}, {diagnosis.confidence:.0%} confidence):\n"
                    f"{diagnosis.fix_instruction}"
                )
        except Exception as e:
            print(f"  [GO] Retry advisor failed ({type(e).__name__}: {e}) — returning raw error")
        return f"Compile failed: {failure.detail[:300]}"

    # ── Private: infrastructure ────────────────────────────────────────────────

    def _collect_prior_files(self, completed_tasks: list[str]) -> list[str]:
        """Collect output files from completed tasks for frozen injection."""
        prior: list[str] = []
        try:
            from autonomous_sprint_runner import TASK_HANDLERS
            for tid in completed_tasks:
                handler = TASK_HANDLERS.get(tid)
                if isinstance(handler, dict) and "subtasks" in handler:
                    for st in handler["subtasks"]:
                        if hasattr(st, "output_files") and st.output_files:
                            prior.extend(st.output_files)
        except Exception as _e:
            print(f"  [GO] {type(_e).__name__}: {_e}")
        return prior

    def _load_context_builder(self):
        try:
            from magic_llm.context_builder import ContextBuilder
            return ContextBuilder(self._root)
        except Exception as e:
            print(f"  [GO] ContextBuilder unavailable: {e}")
            return None

    def _load_response_evaluator(self):
        try:
            from magic_llm.response_evaluator import ResponseEvaluator
            return ResponseEvaluator(self._root)
        except Exception as e:
            print(f"  [GO] ResponseEvaluator unavailable: {e}")
            return None

    def _load_go_intelligence(self, pipeline):
        try:
            from goal_orchestrator.intelligence import GOIntelligence
            return GOIntelligence(magic_llm=pipeline, goal_register_writer=self._write)
        except Exception:
            return None

    def _write_evidence(self, record_type: str, task: FileGenerationTask, result: FileGenerationResult) -> None:
        """C-059: write evidence record before returning."""
        try:
            self._write({
                "record_type": record_type,
                "goal_id": self.goal_id,
                "task_id": task.task_id,
                "output_file": task.output_file,
                "stack": task.stack,
                "status": result.status,
                "attempts": result.attempts,
                "cascade_level": result.cascade_level_reached,
                "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        except Exception as _e:
            print(f"  [GO] {type(_e).__name__}: {_e}")

    @staticmethod
    def _default_writer(record: dict) -> str:
        """Fallback writer — appends to goal_register.jsonl."""
        path = REPO_ROOT / "goals" / "goal_register.jsonl"
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record.get("task_id", "")

    # P1 Fix 5: GEOM lifecycle labels on GitHub Issues
    def _update_geom_label(self, label: str) -> None:
        """Update GEOM lifecycle label on the Goal Register Issue."""
        try:
            github_repo = os.environ.get("GITHUB_REPO", "")
            if not github_repo:
                return
            issue_num = os.environ.get("GOAL_REGISTER_ISSUE", "")
            if not issue_num:
                return
            subprocess.run(
                ["gh", "issue", "edit", issue_num,
                 "--add-label", label,
                 "--repo", github_repo],
                capture_output=True, timeout=15,  # R2: gh CLI can hang on auth failure
            )
        except subprocess.TimeoutExpired:
            print(f"  [GO] GEOM label update timed out — non-blocking")
        except Exception as e:
            print(f"  [GO] GEOM label update failed ({type(e).__name__}: {e}) — non-blocking")

    # P1 Fix 4: per-file failure count persistence
    _FILE_FAILURE_PATH = REPO_ROOT / "sprint-context" / "file-failure-counts.json"

    def _load_file_failure_counts(self) -> dict[str, int]:
        path = self._root / "sprint-context" / "file-failure-counts.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_file_failure_counts(self, counts: dict[str, int]) -> None:
        path = self._root / "sprint-context" / "file-failure-counts.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(counts, indent=2), encoding="utf-8")
