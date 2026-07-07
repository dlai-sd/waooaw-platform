# Work Contract 002 — Chief Business Architect

**Office:** Chief Business Architect (Office 03)

**Sprint:** 002

**Epoch:** 2 — Knowledge System (concluding) / Epoch 3 — Architecture (opening)

**Backlog Items:**
- IB-002 — Produce Business Capability Map
- IB-003 — Define Architectural Drivers
- IB-004 — Define Design Principles

**Goal:** Pass Gate G3

**Gate G3 Definition of Done:**

> The Enterprise Architect can design the complete system boundary without requesting Founder clarification.

**Reviewer:**
- Constitutional Analyst — validates constitutional traceability (every capability cites a claim or acceptance scenario)
- Enterprise Architect — validates architectural alignment (drivers and principles constrain architecture correctly)

**Authorized Inputs:**

| Source | Location | Purpose |
|---|---|---|
| All ratified claims | `knowledge/claims/` (C-001 through C-035) | Constitutional authority for capabilities |
| Confidence Register | `knowledge/confidence-register.md` | Claim confidence context |
| Claim Index | `knowledge/index.md` | Cross-reference and architectural implications |
| GENESIS Part 01 | `constitution/GENESIS.md` Part 01 | Founder Vision, Acceptance Scenarios 001–004 |
| Office Charter | `constitution/ORGANIZATION.md` (Office 03 only) | Decision Space and obligations |

**Authorized Output Location:**
- `knowledge/business-capabilities.md`
- `knowledge/architectural-drivers.md`
- `knowledge/design-principles.md`

---

## Tasks

**BA-001 — Produce Business Capability Map**

Produce `knowledge/business-capabilities.md`.

Every capability must:
- Be named in verb + object format
- Cite the constitutional claim(s) or acceptance scenario(s) that demand it
- Be traceable — no capability may exist without a constitutional basis

Status: `READY`
Dependencies: None

---

**BA-002 — Produce Architectural Drivers**

Produce `knowledge/architectural-drivers.md`.

Every driver must:
- State the non-negotiable constraint it imposes
- Name the capabilities it constrains
- State a measurable target where possible
- Cite the constitutional claim or GENESIS source

Status: `READY`
Dependencies: BA-001

---

**BA-003 — Produce Design Principles**

Produce `knowledge/design-principles.md`.

Every principle must:
- State a directive (what engineering must do)
- Cite the constitutional claim(s) it derives from
- State an enforcement approach

Status: `READY`
Dependencies: BA-001, BA-002

---

**BA-004 — Constitutional Analyst Review**

Raise review request to Constitutional Analyst. CA verifies that every capability cites at minimum one ratified claim or acceptance scenario, and that no capability contradicts a constitutional claim.

Status: `BLOCKED`
Dependencies: BA-001, BA-002, BA-003

---

**BA-005 — Enterprise Architect Review**

Raise review request to Enterprise Architect. EA verifies that architectural drivers are complete, specific, and constrain the right architectural decisions. EA verifies design principles are actionable.

Status: `BLOCKED`
Dependencies: BA-001, BA-002, BA-003

---

## Definition of Done

Sprint 002 is complete when:

1. `knowledge/business-capabilities.md` exists — every capability constitutionally traced
2. `knowledge/architectural-drivers.md` exists — every driver measurable and claimed
3. `knowledge/design-principles.md` exists — every principle actionable and traced
4. CA review: APPROVED
5. EA review: APPROVED

**Gate G3 Test:**

The Founder will present the three outputs to the Enterprise Architect (without additional context) and ask: *"Can you design the system boundary from this?"*

If YES → Gate G3 passes. Enterprise Architect Sprint begins.

If NO → Sprint 002 is extended. Missing capabilities, drivers, or principles are identified.

---

## Operational Discoveries

*Record ambiguities encountered during execution.*
