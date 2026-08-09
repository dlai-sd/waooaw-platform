# WAOOAW Hybrid Application Shell

**Document type:** Architecture Reference — Customer Experience
**Office:** Enterprise Architect (INST-004)
**Work Contract:** WC-034
**Status:** REVIEW CANDIDATE — WC034-A02 complete; A03-A06 companion contracts published
**Constitutional basis:** C-001, C-009, C-023, C-034, C-042, C-059, C-065, C-076
**Architecture decision:** ADR-017 — Next.js 14 TypeScript PWA

## Decision Summary

WAOOAW provides one continuous professional relationship through WhatsApp, web, and a future mobile application. Each authorized channel projects the same relationship, conversation, plan, work, and governance state to the extent supported by its approved read and continuity contracts; no channel may infer synchronization from local state.

The authenticated web experience uses the layout and interaction grammar of a modern conversation application, with the Next.js Chatbot Template as a structural reference. WAOOAW does not copy that template's brand, exact components, or visual identity. It applies the ratified WAOOAW typography, colors, language system, constitutional controls, and employment model.

## Meaning of Hybrid SPA

"Hybrid SPA" means:

- Next.js App Router provides server rendering, route protection, metadata, initial data, and shareable URLs.
- Client transitions, streaming messages, the composer, panels, and optimistic interaction behave like an installed application after load; voice recording does so only in a release that includes approved F6 contracts.
- Public, authentication, customer, and Founder surfaces share one application and design system.
- The PWA is mobile-first and preserves application state across navigation and temporary connectivity loss.

It does not mean a client-only React SPA, a Vite application, a second frontend, or moving authentication and constitutional authorization into browser code.

## Normative Boundary and Dependencies

This document defines the application shell and customer-experience projection. It does not transfer ownership of identity, relationship, conversation, billing, evidence, or professional execution into the web application.

The shell may render implemented capabilities only through approved service contracts. It must represent a capability as unavailable, pending, or read-only when its owning contract is not implemented; it must never manufacture a successful local state to compensate for a missing platform operation.

Cross-channel history display and cross-channel transactional continuity are different capabilities:

- The shell may display a tenant-scoped merged history when an approved read contract supplies it.
- Authenticated handoff, checkpoint commit, delivery deduplication, ordering, replay protection, and exactly-once consequential outcomes depend on WC-060.
- Before WC-060 is complete, the interface must not claim that a WhatsApp-to-web handoff has committed or that an action submitted on one channel cannot be replayed on another.
- Emergency Stop remains channel-independent and must use the existing constitutional path; ordinary conversation streaming must never share, delay, or replace that path.

## Route and Layout Ownership

Route groups are ownership boundaries, not visible URL segments. Authorization is enforced before protected data is fetched.

| Route family | Route group | Layout owner | Rendering default | Required boundary |
|---|---|---|---|---|
| `/`, `/professionals`, `/professionals/[slug]`, `/blogs`, `/blogs/[slug]` | `(public)` | Public layout | Server-first | No authenticated relationship preload; capability and limitation disclosure |
| `/login`, `/register`, `/verify`, `/auth/error` | `(auth)` | Authentication layout | Server shell with isolated interactive form | Keycloak-brokered identity; safe server-owned return target |
| `/home`, `/professionals/mine`, `/relationships/[relationshipId]/*`, `/settings`, `/profile` | `(authenticated)` | Customer application layout | Server-authorized shell with client interaction islands | Validated tenant and participant session; persistent Emergency Stop |
| `/founder/*` | `(founder)` | Founder administration layout | Server-authorized shell | Explicit Founder claim; `/403` on denial; no CSS-only hiding |
| `/403`, not-found, global error, offline recovery | global | Shared system layout | Static or server-first | No fabricated success; correlation reference where available |

The canonical customer relationship routes are:

| Route | Purpose | Mobile presentation |
|---|---|---|
| `/relationships/[relationshipId]` | Redirect to the relationship conversation | Conversation |
| `/relationships/[relationshipId]/conversation` | Durable conversation and composer | Primary edge-to-edge view |
| `/relationships/[relationshipId]/plan` | Goals, checkpoints, and next work | Full-screen secondary view |
| `/relationships/[relationshipId]/work` | Actions, deliverables, approvals, and schedule | Full-screen secondary view |
| `/relationships/[relationshipId]/performance` | Business outcomes and review history | Full-screen secondary view |
| `/relationships/[relationshipId]/consumption` | Allowance, usage, forecast, budget, and alerts | Full-screen secondary view |
| `/relationships/[relationshipId]/governance` | Scope, rights, evidence, pause/resume, and lifecycle | Full-screen secondary view |

Shareable routes identify a view, not a browser-owned authority decision. Relationship and item identifiers are re-authorized on the server for every direct navigation.

## Server and Client Rendering Rules

Server-owned responsibilities:

- session validation, tenant and participant derivation, Founder-claim checks, and safe redirects;
- relationship authorization and initial read-model retrieval;
- metadata, locale, text direction, theme bootstrap, and non-secret feature availability;
- initial conversation page and context summary needed for a stable first render;
- generated-client invocation through the approved server boundary.

Client-owned interaction islands:

- composer text, draft persistence, and explicit send; attachment selection and voice capture only when their separately approved components are included;
- streamed message presentation, cancellation, retry, and reconnect status;
- navigation expansion, context-panel selection, sheets, focus restoration, and keyboard behavior;
- optimistic presentation only when an idempotency key exists and the state remains visibly unconfirmed;
- local preferences that do not grant authority or alter server-owned lifecycle state.

The browser must not derive tenant identity, authorize relationship access, commit lifecycle transitions, interpret transport delivery as constitutional evidence, or call a foundation model directly. Service responses remain authoritative after every optimistic interaction.

## Navigation Contract

Desktop primary navigation uses `My WaooaW Experts`, `Needs your attention`, and `Settings`, with `Profile` and `Sign out` in the account menu. Relationship context uses `Conversation`, `Plan`, `Work`, `Results`, `Usage & budget`, and `Rights & control`.

Route paths remain stable technical identifiers and are not translated. Customer-visible source labels are:

| Route or scope | English source label | Product meaning |
|---|---|---|
| `/professionals/mine` | My WaooaW Experts | Every professional relationship the customer has hired or is evaluating |
| Global priority projection | Needs your attention | Customer actions ordered by the server; omitted until the aggregate contract exists |
| `/conversation` | Conversation | The continuous professional exchange |
| `/plan` | Plan | Goals, checkpoints, and next work |
| `/work` | Work | Actions, deliverables, approvals, and schedule |
| `/performance` | Results | Business outcomes and review history; technical metrics remain supporting evidence |
| `/consumption` | Usage & budget | Allowance, usage, forecast, budget, and alerts |
| `/governance` | Rights & control | Scope, rights, records, pause/resume, lifecycle, and Emergency Stop |

Translations may use domain-native occupational language rather than literal equivalents, but they must preserve these meanings. `Performance`, `Consumption`, `Governance`, and `Priority Work` are internal architecture terms and must not appear as customer navigation labels.

Mobile bottom navigation is fixed to four destinations:

1. `Conversation` — current relationship conversation.
2. `Plan` — goals and next work for the current relationship.
3. `Work` — customer actions, deliverables, approvals, and schedule.
4. `WaooaW Experts` — relationship switcher and all employed professionals.

`Results`, `Usage & budget`, `Rights & control`, `Settings`, and `Profile` remain reachable from the relationship or account header. `Needs your attention` is global on desktop and resolves to a professional-scoped item when opened; it is omitted until the server-owned aggregate contract is approved and is not a fifth mobile destination.

## Canonical Experience Model

```text
Employment Relationship
├── One Professional
├── One Continuous Conversation
├── One Professional Plan
│   ├── Multiple Goals
│   └── Customer and Professional Actions
├── Work
│   ├── Deliverables
│   ├── Approvals
│   └── Scheduled and Completed Activity
├── Performance
│   ├── Outcome Measures
│   ├── Review History
│   └── Improvement Signals
├── Consumption
│   ├── Hired Allowance
│   ├── Usage and Forecast
│   ├── Budget
│   └── Threshold Alerts
└── Governance
    ├── Scope and Rights
    ├── Evidence
    ├── Pause and Resume
    └── Emergency Stop
```

Conversation is where work happens. Relationship is where the customer verifies and governs it.

## Entry and Resume Behavior

After authentication, WAOOAW opens the most recently active conversation by default, including when the latest interaction occurred through WhatsApp. After their contracts exist, the customer may instead select `My WaooaW Experts` or `Needs your attention` as the default start view in Settings.

Resume restores the professional, first unread position, active goal context, and outstanding customer action. It does not automatically mark content as read before that content becomes visible. Cross-channel transitions display a quiet separator such as `Continued on WhatsApp` rather than starting a new thread.

One professional relationship has one durable conversation. Multiple goals are represented in the Professional Plan, not as customer-managed chat threads.

## Multiple Professionals and Configured Identity

A customer account may hold multiple Employment Relationships. These may involve different professional types or repeated hires of the same professional type for different business contexts. Each hire remains a distinct relationship with its own conversation, plan, scope, contract, budget, performance, and evidence history.

The configuration step gives the professional a customer-facing identity within that relationship, including an approved name, avatar, persona expression, language, and business context. Duplicate professional types are identified by configured name and business context, never by labels such as `Agent 1` and `Agent 2`.

Configured professional avatars are functional identity assets and are permitted only in identity locations such as the professional switcher, relationship header, and profile. They are not repeated beside every message. The prohibition on imagery applies to decorative, stock, marketing, atmospheric, and background images; it does not prohibit the WAOOAW logo, application icons, the configured professional avatar, or customer/work-product attachments that are necessary to the professional service.

The purpose of the no-image philosophy is productive, text-focused conversation across WhatsApp, web, and mobile. Visual work products may be attached or previewed on demand, but they do not turn the conversation shell into an image feed.

A customer with one relationship enters that conversation directly. A customer with several relationships still resumes the most recently active conversation by default and can use a professional switcher or `My WaooaW Experts` to change context.

## Application Composition

### Desktop

```text
┌──────────────────┬─────────────────────────────────┬──────────────────────┐
│ Collapsible nav  │ Conversation                    │ Context panel        │
│                  │                                 │                      │
│ WAOOAW logo      │ Professional header             │ Plan by default      │
│ My Experts       │ Message stream                  │ Work                 │
│ Needs attention  │ Inline actions and deliverables │ Results              │
│ Settings         │ Fixed composer                  │ Usage & budget       │
└──────────────────┴─────────────────────────────────┴──────────────────────┘
```

The context panel defaults to Plan. Selecting an action, deliverable, approval, performance signal, or budget alert opens its detail in the panel without removing the customer from the conversation.

### Mobile

- The conversation is edge-to-edge and occupies the primary surface.
- The composer remains above the software keyboard and device safe area.
- Context-panel content opens as a full-screen route or sheet; no desktop panel is compressed beside chat.
- Bottom navigation contains no more than four destinations.
- Back navigation follows a native messaging hierarchy: detail to conversation, conversation to professional list, professional list to application exit/history.
- Layout remains stable when voice recording, attachment selection, or the keyboard opens.

## Conversation Header

Every conversation header contains:

- Professional identity and current availability
- Employment Relationship state
- Active goal or next priority
- Plan access
- Persistent Emergency Stop access

The WAOOAW logo is bold and visible at the top-left of expanded navigation. The icon mark is used for the browser favicon and PWA icon. No other decorative imagery is used; familiar interface icons are allowed.

## Structured Work in Conversation

The message stream supports four governed structured objects:

| Object | Purpose | Required behavior |
|---|---|---|
| Action Card | Work the customer or professional must complete | Names owner, status, goal, due date when relevant, and next command |
| Plan Card | Compact goal and checklist progress | Opens the complete Professional Plan |
| Deliverable Card | Output produced for the customer | Supports preview, download, feedback, and approval where authorized |
| Decision Card | Consequential customer choice | States effect, authority, cost/budget impact, and explicit alternatives before commitment |

Performance and consumption remain stable relationship views. Chat receives concise summaries only for material changes, review moments, and threshold alerts.

## API Ownership and Contract Gaps

ADR-002 and ADR-017 control every web-to-service interface: the approved OpenAPI document is updated first, a TypeScript client is generated, and application code consumes the generated model or a thin typed adapter. Browser components must not construct undocumented service URLs or duplicate business rules.

| Experience capability | Owning component | Current contract status | WC-034 implementation rule |
|---|---|---|---|
| Relationship admission, detail, timeline, and lifecycle | Business Platform | Canonical operations present | Consume generated client; never mutate lifecycle optimistically |
| Skill goals and contract performance | Business Platform | Canonical operations present but contract-scoped | Use only where relationship-to-contract ownership is explicit |
| Approvals and scope-boundary confirmation | Business Platform + Constitutional Engine | Canonical BP operations present | Preserve distinct approval and boundary-confirmation language |
| Customer evidence list, detail, and export | Business Platform Evidence Reader | Canonical operations present | Never call the Constitutional Audit Ledger directly |
| Billing summary, invoices, tiers, and preference | Business Platform/WBE projection | Canonical BP operations present | Consumption UI must distinguish billed value from forecast |
| Durable conversation timeline, send, acknowledgement, read position, and attachment metadata | Business Platform public API; Professional Runtime supplies internal execution/session outcomes | Missing from canonical OpenAPI; interview-message operation exists only in solution contract | BLOCKED until BP adds versioned customer-facing operations and schemas backed by the PR internal contract |
| Professional response stream | Business Platform public stream boundary; Professional Runtime owns the internal execution stream | No approved customer-facing stream contract | BLOCKED until BP and PR define one versioned stream contract; ordinary browser traffic must not connect directly to PR |
| Professional Plan and Priority Work projections | Business Platform | No canonical aggregate operation | BLOCKED; do not compose conflicting lifecycle truth in the browser |
| Relationship Consumption projection with allowance, forecast, and thresholds | WBE through Business Platform | Existing billing operations are insufficient for the specified view | BLOCKED pending owner-approved read contract |
| Registration, email/mobile verification, account linking, and duplicate resolution | Identity boundary + Business Platform | Canonical component contract and BP OpenAPI operations present in `components/identity-boundary.md` and `api-specs/business-platform.openapi.yaml` | Consume generated BP client; implementation remains blocked by the F2 gate table, including ADR-008 Meta reconciliation and independent INST-004 review |
| Cross-channel handoff and continuity checkpoint | Business Platform owns checkpoint truth and public commands; Professional Runtime owns internal channel delivery/session state | Specified by AE-01 solution contract; implementation belongs to WC-060 | BLOCKED until WC-060; the browser consumes only the BP public contract |
| Markup Designer management | WBE domain service through a Business Platform Founder API | Proposed internal WBE endpoint in acquisition specification; no canonical BP operation | BLOCKED until WBE defines the internal behavior and BP exposes an authorized Founder operation in its OpenAPI |
| Trial Budget management | WBE domain service through a Business Platform Founder API | No canonical BP operation or complete internal WBE management contract | BLOCKED pending WBE internal contract and BP Founder facade contract |
| Coupon creation, listing, and deactivation | WBE domain service through a Business Platform Founder API | Validation exists only on internal WBE; management contract and canonical BP operations are incomplete | BLOCKED pending WBE management behavior and BP Founder facade contract |

An unavailable contract produces an explicit capability-unavailable state and correlation reference. Mock data is permitted only in isolated tests and Storybook-equivalent development fixtures; it must never be reachable in a production build as a successful service fallback.

The Business Platform is the sole public REST/stream ingress for ordinary customer and Founder application traffic. WBE remains internal to BP, and PR remains internal for ordinary professional execution; the existing dedicated Emergency Stop WebSocket is the only browser-to-PR exception authorized by this package. Generated web clients target the BP OpenAPI, never private WBE or PR URLs.

## Interaction and Failure Semantics

Every submitted message or consequential command receives a client-generated idempotency key before transport. The visible lifecycle is `draft → sending → accepted | failed`; `delivered` and `read` may appear only when the channel supplies reliable acknowledgements. An accepted command may still be professionally processing and constitutionally uncommitted.

On reconnect, the client re-fetches authoritative state from the last server-confirmed cursor before retrying. Retry reuses the original idempotency key and payload hash. A conflicting payload under the same key is surfaced as a conflict and is never silently replaced.

The shell must provide explicit states for:

- initial loading with stable layout dimensions;
- empty relationship, conversation, plan, work, performance, consumption, and evidence views;
- offline with locally retained unsent draft and no false sent state;
- authentication expiry with preserved non-secret draft and safe re-entry;
- forbidden relationship or Founder access without resource disclosure;
- service degradation, timeout, conflict, and unknown outcome;
- active Emergency Stop, stop pending confirmation, stopped relationship, and unauthorized release attempt;
- streamed response cancellation and partial-response disclosure.

If Stop is issued during a stream, ordinary rendering stops immediately, the dedicated Stop path remains authoritative, and partial content is labelled incomplete. Reconnect cannot imply release or resume.

## Privacy, Cache, and Telemetry Boundary

- Service workers may cache public static assets and the minimum application shell, but not authenticated HTML, relationship payloads, messages, attachments, evidence, profile data, or API responses.
- Draft storage is relationship-scoped, contains no authentication token, has a bounded retention period, and is cleared on explicit sign-out or account switch.
- Tokens remain in secure server-managed sessions; browser storage must not contain bearer or refresh tokens.
- URLs, analytics events, logs, and error reports must not contain message text, attachment names, email, mobile number, business-sensitive context, or evidence payload.
- Correlation IDs may be displayed and reported; tenant IDs, internal authority snapshots, and raw constitutional records may not.
- Attachment preview requires an authorized, short-lived retrieval path and must not create a durable public URL.

## Performance and Resilience Budgets

These budgets are acceptance targets for WC-034 implementation and may be tightened by the owning quality contract:

| Measure | Budget |
|---|---|
| Server-rendered shell usable on a supported mid-tier mobile device | ≤3.0 seconds at p75 on a tested constrained mobile profile |
| Authenticated route transition with cached shell | ≤500ms to visible pending or resolved state at p75 |
| Composer input response | ≤100ms interaction latency at p75 |
| Accepted message acknowledgement under healthy service conditions | ≤1.0 second at p95, excluding professional response generation |
| First streamed professional content after server acceptance | Measured separately by professional/runtime class; never included in message-delivery status |
| Layout shift | No visible shift caused by late font, avatar, status, or toolbar loading; automated CLS target ≤0.1 |
| Conversation history | Cursor-paginated and virtualized or incrementally rendered; no unbounded initial payload |
| Offline recovery | Draft restored without duplicate submission; authoritative cursor reconciled before retry |

Emergency Stop latency is excluded from ordinary UI budgets because AD-001 provides the stricter end-to-end constitutional floor. Frontend changes must neither consume nor obscure that budget.

## Channel-Specific Login and Registration

WAOOAW does not force one authentication interaction onto every channel. WhatsApp uses conversational onboarding. Web and mobile use dedicated login and registration pages based on the restrained layout and interaction quality of the Next.js Chatbot Template.

Both paths resolve to one customer identity and one continuous professional relationship. A customer who registers through WhatsApp and later signs in on web or mobile must see the same conversation, plan, work, and relationship state after secure identity linking.

### WhatsApp Registration

WhatsApp registration happens inside the WhatsApp conversation. There is no redirect to a web registration form for ordinary low-risk onboarding.

The verified WhatsApp mobile number is the channel identity under ADR-023. WAOOAW asks for other mandatory details one at a time in the customer's selected language, explains why each detail is needed, and asks the customer to confirm the collected summary before registration completes.

The conversational flow must:

1. Recognize the Meta-verified WhatsApp number without asking the customer to type it again.
2. Detect an existing linked customer before creating a new registration.
3. Collect only the approved initial registration details.
4. Support text and voice answers, with explicit confirmation when transcription is uncertain.
5. Present privacy, terms, communication consent, and material disclosures in plain language with explicit responses.
6. Confirm the resulting customer profile and selected language.
7. Continue in the same WhatsApp conversation without creating a second thread.

### Initial Registration Data

Initial registration has a five-field ceiling:

| Detail | WhatsApp behavior | Purpose |
|---|---|---|
| Customer name | Ask preferred name | Welcoming identity and communication |
| Email | Ask once, explain that verification is required, then verify through an approved email or federated identity path | Recoverable identity, notices, and web/mobile access |
| Mobile number | Use the Meta-verified WhatsApp number and ask for confirmation; do not request re-entry | Channel identity and continuity |
| Business name | Ask the name customers recognize | Establish initial business context |
| Business domain | Ask as a plain-language business type or industry, not a website-domain field | Route the customer toward a suitable professional |

WhatsApp therefore needs at most four data-collection prompts because the mobile number is already known. Questions are asked one at a time, may be answered by voice, and end with a single editable summary confirmation. Registration completes only after the supplied email is verified.

Email verification may be satisfied by an approved email verification challenge or by Google/Meta authentication when the identity provider supplies a verified email claim. If the provider does not supply a verified email, WAOOAW collects and verifies it separately. Possession of a WhatsApp number alone is not sufficient for a complete customer account.

The following are deferred until trial, professional configuration, hiring, payment, or the first action that genuinely requires them:

- Goals, baseline, success measures, and detailed business context
- Address, operating locations, and service area
- Brand profile, channels, assets, and provider-account connections
- Budget, authority, approval, and risk preferences
- Contract, billing, GST, invoicing, and payment details
- Team members, additional participants, and role assignments
- Professional name, avatar, persona, and relationship-specific configuration
- Any domain-specific detail not required to create the customer account

**Founder resolution:** Email is mandatory for access to WAOOAW professionals. The Suresh walkthrough has been amended because its former optional-email rule was superseded by this decision. Registration design must explain the requirement plainly and minimize effort; it must not offer `Skip` or create a fully registered customer with an unverified email.

WhatsApp registration grants only the assurance permitted by ADR-023. Contract acceptance, payment authorization, Stop release, identity attachment to an existing high-assurance account, and other tiered actions still require their approved step-up path.

### Web and Mobile Authentication Layout

Web and mobile login/register are dedicated authentication pages. They do not simulate a chat conversation and do not place authentication fields inside the professional message stream.

Their visual and behavioral reference is the Next.js Chatbot Template authentication experience:

- Full-height application surface with the WAOOAW logo at top-left and language/theme controls at top-right.
- A focused authentication column on desktop, sized for comfortable reading rather than stretched across the viewport.
- A full-width, edge-to-edge flow on mobile with safe-area padding, stable software-keyboard behavior, and native-feeling transitions.
- Clear login/register switching without returning to the marketing homepage.
- No hero illustration, stock image, marketing carousel, decorative background image, or nested card composition.
- Light and dark themes only.
- Noto Sans with language-specific Noto subsets loaded before interactive content to avoid script and layout shift.
- The selected language is resolved before first render and can always be corrected from the header.

Authentication methods remain Keycloak-brokered and are presented in the approved persona-appropriate order. Controls are commands, not decorative cards. Errors remain inline, preserve entered non-secret values and selected language, and provide a next step.

Registration collects only the minimum mandatory details for the selected identity path. WhatsApp/mobile-number verification links the web or mobile identity to an existing WhatsApp registration when one exists; it must not mint a duplicate customer merely because the customer entered through another channel.

Web and mobile registration require a verified email and an approved strong authentication path. Google or Meta authentication may satisfy the federated identity step when required claims are verified. Email/password or equivalent credential paths require the approved second factor. Authentication assurance is progressive: routine access uses the approved account session, while contract acceptance, payment, Stop release, authority expansion, and other high-risk actions may require fresh or stronger step-up authentication.

After successful login or registration, a safe server-owned return target opens the most recent cross-channel professional conversation or the customer's configured default start view. Authentication itself remains a distinct transition screen.

### Authentication Boundaries

- Keycloak remains the identity broker; the application does not implement credential verification.
- ADR-023 remains the identity authority for WhatsApp-native onboarding; Keycloak does not replace the verified WhatsApp channel identity.
- Linking WhatsApp and Keycloak identities requires explicit verification and deterministic duplicate-account handling.
- Tenant, participant, Founder, and role claims are accepted only from the validated server session.
- Founder routes require an explicit Founder claim and use a server-side route boundary.
- Public pages never preload authenticated relationship data.
- Registration does not create an active Employment Relationship or imply professional authority.

## WhatsApp Interaction Grammar

The baseline conversation release includes chronological messages, timestamps, date separators, unread boundaries, reply context, text, draft preservation, failed-send retry, and approved deep links. Voice recording, attachments, and transactional cross-channel continuation enter only in releases that include their separately approved F6, attachment, and F5/WC-060 contracts; unavailable controls are absent or explicitly disabled without implying capability.

It defers reactions, stickers, stories/status, disappearing messages, social presence, message editing, and group chat.

WAOOAW recreates familiar interaction behavior, not WhatsApp branding. WAOOAW colors, typography, terminology, and constitutional states remain distinct.

## Status Semantics

Three status systems must never be collapsed into one tick vocabulary:

| Status | Customer question | Presentation |
|---|---|---|
| Message delivery | Did my message reach its destination? | Neutral sending, sent, delivered, read where reliable, or failed states |
| Professional processing | What is my professional doing? | Preparing, waiting for customer, scheduled, working, blocked, or completed |
| Constitutional evidence | Was the consequential action authorized and recorded? | WAOOAW evidence mark plus explicit text such as `Recorded` or `Approval recorded` |

WhatsApp messages use explicit evidence text because transport delivery ticks cannot communicate constitutional proof.

## Visual Direction

- Preserve the ratified WAOOAW blue, green, orange, and navy tokens.
- Restrict themes to light and dark.
- Use Noto Sans and approved multi-script subsets.
- Use no imagery beyond the WAOOAW logo and required application icons.
- Boldness comes from hierarchy, type, decisive states, large touch targets, and edge-to-edge mobile composition rather than decorative graphics.
- Emergency Stop red remains reserved exclusively for Emergency Stop.
- Color is always paired with iconography and plain-language text.

## Acceptance Invariants

- Exact 360px mobile and desktop layouts have no horizontal overflow.
- Login, registration, conversation, Plan, Work, Performance, Consumption, and Relationship surfaces support keyboard navigation.
- Urdu mirrors layout correctly; Indic scripts do not clip or force manual font-size compensation.
- When F6 is included, voice controls are available from every professional conversation; before then, no enabled recorder or upload control is rendered.
- Reduced-motion preference disables nonessential motion.
- When F5/WC-060 is included, cross-channel replay does not duplicate messages or create a second conversation; before then, the UI makes no committed-handoff or exactly-once claim.
- Delivery status can never be mistaken for constitutional evidence.
- Emergency Stop remains reachable from every authenticated professional surface.
- Theme, locale, drafts, unread position, and chosen default start view survive navigation and reconnect where constitutionally and technically permitted.

## Product Decisions and Release Gates

| Decision | Product disposition | Implementation effect |
|---|---|---|
| Customer-visible source labels | **CLOSED by INST-011:** `Plan`, `Work`, `Results`, `Usage & budget`, `Rights & control`, `Needs your attention`, and `My WaooaW Experts` | All eleven language packs remain release-blocking and translate meaning, not internal architecture terms; route ownership is unchanged |
| First customer release attachments | **DEFERRED:** text-only conversation ships first | No attachment button, reserved active control, preview, or upload path appears until Product, Security, and service contracts are approved |
| Voice interaction | **DEFERRED from first customer release to F6** | No enabled or visually reserved recorder appears before consent, retention, correction, accessibility, evidence, provider, and API decisions close |
| Cross-channel notification suppression | **DEFERRED to F5/WC-060** | First customer release makes no active-channel suppression or transactional handoff promise |
| Global priority ordering | **DEFERRED until the BP aggregate contract exists** | `Needs your attention` is omitted from navigation and default-view settings; no browser ranking or disabled dead-end destination |
| Public Concierge | **DEFERRED from F1 and the first customer release** | Public pages use direct browse, disclosure, login, and registration commands; no simulated or non-durable concierge fallback |
| Vercel AI SDK use for typed stream consumption | **CLOSED by INST-005:** not approved as an F3 architecture dependency | Reconsider only after the canonical BP/PR stream contract exists; any later proposal remains presentation-only with no provider, persistence, authentication, or business ownership |

The navigation destinations and global-versus-relationship scope are closed by this architecture. The remaining decisions are routed to their owning offices and cannot be silently chosen during implementation.
