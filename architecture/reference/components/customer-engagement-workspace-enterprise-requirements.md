# Customer Engagement Workspace - Enterprise Requirements

| Field | Value |
|---|---|
| Authoring office | Chief Enterprise Architect (INST-004) |
| Authority | Founder instruction in the 2026-10-13 working session |
| Status | AUTHOR REVIEW PASS - CANDIDATE FOR FOUNDER REVIEW AND CHIEF SOLUTION ARCHITECT HANDOFF |
| Purpose | Convert the WC-113 through WC-120 API and agent foundations into one engaging customer experience across the Customer Portal and WhatsApp |
| Delivery type | Enterprise requirements and architecture fitness contract; no implementation |
| Controlling foundations | WC-113 through WC-120; Agent Employment Experience Contract; Omnichannel Continuity Contract; Customer Portal Solution Contract; Conversation Core; Hybrid Application Shell |
| Capability basis | 1.1-1.8, 2.1-2.7, 4.1-4.6, 5.1-5.5, 6.1-6.6, 9.1-9.2, 11.1-11.10 |
| Claim basis | C-001, C-002, C-003, C-005, C-007, C-009-C-011, C-023, C-026, C-030, C-034, C-036-C-039, C-041-C-044, C-048-C-049, C-052, C-057, C-059, C-063, C-079, C-088, C-094 |
| Driver and principle basis | AD-007-013, AD-015, AD-025; DP-003-012, DP-025 |
| Decision basis | ADR-023, ADR-035, ADR-051, ADR-052, ADR-053 as accepted and recorded by WC-120 |

## 1. Executive Requirement

WAOOAW shall present one continuous customer employment experience through two first-class channels:

1. a pane-based Customer Portal workbench; and
2. a WhatsApp conversational application.

The customer may use either channel or both according to convenience. The channels shall not create
separate products, relationships, conversations, lifecycle state, plans, commands, progress truth,
authority, billing, evidence, or outcome interpretation.

Conversation is the primary interaction and authoring path. Structured visual surfaces explain,
summarize, compare, govern, and confirm the authoritative result of the conversation. They do not
replace the conversation with a field-entry application.

The experience shall help the customer achieve business outcomes with a Digital Professional. It
shall not expose the customer to the internal API, service, schema, workflow, agent, prompt, provider,
or evidence architecture required to deliver those outcomes.

## 2. Problem Statement

WC-113 through WC-120 establish substantial reusable foundations:

- one Employment Relationship and durable conversation;
- a generic conversational employment protocol;
- reusable workspace, phase, readiness, plan, command, outcome, and reconciliation APIs;
- generated-client-only web integration through Business Platform;
- DMA employment, content, publication, demand, search, lifecycle, and performance semantics;
- account-switch recovery;
- channel-neutral conversation, WhatsApp transport, continuity, identity, delivery, media, and Stop;
- explicit truth for pending, partial, stale, blocked, unavailable, unknown, failed, and completed
  states.

The remaining enterprise gap is coherent customer composition. The contracts describe many APIs and
domain behaviors, but they do not yet provide a single, detailed experience requirement that tells
Solution Architecture how the customer moves conversationally from discovery and identity through
trial or hire, induction, goals, operations, and performance while seeing the right visual context at
the right time.

Without this component, downstream delivery can drift into one or more of these failure modes:

- a portal made of unrelated forms and dashboards;
- a WhatsApp bot with reduced or divergent business semantics;
- separate lifecycle journeys for portal and WhatsApp;
- API-shaped navigation and technical vocabulary;
- static dashboards that do not follow the active conversation;
- progress inferred by the browser rather than projected by owners;
- a DMA-specific experience that cannot serve another professional;
- environment-specific feature forks that invalidate immutable-image promotion; or
- visual polish without business-outcome clarity, constitutional control, or accessibility.

## 3. Existing Contract Disposition

| Work Contract | Reusable foundation | Experience requirement carried forward | Gap closed by this component |
|---|---|---|---|
| WC-113 | Three conversational employment phases; authoritative visual reflection; owner, blocker, evidence, and next action | Conversation remains primary from grooming through performance | Define one adaptive customer workspace composition across all phases |
| WC-114 | Versioned BP workspace, phase, readiness, plan, command, AIR proposal, WBE eligibility, and adapter contracts | UI consumes owner truth and closed states | Define how those projections become customer-understandable panes and conversational conclusions |
| WC-115 | Generated BP client, structured cards, truth states, product vocabulary, accessibility, persistent Stop | Web cannot call private owners or infer success | Define the complete portal workbench and lifecycle navigation |
| WC-116 | DMA induction, plan validation, dependency isolation, maturity, performance, Web/WhatsApp reuse | DMA provides domain meaning behind generic APIs | Define how agent-specific meaning appears without creating a DMA-specific shell |
| WC-117 | Draft, calendar, review, approval, publication, measurement, improvement, Web/WhatsApp reuse | Organic content work remains governed through common commands | Define engaging work visualization and conversational decision moments |
| WC-118 | Paid demand, leads, search, lifecycle, reputation, experiments, business outcomes, Web/WhatsApp reuse | Complex operations remain owner- and evidence-backed | Define scalable progress, action, cost, risk, and outcome presentation |
| WC-119 | Stale-session recovery, logout, account switch, safe re-entry | Identity transitions preserve truthful state | Include conversational login, registration, logout, and account-switch journeys without weakening identity boundaries |
| WC-120 | Channel-neutral conversation, WhatsApp adapter, continuity, product copy, accessibility, voice, delivery, media, Stop | WhatsApp is a full channel over shared semantics | Define channel parity, brand continuity, lifecycle completeness, and no reduced WhatsApp product |

### 3.1 Bridge closure matrix

The following seams are controlling requirements, not details for implementation to invent:

| Seam | Existing boundary | Required bridge closure | Prohibited shortcut |
|---|---|---|---|
| Anonymous discovery to professional conversation | Public marketplace has no authenticated relationship preload; Conversation Core is relationship-scoped; Public Concierge remains deferred | Anonymous web discovery uses browse, disclosure, and a conversation-shaped guided presentation over published marketplace facts only. A durable professional conversation starts only after an owner-confirmed `DISCOVERED` relationship exists. The guide is not Conversation Core, does not invoke a professional, and retains no protected transcript. | Creating a shadow relationship, public professional chat, or durable anonymous transcript |
| Trial/Hire intent to `DISCOVERED` relationship | The shell preserves professional reference, version, intent, and safe return, but records that the canonical BP admission command is missing | Solution Architecture shall define one additive, idempotent BP admission command that validates the exact disclosure and intent, creates or replays the one `DISCOVERED` relationship required by AEEC-01, and returns the canonical conversation/workspace resume target. Until that contract exists, no client may fabricate a relationship or evaluation ID. | Calling an internal admission endpoint, inventing an ID in the client, or treating registration as admission |
| Web identity inside a conversational journey | Web/Keycloak authentication uses dedicated secure pages; credentials must not enter the professional transcript | Conversation may explain the identity step before navigation and resume afterward, but web login, registration, verification, consent, logout, and provider interaction remain identity-owned screens or redirects. They shall not be simulated as professional messages or fields in the transcript. | Collecting credentials, codes, provider consent, or secrets through chat |
| WhatsApp registration before employment | WhatsApp registration is conversational, but registration does not create active employment | The registration exchange is an institutional identity conversation, not the selected professional's employment conversation. Only the minimum approved registration data persists. After owner-confirmed admission, the channel binds to the canonical relationship conversation without copying the registration transcript into professional context. | Treating phone possession or registration completion as relationship admission or authority |
| Pane and layout preferences | Identity settings own account presentation settings; Onboard owns accepted relationship visibility preferences | Account-wide layout, theme, accessibility, and default-region preferences extend the existing identity settings owner. Relationship-specific default context and visibility extend the existing Onboard preference owner. Transient width and current focus may remain client-local under privacy policy. No preference may carry owner truth. | A new preference service, protected state in local storage, or preferences that change eligibility |
| Message/card to progress-pane focus | Conversation cards can identify governed objects; routes identify views but not authority | BP projections shall provide typed, server-authorized focus references for lifecycle stage, plan item, work item, deliverable, decision, alert, result, cost signal, or governance item. Portal focus and WhatsApp continuation use the same reference and reauthorize it on every open. Focus is navigation state only. | Free-form URLs, client joins, unvalidated IDs, or focus state becoming business state |
| Portal and WhatsApp logout | Web sign-out is Keycloak/NextAuth-owned; WhatsApp uses channel identity and session continuity | Web logout performs the accepted RP/session revocation path. WhatsApp `end session` clears the bounded channel continuity/session binding and requires fresh channel verification before protected continuation; it does not log the customer out of Keycloak, unlink an identity, delete an account, or terminate employment. Account switch requires the accepted secure identity path. | Treating a WhatsApp message as global logout, unlink, account merge, or relationship termination |
| Adaptive progress aggregation | Existing BP projections own configuration, goals, outcomes, operations, alerts, billing, and relationship summaries | Solution Architecture shall reuse those projections and define the smallest BP-owned aggregate or typed composition needed for one progress pane. The browser and WhatsApp adapter shall not join owners or calculate lifecycle readiness. | Browser-side lifecycle orchestration or a dashboard truth store |
| Cross-channel continuation maturity | The continuity contract contributes semantics; WC-120 records accepted decisions and exact implementation gates | Solution Architecture shall bind every handoff to the accepted WC-120 channel-neutral API, identity/assurance profile, idempotency, source-authoritative-until-activation rule, and current gate status. This component does not independently activate an earlier pending continuity package. | Treating a deep link, delivered message, or local cursor as committed handoff |
| Default-off controls and environment parity | WC-115 through WC-120 require disabled-by-default behavior and separate activation authority | Candidate functionality, routes, schemas, and tests shall be present in the same promoted images. A shared owner-controlled capability gate may default off until authorized; it shall evaluate authority and configuration, not environment name, and shall not compile out or replace functionality in Demo. | `if Demo`, environment-specific builds, missing routes, or fake-success fallbacks |

## 4. Enterprise Architecture Decisions

### 4.1 One engagement workspace, two presentations

The logical product is the **Customer Engagement Workspace**. It is not a new deployable and does not
own business truth. It composes existing Business Platform projections around one Employment
Relationship.

| Concern | Portal presentation | WhatsApp presentation | Authoritative owner |
|---|---|---|---|
| Conversation | Persistent central conversation pane | Native chronological conversation | Business Platform Conversation Core |
| Lifecycle and progress | Adaptive progress/context pane | Compact progress summary, governed cards, and explicit continuation actions | Business Platform relationship and employment projections |
| Customer action | Inline governed card or context-pane command | Typed interactive action or secure continuation link | Existing BP command family |
| Business outcome | Visual trend, target, evidence, limitation, and narrative | Concise narrative, target delta, evidence, limitation, and optional portal deep link | BP projection of domain owner evidence |
| Authority and rights | Persistent status and Rights & control surface | Plain-language summary and explicit governed action | Relationship, CE, WBE, and identity owners |
| Emergency Stop | Persistent, immediately reachable control | Persistent typed Stop grammar and confirmation | Existing independent Stop path |

The channel changes density, layout, media, and interaction mechanics. It never changes meaning,
eligibility, authority, consequence, or outcome.

### 4.2 Conversation is the command plane

The customer expresses intent in business language. The Digital Professional:

1. understands the current relationship and lifecycle context;
2. asks only the unresolved questions needed for the next outcome;
3. gives professional advice before accepting a weak or harmful direction;
4. summarizes the inferred change in plain language;
5. requests explicit confirmation when authority, cost, contract, scope, or consequence requires it;
6. submits only an existing typed command after confirmation; and
7. presents the authoritative result, uncertainty, evidence, and next action.

Forms may supplement conversation for precise correction, comparison, accessibility, secure identity
handoff, or provider-owned credential entry. They shall not become the primary workflow for
configuration, goals, planning, Decision Space, or operational review.

### 4.3 Portal composition follows a professional workbench model

The portal shall use a tight workspace composition inspired by the productive relationship among a
development workspace, version control, and an AI collaborator: the customer remains in one working
context while conversation, current work, state, history, and next actions stay mutually visible.
This is a composition principle, not authority to copy another product's visual design or branding.

Expanded portal composition:

```text
+--------------------+--------------------------------------+-------------------------+
| Context/navigation | Conversation                         | Progress/context        |
|                    |                                      |                         |
| My Experts         | Current professional                 | Lifecycle progress      |
| Marketplace        | Continuous exchange                  | Selected object detail  |
| Needs attention    | Governed cards and conclusions       | Evidence and blockers   |
| Account/settings   | Stable composer and Stop             | Next authorized action  |
+--------------------+--------------------------------------+-------------------------+
```

The navigation, conversation, and progress/context regions are independently collapsible within
constitutional and accessibility limits. The customer may:

- hide or reveal eligible regions;
- resize the conversation and progress/context regions within tested minimum and maximum widths;
- choose a default visible context for each relationship;
- restore the default composition;
- retain preferences per account and, where useful, per relationship; and
- use the complete experience by keyboard, screen reader, touch, zoom, and reduced motion.

Emergency Stop, unresolved consequential action, active identity, and critical lifecycle status
cannot be hidden by personalization. A hidden region with new required customer action shall expose
an accessible attention indicator and one-command reveal.

Compact and mobile portal composition remains conversation-first. Secondary context opens as a
full-screen route or sheet; it is never compressed into an unusable side pane.

### 4.4 The progress/context pane is adaptive, not a static dashboard

The progress/context pane shall change its primary projection according to the active lifecycle stage,
conversation selection, and authoritative next action.

| Customer context | Primary progress projection | Required supporting truth |
|---|---|---|
| Marketplace discovery | Fit, outcomes offered, limitations, rights, price basis, trial/hire next action | Offerability, disclosure, evidence portfolio, suitability limitation |
| Login or registration | Identity step, assurance, safe continuation, recoverable failure | No relationship or paid state inferred from authentication |
| Trial or hire | Trial/hire progression, rights, contract, payment/eligibility, activation | Explicit transition boundaries and evidence status |
| Grooming and induction | Requirements completed, unresolved questions, dependencies, confirmations, blocked skills | Owner, reason, blocked effect, evidence freshness, next question |
| Goal and plan setting | Goals, milestones, calendar, Decision Space, budget, acknowledgements | Version, materiality, affected skills, acceptance state |
| Operations | Current work, proposed/approved/executing/completed items, schedule, spend, dependencies | Processing, delivery, evidence, cost, Stop, unknown outcome |
| Performance monitoring | Business target, actual outcome, trend, attribution limits, professional assessment, corrective proposal | Technical metrics only as supporting evidence |
| Pause, renewal, or exit | Consequence, retained context, billing effect, evidence/export, resumption or termination path | Explicit authority, reversibility, and immutable history |
| Marketplace without a relationship | Discovery progress and saved comparison context | No employment authority or relationship truth |

Selecting a message, plan item, deliverable, decision, alert, result, or cost signal shall focus the
pane on that object without changing the active conversation. Returning to lifecycle overview shall
be immediate and preserve the customer's position.

### 4.5 WhatsApp is a full conversational application

WhatsApp shall provide the same customer journey and professional relationship, not a notification
companion or reduced support bot.

WhatsApp shall support, through shared BP semantics:

- discovery continuation and professional selection;
- identity establishment or secure handoff where channel assurance permits;
- trial and hire initiation and explicit confirmation;
- induction and grooming;
- goal, plan, milestone, schedule, budget, and Decision Space formation;
- work review, approval, correction, cancellation, and Stop;
- operational status, blocked state, evidence, cost, and unknown-outcome reconciliation;
- performance and business-outcome review;
- pause, resume, renewal, logout/account-switch continuation, and termination initiation where the
  existing owner contract permits the action.

Where WhatsApp cannot safely complete an identity, payment, contract, assurance, provider credential,
large comparison, or rich visual task, it shall provide an authenticated, relationship-bound,
single-purpose portal continuation. The continuation shall return the customer to the same
conversation and lifecycle context. It shall not create a parallel task, duplicate command, or
generic landing-page detour.

"Same look and feel" means:

- the same WAOOAW voice, terminology, professional identity, lifecycle labels, status meanings, and
  constitutional controls;
- the same concise, consultative, outcome-focused interaction grammar;
- the same governed cards and action meanings adapted to WhatsApp-supported rendering;
- the same evidence, limitation, cost, and consequence transparency; and
- visual assets, where used, derived from the same semantic design tokens and component intent.

It does not mean forcing a three-pane layout into WhatsApp or imitating WhatsApp branding in the
portal.

## 5. End-to-End Customer Lifecycle Requirements

### 5.1 Discovery and marketplace

1. The customer may begin with a business need, not a professional type or skill name.
2. Before a relationship exists, a conversation-shaped marketplace guide may translate the need into
   published professional outcomes and explain why, but it is not a durable professional
   conversation and cannot use protected customer context.
3. Marketplace results shall show professional fit, expected outcomes, limitations, rights, price
   basis, trial availability, and evidence without implying guaranteed results.
4. The customer may compare professionals without losing the discovery conversation.
5. Selecting Trial or Hire shall create an explicit governed transition; browsing or chatting alone
   shall not create employment.
6. The durable selected-professional conversation begins only after BP returns or replays the
   canonical `DISCOVERED` relationship and resume target.

### 5.2 Login and registration

1. Login and registration shall be presented as a coherent conversational journey even when the
   identity provider owns the secure interaction.
2. The professional or WAOOAW guide shall explain why identity is required, what will happen next,
   and which context will be preserved.
3. Provider credentials, one-time codes, secrets, and provider consent shall never be collected in
   the ordinary conversation transcript.
4. Successful authentication shall resume the exact safe marketplace, trial, hire, or relationship
   context.
5. Authentication success shall not be shown as registration, trial, hire, payment, activation, or
   employment success.
6. Recoverable stale session, account switch, denial, logout, or provider failure shall preserve
   non-secret context and show one truthful next action.
7. On web, secure identity pages and redirects remain visually coherent with the workspace but are
   not simulated as professional chat. On WhatsApp, registration remains an institutional identity
   exchange until a relationship is admitted.
8. Web sign-out, WhatsApp end-session, identity unlink, account switch, relationship termination,
   and account deletion are distinct operations and shall never share one ambiguous customer action.

### 5.3 Trial and hire

1. Trial and hire shall use the same conversational employment flow with visibly different
   commercial and authority consequences.
2. Rights, limitations, price consequences, Decision Space, Stop, evidence posture, and trial
   restrictions shall be shown before commitment.
3. Contract, payment, activation, and relationship state shall remain distinct.
4. A conversation may prepare a transition but only the typed owner command and committed evidence
   may complete it.
5. Replays and cross-channel continuation shall never duplicate relationship, charge, contract
   acceptance, trial, or activation.

### 5.4 Grooming and induction

1. The professional shall lead a consultative conversation from the minimum known customer context.
2. Questions shall be progressive and relevant to selected outcomes and skills; the customer shall
   not complete a generic long form.
3. The progress pane or WhatsApp summary shall show what is known, what is missing, why it matters,
   who owns it, what it blocks, and the next question.
4. Optional deferral shall name affected skills and consequences. Mandatory gates cannot be
   overridden by convenience.
5. The customer may correct prior context through successor history without erasing the original
   evidence.
6. Active conversation burden for first-time configuration shall satisfy AD-013.

### 5.5 Goal, plan, milestone, and calendar formation

1. Goals shall be expressed in the customer's business vocabulary and traced to skills and outcome
   measures.
2. The professional shall propose a plan, explain its rationale, identify dependencies and risks,
   and distinguish recommendation from customer commitment.
3. The visual plan shall update from authoritative versions and show proposed, accepted, current,
   superseded, blocked, and reassessment-required states.
4. Material changes shall show affected work, cost, schedule, authority, and required renewed
   agreement before submission.
5. Calendar views shall preserve timezone and tolerance truth while presenting customer-native time.
6. The customer shall be able to move between conversation and plan detail without losing either
   context.

### 5.6 Operations

1. Conversation shall remain the primary place to request, discuss, review, correct, and understand
   work.
2. The progress pane shall separate proposed, awaiting customer, scheduled, executing, blocked,
   completed, failed, and unknown work.
3. Structured cards shall name outcome, owner, state, consequence, cost where applicable, evidence,
   limitation, and next action.
4. Delivery, professional processing, constitutional evidence, commercial consequence, and business
   outcome shall remain separate status dimensions.
5. An accepted request, provider receipt, model output, or HTTP response shall never be displayed as
   completed business work.
6. Emergency Stop shall remain persistent and independent in both channels and all pane states.

### 5.7 Performance and improvement

1. Results shall lead with the customer's stated business outcome and target.
2. Technical measures shall be supporting evidence and translated into domain-native meaning.
3. Performance shall show target, actual, time window, trend, evidence coverage, confidence,
   freshness, attribution limit, customer outcome, and professional interpretation.
4. Missing data shall be missing, not zero. Partial, stale, disputed, unavailable, and unknown shall
   remain distinct.
5. The Digital Professional shall explain why a result changed and propose a corrective plan rather
   than merely report metrics.
6. Customer outcome and professional performance shall remain separate.
7. Improvement proposals shall not self-authorize plan, spend, publication, contact, or authority
   change.

## 6. Conversation and Visualization Grammar

Every material customer interaction shall use one or more of these typed experience patterns:

| Pattern | Conversation behavior | Visual conclusion |
|---|---|---|
| Discover | Ask need-oriented questions and explain professional fit | Comparison or recommendation with evidence and limitations |
| Clarify | Ask one bounded unresolved question at a time | Known/missing summary and blocked effect |
| Advise | Give professional assessment before execution | Recommendation, rationale, alternatives, and risk |
| Propose | Present a versioned plan, work item, or change | Proposed card with owner, impact, cost, and next action |
| Confirm | Restate the consequential change in business language | Explicit confirm/cancel choices and evidence consequence |
| Execute | Acknowledge durable responsibility without claiming completion | Processing state and reconciliation identity |
| Reconcile | Explain uncertain, stale, or conflicting truth | Authoritative current state and safe retry/refresh action |
| Review | Compare intended and observed outcomes | Target/actual/trend/limitations and corrective proposal |
| Govern | Explain rights, authority, scope, billing, or lifecycle consequence | Current boundary, evidence, and governed commands |

Conversation conclusions shall be projectable as governed cards or progress updates. A card is a
view of owner truth, not an independent browser or channel record.

## 7. Functional Requirement Index

| ID | Requirement |
|---|---|
| CEW-ER-001 | One Employment Relationship has one durable conversation and one engagement workspace across Portal and WhatsApp. |
| CEW-ER-002 | Customer Portal and WhatsApp consume the same BP-owned public semantics and typed command families. |
| CEW-ER-003 | Conversation is the primary authoring path for discovery, configuration, goals, plans, operations, and review. |
| CEW-ER-004 | Structured forms are secondary and cannot silently commit authoritative state. |
| CEW-ER-005 | Expanded portal provides context/navigation, conversation, and adaptive progress/context regions. |
| CEW-ER-006 | Eligible regions can be hidden, displayed, and resized while Stop, identity, critical lifecycle state, and required action remain reachable. |
| CEW-ER-007 | Compact portal remains conversation-first and presents secondary context as an accessible route or sheet. |
| CEW-ER-008 | Progress/context projection changes according to lifecycle, selection, authoritative state, and next action. |
| CEW-ER-009 | Selecting visual detail never forks or replaces the continuous conversation. |
| CEW-ER-010 | WhatsApp supports the complete employment lifecycle subject to the same owner, assurance, and authority rules. |
| CEW-ER-011 | Portal continuation from WhatsApp is authenticated, single-purpose, relationship-bound, and returns to the same context. |
| CEW-ER-012 | Login, registration, logout, and account switch preserve safe non-secret context without conflating identity with employment. |
| CEW-ER-013 | Marketplace discovery starts from business needs and carries context into trial or hire. |
| CEW-ER-014 | Trial and hire remain explicit, evidenced, idempotent, and commercially distinct. |
| CEW-ER-015 | Induction shows known, missing, owner, reason, blocked effect, evidence freshness, and next question. |
| CEW-ER-016 | Goals, plan, milestones, calendar, budget, Decision Space, and material change remain versioned and conversationally explainable. |
| CEW-ER-017 | Operational views separate delivery, processing, evidence, commercial, and outcome state. |
| CEW-ER-018 | Performance leads with business outcomes and translates technical evidence into customer-domain meaning. |
| CEW-ER-019 | Every consequential interaction exposes effect, authority, cost where applicable, limitation, and safe next action before commitment. |
| CEW-ER-020 | Emergency Stop is persistent, independent, accessible, and cross-channel effective. |
| CEW-ER-021 | Multiple professionals and multiple same-type relationships remain isolated and switch as complete contexts. |
| CEW-ER-022 | Pane preferences never become business truth and are cleared or retained according to account and privacy policy. |
| CEW-ER-023 | Unsupported, stale, partial, disputed, unavailable, blocked, failed, and unknown states have distinct accessible presentation. |
| CEW-ER-024 | No customer-facing surface exposes raw service, API, enum, prompt, provider, or workflow vocabulary. |
| CEW-ER-025 | DMA-specific semantics appear through the adapter and professional vocabulary without creating a DMA-specific platform shell. |
| CEW-ER-026 | Another conforming professional can use the same workspace without new platform lifecycle states or channel branches. |
| CEW-ER-027 | Browser and channel clients never call PR, AIR, WBE, CE, adapters, or provider APIs directly. |
| CEW-ER-028 | All ordinary customer integration uses generated BP clients or approved channel adapters over the same public contract. |
| CEW-ER-029 | Conversation conclusions and visual projections reconcile to authoritative owner versions and never infer success locally. |
| CEW-ER-030 | The experience meets WCAG 2.2 AA, keyboard, screen-reader, zoom, reflow, non-color, reduced-motion, and locale requirements. |
| CEW-ER-031 | Portal and WhatsApp use the same WAOOAW terminology, professional identity, status meanings, evidence language, and outcome narrative. |
| CEW-ER-032 | The same immutable application images and API contracts promote from Demo to UAT to Production without environment-specific functional degradation or code forks. |
| CEW-ER-033 | Environment differences are limited to protected configuration, identity, endpoints, data, scale, and authorized external connections; they do not remove product behavior from the promoted image. |
| CEW-ER-034 | Provider, traffic, and activation authority remain separate from functional completeness; unavailable external authority is shown truthfully rather than implemented as an environment-specific reduced product. |
| CEW-ER-035 | Customer-visible state survives permitted navigation and channel changes without storing protected truth in the browser or channel. |
| CEW-ER-036 | Needs-attention ordering, resume target, and next action are server projected and never independently ranked by a client. |
| CEW-ER-037 | Anonymous web discovery uses published marketplace facts and non-authoritative presentation only; durable professional conversation requires an owner-confirmed relationship. |
| CEW-ER-038 | One additive idempotent BP admission command creates or replays the AEEC-01 `DISCOVERED` relationship from exact disclosure and Trial/Hire intent. |
| CEW-ER-039 | Registration completion, authentication success, or preserved intent cannot substitute for relationship admission. |
| CEW-ER-040 | Web identity interactions remain identity-owned secure pages/redirects framed by, but not embedded in, professional conversation. |
| CEW-ER-041 | WhatsApp registration is an institutional identity exchange and does not contaminate the professional transcript or grant employment authority. |
| CEW-ER-042 | Account layout preferences extend identity settings; relationship visibility/default-context preferences extend Onboard; transient focus/width remains non-authoritative. |
| CEW-ER-043 | Governed objects expose typed server-authorized focus references shared by portal selection and WhatsApp continuation. |
| CEW-ER-044 | Web logout, WhatsApp end-session, unlink, account switch, relationship termination, and account deletion have distinct language, authority, state, and evidence. |
| CEW-ER-045 | Adaptive progress uses BP-owned projections or the smallest additive BP aggregate; no client joins owners or computes readiness. |
| CEW-ER-046 | Default-off candidate controls preserve complete functionality in promoted images and evaluate owner authority/configuration rather than environment name. |

## 8. Decision Tables

### 8.1 Conversation versus structured interaction

| Situation | Primary interaction | Supporting interaction | Prohibited behavior |
|---|---|---|---|
| Discover need | Conversation | Marketplace comparison | Requiring skill or API knowledge |
| Collect induction context | Conversation | Editable summary | Generic long intake form as primary path |
| Enter credential or payment secret | Provider-owned secure surface | Conversation explains purpose and return | Secret in transcript |
| Compare complex plan versions | Conversation explains | Portal visual diff | WhatsApp silently choosing a version |
| Confirm consequential action | Plain-language confirmation | Typed confirm/cancel control | Free-text interpreted as approval without accepted grammar |
| Correct precise value | Conversation or focused editor | Versioned change preview | Local state becoming authoritative |
| Review performance | Professional narrative | Outcome visualization and evidence detail | Technical dashboard as primary experience |
| Resolve unknown outcome | Reconciliation explanation | Refresh/retry existing command | Blind retry or success assumption |

### 8.2 Channel completion

| Condition | Remain in WhatsApp | Secure portal continuation | Result |
|---|---|---|---|
| Plain-language discovery or configuration | Yes | Optional | Same conversation and workspace version |
| Typed low-risk command at sufficient assurance | Yes | Optional | Existing BP command |
| Identity provider authentication | Explain and initiate | Required provider-owned flow | Return to same safe context |
| Payment or credential entry | Explain and initiate | Required owner surface | No secret in conversation |
| Rich comparison or dense evidence | Summary remains available | Optional recommended detail | No semantic difference |
| Consequential action lacks assurance | No execution | Required reauthentication | No owner call before assurance |
| Unsupported WhatsApp rendering | Text alternative | Optional detail | No hidden action or information |
| Unknown or conflicting state | Explain uncertainty | Optional reconciliation detail | No duplicate command |

### 8.3 Environment parity

| Concern | Permitted environment difference | Prohibited environment difference |
|---|---|---|
| Application image | Immutable promoted digest | Separate Demo/UAT/Production feature builds |
| Functional contract | Same paths, schemas, states, and commands | Demo-only reduced API or UI |
| External systems | Different authorized accounts/endpoints and test data | Hard-coded environment behavior branch |
| Scale | Resource and replica configuration | Missing customer lifecycle capability |
| Activation | Separately authorized configuration and evidence | Equating inactive provider with absent product implementation |
| Customer truth | Environment-isolated data | Fake success or placeholder owner truth |

## 9. Quality Attributes and Fitness Contract

| Fitness ID | Measurable obligation |
|---|---|
| CEW-FIT-01 | Portal and WhatsApp replay the same lifecycle scenario against one relationship and produce equivalent owner state and evidence. |
| CEW-FIT-02 | Discovery-to-trial and discovery-to-hire journeys complete conversationally without requiring technical vocabulary or a primary long form. |
| CEW-FIT-03 | First-time induction, goal, schedule, budget, and Decision Space configuration completes within AD-013 active-conversation limits. |
| CEW-FIT-04 | Changing channel during any lifecycle stage preserves relationship, conversation, lifecycle, plan, message, command, and evidence identities. |
| CEW-FIT-05 | Login, registration, logout, stale-session recovery, and account switch return to the exact safe context with no duplicate account or relationship. |
| CEW-FIT-06 | Pane hide/show/resize/restore passes keyboard, screen-reader, 200% zoom, 360px reflow, RTL, and focus restoration tests. |
| CEW-FIT-07 | Stop remains visible or directly invocable in every portal composition and supported WhatsApp state. |
| CEW-FIT-08 | Each lifecycle stage projects the required progress fields with no browser- or channel-inferred eligibility or completion. |
| CEW-FIT-09 | Delivery, processing, evidence, commercial, and outcome states remain independently testable and visually distinguishable. |
| CEW-FIT-10 | Every consequential action shows effect, authority, cost where applicable, limitation, and explicit confirm/cancel before owner submission. |
| CEW-FIT-11 | Unknown, stale, partial, blocked, unavailable, and disputed fixtures never render as empty or successful state. |
| CEW-FIT-12 | Performance fixtures lead with business outcome and can render technical metrics only as supporting evidence. |
| CEW-FIT-13 | DMA Packages A-E fit the same shell and command grammar without platform fields or branches specific to DMA. |
| CEW-FIT-14 | A non-DMA professional fixture uses the same shell, lifecycle, progress model, and channel contract without code-path specialization in shared owners. |
| CEW-FIT-15 | Client network inspection contains only generated BP public operations, approved identity handoffs, and the independent Stop path. |
| CEW-FIT-16 | No provider credential, secret, token, protected payload, or full telephone identity appears in transcript, URL, telemetry, browser persistence, evidence, or screenshots. |
| CEW-FIT-17 | The same exact application image passes the complete functional journey suite under Demo-, UAT-, and Production-shaped configuration. |
| CEW-FIT-18 | Environment-shaped qualification shows no missing route, component, command, schema, or lifecycle behavior; external calls use authorized emulators or accounts without changing application code. |
| CEW-FIT-19 | Portal-to-WhatsApp-to-portal race, retry, timeout, and replay tests produce one logical command and one authoritative conclusion. |
| CEW-FIT-20 | Customer copy meets the accepted readability, domain-vocabulary, accessibility, and one-primary-action-per-turn controls. |
| CEW-FIT-21 | Anonymous discovery produces zero relationship, conversation, account, membership, trial, contract, payment, or authority writes before the explicit admission command. |
| CEW-FIT-22 | Trial/Hire intent survives identity continuation and the admission command creates or replays exactly one `DISCOVERED` relationship and resume target under duplicate, timeout, and cross-channel replay. |
| CEW-FIT-23 | Web credential/provider flows write no secret or consent payload to conversation history; WhatsApp registration data is absent from professional context except explicitly confirmed minimum profile facts. |
| CEW-FIT-24 | Web logout, WhatsApp end-session, account switch, unlink, termination, and deletion fixtures produce distinct owner calls and cannot trigger one another. |
| CEW-FIT-25 | Pane selection and WhatsApp continuation resolve the same typed focus reference, deny stale or inaccessible references without enumeration, and never mutate owner state by navigation alone. |
| CEW-FIT-26 | Default-off and enabled qualification on the same exact image proves identical route/schema availability across environment-shaped configuration, with authority gates producing truthful blocked states rather than missing functionality. |

## 10. API and Ownership Requirements for Solution Architecture

The Chief Solution Architect shall begin with reuse, not endpoint invention.

1. Map every experience requirement to existing BP operations from WC-084, WC-114/WC-115,
   Conversation Core, relationship workspace, identity, billing, and WC-120.
2. Map every WhatsApp action to the same operation and command family used by the portal.
3. Use `submitEmploymentCommand` for accepted employment commands rather than create lifecycle- or
   DMA-specific public commands.
4. Use owner-projected workspace, phase, readiness, plan, business outcome, operations, alerts,
   billing, marketplace, and relationship summaries.
5. Treat missing visual composition data as a BP projection gap, not permission for browser joins.
6. Add an API only when no accepted operation can express the required owner truth. Any additive API
   shall remain BP-owned, channel-neutral, closed, versioned, generated-client-compatible, and
   traceable to a CEW-ER requirement.
7. Do not introduce a Customer Portal backend, WhatsApp business-logic service, dashboard store,
   client-side workflow engine, or parallel conversation/profile owner.
8. Keep preference state separate from employment, plan, outcome, authority, evidence, and billing
   truth.

## 11. No-Drift Constraints

The downstream solution and implementation packages shall not:

- turn the portal into a collection of API-shaped forms;
- make WhatsApp a notification-only or reduced-lifecycle channel;
- create separate portal and WhatsApp business rules;
- create a second conversation, workspace, plan, progress, or outcome store;
- use channel possession as identity, membership, assurance, or authority;
- infer readiness, completion, eligibility, evidence, or business success in a client;
- expose internal enum codes or technical marketing metrics as primary customer language;
- hide Stop, required customer action, authority, or material limitation through personalization;
- treat Demo as a functionally degraded product or maintain environment-specific feature code;
- claim external-provider readiness, deployment, traffic, or acceptance from functional completeness;
- specialize shared platform UI or APIs for DMA; or
- require implementation teams to invent product copy, owner, transition, error, state, or acceptance
  behavior.

## 12. Required Chief Solution Architect Handoff

The Chief Solution Architect shall produce one versioned solution package that includes:

1. a complete experience-to-owner/API reuse matrix for CEW-ER-001 through CEW-ER-046;
2. portal shell and adaptive progress-pane state machines;
3. WhatsApp interaction grammar and secure continuation sequences for every lifecycle stage;
4. login, registration, logout, stale-session, account-switch, trial, hire, induction, goal, plan,
   operations, performance, pause, resume, renewal, and termination sequences;
5. pane preference, layout, focus, breakpoint, accessibility, persistence, and privacy contracts;
6. governed-card and conversation-conclusion schemas that reuse owner truth;
7. exact generated-client and adapter ownership with no private-owner client exposure;
8. error, stale, partial, blocked, unavailable, unknown, conflict, and reconciliation behavior;
9. environment-parity, immutable-image promotion, configuration, and qualification requirements;
10. a Product/UX acceptance matrix with business-outcome, vocabulary, visualization, responsive,
    accessibility, and cross-channel parity oracles;
11. direct executable oracles for CEW-FIT-01 through CEW-FIT-26;
12. dependency order and bounded Work Contracts for Platform IT Expert implementation; and
13. explicit gaps that require Founder policy or a new ADR, without silently choosing them.

The package is complete only when Platform IT Expert can implement it without inventing an API,
owner, lifecycle, workflow, environment exception, UI state, copy rule, channel rule, or test oracle.

### 12.1 Recommended bounded delivery sequence

The Chief Solution Architect shall determine exact Work Contract identifiers and may refine grouping,
but shall preserve these dependencies and demonstrable vertical outcomes:

| Order | Bounded work component | Required outcome | Depends on |
|---:|---|---|---|
| 1 | Reuse and gap closure | CEW-ER/API/owner matrix; DISCOVERED-admission command; focus reference; adaptive-progress composition; additive BP gaps only; shared state and error model frozen | This enterprise component |
| 2 | Shared engagement shell | Portal regions, pane preferences, responsive composition, relationship switching, Stop, focus, privacy, and generated-client boundary | 1 |
| 3 | Conversational acquisition and identity | Marketplace discovery, login, registration, logout, stale-session recovery, account switch, and exact safe resume | 1-2 |
| 4 | Conversational trial and hire | Disclosure, trial/hire distinction, contract, payment continuation, activation truth, replay, and evidence | 1-3 |
| 5 | Induction and planning | Grooming, known/missing progress, goals, Decision Space, milestones, calendar, material change, and plan acceptance | 1-4 |
| 6 | Operations and performance | Work states, approvals, deliverables, cost, evidence, business outcomes, corrective proposals, pause/resume, renewal, and exit | 1-5 |
| 7 | WhatsApp lifecycle parity | WhatsApp interaction grammar and secure continuations for Components 3-6 over the same owner contracts | 1 and the applicable vertical component |
| 8 | Cross-channel and environment qualification | Portal/WhatsApp races, continuity, exact-image Demo/UAT/Production-shaped qualification, recovery, accessibility, and CEW-FIT closure | 2-7 |

Each component shall end in a customer-observable vertical journey, not an infrastructure-only or
API-only milestone. Shared contracts are frozen before their consumers, but implementation evidence
must prove the customer experience that consumes them.

## 13. Assumptions, Boundaries, and Stops

### Bound assumptions

- Existing accepted APIs and owner contracts remain the source of truth.
- WC-120 records acceptance of ADR-051, ADR-052, and ADR-053 for its bounded scope.
- Portal and WhatsApp may differ in information density and rendering but not in semantics.
- Same-image promotion requires feature completeness in the image; activation and external authority
  remain independent controls.

### Boundaries

- This component defines enterprise requirements, not wire schemas, component implementation, visual
  mockups, provider selection, source changes, deployment, or activation.
- It does not amend constitutional lifecycle states or create a new platform capability owner.
- It does not claim that existing implementation already satisfies these requirements.
- Direct `src/` inspection was not performed because the occupied Enterprise Architect office
  prohibits reading implementation source. The evidence basis is the approved Work Contracts,
  architecture contracts, API ownership records, and acceptance specifications.

### Stops for downstream work

Stop and return to Enterprise Architecture or the Founder if:

- a requirement needs a new business capability or owner;
- channel parity requires divergent business semantics;
- a client would need to infer authoritative progress or eligibility;
- an environment-specific code fork is proposed;
- a new deployable or technology selection is required without an ADR;
- WhatsApp assurance cannot support a consequential action and no secure continuation exists;
- personalization could hide a constitutional control or required customer action; or
- the Solution Architect cannot map a requirement to an owner, API, state, error, and executable
  oracle.

## 14. Definition of Done

This Enterprise Architecture component is complete when:

- WC-113 through WC-120 are traced into one coherent customer experience;
- Portal and WhatsApp are defined as two presentations of one engagement workspace;
- complete conversational login, registration, logout, trial, hire, lifecycle, operations, and
  performance requirements are explicit;
- the adaptive, hideable, displayable, and resizable portal pane model is bounded;
- WhatsApp parity and secure portal continuation are explicit;
- business-outcome-first visualization and consultative professional behavior are explicit;
- environment functional parity and immutable-image promotion are explicit;
- API reuse and prohibited duplication are explicit;
- every requirement has a stable CEW-ER identifier;
- every quality obligation has a measurable CEW-FIT predicate;
- the Chief Solution Architect handoff is sufficient to create bounded implementation Work Contracts
  without product or architecture invention; and
- author review against the Founder instruction, approved capabilities, drivers, principles, Work
  Contracts, owner boundaries, failure modes, security, accessibility, operability, and reversibility
  is PASS.

## 15. Author Review

**Status:** PASS - 2026-10-13

The Chief Enterprise Architect re-read the complete component against the Founder instruction,
WC-113 through WC-120, the approved capability map, architectural drivers, design principles, Agent
Employment Experience Contract, Omnichannel Continuity Contract, Customer Portal Solution Contract,
Conversation Core, Hybrid Application Shell, and the Enterprise Architect quality gate.

Review lenses:

- requirement and lifecycle coverage;
- channel parity and continuity;
- conversation-primary interaction;
- business-outcome and professional-vocabulary primacy;
- owner, API, authority, evidence, and state boundaries;
- identity, trial, hire, Stop, failure, replay, and reconciliation;
- adaptive visualization, personalization, responsive behavior, and accessibility;
- DMA specialization without platform contamination;
- immutable-image environment parity;
- security, privacy, operability, reversibility, and measurable fitness; and
- downstream decomposability without Solution Architect or implementer invention.

Findings and repairs:

1. The first authored version required the Chief Solution Architect to create bounded Work Contracts
   but did not provide a dependency-safe vertical sequence. Section 12.1 now defines eight bounded
   work components from reuse closure through exact-image cross-channel qualification while leaving
   identifiers and detailed decomposition inside Solution Architecture authority.
2. The Founder requested source-code analysis, but direct `src/` reading conflicts with the occupied
   Enterprise Architect office boundary. Section 13 records this limitation and binds conclusions to
   approved Work Contracts, architecture, API ownership, and acceptance evidence rather than
   implying source verification.
3. Environment parity could have been misread as deployment or provider authority. CEW-ER-032
   through CEW-ER-034 and Decision Table 8.3 now distinguish functional completeness in promoted
   images from separately governed activation, external connection, traffic, and environment data.
4. "Same look and feel" could have been interpreted as forcing a portal layout into WhatsApp.
   Section 4.5 defines semantic, brand, vocabulary, control, and outcome parity while permitting
   channel-native density and rendering.
5. The first pass allowed conversational discovery to be read as a public professional conversation,
   conflicting with the relationship-scoped Conversation Core and deferred Public Concierge.
   Section 3.1 and CEW-ER-037 now keep anonymous discovery non-authoritative and begin the durable
   professional conversation only after `DISCOVERED` admission.
6. The preserved Trial/Hire intent had no canonical bridge into AEEC-01 relationship creation.
   CEW-ER-038/039 and CEW-FIT-22 now require one additive idempotent BP admission command and prohibit
   registration, authentication, or client-generated identifiers from substituting for admission.
7. "Conversational login and logout" could have weakened identity ownership or merged distinct
   operations. CEW-ER-040/041/044 and CEW-FIT-23/24 now separate web secure identity pages, WhatsApp
   institutional registration, web RP logout, WhatsApp end-session, unlink, switch, termination, and
   deletion.
8. Pane personalization and selected-object focus lacked explicit owners and could have produced a
   client-side truth store. CEW-ER-042/043/045 and CEW-FIT-25 now bind preferences to existing
   identity/Onboard owners, focus to typed BP-authorized references, and progress composition to BP.
9. Default-off controls could have been misused to preserve environment-specific functional
   degradation. CEW-ER-046 and CEW-FIT-26 now require the complete capability in the same image and
   restrict gates to owner authority/configuration rather than environment-name branches.

No unresolved author finding remains. The component creates no deployable, wire schema, provider
choice, source change, environment mutation, activation, or implementation authority.
