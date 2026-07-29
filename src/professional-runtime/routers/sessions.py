# Implements: architecture/reference/components/professional-runtime.md § PAAS Session Lifecycle
# constitutional_basis: C-023, C-025, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from temporalio.client import Client as TemporalClient
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError

from workflows.paas_workflow import (
    PAASSessionInput,
    PAASSessionWorkflow,
    EmergencyStopSignalPayload,
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
            id=session_id,                   # workflow_id == session_id (ADR-018)
            task_queue=_TEMPORAL_TASK_QUEUE,
        )
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when starting PAAS session workflow",
            exc_info=True,
            extra={
                "context": "start_session",
                "session_id": session_id,
                "contract_id": body.contract_id,
                # C-063: professional_id intentionally excluded from logs
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to start PAAS session workflow: {exc}",
        ) from exc

    logger.info(
        "PAAS session workflow started",
        extra={
            "context": "start_session",
            "session_id": session_id,
            "contract_id": body.contract_id,
            "decision_space_version": body.decision_space_version,
            "organisation_id": body.organisation_id,
            # C-063: professional_id and tenant_id excluded from logs
        },
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
    summary="Get PAAS session workflow status",
)
async def get_session_status(
    session_id: str,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionStatusResponse:
    """
    Describe the Temporal workflow state for the given session_id.
    C-025: session_id == workflow_id (ADR-018).
    Returns 404 if the workflow does not exist in Temporal.
    """
    try:
        handle = temporal.get_workflow_handle(session_id)
        description = await handle.describe()
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when describing PAAS session workflow",
            exc_info=True,
            extra={"context": "get_session_status", "session_id": session_id},
        )
        # Temporal returns NOT_FOUND via RPCError; surface as 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        ) from exc

    raw_status = description.status
    mapped_status = _map_workflow_status(raw_status)

    start_time = description.start_time
    close_time = getattr(description, "close_time", None)

    started_at_iso: str | None = (
        start_time.isoformat() if start_time is not None else None
    )
    closed_at_iso: str | None = (
        close_time.isoformat() if close_time is not None else None
    )

    logger.info(
        "PAAS session status retrieved",
        extra={
            "context": "get_session_status",
            "session_id": session_id,
            "workflow_status": mapped_status,
        },
    )

    return SessionStatusResponse(
        session_id=session_id,
        workflow_id=session_id,
        status=mapped_status,
        started_at=started_at_iso,
        closed_at=closed_at_iso,
    )


@router.delete(
    "/{session_id}",
    response_model=SessionTerminateResponse,
    summary="Terminate a PAAS session workflow via signal",
)
async def terminate_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    Send an EmergencyStop signal to the PAASSessionWorkflow identified by session_id.
    C-025: Termination is always via Temporal signal — never direct kill.
    C-023: The workflow records ABANDONED evidence via CE before halting.
    ADR-018: workflow_id == session_id enables deterministic signal routing.

    The signal handler inside the workflow will:
      1. Halt any in-flight Temporal activity immediately.
      2. Record ABANDONED evidence via CE gRPC (Evidence First — AD-002).
      3. Terminate the workflow.

    This endpoint does NOT wait for workflow completion — it dispatches the signal
    and returns immediately. Callers should poll GET /sessions/{id} for final state
    or use the Emergency Stop WebSocket confirmation frame.
    """
    terminated_at = _now_iso()

    signal_payload = EmergencyStopSignalPayload(
        stopped_by=body.stopped_by,
        reason=body.reason,
        issued_at=terminated_at,
    )

    signal_sent = False
    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.emergency_stop, signal_payload)
        signal_sent = True
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending terminate signal to PAAS session",
            exc_info=True,
            extra={
                "context": "terminate_session",
                "session_id": session_id,
                "reason": body.reason,
                # C-063: stopped_by omitted (may be a professional identifier)
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send terminate signal to session {session_id}: {exc}",
        ) from exc

    logger.info(
        "PAAS session terminate signal dispatched",
        extra={
            "context": "terminate_session",
            "session_id": session_id,
            "reason": body.reason,
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
    summary="Pause a running PAAS session workflow",
)
async def pause_session(
    session_id: str,
    body: SessionPauseRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionPauseResponse:
    """
    Send a pause signal to the PAASSessionWorkflow identified by session_id.
    C-025: Pause is dispatched via Temporal signal — never a direct thread interrupt.
    C-023: Evidence of the pause event is recorded by the workflow via CE gRPC.
    C-063: paused_by is not emitted to logs.

    The signal handler inside the workflow suspends execution of new actions
    while preserving the in-memory Decision Space and session state.
    In-flight actions complete before the pause takes effect.
    """
    paused_at = _now_iso()
    signal_sent = False

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.pause, body.paused_by)
        signal_sent = True
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending pause signal to PAAS session",
            exc_info=True,
            extra={
                "context": "pause_session",
                "session_id": session_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send pause signal to session {session_id}: {exc}",
        ) from exc

    logger.info(
        "PAAS session pause signal dispatched",
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
    summary="Resume a paused PAAS session workflow",
)
async def resume_session(
    session_id: str,
    body: SessionResumeRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionResumeResponse:
    """
    Send a resume signal to a paused PAASSessionWorkflow.
    C-025: Resume is dispatched via Temporal signal.
    C-023: Evidence of the resume event is recorded by the workflow via CE gRPC.
    C-063: resumed_by is not emitted to logs.

    The signal handler inside the workflow re-enables action execution.
    The Decision Space remains in memory — no reload required unless the
    version has changed (which would trigger a separate Decision Space reload
    signal from the workflow's own version-check activity).
    """
    resumed_at = _now_iso()
    signal_sent = False

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.resume, body.resumed_by)
        signal_sent = True
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending resume signal to PAAS session",
            exc_info=True,
            extra={
                "context": "resume_session",
                "session_id": session_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send resume signal to session {session_id}: {exc}",
        ) from exc

    logger.info(
        "PAAS session resume signal dispatched",
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