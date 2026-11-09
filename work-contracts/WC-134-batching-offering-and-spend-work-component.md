# WC-134 - Durable Batching, Offering Metering And Shared Spend Work Component

## 1. Record And Outcome

| Field | Value |
|---|---|
| Parent | [WC-134 WhatsApp Demo rollout](./WC-134-whatsapp-demo-complete-rollout-work-component.md) |
| Related implementation policy | [WC-134 runtime generation and reconciliation](./WC-134-runtime-generation-and-reconciliation-policy.md) |
| Accountable delivery office | Platform IT Expert (INST-010) |
| Founder direction | 2026-11-09: prioritize a work component with implementation clarity for durable batching, full offering metering and shared spend continuity |
| Status | IMPLEMENTATION WORK COMPONENT; NOT A COMPLETION, PR, DEPLOYMENT OR LIVE-ACCEPTANCE CLAIM |
| Batching disposition | CURRENT SCOPE CLOSED FOR THIS ITERATION: approved bounds, contract boundary and fail-closed behavior are recorded; production collection and dispatch are deferred. |
| Delivery order | Batch, offering metering, shared spend continuity, Docker qualification and author review, scoped commits and Founder-review PR |
| Authority | Existing current-session implementation authorization applies. This document does not approve provider configuration, prices, expenditure, external traffic, deployment or live acceptance. |

Customer outcome: consecutive eligible short messages can be understood as one request without
losing the individual messages or their authority; use of a professional's offering is measured
against its actual accepted or trial allowance; and the environment's model and messaging spend
cannot reset when the service tenant changes. Completion requires the integrated behavior and
its failure paths, not just helper code, compilation or a green subset of tests.

The three parts interact: a grouped request is a new bounded runtime input, its actual component
invocations require WBE commercial authorization, and every applicable model and message attempt
must respect the BP operational ceiling. Commercial allowance is not operational spend authority,
and neither owner may mint the other's permission.

## 2. Current Baseline And Reuse

| Surface | Available now | Not yet available |
|---|---|---|
| Conversation admission | [ConversationService](../src/business-platform/Services/ConversationService.cs) records canonical messages, SEND idempotency, evidence and individual mandates, then starts each execution immediately. | A durable wait before starting and a multi-source execution contract. |
| Batch selection | [ConversationBatchWindow](../src/business-platform/Services/ConversationBatchWindow.cs) has a tested bounded, contiguous selection rule with PR-owned task and agent-instance scope and actual UTF-16 text/separator bounds. A source without a task identity is never selected into a batch: it is returned as `IndividualMembers` when it starts a window, or remains a boundary after an owner-bound prefix. It is not sent for clarification solely to obtain a work-item assignment. The approved 10-second, 3-message and 2,000-code-unit ceilings are startup-validated under `ConversationBatching`, but the feature remains disabled. The freeze primitive rejects individual members, reapplies the limits, verifies the first database-clock window is closed and checks selected identities, sequence, admission time, text, language, actor, skill and channel origin against PostgreSQL. It checks the next pending source when an in-window boundary stops selection, rather than silently accepting an omitted member. | The selector is unwired and does not populate the owner-backed task identity or prove it current. Freezing does not verify task ownership, current authority or dispatch readiness. |
| Request clarification | [Question persistence](../infrastructure/postgres/init/99zzz-wc134-request-clarification.sql) provides tenant-isolated, atomically frozen source membership bound to a canonical question and checked against actor, role, relationship version, agent, route, environment and sequence. The production inbound handler correlates a signed WhatsApp reply-context digest to a known delivered question and atomically records the decision with provider-claim acceptance through an owner-controlled function; direct application INSERT remains denied. | Production selection still does not create clarification questions. Durable intent lifecycle, answered-source re-entry, membership/access and mandate validation remain required; question freeze is not dispatch authority. |
| Work and recovery | The [runtime work directory](../infrastructure/postgres/init/89-wc134-runtime-work-directory.sql) uses owner-managed PostgreSQL work claims and current Identity checks; [runtime event worker](../src/business-platform/Services/ConversationRuntimeEventWorker.cs) recovers events from started executions. The [WhatsApp outbox worker](../src/business-platform/Services/WhatsAppOutboxWorker.cs) demonstrates leases and separate unknown-outcome reconciliation. A tenant-scoped [pending-start and membership schema](../infrastructure/postgres/init/99z-wc134-conversation-pending-start.sql) and [admission primitive](../src/business-platform/Services/ConversationPendingStartAdmission.cs) bind source, mandate, evidence and SEND identity transactionally and enumerate canonical order under a conversation lock. Database constraints require an atomic, immutable membership freeze. The [runtime claim fence](../infrastructure/postgres/init/99zz-wc134-pending-runtime-fence.sql) and event worker exclude pending starts while continuing to process eligible started work. | The primitive is not wired into SEND; freezing membership is not authority to dispatch and does not yet bind a request digest. No batch claim, dispatch or recovery worker exists. An event reader is not a start worker. |
| Runtime execution | [Professional Runtime](../src/professional-runtime/routers/conversation_execution.py) uses a deterministic Temporal workflow identity and checks the original request hash on replay. | The request, source and recovery contracts currently bind one original message and mandate, not all batch members. |
| Commercial metering | [WBE meter](../src/billing-engine/meter/service.py) resolves an authorized thread/provider mapping and records attributed immutable costs; [trial service](../src/billing-engine/trial/service.py) owns agent/version trial allocations. | Generation transport, accepted-offering/component allowance reservation and settlement are not integrated. |
| Operational cost | [Inference owner](../src/business-platform/Services/ConversationInferenceOwner.cs) and [WhatsApp traffic budget](../src/business-platform/Services/WhatsAppTrafficBudget.cs) reserve and account for usage; inference has original financial receipts. | Queries and locks use a service tenant; an environment-wide authority surviving tenant changes is not established. |

The existing [bounded resume reader](../src/business-platform/Services/ConversationResumeContextReader.cs)
is prior completed conversation context, not a pending-message batch. Do not describe it as batch
recovery. Reuse existing owners, PostgreSQL and Temporal; do not introduce a separate broker, a
second customer wallet or a channel-owned source of conversation truth.

## 3. Durable Conversation Batching

### 3.0 Current-scope disposition (2026-11-09)

The batching slice for this iteration is closed as a **design and safe-contract boundary**, not as
a customer-facing batching feature. The agreed and verified scope is:

- Keep the approved ceiling at 10 seconds, 3 messages and 2,000 combined UTF-16 code units,
  including newline separators; retain the separate 8,192-token check before any future
  provider dispatch.
- Reuse the bounded contiguous selector and durable PostgreSQL admission/freeze primitives.
  They remain groundwork: canonical SEND does not enqueue pending work, and no batch worker runs.
- Keep the versioned Professional Runtime batch model and OpenAPI components schema-only.
  Every source binds its original mandate/evidence and must identify the same PR-owned work-item
  ID and revision. The schema adds no route, owner verification, persistence, or dispatch authority.
- Require a pre-existing, owner-backed per-SEND work-item reference. If it is absent, use the
  existing individual SEND path; do not infer an association from relationship, skill or timing,
  and do not ask the customer to assign a work item solely to enable batching.
- Keep batching disabled. No current-scope claim is made for durable collection, delayed
  acknowledgement behavior, aggregate execution, production clarification, runtime recovery,
  offering metering or shared-spend integration.

The next batching iteration is deferred until the actual PR-owned source-to-work-item association
is available and can be verified at admission, freeze and dispatch. That iteration must integrate
the existing owners and adopt proven reliability mechanisms—idempotent admission, immutable
ordered membership, bounded windows, fenced leases, per-source authority checks and
unknown-outcome reconciliation—rather than add a second queue or guess at task identity. It must
then wire the collector, versioned multi-source dispatch, aggregate result projection and restart
recovery together and qualify them end to end in Docker before any enablement.

Customer-intent ambiguity and task ownership are separate gates. In a future eligible flow,
clarification may establish whether messages belong to one customer request; it cannot create or
replace a PR work-item identity, and neither a confirmed intent nor a work-item reference alone
authorizes dispatch.

### 3.1 Admission, scope and grouping

1. Retain the existing signed webhook, event-level replay, route, participant, Stop, CE evidence
   and canonical SEND checks. Commit the canonical message, original idempotency identity and
   durable pending-start record atomically, referencing the already persisted individual mandate
   and evidence. Where those owner records cannot share the admission transaction, validate their
   durable references before commit; an orphan mandate alone must never authorize dispatch.
   A replay returns the same message and never creates another queue member. Admission
   acknowledgement means **accepted**, not that processing or delivery completed.
2. Initially group only eligible relationship-bound WhatsApp text messages. Keep guest discovery,
   unsupported media and existing Web behavior unchanged unless separately brought into scope.
   The batch mechanism is channel-neutral below the adapter, but a channel must be explicitly
   enabled; it must not infer that guest traffic has relationship authority.
3. Use a configured, finite maximum wait, member count and combined UTF-16 text bound. A
   bounded time window starts at the first accepted member; later messages do not extend it
   indefinitely. Define and document the actual deployed settings during implementation, validate
   them at startup, and test exact boundaries. No arbitrary values in this document grant policy
   authority. A single valid message too large for the batching bound follows the existing
   individually bounded path, not silent truncation or rejection solely due to batching. Bounds
   apply to the exact combined string including separators and must also meet downstream input
   and tokenizer limits; 8,192 prompt tokens include wrapper and history. Validate the token
   limit with the approved tokenizer before provider dispatch, not a character approximation.
4. Select only a contiguous canonical sequence within the bound. Scope must match environment,
   tenant, relationship, conversation, participant and role, channel binding and recipient
   digest, admitted professional/instance, skill/version, language and all current
   authority-relevant revisions. Treat each message's own mandate and evidence as unique; do not
   compare whole mandate digests as if independent per-message mandates were identical.
5. Require a pre-existing PR-owner-backed work-item ID and revision on each source, and require
   every member in a batch to bind the same ID and revision. If this binding is absent, do not
   infer it from relationship, skill or timing and preserve the individual path. This task-owner
   gate is distinct from customer intent: if the intent boundary is uncertain, clarification may
   establish whether sources are one request, but cannot supply the work-item binding or dispatch
   authority. Different tasks, intervening canonical sequence, scope changes, long gaps, count or
   length bounds end the group; never skip an intervening member to build a batch. Preserve the
   canonical admitted text and order, including multibyte and UTF-16 boundary handling. Current
   WhatsApp admission trims inbound text before canonical SEND; this work must not claim
   byte-for-byte preservation of the original provider payload or change that unrelated existing
   behavior.
   The Founder approved the implementation ceilings on 2026-11-09: a 10-second maximum wait, at
   most 3 messages, and 2,000 combined UTF-16 code units with a newline separator. These values
   are configured under `ConversationBatching`, validated at startup, and remain disabled until
   the collector and dispatch path are integrated. The prompt-token limit remains a separate
   mandatory check.

   Founder clarification, 2026-11-09: when consecutive messages might represent either one
   request or separate jobs and that boundary is uncertain, ask the customer to clarify rather
   than guess. For example, "Make a Diwali post" followed by "Use a festive tone" can form one
   request when the boundary is established; "Also check my invoice" must prompt clarification
   if the system cannot establish whether it is part of the same request. The clarification
   and customer's response must be durable, replay-safe and associated with the relevant pending
   messages; Stop, revocation and deadline checks still apply while waiting. A clarification is
   not itself authorization to dispatch, and an unanswered or ambiguous response must not be
   treated as a confirmed task boundary. Do not incur unapproved provider traffic or spend to
   determine uncertainty.

### 3.2 Durable claim, dispatch and recovery

- Extend the BP-owned PostgreSQL work-capability pattern with a durable batch and immutable
  ordered membership, not an in-memory debounce or an unscoped transcript inventory. The
  admission transaction records pending membership; a transaction serializes grouping for the
  conversation and freezes the exact members before dispatch. Unique source membership and a
  database constraint prevent one source entering multiple active batches.
- Persist a stable batch/execution identity, due time, frozen source-list digest and a dispatch
  state. The minimum observable states are `WAITING`, `CLAIMED`, `DISPATCHING`,
  `STARTED`, `UNRESOLVED` and terminal states. Specify legal transitions, lease ownership and
  expiry in the implementation; retain original records even if a worker crashes. Multiple
  replicas claim with an owner-controlled atomic lease, current tenant/Identity authorization
  and fencing so an expired worker cannot commit a later conflicting transition.
- Before crossing the runtime boundary, persist the exact dispatch identity and request digest.
  Recheck current membership, participant/role, relationship, channel binding, skill/task,
  mandate, deadline and Stop for **every** member. Hold or fence the relevant owner authority
  through the dispatch decision, and recheck when resuming. Denial or revocation is explicit;
  never dispatch stale content or mark a denied member complete. Do not expose an old owner's
  history after reassignment.
- If a crash occurs before the persisted dispatch boundary, a newly authorized worker may resume
  the frozen work. If the boundary may have been crossed, use the same immutable identity to
  query the runtime's durable original execution and reconcile. An unknown outcome remains
  `UNRESOLVED`; a lease timeout is not proof of non-dispatch or permission to call a provider
  again. Only owner-confirmed non-dispatch permits a new dispatch.
- Extend the existing versioned BP/PR/AIR input and recovery contracts to carry an ordered,
  digest-bound list of canonical source references and original mandate/evidence identities.
  BP revalidates each original source and the exact combined input before generation. PR hashes
  the complete request and preserves it in its existing workflow; AIR verifies the bound input.
  Do not concatenate text under an anchor message's unrelated mandate or relax existing
  single-source contracts. Preserve compatibility for non-batched executions.
- Define one truthful aggregate result and project an explicit outcome for each original member.
  A shared reply is linked to the group without creating duplicate customer messages or replies;
  no child is marked complete until the owner-confirmed aggregate outcome warrants it. Partial,
  denied, stopped and unknown states remain visible under existing customer-facing semantics.
  Retention, deletion and legal-hold behavior must apply to every source and derived batch
  without copying content into an unrelated tenant or an unrestricted work directory.

## 4. Full Offering Metering

### 4.1 Commercial authority and attribution

WBE is the commercial owner. Resolve the exact active relationship, accepted contract and
commercial outcome to the immutable accepted offering/version and its WBE-authorized bundle
profile. For trial, bind the BP relationship trial record to WBE's exact customer,
professional type/version, active trial ID and eligible component allocation; check start,
expiry and conversion. Do not assume a participant UUID is an organisation UUID without an
owner-verified mapping. Do not select the newest bundle merely because it shares a tier if the
accepted contract bound a different version.

The component identity must come from an approved institutional thread/catalogue and actual
provider/adapter binding. Track tenant, customer, relationship, accepted offering or trial,
agent instance and version, skill and version, task/work item, component, invocation, reservation
and evidence references. Define the uniqueness scope from the real invocation contract: do not
assume one invocation can only ever have one component, or relax the existing ledger identity
until all callers and migrations establish the correct invariant. Never infer an approved price,
provider or allowance from a display name, sample bundle or default.

### 4.2 Reserve, dispatch, settle and recover

1. Before an eligible external or metered component dispatch, use an authenticated, authorized
   WBE-owned command to resolve the current entitlement and reserve the maximum allowed units
   and monetary exposure. Enforce concurrency atomically against the exact component allocation;
   exhaustion, absent mapping, expired trial, revoked offering or unavailable owner denies
   dispatch explicitly.
2. Bind the reservation to the exact invocation and immutable request/owner evidence. On
   exact replay return the same reservation; changed payload or attribution is a conflict.
   The commercial reservation and BP operational budget reservation are distinct, both required
   before provider dispatch. Persist their coordination state: if only one succeeds, recover or
   release it only with proof that no dispatch occurred. Never treat a network timeout as failure
   proof, manufacture an atomic transaction across services, or make a second provider call.
3. On a known terminal outcome, WBE records actual component units and separate raw and
   authorized marked-up cost in its append-only ledger and settles the exact reservation once.
   Preserve actual overrun and fence further admission where required. Release only with
   owner-confirmed non-dispatch; unknown usage retains the conservative reservation until
   authenticated reconciliation supplies evidence. Financial settlement remains possible after
   Stop without granting permission to release content or start new work.
4. Wire governed generation end to end through the existing BP/PR/AIR path and WBE private
   owner boundary with mTLS, signed delegated context and exact operation/body binding. Other
   offering components, including image, video, voice and channels, must use the same WBE
   contract whenever their supported production path dispatches them. Inventory and wire each
   existing in-scope dispatch surface; unsupported or unapproved components fail closed, not
   simulated as metered or silently excluded from the completion claim.

[DMA bundle definitions](../architecture/reference/billing/dma-bundle-definitions.md) explicitly
state Founder pricing authorization is pending. Repository implementation and synthetic tests
must not activate those prices or create live provider mappings. The trial schema and legacy
wallet assumptions require owner-verified migration and authority mapping, not a second BP
commercial ledger.

## 5. Environment-Wide Shared Spend Continuity

- Extend BP's existing operational owner with a stable environment and approved rolling
  accounting-window identity independent of the current service tenant or activation. Preserve
  original tenant, activation, attempt and receipt references for audit and settlement. Model
  and messaging reservation, settlement and overrun checks must all use the same environment
  authority and serialization lock, including during tenant or activation changes.
- Preserve the approved current policy: at most INR 500 combined model and messaging cost in
  the applicable rolling 24-hour window, or a lower active authority limit. Eligible
  customer-initiated WhatsApp direct replies remain zero provider-message cost under current
  policy; zero messaging provider cost does not make model or institutional compute free.
  Do not introduce paid proactive messages, templates or provider calls.
- Count settled actuals in the applicable rolling window and **all** unresolved reservations,
  even when their original reservation timestamp is older than that window, without
  double-counting the same attempt. An unknown attempt continues to reserve its maximum; expiry or a tenant switch
  does not release it. Record the entire overrun and block further dispatch under the same
  environment authority. Exact retries are idempotent and changed replays conflict.
- Design the owner-controlled migration for existing data, permissions, RLS and concurrent
  transition. Map legacy records to an authoritative environment/window without guessing; if
  records cannot be reconciled, fail closed and expose an operational reconciliation signal.
  Do not reset counters, rewrite financial history or grant broad cross-tenant access to the
  application. Existing original-tenant receipts remain usable after the switch.

## 6. Required Integration And Failure Contracts

| Boundary | Required behavior |
|---|---|
| Webhook to BP | One canonical message and pending member per provider event; changed replay conflicts. Existing acknowledgement, consent, sender and route checks remain intact. |
| BP batch owner to PR | Exact ordered source list, task and individual mandates are bound to one stable batch request and durable runtime identity. An old single-source caller still works. |
| PR to AIR and recovery | Combined input and every source are verified against BP owner evidence; hash, terminal result and fresh-authority recovery bind the same immutable request. No unrelated anchor mandate or blind redispatch. |
| BP/PR/AIR to WBE | Only authenticated, purpose-scoped private calls; WBE independently resolves accepted/trial commercial authority and component mapping, not a caller-supplied allowance or tariff. |
| WBE and BP operational budget | Independent durable reservations are coordinated before dispatch and reconciled on interruption. One owner cannot claim the other's reservation succeeded. |
| Stop, access and privacy | Revocation fences queued and recovering work; settlement of known spend remains possible without releasing customer content. No raw message, phone number, credentials or provider prompt in queue capability, budget or audit logs. |
| Customer outcome | Accepted, processing, completed, denied, stopped and unresolved states are truthful for each message. Missing authority or unknown results never masquerade as success. |

## 7. Completion Checks And Docker Qualification

All implementation is subject to existing WC-134 policy, authority and release gates. The Founder
subsequently authorized Docker behavioral testing; author and execute regressions with the work.
Synthetic providers, credentials and data only; no external provider traffic,
cloud mutation, activation or spend.

| Check | Required evidence |
|---|---|
| Grouping and bounds | Separate signed webhook arrivals within the configured window produce one bound execution and ordered canonical sources. Exact time/count/UTF-16 limits including separators, single oversized valid message, tokenizer limit, long gap, intervening sequence and different task/skill/participant/tenant never lose or improperly combine messages. |
| Durable ownership | Real PostgreSQL transactions exercise concurrent admission/claims, duplicate and changed webhook replay, worker crash before claim, before dispatch, after dispatch and before acknowledgement, restart, lease expiry and stale-worker fencing. Verify one source membership and no duplicate provider attempt. |
| Current authority | Revoke membership, role, binding, skill, task or relationship authority and trigger Stop before dispatch and across restart; each affected member is fenced. Verify reassignments never expose prior owner history. |
| Runtime and result | Actual BP/PR/AIR contracts bind every source, ordered text and mandate to a single execution; altered member or request digest is denied. Verify compatibility, terminal projection per member, partial failure, unknown runtime result and fresh-authority recovery. |
| Offering and trial | Actual owner-backed accepted contract/version and exact customer/agent/version trial select the correct authorized allocation. Test exhaustion, expiry, conversion, missing/invalid mapping, component identity, different customers/agents and concurrent last-unit reservations. |
| Generation and components | Exercise signed private transport through the production generation integration and each supported in-scope component adapter, including absent authority, forged context, exact replay, cost/units settlement, overrun and missing acknowledgement. No live provider. |
| Two-owner recovery | Crash or timeout between WBE and BP reservation, before socket, after socket and during each settlement. Assert no duplicate charge or provider dispatch; uncertain reservations remain until owner evidence resolves them. |
| Shared ceiling | Real PostgreSQL concurrency across model and messaging, tenant/activation switch, rolling-window boundary, old receipt settlement, uncertain usage older than 24 hours and overrun. Example: ₹400 already committed/reserved across both types leaves at most ₹100 under ₹500; changing tenant does not replenish it. |
| Migration and permissions | Fresh install and migration replay, upgrade with existing reservations, tenant isolation, RLS/owner-role privileges, deterministic legacy mapping and fail-closed unresolved migration. |
| Rollout and retained work | Crash after SEND commit but before provider-claim completion; replay returns one member. Disable batching and perform an upgrade/rollback with pending work; it remains recoverable. Mixed old/new spend writers are fenced. |
| Financial lifecycle | An unknown reservation remains counted beyond 24 hours; delayed settlement after trial expiry or provider deactivation uses original approved evidence, and exact replay does not add usage. Test component-unit and monetary-overrun accounting independently. |
| Final gates | Focused tests plus applicable full repository catalog/CI gates, warnings-as-errors and unchanged BP coverage thresholds of 90% line / 80% branch. Wire new tests into explicit release catalog commands where required; report exact commands, results and any skipped cases. |

Do not count unit-only mocks, selector tests, compile success or prior snapshot coverage as
integrated acceptance. Fix failures without weakening gates. Record actual versions, bounds,
outputs and exact-tree evidence in the PR and requirement ledger as required by their owners.

## 8. Delivery Sequence And Exit

1. Implement and qualify batch admission, multi-source authority, durable dispatch and recovery
   as one end-to-end change. Reuse existing ownership and verify all failure paths above.
2. Implement accepted-offering/trial resolution, authenticated component reservation and
   settlement, and generation integration. Wire other supported component dispatch paths; do
   not claim full integration while any supported path bypasses the commercial owner.
3. Implement environment-wide model/messaging continuity, including upgrade and tenant-change
   recovery. Connect both existing reservation paths to the same authority.
4. Run targeted then full applicable Docker qualification and direct author review. Resolve
   real quality-gate failures without bypassing hooks, signing or thresholds.
5. Make dependency-complete scoped milestone commits through normal hooks, preserve unrelated
   work, prepare the PR from the repository template and pass the exact-head precheck. Open a PR
   for Founder review; do not push directly to main, approve or merge it.

If a production owner record, immutable binding, approved tariff or exact migration authority is
missing, implement and test the fail-closed path and report the specific remaining activation
dependency. Such a missing record is not a reason to fabricate authority, mark the component
complete, or stop unrelated repository implementation. Live acceptance, provider enablement,
deployment and actual expenditure remain separately gated.

## 9. Implementation Map And Concrete Change Boundaries

This map names existing files and proposes cohesive new files; proposed names are implementation
targets, not claims that files already exist. Migration numbers are intentionally not reserved:
choose the next available ordered names after checking the whole init chain and concurrent work.
Do not edit an applied historical migration as the only upgrade path. The current uncommitted
WC-134 worktree is the baseline; integrate its changes rather than replacing them.

### 9.1 Batching: BP admission and persisted work

| File | Required change |
|---|---|
| [WhatsAppJourneyService.cs](../src/business-platform/Services/WhatsAppJourneyService.cs) | Keep provider signature, receipt/replay, sender routing and consent ownership; pass authenticated channel origin through canonical SEND. The parser carries signed reply context into the verified proof. A class-level handler now matches it to a delivered canonical question, rechecks route/actor/version, interprets only explicit `ONE`/`SEPARATE`, and records the decision atomically with the claimed provider event. Unknown references remain on the ordinary journey path; Stop and unsupported content do not resolve a question. Preserve existing non-clarification replay digests. Pending-message selection and delayed dispatch are not wired. |
| [ConversationService.cs](../src/business-platform/Services/ConversationService.cs) | Split eligible WhatsApp SEND after existing evidence and mandate creation: in the canonical message/execution/idempotency admission transaction insert pending-start work referencing the original mandate/evidence; return accepted without calling `StartAsync`. The shared conversation advisory lock is now acquired after current route and Identity checks and before assigning the canonical sequence. Pending admission is still unwired. Keep immediate single-message behavior when batching is disabled or ineligible. Preserve concurrent replay handling and ensure source outcomes remain tied to each original SEND. |
| [OperationalMandateResolver.cs](../src/business-platform/Services/OperationalMandateResolver.cs) | Reuse `ValidateExistingAsync` on **each** frozen source before dispatch and on recovery. Compare shared authority coordinates separately from source-specific mandate IDs, purpose, evidence and idempotency. Do not create a replacement mandate by concatenating text. |
| [ConversationBatchWindow.cs](../src/business-platform/Services/ConversationBatchWindow.cs) | The selector covers contiguous bounded selection, owner-backed task scope, and individual fallback when the task reference is absent; it contains startup-validated configuration defaults. Founder-approved ceilings are 10 seconds, 3 members and 2,000 UTF-16 code units with a newline separator; the feature remains disabled. Still wire the selector to canonical candidates and derive the shared authority fingerprint from verified scope. Its over-limit first candidate throws: handle a valid oversized message before selection via the single-message path, without truncation. |
| [ConversationRequestClarification.cs](../src/business-platform/Services/ConversationRequestClarification.cs) | The initial English question asks for explicit `ONE` (all together) or `SEPARATE` (each individually); other replies remain unclear. Canonical question creation is callable through the outbound owner but is not connected to the selector. Signed response correlation and atomic response/claim recording are implemented; unresolved provider references do not confirm a decision. Still implement source re-entry after a decision and explicit question expiration/resolution lifecycle. |
| [99zzz-wc134-request-clarification.sql](../infrastructure/postgres/init/99zzz-wc134-request-clarification.sql) and [ConversationOutboundContributionService.cs](../src/business-platform/Services/ConversationOutboundContributionService.cs) | `CommitClarificationQuestionAsync` persists canonical question/outbox, ordered source membership and freeze in one transaction under the shared conversation lock. It checks actor, role/version, agent, channel binding and recipient, contiguous source order, recorded evidence and unexpired original mandates; its idempotency digest binds ordered source IDs. This does not prove all current authority or connect selection to question creation. Question sources cannot be attached to a second question. The answer table denies direct application INSERT; a restricted SECURITY DEFINER function verifies route, Stop, provider claim and delivery reference, then records answer and accepts claim atomically. Integrate response-to-provider-claim references with retention and applicable data-right processing. |
| [ConversationStoreDbContext.cs](../src/business-platform/Infrastructure/ConversationStoreDbContext.cs) and [ConversationPendingStartAdmission.cs](../src/business-platform/Services/ConversationPendingStartAdmission.cs) | Transaction-bound pending insert and batch freeze primitives exist, and SEND acquires the shared conversation lock before assigning canonical sequence. Pending insertion remains unwired. Integrate it into SEND atomically with original mandate/evidence and idempotency; add persistent batch leases/dispatch receipts and bind source references/digests without duplicating plaintext. Preserve single-message execution and timeline behavior. |
| [99z-wc134-conversation-pending-start.sql](../infrastructure/postgres/init/99z-wc134-conversation-pending-start.sql), [99zz-wc134-pending-runtime-fence.sql](../infrastructure/postgres/init/99zz-wc134-pending-runtime-fence.sql) and a subsequent batch migration | Pending starts bind tenant-scoped canonical source, execution, mandate and SEND evidence with unique keys and RLS. Batch membership must freeze atomically with a contiguous member count and cannot be changed afterwards. The runtime fence excludes pending executions from event claims; deploy both migrations before the updated event worker. Add an owner-only minimal batch claim directory and request digest binding; add state and reference constraints, due indexes, row-level policies and least-privilege owner functions. Atomically claim due work with `SKIP LOCKED` and an incrementing fencing token. Reject stale lease updates. Keep migrations replayable and upgrade-safe. |
| [ConversationRuntimeWorkScope.cs](../src/business-platform/Services/ConversationRuntimeWorkScope.cs), [ConversationRuntimeIdentityAuthority.cs](../src/business-platform/Services/ConversationRuntimeIdentityAuthority.cs) | Reuse the owner-capability and current-membership patterns for batch claims, but distinguish pending start work from the existing event-consumption directory. A claim alone is not permission to read source text or dispatch. |
| Proposed `src/business-platform/Services/ConversationBatchDispatchWorker.cs` and [Program.cs](../src/business-platform/Program.cs) | Register a separately gated hosted worker and options. Claim due work, freeze ordered membership transactionally, validate each source, persist the exact dispatch identity/digest before the network boundary, and distinguish proven non-dispatch from uncertain dispatch. Resume `WAITING`/expired `CLAIMED` safely; reconcile `DISPATCHING` rather than blindly resending. |
| [ConversationBatchWindow.cs](../src/business-platform/Services/ConversationBatchWindow.cs), [Program.cs](../src/business-platform/Program.cs) and [appsettings.json](../src/business-platform/appsettings.json) | Startup binding and validation enforce the approved finite wait/count/text ceilings. `Enabled` defaults false and startup rejects true until durable collection and compatible dispatch/recovery exist, preventing stranded accepted work. Inspect actual retention/data-right processing and wire derived batch references into its owner path without promising deletion behavior not implemented. |
| [ConversationStopFence.cs](../src/business-platform/Services/ConversationStopFence.cs), [ConversationRuntimeEventIngestion.cs](../src/business-platform/Services/ConversationRuntimeEventIngestion.cs) | Integrate the existing Stop and current-access fences with pending and frozen members. Ensure the event worker does not claim a pending start as an already-started execution. Project each member's state from the same authorized aggregate terminal result; emit one reply, with no child marked complete on an unknown outcome. |

**Admission and freeze invariant:** a canonical SEND and its pending-start reference commit
together; the already-durable mandate and evidence must be verified before that commit. The
pending insert takes the conversation lock itself and verifies the message's environment, but
SEND must also take the same lock before assigning its canonical sequence. Freeze
uses the original canonical ordering under a per-conversation serialization boundary. The
member set and input digest never change after `DISPATCHING`. A late arrival creates another
batch. Lease owner, generation/fencing token and state must match on every mutation.

**Task constraint:** establish from the existing task-owning records an immutable task/work-item
reference and define the exact field mapping before enabling grouping. Founder-approved ownership:
BP Conversation owns a durable customer-confirmed request intent, distinct from a work item.
The intent records the exact source messages and the customer's boundary decision, scoped to
environment, tenant, relationship, conversation, agent instance, participant, role and original
route and authority revisions. It is not a work item, mandate or permission to dispatch. PR
continues to own execution and work items; every candidate SEND must carry a PR-verified work-item
ID and revision, and every member in a batch must bind the same ID and revision. BP must revalidate
that owner-backed reference at admission, freeze and immediately before dispatch. The current
relationship-level work-item projection does not bind individual messages to work items and is
not sufficient by itself. The current PR projection is backed by an in-process store; its
`record_work` method has no production caller, and no existing source-to-work-item association
was found. Therefore the required per-SEND owner-backed reference is currently unavailable:
do not derive it from the relationship projection, fabricate an association, or route such a SEND
into batch admission. Preserve that SEND's existing individual dispatch. The selector's task field
is not an authority source; skill and timing alone are not proof of same task. Where the source
record does not carry the PR-owned work-item ID and revision, exclude it from batch membership
and preserve the existing individual SEND path; do not prompt for or infer a work-item assignment
solely to enable batching. Preserve individual dispatch for demonstrably independent messages.
Do not promise this customer-facing behavior is active until an eligible real path has been
demonstrated.

The current [reference resolver](../src/business-platform/Services/ConversationContextProfileService.cs)
sets `SubjectType` to `EMPLOYMENT_RELATIONSHIP` and `SubjectReference` to the relationship ID;
`phase`, `skillId` and `ContextId` are not proven task identifiers. Extend the task-owning
admission/selection path and its source contract to provide a current, owner-backed task/work-item
reference when it exists; bind its version to each SEND and revalidate it at freeze and dispatch.
Do not silently treat the relationship ID as a task ID. A customer request that has not yet been
assigned a task cannot be grouped under this rule until an authorized task/intention identity
exists. An intent confirmation must bind the exact prompted source set and customer response;
it must survive restart and reject changed or ambiguous replay without inventing authority.
If the relationship or agent is ambiguous, resolve it before creating the intent. The current
WhatsApp sender directory has one route per service-tenant/sender; multi-agent selection through
one sender is not established by this decision and cannot be inferred. Demonstrate at least one real admissible
WhatsApp path with the required identity before claiming batch delivery.

**Webhook handoff:** [WhatsAppJourneyService.cs](../src/business-platform/Services/WhatsAppJourneyService.cs)
derives the canonical SEND key from the provider event, while provider-event claim completion is
a separate step. A crash after SEND commit but before claim completion must recover by replaying
the same SEND key, returning its retained pending member, and then completing the provider claim.
Do not couple provider acknowledgement to a worker's start or reply. A changed payload for the
same provider event is a conflict, and a lease retry must not duplicate a member.

**Scheduling and configuration:** assign `due_at = first accepted_at + configured wait` using
the database clock that orders durable admission. Include a later message only if its canonical
admission committed by the freeze transaction and is inside the window; serialize concurrent
admission and freeze on the same conversation key. A maximum count or length may make a batch
ready earlier, but must not skip the first eligible source. The current freeze primitive
conservatively waits until the first deadline even when a bound is reached; early readiness is
not yet implemented. Empty, disabled and ineligible paths
must preserve current semantics. Disabling batching must stop new enrollment without stranding
previously accepted pending work: retain a recovery worker until those records are terminal or
explicitly reconciled. A deployment rollback must either retain compatible readers/workers or
be blocked while pending batches exist.

**State transitions:**

| From | To | Required durable condition |
|---|---|---|
| `WAITING` | `CLAIMED` | Due batch claimed atomically with a new lease token; sources remain eligible for freezing. |
| `CLAIMED` | `DISPATCHING` | Frozen member list, stable execution identity and complete request digest committed; every source passes current owner and Stop checks. |
| `CLAIMED` | `WAITING` | Lease expires before dispatch intent, or explicit pre-dispatch failure is recorded; replacement claimant gets a higher fencing token and revalidates authority. |
| `DISPATCHING` | `STARTED` | Runtime confirms the exact persisted execution/request. |
| `DISPATCHING` | `UNRESOLVED` | Transport result is ambiguous; retain intent and reconcile the same identity, never resubmit merely because a lease expired. |
| `UNRESOLVED` | `STARTED` or terminal | Original runtime owner proves acceptance or a terminal result; result matches the frozen digest and current read authority. |
| `DISPATCHING` or `UNRESOLVED` | `WAITING` | Only if the authoritative runtime owner proves the exact request was not dispatched and current source authority is revalidated; record that proof. |
| `WAITING` or `CLAIMED` | terminal denied/stopped | Owner-confirmed Stop, expiry or revocation before dispatch; project truthful outcomes for affected sources. |
| `STARTED` | terminal | Owner-confirmed runtime terminal event is applied once to the batch and eligible source projections. |

Use the existing lock order for Stop, relationship, membership and execution where applicable;
document and test the complete order before adding locks. A database lock cannot by itself fence
a network call after its transaction commits. The committed intent, owner-side authority checks,
stable identity and runtime reconciliation must collectively cover that race.
The existing terminal-result reconciliation contract reports `UNKNOWN` and requests operator
reconciliation; it does **not** prove non-dispatch. Until a new authoritative absence/fencing
contract is implemented and tested, `UNKNOWN` remains unresolved and the return to `WAITING`
transition is prohibited. A transient 404, timeout, lost response, workflow query failure or
expired lease is not proof that no runtime accepted the start.

The original mandates have finite deadlines. Reject batch configuration whose wait cannot fit the
mandate lifetime, and check every deadline immediately before dispatch. If processing is delayed
past a member's deadline, preserve its original record and return a truthful non-dispatched
outcome; do not renew or reuse it silently. Any fresh authorization or re-submission must use
the existing authorized retry semantics and must not create another provider attempt for an
unknown original outcome.

### 9.2 Batching: runtime, recovery and contracts

| File | Required change |
|---|---|
| [HttpConversationExecutionGateway.cs](../src/business-platform/Services/HttpConversationExecutionGateway.cs) and its [reconciliation partial](../src/business-platform/Services/HttpConversationExecutionGateway.Reconciliation.cs) | Add a versioned batch request/recovery shape and authenticated request binding alongside the existing single-message route. Derive a stable batch execution/idempotency identity from persisted batch identity. Validate the runtime receipt against the frozen request, not just an anchor message. |
| [ConversationReconciliationService.cs](../src/business-platform/Services/ConversationReconciliationService.cs) | Extend original-source and fresh-reader recovery bindings to include the ordered member list and original individual mandates. Reconciliation may observe only the original runtime result and must not issue a new generation request. |
| [ConversationInferenceOwner.cs](../src/business-platform/Services/ConversationInferenceOwner.cs) | Replace the single-input assumption only for explicitly versioned batch requests: load frozen canonical members under owner authority, validate every original mandate and membership, recompute the exact combined bytes and source digest, and perform Stop/current-authority rechecks. Preserve the existing single-source checks and financial receipt ownership. |
| [conversation_models.py](../src/professional-runtime/routers/conversation_models.py), [conversation_execution.py](../src/professional-runtime/routers/conversation_execution.py) | **Groundwork only:** closed batch/member models validate ordered contiguous source identities, individual mandate/evidence binding, shared authority, exact joined text, UTF-16 bound, ordered source digest, and a common PR work-item ID/revision on every source. The OpenAPI components and model tests do not add a route, authenticate delegated context, prove the work-item revision with PR, persist requests, or authorize dispatch. Complete endpoint, replay/recovery and owner-backed identity binding here while preserving the existing single-message behavior. |
| [conversation_execution_workflow.py](../src/professional-runtime/workflows/conversation_execution_workflow.py), [conversation_dispatch.py](../src/professional-runtime/activities/conversation_dispatch.py) | Carry the batch source identity through Temporal input, activity validation and terminal events. Preserve deterministic workflow replay and version any behavior affecting already-running workflows; unknown dispatch remains reconciliation-only. |
| [conversation_generation.py](../src/ai-runtime/conversation_generation.py), [conversation_generation_owner.py](../src/ai-runtime/conversation_generation_owner.py), [conversation_generation_store.py](../src/ai-runtime/conversation_generation_store.py) | Bind the complete member list and combined input digest to the generation request, owner authorization and durable receipt. Verify owner response before socket use and fresh-owner content recovery; do not broaden single-source authorization. |
| [professional-runtime.openapi.yaml](../architecture/reference/api-specs/professional-runtime.openapi.yaml), [conversation-generation.openapi.yaml](../architecture/reference/api-specs/conversation-generation.openapi.yaml), [business-platform.openapi.yaml](../architecture/reference/api-specs/business-platform.openapi.yaml) | Specify versioned private batch and recovery shapes and exact errors; update public schemas only if a customer-visible shape changes. Update generated clients and contract tests only for changed public contracts. |
| [registry.yaml](../infrastructure/workload-identity/registry.yaml) | Add least-privilege route grants only if distinct batch routes are introduced; ensure methods, operation names, audiences and contract-major values match both signers and verifiers. Reuse existing authenticated routes only if their versioned schemas and authority are explicitly compatible. |

The current Python model hashes ordered source records and checks each mandate digest, but this is
not yet the shared cross-service canonicalization contract. Canonicalization must be specified
identically in BP, PR and AIR: ordered members, their source IDs, request/mandate digests, task
identity, language, exact text encoding and separator, combined input digest and schema version.
Publish shared test vectors in the relevant contract tests; never silently normalize or truncate
the customer text. The runtime execution identity must be stable over restart, while member
identities remain individually replayable.

**Execution and response mapping:** each existing SEND already has its own BP execution identity,
but PR currently exposes one `messageId` per execution and event. Add a separate batch execution
identity and a persisted one-to-many mapping to those original BP executions; do not overwrite or
reuse a child's original identity as if it represented the full batch. Freeze the mapping before
start. Project the single owner-confirmed result atomically to the mapped children and link one
professional reply to the batch while keeping each original SEND/replay queryable. Define
stream/cancel/retry behavior for both a member and its batch in the public and private contracts:
a member-specific cancellation must not be interpreted as permission to silently cancel or
complete another member. If independent cancellation cannot be honored once dispatched, return
the existing explicit conflict or batch-level action; do not fabricate separate execution.

Contract version selection must be explicit, not an optional list accidentally accepted by the
old single-source serializer. Mixed-version deployments must keep old requests working; a
batch-capable sender must fail closed if the receiver has not admitted the new version. Preserve
historical Temporal workflow decoding and replay, and validate both old and new versioned
histories in tests. Avoid exposing message text in the durable minimal work-claim directory.

### 9.3 WBE offering and component integration

| File | Required change |
|---|---|
| [relationship_workspace.py](../src/billing-engine/relationship_workspace.py), [main.py](../src/billing-engine/main.py), [private_server.py](../src/billing-engine/private_server.py) | Add private reserve, settle, release and read/reconcile commands under the existing workload-authenticated owner boundary; wire routing in the actual listener. Bind signed tenant, relationship, caller, operation, idempotency and body digest to the command. Do not expose a new unauthenticated public accounting endpoint. |
| Proposed `src/billing-engine/meter/allowance_service.py` | Implement transactional entitlement resolution and per-component reservation. Require exact WBE-owned accepted offering/version or exact active trial, valid catalogue/provider mapping and current allowance; lock the authoritative allocation before checking and reserving. Persist a canonical request digest and immutable owner/attribution references. |
| [meter/service.py](../src/billing-engine/meter/service.py), [wbe_interfaces.py](../src/billing-engine/skeleton/wbe_interfaces.py) | Extend the existing append-only cost writer and interfaces to settle the exact commercial reservation with actual units, raw cost, markup and evidence. Define and test invocation/component uniqueness before changing the current ledger index; exact replay returns the original result, divergent replay fails. Do not pass an unverified caller-provided price as authority. |
| [trial/service.py](../src/billing-engine/trial/service.py), [RelationshipTrialService.cs](../src/business-platform/Services/RelationshipTrialService.cs) | Use the actual relationship-to-trial binding and WBE trial allocation to validate customer, agent/version, active status, expiry and component units. Add owner-verified identity mapping where necessary; do not use the legacy nominal wallet balance as an independently authorized allowance. |
| [bundle_engine.py](../src/billing-engine/markup/bundle_engine.py), [21c-ae01-paid-activation-ordering.sql](../infrastructure/postgres/init/21c-ae01-paid-activation-ordering.sql) | Trace accepted contract, payment/activation outcome and bundle-version ownership. Extend the owning path so a reservation resolves the **accepted** immutable version, not `ORDER BY bundle_version DESC` alone. Treat this SQL file as existing schema evidence; deliver any change in a new ordered migration. |
| Proposed `infrastructure/postgres/init/<next>-wc134-offering-usage.sql` | Add minimal owner-controlled accepted-offering binding, allocation/reservation and immutable settlement references as needed. Define exact idempotency and concurrency constraints, foreign keys, RLS/grants and append-only behavior. Explicitly handle existing rows and migration replay; no seeded prices or fabricated approvals. |
| Proposed `src/business-platform/Services/AuthenticatedOfferingUsageGateway.cs`, [ConversationInferenceOwner.cs](../src/business-platform/Services/ConversationInferenceOwner.cs), [ConversationInferenceController.cs](../src/business-platform/Controllers/ConversationInferenceController.cs) | Use BP's existing signed workload client pattern to coordinate WBE reservation with operational reservation. Persist both IDs and coordination state before provider dispatch; settle/reconcile each owner independently. Handle Stop, lost acknowledgements and pre-dispatch release without granting redispatch. |
| [conversation_generation.py](../src/ai-runtime/conversation_generation.py), [conversation_generation_owner.py](../src/ai-runtime/conversation_generation_owner.py) | Keep generation behind the authenticated BP inference owner; propagate and verify the combined permit/receipt shape needed for both reservations. Do not let AIR mint WBE allowance or call a provider before both owners allow the attempt. |
| [content_service.py](../src/digital-marketing-agent/digital_marketing/content_service.py), [CTG gateway](../src/trust-layer/ctg/gateway.py), other discovered production adapters | Inventory actual component dispatch entry points and their production wiring. Replace or wire provisional usage interfaces through the authenticated owner contract where those paths are enabled; retain existing CTG/CE/provider controls. A protocol or mocked call alone is not evidence that an adapter is metered. |
| [wbe-relationship-workspace.openapi.yaml](../architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml), [registry.yaml](../infrastructure/workload-identity/registry.yaml) | Define exact private command and response/error schemas, operation IDs and least-privilege BP-to-WBE route grants. Update signed-route and contract tests, deployment identity configuration and any generated bindings affected by the actual contract. |

For each reserve command, the stable identity binds component, invocation, accepted
offering/trial, request digest, customer/tenant/relationship, agent/version, skill/version and
work item. Store owner-resolved unit maximum, price/rate version and expiry. `RESERVED` can become
`SETTLED`, `RELEASED` only on evidenced non-dispatch, or remain unresolved; the allocation lock
and settlement append occur in one WBE transaction. The exact handling of a component with
multiple events per invocation must follow the verified adapter contract, not an assumed key.

**Two-owner sequence:** persist a coordinator intent, reserve at WBE, then reserve at the BP
environment budget; persist the returned immutable IDs and request digests. Both confirmed permits
and fresh authority are required before the provider boundary. If either call times out, reconcile
that exact owner identity before proceeding. If the second owner denies and the provider boundary
is provably un-crossed, release the first reservation using its non-dispatch evidence. After a
possible dispatch, retain both reservations until the original attempt's usage or non-dispatch is
proved. Settlement retries query and complete each owner independently; do not make a distributed
transaction or assume a successful response was durably stored by the caller.

**Replay after expiry or revocation:** lookup an existing reservation by immutable identity before
considering a new admission. A known exact settlement or reconciliation remains readable through
the authorized financial recovery path even if the offering, trial or provider mapping later
expires; a current eligibility failure must not make an already-incurred cost disappear. A fresh
reservation still requires current entitlement. Store the original approved catalogue, provider
and rate references with the reservation so settlement does not reprice historical usage using
today's catalog. The current [meter](../src/billing-engine/meter/service.py) resolves active
mapping before ledger replay and needs this behavior explicitly corrected when integrated.

**Units and period:** component ration units and monetary paise are distinct. Reserve conservative
units in the allocation's actual owner-defined billing period; the trial's grant and consumption
must be updated under the same lock as its reservation. Record how actual units are derived for
each supported adapter, including token-based generation versus per-invocation catalogue units.
Unmetered/local or included components still require their explicit approved costing and entitlement
rules; no implicit unlimited allocation, zero compute cost or conversion of trial units to nominal
rupees. A partially consumed or overrun result must not violate a trial ledger constraint or hide
overrun: record full actual evidence and fence further usage, with the owner-defined excess
handling explicit.

### 9.4 Shared environment spend

| File | Required change |
|---|---|
| [WhatsAppGuestTrafficBudget.cs](../src/business-platform/Services/WhatsAppGuestTrafficBudget.cs) | Keep guest session/message and rate-limit policy intact. Separate any per-tenant traffic-count lock from a stable environment-wide **monetary** lock; do not inadvertently change unrelated guest counters. |
| [WhatsAppTrafficBudget.cs](../src/business-platform/Services/WhatsAppTrafficBudget.cs) | Update both registration and customer outbound monetary reservation paths to call the same environment budget owner as inference. Preserve the current free customer-reply policy, per-activation limits and provider eligibility; include legacy original reservations across a tenant switch. |
| [ConversationInferenceOwner.cs](../src/business-platform/Services/ConversationInferenceOwner.cs) | Replace tenant-scoped `CommittedModelSpendAsync` and monetary `LockKey` use with the shared environment owner for reserve, settlement, overrun and receipt recovery. Maintain original budget tenant attribution and settlement after Stop; do not permit inference based only on the WBE commercial reservation. |
| Proposed `src/business-platform/Services/ConversationEnvironmentSpendOwner.cs` | Centralize environment/window key derivation, exact integer-paise accounting, lock acquisition, reserve and settle/reconciliation checks. All callers use the same lock order and owner API. Account for an attempt once: settled actual replaces its outstanding reservation; unknown retains the reservation. |
| Proposed `infrastructure/postgres/init/<next>-wc134-environment-spend.sql` | Add a narrowly privileged owner-managed environment directory and durable references for model and messaging attempts; maintain immutable audit attribution and secure owner routines for cross-tenant totals. Migrate or map eligible legacy rows exactly once using authoritative environment/activation records. If historical environment or cost cannot be proven, retain a blocking reconciliation record rather than reset or guess. |
| [ConversationInferenceEvidence.cs](../src/business-platform/Services/ConversationInferenceEvidence.cs), [ConversationModelCostTests.cs](../tests/business-platform.Tests/ConversationWhatsAppFitness/ConversationModelCostTests.cs) | Bind operational evidence to the stable environment/window, original attempt and computed cost; extend tests for exact paise and full overrun. Avoid content or credentials in evidence. |

Use the policy's rolling 24-hour accounting window, not a calendar-day shortcut. At a supplied
clock instant, define one boundary consistently for both kinds of spend and assert it at the
exact cutoff. A single transaction-scoped lock serializes both reservation paths for the same
environment; tenant or activation changes cannot produce another lock or fresh balance.
Migration and reconciliation must preserve outstanding unknown attempts even after their nominal
expiry. Apply the same lower current authority limit consistently without granting authority to
an expired activation.

The existing model sum filters on `reserved_at > now - 24 hours`, including `RESERVED` rows;
that query does not meet the unresolved-reservation requirement after 24 hours. Replace it for
**all callers**, not just the inference path. Establish an authoritative timestamp for settled
actual usage and apply one documented rolling-window rule consistently; preserve old
unresolved reservations outside the window until settled or proven non-dispatched. Overrun
fencing remains active until an explicit owner-authorized recovery, not merely a time cutoff.
Use checked integer paise conversion for existing INR decimal records and fail closed on
non-integral or unverifiable conversions.

The existing PostgreSQL budget regression in
[WhatsAppTrafficBudgetPostgresTests.cs](../tests/business-platform.Tests/ConversationWhatsAppFitness/WhatsAppTrafficBudgetPostgresTests.cs)
currently inserts a `RESERVED` model attempt older than 24 hours and expects it to be excluded.
Replace that expectation as part of the shared-owner implementation: prove that the old
unresolved amount remains counted, that settlement replaces rather than adds to its reservation,
and that settled usage enters or leaves the window according to the agreed authoritative usage
timestamp. Include exact-cutoff and tenant-switch cases; do not treat a timeout or age as proof
of non-dispatch.

For rollout, a mixed fleet using old tenant locks and new environment locks would allow
overspend. Ship and validate an upgrade strategy that prevents old writers from reserving once
the new authority is active: a database-enforced version fence or an explicitly controlled
quiesce-and-switch with zero old writers. The migration must serialize with in-flight
reservations and map the existing 24-hour exposure **plus all unresolved older attempts**
before admitting new work. Test mixed-version rejection, migration interruption and rollback;
do not rely on synchronized application restart alone.

### 9.5 Tests, integration gates and delivery files

| File | Add or update |
|---|---|
| [ConversationBatchWindowTests.cs](../tests/business-platform.Tests/Conversation/ConversationBatchWindowTests.cs), [ConversationServiceTests.cs](../tests/business-platform.Tests/Conversation/ConversationServiceTests.cs) | Scope and task matching, exact bounds, oversized individual path, transactional admission, configuration-off compatibility and concurrent SEND replay. |
| [WhatsAppGuestSessionPostgresTests.cs](../tests/business-platform.Tests/ConversationWhatsAppFitness/WhatsAppGuestSessionPostgresTests.cs), [WhatsAppRelationshipSafetyRoutingPostgresTests.cs](../tests/business-platform.Tests/ConversationWhatsAppFitness/WhatsAppRelationshipSafetyRoutingPostgresTests.cs) | Exercise separate signed webhook arrivals, replay and current binding/Stop without changing guest behavior. Add a dedicated batch PostgreSQL fixture if these existing fixtures do not own relationship execution. |
| [ConversationRuntimeAuthorityPostgresTests.cs](../tests/business-platform.Tests/Conversation/ConversationRuntimeAuthorityPostgresTests.cs), [ConversationRuntimeProjectionPostgresTests.cs](../tests/business-platform.Tests/Conversation/ConversationRuntimeProjectionPostgresTests.cs), [ConversationReconciliationPostgresTests.cs](../tests/business-platform.Tests/Conversation/ConversationReconciliationPostgresTests.cs) | Claims, crash/fencing, per-member current authority, aggregate projection and unknown-dispatch fresh-reader recovery on real PostgreSQL. |
| [test_conversation_execution.py](../tests/professional-runtime/test_conversation_execution.py), [test_conversation_dispatch_temporal.py](../tests/professional-runtime/test_conversation_dispatch_temporal.py), [test_conversation_generation.py](../tests/ai-runtime/test_conversation_generation.py), [ConversationInferenceOwnerPostgresTests.cs](../tests/business-platform.Tests/Conversation/ConversationInferenceOwnerPostgresTests.cs) | Cross-language digest vectors, reordered/tampered sources, deterministic Temporal replay, exact batch recovery and real owner authorization. |
| [test_meter.py](../tests/billing-engine/test_meter.py), [test_trial_postgres.py](../tests/billing-engine/test_trial_postgres.py), proposed `tests/billing-engine/test_offering_usage_postgres.py` | Actual schema/roles, exact accepted and trial mappings, atomic allowance exhaustion, component replay, ledger append and uncertain settlement. Use a disposable synthetic PostgreSQL database and test migration replay. |
| [WhatsAppTrafficBudgetPostgresTests.cs](../tests/business-platform.Tests/ConversationWhatsAppFitness/WhatsAppTrafficBudgetPostgresTests.cs), [ConversationInferenceOwnerPostgresTests.cs](../tests/business-platform.Tests/Conversation/ConversationInferenceOwnerPostgresTests.cs) | Shared environment lock and sums across both owners and service tenants, old-receipt settlement, rolling boundary, concurrent requests, overrun and unknown outcomes. |
| [engineering-validation.yaml](../validation/engineering-validation.yaml), [run_release_qualification.sh](../scripts/run_release_qualification.sh) | Inspect exact gate selectors; wire any new PostgreSQL/integration tests into an applicable Docker gate that actually runs in CI and release qualification. Existing explicit file lists do not automatically collect new files. Do not replace a real integration test with a skipped unit run. |
| [WC-134-requirements.yaml](./WC-134-requirements.yaml), [WC-134 parent](./WC-134-whatsapp-demo-complete-rollout-work-component.md), this component | Update traceability, exact-tree test evidence and residual risks when implementation is done; do not mark a requirement passed from a plan. Recompute any repository-required digests and validate the ledger. |
| [pull_request_template.md](../.github/pull_request_template.md), [prepare_pr_body.py](../scripts/prepare_pr_body.py) | At the delivery stage preserve the full template, include exact Docker commands and outcomes, run the required prepared-body exact-head/worktree precheck and submit only after applicable gates pass. |

### 9.6 Implementation sequencing and checkpoints

| Step | Dependency-complete exit |
|---|---|
| A0. Current batching scope (closed 2026-11-09) | Bounded selector and durable admission/freeze primitives remain unwired; the runtime batch model/OpenAPI components are schema-only and require a common PR-owned work-item ID/revision. Missing per-SEND owner binding falls back to individual dispatch; batching remains disabled. This closes the current design/safe-contract slice only, not a production feature or completion of WC-134. |
| A. Deferred batch contracts and persistence | Establish the real per-SEND task-owner binding, define the aggregate state machine and cross-language canonicalization vectors, and complete owner-controlled persistence. Do not route an eligible production path to a queue without a functioning worker. |
| B. Batch dispatch and recovery | Signed webhook to canonical admission, durable wait/freeze, per-member validation, runtime dispatch, terminal projection and restart/reconciliation pass together in Docker against PostgreSQL. |
| C. Commercial authority and generation | WBE reservation/settlement owner, accepted/trial binding, private transport and actual generation call path pass the two-owner crash/replay tests. Inventory every supported component path and wire or explicitly fence each. |
| D. Shared operational ceiling | Both model and messaging paths use the same environment authority, upgrade/replay and cross-tenant concurrency tests pass; no second budget or reset. |
| E. Qualification and PR | Relevant full catalog gates, direct author review, scoped commits, template and exact-head precheck complete. Failures or absent live approvals remain visible, not relabelled as completed. |

Step A0 is the only batching checkpoint closed in the current iteration. Steps A through E remain
deferred or incomplete; batching is not customer-complete or enabled until the integrated exits
pass. Existing test results qualify only the code snapshots actually tested.

## 10. Critical Review Disposition And Implementation-Ready Boundaries

| Finding | Disposition before or during implementation |
|---|---|
| Current SEND resolves the relationship as its interaction subject, not a task. Grouping by skill or relationship could mix unrelated requests. | Current scope is closed without production batching. A later iteration requires the existing PR-owner-backed work-item ID and revision on each SEND and revalidates it before dispatch. If the customer request boundary is separately uncertain, clarification may resolve intent but cannot manufacture task identity. Until the owner binding exists, retain individual dispatch; do not treat the selector as completion of the customer batching goal. |
| Provider event claim and canonical SEND commit are separate. A crash between them can leave an acknowledged-looking gap or duplicate work if retried incorrectly. | Section 9.1 requires the original deterministic SEND key, retained pending member and explicit claim completion on replay. A real PostgreSQL webhook crash test is mandatory. |
| A lease or runtime `UNKNOWN` cannot prove that a call never started. | Section 9.1 prohibits redispatch unless a new owner-authoritative absence/fencing contract proves non-dispatch. Until then keep an unresolved outcome, not a success or retryable provider attempt. |
| Existing PR execution and recovery contracts bind one message, while each SEND already has an execution ID. | Section 9.2 requires a separate aggregate identity, immutable mapping to every original execution, compatible versioned contracts, per-member projection and explicit member cancellation behavior. |
| Per-message mandate deadlines can expire while the queue waits or the system is down. | Validate configured wait against authority lifetime, recheck each deadline, and surface a non-dispatched outcome without silently extending authority. |
| Existing cost replay checks current provider mapping first; already-incurred usage must remain settleable after eligibility changes. | Section 9.3 pins reservation-time authority and separates financial recovery of an existing attempt from fresh admission. |
| Existing model spend sum uses a 24-hour timestamp filter even for still-reserved unknown attempts. | Section 9.4 counts unresolved reservations beyond the rolling window, across tenant changes, and fences mixed-version writers. |
| A cross-service pair of reservations is not atomic; provider effects cannot be undone by a timeout. | Section 9.3 specifies a durable two-owner coordinator, exact reconciliation, non-dispatch evidence for release and no blind retry. |
| Previous wording implied provider text is never changed; WhatsApp currently trims before canonical admission. | Section 3 preserves the existing canonical text and does not claim raw provider-byte preservation. The combined UTF-16 bound includes separators, and tokenizer limits are verified separately. |

These are corrected design requirements, not proof of implementation. The exact task-owner
source, immutable accepted-offering binding and component-to-unit mappings remain implementation
discovery and integration work. If the necessary owner authority does not exist, implement the
observable fail-closed boundary and record the precise missing owner capability; do not invent
one or declare the requested customer outcome complete.
