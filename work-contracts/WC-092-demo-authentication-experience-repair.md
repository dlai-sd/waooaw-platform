# WC-092 - Demo Authentication Experience And Identity Handoff Repair

**Office:** Platform IT Expert (INST-010), Skills 2, 4, 5, 6, 7 and 16
**Assigned by:** Founder instruction, 2026-09-12
**Status:** IMPLEMENTATION AUTHORIZED FOR CURRENT SESSION; CLOUD MUTATION NOT AUTHORIZED
**Delivery unit:** One bounded Web and Business Platform repair PR
**Controlling contracts:** `work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md` §§6-7,
`work-contracts/WC-085-wc084-remediation-and-evidence-closure.md` §5,
`architecture/reference/ux/hybrid-ui-acceptance-contract.md`, and
`architecture/reference/product/wc085-identity-architecture-decision.md`
**Runtime baseline:** Demo deployment run `34624655625`; release manifest
`sha256:fddc9530c0b7c59eab07517abae95989a264825feff5966e5495ac2ed683d4b1`;
Web image `ghcr.io/dlai-sd/web@sha256:4bd827a7a0d1db5e0ff8bfeefecd585036092f5d63671faaff5d8b6397ea9566`;
Business Platform image `ghcr.io/dlai-sd/business-platform@sha256:be432a3274cf3d7152252e2b0c1f1c74a38f5d75e118f90bfa482f821f23bf96`
**Constitutional basis:** C-023, C-026, C-049, C-059, C-063, C-065, C-071, C-076, C-080, C-100

## Authority And Scope

The Founder authorized this session to create this Work Component, implement its code and tests,
collect local evidence, pass pre-PR checks, and submit an unmerged PR for Founder review. The
authorization covers only the observed Demo Login/Register defects and the minimum diagnostics needed
to identify an identity-policy denial without exposing tokens or personal data.

Authorized changes are:

1. keep landing-page Login/Register navigation, loading, switching, bounded error and retry states
   inside one dismissible modal while preserving direct `/login` and `/register` routes;
2. bound provider-readiness waiting so Demo scale-from-zero cannot replace or trap the public page;
3. preserve the initiating safe public destination through Login, Register and provider return;
4. replace customer-visible broker terminology with Founder-directed customer language;
5. present unavailable providers truthfully without making them appear actionable;
6. keep account resolution neutral after provider return and show registration content only when the
   server establishes that account completion is required;
7. emit privacy-safe Business Platform denial-rule diagnostics for the existing strict actor
   validation, without logging claim values, tokens, provider subjects, email, names or IP addresses;
8. add focused component, API, contract and browser regression coverage and retain proportional local
   Docker evidence for the PR.

This Work Component does not authorize Azure mutation, deployment, DNS/custom-domain changes, Google
or Meta console changes, provider secret access or rotation, customer traffic, Production action,
self-approval or merge. Google branding that currently displays `azurecontainerapps.io` is a verified
external configuration gap and remains a separately authorized follow-up.

## Observed Baseline And Root Cause Evidence

| ID | Observed behavior | Bound evidence | Engineering interpretation |
|---|---|---|---|
| WC092-O1 | Login click showed a generic full-page loader for more than ten seconds | Founder screenshots; Azure system logs 2026-09-12 04:40-04:42 UTC | Web and Business Platform scaled from zero; auth navigation exposed the global loader instead of a modal-owned boundary |
| WC092-O2 | `/login` rendered standalone with no close control after a landing-page click | Founder screenshot | Intercepted navigation did not preserve the public shell under the slow dependency path |
| WC092-O3 | Login/Register copy exposed “approved identity broker” terminology | Founder direction and screenshots | Customer copy must describe the outcome rather than internal identity architecture |
| WC092-O4 | Apple looked actionable while Email alone showed unavailable | Founder screenshot | Provider states need a distinct, truthful available/coming-soon presentation |
| WC092-O5 | Google displayed “continue to azurecontainerapps.io” | Founder screenshot | OAuth/custom-domain branding gap; not repairable inside this code-only Work Component |
| WC092-O6 | Google returned to a registration modal that immediately failed; retry repeated the failure | Founder screenshots | Provider authentication succeeded, but account resolution/registration was denied |
| WC092-O7 | Google broker redirect returned 303 and Keycloak token exchange returned 200 | Sanitized Demo Log Analytics records at 04:41:49 and 04:41:56 UTC | Google and Keycloak callback path succeeded |
| WC092-O8 | BP identity session and registration start both returned 403 repeatedly | Sanitized Demo Log Analytics records at 04:41:58-04:42:21 UTC | Strict actor validation denied the token before account lookup/creation; current logs omit the failed rule |

## Required Inputs

| Input | Required state | Session result |
|---|---|---|
| WC-084 authentication repair contract | Accepted implementation boundary | PRESENT |
| WC-085 authentication/browser and identity architecture | Owner-reviewed implementation contract | PRESENT |
| Founder visual observations | Login, provider return and Register screenshots supplied in this conversation | PRESENT |
| Live diagnostic authority | Read-only Demo log inspection explicitly requested by Founder | COMPLETE; no mutation performed |
| Implementation authority | Explicit Founder authorization for code, local tests, evidence and PR in this session | PRESENT |
| Provider/DNS/cloud mutation authority | Separately required | ABSENT; excluded from scope |

## Acceptance Matrix

| ID | Required behavior | Executable proof |
|---|---|---|
| WC092-A01 | A public Login/Register click immediately retains the public page and opens a stable modal shell | Delayed-provider Playwright test asserts public hero, dialog and URL state before provider response |
| WC092-A02 | Loading remains in the modal and Close, Escape and backdrop each return directly to the captured public origin | Playwright interaction matrix under delayed and failed provider responses |
| WC092-A03 | Direct `/login` and `/register` loads remain refresh-safe standalone routes | Direct-route Playwright assertions |
| WC092-A04 | Provider projection has a finite deadline and resolves to a bounded, retryable modal state without a global loader | Focused unit/API fault-injection tests and delayed browser test |
| WC092-A05 | Login/Register switching retains one captured origin and a sanitized `returnTo` target | Component and browser navigation tests, including repeated switching |
| WC092-A06 | Customer copy contains no “broker” terminology and uses Founder-directed WAOOAW growth/account language | Locale message tests and browser text assertions |
| WC092-A07 | Enabled providers are actionable; unavailable providers are visually and semantically grouped as Coming soon | Provider component tests plus axe/browser assertions |
| WC092-A08 | Provider return shows neutral account-resolution language until the server distinguishes an existing account from required registration | Authenticated RegisterView and registration bootstrap tests |
| WC092-A09 | Existing account handoff resumes the safe intended destination; new identity shows account completion | API/component tests for `handoffConfirmed` and registration projection |
| WC092-A10 | Persistent policy denial does not loop as a generic retry; the UI offers a fresh sign-in path with safe no-change language | Component/API fault test for 403 and browser error assertion |
| WC092-A11 | Business Platform logs exactly one stable denial-rule identifier without claim values or personal data | Focused validator/middleware tests with captured structured logs |
| WC092-A12 | Existing strict issuer, audience, provider, role, email-verification and timestamp checks remain fail-closed | Existing and expanded Business Platform security tests |
| WC092-A13 | 1366x768, 768x1024 and 360x800 modal states have no document overflow and pass serious/critical axe checks | Chromium/Firefox/WebKit browser matrix where repository runner supports it |
| WC092-A14 | Local evidence distinguishes fixture-backed behavior from unperformed real-provider acceptance | Final evidence section and PR test summary |

## Implementation Sequence

1. Add tests that reproduce delayed provider projection, modal loading ownership, dismissal, safe
   return preservation, neutral provider-return state and persistent 403 behavior.
2. Repair the auth route boundary and provider projection deadline with no new framework or state
   dependency.
3. Update English customer copy and the provider availability presentation; preserve localization
   fallback behavior and add explicit tests for changed source strings.
4. Add stable reason-code diagnostics at the strict Business Platform validation branches. Log only
   the rule identifier and operation context; never claim values or request identity.
5. Run focused Web and Business Platform tests in repository-defined containers immediately after
   each implementation slice.
6. Run production build/typecheck, focused browser matrix, accessibility checks, security/static
   checks and applicable repository pre-PR gates.
7. Complete author review against this matrix, prepare the exact commit-bound PR body, and submit the
   unmerged PR for Founder review.

## Evidence Plan

Evidence remains in existing owning surfaces and PR metadata; no parallel review document is created.

| Evidence | Intended location |
|---|---|
| Focused Web unit result and coverage | `test-results/wc092/web-unit.json` and coverage summary |
| Focused Business Platform test result | `test-results/wc092/business-platform.trx` |
| Browser interaction/accessibility result | `test-results/wc092/playwright.json` |
| Sanitized screenshots for modal states | `test-results/wc092/screenshots/` |
| Qualification summary bound to exact HEAD/images | `test-results/wc092/wc092-qualification.json` |
| Scope, checks, residual external gap and rollback | Pull request body |

Generated raw evidence is committed only when repository precedent and pre-PR policy require it;
otherwise the PR records deterministic command summaries and CI artifacts without repository churn.

## Stops

Stop rather than proceed when:

- a repair requires Azure, DNS, OAuth-console, provider-secret or protected-environment mutation;
- a visual fix changes the frozen public landing experience outside the auth overlay;
- account existence, provider policy, tenant identity or claim values would be disclosed;
- strict token validation would need to be weakened instead of diagnosing and correcting the producer;
- Login/Register behavior invents a new endpoint, account rule or identity-linking policy;
- a host dependency install, host language test environment or live customer identity is proposed;
- a failed check would be hidden, retried without diagnosis, or converted to an advisory result;
- the final branch is not pushed and bound to the exact author-reviewed commit;
- approval, merge, deployment, customer traffic or external-provider acceptance would be inferred.

## Definition Of Done

- [x] WC092-A01 through WC092-A14 have `PASS`, `BLOCKED` or `NOT_RUN` evidence with no unsupported pass.
- [x] Landing-page Login and Register remain modal-owned through delayed loading, switching, bounded
      failure and dismissal; direct routes remain standalone.
- [x] Existing and new customer flows are distinguished only by server-owned identity results, and
      the original safe destination is preserved.
- [x] Customer-facing auth text contains no identity-broker terminology and unavailable provider
      states are unambiguous.
- [x] The Business Platform 403 can be attributed to one privacy-safe validation rule without logging
      any token, claim value, provider subject or personal data.
- [x] Focused unit, API, browser, accessibility, type/build and security checks pass in repository
      containers, with fixture-backed and real-provider boundaries stated exactly.
- [x] Author review finds no unresolved in-scope correctness, security, accessibility, compatibility,
      failure-handling or rollback issue.
- [ ] The exact pushed HEAD passes `scripts/prepare_pr_body.py` and one unmerged PR is submitted for
      Founder review; no self-approval or merge occurs.

## Rollback

Rollback is the prior immutable release tuple. Web modal/copy changes and Business Platform
diagnostic changes are additive and independently revertible. No schema, customer data, provider
configuration or cloud resource is changed. If identity-policy correction cannot be proven without
weakening validation, retain the current fail-closed denial and report the exact blocker.

## Implementation Evidence

**Status:** ENGINEERING QUALIFIED LOCALLY

| Acceptance | Result | Evidence |
|---|---|---|
| WC092-A01 | PASS | Delayed-provider Playwright matrix proves the public hero remains visible while the immediate modal-owned loading dialog is open. |
| WC092-A02 | PASS | Playwright proves Close, Escape and backdrop dismissal restore the public origin; focused dialog and journey unit tests cover lifecycle and focus restoration. |
| WC092-A03 | PASS | All five browser projects prove direct `/login` remains standalone; route/component tests cover direct Register rendering. |
| WC092-A04 | PASS | Provider lookup uses a 12-second abort deadline and fail-closed projection; API unit tests and delayed browser execution pass. |
| WC092-A05 | PASS | Auth journey and view tests cover captured origin and sanitized `returnTo`; the intercepted Register route now forwards search parameters. |
| WC092-A06 | PASS | Full Jest run covers all 11 rendered locales; changed customer strings contain no internal broker terminology. |
| WC092-A07 | PASS | Provider component tests and all five browser projects prove Google/Email actionable and Facebook/Apple disabled under Coming soon. |
| WC092-A08 | PASS | Registration component tests prove neutral account resolution pending server-owned identity results. |
| WC092-A09 | PASS | Registration unit tests cover confirmed handoff and required completion; safe-return tests preserve allowlisted protected destinations. |
| WC092-A10 | PASS | Eighteen registration tests and all five browser projects prove persistent `403` no-change messaging, no generic retry loop and fresh sign-in preserving `/settings` through the real Web BFF. |
| WC092-A11 | PASS | Thirty-three adapter tests prove stable rule identifiers and assert that claim values, tokens and personal data are absent from structured log messages. Live rule identification awaits deployment. |
| WC092-A12 | PASS | Existing strict actor branches remain fail-closed; 33 adapter tests and 12 application-host tests pass. |
| WC092-A13 | PASS | Thirty Playwright cases pass across Chromium, Firefox, WebKit, 360x800 and 768x1024; the modal axe scan reports no serious or critical findings. Four screenshots were visually reviewed without clipping or overlap. |
| WC092-A14 | PASS | This record distinguishes local fixture/BFF evidence from unperformed deployed Google acceptance and the unresolved external hostname branding gap. |

### Local Qualification

- Web Jest: `44/44` suites, `289/289` tests, `0` snapshots.
- TypeScript: strict `tsc --noEmit --incremental false` passed.
- Web image: production `web/Dockerfile` build passed.
- Browser interactions/accessibility: `30/30` passed across five configured projects against the production Web image and a delayed local identity fixture.
- Visual capture: `1/1` passed; reviewed images are retained under `test-results/wc092/screenshots/`.
- Business Platform adapter: `45/45` passed after CI-equivalent CSharpier 1.3.0 formatting.
- Business Platform application host: `12/12` `CustomerIdentityProgramHostTests` passed with no adapter dependency-injection failure.
- Static/security: `git diff --check`, C-073 changed-file traceability, CSharpier 1.3.0, Business Platform vulnerable-package scan and pnpm high-severity audit passed.

### Pull Request Precheck Repair

- PR #425 image builds completed, then Constitutional Engine, Professional Runtime, AI Runtime and
   Billing Engine failed the shared Trivy 0.73.0 HIGH/CRITICAL vulnerability gate.
- Passing Business Platform and Web images isolated the failure to runtime-image package state. The
   failing Debian Bookworm bases contained `libpcre2-8-0 10.42-1`; the repository security candidate
   was `10.42-1+deb12u1`.
- Each affected final image now applies available Debian package upgrades and removes apt indexes
   before creating the non-root runtime user. Trivy policy, severity, ignore-unfixed behavior and
   failure exit code remain unchanged.
- Exact local builds and CI-equivalent Trivy 0.73.0 scans passed for Professional Runtime and
   Constitutional Engine. Both contained `libpcre2-8-0 10.42-1+deb12u1`, reported zero
   HIGH/CRITICAL findings and returned exit `0`, covering the Python slim Bookworm and .NET ASP.NET
   Bookworm runtime-base families. GitHub run `34693228900` subsequently passed all six image jobs,
   including the four repaired images.
- The same run passed all `674/674` Business Platform tests but exposed aggregate branch coverage of
  `79.77%` against the C-076 `80%` gate. Focused fail-closed tests now exercise previously uncovered
  service-client, subject, issued-at, expiry, lifetime, authentication-order and not-before rules;
   the expanded adapter suite passes `45/45` with CSharpier 1.3.0 clean. Exact CI-equivalent aggregate
   requalification passes `686/686` tests at `91.50%` line and `80.02%` branch coverage.

### Evidence Boundary And Residual Gaps

- Browser evidence uses a synthetic signed NextAuth session and a local HTTP Business Platform fixture. It proves Web BFF behavior, not Google, Keycloak or deployed Business Platform acceptance.
- No Azure, DNS, provider-console, secret, deployment or customer-traffic mutation occurred.
- The exact Demo `403` denial rule remains unknown until this diagnostic-only Business Platform change is deployed under separate authority and a new sanitized log record is observed.
- Google consent branding that displays an `azurecontainerapps.io` hostname remains an external configuration gap outside this Work Component.
- The earlier canceled namespace-wide Business Platform run is not evidence; the later exact
   CI-equivalent `686/686` run and its `91.50%` line / `80.02%` branch report supersede it.

## Author Review

**Status:** PASS

Reviewed the complete authorized diff, local qualification results, privacy boundary, rollback path and
fixture-versus-provider evidence. No unresolved in-scope correctness, security, accessibility,
compatibility or failure-handling finding remains. The implementation preserves strict fail-closed
identity validation and adds diagnostics without changing policy. Founder review, approval, deployment,
real-provider acceptance and merge remain explicitly reserved.