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

**Status:** IN_PROGRESS — IB-007 complete. docker-compose.yml and .env.example produced in preceding session (attributed to Platform Architect, Sprint 006). Pending formal WC-006 and review before Gate G4/G5 closed.

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

**Status:** WAITING (blocked by IB-008)

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
| IB-008 | Infrastructure Architecture + Docker Compose | Platform Architect | P0 | G4/G5 | IN_PROGRESS |
| IB-009 | Foundation Implementation (skeleton) | Runtime Professional | P0 | G5 | WAITING |

---

## Backlog Governance

**Who adds items:** Founder, or any office that identifies a needed output from a Constitutional Blocker.

**Who prioritizes:** Founder (acting as COO in Era 0).

**Who closes items:** Reviewer designated in the Work Contract, after evidence is approved.

**What cannot be added:** Items that don't trace to a gate or a constitutional need. Items that ask an office to act outside its Decision Space. Items that bypass the dependency chain.

**The backlog is demand. The organization is supply. Flow is governance.**
