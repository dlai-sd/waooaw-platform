# WC-146 - Demo Deployment Time Reduction, Phase 3

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-146 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-146 |
| Founder assignment | Current conversation: "do this first WC-146 (the three remaining deploy levers) - lets learn to take things to logical conclusions for founder so i can focus on one area" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `d33956fa` (WC-143 merged); Demo run 44929414330 took 45 min 50 s |
| Related contracts | WC-124 Temporal startup qualification; WC-134 Demo WhatsApp autopilot (its `stop` receipt and proof gates are unchanged); WC-142 and WC-143 time reduction |
| Requirement ledger | [WC-146-requirements.yaml](./WC-146-requirements.yaml) |
| Constitutional basis | C-059, C-063 |

## Authority And Scope

### Measured causes (run 44929414330 and Log Analytics, 2026-11-21)

- **Temporal qualification** wrote its captures at 17:43:22 but finished at 17:45:30. The wait loop re-sent identical Log Analytics query text. A direct test showed that Log Analytics returns a cached result to identical query text for about 128 seconds (`print now()` repeated every 12 seconds returned the same value from 04:11:46 to 04:13:39 and a new value at 04:13:53); a unique comment in the query text bypasses the cache. PgBouncer logs were ingested about 5 seconds after they were written, so the watermark was satisfiable at about 17:43:35.
- **WhatsApp activation proof** finished at 17:58:36 although the heartbeat was in Log Analytics from 17:55:56. `_prove` re-sent identical queries every 30 seconds, so it read the same cached "0" results for about two minutes.
- **Verification** starts only after the whole engine finishes, including `cleanup-private` (141 s), although it needs only the applied environment.

### In scope

1. `verify` becomes a job of the deployment engine that needs only `terraform`, so it overlaps `cleanup-private`. Its trusted-caller, stale-release, evidence and verification-environment gates are unchanged, and the neutral entry publishes the URL only when the whole engine, including verification, succeeded.
2. Every Log Analytics poll (Temporal pool wait, provisioner result fallback, ACA execution evidence, WhatsApp proof) sends a unique query text.
3. The Temporal pool wait polls every 3 seconds, keeps the 180-second budget, prints each attempt and keeps the watermark rule.
4. The WhatsApp proof polls every 5 seconds instead of 30; its 600-second timeout and every proof gate are unchanged.

### Out of scope

- Removing or reordering any safety gate, including the `stop` operation and receipt, the migration acceptance order and the Temporal qualification pass criteria.
- Running WhatsApp activation concurrently with verification (activation creates revisions).
- Dispatching a deployment, approval and merge.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-146-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC146-R001 | `environment-deployment.yaml` defines job `verify` that uses `environment-deployment-verification.yaml`, needs only `terraform`, runs under `always()` when `inputs.apply` is true and the Terraform job output `apply_result` is `success`, and does not depend on `cleanup-private`; `deploy.yaml` has no `verify` job and `publish-url` needs `authorize` and `deploy` only; the verification workflow's trusted-caller, stale-release and `<environment>-verification` gates are unchanged |
| WC146-R002 | Every `az monitor log-analytics query` in the deployment workflow and `goal006_capture_aca_execution.sh`, and every autopilot query, carries a unique `// poll` comment per call |
| WC146-R003 | The Temporal pool log wait uses at most 60 attempts with a 3-second sleep, prints `[wc124-temporal-pool] attempt=... latest_log=... end_time=...` per attempt, and still requires a PgBouncer record at or after the execution end time and zero `query_wait_timeout` records |
| WC146-R004 | The WhatsApp proof sleeps `HEARTBEAT_POLL_SECONDS` (5) between polls, keeps the 600-second timeout, and its heartbeat and `42501` queries differ on every poll |

## Implementation Record

Expected saving, estimated from the measured gaps and not claimed until measured: Temporal wait about 2 minutes, WhatsApp proof about 2.5 minutes, verification overlap about 2.3 minutes, about 7 minutes in total. With the WC-143 database-chain reuse (about 8 minutes when its evidence is reusable) the Demo deployment is expected near 30 minutes. The first Demo deployment after merge measures it. The Temporal wait prints per-attempt evidence so the cause and the result are visible in the log.
