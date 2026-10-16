# R-151 - Platform Architecture Review

## Review Control

| Field | Value |
|---|---|
| Pull request | #520 |
| Office | Platform Architect (INST-009) |
| Initial reviewed head | `93ba109fae10b674ee8088622a521d187645767f` |
| Initial disposition | `CHANGES_REQUIRED` |
| Re-reviewed head | `a06026895628b288b33d4e6832417b83a989e6d5` |
| Re-review disposition | `CHANGES_REQUIRED` |
| Follow-up repair | Work Component `1.1.0-candidate.2`; exact-head author verification required |

## Scope

Review of executable lifecycle orchestration, platform dependencies, runner/state prerequisites,
promotion, recovery, capacity, observability and full-tuple rollback.

## Initial Findings And Repair Disposition

| Finding | Required correction | Candidate repair |
|---|---|---|
| Lifecycle truth depended on stoppable infrastructure and lacked recovery/concurrency semantics | Define durable external state, legal transitions, operation identity, lock, resume and reconciler | Section 9.4 stores signed control state outside PostgreSQL and pins transitions, locks, retries, resume, schedule, authority and alert behavior |
| Demo and UAT Temporal behavior was conflated | Keep Demo self-hosted Temporal and UAT Temporal Cloud mTLS separate | Section 11 step 8 explicitly separates start versus verify-only behavior |
| ADR-047 prerequisites were omitted | Pin private runner, OIDC, backend isolation/locking/ownership, imports and drift/partial-apply handling | Section 9.2 and PST-WC09A make these blocking prerequisites |
| UAT promotion could drift from Demo acceptance | Promote identical application/schema/migration identity while separately qualifying required environment differences | Sections 11 and 13 bind Founder-accepted Demo application/schema/migration identity to UAT's independently authorized configuration/dependency manifest |
| Local recovery simulation could be mistaken for Azure qualification | Separate Docker logic proof from authorized private Azure PITR | Section 14 defines the protected provider restore phase and independent evidence |
| Accepted capacity limits were absent | Bind PostgreSQL 40/100, PgBouncer 40/80 and <=80% aggregate use | Section 12 makes all limits and full member accounting blocking |
| Sleep/restart operations lacked owned alerts | Add lifecycle observability catalogue and operations ownership | Section 16.1 pins required signals and preserves bounded alert-receiver authority |
| Rollback did not bind the complete tuple or Terraform partial apply | Pin application/config/dependency/schema identity, prior retention and roll-forward reconciliation | Section 19 defines complete-tuple rollback, retention and `RECOVERY_HOLD` partial-apply handling |

## Constitutional Boundaries

`deploy.yaml` remains the single mutation entry. The scheduled path is observe/alert by default and
may re-stop only under the still-valid original authority. Production remains out of scope.

## Re-review Findings And Follow-up Repair

The re-review closed six findings and identified two contradictions: the candidate required
identical Demo/UAT configuration/dependency tuples despite the accepted Temporal split, and rollback
omitted migration identity.

Candidate 2 promotes immutable application/schema/migration identity while independently
authorizing each environment's provider/configuration/dependency tuple. It also binds rollback to
the migration digest/watermark and secret-catalog digest. The Chief Solution Architect exact-head
author review must verify these repairs before submission.
