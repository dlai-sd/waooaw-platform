# WC-084 - Authentication Readiness And Customer Portal Delivery Plan

**Office:** Chief Solution Architect (INST-005)
**Future implementation executor:** Platform IT Expert (INST-010), Skills 4 and 16 for application
code and Skill 17 only for authorized delivery configuration and qualification
**Assigned by:** Founder instruction, 2026-09-07
**Status:** PLAN AND PROTOTYPE HANDOFF CANDIDATE; RUNNABLE IMPLEMENTATION NOT AUTHORIZED
**Predecessor:** WC-083 route-backed authentication dialog
**Normative parents:** `architecture/reference/ux/hybrid-application-shell.md`,
`architecture/reference/ux/hybrid-ui-acceptance-contract.md`,
`architecture/reference/ux/hybrid-visual-system-contract.md`,
`architecture/reference/components/identity-boundary.md`,
`architecture/reference/components/relationship-workspace.md`
**Architecture decisions:** ADR-002, ADR-003, ADR-008, ADR-014, ADR-017, ADR-023, ADR-034
**Constitutional basis:** C-001, C-002, C-023, C-026, C-042, C-049, C-059, C-063,
C-071, C-076

## 1. Objective

Repair the customer-visible defects left by WC-083, complete truthful Demo readiness for Google,
Facebook, and email authentication, and define a reusable API-first Customer Portal that behaves like
an installed conversation application after login. Produce one standalone HTML/CSS/JavaScript review
prototype before any portal implementation begins.

The Customer Portal is a disruptive flagship WAOOAW deliverable. Acceptance requires a distinctive,
world-class professional AI workforce experience; functional completeness alone is insufficient.
Visual quality, interaction quality, accessibility, responsiveness, conversational coherence, and
truthful constitutional state are first-class delivery outcomes.

The delivery has two distinct outcomes:

1. a production-grade authentication entry experience whose provider choices work when their
   environment gates pass and whose modal behavior remains compact, stable, accessible, and correct;
2. a separate authenticated Customer Portal experience for My Agents, Marketplace, Alerts, Billing,
   Profile, sign-out, and chat/voice interaction with employed professionals.

Plan acceptance authorizes neither runnable source changes nor provider activation. A later
implementation session requires explicit Founder authorization and must use this accepted plan as
its controlling Work Contract.

## 2. Requirement Classification And Precedence

| ID | Requirement | Classification | Required disposition |
|---|---|---|---|
| AUTH-01 | Compact login and registration proportions matching the supplied reference | WC-083 defect | Repair only auth dialog dimensions and spacing |
| AUTH-02 | Google, Facebook, and email usable by Demo portal customers | WC-083 incomplete outcome | Complete environment, broker, API, and end-to-end readiness |
| AUTH-03 | WAOOAW-branded loading animation inside a dimensionally stable modal | WC-083 defect | Replace full-page auth transition loading |
| AUTH-04 | Login/register switching closes directly to the original public route | WC-083 defect | Replace history-depth-dependent dismissal |
| WEB-01 | Production-grade Chrome compatibility and responsive integrity | Cross-cutting defect | Reproduce, repair, and qualify affected routes |
| PORTAL-01 | Separate SPA-like authenticated Customer Portal | New requirement | Deliver through the existing hybrid Next.js application boundary |
| PORTAL-02 | My Agents with chat and voice interaction | New requirement | Reuse relationship/conversation/voice contracts |
| PORTAL-03 | Marketplace browse, trial, and hire | New requirement | Use Business Platform customer APIs only |
| PORTAL-04 | Alerts, Billing, Profile, and sign-out | New requirement | Define owner-backed projections and commands |
| PORTAL-05 | WhatsApp-inspired one-hand mobile navigation and account drawer | New requirement | Prototype, test, and obtain Founder visual acceptance |
| API-01 | APIs reusable by web, future mobile, and WhatsApp | New cross-channel requirement | OpenAPI-first Business Platform facade; no web-only business rules |

When this plan conflicts with WC-083 presentation or acceptance, the explicit defect repairs above
supersede WC-083. All unaffected WC-083 behavior remains mandatory.

### 2.1 Story Points

- **SP-01 - Compact authentication:** As a portal visitor, I can use login and registration dialogs that retain the approved WAOOAW appearance and fit a laptop viewport without initial vertical scrolling.
- **SP-02 - Provider identity:** As a portal visitor, I can recognize Google, Facebook, Apple, and email immediately through their correct marks, colors, labels, and availability states.
- **SP-03 - Google access:** As a new or returning customer, I can authenticate through the enabled Google broker and return safely to my intended WAOOAW destination.
- **SP-04 - Facebook access:** As a new or returning customer, I can authenticate through the separately approved Facebook login application and return safely to WAOOAW.
- **SP-05 - Email access:** As a customer, I can register, verify, and sign in through the Keycloak-owned email flow when social login is unavailable or not preferred.
- **SP-06 - Truthful readiness:** As a visitor, I see only providers that are genuinely ready in the current environment, while unavailable or unreachable providers fail closed without exposing technical or secret details.
- **SP-07 - Stable loading:** As a visitor opening or switching authentication forms, I remain inside a dimensionally stable modal with an accessible WAOOAW-branded loading state instead of seeing a full-page loading screen.
- **SP-08 - Direct dismissal:** As a visitor who switches between login and registration, I can close the dialog once and return directly to the public page where the authentication journey began.
- **SP-09 - Browser integrity:** As a portal user, I can use every affected page in supported Chrome, Edge, Firefox, and Safari-equivalent browsers without clipping, overlap, destructive wrapping, or unreachable controls.
- **SP-10 - My Agents:** As an authenticated customer, I can see my trial and employed professionals, select one, and resume its authorized relationship conversation and current work context.
- **SP-11 - Text conversation:** As a customer, I can send, retry, and reconcile messages with truthful draft, sending, accepted, failed, partial, and evidence states.
- **SP-12 - Voice conversation:** As a customer, I can record, pause, review, correct, cancel, and explicitly send a voice contribution while retaining a complete text fallback.
- **SP-13 - Marketplace:** As a customer, I can browse and compare published professionals, inspect scope and limits, and begin an eligible trial or hire through approved Business Platform operations.
- **SP-14 - Alerts:** As a customer, I can distinguish decisions requiring action from informational updates and open the correct destination without a read action becoming approval.
- **SP-15 - Billing:** As a customer, I can inspect my plan, allowance, forecast, invoices, and payment state using Billing Engine truth projected through Business Platform.
- **SP-16 - Profile and settings:** As a customer, I can manage profile, organization, language, theme, channel preferences, login methods, and security actions within the required assurance boundary.
- **SP-17 - Navigation:** As a mobile customer, I can reach My Agents, Marketplace, and Alerts through a one-hand bottom bar while using a left account drawer for Profile, Billing, Settings, and Sign out.
- **SP-18 - Themes and accessibility:** As a customer, I can use the portal in light or dark theme, with keyboard, screen reader, reduced motion, zoom, RTL, and supported-language behavior preserved.
- **SP-19 - Shared channel APIs:** As a customer using web, future mobile, or WhatsApp, I receive consistent Business Platform-owned state and rules rather than channel-specific business implementations.
- **SP-20 - Safe degradation:** As a customer, I see explicit loading, empty, offline, unavailable, stale, conflict, and error states that never manufacture success or conceal an uncertain outcome.
- **SP-21 - Human override:** As a customer working with any professional, I can always reach Emergency Stop independently of navigation, loading, chat, voice, or service degradation.
- **SP-22 - Frozen public experience:** As the Founder, I can approve these repairs and the new Customer Portal without permitting unrelated changes to the frozen public portal aesthetics.
- **SP-23 - Two-minute onboarding:** As a customer, I can complete lightweight agent onboarding within a two-minute target and continue into an agent-led, domain-adaptive induction conversation.
- **SP-24 - Universal goals:** As a customer, I can turn every agent's declared skills into goals with measures, frequency, and explicit verification through one consistent WAOOAW experience.
- **SP-25 - Outcome traceability:** As a customer, I can see how each verified goal contributes to a business outcome and how agent performance and outcome evidence are measured without implying guaranteed results.
- **SP-26 - Goal-gated operations:** As a customer, I enter Operations only after required goals are verified, while retaining the ability to amend goals and reassess affected outcomes at any time.

### 2.2 Founder Handoff Mandate Trace

This trace is a drift gate. Removing or weakening a listed controlling section requires explicit
Founder review and corresponding Section 14 acceptance updates.

| # | Binding mandate | Controlling sections | Acceptance gate |
|---|---|---|---|
| 1 | Flagship, world-class disruptive Customer Portal | 1, 8.9 | WC084-PORTAL-15 |
| 2 | Prototype is boundary guidance; production has bounded creative liberty | 3, 10 | WC084-PORTAL-16 |
| 3 | Standardized names, styling, font, color, themes, and language-ready layout | 3, 8.2, 8.9 | WC084-PORTAL-16 |
| 4 | Universal Onboard, Induct, goals, outcomes, and Operations lifecycle | 8.5 | WC084-PORTAL-17 through 21 |
| 5 | Distinct WAOOAW experience informed by ChatGPT and WhatsApp ergonomics | 3, 8.3, 8.9 | WC084-PORTAL-22 |
| 6 | Reuse accepted Agent Broker and existing capability contracts before creation | 8.9, 9.2 | WC084-API-03 |
| 7 | Explicit `REUSE`, `AMEND`, `CREATE`, or `DEFER` API discovery | 9.2, 9.4 | WC084-API-03 |
| 8 | Channel-neutral contracts reusable by web, WhatsApp, and future mobile | 9.1, 9.3, 9.4 | WC084-API-01, WC084-API-03 |
| 9 | AI-token, time, and cost optimization without weaker evidence | 13 | WC084-QUAL-01 |
| 10 | Docker-only executable testing and no host virtual environment | 12, 13 | WC084-QUAL-02 |
| 11 | Bounded vertical implementation slices | 11 | WC084-QUAL-01 |
| 12 | Independent, executable acceptance and substantive Founder visual review | 12, 14, 17 | WC084-PORTAL-15, WC084-QUAL-01 |

## 3. Visual Authority And Creative Boundary

The public portal's approved aesthetics are frozen. Implementation must not change unrelated fonts,
font loading, colors, brand tokens, logo treatment, public navigation, landing composition, content,
cards, motion, spacing, or styling.

Authorized visual changes are limited to:

- login and registration modal size, typography, spacing, provider marks, loading state, and auth
  transition behavior;
- CSS repairs strictly necessary to fix reproduced clipping, overflow, overlap, or destructive
  wrapping in supported browsers;
- the new authenticated Customer Portal shell and its owned routes;
- a review prototype that explores the new Customer Portal boundary, lifecycle, and interaction
  direction while using a recognizable WAOOAW visual vocabulary.

The prototype controls required sections, lifecycle relationships, representative states, and
customer journeys. It is guidance and boundary evidence, not production markup or a pixel-perfect
specification. The implementer has creative liberty to improve composition, typography, color,
themes, motion, navigation, density, and responsive behavior inside the authenticated Customer
Portal, provided all required lifecycle states, constitutional controls, customer verification,
evidence visibility, API traceability, and Section 14 acceptance conditions remain intact.

Production implementation must establish standardized Customer Portal names, design tokens,
typography, color, spacing, elevation, motion, breakpoints, themes, iconography, and language-ready
layout. It may take interaction inspiration from ChatGPT's conversational workspace and navigation
ergonomics and WhatsApp's compact, familiar messaging continuity, but must not visually imitate
either product, use their proprietary assets, or weaken WAOOAW's distinct professional identity.

Any aesthetic change outside this list requires a Founder-visible before/after proposal and explicit
authorization before implementation.

## 4. Preserved Behavior

- `/login` and `/register` remain canonical direct-entry and refresh-safe routes.
- Public entry points may intercept those routes into an accessible modal over the invoking page.
- Keycloak remains the sole web credential authority. Web and Business Platform never verify social
  credentials or provider tokens.
- Safe same-origin return targets, locale, direction, theme, focus lifecycle, and reduced-motion
  support remain mandatory.
- Apple remains visibly coming soon until its independent provider gate passes.
- WhatsApp identity remains governed by ADR-023 and is never treated as a Keycloak session.
- Business Platform remains the sole public customer REST/stream facade. Browser and mobile clients
  do not call Professional Runtime, Billing Engine, Constitutional Engine, or ledgers directly.
- Emergency Stop remains persistent and independent of ordinary conversation or loading paths.

## 5. Entry Gates And Required Inputs

### 5.1 Plan And Prototype Gate

The current authorization permits only this plan and the isolated prototype. The prototype must use
fictional, non-customer data; perform no network calls; contain no authentication, payment, provider,
or production logic; and live only under `prototypes/wc084-customer-portal/`.

### 5.2 Implementation Gate

Before runnable implementation, the future executor must verify:

| Input | Required state |
|---|---|
| This WC-084 plan | Founder accepted |
| Prototype visual direction | Founder accepted, including mobile navigation and desktop composition |
| WC-083 final implementation baseline | Exact merged commit and qualification evidence recorded |
| Identity boundary and BP OpenAPI | Current, accepted, and generated-client consistency passing |
| Google provider | OAuth client, approved redirect URIs, Key Vault references, broker configuration, and readiness evidence available |
| Facebook provider | Meta business/app prerequisites, login-only scopes, redirect URIs, Key Vault references, broker configuration, and readiness evidence available |
| Email provider | Keycloak flow, delivery mechanism, verification template, sender/domain, and readiness evidence available |
| Portal capability APIs | Owner-approved operations and schemas for every released view/command |
| Browser baseline | Reproduction evidence for reported Chrome defects and accepted unchanged-route screenshots |
| Current-session implementation authority | Explicit Founder authorization after all preceding gates pass |

Missing provider credentials block that provider's activation, not truthful display of other ready
providers. Missing portal capability contracts block that capability from implementation; the web
must not compensate with local mock success or private service calls.

## 6. Authentication Repair Contract

### 6.1 Compact Visual Geometry

The supplied compact authentication reference controls proportions. The future implementation must
record exact approved pixel values after prototype comparison, subject to these limits:

- initial login and registration provider-choice states fit inside a 1366x768 browser viewport with
  no dialog scrollbar at 100% zoom;
- modal width is stable across loading, login, registration provider choice, and provider error;
- the auth title uses a compact panel heading, not public-page hero typography; target visual scale is
  approximately 20-24px before localization adjustment;
- provider rows retain recognizable Google, Facebook, Apple, and email marks with their established
  brand colors and accessible text labels;
- close control, focus indicator, body text, and commands meet WCAG 2.2 AA target sizes and contrast;
- mobile, 200% zoom, long translations, RTL, and larger text reflow rather than clip or overlap.

Registration workflow steps that genuinely require more vertical content may scroll inside the same
bounded dialog after the provider-choice state. The initial choice screen must not scroll on the
required laptop viewport.

### 6.2 Stable Auth Loading State

Auth navigation opens a modal shell immediately and loads content inside it. The shell reserves the
approved final width and minimum height so content replacement causes no visible layout shift.

The loading visual uses the existing WAOOAW logo or wordmark in a finite circular, spherical, or
sine-wave motion. It must:

- remain inside the auth modal over the originating public page;
- provide visible and screen-reader loading status;
- stop when content resolves, fails, or the dialog is dismissed;
- reduce to a static branded progress state under `prefers-reduced-motion`;
- never delay close, Escape, backdrop dismissal, or Emergency Stop;
- resolve to a bounded error with retry rather than a generic full-page loading screen.

### 6.3 Auth Journey Navigation State Machine

```text
PUBLIC_ORIGIN
  -> AUTH_SHELL_LOADING
  -> LOGIN | REGISTER
LOGIN <-> REGISTER
LOGIN | REGISTER -> PROVIDER_REDIRECT | REGISTRATION_WORKFLOW | AUTH_ERROR
ANY_MODAL_STATE -> DISMISSED_TO_PUBLIC_ORIGIN
DIRECT_LOGIN | DIRECT_REGISTER -> STANDALONE_AUTH_ROUTE
```

The public origin is captured once when the modal journey starts. Login/register switching replaces
the active auth state without stacking dismissible auth origins. Close, Escape, or backdrop click
from any modal auth state returns directly to that original public route and restores invoking focus.
Direct `/login` and `/register` visits remain standalone; dismissal there follows an explicit safe
fallback and never depends on an unknown browser history entry.

### 6.4 Provider Readiness And Activation

The current repository contains browser wiring and readiness projection, but Demo marks Google and
Facebook disabled and the Keycloak realm ships both brokers disabled. Email is marked enabled in the
Demo manifest; an all-unavailable UI therefore indicates readiness-endpoint failure or deployed
configuration drift and must be observable rather than silently indistinguishable.

For each provider, readiness requires all applicable layers:

1. approved external application and least-privilege scopes;
2. exact Demo callback/origin registration;
3. credentials stored only through Azure Key Vault references;
4. enabled Keycloak broker or Keycloak-owned email flow;
5. Business Platform environment manifest enabled with immutable readiness evidence reference;
6. web-to-Business-Platform provider projection reachable in the deployed network;
7. browser redirect, callback, account/registration continuation, sign-out, and repeat-login proof;
8. privacy-safe failure logs and a customer-safe unavailable state.

`GET /api/v1/identity/providers` remains the canonical anonymous projection. Its failure fallback must
remain fail-closed, but telemetry and qualification must distinguish endpoint unreachability,
configuration rejection, and provider-disabled state without exposing secrets to the browser.

## 7. Browser Compatibility Contract

The reported Chrome catalogue compression is release-blocking. Qualification must first reproduce
the exact route, browser version, viewport, zoom, locale, theme, and asset state. Repairs remain
limited to the owning responsive rule and must not visually redesign unaffected routes.

Required browser projects:

- current stable Chrome and Edge on Chromium;
- current stable Firefox;
- WebKit/Safari-equivalent;
- exact viewports 360x800, 768x1024, 1366x768, and 1440x900;
- 100%, 125%, and 200% zoom/reflow scenarios where supported.

Every affected page must assert no incoherent overlap, clipping, inaccessible command, destructive
word wrapping, horizontal document overflow, or fixed-navigation collision. Auth tests additionally
assert initial modal vertical fit. Catalogue tests assert a minimum usable card width and text bounds;
screenshots alone do not substitute for geometry assertions.

## 8. Customer Portal Experience Contract

### 8.1 Product Boundary

The Customer Portal is a distinct authenticated experience, not a landing-page extension and not a
second frontend framework. It uses the existing Next.js hybrid application shell: server-authorized
initial routes and client transitions/interactions that feel SPA-like after load.

The WhatsApp inspiration is interaction architecture, not visual imitation. WAOOAW keeps its own
logo, font, colors, terminology, constitutional status semantics, and professional identity model.

### 8.2 Information Architecture

| Area | Customer outcome | Initial release behavior |
|---|---|---|
| My Agents | Resume work with employed or trial professionals | Default entry; relationship list and selected conversation |
| Configuration | Complete universal agent setup | Exactly two items: Onboard and Induct |
| Goal Setting | Convert declared skills into verified goals | Agent-led goals, measures, frequency, and customer verification |
| Business Outcomes | Understand customer-visible value and performance | Outcomes linked to skills, goals, measures, frequency, and evidence |
| Operations | Conduct governed work against verified goals | Locked until required goals are customer-verified; goals remain amendable |
| Marketplace | Discover, compare, trial, and hire professionals | Browse and inspect offers; trial/hire only through approved lifecycle APIs |
| Alerts | See decisions and events requiring attention | Server-ordered actionable and informational items; no browser ranking |
| Billing | Understand plan, allowance, invoices, payment state, and forecast | BP projection of WBE truth; no browser calculations |
| Profile | Manage identity, organization, language, channels, and security | Account drawer entry to full route or sheet |
| Sign out | End the session and clear protected client state | Account drawer command with deterministic cleanup |

### 8.3 Navigation

Mobile uses a fixed bottom bar with three primary destinations: `My Agents`, `Marketplace`, and
`Alerts`. This leaves room for a later Founder-approved fourth destination without redesign. Profile,
Billing, Settings, account switching, and Sign out live in a left account drawer opened from the
header. Emergency Stop remains visible in the selected relationship header and is never hidden in
the drawer.

Desktop uses a collapsible left rail containing the same global destinations and account access, a
relationship list when My Agents is active, the central conversation/work surface, and an optional
context panel when width permits. At intermediate width, context becomes a full route or sheet; it is
never squeezed beside an unreadable conversation.

### 8.4 My Agents And Conversation

- Resume the most recently active authorized relationship after login.
- Show configured professional identity, relationship state, active goal, unread state, and current
  availability without repeating decorative avatars beside every message.
- Support text conversation with truthful `draft -> sending -> accepted | failed` states.
- Render approved Action, Plan, Deliverable, and Decision cards without treating transport as
  evidence or professional processing as completion.
- Provide voice capture, pause, resume, cancel, review, correction, playback, and explicit send only
  where the accepted WC-062 contract is available.
- Preserve a complete text path when microphone permission, language, upload, or transcription fails.
- Keep Emergency Stop visible and operational throughout chat and voice states.

### 8.5 Universal Agent Lifecycle

Every WAOOAW professional uses the same customer lifecycle:

`Onboard -> Induct -> Goal Verification -> Business Outcomes -> Operations`

- Configuration contains exactly `Onboard` and `Induct` for every agent.
- Onboard covers lightweight presentation choices such as agent name, chat appearance, and timestamp
  visibility and targets completion within two minutes.
- Induct is an agent-led conversation, not a long form. The agent introduces itself and its declared
  skills, learns the customer's profession, organization, terminology, priorities, and constraints,
  adapts its language to that domain, and confirms its understanding in a consultative tone.
- Goal Setting is consistent across all agents. Every declared skill is available to become a goal;
  every active goal records a measure, frequency, and explicit customer verification.
- The agent proposes precise goals and asks only the minimum questions required to verify them.
- Operations remains locked until the required goals are customer-verified.
- Customers may amend goals at any time. Material changes require renewed verification and
  reassessment of dependent outcomes and operational work without erasing historical evidence.
- Every Business Outcome traces to a declared skill, verified goal, performance measure, review
  frequency, current status, and evidence. Agent performance and customer business outcome remain
  distinct; the portal must not imply that an agent guarantees an externally influenced result.

The right panel provides lifecycle status and navigation while the agent conducts induction and goal
setting in the main conversation. Each agent adapts content to its profession, but the lifecycle,
verification semantics, and information grammar remain universal.

### 8.6 Marketplace

Marketplace lists only published and currently offerable professionals from a Business Platform
projection. Search and filters may affect presentation but cannot invent suitability, availability,
price, or trial eligibility. Detail views expose scope, limits, pricing source, trial terms, and the
next authorized command. Trial and hire are distinct, idempotent server-owned lifecycle operations.

### 8.7 Alerts

Alerts combine server-owned attention items and informational notifications while preserving their
type. Each item includes source, relationship when applicable, occurred/due time, severity vocabulary,
read state, available action, and stable destination. The browser may group for display but cannot
re-rank authoritative attention order. Read/acknowledge is not approval, evidence, or completion.

### 8.8 Billing And Profile

Billing displays BP-mediated WBE actuals, invoices, allowance, forecast range, assumptions, payment
state, and commercial consequences. It never derives monetary truth from tokens or local arithmetic.

Profile displays BP/identity-owned customer and organization projections, language/theme/channel
preferences, login methods, assurance needs, and account controls. Sensitive changes require the
server-declared step-up flow. Sign-out clears protected state and relationship drafts according to
the accepted retention policy.

### 8.9 Production Experience Standard

Production establishes accepted semantic tokens and standardized components by reusing existing
WAOOAW elements where suitable, including Agent Broker onboarding and employment contracts,
configuration, goals, performance/outcomes, and operation patterns. Light and dark themes support
keyboard operation, visible focus, screen-reader state announcements, logical properties, RTL, all
approved locales, 200% zoom, safe-area insets, and reduced motion. Fixed-format navigation,
composer, voice controls, counters, and loading shells use stable dimensions.

Visual acceptance includes substantive review at agreed desktop and mobile viewports. Automated
screenshots, geometry assertions, and accessibility checks are necessary evidence but do not replace
Founder review of hierarchy, clarity, coherence, responsiveness, and WAOOAW identity.

## 9. Channel-Neutral API Contract

### 9.1 Ownership Rule

Business Platform is the sole public facade for web, future mobile, and WhatsApp customer
capabilities. Channel adapters may transform presentation and transport, but business state,
authorization, ordering, lifecycle, idempotency, and evidence semantics remain shared.

Every new public REST or SSE operation follows ADR-002:

1. update the canonical Business Platform OpenAPI first;
2. trace the operation to an owning capability and component;
3. define authorization, assurance, tenant derivation, idempotency, pagination/cursor, freshness,
   errors, and unavailable behavior;
4. generate clients for web and future mobile or define the explicit channel adapter mapping;
5. prohibit hand-written browser URLs and web-only business rules.

### 9.2 Required Capability Surfaces

The implementation-readiness classification is:

| Capability surface | Classification | Current canonical operations | Contract work before implementation |
|---|---|---|---|
| Session and sign-out | `REUSE` + `AMEND` | `GET /api/v1/identity/session` | Reuse the session projection. INST-005 and the identity owner must define the Keycloak/NextAuth sign-out closure, protected-draft cleanup, and login-method management boundary; no BP sign-out endpoint is inferred. |
| My Agents | `AMEND` | `GET /api/v1/employment/relationships/{relationshipId}` and relationship workspace reads | Add an owner-approved paginated, tenant-derived relationship-summary collection and authorized resume-target semantics. The existing `POST /api/v1/employment/relationships` does not supply this read model. Endpoint path and wire schema remain INST-005 decisions. |
| Conversation | `REUSE` | `GET/POST /api/v1/employment/relationships/{relationshipId}/conversation/messages`, message retry, read position, SSE stream, and execution cancellation | Reuse the completed WC-060 contracts and generated clients without a parallel portal conversation API. |
| Voice | `REUSE` | Voice session create/read, audio upload, transcript read, correction, explicit send, cancel, and erasure operations under `/api/v1/employment/relationships/{relationshipId}/voice-contributions` | Reuse the completed WC-062 contract and generated clients without changing consent, retention, or Evidence First semantics. |
| Onboard and Induct | `REUSE` + `AMEND` | Agent Broker professional disclosure, relationship offer/trial/contract/activation, customer configuration, and conversation capabilities | Reuse accepted onboarding and relationship lifecycle truth. INST-005 and Product, BP, professional, Data, and Security owners must classify presentation preferences, induction progress, confirmed business context, correction, retention, and cross-channel continuation before implementation. |
| Goal Setting | `REUSE` + `AMEND` | Agent skill declarations and relationship goal/workspace capabilities | Reuse accepted skill and goal truth where complete. Owners must define the universal skill-to-goal projection, measure, frequency, verification, amendment, history, and Operations eligibility semantics without web-only state. |
| Business Outcomes | `CREATE` | No accepted customer-facing aggregate is assumed by this plan | Product, BP, professional, Data, Security, and INST-005 must define outcome-to-skill/goal traceability, agent performance versus external business result, measures, cadence, evidence, trend, correction, and unavailable behavior. No guarantee or browser-derived outcome is permitted. |
| Operations | `REUSE` + `AMEND` | Relationship workspace reads, attention, conversation, execution, cancellation, and Evidence First records | Reuse governed operational capabilities. Owners must bind Operations eligibility to verified goals and define how goal amendments affect active work, outcomes, pending decisions, and historical evidence. |
| Marketplace | `REUSE` + `AMEND` | `GET /api/v1/professionals`, professional disclosure, offerable versions, relationship offerability evaluation, trial, contract, and activation operations | Reuse discovery and lifecycle operations. INST-005 and Product/BP owners must bind browse pagination/filter semantics and the exact trial/hire journey to existing operations; the browser cannot infer offerability. |
| Alerts | `REUSE` + `CREATE` | Relationship-scoped `GET .../workspace/attention`; notification preference `GET/PUT /api/v1/notifications/preferences` | Keep relationship attention as-is. A cross-relationship server-ordered alerts feed, cursor, read/acknowledge behavior, and stable action destination require Product, BP, Data, Security, and INST-005 contracts. No endpoint path or schema is selected by this plan. |
| Billing | `REUSE` + `AMEND` | `GET /api/v1/billing`, `GET/PUT /api/v1/billing/preference`, `GET /api/v1/billing/invoices`, and subscription-tier reads | Reuse current billing truth. WBE/BP owners and INST-005 must confirm whether allowance forecast, payment state, assumptions, and consequences are complete for the initial portal release; the web performs no calculation. |
| Profile/settings | `REUSE` + `CREATE` | Identity session projection and notification preference `GET/PUT` | Channel preferences are reusable. Customer/organization profile, locale/theme persistence, login methods, security actions, assurance requirements, and account switching need owner-approved Product, Identity, Data, Security, BP, and INST-005 contracts. No browser-local profile truth is permitted. |

Contracts must not expose provider secrets, tenant IDs as customer authority, private runtime URLs,
raw constitutional records, or internal billing/AI cost structures. Unknown or unavailable owner
truth remains explicit and never becomes an empty success response.

### 9.3 Cross-Channel Continuity

WC-060 is DONE with R-087, R-088, and R-089 approved, and WC-062 is DELIVERY COMPLETE with
R-096, R-097, and R-098 approved and PR #273 merged as `1a624d6`. WC-084 therefore classifies their
channel-continuity and voice-contribution contracts as `REUSE`; it does not redesign or defer them.
Web, mobile, and WhatsApp may display the same BP-owned history only through those accepted
contracts. New WC-084 aggregation, profile, settings, marketplace, or sign-out semantics remain
blocked until the owner contracts in Section 9.2 are accepted.

### 9.4 API Discovery And Reuse Ledger

Milestone 5 produces one reviewed capability ledger before dependent UI integration. For every
Customer Portal capability it records:

| Required field | Purpose |
|---|---|
| UI capability and lifecycle state | Binds the customer need to a specific portal surface |
| Existing accepted contract and owner | Prevents duplicate or browser-local domain behavior |
| `REUSE`, `AMEND`, `CREATE`, or `DEFER` | Makes the implementation disposition explicit |
| Request, response, and generated-client impact | Defines the public integration boundary |
| Authorization, assurance, tenant, evidence, and audit rules | Preserves constitutional semantics |
| Loading, empty, locked, expired, stale, conflict, partial, and unavailable states | Prevents manufactured success |
| Web, WhatsApp, and future mobile mapping | Proves channel-neutral reuse or records an approved exception |
| Required Product, API, Data, Security, BP, or professional-owner approval | Keeps decisions with their accountable owner |

The ledger is updated as discovery resolves facts. An unclassified or unapproved capability blocks
only its dependent slice. UI code must not invent an endpoint, schema, eligibility rule, outcome,
verification state, or browser-local workaround.

## 10. Prototype Deliverable

Create `prototypes/wc084-customer-portal/index.html` as a dependency-free review artifact containing:

- responsive desktop and mobile Customer Portal compositions;
- light/dark theme switch;
- functional My Agents, Marketplace, and Alerts navigation;
- functional account drawer with Billing, Profile, Settings, and Sign out;
- selected-agent conversation with text send and representative structured work;
- universal two-item Configuration with Onboard and conversational Induct;
- agent-led Goal Setting from declared skills through measures, frequency, and verification;
- goal-linked Business Outcomes and Operations eligibility states;
- voice recording/review state simulation with no microphone or network access;
- Marketplace browse/detail/trial-review states without executing a hire;
- alert read/action simulation;
- loading, empty, offline, and error demonstrations;
- persistent visible Emergency Stop control as a non-operational visual state;
- fictional data and a visible `Prototype - no live actions` status.

The prototype is reviewed for information architecture, lifecycle boundaries, visual direction,
density, one-hand reach, theme behavior, state clarity, and responsive composition. It is not
production markup, a pixel-perfect specification, or evidence that APIs or production features
exist. Founder acceptance authorizes its boundary and guidance, not automatic implementation,
provider activation, deployment, or final visual acceptance.

## 11. Ordered Delivery Milestones

### 11.1 Executor And Authority Matrix

| Work boundary | Accountable owner/executor | Authority limit |
|---|---|---|
| Product release composition and customer semantics | Product Owner (INST-011) and named capability owners | Select first-release behavior and labels; no endpoint, schema, or implementation authority |
| Public BP operations, schemas, errors, and generated-client boundary | Chief Solution Architect (INST-005) with BP/WBE/Identity/professional owners | Design accepted API contracts; no runnable implementation or provider activation |
| Provenance, ordering, freshness, retention, and correction semantics | Data Architect (INST-006) | Supply accepted data contract; no public API or implementation authority |
| Assurance, authorization, anti-enumeration, cache, telemetry, and direct-service denial | Security Architect (INST-007) | Supply accepted security contract; no product or implementation authority |
| Application and web implementation | Platform IT Expert (INST-010), Skills 4 and 16 | Implement accepted contracts in source and tests after explicit current-session authorization |
| Docker, workflow, environment configuration, and delivery qualification | Platform IT Expert (INST-010), Skill 17 | Implement accepted delivery contracts only; Skill 17 grants no API-design, provider, deployment, spend, DNS, or Production authority |
| Provider enablement and environment deployment | Named environment/provider authority under a separate Founder authorization | Activate only the named provider and environment after its complete gate passes |
| Visual acceptance, implementation authorization, PR approval, and merge | Founder | These decisions remain separate and are never inferred from plan or test completion |

No milestone may transfer a decision to a downstream executor. Missing Product, API, Data, Security,
BP, WBE, Identity, or professional-owner input blocks only the dependent release slice and must not
be replaced by browser logic, mock success, or an implementation assumption.

### Milestone 0 - Founder Prototype Review

- Complete and review the standalone prototype.
- Record accepted lifecycle boundary, navigation, terminology, responsive behavior, and requested
  revisions.
- Preserve the approved prototype revision as guidance, not production markup or a ceiling on
  production visual quality.

### Milestone 1 - WC-083 Defect Reproduction And Baseline

- Bind the exact merged WC-083 commit, deployed Demo revision, and image digest.
- Reproduce modal vertical scroll, reopen loading, nested auth dismissal, provider availability, and
  Chrome catalogue destruction with exact browser/environment evidence.
- Capture unchanged public-page baselines. Do not repair unrelated visual differences.

### Milestone 2 - Provider Readiness

- Obtain separate current authority for provider configuration, Demo deployment, and authenticated
  provider proof before any live action.
- Complete Google, Facebook, and email entry gates independently.
- Validate manifests before deployment and reconcile them against actual Keycloak broker state.
- Prove provider endpoint reachability from the deployed web container.
- Execute real provider redirect/callback/registration/login/sign-out/repeat-login acceptance in Demo.
- Keep blocked providers truthfully unavailable with an accountable gate reference outside the UI.

### Milestone 3 - Authentication UX Repair

- Implement compact login and registration geometry.
- Add stable in-modal WAOOAW loading and bounded error/retry states.
- Implement explicit auth journey origin and switch semantics.
- Preserve standalone routes, safe returns, focus, locale, RTL, reduced motion, and accessibility.

### Milestone 4 - Chrome And Cross-Browser Repair

- Repair only reproduced owning CSS/layout defects.
- Add geometry assertions for catalogue, auth, header, consent, and affected breakpoints.
- Confirm frozen-route visual diffs contain only authorized corrections.

### Milestone 5 - API Contract Closure

- Complete the Section 9.4 discovery ledger against the selected first-release composition by
  inspecting accepted Agent Broker, onboarding, configuration, skills, goals, performance/outcomes,
  operation, relationship, conversation, billing, identity, and notification contracts.
- INST-005 and the named owners close every selected `AMEND`/`CREATE` component and OpenAPI contract
  before INST-010 writes dependent implementation code.
- Generate clients and prove consistency for all changed public operations.
- Stop portal implementation for any capability without accepted owner semantics.

### Milestone 6 - Production Experience Foundation

- Establish standardized names, semantic design tokens, typography, color, spacing, iconography,
  motion, themes, breakpoints, locale/RTL behavior, and reusable production components.
- Implement the authenticated shell, responsive navigation, account drawer, route protection,
  loading/error/offline states, and My Agents relationship overview.
- Preserve Emergency Stop and protected caching boundaries.

### Milestone 7 - Universal Agent Lifecycle

- Implement two-item Configuration: two-minute-target Onboard and agent-led conversational Induct.
- Implement declared-skill Goal Setting with measures, frequency, customer verification, amendment,
  and history.
- Implement goal-linked Business Outcomes while distinguishing agent performance from external
  customer results.
- Prove that Operations is locked until required goals are verified and safely reassessed after a
  material goal amendment.

### Milestone 8 - Conversation, Voice, And Operations

- Integrate generated conversation and voice contracts.
- Implement streaming/reconciliation, text draft/send/retry, structured objects, and voice review/send.
- Integrate current work, pending decisions, evidence, results, usage, and controls against verified
  goals and outcomes.
- Validate uncertainty, partial response, permission denial, offline, and Stop behavior.

### Milestone 9 - Marketplace And Supporting Customer Surfaces

- Implement Marketplace, Alerts, Billing, Profile, Settings, sign-out, and their owner-approved
  lifecycle commands and projections.
- Verify trial, hire, expired relationship, read/acknowledge, step-up, and protected-state cleanup.

### Milestone 10 - Final Qualification And Founder Handoff

- Run one clean final Docker campaign against finalized HEAD.
- Review screenshots route by route and theme/locale/viewport state by state.
- Bind build, tests, browser evidence, scans, author review, and PR metadata to one commit.
- Leave the PR unmerged for Founder review.

## 12. Test And Acceptance Plan

### 12.1 Focused Checks

After the first substantive edit in each implementation milestone, run the cheapest behavior-scoped
check that can falsify that change. Host/editor activity is limited to non-executable inspection such
as language-server diagnostics, diff review, and static file comparison; those inspections are not
substitutes for executable evidence. Every executable test, lint, typecheck, schema validator,
generator, build, browser check, and qualification command runs in the repository-approved Docker
test runner or service under C-080. Do not create or use Python, Node, or other host virtual
environments. Reuse an existing applicable container when economical; do not rebuild images or run
the broad integration/browser/scanner campaigns after small edits.

### 12.2 Major-Milestone Docker Campaigns

Run Docker integration campaigns only after these assembled boundaries:

1. Milestones 2-4: complete authentication/provider/browser repair;
2. Milestones 5-7: accepted API contracts plus experience foundation and universal lifecycle;
3. Milestones 8-9: complete conversation, voice, Operations, and supporting surfaces;
4. Milestone 10: one final clean qualification on finalized HEAD.

Each campaign stops on the first deterministic failure. Repair the owning slice, run its focused
check once, then rerun the affected milestone campaign. Do not rebuild unchanged images or rerun
passing expensive stages speculatively.

### 12.3 Required Evidence

- strict TypeScript and production build;
- focused unit/component tests and at least 90% changed interactive line coverage;
- generated-client consistency and OpenAPI validation;
- provider manifest/Keycloak reconciliation and real Demo authentication evidence;
- Chromium Chrome/Edge, Firefox, and WebKit browser matrix;
- exact viewport, zoom/reflow, English/Urdu, LTR/RTL, light/dark, keyboard, reduced-motion, and axe
  checks for owned routes and states;
- geometry assertions for overflow, clipping, overlap, card width, modal fit, fixed navigation,
  software keyboard, and safe areas;
- interaction evidence for Onboard, Induct, goal verification/amendment, outcome traceability,
  Operations locking/unlocking, expired relationships, and cross-channel continuation;
- offline/cache/privacy inspection, authorization negatives, idempotency/replay/conflict tests, and
  no private endpoint leakage;
- Docker image/runtime smoke, SBOM, vulnerability scan, secret scan, and final-HEAD evidence ledger.

## 13. AI Token, Time, And Cost Optimization

- Load only this plan's global boundary, the active milestone, owning component/API sections, touched
  files, nearest tests, and latest focused failure.
- Search exact acceptance IDs and symbols before opening files; do not repeatedly reread full UX,
  identity, billing, or runtime documents.
- Maintain one compact milestone ledger containing facts, changed files, image ID, focused command,
  result, and blocker.
- Use deterministic tools for schema generation, validation, formatting, testing, screenshots,
  geometry checks, hashing, scans, and evidence assembly. Runtime and tests make zero LLM calls.
- Reuse existing components, generated clients, semantic tokens, icon library, fixtures, and pinned
  Docker images. Add no framework, design system, state store, or animation dependency without a
  separately accepted need.
- Run focused executable checks in the smallest applicable Docker runner after local edits. Reserve
  image rebuilds and broad Docker campaigns for Section 12.2 boundaries and final qualification.
- Create no host virtual environment and install no host dependency for implementation or evidence.
- On deterministic failure, inspect the first causal evidence and repair that slice. Do not retry
  unchanged code, regenerate all screenshots, or reopen broad context.
- Record development model calls, focused Docker runs, full campaigns, reused image IDs, retries,
  and avoided duplicate campaigns in final evidence.

Optimization never authorizes weaker assertions, skipped providers, reduced browser/locale coverage,
mock success, bulk screenshot approval, or incomplete author review.

## 14. Acceptance Traceability

| Acceptance ID | Pass condition | Evidence owner |
|---|---|---|
| WC084-AUTH-01 | Initial login and registration fit at 1366x768 without dialog scroll | Milestone 3 browser geometry |
| WC084-AUTH-02 | Provider marks, labels, focus, zoom, RTL, and themes remain usable | Milestone 3 visual/a11y matrix |
| WC084-AUTH-03 | Loading remains in a stable same-size auth modal | Milestone 3 route timing/CLS test |
| WC084-AUTH-04 | Close from switched auth form returns directly to original public route | Milestone 3 navigation tests |
| WC084-IDP-01 | Google completes real Demo login and registration continuation | Milestone 2 integrated evidence |
| WC084-IDP-02 | Facebook completes real Demo login and registration continuation | Milestone 2 integrated evidence |
| WC084-IDP-03 | Email completes real Demo login, verification, and registration | Milestone 2 integrated evidence |
| WC084-IDP-04 | Endpoint/network/config failure is observable and fails closed | Milestone 2 fault tests/log evidence |
| WC084-WEB-01 | Reported Chrome catalogue defect is reproduced then absent | Milestone 1/4 before-after evidence |
| WC084-WEB-02 | Browser/viewport/zoom matrix has no clipping, overlap, or destructive wrapping | Milestone 4 geometry matrix |
| WC084-PORTAL-01 | Founder accepts prototype navigation and visual direction | Milestone 0 acceptance record |
| WC084-PORTAL-02 | Mobile bottom navigation supports My Agents, Marketplace, and Alerts one-handed | Milestone 0/6 browser review |
| WC084-PORTAL-03 | Drawer provides Billing, Profile, Settings, and Sign out | Milestone 0/6 interaction tests |
| WC084-PORTAL-04 | My Agents supports truthful text and approved voice states | Milestone 7 contract/browser tests |
| WC084-PORTAL-05 | Marketplace trial/hire uses owner-approved idempotent BP operations | Milestone 5/6 contract tests |
| WC084-PORTAL-06 | Alerts preserve server order and distinguish read from action/approval | Milestone 5/6 contract tests |
| WC084-PORTAL-07 | Billing displays WBE truth only through BP | Milestone 5/6 network/contract tests |
| WC084-PORTAL-08 | Profile/settings persist only owner-approved identity, organization, locale, theme, channel, login-method, and security state with required step-up | Milestone 5/6 contract and browser tests |
| WC084-PORTAL-09 | Sign-out terminates the Keycloak/NextAuth session and clears protected drafts, caches, and selected relationship context without deleting server-owned customer data | Milestone 5/6 auth and storage tests |
| WC084-PORTAL-10 | Loading, empty, offline, unavailable, stale, and conflict states remain distinguishable and never manufacture success | Milestone 6/7 fault and browser tests |
| WC084-PORTAL-11 | Every authenticated route denies an absent, expired, or insufficient session without rendering protected data | Milestone 6 route and authorization tests |
| WC084-PORTAL-12 | Authenticated HTML, RSC, API, conversation, and voice responses remain `no-store` and protected content is absent from service-worker caches | Milestone 6/7 cache and network inspection |
| WC084-PORTAL-13 | Emergency Stop remains visible, keyboard reachable, and operational during navigation, loading, conversation, voice, modal, offline, and degraded states | Milestone 6-8 interaction and failure tests |
| WC084-PORTAL-14 | Portal code uses generated BP clients and contains zero hand-written private PR, WBE, CE, ledger, or provider calls | Milestone 5/8 generated-client and bundle/network inspection |
| WC084-PORTAL-15 | Founder substantive review accepts the production portal as a coherent, distinctive, world-class WAOOAW experience; functional checks alone cannot pass this row | Milestone 10 visual acceptance record |
| WC084-PORTAL-16 | Production preserves the prototype's required sections and lifecycle boundaries while using standardized production names, tokens, typography, color, themes, and language-ready layout rather than copying prototype markup | Milestone 6/10 design-system and visual review |
| WC084-PORTAL-17 | Configuration contains exactly Onboard and Induct; lightweight Onboard meets the accepted two-minute usability target | Milestone 7 timed interaction and usability evidence |
| WC084-PORTAL-18 | Induct is agent-led, consultative, confirmation-seeking, concise, and adapted to the customer's profession or business domain | Milestone 7 conversation/component tests and review |
| WC084-PORTAL-19 | Every active goal traces to a declared skill, measure, frequency, and explicit customer verification through the universal Goal Setting experience | Milestone 7 contract and interaction tests |
| WC084-PORTAL-20 | Operations remains locked before required goal verification; customers can amend goals and dependent work/outcomes are reassessed without losing history | Milestone 7/8 state-transition and history tests |
| WC084-PORTAL-21 | Every Business Outcome traces to a skill, verified goal, performance measure, review frequency, status, and evidence while distinguishing agent performance from externally influenced results | Milestone 7/8 contract and evidence tests |
| WC084-PORTAL-22 | Navigation and conversation may draw ergonomic inspiration from ChatGPT and WhatsApp but use no proprietary assets, visual imitation, divergent business rules, or non-WAOOAW identity | Milestone 6/10 design and dependency review |
| WC084-API-01 | Web uses generated BP clients; mobile/WhatsApp mappings share semantics | Milestone 5 conformance ledger |
| WC084-API-02 | Browser contains no private PR/WBE/CE endpoint | Milestone 8 bundle/network inspection |
| WC084-API-03 | Every released capability has an owner-reviewed `REUSE`, `AMEND`, `CREATE`, or `DEFER` classification and web, WhatsApp, and future-mobile mapping before dependent implementation | Milestone 5 discovery ledger |
| WC084-QUAL-01 | Final Docker qualification and author review bind one final HEAD | Milestone 10 evidence ledger |
| WC084-QUAL-02 | All executable development and acceptance evidence runs in approved Docker services with no host virtual environment or host-installed dependency workflow | Milestone 1-10 command/evidence ledger |

## 15. Rollback And Release Boundary

- Authentication repair must be independently reversible to the accepted WC-083 route-backed
  behavior without changing identity data or provider credentials.
- Each provider is activated independently only after its readiness evidence passes; rollback
  disables that provider in both Keycloak and the reviewed environment manifest.
- Customer Portal routes remain behind authenticated release control until complete capability and
  browser qualification. A partial route cannot replace the accepted customer shell silently.
- API amendments are additive and version-compatible unless a separately accepted breaking-change
  plan exists. Generated clients and consumers move together.
- Build once and promote the same accepted digest through separately authorized environments.
- Plan/prototype completion, Founder prototype acceptance, implementation authorization, PR approval,
  merge, Demo deployment, UAT, Production, provider activation, and customer traffic are distinct.

Provider slices are independent only while unavailable: a provider missing credentials, external
approval, broker configuration, callback registration, or readiness evidence remains disabled with
an accountable gate reference while other fully qualified providers may proceed. Once a provider is
enabled in an environment, its redirect, callback, registration continuation, returning login,
sign-out, repeat-login, failure, and rollback paths must all pass; partial activation blocks that
provider and it must be disabled rather than released as partly working. At least one fully qualified
provider path, including the Keycloak-owned email flow when selected, is required for an authenticated
portal release. UAT, Production, and customer traffic remain separately authorized regardless of
Demo proof.

## 16. Stops

Stop rather than proceed when:

- runnable implementation is requested without a new explicit Founder authorization;
- the Founder has not accepted this plan or prototype direction;
- a proposed change alters frozen public aesthetics beyond Section 3;
- provider credentials, external approval, callback registration, Key Vault binding, or readiness
  evidence is absent;
- an enabled provider has only a partially passing login, registration, callback, sign-out,
  repeat-login, failure, or rollback path;
- Demo email remains unavailable and deployed network/configuration evidence cannot identify why;
- a portal feature lacks an owner-approved Business Platform contract;
- a portal capability lacks a Section 9.4 classification, accountable owner, or cross-channel mapping;
- web, mobile, or WhatsApp would implement divergent business rules or call private services;
- transactional cross-channel continuity is claimed before WC-060 permits it;
- tests use live customer data, committed secrets, production fallback mocks, or runtime LLM calls;
- a deterministic failure is retried, hidden by baseline replacement, or bypassed by weakening a gate;
- visual screenshots are treated as sufficient without geometry, interaction, accessibility, and
  substantive review;
- prototype markup is treated as production code, a pixel-perfect mandate, or a ceiling on quality;
- an executable check runs on the host or a host virtual environment or dependency install is used;
- cloud mutation, spend, Production, customer traffic, self-approval, self-merge, or direct `main`
  push is proposed without exact authority.

## 17. Definition Of Done

### 17.1 Current Authorized Delivery

This planning activity is complete when:

- this plan covers every Founder requirement, separates WC-083 defects from new scope, defines
  interfaces and ownership, preserves the public-site boundary, grants bounded Customer Portal
  creative liberty, and records lifecycle, API-discovery, milestone, test, and cost controls;
- the standalone prototype demonstrates the Section 10 states and interactions on desktop and mobile,
  in light and dark themes, without network or production behavior;
- the Solution Architect completes author review and records unresolved Founder decisions;
- both artifacts are ready for Founder review without claiming implementation readiness or approval.

### 17.2 Future Implementation Completion

WC-084 implementation is done only when all Section 14 acceptance rows pass, each provider's real
Demo path is proven or remains truthfully blocked by an accepted external gate, all released portal
capabilities use approved generated BP contracts, the Section 9.4 ledger is complete, major-milestone
and final Docker campaigns pass without a host virtual environment, frozen public visuals show no
unauthorized changes, substantive visual review accepts every changed route, and one unmerged
final-HEAD-bound PR is ready for Founder review.

## 18. Solution Architect Author Review

**Status:** PASS - initial author review complete 2026-09-07; bounded institutional repair review
complete 2026-09-08. Founder acceptance remains required.

The review covered requirements completeness, predecessor defect classification, frozen visual
boundary, component ownership, API reuse across channels, provider entry gates, interaction states,
browser/accessibility evidence, failure behavior, security/privacy, reversibility, Docker cadence,
token optimization, acceptance traceability, and authorization stops.

Findings repaired during author review:

1. Replaced language that required broad Docker campaigns after small edits with focused executable
  checks in the smallest applicable Docker runner and milestone-only broad campaigns, matching C-080.
2. Corrected the prototype Plan panel so desktop close/reopen and intermediate/mobile overlay
  behavior are coherent and expose accurate `aria-expanded` state.
3. Added directly reviewable loading, empty, offline, and error states to the prototype Settings
  panel rather than relying on prose or an incidental empty search result.
4. Added Section 2.1 as a one-sentence-per-item story-point summary spanning authentication defects,
  provider readiness, browser integrity, Customer Portal capabilities, shared APIs, degradation,
  Emergency Stop, and the frozen public-experience boundary.
5. On 2026-09-08, completed the API `REUSE/AMEND/CREATE` ledger, separated design, implementation,
  Skill 17 delivery, provider, and Founder authorities, corrected C-080 focused-check language,
  recorded WC-060/WC-062 as accepted reuse baselines, added missing acceptance rows, and reconciled
  independent provider deferral with complete activated-provider behavior.
6. On 2026-09-08, integrated the Founder-requested handoff mandate across the controlling objective,
  visual authority, universal agent lifecycle, channel-neutral discovery ledger, vertical slices,
  Docker-only/no-virtual-environment policy, stops, and executable acceptance rows. The prototype is
  explicitly guidance rather than production markup, and production retains bounded creative liberty
  subject to substantive Founder visual acceptance.

Deterministic checks passed: JavaScript syntax, required local asset presence, editor diagnostics,
diff whitespace, and headless Chromium at 1440x900, 768x1024, and 360x800. The browser checks verified
zero document overflow, the compact agent-list-first hierarchy, Plan close/open, account drawer,
Billing panel, theme switching, mobile voice draft/cancel, and all four system-state previews.

The 2026-09-08 repair pass additionally verified each cited reusable operation against the canonical
Business Platform OpenAPI, reconciled WC-060 and WC-062 against their completion records, reviewed
the complete plan for authority and acceptance consistency, and passed editor diagnostics. It made
no claim that owner-blocked `AMEND` or `CREATE` contracts are accepted or implementation-ready.

No runnable `src/` or `web/` application code, provider configuration, infrastructure, deployment,
or frozen public-site styling was changed. The prototype uses fictional local data and performs no
network or live customer action.
