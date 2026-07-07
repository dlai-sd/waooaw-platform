# ADR-005: PAAS Session Isolation Strategy

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Enterprise Architect (scaling and isolation pattern) + Solution Architect (component design)
**Constitutional Basis:** Constitution Article III (Second Law — authority licensed through constitutional evidence); Constitution Article VI (Three-Ledger Model — Customer Evidence Ledger is private and owned by the customer)

---

## Context

The Pre-Authorized Action Space (PAAS) execution model (used by Trading Professionals) requires:
1. Decision Space parameters loaded into memory at session start
2. In-memory validation per action (zero network calls in execution hot path)
3. No cross-session data contamination (Trader A's risk parameters must never influence Trader B's execution)

The question is: should multiple PAAS sessions share one Professional Runtime instance (with careful cache management), or should each active PAAS session get its own dedicated instance?

## Decision

**Session-affinity: Each active PAAS session is handled by a dedicated Professional Runtime instance.**

Azure Container Apps session affinity routes all requests from a given customer session to the same replica. The PAAS Engine loads the customer's Decision Space into memory at session start and holds it for the session duration.

```
Customer A opens PAAS session
  → Container Apps assigns Replica-1
  → Replica-1 loads Customer A's Decision Space into memory
  → All Customer A's execution requests route to Replica-1

Customer B opens PAAS session
  → Container Apps assigns Replica-2
  → Replica-2 loads Customer B's Decision Space into memory
  → Zero cross-contamination possible
```

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Shared instance with in-memory keyed cache | Cache invalidation risk. If cache eviction policy is wrong, Customer A could see stale Decision Space. In financial execution, this could mean executing outside licensed parameters — constitutional violation. |
| Database lookup per action | Adds ~10ms per action. Incompatible with <250ms total execution guarantee. |
| Redis session cache | Adds infrastructure complexity. Cache miss still requires DB. Not faster than in-memory for hot path. |

## Consequences

**Benefits:**
- Zero risk of cross-session Decision Space contamination
- No cache invalidation logic required
- In-memory validation is <1ms (Decision Space is loaded once per session)

**Trade-offs:**
- Higher memory usage per concurrent PAAS session
- Scaling: 100 concurrent PAAS customers = 100 replicas (but PAAS sessions are time-bounded — 09:15–15:25 IST for NIFTY)
- Container Apps scale-to-zero applies at session end — no idle cost

**Replica failure recovery:**
- If the assigned replica crashes mid-session, Container Apps assigns the customer's next request to a new replica
- The new replica has no in-memory Decision Space — it must reload from database before accepting any execution request
- The Professional Runtime detects missing Decision Space on the first post-failure request and performs a blocking reload (not an execution)
- No execution occurs until reload is confirmed complete; this is a safe pause, not a constitutional violation
- The customer's Emergency Stop connection (via SignalR) is re-established automatically by the SignalR SDK on reconnect
- PAAS sessions are time-bounded (trading hours only)
- After market close, replicas scale to zero
- Cost is proportional to active concurrent sessions, not total customers
