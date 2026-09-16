# Work Contract 096 - Conversational Customer Portal

## Record Control

| Field | Value |
|---|---|
| Office | Platform IT Expert (INST-010) |
| Assigned and authorized by | Founder instruction in the 2026-09-16 continuous working session |
| Status | ENGINEERING QUALIFIED - FOUNDER REVIEW AND MERGE PENDING |
| Branch | `ib/096/conversational-customer-portal` |
| Baseline | `origin/main` at `6c21bb37` after WC-095 merge |
| Delivery type | Customer Portal remediation and reusable conversational interaction component |
| Predecessors | WC-034, WC-060, WC-084, WC-087, WC-088, WC-095 |
| Constitutional basis | C-001, C-002, C-003, C-023, C-034, C-039, C-042, C-049, C-059, C-063, C-065, C-088 |
| Governing decisions | ADR-002, ADR-017, ADR-020, ADR-023, ADR-034, ADR-049 |

## 1. Objective

Deliver one responsive, persistent and conversational Customer Portal in which a customer can:

1. navigate without full-document reloads;
2. discover an offerable professional through an engaging card;
3. select Trial or Hire directly and review the relevant disclosure and Terms before any consequence;
4. continue the selected intent into one authorized relationship without losing professional or version context;
5. see employed or trial agents directly as useful dashboard cards;
6. interact with Marketplace, My Agents, alerts, configuration, goals, work, performance and billing through a contextual conversation surface; and
7. use the same versioned interaction semantics later from mobile and through the existing WhatsApp boundary.

The implementation completes the ratified hybrid application shell. It does not create a second
frontend, a second relationship aggregate, a browser-owned assistant, or an alternate path around
Business Platform, Constitutional Engine, billing, evidence, identity or Emergency Stop.

## 2. Founder Feedback Bound To Scope

| ID | Observed defect or direction | Required outcome |
|---|---|---|
| DF-001 | Marketplace DMA disclosure link resolves to `Not found` | Resolve authoritative professional type/version to a published disclosure route; never derive a slug mechanically in the browser. |
| DF-002 | Trial/Hire continuation is not wired from Marketplace | Preserve exact intent and professional release through disclosure, registration where required, and the explicit relationship command. |
| DF-003 | DMA offer card is dense and internally oriented | Present an outcome-led, customer-facing professional identity, proof, price, trial and limitations with progressive disclosure. |
| DF-004 | Trial and Hire need direct card actions | Every eligible card exposes distinct Trial and Hire actions; disclosure and Terms precede acceptance or activation. |
| DF-005 | Portal navigation refreshes the entire page | Keep one authenticated shell mounted; use client transitions and content-local streamed loading states. |
| DF-006 | Left menu needs collapsible icon rail and right pullout | Provide customer-controlled collapsed and expanded states, labels below icons, accessible tooltips and responsive overlay/pin behavior. |
| DF-007 | My Agents has an unnecessary right frame | Replace it with a direct responsive agent-card dashboard containing authoritative customer-relevant summaries. |
| DF-008 | Every portal feature should be conversational | Provide one persistent, contextual conversation surface with distinct Guide and relationship-professional scopes. |
| DF-009 | Top menu should use ChatGPT-like spatial clarity | Keep a persistent compact top bar with current context and a server-projected contextual work action, not a generic `New chat`. |

## 3. Authority And Stops

Authorized changes are limited to architecture/API specifications, Business Platform public
contracts and orchestration, generated clients, Customer Portal implementation, focused data
migrations only if the accepted interaction contract requires durable state, tests, and an unmerged
pull request.

No live cloud mutation, deployment, DNS change, Production change, provider credential, customer
traffic, PR approval, or merge is authorized. Razorpay credentials remain external input. The work
must stop if it requires weakening tenant isolation, accepting browser-derived authority, bypassing
explicit disclosure or confirmation, treating model output as a committed command, or coupling a
public/mobile client directly to Professional Runtime or a model provider.

## 4. Experience Architecture

### 4.1 Persistent Customer Shell

All customer routes share one authenticated route-group layout. The header, left navigation,
conversation surface, account controls and Emergency Stop remain mounted during internal
navigation. Next.js server components retain authorization and initial-data ownership; `Link`,
router transitions, Suspense and route loading boundaries provide application-like transitions.

The shell contains:

- a left icon rail, collapsed by default at compact widths and customer-expandable toward the right;
- a compact top bar showing current portal/relationship context and one authoritative contextual
  work action;
- a main content pane that streams route content without blanking the shell; and
- a persistent contextual conversation pane that is resizable on desktop and a sheet/full-screen
  view on mobile.

Internal routes use client navigation. Ordinary anchors remain valid only for fragments, downloads
and external destinations. Presentation preference may be local; identity, authorization, active
relationship, unread position and lifecycle state remain server-owned.

### 4.2 Navigation And Top Bar

Collapsed navigation shows icons with accessible names and tooltips. Expanded navigation shows the
label below each icon, a visible active state and relationship-scoped history where applicable. The
toggle exposes `aria-expanded` and `aria-controls`, supports Escape and restores focus.

The top bar contains the navigation toggle, compact WAOOAW identity, current context, contextual
work action, attention indicator, bounded connection/evidence state, preferences, account control
and persistent Emergency Stop when a relationship is active. The contextual action comes from a
server-owned projection. Examples include `Interview agent`, `Configure Maya`, `Review alert`,
`Discuss results` and `Explain this bill`; it opens the corresponding conversational workflow and
does not itself commit a consequential action.

### 4.3 Marketplace And Disclosure

Business Platform returns a canonical customer route/reference for each offer. The browser does not
transform `professionalType` into a slug. Each offer card uses customer-facing identity and outcome
language, concise suitability/proof, transparent price/trial terms, and distinct `Start trial` and
`Hire` actions.

Either action opens an intent-specific disclosure as step one. Disclosure presents scope, outcomes,
limits, commercial consequence, customer rights and a link to applicable Terms and Conditions in a
scannable format. Continue requires explicit acceptance. Cancel and Not now produce no relationship,
contract, trial, payment or authority mutation.

The continuation is bound to professional type, professional version, intent, disclosure revision
and idempotency key. Registration may establish identity/account prerequisites, but it does not
silently start Trial or Hire. Business Platform owns the explicit creation/start command and returns
the authoritative resume destination.

### 4.4 My Agents

My Agents is an unframed responsive dashboard of relationship-bound agent cards. It has no permanent
secondary right frame. Empty state is one focused Marketplace invitation.

Each card may show only owner-projected facts:

- customer-approved identity, professional type/version and Trial/Live/Stopped state;
- configuration progress and next required action;
- skills, verified goal and pending decisions;
- availability, current work, latest activity and blockers;
- evidenced performance summary and freshness; and
- plan/trial, actual/forecast/next-charge and reconciliation state.

Business Platform provides one dashboard summary projection. The browser does not perform per-card
fan-out, join domain facts, invent a score or infer freshness. The primary card action uses the
authoritative resume target.

## 5. Channel-Neutral Customer Interaction Contract

### 5.1 Scopes

One versioned interaction protocol supports two explicit scopes:

- `PORTAL`: WAOOAW Guide for discovery, navigation, account help, cross-agent summaries and
  explanations. It cannot impersonate an employed professional or claim relationship authority.
- `RELATIONSHIP`: the selected professional's durable relationship conversation. It requires an
  authorized `relationshipId` and uses the existing canonical timeline and Stop behavior.

The UI always identifies the active scope and selected professional. Switching scope never copies
protected content, drafts, commands or authority across relationships.

### 5.2 Public Contract

The OpenAPI-first contract exposes reusable operations for:

- opening or reading an authorized interaction context;
- listing and sending durable messages with opaque cursor reconciliation;
- streaming canonical events with SSE and polling fallback;
- updating read position and retrying/cancelling by original idempotency identity;
- returning typed response blocks and action capabilities; and
- submitting an exact typed command with expected versions, consequence metadata and explicit
  confirmation where required.

Clients may send locale, supported presentation capabilities, current surface and opaque selected
resource references. The server re-authorizes every reference and obtains all business facts from
their owners. Web uses a same-origin BFF, mobile uses generated OpenAPI clients with OIDC
Authorization Code plus PKCE, and WhatsApp remains a signed adapter. No client calls a model,
Professional Runtime or private domain service directly.

### 5.3 Structured Responses And Commands

Responses may contain text plus versioned blocks for professional offers, disclosures, navigation,
configuration proposals, decisions, plans, deliverables, performance, billing, evidence and
reconciliation. Unsupported blocks fail visibly and safely.

Natural language may request, explain or prepare work. A consequential operation executes only from
a server-issued typed capability containing the exact subject, expected revision, consequence tier,
expiry and idempotency requirements. The UI distinguishes proposal, confirmation, accepted command,
execution, reconciliation and evidenced completion.

## 6. Security, Privacy And Constitutional Controls

- Tenant and participant identity derive only from the validated token.
- Portal context, URL state, model output and channel possession never grant authority.
- Every protected resource reference is re-authorized at the Business Platform boundary.
- Relationship conversations, drafts, cursors and commands remain relationship-isolated.
- Browser storage may retain presentation preferences and relationship-keyed unsent drafts only;
  protected projections and authority are never cached as truth.
- Payment credentials remain exclusively in Razorpay-hosted collection.
- Terms/disclosure acceptance, step-up authentication, budget/scope confirmation and Emergency Stop
  remain independent controls.
- Logs and metrics exclude message content, credentials, secrets and unnecessary personal data.

## 7. Delivery Components

| Component | Output |
|---|---|
| WC096-01 Contract | Accepted OpenAPI models and operations for canonical offer route, Trial/Hire continuation, dashboard cards and portal interaction scope |
| WC096-02 Shell | Unified customer route layout, client navigation, loading boundaries, collapsible rail and contextual top bar |
| WC096-03 Acquisition | Engaging cards, canonical disclosure routing, direct Trial/Hire, Terms and explicit continuation |
| WC096-04 My Agents | Direct dashboard cards backed by one authoritative summary projection |
| WC096-05 Conversation | Persistent Guide/Professional pane, generic typed blocks and contextual workflow launch |
| WC096-06 Channel reuse | Generated client coverage and contract proof for web, mobile-compatible OAuth usage and WhatsApp adapter parity |
| WC096-07 Qualification | Unit, contract, integration, browser, accessibility, responsive and security evidence |

## 8. Acceptance Criteria

| ID | Acceptance condition |
|---|---|
| WC096-A01 | Marketplace disclosure navigation resolves the exact DMA offer; no type-to-slug browser derivation exists. |
| WC096-A02 | Trial and Hire are distinct, disclosure-first and preserve exact professional/version/intent through registration and continuation. |
| WC096-A03 | Cancel/Not now produces no relationship, trial, contract, payment or authority state. |
| WC096-A04 | Desktop internal navigation creates no full-document request and does not remount the customer shell. |
| WC096-A05 | Content-local pending UI appears immediately and does not shift stable shell controls. |
| WC096-A06 | Left navigation collapses/expands accessibly, opens rightward and satisfies desktop, tablet, mobile, RTL and 200-percent text behavior. |
| WC096-A07 | My Agents renders direct cards with authoritative summary/freshness/blocker states and no right frame or per-card request fan-out. |
| WC096-A08 | Context action and conversation scope update correctly for Marketplace, My Agents, relationship, alert, performance, billing and settings surfaces. |
| WC096-A09 | Portal Guide cannot execute relationship commands or impersonate a professional; cross-relationship context and draft isolation pass. |
| WC096-A10 | Consequential chat actions require typed capability, expected version, idempotency and explicit confirmation; replay yields one outcome. |
| WC096-A11 | Web and WhatsApp project the same canonical relationship result; mobile-client contract generation succeeds without a web dependency. |
| WC096-A12 | Session expiry, direct/deep links, back/forward, offline/reconnect, authorization denial and Emergency Stop remain fail-closed. |
| WC096-A13 | Keyboard, focus, screen-reader announcements, reduced motion and WCAG 2.2 AA checks pass across supported viewports. |
| WC096-A14 | Existing Business Platform and Web coverage thresholds, lint, type checking, build and applicable constitutional gates pass in Docker. |

## 9. Engineering Sequence

1. Update OpenAPI and owner projections first; regenerate clients and lock compatibility tests.
2. Repair canonical offer routing and implement explicit disclosure/Trial/Hire continuation.
3. Consolidate customer layouts and convert internal navigation to persistent client transitions.
4. Implement navigation rail, contextual top bar and content-local loading boundaries.
5. Implement the My Agents dashboard against one aggregate projection.
6. Extend conversation contracts for portal scope and generic typed blocks; preserve the existing
   relationship protocol and channel handoff semantics.
7. Integrate contextual conversation workflows surface by surface.
8. Run focused checks after each slice, then full Docker qualification and author review.

## 10. Evidence And Non-Claims

Implementation evidence must distinguish unit/contract proof, local exact-image proof, browser proof,
emulated channel proof and real deployed acceptance. Local or emulated evidence does not establish
Demo deployment, WhatsApp provider acceptance, mobile application acceptance, Razorpay merchant
readiness, UAT or Production readiness.

## 11. Rollback

Each delivery slice remains revertible without deleting customer records. API additions remain
backward compatible through their accepted version window. UI rollback returns to the prior shell
while preserving canonical relationships, conversations, commands, evidence and billing state.
Rollback must never rewrite history, reuse an idempotency identity for changed material or claim
that an accepted consequential action did not occur.

## 12. Qualification Evidence

- Business Platform: `714/714` tests passed in the repository `test-runner-dotnet` image; raw
  Cobertura result was 77.64% lines and 65.07% branches across the full instrumented assembly.
- Web: `57/57` suites and `356/356` tests passed; coverage was 91.65% statements, 81.71% branches
  and 94.61% lines. Lint, TypeScript and the Next.js production build passed in the Playwright image.
- Browser: WC-096 desktop/360px acceptance passed `5` applicable cases with `1` compact-only skip;
  final focused professional-conversation checks passed for desktop/360px, including Stop access,
  and authoritative offline reconciliation passed in compact Chromium.
- Contract and data: OpenAPI validation completed with zero errors, SQLFluff passed, PostgreSQL
  initialization passed, and an application-role RLS probe returned `1` owner row and `0` rows for
  another tenant.

This is local exact-image and emulated-browser evidence only. It does not establish deployment,
provider or mobile-device acceptance, customer traffic, UAT, Production readiness, PR approval or
merge.