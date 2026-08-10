# Component Specification: Business Platform

**Service:** Business Platform
**Technology:** .NET 9, ASP.NET Core, Entity Framework Core 9, Temporal .NET SDK
**Port:** 5001 (REST external) | internal gRPC client to Constitutional Engine
**Owning Office:** Solution Architect (Sprint 004)
**Constitutional Basis:** AD-002 (Evidence First), AD-004 (Multi-tenant), C-034 (Employment lifecycle), C-036 (Skills as constitutional units), C-037 (Business KPI primacy), C-038 (Pro-rata billing), C-039 (Conversational configuration)

---

## Responsibility

The external-facing service. Every customer interaction enters through this service. It owns the employment lifecycle, the approval workflow state machine, and the customer evidence reading API. It is NOT a pass-through — it contains business logic for employment management and delegates only constitutional governance to the Constitutional Engine.

## Components

### 1. Employment Relationship Manager
Owns the durable AE-01 employment relationship lifecycle and the compatibility boundary for legacy employment contracts.

**Responsibilities:**
- Mint one relationship per tenant, initiating participant, professional type, and evaluation intent
- Persist same-tenant participant-role bindings and append-only, evidence-linked state history
- Enforce the D-03 relationship state graph and explicit EMPLOYER authority for Emergency Stop release
- Resolve tenant and initiating participant from authenticated identity, never request-body tenant hints
- Create/read/update EmploymentContract and DecisionSpace entities
- Preserve legacy contract lifecycle behavior through compatibility adapters
- Trigger Temporal workflow on contract formation and state changes
- Call ConstitutionalEngine.ValidateAction and RecordEvidence (gRPC) before every relationship mutation

**Key methods:**
```
POST /api/v1/employment/relationships       → AdmitEmploymentRelationship
GET  /api/v1/employment/relationships/{id}  → GetEmploymentRelationship
GET  /api/v1/employment/relationships/{id}/timeline
POST /api/v1/employment/relationships/{id}/transitions  → Internal service policy only
POST /api/v1/employment/contracts           → FormEmploymentContract
GET  /api/v1/employment/contracts/{id}      → GetEmploymentContract
PUT  /api/v1/employment/contracts/{id}/activate
PUT  /api/v1/employment/contracts/{id}/suspend
DELETE /api/v1/employment/contracts/{id}   → Terminate
POST /api/v1/employment/contracts/{id}/renew
```

### 2. Approval Workflow Engine
Manages the state machine for Approval-Gate work items.

**Responsibilities:**
- Create ApprovalRequests when Professional Runtime proposes an action
- Present pending approvals to customers via REST API
- Record customer approve/reject decisions
- Detect and route scope-boundary crossing requests to separate confirmation flow
- Call ConstitutionalEngine.RecordEvidence for every approval/rejection

**Key methods:**
```
GET  /api/v1/approvals                     → List pending approvals
GET  /api/v1/approvals/{id}               → Get approval detail
POST /api/v1/approvals/{id}/approve
POST /api/v1/approvals/{id}/reject
POST /api/v1/approvals/{id}/confirm-boundary  → Scope-boundary confirmation
```

### 3. Evidence Reader (read-only)
Provides read access to the Customer Evidence Ledger.

**Responsibilities:**
- Proxy read requests to Constitutional Engine (read-only gRPC call)
- Customer can only read their own tenant's evidence (RLS enforces this at DB layer)
- Export endpoint for data portability (Article IX right)

**Key methods:**
```
GET  /api/v1/evidence                      → List evidence records (paginated)
GET  /api/v1/evidence/{id}                → Get single record
GET  /api/v1/evidence/export              → Full ledger export (zip)
```

### 4. Authority Manager
Manages authority level expansion/restriction decisions.

**Responsibilities:**
- Present authority expansion/restriction decisions to customers
- Call ConstitutionalEngine.GrantAuthorityLicense or RevokeAuthorityLicense on decision
- Record decision in Constitutional Audit Ledger (via Constitutional Engine)

**Key methods:**
```
GET  /api/v1/authority/current            → Current authority level
POST /api/v1/authority/expand
POST /api/v1/authority/restrict
```

### 5. Temporal Workflow Orchestrator
Durable workflow management for multi-step employment operations.

**Responsibilities:**
- Start Temporal workflows on contract formation (onboarding sequence)
- Start Temporal workflows on contract renewal (re-consent sequence)
- Signal workflows on suspension/termination
- All long-running multi-step operations are modelled as Temporal workflows — not as synchronous HTTP chains

### 6. JWT Middleware
**Responsibilities:**
- Validate Keycloak-issued JWT on every request
- Extract `tenant_id` claim and propagate to DB session via `SET LOCAL app.tenant_id`
- Propagate JWT as gRPC metadata to Constitutional Engine calls
- Reject requests with invalid, expired, or missing JWTs before reaching any controller

## Dependencies
- **Constitutional Engine** (gRPC, synchronous, all governance events)
- **PostgreSQL** (business schema, RLS enforced)
- **Temporal** (workflow client)
- **Keycloak** (JWT public key endpoint for validation)

## AE-01 Relationship Foundation (WC-057)

The relationship foundation is implemented by `EmploymentRelationshipDbContext`,
`EmploymentRelationshipService`, and `EmploymentRelationshipsController`. PostgreSQL
migration 19 owns relationship identity, participant-role bindings, append-only state
history, and idempotency records. Every table forces tenant RLS using
`app.current_tenant_id`; constitutional cross-tenant audit remains outside BP roles.

The canonical wire contract is `architecture/reference/api-specs/business-platform.openapi.yaml`.
The customer PWA consumes relationship and timeline reads through an authenticated
server boundary. Contract/payment activation, evaluation workflow, and relationship-wide
Emergency Stop session resolution remain later AE-01 work and are not fabricated here.

## WC-034 F3 Conversation Projection Coordinator

Owns the one durable conversation projection for each authorized Employment Relationship.

**Responsibilities:**
- Authorize every conversation read and command from the validated Keycloak tenant, participant, and relationship binding
- Persist canonical message identity, ordering, unread position, delivery/processing/evidence state, idempotency outcome, and reconciliation cursor
- Accept text contributions and retries without interpreting timeout as success or creating duplicate messages
- Invoke the Professional Runtime internal execution contract only after durable BP acceptance
- Validate and project typed PR execution events through the canonical BP Server-Sent Event boundary
- Preserve Emergency Stop as an independent constitutional transport and state
- Normalize absent, inaccessible, and cross-tenant resources without existence disclosure

**Canonical methods:**
```
GET    /api/v1/employment/relationships/{relationshipId}/conversation/messages
POST   /api/v1/employment/relationships/{relationshipId}/conversation/messages
POST   /api/v1/employment/relationships/{relationshipId}/conversation/messages/{messageId}/retry
PUT    /api/v1/employment/relationships/{relationshipId}/conversation/read-position
GET    /api/v1/employment/relationships/{relationshipId}/conversation/stream
DELETE /api/v1/employment/relationships/{relationshipId}/conversation/executions/{executionId}
```

The normative behavior, versioned data shapes, errors, idempotency, privacy, tenant isolation,
offline reconciliation, acceptance mapping, and dependency gates are defined in
`architecture/reference/components/conversation-core.md`. The public wire contract is
`architecture/reference/api-specs/business-platform.openapi.yaml` version 1.2.0.

## What Business Platform does NOT do
- Does NOT execute professional work (that is Professional Runtime)
- Does NOT write to the Constitutional Audit Ledger directly (only via Constitutional Engine)
- Does NOT call LLMs (that is AI Runtime via Professional Runtime)
- Does NOT maintain WebSocket connections (Emergency Stop is handled by Professional Runtime)

## New Components (v0.8.0 — C-036/037/038)

### 6. Skill Manager
**Responsibility:**
- Manages the lifecycle of individual Skills within an Employment Contract (ACTIVE → PAUSED → TERMINATED per C-036)
- Creates and updates `professional_skills` records
- Routes Skill-level lifecycle events to Constitutional Engine for evidence recording
- Enforces that Skill pause/resume does not affect other Skills in the same contract

**Key methods:**
```
GET  /api/v1/employment/contracts/{id}/skills         → List skills in contract
POST /api/v1/employment/contracts/{id}/skills         → Add skill to contract
PUT  /api/v1/employment/contracts/{id}/skills/{skillId}/pause
PUT  /api/v1/employment/contracts/{id}/skills/{skillId}/resume
PUT  /api/v1/employment/contracts/{id}/skills/{skillId}/goals  → Update KPI targets
```

### 7. Performance Monitor
**Responsibility:**
- Tracks each Skill's performance against its stated business KPIs (C-037, AD-012)
- Receives performance data from Professional Runtime (via REST) after each skill execution cycle
- Presents business KPI dashboards — appointment growth, enquiry rate, trading return — NOT technical metrics
- Triggers alerts when Skill KPIs trend below target for more than 2 consecutive periods

### 8. Subscription Manager
**Responsibility:**
- Records billing events (SubscriptionBillingEvent) at every lifecycle change with minute-level precision (AD-014, C-038)
- Calculates pro-rata charges at billing period end from the event ledger
- Manages trial enrollment, trial conversion, and trial auto-termination
- Generates customer-facing billing summaries (AD-014 — itemised per Skill)

**Billing event triggers:** contract ACTIVATED/TERMINATED/SUSPENDED, skill ACTIVE/PAUSED/RESUMED, trial STARTED/CONVERTED/EXPIRED

## Runtime Requirements (for Dockerfile + startup)

**Tenant isolation interceptor:** BP must register `TenantDbCommandInterceptor` with its EF Core DbContext (see engineering-standards.md Section 10). This must execute before any DB query. JWT middleware stores `tenant_id` in `HttpContext.Items["tenant_id"]` — the interceptor reads it from there.

**JWT middleware order:** In ASP.NET Core middleware pipeline:
```
UseRouting() → UseAuthentication() → UseAuthorization() → [extract tenant_id to HttpContext.Items] → UseEndpoints()
```
The tenant_id extraction middleware runs AFTER authentication so the JWT is validated first.
