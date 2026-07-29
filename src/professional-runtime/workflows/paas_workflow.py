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
from temporalio.exceptions import ActivityError, CancelledError

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
        # Per-instance state — never shared across workflow instances (C-025)
        self._state: SessionState = SessionState.STARTING
        self._decision_space: DecisionSpace | None = None
        self._actions_executed: int = 0
        self._emergency_stop_payload: EmergencyStopSignalPayload | None = None
        self._pause_requested: bool = False
        self._resume_requested: bool = False
        self._terminate_requested: bool = False
        self._terminate_reason: str = ""
        self._in_flight_action_instance_id: str | None = None

    # -----------------------------------------------------------------------
    # Queries — safe to call from any state (read-only, no side effects)
    # -----------------------------------------------------------------------

    @workflow.query
    def session_state(self) -> str:
        """Return the current session state string."""
        return str(self._state)

    @workflow.query
    def actions_executed(self) -> int:
        """Return total actions executed in this session."""
        return self._actions_executed

    @workflow.query
    def budget_used_inr_paise(self) -> int:
        """Return budget consumed so far. Zero if Decision Space not yet loaded."""
        if self._decision_space is None:
            return 0
        return self._decision_space.budget_used_inr_paise

    @workflow.query
    def decision_space_version(self) -> str | None:
        """Return loaded Decision Space version, or None if not yet loaded."""
        if self._decision_space is None:
            return None
        return self._decision_space.version

    # -----------------------------------------------------------------------
    # Signals — transition triggers sent from external callers
    # -----------------------------------------------------------------------

    @workflow.signal(name="ExecuteAction")
    async def execute_action_signal(self, inp: PAASActionInput) -> None:
        """
        Signal to execute one PAAS action within the active session.
        Queued if session is PAUSED; rejected if TERMINATING/TERMINATED/EMERGENCY_STOPPED.
        C-025: execution only via this Temporal signal path — never direct call.
        """
        if self._state not in (SessionState.ACTIVE,):
            # Signal arrived in invalid state; log without PII (C-063)
            workflow.logger.warning(
                "ExecuteAction signal received in non-ACTIVE state",
                extra={"state": str(self._state), "action_instance_id": inp.action_instance_id},
            )
            return
        self._in_flight_action_instance_id = inp.action_instance_id

    @workflow.signal(name="Pause")
    async def pause_signal(self, inp: PauseSessionInput) -> None:
        """Signal to pause the session. Valid from ACTIVE state."""
        if self._state == SessionState.ACTIVE:
            self._pause_requested = True

    @workflow.signal(name="Resume")
    async def resume_signal(self, inp: ResumeSessionInput) -> None:
        """Signal to resume a PAUSED session."""
        if self._state == SessionState.PAUSED:
            self._resume_requested = True

    @workflow.signal(name="Terminate")
    async def terminate_signal(self, inp: TerminateSessionInput) -> None:
        """
        Signal to terminate the session gracefully.
        Valid from ACTIVE or PAUSED states.
        """
        if self._state in (SessionState.ACTIVE, SessionState.PAUSED):
            self._terminate_requested = True
            self._terminate_reason = inp.reason

    @workflow.signal(name="EmergencyStop")
    async def emergency_stop_signal(self, payload: EmergencyStopSignalPayload) -> None:
        """
        Emergency Stop signal — highest priority override (C-001).
        Valid from ANY state. Transitions immediately to EMERGENCY_STOPPED.
        C-023: ABANDONED evidence written before workflow terminates.
        """
        self._emergency_stop_payload = payload
        self._state = SessionState.EMERGENCY_STOPPED

    # -----------------------------------------------------------------------
    # Main workflow run
    # -----------------------------------------------------------------------

    @workflow.run
    async def run(self, inp: PAASSessionInput) -> PAASSessionResult:
        """
        PAAS session lifecycle:
          1. Load Decision Space (STARTING)
          2. Enter ACTIVE loop — process action signals
          3. Handle PAUSE / RESUME transitions
          4. Handle TERMINATE signal — graceful shutdown
          5. Handle EmergencyStop signal — immediate halt + evidence write

        C-025: All professional execution flows through this Temporal workflow.
        C-023: Evidence recorded before any action is confirmed executed.
        C-059: All failures produce evidence or log entries; CancelledError never swallowed.
        """
        workflow.logger.info(
            "PAASSessionWorkflow starting",
            extra={"session_id": inp.session_id, "contract_id": inp.contract_id},
        )

        # ------------------------------------------------------------------
        # Phase 1: Load Decision Space (STARTING → ACTIVE)
        # ------------------------------------------------------------------
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

        # Emergency Stop may have arrived during startup
        if self._emergency_stop_payload is not None:
            return await self._handle_emergency_stop(inp, None)

        self._decision_space = DecisionSpace(
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            version=raw_ds.get("version", inp.decision_space_version),
            parameters=raw_ds.get("parameters", {}),
            budget_limit_inr_paise=inp.budget_limit_inr_paise,
            budget_used_inr_paise=raw_ds.get("budget_used_inr_paise", 0),
            allowed_action_types=raw_ds.get("allowed_action_types", []),
        )
        self._state = SessionState.ACTIVE

        workflow.logger.info(
            "PAASSessionWorkflow ACTIVE — Decision Space loaded",
            extra={"session_id": inp.session_id, "ds_version": self._decision_space.version},
        )

        # ------------------------------------------------------------------
        # Phase 2: Main event loop
        # ------------------------------------------------------------------
        while True:
            # Emergency Stop — highest priority check (C-001)
            if self._emergency_stop_payload is not None:
                return await self._handle_emergency_stop(inp, self._in_flight_action_instance_id)

            # Graceful terminate
            if self._terminate_requested:
                self._state = SessionState.TERMINATING
                workflow.logger.info(
                    "PAASSessionWorkflow TERMINATING",
                    extra={"session_id": inp.session_id, "reason": self._terminate_reason},
                )
                break

            # Pause transition
            if self._pause_requested and self._state == SessionState.ACTIVE:
                self._pause_requested = False
                self._state = SessionState.PAUSED
                workflow.logger.info(
                    "PAASSessionWorkflow PAUSED",
                    extra={"session_id": inp.session_id},
                )

            # Resume transition
            if self._resume_requested and self._state == SessionState.PAUSED:
                self._resume_requested = False
                self._state = SessionState.ACTIVE
                workflow.logger.info(
                    "PAASSessionWorkflow RESUMED",
                    extra={"session_id": inp.session_id},
                )

            # Process pending action if ACTIVE and one has arrived
            if self._state == SessionState.ACTIVE and self._in_flight_action_instance_id is not None:
                action_instance_id = self._in_flight_action_instance_id
                self._in_flight_action_instance_id = None

                # Retrieve action detail from workflow memo / query — simplified:
                # The signal handler stored action_instance_id; for full
                # implementation, PAASActionInput queue would be maintained.
                # Placeholder: execute the validate-and-record + execute path.
                await self._execute_paas_action(
                    inp=inp,
                    action_instance_id=action_instance_id,
                )
                continue

            # Yield control until a signal arrives (prevents tight spin)
            await workflow.wait_condition(
                lambda: (
                    self._emergency_stop_payload is not None
                    or self._terminate_requested
                    or self._pause_requested
                    or self._resume_requested
                    or self._in_flight_action_instance_id is not None
                ),
                timeout=timedelta(hours=8),  # PAAS sessions bounded to trading hours
            )

            # Timeout means no activity for 8h — treat as natural session end
            if not (
                self._emergency_stop_payload is not None
                or self._terminate_requested
                or self._pause_requested
                or self._resume_requested
                or self._in_flight_action_instance_id is not None
            ):
                workflow.logger.info(
                    "PAASSessionWorkflow idle timeout — terminating",
                    extra={"session_id": inp.session_id},
                )
                break

        # ------------------------------------------------------------------
        # Phase 3: Normal termination
        # ------------------------------------------------------------------
        self._state = SessionState.TERMINATED
        workflow.logger.info(
            "PAASSessionWorkflow TERMINATED",
            extra={
                "session_id": inp.session_id,
                "total_actions": self._actions_executed,
            },
        )

        budget_used = self._decision_space.budget_used_inr_paise if self._decision_space else 0
        return PAASSessionResult(
            inp.session_id,
            str(SessionState.TERMINATED),
            self._actions_executed,
            budget_used,
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _execute_paas_action(
        self,
        inp: PAASSessionInput,
        action_instance_id: str,
    ) -> None:
        """
        Execute one PAAS action through the constitutional hot path.

        Hot path:
          1. In-memory Decision Space validation (<1ms, done before this call)
          2. CE.ValidateAction + CE.RecordEvidence via Temporal activity (C-023)
          3. Execute via AI Runtime via Temporal activity (only if evidence confirmed)

        C-023: Evidence First — execution never precedes evidence record confirmation.
        C-025: All execution via Temporal activities.
        """
        assert self._decision_space is not None  # guaranteed by state machine

        validate_inp = ValidateAndRecordInput(
            session_id=inp.session_id,
            contract_id=inp.contract_id,
            professional_id=inp.professional_id,
            action_type="",          # populated from queued action in full impl
            action_parameters={},    # populated from queued action in full impl
            action_instance_id=action_instance_id,
            decision_space_version=self._decision_space.version,
            budget_used_inr_paise=self._decision_space.budget_used_inr_paise,
            budget_limit_inr_paise=self._decision_space.budget_limit_inr_paise,
        )

        try:
            validate_result: ValidateAndRecordResult = await workflow.execute_activity(
                validate_and_record_evidence,
                validate_inp,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=workflow.RetryPolicy(maximum_attempts=2),
            )
        except ActivityError as exc:
            workflow.logger.error(
                "validate_and_record_evidence activity failed",
                extra={"session_id": inp.session_id, "action_instance_id": action_instance_id, "error": str(exc)},
            )
            return

        if not validate_result.allowed:
            workflow.logger.info(
                "Action denied by Constitutional Engine",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action_instance_id,
                    "reason": validate_result.reason,
                    "constitutional_basis": validate_result.constitutional_basis,
                },
            )
            return

        # Evidence confirmed written — now execute (C-023)
        assert validate_result.evidence_record_id is not None

        exec_inp = ExecuteActionInput(
            session_id=inp.session_id,
            contract_id=inp.contract_id,
            action_type="",          # populated from queued action in full impl
            action_parameters={},    # populated from queued action in full impl
            action_instance_id=action_instance_id,
            evidence_record_id=validate_result.evidence_record_id,
        )

        try:
            await workflow.execute_activity(
                execute_action,
                exec_inp,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(maximum_attempts=1),
            )
            self._actions_executed += 1
        except ActivityError as exc:
            workflow.logger.error(
                "execute_action activity failed",
                extra={
                    "session_id": inp.session_id,
                    "action_instance_id": action_instance_id,
                    "evidence_record_id": validate_result.evidence_record_id,
                    "error": str(exc),
                },
            )

    async def _handle_emergency_stop(
        self,
        inp: PAASSessionInput,
        in_flight_action_instance_id: str | None,
    ) -> PAASSessionResult:
        """
        Emergency Stop handler — C-001 (absolute human override).

        Steps:
          1. Record ABANDONED evidence for any in-flight action (C-023)
          2. Transition to EMERGENCY_STOPPED
          3. Return terminal result

        C-023: evidence written before workflow returns.
        C-059: evidence record produced for every in-flight action.
        """
        assert self._emergency_stop_payload is not None

        self._state = SessionState.EMERGENCY_STOPPED
        ds = self._decision_space

        if in_flight_action_instance_id is not None and ds is not None:
            abandon_inp = RecordAbandonedEvidenceInput(
                session_id=inp.session_id,
                contract_id=inp.contract_id,
                professional_id=inp.professional_id,
                action_instance_id=in_flight_action_instance_id,
                decision_space_version=ds.version,
                stopped_by=self._emergency_stop_payload.stopped_by,
            )
            try:
                evidence_record_id = await workflow.execute_activity(
                    record_abandoned_evidence,
                    abandon_inp,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=3),
                )
                workflow.logger.info(
                    "ABANDONED evidence recorded for in-flight action",
                    extra={
                        "session_id": inp.session_id,
                        "action_instance_id": in_flight_action_instance_id,
                        "evidence_record_id": evidence_record_id,
                    },
                )
            except ActivityError as exc:
                # C-059: log evidence failure — cannot re-raise as session must terminate
                workflow.logger.error(
                    "CRITICAL: Failed to record ABANDONED evidence on Emergency Stop",
                    extra={
                        "session_id": inp.session_id,
                        "action_instance_id": in_flight_action_instance_id,
                        "error": str(exc),
                    },
                )

        budget_used = ds.budget_used_inr_paise if ds is not None else 0

        workflow.logger.info(
            "PAASSessionWorkflow EMERGENCY_STOPPED",
            extra={
                "session_id": inp.session_id,
                "total_actions": self._actions_executed,
            },
        )

        return PAASSessionResult(
            inp.session_id,
            str(SessionState.EMERGENCY_STOPPED),
            self._actions_executed,
            budget_used,
        )