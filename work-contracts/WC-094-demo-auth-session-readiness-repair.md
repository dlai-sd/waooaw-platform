# WC-094 - Demo Authentication Session And Readiness Repair

**Office:** Platform IT Expert (INST-010), Skills 4, 16 and 17
**Authorized by:** Founder instruction in the 2026-09-14 working session
**Status:** IMPLEMENTATION AUTHORIZED - SOURCE, TESTS, DEMO DEPLOYMENT CANDIDATE, AND UNMERGED PR
**Baseline:** PR #431 merged as `894a0d28`; Demo deployment run `34840438904`
**Constitutional basis:** C-023, C-049, C-059, C-063, C-065, C-071, C-076; ADR-008

## Objective

Repair the observed Demo authentication defects without changing provider scopes, identity ownership,
or customer-account semantics:

1. logout clears the local NextAuth session, WAOOAW cookies and WAOOAW browser storage, ends the
   Keycloak session, and returns to the public homepage;
2. intercepted Login and Register routes show the approved branded destination while loading;
3. transient provider-projection failure does not make Login disagree with Register, while repeated
   failure remains honestly unavailable;
4. a failed provider launch restores all provider controls without a page reload; and
5. completed registration can enter the portal because Business Platform receives a dedicated
   minimum-256-bit continuity-envelope HMAC key.

## Authority And Stops

Authorized work is limited to the existing Web and Business Platform deployment configuration,
focused tests, generated Demo readiness evidence, and one unmerged PR. Keycloak remains the sole
credential broker. Google and Facebook remain independently projected by Business Platform. No
provider credential, token, authorization code, customer PII, new scope, direct provider call, DNS
change, UAT mutation, Production mutation, approval, or merge is authorized.

Stop if the repair requires reusing identity HMAC material for continuity, exposing a secret,
weakening fail-closed readiness, bypassing Keycloak, or claiming UAT/Production qualification from
Demo evidence.

## Acceptance And Evidence

| ID | Acceptance condition | Evidence |
|---|---|---|
| WC094-A01 | Logout ends Keycloak/NextAuth state, removes WAOOAW state, preserves unrelated state, and returns to `/` | Route/client unit tests and Chromium/Firefox browser evidence pass |
| WC094-A02 | Login/Register loading uses the same brand, title and subtitle as the resolved route | Focused component and browser tests |
| WC094-A03 | One transient BP projection failure retries; repeated failure remains unavailable | Identity API unit tests and Chromium/Firefox provider-parity evidence pass |
| WC094-A04 | A rejected provider launch restores Google and Facebook controls | Provider-command unit tests pass |
| WC094-A05 | Continuity HMAC uses its own generated Key Vault secret, RBAC grant and BP environment binding | Environment renderer and deployment tests pass in the Docker test runner |
| WC094-A06 | Existing auth, accessibility, lint, type and build gates remain passing | Web unit suite: 308/308; pipeline suite: 31/31; lint, TypeScript and production build pass |

## Qualification Evidence

- Web unit suite: 308 tests passed.
- WC-094 Playwright suite: 4 tests passed across Chromium and Firefox.
- Pipeline suite: 31 tests passed in the repository Docker test runner.
- Next.js lint, TypeScript checking and production build passed.
- Browser evidence is limited to Chromium and Firefox; WebKit is not claimed.

## Root-Cause Evidence

Azure logs for `2026-09-14T12:13:20Z` through `12:23:20Z` showed registration start `201`, profile
`200`, completion `200`, then eight relationship-load `500` responses. The first causal exception was
`Continuity envelope HMAC key must contain at least 256 bits`; the live BP revision had no
`ChannelContinuity__EnvelopeHmacKey` binding. Demo configured Google and Facebook available, while
the Web projection used one bounded request and silently substituted unavailable providers on any
failure. The loading route rendered a generic boundary, and logout removed only session-token cookie
variants while persisting a new WAOOAW cross-tab marker.

## Rollback

Revert the WC-094 commits and redeploy the prior exact release tuple. If the continuity secret was
created, leave it disabled or unreferenced according to the environment secret-retention policy; do
not disclose or manually copy its value. Provider availability remains fail-closed throughout rollback.