# WC-090 - Facebook Login Enablement And Google Readiness Repair

**Office:** Platform IT Expert (INST-010)
**Authorization:** Founder-authorized in the 2026-09-10 working session
**Status:** IMPLEMENTATION AUTHORIZED - LOCAL AND DEMO ONLY
**Registration amendment:** Founder-authorized in-session on 2026-09-10 for an allowlisted,
provider-neutral broker-proof boundary limited to `google` and `facebook`
**Derived from:** WC-084 SP-04 and Section 6.4
**Baseline:** PR #416 merged to `origin/main` before this Work Contract
**Constitutional basis:** C-001, C-023, C-026, C-049, C-059, C-063, C-065, C-071, C-076, C-080

## Objective

Enable Facebook login and registration through the existing WAOOAW Web to NextAuth to Keycloak
broker path, and repair the deployed Google provider readiness projection that remains
`Unavailable` after PR #416. Preserve Keycloak as the sole web credential authority and
`GET /api/v1/identity/providers` as the canonical anonymous provider projection.

## Authority And Scope

Authorized work is limited to:

- local configuration and Docker validation;
- Demo Azure Key Vault secret binding and the minimum required Demo identity workload revision or
  restart;
- Keycloak `facebook` broker configuration using Meta App ID `2590813568086235`, login-only scopes
  `email` and `public_profile`, and an approved Demo callback;
- Facebook provider readiness projection and login, registration, cancellation, missing-email,
  repeat-login, sign-out, and failure-path validation;
- provider-specific namespace and trust-digest selection from the signed Keycloak `idp` alias;
- diagnosis and repair of Google broker/readiness drift after merged PR #416;
- focused tests, governed Demo qualification, and one separate pull request for Founder review.

This Work Contract does not authorize UAT, Production, DNS changes, customer traffic, new provider
permissions, expenditure beyond existing Demo resources, secret disclosure, self-approval,
self-merge, or direct push to `main`.

## Work Items

### WC090-01 - Facebook Login Enablement

- Verify the published Meta application, approved login-only permissions, and exact Demo callback.
- Accept the Meta App Secret only through direct terminal entry; never commit, log, or echo it.
- Bind the credential through the approved Demo Key Vault and workload secret-reference path.
- Enable the Keycloak broker and Demo provider projection only when all readiness layers agree.
- Prove returning login and first-time registration, including cancellation and absent-email failure.
- Preserve issuer plus Keycloak subject as the actor key; preserve alias plus opaque upstream subject
      as the login-method key; never use email as identity or persist a provider token.

### WC090-02 - Google Login Readiness Repair

- Treat merged PR #416 and workflow run `34500758490` as the starting evidence, not proof of current
  Demo state.
- Identify the first divergence among Key Vault binding, workload environment, Keycloak broker,
  Business Platform configuration, and anonymous provider projection.
- Repair only the owning configuration or code path and re-run the narrowest applicable checks.
- Prove that Google is projected `AVAILABLE` only when the real Demo broker is usable.

## Required Inputs

| Input | Required state |
|---|---|
| WC-084 SP-04 and Section 6.4 | Present as the controlling provider-readiness design |
| PR #416 baseline | Merged into the branch base |
| Meta application | Published; App ID `2590813568086235`; `email` and `public_profile` approved |
| Facebook callback | Exact Demo Keycloak broker callback registered in Meta |
| Meta App Secret | Supplied only through direct terminal entry when requested |
| Google OAuth credentials | Existing approved Demo secret material; no disclosure or replacement without need |
| Azure authority | Current-session Founder authorization for Demo-only mutations |
| Implementation authority | Current-session Founder authorization recorded above |

Missing or unverifiable input blocks only the affected provider unless it invalidates the shared
identity path.

## Implementation And Validation

1. Establish a clean branch and capture the merged PR #416 baseline.
2. Trace each provider through Key Vault reference, workload environment, Keycloak broker, Business
   Platform configuration, and `GET /api/v1/identity/providers`.
3. Add or update the smallest configuration and code changes required for truthful readiness.
4. Run focused Docker tests immediately after each substantive edit.
5. Apply only authorized Demo secret/configuration changes and record non-secret resource evidence.
6. Validate real browser redirects and callbacks without recording provider tokens or customer data.
7. Run applicable final Docker, C-059, C-065, secret-scan, and PR preparation gates.

## Definition Of Done

- [ ] Facebook is `AVAILABLE` in Demo only when its Keycloak broker and approved credentials are
      active; its real login and registration paths pass.
- [ ] Facebook denial, cancellation, missing email, repeat login, sign-out, and provider failure are
      safe, truthful, and do not expose account existence or secrets.
- [ ] Google no longer appears `Unavailable` in Demo when its approved broker is healthy, and the
      cause of the PR #416 deployment mismatch is repaired at the owning layer.
- [ ] `GET /api/v1/identity/providers` remains fail-closed and exposes no credentials, internal
      endpoints, or provider tokens.
- [ ] Local and Demo validation use Docker test runners and approved deployment tooling.
- [ ] No secret appears in Git history, logs, test artifacts, screenshots, or the PR body.
- [ ] One final-HEAD-bound PR passes applicable repository prechecks and is submitted for Founder
      review without self-approval or self-merge.

## Stops

Stop rather than proceed when:

- the Meta callback, approved permissions, or direct-entry secret is missing;
- a credential cannot be stored through the approved Azure Key Vault reference path;
- a provider would be marked available without a usable broker and complete readiness evidence;
- the repair requires architecture invention, a new dependency, UAT or Production mutation, DNS,
  customer traffic, or unapproved spend;
- a command would print, persist, or transmit a secret through chat, Git, logs, or artifacts;
- deterministic validation fails and the owning defect cannot be isolated within this scope;
- PR approval, merge, or direct `main` mutation would be required.