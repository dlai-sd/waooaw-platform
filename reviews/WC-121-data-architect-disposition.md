# WC-121 Data Architect Disposition

## Record

| Field | Value |
|---|---|
| Institution | INST-006 — Data Architect, Office 06 |
| Review | Founder-requested single-pass review-and-repair |
| Scope | WC-121 solution contract, additive API, implementation Work Contract, and requirement-evidence ledger |
| Date | 2026-10-13 |
| Enterprise requirements | Reviewed and intentionally unchanged |
| Authority | Architecture/specification only; no schema, implementation, provider, deployment, traffic, activation, approval, or merge authority |
| Disposition | **BLOCKED on external recovery decisions and existing acceptance/authority gates** |

## Data Decision Space

This review covers data strategy, persistence patterns, event/idempotency flow, ledger separation,
data lifecycle, migration, and recovery semantics. It does not design physical schemas or select
infrastructure. The Constitutional Audit Ledger remains append-only and separate from Business and
Professional ledgers.

## Findings and exact repairs

| Finding | Blocking risk | Repair |
|---|---|---|
| New persisted data classes lacked a complete owner/write-boundary map. | Implementers could create a second truth store or copy identity, relationship, conversation, provider, or evidence data. | CSA-CEW-001 10.5 now limits persistence to accepted owners and defines permitted preference, coordinator/result, projection metadata, focus metadata, session result, and CE evidence classes. WC-121 Section 8 requires an owner inventory. |
| “One transaction or recoverable saga” did not define the distributed atomicity boundary. | Partial relationship/agent/conversation/workspace/evidence state could be presented as success. | CSA-CEW-001 10.6 now requires reserve-before-effect, canonical digest, local relationship/coordinator/outbox transaction, restartable owner saga, durable receipts, evidence-first terminal success, and accepted-owner-only compensation. |
| Idempotency did not fully define key scope, divergent replay, concurrency, expiry, or stored outcome. | Retry races could duplicate owner effects or lose the original result. | CSA-CEW-001 10.6 and WC-121 Section 8 define scoped key/digest reservation, monotonic states, replayable terminal result, stable child-owner identities, conflict with zero new effects, and permanent first-mint protection through owner uniqueness. |
| Progress had a projection version but insufficient source provenance and invalidation semantics. | Stale or unsupported owner facts could drive “current” progress or next action. | CSA-CEW-001 10.7 defines source-version vectors and invalidation triggers. The additive API now requires per-source and per-item owner, subject, source/contract versions, timing, validity, freshness, and evidence state/reference plus a projection contract version. |
| Focus-token persistence and lifecycle were underspecified. | Tokens could outlive authority, leak protected data, survive key rotation incorrectly, or become evidence. | CSA-CEW-001 10.8 sets a 15-minute maximum, non-extension, minimal claims, current-authority resolution, invalidation events, rotation overlap, fingerprint-only observability, bounded revocation metadata, and explicit non-evidence status. API descriptions reflect these constraints. |
| Tenant isolation did not bind every new data path, maintenance, or restore operation. | Path/body/provider values or background work could cross tenant boundaries. | CSA-CEW-001 10.5 and WC-121 Section 8 require trusted-context tenant binding, relationship/participant composite binding, forced RLS read/write checks, tenant-scoped maintenance/reconciliation, and separate CE audit authority. |
| Retention, correction, erasure, hold, export, and purge behavior were generic. | Data might be over-retained, erased contrary to evidence rules, or restored after erasure. | CSA-CEW-001 10.9 adds a data-class disposition matrix. WC-121 requires an accepted owner, duration, lifecycle action, hold override, purge evidence, and export behavior for every class; missing policy is a stop. |
| Migration language lacked staged cutover and deterministic mixed-version behavior. | Old readers, partial backfills, dual writes, or rollback could corrupt meaning. | CSA-CEW-001 10.10 and WC-121 Section 8 require expand/backfill/verify/cutover/contract, tenant-bounded restartable backfill, quarantine, one dual-write authority, divergence alarms, unsupported-version `UNAVAILABLE`, and separately authorized contraction. |
| Backup/restore scope and recovery consistency were absent. | Restore could break evidence links, duplicate effects, revive revoked focus, or resurrect erased data. | CSA-CEW-001 10.11 and WC-121 Section 8 define backup coverage, tenant/encryption preservation, referential restore checks, cache rebuild, non-resurrection, write reopening only after reconciliation, and an objective-bound restore rehearsal. |
| Reconciliation ownership and evidence were incomplete. | Stuck sagas, orphan effects, outbox gaps, stale projections, purge failures, or evidence gaps could remain silently unresolved. | CSA-CEW-001 10.12 defines tenant-scoped lease-safe reconciliation and quarantine. WC-121 Section 8 requires direct redacted crash, replay, invalidation, lifecycle, migration, restore, and reconciliation evidence. |
| Channel-session end required evidence but its API outcome exposed no evidence reference. | A successful response could not bind to the committed evidence conclusion. | `ConversationChannelSessionOutcomeV1` now requires an opaque `evidenceRef`. |
| The canonical ledger had no independently tracked data-readiness obligation. | Data controls could be diluted across broad security/migration requirements. | WC-121 adds `WC121-R019`; the requirement ledger adds a direct, initially blocked data qualification record and detailed oracle plan. |

## Unresolved external dependencies and mandatory stops

1. **Recovery objectives:** Numeric RPO, RTO, backup retention, regional-copy policy, and
   recovery-environment authority require accepted Platform Architecture/Founder decisions. Data
   Architecture has defined required semantics but has not invented these values.
2. **Owner lifecycle policies:** Implementation impact analysis must bind every affected class to
   already accepted Identity, Onboard, Conversation, BP, owner, and CE retention/erasure/hold
   policies. Any absent policy stops the owning component.
3. **Physical design:** Tables, columns, indexes, migrations, jobs, storage engines, backup
   products, and infrastructure configuration remain implementation/Platform decisions subject to
   impact analysis and explicit current-session implementation authority.
4. **Candidate acceptance:** Founder acceptance of the exact candidate package and digests remains
   open. This review does not accept the package on the Founder's behalf.
5. **Implementation authority:** No source or generated implementation artifact is authorized.
6. **Live capability:** Provider, cloud, deployment, external traffic, activation, PR approval, and
   merge gates remain independently blocked exactly as stated in CSA-CEW-001 and WC-121.

## Focused evidence required before Data PASS

- Contract/OpenAPI/ledger structural validation and digest agreement.
- Owner inventory with no new store or fourth ledger.
- Concurrency and crash injection at every admission/coordinator/outbox/owner/evidence boundary.
- Identical and divergent replay across Portal and WhatsApp.
- Projection provenance, invalidation, stale/unavailable behavior, and deterministic rebuild.
- Focus expiry, revocation, Stop, authority/source-version invalidation, and key rotation.
- Forced-RLS read/write/maintenance/reconciliation/restore cross-tenant negatives.
- Retention, correction, erasure, hold, export, purge, and non-resurrection qualification.
- Expand/backfill/mixed-version/rollback qualification.
- Encrypted backup/PITR restore against accepted RPO/RTO and post-restore reconciliation.

## Disposition

**BLOCKED.** The Data-owned specification gaps identified in this pass are repaired. WC-121 remains
blocked from implementation acceptance until the external recovery objectives and owner lifecycle
policies are accepted and their direct evidence passes. Existing Founder acceptance,
current-session implementation, live-provider, cloud, deployment, traffic, activation, approval,
and merge gates are unchanged.
