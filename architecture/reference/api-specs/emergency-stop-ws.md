# Emergency Stop WebSocket — Frame Specification

**Produced by:** Solution Architect (R-010-01 outstanding gap)
**Date:** 2026-07-07
**Constitutional Basis:** C-001 (Emergency Stop absolute), AD-001 (≤250ms end-to-end), ADR-004 (WebSocket transport)

---

## Overview

The Emergency Stop WebSocket is a dedicated, pre-warmed persistent connection between the customer's browser/mobile app and the Professional Runtime service. It is the PRIMARY path for Emergency Stop — the REST fallback (`POST /api/v1/emergency-stop`) is a secondary path when the WebSocket cannot be established.

**Connection endpoint:** `wss://rt.waooaw.com/ws/emergency-stop`  
**Dev endpoint:** `ws://localhost:5003/ws/emergency-stop`  
**Protocol:** WebSocket (RFC 6455)  
**Authentication:** `Authorization: Bearer <JWT>` header — **never in query string** (ADR-004)

---

## Connection Lifecycle

```
Customer opens authenticated session
        ↓
Client establishes WebSocket:
  GET ws://rt.waooaw.com/ws/emergency-stop
  Headers:
    Authorization: Bearer <Keycloak JWT>
    Sec-WebSocket-Protocol: waooaw-emergency-stop-v1
        ↓
Server validates JWT (RS256, 7-step check per security-architecture.md §2)
If JWT invalid → HTTP 401 (WebSocket upgrade refused, not a 101)
If JWT valid → HTTP 101 Switching Protocols
        ↓
Connection established. Server sends READY frame (see below).
        ↓
Connection maintained for duration of customer session.
Customer or server can send frames at any time.
        ↓
On session end: client sends CLOSE frame. Server acknowledges. Connection closed.
```

---

## Frame Format (JSON over WebSocket text frames)

### Client → Server: EmergencyStopCommand

```json
{
  "type": "EMERGENCY_STOP",
  "contractId": "uuid-of-the-employment-contract",
  "activeSessionIds": ["temporal-workflow-id-1", "temporal-workflow-id-2"]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | string | Yes | Always `"EMERGENCY_STOP"` |
| `contractId` | UUID string | Yes | The Employment Contract being stopped |
| `activeSessionIds` | UUID[] | No | Known active PAAS session IDs (Temporal workflow IDs per ADR-018). If omitted, server halts all known sessions for the contract. |

### Server → Client: EmergencyStopConfirmation

```json
{
  "type": "EMERGENCY_STOP_CONFIRMED",
  "emergencyStopRecordId": "uuid-of-evidence-record",
  "affectedSessions": ["temporal-workflow-id-1"],
  "confirmedAt": "2026-07-07T09:15:23.456Z"
}
```

**Sent only after Constitutional Engine confirms the Emergency Stop evidence record is written (Evidence First — AD-002). The client MUST wait for this frame before showing "STOPPED" to the customer. Do not optimistically show confirmation.**

### Server → Client: READY (sent on connection establishment)

```json
{
  "type": "READY",
  "contractId": "uuid",
  "connectedAt": "2026-07-07T09:00:00.000Z"
}
```

### Server → Client: PING (keep-alive, every 30 seconds)

```json
{ "type": "PING", "timestamp": "2026-07-07T09:00:30.000Z" }
```

### Client → Server: PONG (response to PING)

```json
{ "type": "PONG", "timestamp": "2026-07-07T09:00:30.001Z" }
```

### Server → Client: ERROR

```json
{
  "type": "ERROR",
  "code": "INVALID_CONTRACT" | "JWT_EXPIRED" | "SESSION_NOT_FOUND" | "INTERNAL",
  "message": "Human-readable error description"
}
```

---

## Reconnection Strategy

The Emergency Stop connection MUST be re-established automatically when dropped. A gap in the Emergency Stop connection is a constitutional risk — the customer may be unable to stop an active professional.

**Client reconnection algorithm:**

```
On connection drop (or CLOSE from server):
  1. Attempt reconnect immediately
  2. If fails: wait 1 second, retry
  3. If fails: wait 2 seconds, retry
  4. If fails: wait 4 seconds, retry (exponential backoff, cap at 10s)
  5. After 5 consecutive failures: show WARNING to customer
     "Emergency Stop connection interrupted. Attempting to restore..."
  6. Continue retrying every 10 seconds until restored
  7. On restoration: send a READY acknowledgment and verify contractId

On reconnection:
  → Server re-validates JWT (if expired, redirect to Keycloak refresh flow)
  → Server sends READY frame with current connection state
  → Client resumes normal monitoring
```

**If the customer's JWT expires during a session:**
The WebSocket connection will be closed by the server with code 4001 (JWT expired). The client must silently refresh the JWT via Keycloak's refresh token endpoint and re-establish the WebSocket. During the ≤2-second gap, the REST fallback is available.

---

## Keep-Alive Protocol

**Server heartbeat:** every 30 seconds, server sends PING frame.  
**Client response:** client must respond with PONG within 5 seconds.  
**Server behaviour on timeout:** close connection with code 1001 (Going Away).

**Why this matters:** Azure SignalR / Azure Container Apps have idle connection timeouts. The 30-second heartbeat ensures the connection is never classified as idle.

---

## Latency Guarantees

| Segment | Budget | Notes |
|---|---|---|
| WebSocket frame delivery to server | ≤ 10ms | Pre-established connection on local Azure network |
| Professional Runtime halt initiation | ≤ 20ms | In-memory PAAS session halt |
| Temporal signal to correct replica | ≤ 10ms | ADR-018 signal routing |
| CE TriggerEmergencyStop gRPC | ≤ 80ms | CE evidence write + DB commit |
| EmergencyStopConfirmation frame to client | ≤ 10ms | Response on existing connection |
| **Total P99** | **≤ 250ms** | **Constitutional Floor (C-001)** |

The client MUST measure this round-trip in production and emit it as an OTel metric: `constitutional.emergency_stop.latency_ms` (per engineering-standards.md §8).

---

## Implementation Notes for Runtime Professional

1. Professional Runtime registers the WebSocket route at `/ws/emergency-stop` in FastAPI.
2. JWT is validated on connection (before upgrade). Connection refused if JWT invalid.
3. A separate asyncio task handles PING/PONG keepalives — never block the main WebSocket handler.
4. `contractId` extracted from JWT claim — the client-provided `contractId` in the frame must match the JWT `tenant_id`'s contracts. Mismatch → ERROR frame, connection maintained.
5. `activeSessionIds` passed to CE `TriggerEmergencyStop` gRPC call.
6. CE confirmation must be received before sending `EMERGENCY_STOP_CONFIRMED` to client.
7. The REST fallback endpoint (`POST /api/v1/emergency-stop`) uses the same underlying logic — CE gRPC call, same confirmation requirement.

---

## Web App Implementation Notes

1. Establish WebSocket on user login (not on the emergency stop page — it must already exist).
2. Store the WebSocket connection in React context — accessible from every authenticated component.
3. The Emergency Stop button calls `ws.send(JSON.stringify({ type: "EMERGENCY_STOP", contractId, activeSessionIds }))`.
4. Button shows loading state until `EMERGENCY_STOP_CONFIRMED` frame received.
5. Never show "STOPPED" before confirmation — the customer must know if the stop failed.
6. Display reconnection status (READY → CONNECTING → RECONNECTING) in a subtle status indicator.
