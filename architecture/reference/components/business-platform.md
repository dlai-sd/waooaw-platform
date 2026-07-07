# Component Specification: Business Platform

**Service:** Business Platform
**Technology:** .NET 9, ASP.NET Core, Entity Framework Core 9, Temporal .NET SDK
**Port:** 5001 (REST external) | internal gRPC client to Constitutional Engine
**Owning Office:** Solution Architect (Sprint 004)
**Constitutional Basis:** AD-002 (Evidence First), AD-004 (Multi-tenant), C-034 (Employment lifecycle)

---

## Responsibility

The external-facing service. Every customer interaction enters through this service. It owns the employment lifecycle, the approval workflow state machine, and the customer evidence reading API. It is NOT a pass-through — it contains business logic for employment management and delegates only constitutional governance to the Constitutional Engine.

## Components

### 1. Employment Manager
Manages the full employment lifecycle per C-034.

**Responsibilities:**
- Create/read/update EmploymentContract and DecisionSpace entities
- State machine: EVALUATION → ACTIVE → SUSPENDED → TERMINATED
- Trigger Temporal workflow on contract formation and state changes
- Call ConstitutionalEngine.RecordEvidence (gRPC) for every state transition

**Key methods:**
```
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

## What Business Platform does NOT do
- Does NOT execute professional work (that is Professional Runtime)
- Does NOT write to the Constitutional Audit Ledger directly (only via Constitutional Engine)
- Does NOT call LLMs (that is AI Runtime via Professional Runtime)
- Does NOT maintain WebSocket connections (Emergency Stop is handled by Professional Runtime)

## Runtime Requirements (for Dockerfile + startup)

**Tenant isolation interceptor:** BP must register `TenantDbCommandInterceptor` with its EF Core DbContext (see engineering-standards.md Section 10). This must execute before any DB query. JWT middleware stores `tenant_id` in `HttpContext.Items["tenant_id"]` — the interceptor reads it from there.

**JWT middleware order:** In ASP.NET Core middleware pipeline:
```
UseRouting() → UseAuthentication() → UseAuthorization() → [extract tenant_id to HttpContext.Items] → UseEndpoints()
```
The tenant_id extraction middleware runs AFTER authentication so the JWT is validated first.
