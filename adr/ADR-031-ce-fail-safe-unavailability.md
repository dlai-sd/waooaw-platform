# ADR-031: Constitutional Engine Fail-Safe Behavior on Unavailability

**Status:** Accepted
**Date:** 2026-07-23
**Roles Applied:** Enterprise Architect + Solution Architect + Security Architect
**Constitutional Basis:** C-079 (CE Fail-Safe Halt on Unavailability — RATIFIED); C-023 (Evidence First); C-001 (Human Override); C-003 (Authority Licensed Through Evidence)

---

## Context

The Constitutional Engine (CE) is a mandatory synchronous dependency for every action taken by Business Platform (BP) and Professional Runtime (PR). Every evidence write, every action validation, every Emergency Stop flows through CE.

The original CE design (ADR-001) specified gRPC as the protocol and Evidence First as the law, but did not specify what happens when CE is unreachable. This created an implicit assumption: CE is always available. The audit (2026-07-23) identified this as a High gap — a single point of failure with undefined behavior.

The question this ADR answers: **What must BP and PR do when CE is unreachable?**

---

## Options Considered

### Option 1 — Silent bypass: continue acting without CE confirmation

Rejected immediately. This is a C-023 violation. Evidence First is a constitutional law, not a suggestion. Acting without CE evidence is an unauthorized action regardless of why CE is unavailable.

### Option 2 — Short-circuit cache: replay last known CE responses for N minutes

Rejected. Tempting for latency, but constitutionally unsound:
- A CE DENY decision from 5 minutes ago may have been superseded (authority was granted or revoked)
- Authority licenses and Decision Spaces can be updated at any time — cache invalidation is not guaranteed
- Emergency Stop signals may have fired during the window — replaying old ALLOW decisions after an Emergency Stop is a catastrophic failure mode

### Option 3 — Fail-safe halt: all CE-dependent operations pause until CE recovers

**Selected.** This is the only constitutionally compliant option. When governance is absent, autonomous action stops. This is the constitutional default (C-079).

### Option 4 — Read-only degraded mode: allow reads, block writes

This is actually a subset of Option 3 and is compatible. Read operations (evidence viewing, approval history) do not require CE writes, so they may continue. Only operations that require CE validation or CE evidence writes must halt. This refinement is incorporated into the decision.

---

## Decision

**When CE is detected as unavailable, BP and PR enter Fail-Safe Halt mode. All CE-dependent write operations are suspended. Read operations continue. Recovery is automatic.**

---

## Detection Mechanism

CE unavailability is detected by each caller independently using gRPC health checks:

```
Detection trigger (either):
  A. grpc_health_probe returns NOT_SERVING or connection refused
  B. Any gRPC call to CE returns status code UNAVAILABLE
  C. gRPC call timeout exceeded (deadline: 5 seconds per call — ADR-001 standard)

Confirmation: 2 consecutive failures within 5 seconds = CE declared UNAVAILABLE
  (prevents false positives from transient network blips)

Check interval: every 2.5 seconds (active health probe on CE gRPC health endpoint)
  - BP: polls CE health endpoint via gRPC HealthCheckService
  - PR: polls same endpoint; also detects via UNAVAILABLE on any live call
```

---

## Fail-Safe Halt Behavior by Service

### Business Platform — Halt Behavior

```
CE declared UNAVAILABLE:
  1. Log constitutional event: ce_unavailable, timestamp, last_seen_available
  2. Set in-memory flag: ce_circuit_open = true
  3. Notify Steward Assistant: WhatsApp message within 60 seconds
     "CONSTITUTIONAL ALERT: CE unavailable since {time}. Platform in fail-safe halt.
      Approximate SLA for CE recovery: 2 minutes. No autonomous actions executing."

Incoming HTTP requests while ce_circuit_open = true:
  - /api/v1/employment/* (write operations): 503 Service Unavailable
    Body: { "error": "GOVERNANCE_UNAVAILABLE",
            "message": "The governance service is temporarily unavailable. Your request
                        has been queued and will be processed when governance resumes.",
            "retry_after": 30,
            "constitutional_basis": "C-079" }
    Retry-After header: 30 seconds
  - /api/v1/approvals/* (state transitions): 503 Service Unavailable (same body)
  - /api/v1/authority/* (grants/revocations): 503 Service Unavailable (same body)
  - /api/v1/evidence/* (read): 200 OK — no CE call required for reads
  - /api/v1/approvals/{id} (read): 200 OK — no CE call required for reads
  - Emergency Stop endpoint: Queued locally (see Emergency Stop section below)

Queuing: BP does NOT queue write operations for replay.
  Rationale: Replaying a queued employment action after CE recovery may be constitutionally
  stale (authority may have changed during the halt). Customers re-submit after recovery.
  Queue is for Emergency Stop ONLY (see below).
```

### Professional Runtime — Halt Behavior

```
CE declared UNAVAILABLE:
  1. Log constitutional event (same as BP)
  2. Pause all active PAAS execution loops:
     - Stop dispatching new Temporal activities from AgentExecutionWorkflow
     - Current in-flight activity: completes its current step, then halts before next CE call
     - Temporal heartbeat continues (workflow stays alive, does not time out)
     - PAAS session state: enters PAASSession.state = HALTED_CE_UNAVAILABLE
  3. Session audit record: append HALT_RECORD to constitutional.evidence_records
     (if this fails because CE is unreachable, record to local audit buffer — see below)

Local Audit Buffer (CE unavailable — evidence cannot be written):
  - PR maintains an in-memory circular buffer (max 1,000 records, 10MB)
  - Every governance event that WOULD have been written to CE is appended to this buffer
  - On CE recovery: buffer is flushed to CE in chronological order before any new actions
  - Buffer overflow (> 1,000 records): halt all sessions — something is very wrong
```

### Emergency Stop During CE Unavailability

Emergency Stop is the one operation that cannot wait for CE recovery:

```
Emergency Stop received (via WebSocket) while CE is unavailable:
  1. PR executes the local halt IMMEDIATELY (stops all PAAS activities — no CE call needed for the halt itself)
  2. PR records the Emergency Stop in the local audit buffer
  3. PR marks WebSocket session as EMERGENCY_STOPPED
  4. On CE recovery: flushes local audit buffer → CE records Emergency Stop with timestamp
  5. CE: records emergency_stop_records row with {stopped_at: original timestamp, ce_delay_ms: recovery_delay}

The customer receives Emergency Stop confirmation within the standard ≤250ms SLA because:
- The halt itself (step 1) is local — no CE call in the halt path
- The constitutional record (step 4) is deferred but guaranteed
- The emergency_stop_records.ce_delay_ms documents the deferred recording for audit
```

---

## Recovery

```
CE recovery detection:
  - grpc_health_probe returns SERVING → recovery confirmed
  - BP and PR independently detect recovery via health probe

Recovery sequence (ordered — must complete in this order):
  1. Flush local audit buffer → CE (PR only, if buffer is non-empty)
  2. Flush queued Emergency Stops → CE (if any)
  3. Clear ce_circuit_open flag in BP
  4. Resume PAAS sessions: PAASSession.state → ACTIVE; Temporal activities resume
  5. Log constitutional event: ce_recovered, duration_unavailable_ms
  6. Notify Steward Assistant: "CE recovered. Platform resuming. Unavailability: {duration}ms."
  7. Make constitutional.engine_availability_events record (unavailability start, end, duration)
```

---

## Constitutional Compliance Test

### CCT-CE-AVAIL-01 — PAAS Sessions Halt on CE Unavailability

```python
# Location: tests/constitutional/test_ce_availability.py
# Authority: C-079

# Scenario: CE is killed (chaos injection). Verify all PAAS sessions halt within 5s.
# Tool: Azure Chaos Studio (chaos experiment on CE container)
# or: docker stop constitutional-engine (dev environment)

async def test_paas_sessions_halt_on_ce_unavailability(chaos_client, pr_client):
    # ARRANGE: Start 3 active PAAS sessions
    sessions = await start_three_paas_sessions(pr_client)
    assert all(s.state == "ACTIVE" for s in sessions)

    # ACT: Kill CE
    await chaos_client.stop_service("constitutional-engine")
    await asyncio.sleep(5)  # Wait for detection + halt

    # ASSERT: All sessions halted
    refreshed = await pr_client.get_sessions([s.id for s in sessions])
    assert all(s.state == "HALTED_CE_UNAVAILABLE" for s in refreshed)

    # ASSERT: No new actions were executed during the halt window
    actions_during_halt = await get_actions_after(timestamp=chaos_start)
    assert len(actions_during_halt) == 0  # constitutional requirement: zero actions without CE

    # CLEANUP: Restore CE, verify recovery
    await chaos_client.start_service("constitutional-engine")
    await asyncio.sleep(30)  # Wait for recovery
    refreshed = await pr_client.get_sessions([s.id for s in sessions])
    assert all(s.state == "ACTIVE" for s in refreshed)
```

---

## New Table: constitutional.engine_availability_events

```sql
CREATE TABLE constitutional.engine_availability_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unavailable_since   TIMESTAMPTZ NOT NULL,
    recovered_at        TIMESTAMPTZ,
    duration_ms         BIGINT,  -- computed: recovered_at - unavailable_since
    detecting_service   VARCHAR(30) NOT NULL,  -- 'business_platform' | 'professional_runtime'
    local_buffer_size   INTEGER,  -- how many records were buffered during halt
    sessions_halted     INTEGER,  -- how many PAAS sessions were halted
    emergency_stops_queued INTEGER DEFAULT 0,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
    -- append-only: no UPDATE, no DELETE
);
```

---

## Consequences

**Positive:**
- C-079 is fully compliant — no action executes without CE authorization, ever
- Emergency Stop remains effective even during CE unavailability
- Local audit buffer preserves constitutional integrity even during CE outages
- Clear operational behavior eliminates improvised incident responses

**Negative:**
- Business Platform becomes temporarily unavailable for write operations during CE downtime
- PAAS sessions pause — agent work is delayed, not lost
- Recovery involves a buffer flush which adds ~30 seconds to CE recovery time

**Accepted:** The negative consequences are constitutional requirements, not defects. An agent system that continues acting without governance is not a reliable system — it is a chaotic one.

---

## References
- C-079 (CE Fail-Safe Halt — authorizing claim)
- C-023 (Evidence First — foundational constraint)
- ADR-001 (gRPC for CE — the protocol this builds on)
- architecture/reference/graceful-degradation.md (full degradation manifest)
- architecture/reference/components/constitutional-engine.md (§6 — Unavailability Behavior)
