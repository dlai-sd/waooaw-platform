# Implements: architecture/reference/goal-orchestrator/component-contracts.md §2
# Constitutional basis: C-059 (Traceability), C-069 (Self-Improvement), C-070 (Three Instincts)
"""
GO-Intelligence orchestration types — Category 9-13 record definitions.
All records are committed to the Goal Register before results are returned (C-059).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ── Category 9: Goal Understanding ──────────────────────────────────────────

@dataclass
class GoalUnderstandingRequest:
    """Input to Cat. 9 — converts raw Founder input into structured Goal."""
    raw_input: str
    registrant_id: str                   # INST-NNN or "founder"
    related_goal_ids: list[str] = field(default_factory=list)
    session_context: Optional[str] = None


@dataclass
class GoalUnderstandingRecord:
    """Cat. 9 output — constitutional Goal Understanding Record."""
    record_id: str
    goal_id: str
    record_type: str = "Goal Understanding Record"
    institution_id: str = "INST-013"
    intent: str = ""
    success_criteria_draft: list[dict] = field(default_factory=list)
    constitutional_implications: list[str] = field(default_factory=list)
    clarification_needed: bool = False
    clarifications: list[str] = field(default_factory=list)
    related_goals: list[str] = field(default_factory=list)
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["produced_at"] = self.produced_at.isoformat()
        return d


# ── Category 10: Routing Intelligence ───────────────────────────────────────

@dataclass
class RoutingRequest:
    """Input to Cat. 10 — produces optimal Execution Plan."""
    goal_id: str
    goal_classification: dict            # {scope, nature, risk, urgency}
    understanding_record_id: str
    available_institutions: list[dict]   # OPERATIONAL entries from Institution Registry
    performance_history: list[dict]      # from institutional.go_routing_scores
    active_institution_load: dict        # {inst_id: active_goal_count}


@dataclass
class RoutingDecisionRecord:
    """Cat. 10 output — routing rationale + draft Execution Plan."""
    record_id: str
    goal_id: str
    record_type: str = "Routing Decision Record"
    institution_id: str = "INST-013"
    selected_institutions: list[str] = field(default_factory=list)
    execution_sequence: str = "sequential"
    routing_rationale: dict = field(default_factory=dict)
    cascade_parameters: dict = field(default_factory=lambda: {
        "l1_max_attempts": 3,
        "l2_max_attempts": 2,
        "l3_max_attempts": 1,
    })
    draft_execution_plan_id: str = ""
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["produced_at"] = self.produced_at.isoformat()
        return d


# ── Category 11: Journey Monitor ────────────────────────────────────────────

@dataclass
class JourneyMonitorInput:
    """Input to Cat. 11 — called on every new Goal Register entry."""
    goal_id: str
    new_record: dict
    goal_register_state: dict
    success_criteria: list[dict]
    execution_plan: dict


@dataclass
class MonitorSignal:
    """Cat. 11 output — GO operational log entry (not in main evidence chain)."""
    record_id: str
    goal_id: str
    record_type: str = "Monitor Signal"
    institution_id: str = "INST-013"
    signal_type: str = "NOMINAL"   # NOMINAL|SLA_WARNING|DRIFT_DETECTED|QUALITY_CONCERN
    description: str = ""
    recommended_action: str = ""
    triggered_by_record: str = ""
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["produced_at"] = self.produced_at.isoformat()
        return d


# ── Category 12: Research Query ──────────────────────────────────────────────

@dataclass
class ResearchQueryRequest:
    """Input to Cat. 12 — L2 Remediation research query."""
    goal_id: str
    gap_description: str
    failure_evidence: list[str]          # [record_id of L1 Attempt Records]
    goal_domain: str
    technology_context: dict
    knowledge_domains: list[str] = field(default_factory=list)


@dataclass
class ResearchRecord:
    """Cat. 12 output — external knowledge synthesis committed to Goal Register."""
    record_id: str
    goal_id: str
    record_type: str = "Research Record"
    institution_id: str = "INST-013"
    gap_addressed: str = ""
    sources_queried: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    applicable_patterns: list[str] = field(default_factory=list)
    constitutional_screen_exclusions: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["produced_at"] = self.produced_at.isoformat()
        return d


# ── Category 13: Decision Synthesis ─────────────────────────────────────────

@dataclass
class DecisionSynthesisRequest:
    """Input to Cat. 13 — assembles Founder decision brief."""
    goal_id: str
    understanding_record_id: str
    l1_attempt_record_ids: list[str]
    l2_research_record_id: str
    l3_redesign_record_id: str
    specific_gap: str
    constitutional_context: list[str]


@dataclass
class FounderDecisionBrief:
    """Cat. 13 output — 3-option Founder Evidence Package.
    Delivered via Steward Assistant. Readable in <2 minutes on mobile.
    """
    record_id: str
    goal_id: str
    record_type: str = "Founder Decision Brief"
    institution_id: str = "INST-013"
    headline: str = ""
    goal_summary: str = ""
    what_was_tried: str = ""
    the_gap: str = ""
    option_a: dict = field(default_factory=dict)  # scope reduction
    option_b: dict = field(default_factory=dict)  # architectural redesign
    option_c: dict = field(default_factory=dict)  # goal suspension
    constitutional_note: str = ""
    assembled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["assembled_at"] = d["assembled_at"].isoformat()
        return d
