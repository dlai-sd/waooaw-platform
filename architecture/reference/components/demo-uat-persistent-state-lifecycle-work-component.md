# Demo/UAT Persistent State Lifecycle Work Component

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Status | FOUNDER ACCEPTED UNDER FA-055 - INSTITUTIONAL REVIEW REPAIR CANDIDATE - IMPLEMENTATION REQUIRES SEPARATE WORK CONTRACT AND CURRENT-SESSION AUTHORITY |
| Version | `1.1.0-candidate.2` |
| Founder decision | FA-055, 2026-10-16 |
| Architecture inputs | PR #518 merge `a6bceb310585a2370cb593a32f684381d6ca94c6`; PR #519 architecture commit `7d18239c569d1bc97d6afd3d91981657ecaf052a`; `environment-readiness-and-data-continuity.md`; `azure-deployment-topology.md` |
| Constitutional basis | C-023, C-027, C-059, C-063, C-065, C-071, C-076 and C-080 |
| Applicable ADRs | ADR-010, ADR-011, ADR-013, ADR-014, ADR-015, ADR-034 and ADR-047 |
| Institutional review | Enterprise, Data, Security and Platform reviews of v1.0.0 returned CHANGES_REQUIRED; Data passed candidate 1; candidate 2 closes the remaining Security and Platform findings and requires exact-head author verification |
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
| ADR-034 | Billing integrity, universal prepaid buckets, durable outcomes and financial correctness remain binding |
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
12. exact Demo/UAT apply authority, if any;
13. immutable per-environment authorization tuple: environment, GitHub protected environment, OIDC subject/audience,
    Azure tenant/subscription/resource group, Terraform backend key, runner identity, release SHA,
    plan digest, secret-catalog digest, lease ID and expiry;
14. canonical secret catalog and separate bootstrap, migration, workload, deployment and
    verification principals;
15. dataset-level sidecar cutover ledger and any explicit synthetic-data discard authority;
16. existing ADR-047 runner/state evidence or the prerequisite delivery that closes it;
17. lifecycle-control record location, signing identities, scheduled reconciliation authority and
    alert owner; and
18. promotion evidence binding Founder-accepted Demo application digests and schema/migration
    digest to an independently authorized UAT configuration/dependency manifest.

Missing input is a stop. Skill 17 does not permit the Platform IT Expert to choose it.

## 6. Target Stateful Asset Map

| Asset | Classification | Authority and lifecycle |
|---|---|---|
| Customer business and employment records | `DURABLE_AUTHORITY` | Component-owned PostgreSQL schema; tenant RLS; purpose-specific retention and legal hold |
| Professional records | `DURABLE_AUTHORITY` | Professional schema; tenant/relationship binding; append-only fields where required |
| Constitutional evidence | `DURABLE_AUTHORITY` | Constitutional schema; append-only transition lineage; no update/delete authority |
| Identity and session authority | `DURABLE_AUTHORITY` | Keycloak/Web session databases and owner APIs; no Redis or local-file authority |
| Temporal workflow authority | `DURABLE_AUTHORITY` | Demo: dedicated PostgreSQL database/role; UAT: Temporal Cloud under ADR-015 |
| Billing financial records | `DURABLE_AUTHORITY` | Billing schema; tenant isolation, financial retention and reconciliation evidence |
| Billing halt/release | `DURABLE_AUTHORITY` | PostgreSQL transactional record and append-only release history; missing/uncertain state blocks writes |
| Reconciliation execution/outcome | `DURABLE_AUTHORITY` | Unique PostgreSQL execution identity and immutable outcome/evidence linkage |
| Authentication limiter counters | `BOUNDED_COORDINATION` | Environment Redis; TTL bounded; no identity/session authority |
| Billing catalogue/mode projections | `RECONSTRUCTIBLE_CACHE` | Redis optional; rebuilt from PostgreSQL |
| PgBouncer | Runtime dependency | No authority; may stop only after clients; starts after PostgreSQL |
| Key Vault | `SECRET_AUTHORITY` | Purpose/principal separated; no secret in plan/state/log/evidence |
| Terraform state | `INFRASTRUCTURE_STATE` | Protected environment backend; no customer/application data |
| Telemetry | `OBSERVABILITY` | Redacted and bounded; never sole consequential evidence |
| Local container files | `SCRATCH` | Disposable; no restart correctness obligation |

### 6.1 Required Data Ownership And Retention Register

Before implementation, the Work Contract supplies one machine-readable register with one row per
database/schema/table family. Each row includes:

- component owner, NOLOGIN object owner and authorized writer/readers;
- environment, tenant/relationship scope and RLS policy;
- immutability/append-only rules and permitted transitions;
- purpose, retention, legal/evidence hold and authorized disposition;
- backup inclusion, restore order and restore validation;
- source dataset and cutover treatment;
- API/invariant owner and migration owner.

No generic `application data` row satisfies this input. Constitutional restore qualification proves
all predecessor/successor evidence links, update/delete denials and append-only rules after restore.
Financial restore qualification proves balances, reservations, outcomes, holds, releases and their
evidence references reconcile exactly.

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

### 7.2 Two-Plan Bootstrap And Principal Contract

Bootstrap is an exact two-plan transition:

1. **Plan A - Entra-only foundation.** Create the server, private DNS/networking, Entra
   administrator/bootstrap identity, databases, NOLOGIN owners, schemas, roles and Key Vault
   references. Password authentication remains disabled. No application receives a database
   credential and no workload route is admitted.
2. **Bootstrap transaction.** The Entra bootstrap identity creates only the accepted generated
   non-admin LOGIN roles and grants. It cannot write application data. The no-echo provisioner
   generates each distinct credential in memory and writes only its Key Vault version.
3. **Plan B - reviewed compatibility enablement.** Only after Plan A and bootstrap evidence pass,
   enable the minimum accepted password-authentication compatibility required by PgBouncer,
   Keycloak or another pinned dependency. Administrator passwords remain prohibited.
4. **Handoff.** Separate migration and workload identities receive exact secret-version access.
   Bootstrap access is removed or disabled before application activation.

Every schema uses a NOLOGIN owner. Runtime roles are LOGIN, NOBYPASSRLS, non-owner principals with
only required schema/table/sequence/function rights. Migration authority is separately bounded and
cannot grant itself runtime, owner, administrator or cross-environment rights. `PUBLIC` grants are
revoked. Every tenant table has `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
Receiver-validated tenant context is transaction-local and PgBouncer must reset it before reuse.

Negative tests reject an administrator password, password enablement before Plan A acceptance,
credential echo, shared role/secret, object ownership by a runtime role, `BYPASSRLS`, missing tenant
context, cross-tenant access, foreign-environment access and direct workload-to-server access.

### 7.3 PgBouncer

Deploy one private environment dependency:

- digest-pinned image from the dependency manifest;
- dedicated managed identity and Key Vault references;
- transaction pooling compatible with transaction-local RLS;
- closed network route from approved workloads only;
- connection, saturation, rejection and readiness telemetry;
- `min_replicas=0` outside active leases and verified start before migration/application work.

Direct workload-to-server and public database paths are denied and tested.

### 7.4 Network Denial Matrix

| Source | PostgreSQL 5432 | PgBouncer | Required proof |
|---|---|---|---|
| Same-environment PgBouncer identity/subnet | Allow private TLS | N/A | Hostname-validating TLS and accepted server identity |
| Same-environment application identity/subnet | Deny | Allow exact private route | Positive PgBouncer route and direct-server denial |
| Migration identity/job | Deny direct unless exact accepted exception | Allow exact bounded route | One-shot purpose and post-job revocation |
| Private deployment runner | Deny | Deny application data plane | Control-plane operation only |
| Foreign environment | Deny | Deny | Demo-to-UAT and UAT-to-Demo negative probes |
| Public Internet/public DNS fallback | Deny | Deny | No public endpoint, route or resolution |

Default-deny workload egress permits only accepted environment dependencies. DNS failure cannot fall
back to a public address. Every Demo and UAT plan and live qualification proves the full matrix.

## 8. Billing Durable-Authority Migration

Add expand-only PostgreSQL objects owned by Billing:

1. integrity state and release history;
2. reconciliation execution identity and status;
3. reconciliation outcome and discrepancy/evidence linkage;
4. audit result and last-completed projection;
5. uniqueness/concurrency constraints required for idempotency.

Update Billing so:

- a discrepancy greater than one paise atomically commits reconciliation outcome, discrepancy,
  evidence reference and integrity-halt transition in one PostgreSQL transaction under ADR-034;
- one-paise and lower boundary behavior is explicit and executable;
- halt release appends an authorized release event with actor, authority, reason and evidence and
  never deletes or overwrites the halt history;
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

### 8.1 Reconciliation Idempotency Identity

The Work Contract pins the canonical execution key as:

`environment + tenant/accounting-scope + reconciliation-type + covered-period + source-watermark`

and pins deterministic canonical JSON serialization plus SHA-256 payload digest. PostgreSQL
enforces one transactional claim for that key with states `CLAIMED`, `RUNNING`, `COMMITTED`,
`FAILED_RETRYABLE`, `FAILED_FINAL` and `RECONCILIATION_REQUIRED`. Same key/same digest replays the
terminal outcome; same key/different digest conflicts before financial work. A crash before outcome
commit resumes or safely reclaims the original execution; a crash after commit replays it. Tests
cover cross-tenant/environment collisions, all paise boundaries, duplicate replicas, Redis loss and
crashes before claim, after claim, before outcome commit and after outcome commit.

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

### 9.1 Dataset Cutover Ledger

Removing a sidecar requires one accepted row for every CE, BP, Billing and Demo Temporal dataset:

| Required field | Rule |
|---|---|
| Owner and authority class | Exact component/schema owner; constitutional, business, financial or workflow |
| Source and target | Revision/image/volume plus environment server/database/schema |
| Migration method | Freeze/export/import/backfill or explicit authorized synthetic discard |
| Consistency proof | Counts, digests, key watermarks, foreign-key/invariant and evidence-link reconciliation |
| Write fence | Time and identity that close source writes before final copy |
| Cutover watermark | Immutable source/target/release/schema identity |
| Rollback point | Last state from which prior release can resume without split authority |
| Retention/disposition | Source hold duration and separately authorized deletion |

No sidecar is removed until its row passes. Synthetic Demo data may be discarded only when the
Founder explicitly accepts that row; absence of customer data is not discard authority. Source
volumes remain held until restore, rollback and reconciliation evidence pass.

### 9.2 Terraform State And Runner Prerequisites

Before foundation implementation, either cite accepted evidence or deliver prerequisite components
for:

- ADR-047 private runner activation and exact OIDC subject/audience;
- environment-isolated backend keys, locking and ownership;
- private backend access and public fallback denial;
- cross-environment state/identity denial;
- current-state import/ownership resolution with no duplicate resource creation;
- drift detection, reviewed plan retention and partial-apply reconciliation;
- Storage-account separation required before UAT qualification.

Missing prerequisite evidence blocks PST-WC04; repository state is not proof of deployed ownership.

## 9.3 Provider Reversibility Matrix

ADR-010 requires this accepted exit contract:

| Azure dependency | Portable authority/configuration | Exit/migration proof | Owner and stop |
|---|---|---|---|
| PostgreSQL Flexible Server | Standard PostgreSQL schema/data, role/RLS manifest, logical export and restore ledger | Restore to compatible PostgreSQL, reconcile counts/digests/watermarks, rerun role/RLS and application probes | INST-006 criteria; INST-010 execution; stop on data/invariant mismatch |
| ACA applications/PgBouncer | OCI digests, environment/config schemas, dependency manifest | Run exact tuple on compatible OCI runtime and prove routes, health, scaling and rollback | INST-009; stop on platform-specific behavior |
| Key Vault | Secret catalog metadata and version references, never secret values in repository evidence | Separately authorized no-echo re-seed into compatible secret authority and principal-denial proof | INST-007/009; stop on disclosure or identity mismatch |
| Private DNS/networking | Versioned route, DNS, NSG and denial matrices | Recreate private names/routes and pass every positive/negative source probe | INST-007/009; stop on public/direct fallback |
| Azure Monitor/Log Analytics | OTel schema, redaction and bounded retention contract | Route OTel to compatible sink and prove signal/alert parity | INST-009/Operations; stop on missing security/lifecycle signal |
| Terraform remote state | Versioned roots, import map, backend ownership and digest evidence | Move state through reviewed backend migration with lock, backup and plan equality | INST-009; stop on ownership or plan delta |

An exit is a separately authorized migration, not an automatic fallback. No exit weakens privacy,
evidence, recovery, tenant isolation or service acceptance.

## 9.4 Durable Lifecycle Control Plane

Lifecycle truth is stored outside the stoppable application database in the existing protected
environment lifecycle-evidence storage. It contains no customer data and is hash-chained and signed
by the deployment writer; an independent verification identity signs admission/sleep disposition.
The record binds operation ID, requested action, current/target state, environment, authorization
tuple, secret-catalog digest, release/configuration/dependency/schema/migration digests, lease, step
watermark, attempts, timestamps, evidence digests and failure/hold reason.

The existing `deploy.yaml` is the only mutation entry. It gains the lifecycle action and scheduled
reconciliation trigger rather than creating a new workflow or service. The scheduled path uses a
separate least-privilege environment OIDC identity. It may observe and alert by default; it may
re-stop an automatically started PostgreSQL server only while the original sleep lease and exact
Founder/provider authority remain valid. Otherwise it enters `RECOVERY_HOLD` and alerts Platform
Operations without mutation.

| Current state | Allowed next states |
|---|---|
| `SLEEPING` | `ACTIVATING_DATABASE`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| `ACTIVATING_DATABASE` | `ACTIVATING_GATEWAY`, `FAILED_ACTIVATION`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| `ACTIVATING_GATEWAY` | `MIGRATING`, `FAILED_ACTIVATION`, `SECURITY_HOLD` |
| `MIGRATING` | `ACTIVATING_DEPENDENCIES`, `FAILED_ACTIVATION`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| `ACTIVATING_DEPENDENCIES` | `ACTIVATING_APPLICATIONS`, `FAILED_ACTIVATION`, `SECURITY_HOLD` |
| `ACTIVATING_APPLICATIONS` | `VERIFYING`, `FAILED_ACTIVATION`, `SECURITY_HOLD` |
| `VERIFYING` | `ACTIVE`, `FAILED_ACTIVATION`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| `ACTIVE` | `DRAINING`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| `DRAINING` | `SLEEPING_DEPENDENCIES`, `FAILED_SLEEP`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| `SLEEPING_DEPENDENCIES` | `STOPPING_DATABASE`, `FAILED_SLEEP`, `SECURITY_HOLD` |
| `STOPPING_DATABASE` | `SLEEPING`, `FAILED_SLEEP`, `RECOVERY_HOLD`, `SECURITY_HOLD` |
| Any failed state | original operation resume, `RECOVERY_HOLD` or `SECURITY_HOLD` after evidence review |
| Any nonterminal state | `SECURITY_HOLD` on C-001/security signal |

One environment lock permits one lifecycle operation. Same operation ID resumes from the durable
watermark; a different action conflicts. Bounded retries retain every failure. No hold state admits
traffic, migration, rollback or automatic mutation.

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
8. start Keycloak, Demo self-hosted Temporal and transient Redis dependencies; for UAT, verify the
   ADR-015 Temporal Cloud endpoint, environment-specific mTLS, namespace and readiness without
   creating or starting a UAT Temporal database;
9. deploy/start exact-seven application revisions without rebuilding;
10. rebuild caches and reconcile bounded coordination;
11. run internal health, CCT, identity, billing, workflow and public synthetic probes;
12. publish URL/admit traffic only after complete PASS.

Activation target is 5-20 minutes. Timeout, cost breach, partial dependency, uncertain migration,
stale billing state or failed probe leaves traffic at zero with retained evidence.

UAT activation is prohibited until the Founder accepts Demo application digests and the exact
schema/migration digest being promoted. UAT must use those immutable application and migration
identities without rebuild or reselection. Because Demo and UAT intentionally have different
Temporal and environment dependencies, UAT uses its own separately reviewed configuration and
dependency manifest. Promotion evidence cryptographically binds both environment manifests to the
same accepted application/schema/migration identity and proves each manifest against its own
environment-specific acceptance criteria.

### 11.1 Immutable Provider Authorization Tuple

Every plan, activate, sleep, restore and rollback step verifies the exact per-environment tuple from
Section 5.13. Demo authorization is never reused for UAT or vice versa. The tuple is included in the
signed reviewed-plan digest and lifecycle record. A mismatch in environment, protected GitHub
environment, OIDC subject/audience, Azure tenant/subscription/resource group, backend key, runner
identity, release SHA, plan digest, secret-catalog digest, lease or expiry fails before provider
access. Negative workflow tests mutate each field independently and require denial.

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
| Security evidence | hash-chain/signature validation, writer/verifier separation, `PST-SEC-EVIDENCE-01`, `PST-SEC-EMERGENCY-01` and forged-replacement rejection |
| Authorization | every provider tuple and secret-catalog digest mismatch denied before provider access |
| Network | full Demo/UAT source-denial matrix including public/foreign/direct paths |
| Release | exact-seven unchanged; dependency manifest separately pinned/signed |
| Constitutional | C-023, C-059, C-065, C-071, C-076 and Test Champion gates |

The validation planner must select these gates for changes to Billing, PostgreSQL migrations,
Terraform foundation/workload modules, environment roots, lifecycle scripts, `ci.yaml`,
`deploy.yaml`, reusable deployment/verification workflows or owning architecture.

Capacity qualification uses the accepted limits: 35-day retention, RPO <= 5 minutes, RTO <= 30
minutes, PostgreSQL connection limits 40/100 and PgBouncer client limits 40/80 for Demo/UAT. The
calculation includes current and overlapping revisions, migrations, operations reserve, Keycloak,
Demo Temporal, Billing, Web sessions and every exact-seven member. Planned aggregate use above 80%
blocks activation.

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
- block UAT unless its environment-specific authorization/configuration/dependency tuple is valid
  and promotion evidence binds it to the exact Founder-accepted Demo application/schema/migration
  identity.

### Sleep

- call the same engine in the reverse dependency order from Section 10;
- retain database/storage/backups, state, Key Vault and evidence;
- verify zero application/dependency replicas and stopped PostgreSQL;
- record residual resources and forecast.

The verification workflow independently proves the final state and must not consume success-shaped
fallbacks from the deployment job.

### Protected Azure PITR qualification

Docker CI proves migration/recovery logic but never claims provider recovery. A separately
authorized reusable workflow phase creates an isolated private restore target, selects and records
the restore point, runs sanitized restore, verifies schema/migration watermarks, counts/digests,
tenant and FORCE-RLS denial, constitutional append-only lineage, financial reconciliation and
application smoke, then places cleanup under an evidence-retention hold. The independent
verification identity signs the result. RPO greater than 5 minutes, RTO greater than 30 minutes,
source-route access, cleanup before retained evidence, or any invariant mismatch blocks traffic.

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

### 14.1 Security Holds And Independent Evidence

Lifecycle evidence is hash-chained, content-addressed and signed by distinct deployment-writer and
verification identities. `PST-SEC-EVIDENCE-01` is the executable direct-UPDATE rejection criterion
named **Evidence immutability** in
`architecture/reference/security/security-architecture.md`; `PST-SEC-EMERGENCY-01` is the
executable **Emergency Stop path reachability under Business Platform rate limiting** criterion
from the same record. Both are blocking. The unrelated tests currently labelled `CCT-SEC-04` and
`CCT-SEC-05` in `tests/constitutional/README.md` cannot satisfy these criteria. A forged, replaced,
truncated, wrong-environment or writer-self-accepted chain is rejected. Security, C-001 emergency-stop,
recovery, approval, legal/evidence-retention and destructive-plan holds block activation, rollback,
sleep mutation and traffic admission as applicable. Failed-attempt evidence is retained.

The independent verifier, not the deployment job, signs traffic admission, sleep completion,
restore acceptance and rollback acceptance.

## 15. Documentation And Operations

After executable behavior is qualified, update only:

- this component and its Work Contract requirement ledger;
- environment/data-continuity and Azure topology implementation-bound parameters;
- database/role/migration inventory;
- Billing authority and cache classification;
- sleep/activation/recovery/rollback runbooks;
- CI/deployment evidence references;
- the lifecycle signal/alert catalogue;
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

### 16.1 Lifecycle Observability And Operations

The Work Contract pins signal, threshold, retention, redaction, evidence, owner and escalation for:

- unexpected PostgreSQL start and automatic-restart reconciliation;
- stale/expired lease, stuck transition and exhausted retry;
- failed stop/start and lifecycle lock conflict;
- backup age, PITR/RPO/RTO and restore failure;
- PgBouncer saturation, rejection and server-route failure;
- migration/schema watermark drift;
- public/direct/foreign network-route detection;
- cost forecast/actual drift; and
- evidence-chain/signature failure.

Platform Operations owns alert response under its accepted authority. No alert receiver gains
deployment, data, secret or hold-release authority.

## 17. Dependency-Ordered Work Components

| ID | Dependency | Exact output | Author | Acceptance authority | Independent evidence owner | Exit oracle |
|---|---|---|---|---|---|---|
| PST-WC00 | None | Approved Work Contract, atomic ledger, authority and pinned inputs | INST-010 | Founder/owning contract authorities | INST-015 checks entry evidence | No missing decision or placeholder |
| PST-WC01 | WC00 | Exact current-state impact map and baseline tests | INST-010 | INST-005/006/007/009 by boundary | INST-015 | Every PST-001..013 mapped to source and falsifying test |
| PST-WC02 | WC01 | Additive Billing authority schema and cutover ledger | INST-010 | INST-006 plus Billing owner | INST-015 | Migration twice, cutover and role/RLS tests PASS |
| PST-WC03 | WC02 | Billing PostgreSQL authority implementation | INST-010 | Billing owner under accepted contract | INST-015 | Atomic halt, Redis-loss, restart and idempotency tests PASS |
| PST-WC04 | WC01, WC09A | Demo/UAT Flexible Server foundation | INST-010 | INST-009 topology; INST-006 recovery; INST-007 security | INST-015 | Terraform/policy/cost/no-Production-change PASS |
| PST-WC05 | WC04 | Two-plan bootstrap, PgBouncer and role/RLS contract | INST-010 | INST-006/007/009 | INST-015 | Private route, secret and tenant-isolation matrices PASS |
| PST-WC06 | WC03, WC05 | Dataset cutover, sidecar removal and connection rewiring | INST-010 | Component/data owners | INST-015 | Cutover ledger, topology and service integration PASS |
| PST-WC07 | WC06 | Durable lifecycle controller and sleep path | INST-010 | INST-009; hold owners retain release authority | INST-015 | State-transition, evidence and retained-data sleep rehearsal PASS |
| PST-WC08 | WC07 | Activation and environment-bound UAT promotion | INST-010 | Founder Demo acceptance; INST-009 activation | INST-015 | Database-to-traffic, promoted application/migration identity, environment tuple and fail-closed rehearsal PASS |
| PST-WC09 | WC02-WC08 | `ci.yaml` complete blocking gates | INST-010 | Existing CI/quality policy | INST-015/Test Champion | Change planner and every applicable gate PASS |
| PST-WC09A | WC00 | ADR-047 runner and isolated Terraform state prerequisites | INST-010 | INST-009/007 and existing authority records | INST-015 | Runner, backend, lock, denial, drift and rollback evidence PASS |
| PST-WC10 | WC07-WC09 | `deploy.yaml` lifecycle orchestration | INST-010 | INST-009; Founder retains provider action | INST-015 | Authorization tuple, emulator, holds and rollback matrix PASS |
| PST-WC11 | WC10 | Local verifier, protected PITR, prior-release, capacity and cost qualification | INST-010 | INST-006/007/009 by criterion | INST-015 | Emulator plus authorized restore/RPO/RTO/schema/cost evidence PASS |
| PST-WC12 | WC11 | Mandatory docs and Operations handoff | INST-010 | Owning offices and Platform Operations | INST-015 checks evidence completeness | Owning records and alerts match executable behavior |
| PST-WC13 | WC12 | Author review and exact-head PR | INST-010 | Founder | Automated gates; requested institutional reviews only | Prepared body and all remote-head gates PASS |
| PST-WC14 | WC13 | Founder handoff | INST-010 | Founder | Founder-selected assurance | PR ready; no self-approval/merge/deploy claim |

No component starts while a dependency is incomplete or its exit oracle is partial.
Author evidence never substitutes for independent verification or acceptance.

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
- the lifecycle state machine resumes safely after interruption and rejects concurrent/different actions;
- every provider action verifies the immutable authorization tuple;
- Entra-only Plan A and reviewed Plan B pass all password/secret/principal negative tests;
- tenant context, FORCE RLS, NOBYPASSRLS and PgBouncer reset denial tests pass before and after restore;
- each sidecar dataset has a reconciled cutover/disposition row;
- UAT uses Temporal Cloud, its own valid environment authorization/configuration/dependency tuple,
  and the exact Founder-accepted Demo application/schema/migration identity;
- automatic database restart is detected and safely reconciled;
- migration is additive, idempotent and readable by the previous qualified release;
- restore meets accepted RPO/RTO with sanitized evidence;
- restore proves RPO <= 5 minutes and RTO <= 30 minutes under independent verification;
- capacity remains below the accepted 80% aggregate ceiling;
- exact-seven release identity remains unchanged and dependencies are separately pinned;
- no secret appears in plan/state/log/artifact;
- all selected Docker, CI, security, constitutional and Test Champion gates pass;
- the Skill 17 local Azure verifier exists and its retained runtime artifact passes;
- exact-head author review is PASS and the Founder receives the PR.

## 19. Rollback

Rollback binds the prior complete immutable tuple: exact-seven application digests, configuration
digest, dependency/PgBouncer manifest, schema compatibility, migration digest/watermark,
secret-catalog digest, environment authorization tuple and evidence identity.
The prior qualified revision remains retained at zero traffic for at least 24 hours and through the
active Demo/UAT lease, whichever is later. Rollback never rebuilds, retags or destructively migrates.
Additive schema rolls forward; the prior release must already prove readability.

Terraform partial apply enters `RECOVERY_HOLD`, refreshes/imports actual state, retains the reviewed
plan and reconciles by a new reviewed roll-forward plan. It never guesses rollback or deletes an
unknown resource. The database, PgBouncer, Key Vault, state and backups remain. A failed activation
returns applications and dependencies to zero and leaves PostgreSQL in the safest verified state.
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
