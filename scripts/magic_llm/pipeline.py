# Implements: architecture/reference/magic-llm/architecture.md §4 Architecture
# Constitutional basis: C-059 (Evidence First), C-069 (Self-Improvement), C-077 (Cost Ceiling)
"""
MagicLLM Pipeline — Phase 1 implementation.

Phase 1 scope:
  Cat. 1-6 (engineering): Anthropic Claude Sonnet 4.6 via API (ADR-030 standard)
  Cat. 7-8 (semantic/research): NotImplemented — Phase 2 adds Gemini Vertex AI
  Cat. 9-13 (orchestration): NotImplemented — Phase 2 adds Gemini Vertex AI

Every invocation records a MagicLLMDecisionRecord BEFORE returning results (C-059).
"""
from __future__ import annotations
import json
import os
import re
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .types import (
    FailureClassification,
    MagicLLMDecisionRecord,
    MagicLLMRequest,
    MagicLLMResponse,
    QualityGate,
    TaskCategory,
)

_PHASE2_CATS = {
    TaskCategory.SEMANTIC_UNDERSTANDING,
    TaskCategory.RESEARCH_QUERY,
    TaskCategory.GOAL_UNDERSTANDING,
    TaskCategory.ROUTING_INTELLIGENCE,
    TaskCategory.JOURNEY_MONITOR,
    TaskCategory.RESEARCH_ORCHESTRATION,
    TaskCategory.DECISION_SYNTHESIS,
}

# ── Model routing (extends ADR-030 §Model Routing) ───────────────────────────
_ANTHROPIC_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_HAIKU  = "claude-haiku-20240307"

_ANTHROPIC_CATS = {
    TaskCategory.DEEP_REASONING,
    TaskCategory.CODE_GENERATION,
    TaskCategory.DESIGN_CONTRACTS,
    TaskCategory.REVIEW_EVALUATION,
    TaskCategory.DOCUMENTATION,
    TaskCategory.TEST_GENERATION,
}

# Cost estimates in INR (approximate, for C-077 tracking)
_COST_PER_1K_INPUT  = {"claude-sonnet-4-6": 0.24, "claude-haiku-20240307": 0.02}
_COST_PER_1K_OUTPUT = {"claude-sonnet-4-6": 1.20, "claude-haiku-20240307": 0.10}


class MagicLLMPipeline:
    """
    8-component constitutional AI execution pipeline.

    Component order: Task Classifier → Model Selector → Context Builder →
    Execution Contract → AI Execution Layer → Response Evaluator →
    [Retry Advisor] → Evidence Recorder

    Phase 1: Engineering categories only (Cat. 1-6).
    Phase 2: All 13 categories with Gemini Vertex AI for orchestration.
    """

    def __init__(
        self,
        goal_register_writer: Optional[Callable[[dict], str]] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._write_record = goal_register_writer or self._default_file_writer
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    # ── Public API ───────────────────────────────────────────────────────────

    def invoke(self, request: MagicLLMRequest) -> MagicLLMResponse:
        """
        Single entry point for all MagicLLM invocations.
        Records MagicLLMDecisionRecord to Goal Register BEFORE returning (C-059).
        """
        # ① Task Classifier
        if request.task_category in _PHASE2_CATS:
            raise NotImplementedError(
                f"TaskCategory.{request.task_category.name} requires Phase 2 "
                f"(Gemini Vertex AI). Current implementation supports Cat. 1-6."
            )

        # ② Model Selector
        model, temperature = self._select_model(request.task_category)

        # ③ Context Builder
        prompt = self._build_prompt(request)

        # ④ Execution Contract
        max_tokens = request.max_tokens
        use_thinking = request.task_category.model_hint == "reasoning"

        # ⑤ AI Execution Layer
        raw_response, in_tok, out_tok = self._call_anthropic(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            use_thinking=use_thinking,
        )

        cost = self._estimate_cost(model, in_tok, out_tok)

        # ⑥ Response Evaluator
        status, gates, failure_class, failure_detail = self._evaluate(
            raw_response, request
        )

        response = MagicLLMResponse(
            request_id=str(uuid.uuid4()),
            goal_id=request.goal_id,
            institution_id=request.institution_id,
            task_category=request.task_category,
            status=status,
            raw_output=raw_response or "",
            parsed_artifacts=self._parse_artifacts(raw_response, request.expected_output_format),
            gates_evaluated=gates,
            failure_classification=failure_class,
            failure_detail=failure_detail,
            model_provider="anthropic",
            model_version=model,
            temperature=temperature,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_inr=cost,
            attempt_number=1 if not request.previous_attempt_id else 2,
        )

        # ⑧ Evidence Recorder — BEFORE returning (C-059 Evidence First)
        decision_record = MagicLLMDecisionRecord(
            institution_id="INST-008",
            invoked_by=request.institution_id,
            goal_id=request.goal_id,
            record_id=f"MDR-{request.goal_id}-{request.institution_id}-{int(time.time())}",
            task_category=request.task_category,
            model_provider="anthropic",
            model_version=model,
            temperature=temperature,
            token_allocation=f"{in_tok}/{out_tok}",
            context_strategy=f"{len(request.context_sections)} sections, PTR={'yes' if request.ptr_snapshot else 'no'}",
            gates_evaluated={k: ("PASS" if v else "FAIL") for k, v in gates.items()},
            retry_count=0 if not request.previous_attempt_id else 1,
            cost_incurred_inr=cost,
            cascade_level=request.cascade_level,
        )
        self._write_record(decision_record.to_dict())

        return response

    def retry_with_enhanced_context(
        self,
        goal_id: str,
        failure_evidence: dict,
        attempt: int,
        original_request: Optional[MagicLLMRequest] = None,
    ) -> MagicLLMResponse:
        """L1 Cascade retry — enhanced context from RetryAdvisor."""
        if original_request is None:
            raise ValueError("original_request required for retry")

        correction = self._classify_retry(failure_evidence)
        enhanced_sections = list(original_request.context_sections) + [
            f"## RETRY CORRECTION (attempt {attempt})\n{correction}"
        ]
        retry_req = MagicLLMRequest(
            goal_id=goal_id,
            institution_id=original_request.institution_id,
            go_authorization_id=original_request.go_authorization_id,
            task_category=original_request.task_category,
            task_description=original_request.task_description,
            context_sections=enhanced_sections,
            ptr_snapshot=original_request.ptr_snapshot,
            expected_output_format=original_request.expected_output_format,
            execution_plan_reference=original_request.execution_plan_reference,
            previous_attempt_id=str(uuid.uuid4()),
            cascade_level=1,
        )
        return self.invoke(retry_req)

    def retry_with_research_context(
        self,
        goal_id: str,
        research_record: Any,  # ResearchRecord
        attempt: int,
        original_request: Optional[MagicLLMRequest] = None,
    ) -> MagicLLMResponse:
        """L2 Cascade retry — research findings injected into context."""
        if original_request is None:
            raise ValueError("original_request required for research retry")

        research_section = (
            "## INDUSTRY RESEARCH FINDINGS (Level 2 Remediation)\n"
            + "\n".join(research_record.recommendations[:3])
        )
        enhanced_sections = list(original_request.context_sections) + [research_section]
        retry_req = MagicLLMRequest(
            goal_id=goal_id,
            institution_id=original_request.institution_id,
            go_authorization_id=original_request.go_authorization_id,
            task_category=original_request.task_category,
            task_description=original_request.task_description,
            context_sections=enhanced_sections,
            ptr_snapshot=original_request.ptr_snapshot,
            expected_output_format=original_request.expected_output_format,
            execution_plan_reference=original_request.execution_plan_reference,
            previous_attempt_id=str(uuid.uuid4()),
            cascade_level=2,
            research_record_id=research_record.record_id,
        )
        return self.invoke(retry_req)

    # ── Private: Model Selector (②) ──────────────────────────────────────────

    def _select_model(self, category: TaskCategory) -> tuple[str, float]:
        """Returns (model_name, temperature) for the given task category."""
        if category in (
            TaskCategory.CODE_GENERATION,
            TaskCategory.TEST_GENERATION,
            TaskCategory.DEEP_REASONING,
            TaskCategory.DESIGN_CONTRACTS,
        ):
            return _ANTHROPIC_MODEL, 0.0
        return _ANTHROPIC_HAIKU, 0.0

    # ── Private: Context Builder (③) ─────────────────────────────────────────

    def _build_prompt(self, request: MagicLLMRequest) -> str:
        """Assembles context sections + PTR + constitutional obligations."""
        parts: list[str] = []

        # Constitutional preamble
        parts.append(
            "## CONSTITUTIONAL OBLIGATIONS\n"
            "Every file you produce MUST begin with:\n"
            "# Implements: <spec-path> §<section>\n"
            "# Constitutional basis: C-NNN (<claim name>)\n"
            "Output format: <file path=\"relative/path/to/file.ext\">...content...</file>\n"
        )

        # Platform Type Registry injection (for code tasks)
        if request.ptr_snapshot:
            ptr_lines = [f"  {k}: {v}" for k, v in list(request.ptr_snapshot.items())[:30]]
            parts.append("## PLATFORM TYPE REGISTRY (compiled types)\n" + "\n".join(ptr_lines))

        # Spec sections
        for i, section in enumerate(request.context_sections):
            parts.append(f"## CONTEXT SECTION {i + 1}\n{section}")

        # Task
        parts.append(f"## TASK\n{request.task_description}")

        return "\n\n---\n\n".join(parts)

    # ── Private: AI Execution Layer (⑤) ──────────────────────────────────────

    def _call_anthropic(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        use_thinking: bool,
    ) -> tuple[str | None, int, int]:
        """Direct Anthropic API call matching existing call_llm() pattern."""
        if not self._api_key:
            return None, 0, 0

        THINKING_OVERHEAD = 8000
        THINKING_BUDGET   = 8000
        effective_max = (max_tokens + THINKING_OVERHEAD) if use_thinking else max_tokens

        body: dict[str, Any] = {
            "model": model,
            "max_tokens": effective_max,
            "messages": [{"role": "user", "content": prompt}],
        }
        if use_thinking:
            body["thinking"] = {"type": "enabled", "budget_tokens": THINKING_BUDGET}

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "anthropic-beta": "interleaved-thinking-2025-05-14",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"  [MagicLLM] API call failed: {exc}")
            return None, 0, 0

        in_tok  = data.get("usage", {}).get("input_tokens", 0)
        out_tok = data.get("usage", {}).get("output_tokens", 0)
        text_blocks = [
            b["text"] for b in data.get("content", []) if b.get("type") == "text"
        ]
        return "\n".join(text_blocks) if text_blocks else None, in_tok, out_tok

    # ── Private: Response Evaluator (⑥) ──────────────────────────────────────

    def _evaluate(
        self,
        raw: str | None,
        request: MagicLLMRequest,
    ) -> tuple[str, dict[str, bool], Optional[FailureClassification], Optional[str]]:
        """Runs quality gates. Returns (status, gates_dict, failure_class, detail)."""
        gates: dict[str, bool] = {}

        if not raw:
            gates[QualityGate.FORMAT] = False
            return "escalate", gates, FailureClassification.FORMAT_FAILURE, "empty response"

        # Format gate
        if request.expected_output_format == "xml_file_blocks":
            has_files = bool(re.search(r'<file\s+path=', raw))
            gates[QualityGate.FORMAT] = has_files
            if not has_files:
                return "retry_needed", gates, FailureClassification.FORMAT_FAILURE, "no <file> blocks found"
        elif request.expected_output_format == "json":
            try:
                json.loads(raw)
                gates[QualityGate.FORMAT] = True
            except json.JSONDecodeError as e:
                gates[QualityGate.FORMAT] = False
                return "retry_needed", gates, FailureClassification.SCHEMA_VIOLATION, str(e)
        else:
            gates[QualityGate.FORMAT] = bool(raw.strip())

        # Annotation gate (C-073) — for code tasks
        if request.task_category in (TaskCategory.CODE_GENERATION, TaskCategory.TEST_GENERATION):
            has_implements = "# Implements:" in raw
            gates[QualityGate.ANNOTATION] = has_implements
            if not has_implements:
                return "retry_needed", gates, FailureClassification.ANNOTATION_MISSING, \
                       "missing # Implements: header (C-073)"

        return "accepted", gates, None, None

    # ── Private: Retry Advisor (⑦) ───────────────────────────────────────────

    def _classify_retry(self, failure_evidence: dict) -> str:
        """Maps failure evidence to targeted correction text."""
        fc = failure_evidence.get("failure_classification", "")
        if fc == FailureClassification.CS1061_MISSING_PROPERTY:
            prop = failure_evidence.get("detail", "unknown property")
            return (
                f"CS1061 Fix: The property '{prop}' does not exist on that type. "
                "Consult the Platform Type Registry above for the exact available properties. "
                "Do NOT call TryGetValue() on a non-dictionary type."
            )
        if fc == FailureClassification.CS0246_MISSING_TYPE:
            return "CS0246 Fix: The referenced type is not imported. Add the correct using statement from the PTR above."
        if fc == FailureClassification.ANNOTATION_MISSING:
            return "C-073 Fix: Every file must begin with:\n# Implements: <spec-path> §<section>\n# Constitutional basis: C-NNN"
        if fc == FailureClassification.FORMAT_FAILURE:
            return "FORMAT Fix: Respond with XML file blocks only: <file path=\"...\">...content...</file>"
        return f"GENERIC Fix: Previous attempt failed with: {fc}. Review spec sections carefully."

    # ── Private: Artifact Parser ──────────────────────────────────────────────

    def _parse_artifacts(self, raw: str | None, fmt: str) -> dict[str, Any]:
        if not raw:
            return {}
        if fmt == "xml_file_blocks":
            files: dict[str, str] = {}
            for m in re.finditer(r'<file\s+path="([^"]+)">(.*?)</file>', raw, re.DOTALL):
                files[m.group(1)] = m.group(2).strip()
            return {"files": files}
        if fmt == "json":
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
        return {"prose": raw}

    # ── Private: Cost Estimator ───────────────────────────────────────────────

    def _estimate_cost(self, model: str, in_tok: int, out_tok: int) -> float:
        """Estimates cost in INR for C-077 tracking."""
        r_in  = _COST_PER_1K_INPUT.get(model, 0)
        r_out = _COST_PER_1K_OUTPUT.get(model, 0)
        return round((in_tok / 1000) * r_in + (out_tok / 1000) * r_out, 4)

    # ── Private: Default file-based Goal Register writer (Phase 1) ───────────

    @staticmethod
    def _default_file_writer(record: dict) -> str:
        """Phase 1: writes Decision Records to a JSON-lines file.
        Phase 2: replaced by PostgreSQL constitutional.goal_register insert.
        """
        register_path = Path(__file__).parent.parent.parent / "goals" / "goal_register.jsonl"
        register_path.parent.mkdir(parents=True, exist_ok=True)
        with register_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return record.get("record_id", "")
