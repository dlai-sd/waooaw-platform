# ADR-001: gRPC for Constitutional Engine Internal API

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Enterprise Architect (structural communication pattern) + Solution Architect (API contract design)
**Constitutional Basis:** Constitution Article II (First Law — trust earned through evidence); GENESIS Engineering Quality Mandate (Constitutional Compliance Tests must verify Evidence First)

---

## Context

The Constitutional Engine is the only service that writes to the Constitutional Audit Ledger. Every action that must be governed — approving content, executing a trade, granting authority — must record evidence **before** the calling service returns a success response to the customer. This is the Evidence First principle.

The internal communication protocol between Business Platform / Professional Runtime and the Constitutional Engine must guarantee:
- Synchronous completion (evidence written before response returned)
- Typed contracts (prevent malformed evidence records)
- Sub-10ms latency on the same Container Apps network
- Ability to enforce Evidence First in automated tests

## Decision

**Use gRPC for all internal service-to-service communication with the Constitutional Engine.**

Protocol Buffers define the service contract. All four operations (ValidateAction, RecordEvidence, GrantAuthorityLicense, EvaluatePolicy, EmergencyStop) are defined in `.proto` files and shared across .NET and Python services.

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| REST/HTTP | JSON serialization adds ~1ms overhead. No native streaming. Evidence First is harder to enforce in tests — no typed contract to assert against. |
| GraphQL | Designed for flexible queries, not for low-latency mutation guarantees. Overhead not justified. |
| Async messaging (Temporal activities) | Evidence recording must be synchronous. Async recording means a trade could succeed before evidence is written — constitutional violation. |

## Consequences

**Benefits:**
- Evidence First is architecturally enforced, not just convention
- Strongly typed `.proto` contracts serve as living documentation
- gRPC interceptors handle mTLS and telemetry uniformly
- Python and .NET both have first-class gRPC support

**Trade-offs:**
- `.proto` files must be versioned and shared between services
- gRPC is harder to test manually than REST (requires grpcurl or Postman gRPC)
- Browser cannot call gRPC natively — confirmed: Constitutional Engine is internal-only, never called from browser
