# Component Specification: Professional Runtime

**Service:** Professional Runtime
**Technology:** Python 3.12, FastAPI, Temporal Python SDK, httpx (async HTTP client)
**Port:** 5003 (REST external for Emergency Stop WSS + internal API from Business Platform)
**Owning Office:** Solution Architect (Sprint 004)
**Constitutional Basis:** C-018 (PAAS model), C-025 (PAAS first-class execution), C-035 (Runtime Universality), AD-001 (Emergency Stop ≤250ms), AD-005 (PAAS hot path <50ms), AD-007 (Runtime Universality)

---

## Responsibility

Two execution engines in one service. The Professional Runtime is the only service that executes professional work. It enforces the Runtime Universality principle — all professional types (marketing, creative, trading) run through the same code with different Decision Space configurations.

## Components

### 1. Approval-Gate Engine
Handles the approval-gate execution model (Acceptance Scenarios 001 and 002).

**Responsibility:**
- Receive work orders from Temporal workflow (via Temporal activity)
- Compose proposed action (calls AI Runtime for content generation if needed)
- Submit proposed action to Business Platform's Approval Workflow Engine (REST)
- Wait for approval signal (via Temporal signal from Business Platform)
- On approval: record evidence via Constitutional Engine (gRPC), then execute the action
- On rejection: record evidence via Constitutional Engine, close the work item
- On scope-boundary detection: route to Business Platform's boundary confirmation endpoint

**Key principle:** Every action execution is preceded by a Constitutional Engine RecordEvidence call. No execution returns success before evidence is confirmed written.

### 2. PAAS Engine (Pre-Authorized Action Space)
Handles the PAAS execution model (Acceptance Scenario 003 — trading).

**PAAS session is a Temporal workflow — `PAASSessionWorkflow`:**
Each active PAAS session runs as a long-lived Temporal workflow. The workflow ID is the session ID, which is the routing key for Emergency Stop signals (ADR-018). All PAAS action executions are Temporal activities within this workflow.

**Responsibility:**
- **Session startup:** Start `PAASSessionWorkflow` in Temporal. Load Decision Space from DB into memory via Constitutional Engine validation.
- **Hot path (in-memory only):** For each action signal (received as Temporal activity input):
  1. Validate against in-memory Decision Space (< 1ms)
  2. Check budget constraints (< 1ms)
  3. Call Constitutional Engine to validate and record evidence (gRPC, ~50-80ms)
  4. Execute action via AI Runtime if validation passes
  5. Return execution result
- **Emergency Stop signal handler:** `PAASSessionWorkflow` registers a Temporal signal handler for `EmergencyStop`. On signal receipt:
  1. Halt the in-flight activity immediately
  2. Record ABANDONED evidence via CE gRPC (for any in-flight action)
  3. Signal confirmation back to CE (CE returns halt confirmation to caller)
  4. Terminate the workflow
- **Session teardown:** Release in-memory Decision Space on normal session end, Emergency Stop, or Decision Space version change.
- **Replica isolation:** One PAAS session workflow per active session. Temporal routes signals to the worker executing the workflow — replica-independent (ADR-018).

**Critical constraint:** Steps 1-2 (validation) must complete in <1ms. The entire hot path including Constitutional Engine call must complete within 50ms budget (AD-005).

### 3. Emergency Stop Handler (WebSocket)
**Responsibility:**
- Maintains a persistent WebSocket connection per active customer session
- Receives Emergency Stop commands (JWT authenticated — Authorization header only, never query params — ADR-004)
- On receipt: immediately signal all active work items (PAAS and approval-gate) to halt
- Call Constitutional Engine TriggerEmergencyStop (gRPC)
- Return halt confirmation only after ConstitutionalEngine confirms evidence recorded
- Total end-to-end latency including evidence recording: ≤250ms (AD-001)

### 4. Temporal Worker
**Responsibility:**
- Execute Temporal workflow activities for employment operations
- Implements activity interfaces for: professional onboarding, periodic performance assessment, contract renewal sequences

### 5. Decision Space Loader
**Responsibility:**
- At PAAS session start: load the customer's Decision Space from DB (via gRPC to Constitutional Engine)
- Cache the Decision Space in-memory for the session duration
- On Emergency Stop: discard the in-memory cache
- On Decision Space version change mid-session: detect and halt the PAAS session (the session was opened on an old Decision Space; a new session must be started with the updated version)

### 6. Conversation Execution Coordinator (WC-034 F3)
**Responsibility:**
- Accept or replay BP-authorized professional execution through an internal-only service contract
- Derive tenant, relationship, and delegated actor context from the signed BP service assertion, never request-body hints
- Start durable Temporal execution responsibility before returning `202`
- Emit ordered versioned text-delta, card-proposal, evidence, terminal, Stop, and reconciliation events to BP
- Accept cancellation while preserving partial output and without releasing Emergency Stop
- Fail closed before model dispatch when Stop is active, Decision Space is stale, CE is unavailable, or schema major version is unsupported

**Internal methods (Business Platform only):**
```
POST   /api/v1/internal/conversations/{conversationId}/executions
GET    /api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream
DELETE /api/v1/internal/conversations/{conversationId}/executions/{executionId}
```

The normative contract is `architecture/reference/components/conversation-core.md`; the wire
contract is `architecture/reference/api-specs/professional-runtime.openapi.yaml` version 1.1.0.
These operations are not browser-accessible. PR events become customer-visible only after BP
validates and persists the canonical conversation projection.

### 7. Generic Agent Runtime Adapter Gateway (WC-080 Founder-Accepted Amendment)

**State:** FOUNDER ACCEPTED - 2026-08-31. Implementation still requires the accepted commit to be
merged and bound in the WC-080 implementation issue.

Professional Runtime is the sole platform caller of admitted Agent Runtime Adapters. The gateway:

1. resolves the ACTIVE admission snapshot and immutable artifact without professional-type branching;
2. verifies descriptor identity, protocol range, schema digests, professional and Skill versions,
  execution model, artifact digest, and capabilities before configuration or execution;
3. constructs every adapter envelope from authenticated platform state and never trusts request-body
  tenant, relationship, authority, or lifecycle hints;
4. creates the PR invocation, idempotency identity, projection, outbox, and Temporal workflow before
  adapter dispatch; only the BP-to-PR operation may return `202` for durable responsibility;
5. validates adapter state versions, transitions, results, events, digests, and replay responses;
6. reconciles ambiguous outcomes by immutable invocation identity before any retry or new dispatch;
7. persists and projects accepted adapter facts through the Data Architecture-approved Business
  Platform persistence boundary required by ADR-011;
8. maps private adapter errors into the existing BP-facing vocabulary without exposing adapter
  topology, tenant existence, provider detail, or policy internals;
9. propagates Emergency Stop independently of adapter health, keeps an explicit Emergency Stop
  barrier latched, and reconciles adapter acknowledgement later; and
10. permits resume only from fresh post-Stop authority and never restarts a stopped invocation.

The gateway contains no professional-type switch, domain payload interpretation, admission mutation,
customer projection, constitutional evidence acceptance, provider policy, or automatic recovery
from an explicit Emergency Stop. A CE-unavailability pause resumes automatically only after CE
connectivity and constitutional reconciliation complete. Domain variation is selected only through admitted schema coordinates and descriptor
capabilities. Adapter operations remain absent from the public Professional Runtime OpenAPI.

## Runtime Universality Implementation

The Professional Runtime contains **no professional-type-specific code**. The `executionModel` field of the Decision Space determines which engine handles the session:

```python
if decision_space.execution_model == ExecutionModel.APPROVAL_GATE:
    return await approval_gate_engine.handle(work_item, decision_space)
elif decision_space.execution_model == ExecutionModel.PRE_AUTHORIZED:
    return await paas_engine.handle(action_signal, decision_space)
```

All professional-type logic (what actions are valid, what content to generate, what tools to use) is expressed in the Decision Space configuration. The runtime applies that configuration — it never branches on professional type.

## Dependencies
- **Constitutional Engine** (gRPC, synchronous — every execution and governance event)
- **AI Runtime** (REST internal — for content generation and tool execution)
- **Business Platform** (REST — submits proposed actions; receives approval notifications)
- **PostgreSQL** (reads Decision Space and session state at startup)
- **Temporal** (Temporal worker — receives work assignments)
- **Azure SignalR** (cloud) / plain WebSocket (dev) — Emergency Stop transport
