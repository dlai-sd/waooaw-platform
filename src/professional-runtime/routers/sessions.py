# Implements: architecture/reference/api-specs/emergency-stop-ws.md full
# constitutional_basis: C-023, C-025, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from temporalio.client import Client as TemporalClient
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError

from workflows.paas_workflow import (
    PAASSessionInput,
    PAASSessionWorkflow,
    EmergencyStopSignalPayload,
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
            "Temporal RPC error starting PAAS session workflow",
            exc_info=True,
            extra={"context": "start_session", "contract_id": body.contract_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to start session workflow: {exc}",
        ) from exc

    logger.info(
        "PAAS session workflow started",
        extra={
            "context": "start_session",
            "session_id": session_id,
            "contract_id": body.contract_id,
            # C-063: professional_id deliberately omitted from logs
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
    C-025: Describe Temporal workflow state by session_id (= workflow_id per ADR-018).
    Returns current execution status without exposing PII (C-063).
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
            extra={"context": "get_session_status", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to describe session workflow: {exc}",
        ) from exc

    raw_status = description.status if description else None
    mapped_status = _map_workflow_status(raw_status)

    started_at: str | None = None
    closed_at: str | None = None

    if description and description.start_time:
        started_at = description.start_time.isoformat()
    if description and description.close_time:
        closed_at = description.close_time.isoformat()

    return SessionStatusResponse(
        session_id=session_id,
        workflow_id=session_id,
        status=mapped_status,
        started_at=started_at,
        closed_at=closed_at,
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
    C-025: Send a pause signal to the PAASSessionWorkflow.
    The workflow transitions to PAUSED state — no new actions are accepted.
    In-flight actions complete before the workflow suspends.
    C-063: paused_by is an operator UUID — not a customer PII field.
    """
    paused_at = _now_iso()
    pause_input = PauseSessionInput(paused_by=body.paused_by, paused_at=paused_at)

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.pause, pause_input)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error sending pause signal to PAAS session workflow",
            exc_info=True,
            extra={"context": "pause_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send pause signal: {exc}",
        ) from exc

    logger.info(
        "PAAS session pause signal sent",
        extra={
            "context": "pause_session",
            "session_id": session_id,
            # C-063: paused_by omitted — operator UUID but still minimise exposure
        },
    )

    return SessionPauseResponse(
        session_id=session_id,
        signal_sent=True,
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
    C-025: Send a resume signal to the PAASSessionWorkflow.
    The workflow transitions back to RUNNING state and resumes accepting actions.
    C-059: Evidence of resume is recorded inside the workflow on signal receipt.
    """
    resumed_at = _now_iso()
    resume_input = ResumeSessionInput(resumed_by=body.resumed_by, resumed_at=resumed_at)

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.resume, resume_input)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC error sending resume signal to PAAS session workflow",
            exc_info=True,
            extra={"context": "resume_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send resume signal: {exc}",
        ) from exc

    logger.info(
        "PAAS session resume signal sent",
        extra={
            "context": "resume_session",
            "session_id": session_id,
        },
    )

    return SessionResumeResponse(
        session_id=session_id,
        signal_sent=True,
        resumed_at=resumed_at,
    )


@router.delete(
    "/{session_id}",
    response_model=SessionTerminateResponse,
    summary="Terminate a PAAS session workflow",
)
async def terminate_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    C-025: Send a terminate signal to the PAASSessionWorkflow.
    The workflow performs a graceful teardown:
      1. Completes or abandons in-flight activities.
      2. Records terminal evidence via CE gRPC (C-023 — Evidence First).
      3. Releases in-memory Decision Space.
      4. Workflow completes with TERMINATED status.

    C-059: If the workflow is not found (already terminated), the caller receives
    a 404 — not a silent success — so upstream systems can detect state mismatch.
    C-063: stopped_by is an operator/system UUID, not customer PII.
    """
    terminated_at = _now_iso()
    terminate_input = TerminateSessionInput(
        stopped_by=body.stopped_by,
        reason=body.reason,
        terminated_at=terminated_at,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.terminate, terminate_input)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        # Distinguish "workflow not found" (404) from transient gRPC errors (503)
        rpc_message = str(exc).lower()
        if "not found" in rpc_message or "workflow_not_found" in rpc_message:
            logger.warning(
                "Terminate signal sent to non-existent PAAS session workflow",
                extra={"context": "terminate_session", "session_id": session_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or already terminated",
            ) from exc

        logger.error(
            "Temporal RPC error sending terminate signal to PAAS session workflow",
            exc_info=True,
            extra={"context": "terminate_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send terminate signal: {exc}",
        ) from exc

    logger.info(
        "PAAS session terminate signal sent",
        extra={
            "context": "terminate_session",
            "session_id": session_id,
            "reason": body.reason,
            # C-063: stopped_by omitted from logs
        },
    )

    return SessionTerminateResponse(
        session_id=session_id,
        signal_sent=True,
        terminated_at=terminated_at,
    )


@router.post(
    "/{session_id}/emergency-stop",
    response_model=SessionTerminateResponse,
    status_code=status.HTTP_200_OK,
    summary="Emergency Stop — REST fallback path (secondary to WebSocket)",
)
async def emergency_stop_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    REST fallback for Emergency Stop (C-001, AD-001 ≤250ms SLA).
    Primary path: WebSocket frame at wss://rt.waooaw.com/ws/emergency-stop
    This endpoint is the secondary path when WebSocket cannot be established
    (per emergency-stop-ws.md — 'REST fallback (POST /api/v1/emergency-stop)
    is a secondary path when the WebSocket cannot be established').

    C-001 (Emergency Stop absolute): signal MUST reach the workflow regardless
    of CE availability. Local halt executes immediately; CE evidence is buffered
    if CE is temporarily unavailable (graceful-degradation.md §Scenario 1).

    C-023: Evidence of Emergency Stop is recorded by the workflow via CE gRPC
    before the confirmation is sent back to the caller (Evidence First, AD-002).

    C-059: Every failure path produces an evidence record (logged with exc_info).
    C-063: No PII in log statements.
    """
    stopped_at = _now_iso()
    signal_payload = EmergencyStopSignalPayload(
        stopped_by=body.stopped_by,
        reason="EMERGENCY_STOP",
        stopped_at=stopped_at,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.emergency_stop, signal_payload)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        rpc_message = str(exc).lower()
        if "not found" in rpc_message or "workflow_not_found" in rpc_message:
            logger.warning(
                "Emergency Stop signal sent to non-existent PAAS session workflow — "
                "session may already be terminated",
                extra={"context": "emergency_stop_session", "session_id": session_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or already stopped",
            ) from exc

        logger.error(
            "Temporal RPC error sending Emergency Stop signal to PAAS session workflow",
            exc_info=True,
            extra={"context": "emergency_stop_session", "session_id": session_id},
        )
        # C-001: Emergency Stop must always work. Transient Temporal errors are
        # elevated to 503 so the client can retry immediately on the REST path.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to deliver Emergency Stop signal: {exc}",
        ) from exc

    logger.info(
        "Emergency Stop signal delivered to PAAS session workflow",
        extra={
            "context": "emergency_stop_session",
            "session_id": session_id,
            # C-063: stopped_by omitted from logs
        },
    )

    return SessionTerminateResponse(
        session_id=session_id,
        signal_sent=True,
        terminated_at=stopped_at,
    )