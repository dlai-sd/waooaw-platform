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

| Table | Semantics |
|---|---|
| `business.channel_bindings` | tenant, relationship, participant, channel, external subject hash, conversation reference, assurance level, status, bound/revoked evidence/time |
| `business.continuity_checkpoints` | source/target binding, continuity envelope hash, causal marker, sequence, status, evidence/time |
| `business.delivery_acknowledgements` | transport acceptance and participant observation as separate fields/events |
| `business.channel_message_deduplication` | channel, message ID/hash, received time, outcome reference, expiry; no raw message |

One relationship may have multiple concurrent presentation bindings, including multiple conversations, but each binding is independently authenticated and role-bound. Bindings can be `PREPARED`, `ACTIVE`, `REVOKED`, or `EXPIRED`; those are delivery states, not relationship lifecycle states. Revocation never terminates employment. Binding proof follows relationship constitutional retention; raw channel payload follows payload-store erasure rules.

## Evidence Retrieval

Customer retrieval is always `(authenticated tenant, relationship_id)` scoped. Material evidence includes rights/disclosures, context confirmation, proposals, customer decisions, lifecycle transitions, contract acceptance, payment/activation outcome, charges, degradation, handoff, Stop/release, and unresolved failures. Internal policy traces, other tenants, credentials, raw prompts, and constitutional deliberation are excluded. Payload references are returned only when the referenced payload is tenant-owned and not erased.

## Data Conformance

Zero duplicate first mint; zero cross-tenant retrieval; deterministic activation replay; append-only state and confirmation history; legal erasure without proof loss; channel identity non-equivalence; and timeline reconstruction from admission through handoff/Stop are mandatory.