# WC-135 - Visitor Conversation, Lead Capture And Simulated Customers

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-135 |
| Authoring office | Platform IT Expert (INST-010) |
| Architecture review | Enterprise Architect (INST-004) and Solution Architect (INST-005), each on explicit Founder request, 2026-11-19; findings and dispositions are recorded in the Review Records section |
| Founder assignment | Current conversation, 2026-11-19: tune the WhatsApp "WAOOAW Agent" so a visitor who does not know WAOOAW gets a warm, curious, useful conversation, and prove it with simulated customers that call the same APIs every channel uses |
| Status | DRAFT FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED |
| Implementing office | Named after current-session Founder authorization; on 2026-11-19 the Founder authorized only the writing of this contract |
| Baseline | `origin/main` at `12efe5c4` (WC-134 PR #600 merged) |
| Related contracts | WC-120 conversation; WC-121 provider enablement; WC-133 first contact; WC-134 WhatsApp Demo rollout (guest discovery and authenticated customer channel) |
| Requirement ledger | [WC-135-requirements.yaml](./WC-135-requirements.yaml) |
| Constitutional basis | C-009, C-023, C-039, C-042, C-048, C-049, C-059, C-063; accepted consent, Stop, tenant-isolation and data-rights controls |
| Naming note | "Simulated customer" is used throughout. "Synthetic Approval" (C-044, AD-017) is a different capability and is not used here. |

## Evidence Summary

| # | Observation (Demo, 2026-11-19) | Source |
|---|---|---|
| E1 | A first-time visitor received a consent notice, then, after YES, a catalogue reply that opened with "Welcome to WAOOAW Demo... does not create a customer account..." and listed three skill names with "listed for trial". It gave no description of what each skill does for a business, no portal link and no next question. The STOP line ended three of four messages. | Founder-relayed WhatsApp transcript, 19:58 IST |
| E2 | The visitor reply is a deterministic keyword-and-template renderer. Its fixed text, including "WAOOAW Demo", the portal wording and the 09:00-21:00 IST opening hours, lives in code. | `PortalInteractionService.cs` guest discovery path; `WhatsAppGuestOperatingHours.cs` |
| E3 | The Founder-approved Digital Marketing Professional specification already defines a curious, outcome-led Interview Mode. The live reply does not follow it. | `architecture/reference/agents/digital-marketing-agent.md` section 3.23 |
| E4 | Guest discovery is reachable only through the Meta-signed WhatsApp webhook. The portal conversation API needs a signed-in customer with a membership. No channel-neutral visitor API exists for a web app, a mobile app or a test client. | `WhatsAppJourneyController.cs`; `PortalInteractionsController.cs`; `IGuestConversation` is service-internal |
| E5 | A visitor who sends STOP stays stopped permanently; later messages receive HTTP 200 and no reply. There is no START or resume path. Verified live: stop recorded 2026-11-16, a 2026-11-19 message from that number was accepted and unanswered while a different number was answered. | `WhatsAppGuestSessionService.cs`; Demo logs |
| E6 | The webhook does not log the status or reason of an error response, so four failing calls between 11:53 and 14:01 UTC on 2026-11-19 cannot be classified. | Demo Container Apps console logs |
| E7 | The platform has no lead record. `business.acquisition_intents` stores a trial or hire request after contract acceptance, keyed by a hashed identity, and holds no business type, city, name or email. | `infrastructure/postgres/init/49-wc112-acquisition-intents.sql` |
| E8 | The public site promises four professionals and a "ten minutes a day" experience; the WhatsApp reply described one professional. | `https://cp.demo.waooaw.com` |
| E9 | The existing phone-destination envelope is AES-GCM with a fixed `v1` prefix and no key identifier; its key is the pinned phone-subject key version. A key rotation would leave stored numbers unreadable. | `WhatsAppPhoneDestinationProtector` in `WhatsAppGuestSessionService.cs` |
| E10 | Inbound WhatsApp messages of any type other than `text` are classified as unsupported content, so a tapped button or list reply would be refused. Outbound dispatch builds `text` and `template` payloads only. | `WhatsAppJourneyService.cs` message parsing; `WhatsAppCloudProviderAdapter.cs` |

## Authority And Scope

Founder decisions of 2026-11-19 that bind this contract:

1. Success means the visitor both leaves business details and starts the trial, measured separately
   as full success, lead only, intent only, opt-out and drop-off.
2. This release is fully scripted. The design must allow a later release to switch a tenant to
   generative, policy-bounded free-form answers by configuration, with consent, Stop, pricing and
   claims always fixed text.
3. Replies use simple English: no Hinglish, no technical or legal-heavy wording beyond what consent
   requires.
4. The Digital Marketing Professional is explained in depth. The other three professionals receive
   two to three lines ending "coming soon".
5. Price is not stated in replies in this release; pricing stays in the portal.
6. Business type and city are the core details. Name and email are encouraged, never required. The
   phone number is already known from WhatsApp and is not asked for there.
7. Details are stored as a lead record and carried into trial registration.
8. The phone number is stored as a hash and also as an encrypted raw value.
9. Lead retention is configurable, defaulting to 90 days, and is not hardcoded.
10. The design must support a later "customer mode" in which a small business operates and monitors
    its agents from WhatsApp. Only visitor mode is built here.

In scope: the channel-neutral visitor conversation core and endpoint; the structured reply model
with WhatsApp interactive rendering and inbound interactive parsing; scripted content as
Conversation Policy layers; the lead record, retention and handoff; START/resume; per-response
logging; fair-use limits; the simulated-customer harness and its gate.

Not in scope: customer-mode behavior; price, payment or trial-terms text in replies; generative
free-form answers; new professionals; Meta console or template changes; deployment or provider
mutation; public anonymous web or mobile exposure of the visitor endpoint (built and tested, left
disabled pending the Security decision in Open Decisions); messaging real phone numbers from
simulated customers; changes to constitutional documents. The Hinglish opener and price in DMA
section 3.23 are Founder-directed deviations; amending that section is a separate authorized step.

## Capability, Driver And Decision Trace (Enterprise Architecture)

| Obligation | Capability | Claims / drivers | Decisions it must conform to |
|---|---|---|---|
| Visitor learns what WAOOAW and its professionals do before committing | 1.6 Browse Agent and Skill Catalogue; PG-01 | C-009 (rights visible before hiring), C-039, C-042, C-048, C-049 | ADR-052 (Conversation Policy layers), ADR-019 (grounding, for the later generative responder) |
| Visitor is led from first message to the trial | 1.8 Enroll in Trial Engagement; PG-08, PG-14 | C-009; trial has no billing commitment (C-038) | ADR-051 (one relationship, one conversation after handoff) |
| Minimum context is captured in business language | 1.7 Configure Agent via Conversation; PG-06 | C-039, C-042 | ADR-052 (typed proposals; authoritative owner commits) |
| One behavior across WhatsApp, web and mobile | PG-14, PG-03 | AD-004, AD-013 | ADR-052 (BP is the only public conversation facade; clients cannot supply tenant, prompt or policy), ADR-053 (WhatsApp transport and service window), ADR-002 (OpenAPI first) |
| Consent, Stop, opt-out and deletion | Existing consent and data-rights controls; PG-04 (Stop is channel-independent) | C-001, C-023 | WC-134 guest consent; data-rights endpoint |
| Per-tenant fair use | Existing traffic budget | AD-004 | ADR-006 (per-tenant limits at BP middleware) |
| Simulated-customer evaluation | Founder-directed supporting capability (see Review Records F-E2) | C-059, C-063 | ADR-016 (Python 3.12 for tooling, no new language), ADR-029 (sanctioned model providers), ADR-024 (cost gates) |

**Dependency acceptance.** ADR-051, ADR-052 and ADR-053 are Proposed. WC-135 conforms to them as
written and may not contradict them. The Founder must accept them, or accept WC-135 as
authority to proceed on them, before `IMPLEMENTATION_AUTHORIZED`. If a Founder review amends them,
this contract is re-reviewed before implementation.

**Boundary decisions.**

1. No new deployable service. The visitor conversation core and endpoint live in Business
   Platform, the only public conversation facade (ADR-052). Constitutional evidence for guest
   admission continues to go through the Constitutional Engine.
2. A visitor conversation is pre-relationship guest scope. It is not an Employment Relationship
   conversation. After handoff and registration the relationship conversation (ADR-051) owns the
   history; the visitor transcript is not merged.
3. Scripted content is expressed as Conversation Policy layers (institutional, professional,
   interaction-purpose, vocabulary, locale, channel-rendering), versioned and resolved per tenant
   and professional on the server. Clients may not supply policy, prompt, tenant or authority.
4. The responder interface is the only seam where a later generative responder plugs in. The
   generative responder, when authorized, must be grounded per ADR-019, routed per ADR-024/029, and
   cannot alter fixed-text categories.
5. Build versus adopt: WhatsApp interactive messages (buttons, lists, link buttons) are adopted
   from the Cloud API, not rebuilt. For the simulator the evaluation methodology (persona-driven
   user simulation, separate judge, repeated runs, separate success and policy scores) is adopted;
   the harness is built thin because the personas, the endpoint and the policy are WAOOAW-specific.
   No third-party benchmark code is imported without a dependency review.

## Interface Contract (Solution Architecture)

All paths are Business Platform REST, specified in OpenAPI before any endpoint code (ADR-002),
with generated web client artifacts regenerated from the same spec.

| Operation | Method and path | Notes |
|---|---|---|
| Open or resume a visitor session | `POST /api/v1/visitor/sessions` | Body: channel (`WEB`, `MOBILE`, `SIMULATION`), optional resume token. Tenant and professional context are resolved on the server from the host or credential, never from the body. Returns a signed, short-lived visitor session token bound to channel and tenant. |
| Send a visitor message | `POST /api/v1/visitor/sessions/{sessionId}/messages` | Required `Idempotency-Key` UUID header. Body: `content` of type `TEXT` (bounded text) or `CHOICE` (a `choiceId` from the previous reply). Optional `expectedCursor`. |
| Read the transcript | `GET /api/v1/visitor/sessions/{sessionId}/messages?cursor=&limit=` | Bounded page; own session only. |
| Hand off to the portal | Included in the reply as a `LINK` block with an opaque lead reference | See Handoff Contract. |

WhatsApp does not call these paths over HTTP. The signed webhook (ADR-053) authenticates the sender
and invokes the same in-process conversation core; the channel adapter only renders the structured
reply. Equivalence between the two entry points is a tested requirement.

- **Identity and authorization.** WhatsApp: signed webhook plus phone subject hash. Web and mobile:
  the visitor session token. Simulator: a separate demo-only credential with role
  `visitor-simulator`. Session ownership is enforced on every read and write.
- **Structured reply.** `{ schemaVersion, state, cursor, blocks[] }` where each block is `TEXT`,
  `CHOICES` (up to 3 buttons, unique labels), `LIST` (up to 10 rows) or `LINK` (label and
  destination). A free-text answer is always accepted in addition to any choices. The channel
  limits (button label length, body length, list rows) are configuration read from the channel
  capability layer and are verified against Meta's current documentation before the renderer is
  built; the values used in design discussions (3 buttons, 20-character labels, 10 list rows) come
  from secondary sources.
- **Errors.** RFC 7807 problem responses with fixed codes: `VISITOR_SESSION_REQUIRED` (401),
  `VISITOR_REQUEST_INVALID` (400), `VISITOR_IDEMPOTENCY_CONFLICT` (409), `VISITOR_RATE_LIMITED`
  (429 with `Retry-After`), `VISITOR_UNAVAILABLE` (503). A stopped visitor receives 200 with no
  reply blocks and state `STOPPED`; the response never reveals more than the state.
- **Idempotency and retries.** A repeated `Idempotency-Key` returns the original reply (200) and
  creates no second message or outbound send. Provider redelivery is deduplicated by the existing
  provider-event claim. Clients may retry 429 and 503 safely.
- **Limits and timeouts.** Per-tenant and per-visitor limits at BP middleware (ADR-006), reusing
  the existing guest traffic budget values and notices. Hard timeout 2 s, in line with the
  Business Platform write-operation row of `architecture/reference/slo.md`.
- **Telemetry.** Every response emits one structured log event and metric increments with the
  fields in the Observability Contract.
- **Inbound interactive messages.** WhatsApp `interactive` messages of type `button_reply` and
  `list_reply` are parsed into `CHOICE` content by id. Other non-text types (voice, image,
  location, reaction) continue to receive the fixed "unsupported content" reply, now worded as a
  friendly redirect; reactions and system events are acknowledged without a reply.
- **Outbound interactive messages.** The provider adapter gains interactive and link-button payload
  construction from the canonical block model, inside the existing service-window and template
  rules of ADR-053. Typing and read indicators are sent where the provider supports them and are
  best-effort; their failure never blocks or fails a reply.

## Visitor State Machine (Solution Architecture)

| State | Entered when | Reply type | Leaves on |
|---|---|---|---|
| `NEW` | First inbound from an unseen subject | none yet | any inbound moves to `CONSENT_PENDING` |
| `CONSENT_PENDING` | Welcome and consent notice sent | Fixed text, welcome plus consent plus YES and STOP choices | YES to `DISCOVER`; STOP to `STOPPED`; other text re-sends the notice once, then waits |
| `DISCOVER` | Consent recorded | One question about the business | business type and city captured to `QUALIFY`; unanswered text gets one rephrase |
| `QUALIFY` | Core details captured | One goal question as choices | goal captured, or skipped, to `SHOW_VALUE` |
| `SHOW_VALUE` | Qualified | Digital Marketing Professional explained, matched to the business type | any follow-up stays here; "ready" intent to `OTHER_PROFESSIONALS` or `HANDOFF` |
| `OTHER_PROFESSIONALS` | On request or at close | Two to three lines on the other three, ending "coming soon" | to `HANDOFF` |
| `HANDOFF` | Trial intent | Link to the portal with the opaque lead reference; name and email requested once, with the reason | tap recorded as `INTENT`; session stays open |
| `STOPPED` | STOP | none | START to `CONSENT_PENDING` (consent is asked again) |

Rules for every transition: it is idempotent per provider message or idempotency key; it is
recorded with the prior and next state; STOP is honored in every state at any time and START is a
no-op outside `STOPPED`. Closed hours, rate limits and unsupported content produce their fixed
notices without changing state. If the scripted content for a tenant or professional is missing or
invalid the conversation fails closed with a fixed neutral notice and a logged reason; it never
falls back to hardcoded tenant text.

| Failure | Behavior |
|---|---|
| Constitutional Engine unavailable at consent or admission | Fail closed: 503 to the client, no reply, retry-safe; logged with reason. |
| Lead write fails | The reply is still sent (consent evidence already recorded); the write is retried and the failure is logged; the lead is never reconstructed from transcripts. |
| Provider send fails or is ambiguous | Existing outbox and reconciliation rules; classified reason logged; never blindly resent. |
| Unknown business type | Stored as `OTHER` with the bounded free text; conversation continues. |
| Duplicate delivery or double tap | Same idempotent reply; no second lead or outbound message. |
| Simulator session | Never reaches the provider adapter; leads carry `SIMULATION` and are excluded from product metrics. |

## Data Contract (Solution Architecture)

New table `business.visitor_leads`, created by an additive migration under
`infrastructure/postgres/init/` (append-only, ADR-011), with forced row-level security by tenant
(AD-004) and explicit grants to the Business Platform role only.

| Column | Type and rule |
|---|---|
| `lead_id` | UUID primary key |
| `tenant_id` | UUID, not null, RLS key |
| `subject_hash` | CHAR(64), not null; HMAC of the subject; unique with `tenant_id` while the lead is open |
| `phone_protected` | Text, nullable; AES-GCM envelope `v2.<keyVersion>.<nonce>.<tag>.<ciphertext>` carrying the key version identifier |
| `business_domain` | VARCHAR(64); a value from the existing `business_domain_taxonomy`, else `OTHER` |
| `business_text` | VARCHAR(120), nullable; bounded free text when the domain is `OTHER` |
| `city` | VARCHAR(80), nullable |
| `goal_code` | VARCHAR(48), nullable; a code from a fixed goal list in the content layer |
| `contact_name` | VARCHAR(80), nullable |
| `contact_email_protected` | Text, nullable; same envelope as the phone |
| `source_channel` | `WHATSAPP`, `WEB`, `MOBILE` or `SIMULATION` |
| `consent_reference` | UUID, not null; the guest consent evidence identifier |
| `status` | `OPEN`, `INTENT`, `CONVERTED` |
| `acquisition_intent_id` | UUID, nullable; set at conversion |
| `created_at`, `updated_at` | Timestamps, not null |

Retention is read at purge time from per-tenant options, not stored per row, so a change applies
at once. Index on `(tenant_id, updated_at)` for the purge scan.

- **Options.** `VisitorLeads:RetentionDays` (default 90) and `VisitorLeads:SimulationRetentionDays`
  (default 7), validated at startup: positive integers within a minimum and maximum that are
  Founder-owned; provisional bounds of 7 and 365 days pending Founder confirmation. An invalid
  value fails startup rather than defaulting silently.
- **Purge.** A hosted job runs on a configured interval, takes a database advisory lock so only
  one replica purges, deletes in bounded batches, is idempotent, and logs counts only. `CONVERTED`
  leads are excluded; they follow the customer record.
- **Encryption and keys.** The raw phone and the email use envelope `v2` with the key version
  identifier stored in the ciphertext. New writes use the current pinned version; reads select
  the key by the stored version; a re-wrap job moves rows to the current version before an old
  version is retired. The existing `v1` destination envelope remains readable. Rotating the
  phone-subject key while leads exist is a stop condition until a re-key plan (hash and envelope)
  is approved.
- **Data rights.** The existing data-rights export and deletion cover consent, session and lead.
  Deletion removes the lead and its protected values, and the result is auditable.
- **Classification.** Phone, email and name are personal data. Name is stored in clear under RLS
  and is masked in logs; the phone and email are protected as above. Security confirms this
  classification before implementation.

## Handoff Contract (Solution Architecture)

1. The `LINK` block points to the portal registration or trial page with an opaque, signed,
   single-use lead reference. The reference holds only the lead id and an expiry. It carries no
   personal data and is never logged in full. Its lifetime is a configured value.
2. Tapping the link records `INTENT` on the lead.
3. After the visitor signs in and the identity is verified, registration reads the lead on the
   server. Only non-sensitive fields (business domain, city) are pre-filled by default. Name,
   email and the link to the lead are applied only when the verified identity matches the lead's
   subject; otherwise the visitor re-enters them and no link is made.
4. Completing the trial sets the lead `CONVERTED` and stores `acquisition_intent_id`. A reused or
   expired reference yields an ordinary registration page with no error detail.
5. Handoff preserves context without duplicate delivery (PG-14); the visitor transcript stays in
   guest scope.

## Observability Contract

Each response logs one event with: event name, channel, tenant (not PII), conversation state,
prior state, HTTP status, fixed reason code, content version, latency, and a correlation id. It
never logs message text, phone, email or name. Metric names (counters unless stated): `visitor_turn`,
`visitor_outcome{full,lead,intent,optout,dropoff}`, `visitor_state_exit{state}`,
`visitor_choice_tap{choiceId}`, `visitor_turns_to_first_value` (histogram),
`visitor_policy_violation`, `visitor_response_ms` (histogram). Production conversation sampling
for quality review is permitted only through the PII-masking pipeline and only where the consent
notice discloses quality review; otherwise review uses aggregates and simulated conversations.

## Architecture Fitness Contract

| # | Fitness function | Threshold | Check |
|---|---|---|---|
| F1 | WhatsApp and endpoint equivalence | Identical structured reply for identical input | Parity test over fixed transcripts |
| F2 | Scripted turn latency | P95 within the Business Platform write-operation target in `slo.md`; hard timeout 2 s | Latency test in the Docker runner |
| F3 | No hardcoded tenant or professional text in reply paths | 0 occurrences | Static guard test |
| F4 | Personal data in structured logs | 0 occurrences | Log-capture tests across all outcomes |
| F5 | Retention | 100% of expired leads removed, 0 unexpired removed, 0 converted removed | Purge test with injected clock |
| F6 | Simulator isolation | 0 provider-adapter calls and 0 real-number sends | Isolation test |
| F7 | Policy compliance in the evaluation suite | 0 price, guarantee, forbidden-claim or consent violations | Suite result |
| F8 | Reversibility | Flag-off restores legacy behavior with no data loss | Rollback test |

Conversion and quality targets for the evaluation suite (for example the lift in full-success and
lead rates over the baseline) are Founder-owned values recorded before the baseline run.

## Canonical Requirement Index

| ID | Requirement | Executable evidence |
|---|---|---|
| WC135-R001 | Success is defined and measured as full success, lead only, intent only, opt-out and drop-off, each recorded with the state where the visitor stopped. | Outcome-classification unit tests; fixed-transcript replay test. |
| WC135-R002 | The visitor conversation follows the state machine and failure matrix in this contract; every reply carries one idea and at most one question; STOP is honored in every state. | State-machine unit tests; per-state reply-shape test. |
| WC135-R003 | One channel-neutral conversation core and endpoint serve WhatsApp, the simulator and any future client with identical behavior; the interface contract is implemented as specified; customer mode returns a defined "not available" result; public anonymous web exposure stays disabled by configuration. | Endpoint contract tests; WhatsApp-versus-endpoint parity test (F1); flag-off test. |
| WC135-R004 | Replies use the structured block model; WhatsApp renders interactive messages and link buttons and parses inbound `button_reply` and `list_reply` into choices; other channels render equivalents; limits come from configuration; a free-text answer is always accepted; indicators are best-effort. | Renderer and limit tests; inbound parsing tests; webhook-to-reply integration test. |
| WC135-R005 | Replies come from a responder behind one interface; this release ships a scripted responder reading Conversation Policy layers per tenant and professional (including opening hours and notices); no tenant or professional text is hardcoded in reply paths; the generative responder cannot be selected; fixed-text categories stay fixed. | Responder selection and refusal tests; hardcoded-string guard (F3); content-version and fail-closed tests. |
| WC135-R006 | Scripted content uses simple English, explains the Digital Marketing Professional in depth with examples labelled as examples, gives the other three two to three lines ending "coming soon", states no price or outcome guarantee, carries the portal link at handoff, and shows the STOP reminder only where required; the Founder approves the wording before it is built. | Content lint tests; recorded Founder approval. |
| WC135-R007 | The lead record, encryption envelope `v2` with key version, per-tenant isolation, and lead write behavior follow the Data Contract; name and email are requested once, with the reason, and never required. | Migration and RLS tests; envelope round-trip and rotation tests; write-failure test. |
| WC135-R008 | Lead retention and simulation retention are configurable, validated, applied at purge time, executed by a single-replica purge job that logs counts only; converted leads are excluded; data-rights export and deletion cover leads. | Options validation tests; purge tests with injected clock and concurrent runners; data-rights tests. |
| WC135-R009 | A stopped visitor can send START, is asked for consent again, resumes only after YES, and the transition is audited; other text from a stopped visitor receives no reply. | Guest-session unit and Postgres tests. |
| WC135-R010 | Every webhook and endpoint response emits the Observability Contract event with status, reason code and state and no personal data; production sampling is limited as stated. | Log-capture tests (F4); failure-class coverage test. |
| WC135-R011 | Per-tenant and per-visitor limits apply at BP middleware; the simulator uses a separate demo-only credential with a hard cap on turns and runs and cannot reach the provider adapter or real numbers. | Limit tests; isolation test (F6). |
| WC135-R012 | A simulated-customer harness drives the endpoint with seven personas (Dr. Mehta, Rupali, Kiran, Yashus from DMA section 2, plus a farmer, a tutor-seeker and a trader), each with intent, knowledge, mood and patience; a separate judge scores one criterion per judge with anchored examples; scenarios run repeatedly; task success and policy compliance are scored separately; failure injection covers slow catalogue, media, STOP mid-conversation and unknown language; a baseline against the pre-change replies and a post-change comparison are recorded. | Harness tests with a fake model; recorded baseline and comparison. |
| WC135-R013 | The evaluation suite gates changes to visitor content and prompts; metrics in the Observability Contract are emitted; model use follows ADR-024 and ADR-029 with a per-run cost cap. | Gate-wiring pipeline test; metric-emission tests; cost-cap test. |
| WC135-R014 | The portal handoff follows the Handoff Contract: opaque single-use reference, `INTENT` on tap, non-sensitive prefill by default, link only on verified identity match, conversion sets `CONVERTED`. | Handoff unit tests; reuse and expiry tests; identity-mismatch test. |
| WC135-R015 | Specification precedes code: the component specification, the OpenAPI definition, the Conversation Policy content schema and the generated client artifacts are updated and reviewed before any endpoint or renderer code. | Spec and generated-artifact consistency check; C-059 header trace. |
| WC135-R016 | Privacy: personal data is classified per the Data Contract; logs and evaluation inputs carry none; the consent notice discloses quality review wherever production sampling is used; simulated conversations use only fabricated data. | Classification review record; log tests (F4); content test for the disclosure. |
| WC135-R017 | Validate with the Docker-only runners, perform author review and submit an exact-head PR using the repository template; new tests are wired into the explicit CI and release-qualification lists. | Commands and results in the PR. |

## Work Components And Order (Solution Architecture)

| Order | Work component | Requirements | Depends on |
|---|---|---|---|
| 0 | Specification package and Founder content approval | R015, R006 (wording) | Dependency acceptance of ADR-051/052/053 |
| 1 | Data: migration, envelope `v2`, options, purge job | R007, R008, R016 | 0 |
| 2 | Core: state machine, responder seam, content layers, START | R001, R002, R005, R009 | 0, 1 |
| 3 | Endpoint and channel adapters: visitor API, WhatsApp renderer, inbound interactive parsing, limits | R003, R004, R011 | 2 |
| 4 | Observability and metrics | R010 | 3 |
| 5 | Handoff and registration pre-fill | R014 | 1, 3 |
| 6 | Simulated customers, scoring and gate | R012, R013 | 3 (baseline may run earlier on the current path) |
| 7 | Validation and delivery | R017 | all |

Components 4 to 6 may proceed in parallel after 3. Each component is independently revertible and
may be its own PR.

## Rollout And Rollback

- Per-tenant setting `VisitorConversation:Mode` with values `LEGACY` and `V2`, default `LEGACY`.
  Migrations are additive and ship dark. `V2` is enabled for the Demo tenant only after
  exact-image acceptance and separate Founder authorization.
- Rollback: set the mode to `LEGACY`; the purge job and the new webhook paths respect it. Data
  already written remains and follows retention.
- No deployment, provider mutation or Demo database action is part of this contract.

## Definition Of Done

Direct executable evidence for every requirement and fitness function; a recorded before-and-after
simulated-customer comparison against Founder-set targets; exact-head aggregate qualification as
the Founder directs; author review; Founder handoff. Completion means a new visitor can be taken
from first message to a handed-off trial through the endpoint and WhatsApp, with outcomes measured,
not merely that code merged.

## Stop Conditions

Stop and ask the Founder if any of the following arises: a need to weaken consent, Stop or
data-rights behavior; collecting a mandatory personal field; a need to enable generative replies,
state a price or promise an outcome; any message to a real phone number from the simulator; a
change to Meta configuration or templates; deployment or provider mutation; a contradiction with
ADR-051, ADR-052 or ADR-053 or an unaccepted amendment to them; public anonymous exposure of the
visitor endpoint; rotation of the phone-subject key while leads exist; a model or provider
outside ADR-029; a conflict with an approved specification beyond the recorded deviations; or any
missing detail that would require the implementer to invent an interface, state, schema or policy.

## Review Records

### Enterprise Architect (INST-004) review, 2026-11-19

| # | Finding | Disposition |
|---|---|---|
| F-E1 | The draft had no capability, driver, claim or ADR trace. | Fixed: Capability, Driver And Decision Trace added; constitutional basis corrected (C-009 added). |
| F-E2 | Lead capture and the evaluation harness are not entries in the capability map; an architect may not invent capabilities. | Recorded as Founder-directed supporting capabilities. Open Decision O-1: Business Architecture authors the capability-map entries. Implementation may not start without that entry or an explicit Founder waiver. |
| F-E3 | The draft relied on ADR-051/052/053 without noting they are Proposed. | Fixed: dependency acceptance clause and stop condition. |
| F-E4 | The draft invented "versioned per-tenant content" parallel to ADR-052's Conversation Policy layers. | Fixed: scripted content is Conversation Policy layers; clients cannot supply policy, prompt or tenant. |
| F-E5 | Visitor versus relationship conversation ownership was undefined, risking a second conversation store. | Fixed: visitor scope is pre-relationship; the relationship conversation owns history after handoff. |
| F-E6 | The future generative responder was unconstrained. | Fixed: seam bound to ADR-019 grounding, ADR-024/029 routing and fixed-text categories. |
| F-E7 | No fitness contract or reversibility. | Fixed: Architecture Fitness Contract F1 to F8 and the per-tenant mode flag. |
| F-E8 | Quality review of real conversations raised a privacy and consent gap. | Fixed: sampling only through the PII-masking pipeline and only with disclosed consent; R016. |
| F-E9 | No build-versus-adopt determination for interactive messages or the harness. | Fixed in boundary decision 5. |

### Solution Architect (INST-005) review and implementation-readiness test, 2026-11-19

| # | Gap that would have forced the implementer to invent | Disposition |
|---|---|---|
| F-S1 | Endpoint paths, identity, idempotency, errors, limits, timeouts and the structured reply were unspecified. | Fixed: Interface Contract. |
| F-S2 | How a web or mobile visitor is identified without an account. | Fixed: server-issued visitor session token; public web exposure disabled by default and listed as an Open Decision. |
| F-S3 | State transitions, START semantics and failure behavior were unspecified. | Fixed: Visitor State Machine and failure matrix. |
| F-S4 | The lead schema, keys, constraints, RLS and retention mechanics were unspecified. | Fixed: Data Contract, including single-replica purge and options validation. |
| F-S5 | The existing destination envelope has no key id, so key rotation breaks stored numbers (E9). | Fixed: envelope `v2` with key version, re-wrap job, rotation stop condition. |
| F-S6 | Inbound button and list replies are rejected as unsupported content, and the adapter sends no interactive payloads (E10). | Fixed: inbound parsing and outbound construction in the Interface Contract and R004. |
| F-S7 | Opening hours and notices were hardcoded and not tenant-configurable (E2). | Fixed: in the Conversation Policy layers (R005). |
| F-S8 | The portal handoff could leak or mis-assign personal data through a forwarded link. | Fixed: Handoff Contract with an opaque single-use reference, non-sensitive prefill, and verified-identity linking. |
| F-S9 | Specification-before-code ordering (ADR-002) and generated client artifacts were not required. | Fixed: R015 and work component 0. |
| F-S10 | No rollout order, rollback, or work-component dependency order. | Fixed: Work Components table and Rollout And Rollback. |
| F-S11 | Channel limits for interactive messages came from secondary sources. | Fixed: limits are configuration, verified against Meta documentation before the renderer is built. |

### Open Decisions (Founder-owned)

| # | Decision | Needed before |
|---|---|---|
| O-1 | Capability-map entries for lead capture and simulated-customer evaluation, or a waiver | Implementation authorization |
| O-2 | Acceptance of ADR-051, ADR-052 and ADR-053 | Implementation authorization |
| O-3 | Retention minimum and maximum (provisional 7 and 365 days) and the default simulation retention | Work component 1 |
| O-4 | Security decision on anonymous web and mobile exposure and abuse control | Any enablement of public exposure |
| O-5 | Security confirmation of the personal-data classification and field protection | Work component 1 |
| O-6 | Evaluation targets (conversion and quality lift over baseline) | Baseline run |
| O-7 | Reply wording approval | Work component 2 content build |
