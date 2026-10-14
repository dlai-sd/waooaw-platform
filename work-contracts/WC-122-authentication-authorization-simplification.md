# WC-122 - Authentication and Authorization Simplification

## 0. Record Control

| Field | Value |
|---|---|
| Work Contract | WC-122 |
| Version | 1.0.0-candidate.2 |
| Status | AUTHOR CANDIDATE - IMPLEMENTATION BLOCKED |
| Authorized by | Founder instruction in the 2026-10-14 continuous working session |
| Authoring office | Platform IT Expert, Office 10 |
| Specification office | Chief Solution Architect, Office 05 |
| Required decision authorities | Founder; Enterprise Architect for accepted ADR amendment or identity-platform replacement |
| Implementation office | Platform IT Expert after a separately accepted implementation Work Contract and explicit current-session authorization |
| Solution output | `architecture/reference/components/authentication-authorization-simplification-solution-contract.md` |
| Result | PLANNED |

This Work Contract authorizes requirements and solution-specification work only. It does not
authorize changes under `src/` or `web/`, generated implementation artifacts, dependency changes,
provider-console mutation, secrets, cloud mutation, deployment, external traffic, activation,
approval, or merge.

## 1. Problem Statement

WAOOAW currently coordinates authentication and session state across an external provider,
Keycloak, NextAuth, and Business Platform identity-session records. Login, registration, logout,
account switching, token refresh, tenant resolution, and recovery consequently cross multiple
partially overlapping authorities.

The result is a secure-intent but operationally fragile customer journey:

1. WAOOAW logout can end the application session while a conflicting Keycloak SSO session remains.
2. Broker account selection can fail with `different_user_authenticated`.
3. expired or deployment-invalidated provider authority can remain apparently active to the Web
   application until a downstream API rejects it;
4. registration is represented as an exceptional API response rather than a normal post-
   authentication onboarding state;
5. login and registration expose different navigation while launching the same broker providers;
6. ordinary account switching requires custom recovery orchestration;
7. access, refresh, and ID tokens are copied into the browser-carried NextAuth JWT session; and
8. ephemeral identity state can invalidate signing keys, users, and sessions across deployments.

The Chief Solution Architect must replace this lifecycle with one identity authority, one WAOOAW
application session, and application-owned tenant authorization without weakening the accepted
identity, privacy, tenant-isolation, evidence, or provider boundaries.

## 2. Customer Outcome

Customers must be able to:

1. select Google, Apple, Facebook, or Email from one authentication entry experience;
2. complete authentication once and be routed deterministically either to their WAOOAW workspace
   or to bounded onboarding;
3. sign out of WAOOAW reliably even when an upstream provider is unavailable;
4. explicitly use another account without stale application or Keycloak authority;
5. switch an authorized tenant or workspace without authenticating again;
6. link or unlink providers only through explicit, freshly authenticated, anti-enumerating actions;
7. recover from an expired, revoked, redeployed, or otherwise invalid session without generic fatal
   pages or retry loops; and
8. receive the same safe identity outcome across Demo, UAT, and Production-shaped configuration.

## 3. Constitutional and Architectural Basis

The solution must preserve:

1. C-023 and C-026 tenant isolation and current-membership authorization;
2. C-049 truthful limitation and explicit failure behavior;
3. C-059 specification-to-implementation traceability;
4. C-063 data minimisation;
5. ADR-003 JWT and multi-tenancy controls;
6. ADR-008 Keycloak identity-broker authority until explicitly superseded;
7. ADR-017 Web Application boundary;
8. the WC-034 Identity and Registration Contract;
9. the WC-085 Identity Architecture Decision;
10. the Identity Session Security Contract;
11. accepted WC-105 and WC-119 evidence, while superseding their patch-oriented lifecycle only
    after Founder acceptance and any required ADR amendment; and
12. exact environment origins and callback stability established by the Demo public-domain delivery.

The Chief Solution Architect must identify every conflict with an accepted ADR. The solution may
propose an amendment but may not silently override or create an ADR.

The solution must also conform to:

1. OAuth 2.0 Security Best Current Practice, RFC 9700;
2. OAuth 2.0 for Browser-Based Applications, RFC 10017;
3. OpenID Connect Core 1.0;
4. OpenID Connect RP-Initiated Logout 1.0; and
5. provider-published OIDC/login requirements for the exact enabled Google, Apple, Facebook, and
   Email mechanisms.

## 4. Scope

### 4.1 In scope

- authentication, registration/onboarding, callback, refresh, logout, account-switch, provider-
  linking, tenant-switch, revocation, and recovery state machines;
- one browser-facing application-session authority and its persistence owner;
- Keycloak identity-broker and external-provider responsibilities;
- Google, Apple, Facebook, and Email provider behavior;
- immutable identity keys and explicit account-linking rules;
- separation of global user identity, customer profile, tenant membership, active tenant context,
  and institutional identity;
- Business Platform API authentication and authorization boundaries;
- session and signing-key continuity by environment;
- privacy-safe security telemetry and deterministic customer-visible errors;
- migration from current NextAuth JWT sessions and Business Platform session orchestration;
- rollout, forced-session cutover, rollback, and same-image environment configuration;
- provider-console, DNS, TLS, redirect, mail, and secret prerequisites; and
- implementation-ready acceptance oracles.

### 4.2 Out of scope

- runnable implementation or generated code;
- selecting or purchasing a managed identity vendor;
- changing immutable constitutional records;
- provider-console, Key Vault, Azure, DNS, or deployment mutation;
- customer migration or traffic activation;
- weakening current membership, RLS, assurance, step-up, Stop, audit, or anti-enumeration controls;
- automatic provider linking based only on email;
- a new public identity facade or browser access to private services; and
- Production activation.

## 5. Required Architectural Decisions

The Chief Solution Architect must close each decision in the solution contract.

| ID | Decision |
|---|---|
| AUTHZ-SD-01 | Select exactly one identity authority. The compatible default is durable stock Keycloak; replacing it with managed CIAM requires a separately accepted EA/Founder decision. |
| AUTHZ-SD-02 | Select exactly one WAOOAW browser application-session authority using an opaque `Secure`, `HttpOnly` cookie and server-held tokens. |
| AUTHZ-SD-03 | Remove Business Platform from routine browser-session ownership while preserving API authorization, revocation evidence, and security audit responsibilities. |
| AUTHZ-SD-04 | Define the immutable global identity key as exact issuer plus subject; email, phone, tenant, provider display name, or browser state is never the identity key. |
| AUTHZ-SD-05 | Unify login and registration into one authentication ceremony followed by deterministic post-authentication routing. |
| AUTHZ-SD-06 | Make onboarding an explicit application state, not an exceptional authentication failure. |
| AUTHZ-SD-07 | Separate account switching, tenant switching, local logout, global WAOOAW logout, provider unlinking, and security revocation. |
| AUTHZ-SD-08 | Define explicit provider-linking and collision recovery without silent email linking or duplicate account creation. |
| AUTHZ-SD-09 | Define durable identity configuration, signing-key, provider-link, and user continuity for every environment used for repeatable authentication. |
| AUTHZ-SD-10 | Define a bounded migration that invalidates incompatible legacy sessions once and cannot leave mixed session authorities active. |

## 6. Mandatory Solution Requirements

### 6.1 Authentication and browser session

1. Use OIDC Authorization Code with PKCE, exact issuer and redirect validation, state, nonce, and
   mix-up protection.
2. External provider tokens, Keycloak access tokens, refresh tokens, ID tokens, authorization codes,
   and PKCE material must never be readable by browser JavaScript or stored in browser local/session
   storage.
3. The browser receives only an opaque application-session handle. Authentication tokens remain in
   a server-side session owner selected by the solution.
4. Session identifiers rotate after authentication, privilege or assurance change, account switch,
   tenant switch where policy requires it, recovery, and provider linking.
5. Access tokens are short-lived and exact-audience restricted. Refresh is server-owned, serialized,
   rotation-aware, revocation-aware, and fail closed.
6. A downstream 401 caused by invalid or rotated signing authority must converge on one
   unauthenticated recovery state rather than remain an apparently active session.

### 6.2 Identity, registration, and provider linking

1. Authentication establishes a global identity. It does not create tenant authority, an
   Employment Relationship, payment authority, or professional authority.
2. A new authenticated identity creates or resolves a provisional WAOOAW user, then enters
   onboarding when required profile, legal, or tenant state is incomplete.
3. Returning users and new users use the same provider launch and callback.
4. Provider identities bind by exact issuer and subject. Verified email may support a protected
   recovery decision but cannot silently merge identities.
5. Adding or removing a provider requires an authenticated WAOOAW session, fresh authentication,
   anti-CSRF protection, proof of the new provider, and preservation of at least one usable login
   method.
6. Apple private-relay email and provider email changes must not create a new identity.
7. Email credentials, magic links, passkeys, OTP, recovery, and abuse controls are owned by the
   selected identity authority, not implemented independently by the Web application.

### 6.3 Multi-tenant authorization

1. Global user identity, customer account, tenant membership, role, active tenant context, and
   institutional identity are separate records and authorities.
2. Business Platform resolves current membership from validated identity for every protected
   operation. Browser tenant input and JWT tenant claims are not sufficient authority.
3. Switching tenant changes only an authorized application context; it does not invoke a social
   provider or create another identity session.
4. APIs validate exact issuer, signature, lifetime, audience, authorized party, assurance, and
   current membership before effects.
5. UI state, provider claims, callback parameters, return targets, and application-session contents
   never grant tenant or business authority.
6. Membership removal, account disablement, revocation, and Emergency Stop fail closed at every
   enabled receiver within the accepted consistency contract.

### 6.4 Logout, switching, and recovery

1. `Sign out of WAOOAW` invalidates the local application session first and succeeds without an
   external provider round trip.
2. `Sign out everywhere` invalidates all WAOOAW application sessions and performs standardized
   Keycloak RP-initiated logout as a separately observable step.
3. WAOOAW does not claim to terminate unrelated Google, Apple, or Facebook sessions.
4. `Use another account` explicitly ends the WAOOAW and Keycloak sessions before launching a new
   authorization request. Provider account selection is requested only for this command or a
   security recovery, not for every normal login.
5. Logout, refresh, callback, revoke, and switch races converge deterministically on the most
   restrictive state.
6. Expired, revoked, unknown, legacy, deployment-invalidated, and provider-cancelled sessions
   produce typed recoverable outcomes without loops or generic fatal screens.

### 6.5 Environment continuity and operations

1. Public web and identity origins are stable before provider activation.
2. Identity signing keys, realm configuration, provider links, and test identities are durable for
   any environment expected to support repeatable login testing.
3. Application sessions may be environment-bounded and disposable only when deployment behavior is
   explicit and the customer receives a clean forced reauthentication.
4. Provider secrets remain in the accepted secret owner and never enter source, logs, traces,
   screenshots, test evidence, or browser responses.
5. Authentication availability, callback failure, provider rejection, refresh rejection, account
   collision, session invalidation, onboarding transition, logout, and tenant-switch outcomes emit
   privacy-safe structured telemetry with correlation.
6. SLOs, alert ownership, rollback, break-glass, provider-disable, key-rotation, mail continuity,
   data retention, deletion, and incident response are explicit.

## 7. Required Provider Contract

| Provider | Required behavior |
|---|---|
| Google | OIDC broker; stable subject; exact callback; verified email treated as an attribute; normal SSO by default; account picker only for explicit switch/recovery. |
| Apple | OIDC broker; stable subject as identity; private relay and one-time name delivery handled; client secret rotation and callback ownership explicit. |
| Facebook | Brokered login separated from WhatsApp/DMA business authorization; basic identity scopes only; exact callback and app-mode evidence required. |
| Email | Identity-authority-owned passwordless, passkey, or password flow with verification, recovery, enumeration resistance, rate limiting, and MFA policy. |

The solution must define provider-independent application behavior. A provider-specific failure may
disable that provider but must not corrupt another provider or an existing WAOOAW session.

## 8. Managed CIAM Decision Gate

The target solution remains compatible with durable Keycloak unless separately superseded. The
Chief Solution Architect must provide a quantified decision record comparing durable Keycloak with
at least one managed CIAM class across:

1. Google, Apple, Facebook, Email, passkey, MFA, enterprise SSO, and account-linking support;
2. tenant/organization support without making the vendor tenant model authoritative;
3. data residency, export, deletion, audit, key ownership, DPDPA obligations, and vendor exit;
4. availability, incident ownership, upgrade burden, operational staffing, and recovery;
5. Demo, UAT, Production, monthly active user, SMS/email, enterprise connection, and support cost;
6. migration complexity and rollback; and
7. constitutional governance and evidence requirements.

No vendor replacement proceeds without Founder acceptance and any required Enterprise Architecture,
Data, Security, procurement, and legal decisions.

## 9. Required Outputs

1. `work-contracts/WC-122-authentication-authorization-simplification.md`
2. `work-contracts/WC-122-requirements.yaml`
3. `architecture/reference/components/authentication-authorization-simplification-solution-contract.md`
4. an implementation impact manifest produced by a later authorized implementation Work Contract;
5. ADR amendment proposal only if the accepted solution conflicts with ADR-003, ADR-008, or ADR-017;
6. provider-console and environment prerequisite matrix;
7. migration and rollback plan;
8. acceptance and negative-test matrix; and
9. author-review evidence and Founder handoff.

Items 4 through 8 may be embedded in the solution contract when complete.

### 9.1 Canonical Requirement Index

| Requirement | Required outcome |
|---|---|
| WC122-R001 | One identity authority, one browser application-session authority, and explicit authorization owners. |
| WC122-R002 | Browser receives only an opaque secure session handle; provider and OIDC tokens remain server-side. |
| WC122-R003 | Identity uses exact issuer and subject; provider linking never silently relies on matching email. |
| WC122-R004 | Login and registration use one authentication ceremony and deterministic post-authentication routing. |
| WC122-R005 | Global identity, profile, tenant membership, role, active tenant, and institutional identity remain separate. |
| WC122-R006 | Logout, global logout, account switch, tenant switch, and revocation are distinct deterministic commands. |
| WC122-R007 | Invalid, legacy, revoked, or deployment-invalidated sessions converge on recoverable unauthenticated state. |
| WC122-R008 | Google, Apple, Facebook, and Email expose provider-independent application behavior. |
| WC122-R009 | Every protected API operation validates exact token and current authorization evidence. |
| WC122-R010 | Identity configuration, keys, links, and test users are durable wherever repeatable authentication is claimed. |
| WC122-R011 | Authentication and authorization transitions emit privacy-safe typed telemetry and recovery actions. |
| WC122-R012 | Migration invalidates legacy sessions once and never leaves mixed session authority. |
| WC122-R013 | Durable Keycloak and managed CIAM receive a quantified, governable decision comparison. |
| WC122-R014 | Accepted-contract conflicts, downstream decisions, prohibited designs, and gates are explicit. |
| WC122-R015 | Acceptance covers protocol, browser, identity, onboarding, sessions, tenants, providers, accessibility, and operations. |
| WC122-R016 | The exact-head specification branch passes author review while implementation remains blocked. |

## 10. Acceptance Oracles

The solution is implementation-ready only when:

1. every state and transition for login, onboarding, callback, refresh, logout, account switch,
   tenant switch, provider link/unlink, revocation, and recovery has one owner;
2. no access, refresh, or ID token is carried in browser-readable or browser-persisted state;
3. exactly one application-session authority remains after migration;
4. account identity and tenant authorization are demonstrably separate;
5. direct and brokered provider flows share one post-authentication router;
6. normal login preserves SSO while explicit account switch removes stale Keycloak authority;
7. local logout succeeds during Keycloak/provider outage;
8. provider collision cannot silently merge or duplicate a customer;
9. stale legacy cookies, signing-key rotation, deployment, and mixed-version rollout fail closed;
10. cross-tenant, cross-account, open-redirect, CSRF, replay, mix-up, fixation, token theft, callback
    injection, and race tests have exact expected outcomes;
11. accessibility, localization, mobile/desktop, cancellation, back-button, multi-tab, and
    interrupted-network journeys are specified;
12. real-provider Demo qualification is distinct from synthetic contract tests; and
13. rollback cannot reactivate an invalidated legacy session authority.

## 11. Delivery Stages

| Stage | Output | Gate |
|---|---|---|
| CSA-01 | Current-state authority and data-flow inventory | Every session, token, identity, membership, cookie, store, callback, and revocation owner is enumerated. |
| CSA-02 | Target decisions and state machines | AUTHZ-SD-01 through AUTHZ-SD-10 are closed. |
| CSA-03 | Provider and multi-tenant contracts | Google, Apple, Facebook, Email, linking, tenant selection, and step-up are complete. |
| CSA-04 | Persistence, security, privacy, and operations | Session/key continuity, telemetry, SLO, retention, incident, and rollback are explicit. |
| CSA-05 | Migration and compatibility | Legacy NextAuth/BP session behavior has one bounded cutover and no dual-authority steady state. |
| CSA-06 | Acceptance package | Requirement ledger and executable-oracle plan are complete. |
| CSA-07 | Author review | Every finding is fixed or recorded as a Founder decision blocker. |
| CSA-08 | Founder handoff | Candidate is submitted without implementation, activation, approval, or self-merge. |

## 12. Implementation Gate

Acceptance of WC-122 or its solution contract does not authorize implementation.

Before any runnable code, generated artifact, dependency, migration, or build artifact is created:

1. the Founder must accept the exact solution version;
2. required ADR amendments and specialist dispositions must be accepted;
3. a separate implementation Work Contract must freeze scope, files, sequence, tests, rollout, and
   rollback;
4. the current implementation session must receive explicit Founder authorization; and
5. provider, cloud, deployment, traffic, activation, approval, and merge permissions remain
   separate.

## 13. Definition of Done

WC-122 specification work is complete when:

1. the three required repository artifacts exist and cross-reference exact requirements;
2. every mandatory solution decision and acceptance oracle is explicit;
3. conflicts with existing accepted contracts are identified rather than silently overridden;
4. the candidate contains no implementation or environment mutation;
5. repository documentation validation passes;
6. author review records no unresolved correctness gap;
7. the exact-head branch is pushed for Founder and Chief Solution Architect consideration; and
8. implementation remains blocked.

## 14. Author Review

| Finding | Severity | Resolution |
|---|---|---|
| AR-01 - Accepted contracts were referenced without an explicit supersession/conflict ledger. | High | CSA-AUTH-001 now identifies each affected accepted clause and the authority required before supersession. |
| AR-02 - The target behavior was not bound to named current OAuth/OIDC standards. | Medium | RFC 9700, RFC 10017, OIDC Core, RP-Initiated Logout, and exact provider requirements are normative inputs. |
| AR-03 - A simplified session model could accidentally reactivate legacy authority during rollback. | High | Migration requires one-way legacy-session invalidation and prohibits mixed-authority steady state or automatic rollback to legacy sessions. |
| AR-04 - Tenant switching could be mistaken for provider reauthentication or tenant authority. | High | Tenant switching is explicitly application context only and every protected operation revalidates current membership. |
| AR-05 - Managed CIAM could be treated as an implementation shortcut without governance. | Medium | Replacement requires quantified comparison plus separate Founder, EA, Data, Security, procurement, and legal decisions as applicable. |

**Author review result:** PASS after the resolutions above and repository validation. No unresolved
correctness finding remains in the specification package. This author review is not institutional
approval, implementation authorization, provider readiness, or merge authority.
