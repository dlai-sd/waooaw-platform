# WC-117 - DMA Packages B1/B2 Content Production, Social Publication, And Measurement

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Implementing office | Platform IT Expert (INST-010) |
| Status | FOUNDER ACCEPTED - CURRENT-SESSION IMPLEMENTATION AUTHORIZED 2026-10-09 - DEPLOYMENT, PROVIDER CONNECTION, PUBLICATION, AND ACTIVATION UNAUTHORIZED |
| Parent enterprise requirement | `architecture/reference/components/dma-onboarding-and-autonomous-operation-enterprise-requirements.md` |
| Controlling solution contract | `architecture/reference/components/dma-content-and-social-publication-solution-contract.md` `1.0.0-candidate.1` |
| Generic baseline | WC-114/WC-115 Conversational Employment Protocol |
| Package A dependency | WC-116 qualified/merged behavior and exact DMA manifest tuple |
| Delivery unit | One dependency-ordered implementation PR with independently frozen B1 and B2 evidence; separate activation decisions |
| Constitutional basis | C-001, C-003, C-005, C-007, C-023, C-026, C-035, C-041, C-048, C-049, C-051, C-055, C-059, C-063, C-065, C-066, C-070, C-071, C-078, C-079, C-080, C-094; ADR-002, ADR-003, ADR-009, ADR-014, ADR-020, ADR-021, ADR-024, ADR-029, ADR-031, ADR-035 |
| B1 activation authority | None |
| B2 activation authority | None |
| Deployment/provider authority | None |

## 1. Objective

Implement the accepted B1/B2 solution contract without inventing product rules, customer promises,
provider choices, credential storage, rights/consent semantics, owner boundaries, interfaces,
states, retries, evidence, costs, or activation.

- **B1** delivers customer-input-driven Instagram/Facebook drafts and an approval-ready calendar with
  no external publication.
- **B2** adds separately gated Meta publication, exact reconciliation, supported analytics, and an
  evidence-based improvement loop.

This Work Contract does not authorize runnable implementation by itself. Before changing `src/`,
tests, generated artifacts, migrations, executable configuration, or build output, the Platform IT
Expert must ask:

> This would begin writing implementation code. Do you authorize WC-117 implementation for the current session?

Only explicit current-session Founder confirmation opens implementation. Provider connection,
credential entry, cloud mutation, deployment, publication, customer traffic, and activation remain
unauthorized even after implementation authorization.

## 2. Authorized Outcome And Exclusions

After separate implementation authorization, WC-117 may:

- reconcile active DMA references to the accepted B1/B2 stable skills and package modes;
- implement B1 draft/calendar/rights/rendering/review/correction/cost/evidence behavior;
- implement B2 provider readiness, purpose-bound credential retrieval, publication intent,
  idempotent dispatch, reconciliation, correction/deletion where supported, analytics, and
  improvement proposals;
- extend existing MCP servers and Tool Registry only with the operations fixed by the solution
  contract;
- add owner-local persistence, generated clients, fixtures, deterministic provider emulators, and
  exact tests required by this contract;
- add environment/customer secret-reference templates containing no secret values;
- produce Docker-only local evidence and, only under later explicit authority, hosted Demo evidence;
  and
- prepare a disabled-by-default exact-head PR for Founder review.

Excluded:

- B1 or B2 activation, deployment, live provider login, cloud mutation, credential creation/entry,
  external publication, customer traffic, and Production;
- paid boosting, Meta Ads/Google Ads permissions, advertising spend, audiences, lead handling,
  autonomous crisis response, additional channels, or Packages C-E;
- a new public lifecycle, DMA-specific BP command, new deployable, database, storage product,
  provider selection, protocol major, or authority owner;
- hard-coded OpenAI/Grok/Meta endpoints, a permanent-free-tier assumption, data-sharing enrollment,
  or hidden spend;
- secret values, tokens, private keys, authorization headers, provider payloads, or customer content
  in source, fixtures, logs, evidence, PR text, or generated artifacts;
- unrelated repair/refactor, dependency upgrade, threshold reduction, self-approval, or merge.

## 3. Inputs And Preconditions

| Order | Input | Required state |
|---:|---|---|
| 0 | Fresh `origin/main`, process controls, Platform IT Expert card and selected Skills 2/3/4/5/6/7/12/13/15/17 as applicable | Current and digest-valid |
| 1 | Parent DMA enterprise requirements | Merged and unchanged |
| 2 | B1/B2 solution contract | Founder accepted at exact version/digest |
| 3 | WC-114/WC-115 generic employment contracts | Merged and current |
| 4 | WC-116 Package A manifest, stable Skills 0/1/2, compatibility tuple and evidence | Qualified and exact |
| 5 | ADR-014, ADR-020, ADR-021, AIR/PSE, oauth-vault, MCP Tool Registry, BP/PR/CE/WBE contracts | Current accepted owners |
| 6 | Approved customer-asset owner binding for any media story | Present before that story; otherwise the story is blocked |
| 7 | `work-contracts/WC-117-requirements.yaml` | Exact contract digest; ledger validation PASS |
| 8 | Current-session Founder implementation authorization | Explicit before runnable changes |

No live API key, URL, OAuth token, private key, customer login, or provider account is a local
implementation precondition. Local implementation uses deterministic emulators and non-secret
references. Hosted qualification has separate prerequisites and authority.

## 4. Permitted Surfaces

The implementer must resolve exact existing canonical paths during WC117-00 and record them in the
ledger before editing. Only dependency-complete surfaces directly owned by a requirement may change:

| Owner/purpose | Permitted surface class |
|---|---|
| DMA specification, prompts, dependency/image/admission references | Existing canonical DMA architecture records named by WC-116 |
| DMA B1/B2 semantics and contracts | `src/digital-marketing-agent/**` |
| Generic adapter registration only if required by unchanged contract | Existing profession-neutral agent-adapter registration surfaces |
| BP projection/commands | Existing WC-115 BP implementation and test surfaces |
| PR intent/reconciliation | Existing WC-115 PR implementation and test surfaces |
| AIR proposal/PSE integration | Existing AIR implementation and test surfaces; no direct provider selection |
| MCP/Tool Registry | Existing `instagram-mcp`, `facebook-mcp`, `platform-analytics-mcp`, scheduling/content-tool surfaces and tests |
| oauth-vault | Existing connect/health/retrieve/revoke purpose-bound surfaces and tests |
| Web | Existing generated-BP-client-backed employment workspace and tests |
| Secret/config references | Existing environment templates, Docker fixtures, Terraform/Container Apps surfaces only when separately authorized and selected by impact |
| Cross-owner evidence | Existing contract, integration, constitutional, acceptance, security, accessibility, and performance test surfaces |
| Contract evidence | `validation/evidence/wc117/**` and `work-contracts/WC-117-requirements.yaml` |

Founder amendment accepted 2026-10-09 fixes the previously unresolved paths:

- customer-asset owner: `src/business-platform/Services/CustomerAssets/`;
- Instagram MCP: `src/digital-marketing-agent/mcp/instagram/`;
- Facebook MCP: `src/digital-marketing-agent/mcp/facebook/`; and
- Platform Analytics MCP: `src/digital-marketing-agent/mcp/platform_analytics/`.

The MCP paths serve existing Compose deployable identities and are not new deployables. The asset
owner may use only existing BP persistence and tenant boundaries and introduces no database, storage
product, or public API.

If an exact owner/path does not exist, conflicts with another active source, or requires a new
deployable/storage product/public endpoint, stop. Do not create a plausible parallel path.

Every changed source file must carry repository-standard C-059 traceability to the accepted solution
contract section. Generated artifacts must bind generator/version/input digest/output surface.

## 5. Secret And External-Interface Mandate

1. Committed configuration contains only reference identifiers, never a usable secret.
2. Demo/UAT/Production platform secrets use their separate environment Key Vault.
3. Customer Meta OAuth grants use oauth-vault's tenant/relationship/account compartment; do not
   duplicate tokens in Key Vault, application databases, environment variables, or evidence.
4. Container Apps use managed identity and Key Vault references. Local Docker uses ignored local
   secrets only when a diagnostic needs them; authoritative tests use emulators.
5. `.invalid`, empty, fixture, `CHANGEME`, `PLACEHOLDER`, unresolved `secretref://`, and unresolved
   `oauthref://` values return `NOT_CONFIGURED` and cannot pass readiness.
6. Do not wait for Founder/customer credentials to implement contracts, state machines, clients,
   emulators, or tests.
7. Do not invent or write a dummy secret into Key Vault. A non-secret placeholder proves only that
   absent configuration fails closed.
8. OpenAI/Grok or any provider remains behind AIR/PSE. A credited/funded account is optional hosted
   input, not an implementation dependency or permanent free-tier promise.
9. Meta Demo uses only app-role/test assets under separately recorded provider authority. Demo
   evidence is not general customer or Production readiness.

## 6. Delivery Components

### WC117-00 - Bind Baseline, Digests, Paths, And Authority

**Dependencies:** none.

**Actions:**

1. Verify origin ancestry, process-control digests, controlling solution digest, ledger digest, and
   current-session implementation authority.
2. Resolve and record exact owner paths for BP, PR, AIR, CE client, WBE client, oauth-vault, three
   MCP owners, DMA adapter/specification, web projection, tests, and evidence.
3. Verify WC-116 exact tuple and B1/B2 stable skill availability remains default-off.
4. Inventory active duplicate B1/B2 behavior, numeric labels, direct provider clients, secret paths,
   provider-specific DTOs, and tests.
5. Bind Docker image/runner versions and focused impact selection.

**Exit:** no placeholder controlling digest, stale input, conflicting owner, unapproved path, or
missing authority.

### WC117-01 - Reconcile Canonical B1/B2 Skill Sources

**Dependency:** WC117-00.

**Actions:**

1. Retain `CONTENT_STRATEGY_AND_CALENDAR`, `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`,
   `VISUAL_AND_VIDEO_CONTENT`, and the social slice of
   `MARKETING_PERFORMANCE_AND_IMPROVEMENT` as stable versioned identities.
2. Mark B1/B2 mode, inputs, dependencies, side effects, approval mode, cost, evidence, degradation,
   and availability in the admitted manifest.
3. Convert numeric/channel-specific active descriptions to aliases/references; remove or archive
   duplicate normative behavior only after proving no live consumer.
4. Preserve Instagram/Facebook as channel capabilities, not separate customer employments.
5. Keep Package C-E skills `PLANNED`/`UNAVAILABLE`.

**Tests:** active-source uniqueness, stable-reference, no phantom skill, no premature availability,
and compatibility tuple tests.

**Exit:** one human-readable authority and one machine-readable runtime authority.

### WC117-02 - Implement B1 Input, Rights, And Asset Contracts

**Dependency:** WC117-01.

**Actions:**

1. Implement closed customer input and missing-input records for brand, claim, offer, audience,
   language, location, prohibited topics, channel, and accessibility.
2. Implement asset source/owner/version/digest, permitted use/channel, copyright/license, likeness,
   voice, disclosure, expiry, and withdrawal references.
3. Bind every record to server-derived tenant, relationship, instance, exact plan/manifest versions,
   evidence, correction lineage, and retention class.
4. Prohibit fabricated claims, rights, authors, citations, testimonials, locations, customer
   questions, and consent.
5. Stop media-dependent work when the accepted customer-asset owner binding is absent.

**Tests:** missing/partial/disputed/withdrawn/expired inputs, cross-tenant assets, rights mismatch,
unapproved likeness/voice, correction lineage, and data-minimization negatives.

**Exit:** every draft input is accepted, explicitly missing, or blocked; none is inferred as authority.

### WC117-03 - Implement B1 Draft Generation And Provenance

**Dependency:** WC117-02.

**Actions:**

1. Implement immutable `SocialContentDraftVersion` and exact state transitions.
2. Route generation only through AIR's provider-neutral proposal path and PSE.
3. Bind prompt/model policy, provider/model, scrubbed input digest, output digest, assumptions,
   confidence, evidence, cost/usage, and limitations.
4. Fail closed or use only an admitted disclosed degraded path when no provider is configured,
   funded, healthy, or policy-eligible.
5. Ensure no generation path calls a publishing MCP tool.

**Tests:** deterministic fixture proposals, hostile prompt/tool content, PII scrubber, unsupported
provider, budget exhaustion, idempotent proposal, provenance mismatch, and zero publication-call
assertions.

**Exit:** AIR remains proposal-only and B1 works against emulated/local providers.

### WC117-04 - Implement B1 Channel Rendering And Calendar

**Dependencies:** WC117-02 and WC117-03.

**Actions:**

1. Render exact Instagram/Facebook variants with text, asset references, alt text, tags,
   disclosures, call to action, capability profile, and limitations.
2. Validate channel constraints before `READY_FOR_REVIEW`; unsupported combinations remain blocked.
3. Bind calendar item, IANA zone, UTC instant, local representation, tolerance version, earliest/
   latest window, and materiality.
4. Treat provider limits as versioned retrieved capability data; do not hard-code mutable limits as
   permanent policy.
5. Preserve an accessible customer projection using ordinary customer vocabulary.

**Tests:** text/image/video/carousel fixtures where supported, constraint rejection, time-zone/fold,
stale capability, accessibility, and Instagram/Facebook rendering divergence.

**Exit:** drafts are channel-ready without becoming provider-ready or published.

### WC117-05 - Implement B1 Review, Correction, And Approval

**Dependency:** WC117-04.

**Actions:**

1. Reuse WC-115 plan/patch/review/accept/material-change/reschedule/reassessment commands.
2. Bind approval to one exact draft and plan/calendar digest/version.
3. Create successor versions for every correction; never mutate an approved version.
4. Relock affected drafts on material claim, asset-right, account, channel, policy, provider
   capability, or calendar change.
5. Keep Web and WhatsApp on the same owner operations, versions, idempotency, and secure handoff.

**Tests:** review/change/approve/supersede/withdraw, stale approval, cross-channel replay, material
relock, non-material tolerance, duplicate command, accessibility, and zero provider side effects.

**Exit:** B1 customer journey is complete with no publication authority.

### WC117-06 - Implement B1 Cost, Evidence, And Qualification

**Dependencies:** WC117-03 through WC117-05.

**Actions:**

1. Reserve and reconcile model/content-tool usage through existing WBE/cost owners.
2. Emit privacy-safe evidence for inputs, rights, generation, rendering, review, correction, and
   approval without content/secret payloads.
3. Run B1 success, missing-input, rights, provider, cost, outage, duplicate, Stop, cross-tenant,
   correction, rollback, accessibility, and channel-reuse journeys.
4. Freeze one B1 candidate and prove B2 remains locked/default-off.

**Exit:** every B1 requirement passes on one immutable candidate; no external provider publication
occurred.

### WC117-07 - Implement Credential And Provider Readiness

**Dependency:** WC117-06.

**Actions:**

1. Implement exact Meta account, scope, app-access, token-health, Page authorization, provider
   capability, rate-limit, and channel readiness projections.
2. Retrieve only token health/reference outside MCP; reusable token values remain inside oauth-vault
   to purpose-bound MCP retrieval.
3. Implement environment/customer compartment and managed-identity/Key-Vault-reference contracts.
4. Reject every placeholder/unresolved reference as `NOT_CONFIGURED`.
5. Build deterministic Meta/oauth-vault/Key Vault emulators and hostile isolation fixtures.

**Tests:** absent/placeholder/expired/revoked/wrong-scope/wrong-account/wrong-purpose/wrong-environment,
refresh failure, shared-identity abuse, enumeration, and secret-redaction tests.

**Exit:** provider readiness is truthful without any live credential.

### WC117-08 - Implement Versioned MCP Provider Operations

**Dependency:** WC117-07.

**Actions:**

1. Implement the eight exact Tool Registry operations in the solution contract.
2. Generate or validate owner-local clients from closed provider-neutral schemas.
3. Map Meta request/response/error/rate-limit details inside MCP owners only.
4. Require CE validation before each consequential tool call and the accepted policy for connected
   read operations.
5. Return correlation, receipt/status, retriable classification, provider capability version, and
   privacy-safe diagnostics without tokens/raw payloads.

**Tests:** schema/provider-consumer contracts, CE deny/escalate, oauth purpose/audience, malformed
provider response, rate limit, permission loss, token redaction, and no direct provider-client scans.

**Exit:** external interfaces are executable against emulators with no leaked provider DTO.

### WC117-09 - Implement Publication Intent And Reconciliation

**Dependencies:** WC117-08 and exact B1 qualification.

**Actions:**

1. Implement the exact publication state machine, immutable intent, outbox/inbox, and reconciliation.
2. Bind actor, tenant, relationship, instance, account, draft/asset/calendar/approval/evidence/
   credential/capability versions, idempotency key, and canonical hash.
3. Persist external intent before dispatch.
4. Verify provider outcome before `PUBLISHED`; treat timeout/disconnect/ambiguous response as
   `RECONCILING` or `OUTCOME_UNKNOWN`.
5. Fence queued/in-flight work on Stop and reject late results as new authority.

**Tests:** same-key replay/conflict, crash before/after dispatch, duplicate callback, delayed/reordered
status, restart, timeout, unknown outcome, Stop race, stale approval, and at-most-one logical post.

**Exit:** blind repost is impossible and customer state never outruns provider evidence.

### WC117-10 - Implement Correction, Deletion, And Rollback Limits

**Dependency:** WC117-09.

**Actions:**

1. Probe exact supported correction/deletion capability before offering it.
2. Implement separately authorized delete and delete/re-publish flows with immutable lineage.
3. Preserve provider receipts, cost, evidence, and correction history after provider deletion.
4. Return truthful manual action when provider rollback is unsupported or fails.
5. Prove rollback disables new candidate work without deleting owner facts.

**Tests:** supported/unsupported edit, delete success/failure/unknown, re-publish version separation,
partial correction, Stop, retention split, and rollback.

**Exit:** no UI or evidence claims a rollback the provider did not verify.

### WC117-11 - Implement Measurement And Improvement Loop

**Dependency:** WC117-09.

**Actions:**

1. Implement immutable observation snapshots with metric source/name, mapping version, window,
   collected-at, freshness, coverage, and limitations.
2. Preserve `AVAILABLE`, `PARTIAL`, `STALE`, `UNAVAILABLE`, and `DISPUTED`.
3. Keep engagement observations separate from customer conversion and DMA performance.
4. Implement explicit attribution method/window/source/ambiguity disclosure.
5. Route improvement only to a proposal, materiality check, customer review, and successor
   plan/draft; never self-authorize.

**Tests:** complete/partial/stale/missing/disputed metrics, missing-not-zero, mapping change,
cross-account contamination, attribution ambiguity, two missed review periods, and Package C
side-effect prohibition.

**Exit:** measurement is evidence-based and cannot authorize spend or publication.

### WC117-12 - Prove End-To-End B1/B2 Journeys

**Dependencies:** WC117-10 and WC117-11.

**Actions:**

1. Prove profile/plan -> draft -> review/correction -> exact approval -> publication intent ->
   provider reconciliation -> observation -> improvement proposal.
2. Prove Web/WhatsApp state reuse with secure handoff and no duplicated business logic.
3. Prove two customers share one admitted DMA artifact without data, secret, account, content,
   publication, analytics, Stop, or cost crossover.
4. Prove trial samples cannot publish and hire selection alone cannot publish.
5. Prove Demo/test configuration cannot reach UAT/Production or a non-test customer account.

**Exit:** all positive and negative acceptance oracles pass against deterministic providers.

### WC117-13 - Hosted Demo Qualification Preparation

**Dependency:** WC117-12.

**Actions authorized without provider authority:**

1. Produce a no-secret runbook and machine-readable required-input checklist for Demo app-role/test
   assets, environment secret references, scopes, callbacks, account IDs, and rollback.
2. Prove absent hosted inputs produce `NOT_CONFIGURED`.
3. Freeze the exact candidate, provider API version, capability profile, commands, and expected
   evidence envelope.

**Actions prohibited until separately authorized:** entering credentials, connecting Meta, mutating
Azure, deploying, publishing, retrieving live analytics, or incurring provider spend.

**Exit:** hosted execution is prepared but not performed.

### WC117-14 - Freeze, Qualify, Author Review, And Handoff

**Dependencies:** WC117-12; WC117-13 preparation. Hosted evidence is required only if separately
authorized and must be labelled distinctly.

**Actions:**

1. Freeze exact source, image, manifest, skill, adapter, protocol, MCP schema, provider capability,
   environment, and evidence identities.
2. Run dependency-complete repository Docker qualification.
3. Complete `WC-117-requirements.yaml` with direct immutable evidence.
4. Re-read the complete diff against parent requirements, solution contract, WC-115/116, provider
   facts, authority, security, privacy, cost, failure, rollback, and exclusions.
5. Repair every finding and rerun affected checks.
6. Push final commit, bind author review to the exact remote 40-character head, and prepare the exact
   PR body using repository controls.

**Exit:** author review PASS and Founder-ready PR open without self-approval, merge, deployment,
provider action, publication, customer traffic, or activation.

## 7. Canonical Requirement Index

| Requirement | Normative outcome |
|---|---|
| WC117-R001 | Implementation starts only from accepted exact inputs, digest-valid ledger, fresh baseline, and explicit current-session authority. |
| WC117-R002 | B1 and B2 remain dependency-ordered, independently qualified, default-off, and separately activatable. |
| WC117-R003 | Scope remains Instagram/Facebook organic content, publication, supported analytics, and improvement; Packages C-E remain excluded. |
| WC117-R004 | Stable skill IDs and one human/machine authority replace duplicate numeric/channel behavior. |
| WC117-R005 | BP, DMA adapter, AIR, PR, CE, WBE, oauth-vault, MCP, Key Vault, and asset-owner boundaries remain exact. |
| WC117-R006 | Every changed source/generated artifact has C-059 traceability and no parallel owner/path is invented. |
| WC117-R007 | Customer inputs, claims, offers, topics, rights, likeness, voice, disclosures, accessibility, and correction are explicit versioned records. |
| WC117-R008 | Missing/disputed/expired/withdrawn input or rights fails closed without fabricated facts. |
| WC117-R009 | Drafts are immutable successor versions with exact digests, provenance, cost, evidence, limitations, and legal transitions. |
| WC117-R010 | AIR/PSE is the only model path; direct OpenAI/Grok/provider selection and permanent-free-tier assumptions are absent. |
| WC117-R011 | External providers receive minimized C-078-scrubbed data and model output never becomes authority. |
| WC117-R012 | Instagram/Facebook renderings bind versioned constraints, tags, alt text, disclosures, assets, and capability profile. |
| WC117-R013 | Calendar binds instant, zone, local value, tolerance, window, plan, and materiality without granting publication. |
| WC117-R014 | Review, correction, approval, material change, reschedule, and reassessment reuse exact WC-115 commands. |
| WC117-R015 | Approval binds one exact version/digest and corrections never inherit approval. |
| WC117-R016 | B1 qualification proves zero provider publication calls and B2 remains locked. |
| WC117-R017 | Platform secrets are environment-isolated Key Vault references accessed by managed identity. |
| WC117-R018 | Customer Meta tokens remain only in oauth-vault's tenant/relationship/account compartment and never enter another owner or evidence. |
| WC117-R019 | Placeholder, fixture, `.invalid`, empty, unresolved secret/OAuth references cannot pass readiness or deployment gates. |
| WC117-R020 | Local implementation and qualification use deterministic emulators and do not wait for live credentials. |
| WC117-R021 | Demo uses only separately authorized app-role/test assets and cannot consume UAT/Production/customer secrets. |
| WC117-R022 | The exact eight MCP operations use closed schemas, owner-local clients, and no raw provider DTO outside MCP owners. |
| WC117-R023 | CE validation precedes every consequential external tool call and connected reads follow accepted purpose policy. |
| WC117-R024 | MCP token retrieval is exact-purpose, least-privilege, non-reusable, and privacy-safe. |
| WC117-R025 | Publication preconditions bind exact B1, draft, asset, calendar, approval, entitlement, Decision Space, credential, capability, CE, and Stop state. |
| WC117-R026 | Publication intent is durable before dispatch and binds complete idempotency/concurrency identity. |
| WC117-R027 | Same identity/hash replays; changed hash conflicts with zero owner/provider side effects. |
| WC117-R028 | Timeout, disconnect, crash, duplicate, reorder, and ambiguous outcomes reconcile the original intent without blind repost. |
| WC117-R029 | `PUBLISHED` requires verified exact provider evidence; accepted/receipt/unknown remain distinct. |
| WC117-R030 | Correction/deletion/republication are separately authorized, capability-probed, immutable, and limitation-aware. |
| WC117-R031 | Emergency Stop fences new dispatch, preserves reconciliation, and prevents late result authority. |
| WC117-R032 | Observation snapshots preserve source, metric, mapping, window, freshness, coverage, confidence, and limitations. |
| WC117-R033 | Missing metrics are not zero; engagement, conversion, DMA performance, and attribution remain distinct. |
| WC117-R034 | Improvement creates a proposal and successor plan/draft only; it cannot self-authorize publication or spend. |
| WC117-R035 | Tenant, relationship, instance, account, channel, environment, purpose, secret, content, analytics, Stop, and cost isolation pass hostile tests. |
| WC117-R036 | Logs, traces, metrics, errors, fixtures, evidence, and PR text contain no secrets, tokens, private payloads, or unnecessary personal data. |
| WC117-R037 | Costs are authorized/reserved/reconciled by existing owners and fallback cannot silently change cost or data policy. |
| WC117-R038 | Provider limits/permissions/account requirements are versioned capability facts revalidated at freeze, not permanent hard-coded policy. |
| WC117-R039 | Web and WhatsApp reuse one owner state/command path with idempotency, assurance, secure handoff, and accessible truth. |
| WC117-R040 | B1/B2 success, failure, stale, blocked, unknown, outage, retry, cross-boundary, Stop, correction, rollback, and accessibility journeys pass. |
| WC117-R041 | One immutable candidate passes dependency-complete Docker qualification with direct ledger evidence. |
| WC117-R042 | Hosted Demo evidence, if authorized, is separately labelled and never substitutes for Production/customer acceptance. |
| WC117-R043 | Author review repairs all findings and binds PASS to the exact remote head. |
| WC117-R044 | Founder handoff contains no self-approval, merge, provider connection, publication, deployment, customer traffic, or activation. |

## 8. Validation And Evidence

All authoritative implementation checks run through repository-owned Docker/catalog controls.
Before implementation, the exact current validation commands must be resolved from the current
catalogue; stale command names in this draft are not authority.

Minimum evidence families:

- contract/ledger digest, schema closure, changed-surface, C-059, and generated-client provenance;
- owner-local unit/property tests for BP, DMA, AIR, PR, oauth-vault, MCP, and web;
- provider/consumer MCP contract tests and deterministic Meta emulator;
- rights/input/rendering/calendar/review/correction B1 journeys;
- secret-placeholder, tenant/purpose/audience/environment, RLS, redaction, and anti-enumeration tests;
- publication idempotency, crash, retry, reconciliation, Stop, correction, rollback, and late-result tests;
- analytics freshness/coverage/attribution and improvement-loop tests;
- Web/WhatsApp reuse, accessibility, performance, SAST, dependency, secret, license, and observability gates;
- exact-candidate final qualification; and
- separately authorized hosted Demo evidence, if any, with exact environment/account/API identities.

No host-language command, prose, schema parsing alone, mock success alone, unbound screenshot, dummy
secret, or unversioned provider response can complete a requirement.

## 9. Definition Of Done

WC-117 implementation is complete only when:

- every WC117 requirement is directly evidenced in the digest-bound ledger;
- B1 and B2 each have a frozen identity and separate qualification result;
- all owner boundaries, states, interfaces, idempotency, reconciliation, security, privacy, cost,
  evidence, degradation, rollback, and Stop rules pass;
- no implementation waited for or embedded live Founder/customer credentials;
- placeholder references fail closed and no dummy secret was written to Key Vault;
- local deterministic qualification passes without external side effects;
- any hosted Demo run was separately authorized and used only app-role/test assets;
- no paid media, customer traffic, Production, activation, or excluded action occurred;
- author review is PASS on the exact remote head; and
- the prepared PR is open for Founder review without self-approval or merge.

## 10. Stops

Stop immediately when:

1. current-session implementation authorization is absent;
2. a controlling digest, ancestry, ledger, or exact Package A tuple fails;
3. implementation requires a new owner, public endpoint, deployable, database, storage product,
   provider, protocol major, consent/retention rule, or authority decision;
4. a media story lacks an accepted customer-asset owner binding;
5. a token would leave oauth-vault or a secret would enter source, logs, fixtures, evidence, or the
   DMA image;
6. a placeholder could appear ready or a live secret/provider call is proposed as local test input;
7. Meta requires advertising scopes or another Package C-E capability;
8. a duplicate/timeout/unknown path cannot prove at-most-one logical publication;
9. provider success cannot be independently reconciled;
10. rights, approval, assurance, WBE, CE, tenant, purpose, Stop, cost, or evidence cannot fail closed;
11. analytics would fabricate zero, conversion, attribution, or success;
12. a failed gate would be skipped, suppressed, threshold-reduced, or replaced with prose;
13. provider/cloud mutation, publication, deployment, customer traffic, or activation lacks separate
    exact authority; or
14. exact-head author review and PR preparation cannot bind the remote commit.

Record the blocker. Do not infer, compensate, broaden scope, create dummy authority, or continue
dependent work.

## 11. Rollback And Reversibility

- Before B1 freeze, revert only the failed B1 component to the last executable milestone.
- After B1 freeze, any identity-changing repair creates a new B1 candidate and reruns affected
  dependency closure.
- B2 rollback fences new publication, preserves original intents and reconciliation, disables
  candidate-only projection, and retains append-only approvals, receipts, corrections, cost, and CE
  evidence.
- Provider deletion is not WAOOAW rollback and cannot be claimed unless verified.
- Secret rotation/revocation pauses affected skills and never rewrites historical evidence.
- Successful rollback proof does not authorize rollback execution, deployment, or activation.

## 12. Author Review Requirement

Before handoff, the Platform IT Expert must re-read the complete implementation against the parent
requirements, controlling solution contract, WC-115/116, every WC117 requirement, official provider
facts, and current process controls. Review correctness, scope, authority, customer truth, rights,
security, privacy, isolation, secret handling, data, AI, cost, interfaces, state, failure,
idempotency, reconciliation, observability, tests, rollout, rollback, exclusions, and stops.

Every finding must be repaired and affected Docker checks rerun. PASS must bind the exact pushed
40-character head. Author review is self-verification, not independent approval or activation.

## 13. Current Authorization Boundary

The Founder request authorizes Chief Solution Architect research and authoring of this candidate
solution/Work Contract. It does not accept the candidate, authorize WC-117 implementation, permit
Platform IT Expert execution, authorize provider credentials or connections, permit Azure mutation,
deployment, publication, customer traffic, B1/B2 activation, PR approval, or merge.

## 14. Architecture Author Review

The Chief Solution Architect re-read this complete Work Contract with the parent requirements,
controlling solution contract, WC-114/115/116, Platform IT Expert operating card, accepted OAuth and
secret ADRs, and current official provider facts.

| Finding | Repair | Result |
|---|---|---|
| A publication “command” could imply a new DMA public API | The solution contract now fixes initiation as PR execution of an exact accepted Operations plan/calendar item and stops if the generic path is insufficient | RESOLVED |
| MCP operation names did not alone prevent wire-shape invention | The solution contract now fixes common context, operation-specific inputs/results, closed errors, and reconciliation semantics | RESOLVED |
| Founder-requested dummy values could be mistaken for usable authority | WC117-R019 requires reference placeholders to fail closed and prohibits dummy Key Vault secrets; emulators remove the need to wait for live keys | RESOLVED |
| One implementation package could collapse B1/B2 activation | WC117-R002, R016, R021, R041, and R042 preserve separate candidate, qualification, hosted-evidence, and activation boundaries | RESOLVED |

Requirements coverage, owner boundaries, dependency order, external interfaces, secret/customer
compartments, provider volatility, evidence, failures, tests, rollout, rollback, exclusions, and
stops are complete for Founder review.

**Result: PASS for Work Contract authoring. Platform IT Expert implementation remains unauthorized.**
