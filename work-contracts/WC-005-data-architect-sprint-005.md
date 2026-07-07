# Work Contract 005 — Data Architect

**Office:** Data Architect (Office 06)
**Sprint:** 005
**Epoch:** 3 — Architecture
**Backlog Item:** IB-007 — Produce Data Architecture (completing outstanding artifact)
**Gate:** G4 (partial — IB-007 is one of three G4-blocking items)
**Reviewer:** Solution Architect (interface validation). Constitutional Analyst (Evidence First compliance).

**Gate G4 Definition of Done (for IB-007 contribution):**
> Runtime Professional declares: "I can write migrations from this."

**Authorized Inputs:**

| Source | Location | Purpose |
|---|---|---|
| Component Specifications | `architecture/reference/components/` | Define what data each service owns and reads |
| Three-Ledger claims | `knowledge/claims/C-005.md`, `C-007.md`, `C-027.md` | Constitutional authority for ledger design |
| Evidence state machine claim | `knowledge/claims/C-028.md` | Evidence state transitions |
| Architectural Drivers (data) | `knowledge/architectural-drivers.md` | AD-003, AD-004 (audit immutability, multi-tenant) |
| ADR-003 | `adr/ADR-003-jwt-claims-multi-tenancy.md` | JWT propagation to DB RLS |
| ADR-011 | `adr/ADR-011-database-migration-strategy.md` | Migration constraints |
| Existing ledger design | `architecture/reference/data/ledger-design.md` | What has been produced; do not duplicate |
| Office Charter | `constitution/ORGANIZATION.md` Office 06 | Decision Space and obligations |

**Authorized Output Location:**
- `architecture/reference/data/evidence-schema.md` — the evidence state machine and related schema specifications that complete IB-007

**What is NOT authorized:**
- Changing ledger-design.md (already produced and accepted)
- Producing EF Core migration code (Runtime Professional's scope, Gate G5)
- Altering the three-schema separation (already specified in ledger-design.md)

---

## Tasks

**DA-001 — Produce Evidence State Machine Specification**

Produce `architecture/reference/data/evidence-schema.md`.

This document must specify:
1. The complete evidence state machine: all states, all valid transitions, the constitutional basis for each transition, and which service triggers each transition
2. The state enforcement approach: how the schema prevents invalid transitions (DB constraint or trigger)
3. The `constitutional_basis` field specification: what values are valid, who validates them, and how they are enforced
4. The PAAS execution variant: how the evidence state machine differs for PAAS (pre-authorized) vs Approval-Gate work
5. The Emergency Stop evidence record: what state the in-flight evidence record must be set to when an Emergency Stop fires mid-execution
6. Scope-boundary confirmation state: the `SCOPE_BOUNDARY_PENDING` state path and how it resolves
7. Cross-reference to ledger-design.md: confirm no duplication, only extension

**Constitutional obligations for this task:**
- C-028 (PROPOSED must be a first-class enum, not a boolean)
- C-007 (no state transition may be reversed or deleted once recorded)
- C-027 (append-only — state "transitions" are new records, not updates to existing records)
- AD-002 (Evidence First — every state transition must produce a ledger record before the calling service returns success)

Status: `READY`
Dependencies: ledger-design.md (DONE), all 4 component specs (DONE)
