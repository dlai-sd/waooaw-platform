# WC-034 F4 Relationship Workspace Canonical Contracts

## Amendment 5 Order 3 Acceptance Record

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| acceptance_id | ACC-GOAL-005-INST-005-08 |
| authorization_id | GOA-GOAL-005-INST-005-08 |
| authorization_issued_at | 2026-08-11T02:21:49+00:00 |
| accepted_at | 2026-08-11T02:26:15+00:00 |
| acceptance_validity | VALID - accepted_at is strictly later than issuance |
| decision | ACCEPTED |

## Contribution Record

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| record_id | CR-GOAL-005-INST-005-12 |
| record_type | Contribution Record |
| produced_at | 2026-08-11T02:26:15+00:00 |
| authorization_id | GOA-GOAL-005-INST-005-08 |
| acceptance_id | ACC-GOAL-005-INST-005-08 |
| scope | Publish canonical BP public F4 contract, BP-only PR internal contract, private WBE contract, registered DMA adapter private transport, and CE coverage mapping |
| policy_tuple | A,A,B,A,B,A |
| constraints_preserved | R-069 conditions 1-3, distinct BLOCKED and UNAVAILABLE, fail-closed unresolved states, owner truth boundaries, Evidence First, tenant+relationship isolation, Emergency Stop independence |

## Learning Record

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| record_id | LR-GOAL-005-INST-005-03 |
| record_type | Learning Record |
| produced_at | 2026-08-11T02:26:15+00:00 |
| constitutional_discovery | no |
| evolution_triggered | no |
| improvement_signal | Canonical publication is reliable when operation inventory is frozen first, dependency closure is validated mechanically, and private-owner transports keep strict audience-bound identities without leaking provider, ledger, tenant-authority, ranking, or browser-private ingress surfaces. |

## Canonical Contract Set

| Artifact | Version | SHA-256 |
|---|---|---|
| architecture/reference/api-specs/business-platform.openapi.yaml | 1.3.0 | 357c14bb359d15c6318192e9adf94eac0a4f0537626e9910363539e731d9c22e |
| architecture/reference/api-specs/professional-runtime.openapi.yaml | 1.2.0 | a1aba55e7612cf0f8d342eab51f662d68127f4dd5aabaaa6695dc4e418a51f46 |
| architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml | 1.0.0 | 999b6687f7a0e96e6b362ca286805ee4bb44058f0e67e3dad2f928d74d78eaff |
| architecture/reference/api-specs/dma-relationship-outcome-adapter.openapi.yaml | 1.0.0 | 594524da76b4192493dbaf8ea4515f2d9d5c858dbd896c6020ea055e7230b26b |
| architecture/reference/components/relationship-workspace-ce-contract-coverage.md | 1.0.0 | c11bd9e82680fd8173353ded2e029d1b69a115983cd1b9c160e86adc060e9478 |
| architecture/reference/components/relationship-workspace-canonical-contracts.md | 1.0.0 | SELF_REFERENTIAL_USE_EXTERNAL_VALIDATION_HASH |

## Published Files

- architecture/reference/api-specs/business-platform.openapi.yaml
- architecture/reference/api-specs/professional-runtime.openapi.yaml
- architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml
- architecture/reference/api-specs/dma-relationship-outcome-adapter.openapi.yaml
- architecture/reference/components/relationship-workspace-ce-contract-coverage.md
- architecture/reference/components/relationship-workspace-canonical-contracts.md

## Blockers

None in this publication slice.

## Amendment 5 Order 3 Logical Owner Attestation Acceptance Record

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| acceptance_id | ACC-GOAL-005-INST-005-09 |
| authorization_id | GOA-GOAL-005-INST-005-09 |
| authorization_issued_at | 2026-08-11T02:36:29+00:00 |
| accepted_at | 2026-08-11T02:41:33+00:00 |
| acceptance_validity | VALID - accepted_at is strictly later than issuance |
| decision | ACCEPT |

## Amendment 5 Order 3 Logical Owner Attestation Contribution Record

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| record_id | CR-GOAL-005-INST-005-13 |
| record_type | Contribution Record |
| produced_at | 2026-08-11T02:41:33+00:00 |
| authorization_id | GOA-GOAL-005-INST-005-09 |
| acceptance_id | ACC-GOAL-005-INST-005-09 |
| scope | Hash-bound logical owner attestation for fixed BP, PR, WBE, DMA adapter, and CE coverage artifacts at commit 9b126bd |
| no_edit_statement | This is a no-contract-edit attestation. No OpenAPI or CE coverage bytes were modified; decisions are bound to the fixed hashes below. |
| decision | ACCEPT |

## Hash-Bound Fixed Inputs (No Edit)

| Artifact | Version | Expected SHA-256 | Independently computed SHA-256 | Result |
|---|---|---|---|---|
| architecture/reference/api-specs/business-platform.openapi.yaml | 1.3.0 | 357c14bb359d15c6318192e9adf94eac0a4f0537626e9910363539e731d9c22e | 357c14bb359d15c6318192e9adf94eac0a4f0537626e9910363539e731d9c22e | MATCH |
| architecture/reference/api-specs/professional-runtime.openapi.yaml | 1.2.0 | a1aba55e7612cf0f8d342eab51f662d68127f4dd5aabaaa6695dc4e418a51f46 | a1aba55e7612cf0f8d342eab51f662d68127f4dd5aabaaa6695dc4e418a51f46 | MATCH |
| architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml | 1.0.0 | 999b6687f7a0e96e6b362ca286805ee4bb44058f0e67e3dad2f928d74d78eaff | 999b6687f7a0e96e6b362ca286805ee4bb44058f0e67e3dad2f928d74d78eaff | MATCH |
| architecture/reference/api-specs/dma-relationship-outcome-adapter.openapi.yaml | 1.0.0 | 594524da76b4192493dbaf8ea4515f2d9d5c858dbd896c6020ea055e7230b26b | 594524da76b4192493dbaf8ea4515f2d9d5c858dbd896c6020ea055e7230b26b | MATCH |
| architecture/reference/components/relationship-workspace-ce-contract-coverage.md | 1.0.0 | c11bd9e82680fd8173353ded2e029d1b69a115983cd1b9c160e86adc060e9478 | c11bd9e82680fd8173353ded2e029d1b69a115983cd1b9c160e86adc060e9478 | MATCH |

## Owner-By-Owner Attestation Matrix

| Owner surface | Truth / authority boundary accepted | Caller / audience accepted | Required F4 operation inventory accepted | Policy tuple A,A,B,A,B,A effect accepted | Distinct BLOCKED and UNAVAILABLE accepted | Version and reconciliation behavior accepted | Emergency Stop independence accepted | Browser/private-owner transfer absent | Decision |
|---|---|---|---|---|---|---|---|---|---|
| BP public relationship workspace (`business-platform.openapi.yaml` 1.3.0) | BP is sole ordinary public workspace facade; CE constitutional authority retained; WBE/PR/domain truth not re-owned | JWT-authenticated customer to BP only | Exact 14 operations accepted: getRelationshipWorkspace, getRelationshipWorkspaceChanges, getRelationshipPlan, getRelationshipAttention, getRelationshipWork, getRelationshipResults, getRelationshipUsageBudget, getRelationshipRightsControls, submitRelationshipCommand, getRelationshipCommand, listRelationshipEvidence, getRelationshipEvidence, requestRelationshipEvidenceExport, getRelationshipEvidenceExport | Effects remain explicit through typed command, rights, lifecycle, and consequence surfaces with fail-closed unresolved handling | `RelationshipWorkspaceBlocked` and `RelationshipWorkspaceUnavailable` are distinct and preserved | `schemaVersion`, `workspaceVersion`, expected-version checks, command/evidence export reconciliation, and status model retained | Stop remains dedicated independent path; workspace commands do not subsume Stop | No browser path to PR/WBE/CE/domain private owner routes | ACCEPT |
| PR private execution workspace (`professional-runtime.openapi.yaml` 1.2.0) | PR authoritative for internal execution facts only; no public governance truth transfer | BP internal audience for execution APIs; browser/mobile only for dedicated Emergency Stop WebSocket | Exact 3 relationship workspace operations accepted: getRelationshipExecutionProjection, submitRelationshipExecutionControl, getRelationshipExecutionControl | Consequence controls remain policy-gated through BP/CE; PR does not reinterpret tuple | `BLOCKED` and `UNAVAILABLE` outcomes are distinct in projection and control status | `schemaVersion`, `projectionVersion`, expected projection checks, and durable reconciliation statuses retained | Explicitly independent Stop transport and REST fallback remain separate from workspace controls | Internal routes are BP-only; browsers do not access internal PR operations or model providers | ACCEPT |
| WBE private commercial workspace (`wbe-relationship-workspace.openapi.yaml` 1.0.0) | WBE authoritative for commercial truth; BP relays without recomputation | BP-only private service audience; no browser ingress | Exact 3 operations accepted: getRelationshipCommercialProjection, submitRelationshipCommercialCommand, getRelationshipCommercialCommand | Tuple effect is explicitly preserved in contract text for A,A,B,A,B,A | `Blocked` and `Unavailable` are distinct response contracts and status states | `schemaVersion`, `projectionVersion`, expected projection checks, command reconciliation, and status taxonomy retained | No Stop coupling introduced in WBE route; independent Stop boundary unchanged | Private owner boundary preserved; no browser/private transfer | ACCEPT |
| DMA private domain adapter (`dma-relationship-outcome-adapter.openapi.yaml` 1.0.0) | Domain adapter authoritative for domain outcome projection/validation only; BP owns public incorporation | BP-only registered adapter audience | Exact 3 operations accepted: getDomainOutcomeProjection, validateDomainGoalChange, getDomainCommandOutcome | Tuple-compatible domain consequence inputs remain BP/CE-governed without domain-side policy reinterpretation | No collapse of unavailable/blocked semantics into false success | `schemaVersion`, `contractVersion`, `sourceVersion`, expected source version, and command-outcome reconciliation retained | No Stop coupling introduced; independence preserved by not routing Stop through adapter | Domain-neutral private contract only; no browser/private-owner transfer and no DMA-specific leakage into generic workspace | ACCEPT |
| CE coverage mapping (`relationship-workspace-ce-contract-coverage.md` 1.0.0) | CE remains constitutional validation and evidence authority; no owner-route replacement | Internal architectural coverage audience | Required mapping inventory accepted across ValidateAction, EvaluatePolicy, RecordEvidence, GrantAuthorityLicense, RevokeAuthorityLicense, TriggerEmergencyStop | Tuple A,A,B,A,B,A mapped to consequence families and CE RPC coverage | Unavailable/unknown/partial handling remains explicit and fail-closed for governed success claims | No proto/schema drift: no `constitutional_service.proto` change authorized; mapping preserves reconciliation semantics | TriggerEmergencyStop remains explicit and independent from workspace command path | No browser/private-owner transfer in CE mapping scope | ACCEPT |

## Amendment 5 Order 3 Logical Owner Attestation Learning Record

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| record_id | LR-GOAL-005-INST-005-04 |
| record_type | Learning Record |
| produced_at | 2026-08-11T02:41:33+00:00 |
| constitutional_discovery | no |
| evolution_triggered | no |
| improvement_signal | Hash-bound owner attestation remains reliable when verification includes exact version/hash parity, operation-inventory checks per owner surface, explicit BLOCKED/UNAVAILABLE separation, and independent Stop-path confirmation before ACCEPT decisioning. |

## WC-059 R082-01 Architecture Synchronization Amendment - 2026-08-11

### Enterprise Architecture Attestation

| Field | Value |
|---|---|
| institution_id | INST-004 - Enterprise Architect |
| work_contract | WC-059 - AE-01 Contract, Payment, and Exactly-Once Activation |
| finding | R082-01 - Canonical WBE contract attestation is stale |
| amendment_scope | Synchronize the current canonical publication and architecture traceability for the additive WBE paid-activation operation without changing contract bytes or rewriting the historical INST-005 owner attestation |
| authority | WC-059 assigns INST-004 as architecture reviewer; the INST-004 Decision Space permits reference-architecture publication and traceability maintenance for this non-semantic synchronization |
| decision | ATTESTED - current WBE 1.1.0 contract, ADR-046 route grant, and WBE manifest entry are architecturally coherent |
| acceptance_boundary | This amendment is not a new INST-005 logical-owner acceptance, does not extend ACC-GOAL-005-INST-005-09, and does not claim INST-005 acceptance of WBE 1.1.0 |
| review_boundary | R082-01 remediation evidence is complete; independent re-review remains required for finding closure, and R081-03 remains open |

### Historical Preservation

The WBE 1.0.0 rows and exact three-operation owner inventory above remain the historical
hash-bound attestation made at commit `9b126bd`. They are not rewritten and must not be read as
describing the current committed OpenAPI bytes. This amendment records the later additive WC-059
publication only.

### Current Amended WBE Canonical Publication

| Artifact | Version | SHA-256 | Result |
|---|---|---|---|
| architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml | 1.1.0 | b8ace8ccf218e430b61abb979bbd426843ca84b14a6e2adcfe46243aa1122623 | MATCH - independently computed from current bytes |

Exact current operation inventory:

| Operation ID | Method | Route |
|---|---|---|
| `activatePaidRelationship` | POST | `/internal/v1/relationships/{relationshipId}/paid-activation` |
| `getRelationshipCommercialProjection` | GET | `/internal/v1/relationships/{relationshipId}/commercial-projection` |
| `submitRelationshipCommercialCommand` | POST | `/internal/v1/relationships/{relationshipId}/commercial-commands` |
| `getRelationshipCommercialCommand` | GET | `/internal/v1/relationships/{relationshipId}/commercial-commands/{commandId}` |

### Architecture Consistency Evidence

| Check | Result |
|---|---|
| OpenAPI 3.1 parse and validation with repository-approved OpenAPI Generator 7.17.0 | PASS - no validation issues |
| ADR-046 workload route registry | PASS - exact four method, route, and operation tuples; caller is `business-platform`, target is `billing-engine`, contract major is 1 |
| WBE component manifest for paid activation | PASS - exact POST route, BP-only caller, idempotent operation, and `must_not_expose_to_internet: true` |
| BLOCKED and UNAVAILABLE semantics | PASS - distinct reusable responses and distinct command/projection states remain present |
| Emergency Stop independence | PASS - no Stop route or operation is introduced; ADR-046 Section 5.3 remains controlling |
| Browser ingress | PASS - private internal server, `x-internal: true` on all four operations, BP-only registry grants, and no browser authorization surface |
| Architecture-owned WBE 1.0.0 traceability references | PASS - remaining references are confined to the preserved historical attestation above; no current-facing architecture header requires replacement |

### Amendment Effect

For current architecture traceability, the canonical WBE private contract is version 1.1.0 at the
hash and exact four-operation inventory recorded above. The original 1.0.0 publication and
INST-005 acceptance remain valid historical evidence only. This amendment changes no API bytes,
owner semantics, policy tuple, source ownership, implementation, deployment state, or customer-proof
claim.

## WC-059 WBE 1.1.0 Logical Owner Amendment Acceptance - 2026-08-11

### INST-005 Acceptance Record

| Field | Value |
|---|---|
| institution_id | INST-005 - Solution Architect |
| acceptance_id | ACC-GOAL-005-INST-005-10 |
| acceptance_basis | GOAL-005 Amendment 5 Order 3 logical-owner designation and R-083 EA approval |
| accepted_at | 2026-08-11 |
| acceptance_scope | Append-only WBE 1.1.0 contract amendment and exact four-operation inventory |
| decision | ACCEPT |

INST-005 accepts `architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml` version
1.1.0 at SHA-256 `b8ace8ccf218e430b61abb979bbd426843ca84b14a6e2adcfe46243aa1122623`.
This acceptance is hash-bound and does not modify or supersede the historical 1.0.0 acceptance.

Accepted operation inventory:

| Operation ID | Method | Route |
|---|---|---|
| `activatePaidRelationship` | POST | `/internal/v1/relationships/{relationshipId}/paid-activation` |
| `getRelationshipCommercialProjection` | GET | `/internal/v1/relationships/{relationshipId}/commercial-projection` |
| `submitRelationshipCommercialCommand` | POST | `/internal/v1/relationships/{relationshipId}/commercial-commands` |
| `getRelationshipCommercialCommand` | GET | `/internal/v1/relationships/{relationshipId}/commercial-commands/{commandId}` |

The acceptance preserves WBE captured-payment, paid-subscription, and commercial-projection
ownership; BP-only private ingress; ADR-046 mutual TLS and exact delegated-context binding;
idempotent payment-keyed replay; target-owned payment-material rebinding; distinct BLOCKED and
UNAVAILABLE semantics; CE Evidence First obligations; and Emergency Stop independence.

This acceptance closes the INST-005 dependency retained by R-083 and therefore closes R082-01. It
does not authorize live Razorpay or provider activation, credentials, WC-060, deployment, merge,
implementation expansion, or production/customer claims.

