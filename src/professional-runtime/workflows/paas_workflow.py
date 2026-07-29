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
        self._action_result: PAASActionResult | None = None
        self._input: PAASSessionInput | None = None

    # ------------------------------------------------------------------
    # Queries — safe read-only accessors (no side effects)
    # ------------------------------------------------------------------

    @workflow.query
    def get_state(self) -> str:
        """Return current session state. Safe for read-only callers."""
        return self._state.value

    @workflow.query
    def get_actions_executed(self) -> int:
        """Return total actions executed in this session."""
        return self._actions_executed

    @workflow.query
    def get_budget_used_inr_paise(self) -> int:
        """Return budget used so far. Returns 0 if Decision Space not yet loaded."""
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    @workflow.query
    def get_decision_space_version(self) -> str | None:
        """Return loaded Decision Space version, or None if not yet loaded."""
        if self._decision_space is None:
            return None
        return self._decision_space.version

    # ------------------------------------------------------------------
    # Signals — state mutation entry points
    # ------------------------------------------------------------------

    @workflow.signal
    async def emergency_stop(self, payload: EmergencyStopSignalPayload) -> None:
        """
        Emergency Stop signal handler (C-001, ADR-018).
        Sets flag immediately — actual halt occurs in the run loop.
        ⛔ No execution logic here — signals must be non-blocking.
        """
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED

    @workflow.signal
    async def terminate_session(self) -> None:
        """
        Graceful termination signal. Sets flag; run loop drains and exits.
        """
        self._terminate_requested = True

    @workflow.signal
    async def pause_session(self) -> None:
        """
        Pause execution. In-flight activity completes; new actions queued.
        """
        if self._state == SessionState.ACTIVE:
            self._pause_requested = True

    @workflow.signal
    async def resume_session(self) -> None:
        """
        Resume execution from PAUSED state.
        """
        if self._state == SessionState.PAUSED:
            self._resume_requested = True

    @workflow.signal
    async def execute_paas_action(self, action: PAASActionInput) -> None:
        """
        Submit an action for PAAS hot-path execution.
        Only accepted in ACTIVE state; ignored in other states.
        """
        if self._state == SessionState.ACTIVE:
            self._pending_action = action

    # ------------------------------------------------------------------
    # Main workflow entry point
    # ------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        PAAS session lifecycle implementation.

        Phase 1: Load Decision Space (STARTING → ACTIVE)
        Phase 2: Hot-path action loop (ACTIVE, supports PAUSED/RESUME)
        Phase 3: Terminal handling (TERMINATED or EMERGENCY_STOPPED)

        C-025: isolated per-instance state — _decision_space never shared.
        C-023: Evidence First — every execution follows RecordEvidence confirmation.
        C-059: all caught exceptions produce log evidence.
        """
        self._input = inp

        # ----------------------------------------------------------------
        # Phase 1 — Load Decision Space
        # ----------------------------------------------------------------
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
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                ),
            )
        except CancelledError:
            # Workflow cancelled during startup — safe to propagate
            raise
        except ActivityError as exc:
            # C-059: load failure is evidence-logged; session cannot start
            workflow.logger.error(
                "Decision Space load failed — session cannot become ACTIVE",
                extra={"session_id": inp.session_id, "error": str(exc)},
            )
            self._state = SessionState.TERMINATED
            return PAASSessionResult(
                inp.session_id,
                SessionState.TERMINATED.value,
                0,
                0,
            )

        # Deserialise raw_ds into DecisionSpace (C-025: per-instance object)
        self._decision_space = DecisionSpace(
            contract_id=raw_ds.get("contract_id", inp.contract_id),
            professional_id=raw_ds.get("professional_id", inp.professional_id),
            version=raw_ds.get("version", inp.decision_space_version),
            parameters=raw_ds.get("parameters", {}),
            budget_limit_inr_paise=raw_ds.get("budget_limit_inr_paise", inp.budget_limit_inr_paise),
            budget_used_inr_paise=raw_ds.get("budget_used_inr_paise", 0),
            allowed_action_types=raw_ds.get("allowed_action_types", []),
        )

        self._state = SessionState.ACTIVE

        # ----------------------------------------------------------------
        # Phase 2 — Hot-path action loop
        # ----------------------------------------------------------------
        while True:
            # Priority 1: Emergency Stop (C-001 — absolute override)
            if self._state == SessionState.EMERGENCY_STOPPED:
                await self._handle_emergency_stop(inp)
                break

            # Priority 2: Graceful termination
            if self._terminate_requested:
                self._state = SessionState.TERMINATING
                break

            # Priority 3: Pause/resume transitions
            if self._pause_requested:
                self._pause_requested = False
                self._state = SessionState.PAUSED
                # Wait for resume or emergency stop
                await workflow.wait_condition(
                    lambda: (
                        self._resume_requested
                        or self._state == SessionState.EMERGENCY_STOPPED
                        or self._terminate_requested
                    ),
                    timeout=timedelta(hours=8),  # max trading session duration
                )
                if self._state == SessionState.EMERGENCY_STOPPED:
                    await self._handle_emergency_stop(inp)
                    break
                if self._terminate_requested:
                    self._state = SessionState.TERMINATING
                    break
                self._resume_requested = False
                self._state = SessionState.ACTIVE
                continue

            # Priority 4: Process pending action (if any)
            if self._pending_action is not None:
                action = self._pending_action
                self._pending_action = None
                await self._execute_hot_path(inp, action)
                continue

            # No pending work — yield until something arrives
            try:
                await workflow.wait_condition(
                    lambda: (
                        self._pending_action is not None
                        or self._terminate_requested
                        or self._pause_requested
                        or self._state == SessionState.EMERGENCY_STOPPED
                    ),
                    timeout=timedelta(hours=8),
                )
            except asyncio.TimeoutError:
                # Session idle timeout — treat as graceful termination
                workflow.logger.warning(
                    "PAAS session idle timeout — terminating",
                    extra={"session_id": inp.session_id},
                )
                self._state = SessionState.TERMINATING
                break

        # ----------------------------------------------------------------
        # Phase 3 — Terminal cleanup
        # ----------------------------------------------------------------
        if self._state not in (SessionState.EMERGENCY_STOPPED, SessionState.TERMINATED):
            self._state = SessionState.TERMINATED

        assert self._decision_space is not None  # loaded in Phase 1
        return PAASSessionResult(
            inp.session_id,
            self._state.value,
            self._actions_executed,
            self._decision_space.budget_used_inr_paise,
        )

    # ------------------------------------------------------------------
    # Internal helpers (not workflow entry points)
    # ------------------------------------------------------------------

    async def _execute_hot_path(
        self,
        inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> None:
        """
        PAAS hot path — steps 1-4:
          1. In-memory Decision Space check (<1ms, C-025)
          2. Budget constraint check (<1ms)
          3. CE.ValidateAction + CE.RecordEvidence (C-023 Evidence First)
          4. Execute via AI Runtime

        C-023: execution NEVER occurs before evidence is confirmed written.
        C-059: every rejection/failure produces a log evidence entry.
        C-063: PII must not appear in log statements.
        """
        assert self._decision_space is not None

        ds = self._decision_space

        # Step 1 — in-memory Decision Space validation
        if action.action_type not in ds.allowed_action_types:
            workflow.logger.warning(
                "Action type not in Decision Space — rejected",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action.action_instance_id,
                    "action_type": action.action_type,
                },
            )
            self._action_result = PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Action type not permitted by Decision Space",
            )
            return

        # Step 2 — budget constraint check
        budget_remaining = ds.budget_limit_inr_paise - ds.budget_used_inr_paise
        if budget_remaining <= 0:
            workflow.logger.warning(
                "Budget exhausted — action rejected",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action.action_instance_id,
                },
            )
            self._action_result = PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Budget exhausted",
            )
            return

        # Step 3 — CE.ValidateAction + CE.RecordEvidence (C-023)
        try:
            vr_result = await workflow.execute_activity(
                validate_and_record_evidence,
                ValidateAndRecordInput(
                    inp.session_id,
                    inp.contract_id,
                    inp.professional_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    ds.version,
                    ds.budget_used_inr_paise,
                    ds.budget_limit_inr_paise,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(milliseconds=200),
                    backoff_coefficient=2.0,
                ),
            )
        except CancelledError:
            raise
        except ActivityError as exc:
            # C-059: CE call failure is evidence-logged; action not executed
            workflow.logger.error(
                "CE validate_and_record_evidence failed — action not executed",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action.action_instance_id,
                    "error": str(exc),
                },
            )
            self._action_result = PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Constitutional Engine validation unavailable",
            )
            return

        if not vr_result.allowed:
            # CE denied — no execution; evidence already recorded by CE
            workflow.logger.info(
                "CE denied action",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action.action_instance_id,
                    "reason": vr_result.reason,
                },
            )
            self._action_result = PAASActionResult(
                action.action_instance_id,
                False,
                vr_result.evidence_record_id,
                vr_result.reason,
            )
            return

        # Step 4 — Execute via AI Runtime (C-023: only after evidence confirmed)
        assert vr_result.evidence_record_id is not None, (
            "CE allowed action but returned no evidence_record_id — C-023 violation"
        )

        try:
            exec_result = await workflow.execute_activity(
                execute_action,
                ExecuteActionInput(
                    inp.session_id,
                    inp.contract_id,
                    action.action_type,
                    action.action_parameters,
                    action.action_instance_id,
                    vr_result.evidence_record_id,
                ),
                start_to_close_timeout=timedelta(seconds=45),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                ),
            )
        except CancelledError:
            raise
        except ActivityError as exc:
            # C-059: execution failure logged; evidence already written
            workflow.logger.error(
                "execute_action activity failed after evidence written",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action.action_instance_id,
                    "evidence_record_id": vr_result.evidence_record_id,
                    "error": str(exc),
                },
            )
            self._action_result = PAASActionResult(
                action.action_instance_id,
                False,
                vr_result.evidence_record_id,
                "Execution failed after evidence record written",
            )
            return

        # Success — update budget and action counter
        ds.budget_used_inr_paise += exec_result.get("cost_inr_paise", 0)
        self._actions_executed += 1

        self._action_result = PAASActionResult(
            action.action_instance_id,
            True,
            vr_result.evidence_record_id,
            "Action executed successfully",
            exec_result,
        )

    async def _handle_emergency_stop(self, inp: PAASSessionInput) -> None:
        """
        Emergency Stop terminal handler (C-001 — absolute override).

        1. Record ABANDONED evidence for any in-flight action (C-023).
        2. Set state to EMERGENCY_STOPPED.
        3. Workflow terminates — no further actions possible.

        C-023: evidence written before workflow exits.
        C-059: any CE failure is logged; Emergency Stop proceeds regardless
               (Scenario 1 of graceful-degradation.md — local halt first).
        """
        payload = self._emergency_stop_payload
        stopped_by = payload.stopped_by if payload is not None else "UNKNOWN"

        # Record abandoned evidence for any action that was in flight
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
                        self._decision_space.version if self._decision_space else "unknown",
                        stopped_by,
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=workflow.RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(milliseconds=500),
                        backoff_coefficient=2.0,
                    ),
                )
            except CancelledError:
                raise
            except ActivityError as exc:
                # C-059: CE failure logged; Emergency Stop proceeds regardless
                # (graceful-degradation.md Scenario 1 — local halt is primary)
                workflow.logger.error(
                    "record_abandoned_evidence failed during Emergency Stop — halt proceeds",
                    extra={
                        "session_id": inp.session_id,
                        "action_instance_id": abandoned_action.action_instance_id,
                        "error": str(exc),
                    },
                )

        self._state = SessionState.EMERGENCY_STOPPED
        workflow.logger.warning(
            "PAAS session Emergency Stopped",
            extra={
                "session_id": inp.session_id,
                "stopped_by": stopped_by,
                "actions_executed": self._actions_executed,
            },
        )