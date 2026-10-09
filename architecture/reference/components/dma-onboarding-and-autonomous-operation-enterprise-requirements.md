# DMA Onboarding And Autonomous Operation — Enterprise Requirements

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Enterprise Architect (INST-004) |
| Status | ENTERPRISE REQUIREMENTS COMPLETE — READY FOR CHIEF SOLUTION ARCHITECT |
| Author review | PASS — Enterprise Architect author review and receiving Solution Architect viewpoint review complete |
| Purpose | Controlling enterprise requirements for a detailed Solution Architecture Work Contract |
| Professional | Digital Marketing Agent (DMA) |
| Interface baseline | WC-115 Conversational Employment Protocol |
| Existing product boundary | DMA Release 1: `professionalVersion: 1.0.0`; specification revision `3.1` |
| Authority boundary | Architecture and planning only; no implementation, activation, deployment, provider connection, publication, advertising spend, or customer traffic is authorized by this component |

## 1. Objective

Enable a customer to trial or hire a complete digital marketing office through WAOOAW, understand
the office in ordinary business language, select outcomes rather than technical features, provide the
minimum required inputs, and operate the selected capabilities through the standard WAOOAW
conversational employment interfaces.

The DMA is not modelled as one human job title or as a menu of disconnected tools. It is one governed
digital professional office containing coordinated specialist capabilities. The office is accountable
for improving customer outcomes across digital visibility, engagement, enquiries, conversion,
retention, and measurable growth.

The Chief Solution Architect must translate this component into a bounded solution package and
detailed Work Contract without changing the customer outcomes, capability ownership, authority
boundaries, or canonical source rules defined here.

### 1.1 Mandatory DMA Source Boundary

All DMA-specific implementation must reside in the dedicated
`src/digital-marketing-agent/**` subtree. DMA business rules, domain state, maturity scoring,
capability logic, provider behavior, prompts, orchestration, and profession-specific schemas must
not be scattered across Business Platform, Professional Runtime, AI Runtime, WBE, Constitutional
Engine, generic agent adapters, or other WAOOAW source directories.

Other platform source directories may contain only thin, profession-neutral registration or
integration wiring required to invoke the accepted generic WC-115 interfaces. That wiring must not
duplicate or interpret DMA behavior. If the solution cannot preserve this boundary, the Chief
Solution Architect must stop and return the conflict for Founder decision rather than distributing
DMA implementation across platform owners.

## 2. Customer Promise

The DMA must help the customer answer five plain-language questions:

1. How visible and effective is my business online today?
2. What should we improve first?
3. What content and campaigns will we run?
4. Are those activities producing engagement, enquiries, customers, and growth?
5. What should we change next?

Every capability, screen, conversation, notification, report, and recommendation must trace to at
least one of these questions. Internal platform terms, provider terminology, maturity algorithms,
agent routing, prompts, adapters, and evidence mechanics must not be presented as customer value.

## 3. Controlling Architecture And Canonical Records

| Concern | Canonical owner | Rule |
|---|---|---|
| Professional identity and full skill definitions | `architecture/reference/agents/digital-marketing-agent.md` | One authoritative human-readable DMA specification |
| Runtime skill availability for a DMA version | Versioned machine-readable DMA skill manifest, admitted with the image | Exact stable skill IDs, versions, modes, dependencies, required inputs, side effects, and readiness |
| Prompt content | `architecture/reference/prompts/digital-marketing-agent-prompts.md` | Prompts reference stable skill IDs; prompts never define or activate a skill |
| Image, version, admission, and customer-instance model | `architecture/dma-agent-image-concept.md` | One immutable image per admitted DMA professional version; no image per customer or skill |
| Trial/hire relationship and conversational employment | WC-115 contracts and owner interfaces | Generic employment behavior; no DMA-only lifecycle branch in a platform component |
| Commercial entitlement and pricing | DMA billing profile and bundle definitions | References stable skill IDs and versions; never duplicates skill behavior |
| Provider and shared platform dependencies | `architecture/reference/skill-dependency-register.md` | Dependency inventory only; it must not contain a second DMA skill catalogue |
| Customer-visible outcomes | Business Platform relationship workspace | Customer projection and decisions; DMA results remain proposals until recorded by the owning platform component |

### 3.1 Duplicate Removal Rule

The Solution Architecture package must include a bounded source-consolidation plan:

1. Keep the DMA agent specification as the sole human-readable skill authority.
2. Create or designate one machine-readable skill manifest as the runtime authority for each admitted
   DMA version.
3. Replace duplicated normative skill descriptions in prompt, dependency, billing, image, fixture,
   and interface documents with stable skill references.
4. Retain only the local information those documents own: prompts, dependencies, prices, release
   subset, test inputs, or interface mappings.
5. Delete obsolete duplicated catalogues when no live consumer depends on them. If historical evidence
   must remain, mark it non-normative and move it to the repository-standard archive rather than
   leaving two active sources.
6. Reject any build or admission candidate when two active records disagree about skill identity,
   version, availability, customer inputs, side effects, or mode.

## 4. DMA Office Capability Model

These eight buckets are the customer-facing structure of the DMA office. Human agency role names may
be used to explain expertise, but they are not separate WAOOAW agents, employments, containers, or
customer purchases.

| # | Customer-facing capability | Included DMA work | Customer outcome | Industry expertise represented |
|---|---|---|---|---|
| 1 | Digital Strategy And Marketing Intelligence | Customer profiling; market research; digital maturity assessment; digital presence and account health audit; competitive intelligence; quarterly strategy review | Customer knows the current position, priorities, competitors, and next growth plan | Digital strategist; market research and competitive intelligence analyst |
| 2 | Content, Creative And Social Media | Content strategy; campaign themes; calendar; copy, image, and video creation; Instagram and Facebook publishing; later LinkedIn and consented WhatsApp content | Customer publishes relevant, consistent, correctly tagged content for the intended audience | Content strategist; copywriter; creative producer; social media manager |
| 3 | Paid Media And Campaign Management | Meta and Google campaign planning; content boosting; budget pacing; audience activation; creative testing and campaign optimization | Customer uses an approved budget to reach suitable audiences and generate measurable demand | Paid media specialist; performance marketer; media buyer |
| 4 | Marketing Performance And Improvement | Channel monitoring; engagement, enquiry and conversion measurement; attribution with disclosed limits; reporting; conversion-rate optimization; continuous improvement plan | Customer understands what is working, what is not, and what DMA will improve next | Marketing analyst; attribution analyst; conversion-rate optimization specialist |
| 5 | WhatsApp Customer Interface | Customer-DMA conversation; onboarding; input requests; approvals; notifications; reports; support; governed commands and status | Customer can work with DMA through WAOOAW's standard WhatsApp experience without losing the Web experience | Conversational marketing and customer engagement |
| 6 | Lead Management And Customer Growth | Lead capture; deduplication; qualification; scoring; routing; response; nurturing; booking or handoff; lifecycle communication; retention and reactivation | More suitable enquiries progress into customers and existing customers remain engaged | Demand generation; CRM and lifecycle marketing; marketing automation; revenue operations |
| 7 | Search And Digital Discoverability | Local SEO; Google Business Profile; website and technical SEO recommendations; structured information; GEO/AEO; search monitoring | Customers can find, understand, and trust the business across local, traditional, and AI-assisted search | SEO specialist; local search specialist; organic growth strategist |
| 8 | Client, Location And Reputation Operations | Multi-client isolation; multi-location coordination; approval operations; crisis communications; escalation; service cadence | DMA can serve complex customers safely without mixing locations, brands, authority, data, or responses | Account director; marketing operations; local marketing; reputation and communications |

### 4.1 Existing DMA Skill Disposition

The Solution Architect must use this mapping when consolidating the current catalogue. Existing
numbers are discovery labels, not the future durable identifiers.

| Existing entry | Target capability | Required disposition |
|---|---|---|
| Skill 0 Customer Profiling | Digital Strategy And Marketing Intelligence | Keep as `CUSTOMER_PROFILING` |
| Skill 1 Market Research And Maturity Scoring | Digital Strategy And Marketing Intelligence | Keep as `MARKET_RESEARCH_AND_MATURITY` and apply Section 5 |
| Skill 1b Platform Account Health Check And Standard Setup | Digital Strategy And Marketing Intelligence | Replace with `DIGITAL_PRESENCE_HEALTH_AUDIT`; scan and recommend only. Setup or repair requires a separately defined action capability |
| Skill 2 Content Strategy, Campaign Theme And Calendar | Content, Creative And Social Media | Keep as `CONTENT_STRATEGY_AND_CALENDAR` |
| Skill 4 Instagram Content | Content, Creative And Social Media | Merge channel-specific behavior under `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`; preserve Instagram as a supported channel capability |
| Skill 5 Facebook Presence | Content, Creative And Social Media | Merge under `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`; preserve Facebook as a supported channel capability |
| Skill 6 Google Business Profile | Search And Digital Discoverability | Place under `LOCAL_SEARCH_PRESENCE`; separate assessment, recommendation, and authorized change actions |
| Skill 7 WhatsApp Business Engagement | Lead Management And Customer Growth | Rename to `WHATSAPP_AUDIENCE_ENGAGEMENT`; this is marketing to the customer's audience and is not the WAOOAW customer-DMA interface |
| Skill 7b Lead Conversation Management | Lead Management And Customer Growth | Keep as `LEAD_CONVERSATION_MANAGEMENT` |
| Skill 8 Video And Visual Content | Content, Creative And Social Media | Keep as `VISUAL_AND_VIDEO_CONTENT`; asset rights, likeness, voice, and approval remain explicit |
| Skill 9 Performance Analytics And Reporting | Marketing Performance And Improvement | Keep as `MARKETING_PERFORMANCE_AND_IMPROVEMENT`; every report ends with supported next actions |
| Skill 10 Local SEO | Search And Digital Discoverability | Merge under `SEARCH_AND_DIGITAL_DISCOVERABILITY` |
| Skill 10b GEO | Search And Digital Discoverability | Merge as a declared GEO/AEO sub-capability; do not sell it as a guaranteed or independent magic channel |
| Skill 11 Paid Advertising | Paid Media And Campaign Management | Keep as `PAID_MEDIA_MANAGEMENT` |
| Skill 11b Customer Match | Paid Media And Campaign Management | Keep only as optional `FIRST_PARTY_AUDIENCE_ACTIVATION`, subject to Section 11 |
| Skill 11c Dynamic Creative Optimization | Paid Media And Campaign Management | Keep as an advanced sub-capability available only with sufficient creative, traffic, budget, and conversion evidence |
| Skill 12 Conversion Optimisation | Marketing Performance And Improvement | Rename to the industry-standard `CONVERSION_RATE_OPTIMIZATION` |
| Skill 13 Competitive Intelligence | Digital Strategy And Marketing Intelligence | Keep as `COMPETITIVE_INTELLIGENCE` and feed maturity and strategy reviews |
| Skill 14 WAOOAW Self-Marketing | Institutional-only DMA employment | Mark `INSTITUTIONAL_ONLY`; exclude from customer trial/hire selection and customer billing bundles |
| Undeclared “Skill 14 Reputation Management” references | Client, Location And Reputation Operations | Remove the conflicting numeric reference. Define `REPUTATION_MANAGEMENT` before it can become available |
| Skill 15 Email Marketing | Lead Management And Customer Growth | Place under `EMAIL_AND_LIFECYCLE_MARKETING` |
| Skill 16 Customer Lifecycle Management | Lead Management And Customer Growth | Keep as `CUSTOMER_LIFECYCLE_MARKETING` |
| Skill 18 Multi-Client Operations | Client, Location And Reputation Operations | Treat as an always-on office/platform operating control, not a separately sold customer skill |
| Skill 19 Multi-Location Management | Client, Location And Reputation Operations | Keep as `MULTI_LOCATION_MARKETING` when the customer has more than one governed location |
| Skill 20 Crisis Communications | Client, Location And Reputation Operations | Keep as `CRISIS_COMMUNICATIONS`; external response requires explicit human approval |
| Skill 21 Quarterly Strategy Review | Digital Strategy And Marketing Intelligence | Keep as `PERIODIC_STRATEGY_REVIEW`; cadence is contract-configured rather than encoded in the skill name |
| Phantom or prose-only Skill 3 references | Content, Creative And Social Media | Remove or migrate to `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`; do not create a durable Skill 3 solely to fill a numbering gap |

### 4.2 Capability Types

| Type | Meaning | Customer treatment |
|---|---|---|
| Selectable outcome capability | Produces a customer-requested marketing outcome | Customer may select it in trial or hire when the exact version is available |
| Supporting specialist capability | Used by another selected outcome | Shown as part of the outcome, not sold as confusing internal machinery |
| Always-on office control | Isolation, approvals, evidence, Stop, multi-client safety, and operating discipline | Included whenever DMA operates; not separately selected or advertised as a marketing result |
| Institutional-only capability | Work performed for WAOOAW under a separate institutional relationship | Never shown in a customer trial/hire catalogue |

### 4.3 Autonomous DMA Operating Loop

Autonomous operation means continuous governed professional work, not uncontrolled automatic action.
Each active outcome follows one observable loop:

```text
understand -> observe -> assess -> plan -> request missing input or approval
           -> act within authority -> verify outcome -> explain -> improve
```

| Step | DMA obligation |
|---|---|
| Understand | Use the confirmed customer profile, goals, selected outcomes, constraints, and current authority |
| Observe | Collect only permitted, fresh, outcome-relevant evidence |
| Assess | Distinguish fact, customer confirmation, professional inference, and unavailable evidence |
| Plan | Propose the smallest useful next action with expected outcome, cost, risk, and dependencies |
| Request | Ask for missing customer input or approval only when required; do not repeatedly ask for facts already held and current |
| Act | Execute only admitted skills and side effects inside current Decision Space, budget, consent, and mode |
| Verify | Reconcile provider receipts and customer outcomes; a request or provider acceptance is not automatically success |
| Explain and improve | Report in customer vocabulary, disclose limitations, and create the next evidence-based improvement plan |

### 4.4 Outcome Measures

| Capability | Primary customer measures |
|---|---|
| Strategy and intelligence | Maturity movement, completed priority actions, evidence coverage, and resolved information gaps |
| Content and social | Approved/published content, consistency, relevant reach, engagement, enquiries, and content-driven customer actions |
| Paid media | Qualified demand, conversion outcomes, spend, cost efficiency, pacing, and disclosed attribution |
| Performance and improvement | Measurement coverage, verified changes, improvement experiments, and supported outcome movement |
| WhatsApp customer interface | Completed customer decisions, response timeliness, successful secure handoffs, and unresolved attention |
| Lead and customer growth | Response, qualification, booking/handoff, conversion, retention, and reactivation outcomes |
| Search and discoverability | Accurate presence, relevant visibility, profile/website actions, enquiries, and evidence quality |
| Client, location, and reputation operations | Isolation, location consistency, approval timeliness, issue containment, and safe resolution |

## 5. Digital Marketing Maturity Assessment

### 5.1 Customer-Facing Scale

| Score | Maturity level | Meaning for the customer |
|---:|---|---|
| 1 | Not Visible Online | Customers can hardly find the business online |
| 2 | Basic Online Listing | Some profiles exist, but information is incomplete or outdated |
| 3 | Online Presence Established | Website and important business profiles are available |
| 4 | Regularly Active Online | The business publishes content and keeps profiles updated |
| 5 | Building Customer Engagement | Content receives views, reactions, messages, and enquiries |
| 6 | Generating Leads Online | Digital activities consistently bring potential customers |
| 7 | Converting Leads Into Customers | Leads are followed up, nurtured, and converted systematically |
| 8 | Growing Through Digital Marketing | Marketing decisions use performance data and continuous improvement |
| 9 | Achieving Predictable Digital Growth | Campaigns deliver repeatable leads, customers, and measurable returns |
| 10 | Leading The Market Digitally | The business continuously adapts, outperforms competitors, and sustains growth |

### 5.2 Assessment Dimensions

The overall score must be explainable through these customer-understandable dimensions:

| Dimension | What DMA assesses | Typical evidence |
|---|---|---|
| Business direction | Goals, target customers, offers, differentiation, and priorities | Customer-confirmed profile and goals |
| Online presence | Website and important business profiles are complete, current, and consistent | Public scan plus connected account metadata |
| Search visibility | The business can be found for relevant services and locations | Search Console, Business Profile, website, and public search observations |
| Content consistency | Relevant content is planned, produced, approved, and published regularly | Content calendar and channel history |
| Customer engagement | People view, react, message, enquire, and take useful actions | Channel and analytics observations |
| Lead handling | Enquiries are captured, answered, qualified, routed, and followed up | CRM, booking, inbox, or customer-confirmed process |
| Customer retention | Existing customers receive useful follow-up, reactivation, and loyalty communication | CRM or customer-confirmed lifecycle process |
| Measurement | The customer can connect marketing activity to meaningful business outcomes | Analytics, tags, CRM/booking, and disclosed attribution method |
| Improvement discipline | Performance is reviewed and changes are made from evidence | Review history, experiments, and approved improvement actions |
| Governance and trust | Accounts, permissions, consent, budgets, approvals, claims, and crisis routes are controlled | Connected-account status, customer attestations, and WAOOAW evidence |

### 5.3 Scoring Obligations

- The assessment is a deep analysis service, not a self-scored questionnaire.
- Account health is scanned for assessment. DMA does not repair or configure an account unless a
  separately available and authorized capability covers that action.
- Each dimension must show its score, evidence, freshness, confidence, missing inputs, and recommended
  next action.
- Verified observations, customer-confirmed facts, public observations, and professional inference
  must remain distinguishable.
- Missing or disconnected evidence must be shown as unavailable. It must not be silently scored as
  success or failure.
- The overall 1–10 result must be reproducible from versioned dimension scores and the equal-weight
  calculation in Section 5.5.
- No score may promise future revenue, ranking, enquiries, or market leadership.
- The customer must receive the scale before or with the assessment so the meaning of the score is
  transparent.
- Refresh occurs after material account connection, material business change, an agreed review
  cadence, or customer request.

The Chief Solution Architect must embody the scoring contract below, define its schema and versioning,
and preserve its evidence, freshness, confidence, minimum-coverage, correction, and backward-
compatibility rules. It must not introduce hidden scoring behavior or different weights.

### 5.4 Evidence Acquisition

| Source mechanism | Permitted use | Required treatment |
|---|---|---|
| Customer interview and confirmation | Business direction, current process, offline outcomes, constraints, and known gaps | Mark as customer-confirmed; do not present as independently observed |
| Public presence scan | Website, public profiles, published content, visible business information, and public search observations | Record observation time and limitations; obey provider terms and robots/access rules |
| Read-only connected accounts | Account completeness, channel history, analytics, search, advertising, and engagement observations | Separate consent, scoped authorization, freshness, revocation, and no setup/change side effect |
| Customer-owned operational systems | CRM, booking, commerce, call, or other outcome facts | Use owner APIs or approved imports; preserve source, scope, quality, and customer correction |
| Licensed or approved market sources | Market, audience, category, and competitor context | Preserve source rights, date, method, and confidence; no unsupported causal claim |

### 5.5 Initial Scoring Contract

The first version must use a transparent baseline that can later be revised only through an explicit
version change:

1. Score each of the ten dimensions independently from 1 to 10.
2. Attach the evidence, observation date, confidence, and explanation to every dimension score.
3. Mark a dimension `NOT_ENOUGH_INFORMATION` when evidence is insufficient; never convert missing
   access into a low score.
4. Compute the overall score as the equal-weight arithmetic mean of scored dimensions. Retain one
   decimal place for audit and show the customer the nearest whole-number level from Section 5.1.
5. Publish an overall score only when at least seven dimensions are scored. Otherwise publish a
   “Maturity assessment in progress” result with the missing evidence needed.
6. Always publish evidence coverage as `scored dimensions / 10`; the same overall number with
   different coverage must not appear equally certain.
7. Do not introduce hidden weights, industry benchmarks, or provider-generated grades in version 1.
8. Permit the customer to dispute a fact or score. Corrections create a new assessment version and
   preserve the prior result and reason for change.

## 6. Trial And Hire Modes

The same admitted DMA image may serve trial and hired customer instances. Mode, authority, selected
skills, credentials, budgets, approvals, evidence, and lifecycle belong to the customer Employment
Relationship and agent instance, not to separate image variants.

| Concern | Trial mode | Hire mode |
|---|---|---|
| Purpose | Demonstrate DMA understanding and planning value safely | Operate the selected marketing capabilities within agreed authority |
| Default scope | Profile, maturity assessment, recommendations, sample strategy, sample calendar, and non-published sample content | Contract-selected capabilities that are admitted, ready, connected, funded where needed, and authorized |
| External publication | Prohibited by default | Permitted only for an entitled publishing skill with current credentials and required approval |
| Advertising spend | Prohibited | Permitted only within explicit platform-recorded budget, campaign, provider, and approval authority |
| Customer data | Minimum data required for the trial outcome | Only data required for selected capabilities, with purpose and retention controls |
| Provider connection | Read-only connection may be offered only when separately consented and safely supported; otherwise customer supplies evidence | Scoped customer connection for the selected capability; no reusable credential enters the DMA image |
| Recommendations | Clearly labelled recommendations or samples | May become governed work only after applicable approval and authority checks |
| Upgrade | No silent conversion to hire; no trial state grants live authority | Requires explicit employment/commercial transition and a compatibility/readiness check |

### 6.1 Customer Selection And Partial Readiness

- Customers select desired business outcomes and channels in ordinary language. They are not required
  to understand internal skill IDs or agency roles.
- The domain adapter maps each selection to exact skill and dependency versions from the admitted
  manifest.
- The customer sees what is available now, available after providing an input or connection, included
  only in hire mode, unavailable, or planned for a later release.
- One unavailable skill must not block unrelated ready skills.
- A capability with multiple dependencies may start only the safe ready portion and must identify
  deferred work without implying full readiness.
- Selection does not grant authority. Trial/hire mode, entitlement, readiness, customer input,
  provider connection, approval, budget, and constitutional validation remain separate checks.
- Always-on office controls apply automatically and cannot be disabled through customer skill
  selection.

## 7. Conversational Employment And Channel Reuse

WC-115 is the standard onboarding and employment interface. DMA must fit it through a versioned domain
adapter and skill manifest; platform components must not add DMA-only employment logic.

Web and WhatsApp are channels over the same owner APIs and governed commands:

- Business Platform remains the ordinary public facade and customer-visible state owner.
- WhatsApp must reuse the same application operations, assurance, idempotency, authorization,
  evidence, status, correction, Stop, and failure semantics as Web.
- A WhatsApp message is not authority merely because it came from the customer's phone number.
- Channel-specific rendering and message delivery may differ; business decisions and state must not.
- A command initiated on one channel must be visible and reconcilable on another.
- Duplicate, delayed, reordered, or retried messages must not duplicate work, publication, spend, or
  customer communication.
- Sensitive details must be minimized for the channel. The customer must be routed to a secure
  experience when the assurance or interaction cannot safely occur in WhatsApp.
- Emergency Stop and human escalation remain available independently of a long-running skill.

## 8. Customer Inputs

DMA must ask only for inputs required by the selected outcome and must explain why each input is
needed.

| Capability | Minimum customer inputs |
|---|---|
| Strategy and maturity | Business facts; services; locations; target customers; goals; differentiators; current channels; known competitors; available baseline; optional read-only account connections |
| Content and social | Brand identity; approved claims; offers; audience; language; photos/video or permission to create assets; events; prohibited topics; publishing accounts; approval preference |
| Paid media | Ad accounts; lawful audience and conversion inputs; billing route; campaign objective; geography; budget and stop ceiling; creative approval; landing destination |
| Performance and improvement | Connected channel metrics; website analytics; conversion definition; CRM/booking outcome where available; baseline; attribution limitations |
| WhatsApp interface | Verified customer relationship; channel consent and preference; escalation contact; language; secure handoff route |
| Lead and lifecycle | Lead sources; qualification rules; service area; availability; routing owner; response expectation; booking route; CRM or approved record owner; communication consent and suppression rules |
| Search and discoverability | Verified business name, categories, services, locations, hours, contact details, website/CMS route, Business Profile/Search Console access where applicable, authoritative expertise and claims |
| Operations and reputation | Client/location hierarchy; local owners; approval matrix; brand boundaries; escalation contacts; crisis authority; response constraints |

## 9. Lead Management And Customer Growth Requirements

This capability uses the industry-standard grouping **Demand Generation, Lead Management, CRM And
Lifecycle Marketing**. It must cover the complete path rather than count enquiries alone:

```text
attract -> capture -> acknowledge -> deduplicate -> qualify -> route
        -> respond -> nurture -> book/handoff -> outcome -> retain/reactivate
```

The Solution Architecture must define:

- A customer-domain lead/outcome vocabulary rather than forcing every business to use “lead” or
  “appointment”.
- Source and campaign tagging where available.
- Spam, duplicate, invalid, existing-customer, unqualified, qualified, booked, won, lost, no-response,
  and unknown outcomes without fabricating certainty.
- Customer-owned qualification, routing, service-area, availability, and escalation rules.
- Response and handoff obligations that DMA can actually observe and satisfy.
- Human takeover for sensitive, exceptional, disputed, high-value, or outside-authority situations.
- Nurture, retention, reactivation, and suppression rules tied to lawful channel permissions.
- Traceable conversion measurement with visible attribution limitations.
- No autonomous price negotiation, legal promise, clinical claim, inventory promise, or other
  consequential commitment outside recorded Decision Space.

## 10. Search And Digital Discoverability Requirements

This capability combines **Local SEO**, **traditional search optimization**, and **GEO/AEO** under one
customer outcome: make the business easy to find, understand, and trust.

DMA may:

- Audit consistency and completeness of verified business information.
- Recommend or, when separately authorized, maintain Google Business Profile information and content.
- Assess website crawlability, indexability, page meaning, location/service coverage, structured
  information, internal linking, performance, and conversion routes.
- Plan useful content that answers genuine customer questions using customer-confirmed expertise.
- Monitor search visibility, profile actions, website visits, calls, directions, enquiries, and
  attributable outcomes where evidence supports them.
- Improve content clarity and authoritative citations for traditional and AI-assisted discovery.

DMA must not:

- Guarantee rank, inclusion, citation by an AI system, traffic, enquiries, or revenue.
- Create fake locations, reviews, expertise, authors, credentials, citations, or customer questions.
- Mass-produce low-value pages or content solely to manipulate ranking.
- Treat GEO/AEO as a separate magic channel disconnected from sound website, content, local presence,
  structured information, and authority.

The Solution Architecture must specify provider-independent evidence, customer correction, public
observation limits, freshness, change approval, and rollback for externally visible changes.

## 11. Paid Media And First-Party Audience Activation

Customer Match and equivalent provider features are not a separate customer-facing DMA department.
They are an optional **First-Party Audience Activation** sub-capability of Paid Media.

A WAOOAW hire or trial agreement authorizes the relationship between WAOOAW/DMA and the customer. It
does not by itself prove that the customer lawfully collected each person's data or may disclose and
use it for advertising-platform audience matching.

Before first-party audience activation, the platform must require:

- Customer attestation of collection rights, applicable notice/consent or other lawful basis, intended
  advertising purpose, and authority to share with the named provider.
- Provider-account eligibility and compliance with current provider terms.
- Data minimization, approved identifiers, secure transfer, purpose limitation, retention, deletion,
  suppression, and withdrawal handling.
- Minimum audience and matching limitations presented honestly.
- Separate readiness and authority from ordinary ad campaign management.

If these conditions are not met, ordinary contextual, geographic, interest, keyword, or platform
campaign options may remain available when otherwise authorized; first-party audience activation
must remain unavailable.

## 12. Skill Identity, Version, Image, And Availability

### 12.1 Stable Skill Identity

Current numeric labels contain gaps and collisions and must not become durable external identity.
The Solution Architecture must define stable semantic IDs, for example:

```text
CUSTOMER_PROFILING
MARKET_RESEARCH_AND_MATURITY
CONTENT_STRATEGY
SOCIAL_CONTENT_PUBLISHING
PAID_MEDIA_MANAGEMENT
MARKETING_PERFORMANCE
LEAD_MANAGEMENT
CUSTOMER_LIFECYCLE
SEARCH_DISCOVERABILITY
```

Existing numbers may remain temporary display or migration aliases only when the compatibility plan
requires them. Skill 14's collision between institutional self-marketing and reputation management,
the missing Skill 3 definition, out-of-order extensions, and obsolete version labels must be resolved
before a new manifest is accepted.

### 12.2 Image And Manifest Rules

- One admitted OCI image represents one exact DMA professional type and professional version.
- The image contains only behavior admitted for that version and reports its immutable digest.
- The image carries or is digest-bound to one machine-readable skill manifest.
- The manifest distinguishes `DOCUMENTED`, `IMPLEMENTED`, `QUALIFIED`, `TRIAL_AVAILABLE`,
  `HIRE_AVAILABLE`, `DEGRADED`, and `UNAVAILABLE`; documentation alone never means availability.
- Every skill declares version, capability bucket, required inputs, dependencies, provider
  connections, customer decisions, side effects, approval mode, trial behavior, hire behavior,
  evidence, cost/usage unit, failure behavior, Stop behavior, and compatibility.
- Customer relationships bind exact skill versions. An image or manifest update must not silently
  change an existing customer's selected behavior.
- Many isolated customer instances may use replicas of the same admitted image digest. Durable
  customer state, credentials, employment, billing, evidence, and identity remain platform-owned.
- No platform component branches on a hard-coded DMA skill list. It consumes admitted generic
  manifests and adapter contracts.

## 13. Required Chief Solution Architect Deliverables

The Chief Solution Architect must produce one coherent solution package and a detailed Work Contract
that includes:

1. Exact scope and staged delivery order for the eight capability buckets.
2. Canonical source consolidation and deletion/migration plan.
3. Stable skill taxonomy, aliases, versioning, and machine-readable manifest schema.
4. Mapping from each capability and skill to WC-115 discovery, planning, readiness, confirmation,
   execution, review, correction, Stop, and closure behavior.
5. Trial and hire state model with no silent authority progression.
6. Customer-input, connected-account, credential, provider, approval, and missing-input contracts.
7. Explainable maturity scoring contract and customer report.
8. Web/WhatsApp channel reuse design with one owner API and no duplicated business logic.
9. Lead-management and lifecycle state model.
10. Search/discoverability assessment, action, evidence, and limitation model.
11. Paid-media budget, audience, approval, spend, reconciliation, and first-party-data controls.
12. Image/manifest/admission/instance compatibility model.
13. Customer-visible failure, degraded-mode, stale-data, correction, and dispute behavior.
14. Observability, privacy, security, cost, rollback, reversibility, and Emergency Stop requirements.
15. Dependency-impact map across Business Platform, Professional Runtime, Constitutional Engine, AI
    Runtime/CTG, WBE, oauth-vault, domain adapter, Web, WhatsApp, data owners, and providers.
16. Executable fitness and acceptance contract covering positive, negative, outage, duplicate,
    retry, cross-tenant, cross-relationship, version, mode, and external-side-effect cases.
17. A staged implementation Work Contract for the Platform IT Expert that can be executed
    autonomously without making product, authority, schema, provider, consent, or scoring decisions.
18. Exact updates required to the canonical DMA agent specification, prompt references, dependency
    register, billing references, image concept, fixtures, and admission records, with obsolete
    duplicated normative content deleted or archived.
19. Customer-facing catalogue and maturity-report projections that use the vocabulary in this
    component and never expose internal skill numbering as the primary experience.
20. A source-allocation map proving that all DMA-specific implementation is contained under
    `src/digital-marketing-agent/**` and that any changes elsewhere are thin, profession-neutral
    WC-115 registration or integration wiring.

## 14. Mandatory Delivery Sequence

The solution must use a vertical-slice sequence. It must not implement all channels or skills at once.

| Stage | Required customer outcome |
|---|---|
| 1. Canonical foundation | One accepted DMA skill taxonomy and manifest; duplicate active catalogues removed |
| 2. Understand the business | Customer profile plus explainable 1–10 maturity assessment |
| 3. Plan the work | Prioritized recommendations, content strategy, campaign themes, and calendar |
| 4. Create safely | Customer-input-driven Instagram/Facebook content drafts with tags and approvals |
| 5. Publish safely | Authorized content publication with receipts, correction, rollback where supported, and Stop behavior |
| 6. Measure and improve | Channel observations, customer outcomes, limitations, and a next-action plan |
| 7. Generate and manage demand | Governed paid campaigns and end-to-end lead handling |
| 8. Extend channels and operations | Additional social channels, lifecycle, multi-location, reputation, and advanced optimization only after prior-stage evidence |

Each stage must be independently useful, reversible, observable, and releasable. Later-stage design may
be included, but later-stage availability must not be advertised until its implementation and
qualification gates pass.

## 15. Acceptance Criteria

The Solution Architecture and resulting Work Contract are acceptable only when:

- A customer can understand the DMA office without knowing WAOOAW component names or digital agency
  job titles.
- The eight capability buckets and 1–10 maturity scale are preserved in customer language.
- Every existing DMA skill and conflicting prose reference has the explicit disposition defined in
  Section 4.1; no numbering gap or collision is silently carried forward.
- Every documented skill has one stable identity and one canonical definition.
- Runtime availability is derived from the exact admitted image and manifest, not documentation.
- Every active customer outcome follows the governed operating loop in Section 4.3 and ends with
  verified results, an honest limitation, or a clearly identified next action.
- Trial and hire use the same standard employment interfaces but preserve distinct authority.
- Web and WhatsApp use the same owner operations and reconcile the same state.
- Customer inputs, missing inputs, account connections, consent, credentials, budgets, and approvals
  are explicit for every consequential capability.
- First-party audience activation does not rely on the hire/trial agreement as blanket end-user
  consent.
- Maturity scores, performance reports, attribution, recommendations, and claims expose evidence,
  freshness, confidence, and limitations.
- No external publication, ad spend, customer communication, account change, or consequential lead
  commitment can occur without exact current authority.
- One customer's data, credentials, budget, work, outcomes, or messages cannot cross to another
  customer, relationship, location, or agent instance.
- Provider outage, partial completion, retry, cancellation, delayed receipt, ambiguity, and Emergency
  Stop have explicit safe behavior.
- All DMA-specific implementation is contained under `src/digital-marketing-agent/**`; platform
  component directories contain no DMA business rules, domain state, scoring, provider behavior,
  prompts, orchestration, or profession-specific schemas.
- The Platform IT Expert can implement the Work Contract without inventing a business rule,
  customer promise, consent rule, provider choice, skill identity, scoring rule, or ownership boundary.

## 16. Stops

The Chief Solution Architect must stop and return the package for Enterprise Architecture or Founder
decision if any of the following occurs:

- A second active DMA skill authority is required.
- A customer-facing capability cannot map to an existing platform owner or WC-115 interface without
  creating a new authority boundary.
- A stable skill identity, image/version rule, trial/hire boundary, maturity scoring rule, consent
  rule, or external-side-effect approval remains ambiguous.
- A design requires one container per customer, a platform DMA branch, reusable credentials inside
  the DMA image, or duplicated Web/WhatsApp business logic.
- A design distributes DMA-specific implementation outside `src/digital-marketing-agent/**` or
  requires platform components to own or interpret DMA business behavior.
- A provider selection becomes necessary without an authorized technology decision.
- A capability would be advertised as available before exact manifest, dependency, conformance,
  qualification, and admission evidence exists.
- Implementation, protocol activation, deployment, provider connection, customer traffic, external
  publication, or ad spend is proposed without its separate authority.

## 17. Non-Goals

This component does not:

- Select Meta, Google, CRM, analytics, SEO, content-generation, or messaging provider products.
- Define implementation schemas, endpoints, queues, databases, frameworks, or deployment topology.
- Authorize implementation or modify WC-115.
- Activate the Conversational Employment Protocol.
- Connect a customer account, publish content, contact a lead, run an advertisement, or spend money.
- Guarantee marketing performance, search ranking, lead volume, conversion, revenue, or competitive
  leadership.
- Make every documented DMA skill available in Release 1.
- Turn specialist role names into separately hired WAOOAW agents.

## 18. Chief Solution Architect Handoff

The controlling design instruction is:

> Design one customer-understandable, outcome-driven DMA office that uses WC-115 for employment,
> one admitted DMA image and manifest for exact capability availability, one platform-owned customer
> relationship and instance for authority, and one canonical skill catalogue. Preserve the eight
> capability buckets, the published 1–10 maturity scale, trial/hire separation, Web/WhatsApp API
> reuse, evidence-first reporting, and safe external side effects. Do not introduce duplicate skill
> sources or ask the Platform IT Expert to invent unresolved product or architecture decisions.

## 19. WC-115 Pending Agent-Specific Compliance

### 19.1 Current WC-115 Boundary

WC-115 has qualified the generic Conversational Employment implementation, but it intentionally does
not provide DMA production semantics.

| WC-115 state | Current disposition |
|---|---|
| Generic platform qualification | PASS |
| Capability state | Disabled by default |
| Protocol activation | Not authorized |
| Deployment | Not authorized |
| Customer traffic | Not authorized |
| DMA production changes in WC-115 | None |
| Resolved platform blockers | CB-012, CB-014, and CB-015 are resolved |
| Agent-specific requirements | WC115-R024, WC115-R025, and WC115-R026 remain Founder-reserved for a separately authorized agent-specific delivery |

These are not defects to repair inside WC-115. They are the mandatory bridge between the generic
WAOOAW interfaces and every admitted professional. DMA is the first required implementation of that
bridge.

### 19.2 DMA Requirements Still To Be Delivered

| WC-115 requirement | DMA obligation | Required evidence before availability |
|---|---|---|
| WC115-R024 — Manifest and induction | Implement the exact immutable employment-interface manifest and DMA induction requirement set. Bind professional type/version, manifest version/digest, skill versions, trial/hire support, required customer inputs, dependencies, readiness, side effects, approval needs, and evidence expectations without adding DMA fields to the generic contract | Manifest completeness and digest tests; induction requirement contract tests; admitted image/manifest binding; missing, stale, unknown, and incompatible inputs fail closed |
| WC115-R025 — Plan and material change | Validate that a proposed DMA plan is meaningful for the selected outcomes without accepting or authorizing it. Classify whether a customer, goal, channel, budget, credential, skill, provider, or policy change is material and identify only the affected work that must relock | Plan-validation fixture matrix across all selected DMA capabilities; material/non-material boundary tests; exact current plan/manifest/Decision Space/WBE versions; proof that the adapter cannot mutate plan or authority |
| WC115-R026 — Isolation and performance | Prove whether unaffected DMA skills can continue when one dependency changes or fails. Keep `UNKNOWN` fail-closed. Separately assess customer business outcomes and DMA professional performance with evidence and attribution limitations | Dependency PASS/FAIL/UNKNOWN tests; cross-skill and cross-customer isolation; outcome/performance separation; stale and disputed evidence tests; no unsupported attribution or success |

### 19.3 Required Domain-Adapter Operations

DMA and every future agent must implement the accepted generic domain-adapter operations without
changing their authority:

| Operation | Agent responsibility | Agent must not do |
|---|---|---|
| `getEmploymentInterfaceManifest` | Return one exact immutable interface manifest for the admitted professional version | Activate the protocol, grant entitlement, or claim readiness from documentation alone |
| `getInductionRequirementSet` | Return profession-specific customer inputs and dependencies in the generic requirement envelope | Collect unrelated data or mark an unmet requirement complete |
| `validatePlanCandidate` | Assess domain meaning, completeness, dependencies, and conflicts | Accept the plan, create authority, reserve money, or mutate relationship state |
| `classifyMaterialChange` | Identify materiality and the bounded work affected by a proposed change | Change the plan, silently broaden relock, or waive confirmation |
| `evaluateDependencyIsolation` | Prove that ready work is isolated from a changed or failed dependency | Guess isolation, continue on `UNKNOWN`, or allow one skill failure to corrupt unrelated work |
| `getPerformanceAssessment` | Report customer business outcomes and professional performance as separate evidence-based meanings | Convert activity, provider acceptance, spend, or unsupported correlation into customer success |

Business Platform remains the public facade and authoritative relationship composer. Constitutional
Engine owns constitutional decisions and evidence. WBE owns commercial and skill eligibility.
Professional Runtime owns admitted execution, cancellation, reconciliation, and Stop. AIR remains
proposal-only. The agent adapter owns domain interpretation only.

### 19.4 Standard-Interface Gates For DMA And Future Agents

| Gate | Mandatory compliance |
|---|---|
| Generic contract | DMA, Trading, Tutor, and future professions use the same BP/domain-adapter schemas; profession-specific platform fields are prohibited |
| Exact inventory | Every offered agent version has an exact manifest, adapter version, digest, conformance evidence, and supported protocol version |
| Compatibility | Complete, current, exact-major evidence may become activation-eligible; partial, stale, unknown, missing, or mixed mandatory major versions fail closed |
| Activation separation | Compatibility PASS and `activationEligible=true` are evidence only; neither activates, deploys, or admits customer traffic |
| Partial readiness | Ready skills may proceed only when their dependencies, Decision Space, and commercial eligibility are isolated; deferred skills name the missing requirement and remain paused |
| Induction truth | A conversation or AI proposal creates no customer fact until BP validation, required confirmation, and constitutional evidence complete |
| Plan truth | Initial plans and material changes bind exact versions, require applicable confirmation, and create append-only successor versions |
| Commercial truth | WBE alone decides funded, exhausted, stale, or otherwise ineligible skill work; protected read, Stop, and constitutional paths remain available |
| Generated clients | Each wire contract has one generated owner client with pinned generator/version/input digest and deterministic regeneration; handwritten duplicate DTOs and cross-owner clients are prohibited |
| Idempotency | Every mutation binds authenticated actor, server-derived tenant, relationship, operation family, payload digest, idempotency key, and expected authoritative versions |
| Reconciliation | Unknown owner/provider outcomes reconcile the original work; customers and channels do not retry consequential work blindly |
| Customer-safe state | Customer experiences distinguish pending, partial, stale, unknown, blocked, unavailable, and ready without exposing raw owner codes or implying success |
| Security and tenancy | Tenant and relationship are server-derived; cross-tenant, cross-relationship, cross-instance, reusable credential, and caller-asserted authority paths fail closed |
| Emergency Stop | Stop remains visible, accessible, and operational even when BP, CE, WBE, AIR, identity, provider, or agent adapter dependencies are degraded |
| Trial and hire | Trial rejects consequential work unless a current trial policy explicitly permits it; hire still requires exact entitlement, readiness, authority, budget, consent, and approval |
| Rollback | Candidate behavior remains behind a default-off BP capability gate; rollback is Founder-controlled, fences new work, reconciles earlier work, and preserves append-only history and constitutional evidence |
| Qualification | Positive, negative, outage, duplicate, replay, stale-version, mixed-major, accessibility, security, observability, isolation, rollback, and customer-journey evidence must pass through repository-owned Docker runners |

### 19.5 Solution Architect Additions Required

The detailed DMA Work Contract must therefore:

1. Treat WC115-R024, WC115-R025, and WC115-R026 as explicit delivery requirements, not assumptions.
2. Map every canonical DMA capability and skill to the six accepted domain-adapter operations.
3. Define the DMA manifest and induction content without modifying the generic WC-115 schemas.
4. Define plan validation and material-change rules for profile, maturity, content, publication,
   advertising, performance, WhatsApp, lead, lifecycle, search, location, and reputation work.
5. Define the dependency graph and isolation behavior needed to continue safe unrelated skills.
6. Define separate customer-outcome and DMA-performance assessments using the evidence and maturity
   rules in this component.
7. Include DMA plus at least two other professional fixtures in generic conformance tests so a
   DMA-specific platform contract cannot pass unnoticed.
8. Preserve default-off, no-activation, no-deployment, and no-customer-traffic boundaries until
   separately authorized after agent-specific qualification.

## 20. Receiving Solution Architect Review And Required Packaging

### 20.1 Baseline To Reconcile Before Contract Authoring

The Solution Architect must begin from this exact baseline and resolve any status-record difference
without widening authority:

| Baseline item | Current evidence | Solution treatment |
|---|---|---|
| Generic Conversational Employment | WC-115 qualification PASS; candidate disabled by default; activation, deployment, and customer traffic unauthorized | Reuse as-is; do not redesign or activate |
| DMA Release 1 | `professionalVersion: 1.0.0`, specification revision `3.1`, exact-seven code and image qualification for Skills 0/1/2; commit `b546ca0c` is confirmed on `origin/main` | Treat as the only current DMA execution baseline; verify the exact admitted digest before binding |
| DMA employment semantics | WC115-R024, R025, and R026 remain Founder-reserved | Include in the first agent-specific solution package |
| Provider and cloud use | No provider login, cloud mutation, deployment, DNS, production, or customer traffic authority follows from the existing qualification | Keep prohibited unless a later package receives exact separate authority |
| Status records | Git confirms WC-089 exact-seven merge commit `b546ca0c` on `origin/main`, consistent with `SPRINT-REGISTRY.md`; `PROJECT_STATE.md` still states that PR review and merge remain | Use the merged technical baseline; require correction of the owning institutional status record before claiming institutional closure |

### 20.2 WC-115 Phase Mapping

The solution must map the DMA journey to the three existing phases. It must not create a fourth
platform phase.

| WC-115 phase | DMA meaning | Required outputs | Exit condition |
|---|---|---|---|
| `INDUCTION` | Understand the customer, selected outcomes, mode, authority, required inputs, connections, dependencies, and current marketing position | Confirmed profile; requirement states; connection/readiness facts; preliminary or complete maturity assessment; deferred items | Mandatory induction requirements confirmed; deferred items are explicit; no unresolved mandatory blocker |
| `PLANNING` | Convert goals and maturity evidence into selected capabilities, priorities, milestones, calendar, budget boundaries, approvals, measures, and dependency-aware work | Versioned DMA plan; content/campaign strategy where selected; performance measures; material-change rules; customer review projection | Exact plan version accepted with applicable confirmation, commercial eligibility, Decision Space, and readiness |
| `OPERATIONS` | Run admitted work, monitor evidence, reconcile side effects, report outcomes, request correction, and improve the plan | Work/outcome projections; performance assessment; attention items; corrective proposals; reassessment and successor-plan inputs | Work is completed, paused, reassessment-required, corrected, superseded, or relationship-closed through existing states |

Trial and hire are modes within these phases, not additional phases.

### 20.3 Existing Command Mapping

The Solution Architect must map every DMA customer decision to the existing WC-115 command family.
No DMA-specific public command may be introduced unless the generic protocol is separately amended.

| Existing command | DMA use |
|---|---|
| `CONFIRM_INDUCTION_ITEM` | Confirm a customer fact, required input, connection result, authority choice, or induction requirement |
| `DEFER_INDUCTION_ITEM` | Defer an optional or safely isolatable requirement while naming affected skills |
| `APPLY_CANDIDATE_PATCH` | Apply a BP-validated customer correction or bounded proposal to authoritative employment state |
| `SUBMIT_PLAN_FOR_REVIEW` | Present an exact DMA plan version for customer review |
| `ACCEPT_PLAN_VERSION` | Accept one exact plan version without implicitly accepting later material changes |
| `ACKNOWLEDGE_MATERIAL_CHANGE` | Confirm a classified material change and the bounded work it relocks |
| `RESCHEDULE_WITHIN_TOLERANCE` | Adjust an agreed calendar item within declared non-material tolerance |
| `REQUEST_REASSESSMENT` | Request refreshed maturity, readiness, dependency, plan, or performance assessment |
| `ACKNOWLEDGE_CORRECTIVE_PROPOSAL` | Accept or acknowledge an evidence-based corrective proposal without fabricating successful outcomes |

The Work Contract must include a command-to-owner matrix showing required and prohibited BP, CE, WBE,
PR, AIR, and domain-adapter calls for each applicable DMA command.

### 20.4 Required Solution Packages

The DMA office must not be delivered as one monolithic implementation Work Contract.

| Package | Bounded outcome | Included scope | Explicit exclusions |
|---|---|---|---|
| **A — DMA employment conformance** | The platform can qualify an induction, planning, trial, and hire journey for the currently qualified DMA Release 1 capabilities through WC-115 | Canonical catalogue cleanup; manifest; induction; plan/material-change validation; dependency isolation; outcome/performance meanings; Skills 0/1/2; maturity report; trial/hire projection; generic conformance | External publication, provider mutation, advertising spend, lead contact, protocol activation, deployment, and customer traffic |
| **B1 — Content production** | DMA creates customer-input-driven Instagram/Facebook drafts and an approval-ready calendar | Content creation, asset rights, tags, channel rendering, review, correction, cost/evidence | External publication and paid boosting |
| **B2 — Social publication and measurement** | Authorized content is published and its supported outcomes are observed | Scoped provider connection, publication, receipts, reconciliation, rollback/correction where supported, channel analytics, improvement loop | Paid advertising and autonomous crisis response |
| **C — Paid demand and lead conversion** | Approved campaigns generate and safely progress suitable enquiries | Paid media, budget/spend controls, first-party audience gates, lead capture/qualification/routing/nurture/handoff, conversion measurement | Unsupported consent, autonomous consequential commitments, or guaranteed results |
| **D — Search, lifecycle, and operating scale** | DMA improves discoverability, retention, multi-location consistency, and evidence-based strategy | Local SEO, GEO/AEO, email/lifecycle, multi-location, reputation, periodic strategy review | Provider choices or new authority boundaries without ADR/Founder decision |
| **E — Institutional and advanced capabilities** | Separately governed institutional self-marketing and advanced optimization operate without entering customer catalogues incorrectly | Institutional-only Skill 14, advanced creative optimization, mature multi-client operations | Any reuse of customer authority, data, budget, or credentials |

The first detailed implementation Work Contract produced from this component must be **Package A
only**. Later packages require their own solution closure, dependencies, authority, Work Contract,
qualification, and activation decision.

### 20.5 Package A Definition Of Done

Package A is solution-complete only when:

1. The canonical DMA skill taxonomy and duplicate-removal migration are closed.
2. The exact current DMA image digest, professional version, specification revision, manifest
   version/digest, adapter version, and protocol version form one compatibility tuple.
3. WC115-R024, R025, and R026 have complete DMA contracts and executable acceptance criteria.
4. Skills 0/1/2 map to induction, planning, operations, all six domain-adapter operations, and the
   applicable existing command variants.
5. The customer can see trial/hire mode, selected outcomes, required/deferred inputs, maturity result,
   plan version, readiness, limitations, and next action in customer language.
6. Maturity assessment follows the ten dimensions, evidence acquisition, equal-weight calculation,
   coverage threshold, confidence, correction, and versioning rules in Section 5.
7. Ready and deferred work demonstrate bounded isolation; `UNKNOWN`, stale, incompatible, and missing
   evidence fail closed.
8. Customer outcome and DMA performance remain distinct and evidence-based.
9. DMA, Trading, and Tutor fixtures pass the unchanged generic contracts, including mixed-major and
   missing-manifest negative cases.
10. Stop, rollback, idempotency, reconciliation, tenant/relationship isolation, customer-safe errors,
    accessibility, and generated-client ownership inherit and pass the WC-115 gates.
11. The candidate remains disabled by default and no deployment, activation, provider access, or
    customer traffic is performed.
12. All DMA-specific source is contained under `src/digital-marketing-agent/**`; any source change
    outside that subtree is proven to be thin, profession-neutral WC-115 registration or integration
    wiring with no DMA business rule or state.

### 20.6 Required Solution Artifacts

The receiving Solution Architect must produce or update only the owning artifacts needed for the
selected package:

| Artifact | Required content |
|---|---|
| DMA solution contract | Package scope, owners, interactions, state transitions, failures, rollback, acceptance mapping, and the mandatory `src/digital-marketing-agent/**` source boundary |
| DMA manifest definition | Exact values and references for the accepted generic manifest schema |
| DMA induction contract | Requirement identities, mandatory/optional classification, evidence, readiness, deferral, and correction |
| DMA planning contract | Goal/milestone/work types, calendar constraints, material-change rules, measures, and plan-validation semantics |
| DMA operations contract | Operating cycles, work types, reassessment triggers, degradation, outcome, and performance interpretation |
| Capability/skill trace | Enterprise capability → stable skill ID/version → WC-115 phase → command → adapter operation → owner → evidence → test |
| Interaction sequences | Successful, partial, blocked, stale, unknown, correction, reassessment, Stop, and rollback paths |
| Data and authority map | Record owner, tenant/relationship key, retention class, credential boundary, authority source, and customer projection |
| Compatibility and rollout plan | Version tuple, conformance fixtures, default-off gate, qualification order, shadow/read-only evidence where applicable, rollback, and separate activation decision |
| Implementation Work Contract | Atomic tasks, exact inputs/outputs, generated-client ownership, Docker validation, stops, and no unresolved design decisions |

### 20.7 Version Coordination

The solution must keep these identities separate and bind them explicitly:

| Identity | Meaning |
|---|---|
| DMA product release | Founder-governed product release sequence |
| `professionalVersion` | Immutable admitted DMA behavior version, currently `1.0.0` |
| Specification revision | Human-readable DMA requirements revision, currently `3.1` |
| Manifest version and digest | Exact employment capability and semantics presented to WC-115 |
| Skill ID and skill version | Stable capability identity and independently compatible behavior version |
| Adapter version | Domain-adapter contract implementation version |
| WC-115 protocol version | Generic Conversational Employment compatibility version |
| OCI digest | Exact executable image identity |
| Source commit and evidence digest | Build, conformance, qualification, and traceability identity |

No tag, display label, specification revision, or compatibility PASS may substitute for another
identity or silently advance an existing customer relationship.
