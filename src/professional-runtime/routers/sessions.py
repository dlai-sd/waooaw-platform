# Implements: architecture/reference/components/professional-runtime.md § PAAS Session Lifecycle
# constitutional_basis: C-023, C-025, C-059, C-063
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
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
            id=session_id,                  # workflow_id == session_id (ADR-018)
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
                "rpc_error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start PAAS session workflow",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error starting PAAS session workflow",
            exc_info=True,
            extra={
                "context": "start_session",
                "session_id": session_id,
                "contract_id": body.contract_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error starting session",
        ) from exc

    logger.info(
        "PAAS session workflow started",
        extra={
            "context": "start_session",
            "session_id": session_id,
            "contract_id": body.contract_id,
            "decision_space_version": body.decision_space_version,
            # professional_id intentionally omitted (C-063)
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
    summary="Query PAAS session workflow state",
)
async def get_session(
    session_id: str,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionStatusResponse:
    """
    C-025: Describes the Temporal workflow state for the given session_id.
    No direct execution state is stored in the router — Temporal is the source of truth.
    """
    try:
        handle = temporal.get_workflow_handle(session_id)
        description = await handle.describe()
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        # Temporal returns NOT_FOUND via RPCError when workflow does not exist
        error_str = str(exc).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            ) from exc
        logger.error(
            "Temporal RPC failed when describing PAAS session",
            exc_info=True,
            extra={"context": "get_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to query session state",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error querying PAAS session",
            exc_info=True,
            extra={"context": "get_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error querying session",
        ) from exc

    raw_status = description.status
    started_at_dt = description.start_time
    closed_at_dt = description.close_time

    return SessionStatusResponse(
        session_id=session_id,
        workflow_id=session_id,
        status=_map_workflow_status(raw_status),
        started_at=started_at_dt.isoformat() if started_at_dt else None,
        closed_at=closed_at_dt.isoformat() if closed_at_dt else None,
    )


@router.delete(
    "/{session_id}",
    response_model=SessionTerminateResponse,
    summary="Terminate a PAAS session (sends EmergencyStop signal to workflow)",
)
async def terminate_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    C-025: Termination is effected by sending an EmergencyStop signal to the
    PAASSessionWorkflow — never by direct mutation.
    ADR-018: Emergency Stop signal is routed to the workflow by Temporal; the
    workflow records ABANDONED evidence via CE gRPC before halting.
    C-023: Evidence recording happens inside the workflow, not here.
    """
    terminated_at = _now_iso()
    payload = EmergencyStopSignalPayload(
        stopped_by=body.stopped_by,
        reason=body.reason,
        signal_sent_at=terminated_at,
    )

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(PAASSessionWorkflow.emergency_stop, payload)
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        error_str = str(exc).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            ) from exc
        logger.error(
            "Temporal RPC failed when signalling EmergencyStop",
            exc_info=True,
            extra={
                "context": "terminate_session",
                "session_id": session_id,
                "stopped_by": body.stopped_by,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send termination signal to session workflow",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error terminating PAAS session",
            exc_info=True,
            extra={
                "context": "terminate_session",
                "session_id": session_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error terminating session",
        ) from exc

    logger.info(
        "EmergencyStop signal sent to PAAS session workflow",
        extra={
            "context": "terminate_session",
            "session_id": session_id,
            "stopped_by": body.stopped_by,
            "reason": body.reason,
        },
    )

    return SessionTerminateResponse(
        session_id=session_id,
        signal_sent=True,
        terminated_at=terminated_at,
    )


@router.post(
    "/{session_id}/pause",
    response_model=SessionPauseResponse,
    summary="Pause an active PAAS session workflow",
)
async def pause_session(
    session_id: str,
    body: SessionPauseRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionPauseResponse:
    """
    C-025: Pause is effected by sending a 'pause' signal to the workflow.
    The workflow suspends action acceptance until resumed.
    C-023: If an action is in-flight, the workflow records partial evidence
    before suspending — handled inside the workflow, not here.
    """
    paused_at = _now_iso()

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal("pause", {"paused_by": body.paused_by, "paused_at": paused_at})
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        error_str = str(exc).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            ) from exc
        logger.error(
            "Temporal RPC failed when sending pause signal",
            exc_info=True,
            extra={
                "context": "pause_session",
                "session_id": session_id,
                "paused_by": body.paused_by,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send pause signal to session workflow",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error pausing PAAS session",
            exc_info=True,
            extra={"context": "pause_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error pausing session",
        ) from exc

    logger.info(
        "Pause signal sent to PAAS session workflow",
        extra={
            "context": "pause_session",
            "session_id": session_id,
            "paused_by": body.paused_by,
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
    C-025: Resume is effected by sending a 'resume' signal to the workflow.
    Session isolation (C-025) is maintained — each session's state is
    entirely encapsulated in its own Temporal workflow execution.
    """
    resumed_at = _now_iso()

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal("resume", {"resumed_by": body.resumed_by, "resumed_at": resumed_at})
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        error_str = str(exc).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            ) from exc
        logger.error(
            "Temporal RPC failed when sending resume signal",
            exc_info=True,
            extra={
                "context": "resume_session",
                "session_id": session_id,
                "resumed_by": body.resumed_by,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send resume signal to session workflow",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error resuming PAAS session",
            exc_info=True,
            extra={"context": "resume_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error resuming session",
        ) from exc

    logger.info(
        "Resume signal sent to PAAS session workflow",
        extra={
            "context": "resume_session",
            "session_id": session_id,
            "resumed_by": body.resumed_by,
        },
    )

    return SessionResumeResponse(
        session_id=session_id,
        signal_sent=True,
        resumed_at=resumed_at,
    )