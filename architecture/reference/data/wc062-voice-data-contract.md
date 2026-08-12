# WC-062 Voice Data Contract

| Field | Value |
|---|---|
| Institution | INST-006 — Data Architect |
| Goal / Work Contract | GOAL-005 / WC-062 F6 |
| Authorization / Acceptance | GOA-GOAL-005-INST-006-04 / ACC-GOAL-005-INST-006-04 at 2026-08-12T10:07:18Z |
| Contribution / Learning | CR-GOAL-005-INST-006-05 / LR-GOAL-005-INST-006-03 |
| `produced_at` | 2026-08-12T10:18:11Z |
| Status | COMPLETE — data specification only |

## Classification And Ownership

| Data | Class | Authority | Lifecycle |
|---|---|---|---|
| Raw audio | Sensitive customer payload | BP-owned session metadata; encrypted payload store owns bytes | 30 days after recorded send, or earlier valid erasure; unsent/cancelled payload deleted within 24 hours |
| Provider transcript | Sensitive derived payload | PR produces; BP exposes only for review | Superseded after correction and erased with payload policy; never constitutional truth by itself |
| Customer-corrected text | Sensitive customer payload | BP owns accepted version | Relationship retention policy, erasure eligible |
| Confidence, locale, duration, hashes | Minimized lineage metadata | BP evidence projection | Retained only as needed to prove processing and evidence lineage |
| Consent/send/evidence/erasure facts | Constitutional evidence | CE/audit ledger | Append-only and not erased; contains references and hashes, not audio or transcript text |

Audio and transcript payload are never stored in the constitutional audit ledger. Erasure removes
payload and direct retrieval pointers while preserving an immutable, payload-free record of what
was authorized, when it was processed, which version was sent, and whether erasure completed.

## State And Lineage

Each session is bound to tenant, relationship, actor, opaque session ID, idempotency identity, and
schema version. Audio has a content hash and scan state. A transcript version cites audio hash,
locale, confidence, producing contract version, and predecessor. Customer correction creates a new
version; it never overwrites provider output. Only the explicitly sent corrected or confirmed
version may be referenced by downstream professional input.

Required durable relationships are:

`session -> audio payload -> transcript v1 -> correction vN -> send decision -> evidence reference`

Payload deletion replaces resolvable payload references with tombstones carrying deletion time,
scope, reason class, and evidence reference. Tombstones contain no customer content.

## Minimisation And Metadata

Store no voiceprint, speaker identity, biometric feature, acoustic fingerprint, provider prompt,
provider raw response, listening history, intermediate retry payload, or model-training permission.
Language metadata uses approved BCP 47 locale plus declared/detected source; detection never
silently changes customer selection. Logs and analytics use opaque session/correlation IDs and
coarse state only.

## Retention And Erasure

- Unsent, cancelled, failed-before-send, and abandoned audio/transcripts: delete within 24 hours.
- Sent raw audio: default 30 days, unless an approved relationship policy requires a shorter term.
- Corrected text used as the contribution: retained under the relationship payload policy, with
  customer erasure available unless another lawful/constitutional hold is separately evidenced.
- Quarantined payload: Security may require a shorter isolation period; never exceed 7 days without
  a separately recorded incident hold.
- Erasure is idempotent, tenant/relationship authorized, and Evidence First. Success is returned
  only after payload deletion or a truthful typed blocked outcome is durably recorded.
- Backups and caches must age out under the same declared maximum; no hidden provider copy may be
  treated as platform erasure completion.

## Migration Decision

**Migration required.** Existing relationship-message and evidence stores do not provide the
separate payload, transcript-version, correction-lineage, retention, erasure-tombstone, and scan
state needed by WC-062. The future migration blueprint must add append-only lineage and erasure
records plus payload references without placing audio bytes or transcript text in constitutional
schemas. It must be additive, tenant-isolated, rollback-safe, and use the next unoccupied migration
identifier confirmed at implementation entry. This specification does not create or number SQL.

## Data Acceptance Obligations

Tests must prove cross-tenant and cross-relationship denial, correction version integrity,
idempotent erasure, payload/evidence separation, no content in telemetry, expiry of abandoned and
sent payload, immutable evidence after payload deletion, language metadata fidelity, and safe
handling of provider/retry duplicates.

## Dependencies And Boundaries

Product owns customer-visible retention language and launch locales. Solution owns API and service
contracts. Security owns encryption, scanning, quarantine controls, and hard ceilings. Data owns
classification, authoritative lifecycle, lineage, and migration need. This record defines no API,
security mechanism, implementation, provider, or review verdict.

## Learning Record — LR-GOAL-005-INST-006-03

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-006-03 |
| `record_type` | Learning Record |
| `improvement_signal` | Voice erasure is coherent only when payload, derived transcript, correction lineage, and immutable evidence are classified separately before schema design. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |
| `produced_at` | 2026-08-12T10:18:11Z |

**Verdict:** CR-GOAL-005-INST-006-05 satisfies Amendment 10 Order 1C within INST-006 Decision
Space. It authorizes no migration execution or implementation.
