# Customer Portal UI Coherence Component

**Document type:** Solution Architecture component contract and Work Component
**Office:** Solution Architect (INST-005)
**Status:** PROPOSED - FOUNDER REQUESTED; ENTERPRISE ARCHITECT REVIEW REQUIRED
**Delivery context:** PR #443 follow-up scope
**Constitutional basis:** C-001, C-023, C-042, C-049, C-059, C-063, C-065
**Architecture basis:** ADR-002, ADR-008, ADR-017
**Normative parents:** `architecture/reference/ux/hybrid-application-shell.md`,
`architecture/reference/ux/hybrid-ui-acceptance-contract.md`,
`architecture/reference/ux/hybrid-visual-system-contract.md`, and
`architecture/reference/components/identity-boundary.md`

## 1. Customer Outcomes

| ID | Customer outcome | Customer Portal behavior |
|---|---|---|
| CPUI-O01 | I can immediately find and use WAOOAW as a conversational work environment, not a hidden help widget. | The primary customer workspace exposes the active Guide or Professional context, durable conversation, structured work objects, and only server-issued actions. |
| CPUI-O02 | When I choose Trial or Hire as a new customer, I understand that I am creating an account and I never receive misleading returning-user login language. | The acquisition intent survives broker authentication and registration; each identity outcome renders intent-specific copy and recovery without conflating registration, login, policy denial, or dependency failure. |
| CPUI-O03 | The portal feels like one stable professional application while I move between destinations. | Shared chrome, logo, navigation, content origin, title typography, loading geometry, and focus remain stable across client transitions at supported widths. |

## 2. Component Responsibility

The **Customer Portal UI Coherence** component owns the behavioral composition that turns existing
identity, interaction, relationship, and navigation contracts into one continuous customer
experience. It has three primary subcomponents with non-overlapping responsibilities:

| Subcomponent | Primary responsibility | Does not own |
|---|---|---|
| Conversational Workspace | Present the selected Guide or Professional context, durable messages, typed work objects, composer, and available server-issued actions as a discoverable workspace. | Model execution, relationship authority, action eligibility, or business-state derivation. |
| Acquisition Identity Journey | Preserve Trial/Hire intent and render the exact anonymous, authenticated-visitor, registration-required, account-ready, denied, expired, and unavailable states. | Provider authentication, account creation, membership decisions, or relationship activation. |
| Stable Application Frame | Preserve one mounted shell and stable visual geometry, navigation, logo placement, page title hierarchy, focus, and loading boundaries across customer routes. | Public-site composition, domain-page content, or server authorization. |

The component decomposes the ratified hybrid application architecture. It does not create a new
frontend, redefine identity or relationship domains, or move authority into the browser.

## 3. Required Interfaces

### 3.1 Portal Interaction Projection

The Conversational Workspace consumes the approved Business Platform portal-interaction contract.
The projection identifies:

- active scope: `PORTAL` or `RELATIONSHIP`;
- selected context and authorized alternatives;
- authoritative cursor and durable message sequence;
- versioned text, Action, Plan, Deliverable, and Decision blocks; and
- server-issued capabilities with label, subject, effect, expiry, expected revision,
  confirmation requirement, and idempotency requirement where consequential.

Unsupported blocks or unavailable capabilities fail visibly. The browser does not convert message
text into authority, invent actions, infer relationship access, or call a model or private runtime.

### 3.2 Identity Journey Outcome

The Acquisition Identity Journey consumes typed outcomes from the approved identity boundary:

| Outcome | Required presentation |
|---|---|
| Anonymous with `REGISTER` intent | `Create your WAOOAW account`; show available sign-up providers and a subordinate existing-account login path. |
| `REGISTRATION_REQUIRED` | Continue or resume registration without presenting a sign-in failure. |
| `ACCOUNT_SESSION_READY` | Return to the exact validated Trial/Hire disclosure and decision context. |
| `ASSURANCE_REQUIRED` | Explain that identity confirmation is required and preserve the acquisition context. |
| `ACTION_DENIED` | State that registration cannot continue under current policy; do not infer authentication failure. |
| `DEPENDENCY_UNAVAILABLE` | State that registration is temporarily unavailable and provide bounded retry. |
| Authentication expired or absent | Request secure sign-in while retaining the selected registration intent and safe return target. |

HTTP status alone must not select customer-facing journey language. `LOGIN` and `REGISTER` remain
distinct through provider redirect, callback, registration, recovery, and return.

### 3.3 Application Frame State

The Stable Application Frame consumes route context, authenticated identity state, navigation
state, and optional relationship Stop context. It exposes stable slots for navigation control,
WAOOAW identity, current context, contextual action, preferences, account control, main content,
conversation context, and active-relationship Emergency Stop.

Changing route content or contextual-action text must not move the WAOOAW identity or change the
main content origin. Expanding navigation opens rightward without reflowing the active page.

## 4. Ordered Implementation Slices

### CPUI-01 - Conversational Workspace

**Owner and skill:** Platform IT Expert (INST-010), Web and Business Platform contract implementation.

**Entry gate:** Enterprise Architect accepts this component boundary and confirms that existing
portal-interaction contracts either satisfy Section 3.1 or identifies the required OpenAPI delta.

**Output:** A visible, persistent workspace with context selection, durable conversation, typed
work objects, composer, server-issued actions, loading/error/offline states, and compact full-screen
adaptation. A closed utility drawer may supplement this workspace but cannot be its sole entry.

**First falsifying test:** From My Agents with no relationship selected, a browser test finds the
WAOOAW Guide workspace and composer without opening a floating drawer; selecting an authorized
Professional context changes the complete scoped projection without a document request.

**Bounded completion:** CPUI-A01 through CPUI-A05.

### CPUI-02 - Acquisition Identity Continuity

**Owner and skill:** Platform IT Expert (INST-010), identity-boundary web orchestration.

**Entry gate:** Typed identity outcomes required by Section 3.2 are available through the generated
Business Platform client; absence or ambiguity stops implementation and returns to INST-005.

**Output:** Intent-aware registration entry, recovery, and exact return to the selected Trial/Hire
decision. No registration state uses returning-user login-failure language unless authentication
itself is proven absent or expired.

**First falsifying test:** An anonymous customer selects Hire, completes the broker callback as a
new identity, receives `REGISTRATION_REQUIRED`, and sees `Create your WAOOAW account` with Hire
context retained and no `Sign in could not be completed` or `Sign in again` text.

**Bounded completion:** CPUI-A06 through CPUI-A10.

### CPUI-03 - Stable Application Frame

**Owner and skill:** Platform IT Expert (INST-010), responsive application-shell implementation.

**Entry gate:** Shared frame regions and typography tokens in the ratified visual-system contract
remain authoritative; any conflicting route requirement is escalated to Enterprise Architect.

**Output:** Stable navigation, brand, header, content frame, titles, loading boundaries, focus, and
responsive transitions across the customer portal.

**First falsifying test:** In one browser session, capture the shell geometry before and after each
left-navigation transition across Marketplace, My Agents, Alerts, Settings, Profile, and a
relationship route; the same shell node remains mounted and fixed-region coordinates do not move.

**Bounded completion:** CPUI-A11 through CPUI-A16.

### CPUI-04 - Outcome Qualification

**Owner and skill:** Platform IT Expert (INST-010), browser acceptance and evidence packaging.

**Entry gate:** CPUI-01 through CPUI-03 each hold focused executable evidence at the same candidate
commit.

**Output:** Final-HEAD component, contract, browser, accessibility, visual, and deployed Demo
evidence mapped one-to-one to every acceptance ID.

**First falsifying test:** Run the complete customer journey from Marketplace Trial and Hire through
new-customer registration and back to the selected decision, then traverse the shell and use both
Guide and Professional contexts in the supported viewport matrix.

**Bounded completion:** CPUI-A17 through CPUI-A20 and every prior acceptance ID remains passing.

## 5. Acceptance Contract

| ID | Pass condition |
|---|---|
| CPUI-A01 | The first customer-portal viewport exposes the active conversational workspace or an unambiguous workspace entry; a hidden floating drawer alone fails. |
| CPUI-A02 | The workspace identifies `WAOOAW Guide` or the selected Professional and provides an accessible context selector when alternatives exist. |
| CPUI-A03 | Text plus Action, Plan, Deliverable, and Decision blocks render from versioned server projections; unsupported blocks fail visibly. |
| CPUI-A04 | Every displayed action comes from a current server-issued capability; consequential actions expose effect and explicit confirmation before submission. |
| CPUI-A05 | Switching context preserves relationship isolation, authoritative cursor, draft ownership, focus, and Stop behavior without a full-document request. |
| CPUI-A06 | Trial and Hire preserve professional type, version, intent, disclosure revision, terms version, and safe return target through registration. |
| CPUI-A07 | A new customer sees account-creation language throughout the `REGISTER` journey and never sees generic failed-login language for `REGISTRATION_REQUIRED`. |
| CPUI-A08 | Returning account, assurance-required, policy-denied, expired-authentication, and dependency-unavailable outcomes have distinct truthful copy and recovery actions. |
| CPUI-A09 | Registration completion returns to the exact validated disclosure decision and does not silently start a trial, relationship, contract, or payment. |
| CPUI-A10 | Direct entry, modal entry, callback, refresh, back/forward, timeout, and retry preserve intent without exposing tokens or accepting unsafe return targets. |
| CPUI-A11 | One application-shell DOM identity remains mounted through internal navigation; route changes create no new document request. |
| CPUI-A12 | Brand and navigation-control bounding boxes move no more than 1 CSS pixel across route transitions at a fixed viewport and direction. |
| CPUI-A13 | Navigation expansion opens rightward without changing the main-content origin or obscuring keyboard focus, content, or active Stop. |
| CPUI-A14 | Customer pages use the ratified H1, spacing, content-width, and heading hierarchy; route-specific content cannot redefine global chrome geometry. |
| CPUI-A15 | Loading, empty, error, populated, and long-content states reserve stable frame dimensions and produce cumulative layout shift no greater than 0.10. |
| CPUI-A16 | No overflow, clipping, overlap, or incoherent movement occurs at 360x800, 768x1024, 1440x900, 200-percent zoom, English, or Urdu RTL. |
| CPUI-A17 | Component tests cover every typed identity outcome, workspace block type, unsupported block, capability state, and shell-state transition. |
| CPUI-A18 | Playwright proves both Trial and Hire for anonymous new customers and returning customers, plus cross-route workspace and shell continuity. |
| CPUI-A19 | Reviewer-visible screenshots and geometry/CLS artifacts cover every required viewport and the registration error/recovery states; broad suite totals are not acceptance evidence. |
| CPUI-A20 | Demo acceptance repeats the Founder-reported journeys against the exact deployed revision before the component may be called complete. |

## 6. Explicit Exclusions

- No model-provider selection, prompt design, or Professional Runtime implementation.
- No new relationship, trial, contract, billing, payment, or discount semantics.
- No browser-derived eligibility, authority, context, action, or identity outcome.
- No replacement frontend or client-only authorization model.
- No claim of Production readiness from local fixtures, screenshots, or aggregate test counts.

## 7. Dependency, Cost, Estimate, And Rollback

**Dependencies:** Existing Business Platform portal-interaction, identity, relationship, disclosure,
and Emergency Stop contracts; generated TypeScript clients; Next.js App Router; approved WAOOAW
visual tokens. A missing typed identity outcome or structured portal block is a contract gap, not a
license to hard-code browser behavior.

**Dependency/model decision:** No new frontend framework, model provider, or direct model call is
authorized. Existing dependencies are sufficient. Any proposed package requires normal authority,
license, payload, and security review.

**Estimate:** Four independently reviewable implementation slices. Estimation in elapsed time is
deferred to INST-010 after dependency closure.

**Rollback:** Each slice is separately revertible. Rollback restores the previous presentation but
must preserve identity registrations, drafts allowed by policy, conversations, relationship state,
idempotency records, and constitutional evidence.

## 8. Stop Conditions

Implementation stops and returns to Solution Architect when:

- portal interaction lacks a typed block or capability required by CPUI-A03/A04;
- identity outcomes cannot distinguish registration from authentication and policy failures;
- stable shell behavior would require changing the ratified route or container architecture;
- a browser must infer authority, eligibility, relationship, or account state;
- acceptance requires production fallback data or an undocumented endpoint; or
- any required outcome can be marked complete without its named browser evidence.

## 9. Why Prior Delivery Missed These Outcomes

| Failure mechanism | What happened | Control introduced here |
|---|---|---|
| Broad scope was treated as evidence | WC-096 listed the complete experience, but aggregate suite counts were accepted without proving each visible outcome. | CPUI-A01 through CPUI-A20 require one-to-one evidence. |
| Proxy behavior replaced the requested experience | Drawer open/close and text navigation were treated as proof of a persistent conversational workspace. | CPUI-A01 explicitly fails drawer-only delivery; CPUI-A02-A05 test context and governed work. |
| Tests encoded incorrect language | The 403 registration test expected `Sign in could not be completed`, preserving the defect. | CPUI-A07/A08 require typed outcome-specific language and negative assertions. |
| SPA continuity was reduced to no reload | Tests checked one shell node and document count, but not logo/content geometry, title hierarchy, or layout shift. | CPUI-A11-A16 require bounding-box, CLS, typography, viewport, zoom, and RTL proof. |
| A narrower follow-up was called complete | PR #443 addressed Marketplace acquisition presentation while unresolved WC-096 outcomes were outside its executable matrix. | CPUI-A20 prohibits completion until the original reported journeys pass on the deployed revision. |
| Visual inspection was too narrow | Marketplace screenshots did not exercise cross-route transitions or the failed registration journey. | CPUI-A18-A20 require end-to-end route sequences and reviewer-visible failure-state evidence. |

## 10. Completion Rule

This Work Component is not complete when code exists, a drawer opens, unit tests pass, the shell
avoids a document reload, or a local screenshot looks correct. It is complete only when all
CPUI-A01 through CPUI-A20 pass against one final commit, the exact revision is deployed to Demo,
the Founder-reported Trial/Hire and navigation journeys pass there, and the Founder accepts the
customer outcomes. Engineering evidence remains evidence, not approval.