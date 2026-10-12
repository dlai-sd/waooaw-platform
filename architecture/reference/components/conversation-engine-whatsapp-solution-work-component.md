# Conversation Engine And WhatsApp Solution Work Component

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Status | DRAFT - IMPLEMENTATION HANDOFF BLOCKED |
| Version | `1.0.0-candidate.1` |
| Controlling enterprise package | `conversation-engine-whatsapp-enterprise-architecture.md` |
| Reviewed enterprise head | `65add4540698116b00be1ec72e6000333d05eac9` |
| Merged PR | PR #498, merge commit `4a4420af6ee132623d6b87eb3863d700e56c9b86` |
| Decision package | ADR-052 and ADR-053, both still `Proposed - Founder review required` |
| Implementing office | Platform IT Expert (INST-010), only under a separate Work Contract and explicit current-session implementation authority |
| Authority boundary | Solution architecture and implementation planning only. No implementation, `src/` change, Meta/Azure/DNS/provider mutation, number purchase, deployment, traffic, activation, PR approval, or merge. |

**Blocking rule:** PR #498 is merged, but merge did not change ADR-052 or ADR-053 to Accepted. This
candidate may be reviewed, corrected, and accepted as a solution package, but no implementation
story may start until the Founder accepts the applicable ADRs and separately authorizes an
implementation Work Contract. ADR-052 also depends on prior or simultaneous acceptance of ADR-051.

## 1. Executive Implementation Overview

This package decomposes the merged enterprise package, without treating its proposed decisions as
accepted, into one reusable channel-neutral conversation capability and one environment-configured
WhatsApp adapter:

1. Business Platform remains the ordinary public facade, canonical conversation owner, context
   projection owner, and provider adapter boundary.
2. Professional Runtime owns professional execution, ordering, cancellation, reconciliation, and
   Emergency Stop.
3. AI Runtime owns bounded context assembly, research, analysis, and provider-neutral reasoning.
4. Constitutional Engine owns authority validation, constitutional decisions, and evidence.
5. Web, WhatsApp, and future Mobile share the same canonical conversation semantics. Channel state is
   delivery/session state only.
6. The WhatsApp adapter is reused unchanged across Demo, UAT, and Production through isolated
   configuration and authority. It is not a public shared API for Web or Mobile.
7. No new deployable Conversation Engine service is created. Evidence for a new deployable would
   require a separate accepted C-095 architecture decision.

The implementation sequence begins with mandatory discovery and impact analysis, evolves persistent
contracts through expand -> migrate -> contract, proves each story with targeted tests, completes
author review, and runs the repository-prescribed Docker/end-to-end qualification once at the end.

## 2. Controlling Inputs And Precedence

Apply inputs in this order. Stop rather than reconcile a conflict in implementation:

1. Founder decisions and accepted constitutional/ADR authority;
2. accepted ADR-051, when accepted, plus accepted ADR-052 and ADR-053;
3. the PR #498 enterprise package at reviewed head `65add454...`;
4. `domain-model.md`, `containers.md`, and `capability-to-container-map.md` from that head;
5. remediated requirements from R-146 and R-147 as incorporated into the enterprise package;
6. this solution Work Component and its candidate OpenAPI;
7. the implementation impact analysis and strategic plan, provided neither changes architecture.

An implementation convenience, existing code shape, provider behavior, or screen requirement cannot
override this order.

## 3. Mandatory Platform IT Expert Pre-Implementation Gate

### 3.1 Impact Analysis

Before changing implementation files, the Platform IT Expert must create a written impact-analysis
record that:

1. confirms it read this complete Work Component and every controlling input in Section 2;
2. traces current behavior through Business Platform, Professional Runtime, AI Runtime,
   Constitutional Engine, Phone Identity, WBE, Web, data, deployment, and tests;
3. inventories existing conversation, identity, webhook, outbox/inbox, delivery, media, context,
   policy, Stop, observability, backup, and recovery mechanisms to reuse or extend;
4. names every affected API, generated client, schema, migration, event, worker, UI, configuration,
   deployment workflow, test suite, and runbook;
5. records compatibility risks and behavior that must remain unchanged;
6. maps dependencies and ownership boundaries;
7. identifies conflicts, missing decisions, provider dependencies, and unsafe migrations; and
8. contains a signed conclusion of `READY_FOR_STRATEGIC_PLAN` or `BLOCKED`.

The record must cite file paths and current behavior without modifying those files. A missing
surface is not permission to invent one.

### 3.2 Strategic Implementation Plan

Only after a `READY_FOR_STRATEGIC_PLAN` impact result, the Platform IT Expert must produce a plan that:

- groups changes by the buckets in Section 17;
- separates shared conversation work from WhatsApp-specific adapter work;
- identifies reused contracts/utilities and rejects environment forks;
- sequences contract/schema evolution through expand -> migrate -> contract;
- marks dependency-critical and parallelizable stories;
- defines feature flags, compatibility window, migration watermark, rollback, and Stop conditions;
- records the smallest exact targeted test command for each story;
- schedules ordinary unit/contract/integration/static/migration tests after each story; and
- schedules Docker/container/end-to-end qualification only after all stories and author review.

The implementation gate fails if the plan creates a new deployable, parallel history, channel-owned
profile, free-form client prompt, direct client authority, shared environment identity, or a test
strategy that postpones non-Docker targeted validation.

### 3.3 Mandatory Stops

Stop and raise a blocker for an unaccepted ADR, missing implementation authority, architecture
conflict, unsafe migration, unavailable provider prerequisite, undefined owner, required new
technology/deployable, inability to preserve existing behavior, unresolved Production decision,
or acceptance criterion that cannot be proved without weakening the architecture.

## 4. Target Solution Component Design

```text
Web generated client --------\
Future Mobile generated client -> BP Shared Conversation API -> canonical BP transaction/outbox
Meta signed webhook -> BP WhatsApp Adapter / Phone Identity --/
                                      |
                                      +-> PR professional execution -> AIR context/reasoning
                                      +-> CE authority/evidence
                                      +-> WBE commercial decision
                                      +-> BP channel delivery projection -> Meta outbound API
```

### 4.1 Shared Versus Channel-Specific Responsibility

| Concern | Shared Conversation API | WhatsApp Channel Adapter | Channel clients |
|---|---|---|---|
| Canonical history and sequence | BP owns | Contributes normalized inbound messages | Read/render only |
| Interaction Context | BP resolves | Supplies registered channel capability and opaque references | May send registered key only |
| Conversation Policy | BP selects; AIR applies exact references | Applies rendering constraints only | No authoritative prompt/policy |
| Professional execution | PR owns | Never executes or reasons | Never calls PR/AIR directly |
| Authority/evidence | CE/WBE/domain owners | Carries typed outcomes only | Cannot grant authority |
| Identity | Web/mobile via Keycloak; WhatsApp via signed provider binding | Resolves provider/app/recipient/participant/environment tuple | Cannot supply tenant |
| Delivery | Channel-neutral state dimensions | Meta dispatch/status/media | Presentation/session only |
| Environment isolation | Environment is mandatory data/config binding | Same code, isolated config/identity/state | No cross-environment fallback |
| Public reuse | Web/Mobile use generated BP contract | Not used directly by Web/Mobile | Generated contract only |

### 4.2 Build-Versus-Reuse Decisions

| Capability | Decision |
|---|---|
| Conversation facade/history/idempotency/outbox | Extend existing BP Conversation Core |
| Professional execution and Stop | Extend existing PR and ADR-031 paths |
| Context/reasoning/transcription | Extend AIR and existing WC-062 voice boundary |
| Phone identity | Extend ADR-023 Phone Identity through BP adapter |
| Public API | Additive versioned BP contract; generated clients |
| WhatsApp transport | BP logical adapter over Meta Cloud API; no parallel engine |
| Durable workflows/reconciliation | Reuse existing Temporal/outbox infrastructure found during discovery |
| Secrets | Reuse managed identity + environment Key Vault under ADR-014/046 |
| Media | Reuse erasable payload boundary and isolated scanner pattern |
| Telemetry | Reuse OTel/Azure Monitor with a prohibited-data scanner |

## 5. Candidate API Contract

The machine-readable candidate is
`architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml`.
It is additive and does not replace `business-platform.openapi.yaml` until implementation authority,
impact analysis, compatibility proof, and ADR acceptance exist.

### 5.1 Public Contract Families

| Operation family | Required semantics |
|---|---|
| Read timeline/context | Canonical ordered messages, exact context/policy/source versions, independent state dimensions |
| Submit contribution | Text or reviewed voice; actor/relationship/idempotency/digest/context binding |
| Submit command | Closed typed command with expected source version and required assurance |
| Reconcile | Return original durable receipt/outcome; never blind-retry ambiguous commit |
| Cursor/events | Monotonic canonical cursor; SSE/polling equivalent semantics |
| Cancellation | Request cancellation; never delete history |
| Handoff | Prepare -> authenticate target -> activate or revert; source remains valid on failure |
| Context/profile | List registered contexts; inspect/correct material with append-only lineage |
| State inspection | Delivery, execution, decision, and evidence reported independently |
| Export/erasure | Authorized lifecycle request with hold/external-provider status |

Every mutation requires `Idempotency-Key`, actor from trusted identity, relationship path binding,
canonical payload digest, correlation ID, exact context version, and expected source version when
the subject is mutable. Tenant, authority, system prompt, policy bytes, model selection, provider
credential, or raw phone number are never writable fields.

### 5.2 Error Contract

Use `application/problem+json` with stable safe codes:

`not_accessible`, `assurance_required`, `source_version_conflict`, `context_stale`,
`context_ambiguous`, `idempotency_conflict`, `stop_active`, `policy_unavailable`,
`provider_unavailable`, `template_ineligible`, `media_quarantined`, and
`constitutional_governance_unavailable`.

Errors contain correlation, retry classification, and safe remediation. They never enumerate
tenants/relationships, reflect provider input, or expose phone proofs, provider IDs, signatures,
tokens, payloads, prompts, internal policy, or stack details.

### 5.3 Event Contracts

All events use a closed schema with `eventId`, `eventVersion`, `occurredAt`, `environment`,
`tenantId`, `relationshipId`, `conversationId`, `correlationId`, `causationId`, and opaque payload
references where applicable.

| Event | Producer -> consumer | Required payload |
|---|---|---|
| `ConversationContributionAcceptedV1` | BP -> PR/projections | message ID/sequence, actor kind, contribution kind, context/policy refs, source versions, payload digest |
| `ConversationExecutionRequestedV1` | BP -> PR | execution ID, canonical message, Decision Space/context/policy versions, assurance, typed objective |
| `ConversationExecutionObservedV1` | PR -> BP | execution ID, state, typed result/error, context/policy refs; no provider delivery implication |
| `ContextSourcesChangedV1` | authoritative owner -> BP | subject, old/new version, affected context/profile/summary references |
| `ContextArtifactInvalidatedV1` | BP -> rebuild worker | artifact ID, reason, source watermark, required action |
| `OutboundRepresentationQueuedV1` | BP -> WhatsApp adapter | logical message, attempt, environment binding, eligibility evidence refs, digest |
| `ProviderDeliveryObservedV1` | WhatsApp adapter -> BP | attempt, provider event reference, normalized status, provider/received times |
| `EmergencyStopLatchedV1` | PR/BP -> BP/CE sync | relationship, latch ID, actor proof ref, source channel, CE sync state |

Schema evolution is additive within a major version. Consumers ignore documented optional additions,
reject unknown enum values where safety depends on closed meaning, and dead-letter incompatible
majors without acknowledging business success.

## 6. Data Model And Migration Specification

### 6.1 Ownership And Transaction Boundaries

| Aggregate/record | Owner and binding | Atomicity or handoff |
|---|---|---|
| Canonical conversation/message | BP; environment + tenant + relationship + conversation | Idempotency reservation + protected-intent conflict check + sequence + append + outbox in one transaction |
| Interaction context/policy ref | BP; exact source versions | Immutable resolved version; opaque ref to PR/AIR |
| Observation/profile/summary | BP; relationship/subject | Observation append + projection update; summary metadata after payload write |
| Channel binding | BP/Identity; environment + participant proof | Activation only after current authentication/evidence |
| Inbound provider event | BP transport inbox; environment + app/WABA + recipient number + provider event | Claim + digest + durable typed result + outbox in one consistency boundary |
| Canonical command idempotency | BP relationship boundary | Same transaction as protected mutation or typed rejection |
| Outbound logical message/attempt | BP conversation/transport | Logical message outbox; each retry is a new attempt |
| Provider status observation | BP append-only transport | Idempotent append; derived projection recomputed |
| Media/transcript/correction | Erasable payload/voice boundary | Opaque payload refs; append corrections; only accepted version enters conversation |
| Stop latch/evidence sync | PR operational state + CE evidence | Local halt/latch durable during CE outage; idempotent later evidence sync |

Every tenant-scoped row, uniqueness key, foreign-key path, cursor, idempotency record, payload
reference, worker lease, and provider correlation includes or resolves through trusted environment,
tenant, and relationship context. PostgreSQL uses tenant-consistent composite references, transaction
local context reset, `ENABLE` + `FORCE RLS`, and non-owner `NOBYPASSRLS` runtime roles.

### 6.2 Canonical Ordering And Idempotency Domains

- Allocate one strictly increasing sequence per canonical conversation.
- Enforce unique `(environment, tenant, relationship, conversation, sequence)`.
- Provider timestamp is provenance, not ordering authority; committed BP sequence is authoritative.
- Independent concurrent messages may commit in serialized order.
- One protected pending intent exists per protected subject; exact-intent confirmation can commit
  once across all channels.
- Separate domains:
  - inbound provider event: environment + provider authority + recipient number ID + event ID + digest;
  - canonical command: environment + tenant + relationship + actor + operation + key + digest;
  - outbound attempt: environment + logical message + attempt number + provider binding + digest.
- Same key/same digest replays the original result. Same key/different digest is a conflict with zero
  additional mutation.
- Non-reconstructive tombstones remain through retry, reconciliation, replay, backup/restore, and
  unresolved-attempt horizons even after payload erasure.

### 6.3 Context Observation And Summary Lineage

Observations are append-only and carry subject, type, status, accountable source, source identity and
version, observed/captured/confirmed times, validity, permitted use, predecessor, supersession reason,
and evidence reference. Allowed statuses are `RESEARCHED`, `INFERRED`, `CONFIRMED`, `DISPUTED`,
`STALE`, `SUPERSEDED`, `UNAVAILABLE`, and `ERASED`.

The current profile is a replaceable projection. A summary records exact canonical sequence range or
source set/digests, derivation contract/model/policy versions, production time, sensitivity,
predecessor, invalidation reason, and rebuild state. A summary is never the sole source of a fact.

### 6.4 Delivery Projection

Provider status observations are immutable. A derived attempt projection keeps transport progress
(`QUEUED` -> `SUBMITTED` -> `PROVIDER_ACCEPTED` -> `DELIVERED` -> `READ`), terminal disposition
(`OPEN`, `FAILED`, `EXPIRED`, `CANCELLED`), and reconciliation (`CURRENT`, `UNKNOWN`, `CONFLICTED`)
separate. Late, duplicate, contradictory, and regressive observations remain in history. A later
truthful delivery can supersede an earlier uncertain projection. Retries are distinct attempts under
one logical outbound message. No transport observation changes execution, decision, or evidence.

### 6.5 Expand -> Migrate -> Contract

1. **Expand:** add nullable/new-version records, dual-read compatibility, outbox/inbox, RLS, and
   feature flags without changing current behavior.
2. **Migrate:** idempotently backfill environment/tenant/relationship keys, sequence watermarks,
   context/profile lineage, delivery observations, payload references, and tombstones with provenance.
3. **Cut over:** bind exact schema/data watermark; enable writes only after invariant checks.
4. **Compatibility window:** old readers continue; new-version-only commands remain gated.
5. **Contract:** remove old paths only after rollback expiry and retained-data compatibility proof.

Rollback restores the prior reader/writer contract without destructive down-migration and preserves
new records, canonical messages, accepted decisions, and evidence.

## 7. Identity And Assurance Design

### 7.1 Deterministic WhatsApp Resolution

Resolve from the verified tuple: environment, app/WABA authority, recipient phone-number ID,
provider event ID, and protected participant proof. Outcomes:

| Resolution | Result |
|---|---|
| Exactly one current binding and one accessible active relationship | Continue at the binding's assurance tier |
| Valid first-contact admission | Create only through current admission/opt-in policy; never attach an existing relationship from phone possession |
| Zero, duplicate, ambiguous, inactive, revoked, reassigned, expired, stale | Same non-enumerating unavailable/step-up response; zero relationship mutation |
| Environment/app/WABA/recipient mismatch | Deny and alert; no fallback |

Provider IDs, phone references, message text, and payload hints never independently select tenant or
relationship data.

### 7.2 Assurance Floors

| Tier | Operations | Required proof |
|---|---|---|
| 1 | Information, routine grooming, non-consequential support | Current verified phone binding and active membership; no authority expansion |
| 2 | Exact plan/brief/seasonal or medium commitment | Tier 1 + confirmation bound to intent digest, subject, source version, and expiry |
| 3 | Financial or significant authority-bearing commitment | Fresh stronger-factor step-up bound to one intent; invalidate on completion/change/expiry/Stop/session loss |
| 4 | Contract create/change, Stop release, payment/bank change, deletion, critical operations | Fresh portal authentication + exact authoritative command; never complete in WhatsApp |

Changing channel never upgrades assurance. Number reassignment, revocation, membership/relationship
change, or environment change invalidates derived assurance. Commit always rechecks freshness and
exact intent.

## 8. Interaction Context Resolution

Resolution precedence is:

1. current authenticated actor/environment/tenant/relationship;
2. active Stop and pending protected intent;
3. current Decision Space, relationship, plan, profile, and authority source versions;
4. customer-selected registered subject and server-owned journey state;
5. message intent and channel capabilities;
6. registered client context key and opaque subject reference;
7. default registered context for the current phase.

Unknown keys, unauthorized subjects, version mismatch, ambiguity, or stale material sources produce
zero consequential mutation and either a bounded choice, one clarifying question, or reassessment.
Clients cannot supply free-form context, system instructions, policy, authority, tenant, or model
configuration.

Each assembled segment carries provenance, sensitivity, trust class, source version, and permitted
use. Customer/provider/media/research/retrieval/tool/transcript/history/summary content is untrusted
data and structurally separated from institutional/policy instructions. Every model-proposed tool or
command is independently authorized against current context, Decision Space, source versions, and
assurance.

## 9. Conversation Policy Resolution And Rendering

Compose exact versions in this precedence:

`institutional -> professional persona -> interaction purpose -> customer communication ->
domain vocabulary -> locale/accessibility -> channel rendering`.

Higher layers cannot be weakened by lower layers. Channel rendering may split or shorten but cannot
change recommendation, consent, disclosure, authority, evidence, conclusion, or required action.
Every response declares one primary dialogue act from the enterprise vocabulary.

Material interactions conclude with `understanding`, `analysis`, `recommendation`,
`customer_decision`, `next_action`, `open_items`, and `evidence_state`, or a typed continuation
reason. Research, inference, recommendation, and confirmed fact remain visibly distinct.

## 10. WhatsApp Transport, Template, Status, And Media Design

### 10.1 Signed Ingress And Durable Acknowledgement

- GET echoes challenge only for exact `subscribe`, constant-time environment verify-token match, and
  environment-bound callback host.
- POST accepts only approved `X-Hub-Signature-256` HMAC-SHA256 over bounded exact raw bytes before
  decompression, normalization, parsing, or middleware transformation.
- New events pass the inclusive five-minute freshness boundary against trusted receipt time.
- A delayed retry of an already claimed authentic event replays its durable outcome even when its
  original provider time is now old.
- Provider success is returned only after durable acceptance/outcome or replay of the same durable
  result; otherwise return the approved retryable failure.

### 10.2 Outbound And Eligibility

Only a canonical BP message or typed command outcome creates an outbound representation. Queue-time
and immediate pre-send checks cover current window, opt-in/opt-out, purpose, recipient, relationship,
Stop, environment, exact template/version/locale/schema/category, and approval. Any intervening
revocation creates a typed non-dispatched outcome. No fallback template, channel, environment, or
credential is allowed.

### 10.3 Media Boundary

Server-side retrieval uses short-lived provider authority. Filename, extension, and MIME are
untrusted. Enforce signature sniffing; compressed/expanded size, ratio, page/frame/duration,
CPU/memory/recursion/time limits; deny active/archive/polyglot/parser-capable formats unless approved;
quarantine; scan through isolated identity; immutable verdict lineage; and no interpretation before
clean verdict. Unknown/error/timeout remains quarantined.

Lineage is:

`provider reference -> quarantined payload -> scan verdict -> clean payload -> extraction/transcript
-> customer correction/confirmation -> canonical contribution -> payload-free evidence reference`.

Only the accepted version enters professional context. Erasure removes payload and derivatives,
retains permissible non-reconstructive tombstone/evidence, and reports provider deletion as complete
only when confirmed.

## 11. Environment Configuration And Isolation

| Boundary | Demo | UAT | Production |
|---|---|---|---|
| Founder-provided number input | `9822753575` | `8888912344` | Separate purchase; prefer suffix `926629` |
| Repository-safe display | suffix `3575` | suffix `2344` | `PENDING_FOUNDER_PURCHASE` |
| Meta identity | Dedicated app/WABA/number registration or approved equivalent isolation | Dedicated | Dedicated, dark |
| Provider IDs/secrets | Environment Key Vault only | Environment Key Vault only | Environment Key Vault only |
| Callback | `whatsapp-demo.<approved-domain>` | `whatsapp-uat.<approved-domain>` | `whatsapp.<approved-domain>` |
| Ingress | Stable for Demo lifetime | Stable Azure ingress + DNS/TLS hostname | Stable, separately authorized |
| Data/media/dedup | Dedicated namespaces | Dedicated namespaces | Dedicated namespaces |
| Telemetry/templates | Demo-only | UAT-only | Production-only |
| Deployment authority | Ephemeral authorized apply | Fixed authorized apply | Founder-gated, dark default |
| Backup/recovery | Isolated disposable scope | Isolated durable scope | Isolated durable scope |

The listed telephone values are configuration inputs, not source constants. The operator stores the
complete E.164 value and Meta IDs only in protected environment configuration. Architecture tests
use suffixes or injected fixtures. Stable inbound ingress does not imply stable outbound egress; add
egress only when an authorized dependency requires allow-listing.

Runtime adapter, media scanner, and deployment/configurator use separate environment-bound workload
identities and audiences. Verify token, app secret, outbound authority, media authority, and
deployment authority are distinct. Wrong workload/audience/environment/version, unavailable,
expired, revoked, leaked, or superseded authority fails closed. Rollback never restores a revoked
credential.

## 12. Security, Privacy, Retention, Hold, And Erasure

| Record class | Lifecycle rule |
|---|---|
| Canonical metadata | Preserve permissible metadata; payload follows rights/hold policy |
| Message/context/profile payload | Erase or supersede; append tombstone/lineage; propagate to cache/search/summary/backups |
| Observations/profile | Append successor/stale/dispute/erased state; rebuild projection |
| Summaries/embeddings/cache | Inherit highest source sensitivity/hold; never outlive source |
| Channel binding/assurance | Revoke operational use immediately; retain minimized evidence only |
| Inbox/dedup/tombstone | Remove payload but retain replay-prevention tombstone through horizon |
| Delivery observations | Minimized immutable transport evidence; recompute projection |
| Media/transcript derivatives | Delete all payload/derivatives under scoped hold rules |
| Opt-in/template evidence | Immediate operational revocation; permissible evidence retained |
| Telemetry | No customer/provider payload; bounded retention; incident hold only |
| CE evidence | Constitutional/Legal policy; payload erasure cannot delete constitutional evidence |

Durations are named configuration classes owned by Data/Legal and accepted by the Founder where
rights/cost are material. Hold creation/release is scoped, attributable, evidenced, and never
reactivates operational use.

Ordinary logs, metrics, traces, baggage, exceptions, request capture, dead letters, and scanner
diagnostics exclude payloads, headers, signatures, phone proofs, tenant/relationship IDs, provider
refs, prompts, transcripts, message/media metadata, template variables, context facts, and secrets.
A separately authorized protected diagnostic path requires encryption, RBAC, purpose, access
evidence, retention/hold/erasure, environment isolation, and export prohibition.

## 13. Failure, Retry, Replay, Recovery, And Rollback

| Failure | Required behavior |
|---|---|
| Meta retry/duplicate | Replay stored result; no second message/action |
| Callback unavailable | Provider retry; no fabricated receipt |
| Ambiguous commit response | Reconcile idempotency key; never blind retry |
| Provider timeout | `UNKNOWN`; reconcile same attempt before new attempt |
| Late/out-of-order status | Append observation; recompute projection |
| Media expired/unsafe | Honest unavailable/rejected result; request resend or text alternative |
| Context stale/ambiguous | Reassess or bounded clarification; no consequential execution |
| AIR/model unavailable | Explicit unavailable execution; no synthetic success |
| CE unavailable | Ordinary writes fail safe; typed Stop still latches locally per ADR-031 |
| Handoff failure | Source remains active; no partial transfer |
| Environment mismatch | Reject/alert; no fallback |
| Credential revocation | Stop new calls; reconcile in-flight; never fall back |

Backups are environment-specific, encrypted with environment-specific keys, access-audited, and
separate from runtime/provider credentials. Restore to an isolated non-routable environment with no
callback, outbound, template, or provider authority. Restore in this consistency order:

`schema/watermark -> canonical conversation -> sequence/idempotency/inbox/outbox -> context/profile
lineage -> payload refs/payloads -> delivery observations/projection -> summaries/caches`.

Reactivation requires separate proof of schema, `FORCE RLS`, composite refs, sequence/dedup/outbox,
payload lineage, Stop, current identity/consent/template/environment bindings, and separate authority.

## 14. Observability And Operations

Metrics use bounded safe dimensions and cover verification denials, claim/replay, acceptance latency,
context result/staleness, policy versions, repeated-known-question violations, conclusion completion,
outbound state/age, template rejection, media state/latency, handoff, idempotency conflict, Stop,
environment denial, dead-letter age, erasure propagation, and privacy scanner findings.

Alerts classify customer action, provider outage, WAOOAW defect, security denial, stale authority,
constitutional governance unavailable, privacy leak, and recovery inconsistency. Dead letters retain
safe metadata and protected payload references, not payload. Operator actions are attributable and
environment-bound.

## 15. Deployment, Activation, Teardown, And Promotion

1. Deploy additive schema/contracts disabled.
2. Backfill and prove invariants.
3. Enable shared conversation projection for internal/generated-client tests.
4. Enable Web shared-API adoption and prove no regression.
5. Enable WhatsApp adapter only in an explicitly authorized environment.
6. Activate Demo callback/dispatch only after provider, identity, security, data, smoke, and rollback
   evidence passes.
7. Teardown Demo by disabling callback acceptance first, reconciling/isolating outstanding work,
   revoking temporary authority, disposing erasable data under policy, and proving UAT/Production
   unchanged.
8. Promote to UAT by rebuilding from controlled artifacts/configuration, never by copying Demo
   provider identity, secrets, state, templates, or data.
9. Production remains dark until number purchase, ADR acceptance, security/data/recovery evidence,
   exact candidate qualification, Founder authorization, and rollback rehearsal.

No step permits direct Demo-to-UAT/Production state promotion or Production activation by workflow
default.

## 16. WhatsApp Configuration And Activation Runbook

Each step records operator, timestamp, environment, authority reference, before/after state, safe
evidence, rollback action, and result. `Manual` means Meta/provider UI or support operation;
`Platform` means Azure/DNS/Key Vault/deployment; `Config` means protected application configuration;
`Implementation` means authorized code/schema work; `Security`/`Data` mean validation; `Founder`
means a protected decision that automation cannot make.

| # | Type | Operator-executable step and exit evidence |
|---:|---|---|
| 1 | Founder/Security | Confirm ADR acceptance, separate Work Contract, environment, spend/provider/DNS/deployment authority, operator roles, and stop conditions. Exit: authority references complete. |
| 2 | Manual | Prepare verified Meta Business and environment WABA ownership. Exit: privacy-safe ownership/status evidence. |
| 3 | Manual/Security | Create a dedicated Meta app per environment or document an approved isolation model proving separate authority, callbacks, secrets, templates, telemetry, and revocation. |
| 4 | Manual/Founder | Register Demo `9822753575`, UAT `8888912344`, or separately purchased Production number as protected configuration input; never commit it. |
| 5 | Manual | Complete provider telephone ownership verification. Exit: provider registration status, no OTP/token in evidence. |
| 6 | Manual/Config | Capture phone-number ID, WABA ID, app ID, and API version into the environment's protected configuration inventory. |
| 7 | Manual/Security | Create least-privilege verify token, app secret, outbound authority, and media authority with rotation/revocation owners. |
| 8 | Platform/Security | Store each authority as a distinct versioned secret in the environment Key Vault; prove no cross-environment read. |
| 9 | Platform/Security | Assign separate adapter runtime, media scanner, and deployment/configurator managed identities and audiences. |
| 10 | Platform | Provision stable ingress, environment hostname, DNS, TLS, and exact callback route. UAT uses a hostname over stable Azure ingress, never raw IP. |
| 11 | Config/Security | Configure GET challenge: exact mode, constant-time environment token compare, bound host, non-reflective denial. |
| 12 | Implementation/Security | Configure POST raw-body HMAC-SHA256 before middleware transformation, bounded body, constant-time compare, safe denials. |
| 13 | Manual/Config | Subscribe only required message/status event types and record provider API/schema versions. |
| 14 | Implementation/Data | Configure atomic inbound claim, durable acceptance/rejection, acknowledgement, replay, retention horizon, tombstones, and dead letters. |
| 15 | Implementation/Config | Configure outbound queue/attempts, JIT credential use, provider submission, status correlation, and reconciliation. |
| 16 | Manual/Product | Register environment-specific templates; record category, locale, variables, version, purpose, opt-in basis, and approval/revocation state. |
| 17 | Implementation/Security | Enforce service-window/template/consent eligibility at queue and send time against trusted server time and current state. |
| 18 | Implementation/Security/Data | Configure server media retrieval, quarantine, sniffing/limits, scanning, transcript/correction, clean promotion, retention, hold, and erasure. |
| 19 | Platform/Security/Data | Configure privacy-safe logs/metrics/traces, protected diagnostics if authorized, dead letters, alerts, access, retention, and leakage scans. |
| 20 | Security/Data/Application | Run environment smoke matrix: valid/invalid challenge/HMAC, fresh/stale/replayed event, inbound text, outbound template, statuses, media, Stop, and negative cross-environment tests. |
| 21 | Platform/Founder | Capture exact candidate, config versions, smoke evidence, rollback command/procedure, and activation decision. No activation without decision. |
| 22 | Manual/Platform/Data | Demo teardown: disable callback, drain/reconcile or isolate retained work, revoke credentials, remove provider bindings/templates as authorized, erase payloads, retain required tombstones/evidence, prove UAT/Production unchanged. |
| 23 | Security/Data/Platform | UAT-to-Production promotion: rebuild configuration, reapprove Production templates, validate current consent/identity/recovery, run Production-dark proof; never copy identities/secrets/data/dedup. |
| 24 | Founder | Decide Production number purchase, provider/app model, DNS/provider mutation, deployment, traffic, risk/cost acceptance, activation, rollback, or cancellation. |

## 17. Ordered Implementation Buckets And Stories

The 27 stories below cover buckets A-Y. Dependencies are explicit in Section 18. A story starts only
when all dependencies and its authority gates pass.

### CSA-CEWA-001 - Existing-State Discovery And Impact Analysis

| Field | Specification |
|---|---|
| Bucket | A - Existing-state discovery and impact analysis |
| Objective | Produce the mandatory impact record and exact strategic plan before implementation. |
| Value | Prevents architecture invention, duplication, and unsafe migration. |
| Controlling references | Enterprise §§4, 7, 21-24; ADR-052/053 implementation boundaries; this §3 |
| Affected components/directories | Read-only trace of `src/business-platform/`, `src/professional-runtime/`, `src/ai-runtime/`, `src/constitutional-engine/`, `web/`, data migrations, infra/workflows, tests, API specs, and runbooks. |
| Current behavior | Existing implementations are known only through architecture; exact reusable surfaces require authorized implementation-office inspection. |
| Required behavior | Written impact result and dependency-aware plan with exact paths, owners, migrations, gates, rollback, and per-story commands. |
| In scope | Inventory, compatibility analysis, reuse decisions, conflict/missing-decision log, exact test selectors. |
| Out of scope | Any implementation-file modification, provider/cloud mutation, or architectural resolution. |
| Reuse | Existing Conversation Core, WC-062 voice, ADR-023 identity, ADR-031 Stop, outbox/Temporal, RLS, generated clients, validation runners. |
| API/events | Inventory existing and proposed deltas; no mutation. |
| Data/RLS | Inventory schemas, roles, keys, policies, migrations, backup/recovery. |
| Migration/compatibility | Inventory current schema/API/event versions, compatibility obligations, and safe expand/migrate/contract path; make no migration. |
| Config/secrets | Inventory names/owners only; never read values. |
| Authority/security | Requires separate implementation Work Contract for later work; record current ADR status. |
| Privacy/retention | Trace every payload/derivative/evidence lifecycle. |
| Failure/retry/idempotency/dedup/replay | Map existing semantics and gaps for each boundary. |
| Observability | Inventory current safe telemetry and prohibited-data risks. |
| Rollout/rollback | Define flags, compatibility window, watermark, stop and reversal per story. |
| Targeted tests | No runtime test; validate impact record against a checklist and run repository path/spec lint. |
| Acceptance criteria | 100% of named components/surfaces have path, owner, current behavior, delta, risk, and test command; every conflict is BLOCKED, not assumed. |
| Evidence | Impact record, reuse matrix, exact dependency graph, strategic plan, command ledger. |
| Dependencies | Accepted ADRs and separate implementation authority are required to progress beyond this story. |
| Definition of done | `READY_FOR_IMPLEMENTATION_STORIES` is recorded with no unresolved architectural conflict. |

### CSA-CEWA-002 - Shared Channel-Neutral Conversation Contract

| Field | Specification |
|---|---|
| Bucket | B - Shared channel-neutral conversation contracts |
| Objective | Implement the additive BP contract used by Web, WhatsApp normalization, and future Mobile. |
| Value | One public semantic API prevents channel-specific engines and drift. |
| Controlling references | EA-CE-01/02/07/09; ADR-052 Decision 1-10; enterprise §11 |
| Affected components/directories | BP API/domain/application layers, candidate OpenAPI, generated Web client, contract tests. |
| Current behavior | Existing Conversation Core and business-platform OpenAPI provide partial timeline/command behavior. |
| Required behavior | Versioned timeline, contribution, command, reconcile, cursor/events, cancellation, handoff, context/profile, state, export/erasure contracts. |
| In scope | Additive endpoints/schemas, stable errors, generated clients, compatibility adapter. |
| Out of scope | Provider payloads, model policy bytes, new deployable, Mobile implementation. |
| Reuse | Existing BP Conversation Core, workspace commands, SSE, problem details, client generation. |
| API/events | Implement candidate OpenAPI and Section 5 events; every mutation binds idempotency/digest/context/source versions. |
| Data/RLS | Relationship-scoped access through trusted tenant; no tenant field from clients. |
| Migration/compatibility | Additive versioned contract; retain existing endpoints/readers and prove generated-client backward compatibility before cutover. |
| Config/secrets | Contract version and feature flag only; no secrets. |
| Authority/security | BP reauthorizes every operation; clients cannot call PR/AIR/CE/WBE directly. |
| Privacy/retention | Public projections minimize internal/provider/evidence details. |
| Failure/retry/idempotency/dedup/replay | Original receipt replay; same key/different digest 409; safe unavailable/conflict results. |
| Observability | Operation/result/version/latency with opaque IDs only. |
| Rollout/rollback | Additive disabled contract; dual-read; disable new operations without rewriting data. |
| Targeted tests | BP OpenAPI lint/slice; generated-client compile; endpoint authorization/idempotency/error contract tests. |
| Acceptance criteria | Web and a second generated test client pass identical contract fixtures; forbidden writable fields are rejected; existing endpoints remain byte-compatible where declared. |
| Evidence | OpenAPI diff, generated-client checksum, contract results, backward-compatibility report. |
| Dependencies | CSA-CEWA-001. |
| Definition of done | One additive shared API exists with no channel/provider branch in canonical semantics. |

### CSA-CEWA-003 - Canonical History, Sequencing, And Transactional Outbox

| Field | Specification |
|---|---|
| Bucket | C - Canonical conversation history and sequencing |
| Objective | Guarantee one ordered relationship conversation under concurrent channels. |
| Value | Preserves continuity and prevents duplicate/conflicting decisions. |
| Controlling references | EA-CE-01/05; ADR-052 Decision 1,7,12; enterprise §§10.2-10.3, 15.1-15.3 |
| Affected components/directories | BP persistence/domain services, migrations, outbox worker, integration tests. |
| Current behavior | BP owns timeline/order/idempotency, but new cross-channel invariants require explicit proof. |
| Required behavior | Sequence/idempotency/message/outbox commit atomically; protected intent commits once. |
| In scope | Per-conversation allocator, composite uniqueness, replay, ambiguous-commit reconciliation. |
| Out of scope | Provider delivery ordering as canonical order; history rewrite. |
| Reuse | Existing Conversation Core transaction and outbox patterns. |
| API/events | Contribution receipt returns canonical message/sequence; accepted event publishes post-commit. |
| Data/RLS | Unique environment+tenant+relationship+conversation+sequence; FORCE RLS and tenant-consistent FKs. |
| Migration/compatibility | Expand allocator/state, provenance-backfill sequence watermarks, dual-read old/new records, then contract only after rollback expiry. |
| Config/secrets | Feature flag and migration watermark only. |
| Authority/security | Actor/relationship derived server-side; protected intent source-version check inside transaction. |
| Privacy/retention | Payload reference separate from canonical metadata; erasure leaves permitted tombstone. |
| Failure/retry/idempotency/dedup/replay | Concurrent winner; same digest replay; conflict on changed digest; no gap reuse. |
| Observability | Commit/replay/conflict/outbox latency and sequence gap alerts without IDs. |
| Rollout/rollback | Expand allocator/state, backfill watermark, dual-read, cut over, preserve new sequences on rollback. |
| Targeted tests | BP persistence tests for 100 concurrent appends, duplicate/changed digest, ambiguous commit, outbox atomicity, RLS cross-tenant denial. |
| Acceptance criteria | Exactly 100 unique monotonic sequences for 100 accepted appends; duplicate produces original result; protected intent mutates at most once. |
| Evidence | Migration/reversal output, concurrency results, outbox reconciliation report. |
| Dependencies | CSA-CEWA-002. |
| Definition of done | CE-FIT-01 and CE-FIT-08 persistence prerequisites pass. |

### CSA-CEWA-004 - Interaction Context Resolver

| Field | Specification |
|---|---|
| Bucket | D - Interaction Context resolution |
| Objective | Resolve immutable versioned context from trusted state and bounded hints. |
| Value | Relevant conversation without client prompt/authority injection. |
| Controlling references | EA-CE-03; ADR-052 Decision 3-4,8-9; enterprise §8 |
| Affected components/directories | BP context domain/application/API, persistence, PR request contract, tests. |
| Current behavior | Screens and workspace state provide partial context without the new unified contract. |
| Required behavior | Apply Section 8 precedence and stale/ambiguous/blocked outcomes. |
| In scope | Registered vocabulary, opaque subject refs, source-version binding, invalidation hook. |
| Out of scope | Free-form prompt/context, client tenant/authority, model-selected context. |
| Reuse | Relationship/workspace projections, Decision Space and plan versions. |
| API/events | InteractionContext schema; list contexts; context reference on every execution. |
| Data/RLS | Immutable context row bound to environment/tenant/relationship/conversation/source versions. |
| Migration/compatibility | Add immutable context versions beside legacy context, shadow-resolve/compare, retain prior-version reader through rollback window. |
| Config/secrets | Registered context vocabulary/version; no secrets. |
| Authority/security | Server authorization of key/subject; forged/unknown values cause zero mutation. |
| Privacy/retention | Minimize context payload; inherit source sensitivity and lifecycle. |
| Failure/retry/idempotency/dedup/replay | Deterministic same-input resolution; stale source blocks consequential execution; replay preserves the original bound version. |
| Observability | Safe result category, staleness cause class, resolver latency. |
| Rollout/rollback | Shadow-resolve and compare; feature-gate new context version; retain prior reader. |
| Targeted tests | Precedence table, forged key, cross-subject, stale versions, pending intent, channel downgrade, deterministic replay. |
| Acceptance criteria | All precedence fixtures resolve exact expected context/version; invalid inputs create zero rows/messages/commands. |
| Evidence | Resolver fixture matrix and mutation-count proof. |
| Dependencies | CSA-CEWA-002, CSA-CEWA-003. |
| Definition of done | CE-FIT-02 and CE-FIT-03 targeted tests pass. |

### CSA-CEWA-005 - Layered Conversation Policy And Rendering

| Field | Specification |
|---|---|
| Bucket | E - Layered Conversation Policy and style profiles |
| Objective | Resolve exact policy layers and channel rendering without semantic drift. |
| Value | Consistent, truthful, consultative behavior across channels. |
| Controlling references | EA-CE-04; ADR-052 Decision 5,8; enterprise §9 |
| Affected components/directories | BP policy selection, policy registry, PR/AIR request schema, renderers, conformance tests. |
| Current behavior | Agent prompts and presentations may contain distributed style behavior. |
| Required behavior | Exact precedence, typed dialogue acts, conclusion protocol, no channel-owned tone prompt. |
| In scope | Policy references, conflict rules, semantic rendering fixtures, professional conformance. |
| Out of scope | Prompt text rewrite beyond separately authorized conformance; model/provider choice. |
| Reuse | Existing agent policy/persona records and AIR typed-output contracts. |
| API/events | ConversationPolicyReference and conclusion fields; no policy bytes in public client. |
| Data/RLS | Immutable version references scoped to institution/professional/relationship as applicable. |
| Migration/compatibility | Publish additive policy references, shadow old/new rendering, keep prior supported policy version and block new-only commands on rollback. |
| Config/secrets | Policy registry versions; no secrets. |
| Authority/security | Untrusted content cannot populate policy fields; lower layers cannot weaken safety. |
| Privacy/retention | Communication profile is relationship-scoped and erasable per source class. |
| Failure/retry/idempotency/dedup/replay | Missing/conflicting policy fails closed before model call; retry/replay binds the original version without duplicate execution. |
| Observability | Policy version distribution and safe conformance violation codes. |
| Rollout/rollback | Shadow compare; per-professional opt-in; retain prior supported version. |
| Targeted tests | Precedence conflicts, dialogue-act schema, conclusion fields, injection into policy, semantic-equivalence corpus. |
| Acceptance criteria | Same context/policy yields equivalent recommendation/decision/next action on Web/WhatsApp fixtures; no client can change policy. |
| Evidence | Policy resolution matrix and CE-FIT-04/05/06 corpus results. |
| Dependencies | CSA-CEWA-004. |
| Definition of done | CE-FIT-04, CE-FIT-05, and CE-FIT-06 targeted tests pass. |

### CSA-CEWA-006 - Context Observation, Profile, Summary Lineage

| Field | Specification |
|---|---|
| Bucket | F - Context observation, profile projection, summary lineage and invalidation |
| Objective | Separate immutable observations, replaceable profile, and rebuildable summaries. |
| Value | Reproducible customer understanding without stale or cross-customer memory. |
| Controlling references | EA-CE-05; ADR-052 Decision 7,9,11-12; enterprise §§10, 15.4-15.5 |
| Affected components/directories | BP profiling persistence/services, AIR derivation contract, workers, migrations, tests. |
| Current behavior | Existing profile/summary mechanisms require lineage and invalidation analysis. |
| Required behavior | Legal status transitions, exact source lineage, invalidation, rebuild, no summary-as-fact. |
| In scope | Observation append, projection rebuild, source change event, summary source set/digests. |
| Out of scope | Global customer memory, silent fact promotion, cross-agent sharing without authorization. |
| Reuse | Existing customer profile, RAG, payload store, outbox/worker mechanisms. |
| API/events | Profile inspect/correct; ContextSourcesChanged and ArtifactInvalidated events. |
| Data/RLS | Environment+tenant+relationship+subject keys; append-only observation; erasable summary payload. |
| Migration/compatibility | Backfill observations with explicit provenance, shadow the new projection, rebuild derived artifacts, and retain canonical source compatibility. |
| Config/secrets | Derivation/model/policy version and lifecycle classes. |
| Authority/security | Only accountable sources/owners promote confirmed facts; AIR proposes only. |
| Privacy/retention | Highest-source sensitivity; correction/erasure propagates to summary/vector/cache. |
| Failure/retry/idempotency/dedup/replay | Idempotent deduplicated invalidation/rebuild; replay cannot reactivate a stale artifact or enter new execution. |
| Observability | Projection lag, invalidation/rebuild state, stale-use violation count. |
| Rollout/rollback | Backfill observations with provenance; shadow projection; rebuild derived artifacts. |
| Targeted tests | Status transitions, correction/dispute/erasure, source expiry, model/policy change, cross-tenant leakage, rebuild determinism. |
| Acceptance criteria | Every summary reproduces source set/version; source correction invalidates affected summaries before next consequential execution; zero cross-customer reads. |
| Evidence | Lineage samples, rebuild checksums, RLS/adversarial results. |
| Dependencies | CSA-CEWA-003, CSA-CEWA-004. |
| Definition of done | Context/profile/summary invariants and CE-FIT-03 prerequisites pass. |

### CSA-CEWA-007 - Cross-Channel Continuity And Binding

| Field | Specification |
|---|---|
| Bucket | G - Cross-channel continuity and channel binding |
| Objective | Resume one conversation through authenticated prepare/activate/revert handoff. |
| Value | Seamless continuity without authority expansion or parallel history. |
| Controlling references | EA-CE-01/07; ADR-052 Decision 1; enterprise §§10.3, 11 |
| Affected components/directories | BP continuity/binding services, Web client, adapter integration, tests. |
| Current behavior | Existing omnichannel continuity and F5 handoff foundations are delivered. |
| Required behavior | Signed/hash-bound checkpoint, fresh target authentication, atomic activation/revert. |
| In scope | Channel session state, cursor/read position, active source preservation on failure. |
| Out of scope | Copying history/profile, assurance upgrade by channel switch. |
| Reuse | Existing omnichannel handoff/checkpoint contracts. |
| API/events | Prepare, authenticate, activate, revert; canonical cursor unchanged. |
| Data/RLS | Binding includes environment/tenant/relationship/participant/channel/authenticatedAt/state. |
| Migration/compatibility | Add checkpoint/binding version beside existing handoff, preserve source-channel behavior, and retain the prior handoff reader during rollout. |
| Config/secrets | Handoff TTL/signing key through existing protected configuration. |
| Authority/security | Target reauthentication; assurance cannot exceed proof; binding mismatch denies. |
| Privacy/retention | Checkpoint contains opaque refs/digests, not transcript. |
| Failure/retry/idempotency/dedup/replay | Idempotent deduplicated activation/revert; replay cannot activate twice; source remains active on timeout/failure. |
| Observability | Handoff stage/result/latency, no raw identity. |
| Rollout/rollback | Additive checkpoint version; retain current path until equivalence passes. |
| Targeted tests | Web->WhatsApp->Web, failed target auth, expired/replayed checkpoint, simultaneous activation, source-version change. |
| Acceptance criteria | Relationship/conversation/message IDs and sequence remain unchanged across round trip; failed handoff changes no authority. |
| Evidence | CE-FIT-01 journey and negative handoff matrix. |
| Dependencies | CSA-CEWA-002, CSA-CEWA-003, CSA-CEWA-004. |
| Definition of done | Cross-channel continuity passes without duplicate state. |

### CSA-CEWA-008 - Deterministic Identity Resolution And Assurance

| Field | Specification |
|---|---|
| Bucket | H - Identity resolution and assurance tiers |
| Objective | Resolve provider participant to one authorized relationship and enforce assurance floors. |
| Value | Prevents takeover, cross-tenant attachment, and confirmation downgrade. |
| Controlling references | ADR-023; ADR-053 Decision 1-3; enterprise §§12.7, 14.2 |
| Affected components/directories | BP identity boundary, Phone Identity, binding persistence, command authorization, tests. |
| Current behavior | Meta-signed phone identity supports low-risk participation; stronger actions need explicit contract. |
| Required behavior | Section 7 deterministic outcomes, tiers 1-4, exact-intent binding, invalidation. |
| In scope | Tuple resolution, reassignment/revocation/staleness, non-enumerating denial, portal step-up. |
| Out of scope | Keycloak session issuance from phone, automatic relationship attachment, WhatsApp Tier 4 completion. |
| Reuse | ADR-023 proof, BP Identity Boundary, Keycloak portal authentication. |
| API/events | Internal assertion carries binding/assurance/version/expiry, never raw number or tenant input. |
| Data/RLS | Composite environment/tenant/relationship binding; provider proof cannot bypass RLS. |
| Migration/compatibility | Shadow-resolve existing bindings, backfill immutable environment/assurance versions, default-deny unknown legacy rows, retain prior reads only during bounded verification. |
| Config/secrets | Admission policy, tier/freshness configuration; protected identity keys. |
| Authority/security | Commit-time recheck; zero mutation on denial; Stop release portal-only. |
| Privacy/retention | Minimized phone proof; reassignment revokes operational use and retains limited evidence. |
| Failure/retry/idempotency/dedup/replay | Same verified tuple resolves deterministically; retries replay the same denial/assertion; ambiguous result never auto-retries mutation. |
| Observability | Safe denial reason class and reassignment alert; no phone/tenant IDs. |
| Rollout/rollback | Shadow resolution; migrate bindings; default deny until exact match. |
| Targeted tests | Zero/one/multiple, revoked/reassigned/stale, cross-tenant reuse, environment/recipient mismatch, stale step-up, exact-intent mismatch, Tier 4 denial. |
| Acceptance criteria | Every denied case creates zero relationship/binding/command mutation; Tier 2/3 confirmation commits only exact unexpired intent; Tier 4 never completes via WhatsApp. |
| Evidence | Resolution matrix, mutation counts, assurance test report. |
| Dependencies | CSA-CEWA-001, CSA-CEWA-003. |
| Definition of done | CE-FIT-02/08/12 identity prerequisites pass. |

### CSA-CEWA-009 - Signed WhatsApp Webhook Ingress

| Field | Specification |
|---|---|
| Bucket | I - WhatsApp signed webhook ingress |
| Objective | Authenticate GET/POST callbacks before parsing or mutation. |
| Value | Rejects forged, modified, oversized, stale, and wrong-environment traffic. |
| Controlling references | ADR-053 Decision 3-5,13; enterprise §12.1; R-146 HIGH-02 |
| Affected components/directories | BP public adapter endpoint, raw-body middleware ordering, secret access, ingress tests. |
| Current behavior | Phone Identity validates Meta HMAC/timestamp; exact adapter integration requires discovery. |
| Required behavior | Exact challenge predicates and bounded raw-body HMAC-SHA256 with inclusive freshness. |
| In scope | Header algorithm parse, constant-time compare, host/environment bind, body limit, safe response. |
| Out of scope | Source IP authentication, JSON parse before verification, professional execution in callback. |
| Reuse | ADR-023 verification utility if impact analysis proves exact raw-byte semantics. |
| API/events | Candidate webhook GET/POST; verified envelope passed internally only. |
| Data/RLS | No tenant lookup before verified environment/provider tuple; no durable payload on rejection. |
| Migration/compatibility | Add callback version/config dark, retain existing phone path until raw-byte equivalence passes, and remove old verification only after rollback expiry. |
| Config/secrets | Environment verify token/app secret versions through adapter identity only. |
| Authority/security | Wrong workload/audience/environment/version fails closed; secrets never logged. |
| Privacy/retention | Rejections retain safe reason/correlation only. |
| Failure/retry/idempotency/dedup/replay | Invalid returns non-retryable safe denial; verified-but-undurable returns retryable failure; durable retries enter Story 010 dedup/replay. |
| Observability | Verification outcome and latency with bounded reason labels. |
| Rollout/rollback | Endpoint dark until authorized callback; dual secret overlap only during bounded rotation. |
| Targeted tests | Valid/invalid mode/token/host, valid/invalid/modified signature, middleware mutation, oversized body, `t-300s`/`t+300s` accepted and outside rejected, wrong environment. |
| Acceptance criteria | No parser/tenant/mutation call occurs before verification; all boundary-time predicates match the approved inclusive rule. |
| Evidence | Middleware-order trace, timing/fuzz matrix, secret-access audit. |
| Dependencies | CSA-CEWA-008 and authorized environment configuration. |
| Definition of done | Authentication portion of CE-FIT-09 passes. |

### CSA-CEWA-010 - Atomic Inbound Claim, Acknowledgement, Deduplication, And Replay

| Field | Specification |
|---|---|
| Bucket | J - Atomic durable webhook claim, acknowledgement, deduplication and replay |
| Objective | Persist one durable result before provider success and replay it without repeated work. |
| Value | Prevents webhook loss, duplicate messages, and duplicate professional action. |
| Controlling references | ADR-053 Decision 13; enterprise §§12.1, 15.2-15.3; R-146 HIGH-02; R-147 DA-H4 |
| Affected components/directories | BP transport inbox/outbox, persistence migration, callback coordinator, cleanup/recovery, integration tests. |
| Current behavior | Existing phone dedup exists; atomicity, namespace, result replay, and retention need exact impact proof. |
| Required behavior | `RECEIVED -> VERIFIED -> CLAIMED -> DURABLY_ACCEPTED -> OUTCOME_RECORDED`, with durable typed rejection/conflict/reconciliation. |
| In scope | Compound identity/digest, concurrent first delivery, success gate, delayed retry, tombstone horizon. |
| Out of scope | Acknowledgement before durability; freshness rejection of a known accepted retry; Demo cleanup before horizon. |
| Reuse | Existing inbox/outbox/idempotency/reconciliation primitives where invariants match. |
| API/events | Callback returns success only for durable acceptance/outcome/replay; internal accepted event publishes post-commit. |
| Data/RLS | Environment+app/WABA+recipient number ID+event ID uniqueness; resolved tenant/relationship added without provider-only lookup. |
| Migration/compatibility | Expand inbox/tombstones, dual-record old/new dedup outcomes, backfill no fabricated claims, and preserve both stores through rollback/recovery horizon. |
| Config/secrets | Retention class no shorter than all provider/reconciliation/security/backup/unresolved horizons. |
| Authority/security | Verified event only; same identity/different digest is security conflict with zero additional mutation. |
| Privacy/retention | Erase payload, retain non-reconstructive replay tombstone through horizon/hold. |
| Failure/retry/idempotency/dedup/replay | One concurrent winner; losers replay; crash before commit retries; crash after commit reconciles original result. |
| Observability | Claim winner/replay/conflict/reconciliation/age and callback latency, safe dimensions only. |
| Rollout/rollback | Add inbox and dual-record; prove recovery consistency; never drop old dedup during rollback. |
| Targeted tests | 100 concurrent identical deliveries, changed-digest conflict, crash boundaries, stale unseen event, delayed known retry, restore/replay, cleanup denial. |
| Acceptance criteria | One durable acceptance/outbox/message maximum; all identical retries return the same result; no success is returned before durable state. |
| Evidence | Transaction fault-injection report, retention proof, callback result matrix. |
| Dependencies | CSA-CEWA-003, CSA-CEWA-009. |
| Definition of done | Durable-ack portion of CE-FIT-09 passes. |

### CSA-CEWA-011 - Inbound Message Normalization

| Field | Specification |
|---|---|
| Bucket | K - WhatsApp inbound message normalization |
| Objective | Convert verified Meta text/interactive/media/audio/status events into closed channel-neutral envelopes. |
| Value | Keeps provider concepts out of canonical conversation semantics. |
| Controlling references | EA-CE-07; ADR-053 Decision 6,10; enterprise §12.2 |
| Affected components/directories | BP adapter normalization, schema/version registry, mapping tests. |
| Current behavior | Existing WhatsApp journey/phone path may normalize a smaller provider subset. |
| Required behavior | Closed mapping for supported provider versions/types; unsupported values produce typed non-mutation result. |
| In scope | Text, interactive reply, media ref, audio, reply/context refs, status routing. |
| Out of scope | Provider URLs/tokens in public envelope, raw phone in timeline, canonical business decisions. |
| Reuse | Existing Conversation Core contribution schema and WC-062 voice entry. |
| API/events | Internal `VerifiedProviderEnvelopeV1`; normalized contribution/status event. |
| Data/RLS | Provider provenance stored in transport boundary; canonical record gets opaque correlation. |
| Migration/compatibility | Introduce versioned mapper beside existing normalization, run golden dual-output comparison, and retain previous provider-version mapper during overlap. |
| Config/secrets | Supported Meta API/event schema versions by environment. |
| Authority/security | Environment/identity binding precedes mapping; provider context reference never grants authority. |
| Privacy/retention | Minimize phone/provider fields; raw payload follows inbox lifecycle. |
| Failure/retry/idempotency/dedup/replay | Mapping is deterministic; duplicate provider input deduplicates before mapping; unsupported type records a durable typed outcome for replay. |
| Observability | Message type/schema version/result with bounded labels. |
| Rollout/rollback | Versioned mapper behind adapter flag; retain previous mapper during provider version overlap. |
| Targeted tests | Golden payloads for every supported type/version, unknown/malformed values, reply/media/status routing, privacy field rejection. |
| Acceptance criteria | Every supported fixture produces the exact expected channel-neutral envelope; no provider token/URL/raw phone enters canonical/public schemas. |
| Evidence | Golden mapping corpus and schema-coverage report. |
| Dependencies | CSA-CEWA-010. |
| Definition of done | All supported inputs normalize without channel-specific canonical behavior. |

### CSA-CEWA-012 - Outbound Queueing And Provider Transport

| Field | Specification |
|---|---|
| Bucket | L - Outbound message queueing and provider transport |
| Objective | Dispatch WhatsApp representations only from canonical BP outcomes with isolated authority. |
| Value | Reliable delivery without coupling provider transport to professional success. |
| Controlling references | ADR-053 Decision 6-7,12,14; enterprise §12.3 |
| Affected components/directories | BP outbox/worker, provider client abstraction, Key Vault identity, persistence, tests. |
| Current behavior | Existing outbound/provider registry mechanisms require impact analysis for reuse. |
| Required behavior | Logical message -> distinct attempts -> provider correlation; JIT environment-bound credential use. |
| In scope | Queue, attempt, submission, timeout/unknown, reconciliation, retry as new attempt. |
| Out of scope | Direct PR/AIR/provider send, cross-environment/credential fallback, transport success as execution success. |
| Reuse | Existing outbox/Temporal/provider registry and managed identity patterns. |
| API/events | Consume `OutboundRepresentationQueuedV1`; emit provider submission/status observations. |
| Data/RLS | Logical message bound to canonical message; attempt keyed by environment/message/number/attempt. |
| Migration/compatibility | Add logical-message/attempt records and outbox beside legacy dispatch, dry-run/compare, cut over by flag, preserve queued work on rollback. |
| Config/secrets | Endpoint/API version, timeout, retry policy, separate outbound authority in Key Vault. |
| Authority/security | Adapter identity only; current environment/audience; no secret propagation. |
| Privacy/retention | Payload ref instead of logged content; provider request retained only under lifecycle policy. |
| Failure/retry/idempotency/dedup/replay | Timeout -> UNKNOWN/reconcile same attempt; duplicate worker lease is idempotent; retry creates a new attempt; replay never duplicates the logical message. |
| Observability | Queue age, attempt count, submission/result, reconciliation lag, credential denial class. |
| Rollout/rollback | Provider client disabled; dry-run sink; enable environment after qualification; disable dispatch without deleting queue. |
| Targeted tests | Outbox atomicity, timeout, retry/new attempt, duplicate worker lease, credential denial, environment mismatch, provider 4xx/5xx matrix. |
| Acceptance criteria | One logical message may have many attempts but at most one submission per attempt identity; no transport result mutates execution/decision/evidence. |
| Evidence | Fault-injection/reconciliation report and secret-access audit. |
| Dependencies | CSA-CEWA-002, CSA-CEWA-003, CSA-CEWA-008. |
| Definition of done | Provider transport is recoverable and state-separated. |

### CSA-CEWA-013 - Service Window, Consent, And Template Eligibility

| Field | Specification |
|---|---|
| Bucket | M - Service-window and template eligibility |
| Objective | Fail closed on current service-window, consent, purpose, and exact template state at queue and send. |
| Value | Prevents unauthorized or invalid outbound messages. |
| Controlling references | ADR-053 Decision 8; enterprise §12.4; R-146 MEDIUM-03 |
| Affected components/directories | BP eligibility policy, template config projection, outbound worker, tests. |
| Current behavior | Provider/template behavior is not activated; eligibility contract is new. |
| Required behavior | Trusted receipt-time window, inclusive boundaries, exact approved template tuple, immediate revocation. |
| In scope | Qualifying inbound types, clock, opt-in/out, purpose, locale/schema/category/version/environment. |
| Out of scope | Provider acceptance as WAOOAW consent; fallback template/channel; hard-coded templates. |
| Reuse | Existing consent/provider-config and policy evaluation mechanisms found in discovery. |
| API/events | Eligibility evidence ref on queued event; typed non-dispatched outcome on change. |
| Data/RLS | Template/consent evidence bound to environment/tenant/relationship/recipient/purpose. |
| Migration/compatibility | Add versioned eligibility evidence and shadow evaluation; existing sends remain on old path until parity and rollback-window proof. |
| Config/secrets | Environment template registry and provider window duration/version; no secret in template config. |
| Authority/security | Queue and pre-send reauthorize; Stop/termination/revocation invalidates immediately. |
| Privacy/retention | Consent/template evidence retained by Legal/Data class; variables follow message payload policy. |
| Failure/retry/idempotency/dedup/replay | Boundary race resolved by pre-send check; ineligible attempt never submitted; duplicate queue work deduplicates; replay returns the same typed outcome unless a new command is created. |
| Observability | Safe rejection reason, boundary timing, template version distribution. |
| Rollout/rollback | Shadow eligibility against dry-run; enable only after complete environment template inventory. |
| Targeted tests | Inside/outside/exact boundary, qualifying/nonqualifying inbound, opt-out after queue, template paused/revoked/mismatched locale/schema/version/environment, trusted-clock skew. |
| Acceptance criteria | Every matrix cell has deterministic dispatch/non-dispatch; state change before submission always prevents send. |
| Evidence | Eligibility matrix and provider-template inventory snapshot. |
| Dependencies | CSA-CEWA-010, CSA-CEWA-012. |
| Definition of done | CE-FIT-10 passes. |

### CSA-CEWA-014 - Delivery Observations And Derived Projection

| Field | Specification |
|---|---|
| Bucket | N - Provider delivery/read observations and derived delivery projection |
| Objective | Preserve all provider observations and derive truthful current transport state. |
| Value | Honest delivery without conflating transport, decisions, execution, or evidence. |
| Controlling references | EA-CE-06; ADR-053 Decision 7; enterprise §§12.3, 15.6; R-147 DA-H5 |
| Affected components/directories | BP status adapter, append-only transport data, projection worker/API, tests. |
| Current behavior | Existing provider statuses may use a mutable state; impact analysis decides migration. |
| Required behavior | Immutable observations, explicit precedence/reconciliation, retries as attempts. |
| In scope | Duplicate/late/regressive/contradictory status, provider vs receipt time, recompute after restore. |
| Out of scope | Status causing customer approval, professional completion, or CE evidence. |
| Reuse | Existing delivery/status projection and outbox correlation where compatible. |
| API/events | `ProviderDeliveryObservedV1`; public independent delivery dimension. |
| Data/RLS | Append-only observation keyed by environment/event/attempt; derived projection rebuildable. |
| Migration/compatibility | Dual-write mutable state and immutable observations, compare projections, cut over reads, and retain observation history on rollback. |
| Config/secrets | Provider status mapping/version. |
| Authority/security | Only signed/correlated status can append; mismatched environment denied. |
| Privacy/retention | Minimized provider refs under transport retention/hold class. |
| Failure/retry/idempotency/dedup/replay | Duplicate observation append deduplicates idempotently; replay preserves history; unknown status marks reconciliation without destructive retry. |
| Observability | Observation lag, projection conflict, unknown age, late status count. |
| Rollout/rollback | Dual-write mutable+observation, compare, cut over; retain observation history on rollback. |
| Targeted tests | All permutations of accepted/delivered/read/failed/expired/unknown, duplicate, contradiction, late success after uncertainty, multiple attempts, restore rebuild. |
| Acceptance criteria | Projection is deterministic for every permutation; observation count is lossless; other state dimensions remain unchanged. |
| Evidence | Permutation/property-test results and rebuild checksum. |
| Dependencies | CSA-CEWA-010, CSA-CEWA-012. |
| Definition of done | CE-FIT-07 delivery coverage passes. |

### CSA-CEWA-015 - Media Retrieval, Quarantine, Scan, Retention, And Erasure

| Field | Specification |
|---|---|
| Bucket | O - Media download, quarantine, sniffing, limits, scanning, retention and erasure |
| Objective | Admit only clean, bounded, authorized media through the existing voice/content boundary. |
| Value | Supports low-literacy/voice journeys without malware, resource exhaustion, or privacy leakage. |
| Controlling references | ADR-053 Decision 9-10,14; enterprise §§12.5, 15.7-15.8; R-146 MEDIUM-02; R-147 DA-H6/H7 |
| Affected components/directories | Adapter retrieval, payload/quarantine stores, scanner worker, AIR transcription, BP correction flow, erasure workers, tests. |
| Current behavior | WC-062 voice and erasable payload foundations exist; provider media path is not active. |
| Required behavior | Section 10.3 lineage, deny-by-default formats/limits, scanner-only clean promotion, accepted-version handoff. |
| In scope | Inbound/outbound media, audio transcript/correction, expiry, quarantine, hold, deletion/provider obligation. |
| Out of scope | Client/provider URL exposure, processing uncertain media, implicit send/interpretation consent. |
| Reuse | WC-062 voice data contract, payload store, AIR transcription, existing scanner/storage patterns. |
| API/events | Opaque media ref and typed media states; canonical contribution only after required confirmation. |
| Data/RLS | Payload boundary keyed by environment/tenant/relationship; no reconstructive hash outside boundary. |
| Migration/compatibility | Extend WC-062 lineage additively, migrate opaque refs/derivatives with provenance, retain text fallback and prior accepted contributions on rollback. |
| Config/secrets | Approved type/size/resource policy; separate media credential and scanner identity. |
| Authority/security | Retrieval and scanner permissions separated; scanner has no conversation/provider dispatch authority. |
| Privacy/retention | Payload/derivative/backup/cache/provider deletion tracked; hold is scoped and evidenced. |
| Failure/retry/idempotency/dedup/replay | Expired URL requests resend; timeout/error remains quarantine; retrieval/scan retries deduplicate by payload/version and never replay unsafe content. |
| Observability | Safe state/latency/verdict class; no filename/MIME/content/provider ref in ordinary telemetry. |
| Rollout/rollback | Text first; media flag remains off until format/limit/retention owner decisions recorded; disable intake, retain safe cleanup. |
| Targeted tests | MIME/signature mismatch, archive/polyglot/active format, expansion/resource limits, malware, scan timeout/error, expired URL, low-confidence transcript, correction, erasure/hold/backup propagation. |
| Acceptance criteria | Zero unclean/unknown payload reaches AIR/PR/canonical context; erasure removes all resolvable derivatives and retains only permitted tombstone/evidence. |
| Evidence | CE-FIT-11 corpus, scanner permission proof, erasure lineage report. |
| Dependencies | CSA-CEWA-006, CSA-CEWA-008, CSA-CEWA-011. |
| Definition of done | CE-FIT-11 passes and owner-bound format/limit/retention decisions are recorded. |

### CSA-CEWA-016 - WhatsApp Emergency Stop

| Field | Specification |
|---|---|
| Bucket | P - WhatsApp Emergency Stop |
| Objective | Recognize and durably latch explicit Stop before context/model/ordinary work. |
| Value | Preserves absolute human override during provider retries and CE outage. |
| Controlling references | C-001; ADR-031; ADR-053 Decision 15; enterprise §12.8; R-146 HIGH-04 |
| Affected components/directories | BP adapter command mapping, PR Stop orchestrator/buffer, CE sync, UI/template, tests. |
| Current behavior | PR local halt and CE evidence buffering exist; WhatsApp typed ingress is new. |
| Required behavior | Verified/bound typed Stop bypasses model, latches once, locally halts during CE outage, never auto-releases. |
| In scope | Duplicate/simultaneous channels/restart/timeout/reconnect, ambiguous conversational “stop”, portal-only release. |
| Out of scope | Model/free-text classifier as security boundary; WhatsApp release; ordinary reconnection release. |
| Reuse | Existing Stop orchestrator, SignalR/WebSocket path, ADR-031 local evidence buffer. |
| API/events | Typed Stop command and `EmergencyStopLatchedV1`; safe acknowledgement includes pending CE sync state. |
| Data/RLS | Relationship-scoped latch/idempotency; protected local evidence buffer; tenant-safe CE flush. |
| Migration/compatibility | Add WhatsApp typed ingress to the existing ADR-031 latch without changing latch identity; rollback removes ingress only and never clears an active Stop. |
| Config/secrets | Existing Stop latency budget; no new credential. |
| Authority/security | Signature+binding required; Stop highest precedence; release Tier 4 portal-only. |
| Privacy/retention | Minimized actor proof ref and constitutional evidence; no message text needed for typed control. |
| Failure/retry/idempotency/dedup/replay | Duplicate/simultaneous/replayed Stop returns the same latch; CE flush deduplicates idempotently; no retry/recovery releases it. |
| Observability | Stop detected/latched/halt/CE-sync latency and failure without customer IDs. |
| Rollout/rollback | Stop path must be available before ordinary WhatsApp work; disabling WhatsApp leaves existing Stop active. |
| Targeted tests | CE outage, duplicate delivery, simultaneous Web/WhatsApp, adapter/PR restart, reconnect, timeout, ambiguous text, WhatsApp release attempt, latency budget. |
| Acceptance criteria | All consequential contexts halt within existing <=250 ms P99 budget; one latch/evidence intent; no model call/billing/outbound work before halt. |
| Evidence | CE-FIT-13 timing/state report and CE recovery flush proof. |
| Dependencies | CSA-CEWA-008, CSA-CEWA-010, existing ADR-031 conformance. |
| Definition of done | CE-FIT-13 passes. |

### CSA-CEWA-017 - Privacy-Safe Telemetry, Dead Letters, And Alerts

| Field | Specification |
|---|---|
| Bucket | Q - Privacy-safe logs, metrics, traces, dead letters and alerts |
| Objective | Observe all state machines without exposing prohibited data. |
| Value | Operability and incident response without privacy/security regression. |
| Controlling references | Enterprise §§14.3, 18; R-146 MEDIUM-04 |
| Affected components/directories | Shared logging/OTel middleware, workers, dashboards/alerts, dead letters, leakage tests. |
| Current behavior | OTel and privacy controls exist but new paths add leakage surfaces. |
| Required behavior | Section 12 prohibition across success/failure/framework/retry/scanner/trace paths. |
| In scope | Safe codes/dimensions, protected diagnostic gate, retention/RBAC, automated scan. |
| Out of scope | Payload/high-cardinality labels or “sampled” prohibited data. |
| Reuse | Existing OTel/Azure Monitor, structured logging, privacy scanner, protected evidence patterns. |
| API/events | Correlation uses opaque IDs; exception responses use stable safe problems. |
| Data/RLS | Dead letters store safe metadata + protected payload ref; environment/tenant access enforced. |
| Migration/compatibility | Add safe fields/exporters and leakage gates before new paths; retain existing dashboards during metric-name compatibility window. |
| Config/secrets | Sampling/retention/alert routing per environment; no secret in telemetry config. |
| Authority/security | Protected diagnostics separately authorized and audited; ordinary operators cannot read payloads. |
| Privacy/retention | Explicit lifecycle/hold/deletion/export prohibition for diagnostics and telemetry. |
| Failure/retry/idempotency/dedup/replay | Telemetry failure cannot acknowledge business success; duplicate telemetry is bounded; dead-letter retry/replay uses original idempotency and dedup domains. |
| Observability | Self-monitor privacy-scan failures, dropped spans, dead-letter age, alert delivery. |
| Rollout/rollback | Enable leakage gate before path flags; rollback disables new exporters without losing required safe evidence. |
| Targeted tests | Success/failure/framework/parser/HMAC/retry/dead-letter/scanner/media/trace-baggage leakage corpus; RBAC and retention. |
| Acceptance criteria | Automated scan finds zero prohibited values in every ordinary channel; alerts fire for each classified synthetic fault. |
| Evidence | CE-FIT-14 scan and alert-routing results. |
| Dependencies | CSA-CEWA-002 through CSA-CEWA-016 as applicable; may build shared utilities in parallel after CSA-CEWA-001. |
| Definition of done | CE-FIT-14 passes. |

### CSA-CEWA-018 - Demo Provisioning, Activation, And Complete Teardown

| Field | Specification |
|---|---|
| Bucket | R - Demo environment provisioning and teardown |
| Objective | Qualify the adapter in an isolated disposable Demo environment and remove it safely. |
| Value | Provider proof without contaminating UAT/Production. |
| Controlling references | ADR-053 Decision 1-5,11-14; enterprise §§13.1-13.6, 15.10 |
| Affected components/directories | Environment config, approved IaC/deploy workflow, Key Vault, ingress/DNS/TLS, runbook/evidence; no change without authority. |
| Current behavior | Demo platform exists; WhatsApp provider identity/callback is not activated by this package. |
| Required behavior | Runbook steps 1-22 for Demo using number `9822753575` as protected config input. |
| In scope | Separate app/WABA/IDs/secrets/host/data/media/dedup/telemetry/templates/backup/deployment authority; teardown. |
| Out of scope | UAT/Production resources, hard-coded number, customer traffic, unauthorized provider/cloud mutation. |
| Reuse | Existing Demo deploy/verify/cleanup patterns and environment rendering. |
| API/events | Exact candidate contract/config versions; no Demo-specific API fork. |
| Data/RLS | Demo namespaces/keys/backups only; cleanup respects attempts/horizons/holds. |
| Migration/compatibility | Provision from environment-neutral artifacts; never import another environment; teardown preserves required tombstones/evidence and leaves reusable code unchanged. |
| Config/secrets | Complete Section 11 isolation; separate runtime/scanner/configurator. |
| Authority/security | Each manual/platform action needs exact authority; callback disabled before deletion. |
| Privacy/retention | Dispose payload/derivatives; retain only required tombstone/evidence; provider copies tracked. |
| Failure/retry/idempotency/dedup/replay | Teardown blocked until retry/replay work is terminal or isolated non-routable; dedup/tombstones persist through the required horizon. |
| Observability | Demo-only namespace and alert route; prove UAT/Production unchanged. |
| Rollout/rollback | Activate only after smoke matrix; rollback disables callback/dispatch and restores prior non-routable state. |
| Targeted tests | Environment rendering, negative cross-env secrets/IDs/hosts/state, runbook smoke, teardown with pending/reconciled/hold cases. |
| Acceptance criteria | Demo smoke passes; teardown proves callback disabled, temporary authority revoked, data disposition complete/blocked honestly, and zero UAT/Production diff. |
| Evidence | Safe provider screenshots/receipts, config hashes, smoke report, teardown diff and revocation proof. |
| Dependencies | CSA-CEWA-009 through CSA-CEWA-017; separate Demo activation authority. |
| Definition of done | CE-FIT-12 and CE-FIT-16 Demo evidence passes. |

### CSA-CEWA-019 - UAT Stable Ingress And Activation

| Field | Specification |
|---|---|
| Bucket | S - UAT stable ingress and activation |
| Objective | Qualify durable UAT through stable Azure ingress and DNS/TLS hostname. |
| Value | Production-like provider qualification without Production risk. |
| Controlling references | ADR-053 Decision 1-5,11-14; enterprise §§13.1-13.4 |
| Affected components/directories | UAT config/IaC/workflow/runbook/evidence under separate authority. |
| Current behavior | UAT platform ingress exists; Meta callback identity is not authorized by this package. |
| Required behavior | Runbook for UAT using `8888912344` as protected config, hostname callback, separate ingress/egress analysis. |
| In scope | Stable inbound address, DNS/TLS, isolated provider/data/telemetry/template/recovery, smoke/rollback. |
| Out of scope | Raw-IP callback, assumed static egress, Demo identity reuse, Production activation. |
| Reuse | Existing UAT private runner/deploy/verify and recovery patterns. |
| API/events | Same candidate versions as Demo; environment identity differs. |
| Data/RLS | UAT durable namespaces/backups/restore qualification. |
| Migration/compatibility | Promote immutable artifacts and recreate UAT-specific configuration only; never copy Demo identity/data/dedup; preserve rollback to dark UAT. |
| Config/secrets | UAT-only Key Vault and workload identities; egress only if authorized dependency requires it. |
| Authority/security | Separate UAT provider/DNS/deploy authority and negative cross-env proof. |
| Privacy/retention | UAT retention/hold/erasure classes and test-data policy. |
| Failure/retry/idempotency/dedup/replay | Same production-grade retry/dedup/replay state machines; callback migration retains UAT identity and durable outcomes. |
| Observability | UAT namespace/alerts/SLO evidence. |
| Rollout/rollback | Dark deploy -> smoke -> explicit activation; rollback callback/dispatch while retaining state. |
| Targeted tests | DNS/TLS/hostname, stable ingress, no raw IP, egress independence, cross-env negatives, restore/non-routable reactivation. |
| Acceptance criteria | Meta callback uses valid HTTPS hostname; stable ingress proof exists; no statement/evidence assumes static outbound egress; all UAT identities are unique. |
| Evidence | DNS/TLS/ingress records, smoke/recovery/rollback reports, cross-env inventory diff. |
| Dependencies | CSA-CEWA-018 lessons closed; separate UAT authority. |
| Definition of done | UAT CE-FIT-12 evidence and activation rollback rehearsal pass. |

### CSA-CEWA-020 - Production Readiness And Dark Activation Gates

| Field | Specification |
|---|---|
| Bucket | T - Production-readiness gates |
| Objective | Prove Production can be activated safely while keeping it dark pending Founder decisions. |
| Value | Prevents accidental customer traffic and uncontrolled risk/cost. |
| Controlling references | ADR-053 Decision 1-3,11-14; enterprise §§13, 24 |
| Affected components/directories | Production configuration templates, protected environments, runbook/evidence only until separately authorized. |
| Current behavior | Production WhatsApp number is unpurchased and activation unauthorized. |
| Required behavior | Complete readiness ledger for separate number (preferred suffix `926629`), identity, secrets, data, templates, ingress, recovery, monitoring, rollback. |
| In scope | Dark rendering/plan, exact decision gates, Production-dark negative proof. |
| Out of scope | Purchase, registration, DNS/provider/cloud mutation, deployment, traffic, activation. |
| Reuse | UAT-qualified immutable candidate and controlled environment rendering; never UAT credentials/data. |
| API/events | Exact qualified versions; no Production fork. |
| Data/RLS | Isolated Production scope, keys, backups, retention, RPO/RTO acceptance. |
| Migration/compatibility | Render the exact UAT-qualified artifact into new Production authority/data boundaries; no state copy; retain dark rollback before any traffic. |
| Config/secrets | Placeholder references only until created under authority; no values in repo. |
| Authority/security | Founder owns number purchase, risk/cost, DNS/provider/deploy/traffic/activation decisions. |
| Privacy/retention | Legal/Data acceptance of Production classes and provider obligations. |
| Failure/retry/idempotency/dedup/replay | Production recovery, idempotency/dedup restoration, callback/dispatch rollback, and replay denial are rehearsed without traffic. |
| Observability | Production namespace/alerts/on-call/access audit prepared dark. |
| Rollout/rollback | Dark default; multi-party evidence gate; callback/dispatch independent kill switches. |
| Targeted tests | Environment render without secrets, Production-dark, cross-env denial, protected environment authority, rollback simulation. |
| Acceptance criteria | Zero live callback/dispatch/customer traffic; every activation prerequisite has owner/evidence/status; missing item blocks. |
| Evidence | Readiness ledger, dark proof, Founder decision register. |
| Dependencies | CSA-CEWA-019, CSA-CEWA-023, CSA-CEWA-024, CSA-CEWA-026; separate Founder decisions. |
| Definition of done | Readiness may be PASS while activation remains BLOCKED. |

### CSA-CEWA-021 - Web Regression And Shared-API Adoption

| Field | Specification |
|---|---|
| Bucket | U - Web regression and shared-API adoption |
| Objective | Move Web to the same generated shared contract without semantic or UX regression. |
| Value | Proves the API is truly channel-neutral and preserves current customers. |
| Controlling references | EA-CE-01/02/07; ADR-052; enterprise §§4, 11, 17 |
| Affected components/directories | Web generated client, conversation/workspace UI, BP compatibility adapter, web/API tests. |
| Current behavior | Web uses delivered Conversation Core/workspace contracts. |
| Required behavior | Same canonical history/context/policy/conclusion/states through generated candidate client. |
| In scope | Generated client adoption, cursor/state rendering, registered context hints, regression. |
| Out of scope | Screen prompts as policy, Web-only history/profile, UI redesign unrelated to contract. |
| Reuse | Existing Web conversation/workspace components and client-generation pipeline. |
| API/events | Candidate BP API; SSE/polling canonical cursor. |
| Data/RLS | No direct storage access; BP authorization only. |
| Migration/compatibility | Generate the additive client, support old/new API during a feature-flag window, migrate views incrementally, and retain the current client for rollback. |
| Config/secrets | API version feature flag; no provider secrets. |
| Authority/security | Web cannot send tenant/policy/prompt/authority; Tier 4 portal flow remains authoritative. |
| Privacy/retention | Existing privacy and accessibility behavior preserved. |
| Failure/retry/idempotency/dedup/replay | Reconcile ambiguous mutations using original idempotency; deduplicate event replay by canonical sequence; render independent states honestly. |
| Observability | Safe client operation/error/version metrics. |
| Rollout/rollback | Per-environment/API-version flag; retain current client during compatibility window. |
| Targeted tests | Generated client compile, current Web regression, cross-channel timeline, stale context, state dimensions, accessibility. |
| Acceptance criteria | Existing focused Web suite passes; Web->WhatsApp->Web fixture preserves IDs/sequence/meaning; no Web-only canonical branch remains. |
| Evidence | Regression report, generated-client diff, CE-FIT-01/04 journey. |
| Dependencies | CSA-CEWA-002 through CSA-CEWA-007. |
| Definition of done | Web consumes shared API with preserved behavior. |

### CSA-CEWA-022 - Future Mobile Compatibility Contract

| Field | Specification |
|---|---|
| Bucket | V - Future Mobile compatibility contract |
| Objective | Prove a second generated client can use public semantics without server/channel changes. |
| Value | Avoids future Mobile reimplementation and provider leakage. |
| Controlling references | ADR-052 consequences; enterprise §§2.2, 11, 17 CE-FIT-15 |
| Affected components/directories | Candidate OpenAPI, generated-client compatibility fixture/tests only. |
| Current behavior | Mobile implementation/framework is deferred under ADR-032. |
| Required behavior | Generate and exercise a second language/client contract against fixtures. |
| In scope | Contract generation, auth/context/command/timeline/state semantic conformance. |
| Out of scope | Mobile app/framework, push notifications, Mobile deployment. |
| Reuse | Same BP OpenAPI and fixture server used by Web contract tests. |
| API/events | No Mobile-specific endpoints/fields. |
| Data/RLS | No direct data access; same BP identity/tenant/relationship controls. |
| Migration/compatibility | Contract-only additive proof; no runtime migration. Future clients must honor the published compatibility and deprecation window. |
| Config/secrets | None beyond generated-client test config. |
| Authority/security | Client cannot inject tenant/policy/prompt/authority. |
| Privacy/retention | No new storage or telemetry. |
| Failure/retry/idempotency/dedup/replay | Generated client exposes idempotency/reconcile/dedup-safe cursor/error behavior equivalently. |
| Observability | Contract test only. |
| Rollout/rollback | Not applicable; no Mobile runtime. |
| Targeted tests | Generate second client, compile, run timeline/contribution/command/context/state fixtures and forbidden-field tests. |
| Acceptance criteria | Client generation requires zero server semantic change and passes all shared fixtures. |
| Evidence | Generator command/checksum/compile/test results. |
| Dependencies | CSA-CEWA-002. |
| Definition of done | CE-FIT-15 passes without implementing Mobile. |

### CSA-CEWA-023 - Data Migration, Backup, Restore, And Rollback

| Field | Specification |
|---|---|
| Bucket | W - Data migrations, backup, restore, recovery and rollback |
| Objective | Safely evolve and recover all conversation/adapter data at one consistency point. |
| Value | Prevents data loss, replay, tenant leakage, and irreversible cutover. |
| Controlling references | ADR-052/053 reversibility; enterprise §§15.8-15.10, 20; R-147 DA-H7/M1/M2 |
| Affected components/directories | Database migrations, backfill tools, backup/restore runbooks, recovery tests. |
| Current behavior | Existing environment continuity and PostgreSQL recovery patterns exist. |
| Required behavior | Section 6.5 evolution and Section 13 isolated restore/qualification. |
| In scope | Schema watermark, provenance, consistency group, mixed versions, PITR/restore, no-provider recovery. |
| Out of scope | Destructive down migration, cross-environment remap, restore with provider authority. |
| Reuse | Existing migration runners, PostgreSQL backup/PITR, environment readiness evidence. |
| API/events | Prior and candidate readers coexist; incompatible majors dead-letter safely. |
| Data/RLS | Validate RLS/roles/composite refs/sequences/dedup/outbox/lineage/payload/projection. |
| Migration/compatibility | Normative expand -> migrate -> cutover -> compatibility window -> contract flow; destructive down-migration is prohibited. |
| Config/secrets | Environment-specific encryption/backup authority; temporary restore identity. |
| Authority/security | Restore is isolated/non-routable; UAT/Production reactivation Founder-gated. |
| Privacy/retention | Backup age-out/crypto-erasure and hold behavior verified. |
| Failure/retry/idempotency/dedup/replay | Backfill/rebuild rerunnable and deduplicated; restore at shared consistency watermark; retry/replay reconciles original outcomes after recovery. |
| Observability | Migration/rebuild/restore progress and invariant violations with safe counts. |
| Rollout/rollback | Expand/migrate/cutover/compatibility/contract; rollback prior readers without deleting new data. |
| Targeted tests | Empty/current/partial/repeated migration, mixed versions, rollback, isolated restore, RLS, dedup replay, outbox, erasure/hold/backups, cross-env import denial. |
| Acceptance criteria | Repeated migration converges; rollback preserves new records; restore produces matching invariant/checksum set and cannot contact Meta. |
| Evidence | Migration logs, rollback report, isolated restore qualification, RPO/RTO measurement. |
| Dependencies | CSA-CEWA-003, CSA-CEWA-006, CSA-CEWA-010, CSA-CEWA-014, CSA-CEWA-015. |
| Definition of done | Data/recovery gates pass before final acceptance or environment activation. |

### CSA-CEWA-024 - End-To-End Acceptance And CE-FIT Qualification

| Field | Specification |
|---|---|
| Bucket | X - End-to-end acceptance |
| Objective | Execute the complete CE-FIT-01 through CE-FIT-16 acceptance portfolio on one candidate. |
| Value | Proves architecture behavior across components before container qualification. |
| Controlling references | Enterprise §17; ADR-052/053 fitness sections |
| Affected components/directories | Cross-component contract/integration/journey suites and evidence output. |
| Current behavior | Existing suites prove delivered foundations, not the complete new candidate. |
| Required behavior | All 16 fitness obligations run against exact schema/config/artifact versions. |
| In scope | Positive/negative/concurrency/outage/replay/privacy/isolation/teardown/second-client journeys. |
| Out of scope | Docker qualification before targeted suites pass; live Production. |
| Reuse | Existing contract, integration, browser, recovery, security, data, and environment test runners. |
| API/events | Verify exact candidate OpenAPI/events and backward compatibility. |
| Data/RLS | Include cross-tenant/relationship/environment and restore/migration cases. |
| Migration/compatibility | Qualify fresh, upgraded, mixed-version, rollback, and post-restore candidates before the compatibility window can close. |
| Config/secrets | Injected fixtures/suffixes; no real secrets/numbers in test artifacts. |
| Authority/security | Exact assurance, Stop, HMAC, credential, and environment negative matrix. |
| Privacy/retention | Leakage, erasure, hold, lineage, provider obligation cases. |
| Failure/retry/idempotency/dedup/replay | Fault injection at every durable boundary, idempotency/dedup namespace, retry class, and replay horizon. |
| Observability | Evidence links every test to CE-FIT/story/requirement and exact candidate. |
| Rollout/rollback | Include feature disable and prior-version compatibility journeys. |
| Targeted tests | Run all per-story commands, then the combined non-Docker CE-FIT orchestrator. |
| Acceptance criteria | CE-FIT-01 through CE-FIT-16 all PASS with no unassigned check, skipped predicate, or unbound evidence. |
| Evidence | Fitness ledger, exact commands/results, immutable candidate/config digests. |
| Dependencies | CSA-CEWA-002 through CSA-CEWA-023. |
| Definition of done | Non-Docker implementation acceptance is complete and author review may begin. |

### CSA-CEWA-025 - Final Docker And Containerized End-To-End Validation

| Field | Specification |
|---|---|
| Bucket | X - Final Docker validation |
| Objective | Qualify the complete internally coherent candidate once using repository-prescribed containers. |
| Value | Proves packaging, migrations, networking, identities, and full journeys without wasteful per-story rebuilds. |
| Controlling references | Founder testing direction; ADR-050; repository Docker validation rules |
| Affected components/directories | Existing Docker/Compose/image-scan/end-to-end runners and evidence. |
| Current behavior | Repository has Docker-only final qualification patterns. |
| Required behavior | Run only after all stories, targeted tests, migration/rollback, and implementation author review pass. |
| In scope | Build, Compose, migrations, health/readiness, contract/journey/security scans, image/SBOM as prescribed. |
| Out of scope | Docker after each story; substituting Docker for unit/contract/integration tests. |
| Reuse | Existing impact-selected ADR-050 runners and immutable candidate evidence. |
| API/events | Same exact candidate artifacts as targeted qualification. |
| Data/RLS | Start/migrate/restart/restore paths included where repository runner prescribes. |
| Migration/compatibility | Container qualification exercises fresh install, upgrade/rollback compatibility, and migration watermark consistency on the complete candidate. |
| Config/secrets | Test fixtures only; no live provider/cloud/Production authority. |
| Authority/security | Container least privilege and secret/privacy scans. |
| Privacy/retention | Test cleanup and evidence minimization. |
| Failure/retry/idempotency/dedup/replay | Full-stack retry, duplicate, dedup conflict, delayed replay, outage, and Stop cases. |
| Observability | Container logs/traces scanned and retained with exact digest. |
| Rollout/rollback | Qualification includes feature disable/rollback smoke. |
| Targeted tests | Prerequisite: all story commands. Final: exact repository-prescribed Docker/Compose/E2E commands selected by impact analysis. |
| Acceptance criteria | One exact candidate passes all prescribed container gates. If defects occur, fix, rerun affected targeted tests, then rerun final Docker validation. |
| Evidence | Image/compose/config digests, commands/results, scans, cleanup proof. |
| Dependencies | CSA-CEWA-024 and implementation author review PASS. |
| Definition of done | Final container qualification PASS on the exact submitted candidate. |

### CSA-CEWA-026 - Operational Handoff And Runbooks

| Field | Specification |
|---|---|
| Bucket | Y - Operational handoff and runbooks |
| Objective | Give operators executable activation, incident, rotation, recovery, teardown, and rollback procedures. |
| Value | Safe operation without tribal knowledge or architecture invention. |
| Controlling references | Enterprise §§13, 16, 18, 20, 22; this §§11-16 |
| Affected components/directories | Existing operations/runbook location, dashboards/alerts, access/decision records. |
| Current behavior | General platform runbooks exist; WhatsApp-specific procedures are not active. |
| Required behavior | Convert Section 16 into verified per-environment commands/UI steps with authorities and evidence. |
| In scope | Activation/deactivation, secret rotation/revocation, incident, replay/dead letter, media, Stop, backup/restore, teardown, promotion, rollback. |
| Out of scope | Embedding secrets/IDs, automatic Founder decisions, cross-environment shortcuts. |
| Reuse | Existing deploy/verify/cleanup/recovery/on-call patterns. |
| API/events | Operator reconciliation uses supported APIs/events, never direct state edits. |
| Data/RLS | Break-glass access is environment-scoped, audited, least privilege, and tested. |
| Migration/compatibility | Runbooks cover expand/migrate/cutover/rollback/contract, mixed versions, backup compatibility, and safe retirement of prior procedures. |
| Config/secrets | Named refs and rotation procedures; values remain Key Vault/provider only. |
| Authority/security | Runtime/deployment/scanner/operator/Founder duties separated. |
| Privacy/retention | Incident/evidence collection follows protected diagnostic and lifecycle policy. |
| Failure/retry/idempotency/dedup/replay | Procedures reconcile before retry, preserve idempotency/dedup/tombstones, and replay only through supported commands. |
| Observability | Every alert maps to diagnosis, safe evidence, action, escalation, and closure predicate. |
| Rollout/rollback | Environment-specific activation and rollback checklists, Production dark default. |
| Targeted tests | Tabletop and executable rehearsal for callback loss, secret revoke, provider outage, backlog, scanner failure, CE outage Stop, restore, Demo teardown. |
| Acceptance criteria | Every alert/failure has owner, bounded action, rollback, and evidence; rehearsals complete without cross-environment or direct data mutation. |
| Evidence | Signed runbook rehearsal and access/alert mapping. |
| Dependencies | CSA-CEWA-017 through CSA-CEWA-025. |
| Definition of done | Platform Operations can execute authorized procedures without design choices. |

### CSA-CEWA-027 - Founder Handoff And Implementation Authorization Gate

| Field | Specification |
|---|---|
| Bucket | Y - Operational and institutional handoff |
| Objective | Bind the accepted package, open decisions, exact candidate, and separate implementation authority. |
| Value | Ensures readiness evidence is not mistaken for ADR acceptance, activation, or implementation authority. |
| Controlling references | BOOTSTRAP implementation gate; ADR-052/053 boundaries; enterprise §24 |
| Affected components/directories | Work Contract/PR/evidence records only; no runtime file. |
| Current behavior | This candidate is draft and ADRs are proposed. |
| Required behavior | Founder decisions are explicit; Platform IT Expert receives a bounded separate Work Contract after acceptance. |
| In scope | Decision ledger, accepted versions, exact scope/stops, required inputs, implementation/activation separation. |
| Out of scope | Self-approval, self-merge, implicit acceptance from PR merge, provider/cloud action. |
| Reuse | Repository PR template, prepare-pr precheck, Work Contract conventions. |
| API/events | Bind exact candidate versions; no runtime change. |
| Data/RLS | Bind migration/recovery acceptance and unresolved owner values. |
| Migration/compatibility | Founder handoff binds the accepted compatibility window, migration/rollback evidence, and conditions for later contract/removal. |
| Config/secrets | Bind configuration ownership without values. |
| Authority/security | Founder accepts ADRs/risks and separately authorizes implementation/activation decisions. |
| Privacy/retention | Confirm Data/Legal lifecycle decisions. |
| Failure/retry/idempotency/dedup/replay | Unresolved decision keeps affected stories BLOCKED; handoff resubmission is idempotent and cannot imply acceptance. |
| Observability | Decision/evidence references only. |
| Rollout/rollback | Work Contract states feature, migration, environment, activation and rollback limits. |
| Targeted tests | PR/document precheck and traceability completeness. |
| Acceptance criteria | No proposed ADR or readiness result is represented as implementation/activation authority; all open decisions have owner/status/blocking effect. |
| Evidence | Founder decision record and separate Work Contract, if authorized. |
| Dependencies | Solution package author review and Founder review. |
| Definition of done | Platform IT Expert may start only after explicit current-session implementation authorization. |

## 18. Dependency And Parallelization Table

| Story | Depends on | May run in parallel after dependencies |
|---|---|---|
| 001 Discovery | ADR/authority gate | None; controls all implementation |
| 002 Shared API | 001 | 008 identity analysis, 017 telemetry utility design |
| 003 Canonical data | 002 | 005 policy design after 004 contract is stable |
| 004 Context resolver | 002, 003 | 006 lineage, 007 continuity |
| 005 Policy/rendering | 004 | 006, 007 |
| 006 Profile/summary | 003, 004 | 007, 008 |
| 007 Continuity | 002, 003, 004 | 005, 006, 008 |
| 008 Identity/assurance | 001, 003 | 004-007 |
| 009 Signed ingress | 008 + environment config | 012 outbound design |
| 010 Durable claim | 003, 009 | 012 outbound implementation |
| 011 Normalization | 010 | 012-014 |
| 012 Outbound | 002, 003, 008 | 009-011 |
| 013 Eligibility | 010, 012 | 014, 015 |
| 014 Delivery projection | 010, 012 | 013, 015, 016 |
| 015 Media | 006, 008, 011 | 013, 014, 016 |
| 016 Stop | 008, 010, ADR-031 | 013-015 |
| 017 Telemetry | 001; integrates with each story | Shared utilities early; final leakage proof after 016 |
| 018 Demo | 009-017 + authority | None for provider activation |
| 019 UAT | 018 lessons + authority | Web/Mobile regression if same candidate |
| 020 Production readiness | 019, 023, 024, 026 | Dark planning only |
| 021 Web adoption | 002-007 | 009-020 |
| 022 Mobile contract | 002 | 003-021 |
| 023 Migration/recovery | 003, 006, 010, 014, 015 | 021, 022 |
| 024 CE-FIT acceptance | 002-023 | None; complete candidate |
| 025 Final Docker | 024 + implementation author review | None |
| 026 Operational handoff | 017-025 | Production readiness evidence assembly |
| 027 Founder handoff | Solution author review | No implementation |

Dependency order is normative. “Parallel” never permits a consumer to code against an unstable
contract; contract candidate and compatibility tests must be frozen first.

## 19. Targeted Testing Strategy

### 19.1 Per-Story Rule

For each story, the Platform IT Expert records and runs the smallest repository-native commands that
cover the changed surface:

- .NET: filtered Business Platform/Constitutional Engine unit and integration tests;
- Python: exact Professional Runtime/AI Runtime test modules or node IDs;
- Web: exact Jest/Playwright projects or test names plus type/lint checks;
- contracts: OpenAPI lint/slice, generated-client build, and producer/consumer fixtures;
- data: migration up/repeat/rollback-compatibility, RLS, backfill, restore, and invariant queries;
- security: HMAC, assurance, secret authority, media, Stop, environment, and telemetry leakage tests;
- static: formatter, linter, type checker, and dependency/spec trace gates for changed components.

No story is complete because a broader suite happened to pass; its exact predicates and evidence must
pass. Conversely, Docker is not a substitute for these targeted checks.

### 19.2 Required Behavioral Portfolio

| Portfolio | Stories | Required predicates |
|---|---|---|
| Canonical continuity | 002-007, 021-022 | One conversation/sequence, deterministic context/policy, semantic equivalence |
| Identity/authority | 008, 013, 016 | Deny zero/ambiguous/revoked/reassigned/stale/mismatch with zero mutation; exact-intent tiers; portal-only Tier 4 |
| Ingress/replay | 009-011 | Raw HMAC before parse, inclusive five minutes, atomic claim, delayed accepted retry |
| Outbound/delivery | 012-014 | Separate idempotency domains; queue/send eligibility; immutable observations; independent state dimensions |
| Media/privacy | 015, 017 | Isolated retrieval/scan, lineage/erasure, zero telemetry leakage |
| Stop/resilience | 016, 023 | Immediate model-free halt, CE outage durability, restore consistency |
| Environments | 018-020 | Exact isolation, Demo teardown, UAT hostname/stable ingress, Production dark |

### 19.3 Final Docker Rule

Docker builds, Compose suites, image scans, and full containerized end-to-end checks run once only
after:

1. all implementation stories are complete;
2. every targeted test and static check passes;
3. migrations, restore, and rollback pass;
4. the branch is internally coherent; and
5. implementation author review passes.

If final Docker qualification finds a defect, fix it, rerun only affected targeted tests, then rerun
the complete final Docker qualification on the new exact candidate.

## 20. Bidirectional Traceability Matrix

### 20.1 Architecture To Story To Fitness

| Enterprise requirement | ADR decision | Story | Affected component | Test/evidence | CE-FIT |
|---|---|---|---|---|---|
| EA-CE-01 one relationship conversation | ADR-052 D1 | 002, 003, 007, 021 | BP, Web, channel binding | Web->WA->Web IDs/sequence/authority | 01 |
| EA-CE-03 server-resolved context | ADR-052 D3-4, D9 | 004, 008 | BP Context/Identity | forged key, cross-subject, stale source, zero mutation | 02, 03 |
| EA-CE-04 versioned layered policy | ADR-052 D5, D8 | 005 | BP, PR, AIR, renderers | precedence, injection, semantic corpus | 04, 05, 06 |
| EA-CE-05 canonical versus working context | ADR-052 D7, D11-12 | 003, 006 | BP, AIR, payload store | lineage, invalidation, rebuild, no summary-as-fact | 03, 05 |
| EA-CE-06 independent state dimensions | ADR-053 D7 | 012, 014 | BP adapter/projection | state transition and status permutation tests | 07 |
| Concurrent protected intent commits once | ADR-052 D12 | 003, 008 | BP command transaction | simultaneous Web/WA exact intent | 08 |
| Signed webhook and durable result | ADR-053 D5, D13 | 009, 010 | BP adapter/inbox/outbox | challenge/HMAC/body/freshness/claim/replay faults | 09 |
| Service window/template/consent | ADR-053 D8 | 013 | BP eligibility/outbound | boundary and revocation matrix | 10 |
| Safe media/voice reuse | ADR-053 D9-10, D14 | 015 | BP, scanner, AIR voice, payload store | unsafe formats/resources/malware/correction/erasure | 11 |
| Environment isolation | ADR-053 D1-4, D11-14 | 008-010, 012, 015, 018-020, 023 | Provider, BP, Key Vault, data, ingress | negative cross-env and restore/import tests | 12 |
| Stop before model, durable in CE outage | ADR-053 D15; ADR-031 | 016 | BP adapter, PR, CE | outage/duplicate/simultaneous/restart/release/latency | 13 |
| Privacy-safe operations | ADR-052 D11; ADR-053 D3/D9/D14 | 017 | All changed components | automated success/failure leakage scan | 14 |
| Future Mobile reuses public semantics | ADR-052 D10 and consequences | 002, 022 | BP API/generated client | second-client generation/conformance | 15 |
| Complete Demo teardown | ADR-053 D1-4, D11 | 018, 026 | Provider, Azure, data, operations | callback/authority/data/tombstone and zero UAT/Prod diff | 16 |

### 20.2 CE-FIT Reverse Coverage

| CE-FIT | Primary story/test owner | Required passing evidence |
|---|---|---|
| 01 | 003/007/021 | Cross-channel canonical journey |
| 02 | 004/008 | Forged/unknown/cross-subject zero-mutation matrix |
| 03 | 004/006 | Source change staleness before execution |
| 04 | 005/021 | Cross-channel semantic equivalence corpus |
| 05 | 005/006 | Known-current-fact repeat-question detector |
| 06 | 005 | Conclusion fields or typed continuation reason |
| 07 | 012/014 | Independent delivery/execution/decision/evidence transition tests |
| 08 | 003/008 | Concurrent exact-intent commit-at-most-once |
| 09 | 009/010 | Challenge, HMAC, raw body, size, freshness, claim, replay |
| 10 | 013 | Window/template/consent queue/send matrix |
| 11 | 015 | Media safety, resource, scan, transcript, correction, erasure |
| 12 | 008/018/019/020/023 | Credential/number/host/state/import cross-environment denial |
| 13 | 016 | CE outage, duplicate, simultaneous, restart, release denial, latency |
| 14 | 017 | Zero prohibited telemetry data |
| 15 | 022 | Second generated client without server semantic change |
| 16 | 018/026 | Demo disabled/revoked/disposed with UAT/Production unchanged |

No CE-FIT check is unassigned. Removing a story requires remapping and preserving its exact fitness
oracle; otherwise the package becomes defective and implementation stops.

## 21. Open Decisions, Blockers, Assumptions, And Founder Actions

| Item | Owner | Status/effect |
|---|---|---|
| Accept ADR-051 one-relationship workspace decision | Founder | BLOCKS ADR-052 unless accepted simultaneously |
| Accept ADR-052 | Founder | BLOCKS shared context/policy/history implementation |
| Accept ADR-053 | Founder | BLOCKS WhatsApp provider/environment implementation |
| Separate Platform IT Expert Work Contract/current-session authorization | Founder | BLOCKS every implementation-file change |
| Exact Meta environment-isolation model (dedicated apps/WABAs or proven equivalent) | Founder/Security/Platform | BLOCKS provider preparation |
| Production number purchase, exact E.164, provider registration | Founder | BLOCKS Production provider configuration |
| Approved domains/hostnames and DNS mutation | Founder/Platform | BLOCKS live callback |
| Media types, sizes, resource ceilings, rejected-payload retention | Product/Security/Data, Founder accepts material risk | BLOCKS media activation |
| Retention classes, legal-hold rules, erasure/provider obligations | Data/Legal, Founder accepts material rights/cost | BLOCKS affected data activation |
| UAT/Production RPO/RTO and backup cost | Data/Platform, Founder accepts | BLOCKS durable activation |
| Provider API version, event subscriptions, window boundary, retry horizon | Platform IT impact analysis against current official provider contract | BLOCKS exact configuration/tests if unresolved |
| Stable outbound egress requirement | External dependency owner/Platform | Not assumed; add only under authority |
| Production deployment, DNS/provider mutation, traffic, activation, risk/cost | Founder | Always separate protected decisions |

Assumptions: existing Conversation Core, omnichannel continuity, WC-062 voice, ADR-023 phone identity,
ADR-031 Stop, managed identity/Key Vault, RLS, outbox/Temporal, OTel, and Docker validation mechanisms
exist as described by the controlling architecture. Story 001 must verify them. A failed assumption
is a blocker, not permission to replace the architecture.

## 22. Platform IT Expert Handoff Checklist

- [ ] ADR-051/052/053 acceptance recorded as applicable.
- [ ] Separate implementation Work Contract and current-session implementation authorization exist.
- [ ] Complete impact analysis is `READY_FOR_STRATEGIC_PLAN`.
- [ ] Strategic plan groups shared versus WhatsApp work and records exact paths/commands.
- [ ] No new deployable, channel history/profile, environment fork, or client authority exists.
- [ ] API/event/data contracts and compatibility windows are frozen before consumers.
- [ ] Expand -> migrate -> contract, backup/restore, rollback, and feature gates are explicit.
- [ ] Every story's targeted unit/contract/integration/static/migration tests pass.
- [ ] CE-FIT-01 through CE-FIT-16 have exact evidence.
- [ ] Implementation author review passes before Docker.
- [ ] Final Docker/end-to-end qualification runs once on the complete exact candidate.
- [ ] Runbooks are rehearsed; Demo teardown and Production-dark proof pass.
- [ ] Provider/cloud/DNS/number/traffic/activation actions have separate authority.
- [ ] Exact secrets, provider identifiers, and telephone identities remain protected configuration.
- [ ] Founder receives exact candidate, evidence, blockers, rollback, and activation decisions.

## 23. Implementation-Readiness Result

**Contract completeness:** PASS for candidate solution decomposition. The package supplies boundaries,
contract families, data ownership/atomicity, identity/assurance, state machines, failure behavior,
environment isolation, migration/recovery, security/privacy, tests, evidence, dependency order,
runbook, rollout, rollback, and stops.

**Implementation authority/readiness:** BLOCKED. ADR-051/052/053 acceptance and a separate Platform IT
Expert implementation Work Contract/current-session authorization are absent. Provider, Azure, DNS,
number purchase, deployment, traffic, and activation remain separately blocked.

## 24. Chief Solution Architect Author Review Record

### 24.1 Review Lenses

| Lens | Result |
|---|---|
| Fidelity to PR #498 exact reviewed head | PASS |
| Consistency with ADR status and dependencies | PASS |
| CE-FIT-01 through CE-FIT-16 coverage | PASS |
| One shared capability; no duplicate engine/history/profile | PASS |
| API/event/data/identity/context/policy completeness | PASS |
| Environment/secret/authority isolation | PASS |
| Migration/recovery/rollback feasibility | PASS |
| Operator runbook and measurable story criteria | PASS |
| Targeted tests versus final Docker sequencing | PASS |
| Explicit blockers/Founder actions and no implementation code | PASS |

### 24.2 Findings And Corrections

| Finding | Correction | Result |
|---|---|---|
| AR-01: story tables combined rollout/rollback with migration and did not explicitly name backward compatibility or dedup/replay in every story | Added `Migration/compatibility` and `Failure/retry/idempotency/dedup/replay` to all 27 stories and strengthened story-specific predicates | RESOLVED |
| AR-02: overview called the merged enterprise package “accepted,” which could be read as ADR acceptance | Changed the wording to “merged”; retained the explicit proposed-ADR and blocked-handoff statements | RESOLVED |

The exact 40-character reviewed commit and final PASS result are bound in the prepared PR body after
the final push; any later commit invalidates that binding.

**Current result:** PASS for the draft solution package. Implementation handoff remains BLOCKED by
Section 21 and the Record Control blocking rule.
