# ADR-018: Emergency Stop Signal Routing via Temporal

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Enterprise Architect (signal routing design) + Solution Architect (component interaction)
**Constitutional Basis:** C-013 (Emergency Override — absolute constitutional right); C-001 (human override architecturally guaranteed); AD-001 (≤250ms end-to-end Emergency Stop); ADR-005 (PAAS session affinity — sessions are replica-bound in memory)

---

## Context

The R-007 critical review identified GAP-003:

> *"At scale with multiple Professional Runtime replicas, an Emergency Stop for a customer must halt the SPECIFIC replica holding that customer's PAAS session. The TriggerEmergencyStop RPC arrives at the Constitutional Engine — but CE doesn't know which Professional Runtime replica owns the session. This is unspecified."*

The problem:

```
Customer issues Emergency Stop
  → Business Platform → Constitutional Engine: TriggerEmergencyStop(contract_id)
  → CE records the stop event
  → CE must signal the correct Professional Runtime replica to halt
  → But which replica? CE has no registry of "replica X owns session Y"
```

ADR-005 uses session affinity: the same Container Apps client IP is routed to the same PR replica. But CE is not a client of PR (CE is internal). CE cannot use session affinity to find the right replica. CE making a direct HTTP call to "the PR replica holding session S" would require CE to maintain a session registry — coupling CE to PR's scaling topology, which is architecturally wrong.

---

## Decision

**PAAS sessions are modelled as Temporal workflows. Emergency Stop is delivered via Temporal signal.**

```
PAAS session lifecycle:
  Customer opens PAAS session
    → Professional Runtime starts Temporal workflow: PAASSessionWorkflow(session_id)
    → Workflow runs indefinitely (until customer ends session, Emergency Stop, or timeout)
    → All PAAS action executions are Temporal activities within this workflow
    → The Temporal worker that picks up the workflow activities IS the PR replica

Emergency Stop delivery:
  CE receives TriggerEmergencyStop(contract_id, active_session_ids=[workflow_id_1, ...])
    → CE uses Temporal client to send signal: PAASSessionWorkflow.EmergencyStop
    → Temporal server routes the signal to the worker currently executing the workflow
    → The PR replica (Temporal worker) receives the signal
    → Worker halts current activity, records ABANDONED evidence via CE gRPC, confirms halt
    → CE records Emergency Stop event in Constitutional Audit Ledger
    → CE returns confirmed halt to caller (within AD-001 budget)
```

**Why Temporal signals solve the fan-out problem:**

Temporal's signal mechanism is replica-independent. The signal is addressed to a workflow by `workflow_id`. Temporal server knows which worker is executing that workflow and routes the signal there. The routing is Temporal's responsibility — not CE's, not the load balancer's. This is the correct separation of concerns.

---

## Design Additions Required

### 1. PAAS Session as Temporal Workflow

`PAASSessionWorkflow` is a long-running Temporal workflow with:
- Start: Decision Space loaded into memory, session registered
- Activities: each PAAS action execution is a Temporal activity
- Signal handler: `EmergencyStop` signal triggers immediate halt of in-flight activity, records ABANDONED evidence
- End: normal session close (market hours end, customer closes session), Emergency Stop, or Decision Space version change

The workflow ID is the session ID. The session ID is the unit of routing for Emergency Stop.

### 2. Constitutional Engine Temporal Client

Constitutional Engine adds a Temporal client dependency (it already has a PostgreSQL dependency). The CE uses this client ONLY for sending Emergency Stop signals — not for workflow orchestration (which remains Professional Runtime's responsibility).

This is a narrow, justified addition to CE's dependencies. The CE does not become a Temporal workflow author; it becomes a signal sender on the safety-critical path.

### 3. active_session_ids = Temporal Workflow IDs

In `EmergencyStopRequest`, the `active_session_ids` field (already in `constitutional_service.proto`) carries the Temporal workflow IDs of active PAAS sessions for the contract. Business Platform must pass these IDs when calling CE's `TriggerEmergencyStop`. Business Platform knows the active session IDs because it records them when the PAAS session starts (in `business.paas_sessions` — see GAP-004 resolution).

### 4. Latency Budget Compatibility

Temporal signal delivery: `< 10ms` on the same Container Apps environment. This fits within the existing latency budget:

| Segment | Budget (AD-005) | With Temporal signal |
|---|---|---|
| PAAS hot path | < 50ms | unchanged |
| CE evidence recording | < 80ms | unchanged |
| Emergency Stop detection + routing | < 50ms | signal delivery < 10ms ✓ |
| Halt + confirm | < 50ms | unchanged |
| Safety margin | ~20ms | maintained |
| **Total** | **≤250ms** | **≤250ms ✓** |

---

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| CE maintains session-to-replica registry | CE must be updated on every PR scale event. Tight coupling between CE and PR scaling topology. If the registry is stale, Emergency Stop fails. This is not architecturally acceptable for a safety-critical path. |
| Redis pub/sub: CE publishes stop event; all PR replicas subscribe | All replicas receive the signal; only the owning replica acts. Works, but: adds Redis to the infrastructure, adds latency (Redis round trip), and distributes the halt logic to every replica rather than the owning replica. Complexity without benefit over Temporal signals. |
| PR directly handles all Emergency Stops via WebSocket | This only works when the Emergency Stop arrives via the WebSocket connection. If the customer sends Emergency Stop via the web UI REST call → Business Platform → CE, there is no WebSocket path. Both paths must work. |
| Direct HTTP from CE to PR replica | Requires CE to know the address of the specific PR replica — which changes on scaling, restarts, and failovers. Not feasible in a dynamic Container Apps environment without a service mesh or registry. |

---

## Consequences

**Benefits:**
- Emergency Stop delivery is replica-independent — works identically at 1 PR replica and at 100
- Temporal handles the routing; CE does not need to know PR's topology
- Signal delivery is durable — Temporal persists signals until the workflow receives them
- If the owning replica crashes between signal send and receive, Temporal re-routes to a new replica on workflow restart
- No new infrastructure required (Temporal is already in the stack, ADR-015)

**Trade-offs:**
- PAAS session must be modelled as a Temporal workflow (existing component specs describe the PAAS Engine but did not explicitly state the workflow model — component specs require update per EA-007-04)
- CE gains a Temporal client dependency (narrow, justified, documented here)
- Session IDs must be passed in `TriggerEmergencyStop` — Business Platform must track active sessions (requires `business.paas_sessions` table, GAP-004 resolution)
