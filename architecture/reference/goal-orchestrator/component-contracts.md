# Goal Orchestrator — Component Contracts

**Classification:** Reference Architecture — Component Specification
**Status:** Proposed — Awaiting Enterprise Architect review
**Produced by:** Solution Architect (INST-005) — GOAL-002 Phase B (2026-07-27)
**Constitutional Basis:** C-059 (Traceability) · ORGANIZATION.md Office 05 (Solution Architect Decision Space)
**Goal Reference:** GOAL-002 Phase B
**Implements:** architecture/reference/goal-orchestrator/intelligence.md (Phase A) · architecture/reference/magic-llm/architecture.md
**Output files (for Runtime Implementation Professional):**
```
scripts/magic_llm/__init__.py
scripts/magic_llm/types.py
scripts/magic_llm/pipeline.py          ← 8-component pipeline (engineering Cat. 1-8)
scripts/magic_llm/orchestration.py     ← GO-Intelligence (Cat. 9-13)
scripts/magic_llm/evidence_recorder.py
scripts/goal_orchestrator/__init__.py
scripts/goal_orchestrator/intelligence.py   ← GO-Intelligence coordinator
scripts/goal_orchestrator/cascade_handler.py  ← Remediation Cascade state machine
infrastructure/postgres/init/10-goal-orchestrator-performance.sql
```

---

## §1 — Shared Types (`scripts/magic_llm/types.py`)

```python
# Implements: architecture/reference/magic-llm/architecture.md §5 Engineering Task Classification
# Constitutional basis: C-059 (Traceability)
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional
from datetime import datetime


class TaskCategory(Enum):
    # Engineering execution (invoked by Runtime Implementation Professional)
    DEEP_REASONING       = 1   # Steps 01-05: large context, deliberate analysis
    CODE_GENERATION      = 2   # Step 08: source code, compile required
    DESIGN_CONTRACTS     = 3   # Steps 06-07: interface contracts, pseudocode
    REVIEW_EVALUATION    = 4   # Steps 04, 10: fast, structured output
    DOCUMENTATION        = 5   # Step 13: writing quality, fast
    TEST_GENERATION      = 6   # Step 11: test code, AAA pattern
    SEMANTIC_UNDERSTANDING = 7 # Knowledge-deriving agents (RepoNav Semantic Twin)
    RESEARCH_QUERY       = 8   # L2 Remediation: external knowledge synthesis

    # Goal Orchestration (invoked by Goal Orchestrator — INST-013 only)
    GOAL_UNDERSTANDING   = 9   # GEOM G-2: raw input → Understanding Record
    ROUTING_INTELLIGENCE = 10  # GEOM G-4: Goal + registry → Execution Plan
    JOURNEY_MONITOR      = 11  # GEOM G-5: continuous drift + SLA detection
    RESEARCH_ORCHESTRATION = 12  # GEOM §10 L2: research query in cascade context
    DECISION_SYNTHESIS   = 13  # Founder escalation: 3-option decision brief


class QualityGate(Enum):
    FORMAT        = "format"        # response follows expected output structure
    COMPILE       = "compile"       # code compiles (Cat. 2, 6, 7)
    SPEC_ALIGN    = "spec_align"    # C-032: no drift from Design Record
    ANNOTATION    = "annotation"    # C-073: @constitutional present
    SCHEMA        = "schema"        # structured outputs satisfy schema
    EVIDENCE_TRACE = "evidence_trace"  # all claims traceable to source (Cat. 7, 8)


class FailureClassification(Enum):
    CS1061_MISSING_PROPERTY   = "CS1061"   # model referenced nonexistent property
    CS0246_MISSING_TYPE       = "CS0246"   # model referenced nonexistent type
    CS0505_NONVIRTUAL_OVERRIDE = "CS0505"  # override on non-virtual method
    SPEC_DRIFT                = "SPEC_DRIFT"  # output contradicts Design Record
    FORMAT_FAILURE            = "FORMAT_FAILURE"  # output format not followed
    ANNOTATION_MISSING        = "ANNOTATION_MISSING"  # constitutional header absent
    SCHEMA_VIOLATION          = "SCHEMA_VIOLATION"   # structured output malformed
    EVIDENCE_INCOMPLETE       = "EVIDENCE_INCOMPLETE" # not all claims traceable
    GOAL_OUTCOME_MISALIGNMENT = "GOAL_OUTCOME_MISALIGNMENT"  # Gate Fail


@dataclass
class MagicLLMRequest:
    """Universal input to any MagicLLM invocation."""
    goal_id: str                       # GOAL-NNN
    institution_id: str                # INST-NNN of invoking Institution
    go_authorization_id: str           # GOA-GOAL-NNN-INST-NNN-NN
    task_category: TaskCategory
    task_description: str              # human-readable task purpose
    context_sections: list[str]        # ordered list of context content blocks
    ptr_snapshot: dict[str, Any]       # Platform Type Registry (for Cat. 2, 6)
    expected_output_format: str        # "xml_file_blocks" | "json" | "prose" | "knowledge_graph"
    execution_plan_reference: str      # record_id of Execution Plan in Goal Register
    previous_attempt_id: Optional[str] = None  # if this is a retry
    cascade_level: Optional[int] = None        # 1|2|3 if in remediation cascade
    research_record_id: Optional[str] = None   # if L3 redesign — inject research findings


@dataclass
class MagicLLMResponse:
    """Universal output from any MagicLLM invocation."""
    request_id: str
    goal_id: str
    institution_id: str
    task_category: TaskCategory
    status: str                        # "accepted" | "retry_needed" | "escalate"
    raw_output: str                    # the LLM's raw response
    parsed_artifacts: dict[str, Any]   # parsed output (file blocks, JSON, etc.)
    gates_evaluated: dict[str, bool]   # {QualityGate.name: passed}
    failure_classification: Optional[FailureClassification] = None
    failure_detail: Optional[str] = None
    model_provider: str = ""
    model_version: str = ""
    temperature: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_inr: float = 0.0
    attempt_number: int = 1
    produced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MagicLLMDecisionRecord:
    """Constitutional evidence record — committed to Goal Register before results used.
    Implements: architecture/reference/magic-llm/architecture.md §10 Evidence
    Constitutional basis: C-059 (every decision is evidence)
    """
    institution_id: str                # owner = INST-008 (AI Architect)
    invoked_by: str                    # INST-010 (engineering) or INST-013 (orchestration)
    goal_id: str
    record_id: str                     # MDR-GOAL-NNN-INST-NNN-NN
    record_type: str = "MagicLLM Decision Record"
    task_category: TaskCategory = TaskCategory.CODE_GENERATION
    model_provider: str = ""
    model_version: str = ""
    temperature: float = 0.0
    token_allocation: str = ""         # "input/output"
    context_strategy: str = ""
    tools_invoked: list[str] = field(default_factory=list)
    gates_evaluated: dict[str, str] = field(default_factory=dict)  # gate: PASS|FAIL
    retry_count: int = 0
    retry_classifications: list[str] = field(default_factory=list)
    performance_score_used: float = 0.0
    cost_incurred_inr: float = 0.0
    cascade_level: Optional[int] = None
    produced_at: datetime = field(default_factory=datetime.utcnow)
```

---

## §2 — GO-Intelligence Types (`scripts/magic_llm/orchestration.py`)

```python
# Implements: architecture/reference/goal-orchestrator/intelligence.md §2
# Constitutional basis: C-059 · C-069 · C-070
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from .types import MagicLLMRequest, TaskCategory


# ── Category 9: Goal Understanding ──────────────────────────────────────────

@dataclass
class GoalUnderstandingRequest:
    """Input to Cat. 9 — converts raw Founder input into structured Goal."""
    raw_input: str                       # plain English, transcript, notes — any format
    registrant_id: str                   # INST-NNN or "founder"
    related_goal_ids: list[str]          # for conflict/dependency detection
    session_context: Optional[str] = None  # any additional Founder context

@dataclass
class GoalUnderstandingRecord:
    """Cat. 9 output — constitutional Goal Understanding Record.
    Committed to Goal Register before Classification begins.
    """
    record_id: str                       # UR-GOAL-NNN-INST-013-01
    goal_id: str
    record_type: str = "Goal Understanding Record"
    institution_id: str = "INST-013"
    intent: str = ""                     # structured business outcome statement
    success_criteria_draft: list[dict] = field(default_factory=list)  # [{id, criterion}]
    constitutional_implications: list[str] = field(default_factory=list)
    clarification_needed: bool = False
    clarifications: list[str] = field(default_factory=list)
    related_goals: list[str] = field(default_factory=list)
    produced_at: datetime = field(default_factory=datetime.utcnow)


# ── Category 10: Routing Intelligence ───────────────────────────────────────

@dataclass
class RoutingRequest:
    """Input to Cat. 10 — produces optimal Execution Plan."""
    goal_id: str
    goal_classification: dict            # {scope, nature, risk, urgency}
    understanding_record_id: str
    available_institutions: list[dict]   # from Institution Registry (OPERATIONAL only)
    performance_history: list[dict]      # from institutional.goal_orchestrator_performance
    active_institution_load: dict        # {inst_id: active_goal_count}

@dataclass
class RoutingDecisionRecord:
    """Cat. 10 output — routing rationale + draft Execution Plan.
    Reviewed by Constitutional Analyst before GO Authorizations issued.
    """
    record_id: str                       # RDR-GOAL-NNN-INST-013-01
    goal_id: str
    record_type: str = "Routing Decision Record"
    institution_id: str = "INST-013"
    selected_institutions: list[str] = field(default_factory=list)   # [INST-NNN]
    execution_sequence: str = ""         # "sequential" | "parallel" | "hybrid"
    routing_rationale: dict = field(default_factory=dict)  # {inst_id: rationale_str}
    cascade_parameters: dict = field(default_factory=lambda: {
        "l1_max_attempts": 3,
        "l2_max_attempts": 2,
        "l3_max_attempts": 1,
    })
    draft_execution_plan_id: str = ""    # references the draft plan record
    produced_at: datetime = field(default_factory=datetime.utcnow)


# ── Category 11: Journey Monitor ────────────────────────────────────────────

class MonitorSignalType(str):
    NOMINAL         = "NOMINAL"
    SLA_WARNING     = "SLA_WARNING"
    DRIFT_DETECTED  = "DRIFT_DETECTED"
    QUALITY_CONCERN = "QUALITY_CONCERN"

@dataclass
class JourneyMonitorInput:
    """Input to Cat. 11 — called on every new Goal Register entry."""
    goal_id: str
    new_record: dict                     # the new contribution/learning/decision record
    goal_register_state: dict            # current accumulated evidence
    success_criteria: list[dict]         # SC-NNN list
    execution_plan: dict                 # Evidence Specifications + Participation Windows

@dataclass
class MonitorSignal:
    """Cat. 11 output — GO operational log entry (not main evidence chain)."""
    record_id: str                       # MS-GOAL-NNN-INST-013-NN
    goal_id: str
    record_type: str = "Monitor Signal"
    institution_id: str = "INST-013"
    signal_type: str = MonitorSignalType.NOMINAL
    description: str = ""
    recommended_action: str = ""
    triggered_by_record: str = ""        # record_id that triggered this signal
    produced_at: datetime = field(default_factory=datetime.utcnow)


# ── Category 12: Research Query (Orchestration) ──────────────────────────────

@dataclass
class ResearchQueryRequest:
    """Input to Cat. 12 — L2 Remediation research query."""
    goal_id: str
    gap_description: str                 # exactly what outcome is not being met
    failure_evidence: list[str]          # [record_id of L1 Attempt Records]
    goal_domain: str                     # from Goal Understanding classification
    technology_context: dict             # from Platform Type Registry
    knowledge_domains: list[str] = field(default_factory=list)  # override default sources

@dataclass
class ResearchRecord:
    """Cat. 12 output — external knowledge synthesis.
    Committed to Goal Register. Injected into producing Institution's L2 retry context.
    """
    record_id: str                       # RR-GOAL-NNN-INST-013-01
    goal_id: str
    record_type: str = "Research Record"
    institution_id: str = "INST-013"
    gap_addressed: str = ""
    sources_queried: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)  # [{source, finding, relevance}]
    applicable_patterns: list[str] = field(default_factory=list)
    constitutional_screen_exclusions: list[dict] = field(default_factory=list)
    confidence: float = 0.0              # 0.0-1.0
    recommendations: list[str] = field(default_factory=list)  # ranked
    produced_at: datetime = field(default_factory=datetime.utcnow)


# ── Category 13: Decision Synthesis ─────────────────────────────────────────

@dataclass
class DecisionSynthesisRequest:
    """Input to Cat. 13 — assembles Founder decision brief."""
    goal_id: str
    understanding_record_id: str
    l1_attempt_record_ids: list[str]
    l2_research_record_id: str
    l3_redesign_record_id: str
    specific_gap: str                    # the precise unresolvable gap
    constitutional_context: list[str]    # relevant claims, articles, amendments

@dataclass
class FounderDecisionBrief:
    """Cat. 13 output — constitutional Founder Evidence Package.
    Delivered via Steward Assistant. Designed for mobile reading in <2 minutes.
    """
    record_id: str                       # FDB-GOAL-NNN-INST-013-01
    goal_id: str
    record_type: str = "Founder Decision Brief"
    institution_id: str = "INST-013"
    headline: str = ""                   # one sentence: what Founder must decide
    goal_summary: str = ""              # 2 sentences
    what_was_tried: str = ""            # L1/L2/L3 plain-English summary
    the_gap: str = ""                   # the precise problem in plain language
    option_a: dict = field(default_factory=dict)  # {title, what_changes, what_preserved}
    option_b: dict = field(default_factory=dict)  # {title, new_goal_scope, estimated_effort}
    option_c: dict = field(default_factory=dict)  # {title, defer_until, unblock_conditions}
    constitutional_note: str = ""        # which option best preserves integrity
    assembled_at: datetime = field(default_factory=datetime.utcnow)
```

---

## §3 — Cascade Handler State Machine (`scripts/goal_orchestrator/cascade_handler.py`)

```python
# Implements: architecture/reference/goal-orchestrator/intelligence.md §1
#             constitution/GEOM.md §10 (Remediation Cascade)
# Constitutional basis: C-070 Instinct 3 · C-001 (Founder = last resort)
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, Awaitable
from datetime import datetime


class CascadeState(Enum):
    NOMINAL           = auto()  # no cascade active
    L1_ACTIVE         = auto()  # Level 1 retries in progress
    L1_EXHAUSTED      = auto()  # L1 all attempts failed
    L2_ACTIVE         = auto()  # Level 2 research query in progress
    L2_EXHAUSTED      = auto()  # L2 all attempts failed
    L3_ACTIVE         = auto()  # Level 3 expert-informed redesign in progress
    L3_EXHAUSTED      = auto()  # L3 failed
    FOUNDER_PENDING   = auto()  # Evidence Package sent, awaiting Founder
    RESOLVED          = auto()  # any level resolved the Goal Outcome Alignment
    ESCALATED         = auto()  # Founder made decision


@dataclass
class CascadeContext:
    """Mutable state for one cascade activation on a Goal."""
    goal_id: str
    gate_step: int                       # which EEM step triggered (6, 10, or 14)
    state: CascadeState = CascadeState.NOMINAL
    l1_attempts: int = 0
    l1_max: int = 3
    l2_attempts: int = 0
    l2_max: int = 2
    l3_attempts: int = 0
    l3_max: int = 1
    l1_record_ids: list[str] = field(default_factory=list)
    l2_research_record_id: Optional[str] = None
    l3_redesign_record_id: Optional[str] = None
    founder_brief_id: Optional[str] = None
    founder_decision: Optional[str] = None  # "a" | "b" | "c"
    activated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by_level: Optional[int] = None  # 1, 2, or 3


class CascadeHandler:
    """
    Constitutional Remediation Cascade state machine.
    Called by Goal Orchestrator on every Goal Outcome Alignment Gate failure.

    State transitions are strictly ordered — no level may be skipped.
    Each transition produces a Goal Register entry before proceeding.
    """

    # ── State transition map (current_state → valid_next_states) ──────────
    VALID_TRANSITIONS: dict[CascadeState, list[CascadeState]] = {
        CascadeState.NOMINAL:         [CascadeState.L1_ACTIVE],
        CascadeState.L1_ACTIVE:       [CascadeState.RESOLVED, CascadeState.L1_EXHAUSTED],
        CascadeState.L1_EXHAUSTED:    [CascadeState.L2_ACTIVE],
        CascadeState.L2_ACTIVE:       [CascadeState.RESOLVED, CascadeState.L2_EXHAUSTED],
        CascadeState.L2_EXHAUSTED:    [CascadeState.L3_ACTIVE],
        CascadeState.L3_ACTIVE:       [CascadeState.RESOLVED, CascadeState.L3_EXHAUSTED],
        CascadeState.L3_EXHAUSTED:    [CascadeState.FOUNDER_PENDING],
        CascadeState.FOUNDER_PENDING: [CascadeState.ESCALATED],
        CascadeState.RESOLVED:        [],   # terminal
        CascadeState.ESCALATED:       [],   # terminal
    }

    def __init__(
        self,
        context: CascadeContext,
        goal_register_writer: Callable[[dict], Awaitable[str]],  # returns record_id
        magic_llm: "MagicLLMPipeline",
        go_intelligence: "GOIntelligence",
        steward_notifier: Callable[[str, str], Awaitable[None]],  # (goal_id, brief_id)
    ) -> None:
        self.ctx = context
        self._write = goal_register_writer
        self._llm = magic_llm
        self._go = go_intelligence
        self._notify = steward_notifier

    def _transition(self, to: CascadeState) -> None:
        """Constitutional state transition — validates before applying."""
        valid = self.VALID_TRANSITIONS[self.ctx.state]
        if to not in valid:
            raise ValueError(
                f"Invalid cascade transition {self.ctx.state} → {to}. "
                f"Valid: {valid}. Goal: {self.ctx.goal_id}"
            )
        self.ctx.state = to

    async def on_gate_fail(self, failure_evidence: dict) -> CascadeState:
        """
        Entry point: called by Goal Orchestrator when an Alignment Gate fails.
        Orchestrates the full cascade autonomously.
        Returns the final CascadeState.
        """
        self._transition(CascadeState.L1_ACTIVE)
        await self._run_l1(failure_evidence)

        if self.ctx.state == CascadeState.RESOLVED:
            return self.ctx.state

        # L1 exhausted → L2
        self._transition(CascadeState.L2_ACTIVE)
        await self._run_l2(failure_evidence)

        if self.ctx.state == CascadeState.RESOLVED:
            return self.ctx.state

        # L2 exhausted → L3
        self._transition(CascadeState.L3_ACTIVE)
        await self._run_l3()

        if self.ctx.state == CascadeState.RESOLVED:
            return self.ctx.state

        # L3 exhausted → Founder
        self._transition(CascadeState.FOUNDER_PENDING)
        await self._escalate_to_founder()

        return self.ctx.state

    async def on_founder_decision(self, decision: str) -> None:
        """Called when Founder responds to the Evidence Package (option a/b/c)."""
        if decision not in ("a", "b", "c"):
            raise ValueError(f"Invalid Founder decision '{decision}' — must be a, b, or c")
        self.ctx.founder_decision = decision
        self._transition(CascadeState.ESCALATED)
        # Goal Orchestrator acts on decision separately

    # ── Private level runners ─────────────────────────────────────────────

    async def _run_l1(self, failure_evidence: dict) -> None:
        while self.ctx.l1_attempts < self.ctx.l1_max:
            self.ctx.l1_attempts += 1
            result = await self._llm.retry_with_enhanced_context(
                goal_id=self.ctx.goal_id,
                failure_evidence=failure_evidence,
                attempt=self.ctx.l1_attempts,
            )
            record_id = await self._write({
                "record_type": "L1 Attempt Record",
                "goal_id": self.ctx.goal_id,
                "attempt": self.ctx.l1_attempts,
                "failure_classification": result.failure_classification,
                "outcome": result.status,
            })
            self.ctx.l1_record_ids.append(record_id)
            if result.status == "accepted":
                self.ctx.resolved_by_level = 1
                self.ctx.resolved_at = datetime.utcnow()
                self._transition(CascadeState.RESOLVED)
                return
        self._transition(CascadeState.L1_EXHAUSTED)

    async def _run_l2(self, failure_evidence: dict) -> None:
        # Issue Collaboration Amendment → Enterprise Architect runs Research Query
        research = await self._go.research_query(
            goal_id=self.ctx.goal_id,
            failure_evidence=failure_evidence,
            l1_record_ids=self.ctx.l1_record_ids,
        )
        self.ctx.l2_research_record_id = research.record_id

        while self.ctx.l2_attempts < self.ctx.l2_max:
            self.ctx.l2_attempts += 1
            result = await self._llm.retry_with_research_context(
                goal_id=self.ctx.goal_id,
                research_record=research,
                attempt=self.ctx.l2_attempts,
            )
            if result.status == "accepted":
                self.ctx.resolved_by_level = 2
                self.ctx.resolved_at = datetime.utcnow()
                self._transition(CascadeState.RESOLVED)
                return
        self._transition(CascadeState.L2_EXHAUSTED)

    async def _run_l3(self) -> None:
        # Enterprise Architect reviews Research Record + revises Engineering Proposal
        redesign_id = await self._go.expert_informed_redesign(
            goal_id=self.ctx.goal_id,
            research_record_id=self.ctx.l2_research_record_id,
        )
        self.ctx.l3_redesign_record_id = redesign_id
        self.ctx.l3_attempts = 1
        # EEM re-runs from Step 03 — success/failure comes back via on_gate_fail or resolved
        # The redesign run result is tracked separately; this handler waits for callback
        # (implementation: redesign triggers a new EEM pass; callback invoked on Gate check)
        self._transition(CascadeState.L3_EXHAUSTED)  # if no callback = fail

    async def _escalate_to_founder(self) -> None:
        brief = await self._go.synthesise_decision(
            goal_id=self.ctx.goal_id,
            l1_ids=self.ctx.l1_record_ids,
            l2_id=self.ctx.l2_research_record_id,
            l3_id=self.ctx.l3_redesign_record_id,
        )
        self.ctx.founder_brief_id = brief.record_id
        await self._write(brief.__dict__)
        await self._notify(self.ctx.goal_id, brief.record_id)
```

---

## §4 — GO-Intelligence Coordinator (`scripts/goal_orchestrator/intelligence.py`)

```python
# Implements: architecture/reference/goal-orchestrator/intelligence.md §1
# Constitutional basis: C-070 · C-069 · GEOM §6
from __future__ import annotations
from typing import TYPE_CHECKING
from .cascade_handler import CascadeHandler, CascadeContext
from scripts.magic_llm.orchestration import (
    GoalUnderstandingRequest, GoalUnderstandingRecord,
    RoutingRequest, RoutingDecisionRecord,
    JourneyMonitorInput, MonitorSignal,
    ResearchQueryRequest, ResearchRecord,
    DecisionSynthesisRequest, FounderDecisionBrief,
)
from scripts.magic_llm.types import TaskCategory, MagicLLMRequest


class GOIntelligence:
    """
    The Goal Orchestrator's AI intelligence layer.
    All 5 intelligence invocation points are here.
    Every method records a Decision Record to the Goal Register
    BEFORE returning its result (C-059).
    """

    def __init__(self, magic_llm: "MagicLLMPipeline", goal_register: "GoalRegister") -> None:
        self._llm = magic_llm
        self._gr = goal_register

    # ── Point 1: GEOM G-2 ───────────────────────────────────────────────

    async def understand_goal(self, req: GoalUnderstandingRequest) -> GoalUnderstandingRecord:
        """Cat. 9 — Convert raw input into structured Goal Understanding Record."""
        response = await self._llm.invoke(MagicLLMRequest(
            goal_id=req.raw_input[:8],  # provisional until goal_id assigned
            institution_id="INST-013",
            go_authorization_id="internal",  # GO-Intelligence is self-authorized
            task_category=TaskCategory.GOAL_UNDERSTANDING,
            task_description="Convert raw Goal input to structured Understanding Record",
            context_sections=[req.raw_input, str(req.related_goal_ids)],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        ))
        record = GoalUnderstandingRecord(
            record_id=self._gr.next_record_id("UR"),
            goal_id=req.raw_input[:8],
            **response.parsed_artifacts,
        )
        await self._gr.commit(record.__dict__)  # Evidence First — commit before returning
        return record

    # ── Point 2: GEOM G-4 ───────────────────────────────────────────────

    async def plan_routing(self, req: RoutingRequest) -> RoutingDecisionRecord:
        """Cat. 10 — Select optimal Institutions + produce Execution Plan."""
        response = await self._llm.invoke(MagicLLMRequest(
            goal_id=req.goal_id,
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.ROUTING_INTELLIGENCE,
            task_description="Select optimal Institutions and produce Execution Plan",
            context_sections=[
                str(req.goal_classification),
                str(req.available_institutions),
                str(req.performance_history),
                str(req.active_institution_load),
            ],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        ))
        record = RoutingDecisionRecord(
            record_id=self._gr.next_record_id("RDR"),
            goal_id=req.goal_id,
            **response.parsed_artifacts,
        )
        await self._gr.commit(record.__dict__)
        return record

    # ── Point 3: GEOM G-5 (continuous) ──────────────────────────────────

    async def monitor_entry(self, inp: JourneyMonitorInput) -> MonitorSignal:
        """Cat. 11 — Analyse new Goal Register entry for drift/SLA signals."""
        response = await self._llm.invoke(MagicLLMRequest(
            goal_id=inp.goal_id,
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.JOURNEY_MONITOR,
            task_description="Detect drift and SLA risk in new Goal Register entry",
            context_sections=[str(inp.new_record), str(inp.success_criteria)],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        ))
        signal = MonitorSignal(
            record_id=self._gr.next_record_id("MS"),
            goal_id=inp.goal_id,
            **response.parsed_artifacts,
        )
        # Monitor signals go to GO operational log — not main evidence chain
        await self._gr.commit_operational(signal.__dict__)
        return signal

    # ── Point 4: GEOM §10 L2 ─────────────────────────────────────────────

    async def research_query(
        self,
        goal_id: str,
        failure_evidence: dict,
        l1_record_ids: list[str],
    ) -> ResearchRecord:
        """Cat. 12 — L2 Remediation: query external industry knowledge."""
        response = await self._llm.invoke(MagicLLMRequest(
            goal_id=goal_id,
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.RESEARCH_ORCHESTRATION,
            task_description="Query industry knowledge for Goal outcome gap",
            context_sections=[str(failure_evidence), str(l1_record_ids)],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        ))
        record = ResearchRecord(
            record_id=self._gr.next_record_id("RR"),
            goal_id=goal_id,
            **response.parsed_artifacts,
        )
        await self._gr.commit(record.__dict__)
        return record

    # ── Point 5: Founder Escalation ──────────────────────────────────────

    async def synthesise_decision(
        self,
        goal_id: str,
        l1_ids: list[str],
        l2_id: str | None,
        l3_id: str | None,
    ) -> FounderDecisionBrief:
        """Cat. 13 — Assemble 3-option Founder decision brief."""
        response = await self._llm.invoke(MagicLLMRequest(
            goal_id=goal_id,
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.DECISION_SYNTHESIS,
            task_description="Synthesise Founder decision brief from cascade evidence",
            context_sections=[str(l1_ids), str(l2_id), str(l3_id)],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        ))
        brief = FounderDecisionBrief(
            record_id=self._gr.next_record_id("FDB"),
            goal_id=goal_id,
            **response.parsed_artifacts,
        )
        await self._gr.commit(brief.__dict__)
        return brief
```

---

## §5 — Database Schema (`infrastructure/postgres/init/10-goal-orchestrator-performance.sql`)

```sql
-- Implements: architecture/reference/goal-orchestrator/intelligence.md §3 Self-Improvement
-- Constitutional basis: C-069 (Platform Self-Improvement)
-- Schema: institutional

CREATE TABLE institutional.goal_orchestrator_performance (
    id                      BIGSERIAL PRIMARY KEY,
    goal_id                 TEXT NOT NULL,
    goal_type               TEXT NOT NULL,   -- nature classification
    institution_id          TEXT NOT NULL,
    routing_decision_id     TEXT,            -- MDR record_id for Cat. 10 invocation
    -- Routing outcome signals
    delivered_on_sla        BOOLEAN,
    cascade_triggered       BOOLEAN DEFAULT FALSE,
    cascade_level_reached   INTEGER,         -- 1, 2, 3, or NULL if no cascade
    cascade_resolved        BOOLEAN,
    founder_escalated       BOOLEAN DEFAULT FALSE,
    -- Understanding quality
    understanding_accuracy  FLOAT,           -- 0-1: did draft SC match Founder intent?
    clarifications_needed   INTEGER DEFAULT 0,
    -- Research quality (L2)
    research_query_used     BOOLEAN DEFAULT FALSE,
    research_resolution_rate FLOAT,          -- 0-1: did research enable L2 success?
    -- Decision brief quality (escalation)
    founder_asked_followup  BOOLEAN DEFAULT FALSE,  -- did Founder need more info?
    -- Composite routing score (updated daily by C-069 loop)
    routing_score           FLOAT,
    recorded_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_go_perf_inst_type ON institutional.goal_orchestrator_performance
    (institution_id, goal_type);
CREATE INDEX idx_go_perf_goal ON institutional.goal_orchestrator_performance (goal_id);

-- Materialised view: current Institution routing scores per Goal type
CREATE MATERIALIZED VIEW institutional.go_routing_scores AS
SELECT
    institution_id,
    goal_type,
    COUNT(*)                                          AS total_routings,
    AVG(CASE WHEN delivered_on_sla THEN 1.0 ELSE 0.0 END)   AS sla_rate,
    AVG(CASE WHEN NOT cascade_triggered THEN 1.0 ELSE 0.0 END) AS no_cascade_rate,
    AVG(CASE WHEN NOT founder_escalated THEN 1.0 ELSE 0.0 END) AS no_escalation_rate,
    -- Composite score: weighted routing quality
    (AVG(CASE WHEN delivered_on_sla THEN 1.0 ELSE 0.0 END) * 0.50
   + AVG(CASE WHEN NOT cascade_triggered THEN 1.0 ELSE 0.0 END) * 0.35
   + AVG(CASE WHEN NOT founder_escalated THEN 1.0 ELSE 0.0 END) * 0.15)
                                                      AS routing_score
FROM institutional.goal_orchestrator_performance
WHERE recorded_at > NOW() - INTERVAL '48 hours'
GROUP BY institution_id, goal_type;

CREATE UNIQUE INDEX ON institutional.go_routing_scores (institution_id, goal_type);
```

---

## §6 — Integration Boundary Summary

| From | To | Contract | Protocol |
|---|---|---|---|
| Goal Orchestrator (INST-013) | MagicLLM | `MagicLLMRequest` | `await magic_llm.invoke(req)` → `MagicLLMResponse` |
| CascadeHandler | GOIntelligence | `research_query()`, `synthesise_decision()` | async method calls |
| CascadeHandler | Goal Register | `goal_register_writer(record_dict)` | injected callable → returns `record_id` |
| CascadeHandler | Steward Notifier | `steward_notifier(goal_id, brief_id)` | injected callable |
| EEM Step 08 | MagicLLM | `MagicLLMRequest` (Cat. 1-8) | same as above |
| EEM Gate check | CascadeHandler | `cascade_handler.on_gate_fail(evidence)` | async |
| Founder response | CascadeHandler | `cascade_handler.on_founder_decision("a"|"b"|"c")` | Steward Assistant routes |

---

*Produced by Solution Architect (INST-005) — GOAL-002 Phase B*
*For Enterprise Architect review (INST-004).*
*Pending review, these are proposed component contracts — not yet governing.*
