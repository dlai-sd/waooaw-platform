# Demo/UAT Persistent-State Lifecycle Runbook

## Boundary

This runbook applies only to Demo and UAT. It does not grant Azure access, plan/apply, deployment,
restore qualification, traffic admission, Production, approval, or merge authority. Each real
provider action requires current-session Founder authority and an unexpired environment-exact
authorization tuple.

## Plan

1. Select the successful current-`main` exact-seven release.
2. Verify private-runner and isolated-state prerequisites.
3. Generate non-destructive foundation, dependency, and workload plans.
4. Reject deletion, public/direct/foreign database routes, secret disclosure, capacity above 80%,
   combined sleeping cost above INR 3,200, or active cost above INR 10,000 before GST.
5. Retain the reviewed plan, protected inventory, cost inventory, and tuple digests.

## Activate

1. Confirm terminal state `SLEEPING`, current Founder authority, lease, and exact tuple.
2. Start PostgreSQL and wait for `Ready`.
3. Apply the reviewed PgBouncer scale and dependency plan.
4. Run additive migrations through PgBouncer and verify the schema watermark.
5. Start dependencies and applications.
6. Run independent route, role/RLS, Billing, evidence-chain, capacity, and application checks.
7. Admit traffic and publish the URL only after the independent verifier signs acceptance.
8. On failed or uncertain work, retain evidence and enter `FAILED_ACTIVATION`, `RECOVERY_HOLD`, or
   `SECURITY_HOLD`; never report success-shaped fallback state.

## Database Paths (WC-177)

Read the plan first, then act. Nothing here grants Azure, deployment, Production, approval or merge authority.

1. **Read the plan.** The deployment job summary shows "Database path" and its reason;
   `wc143-database-chain-decision.json` holds the full decision. The path is `reuse`, `update` or `full`.
2. **When each path runs.** `reuse`: nothing database-related changed. `update`: only new init files
   headed `-- wc177-apply: update` that pass the lint (additive: create, add nullable/defaulted columns,
   policies, grants to existing roles, bounded backfills; no drops, renames, type changes, role or
   extension changes). `full`: first deployment, unreadable or older record, a changed chain input or
   applied file, a new file that is not update-class, a reset, or a failed live fact.
3. **Force the full chain.** Dispatch the deployment with `database_path=full`. Use it for first setup,
   role or secret changes, resets and destructive or privileged SQL; it is never chosen by assumption.
4. **Recover from an update refusal.** A refused or failed update changes nothing beyond the files whose
   transaction committed with their ledger row. Read `wc177-database-update.log` (the reason is
   `WC177_UPDATE_REFUSED` or `WC177_UPDATE_FAILED`; a lock timeout is retried a bounded number of times).
   Fix the file and redeploy; use `database_path=full` only when the file is not update-class. Do not retry
   an unchanged failure.
5. **The restore marker.** Before each update the workflow records `wc177-restore-marker.json`: the
   server and its earliest restorable point at that moment. A real point-in-time restore still needs its
   own Founder authority and the PITR procedure below.
6. **Resume a failed run.** After the database and migration checkpoint, dispatch with
   `resume_from=activation`; it is honoured only when the plan reports `reuse` and the checkpoint is bound
   to the same release, otherwise the deployment starts from the beginning.

## Sleep

1. Confirm terminal state `ACTIVE`, current Founder authority, lease, and complete PASS gate input.
2. Drain traffic and record application/workflow watermarks.
3. Scale applications, Temporal/Keycloak, and PgBouncer to zero; verify zero replicas.
4. Verify backups, protected inventory, migration/schema watermarks, and absence of active or
   uncertain work.
5. Stop PostgreSQL last. Never delete the server, storage, backups, Key Vault, Terraform state, or
   lifecycle evidence.
6. Retain the execution result and residual monthly cost.

## Recovery And Rollback

- Docker evidence uses only isolated synthetic fixtures and never claims provider recovery.
- A real PITR qualification requires separate Founder authority, an isolated private restore
  target, a recorded restore point, sanitized verification, and independent acceptance.
- RPO above 5 minutes or RTO above 30 minutes enters `RECOVERY_HOLD`.
- Rollback reuses the complete immutable prior release/configuration/dependency/schema/migration/
  plan/secret-catalog tuple. Additive schema is retained; no destructive down-migration is allowed.
- Partial or uncertain infrastructure state is reconciled forward under `RECOVERY_HOLD`.

## Alerts And Escalation

The controlling signal definitions are in
`infrastructure/operations/wc124-lifecycle-alerts.yaml`. Platform Operations may observe, alert,
and escalate. Alert ownership grants no deployment, data, secret, provider-action, traffic, or
hold-release authority. The sole scheduled mutation is re-stopping an unexpectedly restarted
sleeping PostgreSQL server when every catalogued condition passes; otherwise enter
`RECOVERY_HOLD`.
