# Implements: architecture/reference/components/professional-runtime.md § PAAS Session Lifecycle
# constitutional_basis: C-023, C-025, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from temporalio.client import Client as TemporalClient
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError

from admission_guard import AdmissionActivationBinding, AdmissionActivationGuard, AdmissionGuardError
from relationship_workspace import _authorize
from workload_identity import DelegatedContext, ServiceAuthError
from workflows.paas_workflow import (
    PAASSessionInput,
    PAASSessionWorkflow,
    PauseSessionInput,
    ResumeSessionInput,
    TerminateSessionInput,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/paas/sessions", tags=["paas-sessions"])

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class SessionStartRequest(BaseModel):
    contract_id: str = Field(..., description="Employment contract UUID")
    professional_id: str = Field(..., description="Professional UUID — never logged (C-063)")
    decision_space_version: str = Field(..., description="Pinned Decision Space version")
    organisation_id: str = Field(..., description="Organisation UUID")
    tenant_id: str = Field(..., description="Tenant UUID (gRPC metadata)")
    professional_type_id: str = Field(..., description="Admitted reusable professional type")
    professional_version: str = Field(..., description="Exact admitted professional version")
    admission_state: str = Field(..., description="BP-owned admission lifecycle projection")
    admission_content_digest: str = Field(..., description="Exact admitted contract digest")
    artifact_digest: str = Field(..., description="Exact admitted implementation artifact digest")
    runtime_version: str = Field(..., description="Exact compatible Professional Runtime version")
    customer_contract_digest: str = Field(..., description="Exact accepted customer contract digest")


class SessionStartResponse(BaseModel):
    session_id: str
    workflow_id: str
    started_at: str
    status: str


class SessionStatusResponse(BaseModel):
    session_id: str
    workflow_id: str
    status: str
    started_at: str | None
    closed_at: str | None


class SessionTerminateRequest(BaseModel):
    stopped_by: str = Field(..., description="Operator/system UUID that issued the stop")
    reason: str = Field(default="OPERATOR_TERMINATE")


class SessionTerminateResponse(BaseModel):
    session_id: str
    signal_sent: bool
    terminated_at: str


class SessionPauseRequest(BaseModel):
    paused_by: str


class SessionPauseResponse(BaseModel):
    session_id: str
    signal_sent: bool
    paused_at: str


class SessionResumeRequest(BaseModel):
    resumed_by: str


class SessionResumeResponse(BaseModel):
    session_id: str
    signal_sent: bool
    resumed_at: str


# ---------------------------------------------------------------------------
# Temporal client dependency
# ---------------------------------------------------------------------------


async def get_temporal_client(request: Request) -> TemporalClient:
    """
    Retrieve the shared TemporalClient from application state.
    The client is initialised at startup in main.py and attached to app.state.
    C-025: All PAAS execution runs as Temporal workflows — client is mandatory.
    """
    client: TemporalClient | None = getattr(request.app.state, "temporal_client", None)
    if client is None:
        logger.error(
            "Temporal client not initialised in app.state",
            extra={"context": "get_temporal_client"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal client not available",
        )
    return client


def get_admission_guard() -> AdmissionActivationGuard:
    return AdmissionActivationGuard(os.getenv("PR_RUNTIME_VERSION"), os.getenv("PR_ARTIFACT_DIGEST"))


async def require_session_workload_context(request: Request, body: SessionStartRequest) -> DelegatedContext:
    try:
        relationship_id = uuid.UUID(body.contract_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="INVALID_CONTRACT_ID") from exc

    try:
        return await _authorize(
            request,
            "/api/v1/paas/sessions",
            "startPAASSession",
            relationship_id,
            body.model_dump(mode="json"),
            None,
            body.tenant_id,
        )
    except ServiceAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.code) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEMPORAL_TASK_QUEUE = "paas-session-queue"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _map_workflow_status(raw_status: WorkflowExecutionStatus | None) -> str:
    """Map Temporal WorkflowExecutionStatus enum to a human-readable string."""
    if raw_status is None:
        return "UNKNOWN"
    status_map: dict[WorkflowExecutionStatus, str] = {
        WorkflowExecutionStatus.RUNNING: "RUNNING",
        WorkflowExecutionStatus.COMPLETED: "COMPLETED",
        WorkflowExecutionStatus.FAILED: "FAILED",
        WorkflowExecutionStatus.CANCELED: "CANCELLED",
        WorkflowExecutionStatus.TERMINATED: "TERMINATED",
        WorkflowExecutionStatus.CONTINUED_AS_NEW: "CONTINUED_AS_NEW",
        WorkflowExecutionStatus.TIMED_OUT: "TIMED_OUT",
    }
    return status_map.get(raw_status, str(raw_status))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new PAAS session workflow",
)
async def start_session(
    body: SessionStartRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
    admission_guard: AdmissionActivationGuard = Depends(get_admission_guard),
    workload_context: DelegatedContext = Depends(require_session_workload_context),
) -> SessionStartResponse:
    """
    C-025: Start a PAASSessionWorkflow in Temporal.
    Each session maps 1-to-1 with a Temporal workflow; the session_id IS
    the workflow_id (ADR-018 — enables deterministic Emergency Stop routing).
    C-063: professional_id is accepted but never emitted to logs.
    C-023: Evidence is recorded inside the workflow before any execution.
    C-025: Session isolation — each workflow holds its own Decision Space in memory.
            No shared mutable state across workflow instances.
    """
    _ = workload_context
    try:
        admission_guard.require_admitted(
            AdmissionActivationBinding(
                professional_type_id=body.professional_type_id,
                professional_version=body.professional_version,
                admission_state=body.admission_state,
                admission_content_digest=body.admission_content_digest,
                artifact_digest=body.artifact_digest,
                runtime_version=body.runtime_version,
                customer_contract_digest=body.customer_contract_digest,
            )
        )
    except AdmissionGuardError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=exc.code) from exc

    session_id = str(uuid.uuid4())
    started_at = _now_iso()

    workflow_input = PAASSessionInput(
        session_id=session_id,
        contract_id=body.contract_id,
        professional_id=body.professional_id,
        decision_space_version=body.decision_space_version,
        organisation_id=body.organisation_id,
        tenant_id=body.tenant_id,
        started_at=started_at,
    )

    try:
        await temporal.start_workflow(
            PAASSessionWorkflow.run,
            workflow_input,
            id=session_id,  # workflow_id == session_id (ADR-018)
            task_queue=_TEMPORAL_TASK_QUEUE,
        )
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error starting PAAS session workflow",
            exc_info=True,
            extra={"context": "start_session", "session_id": session_id, "rpc_error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to start PAAS session workflow: {exc}",
        ) from exc

    logger.info(
        "PAAS session workflow started",
        extra={"context": "start_session", "session_id": session_id},
    )

    return SessionStartResponse(
        session_id=session_id,
        workflow_id=session_id,
        started_at=started_at,
        status="RUNNING",
    )


@router.get(
    "/{session_id}",
    response_model=SessionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get PAAS session workflow status",
)
async def get_session_status(
    session_id: str,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionStatusResponse:
    """
    C-025: Describe the Temporal workflow state for the given session.
    The session_id is the Temporal workflow_id (ADR-018).
    C-063: session_id is a UUID — no PII in log output.
    """
    try:
        handle = temporal.get_workflow_handle(session_id)
        description = await handle.describe()
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error describing PAAS session workflow",
            exc_info=True,
            extra={"context": "get_session_status", "session_id": session_id, "rpc_error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found or workflow unavailable: {session_id}",
        ) from exc

    raw_status = description.status if description is not None else None
    mapped_status = _map_workflow_status(raw_status)

    start_time: str | None = None
    close_time: str | None = None

    if description is not None:
        if description.start_time is not None:
            start_time = description.start_time.isoformat()
        if description.close_time is not None:
            close_time = description.close_time.isoformat()

    logger.info(
        "PAAS session status retrieved",
        extra={"context": "get_session_status", "session_id": session_id, "status": mapped_status},
    )

    return SessionStatusResponse(
        session_id=session_id,
        workflow_id=session_id,
        status=mapped_status,
        started_at=start_time,
        closed_at=close_time,
    )


@router.delete(
    "/{session_id}",
    response_model=SessionTerminateResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate a PAAS session workflow",
)
async def terminate_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    C-025: Send a TERMINATE signal to the PAASSessionWorkflow.
    The workflow handles orderly shutdown: records ABANDONED evidence for
    any in-flight action (C-023) before halting.
    C-063: stopped_by is an operator UUID — never logged as PII.
    """
    terminated_at = _now_iso()
    terminate_input = TerminateSessionInput(
        session_id=session_id,
        reason=body.reason,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.signal_terminate, terminate_input)
        signal_sent = True
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error sending TERMINATE signal to PAAS session",
            exc_info=True,
            extra={"context": "terminate_session", "session_id": session_id, "rpc_error": str(exc)},
        )
        signal_sent = False

    logger.info(
        "PAAS session TERMINATE signal dispatched",
        extra={
            "context": "terminate_session",
            "session_id": session_id,
            "signal_sent": signal_sent,
        },
    )

    return SessionTerminateResponse(
        session_id=session_id,
        signal_sent=signal_sent,
        terminated_at=terminated_at,
    )


@router.post(
    "/{session_id}/pause",
    response_model=SessionPauseResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause a PAAS session workflow",
)
async def pause_session(
    session_id: str,
    body: SessionPauseRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionPauseResponse:
    """
    C-025: Send a PAUSE signal to the PAASSessionWorkflow.
    The workflow suspends new action processing; in-flight actions complete
    and evidence is recorded (C-023) before the workflow enters PAUSED state.
    C-063: paused_by is an operator UUID — never logged as PII.
    """
    paused_at = _now_iso()
    pause_input = PauseSessionInput(
        session_id=session_id,
        reason=f"operator:{body.paused_by}",
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.signal_pause, pause_input)
        signal_sent = True
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error sending PAUSE signal to PAAS session",
            exc_info=True,
            extra={"context": "pause_session", "session_id": session_id, "rpc_error": str(exc)},
        )
        signal_sent = False

    logger.info(
        "PAAS session PAUSE signal dispatched",
        extra={
            "context": "pause_session",
            "session_id": session_id,
            "signal_sent": signal_sent,
        },
    )

    return SessionPauseResponse(
        session_id=session_id,
        signal_sent=signal_sent,
        paused_at=paused_at,
    )


@router.post(
    "/{session_id}/resume",
    response_model=SessionResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume a paused PAAS session workflow",
)
async def resume_session(
    session_id: str,
    body: SessionResumeRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionResumeResponse:
    """
    C-025: Send a RESUME signal to the PAASSessionWorkflow.
    The workflow transitions from PAUSED back to RUNNING state and
    resumes processing action signals.
    C-063: resumed_by is an operator UUID — never logged as PII.
    """
    resumed_at = _now_iso()
    resume_input = ResumeSessionInput(
        session_id=session_id,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.signal_resume, resume_input)
        signal_sent = True
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error sending RESUME signal to PAAS session",
            exc_info=True,
            extra={"context": "resume_session", "session_id": session_id, "rpc_error": str(exc)},
        )
        signal_sent = False

    logger.info(
        "PAAS session RESUME signal dispatched",
        extra={
            "context": "resume_session",
            "session_id": session_id,
            "signal_sent": signal_sent,
        },
    )

    return SessionResumeResponse(
        session_id=session_id,
        signal_sent=signal_sent,
        resumed_at=resumed_at,
    )
