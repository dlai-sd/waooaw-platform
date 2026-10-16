# CB-020 - WC-124 Persistent-State Implementation Inputs

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-020` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-16` |
| Status | **OPEN** |
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
They do not pin all values required before implementation:

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

PST-WC00 has no valid exit while these inputs are absent. PST-WC01 through PST-WC14 must not start,
and no runnable code, Terraform, workflow or build artifact may be created.
