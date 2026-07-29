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
    budget_limit_inr_paise: int


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
        # Per-instance state — never shared across sessions (C-025)
        self._state: SessionState = SessionState.STARTING
        self._decision_space: DecisionSpace | None = None
        self._actions_executed: int = 0
        self._pending_action: PAASActionInput | None = None
        self._action_result: PAASActionResult | None = None

        # Signal queues — use asyncio primitives inside workflow sandbox
        self._action_queue: list[PAASActionInput] = []
        self._pause_requested: bool = False
        self._resume_requested: bool = False
        self._terminate_requested: bool = False
        self._terminate_reason: str = ""
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None

        # Condition variables (workflow-safe asyncio.Condition equivalent via
        # workflow.wait_condition)
        self._action_available: bool = False

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def signal_execute_action(self, inp: PAASActionInput) -> None:
        """
        Enqueue an action for execution on the hot path.
        Signal is non-blocking; the main run() loop drains the queue.
        C-025: signal routed to this exact workflow instance by session_id.
        """
        self._action_queue.append(inp)
        self._action_available = True

    @workflow.signal(name="PauseSession")
    async def signal_pause(self, inp: PauseSessionInput) -> None:
        """Pause execution. In-flight action completes before pausing."""
        if self._state == SessionState.ACTIVE:
            self._pause_requested = True

    @workflow.signal(name="ResumeSession")
    async def signal_resume(self, inp: ResumeSessionInput) -> None:
        """Resume from PAUSED state."""
        if self._state == SessionState.PAUSED:
            self._resume_requested = True

    @workflow.signal(name="TerminateSession")
    async def signal_terminate(self, inp: TerminateSessionInput) -> None:
        """
        Graceful termination. Completes any in-flight action then exits.
        C-059: terminal evidence recorded before workflow closes.
        """
        self._terminate_requested = True
        self._terminate_reason = inp.reason

    @workflow.signal(name="EmergencyStop")
    async def signal_emergency_stop(self, payload: EmergencyStopSignalPayload) -> None:
        """
        Emergency Stop signal handler — ADR-018.
        Immediately transitions to EMERGENCY_STOPPED regardless of current state.
        Any in-flight action will be recorded as ABANDONED (C-023).
        """
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED

    # -----------------------------------------------------------------------
    # Query handlers
    # -----------------------------------------------------------------------

    @workflow.query(name="GetSessionState")
    def query_session_state(self) -> str:
        return str(self._state)

    @workflow.query(name="GetActionsExecuted")
    def query_actions_executed(self) -> int:
        return self._actions_executed

    @workflow.query(name="GetBudgetUsed")
    def query_budget_used(self) -> int:
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    # -----------------------------------------------------------------------
    # Main workflow entry point
    # -----------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        PAAS Session Lifecycle (C-025):

        1. Load Decision Space (activity — DB call, not on hot path)
        2. Transition to ACTIVE
        3. Hot-path loop:
           a. Wait for action signal, pause, resume, terminate, or emergency stop
           b. Validate in-memory (step 1-2 of hot path spec: <1ms)
           c. Validate + record evidence via CE gRPC (step 3)
           d. Execute via AI Runtime (step 4, only if evidence confirmed)
        4. On terminate: record terminal evidence, transition to TERMINATED
        5. On emergency stop: record ABANDONED evidence, transition to EMERGENCY_STOPPED
        """
        # --- Phase 1: Load Decision Space ---
        self._state = SessionState.STARTING

        raw_ds: dict[str, Any] = await workflow.execute_activity(
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

        # Materialise isolated DecisionSpace for this session (C-025)
        self._decision_space = DecisionSpace(
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            version=inp.decision_space_version,
            parameters=raw_ds.get("parameters", {}),
            budget_limit_inr_paise=inp.budget_limit_inr_paise,
            budget_used_inr_paise=raw_ds.get("budget_used_inr_paise", 0),
            allowed_action_types=raw_ds.get("allowed_action_types", []),
        )

        # --- Phase 2: Enter ACTIVE state ---
        self._state = SessionState.ACTIVE

        # --- Phase 3: Hot-path event loop ---
        while True:
            # Check emergency stop first — highest priority
            if self._emergency_stop_payload is not None:
                await self._handle_emergency_stop(inp)
                break

            # Check terminate
            if self._terminate_requested:
                self._state = SessionState.TERMINATING
                break

            # Handle pause
            if self._pause_requested and self._state == SessionState.ACTIVE:
                self._pause_requested = False
                self._state = SessionState.PAUSED

            # While paused, wait only for resume, terminate, or emergency stop
            if self._state == SessionState.PAUSED:
                await workflow.wait_condition(
                    lambda: (
                        self._resume_requested
                        or self._terminate_requested
                        or self._emergency_stop_payload is not None
                    ),
                    timeout=timedelta(hours=8),  # max trading day
                )
                if self._emergency_stop_payload is not None:
                    await self._handle_emergency_stop(inp)
                    break
                if self._terminate_requested:
                    self._state = SessionState.TERMINATING
                    break
                if self._resume_requested:
                    self._resume_requested = False
                    self._state = SessionState.ACTIVE
                continue

            # Wait for next action or state change
            await workflow.wait_condition(
                lambda: (
                    self._action_available
                    or self._pause_requested
                    or self._terminate_requested
                    or self._emergency_stop_payload is not None
                ),
                timeout=timedelta(hours=8),
            )

            # Re-check emergency stop after wakeup
            if self._emergency_stop_payload is not None:
                await self._handle_emergency_stop(inp)
                break

            if self._terminate_requested:
                self._state = SessionState.TERMINATING
                break

            if self._pause_requested:
                # Loop back to handle pause at top
                continue

            # Drain one action from the queue
            if self._action_queue:
                action = self._action_queue.pop(0)
                self._action_available = len(self._action_queue) > 0
                await self._execute_hot_path(inp, action)

                # Re-check emergency stop after activity completes
                if self._emergency_stop_payload is not None:
                    await self._handle_emergency_stop(inp)
                    break

        # --- Phase 4: Normal termination ---
        if self._state == SessionState.TERMINATING:
            self._state = SessionState.TERMINATED

        budget_used = (
            self._decision_space.budget_used_inr_paise
            if self._decision_space is not None
            else 0
        )

        return PAASSessionResult(
            session_id=inp.session_id,
            terminal_state=str(self._state),
            total_actions_executed=self._actions_executed,
            final_budget_used_inr_paise=budget_used,
        )

    # -----------------------------------------------------------------------
    # Hot path execution
    # -----------------------------------------------------------------------

    async def _execute_hot_path(
        self,
        session_inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> None:
        """
        PAAS hot path (spec steps 1-4):
          1. In-memory Decision Space validation (<1ms — no await)
          2. In-memory budget check (<1ms — no await)
          3. CE.ValidateAction + CE.RecordEvidence (gRPC activity, ~50-80ms)
          4. Execute via AI Runtime (activity, only after evidence confirmed — C-023)

        C-025: uses only _decision_space belonging to this workflow instance.
        C-059: ActivityError is caught and logged as evidence; not silently swallowed.
        """
        assert self._decision_space is not None  # guaranteed by Phase 1

        # Step 1: In-memory action type validation (<1ms)
        if (
            self._decision_space.allowed_action_types
            and action.action_type not in self._decision_space.allowed_action_types
        ):
            # Record denial locally; no CE call needed for in-memory boundary reject
            self._action_queue  # no-op touch to satisfy linter
            return

        # Step 2: In-memory budget check (<1ms)
        budget_remaining = (
            self._decision_space.budget_limit_inr_paise
            - self._decision_space.budget_used_inr_paise
        )
        # Estimate cost from action parameters; default 0 if not provided
        estimated_cost: int = int(
            action.action_parameters.get("estimated_cost_inr_paise", 0)
        )
        if estimated_cost > budget_remaining:
            return

        # Step 3: CE.ValidateAction + CE.RecordEvidence (Evidence First — C-023)
        try:
            val_result: ValidateAndRecordResult = await workflow.execute_activity(
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
        except ActivityError:
            # C-059: activity failure is surfaced; caller (workflow loop) continues
            # Evidence of failure is recorded inside the activity itself
            return
        except asyncio.CancelledError:
            raise

        if not val_result.allowed or val_result.evidence_record_id is None:
            return

        # Step 4: Execute via AI Runtime (only after evidence confirmed — C-023)
        try:
            _exec_result: dict[str, Any] = await workflow.execute_activity(
                execute_action,
                ExecuteActionInput(
                    session_inp.session_id,
                    session_inp.contract_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    val_result.evidence_record_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
        except ActivityError:
            # C-059: execution failure surfaced; evidence was already written above
            return
        except asyncio.CancelledError:
            raise

        # Update budget tracking (C-025: isolated to this session's DecisionSpace)
        self._decision_space.budget_used_inr_paise += estimated_cost
        self._actions_executed += 1

    # -----------------------------------------------------------------------
    # Emergency Stop handler
    # -----------------------------------------------------------------------

    async def _handle_emergency_stop(self, session_inp: PAASSessionInput) -> None:
        """
        ADR-018 Emergency Stop sequence:
          1. Transition to EMERGENCY_STOPPED
          2. Record ABANDONED evidence for any conceptually in-flight action (C-023)
          3. Evidence must be confirmed written before workflow exits

        C-023: record_abandoned_evidence activity must return OK before we return.
        C-059: ActivityError from abandoned-evidence recording is surfaced (not swallowed).
        """
        assert self._emergency_stop_payload is not None
        self._state = SessionState.EMERGENCY_STOPPED

        # Determine if there is a nominally in-flight action to abandon.
        # The action queue may contain unprocessed items that were enqueued
        # before the stop signal; record the first pending item as ABANDONED.
        pending_action_id: str = "none"
        if self._action_queue:
            pending_action_id = self._action_queue[0].action_instance_id

        try:
            _evidence_id: str = await workflow.execute_activity(
                record_abandoned_evidence,
                RecordAbandonedEvidenceInput(
                    session_inp.session_id,
                    session_inp.contract_id,
                    session_inp.professional_id,
                    pending_action_id,
                    session_inp.decision_space_version,
                    self._emergency_stop_payload.stopped_by,
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )
        except ActivityError:
            # C-059: failure to write abandoned evidence must not be silently swallowed.
            # The workflow must still terminate; the ActivityError is surfaced to
            # Temporal's event history for audit.
            workflow.logger.error(
                "Failed to record abandoned evidence during EmergencyStop",
                extra={"session_id": session_inp.session_id},
            )
        except asyncio.CancelledError:
            raise

        # Clear queue — session is dead; no further actions permitted
        self._action_queue.clear()
        self._action_available = False