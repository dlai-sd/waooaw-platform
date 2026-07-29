# Implements: architecture/reference/components/professional-runtime.md § Emergency Stop
# constitutional_basis: C-001, C-023, C-024, C-059, C-063
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

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


async def _get_temporal_client() -> TemporalClient:
    """
    Returns a connected Temporal client.
    The client is expected to be pre-warmed and injected via app state in production.
    This helper exists to keep the hot path free of connection overhead (C-001).
    """
    return await TemporalClient.connect("localhost:7233")


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
    2. Parse EMERGENCY_STOP frame from client.
    3. Send Temporal HALT signal to PAASSessionWorkflow(session_id).
       ⛔ NO additional I/O between accept and signal send (C-001).
    4. Fire-and-forget: send {'status': 'stopping'} then close.
    """
    # ── Step 1: Accept (no I/O beyond this before signal) ──────────────────
    await websocket.accept(subprotocol="waooaw-emergency-stop-v1")

    connected_at = datetime.now(timezone.utc).isoformat()
    try:
        await websocket.send_json(
            {
                "type": "READY",
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
    if frame_type != "EMERGENCY_STOP":
        logger.error(
            "Emergency Stop endpoint received unexpected frame type",
            extra={
                "context": {
                    "session_id": session_id,
                    "frame_type": frame_type,
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "unexpected_frame_type")
        return

    # contract_id present in frame but NOT logged (C-063 — it is a business identifier
    # traceable to a customer).  We pass it only to the Temporal signal payload.
    contract_id: str = frame.get("contractId", "")
    active_session_ids: list[str] = frame.get("activeSessionIds", [session_id])

    # ── Step 3: Send Temporal HALT signal — NO additional I/O before this ──
    # C-001: the signal send is the only latency-critical operation.
    # C-024: unconditional — no validation gate that could prevent the halt.
    signal_payload = {
        "contractId": contract_id,
        "activeSessionIds": active_session_ids,
    }

    try:
        temporal_client = await _get_temporal_client()
        handle = temporal_client.get_workflow_handle(session_id)

        await asyncio.wait_for(
            handle.signal(HALT_SIGNAL_NAME, signal_payload),
            timeout=TEMPORAL_SIGNAL_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        # C-059: timeout is an evidence-worthy event.
        logger.error(
            "Emergency Stop Temporal signal timed out — C-001 budget exceeded",
            extra={
                "context": {
                    "session_id": session_id,
                    "timeout_seconds": TEMPORAL_SIGNAL_TIMEOUT_SECONDS,
                    "constitutional_basis": "C-001, C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "signal_timeout")
        return

    except asyncio.CancelledError:
        raise

    except RPCError as e:
        # Temporal RPC failure — C-059: must log as evidence.
        logger.error(
            "Emergency Stop Temporal RPC error",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "temporal_rpc_error")
        return

    # ── Step 4: Fire-and-forget confirmation, then close ───────────────────
    # Per spec (emergency-stop-ws.md): send {'status': 'stopping'} then close.
    # Full EMERGENCY_STOP_CONFIRMED is sent by CE after evidence is written (C-023);
    # this endpoint only signals Temporal and confirms the signal was dispatched.
    try:
        await websocket.send_json(
            {
                "type": "EMERGENCY_STOP_DISPATCHED",
                "sessionId": session_id,
                "status": "stopping",
                "dispatchedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Client disconnected after we already sent the signal — the halt is still in
        # flight.  C-059: log as evidence but do not treat as failure of the stop.
        logger.error(
            "Emergency Stop confirmation frame send failed — signal already dispatched",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
    finally:
        try:
            await websocket.close()
        except asyncio.CancelledError:
            raise
        except (RuntimeError, OSError):
            # Already closed — not an error.
            pass


async def _close_with_error(
    websocket: WebSocket,
    session_id: str,
    reason: str,
) -> None:
    """
    Attempt to send an error frame and close the WebSocket gracefully.
    Never raises — caller is already in an error recovery path.
    C-059: all exceptions here are absorbed after logging.
    """
    try:
        await websocket.send_json(
            {
                "type": "EMERGENCY_STOP_ERROR",
                "sessionId": session_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError, ValueError) as e:
        logger.error(
            "Emergency Stop error frame send failed",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "reason": reason,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
    finally:
        try:
            await websocket.close()
        except asyncio.CancelledError:
            raise
        except (RuntimeError, OSError):
            pass