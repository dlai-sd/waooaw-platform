# Knowledge Confidence Register

**Produced by:** Constitutional Analyst (Sprint 001)
**Date:** 2026-07-07
**Work Contract:** WC-001
**Status:** Complete — 30 claims

---

## Reading this Register

- **LAW**: Derived from constitutional first principles. Can only be contradicted by a constitutional amendment. Confidence ≥ 95%.
- **CONFIRMED**: Survived adversarial testing. Ratified as a Constitutional Precedent (CP). Confidence 90–97%.
- **HYPOTHESIS**: Supported by case evidence but not yet cross-validated. May be contradicted by future cases. Confidence 70–90%.
- **EMPIRICAL**: Direct observation from a simulation case or audit. Neutral, no inference. Confidence 95–98%.
- **ARCHITECTURAL_IMPLICATION**: Derived from CONFIRMED or LAW claims. Authorizes specific architectural decisions. Confidence 85–98%.

---

## Register

| ID | Type | Statement (abbreviated) | Confidence | Status | Produces |
|---|---|---|---|---|---|
| C-001 | LAW | Human override is absolute and architecturally guaranteed | 100% | RATIFIED | C-022, C-023 |
| C-002 | LAW | Trust earned through observable evidence (First Law) | 100% | RATIFIED | C-023, C-027 |
| C-003 | LAW | Authority licensed through constitutional evidence (Second Law) | 100% | RATIFIED | C-010, C-025 |
| C-004 | LAW | Capability, Trust, Authority are three independent systems | 100% | RATIFIED | — |
| C-005 | LAW | Three-Ledger Model — owned by different stakeholders, never merged | 100% | RATIFIED | C-026 |
| C-006 | LAW | Doctrine of Institutional Independence | 100% | RATIFIED | C-026 |
| C-007 | LAW | No evidence deleted or modified — append-only | 100% | RATIFIED | C-027 |
| C-008 | LAW | Constitutional Chain — lower artifact must not contradict higher | 100% | RATIFIED | — |
| C-009 | CONFIRMED | Pre-employment rights visibility is a constitutional obligation (CP-001) | 95% | RATIFIED | C-028 |
| C-010 | CONFIRMED | Proposed state is a first-class institutional concept (CP-002) | 95% | RATIFIED | C-028 |
| C-011 | CONFIRMED | Scope-boundary confirmation is mandatory, distinct from approval (CP-003) | 95% | RATIFIED | C-029 |
| C-012 | EMPIRICAL | Rights visibility influenced Dr. Mehta's hiring decision (Case 001) | 95% | RATIFIED | C-009 |
| C-013 | EMPIRICAL | Shadow authority trial invented independently by customer (Case 001) | 95% | RATIFIED | C-010, C-014 |
| C-014 | HYPOTHESIS | Shadow authority trial is convergent natural customer behavior | 70% | DRAFT | — |
| C-015 | EMPIRICAL | Creative voice mismatch was Sana's primary rejection criterion (Case 002) | 95% | RATIFIED | C-016 |
| C-016 | HYPOTHESIS | Creative Standard Profile is a constitutional document for creative professions | 80% | DRAFT | C-030 |
| C-017 | EMPIRICAL | Review-before-execute was incoherent for trading execution (Case 003) | 98% | RATIFIED | C-018, C-025 |
| C-018 | HYPOTHESIS | PAAS model is the constitutionally coherent alternative for millisecond-scale professions | 90% | DRAFT | C-025 |
| C-019 | EMPIRICAL | Emergency Stop deterministic latency makes PAAS constitutionally valid (Case 003) | 97% | RATIFIED | C-020, C-024 |
| C-020 | HYPOTHESIS | Absolute time guarantee required for human override in high-velocity contexts | 90% | DRAFT | C-024 |
| C-021 | EMPIRICAL | RED_TEAM: Founder amendment authority unchecked (Attack 001, CRITICAL) | 98% | RATIFIED | — |
| C-022 | EMPIRICAL | RED_TEAM: Professional Identity is institutionally dependent (Attack 003, CRITICAL) | 97% | RATIFIED | — |
| C-023 | ARCH_IMPL | Evidence First — Constitutional Engine records before returning success | 97% | RATIFIED | — |
| C-024 | ARCH_IMPL | Emergency Stop ≤250ms hard architectural guarantee | 97% | RATIFIED | — |
| C-025 | ARCH_IMPL | PAAS is a first-class execution model requiring dedicated runtime | 95% | RATIFIED | — |
| C-026 | ARCH_IMPL | Three-ledger separation enforced at database layer (schema + RLS) | 95% | RATIFIED | — |
| C-027 | ARCH_IMPL | Constitutional Audit Ledger append-only at database level | 98% | RATIFIED | — |
| C-028 | ARCH_IMPL | Proposed state is a first-class enum in the evidence schema | 95% | RATIFIED | — |
| C-029 | ARCH_IMPL | Scope-boundary confirmation is a distinct record type in the audit ledger | 95% | RATIFIED | — |
| C-030 | ARCH_IMPL | Decision Space is the single architectural primitive | 85% | DRAFT | — |

---

## Confidence Distribution

| Type | Count | Mean Confidence |
|---|---|---|
| LAW | 8 | 100% |
| CONFIRMED | 3 | 95% |
| EMPIRICAL | 7 | 96.4% |
| HYPOTHESIS | 4 | 82.5% |
| ARCHITECTURAL_IMPLICATION | 8 | 95.3% |
| **TOTAL** | **30** | — |

---

## Claims Requiring Founder Deliberation

The following claims are DRAFT and cannot be consumed by downstream offices until Founder reviews:

| ID | Type | Risk if acted upon prematurely |
|---|---|---|
| C-014 | HYPOTHESIS | Low — shadow authority support is architecturally safe to build speculatively |
| C-016 | HYPOTHESIS | Medium — may require constitutional amendment; affects creative profession employment model |
| C-018 | HYPOTHESIS | Low — PAAS model is already architecturally committed; hypothesis supports the commitment |
| C-020 | HYPOTHESIS | Low — 250ms bound is already architecturally committed (GENESIS parameter); hypothesis supports it |
| C-030 | ARCH_IMPL | Medium — ECI-001 not yet confirmed; if Decision Space is not the primitive, this architectural framing needs revision |
