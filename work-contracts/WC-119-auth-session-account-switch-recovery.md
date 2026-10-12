# WC-119 - Authentication Session Account-Switch Recovery

## Record Control

| Field | Value |
|---|---|
| Office | Platform IT Expert (INST-010), Skills 4, 5, 6, 12, 14 and 16 |
| Authorized by | Founder instruction in the 2026-10-12 working session |
| Status | IMPLEMENTATION AUTHORIZED - SOURCE, TESTS, AND UNMERGED PR |
| Baseline | `41791f5c639f12abd83d16c57cf2017d67261e0f` |
| Delivery unit | One bounded defect-repair PR |

## Authority And Scope

The Founder authorized a new Work Component to repair the Demo authentication defect evidenced on
2026-10-12. The repair is limited to stale-session recovery and account switching across the existing
Web, NextAuth, Business Platform session-revocation, and Keycloak RP-logout boundaries, plus focused
tests and directly impacted post-logout configuration.

No account linking, provider policy weakening, unrelated authentication behavior, cloud mutation,
deployment, customer-data access, Production action, approval, or merge is authorized.

## Inputs

- Founder-provided Login, Google account-selection, and Facebook consent screenshots.
- Read-only Azure Demo telemetry for revisions `ca-demo-web--0000060`,
  `ca-demo-business-platform--0000055`, `ca-demo-identity-edge--0000003`, and
  `ca-demo-keycloak--0000011`.
- `architecture/reference/components/identity-boundary.md` Section 11.
- `architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md`
  `AUTH-STATE-01`.
- WC105-R028, WC105-R043, WC105-R044, and WC107-R004.
- Exact `origin/main` baseline and repository Docker runners.

## Root-Cause Evidence

- At `2026-10-12T05:12:32Z`, Keycloak emitted `IDENTITY_PROVIDER_LOGIN_ERROR` with
  `error="different_user_authenticated"` for the Google broker. The event identifies different
  opaque prior and selected identities, proving an active Keycloak SSO session survived while a
  different Google account was selected.
- Business Platform returned `403` from `GET /api/v1/identity/session` before and after the broker
  rejection. The Web client maps that typed problem to the recoverable Login state and displays its
  correlation reference.
- The Web Account Switch implementation revoked Business Platform authority and cleared NextAuth,
  but did not execute Keycloak RP-initiated logout. Direct provider launch from Login likewise did
  not clear an already conflicting Keycloak SSO session.
- All affected Container Apps were running and provisioned successfully; Identity Edge requests
  completed normally. This excludes service availability, callback routing, and image startup as
  the primary cause.

## Canonical Requirement Index

| Requirement | Required observable behavior | Executable evidence |
|---|---|---|
| WC119-R001 | A recoverable Login session denial must not launch a broker while stale NextAuth/Keycloak authority remains. The selected provider action first starts the nonce-bound RP logout transition. | Login/provider component tests. |
| WC119-R002 | Account Switch must revoke WAOOAW sessions, clear protected browser state, preserve the server-held ID token until the nonce is redeemed, and traverse Keycloak RP logout before returning to Login. | Account-switch and logout-route tests. |
| WC119-R003 | Keycloak post-logout return is the exact same-origin `/login` target already declared by the environment identity manifests. Arbitrary browser return targets remain prohibited. | Logout-route and Terraform/config assertions. |
| WC119-R004 | A clean Login or Registration provider launch remains direct; Google retains `prompt=select_account` and `max_age=0`; Facebook behavior remains unchanged. | Provider command regression tests. |
| WC119-R005 | Revocation, logout, or continuation failure is shown truthfully and never falls through to broker launch or successful account switching. | Component and route failure-path tests. |
| WC119-R006 | Focused and impacted Web checks pass in the repository Docker runner; author review confirms no unrelated functional change. | Docker test, lint/type/build evidence and final diff review. |

## Definition Of Done

- Requirements are mirrored in `work-contracts/WC-119-requirements.yaml`.
- The stale-session provider path and authenticated Account Switch both traverse the existing
  nonce-bound Keycloak logout route before a different broker actor can authenticate.
- Normal provider launch, safe-return, sign-out, registration, and failure behavior remain covered.
- Focused and impacted Web validation passes in the Docker TypeScript runner.
- Author review covers authentication state transitions, privacy, CSRF, open redirect, failure
  handling, rollback, and scope.
- The exact-head branch is pushed and one unmerged PR is submitted for Founder review.

## Stop Conditions

Stop on any requirement to auto-link accounts, ignore `different_user_authenticated`, weaken
state/nonce/PKCE/CSRF checks, accept an arbitrary post-logout URL, expose identity data, add a
dependency, mutate a provider or cloud environment, deploy, bypass a quality gate, self-approve, or
self-merge.

## Exclusions

- Facebook consent denial (`access_denied`, provider permissions error) is separate provider/user
  behavior and is not changed by this Work Component.
- Live Demo deployment and real-provider acceptance.
- Email, Apple, mobile, registration-profile, Marketplace, billing, and agent functionality.
