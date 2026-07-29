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
        self._in_flight_action: PAASActionInput | None = None

        # Signal queues — Temporal delivers signals to these
        self._action_queue: asyncio.Queue[PAASActionInput] = asyncio.Queue()
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None
        self._pause_requested: bool = False
        self._resume_requested: bool = False
        self._terminate_requested: bool = False

    # ------------------------------------------------------------------
    # Signal handlers (ADR-018: Emergency Stop via Temporal Signal)
    # ------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def signal_execute_action(self, action: PAASActionInput) -> None:
        """Enqueue an action for hot-path execution."""
        await self._action_queue.put(action)

    @workflow.signal(name="EmergencyStop")
    async def signal_emergency_stop(self, payload: EmergencyStopSignalPayload) -> None:
        """
        ADR-018: Emergency Stop signal. Sets state immediately, unblocks run loop.
        The workflow halts, records ABANDONED evidence, then terminates.
        """
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED

    @workflow.signal(name="Pause")
    async def signal_pause(self) -> None:
        """Pause the session — no new actions processed until Resume."""
        self._pause_requested = True

    @workflow.signal(name="Resume")
    async def signal_resume(self) -> None:
        """Resume a paused session."""
        self._resume_requested = True
        self._pause_requested = False

    @workflow.signal(name="Terminate")
    async def signal_terminate(self) -> None:
        """Graceful termination — drain in-flight action then stop."""
        self._terminate_requested = True

    # ------------------------------------------------------------------
    # Query handlers
    # ------------------------------------------------------------------

    @workflow.query(name="GetState")
    def query_state(self) -> str:
        return self._state.value

    @workflow.query(name="GetActionsExecuted")
    def query_actions_executed(self) -> int:
        return self._actions_executed

    @workflow.query(name="GetBudgetUsed")
    def query_budget_used(self) -> int:
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    # ------------------------------------------------------------------
    # Main workflow run
    # ------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        PAAS Session lifecycle — all professional execution is via this workflow (C-025).
        Every action execution is preceded by CE.RecordEvidence (C-023).
        No PII in log statements (C-063).
        """
        # ── Phase 1: Load Decision Space ──────────────────────────────
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
                retry_policy=workflow.RetryPolicy(maximum_attempts=3),
            )
        except CancelledError:
            raise
        except ActivityError as exc:
            workflow.logger.error(
                "Decision Space load failed — session cannot start",
                extra={"context": {"session_id": inp.session_id}},
            )
            # Re-raise: no execution without validated Decision Space (C-025)
            raise

        # Reconstruct isolated Decision Space from serialised activity result
        self._decision_space = DecisionSpace(
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            version=inp.decision_space_version,
            parameters=raw_ds.get("parameters", {}),
            budget_limit_inr_paise=inp.budget_limit_inr_paise,
            budget_used_inr_paise=raw_ds.get("budget_used_inr_paise", 0),
            allowed_action_types=raw_ds.get("allowed_action_types", []),
        )
        self._state = SessionState.ACTIVE

        # ── Phase 2: Event loop ───────────────────────────────────────
        while True:
            # Check Emergency Stop first — highest priority
            if self._state == SessionState.EMERGENCY_STOPPED:
                await self._handle_emergency_stop(inp)
                break

            # Check graceful terminate
            if self._terminate_requested and self._in_flight_action is None:
                self._state = SessionState.TERMINATING
                break

            # Handle pause/resume
            if self._pause_requested and self._state == SessionState.ACTIVE:
                self._state = SessionState.PAUSED

            if self._resume_requested and self._state == SessionState.PAUSED:
                self._state = SessionState.ACTIVE
                self._resume_requested = False

            # While paused, wait for a signal
            if self._state == SessionState.PAUSED:
                await workflow.wait_condition(
                    lambda: (
                        self._resume_requested
                        or self._terminate_requested
                        or self._state == SessionState.EMERGENCY_STOPPED
                    ),
                    timeout=timedelta(hours=8),
                )
                continue

            # Process queued actions when ACTIVE
            if self._state == SessionState.ACTIVE:
                try:
                    action = self._action_queue.get_nowait()
                except asyncio.QueueEmpty:
                    # Wait for next signal (action, pause, terminate, emergency stop)
                    await workflow.wait_condition(
                        lambda: (
                            not self._action_queue.empty()
                            or self._pause_requested
                            or self._terminate_requested
                            or self._state == SessionState.EMERGENCY_STOPPED
                        ),
                        timeout=timedelta(hours=8),
                    )
                    continue

                # Execute action through hot path
                await self._execute_hot_path(inp, action)

        # ── Phase 3: Teardown ─────────────────────────────────────────
        terminal = self._state.value
        if self._state != SessionState.EMERGENCY_STOPPED:
            self._state = SessionState.TERMINATED
            terminal = SessionState.TERMINATED.value

        # Release in-memory Decision Space (GC will collect; explicit clear for clarity)
        budget_used = self._decision_space.budget_used_inr_paise if self._decision_space else 0
        self._decision_space = None

        return PAASSessionResult(
            session_id=inp.session_id,
            terminal_state=terminal,
            total_actions_executed=self._actions_executed,
            final_budget_used_inr_paise=budget_used,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_hot_path(
        self,
        inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> None:
        """
        PAAS hot-path steps (AD-005: <50ms total target):
          1. In-memory Decision Space validation (<1ms)
          2. In-memory budget check (<1ms)
          3. CE.ValidateAction + CE.RecordEvidence via activity (~40ms gRPC)
          4. Execute via AI Runtime activity
        C-023: RecordEvidence confirmed before execution returns success.
        C-063: no PII in log statements.
        """
        assert self._decision_space is not None  # guaranteed by state machine

        self._in_flight_action = action

        try:
            # Step 1 — in-memory Decision Space validation
            ds_violation = self._validate_decision_space(action)
            if ds_violation:
                workflow.logger.warning(
                    "Action rejected by Decision Space",
                    extra={"context": {"action_type": action.action_type}},
                )
                self._in_flight_action = None
                return

            # Step 2 — in-memory budget check
            budget_violation = self._check_budget(action)
            if budget_violation:
                workflow.logger.warning(
                    "Action rejected: budget ceiling reached",
                    extra={"context": {"action_type": action.action_type}},
                )
                self._in_flight_action = None
                return

            # Step 3 — CE.ValidateAction + CE.RecordEvidence (C-023)
            try:
                val_result: ValidateAndRecordResult = await workflow.execute_activity(
                    validate_and_record_evidence,
                    ValidateAndRecordInput(
                        inp.session_id,
                        inp.contract_id,
                        inp.professional_id,
                        action.action_type,
                        action.action_parameters,
                        action.action_instance_id,
                        self._decision_space.version,
                        self._decision_space.budget_used_inr_paise,
                        self._decision_space.budget_limit_inr_paise,
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=2),
                )
            except CancelledError:
                raise
            except ActivityError as exc:
                workflow.logger.error(
                    "CE validation/evidence activity failed",
                    extra={"context": {"action_instance_id": action.action_instance_id}},
                )
                # C-059: failure itself is the evidence signal; activity records on retry
                self._in_flight_action = None
                return

            if not val_result.allowed:
                workflow.logger.info(
                    "Action denied by Constitutional Engine",
                    extra={
                        "context": {
                            "action_type": action.action_type,
                            "reason": val_result.reason,
                        }
                    },
                )
                self._in_flight_action = None
                return

            # Step 4 — Execute via AI Runtime (evidence confirmed written — C-023)
            try:
                await workflow.execute_activity(
                    execute_action,
                    ExecuteActionInput(
                        inp.session_id,
                        inp.contract_id,
                        action.action_type,
                        action.action_parameters,
                        action.action_instance_id,
                        val_result.evidence_record_id or "",
                    ),
                    start_to_close_timeout=timedelta(seconds=45),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=2),
                )
            except CancelledError:
                raise
            except ActivityError as exc:
                workflow.logger.error(
                    "Action execution activity failed",
                    extra={"context": {"action_instance_id": action.action_instance_id}},
                )
                # C-059: activity-level evidence already written; log only
                self._in_flight_action = None
                return

            # Update budget tracking (in-memory — no DB call on hot path)
            cost = action.action_parameters.get("estimated_cost_inr_paise", 0)
            if isinstance(cost, int):
                self._decision_space.budget_used_inr_paise += cost

            self._actions_executed += 1

        except CancelledError:
            # Propagate — Temporal must handle cancellation correctly
            raise
        finally:
            self._in_flight_action = None

    async def _handle_emergency_stop(self, inp: PAASSessionInput) -> None:
        """
        ADR-018 Emergency Stop handler.
        1. Halt in-flight activity (Temporal cancellation handles this via CancelledError above)
        2. Record ABANDONED evidence for any in-flight action (C-023)
        3. Terminate workflow
        AD-001: total CE contribution ≤100ms budget.
        C-063: no PII in logs.
        """
        payload = self._emergency_stop_payload
        stopped_by = payload.stopped_by if payload else "unknown"

        if self._in_flight_action is not None:
            try:
                await workflow.execute_activity(
                    record_abandoned_evidence,
                    RecordAbandonedEvidenceInput(
                        inp.session_id,
                        inp.contract_id,
                        inp.professional_id,
                        self._in_flight_action.action_instance_id,
                        self._decision_space.version if self._decision_space else "unknown",
                        stopped_by,
                    ),
                    start_to_close_timeout=timedelta(seconds=5),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=3),
                )
            except CancelledError:
                raise
            except ActivityError:
                workflow.logger.error(
                    "Failed to record ABANDONED evidence on Emergency Stop",
                    extra={"context": {"session_id": inp.session_id}},
                )
                # C-059: log is the evidence of the failure; do not suppress

        workflow.logger.info(
            "PAAS session terminated by Emergency Stop",
            extra={"context": {"session_id": inp.session_id}},
        )

    def _validate_decision_space(self, action: PAASActionInput) -> bool:
        """
        Step 1 hot path: in-memory Decision Space check (<1ms).
        Returns True if there is a violation (action should be rejected).
        C-025: isolated per-session; no shared state.
        """
        ds = self._decision_space
        if ds is None:
            return True  # No Decision Space loaded — reject

        allowed = ds.allowed_action_types
        if allowed and action.action_type not in allowed:
            return True  # Action type not in licensed Decision Space

        return False

    def _check_budget(self, action: PAASActionInput) -> bool:
        """
        Step 2 hot path: in-memory budget ceiling check (<1ms).
        Returns True if budget ceiling would be breached.
        Budget fields: budget_limit_inr_paise, budget_used_inr_paise, estimated_cost_inr_paise.
        """
        ds = self._decision_space
        if ds is None:
            return True

        estimated_cost = action.action_parameters.get("estimated_cost_inr_paise", 0)
        if not isinstance(estimated_cost, int):
            estimated_cost = 0

        projected_used = ds.budget_used_inr_paise + estimated_cost
        if projected_used > ds.budget_limit_inr_paise:
            return True  # Ceiling breach

        return False