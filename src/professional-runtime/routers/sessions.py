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
            "Temporal RPC failed when starting PAAS session workflow",
            exc_info=True,
            extra={"context": "start_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to start PAAS session workflow: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid input when starting PAAS session workflow",
            exc_info=True,
            extra={"context": "start_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid session input: {exc}",
        ) from exc

    logger.info(
        "PAAS session workflow started",
        extra={
            "context": "start_session",
            "session_id": session_id,
            "contract_id": body.contract_id,
            "organisation_id": body.organisation_id,
            "tenant_id": body.tenant_id,
            # C-063: professional_id intentionally omitted from log
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
    status_code=status.HTTP_200_OK,
    summary="Get PAAS session workflow status",
)
async def get_session_status(
    session_id: str,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionStatusResponse:
    """
    C-025: Describe the Temporal workflow state for the given session.
    C-063: No PII is emitted to logs.
    C-059: All RPCErrors are logged with evidence context before re-raising.
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to describe PAAS session: {exc}",
        ) from exc

    raw_status = description.status
    mapped_status = _map_workflow_status(raw_status)

    started_at: str | None = None
    closed_at: str | None = None

    if description.start_time is not None:
        started_at = description.start_time.isoformat()
    if description.close_time is not None:
        closed_at = description.close_time.isoformat()

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
        started_at=started_at,
        closed_at=closed_at,
    )


@router.post(
    "/{session_id}/pause",
    response_model=SessionPauseResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause an active PAAS session workflow via signal",
)
async def pause_session(
    session_id: str,
    body: SessionPauseRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionPauseResponse:
    """
    C-025: Pause is delivered as a Temporal signal — never a direct call.
    C-063: paused_by is operator UUID; not PII — safe to log at INFO.
    C-059: RPCErrors produce evidence log entry before raising HTTP 503.
    """
    paused_at = _now_iso()
    pause_payload = PauseSessionInput(paused_by=body.paused_by, paused_at=paused_at)

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.pause, pause_payload)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending pause signal to PAAS session",
            exc_info=True,
            extra={
                "context": "pause_session",
                "session_id": session_id,
                "paused_by": body.paused_by,
            },
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
            "paused_by": body.paused_by,
            "paused_at": paused_at,
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
    status_code=status.HTTP_200_OK,
    summary="Resume a paused PAAS session workflow via signal",
)
async def resume_session(
    session_id: str,
    body: SessionResumeRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionResumeResponse:
    """
    C-025: Resume is delivered as a Temporal signal — never a direct call.
    C-063: resumed_by is operator UUID; not PII — safe to log at INFO.
    C-059: RPCErrors produce evidence log entry before raising HTTP 503.
    """
    resumed_at = _now_iso()
    resume_payload = ResumeSessionInput(resumed_by=body.resumed_by, resumed_at=resumed_at)

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.resume, resume_payload)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending resume signal to PAAS session",
            exc_info=True,
            extra={
                "context": "resume_session",
                "session_id": session_id,
                "resumed_by": body.resumed_by,
            },
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
            "resumed_by": body.resumed_by,
            "resumed_at": resumed_at,
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
    status_code=status.HTTP_200_OK,
    summary="Terminate a PAAS session workflow via signal",
)
async def terminate_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    C-025: Termination is delivered as a Temporal signal — never a direct call.
    C-023: Evidence of the termination is recorded inside the workflow before
           the workflow exits; this endpoint merely signals intent.
    C-059: All RPCErrors produce an evidence log entry before raising HTTP 503.
    C-063: stopped_by is operator UUID; not PII — safe to log at INFO.
           reason is a controlled enum string — safe to log.
    """
    terminated_at = _now_iso()
    terminate_payload = TerminateSessionInput(
        stopped_by=body.stopped_by,
        reason=body.reason,
        terminated_at=terminated_at,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.terminate, terminate_payload)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending terminate signal to PAAS session",
            exc_info=True,
            extra={
                "context": "terminate_session",
                "session_id": session_id,
                "stopped_by": body.stopped_by,
                "reason": body.reason,
            },
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
            "stopped_by": body.stopped_by,
            "reason": body.reason,
            "terminated_at": terminated_at,
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
    summary="Emergency stop a PAAS session — C-001 absolute override path",
)
async def emergency_stop_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    C-001 ABSOLUTE OVERRIDE: Emergency Stop must always be processed.
    This REST endpoint is the SECONDARY Emergency Stop path (primary is WSS).
    It sends the EmergencyStop signal directly to the named Temporal workflow
    (session_id == workflow_id, per ADR-018), bypassing all other queuing.

    C-023: CE evidence is recorded inside the workflow on signal receipt —
           Evidence First guarantee is maintained inside PAASSessionWorkflow.
    C-025: Signal is delivered via Temporal — replica-independent routing (ADR-018).
    C-059: All exceptions produce an evidence log entry before raising.
    C-063: stopped_by is operator UUID — not PII; safe to log.
    AD-001: ≤250ms SLA — signal dispatch is non-blocking; workflow handles
            the CE call asynchronously within its execution context.
    """
    terminated_at = _now_iso()
    stop_payload = EmergencyStopSignalPayload(
        stopped_by=body.stopped_by,
        reason=body.reason,
        stopped_at=terminated_at,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.emergency_stop, stop_payload)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Temporal RPC failed when sending EmergencyStop signal to PAAS session — "
            "C-001 violation risk: halt may not have been delivered",
            exc_info=True,
            extra={
                "context": "emergency_stop_session",
                "session_id": session_id,
                "stopped_by": body.stopped_by,
                "reason": body.reason,
                # C-059: this evidence log entry substitutes the CE record
                # that would normally be written; the workflow will write
                # the authoritative record on signal receipt if Temporal recovers.
                "c059_evidence": "emergency_stop_signal_delivery_failed",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to deliver Emergency Stop signal: {exc}",
        ) from exc

    logger.warning(
        "C-001 EmergencyStop signal dispatched to PAAS session workflow",
        extra={
            "context": "emergency_stop_session",
            "session_id": session_id,
            "stopped_by": body.stopped_by,
            "reason": body.reason,
            "terminated_at": terminated_at,
        },
    )

    return SessionTerminateResponse(
        session_id=session_id,
        signal_sent=True,
        terminated_at=terminated_at,
    )