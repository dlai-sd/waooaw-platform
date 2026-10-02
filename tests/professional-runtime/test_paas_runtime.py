# Implements: architecture/reference/components/professional-runtime.md §2 PAAS Engine
# constitutional_basis: C-023, C-025, C-059, C-063, C-076
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from temporalio.client import WorkflowExecutionStatus

from admission_guard import AdmissionActivationGuard
from routers.sessions import (
    SessionPauseRequest,
    SessionResumeRequest,
    SessionStartRequest,
    SessionTerminateRequest,
    _map_workflow_status,
    get_session_status,
    get_temporal_client,
    pause_session,
    require_session_workload_context,
    resume_session,
    start_session,
    terminate_session,
)
from workload_identity import ServiceAuthError
from workflows.paas_workflow import (
    DecisionSpace,
    EmergencyStopSignalPayload,
    PAASActionInput,
    PAASSessionInput,
    PAASSessionWorkflow,
    PauseSessionInput,
    ResumeSessionInput,
    SessionState,
    TerminateSessionInput,
    ValidateAndRecordResult,
    execute_action,
    record_abandoned_evidence,
    validate_and_record_evidence,
)


def _session_input() -> PAASSessionInput:
    return PAASSessionInput(
        session_id="session-a",
        contract_id="contract-a",
        professional_id="professional-a",
        organisation_id="organisation-a",
        decision_space_version="v1",
        tenant_id="tenant-a",
        started_at="2026-08-15T00:00:00+00:00",
    )


def _decision_space(*, budget: int = 100, used: int = 0) -> DecisionSpace:
    return DecisionSpace(
        contract_id="contract-a",
        professional_id="professional-a",
        version="v1",
        parameters={},
        budget_limit_inr_paise=budget,
        budget_used_inr_paise=used,
        allowed_action_types=["summarize"],
    )


async def test_temporal_dependency_fails_closed_and_returns_configured_client() -> None:
    request = MagicMock()
    request.app.state.temporal_client = None
    with pytest.raises(HTTPException) as failure:
        await get_temporal_client(request)
    assert failure.value.status_code == 503

    client = MagicMock()
    request.app.state.temporal_client = client
    assert await get_temporal_client(request) is client


async def test_session_start_requires_exact_bp_workload_context() -> None:
    body = _admitted_session_request()
    request = MagicMock()
    context = MagicMock()
    with patch("routers.sessions.authorize_paas_session_start", new=AsyncMock(return_value=context)) as authorize:
        assert await require_session_workload_context(request, body) is context

    authorize.assert_awaited_once_with(
        request,
        uuid.UUID(body.contract_id),
        body.model_dump(mode="json"),
        body.tenant_id,
    )


async def test_session_start_rejects_malformed_contract_id_before_authorization() -> None:
    body = _admitted_session_request().model_copy(update={"contract_id": "not-a-uuid"})
    with patch("routers.sessions.authorize_paas_session_start", new=AsyncMock()) as authorize:
        with pytest.raises(HTTPException) as failure:
            await require_session_workload_context(MagicMock(), body)

    assert failure.value.status_code == 422
    assert failure.value.detail == "INVALID_CONTRACT_ID"
    authorize.assert_not_awaited()


async def test_session_start_fails_closed_when_workload_authentication_fails() -> None:
    with patch(
        "routers.sessions.authorize_paas_session_start",
        new=AsyncMock(side_effect=ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")),
    ):
        with pytest.raises(HTTPException) as failure:
            await require_session_workload_context(MagicMock(), _admitted_session_request())

    assert failure.value.status_code == 401
    assert failure.value.detail == "SERVICE_AUTHENTICATION_FAILED"


def test_workflow_status_mapping_is_complete_and_unknown_safe() -> None:
    expected = {
        WorkflowExecutionStatus.RUNNING: "RUNNING",
        WorkflowExecutionStatus.COMPLETED: "COMPLETED",
        WorkflowExecutionStatus.FAILED: "FAILED",
        WorkflowExecutionStatus.CANCELED: "CANCELLED",
        WorkflowExecutionStatus.TERMINATED: "TERMINATED",
        WorkflowExecutionStatus.CONTINUED_AS_NEW: "CONTINUED_AS_NEW",
        WorkflowExecutionStatus.TIMED_OUT: "TIMED_OUT",
    }
    assert _map_workflow_status(None) == "UNKNOWN"
    assert {_status: _map_workflow_status(_status) for _status in expected} == expected


async def test_router_starts_and_describes_temporal_workflow() -> None:
    temporal = MagicMock()
    temporal.start_workflow = AsyncMock()
    body = _admitted_session_request()

    started = await start_session(body, temporal, AdmissionActivationGuard("1.3.0", "sha256:" + "2" * 64))

    assert started.session_id == started.workflow_id
    workflow_input = temporal.start_workflow.await_args.args[1]
    assert workflow_input.tenant_id == "tenant-a"
    assert workflow_input.budget_limit_inr_paise == 0

    description = MagicMock()
    description.status = WorkflowExecutionStatus.COMPLETED
    description.start_time = datetime(2026, 8, 15, tzinfo=timezone.utc)
    description.close_time = datetime(2026, 8, 15, 0, 1, tzinfo=timezone.utc)
    handle = MagicMock()
    handle.describe = AsyncMock(return_value=description)
    temporal.get_workflow_handle.return_value = handle

    status = await get_session_status(started.session_id, temporal)
    assert status.status == "COMPLETED"
    assert status.started_at == "2026-08-15T00:00:00+00:00"
    assert status.closed_at == "2026-08-15T00:01:00+00:00"

    handle.describe.return_value = None
    unknown = await get_session_status(started.session_id, temporal)
    assert unknown.status == "UNKNOWN"
    assert unknown.started_at is None
    assert unknown.closed_at is None


async def test_router_dispatches_typed_lifecycle_signals() -> None:
    temporal = MagicMock()
    handle = MagicMock()
    handle.signal = AsyncMock()
    temporal.get_workflow_handle.return_value = handle

    terminated = await terminate_session(
        "session-a",
        SessionTerminateRequest(stopped_by="operator-a", reason="stop"),
        temporal,
    )
    paused = await pause_session("session-a", SessionPauseRequest(paused_by="operator-a"), temporal)
    resumed = await resume_session("session-a", SessionResumeRequest(resumed_by="operator-a"), temporal)

    assert terminated.signal_sent and paused.signal_sent and resumed.signal_sent
    signals = handle.signal.await_args_list
    assert signals[0].args[0] is PAASSessionWorkflow.signal_terminate
    assert signals[0].args[1] == TerminateSessionInput(session_id="session-a", reason="stop")
    assert signals[1].args[0] is PAASSessionWorkflow.signal_pause
    assert signals[1].args[1] == PauseSessionInput(session_id="session-a", reason="operator:operator-a")
    assert signals[2].args[0] is PAASSessionWorkflow.signal_resume
    assert signals[2].args[1] == ResumeSessionInput(session_id="session-a")


async def test_workflow_signals_and_queries_preserve_state_guards() -> None:
    workflow = PAASSessionWorkflow()
    action = PAASActionInput("summarize", {}, "action-a")

    await workflow.signal_execute_action(action)
    assert workflow._pending_actions == []
    workflow._state = SessionState.ACTIVE
    await workflow.signal_execute_action(action)
    await workflow.signal_pause(PauseSessionInput("session-a", "operator"))
    assert workflow._pending_actions == [action]
    assert workflow._pause_requested is True

    workflow._state = SessionState.PAUSED
    await workflow.signal_resume(ResumeSessionInput("session-a"))
    await workflow.signal_terminate(TerminateSessionInput("session-a", "done"))
    assert workflow._resume_requested is True
    assert workflow._terminate_requested is True
    assert workflow._terminate_reason == "done"
    assert workflow.query_session_state() == str(SessionState.PAUSED)
    assert workflow.query_budget_used() == 0
    assert workflow.query_total_actions_executed() == 0

    await workflow.signal_emergency_stop()
    assert workflow._state == SessionState.EMERGENCY_STOPPED
    assert workflow._emergency_stop_payload == EmergencyStopSignalPayload(
        stopped_by="constitutional-engine",
        reason="Emergency Stop",
    )


async def test_action_hot_path_denies_out_of_scope_budget_and_ce_rejection() -> None:
    workflow = PAASSessionWorkflow()
    workflow._decision_space = _decision_space()
    session = _session_input()

    outside = await workflow._execute_paas_action(
        session,
        PAASActionInput("publish", {}, "action-outside"),
    )
    assert outside.allowed is False
    assert "not in Decision Space" in outside.reason

    workflow._decision_space = _decision_space(budget=10, used=10)
    exhausted = await workflow._execute_paas_action(
        session,
        PAASActionInput("summarize", {}, "action-budget"),
    )
    assert exhausted.reason == "Budget exhausted"

    workflow._decision_space = _decision_space()
    denied = ValidateAndRecordResult(False, "evidence-denied", "policy denied", "C-041")
    with patch("workflows.paas_workflow.workflow.execute_activity", new=AsyncMock(return_value=denied)):
        result = await workflow._execute_paas_action(
            session,
            PAASActionInput("summarize", {}, "action-denied"),
        )
    assert result.allowed is False
    assert result.evidence_record_id == "evidence-denied"


async def test_action_executes_only_after_evidence_and_updates_budget() -> None:
    workflow = PAASSessionWorkflow()
    workflow._decision_space = _decision_space()
    calls: list[object] = []

    async def execute(activity: object, *_args: object, **_kwargs: object) -> object:
        calls.append(activity)
        if activity is validate_and_record_evidence:
            return ValidateAndRecordResult(True, "evidence-a", "allowed", "C-041")
        if activity is execute_action:
            return {"content": "done", "cost_inr_paise": 7}
        raise AssertionError("unexpected activity")

    with patch("workflows.paas_workflow.workflow.execute_activity", side_effect=execute):
        result = await workflow._execute_paas_action(
            _session_input(),
            PAASActionInput("summarize", {"topic": "today"}, "action-a"),
        )

    assert calls == [validate_and_record_evidence, execute_action]
    assert result.allowed is True
    assert result.evidence_record_id == "evidence-a"
    assert workflow._decision_space.budget_used_inr_paise == 7
    assert workflow.query_total_actions_executed() == 1
    assert workflow._in_flight_action is None


async def test_emergency_stop_records_abandonment_and_releases_session_state() -> None:
    workflow = PAASSessionWorkflow()
    workflow._decision_space = _decision_space(used=9)
    workflow._in_flight_action = PAASActionInput("summarize", {}, "action-a")
    workflow._emergency_stop_payload = EmergencyStopSignalPayload("operator-a", "stop")
    execute = AsyncMock(return_value="evidence-abandoned")

    with patch("workflows.paas_workflow.workflow.execute_activity", new=execute):
        result = await workflow._handle_emergency_stop(_session_input())

    assert execute.await_args.args[0] is record_abandoned_evidence
    assert result.terminal_state == str(SessionState.EMERGENCY_STOPPED)
    assert result.final_budget_used_inr_paise == 9
    assert workflow._decision_space is None


async def test_workflow_run_loads_decision_space_and_terminates_orderly() -> None:
    workflow = PAASSessionWorkflow()
    loaded = {
        "contract_id": "contract-a",
        "professional_id": "professional-a",
        "version": "v1",
        "parameters": {"mode": "governed"},
        "budget_limit_inr_paise": 100,
        "budget_used_inr_paise": 12,
        "allowed_action_types": ["summarize"],
    }

    async def wait_for_signal(predicate: object) -> None:
        workflow._terminate_requested = True
        assert callable(predicate) and predicate()

    with (
        patch("workflows.paas_workflow.workflow.execute_activity", new=AsyncMock(return_value=loaded)),
        patch("workflows.paas_workflow.workflow.wait_condition", side_effect=wait_for_signal),
    ):
        result = await workflow.run(_session_input())

    assert result.terminal_state == str(SessionState.TERMINATED)
    assert result.final_budget_used_inr_paise == 12
    assert workflow._decision_space is not None
    assert workflow._decision_space.parameters == {"mode": "governed"}


async def test_cancellation_is_never_swallowed_by_router_or_workflow() -> None:
    temporal = MagicMock()
    temporal.start_workflow = AsyncMock(side_effect=asyncio.CancelledError())
    body = _admitted_session_request()
    with pytest.raises(asyncio.CancelledError):
        await start_session(body, temporal, AdmissionActivationGuard("1.3.0", "sha256:" + "2" * 64))


def _admitted_session_request() -> SessionStartRequest:
    return SessionStartRequest(
        contract_id="12345678-1234-1234-1234-123456789abc",
        professional_id="professional-a",
        decision_space_version="v1",
        organisation_id="organisation-a",
        tenant_id="tenant-a",
        professional_type_id="DIGITAL_MARKETING_LOCAL_SERVICE",
        professional_version="3.1.0",
        admission_state="ACTIVE",
        admission_content_digest="sha256:" + "1" * 64,
        artifact_digest="sha256:" + "2" * 64,
        runtime_version="1.3.0",
        customer_contract_digest="sha256:" + "3" * 64,
    )
