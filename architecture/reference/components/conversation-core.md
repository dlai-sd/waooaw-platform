# Component Specification: Conversation Core

**Work Contract:** WC-034 / IB-014 / F3 Conversation Core
**Office:** INST-005 Solution Architect
**Status:** ARCHITECTURE APPROVED — R-059; IMPLEMENTATION AND DEPLOYMENT BLOCKED
**Owning containers:** Business Platform (public conversation truth) and Professional Runtime (professional execution)
**Constitutional basis:** C-001, C-002, C-005, C-023, C-026, C-032, C-042, C-049, C-059, C-063, C-065, C-071, C-076; ADR-002, ADR-003, ADR-005, ADR-015, ADR-017, ADR-018, ADR-031

## 1. Scope and Ownership

Conversation Core embodies one durable conversation per Employment Relationship. It introduces no deployable service.

| Container | Owns | Must not own |
|---|---|---|
| Business Platform (BP) | Conversation identity, durable ordered timeline, unread position, customer commands, idempotency outcomes, canonical message/card projection, public SSE boundary | Professional reasoning, model dispatch, direct model-provider access, Emergency Stop transport |
| Professional Runtime (PR) | Relationship-scoped professional execution, typed execution events, partial/cancelled outcomes, CE-gated evidence state received from existing constitutional paths | Public browser ingress, durable customer conversation truth, tenant or relationship authorization policy |
| Web PWA | Draft text, visibly unconfirmed optimistic state, generated BP client use, BP SSE presentation, relationship-local offline outbox | Tenant derivation, duplicate decisions, delivery/evidence inference, PR/provider URLs |
| AI Runtime | Existing internal inference and tool execution behind PR | Conversation persistence, customer identity, browser connections |

Ordinary browser traffic terminates at BP. The browser MUST NOT connect to PR or a model provider for timeline, send, retry, cancellation, or streaming. The dedicated Emergency Stop WebSocket remains the only existing browser-to-PR exception and is unchanged by F3. `@ai-sdk/react` is not an F3 architecture dependency and is prohibited until separately approved.

**Explicit exclusions:** attachments, voice, cross-channel checkpoint commit, notification suppression, Plan/Priority Work aggregation, Usage & budget, Founder administration, F4-F8, application code, dependency installation, provider activation, and deployment.

## 2. Invariants

1. One Employment Relationship has exactly one durable conversation projection.
2. BP resolves `tenant_id`, participant, relationship access, and role from the validated Keycloak session. No public request body, URL, cursor, event, or card contains `tenant_id`.
3. A missing, inaccessible, or cross-tenant relationship returns the same `CONVERSATION_NOT_ACCESSIBLE` problem shape and timing class.
4. BP is authoritative for message identity, ordering, delivery, processing, evidence presentation, unread position, and reconciliation cursors.
5. PR accepts internal execution only from authenticated BP service identity carrying tenant context in its signed service assertion. PR never trusts tenant or participant values in an execution body.
6. Transport acceptance is not delivery, professional completion, or constitutional evidence. These states remain independent.
7. Evidence is shown as `RECORDED` only after the existing CE path confirms the evidence record. A nullable evidence reference is never interpreted as confirmation.
8. Every mutation carries an `Idempotency-Key`. BP stores the operation family, authenticated actor, relationship, key, canonical payload hash, and prior outcome.
9. Same actor + relationship + operation + key + hash replays the prior outcome. Divergent reuse returns `CONVERSATION_IDEMPOTENCY_CONFLICT` with no mutation or PR dispatch.
10. Cursors are opaque, tenant/relationship-bound, integrity-protected, and non-authoritative when held by the browser. Cursor expiry requires timeline reconciliation; it never authorizes blind retry.
11. PR event IDs and sequence numbers are monotonic within one execution. BP assigns the canonical conversation sequence after validation and persistence.
12. Emergency Stop preempts execution and streaming. Ordinary reconnect, retry, or cancellation cannot release Stop.

## 3. Public BP Contract

The canonical wire contract is `architecture/reference/api-specs/business-platform.openapi.yaml`.

| Operation | Purpose | Success meaning |
|---|---|---|
| `GET /api/v1/employment/relationships/{relationshipId}/conversation/messages` | Read a cursor-paginated authoritative timeline and unread boundary | Snapshot returned; no read position mutation |
| `POST /api/v1/employment/relationships/{relationshipId}/conversation/messages` | Accept one text contribution and create/replay its execution intent | `202` means BP accepted durable responsibility, not delivery or evidence |
| `POST /api/v1/employment/relationships/{relationshipId}/conversation/messages/{messageId}/retry` | Reconcile and retry a failed or unresolved contribution using its original key/hash | `202` means the same logical message is pending; never creates a second message |
| `PUT /api/v1/employment/relationships/{relationshipId}/conversation/read-position` | Advance the authenticated participant's unread position | Monotonic position accepted or replayed |
| `GET /api/v1/employment/relationships/{relationshipId}/conversation/stream` | Stream canonical BP events as SSE | Events are projections of BP-accepted state only |
| `DELETE /api/v1/employment/relationships/{relationshipId}/conversation/executions/{executionId}` | Request cancellation through BP | Cancellation accepted or terminal outcome replayed; Stop remains separate |

### 3.1 Timeline

The default page is newest-first for efficient resume but items in each response are in ascending canonical `sequence`. `cursor` requests older pages. `afterCursor` is used only for forward reconciliation after reconnect. Supplying both is invalid. The response includes `authoritativeCursor`, `nextCursor`, `unreadBoundaryMessageId`, and `hasMore`.

Date and channel separators are presentation derived from canonical `acceptedAt`, `channel`, and sequence. They are not independently persisted messages. A WhatsApp provenance label is informational in F3; it does not claim F5 checkpoint continuity.

### 3.2 Send and Retry

The v1 customer command accepts text only. `clientMessageId` is a UUID generated once per relationship-local draft and retained through offline retries. `expectedCursor` is an observation, not a precondition for acceptance; when stale, BP accepts or replays the command and returns the current authoritative cursor.

Retry is legal only for `FAILED` or `UNRESOLVED` messages. It MUST use the original `Idempotency-Key`; BP compares the stored canonical payload hash and dispatch identity before scheduling the same logical execution. A second message ID is never minted. A terminal `COMPLETED` outcome is replayed. A changed payload requires a new send with a new client message and key.

### 3.3 Stream

BP exposes authenticated Server-Sent Events (`text/event-stream`). Authentication uses the approved server session/BFF boundary; tokens never appear in URLs. `Last-Event-ID` resumes within the retention window. An expired or invalid event cursor emits or returns `reconciliation.required`; the client then fetches the timeline before any retry.

Event types are versioned and include `message.accepted`, `processing.started`, `response.delta`, `card.upserted`, `message.completed`, `message.failed`, `stream.cancelled`, `stop.applied`, `reconciliation.required`, and `heartbeat`. Delta events are always `partial=true`; BP persists a final canonical message projection before emitting `message.completed`.

Cancellation stops the selected execution when possible and preserves already accepted partial content with `partial=true` and `completionReason=CANCELLED`. It does not delete history, revoke evidence, or release Emergency Stop.

## 4. Internal PR Execution and Stream Contract

The canonical internal wire contract is `architecture/reference/api-specs/professional-runtime.openapi.yaml`.

| Operation | Caller | Purpose |
|---|---|---|
| `POST /api/v1/internal/conversations/{conversationId}/executions` | BP only | Start or replay professional processing for one BP-accepted customer message |
| `GET /api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream` | BP only | Consume ordered typed PR execution events as SSE |
| `DELETE /api/v1/internal/conversations/{conversationId}/executions/{executionId}` | BP only | Request execution cancellation without changing Stop state |

BP service authentication, mTLS where applicable, correlation ID, and `Idempotency-Key` are required. Tenant identity is derived from the signed BP service assertion, not from path/query/body data. The request identifies only the BP conversation, canonical customer message, relationship-scoped execution context reference, locale, and decision-space version.

PR returns `202` only after durable Temporal execution responsibility is accepted. Same key/hash returns the existing execution. Divergent reuse returns `EXECUTION_IDEMPOTENCY_CONFLICT`. CE unavailable, Stop active, stale Decision Space, or unavailable runtime returns an explicit fail-safe state; PR never starts model dispatch in those states.

PR events are internal facts, not customer truth. BP validates schema version, conversation/execution correlation, sequence monotonicity, and allowed state transition before persisting and projecting them. Unknown major versions halt that execution projection with `EXECUTION_SCHEMA_UNSUPPORTED`; unknown additive fields in the same major version are ignored.

## 5. Versioned Data Contracts

All public F3 schemas use semantic major/minor strings. F3 starts at `1.0`.

### 5.1 Compatibility Rules

| Change | Rule |
|---|---|
| Add optional field or event type | Minor-compatible; consumer ignores unknown optional fields/types and reconciles timeline when state is material |
| Remove/rename field, change meaning/type, reorder required state transition | Major version; old and new versions coexist through an explicit migration window |
| Unknown major message/card/event schema | Fail closed for commands; render honest unsupported state for historical reads; never execute a card command |
| Card command expansion | Requires an owner-approved operation; a renderer cannot invent an endpoint |

### 5.2 Message V1

`ConversationMessageV1` contains: `schemaVersion`, `messageId`, `relationshipId`, canonical `sequence`, actor, channel, typed content blocks, zero or more governed cards, independent delivery/processing/evidence states, `partial`, optional completion reason, optional `retryOfMessageId`, optional customer `clientMessageId`, and canonical timestamps.

Allowed v1 content is `TEXT`. Attachments and voice require later approved schema versions and remain unavailable in F3.

### 5.3 Governed Card V1

Every card has `schemaVersion`, `cardId`, `cardType`, owner, state, effect summary, and zero or more typed commands. Commands contain identifiers and availability only; their target operation must already exist in an approved generated BP contract.

| Card | Additional required fields | F3 behavior |
|---|---|---|
| Action | owner, action state, effect, optional due date | Render and navigate/command only when approved operation exists |
| Plan | goal, progress state, effect | Opens Plan only when F4 is released; otherwise honest unavailable state |
| Deliverable | owner, deliverable state, effect | Metadata only; attachment preview/download remains excluded |
| Decision | owner, decision state, effect, authority impact, alternatives | No commitment without a separately approved command operation |

Card state never substitutes for relationship, approval, evidence, billing, or Plan truth owned elsewhere.

## 6. State Semantics

| Dimension | Values | Meaning |
|---|---|---|
| Delivery | `LOCAL_ONLY`, `ACCEPTED`, `FAILED`, `UNRESOLVED` | Browser-local versus BP durable acceptance; no evidence meaning |
| Processing | `NOT_STARTED`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `STOPPED` | Professional execution lifecycle |
| Evidence | `NOT_APPLICABLE`, `PENDING`, `RECORDED`, `FAILED` | CE-confirmed evidence status only |
| Completion reason | `COMPLETE`, `PARTIAL_FAILURE`, `CANCELLED`, `EMERGENCY_STOPPED` | Why content stopped changing |

The UI may present `sending` for `LOCAL_ONLY`, but that value is never accepted from or persisted by BP. Evidence green/`Recorded` requires `RECORDED` plus a non-null evidence reference.

## 7. Offline and Unknown-Outcome Reconciliation

1. Drafts are stored relationship-locally and visibly unsent. They contain no token, tenant ID, evidence payload, or protected timeline.
2. On reconnect, the client fetches the authoritative timeline using its last accepted cursor before submitting or retrying queued work.
3. It matches `clientMessageId` and the prior idempotency outcome. If present, local state adopts the canonical message and discards the queued duplicate.
4. If absent and the prior outcome is unknown, the client submits the exact original request with the exact original `Idempotency-Key`.
5. BP replays acceptance or creates the one canonical message. Divergent local content remains a new draft and cannot reuse the key.
6. The outbox removes an item only after canonical acceptance/replay. Timeout alone never means success.
7. Sign-out and account switch clear all drafts, cursors, stream IDs, and outbox records according to F2 policy.

Service workers MUST NOT cache authenticated timeline, stream, error, or command responses. URL, query, logs, analytics, and telemetry MUST NOT contain message text, card payload, token, tenant identifier, client message ID, or evidence payload. Correlation IDs and opaque resource IDs are permitted only in structured server telemetry under existing retention policy.

## 8. Error Contract

Public errors use RFC 9457 `ConversationProblemDetail` with stable `code` and `correlationId`. They never echo submitted text, card data, tokens, tenant identity, internal PR/provider details, or relationship existence.

| HTTP | Code | Required behavior |
|---|---|---|
| 400 | `CONVERSATION_REQUEST_INVALID` | Reject malformed/unsupported version or mutually exclusive cursors |
| 401 | `CONVERSATION_SESSION_REQUIRED` | Re-authenticate; hide protected content immediately |
| 404 | `CONVERSATION_NOT_ACCESSIBLE` | Normalized missing/cross-tenant/inaccessible response |
| 409 | `CONVERSATION_IDEMPOTENCY_CONFLICT` | Zero mutation; preserve original canonical outcome |
| 409 | `CONVERSATION_STATE_CONFLICT` | Reconcile timeline before next command |
| 410 | `CONVERSATION_CURSOR_EXPIRED` | Fetch an authoritative timeline snapshot |
| 422 | `CONVERSATION_RETRY_NOT_ALLOWED` | Original is not failed/unresolved or identity does not match |
| 423 | `CONVERSATION_STOPPED` | Stop remains active; ordinary retry/reconnect cannot release it |
| 429 | `CONVERSATION_RATE_LIMITED` | Honor `Retry-After`; keep same command identity |
| 503 | `CONVERSATION_EXECUTION_UNAVAILABLE` | Explicit unresolved state; no fabricated professional response |
| 503 | `CONSTITUTIONAL_ENGINE_UNAVAILABLE` | Fail safe per ADR-031; no execution/model dispatch |

Internal PR errors use the corresponding execution codes: `EXECUTION_REQUEST_INVALID`, `EXECUTION_NOT_ACCESSIBLE`, `EXECUTION_IDEMPOTENCY_CONFLICT`, `EXECUTION_SCHEMA_UNSUPPORTED`, `EXECUTION_STOPPED`, `EXECUTION_DECISION_SPACE_STALE`, `EXECUTION_CONSTITUTIONAL_UNAVAILABLE`, and `EXECUTION_RUNTIME_UNAVAILABLE`.

## 9. F3 Acceptance Mapping

| Acceptance ID | Contract evidence |
|---|---|
| UX-CONV-01 | BP send `202` and independent delivery/processing/evidence states prohibit premature success |
| UX-CONV-02 | Original-key/hash retry and one canonical `messageId` |
| UX-CONV-03 | Timeline `authoritativeCursor`, `clientMessageId`, `Last-Event-ID`, cursor-expiry reconciliation |
| UX-CONV-04 | Versioned delta/completion/cancel events; `partial` and completion reason |
| UX-CONV-05 | Separate delivery, processing, and evidence enums |
| UX-CONV-06 | Versioned Action, Plan, Deliverable, and Decision cards with owner/state/effect/commands |
| UX-CONV-07 | Relationship-bound paths, cursors, drafts, client IDs, and normalized tenant authorization |
| CCT-UX-HO-01 | Existing persistent Stop remains independent and reachable; F3 does not change transport |
| CCT-UX-HO-02 | `stop.applied`, `STOPPED`, partial completion, and no Stop release through reconnect |
| CCT-UX-HO-03 | Existing dedicated Stop confirmation contract remains authoritative |
| CCT-UX-EF-01 | Evidence `PENDING` precedes CE-confirmed `RECORDED` |
| CCT-UX-EF-02 | Delivery and evidence states are structurally independent |
| UX-PWA-03 | Relationship-local unsent draft plus reconcile-before-submit algorithm |
| UX-RES-01 | `UNRESOLVED`, stable idempotency identity, correlation ID, no timeout success |
| UX-CONTRACT-01 | Public operations/stream exist only in BP; PR operations are `x-internal` |
| UX-SHELL-02 | Every relationship path is server-authorized before protected data |
| UX-PRIV-01 | No sensitive values in URL/telemetry; no authenticated service-worker caching |
| CCT-UX-A11Y-04 | Event semantics support one polite announcement per state transition without focus movement |

## 10. Dependency Gates

| Gate | Requirement | Status after this contract |
|---|---|---|
| G-F3-01 | BP timeline/send/retry/read-position/cancel/SSE OpenAPI is canonical and generator-compatible | CLEARED — R-059 |
| G-F3-02 | PR internal execution/cancel/SSE OpenAPI is canonical and explicitly internal | CLEARED — R-059 |
| G-F3-03 | Message, card, event, idempotency, error, privacy, tenant, and reconciliation semantics are complete | CLEARED — R-059 |
| G-F3-04 | All F3 acceptance IDs map to contract evidence | CLEARED — R-059 |
| G-F3-05 | Independent INST-004 review approves the package | CLEARED — R-059 APPROVED |
| G-F3-06 | OpenAPI validation and generated BP TypeScript client compatibility pass without manual patches | CLEARED — OpenAPI Generator 7.17.0 and strict TypeScript PASS; R-059 confirmed |
| G-F3-07 | C-095 determination: no new deployable platform component; existing BP and PR manifests remain controlling | CLEARED — R-059; no skeleton required for a new service |
| G-F3-08 | Selected F3 implementation session receives separate Founder/GO authorization | BLOCKED — this architecture session grants none |
| G-F3-09 | Deployment authorization | BLOCKED — separate Founder action required |

F3 implementation remains blocked until G-F3-08 is closed through separate authorization.
Deployment remains blocked by G-F3-09. F4-F8 remain outside this package regardless of F3 gate status.

## 11. Definition of Done

- BP is the only ordinary public conversation ingress and PR is internal-only.
- Timeline, send, retry, read position, cancellation, and streaming behavior are fully specified.
- Message, card, and stream schemas are versioned with explicit compatibility rules.
- Idempotency, privacy, tenant isolation, error, offline, unknown-outcome, Stop, and evidence behavior are deterministic.
- Every F3 acceptance ID maps to a contract surface.
- OpenAPI validation and generated-client compatibility evidence are recorded.
- Independent INST-004 review is recorded before architecture approval.
- No application code, frontend dependency, provider connection, F4-F8 work, or deployment is produced.