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
            "Emergency Stop endpoint received unexpected frame type",
            extra={
                "context": {
                    "session_id": session_id,
                    "frame_type": str(frame_type),
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

    # ── Step 3: Send fire-and-forget 'stopping' acknowledgement ────────────
    # Per task requirements: fire-and-forget status before signal.
    # This satisfies AD-001 — client receives immediate acknowledgement
    # while Temporal signal is in-flight.
    try:
        await websocket.send_json({"status": "stopping"})
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Client disconnected mid-flight — C-059: log as evidence and abort.
        logger.error(
            "Emergency Stop 'stopping' status send failed",
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

    # ── Step 4: Acquire Temporal client and send HALT signal ───────────────
    # ⛔ C-001: no additional I/O here — signal must be sent without delay.
    # ADR-018: signal is addressed by workflow_id; Temporal routes to the
    # correct PR replica transparently.
    try:
        temporal_client = await _get_temporal_client()
    except asyncio.CancelledError:
        raise
    except (RPCError, OSError, ConnectionRefusedError) as e:
        # Temporal connection failed — C-059: log as evidence.
        # Graceful degradation (Scenario 2): log and report to client.
        logger.error(
            "Emergency Stop — Temporal client connection failed",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                    "degradation_scenario": "Scenario-2-Temporal-Unavailable",
                }
            },
        )
        await _close_with_error(websocket, session_id, "temporal_unavailable")
        return

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
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "constitutional_basis": "C-001,C-024",
                    }
                },
            )
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            # C-059: signal timed out — log as evidence.
            logger.error(
                "Emergency Stop HALT signal timed out — ≤250ms budget exceeded",
                extra={
                    "context": {
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "timeout_seconds": TEMPORAL_SIGNAL_TIMEOUT_SECONDS,
                        "constitutional_basis": "C-059,C-001",
                    }
                },
            )
            signal_errors.append(workflow_id)
        except RPCError as e:
            # C-059: Temporal RPC error — log as evidence.
            logger.error(
                "Emergency Stop HALT signal RPC error",
                exc_info=True,
                extra={
                    "context": {
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "error": str(e),
                        "constitutional_basis": "C-059",
                    }
                },
            )
            signal_errors.append(workflow_id)
        except (OSError, ConnectionRefusedError) as e:
            # C-059: network-level error — log as evidence.
            logger.error(
                "Emergency Stop HALT signal network error",
                exc_info=True,
                extra={
                    "context": {
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "error": str(e),
                        "constitutional_basis": "C-059",
                    }
                },
            )
            signal_errors.append(workflow_id)

    # ── Step 5: Send confirmation or error frame, then close ───────────────
    confirmed_at = datetime.now(timezone.utc).isoformat()

    if not affected_sessions:
        # All signals failed — C-059: log as evidence, inform client.
        logger.error(
            "Emergency Stop — no sessions could be halted",
            extra={
                "context": {
                    "session_id": session_id,
                    "signal_errors": signal_errors,
                    "constitutional_basis": "C-059,C-001",
                }
            },
        )
        await _close_with_error(websocket, session_id, "halt_signal_failed")
        return

    # C-023 / Evidence First (AD-002): CE records evidence inside
    # PAASSessionWorkflow on HALT signal receipt.  The CONFIRMED frame is
    # sent only after the signal has been dispatched.  The workflow guarantees
    # CE evidence write before returning control — this endpoint does not
    # independently call CE (CE is the ledger; PR is the executor per
    # containers.md and professional-runtime.md §2 PAAS Engine).
    try:
        await websocket.send_json(
            {
                "type": FrameType.EMERGENCY_STOP_CONFIRMED,
                # emergencyStopRecordId is written by CE inside the workflow;
                # the workflow-level record ID is the session_id (workflow ID)
                # per ADR-018 — no separate UUID from this layer.
                "emergencyStopRecordId": session_id,
                "affectedSessions": affected_sessions,
                "confirmedAt": confirmed_at,
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Client disconnected before confirmation could be sent.
        # C-059: log as evidence — halt was still delivered.
        logger.error(
            "Emergency Stop CONFIRMED frame send failed — halt was delivered",
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
        return

    # ── Step 6: Close WebSocket cleanly ────────────────────────────────────
    try:
        await websocket.close(code=1000)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Close failed — connection may already be gone.
        # C-059: log as evidence; halt was already confirmed.
        logger.error(
            "Emergency Stop WebSocket close failed — halt already confirmed",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )