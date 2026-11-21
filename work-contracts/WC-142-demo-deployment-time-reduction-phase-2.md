# WC-142 - Demo Deployment Time Reduction, Phase 2

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-142 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-142 |
| Founder assignment | Current conversation: "I am really concerned regarding reducing time bringing it to less than 30 min"; "go, do 3 | Temporal shutdown-hang fix (WC-142) ... and test locally ... then do a pr which is ready for my review" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `76fd074b` (WC-140 merged; Demo run 44921194343 took 48 min 21 s) |
| Related contracts | WC-124 Temporal startup qualification; WC-140 time reduction (its R004 "mutations serial" is deliberately superseded by WC142-R004) |
| Requirement ledger | [WC-142-requirements.yaml](./WC-142-requirements.yaml) |
| Constitutional basis | C-059, C-063 |

## Authority And Scope

### In scope

1. The Temporal startup job stops the server within a bounded time on exit, always prints the Temporal log tail, and keeps the exit status of the qualification (run 44916211268 lost a deployment to an unbounded stop).
2. Job-status polls on the success path use a shorter sleep with an equal or longer total budget.
3. The activation-readiness invocations poll every 3 seconds instead of 15.
4. The Demo revision cleanup retires obsolete revisions of different apps concurrently, still serially within one app, and refuses the whole cleanup before any mutation when any app rolled out meanwhile.

### Out of scope (separate Work Contracts, each needs Founder authorization)

- The WhatsApp activation proof wait and the Temporal log-ingestion wait (they are safety evidence).
- Running cleanup and verification concurrently, and the pre-dispatch image mirror and broker start.
- Skipping the database authority chain when `reset_demo_database` is unchecked.
- Dispatching a deployment, approval and merge.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-142-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC142-R001 | On exit the Temporal startup controller sends SIGTERM to the server, waits at most 15 seconds, then sends SIGKILL, prints `WC142_TEMPORAL_SHUTDOWN graceful` or `WC142_TEMPORAL_SHUTDOWN forced`, prints the last 150 Temporal log lines and the sampler log, and exits with the status the qualification had before the trap ran |
| WC142-R002 | The PgBouncer preflight, billing migration, Temporal status, WC-124 provisioner and WC-124 handoff job polls sleep 3 seconds between checks and use attempt counts (200, 400, 200, 600, 600) whose sleep time is at least the previous attempts times 10 seconds; the `Unknown` grace handling is unchanged |
| WC142-R003 | The migration, dependency and activation readiness invocations use `--interval-seconds 3` with unchanged timeouts |
| WC142-R004 | Revisions of different apps are retired concurrently and those of one app serially, results keep app order, and a rollout detected in any app aborts the cleanup before any revision is retired |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. The estimated saving of this contract is small (about 1.5 to 2 minutes) because the measured polling cost is about half of each old interval; the end-to-end figure is measured by the first Demo deployment after merge and is not claimed here. The Temporal stall of run 44916211268 did not reproduce locally (6 of 6 clean stops) and in run 44921194343, so R001 is a bounded safeguard, not a proven root-cause fix.
