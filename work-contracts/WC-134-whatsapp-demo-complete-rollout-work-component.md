# WC-134 - Complete WhatsApp Demo Rollout Work Component

## 1. Record Control And Delivery Commitment

| Field | Value |
|---|---|
| Work Contract | WC-134 |
| Authoring office / accountable delivery owner | Platform IT Expert (INST-010) |
| Founder assignment | Current conversation, 2026-11-06: prepare the complete work component for own-number and anyone-on-Demo rollout |
| Status | REPOSITORY IMPLEMENTATION QUALIFIED; PUBLIC/LIVE ACCEPTANCE NOT COMPLETE |
| Baseline reviewed | Main `8cf1e38bd0c45c44dab0ff911f2f8808558aed11`; deployed BP digest `sha256:401545767c9d2546731accbaa6949347a796ef7ff2c8eba402a47f7835dec126` |
| Related owners/contracts | WC-120 conversation; WC-121 provider enablement; WC-133 first contact; WC-123 identity; WC-115 employment; WC-124 data/runtime lifecycle |
| Requirement ledger | [WC-134-requirements.yaml](./WC-134-requirements.yaml) |
| Constitutional basis | C-023, C-026, C-039, C-042, C-059, C-062, C-063; accepted identity, tenant isolation, consent and Stop controls |
| Delivery model | One integrated correction scope and coordinated PR where feasible, followed by exact-image configuration and live acceptance |

The prioritized remaining implementation for batching, offering metering and shared spend is
specified in the [batching, offering and spend work component](./WC-134-batching-offering-and-spend-work-component.md).

**Completion means the customer journey works, not that code merged or a workflow turned green.**
All dependencies necessary for the supported Demo journey are delivery obligations of this component.
Missing configuration, owner decisions, provider actions, operational wiring, test coverage and
deployment evidence stay open requirements with an explicit next action. They cannot be omitted,
relabelled as somebody else's responsibility or treated as a successful partial rollout.

The Founder explicitly authorized current-session implementation and accepted the exact WC-120,
WC-121 and WC-123 source versions listed in the session record. The Founder clarified the required
cross-channel journey on 2026-11-06: WhatsApp is a guest discovery channel as well as an authenticated
customer channel; a first message is not customer registration. Use one dedicated Demo service
tenant for operational isolation, with a distinct channel-scoped guest participant/session per
verified sender. Do not create a customer tenant, WAOOAW account, membership, or employment from
WhatsApp traffic. Keep that guest scope separate from account identity and relationship authority.

The web portal requires login to browse its authenticated marketplace experience, but not completed
customer registration. WhatsApp guests may browse offerings and use an explicitly bounded,
approved agent-preview/interview experience without a WAOOAW account. Trial or Hire from either
channel requires the account and registration flow owned by the web portal/Identity. Web
registration requires a WhatsApp number and a short-lived, single-use OTP requested by the customer
on the registration page. Send that authentication code only through an approved WhatsApp
authentication-template path after the explicit request. The verified number may identify a
completed registration, but number matching or OTP verification proves channel possession only;
it does not authenticate an account session, establish membership/employment, or authorize private
relationship access. Any WhatsApp account/relationship access still requires the separate
authenticated Identity, current-membership, and channel-binding controls. Identity consumes the
OTP; it is never stored in a conversation transcript.

Web, WhatsApp, and future mobile reuse the Business Platform-owned Conversation layer, catalogue
facts, agent/relationship owners, and action semantics. Channel adapters own transport,
authentication/assurance handoff, and rendering only; they do not implement separate assistants or
business truth. Guest discovery/preview state is not a relationship conversation. After an
owner-authorized relationship exists, the customer may continue through the canonical relationship
conversation. Any handoff preserves explicit intent and opaque references; it never copies or
transfers transcript history. The current relationship-only Conversation API therefore has a
required additive guest-session contract gap, tracked in R004/R019; do not improvise a public
relationship endpoint or adapter-owned transcript store.

The participant scope must remain independently enforced for guest context, consent, STOP, budgets,
outbox, delivery status, and provider egress. Account-specific data additionally requires current
Identity session and membership authorization. Account/channel linking does not move or copy
canonical history.

This direction authorizes repository implementation and Docker-based qualification only. It does
not authorize provider or cloud access/mutation, credentials, DNS, deployment, external traffic,
public activation, recurring expenditure, or live acceptance. Those actions remain individually
gated by exact current authority, approved limits, and immutable candidate evidence. The Founder
approved the following public-beta target policy on 2026-11-06: voluntary inbound guest discovery
and bounded text-only preview; no proactive customer messages or alerts, marketing campaigns, or
template initiation; outbound customer messages are direct responses to inbound customer messages
within the free service window; maximum 10 messages per guest per 24 hours,
100 new guest sessions per day, and INR 500 per day combined messaging/model cost; published
service hours 09:00-21:00 IST; stop AI work with a clear limit/closed-hours response when a bound
is reached. The current guest discovery path uses local catalogue lookup and makes no model-provider
call; direct replies carry zero provider-message cost under this Founder-approved policy. Do not
enable a paid model or proactive send path without separate cost instrumentation and approval.
This is a target policy, not live activation or spend authority. Obtain separate exact-candidate
live approval before public traffic. A human-confirmed operator alert route remains a release
requirement; it is not a customer-message channel.
Tests were authored with each story and then executed through consolidated Docker qualification
after implementation. Section 3 records the final repository evidence and the remaining live
acceptance boundary. No new institutional reviewer is invoked without Founder direction. No
direct-main push, self-approval or self-merge is permitted.

## 2. Required Customer Outcome

1. The Founder can message the published Demo number from the approved own number and receive a
   useful reply, continue the conversation, and stop it reliably.
2. Any eligible person who voluntarily messages that number can browse WAOOAW offerings and
   conduct an approved, bounded agent preview without a WAOOAW account, invitation, or seeded
   contact. A verified sender receives only a channel-scoped guest session in the dedicated Demo
   service tenant; first contact never registers a customer or creates a customer tenant, account,
   membership, or employment.
3. Guest discovery remembers only the minimum session context needed for useful, catalogue-grounded
   turns. Trial/Hire intent continues through the web portal's Identity-owned login/registration
   journey; the customer can then verify WhatsApp control by OTP and return to the same conversation
   context without copying history or implying a hire/trial.
4. Existing customers can continue an authorized professional relationship from WhatsApp and Web
   using canonical history. Consequential actions preserve stronger proof and current owner APIs.
5. Delivery, expiry, consent withdrawal, service-window rules, costs, failures and Stop are
   observable and controlled. One user's messages, limits or Stop must not affect another's scope.
6. Demo is available during an approved published operating window, with a working incident route
   and an explicitly controlled global shutdown.

### 2.1 Journey states and channel responsibilities

| State | Web portal | WhatsApp | Shared owner and boundary |
|---|---|---|---|
| Discover | Customer logs in to browse Marketplace; completed customer registration and workspace membership are not prerequisites for published offer details. | A voluntary first message starts guest discovery; no WAOOAW login or registration is required. | Business Platform Conversation layer and current catalogue projection. Guest scope is sender-bound and Demo-tenant-scoped, not a customer Identity or relationship. |
| Preview / interview | Continue the authenticated Guide experience using the same approved public offer and preview semantics. | Ask about an offering and use the explicitly approved, bounded agent-preview capability. | No private customer data, relationship tools, consequential actions, shadow relationship, or claim that a preview is employment. |
| Trial / Hire intent | Preserve selected professional/version, intent, disclosure, and safe return target. | Explain that an account is needed and return a secure portal continuation link bound to opaque intent. | BP preserves intent; clients do not create relationship or evaluation IDs. |
| Account | Identity login establishes an authenticated visitor; if registration is required, complete it in the web portal using currently supported Identity/SSO methods. Mobile is optional for account registration. | Remains a guest channel until Identity binding succeeds; do not collect passwords, SSO credentials, or registration data in chat. | Identity owns account creation, login, verification, assurance, and recovery. Registration alone does not create membership or a relationship. |
| Bind WhatsApp | In an authenticated, sufficiently assured portal session, request linking and approve the displayed WhatsApp number. | Receive a short-lived OTP and submit it to the Identity-owned verifier. The code is not a conversation contribution. | OTP is bound to the portal actor, WhatsApp guest scope, purpose, expiry, attempt limit, and single use. Identity confirms the binding; OTP alone grants no account or relationship access. |
| Trial / Hire completion | Review exact disclosure/terms, complete required registration, and explicitly confirm; BP/owner admission decides the relationship. | Resume the same acquisition context and show status or a secure portal link; no direct employment or payment authority. | Current membership/assurance checks and owner APIs govern every protected read/action. Guest history is not copied into canonical relationship history. |
| Relationship conversation | Use the canonical relationship conversation and authorized projections. | Continue that same canonical relationship conversation after fresh channel authorization. | BP Conversation is canonical; adapters only normalize, authenticate, and render. Future mobile reuses the same owner/API semantics. |

The guest session may preserve an explicit, minimized discovery context across the portal handoff,
but cannot silently merge account identity, expose account-specific data, or become the relationship
transcript. An approved handoff may resume the same guest context; relationship admission creates or
resumes only the canonical owner-authorized relationship conversation. Service consent is distinct
from marketing/template consent.

The own-number pilot is the first acceptance cohort, not permission to stop before public Demo
readiness. Both cohorts must pass before this component is DONE. Public Demo admission is voluntary
service use, not blanket permission for marketing or unsolicited contact.

## 3. Verified Baseline And Open Evidence

| Observation | Evidence / interpretation |
|---|---|
| Runner accepts real work and terminal cleanup succeeds | Environment Deployment run `42178558350`, provider-operation and cleanup PASS. Earlier runner failures are not the current product blocker. |
| BP and dependent Demo apps are Running | Read-only Azure inspection, 2026-11-06. BP minimum/maximum replicas both 1; runtime startup alone does not prove healthy application dependencies. |
| Callback DNS/TLS and invalid-token rejection work | Dedicated callback GET returned HTTP 401. This is not valid-token/provider subscription or delivery proof. |
| Registration/runtime align; credential metadata READY | Run `42178558350`, `whatsapp-operation-42178558350-1/evidence-apply.json`. Metadata does not prove token scope, protected binding correctness or actual send. |
| Messaging is OFF | Callback acceptance, dispatch and provider availability false; conversation enabled flag, authority, policy and template projection settings absent at inspection. |
| One recipient/tenant is enforced throughout runtime | [Capability gate](../src/business-platform/Services/WhatsAppCapabilityGate.cs), [journey](../src/business-platform/Services/WhatsAppJourneyService.cs), [provider adapter](../src/business-platform/Services/WhatsAppCloudProviderAdapter.cs), [tenant scope](../src/business-platform/Services/WhatsAppTenantExecutionScope.cs). Public admission is not a switch. |
| Guest discovery and same-chat routing partially work locally | [Guest-session service](../src/business-platform/Services/WhatsAppGuestSessionService.cs) persists a sender-scoped guest under Business Platform with replay-safe admission evidence; before discovery it sends a fixed Privacy-Notice-linked service-consent prompt and requires a later exact YES with separate Constitutional Engine evidence. [Provider adapter](../src/business-platform/Services/WhatsAppCloudProviderAdapter.cs) resolves its digest-bound AES-GCM reply route only for eligible delivery. An idempotent migration copies legacy provisional rows. BP exposes a transport-neutral [guest Conversation service contract](../src/business-platform/Services/PortalInteractionService.cs) backed by the same participant-scoped portal interaction storage and catalogue used by the web Guide; WhatsApp uses that contract. Consented guests can browse current catalogue projections and use at most three recent turns for catalogue-grounded follow-ups. Web/mobile adapter integration, approved agent-preview behavior, and account linking remain open. |
| Operational alert evaluation lacks production caller | [ConversationOperationsService](../src/business-platform/Services/ConversationOperationsService.cs) is registered, but no production caller/exporter was found in the reviewed source and scripts. |
| Existing notification route failed human receipt check | Azure mobile push reported Succeeded at 07:17:18 UTC; Founder reported Not received. Email test was denied before send because the group has no email receiver. No new alert resource was created. |
| Public-beta target limits are only partly enforced | [WhatsAppGuestTrafficBudget](../src/business-platform/Services/WhatsAppGuestTrafficBudget.cs) and the outbound [WhatsAppTrafficBudget](../src/business-platform/Services/WhatsAppTrafficBudget.cs) persist inbound/outbound guest-message events, enforce ten combined guest messages per rolling 24 hours, the activation-authority tenant-wide rolling-minute limit, and 100 new public guest sessions per IST day, and reserve zero provider cost for direct replies. Reservations are tenant-isolated, idempotent and serialized across activations. The final available combined-message or rolling-minute slot is reserved for a fixed reply that skips catalogue discovery. Daily session-cap exhaustion now creates an idempotent guide-only Conversation notice and a protected-destination outbox entry without storing customer text or admitting a guest session; provider dispatch checks STOP and ordinary service-window/traffic eligibility. This path is build-validated but its focused tests and provider qualification remain pending. Generic WhatsApp delivery rejects templates and non-customer-response purposes; provider egress is limited to the free customer-response window. The guest path is catalogue-only and makes no model-provider calls; any future model call requires metered pricing before enablement. |
| Non-text inbound media handling is incomplete | [WhatsAppJourneyService](../src/business-platform/Services/WhatsAppJourneyService.cs) classifies signed non-text provider messages without parsing or retrieving media content. Public guest sessions receive a fixed text-only explanation through the shared Conversation/outbox path, without persisting the provider media reference or creating a customer transcript turn. Existing relationship contacts receive a neutral fixed limitation as an idempotent SYSTEM contribution through canonical Conversation/outbox, without fabricating a customer text or invoking the professional runtime. Regression cases cover changed-batch replay of a mixed status/text/image webhook, existing-relationship reply idempotency, and a 4096 UTF-16-code-unit Unicode text boundary with rejection of 4097 before any message/outbox effect; execution remains deferred until all stories are implemented. Exact-image qualification remains open. |
| Required web WhatsApp verification is partially implemented | [IdentityService](../src/business-platform/Services/IdentityService.cs) binds a registration OTP to its own destination HMAC, enforces the returned one-minute resend boundary and five incorrect guesses, and serializes confirmation against account completion. Both completion paths reject unverified incomplete registrations. [Migration 73](../infrastructure/postgres/init/73-wc134-required-verified-whatsapp-registration.sql) retires unbound pending codes and unproven incomplete-registration mobile claims; replay preserves newly bound proofs. Registration UI permits corrected-code retries without persisting number/code. Authored API, PostgreSQL, UI, and migration regression cases remain unexecuted under the end-of-stories testing instruction. Docker compilation and web type-check pass. Section 8 records subsequent dedicated template dispatch and Boolean-only registration recognition; authenticated linking, protected provider readback, and final behavioral/live qualification remain release-blocking. |
| Three pilot policy records are now Founder-approved | Constitution `fbeea62b...b202`, interaction API `c5b30ab1...3221`, product acceptance matrix `1c29f7ad...0a5a`; exact source hashes must be revalidated and composition retained durably before installation. Approval does not activate traffic. |
| CI qualification passes but has limited identity evidence | CI `42169059339` catalog receipt PASS in hosted-shadow mode. It is not independently an exact deployed-BP-image/provider acceptance receipt. |
| Private configuration is intentionally inaccessible locally | Storage public access Disabled/default Deny. Use the approved private execution path; do not open the network or export secrets to Codespaces. |
| Runner live fix has recorded stack drift | Three Demo job images updated under explicit exception; stack parameter still old. Reconciliation must preserve key-import app, identities, scaling and unrelated resources. |

The Founder previously reported Meta callback save/messages subscription and an approved Marketing
template. Reconcile this with current provider metadata; do not ask for repeated setup or assume a
negative-token probe proves subscription. No live message exchange is accepted yet.

### 3.1 Final repository qualification evidence

The consolidated WC-134 repository candidate is qualified for Founder review. All commands below
ran in Docker; no host interpreter or virtual environment was used.

| Qualification surface | Result |
|---|---|
| Business Platform | PASS: 2,373 tests; 90.01% line and 80.11% branch coverage |
| Professional Runtime | PASS: 396 tests; 90.90% line and 81.36% branch coverage |
| AI Runtime | PASS: 296 tests; 93.47% line and 80.05% branch coverage |
| Digital Marketing Agent | PASS: 104 tests; 94.98% line and 82.64% branch coverage |
| Billing and offering usage | PASS: 479 tests with 14 intentional integration skips |
| PostgreSQL migration/offering gate | PASS: 72 tests |
| Web quality, build, unit and coverage gates | PASS |
| OpenAPI, protobuf and generated-client specification gate | PASS |
| Real-container REST reconciliation | PASS for every Business Platform lane; final PR-only repairs separately passed 214 Professional Runtime conversation-execution tests and 36 REST validation-control tests without repeating the complete expensive gate |
| Release preflight | PASS: 82 tests |
| Release test lane | PASS: 664 tests |
| Release PostgreSQL, Demo-data and simulator lanes | PASS |
| WC-123 impact/session validation | PASS: 14 tests |
| GOAL-006 Docker Azure CLI end-to-end verification | PASS: image/emulator, extension readiness, stopped-service recovery, database handoff, positive deployment, negative deployment and broker cleanup |

This evidence qualifies repository implementation, migrations, contracts, exact-image integration
and controlled Azure deployment behavior. It does not activate WhatsApp traffic or authorize
provider/cloud mutation, public traffic, recurring spend or customer communication. Full WC-134
DONE remains blocked on protected current Meta readback, independently authorized exact-candidate
activation, actual alert receipt, and successful own-number and eligible-public-sender live message
cohorts. Those actions require separate Founder authority and immutable evidence.

## 4. Complete Requirement And Acceptance Matrix

Every row is mandatory. Tests named below are additions/extensions to existing owner tests, not
permission to create parallel identity, conversation, transport or deployment systems.

| ID | Required outcome and proposed fix | Measurable acceptance |
|---|---|---|
| WC134-R001 | Replace fixed-recipient public admission with sender-bound guest-session resolution. Keep the business app/WABA/sender distinct from customer phone identities. Create a distinct channel-scoped guest participant/session per sender inside the dedicated Demo service tenant; keep the own-number cohort available. | Two previously unseen senders enter without contact seeding; each resolves to a distinct guest scope and canonical reply recipient; wrong business sender/environment and ambiguous/reassigned binding fail closed. No first-contact customer account, customer tenant, membership, relationship, or employment is created. |
| WC134-R002 | Enforce guest participant scope plus tenant RLS across webhook, authority, worker, outbox, delivery status, budget, Stop, and provider egress. Apply Identity session and membership checks only when a guest transitions to account/relationship access. | Concurrent users and status callbacks resolve only to their own scope; a reply is sent only to its canonical recipient; one user's payload, history, budget, OTP, or Stop cannot select another scope. No wildcard/bypass-RLS shortcut or unscoped cross-tenant scan. |
| WC134-R003 | Complete user-initiated guest-session consent, bounded admission, and replay-safe evidence before discovery effects. Treat service and marketing consent separately. Do not perform customer registration on first contact. | A first inbound message creates only a minimal, evidence-backed channel guest session and returns the fixed Privacy-Notice-linked service-consent prompt without storing customer text or performing discovery. Only an exact affirmative reply records versioned consent evidence and enables subsequent discovery; replay, invalid replies, CE failure, and STOP do not bypass the consent gate. No customer identity/account, tenant, membership, relationship, employment, or marketing consent is implicitly created. |
| WC134-R004 | Implement a stateful guest discovery/agent-preview mode on the shared BP Conversation layer, reusing current catalogue/offer facts and approved preview capabilities across Web, WhatsApp, and future Mobile. Specify an additive guest-session API; never create a WhatsApp-owned assistant or transcript store. | Guest can browse offerings and ask useful agent-preview questions without account registration; correction/return/ambiguity preserve only bounded session context; preview has no private relationship data or consequential tools; the same owner projections and semantics are used across channels. BP exposes an additive guest-session service contract; Web/mobile adapter integration and approved preview behavior must be completed before this requirement passes. |
| WC134-R005 | Complete the Web-owned account and channel-binding journey. Web registration requires a WhatsApp number verified by a purpose-bound, single-use OTP sent only after the registrant explicitly requests it. Each challenge is bound to the exact destination; only its own successful confirmation sets the registration match key, and competing pending challenges are retired. A match to a completed registration may identify the number internally but grants no account or relationship access. Trial/Hire requires an Identity-authenticated account and completed registration where required; WhatsApp channel binding remains a separate, authenticated Identity flow. | Registration cannot complete until email, profile, and WhatsApp-number verification are complete. OTP expires after 15 minutes, enforces a one-minute resend cooldown and five incorrect guesses per challenge, is redacted, is delivered only through an approved authentication-template path, and is never persisted as conversation content. Same-key replay causes no resend; registration proof cannot be consumed by account-level verification. A verified-number match is limited to account recognition and cannot bypass Identity session, current membership, assurance, or channel-binding checks. Binding requires explicit relationship-channel consent and a trial-active or active relationship; it fails closed for a stopped guest session or withdrawn channel and cannot itself clear STOP. Wrong-account, replay, expiry, cancellation, and stale membership fail closed. No history is moved or copied and no registration/login alone creates a relationship. |
| WC134-R006 | Wire existing-customer and professional/system responses into canonical outbound delivery. Resolve actual skill/context rather than treating channel name as a skill. Queue intended journey outcomes rather than only returning them in an internal receipt. | Existing relationship inbound reaches the proper runtime; canonical reply and outbox row are committed through the owner; a real reply arrives and appears consistently on Web; progress, assurance-required and Stop outcomes have explicit customer-visible delivery behavior. |
| WC134-R007 | Complete durable provider dispatch/status handling, ordered per-conversation delivery, idempotency, unknown-outcome reconciliation and bounded recovery. Verify all participating service contracts. | Provider acceptance is distinguished from delivered/read; callbacks before/after HTTP response converge; duplicates, worker restart, timeout and lost response cause no duplicate send or lost canonical reply; failures are actionable. |
| WC134-R008 | Enforce inbound plus outbound message counts for the pilot and per-user plus global public-Demo admission/rate/concurrency/spend limits. Bind limits to actual pricing and avoid retry double-counting. | Real PostgreSQL concurrent/replay tests prove ten combined pilot messages is a hard processing/dispatch ceiling with documented Stop handling; activation-authority rolling-minute and daily session caps serialize across senders; session-cap denial yields an idempotent guide-only shared Conversation reply through a protected-destination outbox, stores no inbound customer text, admits no guest session, and is suppressed if STOP is recorded before dispatch; exhaustion yields a controlled outcome and never unknown invoice claims. |
| WC134-R009 | Finish recipient consent withdrawal, provisional STOP, relationship Emergency Stop, operator channel Stop, release/re-consent and expiry semantics. Clarify phrase matching and acknowledgement without weakening a latched fence. | STOP/repeated STOP with queued/in-flight work prevents new ordinary egress; unrelated users continue; operator Stop and expiry contain traffic; resumed authority never silently clears withdrawn consent; acknowledgement policy and any bounded in-flight race are measured. |
| WC134-R010 | Wire queue age, unresolved outcomes, dead letters, privacy/isolation and Stop signals to scheduled evaluation, actual alert delivery, acknowledgement/escalation and missing-signal detection. | Inject each signal safely; detection/response deadlines in the accepted runbook pass; Founder receives a real test notification; absent evaluator/exporter/receiver is itself a failure, not green silence. |
| WC134-R011 | Privately verify Meta app mode, business sender/WABA, callback valid challenge, messages/status subscription, token scopes/expiry, billing/limits, template inventory and API version. Preserve existing verified setup. | Provider-owned metadata and signed real inbound/status events match the current environment; exact least-privilege credential versions work from the workload identity; no protected values appear in logs, artifacts or workflow inputs. |
| WC134-R012 | Support direct replies to customer messages, plus a purpose-bound WhatsApp authentication OTP that a user explicitly requests on the web registration page and that uses a privately verified, Meta-approved authentication template. Alerts, marketing, unsolicited OTPs, and all other template initiation remain disabled. | Direct free-text replies to inbound customer messages are accepted only in the valid free service window. The separate registration-OTP path accepts only the configured approved authentication template and an Identity registration challenge/code; it fails closed when approval/configuration is absent. All generic templates and other outbound purposes still fail closed before provider egress. |
| WC134-R013 | Make unsupported message types and webhook batching safe and understandable. Declare the actual released text/media/locale capability. | Signed public-guest text/image batches process both events; unsupported content for guests and existing relationships gets a fixed explanation through the shared Conversation/outbox path without media retrieval, fabricated customer text, professional-runtime invocation, or transcript persistence; event-level replay survives changed batch composition; 4096 UTF-16-code-unit text with multibyte Unicode is accepted and 4097 is rejected. Exact-image qualification remains required before acceptance; no unqualified media processing is advertised. |
| WC134-R014 | Prove complete live schema/migrations, identity/conversation/outbox foreign keys and RLS, CE evidence, runtime/context/catalogue and connection/dependency readiness. Reuse additive idempotent migrations. | Private preflight on the exact candidate confirms migrations including onboarding, required grants/policies, service transport and budgeted connections; repeat application has zero unintended drift; failure causes no reset or ad-hoc owner escalation. |
| WC134-R015 | Assemble and install the full current authority/policy/template/binding configuration and honest readiness receipts using existing protected operators. Extend closed schemas only as required for public admission. | Independent source-derived receipts cover the whole approved window; exact immutable candidate digest is reviewed and separately approved; readback matches; no placeholder reference, invented expiry, fake tenant or self-approved receipt. |
| WC134-R016 | Qualify operator activation, Stop, rollback and recovery with known compatible artifacts/configuration and containment checks. Make the short pilot window operationally usable. | Preparation/review does not consume most of the pilot window; activation never enables expired authority; failed partial apply closes traffic and old workers; rollback preserves claims/history/consent and does not resend unknown outcomes or restore revoked credentials. |
| WC134-R017 | Provide approved Demo availability, public entry instructions, working number/QR/link, welcome/privacy/limitations copy, business hours or operating window and incident ownership. Prevent scheduled stop/start or full deployment from silently invalidating readiness. | During the published window all required apps/dependencies are healthy; outside it the state is explicit; restart/deployment rechecks authority and registration and cannot silently reactivate; availability/entry information is verified from a second device. |
| WC134-R018 | Complete data/privacy lifecycle for provisional and linked users: minimal collection, protected recipient resolution, retention/erasure/legal hold, logs/telemetry and revoked/reassigned number handling. | Defined data lifetimes and owner deletion/linking behavior are tested; sensitive payloads/identifiers are absent from operational evidence; withdrawal/reassignment cannot expose prior user's history; Demo never uses UAT/Production credentials or data. |
| WC134-R019 | Provide a deterministic local-to-live qualification path bound to exact source, runner, application and configuration identities. Wire new regressions into explicit catalog gates. | Production-DI, real-PostgreSQL and multi-user provider-envelope tests pass; exact published images pass required dependency checks; each changed selector runs in CI; simulated tests are not presented as live Meta delivery. |
| WC134-R020 | Reconcile delivery infrastructure and operational source-of-truth drift without unrelated mutation. Include alerts and new configuration in durable ownership. | Reviewed runner-stack plan changes only approved targets; key-import and unrelated resources unchanged; subsequent deployment/status/cleanup operate on consistent pins; monitoring/configuration can be reproduced without undocumented session files. |
| WC134-R021 | Execute own-number and public-Demo end-to-end live acceptance, including browser continuity, outages and real cost reconciliation. | Both acceptance scripts in Section 7 pass with timestamped redacted evidence, observed delivery, Stop and containment; no remaining requirement is called complete using only workflow success. |
| WC134-R022 | Close all newly discovered dependencies before release and publish one honest completion matrix/runbook. | Every R001-R021 has accepted evidence; discovered issues are mapped to a row or added before freeze; no unresolved blocker is hidden behind an exclusion, another component or a green parent gate. Founder reviews rollout and remaining operational risk explicitly. |

## 5. Implementation Surfaces And Integration Rules

Use the existing Business Platform webhook, phone identity/onboarding, Portal interaction,
conversation context, contribution/outbox, provider credentials/adapter, traffic budget,
tenant interceptor and operational signal owners. Extend their contracts coherently, including
API/OpenAPI, generated consumers, options, provider/activation schemas, SQL, fixtures, CI selectors
and runbooks. No parallel contact database, public business API, identity token or conversation store.

Particular coupling that must be resolved together:

- Business sender identity is not a customer recipient. Public routing must not read the one pilot
  telephone from the global provider secret and use it as every outgoing destination.
- Derive public sender identity with its own pinned, identity-stable HMAC key. Meta App Secret
  rotation is for callback verification and must not silently create new sender identities; key
  replacement requires an approved binding-preserving migration.
- Resolve each authenticated provider subject through Identity before entering tenant-bound work.
  Background leases and delivery-status correlation need the same canonical scoping; do not solve
  multi-user processing by unscoped scans or relaxed RLS.
- Keep pre-employment discovery distinct from employed-professional execution. Skills, current
  context and assurance come from their existing authoritative owners, not the channel label.
- Shared history, response generation and canonical outbox publication must recover atomically or
  through proven idempotent steps. Provider acknowledgement alone is not delivery.
- Stop, limits and consent must be rechecked immediately before effects. Marketing, account
  completion and consequential employment actions are distinct decisions.
- Unsupported capabilities require truthful customer behavior, not repeated webhook errors.
  Media processing must not be enabled without its full existing safety/data/provider requirements.

Do not rebuild runner images for ordinary application edits. Remove stale unused image artifacts
before any authorized new build, preserving referenced images/containers/volumes. Use catalog-owned
focused execution, then dependency-complete milestones and one final exact-candidate qualification.

## 6. Dependency-Ordered Delivery And Decision Bundle

| Milestone | Work and exit condition |
|---|---|
| M0 - Baseline and decisions | Confirm live source/image/configuration, inventory existing evidence, reproduce gaps, and verify the Founder-approved public admission/assurance target policy. Collect any remaining authority decisions once. |
| M1 - Guest session and routing | R001-R003, guest participant/binding/activation schema and migration design; prove two-user isolation and replay before enabling any sender. Use the dedicated Demo service tenant, not a customer tenant, and never register an account from first contact. |
| M2 - Shared discovery and account bridge | R004-R005, R006-R007, R012-R013; close the additive guest-session API gap, prove useful preview turns and portal registration/OTP handoff, then prove canonical relationship continuity. |
| M3 - Controls and operations | R008-R010, R014, R016-R018; prove budgets, Stop, alerts, dependencies, privacy and containment on the integrated candidate. |
| M4 - Immutable delivery | R011, R015, R019-R020; freeze tested candidate, author review, one coordinated PR where feasible, Founder merge, attested publication and protected zero-traffic deployment/preflight. |
| M5 - Own-number acceptance | Assemble/review candidate, separate exact-digest approval, bounded live test, operator Stop and cost/evidence reconciliation. Fix any finding and rerun affected closure; do not call public rollout ready. |
| M6 - Open Demo acceptance and release | Independently approved public operating limits/window; two-user and new-user live acceptance; publish verified entry path, runbook, monitoring ownership and complete ledger. |

The Founder-approved public-beta target is: any voluntary inbound sender; guest discovery and
bounded text-only preview without registration; no proactive customer messages/alerts, template
initiation, or marketing campaigns; direct replies only within the free service window; ten
combined messages per guest per 24 hours; at most 100 new guest sessions per day; INR 500 maximum
combined messaging and model spend per day; and published service hours 09:00-21:00 IST. At any
message, session, or spend limit, stop discovery/model processing and return a clear bounded
response where the approved free reply path permits it. The current guest path performs local
catalogue lookup without model-provider calls and reserves zero provider-message cost for replies.
Before enabling any nonzero-cost provider/model path, instrument actual unit prices and prove the
INR 500 ceiling; public activation remains off until per-minute/concurrency controls and all
remaining limits are qualified. This policy approval is not provider, deployment, live-traffic, or
spend authorization.

The remaining decision bundle must state: isolated identity/tenant admission policy;
assurance/linking path; verified per-message/provider/model pricing; incident owner and delivered
alert receiver; consent/retention/re-consent; supported text/media/locales; and exact
activation/rollback artifacts. The current own-number approval remains 30 minutes, ten combined
messages, INR 10, no other customers. Do not extrapolate it to public traffic.

An existing alert proposal estimates roughly INR 314.25/month for one conservatively costed
one-minute log rule and one monitored series, excluding tax/ingestion/other rules. This is neither
approved expenditure nor a complete alerting design. Recalculate the integrated monitoring and
application/provider operating cost before seeking deployment approval.

## 7. Mandatory Executable Acceptance

### A. Own-number pilot

1. Preflight exact deployed image/configuration, protected bindings, provider subscription,
   dependencies, migrations, current receipts, delivered alerts and verified Stop path.
2. Review exact activation bytes and obtain independent Founder approval; open only the approved
   30-minute/ten-combined-message/INR-10 window. Fit the approved script within those limits;
   obtain an explicit amended test allowance before any additional live messages.
3. Use a user-initiated Hello for the minimum path. If testing the separately approved Marketing
   invitation, verify locale/body/version and count it within the authorized allowance.
4. Observe signed callback, evidence-backed admission, canonical inbound/guide/outbox, actual
   provider submission and actual recipient-visible reply/status. Verify a useful second turn.
5. Verify the approved Stop test, no later ordinary send, operator shutdown, exact message/cost
   reconciliation and zero unintended residual processing. Simulated edge cases do not consume
   unauthorized live traffic.

### B. Anyone-on-Demo cohort

1. Under separately approved public limits/window, use at least two consenting previously unseen
   numbers concurrently, with no account/contact/relationship seeding or marketing prerequisite.
2. Browse offerings and conduct approved agent previews in guest scope; prove per-sender context,
   recipient delivery, distinct limits/STOP, no private-data access, and no fabricated relationship.
3. Exercise return visit, portal account registration with explicitly requested WhatsApp OTP,
   verified-number recognition without account-authority escalation, login, OTP channel binding, preserved
   Trial/Hire intent, Web continuity, and an existing relationship. Consequential actions require
   the existing stronger assurance and owner admission path.
4. Verify one user's Stop and quota cannot stop or spend another's allowance; verify global cap
   and shutdown. Test service-window/template behavior and unsupported content with consent.
5. Exercise provider delay, duplicate/status ordering, process restart, dependency outage and alert
   delivery using safe controlled faults and a preapproved message/cost budget. Reconcile all
   accepted/unknown/delivered outcomes; do not blindly resend.
6. Reconcile actual charges and retained data, publish availability/support details, and obtain
   Founder release acceptance against the complete ledger.

### Evidence rules

Record exact commands and results, candidate/configuration digests, source/run IDs, test selectors,
message correlation digests, timestamps, state transitions and real delivery observations.
Keep protected identifiers/content/secrets inside approved private stores; publish redacted proof.
No synthetic tenant, test fixture, fake receipt expiry or guessed template version is live evidence.
If validation cannot access the private plane, execute through existing sanctioned private
orchestration. Do not weaken network rules or reuse an unrelated identity to make a check green.

## 8. Failure, Rollback And Completion

### Registration verification implementation checkpoint

The dedicated registration-only WhatsApp dispatcher is implemented with protected Authentication
template readback, exact ID/name/API locale and pinned-account checks, Copy-code BODY/button
parameters, and a shared append-only message/rate/spend reservation before egress. This does not
enable generic conversation templates or account-level OTP initiation. The challenge and request
idempotency record are committed before sending; durable delivery state prevents replay from
resending unresolved effects or consuming an unsubmitted proof. Outcome persistence restores
transaction-local actor context after egress. The UI distinguishes replaying an unresolved request
from an explicit new-code request; the server still enforces the resend cooldown.

Protected candidate assembly accepts optional `registration_verification` metadata containing
`TemplateId`, `TemplateName`, `Locale`, and `ApprovalReference` only with the explicit
`AllowRegistrationVerification` authority permission. The configuration digest includes those
fields, and the complete candidate still requires independent approval. Registration-only
deployment, legacy activation, and operator Stop explicitly disable the OTP path; a later activation
must opt in again. The reservation table's `outbox_id` is the shared durable egress identity:
conversation sends use their outbox UUID and registration sends use their challenge UUID.

Regression cases cover template rejection/malformed readback, recipient/account/authority changes,
BODY/button payloads, durable interrupted/failed dispatch, explicit UI recovery, protected
configuration and mixed reply/OTP reservation races under PostgreSQL RLS. They are authored but not
executed yet. Host and pinned Docker compilation pass with zero warnings/errors; targeted Python
lint/format and web type checks pass. These are static/build results, not integrated test evidence.

The Founder reported Authentication template `waooaw_registration_otp`, ID
`1476143084372706`, as Active - Quality pending. This is setup evidence only: the exact API locale,
protected approved readback, pricing/traffic authority and actual delivery remain unverified.
Production settings remain disabled with no locale or approval reference. The account-association
implementation checkpoint below does not complete relationship channel attachment or live acceptance. No cloud
mutation, provider read/send, live continuity, or release readiness is claimed.

### Registration recognition and protected public-admission checkpoint

Signed inbound sender handling now supplies the normalized number transiently to the guest service.
Only a consent-confirmation response that passes operating-hours and traffic checks performs the
Identity lookup. Keyed/versioned match candidates enter a bounded Boolean-only database routine;
the routine requires a completed, verified registration and a submitted/consumed proof for the same
destination. A dedicated non-login, non-superuser, non-bypass-RLS principal owns it; the ordinary
application role cannot scan other actors' registrations or assume that principal. Temporary
migration memberships and schema CREATE privileges are withdrawn. Principal handoff preserves this
routine owner, auth preview applies the migration, and schema verification admits only the exact
dedicated SELECT policy without weakening the existing actor policy.

A recognized number receives truthful registered-but-unlinked guidance after consent. It remains
outside private account/relationship history; no session, membership or channel link is inferred.
Recognition failure remains an explicit dependency failure with replay-safe provider-claim recovery.
STOP, unsupported messages, closed-hours replies and limit notices bypass recognition. Regression
cases cover actual PostgreSQL RLS/permissions, repeat migration, key rotation, mismatched and
unsubmitted proofs, production-DI registration completion, signed consent recovery and STOP during
an Identity-recognition outage. Author review tightened paired-array expansion to explicit
`ROWS FROM` and rejects unintended grantees of the dedicated recognition role, not just inherited
privileges held by that role. Authored regressions include empty, unequal, null, multidimensional and
over-64 candidate arrays, unsafe role attributes and an application-role membership grant. Execution
remains deferred.

Protected candidate validation now accepts public admission only as an explicit Boolean permission
alongside guest admission and a pinned sender pseudonymization key. Registration-only setup installs
the exact optional key version but cannot activate public traffic. Registration, legacy activation,
Stop and Terraform deployment explicitly close omitted guest/public/OTP permissions, preventing stale
environment values from preserving prior access. Candidate approval remains exact and independent;
no public activation is performed. New operator regressions are authored, not executed.

Static/build evidence for this checkpoint (not behavioral or live acceptance):

- `dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --no-restore -warnaserror`
  passed with zero warnings/errors.
- The pinned Docker runner command below passed with zero warnings/errors; its workload-verification
  notice did not fail compilation.
  ```sh
  docker compose --project-name waooaw-wc134 --profile test-dotnet run --rm --no-deps --pull never test-runner-dotnet sh -c 'mkdir -p /tmp/nuget-packages && cp -a /opt/nuget/packages/. /tmp/nuget-packages/ && export NUGET_PACKAGES=/tmp/nuget-packages && dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-recognition -warnaserror'
  ```
- `ruff check scripts/wc120_whatsapp_activation.py scripts/wc133_whatsapp_operations.py scripts/wc124_db_provisioner.py tests/pipeline/test_wc120_whatsapp_activation.py tests/pipeline/test_wc133_whatsapp_operations.py tests/pipeline/test_wc124_db_provisioner.py`
  passed.
- `sqlfluff parse infrastructure/postgres/init/74-wc134-whatsapp-registration-recognition.sql --dialect postgres --format none`
  passed; existing root configuration emitted deprecation/unknown-rule warnings. This parser does not
  substitute for executing the migration or checking PostgreSQL privileges.
- `bash -n scripts/run_auth_preview.sh` and `git diff --check` passed.

### Authenticated account-association implementation checkpoint

The owning portal actor can start, explicitly approve, inspect and cancel a WhatsApp account-link
challenge. Production relational calls require actual issuer-qualified actor context, current owner
membership and completed registration. BP selects or validates the caller-owned consumed, submitted
destination-bound registration proof; an arbitrary proof UUID or client-supplied number grants
nothing. Registration-row locking serializes actor idempotency, and link-row locking serializes
approval, cancellation, expiry and confirmation.

Approval returns an AES-GCM protected `LINK ...` instruction with independent purpose-derived key
material. Its encrypted actor/membership snapshot is revalidated against current authority; it is
not itself current membership. Confirmation requires the exact fresh signed message after approval,
the exact verified destination and nonempty constitutional evidence before marking `Linked`.
Same-message replay is inert, another message cannot reuse a completed challenge, and cancelled,
expired, wrong-number, wrong-account, revoked-proof and stale-membership cases fail closed.
Post-evidence proof reads bypass EF tracking so a revoked proof cannot be accepted from a stale
tracked entity. Evidence outages leave the challenge pending and the provider event recoverable.

The same consented, traffic- and hours-gated control path handles existing relationship-bound
contacts; a withdrawn channel or relationship Stop fence denies the instruction. Neither valid
instructions nor malformed `LINK` whitespace variants become customer conversation turns or runtime
input. Replies are guide-only contributions in the shared BP Conversation store. Association
creates no portal session, employment, relationship channel binding, private access or history move.
Migration 75 adds confirmation/cancellation evidence, expires legacy unproven `Linked` labels and
validates the evidence constraint instead of accepting legacy labels as verified associations.

The same-origin authenticated BFF uses the generated Identity client and existing shared
authority-change limiter. The owner/verified-number profile surface requires explicit approval,
shows only a masked number and ephemeral instruction, retains command keys after uncertain
results, distinguishes fresh-sign-in requirements from ordinary denial, and cancels a pending
server challenge before offering a replacement. No browser storage, URL credential or automatic
clipboard action is added.

Authored regressions cover real-PostgreSQL application-role registration/proof isolation, production
DI, wrong sender, membership revocation, migration retirement/replay/validation, explicit expiry,
cancellation/evidence failure/replay, key rotation/retirement, malformed tokens, signed envelope
recovery, non-retention and Stop/closed-hours precedence for guest and relationship-bound contacts.
Webhook ingress and capability checks share an injectable clock with guest budgets; the signed
PostgreSQL fixture uses deterministic open/closed instants rather than depending on wall-clock
service hours. Production defaults remain the system clock. These tests are not executed yet,
per the Founder instruction to wait until all stories are implemented.

Host and pinned Docker compilation passed with zero warnings/errors; web TypeScript checks passed.
The pinned build used:

```sh
docker compose --project-name waooaw-wc134 --profile test-dotnet run --rm --no-deps --pull never test-runner-dotnet sh -c 'mkdir -p /tmp/nuget-packages && cp -a /opt/nuget/packages/. /tmp/nuget-packages/ && export NUGET_PACKAGES=/tmp/nuget-packages && dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --artifacts-path /tmp/artifacts/wc134-linking -warnaserror'
```

Compilation is not behavioral qualification. Remaining guest-preview/shared adapter, canonical
runtime response, lifecycle/operations stories, exact Meta locale/protected readback, final Docker
tests and both separately authorized live cohorts remain delivery obligations. Traffic remains off.

### Canonical relationship-skill routing checkpoint

Ordinary relationship WhatsApp text no longer submits the transport name `WHATSAPP` as a runtime
skill. The shared BP Conversation owner resolves accepted, applicable, currently granted/constrained
skills. A single candidate is used; with several, a still-authorized last customer skill from the
same environment and canonical relationship supplies shared Web/WhatsApp context. Missing or
ambiguous context fails explicitly instead of choosing an arbitrary skill. Existing actor-scoped
accepted-send idempotency retains the original skill on retry without restoring authority for a new
message; normal mandate resolution still checks the exact admitted runtime binding and authority.

Where the canonical outbound owner is available, missing skill selection now commits a fixed
system instruction to choose the current task in the secure portal, without customer runtime
input or professional execution. Replay retains that outcome; repaired owner context applies to a
new message, not retroactively to the denied one. Without that owner, selection conflicts release
only the owned nonterminal provider claim and return an explicit 409. Additional authored cases
cover shared Web context, ambiguity, retired context, revoked authority and caller-bound accepted
send replay. Execution remains deferred; R006 remains blocked.

### Canonical journey-reply implementation checkpoint

Relationship progress and existing assurance-required outcomes now use the same canonical outbound
owner as unsupported-content guidance. Progress commits one system `INFORM` turn and never also
starts professional execution. Owner context resolves against the current workspace version;
system notices no longer require a fictitious `1.0` workspace version.

The canonical system message, `message.completed` timeline event, WhatsApp outbox row and
idempotency outcome commit in one transaction. Journey stage and confirmation state persist before
that commit. A retry after canonical commit but before provider-claim completion recovers the exact
stored text/status/stage rather than recalculating progress, creating a duplicate message or
changing the request digest with a newer ingress timestamp. Provider identity/payload checks still
precede recovery. Evidence remains `PENDING`; queue acceptance is not provider delivery.
Non-cancelled relationship-processing failures now release only the owned nonterminal provider
lease, matching guest ingress; cancellation/crash retains lease-expiry recovery. Authored signed
PostgreSQL coverage injects owner-context failure and retries the same event immediately.

Authored regressions cover progress without execution, tier-2/3/4 guidance, replay, current workspace
versions, canonical event payloads, signed-envelope PostgreSQL selection guidance and repair with a
new message, interrupted provider-claim recovery, and a canonical progress-to-outbox-to-provider
adapter round trip with exactly one mocked HTTP submission. Host and pinned Docker compilation pass with
zero warnings/errors. Behavioral execution remains deferred until all stories are implemented.
These fixtures use a runtime stub; they do not prove professional response generation or delivery.

Stop and end-session outcomes still terminate/revoke through their owners and are not ordinary
outbound acknowledgements: the hard stop/eligibility fence is not bypassed to send them. Their
required customer-visible acceptance policy remains open, alongside production runtime-to-BP
response ingestion, actual provider delivery and Web/live cross-channel continuity. No live send,
provider/cloud mutation, activation or readiness claim has occurred.

Author review also closed a destination fallback gap: a relationship outbox naming another sender
may not use the protected pilot number. Without a sender-bound encrypted destination, egress now
fails explicitly before provider traffic or budget reservation. The authored regression verifies
that denial. This does not enable public relationship replies; their authenticated destination
resolution and independent end-to-end acceptance remain required.

### Runtime execution-handoff implementation checkpoint

Author review found that BP assigned a random execution reference while PR named the same accepted
request with an actor/tenant/relationship/conversation/key-bound UUID-v5. The HTTP gateway ignored
PR's body, so HTTP success did not prove a usable, correlated execution acknowledgement.
New BP execution records now use PR's existing UUID-v5 namespace and exact naming tuple. Previously
persisted local references are not rewritten: their original request key still derives the correct
runtime identity on retry. No tenant, membership or execution authority is granted by an ID.

The gateway requires the existing `202` acceptance or `200` replay shape and validates schema,
runtime/conversation/message correlation, required fields, timestamps, replay semantics, allowed
state and terminal reason. Empty, oversized, malformed or duplicate-member acknowledgements fail
explicitly; the body is bounded to 16 KiB. Caller cancellation remains cancellation rather than
being relabelled as a runtime failure. A returned terminal replay is not yet projected as BP
completion: durable event ingestion remains required.

BP send replay now reads current canonical message/execution state, including concurrent-send
recovery, rather than returning a stale stored acceptance snapshot. Failed retries refresh their
stored unresolved outcome and failure event. Signed WhatsApp retries use that current failure to
invoke the Conversation owner's retry path with the same message, execution and provider-derived
key; a failed retry leaves the provider claim recoverable and is not labelled accepted. The retry
entry rechecks the hard Stop fence. Authored PostgreSQL coverage exercises two dispatch failures,
repair and exact-message replay with one canonical execution. This is a stubbed dispatch proof,
not real runtime unknown-outcome acceptance; the persisted-mandate checkpoint below closes the
local exact-request gap but not durable runtime-status/stream or live reconciliation.

PR's workflow now applies valid completed/failed signals to its state and terminal wait condition,
and marks started/response events RUNNING. Late ordinary events cannot overwrite a terminal state;
the dedicated Emergency Stop signal still preempts it. Inconsistent terminal data and attempts to
bypass dedicated Stop/cancel signals append an explicit reconciliation-required event instead of
claiming completion.

Authored .NET regressions cover the Python UUID-v5 interoperability vector, actor/key separation,
persisted send/replay identity, valid acknowledgement and legacy retry, terminal replay, malformed
success shapes and caller cancellation. Authored real-workflow unit regressions cover completed/
failed closure, invalid-state reconciliation and Stop precedence. These are not behavioral test
results: Founder reconfirmed on 2026-11-07 that tests run only after all stories are implemented.
Host and pinned Docker compilation pass with zero warnings/errors; Ruff, Python syntax,
requirement-ledger binding and whitespace checks pass. Runtime text generation, recoverable stream ingestion,
owner-confirmed cancellation, canonical response projection and both live cohorts remain open.
Existing traffic remains off; deployment must reconcile/drain old execution responsibility before
activating the changed workflow. R006 remains BLOCKED.

### Persisted mandate replay-authority checkpoint

The existing OperationalMandateSnapshots already persist the original runtime mandate. Reuse now
passes through current membership, relationship lifecycle/Stop, active admission/runtime binding,
applicable accepted skill authority, active verified goal, contract and Decision Space checks before
returning that snapshot. Reconstructed current authority must match the stored mandate digest after
normalizing only its original mandate ID, deadline and CE evidence references. Snapshot identity,
binding IDs, digest, deadline and nonempty CE evidence must also agree. Changed role, runtime
policy, contract, context/configuration/goal revisions or authority fail closed.

Successful replay returns the original mandate unchanged: no new snapshot, deadline extension,
replacement CE identity or divergent runtime body. Expired mandates cannot start or renew work
through retry; status/event reconciliation of already accepted work remains a separate obligation.
Empty CE evidence cannot mint or replay a mandate. Skill applicability is checked in both initial
resolution and replay, matching the canonical channel-selection boundary.

Authored resolver regressions cover byte-identical replay/no renewal, current-authority revocation,
role/contract/runtime/Decision Space drift, snapshot evidence/digest corruption and expiry.
An authored integration of the real resolver and real HTTP gateway simulates a lost accepted
response and verifies the exact original JSON body, runtime ID and key on the replay response.
It uses in-memory owner data and mocked HTTP, not real PostgreSQL/Temporal or provider delivery.
Behavioral tests remain deferred per Founder; static compilation is not acceptance.

### Confirmed runtime-cancellation checkpoint

The BP HTTP gateway now sends the existing private PR DELETE operation using the original
actor-scoped runtime execution identity and a fresh scoped BP assertion. Current relationship
access, original actor membership/role and nonempty CE cancellation evidence are checked before
dispatch, including rechecks after evidence. Cancellation does not mint a mandate or renew its
deadline; original execution identity is reconstructed from durable SEND ownership.

The same bounded/correlated acknowledgement reader validates start and cancellation outcomes.
Only a confirmed CANCELLED result or an existing terminal replay can settle cancellation. Runtime
partial/completion reason/timestamp are preserved, rather than setting partial true unconditionally.
A completion or failure racing cancellation is projected as that outcome, not relabelled cancelled.
For both Start and DELETE, HTTP 423 or a confirmed STOPPED replay propagates Stop;
a missing/unbound/nonterminal cancellation reply fails.
The configured command deadline also bounds receipt-body reads after successful headers; caller
cancellation remains cancellation rather than being translated into an unavailable runtime.

BP changes message, execution, canonical event and cancellation idempotency only after that
confirmation. Relational persistence uses a serializable transaction with execution/message row
locks and state reload; late confirmation cannot overwrite a persisted Stop or inconsistent terminal
state. Failed/uncertain remote cancellation leaves local state and cancellation idempotency intact
for same-key reconciliation. Timeline/evidence/provider delivery are not inferred from cancellation.
An unresolved start failure without a confirmed terminal reason remains cancellable through PR,
without repeating Start. Confirmed runtime failure replays as terminal rather than restarting the
same execution. Cancellation and Stop cannot be retried as new work; a retry-time Stop records the
same stopped outcome as initial dispatch, instead of being downgraded to ordinary failure.
That record uses the existing SQL/API vocabulary: FAILED delivery, STOPPED processing,
EMERGENCY_STOPPED completion and stop.applied, preserving existing partial content flags.

Authored gateway/service regressions cover exact DELETE identity/assertion, partial false/true,
terminal completion/failure replay, unavailable or unbound responses, no mutation on remote failure,
same-key replay, membership revocation during evidence and Stop winning a late confirmation.
Additional authored cases cover cancellation after a lost start acknowledgement, terminal-failure
retry, Stop during redispatch, stalled post-header bodies and caller cancellation during body reads.
The signed PostgreSQL fixture also authors failed cancellation followed by same-key success/replay
through the real relational transaction path with a runtime stub. It now adds the relevant
production message-delivery/completion, execution-completion and event-type CHECK constraints to
its EF-created schema and authors initial Stop persistence against those constraints. This is not
full production RLS/DI or real runtime concurrency qualification. Behavioral execution remains
deferred until all stories are implemented; production-DI/real-PR cancellation and live acceptance
remain unqualified.

### Verified public relationship-destination checkpoint

Signed provider ingress now retains only an encrypted, sender-digest-bound destination and its
provider-message timestamp for an already attached relationship contact. This path requires the
internal signed-envelope handler's transient verified phone value, an active channel binding and
an unstopped contact/relationship; a direct proof call or browser-provided hash cannot install a
destination. Older/equal provider timestamps cannot replace a newer route. STOP/end-session
instructions do not refresh it. The verified timestamp is an optimistic concurrency token: a stale
reader cannot overwrite a newer committed route and instead releases its provider claim for retry.
Migration 76 adds nullable fields and a paired-value CHECK without
backfilling unverified legacy numbers, resetting data or expanding database privileges.

Relationship provider egress resolves this destination through the existing outbox owner, requiring
current active channel and matching active participant role, consent, service window and a fresh
destination timestamp. It decrypts only with the protected sender key and exact outbox sender digest.
Absent public destination cannot fall back to another person's configured pilot number. Original
pilot-only routing remains supported for the matching configured pilot. Destination replacement,
membership/channel revocation and expiry during protected reads fail closed on the final egress
recheck.

The capability gate accepts other well-formed sender digests only under independently enabled
public-Demo authority in its exact tenant. Provider reservations now bind the actual outbox sender
digest rather than substituting the pilot digest; the reservation still consumes the same global
activation budget and requires the owned DISPATCHING lease.

Authored provider regressions cover exact public recipient/text, missing/expired/future/tampered
destinations, route replacement and participant/channel revocation during protected reads,
pilot-only denial and no wrong-pilot fallback. A real-PostgreSQL stale-reader regression authors
concurrent route replacement protection. The signed PostgreSQL fixture authors captured
destination encryption and runs migration 76 twice; the forced-RLS budget fixture adds a public
sender contention case sharing the pilot activation ceiling. These tests remain final-only.
This does not create a relationship ChannelBinding, authorize account attachment or complete
privacy/retention/reassignment, real runtime response production, provider delivery or live acceptance.

### Shared guest-control and late-Stop checkpoint

The shared fixed-notice owner now explicitly admits the existing registered-number acknowledgement
and account-association success/denial notices. Account-link text remains a fixed, centralized
Identity instruction outcome, not an arbitrary assistant reply or customer/runtime transcript.
Previously those valid paths were rejected by the fixed-notice allowlist after their owner action.
All ten admitted fixed notices have authored guide-only/replay regressions; unknown text still fails.

The shared guest Conversation writer rechecks any WhatsApp guest's current Stop/admission/consent
evidence and notice version before persisting customer content. It uses the same sender advisory lock
as guest ingress, rereading state after acquiring it, before its own interaction lock. Queueing likewise
checks current admitted sender state under that lock and verifies the stored canonical GUIDE message,
sequence and exact content rather than trusting caller-supplied text. A late Stop cannot be bypassed
through a direct shared-owner call, stale guest object, fabricated reply or delayed queue operation.
Participant-scoped portal discovery without a WhatsApp guest record retains its existing behavior;
this is not completion of Web/mobile guest adapter parity.

Admission and service-consent evidence requests now execute outside the sender database lock.
After evidence returns, ingress reacquires the lock, reloads Stop and current authority and only then
projects admission/consent. A concurrent STOP can latch while CE is slow; late evidence cannot revive
a stopped guest. The original pending admission/evidence inputs remain durable for retry. Existing
consent-notice identity is rechecked before installing consent, and unsupported media cannot consent.
Older/equal inbound timestamps and stopped sessions no longer refresh an existing guest destination.

Authored real-PostgreSQL regressions pause admission/consent evidence and verify independent STOP
completes before evidence release, with no late admission/consent/message/outbox. Another regression
holds the sender lock while stopping and checks shared-writer/queue rejection after the wait.
Direct-owner consent/version/Stop and canonical queue input/replay tests are also authored. For a
stale notice version, a fresh notice resets the current consent only under the sender lock and stores
the previous consent reference in tenant-scoped history; a later exact YES can record fresh evidence.
Renewal and history-migration regressions are authored but not executed. Notice queueing does not prove
delivery. These tests remain final-only; consent expiry, retention/reassignment and measured live
Stop races are still open.

For linked relationship contacts, a trimmed, case-insensitive message exactly equal to `STOP`
withdraws WhatsApp recipient consent only. It does not stop the employment relationship, returns no
WhatsApp acknowledgement, and issues no further internal session token. Incidental STOP wording is
not a Stop command. The separate exact `EMERGENCY STOP` command invokes the relationship Stop owner;
once recipient consent is withdrawn, no ordinary reply is sent even if the relationship Stop succeeds.
This phrase split is locally implemented and covered by authored regressions; its acknowledgement,
re-consent, operator-release and in-flight delivery policies remain unqualified.

### Conversation workload-identity checkpoint

Start, Cancel and the existing PR stream now require ADR-046 mutual TLS plus the shared signed,
single-use BP delegated envelope. The BP named client retains its workload certificate and exact
PR SPIFFE validation, rejects plaintext and redirects, and loads credentials independently of
workspace endpoint configuration. The legacy Conversation JWT secret cannot authorize these
operations. Unrelated PAAS/voice JWT routes are unchanged, not declared migrated.

The envelope binds the registered operation/route/audience, original runtime/message/conversation,
actor/role/tenant/relationship, CE decision reference, correlation and idempotency. Start sends
the shared canonical JSON representation verbatim and signs that byte digest; PR hashes received
bytes without altering Unicode escaping, then binds the typed original mandate. Cancellation and
stream reads bind the stored original message/execution; stream envelopes also bind the cursor.
Retries use fresh envelope IDs without changing the original mandate or command identity.
Missing/expired/replayed/drifted workload authority fails before protected mutation. Missing
workload material degrades PR readiness; listener/configuration deployment remains unqualified.

Authored production-router tests use asymmetric delegated signatures and transport-owned peer
certificates (not an authorization override) for Start/replay/Cancel/stream, absent/foreign/cross-
environment peers, old JWT rejection, body drift, replay, message/execution/decision/cursor drift
and exact registry grants. Existing execution-state tests explicitly isolate authentication; they
are not provider/production-auth evidence. BP tests cover canonical Unicode wire bytes, fresh
retry envelopes, absent credentials/plaintext denial, factory certificate/redirect controls and
production DI. These behavioral tests remain deferred until all stories are implemented.
Runtime response generation, durable BP event ingestion, relationship attachment, combined
limits/privacy/operations and both live cohorts remain delivery obligations.

### Shared rolling-minute quota checkpoint

Guest traffic, relationship provider replies and requested registration OTP reservations now
share the same tenant-wide budget lock and rolling-minute counter. Previously guest events and
provider reservations had independent minute ceilings, and relationship dispatch did not take
the guest/OTP lock. Mixed channels could therefore consume more than the approved tenant rate.
The common count includes guest inbound/outbound events and non-guest provider/OTP reservations,
including recent earlier activations. It excludes the duplicate cost reservation for a guest
outbox: guest provider dispatch writes its traffic event and cost row atomically. Tenant isolation,
strict time boundaries, and unchanged-activation checks remain enforced. The final guest notice
slot now observes that shared capacity; no new proactive or paid send path is enabled.

Authored coverage checks relationship/OTP contributions, no double counting of a guest dispatch,
foreign-tenant exclusion and the exact cutoff. Forced-RLS PostgreSQL contention now includes mixed
guest inbound, relationship replies and requested OTPs, with actual guest migration replay and
both append-only ledgers. Behavioral execution remains deferred. Activation-total pilot inbound
accounting, metered model cost, privacy/lifecycle, alerts and exact-provider/live acceptance remain
open requirements, not exclusions or a claim of completed R008.

### Containment and completion

On the first failed mutation, stop that mutation path, classify the actual failure and inspect
current state before retrying. Do not rerun an unchanged failing workflow as diagnosis. Preserve
successful unaffected evidence only when its immutable input identities remain compatible.
Containment takes priority: close acceptance/dispatch, stop new leases, reconcile unknown effects,
preserve data/claims/Stop latches and prove old workers retired. Report containment as unconfirmed
until readback and worker checks prove it.

DONE requires all 22 requirements accepted, both live cohorts passed, working alert delivery,
actual budgets/cost evidence, reproducible deployment/configuration ownership, and an operational
runbook the Founder can use without reconstructing the conversation. Author tests and Founder
review/merge are required. Necessary approvals are completed milestones, not exemption labels.

This component does not declare DONE while any required dependency remains unresolved. It may
report a specific blocked action with evidence, accountable closure owner and next decision;
it must not describe a partial release as fully working.
