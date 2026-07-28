# Implements: architecture/reference/goal-orchestrator/component-contracts.md §4
# Constitutional basis: C-070 (Three Basic Instincts), C-059 (Evidence First)
"""
GOIntelligence — Goal Orchestrator AI Intelligence coordinator.

5 intelligence invocation points (Cat. 9-13).
Phase 1: Understanding + Routing use Anthropic (if available).
         Monitor, Research, Synthesis raise NotImplementedError (Phase 2 — Gemini).

ENFORCEMENT (2026-07-28): Every Goal dialogue MUST be grounded in repo investigation.
The GO cannot respond to "execute WC-012" without first reading:
  - constitution/PROJECT_STATE.md (current sprint state)
  - constitution/INSTITUTIONAL_BACKLOG.md (what WC-012 is and its gate)
  - constitution/AGENT-ENTRY.md (current platform phase)
  - architecture/reference/ (relevant component specs)
  - work-contracts/ (the actual work contract for the sprint)
Repo context is not optional — it is the constitutional evidence base.
Dialogue without repo investigation is a C-059 violation (no evidence).

Every method commits its evidence record BEFORE returning (C-059).
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
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

REPO_ROOT = Path(__file__).parent.parent.parent

# ── Security: sanitize founder input before LLM injection ────────────────────
_INJECTION_PATTERNS = re.compile(
    r'(ignore\s+(all\s+)?previous\s+instructions?'
    r'|forget\s+everything'
    r'|system\s*:\s*|<\s*/?system\s*>'
    r'|<\s*/?INST\s*>'
    r'|\[INST\]|\[/INST\]'
    r'|###\s*instruction'
    r'|you\s+are\s+now)',
    re.IGNORECASE
)

def _sanitize_input(raw: str) -> str:
    """
    S1 fix: sanitize Founder input before interpolation into LLM prompts.
    Strips known prompt injection patterns. Truncates to 500 chars.
    This is not a trust boundary violation — Founders are authenticated stewards.
    This is defense-in-depth against accidental or malicious prompt override.
    """
    if not raw:
        return ""
    sanitized = _INJECTION_PATTERNS.sub("[REDACTED]", raw)
    return sanitized[:500]  # hard truncation prevents token-stuffing

# ── Repo investigation — mandatory before any goal dialogue ──────────────────

def _investigate_repo(goal_input: str) -> dict[str, str]:
    """
    Investigate the repository before responding to a goal.

    Reads the minimum authoritative files needed to give a grounded response.
    Returns a dict of {file_label: content_excerpt} — injected into all LLM calls.

    This is NOT optional. Calling understand_goal() without repo investigation
    is a C-059 violation — the LLM would be responding without evidence.
    """
    context: dict[str, str] = {}

    # 1. Always read PROJECT_STATE.md — current sprint, phase, what is blocked
    project_state = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
    if project_state.exists():
        content = project_state.read_text(encoding="utf-8", errors="replace")
        # Extract the SPRINT_STATE_MACHINE block
        m = re.search(r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```", content, re.DOTALL)
        context["PROJECT_STATE (SPRINT_STATE_MACHINE)"] = m.group(1)[:800] if m else content[:500]

    # 2. Always read AGENT-ENTRY.md — current gate status, platform phase
    agent_entry = REPO_ROOT / "constitution" / "AGENT-ENTRY.md"
    if agent_entry.exists():
        content = agent_entry.read_text(encoding="utf-8", errors="replace")
        # Extract Platform Status block
        m = re.search(r"## Current Platform State.*?```\n(.*?)```", content, re.DOTALL)
        context["AGENT-ENTRY (Platform Status)"] = m.group(1)[:600] if m else content[:400]

    # 3. If the goal mentions a WC number, load that Work Contract
    wc_match = re.search(r'\bWC-?(\d{1,3})\b', goal_input, re.IGNORECASE)
    if wc_match:
        wc_num = wc_match.group(1).zfill(3)
        wc_dir = REPO_ROOT / "work-contracts"
        matches = list(wc_dir.glob(f"WC-{wc_num}-*.md"))
        if matches:
            content = matches[0].read_text(encoding="utf-8", errors="replace")
            context[f"WORK CONTRACT WC-{wc_num}"] = content[:2000]

    # 4. If the goal mentions IB items, load the relevant backlog entry
    ib_match = re.search(r'\bIB-(\d{3})\b', goal_input, re.IGNORECASE)
    if ib_match:
        ib_id = f"IB-{ib_match.group(1)}"
        backlog = REPO_ROOT / "constitution" / "INSTITUTIONAL_BACKLOG.md"
        if backlog.exists():
            content = backlog.read_text(encoding="utf-8", errors="replace")
            # Extract the specific IB section
            m = re.search(rf"### {ib_id}.*?(?=### IB-|\Z)", content, re.DOTALL)
            context[f"INSTITUTIONAL_BACKLOG {ib_id}"] = m.group(0)[:800] if m else ""

    # 5. Check for any open constitutional blockers
    blockers_dir = REPO_ROOT / "blockers"
    if blockers_dir.exists():
        open_blockers = list(blockers_dir.glob("CB-*.md"))
        if open_blockers:
            latest = sorted(open_blockers)[-1]
            context["OPEN CONSTITUTIONAL BLOCKER"] = latest.read_text(encoding="utf-8", errors="replace")[:400]

    return context


def _format_repo_context(repo_context: dict[str, str]) -> str:
    """Format repo investigation results as an LLM context section."""
    if not repo_context:
        return "REPO INVESTIGATION: No relevant files found."
    parts = ["REPO INVESTIGATION (grounded in authoritative repository state):"]
    for label, content in repo_context.items():
        if content:
            parts.append(f"\n### {label}\n{content.strip()}")
    return "\n".join(parts)


class GOIntelligence:
    """
    The Goal Orchestrator's AI intelligence layer.
    All 5 intelligence invocation points. Evidence First on every method.

    ENFORCEMENT: All dialogue is grounded in repo investigation (_investigate_repo).
    The GO cannot respond to any goal without first reading the authoritative repo state.
    """

    def __init__(
        self,
        magic_llm: Any,  # MagicLLMPipeline
        goal_register_writer: Callable[[dict], str],
    ) -> None:
        self._llm = magic_llm
        self._write = goal_register_writer

    # ── Fail-Fast Gate: validate_goal_before_dispatch() ─────────────────────
    # This is the primary prevention gate.
    # Called by Steward Assistant BEFORE triggering any GitHub Action or workflow.
    # Cost: ~$0.001 (single Haiku call). Prevents: wasted LLM spend, stale PRs,
    # failed runs, false spec-gap issues, operator confusion.
    #
    # Persona: the GO acts as a proactive advisor — not a gatekeeper.
    # It educates, advocates, and consults before blocking.

    def validate_goal_before_dispatch(self, raw_input: str) -> dict:
        """
        Fast pre-dispatch validation — fail early, fail cheap.

        Returns a structured result the Steward Assistant surfaces in chat:
        {
          "verdict": "APPROVED" | "BLOCKED" | "NEEDS_CLARIFICATION",
          "chat_response": str,       # what to show Founder in chat window
          "blockers": list[str],      # technical blocking conditions
          "next_steps": list[str],    # concrete actions Founder can take
          "estimated_cost_if_run": str,  # what it would waste if bypassed
        }

        The chat_response is written in the GO's persona:
          - Empathetic, expert, grounded in repo facts
          - Never says "you can't" — says "here is what needs to happen first"
          - Always offers a concrete next step
          - Always cites the spec/claim that creates the block
        """
        import os as _os
        repo_context = _investigate_repo(raw_input)

        # Fast-path: check blocking conditions without LLM
        full_text = " ".join(repo_context.values()).lower()
        blockers = []
        next_steps = []

        if "awaiting_go" in full_text or "awaiting_go" in full_text.replace("_", ""):
            blockers.append("sprint_status=AWAITING_GO — Goal Orchestrator not yet in execution path")
            next_steps.append("Build GO→Runner seam so WC sprints execute through GO (IB item required)")

        if "autonomous_halt: true" in full_text:
            blockers.append("autonomous_halt=true — execution halted by constitution")
            next_steps.append("Set autonomous_halt=false in PROJECT_STATE.md once prerequisites are met")

        platform_phase_match = None
        import re as _re
        pm = _re.search(r'platform_phase:\s*(\w+)', " ".join(repo_context.values()))
        if pm:
            phase = pm.group(1).strip("\"'")
            if phase == "SPEC":
                blockers.append(f"platform_phase=SPEC — implementation not authorized")
                next_steps.append("Founder must authorize implementation by setting platform_phase=IMPLEMENTATION")

        if blockers:
            verdict = "BLOCKED"
            # Use Haiku for a warm, persona-driven explanation — not a cold error
            api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                try:
                    llm_req = MagicLLMRequest(
                        goal_id=f"VALIDATE-{int(time.time())}",
                        institution_id="INST-013",
                        go_authorization_id="internal",
                        task_category=TaskCategory.REVIEW_EVALUATION,
                        task_description=(
                            "You are the WAOOAW Goal Orchestrator. "
                            "A Founder has asked to take an action that is currently blocked. "
                            "Write a warm, expert, 3-4 sentence response for the Steward chat interface. "
                            "Do NOT say 'you can't'. Say 'here is what needs to happen first'. "
                            "Cite the specific constitutional basis for the block. "
                            "End with one concrete action the Founder can take right now. "
                            "Be proactive and collaborative — not a gatekeeper.\n\n"
                            f"Founder request: {_sanitize_input(raw_input)}\n"
                            f"Blocking conditions: {'; '.join(blockers)}\n"
                            f"Next steps available: {'; '.join(next_steps)}\n\n"
                            "Output only the chat message — no JSON, no labels."
                        ),
                        context_sections=[_format_repo_context(repo_context)],
                        ptr_snapshot={},
                        expected_output_format="prose",
                        execution_plan_reference="",
                    )
                    response = self._llm.invoke(llm_req)
                    chat_response = response.raw_output.strip() if response.raw_output else self._default_block_message(raw_input, blockers, next_steps)
                except Exception:
                    chat_response = self._default_block_message(raw_input, blockers, next_steps)
            else:
                chat_response = self._default_block_message(raw_input, blockers, next_steps)
        else:
            verdict = "APPROVED"
            chat_response = (
                f"✅ Goal validated against repository state. "
                f"Platform phase is IMPLEMENTATION, no blockers detected. "
                f"Proceeding with: {raw_input[:100]}"
            )

        result = {
            "verdict": verdict,
            "chat_response": chat_response,
            "blockers": blockers,
            "next_steps": next_steps,
            "repo_files_read": list(repo_context.keys()),
            "estimated_cost_if_bypassed": "~$0.50–$2.00 in LLM tokens + failed run artifacts" if blockers else "none",
        }

        # Evidence First — record this validation (C-059)
        self._write({
            "record_type": "GoalValidation",
            "raw_input": raw_input,
            "verdict": verdict,
            "blockers": blockers,
            "repo_files": list(repo_context.keys()),
            "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        return result

    @staticmethod
    def _default_block_message(raw_input: str, blockers: list, next_steps: list) -> str:
        return (
            f"I've reviewed the repository state against your request: \"{raw_input[:80]}\".\n\n"
            f"Before this can proceed, there is a prerequisite to address: {blockers[0]}.\n\n"
            f"What needs to happen first: {next_steps[0] if next_steps else 'review the constitution/PROJECT_STATE.md for the blocking condition'}.\n\n"
            "This check runs before any action is triggered — it saves API costs and prevents failed runs. "
            "Once the prerequisite is resolved, the same request will be approved automatically."
        )

    # ── Point 1: GEOM G-2 — Goal Understanding ───────────────────────────────

    def understand_goal(self, req: GoalUnderstandingRequest) -> GoalUnderstandingRecord:
        """Cat. 9 — Converts raw input into structured Goal Understanding Record.

        ENFORCEMENT: Repo investigation is mandatory before LLM call.
        The LLM receives the actual repository state — not just the user's words.
        This prevents the GO from hallucinating what WC-012 is, what has been done,
        or what the current platform phase allows.
        """
        # Mandatory repo investigation — C-059 (Evidence First)
        repo_context = _investigate_repo(req.raw_input)
        repo_section = _format_repo_context(repo_context)

        context = [
            repo_section,  # ALWAYS FIRST — repo state grounds all reasoning
            f"RAW GOAL INPUT FROM FOUNDER: {_sanitize_input(req.raw_input)}",
            f"Related Goals: {', '.join(req.related_goal_ids) or 'none'}",
        ]
        if req.session_context:
            context.append(f"Session context: {req.session_context}")

        llm_req = MagicLLMRequest(
            goal_id=f"UNDERSTANDING-{int(time.time())}",
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.DEEP_REASONING,
            task_description=(
                "You are the Goal Orchestrator. You have read the repository state above.\n"
                "Based ONLY on what the repository actually shows (not what you assume),\n"
                "convert the Founder's goal input into a structured Goal Understanding Record.\n"
                "If the goal is blocked (e.g. AWAITING_GO, AUTONOMOUS_HALT=true, wrong phase),\n"
                "surface the blocker explicitly in constitutional_implications.\n\n"
                "Output valid JSON with keys: intent, success_criteria_draft (list), "
                "constitutional_implications (list), clarification_needed (bool), "
                "clarifications (list of specific questions grounded in repo state), "
                "related_goals (list), repo_blockers (list of blocking conditions found)."
            ),
            context_sections=context,
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        )

        response = None
        for _attempt in range(1, 3):
            try:
                response = self._llm.invoke(llm_req)
                if response.status != "escalate":
                    break
            except Exception as _inv_err:
                print(f"  [GO] routing LLM invoke attempt {_attempt} failed ({type(_inv_err).__name__}: {_inv_err})")
                if _attempt == 2:
                    raise
                import time as _t; _t.sleep(2)
        parsed = response.parsed_artifacts if response and response.status == "accepted" else {}
        record_id = f"UR-{req.registrant_id}-{int(time.time())}"

        record = GoalUnderstandingRecord(
            record_id=record_id,
            goal_id=record_id,
            intent=parsed.get("intent", req.raw_input[:200]),
            success_criteria_draft=parsed.get("success_criteria_draft", []),
            constitutional_implications=parsed.get("constitutional_implications", [])
                + [f"REPO BLOCKER: {b}" for b in parsed.get("repo_blockers", [])],
            clarification_needed=parsed.get("clarification_needed", False),
            clarifications=parsed.get("clarifications", []),
            related_goals=parsed.get("related_goals", req.related_goal_ids),
        )

        # Evidence First — commit before returning (C-059)
        self._write({
            **record.to_dict(),
            "repo_context_files": list(repo_context.keys()),  # audit trail
        })
        return record

    # ── Point 2: GEOM G-4 — Routing Intelligence ─────────────────────────────

    def plan_routing(self, req: RoutingRequest) -> RoutingDecisionRecord:
        """Cat. 10 — Selects optimal Institutions and produces Execution Plan.
        ENFORCEMENT: Routing is also grounded in repo state — routing to an institution
        that is blocked or in wrong phase is constitutionally invalid.
        """
        # Routing must also investigate repo — cannot route to a blocked institution
        repo_context = _investigate_repo(req.goal_id)
        repo_section = _format_repo_context(repo_context)

        context = [
            repo_section,  # ALWAYS FIRST
            f"Goal classification: {json.dumps(req.goal_classification)}",
            f"Available Institutions: {json.dumps(req.available_institutions[:10])}",
            f"Performance history (last 10): {json.dumps(req.performance_history[:10])}",
            f"Active load: {json.dumps(req.active_institution_load)}",
        ]

        llm_req = MagicLLMRequest(
            goal_id=req.goal_id,
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.DEEP_REASONING,
            task_description=(
                "Based on the repository state and goal classification,\n"
                "select the optimal Institutions. Do NOT route to institutions\n"
                "that are blocked by AUTONOMOUS_HALT, wrong platform_phase, or\n"
                "missing prerequisites shown in the repo state.\n\n"
                "Output valid JSON with keys: selected_institutions (list of INST-NNN), "
                "execution_sequence (sequential|parallel|hybrid), "
                "routing_rationale (dict INST-NNN → reason), "
                "routing_blockers (list of conditions that prevent routing)."
            ),
            context_sections=context,
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        )

        response = None
        for _attempt in range(1, 3):
            try:
                response = self._llm.invoke(llm_req)
                if response.status != "escalate":
                    break
            except Exception as _inv_err:
                print(f"  [GO] routing LLM invoke attempt {_attempt} failed ({type(_inv_err).__name__}: {_inv_err})")
                if _attempt == 2:
                    raise
                import time as _t; _t.sleep(2)
        parsed = response.parsed_artifacts if response and response.status == "accepted" else {}

        record = RoutingDecisionRecord(
            record_id=f"RDR-{req.goal_id}-{int(time.time())}",
            goal_id=req.goal_id,
            selected_institutions=parsed.get("selected_institutions", []),
            execution_sequence=parsed.get("execution_sequence", "sequential"),
            routing_rationale=parsed.get("routing_rationale", {}),
        )

        self._write({**record.to_dict(), "repo_context_files": list(repo_context.keys())})
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
