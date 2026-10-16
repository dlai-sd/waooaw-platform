# CB-020 - WC-124 Persistent-State Implementation Inputs

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-020` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-16` |
| Status | **CLOSED — OWNER INPUT GATE RESOLVED 2026-10-16** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | Issue #521 / WC-124 / PST-WC00 through PST-WC14 |
| Constitutional basis | C-023, C-032, C-059, C-063, C-080; FA-055; Work Component sections 2, 5 and 20 |
| Resolution authority | Founder plus the named owning architecture/data/security/platform authorities |

## Blocking Facts

Issue #521 supplies explicit current-session implementation authority and Release Qualification OFF.
It does not authorize provider action. The accepted Work Component also makes the following values
mandatory Work Contract inputs and orders INST-010 to stop rather than select them.

The accepted sources establish persistent private Demo/UAT PostgreSQL, dedicated PgBouncer, retained
data during sleep, exact recovery/capacity thresholds and the separate provider-action boundary.
At blocker creation they did not pin all values required before implementation:

1. exact Demo and UAT PostgreSQL SKU, storage, autogrow and availability posture;
2. exact per-environment monthly estimate and owner-approved reserve under FA-052;
3. accepted PostgreSQL and AzureRM/provider versions for the new phase-2 foundation resources;
4. PgBouncer image digest, CPU/memory allocation, server limits and exact timeout set;
5. complete database/schema/NOLOGIN-owner/runtime-reader-writer/migration-role inventory for
   Keycloak, Demo Temporal, CE, BP, PR, AIR, Billing and Web sessions;
6. exact Entra bootstrap identity and generated non-admin credential handoff;
7. existing Billing Redis halt/audit cutover treatment, initial post-cutover authority state and
   mandatory reconciliation;
8. exact migration order, previous-release compatibility window, sleep lease, automatic-restart
   reconciliation interval and activation timeout;
9. accepted sanitized restore fixture and exact backup/PITR qualification inputs;
10. immutable Demo and UAT authorization tuples, including protected environment, OIDC
    subject/audience, tenant/subscription/resource group, backend key, runner identity, release,
    plan, secret-catalog, lease and expiry values;
11. accepted canonical secret catalogue and separate bootstrap, migration, workload, deployment and
    verification principals;
12. dataset-level CE/BP/Billing/Demo-Temporal cutover decisions, including any synthetic-data discard
    authority;
13. accepted live evidence of ADR-047 runner/state ownership, environment backend isolation and
    Storage-account separation, or a separately bounded prerequisite delivery;
14. lifecycle-control signing identities, scheduled reconciliation mutation authority, alert owner
    and exact signal retention; and
15. UAT promotion evidence binding the Founder-accepted Demo application/schema/migration identity
    to the UAT dependency manifest.

Legacy `infrastructure/terraform/environments/dev` values, local Compose defaults and currently
deployed repository configuration are evidence of the current gap. They are not accepted WC-124
inputs and cannot be promoted into authority by INST-010.

## Evidence

- Process control `wc100-r033-v1`: all declared source digests PASS.
- Selected branch: `ib/124/persistent-state-lifecycle`.
- Intake HEAD and `origin/main`: `5a849683abec38ebb6d9d72b37b211d8a3376806`.
- `origin/main` ancestry: PASS.
- Static no-build preflight: PASS.
- Docker requirement-ledger validation: PASS, 34 requirements.
- Accepted topology states only environment-specific low-cost capacity and permits Demo to use the
  lowest qualified capacity; the later Work Component requires the Work Contract to pin the exact
  values and prohibits the implementer from selecting them.

## Required Resolution

Resolve this blocker by one of these authority-preserving paths:

1. amend issue #521/WC-124 with the exact accepted values and evidence listed above; or
2. authorize the owning architecture/data/security/platform authorities to produce and accept one
   bounded WC-124 input package, then bind its complete digest into the Work Contract and ledger.

Provider authorization remains separate. Resolving this blocker does not authorize any real Azure
query, plan/apply, deployment, restore qualification, DNS, traffic admission, activation,
Production action, approval or merge.

## Bounded Owner Input Package - 2026-10-16

The Founder-authorized integrated INST-009/INST-006/INST-007 owner pass produced
`work-contracts/WC-124-persistent-state-inputs.yaml`. For every item it records the exact selected
value or closed generated-evidence contract, deciding owners, rationale, source constraints,
acceptance statement, rollback/stop condition and package evidence. It does not promote legacy
implementation defaults or fabricate provider-derived values. Its complete SHA-256 is
`210b18e540c60dc7a0b530b7ca7220e5c5468067a4fa3cebccfece1b9232604c`.

| Item | Status | Exact result |
|---|---|---|
| 1 PostgreSQL sizing | RESOLVED | Demo/UAT `B_Standard_B1ms`, 32 GiB, autogrow disabled, single-zone/no-HA; connection limits 40/100 |
| 2 cost/reserve | RESOLVED | Demo INR 1,100; UAT INR 1,600; combined INR 2,700; owner reserve INR 3,200/month before GST |
| 3 platform versions | RESOLVED | PostgreSQL 16; Terraform 1.9.8; AzureRM 4.14.0 |
| 4 PgBouncer | RESOLVED | `docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9`; exact resources/limits/timeouts accepted |
| 5 data/role inventory | RESOLVED | Eight row-complete database/schema/table-family inventories with NOLOGIN owners and separated migration/runtime/read roles |
| 6 bootstrap/handoff | RESOLVED | Exact environment bootstrap identity names, generated role list, no-echo Key Vault version handoff and pre-activation revocation |
| 7 Billing cutover | RESOLVED | `RECONCILIATION_REQUIRED` initial state; existing halt preserved; exact fail-closed reconciliation mapping |
| 8 order/timing | RESOLVED | Exact migration/activation order, 24-hour compatibility/lease, five-minute restart reconciliation and 20-minute activation timeout |
| 9 recovery fixture | RESOLVED | Existing synthetic fixture schema plus exact Demo/UAT deterministic generation and live PITR qualification contract |
| 10 authorization tuples | RESOLVED | Static Demo/UAT tuples pinned; provider-operation values are closed generated runtime bindings; current apply authority is none |
| 11 secret/principals | RESOLVED | Exact catalog additions, separated principal patterns and canonical digest generation/binding contract |
| 12 dataset cutover | RESOLVED | CE/BP/Billing/Demo-Temporal preserve-and-reconcile ledger; no discard or deletion authority |
| 13 runner/state evidence | RESOLVED | PST-WC09A exact prerequisite exit contract accepted; live evidence explicitly not yet proven; PST-WC04 remains dependent |
| 14 lifecycle control | RESOLVED | Exact writer/verifier/scheduler identities, sole scheduled mutation, Platform Operations owner and per-signal retention |
| 15 UAT promotion | RESOLVED | Exact generated digest/signature/equality gate; current Founder Demo and UAT acceptance remain none |

**Disposition:** CB-020 is **CLOSED**. `implementation_may_begin=true`; PST-WC01 may begin under the
existing implementation authority. The exact PgBouncer OCI index digest was obtained through the
Founder-authorized read-only public manifest lookup; no image was pulled or run.

## Preserved Authority Boundary

The owner decisions grant no Azure access, image pull/publication, provider plan/apply, deployment, restore
qualification, traffic admission, Demo acceptance, UAT action, Production action, approval or
merge. The one authorized public manifest lookup supplied the exact immutable PgBouncer digest;
no digest was fabricated.

## Runner Remediation

The Founder authorized bounded local Docker daemon repair after targeted network cleanup did not
restore the commit hook. INST-010 configured the daemon with non-overlapping
`172.19.0.0/16` default address space allocated as `/24` networks, preserving the existing Azure DNS
setting. The daemon restarted successfully, the existing `waooaw-auth-ui-preview` container returned
to `running` under its unchanged `unless-stopped` policy, and two simultaneous automatic networks
were created as `172.19.1.0/24` and `172.19.2.0/24` and then removed.

The retained pre-remediation candidate correctly remains failed under the execution-contract
no-blind-retry rule. This blocker update creates a new candidate identity for the next hook run;
prior failure evidence is not deleted or rewritten.

## Stop

Stop before provider access on any package mismatch, missing generated evidence, invalid PgBouncer
digest, failed PST-WC09A oracle, stale authorization tuple, cost/capacity breach, secret exposure,
Production delta, public/direct route, uncertain Billing state, recovery failure, or absent future
Founder acceptance. This owner pass creates no runnable code, Terraform, workflow or build artifact
and does not start PST-WC01.
