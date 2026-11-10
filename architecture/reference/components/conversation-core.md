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

Send replay reads current canonical message/execution state, not a stale acceptance receipt.
WC-134 customer-routed WhatsApp reads and retained replays additionally require the
current routing owner inside the owning PostgreSQL read transaction. This includes
timeline, execution/event replay, channel-skill context and recovered journey replies.
The full sender/Identity/participant/channel/canonical-conversation/Stop guard is
retained through materialization, with activation and recipient admission checked
at release. Stored content and empty results do not bypass current authority.
Read-position changes recheck after evidence; cancellation rechecks before its remote
request and before local commit. No routing locks span remote work. Unscoped Web and
service-guest paths retain their existing behavior.
Failed retry records retain an unresolved outcome and failure event. WC-134 WhatsApp
webhook replay does not invoke Retry/Start again, for either known failure or
unresolved acceptance. It queues one idempotent shared-Conversation system notice
directing the customer to the secure portal; an unknown outcome remains unknown.
Direct customer-routed Retry rejects unresolved delivery/outcome before evidence,
mandate resolution or Start, and rereads those states after owning row locks.
Queued admissions also remain ineligible for Retry. These restrictions do not
change the unscoped portal retry path or turn webhook replay into fresh authority.
The original persisted mandate is reused only after current owner authority and its snapshot
integrity are rechecked. Matching replay preserves the exact request/deadline; changed authority
or expiry fails closed. Durable runtime-status/event reconciliation after an ambiguous acceptance
remains a separate WC-134 recovery obligation.

The BP runtime event worker consumes the original execution's event stream only;
it has no Start/interpreter/provider dispatch dependency. A queued admission
retained after late route denial therefore is not implicitly redispatched.
Terminal treatment, real restart and revoked-authority recovery remain unqualified.
WC-134 pending batch starts are excluded from both the runtime work claim and the
event worker's candidate query. This fence does not dispatch a batch or complete
pending messages; canonical SEND admission and batch dispatch remain separate work.

For WC-134 signed WhatsApp ingress, the transport name is not a runtime skill. BP resolves the
relationship's accepted, applicable, currently granted/constrained skill. With several candidates,
only a still-authorized last customer skill from the same environment and canonical relationship
may supply the context; absent or ambiguous context returns an explicit selection conflict.
An actor-bound accepted send retry retains its stored skill without restoring revoked authority
for a new message. Normal mandate resolution still checks the exact admitted runtime binding,
contract, goal and current Decision Space before new execution. These implementation checks do
not constitute production-DI reply delivery or live cross-channel acceptance.

For WC-134 journey guidance, unavailable skill selection can instead commit a fixed canonical
system instruction to select the task in the secure portal, without a professional execution.
Replaying that provider event preserves the guidance; a new message can use repaired owner context.
Progress and assurance-required guidance use the canonical outbound contribution owner, resolving
current workspace references rather than requiring a fabricated workspace version. Message,
`message.completed` event, outbox row and idempotency outcome commit atomically. Interrupted
provider-claim completion recovers the stored journey outcome without regenerating the reply.
This is queued system guidance, not proof of provider delivery, professional completion or evidence.
Stop remains a hard outbound fence.

For already attached public WhatsApp relationships, signed ingress retains an encrypted
sender-digest-bound destination with the provider timestamp. Outbox-owned resolution requires
current binding/participant role, consent, service window and fresh destination; decryption and
final egress recheck reject tampering, replacement and revocation. No route is accepted from a
browser-provided hash or direct proof call. Public authority may admit other valid sender digests
only in its exact Demo tenant, and reservations bind that actual sender while sharing the activation
budget. A missing destination never substitutes another person's pilot phone. This transport
resolution does not create account authority, a relationship binding or transcript transfer.

Shared WhatsApp guest writes and queueing use the ingress sender lock and recheck current Stop.
Customer-text persistence additionally requires current admission/consent evidence and notice
version; queueing validates the actual canonical GUIDE content/sequence. Fixed registration/link
outcomes are explicitly allowlisted guide-only notices. Admission/consent evidence is requested
outside the sender lock, then projected only after fresh Stop/authority/notice rechecks, so slow
evidence cannot block guest STOP or resurrect a withdrawn guest. Non-WhatsApp portal discovery
retains its existing participant-scoped contract.

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

ADR-046 mutual TLS and a single-use asymmetric BP delegated envelope are mandatory for these
three operations. There is no JWT/plain-HTTP fallback. BP uses the registered workload client
certificate, validates PR's exact SPIFFE identity and does not follow redirects. The envelope
binds method, registered route/operation/audience, actor, tenant, relationship, conversation,
original runtime execution, canonical message, CE decision reference, correlation and command
idempotency. BP sends the shared canonical body representation verbatim and signs its byte digest;
PR checks the received bytes without changing Unicode escaping. Start also checks the derived
execution/message/decision against its typed mandate. Cancel/stream rebind the original message
and execution; a stream envelope binds its cursor. Each retry gets a fresh envelope while preserving
the original command/mandate, not a renewed execution allowance.

PR derives authority only from the verified workload peer and envelope, never path/query/body
tenant claims. Missing workload material fails closed and degrades runtime readiness. Existing
legacy JWT authentication for unrelated PAAS/voice routes is not migrated by this increment.
The private listener is `private_server.py` (HTTPS port 5443 by default); BP credentials load
independently of unrelated workspace endpoint configuration.

PR returns `202` only after durable Temporal execution responsibility is accepted. Same key/hash returns the existing execution. Divergent reuse returns `EXECUTION_IDEMPOTENCY_CONFLICT`. CE unavailable, Stop active, stale Decision Space, or unavailable runtime returns an explicit fail-safe state; PR never starts model dispatch in those states.

PR events are internal facts, not customer truth. BP validates schema version, conversation/execution correlation, sequence monotonicity, and allowed state transition before persisting and projecting them. Unknown major versions halt that execution projection with `EXECUTION_SCHEMA_UNSUPPORTED`; unknown additive fields in the same major version are ignored.

WC-134 aligns new BP execution references with PR's existing UUID-v5 namespace
`f3e57984-3923-4f89-91bd-32453502471a` and UTF-8 colon-separated tuple of tenant, relationship,
actor, conversation and idempotency key (canonical lowercase UUIDs). Legacy local references are
not rewritten; retry still derives the original runtime identity from the original key. The HTTP
gateway checks the bounded acknowledgement body, correlation, required fields and acceptance/replay
state instead of treating any successful HTTP response as accepted responsibility.

The PR workflow applies consistent completed/failed events to its terminal state, rejects conflicting
terminal signals with `reconciliation.required`, and retains dedicated Stop precedence. Neither
validated start acknowledgement nor workflow state alone completes BP projection or proves a
customer reply: recoverable runtime-event ingestion remains a WC-134 delivery obligation.

The WC-134 BP event transport now signs the original execution/message/actor/tenant/relationship,
CE decision and committed `Last-Event-ID` cursor on the existing private SSE route. Each connection
has a bounded lifetime; each UTF-8 line/frame is capped at 262,144 bytes. Schema, frame/payload
identity, sequence continuity and typed payloads are checked before an event is returned.
Heartbeats do not advance the durable sequence. A truncated/nonterminal stream, malformed frame,
gap or divergent identity is an explicit failure, not completion. Owner Stop and expired cursor
remain distinct outcomes. Caller cancellation is preserved.

BP now has an authored runtime-event receipt/checkpoint projection and a scoped recovery worker.
The projection serializes with the shared Stop barrier, checks the original SEND identity and
current relationship participant, rejects gapped/divergent events and expired response mandates,
and commits the digest receipt, cursor, separate professional/system message, public event and
eligible terminal WhatsApp outbox together. Customer input text is unchanged. Public delta,
message, failure, reconciliation and read-only employment-decision card payloads use their
existing public schema shapes. PR evidence does not become CE-confirmed customer evidence.
Known bound AIR limitations produce an explicit system notice and FAILED terminal; unknown
outcomes remain recoverable reconciliation, not fabricated completion. Empty proposals are
rejected. A persisted proposal without its terminal signal can be reconciled on replay.

WhatsApp SEND persists the verified original binding and recipient digest. Delayed replies cannot
switch to a replacement binding. Missing/withdrawn binding and consent/window denial preserve the
full canonical Web outcome but explicitly record unresolved delivery. An output over 4096
characters remains complete in Web and produces a separate bounded SYSTEM portal notice,
atomically queued under the original recipient; it never silently truncates the professional
output or claims that a failed request succeeded. A separate runtime-terminal checkpoint allows output
recovery after an earlier owner-confirmed completion. Stream interruption retains committed
events and schedules retry with operational signals; caller cancellation is not converted to
success.

The worker is registered but `Wc120Conversation:RuntimeEventIngestionEnabled` defaults to false.
Migrations 88/89 add current Identity admission/commit row locks and a minimal owner-managed
work directory populated by verified canonical SEND, without transcript inventory or bypass-RLS
tenant scans. Immutable issuer/actor/account/membership and original routing coordinates bind each
execution. The owner claims one due environment-bound capability with `SKIP LOCKED` and rechecks
active actor/login/account/organisation and OWNER/MANAGER membership. Its tenant scope serves
Web independently of WhatsApp activation and cannot override a different HTTP/WhatsApp authority.
Projection rechecks current Identity in its commit transaction; runtime outbox egress rechecks
the same membership and immutable recipient again. Legacy executions without original Identity
coordinates fail closed rather than acquiring a newly fabricated authority.

Current response mandates reuse the existing resolver's exact replay checks, on the projection
transaction's connection: original digest, admitted artifact/runtime binding, skill, verified goal,
contract, Decision Space, revisions and deadline cannot be silently renewed. SEND admission is
committed and its transaction released before the private runtime call.
The same projection connection now loads the source, Identity, relationship, mandate and
WhatsApp eligibility within the commit transaction. Final completion/failure that releases an
existing reply revalidates the mandate too; expiry between a delta and terminal cannot queue the
reply or advance its cursor. Empty or SYSTEM-only output cannot become professional success.
Contact locks precede channel-binding locks, matching the relationship attachment owner.
The immutable-source guard belongs inside the deferred trigger, not its migration DO block;
deferred admission/input/execution/directory rollback and all frozen-coordinate regressions are
authored and compile, but have not been executed.

The current PR dispatch unconditionally constructs an `INDUCTION_CONTEXT` employment-patch
proposal. AIR configures only the disabled interpreter unless an interpreter is explicitly
injected. This is not an ordinary professional response path. Completing generation requires a
declared professional execution backend and exact prompt/model policy, governed provider access,
durable usage/budget evidence and unknown-outcome handling. It must not be replaced with an
ungoverned PSE/default CTG call or portrayed as complete because a SYSTEM notice is delivered.
Old executions without original Identity coordinates additionally require an explicit
owner-authorized remediation path; current membership alone cannot manufacture original authority.
The Founder requested preparation of the missing backend/policy for approval and selected
explicit fresh-owner, no-redispatch reconciliation. The approved operation separation, bindings,
bounds, durable accounting/result lifecycle and read-only recovery contract are recorded in
[the WC-134 approval supplement](../../../work-contracts/WC-134-runtime-generation-and-reconciliation-policy.md).
The Founder approved the implementation design on 2026-11-08. Approval does not admit a provider,
complete implementation, or activate traffic. On 2026-11-08 the Founder delegated selection of the
additive wire-contract details ("you decide", no revisions); sections 4.1 and 4.2 were selected
unchanged within the approved design and current-session implementation authority.

Complete governed professional generation/metering, legacy-authority remediation, full
PostgreSQL authority/Stop/binding/rollback races and integrated author review remain obligations
before activation. This is not completed runtime delivery or a readiness claim.
Projection/restart/Stop/recipient/limit, Identity revocation locks, private directory/environment
claims and tenant-interceptor regressions are authored; Docker compilation and migration lint pass.
Behavioral tests remain deferred until all implementation stories are complete.

WC-134 cancellation uses the original SEND actor/key to address PR's runtime execution and requires
current relationship access/membership plus CE evidence before private DELETE. BP accepts only a
bound confirmed terminal response: actual partial/reason/timestamp remain owner facts, and an
existing completion/failure is not relabelled cancellation. Stop propagates unchanged. Local
message/execution/event/idempotency commit after confirmation under relational row locks and
state reload; uncertain remote outcomes remain retryable with the same cancellation key.
An unconfirmed dispatch failure remains cancellable; a known terminal failure replays without
restarting the execution. Cancelled/Stopped work cannot be retried. Owner Stop (423 or STOPPED
replay) propagates for Start and DELETE. Stop during initial/redispatch persists FAILED delivery,
STOPPED processing, EMERGENCY_STOPPED completion and stop.applied with existing partial flags
preserved, using the SQL/API vocabulary rather than inventing a new delivery state/event.
Start/DELETE deadlines bound receipt-body reads as well as headers; caller cancellation is preserved.

WC-134 uses one tenant-wide advisory budget lock and rolling-minute count for guest traffic,
relationship provider replies and explicitly requested registration OTPs. Guest provider dispatch
records a traffic event and cost reservation atomically; the shared count excludes that duplicate
cost row while still counting relationship/OTP reservations without guest events. Tenant and strict
rolling-window predicates apply across activation renewal. The reserved final guest notice slot
uses this shared count, not an isolated guest allowance. Authority drift is checked against both
active ledgers before provider/OTP reservation. Activation-total pilot inbound accounting, model
cost instrumentation and full privacy/lifecycle qualification remain open obligations.

### 4.1 WC-134 Professional Generation Contract

**Status:** SELECTED UNDER FOUNDER-DELEGATED DESIGN AUTHORITY, 2026-11-08; NOT ACTIVATED.
**Authority:** Approved WC-134 runtime generation and reconciliation policy, sections 2-5.

PR resolves one declared operation from the exact ACTIVE admitted skill, its input/output schema
digests, permitted actions and professional adapter. Supported operation kinds are
`PROFESSIONAL_RESPONSE` and `EMPLOYMENT_CONTRIBUTION_INTERPRETATION`. Missing or ambiguous declarations
fail explicitly before either AIR operation is dispatched. Neither channel nor model output selects
the operation. Existing accepted execution identities and original mandates remain unchanged.

The optional `skillManifest[].conversationOperation` declaration is immutable admission content.
It contains `kind`, `governedAction`, `inputSchemaDigest`, `outputSchemaDigest`, `promptPolicy`,
`modelPolicy`, and, only for interpretation, an explicit `patchType`. Each policy reference contains
`ref`, `version` and a `sha256:`-prefixed digest. BP validates the declaration against the skill's
constitutional actions and current runtime schema/prompt binding before including it as optional
`operationalMandate.conversationOperation`. PR repeats the binding checks. Absent declarations
remain absent in legacy mandate serialization/digests; they never imply an induction operation.
Adding a declaration requires a newly accepted admission revision, not a legacy-data backfill.
New workflow dispatch inputs record `operationPolicyVersion: "1.0"` independently of the original
mandate. Pre-policy inputs remain read-only recovery: a missing declaration cannot be reclassified
as a known failure, redispatched, or supplied with fabricated policy coordinates.

`PROFESSIONAL_RESPONSE` uses the separate bounded generation contract in
[AI Runtime section 1.1](./ai-runtime.md#11-wc-134-bounded-generation-wire-contract).
Employment interpretation retains its typed proposal contract; an ordinary response cannot apply
an employment patch or imply completed business work. A professional specification digest must
never be substituted for an independently resolved model-policy digest.

The accepted PR workflow durably owns the generation request and activity. It persists admission,
attempt identity, CE authorization, budget reservation and dispatch state before inference.
Repeated activity execution reads the same result/attempt; it cannot redispatch an unknown
socket outcome. A durable result reaches the existing ordered PR event stream only after usage
and audit persistence. BP validates the original event identity and atomically commits its receipt,
checkpoint, canonical projection and eligible outbox. Empty/SYSTEM-only output is not professional
success. Unknown outcomes remain unresolved; Stop/cancellation cannot fabricate non-dispatch or
zero usage. Both operations remain unavailable when their exact required owner bindings are absent.

### 4.2 WC-134 Fresh-Owner Read-Only Recovery Contract

**Status:** SELECTED UNDER FOUNDER-DELEGATED DESIGN AUTHORITY, 2026-11-08; NOT ACTIVATED.
**Authority:** Approved WC-134 runtime generation and reconciliation policy, section 6.

Public BP command:

`POST /api/v1/employment/relationships/{relationshipId}/conversation/executions/{executionId}/reconcile`

The closed `ReconcileConversationExecutionRequestV1` body contains only `schemaVersion: "1.0"`,
`expectedMessageId` (UUID), and `expectedProjectionVersion` (nonnegative owner-issued integer).
Existing `Idempotency-Key` and correlation headers remain mandatory. BP derives tenant, requester,
relationship access and original execution/source identity; none is caller-supplied authority.
The version is checked against the persisted execution projection, never a browser counter.
`GET /api/v1/employment/relationships/{relationshipId}/conversation/messages/{messageId}/execution`
provides the tenant-authorized original execution identity and projection version without a
runtime call. The Web adapter reads this projection on explicit "Check original runtime result"
intent and submits the shared recovery command. It neither reconstructs dispatch identity from
local storage nor retries inference; UNKNOWN is rendered as operator reconciliation required.

Fresh Identity authentication, current OWNER/MANAGER membership, relationship access and explicit
CE permission for `READ_EXISTING_RUNTIME_RESULT` precede a separate five-minute reconciliation
authority record. It binds requester/issuer/account/membership, original execution/source digest,
current relationship/Decision Space, CE decision/evidence, expected projection version and request
idempotency. It does not fill missing original authority fields or extend the original mandate.

Private PR operation:

`POST /api/v1/internal/conversations/{conversationId}/executions/{executionId}/reconcile`

This is a read-only terminal-result lookup, not Start, Resume, cancellation, a workflow signal or
inference admission. ADR-046 mTLS and a fresh signed delegated envelope bind the distinct original
source and current requester under purpose `READ_EXISTING_RUNTIME_RESULT`. The closed body
contains `schemaVersion`, `originalMessageId`, `originalSourceDigest`, `afterSequence`,
`reconciliationAuthorityId`, `permissionExpiresAt`, and `expectedProjectionVersion`.
Tenant/requester/CE coordinates come from the verified envelope, not these fields.

The bound result contains `schemaVersion`, `conversationId`, `executionId`, `originalMessageId`,
`originalSourceDigest`, `reconciliationAuthorityId`, `state`, `events`, `originalRequestDigest`,
`resultDigest`, and `nextAction`. Returned terminal states are `COMPLETED`, `FAILED` and `CANCELLED`.
STOP returns the existing 423 problem; unavailable/malformed retained results return the existing
503 problem with an operator-recovery title. `UNKNOWN` carries no result/events and requires
`OPERATOR_RECONCILIATION_REQUIRED`; a valid terminal returns `RECONCILE_CANONICAL_PROJECTION`.
Source/version divergence is a conflict, not a new request. Only durably stored, exactly bound
terminal events are returned; lookup cannot schedule missing work or fabricate a terminal result.
`resultDigest` binds the canonical returned terminal/event payload and is absent without a result.

The exact original-source fingerprint and original request digest are specified in
[WC-134 runtime policy section 9.4](../../../work-contracts/WC-134-runtime-generation-and-reconciliation-policy.md#94-original-source-and-terminal-snapshot).
The original actor comes from the immutable source, not the fresh requester. The signed envelope's
command id is the reconciliation authority id, subject is the conversation, and expected versions
bind `message`, `source_digest`, `projection_version`, `after_sequence`, current `decision_space`,
`constitutional_decision` (`ce-decision:{UUID}`) and `constitutional_evidence` (`ce-evidence:{UUID}`).
Its effective role is current OWNER or
MANAGER. Both the signed envelope and five-minute permission must still be active after lookup.
A single `GetConversationExecutionTerminalSnapshot` query returns source state and terminal events
consistently, without depending on the caller process's inference/activity worker. At most 4096
retained events are returned; missing, gapped, divergent or system-only completion is unavailable.
The cursor can equal the terminal sequence for an empty, idempotent tail, but cannot exceed it.
The BP projection version remains an independent BP transaction check, not a PR workflow revision.

BP persists `projection_version` on the execution and advances it on every EF-owned execution
mutation, including cancellation and runtime progress. Current execution status exposes that
nonnegative version. Recovery request replay uses requester/execution/idempotency plus the exact
request digest; expiry or changed membership/Decision Space cannot replay authority as current.
The separate authority stores the original source and owner-issued PR request/result digests,
fresh requester/issuer/account/membership/role, Decision Space snapshot/version, CE evidence,
five-minute expiry and expected projection version. Original execution authority fields are immutable.
Fresh Identity and participant/relationship rows are locked and rechecked at admission and projection;
CE and the private lookup run outside those transactions so they cannot hold Stop locks.
The complete event tail, receipts, canonical reply, projection version, authority result and any
eligible outbox commit in one transaction. Any validation error rolls them all back. Expired or
unknown lookups persist no success-shaped outcome. A recovery outbox reference includes the
authority id; egress independently rechecks its expiry/current membership/Decision Space and
the persisted original recipient before sending. Legacy missing recipient is Web-only.
The final runtime WhatsApp egress admission uses one connection/transaction for the dispatch
barrier, execution, outbox lease, canonical message, current Identity, relationship/participant,
contact and original binding checks. The canonical text must still match the queued digest;
erasure or replacement denies egress while preserving the already committed execution outcome.
Recovery expiry is checked again after lock waits. This transaction commits and releases its
locks before the provider socket; it does not hold the Stop barrier across an external call.
Provider activation and credential validity are rechecked after admission. An already admitted
provider attempt remains subject to the existing unknown-outcome accounting and cannot be
described as cancelled merely because Stop subsequently occurred.

BP projection uses an explicitly separate permission mode, rechecking fresh authority and
membership inside the commit transaction. Existing receipt uniqueness remains keyed to the
original event. Repeated recovery cannot create duplicate messages or sends. STOP, revoked
membership, permission expiry or divergent replay fences projection and delivery.
WhatsApp additionally requires the persisted original recipient/binding, current consent/window
and fresh permission. Missing legacy recipient coordinates produce Web-only recovery, never a
destination inferred from today's number or binding. Existing public projection/problem schemas
carry the result; no transcript is copied or transferred and unknown work remains unresolved.

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