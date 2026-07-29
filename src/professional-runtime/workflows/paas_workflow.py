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
        # Per-instance state — never module-level (C-025 session isolation).
        self._state: SessionState = SessionState.STARTING
        self._decision_space: DecisionSpace | None = None
        self._actions_executed: int = 0
        self._pending_action: PAASActionInput | None = None
        self._pending_action_result: PAASActionResult | None = None
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None
        self._pause_reason: str | None = None
        self._terminate_reason: str | None = None
        # Signals use asyncio.Event for deterministic Temporal scheduling.
        self._action_signal_received: asyncio.Event = asyncio.Event()
        self._resume_signal_received: asyncio.Event = asyncio.Event()
        self._terminate_signal_received: asyncio.Event = asyncio.Event()
        self._emergency_stop_signal_received: asyncio.Event = asyncio.Event()

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def signal_execute_action(self, inp: PAASActionInput) -> None:
        """
        Signal: request execution of a PAAS action.
        Only accepted while ACTIVE; ignored (with log) otherwise.
        C-025: each action execution is isolated to this workflow instance.
        """
        if self._state != SessionState.ACTIVE:
            workflow.logger.warning(
                "ExecuteAction signal received in non-ACTIVE state",
                extra={"state": self._state},
            )
            return
        self._pending_action = inp
        self._action_signal_received.set()

    @workflow.signal(name="PauseSession")
    async def signal_pause_session(self, inp: PauseSessionInput) -> None:
        """Signal: pause this session. Only accepted while ACTIVE."""
        if self._state != SessionState.ACTIVE:
            workflow.logger.warning(
                "PauseSession signal received in non-ACTIVE state",
                extra={"state": self._state},
            )
            return
        self._pause_reason = inp.reason
        self._state = SessionState.PAUSED
        workflow.logger.info("Session paused")

    @workflow.signal(name="ResumeSession")
    async def signal_resume_session(self, inp: ResumeSessionInput) -> None:
        """Signal: resume a paused session."""
        if self._state != SessionState.PAUSED:
            workflow.logger.warning(
                "ResumeSession signal received but session is not PAUSED",
                extra={"state": self._state},
            )
            return
        self._pause_reason = None
        self._state = SessionState.ACTIVE
        self._resume_signal_received.set()
        workflow.logger.info("Session resumed")

    @workflow.signal(name="TerminateSession")
    async def signal_terminate_session(self, inp: TerminateSessionInput) -> None:
        """Signal: begin orderly termination of this session."""
        if self._state in (SessionState.TERMINATED, SessionState.EMERGENCY_STOPPED):
            return
        self._terminate_reason = inp.reason
        self._state = SessionState.TERMINATING
        self._terminate_signal_received.set()
        workflow.logger.info("Session termination requested")

    @workflow.signal(name="EmergencyStop")
    async def signal_emergency_stop(self, payload: EmergencyStopSignalPayload) -> None:
        """
        Signal: Emergency Stop. Highest-priority signal.
        Must be handled ≤250ms (AD-001). Temporal signal delivery is near-immediate;
        the handler transitions state atomically before any next activity is scheduled.
        C-023: abandoned evidence is recorded before workflow terminates.
        """
        if self._state == SessionState.EMERGENCY_STOPPED:
            return
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED
        self._emergency_stop_signal_received.set()
        workflow.logger.warning(
            "Emergency Stop signal received — halting session",
        )

    # -----------------------------------------------------------------------
    # Query handlers
    # -----------------------------------------------------------------------

    @workflow.query(name="GetSessionState")
    def query_session_state(self) -> str:
        return str(self._state)

    @workflow.query(name="GetBudgetUsed")
    def query_budget_used(self) -> int:
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    @workflow.query(name="GetActionsExecuted")
    def query_actions_executed(self) -> int:
        return self._actions_executed

    # -----------------------------------------------------------------------
    # Main workflow entrypoint
    # -----------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        Main workflow execution. Follows the PAAS session state machine.

        C-025: inp is the sole source of configuration for this session.
        No module-level or class-level shared state is read.
        C-023: evidence is recorded before any execution returns success.
        C-059: every caught exception produces a log or evidence record.
        """
        workflow.logger.info("PAASSessionWorkflow starting")

        # ------------------------------------------------------------------
        # Phase 1 — STARTING: load Decision Space
        # ------------------------------------------------------------------
        try:
            ds_raw: dict[str, Any] = await workflow.execute_activity(
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
        except ActivityError as exc:
            workflow.logger.error(
                "Failed to load Decision Space — session cannot start",
                extra={"session_id": inp.session_id, "error": str(exc)},
            )
            return PAASSessionResult(
                inp.session_id,
                str(SessionState.TERMINATED),
                0,
                0,
            )

        self._decision_space = DecisionSpace(
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            version=inp.decision_space_version,
            parameters=ds_raw.get("parameters", {}),
            budget_limit_inr_paise=inp.budget_limit_inr_paise,
            budget_used_inr_paise=ds_raw.get("budget_used_inr_paise", 0),
            allowed_action_types=ds_raw.get("allowed_action_types", []),
        )
        self._state = SessionState.ACTIVE
        workflow.logger.info("Decision Space loaded — session ACTIVE")

        # ------------------------------------------------------------------
        # Phase 2 — ACTIVE: process action signals until terminal condition
        # ------------------------------------------------------------------
        while self._state not in (
            SessionState.TERMINATING,
            SessionState.TERMINATED,
            SessionState.EMERGENCY_STOPPED,
        ):
            # Wait for one of: action, resume (if paused), terminate, emergency stop.
            self._action_signal_received.clear()

            await workflow.wait_condition(
                lambda: (
                    self._action_signal_received.is_set()
                    or self._terminate_signal_received.is_set()
                    or self._emergency_stop_signal_received.is_set()
                    or (
                        self._state == SessionState.ACTIVE
                        and self._pending_action is not None
                    )
                )
            )

            # Priority 1: Emergency Stop
            if self._emergency_stop_signal_received.is_set():
                break

            # Priority 2: Terminate
            if self._terminate_signal_received.is_set():
                break

            # Priority 3: Execute pending action (only when ACTIVE)
            if self._state == SessionState.ACTIVE and self._pending_action is not None:
                action = self._pending_action
                self._pending_action = None
                self._action_signal_received.clear()
                await self._execute_single_action(inp, action)

        # ------------------------------------------------------------------
        # Phase 3 — Handle terminal states
        # ------------------------------------------------------------------
        final_budget = (
            self._decision_space.budget_used_inr_paise
            if self._decision_space is not None
            else 0
        )

        if self._state == SessionState.EMERGENCY_STOPPED:
            # Record abandoned evidence for any in-flight action (C-023).
            if self._pending_action is not None:
                assert self._emergency_stop_payload is not None
                await self._record_abandoned(inp, self._pending_action, self._emergency_stop_payload)
            workflow.logger.warning("Session terminated via Emergency Stop")
            return PAASSessionResult(
                inp.session_id,
                str(SessionState.EMERGENCY_STOPPED),
                self._actions_executed,
                final_budget,
            )

        # Orderly termination
        self._state = SessionState.TERMINATED
        workflow.logger.info(
            "Session terminated orderly",
            extra={"reason": self._terminate_reason},
        )
        return PAASSessionResult(
            inp.session_id,
            str(SessionState.TERMINATED),
            self._actions_executed,
            final_budget,
        )

    # -----------------------------------------------------------------------
    # Internal helpers (workflow-deterministic — only workflow.execute_activity
    # and workflow.wait_condition; no direct I/O)
    # -----------------------------------------------------------------------

    async def _execute_single_action(
        self,
        session_inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> None:
        """
        Execute one PAAS action through the full hot path.

        Hot path (AD-005 — <50ms total):
          1. In-memory Decision Space check (<1ms, synchronous)
          2. Budget check (<1ms, synchronous)
          3. CE ValidateAction + RecordEvidence (gRPC, ~50-80ms) — activity
          4. Execute via AI Runtime — activity (only if step 3 allows)

        C-023: execution NEVER proceeds before evidence is confirmed written.
        C-059: every rejection or error produces a log entry (evidence via activity).
        """
        assert self._decision_space is not None

        # Step 1 — in-memory Decision Space check (<1ms, no I/O)
        if action.action_type not in self._decision_space.allowed_action_types:
            workflow.logger.warning(
                "Action type not in Decision Space — denied without CE call",
                extra={"action_instance_id": action.action_instance_id},
            )
            return

        # Step 2 — budget check (<1ms, no I/O)
        # Budget remaining is computed from the two budget fields on DecisionSpace.
        budget_remaining = (
            self._decision_space.budget_limit_inr_paise
            - self._decision_space.budget_used_inr_paise
        )
        if budget_remaining <= 0:
            workflow.logger.warning(
                "Budget exhausted — action denied without CE call",
                extra={"action_instance_id": action.action_instance_id},
            )
            return

        # Step 3 — CE ValidateAction + RecordEvidence (C-023 Evidence First)
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
        except ActivityError as exc:
            # C-059: exception caught without re-raise — log as evidence.
            workflow.logger.error(
                "validate_and_record_evidence activity failed",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "error": str(exc),
                },
            )
            return

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

        # C-023: evidence is confirmed written — proceed to execution.
        assert val_result.evidence_record_id is not None

        # Step 4 — Execute via AI Runtime
        try:
            await workflow.execute_activity(
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
        except ActivityError as exc:
            # C-059: execution failure logged; evidence already written (C-023 preserved).
            workflow.logger.error(
                "execute_action activity failed — evidence record remains intact",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "evidence_record_id": val_result.evidence_record_id,
                    "error": str(exc),
                },
            )
            return

        self._actions_executed += 1
        # Update in-memory budget tracking from Decision Space.
        # Actual cost accounting is owned by CE; we track locally for fast budget check.
        # This is an approximation — CE is authoritative.
        self._decision_space.budget_used_inr_paise += (
            self._decision_space.parameters.get("action_cost_inr_paise", 0)
        )
        workflow.logger.info(
            "Action executed successfully",
            extra={"action_instance_id": action.action_instance_id},
        )

    async def _record_abandoned(
        self,
        session_inp: PAASSessionInput,
        action: PAASActionInput,
        stop_payload: EmergencyStopSignalPayload,
    ) -> None:
        """
        Record ABANDONED evidence for an in-flight action on Emergency Stop.
        C-023: evidence must be written before the workflow terminates.
        C-059: failure to record is logged as evidence of the failure itself.
        """
        try:
            evidence_id: str = await workflow.execute_activity(
                record_abandoned_evidence,
                RecordAbandonedEvidenceInput(
                    session_inp.session_id,
                    session_inp.contract_id,
                    session_inp.professional_id,
                    action.action_instance_id,
                    session_inp.decision_space_version,
                    stop_payload.stopped_by,
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )
            workflow.logger.warning(
                "Abandoned evidence recorded for in-flight action",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "evidence_record_id": evidence_id,
                },
            )
        except ActivityError as exc:
            # C-059: failure to record abandoned evidence must be logged.
            workflow.logger.error(
                "CRITICAL: Failed to record abandoned evidence on Emergency Stop — "
                "C-023 may be violated; manual reconciliation required",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "error": str(exc),
                },
            )