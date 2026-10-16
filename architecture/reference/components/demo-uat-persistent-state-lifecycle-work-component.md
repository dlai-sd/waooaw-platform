# Demo/UAT Persistent State Lifecycle Work Component

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Status | FOUNDER ACCEPTED UNDER FA-055 - IMPLEMENTATION REQUIRES SEPARATE WORK CONTRACT AND CURRENT-SESSION AUTHORITY |
| Version | `1.0.0` |
| Founder decision | FA-055, 2026-10-16 |
| Architecture inputs | PR #518 merge `a6bceb310585a2370cb593a32f684381d6ca94c6`; PR #519 architecture commit `7d18239c569d1bc97d6afd3d91981657ecaf052a`; `environment-readiness-and-data-continuity.md`; `azure-deployment-topology.md` |
| Constitutional basis | C-023, C-027, C-059, C-063, C-065, C-071, C-076 and C-080 |
| Applicable ADRs | ADR-010, ADR-011, ADR-013, ADR-014, ADR-015 and ADR-047 |
| Implementing office | Platform IT Expert (INST-010), Skill 17 |
| Target environments | Demo and UAT only |
| Authority boundary | Specification and implementation handoff. No `src/` implementation in the authoring session; no provider query/mutation, Terraform apply, deployment, traffic, Production, approval or merge. |

## 1. Outcome

Implement one governed lifecycle in which Demo and UAT:

1. use environment-owned persistent PostgreSQL Flexible Server and dedicated PgBouncer;
2. contain no replica-local PostgreSQL or component-local authority Redis sidecars;
3. keep billing, identity, workflow, session, tenant, idempotency, hold and evidence authority in
   governed PostgreSQL;
4. enter near-zero-cost sleep without deleting authoritative data;
5. reactivate through explicit database-to-traffic gates;
6. prove the behavior in Docker, CI, Terraform plans, deployment rehearsal and exact-head PR
   evidence; and
7. preserve Founder-only approval and merge.

Near-zero cost means compute can reach zero while storage, backups, DNS, retained telemetry and
control-plane costs remain. Literal zero cost requires deletion and is not part of this component.

## 2. Controlling Inputs And Precedence

Apply inputs in this order:

1. FA-055 and the current authorization boundary in `constitution/PROJECT_STATE.md`;
2. `environment-readiness-and-data-continuity.md`;
3. `azure-deployment-topology.md`;
4. accepted data, security, recovery and role/RLS contracts;
5. this Work Component;
6. the later approved Work Contract and atomic requirement ledger;
7. current implementation only as evidence of a gap, never as authority.

The implementer stops rather than selecting an Azure SKU, HA posture, recovery target, role,
credential path, migration meaning, cost exception or destructive lifecycle not pinned by the
approved inputs.

### 2.1 ADR And Claim Applicability

No new ADR is required for this Work Component. It applies accepted decisions rather than selecting
a new technology, provider, workflow engine, registry, secret store or migration policy:

| Reference | Binding effect |
|---|---|
| C-023 / C-027 | Lifecycle success and consequential state require durable evidence; constitutional evidence remains append-only |
| C-059 | Every implementation, migration, workflow and test traces to this accepted component |
| C-063 | Customer data and secrets remain purpose-bound, private and absent from plans/logs/artifacts |
| C-065 | Author, approver and merger remain separate |
| C-071 / C-076 / C-080 | Quality, coverage and Docker-only executable validation are non-waivable |
| ADR-010 | Azure services retain named escape hatches; no undocumented lock-in is introduced |
| ADR-011 | Database evolution is additive; constitutional records are never destructively migrated |
| ADR-013 | Existing GitHub Actions CI/CD remains the delivery path and CCTs remain blocking |
| ADR-014 | Cloud secrets use Key Vault references and never enter source, plan or evidence |
| ADR-015 | Demo self-hosted Temporal and UAT Temporal Cloud retain their accepted environment split |
| ADR-047 | Private runner, OIDC, state and local Azure-emulator qualification remain controlling |

A future implementation that needs a new Azure service, database technology, cache authority,
workflow engine, destructive migration, public database path or Production topology must stop for
the owning architect and a new or amended ADR. FA-055 accepts the lifecycle and cost boundary; it
does not amend the ADRs above or create implementation/provider authority.

## 3. Current-State Gap Baseline

| Gap ID | Current behavior | Required state |
|---|---|---|
| PST-001 | Workload Terraform injects `localhost` database URLs | Every cloud workload uses private TLS through environment PgBouncer |
| PST-002 | CE, BP and Billing revisions contain PostgreSQL sidecars | No application revision contains an authority datastore |
| PST-003 | Billing revision contains Redis sidecar | Billing Redis, if selected, is an environment transient dependency only |
| PST-004 | Temporal has replica-local PostgreSQL in Demo | Demo Temporal uses its own database/role on the environment server |
| PST-005 | Foundation Terraform has no Demo/UAT Flexible Server | One independently sized persistent server per environment |
| PST-006 | No dedicated PgBouncer deployment | One private digest-pinned PgBouncer dependency per environment |
| PST-007 | Billing integrity halt is a permanent Redis key | PostgreSQL is authoritative for halt and release |
| PST-008 | Reconciliation outcomes/status are Redis records | PostgreSQL stores durable execution and outcome records |
| PST-009 | Reconciliation idempotency is a Redis lease | Database uniqueness/outcome makes completion idempotent; Redis lease is optional and bounded |
| PST-010 | CI does not prove Redis-loss safety or sidecar absence | Blocking authority, topology, migration, recovery and lifecycle gates |
| PST-011 | Deployment has no ordered persistent-data activation/sleep gates | `deploy.yaml` orchestrates plan/activate/sleep through reusable workflows |
| PST-012 | Cost control conflates stopped compute and deleted data | Sleep retains data and records residual cost; deletion is excluded |
| PST-013 | Skill 17 names `scripts/run_goal006_local_azure_verification.sh`, but current `main` does not contain it | Restore or implement the canonical Docker/Azure-CLI emulator verifier before cloud-delivery qualification |

The Platform IT Expert must refresh this baseline against the exact implementation head before
editing. A changed path or already-closed gap updates the trace matrix; it does not remove the
acceptance oracle.

## 4. Scope

### 4.1 Included

- PostgreSQL Flexible Server Terraform for Demo and UAT;
- private DNS, subnet/routing, TLS and access-denial contracts;
- dedicated PgBouncer deployment and least-privilege role routes;
- separate application databases/schemas/roles;
- additive billing authority migrations and runtime changes;
- removal of cloud application PostgreSQL and Billing Redis sidecars;
- reconstruction/fail-closed treatment for permitted caches;
- environment sleep, activation and restart reconciliation;
- CI, precheck, release, migration, recovery and lifecycle evidence;
- `ci.yaml`, `deploy.yaml`, reusable deployment and verification workflows;
- local Docker fixtures and local Azure emulator/rehearsal paths;
- mandatory owning documentation and operational runbooks;
- exact-head PR preparation and Founder handoff.

### 4.2 Excluded

- Production database, HA, Redis or activation;
- customer traffic or acceptance;
- provider access, apply, spend or DNS without separate authority;
- deleting databases/backups as routine cost control;
- destructive down-migrations;
- a new deployment entry workflow;
- changing the exact-seven first-party image count;
- introducing a new database, cache, workflow engine or cloud service;
- changing business, identity, billing or constitutional behavior beyond moving existing authority
  to the accepted persistent boundary;
- self-approval or self-merge.

## 5. Required Inputs Before Implementation

The Work Contract must pin:

1. exact Demo and UAT PostgreSQL SKU, storage, autogrow and availability posture;
2. exact monthly estimate and owner-approved cost reserve beneath FA-052;
3. PostgreSQL version and provider version already accepted by the platform contract;
4. PgBouncer image digest, resource allocation, pool mode, server/client limits and timeouts;
5. database/schema/role inventory for Keycloak, Temporal, CE, BP, PR, AIR, Billing and Web sessions;
6. Entra bootstrap and any generated non-admin password handoff;
7. billing cutover treatment for existing Redis halt/audit values;
8. initial post-cutover billing state and required reconciliation;
9. migration order and previous-release compatibility window;
10. sleep lease, automatic-restart reconciliation interval and activation timeout;
11. backup/PITR and sanitized-restore fixture;
12. exact Demo/UAT apply authority, if any.

Missing input is a stop. Skill 17 does not permit the Platform IT Expert to choose it.

## 6. Target Stateful Asset Map

| Asset | Classification | Authority and lifecycle |
|---|---|---|
| Application data | `DURABLE_AUTHORITY` | PostgreSQL; component schema/invariants; backup and restore qualified |
| Billing halt/release | `DURABLE_AUTHORITY` | PostgreSQL transactional record; missing/uncertain state blocks writes |
| Reconciliation execution/outcome | `DURABLE_AUTHORITY` | Unique PostgreSQL execution identity and immutable outcome linkage |
| Authentication limiter counters | `BOUNDED_COORDINATION` | Environment Redis; TTL bounded; no identity/session authority |
| Billing catalogue/mode projections | `RECONSTRUCTIBLE_CACHE` | Redis optional; rebuilt from PostgreSQL |
| PgBouncer | Runtime dependency | No authority; may stop only after clients; starts after PostgreSQL |
| Key Vault | `SECRET_AUTHORITY` | Purpose/principal separated; no secret in plan/state/log/evidence |
| Terraform state | `INFRASTRUCTURE_STATE` | Protected environment backend; no customer/application data |
| Telemetry | `OBSERVABILITY` | Redacted and bounded; never sole consequential evidence |
| Local container files | `SCRATCH` | Disposable; no restart correctness obligation |

## 7. PostgreSQL And PgBouncer Implementation

### 7.1 Foundation

Modify the existing phase-2 foundation module and Demo/UAT roots to create one persistent Flexible
Server per environment with:

- accepted low-cost independent sizing;
- private routing and DNS;
- TLS-only connectivity;
- 35-day backup/PITR contract;
- storage/autogrow limits;
- lifecycle protection against workload destroy;
- diagnostic and cost tags;
- outputs containing identifiers/hostnames, never credentials.

Production roots must produce no change.

### 7.2 Bootstrap

Use the accepted Entra bootstrap identity and no-echo provisioner to create separate databases,
schemas and least-privilege roles. Bootstrap is idempotent, environment-bound and fails before
application plan on partial state.

### 7.3 PgBouncer

Deploy one private environment dependency:

- digest-pinned image from the dependency manifest;
- dedicated managed identity and Key Vault references;
- transaction pooling compatible with transaction-local RLS;
- closed network route from approved workloads only;
- connection, saturation, rejection and readiness telemetry;
- `min_replicas=0` outside active leases and verified start before migration/application work.

Direct workload-to-server and public database paths are denied and tested.

## 8. Billing Durable-Authority Migration

Add expand-only PostgreSQL objects owned by Billing:

1. integrity state and release history;
2. reconciliation execution identity and status;
3. reconciliation outcome and discrepancy/evidence linkage;
4. audit result and last-completed projection;
5. uniqueness/concurrency constraints required for idempotency.

Update Billing so:

- integrity halt and release commit in PostgreSQL;
- wallet/consequential writes read authoritative halt state;
- uncertain/missing state fails closed;
- reconciliation claims one durable execution identity;
- same identity/same digest replays the recorded outcome;
- same identity/different digest conflicts;
- Redis cannot create, clear or outlive a halt;
- cached audit/catalogue/mode projections rebuild after Redis loss;
- clear-halt preserves who/why/evidence rather than deleting authority;
- startup and readiness prove database authority before accepting traffic.

The migration must preserve the accepted fail-safe choice for any existing Redis halt. The
implementer may not infer that Redis absence means unhalted.

## 9. Workload Terraform Changes

Remove from cloud application revisions:

- CE, BP and Billing PostgreSQL containers;
- Billing Redis container;
- replica-local authority volumes;
- Temporal PostgreSQL sidecar;
- cloud `localhost` database URLs;
- shared PostgreSQL superuser credentials.

Add:

- environment PgBouncer endpoints;
- per-service database/role references;
- dependency/readiness ordering;
- migration job identity and exact release/schema binding;
- no-echo secret references;
- lifecycle inputs for active/sleep states;
- verification outputs required by the reusable deployment workflow.

Local Compose may retain ephemeral PostgreSQL/Redis fixtures only when named and tested as
non-authoritative Docker test dependencies.

## 10. Sleep Contract

`sleep` is one idempotent operation:

1. validate authority, environment and active release;
2. close ingress and block new consequential work;
3. drain or reconcile active requests, workflows and migrations;
4. record release, schema, billing-halt, audit and evidence watermarks;
5. prove backup/recovery readiness and zero destructive plan delta;
6. scale exact-seven application revisions to zero;
7. scale PgBouncer and transient dependencies to zero;
8. stop PostgreSQL compute;
9. verify stopped state and record residual monthly cost;
10. schedule bounded automatic-start/maintenance reconciliation.

Sleep fails if work is uncertain, evidence is incomplete, a migration is active, backup proof is
stale, a protected resource would be deleted, or PostgreSQL does not reach the verified stopped
state. Failure never proceeds to deletion.

## 11. Activation Contract

`activate` is one idempotent operation:

1. validate current-session provider authority, lease and cost forecast;
2. select a successful current-main CI release and exact-seven tuple;
3. start PostgreSQL and wait for private-TLS readiness;
4. verify roles, RLS, backup, schema, migration and billing-halt watermarks;
5. start PgBouncer and verify every service route;
6. execute accepted expand-only migrations once;
7. verify previous-release schema compatibility;
8. start Keycloak, Temporal and transient Redis dependencies;
9. deploy/start exact-seven application revisions without rebuilding;
10. rebuild caches and reconcile bounded coordination;
11. run internal health, CCT, identity, billing, workflow and public synthetic probes;
12. publish URL/admit traffic only after complete PASS.

Activation target is 5-20 minutes. Timeout, cost breach, partial dependency, uncertain migration,
stale billing state or failed probe leaves traffic at zero with retained evidence.

## 12. `ci.yaml` Changes

Extend the existing change-planned CI graph; do not create a parallel CI workflow.

| Gate | Required executable proof |
|---|---|
| Terraform/static | fmt/validate/policy across Demo/UAT roots; Production no-change |
| Topology | no cloud member PostgreSQL/Billing Redis sidecar, local authority volume or `localhost` DB route |
| Secret safety | no secret value in Terraform plan, output, workflow log or artifact |
| Migration | real PostgreSQL + PgBouncer; canonical migration order; second apply idempotent |
| Roles/RLS | each role has only accepted database/schema rights through PgBouncer |
| Billing authority | halt/release, audit and reconciliation survive Redis deletion and process restart |
| Concurrency | two Billing replicas produce one durable reconciliation completion |
| Cache | catalogue/mode projections rebuild; cache loss never changes outcome |
| Sleep | drain/watermark/order/idempotency and protected-resource assertions |
| Activation | database-to-traffic order, timeout and fail-closed matrix |
| Recovery | backup/PITR fixture, sanitized restore and prior-release compatibility |
| Release | exact-seven unchanged; dependency manifest separately pinned/signed |
| Constitutional | C-023, C-059, C-065, C-071, C-076 and Test Champion gates |

The validation planner must select these gates for changes to Billing, PostgreSQL migrations,
Terraform foundation/workload modules, environment roots, lifecycle scripts, `ci.yaml`,
`deploy.yaml`, reusable deployment/verification workflows or owning architecture.

## 13. `deploy.yaml` And Reusable Workflow Changes

Keep `.github/workflows/deploy.yaml` as the only manual entry and add a closed action choice:
`plan`, `activate`, or `sleep`. Do not expose delete.

### Plan

- authorize dispatcher and current-main release;
- resolve environment, state, cost and lease;
- generate immutable foundation/dependency/workload plans;
- reject destruction, public database access, cross-environment state and secret disclosure;
- record expected monthly active/sleep cost and protected inventory.

### Activate

- call the reusable engine in the exact Section 11 order;
- bind every step to environment, release SHA, run identity and reviewed plan;
- publish URL only after independent verification.

### Sleep

- call the same engine in the reverse dependency order from Section 10;
- retain database/storage/backups, state, Key Vault and evidence;
- verify zero application/dependency replicas and stopped PostgreSQL;
- record residual resources and forecast.

The verification workflow independently proves the final state and must not consume success-shaped
fallbacks from the deployment job.

## 14. Local Docker And Azure Emulator Qualification

Use repository Docker runners only.

1. Retain local PostgreSQL, PgBouncer and Redis as explicit test fixtures.
2. Run migrations twice through PgBouncer.
3. Run focused Billing authority and Redis-loss tests.
4. Run multi-replica reconciliation and fail-closed readiness tests.
5. Run Terraform and workflow contract tests.
6. Restore or implement the Skill 17-required
   `scripts/run_goal006_local_azure_verification.sh`, prove it uses the pinned Docker Azure CLI
   against the deterministic local control-plane emulator, and run it for focused lifecycle
   iteration.
7. Run `scripts/run_goal006_local_rehearsal.sh` once before submission.
8. Preserve failed-attempt and final evidence artifacts.
9. State explicitly that emulator evidence does not prove Azure provider scheduling, identity,
   networking, DNS, cost or service availability.

Live Azure plan/apply or deployment evidence requires separate authority.

## 15. Documentation And Operations

After executable behavior is qualified, update only:

- this component and its Work Contract requirement ledger;
- environment/data-continuity and Azure topology implementation-bound parameters;
- database/role/migration inventory;
- Billing authority and cache classification;
- sleep/activation/recovery/rollback runbooks;
- CI/deployment evidence references;
- `PROJECT_STATE.md` only for an externally meaningful transition.

Do not rewrite PR #518/#519 history, create a parallel architecture, or claim deployment from local
evidence.

## 16. PR Preparation, Merge And Post-Merge

1. branch from current `origin/main`;
2. implement dependency-ordered components and keep unrelated changes out;
3. use conventional commits with required C-059 fields and co-author trailer;
4. run focused checks after each component and impacted Docker qualification at completion;
5. complete author review against every requirement and repair all findings;
6. before final push, prepare the exact template body with:
   `python scripts/prepare_pr_body.py --body-file /tmp/pr-body.md --base origin/main --allow-unpushed-head`;
7. push the final commit;
8. rerun without `--allow-unpushed-head` and update the PR body with exact remote-head evidence;
9. verify Release qualification, C-059, C-065, migration/state-authority, Test Champion and local
   Azure runtime artifacts once;
10. hand the PR to the Founder.

Only the Founder may approve and merge. A merge to `main` triggers main CI and creates a deployable
candidate, not deployment authority. `deploy.yaml apply/activate/sleep`, Demo mutation, UAT mutation,
traffic and acceptance remain separately authorized.

## 17. Dependency-Ordered Work Components

| ID | Dependency | Exact output | Exit oracle |
|---|---|---|---|
| PST-WC00 | None | Approved Work Contract, atomic ledger, authority and pinned inputs | No missing decision or placeholder |
| PST-WC01 | WC00 | Exact current-state impact map and baseline tests | Every PST-001..013 mapped to source and falsifying test |
| PST-WC02 | WC01 | Additive Billing authority schema | Migration twice and role/RLS tests PASS |
| PST-WC03 | WC02 | Billing PostgreSQL authority implementation | Redis-loss, restart, halt and idempotency tests PASS |
| PST-WC04 | WC01 | Demo/UAT Flexible Server foundation | Terraform/policy/cost/no-Production-change PASS |
| PST-WC05 | WC04 | Dedicated PgBouncer and role bootstrap | Private route and least-privilege tests PASS |
| PST-WC06 | WC03, WC05 | Workload sidecar removal and connection rewiring | Topology scan and service integration PASS |
| PST-WC07 | WC06 | Sleep lifecycle | Ordered, idempotent, retained-data sleep rehearsal PASS |
| PST-WC08 | WC07 | Activation lifecycle | Database-to-traffic and fail-closed rehearsal PASS |
| PST-WC09 | WC02-WC08 | `ci.yaml` complete blocking gates | Change planner and every applicable gate PASS |
| PST-WC10 | WC07-WC09 | `deploy.yaml` plan/activate/sleep orchestration | Workflow contract, emulator and rollback matrix PASS |
| PST-WC11 | WC10 | Canonical local Azure verifier plus recovery, prior-release and cost qualification | Docker Azure-CLI emulator, restore/RPO/RTO/schema/cost evidence PASS |
| PST-WC12 | WC11 | Mandatory docs and operational handoff | Owning records match executable behavior |
| PST-WC13 | WC12 | Author review and exact-head PR | Prepared body and all remote-head gates PASS |
| PST-WC14 | WC13 | Founder handoff | PR ready; no self-approval/merge/deploy claim |

No component starts while a dependency is incomplete or its exit oracle is partial.

## 18. Acceptance Oracles

The delivery is implementation-ready and complete only when:

- Demo and UAT plans contain one environment Flexible Server and dedicated PgBouncer;
- no cloud application revision contains PostgreSQL or Billing Redis authority sidecars;
- every application uses its own role through private PgBouncer;
- Production plan is unchanged;
- deleting/restarting Redis cannot clear Billing halt, erase audit history or duplicate outcome;
- sleep retains all authoritative data and reaches verified zero application/dependency replicas;
- sleeping residual cost is measured and below the approved envelope;
- activation starts in the accepted order and publishes no traffic before complete verification;
- automatic database restart is detected and safely reconciled;
- migration is additive, idempotent and readable by the previous qualified release;
- restore meets accepted RPO/RTO with sanitized evidence;
- exact-seven release identity remains unchanged and dependencies are separately pinned;
- no secret appears in plan/state/log/artifact;
- all selected Docker, CI, security, constitutional and Test Champion gates pass;
- the Skill 17 local Azure verifier exists and its retained runtime artifact passes;
- exact-head author review is PASS and the Founder receives the PR.

## 19. Rollback

Application rollback switches to the prior immutable exact-seven tuple without rebuilding or
destructive migration. The database, PgBouncer, Key Vault, state and backups remain. The prior
release must read the additive schema before traffic. A failed activation returns applications and
dependencies to zero and leaves PostgreSQL in the safest verified state; it does not delete data.
A failed sleep keeps traffic closed and reports the actual residual state for operator decision.

## 20. Stops

Stop for:

- missing Work Contract or current-session implementation authorization;
- unpinned SKU, cost, role, PgBouncer or cutover decision;
- provider access/mutation without exact current authority;
- destructive or Production plan delta;
- secret in plan/state/log/evidence;
- direct/public database route;
- uncertain Billing halt or migration outcome;
- inability to prove Redis-loss safety;
- recovery objective failure;
- two reproducible infrastructure failures;
- cost forecast above FA-052;
- conflict with unrelated user changes;
- any request to self-approve, self-merge or infer deployment authority.

## 21. Chief Solution Architect Handoff

The Platform IT Expert receives a closed implementation boundary: persist authority in
environment-owned PostgreSQL, route through dedicated PgBouncer, remove cloud authority sidecars,
make Billing Redis-safe, implement retained-data sleep and explicit reactivation, bind the behavior
into existing CI and deployment entry paths, qualify it with Docker/emulator evidence, and prepare
an exact-head Founder-ready PR.

No architecture, provider, SKU, cost exception, destructive lifecycle, Production, approval, merge
or deployment decision is delegated to implementation.
