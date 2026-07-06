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

**Status:** IN_PROGRESS (Sprint 001 assigned)

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

**Status:** WAITING (blocked by IB-001)

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

**Status:** WAITING (blocked by IB-001, IB-002)

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

**Status:** WAITING (blocked by IB-001)

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

**Status:** WAITING (blocked by IB-002, IB-003, IB-004)

---

## Backlog Index

| ID | Goal | Office | Priority | Gate | Status |
|---|---|---|---|---|---|
| IB-001 | Produce Constitutional Knowledge Corpus | Constitutional Analyst | P0 | G2 | IN_PROGRESS |
| IB-002 | Produce Business Capability Map | Business Architect | P0 | G3 | WAITING |
| IB-003 | Define Architectural Drivers | Business Architect | P0 | G3 | WAITING |
| IB-004 | Define Design Principles | Business Architect | P0 | G3 | WAITING |
| IB-005 | Produce Reference Architecture | Enterprise Architect | P0 | G4 | WAITING |

---

## Backlog Governance

**Who adds items:** Founder, or any office that identifies a needed output from a Constitutional Blocker.

**Who prioritizes:** Founder (acting as COO in Era 0).

**Who closes items:** Reviewer designated in the Work Contract, after evidence is approved.

**What cannot be added:** Items that don't trace to a gate or a constitutional need. Items that ask an office to act outside its Decision Space. Items that bypass the dependency chain.

**The backlog is demand. The organization is supply. Flow is governance.**
