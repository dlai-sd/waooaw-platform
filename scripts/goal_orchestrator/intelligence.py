# Implements: architecture/reference/goal-orchestrator/component-contracts.md §4
# Constitutional basis: C-070 (Three Basic Instincts), C-059 (Evidence First)
"""
GOIntelligence — Goal Orchestrator AI Intelligence coordinator.

5 intelligence invocation points (Cat. 9-13).
Phase 1: Understanding + Routing use Anthropic (if available).
         Monitor, Research, Synthesis raise NotImplementedError (Phase 2 — Gemini).

Every method commits its evidence record BEFORE returning (C-059).
"""
from __future__ import annotations
import json
import time
from typing import Any, Callable, Optional

from scripts.magic_llm.orchestration import (
    FounderDecisionBrief,
    GoalUnderstandingRecord,
    GoalUnderstandingRequest,
    JourneyMonitorInput,
    MonitorSignal,
    ResearchRecord,
    ResearchQueryRequest,
    RoutingDecisionRecord,
    RoutingRequest,
)
from scripts.magic_llm.types import MagicLLMRequest, TaskCategory


class GOIntelligence:
    """
    The Goal Orchestrator's AI intelligence layer.
    All 5 intelligence invocation points. Evidence First on every method.
    """

    def __init__(
        self,
        magic_llm: Any,  # MagicLLMPipeline
        goal_register_writer: Callable[[dict], str],
    ) -> None:
        self._llm = magic_llm
        self._write = goal_register_writer

    # ── Point 1: GEOM G-2 — Goal Understanding ───────────────────────────────

    def understand_goal(self, req: GoalUnderstandingRequest) -> GoalUnderstandingRecord:
        """Cat. 9 — Converts raw input into structured Goal Understanding Record.
        Phase 1: uses Anthropic reasoning model.
        Evidence committed to Goal Register before returning.
        """
        context = [
            req.raw_input,
            f"Related Goals: {', '.join(req.related_goal_ids) or 'none'}",
        ]
        if req.session_context:
            context.append(req.session_context)

        llm_req = MagicLLMRequest(
            goal_id=f"UNDERSTANDING-{int(time.time())}",
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.DEEP_REASONING,  # Phase 1 proxy for Cat. 9
            task_description=(
                "Convert the raw Goal input into a structured Goal Understanding Record.\n"
                "Output valid JSON with keys: intent, success_criteria_draft (list), "
                "constitutional_implications (list), clarification_needed (bool), "
                "clarifications (list), related_goals (list)."
            ),
            context_sections=context,
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        )

        response = self._llm.invoke(llm_req)

        parsed = response.parsed_artifacts if response.status == "accepted" else {}
        record_id = f"UR-{req.registrant_id}-{int(time.time())}"

        record = GoalUnderstandingRecord(
            record_id=record_id,
            goal_id=record_id,
            intent=parsed.get("intent", req.raw_input[:200]),
            success_criteria_draft=parsed.get("success_criteria_draft", []),
            constitutional_implications=parsed.get("constitutional_implications", []),
            clarification_needed=parsed.get("clarification_needed", False),
            clarifications=parsed.get("clarifications", []),
            related_goals=parsed.get("related_goals", req.related_goal_ids),
        )

        # Evidence First — commit before returning (C-059)
        self._write(record.to_dict())
        return record

    # ── Point 2: GEOM G-4 — Routing Intelligence ─────────────────────────────

    def plan_routing(self, req: RoutingRequest) -> RoutingDecisionRecord:
        """Cat. 10 — Selects optimal Institutions and produces Execution Plan.
        Phase 1: uses Anthropic reasoning model.
        """
        context = [
            f"Goal classification: {json.dumps(req.goal_classification)}",
            f"Available Institutions: {json.dumps(req.available_institutions[:10])}",
            f"Performance history (last 10): {json.dumps(req.performance_history[:10])}",
            f"Active load: {json.dumps(req.active_institution_load)}",
        ]

        llm_req = MagicLLMRequest(
            goal_id=req.goal_id,
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.DEEP_REASONING,  # Phase 1 proxy for Cat. 10
            task_description=(
                "Select the optimal set of Institutions and sequence for this Goal.\n"
                "Output valid JSON with keys: selected_institutions (list of INST-NNN), "
                "execution_sequence (sequential|parallel|hybrid), "
                "routing_rationale (dict INST-NNN → reason string)."
            ),
            context_sections=context,
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        )

        response = self._llm.invoke(llm_req)
        parsed = response.parsed_artifacts if response.status == "accepted" else {}

        record = RoutingDecisionRecord(
            record_id=f"RDR-{req.goal_id}-{int(time.time())}",
            goal_id=req.goal_id,
            selected_institutions=parsed.get("selected_institutions", []),
            execution_sequence=parsed.get("execution_sequence", "sequential"),
            routing_rationale=parsed.get("routing_rationale", {}),
        )

        self._write(record.to_dict())
        return record

    # ── Point 3: GEOM G-5 — Journey Monitor ──────────────────────────────────

    def monitor_entry(self, inp: JourneyMonitorInput) -> MonitorSignal:
        """Cat. 11 — Continuous drift and SLA monitoring.
        Phase 2 implementation (Gemini Flash Lite).
        Phase 1: returns NOMINAL signal (monitoring not active).
        """
        signal = MonitorSignal(
            record_id=f"MS-{inp.goal_id}-{int(time.time())}",
            goal_id=inp.goal_id,
            signal_type="NOMINAL",
            description="Phase 1: journey monitoring not yet active (Phase 2 — Gemini)",
            triggered_by_record=inp.new_record.get("record_id", ""),
        )
        # Operational log only — not in main evidence chain
        self._write({"_operational": True, **signal.to_dict()})
        return signal

    # ── Point 4: GEOM §10 L2 — Research Query ────────────────────────────────

    def research_query(
        self,
        goal_id: str,
        failure_evidence: dict,
        l1_record_ids: list[str],
    ) -> ResearchRecord:
        """Cat. 12 — L2 Remediation: external knowledge synthesis.
        Phase 2 implementation (Gemini 2.5 Pro with external knowledge).
        Phase 1: raises NotImplementedError — CascadeHandler skips to L3.
        """
        raise NotImplementedError(
            "Research Query (Cat. 12) requires Phase 2 (Gemini Vertex AI + "
            "external knowledge base integration). CascadeHandler will proceed to L3."
        )

    def expert_informed_redesign(
        self,
        goal_id: str,
        research_record_id: Optional[str],
    ) -> str:
        """L3 redesign — Enterprise Architect revises Engineering Proposal.
        Phase 2: triggers EEM Step 03 restart with research context.
        Phase 1: raises NotImplementedError.
        """
        raise NotImplementedError(
            "Expert-Informed Redesign (L3) requires Phase 2 (EEM Step 03 restart loop). "
            "CascadeHandler will proceed to Founder Escalation."
        )

    # ── Point 5: Founder Escalation — Decision Synthesis ─────────────────────

    def synthesise_decision(
        self,
        goal_id: str,
        l1_ids: list[str],
        l2_id: Optional[str],
        l3_id: Optional[str],
    ) -> FounderDecisionBrief:
        """Cat. 13 — Assembles 3-option Founder decision brief.
        Phase 2: Gemini 2.5 Pro with full evidence package.
        Phase 1: raises NotImplementedError — CascadeHandler uses minimal brief.
        """
        raise NotImplementedError(
            "Decision Synthesis (Cat. 13) requires Phase 2 (Gemini Vertex AI). "
            "CascadeHandler uses a minimal plain-text brief in Phase 1."
        )
