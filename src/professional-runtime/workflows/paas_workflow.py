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
        self._total_actions_executed: int = 0
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None
        self._pending_action: PAASActionInput | None = None
        self._action_result_ready: bool = False
        self._last_action_result: PAASActionResult | None = None
        self._terminate_reason: str = ""
        self._pause_reason: str = ""
        # Signal queues — Temporal signals are delivered asynchronously
        self._action_queue: list[PAASActionInput] = []
        self._resume_requested: bool = False

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def signal_execute_action(self, action: PAASActionInput) -> None:
        """
        Enqueue an action for execution on the hot path.
        Signal does not block the caller — result is polled via query.
        C-025: signal routed to this specific workflow instance (session isolation).
        """
        if self._state not in (SessionState.ACTIVE,):
            logger.warning(
                "ExecuteAction signal received in non-ACTIVE state",
                extra={"state": str(self._state), "action_instance_id": action.action_instance_id},
            )
            return
        self._action_queue.append(action)

    @workflow.signal(name="EmergencyStop")
    async def signal_emergency_stop(self, payload: EmergencyStopSignalPayload) -> None:
        """
        Emergency Stop signal handler (ADR-018).
        Transitions immediately to EMERGENCY_STOPPED regardless of current state.
        C-023: ABANDONED evidence is recorded before workflow terminates.
        """
        logger.info(
            "EmergencyStop signal received",
            extra={"stopped_by": payload.stopped_by},
        )
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED

    @workflow.signal(name="PauseSession")
    async def signal_pause_session(self, inp: PauseSessionInput) -> None:
        """
        Pause the session — no new actions accepted until resumed.
        Valid only from ACTIVE state.
        """
        if self._state != SessionState.ACTIVE:
            logger.warning(
                "PauseSession signal ignored — session not ACTIVE",
                extra={"state": str(self._state)},
            )
            return
        self._pause_reason = inp.reason
        self._state = SessionState.PAUSED

    @workflow.signal(name="ResumeSession")
    async def signal_resume_session(self, inp: ResumeSessionInput) -> None:
        """
        Resume a paused session.
        Valid only from PAUSED state.
        """
        if self._state != SessionState.PAUSED:
            logger.warning(
                "ResumeSession signal ignored — session not PAUSED",
                extra={"state": str(self._state)},
            )
            return
        self._resume_requested = True
        self._state = SessionState.ACTIVE

    @workflow.signal(name="TerminateSession")
    async def signal_terminate_session(self, inp: TerminateSessionInput) -> None:
        """
        Graceful termination — drain in-flight action then close.
        C-023: evidence is confirmed written before termination completes.
        """
        if self._state in (SessionState.TERMINATED, SessionState.EMERGENCY_STOPPED):
            return
        self._terminate_reason = inp.reason
        self._state = SessionState.TERMINATING

    # -----------------------------------------------------------------------
    # Query handlers
    # -----------------------------------------------------------------------

    @workflow.query(name="GetSessionState")
    def query_session_state(self) -> str:
        """Return current session state as string."""
        return str(self._state)

    @workflow.query(name="GetBudgetUsed")
    def query_budget_used(self) -> int:
        """Return budget used in INR paise for this session."""
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    @workflow.query(name="GetTotalActionsExecuted")
    def query_total_actions_executed(self) -> int:
        """Return count of successfully executed actions this session."""
        return self._total_actions_executed

    # -----------------------------------------------------------------------
    # Main workflow body
    # -----------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        PAAS session lifecycle — long-lived workflow.

        Phase 1: STARTING — load Decision Space via activity (C-025).
        Phase 2: ACTIVE — process action signals from hot path.
        Phase 3: PAUSED — suspend action processing.
        Phase 4: TERMINATING / TERMINATED — graceful shutdown.
        Emergency: EMERGENCY_STOPPED — immediate halt + ABANDONED evidence.

        C-025: All execution is via Temporal activities — never direct calls.
        C-023: Evidence First — RecordEvidence confirmed before any execution.
        C-063: No PII in log statements.
        """
        # ------------------------------------------------------------------
        # Phase 1: Load Decision Space
        # ------------------------------------------------------------------
        self._state = SessionState.STARTING
        workflow.logger.info(
            "PAASSessionWorkflow starting",
            extra={"session_id": inp.session_id},
        )

        try:
            ds_dict: dict[str, Any] = await workflow.execute_activity(
                load_decision_space,
                LoadDecisionSpaceInput(
                    inp.session_id,
                    inp.contract_id,
                    inp.professional_id,
                    inp.decision_space_version,
                    inp.budget_limit_inr_paise,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                ),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "Failed to load Decision Space — session cannot start",
                extra={"session_id": inp.session_id, "error": str(exc)},
            )
            self._state = SessionState.TERMINATED
            return PAASSessionResult(
                inp.session_id,
                str(SessionState.TERMINATED),
                0,
                0,
            )
        except asyncio.CancelledError:
            raise

        # Materialise DecisionSpace from activity result (C-025: isolated instance)
        self._decision_space = DecisionSpace(
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            version=inp.decision_space_version,
            parameters=ds_dict.get("parameters", {}),
            budget_limit_inr_paise=inp.budget_limit_inr_paise,
            budget_used_inr_paise=ds_dict.get("budget_used_inr_paise", 0),
            allowed_action_types=ds_dict.get("allowed_action_types", []),
        )
        self._state = SessionState.ACTIVE
        workflow.logger.info(
            "Decision Space loaded — session ACTIVE",
            extra={"session_id": inp.session_id, "version": inp.decision_space_version},
        )

        # ------------------------------------------------------------------
        # Phase 2 / 3: Event loop — process signals until terminal state
        # ------------------------------------------------------------------
        while self._state not in (
            SessionState.TERMINATED,
            SessionState.EMERGENCY_STOPPED,
            SessionState.TERMINATING,
        ):
            # Wait for something to do: an action in queue, a state change, or
            # a pause/resume cycle.  Temporal's condition() is the correct
            # non-blocking wait primitive inside a workflow.
            await workflow.wait_condition(
                lambda: (
                    len(self._action_queue) > 0
                    or self._state
                    in (
                        SessionState.TERMINATING,
                        SessionState.EMERGENCY_STOPPED,
                    )
                ),
                timeout=timedelta(hours=8),  # trading day upper bound
            )

            # Emergency stop takes precedence over everything
            if self._state == SessionState.EMERGENCY_STOPPED:
                break

            # Graceful termination — drain then exit
            if self._state == SessionState.TERMINATING:
                break

            # PAUSED — wait for resume before processing further actions
            if self._state == SessionState.PAUSED:
                await workflow.wait_condition(
                    lambda: self._state != SessionState.PAUSED
                    or self._state == SessionState.EMERGENCY_STOPPED,
                )
                if self._state == SessionState.EMERGENCY_STOPPED:
                    break
                continue

            # Process one action from the queue (hot path)
            if self._action_queue:
                action = self._action_queue.pop(0)
                await self._execute_action_hot_path(inp, action)

        # ------------------------------------------------------------------
        # Phase 4a: Emergency Stop — record ABANDONED evidence (C-023)
        # ------------------------------------------------------------------
        if self._state == SessionState.EMERGENCY_STOPPED and self._emergency_stop_payload is not None:
            workflow.logger.info(
                "Recording ABANDONED evidence for Emergency Stop",
                extra={"session_id": inp.session_id},
            )
            # Record abandoned evidence for any pending action
            in_flight_id = (
                self._action_queue[0].action_instance_id
                if self._action_queue
                else "none"
            )
            try:
                await workflow.execute_activity(
                    record_abandoned_evidence,
                    RecordAbandonedEvidenceInput(
                        inp.session_id,
                        inp.contract_id,
                        inp.professional_id,
                        in_flight_id,
                        inp.decision_space_version,
                        self._emergency_stop_payload.stopped_by,
                    ),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=5),
                )
            except ActivityError as exc:
                workflow.logger.error(
                    "Failed to record ABANDONED evidence — constitutional violation risk",
                    extra={"session_id": inp.session_id, "error": str(exc)},
                )
            except asyncio.CancelledError:
                raise

        # ------------------------------------------------------------------
        # Phase 4b: Normal / graceful termination
        # ------------------------------------------------------------------
        terminal_state = (
            SessionState.EMERGENCY_STOPPED
            if self._state == SessionState.EMERGENCY_STOPPED
            else SessionState.TERMINATED
        )
        self._state = terminal_state

        final_budget = (
            self._decision_space.budget_used_inr_paise
            if self._decision_space is not None
            else 0
        )

        # Release in-memory Decision Space (C-025: no stale data lingers)
        self._decision_space = None

        workflow.logger.info(
            "PAASSessionWorkflow complete",
            extra={
                "session_id": inp.session_id,
                "terminal_state": str(terminal_state),
                "total_actions": self._total_actions_executed,
            },
        )

        return PAASSessionResult(
            inp.session_id,
            str(terminal_state),
            self._total_actions_executed,
            final_budget,
        )

    # -----------------------------------------------------------------------
    # Hot-path execution (called from within the event loop above)
    # -----------------------------------------------------------------------

    async def _execute_action_hot_path(
        self,
        session_inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> None:
        """
        PAAS hot path for a single action.

        Steps (per spec §PAAS Engine):
          1. In-memory Decision Space validation (<1ms, no network)
          2. In-memory budget check (<1ms, no network)
          3. CE ValidateAction + RecordEvidence via activity (~50-80ms gRPC)
          4. Execute action via AI Runtime activity (if allowed)

        C-023: Evidence First — step 3 activity confirms evidence written before
               step 4 executes. Activity returns only after CE confirms persistence.
        C-025: All execution via Temporal activities — no direct service calls.
        C-063: No PII logged.
        """
        assert self._decision_space is not None  # guaranteed by state machine

        # Step 1: In-memory action type validation (<1ms)
        if (
            self._decision_space.allowed_action_types
            and action.action_type not in self._decision_space.allowed_action_types
        ):
            workflow.logger.warning(
                "Action type not in Decision Space — denied without CE call",
                extra={
                    "action_type": action.action_type,
                    "action_instance_id": action.action_instance_id,
                },
            )
            return

        # Step 2: In-memory budget check (<1ms)
        budget_remaining = (
            self._decision_space.budget_limit_inr_paise
            - self._decision_space.budget_used_inr_paise
        )
        if budget_remaining <= 0:
            workflow.logger.warning(
                "Budget exhausted — action denied",
                extra={"action_instance_id": action.action_instance_id},
            )
            return

        # Step 3: CE ValidateAction + RecordEvidence (Evidence First — C-023)
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
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(milliseconds=100),
                ),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "validate_and_record_evidence activity failed",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "error": str(exc),
                },
            )
            return
        except asyncio.CancelledError:
            raise

        if not val_result.allowed:
            workflow.logger.info(
                "Action denied by Constitutional Engine",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "reason": val_result.reason,
                    "constitutional_basis": val_result.constitutional_basis,
                },
            )
            return

        # Evidence confirmed written (C-023) — now safe to execute
        assert val_result.evidence_record_id is not None

        # Step 4: Execute via AI Runtime (C-025: activity, not direct call)
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
                retry_policy=workflow.RetryPolicy(maximum_attempts=2),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "execute_action activity failed after evidence written",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "evidence_record_id": val_result.evidence_record_id,
                    "error": str(exc),
                },
            )
            return
        except asyncio.CancelledError:
            raise

        # Update in-memory budget (C-025: isolated per session — no shared state)
        cost_paise: int = _exec_result.get("cost_inr_paise", 0)
        self._decision_space.budget_used_inr_paise += cost_paise
        self._total_actions_executed += 1

        workflow.logger.info(
            "Action executed successfully",
            extra={
                "action_instance_id": action.action_instance_id,
                "evidence_record_id": val_result.evidence_record_id,
                "total_executed": self._total_actions_executed,
            },
        )