# WC-098 - Customer Registration Readiness

**Office:** Platform IT Expert (INST-010), Skills 2, 4, 16 and 17
**Authorized by:** Founder instruction in the 2026-09-16 working session
**Status:** IMPLEMENTATION AUTHORIZED - SOURCE, TESTS, EVIDENCE, AND UNMERGED PR
**Baseline:** PR #444 merged as `c0d24a09`; Demo deployment run `35090381432`
**Constitutional basis:** C-023, C-042, C-049, C-059, C-063, C-065, C-071, C-076; ADR-008
**Normative component:** `architecture/reference/components/customer-portal-ui-coherence.md` §3.2 and CPUI-A06 through CPUI-A10, CPUI-A17, CPUI-A19 and CPUI-A20

## Goal

Make customer registration truthful, recoverable, and operationally ready: the portal has one
deterministic dark default, presents the broker-verified primary email without allowing silent
mutation, and never offers an SMS action that the deployed platform cannot complete.

## Objectives

1. Remove `system` as a supported portal theme, default every new or invalid preference to dark,
   and retain an explicit light/dark customer toggle.
2. Present the broker-verified email as a read-only primary registration field with its provider
   source; require email verification when the broker has not supplied a verified email claim.
3. Repair registration actor continuity so every registration operation uses the same verified
   issuer-and-subject identity boundary.
4. Keep mobile verification visibly optional but disabled, with honest budget/readiness copy, until
   a separately authorized SMS dispatcher and India delivery budget exist.
5. Preserve typed identity failures through the Web boundary and provide bounded skip, back,
   restart, or retry recovery appropriate to the failure.
6. Remove duplicate and implementation-oriented registration headings.

## Requirements

| ID | Requirement |
|---|---|
| WC098-R01 | `ThemePreference` accepts only `dark` and `light`; absent, invalid, and legacy `system` values resolve to `dark`. |
| WC098-R02 | Server-rendered first load and hydrated controls agree on dark when no valid preference exists. |
| WC098-R03 | Registration projects a masked or full broker-verified primary email according to the approved identity response, marks it read-only, and identifies Google or Facebook as its source. |
| WC098-R04 | A missing or unverified broker email follows the existing email-verification state; no browser assertion may mark email verified. |
| WC098-R05 | Start, read, profile, email, mobile, and completion operations authorize the registration through one `VerifiedCustomerActor` representation. |
| WC098-R06 | Optional SMS verification is disabled in the registration UI while the runtime uses `UnconfiguredVerificationDispatcher`; completion without mobile remains available. |
| WC098-R07 | The Web registration proxy retains approved problem `code`, status, and correlation identifier while excluding secrets and internal detail. |
| WC098-R08 | Registration has one customer-facing title and description owner; copy describes account creation rather than broker implementation. |
| WC098-R09 | Provider projection cold start cannot be presented as permanent provider disablement without an actionable bounded retry. |
| WC098-R10 | No provider scope, credential ownership, account semantics, Production state, or SMS vendor commitment changes in this Work Contract. |

## Definition Of Done

| ID | Completion condition | Required evidence |
|---|---|---|
| WC098-D01 | Dark is the deterministic default and only dark/light values are persisted or rendered. | Preference, root-layout and control tests pass. |
| WC098-D02 | Registration displays one read-only broker-verified email and provider source; unverified email still requires verification. | Component and Business Platform journey tests pass. |
| WC098-D03 | A real journey-service registration can reach every authorized registration operation without `IDENTITY_RESOURCE_NOT_ACCESSIBLE`. | PostgreSQL or production-shaped HTTP integration regression passes. |
| WC098-D04 | SMS is labelled optional, disabled, and unavailable pending budget/provider activation; account completion remains usable. | Component and browser acceptance pass. |
| WC098-D05 | Approved backend problem codes produce distinct safe recovery, including registration restart for inaccessible state. | Route and component tests pass. |
| WC098-D06 | Login/Register provider cold-start behavior remains fail-closed but exposes bounded retry rather than four unexplained disabled controls. | API/component test proves timeout then recovery. |
| WC098-D07 | No duplicate registration title, inaccessible close control, overflow, or dead-end occurs at 360x800 and 1440x900. | Chromium screenshots, accessibility scan, and journey assertions pass. |
| WC098-D08 | Final commit passes focused Web, Business Platform, OpenAPI, lint, type, build, security, and applicable-diff pre-PR gates in repository Docker containers. | Attached qualification and prepared PR evidence. |
| WC098-D09 | Founder-reported provider, registration, and mobile journeys are repeated against one exact Demo revision. | Post-deployment Azure log correlation and Founder acceptance; not claimable by local evidence. |

## Root-Cause Evidence

Demo run `35090381432` deployed source `474a8bcb` as Web revision `ca-demo-web--0000044`
and Business Platform revision `ca-demo-business-platform--0000039`. Azure retained logs show:

- Business Platform scaled from zero at `2026-09-16T12:34:02Z`; containers started at
  `12:34:25Z`. Web provider projection failed twice during that interval and substituted its
  all-unavailable fallback. Provider discovery recovered with HTTP 200 at `12:35:26Z`.
- registration `7880a19e-e668-41ee-8585-b78b0c4bb60e` was created with HTTP 201 and its profile
  updated with HTTP 200, then six mobile-verification starts returned HTTP 404
  `IDENTITY_RESOURCE_NOT_ACCESSIBLE`.
- broker registration stores `VerifiedCustomerActor.Subject`, while the mobile endpoint uses the
  legacy composite `issuer + separator + subject` key. The mismatch rejects the same registration.
- the deployed runtime registers `UnconfiguredVerificationDispatcher`; SMS delivery cannot succeed
  after actor continuity is repaired.
- Keycloak recorded `LOGOUT_ERROR session_expired` at `11:53:11Z` and a later inactive-session
  refresh failure. No complete distributed trace exists because Demo OpenTelemetry is not enabled.

## Authority, Cost, And Stops

Authorization covers the existing Web and Business Platform registration code, generated contract
when required, focused tests, local Docker qualification, evidence files, and one unmerged PR. It
does not authorize an SMS vendor, DLT registration, message spend, secret creation, Azure mutation,
Demo deployment, UAT, Production, customer traffic, provider-scope change, approval, or merge.

Stop if implementation would expose an unmasked email outside the authenticated registration
boundary, let the browser assert email verification, weaken issuer-and-subject isolation, enable SMS
without a dispatcher and budget, or infer deployment acceptance from local tests.

## Rollback

Revert the WC-098 implementation commits and redeploy the prior exact release tuple. Rollback must
preserve existing registration, account, identity, idempotency, and customer preference records.
Legacy `system` preferences remain safely interpreted as dark during forward operation; rollback
must not rewrite customer records or disclose identity data.