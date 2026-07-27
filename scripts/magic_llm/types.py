# Implements: architecture/reference/magic-llm/architecture.md §5 Engineering Task Classification
# Constitutional basis: C-059 (Traceability), C-069 (Self-Improvement)
"""
MagicLLM — Universal Constitutional AI Execution Layer

Phase 1: Engineering categories (Cat. 1-6) via Anthropic API.
         Orchestration categories (Cat. 9-13) via Gemini (Phase 2).
         Semantic Understanding (Cat. 7) and Research Query (Cat. 8): Phase 2.

Every invocation produces a MagicLLMDecisionRecord committed to the Goal Register
before results are used (C-059: Evidence First).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime, timezone


class TaskCategory(Enum):
    # ── Engineering execution (invoked by Runtime Implementation Professional) ──
    DEEP_REASONING         = 1  # Steps 01-05: large context, deliberate analysis
    CODE_GENERATION        = 2  # Step 08: source code output, compile required
    DESIGN_CONTRACTS       = 3  # Steps 06-07: interface contracts, pseudocode
    REVIEW_EVALUATION      = 4  # Steps 04, 10: fast, structured output
    DOCUMENTATION          = 5  # Step 13: writing quality, fast
    TEST_GENERATION        = 6  # Step 11: test code, AAA pattern
    SEMANTIC_UNDERSTANDING = 7  # Knowledge-deriving agents (RepoNav Semantic Twin)
    RESEARCH_QUERY         = 8  # L2 Remediation: external knowledge synthesis

    # ── Goal Orchestration (invoked by Goal Orchestrator — INST-013 only) ──
    GOAL_UNDERSTANDING      = 9   # GEOM G-2: raw input → Understanding Record
    ROUTING_INTELLIGENCE    = 10  # GEOM G-4: Goal + registry → Execution Plan
    JOURNEY_MONITOR         = 11  # GEOM G-5: continuous drift + SLA detection
    RESEARCH_ORCHESTRATION  = 12  # GEOM §10 L2: cascade research context
    DECISION_SYNTHESIS      = 13  # Founder escalation: 3-option decision brief

    @property
    def is_engineering(self) -> bool:
        return self.value <= 8

    @property
    def is_orchestration(self) -> bool:
        return self.value >= 9

    @property
    def model_hint(self) -> str:
        """Maps to existing ADR-030 model_hint for backward compatibility."""
        if self in (
            TaskCategory.DEEP_REASONING,
            TaskCategory.CODE_GENERATION,
            TaskCategory.DESIGN_CONTRACTS,
            TaskCategory.TEST_GENERATION,
            TaskCategory.GOAL_UNDERSTANDING,
            TaskCategory.ROUTING_INTELLIGENCE,
            TaskCategory.RESEARCH_QUERY,
            TaskCategory.RESEARCH_ORCHESTRATION,
            TaskCategory.DECISION_SYNTHESIS,
        ):
            return "reasoning"
        return "auto"


class QualityGate(str, Enum):
    FORMAT         = "format"       # response follows expected output structure
    COMPILE        = "compile"      # code compiles (Cat. 2, 6)
    SPEC_ALIGN     = "spec_align"   # C-032: no drift from Design Record
    ANNOTATION     = "annotation"   # C-073: @constitutional present
    SCHEMA         = "schema"       # structured outputs satisfy schema
    EVIDENCE_TRACE = "evidence_trace"  # claims traceable to source (Cat. 7, 8)


class FailureClassification(str, Enum):
    CS1061_MISSING_PROPERTY    = "CS1061"
    CS0246_MISSING_TYPE        = "CS0246"
    CS0505_NONVIRTUAL_OVERRIDE = "CS0505"
    SPEC_DRIFT                 = "SPEC_DRIFT"
    FORMAT_FAILURE             = "FORMAT_FAILURE"
    ANNOTATION_MISSING         = "ANNOTATION_MISSING"
    SCHEMA_VIOLATION           = "SCHEMA_VIOLATION"
    EVIDENCE_INCOMPLETE        = "EVIDENCE_INCOMPLETE"
    GOAL_OUTCOME_MISALIGNMENT  = "GOAL_OUTCOME_MISALIGNMENT"
    UNKNOWN                    = "UNKNOWN"


@dataclass
class MagicLLMRequest:
    """Universal input to any MagicLLM invocation.
    Implements: architecture/reference/goal-orchestrator/component-contracts.md §1
    """
    goal_id: str
    institution_id: str                  # INST-NNN of invoking Institution
    go_authorization_id: str             # GOA-GOAL-NNN-INST-NNN-NN (or "internal" for GO-self)
    task_category: TaskCategory
    task_description: str
    context_sections: list[str]          # ordered context blocks
    ptr_snapshot: dict[str, Any]         # Platform Type Registry
    expected_output_format: str          # "xml_file_blocks" | "json" | "prose" | "knowledge_graph"
    execution_plan_reference: str        # record_id of Execution Plan
    previous_attempt_id: Optional[str] = None
    cascade_level: Optional[int] = None  # 1|2|3 if in remediation
    research_record_id: Optional[str] = None
    max_tokens: int = 10_000


@dataclass
class MagicLLMResponse:
    """Universal output from any MagicLLM invocation."""
    request_id: str
    goal_id: str
    institution_id: str
    task_category: TaskCategory
    status: str                          # "accepted" | "retry_needed" | "escalate"
    raw_output: str
    parsed_artifacts: dict[str, Any] = field(default_factory=dict)
    gates_evaluated: dict[str, bool] = field(default_factory=dict)
    failure_classification: Optional[FailureClassification] = None
    failure_detail: Optional[str] = None
    model_provider: str = "anthropic"
    model_version: str = "claude-sonnet-4-6"
    temperature: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_inr: float = 0.0
    attempt_number: int = 1
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MagicLLMDecisionRecord:
    """Constitutional evidence record — committed to Goal Register before results used.
    Implements: architecture/reference/magic-llm/architecture.md §10
    Constitutional basis: C-059 (every AI decision is evidence)
    """
    institution_id: str                  # INST-008 (AI Architect — MagicLLM owner)
    invoked_by: str                      # INST-010 (engineering) | INST-013 (orchestration)
    goal_id: str
    record_id: str                       # MDR-GOAL-NNN-INST-NNN-NN
    record_type: str = "MagicLLM Decision Record"
    task_category: Optional[TaskCategory] = None
    model_provider: str = ""
    model_version: str = ""
    temperature: float = 0.0
    token_allocation: str = ""
    context_strategy: str = ""
    tools_invoked: list[str] = field(default_factory=list)
    gates_evaluated: dict[str, str] = field(default_factory=dict)  # gate: "PASS"|"FAIL"
    retry_count: int = 0
    retry_classifications: list[str] = field(default_factory=list)
    performance_score_used: float = 0.0
    cost_incurred_inr: float = 0.0
    cascade_level: Optional[int] = None
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["task_category"] = self.task_category.name if self.task_category else None
        d["produced_at"] = self.produced_at.isoformat()
        return d
