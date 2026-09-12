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

- [ ] WC092-A01 through WC092-A14 have `PASS`, `BLOCKED` or `NOT_RUN` evidence with no unsupported pass.
- [ ] Landing-page Login and Register remain modal-owned through delayed loading, switching, bounded
      failure and dismissal; direct routes remain standalone.
- [ ] Existing and new customer flows are distinguished only by server-owned identity results, and
      the original safe destination is preserved.
- [ ] Customer-facing auth text contains no identity-broker terminology and unavailable provider
      states are unambiguous.
- [ ] The Business Platform 403 can be attributed to one privacy-safe validation rule without logging
      any token, claim value, provider subject or personal data.
- [ ] Focused unit, API, browser, accessibility, type/build and security checks pass in repository
      containers, with fixture-backed and real-provider boundaries stated exactly.
- [ ] Author review finds no unresolved in-scope correctness, security, accessibility, compatibility,
      failure-handling or rollback issue.
- [ ] The exact pushed HEAD passes `scripts/prepare_pr_body.py` and one unmerged PR is submitted for
      Founder review; no self-approval or merge occurs.

## Rollback

Rollback is the prior immutable release tuple. Web modal/copy changes and Business Platform
diagnostic changes are additive and independently revertible. No schema, customer data, provider
configuration or cloud resource is changed. If identity-policy correction cannot be proven without
weakening validation, retain the current fail-closed denial and report the exact blocker.

## Implementation Evidence

**Status:** PENDING

## Author Review

**Status:** PENDING