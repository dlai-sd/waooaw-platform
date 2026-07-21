# INSTITUTIONAL_BACKLOG.md

**Authority:** Founder (as COO, Era 0)

**Purpose:** The governed queue of work the institution must complete to advance through gates and build WAOOAW. Work does not originate from offices. It originates here. Offices pull from this backlog.

**This is not a project plan. It is a constitutional queue.**

---

## How This Backlog Works

```
Founder prioritizes backlog
        ↓
Active office reads highest-priority item assigned to it
        ↓
Office creates or updates Work Contract to satisfy backlog item
        ↓
Office executes Work Contract
        ↓
Evidence produced
        ↓
Reviewer approves
        ↓
Backlog item marked DONE
        ↓
Next office pulls next item
```

A backlog item is BLOCKED when a Constitutional Blocker exists for it.
A backlog item is IN_PROGRESS when an office's Work Contract references it.
A backlog item is DONE only when its Success Criteria are met and reviewed.

---

## Backlog Item Format

```
IB-XXX
Goal:             What the institution needs
Office:           Which office is responsible
Priority:         P0 (Gate-blocking) | P1 (High value) | P2 (Needed soon)
Gate:             Which gate this satisfies or enables
Depends On:       [IB-XXX list] or NONE
Success Criteria: Measurable. Falsifiable. Reviewer-verifiable.
Inputs:           What the office needs to begin
Outputs:          What the office must produce
Status:           WAITING | IN_PROGRESS | DONE | BLOCKED
```

---

## Active Backlog

---

### IB-001 — Produce Constitutional Knowledge Corpus

**Goal:** Enable the Enterprise Architect to derive the complete reference architecture without requiring Founder clarification.

**Office:** Constitutional Analyst

**Priority:** P0 — Gate G2 blocking

**Gate:** G2

**Depends On:** NONE

**Success Criteria:**
- At least 20 typed, atomic, traceable claims exist in `knowledge/claims/`
- Confidence Register is complete
- Claim Index is complete
- Enterprise Architect declares: "I can derive architecture from this without asking the Founder."

**Inputs:**
- CONSTITUTION.md
- GENESIS.md
- simulation/PRECEDENTS.md
- simulation/001-dr-mehta-dental-clinic.md
- simulation/002-sana-beauty-artist-mumbai.md
- simulation/003-high-frequency-constitutional-employment.md
- RED_TEAM.md

**Outputs:**
- `knowledge/claims/C-XXX.md` (individual claim files)
- `knowledge/confidence-register.md`
- `knowledge/index.md`

**Status:** DONE — Gate G2 passed 2026-07-07

---

### IB-002 — Produce Business Capability Map

**Goal:** Define the complete set of business capabilities WAOOAW must support, traceable to constitutional claims and acceptance scenarios.

**Office:** Chief Business Architect

**Priority:** P0 — Gate G3 blocking

**Gate:** G3

**Depends On:** IB-001

**Success Criteria:**
- Every business capability cites the constitutional claim or acceptance scenario that demands it
- Enterprise Architect declares: "I can design the system boundary from this."
- No capability exists without constitutional basis

**Inputs:**
- Approved knowledge corpus from IB-001
- GENESIS Part 01 (Acceptance Scenarios)
- CONSTITUTION.md (Constitutional Purpose)

**Outputs:**
- `knowledge/business-capabilities.md`

**Status:** DONE — 2026-07-07

---

### IB-003 — Define Architectural Drivers

**Goal:** Define the non-negotiable constraints that determine architecture — availability, latency, auditability, multi-tenancy, AI governance, cost, security, scalability, compliance, disaster recovery.

**Office:** Chief Business Architect

**Priority:** P0 — Gate G3 blocking

**Gate:** G3

**Depends On:** IB-001

**Success Criteria:**
- Every Architectural Driver states which capabilities it constrains and how
- Enterprise Architect declares: "These constraints define my design space."
- No driver is invented — each traces to a constitutional claim or business need

**Inputs:**
- Approved knowledge corpus from IB-001
- Business Capability Map from IB-002

**Outputs:**
- `knowledge/architectural-drivers.md`

**Status:** DONE — 2026-07-07

---

### IB-004 — Define Design Principles

**Goal:** Define engineering principles derived from constitutional claims that govern all architecture and implementation decisions.

**Office:** Chief Business Architect

**Priority:** P0 — Gate G3 blocking

**Gate:** G3

**Depends On:** IB-001

**Success Criteria:**
- Every principle traces to a constitutional claim
- Principles include at minimum: Evidence First, API First, Configuration over Code, Event First, Tenant Isolation, Observability by Default, Security by Design
- Enterprise Architect declares: "These principles govern every design choice I make."

**Inputs:**
- Approved knowledge corpus from IB-001

**Outputs:**
- `knowledge/design-principles.md`

**Status:** DONE — 2026-07-07

---

### IB-005 — Produce Reference Architecture

**Goal:** Derive the technology-agnostic reference architecture from business capabilities, architectural drivers, and design principles.

**Office:** Chief Enterprise Architect

**Priority:** P0 — Gate G4 blocking

**Gate:** G4

**Depends On:** IB-002, IB-003, IB-004

**Success Criteria:**
- C4 model complete (Context, Container, Component levels)
- Domain model complete
- Every architectural component traces to a business capability
- Solution Architect declares: "I can decompose this into implementable components."
- No technology selected yet

**Inputs:**
- Business Capability Map (IB-002)
- Architectural Drivers (IB-003)
- Design Principles (IB-004)
- Constitutional knowledge corpus (IB-001)

**Outputs:**
- `architecture/reference/context.md`
- `architecture/reference/containers.md`
- `architecture/reference/components.md`
- `architecture/reference/domain-model.md`
- `adr/` (Architecture Decision Records, technology-agnostic at this stage)

**Status:** DONE — 2026-07-07 (R-004 CA review APPROVED, R-005 BA review APPROVED. Gate G3 confirmed passed.)

---

### IB-006 — Produce Component Specifications

**Goal:** Decompose the Reference Architecture into implementable component specifications with precise interfaces, responsibilities, and integration patterns.

**Office:** Solution Architect

**Priority:** P0 — Gate G4 blocking

**Gate:** G4

**Depends On:** IB-005

**Success Criteria:**
- Component specification exists for each of the 4 services
- Every component traces to a business capability
- Every interface is specified (gRPC contracts, REST endpoints, event contracts)
- Runtime Professional declares: “I can implement this without inventing logic.”

**Inputs:**
- Reference Architecture (IB-005)
- Business Capability Map (IB-002)
- ADRs (adr/)

**Outputs:**
- `architecture/reference/components/business-platform.md`
- `architecture/reference/components/constitutional-engine.md`
- `architecture/reference/components/professional-runtime.md`
- `architecture/reference/components/ai-runtime.md`

**Status:** DONE — 2026-07-07 (Produced concurrently with IB-005 in Sprint 003 session. R-004 covers constitutional traceability. R-005 confirms capability coverage. Process deviation noted in operational-discoveries.md: IB-006 was produced by EA session without a separate WC-004. Outputs accepted; proto file gap (CA-R004-01) to be resolved before Gate G5.)

---

### IB-007 — Produce Data Architecture

**Goal:** Design the data architecture that faithfully implements the Three-Ledger Model, evidence state machine, and employment lifecycle.

**Office:** Data Architect

**Priority:** P0 — Gate G4 blocking

**Gate:** G4

**Depends On:** IB-005, IB-006

**Success Criteria:**
- Three-ledger separation is specified at the schema level
- Evidence state machine is fully specified
- Employment lifecycle states are mapped to schema
- Constitutional Audit Ledger immutability is enforced at DB level
- Runtime Professional declares: “I can write migrations from this.”

**Inputs:**
- Reference Architecture (IB-005)
- Component Specifications (IB-006)
- Claims C-005, C-007, C-027, C-028, C-034

**Outputs:**
- `architecture/reference/data/ledger-design.md`
- `architecture/reference/data/evidence-schema.md`

**Status:** DONE — 2026-07-07 (WC-005, Sprint 005. Both outputs produced: ledger-design.md and evidence-schema.md. Evidence state machine fully specified including ABANDONED state, action_instance_id linkage, PAAS variant, Emergency Stop handling, and scope-boundary confirmation path. Pending R-006 review before Gate G4 formally closes.)

---

### IB-008 — Produce Infrastructure Architecture and Local Environment

**Goal:** Produce the local development infrastructure (Docker Compose) and infrastructure architecture specification so the Runtime Professional can start all services locally.

**Office:** Platform Architect

**Priority:** P0 — Gate G5 trigger

**Gate:** G4/G5

**Depends On:** IB-007

**Success Criteria:**
- `docker-compose.yml` runs `docker compose up` and all services start
- `.env.example` documents all required environment variables
- Runtime Professional can start the full local stack in one command

**Inputs:**
- Component Specifications (IB-006)
- Data Architecture (IB-007)
- All relevant ADRs (ADR-011 through ADR-015)

**Outputs:**
- `docker-compose.yml`
- `.env.example`

**Status:** DONE — 2026-07-07 (WC-006, Sprint 006. R-006 EA review APPROVED. docker-compose.yml and .env.example validated against component specs and all relevant ADRs. Three IB-009 implementation notes raised: Temporal DB user, web healthcheck, AI Runtime pgvector access.)

---

### IB-009 — Foundation Implementation (Gate G5)

**Goal:** Implement the skeleton of all 4 services, proving the architecture is implementable. Not feature-complete — skeleton only. Every service starts, connects, and passes at least one Constitutional Compliance Test.

**Office:** Runtime Implementation Professional

**Priority:** P0 — Gate G5 (first working code)

**Gate:** G5

**Depends On:** IB-008

**Success Criteria:**
- `docker compose up` starts all 4 services and the full infrastructure stack
- Each service has a `/health` endpoint returning 200
- Business Platform can call Constitutional Engine via gRPC
- First Constitutional Compliance Test passes: Evidence First enforcement verified
- Runtime Universality Test skeleton: all 3 professional scenarios configure without code changes

**Inputs:**
- Component Specifications (IB-006)
- Data Architecture (IB-007)
- Docker Compose (IB-008)
- All approved ADRs

**Outputs:**
- `src/` directory with all 4 service skeletons
- `tests/constitutional/` with first CCT
- All services passing `docker compose up`

**Status:** AUTHORIZED — All R-007 P0 gaps closed. IB-010 DONE (R-009), IB-012 DONE (R-010), IB-013 DONE (R-008). Gate G5 clear.

---

### IB-010 — Security Architecture

**Goal:** Produce a security architecture that guarantees Constitutional Floors cannot be violated by security threats, and that the platform meets world-class security standards.

**Office:** Security Architect (Office 07)

**Priority:** P0 — Gate G5 blocking

**Gate:** G5

**Depends On:** IB-005, IB-006, IB-007

**Success Criteria:**
- Threat model covers all STRIDE categories against all platform assets
- Network topology specifies which containers are public vs internal
- JWT validation specification (algorithm, key rotation, claim extraction)
- Azure Key Vault secret injection pattern for Container Apps specified
- OWASP Top 10 addressed for each service
- Security ADRs produced for any decisions not already covered

**Inputs:** Reference Architecture, Component Specifications, Data Architecture, Constitution Articles IX/X, Architectural Drivers (security), all existing ADRs

**Outputs:**
- `architecture/reference/security/security-architecture.md`
- `architecture/reference/security/threat-model.md`

**Status:** IN_PROGRESS — Sprint 008

---

### IB-011 — Engineering Quality Standards

**Goal:** Mandate coding standards, tooling, testing frameworks, and deployment quality gates so the Runtime Professional builds at world-class standards from day one.

**Office:** Enterprise Architect (governance) + Platform Architect (CI/CD)

**Priority:** P0 — Gate G5 blocking

**Gate:** G5

**Depends On:** IB-005, IB-006

**Success Criteria:**
- Coding standards defined per language (.NET, Python, TypeScript)
- Automated code review tooling mandated (SAST, dependency scan, coverage)
- Testing pyramid with coverage targets defined
- Deployment pipeline quality gates defined
- Constitutional Compliance Test category formally specified

**Inputs:** GENESIS Engineering Quality Mandate, Component Specifications, existing ADRs

**Outputs:**
- Addition to GENESIS Engineering Quality Mandate (amendment)
- `architecture/reference/engineering-standards.md`

**Status:** WAITING (IB-010 first)

---

### IB-012 — OpenAPI Specifications

**Goal:** Produce OpenAPI 3.1 specifications for all REST-facing services, fulfilling ADR-002 (spec-first) before implementation begins.

**Office:** Solution Architect (Office 05)

**Priority:** P0 — Gate G5 blocking

**Gate:** G5

**Depends On:** IB-006

**Success Criteria:**
- `architecture/reference/api-specs/business-platform.openapi.yaml` — all endpoints from component spec
- `architecture/reference/api-specs/professional-runtime.openapi.yaml` — WebSocket and internal REST
- All schemas defined (EmploymentContract, DecisionSpace, ApprovalRequest, EvidenceRecord)
- All security schemes defined (JWT Bearer)
- Spectral linting passes on both specs

**Inputs:** Component Specifications (IB-006), Data Architecture (IB-007), ADR-002, ADR-003

**Outputs:**
- `architecture/reference/api-specs/business-platform.openapi.yaml`
- `architecture/reference/api-specs/professional-runtime.openapi.yaml`

**Status:** IN_PROGRESS — Sprint 009

---

### IB-013 — Technology Stack ADRs

**Goal:** Produce missing ADRs for all technology selections made in the architecture phase (language, framework), satisfying the EA Quality Gate obligation.

**Office:** Enterprise Architect (Office 04)

**Priority:** P0 — Gate G5 blocking

**Gate:** G5

**Depends On:** IB-005, IB-006

**Success Criteria:**
- ADR-016: service language selection (.NET 9 / Python 3.12) — alternatives rejected
- ADR-017: web application framework (Next.js / TypeScript) — alternatives rejected
- ADR-018: Emergency Stop Temporal signal routing — design specified, alternatives rejected

**Inputs:** Component Specifications, existing ADRs, architectural drivers

**Outputs:**
- `adr/ADR-016-service-language-selection.md`
- `adr/ADR-017-web-application-framework.md`
- `adr/ADR-018-emergency-stop-temporal-signal.md`

**Status:** IN_PROGRESS — Sprint 007

---

## Backlog Index

| ID | Goal | Office | Priority | Gate | Status |
|---|---|---|---|---|---|
| IB-001 | Produce Constitutional Knowledge Corpus | Constitutional Analyst | P0 | G2 | DONE |
| IB-002 | Produce Business Capability Map | Business Architect | P0 | G3 | DONE |
| IB-003 | Define Architectural Drivers | Business Architect | P0 | G3 | DONE |
| IB-004 | Define Design Principles | Business Architect | P0 | G3 | DONE |
| IB-005 | Produce Reference Architecture | Enterprise Architect | P0 | G4 | DONE |
| IB-006 | Produce Component Specifications | Solution Architect | P0 | G4 | DONE |
| IB-007 | Produce Data Architecture | Data Architect | P0 | G4 | DONE |
| IB-008 | Infrastructure Architecture + Docker Compose | Platform Architect | P0 | G4/G5 | DONE |
| IB-009 | Foundation Implementation (skeleton) | Runtime Professional | P0 | G5 | AUTHORIZED |
| IB-010 | Security Architecture | Security Architect | P0 | G5 | DONE |
| IB-011 | Engineering Quality Standards | EA + Platform Architect | P0 | G5 | DONE |
| IB-012 | OpenAPI Specifications | Solution Architect | P0 | G5 | DONE |
| IB-013 | Technology Stack ADRs (016/017/018) | Enterprise Architect | P0 | G5 | DONE |
| IB-014 | Customer Self-Service Portal (Domain 7) | Business Architect + SA | P1 | G5-parallel | WAITING |
| IB-015 | Constitutional CS Agents (Domain 8) — FR-001 Path A | Business Architect + Runtime Professional | P1 | G5-parallel | WAITING |
| IB-016 | Platform Operations Architecture | Platform Architect | P1 | G5-parallel | WAITING |
| IB-017 | Phase 2 Readiness Sprint | Platform Architect + EA | P0 | G5-prerequisite | DONE |
| IB-018 | Agent Teams — Constitutional Team Architecture | Enterprise Arch + BA + CA | P1 | Post-MVI (Enterprise) | DEFERRED |
| **IB-019** | **DMA Multi-Mode: Chain, Franchise, Agency — Full Architecture** | **Business Architect + DMA Agent** | **P2** | **Post FR-005 (50+ customers)** | **WAITING** |

---

## IB-014 — Customer Self-Service Portal (Domain 7)

**Goal:** Define Domain 7 business capabilities and the portal's integration contract with the Business Platform API. Extend the OpenAPI spec with two missing endpoints identified in the critical review.

**Office:** Business Architect (capabilities) + Solution Architect (API addenda)
**Priority:** P1 — G5-parallel (does not block IB-009)
**Gate:** G5-parallel — delivered during IB-009 sprint
**Depends On:** IB-012 (OpenAPI spec, which this extends)

**Constitutional Basis:** Article IX (Right of Review, data portability), C-001 (Emergency Stop always accessible), C-034 (employment lifecycle visible to customer)

**Design Frame — Domain 7 Capabilities:**

| Capability | What the customer does | API |
|---|---|---|
| 7.1 Hire a Professional (guided) | Step-by-step wizard: professional type → Decision Space → goals → activate | POST /api/v1/employment/contracts |
| 7.2 Monitor Activity (polling at MVI) | Approval queue + evidence feed, refreshed on-screen or on pull-to-refresh | GET /api/v1/approvals, GET /api/v1/evidence |
| 7.3 Act on Approval Queue | Approve/reject/confirm-boundary in one tap | POST /api/v1/approvals/{id}/approve |
| 7.4 Emergency Stop (always visible) | Red button, fixed position, pre-warmed WebSocket | WSS /ws/emergency-stop |
| 7.5 View Evidence Ledger | Full audit trail, filterable | GET /api/v1/evidence |
| 7.6 Export Evidence | Data portability download (Article IX) | GET /api/v1/evidence/export |
| 7.7 Manage Authority | Expand/restrict with evidence justification | POST /api/v1/authority/expand |
| 7.8 Manage Contract Lifecycle | Suspend, terminate, renew | PUT/DELETE /api/v1/employment/contracts/{id} |

**Notification model at MVI:** Polling (no new infrastructure). Real-time push via SSE deferred post-MVI. This is a pragmatic decision — polling suffices for approval-gate workflows where latency of seconds is acceptable. Emergency Stop is always real-time via the pre-warmed WebSocket (not polling).

**Constitutional Portal Constraints (enforced in UI, not just described):**
- Emergency Stop present on every authenticated page — fixed position, cannot scroll away, no confirmation dialog
- Evidence records have no edit affordance — read-only with no ambiguity
- Scope boundary confirmation requires typed acknowledgment — no checkbox substitution
- `tenant_id` and internal UUIDs never displayed to customer

**Two missing API endpoints (SA addendum to IB-012):**

1. `GET /api/v1/employment/contracts/{id}/status` — returns professional execution state: `{state: IDLE | EXECUTING | AWAITING_APPROVAL}`. Execution state is derived from Professional Runtime PAAS session + pending ApprovalRequest count. Business Platform queries internally; customer never calls PR directly.

2. `GET /api/v1/professional-templates` — catalogue of WAOOAW-provided professional templates (required for IB-015 / Domain 8). New in IB-015 scope but the endpoint lives in Business Platform.

**Outputs:**
- Domain 7 capability map (Business Architect)
- Addendum to `architecture/reference/api-specs/business-platform.openapi.yaml` (SA — 2 endpoints)

**Status:** WAITING (G5-parallel)

---

## IB-015 — Constitutional Customer Success Agents (Domain 8) — FR-001 Path A

**Goal:** Design Domain 8 capabilities for L1/L2/L3 customer success agents, governed by the constitutional framework under FR-001 (Founder Resolution: Customer as Contract Holder).

**Office:** Business Architect (capabilities) + Runtime Professional (professional type config)
**Priority:** P1 — G5-parallel
**Gate:** G5-parallel
**Depends On:** IB-009 (foundation implementation must exist before CS professional type can be configured), IB-014 (ProfessionalTemplate endpoint)

**Constitutional Basis:** FR-001 (Path A), C-003 (authority licensed), C-030 (Decision Space as primitive), C-035 (Runtime Universality — CS agents run on the same Professional Runtime as marketing/trading agents), DP-003 (Configuration over Code — professional type differences are configuration)

---

### FR-001 Resolution Summary (Founder Decision — 2026-07-07)

**Customer holds the Employment Contract.** Each CS support interaction instantiates an Employment Contract: `Customer → CS_Agent`. WAOOAW provides Decision Space templates (ProfessionalTemplates) that the customer deploys with minimal configuration. The customer retains all constitutional rights over the CS agent: Emergency Stop, Right of Review, evidence ledger ownership, authority management.

This resolves both blocking conflicts from the critical review:
- Tenant isolation: CS agent's JWT carries `tenant_id = customer's tenant_id`. RLS works normally. ✓
- Emergency Stop: Customer is the contract holder. Existing WebSocket mechanism works. ✓

---

### Design Frame — Domain 8 Capabilities

| Capability | Description | Execution Model |
|---|---|---|
| 8.1 Hire CS Agent from Template | Customer selects a WAOOAW-provided CS agent template. Employment Contract created automatically. | Business Platform + ProfessionalTemplate |
| 8.2 Receive L1 Support (Autonomous) | CS agent reads evidence, retrieves status, explains in plain language. No customer approval needed per action. | PAAS (PRE_AUTHORIZED) |
| 8.3 Approve L2 Proposed Change | CS agent proposes a configuration or billing change. Customer approves before execution. | APPROVAL_GATE |
| 8.4 Escalate to Human Expert (L3) | Customer or L2 agent requests human escalation. Agent prepares brief; human expert decides. | Out-of-band (human) |
| 8.5 Stop CS Agent | Emergency Stop — same mechanism as any other professional. Customer exercises via WebSocket. | ADR-004 / ADR-018 |
| 8.6 Review CS Interaction History | Full evidence record of all CS agent actions within this contract. | GET /api/v1/evidence |

### Decision Space Templates (WAOOAW-Managed)

**L1 Template — Autonomous Support Agent:**
```
professionalType:      CUSTOMER_SUCCESS_L1
executionModel:        PRE_AUTHORIZED
authorizedActions:
  - READ_EVIDENCE_SUMMARY (retrieve and summarize customer's own evidence records)
  - READ_CONTRACT_STATUS (retrieve employment contract and professional states)
  - EXPLAIN_ACTION (plain-language explanation of a specific evidence record)
  - GUIDE_SELF_SERVICE (navigation instructions — read-only)
prohibitedActions:
  - Any write operation (modify contract, change Decision Space, process billing)
  - Any operation on another customer's data
alwaysAskActions:
  - Any action type not in authorizedActions above → escalate to L2
```

**L2 Template — Configuration & Billing Agent:**
```
professionalType:      CUSTOMER_SUCCESS_L2
executionModel:        APPROVAL_GATE
authorizedActions:
  - READ_EVIDENCE_SUMMARY (inherited from L1)
  - APPLY_DECISION_SPACE_TEMPLATE (propose applying a WAOOAW pre-approved template change)
  - PROCESS_BILLING_REQUEST (within defined INR threshold)
  - RESET_PROFESSIONAL (propose suspending and reactivating a professional)
prohibitedActions:
  - Process billing above defined threshold without L3 escalation
  - Create or delete Employment Contracts
  - Modify Constitutional Audit Ledger records
alwaysAskActions:
  - Billing requests above threshold → escalate to L3
  - Any action not in authorizedActions → escalate to L3
```

### New Domain Model Concept: ProfessionalTemplate

```
ProfessionalTemplate {
  id:             UUID
  tenantId:       UUID  // WAOOAW's own tenant_id (readable by all as catalogue)
  name:           string  // "L1 Customer Success Agent"
  professionalType: string  // CUSTOMER_SUCCESS_L1 / CUSTOMER_SUCCESS_L2
  decisionSpaceTemplate: DecisionSpaceInput  // pre-filled, customer cannot modify prohibited list
  contractLifecycleType: PERMANENT | SESSION_BOUND
  isPublished:    boolean  // WAOOAW controls which templates are available
  createdAt:      datetime
}
```

**Storage:** `business.professional_templates` table, in WAOOAW's own tenant. All tenants can read published templates via `GET /api/v1/professional-templates` (no RLS restriction on catalogue reads — it is a public catalogue within the platform, analogous to a job board).

**Session-bound contracts:** CS interaction contracts have `contractLifecycleType: SESSION_BOUND`. They transition `EVALUATION → ACTIVE → TERMINATED` within the duration of a support interaction. The standard four-state lifecycle (C-034) applies — just at a shorter timescale.

### Architecture Impact: Zero New Containers

| Component | Change |
|---|---|
| Professional Runtime | New `professional_type` values: `CUSTOMER_SUCCESS_L1` (handled by PAAS Engine), `CUSTOMER_SUCCESS_L2` (handled by Approval-Gate Engine). No code changes — DP-003. |
| Business Platform | New table `professional_templates`. New endpoint `GET /api/v1/professional-templates`. New endpoint `POST /api/v1/employment/contracts/from-template/{templateId}`. |
| Constitutional Engine | No change. Evidence First and Emergency Stop apply as-is. |
| AI Runtime | New tool set for CS agent: `fetch_evidence_summary`, `fetch_contract_status`. Same Decision Space injection pattern. |

**Outputs:**
- Domain 8 capability map (Business Architect)
- `professional_templates` table specification (Data Architect addendum)
- `CUSTOMER_SUCCESS_L1 / L2` Decision Space YAML templates (Runtime Professional)

**Status:** WAITING (G5-parallel, blocked by IB-009)

---

## IB-016 — Platform Operations Architecture

**Goal:** Define the operational capability inventory for WAOOAW platform operators and the observability architecture for constitutional compliance monitoring. No new infrastructure containers at MVI.

**Office:** Platform Architect
**Priority:** P1 — G5-parallel
**Gate:** G5-parallel
**Depends On:** IB-009 (services must exist before ops tooling can be configured)

**Constitutional Basis:** AD-009 (Observability by Default), GENESIS Engineering Quality Mandate (zero manual operational procedures)

---

### Design Frame — Operational Capabilities

| Capability | What operators get | Infrastructure |
|---|---|---|
| **Platform Health** | All service health, DB connection pool, Temporal worker count, cert expiry countdown | OTel metrics → Jaeger (dev) / Azure Monitor Workbooks (cloud) |
| **Constitutional Compliance Monitor** | P99 Emergency Stop latency, Evidence First enforcement rate (% of governance events where CE confirmed before caller returned), CCT pass/fail trend | OTel metrics tagged `constitutional.*` — Azure Monitor alert rules |
| **PAAS Session Management** | View active PAAS sessions by customer, state, and duration; force-terminate crashed sessions | Temporal UI (already in docker-compose) + `GET /api/v1/paas/sessions` (already in PR OpenAPI) |
| **Workflow Management** | View/retry/cancel stuck Temporal employment lifecycle workflows | Temporal UI (already in docker-compose) |
| **Secret & Certificate Expiry** | 30-day warning before expiry on all secrets and certificates | Azure Key Vault → Azure Monitor alerts (cloud); manual check script (dev) |
| **Cost Monitoring** | Per-environment cloud cost; alert on approach to INR 10,000/month (AD-006) | Azure Cost Management alerts |
| **P0 Runbooks** | Documented response for every P0 scenario | `architecture/reference/operations/runbooks/` (produced in IB-009 sprint) |

### Observability Stack (corrected from design frame)

No Grafana at MVI — Grafana is not in `docker-compose.yml` and has no ADR. The decided observability stack (ADR-009) is:
- **Dev:** Jaeger all-in-one (already in docker-compose.yml) — distributed traces, service latency
- **Cloud:** Azure Monitor / Application Insights — OTel traces, metrics, alerts, workbooks

Grafana can be added post-MVI via ADR-019 if Azure Monitor workbooks are insufficient. No ADR = no Grafana in IB-009.

### Constitutional OTel Metric Names (for Runtime Professional)

These must be emitted by the services. The Runtime Professional must instrument them:

| Metric | Emitting Service | Dimensions |
|---|---|---|
| `constitutional.emergency_stop.latency_ms` | Professional Runtime | `contract_id`, `result: confirmed/failed` |
| `constitutional.evidence_first.enforcement_rate` | Constitutional Engine | `calling_service`, `action_type` |
| `constitutional.paas.active_sessions` | Professional Runtime | (gauge, no dimensions needed) |
| `constitutional.evidence.state_transition.count` | Constitutional Engine | `from_state`, `to_state` |
| `constitutional.cct.result` | CI/CD pipeline | `test_name`, `environment`, `result: pass/fail` |

### Operator Events Model (corrected from design frame)

Operator actions (force-terminate session, trigger manual cert rotation, restart a service) are **not** Constitutional Audit Ledger events. The CAL is for professional actions under Employment Contracts. Operator actions have no `contract_id` or `professional_id`.

Operator actions are recorded as **OTel structured events** tagged:
```
span.name:          waooaw.operations.<action_name>
attributes:
  operator_id:      <Keycloak user ID of the WAOOAW operator>
  action:           FORCE_TERMINATE_SESSION | MANUAL_CERT_ROTATION | SERVICE_RESTART | ...
  target:           <session_id or service name>
  reason:           <operator-provided reason>
  timestamp:        <ISO 8601>
```

These are queryable in Jaeger/Azure Monitor and provide an operational audit trail without contaminating the Constitutional Audit Ledger's domain model.

**Outputs:**
- Operational capability spec (Platform Architect)
- OTel metric names added to component specs (SA addendum)
- Runbooks (Platform Architect — produced during IB-009 sprint)

**Status:** WAITING (G5-parallel, blocked by IB-009)

**Who adds items:** Founder, or any office that identifies a needed output from a Constitutional Blocker.

**Who prioritizes:** Founder (acting as COO in Era 0).

**Who closes items:** Reviewer designated in the Work Contract, after evidence is approved.

**What cannot be added:** Items that don't trace to a gate or a constitutional need. Items that ask an office to act outside its Decision Space. Items that bypass the dependency chain.

**The backlog is demand. The organization is supply. Flow is governance.**

---

### IB-019 — DMA Multi-Mode: Chain, Franchise, and Agency Full Architecture

**Goal:** Design the complete DMA architecture for three advanced account modes — company-owned chain (MULTI_UNIT_OWNED), franchise network (FRANCHISE), and digital marketing agency (already partially implemented via C-075/Skill 18). This IB extends the existing Skill 19 (Multi-Location), Skill 18 (Agency Operations), and the benchmark model to fully serve hotel chains, restaurant franchises, furniture store groups, and large agencies.

**Office:** Business Architect (capabilities) + DMA Agent (spec update)

**Priority:** P2 — **WAITING until FR-005 (50+ paying single-unit customers)**

**Gate:** Post-FR-005 (after first paying customer cohort is established and generating cashflow)

**Depends On:** IB-009 (foundation live), FR-005 (50 diverse customers — real revenue before complex architecture investment)

**Why this is P2 and not P0:**
Single-unit customers (Dr. Mehta, Rupali, Ramesh) are the fastest path to revenue, the simplest to serve, and the validation that the core platform works. A hotel chain or franchise network is a longer sales cycle, a more complex integration, and requires the single-unit track record to sell. Yogesh's stated priority: *"Get single unit/account customer onboarded, serving, and creating WaooaW. With secured cashflow, venture into agency, franchise, or multi-unit."* This IB is correctly P2.

**Business case for venturing into this at FR-005:**
- A hotel chain with 10 locations = 10× the revenue of one single-unit customer
- A dental franchise with 50 clinics = 50× the seat revenue at near-zero marginal cost
- An agency with 50 client seats at ₹1,299/seat = ₹64,950/month from one agency relationship
- The complexity investment pays off exponentially once the single-unit product is proven

---

### Gap Inventory (for Work Contract when this IB is authorized)

**Gap 2: Internal benchmark for chains (MULTI_UNIT_OWNED)**

*Problem:* The current 1-7 maturity score compares a business to external competitors. A hotel chain with 10 branches needs a DIFFERENT benchmark: *"Which of my own branches is performing best, and why?"* The internal cross-location benchmark is 10× more actionable than the external one because it leads to replicable improvements.

*Design required:*
- `CROSS_LOCATION_PERFORMANCE_SCORE`: normalized comparison of all locations within one account
- Benchmark dimensions: content consistency, GBP rating, review response rate, engagement, CPL
- Output: "Mumbai branch leads in Instagram engagement. Jaipur branch leads in GBP rating. Kondhwa branch lags in all dimensions — here's a tailored plan to close the gap."
- Drives Skill 19 content routing: "replicate what Mumbai is doing in Kondhwa"

**Gap 3: Budget allocation strategy across locations**

*Problem:* Equal ad spend split across 10 locations is almost always wrong. No framework exists for performance-based, need-based, or strategic allocation.

*Design required:*
- `BUDGET_ALLOCATION_MODEL` enum: EQUAL_SPLIT | PERFORMANCE_BASED | NEED_BASED | STRATEGIC
- Performance-based: allocate proportional to conversion rate per location
- Need-based: give more to locations that are underperforming relative to their market potential
- Strategic: more to new openings (launch budget), less to mature stable locations
- This is a quarterly decision (Skill 21), not monthly
- CE.ValidateAction: C-043 applies per-location (each location has its own ceiling), not per-account

**Gap 4: Brand consistency gate across locations**

*Problem:* The SCR checks each location's content independently. A furniture chain running a "20% off" sale in Mumbai but full price in Delhi, or Pune using a deprecated logo variant, creates brand inconsistency that the current spec cannot detect.

*Design required:*
- `BRAND_CONSISTENCY_CHECK` (new SCR step 5 for MULTI_UNIT accounts):
  - Does this content contradict any concurrent content at another location? (price, promotion, offer)
  - Is the logo, color palette, and font consistent with the approved brand guidelines?
  - If contradicting: APPROVAL_GATE escalation before publishing
- Brand asset vault: approved logo versions, color codes, tone guidelines — shared across all locations

**Gap 5: Cross-client intelligence vs cross-location intelligence (data access model)**

*Problem:* Both agency (Yashus's clients) and chain (hotel's 10 branches) generate cross-unit intelligence, but the data ownership and privacy model is fundamentally different.

| | Agency cross-client | Chain cross-location |
|---|---|---|
| Data owner | Each client owns their own data | Chain owner owns ALL location data |
| C-048 implications | Agent must anonymize (C-048 — no cross-client exposure) | No anonymization needed (same owner) |
| Benchmark access | Tier 3 RAG only (platform aggregate, anonymized) | Direct DB read (all locations same tenant) |
| Platform architecture | Separate tenant_ids | Same tenant_id (multi-location flag) |

*Design required:* Different data access patterns in AI Runtime for agency vs chain intelligence queries.

**Gap 6: Franchise model (FRANCHISE account_mode)**

*Problem:* A franchise has independently-owned franchisees sharing a brand. Each franchisee pays separately. Brand standards are mandatory. The benchmark between franchisees is both competitive and collaborative.

*Design required:*
- `FRANCHISE` account_mode: franchisee accounts linked to a franchisor account
- Franchisor sets: brand guidelines, prohibited content (brand consistency gate), benchmark targets
- Franchisee pays: their own WAOOAW subscription + their own ad spend
- Franchisor sees: aggregate performance across all franchisees (their IP as franchisor)
- Franchisee sees: their own performance + how they rank vs other franchisees (motivational, anonymized)
- Commercial: franchisor may pay a brand protection fee to WAOOAW; franchisees pay standard rate

**Gap 7: Portfolio maturity score + consistency score for chains**

*Problem:* A chain averaging 5/7 maturity with a range of 2-7 has a different problem than a chain consistently at 3/7. Current Skill 1 only produces a per-location score.

*Design required:*
- `PORTFOLIO_MATURITY_SCORE`: weighted average of all location scores
- `BRAND_CONSISTENCY_INDEX`: std deviation of maturity scores across locations
  - Low std dev + high avg = excellent (all locations performing consistently well)
  - Low std dev + low avg = systematic underperformance (whole chain needs work)
  - High std dev = inconsistency problem (some locations great, some failing)
- This feeds the quarterly planning session (Skill 21) with a chain-level strategic framing

---

### Success Criteria for IB-019

When this IB is authorized and completed:
- [ ] MULTI_UNIT_OWNED account mode fully specced (Skill 0 routing → full capability stack)
- [ ] Cross-location performance dashboard (internal benchmark) for chain owners
- [ ] Budget allocation framework (3 models: equal, performance-based, need-based)
- [ ] Brand consistency gate (SCR Step 5 for multi-unit accounts)
- [ ] Franchise model (FRANCHISE account_mode) architecture + commercial model
- [ ] Portfolio maturity + consistency scores in Skill 1 for multi-unit accounts
- [ ] Cross-client vs cross-location data access pattern documented and implemented
- [ ] Simulation run for: "Horizon Hotels — 10 branch chain" → Grade A
- [ ] Simulation run for: "FitFusion Franchise — 25 franchisees" → Grade A

---

### Inputs Required When IB-019 is Authorized

- Real customer(s) with multi-unit requirement (to validate the spec against actual use case)
- FR-005 milestone achieved (50+ single-unit customers — proven revenue)
- Yogesh's explicit authorization ("IB-019 authorized — begin multi-mode architecture")
- SIM-020 and SIM-021 Grade A verified in production (not just simulation)

