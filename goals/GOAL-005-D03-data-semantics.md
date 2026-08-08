# D-03 — Durable Identity and State Data Semantics

**Producing Institution:** INST-006 — Data Architect
**Authorization:** GOA-GOAL-005-INST-006-01
**Status:** CONTRIBUTED — data semantics only, implementation-neutral

## Acceptance Record

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-006-01 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-08T11:20:20+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-006-01 |
| `acceptance_timestamp` | 2026-08-08T11:20:20+00:00 |
| Decision | ACCEPTED |

## Contribution Record

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-006-01 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-08T11:20:21+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-006-01 |
| Contribution | D-03 durable identity, state, idempotency, evidence-correlation, and continuity data semantics |

## Durable Identity Semantics

| Identity class | Semantic owner | Non-equivalence boundary |
|---|---|---|
| Employment Relationship | Platform constitutional domain | Not conversation, contract, payment, or participant identity |
| Participant | Originating authority domain with constitutional mapping | Does not imply employment or payment state |
| Conversation | Channel/runtime domain | Cannot create, mutate, or replace relationship identity |
| Contract | Contract-governance domain | Never reused as relationship identity |
| Payment | Billing domain | Never sufficient as activation identity by itself |
| Professional | Agent-governance domain | Not customer or relationship identity |
| Customer | Customer/tenant domain | Not merged with participant roles without explicit binding |

These identities may be linked but never interchanged or collapsed.

## Aggregate and Correlation Semantics

The Employment Relationship is AE-01's primary lifecycle aggregate. Every consequential event carries relationship identity as primary correlation anchor and, where relevant, participant, contract, payment, and conversation identities as secondary anchors. Correlation preserves authorization, proposal/consent, payment, activation, continuity, and later-lifecycle causality.

## State Persistence

1. Relationship state is a durable, time-ordered history, not only a mutable current snapshot.
2. State changes require linked precondition evidence.
3. Proposed, accepted-contract, active, paused/stopped, and terminated states remain semantically distinct.
4. Channel changes do not cause lifecycle transitions.
5. Payment does not implicitly mutate employment state without contract and authority evidence.

## Idempotency and Activation Evidence

Every externally replayable consequential command has an idempotency intent key scoped to tenant, relationship, and command purpose. The same key and materially same command returns the same constitutional outcome. The same key with materially different content produces an explicit conflict record.

Exactly-once activation is an evidence property. Relationship-version activation intent means relationship identity plus accepted-contract identity; activation-eligible payment identity is a mandatory evidence dimension. Activation Intent Identity is the full tuple of tenant identity, relationship identity, accepted-contract identity, and activation-eligible payment identity. Command purpose is fixed as `ACTIVATE_EMPLOYMENT_RELATIONSHIP`, validated semantically, and excluded from uniqueness so purpose variation cannot create another activation. A valid chain proves explicit contract acceptance, activation-eligible payment, required authority, and no prior successful activation for the tuple. Replay produces deterministic non-duplication evidence linked to the original activation record. Payment alone never constitutes activation intent.

## Tenant and Channel Continuity

- Relationship, participant, state, and evidence records are constitutionally tenant-scoped.
- Cross-tenant correlation requires explicit constitutional authorization.
- Tenant scope is mandatory retrieval semantics, not an optional filter.
- Channel handoff links a new conversation container to the same relationship.
- Handoff evidence proves participant reauthentication, preserved relationship identity, and preserved contract/authority context.
- These semantics do not select a D-04 transport protocol.

## Retention and Erasure

Customer Evidence, Professional Experience, and Constitutional Audit remain separate ledgers. Constitutional audit facts are append-only and non-retroactive. Erasure distinguishes legally erasable customer personal-data payloads from constitutional event integrity that must be preserved. D-02 must make this rights boundary normative.

## Attribution and Retrieval

Every material relationship record is attributable to its producing Institution/system actor, triggering participant context, governing authority context, and production time. Retrieval must support a relationship timeline, participant accountability, activation-proof reconstruction, and checks of rights, limits, and Emergency Stop visibility.

## Consistency and Failure

Relationship correctness takes precedence over channel immediacy. Partial failure fails safe toward non-duplication and non-escalation of authority. An incomplete evidence chain leaves a transition non-final or explicitly failed. Secondary projections may converge eventually; constitutional lifecycle truth may not. Conflicts are explicit and attributable, never silently overwritten.

## Conformance Checks

1. **Identity separation:** zero substitution of relationship identity by conversation, contract, payment, professional, or customer identity.
2. **Activation uniqueness:** exactly one successful outcome for each relationship-version activation intent.
3. **Replay determinism:** replay resolves to the prior outcome or an explicit conflict.
4. **Tenant boundary:** zero unauthorized cross-tenant retrievals.
5. **Continuity:** every channel continuation has relationship-preserving handoff evidence.
6. **Attribution:** every material lifecycle event has actor and production-time attribution.
7. **Transition validity:** every transition links its prerequisite evidence.
8. **Audit immutability:** constitutional evidence has no retroactive overwrite/delete behavior.
9. **Reconstruction:** evidence reconstructs proposal through activation and later lifecycle.
10. **Boundary integrity:** payment success alone never creates or mutates employment state.

## Gap Disposition

- G5-TRIAL-POLICY-01 is nonblocking for D-03 and remains a D-05 closure requirement.
- Detailed AEEC retention and rights wording is a nonblocking D-02 dependency.
- D-04 channel protocol and security assurance are nonblocking for D-03.

No gap blocks this D-03 contribution.

## Authority Boundary

This contribution defines data semantics only. It defines no database schema, API, storage engine, code, implementation sequence, or D-04 channel protocol. INST-006 does not approve its own evidence or perform D-07 validation.

## Learning Record

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-006-01 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-08T11:20:22+00:00 |
| `improvement_signal` | D-02 should make explicit that relationship identity is independent from channel, contract, payment, customer, and professional identities. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |

## Clarification Contribution Record

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | CCR-GOAL-005-INST-006-01 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-08T11:46:12+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-006-01 |
| Decision | R-036 activation terminology correction accepted; canonical tuple reconciled by INST-004 |

## Clarification Learning Record

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-006-02 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-08T11:46:13+00:00 |
| `improvement_signal` | Distinguish activation intent from its evidence dimensions, then define uniqueness over one canonical constitutional tuple. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |