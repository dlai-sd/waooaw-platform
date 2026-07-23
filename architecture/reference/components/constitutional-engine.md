# Component Specification: Constitutional Engine

**Service:** Constitutional Engine
**Technology:** .NET 9, ASP.NET Core, gRPC (Grpc.AspNetCore), Entity Framework Core 9
**Port:** 5002 (gRPC, internal only — never exposed externally)
**Owning Office:** Solution Architect (Sprint 004)
**Constitutional Basis:** C-023 (Evidence First), C-027 (append-only ledger), C-029 (scope-boundary record), AD-002 (Evidence First enforcement), AD-003 (Audit Ledger immutability)

---

## Responsibility

The constitutional backbone. The only service that writes to the Constitutional Audit Ledger. All governance events — approvals, rejections, authority changes, Emergency Stops — flow through this service before the calling service may return success. This is the architectural implementation of Evidence First.

**Constitutional Engine is never called by the customer directly. It is never exposed to the internet.**

## Proto Contract

All communication is via Protocol Buffers. Proto files live in `architecture/reference/proto/constitutional_service.proto`.

```protobuf
service ConstitutionalService {
  rpc RecordEvidence(RecordEvidenceRequest) returns (RecordEvidenceResponse);
  rpc ValidateAction(ValidateActionRequest) returns (ValidateActionResponse);
  rpc GrantAuthorityLicense(GrantAuthorityRequest) returns (GrantAuthorityResponse);
  rpc RevokeAuthorityLicense(RevokeAuthorityRequest) returns (RevokeAuthorityResponse);
  rpc EvaluatePolicy(EvaluatePolicyRequest) returns (EvaluatePolicyResponse);
  rpc TriggerEmergencyStop(EmergencyStopRequest) returns (EmergencyStopResponse);
}
```

## Components

### 1. Evidence First Enforcer (core component)
**Responsibility:** Receives RecordEvidence requests and writes to the Constitutional Audit Ledger atomically before returning. If the write fails, returns gRPC error — the calling service must treat this as a failure and not return success to the customer.

**Invariants:**
- Write is within a database transaction
- If transaction fails → gRPC error code INTERNAL → caller does not return success
- Record is append-only — no UPDATE or DELETE ever issued on this table
- Every record carries `tenant_id` from gRPC metadata (propagated from caller's JWT)

### 2. PAAS Boundary Validator
**Responsibility:** Validates whether a proposed PAAS action falls within the current Decision Space. Called by Professional Runtime on every PAAS action before execution.

**Logic:**
- Load Decision Space (from cache warmed at session start, or from DB on miss)
- Check action type against `authorizedActions`, `prohibitedActions`, `alwaysAskActions`
- Check budget constraints (spend limits, position limits for trading)
- Return ALLOW / DENY / ESCALATE
- On DENY: emit `constitutional.authority.violated` OTel span

### 3. Authority License Manager
**Responsibility:** Records authority expansion and restriction events. Validates that expansions are justified by evidence (evidence IDs must be provided and must belong to the same contract).

### 4. Emergency Stop Handler
**Responsibility:** Receives TriggerEmergencyStop requests. Records the stop event in the Constitutional Audit Ledger before returning confirmation. Also signals the affected Professional Runtime to halt (via a Temporal signal or a shared coordination mechanism).

**Latency constraint:** This path is on the critical latency budget. The DB write must complete within 80ms (per the PAAS latency budget table in AD-005).

### 5. Policy Evaluator
**Responsibility:** General-purpose policy evaluation for permission decisions. Returns a policy decision with a constitutional justification string that is stored in every audit record (AD-008 — every permission decision must name its constitutional basis).

## Dependencies
- **PostgreSQL** (constitutional schema, append-only operations only)
- **Temporal** (client only — used by Emergency Stop Handler to send `PAASSessionWorkflow.EmergencyStop` signals; CE does not author or orchestrate workflows — ADR-018)

## Runtime Requirements (for Dockerfile)

**gRPC Health Checking Protocol:** The CE exposes a gRPC health service (grpc.health.v1.Health) on port 5002 alongside the ConstitutionalService. This is required for:
- `docker-compose.yml` healthcheck (dev: TCP port check via `nc`; CI/production: `grpc_health_probe`)
- Azure Container Apps health probes in cloud deployment

Implementation: Register `services.AddGrpc().AddHealthChecks()` in ASP.NET Core startup. The `grpc_health_probe` binary must be installed in the production Dockerfile — see `architecture/reference/dockerfiles/Dockerfile.dotnet-service`.

**Tenant isolation interceptor:** The CE must register `TenantDbCommandInterceptor` with its DbContext (see engineering-standards.md Section 10). This intercepts every DB command and executes `SET LOCAL app.tenant_id` before the query runs. RLS depends on this.

## 6. Unavailability Behavior (C-079, ADR-031)

**Constitutional basis:** C-079 mandates that when CE is unavailable, all CE-dependent operations enter Fail-Safe Halt. This section defines what CE itself does to support detection and recovery.

**Health endpoint (mandatory):** CE exposes `grpc.health.v1.Health` on port 5002 (alongside ConstitutionalService). This is the detection mechanism for callers.

```
Health states:
  SERVING     → CE is operational; callers may proceed
  NOT_SERVING → CE is starting up or shutting down; callers must halt
  UNKNOWN     → CE cannot assess its own health; callers must treat as NOT_SERVING
```

**CE startup gate:** CE must reach SERVING state before reporting healthy to the health probe. Specifically, CE must confirm:
1. PostgreSQL connection pool is healthy (constitutional schema accessible)
2. A test RecordEvidence write succeeds (verifies DB write path, not just connection)
3. gRPC server is accepting requests

Only after all three pass does CE set its health state to SERVING.

**Graceful shutdown:** On SIGTERM (Kubernetes/Container Apps pod termination), CE:
1. Sets health state to NOT_SERVING (callers detect and halt immediately)
2. Waits for in-flight gRPC calls to complete (drain timeout: 10 seconds)
3. Flushes any pending DB writes
4. Shuts down cleanly

This ensures that a rolling restart does not create a window where CE is unreachable without callers knowing.

**constitutional.engine_availability_events table:** CE writes one record per availability event (see ADR-031). These records are written by callers (BP, PR), not by CE itself — because CE may be unavailable when the record is needed. BP and PR write to this table directly.

**Full unavailability specification:** see `adr/ADR-031-ce-fail-safe-unavailability.md`

---

## What Constitutional Engine does NOT do
- Does NOT expose REST endpoints
- Does NOT call other services
- Does NOT make business logic decisions — it records and validates, it does not govern
- Does NOT store customer business data (evidence records contain constitutional events, not business content)
- Does NOT continue serving requests in a degraded mode — it is either SERVING or NOT_SERVING (C-079)
