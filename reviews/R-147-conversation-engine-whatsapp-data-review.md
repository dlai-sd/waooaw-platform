# R-147 — Conversation Engine And WhatsApp Data Architecture Review

**Office:** Data Architect (INST-006)
**Review mode:** Founder-requested, single-pass institutional architecture review
**Branch:** `architecture/conversation-engine-whatsapp`
**Commit reviewed:** `f5bb9e4927a9946a98da78e265abdaad4ff46f91`
**Date:** 2026-10-12
**Verdict:** **CHANGES REQUIRED**

## Scope

This review evaluates whether the proposed Conversation Engine and WhatsApp enterprise architecture
defines sufficient data boundaries for the Chief Solution Architect to proceed without inventing
ownership or lifecycle semantics. It covers canonical ordering and concurrency; tenant/RLS
ownership; Context Profile fact and summary lineage; idempotency and provider-event deduplication;
delivery-state monotonicity; media, transcript, payload, and evidence separation; retention,
erasure, and legal hold; environment isolation; backup and recovery; and migration and rollback.

It does not review provider security, application component design, physical schema, endpoint design,
or implementation, except where those concerns expose a missing data decision.

## Evidence Read

- Compact Data office context requested for this review; no compact Data office card exists in the
  branch's `.github/agent-context/` set.
- Complete committed diff at `f5bb9e49`, including the ADR index and capability, container, context,
  and domain-model reference updates.
- `architecture/reference/components/conversation-engine-whatsapp-enterprise-architecture.md`,
  Sections 1–26.
- `adr/ADR-052-channel-neutral-conversation-context-policy.md`.
- `adr/ADR-053-whatsapp-environment-isolation-transport.md`.
- Directly cited controlling data decisions needed to test consistency:
  - `adr/ADR-003-jwt-claims-multi-tenancy.md`;
  - `adr/ADR-051-conversational-employment-workspace.md`;
  - `architecture/reference/data/relationship-workspace-data-contract.md`, Sections 1–3 and 7–13;
  - `architecture/reference/data/wc062-voice-data-contract.md`;
  - `architecture/reference/components/environment-readiness-and-data-continuity.md`,
    Sections 8 and 12.

## Findings

### BLOCKING

#### DA-B1 — The handoff still requires the Solution Architect to invent the data boundary

**Package references:** Sections 7, 15, 21, 22.8, 23, and 24.

Section 15 lists logical records and broad authorities, but does not establish the minimum data
boundary needed to decompose them: system of record versus projection, tenant/relationship and
environment keys, transactional boundaries, payload-store references, lifecycle owner, or recovery
owner. Section 22 nevertheless requires the Solution Architect to consume “data ownership
references from the Data Architecture contribution,” while Section 23 confirms that contribution
does not yet exist. Section 24 says the open values need not block Solution Architecture, but
configurability cannot resolve absent ownership and atomicity boundaries.

This is not a request for physical tables. It is a missing logical contract. In particular, BP,
Phone Identity, the BP transport projection, the voice boundary, CE, and the payload store can each
plausibly own parts of one inbound or outbound lifecycle; the package does not define which owner
atomically accepts, sequences, deduplicates, tombstones, restores, and reconciles each record.

**Required remediation:** Add a normative logical data-boundary matrix before Solution Architecture
begins. For every Section 15 record, identify the authoritative owner, durable store boundary,
mandatory tenant/relationship/environment binding, write authority, projection consumers,
transaction/consistency boundary, retention and erasure owner, legal-hold owner, and backup/restore
owner. State which cross-boundary references are opaque IDs or non-reconstructive hashes and which
operations require an outbox/inbox or equivalent atomic handoff. The values for retention duration
and RPO/RTO may remain configurable, but their owners and fail-closed semantics may not.

### HIGH

#### DA-H1 — Canonical sequencing and concurrent acceptance are not deterministic enough

**Package references:** Sections 5 (`EA-CE-01`), 10.2–10.3, 11, 15, 16, and 17
(`CE-FIT-01`, `CE-FIT-08`).

“BP assigns canonical sequence after durable acceptance” does not define whether acceptance,
idempotency reservation, pending-intent conflict detection, message append, sequence allocation, and
outbox publication are one transaction. It also leaves undefined the ordering scope, uniqueness
rule, treatment of sequence gaps, provider timestamp versus receipt order, and retry behavior after
an ambiguous commit response. Two independent submissions may be accepted, but no rule determines
their stable order under concurrent writers.

**Required remediation:** Define one monotonically increasing sequence per canonical conversation,
allocated by BP in the same transaction as idempotency reservation and canonical append, with a
unique `(tenant, relationship, conversation, sequence)` invariant. Define stable tie behavior,
provider timestamps as provenance rather than ordering authority, conflict serialization for a
protected subject, post-commit publication, and replay of the original committed result after an
ambiguous response.

#### DA-H2 — Tenant and RLS ownership is asserted but not carried through every record and worker

**Package references:** Sections 8.1, 10.1–10.3, 12.2–12.3, 13.4, 14.2, and 15.

Section 15 requires tenant RLS globally, but several listed records are described only by
relationship, conversation, provider, or environment identity. The package does not require
tenant-bound composite references, identify how callbacks and asynchronous workers obtain trusted
tenant context, or prohibit a provider reference from becoming a cross-tenant lookup key. This is
weaker than ADR-003's current membership-derived tenant context, transaction-local reset,
`FORCE RLS`, and non-owner/`NOBYPASSRLS` role rules.

**Required remediation:** Require every tenant-scoped row, uniqueness key, foreign-key path,
idempotency key, cursor, payload reference, and provider correlation to include or resolve through
the authenticated tenant and selected relationship. Specify tenant derivation for web requests,
provider callbacks, scheduled reconciliation, media retrieval, transcription callbacks, and
recovery jobs. Require transaction-local context reset, `ENABLE` plus `FORCE RLS`, non-owner
`NOBYPASSRLS` runtime roles, composite tenant-consistent references, and normalized zero-disclosure
denials. Provider IDs, phone proofs, message IDs, and environment names must never independently
select tenant data.

#### DA-H3 — Context Profile facts and derived summaries lack reproducible lineage contracts

**Package references:** Sections 5 (`EA-CE-05`), 8.1, 9.3, 10.1–10.2, 14.3, 15, and 20.

The package distinguishes confirmed facts, research, analysis, inference, correction, and summary,
but it does not define immutable observations versus the current profile projection; allowed status
transitions; promotion of inference or research into confirmed fact; dispute handling; or the exact
lineage of a summary. “Versioned and attributable” is insufficient to reproduce or invalidate a
summary after correction, erasure, source expiry, policy change, or model change.

**Required remediation:** Define an append-only fact/observation lineage and a replaceable current
profile projection. Each fact version must bind tenant, relationship, subject, fact type, status,
accountable source, source identity/version, observed/captured/confirmed times, validity, permitted
use, predecessor/supersession reason, and evidence reference where applicable. Define legal
transitions among researched, inferred, confirmed, disputed, stale, superseded, unavailable, and
erased. Each summary must record covered canonical sequence range or explicit source set and
digests, derivation contract/model/policy versions, produced time, sensitivity, predecessor,
invalidation reason, and rebuild status. A summary must never be the sole source of a fact.

#### DA-H4 — Idempotency and provider-event deduplication do not have a complete lifecycle

**Package references:** Sections 10.3, 11, 12.1–12.3, 13.4–13.5, 15, 16, 18, and 20.

The package names a durable provider-event ID, TTL, outcome reference, payload digest, and
idempotency key, but does not define namespace uniqueness, atomic reservation, conflicting-payload
behavior, TTL floor, lifecycle after payload erasure, retry after TTL, or recovery consistency.
Demo cleanup is allowed to clear deduplication state while retained unresolved attempts may still
exist. A replay arriving after dedup expiry could therefore append a second canonical message or
repeat a professional action.

**Required remediation:** Define separate inbound-event, canonical-command, and outbound-dispatch
idempotency domains. Require environment, provider/app or phone-number identity, tenant,
relationship where resolved, operation, external ID/idempotency key, and canonical payload digest
in their uniqueness rules. Atomically reserve deduplication with canonical acceptance or a durable
typed rejection; same key/different digest must be a conflict. Set a policy-owned TTL no shorter
than provider retry/reconciliation and security replay horizons. After payload erasure, retain a
non-reconstructive tombstone sufficient to prevent replay for the required horizon. Back up and
restore dedup/outbox state to the same consistency point as canonical messages, and prohibit Demo
cleanup while a retained attempt can still cause provider retry.

#### DA-H5 — Delivery state is neither monotonic nor lossless under out-of-order provider status

**Package references:** Sections 5 (`EA-CE-06`), 12.3, 15, 16, 17 (`CE-FIT-07`), and 18.

The enum `QUEUED`, `SUBMITTED`, `PROVIDER_ACCEPTED`, `DELIVERED`, `READ`, `FAILED`, `EXPIRED`,
`UNKNOWN` is not a total monotonic progression. `UNKNOWN`, `FAILED`, and `EXPIRED` may later receive
a valid `DELIVERED` or `READ`; provider callbacks may arrive duplicated or out of order; and one
attempt may fail before a later attempt succeeds. A mutable attempt state plus `stateVersion` can
discard the provider observation history or reject truthful late evidence.

**Required remediation:** Store immutable, idempotent provider-status observations with provider
event identity, provider time, received time, environment binding, correlation, and raw normalized
status. Derive a current delivery projection using an explicit transition/precedence table that
separates transport progress from terminal attempt disposition and reconciliation uncertainty.
Model retries as distinct attempts under one outbound logical message. Define handling for late,
duplicate, contradictory, and regressive observations and prohibit all transport states from
changing execution, decision, or evidence state.

#### DA-H6 — Media/transcript separation regresses the already-defined voice data contract

**Package references:** Sections 12.2, 12.5, 14.3, 15, 16, and 20.

The package correctly separates media payload from immutable evidence metadata, but
`Transcript/Correction | Voice boundary` is not an authoritative storage or lifecycle owner. It
does not carry forward the directly cited WC-062 distinctions among raw audio, provider transcript,
customer-corrected text, accepted contribution, minimized lineage metadata, evidence, and erasure
tombstone. It also does not state whether WhatsApp media, extracted content, embeddings, summaries,
or malware quarantine are payload derivatives subject to the same erasure and hold decision.

**Required remediation:** Incorporate the WC-062 lineage as a channel-neutral invariant:
`provider media reference -> erasable payload -> derived transcript/extraction version ->
customer correction/confirmation -> accepted canonical contribution -> payload-free evidence
reference`. Assign each node an authority, classification, store boundary, retention class, legal
hold behavior, and erasure behavior. Require versioned correction rather than overwrite; only the
accepted version may enter professional context. Payload deletion must remove resolvable pointers
and leave only a non-reconstructive tombstone and permissible evidence metadata. Explicitly include
quarantine, extracted text, thumbnails, embeddings, summaries, caches, and provider copies in the
erasure/accountability model.

#### DA-H7 — Retention, erasure, legal hold, backup, and recovery ownership are unresolved

**Package references:** Sections 2.1, 5 (`EA-CE-05`, `EA-CE-08`), 13.4–13.5, 14.3, 15–16, 20,
21, and 24.

The package promises retention, erasure, legal hold, and recovery, but only media receives a
bounded-retention adjective. It does not define retention classes for canonical messages, profile
facts, summaries, checkpoints, channel bindings, status observations, dedup tombstones, transcripts,
opt-in/template evidence, or operational telemetry. It does not define hold precedence and release,
erasure propagation, backup expiry, or who authorizes and verifies restore. Section 24 leaves both
durations and recovery objectives open; Section 16 assumes dedup restoration without defining a
shared recovery point. Environment isolation also lacks a rule preventing a restore into another
environment from becoming routable or contacting Meta.

**Required remediation:** Add a lifecycle matrix for every Section 15 record and derivative,
identifying retention-policy owner, configurable duration class, trigger, legal-hold authority and
scope, hold release, erasure/correction propagation, tombstone/evidence result, cache/search/backup
age-out, and verification evidence. Add environment-specific backup ownership, encryption and key
scope, backup isolation, recovery authority, RPO/RTO owner, restore order and consistency group,
PITR/restore qualification, and reconciliation after restore. Any restore must target an isolated,
non-routable environment with separate temporary authority; prove tenant/FORCE-RLS controls,
schema watermark, canonical sequence and dedup/outbox consistency, and no provider callback or
outbound dispatch before explicit reactivation.

### MEDIUM

#### DA-M1 — Environment isolation identifies assets but not physical anti-collision invariants

**Package references:** Sections 5 (`EA-CE-08`), 13.1–13.5, 15, 16, and 17 (`CE-FIT-12`,
`CE-FIT-16`).

The isolation matrix says data and namespaces are separate, but does not define whether separation
is by subscription/account, database, schema, storage account/container, or another enforceable
boundary. More importantly at enterprise level, it does not require environment in every natural
and uniqueness key or prohibit import/restore/replay across environments. A copied provider event
or backup could collide or become actionable in the wrong environment.

**Required remediation:** Require environment identity as an immutable part of provider-event,
phone-binding, template, delivery, media, dedup, and backup namespaces. Define that cross-environment
restore/import is quarantined and non-routable, must remap no provider authority, and cannot emit
callbacks or outbound messages. Require separate encryption/key authority and runtime principals,
plus negative collision tests for equal provider IDs and idempotency keys in different environments.
The downstream Platform/Data design may choose the physical technology, but it must prove these
separation invariants.

#### DA-M2 — Migration and rollback do not cover schema, data, and mixed-version operation

**Package references:** Sections 8.5, 10.1–10.2, 15, 20, and 22.

Section 20 addresses semantic rollback of policy/context versions and rebuildable summaries, but
not introduction of tenant-bound sequences, profile lineage, dedup tombstones, delivery
observations, payload references, transcript versions, or environment namespaces. There is no
backfill provenance, mixed-release compatibility window, cutover watermark, validation, or rollback
rule. A “prior supported schema” alone does not show that the prior application can safely read
records created by the new release.

**Required remediation:** Require expand/migrate/contract evolution with a pre-traffic migration
lock, schema and data watermarks, idempotent tenant/relationship-bounded backfill, row-count and
lineage validation, previous-release read compatibility during the rollback window, and no
destructive down-migration. Define cutover and rollback behavior for sequence allocation,
idempotency namespaces, derived-summary rebuilds, delivery projection recomputation, and payload
tombstones. Contract only after rollback expiry and retained-data compatibility evidence.

### LOW

No LOW-severity findings.

## Required Remediation Summary

Before the Chief Solution Architect proceeds, the package must resolve **DA-B1** and incorporate the
normative data invariants in **DA-H1–DA-H7**. **DA-M1–DA-M2** may be satisfied in the same amendment
or by an explicitly controlling Data Architecture contribution referenced by Sections 15 and 22,
provided that contribution is accepted before Solution Architecture starts and does not delegate
logical ownership decisions back to the Solution Architect.

Exact retention durations, numeric RPO/RTO targets, physical database products, indexes, and storage
topology may remain downstream configurable decisions. Their accountable owners, isolation,
lineage, consistency, fail-closed behavior, legal-hold semantics, and qualification obligations
must be fixed now.

## Verdict

**CHANGES REQUIRED.** The package has strong channel-neutral authority boundaries and correctly
separates canonical history, model context, transport state, professional outcome, and evidence.
However, it does not yet give the Chief Solution Architect a complete logical data contract.
Proceeding now would require invention of transactional ownership, RLS propagation, lineage,
deduplication expiry, status reconciliation, payload lifecycle, restore authority, and migration
boundaries.
