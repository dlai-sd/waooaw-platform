# DMA Packages B1/B2 Content And Social Publication Solution Contract

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Status | CANDIDATE FOR FOUNDER ACCEPTANCE - IMPLEMENTATION, DEPLOYMENT, PROVIDER CONNECTION, PUBLICATION, AND ACTIVATION UNAUTHORIZED |
| Version | `1.0.0-candidate.1` |
| Parent requirement | `architecture/reference/components/dma-onboarding-and-autonomous-operation-enterprise-requirements.md` Sections 13-16 and 20.4 |
| Generic employment baseline | WC-114/WC-115 Conversational Employment Protocol |
| Package A baseline | WC-116 and DMA employment manifest for Skills 0/1/2 |
| Implementing office | Platform IT Expert (INST-010), only after separate Founder authorization under WC-117 |
| Constitutional basis | C-001, C-003, C-005, C-007, C-023, C-026, C-035, C-041, C-048, C-049, C-051, C-055, C-059, C-063, C-065, C-066, C-070, C-071, C-078, C-079, C-080, C-094; ADR-002, ADR-003, ADR-009, ADR-014, ADR-020, ADR-021, ADR-024, ADR-029, ADR-031, ADR-035 |

## 1. Objective And Package Closure

This contract closes the Solution Architecture for two dependency-ordered but independently
qualified DMA packages:

| Package | Bounded outcome | Consequential side effect | Activation boundary |
|---|---|---|---|
| B1 - Content production | Customer-input-driven Instagram/Facebook drafts and an approval-ready calendar | None. Draft creation, rendering, review, correction, and approval records only | Separate B1 activation decision |
| B2 - Social publication and measurement | Exact approved content is published through a scoped customer connection and supported outcomes are observed | External publication, deletion/correction where supported, and read-only analytics retrieval | Separate B2 activation decision after B1 qualification |

B1 and B2 may share one implementation branch and WC-117 evidence package, but they are not one
authority grant. B1 qualification cannot activate B2. B2 qualification cannot authorize a provider
connection, publication, customer traffic, or environment deployment.

Package C paid media, paid boosting, ad-account scopes, spend, audience activation, lead handling,
autonomous crisis response, additional social channels, and institutional marketing are excluded.

## 2. Protected Invariants

1. Business Platform (BP) remains the sole ordinary public facade, relationship authority, customer
   projection owner, and public error mapper.
2. AI Runtime (AIR) produces proposals only. Model output cannot approve content, authorize
   publication, select a customer account, or report publication success.
3. Professional Runtime (PR) owns execution coordination, durable external intent, and ambiguous
   outcome reconciliation; it does not own customer approval or credentials.
4. Constitutional Engine (CE) validates every external tool action before dispatch. Publication,
   correction, deletion, and connected analytics retrieval are separately validated actions.
5. oauth-vault remains the sole owner of customer-delegated Meta tokens under ADR-021. Tokens do not
   enter the DMA image, BP, PR state, AIR prompts, MCP request logs, evidence payloads, or source.
6. Azure Key Vault remains the cloud owner of environment platform secrets under ADR-014. Customer
   OAuth tokens remain in oauth-vault's per-tenant encryption boundary; they are not duplicated as
   ad hoc Key Vault secrets.
7. WBE remains the commercial eligibility and usage authority. No model or provider call bypasses
   an accepted entitlement, cost unit, or usage ceiling.
8. Draft approval and publication authority are distinct. An `APPROVED` draft has zero external
   side effects until a PR-owned publication intent from the exact accepted plan passes version, account, credential,
   assurance, Decision Space, CE, WBE, and Stop checks.
9. Provider acceptance, a returned identifier, or an HTTP success code is not publication success.
   `PUBLISHED` requires reconciled provider evidence for the exact intent and content digest.
10. Missing, placeholder, expired, revoked, stale, partial, disputed, rate-limited, or unknown input
    cannot become ready, authorized, published, measured, or successful.
11. Emergency Stop fences new dispatch, preserves reconciliation, and rejects late results as new
    authority. It never deletes immutable intent, receipts, corrections, or evidence.
12. One customer's assets, tokens, accounts, drafts, calendars, publications, analytics, costs, and
    evidence cannot cross tenant, relationship, location, channel account, or agent instance.
13. Trial mode may generate clearly labelled samples and calendars. It cannot connect a real
    customer publishing account or publish externally unless a later accepted trial policy
    explicitly authorizes that exact side effect.
14. Customer claims, offers, rights, authorship, likeness, disclosures, tags, accessibility text,
    and prohibited topics are customer-controlled facts. The DMA cannot fabricate or infer them as
    approval.
15. Provider-specific capabilities and limits are versioned observations, not permanent promises.
    A failed or stale capability probe fails closed and does not change an approved plan silently.

## 3. Reuse And Build-Versus-Adopt Decisions

| Concern | Decision | Reason |
|---|---|---|
| Employment, plan, commands, approval, versions | Reuse WC-115 BP operations and command family | No DMA-specific public lifecycle or command |
| Model inference | Reuse AIR Provider Abstraction Layer and Provider Selection Engine | No direct OpenAI, Grok, or provider SDK in DMA |
| External tools | Reuse ADR-020 MCP Tool Registry and CE pre-call validation | One governed chokepoint |
| Customer OAuth | Reuse ADR-021 oauth-vault | Existing tenant-isolated acquisition, refresh, health, and revocation owner |
| Platform API secrets | Reuse ADR-014 environment Key Vault references | No committed or image-baked secret |
| Instagram/Facebook | Adopt official Meta APIs behind `instagram-mcp` and `facebook-mcp` | No browser or DMA direct provider client |
| Analytics | Reuse `platform-analytics-mcp` with read-only purpose-bound operations | Publication MCPs do not become analytics stores |
| Customer-visible state | Reuse BP relationship workspace projections | No duplicate portal/channel truth |
| Scheduling | Reuse admitted calendar/plan semantics and `scheduling-mcp` only if already qualified | Calendar does not grant publication authority |
| Durable customer asset delivery | Reuse the repository-approved customer-asset owner when pinned by implementation baseline | No new storage product or unsigned public URL may be invented in WC-117 |

If no accepted customer-asset owner can provide a provider-fetchable, time-bounded media reference,
B1 may qualify text-only draft behavior and asset metadata, but any dependent media story and all B2
media publication stories stop. The Platform IT Expert may not select or deploy a new storage
service inside WC-117.

## 4. Stable Capability And Skill Boundary

| Stable skill | Package | Required behavior | Prohibited behavior |
|---|---|---|---|
| `CONTENT_STRATEGY_AND_CALENDAR` | B1 | Convert accepted plan inputs into versioned themes, briefs, calendar items, measures, and review points | Publication, spend, account mutation |
| `SOCIAL_CONTENT_CREATION_AND_PUBLISHING` B1 mode | B1 | Produce Instagram/Facebook channel drafts, asset/rendering metadata, tags, disclosure, alt text, evidence, cost, and limitations | Provider calls or implied publication |
| `VISUAL_AND_VIDEO_CONTENT` B1 mode | B1 optional dependency | Produce or transform assets only through admitted tools with rights and likeness authority | Unlicensed asset use, unapproved digital twin/voice, external publication |
| `SOCIAL_CONTENT_CREATION_AND_PUBLISHING` B2 mode | B2 | Dispatch an exact approved content version to one exact authorized account and reconcile its outcome | Paid boosting, ad scopes, account setup, cross-post inference |
| `MARKETING_PERFORMANCE_AND_IMPROVEMENT` social slice | B2 | Retrieve supported post/account observations, disclose coverage and attribution limits, and propose the next improvement | Fabricated conversion, guaranteed result, hidden benchmark |

Numeric legacy labels remain aliases only. The admitted manifest must declare stable ID, version,
package, mode, inputs, dependencies, side effects, approval mode, cost unit, evidence, degradation,
and availability. Documentation is never availability.

## 5. Owner And Trust-Boundary Map

| Owner | Owns | Must not own |
|---|---|---|
| BP | Draft/calendar customer projection, approval/correction command validation, publication request facade, safe status/errors | Tokens, provider clients, model authority |
| DMA adapter | Channel semantics, content constraints, evidence interpretation, improvement meanings | Public API, customer authority, credentials |
| AIR | Scrubbed proposal generation, provider-neutral inference provenance | Approval, publication, analytics truth |
| PR | Durable publication intent, dispatch/reconciliation workflow, provider correlation | Token storage, content approval |
| CE | Action validation and append-only constitutional evidence | Content generation or provider execution |
| WBE | Entitlement, cost/usage unit, commercial consequence | Publication result |
| oauth-vault | Customer OAuth acquisition result, encrypted tokens, refresh, health, revocation | Content, analytics, provider business logic |
| `instagram-mcp` / `facebook-mcp` | Provider contract translation and exact provider receipts | Customer approval, token persistence, retry policy authority |
| `platform-analytics-mcp` | Read-only supported observations and provider metadata | Attribution decisions or customer outcome truth |
| Key Vault | Per-environment platform secrets and oauth-vault master key | Customer content, analytics, approval state |
| Customer-asset owner | Immutable asset version, rights metadata, retention and provider delivery reference | Publication authority |

## 6. Credential, Secret, And Placeholder Contract

### 6.1 Environment and customer compartments

- Demo, UAT, and Production use separate Key Vaults and separate oauth-vault data boundaries.
- Platform-owned Meta app secrets and model-provider API keys are environment secrets referenced from
  the environment Key Vault by managed identity.
- Customer Meta grants are stored only by oauth-vault under the server-derived tenant,
  relationship/contract, platform, account, scope set, token version, and expiry.
- oauth-vault encryption remains per tenant with the environment master key in Key Vault as defined
  by ADR-021. This is the canonical customer compartment; a shared secret name prefix alone is not
  a security boundary.
- Workload identities receive only the minimum Key Vault or oauth-vault operation required for their
  purpose. A shared identity with cross-customer token retrieval is prohibited.

### 6.2 Placeholder semantics

Committed manifests and deployment templates may contain non-secret reference identifiers such as:

```text
secretref://demo/platform/meta-app-secret
secretref://demo/platform/llm-provider-key
oauthref://{tenant}/{relationship}/meta/{account}
https://provider.invalid/not-configured
```

They are configuration schema examples, not usable credentials or endpoints. The implementation must
classify `.invalid`, `CHANGEME`, `PLACEHOLDER`, empty, fixture, and unresolved `secretref`/`oauthref`
values as `NOT_CONFIGURED`; readiness, deployment qualification, and publication must fail closed.
No dummy secret value is written to Key Vault merely to satisfy existence checks.

Implementation and Docker qualification must proceed without waiting for live Founder/customer keys
by using local protocol emulators, deterministic fixtures, and secret-reference contract tests.
Hosted provider acceptance remains a separate evidence class and cannot be replaced by those tests.

### 6.3 Demo policy

- Demo may use Meta development-mode assets owned by registered app roles/testers, with no claim that
  an external customer account is supported.
- Demo customer tokens remain in the Demo oauth-vault customer compartment; platform app secrets
  remain in the Demo Key Vault.
- OpenAI, xAI/Grok, or another provider is not assumed to have a permanent free tier. Demo may use an
  explicitly credited or funded provider account accepted by PSE policy, or the admitted local/test
  provider path. Absence of a usable provider credential returns `NOT_CONFIGURED` or the approved
  degraded mode; it never triggers an unapproved provider, data-sharing program, or hidden spend.
- Production customer OAuth grants, secrets, content, and analytics never enter Demo.

## 7. B1 Content Contract

### 7.1 Required inputs

Every draft binds exact versions of:

- tenant, relationship, agent instance, trial/hire mode, selected stable skills, manifest, plan, and
  Decision Space;
- brand identity, approved claims/offers, audience, language, location, prohibited topics, and
  customer correction state;
- asset source, owner, rights basis, permitted channels/uses, likeness/voice authority, expiry, and
  required disclosure;
- calendar item, channel/account class, content objective, call to action, tag policy, accessibility
  requirement, and approval mode;
- prompt policy, model policy, provider/model identity, input digest, output digest, evidence
  references, cost/usage record, confidence, assumptions, and limitations.

Missing mandatory input yields `NEEDS_INPUT`; it cannot be substituted by generated facts.

### 7.2 Draft aggregate

The immutable `SocialContentDraftVersion` contains:

- `draftId`, monotonic `draftVersion`, `supersedes`, canonical content digest;
- channel renderings for Instagram and/or Facebook with text, media references, alt text, tags,
  disclosures, link/call-to-action, and provider-capability profile version;
- rights and customer-input references, not raw credentials or unnecessary personal data;
- provenance, evidence, cost/usage, limitations, policy findings, and required approvals;
- calendar identity, earliest/latest publish window, time zone, tolerance version, and materiality;
- state and customer-safe blocked/next-action projection.

Legal states are:

```text
PROPOSED -> NEEDS_INPUT | READY_FOR_REVIEW | WITHDRAWN
NEEDS_INPUT -> PROPOSED | WITHDRAWN
READY_FOR_REVIEW -> CHANGES_REQUESTED | APPROVED | WITHDRAWN
CHANGES_REQUESTED -> PROPOSED | WITHDRAWN
APPROVED -> SUPERSEDED | WITHDRAWN
```

Correction always creates a successor version. Approval binds one exact digest/version and does not
flow to successors. A material plan, claim, asset-right, account, channel, policy, or calendar change
relocks the affected draft.

### 7.3 B1 operations

B1 uses WC-115 operations and commands; it adds no DMA-specific public endpoint:

| Existing operation/command | B1 use |
|---|---|
| `getEmploymentPlan*` | Read exact accepted content strategy/calendar plan |
| `APPLY_CANDIDATE_PATCH` | Apply a validated customer fact or draft correction |
| `SUBMIT_PLAN_FOR_REVIEW` | Present an exact calendar/draft set for review |
| `ACCEPT_PLAN_VERSION` | Accept the exact plan/calendar version, not publication |
| `ACKNOWLEDGE_MATERIAL_CHANGE` | Relock affected drafts after a material change |
| `RESCHEDULE_WITHIN_TOLERANCE` | Move an item only inside accepted calendar tolerance |
| `REQUEST_REASSESSMENT` | Refresh missing/stale input, capability, cost, or evidence |

AIR proposal operations remain private and proposal-only. Content generation does not invoke a
publishing MCP tool.

## 8. B2 Publication Contract

### 8.1 Publication preconditions

One publication intent is created only when all of the following are current and exact:

1. B1 is qualified for the candidate and the draft state is `APPROVED`.
2. Draft version/digest, calendar window, channel rendering, asset version/rights, and disclosures
   match the request.
3. Hire/trial policy, entitlement, WBE eligibility, cost ceiling, Decision Space, assurance, customer
   account selection, approval, and CE validation allow the exact action.
4. oauth-vault health is `VALID` for the exact tenant/relationship/platform/account/scope set.
5. Provider capability/rate-limit profile is fresh and supports the requested rendering.
6. Emergency Stop is not active and the execution can still be safely cancelled or reconciled.

### 8.2 Tool operations

The Tool Registry exposes closed versioned operations behind existing MCP owners:

| Tool | Purpose | Consequence |
|---|---|---|
| `instagram.post_content` | Create/process/publish one exact Instagram rendering and return provider correlation | Consequential |
| `instagram.get_publish_status` | Reconcile container/media status for the original intent | Read-only reconciliation |
| `instagram.delete_content` | Delete one exact published media object when supported and separately authorized | Consequential correction |
| `facebook.post_content` | Publish one exact Facebook Page rendering and return provider correlation | Consequential |
| `facebook.get_publish_status` | Reconcile original Page publication | Read-only reconciliation |
| `facebook.delete_content` | Delete one exact Page post when supported and separately authorized | Consequential correction |
| `platform_analytics.get_instagram_insights` | Read supported observations for exact media/account/window | Read-only connected data |
| `platform_analytics.get_facebook_insights` | Read supported observations for exact post/Page/window | Read-only connected data |

Every consequential call has a distinct CE action type and idempotency identity. MCP servers retrieve
the token for the exact operation purpose from oauth-vault; callers never receive a reusable token.
Provider SDK response shapes remain private to MCP servers.

No DMA-specific public publication command is introduced. PR creates a publication intent only while
executing the exact accepted plan/calendar item through the existing admitted Operations path. A
customer correction, material change, Stop, or approval withdrawal uses existing WC-115 commands and
fences that operation. If the accepted PR Operations path cannot represent this trigger without a
new public command, B2 stops for a separately accepted generic protocol amendment.

### 8.2.1 Closed provider-neutral tool envelopes

Every operation uses `SocialToolContextV1`:

| Field | Rule |
|---|---|
| `operationId`, `intentId`, `idempotencyKey`, `canonicalRequestDigest` | Required immutable identities; no provider retry creates new values |
| `tenantAuthorityRef`, `relationshipRef`, `agentInstanceRef` | Server-derived opaque references; raw tenant/customer identity prohibited |
| `channel`, `channelAccountRef`, `credentialRefVersion` | Exact admitted channel/account and oauth-vault reference version |
| `decisionSpaceVersion`, `ceEvidenceRef`, `wbeEligibilityVersion` | Exact current authority/evidence references |
| `capabilityProfileVersion`, `requestedAt`, `deadlineAt`, `traceId` | Versioned provider facts and bounded execution/correlation |

`post_content` additionally requires the exact draft/version/digest, rendering payload, ordered
asset delivery references/digests, rights/disclosure references, calendar window, and approval
reference/version. It returns only:

- `ACCEPTED` or `PROCESSING` with opaque provider correlation and next status time;
- `PUBLISHED` with opaque publication reference, verified published time, and receipt digest;
- `FAILED` with closed reason/retry classification and zero success fields; or
- `OUTCOME_UNKNOWN` with original correlation and mandatory reconciliation.

`get_publish_status` requires the original context, correlation, and receipt digest when present. It
cannot accept a replacement content payload and returns `PROCESSING`, `PUBLISHED`, `FAILED`,
`NOT_FOUND_UNPROVEN`, or `OUTCOME_UNKNOWN`.

`delete_content` requires the original verified publication reference, exact correction/withdrawal
authority, reason code, expected publication version, and new idempotency identity. It returns
`DELETE_ACCEPTED`, `DELETED`, `DELETE_UNSUPPORTED`, `FAILED`, or `OUTCOME_UNKNOWN`.

Analytics operations require exact publication/account references, UTC observation window, requested
canonical metric set/version, and purpose. They return metric observations with provider metric
name, canonical mapping version, value/unit, observation window, collected-at, freshness, coverage,
and limitation codes. They cannot return credentials, audience-member identity, raw provider
payloads, inferred conversion, or publication authority.

All operations use a closed private error set:
`INVALID_REQUEST`, `NOT_ACCESSIBLE`, `AUTHORITY_DENIED`, `ASSURANCE_REQUIRED`, `VERSION_CONFLICT`,
`IDEMPOTENCY_CONFLICT`, `NOT_CONFIGURED`, `CREDENTIAL_EXPIRED`, `SCOPE_INSUFFICIENT`,
`ACCOUNT_UNSUPPORTED`, `CAPABILITY_STALE`, `RATE_LIMITED`, `PROVIDER_UNAVAILABLE`,
`OUTCOME_UNKNOWN`, and `STOPPED`. Transport timeout never authorizes retry; the original intent moves
to reconciliation. Provider details map to private reason codes and privacy-safe correlation only.

### 8.3 Publication state and idempotency

The immutable publication state is:

```text
REQUESTED -> VALIDATING
VALIDATING -> BLOCKED | ACCEPTED | CANCELLED
ACCEPTED -> DISPATCHING | CANCELLED | STOPPED
DISPATCHING -> RECONCILING | PUBLISHED | FAILED | STOPPED
RECONCILING -> PUBLISHED | FAILED | OUTCOME_UNKNOWN | STOPPED
PUBLISHED -> CORRECTION_REQUIRED | DELETE_PENDING
DELETE_PENDING -> DELETED | RECONCILING | FAILED | STOPPED
```

Each intent binds authenticated actor, server-derived tenant/relationship/instance, channel,
account, draft/version/digest, asset digests, calendar version, operation family, idempotency key,
canonical request hash, approval/evidence versions, credential reference version, and provider
capability version.

Same identity and hash replay the original receipt/outcome. Same identity with a different hash
conflicts before CE, oauth-vault, MCP, or provider calls. A timeout or disconnect enters
`RECONCILING`; blind retry is prohibited. `OUTCOME_UNKNOWN` remains customer-visible and blocks a
replacement publication unless an exact non-publication proof or separately approved correction
path exists.

### 8.4 Correction and rollback

- Text/media cannot be assumed editable after publication.
- A supported metadata correction requires its own exact capability probe and CE action.
- Otherwise correction means delete-and-republish: a new intent, new idempotency identity, explicit
  customer-visible consequence, and preserved lineage to the original publication.
- Provider deletion does not erase WAOOAW's immutable intent, receipt, evidence, cost, and correction
  history. Customer-removable content follows the accepted retention/erasure matrix.
- When deletion is unavailable or fails, state remains `CORRECTION_REQUIRED` or `FAILED` with a
  manual next action; the system never claims rollback.

## 9. Measurement And Improvement Contract

An `ObservationSnapshot` binds tenant, relationship, channel/account, publication IDs, provider
metric names, provider API/version, observation window, collected-at time, freshness, coverage,
limitations, and raw-to-canonical mapping version.

States are `AVAILABLE`, `PARTIAL`, `STALE`, `UNAVAILABLE`, and `DISPUTED`. Missing metrics remain
missing; they never become zero. Provider engagement observations are not customer conversion facts.
Attribution must name its method, window, included sources, excluded sources, confidence, and known
ambiguity.

The improvement loop is:

```text
observe -> validate freshness/coverage -> compare to accepted measure
        -> explain evidence and limitations -> propose bounded change
        -> customer review/materiality classification -> new plan/draft version
```

An improvement proposal is not self-authorizing. It reuses WC-115 proposal, plan, material-change,
and command semantics. No B2 metric can authorize Package C spend or lead action.

## 10. Security, Privacy, Cost, And Observability

- All provider calls use TLS and workload identity on internal hops; exact audience, caller, purpose,
  tenant, relationship, and operation are checked before secret retrieval.
- AIR receives minimized, PII-scrubbed inputs under C-078. Raw customer tokens, provider payloads,
  and unnecessary personal analytics do not enter prompts or reasoning traces.
- Rights, consent, and customer approvals are versioned evidence references. Withdrawal or token
  revocation fences new use and relocks affected work.
- Logs, traces, metrics, errors, screenshots, fixtures, and evidence exclude tokens, secret values,
  authorization headers, raw provider responses, private content, tenant existence, and personal
  audience data.
- Telemetry includes privacy-safe correlation, exact versions, queue/dispatch/reconciliation state,
  provider reason class, rate-limit disposition, credential health class, Stop state, cost/usage,
  observation freshness, and correction result.
- Costs are reserved before paid model/tool work where required, committed from actual usage, and
  reconciled on timeout. No provider fallback may silently change data policy, quality tier, or cost.
- Provider terms, app review, permissions, account type, Page Publishing Authorization, content
  limits, and media constraints are preflight inputs, not retryable implementation assumptions.

## 11. Provider Fact Register

These facts guide the candidate and must be revalidated against official sources at implementation
freeze and before hosted qualification:

| Source checked 2026-10-09 | Fact used by this contract |
|---|---|
| Meta Instagram Content Publishing documentation | Professional accounts only; advanced/standard access and named publishing permissions; provider-fetchable media; container/status/publish flow; rate-limit endpoint; provider media constraints; AI-generated disclosure field |
| Microsoft Azure multitenant Key Vault guidance updated 2026-10-02 | Separate vaults provide stronger tenant isolation; shared-vault naming is not access control; identity compromise blast radius and service limits must be considered |
| Microsoft Azure Container Apps secret guidance updated 2026-09-11 | Key Vault references require managed identity/RBAC; secret rotation/revision behavior is explicit; production values should not be embedded directly |
| OpenAI official API pricing | API use is metered; no permanent zero-cost assumption is encoded |
| xAI official model pricing | Grok API models and media generation are metered; no permanent zero-cost assumption is encoded |

Official documentation is volatile. Provider-specific numbers are capability-profile data with
retrieval time and API version, not hard-coded constitutional policy.

## 12. Failure And Degraded Behavior

| Condition | Required result |
|---|---|
| Model unavailable/unfunded | B1 uses an admitted local/degraded path or `BLOCKED`; no provider substitution without PSE authority |
| Missing mandatory customer input/rights | `NEEDS_INPUT`; no generation from invented facts |
| Placeholder/unresolved secret reference | `NOT_CONFIGURED`; B2 locked |
| Token expired/revoked/refresh failed | Affected account/skill paused; reconnect action; unrelated isolated work may continue |
| App permission/review/account unsupported | `BLOCKED_UNSUPPORTED`; no repeated provider calls |
| Provider rate limit | Honor provider retry metadata and calendar validity; do not cross the approved window silently |
| Timeout/disconnect after dispatch | `RECONCILING`; query original correlation, never blind repost |
| Provider says success but verification unavailable | `OUTCOME_UNKNOWN`; no success projection |
| Partial carousel/multi-asset preparation | No publish call; clean up where supported and preserve failure evidence |
| Analytics partial/stale | Report coverage/freshness/limitations; no zero fill or success claim |
| CE unavailable | No new consequential call; safe reads and Stop remain available |
| Key Vault/oauth-vault unavailable | No new credentialed dispatch; reconcile only when safe; never use stale token beyond accepted policy |
| Emergency Stop | Fence queued/new work, cancel where safe, reconcile in-flight, reject late authority |

## 13. Qualification And Activation Sequence

1. Freeze solution and WC-117 digests.
2. Implement and qualify B1 using local deterministic providers and no external publication.
3. Freeze a B1 candidate and record exact manifest/skill/interface/evidence tuple.
4. Founder separately decides B1 activation.
5. Implement B2 against emulated provider contracts and placeholder-reference fail-closed tests.
6. Qualify security, isolation, idempotency, reconciliation, Stop, measurement, and rollback locally.
7. Under separate provider/environment authority, qualify Meta app-role/test assets in Demo.
8. Freeze a B2 candidate with exact provider API/capability profile and hosted evidence.
9. Founder separately decides B2 activation and any customer connection or traffic.

No step implies the next.

## 14. Acceptance Oracles

1. B1 creates channel-correct drafts and an approval-ready calendar from only accepted customer
   inputs, rights, plan, and policy versions.
2. Draft correction and approval are immutable, exact-version, accessible, and have zero provider
   calls.
3. B2 cannot start without exact B1 qualification and a current approved draft.
4. Every external call passes CE before MCP dispatch and uses a purpose-bound oauth-vault token.
5. Duplicate, delayed, reordered, timeout, restart, and replay paths produce at most one logical
   publication and preserve exact reconciliation evidence.
6. Cross-tenant, relationship, instance, account, channel, environment, and purpose attacks fail
   before secret retrieval or provider calls and do not reveal existence.
7. Missing/placeholder secrets, absent funding, unsupported accounts, stale capabilities, revoked
   scopes, and expired tokens remain blocked.
8. Provider result, receipt, verification, correction, deletion, and unknown outcomes remain
   distinct and customer-truthful.
9. Analytics preserve provider names, windows, freshness, coverage, mapping, and attribution
   limitations; missing is never zero.
10. Demo proves only app-role/test-asset behavior and cannot consume Production credentials or claim
    general customer readiness.
11. B1 and B2 remain default-off and separately activatable/rollbackable.
12. No paid advertising, boosting, lead contact, crisis response, additional channel, customer
    traffic, or Production action occurs.

## 15. Stops

Stop the affected work when:

- an existing owner or WC-115 command cannot express the required behavior;
- a new public endpoint, deployable, database, storage product, provider, consent policy, retention
  period, or authority boundary is required but not accepted;
- no approved customer-asset owner can meet a required provider-fetchable media contract;
- Meta or another provider requires scopes outside this package, including advertising scopes;
- implementation would store a token outside oauth-vault, duplicate it in Key Vault, or expose it to
  DMA/AIR/BP/PR;
- a placeholder could pass readiness, a live secret is required for local qualification, or Demo
  would reuse UAT/Production/customer credentials;
- provider ambiguity cannot reconcile without duplicate side effects;
- a rights, likeness, claim, disclosure, approval, attribution, or customer-copy decision is missing;
- cross-customer isolation, Stop, evidence, WBE, CE, or retention cannot fail closed; or
- qualification, author review, and exact-head evidence cannot bind one immutable candidate.

The implementer records the blocker and does not infer, compensate, silently degrade, broaden scope,
or treat a dummy value as authority.

## 16. Implementation Readiness

**Result: READY FOR FOUNDER REVIEW, NOT IMPLEMENTATION.**

This candidate fixes package boundaries, owners, stable states, reuse decisions, tool operations,
credential compartments, placeholder semantics, idempotency, reconciliation, measurement,
degradation, acceptance, rollout, rollback, and stops. WC-117 atomizes the implementation.

Implementation still requires Founder acceptance of this exact candidate, a digest-valid WC-117
ledger, and explicit current-session implementation authorization. Hosted Meta qualification,
provider credentials, environment mutation, deployment, publication, customer traffic, and B1/B2
activation each remain separately prohibited until explicitly authorized.

## 17. Architecture Author Review

| Lens | Finding | Repair | Result |
|---|---|---|---|
| Generic command ownership | The first draft referred to a “publication command,” but WC-115 defines no DMA-specific publish command | Bound publication initiation to PR execution of the exact accepted Operations plan/calendar item and added a hard stop if the generic path cannot represent it | RESOLVED |
| Interface completeness | Tool names alone left provider-neutral request/result/error shapes open to implementer invention | Added closed shared context, operation-specific inputs/results, analytics fields, error vocabulary, and timeout/reconciliation semantics | RESOLVED |
| Secret mandate | A literal dummy secret in Key Vault could pass existence checks and conflict with ADR-014/021 | Limited placeholders to non-secret references, required `NOT_CONFIGURED`, and retained real customer tokens only in the Azure-hosted oauth-vault compartment | RESOLVED |
| Demo cost truth | “Free tier” availability is volatile and not guaranteed by official OpenAI/xAI pricing | Required funded/credited or admitted local/test providers and prohibited permanent-free-tier assumptions | RESOLVED |
| Package authority | One coordinated delivery could accidentally merge B1 and B2 activation | Kept separate candidate identities, qualification evidence, default-off gates, and Founder activation decisions | RESOLVED |

The complete candidate was reviewed against the parent DMA requirements, WC-114/115/116, ADR-014,
ADR-020, ADR-021, AIR/PSE, official Meta/Azure/OpenAI/xAI facts, the Solution Architect standard, and
the Founder request. Scope, ownership, interfaces, states, authority, security, privacy, cost,
failure, idempotency, reconciliation, observability, tests, rollout, rollback, exclusions, and stops
are closed for Founder review.

**Result: PASS for architecture authoring. Implementation remains unauthorized.**
