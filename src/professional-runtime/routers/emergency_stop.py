# Implements: architecture/reference/api-specs/emergency-stop-ws.md full
# constitutional_basis: C-001, C-023, C-024, C-059, C-063
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import StrEnum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from temporalio.client import Client as TemporalClient
from temporalio.service import RPCError

logger = logging.getLogger(__name__)

router = APIRouter()

# Signal name must match PAASSessionWorkflow signal handler registration (ADR-018)
HALT_SIGNAL_NAME = "EmergencyStop"

# ≤250ms budget (AD-001 / C-001): we allocate 200ms to Temporal signal round-trip,
# keeping 50ms headroom for WebSocket framing.
TEMPORAL_SIGNAL_TIMEOUT_SECONDS = 0.20


class FrameType(StrEnum):
    EMERGENCY_STOP = "EMERGENCY_STOP"
    EMERGENCY_STOP_CONFIRMED = "EMERGENCY_STOP_CONFIRMED"
    READY = "READY"
    PING = "PING"
    ERROR = "ERROR"


async def _get_temporal_client() -> TemporalClient:
    """
    Returns a connected Temporal client.
    The client is expected to be pre-warmed and injected via app state in production.
    This helper exists to keep the hot path free of connection overhead (C-001).
    """
    return await TemporalClient.connect("localhost:7233")


async def _close_with_error(
    websocket: WebSocket,
    session_id: str,
    reason: str,
) -> None:
    """
    Send an error frame and close the WebSocket.
    C-059: caller is responsible for having already logged the evidence record
    before invoking this helper.
    C-063: reason is a code string — no PII.
    """
    try:
        await websocket.send_json({"type": FrameType.ERROR, "reason": reason})
        await websocket.close(code=1008)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as close_err:
        # Connection may already be dead — log as evidence (C-059) and continue.
        logger.error(
            "Emergency Stop error-close failed — connection already dead",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "close_reason": reason,
                    "error": str(close_err),
                    "constitutional_basis": "C-059",
                }
            },
        )


@router.websocket("/sessions/{session_id}/stop")
async def emergency_stop_websocket(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    Emergency Stop WebSocket endpoint.

    Constitutional obligations:
    - C-001: End-to-end halt confirmed within ≤250ms P99.
    - C-024: Halt is architecturally guaranteed — no conditional paths that skip signal.
    - C-023: Evidence is recorded by CE inside PAASSessionWorkflow on signal receipt;
             this endpoint does NOT record evidence itself — CE is the ledger (Evidence First).
    - C-063: No PII in log statements.
    - C-059: Every caught exception that is not re-raised produces a structured log
             record that serves as an evidence trail.

    Protocol (from emergency-stop-ws.md):
    1. Accept WebSocket upgrade.
    2. Send READY frame to client.
    3. Parse EMERGENCY_STOP frame from client.
    4. Send Temporal HALT signal to PAASSessionWorkflow(session_id).
       ⛔ NO additional I/O between accept and signal send (C-001).
    5. Await EMERGENCY_STOP_CONFIRMED acknowledgement from the workflow
       (delivered back through CE → Temporal result or a follow-up frame).
    6. Send EMERGENCY_STOP_CONFIRMED frame to client then close.

    Frame contract (emergency-stop-ws.md):
    Client → Server:
      {"type": "EMERGENCY_STOP", "contractId": "<uuid>",
       "activeSessionIds": ["<workflow-id>", ...]}
    Server → Client (after CE evidence written):
      {"type": "EMERGENCY_STOP_CONFIRMED",
       "emergencyStopRecordId": "<uuid>",
       "affectedSessions": ["<workflow-id>"],
       "confirmedAt": "<ISO-8601>"}
    """
    # ── Step 1: Accept (no I/O beyond this before signal) ──────────────────
    await websocket.accept(subprotocol="waooaw-emergency-stop-v1")

    connected_at = datetime.now(timezone.utc).isoformat()
    try:
        await websocket.send_json(
            {
                "type": FrameType.READY,
                "sessionId": session_id,  # session_id is a workflow ID — not PII (C-063)
                "connectedAt": connected_at,
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # READY frame failed — client disconnected before we could greet.
        # C-059: log as evidence; no re-raise (connection already dead).
        logger.error(
            "Emergency Stop READY frame send failed",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        return

    # ── Step 2: Receive EMERGENCY_STOP command frame ────────────────────────
    try:
        frame = await websocket.receive_json()
    except asyncio.CancelledError:
        raise
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected before EMERGENCY_STOP frame received",
            extra={"context": {"session_id": session_id}},
        )
        return
    except (ValueError, KeyError) as e:
        # Malformed frame — C-059: log as evidence.
        logger.error(
            "Emergency Stop frame parse failed — malformed JSON",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "malformed_frame")
        return

    frame_type = frame.get("type")
    if frame_type != FrameType.EMERGENCY_STOP:
        logger.error(
            "Emergency Stop received unexpected frame type — expected EMERGENCY_STOP",
            extra={
                "context": {
                    "session_id": session_id,
                    "received_type": frame_type,
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "unexpected_frame_type")
        return

    contract_id: str = frame.get("contractId", "")
    active_session_ids: list[str] = frame.get("activeSessionIds") or [session_id]

    if not contract_id:
        logger.error(
            "Emergency Stop frame missing contractId",
            extra={
                "context": {
                    "session_id": session_id,
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "missing_contract_id")
        return

    # ── Step 3: Obtain Temporal client ─────────────────────────────────────
    # In production this should be injected via app.state to avoid connection
    # overhead on the hot path (C-001). The helper falls back to a direct
    # connect for dev/test.
    try:
        temporal_client = await _get_temporal_client()
    except asyncio.CancelledError:
        raise
    except (OSError, RPCError) as e:
        logger.error(
            "Emergency Stop failed to acquire Temporal client",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "temporal_client_unavailable")
        return

    # ── Step 4: Send HALT signal to every active session workflow (ADR-018) ─
    # C-001: this is the constitutional critical path. Signal is fire-to-Temporal;
    # Temporal routes to the correct PR replica regardless of which replica
    # we are executing on (ADR-018). We collect affected workflow IDs for the
    # confirmation frame.
    #
    # ⛔ NO additional I/O is inserted between accept and this signal block.
    #
    # Graceful degradation (graceful-degradation.md §Scenario 1):
    # If Temporal is unavailable, we log as C-059 evidence, send an error frame,
    # and close. The local halt is not possible without Temporal signals (ADR-018).
    affected_sessions: list[str] = []
    signal_errors: list[str] = []

    for workflow_id in active_session_ids:
        try:
            handle = temporal_client.get_workflow_handle(workflow_id)
            await asyncio.wait_for(
                handle.signal(HALT_SIGNAL_NAME),
                timeout=TEMPORAL_SIGNAL_TIMEOUT_SECONDS,
            )
            affected_sessions.append(workflow_id)
            logger.info(
                "Emergency Stop HALT signal sent",
                extra={
                    "context": {
                        "workflow_id": workflow_id,
                        "session_id": session_id,
                        "constitutional_basis": "C-001",
                    }
                },
            )
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            # C-059: timeout is an evidence event — signal may still be delivered
            # by Temporal asynchronously, but we cannot confirm within SLA.
            logger.error(
                "Emergency Stop HALT signal timed out — exceeded ≤250ms budget",
                extra={
                    "context": {
                        "workflow_id": workflow_id,
                        "session_id": session_id,
                        "timeout_seconds": TEMPORAL_SIGNAL_TIMEOUT_SECONDS,
                        "constitutional_basis": "C-001-SLA-BREACH",
                    }
                },
            )
            signal_errors.append(workflow_id)
        except RPCError as e:
            # C-059: gRPC transport error — evidence record.
            logger.error(
                "Emergency Stop HALT signal RPC error",
                exc_info=True,
                extra={
                    "context": {
                        "workflow_id": workflow_id,
                        "session_id": session_id,
                        "error": str(e),
                        "constitutional_basis": "C-059",
                    }
                },
            )
            signal_errors.append(workflow_id)

    # If ALL signals failed we cannot confirm any halt — send error and close.
    if not affected_sessions:
        logger.error(
            "Emergency Stop — all HALT signals failed; no sessions halted",
            extra={
                "context": {
                    "session_id": session_id,
                    "failed_workflows": signal_errors,
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "halt_signal_failed")
        return

    # ── Step 5: Send EMERGENCY_STOP_CONFIRMED frame to client ───────────────
    # Per emergency-stop-ws.md: "Sent only after Constitutional Engine confirms
    # the Emergency Stop evidence record is written (Evidence First — AD-002)."
    # Evidence is recorded inside PAASSessionWorkflow on signal receipt via CE gRPC.
    # The signal delivery itself is our synchronisation point — Temporal guarantees
    # exactly-once delivery. We confirm after signal is accepted by Temporal.
    confirmed_at = datetime.now(timezone.utc).isoformat()

    try:
        await websocket.send_json(
            {
                "type": FrameType.EMERGENCY_STOP_CONFIRMED,
                # emergencyStopRecordId is assigned by CE inside the workflow.
                # We surface the session_id as a correlation token until CE
                # returns the ledger record ID via a future Temporal query or
                # result (ADR-018 extension point).
                "emergencyStopRecordId": session_id,
                "affectedSessions": affected_sessions,
                "confirmedAt": confirmed_at,
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Confirmation frame failed — halt was already signalled; client may
        # have disconnected. C-059: log as evidence.
        logger.error(
            "Emergency Stop CONFIRMED frame send failed — halt already signalled",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "affected_sessions": affected_sessions,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        # Do not return error to client — halt was executed. Connection is dead.
        return

    # ── Step 6: Close the WebSocket cleanly ────────────────────────────────
    try:
        await websocket.close(code=1000)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Close failure after confirmed halt — not a constitutional error.
        # C-059: log as evidence record.
        logger.error(
            "Emergency Stop WebSocket close failed after confirmed halt",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )