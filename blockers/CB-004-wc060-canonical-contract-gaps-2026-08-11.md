# CB-004 — WC-060 Canonical Contract Gaps

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | CB-004 |
| `record_type` | Clearance Record |
| `produced_at` | 2026-08-11T16:31:33Z |
| Status | **RESOLVED — WC-060 SPECIFICATION READY; IMPLEMENTATION UNAUTHORIZED** |
| Raised by | INST-013 — Goal Orchestrator |
| Evidence baseline | `origin/main` at `0eed497`; includes WC-059 merge `b0dbe9c` and PROJECT_STATE v2 merge `c42a239` |

## Blocker

A fresh WC-060 grooming and dependency audit cannot confirm that all canonical
contracts are complete or that all nine tasks can execute without architecture
invention.

1. ADR-002 makes `architecture/reference/api-specs/business-platform.openapi.yaml`
   the source of truth and requires every endpoint to exist there before
   implementation. The approved D-06 Solution Contract names the two handoff
   operations and the Neutral Continuity Envelope, but the canonical BP OpenAPI
   contains no handoff paths or continuity-envelope schema.
2. WC060-05 and R-074 require BP to query CE/Audit Sink through an approved
   read contract. The BP component contract describes a read-only CE gRPC call,
   but `architecture/reference/proto/constitutional_service.proto` and the CE
   component contract expose no evidence-read or evidence-export RPC. ADR-001
   requires CE service-to-service contracts to be defined in protobuf.
3. The D-06 Data Contract defines Migration 22 table purposes and field families,
   but not an exact executable blueprint for primary keys, foreign keys, field
   types/nullability, checkpoint and acknowledgement state constraints,
   uniqueness/idempotency constraints, Migration 22 indexes, or deterministic
   retention/expiry behavior. WC060-01 calls for the "exact Migration 22
   blueprint" and R-074 claims these controls are complete; the merged contract
   does not yet make those choices mechanical.

These are specification gaps, not WC-060 implementation deliverables. INST-010
cannot choose the missing wire and persistence contracts without entering
INST-005/INST-006 Decision Space.

## Evidence Preserved As Ready

- WC-059 is DONE and PR #265 merged as `b0dbe9c`.
- FA-037, Amendment 6, and R-073/R-074/R-075 are present and preserve the
  authorization boundary.
- WC060-02, WC060-04, WC060-06, WC060-07, and the behavioral portions of
  WC060-08 have approved security, identity, routing, Stop, and replay semantics.
- UX-CONV-03, UX-RES-02, and UX-CONT-01 through UX-CONT-06 have explicit pass
  conditions in the hybrid UI acceptance contract.
- The proportional F8 categories, C-076 coverage floor, Docker runners, web
  scripts, and independent INST-007/INST-006/INST-004 implementation-review
  sequence are defined and executable once the canonical contracts close.
- WC-060-specific CCT and browser test files do not yet exist by design; creating
  them is WC060-08/WC060-09 implementation scope, not a harness blocker.

## Required Resolution Evidence

1. INST-005 publishes and independently reviews a spec-first BP OpenAPI update
   containing the handoff operations, Neutral Continuity Envelope, request and
   response schemas, security, idempotency, versioning, and privacy-safe error
   outcomes required by D-06 and WC-060.
2. INST-005 publishes and independently reviews the CE/Audit Sink protobuf read
   contract required by the Evidence Reader, including tenant, relationship,
   participant-role, pagination/export, payload-reference, erasure, and
   privacy-safe failure semantics; INST-007 confirms the access boundary.
3. INST-006 publishes and independently reviews the complete Migration 22
   executable data contract, including keys, types, constraints, forced RLS,
   append-only protections, indexes, replay uniqueness, legal retention, and
   expiry semantics.
4. INST-004 performs a fresh integrated architecture review confirming that the
   repaired BP, CE, security, and data contracts are mutually consistent and
   require no INST-010 architecture decision.
5. INST-002 performs fresh CA readiness review only after items 1 through 4 are
   merged and current.

## Gate Effect

- WC-060 grooming: **BLOCKED**.
- GEP-GOAL-005-INST-013-09: not produced while its implementation inputs are
  incomplete.
- Fresh INST-002 CA readiness: not requested prematurely.
- Registrant acknowledgement statement: not issued because there is no
  CA-ready execution plan to acknowledge.
- GOA-GOAL-005-INST-010-06 and INST-010 Goal Acceptance: not issued.
- Implementation, migrations, generated production clients, provider activation,
  deployment, merge, and F6-F8 feature work remain unauthorized.

## Resolution — 2026-08-11

All required resolution evidence is present in the readiness branch:

1. BP OpenAPI v1.7.0 defines both handoff operations, the signed Neutral Continuity
  Envelope, aligned binding/checkpoint states, role-filtered Evidence Reader behavior,
  deterministic JSON export, erased-payload behavior, and privacy-safe outcomes.
2. CE protobuf defines `QueryEvidenceRecords` with tenant-metadata-only scope, opaque
  authorized evidence IDs, bounded pagination, erased-payload metadata, and no payload,
  credential, prompt, policy, or storage-coordinate disclosure.
3. The D-06 Migration 22 contract fixes exact columns, types, keys, valid composite foreign
  keys, checks, unique indexes, forced RLS, transition and append-only triggers, 15-minute
  checkpoint expiry, 48-hour deduplication retention, maintenance authority, and replay rules.
4. Fresh independent INST-005, INST-006, and INST-007 reviews approved their respective
  integration, data, and security boundaries. INST-004 then approved the integrated package
  after explicit HMAC adversarial CCT, evidence-export, and erased-payload clarifications.
5. Fresh INST-002 review declared the package constitutionally ready and confirmed this
  blocker may close while implementation authority remains absent.

CB-004 is therefore closed as a specification blocker. Amendment 9 may proceed to formal CA
readiness review and future Registrant acknowledgement. Closing this blocker does not issue
`GOA-GOAL-005-INST-010-06`, create `ACC-GOAL-005-INST-010-06`, satisfy the required future
Founder session directive, or authorize implementation, migration execution, generated
production clients, provider activation, deployment, PR merge, self-review, or F6-F8 work.