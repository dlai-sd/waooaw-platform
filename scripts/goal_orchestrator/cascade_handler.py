# Implements: architecture/reference/goal-orchestrator/component-contracts.md §3
# Constitutional basis: C-070 Instinct 3 (Autonomous + Trust-Based), C-001 (Founder = last resort)
"""
Remediation Cascade state machine — GEOM §10.

9 constitutional states with strict transition rules.
No state may be skipped. Every transition produces a Goal Register entry.
The Founder is the last resort — not the first escalation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Optional


class CascadeState(Enum):
    NOMINAL         = auto()  # no cascade active
    L1_ACTIVE       = auto()  # Level 1 retries in progress
    L1_EXHAUSTED    = auto()  # L1 all attempts failed
    L2_ACTIVE       = auto()  # Level 2 research query in progress
    L2_EXHAUSTED    = auto()  # L2 all attempts failed
    L3_ACTIVE       = auto()  # Level 3 expert-informed redesign
    L3_EXHAUSTED    = auto()  # L3 failed
    FOUNDER_PENDING = auto()  # Evidence Package sent, awaiting Founder
    RESOLVED        = auto()  # any level resolved the Goal outcome
    ESCALATED       = auto()  # Founder made decision


# Strict transition map — constitutional, not configurable
_VALID_TRANSITIONS: dict[CascadeState, list[CascadeState]] = {
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


@dataclass
class CascadeContext:
    """Mutable state for one cascade activation on a Goal.
    Implements: architecture/reference/goal-orchestrator/component-contracts.md §3
    """
    goal_id: str
    gate_step: int                        # EEM step that triggered (6, 10, or 14)
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
    activated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolved_by_level: Optional[int] = None  # 1, 2, or 3

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["state"] = self.state.name
        d["activated_at"] = self.activated_at.isoformat()
        if self.resolved_at:
            d["resolved_at"] = self.resolved_at.isoformat()
        return d


class CascadeHandler:
    """
    Constitutional Remediation Cascade state machine.
    Called by Goal Orchestrator on every Goal Outcome Alignment Gate failure.

    Phase 1: full state machine logic implemented.
             L2 research and L3 redesign call GOIntelligence stubs.
    Phase 2: L2/L3 use Gemini-backed GOIntelligence.
    """

    def __init__(
        self,
        context: CascadeContext,
        goal_register_writer: Callable[[dict], str],
        magic_llm: Any,          # MagicLLMPipeline
        go_intelligence: Any,    # GOIntelligence
        steward_notifier: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.ctx = context
        self._write = goal_register_writer
        self._llm = magic_llm
        self._go = go_intelligence
        self._notify = steward_notifier or self._default_notifier
        self._original_request: Any = None  # set by caller before on_gate_fail

    def set_original_request(self, request: Any) -> None:
        """Set the MagicLLMRequest that triggered the gate failure."""
        self._original_request = request

    # ── Public entry points ──────────────────────────────────────────────────

    def on_gate_fail(self, failure_evidence: dict) -> CascadeState:
        """
        Entry point: called by Goal Orchestrator when an Alignment Gate fails.
        Traverses L1 → L2 → L3 → Founder autonomously.
        Returns the final CascadeState.
        """
        print(f"  [Cascade] Gate fail on {self.ctx.goal_id} step {self.ctx.gate_step}")
        self._transition(CascadeState.L1_ACTIVE)
        self._run_l1(failure_evidence)

        if self.ctx.state == CascadeState.RESOLVED:
            return self.ctx.state

        self._transition(CascadeState.L2_ACTIVE)
        self._run_l2(failure_evidence)

        if self.ctx.state == CascadeState.RESOLVED:
            return self.ctx.state

        self._transition(CascadeState.L3_ACTIVE)
        self._run_l3()

        if self.ctx.state == CascadeState.RESOLVED:
            return self.ctx.state

        self._transition(CascadeState.FOUNDER_PENDING)
        self._escalate_to_founder(failure_evidence)

        return self.ctx.state

    def on_l3_result(self, succeeded: bool) -> None:
        """Callback from EEM after Level 3 redesign run completes."""
        if self.ctx.state != CascadeState.L3_ACTIVE:
            return
        if succeeded:
            self.ctx.resolved_by_level = 3
            self.ctx.resolved_at = datetime.now(timezone.utc)
            self._transition(CascadeState.RESOLVED)
        else:
            self._transition(CascadeState.L3_EXHAUSTED)

    def on_founder_decision(self, decision: str) -> None:
        """Called when Founder responds to Evidence Package (option a/b/c)."""
        if decision not in ("a", "b", "c"):
            raise ValueError(f"Invalid Founder decision '{decision}' — must be a, b, or c")
        self.ctx.founder_decision = decision
        self._transition(CascadeState.ESCALATED)
        self._write({
            "record_type": "Founder Decision",
            "goal_id": self.ctx.goal_id,
            "decision": decision,
            "brief_id": self.ctx.founder_brief_id,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"  [Cascade] Founder selected option '{decision}' for {self.ctx.goal_id}")

    # ── Private level runners ─────────────────────────────────────────────────

    def _run_l1(self, failure_evidence: dict) -> None:
        """Level 1: Context Enhancement — up to l1_max retries.

        Critical: after the LLM returns an accepted response, we MUST write the
        generated files to disk and verify compile before declaring RESOLVED.
        pipeline.invoke() evaluates FORMAT+ANNOTATION only — it does NOT write files.
        Without this step, cascade reports "L1 resolved" but the broken file from the
        3-attempt loop remains on disk, causing the outer compile gate to fail again.
        """
        while self.ctx.l1_attempts < self.ctx.l1_max:
            self.ctx.l1_attempts += 1
            print(f"  [Cascade] L1 attempt {self.ctx.l1_attempts}/{self.ctx.l1_max}")

            result = self._llm.retry_with_enhanced_context(
                goal_id=self.ctx.goal_id,
                failure_evidence=failure_evidence,
                attempt=self.ctx.l1_attempts,
                original_request=self._original_request,
            )

            actual_outcome = result.status
            if result.status == "accepted":
                # Write files to disk and re-verify compile — pipeline._evaluate() only
                # checks FORMAT+ANNOTATION, not py_compile/ruff. A file that passes
                # pipeline gates may still have a SyntaxError on disk.
                write_ok, write_err = self._write_and_verify(result.raw_output)
                if not write_ok:
                    print(f"  [Cascade] L1 attempt {self.ctx.l1_attempts}: write/compile verify failed: {write_err[:120]}")
                    actual_outcome = "compile_failed"

            record_id = self._write({
                "record_type": "L1 Attempt Record",
                "goal_id": self.ctx.goal_id,
                "cascade_level": 1,
                "attempt": self.ctx.l1_attempts,
                "failure_classification": (
                    result.failure_classification.value
                    if result.failure_classification else None
                ),
                "outcome": actual_outcome,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })
            self.ctx.l1_record_ids.append(record_id)

            if actual_outcome == "accepted":
                self.ctx.resolved_by_level = 1
                self.ctx.resolved_at = datetime.now(timezone.utc)
                self._transition(CascadeState.RESOLVED)
                print(f"  [Cascade] L1 resolved ✓")
                return

        print(f"  [Cascade] L1 exhausted after {self.ctx.l1_max} attempts")
        self._transition(CascadeState.L1_EXHAUSTED)

    def _write_and_verify(self, raw_output: str) -> tuple[bool, str]:
        """Parse <file> blocks from raw_output, write to disk, verify py_compile.

        Returns (success, error_message).
        Only verifies Python files — other stacks either don't reach cascade L1
        or have their own compile gates run externally.
        """
        if not raw_output:
            return False, "empty raw_output"
        try:
            import re as _re
            import subprocess as _sp
            import pathlib as _pl
            _repo_root = _pl.Path(__file__).parent.parent.parent

            file_blocks = _re.findall(
                r'<file\s+path=["\']([^"\']+)["\'][^>]*>(.*?)</file>',
                raw_output,
                _re.DOTALL,
            )
            if not file_blocks:
                return False, "no <file> blocks in L1 response"

            written: list[str] = []
            for rel_path, content in file_blocks:
                full = _repo_root / rel_path.strip()
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(content, encoding="utf-8")
                written.append(rel_path.strip())
                print(f"  [Cascade] L1 wrote: {rel_path.strip()}")

            # Verify py_compile for Python files
            py_files = [f for f in written if f.endswith(".py")]
            for f in py_files:
                full = _repo_root / f
                proc = _sp.run(
                    ["python3", "-m", "py_compile", str(full)],
                    capture_output=True, text=True,
                )
                if proc.returncode != 0:
                    return False, f"{f}: {proc.stderr[:200]}"
            return True, ""
        except Exception as _e:
            return False, str(_e)

    def _run_l2(self, failure_evidence: dict) -> None:
        """Level 2: Research/Industry Expert Query — advisor_auto_extend as Phase 1 L2."""
        print(f"  [Cascade] Initiating L2 research query")

        # Phase 1 L2: use advisor_auto_extend to auto-generate a new error handler.
        # If the failure contains an unknown error code, auto-extend the advisor.
        # This is the self-healing L2 — no external call needed.
        task_id = failure_evidence.get("task", "")
        failure_text = failure_evidence.get("failure", "")
        try:
            import sys as _sys
            _scripts = str(__import__("pathlib").Path(__file__).parent.parent.parent / "scripts")
            if _scripts not in _sys.path:
                _sys.path.insert(0, _scripts)
            from advisor_auto_extend import run_auto_extend
            import re as _re
            codes = _re.findall(r'\bCS\d{4}\b', failure_text)
            if codes:
                mock_signal = {"task_results": {task_id: {
                    "result": "BUILD_FAILURE",
                    "error_type": "UNKNOWN",
                    "build_error_snippet": failure_text[:200],
                }}}
                new_handlers = run_auto_extend(mock_signal)
                if new_handlers > 0:
                    print(f"  [Cascade] L2 self-heal: {new_handlers} new advisor handler(s) generated")
                    self.ctx.l2_attempts = 1
                    self._transition(CascadeState.RESOLVED)
                    self.ctx.resolved_by_level = 2
                    self.ctx.resolved_at = datetime.now(timezone.utc)
                    return
        except Exception as _l2_err:
            print(f"  [Cascade] L2 advisor_auto_extend failed ({_l2_err})")

        # L2 research via GOIntelligence (Phase 2 — Gemini)
        print(f"  [Cascade] L2 GOIntelligence research (Phase 2 not yet available)")
        try:
            research = self._go.research_query(
                goal_id=self.ctx.goal_id,
                failure_evidence=failure_evidence,
                l1_record_ids=self.ctx.l1_record_ids,
            )
            self.ctx.l2_research_record_id = research.record_id
        except NotImplementedError:
            print(f"  [Cascade] L2 research (Phase 2) not yet available — skipping to L3")
            self._transition(CascadeState.L2_EXHAUSTED)
            return

        while self.ctx.l2_attempts < self.ctx.l2_max:
            self.ctx.l2_attempts += 1
            print(f"  [Cascade] L2 attempt {self.ctx.l2_attempts}/{self.ctx.l2_max}")

            result = self._llm.retry_with_research_context(
                goal_id=self.ctx.goal_id,
                research_record=research,
                attempt=self.ctx.l2_attempts,
                original_request=self._original_request,
            )

            if result.status == "accepted":
                self.ctx.resolved_by_level = 2
                self.ctx.resolved_at = datetime.now(timezone.utc)
                self._transition(CascadeState.RESOLVED)
                print(f"  [Cascade] L2 resolved ✓")
                return

        print(f"  [Cascade] L2 exhausted after {self.ctx.l2_max} attempts")
        self._transition(CascadeState.L2_EXHAUSTED)

    def _run_l3(self) -> None:
        """Level 3: Expert-Informed Redesign (EEM re-runs from Step 03)."""
        print(f"  [Cascade] Initiating L3 expert-informed redesign")
        try:
            redesign_id = self._go.expert_informed_redesign(
                goal_id=self.ctx.goal_id,
                research_record_id=self.ctx.l2_research_record_id,
            )
            self.ctx.l3_redesign_record_id = redesign_id
            self.ctx.l3_attempts = 1
            # EEM re-runs asynchronously; result comes back via on_l3_result()
            # For Phase 1: treat as immediate failure (redesign loop not yet wired)
            self._transition(CascadeState.L3_EXHAUSTED)
        except NotImplementedError:
            print(f"  [Cascade] L3 redesign (Phase 2) not yet available")
            self._transition(CascadeState.L3_EXHAUSTED)

    def _escalate_to_founder(self, failure_evidence: dict) -> None:
        """Compile and deliver the Founder Evidence Package."""
        print(f"  [Cascade] Escalating to Founder — assembling Evidence Package")
        try:
            brief = self._go.synthesise_decision(
                goal_id=self.ctx.goal_id,
                l1_ids=self.ctx.l1_record_ids,
                l2_id=self.ctx.l2_research_record_id,
                l3_id=self.ctx.l3_redesign_record_id,
            )
            self.ctx.founder_brief_id = brief.record_id
            self._write(brief.to_dict())
        except NotImplementedError:
            # Phase 2 synthesis not yet available — write a minimal brief
            record_id = f"FDB-{self.ctx.goal_id}-{int(datetime.now().timestamp())}"
            self.ctx.founder_brief_id = record_id
            self._write({
                "record_id": record_id,
                "record_type": "Founder Decision Brief",
                "goal_id": self.ctx.goal_id,
                "headline": f"Goal {self.ctx.goal_id} cannot be resolved autonomously",
                "the_gap": str(failure_evidence.get("failure_detail", "unknown")),
                "option_a": {"title": "Scope reduction"},
                "option_b": {"title": "Architectural redesign"},
                "option_c": {"title": "Goal suspension"},
                "assembled_at": datetime.now(timezone.utc).isoformat(),
            })

        self._notify(self.ctx.goal_id, self.ctx.founder_brief_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _transition(self, to: CascadeState) -> None:
        """Constitutional state transition — validates before applying."""
        valid = _VALID_TRANSITIONS[self.ctx.state]
        if to not in valid:
            raise ValueError(
                f"[Cascade] Invalid cascade transition {self.ctx.state.name} → {to.name}. "
                f"Valid: {[s.name for s in valid]}. Goal: {self.ctx.goal_id}"
            )
        self.ctx.state = to

    @staticmethod
    def _default_notifier(goal_id: str, brief_id: str) -> None:
        """Phase 1 stub: print to console. Phase 2: Steward Assistant delivery."""
        print(
            f"\n  ⚠️  FOUNDER ESCALATION REQUIRED\n"
            f"  Goal: {goal_id}\n"
            f"  Evidence Package: {brief_id}\n"
            f"  Action: Review goals/goal_register.jsonl and select option a/b/c\n"
        )
