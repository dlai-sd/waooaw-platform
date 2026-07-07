# Knowledge Claim Index

**Produced by:** Constitutional Analyst (Sprint 001)
**Date:** 2026-07-07
**Work Contract:** WC-001
**Total Claims:** 35 (30 original + 5 added in response to EA review R-001)

---

## By Type

### LAW — 11 claims
Constitutional first principles. Source: Constitution and GENESIS. Cannot be contradicted by architecture or implementation.

| ID | Statement |
|---|---|
| C-001 | Human override is absolute and architecturally guaranteed |
| C-002 | Trust earned through observable evidence (First Law) |
| C-003 | Authority licensed through constitutional evidence (Second Law) |
| C-004 | Capability, Trust, and Authority are three independent systems |
| C-005 | Three-Ledger Model — three owners, never merged |
| C-006 | Doctrine of Institutional Independence |
| C-007 | No evidence deleted or modified — append-only |
| C-008 | Constitutional Chain — lower artifacts must not contradict higher |
| C-031 | No significant architectural decision without an ADR |
| C-032 | Implementation may not create architecture — gaps escalate upstream |
| C-033 | Phase Gate passage is constitutionally binding — no skipping |

---

### CONFIRMED — 3 claims
Ratified Constitutional Precedents (CPs). Binding on architecture.

| ID | Statement | Source Precedent |
|---|---|---|
| C-009 | Pre-employment rights visibility is a constitutional obligation | CP-001 |
| C-010 | Proposed state is a first-class institutional concept | CP-002 |
| C-011 | Scope-boundary confirmation is mandatory and distinct from approval | CP-003 |

---

### EMPIRICAL — 7 claims
Direct observations from cases or RED_TEAM audit. Neutral, no inference.

| ID | Statement | Source |
|---|---|---|
| C-012 | Rights visibility influenced Dr. Mehta's hiring decision | Case 001 |
| C-013 | Customer independently invented shadow authority trial | Case 001 |
| C-015 | Creative voice mismatch was primary rejection criterion | Case 002 |
| C-017 | Review-before-execute was incoherent for trading | Case 003 |
| C-019 | Emergency Stop deterministic latency makes PAAS constitutional | Case 003 |
| C-021 | Founder amendment authority unchecked (CRITICAL) | RED_TEAM Attack 001 |
| C-022 | Professional Identity is institutionally dependent (CRITICAL) | RED_TEAM Attack 003 |

---

### HYPOTHESIS — 4 claims
Supported by case evidence, not yet cross-validated. May be contradicted by future cases.

| ID | Statement | Confidence | Needs |
|---|---|---|---|
| C-014 | Shadow authority trial is convergent natural customer behavior | 70% | Case 002/003 cross-validation |
| C-016 | Creative Standard Profile is a constitutional document | 80% | Healthcare/Legal cross-validation |
| C-018 | PAAS is the constitutionally coherent model for millisecond-scale professions | 90% | One additional high-velocity professional domain |
| C-020 | Absolute time guarantee required for human override in high-velocity contexts | 90% | Same cross-validation as C-018 |

---

### ARCHITECTURAL_IMPLICATION — 10 claims
Derived from CONFIRMED or LAW claims. These authorize specific architectural decisions.

| ID | Statement | Authorizes |
|---|---|---|
| C-023 | Evidence First — Constitutional Engine records before success returned | ADR-001 (gRPC synchronous protocol) |
| C-024 | Emergency Stop ≤250ms hard architectural guarantee | ADR-004 (Azure SignalR) |
| C-025 | PAAS is a first-class execution model | ADR-005 (PAAS session isolation) |
| C-026 | Three-ledger separation enforced at database level | ADR-003 (JWT + RLS), Data Architecture |
| C-027 | Constitutional Audit Ledger append-only at database level | ADR-011 (no destructive migrations on constitutional schema) |
| C-028 | Proposed state is a first-class enum in the evidence schema | Data Architecture — evidence schema design |
| C-029 | Scope-boundary confirmation is a distinct record type | Data Architecture — audit record schema |
| C-030 | Decision Space is the single architectural primitive | Enterprise Architecture — core domain model |
| C-034 | Employment lifecycle: Evaluation, Active, Suspended, Terminated states | Enterprise Architecture — employment domain model |
| C-035 | Runtime Universality — all scenarios on one codebase, zero code changes | Professional Runtime architecture |

---

## By Status

| Status | Count | IDs |
|---|---|---|
| RATIFIED | 30 | C-001–C-013, C-015, C-017, C-019, C-021–C-029, C-031, C-032, C-033, C-035 |
| DRAFT | 5 | C-014, C-016, C-018, C-020, C-030, C-034 |

---

## By Source

| Source | Claims Produced |
|---|---|
| Constitution CONSTITUTION.md | C-001 through C-008 |
| GENESIS.md | Contributes to C-008 (Constitutional Chain) |
| PRECEDENTS.md CP-001 | C-009 |
| PRECEDENTS.md CP-002 | C-010 |
| PRECEDENTS.md CP-003 | C-011 |
| PRECEDENTS.md ECI-001 | C-030 |
| Simulation Case 001 | C-012, C-013, C-014 |
| Simulation Case 002 | C-015, C-016 |
| Simulation Case 003 | C-017, C-018, C-019, C-020 |
| RED_TEAM.md | C-021, C-022 |
| Derived (ARCH_IMPL) | C-023 through C-030 |

---

## Cross-Reference: Claims that directly authorize architecture decisions

This section is for the Enterprise Architect. These claims are the constitutional basis for the architecture already documented in `architecture/` and `adr/`.

| Architecture Decision | Constitutional Authority |
|---|---|
| gRPC synchronous protocol for Constitutional Engine (ADR-001) | C-023 (Evidence First), C-002 (First Law) |
| OpenAPI spec-first (ADR-002) | C-008 (Constitutional Chain — interface before implementation) |
| JWT tenant_id for multi-tenancy (ADR-003) | C-005 (Three-Ledger), C-026 (DB-level enforcement) |
| Azure SignalR Emergency Stop (ADR-004) | C-024 (≤250ms guarantee), C-001 (human override absolute) |
| PAAS session isolation (ADR-005) | C-025 (PAAS first-class model), C-018 (PAAS hypothesis) |
| Keycloak identity broker (ADR-008) | C-009 (CP-001: rights visibility — customer must identify before rights are shown) |
| Constitutional Audit Ledger append-only (ADR-011 migration rule) | C-027, C-007 |
| Evidence state machine (Data Architecture) | C-028 (Proposed enum), C-029 (ScopeBoundaryConfirmation record) |
| Core domain: Decision Space as primitive | C-030, C-014 (ECI-001) |
