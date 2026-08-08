# D-03 — Identity and Employment State Model

**Producing Institution:** INST-004 — Enterprise Architect
**Authorization:** GOA-GOAL-005-INST-004-01
**Status:** CONTRIBUTED — specification-level, implementation-neutral

## Acceptance Record

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-01 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-08T11:30:15+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-01 |
| `acceptance_timestamp` | 2026-08-08T11:30:15+00:00 |
| Decision | ACCEPTED |

## Contribution Record

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-004-01 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-08T11:30:16+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-01 |
| Contribution | D-03 Identity and Employment State Model architecture |

## Scope

This contribution defines architecture-level identity, employment lifecycle, legal transition, evidence, and idempotency semantics. It consumes D-01, R-035, and open constraint G5-TRIAL-POLICY-01. It does not define APIs, schemas, code, deployment, D-02 clause text, D-04 transport contracts, D-06 Work Contracts, or commercial policy.

## Identity Model

| Identity | Meaning |
|---|---|
| Tenant identity | Legal and isolation boundary |
| Employment Relationship identity | Durable cross-channel identity of one governed customer-professional relationship |
| Participant identity | Person or institutional actor, role-bound at relationship scope |
| Professional identity | Digital professional identity independent of channel sessions |
| Authority identity | Licensed authority snapshot/version active at a relationship state |
| Contract identity | Accepted contract/version governing active authority |
| Payment activation identity | Activation-eligible payment-event identity used for exactly-once behavior |
| Channel continuity identity | Channel-specific binding to one Employment Relationship |
| Correlation identity | End-to-end causal reference for a consequential command or transition |

Identity invariants:

1. One Employment Relationship persists across supported channels; channel changes never mint a relationship.
2. An Employment Relationship identity is minted exactly once at first valid `DISCOVERED` admission for a tenant-participant-professional evaluation intent. Retries, reconnects, and duplicate admissions reuse it. A new relationship requires explicit customer-authorized fork evidence referencing the source relationship.
3. Capability, trust, and authority remain distinct; capability never implies authority.
4. Participant roles are scoped to one tenant and one relationship.
5. Trial/live mode is explicit and customer-visible.
6. Transitions require attributable, authenticated authority within the same tenant.
7. Emergency Stop is relationship-resolvable across channels.
8. Consequential transitions and approvals produce append-only evidence.

## Aggregate Boundary

The **Employment Relationship aggregate** owns relationship identity and tenant binding, lifecycle state, participant-role bindings, authority snapshot reference, accepted-contract checkpoint, activation checkpoint, channel-continuity bindings, transition/correlation references, and pause/stop/resume/terminate markers.

Domain execution, skill internals, trial commercial values, transport mechanics, and persistence implementation remain outside the aggregate.

## Lifecycle

| State | Permitted next states |
|---|---|
| `DISCOVERED` | `INTERVIEWING` |
| `INTERVIEWING` | `TRIAL_ACTIVE`, `CONFIGURING` |
| `TRIAL_ACTIVE` | `CONFIGURING` |
| `CONFIGURING` | `CONTRACT_PENDING_ACCEPTANCE` |
| `CONTRACT_PENDING_ACCEPTANCE` | `CONTRACT_ACCEPTED_PENDING_PAYMENT` |
| `CONTRACT_ACCEPTED_PENDING_PAYMENT` | `ACTIVATION_PENDING` |
| `ACTIVATION_PENDING` | `ACTIVE` |
| `ACTIVE` | `PAUSED`, `STOPPED_EMERGENCY`, `TERMINATED` |
| `PAUSED` | `ACTIVE`, `STOPPED_EMERGENCY`, `TERMINATED` |
| `STOPPED_EMERGENCY` | `PAUSED`, `ACTIVE`, `TERMINATED` |
| `TERMINATED` | none |

No trial state can transition directly to `ACTIVE`. Exit from `STOPPED_EMERGENCY` to `PAUSED` or `ACTIVE` requires an explicit customer-authorized release command from an authorized same-tenant employer participant, with evidence linked to the originating stop correlation identity. Timeout, system action, retry, channel possession, reauthentication, or reconnection cannot release the stop. A constitutionally authorized non-customer action may transition from `STOPPED_EMERGENCY` only to `TERMINATED`.

## Transition Preconditions

| Command | Preconditions |
|---|---|
| Start interview | Rights, limitations, authority visibility, and participant authentication |
| Enter trial | Trial disclosure; explicit trial/live distinction; no consequential external-execution entitlement |
| Submit configuration | Outcome, budget, authority boundaries, and stop conditions proposed in business language |
| Present contract | Complete configuration and rights/boundary disclosures |
| Accept contract | Explicit acceptance by an authorized participant |
| Confirm activation payment | Accepted contract and activation-eligible validated payment event |
| Activate | Accepted contract, confirmed payment, no prior successful activation for the activation identity |
| Pause/resume | Legal current state and authorized command |
| Emergency stop | Valid stop authority; immediate hold and rejection of further consequential commands |
| Terminate | Authorized command, termination evidence, and permanent removal of active execution authority |
| Channel handoff | Same tenant and relationship, target-channel reauthentication, no implicit role merge |

## Exactly-Once Activation

Activation is one constitutional transition. Activation Intent Identity is the four-part tuple of tenant identity, relationship identity, accepted-contract identity, and activation-eligible payment identity. Command purpose has one canonical semantic value, `ACTIVATE_EMPLOYMENT_RELATIONSHIP`; it is validated but is not an identity dimension. The first valid activation records `ACTIVE` and its evidence correlation. Replay of the same tuple returns the existing outcome without another activation, charge, contract activation, or relationship. Purpose aliases or variations cannot create another activation path. Conflicting mappings are rejected and evidenced as integrity violations.

## Evidence, Authority, and Continuity

1. Every consequential command carries one correlation identity reused by its resulting records.
2. A transition is invalid when its evidence commitment fails.
3. Scope-boundary confirmation remains distinct from ordinary approval.
4. Trial/live changes are evidenced and customer-visible.
5. Relationship, participant, and authority identities link every consequential transition.
6. Channels transport and present state; the Employment Relationship owns state.
7. Channel failure cannot terminate employment or alter authority.
8. Authority snapshots are versioned and transition-bound; changes are explicit governed events.
9. Relationship identities cannot cross tenant boundaries.

## Failure and Degradation

- Constitutional-governance or evidence-gate unavailability halts consequential transitions.
- Uncertain payment keeps the relationship pre-active.
- Continuity failure preserves the last valid state and cannot duplicate a transition on reconnect.
- Partial failure and replay follow exactly-once rules.
- Unresolved policy blocks policy-dependent commercialization, not this foundation model.

## Cross-Deliverable Ownership

| Deliverable | Owns |
|---|---|
| D-03 | Identity, state, transition, idempotency, and evidence-correlation semantics |
| D-02 | Normative clauses consuming D-03 semantics |
| D-04 | Channel transport and continuity conformance |
| D-05 | Shared policy-gap closure, including trial policy |
| D-06 | Release grooming and simulation consumption of approved foundations |

No downstream deliverable may silently redefine D-03 invariants.

## Acceptance Criteria

D-03 architecture conforms only when:

1. One non-overlapping Employment Relationship aggregate is declared.
2. Identity classes and participant roles are explicit and tenant-scoped.
3. The state set covers discovery through activation plus pause, stop, and termination.
4. Illegal paths and all consequential transition preconditions are explicit.
5. Exactly-once activation defines replay and conflict behavior.
6. Evidence and correlation invariants cover all consequential transitions.
7. Channel continuity preserves relationship identity.
8. Authority/capability separation holds throughout.
9. Failure semantics prevent constitutional bypass.
10. Cross-deliverable ownership is non-overlapping.
11. G5-TRIAL-POLICY-01 is consumed but not resolved here.

## Gap Disposition

- G5-TRIAL-POLICY-01 remains nonblocking for D-03 and blocking for D-06 finalization.
- Lifecycle-rights wording is a nonblocking D-02 dependency.
- Channel authentication and handoff assurance are a nonblocking D-04 dependency.
- Pause/termination commercial edge handling is a D-05/D-06 dependency.

No gap blocks D-03 acceptance.

## Learning Record

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-004-01 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-08T11:30:17+00:00 |
| `improvement_signal` | State and identity foundations can close before trial commercial policy when policy-dependent transitions remain explicitly gated. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |

## Clarification Contribution Record

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | CCR-GOAL-005-INST-004-01 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-08T12:20:00+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-01 |
| Decision | R-036 corrections accepted; canonical activation rule reconciled with INST-006 |

## Clarification Learning Record

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-004-02 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-08T12:20:01+00:00 |
| `improvement_signal` | State foundations must state release authority, first-mint timing, retry reuse, and activation uniqueness explicitly. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |