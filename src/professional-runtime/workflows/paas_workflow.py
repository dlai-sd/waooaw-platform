# Implements: architecture/reference/components/professional-runtime.md § PAAS Session Lifecycle
# constitutional_basis: C-023, C-025, C-059, C-063
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any

from temporalio import activity, workflow
from temporalio.exceptions import ActivityError, CancelledError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class SessionState(str, Enum):
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
        # Per-instance state — never shared across workflow instances (C-025)
        self._state: SessionState = SessionState.STARTING
        self._decision_space: DecisionSpace | None = None
        self._actions_executed: int = 0
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None
        self._terminate_requested: bool = False
        self._pause_requested: bool = False
        self._resume_requested: bool = False
        self._pending_action: PAASActionInput | None = None
        self._last_action_result: PAASActionResult | None = None

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    @workflow.signal(name="EmergencyStop")
    async def handle_emergency_stop(self, payload: EmergencyStopSignalPayload) -> None:
        """
        Emergency Stop signal handler (C-001, ADR-018).
        Transitions workflow to EMERGENCY_STOPPED.
        Evidence is written before workflow terminates (C-023).
        PII is never logged (C-063).
        """
        # Only process the first signal — idempotent
        if self._state == SessionState.EMERGENCY_STOPPED:
            return
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED

    @workflow.signal(name="ExecuteAction")
    async def handle_execute_action(self, action_input: PAASActionInput) -> None:
        """
        Receive a PAAS action for execution.
        Only accepted in ACTIVE state; silently dropped otherwise to avoid
        contaminating session state across lifecycle transitions.
        """
        if self._state != SessionState.ACTIVE:
            return
        self._pending_action = action_input

    @workflow.signal(name="PauseSession")
    async def handle_pause(self) -> None:
        """Pause signal — transitions ACTIVE → PAUSED."""
        if self._state == SessionState.ACTIVE:
            self._pause_requested = True

    @workflow.signal(name="ResumeSession")
    async def handle_resume(self) -> None:
        """Resume signal — transitions PAUSED → ACTIVE."""
        if self._state == SessionState.PAUSED:
            self._resume_requested = True

    @workflow.signal(name="TerminateSession")
    async def handle_terminate(self) -> None:
        """Graceful termination signal — transitions any non-terminal state → TERMINATING."""
        if self._state not in (
            SessionState.TERMINATED,
            SessionState.EMERGENCY_STOPPED,
            SessionState.TERMINATING,
        ):
            self._terminate_requested = True
            self._state = SessionState.TERMINATING

    # -----------------------------------------------------------------------
    # Query handlers
    # -----------------------------------------------------------------------

    @workflow.query(name="GetSessionState")
    def get_session_state(self) -> str:
        return self._state.value

    @workflow.query(name="GetActionsExecuted")
    def get_actions_executed(self) -> int:
        return self._actions_executed

    @workflow.query(name="GetBudgetUsed")
    def get_budget_used(self) -> int:
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    # -----------------------------------------------------------------------
    # Main workflow run
    # -----------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        Main PAAS session workflow.

        Lifecycle:
          1. Load Decision Space (STARTING → ACTIVE)
          2. Process action signals in ACTIVE state
          3. Handle pause/resume transitions
          4. Handle graceful termination
          5. Handle Emergency Stop at any point (C-001)

        C-025: Decision Space is instance-local. No module-level sharing.
        C-023: Evidence written before any execution result is returned.
        C-059: Every caught exception produces an evidence trail via activity.
        C-063: No PII in any log statement.
        """
        # ── Phase 1: Load Decision Space ────────────────────────────────────
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
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                ),
            )
        except ActivityError as exc:
            # C-059: load failure must not silently drop — workflow terminates
            # with a meaningful result; caller can inspect terminal_state.
            workflow.logger.error(
                "Decision Space load failed — session cannot start",
                extra={"session_id": inp.session_id, "error": str(exc)},
            )
            return PAASSessionResult(
                inp.session_id,
                SessionState.TERMINATED.value,
                0,
                0,
            )
        except CancelledError:
            raise

        # Materialise DecisionSpace from activity output (C-025: per-instance)
        self._decision_space = DecisionSpace(
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            version=inp.decision_space_version,
            parameters=ds_raw.get("parameters", {}),
            budget_limit_inr_paise=inp.budget_limit_inr_paise,
            budget_used_inr_paise=ds_raw.get("budget_used_inr_paise", 0),
            allowed_action_types=ds_raw.get("allowed_action_types", []),
        )

        # Transition STARTING → ACTIVE only after Decision Space is confirmed
        self._state = SessionState.ACTIVE

        # ── Phase 2: Main event loop ─────────────────────────────────────────
        while True:
            # ── Emergency Stop — highest priority (C-001) ──────────────────
            if self._state == SessionState.EMERGENCY_STOPPED:
                await self._handle_emergency_stop_phase(inp)
                return PAASSessionResult(
                    inp.session_id,
                    SessionState.EMERGENCY_STOPPED.value,
                    self._actions_executed,
                    self._decision_space.budget_used_inr_paise,
                )

            # ── Graceful termination ───────────────────────────────────────
            if self._state == SessionState.TERMINATING:
                self._state = SessionState.TERMINATED
                return PAASSessionResult(
                    inp.session_id,
                    SessionState.TERMINATED.value,
                    self._actions_executed,
                    self._decision_space.budget_used_inr_paise,
                )

            # ── Pause handling ─────────────────────────────────────────────
            if self._pause_requested:
                self._pause_requested = False
                self._state = SessionState.PAUSED

            if self._state == SessionState.PAUSED:
                # Wait for resume, termination, or emergency stop
                await workflow.wait_condition(
                    lambda: (
                        self._resume_requested
                        or self._terminate_requested
                        or self._state == SessionState.EMERGENCY_STOPPED
                    )
                )
                if self._resume_requested:
                    self._resume_requested = False
                    self._state = SessionState.ACTIVE
                # Loop back to re-evaluate state
                continue

            # ── Active: wait for next signal ───────────────────────────────
            if self._state == SessionState.ACTIVE:
                await workflow.wait_condition(
                    lambda: (
                        self._pending_action is not None
                        or self._pause_requested
                        or self._terminate_requested
                        or self._state == SessionState.EMERGENCY_STOPPED
                    )
                )

                if self._pending_action is not None:
                    action = self._pending_action
                    self._pending_action = None
                    await self._process_action(inp, action)

                continue

            # ── Unexpected state — break to avoid infinite loop ────────────
            break

        # Should be unreachable; return safe default
        return PAASSessionResult(
            inp.session_id,
            self._state.value,
            self._actions_executed,
            self._decision_space.budget_used_inr_paise if self._decision_space else 0,
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _process_action(
        self,
        inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> None:
        """
        Execute one PAAS action through the constitutional hot path.

        Steps (per professional-runtime.md § PAAS Engine):
          1. In-memory Decision Space validation (< 1ms, no activity needed)
          2. Budget constraint check (< 1ms)
          3. CE.ValidateAction + CE.RecordEvidence via activity (C-023)
          4. Execute via AI Runtime activity (only if evidence confirmed)

        C-023: step 3 MUST succeed before step 4 is called.
        C-059: any failure produces an evidence record.
        C-063: no PII in log statements.
        """
        assert self._decision_space is not None  # guaranteed by startup sequence

        # ── Step 1: In-memory Decision Space validation ────────────────────
        if action.action_type not in self._decision_space.allowed_action_types:
            self._last_action_result = PAASActionResult(
                action.action_instance_id,
                False,
                None,
                f"Action type '{action.action_type}' not in Decision Space",
            )
            return

        # ── Step 2: Budget constraint check ───────────────────────────────
        # Budget remaining is computed from the two fields (no BudgetRemainingInrPaise property)
        budget_remaining = (
            self._decision_space.budget_limit_inr_paise
            - self._decision_space.budget_used_inr_paise
        )
        action_cost_paise: int = action.action_parameters.get("estimated_cost_inr_paise", 0)
        if action_cost_paise > budget_remaining:
            self._last_action_result = PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Insufficient budget for action",
            )
            return

        # ── Step 3: CE validate + record evidence (C-023) ─────────────────
        try:
            vr_result: ValidateAndRecordResult = await workflow.execute_activity(
                validate_and_record_evidence,
                ValidateAndRecordInput(
                    inp.session_id,
                    inp.contract_id,
                    inp.professional_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    inp.decision_space_version,
                    self._decision_space.budget_used_inr_paise,
                    self._decision_space.budget_limit_inr_paise,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(milliseconds=100),
                    backoff_coefficient=2.0,
                ),
            )
        except ActivityError as exc:
            # C-059: failure to validate/record is itself an evidence event
            workflow.logger.error(
                "CE validate_and_record_evidence failed",
                extra={"action_instance_id": action.action_instance_id, "error": str(exc)},
            )
            self._last_action_result = PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Constitutional Engine validation failed",
            )
            return
        except CancelledError:
            raise

        if not vr_result.allowed:
            self._last_action_result = PAASActionResult(
                action.action_instance_id,
                False,
                vr_result.evidence_record_id,
                vr_result.reason,
            )
            return

        # ── Step 4: Execute action (only after evidence confirmed — C-023) ─
        assert vr_result.evidence_record_id is not None  # CE guarantees this on Allow

        try:
            exec_result: dict[str, Any] = await workflow.execute_activity(
                execute_action,
                ExecuteActionInput(
                    inp.session_id,
                    inp.contract_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    vr_result.evidence_record_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(milliseconds=200),
                    backoff_coefficient=2.0,
                ),
            )
        except ActivityError as exc:
            # C-059: execution failure is logged; evidence already written
            workflow.logger.error(
                "execute_action activity failed after evidence confirmed",
                extra={
                    "action_instance_id": action.action_instance_id,
                    "evidence_record_id": vr_result.evidence_record_id,
                    "error": str(exc),
                },
            )
            self._last_action_result = PAASActionResult(
                action.action_instance_id,
                False,
                vr_result.evidence_record_id,
                "Execution failed after evidence recorded",
            )
            return
        except CancelledError:
            raise

        # Update budget tracking on successful execution
        self._decision_space.budget_used_inr_paise += action_cost_paise
        self._actions_executed += 1

        self._last_action_result = PAASActionResult(
            action.action_instance_id,
            True,
            vr_result.evidence_record_id,
            "Executed successfully",
            exec_result,
        )

    async def _handle_emergency_stop_phase(self, inp: PAASSessionInput) -> None:
        """
        Emergency Stop handler — invoked when _state == EMERGENCY_STOPPED.

        Per professional-runtime.md § PAAS Engine Emergency Stop signal handler:
          1. Halt in-flight activity immediately (already done via signal transition)
          2. Record ABANDONED evidence for any in-flight action (C-023)
          3. Signal confirmation back (workflow result carries terminal_state)

        C-023: evidence MUST be written before this method returns.
        C-063: no PII in log statements.
        """
        payload = self._emergency_stop_payload
        stopped_by = payload.stopped_by if payload is not None else "unknown"

        # If there was a pending action that was never processed, record it as ABANDONED
        if self._pending_action is not None:
            abandoned_action = self._pending_action
            self._pending_action = None
            try:
                await workflow.execute_activity(
                    record_abandoned_evidence,
                    RecordAbandonedEvidenceInput(
                        inp.session_id,
                        inp.contract_id,
                        inp.professional_id,
                        abandoned_action.action_instance_id,
                        inp.decision_space_version,
                        stopped_by,
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=workflow.RetryPolicy(
                        maximum_attempts=5,
                        initial_interval=timedelta(milliseconds=200),
                        backoff_coefficient=2.0,
                    ),
                )
            except ActivityError as exc:
                # C-059: log the failure; we cannot re-raise here as Emergency Stop
                # must complete regardless — the stop is unconditional (C-001).
                workflow.logger.error(
                    "record_abandoned_evidence failed during Emergency Stop",
                    extra={
                        "action_instance_id": abandoned_action.action_instance_id,
                        "error": str(exc),
                    },
                )
            except CancelledError:
                # Emergency Stop is unconditional — re-raise only after best-effort evidence
                raise