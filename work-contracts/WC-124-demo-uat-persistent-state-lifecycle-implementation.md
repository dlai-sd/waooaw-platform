# WC-124 - Demo/UAT Persistent State Lifecycle Implementation

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-124 |
| GitHub Work Contract | Issue #521 |
| Status | IMPLEMENTATION_AUTHORIZED |
| Founder authority | FA-055 plus explicit current-session implementation authorization on 2026-10-16 |
| Implementing office | Platform IT Expert (INST-010), Skill 17 |
| Source Work Component | `architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md` v1.1.0-candidate.2 |
| Source acceptance | PR #520 merged as `5a849683abec38ebb6d9d72b37b211d8a3376806` |
| Requirement ledger | `work-contracts/WC-124-requirements.yaml` |
| Owner input package | `work-contracts/WC-124-persistent-state-inputs.yaml` |
| Owner input package SHA-256 | `210b18e540c60dc7a0b530b7ca7220e5c5468067a4fa3cebccfece1b9232604c` |
| Input gate | **CLEAR — all 15 inputs resolved; `implementation_may_begin=true`; CB-020 CLOSED** |
| Release Qualification | OFF by explicit current-session Founder authority |
| Result | PLANNED |

Issue #521 is the implementation Work Contract. This repository mirror supplies the digest-bound
canonical requirement index required by `validation/process-control.yaml`. FA-055 and the accepted
Work Component control any conflict.

## Authority And Scope

Implement PST-WC00 through PST-WC14 for Demo and UAT only:

- migrate Billing halt, release, reconciliation, audit, outcome and idempotency authority to
  PostgreSQL;
- create the accepted PostgreSQL Flexible Server, PgBouncer, principal, RLS, private-network,
  Terraform-state and private-runner contracts;
- cut over CE, BP, Billing and Demo Temporal datasets and remove cloud authority sidecars;
- implement retained-data sleep, explicit activation, lifecycle evidence, holds and reconciliation;
- extend the existing `ci.yaml` and `deploy.yaml` delivery paths;
- prove security, tenant isolation, recovery, capacity, cost and rollback behavior;
- update mandatory owning records and prepare an exact-head Founder-ready PR.

No real Azure query, plan/apply, deployment, restore qualification, DNS, traffic admission,
activation, Production action, approval or merge is authorized. Each such action requires separate
current Founder authorization.

## Inputs

- Issue #521, FA-055 and the accepted Work Component.
- `architecture/reference/components/environment-readiness-and-data-continuity.md`.
- `architecture/reference/pipeline/azure-deployment-topology.md`.
- ADR-010, ADR-011, ADR-013, ADR-014, ADR-015, ADR-034 and ADR-047.
- Existing accepted data, security, recovery, role/RLS, Billing and release contracts.
- Demo/UAT only; Production must produce no change.
- PostgreSQL authority and backups remain retained during sleep; routine deletion is prohibited.
- Backup retention 35 days; RPO <= 5 minutes; RTO <= 30 minutes.
- PostgreSQL connection limits 40/100 and PgBouncer client limits 40/80 for Demo/UAT.
- Planned aggregate capacity above 80% blocks activation.
- Sleeping cost target INR 700-3,200/month before GST; active plans fail closed above FA-052's
  INR 10,000 monthly envelope.
- Exact-seven application release identity remains unchanged.
- Demo retains self-hosted Temporal; UAT retains Temporal Cloud under ADR-015.
- `deploy.yaml` remains the only mutation entry.
- Existing protected lifecycle-evidence storage remains the control record location.
- Exact provider SKU, storage, availability, versions, PgBouncer build-and-pin contract,
  resources/timeouts, role/secret catalogue, dataset treatment, runner/state prerequisite and
  environment authorization tuples are accepted in the digest-bound owner package.
- Provider-operation release SHA, plan digest, runner execution identity, lease/expiry and the
  PgBouncer, extended-catalog, restore and promotion digests are generated evidence under closed
  pre-access contracts. They are not fabricated present values or missing design inputs.
- Live ADR-047 runner/state ownership remains the mandatory PST-WC09A exit prerequisite; its
  acceptance here does not claim that live evidence already exists. PST-WC04 cannot start until
  every PST-WC09A oracle passes.
- CB-020 is closed and PST-WC01 may begin under the existing implementation authority. This owner
  pass does not authorize provider access, plan/apply,
  deployment, restore qualification, traffic, UAT acceptance, Production, approval, or merge.

## Owner Decision Closure

The Founder-authorized integrated INST-009/INST-006/INST-007 decision pass accepted all fifteen
technical inputs in `work-contracts/WC-124-persistent-state-inputs.yaml`, SHA-256
`210b18e540c60dc7a0b530b7ca7220e5c5468067a4fa3cebccfece1b9232604c`.
The package is controlling in full; extracting a value without its rationale, source constraints,
acceptance statement, rollback/stop condition and package-evidence classification is invalid.

The package distinguishes exact owner decisions from values that can exist only during a later
authorized operation:

- PgBouncer is pinned to
  `docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9`
  from the Founder-authorized read-only public manifest lookup; tag-only use and fabricated digests
  remain prohibited.
- protected-workflow release, plan, runner, lease and expiry fields must be generated and validated
  as one immutable environment tuple before provider access;
- target-specific restore fixtures/points and UAT promotion digests must be generated, signed and
  accepted at their later gates; no current restore or UAT acceptance is claimed; and
- PST-WC09A must produce live runner/backend ownership, isolation, denial, import, drift,
  partial-apply and Storage-account-separation evidence before PST-WC04.

## Canonical Requirement Index

| Requirement | Normative obligation | PST component |
|---|---|---|
| WC124-R001 | Preserve the complete authority boundary, Release Qualification OFF control and separate protected-action gates. | PST-WC00 |
| WC124-R002 | Refresh PST-001 through PST-013 against the exact implementation head and bind every gap to source and a falsifying test. | PST-WC01 |
| WC124-R003 | Prove or implement ADR-047 private-runner identity, isolated Terraform state, locking, denial, drift, import and rollback prerequisites. | PST-WC09A |
| WC124-R004 | Implement one protected private PostgreSQL Flexible Server per Demo/UAT environment with accepted retention, sizing inputs, lifecycle protection and no Production delta. | PST-WC04 |
| WC124-R005 | Implement Entra-only Plan A, databases, NOLOGIN owners, schemas, roles and Key Vault references without workload credentials or traffic. | PST-WC05 |
| WC124-R006 | Implement reviewed Plan B compatibility enablement and remove bootstrap access before activation. | PST-WC05 |
| WC124-R007 | Enforce separate migration/runtime principals, NOBYPASSRLS, FORCE RLS, revoked PUBLIC grants and transaction-local tenant context reset. | PST-WC05 |
| WC124-R008 | Deploy one digest-pinned private PgBouncer dependency per environment with transaction pooling, zero-idle scaling and saturation/readiness telemetry. | PST-WC05 |
| WC124-R009 | Enforce and test the complete private/public/direct/foreign-environment network denial matrix without public fallback. | PST-WC05 |
| WC124-R010 | Add expand-only Billing integrity, release, reconciliation, outcome, discrepancy, evidence and audit PostgreSQL objects and constraints. | PST-WC02 |
| WC124-R011 | Atomically commit discrepancy, evidence, outcome and integrity halt for amounts above one paise with explicit boundary behavior. | PST-WC03 |
| WC124-R012 | Make halt release append-only, authorized and evidence-bound; uncertain or missing authority must fail closed. | PST-WC03 |
| WC124-R013 | Implement canonical reconciliation identity, deterministic digest, durable claim states, replay/conflict and crash recovery semantics. | PST-WC03 |
| WC124-R014 | Prove Redis cannot create, clear or outlive authority and that permitted projections rebuild without changing outcomes. | PST-WC03 |
| WC124-R015 | Remove cloud PostgreSQL/Billing Redis/Temporal PostgreSQL sidecars, local authority volumes, localhost routes and shared superuser credentials. | PST-WC06 |
| WC124-R016 | Complete the dataset-level CE/BP/Billing/Demo-Temporal cutover ledger, write fences, reconciliation, retention and rollback points before removal. | PST-WC06 |
| WC124-R017 | Implement signed hash-chained lifecycle evidence, one environment lock, idempotent resume, bounded retries and fail-closed hold states. | PST-WC07 |
| WC124-R018 | Implement retained-data sleep in the specified drain-to-database-stop order with protected-resource, backup, watermark, cost and restart-reconciliation gates. | PST-WC07 |
| WC124-R019 | Implement activation in the specified database-to-traffic order, without rebuild or traffic before independent verification. | PST-WC08 |
| WC124-R020 | Bind UAT promotion to Founder-accepted Demo application/schema/migration identity while retaining UAT-specific Temporal/configuration dependencies. | PST-WC08 |
| WC124-R021 | Verify every provider operation against the immutable per-environment authorization tuple and deny each independently mutated field before access. | PST-WC08 |
| WC124-R022 | Extend `ci.yaml` change planning and all topology, secret, migration, RLS, Billing, lifecycle, recovery, security, authorization, network, release and constitutional gates. | PST-WC09 |
| WC124-R023 | Enforce connection calculations, 80% capacity ceiling, retention, RPO/RTO and cost thresholds as blocking evidence. | PST-WC09 |
| WC124-R024 | Extend `deploy.yaml` plan to authorize, bind and retain immutable non-destructive private foundation/dependency/workload plans and cost inventory. | PST-WC10 |
| WC124-R025 | Extend `deploy.yaml` activate to enforce exact sequencing, holds, promotion identity and independent traffic admission. | PST-WC10 |
| WC124-R026 | Extend `deploy.yaml` sleep to reverse dependencies while retaining authority, state, secrets, backups and evidence. | PST-WC10 |
| WC124-R027 | Implement Docker recovery fixtures, additive migration compatibility, sanitized restore, role/RLS, constitutional and financial reconciliation tests. | PST-WC11 |
| WC124-R028 | Reserve real Azure plan/apply, deployment, PITR restore qualification and traffic proof for separate exact Founder authorization. | PST-WC11 |
| WC124-R029 | Restore or implement the pinned Docker Azure CLI emulator verifier and run focused verification plus one final local rehearsal. | PST-WC11 |
| WC124-R030 | Implement evidence immutability, emergency-stop reachability, forged-chain rejection and writer/verifier separation tests. | PST-WC11 |
| WC124-R031 | Implement lifecycle, backup, PgBouncer, migration, route, cost and evidence observability with redaction, retention, ownership and escalation. | PST-WC12 |
| WC124-R032 | Bind rollback to the complete immutable prior tuple, preserve additive schema and enter recovery hold on partial/uncertain infrastructure state. | PST-WC11 |
| WC124-R033 | Update only mandatory owning documentation, inventories, runbooks, alert catalogues and implementation evidence after executable qualification. | PST-WC12 |
| WC124-R034 | Complete exact-head author review, mandatory engineering candidate qualification, PR preparation and Founder handoff without self-approval, merge, deployment or activation claims. | PST-WC13 / PST-WC14 |

Dependencies are exactly those in Work Component section 17. No PST component starts before every
dependency is complete and its exit oracle passes.

## Definition Of Done

Every acceptance oracle in Work Component section 18 is either:

1. PASS with direct repository-owned Docker/catalog evidence on the exact candidate; or
2. `FOUNDER_RESERVED` only where the oracle requires real Azure/provider action that remains outside
   this session's authority.

Mandatory engineering candidate qualification, security, privacy, migration, rollback, same-image,
PR prechecks, author review, C-059, C-065 and required CI remain blocking. Release Qualification is
not run under the exact current-session Founder authority.

The final remote HEAD equals the local HEAD, branch HEAD, PR head and reviewed commit. The PR is
handed to the Founder and is not approved, merged, deployed, activated or admitted to traffic by the
implementer.

## Rollback Boundary

Rollback binds the prior complete immutable application, configuration, dependency/PgBouncer,
schema, migration, secret-catalog, environment-authorization and evidence tuple. It never rebuilds,
retags, destructively migrates or deletes unknown infrastructure. Partial apply or uncertain state
enters `RECOVERY_HOLD` and requires a new reviewed roll-forward plan.

## Stop Conditions

Stop on:

- a missing/conflicting accepted input, architecture decision, exact SKU/version/digest/role/secret
  catalogue, dataset disposition, runner/state ownership or authorization tuple;
- provider access or mutation without exact current authority;
- destructive or Production plan delta;
- secret exposure in source, plan, state, log, artifact or evidence;
- direct/public database route or cross-environment authority;
- uncertain Billing halt, migration or reconciliation outcome;
- inability to prove Redis-loss safety, recovery objectives or rollback;
- capacity or cost threshold breach;
- two reproducible infrastructure failures;
- conflicting unrelated user changes, process-control mismatch or exact-head mismatch;
- a requested quality-gate exception, self-approval, self-merge or inferred deployment authority.
