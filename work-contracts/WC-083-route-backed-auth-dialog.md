# WC-083 - Route-Backed Authentication Dialog

**Office:** Platform IT Expert (Office 10)
**Authorization:** Founder-authorized in the 2026-09-06 working session
**Status:** IMPLEMENTED - PR validation pending
**Constitutional basis:** C-049, C-059, C-063, C-071, C-076
**Controlling identity contract:** `architecture/reference/components/identity-boundary.md`
**Depends on:** WC-077 shared identity foundation

## Objective

Deliver a WAOOAW-native login and registration dialog that preserves canonical server-backed routes,
Keycloak as the sole credential authority, Business Platform provider readiness, safe internal return
targets, and the existing registration state machine. The dialog must provide truthful Google,
Facebook, Apple, and email choices; Apple remains a non-authenticating placeholder. Registration must
show an accessible WAOOAW progress visual driven by actual workflow state.

This sprint does not change landing-page content, public navigation items, global fonts, or approved
brand tokens. It does not activate an identity provider, collect credentials in WAOOAW application
code, or treat a WhatsApp session as a Keycloak session.

## Delivery Plan

### Milestone 1 - Route-backed dialog and providers

- Keep `/login` and `/register` as canonical direct-entry and OAuth-return routes.
- Intercept public navigation to present those routes in an accessible dialog over the originating
  public page.
- Restore the invoking route and focus on backdrop or Escape dismissal.
- Project provider readiness from `GET /api/v1/identity/providers`; fail closed when it is unavailable.
- Pass only a stable provider ID from browser code. Resolve the environment-owned Keycloak broker
  alias on the server before issuing `kc_idp_hint`.
- Show unavailable providers honestly. Apple never starts OAuth in this sprint; clicking it shows a
  localized coming-soon message naming only currently available alternatives plus email/WhatsApp
  registration guidance.

### Milestone 2 - Registration progress

- Reuse the existing server session decision and `RegistrationFlow` state machine.
- Add a six-state `WAOOAW` progress visual mapped to actual `nextAction` values.
- Preserve textual status, error semantics, reduced-motion behavior, RTL, dark theme, and mobile
  layout.
- Do not expose a fabricated percentage or mark an optional step as mandatory.

### Milestone 3 - Qualification and review

- Add focused unit and browser tests for provider readiness, server-side broker translation, safe
  return handling, dialog semantics, focus restoration, Escape/backdrop dismissal, direct-route
  fallback, Apple placeholder behavior, registration progress, reduced motion, RTL, and mobile.
- Run Docker qualification after Milestones 1 and 2 are assembled, then once on finalized clean HEAD.
- Capture generated-client consistency, build, unit coverage, Playwright/axe, screenshots, SBOM,
  Trivy, Gitleaks history/diff, and applicable repository precheck evidence.
- Prepare the PR body only after the final push and submit the exact prechecked body.

## Cost And Time Controls

- Read only the owning routes, components, contracts, and neighboring tests.
- Reuse generated clients, existing design tokens, identity state machines, and test harnesses.
- Run focused host checks after small edits; do not rebuild Docker images for each edit.
- Run Docker only at completed major milestones and final qualification.
- Keep one machine-readable evidence ledger and one session recovery checkpoint.
- Prefer deterministic checks that fail before expensive browser or image-scan stages.

## Definition Of Done

- [x] `/login` and `/register` remain functional canonical routes when opened directly or refreshed.
- [x] Public login and registration entry points open route-backed dialogs without changing public
      navigation labels or landing-page content.
- [x] Dialog has an accessible name, modal semantics, focus containment, Escape/backdrop dismissal,
      focus restoration, scroll containment, and responsive mobile behavior.
- [x] Return destinations are same-origin and allowlisted; external and protocol-relative targets are
      rejected.
- [x] Google and Facebook start only when projected `AVAILABLE` and always use NextAuth to Keycloak.
- [x] Provider IDs are translated to broker aliases server-side; aliases, secrets, and provider tokens
      are not projected to or stored by browser code.
- [x] Apple remains non-authenticating and displays an honest coming-soon message with available
      alternatives.
- [x] Email remains a Keycloak-owned fallback. WhatsApp is presented only as an approved registration
      path and never upgraded locally into a web session.
- [x] Registration keeps the current idempotent, data-minimizing workflow and gains state-driven,
      reduced-motion-safe WAOOAW progress.
- [x] Focused tests, full unit coverage gate, Playwright/axe, Docker build, SBOM, Trivy, Gitleaks, and
      applicable repository prechecks pass on final HEAD.
- [x] Evidence is recorded against the final commit and attached or linked in the PR body.
- [ ] All required PR checks pass before the PR is handed to the Founder for review and merge.

## Evidence Ledger

| Evidence | Required result | Final reference |
|---|---|---|
| Focused auth unit tests | PASS | `jest.json`: included in 188/188 passing tests |
| Business Platform provider tests | PASS | `provider-tests.trx`: 9/9 passing tests |
| Generated API consistency | No applicable branch diff | WC-083 changes neither API specs nor generated client output |
| Web production build | PASS | `wc083-qualification.json`: production build and typecheck PASS |
| Jest coverage | Repository thresholds PASS | `coverage/coverage-summary.json`: 94.77% lines, 82.59% branches, 91.87% functions, 91.89% statements |
| Playwright auth/public matrix | PASS; zero unexpected failures | `playwright.json`: 20 passed, 0 skipped |
| Axe accessibility | Zero serious or critical violations | `wc083-qualification.json`: axe PASS |
| Desktop/mobile/RTL/dark screenshots | Reviewed against final HEAD | `screenshots.sha256`: four reviewed captures |
| Docker image build and runtime smoke | PASS | `wc083-qualification.json`: image digests and runtime probes recorded |
| SBOM and Trivy | Generated; zero blocking vulnerabilities | `sbom.json`; `trivy.json`: 0 findings |
| Gitleaks history and applicable diff | Recorded; diff has zero findings | `gitleaks-history.json`; `gitleaks-diff.json`: 0 diff findings |
| PR body precheck | PASS against `origin/main` | Pending |
| GitHub PR status checks | All required checks PASS | Pending |

## Stop Conditions

- Stop rather than activate Google, Facebook, or Apple without accepted environment readiness.
- Stop rather than add direct provider API calls, browser credential verification, or provider-token
  persistence.
- Stop rather than broaden changes into landing content, menu items, global font selection, or brand
  color changes without new Founder authorization.
- Stop and report if the canonical OAuth callback cannot remain route-backed or if Docker evidence
  cannot be bound to the final commit.