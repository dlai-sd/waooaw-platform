# WC-062 Voice Solution Contract

| Field | Value |
|---|---|
| Institution | INST-005 — Solution Architect |
| Goal / Work Contract | GOAL-005 / WC-062 F6 |
| Authorization / Acceptance | GOA-GOAL-005-INST-005-11 / ACC-GOAL-005-INST-005-11 at 2026-08-12T10:07:17Z |
| Contribution / Learning | CR-GOAL-005-INST-005-14 / LR-GOAL-005-INST-005-05 |
| `produced_at` | 2026-08-12T10:18:10Z |
| Status | COMPLETE — solution specification only |

## Ownership And C-095 Decision

BP is the sole authenticated public facade and owns relationship authorization, public workflow
state, idempotency, customer-safe outcomes, and Evidence First transitions. PR privately owns
transcription orchestration and accepted-text handoff. AIR privately owns provider-neutral speech
to text dispatch, language capability, and confidence result. The browser calls only generated BP
operations and never PR, AIR, CE, object storage, MCP, or a provider.

Voice is a logical extension of existing BP, PR, and AIR components, not a new deployable service.
No new component manifest or service skeleton is required under C-095. Existing manifests must be
updated only if implementation adds a new independently deployable boundary, which this contract
forbids.

## Contract Versions

- BP public OpenAPI: next additive minor version from the current canonical contract.
- PR private voice orchestration contract: `VoiceOrchestrationV1` version `1.0.0`.
- AIR private transcription contract: `ProviderNeutralTranscriptionV1` version `1.0.0`.
- All enums are closed for the declared major version; unknown values fail as `contract_mismatch`.

## BP Public Operations

All paths are under `/api/v1/employment/relationships/{relationshipId}/voice-contributions` and
obtain tenant identity only from the authenticated session.

| Operation ID | Method / suffix | Request / response |
|---|---|---|
| `createVoiceContributionSession` | `POST /sessions` | `CreateVoiceContributionSessionRequestV1` / `VoiceContributionSessionV1` |
| `getVoiceContributionSession` | `GET /sessions/{sessionId}` | none / `VoiceContributionSessionV1` |
| `uploadVoiceContributionAudio` | `POST /sessions/{sessionId}/audio` | binary multipart plus idempotency header / `VoiceUploadReceiptV1` |
| `getVoiceContributionTranscript` | `GET /sessions/{sessionId}/transcript` | none / `VoiceTranscriptV1` |
| `submitVoiceContributionCorrection` | `PUT /sessions/{sessionId}/correction` | `VoiceCorrectionRequestV1` / `VoiceCorrectionReceiptV1` |
| `sendVoiceContribution` | `POST /sessions/{sessionId}/send` | `SendVoiceContributionRequestV1` / `VoiceContributionOutcomeV1` |
| `cancelVoiceContributionSession` | `POST /sessions/{sessionId}/cancel` | `CancelVoiceContributionRequestV1` / `VoiceContributionOutcomeV1` |
| `requestVoicePayloadErasure` | `POST /{contributionId}/erasure` | `VoicePayloadErasureRequestV1` / `VoicePayloadErasureReceiptV1` |

Principal schemas carry opaque IDs, `schemaVersion`, state, language, confidence band, corrected
text only where authorized, timestamps, allowed commands, `evidenceReference` only after durable
recording, and RFC 9457 errors. Raw audio never appears in JSON. Public requests contain no
`tenantId`, provider, credential, internal route, storage URI, or evidence-ledger address.

## State And Sequence

`CREATED -> UPLOADING -> UPLOADED -> TRANSCRIBING -> REVIEW_REQUIRED -> READY_TO_SEND ->
SENDING -> RECORDED`. Terminal or controlled states are `CANCELLED`, `REJECTED`, `QUARANTINED`,
`UNAVAILABLE`, `UNKNOWN`, and `STOPPED`.

1. BP authorizes relationship and creates a session.
2. BP accepts one bounded upload and privately requests PR orchestration.
3. PR sends a provider-neutral request to AIR; AIR returns transcript, locale, confidence, and
   provider-neutral failure only.
4. BP exposes review state. Correction creates a new version linked to the original; it does not
   overwrite lineage.
5. Send is allowed only from `READY_TO_SEND`. BP validates authorization, calls Evidence First,
   and returns `RECORDED` only after durable evidence succeeds.
6. On timeout or disconnect, GET reconciles authoritative state before any retry.

## Idempotency And Failures

Mutating operations require an idempotency key bound to actor, tenant, relationship, session,
operation, and canonical payload hash. Same key/same hash returns the original receipt; same
key/different hash returns `409 idempotency_conflict`. Unknown outcomes retain the same key.

Typed failures include `permission_required`, `unsupported_language`, `invalid_media`,
`limit_exceeded`, `malware_quarantined`, `transcription_unavailable`, `confidence_review_required`,
`consent_required`, `stale_version`, `idempotency_conflict`, `relationship_forbidden`,
`evidence_unavailable`, `stopped`, and `contract_mismatch`. Errors expose correlation references,
not provider, storage, tenant, transcript, malware-signature, or credential detail.

## Owner Inputs

Product controls channel, launch languages, confidence journey, operating duration/size, and
acceptance meanings. Data controls authoritative storage, lineage, retention, erasure, and
migration. Security controls media validation ceiling, scanning/quarantine, encryption, replay,
residency, abuse, and privacy-safe observability. This contract consumes their approved values and
does not silently default them.

## Learning Record — LR-GOAL-005-INST-005-05

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-005-05 |
| `record_type` | Learning Record |
| `improvement_signal` | Provider-neutral voice needs one explicit public state machine and stable idempotency identity before client generation; otherwise retry, correction, and Evidence First semantics diverge across BP, PR, and AIR. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |
| `produced_at` | 2026-08-12T10:18:10Z |

**Verdict:** CR-GOAL-005-INST-005-14 satisfies Amendment 10 Order 1B within INST-005 Decision
Space. It authorizes no implementation, generated client, migration, or integrated review.

## Canonical Contract Repair — CR-GOAL-005-INST-005-15

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-005-15 |
| `record_type` | Contribution Record — repair attestation |
| `produced_at` | 2026-08-12T10:59:19Z |
| Repairs | The canonical-contract omission in CR-GOAL-005-INST-005-14; its operation catalog existed only in prose |
| Scope | Specification artifacts only; no source, generated client, migration, provider activation, deployment, or implementation authority |
| Status | COMPLETE |

The Solution owner publishes the following exact canonical contracts:

| Boundary | Canonical artifact | Version | SHA-256 |
|---|---|---|---|
| BP authenticated public facade | `architecture/reference/api-specs/business-platform.openapi.yaml` | `1.8.0` | `a3fb13593da4a2fc2121ba0f603849de7113529df65092caa53a0273d84a0b75` |
| PR private orchestration | `architecture/reference/api-specs/professional-runtime.openapi.yaml` | `1.3.0`; `VoiceOrchestrationV1` `1.0.0` | `debcdb33bc7ecfbcec111be618c36cc9508d1009374effb09e7a771daf007d74` |
| AIR private transcription | `architecture/reference/api-specs/ai-runtime-transcription.openapi.yaml` | `ProviderNeutralTranscriptionV1` `1.0.0` | `4f24e86a4003c76efa70d3b61a7d9da6fbe5346b7f67926c8bf70132b9dbd94d` |

The BP artifact contains the eight declared public operations and no browser-private route. The PR
and AIR operations are service-authenticated, marked `x-internal`, and expose no provider or
credential field. Tenant context is derived from authenticated claims rather than request-body
fields. Mutating submission and cancellation operations carry idempotency keys; GET operations
reconcile authoritative state. BP remains the Evidence First success boundary, and Emergency Stop
remains independent of transcription availability and ordinary voice control paths.

Validation parsed all three YAML documents, found unique operation IDs, resolved every local
reference reachable from the new voice paths and schemas, and found no `tenantId` request field.
The whole BP document retains one pre-existing unresolved `#/components/responses/Forbidden`
reference outside the voice graph; this repair neither introduces nor changes that unrelated debt.

## Learning Record — LR-GOAL-005-INST-005-06

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-005-06 |
| `record_type` | Learning Record |
| `improvement_signal` | A prose operation catalog can guide a contract but cannot satisfy an Entry Gate that requires canonical, generated-client-compatible contract bytes. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |
| `produced_at` | 2026-08-12T10:59:19Z |

**Repair verdict:** CR-GOAL-005-INST-005-15 closes the concrete Solution specification gap. R-091
reviewed the earlier package and must be superseded by a fresh integrated EA review before final CA
readiness can be determined. This repair grants no implementation authority.
