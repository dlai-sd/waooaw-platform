# WAOOAW Hybrid Application Shell

**Document type:** Architecture Reference — Customer Experience
**Office:** Enterprise Architect (INST-004)
**Work Contract:** WC-034
**Status:** DRAFT — Founder discussion decisions recorded 2026-08-08
**Constitutional basis:** C-001, C-009, C-023, C-034, C-042, C-059, C-065, C-076
**Architecture decision:** ADR-017 — Next.js 14 TypeScript PWA

## Decision Summary

WAOOAW provides one continuous professional relationship through WhatsApp, web, and a future mobile application. Each channel is a synchronized projection of the same relationship, conversation, plan, work, and governance state.

The authenticated web experience uses the layout and interaction grammar of a modern conversation application, with the Next.js Chatbot Template as a structural reference. WAOOAW does not copy that template's brand, exact components, or visual identity. It applies the ratified WAOOAW typography, colors, language system, constitutional controls, and employment model.

## Meaning of Hybrid SPA

"Hybrid SPA" means:

- Next.js App Router provides server rendering, route protection, metadata, initial data, and shareable URLs.
- Client transitions, streaming messages, the composer, voice recording, panels, and optimistic interaction behave like an installed application after load.
- Public, authentication, customer, and Founder surfaces share one application and design system.
- The PWA is mobile-first and preserves application state across navigation and temporary connectivity loss.

It does not mean a client-only React SPA, a Vite application, a second frontend, or moving authentication and constitutional authorization into browser code.

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

After authentication, WAOOAW opens the most recently active conversation by default, including when the latest interaction occurred through WhatsApp. The customer may instead select `My Professionals` or `Priority Work` as the default start view in Settings.

Resume restores the professional, first unread position, active goal context, and outstanding customer action. It does not automatically mark content as read before that content becomes visible. Cross-channel transitions display a quiet separator such as `Continued on WhatsApp` rather than starting a new thread.

One professional relationship has one durable conversation. Multiple goals are represented in the Professional Plan, not as customer-managed chat threads.

## Application Composition

### Desktop

```text
┌──────────────────┬─────────────────────────────────┬──────────────────────┐
│ Collapsible nav  │ Conversation                    │ Context panel        │
│                  │                                 │                      │
│ WAOOAW logo      │ Professional header             │ Plan by default      │
│ Professionals    │ Message stream                  │ Work                 │
│ Priority work    │ Inline actions and deliverables │ Performance          │
│ Settings         │ Fixed composer                  │ Consumption          │
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

## Login and Registration Experience

Login and registration use the same restrained, conversation-first application grammar as the Next.js Chatbot Template. They must feel like entering or resuming a conversation, not leaving WAOOAW for a generic enterprise identity page.

### Shared Layout

- Full-height application surface with the WAOOAW logo at top-left and language/theme controls at top-right.
- A focused authentication column on desktop, sized for comfortable reading rather than stretched across the viewport.
- A full-width, edge-to-edge authentication flow on mobile with safe-area padding and native keyboard behavior.
- No hero illustration, stock image, marketing carousel, decorative background image, or nested card composition.
- Light and dark themes only.
- Noto Sans with language-specific Noto subsets loaded before interactive content to avoid script and layout shift.
- The selected language is resolved before first render and can always be corrected from the header.

### Login

The first message is direct: `Continue with your WaooaW professionals.` The page presents the available Keycloak-brokered methods in persona-appropriate order:

1. Continue with Google
2. Continue with WhatsApp/Phone
3. Additional approved identity providers when configured
4. Existing account credentials where institutionally supported

Authentication controls are commands, not decorative cards. Errors remain inline, preserve the selected language, and provide a next step. A safe server-owned return target resumes the exact professional and unread position that initiated login.

### Registration

Registration is progressive and conversational in pacing, but each legal or consequential consent remains an explicit form decision. It collects only the minimum information needed for the selected identity path and professional experience.

The flow:

1. Select or confirm identity method.
2. Confirm detected language.
3. Collect and verify WhatsApp/phone only when required for continuity or the selected professional.
4. Explain why each requested field is needed at the point of collection.
5. Confirm terms and privacy through explicit, accessible controls.
6. Resume the pre-authentication conversation or professional context.

A public Concierge conversation may be summarized above the authentication action as `Continue this conversation`, but authentication never displays fabricated message history or treats the Concierge as a hired professional.

### Authentication Boundaries

- Keycloak remains the identity broker; the application does not implement credential verification.
- Tenant, participant, Founder, and role claims are accepted only from the validated server session.
- Founder routes require an explicit Founder claim and use a server-side route boundary.
- Public pages never preload authenticated relationship data.
- Registration does not create an active Employment Relationship or imply professional authority.

## WhatsApp Interaction Grammar

The first release includes chronological messages, timestamps, date separators, unread boundaries, reply context, text, universal voice recording, relevant attachments, draft preservation, failed-send retry, deep links, and cross-channel continuation.

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
- Voice controls are available from every professional conversation.
- Reduced-motion preference disables nonessential motion.
- Cross-channel replay does not duplicate messages or create a second conversation.
- Delivery status can never be mistaken for constitutional evidence.
- Emergency Stop remains reachable from every authenticated professional surface.
- Theme, locale, drafts, unread position, and chosen default start view survive navigation and reconnect where constitutionally and technically permitted.

## Decisions Still Required

1. Final four mobile bottom-navigation destinations.
2. Desktop navigation labels and whether Priority Work is global or professional-scoped.
3. Exact customer-visible names for Plan, Work, Performance, Consumption, and Relationship in all language packs.
4. Which attachment types are required for the first professional release.
5. Voice-message retention, transcription consent, and transcript correction behavior.
6. The notification contract when the customer is active on one channel and receives activity on another.
7. Whether a customer may employ multiple professionals at first release and how global priority ordering behaves.