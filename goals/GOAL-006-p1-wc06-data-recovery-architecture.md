# GOAL-006 P1-WC06 Data Isolation, Recovery, Retention, And Migration Architecture

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-006 — Data Architect |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-006-01 |
| `record_type` | Contribution Record |
| `go_authorization` | GOA-GOAL-006-INST-006-01 |
| `acceptance_record` | ACC-GOAL-006-INST-006-01 |
| `work_component` | P1-WC06 — Data Isolation, Backup, Restore, Retention, And Migration |
| `status` | ACCEPTED — R-112 / CR-GOAL-006-INST-005-02 |
| Accepted dependencies | P1-WC01, P1-WC03, P1-WC04, P1-WC05; R-107, R-109, R-110, R-111 |

## Authority And Evidence Boundary

INST-006 defines data isolation, classification, persistence, backup, restore, retention, migration,
recovery recommendations, and deterministic data tests. It cannot overwrite PA-01 through PA-08,
component topology, or P1-WC05; design concrete schemas/migrations; select keys or credentials;
accept Production RPO/RTO, retention, legal, cost, regional, or residual-risk decisions; implement,
deploy, query providers, change DNS, activate operations, approve, merge, or self-review.

Live cloud, database, identity, workflow, cache, registry, state, certificate, backup, customer-data,
and Production conditions are `UNVERIFIED`. Repository declarations are not effectiveness evidence.

## Immutable Reuse

Evidence First, append-only transitions, three-ledger separation, additive correction, JWT-derived
tenant authority, current authoritative relationship checks, additive constitutional migrations,
same-digest compute recovery, environment isolation, and P1-WC05 security custody are preserved.
A restore preserves record IDs, action grouping, tenant/relationship binding, versions, basis,
ordering, source timestamps, and lineage. Recovery may append an event; it never rewrites source facts.

## Environment Model

| Environment | Permitted | Prohibited | Recovery treatment |
|---|---|---|---|
| Development | Synthetic fixtures/approved developer test data | Production payloads, identities, workflows, secrets, telemetry | Deterministic recreation only |
| Demo | Synthetic by default; approved irreversible anonymization | Production payloads, reversible pseudonyms, credentials, identity/workflow exports | Isolated backup/restore; JIT shutdown preserves durable state |
| UAT | Synthetic representative data; approved irreversible anonymization | Production payloads/IDs/secrets/snapshots/workflows | Isolated PITR/restore for migration and recovery qualification |
| Production | Authorized customer, professional, constitutional, operational, commercial data | Lower-environment identities/credentials/test truth | Strongest accepted protection; no destructive lifecycle |
| Delivery plane | Source, config, manifests, SBOM, provenance, signatures, scans, tests | Customer payloads, secrets, keys, tokens, state contents | Integrity recovery without changing digest identity |

No Production database, backup, export, snapshot, WAL, Keycloak export, Temporal history, Redis dump,
telemetry, index/vector set, secret export, or customer file may move to a lower environment.
Synthetic data must not derive from identifiable Production subjects. Irreversible anonymization
requires recorded proof covering free text, rare combinations, time, location, media, embeddings, and
linkage keys. Masking, hashing low-entropy IDs, encryption, or reversible pseudonyms do not qualify.

## Isolation And Classification

`tenant_id` comes only from validated authentication/delegation and is set transaction-locally for
every tenant-scoped database transaction. Pooling resets context each transaction. Missing, stale, or
mismatched context returns no rows, counts, timing hints, exports, or mutation success. Relationship
scope is independently resolved and binds projections, workflows, evidence, billing, exports, caches,
and cursors.

| State class | Authority and recovery invariant |
|---|---|
| Constitutional PostgreSQL | CE-owned INSERT/SELECT evidence; encrypted PITR; no logical record update/delete/rekey/down-migration |
| Business/customer PostgreSQL | RLS-governed facts and correction lineage; Production never copied down |
| Professional Experience | Preserve identity and ownership; never merge or reassign on restore |
| Billing | Preserve tenant, idempotency, actual/forecast distinction, reconciliation lineage |
| Institutional learning | Separate authority; only approved anonymized/aggregate content |
| pgvector/customer vectors | Compatible extension; source-equivalent sensitivity/retention; rebuild only with exact provenance |
| Keycloak | Versioned config plus protected environment identity state; revoke invalid restored sessions |
| Temporal | Durable sensitive history; reconcile external effects and prevent duplicate execution |
| Redis | Transient by default; flush/rebuild unless an accepted contract proves durability |
| Ollama | Pinned weights reconstructible; prompts/context not persisted by default |
| Telemetry | Sensitive operational data; never ledger authority or lower-environment fixture |
| Terraform state/plans | Sensitive isolated control-plane metadata; encrypted locked version recovery; plans short-lived |
| GitHub/GHCR evidence | Preserve commit, manifest, digest, SBOM, provenance, signature, scans, approvals, history |
| Certificate/secret metadata | Preserve references/version/status only; values and keys remain under P1-WC05 custody |

## Encryption And Recovery Boundaries

Backups, archives, state, exports, and restore channels are encrypted in transit and at rest.
Environment-scoped recovery identities do not imply application, deployment, state-admin, or secret
authority. Recovery metadata may carry key references/versions, never values. Restore preflight proves
required key versions are available; ambiguity or decryption failure fails closed. Rotation preserves
required decryptability until lawful expiry. Production restore follows P1-WC05 authority/break-glass.
Security-authorized infrastructure key rotation or physical re-encryption is permitted only when
logical record identity, content, ordering, lineage, and retained-backup decryptability remain unchanged;
it may never masquerade as an evidence correction or rewrite.

**Compute Recovery** reapplies reviewed IaC and a qualified OCI digest/configuration pair, recreates
stateless services, and verifies manifest, health, boundaries, and config. It does not restore data.

**Data Recovery** restores environment-isolated authoritative state to an approved point, verifies
chain/encryption/checksum/source/compatibility, restores durable classes in dependency order,
reconciles PITR, workflows, evidence tails, billing idempotency and uncertain external effects, and
reopens writes only after integrity and constitutional checks. Service health proves neither path.

## Backup, PITR, And Evidence Tail

PostgreSQL uses encrypted full backups plus WAL sufficient for PITR. Chains, archives, manifests, and
evidence remain environment-isolated. Preflight verifies checksum, continuity, source, key reference,
database/extension version, and restorable point. Restore first targets an isolated recovery boundary.
Schemas sharing a PostgreSQL boundary form one consistency group unless an accepted contract proves
otherwise. Production recovery tests use an authorized Production-class isolation boundary or an
approved synthetic equivalent, never a lower environment.

A restored point is compared to independently retained evidence and release watermarks. Missing
committed evidence, identifier gaps, broken lineage, or terminal-state conflicts block writes. Tails
are replayed from accepted archives/replicas, never synthesized. Unrecoverable committed evidence is a
Constitutional Blocker, not ordinary RPO loss. Recovery appends Evidence First records when safe.

Keycloak configuration is promoted from reviewed config and reconciled with environment identity.
Temporal state is reconciled with application data; uncertain workflows remain paused until
idempotency, evidence, and external outcomes are resolved. Recovery cannot revive stale authority or
duplicate billing, actions, approvals, schedules, or evidence.

Terraform recovery restores the exact backend generation under locking. GitHub/GHCR retain each
digest needed by an active environment, rollback, incident, hold, or review. Rebuilding the same source
does not replace a lost digest.

## Retention, Hold, Deletion, Export

No new or general statutory/customer retention duration is accepted here. Previously accepted
class-specific lifecycle constraints remain controlling, including WC-062 voice payload, transcript,
quarantine, backup, and cache limits of 24 hours, 30 days, and 7 days according to that contract's
defined classes and conditions; those values are not generalized to other GOAL-006 data. Product,
Legal, Security, cost, and Founder decisions remain required where protected. Constitutional
correction/deletion/erasure adds
evidence; it never rewrites the ledger. Customer data follows purpose-bound minimum lifecycle;
Professional Experience preserves ownership; Billing follows authoritative Billing/Legal policy;
telemetry uses the shortest approved diagnostic/security/SLO period; reconstructible artifacts exist
only while useful and reproducible.

A legal/constitutional hold is Evidence First, exactly scoped, separately authorized, and suspends
only covered deletion/expiry. It grants no access or cross-environment movement. Deletion is
idempotent and reports completed, pending reconciliation, hold-blocked, authorized-scope not-found, or
failed. It cannot report success before authoritative completion. Restores reapply later deletion,
hold, revocation, termination, and correction events before customer access.

An export is tenant/relationship-authorized, manifest-bound, integrity-verifiable, encrypted,
expiring, and logically separates ledgers. It names scope, owners, versions, included/excluded classes,
integrity values, and evidence references. It contains no unrelated tenant, secret, key, topology, or
prohibited payload and does not become a source of truth or authorize erasure/migration/import.

## Migration And Same-Digest Compatibility

ADR-011 controls: EF Core owns application migrations; init completes before dependents; constitutional
change is additive; destructive operations/down-migrations are prohibited; pgvector is provisioned as
an environment prerequisite; Python services gain no schema ownership.

Each migration binds predecessor, release digest/config, supported source/target versions,
PostgreSQL/extensions, verified recovery point, forward/rollback behavior, lock/capacity/failure,
RLS/permission impact, immutable scan, and tenant/relationship/billing/identity/workflow/vector/export/
deletion/hold tests. Business schemas use expand/contract. Constitutional faults use additive forward
fixes; application rollback occurs only when the old digest reads the current additive version.

Every restore/rollback tuple is `manifest + OCI digests + reviewed config + data version + state
generation + recovery point`. Mandatory Billing membership, signatures, non-secret config, key/cert
references, and migration compatibility must verify. Missing or mutable identity fails closed.

## Recovery Objective Recommendations

**All values are `RECOMMENDATION NOT ACCEPTED`, not commitments or deployed capability.**

| Tier | State | Demo/UAT recommendation | Production recommendation |
|---|---|---|---|
| DR-0 | Constitutional evidence, authority history, committed billing/action evidence | RPO ≤15m; RTO ≤4h | RPO ≤5m; RTO ≤60m; committed loss is a Constitutional Blocker |
| DR-1 | Business/professional DB, Keycloak identity, active Temporal | RPO ≤60m; RTO ≤8h | RPO ≤15m; RTO ≤2h |
| DR-2 | Terraform, manifests, attestations, cert/secret metadata | RPO ≤15m; RTO ≤4h | RPO ≤15m; RTO ≤2h |
| DR-3 | Incident/SLO telemetry | RPO ≤24h; RTO ≤8h | RPO ≤60m; RTO ≤4h |
| DR-4 | Proven reconstructible caches/indexes/models | No backup; RTO ≤4h | No backup; RTO ≤2h |

Data recommends; Platform proves feasibility/cost; QA measures; component owners validate; Founder
accepts protected Production tradeoffs. Shared boundaries use the strictest accepted objective.
Recommended drills: persistence-changing releases in Demo/UAT; isolated DR-0/1 PITR every 30 days;
complete Production-class data/compute recovery and state recovery every 90 days; verified point before
Production migration; rerun after relevant failure/change. Cadences are also NOT ACCEPTED.

Drill evidence records authority, isolated target, source class, chain/point, key references, digest,
config/data/state versions, measured RPO/RTO, checksums, ledger/RLS/tenant/relationship/billing/identity/
workflow/vector/deletion/hold/export results, deviations, cleanup, reviewer, and proof no Production
data entered lower environments.

## Deterministic Test Matrix

| Tests | Required proof |
|---|---|
| DATA-01–03 | Authenticated transaction-local tenant/RLS, pool reset, relationship context; no cross-scope rows/counts/timing/cache/vector/export |
| DATA-04–05 | Constitutional destructive operations fail; IDs, lineage, basis, ordering, terminal states survive PITR |
| DATA-06–07 | No Production class below Production; anonymization fails on any re-identification path |
| DATA-08–09 | Chain/checksum/encryption/source/PITR/extension verify; evidence-tail loss blocks writes |
| DATA-10–11 | Keycloak isolation/session revocation; Temporal recovery prevents duplicate effects and pauses uncertainty |
| DATA-12–13 | Redis is non-authoritative; vector rebuild uses exact source/model/config/tenant and lifecycle |
| DATA-14–16 | State recovery/no secrets; exact GHCR evidence; compatible immutable recovery tuple |
| DATA-17–18 | Supported additive migrations and rollback readability; prohibited operations rejected automatically |
| DATA-19–21 | Deletion propagation, exact hold scope, and post-restore lifecycle replay |
| DATA-22–23 | Complete isolated export; no secret/key/token in recovery/export/evidence surfaces |
| DATA-24–26 | RPO/RTO measured from authoritative boundaries; termination and identity continuity survive recovery |
| DATA-27–28 | Billing idempotency/lineage; telemetry redaction and tenant isolation |

P1-WC08 may consolidate IDs but must preserve every proof and gate effect.

## Phase 2 Blockers And Protected Decisions

Open blockers: encrypted backup/PITR/drills; CT-06 direct/PgBouncer and transaction-local RLS client
contract; non-production data provenance gate; PostgreSQL/Keycloak/Temporal/Billing/evidence recovery
ordering; evidence-tail verification; state recovery; automated migration prohibitions; immutable
digest/data compatibility; retention/hold/deletion; export; key/cert recovery; GHCR/GitHub retention;
Redis/vector/Ollama classification; accepted Production objectives; and live-state qualification.
CT-01 and CT-05 remain future Phase 2 blockers outside Data Architecture. No blocker authorizes repair.

Founder retains Production objectives/residual risk, regions, spend, DNS, activation, break glass,
phase authorization, approval, merge, and Operations activation. Security owns custody/access;
Platform owns service integration/storage/state/capacity/cost; component owners own health and
compatibility; Product/Legal own customer-visible lifecycle and law; QA owns measured qualification.

Unknowns include all live backups, WAL, replicas, restore points, retention/encryption/state/vault
settings, drills, deployed versions/topology, schema/client/pooling/volume/workload/migration history,
customer/legal records, Production objectives/cost/region, Redis durability, vector reproducibility,
Keycloak/Temporal compatibility, and GitHub/GHCR retention. No recommendation is implemented,
measured, independently reviewed, or accepted.

## Completeness And Contribution Record

Environment model, no-Production-data rules, isolation, all named data classes, encryption interfaces,
backup/PITR/evidence tails, retention/hold/deletion/export, migration/rollback, compute-versus-data
recovery, same-digest compatibility, objective recommendations, drills, tests, blockers, protected
decisions, and unknowns are complete at design level. Live effectiveness and Production readiness are
not established.

| Field | Value |
|---|---|
| Contribution | CR-GOAL-006-INST-006-01 |
| Materiality | M2 — specialist Data Architecture contribution |
| Data verdict | DESIGN REQUIREMENTS DEFINED; IMPLEMENTATION/LIVE/PRODUCTION UNVERIFIED |
| RPO/RTO verdict | RECOMMENDATION NOT ACCEPTED |
| Residual risk | IDENTIFIED, NOT ACCEPTED |
| Implementation/cloud/DNS/Production authority | NOT GRANTED |
| Self-review | NOT PERFORMED |
| Required review | Independent architecture coherence and constitutional evidence/isolation validation |
| Downstream effect if accepted | Satisfies P1-WC06 for P1-WC07 only; does not unblock Phase 2 or Phase 3 |
