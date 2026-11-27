# WC-177 - Deployment Time Reduction, Phase 4: A Database Update Path And Faster Application Stages

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-177 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-134 (Demo rollout recovery); continues WC-142, WC-143, WC-145 and WC-146 |
| Founder assignment | Current conversation, 2026-11-27: "how can we improve Database path as well? there can be a path to refresh and apply full db. But we shall have 'db update' only path which shall make it faster/cheaper with avoiding overheads? any ways uat and prod will work in this fashion", then "verify these unverified points ... cost of implementing a work contract and finding that few points should have verified earlier", then "yes, please write a work contract detailed enough and mention need to updating constitutional components during implementation so documentation reflect these changes for future sessions." |
| Status | GROOMED AND VERIFIED LOCALLY, AWAITING FOUNDER REVIEW. Implementation has not started and needs the Founder's explicit authorization for the session, chunk by chunk. Requirements that name a Founder decision (D1 to D3) stop at that decision. |
| Baseline | `origin/main` at `18e76536` (PR #659 merged); measured run 45983274213 (Demo, success, 40 minutes) |
| Requirement ledger | [WC-177-requirements.yaml](./WC-177-requirements.yaml) |
| Constitutional basis | C-023, C-059, C-063, C-065 |
| Relationship to earlier contracts | WC-124 (the database authority chain) is preserved as the full path. WC-143 (reuse of an unchanged chain) is extended: its fingerprint covers every init SQL file, so any SQL change invalidates reuse and forces the whole chain. WC-146 (poll caching, verify overlap) is unchanged. WC-168 added the quiesce step for the reuse path; this contract makes that step conditional. Digest-bound earlier contracts are not edited; this contract records what it supersedes. |
| Deployment | One Demo deployment per completed chunk, then the live proof in R022 |

## Why This Contract Exists

A Demo deployment takes about 40 minutes when it succeeds, and 8 of the last 18 runs failed or were cancelled, so the
expected time to a good deployment is over an hour. The Founder cannot rely on a deployment he starts. Earlier phases
removed waste inside each stage. What remains is structural: **every database change, even one new table, runs the
whole database identity ceremony, and every deployment re-runs work that has nothing to do.** UAT and Production will
use the same engine, so the cost and the risk repeat there unless the path is split now.

## How It Was Verified (before writing this contract)

Everything marked VERIFIED was run on 2026-11-27 against the real init files from `origin/main`, on a local PostgreSQL 16
instance (pgvector image) that replays the WC-124 role model: a non-superuser bootstrap principal applies the chain, the
service owner roles and migrators are created by `00-wc124-principal-bootstrap.sql`, and the provisioner's own grants are
reproduced. Demo was not touched. The harness and the result log are kept in the session files as
`db-update-path-harness.sh` and `db-update-path-run4.log`; R011 turns them into a repository test.

| Question | Result | Evidence class |
|---|---|---|
| Does today's `bp_migrator` apply new init SQL? | No. Of the last 30 files, 23 pass and 7 fail (`permission denied to grant role "wbe_owner"`, `must be owner of table`, `permission denied to create role`). With `wbe_owner` granted and the bootstrap-owned objects reassigned, 26 pass and 4 fail. Cause: the files were written for the bootstrap principal, which holds `bp_owner` and `wbe_owner` itself. They run `GRANT wbe_owner TO session_user` and `RESET ROLE`. A migrator whose default role is `bp_owner` returns to `bp_owner` on `RESET ROLE`, which cannot touch `wbe_owner` tables. | VERIFIED (replica) |
| Does a dedicated update role fix it? | Yes. A login role with membership in `bp_owner` and `wbe_owner` and no default-role override applied **29 of the last 30** files. The one failure creates a role (`wc172-03`), which needs `CREATEROLE`. | VERIFIED (replica) |
| Can the update role read and write the init-chain ledger? | Not by default: the ledger schema is closed to everyone but the bootstrap. After `GRANT USAGE` on the schema and `SELECT, INSERT, UPDATE` on the table, yes. | VERIFIED (replica) |
| Do objects owned by the bootstrap block an update? | Yes. Files with no `SET ROLE` create tables owned by the bootstrap principal (visitor tables, `identity.phone_onboarding`, several functions). An update role cannot alter them (`wc137-02` failed). `REASSIGN OWNED BY bootstrap TO bp_owner`, run once in the full path, fixed it. | VERIFIED (replica); the same ownership on real Demo is EXPECTED from the file content and is proved by R005 |
| Why does a database change cost the whole chain today? | `wc143_database_chain_record.py` fingerprints every file under `infrastructure/postgres/init/` together with the chain scripts. One new SQL file changes the fingerprint, so reuse is refused. | CODE |
| Does the chain code support Production? | No. `chain_fingerprint` raises unless the environment is `demo` or `uat`, and every chain step in the workflow is guarded the same way. Production has no database path yet. | CODE |
| Does the existing architecture allow the update path? | Yes in intent: `environment-readiness-and-data-continuity.md` section 8.2 forbids the bootstrap from "routine migration" and describes a digest-pinned, additive, pre-traffic migration job. Today's chain uses the bootstrap for routine migration. The update principal holds two owner roles, which that section's "only its owned schemas" wording does not yet allow; that is decision D2. | CODE (architecture) |
| Is a job image with `psql` already pinned? | Yes. `infrastructure/terraform/phase2/modules/workload/main.tf` pins `docker.io/library/postgres@sha256:0cefaabd...` for a Container Apps job. The Billing authority migration (`job-<env>-wc124-billing-migration`, same file) is the template: a short-lived in-network job through PgBouncer with a Key Vault secret. | CODE |
| Where does the time go? | Run 45983274213, 41 minutes of step time: database chain 9.8 minutes (authority open 99 s, quiesce 74 s, provisioner 76 s, handoff 67 s, bootstrap removal 47 s, verification and records the rest); vendor, Billing and Temporal migrations 5.6 minutes (vendor 137 s, Billing 33 s, Temporal qualification 145 s); application activation, readiness and revision cleanup 7.5 minutes; broker, mirror, verify and cleanup jobs 8.6 minutes; Terraform plans and applies 3.9 minutes; WhatsApp activation 3.6 minutes (210 s); other gates 2.5 minutes. | MEASURED (GitHub job steps) |
| Why are vendor migrations slow? | Demo's PostgreSQL (B1ms, `max_connections` 50) leaves 25 usable connections. The step waits for the connection metric to show headroom between Keycloak and Temporal; the metric lags about two one-minute buckets. They run on every deployment with no skip rule. | CODE, MEASURED |
| Why does Temporal qualification take 145 s? | It first waits for the previous Temporal copy to scale to zero after its idle cooldown (`wait_for_replicas_drained.sh`, 480 s budget), then runs a 60-second qualification. That is why the reuse path needs the quiesce step. | CODE, MEASURED |
| Terraform | Five stages (foundation plan 63 s, workload plan 100 s, dormant apply 72 s, activation plan 80 s, activation apply 91 s), 386 resource refreshes, 19 apps changed at activation. The foundation plan said "No changes". | MEASURED |

Not verified, and proved first by the requirement named: real Demo ownership of bootstrap-owned objects (R005); PgBouncer
transaction-mode behaviour for whole-file application (R011, using the local PgBouncer in `scripts/lib/wc124_local_stack.sh`);
whether the pinned `postgres` image or the provisioner image carries what the apply program needs (R006); any saving in the
application stages (R012 to R015 measure before they change anything).

## Objectives

| Id | Objective |
|---|---|
| O1 | A deployment with no database change spends about one minute on the database, instead of about 15 |
| O2 | A deployment whose only database change is new additive SQL applies it in three to four minutes, with the applications running and no bootstrap authority opened |
| O3 | The full chain stays available as an explicit, separate path for first setup, role or secret changes, resets and destructive changes, and is never chosen by assumption |
| O4 | UAT uses the same paths; Production is designed to use the update path first and stays refused until the Founder decides D1 and D2 |
| O5 | Every stage records the path it took and its seconds, so each saving is measured, not claimed |
| O6 | The constitutional and architecture documents, the Platform IT Expert specification, the runbooks and the state surfaces describe the new paths in the same pull requests that implement them, so a future session starts from the truth |

## Authority And Scope

In scope: `.github/workflows/environment-deployment.yaml`; `scripts/wc143_database_chain_record.py`,
`scripts/wc143_database_chain_live_facts.sh`, `scripts/wc124_db_provisioner.py`, `scripts/wc124_init_chain_lint.py`,
`scripts/wc124_init_chain_local.sh`, `scripts/wc124_pre_activation_evidence.py` and related tests; the secret catalog
(`infrastructure/environment-readiness/secret-catalog.json`); the Terraform workload module (one new job); the
documents listed in the Documentation And Constitutional Currency section; Demo deployments and the live proof.

Out of scope: UAT and Production deployments (only their guards and refusal tests); a PostgreSQL size or SKU change; any
change to application code or customer journeys (WC-176); Keycloak and Temporal version changes; removing or reordering a
safety gate without the Founder's decision D3; creating or amending an ADR (Platform IT does not hold that authority; an
ADR need is raised to the Enterprise Architect); editing `constitution/CONSTITUTION.md` or `constitution/GENESIS.md`.

Authority limits: no secret value is read or printed; the update principal is created only by the full path while the
bootstrap authority is open, and no standing human or workflow credential gains database authority; every Demo run is
started by the Founder and is never watched or polled by the agent; implementation code needs the Founder's
authorization for the session (the Implementation Gate); validation runs in Docker only, once per completed chunk.

## Design

### Three database paths, chosen by one read-only plan

The plan runs where the "Decide WC-124 database chain reuse" step runs today. It reads only the repository, the sealed
record from the last successful deployment, and the live facts the reuse path already reads. It never connects to the
database.

| Path | Chosen when | What runs | Applications |
|---|---|---|---|
| `reuse` | The chain fingerprint (chain scripts, secret catalog, `00-wc124-principal-bootstrap.sql`, update-principal definition) is unchanged, the recorded init-file digests equal the repository's, the live facts match, the record is intact and under 7 days old | Credential handoff verification and the terminal authority checks only | Not stopped |
| `update` | The chain fingerprint is unchanged, every recorded init file has the same digest, and the only difference is new files, each declared `update` class and passing the lint | The update job applies the new files as the update principal through PgBouncer; read-only verification; the record is rewritten | Not stopped |
| `full` | Anything else: first deployment, an unreadable or older-version record, a changed chain input, a changed already-applied file, a new `full`-class or unclassified file, a requested reset, a failed live fact, or the dispatch input `database_path=full` | The WC-124 chain exactly as today, plus the one-time update-principal setup | Stopped as today when a reset or the Temporal qualification needs it |

Any doubt selects `full`. A refusal inside the update job (changed digest, unknown file class, a statement outside the
update rules) fails the deployment with the reason and changes nothing; the next dispatch uses `database_path=full`.

### File classes (what "additive" means, enforced by the lint)

Every new init file starts with the header `-- wc177-apply: update` or `-- wc177-apply: full`. A missing header means
`full`. An `update` file may only: create tables, indexes, functions, triggers, policies, sequences and types with the
idempotent forms of the Idempotent Init-Chain SQL Standard; add columns (nullable or defaulted); add constraints and
policies; grant or revoke privileges to or from existing roles; run bounded backfills; set owners to `bp_owner` or
`wbe_owner`. Every object-creating statement must run under `SET LOCAL ROLE bp_owner` or `wbe_owner` inside the file's
transaction, with `lock_timeout` and `statement_timeout` set. An `update` file may not drop or rename tables, columns,
schemas or types, truncate, change a column type, create or alter roles, grant a role to another role, create or alter
extensions, or change anything owned by `ce_owner`, `pr_owner`, `air_owner`, `billing_owner` or `web_session_owner`.
Those belong in a `full` file, which the Founder reviews as a destructive or privileged change.

### The update principal

One login role (name fixed in R005) with no default role, no superuser, no `CREATEROLE`, no `CREATEDB`, member of exactly
the owner roles the `update` class allows (today `bp_owner` and `wbe_owner`), with `CONNECT` on the application database,
and `USAGE` on the ledger schema with `SELECT, INSERT, UPDATE` on the ledger table. Its credential is a new Key Vault
secret in the secret catalog, read only by the update job's identity, like the Billing migration credential. The full
path creates it, grants the memberships and ledger access, and runs `REASSIGN OWNED BY <bootstrap> TO bp_owner` while the
bootstrap authority is open. Its memberships are listed in the provisioner result evidence and checked by R008 on every
update.

### The record

The sealed record (WC-143) gains: the list of applied init files with digests, the Keycloak and Temporal image digests and
the PgBouncer image and configuration digest that were last qualified, and the schema version. It is written after a
successful `full` and after a successful `update` (WC143-R001 only allowed the full chain to write it). A version-1
record is not an error: it selects `full` once and is replaced.

### Vendor migrations and Temporal qualification

They run when the recorded vendor image digests, their migration job definitions or the PgBouncer image and configuration
differ, or when the record has no earlier success. Otherwise they are skipped with labelled evidence. The quiesce step
(WC-168) runs only when the Temporal qualification runs, because that is the only reason it exists on the reuse path.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-177-requirements.yaml` binds to this file's complete SHA-256 digest;
any edit of this file after the ledger is written requires a new digest.

| Id | Requirement |
|---|---|
| WC177-R001 | The database plan step chooses `reuse`, `update` or `full` per the Design table from the repository, the sealed record and the live facts, never connects to the database, writes the path and the reason to the job summary and an evidence file, and selects `full` for every input it cannot read or does not recognise. A unit test covers each row of the decision table and each fail-closed case. |
| WC177-R002 | The sealed record is version 2: it carries the applied init-file digests, the last qualified vendor and PgBouncer digests and the schema version, is written after a successful `full` or `update`, is still sealed by `record_sha256`, and a version-1 record selects `full` once without failing the deployment. WC143-R001's "written only by the full chain" is superseded and the supersession is recorded here and in the topology document. |
| WC177-R003 | Every deployment writes, for each stage group (database, vendor migrations, Temporal qualification, Terraform, activation, readiness, cleanup, verification, WhatsApp), the path taken, the reason and the seconds to the job summary and to an evidence file, so each later saving is measured against run 45983274213. |
| WC177-R004 | New init files carry the `-- wc177-apply: update|full` header; `wc124_init_chain_lint.py` rejects a file with no header only as `full`, rejects any `update` file that breaks the update rules in the Design section (including a missing `SET LOCAL ROLE` for object creation), and has tests for each rule. Existing files are not changed and are treated as already applied. |
| WC177-R005 | The full path creates the update principal (no default role, no superuser, no `CREATEROLE`, no `CREATEDB`), grants it exactly the owner memberships the update class allows, grants it `CONNECT` and the ledger access, runs `REASSIGN OWNED BY` the bootstrap principal to `bp_owner`, and records the memberships and the count of bootstrap-owned objects before and after in the provisioner result. The credential is added to the secret catalog, the provisioner's credential specifications and the Key Vault handoff, and is readable only by the update job. The first Demo full run proves the ownership assumption with real data. |
| WC177-R006 | A Container Apps job `job-<env>-wc124-database-update` in the workload module, modelled on `job-<env>-wc124-billing-migration`, runs a pinned image that carries `psql` and the apply program, connects as the update principal through PgBouncer, applies only ledger-missing `update` files in C-locale order, each in one transaction together with its ledger row, and refuses a changed digest, an unclassified or `full` file and any statement outside the update rules. The workflow input `database_path` (`auto` or `full`) is added; `reset_demo_database` is unchanged. Before building, the requirement confirms which image carries what the apply program needs. |
| WC177-R007 | The update path does not stop or quiesce any application and keeps the existing order (database change before runtime dependencies and application activation). Lock waits are bounded by the files' `lock_timeout`; the job retries a lock timeout a bounded number of times with a pause and then fails with the blocking statement named. A test holds a conflicting lock and shows the bounded failure and a clean retry. |
| WC177-R008 | After an `update` the deployment runs a read-only verification as the update principal: the ledger rows equal the repository digests; every object in the new files is owned by an owner role; the Business Platform schema health check object set exists; the update principal's memberships equal the expected set and it holds no superuser, `CREATEROLE` or `CREATEDB`. A failure fails the deployment. |
| WC177-R009 | `wc124_pre_activation_evidence.py` and the activation bundle accept the `update` path with its own labelled evidence (as `reuse` is labelled today) and still reject evidence bound to a different execution or record. The terminal live checks (no Secrets Officer assignment, no bootstrap administrator) and the credential handoff verification run on every path. |
| WC177-R010 | Keycloak and Temporal vendor migrations and the Temporal startup qualification are skipped, with labelled evidence, only when the recorded vendor and PgBouncer digests and the migration job definitions equal the current ones and the record shows an earlier success; otherwise they run unchanged. The quiesce step runs only when the Temporal qualification runs. A test covers each skip and each forced-run input. |
| WC177-R011 | The local qualification `wc124_init_chain_local.sh` (fresh pinned pgvector instance) gains: the replica scenario of this contract (base chain by the bootstrap, then pending files by the update principal); the local PgBouncer in transaction mode between the update principal and the database; zero `pg_dump --schema-only` drift between "full chain" and "base chain plus update"; refusal of a `full`-class, unclassified and changed-digest file; the lock-timeout case; and evidence in `test-results/wc124/init-chain-local/`. It runs in Docker and is listed in the release qualification gate. |
| WC177-R012 | The application-only fast path is defined by the plan, not by assumption: a stage is skipped only when its own plan output proves it has nothing to do (a "No changes" Terraform plan, a running and unchanged PgBouncer, unchanged runtime dependencies). No safety gate is removed. Each skipped stage is recorded with the proof it used. Measured before and after. |
| WC177-R013 | The cost of the five Terraform stages (386 refreshes each) is measured, and a reduction is implemented only if the plan provenance rules (exact plan binary, state lineage and serial, backend, run and attempt) still hold; otherwise the finding and the reason are written into the topology document and nothing changes. |
| WC177-R014 | The 210-second WhatsApp activation is measured by phase. Savings inside its existing proof gates (polling, parallel reads) are implemented. Skipping it, or moving it after go-live, changes a safety gate and needs decision D3. |
| WC177-R015 | A failed deployment can resume at the failed stage group: each stage group writes a checkpoint bound to the release SHA, run, plan digests and its inputs; a `resume_from` input is honoured only when every checkpoint before it is intact and bound to the same release; otherwise the deployment starts from the beginning. Existing resume work (`goal006_activation_readiness.py --resume-stopped`, the deployment resume preflight) is read first and reused. |
| WC177-R016 | UAT uses the same three paths and guards as Demo, with a restore marker (the recorded point-in-time before the database change) written before each `update` on UAT. Production is refused by the plan and by a test until D1 and D2 are answered; the Production design (update path first, restore marker, `full` only with the Founder's approval) is written into the topology and lifecycle documents. |
| WC177-R017 | The Platform IT Expert specification (`architecture/reference/agents/platform-it-expert-agent.md`) is updated in the implementing pull requests: section 2.5 (file classes, the header, the update rules, the update principal, the ledger, the two executable gates extended) and a skill (a new skill or an extension of an existing one, keeping any skill-count assertion and the version and changelog rows consistent) for choosing and running the database path and reading the plan evidence. |
| WC177-R018 | `architecture/reference/pipeline/azure-deployment-topology.md` is updated: deployment strategy (items 3 and 4), the tooling map (the plan step, the update job, the lint header, the record version), the operator handbook update entry, the stage-time table, and the supersession of WC143-R001. |
| WC177-R019 | `architecture/reference/components/environment-readiness-and-data-continuity.md` (sections 8.1 and 8.2: the role and ownership floor gains the update principal, with its prohibited authority) and `architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md` (section 7.2, principal contract) are updated to match what ships. No ADR is created or amended by Platform IT; if D2 finds that an ADR must change, a request is raised to the Enterprise Architect and the requirement records it. |
| WC177-R020 | A runbook entry (in `architecture/reference/runbooks/demo-uat-persistent-state-lifecycle.md`, or a new runbook it links) tells the operator, in order: how to read the plan evidence, when each path runs, how to force `database_path=full`, how to recover from an update refusal, and what the restore marker is. |
| WC177-R021 | The generated and registered surfaces are current in every pull request: new tests are registered in `validation/engineering-validation.yaml` and the release qualification gate; `scripts/run_platform_state_refresh.sh` is run before the last commit; `constitution/PROJECT_STATE.md` records the state transitions (update path live on Demo; UAT parity; Production decision pending); and a pipeline test fails when the workflow input names, the file-class header token, the update principal name, the record version and the documents in R017 to R020 disagree. |
| WC177-R022 | Live proof on Demo, each started by the Founder: (a) a deployment with no database change takes the `reuse` path and its database stages take about two minutes or less; (b) a deployment whose only database change is a harmless idempotent `update` file takes the `update` path with applications running; (c) a dispatch with `database_path=full` still completes; (d) the measured times are recorded against the baseline in this contract. The first real additive SQL file of a later work contract may serve as (b). |

## Founder Decisions Needed

| Id | Decision | Blocks |
|---|---|---|
| D1 | Production database path: approve that Production uses the update path first, with a point-in-time restore marker before every change and `full`-class changes only with the Founder's approval in the PR | R016 for Production |
| D2 | The update principal holds membership in two owner roles (`bp_owner`, `wbe_owner`), which section 8.2 of the environment-readiness component does not allow today ("only its owned schemas"). Platform IT proposes one principal with exactly those memberships, enforced by the lint and checked on every update. The Enterprise Architect rules on the wording, and on whether an ADR changes, before R005 ships | R005, R019 |
| D3 | May any safety gate be moved or skipped (WhatsApp activation after go-live, skipping it when nothing changed, sharing one Terraform refresh)? The default is no; R012 to R014 improve only inside the existing gates until the Founder answers | R013, R014 (the gate-changing parts) |

## Execution Chunks (dependency order)

| Chunk | Requirements | Outcome | Depends on |
|---|---|---|---|
| A. Plan and measure | R001 to R003 | The path is chosen by a read-only plan; every stage reports its path and seconds | none |
| B. The update path | R004 to R011 | New additive SQL applies in three to four minutes with applications running; vendor and Temporal work runs only on change | A; D2 for R005 |
| C. Faster application stages | R012 to R015 | No-op stages skipped on proof; Terraform and WhatsApp measured; failed runs resume | A; D3 for the gate-changing parts |
| D. UAT and Production | R016 | UAT parity; Production refused until decided | B; D1 and D2 for Production |
| E. Documentation and constitutional currency | R017 to R021 | The specification, the architecture documents, the runbook and the state surfaces describe what shipped | written inside each chunk's pull requests, completed here |
| F. Proof | R022 | The live paths and the measured times are recorded | A to E deployed |

Chunk A first, because it changes nothing in the database and makes every later saving measurable. Chunk B ships in
two pull requests: first the lint, the principal, the update job and the local qualification with the full path
unchanged (so a deployment still behaves as today); then the plan switches `update` on. Docker validation runs once per
completed chunk, never per defect.

## Documentation And Constitutional Currency (explicit, per the Founder's instruction)

Documents are updated in the same pull request as the behaviour they describe, never afterwards. The agent does not
rely on memory notes; the repository is the record. Digest-bound earlier contracts are not edited.

| Document or surface | What changes | Requirement | Authority note |
|---|---|---|---|
| `architecture/reference/agents/platform-it-expert-agent.md` | Section 2.5 standard; the database-path skill; version and changelog rows | R017 | Platform IT's own specification |
| `architecture/reference/pipeline/azure-deployment-topology.md` | Strategy, tooling map, operator update, stage-time table, WC143-R001 supersession, Production design | R018, R016 | Platform IT operator handbook |
| `architecture/reference/components/environment-readiness-and-data-continuity.md` | Sections 8.1 and 8.2 role and ownership floor | R019 | Changed only as D2 allows; EA request if an ADR is needed |
| `architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md` | Section 7.2 principal contract | R019 | Same as above |
| `architecture/reference/runbooks/demo-uat-persistent-state-lifecycle.md` | Operator steps for the paths | R020 | Platform IT |
| `infrastructure/environment-readiness/secret-catalog.json` | The update credential | R005 | Platform IT with the provisioner |
| `validation/engineering-validation.yaml`, release qualification gate | New tests registered | R021 | Platform IT |
| `constitution/PROJECT_STATE.md`, `README.md`, `SPRINT-REGISTRY.md`, `constitution/AGENT-ENTRY.md`, `architecture/reference/work-contract-delivery-ledger.yaml`, `validation/process-control.yaml` | Generated by `scripts/run_platform_state_refresh.sh`; the PROJECT_STATE checkpoint is written by hand at each state transition | R021 | Platform IT; the Founder merges |
| `constitution/CONSTITUTION.md`, `constitution/GENESIS.md`, any ADR | Not touched by this contract | none | Class 1 immutable; ADRs belong to the Enterprise Architect |

## Definition Of Done

1. Every requirement has direct executable evidence in `WC-177-requirements.yaml`: a failing test first where code changes, then passing in the Docker runners (Python with `PYTHONPATH=/workspace:/workspace/scripts`; the local database qualification in its Docker runner).
2. After each chunk is merged and the Founder deploys it, the matching part of R022 runs and its measured times are written into the Implementation Record.
3. R022 closes the contract: the `reuse`, `update` and explicit `full` paths each completed on Demo, and the saving is stated as measured against the 40-minute baseline.
4. The documents in the table above describe the shipped behaviour, and the R021 consistency test passes.
5. Decisions D1 to D3 are answered, or their requirements are recorded as waiting.
6. Author review is bound to the exact head commit; every pull request goes to the Founder for review and merge. No self-approval.

## Stop Conditions

- A requirement reaches decision D1, D2 or D3.
- The update principal would need an authority the Design does not list (superuser, `CREATEROLE`, a standing human credential, an owner role outside `bp_owner` and `wbe_owner`).
- A change would remove or reorder a safety gate, or weaken the fail-closed rule that any doubt selects `full`.
- A real Demo run shows the ownership assumption in R005 is wrong in a way the reassign does not fix.
- A destructive or privileged SQL change is needed (it goes to a `full` file and the Founder).

## Implementation Record

Not started. Expected savings below are estimates from the measured step times of run 45983274213, are not claimed, and
are replaced by measured values in R022.

| Change | Estimated saving | Basis |
|---|---|---|
| `reuse` path (no database change) | about 8 to 9 minutes | The chain's authority, provisioner, handoff and removal steps are skipped; vendor, Temporal and quiesce skip when pins are unchanged |
| `update` path (additive SQL only) | about 9 to 10 minutes versus today's full chain | Applies in about 3 to 4 minutes instead of about 14 to 15 |
| Application-stage work (R012 to R015) | about 3 to 6 minutes, least certain | Depends on what the measurements allow without changing a gate |
| Failed run | A resumed run costs the remaining stages instead of restarting | Eight of the last 18 runs failed or were cancelled |

### Grooming Log

| Date | Item | Result |
|---|---|---|
| 2026-11-27 | Contract created | From the Founder's deployment-time analysis; 22 requirements, three Founder decisions |
| 2026-11-27 | Replica test: existing migrator | Verified: a migrator with default role `bp_owner` applies 23 of the last 30 files (26 once `wbe_owner` is granted and bootstrap-owned objects are reassigned); files that grant owner roles to the session user or use `RESET ROLE` fail |
| 2026-11-27 | Replica test: dedicated update principal | Verified: 29 of the last 30 files apply; the only failure creates a role |
| 2026-11-27 | Replica test: ledger and ownership | Verified: the ledger needs one grant; bootstrap-owned objects need `REASSIGN OWNED BY` once |
| 2026-11-27 | Run 45983274213 timing | Measured: 41 minutes of step time; the database chain 9.8 minutes, migrations and qualification 5.6, activation and readiness 7.5, jobs around the apply 8.6, Terraform 3.9, WhatsApp 3.6, other 2.5 |
| 2026-11-27 | Production | Code refuses it today; the update path is therefore Production's first database path, not an optimisation |
