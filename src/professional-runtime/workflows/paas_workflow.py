# Implements: architecture/reference/components/professional-runtime.md § PAAS Session Lifecycle
# constitutional_basis: C-023, C-025, C-059, C-063
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from typing import Any

from temporalio import activity, workflow
from temporalio.exceptions import ActivityError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class SessionState(StrEnum):
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


@dataclass
class DecisionSpace:
    """Isolated per-session Decision Space. Never shared across sessions (C-025)."""

    contract_id: str
    professional_id: str
    version: str
    parameters: dict[str, Any]
    budget_limit_inr_paise: int
    budget_used_inr_paise: int = 0
    allowed_action_types: list[str] = field(default_factory=list)


@dataclass
class PAASSessionInput:
    session_id: str
    contract_id: str
    professional_id: str
    organisation_id: str
    decision_space_version: str
    tenant_id: str
    started_at: str
    budget_limit_inr_paise: int = 0


@dataclass
class PAASActionInput:
    action_type: str
    action_parameters: dict[str, Any]
    action_instance_id: str


@dataclass
class PAASActionResult:
    action_instance_id: str
    allowed: bool
    evidence_record_id: str | None
    reason: str
    executed_content: dict[str, Any] | None = None


@dataclass
class EmergencyStopSignalPayload:
    stopped_by: str
    reason: str


@dataclass
class PAASSessionResult:
    session_id: str
    terminal_state: str
    total_actions_executed: int
    final_budget_used_inr_paise: int


# ---------------------------------------------------------------------------
# Activity input/output types
# ---------------------------------------------------------------------------


@dataclass
class LoadDecisionSpaceInput:
    session_id: str
    contract_id: str
    professional_id: str
    decision_space_version: str
    budget_limit_inr_paise: int


@dataclass
class ValidateAndRecordInput:
    session_id: str
    contract_id: str
    professional_id: str
    action_type: str
    action_parameters: dict[str, Any]
    action_instance_id: str
    decision_space_version: str
    budget_used_inr_paise: int
    budget_limit_inr_paise: int


@dataclass
class ValidateAndRecordResult:
    allowed: bool
    evidence_record_id: str | None
    reason: str
    constitutional_basis: str


@dataclass
class ExecuteActionInput:
    session_id: str
    contract_id: str
    action_type: str
    action_parameters: dict[str, Any]
    action_instance_id: str
    evidence_record_id: str


@dataclass
class RecordAbandonedEvidenceInput:
    session_id: str
    contract_id: str
    professional_id: str
    action_instance_id: str
    decision_space_version: str
    stopped_by: str


@dataclass
class PauseSessionInput:
    session_id: str
    reason: str


@dataclass
class ResumeSessionInput:
    session_id: str


@dataclass
class TerminateSessionInput:
    session_id: str
    reason: str


# ---------------------------------------------------------------------------
# Activity stubs (implementations live in activities/ — declared here for
# workflow.execute_activity references; C-025: all execution via Temporal)
# ---------------------------------------------------------------------------


@activity.defn
async def load_decision_space(inp: LoadDecisionSpaceInput) -> dict[str, Any]:
    """
    Load and validate Decision Space from DB via Constitutional Engine.
    Returns serialised DecisionSpace parameters.
    C-059: any failure is evidence-logged by caller.
    """
    raise NotImplementedError("Implemented in activities/paas_activities.py")


@activity.defn
async def validate_and_record_evidence(inp: ValidateAndRecordInput) -> ValidateAndRecordResult:
    """
    Step 3 of PAAS hot path:
      - Call CE.ValidateAction (gRPC)
      - If ALLOW: call CE.RecordEvidence (Evidence First — C-023)
      - Return decision + evidence_record_id
    C-023: RecordEvidence MUST return OK before this activity returns success.
    """
    raise NotImplementedError("Implemented in activities/paas_activities.py")


@activity.defn
async def execute_action(inp: ExecuteActionInput) -> dict[str, Any]:
    """
    Step 4 of PAAS hot path: execute via AI Runtime.
    Only called after evidence is confirmed written (C-023).
    """
    raise NotImplementedError("Implemented in activities/paas_activities.py")


@activity.defn
async def record_abandoned_evidence(inp: RecordAbandonedEvidenceInput) -> str:
    """
    Record ABANDONED state evidence for any in-flight action on Emergency Stop.
    C-023: evidence written before workflow terminates.
    Returns evidence_record_id.
    """
    raise NotImplementedError("Implemented in activities/paas_activities.py")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


@workflow.defn(name="PAASSessionWorkflow")
class PAASSessionWorkflow:
    """
    Long-lived Temporal workflow representing one active PAAS session.
    Workflow ID == session_id (idempotency key and Emergency Stop routing key — ADR-018).

    Session isolation guarantee (C-025):
      - Decision Space loaded once per workflow instance into _decision_space.
      - No shared module-level state; each workflow run is a separate instance.
      - Temporal worker isolation ensures no cross-session contamination.

    State machine:
      STARTING → ACTIVE → (PAUSED ↔ ACTIVE) → TERMINATING → TERMINATED
      Any state → EMERGENCY_STOPPED (on EmergencyStop signal)
    """

    def __init__(self) -> None:
        # Per-instance state — never shared across sessions (C-025).
        self._state: SessionState = SessionState.STARTING
        self._decision_space: DecisionSpace | None = None
        self._total_actions_executed: int = 0
        self._in_flight_action: PAASActionInput | None = None

        # WC041-04: Skill Runtime session state (ADR-043 §3).
        # Persisted in Temporal workflow state — survives session restart.
        self._locked_artifacts: dict[str, Any] = {}  # skill_id → LockedArtifact
        self._crystallization_complete: dict[str, bool] = {}  # skill_id → bool

        # Signal queues — populated by signal handlers, drained by run().
        self._pending_actions: list[PAASActionInput] = []
        self._pause_requested: bool = False
        self._resume_requested: bool = False
        self._terminate_requested: bool = False
        self._terminate_reason: str = ""
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def signal_execute_action(self, inp: PAASActionInput) -> None:
        """Enqueue a PAAS action for execution on the hot path."""
        if self._state == SessionState.ACTIVE:
            self._pending_actions.append(inp)
        else:
            logger.warning(
                "ExecuteAction signal received in non-ACTIVE state",
                extra={"state": self._state},
            )

    @workflow.signal(name="PauseSession")
    async def signal_pause(self, inp: PauseSessionInput) -> None:
        """Request session pause."""
        if self._state == SessionState.ACTIVE:
            self._pause_requested = True

    @workflow.signal(name="ResumeSession")
    async def signal_resume(self, inp: ResumeSessionInput) -> None:
        """Request session resume from PAUSED state."""
        if self._state == SessionState.PAUSED:
            self._resume_requested = True

    @workflow.signal(name="TerminateSession")
    async def signal_terminate(self, inp: TerminateSessionInput) -> None:
        """Request orderly session termination."""
        self._terminate_requested = True
        self._terminate_reason = inp.reason

    @workflow.signal(name="EmergencyStop")
    async def signal_emergency_stop(self, payload: EmergencyStopSignalPayload | None = None) -> None:
        """
        Emergency Stop signal handler (ADR-018).
        Transitions unconditionally to EMERGENCY_STOPPED.
        The run() loop detects this and halts immediately.
        """
        self._emergency_stop_payload = payload or EmergencyStopSignalPayload(
            stopped_by="constitutional-engine",
            reason="Emergency Stop",
        )
        self._state = SessionState.EMERGENCY_STOPPED

    # -----------------------------------------------------------------------
    # Query handlers
    # -----------------------------------------------------------------------

    @workflow.query(name="GetSessionState")
    def query_session_state(self) -> str:
        """Return current session state string."""
        return str(self._state)

    @workflow.query(name="GetBudgetUsed")
    def query_budget_used(self) -> int:
        """Return budget used in INR paise."""
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    @workflow.query(name="GetTotalActionsExecuted")
    def query_total_actions_executed(self) -> int:
        """Return total actions executed in this session."""
        return self._total_actions_executed

    # -----------------------------------------------------------------------
    # Main workflow run
    # -----------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        PAAS session lifecycle state machine.

        STARTING → load Decision Space (activity)
        ACTIVE   → drain pending action queue, handle pause/terminate/emergency-stop
        PAUSED   → wait for resume or terminate or emergency-stop
        TERMINATING → drain remaining queued actions (or skip on emergency-stop)
        TERMINATED / EMERGENCY_STOPPED → return PAASSessionResult
        """

        # ------------------------------------------------------------------
        # Phase 1: STARTING — load Decision Space
        # ------------------------------------------------------------------
        self._state = SessionState.STARTING

        try:
            raw_ds = await workflow.execute_activity(
                load_decision_space,
                LoadDecisionSpaceInput(
                    inp.session_id,
                    inp.contract_id,
                    inp.professional_id,
                    inp.decision_space_version,
                    inp.budget_limit_inr_paise,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
        except ActivityError:
            logger.error(
                "Failed to load Decision Space during STARTING phase",
                exc_info=True,
                extra={"session_id": inp.session_id},
            )
            # Surface as TERMINATED — CE will record abandonment evidence
            # via the caller; we cannot record here without a decision space.
            return PAASSessionResult(
                inp.session_id,
                str(SessionState.TERMINATED),
                0,
                0,
            )
        except asyncio.CancelledError:
            raise

        # Reconstruct DecisionSpace from serialised activity output
        self._decision_space = DecisionSpace(
            contract_id=raw_ds.get("contract_id", inp.contract_id),
            professional_id=raw_ds.get("professional_id", inp.professional_id),
            version=raw_ds.get("version", inp.decision_space_version),
            parameters=raw_ds.get("parameters", {}),
            budget_limit_inr_paise=raw_ds.get("budget_limit_inr_paise", inp.budget_limit_inr_paise),
            budget_used_inr_paise=raw_ds.get("budget_used_inr_paise", 0),
            allowed_action_types=raw_ds.get("allowed_action_types", []),
        )

        # Emergency stop may have arrived during startup
        if self._emergency_stop_payload is not None:
            return await self._handle_emergency_stop(inp)

        self._state = SessionState.ACTIVE

        # ------------------------------------------------------------------
        # Phase 2: ACTIVE — main event loop
        # ------------------------------------------------------------------
        while True:
            # Priority 1: Emergency Stop (unconditional)
            if self._emergency_stop_payload is not None:
                return await self._handle_emergency_stop(inp)

            # Priority 2: Terminate request
            if self._terminate_requested:
                self._state = SessionState.TERMINATING
                break

            # Priority 3: Pause request
            if self._pause_requested and self._state == SessionState.ACTIVE:
                self._pause_requested = False
                self._state = SessionState.PAUSED

                # Wait for resume or terminate or emergency-stop
                await workflow.wait_condition(
                    lambda: self._resume_requested or self._terminate_requested or self._emergency_stop_payload is not None
                )

                if self._emergency_stop_payload is not None:
                    return await self._handle_emergency_stop(inp)

                if self._terminate_requested:
                    self._state = SessionState.TERMINATING
                    break

                # Resume
                self._resume_requested = False
                self._state = SessionState.ACTIVE
                continue

            # Priority 4: Drain pending action queue
            if self._pending_actions:
                action = self._pending_actions.pop(0)
                await self._execute_paas_action(inp, action)
                continue

            # Nothing pending — yield to Temporal scheduler and wait for
            # any of: new action, pause, terminate, or emergency-stop.
            await workflow.wait_condition(
                lambda: (
                    bool(self._pending_actions)
                    or self._pause_requested
                    or self._terminate_requested
                    or self._emergency_stop_payload is not None
                )
            )

        # ------------------------------------------------------------------
        # Phase 3: TERMINATING — drain any remaining queued actions then end
        # ------------------------------------------------------------------
        self._state = SessionState.TERMINATING

        # Drain remaining actions before terminating (orderly shutdown)
        while self._pending_actions:
            if self._emergency_stop_payload is not None:
                return await self._handle_emergency_stop(inp)
            action = self._pending_actions.pop(0)
            await self._execute_paas_action(inp, action)

        self._state = SessionState.TERMINATED

        budget_used = self._decision_space.budget_used_inr_paise if self._decision_space is not None else 0
        return PAASSessionResult(
            inp.session_id,
            str(SessionState.TERMINATED),
            self._total_actions_executed,
            budget_used,
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _execute_paas_action(
        self,
        session_inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> PAASActionResult:
        """
        PAAS hot path (steps 1-4 per spec):
          1. In-memory Decision Space validation (<1ms — synchronous guard)
          2. In-memory budget check (<1ms — synchronous guard)
          3. CE ValidateAction + RecordEvidence (activity, gRPC, ~50-80ms)
          4. Execute via AI Runtime (activity, only if evidence confirmed)

        C-023: Evidence MUST be written before execution returns success.
        C-025: Execution runs as Temporal activity — never direct call from router.
        """
        assert self._decision_space is not None  # guaranteed by STARTING phase

        self._in_flight_action = action

        # Step 1: In-memory Decision Space validation
        if action.action_type not in self._decision_space.allowed_action_types:
            self._in_flight_action = None
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                f"action_type '{action.action_type}' not in Decision Space",
            )

        # Step 2: In-memory budget check
        budget_remaining = self._decision_space.budget_limit_inr_paise - self._decision_space.budget_used_inr_paise
        if budget_remaining <= 0:
            self._in_flight_action = None
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Budget exhausted",
            )

        # Step 3: CE ValidateAction + RecordEvidence (activity — C-023)
        val_result: ValidateAndRecordResult
        try:
            val_result = await workflow.execute_activity(
                validate_and_record_evidence,
                ValidateAndRecordInput(
                    session_inp.session_id,
                    session_inp.contract_id,
                    session_inp.professional_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    session_inp.decision_space_version,
                    self._decision_space.budget_used_inr_paise,
                    self._decision_space.budget_limit_inr_paise,
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )
        except ActivityError as exc:
            logger.error(
                "validate_and_record_evidence activity failed",
                exc_info=True,
                extra={"action_instance_id": action.action_instance_id},
            )
            self._in_flight_action = None
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                f"CE validation activity error: {exc}",
            )
        except asyncio.CancelledError:
            raise

        if not val_result.allowed:
            self._in_flight_action = None
            return PAASActionResult(
                action.action_instance_id,
                False,
                val_result.evidence_record_id,
                val_result.reason,
            )

        # Step 4: Execute via AI Runtime (C-023: evidence confirmed written above)
        executed_content: dict[str, Any] = {}
        try:
            executed_content = await workflow.execute_activity(
                execute_action,
                ExecuteActionInput(
                    session_inp.session_id,
                    session_inp.contract_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    val_result.evidence_record_id or "",
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
        except ActivityError as exc:
            logger.error(
                "execute_action activity failed after evidence confirmed",
                exc_info=True,
                extra={"action_instance_id": action.action_instance_id},
            )
            self._in_flight_action = None
            return PAASActionResult(
                action.action_instance_id,
                False,
                val_result.evidence_record_id,
                f"Execution activity error: {exc}",
                None,
            )
        except asyncio.CancelledError:
            raise

        self._total_actions_executed += 1

        # Update in-memory budget tracking
        cost_paise = executed_content.get("cost_inr_paise", 0)
        self._decision_space.budget_used_inr_paise += cost_paise

        self._in_flight_action = None
        return PAASActionResult(
            action.action_instance_id,
            True,
            val_result.evidence_record_id,
            "Executed",
            executed_content,
        )

    async def _handle_emergency_stop(
        self,
        session_inp: PAASSessionInput,
    ) -> PAASSessionResult:
        """
        Emergency Stop handler (ADR-018, C-023):
          1. If there is an in-flight action, record ABANDONED evidence via CE.
          2. Transition to EMERGENCY_STOPPED.
          3. Release Decision Space (set to None — C-025 session isolation).
          4. Return terminal result.

        C-023: ABANDONED evidence MUST be written before this method returns.
        """
        payload = self._emergency_stop_payload
        assert payload is not None

        self._state = SessionState.EMERGENCY_STOPPED

        # Record ABANDONED evidence for any in-flight action (C-023)
        if self._in_flight_action is not None:
            in_flight = self._in_flight_action
            try:
                await workflow.execute_activity(
                    record_abandoned_evidence,
                    RecordAbandonedEvidenceInput(
                        session_inp.session_id,
                        session_inp.contract_id,
                        session_inp.professional_id,
                        in_flight.action_instance_id,
                        session_inp.decision_space_version,
                        payload.stopped_by,
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                )
            except ActivityError:
                # C-059: log evidence of the failure; we still terminate.
                logger.error(
                    "record_abandoned_evidence failed during Emergency Stop",
                    exc_info=True,
                    extra={"action_instance_id": in_flight.action_instance_id},
                )
            except asyncio.CancelledError:
                raise

        budget_used = self._decision_space.budget_used_inr_paise if self._decision_space is not None else 0

        # Release Decision Space — C-025 session isolation
        self._decision_space = None

        return PAASSessionResult(
            session_inp.session_id,
            str(SessionState.EMERGENCY_STOPPED),
            self._total_actions_executed,
            budget_used,
        )
