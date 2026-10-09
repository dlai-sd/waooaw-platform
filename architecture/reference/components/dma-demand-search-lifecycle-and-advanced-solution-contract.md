# DMA Packages C/D/E Demand, Search, Lifecycle, And Advanced Solution Contract

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Status | CANDIDATE FOR FOUNDER REVIEW - IMPLEMENTATION, DEPLOYMENT, PROVIDER CONNECTION, EXTERNAL ACTION, CUSTOMER TRAFFIC, AND ACTIVATION UNAUTHORIZED |
| Version | `1.0.0-candidate.1` |
| Parent requirement | `architecture/reference/components/dma-onboarding-and-autonomous-operation-enterprise-requirements.md` Sections 8-18 and 20.4 |
| Generic employment baseline | WC-114/WC-115 Conversational Employment Protocol |
| Package dependencies | WC-116 Package A; WC-117 Packages B1/B2 |
| Intended implementing office | Platform IT Expert (INST-010), only under WC-118 after separate current-session Founder implementation authorization |
| Constitutional basis | C-001, C-003, C-005, C-007, C-023, C-026, C-035, C-037, C-041, C-043, C-048, C-049, C-050, C-051, C-053-C-057, C-059, C-062-C-063, C-065-C-066, C-070-C-071, C-078-C-080, C-088-C-091, C-094; ADR-002, ADR-003, ADR-009, ADR-010, ADR-014, ADR-020-ADR-024, ADR-026, ADR-029, ADR-031, ADR-034-ADR-035 |

## 1. Objective And Package Closure

This contract closes the solution boundary for three dependency-ordered DMA packages. Each package
is independently frozen, qualified, activated, and reversible.

| Package | Bounded outcome | Consequential side effects | Separate activation boundary |
|---|---|---|---|
| C - Paid demand and lead conversion | Approved paid campaigns generate and safely progress suitable enquiries through customer-owned rules | Campaign and budget mutation, provider spend, lead capture, communication, booking/handoff, conversion upload, optional first-party audience use | Package C activation; first-party audience activation remains a separately qualified sub-gate |
| D - Search, lifecycle, and operating scale | DMA improves discoverability, retention, multi-location consistency, reputation handling, and periodic strategy | Approved website/profile changes, consented email/lifecycle messages, location-level actions, approved review responses | Package D activation; each connected owner/provider remains separately ready |
| E - Institutional and advanced capabilities | WAOOAW institutional marketing and advanced optimization operate in a boundary that cannot consume customer authority | Institutional campaigns, advanced creative experiments, crisis actions, cross-client aggregate learning | Package E activation; institutional marketing, crisis response, and cross-client learning each require explicit authority |

Package C depends on qualified Package A employment semantics and the exact Package B creative,
publication, measurement, and asset contracts it consumes. Package D may use Package C lead/outcome
evidence but cannot depend on paid media for basic search or lifecycle operation. Package E depends
on qualified Package C/D behavior for any advanced optimization that uses those outcomes.

Qualification never grants deployment, provider connection, credential entry, external action,
customer traffic, spend, data upload, customer contact, or activation.

## 2. Protected Invariants

1. Business Platform (BP) remains the public facade, relationship authority, customer projection
   owner, and public error mapper.
2. DMA owns profession-specific interpretation only under `src/digital-marketing-agent/**`.
3. Professional Runtime (PR) owns durable external intent, dispatch coordination, cancellation,
   reconciliation, and Emergency Stop fencing.
4. Constitutional Engine (CE) validates every consequential tool action before dispatch and records
   evidence before governed success.
5. Work and Billing Engine (WBE) alone owns entitlement, budget availability, reservation, actual
   charge, refund/credit, management fee, and commercial consequence.
6. AI Runtime (AIR) remains proposal-only. Model or provider output cannot approve a campaign,
   audience, lead action, website change, message, reputation response, institutional claim, or
   cross-client conclusion.
7. ADR-026 `WAOOAW_MANAGED` is the only accepted paid-account model. `CUSTOMER_OWNED` remains
   unavailable until separately authorized.
8. A plan, approval, wallet balance, provider acceptance, receipt, webhook, click, lead, or model
   score is not business success. Owner evidence and reconciliation determine truthful state.
9. Customer authority, data, credentials, budgets, audiences, leads, locations, messages, outcomes,
   and evidence never cross tenant, relationship, account, location, agent instance, or environment.
10. Trial mode cannot spend, upload an audience, contact a real lead, change a profile/site, send a
    lifecycle message, or execute institutional actions.
11. Missing, placeholder, expired, revoked, stale, partial, disputed, suppressed, unverified, or
    unknown state never becomes ready, eligible, authorized, active, contacted, converted, or
    successful.
12. Emergency Stop fences new external actions, prevents late results from creating authority, and
    preserves bounded reconciliation and immutable evidence.
13. Consent or lawful-purpose evidence is purpose-, channel-, provider-, audience-, account-, and
    version-specific. Employment agreement is not blanket end-user consent.
14. Suppression, withdrawal, opt-out, unsubscribe, complaint, sensitive/high-risk, and apparent-minor
    states take precedence over nurture, optimization, automation, and performance goals.
15. No guarantee is made for ranking, AI citation, impressions, leads, booking, conversion, revenue,
    reputation recovery, or market leadership.
16. Provider limits, scopes, policies, API versions, account eligibility, and test facilities are
    retrieved capability facts with freshness and provenance, not constitutional constants.
17. Customer facts and approved claims are never inferred from model output, provider suggestions,
    competitor content, or cross-client statistics.
18. Package E institutional authority cannot be reused as customer authority, and customer
    authority cannot be reused for WAOOAW institutional marketing.

## 3. Reuse And Build-Versus-Adopt Decisions

| Concern | Decision | Constraint |
|---|---|---|
| Employment, plans, commands, material changes | Reuse WC-115 | No DMA-specific public lifecycle or command |
| Paid account ownership | Reuse ADR-026 WAOOAW MBM and Google MCC model | Customer-owned model remains blocked |
| Commercial controls | Reuse WBE and ADR-034 | DMA never owns wallet truth or invoice calculation |
| Model inference | Reuse AIR/PSE under ADR-024/ADR-029 | No direct OpenAI, xAI/Grok, or other model SDK/key in DMA |
| External actions | Reuse ADR-020 MCP Tool Registry with CE pre-call validation | Closed provider-neutral tools only |
| Customer delegated OAuth | Reuse ADR-021 oauth-vault | Tokens never enter DMA, AIR, BP, PR, logs, evidence, or source |
| Environment platform secrets | Reuse ADR-014 Azure Key Vault references by managed identity | Separate Demo/UAT/Production vault and identity boundaries |
| Customer-specific non-OAuth credentials | Reuse an accepted Azure-hosted customer credential owner when it supports the exact credential class | If no accepted owner exists, the dependent story stops; WC-118 cannot invent a vault service |
| Campaign creative/assets/publication evidence | Reuse WC-117 | Paid media cannot silently redefine draft or rights truth |
| Lead/booking/customer outcome owner | Reuse the accepted customer-domain record owner and booking/CRM integration when pinned at WC-118 baseline | No generic lead database or booking product may be invented |
| Search evidence | Adopt official Search Console/Business Profile/analytics APIs behind accepted MCP owners; public observation remains terms-bound | Paid SEO data provider remains a separate adopt/ADR decision |
| Website changes | Reuse an accepted CMS/customer-asset owner behind MCP | Without an accepted owner, deliver approved change packages only |
| Email/lifecycle transport | Provider-neutral `email-mcp` contract | Named provider adoption, sender-domain setup, and live credentials require accepted decision and hosted authority |
| Multi-location | Compose existing relationship/location/account references | No tenant or employment per location unless separately decided |
| Institutional marketing | Separate WAOOAW institutional relationship, Decision Space, WBE bucket, credentials, and evidence | No customer record can satisfy an institutional prerequisite |
| Cross-client intelligence | Aggregate only through an accepted privacy-preserving platform-intelligence owner | No raw customer record, small cohort, or re-identifiable export |

## 4. Stable Skills And Package Boundary

| Stable skill | Package | Accepted meaning | Explicitly prohibited |
|---|---|---|---|
| `PAID_MEDIA_MANAGEMENT` | C | Plan, approve, fund, launch, monitor, pause, reconcile, and report Meta/Google campaigns under ADR-026 | Unapproved spend, unsupported provider/account model |
| `FIRST_PARTY_AUDIENCE_ACTIVATION` | C sub-gate | Purpose-specific minimized audience activation after lawful-basis, eligibility, suppression, transfer, and deletion gates | Treating employment or CRM possession as consent |
| `LEAD_MANAGEMENT` | C | Capture, acknowledge, deduplicate, qualify, route, nurture, book/handoff, and record outcome using customer rules | Autonomous price/legal/clinical/inventory commitments |
| `MARKETING_PERFORMANCE` | C/D | Evidence, freshness, attribution limits, spend/outcome reporting, and improvement proposal | Fabricated conversion or causal certainty |
| `SEARCH_DISCOVERABILITY` | D | Local SEO, traditional search, GEO/AEO assessment, approved content/change packages, and evidence | Rank/citation guarantees or manipulative pages |
| `CUSTOMER_LIFECYCLE` | D | Consented lifecycle, retention, reactivation, suppression, and outcome measurement | Purchased/scraped lists or contact after withdrawal |
| `MULTI_LOCATION_OPERATIONS` | D | Location hierarchy, scoped approvals, account routing, local consistency, and aggregate reporting | Cross-location budget/account/lead leakage |
| `REPUTATION_AND_RESPONSE` | D | Monitor, classify, propose, approve, publish where authorized, and escalate sensitive/crisis matters | Fabricated reviews or autonomous crisis response |
| `INSTITUTIONAL_MARKETING` | E | WAOOAW-only self-marketing under institutional authority | Appearing in customer catalogues or using customer assets |
| `ADVANCED_CREATIVE_OPTIMIZATION` | E | Approved creative variants and bounded experiments using qualified Package B/C evidence | Model-selected spend/authority or unapproved claims |
| `ADVANCED_MULTI_CLIENT_INTELLIGENCE` | E | Thresholded, privacy-preserving aggregate learning | Customer-level export, ranking, or competitive exploitation |
| `CRISIS_COMMUNICATIONS` | E | Detection, immediate escalation, evidence preservation, and approved response | Autonomous publication or legal/regulatory response |

Legacy numeric labels are aliases only. The active DMA specification and manifest must resolve the
Skill 14 collision by assigning institutional marketing only to `INSTITUTIONAL_MARKETING`; customer
reputation behavior uses `REPUTATION_AND_RESPONSE`.

## 5. Owner And Trust-Boundary Map

| Owner | Owns | Must not own |
|---|---|---|
| BP | Customer projections, command validation, safe states/errors, accepted customer corrections | Provider clients, credentials, spend calculation |
| DMA | Domain rules, closed state interpretation, provider-neutral request meaning, limitations | Public authority, secrets, commercial truth |
| PR | Durable external intents, workflow, dispatch, cancellation, reconciliation, Stop | Approval, consent, lead/customer truth |
| CE | Constitutional validation and append-only evidence | Campaign/lead/search/lifecycle execution |
| WBE | Entitlement, budget buckets, reservations, charges, credits, fees, commercial consequence | Provider result or lead status |
| AIR/PSE | Minimized proposals and provider-neutral model provenance | Owner mutation or external action |
| oauth-vault | Customer OAuth acquisition, encrypted grants, scope/version/expiry/refresh/revocation | Campaign, lead, content, or outcome state |
| Azure Key Vault | Environment platform secrets and accepted environment master keys | Customer business records or ad hoc OAuth token copies |
| Paid-media MCPs | Meta/Google contract translation, provider correlation, capability facts | Budget authority, customer approval, retry authority |
| Lead/CRM/booking MCPs | Provider translation and exact receipts/webhooks | Qualification policy or customer-visible truth |
| Search/CMS/GBP MCPs | Read/change translation and provider receipts | Rank promises or approval |
| Email/lifecycle MCP | Consent-bound transport, unsubscribe/bounce/provider receipt | Consent truth or lifecycle decision |
| Platform analytics | Provider observations and mapping metadata | Attribution certainty or business outcome authority |
| Platform intelligence | Approved anonymized/aggregated statistics | Raw customer data or institutional/customer authority bridging |

### 5.1 Durable record ownership

| Record | Durable owner | DMA treatment |
|---|---|---|
| Employment plan, command, customer-visible package/skill projection | Existing BP WC-115 store with tenant RLS | Interpret through stable references; no duplicate lifecycle |
| External campaign/change/contact/booking intent and reconciliation | PR outbox/inbox and workflow state | Supply closed domain payload and interpret verified result |
| Entitlement, wallet, reservation, spend, fee, credit/refund | WBE | Read exact owner version/consequence only |
| Constitutional decision/evidence | CE append-only ledger | Reference evidence identity; never copy payload |
| OAuth grant | oauth-vault | Read health/reference only; token stays in owner |
| Non-OAuth customer credential | Accepted Azure-hosted customer credential owner | Read health/reference only; missing owner blocks the story |
| Campaign/provider object | Provider, through paid-media MCP owner | Keep opaque provider reference and verified receipt digest |
| Lead/contact/customer outcome | Accepted customer operational owner or generic BP domain-work projection fixed at baseline | DMA classifies/proposes; it does not create a second CRM truth |
| Booking/handoff | Accepted booking/CRM owner | Keep intent, correlation, receipt, and customer-safe outcome reference |
| Search/profile/site truth | Verified external owner through Search/GBP/CMS MCP | Keep assessment/change/receipt references, not a shadow site store |
| Consent, suppression, unsubscribe, withdrawal | Accepted customer operational/consent owner fixed at baseline | Treat current version as a mandatory dispatch prerequisite |
| Provider observations | Platform analytics immutable snapshot owner | Interpret source/freshness/coverage/limitations |
| DMA manifests, rule versions, state-machine definitions | DMA admitted image and digest-bound contracts | Immutable profession semantics only; no customer secret or duplicate owner fact |
| Cross-client aggregate | Accepted platform-intelligence owner | Consume only thresholded privacy-safe output |

No new persistent table is authorized by this contract. If an existing generic owner cannot preserve
the required identity, version, RLS, append-only/supersession, outbox/inbox, retention, and erasure
semantics, implementation stops for a separately accepted data contract.

### 5.2 Source allocation map

The following paths are the exact DMA-owned implementation surfaces. They are modules in the
existing DMA deployable, not new deployables:

| Concern | Exact source surface |
|---|---|
| C/D/E closed contracts and fixtures | `src/digital-marketing-agent/contracts/cde/**` |
| Paid campaign and audience semantics | `src/digital-marketing-agent/digital_marketing/paid_demand.py` |
| Lead and conversion semantics | `src/digital-marketing-agent/digital_marketing/lead_management.py` |
| Search/GEO/AEO semantics | `src/digital-marketing-agent/digital_marketing/discoverability.py` |
| Lifecycle and suppression semantics | `src/digital-marketing-agent/digital_marketing/lifecycle.py` |
| Multi-location and reputation semantics | `src/digital-marketing-agent/digital_marketing/operating_scale.py` |
| Institutional, experiment, aggregate, and crisis semantics | `src/digital-marketing-agent/digital_marketing/advanced_capabilities.py` |
| Meta Ads contract translation | `src/digital-marketing-agent/mcp/meta_ads/**` |
| Google Ads contract translation | `src/digital-marketing-agent/mcp/google_ads/**` |
| Provider-neutral lead/CRM/booking translation | `src/digital-marketing-agent/mcp/lead_operations/**` |
| Provider-neutral search/GBP/CMS translation | `src/digital-marketing-agent/mcp/discoverability/**` |
| Provider-neutral email/lifecycle translation | `src/digital-marketing-agent/mcp/lifecycle/**` |
| Direct C/D/E tests | `src/digital-marketing-agent/tests/cde/**` |

Meta Ads and Google Ads are already selected by ADR-026. A provider-specific CRM, booking, SEO data,
CMS, email, review, or platform-intelligence adapter may not be added under the provider-neutral
surfaces until its adoption and exact owner are accepted. Existing BP/PR/CE/WBE/AIR/Web changes are
limited to generic WC-115 registration, generated-client, projection, or owner behavior and cannot
contain a hard-coded DMA skill, state, provider, or rule.

## 6. Secret, Credential, And Environment Contract

### 6.1 Required compartments

- Demo, UAT, and Production use separate Azure Key Vaults, managed identities, oauth-vault data
  boundaries, databases, provider applications/accounts, and evidence identities.
- Platform-owned provider keys, app secrets, webhook verification secrets, and service credentials
  are environment secrets referenced from the environment Key Vault by least-privilege managed
  identity.
- Customer OAuth grants remain only in oauth-vault under server-derived environment, tenant,
  relationship, provider, account, scope set, purpose, token version, and expiry.
- Customer-specific API keys, login credentials, certificates, or private keys use only an accepted
  Azure-hosted customer credential compartment with the same server-derived coordinates. If the
  existing credential owner cannot represent the class, the capability is `NOT_CONFIGURED`.
- A shared secret name, prefix, label, application process, or customer-supplied reference is not an
  isolation boundary. Access is enforced by owner authorization, encryption boundary, managed
  identity/RBAC, purpose, audience, and negative cross-tenant tests.
- Vault-per-customer or deployment-stamp isolation may be selected only by an accepted platform
  architecture decision after scale, limits, RBAC, recovery, rotation, cost, and blast radius are
  evaluated. WC-118 cannot select that topology implicitly.

### 6.2 Non-secret placeholders

Committed schemas and templates may use:

```text
secretref://demo/platform/google-ads-app-secret
credentialref://demo/{tenant}/{relationship}/crm/{account}
oauthref://demo/{tenant}/{relationship}/meta-ads/{account}
https://provider.invalid/not-configured
```

These are references, never usable credentials. Empty values, `.invalid`, `CHANGEME`,
`PLACEHOLDER`, fixture/test values, unresolved references, and cross-environment references produce
`NOT_CONFIGURED`. No dummy secret is written to Key Vault to satisfy existence checks.

Local implementation and qualification use deterministic provider, oauth-vault, Key Vault, webhook,
CRM, booking, CMS, email, and analytics emulators. No live key, URL, login, token, certificate, or
private key is an implementation prerequisite.

### 6.3 Demo policy

- Demo may use official provider test accounts, development-mode assets, app-role/tester assets,
  sandbox facilities, or explicitly funded/credited accounts accepted by provider and PSE policy.
- A public or advertised free tier is never assumed to be permanent and never authorizes hidden
  spend or data-sharing enrollment.
- Demo secrets remain in Demo Key Vault; Demo customer grants remain in the Demo customer credential
  compartment. UAT, Production, and real-customer credentials never enter Demo.
- Demo evidence proves only the exact tested account, scopes, API version, capability profile, and
  asset class. It is not Production or general customer acceptance.

## 7. Package C Contract - Paid Demand And Lead Conversion

### 7.1 Paid campaign aggregate

`PaidCampaignVersion` is immutable and binds:

- tenant, relationship, instance, mode, stable skill, manifest, plan, Decision Space, WBE policy;
- provider/account model, channel, objective, geography, schedule, budget ceiling, pacing, stop
  rule, management fee version, conversion definition, landing destination, creative/rights;
- audience basis, exclusions, age/location constraints, first-party-audience state when applicable;
- exact approval, assurance, provider capability, credential, app/account eligibility, policy,
  prompt/model provenance for proposals, and evidence references.

Legal states:

```text
DRAFT -> NEEDS_INPUT | READY_FOR_REVIEW | WITHDRAWN
READY_FOR_REVIEW -> CHANGES_REQUESTED | APPROVED | WITHDRAWN
APPROVED -> READINESS_PENDING | SUPERSEDED | WITHDRAWN
READINESS_PENDING -> READY | BLOCKED | SUPERSEDED
READY -> DISPATCHING | PAUSED | SUPERSEDED
DISPATCHING -> ACTIVE | RECONCILING | FAILED
ACTIVE -> PAUSE_PENDING | CHANGE_PENDING | COMPLETED | RECONCILING
PAUSE_PENDING -> PAUSED | RECONCILING
RECONCILING -> ACTIVE | PAUSED | FAILED | OUTCOME_UNKNOWN
```

Every material change creates a successor version and requires new approval. Spend never continues
when wallet, Decision Space, provider eligibility, consent, credential, Stop, or exact version is
not current.

### 7.2 Budget, spend, and reconciliation

- Campaign ceiling, period ceiling, provider allocation, pacing tolerance, low-balance threshold,
  pause rule, and management fee are exact accepted versions.
- WBE reserves before provider mutation, commits actual provider charges, releases unused
  reservation, records pass-through credits/refunds, and reconciles discrepancies.
- Provider-reported spend and WBE ledger remain distinct. Difference above accepted tolerance blocks
  new spend and creates reconciliation; DMA cannot compensate by changing a campaign.
- Zero balance or expired authority causes provider pause intent, not silent cancellation.
- Spend state is `AVAILABLE`, `LOW`, `EXHAUSTED`, `STALE`, `DISPUTED`, or `UNKNOWN`; only current
  `AVAILABLE` can authorize new spend.

### 7.3 Provider-neutral paid-media tools

Closed operations are:

- `paid_media.get_account_readiness`
- `paid_media.create_campaign`
- `paid_media.get_campaign_status`
- `paid_media.update_campaign`
- `paid_media.pause_campaign`
- `paid_media.get_spend`
- `paid_media.get_conversion_observations`
- `paid_media.upload_conversion` only when separately ready and authorized

Provider-specific Meta/Google DTOs remain inside MCP owners. Every mutation binds one durable PR
intent, canonical request digest, idempotency key, exact campaign version, WBE reservation, CE
evidence, account/capability/credential version, and deadline. Timeout or disconnect reconciles the
original intent; blind retry is prohibited.

### 7.4 First-party audience activation

`AudienceActivationVersion` is independently gated:

```text
PROPOSED -> RIGHTS_REVIEW -> ELIGIBILITY_REVIEW -> READY_FOR_APPROVAL
READY_FOR_APPROVAL -> APPROVED | REJECTED | WITHDRAWN
APPROVED -> PREPARING -> UPLOAD_PENDING -> ACTIVE | PARTIAL | FAILED | OUTCOME_UNKNOWN
ACTIVE -> REFRESH_PENDING | DELETE_PENDING | EXPIRED
DELETE_PENDING -> DELETED | PARTIAL | OUTCOME_UNKNOWN
```

It requires customer attestation and evidence for collection rights, notice/consent or other
accepted lawful basis, named provider and purpose, eligible account, approved identifiers,
minimization/normalization/hash method, suppression/withdrawal handling, transfer, retention,
deletion, minimum audience limitations, and provider policy. Raw identifiers never enter AIR,
logs, evidence, or DMA durable state. Ordinary contextual/geographic/interest/keyword campaigns may
remain available when this sub-gate is blocked.

### 7.5 Lead and conversion aggregate

`LeadCaseVersion` binds source/campaign where available, customer-domain vocabulary, consent/channel
permissions, identity confidence, duplicate group, qualification/routing rules, service area,
availability, response expectation, owner, booking/handoff route, suppression, and evidence.

Legal states:

```text
CAPTURED -> ACKNOWLEDGEMENT_PENDING | SPAM | INVALID | DUPLICATE | SUPPRESSED
ACKNOWLEDGEMENT_PENDING -> ACKNOWLEDGED | ESCALATED | EXPIRED
ACKNOWLEDGED -> QUALIFICATION_PENDING | HUMAN_TAKEOVER | SUPPRESSED
QUALIFICATION_PENDING -> QUALIFIED | UNQUALIFIED | NEEDS_INPUT | HUMAN_TAKEOVER
QUALIFIED -> ROUTING_PENDING | NURTURE_PENDING | HUMAN_TAKEOVER
ROUTING_PENDING -> ROUTED | BOOKING_PENDING | FAILED | OUTCOME_UNKNOWN
BOOKING_PENDING -> BOOKED | HANDED_OFF | FAILED | OUTCOME_UNKNOWN
NURTURE_PENDING -> NURTURING | SUPPRESSED | EXPIRED
ROUTED | BOOKED | HANDED_OFF | NURTURING -> WON | LOST | NO_RESPONSE | UNKNOWN_OUTCOME | SUPPRESSED
```

Sensitive, disputed, high-value, complaint, apparent-minor, unsupported-domain, or outside-authority
cases require human takeover. DMA never autonomously makes price, legal, clinical, inventory,
eligibility, credit, or service guarantees. Conversion evidence names source, method, window,
confidence, and attribution limits; missing conversion remains unknown.

## 8. Package D Contract - Search, Lifecycle, And Operating Scale

### 8.1 Search and discoverability

`DiscoverabilityAssessmentVersion` binds verified business identity, location/category/service facts,
site/property ownership, source/API version, observation time, freshness, evidence class, confidence,
limitations, and customer corrections across:

- business information consistency and Google Business Profile readiness;
- crawlability, indexability, page meaning, internal links, structured information, performance,
  service/location coverage, and conversion routes;
- Search Console observations and public/provider-independent search evidence;
- useful question-led content grounded in customer-confirmed expertise;
- GEO/AEO clarity, citations, authority, and machine-understandable facts without citation promises.

Assessment is read-only. A change package is immutable and states target, exact before version,
proposed after value, owner, approval, rollback ability, evidence, and consequence. Provider/CMS
mutation occurs only after exact approval, credential/readiness, CE, and Stop checks.

### 8.2 Lifecycle and email

`LifecycleSequenceVersion` binds purpose, lawful basis/consent, source, audience/segment rule,
template/content version, channel, cadence, quiet hours, start/stop conditions, expiry, sender
identity, reply/escalation route, suppression policy, and approved claims.

States:

```text
DRAFT -> NEEDS_CONSENT_EVIDENCE | READY_FOR_REVIEW | WITHDRAWN
READY_FOR_REVIEW -> APPROVED | CHANGES_REQUESTED | WITHDRAWN
APPROVED -> READY | BLOCKED | SUPERSEDED
READY -> SCHEDULED | PAUSED
SCHEDULED -> DISPATCHING | CANCELLED | PAUSED
DISPATCHING -> SENT | PARTIAL | RECONCILING | FAILED
SENT -> OBSERVING | SUPPRESSED
OBSERVING -> COMPLETED | CORRECTIVE_PROPOSAL | SUPPRESSED
```

Unsubscribe, opt-out, withdrawal, hard bounce, complaint, legal hold, and customer correction update
the authoritative suppression owner before any later dispatch. Purchased, scraped, or
unsubstantiated lists are prohibited. No free-tier volume or provider is encoded as a permanent
entitlement.

### 8.3 Multi-location

Every action binds one location or an explicit approved location set. Location inheritance is
versioned for brand facts, prohibited topics, approval authority, channel accounts, budgets,
service areas, schedules, and escalation contacts. Location override never weakens constitutional,
consent, rights, Stop, or financial controls.

Brand-level approval applies only to the exact enumerated active locations and version. Location
account, lead, spend, content, review, and outcome evidence remain separable. Aggregate reporting
shows coverage and missing locations and never converts missing data to zero.

### 8.4 Reputation and periodic strategy

Review/mention observation remains read-only. Proposed response states are `NEEDS_INPUT`,
`READY_FOR_REVIEW`, `ESCALATED`, `APPROVED`, `PUBLISHED`, `RECONCILING`, `FAILED`, and
`OUTCOME_UNKNOWN`. Complaint, legal/regulatory, safety, discrimination, clinical, financial,
apparent-minor, extortion, media, or crisis content escalates without autonomous response.

Periodic strategy review compares accepted goals with evidence across search, content, paid demand,
lead, lifecycle, location, reputation, cost, and limitations. It produces a proposal and successor
plan only; it cannot alter authority or activate a package.

## 9. Package E Contract - Institutional And Advanced Capabilities

### 9.1 Institutional marketing isolation

Institutional work uses:

- organisation `WAOOAW_INSTITUTIONAL`;
- a dedicated employment relationship and agent instance;
- Decision Space `WAOOAW_INSTITUTIONAL_MARKETING`;
- institutional WBE budget/funding source and provider accounts;
- institutional Key Vault/oauth-vault/customer-credential coordinates;
- institutional plans, approvals, evidence, Stop scope, and reporting.

No customer relationship, credential, wallet, audience, lead, asset, content, claim, performance
record, or outcome may satisfy an institutional prerequisite. Portfolio claims require the accepted
minimum cohort/diversity threshold, immutable source evidence, disclosure, and current approval.

### 9.2 Advanced creative optimization

An experiment binds exact hypothesis, variants, audience boundaries, budget allocation, success and
guardrail metrics, minimum/maximum duration, stop-loss, statistical method, approval, and prohibited
changes. Optimization may propose or select only inside that accepted envelope. It cannot increase
total spend, widen geography/audience, introduce a new claim/asset, use first-party data, or continue
after Stop/guardrail failure without new authority.

### 9.3 Advanced multi-client intelligence

Cross-client learning is allowed only through an accepted platform-intelligence product that:

- removes direct identifiers and customer content;
- enforces minimum cohort size and domain/geography/time disclosure controls;
- prevents membership inference, small-cell reporting, and customer ranking;
- preserves source lineage, representativeness, freshness, confidence, and limitations;
- supports customer exclusion/withdrawal where required; and
- returns bounded benchmark/proposal facts, never raw records or authority.

Absent an accepted owner, privacy profile, and threshold policy, this capability remains unavailable.

### 9.4 Crisis communications

Detection may create an urgent signal and preserve the source. Every response remains approval-gated.
Legal, regulatory, safety, media, review-bomb, extortion, data-breach, or public-harm events route to
the named human/institutional authority. The DMA does not admit fault, threaten, make legal claims,
disclose personal data, delete evidence, or publish autonomously.

## 10. Shared Idempotency, Errors, And Customer Truth

Every mutation binds authenticated actor, server-derived tenant, relationship, instance, package,
operation family, canonical payload hash, idempotency key, expected owner versions, purpose,
assurance, CE evidence, WBE state, credential/capability version, and deadline.

Same identity/hash replays the original immutable result. Same identity with a different hash
conflicts with zero owner/provider side effects. `202 Accepted` means durable responsibility, not
business completion.

Public state uses the existing WC-115 problem contract and customer-safe mappings. Private owners use
closed reason codes including:

```text
NOT_CONFIGURED, NOT_ACCESSIBLE, INVALID_REQUEST, AUTHORITY_DENIED,
ASSURANCE_REQUIRED, VERSION_CONFLICT, IDEMPOTENCY_CONFLICT,
CONSENT_REQUIRED, SUPPRESSED, BUDGET_UNAVAILABLE, ACCOUNT_UNSUPPORTED,
CAPABILITY_STALE, CREDENTIAL_EXPIRED, SCOPE_INSUFFICIENT, RATE_LIMITED,
PROVIDER_UNAVAILABLE, RECONCILIATION_REQUIRED, OUTCOME_UNKNOWN
```

No error, metric, log, trace, fixture, screenshot, evidence, or PR text exposes secrets, raw
provider payloads, audience identifiers, lead/customer content, tenant existence, private strategy,
or re-identifiable cross-client data.

## 11. Observability, Cost, Security, And Privacy

- Telemetry binds privacy-safe correlation, package/skill/plan/version, owner state, provider/API
  capability version, credential health class, WBE reservation/charge class, dispatch/reconciliation,
  Stop, freshness, coverage, attribution method, and limitation codes.
- Metrics separate availability, readiness, spend, provider delivery, lead progression, conversion,
  search observation, lifecycle delivery, suppression, reputation, business outcome, and DMA
  performance.
- Costs are authorized/reserved before paid work, committed from actual usage, and reconciled on
  ambiguity. Fallback cannot silently change provider, data use, residency, quality, or cost.
- AIR inputs are minimized and PII-scrubbed under C-078. Audience identifiers, lead content, message
  bodies, raw reviews, and customer records do not enter prompts unless an accepted minimized purpose
  explicitly requires it.
- Web and WhatsApp reuse the same BP state, commands, assurance, idempotency, secure handoff,
  correction, suppression, and Stop semantics.

## 12. Current Provider And Compliance Fact Register

Facts below are implementation-free research inputs checked on 2026-10-09. They must be revalidated
from official sources at implementation freeze and hosted qualification.

| Official source | Candidate fact |
|---|---|
| Microsoft Azure multitenant Key Vault guidance | Shared, vault-per-tenant, and tenant-owned vault models have different isolation, scale, RBAC, cost, and blast-radius trade-offs; resource topology requires an explicit platform decision |
| Microsoft Azure Container Apps managed identity/secret guidance | Key Vault references use managed identity and least-privilege access; secret values are not embedded in source or image |
| Google Ads API access/OAuth/test-account documentation | API access, OAuth project/account approval, manager/client relationships, and test/production eligibility are explicit readiness facts |
| Google Ads Customer Match/Data Manager policy | First-party audience use requires eligible accounts, provider policy compliance, approved data handling, opt-out/suppression, and purpose-specific customer evidence |
| Meta Marketing API system-user/permission documentation | Server-to-server access, ad-account assets, `ads_management`/`ads_read`/`leads_retrieval`, lead webhooks, and custom audiences require exact app/account permissions |
| Google Search Console authorization | OAuth and verified property access are required; read-only and write-capable scopes remain distinct |
| Google Business Profile OAuth/setup | Project approval, merchant authorization, verified business ownership, and revocation are readiness facts |
| India Digital Personal Data Protection Act, 2023 and notified rules | Notice/consent where relied upon, purpose limitation, withdrawal, safeguards, processor controls, and breach handling require durable owner evidence; this contract does not provide legal advice |
| OpenAI and xAI official API/pricing/security pages | API access is credentialed and metered; keys are secrets; no permanent free-tier assumption is accepted |

## 13. Failure And Degraded Behavior

| Condition | Required behavior |
|---|---|
| Missing live credentials | Local qualification proceeds with emulators; hosted action remains `NOT_CONFIGURED` |
| Wallet/reservation stale, disputed, exhausted, or unknown | No new paid dispatch; preserve safe reads and reconciliation |
| Provider timeout after mutation | Persist `RECONCILING`; query original correlation; never duplicate |
| Lead webhook duplicate/reorder | Inbox/idempotency produces one logical lead transition |
| Consent/suppression uncertainty | Block audience/contact action; unrelated contextual campaign may continue if isolated |
| CRM/booking unavailable | Preserve lead and handoff intent; show limitation; no fabricated booking |
| Search/SEO provider unavailable | Use accepted provider-independent evidence or mark partial/unavailable |
| CMS/GBP change unsupported | Deliver approved change package/manual action; never claim applied |
| Email unsubscribe path unavailable | Fence new sends for affected scope and alert; unsubscribe is not degradable |
| Multi-location partial outage | Isolate affected location only when exact dependency proof exists |
| Reputation/crisis signal | Escalate; no autonomous response |
| Cross-client threshold not met | No benchmark/output; no smaller cohort fallback |
| CE unavailable | No new consequential action; safe reads and Emergency Stop remain |
| Key Vault/oauth-vault unavailable | No new credentialed action; no stale-secret fallback |
| Emergency Stop | Fence new/queued work, cancel where safe, reconcile in-flight, reject late authority |

## 14. Qualification And Activation Sequence

1. Freeze this solution contract and WC-118 digests.
2. Implement shared stable-skill, manifest, secret-reference, owner, state, and emulator foundations.
3. Implement and locally qualify Package C without live spend, lead contact, audience upload, or
   provider mutation.
4. Under separate hosted authority, qualify exact provider test assets/accounts and freeze Package C.
5. Founder separately decides Package C activation; first-party audience activation remains separate.
6. Implement and locally qualify Package D with search, CMS, email, CRM, booking, and profile
   emulators and no live change/contact.
7. Under separate hosted authority, qualify each selected provider/account and freeze Package D.
8. Founder separately decides Package D activation.
9. Implement and locally qualify Package E against institutional fixtures and privacy-safe aggregate
   fixtures without live institutional action or customer data.
10. Under separate authority, qualify the institutional boundary and accepted platform-intelligence
    owner; freeze Package E.
11. Founder separately decides Package E activation and any Production/customer traffic.

No step implies the next.

## 15. Acceptance Oracles

1. Each package can freeze and qualify independently without activating another package.
2. C campaign/spend/provider state never outruns WBE, CE, approval, credential, or provider evidence.
3. Duplicate, crash, retry, reorder, timeout, and restart paths create at most one logical external
   action and reconcile the original intent.
4. First-party audience activation is blocked independently without blocking lawful contextual work.
5. Lead capture through outcome preserves consent, suppression, human takeover, source, attribution
   limits, and customer-domain meaning.
6. Search assessment is provider-independent and approved changes are exact, reversible where
   supported, and truthfully verified.
7. Lifecycle dispatch stops on withdrawal/unsubscribe/suppression before performance optimization.
8. Multi-location actions cannot cross account, budget, approval, lead, asset, or Stop scope.
9. Reputation/crisis handling escalates sensitive cases and never fabricates or autonomously admits.
10. Institutional marketing uses only institutional authority, funding, credentials, evidence, and
    claims.
11. Cross-client intelligence emits nothing below accepted privacy thresholds and never reveals a
    customer or raw record.
12. Placeholder and unresolved secret references fail readiness while deterministic local
    implementation remains executable.
13. Demo/UAT/Production and customer compartments fail closed under cross-environment and
    cross-tenant attacks.
14. Web and WhatsApp show the same truthful owner state, corrections, suppression, limitations, and
    Stop behavior.
15. No package promises rank, leads, conversion, revenue, or permanent free provider access.

## 16. Stops

Stop affected work if:

- an existing owner or WC-115 command cannot express required behavior;
- a new public endpoint, authority owner, deployable, database, secret service, CRM, booking system,
  email provider, SEO provider, CMS, platform-intelligence product, or retention policy is required
  without acceptance;
- implementation requires `CUSTOMER_OWNED` paid accounts contrary to ADR-026;
- a customer credential class has no accepted Azure-hosted owner/compartment;
- a provider selection is required where the parent requirement or ADR leaves it open;
- a provider requires broader scopes, data use, or account ownership than accepted;
- consent, suppression, audience, lead, crisis, institutional, or cross-client policy remains
  ambiguous;
- a provider result cannot reconcile without blind duplicate action;
- DMA-specific logic would be placed outside `src/digital-marketing-agent/**`;
- a package would be advertised as available before exact manifest, dependency, qualification,
  hosted evidence where required, and separate activation; or
- implementation, deployment, provider connection, external action, spend, customer contact,
  traffic, or activation is proposed without exact separate authority.

## 17. Implementation Readiness

The solution is ready for Founder review and, only after acceptance, a separately authorized WC-118
implementation sprint. The Platform IT Expert receives fixed owners, package boundaries, stable
skills, states, identity, idempotency, secrets, provider-neutral tools, failure behavior, evidence,
qualification, rollout, rollback, exclusions, and stops. Open provider/adoption decisions are hard
stops rather than implementation discretion.

## 18. Architecture Author Review

### 18.1 Findings And Repairs

| Lens | Finding | Repair | Result |
|---|---|---|---|
| Source allocation | Authority boundaries were fixed, but the implementer could still invent DMA module paths | Added exact existing-deployable C/D/E contract, behavior, MCP, and test surfaces in Section 5.2 | RESOLVED |
| Data ownership | Lead, lifecycle, provider, consent, and aggregate records lacked one compact durable-owner matrix | Added Section 5.1, prohibited a new table, and made any generic-owner semantic gap a separate data-contract stop | RESOLVED |
| Secrets | The Founder requested implementation without waiting for keys, while dummy secret values could create false readiness | Kept non-secret references and deterministic emulators, required environment/customer compartments, and prohibited dummy Key Vault values from satisfying readiness | RESOLVED |
| Provider choice | Current records leave CRM, booking, SEO, CMS, email, review, and intelligence providers open | Kept provider-neutral contracts and made provider-specific adoption an explicit hard stop | RESOLVED |
| Authority | Combined C/D/E delivery could imply one broad activation | Retained independent candidate, hosted-evidence, rollback, and activation gates for C, D, E and the first-party-audience sub-gate | PASS |
| Requirements coverage | Parent Sections 8-18 and 20.4 were checked against skills, states, owners, failures, qualification, and WC-118 | All bounded outcomes map to a solution section and WC118 requirement | PASS |

### 18.2 Result

The complete solution contract was re-read against the parent DMA enterprise requirements,
WC-114/WC-115, WC-116, WC-117, ADR-026, the applicable ADR index, current DMA skill/dependency
records, official-source provider facts, and the Chief Solution Architect quality gate.

**Result: PASS for Founder review.** The package fixes scope, owners, source allocation, record
ownership, stable skills, states, interfaces, security, secrets, privacy, consent, commercial
controls, failure/reconciliation, observability, tests, qualification, rollout, rollback, exclusions,
and stops. It grants no implementation, deployment, provider action, spend, contact, traffic,
activation, self-approval, or merge authority.
