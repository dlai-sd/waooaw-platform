# Implements: architecture/reference/components/professional-runtime.md § PAAS Session Lifecycle
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
            "Failed to start PAASSessionWorkflow via Temporal RPC",
            exc_info=True,
            extra={"context": "start_session", "contract_id": body.contract_id},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Temporal RPC error: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid input when starting PAAS session",
            exc_info=True,
            extra={"context": "start_session", "contract_id": body.contract_id},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    logger.info(
        "PAASSessionWorkflow started",
        extra={
            "context": "start_session",
            "session_id": session_id,
            "contract_id": body.contract_id,
            "organisation_id": body.organisation_id,
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
    C-025: Describe the Temporal workflow state for the given session_id.
    workflow_id == session_id (ADR-018).
    C-063: No PII in log statements.
    C-059: All errors produce evidence via logging.
    """
    try:
        handle = temporal.get_workflow_handle(session_id)
        description = await handle.describe()
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Failed to describe Temporal workflow",
            exc_info=True,
            extra={"context": "get_session_status", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Temporal RPC error: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Session not found or invalid session_id",
            exc_info=True,
            extra={"context": "get_session_status", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
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
    The workflow handles teardown, evidence recording, and Decision Space release.
    C-063: stopped_by UUID is accepted but not logged verbatim (operator identity).
    C-059: All error paths produce log evidence before raising.
    ADR-018: workflow_id == session_id — deterministic signal routing.
    """
    terminated_at = _now_iso()

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(
            PAASSessionWorkflow.terminate_session,
            TerminateSessionInput(
                stopped_by=body.stopped_by,
                reason=body.reason,
                terminated_at=terminated_at,
            ),
        )
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Failed to send TERMINATE signal to PAASSessionWorkflow",
            exc_info=True,
            extra={
                "context": "terminate_session",
                "session_id": session_id,
                "reason": body.reason,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Temporal RPC error: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid session_id or signal payload for TERMINATE",
            exc_info=True,
            extra={"context": "terminate_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        ) from exc

    logger.info(
        "TERMINATE signal sent to PAASSessionWorkflow",
        extra={
            "context": "terminate_session",
            "session_id": session_id,
            "reason": body.reason,
            # C-063: stopped_by not logged
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
    The workflow suspends in-flight execution and holds Decision Space in memory.
    C-063: paused_by UUID is not emitted to logs.
    C-059: All error paths produce log evidence before raising.
    ADR-018: workflow_id == session_id — deterministic signal routing.
    """
    paused_at = _now_iso()

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(
            PAASSessionWorkflow.pause_session,
            PauseSessionInput(
                paused_by=body.paused_by,
                paused_at=paused_at,
            ),
        )
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Failed to send PAUSE signal to PAASSessionWorkflow",
            exc_info=True,
            extra={
                "context": "pause_session",
                "session_id": session_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Temporal RPC error: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid session_id or signal payload for PAUSE",
            exc_info=True,
            extra={"context": "pause_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        ) from exc

    logger.info(
        "PAUSE signal sent to PAASSessionWorkflow",
        extra={
            "context": "pause_session",
            "session_id": session_id,
            # C-063: paused_by not logged
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
    summary="Resume a paused PAAS session workflow",
)
async def resume_session(
    session_id: str,
    body: SessionResumeRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionResumeResponse:
    """
    C-025: Send a RESUME signal to the PAASSessionWorkflow.
    The workflow re-enables execution against the held-in-memory Decision Space.
    C-063: resumed_by UUID is not emitted to logs.
    C-059: All error paths produce log evidence before raising.
    ADR-018: workflow_id == session_id — deterministic signal routing.
    """
    resumed_at = _now_iso()

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(
            PAASSessionWorkflow.resume_session,
            ResumeSessionInput(
                resumed_by=body.resumed_by,
                resumed_at=resumed_at,
            ),
        )
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Failed to send RESUME signal to PAASSessionWorkflow",
            exc_info=True,
            extra={
                "context": "resume_session",
                "session_id": session_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Temporal RPC error: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid session_id or signal payload for RESUME",
            exc_info=True,
            extra={"context": "resume_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        ) from exc

    logger.info(
        "RESUME signal sent to PAASSessionWorkflow",
        extra={
            "context": "resume_session",
            "session_id": session_id,
            # C-063: resumed_by not logged
        },
    )

    return SessionResumeResponse(
        session_id=session_id,
        signal_sent=True,
        resumed_at=resumed_at,
    )


@router.post(
    "/{session_id}/emergency-stop",
    response_model=SessionTerminateResponse,
    status_code=status.HTTP_200_OK,
    summary="Emergency stop a PAAS session workflow (AD-001 ≤250ms)",
)
async def emergency_stop_session(
    session_id: str,
    body: SessionTerminateRequest,
    temporal: TemporalClient = Depends(get_temporal_client),
) -> SessionTerminateResponse:
    """
    AD-001: Emergency Stop must complete in ≤250ms.
    C-025: Sends EmergencyStop signal to the PAASSessionWorkflow.
    The workflow halts the in-flight activity immediately, records ABANDONED
    evidence via CE gRPC, then terminates — all inside the workflow (C-023).
    C-063: stopped_by UUID is not emitted to logs.
    C-059: All error paths produce log evidence before raising.
    ADR-018: workflow_id == session_id — deterministic signal routing to the
             exact replica holding the in-memory Decision Space.
    """
    terminated_at = _now_iso()

    try:
        handle = temporal.get_workflow_handle(session_id)
        await handle.signal(
            PAASSessionWorkflow.emergency_stop,
            EmergencyStopSignalPayload(
                stopped_by=body.stopped_by,
                reason=body.reason,
                stopped_at=terminated_at,
            ),
        )
    except asyncio.CancelledError:
        raise
    except RPCError as exc:
        logger.error(
            "Failed to send EmergencyStop signal to PAASSessionWorkflow",
            exc_info=True,
            extra={
                "context": "emergency_stop_session",
                "session_id": session_id,
                "reason": body.reason,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Temporal RPC error: {exc}",
        ) from exc
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid session_id or signal payload for EmergencyStop",
            exc_info=True,
            extra={"context": "emergency_stop_session", "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        ) from exc

    logger.info(
        "EmergencyStop signal sent to PAASSessionWorkflow",
        extra={
            "context": "emergency_stop_session",
            "session_id": session_id,
            "reason": body.reason,
            # C-063: stopped_by not logged
        },
    )

    return SessionTerminateResponse(
        session_id=session_id,
        signal_sent=True,
        terminated_at=terminated_at,
    )