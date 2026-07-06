# WAOOAW — Service Architecture and API Design

**Altitude:** 32K — Container/Service Detail

**Version:** 0.1

**Depends on:** architecture/100k/README.md

---

## Service Communication Overview

```
                    EXTERNAL
┌──────────────────────────────────────────────────┐
│  Customer Browser / Mobile PWA                    │
│  React Native App (Phase 2)                       │
└──────────────────────────────────────────────────┘
                     │ HTTPS REST + WebSocket
                     ↓
┌──────────────────────────────────────────────────┐
│  API Gateway (NGINX)                              │
│  JWT validation | Rate limiting | Routing         │
│  Routes /api/v1/* to internal services            │
└──────────────────────────────────────────────────┘
                     │
          ┌──────────┴────────────────┐
          │                           │
          ↓ REST                      ↓ REST + WS
┌─────────────────┐      ┌───────────────────────┐
│ Business        │      │ Professional Runtime   │
│ Platform        │      │ (PAAS + Approval-Gate) │
│ (.NET)          │      │ (Python)               │
└─────────────────┘      └───────────────────────┘
          │                          │
          │ gRPC (internal)          │ gRPC (internal)
          ↓                          ↓
┌──────────────────────────────────────────────────┐
│  Constitutional Engine (.NET)                     │
│  ← Only service that writes to Audit Ledger       │
│  ← Only service that manages Authority Licenses   │
└──────────────────────────────────────────────────┘
                     │
          ┌──────────┴────────────────┐
          │                           │
          ↓ gRPC                      ↓ Temporal
   PostgreSQL                Professional Runtime
   (Evidence)                 (via workflow triggers)

          ↓ REST (internal, from Professional Runtime)
┌──────────────────────────────────────────────────┐
│  AI Runtime (Python)                              │
│  LLM Gateway — stateless inference               │
└──────────────────────────────────────────────────┘
                     │
          ┌──────────┴────────────────┐
          │                           │
   Azure OpenAI              Ollama / Anthropic
   (US East)                 (fallback / dev)
```

---

## Communication Protocols by Route

| From | To | Protocol | Reason |
|---|---|---|---|
| Browser/Mobile | API Gateway | HTTPS REST | Standard client-server |
| Browser/Mobile | API Gateway | WebSocket (SignalR) | Emergency Stop, real-time updates |
| API Gateway | Business Platform | HTTPS REST | Internal routing |
| API Gateway | Professional Runtime | WebSocket | Emergency Stop passthrough |
| Business Platform | Constitutional Engine | gRPC | Low latency, typed contracts, must be sync |
| Professional Runtime | Constitutional Engine | gRPC | Evidence recording must complete before response |
| Professional Runtime | AI Runtime | HTTPS REST | Stateless inference, easy mock in tests |
| All services | Temporal | Temporal SDK | Workflow triggers, not HTTP |
| Constitutional Engine | PostgreSQL | TCP (native) | Direct, no intermediary |

**Why gRPC for Constitutional Engine calls?**

Evidence recording must complete before the API response returns (Evidence First principle). gRPC provides typed contracts, bidirectional streaming, and sub-10ms round trips on the same network. HTTP/REST adds JSON parsing overhead and makes the Evidence First guarantee harder to enforce in tests.

---

## External API — Customer-Facing (Business Platform)

**Base:** `https://api.waooaw.com/api/v1/`
**Auth:** Bearer JWT (issued by Keycloak/Azure AD B2C)
**Format:** JSON, OpenAPI 3.0 spec

### Employment Module

```
POST   /employment/contracts
         Creates Employment Contract (triggers EmploymentLifecycleWorkflow)
         Body: { professionalId, customerId, decisionSpaceParams, reviewCadence }
         Returns: { contractId, status: "onboarding" }

GET    /employment/contracts/{contractId}
         Get contract state, authority level, evidence summary

PATCH  /employment/contracts/{contractId}/authority
         Request authority expansion (triggers AuthorityEscalationWorkflow)
         Body: { requestedExpansion, justification }

DELETE /employment/contracts/{contractId}
         Terminate contract (triggers TerminationWorkflow)
         Returns: { status: "terminated", dataExportUrl }
```

### Approval Queue Module

```
GET    /approvals/pending
         List pending approvals for authenticated customer
         Returns: [ { approvalId, proposalType, proposalContent, expiresAt } ]

POST   /approvals/{approvalId}/approve
         Approve a proposed action (resumes ApprovalGateWorkflow)

POST   /approvals/{approvalId}/reject
         Reject with optional note (records evidence, resumes workflow)
```

### Evidence Module

```
GET    /evidence/ledger
         Customer's evidence timeline (paginated, date-filtered)
         Returns: [ { timestamp, eventType, summary, professionalId } ]

GET    /evidence/export
         Request portable export of Customer Evidence Ledger
         Returns: { exportJobId } → async, notified via push
```

### Marketplace Module

```
GET    /marketplace/professionals
         Browse available professionals
         Query: ?profession=marketing&specialization=dental&location=india

GET    /marketplace/professionals/{professionalId}
         Professional profile (Experience Ledger summary, public stats)
```

### Emergency Stop (WebSocket)

```
WS     /ws/emergency-stop/{contractId}
         Connect on session start. Send "STOP" message any time.
         Server guarantees halt + confirmation within 250ms.
         Evidence recorded: emergency stop event with timestamp.
```

---

## Internal API — Constitutional Engine (gRPC)

**Service:** `constitutional-engine:5002`
**Protocol:** gRPC, mTLS between services
**Consumers:** Business Platform, Professional Runtime

```protobuf
service ConstitutionalEngine {

  // Validate whether an action is within the licensed Decision Space
  rpc ValidateAction (ValidateActionRequest) returns (ValidateActionResponse);

  // Record evidence to the appropriate ledger (append-only)
  rpc RecordEvidence (RecordEvidenceRequest) returns (RecordEvidenceResponse);

  // Grant or modify an authority license
  rpc GrantAuthorityLicense (GrantAuthorityRequest) returns (AuthorityLicense);

  // Evaluate an action against Constitutional Floors
  rpc EvaluatePolicy (EvaluatePolicyRequest) returns (PolicyEvaluation);

  // Signal Emergency Stop — must complete within 250ms
  rpc EmergencyStop (EmergencyStopRequest) returns (EmergencyStopConfirmation);
}
```

**RecordEvidence is the most critical call:**
- Must complete and return success BEFORE the calling service returns its own response
- This is how Evidence First is architecturally enforced — not by convention but by code structure
- If RecordEvidence fails, the calling service must NOT return success to the customer
- gRPC timeout: 5 seconds. Evidence recording failure is a system error, not a customer error.

---

## Internal API — Professional Runtime

**External (via API Gateway):** HTTPS REST for approval actions, WebSocket for Emergency Stop
**Internal:** gRPC calls to Constitutional Engine

### Approval-Gate Path (REST)

```
POST   /internal/workflows/approval-gate/start
         Called by Business Platform when contract is active
         Body: { contractId, decisionSpaceId }
         Returns: { workflowId }

POST   /internal/proposals/{proposalId}/publish
         Called internally when approval received
         Records evidence via Constitutional Engine first
         Then publishes to external platform (Instagram, etc.)
```

### PAAS Path (no HTTP in execution loop)

The PAAS execution path does NOT use HTTP. The PAAS Engine:
1. Loads Decision Space parameters from Constitutional Engine at session start (one gRPC call)
2. Validates actions in-memory against cached parameters (no network call per trade)
3. Records evidence via gRPC to Constitutional Engine (async after execution)
4. Receives Emergency Stop via WebSocket (passed through from API Gateway)

**This is why PAAS achieves <250ms:** The execution hot path has zero network calls. Only session open and session close hit the network.

---

## Internal API — AI Runtime (REST)

**Service:** `ai-runtime:5004`
**Protocol:** HTTPS REST (not gRPC — easier to mock for testing)
**Consumer:** Professional Runtime (called as Temporal Activity)

```
POST   /inference
         Execute an LLM inference call
         Body: {
           model: "gpt-4o" | "claude-3-5-sonnet" | "llama3",
           messages: [...],
           constitutionalContext: { decisionSpaceId, professionalId, customerId },
           maxTokens: 2000,
           temperature: 0.7
         }
         Returns: { content, model, tokensUsed, providerId, latencyMs }

POST   /prompts/build
         Build a constitutional prompt for a professional
         Body: { professionalType, customerContext, taskDescription, decisionSpaceConstraints }
         Returns: { systemPrompt, userPrompt, contextualNotes }
```

**The `constitutionalContext` field is not optional.** Every inference call carries the constitutional context. This enables:
- Audit trail of which professional made which AI call
- Evidence recording (via Constitutional Engine) of AI-generated content
- Provider routing based on professional type (trading may use faster model)

---

## Scaling Strategy Per Service

### Business Platform
**Scale driver:** API request volume (customer portal usage)
**Strategy:** Horizontal — add Container App replicas
**State:** Stateless — JWT tokens, no session affinity needed
**Database:** Shared PostgreSQL with connection pooling (PgBouncer)
**Scale range:** 1–10 replicas

### Constitutional Engine
**Scale driver:** Evidence write volume + authority check frequency
**Strategy:** Horizontal — but with careful consideration
**State:** Stateless API, stateful PostgreSQL
**Critical:** Evidence writes must be durable. Scale out reads with read replica. Never sacrifice durability for throughput.
**Scale range:** 2–8 replicas (minimum 2 for HA)

### Professional Runtime — Marketing Path
**Scale driver:** Number of active approval-gate workflows
**Strategy:** Horizontal — Temporal workers scale independently
**State:** Workflow state managed by Temporal (not in memory)
**Scale range:** 1–20 workers

### Professional Runtime — PAAS Path (Trading)
**Scale driver:** Number of concurrent trading sessions
**Strategy:** Session-affinity — one dedicated instance per active session preferred
**Reason:** PAAS in-memory Decision Space cache must be consistent per session
**State:** Per-session in-memory Decision Space parameters
**Scale range:** 0–N (one per concurrent active PAAS customer)

### AI Runtime
**Scale driver:** LLM inference call volume (concurrent professional executions)
**Strategy:** Horizontal — stateless, scale aggressively
**State:** Completely stateless — no session data
**Cost consideration:** AI Runtime is the most expensive to run at scale (LLM token costs dominate)
**Scale range:** 1–50 replicas (consumption-based pricing keeps dev cost near zero)

---

## API Versioning Strategy

```
Current: /api/v1/

Breaking change policy:
  - New field in response: NON-breaking, add without version change
  - Removed field: BREAKING, must version
  - Changed field type: BREAKING, must version
  - New required field in request: BREAKING, must version

/api/v1/ → maintained for minimum 12 months after /api/v2/ launch
/api/v2/ → introduced only when breaking changes are required
```

**OpenAPI 3.0 specification for every endpoint** — generated and published at:
`GET /api/v1/openapi.json`

The AI Runtime Professional reads the OpenAPI spec when implementing a new endpoint. The spec IS the contract. The implementation serves the spec, not the other way around.

---

## Service Segregation — Constitutional Enforcement

The Constitutional Engine must never be directly accessible from the same process as Business Platform. This is the Doctrine of Institutional Independence at the network layer.

**Enforcement in Container Apps:**
```
Network policy:
  - Business Platform → Constitutional Engine: ALLOWED (port 5002 gRPC)
  - Professional Runtime → Constitutional Engine: ALLOWED (port 5002 gRPC)
  - Constitutional Engine → PostgreSQL: ALLOWED (port 5432)
  - NO other service → PostgreSQL Constitutional Audit Ledger directly: BLOCKED
  - External traffic → Constitutional Engine: BLOCKED (internal only)
```

No customer API call ever directly touches the Constitutional Engine. It is always mediated through Business Platform or Professional Runtime. This prevents a customer from manipulating evidence through a direct API call.

---

## ADRs Required Before Implementation

The following Architecture Decision Records must be ratified before any service is implemented:

| ADR | Decision Required |
|---|---|
| ADR-001 | gRPC vs REST for Constitutional Engine internal API |
| ADR-002 | OpenAPI spec generation — code-first vs spec-first |
| ADR-003 | JWT structure and claims for multi-tenant isolation |
| ADR-004 | Emergency Stop WebSocket — SignalR vs plain WS |
| ADR-005 | PAAS session isolation strategy (1 instance per session vs shared) |
| ADR-006 | API rate limiting — per customer tier vs global |
| ADR-007 | gRPC mTLS certificate management between services |
