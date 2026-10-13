# WC-120 - Channel-Neutral Conversation And WhatsApp Implementation

## Record Control

| Field | Value |
|---|---|
| Work Contract ID | WC-120 |
| Authoring office | Chief Solution Architect (INST-005) |
| Assigned implementation office | Platform IT Expert (INST-010), only after the gates in this contract pass |
| Status | READY_FOR_STRATEGIC_PLAN - SPECIFICATION INTEGRATED AND DOCKER-VALIDATED; IMPLEMENTATION UNAUTHORIZED |
| Current-main baseline | `c2a1baf64cb3b2652ce29ed930ac4a60f14e73bb` |
| Source PR | PR #499, merged as `c2a1baf64cb3b2652ce29ed930ac4a60f14e73bb` |
| Candidate solution package | `architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md`, repaired WC-120 version `1.0.0-candidate.2`; pinned PR #499 source blob `224d8f43f2a46e810eb5b13aac35570b6f0ebcda` |
| Candidate channel-neutral API | `architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml`, repaired WC-120 version `1.0.0-candidate.2`; pinned PR #499 source blob `77b7875a0d294be3aba21534bf33cd92c7527e15` |
| Compatibility crosswalk | `work-contracts/WC-120-operation-schema-owner-compatibility-crosswalk.md` |
| Controlling enterprise input | PR #498 reviewed head `65add4540698116b00be1ec72e6000333d05eac9`, merged as `4a4420af6ee132623d6b87eb3863d700e56c9b86` |
| Existing Conversation Core | `architecture/reference/components/conversation-core.md`, blob `1004255bbd01e3d10dd53a64a2b115ac059ad631` |
| Existing WC-114 / WC-115 | `work-contracts/WC-114-conversational-employment-solution-contract.md` blob `11ba639efa43d3288ba1eb39fd2e05308c42e6c0`; `work-contracts/WC-115-conversational-employment-implementation.md` blob `337fcef0a51a4c2ef2ff72423a7afc64969d8914` |
| Existing BP and employment APIs | `architecture/reference/api-specs/business-platform.openapi.yaml` blob `406153fec469a5bf6b5919000110a6af1dfa6a46`; `architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml` blob `bf7d3466c4113049f9f61200583811a25e454951` |
| Accepted specialist profile | `architecture/reference/api-specs/conversational-employment-specialist-profiles.yaml`, blob `9c7ccecd64791010f1ba15b69d9b8a128d466d66` |
| Prior single-pass reviews | R-146 Security blob `e7ba98253092b7283fc70422fcf5539aab006d5c`; R-147 Data blob `df8e78409c0cc7afc4177ab5f181971af46b3f2f` |
| Constitutional basis | C-039, C-059; CE-FIT-01 through CE-FIT-16; ADR-051, ADR-052, ADR-053 |

### Founder Authorization And Accepted Decisions

On 2026-10-12, the Founder explicitly directed that ADR-051, ADR-052, and ADR-053 are
approved and authorized, and directed that this decision be recorded in this Work Contract.
This is the acceptance evidence for this bounded scope. ADR-051 is accepted before ADR-052;
ADR-052's acceptance dependency is therefore satisfied. ADR-053 is accepted subject to the
accepted channel-neutral conversation and policy decisions in ADR-052.

This decision resolves the ADR-acceptance prerequisite recorded in CB-010. Any earlier
`Proposed - Founder review required` status captured in a prior snapshot is superseded for
this scope by the Founder decision recorded here. This records ADR acceptance only: it is
not approval of this Work Contract's implementation, current-session authority to write code,
or permission for provider, cloud, deployment, traffic, or activation actions.

The Founder separately authorized the authoring of this contract in the current conversation.
That authority is limited to recording and preparing the governed implementation package.

### Explicit Status Replacement

For the PR #499 solution package, this Work Contract replaces the former status
`DRAFT - IMPLEMENTATION HANDOFF BLOCKED` with:

> **FORMALLY RECORDED - ADR-051/052/053 FOUNDER-ACCEPTED; SPECIFICATION CLOSURE
> COMPLETE; READY_FOR_STRATEGIC_PLAN; SEPARATE IMPLEMENTATION AUTHORIZATION REQUIRED**

This is the recorded status of the work component, not a claim that its source package was
rewritten or independently re-approved. ADR-051/052/053 acceptance supersedes the stale
"Proposed - Founder review required" labels in the PR #499 candidate for this governed scope.
WC-120 does not override source history or reviewer verdicts. The compatibility crosswalk, seven specification corrections, required specialist contributions,
and exact Docker-only ledger/OpenAPI validation are complete in this package. The specification is
`READY_FOR_STRATEGIC_PLAN`. Founder acceptance of this exact integrated Work Contract and separate
explicit current-session implementation authorization remain required before implementation;
protected Legal/Founder/provider/platform decisions remain fail-closed at their named later gates.

## 1. Objective And Authority

WC-120 governs the additive WhatsApp transport and cross-channel continuity work described
by PR #499. It does not replace, fork, or create another Conversation Core, relationship
workspace, transcript, API owner, context/profile store, or employment protocol. Existing
BP Conversation Core and the Founder-accepted WC-114/WC-115 contracts remain authoritative
for their existing surfaces and behavior.

Source precedence is: Founder-authorized constitutional decisions and accepted ADRs; the
merged PR #498 enterprise architecture; the existing Conversation Core and WC-114/WC-115
contracts for already-owned behavior; then the PR #499 solution package and candidate API
only where they are compatible with those controlling inputs. WC-120 adds stricter
implementation gates and does not silently supersede any owner contract. A conflict,
duplicate operation, or missing compatibility mapping is a stop for Founder direction.
PR #499's 27 stories, candidate schemas, runbook, CE-FIT mapping, failure/recovery, and
rollback remain the intended delivery decomposition subject to this precedence and the
closure gates below; they are not authority to invent or replace a controlling surface.

The target is one reusable channel-neutral conversation capability and one environment-
isolated WhatsApp adapter. Business Platform remains the public facade and canonical
conversation owner; Professional Runtime owns execution and Emergency Stop; AI Runtime
owns bounded context assembly and provider-neutral reasoning; Constitutional Engine owns
authority decisions and evidence. Web, WhatsApp, and future Mobile use common conversation
semantics; channel state is delivery/session state only. No new deployable Conversation
Engine service is introduced.

Before the Platform IT Expert can return `READY_FOR_STRATEGIC_PLAN`, the Chief Solution
Architect must close the PR #499 specification findings, complete the existing-contract
crosswalk, and obtain the specialist contributions in §2.2. After this Work Contract is
Founder-accepted and separate current-session implementation authority is granted, the
Platform IT Expert may perform the impact analysis, plan, and dependency-ordered additive
implementation within the exact reconciled package. No implementation file, test, generated
artifact, migration, executable configuration, or build output may be written before that
explicit authorization.

### Exclusions

- No source-code, test-code, generated-code, migration, or build-artifact changes under
  the current contract-authoring authorization.
- No new deployable, parallel conversation history/profile, channel-owned authority, or
  client-supplied tenant, policy, or authorization.
- No Meta/provider login or mutation, number purchase, Azure or other cloud mutation,
  DNS change, deployment, external traffic, activation, or Production apply.
- No reuse or publication of complete telephone identities, credentials, tokens, keys,
  provider payloads, or customer content in repository files, fixtures, logs, evidence,
  or PR text.
- No change to the controlling enterprise architecture, unaccepted decision, owner
  boundary, or product policy; no new technology or provider choice without its required
  decision and authority.
- No PR approval, merge, or representation of Founder approval beyond the explicit
  decisions recorded in this contract.

## 2. Required Inputs And Preconditions

| Input | Required state |
|---|---|
| PR #498 enterprise package and exact reviewed head | Merged; use the pinned head and controlling artifacts named by the PR #499 solution package |
| PR #499 solution package and candidate API | Merged candidate; preserve its compatible decomposition, subject to the precedence, crosswalk, and specification-closure gates below |
| Existing Conversation Core and BP API | Reuse the pinned Core and public API; no parallel timeline, unread/read position, command, or transport authority |
| WC-114 and WC-115 | Merged contracts; preserve their existing BP facade, Conversation Core, relationship workspace, owner boundaries, accepted specialist profiles, default-off posture, and rollback rules |
| WC-114 employment API and specialist profile | Use the pinned BP OpenAPI and profile as compatibility inputs; do not weaken, copy inconsistently, or bypass their operation, assurance, data, AI, product, or Stop controls |
| R-146 and R-147 | Treat the pinned Security and Data reviews as one-pass input records; their original verdicts remain `CHANGES REQUIRED`, and PR #498 §27 records author repairs, not reviewer re-approval |
| ADR-051 - Conversational Employment Workspace and Employment Readiness Protocol | Founder-accepted in this contract on 2026-10-12 |
| ADR-052 - Channel-Neutral Conversation Context and Policy | Founder-accepted in this contract on 2026-10-12, after ADR-051 |
| ADR-053 - WhatsApp Environment Isolation and Transport Boundary | Founder-accepted in this contract on 2026-10-12 |
| Existing ADR-023 phone identity and ADR-031 Emergency Stop assumptions | Verify current accepted owner contracts and exact behavior during CSA-CEWA-001; any mismatch is a stop, not permission to redesign |
| PR #499 open review threads | All seven findings below must be closed by corrected specification and direct validation before implementation may start |
| This exact WC-120 revision | Founder acceptance required before implementation planning or execution |
| Requirement/evidence ledger | `work-contracts/WC-120-requirements.yaml` maps each canonical WC120-RNNN obligation below; its digest must match this exact contract revision and pass `scripts/validate_requirement_ledger.py` in the repository Docker test runner before implementation planning or execution |
| Current-session implementation authority | Explicit Founder confirmation required before any runnable or implementation artifact is written |
| Environment/provider authority | Separate, exact authority required for each provider, cloud, DNS, deployment, traffic, activation, and Production action; none is granted here |

### 2.1 Specification Closure Gate

At the time WC-120 was prepared, the following PR #499 review threads were unresolved.
They are binding correction and test requirements for the contract/API package, not optional
suggestions:

| Review thread | Required closure |
|---|---|
| [R-4248036961](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248036961) | Declare the WhatsApp webhook wire media type as `application/json`; preserve exact raw bytes for signature verification before deserialization. |
| [R-4248037029](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037029) | Replace committed Demo/UAT telephone inputs with repository-safe suffix-only labels; ensure complete values are absent from current files and evidence. Any repository-history remediation must use an explicitly approved cleanup plan and must not silently rewrite shared history. |
| [R-4248037076](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037076) | Add the durable conversation read-position operation or a compatible successor; an event-stream cursor is not a substitute. |
| [R-4248037125](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037125) | Make registered command descriptors discoverable from interaction context or a typed command-catalog operation. |
| [R-4248037174](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037174) | Add an idempotent handoff-revert operation and request semantics that preserve the source binding. |
| [R-4248037216](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037216) | Constrain contribution variants so exactly one correctly typed, non-null payload is accepted for each discriminator. |
| [R-4248037259](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037259) | Replace free-form command parameters and command type with a closed, typed union of registered command schemas. |

The Chief Solution Architect records the corrected package revision and evidence that each
thread's observable predicate is covered. The implementing office must not infer or invent
these contracts in code. If any correction conflicts with the accepted enterprise package,
stop and return the conflict to the Founder rather than choosing an interpretation.

### 2.2 Existing-Contract Crosswalk And Specialist Review Gate

Before `CSA-CEWA-001` may return `READY_FOR_STRATEGIC_PLAN`, its evidence must map every
PR #499 candidate operation and schema to the existing BP Conversation Core and WC-114/WC-115
contracts, including canonical messages/order, durable read position, command discovery,
employment commands, channel binding/revert, identity/assurance, Stop, and generated-client
ownership. The crosswalk must identify reuse, compatible additive operations, and removed or
replaced candidate operations. A duplicate owner or incompatible wire contract is a stop;
the Platform IT Expert must not choose a successor or perform migration by inference.

This Work Contract requests one-pass, write-access review and bounded owner contribution from
the required offices listed in [WC-120 specialist review requests](../reviews/WC-120-specialist-review-requests.md):
Data Architect, Security Architect, Platform Architect, AI Architect, Product Owner, and Test
Champion. Each office must return a scoped disposition with exact finding IDs and contract
locations, or explicitly record no findings. The Chief Solution Architect repairs accepted
findings and updates the traceability ledger. A second review pass is not implied; material
owner-boundary changes or unresolved conflicts stop for Founder direction.

R-146 and R-147 were the one-pass Security and Data reviews of the PR #498 enterprise
architecture, not reviews of WC-120 or approval of downstream specialist contributions.
Their Section 27 author-remediation mapping is retained as input. Neither the historical
review verdict nor the existence of the remediation table is represented as post-repair
reviewer approval.

### 2.3 Data Profile Binding And Protected Decisions

WC120-R004, R006, R007, R010, R012, R014, R015, R023, R029, R036, R037, and
R039 inherit the accepted WC-115 data profile at blob
`9c7ccecd64791010f1ba15b69d9b8a128d466d66`; PR #498 §15 and PR #499 §§6,
12, 13, and 20 specialize it without weakening it. The implementation crosswalk must prove:

- BP remains the sole owner of canonical relationship conversation/message truth. Canonical
  append atomically reserves idempotency, checks protected-intent conflict, allocates sequence,
  appends the message, and publishes its outbox record. Consumer effect and inbox commit
  atomically. Inbound provider events, canonical commands, and outbound attempts use separate,
  complete idempotency namespaces; same identity and digest replay, while divergent reuse
  conflicts with zero additional mutation.
- Every tenant-scoped row, uniqueness key, reference, cursor, payload reference, worker lease,
  inbox/outbox record, provider correlation, and recovery job is bound to immutable environment
  and server-derived tenant context, plus relationship after resolution. Tenant stores use
  transaction-local context, tenant-complete composite references, `ENABLE` and `FORCE RLS`,
  and non-owner `NOBYPASSRLS` application and worker roles. Migration authority remains
  bounded to schema work and does not become a runtime bypass.
- Observations and corrections are append-only, acyclic supersessions using compare-and-swap.
  Profiles are reproducible projections. Summaries bind their exact source set or canonical
  sequence range and derivation contract/model/policy versions, and are invalidated by source
  correction, erasure, expiry, or incompatible policy/model changes.
- Customer/provider payload bytes and all media/transcript derivatives remain in the approved
  erasable payload boundary behind opaque references. Only a customer-confirmed transcript or
  correction may become a canonical contribution. Erasure removes resolvable payload links and
  derivatives while retaining only owner-permitted non-reconstructive replay tombstones and
  minimized evidence metadata.
- Existing WC-115 retention classes remain controlling wherever the record-to-class mapping is
  exact: constitutional evidence is permanent; plans, commands, and owner facts use relationship
  closure plus seven years; customer projection content uses relationship closure plus 90 days;
  idempotency and reconciliation use terminal outcome plus 30 days; AIR transient content is
  deleted within one hour after terminal state and has a 24-hour absolute maximum. Legal hold
  suspends erasure without rewriting history, backups inherit source expiry, and erasure
  verification is required.
- Backup and restore preserve canonical messages, sequence, idempotency, inbox/outbox, and dedup
  at one consistency point. Restore first targets an isolated non-routable environment with no
  provider authority, then proves schema watermark, forced RLS, composite references, sequence,
  replay protection, payload lineage, projection rebuild, and provider-egress denial.
- Evolution is forward-only expand -> idempotent backfill -> verify -> cutover -> contract, with
  resumable deterministic checkpoints, a mixed-version compatibility window, and no destructive
  down-migration. Rollback restores the prior reader/writer contract while retaining safe additive
  records, canonical decisions, and evidence.

The Data Architect fixes the following implementation controls for WC-120:

- Canonical sequence uses one BP allocator row per
  `(environment, tenant, relationship, conversation)`. Compare-and-swap or row locking advances
  `next_sequence` in the same transaction as idempotency reservation, message append, and outbox
  append. The database rejects duplicate composite sequence values. Provider time never orders the
  canonical timeline.
- Outbox and inbox ordering is
  `(environment, tenant, relationship, owner, aggregate_id, sequence)`. A lease is 60 seconds with
  a 20-second heartbeat. Retry delay is exactly
  `min(2^(attempt_number - 1) seconds, 300 seconds)` with no jitter, for at most 12 delivery
  attempts. Attempt 12 or a non-retryable schema/contract error enters `BLOCKED` poison disposition
  with payload-free evidence; silent discard is prohibited. Lease loss, restart, and takeover
  replay the same identity and digest.
- Canonical JSON uses RFC 8785 JCS plus SHA-256; provider ingress and binary payloads use SHA-256 of
  the authenticated exact bytes. Inbound provider event, canonical command, and outbound attempt
  use the separate identity tuples in PR #499 §6.2. Same identity and digest returns the original
  durable result; divergent digest returns conflict with zero additional effect. Unresolved
  identities never expire. Terminal replay tombstones expire 30 days after terminal outcome unless
  held.
- Tenant context is set transaction-locally from the authenticated server boundary and reset on
  transaction end. Every tenant-bearing primary/unique key and reference is environment- and
  tenant-complete; relationship is included after resolution. Application and worker roles are
  non-owner `NOBYPASSRLS`; tenant stores use `ENABLE ROW LEVEL SECURITY` and
  `FORCE ROW LEVEL SECURITY`. Migration credentials are schema-only, time-bounded, audited, and
  prohibited from runtime traffic.
- Observation supersession is same-owner, acyclic, append-only, and compare-and-swap guarded.
  Summary lineage stores the exact source IDs/digests or canonical sequence interval plus
  derivation-contract, model, and policy versions. Source correction, erasure, expiry, or an
  incompatible derivation version marks the summary invalid before it can be read as current.
- Migration backfill uses deterministic ascending owner primary-key order in batches of at most
  1,000 rows, commits a resumable watermark after each batch, and is safe to repeat. Cutover requires
  zero invariant violations and a candidate-bound restore qualification. Old readers remain
  supported for at least seven continuous days after cutover; contraction additionally requires
  zero old-reader traffic for 24 continuous hours, rollback-window expiry, and explicit authority.

The Data Architect also fixes this record-to-lifecycle mapping:

| WC-120 record | Lifecycle class and exact Data control |
|---|---|
| Inbound claim, normalized provider-event metadata, digest, inbox result, and replay tombstone | Existing `idempotency_and_reconciliation`: terminal outcome plus 30 days; unresolved records do not age out |
| Authenticated raw provider body | New `whatsapp_provider_transient`: encrypted erasable payload boundary; delete within 24 hours after durable normalization/rejection, while retaining only digest and non-reconstructive replay metadata |
| Delivery/status observation and opt-in/template decision evidence | Existing `plans_commands_owner_facts`: relationship closure plus seven years; append-only and payload-minimized |
| Accepted customer message, media, confirmed transcript, correction, and derived customer projection | Existing `customer_projection_content`: relationship closure plus 90 days; source erasure propagates to every derivative |
| Rejected, infected, expired, unknown, or abandoned quarantined media and derivatives | New `whatsapp_quarantine_transient`: delete within 24 hours after terminal verdict; never enters canonical context |
| Dead letter / poison disposition | No customer/provider payload; bounded reason, digest, opaque record reference, attempt count, and timestamps only; terminal outcome plus 30 days |
| Generated export artifact | New `customer_export_transient`: encrypted, single-purpose, delete within 24 hours of creation or immediately after verified revocation |
| Separately authorized protected diagnostic payload | New `protected_diagnostic_transient`: encrypted, purpose-bound, access-evidenced, non-exportable, and deleted within seven days; absent unless separately authorized |
| CE evidence reference | Existing constitutional evidence class; payload erasure removes reconstructive linkage but cannot rewrite CE evidence |

Legal hold is a scoped immutable record naming environment, tenant, affected record/payload classes,
legal authority reference, creator, creation time, and release authority reference. Hold suspends
physical erasure but never restores consent, eligibility, binding, or operational use. After verified
release, the erasure queue must start within 24 hours, complete all platform-controlled deletion and
derivative invalidation within 72 hours, and record completion or an honest unresolved
external-provider outcome. Hold creation/release authority and the legal basis for the four new
lifecycle classes remain Legal decisions; Founder acceptance is required where the resulting rights,
cost, or risk is material.

The Data Architect proposes these exact recovery targets for acceptance:

| Environment | RPO / maximum data loss | RTO |
|---|---:|---:|
| Demo | 24 hours | 8 hours |
| UAT | 4 hours | 4 hours |
| Production | 15 minutes | 2 hours |

Recovery covers one consistency group containing canonical conversation/message state, sequence
allocator, idempotency, inbox/outbox, dedup/tombstones, lineage, payload references, and immutable
delivery observations. Qualification restores to a non-routable no-provider-egress environment and
proves schema watermark, row counts/checksums, forced RLS, composite references, sequence uniqueness,
replay, lineage rebuild, source expiry, and projection equivalence before any reactivation.
Founder acceptance of the numeric recovery targets and any material recovery cost remains required.

Data-owned values and controls above are closed and may not be selected by the implementer. The
exact Core/WC-114/WC-115 operation/schema/store crosswalk, corrected PR #499 candidate, Legal
acceptance of hold/lifecycle legal basis, Founder acceptance of material lifecycle and recovery
consequences, and provider deletion capability are named external gates. Until the applicable gate
is accepted, only the affected persistence, contraction, restore activation, teardown, or external
erasure claim is stopped.

### 2.4 Security Profile Binding And Denial Invariants

WC120-R008 through WC120-R010, WC120-R012 through WC120-R020, WC120-R026, WC120-R028,
and WC120-R038 inherit these already accepted controls; this section creates no new policy:

- PR #498 §§12.1/14.2 and PR #499 §10.1 require the approved
  `X-Hub-Signature-256` HMAC-SHA256 form over bounded exact raw request bytes before
  decompression, normalization, parsing, or middleware transformation, with constant-time
  comparison. Invalid, oversized, malformed, or wrong host/app/WABA/recipient/environment
  input is denied before mutation. A previously unseen event is fresh only inside ADR-023's
  inclusive five-minute boundary against trusted receipt time. An already claimed authentic
  delayed retry instead replays its durable same-identity/same-digest result; same
  identity/different digest conflicts with zero additional mutation.
- ADR-023 and PR #498 §12.7 bind phone identity to environment, app/WABA, recipient,
  protected participant proof, current membership, relationship, and reassignment/revocation
  state. Phone possession never attaches an existing relationship. Tier 1 cannot expand
  authority; Tier 2 confirmation binds intent digest, subject, source version, and expiry;
  Tier 3 requires a fresh stronger factor; Tier 4 is portal-only and includes Stop release.
  Assurance is rechecked at commit and invalidated by completion/change/expiry, Stop/session
  loss, reassignment, revocation, membership/relationship change, or environment change.
- Accepted specialist profile blob `9c7ccecd64791010f1ba15b69d9b8a128d466d66`
  controls its listed employment-service calls through `security_profile.workload_identity`,
  `security_profile.assurance`, `security_profile.denial`, `freshness_profile`, and
  `emergency_stop_profile`. PR #498 §13.6 separately controls the WhatsApp adapter,
  media-scanner, and configurator identities, including runtime audience
  `urn:waooaw:service:whatsapp-adapter:<environment>`. Neither profile substitutes for the
  other. Wrong caller/purpose/audience/operation/environment/version/age/replay identity and
  unknown, unavailable, expired, revoked, superseded, or leaked authority fail closed.
  Rotation permits only the provider-supported overlap of current and immediately previous
  authorized versions. Emergency revocation stops new dispatch/retrieval, reconciles
  in-flight work without credential fallback, and rollback never restores revoked authority.
- PR #498 §§12.5/12.8/14.2-14.3 and PR #499 §§10.3/12/14 control media, Stop, and
  telemetry. Media stays quarantined until signature/type and bounded-resource validation
  plus an isolated clean scan verdict; mismatch, active/archive/polyglot/parser-capable
  content, expansion, malware, expiry, unknown, error, or timeout cannot enter professional
  context. Typed Stop is recognized after signature/binding verification but before context,
  model, queue, billing, or outbound work; it latches through CE outage and cannot be released
  by WhatsApp, retry, restart, reconnect, or ordinary operator action. Ordinary telemetry,
  exceptions, baggage, request capture, dead letters, and scanner diagnostics exclude payloads,
  headers, signatures, phone proofs, tenant/relationship identifiers, provider refs, prompts,
  transcripts, message/media metadata, template variables, context facts, and secrets.

All denials above use closed, non-enumerating outcomes, make no downstream owner call, and
create zero relationship, binding, command, conversation, dispatch, payload-promotion, or
authority mutation. Security evidence may record only accepted privacy-safe reason/reference
metadata. Tests must assert both state non-mutation and absence of prohibited telemetry.
Missing proof against the exact candidate is a stop; the implementer may not choose replacement
thresholds, audiences, operation classes, retention, diagnostic policy, or credential behavior.

#### 2.4.1 Security-Owned Exact Control Profile

INST-007 fixes the following security ceilings and floors for WC-120. Product, Data, Legal, or a
provider owner may narrow an enabled business subset or require longer retention, but may not weaken
these controls:

- Webhook POST accepts at most `1 MiB` of wire bytes and only `Content-Encoding: identity`.
  The limit is enforced while reading the raw stream, before buffering, decompression, middleware,
  JSON parsing, or owner calls. GET verification accepts only the exact expected parameters; each
  parameter is at most `1 KiB` and the complete request target is at most `8 KiB`.
- The unseen-event freshness boundary is inclusive `[-5 minutes, +5 minutes]` against trusted
  receipt time. A durable replay tombstone containing only compound event identity, canonical
  digest, and typed outcome is retained for at least `7 days` after the terminal outcome and longer
  when the provider retry, unresolved reconciliation, backup/restore, hold, or Data-owned lifecycle
  horizon remains open. Payload is not retained merely to satisfy replay prevention.
- WhatsApp runtime tokens and secret material are fetched just in time, remain in process memory for
  at most `5 minutes`, and are never persisted. Planned rotation may accept the current and
  immediately previous authorized version for at most `15 minutes`, only where the provider
  supports that overlap. Emergency revocation, leakage, environment mismatch, or supersession has
  zero overlap. A failed or unavailable live authority check denies new dispatch/retrieval.
- The WC-120 media security ceiling permits only non-animated JPEG, non-animated PNG, Ogg/Opus
  audio, and MPEG audio whose declared type, signature, and sniffed type agree exactly. SVG, GIF,
  PDF, video, archives, office documents, fonts, executables, scripts, HTML/XML, active content,
  polyglots, and any unknown/parser-capable format are denied. Product may enable a subset only.
  Downloaded bytes are capped at `25 MiB`; total decoded/expanded material at `100 MiB`; expansion
  ratio at `10:1`; decoded image size at `40 megapixels`; audio duration at `15 minutes`; parser
  CPU at `5 seconds`; parser wall time at `10 seconds`; scanner/parser memory at `256 MiB`; and
  parser recursion at `16`. Archive entries, document pages, video frames, and animation frames
  have a ceiling of zero. Scanner engine/policy/signature versions are immutable verdict inputs;
  signatures older than `24 hours`, unavailable version evidence, timeout, error, or inconclusive
  verdict remain quarantined.
- Ordinary telemetry uses only environment, service, build version, control/policy version, closed
  reason code, boolean outcome, minute time bucket, and bounded latency bucket. The closed security
  reason set is `SIGNATURE_INVALID`, `TOKEN_INVALID`, `REQUEST_TOO_LARGE`, `ENCODING_DENIED`,
  `FRESHNESS_DENIED`, `REPLAY_CONFLICT`, `BINDING_DENIED`, `ASSURANCE_REQUIRED`,
  `AUTHORITY_DENIED`, `AUTHORITY_UNAVAILABLE`, `MEDIA_DENIED`, `SCAN_UNAVAILABLE`, and
  `STOP_LATCHED`. No free text, exception text, request/event/provider/customer reference, raw
  duration, or high-cardinality label is permitted. A separately authorized protected evidence
  record may use a random opaque security-event reference, but it may not enter ordinary telemetry.
- The accepted Emergency Stop profile fixes the primary and fallback routes, excludes CE, BP, WBE,
  AIR, domain-adapter, and identity-provider dependencies from halt execution, requires the
  prewarmed authenticated Stop channel when the identity provider is unavailable, and sets
  end-to-end p99 to `250 ms` with PR halt confirmation target `50 ms`. These are maximums, not
  monitoring averages, and release still requires separate fresh Tier 4 portal authority.

Anything outside this profile is denied until INST-007 accepts a revised profile. Product media
locale/copy, Data/Legal payload lifecycle, provider account topology, and deployment values remain
with their named owners; this security profile does not decide or authorize them.

## 3. Permitted Surfaces And Delivery Components

### 3.1 Owner And Surface Boundaries

The Platform IT Expert may select only existing canonical surfaces directly owned by these
components, and must record the exact paths and consumers during CSA-CEWA-001:

| Owner | Bounded responsibility | Surface constraint |
|---|---|---|
| Business Platform (BP) | Public conversation facade, canonical conversation/message state, interaction context, policy projection, WhatsApp adapter boundary, delivery projection | Reuse the existing BP owners and contracts; no new Conversation Engine deployable or parallel history/profile |
| Professional Runtime (PR) | Professional execution, ordering, cancellation, reconciliation, and Emergency Stop behavior | Extend the existing runtime owner only; no channel-owned execution or reasoning |
| AI Runtime (AIR) | Bounded context assembly, research, analysis, provider-neutral reasoning | Consume server-resolved context and accepted references; no client prompt/policy authority or provider selection |
| Constitutional Engine (CE) | Authority validation, constitutional decisions, evidence | Preserve existing CE interfaces and fail-safe behavior |
| Phone Identity / WhatsApp adapter | Signed provider identity resolution and channel transport at the BP boundary | Preserve ADR-023 ownership; no tenant supplied by client and no shared environment identity |
| Web and future Mobile | Generated-client-backed presentation and shared API adoption | No direct PR/AIR calls, authority, or channel-specific conversation semantics |
| Data and persistence owners | Canonical persistence, ordering, outbox/inbox, migrations, RLS, retention, backup and restore | Existing owner and storage only; no new product or cross-owner writes |
| Deployment and operations | Environment configuration, secrets, telemetry, runbooks, recovery | Existing protected configuration only; provider/cloud changes require separate authority |
| Tests and evidence | Owner-local unit, contract, integration, security, migration, journey and qualification evidence | Repository-native paths discovered by impact analysis; do not invent a parallel test/evidence surface |

If an exact owner/path is absent, conflicts with a controlling contract, or would create a new
deployable or persistence owner, stop. Do not substitute a plausible path.

#### 3.1.1 AI Runtime Handoff Control

The BP context resolver remains the authority for context and policy selection. PR may hand AIR
only the minimum bounded contribution and server-resolved references required for the current
operation. The handoff binds the exact `InteractionContext`, Decision Space, plan/profile/source
versions, effective conversation-policy versions, operation family, relationship reference,
assurance, freshness, and permitted use. It never contains client-supplied instructions or policy,
raw customer identity, provider credentials, an unbounded transcript, unrelated history, or a
channel-selected model/provider.

Every assembled segment carries source identity and version, provenance, freshness, sensitivity,
trust class, and permitted-use metadata. Customer/provider/media/transcript/history/summary,
research/retrieval, tool/MCP output, and agent-produced content remain structurally separated
untrusted data. Instruction-like content cannot alter institutional or conversation policy, the
semantic catalogue, tenant/relationship, operation class, authority, or tool/command eligibility.
Every proposed tool call, command, patch, or context change is independently authorized against the
current server-owned context and source versions.

The pinned accepted `ai_profile` in
`architecture/reference/api-specs/conversational-employment-specialist-profiles.yaml` is mandatory:

- AIR independently canonicalizes RFC 8785/JCS request bytes excluding the digest field and verifies
  the SHA-256 digest and the accepted PR-workload/relationship/operation/idempotency/digest tuple.
- The BP-owned semantic catalogue is not caller-selectable and binds
  `catalogue_ref`, `catalogue_version`, and `catalogue_digest`; its entries bind patch type,
  operation, pointer template, value schema, and cardinality.
- Request, receipt, and result preserve `protocol_version`, `patch_type`, prompt-policy
  reference/digest, model-policy reference/digest, and `model_decision_ref`.
- AIR result states remain the closed accepted set: `PENDING` has no operations; `PROPOSED` has a
  non-empty operation set and no reason code; `UNREPRESENTABLE` and `FAILED` have no operations and
  require a closed reason code. Confidence grants no authority. Material uncertainty requires an
  unresolved question and prohibits operations.
- Transient raw content is encrypted, never logged, deleted within one hour after a terminal result,
  and never retained beyond 24 hours. The immutable digest-bound AI evaluation corpus must pass the
  WC-115-R101 digest, path, provenance, injection, minimisation, confidence, and
  unresolved-question oracles at 100%.

Research, inference, recommendation, and confirmed fact remain separate typed states. Research
retains source, capture time, and expiry; inference retains basis and remains unconfirmed;
confidence cannot promote either to fact; only the accountable source/owner can confirm. Source
correction, expiry, policy/model change, or material source-version change invalidates affected
derived context before consequential reuse.

Provider/model choice remains behind AIR's accepted model-policy boundary and is never delegated to
the channel or public client. AIR/model unavailability projects an explicit `UNAVAILABLE` outcome
with no synthetic response, operation, command, patch, or success. An unresolved in-flight outcome
projects `PENDING` internally and `UNKNOWN` only in the customer-visible reconciliation dimension;
it is not availability or success and cannot authorize blind retry. Missing/conflicting policy,
stale source, failed digest/provenance verification, prompt-injection contamination, or unknown
authority blocks before model invocation or consequential mutation.

Required negative evidence includes direct and indirect prompt injection, quoted-policy imitation,
hostile transcript/media/retrieval/tool output, cross-segment contamination, policy/catalogue and
tenant/relationship substitution, stale lineage, raw-identity/unrelated-history leakage,
channel/provider selection, unavailable model, and unresolved outcome. Any missing accepted
profile value, exact BP/PR/AIR contract crosswalk, or immutable evaluation-corpus binding is a
pre-implementation stop; the implementer must not invent a fallback.

### 3.2 Delivery Components

| Component | Source stories | Required output and exit evidence |
|---|---|---|
| WC120-00 - Baseline, Authority, And Impact | CSA-CEWA-001 | Exact source and ADR digests, existing-owner/path inventory, compatibility and risk analysis, and a signed `READY_FOR_STRATEGIC_PLAN` or `BLOCKED` result |
| WC120-01 - Shared Conversation Foundation | CSA-CEWA-002 through CSA-CEWA-008 | Frozen shared API, canonical history/order/outbox, server-resolved context and policy, observation lineage, cross-channel binding, deterministic identity and assurance; contract and denial tests pass |
| WC120-02 - WhatsApp Ingress And Delivery | CSA-CEWA-009 through CSA-CEWA-014 | Signed ingress, atomic claim/dedup/replay, normalized inbound, idempotent outbound, consent/window/template eligibility, independent delivery dimensions; provider-emulator and replay tests pass |
| WC120-03 - Media, Stop, And Operations Signals | CSA-CEWA-015 through CSA-CEWA-017 | Quarantine/scan/retention/erasure, Emergency Stop, dead-letter/alert/telemetry boundaries; hostile privacy and stop/recovery tests pass |
| WC120-04 - Environment Readiness | CSA-CEWA-018 through CSA-CEWA-020 | Demo provisioning/teardown, UAT stable-ingress readiness, and Production-dark evidence; each environment remains separately authorized and isolated |
| WC120-05 - Client Adoption And Data Recovery | CSA-CEWA-021 through CSA-CEWA-023 | Web compatibility, future Mobile contract, expand/migrate/contract, backup, restore, rollback, and invariant evidence |
| WC120-06 - Qualification And Founder Handoff | CSA-CEWA-024 through CSA-CEWA-027 | Bidirectional CE-FIT qualification, exact-candidate Docker validation, rehearsed runbooks, author review, residual-risk package, and Founder authorization gate |

The source package's per-story inputs, affected-owner analysis, migration/compatibility,
failure/retry/idempotency behavior, rollout/rollback, targeted tests, acceptance criteria,
evidence, and dependencies remain normative for every story. The delivery groupings above do
not replace those story-level contracts.

### 3.3 Accepted Platform Architecture Control Profile

The Platform Architect disposition for WC120-R041 accepts the following values already fixed by
ADR-053 and the PR #498/#499 architecture. This profile is specification evidence only and grants
no provider, cloud, DNS, deployment, traffic, activation, teardown, recovery, or Production
authority.

| Control | Accepted target and owner |
|---|---|
| Environment identity | Demo, UAT, and Production have distinct phone/provider identity, app/WABA authority, callback hostname/certificate, secrets, Key Vault/workload access, dedup/replay namespace, data/media, telemetry/alerts, templates, and deployment authority. Platform Architecture owns topology; Security owns credential/workload controls; BP/Data own application state. Cross-environment fallback or mutation target: `0`. |
| Ingress and callback | Environment-specific HTTPS hostnames are `whatsapp-demo.<approved-domain>`, `whatsapp-uat.<approved-domain>`, and `whatsapp.<approved-domain>`. UAT uses stable Azure ingress plus DNS/TLS hostname; Demo ingress is stable for its authorized lifetime; Production is stable and dark pending separate authority. The approved domain, certificate references, ingress addresses, and callback registrations remain protected configuration and separate Platform/Founder-authorized actions. |
| DNS/TLS/provider ownership | Platform prepares or applies Azure ingress, DNS, TLS, and callback routing only under environment-specific authority. The provider/configuration operator owns app/WABA and callback registration. Runtime may read its immutable binding but cannot mutate DNS, TLS, provider configuration, or deployment. |
| Egress | No stable outbound egress is required by default. Platform may specify an environment-specific egress address only when an authorized external dependency proves allow-listing is required; ingress and egress trust remain separate. During isolated restore qualification, provider egress target: `0`. |
| Protected configuration | Complete telephone identities, provider IDs, host bindings, certificate references, and secret values remain in environment-protected configuration. Adapter, media scanner, and deployment/configurator use separate environment-bound workload identities and audiences. A catch-all credential and cross-environment read are prohibited; rollback never restores revoked authority. |
| Telemetry and alerting | Environment-specific privacy-safe metrics cover verification denial, claim/replay, durable acceptance latency, context/policy state, outbound state/age, template rejection, media state/latency, handoff, idempotency conflict, Stop, environment denial, dead-letter age, erasure propagation, recovery consistency, and privacy scanning. Alerts classify customer action, provider outage, WAOOAW defect, security denial, stale authority, constitutional-governance unavailability, privacy leak, and recovery inconsistency. Prohibited telemetry/dead-letter disclosure target: `0`. Platform Operations owns routing/runbooks and the numeric alert profile below; emitting component owners own signal correctness; Security/Data own privacy and retention controls. |
| Recovery and rollback | Data owns backup policy, consistency groups, restore procedure, and RPO/RTO proposals; Platform owns infrastructure execution; Founder gates material cost/risk and UAT/Production recovery activation. Restore first enters an isolated, non-routable environment with separate temporary workload/encryption authority and no callback, outbound dispatch, template, or provider credential. Application rollback preserves additive schema/history/evidence and cannot reverse provider, DNS, or customer-visible effects. |
| Demo teardown | Disable callback acceptance or expose explicit unavailable response first; reconcile or isolate unresolved work through provider retry/dedup/hold/erasure horizons; revoke temporary authority; expire/erase eligible payloads; retain required tombstones/evidence; and prove UAT/Production bindings changed by `0`. Teardown is a separately authorized Platform/provider/Data action. |
| Production | Production remains dark. Number purchase, provider/app creation, DNS/provider mutation, deployment, traffic, activation, recovery activation, rollback execution, or cancellation requires separate Founder authority. |

#### Platform-Owned Service Objective And Alert Profile

The following targets are fixed by Platform Architecture for WC120-R041. An **eligible interval**
is time in which the exact environment is separately authorized, enabled, outside an announced
maintenance window, and expected to accept traffic. Provider delivery after WAOOAW durable
acceptance is excluded from ingress availability but remains visible through the outbound and
reconciliation objectives. Production-dark readiness proves configuration and synthetic
non-routing checks; it does not start a customer-traffic SLO or authorize activation.

| Objective | Exact target and measurement window |
|---|---|
| Callback ingress availability | Demo: `>=99.0%` over each rolling 24 eligible hours. UAT: `>=99.9%` over rolling 30 eligible days. Production, only after separate activation: `>=99.95%` per calendar month. Success is an environment-bound HTTPS callback reaching the healthy BP adapter and producing the correct challenge or authenticated application response; DNS, TLS, ingress, and adapter failures count. |
| Durable signed-event acceptance | From trusted receipt after bounded body acquisition through atomic durable claim/outcome: `p95 <=1 s`, `p99 <=2 s`, and no eligible request `>5 s`, evaluated over rolling 15 minutes. With fewer than 100 eligible events, the 5-second per-event ceiling and an environment-bound synthetic claim probe apply. Invalid input is excluded from latency percentiles but its fail-closed response and zero mutation remain mandatory. |
| Outbound queue and reconciliation | Eligible canonical outbound work reaches first provider-attempt state at `p95 <=30 s`, `p99 <=60 s` over rolling 15 minutes; oldest eligible queued item is `<=120 s`. A provider timeout or unknown result reaches a durable reconciled terminal or explicitly `UNRESOLVED` state within `15 min`; retries never create another logical dispatch. |
| Emergency Stop propagation | From durable, verified Stop receipt: PR halt confirmation target `<=50 ms`; latched fence visible at BP/PR enforcement points `p95 <=100 ms`, `p99 <=250 ms`, hard ceiling `1 s`, rolling 15 minutes. Every consequential operation after receipt is denied; CE or identity-provider outage, duplicate delivery, restart, and simultaneous channels do not relax the ceiling or latch. |
| Isolation and disclosure | Cross-environment fallback/mutation, provider egress during isolated restore, prohibited telemetry/dead-letter disclosure, and UAT/Production binding changes during Demo teardown each equal `0`. Any occurrence consumes the entire error budget. |

Platform Operations owns the following routing and timing controls:

| Alert | Exact trigger | Required response |
|---|---|---|
| Isolation, privacy, Production-dark, or Stop hard-ceiling breach | Any single occurrence | Detect within `1 min`; page delivery within `5 min`; acknowledge within `10 min`; fence the affected path or environment within `30 min`. |
| Availability error-budget burn | `>=14.4x` burn over 1 hour or `>=6x` over 6 hours against the applicable environment target | Page within `5 min`; acknowledge within `15 min`; begin mitigation within `30 min`. |
| Durable-acceptance latency | `p99 >2 s` for 5 consecutive minutes or any request `>5 s` | Page within `5 min`; acknowledge within `15 min`. |
| Outbound queue/reconciliation | Oldest eligible item `>120 s` for 5 minutes, or any unknown outcome remains unreconciled `>15 min` | Page within `5 min`; acknowledge within `15 min`; suspend unsafe retry when outcome identity is uncertain. |
| Recovery inconsistency or provider egress in isolated restore | Any checksum/invariant mismatch or any provider egress | Fail qualification immediately, page within `5 min`, and keep the restore non-routable. |
| Dead-letter age | Oldest actionable dead letter `>15 min` | Notify the owning component within `5 min`; page if age reaches `30 min` or growth continues for 15 minutes. |

Every alert uses environment-specific routing, privacy-safe opaque references, a named component
runbook, and retained delivery/acknowledgement evidence. Missing signal emission or alert delivery
is itself a failed oracle; silence cannot satisfy an SLO.

Data owns the numeric recovery profile under PR #498 §15.9. WC-120 §2.3 now fixes the proposed
limits at Demo RPO/data loss 24 hours and RTO 8 hours, UAT RPO/data loss 4 hours and RTO 4 hours,
and Production RPO/data loss 15 minutes and RTO 2 hours. Founder acceptance of those material
cost/risk limits and candidate-bound recovery evidence remain required before recovery or promotion.
That acceptance stop applies to WC120-R023, not the closed Platform-owned WC120-R041 specification.
Provider, cloud, DNS, deployment, traffic, teardown, recovery, and Production actions remain
separately authorized.

### 3.4 Accepted Product Control Profile

The INST-011 Product Owner disposition accepts `WC-120-product-acceptance-matrix.yaml` as the
controlling WC120-R042 profile. Product-owned choices are closed:

- initial supported locale is `en-IN`; unsupported locale is explicit and creates zero
  consequential action;
- customer copy targets Flesch-Kincaid grade `<= 8`, sentences `<= 20` words, and one primary
  action per turn, with only recorded legal/proper-name/provider-text exceptions and an adjacent
  plain-language explanation;
- text, card, interactive, and audio renderings preserve the same state, action, authority,
  consent, limitation, and consequence; audio always has a text alternative and no audio-only
  confirmation, correction, cancel, or Stop control;
- exact consent, service-window, template, media, correction, confirmation, cancellation, stale,
  ambiguous, blocked, and unavailable copy and actions are those in the matrix;
- initial Product media support is an `en-IN` WhatsApp voice contribution no larger than
  `5 MiB` or `120 seconds`; all other media is unsupported for the initial release, and a stricter
  accepted Security, Data, or provider limit controls;
- accessibility target is WCAG 2.2 Level AA with the matrix's keyboard, focus, live-region,
  non-color, screen-reader, zoom, and always-reachable Stop controls; and
- the matrix's direct oracles are normative. Test Champion binds their exact Docker-only selectors
  during approved implementation; evidence that cannot exist before implementation is expected-fail,
  not a Product specification blocker.

Legal/Founder retains material consent-rights and purpose policy; Security retains media admission
and safety; Data retains lifecycle/retention/erasure/legal hold; provider/Platform owners retain
provider constraints, configuration, deployment, and activation. Those named dependencies fail
closed for the affected capability and do not reopen a Product-owned value.

## 4. Definition Of Done

WC-120 is complete only when all of the following are evidenced:

1. The controlling inputs are reconciled by the source precedence in §1; the PR #499 package
   and API are versioned only where compatible with the exact PR #498 head, existing Core,
   WC-114/WC-115, and Founder-accepted ADR-051/052/053.
2. Every normative obligation, compatibility crosswalk item, specialist contribution, and
   specification-closure finding has a stable WC120-RNNN requirement, owner, dependency,
   acceptance oracle, targeted test, evidence location, and failure/rollback behavior in
   the validated ledger.
3. The Platform IT Expert's impact analysis is `READY_FOR_STRATEGIC_PLAN`; it traces current
   behavior and exact owning paths without changing implementation.
4. The implementation plan freezes shared contracts before consumers, preserves the
   story dependencies below, defines compatibility windows and feature gates, and assigns
   the smallest repository-native tests to every story.
5. All 27 stories meet their source-package acceptance criteria. The
   `WC-120-fitness-evidence-matrix.yaml` contains CE-FIT-01 through CE-FIT-16, each mapped
   bidirectionally to stories, direct positive/boundary oracles, exact Test Champion-selected
   repository test selectors, candidate identity, and evidence location.
6. API/OpenAPI validation proves the specified 16 paths, 17 operations, and 28 local schemas,
   resolves all 156 local references plus the pinned external employment-command schema
   reference, and covers every correction in the Specification Closure Gate.
7. Data evolution follows expand -> migrate -> contract; migration, backup, restore, and
   rollback evidence passes before any destructive contraction or environment promotion.
   Recovery evidence records environment, injected fault, commands, watermark, accepted
   RPO/RTO and data-loss bounds, invariant/checksum oracle, and provider-egress denial.
8. Every story's targeted unit, contract, integration, static, security/privacy, migration,
   and compatibility checks pass before final Docker qualification.
9. Final Docker, image, and containerized end-to-end qualification runs once on the complete
   exact candidate after all targeted tests and implementation author review pass. An
   immutable `test-results/wc120/candidate-manifest.json` binds source commit; Work Contract,
   requirements-ledger, solution, API, Product-matrix, and fitness-matrix digests; application
   image and test-runner image digests; schema and migration watermark;
   configuration/feature-flag versions; targeted tests; recovery; CE-FIT results; and final
   qualification. Any relevant change invalidates affected evidence and reruns impacted targeted
   tests plus final qualification.
10. The operational runbook is complete and rehearsed in an authorized non-production
    environment; environment isolation, teardown, recovery, privacy-safe telemetry, and
    Emergency Stop evidence pass.
11. The implementation author review records PASS against the exact 40-character candidate
    commit, with all findings resolved or the contract marked BLOCKED.
12. Founder handoff contains the candidate identity, verified evidence, open risks, rollback
    and recovery instructions, remaining authority decisions, and exact decisions requested.
    No deployment, provider action, traffic, activation, Production change, approval, or merge
    is inferred from completion.
13. The one-pass Data, Security, Platform, AI, Product, and Test Champion review requests
    have scoped dispositions, and the Chief Solution Architect's repairs are recorded without
    misrepresenting any office decision.
14. The Product Owner accepts the customer-state and accessibility matrix for each
    implementation-enabled journey. The accepted Product profile is exact; named external
    consent-policy, provider/template, media-safety/lifecycle, activation, and implementation-
    evidence gates remain fail closed for the affected capability.

## 5. Ordered Stories And Dependencies

Story identifiers and acceptance detail are retained from Section 17 of the PR #499 solution
package. The dependency order below is normative; parallel work never permits a consumer to
code against an unstable contract.

| Story | Name | Depends on |
|---|---|---|
| CSA-CEWA-001 | Existing-State Discovery And Impact Analysis | ADR/authority gate; controls all implementation |
| CSA-CEWA-002 | Shared Channel-Neutral Conversation Contract | 001 |
| CSA-CEWA-003 | Canonical History, Sequencing, And Transactional Outbox | 002 |
| CSA-CEWA-004 | Interaction Context Resolver | 002, 003 |
| CSA-CEWA-005 | Layered Conversation Policy And Rendering | 004 |
| CSA-CEWA-006 | Context Observation, Profile, Summary Lineage | 003, 004 |
| CSA-CEWA-007 | Cross-Channel Continuity And Binding | 002, 003, 004 |
| CSA-CEWA-008 | Deterministic Identity Resolution And Assurance | 001, 003 |
| CSA-CEWA-009 | Signed WhatsApp Webhook Ingress | 008 and authorized environment configuration |
| CSA-CEWA-010 | Atomic Inbound Claim, Acknowledgement, Deduplication, And Replay | 003, 009 |
| CSA-CEWA-011 | Inbound Message Normalization | 010 |
| CSA-CEWA-012 | Outbound Queueing And Provider Transport | 002, 003, 008 |
| CSA-CEWA-013 | Service Window, Consent, And Template Eligibility | 010, 012 |
| CSA-CEWA-014 | Delivery Observations And Derived Projection | 010, 012 |
| CSA-CEWA-015 | Media Retrieval, Quarantine, Scan, Retention, And Erasure | 006, 008, 011 |
| CSA-CEWA-016 | WhatsApp Emergency Stop | 008, 010, ADR-031 conformance |
| CSA-CEWA-017 | Privacy-Safe Telemetry, Dead Letters, And Alerts | 001; integrate with applicable stories |
| CSA-CEWA-018 | Demo Provisioning, Activation, And Complete Teardown | 009-017 and separate Demo authority |
| CSA-CEWA-019 | UAT Stable Ingress And Activation | 018 lessons closed and separate UAT authority |
| CSA-CEWA-020 | Production Readiness And Dark Activation Gates | 019, 023, 024, 026 and separate Founder decisions |
| CSA-CEWA-021 | Web Regression And Shared-API Adoption | 002-007 |
| CSA-CEWA-022 | Future Mobile Compatibility Contract | 002 |
| CSA-CEWA-023 | Data Migration, Backup, Restore, And Rollback | 003, 006, 010, 014, 015 |
| CSA-CEWA-024 | End-To-End Acceptance And CE-FIT Qualification | 002-023 |
| CSA-CEWA-025 | Final Docker And Containerized End-To-End Validation | 024 and implementation author review PASS |
| CSA-CEWA-026 | Operational Handoff And Runbooks | 017-025 |
| CSA-CEWA-027 | Founder Handoff And Implementation Authorization Gate | Solution author review; no implementation |

Stories 018-020 describe readiness and evidence only unless their separate environment
authorities are granted. Their presence in the sequence is not authority to activate an
environment.

## 6. Canonical Requirement Index

Every normative implementation obligation is assigned one stable ID. These IDs are the
contract-to-ledger join key; the referenced PR #499 story remains authoritative for detailed
semantics and acceptance conditions.

| Requirement ID | Source | Observable outcome and acceptance oracle |
|---|---|---|
| WC120-R001 | Record Control; §2; CSA-CEWA-001 | Work starts only from the exact reviewed enterprise package, Founder-accepted ADRs, accepted WC-120, digest-valid ledger, and separate current-session authorization. |
| WC120-R002 | §1; CSA-CEWA-001 through CSA-CEWA-027 | BP, PR, AIR, CE, identity, data, Web, and operations retain their stated ownership; no new deployable, history/profile owner, client authority, or cross-owner write appears. |
| WC120-R003 | Solution §5; CSA-CEWA-002 | The shared candidate API preserves one channel-neutral conversation contract and its documented protocol, identity, authorization, limits, errors, retries, telemetry, and failure behavior. |
| WC120-R004 | Solution §6; CSA-CEWA-003 | Canonical message order, transaction boundaries, idempotency domains, and outbox behavior remain durable and prove no duplicate or reordered logical effect. |
| WC120-R005 | Solution §§8-9; CSA-CEWA-004/005 | Interaction context is server-resolved and versioned; policy layers and rendering remain bounded, with no client-supplied prompt or policy authority. |
| WC120-R006 | Solution §6.3; CSA-CEWA-006 | Context observations, profiles, summaries, and lineage preserve source/version, privacy, retention, and correction semantics. |
| WC120-R007 | Solution §4; CSA-CEWA-007 | Web-to-WhatsApp-to-Web continuity preserves relationship/conversation/message identity and sequence; denial, expiry, replay, or revert cannot grant authority. |
| WC120-R008 | ADR-023; §2.4; PR #498 §§12.7/14.2; Solution §7; CSA-CEWA-008 | Identity binds environment, app/WABA, recipient, protected participant proof, membership, relationship, reassignment/revocation, and accepted Tier 1-4 assurance. Phone possession never attaches an existing relationship; denial is non-enumerating and creates zero protected mutation or disclosure. |
| WC120-R009 | §2.4; PR #498 §12.1; Solution §10.1; CSA-CEWA-009 | WhatsApp webhook declares `application/json`; bounded exact raw bytes are authenticated before decompression or transformation, with constant-time signature/token comparison, inclusive five-minute new-event freshness, and exact host/app/recipient/environment binding. |
| WC120-R010 | §2.4; PR #498 §12.1; Solution §§10.1, 13; CSA-CEWA-010 | Compound event claim is atomic: same identity/digest returns the durable result, divergent reuse conflicts with zero additional mutation, and an authentic already-claimed delayed retry is not rejected only because its provider timestamp aged. |
| WC120-R011 | Solution §§5, 10; CSA-CEWA-011 | Provider events are normalized into the accepted domain contract without trusting provider-controlled tenant, authority, or policy fields. |
| WC120-R012 | Solution §10.2; CSA-CEWA-012 | Outbound work is queued and dispatched under separate idempotency and provider boundaries; duplicate, timeout, crash, and unknown outcomes reconcile safely. |
| WC120-R013 | Solution §§10.2, 10.3; CSA-CEWA-013 | Consent, service-window, and template eligibility is checked against current state; ineligible sends fail closed without dispatch. |
| WC120-R014 | Solution §10; CSA-CEWA-014 | Delivery observations are immutable and project independent delivery dimensions; callbacks may not overwrite unrelated message state. |
| WC120-R015 | §2.4; PR #498 §§12.5/14.2; Solution §§10.3, 12; CSA-CEWA-015 | Media stays quarantined until bounded type/signature/resource validation and an isolated clean scan verdict; active/archive/polyglot/parser-capable, expanded, malicious, expired, unknown, error, or timeout outcomes fail safely under approved lifecycle boundaries. |
| WC120-R016 | §2.4; PR #498 §12.8; Solution §§12-13; CSA-CEWA-016 | After signature/binding verification, typed Stop precedes context/model/queue/billing/outbound work, latches through dependency failure, and prevents retries, restarts, reconnects, simultaneous channels, late results, WhatsApp release, or ordinary operator action from regaining authority. |
| WC120-R017 | §2.4; PR #498 §14.3; Solution §14; CSA-CEWA-017 | Telemetry, request capture, framework errors, baggage, dead letters, and scanner diagnostics expose only approved bounded reason/reference metadata; prohibited identity, header/signature, secret, payload, prompt, transcript, message/media metadata, template variable, context, and customer-content leakage is zero. |
| WC120-R018 | Solution §§11, 15-16; CSA-CEWA-018 | Demo provisioning is isolated, default-off, auditable, and completely torn down; Demo activity cannot affect UAT or Production. |
| WC120-R019 | Solution §§11, 15; CSA-CEWA-019 | UAT readiness uses its stable ingress and exact isolated configuration; UAT activation remains separately authorized. |
| WC120-R020 | Solution §15; CSA-CEWA-020 | Production readiness is evidence-only and dark; no Production mutation, traffic, or activation occurs under WC-120. |
| WC120-R021 | Solution §4; CSA-CEWA-021 | Web adopts the shared generated-client contract while preserving existing behavior and rejecting invalid or stale responses safely. |
| WC120-R022 | Solution §4; CSA-CEWA-022 | Future Mobile compatibility is represented by the shared API contract without server semantic changes or channel-specific authority. |
| WC120-R023 | §2.3; Solution §§6, 13; CSA-CEWA-023 | Expand/migrate/contract, migration watermark, backup, restore, rollback, and recovery invariants are tested before contraction; Data proposes Demo 24h/8h, UAT 4h/4h, and Production 15m/2h RPO/RTO targets, with maximum data loss equal to RPO, subject to Founder acceptance and exact-candidate fault/checksum/no-egress evidence. |
| WC120-R024 | Solution §§19-20; CSA-CEWA-024; WC-120-fitness-evidence-matrix.yaml | CE-FIT-01 through CE-FIT-16 map bidirectionally to stories, source oracles, exact Test Champion-selected test selectors, exact-candidate manifest, and evidence. |
| WC120-R025 | Solution §19.3; CSA-CEWA-025 | Final Docker/image/end-to-end qualification binds to an immutable candidate manifest covering source, image, API/solution, schema, migration, configuration, targeted tests, recovery, CE-FIT, and qualification digests. |
| WC120-R026 | Solution §§14-16, 22; CSA-CEWA-026 | Operational procedures cover alerting, dead letters, Stop, environment setup/teardown, recovery, rollback, privacy, and escalation; rehearsals produce retained evidence. |
| WC120-R027 | Solution §23; CSA-CEWA-027 | Founder receives the exact candidate, evidence, risks, rollback, and requested decisions; implementation, deployment, activation, PR approval, and merge remain distinct authorities. |
| WC120-R028 | PR #499 review `R-4248037029`; Solution §§11-12 | Complete telephone identities are absent from current files, fixtures, logs, evidence, and PR text; any shared-history cleanup follows a separate approved plan. |
| WC120-R029 | PR #499 review `R-4248037076`; enterprise §448 | A durable read-position mutation or compatible successor is present and advances participant state; an event-stream cursor alone does not pass. |
| WC120-R030 | PR #499 review `R-4248037125`; Solution §8 | Registered command descriptors and accepted typed payload references are discoverable from interaction context or a typed catalog operation. |
| WC120-R031 | PR #499 review `R-4248037174`; Solution §§4.1, 17 | Handoff revert is an idempotent operation preserving the source binding through retry, uncertainty, expiry, and denial. |
| WC120-R032 | PR #499 review `R-4248037216`; Solution §§5, 9 | Contribution discriminator variants require exactly one corresponding non-null payload and reject missing, mismatched, or simultaneous variants. |
| WC120-R033 | PR #499 review `R-4248037259`; Solution §5 | Command types and parameters form a closed typed union of registered command schemas; arbitrary keys and values are rejected by contract validation. |
| WC120-R034 | PR #499 package test evidence; repaired candidate OpenAPI | OpenAPI validation proves 16 paths, 17 operations, 28 local schemas, 156 resolved local references, and the pinned external employment-command schema reference, with generated-client and producer/consumer fixtures passing. |
| WC120-R035 | Solution §§3, 18-19; all stories; WC-120-fitness-evidence-matrix.yaml | Each story and CE-FIT item has exact repository-native commands/test selectors, predicates, candidate binding, evidence references, and failure/rollback result frozen before implementation starts; the generic ledger validator alone is insufficient. |
| WC120-R036 | PR #498 §§4, 22; WC-114; WC-115-R005/R006 | WhatsApp remains an additive transport/session adapter over the existing BP Conversation Core and employment workspace; no second timeline, transcript, relationship, API owner, or authority is introduced. |
| WC120-R037 | Existing Core API; WC-114 BP API; PR #499 review R-4248037076/7125/7174 | Candidate operations are crosswalked to canonical read position, command discovery, employment operations, and handoff/revert contracts; only compatible additive operations remain. |
| WC120-R038 | §2.4; ADR-023; accepted profile blob `9c7ccecd64791010f1ba15b69d9b8a128d466d66`; WC-115 R102-R108; PR #498 §§12.7/13.6 | Employment calls use the accepted caller/audience/purpose/age/replay and assurance profiles; WhatsApp workloads use separate exact environment identities and adapter audience. Bounded rotation overlap, emergency revocation, no credential fallback, non-restoration on rollback, closed denial, no downstream owner call, and zero authority/data mutation are mandatory. |
| WC120-R039 | §2.3; WC-115 data profile and R077-R084; PR #498 §15 and R-147 | Section 2.3 fixes exact Data-owned ownership, sequence/transaction, inbox/outbox lease/retry/poison, digest/idempotency horizon, forced-RLS, lineage, lifecycle, recovery-target, and migration-window values and oracles; only named Legal/Founder/provider acceptances and the owner-contract crosswalk remain external gates. |
| WC120-R040 | §3.1.1; WC-115 AIR profile and R095-R101; PR #498 §§8, 14, 16, 21 | AIR receives only minimized, server-resolved, source-versioned context and structurally separated untrusted content; accepted digest/catalogue/provenance/result/transient-content controls apply; researched, inferred, confirmed, unavailable, pending, and unknown states remain distinct; prompt injection cannot alter policy or authority; no provider choice or synthetic success is delegated to the channel. |
| WC120-R041 | PR #498 §§13, 17-21, 23-24; Platform Architect contribution | Ingress, DNS/TLS, environment isolation, observability, recovery, teardown, and measurable WhatsApp SLOs have named owners and accepted targets; no infrastructure mutation is implied. |
| WC120-R042 | PR #498 §§17, 23-24, 26; WC-115 §7.4; §3.4; WC-120-product-acceptance-matrix.yaml | Product-owned journeys use the accepted `en-IN` locale, bounded readability/text-audio parity, exact consent/service-window/template/media/degraded copy and actions, voice correction/send consent, WCAG 2.2 AA presentation, and always-reachable Stop; named external gates remain fail closed. |
| WC120-R043 | PR #498 §27; R-146; R-147; §2.2 | Historical review findings, author repairs, and current office dispositions are represented separately; no author repair is labelled reviewer approval. |
| WC120-R044 | PR #498 §17; CE-FIT-01..16; Test Champion disposition | The fitness matrix has exactly one row per CE-FIT item, maps each to one or more stories, positive/boundary oracles, exact test selectors, immutable candidate binding, and a planned evidence location. |

## 7. Validation And Evidence

### 7.1 PR #499 Architecture-Package Evidence

PR #499 recorded the following plan-validation result. WC-120 does not reuse its host-Python
invocation as qualification evidence: C-080 requires the Docker-only rerun shown here. These
results validate only the architecture candidate and are not implementation evidence:

```text
Required WC-120 rerun command (result not yet claimed):
docker compose --profile test-python run --rm test-runner-python pytest -q tests/test_openapi_slice.py tests/validation_control/test_spec_lint_scope.py
Historical PR #499 reported results (non-qualifying for WC-120):
Unit tests: PASS (7/7)
Integration: N/A - architecture-only package
CE-FIT: PASS - CE-FIT-01 through CE-FIT-16 assigned to stories, components, tests, and evidence
OpenAPI: HISTORICAL PR #499 RESULT ONLY - YAML parsed; 14 paths; 23 schemas; 133/133 local
references resolved. It does not qualify repaired candidate.2, which requires the Docker-only
R034 selector and generated-client/producer-consumer evidence before implementation.
Package structure: PASS - 27 stories x 23 mandatory fields; 24 runbook steps
Spec lint: PASS - scoped repository lint selected existing BP/PR specs plus the candidate
Diff check: PASS - git diff --check
YAML lint: PASS - relaxed profile (line-length warnings only)
```

### 7.2 WC-120 Integrated Specification Validation

The restored validators are byte-identical to merged commit
`846dc2098844b97ccd266048c9557a0886712237`. On the integrated candidate:

```text
docker compose --profile test-python run --rm test-runner-python python scripts/validate_requirement_ledger.py --ledger work-contracts/WC-120-requirements.yaml --contract work-contracts/WC-120-conversation-engine-whatsapp-implementation.md
PASS - Requirement ledger validation passed: 44 requirements

docker compose --profile test-python run --rm test-runner-python pytest -q tests/test_openapi_slice.py tests/validation_control/test_spec_lint_scope.py
PASS - 7 passed
```

These are specification/contract validation results. They do not represent any implementation,
story, generated-client, CE-FIT, migration, recovery, deployment, or activation test as passing.

### 7.3 Required Implementation Test Portfolio

For every story, the implementer records and runs the smallest exact repository-native
commands for the changed surfaces. The impact analysis and strategic plan must pin those
commands before implementation starts; they must not be guessed after code is written.

- .NET: filtered Business Platform / Constitutional Engine unit and integration tests.
- Python: exact Professional Runtime / AI Runtime test modules or node IDs.
- Web: exact Jest/Playwright projects or test names, plus type and lint checks.
- Contracts: OpenAPI lint/slice, generated-client build, and producer/consumer fixtures.
- Data: migration up/repeat/rollback compatibility, RLS, backfill, restore, and invariant queries.
- Security/privacy: signature verification, identity/assurance, secret authority, media isolation,
  Emergency Stop, environment isolation, and telemetry-leakage tests.
- Static/traceability: formatter, linter, type checker, dependency/spec trace gates, and the
  validated WC-120 requirement ledger.

At minimum, explicit predicates must prove: JSON webhook media type with raw-byte signature
verification; durable read-position advancement; authorized interaction-context command
discovery; idempotent handoff revert; exactly one correctly typed contribution payload;
closed typed command payloads; and absence of complete telephone identities from current
repository files, fixtures, logs, evidence, and PR text. The repository-history remediation
for already committed sensitive inputs requires a separately approved plan.

The behavioral portfolio in Section 19.2 of the solution package is mandatory: canonical
continuity; identity and authority denial with zero mutation; ingress signature, freshness,
atomic claim and replay; outbound idempotency and delivery projections; media/privacy;
Emergency Stop and recovery; and environment isolation. All CE-FIT-01 through CE-FIT-16
must map to direct acceptance oracles and evidence in
`work-contracts/WC-120-fitness-evidence-matrix.yaml`. INST-015 has bound every row to an exact
planned Docker-only command, path, and test node. Pre-implementation absence of those named
test artifacts is expected and does not block specification readiness; changing or omitting a
planned selector does. Before its story completes, the exact node must exist, directly prove
the complete positive and boundary oracle, and pass on the bound candidate.

The Test Champion control profile is normative:

- all test execution uses the repository Compose runners; host Python and virtual environments
  are prohibited;
- all `16/16` direct CE-FIT rows pass with `0` skipped, xfailed, quarantined, or flaky-retry
  allowances;
- changed services meet at least `90%` line and `80%` branch coverage without lowering an
  existing stronger threshold;
- CE-FIT-08 executes `100` coordinated cross-channel race trials on the exact candidate;
- accessibility selectors execute all five configured Playwright projects, with `0` serious or
  critical axe violations, `100%` keyboard reachability and non-colour state meaning, `200%`
  zoom, `360` CSS-pixel compact reflow, deterministic focus, accepted accessible names/roles,
  and always-reachable Stop;
- each row retains its native test report plus `selector-result.json`, runner-image digest, and
  candidate-manifest digest in its assigned evidence directory; and
- a broad suite, supporting regression, or final Docker run cannot substitute for a direct row.

The existing `scripts/validate_requirement_ledger.py` checks ledger shape, IDs, required
fields, contract digest, and completion evidence; it does not prove CE-FIT completeness,
test executability, or candidate binding. A passing ledger-validator result is not evidence
that those obligations pass. The Test Champion must explicitly disposition the matrix and
its candidate/evidence bindings. Any automation enhancement to the validator is a separate
code change requiring its own authority; it is not implied by WC-120.

Customer-visible acceptance is separately captured in
`work-contracts/WC-120-product-acceptance-matrix.yaml`. Product owns approved copy, supported
locale/readability choices, consent journeys, and user-visible outcomes; BP enforces transport
eligibility, while Security/Data own their control decisions. The Product values are accepted in
§3.4. Named Legal/Founder, Security, Data, provider, Platform, and implementation-evidence
dependencies remain fail-closed gates for the affected capability and are not implementer defaults.

Run final Docker, image scans, and full containerized end-to-end validation only after all
stories, targeted tests, static checks, migration/restore/rollback checks, and implementation
author review pass. A broad suite does not replace per-story targeted evidence.

## 8. Rollback And Reversibility

The failure and rollback behavior in Sections 13 and 18 of the PR #499 solution package is
normative. Before implementation, the strategic plan must bind it to exact owner paths,
feature gates, schema versions, migration watermarks, backup/restore points, and tested
commands.

- Use additive expand -> migrate -> contract evolution; retain compatible readers and
  source behavior until the new path proves equivalence.
- Keep new behavior disabled or shadowed until its exact acceptance predicates pass.
- On failure, stop the affected path, preserve evidence, and return to the last compatible
  application behavior while retaining safe additive schema. Do not run destructive
  contraction as an ad hoc rollback.
- Story 023 must prove backup, restore, migration compatibility, and recovery consistency;
  record the environment, injected fault, exact backup/restore/rollback commands, schema and
  migration watermark, accepted numeric RPO/RTO and data-loss bounds, invariant/checksum
  oracle, provider-egress denial, and retained evidence for each environment.
- Stop and reconcile external provider operations independently. Application rollback does
  not reverse a sent message, provider registration, DNS mutation, or customer-visible effect.
- Demo teardown, UAT recovery, and Production-dark evidence are separate acceptance
  activities; none grants authority to mutate or activate that environment.

If rollback cannot preserve existing behavior or integrity, stop and request Founder
direction before proceeding.

## 9. Stops

Stop the affected story and report a blocker when:

- This exact Work Contract or its requirement ledger has not received the required Founder
  acceptance/validation, or current-session implementation authorization is absent.
- A required owning contract, owner, interface, security property, or accepted decision
  cannot be verified; ADR-023/ADR-031 assumptions fail; or the corrected package conflicts
  with the accepted enterprise architecture.
- Any of the seven PR #499 review findings remains unresolved or lacks its explicit test
  predicate.
- The crosswalk to Conversation Core or WC-114/WC-115 is missing, duplicate, incompatible,
  or would weaken an accepted owner contract.
- A required Data, Security, Platform, AI, Product, or Test Champion contribution is absent,
  ambiguous, or conflicts with an accepted profile; R-146/R-147 are inputs, not substitutes
  for downstream contribution or reviewer approval.
- A complete telephone identity, credential, token, key, provider payload, or customer
  content is found in a location prohibited by this contract.
- A migration is destructive or not demonstrably reversible; an acceptance oracle cannot
  be proved; the required owner or path does not exist; or preserving current behavior
  requires inventing architecture or policy.
- A provider, environment, DNS, deployment, Production, cost, retention, legal-hold, media,
  RPO/RTO, or activation decision lacks its own named authority.
- A test, security, privacy, CE-FIT, traceability, rollback, or exact-candidate gate fails.
- The CE-FIT matrix is incomplete, lacks an exact Test Champion-selected planned Docker
  command/path/node, is stale for the candidate, or lacks direct evidence binding. Before a
  story completes, its planned node being absent, skipped, indirect, or non-passing is also a stop;
  pre-implementation absence of the named implementation test artifact is expected.
- The Product acceptance matrix has unaccepted consent, locale/media, copy, accessibility,
  service-window/template, voice-correction, or degraded-state decisions for the affected
  journey.
- The candidate manifest, recovery limits, or provider-egress denial evidence is missing or
  does not match the tested source/configuration/image.

Do not resolve a stop by reducing a threshold, weakening a contract, changing a test, or
assuming approval.

## 10. Handoff Evidence

The implementation handoff package delivered to the Founder must include:

1. This accepted WC-120 revision and its validated `WC-120-requirements.yaml` ledger bound
   to the exact Work Contract SHA-256.
2. The completed Core/WC-114/WC-115 compatibility crosswalk and corrected, versioned
   solution package and API digest, closure evidence for all seven
   PR #499 review threads, and protected-configuration evidence without secret values.
3. Scoped dispositions and repair evidence for each required office, with R-146/R-147
   accurately identified as prior one-pass enterprise reviews and author-remediation
   records.
4. Platform IT Expert impact analysis and dependency-ordered strategic plan with exact
   paths, commands, owners, feature gates, compatibility window, and rollback.
5. Per-story targeted test evidence, producer/consumer contract evidence, migration /
   backup / restore / rollback evidence, and bidirectional CE-FIT-01..16 traceability.
6. The completed Product acceptance matrix, Test Champion-dispositioned CE-FIT matrix,
   immutable candidate manifest, and exact-candidate evidence references.
7. Privacy, signature, assurance, idempotency, replay, Emergency Stop, environment
   isolation, sensitive-data non-disclosure, and telemetry-leakage evidence.
8. Exact-candidate Docker/container qualification, image evidence, rehearsed runbooks,
   authorized teardown/recovery proof, and implementation author review bound to the
   exact 40-character commit.
9. A concise residual-risk and open-decision list, including each ungranted environment
   authority and any separate Founder decision required.

The handoff is complete only as an evidence package for Founder review. It does not authorize
deployment, provider mutation, activation, traffic, Production change, PR approval, or merge.

## 11. Author Review

The author must review this complete Work Contract against PR #498's merged architecture and
remediation record, PR #499's candidate package and seven review threads, the exact current
Conversation Core/WC-114/WC-115 inputs, Founder ADR approval, required specialist profiles,
and the Chief Solution Architect's handoff standard. Review coverage includes precedence,
additive scope, authority, cross-contract compatibility, office-review provenance, requirements,
sequencing, test oracles, sensitive-data handling, rollback, stops, and handoff evidence.

### 11.1 Findings And Repairs

| Finding | Repair | Result |
|---|---|---|
| PR #499 candidate could be read as superseding WC-114/WC-115 or creating parallel conversation authority. | Set explicit source precedence and require a path/operation/schema compatibility crosswalk against the existing Conversation Core, BP API, WC-114/WC-115, and accepted profile before implementation planning. | RESOLVED |
| Stale PR #499 status and ADR labels obscured the Founder decision and the remaining implementation gate. | Recorded the Work Contract status replacement and Founder approval of ADR-051/052/053; explicitly retained specification, office-contribution, exact-contract acceptance, and session-authorization gates. | RESOLVED |
| PR #498 R-146/R-147 could be misrepresented as downstream office approval. | Pinned their original `CHANGES REQUIRED` review records and PR #498 §27 author remediation; stated that neither is a post-repair reviewer approval or WC-120 review. | RESOLVED |
| WC-114/WC-115 specialist profiles were not explicitly carried into identity, data, AIR, or platform requirements. | Added WC120-R038 through WC120-R042, pinned the existing profile, and made specialist contributions a hard pre-implementation gate. | RESOLVED |
| The ledger's required-evidence details did not meet this contract's own Definition of Done. | Added planned evidence destinations and failure/rollback behavior to every ledger row through the shared defaults, and added traceable requirements for cross-contract reuse and office dispositions. | RESOLVED |

**Contract authoring result:** superseded by
`reviews/WC-120-solution-architect-integration-disposition.md`, which binds the complete integrated
author review and exact artifact digests.
**Strategic-plan readiness:** `READY_FOR_STRATEGIC_PLAN` - compatibility, seven findings, all six
specialist dispositions, Product/CE-FIT matrices, and exact Docker-only specification validation
are complete.
**Implementation readiness:** no implementation is authorized. Founder acceptance of the exact
integrated package and separate explicit current-session implementation authorization remain
mandatory. Protected Legal/Founder/provider/platform decisions and implementation-phase evidence
remain fail-closed at their affected implementation, promotion, deployment, or activation gates.
