# WC-105 Authentication Flow Defect Remediation Plan

**Artifact type:** Solution Architecture component contract and implementation Work Component plan
**Owning office:** Chief Solution Architect (INST-005)
**Implementation office:** Platform IT Expert (INST-010), Skills 4, 5, 6, 12, 14 and 16
**Parent delivery:** WC-105 Authentication, Guide, Session, And Landing Defect Repair
**Trigger:** Founder-reported defects after PR #474 Demo deployment
**Analysed source:** `origin/main` at `4a02ff1279b4e846b69278c07efa9d057f621a46`
**Status:** FOUNDER ACCEPTED - IMPLEMENTATION AUTHORIZED FOR 2026-09-27 SESSION
**New deployable component:** NO - existing Web Application and identity boundary only
**Application implementation authority:** GRANTED BY FOUNDER IN 2026-09-27 SESSION
**Environment authority:** NONE
**Constitutional basis:** C-023, C-026, C-032, C-042, C-049, C-059, C-063, C-065, C-071, C-080; ADR-017

## 1. Objective

Repair the Login and Registration experience observed after PR #474 without weakening Keycloak,
identity-session, registration ownership, safe-return, privacy, accessibility, or fail-closed
boundaries. The implementation must provide stable modal composition, truthful provider readiness,
recoverable session transitions, consistent WAOOAW branding, and deterministic completion evidence.

This plan contains the complete behavioral contract required by Platform IT Expert. It does not
authorize application changes, provider changes, cloud deployment, or acceptance.

## 2. Decision And Supersession Boundary

Upon Founder acceptance, this plan supersedes only these earlier presentation clauses:

| Existing requirement | Superseding decision |
|---|---|
| `hybrid-application-shell.md` Web and Mobile Authentication Layout: dedicated authentication pages | Login and Registration remain dedicated authentication experiences but are always presented in an accessible modal over the public shell. |
| WC-093 Section 24.3: direct-route fallback remains unchanged | Direct `/login`, `/register`, and their loading/error/continuation states render the same modal composition as intercepted navigation. |
| WC-083 browser assertion: direct auth routes contain zero dialogs | Replace with assertions that direct auth routes contain exactly one correctly named modal. |
| WC-083 loading assertion: loading content is replaced by the provider grid | Provider controls remain mounted and visible while readiness resolves; each control is disabled until its own authoritative availability is known. |

All identity, authorization, privacy, safe-return, provider-order, localization, accessibility, and
account-creation boundaries not expressly changed above remain controlling.

## 3. Component Boundary

The work modifies internal modules of the existing ADR-017 Web Application and, only where required
to preserve typed recovery evidence, the existing Business Platform identity boundary. It creates no
new deployable service, route, provider, authentication method, persistence store, or dependency.

| Owner | Responsibility |
|---|---|
| Public/auth route composition | Render the public shell and exactly one `AuthDialog` for direct and intercepted Login/Registration routes. |
| Auth dialog | Own close, Escape, backdrop, focus restoration, sizing, and stable content geometry. |
| Provider readiness | Project four controls immediately; enable only providers reported `AVAILABLE` and supported by the approved broker. |
| Registration state machine | Preserve non-secret draft data, reject stale authority, recover safely from abandoned or changed sessions, and complete only after durable confirmation. |
| Identity boundary | Return existing typed problem codes and correlation IDs; never expose tokens, claims, account IDs, registration IDs, or customer data in browser messages or logs. |
| Observability | Record privacy-safe route, operation, status class, typed problem code, correlation ID, service revision, and recovery outcome. |

## 4. Evidence Baseline

### 4.1 Source And Test Evidence

| Evidence | Finding |
|---|---|
| `web/app/icon.tsx` | Generates a white letter `W` on navy; it does not render the WAOOAW mark. |
| `web/components/auth/AuthBoundary.tsx` | Loading renders brand, progress bar, and text but no provider controls. |
| `web/components/auth/LoginView.tsx` | Renders brand and providers but no `Don't have an account? Register` line. |
| `web/app/(auth)/layout.tsx` | Direct auth routes render inside `AppShell` without `AuthDialog`. |
| `web/app/@authModal/(.)register/layout.tsx` | Only intercepted registration navigation is wrapped in `AuthDialog`. |
| `web/app/globals.css` | Entry dialog is fixed at 360px desktop height and 500px compact height with `overflow: auto`, allowing the observed internal scrollbar. |
| `web/components/auth/RegisterView.tsx` | Authenticated registration renders `RegistrationFlow` without `AuthBrand`. |
| `web/components/auth/RegistrationProgress.tsx` | Renders six letter circles without directional connectors. |
| `web/lib/identity-messages.ts` | Includes the unwanted provider-and-budget sentence and the label `Complete registration`. |
| `web/components/auth/RegistrationFlow.tsx` | Final action has disabled Mobile verification and Complete registration only; no Cancel action. Registration start/complete denials replace the form with a generic full error view. |
| `web/tests/e2e/wc083-auth-dialog.spec.ts` | Tests intentionally require replacement loading geometry and direct routes with no dialog. |
| `web/components/auth/RegistrationFlow.test.tsx` | Tests intentionally require the long SMS limitation copy and `Complete registration`. |

### 4.2 Demo Evidence

Read-only Dockerized Azure CLI inspection on 2026-09-27 identified:

- Web revision `ca-demo-web--0000055`, created `2026-09-27T09:24:33Z`, image
  `ghcr.io/dlai-sd/web@sha256:77ae8013e2b69ca15cee8135b72de4e6144a9a9fc59079f5b52cc91da993c312`.
- Business Platform revision `ca-demo-business-platform--0000050`.
- Between `09:20Z` and `10:15Z`: 39 provider reads returned `200`; 31 identity-session reads
  returned `403`; one registration start returned `403`; two registration completion requests
  returned `403`.
- The same window contains a successful independent path: registration start `201`, profile update
  `200`, completion `200`, then identity session `200`.
- Current revisions show only deployment-start probe failures around `09:24Z`; no later restart or
  crash evidence explains the customer-visible failures.
- The workspace ingested only `ContainerAppConsoleLogs_CL` and `ContainerAppSystemLogs_CL`; no
  distributed request/dependency/span table was available. Web emitted no typed registration failure
  record for the observed `403` responses.

The evidence confirms a real session/registration authorization failure. It does not identify the
exact typed problem code because the retained logs omit it. Source shows that registration start
requires a fresh validated broker actor and completion revalidates access to the actor-bound
registration. The likely stale/changed-session cause must therefore remain a hypothesis until a
reproduction captures the status, problem code, correlation ID, and transition state together.

## 5. Defect And Impact Analysis

| ID | Flow | Confirmed defect | Customer and platform impact | Evidence |
|---|---|---|---|---|
| AUTH-UI-01 | Shared | Browser tab icon is not the WAOOAW mark. | Weak brand recognition; installed PWA and browser tab present an inconsistent identity. | Generated icon is a single `W`; manifest points both icon purposes to `/icon`. |
| AUTH-UI-02 | Login | Loading replaces provider controls instead of showing stable disabled controls. | Layout transition reduces trust and causes avoidable visual movement at the first conversion step. | `AuthBoundary` and passing WC-083 geometry test encode replacement behavior. |
| AUTH-UI-03 | Login | Standard registration switch is absent. | A customer who does not yet have an account lacks the expected direct next action. | `LoginView` has no Register link. |
| AUTH-STATE-01 | Login to Registration | Abandoning Login and selecting Register can produce a generic fatal screen from stale or changed session/registration authority. | Blocks acquisition, obscures the recoverable next step, and makes a valid security denial appear as platform failure. | Demo registration start `403`, completion `403` twice, repeated session `403`; UI maps denials to full generic error. |
| AUTH-UI-04 | Registration | Entry modal uses a fixed short height and internal vertical scrolling. | Legal/action content is hidden below the fold and the modal appears unfinished. | Desktop entry height is 360px with `overflow: auto`; supplied screenshot shows scrollbar. |
| AUTH-UI-05 | Login and Registration | Direct routes and post-provider registration continuation can render full-page auth screens. | Experience changes after OAuth return and breaks the modal-only requirement. | `(auth)` layout omits `AuthDialog`; existing E2E test requires zero dialogs on direct routes. |
| AUTH-COPY-01 | Registration | Optional-mobile copy includes an internal provider/budget explanation. | Exposes implementation planning language and distracts from the optional choice. | `smsBudget` is rendered and asserted by tests. |
| AUTH-UI-06 | Registration | Registration continuation omits auth branding and uses larger full-page title styling. | Brand and hierarchy visibly jump between provider entry and profile completion. | `RegisterView` bypasses `AuthBrand` after authentication; full-page and modal title sizes differ. |
| AUTH-UI-07 | Registration | Progress uses large isolated WAOOAW circles without directional arrows. | Sequence and direction are harder to understand; controls consume excess vertical space. | Six grid circles are rendered with no connector or arrow element. |
| AUTH-UI-08 | Registration | Final action row lacks Cancel and says `Complete registration`. | Customer cannot abandon clearly from the final step; command language is longer and inconsistent with entry terminology. | Final command row contains disabled Mobile verification and `Complete registration` only. |

## 6. Proposed Component Fixes And Definition Of Done

### AUTH-UI-01 - WAOOAW Browser And PWA Icon

**Fix:** Replace the generated single-letter icon with a square, transparent-safe rendition of the
repository-owned WAOOAW mark. Use one canonical asset source for App Router metadata and manifest
icons, with browser-compatible sizes and a maskable variant whose safe zone does not crop the mark.

**Definition of Done:**

1. Browser tabs show the recognizable WAOOAW mark at 16px and 32px in Chromium, Firefox, and WebKit.
2. Manifest icons resolve successfully at every declared size and include `any` and `maskable` purpose.
3. Light and dark browser chrome do not make any logo segment disappear.
4. Automated metadata/HTTP checks reject a missing icon, the old single `W`, wrong MIME type, or a
   manifest URL that does not resolve.

### AUTH-UI-02 - Stable Login Provider Loading

**Fix:** Compose one Login view for loading and ready states. Render Google, Facebook, Apple, and
Email controls immediately in the approved two-by-two order. While provider projection is pending,
all four controls remain visible and disabled and the progress indicator is announced. On completion,
enable only providers that are both `AVAILABLE` and supported; unavailable providers remain disabled
with truthful accessible labels.

**Definition of Done:**

1. The same four provider DOM controls exist before, during, and after provider discovery.
2. All controls are disabled while readiness is unresolved; no click can launch a broker.
3. Google/Facebook become enabled only when authoritative readiness says `AVAILABLE`; Apple/Email
   remain disabled under current rules.
4. Dialog x/y/width/height, logo, title, provider positions, and legal/switch text do not move by more
   than 1 CSS pixel between loading and resolved states at 1365x617 and 360x800.
5. Failure keeps the four controls visible and disabled, presents an inline retry, and never replaces
   the dialog with a generic error page.

### AUTH-UI-03 - Login Registration Switch

**Fix:** Add the standard line `Don't have an account? Register` beneath Login providers. `Register`
is a route-backed link carrying the same validated `returnTo`; it changes the modal content without
returning to or reloading the marketing page.

**Definition of Done:**

1. The exact English line is visible in Login loading, ready, and recoverable-failure states.
2. The Register link preserves only a server-approved safe return target.
3. Keyboard activation moves to the Registration modal and places focus on its heading.
4. No token, provider state, one-time code, or unsafe return URL is copied into the link.

### AUTH-STATE-01 - Abandoned Login And Registration Recovery

**Fix:** Introduce an explicit browser presentation state machine around existing server authority:
`LOGIN_LOADING -> LOGIN_READY -> BROKER_REDIRECT -> REGISTRATION_RESOLVING -> REGISTRATION_ACTIVE ->
COMPLETED`. Cancel or path-switch events abort in-flight requests, clear transient provider launch and
registration identifiers, retain only approved non-secret profile draft fields, and start the newly
selected path with a fresh operation-scoped idempotency key.

Do not bypass freshness or actor binding. A stale, changed, expired, or inaccessible session must map
to a typed inline recovery inside the modal:

- `IDENTITY_STEP_UP_REQUIRED`: offer `Continue securely` and relaunch the selected approved broker.
- `IDENTITY_SESSION_REQUIRED`, `401`, or expired bearer: return to provider choice in the same modal.
- `IDENTITY_RESOURCE_NOT_ACCESSIBLE` for a stale registration: discard only the inaccessible
  registration reference, preserve permitted draft fields, and start a new registration after the
  current actor is validated.
- `IDENTITY_ACTION_DENIED`: show a customer-safe inline denial and `Sign in again`; never retry
  automatically or weaken policy.
- dependency timeout/unavailability: preserve the modal and draft, disable commands, and offer a
  bounded retry with the same idempotency key for the uncertain operation.

**Definition of Done:**

1. Abandon Login at every pre-redirect, redirect-return, and resolving state, then select Register;
   Registration opens in the same modal without the generic fatal screen.
2. Switching Login to Register and Register to Login aborts obsolete requests; late responses cannot
   overwrite the active view.
3. A changed provider actor cannot resume or complete another actor's registration.
4. Recoverable `401/403/404/409/503` cases retain only approved non-secret draft values and provide one
   explicit next action inside the modal.
5. Idempotent retry cannot create duplicate registrations, accounts, memberships, or security events.
6. Demo evidence captures the exact typed problem code and recovery outcome without tokens, email,
   subject, account, registration, or tenant identifiers.
7. The successful recovery sequence ends with registration completion `200` and identity-session
   `200`; no unexplained registration start/completion `403` remains.

### AUTH-UI-04 - Registration Modal Height

**Fix:** Replace the fixed 360px entry height with content-driven sizing bounded by the viewport.
Desktop and ordinary mobile states must fit their complete default content without an internal
vertical scrollbar. Maintain one stable width and minimum height across adjacent states where doing
so does not clip content. Use a shared maximum width of 560px, 16px minimum viewport clearance,
`height: auto`, and `max-height: calc(100dvh - 2rem)`; content spacing may compact responsively but
interactive targets remain at least 44px.

**Definition of Done:**

1. Provider entry, resolving, profile, optional-mobile, review, and recoverable-error states have
   `scrollHeight <= clientHeight + 1` at 1365x617, 1440x900, 390x844, and 360x800 at 100% text size.
2. Modal edges retain at least 16px viewport clearance and no page-level horizontal overflow occurs.
3. At 200% text zoom or unusually short viewports, one controlled modal scrollbar is permitted so all
   content remains reachable; nested scroll containers are prohibited.
4. State changes do not clip the close control, primary action, Cancel, legal links, or focus outline.

### AUTH-UI-05 - Modal-Only Authentication Presentation

**Fix:** Make direct and intercepted Login/Registration routes converge on one modal shell over the
public background. OAuth callback, loading, registration continuation, recoverable error, and direct
URL refresh must preserve that composition. Route ownership and server authorization remain unchanged;
the modal is presentation, not browser-owned auth authority.

**Definition of Done:**

1. `/login`, `/register`, safe-return variants, intercepted links, browser refresh, OAuth callback,
   and recoverable errors each render exactly one accessible dialog.
2. No Login or Registration state renders as an unframed full-page auth column.
3. Close, Escape, and backdrop return to the validated public origin; browser Back does not reopen a
   stale modal or lose the safe return target.
4. Focus enters the heading or first actionable control, remains trapped while open, and returns to
   the originating trigger or public main landmark on close.
5. Public content behind the modal is inert to pointer and keyboard input and is not duplicated in the
   accessibility tree.

### AUTH-COPY-01 - Optional Mobile Copy

**Fix:** Display only `Mobile verification (optional)` and `SMS verification is not available yet.`
Remove the provider-and-budget sentence from every visible locale and accessibility label.

**Definition of Done:**

1. English displays exactly the two approved strings and no provider/budget explanation.
2. Every supported locale has complete reviewed equivalents or uses the approved fallback policy.
3. Mobile verification remains visibly disabled and cannot issue a network request.
4. Tests reject the removed sentence in visible text, accessible text, and rendered HTML.

### AUTH-UI-06 - Registration Branding And Title

**Fix:** Use the same `AuthBrand` logo container, image asset, alignment, and title token for Login,
Registration provider entry, Registration resolving, profile, optional-mobile, review, and error
states. The Registration title is `Create your WAOOAW account`. Both titles use the existing modal
brand token of 1.45rem with 1.2 line height, and both use the existing 104px by 38px visible logo box.

**Definition of Done:**

1. Every Login and Registration modal state shows the WAOOAW logo at the same x/y position and
   computed width/height within 1 CSS pixel.
2. Login and Registration titles have the same computed font size, line height, weight, and maximum
   text width in the same locale and viewport.
3. Long translated titles wrap without clipping, overlap, horizontal scroll, or moving the close icon.
4. No state displays both the shell logo and a second competing auth logo inside the modal.

### AUTH-UI-07 - Directional Registration Progress

**Fix:** Keep the six-letter WAOOAW sequence but use smaller fixed-size circles connected by
directional arrow icons. Arrows point inline-forward, reverse under RTL, and are decorative; the
accessible output continues to announce the current named step. Complete, active, upcoming, pending,
and reduced-motion states remain distinct without relying on color alone. Circles are 38px with
0.75rem letters above 480px and 32px with 0.7rem letters at 480px and below. Five existing Lucide
`ArrowRight` icons render at 14px between circles and reverse visually in RTL.

**Definition of Done:**

1. Six circles and five connectors fit without wrapping or horizontal overflow at 360px.
2. Each circle has a stable explicit size smaller than the PR #474 baseline; letter text fits every
   supported script and 200% zoom behavior remains usable.
3. Arrows point right in LTR and left in RTL and do not add duplicate screen-reader announcements.
4. Pending animation is disabled under reduced motion; active state remains perceivable without it.
5. Step changes do not alter modal width or hide the current textual step label.

### AUTH-UI-08 - Registration Cancellation And Final Command

**Fix:** Preserve the upper-right close icon and add a visible `Cancel` command in the final action
row beside disabled `Mobile verification (optional)` and primary `Register`. Close and Cancel share
one cancellation contract: abort active work, clear transient registration state, preserve no secret,
and return to the validated origin. Rename `Complete registration` to `Register` in every applicable
state and locale.

**Definition of Done:**

1. Every Registration modal has one upper-right close icon with accessible name `Close`.
2. The final row contains, in logical reading order, disabled Mobile verification, Cancel, and primary
   Register; all controls remain reachable at 360px and 200% zoom.
3. Cancel and close produce the same state cleanup and safe navigation outcome.
4. Register is disabled while completion is pending and cannot submit twice.
5. `Complete registration` is absent from visible and accessible English UI; localized labels follow
   the approved vocabulary update.

## 7. Implementation Work Components

| Work Component | Scope | Immediate focused proof |
|---|---|---|
| WC-AUTH-01 Brand icon | App Router icon and manifest metadata; no unrelated SEO changes | Metadata/component test plus HTTP content-type and non-old-icon assertion |
| WC-AUTH-02 Stable entry composition | Shared loading/ready provider model and Login switch | AuthBoundary, LoginView, ProviderCommands component tests |
| WC-AUTH-03 Modal route convergence | Direct/intercepted route layouts, dismissal, focus, safe return | Focused Playwright direct/intercepted/refresh/callback matrix |
| WC-AUTH-04 Registration visual refinement | Modal sizing, shared brand, title, progress connectors, action row, copy | Component tests and 360/390/1365/1440 geometry assertions |
| WC-AUTH-05 Session recovery | Transition state, abort/late-response protection, typed recovery, idempotency | Unit tests for every typed outcome plus real PostgreSQL identity tests |
| WC-AUTH-06 Integrated qualification | Full journey, accessibility, localization, privacy, telemetry, images | Final Docker-only Jest, lint, type/build, Playwright, axe, scanner and Demo evidence campaign |

Each first substantive implementation edit must be followed immediately by the listed focused Docker
check. Platform IT Expert must not defer all validation to WC-AUTH-06.

### 7.1 Expected Implementation Surface

| Work Component | Expected source | Expected tests |
|---|---|---|
| WC-AUTH-01 | `web/app/icon.tsx`, `web/app/manifest.ts`, existing repository-owned logo assets | App metadata tests and focused browser asset checks |
| WC-AUTH-02 | `web/components/auth/AuthBoundary.tsx`, `LoginView.tsx`, `ProviderCommands.tsx` | Corresponding component tests and WC-083 loading journey |
| WC-AUTH-03 | `web/app/(auth)/layout.tsx`, auth modal layouts, `AuthDialog.tsx`, `AuthJourney.tsx` | Auth dialog unit tests and direct/intercepted Playwright matrix |
| WC-AUTH-04 | `AuthBrand.tsx`, `RegisterView.tsx`, `RegistrationFlow.tsx`, `RegistrationProgress.tsx`, `identity-messages.ts`, `globals.css` | Registration component, progress, localization, geometry, screenshot and axe tests |
| WC-AUTH-05 | Registration flow and proxy route; existing Business Platform identity service/controller only if typed evidence proves the defect is server-owned | Transition race tests, proxy problem-code tests, PostgreSQL actor/idempotency tests and focused browser recovery journeys |
| WC-AUTH-06 | Existing Docker test/preview configuration only when required to execute the accepted gates | Final exact-image qualification and bounded Demo evidence |

Files outside this map require a recorded dependency reason before modification. A backend change is
not authorized merely because Demo returned `403`; first reproduce and retain the typed problem code.

## 8. Test And Evidence Contract

### 8.1 Required Automated Coverage

1. Component tests cover every state and transition named in Sections 6 and 10.
2. Playwright covers Chromium, Firefox, and WebKit at 1365x617 and 360x800, plus Chromium at 1440x900
   and 390x844.
3. Every visual state is checked in light/dark, English, one long-label locale, Urdu RTL, keyboard-only,
   reduced-motion, and 200% text zoom modes as applicable.
4. Geometry assertions cover modal viewport clearance, no baseline internal scroll, no horizontal
   overflow, stable provider positions, logo/title alignment, action visibility, and close visibility.
5. Accessibility assertions cover dialog name, focus trap/return, inert background, status/alert live
   regions, disabled-control names, contrast, and connector silence.
6. Identity integration tests use real PostgreSQL and prove actor isolation, stale registration
   rejection, safe recovery, idempotency, no duplicate account/membership, and no cross-tenant access.
7. Existing tests that assert standalone auth pages, replacement loading UI, long SMS copy, or
   `Complete registration` must be replaced and trace to the superseding defect ID. They must not be
   deleted without equivalent positive and negative coverage.

### 8.2 Demo Evidence

After separate Founder authorization for deployment, retain one bounded evidence package containing:

- exact 40-character source commit, Web and Business Platform image digests, revision names, and
  deployment time;
- browser screenshots for each default Login/Registration state at desktop and mobile;
- status counts for provider, registration, completion, and identity-session endpoints;
- privacy-safe typed failure and recovery records with correlation continuity;
- zero unexplained registration `403`, `5xx`, timeout, crash, or post-start probe failure during the
  observation window;
- explicit statement whether distributed traces were available; console logs must not be called
  traces;
- Founder visual acceptance remains separate from author review and automated qualification.

## 9. Stops And Non-Goals

Stop and return to Solution Architect or Founder if implementation requires a new provider, endpoint,
schema, persistence mechanism, auth dependency, token exposure, weaker freshness/actor validation,
unsafe return target, hidden policy denial, or exception to accessibility at 200% zoom.

The work must not:

- enable Apple, Email, or SMS before their existing authority and readiness gates pass;
- treat disabled presentation as provider authorization;
- clear or bypass server identity merely to avoid a `403`;
- reuse a registration across different validated actors;
- log tokens, email addresses, subjects, account IDs, registration IDs, tenant IDs, or SQL values;
- change Marketplace, relationship, billing, agent, or cloud-delivery behavior;
- modify Production, DNS, provider configuration, or live infrastructure;
- add a new UI framework, state library, icon library, or telemetry dependency.

## 10. Plain-English Login And Registration Flows

This section is normative input for test-case derivation.

### 10.1 Login Flow

1. The customer selects Login or opens `/login` directly.
2. The public page remains visible behind one modal. Focus moves into the modal, which immediately
   shows the WAOOAW logo, `Log in to WAOOAW`, four provider buttons, and
   `Don't have an account? Register`.
3. While WAOOAW checks provider readiness, all four provider buttons remain visible but disabled. A
   progress status is announced without replacing or moving the buttons.
4. When readiness completes, Google and Facebook become enabled only if the server says they are
   available. Apple and Email remain visible and disabled under the present rules.
5. The customer may close or cancel Login at any time. WAOOAW aborts unfinished browser requests,
   clears temporary launch state, returns to the validated public page, and does not create an account.
6. If the customer selects Register, the same modal changes to Registration. The page does not reload,
   no full-page auth screen appears, and no stale Login response can overwrite Registration.
7. If the customer selects an enabled provider, WAOOAW uses Keycloak. After the provider returns, the
   same modal either continues Registration for a new customer or continues to the validated target
   for an existing customer.
8. If the session expired or must be refreshed, the modal explains the next safe action inline and
   offers `Sign in again` or `Continue securely`. It does not display a generic full-page error.

### 10.2 Registration Flow

1. The customer selects Register, follows the Login registration link, returns from a provider, or
   opens `/register` directly. Every path opens exactly one Registration modal over the public page.
2. The modal always shows the same WAOOAW logo position and title style as Login, an upper-right close
   icon, and the compact WAOOAW progress sequence with arrows showing forward direction.
3. Before provider readiness is known, all provider choices remain visible and disabled. Available
   approved providers become enabled when the check completes.
4. After successful provider authentication, WAOOAW validates the current actor and registration.
   It then displays the verified email and asks for name, business name, and type of business.
5. The customer saves the profile. WAOOAW preserves these non-secret values during a safe retry but
   never stores tokens or one-time codes in browser draft storage.
6. The final step shows `Mobile verification (optional)` and
   `SMS verification is not available yet.` Mobile verification remains disabled.
7. The same final row shows Cancel and Register. Register is the primary action and is disabled while
   a completion request is active so one customer action cannot create duplicate records.
8. Close or Cancel aborts unfinished requests, clears transient registration identifiers, and returns
   safely without completing an account. Approved non-secret draft retention follows the current
   session-expiry policy.
9. If Login was abandoned, the actor changed, or a stale registration cannot be accessed, WAOOAW does
   not continue under the wrong identity. It keeps the customer in the modal, explains the safe next
   step inline, preserves permitted draft values, and restarts secure authentication or registration.
10. Registration succeeds only after the server durably confirms completion. WAOOAW then opens the
    validated return target. A transport response alone is not presented as successful registration.
11. At normal desktop and mobile text size, every step fits without an internal scrollbar. At 200%
    text zoom or an unusually short viewport, one modal scrollbar may appear so no content or action
    becomes unreachable.

## 11. Platform IT Expert Handoff

Platform IT Expert may execute WC-AUTH-01 through WC-AUTH-06 only after:

1. Founder acceptance of this plan and its Section 2 supersessions is recorded in this session.
2. Founder implementation authorization for the current session is recorded in this session.
3. The implementation branch is not `main` and unrelated working-tree changes remain untouched.
4. Skill 16 entry gates and Docker-only test execution requirements are satisfied.
5. Any Demo deployment and Azure evidence collection receives separate current authority.

Implementation returns to the Founder as one reviewable PR with exact requirement-to-source-to-test
traceability for AUTH-UI-01 through AUTH-UI-08, AUTH-COPY-01, and AUTH-STATE-01. Platform IT Expert
performs author review but does not self-approve or merge.

## 12. Solution Architect Author Review

**Review status:** PASS - 2026-09-27

The owning Solution Architect re-read the complete plan against the Founder defect report, PR #474
source evidence, Demo telemetry, existing UX contracts, ADR-017, identity boundaries, and the
Solution Architect Professional Standard.

| Lens | Finding | Resolution |
|---|---|---|
| Requirements coverage | All ten concrete defects require individual acceptance criteria and plain-English flow coverage. | AUTH-UI-01 through AUTH-UI-08, AUTH-COPY-01, and AUTH-STATE-01 each have a bounded fix and Definition of Done; Section 10 covers both flows. |
| Architecture consistency | Modal-only behavior conflicts with older dedicated-page and direct-fallback clauses. | Section 2 names the exact supersessions and makes them conditional on Founder acceptance. |
| Implementation determinism | Initial draft left progress dimensions and likely source ownership open to implementation choice. | Exact circle, text, arrow, title, logo, modal-width, viewport and target-size constraints plus Section 7.1 were added. |
| Security and privacy | Avoiding the error screen could tempt implementation to bypass a valid actor/freshness denial. | AUTH-STATE-01 preserves fail-closed checks and requires typed inline recovery, actor isolation, idempotency and privacy-safe evidence. |
| Accessibility | An absolute no-scroll rule would make content unreachable at 200% zoom or short viewports. | Baseline states prohibit internal scroll; one controlled modal scrollbar is explicitly allowed only when accessibility requires it. |
| Evidence quality | Azure logs prove status failures but not the exact problem code or source-commit binding. | Section 4 states those limits and Section 8 requires typed correlation evidence and exact revision/digest/commit binding after deployment. |
| Scope and reversibility | The task must not become an auth-platform redesign. | Existing routes, providers, APIs and components are retained; no new dependency or deployable component is allowed. |

**Unresolved author-review findings:** None.

**Handoff decision:** RETURNED TO PLATFORM IT EXPERT for the Founder-authorized 2026-09-27
implementation session. Author review verifies plan quality; it is not approval or merge authority.