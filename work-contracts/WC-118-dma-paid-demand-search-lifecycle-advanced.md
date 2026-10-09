# WC-118 - DMA Packages C/D/E Paid Demand, Search, Lifecycle, And Advanced Capabilities

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Implementing office | Platform IT Expert (INST-010) |
| Status | CANDIDATE FOR FOUNDER REVIEW - IMPLEMENTATION, DEPLOYMENT, PROVIDER CONNECTION, EXTERNAL ACTION, CUSTOMER TRAFFIC, AND ACTIVATION UNAUTHORIZED |
| Parent enterprise requirement | `architecture/reference/components/dma-onboarding-and-autonomous-operation-enterprise-requirements.md` |
| Controlling solution contract | `architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md` `1.0.0-candidate.1` |
| Generic baseline | WC-114/WC-115 Conversational Employment Protocol |
| Package dependencies | WC-116 Package A and WC-117 Packages B1/B2 qualified/merged behavior |
| Delivery unit | One dependency-ordered implementation package with independent C, D, and E candidate freezes, qualification evidence, rollback controls, and activation decisions |
| Constitutional basis | C-001, C-003, C-005, C-007, C-023, C-026, C-035, C-037, C-041, C-043, C-048, C-049, C-050, C-051, C-053-C-057, C-059, C-062-C-063, C-065-C-066, C-070-C-071, C-078-C-080, C-088-C-091, C-094; ADR-002, ADR-003, ADR-009, ADR-010, ADR-014, ADR-020-ADR-024, ADR-026, ADR-029, ADR-031, ADR-034-ADR-035 |
| Package C activation authority | None |
| Package D activation authority | None |
| Package E activation authority | None |
| Deployment/provider/external-action authority | None |

## 1. Objective

Implement the accepted C/D/E solution contract as three independently qualified, default-off DMA
packages without making product, owner, provider, consent, secrets, authority, schema, state,
commercial, privacy, retention, or activation decisions.

- **Package C** implements paid-media planning/execution controls, first-party-audience gating, lead
  capture/progression, booking/handoff, spend and conversion evidence.
- **Package D** implements search/discoverability, approved external changes, lifecycle/email,
  suppression, multi-location, reputation, and periodic strategy.
- **Package E** implements institutionally isolated WAOOAW marketing, advanced creative experiments,
  privacy-preserving multi-client intelligence, and approval-gated crisis communications.

This contract does not authorize runnable implementation by itself. Before changing `src/`, tests,
generated artifacts, migrations, executable configuration, infrastructure, workflows, or build
output, the Platform IT Expert must ask:

> This would begin writing implementation code. Do you authorize WC-118 implementation for the current session?

Only an explicit current-session Founder confirmation opens implementation. It does not authorize
deployment, provider connection, credential entry, external action, spend, audience upload, lead
contact, profile/site change, lifecycle communication, institutional marketing, customer traffic,
or activation.

## 2. Authorized Outcome And Exclusions

After separate implementation authorization, WC-118 may:

- reconcile active DMA sources to the stable C/D/E skills fixed by the solution contract;
- implement DMA-specific contracts and behavior under `src/digital-marketing-agent/**`;
- add only thin profession-neutral registration to existing WC-115 owners;
- extend accepted MCP/credential/analytics owners with the exact provider-neutral operations in the
  solution contract, without selecting an unresolved provider;
- add owner-local persistence, generated clients, fixtures, deterministic emulators, and exact tests;
- add environment/customer secret-reference templates containing no secret values;
- freeze and qualify separate C, D, and E candidates with a digest-bound ledger; and
- prepare an exact-head PR for Founder review.

Excluded:

- any package activation, deployment, cloud/provider mutation, live login, credential creation or
  entry, spend, audience upload, lead/customer contact, website/profile change, email/lifecycle send,
  institutional campaign, customer traffic, UAT, Production, approval, or merge;
- `CUSTOMER_OWNED` paid accounts, provider adoption where no accepted decision exists, hidden
  fallback, permanent-free-tier assumption, or unapproved data-sharing program;
- a new public command, public endpoint, deployable, database, authority owner, credential service,
  CRM, booking system, email provider, SEO provider, CMS, platform-intelligence product, or protocol;
- raw secrets, tokens, private keys, logins, authorization headers, customer content, lead/audience
  identifiers, or provider payloads in source, fixtures, logs, evidence, or PR text;
- autonomous consequential commitments, crisis response, rank/revenue/lead guarantees, purchased or
  scraped contact lists, fabricated reviews/locations/claims, or customer-to-institutional reuse;
- unrelated repair/refactor, dependency upgrade, threshold reduction, self-approval, or merge.

## 3. Inputs And Preconditions

| Order | Input | Required state |
|---:|---|---|
| 0 | Fresh `origin/main`, process controls, Platform IT Expert card and selected applicable skill sections | Current and digest-valid |
| 1 | Parent DMA enterprise requirements | Merged and unchanged |
| 2 | C/D/E solution contract | Founder accepted at exact version/digest |
| 3 | WC-114/WC-115 generic employment contracts | Merged and current |
| 4 | WC-116 Package A manifest/adapter/compatibility tuple | Qualified, merged, exact |
| 5 | WC-117 Package B draft/publication/measurement/asset contracts | Qualified, merged, exact |
| 6 | ADR-026 paid-account model and current WBE/CE/BP/PR/AIR/PSE/oauth-vault/MCP/Key Vault contracts | Accepted and current |
| 7 | Exact owner/path for lead/CRM/booking, CMS/GBP/search, email/lifecycle, and platform-intelligence stories | Present and accepted before dependent story; absent owner blocks only that story |
| 8 | Exact provider/adoption decision where current architecture leaves provider open | Accepted before provider-specific implementation; emulator-only provider-neutral work may proceed |
| 9 | `work-contracts/WC-118-requirements.yaml` | Exact contract digest and solution digest; ledger validation PASS |
| 10 | Current-session Founder implementation authorization | Explicit before any runnable change |

No live API key, URL, token, login, private key, certificate, customer account, or provider
connection is a local implementation precondition.

## 4. Permitted Surfaces

| Owner/purpose | Permitted surface class |
|---|---|
| DMA specification, prompt/dependency/image/admission references | Existing canonical DMA architecture records, only for source reconciliation required by WC118 |
| DMA C/D/E semantics, state, provider-neutral MCP contracts, emulators, fixtures | `src/digital-marketing-agent/**` |
| Profession-neutral adapter registration | Existing generic WC-115 registration surfaces only |
| BP projections/commands | Existing WC-115 BP surfaces, with no DMA business interpretation |
| PR intents/reconciliation | Existing WC-115 PR surfaces |
| CE/WBE/AIR integrations | Existing accepted owner surfaces, with no authority transfer |
| oauth-vault/customer credential integration | Existing accepted owner surfaces; references and health only outside the owner |
| Web/WhatsApp | Existing generated-BP-client-backed employment workspace/channel surfaces |
| Infrastructure/templates | Existing environment templates only when separately authorized and selected by impact; no secret values |
| Cross-owner tests | Existing contract, integration, constitutional, acceptance, security, accessibility, privacy, performance, and isolation surfaces |
| Evidence | `validation/evidence/wc118/**` and `work-contracts/WC-118-requirements.yaml` |

The exact DMA-owned implementation paths are:

```text
src/digital-marketing-agent/contracts/cde/**
src/digital-marketing-agent/digital_marketing/paid_demand.py
src/digital-marketing-agent/digital_marketing/lead_management.py
src/digital-marketing-agent/digital_marketing/discoverability.py
src/digital-marketing-agent/digital_marketing/lifecycle.py
src/digital-marketing-agent/digital_marketing/operating_scale.py
src/digital-marketing-agent/digital_marketing/advanced_capabilities.py
src/digital-marketing-agent/mcp/meta_ads/**
src/digital-marketing-agent/mcp/google_ads/**
src/digital-marketing-agent/mcp/lead_operations/**
src/digital-marketing-agent/mcp/discoverability/**
src/digital-marketing-agent/mcp/lifecycle/**
src/digital-marketing-agent/tests/cde/**
```

These paths are inside the existing DMA deployable. They do not authorize a new service. A
provider-specific module under a provider-neutral surface is prohibited until the provider and exact
owner are accepted.

If an exact path/owner does not exist, conflicts with an active source, or requires a new service,
database, public API, provider, or authority, stop. Do not create a plausible parallel owner.

Every changed source file must carry the repository-standard C-059 header pointing to the exact
controlling solution-contract section. Generated artifacts bind generator, version, input digest,
output path, and reproducible command.

## 5. Secret And External-Interface Mandate

1. Demo/UAT/Production use separate Key Vaults, managed identities, oauth-vault/customer-credential
   boundaries, databases, provider accounts/applications, and evidence identities.
2. Environment platform secrets use Azure Key Vault references and least-privilege managed identity.
3. Customer OAuth grants remain in oauth-vault under server-derived environment, tenant,
   relationship, provider, account, purpose, scopes, version, and expiry.
4. Customer non-OAuth keys/logins/certificates/private keys use only an accepted Azure-hosted
   customer credential compartment. Missing owner support returns `NOT_CONFIGURED`.
5. Committed values such as `secretref://`, `oauthref://`, `credentialref://`, and `.invalid` URLs
   are schema examples. Empty, fixture, placeholder, unresolved, and cross-environment values fail
   readiness and hosted gates.
6. No dummy secret value is written to Key Vault to satisfy an existence check.
7. Local implementation uses deterministic emulators. Demo may use official test/development assets
   or an explicitly funded/credited PSE-approved provider account under separate authority.
8. A free tier is never assumed permanent and absence of a live credential is never replaced with
   hidden spend, unapproved provider fallback, or data-sharing enrollment.

## 6. Delivery Components

### WC118-00 - Bind Baseline, Digests, Authority, And Owner Paths

**Actions:**

1. Verify exact `origin/main`, process-control digests, WC-116/117 qualified tuples, solution digest,
   ledger digest, and current-session authority.
2. Resolve exact existing owner/path for every dependent story.
3. Record unresolved provider/adoption decisions as hard stops, not implementation choices.
4. Run changed-surface, C-059, ledger, secret, and prohibited-provider preflight in Docker.

**Exit:** no stale input, placeholder identity, unknown owner, or unrecorded authority.

### WC118-01 - Reconcile Canonical C/D/E Skill Sources

**Dependency:** WC118-00.

**Actions:**

1. Reconcile paid media, lead, search, lifecycle, multi-location, reputation, institutional,
   advanced optimization, multi-client intelligence, and crisis definitions to stable IDs.
2. Resolve the Skill 14 institutional/reputation collision.
3. Replace duplicate behavior in prompt/dependency/billing/image/fixture/admission records with stable
   references.
4. Preserve legacy numbers only as migration aliases.
5. Update the exact admitted manifest states without advertising implementation as availability.

**Tests:** active-source uniqueness, collision, obsolete label, duplicate behavior, manifest state,
and stable-reference scans.

**Exit:** one human-readable and one machine-readable authority with no collision.

### WC118-02 - Implement Shared Identity, Secret, State, And Emulator Foundations

**Dependency:** WC118-01.

**Actions:**

1. Implement closed package/skill/provider/account/location/audience/lead/sequence/experiment
   identities and exact version references.
2. Implement non-secret reference parsing and fail-closed placeholder semantics.
3. Implement deterministic Key Vault, oauth-vault, customer-credential, provider, webhook, CRM,
   booking, CMS, email, analytics, and platform-intelligence emulators.
4. Implement privacy-safe closed diagnostics and telemetry envelopes.
5. Prove environment, tenant, relationship, instance, account, location, purpose, and identity
   isolation before secret retrieval or owner calls.

**Exit:** all later stories run without live credentials and cannot cross a boundary.

### WC118-03 - Implement Package C Campaign Planning And Approval

**Dependencies:** WC118-02 and WC-117 exact creative/asset contracts.

Implement immutable `PaidCampaignVersion`, material-change classification, exact objective,
geography, schedule, budget/pacing/stop, creative/rights, landing, conversion, audience, provider
capability, account model, approval, and limitation fields. Reuse WC-115 plan/command semantics.

**Tests:** complete/missing/disputed inputs, stale plan/creative/rights, illegal transition,
approval inheritance, material change, trial, and zero provider-call tests.

### WC118-04 - Implement Package C Wallet, Reservation, And Spend Controls

**Dependency:** WC118-03.

Integrate WBE-owned entitlement, wallet, reservation, actual charge, management fee, credit/refund,
low/exhausted balance, discrepancy, and reconciliation without recomputation in DMA.

**Tests:** reserve/commit/release, low/zero balance, credit pass-through, disputed/stale/unknown,
concurrent spend, rounding, provider/WBE discrepancy, and pause-intent tests.

### WC118-05 - Implement Package C Paid-Media MCP Operations

**Dependencies:** WC118-03 and WC118-04.

Implement the eight closed `paid_media.*` operations behind accepted MCP owners, owner-local
provider mappings, exact scope/capability/account checks, CE validation, idempotency, durable intent,
status reconciliation, rate-limit handling, and privacy-safe receipts.

**Tests:** provider/consumer schemas, Meta/Google emulators, CE deny/escalate, WBE denial, scope,
account, capability, duplicate, crash, timeout, reorder, restart, Stop, and redaction.

### WC118-06 - Implement Package C Campaign Execution And Reconciliation

**Dependency:** WC118-05.

Implement the exact campaign state machine, outbox/inbox, provider correlation, verified activation,
change, pause, spend observation, unknown outcome, correction, and rollback fencing. No provider
response alone may set customer success.

**Exit:** at most one logical provider mutation per accepted intent.

### WC118-07 - Implement First-Party Audience Activation Sub-Gate

**Dependency:** WC118-06.

Implement the separate audience state machine, collection-right/lawful-purpose attestation,
provider/account eligibility, approved identifiers, minimization/normalization/hash, suppression,
withdrawal, retention/deletion, transfer, match limitation, and exact provider-policy profile.

**Tests:** absent/invalid consent, wrong purpose/provider/account, suppressed/withdrawn identifiers,
duplicate upload, partial match, minimum audience, delete/unknown, raw-identifier leak, and contextual
campaign isolation.

**Exit:** audience activation may remain blocked while ordinary lawful campaigns remain independent.

### WC118-08 - Implement Package C Lead Capture And Deduplication

**Dependencies:** WC118-02 and WC118-06.

Implement signed/purpose-bound provider webhook intake, inbox deduplication, immutable
`LeadCaseVersion`, spam/invalid/existing-customer/duplicate/suppression states, source/campaign
references, and anti-enumeration.

**Tests:** replay, reorder, forged webhook, cross-tenant/account/campaign, duplicate identity,
partial data, suppressed contact, apparent minor, and privacy-safe error tests.

### WC118-09 - Implement Package C Qualification, Routing, Nurture, And Handoff

**Dependency:** WC118-08.

Implement customer-owned qualification, service-area, availability, routing, response, escalation,
template, channel permission, human takeover, nurture, booking/handoff, and no-consequential-promise
rules. Persist intent before contact or booking action and reconcile ambiguity.

**Tests:** qualified/unqualified/needs-input, outside area/hours, complaint/sensitive/high-value,
template boundary, opt-out, three-exchange/handoff limit where applicable, booking timeout, duplicate
contact, no-response, and human-takeover tests.

### WC118-10 - Implement Package C Conversion And Attribution Evidence

**Dependencies:** WC118-06 and WC118-09.

Implement conversion observations/uploads only through accepted owners, with exact source, method,
window, mapping, consent, confidence, coverage, deduplication, correction, and limitations.
Engagement, lead, booking, won/lost, revenue, and DMA performance remain distinct.

### WC118-11 - Freeze And Qualify Package C

**Dependencies:** WC118-03 through WC118-10.

Run complete local Docker qualification with emulators and zero live spend/contact/upload. If
separately authorized, run hosted test-account qualification and label it distinctly. Freeze exact
source/image/manifest/skill/MCP/provider-capability/environment/evidence identities and prove D/E
remain locked.

### WC118-12 - Implement Package D Search Assessment

**Dependencies:** WC118-02 and qualified Package C only where paid/conversion evidence is consumed.

Implement immutable provider-independent discoverability assessment across verified business facts,
GBP, site/property, crawl/index/meaning/structured information, Search Console, content,
performance, conversion routes, GEO/AEO clarity, evidence/freshness/confidence/limitations, and
customer correction.

**Tests:** public/read-only observation, robots/terms, unverified property/location, stale/partial
evidence, missing-not-zero, fabricated location/expertise/citation, ranking guarantee, and
provider-unavailable tests.

### WC118-13 - Implement Package D Approved Search/Profile/CMS Changes

**Dependency:** WC118-12.

Implement immutable change packages, exact before/after version, approval, owner, credential,
capability, CE, intent, receipt, verification, rollback/manual-action, and unknown outcome.
Without an accepted write owner, produce an approved delivery package only.

### WC118-14 - Implement Package D Lifecycle And Email Foundations

**Dependency:** WC118-02.

Implement immutable `LifecycleSequenceVersion`, consent/lawful-purpose source, sender/domain
readiness, audience/segment, template, cadence/quiet hours, trigger, expiry, approval, and
suppression precedence. Keep provider adoption behind an accepted decision.

**Tests:** purchased/scraped list, missing consent, sender/domain unverified, excessive cadence,
stale template, prohibited claim, cross-purpose segment, and zero-send tests.

### WC118-15 - Implement Package D Lifecycle Dispatch And Suppression

**Dependency:** WC118-14.

Implement provider-neutral contact import, sequence/campaign creation, send, receipt, bounce,
complaint, unsubscribe, opt-out, withdrawal, suppression, reconciliation, and evidence operations.
Authoritative suppression commits before future dispatch.

**Tests:** duplicate/reorder, unsubscribe race, hard bounce, complaint, withdrawal, partial send,
timeout, retry, provider outage, Stop, and redaction. A broken unsubscribe path fences affected sends.

### WC118-16 - Implement Package D Multi-Location Operations

**Dependencies:** WC118-12 through WC118-15 as selected.

Implement versioned location hierarchy, brand inheritance, local overrides, enumerated location-set
approval, account/budget/lead/content/review routing, local Stop scope, and coverage-aware aggregate
reporting.

**Tests:** one/all/subset locations, stale hierarchy, closed location, wrong account/budget/lead,
partial outage, location override, approval-set drift, and cross-location Stop isolation.

### WC118-17 - Implement Package D Reputation And Strategy Review

**Dependencies:** WC118-12 and WC118-16.

Implement read-only review/mention observations, response proposal/review/approval/publication
reconciliation, sensitive/crisis escalation, and evidence-based periodic strategy proposals.
Never fabricate a review, customer, response, citation, or success.

### WC118-18 - Freeze And Qualify Package D

**Dependencies:** WC118-12 through WC118-17.

Run complete local qualification with provider emulators and zero live change/contact. Under separate
authority, run exact hosted account qualification. Freeze Package D and prove C remains unchanged and
E remains locked.

### WC118-19 - Implement Package E Institutional Isolation

**Dependency:** WC118-02.

Implement the exact institutional organisation, relationship, Decision Space, WBE bucket, provider
account, credential references, plans, approvals, claims, evidence, Stop scope, and reporting.
Prohibit any customer reference from satisfying an institutional prerequisite.

### WC118-20 - Implement Package E Advanced Experiments And Intelligence

**Dependencies:** WC118-11, WC118-18, and accepted platform-intelligence owner/profile.

Implement immutable experiment envelopes and privacy-preserving aggregate intelligence with exact
hypothesis, variants, budget, guardrails, duration, stop-loss, statistical method, cohort threshold,
small-cell/membership-inference controls, lineage, confidence, limitations, and withdrawal.

**Tests:** budget/audience/geography widening, unapproved claim/asset, guardrail failure, early
stopping, small cohort, re-identification, customer ranking, biased/stale cohort, and absent-owner
hard stop.

### WC118-21 - Implement Package E Crisis Communications

**Dependency:** WC118-19.

Implement detection, urgent signal, source preservation, severity, named escalation, approval-gated
response, and no-autonomous-publication rules for review-bomb, extortion, legal/regulatory, safety,
media, data-breach, and public-harm cases.

### WC118-22 - Freeze And Qualify Package E

**Dependencies:** WC118-19 through WC118-21.

Run local institutional and privacy-safe aggregate fixtures without live institutional action or
customer data. Hosted qualification requires separate authority and exact institutional accounts.
Freeze E independently.

### WC118-23 - Prove Cross-Package Journeys And Rollback

**Dependencies:** WC118-11, WC118-18, and WC118-22.

Execute success, blocked, partial, stale, disputed, duplicate, replay, outage, ambiguous outcome,
cross-tenant/relationship/instance/account/location/environment, consent withdrawal, suppression,
wallet exhaustion, provider failure, Stop, correction, rollback, accessibility, and Web/WhatsApp
reuse journeys. Prove rollback of one package does not delete facts or activate another.

### WC118-24 - Prepare Hosted Qualification Inputs

**Dependency:** WC118-23.

Produce non-secret required-input manifests for Demo provider accounts, scopes, app/project review,
test assets, callback/webhook, managed identities, Key Vault references, customer compartments,
funding ceilings, cleanup, expected evidence, and separate authority.

**Prohibited:** entering credentials, Azure mutation, deployment, provider action, spend, contact,
traffic, or activation.

### WC118-25 - Final Qualification, Author Review, And Founder Handoff

**Dependencies:** WC118-23 and WC118-24.

1. Freeze all exact candidate identities.
2. Run dependency-complete Docker/catalog qualification.
3. Complete the WC-118 ledger with immutable evidence.
4. Re-read the complete diff against all controlling inputs and quality lenses.
5. Repair every finding and rerun affected checks.
6. Push the final commit, bind author review to the remote 40-character head, run repository PR
   preparation, and open the exact prepared PR.

**Exit:** Founder-ready PR, no self-approval, merge, deployment, provider action, spend, contact,
traffic, or activation.

## 7. Canonical Requirement Index

| Requirement | Normative outcome |
|---|---|
| WC118-R001 | Implementation begins only from fresh exact inputs, valid contract/solution digests, resolved owners, valid ledger, and explicit current-session authority. |
| WC118-R002 | C, D, and E remain dependency-ordered, independently frozen, qualified, rollbackable, default-off, and separately activatable. |
| WC118-R003 | Scope contains only the accepted C/D/E outcomes and excludes deployment, provider action, spend, contact, traffic, and activation. |
| WC118-R004 | Stable semantic skill IDs replace numeric identity and resolve the Skill 14 institutional/reputation collision. |
| WC118-R005 | DMA-specific implementation remains under `src/digital-marketing-agent/**`; other owners contain thin profession-neutral integration only. |
| WC118-R006 | Every source/generated change has exact C-059 specification and generator traceability. |
| WC118-R007 | BP, DMA, PR, CE, WBE, AIR/PSE, credential, MCP, analytics, and platform-intelligence ownership remains exact. |
| WC118-R008 | ADR-026 WAOOAW-managed paid accounts remain the only accepted paid-account model. |
| WC118-R009 | Environment platform secrets use separate Azure Key Vault references and least-privilege managed identities. |
| WC118-R010 | Customer OAuth and non-OAuth credentials remain in accepted server-derived customer compartments and never enter other owners. |
| WC118-R011 | Placeholder, fixture, empty, unresolved, `.invalid`, and cross-environment references fail readiness without blocking emulator-based implementation. |
| WC118-R012 | No permanent free tier, hidden spend, unapproved fallback, dummy Key Vault value, or data-sharing enrollment is assumed. |
| WC118-R013 | Deterministic emulators cover every external owner/protocol required for local qualification. |
| WC118-R014 | Paid campaigns use immutable versions and exact plan, creative, rights, objective, account, budget, approval, capability, and authority references. |
| WC118-R015 | Material campaign changes create successor versions and never inherit approval or authority. |
| WC118-R016 | WBE alone owns entitlement, wallet, reservation, charge, fee, credit/refund, and commercial consequence. |
| WC118-R017 | Provider and WBE spend remain distinct and discrepancies block new spend pending reconciliation. |
| WC118-R018 | Paid-media MCP operations use closed provider-neutral schemas and keep Meta/Google DTOs inside owners. |
| WC118-R019 | Every paid mutation persists one exact intent before dispatch and reconciles without blind duplicate action. |
| WC118-R020 | Campaign state cannot become active/successful from HTTP acceptance, receipt, webhook, or model output alone. |
| WC118-R021 | First-party audience activation is a separate gate with lawful-purpose, eligibility, minimization, suppression, retention, deletion, and provider-policy evidence. |
| WC118-R022 | Raw audience identifiers never enter AIR, logs, evidence, DMA durable state, or unauthorized owner surfaces. |
| WC118-R023 | Blocking first-party audience activation does not block otherwise lawful isolated campaign strategies. |
| WC118-R024 | Lead intake verifies webhook/source purpose and deduplicates replay/reorder into one logical case. |
| WC118-R025 | Lead state preserves spam, invalid, duplicate, existing-customer, suppressed, qualified, routed, booked, won/lost, no-response, and unknown distinctions. |
| WC118-R026 | Customer-owned qualification, service area, availability, routing, response, escalation, and channel rules control lead progression. |
| WC118-R027 | Sensitive, disputed, high-value, complaint, apparent-minor, unsupported, and outside-authority cases require human takeover. |
| WC118-R028 | DMA never makes autonomous price, legal, clinical, inventory, eligibility, credit, or service commitments. |
| WC118-R029 | Lead contact, booking, and handoff persist intent, enforce consent/suppression, and reconcile ambiguous outcomes. |
| WC118-R030 | Conversion evidence preserves source, method, window, mapping, confidence, coverage, correction, and attribution limitations. |
| WC118-R031 | Engagement, lead, booking, conversion, revenue, customer outcome, and DMA performance remain distinct. |
| WC118-R032 | Search assessment binds verified business/site/location facts, source, freshness, evidence, confidence, limitations, and correction. |
| WC118-R033 | Search/GEO/AEO behavior cannot fabricate locations, expertise, citations, questions, reviews, ranking, inclusion, traffic, or revenue claims. |
| WC118-R034 | Search/profile/CMS changes use immutable approved change packages, exact before/after versions, receipts, verification, and truthful rollback/manual action. |
| WC118-R035 | An absent accepted write owner yields an approved delivery package, never an invented provider or false applied state. |
| WC118-R036 | Lifecycle sequences bind purpose, consent/lawful basis, sender, segment, template, cadence, trigger, expiry, approval, and suppression policy. |
| WC118-R037 | Purchased, scraped, unsubstantiated, cross-purpose, or withdrawn contact data cannot be imported or contacted. |
| WC118-R038 | Unsubscribe, opt-out, withdrawal, hard bounce, complaint, and suppression commit before later dispatch and override optimization. |
| WC118-R039 | A failed unsubscribe path fences affected sends and cannot degrade to continued contact. |
| WC118-R040 | Email/lifecycle provider adoption and sender-domain readiness remain accepted external decisions, not implementer choices. |
| WC118-R041 | Multi-location actions bind an exact location or enumerated location set and isolate account, budget, lead, content, approval, and Stop scope. |
| WC118-R042 | Aggregate location reporting exposes coverage/missing locations and never converts missing data to zero. |
| WC118-R043 | Reputation observations remain read-only until an exact response is reviewed, approved, dispatched, and verified. |
| WC118-R044 | Complaint, legal/regulatory, safety, discrimination, clinical, financial, apparent-minor, extortion, media, and crisis content escalates without autonomous response. |
| WC118-R045 | Periodic strategy review creates evidence-based proposals and successor plans without self-authorizing changes. |
| WC118-R046 | Institutional marketing uses only WAOOAW institutional relationship, Decision Space, budget, credentials, claims, evidence, and Stop scope. |
| WC118-R047 | No customer authority, data, credential, wallet, audience, lead, asset, content, or outcome satisfies an institutional prerequisite. |
| WC118-R048 | Advanced experiments remain inside approved hypothesis, variants, budget, audience, geography, guardrail, duration, and stop-loss boundaries. |
| WC118-R049 | Cross-client intelligence requires an accepted owner, minimum cohort, small-cell and membership-inference controls, lineage, confidence, and limitations. |
| WC118-R050 | Cross-client outputs never expose raw records, identify/rank customers, or become authority. |
| WC118-R051 | Crisis detection creates an urgent signal and evidence; every response remains approval-gated. |
| WC118-R052 | Every mutation binds actor, server-derived authority, package, operation, hash, idempotency key, exact owner versions, purpose, evidence, and deadline. |
| WC118-R053 | Same identity/hash replays; changed hash conflicts with zero owner/provider side effects. |
| WC118-R054 | Timeout, disconnect, crash, duplicate, reorder, restart, and late-result paths reconcile the original intent. |
| WC118-R055 | Emergency Stop fences new/queued action, preserves safe reconciliation, and prevents late authority. |
| WC118-R056 | Logs, traces, metrics, errors, fixtures, evidence, screenshots, and PR text remain secret-, PII-, audience-, lead-, content-, and payload-safe. |
| WC118-R057 | Web and WhatsApp reuse one BP owner state/command path with assurance, idempotency, correction, suppression, limitations, and Stop. |
| WC118-R058 | C/D/E positive, negative, outage, replay, isolation, consent, suppression, cost, accessibility, rollback, and channel journeys pass in Docker. |
| WC118-R059 | Each package has one immutable candidate and direct ledger evidence; hosted evidence is distinct and authority-bound. |
| WC118-R060 | Final author review repairs all findings and Founder handoff contains no self-approval, merge, deployment, provider action, spend, contact, traffic, or activation. |

## 8. Validation And Evidence

All authoritative checks run through repository-owned Docker/catalog controls. The implementer must
resolve current commands from the validation catalogue rather than treating stale examples as
authority.

Minimum evidence families:

- contract/solution/ledger digest, schema closure, changed-surface, C-059, and generated provenance;
- stable-skill/source uniqueness and manifest compatibility;
- secret-reference, placeholder, Key Vault, oauth/customer-credential, environment, tenant, purpose,
  audience, and redaction tests;
- campaign, WBE, provider-MCP, idempotency, reconciliation, spend, Stop, and rollback tests;
- first-party audience lawful-purpose, suppression, minimization, upload/delete, and leak tests;
- lead webhook, deduplication, qualification, routing, contact, booking, handoff, outcome, and human
  takeover tests;
- search assessment/change, lifecycle/email/suppression, multi-location, reputation, and strategy
  tests;
- institutional isolation, advanced experiment, aggregate privacy, and crisis escalation tests;
- Web/WhatsApp reuse, accessibility, bounded performance, SAST, dependency, secret, license,
  observability, CCT, and exact-candidate qualification.

The ledger starts `PLANNED`/`expected-fail`. A local emulator PASS is not hosted provider acceptance.
No host language tool, ad hoc container, prose, mock-only test, or stale evidence completes a runtime
requirement.

## 9. Definition Of Done

- [ ] All Section 3 preconditions pass.
- [ ] Every WC118 requirement has direct immutable evidence.
- [ ] Canonical C/D/E skill sources contain no active collision or duplicate behavior.
- [ ] All DMA-specific implementation remains in the mandated subtree.
- [ ] Secrets and credentials obey environment/customer/institutional compartments with negative isolation evidence.
- [ ] Package C passes with zero unauthorized live spend, audience upload, contact, or provider mutation.
- [ ] Package D passes with zero unauthorized live profile/site change or lifecycle contact.
- [ ] Package E passes with zero unauthorized institutional action or customer-data use.
- [ ] Each package freezes independently and can roll back without deleting owner facts/evidence or changing another package.
- [ ] Candidate behavior remains default-off and no excluded action occurred.
- [ ] Author review is PASS on the exact remote head.
- [ ] The prepared PR is open for Founder review without self-approval or merge.

## 10. Stops

Stop affected work when:

1. current-session implementation authorization is absent;
2. baseline, process-control, contract, solution, ledger, ancestry, or candidate identity fails;
3. an input/owner/path/provider decision is missing, contradictory, changed, or unaccepted;
4. implementation requires a new owner, public API, deployable, database, credential service,
   provider, CRM, booking system, CMS, email product, SEO product, platform-intelligence product, or
   protocol;
5. `CUSTOMER_OWNED` paid accounts or an unaccepted provider/account model becomes necessary;
6. consent, suppression, audience, lead, retention, crisis, institutional, or aggregate policy is
   ambiguous;
7. a credential would leave its accepted Azure-hosted owner or cross environment/customer purpose;
8. a consequential action cannot persist intent and reconcile without blind retry;
9. provider scope/data use exceeds the accepted package;
10. a generic platform schema/owner would need DMA-specific behavior;
11. a test, CCT, security, privacy, accessibility, observability, ledger, or qualification gate fails;
12. a threshold reduction, broad catch, silent default, success-shaped fallback, or stale evidence
    carry-forward is proposed;
13. deployment, provider connection, external action, spend, customer contact, traffic, or
    activation becomes necessary; or
14. exact-head author review and PR preparation cannot bind the remote 40-character head.

Record a blocker. Do not infer, compensate, widen scope, or continue dependent work.

## 11. Rollback And Reversibility

- Before each package freeze, revert only the failed story to the last executable milestone while
  retaining failure evidence.
- After freeze, any source, dependency, configuration, schema, provider capability, or build-input
  repair creates a new candidate and reruns affected dependency closure.
- Runtime rollback controls are implemented but not executed by this contract: disable the package
  gate, fence new work, preserve/reconcile in-flight intents, restore the prior projection, and keep
  append-only plans, commands, spend, leads, messages, provider facts, and CE evidence.
- Audience deletion, unsubscribe/suppression, and externally requested corrections continue through
  their safe owner paths during rollback.
- Rolling back C, D, or E cannot activate, rewrite, or delete another package.

## 12. Current Authorization Boundary

Founder acceptance of this document would approve the solution/implementation contract only.
Implementation requires a later explicit current-session answer to the gate in Section 1. Deployment,
cloud/provider mutation, credentials, spend, audience upload, contact, traffic, activation, PR
approval, and merge remain separate Founder decisions.

## 13. Architecture Author Review

### 13.1 Findings And Repairs

| Lens | Finding | Repair | Result |
|---|---|---|---|
| Independent executability | The first pass permitted a surface class without fixing DMA file ownership | Added exact module, MCP, contract, fixture, and test paths in Section 4 | RESOLVED |
| Persistent truth | A runtime implementer could infer a new lead/lifecycle store | Bound implementation to the solution record-owner matrix and made any missing generic-owner semantic a stop | RESOLVED |
| External inputs | Live keys or accounts could be mistaken for implementation prerequisites | Required emulators and non-secret references; separated local, hosted, deployment, external-action, and activation evidence | RESOLVED |
| Provider adoption | Existing records contain stale named-provider suggestions and unresolved choices | Required provider-neutral implementation and separate acceptance before provider-specific code | RESOLVED |
| Granularity | C/D/E needed independently executable order and acceptance | Added WC118-00 through WC118-25 with explicit dependencies, actions, tests, exits, freezes, and cross-package proof | PASS |
| Requirement closure | Contract obligations needed machine-checkable identity | Added exactly WC118-R001 through WC118-R060 and a digest-bound ledger | PASS |

### 13.2 Result

The complete Work Contract was re-read against its solution contract, parent requirements, WC-114
through WC-117, ADR-026, provider/secret research, Platform IT Expert handoff requirements, and all
quality lenses. Requirements, owners, source allocation, dependency order, interfaces, states,
idempotency, reconciliation, secrets, security, privacy, consent, suppression, cost, observability,
tests, hosted evidence, rollout, rollback, exclusions, and stops are explicit.

**Result: PASS for Founder review.** The Platform IT Expert is not authorized to implement until the
Founder accepts the exact solution/contract package and separately answers the current-session
implementation gate. No deployment, provider action, spend, contact, traffic, activation,
self-approval, or merge is authorized.
