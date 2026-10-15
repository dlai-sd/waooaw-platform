# CB-019 - WC-123 Web Session Database Route

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-019` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-15` |
| Status | **CLOSED — 2026-10-15** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-123 runtime configuration repair R1-R3 and dependent validation/PR delivery |
| Constitutional basis | C-023, C-059, C-063, C-080; CSA-AUTH-001 Sections 12.7-12.8; WC-123 Sections 2.2, 7.2, 7.3, 12, and 15 |
| Resolution authority | Chief Solution Architect and Chief Platform Architect for one accepted application PostgreSQL/PgBouncer route; Founder for amended implementation authority |

## Blocking Facts

The failed Demo revision proved that `WAOOAW_SERVER_SESSION_MODE` is absent from the phase-2 Web
runtime environment. Adding that one value cannot complete or safely activate WC-123:

1. `web/app/api/health/ready/route.ts` requires the Web session store, configuration digests,
   identity edge, and Business Platform to be ready.
2. `web/lib/web-session-store.ts` requires `WEB_SESSION_DATABASE_URL`, three structured keyrings,
   their active write versions, and the accepted schema/deploy version.
3. The closed-world secret catalog declares those dependencies, but the current credential seeder
   creates one generic random string for every platform-generated secret. That output is not a
   versioned keyring and cannot be a private PgBouncer connection URL.
4. The active phase-2 Demo workload deploys PostgreSQL as replica-local sidecars for selected
   Container Apps. Web has no PostgreSQL sidecar and no route to another app's sidecar.
5. The active phase-2 UAT root likewise supplies no accepted Web-reachable PgBouncer/application
   PostgreSQL endpoint.
6. The older `infrastructure/terraform/modules/core` root contains a PgBouncer resource, but it is
   not the active phase-2 environment topology and uses a different database/foundation contract.
   Reintroducing or copying it would be an unaccepted topology decision.

## Contract Conflict

CSA-AUTH-001 Sections 12.7-12.8 and WC-123 require the existing application PostgreSQL boundary,
private TLS, hostname/certificate verification, PgBouncer transaction pooling, the restricted
`web_session_app` role, and no direct/public fallback. WC-123 also prohibits a new deployable,
database service, image-baked environment value, placeholder secret, or invented route.

The active phase-2 implementation therefore lacks a required accepted input. A random database
secret, direct sidecar address, new PgBouncer Container App, duplicated PostgreSQL sidecar, or
disabled readiness check would compensate for the missing contract and violate the Work Contract.

## Gate Effect

- Runtime repair R1 cannot be completed truthfully.
- Dedicated liveness/readiness probes R2 cannot be qualified against the mandatory session-store
  dependency.
- Cross-artifact and final-image gates R3 cannot define a passing environment-shaped contract.
- Docker completion, author review, and Founder-ready PR delivery remain blocked.
- No Terraform, workflow, Web, secret, provider, cloud, deployment, traffic, or activation change
  has been made.

## Required Resolution

1. Accept one exact phase-2 Demo and UAT application PostgreSQL/PgBouncer route satisfying
   CSA-AUTH-001 Sections 12.7-12.8, including ownership, private DNS/TLS, certificate trust,
   lifecycle, rollback, capacity, and environment isolation.
2. Bind `WEB_SESSION_DATABASE_URL` construction to that accepted route without exposing its value
   to Terraform state, workflow inputs/outputs, logs, or retained evidence.
3. Define purpose-specific platform generation for the three versioned keyring secrets and their
   write-version identifiers; generic random-string generation is insufficient.
4. Amend the exact WC-123 impact manifest and implementation paths if the accepted resolution adds
   or changes a deployable, dependency, Terraform root, migration path, or rollback boundary.
5. Re-authorize implementation against the amended accepted package.

Until those inputs exist, only independently bounded diagnostic-evidence work may proceed, and no
partial repair may be represented as WC-123 completion.

## Resolution And Closure Evidence

The Founder accepted CSA-AUTH-001 Section 12.7.1 and the matching environment-readiness and Azure
topology amendments on 2026-10-15:

- Demo uses one digest-pinned disposable PostgreSQL/PgBouncer dependency Container App and wipes
  its `EmptyDir` data on every deployment.
- UAT uses persistent private Azure Database for PostgreSQL Flexible Server with a dedicated
  private PgBouncer dependency, 35-day PITR, sanitized restore, RPO <= 5 minutes, and RTO <= 30
  minutes.
- Production uses a separate highly available PostgreSQL boundary under separate authority.
- Database URLs and structured keyrings are owned by `wc123-no-echo-provisioner`; the generic
  deployment seeder cannot create or overwrite them.

Platform IT implemented the safe migration-state boundary: every active phase-2 root explicitly
selects `disabled`; `shadow` or `enforced` requires the complete independent digest, write-version,
secret-reference, and readiness contract. Therefore the missing-architecture-input blocker is
closed without claiming session-authority activation. Demo/UAT database resources, private route,
no-echo credential execution, qualification, cloud apply, traffic, and Production activation remain
separately gated.
