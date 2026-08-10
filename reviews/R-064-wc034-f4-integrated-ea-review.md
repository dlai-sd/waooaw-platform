# R-064 - WC-034 F4 Integrated Enterprise Architecture Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-004-09 |
| `record_type` | Contribution Record |
| `authorization_id` | GOA-GOAL-005-INST-004-08 |
| `acceptance_record` | ACC-GOAL-005-INST-004-08 |
| `reviewed_commit` | `ba5e21081adcad29ef33f820c7a934051604b8fc` |
| `produced_at` | 2026-08-10T14:45:00+00:00 |
| Date | 2026-08-10 |
| Review type | Fresh independent integrated technical review for G-F4-11 |
| **Decision** | **APPROVED WITH CONDITIONS** |

## 1. Independence And Scope

This review was produced in a fresh INST-004 Enterprise Architect context after `ACC-GOAL-005-INST-004-08` at `2026-08-10T14:39:02+00:00`. This context did not author `CR-GOAL-005-INST-004-08` or any reviewed INST-005, INST-006, INST-007, or INST-011 contribution, and did not repair any reviewed artifact.

The reviewer examined the complete WC-034 F4 Orders 1-5 architecture package through commit `ba5e210`. The review covers technical coherence, ownership, dependency closure, public/private boundaries, owner contracts, DMA adapter neutrality, compatibility specification, gate trace, contradiction scan, ADR impact, unresolved risk, and implementation/deployment boundaries. It does not authorize product policy, canonical OpenAPI edits, generated clients, source, tests, implementation, deployment, F5-F8, merge, or self-review.

The unrelated pre-existing modification to `logs/blueprint_assurance_report.json` was not read or changed. The concurrently produced fresh constitutional review R-063 / `CR-GOAL-005-INST-002-06` was treated as independent G-F4-11 evidence and was not modified.

## 2. Executive Determination

The Orders 1-5 package is technically coherent as an architecture and future-evidence specification. It preserves BP as the sole ordinary public governance facade, WBE as sole commercial-truth authority, CE as internal constitutional validation and evidence authority, PR as an internal execution-truth supplier, web as a generated-BP-client consumer, and professional/domain adapters as private semantic contributors. F4 creates no new deployable component.

The package defines exactly fourteen future F4 public BP operations, deterministic typed commands, expected-version and request-hash idempotency, privacy-safe errors, source-relative freshness and provenance, stable BP-owned attention ordering, Evidence First, and explicit partial/unknown reconciliation. No browser route to PR, WBE, CE, adapters, providers, or ledgers is authorized.

Approval is conditional because the Security contract introduces mutually authenticated workload boundaries for BP-to-WBE, BP-to-PR, and BP-to-professional/domain-adapter traffic that are not covered by the accepted ADR set cited as sufficient by the Enterprise Architecture contribution. This is a pre-implementation architecture decision, not a reason to reject the logical ownership model. The condition must be resolved through the authorized ADR process before G-F4-12 implementation authorization can rely on those contracts.

## 3. Findings Ordered By Severity

No CRITICAL defect was found.

### EA-F4-01 - Workload Authentication Exceeds The Accepted ADR Boundary

**Severity:** HIGH if implementation is authorized without resolution

The F4 Security contract requires mutually authenticated BP-to-WBE, BP-to-CE, BP-to-PR, and BP-to-professional/domain-owner calls with independently verified workload identity, audience, delegated purpose, operation, relationship, and version bindings. The accepted architecture baseline does not fully decide how that requirement is realized:

- ADR-007 decides managed cloud mTLS only for BP-to-CE and PR-to-CE and explicitly permits plain gRPC in the isolated development Docker network.
- The existing security architecture lists BP-to-CE and PR-to-CE as the mTLS routes, PR-to-AI as plain HTTP in development/TLS in cloud, and does not decide BP-to-WBE, BP-to-PR, or BP-to-domain-adapter workload authentication.
- ADR-014 governs secret storage and managed identity for Key Vault access; it does not select a service-authentication protocol for these routes.
- `CR-GOAL-005-INST-004-08` states that accepted ADRs cover the F4 refinement and that no new ADR or amendment is required.

The logical requirement is sound, but the ADR-impact conclusion is incomplete. Before any G-F4-12 implementation amendment or owner-contract implementation GOA, INST-013 must route this decision to the authorized architecture process. That process must either amend an accepted ADR or publish an accepted ADR that defines workload identity and mutual authentication for BP-to-WBE, BP-to-PR, and BP-to-domain-adapter traffic across development, CI, and cloud, including credential source, audience validation, rotation, failure behavior, and environment parity. Implementation may not silently generalize ADR-007 or choose a local mechanism.

### EA-F4-02 - Current Control-Plane Status Contains Superseded Statements

**Severity:** MEDIUM

The ordered Contribution Records validly supersede historical candidate-state tables, but current control-plane surfaces still contain statements that can be misread as present gate truth. In particular, the top F4 checkpoint in `constitution/PROJECT_STATE.md` still describes BP/WBE owner routing as blocked before Amendment 3 mapping, Amendment 3 as proposed, and no current F4 GO Authorization, despite completed Orders 1-5 and authorized Order 6. Candidate contract tables also retain pre-authorization `BLOCKED pending` states, although their re-attestation text correctly identifies those tables as historical.

The package remains reviewable because the post-acceptance Contribution Records and Order chronology are explicit and controlling. Before a later implementation amendment is proposed, the authorized project-state owner must reconcile the current checkpoint and publish one unambiguous gate snapshot. Historical candidate tables may remain historical, but they must not be used as current gate evidence.

### EA-F4-03 - WBE `BLOCKED` Outcome Must Be Preserved In The Canonical Internal Contract

**Severity:** MEDIUM

The Solution contract's BP-to-WBE section lists WBE command outcomes as `COMPLETED`, `PENDING`, `REJECTED`, `CONFLICT`, `UNKNOWN`, or `UNAVAILABLE`. The later logical WBE owner contract also requires `BLOCKED` for unresolved Founder policy, commercial authority, lifecycle, assurance, or owner prerequisites. The public command contract already supports `BLOCKED`, and the WBE owner record is the later controlling owner acceptance, so this does not invalidate the package.

The future canonical internal WBE contract and compatibility evidence must include the owner-approved `BLOCKED` outcome distinctly from `REJECTED` and `UNAVAILABLE`. No implementation may collapse unresolved policy into rejection, temporary unavailability, or success.

### EA-F4-04 - PR And Domain Transport Placement Remain Later Owner Dependencies

**Severity:** LOW

The Solution contract deliberately leaves concrete PR contract publication and each domain adapter's transport/deployable placement to later owner work. Amendment 3 validly closes architecture contribution evidence without creating those endpoints, but implementation cannot assume their existence. A later implementation plan must name the PR owner contract and DMA adapter transport/registration dependencies, supported versions, service identity, and executable evidence before dependent Results or Work commands are enabled. Until then, affected families remain `UNAVAILABLE` or `BLOCKED`.

## 4. Integrated Architecture Matrix

| Concern | Determination | Controlling architecture |
|---|---|---|
| Public facade | PASS | BP is the sole ordinary public Relationship Workspace facade; Emergency Stop remains separately governed. |
| Relationship governance | PASS | BP owns Plan, goal, Work, deliverable, approval, schedule, scope, authority, lifecycle, rights, Results composition, evidence mediation, commands, reconciliation, and authoritative attention order. |
| Commercial truth | PASS | WBE alone owns actuals, allowances, budgets, ceilings, forecasts, thresholds, assumptions, validity, pacing choices, and commercial consequences; BP relays without recalculation or a second ledger. |
| Constitutional authority | PASS | CE remains internal validation, authority-licensing, and constitutional-evidence authority; governed success waits for required CE confirmation. |
| Execution truth | PASS WITH LATER DEPENDENCY | PR supplies internal execution facts only; it owns no public governance, authority, Results, rights, attention order, or WBE truth. Concrete F4 PR owner contracts remain later work. |
| Web boundary | PASS | Web uses only the future generated BP public client, performs no tenant selection, ranking, secondary sorting, truth aggregation, or direct private-service access. |
| Domain adapter | PASS WITH PRESERVATION CONDITIONS | The adapter contributes versioned domain semantics and provenance only. BP retains public composition and ordering. DMA details do not enter the generic contract. |
| Deployable topology | PASS | F4 introduces no new deployable component. Adapter placement remains owner-specific and does not create a generic public service. |
| Tenant and relationship isolation | PASS | Tenant authority is server-derived; every projection, cursor, command, item, export, source version, and adapter contribution is independently relationship-authorized. |
| Ordering | PASS | BP supplies the complete authoritative attention sequence and stable ties; no public rank, score, filter, reorder, personalization, or cross-relationship aggregation exists. |
| Evidence and correction | PASS | Pending and recorded evidence remain distinct; correction and dispute preserve append-only constitutional lineage. |
| Commands and reconciliation | PASS | Typed discriminated commands, expected versions, request-hash idempotency, owner-scoped identities, `PARTIAL`/`UNKNOWN`, and no blind retry are aligned. |
| Product composition | PASS WITH POLICY BLOCKS | Relationship context and six mandatory views are retained; `F4-POL-01` through `F4-POL-06` remain fail-closed. |
| ADR impact | CONDITION | Existing ADRs cover BP/web/CE/WBE ownership but not all newly mandated workload-authentication routes; EA-F4-01 must be resolved before implementation authority. |

## 5. Exact Fourteen-Operation Verification

The Solution contract and compatibility specification contain the same exact future public F4 inventory under `/api/v1/employment/relationships/{relationshipId}/workspace`:

1. `getRelationshipWorkspace`
2. `getRelationshipWorkspaceChanges`
3. `getRelationshipPlan`
4. `getRelationshipAttention`
5. `getRelationshipWork`
6. `getRelationshipResults`
7. `getRelationshipUsageBudget`
8. `getRelationshipRightsControls`
9. `submitRelationshipCommand`
10. `getRelationshipCommand`
11. `listRelationshipEvidence`
12. `getRelationshipEvidence`
13. `requestRelationshipEvidenceExport`
14. `getRelationshipEvidenceExport`

The inventory contains no public tenant-authority field, generic action or proxy, arbitrary callback or service destination, ranking/reordering operation, private owner operation, ledger operation, provider operation, or workspace Emergency Stop replacement. The compatibility specification requires inventory equality, unique operation IDs, dependency-closed schemas, required idempotency on both POST operations, RFC 9457 errors, strict TypeScript, deterministic two-run generation, and no manual patch.

## 6. Gate Determination

| Gate | Integrated review state | Evidence or condition |
|---|---|---|
| G-F4-01 | CONTRIBUTION SATISFIED | `CR-GOAL-005-INST-003-04` |
| G-F4-02 | CONTRIBUTION SATISFIED | `CR-GOAL-005-INST-004-08` |
| G-F4-03 | CONTRIBUTION SATISFIED WITH REVIEW CONDITION | `CR-GOAL-005-INST-005-05`; EA-F4-01 and EA-F4-03 govern later canonicalization/implementation. |
| G-F4-04 | CONTRIBUTION SATISFIED | `CR-GOAL-005-INST-006-04` |
| G-F4-05 | CONTRIBUTION SATISFIED WITH REVIEW CONDITION | `CR-GOAL-005-INST-007-05`; workload-authentication ADR coverage must be resolved before implementation. |
| G-F4-06 | CONTRIBUTION SATISFIED WITH POLICY BLOCKS | `CR-GOAL-005-INST-011-05`; `F4-POL-01` through `F4-POL-06` remain unresolved and fail-closed. |
| G-F4-07 | LOGICAL OWNER CONTRIBUTION SATISFIED | `CR-GOAL-005-INST-005-06`; accepted as future BP contract ownership, not a canonical OpenAPI or endpoint. |
| G-F4-08 | LOGICAL OWNER CONTRIBUTION SATISFIED WITH REVIEW CONDITION | `CR-GOAL-005-INST-005-07`; preserve `BLOCKED` and resolve workload authentication before implementation. |
| G-F4-09 | CONTRIBUTION SATISFIED WITH PRESERVATION CONDITIONS | Ordered chain `CR-GOAL-005-INST-011-06` -> `CR-GOAL-005-INST-003-05` -> `CR-GOAL-005-INST-005-08`. |
| G-F4-10 | SPECIFICATION CONTRIBUTION SATISFIED; EXECUTABLE CLOSURE OPEN/BLOCKED | `CR-GOAL-005-INST-005-09` defines future evidence only; no canonical OpenAPI, generated client, compile, hashes, fixtures, live integration, or browser evidence exists. |
| G-F4-11 | REVIEW CONTRIBUTIONS COMPLETE; CONDITIONAL PACKAGE APPROVAL | R-063 / `CR-GOAL-005-INST-002-06` supplies the fresh constitutional review. This R-064 / `CR-GOAL-005-INST-004-09` supplies the fresh integrated technical review. Conditions in both reviews remain mandatory. |

G-F4-12 implementation authorization remains **OPEN/BLOCKED**. It requires a later Execution Plan amendment, fresh CA readiness, Registrant acknowledgement, valid GOA issuance, valid INST-010 acceptance, and satisfaction or explicit gate placement of the review conditions above. G-F4-13 deployment remains **OPEN/BLOCKED** under separate release authority. F5-F8 remain **EXCLUDED**.

## 7. Unresolved-Risk Statement

1. Workload-authentication protocol and environment behavior for BP-to-WBE, BP-to-PR, and BP-to-domain-adapter traffic are not covered by an accepted ADR. EA-F4-01 is a mandatory pre-implementation condition.
2. `F4-POL-01` through `F4-POL-06` remain unresolved. Affected commands and consequences must remain `BLOCKED` or `UNAVAILABLE`; no owner, implementer, or reviewer may choose a default.
3. Executable G-F4-10 remains unproven. The fourteen operations and their schema closure have not been added to canonical BP OpenAPI, generated, compiled, fixture-tested, or scanned.
4. Current project-state text contains superseded gate assertions. The ordered Contribution Records control, but the checkpoint must be reconciled before later authorization uses it as a current-status source.
5. The future WBE internal contract must preserve `BLOCKED` distinctly, and concrete PR/DMA adapter owner contracts remain later dependencies.
6. DMA v3.1 is not represented as having current-version Founder approval or customer proof. Provider execution, enquiry-to-booking attribution, normalized cross-channel evidence, and customer-funded campaign outcomes remain unproven.
7. No F4 implementation, live integration, browser, deployment, production, or customer-proof evidence exists. Architecture and evidence specification must not be relabelled as runtime assurance.

## 8. Decision And Exact Conditions

**APPROVED WITH CONDITIONS.** The WC-034 F4 Orders 1-5 package through commit `ba5e210` is accepted as an integrated architecture and future-evidence specification. This record completes the fresh INST-004 technical-review contribution required by G-F4-11. Together with R-063 / `CR-GOAL-005-INST-002-06`, both independent review contributions are present, and G-F4-11 has **CONDITIONAL PACKAGE APPROVAL** subject to all conditions in both reviews.

The exact technical conditions are:

1. Before G-F4-12 implementation authorization may rely on the F4 internal contracts, the authorized ADR process must decide workload identity and mutual authentication for BP-to-WBE, BP-to-PR, and BP-to-domain-adapter traffic across development, CI, and cloud. No implementation context may silently extend ADR-007.
2. Before canonical internal WBE contract implementation, `BLOCKED` must be retained as a distinct owner outcome for unresolved policy or authority prerequisites.
3. Before a later implementation amendment is proposed, the authorized project-state owner must reconcile superseded F4 checkpoint statements and publish an unambiguous current gate snapshot.
4. `F4-POL-01` through `F4-POL-06` remain fail-closed until prospectively resolved by the Registrant/Founder and accountable owner. Review approval supplies no policy default.
5. Executable G-F4-10 remains open and blocked until a separately authorized contribution produces the canonical contract and complete passing evidence manifest defined by `CR-GOAL-005-INST-005-09`.

This decision does not authorize canonical OpenAPI changes, generated clients, source, tests, migrations, builds, provider activation, implementation, deployment, F5-F8, merge, production operation, or customer proof.