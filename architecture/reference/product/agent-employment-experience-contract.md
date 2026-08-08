# Agent Employment Experience Contract — Foundation v1.0

**Status:** D-02 CONTRIBUTED — PENDING GATE REVIEW
**Version:** 1.0-foundation
**Program:** GOAL-005
**Work Contract:** WC-052
**Purpose:** Define the invariant customer-facing relationship shared by every WAOOAW professional across WhatsApp, web, mobile, and future supported channels.

> This is not ADR-035's Platform-Agent Contract. ADR-035 governs machine signals between platform services and agents. Agent Base Spec v1.0 governs common agent behavior. This contract governs what a customer may consistently expect from the employment relationship.

## 1. Contract Boundaries

| Contract | Governs | Does not govern |
|---|---|---|
| Agent Employment Experience Contract | Customer journey, rights, relationship state, channel continuity, employment transitions | Domain skill behavior or service-to-agent signal schemas |
| Agent Base Spec | Behavior every agent inherits | Customer-channel composition and employment UX |
| Platform-Agent Contract | Versioned platform signals consumed by agents | Customer-facing journey semantics |
| Agent domain specification | Professional expertise, skills, Decision Consequence Map, domain vocabulary | Generic employment platform behavior |

## 2. Normative Foundation

| Clause | Normative obligation | Constitutional basis |
|---|---|---|
| AEEC-01 | Mint one Employment Relationship at first valid `DISCOVERED` admission; retries reuse it unless an evidenced customer-authorized fork exists. | C-005, C-026, C-034; D-03 |
| AEEC-02 | Before trial or commitment, disclose rights, skills, limitations, authority, evidence posture, Emergency Stop, and price consequences in plain language. | C-009, C-012, C-043, C-049, C-051 |
| AEEC-03 | Capability, Trust, and Authority are non-substitutable; capability or trust never grants or expands authority. | C-002, C-003, C-004 |
| AEEC-04 | Interview and trial expose proposed behavior only. Trial mode is explicit and cannot execute consequential external action or silently become paid employment. | C-001, C-038, C-049, C-088 |
| AEEC-05 | Configure outcome, Decision Space, budget ceiling, skills, review cadence, and stop conditions conversationally in business language. | C-030, C-037, C-039, C-043 |
| AEEC-06 | Contract formation requires explicit acceptance by an authorized same-tenant participant and immutable evidence of accepted terms and authority scope. Ordinary approval is distinct from explicit scope-boundary confirmation. | C-009, C-010, C-011, C-034 |
| AEEC-07 | Activation uses the tuple tenant + relationship + accepted contract + activation-eligible payment. Purpose is fixed as `ACTIVATE_EMPLOYMENT_RELATIONSHIP` and excluded from uniqueness. Replay returns the prior outcome without duplicate activation, charge, or relationship. | C-023, C-038, C-088, C-090; D-03 |
| AEEC-08 | Every consequential transition is attributable and reconstructable; it cannot report success unless constitutional evidence commits. | C-002, C-005, C-007, C-023 |
| AEEC-09 | Emergency Stop remains reachable across channels. Release to `PAUSED` or `ACTIVE` requires explicit same-tenant customer authority linked to the stop evidence; non-customer action may only terminate. | C-001, C-024, C-038; D-03 |
| AEEC-10 | Channel changes presentation only, never relationship identity, rights, authority, billing state, or lifecycle ownership. | C-006, C-026, C-034, C-035 |
| AEEC-11 | Governance/evidence unavailability halts consequential transitions. Uncertain activation remains pre-active; degradation is disclosed and attributable. | C-023, C-079 |
| AEEC-12 | Information asymmetry, concealed degradation, and self-serving or known-undeliverable recommendations are prohibited. | C-048, C-049 |
| AEEC-13 | Customer Evidence, Professional Experience, and Constitutional Audit remain separate; erasable personal payloads are distinguished from append-only constitutional event integrity subject to applicable law. | C-005, C-007, C-063 |
| AEEC-14 | AE-02 through AE-06 inherit this foundation and may specialize domain behavior without weakening common rights or invariants. | GOAL-005; D-01 |
| AEEC-15 | Every downstream clause and conformance artifact traces to constitutional claims and D-03 invariants. | C-059 |
| AEEC-16 | Detailed alerts, reviews, later lifecycle commerce, multi-agent, version, and organizational-delegation behavior remains deferred to its named wave and cannot weaken AEEC-01 through AEEC-15. | C-008, C-029, C-032, C-041, C-053, C-094, C-099 |

## 3. Cross-Channel Invariants

1. One employment relationship has one durable identity across all channels.
2. A channel changes presentation, not rights, authority, evidence, billing, or relationship state.
3. The customer can always discover current authority, active work, material evidence, cost state, and Emergency Stop.
4. A channel handoff requires authenticated continuity and cannot silently merge people, tenants, or conversations.
5. A trial carries constitutional rights from its first consequential interaction.
6. Hire is an explicit evidenced transition; conversation alone cannot silently create a paid relationship.
7. Domain vocabulary may specialize presentation but cannot weaken common rights or hide limitations.
8. Loss of a channel must not destroy the relationship or authorize work that was not previously authorized.

## 4. Open Policy Placeholders

| Placeholder | Closure |
|---|---|
| G5-TRIAL-POLICY-01 | D-05 defines trial duration, inclusion, price/credit, ownership, expiry, conversion, cancellation/refund, qualifying customer, and proof threshold; blocks D-06 finalization |
| OP-LIFECYCLE-COMM-01 | D-05/D-06 closes pause and termination commercial edge handling |
| OP-CHANNEL-ASSURANCE-01 | D-04 defines channel authentication and handoff assurance without redefining D-03 identity |

## 5. Foundation Conformance

Foundation conformance requires deterministic checks for rights-before-commitment; scope confirmation distinct from approval; capability/trust/authority separation; customer-only evidenced stop release; attributable timeline reconstruction; fail-safe CE/evidence unavailability; non-exploitation; price/limitation disclosure; retention/erasure boundary; channel invariance; four-part activation uniqueness and replay; and complete claim/D-03 traceability.

## 6. Institutional Records

### INST-004 — Enterprise Architecture

| Field | Acceptance | Contribution | Learning |
|---|---|---|---|
| `institution_id` | INST-004 | INST-004 | INST-004 |
| `goal_id` | GOAL-005 | GOAL-005 | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-02 | CR-GOAL-005-INST-004-02 | LR-GOAL-005-INST-004-03 |
| `record_type` | Acceptance Record | Contribution Record | Learning Record |
| `produced_at` | 2026-08-08T13:10:00+00:00 | 2026-08-08T13:10:01+00:00 | 2026-08-08T13:10:02+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-02 | GOA-GOAL-005-INST-004-02 | — |
| Result | ACCEPTED | AEEC Foundation v1.0 contributed | D-03 invariants reduce downstream ambiguity without selecting protocols |

### INST-002 — Constitutional Analysis

| Field | Acceptance | Contribution | Learning |
|---|---|---|---|
| `institution_id` | INST-002 | INST-002 | INST-002 |
| `goal_id` | GOAL-005 | GOAL-005 | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-002-01 | CR-GOAL-005-INST-002-01 | LR-GOAL-005-INST-002-01 |
| `record_type` | Acceptance Record | Contribution Record | Learning Record |
| `produced_at` | 2026-08-08T13:11:00+00:00 | 2026-08-08T13:11:01+00:00 | 2026-08-08T13:11:02+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-002-01 | GOA-GOAL-005-INST-002-01 | — |
| Result | ACCEPTED | Rights, consent, Human Override, evidence, and traceability contributed | Rights must be lifecycle preconditions, not informational appendices |
