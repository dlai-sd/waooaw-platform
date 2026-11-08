# WC-134 Runtime Generation And Owner Reconciliation Policy

## 1. Record And Approval Boundary

| Field | Value |
|---|---|
| Parent | [WC-134](./WC-134-whatsapp-demo-complete-rollout-work-component.md), R006/R007/R008/R012 |
| Author | Platform IT Expert, INST-010 |
| Status | FOUNDER-APPROVED IMPLEMENTATION DESIGN; NOT AN ACTIVATION OR COMPLETION CLAIM |
| Founder direction | Current conversation, 2026-11-07: prepare the missing governed backend/policy for approval; add explicit fresh-authenticated owner reconciliation without redispatch |
| Founder approval | Recovered prior-session direction "approved, proceed with next steps"; reconfirmed on 2026-11-08 by selecting "Resume the approved runtime work" and explicitly granting current-session implementation authorization |
| Existing implementation authority | Current-session repository implementation explicitly authorized on 2026-11-08; specification approval, provider, deployment, expenditure and live-acceptance gates remain independent |
| Delivery boundary | Repository implementation; Docker compilation/static checks during implementation; behavioral tests only after all stories are implemented |

This supplement records the approved execution and recovery design. It does not amend an ADR,
admit a professional artifact, configure a provider, authorize expenditure, or approve deployment.
Approval selects this implementation design. Activation still requires exact-candidate evidence
and the parent's separately authorized live acceptance for both journeys.

## 2. Verified Gap And Required Separation

At the approval baseline, the PR conversation coordinator sent every accepted text contribution
to AIR as an `INDUCTION_CONTEXT` employment patch. AIR's configured default interpreter reported
model unavailability. Neither constituted a general professional response implementation.

The current CTG defaults are not an acceptable production substitute: its default CE transport
is insecure, its default audit writer logs instead of durably recording evidence, and its
registry/vault clients do not implement the required delegated-context boundary. The registry
client also expects fields/naming not supplied by the current public provider DTO.

Implement two explicit, independently validated operations:

| Operation | Owner/result | Forbidden inference |
|---|---|---|
| Ordinary admitted-skill conversation | PR executes the exact admitted professional skill; AIR returns bounded generated content | A reply does not prove a business action, readiness change, billing outcome, or CE evidence |
| Employment contribution interpretation | Existing AIR typed proposal contract; BP independently validates any proposed changes | Ordinary conversation is not silently classified as an induction update |

PR selects an operation from the accepted skill's declared input/output contract and permitted
actions, not from channel-specific heuristics or model text. Missing or ambiguous declarations
produce an explicit unavailable/unsupported outcome. Add no profession-specific business logic
to BP, PR, or AIR; retain admitted professional adapter ownership.

Sources: [PR coordinator](../src/professional-runtime/routers/conversation_execution.py),
[AIR interpreter configuration](../src/ai-runtime/employment_patch.py),
[CTG](../src/trust-layer/ctg/gateway.py),
[provider API](../src/business-platform/Controllers/ProvidersController.cs),
[PR responsibility](../architecture/reference/components/professional-runtime.md),
[AIR responsibility](../architecture/reference/components/ai-runtime.md).

## 3. Approved Governed Backend And Policy Binding

Use the existing PAL/PSE selection contract from
[ADR-029](../adr/ADR-029-multi-provider-llm-strategy.md), through the
[ADR-042 CTG pipeline](../adr/ADR-042-provider-registry-constitutional-tool-gateway.md).
Do not directly enable the current PSE stub/router or bypass CTG.

1. Resolve the exact ACTIVE admitted skill and its professional adapter.
2. Resolve prompt policy by the original mandate's prompt version and digest.
3. Resolve model policy from the admitted professional specification and its explicit immutable
   policy binding. A specification digest is not itself a model/provider policy.
4. PSE intersects its mandatory rules with that policy's allowed providers, regions, models,
   tiers and fallbacks. No hardcoded provider choice in the conversation coordinator.
5. Registry-owned endpoint/authentication settings select the concrete PAL adapter. Implement
   only declared, policy-allowed adapters. A missing adapter is unavailable, not a free fallback.
6. Preserve mandatory language/domain routing, residency and plan-tier constraints. LOCAL Ollama
   is eligible only where those rules permit it; its repository default model tag is not an
   immutable artifact identity. No policy implies that LOCAL always satisfies every request.
7. A fallback is a separately admitted dispatch with its own remaining-budget reservation and
   durable evidence. Never fallback after an unknown primary outcome.

The activation binding must contain provider identity, endpoint/configuration digest, exact
model/version or artifact digest, region, tokenizer/version, prompt reference/version/digest,
model-policy reference/version/digest, rate-schedule digest and validity interval. Resolve these
from approved owner records; do not fabricate digests, infer approval from a tag, or load API
keys from AIR environment variables.

No concrete provider is enabled by this approval. Unresolved binding coordinates fail closed.
Model credentials remain in the protected vault and are injected only at the socket boundary.
External-provider prompts require the existing C-078 scrubber contract; missing scrubbing
capability prohibits external dispatch. A self-hosted provider is exempt only when its registered
deployment actually stays within the institutional boundary.

## 4. Approved Bounds And Monetary Accounting

These are Founder-approved upper bounds, not independently spendable allowances:

| Bound | Approved value and enforcement |
|---|---|
| Prompt | At most 8,192 tokens including system wrapper and bounded context; use the bound tokenizer, never a character-count approximation |
| Generation | At most 2,048 output tokens; enforce the provider limit and verify reported usage |
| Canonical text | Existing 32,000-character BP bound; no silent truncation |
| WhatsApp | Existing 4,096-character bound; preserve full Web output and send bounded portal guidance |
| Provider attempt | 30-second deadline; caller cancellation and Stop propagate |
| Concurrency | Initially one active model attempt per environment and per tenant; queued work remains durable |
| Demo daily cost | At most INR 500 combined messaging/model cost, using the same approved environment/day authority and reservations, not independent INR 500 pools |
| Customer initiation | Existing consent, service hours, inbound/window, traffic and STOP rules remain controlling |

Reserve the conservative maximum cost before dispatch from approved input/output rates and
token limits, rounding upward to integer paise. Local provider billing of zero is not evidence
that institutional compute costs are zero. Missing rate/cost evidence denies monetary admission.
CE receives the current contract/Decision Space and owner-confirmed budget context; it must
explicitly allow the proposed action and bound. AIR cannot grant its own budget.

The budget owner records reservation, actual usage and settlement with tenant, environment/day,
original execution/attempt identity, policy/rate digests and CE evidence references. Store no
prompt, credential or phone number in accounting records. Concurrent reservations must serialize
on the shared ceiling. Unknown usage retains the full reservation. A reported overrun is recorded
in full and halts further dispatch; never clamp spending to manufacture a passing ledger.

## 5. Durable Generation, Evidence And Unknown Outcomes

PR owns durable professional execution; AIR owns bounded inference responsibility. A separate
versioned generation contract must not masquerade as an employment patch.

- Persist exact request identity/digest, original authority/policy references and a queued
  receipt before returning acceptance. Inference never relies on a detached process-local task.
- Use durable PR workflow/activities and owner persistence. Short HTTP admission returns the
  receipt; subsequent activity polling reads that same accepted identity.
- Before socket dispatch, persist admission evidence, budget reservation and `DISPATCHING`.
  Unknown/crash recovery never interprets a `DISPATCHING` orphan as permission to call again.
- Recover `QUEUED` work only when there is proof that socket dispatch has not begun.
- Persist provider result reference, output digest and usage before signaling PR. Audit/usage
  persistence failure prevents successful result release.
- Reconcile lost acknowledgements from the persisted result. Provider-native reconciliation
  must be documented for each adapter; lack of a lookup/idempotency guarantee leaves `UNKNOWN`.
- An unknown provider outcome cannot trigger retry, fallback, settlement-to-zero, or completion.
  Expose an actionable operator reconciliation state with the original attempt identity.
- Use signed delegated context and mTLS for registry, CE, vault and runtime boundaries, following
  [ADR-046](../adr/ADR-046-workload-identity-and-service-authentication.md).
  Require explicitly injected production CTG dependencies; no logging-only audit or plaintext
  default client is a production success path.
- Record authorization/dispatch/result evidence through their owner APIs. Provider output never
  becomes BP `RECORDED` CE evidence merely because it was stored.
- Typed professional output reaches the existing ordered PR event stream. BP atomically commits
  message/card, receipt, checkpoint and eligible outbox; terminal failure remains truthful.
- Stop dominates queued/admitted work and suppresses late output. Cancellation of an in-flight
  request does not prove that the provider neither acted nor charged.

## 6. Explicit Fresh-Owner Legacy Reconciliation

Never populate missing original issuer/account/membership fields from today's membership.
Preserve the original execution, input, actor, request/idempotency identity and runtime cursor.
Fresh authority is a separate, time-bounded permission to read an existing result, not a renewal
of the original execution mandate.

Approved BP customer command:

`POST /api/v1/employment/relationships/{relationshipId}/conversation/executions/{executionId}/reconcile`

The closed request contains `schemaVersion`, `expectedMessageId`, and an owner-issued expected
projection version; use the existing idempotency/correlation headers. Tenant, recipient, private
endpoint, original actor and provider/mandate references are never caller-supplied authority.

Admission requires a freshly authenticated Identity session, current OWNER/MANAGER membership,
current relationship access and an explicit CE permission for `READ_EXISTING_RUNTIME_RESULT`.
The command must not confirm STOP, renew an expired generation mandate, apply a patch, or Start,
Resume, retry, signal an interpreter, or dispatch a provider call.

Store a separate reconciliation-authority record bound to the current requester, issuer,
account/membership, original execution and source digest, current relationship/Decision Space,
CE permission/evidence, expected projection version, idempotency identity and a five-minute
expiry. Original authority remains unchanged. A changed/revoked membership or expired permission
fences both canonical projection and later delivery.

The private read-only PR recovery contract carries distinct original-source and current-requester
coordinates with signed purpose `READ_EXISTING_RUNTIME_RESULT`. Do not impersonate the original
actor using a newly signed ordinary execution/stream request. PR returns only a durably stored,
exactly bound terminal result/events, or an explicit stopped, unavailable, unknown or conflict
outcome. It must not schedule work to manufacture a missing terminal.

BP uses a separate reconciliation permission mode for projection: it verifies the original
event/result identity and digest plus the fresh read-only permission. It does not pretend that
an expired original mandate is current. Receipt uniqueness still refers to original event
identity; repeated reconciliation cannot create duplicate messages or outbox sends.

WhatsApp delivery additionally needs the persisted original recipient/binding, current consent,
window, participant authority and fresh permission. If legacy original-recipient coordinates are
missing, the result is Web-only: never infer a destination from the current phone/binding.
Reconciliation does not copy or transfer a transcript. Unknown/missing results remain unresolved
with an operator next action; a new professional request requires separate explicit customer intent.

## 7. Connected Implementation And Regression Plan

| Step | Implementation surface | Required regressions |
|---|---|---|
| 1 | Versioned operation declaration and exact prompt/model-policy resolver; BP/PR/AIR contracts and generated clients | Ordinary reply is not induction patch; unsupported declaration; changed digest/policy; no provider call on failure |
| 2 | Explicit production CTG registry/CE/vault/audit clients, workload grants and PAL adapters | mTLS/signed tenant/actor/purpose; DTO shape; absent credential; CE non-ALLOW; unavailable audit; residency/routing constraints |
| 3 | Shared budget reservation/settlement and bounded tokenizer policy | Concurrent day/tenant reservations; exact token thresholds; combined messaging/model ceiling; unknown usage; full overrun accounting |
| 4 | Durable generation admission/workflow, provider-result persistence and read-only reconciliation | Crash before/after socket; lost receipt/result signal; no retry/fallback for unknown; usage/audit failure; Stop/cancel races |
| 5 | Fresh-owner reconciliation command, separate authority record and private terminal-result read | Changed requester/tenant; revoked membership; expired permission; divergent replay; no Start/interpreter/provider calls; missing legacy recipient stays Web-only |
| 6 | Integrated canonical projection/outbox and release wiring | Transaction rollback; final-expiry/Stop/binding races; cursor replay; no empty/SYSTEM success; full Web/bounded WhatsApp output; default-off compatibility |

Author regressions with implementation and perform direct author review across the complete
chain. Compile/type-check/static-lint only during these steps. After all WC-134 implementation
stories are complete, run the existing Docker behavioral runners against the exact candidate,
including real PostgreSQL and Temporal recovery/locking cases. Wire every new regression into
the explicit qualification commands. Compilation is not behavioral evidence.

Final review must verify permissions/ownership/RLS, transaction and lock ordering, resource
lifetime, idempotency, authority expiry, output/error shapes, provider unknown-state handling
and combined budget settlement. No review subagent or other office is invoked without the Founder.

## 8. Founder Decision

Approved design: the operation separation, registry/PSE/CTG backend binding, approved bounds,
durable accounting/result lifecycle, and explicit fresh-owner read-only legacy recovery above.
Approval permits implementing these additions; it does not supply unresolved provider/prompt
coordinates or activate them. Any conflict with admitted policy or an architectural authority
boundary remains an explicit blocker, never an unauthorized amendment.

The Founder approved this design and authorized resumption of repository implementation on
2026-11-08. The generation/legacy items remain incomplete until implemented and qualified.
The separate versioned generation and read-only recovery wire contracts are published in
Conversation Core sections 4.1-4.2 and AI Runtime section 1.1. On 2026-11-08 the Founder delegated
the detailed contract selection ("you decide", no revisions); the published contracts were
selected unchanged within this approved design. Unresolved activation bindings remain fail-closed; this approval supplies no
provider credentials, immutable model/prompt coordinates, spend authority or live activation.

### 2026-11-08 continuation checkpoint

Work continues in `/workspaces/waooaw-platform-wc134`, branch
`ib/134/whatsapp-demo-complete-rollout`, on the errored session's uncommitted implementation.
No prior changes were reset or discarded.

The immutable admission declaration and BP-to-PR mandate binding are implemented for explicit
professional-response versus employment-interpretation operations. Both owners enforce exact
schema/prompt binding and admitted actions. Interpretation uses the declared patch type and actual
model-policy reference, not the professional specification digest. Legacy mandate serialization
omits the additive declaration and preserves its existing digest.

Missing declarations fail before AIR admission for new work. The still-unimplemented governed
generation backend produces an explicit unavailable outcome rather than an employment patch or
professional success. Pre-policy workflows retain read-only reconciliation and cannot be
redispatched or reclassified as a confirmed failure. An independent durable dispatch-policy marker
distinguishes new work without rewriting original mandates.

Regressions are authored in the existing admission, mandate-resolver and PR execution suites,
including policy drift, operation separation, declared patch selection, legacy serialization and
pre-policy unknown outcomes. Behavioral execution remains deferred. The new Python regressions
are inside the existing explicit service-integration selector; no new test-file discovery is assumed.

Static evidence:

- Existing Docker .NET runner: `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-operation -warnaserror`
  PASS, zero warnings/errors, after repairing an inference-policy type-name collision.
- Docker Ruff checks on changed PR source and tests PASS; Python syntax and JSON/OpenAPI parsing
  PASS. These checks execute no behavioral tests and prove neither model output nor recovery.
  Final commands inside that runner:
  ```sh
  ruff check src/professional-runtime/routers/conversation_models.py src/professional-runtime/routers/conversation_execution.py src/professional-runtime/activities/conversation_dispatch.py tests/professional-runtime/test_conversation_execution.py
  PYTHONPYCACHEPREFIX=/tmp/wc134-syntax python -m compileall -q src/professional-runtime/routers/conversation_models.py src/professional-runtime/routers/conversation_execution.py src/professional-runtime/activities/conversation_dispatch.py tests/professional-runtime/test_conversation_execution.py
  ```

Whole-chain generation, private registry/vault/audit/budget integration, tokenizer/monetary
admission, provider-result persistence, fresh-owner reconciliation and integrated qualification
remain incomplete. No provider/model is enabled, no external request or deployment occurred, and
R006/R007/R008/R012 are not marked PASS.

The Founder subsequently authorized drafting and approved the internal interface detail:
"authorised for drafting and approval is given on draft". Section 9 records that delegated
selection. Missing internal contract detail is no longer an approval blocker. Missing actual
approved artifacts, provider activation and owner capability remain fail-closed; drafting an
interface does not create an active policy, credential, tariff or evidence record.

## 9. Private Owner Contract Selection

**Authority:** Founder-authorized drafting and approval of the draft, 2026-11-08.
**Boundary:** Existing BP registry/admission, protected vault, CE Audit Sink and monetary owners;
no new institutional office, ADR, deployment, credential creation or provider activation.
All objects below are closed, versioned `1.0` contracts. UUID identities and SHA-256 digests
are validated, not merely nonempty strings. Digests use `sha256:` plus 64 lowercase hex digits.
Missing or divergent coordinates are explicit unavailable/conflict outcomes.

### 9.1 Exact Immutable Policy And Registry Resolution

BP owns `POST /internal/v1/professional-inference-bindings/resolve`, internal only.
ADR-046 mTLS and a signed PR/AIR envelope bind current tenant, original actor, relationship,
execution/message, correlation, idempotency and purpose `RESOLVE_PROFESSIONAL_INFERENCE_BINDING`.
The closed request contains `schemaVersion`, `mandateId`, `mandateDigest`, `skillId`,
`skillVersion`, `inputSchemaDigest`, `outputSchemaDigest`, `promptPolicy` and `modelPolicy`.
The registry independently verifies the exact admitted artifact and its accepted skill binding.
It does not trust a submitted specification digest as a model-policy reference.

The closed resolution contains `schemaVersion`, `bindingId`, `bindingDigest`, `admissionDigest`,
`promptArtifact`, `modelPolicyArtifact`, `providerBindings`, `approvedAt`, `validUntil` and
`approvalEvidenceRef`. Each artifact has its exact `reference` (`ref`, `version`, `digest`) and
`content`; the reference digest hashes canonical content, not the reference itself.
Prompt content contains `schemaVersion` and nonempty `instructionText`, treated as data, not
executable template expressions. Model-policy content contains `schemaVersion`,
`permittedActions`, `allowedTiers`, `allowedProviders`, `allowedRegions`, `allowedModels`,
`allowedFallbacks`, `maximumPromptTokens`, `maximumOutputTokens` and `attemptTimeoutSeconds`.
Bounds can narrow, never enlarge, section 4. Empty permitted sets deny dispatch.

Each provider binding contains `providerName`, `adapterKind`, `endpoint`, `configurationDigest`,
`modelId`, `modelVersion`, `modelArtifactDigest`, `region`, `tokenizerReference`,
`rateScheduleReference`, `credentialRoutingReference` and `deploymentEvidenceRef`.
Actual immutable tokenizer, rate, deployment and credential routing records must be resolved
through their owning stores. A provider name, mutable model tag, environment API key or LOCAL
label is not such evidence. Provider settings stay private: the public provider DTO does not
acquire vault routing fields. Mandatory ADR-029 rules are intersected with this policy, not
replaced by a policy that happens to allow a provider.

The response digest binds the complete resolution excluding `bindingDigest`. Endpoint/authentication
changes require a newly approved binding. No source file, default seed, or invented digest may
stand in for an absent approved owner record. Recheck active admission and binding validity at
dispatch; a cache cannot extend approval or survive revocation as authority.

### 9.2 Credential And Durable Audit Boundaries

The existing protected vault/CTG boundary resolves `credentialRoutingReference` against the
selected provider binding and verified delegated tenant/relationship/attempt. The reference
selects an owner-approved route, not a caller-supplied URL, secret path or vault name.
Use the existing managed-identity Key Vault boundary with TLS for cloud secret retrieval.
Any internal service hop additionally requires ADR-046 workload authentication and the exact
registered credential-resolution purpose. Inject the credential only immediately before the
authorized provider socket; do not persist it in AIR, requests, results, accounting or logs.
Missing/expired credentials deny dispatch; no AIR environment-key fallback or implicit refresh.

CE remains the owner of `audit_sink.evidence_records` under ADR-044. CTG's production audit
writer must return an owner-confirmed `evidenceRecordId`, `evidenceDigest` and `recordedAt`
after the immutable insert commits. The proof binds original execution/attempt, CE decision,
policy/binding/request/output digests and execution/usage outcome. Raw prompts, output, credentials,
phone numbers and full vault paths are forbidden. Operational content stays in the existing
erasable payload boundary. Logging is not an audit acknowledgement. Lost acknowledgements are
reconciled by the same immutable identity/digest; they do not authorize a second provider call.

### 9.3 Shared Monetary Owner Commands

BP's existing operational traffic-budget owner is extended, not replaced with an AIR ledger.
Its private reservation and settlement commands bind the same environment, tenant, activation/
allowance and accounting window as messaging. WBE remains the commercial-allowance/billing owner;
an operational ceiling does not mint a commercial allowance.

`ReserveProfessionalInferenceV1` contains `schemaVersion`, original execution/attempt,
`requestDigest`, `providerBindingDigest`, `rateScheduleReference`, `budgetAllowanceRef`,
`maximumPromptTokens`, `maximumOutputTokens` and CE decision/evidence references.
The owner resolves the approved tariff and computes the conservative maximum; a caller's claimed
price is not authority. The tariff declares currency `INR`, nonnegative integer input/output
cost numerators in paise, a positive token denominator, base attempt/compute cost and validity.
Round upward only after exact integer/rational computation, never by floating-point estimates.
Zero provider billing does not default the compute tariff to zero.

The committed reservation returns `reservationId`, `reservedCostPaise`, `authorityDigest`,
`windowStart`, `windowEnd` and `expiresAt`. Serialize against the existing messaging budget lock
and environment-wide concurrency authority. Count messaging and model reservations together;
do not create two INR 500 allowances or reset the current messaging window to gain allowance.
Reservation expiry alone never releases a possibly dispatched attempt.

`SettleProfessionalInferenceV1` contains the original reservation/attempt, binding/rate digests,
known input/output token usage and durable usage/audit evidence references. The owner computes
and records the full actual charge, including overrun; it never trusts or clamps a submitted
total. UNKNOWN has no synthetic zero settlement and retains the reservation. A known no-socket
failure requires durable non-dispatch evidence before any release. Idempotent replay validates
the exact command digest; divergent replay is a conflict. Overrun fences new dispatch across
the shared budget authority.

### 9.4 Original Source And Terminal Snapshot

The private PR recovery source digest hashes canonical UTF-8 JSON with sorted keys, compact
separators and ASCII JSON escaping, containing exactly `schemaVersion`, `tenantId`,
`relationshipId`, `conversationId`, `executionId`, `originalMessageId`, `originalActorId`,
`mandateId` and `mandateDigest`. All values come from the immutable original records.
BP derives the runtime execution UUID from the original SEND actor/key; PR uses its stored
workflow identity. The fingerprint deliberately excludes today's membership, role, deadline,
cursor and projection version. Missing original mandate/source coordinates are unavailable;
they are never supplied from the fresh requester.

PR also returns `originalRequestDigest` from its persisted original `requestHash`, prefixed with
`sha256:`. BP must not reconstruct that hash from mutable locale/context or substitute its
different SEND hash. The result digest binds this owner-issued original request digest, the source
fingerprint, authority id and exact returned terminal events. BP persists that receipt with the
fresh permission; replay cannot replace an existing original request/event digest.

One Temporal query obtains source state and terminal events atomically. Recovery does not use
separate mutable state/event queries, require an inference worker, or invoke Start, signal,
cancellation, AIR or a provider. A nonterminal/missing retained result remains UNKNOWN/UNAVAILABLE
with no content. STOP is fenced. Returned events must be contiguous, retain their original ids,
and end with the exact matching terminal state/reason; malformed/incomplete results are unavailable.
Permission is checked both before and after the lookup. The BP projection version is owner-issued
concurrency authority, not a PR execution version; it remains a BP transaction check.

### 2026-11-08 private recovery continuation checkpoint

Section 9 is selected under the subsequent Founder drafting/approval authority. The previous
internal-interface approval blocker is removed, not replaced with fabricated activation evidence.

The private BP-to-PR read-only recovery route, registered grant, closed request/result models and
atomic Temporal terminal-snapshot query are implemented. The fresh delegated requester remains
separate from the immutable original actor. Permission purpose, current role/Decision Space,
CE decision/evidence, source, authority id, cursor and expected BP projection version are bound.
Expiry is rechecked after the bounded lookup and before response release. Recovery cannot invoke
Start, signal, cancellation, interpreter or provider; an unavailable local activity worker does
not force redispatch. Source/event drift, incomplete or system-only completion, STOP and missing
original request/mandate coordinates fail explicitly. Unknown work carries no result content.

The existing Identity lock adapter now returns its database-owned OWNER/MANAGER role, rather
than discarding the role returned by migration 88. It does not manufacture original Identity
coordinates or take roles from JWT claims.

Authored regressions cover distinct fresh requester, both permitted roles, immutable source drift,
closed request/primitive validation, expired or divergent permission, original terminal states,
unknown outcomes, exact 4096-event bound, terminal cursor tail, bounded unavailable lookup,
no legacy-JWT ingress and read-only snapshot behavior. Identity role regressions use the existing
real-PostgreSQL fixture. They have not been executed.

Static evidence:

- Docker .NET runner: `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-recovery -warnaserror`
  PASS, zero warnings/errors, including the newly authored Identity role regressions.
- Docker Python runner: `ruff check src/professional-runtime/routers/conversation_models.py src/professional-runtime/routers/conversation_execution.py src/professional-runtime/workflows/conversation_execution_workflow.py src/professional-runtime/main.py tests/professional-runtime/test_conversation_execution.py`
  PASS; syntax compilation of the same files PASS.
- Docker parsing of the canonical PR OpenAPI and workload registry PASS; scoped whitespace
  check PASS. No behavioral, PostgreSQL, Temporal or live-provider test was run.

The Python regressions remain inside the explicit service-integration selector. The .NET
business-platform gate runs the complete existing test project, including the extended fixture.
Qualification execution remains final-only.

The public BP reconciliation command, five-minute authority persistence, CE read-permission
admission, transactional projection/delivery fencing and governed generation/budget backend
remain incomplete. The private route alone is not end-to-end recovery or R006/R007/R008/R012 PASS.
No provider, credential, tariff, deployment or traffic was activated, and no existing worktree
changes were reset, discarded, committed or pushed.

### 2026-11-08 shared BP recovery and Web continuation checkpoint

The shared BP recovery command now persists a separate five-minute read authority, calls the
private PR terminal lookup with the fresh requester, and applies its retained event tail under
the dispatch/execution locks in one PostgreSQL transaction. Source, current Identity membership,
Decision Space, Stop and authority expiry are rechecked. UNKNOWN does not store a success; a
concurrent projection change during its lookup returns conflict instead of a stale unresolved
projection. Original actor/mandate/recipient coordinates remain unchanged.

The public request requires an integer projection version without permissive Web number-string
coercion. Execution versions are advanced before serializing cancellation outcomes and on
persisted execution changes, using the same idempotent version-advancement helper.
The private HTTP client validates closed identity/result shapes, bounded response reads, exact
terminal reasons and Python-compatible ASCII result digests. Recovery-specific outbox references
bind the committed authority and original recipient; final concurrent egress fencing still
needs qualification and any required repair.

Web is a transport/rendering adapter to this shared BP service, not a second recovery engine.
The regenerated client exposes the recovery command and execution projection version.
An authenticated original-message execution lookup permits a fresh device to discover that
version. Explicit "Check original runtime result" intent performs the read-only recovery command
and then reloads the canonical timeline. UNKNOWN states that operator reconciliation is required;
the adapter neither replays SEND nor reconstructs original runtime identity from browser storage.

Additional regressions are authored for strict public primitives, projection-version advancement,
unknown/foreign authority, independent Python Unicode/surrogate-pair/DEL digest compatibility,
inclusive 4096/4097 event limits, signed fresh-requester transport, owner failure semantics,
bounded/stalled response reads, caller cancellation, forced RLS and immutable authority identity,
and Web boundary/fresh-device recovery. They remain unexecuted. Tests were added to the existing
HTTP, PostgreSQL and Web suites plus the automatically collected BP test project; no new
standalone Python test selector is assumed.

Diagnostic static evidence, not authoritative catalog qualification:

- Docker .NET runner:
  `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-recovery -warnaserror`
  PASS, zero warnings/errors for the current recovery code and authored regressions.
- Docker Web runner: `pnpm exec tsc --noEmit --incremental false` PASS after regeneration.
  Formatting initially failed because source was read-only; scoped writable formatting mounts
  repaired that runner input before the successful formatting/type-check invocation.
- Docker Python runner: `python scripts/wc124_init_chain_lint.py` PASS, 92 SQL files, zero
  findings. The first run reported 14 existing WC-133/WC-134 init-chain authoring findings;
  constraint replacements now pair their guarded DROP/ADD in one statement and the recreated
  registration index uses IF NOT EXISTS. These edits preserve the same constraint/index
  definitions. Three-run migration replay and schema drift have not been executed.
- Docker BP OpenAPI parsing and execution-version/message-parameter resolution PASS.

No behavioral tests, live PostgreSQL/Temporal recovery, cloud/provider access, deployment,
commit, push or PR occurred. The full WC-134 item remains incomplete. Governed inference,
shared monetary/vault/audit integration, other pending rollout stories, integrated Docker
behavioral qualification and direct final author review remain required before a Founder-review
PR. Separate live acceptance remains outside this repository implementation authority.

### 2026-11-08 atomic recovery and final egress continuation checkpoint

Final runtime WhatsApp egress admission now uses the existing outbox service and one shared
PostgreSQL connection/transaction. It locks the dispatch barrier, execution, outbox, canonical
message, Identity membership, relationship/participant, contact and original binding; rechecks
Stop, terminal state, lease ownership/expiry, consent/window, fresh recovery authority and the
queued text digest; and denies erased or changed canonical content. Locks are released before
the external provider call. Provider activation and credential validity are checked again after
this admission. This is an admission boundary, not a promise to cancel an already admitted
external attempt; unknown-outcome reservation/accounting obligations are unchanged.

The provider adapter accepts the shared camel-case canonical text contract while retaining
legacy property-casing compatibility. Case-alias duplicate fields, unmapped fields and NUL text
are rejected rather than projected to provider content.

`ConversationReconciliationPostgresTests` now authors real-PostgreSQL projection scenarios using
the EF-mapped owner schemas and migrations 87-90: recovery with a fresh owner and an expired
original mandate, preservation of missing original Identity coordinates, complete rollback after
a persisted delta when a later event/gap/expiry fails, and membership/Stop/version rejection.
Its runtime egress cases cover permitted delivery and changed membership, consent, binding,
Stop/stopped-at, cancelled execution/outbox, expired authority, erased output and changed text.
An interceptor advances the test clock after the actual receipt INSERT, not after an arbitrary
number of clock reads. These scenarios supplement, not replace, full init-chain/production-RLS
and retained-Temporal qualification.

The existing provider suite adds a shared camel-case positive case and case-alias/NUL negative
cases. All added regressions remain unexecuted as instructed. They are collected by the existing
complete BP test-project gate. Diagnostic Docker compilation of the final slice passes:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-recovery -warnaserror`,
zero warnings/errors. Scoped whitespace passes. Initial compilation defects in test plumbing
(unused clock parameter, missing namespace imports and asynchronous response factory shape) were
corrected before the final successful build.

Recovery/delivery remain WIP pending behavioral qualification and any resulting repairs.
Governed inference, routing, broader controls/privacy, monitoring/readiness and final qualification
remain unfinished; no requirement or release is marked PASS, and no PR or live action occurred.

### WC-134 bounded delivery checkpoint — relationship inbound accounting

The Founder requested a course correction after repeated recovery refinement. The delivery scope
is frozen to the existing 22 WC-134 requirements, with separate implementation, Docker qualification
and protected/live evidence obligations. Recovery implementation is parked for integrated
qualification; additional recovery changes require an acceptance gap or an actual failure.
Its final retained-tail changes reuse one shape validator across transport and projection, and
verify persisted receipt digests during replay rather than trusting a repeated aggregate digest.
They are compiled but not behaviorally qualified.

Relationship inbound now uses the existing `WhatsAppTrafficBudget` and append-only traffic-event
ledger, not a second allowance. Under the existing tenant-wide advisory lock, it counts guest
events and provider/OTP reservations, preserves the original provider-message/sender decision on
replay, and rejects authority drift in either ledger. Current activation is checked again after
lock acquisition. Canonical runtime submission happens only after this reservation; a final-slot
capacity decision produces a canonical system limitation rather than invoking professional work.
Production DI supplies the existing budget owner. Legacy constructor-based simulations without a
capability gate retain their existing behavior.

Recipient STOP and relationship EMERGENCY STOP precede ordinary inbound-budget admission.
Already withdrawn/stopped contacts do not consume a new ordinary inbound reservation. Stop does
not acquire a fresh processing allowance or authorize a provider reply.

Authored regressions cover combined relationship inbound/provider reply exhaustion, replay after
exhaustion, shared minute decisions, foreign-sender identity collision, provider-authority drift,
signed STOP after budget exhaustion without runtime/outbox work, and forced-RLS PostgreSQL
relationship-inbound/OTP/provider contention. They remain unexecuted under the unchanged
implementation-first testing sequence and are collected by the existing complete BP project gate.

This closes the missing same-tenant relationship-inbound accounting implementation, not R008
acceptance. Cross-tenant routing, model-price/combined monetary integration, concurrency controls,
the competing final-notice-slot delivery race and integrated qualification remain open. No budget,
provider, activation, live authority or requirement PASS is inferred from compilation.

Final diagnostic validation of this slice: Docker
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-controls -warnaserror`
PASS, zero warnings/errors; scoped `git diff --check` PASS. An initial test compilation used
the wrong DbSet property name; the assertion now uses the mapped `ConversationExecution` entity
set. No behavioral tests, provider calls, deployment, commits, pushes or PR occurred.

### WC-134 bounded delivery checkpoint — Identity channel attachment

R005's previously identified membership/account-link race now has a shared owner check on the
channel-binding transaction, including replay. The controller forwards the verified actor and
current membership snapshot. After CE evidence and guest Stop locking, the Identity owner joins
the existing customer connection/transaction; calls the existing current-Identity lock capability;
locks and reloads registration, account link and mobile proof; and verifies the exact account,
OWNER membership, actor, sender digest and consumed/submitted destination proof. The same
transaction retains all Identity locks through the subsequent relationship/participant/contact/
binding checks and channel commit. No new connection can release that authority early.

Legacy in-memory authoring fixtures without verified portal coordinates keep their existing
simulation path. Relational attachment cannot use that path: missing Identity owner or verified
coordinates is an explicit denial/unavailable outcome. It is not a new Identity session or
permission to restore withdrawn consent, Stop or expired portal assurance.

Authored owner mutation cases cover cancellation, actor/tenant/account mismatch, manager role,
changed sender, absent/future confirmation evidence, proof revocation and registration changes.
Attachment-service cases cover revocation during CE evidence and denial of an existing-binding
replay. Production-DI Identity/real-PostgreSQL cases use the actual Identity migrations and current
membership lock function to cover revoked membership, role, account, link, proof and registration,
and show that revocation locks remain held until the calling binding transaction rolls back.
The fixture's execution table is minimal for migration 88; it does not qualify the full runtime
schema/init chain or live relationship attachment. Behavioral cases remain deferred.

Cross-tenant sender routing, protected provider delivery, integrated relationship journey and
final Docker qualification still remain; R005 is not marked PASS.

Diagnostic Docker compilation of the complete Identity-binding slice:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-identity-binding -warnaserror`
PASS, zero warnings/errors. Scoped whitespace PASS. No behavioral qualification was executed.

### WC-134 bounded delivery checkpoint — shared Marketplace catalogue semantics

Existing Web Marketplace interaction requests now use the same BP-owned catalogue discovery,
correction, bounded follow-up and published preview logic as WhatsApp guest discovery. The Web
adapter only renders that owner response and discloses its public-catalogue/non-professional limit.
Public request/response shapes, authentication, current membership and `PORTAL` scope remain
unchanged. WhatsApp retains its distinct guest participant and `GUEST_DISCOVERY` scope; no account
or guest history is copied, and no new relationship or private access is granted.

Only Marketplace customer turns since the latest non-Marketplace customer turn can enter the
three-turn discovery context. Account/billing/settings/relationship text cannot seed or revive a
catalogue selection. Marketplace requests also apply the shared current-WhatsApp-guest guard
when their participant has such a guest record; changing entry method cannot bypass consent/Stop.
Missing catalogue is explicitly unavailable rather than a fabricated preview.

Owner parity, separate timelines, account-surface interruption and replay regressions are authored,
along with Web disclosure/API-boundary rendering coverage. Docker test-project compilation
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-shared-catalogue -warnaserror`
PASS, zero warnings/errors. Docker Web `pnpm exec tsc --noEmit --incremental false` PASS and scoped
whitespace PASS. Behavioral tests remain deferred.

This is reuse through the existing membership-scoped Web API, not anonymous/unregistered visitor
admission or completed R004. Additive visitor admission, actual governed preview execution and
future Mobile integration remain open. No provider, cloud, traffic or spend authority is changed.

### WC-134 bounded delivery checkpoint — operational alert rule wiring

Added the closed, default-absent Demo monitoring tuple and a one-minute rule for
payload-free exact-candidate alerts and missing evaluator heartbeat, forwarded to
the existing approved action group. BP now exports a machine-readable observation
with activation/release/configuration identity and observation time only after
current-authority evaluation; environment drift also suppresses success heartbeat.
The query rejects stale/other-candidate observations and is bound by its immutable
digest in the reviewed configuration. Lease reconciliation retains the tuple.

The operator acknowledgement/escalation/readiness procedure is in
`infrastructure/operations/wc134-whatsapp-monitoring.md`. It explicitly separates
evaluation, Azure delivery, actual receipt and human acknowledgement and does not
claim an automatic fence. Cross-tenant evaluation, automatic acknowledgement
tracking/escalation, executable KQL behavior and actual protected receiver evidence
remain open. Regressions are authored, behavioral execution remains deferred, and
no cloud action, provider call, activation or monitoring spend is authorized here.

Diagnostic Docker BP test-project build PASS, zero warnings/errors. Docker Python
Ruff check/format PASS. Docker Terraform 1.9.8 workload-module validation against
the pinned AzureRM 4.14.0 schema PASS after restoring the missing provider only in
an ephemeral container and including the existing local environment contract.
No Terraform plan/apply or behavioral tests were run. Scoped whitespace PASS.

## 10. Founder-frozen execution boundary

Founder confirmed this boundary on 2026-11-08: retain all original R001-R022;
finish shared routing, then governed execution/shared accounting, then lifecycle
controls and remaining repository readiness, then integrated Docker behavioral
qualification and Founder-review PR. These blocks organize execution only: they
do not replace or reduce the original acceptance requirements.

Use existing shared BP owners for WhatsApp and Web, reusable by future Mobile.
No new Mobile application, unrelated refactoring or speculative refinement is in
scope. Author tests during implementation; compilation/static checks are not
acceptance. Provider readback, deployment, spend, activation and live acceptance
retain separate authorization gates. Report required external evidence as gated,
never delivered or removed. No regrouping, scope change or restart of this plan
without explicit Founder approval; report concrete dependency blockers instead.

### Routing implementation checkpoint

The shared attachment owner now publishes exact sender-to-customer binding and
Identity coordinates in its customer binding transaction. New attachment and
authenticated replay share the publisher, and divergent replay cannot replace or
renew the record. Migration 91 supplies a service-tenant-indexed private directory
with FORCE RLS, customer-scoped writes, cross-customer sender uniqueness, a binding
foreign key and no ordinary UPDATE/DELETE grants. No existing customer-table RLS
policy or recipient gate was relaxed, and no legacy route was invented.

Publication/replay/mutation cases and production-prerequisite PostgreSQL migration
replay, directory visibility and customer-table isolation cases are authored.
Docker test-project compilation PASS, zero warnings/errors. Behavioral execution
remains deferred. Directory publication is a routing prerequisite, not a tenant
switch grant: ingress, worker, callback, final egress and shared accounting wiring
must still consume a freshly validated owner route. The routing block remains open.

### Routing checkpoint — fresh shared-owner route validation

Added an exact service-tenant/sender-key lookup and shared current-route guard.
Directory coordinates must match the expected issuer and sender, then pass the
existing same-transaction Identity registration/link/current-OWNER checks.
Relationship, participant, contact and channel rows are locked in the attachment
order and reread; changed or ambiguous binding, wrong actor/role/evidence,
withdrawal, stopped/ineligible relationship or invalid conversation UUID denies
the route. PostgreSQL also locks and checks the exact canonical conversation's
environment, customer tenant and relationship. New attachment and authenticated
replay call this guard before commit.
The returned snapshot grants no session, fresh mandate, guest consent, Stop
release or provider permission.

Sixteen owner mutation/current-route scenarios and exact keyed-lookup isolation
cases are authored. The existing full-init-chain grant test now also checks the
directory's FORCE RLS and SELECT/INSERT-only application privileges, invokes the
actual canonical-conversation guard for current and wrong-tenant/relationship/
conversation/environment tuples, and checks that a concurrent update remains
blocked until the caller's transaction ends. Docker
test-project compilation PASS, zero warnings/errors; behavioral execution remains
deferred. Ingress/worker/callback/final egress and shared accounting consumption,
guest Stop/consent fencing and production lock-wait/canonical conversation
qualification remain open in this same routing block.

### Routing checkpoint — transaction-bound ordinary database entry

The internal BP routing owner now selects a service-tenant/sender candidate,
locks and checks guest admission/current consent/Stop, validates current
Identity/relationship authority in a customer transaction, and checks the
relationship Stop latch before ordinary database work. It saves and rereads the
route, Stop and guest consent before committing; tuple or relationship-version
drift denies the transaction. No provider socket or slow evidence operation
belongs under this database entry's sender lock, and safety controls keep their
separate priority path.

An internal candidate scope and confirmed-route recipient check select the
customer RLS tenant without broadening the existing activation recipient gate.
The interceptor refuses conflicting HTTP/runtime tenant authority. Scope
restoration, wrong-coordinate confirmation, activation drift, concurrent scope
isolation, missing scope/non-PostgreSQL denial, sixteen guest-consent/Stop cases
and real-PostgreSQL interceptor visibility/write/restoration cases are authored.
The owner is registered in production DI. Docker test-project compilation PASS,
zero warnings/errors; scoped whitespace PASS. Behavioral execution is deferred.

Webhook, worker, callback, provider and combined-accounting adapters do not yet
consume this entry. Cross-tenant effects remain denied by their existing gates;
this checkpoint is not end-to-end routing, customer continuity or R002 acceptance.
Those adapter connections remain the next work inside the same frozen block.

### Routing checkpoint - restricted signed delivery observations

Signed provider statuses carrying a valid `recipient_id` now derive the same
protected sender digest as ingress. The BP delivery-observation owner resolves
only the exact service-tenant/sender directory row. Customer observations require
the signed opaque outbox UUID and lock the exact canonical outbox and historical
channel binding under customer RLS. Environment, tenant, sender, participant,
binding evidence and conversation must match. The existing attempted-submission,
traffic-reservation, provider-reference, divergent-replay and early-status checks
remain in the outbox owner. Its claim and observation writes use the same owning
transaction rather than opening another service-scoped context.

Historical status recording deliberately does not require renewed Identity,
current binding activation, guest consent or an unstopped relationship. It is
receipt reconciliation only: the candidate never becomes a confirmed dispatch
route, and this path does not queue work, grant a session, clear Stop, or submit a
provider request. Legacy statuses without a signed recipient remain service-scoped;
an opaque UUID alone cannot select a customer tenant. Missing customer correlation
or missing routing owner fails explicitly. Known service-scoped sources must also
match the signed sender's attempted canonical outbox.

Authored full-production-schema cases cover the historical revoked binding with
an existing relationship Stop latch, replay, missing/foreign outbox, sender,
environment, tenant, participant, binding and evidence mismatch, caller-transaction
requirement, and a blocked concurrent binding mutation. Existing status tests also
cover owner-unavailable no-effects denial and malformed signed recipient fields.
Behavioral execution remains deferred under the frozen final-only qualification
boundary. Docker test-project compilation is diagnostic evidence, not R002/R007
acceptance. Ordinary ingress, worker leasing, provider egress and shared-accounting
adapter integration remain open in this same routing block.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-status-routing -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. No behavioral,
PostgreSQL, provider or live test was executed.

### Routing checkpoint - shared service-tenant relationship inbound accounting

The existing BP traffic owner now accepts exact confirmed customer relationship
and channel-binding coordinates for inbound reservation. It requires the active
internal routing scope; a directory candidate, customer tenant assertion or
missing routing owner cannot reserve against the Demo allowance. The owner checks
the same route before reservation, after the shared budget lock, on replay and
before commit. The database override exists only during the service-tenant budget
operation and restores the customer scope on success or failure.

Customer inbound events use the existing service-tenant ledger, activation digest,
authority digest, advisory lock and idempotent provider-message identity. They
compete with guest inbound and provider reservations under the same combined
activation and rolling-minute limits. No customer-tenant allowance, transcript,
new table or new grant is introduced. The existing same-tenant entry remains
unchanged. The relationship ingress adapter now supplies exact binding/relationship
coordinates to this owner; cross-tenant ingress itself still requires its staged
route integration and remains denied by existing entry gates.

Eight no-effects route-denial cases are authored. The existing forced-RLS
PostgreSQL race fixture adds a mixed customer-inbound/guest-inbound/provider
reservation mode, exact persisted-decision replay, customer-ledger invisibility,
absence of customer-tenant ledger rows and scope restoration after an explicit
reservation denial. These cases are not executed yet. Diagnostic Docker
test-project compilation and scoped whitespace validation are not R002/R008
acceptance. Worker/provider outbound accounting and full ingress routing remain
open inside the same frozen routing block.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-shared-inbound -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. Behavioral,
PostgreSQL race and live-provider execution remain deferred.

### Routing checkpoint - fresh customer provider dispatch admission

The shared relationship owner now exposes a short-lived final-egress recheck
for an already confirmed route. It locks the service sender and checks current
guest admission/versioned consent/Stop; the exact directory candidate is read
under the service override, then current Identity, relationship, participant,
binding, canonical conversation and relationship Stop are checked under customer
RLS. Guest consent and activation are checked again. All database transactions
and sender locks end before protected provider/socket work.

The provider adapter admits a customer tenant only with this internal confirmed
route and registered fresh-recheck owner. It runs the recheck before canonical
projection and again immediately before egress, uses the shared outbound
reservation command, and rereads current protected destination, relationship
Stop and exact dispatch lease/owner/attempt/payload. Customer delivery requires
its protected destination and cannot fall back to the own-number pilot. The
activation recipient gate still evaluates the original service tenant and sender;
it is not widened to arbitrary customer tenants.

Six route/scope/issuer/non-PostgreSQL denial cases and a no-routing-owner provider
no-socket/no-reservation case are authored. Existing same-tenant provider behavior
is retained. These regressions have not been executed and customer-provider
success, forced-RLS concurrent authority changes and real delivery remain
unqualified. Database checks before a remote socket do not eliminate the
in-flight Stop/reassignment race or promise remote cancellation.

The hosted worker does not yet install a customer execution scope or call this
path. Restricted reconciliation after revocation and staged ingress remain open
in the same frozen routing block. No activation, provider call or spend occurred,
and no R002/R007/R008 acceptance is claimed.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-egress-route -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. Behavioral and
live-provider execution remain deferred.

### Routing checkpoint - hosted customer worker consumption

The hosted worker now alternates customer-first and service-first polls, with
fallback to the other cohort when no item is available. Customer discovery feeds
the fresh relationship owner and exact-item lease entry. The owner returns the
lease with its validated candidate and complete route snapshot only after its
final checks. Before invoking worker operations it reinstalls a customer scope,
checks lease coordinates/expiry and repeats fresh egress authority validation.
All sender/Identity validation transactions have ended before provider and
heartbeat operations begin. Partial worker-owner registration fails explicitly.

Ordinary customer dispatch now reaches the guarded provider adapter and shared
outbound budget. Reconciliation for a currently authorized customer route reads
only its exact canonical outbox and persisted delivery observations; it cannot
call a provider or resend. Customer BeginDispatch, heartbeat and result writes
lock the exact route/owner/unexpired outbox under customer RLS in their own
transactions, so a competing owner cannot replace work between ownership read
and update. Result and observation persistence commit together. Existing
service-scoped worker behavior is unchanged.

Authored cases cover changed lease coordinates, expired/candidate/non-PostgreSQL
worker entry with no callback, partial owner wiring with untouched pending work,
both polling preferences for the existing service cohort, and forced-RLS
wrong-owner heartbeat/result rejection plus persisted UNKNOWN result. These
cases remain unexecuted. Successful full-chain customer worker/provider execution
and restart/concurrency qualification are not claimed.

Stopped, withdrawn or Identity-revoked customer work still fails the ordinary
fresh lease entry. Signed status callbacks can record historical receipts, but
the dedicated post-revocation reconciliation worker path remains open; this
checkpoint does not clear Stop or convert unknown submission into unsent work.
Staged ingress and that restricted reconciliation path remain in the same frozen
routing block. No cloud/provider call, live activation, spend or requirement
acceptance occurred.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-customer-worker -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. Behavioral,
PostgreSQL, restart and live-provider execution remain deferred.

### Routing checkpoint - historical receipt-only worker reconciliation

Customer worker discovery now enters the restricted historical observation owner
before ordinary fresh-route leasing. Under the active service scope it resolves
only the sender's attachment directory row, switches to candidate customer RLS
without confirming a sending route, locks the exact outbox with `SKIP LOCKED`
and checks the historical binding/participant/evidence/conversation tuple.
Unresolved or expired ambiguous submission reads only that canonical message's
persisted delivery observations. DELIVERED/READ converges to DELIVERED; FAILED
converges to BLOCKED. Outbox transition and work-directory scheduling update
commit together without incrementing attempts or creating a receipt.

No current Identity membership, guest consent or active binding/relationship
is required for historical reconciliation. It cannot invoke a provider, send,
clear Stop, publish a session, or mark unknown work as unsent. An active lease,
held row lock or absence of terminal receipt remains untouched; ordinary pending
work still proceeds through the separately governed fresh route. Sender activation
authority remains required. Stopped/revoked historical work no longer depends on
ordinary egress authority to converge its already-persisted delivery receipts.

Four focused forced-RLS cases are authored for DELIVERED, READ, FAILED and UNKNOWN,
with repeat reconciliation, unchanged attempt counts, no confirmed route,
no Identity/guest tables, foreign-tenant receipt rejection, held outbox lock,
recipient denial and scope restoration. The earlier full-schema historical
source guard covers a revoked binding and relationship Stop; the combined full
production migration/revocation/concurrency journey remains unexecuted.

This wires the restricted reconciliation worker path, not live acceptance.
Staged signed ingress remains the next open adapter in the frozen routing block.
No behavioral execution, provider/cloud call, spend or requirement PASS is claimed.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-historical-reconciliation -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. Historical
PostgreSQL/revocation/restart and live-provider execution remain deferred.

### Routing checkpoint - staged ordinary signed ingress

After raw signature, provider envelope and sender binding checks, ordinary
WhatsApp ingress now looks up the sender's exact service directory candidate.
No candidate continues through the existing service-tenant guest path. A
candidate must pass the bounded ordinary database route entry and fresh
Identity/consent/Stop/canonical recheck before a confirmed customer scope invokes
the existing Conversation journey. Validation transactions and sender locks end
before journey evidence/runtime calls. A missing customer contact never falls
back to creating a guest in the customer tenant.

The journey validates customer contact, sender and exact active binding against
the confirmed route instead of broadening the activation recipient gate.
Relationship inbound supplies the exact coordinates to the already shared
service-budget owner. Provider claims and canonical customer work retain their
selected customer RLS scope. This entry does not mint Identity, membership,
relationship, session authority or a new mandate.

Six authored routing cases cover unchanged guest flow, surfaced guest failure,
missing scope, forbidden service override, candidate/non-PostgreSQL denial and
foreign sender, with no invented customer authority or scope leak. These cases
are not executed; full customer ingress success, concurrent revocation and
canonical-effect qualification remain open.

Exact recipient STOP and relationship EMERGENCY STOP deliberately remain outside
this consent/membership-gated ordinary entry. The separate safety implementation
is recorded in the next safety checkpoint; behavioral qualification remains
required before the routing block can close.
No full R002 acceptance, provider/cloud execution or spend is claimed.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-signed-ingress -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. Behavioral,
customer full-chain and live-provider execution remain deferred.

### Routing checkpoint - restricted signed safety controls

Signed exact STOP and EMERGENCY STOP now enter a dedicated BP safety operation,
not the ordinary Conversation journey. Production-scoped signed ingress fails
explicitly if its routing owner is missing. Safety provider claims stay in the
service tenant, so a later guest/customer route transition does not change their
replay coordinates.

Recipient STOP first acquires the service sender lock and commits a stopped
guest tombstone, preserving existing consent/admission references and issuing no
reply, session, account, registration or employment. This containment precedes
provider-claim acquisition, directory lookup and customer writes. An exact
directory candidate selects customer RLS; locked relationship/participant/contact/
binding rows must correlate to the directory's sender, actor and bound evidence.
Only the existing contact opt-out and its pending-confirmation/journey flags
change. A revoked participant or historical revoked channel can still withdraw
messages. Wrong correlation or competing active sender bindings deny customer
mutation; the already committed service sender fence is not undone.

EMERGENCY STOP requires the exact active, nonrevoked WhatsApp binding and current
matching active participant, but does not require current Identity login/OWNER
membership, guest admission, consent or absence of guest recipient STOP. It
selects only that customer relationship and calls the existing Emergency Stop
owner after validation transactions end. The existing owner retains local
containment, evidence-first confirmation, participant revalidation at commit and
pending-evidence errors. An unbound emergency command denies explicitly rather
than becoming catalogue discovery. No ordinary route confirmation, provider
permission, budget reservation, destination update or customer transcript is
created. Emergency acknowledgement here is an internal receipt only: provider
delivery and the final acknowledgement policy are not qualified.

Ten PostgreSQL forced-RLS scenarios, eight scope/input denial scenarios and four
signed adapter owner/no-fallback scenarios are authored. They cover historical
recipient withdrawal, mismatched evidence, revoked emergency authority, replay,
missing route, no Identity/consent, guest STOP bypass for Emergency Stop, pending
CE evidence and untouched foreign contacts. The PostgreSQL fixture uses generated
schemas plus the actual directory migration, not the full production chain.
The catalog BP test gate discovers the entire assembly, including these cases.
Behavioral execution remains deferred.

Fresh-authority/late-revocation, competing insertion, lock-wait latency, in-flight
remote submission/reassignment, production migration grants and delivered
acknowledgement races remain unqualified; this checkpoint does not accept
R002/R009 or close the routing block. No remote cancellation, provider/cloud
execution, live activation or spend is claimed.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-safety-routing -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. No behavioral tests
were executed; authored regressions are not acceptance evidence.

### Routing checkpoint - canonical ingress commit authority

Ordinary route validation is no longer the only customer authority check before
canonical admission. BP Conversation Send, routed Retry and outbound journey
contribution now call the routing owner immediately before canonical persistence,
after their evidence, mandate and context-resolution work. The owner requires
the selected confirmed customer snapshot and matching tenant, participant,
relationship, conversation, channel and supplied binding/sender coordinates.
Missing production owner and candidate-only or mismatched scope deny explicitly.

The check joins the caller's existing PostgreSQL connection and transaction using
the existing BP borrowed-context pattern. It acquires the service sender lock,
rereads guest consent/Stop and the exact directory entry in service RLS, restores
customer RLS, and invokes the shared current Identity/relationship/channel/
canonical/Stop guard. These locks remain owned by the caller through canonical
commit. Runtime membership resolution follows the sender/current-route check so
it does not invert the sender-before-Identity lock order. Activation authority
is checked again after SaveChanges and before commit. Denial rolls back canonical
messages, executions, events, outcomes and queued journey responses; prior
evidence is not fabricated, removed or promoted into successful admission.

Routed Retry adds the same bounded admission transaction and requires the
original execution's channel binding and sender coordinates. After the route
check it locks and reloads the exact canonical message, execution and original
SEND outcome; changed origin/request/message correlation, missing rows or late
Stop/cancellation/completion cannot be overwritten into a queued retry.
Unscoped Web/portal
retry retains its existing persistence path; this change does not authorize
legacy unproven WhatsApp origin replay or alter the external-UNKNOWN policy.

Send and routed Retry additionally rerun fresh current route validation after
the admission transaction ends and before invoking the runtime Start operation.
Validation failures remain explicit authority failures outside the existing
unknown-start catch; they do not fabricate a remote request or failed provider
receipt. A post-admission denial can leave a durable queued admission without
starting runtime work. It does not clear Stop, renew the mandate or implicitly
redispatch that admission. Recovery/terminal treatment still requires integrated
qualification. No sender lock or admission transaction spans runtime Start.

Ten authored consumer cases cover Send/Retry/journey contribution denial on
missing owner, non-PostgreSQL persistence and activation change during evidence
or before contribution commit, plus unproven routed retry origin, asserting no new canonical persistence/runtime
start and unchanged failed retry state. Eight exact-snapshot cases reject
foreign coordinates, Web channel and unconfirmed candidates. The forced-RLS
safety fixture also authors a stopped-sender canonical commit denial, caller
customer-scope restoration, and sender-lock retention until owning rollback.
These regressions compile but have not executed. Full current Identity/consent
success, actual production migration grants, late mutation/Stop insertion,
runtime restart and in-flight races remain unqualified.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-ingress-commit -warnaserror`
PASS, zero warnings/errors. Scoped whitespace check has no findings. Behavioral
testing remains deferred; no routing acceptance, provider/cloud activation or
spend is claimed.

### Routing checkpoint - no redispatch from webhook recovery

The queued-admission trace confirms the existing runtime recovery worker only
reads the original execution's event stream; it has no Start dependency. The
existing Retry eligibility rejects a queued, accepted admission. No terminal
state, confirmed remote failure, completed work or new mandate is fabricated for
a late-authority-denied queued row. Its final operational resolution remains a
qualification/lifecycle obligation, not implicit restart permission.

The same trace found the WhatsApp journey automatically invoking Retry after
replaying an unresolved canonical send. That automatic Retry is removed. An
unknown original delivery now returns `RECONCILIATION_REQUIRED`; a known failed
original returns `SECURE_PORTAL_REQUIRED`. Both publish a bounded shared
Conversation system notice that explicitly says no new professional work was
started and directs the customer to the secure portal. The existing deterministic
journey contribution identity recovers the same notice without new execution or
duplicate outbox publication. A missing contribution owner fails explicitly;
it cannot fallback into a new Start.

The direct customer-routed Retry entry also denies unresolved message delivery
or original SEND outcome before new evidence/mandate resolution, and after the
commit-time row locks/reload. This does not grant portal retry authority, change
unscoped Web retry behavior, settle an unknown attempt, release a reservation or
clear Stop. Fresh-owner read-only reconciliation remains the separate mechanism
for retrieving retained outcomes; WhatsApp recognition does not authenticate it.

Three authored journey regressions assert a single original runtime start,
evidence call and mandate resolution for unknown/known failures, repeated notice
recovery, and missing-owner failure, with unchanged original failed execution.
The consumer matrix adds unresolved/queued direct-routed retry denial without
additional evidence/mandate/Start. The signed PostgreSQL journey regression now
expects one original Start and a canonical reconciliation notice through replay,
retaining cancellation and original execution/mandate assertions. Those
behavioral cases remain unexecuted; successful notice queueing is not provider
delivery or final unknown-outcome resolution.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-ingress-replay -warnaserror`
PASS, zero warnings/errors. Scoped whitespace checks have no findings.
Full migration/restart/provider/late-authority behavior remains unqualified.
The frozen routing block remains in progress; no requirement acceptance,
activation, provider/cloud execution or spend is claimed.

### Routing checkpoint - exact customer outbox lease boundary

The BP outbox owner now has an internal exact-item customer lease entry. It
requires the complete confirmed route snapshot, including conversation, participant
role and relationship version, not just an asserted tenant or candidate directory
row. Generic next-item leasing refuses a selected customer scope. The customer
entry selects only the given outbox UUID and its exact environment, tenant,
relationship, conversation and sender digest under customer RLS; it locks that
row with `FOR UPDATE SKIP LOCKED` before applying the existing ordering,
retry-count, due-time and unresolved-submission rules. Route and activation are
rechecked before save and commit. A claimed lease is not dispatch permission.

Four real-PostgreSQL cases are authored for PENDING, UNRESOLVED, expired
DISPATCHING and exhausted expired LEASED work. They include candidate-only and
generic-scan denial, full-snapshot substitution, foreign UUID isolation,
canonical row-coordinate drift, preceding-message order, a held concurrent row
lock, repeat-claim exclusion, activation change and untouched foreign work.
Unknown prior submission retains its attempt count and reconciliation flag.
The fixture exercises actual forced RLS and the production tenant interceptor,
but is not the full migration chain. Behavioral execution remains deferred.

Worker discovery through an owner-indexed work directory, fresh route acquisition
and the provider dispatch/reconciliation scope remain incomplete. This entry is
not yet called by the hosted worker; it does not enumerate customer routes,
enable sending, solve in-flight Stop, or complete R002/R007. The frozen routing
block remains in progress.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-routed-lease -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. The authored
PostgreSQL cases have not been executed; no provider or cloud operation occurred.

### Routing checkpoint - owner-indexed outbox discovery and fresh lease entry

Migration 92 adds a minimal BP-owner-only work directory containing outbox UUID,
service/customer tenant coordinates, environment, sender digest, binding, due
time and terminal flag. Customer outbox insertion publishes it in the same
transaction only when the attachment directory and historical binding match the
canonical outbox. Indexed source coordinates cannot be changed; ordinary lease,
heartbeat, retry and terminal updates synchronize scheduling. There is no
unscoped transcript scan or legacy backfill.

The indexed claim function requires the caller's service-tenant database context
and returns only one due outbox UUID and sender digest for the exact environment.
It skips locked candidates and reserves discovery for 45 seconds; it neither
leases the outbox nor returns customer text or authorizes dispatch. The .NET
directory owner requires the active service scope, verifies sender admission and
unchanged activation, and commits discovery only after these checks. An internal
relationship owner entry feeds the discovered item through existing fresh
Identity/guest-consent/Stop/canonical-route validation before exact-item leasing.
Only bounded database work is performed under the sender lock.

The exact lease uses its own customer transaction. If the outer route's final
recheck later denies, an already committed lease may remain until expiry, but no
provider work is started. Fresh dispatch admission remains required; this is not
an atomic send claim or a renewed mandate.

Authored PostgreSQL cases apply migrations 91/92 twice, demonstrate transactional
publication, deny direct directory reads and unscoped claims, skip a held work
lock, roll back discovery on recipient denial, suppress repeat discovery,
exercise exact leasing and lease-expiry rescheduling, enforce immutable source
and terminal suppression. This focused fixture uses minimal relationship-source
tables; the full init-chain fixture separately asserts owner, FORCE RLS, denied
direct privileges and exact function grants. No behavioral case is executed yet.

The hosted worker does not yet consume this customer path. Final provider
dispatch/reconciliation admission, shared outbound budget and staged ingress
remain open in the frozen routing block. This is not R002/R007 acceptance or live
continuity. No provider, cloud activation, spend or readiness claim is introduced.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-work-discovery -warnaserror`
PASS, zero warnings/errors. Docker
`python scripts/wc124_init_chain_lint.py --init-directory /tmp/wc134-outbox-init`
with migration 92 alone PASS, zero findings. Scoped `git diff --check` PASS.
Behavioral and full migration replay execution remain deferred.

### Routing implementation block - evidence-bound End, renewal and original delivery history

Migration 93 adds an owner-only FORCE-RLS route history and narrowly scoped
same-owner renewal. The original binding must be ENDED with nonempty retirement
evidence. Its fresh replacement must retain the tenant, issuer/actor, account,
membership, relationship, role, canonical conversation and sender; it must carry
fresh attachment evidence and cannot compete with another active sender binding.
Archive and publication are atomic with attachment. Existing fresh Identity,
guest STOP, relationship Stop and contact-withdrawal guards remain mandatory.
No recipient consent or Stop state is reset and no cross-owner transfer is enabled.
The publication timestamp uses wall-clock validation, not transaction-start time,
because attachment evidence recording precedes publication.

Channel End now performs its remote evidence call before acquiring database locks.
It then locks relationship, participant and binding rows in that order, reloads
the original relationship and binding, and rechecks the exact active participant
binding and role. Changed source/version, revoked authority and empty evidence deny.
Concurrent End returns its original committed evidence without overwriting it;
same-key divergent requests remain conflicts. No lock spans the evidence call.

Callbacks and hosted-worker recovery resolve the original indexed outbox binding
through current directory or retired history, not whichever binding is current.
Fresh customer worker leasing requires that original binding to match the current
confirmed binding. Retired pending/ordinary expired leased work is BLOCKED without
incrementing attempts. Unknown submissions, active dispatches and exhausted leases
retain original receipt-only convergence; no provider redispatch or cancellation
claim is made.

Authored coverage includes 13 PostgreSQL renewal cases: migration triple replay,
same-owner exact replay, transaction rollback, active original, absent retirement
evidence, withdrawal, foreign actor/account/tenant/relationship/conversation,
original callback correlation, new-work indexing, retired unsent containment,
unknown/exhausted/active-dispatch preservation and scope restoration. Six channel-End
evidence-time mutation/concurrent-outcome cases supplement the existing End replay
case. The indexed-directory fixture now applies migration 93 as well. These are
authored regressions, not passing behavioral evidence.

Docker diagnostic evidence:

- `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-route-lifecycle -warnaserror`
  PASS, zero warnings/errors.
- `python scripts/wc124_init_chain_lint.py`
  PASS, 95 SQL files, zero findings.

This completes the bounded same-owner channel lifecycle implementation chunk.
The full frozen routing block is not accepted: production-schema race/restart and
protected-read qualification remain, and cross-owner reassignment/retention must
follow the separately defined privacy authority, not silently widen this renewal.
R001-R022 remain unaccepted; final behavioral execution is deferred as instructed.
No provider/cloud request, activation, spend, commit, push or PR is claimed.

### Routing implementation block - protected reads and direct original-binding fencing

The shared current-route transaction guard now protects timeline reads,
message/execution lookup, both event replay entries, channel-skill replay/context
and retained journey reply recovery. Stored SEND, terminal Retry/CANCEL,
read-position and outbound-contribution replay paths acquire the same guard before
returning retained data. Empty results cannot bypass authority. Routed reads require
PostgreSQL and the production routing owner, bind the exact requester/relationship
and environment, and reject candidate-only or changed activation. Sender, current
Identity, participant, binding, canonical conversation and Stop locks remain through
bounded materialization; recipient/activation are rechecked at release. Failed
read admission disposes its transaction and releases locks before propagating denial.
No read lock spans constitutional evidence or provider/runtime operations.

Read-position writes now acquire routing authority after evidence, reload current
position and recheck before commit. Cancellation revalidates fresh routing before
the remote cancellation request and inside the later owning canonical transaction.
This cannot retract a remote operation already issued; a late denial does not
invent a committed cancellation result.

Migration 93 additionally exposes a narrow customer-scoped original-outbox match
function. The exact customer lease entry itself uses it under its outbox transaction,
retaining index/directory share locks through lease commit. A wrapper cannot
accidentally admit old work under a renewed binding, and direct internal calls have
the same fence. No application-role index/history read grants or transcript scan
are added. Historical callback/receipt-only recovery remains separate from fresh
send authority.

Authored regressions cover 14 protected-read/replay/mutation surfaces across four denial
modes (56 scenarios), final-release activation/candidate checks, repeated real-PG
STOP read denial with transaction/advisory-lock cleanup, all four direct exact-lease
states with retired-index denial, and post-renewal old/new indexed work matching.
Production DI already supplies the scoped routing and shared execution owners to
Conversation and contribution services; no alternate adapter or owner was introduced.
Hosted-worker restart remains discovery of the immutable original work: historical
convergence precedes fresh lease, and unknown runtime replay never invokes Start.

Diagnostic Docker validation:

- `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-protected-routing -warnaserror`
  PASS, zero warnings/errors.
- `python scripts/wc124_init_chain_lint.py`
  PASS, 95 SQL files, zero findings.

The bounded protected-read/revocation/replay/direct-lease implementation chunk is
complete. Behavioral, production-schema race/restart and full integrated qualification
remain deferred until frozen-scope implementation is complete. Reassignment attempts
to a different owner/tenant/relationship remain denied with no history transfer;
physical number-recycling detection, retention/erasure/legal hold and any authorized
reassignment workflow remain R018 privacy obligations. No new reassignment policy,
R001-R022 acceptance, live continuity, activation, provider request or spend is claimed.

### Routing closure inventory and explicit blockers

This inventory is implementation evidence for the frozen routing phase, not
behavioral acceptance. References below identify the actual production entry and
the owning authority, rather than marking R002 complete from a compilation result.

| Surface | Production entry and authority | Authored evidence / remaining limit |
|---|---|---|
| Signed messages, including provider-claim replay | `WhatsAppJourneyService` selects the exact service directory candidate; `WhatsAppRelationshipRouting.ExecuteSignedIngressAsync` validates before the operation and again before returning customer receipts | `WhatsAppDemoProviderTests`, `WhatsAppRelationshipRoutingScopeTests`; customer late-revocation end-to-end qualification remains deferred |
| Unbound service receipt release | The same ingress wrapper rechecks service activation/recipient and denies a directory row published while its operation was in progress | Four unchanged/activation/recipient/new-route regressions in `WhatsAppRelationshipRoutingScopeTests` |
| STOP / EMERGENCY STOP | `ReceiveSignedSafetyControlAsync` commits service recipient containment before customer work; emergency uses exact current participant/channel, independently of ordinary OWNER/consent admission | `WhatsAppRelationshipSafetyRoutingPostgresTests`; remote halt is never inferred from a receipt |
| Canonical Send/Retry/reply and retained reads | `ConversationService` and `ConversationOutboundContributionService` use the owning-transaction route guard; stored/empty results do not grant authority | 56 denial scenarios and PostgreSQL lock cleanup authored; no behavioral execution |
| Attachment, End and renewal | `AttachLinkedPhoneAsync`, `EndChannelSessionAsync` and migration 93 bind current Identity, exact relationship/role/conversation and evidence; different-owner renewal denies | Attachment, End, publication and renewal cases authored; no transfer/re-consent workflow enabled |
| Customer discovery and restart | `WhatsAppOutboxWorkDirectory` returns only original indexed work; `WhatsAppOutboxWorker` performs historical convergence before current route lease | Directory and exact-lease PostgreSQL cases authored; no unscoped transcript scan |
| Fresh customer lease and provider dispatch | Direct `LeaseRelationshipAsync` checks original index/current directory in its transaction; cloud dispatch checks fresh route, destination, Stop, canonical payload and attempted lease before submission | Lease, provider and scope cases authored; no lock spans a provider socket or remote cancellation guarantee |
| Delivery result/status after revocation | `RecordDeliveryObservationAsync` uses original indexed current/retired binding and canonical source; `RecordResultAsync` requires the owned original lease | Historical receipt convergence remains permissible without restoring send authority |
| Shared message accounting | `WhatsAppTrafficBudget` binds confirmed customer route/outbox, then selects only the original service ledger under a bounded override | Existing mixed-tenant budget cases authored; model monetary accounting belongs to the next frozen phase |
| Runtime restart and fresh-owner result recovery | `ConversationRuntimeEventWorker` consumes only original retained events under its separate runtime work owner; authenticated `ConversationController` recovery uses current membership/Decision Space and a five-minute read permission | No WhatsApp reconciliation command is introduced: Journey directs the customer to the secure portal. Neither restart nor recovery invokes Start |
| Production registration | `Program.cs` supplies scoped routing, historical delivery and contribution owners to Journey/Conversation/outbox/provider/worker entries | Missing owners explicitly deny; catalog qualification remains deferred |
| Physical schema authority | Migrations 91-93 retain FORCE RLS, owner-only history/index and only narrow EXECUTE grants | Full-init fixture now explicitly checks all three migration-93 functions, owners, SECURITY DEFINER, pinned search path/row security and no PUBLIC execute; unexecuted |

The trace found and repaired a further real bypass: `ClaimProviderEventAsync`
can return an accepted stored receipt without calling the protected Conversation
reader. The signed ingress wrapper now performs a fresh current-route check
after its operation, including that replay path. No routing locks span the
operation. Service receipts also cannot cross a newly published customer route.
A late denial may leave an already committed claim/canonical outcome; it withholds
the response and never invents rollback of completed remote work.

**Closure decision: full routing closure remains BLOCKED, not DONE.**

1. **R018 policy dependency:** the accepted boundary rejects different-owner
   attachment/renewal; there is no approved number-recycling detection,
   different-owner release/re-consent or retention/erasure/legal-hold policy in
   this routing authority. A provider-signed message proves present number
   control, not continuity of the former human. Cannot silently transfer, delete
   historical evidence or promise detection of physical carrier reassignment.
   The Founder subsequently approved customer-initiated same-account phone
   replacement with fresh portal authentication, new-number OTP and explicit
   consent, without automatic relationship reconnection. See the phone-change
   checkpoint below. Different-customer reassignment, carrier-recycling detection
   and retention/hold authority remain outside that approval.
2. **Qualification dependency, deliberately deferred:** production-schema
   two-customer ingress/replay/late revocation, provider handoff, pooled RLS,
   restart, migration replay and integrated Stop races must be executed on the
   candidate before full R002 acceptance. Static lint cannot substitute.
   This is not a request to violate the frozen final-only behavioral sequence.

No additional uncovered production entry was identified in the surfaces listed
above after the receipt-release repair. That bounded finding is not proof of
unexecuted races or closure of R018. The routing phase stays open pending its
policy boundary and final qualification; no automatic move to governed execution
is authorized by this report.

### Approved customer phone-change implementation checkpoint

The Founder explicitly approved implementing the proposed customer-initiated
phone-change flow in this continuous session. This is not permission to transfer
another customer's number, account or history, or to activate provider traffic.

Implementation surfaces are the Identity phone-change owner, four canonical
API endpoints, generated Identity client, same-origin authenticated BFF and the
portal profile's phone-change form. Migration 94 adds an actor/account/tenant/
membership-bound request that retains only masked destinations and versioned
HMAC candidates, source snapshot and constitutional evidence references.
Its FORCE-RLS owner follows the Identity schema's `web_session_owner`.
The private conflict function uses the existing isolated recognition principal,
current OWNER membership and a pinned search path; it returns no account identity.
Principal handoff preserves that function's RLS-admitted owner.

Start and confirm require nonfuture portal authentication no older than five
minutes, current OWNER membership, active Identity and a completed registration.
The replacement number receives a random six-digit destination-bound OTP through
the existing activation/template/admission/budget-gated dispatcher. Proof expires
after five minutes, five wrong codes expire it, and identical wrong-request replay
does not consume another attempt. Limits are one request per minute, three per
rolling hour and ten per rolling day for the registration. Dispatching/unavailable
delivery is explicitly unresolved and is never automatically resent.

Constitutional evidence runs outside database locks. The owning transaction
reacquires current Identity locks and reloads registration source, challenge and
membership before mutation. Confirmation requires the explicit versioned consent
to replace the number, revoke old WhatsApp access, preserve original-account
history and require fresh relationship approvals. It updates the verified profile
and consumes its new proof while cancelling old account-link authority and
revoking active/prepared WhatsApp channel bindings for the caller across their
account's membership scopes. Competing pending phone-change proofs expire.
All changes commit or roll back together; source substitution, expiry or a late
authority change denies promotion.

No conversation, guest history, participant, outbox recipient or original binding
is moved to the new number. Retained pending work remains fenced by the existing
current-route guards; possibly submitted originals retain historical receipt
correlation without redispatch. Fresh signed `LINK ...` confirmation and separate
explicit channel approval for each professional relationship remain mandatory.
OTP alone neither creates account authority nor completes a WhatsApp association.
Conflicting completed registration or historically confirmed foreign account-link
ownership blocks automatic change; account recovery is separate.

Status recovery and cancellation are current-owner commands. The portal keeps
phone and OTP only in component memory, exposes unknown-result recovery, clears
stale link UI after confirmed replacement and persists no phone/OTP in browser
storage. The BFF uses a current server-held access token, closed command schemas,
same-origin admission and no-store responses. The APIs accept no client tenant,
account, prior-number or routing authority.

Authored regressions cover full-schema owning commit and rollback, destination
collision, foreign challenge, freshness/future-time denial, consent, wrong-code
replay/exhaustion, failed delivery/replay, cancellation/rate limiting, post-evidence
membership revocation, concurrent confirmations, compatible new linking proof and
unchanged pending/unknown outbox recipients. Full-init assertions cover table RLS,
immutable request-column permissions and the conflict function's owner/grants.
Portal and BFF regressions cover consent, no sensitive storage, no automatic
dispatch, unknown-result recovery, fresh sign-in and closed authenticated commands.

This checkpoint is implementation evidence, not behavioral qualification or R018
acceptance. Final permitted diagnostics:

- Docker `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-phone-change -warnaserror`:
  PASS, zero warnings/errors, including authored phone-change regressions.
- Docker `tsc --noEmit --incremental false`: PASS for the Web tree, generated
  client and authored BFF/portal regressions using the runner's existing dependencies.
- Docker-backed `sh web/scripts/generate-api.sh`: PASS; canonical client regenerated.
- Docker `python scripts/wc124_init_chain_lint.py`: PASS, 96 SQL files, zero findings.
- Docker YAML parsing of `work-contracts/WC-134-requirements.yaml`: PASS.

Behavioral regressions remain deliberately
unexecuted until the frozen integrated qualification phase. No live OTP, provider
traffic, activation, cloud request or spend is authorized by this checkpoint.

Closure-inventory diagnostic validation:

- Docker `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-routing-closure -warnaserror`:
  PASS, zero warnings/errors.
- Docker `python scripts/wc124_init_chain_lint.py`: PASS, 95 SQL files, zero findings.
- Docker parsing of `work-contracts/WC-134-requirements.yaml`: PASS.
- Scoped whitespace checks: no findings.

The four newly authored receipt-release scenarios and full-schema function/grant
assertions compiled; they were not behaviorally executed. The customer wrapper's
fresh post-operation check still requires final integrated late-revocation evidence.
No milestone commit, PR, provider call, activation or spend occurred.

### Routing checkpoint - shared customer outbound reservation ledger

The traffic owner now exposes an internal customer outbound reservation command
requiring the entire confirmed route snapshot and matching dispatch coordinates.
It locks and reads the exact canonical attempted outbox under customer RLS,
including payload, attempt, unexpired lease, purpose and no-template policy.
Only then does a bounded database override select the original Demo service tenant
for the existing budget ledger and advisory lock in the same transaction.
Customer outbound, guest events and existing provider reservations consume the
same activation, rolling-minute and spend totals; no customer allowance is created.
Route and activation are rechecked before reservation commit and customer scope
is restored on both success and denial. Direct replies retain the approved zero
provider-message reservation cost; this does not implement model-cost accounting.

Delivery-status correlation now reads a routed customer's original reservation
from that service ledger through the restricted temporary override, requiring the
same sender, outbox and attempt. Observation/claim writes retain customer scope.
The existing same-tenant path remains unchanged.

Authored regressions cover snapshot and request substitution, missing scope,
candidate-only/missing-owner denial, non-PostgreSQL refusal and no ledger effects.
The forced-RLS mixed-budget fixture adds customer outbound competing with guest
inbound and service-provider reservations, payload mismatch, duplicate reservation
denial, customer-ledger invisibility, exact service-only ledger rows and scoped
delivery-reservation readback. These tests remain unexecuted.

The cloud provider adapter still refuses cross-tenant dispatch and does not yet
call this internal reservation command. Final dispatch/Stop/destination admission,
hosted-worker consumption and staged ingress remain open. This accounting
checkpoint alone does not authorize a send or accept R002/R007/R008.

Diagnostic validation in the pinned Docker .NET test runner:
`dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-shared-outbound -warnaserror`
PASS, zero warnings/errors. Scoped `git diff --check` PASS. Behavioral,
PostgreSQL race and live-provider execution remain deferred.

### Generation checkpoint - agent-specific execution and shared monetary owner

The candidate now separates `PROFESSIONAL_RESPONSE` generation from employment
interpretation in the existing durable PR dispatch coordinator. BP revalidates
the original accepted input, effective language, full mandate, confirmed
`TRIAL_ACTIVE`/`ACTIVE` relationship, admitted professional instance and exact
skill/prompt/model revisions. DMA, trading and agriculture do not share a generic
skill pool; profession-specific semantics remain outside BP/PR/AIR.

[Migration 95](../infrastructure/postgres/init/95-wc134-governed-conversation-generation.sql)
adds AIR admission/dispatch claims and immutable results, relationship-specific
sealed inference bindings, and the BP monetary ledger with FORCE RLS and narrow
grants. Only one concurrent original admission can reserve funds; duplicates
cannot poison its result. A known pre-reservation queue denial releases only
the admission claim. Unknown reservation receipts and claimed executions never
gain redispatch permission. Terminal monetary settlement is also immutable at
the database boundary and records full per-component-ceiling cost.

The monetary owner uses the existing messaging owner's rolling 24-hour window
and service-tenant advisory lock. Model, OTP and ordinary/customer outbound
reservations share `min(INR500, approved MaximumSpendInr)`, not separate pools.
The UTC `cost_day` is a reporting coordinate, not a midnight budget reset.
Unknown model usage retains its full reservation and attempt slot. Full monetary
or token overruns halt later model/message admission. Financial settlement after
Stop/expiry does not authorize content release.

The six private AIR/BP capability routes, signed BP-to-CE decisions/evidence,
workload registry grants, optional named mTLS listeners and dedicated CTG boundary
are wired. Missing configuration remains unavailable. This does not enable a
listener, publish a binding, install credentials or authorize provider calls.
The canonical candidate contract is
[conversation-generation.openapi.yaml](../architecture/reference/api-specs/conversation-generation.openapi.yaml).

Author review found that pre/post Ollama tag checks cannot exclude a transient
model rebind. The candidate tag-addressed adapter therefore explicitly refuses
dispatch before reservation or provider traffic. This enforces the already
approved immutable-model requirement; it does not admit an alternative backend.
An atomic digest-bound institutional invocation boundary remains necessary.
Ollama's [generation contract](https://docs.ollama.com/api/generate) names a model;
its standard response does not attest the exact manifest digest used.

### Candidate model parameter selection - 2026-11-08

The Founder requested a current free model selected through parameters rather
than hardcoded generation logic. The selected candidate binding value is
`model: qwen3.8:27b-q4_K_M`, not a floating `latest` alias.
The [official model entry](https://ollama.com/library/qwen3.8:27b-q4_K_M)
lists Qwen3.8 27.3B, Q4_K_M quantization, approximately 18 GB of weights and
Apache 2.0 licensing. This is a current general-purpose candidate, not evidence
that it is best for every admitted agent skill.

This records the intended parameter only: no active relationship binding,
approval evidence, model digest or tokenizer digest is invented or published.
The existing binding's `model` and `modelDigest` fields remain the execution
coordinates. Full artifact verification and sufficient inference-host memory
(weights plus context/runtime overhead) must precede publication. Model weights
have no local per-token fee; hosting, hardware and electricity are not free.
No model download, invocation, deployment change or removal of the immutable
dispatch guard accompanies this selection.

Other remaining exits:

- Fresh-owner canonical recovery of retained Temporal events remains separate.
  Recovery of an AIR-only completed receipt after the original deadline is not
  wired to that fresh authority. Original-owner completed replay is protected;
  extending the original execution mandate is forbidden.
- A lost BP reservation receipt remains unresolved with funds/slot held. No
  financial reconciliation or automatic release is claimed.
- Protected binding publication, approved evidence provenance, mandatory
  policy/plan materialization and stable environment budget tenancy remain
  qualification/owner-wiring obligations. No approval record is seeded here.
- Production PostgreSQL monetary contention, admission crashes, TLS/DI and
  final whole-chain behavior remain unqualified.

Authored, unexecuted regressions cover agent-specific operation separation,
exact token/text bounds, full overrun arithmetic, protected result replay,
unknown receipts, queued retry and duplicate admission; signed workload
positive/replay/peer/purpose/route/method/operation/audience/digest cases; CE private
model denial with preserved legacy actions; full-init RLS/grants; and actual
migration-backed model totals spanning midnight, foreign/expired-row exclusion,
per-component settlement and rejected terminal replacement.

Sources: [AIR regressions](../tests/ai-runtime/test_conversation_generation.py),
[PR operation separation](../tests/professional-runtime/test_conversation_execution.py),
[workload regressions](../tests/business-platform.Tests/WorkloadIdentityClientTests.cs),
[CE boundary regressions](../tests/constitutional-engine.Tests/Services/ConversationInferenceWorkloadMiddlewareTests.cs),
[model cost arithmetic](../tests/business-platform.Tests/ConversationWhatsAppFitness/ConversationModelCostTests.cs),
and [migration-backed ledger reads](../tests/business-platform.Tests/ConversationWhatsAppFitness/WhatsAppTrafficBudgetPostgresTests.cs).

Permitted Docker diagnostics:

- `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-generation -warnaserror`:
  PASS, zero warnings/errors (final workload test expansion recompiled before reporting).
- `dotnet build tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj --artifacts-path /tmp/artifacts/wc134-generation-ce -warnaserror`:
  PASS, zero warnings/errors.
- Python `compileall` and Ruff `--select E9,F63,F7,F82` on changed generation,
  transport, PR coordinator and authored Python regressions: PASS.
- AIR imports without lifespan/provider startup: PASS.
- `python scripts/wc124_init_chain_lint.py`: PASS, 97 SQL files, zero findings.
- Docker OpenAPI metadata validation: PASS, six routes, all local references,
  component-schema syntax and exact AIR property/required-field sets.
- Requirement-ledger YAML parsing and scoped whitespace checks: PASS.
- `python scripts/validate_requirement_ledger.py --changed-file work-contracts/WC-134-requirements.yaml`:
  PASS against the current Work Contract; no requirement acceptance is implied.

This checkpoint does not close R006/R007/R008 or the generation chunk. Behavioral
tests remain deferred. No model/OTP/provider traffic, activation, expenditure,
milestone commit, push or PR occurred.

### Offering alignment and original financial receipt recovery - 2026-11-08

The Founder clarified that each agent offering blends skill-specific LLM,
image/video/voice and customer-authorized channel capabilities, with an offering
cost pipeline. The existing
[DMA bundle definitions](../architecture/reference/billing/dma-bundle-definitions.md),
[WBE usage attribution](../src/billing-engine/meter/service.py) and
[trial allocations](../src/billing-engine/trial/service.py) remain the owning
commercial surfaces. This candidate model ledger is the Demo spend safety owner,
not a replacement customer offering, wallet, markup engine or generic skill pool.
Generation is not yet wired through all those offering allowances and meters.

Read-only Azure inspection found no deployed Ollama/inference app, no GPU profile
in the Demo environment, and an AI Runtime allocation of 0.5 vCPU/1 GiB. The
Qwen3.8 27B parameter above is therefore an inactive research candidate, not a
hardware-qualified recommendation or published binding. A paid hosted provider
may be considered; none has been selected, admitted or activated by this change.

Financial recovery implementation:

- Migration 95 adds customer-tenant-scoped budget receipts. Each receipt's
  original service tenant, customer tenant, execution and reservation are bound
  by a composite foreign key to the monetary reservation. Application grants
  permit only SELECT/INSERT; UPDATE/DELETE are not permitted.
- The BP owner creates the receipt in the same transaction as reservation and
  rejects another reservation for an execution already having a receipt,
  including when the current activation points at a different service tenant.
- Settlement locates its ledger through the persisted receipt, not current
  activation options. Original actor, relationship, idempotency key, request and
  full mandate still have to match the original ledger row. A terminal identical
  settlement replay returns before requesting new CE settlement evidence.
- The signed mTLS `reconcileConversationInference` route reads only the original
  financial state and coordinates. Missing receipts return UNRESOLVED, not an
  absence proof. No binding, professional text, release or dispatch permit is
  returned. No current activation or live original execution mandate is renewed.
- AIR read-only recovery can attach financial coordinates to an unresolved
  response, including when a crash prevented AIR result persistence. Its
  original stored result remains immutable. RESERVED, SETTLED and RELEASED
  financial states do not become professional completion or redispatch authority.

Sources:
[BP owner](../src/business-platform/Services/ConversationInferenceOwner.cs),
[migration](../infrastructure/postgres/init/95-wc134-governed-conversation-generation.sql),
[AIR recovery](../src/ai-runtime/conversation_generation.py),
[private contract](../architecture/reference/api-specs/conversation-generation.openapi.yaml).
Seven route grants and the matching private HTTP example are wired.

Authored regressions cover financial state without content/redispatch,
lost-reservation receipt recovery, a crash before AIR result save, foreign
reservation rejection, exact customer/execution/reservation lookup, changed or
removed activation, composite-FK rejection and full-schema RLS/narrow grants.
These are not executed acceptance tests.

Permitted Docker diagnostics:

- `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-financial-recovery -warnaserror`:
  PASS, zero warnings/errors.
- `python -m compileall -q src/ai-runtime/conversation_generation.py src/ai-runtime/conversation_generation_owner.py tests/ai-runtime/test_conversation_generation.py`:
  PASS with bytecode directed to container `/tmp`.
- `python -m ruff check --select E9,F63,F7,F82 src/ai-runtime/conversation_generation.py src/ai-runtime/conversation_generation_owner.py tests/ai-runtime/test_conversation_generation.py`:
  PASS.
- `python scripts/wc124_init_chain_lint.py`: PASS, 97 SQL files, zero findings.
- Docker OpenAPI/registry metadata checks: PASS, seven matching route grants,
  five AIR field/required wire shapes and valid component schemas. The initial
  metadata probe incorrectly treated the always-emitted result schema-version
  default as an input-required field; the corrected wire check passed.

Remaining chunk exits include bounded conversational context/resume and batching,
the full relationship-specific offering allowance/metering path, environment-wide
spend continuity across service-tenant changes, retained AIR professional content
under fresh-owner canonical recovery, protected binding publication/provenance and
an admitted provider. Idle conversation must not trigger inference, polling or
automatic summarization. Explicitly authorized background work is separate and
must remain bounded by its own work authority; this checkpoint does not claim
that those lifecycle scenarios have been completed or behaviorally qualified.

R006/R007/R008 remain BLOCKED. Behavioral tests remain deferred. No provider
traffic, model download, media creation, customer connector activation, deployment
change or expenditure occurred.

### Fresh-owner retained content recovery - 2026-11-08

The Founder selected this chunk before bounded conversation resume/batching and
full offering metering. The new path is restricted to retained completed
professional generation under separately persisted current recovery permission.
It never renews the original execution mandate or impersonates its actor.

- BP `readConversationInferenceContent` uses the actual stored reconciliation
  authority, requester/role/idempotency, source digest, projection/cursor and
  permission expiry. Both the requesting membership and original execution's
  account/membership/active participant are checked; legacy executions missing
  proven original Identity remain denied. Whole original mandate, canonical
  text/language and runtime identity must match. WhatsApp recovery checks original
  binding, same participant/conversation, current owner route and consent.
  It takes the sender lock before the Stop and execution locks, matching normal
  execution; provenance and service tenant are rechecked after locking so a
  concurrent route change cannot switch the recipient or introduce lock inversion.
- AIR `recoverConversationGenerationContent` has a separate closed request and
  workload purpose. BP read permission is checked before and after the
  Stop-scoped original result lookup. No claim/write, financial reconciliation,
  reservation, release, model dispatch or deadline renewal occurs.
- The read returns the retained result plus its immutable database persistence
  timestamp. PR does not invent the original completion time or use the fresh
  read time as a new original event.
- PR reconstructs only the exact retained generation payload, checks the accepted
  request hash and deterministic original runtime identity, and uses fresh-reader
  context rather than original-actor context. A dedicated read-only Temporal
  query supplies the original dispatch source and ordered retained events.
- Only bounded COMPLETED AIR output with original reservation/evidence becomes a
  terminal canonical reconciliation projection. Partial/competing runtime output,
  changing runtime source, missing legacy dispatch source, expired read permission,
  unavailable owner and unknown AIR result do not become new work or false
  completion. The runtime is re-read before release; no Temporal signal/activity
  is started. Stable source events and durable AIR timestamp make repeated
  projection candidates stable; BP's existing atomic reconciliation controls
  remain responsible for customer-visible output and deduplication.

PostgreSQL microsecond normalization is applied when matching stored permission
expiry to its original wire value; this does not extend the permission.

Authored, unexecuted regressions:

- AIR expired original mandate/fresh different reader, revocation before or after
  retained access, missing result and reader binding drift, with no new work.
- PR retained AIR-only result after original expiry, stable original source/hash,
  canonical completion without workflow mutation, unknown result, denied read,
  partial output, changed original request/source and missing/future persistence
  timestamp. Repeated recovery must return identical projection candidates.
- BP migration-backed current requester/original membership/participant,
  projection/Stop/source denial and read-only success; existing canonical recovery
  replay/rollback tests remain the controlling projection regressions.
- Shared workload validation admits OWNER/MANAGER only for the distinct content
  recovery purpose, not for ordinary model-evidence calls.

Sources:
[BP content owner](../src/business-platform/Services/ConversationInferenceOwner.cs),
[AIR content recovery](../src/ai-runtime/conversation_generation.py),
[AIR retained store](../src/ai-runtime/conversation_generation_store.py),
[PR projection](../src/professional-runtime/routers/conversation_execution.py),
[AIR regressions](../tests/ai-runtime/test_conversation_generation.py),
[PR regressions](../tests/professional-runtime/test_conversation_execution.py),
[BP PostgreSQL regressions](../tests/business-platform.Tests/Conversation/ConversationReconciliationPostgresTests.cs).

Candidate contract now declares nine private routes. Docker compilation of BP/CE
test projects passes with zero warnings/errors; Python compilation, fatal/static
Ruff selectors and PR router import without lifespan/provider startup pass.
Contract/schema/registry metadata and ledger checks are recorded after the final
timestamp-envelope change; behavioral acceptance is not implied.

Founder requested local commits, then explicitly selected "Keep behavioral tests
deferred; continue implementation and commit when complete" when informed that
mandatory commit hooks run behavioral gates. Changes remain uncommitted; hooks
will not be bypassed. No provider/model/OTP traffic, activation or spend occurred.
Bounded resume/batching and full offering metering remain the next implementation
chunks. R006/R007/R008 remain BLOCKED pending full implementation and qualification.

### Bounded canonical resume

Founder instruction, 2026-11-08: proceed unattended through bounded resume/batching,
full offering metering, Docker behavioral qualification and PR preparation. This
supersedes behavioral-test deferral; it does not approve activation, pricing,
provider traffic, institutional review or self-merge.

BP now supplies an owner-checked, digest-bound context with inference resolution
and reservation. The approved static model binding remains separately validated:
canonical history is not an operator-authored model policy or execution authority.
The context is limited to the same tenant, relationship, conversation and agent
skill. Selection uses the original input's sequence and acceptance time, not a
fresh wall clock: at most twelve completed, nonpartial CUSTOMER/PROFESSIONAL turns
from the preceding seven days, totaling at most 8000 UTF-16 units. The whole newest
contiguous selected suffix is retained; oversized turns are not split or skipped
to include older history. Turns that complete after the original acceptance are
excluded, so a retry does not incorporate later results.

The existing canonical store remains the only transcript store. No idle timer,
model polling, automatic model summary or cross-agent/customer history transfer
is introduced. A returning customer causes context selection only as part of an
authorized inbound execution. AIR verifies context coordinates, digest, ordered
source IDs and exact aggregate bounds before use; the existing bound tokenizer
still caps the entire prompt at 8192 input tokens.

Nonempty history requires the explicitly admitted
`RAW_SYSTEM_CANONICAL_HISTORY_V1` prompt wrapper; its identifier participates in
the existing immutable prompt artifact digest. Existing
`RAW_SYSTEM_DOUBLE_NEWLINE` bindings cannot silently acquire different prompt
semantics. History is serialized as untrusted reference data, never current
authority or approval. Reservation evidence records the context digest, and a
changed context during reservation/current dispatch causes denial.

Docker behavioral qualification exposed defects in the earlier recovery chunk:
certificate-only PEMs were loaded using a private-key loader; BP fresh content
reads omitted the shared CE Stop-table check; generation and recovery took Stop
and execution locks in different order; system-response OpenAPI metadata was not
fully wired. These are corrected without relaxing current authority. Fixtures now
compare PostgreSQL JSONB/timestamps by canonical value, not serialization spacing
or equivalent UTC spelling.

Sources:
[BP context reader](../src/business-platform/Services/ConversationResumeContextReader.cs),
[BP exact selection regressions](../tests/business-platform.Tests/Conversation/ConversationResumeContextReaderTests.cs),
[AIR bounds and prompt regressions](../tests/ai-runtime/test_conversation_generation.py).

**Remaining, not accepted:** durable short-message batching across separate
webhooks, complete WBE-owned relationship/offering allowance and component
metering, environment-wide shared spend continuity, and final integrated
qualification/commit/PR gates. The existing synchronous WhatsApp ingress holds
sender/route authority during processing; an in-memory debounce under that lock
would neither collect concurrent callbacks nor survive worker restart. It is not
used as a substitute for a durable, canonical-source-bound queue.

Metering integration must use WBE's actual institutional thread catalog,
provider account mapping, append-only invocation ledger, current accepted
relationship bundle and agent/version-specific trial allocation. The existing
`MeterService.record_usage` has no generation transport caller and its
`thread_catalog.thread_type/provider_account_id` lookup does not match the real
`institutional.thread_catalog.thread_id/provider` schema. Those gaps are not
resolved by writing a second BP customer wallet or choosing unapproved DMA
pricing. This checkpoint does not claim full offering metering or PR readiness.

#### Targeted Docker evidence after behavioral-test authorization

Executed from the isolated WC-134 worktree with project name `waooaw-wc134`;
no host interpreter, provider request or cloud action was used.

- Python Compose runner, `pytest tests/ai-runtime/test_conversation_generation.py -q`
  with AIR/trust-layer `PYTHONPATH`: **49 passed**.
- Python Compose runner, `pytest tests/professional-runtime/test_conversation_execution.py tests/professional-runtime/test_employment_air_gateway.py -q`
  with PR `PYTHONPATH`: **203 passed**.
- Docker socket wrapper and explicit `/var/run/docker.sock` mount,
  `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-budget-final -warnaserror --filter "FullyQualifiedName~WhatsAppTrafficBudgetPostgresTests" --logger "console;verbosity=minimal"`:
  **8 passed**, zero failed or skipped.
- Same Docker runner,
  `dotnet test tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj --artifacts-path /tmp/artifacts/wc134-ce-final -warnaserror --filter "FullyQualifiedName~ServiceBoundaryTests" --logger "console;verbosity=minimal"`:
  **34 passed**, zero failed or skipped.

The receipt fixture now models a separate signed AIR callback using the standard
tenant command interceptor without retaining the original WhatsApp ingress scope.
Its outbox fixture grants the UPDATE privilege needed for row locking. Production
grants, RLS and tenant-interceptor precedence are unchanged. Full staged-tree
hooks, release qualification, batching and WBE offering integration are not
established by these targeted results.

#### Identity qualification and commit-gate repair checkpoint

Mandatory implementation hooks exposed unqualified Identity and attachment paths.
Focused Docker execution identified omitted canonical migration 47 in the HTTP
fixtures, an unverified manually started registration, and missing account-link
subject migration 77. Fixtures now retain the real verification grants and require
their own destination-bound proof. No production authority check was bypassed.

Runtime defects corrected during qualification:

- Account-link creation's `Location` now resolves to its explicit MVC action name.
  The integration fixture follows the returned URI and verifies the same link.
- New links store the verified plain actor subject. Owned reads, relationship
  attachment revalidation and phone replacement cancellation accept existing
  issuer-qualified links only for the matching verified actor and current authority.
- EF records the immediate challenge-to-phone-change dependency. Consumed proof
  and completed replacement evidence are saved before updating the contact, within
  the same original transaction; original completion snapshots remain immutable.
- Migration 96 permits current Identity organisation row locks without writes,
  restricts link updates to transition columns, and enforces canonical 32-hex
  Identity matching. Replay and source-column privilege regressions pass.
- Migration 73 creates the completed-contact index before registration backfills,
  avoiding pending deferred-trigger events during index creation on replay.

Docker evidence, without provider calls, deployment or activation:

- `csharpier check src/business-platform`: **PASS, 139 files checked**.
- `sh scripts/validation_control/run_dotnet_quality_gate.sh src/business-platform/business-platform.csproj wc134-identity-quality`:
  **PASS, build zero warnings/errors**. The separate directory check above covers
  C# source, not merely the project manifest.
- `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-identity-final -warnaserror --filter "FullyQualifiedName~CustomerPhoneChangePostgresTests|FullyQualifiedName~IdentityCompletionPostgresTests|FullyQualifiedName~CustomerIdentityJourneyHttpPostgresTests|FullyQualifiedName~CustomerIdentityProgramHostTests" --logger "console;verbosity=minimal"`:
  **63 passed, zero failed/skipped**.
- After final SQL formatting,
  `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-identity-resume-acceptance -warnaserror --filter "FullyQualifiedName~CustomerPhoneChangePostgresTests|FullyQualifiedName~WhatsAppAccountLinkConfirmationTests|FullyQualifiedName~ConversationResumeContextReaderTests|FullyQualifiedName~Program_RegistrationMobile_DestinationBindingAndCooldownPersistInPostgres" --logger "console;verbosity=minimal"`:
  **76 passed, zero failed/skipped**. This includes both canonical and legacy link
  cancellation, immutable snapshots, restricted grants, migration replay and
  exact bounded resume selection.
- `sqlfluff lint infrastructure/postgres/init/73-wc134-required-verified-whatsapp-registration.sql infrastructure/postgres/init/94-wc134-customer-phone-change.sql infrastructure/postgres/init/96-wc134-runtime-identity-row-lock-policy.sql --config .sqlfluff`:
  **PASS**. Existing deprecated/unknown configuration warnings remain; no lint
  suppression or success-shaped shell fallback was used. Actor columns retain
  their declared canonical `C` collation.

These Identity results alone do not clear the entire implementation commit gate.
The subsequent attachment and budget/reply qualification below supersedes the
earlier missing-authority fixture status. Durable batching, WBE offering metering,
full qualification and PR submission remain open.

#### Attachment and remaining budget/reply qualification checkpoint

Relational attachment now uses the canonical full-schema Identity service,
verified actor, current OWNER membership and original confirmed account link.
Missing/revoked Identity and foreign-link cases remain denied. Migration 97
repairs the missing contact tenant policy exposed by migration 60's FORCE RLS:
`business_app` and `bp_owner` can read/update only their current tenant's contacts,
and neither can retarget a contact to another tenant. No bypass privilege or
replacement Identity authority is introduced.

The remaining focused WhatsApp failures were fixture mismatches, not permission
to weaken production guards. Tests now use the admitted guest recipient, isolate
per-guest limits from activation/minute limits, assert final-reply slot reservation,
bind callbacks to their actual app/WABA/recipient, and provide the canonical
outbound contribution owner. The exhausted-budget/STOP regression uses PostgreSQL
so provider-claim lease release executes against a relational database. Invalid
sender admission is denied before borrowing a recorded event. Reply assertions
deserialize canonical text instead of comparing JSON-escaped source text.

Docker evidence:

- `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-attachment-negative -warnaserror --filter "FullyQualifiedName~WhatsAppAttachmentPostgresTests" --logger "console;verbosity=minimal"`:
  **18 passed, zero failed/skipped**, including policy replay, own-tenant updates,
  foreign reads/writes and retarget denial for both application and table owner.
- `sqlfluff lint infrastructure/postgres/init/97-wc134-whatsapp-contact-tenant-policy.sql --config .sqlfluff`:
  **PASS**, with only the existing configuration warnings.
- `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-budget-reply-repair-4 -warnaserror --filter "FullyQualifiedName~WhatsAppGuestTrafficBudgetTests|FullyQualifiedName~WhatsAppDemoProviderTests|FullyQualifiedName~CeFit09WebhookIngressTests|FullyQualifiedName~Wc121_StatusUsesSharedTruthAndEndSessionLeavesRelationshipActive" --logger "console;verbosity=minimal"`:
  **134 passed, zero failed/skipped**. Compilation uses warnings as errors.

The full Docker BP test/coverage commit gate,
`sh scripts/validation_control/run_dotnet_test_gate.sh business-platform tests/business-platform.Tests/business-platform.Tests.csproj`,
completed with **1966 passed, 37 failed, zero skipped, 2003 total**. Coverage
acceptance was not reached because test execution failed. The focused passes
above are not full-gate clearance.

Additional qualification corrected a legacy contact fixture's missing migration
76 and used the sender's original progress timestamp when checking destination
verification across replays. Both signed-account-link variants pass in the
subsequent five-test selector; three other cases remained failing at that point.
The full-schema failure is specifically an unexpected table-level UPDATE grant
on `conversation_delivery_observations`; do not broaden privileges or weaken its
assertion. The first-contact fixture now reaches consent evidence/retry checks
with a genuinely later sender timestamp and asserts exact provider event IDs,
including unsupported input. Its later budget/timeline expectations still need
qualification. The latest five-test diagnostic run completed before shutdown:
**two passed, three failed**. Both signed-account-link variants pass. Delivery
observations remain owned by `bp_owner`, but `business_app` has table-level
UPDATE/DELETE. First-contact exact provider IDs pass; its timeline assertion
expects five messages and receives six. These are unresolved failures, not PASS.

Founder requested parking for Codespace restart. Implementation commits, durable
batching, WBE-owned offering metering, release qualification and PR submission
remain open. No provider call, activation, deployment, cloud mutation or spend
was performed. Signing and implementation hooks remain active.

#### Resumed BP qualification and public recovery evidence

Founder direction "resume WC-134" continues the existing office, bootstrap and
implementation/testing/commit/PR authority; no bootstrap repetition or new
activation authority is implied.

The original 37 full-suite failures have been repaired and qualified in their
owning selectors. Migration 82 explicitly revokes delivery-observation
UPDATE/DELETE and outbox/Stop-latch DELETE inherited from migration 02's default
future-table grants. Migration 85 grants `ai_runtime_app` schema USAGE for its
already admitted Stop-lock functions. Neither grants a Stop bypass. Strict Docker
SQL lint for both migrations passes.

Relational fixtures now preserve actual tenant/Identity/role/evidence admission,
schema-qualified deferred constraints, exact row-lock privileges, canonical
original SEND evidence and early owner-gateway configuration. First-contact
assertions cover exact provider event IDs, immutable consent replays, unsupported
media's GUIDE-only limitation and final-reply-slot-aware per-sender budgets.
Focused qualification passed 134 cases plus the final two first-contact cases in
separate runs; the last guest fixture edit was formatted in Docker.

Full Docker command:
`sh scripts/validation_control/run_dotnet_test_gate.sh business-platform tests/business-platform.Tests/business-platform.Tests.csproj`
through the `waooaw-wc134` Compose runner and Docker socket wrapper:
**2003 passed, zero failed/skipped**; warnings-as-errors build: **PASS**, zero
warnings/errors. **The gate still FAILS:** line coverage **87.31%**, branch coverage
**77.03%**, below the unchanged **90% / 80%** acceptance thresholds.
Cobertura source:
`test-results/coverage/business-platform/3c78e93f-a243-4834-9982-90fb0fb09eaa/coverage.cobertura.xml`.
This supersedes the parked test-failure status, not the incomplete delivery status.

Coverage diagnosis found unexecuted public reconciliation admission/recheck and
generation-owner reserve/source/settle paths. New public recovery regressions use
the real migration-backed tenant application role and current Identity, rather
than directly calling only the projection helper. They cover a fresh different
reader after original mandate expiry, completion replay without a second CE or
runtime call, UNKNOWN reread without renewed evidence or a false projection,
changed idempotent requests, unavailable/denied/empty CE evidence, owner/projection
drift after CE or remote read, shared Stop and malformed remote coordinates.
The initial test run exposed invalid UNKNOWN fixture digests; the fixture now
omits result/request digests as required by the closed wire contract.

Docker targeted command:
`dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-public-recovery-final -warnaserror --filter "FullyQualifiedName~PublicRecovery" --logger "console;verbosity=minimal"`:
**12 passed, zero failed/skipped**. These targeted passes do not establish the
full coverage thresholds. No coverage exclusion or threshold reduction was made.

The scoped bounded-resume selector commit attempt was **blocked by active
implementation hooks**. The first causal failure was WC-134 Web TypeScript lint;
the hook's BP snapshot also contained the initial three new recovery fixture
failures, before the targeted correction above. No commit or hook bypass is
claimed. Gitleaks, TypeScript dependency scan and BP static quality passed in
that attempt. Hook manifest:
`5b50ab4d1daa084a3e07449bd3b886bf1ea428ac/precheck-manifest.json` in the shared Git
precheck cache.

The Web repairs are restricted to WC-134 Identity surfaces: native semantic
`output` status elements retain paragraph layout; optional command keys reset
without deleting object properties; test environment cleanup uses the existing
repository `Reflect.deleteProperty` pattern. Account-link tests now assert that
only the recovery link UUID, not the encrypted instruction, is stored in session
storage and await completed approval/status responses before relationship
selection. Docker `biome lint` on the five changed source/test files: **PASS**,
two existing style warnings. Docker
`jest --runInBand --runTestsByPath app/api/identity/account-links/route.test.ts app/api/identity/phone-changes/route.test.ts components/portal/WhatsAppAccountLink.test.tsx components/portal/WhatsAppPhoneChange.test.tsx`:
**35 passed, four suites passed**. Docker `tsc --noEmit --incremental false` on
the complete Web snapshot: **PASS**.

The evidence checkpoint is committed separately with documentation hooks and
configured signing; implementation remains independently gated. Remaining
implementation, coverage qualification, durable separate-webhook batching,
WBE-owned offering/component metering and final PR gates remain open. No provider
request, download, activation, deployment, cloud mutation or spend occurred.
