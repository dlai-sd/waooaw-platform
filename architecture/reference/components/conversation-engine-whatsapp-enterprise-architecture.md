# Conversation Engine And WhatsApp Enterprise Architecture

**Status:** PROPOSED - Founder review required
**Date:** 2026-10-12
**Office:** Chief Enterprise Architect (INST-004)
**Authorization:** Founder-authorized bounded architecture assignment, 2026-10-12
**Decision package:** ADR-052 and ADR-053
**Extends:** ADR-023, ADR-051, Conversation Core, Omnichannel Continuity, WC-062 Voice
**Does not authorize:** implementation, source changes, provider activation, credentials, deployment,
DNS mutation, customer traffic, expenditure, Production activation, PR approval, or merge

## 1. Purpose And Required Outcome

This package defines the enterprise architecture for one governed, channel-neutral professional
conversation across web, WhatsApp, and a future mobile application. It is the controlling input for
the Chief Solution Architect to produce implementable component, API, data, security, deployment,
and test contracts without inventing a boundary, owner, state, failure behavior, or quality target.

The architecture must support:

1. one durable professional conversation per Employment Relationship;
2. continuity when a customer moves between web, WhatsApp, and future mobile;
3. semantic context switching based on the customer's current journey, function, subject, and
   authoritative relationship state rather than on an untrusted screen prompt;
4. consultative, appreciative, engaged, evidence-seeking professional communication that progresses
   toward an explicit conclusion;
5. a more curious and investigative style during induction and grooming, including authorized
   research and data analysis before asking the customer for information already available;
6. reusable public conversation contracts through Business Platform;
7. WhatsApp text, interactive response, status, template, media, and voice handling;
8. distinct Demo, UAT, and Production WhatsApp identities and Azure ingress boundaries; and
9. deterministic security, privacy, evidence, replay, delivery, recovery, and observability rules.

## 2. Scope

### 2.1 Included

- Enterprise capability, context, container, ownership, trust, and deployment views.
- Interaction Context and Conversation Policy concepts.
- Cross-channel history, checkpoint, ordering, delivery, and reconciliation semantics.
- Web, WhatsApp, and future-mobile reuse boundaries.
- WhatsApp webhook verification, signed ingress, message normalization, outbound dispatch, delivery
  status, media retrieval, voice contribution, service-window, and template responsibilities.
- Phone identity, web/mobile identity, relationship resolution, assurance, and step-up boundaries.
- Demo/UAT/Production number and environment isolation.
- Security and privacy threats, data classes, retention ownership, failure modes, observability,
  reversibility, and measurable fitness obligations.
- Exact handoff requirements for Solution, Data, Security, Platform, AI, Product, Runtime, and Test.

### 2.2 Excluded

- Endpoint paths, physical schemas, classes, packages, Terraform resources, workflow YAML, prompt
  text, provider credentials, certificates, secrets, and implementation code.
- Purchasing or registering the Production number.
- Activating a Meta app, WABA, phone number, template, callback, provider token, DNS record, Azure
  resource, or customer traffic.
- Replacing the Employment Relationship, Conversation Core, Conversational Employment Workspace,
  Phone Identity Service, Professional Runtime, AI Runtime, Constitutional Engine, or WBE.
- A mobile framework decision. ADR-032 remains reserved and mobile implementation remains deferred.
- Cross-agent memory sharing outside an explicit, governed relationship or authorized shared context.

## 3. Source Obligations And Traceability

| Obligation | Source | Architectural response |
|---|---|---|
| Natural-language configuration remains a universal path | C-039; Capability 1.7; AD-013 | Conversation Core remains the single public conversational authority under BP |
| Customer context is learned before active work | Capability 1.5 | Induction/grooming Context Profile with fact, inference, research, confirmation, and freshness lineage |
| Context follows the customer across interfaces | Founder requirement; ADR-051; WC-060 | One relationship conversation, separate channel sessions, signed continuity checkpoints |
| Screen/function changes alter relevant context safely | Founder requirement; C-003; C-030 | Server-resolved Interaction Context; clients supply bounded hints, never authority or prompt text |
| Conversation is consultative and reaches a conclusion | Founder requirement; DP-011; C-037; C-049 | Versioned Conversation Policy with dialogue acts and explicit conclusion protocol |
| Grooming is curious and research-led | Founder requirement; Capability 1.5; C-002; C-050 | Research-before-question rule and typed unknown/inference/confirmed states |
| All channels reuse one API and history | Founder requirement; ADR-002; ADR-051 | BP remains the only ordinary public facade; generated clients consume the same contracts |
| WhatsApp supports low-literacy and voice-first journeys | C-042; AD-015; ADR-023 | WhatsApp adapter normalizes text/media/audio into governed conversation contributions |
| Tenant context cannot be supplied by message payload | AD-004; ADR-003; C-063 | Identity-derived tenant and relationship resolution; normalized inaccessible response |
| Consequential actions require current authority | C-003; C-023; C-041 | Conversation proposes; BP/CE/WBE/PR authoritative owners validate and commit |
| Failure never becomes optimistic success | C-023; C-049; ADR-031 | Independent acceptance, dispatch, delivery, read, execution, and evidence states |
| Environment trust cannot cross boundaries | ADR-014; ADR-046; FA-052 pattern | Separate number binding, app authority, secret set, state, storage, telemetry, and ingress per environment |

## 4. Existing Baseline And Reconciliation

The Solution Architect must preserve these delivered foundations:

- Conversation Core: BP owns durable timeline, message identity, ordering, unread state, public
  commands, idempotency, canonical projection, and SSE; PR owns professional execution.
- Omnichannel Continuity: multiple channel conversations resolve one Employment Relationship while
  retaining separate delivery/session state; handoff reauthenticates and preserves authority.
- Browser Voice: BP owns the public voice contribution state; PR orchestrates; AIR performs
  provider-neutral transcription; explicit correction and send consent precede consequential use.
- ADR-023 Phone Identity: Meta-signed phone identity may establish low-risk WhatsApp participation;
  stronger actions require confirmation, step-up, or portal-only completion.
- ADR-051 Conversational Employment Workspace: one relationship, one durable professional
  conversation, one authoritative BP workspace; conversation proposes and authoritative owners commit.

Any older record that describes F3, F5, or F6 implementation as blocked is historical to that
contract's creation. Delivery records show those implementation scopes were merged. This package
does not claim that Meta provider activation, live credentials, callback configuration, deployment,
or real-number customer proof has occurred.

## 5. Enterprise Architecture Decisions

### EA-CE-01 - One Relationship Conversation

Each Employment Relationship has exactly one durable professional conversation and one canonical
message sequence. Channel changes create or resume channel sessions; they do not create a second
professional memory, Decision Space, plan, or employment relationship.

### EA-CE-02 - Business Platform Is The Public Conversation Facade

Web, WhatsApp, and future mobile access conversation capability only through BP-owned public
contracts or provider callback boundaries. No channel calls PR, AIR, CE, WBE, an LLM provider, object
storage, or an MCP server directly.

### EA-CE-03 - Context Is Server-Resolved

The effective Interaction Context is derived from authenticated identity, relationship, professional,
journey phase, current subject, pending intent, authoritative state versions, channel capability,
locale, and an optional bounded client hint. A route, screen, button, webhook text, model output, or
client-supplied context label cannot grant authority or override server truth.

### EA-CE-04 - Style Is A Versioned Policy

Conversation style is composed from institutional, professional, interaction, customer, locale, and
channel policy layers. Frontends and channel adapters do not contain independent tone prompts.

### EA-CE-05 - History And Working Context Are Distinct

The canonical history is durable and complete subject to retention rights. Working model context is a
bounded, versioned, attributable projection assembled for one execution. Summaries, retrieved facts,
and inferred context never replace or rewrite the canonical timeline.

### EA-CE-06 - Channel Delivery Is Independent From Professional Outcome

Provider acceptance, transport delivery, participant observation, professional execution, and
constitutional evidence are separate state dimensions. No timeout, HTTP success, provider receipt,
or read receipt implies a completed professional outcome.

### EA-CE-07 - WhatsApp Is An Adapter, Not A Parallel Engine

The WhatsApp boundary verifies Meta, resolves phone identity, normalizes provider events, and
dispatches outbound representations. It does not own customer truth, conversation history,
professional reasoning, authority, billing, or lifecycle state.

### EA-CE-08 - Environments Are Independently Trusted

Demo, UAT, and Production use distinct WhatsApp numbers, app/WABA bindings, callback hostnames,
secrets, provider identifiers, deduplication state, media storage, conversation data, telemetry,
deployment authority, and evidence scope. No runtime fallback crosses environments.

### EA-CE-09 - Existing Containers Are Sufficient

No new deployable Conversation Engine service is justified. The capability is a composition of
existing BP, PR, AIR, Phone Identity, CE, WBE, relational storage, payload storage, channel clients,
and Meta. A later Solution design may identify an independently scalable adapter only by returning
to Enterprise Architecture with measured evidence and a C-095 decision.

### EA-CE-10 - Decision Acceptance Is Ordered

ADR-052 depends on acceptance of ADR-051 or an explicit simultaneous Founder decision that accepts
both without changing ADR-051's one-relationship/one-conversation ownership. ADR-053 may establish
environment isolation independently, but its channel-neutral context, history, and voice semantics
depend on accepted ADR-052. No downstream implementation may treat a proposed ADR as accepted merely
because its contract is detailed or included in a PR.

## 6. Context View

```text
Customer
  | web HTTPS/SSE/WSS
  | future mobile HTTPS/SSE/WSS
  | WhatsApp text/interactive/media/audio
  v
+--------------------------- WAOOAW Platform ----------------------------+
| Web/Mobile Client -> Business Platform Conversation/Workspace facade    |
| Meta Webhooks ----> BP WhatsApp boundary -> Phone Identity Service      |
|                                      |                                  |
|                                      v                                  |
|                         canonical relationship conversation             |
|                                      |                                  |
|                         Professional Runtime -> AI Runtime               |
|                                      |                                  |
|                Constitutional Engine / WBE / domain owners               |
+-------------------------------------------------------------------------+
                   ^                           |
                   | signed events             | outbound messages/media
                   +-------- Meta Cloud API ----+
```

External actors are the customer, Meta WhatsApp Cloud API, web/mobile identity provider, and approved
research/tool providers. Meta is a transport and identity-assertion source, not a constitutional
authority.

## 7. Logical Component And Ownership View

| Structural role | Existing owner | Owns | Must not own |
|---|---|---|---|
| Public Conversation Facade | Business Platform | Public commands, history, cursors, context projection, policy references, channel-neutral outcomes | Model dispatch, provider credentials, constitutional decisions |
| Interaction Context Resolver | Business Platform composition | Effective context selection from authoritative state and bounded hints | Free-form prompt acceptance, tenant override |
| Conversation Policy Resolver | Business Platform + AI Runtime contract | Exact policy version and applicable layers | Customer truth, authority, arbitrary model tone |
| Professional Execution | Professional Runtime | Execution identity, ordering, cancellation, Stop, typed events | Public ingress, relationship authorization |
| Context Assembly And Reasoning | AI Runtime | Bounded execution context, retrieval, analysis, provider-neutral inference | Durable conversation truth, final authority |
| WhatsApp Ingress/Egress Adapter | BP boundary | Challenge response, signature validation, normalization, outbound dispatch, provider status projection | Relationship truth, reasoning, billing |
| Phone Identity | Phone Identity Service | Minimized phone proof, replay/dedup support, tenant-scoped internal assertion | Keycloak session, relationship takeover |
| Voice Orchestration | BP/PR/AIR existing boundary | Media state, scanning handoff, transcription, correction, accepted-text handoff | Implicit send consent |
| Constitutional Governance | Constitutional Engine | ValidateAction, Evidence First, Stop evidence | Conversation presentation |
| Commercial Governance | WBE | Usage, budget, allowance, billing consequence | Conversation history |
| Durable Conversation Store | BP relational/payload boundaries | Canonical metadata, ordered messages, policy/context refs, channel receipts | Immutable constitutional evidence |
| Channel Clients | Web, WhatsApp, future mobile | Presentation, local drafts, accessibility, transport-specific controls | Durable authority, independent history |

## 8. Interaction Context Model

### 8.1 Required Concept

The Solution Architect must define a versioned `InteractionContext` contract with at least:

```text
InteractionContext
  context_id
  schema_version
  relationship_id
  professional_instance_id
  conversation_id
  phase
  purpose
  subject_type
  subject_reference
  pending_intent_reference?
  decision_space_version
  plan_version?
  profile_version?
  policy_version
  locale
  channel
  assurance_level
  source_versions[]
  freshness
  resolved_at
```

Tenant identity, participant authority, provider credential, raw phone number, system prompt, and
secret material are never client-writeable fields.

### 8.2 Context Vocabulary

The first solution contract must support, without agent-specific renaming:

| Phase | Purposes |
|---|---|
| Discovery | `PROFESSIONAL_DISCOVERY`, `OFFERING_EXPLANATION`, `TRIAL_EXPLORATION` |
| Induction | `IDENTITY_CONFIRMATION`, `CUSTOMER_ONBOARDING`, `CUSTOMER_GROOMING`, `CONTEXT_CONFIRMATION` |
| Planning | `GOAL_FORMATION`, `PLAN_FORMATION`, `MILESTONE_REVIEW`, `CALENDAR_REVIEW`, `DECISION_SPACE_CONFIGURATION` |
| Operations | `WORK_REVIEW`, `ACTION_APPROVAL`, `ISSUE_RESOLUTION`, `DELIVERABLE_REVIEW`, `PERFORMANCE_REVIEW` |
| Governance | `RIGHTS_EXPLANATION`, `EVIDENCE_REVIEW`, `EMERGENCY_STOP`, `AUTHORITY_CHANGE` |
| Commercial | `USAGE_REVIEW`, `BILLING_EXPLANATION`, `PLAN_CHANGE` |
| Closure | `SUSPENSION`, `TERMINATION`, `EXPORT`, `FINAL_SUMMARY` |

Agent-specific capabilities may refine `subject_type`; they may not redefine phase, authority, or
universal purpose semantics.

### 8.3 Resolution Precedence

Effective context is resolved in this order:

1. active Emergency Stop or constitutional halt;
2. authenticated tenant, participant, role, and relationship access;
3. pending consequential intent requiring confirmation, reconciliation, or step-up;
4. explicit customer selection validated against an available BP command;
5. current relationship/workspace phase and selected subject;
6. latest committed channel continuity checkpoint;
7. classified customer message intent;
8. bounded route/screen hint; and
9. safe relationship-home default.

Lower-precedence evidence cannot override a higher-precedence state. Ambiguity presents a concise
choice or asks one clarifying question; it never guesses a consequential context.

### 8.4 Screen And Function Switching

Web and future mobile send a registered `surface_context_key` and opaque `subject_reference`. BP
validates both against the authenticated route, available commands, relationship, and source version.
The mapping is centrally versioned and exposed through generated contracts. A client cannot send
prompt text or arbitrary policy identifiers.

WhatsApp derives context from current continuity checkpoint, pending intent, message classification,
and explicit commands. A message that appears to change subject while a consequential confirmation is
pending must resolve or cancel the pending intent before switching.

### 8.5 Context Lifecycle

```text
RESOLVED -> ACTIVE -> CHECKPOINTED -> SUPERSEDED
    |          |
    |          +-> STALE_REASSESSMENT_REQUIRED
    +-> AMBIGUOUS
    +-> BLOCKED
```

Every professional execution binds the exact context and policy versions used. Material relationship,
plan, Decision Space, identity, or authority changes stale affected contexts and prevent silent reuse.

### 8.6 Trusted Context Assembly

Every assembled segment carries provenance, sensitivity, tenant, relationship, source identity,
source version, freshness, and permitted-use metadata. Institutional instructions and accepted
policy are structurally separated from untrusted content. Customer messages, provider metadata,
media, transcripts, quoted history, retrieved research, tool/MCP output, derived summaries, and
agent-produced text are always untrusted data, even when previously stored by WAOOAW.

Instruction-like text in an untrusted segment cannot populate policy or authority fields. Every
model-proposed tool call, command, context change, or customer-state patch is independently
authorized against the current Interaction Context, source versions, Decision Space, participant
assurance, and registered operation contract. Indirect prompt injection, quoted-policy imitation,
cross-segment contamination, and malicious retrieved content are required adversarial cases.

## 9. Conversation Policy And Style

### 9.1 Policy Composition

```text
Institutional Policy
  + Professional Persona Policy
  + Interaction Purpose Policy
  + Customer Communication Profile
  + Domain Vocabulary Policy
  + Locale/Accessibility Policy
  + Channel Rendering Policy
  = Effective Conversation Policy (versioned)
```

Conflicts resolve toward constitutional safety, truthful limitation, customer rights, professional
domain rules, and then presentation preference. A channel policy may shorten or split content but
cannot weaken disclosure, consent, authority, or evidence.

### 9.2 Universal Professional Style

Every customer-facing response must:

- acknowledge the customer's contribution specifically, without repetitive praise or manipulation;
- demonstrate relevant understanding before requesting more information;
- communicate as a consultative expert, not a form or generic chatbot;
- use the customer's business and occupational vocabulary;
- distinguish known fact, research finding, inference, recommendation, and required decision;
- be forthcoming about uncertainty, limitation, cost, delay, or unavailable evidence;
- recommend a next action with reasons;
- avoid jargon, raw internal identifiers, model/provider language, and fabricated confidence; and
- progress toward an explicit conclusion rather than prolonging conversation for engagement.

### 9.3 Induction And Grooming Style

During `CUSTOMER_ONBOARDING`, `CUSTOMER_GROOMING`, and `CONTEXT_CONFIRMATION`, the professional must:

1. state what is already known and avoid asking for it again;
2. conduct authorized research and available-data analysis before asking the customer;
3. identify the smallest material knowledge gap;
4. ask one primary question per turn unless safety requires a grouped confirmation;
5. explain why a sensitive or high-effort question matters;
6. record research as sourced and time-bounded, inference as unconfirmed, and customer confirmation
   as attributable fact;
7. summarize accumulated understanding at meaningful checkpoints;
8. invite correction without making the customer re-enter unaffected information; and
9. conclude grooming with confirmed context, unresolved/deferred items, derived recommendation,
   evidence/limitations, and the next governed decision.

Curiosity is measured by improved understanding and decision quality, not by question count.

### 9.4 Dialogue Acts

Solution contracts must type at least:

`ACKNOWLEDGE`, `INFORM`, `ASK`, `CONFIRM_INFERENCE`, `PRESENT_RESEARCH`,
`PRESENT_RECOMMENDATION`, `PRESENT_OPTIONS`, `REQUEST_DECISION`, `WARN`,
`DISCLOSE_LIMITATION`, `SUMMARIZE`, `CONCLUDE`, `ESCALATE`, and `HANDOFF`.

Each response declares one primary dialogue act and may include bounded supporting acts. A
consequential `REQUEST_DECISION` must use the authoritative command contract rather than treating
free text as sufficient unless the exact risk tier explicitly permits text confirmation.

### 9.5 Conclusion Protocol

At the end of a material interaction, the professional presents:

1. `understanding` - concise confirmed situation;
2. `analysis` - relevant evidence and reasoning summary, without hidden chain-of-thought;
3. `recommendation` - best outcome and why;
4. `customer_decision` - what, if anything, requires explicit confirmation;
5. `next_action` - owner, timing meaning, and blocked effect;
6. `open_items` - unknown, deferred, unavailable, or disputed matters; and
7. `evidence_state` - recorded, pending, not applicable, or unavailable.

The channel may render this as text, cards, interactive replies, or audio, but the semantics remain
identical.

### 9.6 Prohibited Style Behavior

- Generic praise on every turn.
- Pretending an inference is a fact.
- Asking the customer for data already held and current.
- Hiding a failure behind a friendly response.
- Continuing discovery after the minimum sufficient context is confirmed.
- Urgency, scarcity, or upgrade pressure unrelated to customer risk.
- Different recommendations solely because the customer changed channels.
- Letting a model invent authority, readiness, price, evidence, or completion.

## 10. Customer Understanding And Memory

### 10.1 Context Profile

Each relationship maintains a governed projection with:

- customer-confirmed facts;
- externally researched facts with source, capture time, and expiry;
- analytical findings with method/version;
- unconfirmed inferences with confidence and basis;
- corrections and supersession lineage;
- goals, priorities, constraints, exclusions, and preferences;
- communication profile and locale;
- unresolved material questions;
- current domain maturity or readiness assessment; and
- references to source messages and authoritative owner records.

### 10.2 Memory Tiers

| Tier | Content | Use |
|---|---|---|
| Canonical history | Durable ordered customer/professional messages and typed cards | Customer continuity, audit, replay |
| Authoritative relationship state | Contract, Decision Space, plan, goals, authority, billing, evidence refs | Deterministic gating and presentation |
| Context profile | Confirmed/researched/inferred customer understanding | Relevance and grooming |
| Execution working set | Bounded retrieved excerpts and current task inputs | One professional execution |
| Derived summary | Versioned, attributable compression of older history | Cost/latency control; never source-of-truth replacement |

Cross-customer context is prohibited. Cross-agent context is prohibited unless an explicit
relationship-level authorization identifies purpose, fields, recipient, expiry, and evidence.

### 10.3 Simultaneous Channels

BP assigns canonical sequence after durable acceptance. Concurrent web/mobile/WhatsApp submissions
may both be accepted if they are independent. Conflicting commands use source-version checks and
return an explicit conflict. Pending consequential intent is unique per protected subject and cannot
be completed twice from two channels.

## 11. Channel-Neutral Contract Families

The Solution Architect must define generator-compatible contracts for:

1. read canonical timeline and current context;
2. submit text or reviewed voice contribution;
3. submit a typed customer command;
4. retry/reconcile an unresolved contribution;
5. advance read/observed position;
6. stream or poll canonical events;
7. request cancellation without deleting history;
8. prepare, authenticate, activate, or revert channel handoff;
9. inspect and correct Context Profile material;
10. obtain the available surface contexts and commands;
11. inspect delivery, execution, and evidence state independently; and
12. export or request erasure according to data classification.

Every mutation binds actor, relationship, operation, idempotency key, canonical payload digest,
expected source version where applicable, context version, correlation, and current authority.

## 12. WhatsApp Transport Architecture

### 12.1 Inbound Verification

The public HTTPS callback supports:

- Meta GET challenge verification using a protected environment-specific verify token;
- POST signature validation over exact raw bytes using `X-Hub-Signature-256`;
- fail-closed behavior before JSON interpretation when signature validation fails;
- provider event schema/version validation;
- timestamp/freshness policy and durable provider-event deduplication;
- normalized handling of inbound messages and delivery-status notifications; and
- a bounded callback response within the approved current provider contract, independent from
  asynchronous professional execution.

Source IP is not an authentication factor. A static WAOOAW ingress IP does not replace signature,
replay, schema, or deduplication controls.

GET challenge verification echoes `hub.challenge` only when the request uses the exact expected
subscribe mode, the supplied token matches the environment-bound verify-token version in
constant-time, and the callback host resolves to the same environment binding. All other inputs
receive a non-reflective denial.

POST verification parses the declared signature algorithm, permits only the approved HMAC-SHA256
form, computes over the exact bounded raw request bytes before decompression, normalization, parsing,
or middleware transformation, and compares in constant-time. Oversized bodies are rejected before
buffer amplification. Responses never reflect signatures, tokens, payloads, phone proofs, provider
identifiers, or parser errors.

The inbound event state machine is:

```text
RECEIVED -> VERIFIED -> CLAIMED -> DURABLY_ACCEPTED -> OUTCOME_RECORDED
                 |          |              |
                 v          v              v
              REJECTED   CONFLICT       RECONCILING
```

The compound provider-event identity is environment + provider app/WABA authority + recipient
phone-number ID + provider event/message/status ID. Claim, canonical payload digest, normalized typed
acceptance or durable typed rejection, and inbox/outbox handoff are one BP-owned consistency
boundary. Concurrent first delivery has one winner; same identity/same digest replays the durable
result; same identity/different digest is a conflict with zero additional mutation.

Success is returned to Meta only after `DURABLY_ACCEPTED`, `OUTCOME_RECORDED`, or retrieval of the
same previously durable result. Before that point the adapter returns the approved retryable provider
failure. A previously unseen event is fresh only when its provider timestamp is within ADR-023's
inclusive five-minute skew of trusted server receipt time. Freshness never discards an authentic
retry already found in durable deduplication merely because the original provider timestamp is old.
Deduplication retention is policy-owned and cannot be shorter than provider retry, WAOOAW
reconciliation, security replay, backup/restore, or unresolved-attempt horizons.

### 12.2 Inbound Message Normalization

Supported provider inputs are normalized into a channel-neutral envelope:

```text
provider_event_id
provider_phone_number_id
participant_phone_proof
message_type
text_or_interactive_value?
media_reference?
provider_timestamp
reply_to_reference?
provider_context_reference?
integrity_result
environment_binding
```

Raw phone numbers are minimized and protected under the Phone Identity contract. Provider tokens and
download URLs never enter the public envelope or durable conversation timeline.

### 12.3 Outbound Dispatch

An outbound WhatsApp representation is created only from a canonical BP message or typed command
outcome. Dispatch binds environment, approved phone-number ID, recipient proof, service-window state,
template identity/version/locale where required, message payload digest, correlation, and idempotency.

The provider adapter records:

`QUEUED`, `SUBMITTED`, `PROVIDER_ACCEPTED`, `DELIVERED`, `READ`, `FAILED`, `EXPIRED`, or `UNKNOWN`.

These are delivery states only. `READ` is not customer approval, professional completion, or
constitutional evidence.

### 12.4 Service Window, Consent, And Templates

- Customer-initiated conversation establishes the applicable Meta service window but does not grant
  unlimited purpose or indefinite marketing consent.
- Outside the service window, only an approved, exact-version, localized template may be dispatched.
- WAOOAW opt-in evidence and purpose must remain valid independently of provider acceptance.
- Template category, language, variable schema, approval status, and environment binding are
  versioned configuration, never free-form runtime input.
- A rejected, paused, unapproved, or mismatched template fails closed with a customer-safe unresolved
  outcome and an operator-visible reason code.

The service window opens only from a qualifying, verified and durably accepted inbound customer
message type under the current provider contract. BP receipt time from the trusted server clock is
the enforcement anchor; provider time remains provenance and freshness evidence. The exact inclusive
boundary follows the approved provider contract and is tested at both sides of the boundary.
Window, opt-in, opt-out, purpose, recipient, template approval/version/locale/schema, and relationship
state are validated both when queued and immediately before provider submission. Opt-out, consent
revocation, relationship termination, Stop, template revocation, or environment deactivation
invalidates queued work immediately. A state change between queue and submission produces a typed
non-dispatched outcome and reconciliation evidence, never fallback to another template or channel.

### 12.5 Media And Voice

Inbound media uses the provider media ID to obtain a short-lived authenticated retrieval URL
server-side. The URL and token are never exposed to a client or stored as durable conversation text.
The media path must:

1. authorize environment and phone-number binding;
2. retrieve within provider validity;
3. treat filename, extension and declared MIME as untrusted; verify content signature and sniffed
   type against a deny-by-default approved format policy;
4. enforce compressed and expanded size, decompression ratio, page/frame/duration, parser CPU,
   memory, recursion and timeout ceilings;
5. deny active content, archives, polyglots and parser-capable formats unless the exact format is
   separately approved;
6. quarantine and scan through an isolated scanner identity before interpretation;
7. record immutable scanner engine/signature/policy versions and verdict lineage;
8. keep timeout, scanner error, unknown format and inconclusive verdict in quarantine;
9. store payload only in the approved erasable boundary;
10. preserve immutable evidence metadata separately;
11. route audio through the existing provider-neutral voice orchestration;
12. require transcript review/correction when confidence or policy requires it;
13. prohibit silence, transcription, or upload completion from implying send consent; and
14. render the accepted contribution into the same canonical conversation sequence.

Only the isolated scanner workload may move a payload from quarantine to clean state, and it has no
conversation, provider-dispatch, PR, AIR, CE, WBE, or cross-environment authority. Rejected payload
retention, deletion, legal hold, and customer-visible explanation follow the lifecycle matrix in
Section 15; media activation remains blocked until the Section 24 owner decision is recorded.

For WhatsApp audio, an explicit customer send already occurred at the provider channel, but
consequential interpretation may still require a confirmation turn when transcription confidence,
risk tier, or detected ambiguity requires it.

### 12.6 Interactive And Risk-Tier Semantics

- Tier 1: routine conversation and informational requests under phone identity.
- Tier 2: explicit typed or interactive confirmation bound to the exact summarized intent.
- Tier 3: current stronger-factor step-up; absence or failure routes to portal.
- Tier 4: portal-only, including Stop release and other critical changes.

Changing channels never upgrades assurance. A web login may establish a stronger target-channel
session only through the existing continuity activation and evidence path.

### 12.7 Deterministic Phone Resolution And Assurance

The signed event first resolves the environment, provider app/WABA authority, and recipient
phone-number ID. Only then may Phone Identity derive a protected participant proof from the signed
sender. Resolution evaluates active channel binding, tenant membership, relationship role, number
reassignment/revocation state, assurance and freshness.

| Resolution cardinality/state | Required result |
|---|---|
| Exactly one active binding with current membership and matching environment/recipient | Continue under that tenant and relationship |
| No binding but valid first-contact admission policy | Start only a new evaluation/admission flow; never attach an existing relationship |
| Zero without valid first-contact admission | Normalized unavailable response; zero tenant or relationship mutation |
| Multiple, conflicting or ambiguous bindings | Normalized unavailable response; security event; zero mutation |
| Inactive, revoked, reassigned, expired or stale binding | Normalized unavailable/step-up response; zero protected mutation |
| App/WABA, recipient phone-number ID or environment mismatch | Deny and alert; no fallback |

Provider IDs, phone references, payload hints and message text never independently select tenant or
relationship data. First-contact admission requires the verified event, bound recipient/environment,
current admission policy and opt-in evidence; phone possession alone is insufficient.

| Tier | Operation families | Required assurance and freshness |
|---|---|---|
| 1 | Information, routine grooming, non-consequential support | Current verified phone binding and active membership/session; no authority expansion |
| 2 | Exact plan/brief/seasonal or other medium commitment | Tier 1 plus explicit confirmation bound to intent digest, subject, source version and expiry |
| 3 | Financial/significant authority-bearing commitment | Fresh stronger-factor step-up bound to one intent; invalidated on completion, change, expiry, Stop or session loss |
| 4 | Contract creation/change, Stop release, payment/bank change, deletion and other critical actions | Fresh portal authentication and exact authoritative command; never WhatsApp completion |

The solution security contribution may further restrict an operation but cannot lower these floors.
Step-up freshness can never exceed the underlying authenticated session and is rechecked at commit.
Number reassignment, participant revocation, membership loss, relationship change, or environment
change invalidates all derived WhatsApp assurance.

### 12.8 WhatsApp Emergency Stop

An explicit typed WhatsApp Stop command is recognized after signature and binding verification but
before context classification, model execution, ordinary professional queuing, billing, or outbound
work. It latches idempotently to the resolved Employment Relationship and invokes the existing Stop
orchestrator. It does not depend on free-text model interpretation.

During CE unavailability, the adapter follows ADR-031: execute the local halt, append the protected
relationship-scoped Stop event to the bounded local evidence buffer, acknowledge that the halt is
active and evidence synchronization is pending, flush idempotently after CE recovery, and never
auto-release. Duplicate delivery, adapter restart, simultaneous channel Stop, timeout, reconnect, or
operator action cannot create a second Stop or release the latch.

Conversational uses of "stop" that are not the explicit typed Stop command trigger a safe
clarification with the explicit Stop control immediately available. Ambiguity never suppresses the
control and never silently converts unrelated text into a release. Release remains Tier 4 portal-only.

## 13. Environment And Deployment Topology

### 13.1 Number Allocation

| Environment | Binding decision | Repository-safe identifier |
|---|---|---|
| Demo | Dedicated number selected by Founder; short-lived application deployment | Display-number suffix `3575` |
| UAT | Dedicated number selected by Founder; stable Azure ingress | Display-number suffix `2344` |
| Production | Separate number to be purchased; preferred keypad suffix for `WAOOAW` is `926629` | `PENDING_FOUNDER_PURCHASE` |

The exact E.164 number, Meta phone-number ID, WABA ID, app ID, verification token, and access
authority are protected environment configuration. Exact phone values and credentials must not be
hard-coded in source, workflow, images, logs, or architecture tests.

### 13.2 Ingress And DNS

Each environment exposes a distinct HTTPS hostname:

```text
whatsapp-demo.<approved-domain>
whatsapp-uat.<approved-domain>
whatsapp.<approved-domain>
```

The Azure environment has a stable ingress address for its lifetime. DNS binds the approved hostname
to the environment ingress, and the callback uses the hostname, not a raw IP, so TLS identity and
controlled migration remain possible. UAT retains a stable Azure ingress and DNS binding. Demo may
create and remove its app revision and callback routing, but reuse of the Demo number never permits
reuse of UAT or Production credentials/state.

`deploy.yaml` may render and verify an already authorized environment binding. It must not purchase a
number, create provider authority, rotate a protected secret, mutate Production DNS, register a live
callback, or activate customer traffic without the matching Founder authority.

### 13.3 Egress

Stable outbound egress is required only when an approved external dependency requires allow-listing.
It is not inferred from the static inbound requirement. If required, Platform Architecture must
provide an environment-specific egress address without merging ingress and egress trust.

### 13.4 Isolation Matrix

| Asset | Demo | UAT | Production |
|---|---|---|---|
| Phone number and phone-number ID | Dedicated | Dedicated | Dedicated |
| Meta app/WABA authority | Environment-bound | Environment-bound | Environment-bound |
| Callback hostname/certificate | Demo | UAT | Production |
| Verify token/app secret/access authority | Separate | Separate | Separate |
| Key Vault secret names and workload access | Separate | Separate | Separate |
| Deduplication/replay namespace | Separate | Separate | Separate |
| Conversation, context, and media data | Separate | Separate | Separate |
| Telemetry and alert routing | Separate | Separate | Separate |
| Template approval binding | Demo/test | UAT qualification | Production-approved |
| Deployment authority | Ephemeral authorized apply | Fixed authorized apply | Dark until separately authorized |

### 13.5 Demo Cleanup

Demo teardown must disable callback delivery or route it to an explicit unavailable response before
removing the active revision; revoke temporary provider authority; expire temporary media; clear
erasable payload and deduplication state under approved retention; preserve required privacy-safe
deployment/evidence records; and prove that UAT/Production bindings were untouched.

Cleanup is prohibited while any provider retry, unresolved inbound event, outbound attempt,
reconciliation, legal hold, erasure propagation, or retained deduplication/tombstone horizon remains
capable of causing work. An authorized cleanup either reaches a proven terminal/reconciled state or
retains an isolated non-routable recovery boundary until the horizon closes.

### 13.6 Provider Workload And Secret Authority

Logical workload identities are environment-specific:

```text
spiffe://waooaw.<environment>/workload/business-platform/whatsapp-adapter
spiffe://waooaw.<environment>/workload/business-platform/whatsapp-media-scanner
spiffe://waooaw.<environment>/deployment/whatsapp-configurator
```

The runtime audience is `urn:waooaw:service:whatsapp-adapter:<environment>`. Deployment/configuration
authority has a distinct audience and cannot invoke conversation or provider-message operations.

| Protected authority | Runtime adapter | Media scanner | Deployment/configurator |
|---|---|---|---|
| Callback verify token compare | Read current/overlap version | None | Rotate/revoke reference |
| Webhook HMAC app secret | Read current/overlap version | None | Rotate/revoke reference |
| Outbound message authority | JIT read/use for exact environment/audience | None | Provision/rotate/revoke reference |
| Media retrieval authority | JIT read/use for exact environment/media operation | None | Provision/rotate/revoke reference |
| Quarantine read / clean promotion | None | Exact object only; promote verdict | Configure policy, no payload read |
| Callback/provider configuration | Read own immutable binding | None | Prepare/apply only under separate authority |
| DNS/TLS/Azure deployment | None | None | Prepare/apply only under separate authority |

Managed workload identity and Key Vault policy enforce the matrix. A catch-all provider credential is
prohibited. Secrets remain in process memory only for the shorter of operation need, credential
validity, cache policy, or approved rotation overlap; they never propagate to PR, AIR, CE, WBE,
clients, logs, traces, dead letters, or persisted conversation data. Access, rotation, revocation,
denial and configuration changes are audited with privacy-safe references.

Unknown, unavailable, wrong-workload, wrong-audience, wrong-environment, expired, revoked,
superseded, leaked or version-mismatched authority fails closed. Rotation permits only the bounded
provider-supported overlap of current and immediately previous authorized versions. Emergency
revocation terminates new dispatch/retrieval and reconciles in-flight work without credential
fallback. Rollback may restore non-secret configuration but can never restore or reactivate a
revoked, expired, leaked, wrong-environment or superseded credential.

## 14. Security Architecture

### 14.1 Trust Boundaries

1. Meta public webhook to BP public adapter.
2. Browser/mobile authenticated session to BP public API.
3. BP to Phone Identity, PR, CE, WBE, and storage.
4. PR to AIR.
5. BP/provider adapter to Meta Graph API and media retrieval.
6. Environment deployment authority to Azure, DNS, Key Vault, and Meta configuration.

### 14.2 Threats And Required Outcomes

| Threat | Required control and outcome |
|---|---|
| Forged webhook | Exact raw-body HMAC validation; reject before parsing; no mutation |
| Replay/duplicate | Freshness check plus durable provider-event ID; replay prior outcome |
| Phone takeover | Phone possession cannot attach an existing relationship; fresh higher assurance required |
| Cross-tenant reference | Identity-derived tenant and normalized inaccessible response; zero disclosure |
| Context injection | Registered context keys and server resolution; free-form prompt/context rejected |
| Pending-intent confusion | Bind confirmation to intent digest, subject, source version, and expiry |
| Channel downgrade | Reduced capability, never reduced protection |
| Media abuse | Type/size gate, quarantine, scan, timeout, no processing before clean verdict |
| Provider URL/token leakage | Server-only retrieval; redacted telemetry; no durable signed URL |
| Template substitution | Exact approved template/version/locale/variables binding |
| Delivery spoofing | Provider status correlated to exact outbound message and environment |
| Cross-environment credential use | Audience/environment binding and separate secret authority; fail closed |
| Prompt injection in customer/media content | Treat all content as untrusted data; policy/context cannot be overwritten |
| Model-generated authority | Typed proposals only; authoritative owners validate and commit |
| Stop bypass | Stop takes precedence across contexts/channels; ordinary reconnect cannot release |
| Excessive conversation extraction | Rate, abuse, export, and privacy policy; no hidden system/policy disclosure |

### 14.3 Privacy

- Minimize raw phone number persistence; use protected proof and authorized display only where needed.
- Keep message/media payload separate from immutable evidence metadata.
- Prohibit content, phone, media URL, transcript, tenant, or provider token in URL, analytics, or
  unapproved logs.
- Support access, correction, export, erasure, retention, legal hold, and evidence-separation rights.
- Research ingestion records purpose, source, freshness, and permitted use.
- Conversation summaries inherit the highest sensitivity of their source material.

Ordinary logs, metrics, traces, baggage, exception responses, request capture, dead-letter
diagnostics and scanner diagnostics must not contain payloads, headers, signatures, phone proofs,
tenant/relationship identifiers, provider references, prompts, transcripts, message/media metadata,
template variables, context facts, or secret material. High-cardinality customer/provider labels
are prohibited.

A separately authorized protected diagnostic/evidence path may retain the minimum encrypted payload
needed for a named purpose. It requires explicit RBAC, purpose, access evidence, retention/deletion
class, legal-hold behavior, environment boundary and export prohibition. Sampling cannot turn
prohibited data into permitted telemetry. Automated leakage tests cover successful and exceptional
paths, framework errors, retry queues, dead letters, scanner failures and trace propagation.

## 15. Data Architecture Obligations

### 15.1 Normative Logical Data Boundary

| Record | System of record / durable boundary | Mandatory binding | Write authority | Consistency and handoff | Lifecycle / recovery owner |
|---|---|---|---|---|---|
| Canonical Conversation | BP relational relationship boundary | environment, tenant, relationship, conversation | BP relationship service | One per relationship; root for sequence and channel projections | BP/Data |
| Conversation Message | BP relational metadata + opaque payload-store reference | environment, tenant, relationship, conversation, sequence | BP conversation service | Idempotency reservation, sequence allocation, append and outbox are one transaction | BP/Data |
| Channel Session/Binding | BP relational identity boundary | environment, tenant, relationship, participant proof, channel | BP identity/continuity service | Fresh authentication and evidence before activation | BP/Data + Identity owner |
| Interaction Context | BP relational relationship boundary | environment, tenant, relationship, conversation, source versions | BP context resolver | Immutable resolved version; execution receives opaque ID/version | BP/Data |
| Conversation Policy Reference | BP relational reference; policy bytes in approved policy registry | environment, tenant/relationship scope, exact layer versions | Policy owner publishes; BP selects | Opaque immutable reference to AIR; no policy bytes from client | Policy owner + BP/Data |
| Context Observation | BP append-only relationship boundary | environment, tenant, relationship, subject, source | BP profiling/context service | Append observation, then update current projection transactionally | BP/Data |
| Current Context Profile | BP replaceable relationship projection | environment, tenant, relationship, profile version | BP profiling/context service | Derived only from retained observations | BP/Data |
| Derived Summary | Approved erasable/derived payload boundary + BP metadata | environment, tenant, relationship, explicit source set | BP/AIR derivation under typed contract | Metadata commit only after payload write; invalidation is append-only | BP/Data |
| Context Checkpoint | BP relational continuity boundary | environment, tenant, relationship, source/target channel | BP continuity service | Signed/hash-bound; prepare/activate/revert with outbox/evidence refs | BP/Data |
| Inbound Provider Event | BP transport inbox | environment, app/WABA, recipient number ID, provider event ID | BP WhatsApp adapter | Atomic claim with typed acceptance/rejection and outbox | BP/Data |
| Canonical Command Idempotency | BP relationship boundary | environment, tenant, relationship, actor, operation, key, digest | BP command owner | Atomic with protected mutation or typed rejection | BP/Data |
| Outbound Logical Message | BP conversation boundary | environment, tenant, relationship, conversation message | BP conversation/transport owner | Created from canonical message only; outbox to attempts | BP/Data |
| Outbound Delivery Attempt | BP transport boundary | environment, outbound message, attempt number, provider binding | BP WhatsApp adapter | Each retry is a new attempt; provider submission through outbox | BP/Data |
| Provider Status Observation | BP append-only transport boundary | environment, provider event ID, attempt/correlation | BP WhatsApp adapter | Idempotent append; projection recomputed by precedence contract | BP/Data |
| Media/Voice Payload | Erasable payload/quarantine boundary | environment, tenant, relationship, opaque payload ID | Retrieval/scanner/voice roles by state | Metadata uses opaque ID; no reconstructive hash outside payload boundary | Payload/Data owner |
| Transcript/Correction | Erasable voice payload boundary + BP lineage metadata | environment, tenant, relationship, contribution, version | Voice orchestration; customer correction through BP | Versioned append; accepted version alone reaches conversation | Voice/Data owner |
| Dedup/Erasure Tombstone | BP transport/relationship boundary | complete idempotency namespace; non-reconstructive digest | Owning BP operation | Retained after payload erasure for replay horizon | BP/Data |
| Evidence Reference | CE append-only evidence boundary | environment, tenant, relationship, evidence ID | CE only | Opaque reference from BP; never payload duplication | CE/Data |

Cross-boundary references are opaque identifiers or keyed non-reconstructive digests. No store
dereferences another store's internal location. Any operation that must durably accept in one
boundary and continue in another uses an inbox/outbox or equivalent atomic handoff with explicit
reconciliation. Retention duration and numeric recovery targets may be configurable; ownership,
isolation, consistency and fail-closed behavior are fixed here.

### 15.2 Canonical Ordering And Concurrency

There is one monotonically increasing sequence per canonical conversation. BP allocates it in the
same transaction as idempotency reservation, pending-intent conflict check, canonical message append,
and outbox publication. `(environment, tenant, relationship, conversation, sequence)` is unique.
Commit order is canonical order; provider/customer timestamps are provenance only. Sequence gaps are
permitted only for rolled-back reservations that are never externally visible, or represented by a
typed tombstone under the physical design; they cannot be silently reused.

Protected-subject commands serialize against the same subject/source version. Independent messages
may commit concurrently and receive the stable order chosen by the BP transaction boundary. An
ambiguous client response reconciles by the original idempotency identity and replays the committed
result; it never allocates another sequence.

### 15.3 Tenant And RLS Invariants

Every tenant-scoped row, uniqueness key, foreign-key path, cursor, payload reference, idempotency
namespace, provider correlation and outbox/inbox record includes environment and tenant, and includes
relationship where relationship resolution has occurred. Composite references enforce matching
environment/tenant/relationship. Provider IDs, phone proofs, message IDs, media IDs and environment
names never independently select tenant data.

Web derives tenant from the authenticated membership selected under ADR-003. Signed provider
callbacks first resolve environment/recipient authority, then Phone Identity supplies a protected
participant proof; BP membership/relationship resolution supplies tenant. Scheduled reconciliation,
media retrieval, transcription callbacks and recovery jobs consume a signed workload assertion bound
to exact environment, tenant, relationship, operation and object/attempt. Each DB transaction sets
and resets tenant context locally. Tenant stores use `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL
SECURITY`, composite tenant-consistent references, and non-owner `NOBYPASSRLS` runtime roles.
Unresolved or mismatched context returns normalized zero-disclosure denial.

### 15.4 Context Observation And Summary Lineage

Observations are append-only; the current Context Profile is replaceable and reproducible. Each
observation version binds environment, tenant, relationship, subject, fact type, value/payload
reference, status, accountable source, source identity/version, observed/captured/confirmed times,
valid-from/to, freshness, sensitivity, permitted use, predecessor, supersession/invalidation reason,
and evidence reference where applicable.

Allowed states are `RESEARCHED`, `INFERRED`, `CONFIRMED`, `DISPUTED`, `STALE`, `SUPERSEDED`,
`UNAVAILABLE`, and `ERASED`. Research or inference becomes confirmed only through attributable
customer confirmation or an approved authoritative source rule. Correction appends a successor and
supersedes the prior version; dispute never overwrites; expiry stales; erasure removes payload and
leaves only the permissible non-reconstructive tombstone/evidence metadata.

Each summary records the covered canonical sequence range or explicit source IDs and digests,
derivation contract/model/policy versions, produced time, sensitivity, predecessor, invalidation
reason and rebuild state. Correction, erasure, source expiry, policy/model incompatibility or
relationship change invalidates affected summaries. A summary is never the sole source of a fact.

### 15.5 Idempotency And Deduplication Domains

Separate domains exist for inbound provider events, canonical customer commands, and outbound
dispatch. Their uniqueness namespaces include:

- inbound: environment + provider app/WABA + recipient phone-number ID + provider event ID + digest;
- command: environment + tenant + relationship + actor + operation + idempotency key + digest; and
- outbound: environment + tenant + relationship + outbound logical message + attempt + digest.

Reservation is atomic with canonical acceptance or durable typed rejection. Same namespace/same
digest replays; same namespace/different digest conflicts. Retention is policy-owned and no shorter
than all applicable provider retry/reconciliation, security replay, unresolved outcome, backup/restore
and legal-hold horizons. Payload erasure retains a non-reconstructive tombstone for that horizon.
Dedup, inbox, outbox and canonical messages share a recovery consistency point. Demo cleanup cannot
remove protection while a retained attempt/event can retry.

### 15.6 Delivery Observation And Projection

Provider status is immutable observation, not a mutable truth row. Each observation binds provider
event ID, environment, attempt, provider correlation, normalized raw status, provider time, trusted
received time, payload digest and predecessor/conflict information. Duplicate observations replay.
Late, contradictory or regressive observations remain recorded.

Each retry is a distinct attempt under one outbound logical message. A deterministic projection
combines transport progress (`QUEUED`, `SUBMITTED`, `PROVIDER_ACCEPTED`, `DELIVERED`, `READ`) with
attempt disposition (`OPEN`, `FAILED`, `EXPIRED`, `CANCELLED`) and reconciliation
(`CURRENT`, `UNKNOWN`, `CONFLICTED`). Later valid delivery/read evidence may supersede an earlier
unknown or failure projection without deleting history. No transport observation changes
professional execution, customer decision or evidence state.

### 15.7 Media, Transcript And Erasure Lineage

The channel-neutral lineage is:

```text
provider media reference
  -> quarantined erasable payload
  -> immutable scan verdict/version
  -> clean erasable payload
  -> derived transcript/extraction version
  -> customer correction/confirmation version
  -> accepted canonical contribution
  -> payload-free evidence reference
```

Raw audio/media, quarantined copies, extracted text, transcripts, corrections, thumbnails,
embeddings, summaries, caches and temporary provider downloads are payload or payload derivatives.
Each has an authority, classification, store boundary, retention class, legal-hold behavior and
erasure path in Section 15.8. Corrections append; they never overwrite. Only the accepted version
enters professional context. Payload erasure removes resolvable pointers and derivatives and leaves
only a non-reconstructive tombstone plus permissible minimized evidence metadata. Provider-held
copies are tracked as an external deletion/expiry obligation and never reported as erased until
provider outcome is known or honestly unresolved.

### 15.8 Lifecycle, Hold And Erasure Matrix

| Record class | Policy owner / trigger | Legal hold | Erasure/correction result | Backup/cache behavior |
|---|---|---|---|---|
| Canonical message metadata | Product/Data/Legal; relationship and statutory trigger | Founder/Legal scoped hold | Preserve permissible metadata; erase payload reference/content under approved right | Age out payload in backups; metadata follows evidence policy |
| Message/context/profile payload | Data/Legal; purpose end, correction, customer right | Scoped hold blocks deletion and is visible to authorized process | Delete/supersede payload; append tombstone/lineage | Propagate to cache/search/summary; backup crypto/expiry erasure |
| Context observations/profile | Data/Legal; validity/freshness/correction | Fact/purpose scoped | Append successor, stale, dispute, or erase payload | Rebuild projection after restore |
| Derived summary/embedding/cache | Data; source/policy invalidation | Inherits source hold/sensitivity | Invalidate and delete/rebuild with source set | Never outlive source retention |
| Channel binding/assurance | Identity/Data; revocation, membership end, expiry | Security/Legal hold on evidence only | Revoke active use; retain minimized evidence | Restored inactive until revalidated |
| Provider inbox/dedup/tombstone | Security/Data; retry/replay horizon | Security incident hold | Remove payload, retain non-reconstructive replay tombstone | Same recovery point as canonical append |
| Delivery/status observations | Data/Legal; provider/accountability horizon | Incident/dispute hold | Retain minimized immutable transport evidence | Recompute projection after restore |
| Media/transcript derivatives | Data/Legal/Product; purpose, expiry, erasure | Explicit payload hold | Delete payload and derivatives; retain permissible tombstone/evidence | Quarantine/clean/cache/backups all age out |
| Opt-in/template evidence | Legal/Product/Data; consent and regulatory horizon | Dispute/regulatory hold | Revoke operational use immediately; retain permissible evidence | Restored inactive pending current consent check |
| Operational telemetry | Security/Operations/Data; diagnostic horizon | Incident hold | Delete/aggregate under telemetry policy | No customer payload; bounded backup |
| CE evidence reference | Constitutional/Legal | Constitutional hold rules | Never delete through payload erasure; minimize payload linkage | CE recovery policy |

Durations are named configuration classes, not hard-coded defaults. The Data/Legal contribution owns
class values; Founder accepts material rights/cost consequences. Hold creation and release are
attributable, scoped, evidenced and cannot silently reactivate operational use. Erasure propagates to
payload, cache, search, vector, summary, export, retry/dead-letter and backups according to their
class, with completion or unresolved external-provider status evidenced.

### 15.9 Backup And Recovery

Backups are environment-specific, encrypted with environment-specific key authority, access-audited,
and isolated from runtime/provider credentials. Data owns backup policy and restore procedure;
Platform owns infrastructure execution; Founder authority gates UAT/Production recovery activation.
Data owns RPO/RTO proposals and consistency groups; Founder accepts material cost/risk.

Restore order is schema/watermark -> canonical relationship/conversation -> idempotency/inbox/outbox
and sequence allocator -> context/profile lineage -> payload references/payloads -> delivery
observations/projections -> derived summaries/caches. Canonical messages, sequence state,
idempotency, dedup and outbox restore to the same consistency point.

Every restore first targets an isolated, non-routable environment with separate temporary workload
and encryption authority and no Meta callback, outbound dispatch, template or provider credential.
Qualification proves schema watermark, tenant/FORCE-RLS policy, composite references, sequence,
dedup/outbox consistency, payload linkage, lineage rebuild and reconciliation. Provider traffic
requires a separate explicit reactivation after current identity, consent, templates, Stop and
environment bindings are revalidated.

### 15.10 Environment Anti-Collision

Environment is immutable in provider-event, phone-binding, template, delivery, media, dedup,
tombstone, payload and backup namespaces. Equal provider IDs, phone proofs, idempotency keys or media
IDs in different environments cannot collide. Runtime principals, encryption keys and storage
authority are environment-specific.

Cross-environment import/restore is quarantined, non-routable and has no provider authority. It may
not remap environment, tenant, phone, app/WABA, template or callback identities in place and cannot
emit callbacks or outbound messages. Any approved migration creates new target identities through a
separately governed process with lineage and rollback evidence.

## 16. Failure Modes And Recovery

| Failure | Customer-visible behavior | Recovery invariant |
|---|---|---|
| Meta webhook retry | No duplicate message or action | Replay stored acceptance/outcome |
| Callback unavailable | Meta may retry; no fabricated receipt | Restore same environment binding and dedup state |
| Outbound provider timeout | `UNKNOWN` or unresolved delivery | Reconcile same outbound identity before retry |
| Delivery failure | Honest failed/unresolved state; alternate channel only with consent/policy | Never mark professional outcome failed solely from transport |
| Media URL expired | Explain media unavailable and request resend | Do not reuse stale URL/token |
| Scan/transcription unavailable | Text alternative or safe retry | No unscanned/uncertain media enters reasoning |
| Context ambiguity | Offer bounded choices or one clarifying question | No consequential execution |
| Stale plan/Decision Space | Reassessment required | Bind new context to current source versions |
| AIR/model unavailable | Explicit unavailable professional response state | No synthetic success |
| CE unavailable | Fail safe under ADR-031 | Stop remains executable |
| Channel handoff failure | Source remains active | No partial authority transfer |
| Environment binding mismatch | Reject and alert | No cross-environment fallback |
| Demo teardown during delivery | Stop acceptance before teardown; unresolved attempts retained per policy | UAT/Production untouched |

## 17. Quality Attributes And Fitness Contract

| ID | Fitness obligation | Passing evidence |
|---|---|---|
| CE-FIT-01 | One relationship has one canonical conversation across channels | Web -> WhatsApp -> web scenario retains IDs, sequence, plan and authority |
| CE-FIT-02 | Context switching is server-authorized | Forged/unknown context key and cross-subject reference produce zero mutation |
| CE-FIT-03 | Context reflects current source versions | Decision Space/plan/profile change stales affected context before next execution |
| CE-FIT-04 | No channel-specific recommendation drift | Same confirmed context/policy yields semantically equivalent recommendation across channels |
| CE-FIT-05 | Grooming avoids repeated known questions | Test corpus detects questions for current confirmed facts and fails |
| CE-FIT-06 | Material conversations conclude explicitly | Required conclusion fields present or typed reason indicates continuation |
| CE-FIT-07 | Delivery, execution, and evidence remain independent | State-transition tests prohibit implication across dimensions |
| CE-FIT-08 | Concurrent channels cannot double-commit | Same protected intent across web/WhatsApp commits at most once |
| CE-FIT-09 | Webhook authenticity and durable acknowledgement are fail closed | Challenge predicates, valid/invalid HMAC, constant-time raw-byte verification, modified/oversized body, concurrent claim, stale/new and delayed accepted-retry tests |
| CE-FIT-10 | WhatsApp service-window/template rules are deterministic | Inside/outside window and approved/rejected/version-mismatch scenarios |
| CE-FIT-11 | Media cannot bypass safety or consent | Signature/MIME mismatch, archive/polyglot/active format, expansion/resource limit, malware, scanner timeout/error, expired URL, low confidence and correction scenarios |
| CE-FIT-12 | Environment isolation is exact | Demo credential/number/host/state rejected in UAT and Production, and vice versa |
| CE-FIT-13 | Stop is universal | Typed Stop under CE outage, duplicate delivery, simultaneous channels, adapter restart and WhatsApp release attempt blocks all consequential contexts within existing latency budget |
| CE-FIT-14 | Privacy-safe observability | Automated success/failure-path scan finds no prohibited payload/header/signature/identity/provider/prompt/transcript/media/secret data in logs, metrics, traces, baggage, exceptions or dead letters |
| CE-FIT-15 | Mobile can reuse public semantics | Contract conformance uses a second generated client without server semantic changes |
| CE-FIT-16 | Demo teardown is bounded | Teardown evidence proves callback disabled, temporary state handled, UAT/Prod unchanged |

## 18. Observability And Operational Evidence

Metrics and traces must use opaque identifiers and include:

- webhook verification failures by safe reason;
- inbound dedup/replay count;
- canonical acceptance latency;
- context resolution result and ambiguity/staleness count;
- policy version distribution;
- repeated-known-question violations;
- conclusion completion and unresolved-interaction rates;
- outbound queue, provider acceptance, delivery, read, failure, unknown, and age;
- service-window/template rejection;
- media retrieval/scan/transcription states and latency;
- channel handoff success/revert;
- cross-channel idempotency conflict;
- Stop propagation;
- environment-binding denial; and
- payload/log privacy scanner findings.

Alerts must distinguish customer action, provider outage, WAOOAW defect, security denial, stale
authority, and unavailable constitutional governance.

## 19. Cost And Capacity

- Message classification and routine routing use the approved lowest sufficient tier under ADR-024.
- Canonical history is not sent wholesale to a model; bounded retrieval and versioned summaries
  control cost and latency.
- Media retrieval, scanning, transcription, storage, and outbound templates are metered independently.
- Provider retry amplification is bounded by deduplication and reconciliation.
- Demo scales to zero only after callback acceptance is safely disabled.
- UAT fixed ingress does not imply minimum application replicas unless qualification demands it.
- Production sizing remains a Platform Architecture decision based on measured UAT volume and SLOs.

## 20. Reversibility And Migration

ADR-052 can be rejected before implementation without data migration. After implementation:

- preserve canonical message and context history while disabling new context/policy versions;
- retain the prior supported policy/context schema for a bounded rollback window;
- block commands introduced only by the new version during rollback;
- never rewrite evidence or accepted customer decisions; and
- migrate summaries/checkpoints as derived artifacts with reproducible source references.

ADR-053 permits an environment to move to a new Azure ingress or hostname by controlled DNS and Meta
callback rebinding while retaining the same environment identity and proving no cross-environment
fallback. Number migration requires an explicit provider migration plan, customer communication,
template/opt-in continuity analysis, rollback, and Founder authority.

Schema and data evolution uses expand -> migrate -> contract. Before traffic, a migration lock binds
the exact schema/data watermark. Backfill is idempotent and bounded by environment, tenant and
relationship, records source/provenance, and validates row counts, composite references, sequence,
lineage, dedup, payload and projection invariants. Mixed releases retain previous-version read
compatibility during the rollback window.

Cutover records a watermark for sequence allocation, idempotency namespace, context/profile lineage,
delivery projection, payload/tombstone and summary rebuild. Rollback restores the prior reader/writer
contract without destructive down-migration and preserves records created under the new version.
Contract/removal occurs only after rollback expiry and retained-data compatibility evidence.

## 21. Dependency Impact

| Surface | Required downstream work |
|---|---|
| Business Platform | Context/policy projection, channel-neutral contracts, WhatsApp adapter, delivery state |
| Professional Runtime | Bind executions to context/policy versions; preserve Stop and idempotency |
| AI Runtime | Context assembly, policy application, research/fact/inference separation, voice reuse |
| Constitutional Engine | Existing authority/evidence/Stop integration; no conversational authority |
| WBE | Existing usage/budget truth projected without recomputation |
| Web | Registered context hints, generated client, one canonical timeline |
| Future mobile | Same generated public semantics; mobile-specific presentation only |
| Meta/WhatsApp | Environment registration, callback, templates, messages, media, status |
| Azure/Platform | Static environment ingress, DNS/TLS, Key Vault, optional separate egress, monitoring |
| Data | Physical schema, RLS, retention, erasure, recovery, conflict/index design |
| Security | Threat controls, secret/workload authority, media safety, abuse, privacy validation |
| Product/Agent specs | Context-purpose behavior, customer-visible style, conclusion and fallback semantics |
| Test Champion | Fitness contract automation and cross-channel/environment matrices |

## 22. Chief Solution Architect Handoff

The Chief Solution Architect must produce one coherent versioned solution package containing:

1. component responsibility and interaction diagrams using only the approved container boundaries;
2. public BP and internal BP/PR/AIR/Phone Identity contracts;
3. exact Interaction Context resolution and conflict state machines;
4. Conversation Policy resolution, versioning, and rendering contracts;
5. channel-neutral message, command, card, event, delivery, and error schemas;
6. WhatsApp challenge, inbound, outbound, template, status, media, and voice sequences;
7. authentication, authorization, assurance, idempotency, replay, Stop, and privacy behavior;
8. data ownership references from the Data Architecture contribution;
9. deployment topology references from Platform Architecture;
10. failure, reconciliation, rollback, and observability contracts;
11. generated-client compatibility and mobile reuse proof approach;
12. mapping from every component behavior to CE-FIT-01 through CE-FIT-16;
13. an impact assessment for existing Conversation Core, F5 continuity, F6 voice, ADR-023, and
    ADR-051 surfaces; and
14. explicit implementation tasks and stops for Platform IT Expert, without implementation itself.

The Solution Architect must not:

- create a new Conversation Engine service without a returned C-095 decision;
- let a channel own relationship truth or reasoning;
- accept tenant, authority, prompt, or policy from a client payload;
- collapse provider delivery into customer decision or constitutional evidence;
- hard-code phone numbers, provider IDs, credentials, callback hosts, or templates;
- activate mobile architecture under ADR-032; or
- treat this proposed package as Founder acceptance or implementation authority.

## 23. Required Office Contributions Before Implementation

| Office | Required contribution |
|---|---|
| Data Architect | Physical ownership, RLS, sequence/concurrency, retention, erasure, recovery, media and dedup lifecycle |
| Security Architect | Threat model, webhook/raw-body verification, secret/workload authority, media safety, abuse, step-up, privacy-safe telemetry |
| Platform Architect | Azure ingress/DNS/TLS, environment isolation, optional egress, callback operations, rollback, Demo teardown |
| AI Architect | Policy/context assembly, research and inference lineage, prompt-injection separation, tier/cost behavior |
| Product Owner | Customer-visible context transitions, style acceptance, WhatsApp consent/template journeys, unsupported states |
| Test Champion | Executable fitness and adversarial matrices |

Founder-requested Data and Security reviews may validate this EA package now. Their review does not
substitute for the detailed downstream Data and Security solution contributions.

## 24. Open Owner-Bound Decisions

| Decision | Owner | Current state | Stop condition |
|---|---|---|---|
| Exact Production E.164 number | Founder | Not purchased; preferred suffix `926629` | Production configuration/activation blocked |
| Approved domain hostnames | Founder/Platform authority | Patterns proposed, exact domain pending | DNS/callback mutation blocked |
| Meta app/WABA topology per environment | Founder + Security/Platform | Must be environment-isolated; exact account arrangement pending | Provider activation blocked |
| Retention durations by payload class | Data + Legal/Founder | Must be explicit downstream | Implementation of persistence cleanup blocked |
| Recovery objectives by data class and environment | Data + Platform/Founder | RPO/RTO and restore authority not yet approved | Persistence/deployment qualification blocked |
| Supported WhatsApp media types/sizes/locales | Product + Security + Data | Architecture requires bounded declaration | Media activation blocked |
| Production traffic, cost, DNS, provider credentials | Founder | Not authorized by this package | Production remains dark |

These decisions do not block Solution Architecture if its contracts keep the values configurable and
fail closed. They do block the corresponding provider, data-lifecycle, DNS, or Production activation.

## 25. External Primary References

- Meta, WhatsApp Cloud API:
  https://developers.facebook.com/docs/whatsapp/cloud-api
- Meta, create and verify webhook endpoints:
  https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint
- Meta, secure Graph API webhooks:
  https://developers.facebook.com/docs/graph-api/webhooks/securing
- Meta, WhatsApp messages and media:
  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
- Meta, message templates:
  https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates
- Microsoft, Azure Container Apps networking:
  https://learn.microsoft.com/en-us/azure/container-apps/networking
- Microsoft, Azure Container Apps custom domains and certificates:
  https://learn.microsoft.com/en-us/azure/container-apps/custom-domains-certificates
- Microsoft, Azure Container Apps custom virtual networks:
  https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks

External references support provider and infrastructure facts only. WAOOAW constitutional claims,
capabilities, drivers, accepted ADRs, and Founder decisions remain authoritative for architecture.

## 26. Enterprise Architecture Definition Of Done

- Every Founder requirement maps to a structural decision and owner.
- Existing F3/F5/F6, ADR-023, and ADR-051 authority boundaries are preserved.
- No unapproved new deployable service or technology is introduced.
- Context, policy, history, channel, identity, delivery, media, environment, failure, security, data,
  observability, cost, and reversibility are specified.
- The Solution Architect can decompose the package without inventing a boundary or quality target.
- Security and Data reviews are completed once, and valid findings are applied.
- Author review records no unresolved finding.
- The PR is prepared for Founder review; it is not self-approved or self-merged.

## 27. Institutional Review Remediation Record

The Founder-requested single-pass reviews were performed against commit `f5bb9e49`.

| Review finding | Resolution in this package |
|---|---|
| R-146 HIGH-01 phone identity/assurance | Sections 12.7, 15.3 and CE-FIT-02/08/12 |
| R-146 HIGH-02 webhook acknowledgement/replay | Sections 12.1, 15.1, 15.5 and CE-FIT-09 |
| R-146 HIGH-03 secret/workload authority | Section 13.6 and CE-FIT-12/14 |
| R-146 HIGH-04 WhatsApp Stop | Section 12.8, Section 16 and CE-FIT-13 |
| R-146 MEDIUM-01 context injection | Section 8.6 and CE-FIT-02/04/14 |
| R-146 MEDIUM-02 media safety | Sections 12.5, 15.7/15.8 and CE-FIT-11 |
| R-146 MEDIUM-03 service window/template time | Section 12.4 and CE-FIT-10 |
| R-146 MEDIUM-04 telemetry privacy | Sections 14.3, 15.8 and CE-FIT-14 |
| R-147 DA-B1 logical boundary | Section 15.1 |
| R-147 DA-H1 ordering/concurrency | Section 15.2 |
| R-147 DA-H2 tenant/RLS | Section 15.3 |
| R-147 DA-H3 fact/summary lineage | Section 15.4 |
| R-147 DA-H4 idempotency/dedup lifecycle | Section 15.5 |
| R-147 DA-H5 delivery observations | Section 15.6 |
| R-147 DA-H6 media/transcript lineage | Section 15.7 |
| R-147 DA-H7 lifecycle/recovery | Sections 15.8/15.9 |
| R-147 DA-M1 environment anti-collision | Section 15.10 |
| R-147 DA-M2 migration/rollback | Section 20 |

The original review records remain immutable evidence of the single pass. This remediation is author
repair, not reviewer approval. Founder review remains the acceptance gate.
