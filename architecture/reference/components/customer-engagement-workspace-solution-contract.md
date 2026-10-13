# Customer Engagement Workspace Solution Contract

## 0. Record Control

| Field | Value |
|---|---|
| Solution ID | CSA-CEW-001 |
| Version | 1.0.0-candidate.6 |
| Status | AUTHOR REVIEW PASS - SPECIALIST-INTEGRATED CANDIDATE FOR FOUNDER REVIEW - IMPLEMENTATION BLOCKED |
| Office | Chief Solution Architect, Office 05 |
| Scope | Customer Portal and WhatsApp customer engagement experience |
| Enterprise input | `architecture/reference/components/customer-engagement-workspace-enterprise-requirements.md` |
| API input | `architecture/reference/api-specs/business-platform.openapi.yaml` |
| Conversation API input | `architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml` |
| Additive API candidate | `architecture/reference/api-specs/customer-engagement-workspace-business-platform.openapi.yaml` |
| Controlling implementation contract | `work-contracts/WC-121-customer-engagement-workspace-implementation.md` |

This contract specifies implementation behavior. It does not authorize source changes, generated
artifacts, provider or cloud mutation, deployment, external traffic, activation, PR approval, or
merge. Founder acceptance and each applicable protected-action gate remain separate.

## 1. Decision Space and Constitutional Obligations

### 1.1 Decision Space

The Chief Solution Architect may:

1. bind accepted Enterprise Architecture to solution components and owner boundaries;
2. reuse, tighten, or add Business Platform contracts without changing constitutional ownership;
3. specify customer journeys, state, errors, data, security, accessibility, operability, rollout,
   and evidence;
4. decompose the solution into dependency-ordered Work Components; and
5. produce one controlling implementation Work Contract.

The Chief Solution Architect may not implement source, select or mutate a live provider account,
deploy, send external traffic, activate a capability, approve a PR, merge, or treat candidate
architecture as accepted authority.

### 1.2 Non-negotiable obligations

1. One Employment Relationship has one agent instance, one durable conversation, and one
   engagement workspace.
2. Business Platform is the only public business facade for Portal and WhatsApp.
3. Portal and WhatsApp are presentations of shared owner state, not separate products.
4. Conversation is the primary authoring path; visual controls clarify and navigate owner truth.
5. Identity, employment, channel session, unlink, termination, and deletion are distinct domains.
6. Emergency Stop remains independent, persistent, accessible, and cross-channel effective.
7. Browser and channel clients never infer readiness, success, authority, or next-action order.
8. Unknown, stale, disputed, blocked, partial, and unavailable truth remains explicit.
9. The same immutable image and API contract promote through Demo, UAT, and Production.
10. Provider authority, deployment authority, traffic authority, and activation authority remain
    separate from functional completeness.

## 2. Accepted Source Precedence

Conflicts are resolved in this order:

1. Constitution and accepted Decision Space.
2. Accepted ADRs and owner contracts.
3. Enterprise requirements `CEW-ER-001` through `CEW-ER-046` and fitness obligations
   `CEW-FIT-01` through `CEW-FIT-26`.
4. Canonical Business Platform and channel-neutral API contracts.
5. This solution contract.
6. WC-121.
7. Implementation details and generated clients.

An implementer stops when a lower source cannot satisfy a higher source without changing owner,
authority, state meaning, or public compatibility.

## 3. Solution Decisions

| ID | Decision | Consequence |
|---|---|---|
| CEW-SD-001 | Customer Engagement Workspace is one product capability with Portal and WhatsApp presentations. | No channel-specific lifecycle or business state. |
| CEW-SD-002 | Existing BP `admitEmploymentRelationship` is tightened, not replaced. | One atomic, idempotent admission creates/replays `DISCOVERED`, agent instance, conversation, and workspace. |
| CEW-SD-003 | Existing BP relationship workspace remains the source aggregate. | One additive engagement-progress projection composes source-owner facts; it does not create a truth store. |
| CEW-SD-004 | Account layout extends identity settings; relationship default context extends Onboard preferences. | Layout cannot grant authority or mutate business state. |
| CEW-SD-005 | BP emits opaque, expiring focus references and reauthorizes them on every resolution. | Portal selection and WhatsApp continuation share focus without exposing authority-bearing IDs. |
| CEW-SD-006 | WhatsApp end-session is a bounded channel-session command. | It cannot log out web, unlink, terminate, or delete. |
| CEW-SD-007 | Web authentication remains identity-owned secure pages and redirects. | Credentials, consent payloads, and provider tokens never enter professional conversation. |
| CEW-SD-008 | WhatsApp registration is an institutional identity exchange outside the professional transcript. | Phone possession alone cannot attach a relationship or grant employment authority. |
| CEW-SD-009 | UI clients render server-projected next action and progress. | No client-side joins, ranking, lifecycle inference, or success inference. |
| CEW-SD-010 | Default-off gates evaluate capability authority/configuration, never environment name. | Demo carries complete routes, schemas, and components even when a protected action is blocked. |
| CEW-SD-011 | Live-provider qualification is independent of emulator qualification. | Emulator evidence cannot satisfy provider acceptance. |
| CEW-SD-012 | Requested WhatsApp sender and Demo-recipient identities remain protected configuration references. | No full number in repository, fixtures, URLs, logs, telemetry, screenshots, or evidence. |
| CEW-SD-013 | Every CEW edge is governed by the candidate-specific security envelope in Section 11. | No implementation may rely on identifier possession, a JWT tenant claim, browser state, provider identity, network location, or prior authorization as current authority. |
| CEW-SD-014 | CEW deploys only as capability slices of the existing Web, Business Platform, Conversation/adapter, and evidence-owning workloads in the accepted exact-seven release tuple. | No CEW image, public ingress, provider bridge, queue, database, or eighth first-party deployable is introduced. |
| CEW-SD-015 | Release, configuration, provider readiness, traffic, and feature activation are independent, evidence-bearing gates. | A healthy deployment or configured credential cannot imply provider acceptance, customer traffic, or activation. |

## 4. Reuse, Tighten, and Add Matrix

| Capability | Decision | Canonical surface or owner |
|---|---|---|
| Registration, login, fresh assurance, account switch, web logout | Reuse | Identity Boundary and existing BP identity operations |
| Account layout | Add bounded subresource; merge into canonical identity settings | `GET/PUT /api/v1/identity/settings/workspace-layout` |
| Anonymous marketplace discovery | Reuse | `GET /api/v1/professionals/marketplace` and disclosure operations |
| Relationship admission | Tighten existing operation | `POST /api/v1/employment/relationships` |
| Trial | Reuse | `POST /api/v1/employment/relationships/{relationshipId}/trial` |
| Hire/contract/payment | Reuse | Existing relationship contract, acceptance, billing, and payment operations |
| Onboard preferences | Tighten existing Onboard model; candidate exposes bounded subresource | `GET/PUT .../workspace/preferences` |
| Induction/configuration | Reuse | Existing relationship configuration/Onboard operations |
| Goals, plans, schedules, budgets, outcomes | Reuse | Existing BP relationship goals, outcomes, operations, workspace, and billing projections |
| Canonical conversation, contributions, typed commands, receipts | Reuse | Channel-neutral conversation API |
| Adaptive progress | Add smallest BP projection | `GET .../workspace/engagement-progress` |
| Visual/message focus | Add resolver over typed opaque references | `POST .../workspace/focus-resolutions` |
| Cross-channel handoff | Reuse | Existing prepare, activate, and revert handoff operations |
| WhatsApp end-session | Add bounded command | `POST .../channel-sessions/{channelSessionId}/end` |
| Stop | Reuse independent Stop path | Canonical relationship Stop owner |
| Provider webhook | Reuse | Channel-neutral WhatsApp callback |

No new deployable, lifecycle owner, identity store, conversation store, progress truth store, or
provider-specific business API is authorized.

## 5. Component and Ownership Model

| Component | Owns | Must not own |
|---|---|---|
| Portal Shell | Responsive regions, routing, accessible focus, presentation preference controls | Business truth, lifecycle transition, readiness, authority |
| WhatsApp Adapter | Protocol verification, normalization, provider message correlation, channel rendering | Employment decisions, identity proof policy, canonical history |
| BP Customer Engagement Facade | Admission orchestration, workspace projection, focus resolution, preference facade, channel-session command | PR execution, provider credentials, identity-provider secrets |
| BP Conversation Core | Canonical transcript, sequence, typed command/result, handoff state | Customer account authentication or provider delivery truth |
| Identity Boundary | Account, participant proof, assurance, linking, switch, logout, unlink | Employment relationship or professional transcript |
| Employment Owners | Relationship lifecycle, trial, contract, goals, operations, outcomes, commercial truth | Portal layout or provider protocol |
| Professional Runtime | Governed professional execution and owner results | Customer-facing public API or channel-specific history |
| Constitutional Engine | Decision Space validation, Stop policy, evidence commitment | Presentation layout |
| Evidence/Telemetry | Correlation, audit/evidence references, redaction controls | Raw credentials, protected telephone identity, message content by default |

### 5.1 Public call rule

Portal calls BP through generated clients plus approved identity handoffs and the independent Stop
path. WhatsApp provider traffic terminates at the approved adapter, which calls the same BP public
semantics. Neither presentation calls PR, AIR, WBE, CE, another adapter, or provider business APIs
directly.

## 6. Portal Experience Contract

### 6.1 Expanded composition

The expanded workspace contains:

1. **Context region** - relationship switcher, lifecycle navigation, marketplace access, account
   and help.
2. **Conversation region** - continuous transcript, composer, attachments/voice where accepted,
   typed confirmations, operation status, reconciliation, and Stop.
3. **Progress/context region** - adaptive owner-projected progress, evidence freshness, selected
   object detail, next action, cost/limits, and correction routes.

Customers may hide, display, collapse, or resize eligible context and progress regions. The
conversation remains primary. Stop, identity state, current lifecycle, required customer action,
and error/recovery status remain reachable in every composition.

### 6.2 Compact composition

At narrow widths the conversation remains the primary page. Context and progress become
keyboard- and screen-reader-accessible routes or sheets, preserve focus, and return to the exact
conversation position. Compact mode exposes no reduced lifecycle or command set.

### 6.3 Preference scopes

| Preference | Owner | Persistence | Authority effect |
|---|---|---|---|
| Navigation/progress visibility and conversation width | Identity settings | Cross-device account | None |
| Default relationship focus and focus-open behavior | Relationship Onboard | Per relationship | None |
| Current selected focus and temporary drag width | Client session | Ephemeral | None |
| Current progress, eligibility, next action | BP projection/source owners | Server truth | Authoritative projection |

Unsafe, inaccessible, stale, or expired focus is discarded and replaced by the server-projected
safe default. A preference can never reopen a relationship or object the participant cannot access.

### 6.4 Customer language

All visible copy uses customer-domain language. Raw service names, API paths, schema names, enum
values, prompt text, provider codes, and workflow implementation terms are mapped to the common
WAOOAW vocabulary. Every consequential turn has one primary action and exposes effect, authority,
cost where applicable, limitation, confirmation, cancellation, and safe recovery.

## 7. WhatsApp Experience Contract

WhatsApp renders the same professional identity, lifecycle meaning, evidence language, status
meaning, and next action as Portal. It uses short conversational turns, numbered or interactive
choices where supported, explicit confirmation, `Back`, `Help`, `Status`, and independent `Stop`.

Channel adaptation preserves the Portal's information hierarchy rather than imitating browser
chrome:

| Portal visual element | WhatsApp presentation | Parity rule |
|---|---|---|
| Professional header | Verified professional name and WAOOAW identity at session start and material context change | Same professional/relationship identity |
| Lifecycle navigation | Short stage label plus `Status`/`Menu` choices | Same server-projected current stage and available destinations |
| Conversation timeline | Canonically ordered message turns and delivery/processing updates | Same message, command, and conclusion identities |
| Adaptive progress pane | Compact progress summary with needs-attention first and `View` choices | Same item state, owner, evidence freshness, and server-ranked action |
| Detail card | Message section with explicit state, effect, limit, and secure continuation when required | Same governed object and focus reference |
| Primary action | One quick reply, interactive control, or numbered choice; text fallback when unsupported | Same typed command and confirmation |
| Adverse status | Text label plus channel-supported icon; never icon or color alone | Same unknown/stale/blocked/failed/unavailable meaning |
| Stop control | Persistent `Stop` command/help affordance | Same independent cross-channel effect |

Brand color, spacing, typography, and card treatment apply where WhatsApp templates/components
support them. Where the provider controls rendering, terminology, order, identity, status meaning,
accessible text, and action semantics are the binding equivalence. Unsupported rich controls fall
back to text without reducing capability or authority checks.

When a secure or visually dense Portal interaction is necessary, BP issues a single-purpose,
expiring, relationship-bound continuation. After authentication and action, the customer returns
to the same relationship, conversation, message/command, and focus. The durable transcript records
the governed professional result, not credentials, provider tokens, institutional registration
payloads, or unconfirmed registration data.

WhatsApp `End session`:

1. ends only the current WhatsApp channel session;
2. confirms the durable relationship and conversation remain available;
3. does not log out Portal, unlink the number, switch accounts, terminate employment, or delete
   data; and
4. requires a distinct, idempotent BP command and evidence.

## 8. Journey and Operation Trace

| Journey | Required sequence | Primary operations |
|---|---|---|
| Anonymous discovery | Need conversation -> marketplace facts -> professional disclosure -> explicit Trial/Hire intent | Marketplace/disclosure reads only |
| Registration continuation | Preserve non-secret intent -> identity-owned registration -> safe return -> explicit admission | Identity operations, then admission |
| Login continuation | Preserve safe return -> identity page -> assurance -> exact safe context | Identity operations; no relationship write |
| Trial admission | Exact disclosure + Trial -> admission -> one `DISCOVERED` relationship -> trial command | `admitEmploymentRelationship`, `startEmploymentRelationshipTrial` |
| Hire admission | Exact disclosure + Hire -> admission -> induction/contract conversation | Admission, configuration, contract operations |
| Induction | Known/missing/owner/reason/block/evidence/next question -> confirm -> owner write | Workspace/configuration operations |
| Skills and goals | Conversational proposal -> visual compare -> explicit confirm -> versioned owner write | Goals/plan operations |
| Operations | Start/schedule/work -> separate delivery/processing/evidence/commercial/outcome truth | Operations/workspace projections |
| Performance | Outcome first -> supporting technical evidence -> correction/next goal | Outcome/performance reads and commands |
| Pane focus | Select card/object -> resolve opaque focus -> progress region updates -> conversation preserved | Progress and focus operations |
| Portal to WhatsApp | Prepare -> target auth/assurance -> activate -> same conversation/context | Handoff operations |
| WhatsApp to Portal | Single-purpose link -> Portal auth -> activate -> exact focus | Handoff and focus operations |
| Retry/reconcile | Timeout/unknown -> operation status -> original outcome or safe retry | Operation reconciliation |
| Web logout | Identity-owned logout -> clear secrets/session -> retain policy-approved layout | Identity operation only |
| WhatsApp end-session | Confirm -> end channel session -> retain relationship/conversation | Channel-session end |
| Unlink/switch/terminate/delete | Separate wording, assurance, owner command, evidence, and effects | Respective identity/employment/data-rights operations |

## 9. State and Failure Semantics

### 9.1 Lifecycle stages

BP projects these presentation stages from owner state:

`DISCOVERED -> TRIAL_OR_HIRE -> INDUCTION -> SKILLS_AND_GOALS -> OPERATIONS -> PERFORMANCE`

`PAUSED_RENEWAL_OR_EXIT` is a projected branch, not a new employment state. The client never
advances a stage locally.

### 9.2 Truth dimensions

Delivery, processing, evidence, commercial, and outcome are independent. `SENT` does not mean
`ACCEPTED`; `ACCEPTED` does not mean `PROCESSING`; `PROCESSING` does not mean evidence committed;
evidence committed does not imply payment settled or business outcome achieved.

### 9.3 Failure table

| Condition | Customer presentation | Mutation rule | Recovery |
|---|---|---|---|
| Invalid input | Explain exact correctable field in customer language | None | Correct and resubmit |
| Authentication missing/stale | Secure identity continuation | None | Login or step-up, then safe return |
| Unauthorized/inaccessible | Non-enumerating denial | None | Switch authorized context or contact support |
| Version conflict | Show changed truth and compare | No overwrite | Refresh and reconfirm |
| Timeout/unknown outcome | `Still checking`, never failure or success | No blind retry | Reconcile by operation/idempotency key |
| Owner unavailable | Explicit unavailable/blocked state | No inferred success | Retry per policy; preserve draft locally only if non-secret |
| Evidence unavailable | Action stopped or pending evidence | No committed-success rendering | Reconcile evidence owner |
| Provider delivery failure | Delivery failed while owner result remains separate | No duplicate command | Retry delivery or use Portal |
| Stale/expired focus | Explain context changed | No owner mutation | Fetch fresh projection |
| Stop active | Persistent stopped state | Deny non-release work | Independent authorized release process |

Every API error uses `application/problem+json`, stable customer-mappable code, correlation ID, and
retryability. Logs and telemetry use codes and opaque identifiers, not protected payloads.

## 10. API and Data Semantics

The candidate API is normative for the additive delta.

### 10.1 Admission atomicity

One transaction or recoverable saga must bind:

1. authenticated participant and tenant;
2. exact active professional admission and version;
3. exact disclosure version;
4. canonical Trial/Hire intent;
5. constitutional validation and evidence;
6. one `DISCOVERED` relationship;
7. one immutable agent instance;
8. one canonical relationship conversation; and
9. one initial workspace and resume focus.

The idempotency key plus canonical request digest reserve one outcome before side effects. Duplicate,
timeout, and cross-channel replay return the original identifiers. Same key with different canonical
input is `409`; inactive/mismatched admission or disclosure is `422`; unavailable validation or
evidence is `503` and cannot appear successful.

### 10.2 Progress composition

The progress projection reads owner facts and stores only projection metadata needed for versioning,
cache invalidation, and provenance. Each item exposes state, owner, required flag, truth dimensions,
updated time, blocked effect where applicable, and a server-ranked next action. Missing owner facts
produce `UNKNOWN` or `UNAVAILABLE`, never omission or success.

### 10.3 Focus integrity

Focus tokens are opaque, integrity protected, expiring, relationship scoped, and bound to a subject
version and intended destination. They are submitted only in a protected request body, never in a
path, query, fragment, redirect URL, referrer, browser history, analytics event, log, trace, metric,
or evidence payload. Resolution rechecks tenant, participant, relationship, object, version,
assurance, Stop state, and current authority. Denials do not enumerate other relationships or
objects. Navigation alone performs no owner mutation.

### 10.4 Compatibility

Canonical implementation merges this candidate into the existing BP OpenAPI and regenerates clients.
Existing response fields and accepted inputs remain compatible for the supported version. New fields
are additive unless a new schema version is negotiated. No Portal- or WhatsApp-only business model
may fork from the canonical contract.

### 10.5 Persistence ownership and write boundaries

No CEW surface creates a fourth ledger or a second source of owner truth. Persisted CEW data is
limited to the following owner-controlled classes:

| Data class | Accountable owner | Persistence rule |
|---|---|---|
| Account layout | Identity settings | Tenant-and-participant scoped, versioned, mutable preference; never copied into BP truth |
| Relationship workspace preference | Relationship Onboard owner | Tenant-and-relationship scoped, versioned, mutable preference |
| Admission reservation and result | Existing BP relationship idempotency/admission owner | Durable canonical request digest and one replayable outcome; references owner records rather than copying payloads |
| Progress projection metadata/cache | BP relationship governance | Disposable composition metadata only; source facts remain with their owners |
| Focus reference | BP focus issuer | Prefer integrity-protected stateless claims; if revocation state is required, store only a token hash and lifecycle metadata |
| Channel-session command result | BP Conversation Core | Existing session/version and command-result persistence; provider delivery remains separate |
| Constitutional evidence | Constitutional Engine/Audit Ledger | Append-only evidence records and opaque references; never rewritten by preference, projection, erasure, or rollback |

Every BP-owned mutable or operational record is bound to trusted `tenant_id`; relationship data also
uses `relationship_id`, and participant-owned data also uses the server-resolved participant. These
bindings participate in composite references/uniqueness and forced RLS for both read and write.
Tenant identity is never accepted from a request body, token claim alone, path alone, or provider
payload. Cross-tenant audit remains a separately authorized CE/Audit boundary, not a BP RLS bypass.

### 10.6 Admission transaction and idempotency protocol

Admission is externally atomic but may span existing owners. BP first reserves
`(tenant, operation purpose, Idempotency-Key)` with the canonical material-request digest and
`clientIntentId` before invoking any side effect. The durable coordinator records a monotonic state
(`RESERVED`, `IN_PROGRESS`, `SUCCEEDED`, `FAILED_RETRYABLE`, or `CONFLICT`), correlation, owner-step
receipts, evidence reference, and the complete terminal outcome.

Within a BP database, relationship mint, first-admission uniqueness, coordinator transition, and
outbox publication commit in one local transaction. Cross-owner work is a restartable,
forward-recoverable saga: each owner call has its own stable idempotency identity derived from the
reserved operation, and no `201`/`200` is returned until every required owner receipt and committed
evidence reference are durable. A crash or timeout leaves a reconcilable non-success state, never a
partial success response. Compensation may use only an accepted owner operation and never deletes
immutable evidence or a committed owner effect.

Equivalent replays return the stored terminal outcome. A changed canonical digest under the same
key records/returns conflict with zero new side effects. Reservation, hash comparison, state
transition, and result publication are concurrency-arbitrated; expiry of an operational key never
permits a second first mint because canonical owner uniqueness remains authoritative. All other CEW
mutations follow the same key/digest/result rule within their owning aggregate.

### 10.7 Projection provenance and invalidation

Every progress item carries accountable source owner, source-relative subject identity and version,
source contract version, produced time, observed time where applicable, last authoritative
confirmation, declared validity where present, freshness, and evidence state/reference. BP also
publishes its composition version and generation time. BP never synthesizes one global source
version or treats cache time as authoritative confirmation.

Projection metadata records the exact source-version vector and projection-contract version used.
Owner change/event, correction or supersession, relationship/participant revocation, Stop,
retention/erasure effect, unsupported source contract, or declared-validity expiry invalidates the
affected cache. Invalidation is monotonic and idempotent. Until recomposition succeeds, BP returns
the affected contribution as `STALE` or `UNAVAILABLE`; it does not serve it as current, omit it, or
reuse it to rank a consequential next action. Caches are rebuildable solely from currently
authorized owner facts and retained lineage.

### 10.8 Focus-reference lifecycle

A focus token contains or resolves to only an issuer/version, random token identity, tenant,
relationship, participant/role binding, destination, source subject/version, authority version,
issued time, expiry, and integrity-key identifier. It contains no raw PII, provider identity,
credential, message content, or business payload. Maximum lifetime is 15 minutes; clients cannot
refresh or extend it. Each mint uses a new random identity.

Resolution verifies integrity with an accepted active/retiring key, expiry, all bindings, current
membership/authority, Stop state, and source version. Logout, unlink, participant or role
revocation, relationship termination/deletion effect, Stop, subject correction/supersession, or
authority-version change invalidates resolution even before expiry. Integrity keys rotate with an
overlap no longer than the maximum token lifetime. Logs, telemetry, caches, and evidence may retain
only a keyed token fingerprint. Any optional revocation row expires no later than the token and is
purged unless a legal hold applies to the lifecycle event; the token itself is never evidence.

### 10.9 Retention, erasure, correction, and legal hold

| Data class | Normal disposition | Erasure/correction | Legal hold |
|---|---|---|---|
| Layout and relationship preferences | Retention owned by Identity/Onboard policy | Correct in place by version or erase; inaccessible relationships are not restored | Freeze only the held record under that owner's policy |
| Admission/idempotency and channel-command results | Retain through the owning operation's retry/reconciliation window and relationship policy | Minimise payload to digest and references; erasure cannot remove replay protection needed to prevent duplicate effects | Suspend purge for scoped records |
| Projection cache/metadata | Short-lived and disposable | Invalidate and purge; rebuild only from still-authorized facts | Hold source evidence, not a stale convenience cache, unless specifically scoped |
| Focus lifecycle metadata | Through token expiry plus bounded abuse/reconciliation window | Purge token fingerprints/revocation metadata when no longer required | Hold only the lifecycle/audit event, never revive token authority |
| Transcript, owner facts, and evidence | Existing Conversation/owner/CE policy | Owner correction and erasure workflows; immutable evidence retains permitted minimal lineage/hashes | Existing owner and CE hold controls |

The implementation impact analysis must bind each class to an accepted retention owner, duration,
erase/correct action, hold override, purge evidence, and export behavior. Missing policy is a stop;
implementers may not invent a duration or make immutable evidence erasable.

### 10.10 Migration and mixed-version safety

Persisted changes use expand/backfill/verify/cutover/contract. Expansion is additive and readable by
the prior application; backfill is tenant-bounded, restartable, idempotent, observable, and
quarantines malformed records without fabricating defaults. Dual-read or dual-write, when required,
has one declared authority and a deterministic divergence alarm. New writers do not emit a state
that any concurrently supported reader misinterprets as success. Contract/destructive cleanup is a
separate, later authorization after old readers and rollback windows are gone.

Schema and projection contract versions travel independently. Unsupported future source contracts
produce `UNAVAILABLE`; they are never silently down-converted. Rollback disables new entry while
preserving reads, replay, reconciliation, Stop, data rights, and all committed owner/evidence facts.

### 10.11 Backup, restore, and recovery objectives

Backups cover all BP mutable state, coordinator/outbox state, projection metadata needed for
diagnosis, and the separately protected immutable evidence ledger with tenant isolation and
encryption preserved. Restore qualification must prove referential consistency among admission
outcomes, owner identifiers, command results, and evidence references; projection caches may be
discarded and rebuilt. Point-in-time recovery must not resurrect erased payloads, expired focus
authority, revoked bindings, or superseded truth; post-restore replay/reconciliation repairs any
outbox or owner gap before writes reopen.

Numeric RPO/RTO, backup retention, regional copy, and recovery-environment authority are Platform
Architecture/Founder inputs. Their absence blocks implementation acceptance for CEW persistence;
this contract does not invent those external decisions. A restore rehearsal against the accepted
objectives is required before Component 08 passes.

### 10.12 Reconciliation and operational evidence

A tenant-scoped reconciler leases non-terminal admission and command operations, compares durable
owner receipts and evidence references, retries only with the original owner idempotency identity,
and reaches `SUCCEEDED`, `FAILED_RETRYABLE`, or an operator-visible quarantine. It also detects
orphan owner effects, missing outbox delivery, projection source-vector drift, purge failures, and
evidence-reference gaps. Lease expiry permits takeover without duplicate effects. No reconciler may
cross tenant boundaries, infer success from transport delivery, or manufacture a missing evidence
record.

Required redacted evidence includes concurrency arbitration, crash at every write boundary,
divergent replay, stuck-operation recovery, orphan detection, cache invalidation/rebuild,
cross-tenant denial, retention/erasure/hold and purge, expand/backfill/mixed-version rollback,
backup/restore, RPO/RTO rehearsal, and post-restore reconciliation. Evidence records use opaque
correlation/owner references and exact contract/image/migration digests, never protected payloads.

## 11. Security, Privacy, and Data Rights

1. Authentication and assurance are identity-owned.
2. Relationship and object authorization are evaluated server-side on every operation.
3. Anonymous marketplace reads cannot create account, membership, relationship, conversation,
   trial, contract, payment, or authority state.
4. Credentials, tokens, secrets, full telephone identity, provider payloads, and consent payloads
   never enter URLs, transcript, browser persistence, telemetry, screenshots, or evidence.
5. Browser persistence is limited to non-secret presentation state allowed by policy; owner truth is
   refetched.
6. WhatsApp signatures and replay controls are verified before normalization.
7. Rate limits, abuse controls, payload limits, content-type validation, and redaction apply at
   public edges.
8. Export, correction, erasure, retention, and legal hold use the existing data-rights owner and do
   not rewrite immutable evidence contrary to policy.
9. Account deletion, unlink, employment termination, logout, and channel-session end remain separate
   commands and audit events.
10. Requested Demo sender and recipient identities are runtime secrets referenced only as
    `DEMO_WHATSAPP_SENDER_REF` and `DEMO_WHATSAPP_TEST_RECIPIENT_REF`.

### 11.1 Candidate threat model and trust boundaries

The CEW threat boundary includes the anonymous browser, authenticated browser, Portal server,
Business Platform, Identity Boundary, Phone Identity Service/WhatsApp adapter, provider callback,
Conversation Core, employment/commercial owners, CE/evidence owner, background reconciler, and
telemetry/export paths. Required threat cases are:

| Threat | Required control and failure |
|---|---|
| Forged/stale customer identity, JWT substitution, or tenant claim | Independently validate issuer, signature, algorithm, audience, expiry/not-before and actor subject; derive tenant and roles only from current actor-keyed membership; fail closed. |
| IDOR, confused deputy, cross-tenant/relationship/object access | Authorize current participant, relationship, effective role, lifecycle, scope, command purpose, subject and owner versions before disclosure; inaccessible and absent resources are privacy-indistinguishable. |
| Focus theft, tamper, URL leakage, replay, or stale authority | Apply Section 10.8 claims, body-only transport, integrity verification, maximum lifetime, current-authority recheck, keyed fingerprint-only telemetry, revocation events, and single-use consumption for continuation/command-bearing focus. |
| Admission replay/key flooding or divergent retries | Reserve principal/purpose/key plus canonical digest before effects; arbitrate concurrency, return the durable original result, conflict without effects, and apply bounded quotas without evicting replay protection for committed effects. |
| CSRF, login CSRF, session fixation, stale assurance, or unsafe return | Use Identity-owned server sessions, transaction-bound state/nonce/PKCE, session rotation, strict cookie controls, mutation CSRF defense, fresh assurance where required, and server-issued single-use safe-return references. |
| Forged, stale, replayed, oversized, or parser-confusing WhatsApp callback | Authenticate raw bytes before parsing, verify the accepted provider signature and bounded timestamp, deduplicate provider message/event identity, enforce content/media limits, and acknowledge only according to the accepted adapter contract. |
| Workload impersonation or lateral movement | Independently authenticate allowlisted peer workload and operation in addition to the original customer proof; encrypted networking alone is insufficient. |
| Secret, phone, token, message, or customer-content disclosure | Secret-store references, encryption, minimization, deny-by-default telemetry attributes, structured redaction and seeded canary scans; no raw protected payload by default. |
| Stop suppression, release by ordinary flow, or rollback resurrection | Stop bypasses ordinary queues and rate limits, wins races before non-Stop commit, persists across sessions/channels/restarts, and can be released only by its accepted independent release contract. |

This table specializes the accepted platform threat model for WC-121. It does not weaken stronger
accepted Identity, Relationship Workspace, AE-01, Stop, evidence, privacy, or owner controls.

### 11.2 Authentication, assurance, authorization, and isolation

1. BP validates the raw customer proof on every request. Tenant, membership, effective roles, and
   participant identity come only from current actor-keyed membership; a JWT tenant/role claim,
   path, body, header, browser store, focus reference, provider callback, or prior result is never
   authority.
2. Routine authenticated CEW reads and presentation-preference writes require current
   `AAL2_ACCOUNT`. `HIRE`, channel linking, payment, sensitive account change, authority change,
   destructive action, and any owner-classified consequential action require the accepted
   `AAL3_FRESH`/mobile and typed-acknowledgement controls. Authentication success alone never
   executes the pending action. Emergency Stop remains available under its lower-assurance
   fail-safe contract; release uses the separately accepted stronger contract.
3. Authorization runs before existence, state, version, assurance, validation, or conflict detail:
   current tenant membership, relationship participation, effective role, command entitlement,
   lifecycle, scope/authority, object ownership, purpose, and authoritative versions are checked on
   every read, mutation, focus resolution, retry, callback-induced command, and background job.
4. Inaccessible and absent tenant/relationship/object/session/focus resources use one
   privacy-indistinguishable status/code/shape/header/timing family. Lists, counts, cursors,
   filenames, focus labels, and timing contain only already-authorized resources.
5. Forced tenant isolation applies to reads, writes, uniqueness, caches, queues, outbox,
   reconciliation, retention, export, restore, and maintenance. Service or operator identity never
   grants customer-resource authority.

The public wire contract preserves that evaluation order. Every authenticated success and error is
`Cache-Control: no-store`. After authentication, an inaccessible or absent tenant, relationship,
object, session, or focus returns the same normalized `404` family. A `403` assurance or entitlement
response is permitted only after the caller is authorized to know the resource and denial class;
`409`, `410`, `422`, version, lifecycle, validation, and retry detail are likewise disclosed only
after resource authorization. Status, code, body shape, headers, and externally observable timing
must not reveal which tenant/object binding or authorization predicate failed.

### 11.3 Browser session, CSRF, and safe return

Portal authentication remains Identity-owned. Server sessions use `Secure`, `HttpOnly`,
`SameSite=Lax` or stricter host-only cookies, narrow path/domain, bounded idle and absolute expiry,
rotation after authentication/step-up/account or tenant switch, refresh-token rotation, and
server-side revocation. Logout, switch, unlink, termination, deletion, Stop, and end-session each
clear or change only their accepted scope. Cacheable authenticated responses use private/no-store
policy as appropriate; credentials, focus/safe-return references, assurance and CSRF material are
not placed in service-worker or durable browser storage.

Every cookie-authenticated mutation requires an unguessable session-bound CSRF value plus
Origin/Fetch-Metadata validation; missing or mismatched proof fails before owner work. Bearer-only
non-browser callers must not acquire ambient cookie authority. Identity redirects bind exact
issuer, actor session, intent, provider, locale, safe-return purpose, state, nonce and PKCE. Safe
return is a server-issued opaque, single-use, maximum-15-minute reference bound to actor session,
tenant when known, relationship/focus when authorized, purpose and allowed relative destination.
Absolute, scheme-relative, encoded-host, user-info and unregistered destinations are denied.
Authentication or step-up consumes/revalidates the reference and current authority, then mints any
fresh focus; it never replays a pending mutation automatically.

### 11.4 Focus construction, transport, replay, and revocation

Section 10.8 is mandatory. Cryptographic construction uses an approved authenticated integrity
scheme, an unpredictable identity with at least 128 bits of entropy, explicit issuer/audience and
token-type separation, an active key identifier, and canonical serialization. A token is never an
authorization grant and never contains protected payload.

Focus is resolved by body-only `POST`; responses are `Cache-Control: no-store`. A
continuation/command-bearing token is atomically single-use. Reuse, key mismatch, expiry, tamper,
binding/version/authority change, logout, switch, unlink, revocation, Stop, termination, deletion,
correction or supersession returns a privacy-safe non-success and performs no owner mutation.
Ordinary display focus may be resolved repeatedly only when explicitly typed as non-command-bearing;
every resolution still reauthorizes, and each successful projection issues a fresh token identity.

### 11.5 Admission idempotency and abuse resistance

The Section 10.6 reservation is scoped to current actor, tenant, operation purpose and key; its
canonical digest covers every material semantic input and accepted contract version. Keys have at
least 128 bits of entropy and a constrained alphabet/length. Principal, IP/network-risk,
professional-admission and tenant controls bound reservation creation, concurrent in-flight work,
divergent-key attempts and status polling. Limits produce privacy-safe `429`/`Retry-After` with zero
new side effects and never apply to Emergency Stop.

High-cardinality keys, changed digests, abandoned reservations, and repeated conflicts are security
signals. Attackers cannot force eviction or expiry that permits a duplicate first mint; committed
effect replay protection and owner uniqueness survive the ordinary retry window. A rate limiter,
cache outage, process restart, rollback, or clock change cannot turn an unknown outcome into a new
admission or success.

### 11.6 WhatsApp callback, replay, rate, and media controls

Before decompression, JSON/form parsing, normalization, identity lookup, acknowledgement side
effects, or command dispatch, the approved adapter:

1. reads a bounded raw byte stream and rejects over-limit or unsupported encoding/content type;
2. computes and constant-time compares the accepted Meta signature over the exact raw bytes using
   the current/overlap secret; no reserialization is permitted;
3. validates the accepted Meta freshness proof within the contractually fixed maximum five-minute
   skew before processing; local receipt time is not provider freshness, and an inbound wire
   contract that cannot supply the accepted proof keeps callback activation blocked until an
   authorized contract amendment defines an equivalent replay-resistant proof;
4. reserves the provider account/phone reference and event/message identity before processing, so
   duplicate delivery returns the original acknowledgement and dispatches no duplicate command;
5. resolves phone/channel binding through the Phone Identity Service and then current relationship
   authority; payload tenant, relationship, actor, focus, command or sender assertions are hints
   only; and
6. records a redacted security outcome for signature, freshness, replay, size, type and dispatch.

Unknown/unlinked senders receive no relationship-existence detail. Per-source, phone-reference,
tenant, session and operation abuse controls bound callbacks, outbound attempts and expensive work;
Stop remains separately reachable and unthrottled by ordinary limits. Media is default-deny:
allowlisted type and signature/magic bytes must agree, declared/actual size, count and decompressed
size are bounded, filenames/metadata are sanitized, active content is rejected, malware and C-061
safety/consent gates complete before use, retrieval uses an isolated non-public principal with
timeouts/redirect restrictions, and quarantine objects never enter transcript, inference, evidence
payload or customer download.

### 11.7 Workload identity, secrets, and encryption

Every BP call to Identity, Phone Identity/adapter, Conversation, employment/commercial owners, CE,
PR, evidence and storage requires mutually authenticated, allowlisted workload identity plus
independent audience, caller, operation/purpose and delegated customer/relationship checks. The
original customer proof is independently validated where the accepted owner contract requires it.
No shared all-service credential, network-location trust, arbitrary service delegation, or
customer-controlled internal identity is permitted. Least-privilege identities are separate for
online request, callback, reconciler, migration, restore and export purposes.

Secrets and signing material exist only in an authorized secret manager behind protected
references, are absent from images/configuration artifacts and customer payloads, and support
versioned rotation, bounded overlap, immediate revocation and auditable access. Provider webhook,
focus/safe-return signing, CSRF/session, database, mTLS and export keys are purpose-separated.
Compromise revokes the affected purpose and invalidates derived authority; it does not silently
fall back to an old or default secret.

TLS protects every external and internal hop; customer-private data, idempotency/coordinator state,
session/focus/revocation state, backups, quarantine, exports and evidence are encrypted at rest
under accepted owner/platform policy. Export uses a short-lived authenticated retrieval grant.
Key unavailability fails closed for writes and protected reads; rotation/restore tests prove old
ciphertext readability only for the accepted retention window and prove revoked authority is not
resurrected. Numeric algorithms, key custody and rotation periods remain governed by accepted
Security/Platform contracts rather than invented by WC-121.

### 11.8 Telemetry redaction and security evidence

Telemetry is deny-by-default. Allowed fields are operation/security-event code, outcome class,
latency bucket, schema/image version, environment identifier, and keyed opaque fingerprints for
correlation, tenant, relationship, actor, message, token or idempotency identity when operationally
required. Raw or reversibly masked credentials, cookies, authorization/CSRF headers, provider
signatures/secrets, focus/safe-return/idempotency values, full phone/email, message/media content,
request/response bodies, filenames, URLs/query strings, owner payloads, stack traces and policy
internals are prohibited.

Redaction occurs before log/span/metric/evidence/export serialization and again at the collector
boundary. Cardinality is bounded. Seeded canaries and full-surface scans fail the release on any
prohibited value. Security evidence records the decision and opaque correlation, not the secret or
attacker payload; alert access and retention follow the accepted owner policy.

### 11.9 Stop precedence and destructive/session operation separation

Stop is evaluated before ordinary routing and immediately before every non-Stop governed commit.
When Stop races admission, focus, handoff, channel end, owner command, reconciliation or provider
delivery, Stop wins: new effects cease, in-flight uncertainty is quarantined/reconciled, delivery
does not imply execution, and a committed pre-Stop effect remains truthful. Stop is not blocked by
ordinary CSRF step-up, acknowledgement, rate limits, projection/provider/owner availability, an
ended session, logout or rollback. Abuse protection may authenticate/record the requester under the
accepted fail-safe Stop contract but cannot delay cessation.

Logout, web-session revocation, WhatsApp end-session, account switch, channel unlink, relationship
termination, account deletion, Stop activation and Stop release have distinct operation IDs,
purpose-bound idempotency namespaces, assurance/acknowledgement, owners, evidence types, effects and
recovery. No generic `end`, `close`, reconnect, timeout, token refresh, cleanup, rollback or provider
event may dispatch more than one or substitute for another. Stop release is never a side effect of
any of them.

### 11.10 Rollback, revocation, and mandatory security stops

Rollback never restores an expired/revoked session, membership, role, phone link, focus/safe-return
reference, CSRF/assurance proof, workload credential or secret version; never reopens ingress,
provider traffic or capability authority; and never deletes security/evidence conclusions.
Capability disablement blocks new work while retaining authorized Stop, read, reconciliation and
data-right paths. Revocation propagates to caches, queues, projections, sessions and background work
before affected work resumes. Unknown effects reconcile under original identities.

Implementation stops when any accepted identity/assurance, authorization/role, Stop/release,
provider-signature, media, rate/abuse, workload-identity, key/secret, encryption, telemetry,
retention/revocation, or privacy-safe error contract is absent or incompatible; when exact raw-byte
signature verification cannot be proven; when a protected value appears in a prohibited surface;
or when rollback/recovery can resurrect authority. The implementer may not invent the missing
Legal, Founder, Product, provider, Platform, retention, key-custody, recovery, deployment, traffic,
activation, approval, or merge decision.

## 12. Accessibility, Performance, and Operability

### 12.1 Accessibility

The solution must pass WCAG 2.2 AA, full keyboard use, visible focus, logical focus order,
screen-reader names/status announcements, 200% zoom, 360 CSS-pixel reflow, non-color meaning, RTL,
locale formatting, reduced motion, and focus restoration across sheets, redirects, and pane changes.

### 12.2 Performance budgets

| Measure | Budget at p95 under qualification load |
|---|---|
| Portal shell usable with cached static assets | <= 2.5 seconds |
| Conversation send acknowledgement | <= 1.0 second when BP accepts |
| Progress projection | <= 1.5 seconds, or explicit loading/unavailable state |
| Focus resolution | <= 750 milliseconds |
| Pane interaction | No long task > 200 milliseconds attributable to workspace code |
| WhatsApp acknowledgement after verified inbound | <= 2.0 seconds excluding provider network delay |

Budgets are qualification targets, not permission to fabricate optimistic success.

### 12.3 Telemetry

Required dimensions are environment identifier, component, operation ID, schema version, outcome
class, latency, retry count, channel, lifecycle stage, and opaque correlation/relationship/message
references. Metrics include admission replay/conflict, journey completion/abandonment, progress and
focus failures, unknown outcomes, handoff success/revert, end-session results, Stop reachability,
provider delivery, accessibility violations, and redaction failures.

Alerts distinguish customer-impacting owner failure, provider delivery failure, evidence failure,
identity failure, and UI render failure. Runbooks must state safe stop, reconciliation, rollback, and
the owner to contact.

## 13. Environment, Rollout, Rollback, and Provider Gate

### 13.1 Same-image rule

Demo, UAT, and Production use the same immutable application digests, routes, components, schemas,
and lifecycle behavior. Configuration may vary only for protected endpoints, identity, secrets,
data, scale, and authorized external connections. Code and templates may not branch on environment
to remove behavior.

Default-off capability controls:

1. are present in the same image;
2. evaluate explicit owner authority/configuration, not `Demo`, `UAT`, or `Production`;
3. show a truthful blocked/unavailable state when authority is absent; and
4. do not return success-shaped stubs.

### 13.2 Rollout

1. Merge and validate API contracts and generated clients.
2. Qualify owner operations and projections with repository-owned fixtures.
3. Qualify Portal and WhatsApp against emulators using the same image.
4. Qualify cross-channel races, retries, replay, Stop, data rights, and accessibility.
5. Obtain separate provider, cloud, deployment, traffic, and activation authority.
6. Perform live-provider qualification only in the authorized account and bounded recipient set.

### 13.3 Rollback

Presentation rollback reverts routing/configuration to the last accepted image without deleting
owner state. API rollback preserves backward-compatible fields and accepts prior clients.
Admission, command, evidence, payment, and provider side effects are reconciled, not erased or
claimed reversed. Capability disablement blocks new entry while preserving read/recovery/Stop/data
rights. Any uncertain mutation is surfaced and reconciled by idempotency/correlation identity.

### 13.4 Meta same-number feasibility

The official Meta getting-started guide models selection of a business `From` number and addition
of a `To` recipient, and later uses a test business phone-number ID with a WhatsApp user phone
number. It does not explicitly confirm that one exact identity may serve as both registered business
sender and customer recipient:

`https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started.md/`

Therefore live Demo self-messaging with the requested same sender/recipient identity is
**BLOCKED**, not rejected and not assumed feasible. The gate closes only with one of:

1. binding official Meta support confirmation for the target account and configuration;
2. a separately authorized, bounded provider feasibility probe with retained evidence; or
3. a distinct Founder-authorized Demo recipient identity.

Emulator qualification may proceed with symbolic identities but cannot satisfy live-provider
acceptance.

### 13.5 Deployment topology and provider boundary

CEW is not a new deployable. Portal assets run in the existing Web image; BP admission, projection,
focus, and channel-session APIs run in the existing BP image; channel translation and provider
delivery run only through the accepted Conversation/WhatsApp adapter boundary; owner and evidence
work remains in its accepted exact-seven workload. Only Web, BP, and the accepted identity edge may
use existing public ingress. Provider callbacks terminate at the accepted callback edge and pass a
verified, deduplicated, channel-neutral envelope inward. No provider credential, provider SDK,
provider payload, or delivery status becomes BP business authority.

Each environment uses its existing isolated ACA environment, VNet, managed identities, Key Vault,
data boundary, telemetry, and evidence boundary. CEW creates no public hostname, shared
cross-environment identity, direct provider-to-owner route, direct client-to-provider business
route, or cross-environment network path. Any required topology outside this mapping is a new
architecture decision and blocks the owning component.

### 13.6 Closed-world configuration, capability, and secret gates

The accepted environment manifest and secret dependency catalog are the only deployment-time
configuration sources. The rendered configuration is schema-versioned and bound to the release
tuple by digest. Unknown keys, environment mismatches, unbound digests, mutable image references,
undeclared endpoints, or hand-written consumer mappings fail before mutation.

Each CEW capability has an explicit default-off record containing capability contract version,
requested state, authority-evidence reference, required dependency IDs, configuration digest, and
effective state. Effective states are `BLOCKED`, `UNAVAILABLE`, `READY_INACTIVE`, or `ACTIVE`;
they are never inferred from environment name. `ACTIVE` additionally requires separate activation
authority and a recorded traffic decision. Missing or stale authority can only reduce state.

Secrets are runtime references to the accepted catalog, resolved by the exact consuming workload's
managed identity. Sender identity, recipient allowlist, callback signature material, provider
credential, focus integrity keys, workload credentials, and encryption keys have distinct logical
purposes and rotation classes. Values are prohibited from image layers, manifests, Terraform,
state, plans, workflow inputs/outputs, command arguments, logs, traces, evidence, and repository
artifacts. Metadata readiness proves only reference existence, enabled state, expiry, version, and
consumer authorization; it never proves provider acceptance or permits traffic.

### 13.7 Health, readiness, capacity, and backpressure

Liveness is process-local and must not call an owner, provider, database, or telemetry sink.
Startup proves schema/configuration parsing and construction of mandatory route dependencies.
Traffic readiness proves mandatory private dependencies, current migration watermark,
configuration/release digest agreement, Stop enforcement, and evidence-write availability.
Optional provider/channel readiness is reported separately and cannot make unrelated reads
unready. No probe sends provider traffic, exercises a consequential command, or records success
for an external effect.

Impact analysis must freeze a workload envelope for Portal sessions, BP requests, concurrent
admissions, progress/focus operations, inbound callbacks, outbound deliveries, owner calls,
reconciliation backlog, payload size, and telemetry cardinality, plus per-resource soft and hard
limits. Load qualification must prove the Section 12.2 latency budgets within that envelope and a
bounded recovery time after overload. Missing forecasts or limits block activation.

Every ingress and asynchronous boundary has a bounded queue/concurrency limit and exposes depth,
age, rejection, retry, and saturation. Admission control rejects before owner effects; retry uses
bounded jitter and original idempotency identity; expired or poison work is quarantined for
reconciliation. Provider acknowledgement remains distinct from business processing. Overload may
return typed `429`/`503`/`UNAVAILABLE`, but may not drop accepted work, fabricate success, bypass
Stop, or retry a non-idempotent effect without durable reservation.

### 13.8 SLO, observability, and alert contract

The SLIs are availability of authorized Portal/BP operations, successful verified-callback
admission, Section 12.2 latency, owner/evidence conclusion completion, queue age, and recovery from
dependency failure. Provider delivery is a separate SLI and never upgrades owner/evidence success.
Numeric availability target, error budget, evaluation windows, qualification load, queue-age
limits, and incident response objectives require accepted Product/Platform/Founder inputs before
live activation; this contract does not invent them.

Metrics, logs, and traces use the redacted dimensions in Section 12.3 and bind environment,
release/configuration digest, operation, capability state, and opaque correlation. Alerts must
separately cover customer-impacting owner failure, evidence failure, identity/authorization
failure, provider callback/delivery failure, migration/reconciliation failure, saturation/queue
age, readiness/configuration drift, redaction canary, and Stop-path failure. Each alert has an
owner, severity, runbook, safe action, reconciliation path, and evidence destination. Missing SLO
inputs, alert ownership, tested routing, or runbook evidence blocks traffic activation.

### 13.9 Immutable promotion and migration sequence

CEW promotion extends, and never replaces, the accepted exact-seven release tuple:
`signed manifest + exact image digests + reviewed configuration/catalog digests + dependency
manifest + schema compatibility + evidence`. The exact tuple qualified in Component 08 is promoted
without rebuild, retag, image mutation, or environment-specific feature compilation.

Deployment order is preflight; additive expand migration; tenant-bounded backfill; verification and
quarantine closure; new revision at zero traffic; private startup/readiness; repository-owned
journey, security, performance, and rollback probes; independent tuple verification; then a
separately authorized traffic switch. Cutover precedes no destructive contraction. Contract
migration occurs only after the prior-reader and rollback windows close under separate authority.
A migration, compatibility, evidence, or probe failure leaves the previous revision serving and the
new revision at zero traffic.

### 13.10 Deployment, rollback, and recovery integration

Deployment uses the accepted environment-isolated OIDC, ephemeral private runner, managed identity,
private state/configuration, policy, cost, lease, and independent-verification gates. The pipeline
must prove source authorization, signed digests, expected subscription/resource group/environment,
no foreign-environment reference, current rollback tuple, and no secret value before mutation.
Implementation authorization is not cloud, deployment, traffic, or activation authority.

Rollback is a traffic/configuration switch to the immediately previous qualified compatible tuple;
it does not rebuild, retag, run a destructive down-migration, erase an owner effect, restore an old
security state, or claim a provider effect reversed. Capability disablement blocks new entry while
preserving read, reconciliation, Stop, and data-right paths. Post-switch reconciliation and
non-resurrection evidence are mandatory.

UAT must qualify backup/PITR, isolated restore, tenant/RLS checks, evidence linkage, current-key
decryption, erased/revoked-state non-resurrection, reconciliation, and previous-image readability.
Production recovery remains plan-only until separately authorized. Numeric RPO, RTO, backup
retention, regional-copy policy, recovery environment, incident owner, and recovery-execution
authority are mandatory external decisions; their absence blocks deployment acceptance and live
activation.

### 13.11 Independent traffic and activation gates

The following records are separate and non-transitive: implementation authority, provider-account
authority, credential-use authority, cloud mutation authority, deployment authority, external
traffic authority with bounded recipients and window, feature activation authority, PR approval,
and merge. A prior environment acceptance, healthy revision, successful plan, credential presence,
emulator result, or issue label satisfies none of them.

Activation is an explicit post-deployment operation against the qualified release/configuration
digest. It records approver/authority evidence, capability, environment, bounded audience, start
and expiry, rollback tuple, incident owner, spend boundary, and observability readiness. A mismatch,
expiry, missing record, or Stop state fails closed to `READY_INACTIVE` or `BLOCKED`, never active.

### 13.12 Live Demo provider gate and required evidence

Live Demo remains blocked by Section 13.4 and every independent gate in Section 13.11. After those
gates close, the pipeline may deploy only the Component 08 digest, resolve protected references in
the authorized secret store, verify callback challenge/signature and bounded allowlist, and perform
only the approved scenario/window. Deployment must begin inactive; callback or outbound traffic is
not enabled by deployment success.

Required redacted evidence is: signed release/configuration/catalog digests; migration and readiness
results; capability-state transitions; provider feasibility basis; opaque provider account,
sender, and recipient reference identifiers; callback verification; bounded inbound/outbound
delivery separated from owner/evidence conclusions; SLO/alert routing; capacity/backpressure
result; rollback and reconciliation rehearsal; incident owner; spend/window/recipient bounds; and
proof of deactivation at expiry. Full telephone identity, credential, payload, or secret is never
evidence. Emulator evidence cannot close this gate.

## 14. Enterprise Requirement Traceability

| Requirement | Solution binding | Direct evidence |
|---|---|---|
| CEW-ER-001 | SD-001; Sections 5, 8 | One relationship/conversation/workspace identity journey |
| CEW-ER-002 | SD-001; Sections 4, 5 | Generated BP client and adapter contract tests |
| CEW-ER-003 | Sections 6-8 | Conversation-first journey suite |
| CEW-ER-004 | Sections 6, 9 | No silent visual-control owner writes |
| CEW-ER-005 | Section 6.1 | Expanded three-region UI test |
| CEW-ER-006 | Sections 6.1, 12.1 | Reachability and pane-control accessibility tests |
| CEW-ER-007 | Section 6.2 | 360px compact composition test |
| CEW-ER-008 | Sections 6, 10.2 | Lifecycle/focus projection fixtures |
| CEW-ER-009 | Sections 6.3, 10.3 | Transcript identity preserved during focus changes |
| CEW-ER-010 | Sections 7, 8 | Portal/WhatsApp parity matrix |
| CEW-ER-011 | Sections 7, 8 | Authenticated handoff and exact-return test |
| CEW-ER-012 | Sections 7-9 | Identity lifecycle distinctness tests |
| CEW-ER-013 | Sections 8, 10.1 | Anonymous discovery and intent carryover |
| CEW-ER-014 | Sections 8, 10.1 | Trial/Hire evidence, idempotency, and commercial tests |
| CEW-ER-015 | Sections 6, 8 | Induction projection completeness |
| CEW-ER-016 | Sections 8-10 | Versioned plan/goal/budget/Decision Space tests |
| CEW-ER-017 | Section 9.2 | Independent truth-dimension fixtures |
| CEW-ER-018 | Sections 6.4, 8 | Outcome-first performance rendering |
| CEW-ER-019 | Sections 6.4, 7 | Consequential-action disclosure/confirm tests |
| CEW-ER-020 | Sections 1.2, 8, 9 | Stop reachability/effect suite |
| CEW-ER-021 | Sections 5, 6 | Multi-relationship isolation/switch tests |
| CEW-ER-022 | Sections 6.3, 11 | Preference scope/privacy tests |
| CEW-ER-023 | Section 9.3 | Distinct adverse-state fixtures |
| CEW-ER-024 | Section 6.4 | Customer-language and raw-vocabulary scan |
| CEW-ER-025 | Sections 5, 6.4 | DMA adapter vocabulary fixture |
| CEW-ER-026 | Sections 5, 8 | Non-DMA professional conformance fixture |
| CEW-ER-027 | Section 5.1 | Client network allowlist test |
| CEW-ER-028 | Sections 4, 5.1 | Generated-client/approved-adapter dependency scan |
| CEW-ER-029 | Sections 9, 10.2 | Owner-version reconciliation tests |
| CEW-ER-030 | Section 12.1 | Automated/manual accessibility qualification |
| CEW-ER-031 | Sections 6.4, 7 | Cross-channel terminology snapshots |
| CEW-ER-032 | Section 13.1 | Exact-image three-configuration qualification |
| CEW-ER-033 | Section 13.1 | Configuration and changed-digest attestation |
| CEW-ER-034 | Sections 13.1-13.4 | Protected-action and truthful-block tests |
| CEW-ER-035 | Sections 6.3, 10.3, 11 | Navigation/channel persistence without client truth |
| CEW-ER-036 | Sections 9, 10.2 | Server-ranked next-action test |
| CEW-ER-037 | Sections 8, 11 | Anonymous zero-write oracle |
| CEW-ER-038 | SD-002; Section 10.1 | Admission duplicate/timeout/replay oracle |
| CEW-ER-039 | Sections 8, 10.1 | Identity success cannot create relationship |
| CEW-ER-040 | SD-007; Sections 7, 11 | Web secret/transcript isolation |
| CEW-ER-041 | SD-008; Sections 7, 11 | WhatsApp registration/professional-context isolation |
| CEW-ER-042 | SD-004; Section 6.3 | Preference owner and authority tests |
| CEW-ER-043 | SD-005; Section 10.3 | Shared typed-focus resolution tests |
| CEW-ER-044 | SD-006; Sections 7-9 | Distinct operation/effect matrix |
| CEW-ER-045 | SD-003; Section 10.2 | No-client-join and owner-provenance tests |
| CEW-ER-046 | SD-010; Section 13.1 | Same-image default-off/enabled oracle |

## 15. Fitness Oracles

Each oracle must be repository-owned, executable in Docker, fail before the applicable
implementation, and pass against the exact candidate.

| Fitness ID | Direct executable oracle |
|---|---|
| CEW-FIT-01 | Run the same lifecycle fixture through Portal and WhatsApp; compare relationship, command, owner-state, and evidence IDs. |
| CEW-FIT-02 | Complete discovery-to-trial and discovery-to-hire using conversation and one-action turns; assert no primary long form or raw vocabulary. |
| CEW-FIT-03 | Timed first-use fixture completes induction, goal, schedule, budget, and Decision Space within accepted AD-013 limits. |
| CEW-FIT-04 | Switch channel at every stage; assert invariant relationship, conversation, lifecycle, plan, message, command, and evidence identities. |
| CEW-FIT-05 | Registration/login/logout/stale-session/switch fixtures return to exact safe context with one account and relationship. |
| CEW-FIT-06 | Axe plus keyboard/screen-reader/manual suite covers hide/show/resize/restore at 200%, 360px, RTL, and focus restore. |
| CEW-FIT-07 | Enumerate every Portal composition and WhatsApp state; assert Stop is visible or directly invocable and effective. |
| CEW-FIT-08 | Fixture every lifecycle stage; compare progress fields and next action to BP projection with client inference disabled. |
| CEW-FIT-09 | Vary five truth dimensions independently; assert distinct accessible status and no collapsed success. |
| CEW-FIT-10 | Snapshot every consequential action before submission; assert effect, authority, cost if applicable, limitation, confirm, and cancel. |
| CEW-FIT-11 | Inject unknown/stale/partial/blocked/unavailable/disputed truth; assert none renders empty or successful. |
| CEW-FIT-12 | Performance fixtures place business outcome before optional supporting technical evidence. |
| CEW-FIT-13 | Run DMA Packages A-E through shared shell/grammar; changed-path scan finds no DMA branch in shared owners. |
| CEW-FIT-14 | Run one non-DMA fixture through identical shell/lifecycle/progress/channel contracts with no shared-owner specialization. |
| CEW-FIT-15 | Capture client traffic; allow only generated BP operations, approved identity handoffs, and independent Stop. |
| CEW-FIT-16 | Scan transcript, URL, telemetry, persistence, evidence, and screenshots for seeded secrets/tokens/full phone identity; find zero. |
| CEW-FIT-17 | Record one image digest and pass the full suite under Demo-, UAT-, and Production-shaped configuration. |
| CEW-FIT-18 | Compare route/component/command/schema/lifecycle manifests across configurations; assert equality and authorized emulator/account substitution only. |
| CEW-FIT-19 | Race Portal-WhatsApp-Portal retry/timeout/replay; assert one logical command and authoritative conclusion. |
| CEW-FIT-20 | Readability/domain-language/accessibility scanner and conversation snapshots enforce one primary action per turn. |
| CEW-FIT-21 | Snapshot all write stores before/after anonymous discovery; assert zero account/membership/relationship/conversation/trial/contract/payment/authority writes. |
| CEW-FIT-22 | Preserve Trial/Hire through identity; duplicate, timeout, and cross-channel replay admission; assert one `DISCOVERED` relationship and resume target. |
| CEW-FIT-23 | Seed web and WhatsApp registration secrets; assert zero professional transcript/context occurrences except explicitly confirmed minimum profile facts. |
| CEW-FIT-24 | Invoke logout/end-session/switch/unlink/terminate/delete independently; assert exact owner call and zero cross-trigger. |
| CEW-FIT-25 | Resolve one focus from Portal and WhatsApp; assert same destination, deny stale/inaccessible without enumeration, and zero owner mutation. |
| CEW-FIT-26 | Run default-off and enabled on one image across three configurations; assert equal manifests and truthful authority-block states. |

## 16. Dependency-Ordered Work Components

| Work Component | Outcome | Depends on | Completion evidence |
|---|---|---|---|
| CEW-WC-01 Contract baseline and generated clients | Canonical BP API incorporates candidate delta without fork | Founder accepts exact package and WC-121; implementation authorized | OpenAPI validation, compatibility tests, generated-client build |
| CEW-WC-02 Portal workspace shell | Expanded/compact conversation-first regions and preferences | 01 | Component, accessibility, responsive, persistence tests |
| CEW-WC-03 Acquisition and identity continuity | Anonymous discovery, registration/login return, exact admission | 01-02 | Zero-write, safe-return, admission idempotency/security tests |
| CEW-WC-04 Trial, hire, and lifecycle workspace | Conversational trial/hire and adaptive lifecycle progress | 01-03 | Journey, commercial-distinction, progress truth tests |
| CEW-WC-05 Induction, skills, goals, and planning | Conversational configuration with visual verification | 01-04 | Version/conflict/evidence/Decision Space tests |
| CEW-WC-06 Operations and performance | Outcome-first operation, evidence, budget, and performance experience | 01-05 | Five-dimension, outcome, alert, reconciliation tests |
| CEW-WC-07 WhatsApp parity and end-session | Shared lifecycle presentation and distinct session semantics | 01, 03-06; WC-120 accepted capability | Adapter, parity, identity separation, end-session tests |
| CEW-WC-08 Cross-channel and same-image qualification | Handoff, races, accessibility, privacy, operability, environment parity | 02-07 | CEW-FIT-01 through CEW-FIT-26 and image digest attestation |
| CEW-WC-09 Live Demo provider and deployment | Authorized provider configuration, deployment, traffic, and bounded live acceptance | 08 plus all separate protected-action gates and same-number feasibility closure | Provider evidence, deployment digest, live journey evidence, rollback rehearsal |

Components 01-08 are specification-complete but implementation-blocked until the external Data,
Security, and Platform dependencies recorded in their specialist dispositions are accepted or
closed, the Founder accepts the exact package, Docker-only validation passes, and current-session
implementation authorization is recorded. Component 09 is additionally **BLOCKED** until Section
13.4 closes and separate provider, cloud, deployment, traffic, and activation authority is recorded.

## 17. No-Drift Rules

The Platform IT Expert must stop and escalate rather than:

1. invent a second admission, conversation, relationship, progress truth, or provider business API;
2. place identity secrets or institutional registration in professional conversation;
3. infer owner completion, eligibility, next action, or success in a client;
4. make Demo a functionally reduced build;
5. use environment names as capability logic;
6. represent emulator evidence as live-provider evidence;
7. embed protected sender or recipient identity in repository artifacts;
8. conflate logout, end-session, unlink, switch, termination, deletion, or Stop;
9. add DMA-specific states or branches to the shared platform; or
10. deploy, send traffic, activate, approve, or merge without separate authority.

## 18. Solution Readiness

| Area | Result |
|---|---|
| Owner/component boundaries | READY FOR FOUNDER REVIEW |
| Existing API reuse | READY FOR FOUNDER REVIEW |
| Additive API delta | READY FOR VALIDATION |
| Portal and WhatsApp journeys | READY FOR FOUNDER REVIEW |
| Data architecture and lifecycle contract | REPAIRED - EXTERNAL RECOVERY OBJECTIVES AND OWNER LIFECYCLE POLICIES BLOCK IMPLEMENTATION ACCEPTANCE |
| Security architecture and privacy contract | REPAIRED - EXTERNAL ACCEPTED CONTROL PROFILES, CALLBACK FRESHNESS, AND DIRECT EVIDENCE BLOCK IMPLEMENTATION ACCEPTANCE |
| Accessibility and customer experience | READY FOR FOUNDER REVIEW |
| Platform topology/configuration/promotion contract | REPAIRED - EXTERNAL SLO, CAPACITY, RECOVERY, AND AUTHORITY DECISIONS BLOCK ACCEPTANCE |
| Components 01-08 | SPECIFICATION COMPLETE - IMPLEMENTATION BLOCKED BY SPECIALIST AND AUTHORITY GATES |
| Component 09 live provider/deployment | BLOCKED - SAME-NUMBER FEASIBILITY AND PROTECTED AUTHORITIES ABSENT |

This package becomes implementation input only after Docker-only validation, Founder acceptance of
the exact package and WC-121, closure or explicit acceptance of every specialist dependency, and
explicit implementation authorization for the current session.

## 19. Author Review Record

| Finding | Severity | Repair | Result |
|---|---|---|---|
| Existing BP admission could have been forked by a new customer command | Material | CEW-SD-002 and Sections 4/10.1 require compatible tightening of `admitEmploymentRelationship` | CLOSED |
| Account layout, relationship defaults, and transient focus could have shared an unsafe truth store | Material | CEW-SD-004 and Section 6.3 bind each scope to its accepted owner and give preferences zero authority | CLOSED |
| Adaptive progress could have become a second lifecycle/readiness owner | Material | CEW-SD-003 and Section 10.2 restrict it to a provenance-bearing composition of owner facts | CLOSED |
| Portal card focus and WhatsApp continuation could have diverged or become an authorization token | Material | CEW-SD-005 and Section 10.3 require one opaque reference and reauthorization on every resolution | CLOSED |
| End-session could have been confused with logout, unlink, termination, deletion, or Stop | Material | CEW-SD-006 and Sections 7-9 define a bounded channel-session command and distinct effects | CLOSED |
| WhatsApp "same look and feel" lacked an explicit visual-to-channel adaptation | Material | Section 7 now maps Portal hierarchy to WhatsApp presentation and freezes semantic/accessibility parity | CLOSED |
| Same sender/recipient live Demo feasibility lacked binding official confirmation | Blocking for live provider only | Section 13.4 blocks live self-messaging pending official confirmation, authorized probe, or distinct recipient | CLOSED FOR COMPONENTS 01-08; COMPONENT 09 BLOCKED |
| Implementation Work Contract lacked stable repository-ledger requirements | Material | WC-121 now defines WC121-R001 through WC121-R021 with a digest-bound evidence ledger | CLOSED |
| Same-image completeness could have been mistaken for provider/deployment authority | Material | Sections 13 and 16 preserve separate provider, cloud, deployment, traffic, activation, approval, and merge gates | CLOSED |
| Persistence ownership, saga atomicity, projection provenance, focus lifecycle, tenant isolation, retention, migration, restore, and reconciliation lacked implementation-grade Data predicates | Material | Data Architect disposition repaired Sections 10.5-10.12, the API provenance/evidence schemas, WC-121 data controls, and WC121-R019 | CLOSED IN SPECIFICATION; EXTERNAL RECOVERY AND OWNER POLICY INPUTS BLOCK IMPLEMENTATION ACCEPTANCE |
| Trust boundaries, current authority, anti-enumeration, browser continuity, focus/admission abuse, WhatsApp ingress, workload identity, encryption/redaction, Stop precedence, and non-resurrection were incomplete | Material | Security Architect disposition repaired CEW-SD-013, Sections 11.1-11.10, authenticated API cache/denial behavior, WC-121 security controls, and WC121-R020 | CLOSED IN SPECIFICATION; EXTERNAL CONTROL ACCEPTANCE AND DIRECT EVIDENCE BLOCK IMPLEMENTATION ACCEPTANCE |
| Existing-workload placement, provider edge, capability/configuration, secret reference, health/readiness, capacity/backpressure, SLO/alert, promotion, migration, rollback, DR, and activation behavior was not one executable platform contract | Material | CEW-SD-014/015 and Sections 13.5-13.12 bind CEW to the accepted exact-seven topology and define fail-closed platform gates and evidence | CLOSED; EXTERNAL NUMERIC/OWNER/AUTHORITY INPUTS BLOCK ACCEPTANCE |
| Specialist repairs introduced SD-013 through SD-015 while WC-121 still cited only SD-001 through SD-012 and overstated Components 01-08 readiness | Material | WC-121 now binds SD-001 through SD-015 and the readiness/entry-gate language states every Data, Security, Platform, Founder, validation, and session-authorization dependency | CLOSED |

Author review confirms complete trace from `CEW-ER-001` through `CEW-ER-046`, direct oracles for
`CEW-FIT-01` through `CEW-FIT-26`, one bounded owner per additive surface, and an exact
implementation specification for Components 01-08. The specialist dispositions remain blocking
inputs rather than implicit defaults: implementation cannot begin until their external dependencies
and every authority gate close. Live-provider Component 09 remains explicitly blocked and cannot be
represented as accepted or complete.
