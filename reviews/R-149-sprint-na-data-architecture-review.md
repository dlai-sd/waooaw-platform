# R-149 - Data Architecture Review

## Review Control

| Field | Value |
|---|---|
| Pull request | #520 |
| Office | Data Architect (INST-006) |
| Initial reviewed head | `93ba109fae10b674ee8088622a521d187645767f` |
| Initial disposition | `CHANGES_REQUIRED` |
| Re-reviewed head | `a06026895628b288b33d4e6832417b83a989e6d5` |
| Final disposition | `PASS` |

## Scope

Review of data ownership, tenant isolation, migration/cutover, Billing financial integrity,
idempotency, recovery and lifecycle disposition.

## Initial Findings And Repair Disposition

| Finding | Required correction | Candidate repair |
|---|---|---|
| Principal, ownership, grant and RLS contract was incomplete | Pin NOLOGIN owners, LOGIN/NOBYPASSRLS runtime roles, FORCE RLS, revoked PUBLIC, transaction-local tenant context and PgBouncer reset | Sections 7.2 and 12 require the complete model and negative tests before and after restore |
| Recovery requirements were weakened | Restore 35-day PITR, RPO <= 5 minutes and RTO <= 30 minutes | Sections 12 and 13 require all limits and independent protected-Azure restore proof |
| Sidecar removal lacked dataset-level accounting | Add a CE, BP, Billing and Temporal cutover ledger | Section 9.1 requires owner, source/target, consistency, fence, watermark, rollback and disposition for every dataset |
| Billing transaction did not bind ADR-034 semantics | Make discrepancy/outcome/evidence/halt atomic over the one-paise threshold | Sections 4 and 8 add ADR-034 and the required transaction/release semantics |
| Reconciliation idempotency was underspecified | Pin key scope, serialization, state machine and crash behavior | Section 8.1 defines the canonical key, canonical JSON/SHA-256 digest, states, replay/conflict and crash tests |
| Asset register was too coarse | Expand ownership, access, tenancy, retention/hold, backup, restore and disposition | Sections 6 and 6.1 require a machine-readable, dataset-level register and invariant-specific restore proof |

## Constitutional Boundaries

Uncertain Billing authority, tenant context, cutover state or restore evidence fails closed. Synthetic
data is not discard authority. Source volumes remain retained until rollback and reconciliation
evidence pass.

## Re-review Disposition

The Data Architect verified closure of all six findings at `a0602689` and found no material data
contradiction. The later candidate clarifies cross-environment promotion identity without changing
the accepted data, RLS, cutover, Billing, idempotency or recovery contracts.
