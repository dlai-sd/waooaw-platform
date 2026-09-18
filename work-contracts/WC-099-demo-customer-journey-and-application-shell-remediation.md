# WC-099 - Demo Customer Journey And Application Shell Remediation

## Record Control

| Field | Value |
|---|---|
| Office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-18 continuous working conversation |
| Status | DRAFT FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED |
| Delivery shape | One atomic remediation iteration; partial defect closure is not completion |
| Trigger | Founder Demo acceptance findings after WC-095 through WC-098 deployment |
| Scope owners | Web Application, Business Platform, Demo environment configuration |
| Implementing office | Platform IT Expert operating in INST-010 Runtime Implementation Professional Decision Space, only after current-session Founder authorization |
| Requested review | Founder-requested single-pass institutional author review on 2026-09-18; dispositions recorded in Section 15 |
| Environment branding variance | Founder accepted the Azure Container Apps technical origin for Demo on 2026-09-18; WAOOAW-domain provider branding remains mandatory before UAT or Production traffic |
| Predecessors | WC-092, WC-093, WC-094, WC-095, WC-096, WC-097 and WC-098 |
| Governing architecture | Hybrid Application Shell; Hybrid Application Visual System; Customer Portal; Identity; Employment Lifecycle |
| Constitutional basis | C-001, C-002, C-023, C-042, C-049, C-059, C-063, C-065, C-071 and C-076 |

## 1. Authority And Decision Space

This Work Contract records every defect reported by the Founder during the 2026-09-18 Demo review,
the evidence-backed impact analysis, and an implementation-ready remediation boundary. The Solution
Architect may define component responsibilities, integration behavior, interface outcomes, layout
composition, acceptance conditions and evidence requirements.

This document does **not** authorize implementation code, database changes, generated clients,
secret creation, cloud mutation, deployment, customer traffic, PR approval or merge. Before any
runnable implementation begins, the Founder must explicitly authorize that implementation for the
current session. Demo configuration changes require separately valid environment authority.

The implementing agent must not reinterpret, split, defer, downgrade or silently omit a defect. A
scope change requires a written Founder-approved amendment to this Work Contract. Discovery of an
architectural contradiction stops the affected work and returns it to the Solution Architect; it is
not resolved privately in implementation.

The Founder explicitly requested this document's single-pass institutional author review. That
request authorizes the review and amendment of this draft, not implementation or environment
mutation. Institutional perspectives in Section 15 are bounded reviews of one authored contract;
they do not activate an institution, constitute independent acceptance, or replace Founder approval.

## 2. Atomic Outcome

Deliver one coherent customer journey in which a customer can:

1. understand WAOOAW's information use before selecting Google;
2. select the intended Google account after logout or account switching;
3. enter a visibly complete authenticated destination without a blank shell;
4. start Trial or Hire using the internally resolved customer membership identity;
5. see the resulting relationship in My Agents;
6. use the Guide without configuration failure, clipping or collision with account controls; and
7. move between portal routes within stable, space-efficient, responsive application chrome.

All eleven defects in Section 4 form one acceptance set. Passing tests for a subset, hiding a failed
state, or proving only API health does not satisfy this outcome.

## 3. Evidence Baseline And Confidence Rules

The baseline is read-only source inspection and retained Azure Container Apps console telemetry from
the Demo deployment beginning 2026-09-18 04:09 UTC. Console logs are not distributed traces, so the
contract distinguishes confirmed causes from hypotheses.

| Evidence | Observed result | Architectural conclusion |
|---|---|---|
| Acquisition continuation | 3 of 3 observed requests returned HTTP `403` | Trial and Hire fail before relationship creation |
| My Agents relationship reads | 30 of 30 observed requests returned HTTP `200` | Empty My Agents is downstream of failed acquisition, not a list endpoint outage |
| Guide operations | Repeated HTTP `500`; 8 recorded HMAC-key exceptions | Guide is operationally unavailable in Demo |
| Guide configuration | No `Conversation:CursorHmacKey` environment/secret binding; service requires at least 32 characters | Missing Demo binding is the confirmed Guide failure |
| Identity provider projection | 5 of 5 observed calls returned HTTP `200` | First-login retry is not proven to be a provider API outage |
| Acquisition identity path | Membership middleware resolves an internal account; acquisition attempts to parse the external broker subject as an internal GUID | Confirmed identity-boundary defect |
| Auth interaction | Authenticated login auto-continues; Google launch does not require account selection | Confirmed silent prior-account reuse risk |
| Auth disclosure | No WAOOAW information-use disclosure precedes provider handoff | Confirmed customer disclosure gap |
| Application home | Authenticated `/home` is redirect-only and renders no destination content while resolution is pending | Confirmed blank-shell design defect |
| Application shell | Route-varying controls share horizontal space; navigation width can change; Guide and account drawer share stacking level | Confirmed structural layout instability/collision risk |

For D-001, implementation must first add or use bounded timing/state evidence to locate the first
failing or delayed boundary. It must not claim a root cause from the current provider `200` evidence.
The acceptance condition still applies even if the final repair is only in Web transition handling.
The diagnostic record must distinguish route render, provider projection, launch command, broker
redirect and callback/session resolution; carry one opaque correlation identifier and monotonic
duration per transition; and exclude provider subject, email, tokens, authorization material and URL
query values. It must record a stable reason code before showing retry.

## 4. Founder-Reported Defect Register

The wording below preserves every reported symptom and its impact. Severity reflects customer harm,
not implementation size.

| ID | Founder-reported defect | Evidence-backed cause or status | Customer/business impact | Severity |
|---|---|---|---|---|
| D-001 | First login shows loading and then asks the customer to retry | Cause not yet proven; observed provider projection calls succeeded | Damages first-use confidence and may cause abandonment | High |
| D-002 | No WAOOAW information-use disclosure before Google handoff | Required provider scopes are requested without a WAOOAW pre-handoff explanation; external OAuth branding is incomplete | Customer cannot make an informed privacy choice; trust and consent-quality risk | High |
| D-003 | Login after logout silently resumes the previous Google account | WAOOAW/Keycloak logout does not guarantee browser-level Google account selection; login auto-continues an available SSO session | Wrong-account and shared-device privacy risk | High |
| D-004 | `/home` displays an empty customer shell until another menu is selected | Redirect-only route has no stable pending/destination presentation | Portal appears broken immediately after successful authentication | High |
| D-005 | Trial and Hire continuation fail | Internal membership identity is discarded and external broker subject is parsed as an internal GUID; observed requests return `403` | Both core acquisition journeys are blocked | Blocker |
| D-006 | Trial agent is absent from My Agents | No relationship exists because acquisition failed; list endpoint itself remains healthy | Customer is led to believe Trial succeeded although no agent was created | Blocker - same acquisition root |
| D-007 | Header elements move between pages | Route-varying labels/actions compete in a horizontal header and navigation expansion changes geometry | Highly visible instability reduces engagement, confidence and perceived quality | High |
| D-008 | Portal typography is oversized and inconsistent | Application headings exceed the ratified 32px H1 / 24px H2 scale and chrome families do not share one hierarchy | Low information density, poor scanning and unfinished visual quality | High |
| D-009 | Guide overlays content/account menu, clips interaction and cannot be resized | Fixed overlay, conflicting stacking, viewport-height assumptions and no split-pane contract | Blocks account controls and prevents reliable Guide use | High |
| D-010 | Guide is unavailable | Demo lacks the required cursor-HMAC binding and Guide operations fail closed with `500` | All Guide history and send operations fail | High |
| D-011 | `Verified - AAL2_ACCOUNT` consumes a separate top-bar item | Internal assurance code is exposed as global chrome rather than customer-facing account detail | Wastes space, contributes to movement and confuses customers | Medium |

## 5. Non-Negotiable Architecture Decisions

### 5.1 Identity And Disclosure

1. Keycloak remains the identity broker. Web does not call Google directly and no provider scope is
   added by this contract.
2. Before the first Google handoff, WAOOAW presents a concise disclosure naming the information it
   requests and why. The customer explicitly continues or cancels. Provider-owned consent remains
   provider-owned; WAOOAW must not imply that its disclosure replaces Google consent.
3. Logout continues to clear WAOOAW and Keycloak session state. The next explicit Google login or
   account-switch command must permit account selection rather than silently assuming the prior
   Google identity.
4. A valid current WAOOAW session may resume its safe destination without repeatedly showing the
   disclosure. A new provider launch after explicit logout/account switch must not bypass selection.
5. Loading, retry, cancellation, provider unavailability and callback failure are distinct visible
   states. No state may leave provider commands permanently disabled or report authentication success
   before the server-authoritative session exists.
6. The localized disclosure must preserve this exact English source meaning: **“WAOOAW will receive
   your name, email address, profile information and Google account identifier to sign you in,
   identify your WAOOAW account, and support registration only when you explicitly choose it.
   WAOOAW does not receive your Google password.”** It links to the WAOOAW Privacy Notice and exposes
   distinct `Continue to Google` and `Cancel` commands. No preselected checkbox or bundled employment,
   payment, marketing or platform consent is permitted.
7. Demo may continue to show its Azure Container Apps technical origin under the Founder-approved
   environment variance; this does not waive the WAOOAW disclosure in item 6. Before UAT or Production
   traffic, the external broker/provider screen must identify WAOOAW through the approved
   merchant/application display name and approved WAOOAW public identity origin. Repository readiness,
   provider-console configuration and public-origin/DNS mutation remain separate evidence classes and
   require their own valid owners and environment authority.

### 5.2 Customer Identity And Acquisition

1. Customer Membership Middleware remains the owner of the internal customer account/membership
   resolution for membership-required Business Platform routes.
2. Acquisition consumes that resolved internal identity. It must never parse or reinterpret an
   external broker `sub`/participant identifier as the internal customer account GUID.
3. Trial and Hire share the corrected identity boundary but preserve their distinct intent,
   disclosure, commercial and evidence semantics.
4. A successful continuation is exactly-once and replay-safe. Retry cannot create duplicate
   relationships, agent instances, trials, contracts or payment obligations.
5. My Agents remains a projection of authorized relationships. It must not fabricate a relationship
   locally to compensate for an acquisition failure.
6. The same accepted acquisition result must become visible through My Agents without logout,
   unrelated menu navigation or browser refresh.
7. Acquisition records and evidence retain the resolved internal account, membership, tenant, actor,
   intent and idempotency bindings as separate meanings. External broker subject remains an identity
   binding input and is never stored or projected as the internal account identifier.

### 5.3 Authenticated Entry

1. `/home` must resolve to a visible, server-authorized destination or a bounded skeleton/status that
   occupies the final content geometry. It may not render an unexplained empty shell.
2. Zero relationships resolves to Marketplace. One or more retained relationships resolves to My
   Agents or the architecture-approved most-recent relationship destination.
3. Temporary identity or relationship-read unavailability renders an explicit recoverable state;
   it does not masquerade as an empty account or redirect loop.
4. Direct navigation, refresh and client transition must produce the same authorized destination.

### 5.4 Authenticated Application Shell

The Founder-directed shell replaces the fixed authenticated horizontal top menu. Public and auth
page headers are outside this decision and retain their separately approved composition.

#### Expanded Desktop Composition

```text
+----------------+--------------------------------------------------+
| WAOOAW logo    |                                     [User icon]  |
|                |                                                  |
| My Agents      | Page content / relationship workspace            |
| Marketplace    |                                                  |
| Alerts         |                                                  |
| Settings       |                                                  |
|                |                                                  |
| Language       |                                                  |
| Theme          |                                                  |
+----------------+--------------------------------------------------+
```

1. The authenticated shell has no full-width horizontal top bar.
2. A persistent left rail reaches the viewport's top and bottom edges. It owns the WAOOAW logo at
   the top, primary navigation in the middle, and language/theme controls at the bottom.
3. The content origin is stable across every route, status, locale, account state and navigation
   interaction. The content grid reserves a 76px compact rail. Expanding to 184px overlays only the
   additional 108px above the content layer; it does not change the content grid, scroll position or
   page width. The rail collapses on Escape and after mobile destination selection.
4. The rail uses two stable modes: 76px compact mark/icons and 184px expanded logo/labels. Icon-only
   controls have accessible names and tooltips. Expansion state is non-authoritative presentation
   preference; it must not contain or reveal account, relationship or conversation data.
5. Only the user icon floats at the top-right of the content canvas. It is a 44px minimum stable
   control with a reserved inset and cannot shift page headings or content.
6. The user menu contains Profile, Billing, Settings, account switching, sign out and the
   customer-facing assurance statement. It opens into available space above the Guide and restores
   focus to the user icon when closed.
7. Internal code `AAL2_ACCOUNT` is not global chrome. Present it in plain language within account
   security detail, for example `Account security: Verified`, while retaining exact internal data
   only where diagnostically authorized.
8. Emergency Stop remains persistently reachable and is not hidden in the user menu, left-rail
   overflow, Guide or route content.
9. Application H1/H2/H3 typography follows the ratified 32px/24px/20px scale. Public hero display
   typography is not changed by this contract. Text does not scale with viewport width.
10. The shell uses the semantic token system, supports light/dark themes and all supported locales,
    and does not introduce decorative cards, gradients or new brand treatment.

#### Compact And Mobile Composition

1. Mobile global routes use `My Agents`, `Marketplace` and `Alerts` in the stable bottom navigation;
   Settings remains in the account flow. Relationship routes use exactly `Conversation`, `Plan`,
   `Work` and `WaooaW Experts` as required by the ratified shell. No desktop rail is compressed into
   unusable width and changing contexts must not leave stale destinations selected.
2. The compact user icon remains reachable without creating a horizontal header.
3. Language, theme, Profile, Billing, Settings, account switching and sign out remain reachable from
   the mobile account/settings flow.
4. Content respects safe areas, software keyboard, 200% text zoom and RTL direction. No fixed control
   covers the first heading, final action, composer or Emergency Stop.

### 5.5 Guide Workspace And Configuration

1. Demo receives one generated, secret-backed `Conversation:CursorHmacKey` of at least 32 characters
   through the approved environment rendering and secret-reference path. The value never appears in
   source, logs, PR text, screenshots or evidence.
2. Startup/readiness must expose missing or invalid Guide configuration before customer traffic.
   A healthy container with an unusable Guide is not a passing deployment.
3. On expanded desktop, Guide opens as a right-side workspace pane, not a fixed overlay. It has
   a 320px minimum width, 400px default width and 560px maximum width, further bounded so the primary
   workspace remains at least 480px wide. Below that fit threshold it changes to the compact sheet or
   route treatment. Its separator supports pointer drag and keyboard Arrow adjustments with Home/End
   to minimum/maximum and exposes separator/value semantics.
4. Opening Guide reduces the designated content workspace only when sufficient width exists; it does
   not cover the account menu, page controls, lifecycle actions or Emergency Stop.
5. At intermediate/compact widths, Guide uses an accessible sheet or full-screen route with explicit
   close, focus containment and focus restoration. It never compresses primary content below its
   architectural minimum.
6. Timeline and composer form one viewport-bounded layout. The message input and send command remain
   visible at default zoom, 200% zoom and with long translated text.
7. Guide width preference may be retained as non-authoritative local presentation state. It cannot
   contain customer, relationship, conversation or cursor data, alter relationship authority, or
   leak across customer isolation boundaries. Sign-out and account switch clear it with the other
   WAOOAW presentation state.
8. GET history, send, retry, empty, loading, unavailable and recovery states remain truthful. Web
   does not convert an HTTP `500` into an empty successful conversation.
9. Cursor-key rotation must not lose or rewrite messages. A cursor signed by a retired key either
   remains valid during the catalog-declared overlap or receives an explicit stale/reconciliation
   outcome that triggers a separately authorized complete reload. It is never treated as empty,
   malformed content success or authority.

### 5.6 Data And Persistence Effects

1. No new customer, relationship, conversation, consent or constitutional ledger is introduced.
2. The acquisition repair uses existing relationship, instance, idempotency and evidence persistence
   contracts. A schema migration is expected to be unnecessary; if implementation proves otherwise,
   the implementing office must stop for Data Architect and Solution Architect review before writing
   a migration.
3. The WAOOAW pre-provider disclosure is a presentation acknowledgement that permits one provider
   launch. It is not constitutional evidence, employment consent or a durable customer profile fact.
   Telemetry may record only disclosure version, outcome class, time and opaque correlation.
4. Guide messages remain in their existing authoritative persisted conversation. Resizing, rail mode,
   account-menu state and loading state are non-authoritative browser presentation only.
5. Cursor invalidation and account/relationship switching clear in-memory projections without
   deleting or rewriting authoritative messages, relationships or evidence.

## 6. Component Ownership And Change Boundary

| Component | Required responsibility | Prohibited drift |
|---|---|---|
| Web authentication | Disclosure, launch states, account-selection intent, safe return and bounded retry presentation | No direct Google integration, new scope or browser-owned authentication truth |
| Identity/public-origin configuration | Approved WAOOAW provider display and public broker origin | No incidental ACA hostname as customer identity; no mutation without environment/provider authority |
| Web application layout | Stable entry resolution and authenticated shell composition | No changes to approved public/auth headers unless required by D-001 to D-003 and explicitly evidenced |
| Web navigation/preferences | Left-rail placement, fixed geometry, locale/theme persistence and responsive access | No duplicate preference stores or route-specific shell forks |
| Web account controls | Floating user command, account menu, plain-language assurance | No hidden Emergency Stop and no internal assurance code as primary customer copy |
| Web Guide workspace | Resizable desktop pane and compact sheet/route with truthful states | No fixed overlay over customer work; no local fake success |
| Business Platform membership/acquisition | Consume resolved internal membership identity and preserve exactly-once continuation | No external-subject GUID parsing and no second customer identity model |
| Business Platform relationship projection | Return authorized resulting relationship | No special-case synthetic Trial item |
| Business Platform conversation | Validate cursor key and provide persisted Guide history/send semantics | No weak/default production secret and no fail-open cursor signing |
| Demo environment renderer | Generate/reference/bind Guide cursor-HMAC material and prove readiness | No manual portal secret, plaintext value or Demo-to-Production inference |

No new deployable service, identity store, relationship aggregate, navigation framework, theme system
or conversation protocol is authorized. Public API or schema changes require OpenAPI-first update and
generated-client drift evidence. If no contract shape changes, implementations must preserve the
existing API surface.

## 7. Requirement-To-Source-To-Executable-Evidence Matrix

Every row is normative. `PASS` requires both the behavior and listed evidence at one exact candidate
head/image tuple. A substitute test or aggregate suite count cannot close a row.

| Requirement | Defect trace | Owning surface | Required executable evidence |
|---|---|---|---|
| R-001 First login reaches provider selection or a specific recoverable state without an unexplained retry | D-001 | Web auth route, provider command and identity projection boundary | Focused state/timing tests plus clean-browser Chromium, Firefox and WebKit journey; retained failure reason evidence |
| R-002 WAOOAW disclosure appears before first Google handoff and cancel performs no handoff | D-002 | Web auth UI | Unit assertions for exact scope-purpose content and explicit continue/cancel; browser network assertion that cancel launches no provider request |
| R-003 Explicit post-logout/account-switch login permits Google account selection | D-003 | Web auth command and Keycloak launch contract | Browser journey proving logout, second login and account-choice prompt/selection intent; no stale WAOOAW session |
| R-004 `/home` never displays unexplained blank shell | D-004 | Authenticated home/layout | Direct-load, refresh, client-transition, zero/one/many relationship and upstream-unavailable browser tests with visible-state assertions |
| R-005 Trial continuation uses resolved internal membership and succeeds once | D-005, D-006 | BP middleware/acquisition | Focused integration test with non-GUID external subject and valid internal account; HTTP success plus one relationship/instance/evidence result |
| R-006 Hire continuation uses the same corrected identity boundary without weakening commercial gates | D-005, D-006 | BP acquisition | Focused integration tests for valid hire, missing disclosure/admission/evidence denial and replay; no duplicate obligation |
| R-007 Resulting Trial/Hire appears in My Agents without refresh or unrelated navigation | D-005, D-006 | BP projection and Web My Agents | End-to-end Trial and Hire journeys asserting returned relationship identity and visible list item |
| R-008 Authenticated desktop has no horizontal top menu and rail reaches both viewport edges | D-007 | Web shell | Desktop semantic and screenshot assertions at 1280x720, 1440x900 and 1920x1080 |
| R-009 Route changes and rail expansion do not move content origin, logo or user control | D-007 | Web shell/navigation | Pixel/geometry assertions before/after every primary route and rail mode; maximum 1px rendering tolerance |
| R-010 Logo, primary links, language/theme and user controls follow Section 5.4 placement | D-007, D-011 | Web shell/navigation/account | DOM-order, keyboard-order, accessible-name and screenshot assertions in compact/expanded, LTR/RTL and light/dark states |
| R-011 Assurance is plain-language account detail, not separate top chrome | D-011 | Web account menu | Component and browser assertions; customer-visible DOM contains no `AAL2_ACCOUNT` |
| R-012 Application typography uses 32/24/20px hierarchy without clipping | D-008 | Web visual system/application pages | Computed-style and screenshot assertions on Home destination, Marketplace, My Agents, Alerts, Settings, Profile and relationship views |
| R-013 Guide configuration is valid before Demo traffic | D-010 | Environment renderer and BP startup/readiness | Docker-rendered environment tests; exact candidate startup/readiness with secret reference and no secret disclosure; negative missing/short-key tests |
| R-014 Guide history and send work after deployment | D-009, D-010 | BP conversation and Web Guide | Persistence/reload integration test and authorized Demo smoke test showing successful GET/POST without logging content or secrets |
| R-015 Guide is a resizable non-overlapping desktop pane | D-009 | Web Guide workspace | Pointer and keyboard resize tests at min/default/max widths; geometry assertions against account menu, content actions and Emergency Stop |
| R-016 Compact Guide is accessible and keeps composer/actions visible | D-009 | Web Guide workspace | 360x800 and 390x844 Chromium/Firefox/WebKit tests; focus trap/restore, keyboard, 200% zoom, long Hindi and Urdu text |
| R-017 Theme and language remain durable after relocation | D-007, D-008 | Web preferences and shell | Existing preference tests plus route/reload browser tests for every supported locale option, RTL, light and dark |
| R-018 Emergency Stop remains persistently reachable in all shell/Guide/account states | D-007, D-009 | Web shell and Stop control | CCT-HO-02 plus desktop/mobile geometry, keyboard and z-order assertions |
| R-019 No regression to tenant, participant, relationship or conversation isolation | D-003, D-005, D-006, D-009, D-010 | BP and Web server boundaries | Two-tenant/two-participant hostile integration tests; unauthorized IDs remain non-enumerating |
| R-020 One exact release passes the whole Founder acceptance journey | D-001 through D-011 | Integrated candidate | Clean-profile Login -> disclosure -> registration/resume -> Trial -> My Agents -> Guide -> logout -> account selection -> Hire journey, with screenshots and sanitized endpoint outcomes |
| R-021 UAT/Production provider handoff identifies approved WAOOAW brand and public identity origin | D-002 promotion gate; Founder-deferred for Demo | Identity/public-origin configuration and authorized provider setup | Before UAT/Production traffic: rendered-origin/configuration proof plus authorized clean-browser provider screenshot/semantic assertion; incidental cloud hostname is absent as application identity |
| R-022 Cursor-key rotation preserves conversation truth | D-009, D-010 | Environment catalog, BP conversation and Web recovery | Current/prior/retired key tests proving overlap or explicit reconciliation, complete reload and zero message loss/duplication |
| R-023 No unintended persistence model is added | D-002, D-005, D-006, D-009, D-010 | BP acquisition/conversation and Web presentation state | Schema-diff/migration assertion, browser-storage inspection, and persistence tests proving only existing authoritative records change |

## 8. Required Visual State Matrix

Visual qualification must test default state and interaction state. Capturing one wide desktop image
does not qualify responsive behavior.

| Dimension | Required states |
|---|---|
| Viewports | 360x800, 390x844, 768x1024, 1280x720, 1440x900, 1920x1080 |
| Routes | Marketplace, My Agents, Alerts, Settings, Profile, relationship workspace and `/home` resolution |
| Navigation | Compact, expanded, active route, long translated label |
| Account | Closed/open, assurance visible, Guide closed/open |
| Guide | Closed, default width, minimum width, maximum width, long timeline, composer focused, unavailable/recovered |
| Preferences | Light, dark, English, one long Indic locale and Urdu RTL |
| Accessibility | Keyboard-only, visible focus, reduced motion, 200% text zoom |
| Acquisition | Trial intent, Hire intent, pending, success, replay and truthful failure |

At every state, automated geometry must assert no incoherent overlap, clipping, horizontal page
scroll, content-origin shift or unreachable command. Screenshots supplement these assertions; human
inspection alone is insufficient.

## 9. Security, Privacy And Failure Requirements

1. Provider tokens, authorization codes, broker subjects, customer PII, conversation content and
   secret values do not enter screenshots, logs or PR evidence.
2. Internal account identity remains server-derived. Browser-supplied tenant/account IDs cannot
   select acquisition ownership.
3. Disclosure acceptance is bounded to the provider launch and purpose; it is not generalized into
   employment, contract, payment or marketing consent.
4. Cursor signing remains fail-closed. Demo readiness prevents traffic when configuration is invalid;
   implementation must not introduce a hardcoded fallback key.
5. Account and Guide surfaces are keyboard operable, close on Escape where appropriate, contain focus
   when modal/sheet semantics apply, and restore focus to their invoker.
6. Error presentation is customer-safe and correlation-capable. It distinguishes authentication,
   acquisition and Guide failures without exposing internals.
7. Existing CSP, CSRF, safe-return, idempotency, anti-enumeration, RLS and generated-client controls
   remain passing.
8. Account switch, sign-out, relationship switch, session expiry and authorization failure clear or
   invalidate prior protected browser projections, Guide cursors, optimistic state and back/forward
   restorability before another context renders.
9. Authenticated pages and API/RSC responses remain private and non-cacheable; the service worker
   cannot replay relationship, account or Guide truth as current.

## 10. Ordered Single-Iteration Work Plan

| Milestone | Scope | Exit condition |
|---|---|---|
| WC099-00 Contract freeze | Founder accepts this exact defect set, severity, shell composition and atomic completion rule | Written Founder acceptance or amendment; implementation separately authorized |
| WC099-01 Evidence harness | Reproduce all defects; add bounded D-001 diagnostics and geometry/customer-journey assertions that initially fail for the right reasons | Every R-001 through R-023 has an executable evidence owner; D-001's first causal state is confirmed before repair |
| WC099-02 Identity and acquisition repair | D-001 through D-006 | Disclosure/account selection/home behavior pass; Trial and Hire create exactly one authorized relationship and appear in My Agents |
| WC099-03 Stable shell and typography | D-007, D-008 and D-011 | Founder-directed rail/account composition and all R-008 through R-012/R-017/R-018 checks pass |
| WC099-04 Guide workspace and readiness | D-009 and D-010 | Secret-backed readiness, persisted interaction, resizable pane and compact accessibility checks pass |
| WC099-05 Integrated qualification | Entire Demo contract at one exact head and image tuple | R-001 through R-020 and R-022 through R-023 pass; R-021 carries only the recorded Demo variance; full affected suites, visual matrix, security checks and author review pass |
| WC099-06 Founder handoff | One unmerged PR with exact evidence package | No partial/deferred/untested row except the exact R-021 Demo variance; Founder receives PR for review and merge |

Milestones permit controlled implementation and review but do not permit separate completion claims.
The implementation PR is not ready while any defect or requirement remains partial, deferred,
untested, substituted or known-failing, except R-021 with the exact
`FOUNDER-DEFERRED-NOT-APPLICABLE-TO-DEMO` status. That status cannot authorize UAT or Production
traffic.

## 11. Qualification And Evidence Package

The implementing agent must attach or link sanitized evidence in the PR for:

- exact source head, immutable image digests and environment/revision identifiers;
- a defect closure table mapping D-001 through D-011 to R-001 through R-023;
- focused Web component, BP unit/integration, environment-renderer and browser results;
- full affected Web and Business Platform suites in repository-standard Docker containers;
- lint, type checking, production build, OpenAPI/generated-client drift checks when applicable;
- branch and line coverage at or above repository gates, with changed behavior directly exercised;
- the complete visual state matrix with automated geometry results and representative screenshots;
- accessibility results including axe, keyboard, focus, RTL, reduced-motion and 200% zoom;
- hostile tenant/participant/account identity, replay and missing/short-secret cases;
- authorized Demo smoke evidence for Login, Trial, My Agents, Guide, logout/account selection and
  Hire, clearly separated from local exact-image proof;
- provider-brand/public-origin evidence supplied by its authorized owner for UAT/Production
   promotion; Demo evidence records R-021 as `FOUNDER-DEFERRED-NOT-APPLICABLE-TO-DEMO`, never `PASS`;
- a machine-readable obligation ledger with requirement, source, test, raw-evidence reference,
   evidence class, result, residual risk and reviewer fields for R-001 through R-023;
- a secret/PII scan proving retained evidence contains no sensitive value; and
- author review against every normative sentence in this Work Contract.

All Python-based repository tooling, tests and evidence scripts must run in Docker. No Python virtual
environment may be created, activated or used. Actual cloud proof, local exact-image proof,
emulation/static proof and untested stages must remain explicitly distinguished.

## 12. Definition Of Done

WC-099 is complete only when all of the following are true at one exact candidate:

1. D-001 through D-011 each have a confirmed repair and direct executable evidence.
2. R-001 through R-020 and R-022 through R-023 are individually marked `PASS`; no row is partial,
   deferred, substituted or inferred from an aggregate count. R-021 is recorded as
   `FOUNDER-DEFERRED-NOT-APPLICABLE-TO-DEMO` and remains mandatory before UAT or Production traffic.
3. Trial and Hire each succeed through the real membership boundary and appear in My Agents without
   duplicates or unrelated navigation.
4. Authenticated pages have no horizontal top menu; the full-height left rail, floating user control,
   relocated theme/language controls and plain-language assurance match Section 5.4.
5. Route changes, locale changes, account/Guide state and rail interaction do not shift the stable
   content origin or cover customer controls.
6. Guide history and send succeed with approved secret-backed configuration, and the Guide is
   resizable/non-overlapping on desktop and accessible on compact layouts.
7. The full visual, accessibility, security, isolation, replay, build and regression gates pass.
8. The complete Founder acceptance journey R-020 passes in an environment explicitly authorized for
   that execution.
9. The PR contains the exact evidence package and no secrets or customer PII.
10. The implementing agent performs author review and hands one unmerged PR to the Founder. The agent
    does not self-approve, self-merge or claim Production readiness.
11. D-002's WAOOAW disclosure is proved in Demo. Provider branding/public-origin acceptance remains
   pending under R-021 and must be proved by its authorized owner before UAT or Production traffic;
   repository changes alone cannot satisfy that promotion gate.
12. No unintended data schema, durable disclosure-consent record, authenticated browser cache or
   parallel relationship/conversation truth has been introduced.

Passing unit tests, returning HTTP `200`, container readiness, visual screenshots without semantic
assertions, or fixing only the two Blocker defects is insufficient.

## 13. Stop Conditions And Explicit Exclusions

Stop and return for a Founder/architectural decision if implementation requires:

- new Google scopes or direct Google integration;
- a new deployable service, identity model, relationship aggregate or conversation protocol;
- weakening membership derivation, idempotency, RLS, CSP, CSRF, evidence or cursor signing;
- plaintext/manual secret handling or reuse of unrelated HMAC material;
- changing approved public-page visual composition outside the bounded auth defects;
- changing employment, payment, admission, authority or constitutional semantics;
- deferring any D-001 through D-011 item while claiming WC-099 completion; or
- Production mutation, customer traffic, PR approval or merge without separate authority.

Excluded unless separately amended are new identity providers, new professional capabilities,
payment-provider onboarding, broad public-site redesign, native mobile application work and unrelated
repository failures. Provider-console display-name/origin alignment and the minimum public-origin/DNS
work needed to close R-021 are included UAT/Production promotion requirements but are
Founder-deferred for Demo until their owning office has current mutation authority; they may not be
broadened into a provider migration, scope change or general DNS redesign.

## 14. Rollback And Post-Deployment Verification

The implementation plan must support independent rollback of Web, Business Platform and Demo
configuration while preserving compatibility. A rollback must not delete relationships, conversation
history, evidence or secrets. If a new secret reference is introduced and application rollback no
longer consumes it, retain or disable it according to approved secret-retention policy; never disclose
or manually copy its value.

After an authorized Demo deployment, verify the exact active revisions/images, execute R-020 once,
record R-021 as `FOUNDER-DEFERRED-NOT-APPLICABLE-TO-DEMO`, and exercise the non-destructive
cursor-rotation proof required by R-022 with sanitized evidence. Confirm no acquisition `403` from
the identity mismatch, no Guide HMAC `500`, no duplicate relationship, no blank `/home`, and no
shell/Guide overlap at the required viewports. This Demo result does not establish UAT or Production
readiness; those environments cannot receive traffic until R-021 passes.

## 15. Founder-Requested Institutional Author Review

This is one consolidated review/request/edit pass. It records the specialized perspective applied,
the gap found, the amendment made, and any remaining owner gate. It does not impersonate independent
acceptance or activate an institution.

| Perspective | Review finding | Draft amendment/disposition | Remaining owner gate |
|---|---|---|---|
| Solution Architect (INST-005) | Initial draft covered all symptoms but left several interfaces and completion meanings under-specified | Added deterministic component, integration, persistence and evidence contracts | Founder contract acceptance |
| Enterprise Architect (INST-004) | Full-height rail plus conversation/right pane fits the ratified three-region shell; no new container, domain or technology decision is required | CONCUR within existing Reference Architecture; public/auth layouts remain outside shell replacement | EA re-entry only if implementation requires a new service, domain or ADR |
| Constitutional Analyst (INST-002) | Disclosure could be misread as durable constitutional or employment consent; completion evidence needed explicit classification | Disclosure is one launch acknowledgement only; evidence classes and atomic completion remain explicit | No new claim proposed; Founder retains constitutional acceptance |
| Data Architect (INST-006) | Data effects, cursor rotation and browser presentation persistence were implicit | Added Section 5.6, rotation continuity and schema/migration stop condition | Re-review only if a schema migration or new durable fact is required |
| Security Architect (INST-007) | Account switching, browser restoration, provider branding boundary and secret rotation needed stronger controls | Added context invalidation, private caching, minimum telemetry, secret lifecycle and R-021/R-022 proofs | Provider/public-origin mutation requires authorized Security/Platform path |
| Platform Architect (INST-009) | A secret binding alone does not establish feature readiness; provider brand/origin spans manifest, DNS and external configuration | Added rendered-config, startup/readiness, active-revision and authorized external-screen evidence | Provider/DNS mutation authority is required before UAT/Production traffic; Founder deferred it for Demo |
| QA and Test Engineering (INST-015 perspective only) | Screenshots and aggregate counts could still mask missing obligations | Added machine-readable obligation ledger and direct visual/semantic/security evidence per requirement | INST-015 is not operational; it cannot independently accept or execute unless separately activated and routed |
| Platform IT Expert / Runtime Implementation Professional (INST-010) | Implementer needed exact responsive dimensions, mobile destinations, diagnostic fields and data-change boundary to avoid design-by-code | Added exact rail/Guide dimensions, mobile contract, D-001 telemetry and R-001 through R-023 implementation request | Current-session implementation authorization remains mandatory |

### 15.1 Platform IT Expert Single-Pass Implementation Request

Once explicitly authorized, Platform IT Expert must implement this as one bounded PR and one exact
candidate, in milestone order from WC099-01 through WC099-06. It must repair owning behavior rather
than tests, preserve unrelated dirty work, use existing libraries/patterns, run all Python tooling in
Docker without a virtual environment, and stop on every Section 13 condition. It may add focused
instrumentation and tests before repair, but it may not hand off a partial defect set as complete.

The expected impact surface is the existing Web authentication commands and routes, authenticated
home/layout, application shell/navigation/preferences/account controls, Guide workspace, Business
Platform membership/acquisition/conversation components, canonical environment renderer/secret
catalog, and their focused/full tests. Touching another service or domain requires a traceable reason
in the obligation ledger and must remain inside this contract's component boundaries.

### 15.2 Substantial External Gates

Only two non-document gates remain substantial:

1. **Implementation authority:** no source, test, build artifact or deployment work may start until
   the Founder explicitly authorizes WC-099 implementation for the current session.
2. **Provider/public-origin mutation authority:** R-021 requires approved external provider and DNS
   configuration before UAT or Production traffic. The implementing PR may prepare and validate
   repository configuration; the Founder-approved Demo variance permits Demo completion while this
   promotion gate remains pending.

Neither gate permits scope reduction. The first gate blocks all implementation. The second gate does
not block Demo completion under the recorded variance, but it blocks UAT and Production promotion.

### 15.3 Public-Origin Readiness Review - 2026-09-18

A read-only review of `https://www.waooaw.com` and `https://waooaw.com` found reusable public brand
content but did not establish R-021 readiness:

| Input | Live finding | R-021 treatment |
|---|---|---|
| Brand name and public proposition | Homepage identifies `WAOOAW - Agents Earn Your Business` and describes an AI Agent Marketplace | Reusable subject to Founder brand approval |
| Privacy notice | Genuine page exists at `/privacy/`, last updated 2026-03-29, and publishes `privacy@waooaw.com` | Reusable content; endpoint is not acceptable until TLS and canonical redirect defects are repaired |
| Terms | Genuine page exists at `/terms/`, last updated 2026-03-29, and publishes `legal@waooaw.com` | Reusable content; endpoint is not acceptable until TLS and canonical redirect defects are repaired |
| TLS | Apex and `www` return a certificate whose names cover only `cp.demo.waooaw.com`, `plant.demo.waooaw.com` and `pp.demo.waooaw.com` | Blocker for public UAT/Production branding URLs |
| Canonical redirects | `/privacy` and `/terms` redirect to insecure `http://www.waooaw.com:8080/.../` | Must redirect directly to the approved HTTPS canonical URL with no internal port exposure |
| Route truth | `/privacy-policy`, `/terms-of-service`, `/contact`, `/support`, `robots.txt` and `sitemap.xml` return the homepage shell with HTTP `200` | These are not valid policy/support/discovery resources; provider configuration must use only verified genuine endpoints |
| Logo asset | Public favicon exists but is 789x621; no stable approved square OAuth logo URL was discovered | Supply an approved square WAOOAW provider asset and stable HTTPS URL |
| Customer support | Public application bundle uses `customersupport@dlaisd.com`; no genuine `/support` page was found | Founder/owner must approve the support identity and publish a truthful WAOOAW support URL or address |
| Identity/application host | Common candidates `auth`, `identity`, `login`, `app` and `uat` under `waooaw.com` had no public DNS record | Platform owner must select exact UAT/Production application, identity and callback origins before configuration |

R-021 may pass only when the authorized owner proves all of the following in the target environment:

1. exact canonical WAOOAW application and identity hostnames are approved and resolve correctly;
2. valid publicly trusted certificates cover every advertised hostname;
3. HTTP and alternate-host redirects terminate at canonical HTTPS URLs without internal ports;
4. homepage, Privacy Notice, Terms and support destinations are genuine, stable and return truthful
   status/content rather than a generic fallback shell;
5. approved WAOOAW display name, square logo, homepage, Privacy Notice, Terms and support contact are
   configured in the provider screen;
6. Keycloak issuer, Web origin, provider authorized domain, redirect URI and post-logout URI match the
   same reviewed environment manifest exactly; and
7. clean-browser evidence shows WAOOAW identity and URLs with no incidental cloud hostname presented
   as the application identity.

The review did not test mailbox delivery, domain ownership verification, provider-console state or
DNS/control-plane ownership. Those remain owner-supplied evidence, not assumptions from public HTML.

## 16. Final Solution Architect Review

The contract stays within INST-005 Decision Space:

- existing Web, Business Platform and environment components retain ownership;
- no Reference Architecture service or domain boundary is changed;
- customer identity, relationship, constitutional evidence and conversation truth remain server-owned;
- the Founder-directed shell is specified as component composition and interaction contract;
- implementation details remain with the authorized implementing office; and
- every reported defect is bound to customer impact and direct executable evidence;
- Data, Security, Platform and constitutional meanings are explicit without introducing a new owner;
   and
- the only unresolved matters are protected execution authorities, not missing design decisions.

**Solution Architect disposition:** READY FOR FOUNDER CONTRACT REVIEW. IMPLEMENTATION REMAINS
UNAUTHORIZED UNTIL THE FOUNDER EXPLICITLY AUTHORIZES IT FOR A CURRENT SESSION.