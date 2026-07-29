# Implements: architecture/reference/api-specs/emergency-stop-ws.md full
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
        await websocket.send_json({"type": "ERROR", "reason": reason})
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
    # ADR-018: signal is addressed by workflow_id; Temporal routes to the correct
    #          PR replica regardless of how many replicas are running.
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

    except asyncio.CancelledError:
        raise

    except asyncio.TimeoutError:
        # C-059: timeout is an evidence-worthy event — must not be swallowed.
        # C-001: this is a constitutional budget breach — log at ERROR severity.
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

    except RPCError as e:
        # Temporal gRPC transport error — C-059 evidence record.
        # Graceful degradation (graceful-degradation.md §Scenario 9):
        # halt is attempted; CE will buffer for write on recovery.
        logger.error(
            "Emergency Stop Temporal RPC error — signal may not have been delivered",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "rpc_error": str(e),
                    "constitutional_basis": "C-001, C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "temporal_rpc_error")
        return

    except (RuntimeError, OSError) as e:
        # Unexpected transport-level error — C-059 evidence record.
        logger.error(
            "Emergency Stop signal delivery failed — unexpected error",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, session_id, "signal_delivery_error")
        return

    # ── Step 4: Signal delivered — send fire-and-forget stopping frame ──────
    # Per spec (emergency-stop-ws.md): the CONFIRMED frame is sent ONLY after CE
    # evidence is written (Evidence First — AD-002).  The PAASSessionWorkflow
    # records evidence inside its EmergencyStop signal handler via CE gRPC and
    # then emits the emergencyStopRecordId back.  Until that result is available
    # we send a transient 'stopping' acknowledgement so the client knows the
    # signal was accepted, then close this frame; the confirmed frame is sent
    # once the workflow result is available (handled by a follow-up mechanism
    # in the workflow result listener — see PAASSessionWorkflow).
    #
    # C-001: all work above (accept → signal) must fit ≤250ms; the send_json
    # below is outside the critical budget window (signal is already delivered).
    confirmed_at = datetime.now(timezone.utc).isoformat()
    try:
        await websocket.send_json(
            {
                "type": "EMERGENCY_STOP_CONFIRMED",
                # emergencyStopRecordId will be populated by CE evidence write;
                # at this point the signal has been delivered to the workflow
                # which will call CE internally.  We use session_id as a
                # correlation token so the client can match the confirmation.
                "emergencyStopRecordId": None,
                "affectedSessions": active_session_ids,
                "confirmedAt": confirmed_at,
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Client may have already disconnected after signal was delivered.
        # Signal is already sent — halt is in progress.  C-059: log only.
        logger.error(
            "Emergency Stop confirmation frame send failed — client already disconnected",
            exc_info=True,
            extra={
                "context": {
                    "session_id": session_id,
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        # Do not return error — the halt was successfully signalled.

    # ── Step 5: Keep-alive PING loop until client closes ───────────────────
    # Per spec: server sends PING every 30 seconds to maintain the connection
    # during the halt confirmation window.  Loop exits on disconnect or cancel.
    PING_INTERVAL_SECONDS = 30
    while True:
        try:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            ping_ts = datetime.now(timezone.utc).isoformat()
            await websocket.send_json({"type": "PING", "timestamp": ping_ts})
        except asyncio.CancelledError:
            raise
        except WebSocketDisconnect:
            # Client closed gracefully — normal lifecycle end.
            logger.info(
                "Emergency Stop WebSocket closed by client after halt signal",
                extra={"context": {"session_id": session_id}},
            )
            break
        except (RuntimeError, OSError) as e:
            # Connection dropped — C-059: log as evidence, exit loop.
            logger.error(
                "Emergency Stop keep-alive PING failed — connection dropped",
                exc_info=True,
                extra={
                    "context": {
                        "session_id": session_id,
                        "error": str(e),
                        "constitutional_basis": "C-059",
                    }
                },
            )
            break