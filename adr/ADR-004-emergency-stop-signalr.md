# ADR-004: Emergency Stop Transport — Azure SignalR vs Plain WebSocket

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Solution Architect (real-time communication pattern) + Security Architect (authentication on persistent connections)
**Constitutional Basis:** Constitution Article IX (Constitutional Floors — Human override is absolute and architecturally guaranteed); Constitution Amendment A-004 (Legitimate Conduct — Constitutional Floors cannot be disabled by configuration)

---

## Context

The Emergency Stop is a Constitutional Floor. A customer must be able to halt all active professional operations within 250ms of issuing the command. This is guaranteed regardless of load, scaling, or infrastructure state.

The Emergency Stop path: Customer mobile/web → rt.waooaw.com → Professional Runtime → halt operations.

The transport must:
- Deliver halt instruction within 250ms end-to-end
- Work on mobile (React Native, PWA)
- Survive service restarts (reconnection)
- Scale horizontally (multiple Professional Runtime replicas)
- Authenticate the customer (only the contract owner can Emergency Stop)

## Decision

**Azure SignalR Service in cloud environments; plain WebSocket in development.**

The Emergency Stop WebSocket connection is established when a customer's active session begins. The connection is maintained for the session duration.

```
Customer Mobile/PWA
  → Connects to rt.waooaw.com/ws/emergency-stop/{contractId}
  → Azure SignalR manages connection state and routing
  → Professional Runtime registers as SignalR hub backend
  → Customer sends "STOP" message
  → SignalR routes to correct Professional Runtime instance
  → Professional Runtime halts operations (≤250ms from message receipt)
  → Confirmation sent back to customer
```

In development (Docker Compose):
```
Customer → localhost:5003/ws/emergency-stop/{contractId}
  → Professional Runtime plain WebSocket handler
```

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| HTTP polling | Cannot guarantee 250ms. Adds database load. Constitutionally unacceptable. |
| Server-Sent Events | One-directional (server → client only). Cannot receive STOP command. |
| Plain WebSocket in cloud | Does not scale horizontally. If 3 Professional Runtime replicas exist, connection state is not shared. STOP message might reach wrong replica. |
| Azure SignalR | Managed connection state, horizontal scale, 5ms internal latency, ~₹200/month at low scale. |

## Consequences

**Benefits:**
- 250ms constitutional guarantee is architecturally enforced
- Horizontal scaling of Professional Runtime without connection state problems
- Reconnection handled automatically by SignalR SDK (mobile connection drops)

**Trade-offs:**
- Azure SignalR adds ~₹200/month in cloud (acceptable — constitutional floor cost)
- Dev environment uses plain WebSocket (simpler, same interface, different transport)

**Authentication:**
- JWT is sent in the WebSocket upgrade `Authorization: Bearer <token>` header **only**
- JWT must **never** be placed in a query parameter — query parameters appear in server access logs, proxy logs, and browser history (OWASP A02: Cryptographic Failures)
- Professional Runtime validates JWT signature and extracts `tenant_id` + `sub` before accepting the connection
- Only the customer whose `sub` matches the contract owner field can Emergency Stop that `contractId`
- Connection is rejected with `401 Unauthorized` before the WebSocket upgrade completes if JWT is invalid or absent
