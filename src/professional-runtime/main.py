"""
Professional Runtime — main.py
Handles: PAAS execution, Approval-Gate execution, Emergency Stop WebSocket.
Constitutional Basis: C-035 (Runtime Universality), C-001 (Emergency Stop absolute),
                      ADR-018 (Temporal signal routing), ADR-020 (MCP tools)
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

# ─── Observability (ADR-009) ──────────────────────────────────────────────────
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup_telemetry() -> None:
    resource = Resource.create({"service.name": "professional-runtime"})
    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    )
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("professional-runtime")

# ─── Startup / shutdown ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Professional Runtime starting — constitutional governance active")
    yield
    logging.info("Professional Runtime shutting down")

app = FastAPI(
    title="WAOOAW Professional Runtime",
    description="Executes digital professional work under constitutional governance.",
    lifespan=lifespan
)

# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, Any]:
    """
    Health check endpoint.
    Returns constitutional engine reachability and active PAAS session count.
    """
    return {
        "status": "healthy",
        "temporalConnected": True,   # TODO Sprint 2: check real Temporal connection
        "constitutionalEngineReachable": True,  # TODO Sprint 2: CE gRPC health probe
        "activePAASSessions": 0      # TODO Sprint 2: read from PAASSession registry
    }

# ─── Emergency Stop WebSocket (C-001, AD-001, ADR-004) ────────────────────────
@app.websocket("/ws/emergency-stop")
async def emergency_stop_websocket(websocket: WebSocket) -> None:
    """
    Emergency Stop WebSocket — pre-warmed persistent connection.
    Customer connects at session start; sends EmergencyStopCommand when needed.
    Constitutional Floor: must respond within 250ms P99 (AD-001).
    Authentication: Bearer JWT in Authorization header (never in query string — ADR-004).
    """
    # TODO Sprint 2: Validate JWT from WebSocket headers
    # TODO Sprint 2: Check Authorization: Bearer <token> header

    await websocket.accept()

    # Send READY frame (emergency-stop-ws.md specification)
    await websocket.send_json({"type": "READY", "connectedAt": "2026-07-08T00:00:00Z"})
    logging.info("Emergency Stop WebSocket connected — constitutional coverage active")

    # Keepalive ping task (emergency-stop-ws.md — 30s heartbeat)
    async def send_pings() -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "PING"})
            except Exception:
                break

    ping_task = asyncio.create_task(send_pings())

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "PONG":
                continue  # Heartbeat response — ignore

            if msg_type == "EMERGENCY_STOP":
                with tracer.start_as_current_span("constitutional.emergency_stop"):
                    contract_id = data.get("contractId")
                    session_ids = data.get("activeSessionIds", [])

                    logging.warning(
                        "EMERGENCY STOP received: contract=%s sessions=%s",
                        contract_id, session_ids
                    )

                    # TODO Sprint 2: Call CE.TriggerEmergencyStop gRPC
                    # TODO Sprint 2: Send Temporal signals to PAASSessionWorkflow (ADR-018)

                    # Confirmation sent AFTER CE confirms evidence recorded (Evidence First)
                    await websocket.send_json({
                        "type": "EMERGENCY_STOP_CONFIRMED",
                        "emergencyStopRecordId": "stub-not-yet-ce-confirmed",
                        "affectedSessions": session_ids,
                        "confirmedAt": "2026-07-08T00:00:00Z"
                    })
            else:
                logging.warning("Unknown WebSocket message type: %s", msg_type)

    except WebSocketDisconnect:
        logging.info("Emergency Stop WebSocket disconnected — customer session ended")
    finally:
        ping_task.cancel()

# ─── PAAS Session Management (internal — called by Business Platform) ─────────
@app.post("/api/v1/paas/sessions")
async def start_paas_session(body: dict[str, Any]) -> dict[str, Any]:
    """
    Start a PAAS session (ADR-018 — creates PAASSessionWorkflow in Temporal).
    Internal endpoint — not accessible from internet.
    """
    contract_id = body.get("contractId")
    # TODO Sprint 2: Start PAASSessionWorkflow via Temporal SDK
    session_id = "stub-session-id"
    logging.info("PAAS session started (stub): contract=%s session=%s", contract_id, session_id)
    return {"sessionId": session_id, "contractId": contract_id, "state": "STARTING"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5003, log_level="info")
