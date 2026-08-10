# GOAL-005 F4 Workload Identity And Service Authentication Learning

## G-10 Attestation

| Attestation field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-004-06 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-10T15:50:17+00:00 |
| `authorization_id` | [GOA-GOAL-005-INST-004-09](GOAL-005-execution-plan.md#goa-goal-005-inst-004-09) |
| `acceptance_record` | [ACC-GOAL-005-INST-004-09](GOAL-005-execution-plan.md#acc-goal-005-inst-004-09) at 2026-08-10T15:10:37+00:00 |
| Contribution | [CR-GOAL-005-INST-004-10](GOAL-005-f4-workload-identity-contribution.md) |
| Architecture decision | [ADR-046](../adr/ADR-046-workload-identity-and-service-authentication.md) - PROPOSED |
| `improvement_signal` | Architecture reviews must test every newly introduced private caller-target route against accepted ADR route scope and all required environments; network encryption, secret custody, delegated context, constitutional authorization, and workload identity are separate concerns and must not be inferred from one another. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |

## 1. Discovery And Evolution Rationale

`constitutional_discovery` is **no** because Order 1 found an architecture coverage gap, not a new constitutional principle or contradiction in ratified claims. Existing C-003, C-006, C-023, C-026, C-031, C-032, C-063, and the Security by Design obligations already require authenticated, bounded, privacy-safe service behavior. No CD record is warranted by this contribution.

`evolution_triggered` is **no** because the gap can be resolved within INST-004's existing Decision Space through a new proposed ADR and the already authorized independent review sequence. No WIOM Stage W-5 institutional evolution, charter change, new Institution, or new constitutional mechanism is required. If independent reviewers identify a claim conflict or an institutional capability gap, they must raise that prospectively in their own authorized records; this Learning Record does not pre-judge that outcome.

## 2. Reusable Learning

The reusable architecture-review rule is:

> For every new private integration, enumerate caller, target, environment, trust root, exact workload identity, intended audience, delegated context, target rebinding, operation policy, credential lifecycle, failure behavior, and executable evidence. An accepted ADR for a different route or environment is not coverage by analogy.

This rule should be applied before an integrated architecture package states that no ADR impact exists. In particular:

- mTLS proves peer possession of an asymmetric identity; it does not by itself grant operation, tenant, relationship, or constitutional authority;
- a signed delegation envelope preserves provenance and request binding; it is not independently authoritative and must be rebound to the authenticated caller and target-owned truth;
- secret storage decides custody, not identity semantics;
- environment parity means the same security properties and policy behavior, not necessarily the same issuer implementation;
- CE remains the constitutional authority but must not become a circular dependency for service authentication; and
- Emergency Stop independence must be tested whenever a new trust or availability dependency is introduced near PR or CE paths.

## 3. Rejected Shortcuts

The following shortcuts were attractive because they reduce local setup or reuse existing artifacts, but they are not acceptable:

| Shortcut | Reusable rejection reason |
|---|---|
| Shared HMAC in dev/CI | Exercises a different identity and compromise model from cloud and cannot prove a unique asymmetric workload. |
| Trust the Docker/CI network and use plaintext | Tests neither mutual identity nor audience/route policy and allows environment-only bypass behavior. |
| Accept tenant or relationship headers from the caller | Converts untrusted input into authority and enables confused-deputy and cross-tenant failures. |
| Match certificate CN or a broad SAN pattern | Confuses certificate possession with exact workload, trust-domain, audience, and operation authorization. |
| Ask CE to authenticate each service request | Creates a circular availability dependency and conflates transport identity with constitutional authorization. |
| Store a root or shared service credential in a developer password manager | Makes trust depend on manual human ceremony, cannot reproduce CI identity, and weakens issuance and rotation evidence. |
| Reuse one root or certificate across environments/workloads | Expands compromise blast radius and defeats ADR-014 environment isolation. |
| Treat a signed delegated envelope as a bearer capability | Permits replay and cross-target use unless it is rebound to mTLS caller, audience, route, body, tenant, relationship, and target truth. |
| Silently generalize ADR-007 | Changes an accepted decision's route and environment scope without authorization or review. |

## 4. Process Improvement

Future integrated reviews should include a route-to-ADR coverage matrix before declaring the ADR impact complete. Each row should name:

1. caller and target;
2. protocol and every required environment;
3. identity issuer and trust root;
4. caller identity, target audience, and allowed operation;
5. delegated authority/context source and target rebinding;
6. rotation, revocation, expiry, and compromise behavior;
7. fail-closed, privacy, observability, replay, idempotency, and Stop behavior; and
8. the exact accepted ADR section that decides those properties.

A blank cell is a decision gap, not an implementation detail. It must be routed before implementation authorization rather than filled by a developer, test harness, deployment manifest, or local convention.

## 5. Follow-Up Owner

| Follow-up | Accountable owner | Boundary |
|---|---|---|
| Independent business-driver and capability review | INST-003 under a later valid Amendment 4 Order 2 GOA and Acceptance Record | Review only; may not edit ADR-046 or authorize implementation |
| Fresh constitutional and claim-traceability review | A fresh INST-002 context under a later valid Amendment 4 Order 3 GOA and Acceptance Record | Must be distinct from R-065; review only; may not repair ADR-046 |
| ADR status and EA-F4-01 checkpoint after approvals | INST-013 | Mechanical verification and recording only; no authorship, repair, or acceptance vote |
| Future internal contract and executable evidence planning | INST-005 and INST-007, routed prospectively by INST-013 | Must preserve ADR-046 if accepted, owner boundaries, policy blocks, and evidence specification; no work begins from this Learning Record |
| Future implementation contribution | INST-010 only after a separate amendment, fresh CA readiness, exact Registrant acknowledgement, GOA, and acceptance | No implementation, provider activation, or deployment authority exists now |

The immediate next step is independent review, not implementation. ADR-046 remains `PROPOSED`, and this Learning Record does not trigger or authorize downstream execution.