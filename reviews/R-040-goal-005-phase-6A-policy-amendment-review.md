# R-040 — GOAL-005 Phase 6A Trial-Policy Amendment Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | R-040 |
| `record_type` | Clearance Record |
| `produced_at` | 2026-08-08T12:31:00+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-05 |
| Decision | **CLEAR** |

## Review

INST-004 independently reviewed `GOAL-005-D06-product-attestation.md`, the amended G5-TRIAL-POLICY-01 duration, and the controlling D-02, D-03, and D-04 foundations.

The change from “14 calendar days or 3 sessions” to “14 calendar days” is a product entitlement decision. It does not add a lifecycle state, change ownership of the Employment Relationship, alter the four-part activation tuple, grant consequential trial authority, weaken evidence or Emergency Stop, redefine channel continuity, or require an architecture decision.

The existing implementation contains a 48-hour reminder and trial-expiry behavior. D-06 Work Contracts must reconcile those behaviors with customer-initiated conversion and the prohibition on pressure; this is implementation grooming, not an architecture change.

## Conditions Carried to D-06

1. Trial expiry may stop new trial activity but must preserve evidence access, customer-owned approved artifacts, termination, and Emergency Stop.
2. Reminder behavior must be informational, bounded, and non-converting.
3. No implementation contract may recreate completed WC-031 through WC-043 foundations without a proven gap.
4. Simulation must cover inactivity, expiry, replay, and attempted direct trial-to-`ACTIVE` transition.

## Decision

The Product Owner attestation and duration amendment are accepted. CB-003 may close and full D-06 specialist authorizations may issue. No implementation is authorized.