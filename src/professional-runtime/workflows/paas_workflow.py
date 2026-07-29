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
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None
        self._pause_reason: str | None = None
        self._terminate_reason: str | None = None
        # Signals are delivered via asyncio.Event for deterministic waiting
        self._action_ready: asyncio.Event = asyncio.Event()
        self._action_consumed: asyncio.Event = asyncio.Event()
        self._resume_event: asyncio.Event = asyncio.Event()
        self._terminate_event: asyncio.Event = asyncio.Event()
        self._emergency_stop_event: asyncio.Event = asyncio.Event()

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def signal_execute_action(self, inp: PAASActionInput) -> None:
        """Enqueue an action for execution on the hot path."""
        if self._state not in (SessionState.ACTIVE,):
            # Silently drop signals received in non-active states; evidence
            # of dropped signals is implicit in session state (C-059).
            logger.warning(
                "ExecuteAction signal received in non-active state",
                extra={"state": self._state},
            )
            return
        self._pending_action = inp
        self._action_consumed.clear()
        self._action_ready.set()

    @workflow.signal(name="PauseSession")
    async def signal_pause_session(self, inp: PauseSessionInput) -> None:
        """Pause the session — halts new action processing."""
        if self._state != SessionState.ACTIVE:
            return
        self._pause_reason = inp.reason
        self._state = SessionState.PAUSED
        self._resume_event.clear()

    @workflow.signal(name="ResumeSession")
    async def signal_resume_session(self, _inp: ResumeSessionInput) -> None:
        """Resume a paused session."""
        if self._state != SessionState.PAUSED:
            return
        self._state = SessionState.ACTIVE
        self._resume_event.set()

    @workflow.signal(name="TerminateSession")
    async def signal_terminate_session(self, inp: TerminateSessionInput) -> None:
        """Gracefully terminate the session."""
        self._terminate_reason = inp.reason
        self._state = SessionState.TERMINATING
        self._terminate_event.set()

    @workflow.signal(name="EmergencyStop")
    async def signal_emergency_stop(self, inp: EmergencyStopSignalPayload) -> None:
        """
        Emergency Stop signal (ADR-018). Takes priority over all other states.
        Records ABANDONED evidence for any in-flight action before terminating (C-023).
        """
        self._emergency_stop_payload = inp
        self._state = SessionState.EMERGENCY_STOPPED
        self._emergency_stop_event.set()

    # -----------------------------------------------------------------------
    # Queries
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
        PAAS session lifecycle.

        Constitutional guarantees:
          C-025: Entire professional execution runs as Temporal workflow.
          C-023: Evidence recorded before execution; ABANDONED evidence recorded
                 before Emergency Stop terminates workflow.
          C-059: Every caught exception produces a log entry or evidence record.
          C-063: No PII in log statements (session_id only, no professional details).
        """
        workflow.logger.info(
            "PAASSessionWorkflow starting",
            extra={"session_id": inp.session_id},
        )

        # ------------------------------------------------------------------
        # Step 1: Load Decision Space (STARTING → ACTIVE)
        # ------------------------------------------------------------------
        load_input = LoadDecisionSpaceInput(
            inp.session_id,
            inp.contract_id,
            inp.professional_id,
            inp.decision_space_version,
            inp.budget_limit_inr_paise,
        )
        try:
            ds_dict: dict[str, Any] = await workflow.execute_activity(
                load_decision_space,
                load_input,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(maximum_attempts=3),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "Decision Space load failed — session cannot start",
                extra={"session_id": inp.session_id, "error": str(exc)},
            )
            return PAASSessionResult(
                inp.session_id,
                str(SessionState.TERMINATED),
                0,
                0,
            )

        # Materialise the per-instance Decision Space — isolated to this workflow (C-025)
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

        # ------------------------------------------------------------------
        # Step 2: Main event loop — process actions until terminal signal
        # ------------------------------------------------------------------
        while self._state not in (
            SessionState.TERMINATING,
            SessionState.TERMINATED,
            SessionState.EMERGENCY_STOPPED,
        ):
            # Wait for one of: action signal, pause, terminate, emergency stop
            await workflow.wait_condition(
                lambda: (
                    self._action_ready.is_set()
                    or self._terminate_event.is_set()
                    or self._emergency_stop_event.is_set()
                    or self._state == SessionState.PAUSED
                ),
            )

            # Priority 1: Emergency Stop (overrides everything — ADR-018)
            if self._emergency_stop_event.is_set():
                break

            # Priority 2: Terminate signal
            if self._terminate_event.is_set():
                break

            # Priority 3: Paused — wait for resume or terminal signal
            if self._state == SessionState.PAUSED:
                await workflow.wait_condition(
                    lambda: (
                        self._resume_event.is_set()
                        or self._terminate_event.is_set()
                        or self._emergency_stop_event.is_set()
                    ),
                )
                self._resume_event.clear()
                if self._emergency_stop_event.is_set() or self._terminate_event.is_set():
                    break
                # Resumed — loop back to top
                continue

            # Priority 4: Process pending action
            if self._action_ready.is_set() and self._pending_action is not None:
                action = self._pending_action
                self._pending_action = None
                self._action_ready.clear()

                result = await self._execute_hot_path(inp, action)
                self._action_result = result

                if result.allowed and result.executed_content is not None:
                    self._actions_executed += 1

                self._action_consumed.set()

        # ------------------------------------------------------------------
        # Step 3: Handle terminal state
        # ------------------------------------------------------------------
        final_budget = (
            self._decision_space.budget_used_inr_paise
            if self._decision_space is not None
            else 0
        )

        if self._emergency_stop_event.is_set() and self._emergency_stop_payload is not None:
            await self._handle_emergency_stop(inp)
            return PAASSessionResult(
                inp.session_id,
                str(SessionState.EMERGENCY_STOPPED),
                self._actions_executed,
                final_budget,
            )

        # Normal termination
        self._state = SessionState.TERMINATED
        workflow.logger.info(
            "PAASSessionWorkflow terminated normally",
            extra={
                "session_id": inp.session_id,
                "actions_executed": self._actions_executed,
            },
        )
        return PAASSessionResult(
            inp.session_id,
            str(SessionState.TERMINATED),
            self._actions_executed,
            final_budget,
        )

    # -----------------------------------------------------------------------
    # Hot path execution (C-025, C-023)
    # -----------------------------------------------------------------------

    async def _execute_hot_path(
        self,
        session_inp: PAASSessionInput,
        action: PAASActionInput,
    ) -> PAASActionResult:
        """
        PAAS hot path (AD-005: <50ms end-to-end):
          1. In-memory Decision Space validation (<1ms) — steps 1-2
          2. CE.ValidateAction + CE.RecordEvidence via activity (C-023) — step 3
          3. Execute via AI Runtime activity — step 4

        C-023: Evidence is recorded before execution is confirmed.
        C-059: Any error produces a log with context; no bare except.
        C-063: No PII in log statements.
        """
        ds = self._decision_space
        if ds is None:
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Decision Space not loaded",
            )

        # Step 1: In-memory action type check (<1ms)
        if ds.allowed_action_types and action.action_type not in ds.allowed_action_types:
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                f"Action type '{action.action_type}' not in Decision Space",
            )

        # Step 2: In-memory budget check (<1ms)
        action_cost = action.action_parameters.get("estimated_cost_inr_paise", 0)
        if ds.budget_used_inr_paise + action_cost > ds.budget_limit_inr_paise:
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Budget ceiling exceeded",
            )

        # Step 3: CE validate + record evidence (C-023 — evidence before execution)
        validate_input = ValidateAndRecordInput(
            session_inp.session_id,
            session_inp.contract_id,
            session_inp.professional_id,
            action.action_type,
            action.action_parameters,
            action.action_instance_id,
            ds.version,
            ds.budget_used_inr_paise,
            ds.budget_limit_inr_paise,
        )
        try:
            vr: ValidateAndRecordResult = await workflow.execute_activity(
                validate_and_record_evidence,
                validate_input,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=workflow.RetryPolicy(maximum_attempts=2),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "validate_and_record_evidence activity failed",
                extra={
                    "session_id": session_inp.session_id,
                    "action_instance_id": action.action_instance_id,
                    "error": str(exc),
                },
            )
            # C-059: failure is logged; not re-raised — caller receives Deny result
            return PAASActionResult(
                action.action_instance_id,
                False,
                None,
                "Constitutional validation activity failed",
            )

        if not vr.allowed:
            return PAASActionResult(
                action.action_instance_id,
                False,
                vr.evidence_record_id,
                vr.reason,
            )

        # Evidence confirmed written — now safe to execute (C-023)
        evidence_record_id = vr.evidence_record_id or ""

        # Step 4: Execute via AI Runtime
        exec_input = ExecuteActionInput(
            session_inp.session_id,
            session_inp.contract_id,
            action.action_type,
            action.action_parameters,
            action.action_instance_id,
            evidence_record_id,
        )
        try:
            exec_result: dict[str, Any] = await workflow.execute_activity(
                execute_action,
                exec_input,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(maximum_attempts=1),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "execute_action activity failed",
                extra={
                    "session_id": session_inp.session_id,
                    "action_instance_id": action.action_instance_id,
                    "error": str(exc),
                },
            )
            # C-059: failure is logged with context; not re-raised
            return PAASActionResult(
                action.action_instance_id,
                False,
                evidence_record_id,
                "Execution activity failed after evidence recorded",
            )

        # Update in-memory budget on success
        ds.budget_used_inr_paise += action_cost

        return PAASActionResult(
            action.action_instance_id,
            True,
            evidence_record_id,
            "executed",
            exec_result,
        )

    # -----------------------------------------------------------------------
    # Emergency Stop handler (ADR-018, C-023)
    # -----------------------------------------------------------------------

    async def _handle_emergency_stop(self, session_inp: PAASSessionInput) -> None:
        """
        On Emergency Stop:
          1. Record ABANDONED evidence for any in-flight action (C-023).
          2. Log terminal state (C-059, no PII — C-063).

        Evidence written before workflow terminates (C-023).
        """
        payload = self._emergency_stop_payload
        if payload is None:
            return

        # Record abandoned evidence for any pending in-flight action
        in_flight_action_id = (
            self._pending_action.action_instance_id
            if self._pending_action is not None
            else "none"
        )

        abandon_input = RecordAbandonedEvidenceInput(
            session_inp.session_id,
            session_inp.contract_id,
            session_inp.professional_id,
            in_flight_action_id,
            self._decision_space.version if self._decision_space is not None else "unknown",
            payload.stopped_by,
        )
        try:
            _evidence_id: str = await workflow.execute_activity(
                record_abandoned_evidence,
                abandon_input,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=workflow.RetryPolicy(maximum_attempts=3),
            )
        except ActivityError as exc:
            # C-059: failure to record abandoned evidence must be logged
            workflow.logger.error(
                "record_abandoned_evidence failed during Emergency Stop",
                extra={
                    "session_id": session_inp.session_id,
                    "error": str(exc),
                },
            )

        workflow.logger.info(
            "PAASSessionWorkflow Emergency Stopped",
            extra={
                "session_id": session_inp.session_id,
                "actions_executed": self._actions_executed,
            },
        )
        self._state = SessionState.EMERGENCY_STOPPED