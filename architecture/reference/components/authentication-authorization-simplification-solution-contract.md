# Authentication and Authorization Simplification Solution Contract

**Contract ID:** CSA-AUTH-001  
**Work Contract:** WC-122  
**Version:** 1.0.0-candidate.2  
**Owning office:** Chief Solution Architect, Office 05  
**Status:** AUTHOR CANDIDATE FOR CHIEF SOLUTION ARCHITECT AND FOUNDER REVIEW - IMPLEMENTATION BLOCKED  
**Implementation authority:** None  

## 1. Purpose

This contract defines the required target architecture for predictable customer authentication and
multi-tenant authorization across WAOOAW Web, Keycloak, Business Platform, and Google, Apple,
Facebook, and Email identity paths.

It replaces patch-by-patch coordination with three explicit planes:

1. **Identity plane:** one authority authenticates credentials and binds external identities.
2. **Application-session plane:** one Web BFF session represents the browser's WAOOAW login.
3. **Authorization plane:** Business Platform and each enabled receiver enforce current tenant,
   membership, assurance, resource, and action authority.

The planes exchange typed evidence but do not share ownership.

## 2. Controlling Invariants

1. Stock Keycloak remains the identity authority unless a separately accepted Enterprise
   Architecture and Founder decision selects managed CIAM.
2. The browser has one opaque WAOOAW application-session cookie. It does not possess provider,
   Keycloak, access, refresh, or ID tokens.
3. Business Platform is not a browser-session authority. It validates API callers, resolves current
   membership, authorizes operations, records security evidence, and may revoke application
   authority through an explicit contract.
4. Identity is exact `(issuer, subject)`. Email, phone, display name, tenant, cookie, callback,
   provider access token, and organization role are not identity keys.
5. Authentication alone grants no tenant, commercial, employment, payment, professional, or
   institutional authority.
6. Tenant membership is durable application data resolved on every protected operation.
7. Login and registration use one authentication ceremony. Onboarding is a post-authentication
   application state.
8. Local logout, global WAOOAW logout, account switch, tenant switch, provider unlink, and security
   revocation are distinct commands.
9. Every transition is idempotent, race-defined, privacy-safe, and observable.
10. No migration may leave two application-session authorities active as a steady state.

## 3. Normative Standards and Supersession Boundary

### 3.1 Standards

The implementation design must conform to:

1. RFC 9700, OAuth 2.0 Security Best Current Practice;
2. RFC 10017, OAuth 2.0 for Browser-Based Applications;
3. OpenID Connect Core 1.0;
4. OpenID Connect Discovery 1.0;
5. OpenID Connect RP-Initiated Logout 1.0; and
6. the current exact-provider requirements accepted for Google, Apple, Facebook, and Email.

When a provider extension conflicts with the common contract, the most restrictive compatible rule
applies or that provider remains disabled.

### 3.2 Accepted-contract conflict ledger

This candidate does not supersede an accepted contract until the Founder accepts the exact
candidate and any required Enterprise Architecture amendment. The Chief Solution Architect must
close these known conflicts:

| Existing authority | Current clause | Required disposition |
|---|---|---|
| ADR-008 and WC-085 | Stock Keycloak is the accepted broker. | Preserve durable Keycloak by default. Managed CIAM substitution requires an accepted ADR amendment and Founder decision. |
| WC-085 First Slice Defaults | Initial implementation permits one active OWNER workspace and states no persistent-Keycloak change. | Preserve current membership authority, but amend the continuity limitation before claiming repeatable multi-provider environments or multi-membership selection. |
| Identity Session Security Contract | Social login requests account selection after logout. | Narrow forced account selection to explicit account switch and bounded recovery; normal login uses ordinary SSO. |
| WC-105 | Login and Registration are separate dedicated entry experiences. | They may remain separate presentation routes, but they invoke one authentication ceremony and one post-authentication router. |
| WC-105 and WC-119 | Typed denial and stale-session recovery trigger custom retry/logout behavior. | Preserve as interim compatibility only; replacement sessions converge through the canonical state machines in Section 7. |
| WC-034 | Keycloak is the only web credential authority and BP owns membership/authorization. | Preserve. The Web BFF owns only the application session and token custody, not credentials or tenant authority. |
| ADR-017 | Web Application owns server-side identity integration. | Preserve while replacing browser-carried token custody with an accepted server-side session owner. |
| Demo public-domain delivery | Stable origins and callbacks are environment prerequisites. | Preserve as an entry gate; domain publication does not establish provider or authentication readiness. |

No implementation Work Contract may proceed while a conflict above lacks an accepted disposition.

## 4. Target Component Model

```text
+---------------- Google / Apple / Facebook / Email ----------------+
|                                                                   |
+------------------------------+------------------------------------+
                               |
                               v
                 +-----------------------------+
                 | Identity Authority          |
                 | durable Keycloak by default |
                 | credentials, broker links,  |
                 | MFA, SSO, auth session      |
                 +-------------+---------------+
                               |
                    OIDC code + PKCE
                               |
                               v
                 +-----------------------------+
                 | WAOOAW Web BFF              |
                 | callback, token custody,    |
                 | opaque application session, |
                 | post-auth routing           |
                 +-------------+---------------+
                               |
                  audience-bound API token
                               |
                               v
                 +-----------------------------+
                 | Business Platform           |
                 | global user/profile,        |
                 | onboarding, current tenant  |
                 | membership, authorization,  |
                 | security evidence           |
                 +-------------+---------------+
                               |
                  bounded service delegation
                               |
                               v
                 +-----------------------------+
                 | CE / PR / WBE / AIR /       |
                 | domain owners enforce own   |
                 | resource and action policy  |
                 +-----------------------------+
```

## 5. Responsibility Matrix

| Responsibility | Identity authority | Web BFF | Business Platform | Other resource owners |
|---|---:|---:|---:|---:|
| Verify provider/email credential | Own | No | No | No |
| Bind external provider identity | Own | Orchestrate UI only | Record normalized reference where approved | No |
| Maintain upstream SSO | Own | No | No | No |
| Exchange authorization code | Issue/validate | Own | No | No |
| Hold access/refresh/ID tokens | Issue | Own server-side custody | Receive only exact bounded access token | Receive only accepted delegated/original authority |
| Browser application session | No | Own | No | No |
| Global customer profile | No | Present | Own | No |
| Onboarding status | No | Route/present | Own | No |
| Tenant and membership truth | No | Present selected context | Own canonical customer membership | Enforce accepted local/resource membership contract |
| Active tenant context | No | Own session selection after BP authorization | Validate every use | Validate every use |
| Business authorization | No | Never final | Own BP operations | Own local operations |
| Security evidence | IdP events | Session events | Authorization and customer identity events | Local effect events |

## 6. Canonical Data Model

### 6.1 Global user

`GlobalUser` represents one WAOOAW customer person and contains no tenant authority.

Minimum logical fields:

- opaque `user_id`;
- lifecycle state;
- minimum profile and locale;
- legal acceptance references;
- created/updated timestamps; and
- deletion/retention state.

### 6.2 External identity

`ExternalIdentity` binds:

- exact issuer;
- exact subject;
- provider class;
- global user ID;
- verification/provenance class;
- linked, last-authenticated, and retired timestamps; and
- privacy-safe recovery state.

The unique key is `(issuer, subject)`. Provider email is mutable profile evidence, not the key.

### 6.3 Tenant membership

`TenantMembership` binds a global user/account to one tenant with current role, state, and policy
evidence. A user may hold zero, one, or multiple memberships. The identity authority does not mint
or own these memberships.

### 6.4 Application session

The server-side `ApplicationSession` contains:

- opaque session ID;
- global user/account reference;
- exact identity issuer and subject reference;
- current assurance and authentication time;
- optional active tenant selected from authorized memberships;
- upstream IdP session reference required for logout;
- server-held encrypted token material or reference;
- created, idle, absolute-expiry, rotation, and revocation state;
- deployment/schema compatibility version; and
- privacy-safe device/risk class when separately approved.

The browser cookie contains only an opaque, integrity-protected session handle and required cookie
metadata.

## 7. Canonical State Machines

### 7.1 Authentication

```text
ANONYMOUS
  -> AUTH_STARTING
  -> PROVIDER_REDIRECTED
  -> CALLBACK_VALIDATING
  -> IDENTITY_RESOLVED
  -> SESSION_ESTABLISHED
  -> ROUTING
       -> READY
       -> ONBOARDING_REQUIRED
       -> TENANT_SELECTION_REQUIRED
       -> RECOVERY_REQUIRED
```

Any validation, provider, collision, revocation, or dependency failure transitions to one typed
recoverable or terminal state. No failure returns an apparently authenticated session.

### 7.2 Onboarding

```text
NOT_STARTED
  -> PROFILE_REQUIRED
  -> LEGAL_ACCEPTANCE_REQUIRED
  -> TENANT_DECISION_REQUIRED
  -> READY
```

Provider authentication may create or resolve a provisional global user but does not silently
create an organization, employment relationship, payment authority, or consequential entitlement.

### 7.3 Local logout

```text
ACTIVE
  -> LOCAL_REVOCATION_COMMITTED
  -> COOKIE_EXPIRED
  -> ANONYMOUS
```

The result is independent of Keycloak or provider availability.

### 7.4 Global WAOOAW logout

```text
ACTIVE
  -> ALL_APPLICATION_SESSIONS_REVOKED
  -> LOCAL_COOKIE_EXPIRED
  -> KEYCLOAK_RP_LOGOUT_REQUESTED
  -> ANONYMOUS | ANONYMOUS_WITH_UPSTREAM_LOGOUT_WARNING
```

WAOOAW never claims that Google, Apple, or Facebook itself was signed out.

### 7.5 Use another account

```text
ACTIVE_OR_CONFLICTED
  -> LOCAL_SESSION_REVOKED
  -> KEYCLOAK_SESSION_ENDED
  -> FRESH_AUTHORIZATION
  -> PROVIDER_ACCOUNT_SELECTION
  -> NEW_APPLICATION_SESSION
```

Normal login does not force provider account selection. Explicit switching does.

### 7.6 Tenant switch

```text
ACTIVE_SESSION
  -> MEMBERSHIP_LIST_AUTHORIZED
  -> TARGET_MEMBERSHIP_REVALIDATED
  -> SESSION_CONTEXT_ROTATED
  -> TARGET_TENANT_ACTIVE
```

No provider redirect occurs unless current assurance is insufficient for the requested operation.

## 8. OIDC and Token Contract

1. Authorization Code with PKCE `S256` is mandatory.
2. Callback processing validates exact issuer, state, nonce, code verifier, redirect URI, client,
   signature, time, and required provider evidence.
3. Redirect and post-logout URIs are exact registered HTTPS values outside local development.
4. Access tokens are audience-restricted to their resource server and contain only required claims.
5. Refresh tokens never enter browser-visible state, logs, traces, exceptions, or test artifacts.
6. Refresh is single-flight per session. Rotation or reuse detection revokes the session family.
7. Token/JWKS/key rollover has overlap, cache, retry, and forced-reauthentication behavior.
8. An API 401 invalidates or revalidates the application session once; it cannot create a refresh
   loop.
9. Web callback completion rotates the application-session identifier before authenticated content
   is returned.
10. Back-channel or explicit revocation events invalidate affected application sessions when
    supported; otherwise bounded expiry and current-membership checks remain mandatory.

## 9. Provider Contract

### 9.1 Google

- use brokered OIDC with `openid profile email`;
- key identity by Google issuer and `sub`;
- require exact registered Keycloak broker callback;
- use normal SSO for ordinary login;
- apply `prompt=select_account` only to explicit account switch or bounded recovery;
- treat verified email as an attribute, not an identity key; and
- provider cancellation returns to a clean unauthenticated entry state.

### 9.2 Apple

- key identity by Apple issuer and `sub`;
- preserve identity when private-relay email changes;
- capture the one-time name response only when present and permitted;
- define Apple client-secret signing-key ownership and rotation;
- use exact Services ID/domain/callback registration; and
- do not infer provider linking from email equality.

### 9.3 Facebook

- keep customer login separate from WhatsApp and DMA business authorization;
- request only accepted login scopes;
- key identity by broker issuer and subject;
- define Development/Live app-mode and tester evidence by environment;
- use exact broker callback and stable domains; and
- normalize provider denial without disclosing account existence.

### 9.4 Email

The identity authority owns the email mechanism. The final solution must select and specify:

- passkey and/or magic-link as the preferred passwordless path; or
- password plus verification, recovery, MFA, breached-password, throttling, and lockout controls.

Email start, completion, recovery, and resend responses are anti-enumerating. WAOOAW Web does not
store or verify passwords or OTPs.

## 10. Linking and Collision Resolution

1. A user starts linking only from an active WAOOAW session.
2. Linking requires fresh authentication of the current identity and proof of the new identity.
3. If the new issuer/subject is already linked elsewhere, the operation stops in a non-enumerating
   recovery state. It does not merge or create another user.
4. Email equality alone never links accounts.
5. Unlinking requires fresh authentication and preserves at least one usable authentication method.
6. Concurrent link/unlink operations serialize on both identities and the global user.
7. Every outcome is idempotent and emits privacy-safe security evidence.
8. Administrative recovery requires a separately approved, dual-controlled contract.

## 11. Authorization and Multi-Tenancy

1. Business Platform and each enabled resource owner validate exact token issuer, signature,
   lifetime, audience, authorized party, assurance, and accepted algorithm.
2. Current membership is resolved from authoritative storage using validated identity. Client
   tenant input is never proof.
3. The active tenant in the application session is a convenience context only. Every protected
   operation revalidates membership and local resource/action policy.
4. Tenant selection and role changes rotate the application session where risk policy requires it.
5. Step-up authentication is required for sensitive account, provider, membership, payment,
   hiring, recovery, credential, and consequential authority changes.
6. Customer and institutional identities remain isolated. No role or token is silently translated
   between them.
7. RLS, tenant transaction context, idempotency, evidence-first behavior, and Emergency Stop remain
   independently enforced.
8. Authorization denial is typed, privacy-safe, and does not disclose another tenant or account.

## 12. Session Persistence and Continuity

The Chief Solution Architect must select one existing or explicitly approved persistence owner for
server-side Web sessions. The choice must not create an ungoverned database or make browser state
authoritative.

Required properties:

1. encryption at rest and in transit;
2. hashed or otherwise nonrecoverable browser session handles;
3. atomic rotate, revoke-one, revoke-family, and revoke-all;
4. idle and absolute expiry;
5. schema/version compatibility during rollout;
6. bounded cleanup and retention;
7. fail-closed outage behavior;
8. environment isolation;
9. backup/RPO/RTO classification; and
10. no raw token or personal data in indexes, logs, metrics, or traces.

Keycloak realm configuration, signing keys, provider links, and test identities must be durable in
every environment used for repeatable login testing. If Demo or UAT intentionally resets
application data, identity continuity must be independently preserved or the environment must
truthfully declare and enforce a complete forced-session/user reset.

## 13. Error and Recovery Contract

Minimum typed outcomes:

- `AUTHENTICATION_CANCELLED`
- `AUTHENTICATION_PROVIDER_UNAVAILABLE`
- `AUTHENTICATION_CALLBACK_INVALID`
- `AUTHENTICATION_SESSION_EXPIRED`
- `AUTHENTICATION_SESSION_REVOKED`
- `AUTHENTICATION_LEGACY_SESSION`
- `AUTHENTICATION_ACCOUNT_COLLISION`
- `AUTHENTICATION_STEP_UP_REQUIRED`
- `ONBOARDING_REQUIRED`
- `TENANT_SELECTION_REQUIRED`
- `TENANT_MEMBERSHIP_REQUIRED`
- `TENANT_MEMBERSHIP_INACTIVE`
- `IDENTITY_LINK_REAUTH_REQUIRED`
- `IDENTITY_DEPENDENCY_UNAVAILABLE`

Customer messages do not expose provider subject, email existence, account existence, tenant,
membership, token, callback parameter, internal route, or stack detail. Every server outcome has a
privacy-safe correlation ID and one deterministic customer action.

## 14. Observability and Operations

Required structured transitions:

- authentication start and callback outcome;
- provider selected and provider-class failure;
- identity resolve/create/collision;
- onboarding state transition;
- application session create/rotate/refresh/revoke/expire;
- Keycloak RP logout request/outcome;
- account switch and tenant switch;
- provider link/unlink;
- API authentication rejection class;
- authorization denial class; and
- forced migration/logout.

Events contain no authorization code, token, PKCE material, raw cookie, password, OTP, provider
subject, raw email/phone, tenant ID, callback query, or unbounded user agent.

The implementation contract must define SLOs for authentication completion, callback errors,
session-store availability, refresh failures, provider failures, and authorization latency, with
alert owner, threshold, error budget, and runbook.

## 15. Migration and Rollback

### 15.1 Required sequence

1. Freeze the accepted target contract and persistence owner.
2. Establish stable public origins, TLS, provider callbacks, mail, secrets, and durable Keycloak
   continuity.
3. Implement the server-side session path behind a disabled environment flag.
4. Validate callback, refresh, logout, switch, onboarding, provider-link, tenant, and race behavior.
5. Deploy code that can recognize legacy sessions only to invalidate them.
6. Activate the new path in Demo with one announced forced sign-out.
7. Remove legacy session creation and Business Platform routine session orchestration.
8. Prove no legacy authority is accepted.
9. qualify UAT and Production from the same immutable image and environment configuration.

### 15.2 Rollback

Rollback may disable new authentication starts and restore the prior deployable only if it does not
reactivate invalidated legacy sessions or accept mixed session formats. A rollback requiring legacy
authority restoration is a new Founder decision, not an automatic operational step.

## 16. Managed CIAM Alternative

Before implementation authorization, the Chief Solution Architect must append a scored comparison
of durable Keycloak and managed CIAM using the criteria in WC-122 Section 8. Until accepted
otherwise, durable Keycloak is the compatible target.

Managed CIAM may replace Keycloak only if:

1. provider, email, MFA, linking, enterprise SSO, organization, export, deletion, and audit
   requirements are met;
2. WAOOAW tenant membership remains authoritative in Business Platform;
3. provider and application portability are preserved;
4. data residency, retention, processor, breach, key, and exit obligations are accepted;
5. cost and availability are bounded; and
6. migration and rollback do not create duplicate users or dual identity authority.

## 17. Acceptance Matrix

| Area | Mandatory evidence |
|---|---|
| Protocol | code+PKCE, state, nonce, issuer, audience, azp, JWKS rotation, exact redirect, mix-up and replay tests |
| Browser | no browser-readable tokens; cookie security; CSRF; cache; history; multi-tab; back-button tests |
| Identity | returning/new user, provider collision, verified-email change, Apple relay, link/unlink concurrency |
| Onboarding | new user, incomplete profile, legal acceptance, create/join tenant, interrupted resume |
| Session | fixation, rotate, idle/absolute expiry, refresh rotation, reuse, revoke races, deployment invalidation |
| Logout | local outage-safe logout, global logout, Keycloak outage, stale cookie, history/cache restoration |
| Account switch | same provider/same user, same provider/different user, cross-provider, cancellation, provider outage |
| Tenant | zero/one/many memberships, inactive/removed role, cross-tenant input, concurrent switch |
| Authorization | issuer/audience/azp/assurance denial, current membership, RLS, resource ownership, step-up |
| Providers | real Demo Google, Apple, Facebook, and Email qualification separated from synthetic tests |
| Accessibility | keyboard, focus, screen reader, zoom, reduced motion, locale, RTL, mobile and desktop |
| Operations | structured telemetry, redaction, SLO alerts, key rotation, secret rotation, rollback and incident drill |

## 18. Prohibited Designs

The implementation must not:

1. store Keycloak/provider tokens in a browser-carried JWT session;
2. use email as the global identity key;
3. auto-link identities solely by matching email;
4. treat registration-required as an untyped or generic authentication failure;
5. force provider account selection on every normal login;
6. require a provider round trip for local WAOOAW logout;
7. require social reauthentication for ordinary tenant switching;
8. accept browser/JWT tenant claims as sufficient authorization;
9. preserve concurrent legacy and replacement application-session authorities;
10. create provider-specific customer account logic in the Web client;
11. allow provider failure to corrupt another provider or existing session; or
12. claim implementation, deployment, provider, security, or Production readiness from this
    specification alone.

## 19. Downstream Handoff

The accepted candidate must hand off:

- exact component/file impact to Platform IT Expert;
- session/token/threat controls to Security Architect if the Founder requests that review;
- persistence, retention, migration, RPO/RTO, and deletion to Data Architect if the Founder requests
  that review;
- identity-platform replacement or ADR conflicts to Enterprise Architect;
- customer copy and provider/onboarding behavior to Product Owner;
- cost, SLO, deployment, and recovery to Platform Architecture and Platform IT Expert; and
- provider-console, cloud, deployment, traffic, and activation actions to separately authorized
  execution.

No handoff authorizes another office, implementation, or external mutation by itself.
