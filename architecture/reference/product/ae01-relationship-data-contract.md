# AE-01 Relationship and Data Contract

**Producing Institution:** INST-006 — Data Architect
**Authorization:** GOA-GOAL-005-INST-006-02
**Status:** D-06 CONTRIBUTED — implementation-neutral
**Applies to:** WC-057 through WC-060

## Identity and First Mint

The canonical first-admission key is:

`tenant_id + initiating_participant_id + professional_type + evaluation_intent_id`

`evaluation_intent_id` is a customer- or channel-generated UUID persisted before admission. HTTP retries, Meta webhook retries, reconnects, and concurrent requests reuse it. A database unique constraint on the four fields arbitrates concurrent first mint. The winner returns the new relationship; a loser reads and returns that same relationship. A distinct relationship requires an explicit customer-authorized fork with `source_relationship_id` and fork evidence.

Neither conversation, channel, customer, participant, professional, contract, nor payment identity may be used as the relationship primary key.

## Migration 19 — Relationship Foundation

Migration `19-ae01-employment-relationship.sql` creates:

| Table | Required fields and constraints |
|---|---|
| `business.employment_relationships` | `relationship_id UUID PK`, `tenant_id UUID`, `professional_type`, `evaluation_intent_id UUID`, `initiating_participant_id UUID`, `state`, `state_version`, `authority_snapshot_id`, `accepted_contract_id`, `activation_id`, `stopped_at`, `created_at`; unique first-admission key; legal-state check |
| `business.relationship_participants` | tenant, relationship, participant, role (`EVALUATOR`, `EMPLOYER`, `OUTCOME_OWNER`, `RELATIONSHIP_MANAGER`), status, bound/revoked evidence; unique active relationship/participant/role |
| `business.relationship_state_history` | tenant, relationship, monotonic version, from/to state, actor/role, authority, correlation UUID, evidence ID, occurred time; append-only |
| `business.relationship_idempotency` | tenant, relationship, purpose, idempotency key, material request hash, outcome reference, status; unique tenant/purpose/key |

Every table enables and forces RLS. Ordinary application access requires `tenant_id = current_setting('app.current_tenant_id')::uuid`. Cross-tenant reads are unavailable to BP roles. Constitutional cross-tenant audit uses the CE/Audit Sink boundary under separate roles and explicit authorization, never an RLS bypass in BP.

Indexes: `(tenant_id, relationship_id)`, `(tenant_id, initiating_participant_id, professional_type)`, `(tenant_id, relationship_id, state_version)`, and `(tenant_id, relationship_id, correlation_id)`. At 100,000 state-history rows, tenant/relationship timeline and correlation lookup must remain below 100ms P95 in the integration environment.

## Migration 20 — Context and Configuration

| Table | Semantics |
|---|---|
| `payload_store.relationship_context_payloads` | Erasable values, source, confidence, confirmation status/time, invalidated time, payload hash; no constitutional proof |
| `business.context_confirmation_events` | Payload reference/hash only, field type, confirmation/correction action, actor, correlation, evidence ID; append-only and no raw PII |
| `business.relationship_goals` | Goal, baseline, measure, target/decision threshold, evidence source, review cadence, status |
| `business.relationship_skill_configuration` | Pinned skill/version, goal reference, authority state, applicability and reason |
| `business.decision_space_snapshots` | Immutable version, budget ceiling, authority boundaries, stop conditions, review cadence, accepted evidence |

Customer correction invalidates the old payload and adds a new payload; it never rewrites confirmation evidence. DPDPA erasure purges payload values through ADR-044 while retaining hashes and constitutional event integrity.

## Migration 21 — Contract and Activation

| Table | Semantics |
|---|---|
| `business.employment_contract_versions` | Immutable relationship-scoped version/hash, AEEC version, domain schedule payload reference/hash, configuration snapshot, price/tax summary, state |
| `business.contract_acceptances` | Exact contract/version/hash, participant/role, authentication assurance, scope confirmation, acceptance evidence/time; one effective acceptance per version |
| `business.activation_intents` | Canonical tenant + relationship + accepted contract + payment tuple, request hash, status (`PENDING`, `SUCCEEDED`, `FAILED_RETRYABLE`, `CONFLICT`), outcome subscription/evidence/time |

The activation tuple has one unique row. Processing first performs `INSERT ... ON CONFLICT DO NOTHING`, then locks/reads that row. Identical request hash with `SUCCEEDED` returns the stored outcome. Identical pending/retryable requests resume the same workflow. Different material hash records `CONFLICT` without mutation. The unique constraint is not exposed as a caller-visible 409 for identical replay.

## Migration 22 — Continuity and Evidence Projection

Migration `22-ae01-continuity-evidence.sql` creates the following exact contract. All UUID
defaults use `gen_random_uuid()` and all timestamps use `TIMESTAMPTZ` in UTC.

### `business.channel_bindings`

| Column | Type and nullability | Constraint or meaning |
|---|---|---|
| `binding_id` | `UUID NOT NULL` | Primary key; unique `(tenant_id, binding_id)` for composite references |
| `tenant_id` | `UUID NOT NULL` | RLS anchor; never accepted from a request body |
| `relationship_id` | `UUID NOT NULL` | Composite FK to `employment_relationships(tenant_id, relationship_id)` |
| `participant_id` | `UUID NOT NULL` | Server-resolved participant; BP verifies an active relationship-role binding |
| `participant_role` | `VARCHAR(32) NOT NULL` | `EVALUATOR`, `EMPLOYER`, `OUTCOME_OWNER`, or `RELATIONSHIP_MANAGER` |
| `channel` | `VARCHAR(16) NOT NULL` | `WHATSAPP` or `WEB` |
| `external_subject_hash` | `CHAR(64) NOT NULL` | Lowercase SHA-256; no raw phone, provider subject, token, or credential |
| `conversation_id` | `VARCHAR(256) NOT NULL` | Channel conversation reference; not relationship identity |
| `assurance_level` | `VARCHAR(40) NOT NULL` | `TIER_1_PHONE_IDENTITY`, `TIER_2_EXPLICIT_CONFIRMATION`, `TIER_3_MPIN`, or `TIER_4_PORTAL_FRESH` |
| `status` | `VARCHAR(16) NOT NULL DEFAULT 'PREPARED'` | `PREPARED`, `ACTIVE`, `REVOKED`, or `EXPIRED` |
| `prepared_evidence_id` | `UUID NOT NULL` | Opaque CE evidence reference for preparation |
| `bound_evidence_id` | `UUID` | Required when status becomes `ACTIVE` |
| `revoked_evidence_id` | `UUID` | Required for `REVOKED`; absent for `ACTIVE` |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Immutable creation time |
| `bound_at` | `TIMESTAMPTZ` | Required when status becomes `ACTIVE` |
| `revoked_at` | `TIMESTAMPTZ` | Required for `REVOKED` or `EXPIRED` |

Checks enforce the status enumeration, lowercase SHA-256 shape, and these state-dependent
values: `ACTIVE` requires non-null `bound_evidence_id` and `bound_at`; `REVOKED` requires
non-null `revoked_evidence_id` and `revoked_at`; `EXPIRED` requires `revoked_at`; and
`PREPARED` has none of those resolution fields. A transition trigger allows only
`PREPARED → ACTIVE|REVOKED|EXPIRED` and `ACTIVE → REVOKED|EXPIRED`, rejects reopening a
terminal state, and prevents changes to identity, assurance, relationship, and existing
evidence fields. A prepared binding is revoked when its participant role is revoked or Stop
fires; it expires when its checkpoint reaches `expires_at`. An active binding is revoked only
for explicit participant/role revocation or Stop and expires only when its independently
authenticated channel credential expires. Activating another participant or channel never
implicitly revokes an active binding. A partial unique index on
`(tenant_id, relationship_id, participant_id, channel)` where status is `PREPARED` or
`ACTIVE` prevents competing live bindings for the same participant and channel while allowing
multiple participants, channels, and conversations on one relationship. Indexes also cover
`(tenant_id, relationship_id, status)` and `(tenant_id, conversation_id)`.

### `business.continuity_checkpoints`

| Column | Type and nullability | Constraint or meaning |
|---|---|---|
| `checkpoint_id` | `UUID NOT NULL` | Primary key; unique `(tenant_id, checkpoint_id)` |
| `tenant_id` | `UUID NOT NULL` | RLS anchor |
| `relationship_id` | `UUID NOT NULL` | Composite FK to the relationship |
| `source_binding_id` | `UUID NOT NULL` | Composite FK `(tenant_id, source_binding_id)` to channel bindings |
| `target_binding_id` | `UUID NOT NULL` | Composite FK `(tenant_id, target_binding_id)` to channel bindings; differs from source |
| `continuity_envelope_hash` | `CHAR(64) NOT NULL` | Lowercase SHA-256 of canonical Neutral Continuity Envelope bytes |
| `material_request_hash` | `CHAR(64) NOT NULL` | Lowercase SHA-256 used for divergent replay detection |
| `causal_marker` | `UUID NOT NULL` | Unique within tenant and relationship |
| `sequence_number` | `BIGINT NOT NULL` | Positive and unique within tenant and relationship |
| `idempotency_key` | `UUID NOT NULL` | Unique within tenant and relationship |
| `status` | `VARCHAR(16) NOT NULL DEFAULT 'PREPARED'` | `PREPARED`, `COMMITTED`, `REVERTED`, `CONFLICT`, or `EXPIRED` |
| `prepared_evidence_id` | `UUID NOT NULL` | Opaque CE preparation evidence reference |
| `resolution_evidence_id` | `UUID` | Required for every terminal status |
| `prepared_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Preparation time |
| `expires_at` | `TIMESTAMPTZ NOT NULL` | Exactly 15 minutes after `prepared_at` |
| `resolved_at` | `TIMESTAMPTZ` | Required for every terminal status |

Checks enforce status enumeration, positive sequence number, differing source and target
bindings, lowercase SHA-256 shape, `expires_at = prepared_at + INTERVAL '15 minutes'`, and
null resolution fields only for `PREPARED`; every terminal row requires
`resolution_evidence_id` and `resolved_at`. A transition trigger permits only
`PREPARED → COMMITTED|REVERTED|CONFLICT|EXPIRED`, rejects terminal-row updates, and prevents
changes to hashes, bindings, causal marker, sequence, idempotency, and preparation evidence.
Target authentication, current role/authority, Stop state, and evidence
commit all pass before `COMMITTED`. The source binding remains active after commit because
AE-01 permits concurrent independently authenticated channels. Identical
`(idempotency_key, material_request_hash, continuity_envelope_hash)` returns the prior row;
reuse with either hash changed records `CONFLICT` with zero binding or relationship mutation.
Unique `(tenant_id, relationship_id, idempotency_key)` is the concurrency arbiter; after a
conflict, the stored hashes determine identical replay versus divergent use. Unique
`(tenant_id, relationship_id, causal_marker)` and
`(tenant_id, relationship_id, sequence_number)` enforce causal identity and order. The
implementation locks the relationship row and assigns
`MAX(sequence_number) + 1`, preventing gaps and out-of-order commit. Indexes cover
`(tenant_id, relationship_id, sequence_number)`, `(tenant_id, relationship_id, status)`, and
`(tenant_id, target_binding_id, status)`.

### `business.delivery_acknowledgements`

| Column | Type and nullability | Constraint or meaning |
|---|---|---|
| `acknowledgement_id` | `UUID NOT NULL` | Primary key |
| `tenant_id` | `UUID NOT NULL` | RLS anchor |
| `relationship_id` | `UUID NOT NULL` | Composite FK to the relationship |
| `checkpoint_id` | `UUID` | Optional composite FK to a continuity checkpoint |
| `binding_id` | `UUID NOT NULL` | Composite FK to the independently authenticated binding |
| `message_id_hash` | `CHAR(64) NOT NULL` | Lowercase SHA-256; no raw provider message ID |
| `acknowledgement_type` | `VARCHAR(32) NOT NULL` | `TRANSPORT_ACCEPTED` or `PARTICIPANT_OBSERVED` |
| `acknowledged_at` | `TIMESTAMPTZ NOT NULL` | Provider or participant event time |
| `evidence_id` | `UUID NOT NULL` | Opaque CE evidence reference |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Durable receipt time |

Checks enforce acknowledgement type enumeration and lowercase SHA-256 shape. Rows are
append-only through a `BEFORE UPDATE OR DELETE` trigger that raises an exception for every
database role; grants additionally omit `UPDATE` and `DELETE` for `business_app`. Unique `(tenant_id, binding_id, message_id_hash,
acknowledgement_type)` makes each acknowledgement independently replay-safe. Transport
acceptance never implies participant observation. Indexes cover
`(tenant_id, relationship_id, acknowledged_at)`, `(tenant_id, checkpoint_id)`, and
`(tenant_id, binding_id, message_id_hash)`.

### `business.channel_message_deduplication`

| Column | Type and nullability | Constraint or meaning |
|---|---|---|
| `deduplication_id` | `UUID NOT NULL` | Primary key |
| `tenant_id` | `UUID NOT NULL` | RLS anchor |
| `relationship_id` | `UUID NOT NULL` | Composite FK to the relationship |
| `binding_id` | `UUID NOT NULL` | Composite FK to the channel binding |
| `provider_message_id_hash` | `CHAR(64) NOT NULL` | Lowercase SHA-256; no raw provider identifier |
| `material_message_hash` | `CHAR(64) NOT NULL` | Lowercase SHA-256 of canonical material message bytes |
| `received_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | First receipt time |
| `outcome_reference` | `UUID` | Prior durable outcome; required when processing completes |
| `status` | `VARCHAR(16) NOT NULL DEFAULT 'RECEIVED'` | `RECEIVED`, `SUCCEEDED`, `FAILED`, or `CONFLICT` |
| `expires_at` | `TIMESTAMPTZ NOT NULL` | Exactly 48 hours after `received_at` |

Checks enforce status enumeration, lowercase SHA-256 shape,
`expires_at = received_at + INTERVAL '48 hours'`, null `outcome_reference` for `RECEIVED`,
and non-null `outcome_reference` for terminal states. Unique `(tenant_id, binding_id,
provider_message_id_hash)` arbitrates concurrent delivery.
The first receiver owns processing. Identical material hash replays the stored status and
outcome; a changed material hash returns `CONFLICT` with zero mutation. Only
`RECEIVED → SUCCEEDED|FAILED|CONFLICT` is legal; a transition trigger rejects terminal-row
updates and changes to identity, hashes, relationship, binding, receipt, or expiry. Expired
rows may be deleted only by the `business_continuity_maintenance` NOLOGIN role after
`expires_at`; it has RLS-constrained `SELECT` and `DELETE` on this table only, receives a
tenant setting from the scheduled maintenance transaction, and has no membership in
`business_app` or constitutional roles. A daily BP maintenance job deletes only expired rows
for one explicitly selected tenant per transaction and emits an operational cleanup metric;
the deletion is not a constitutional decision and does not create CE evidence. Expiry never
deletes the linked constitutional evidence or delivery acknowledgement. Indexes cover
`(tenant_id, relationship_id, received_at)`, `(tenant_id, binding_id,
provider_message_id_hash)`, and `expires_at` for maintenance.

### Cross-Table Enforcement And Retention

All four tables enable and force RLS using
`tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID` for both
`USING` and `WITH CHECK`. `business_app` receives only the operations required by the legal
transition rules; trigger-enforced transition guards reject illegal status changes.
`delivery_acknowledgements` has no `UPDATE` or `DELETE` grant. Checkpoint and binding
terminal evidence, hashes, and acknowledgement rows follow relationship constitutional
retention. Deduplication rows alone are operational and expire after 48 hours. No table stores
raw channel payload, phone, provider subject, credential, or customer content.

One relationship may have multiple concurrent presentation bindings and conversations, but
every binding is independently authenticated and role-bound. Binding and checkpoint statuses
are delivery state only; they never own or mutate D-03 relationship lifecycle, contract,
authority, payment, or billing truth. CE evidence IDs are opaque references rather than
cross-database foreign keys.

## Evidence Retrieval

Customer retrieval is always `(authenticated tenant, relationship_id)` scoped. Material evidence includes rights/disclosures, context confirmation, proposals, customer decisions, lifecycle transitions, contract acceptance, payment/activation outcome, charges, degradation, handoff, Stop/release, and unresolved failures. Internal policy traces, other tenants, credentials, raw prompts, and constitutional deliberation are excluded. Payload references are returned only when the referenced payload is tenant-owned and not erased.

## Data Conformance

Zero duplicate first mint; zero cross-tenant retrieval; deterministic activation replay; append-only state and confirmation history; legal erasure without proof loss; channel identity non-equivalence; and timeline reconstruction from admission through handoff/Stop are mandatory.