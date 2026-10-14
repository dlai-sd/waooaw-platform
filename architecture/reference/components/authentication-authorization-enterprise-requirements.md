# Authentication And Authorization Enterprise Requirements

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Enterprise Architect (INST-004) |
| Status | ENTERPRISE REQUIREMENTS COMPLETE — READY FOR CHIEF SOLUTION ARCHITECT |
| Author review | PASS — 2026-10-14 |
| Purpose | Enterprise requirements input for Chief Solution Architect decomposition and Work Contract creation |
| Scope | Customer authentication, application sessions, identity linking, multi-tenant authorization, provider integration, migration, and qualification |
| Source-analysis authority | Founder-authorized temporary implementation-analysis role; read-only source inspection completed before returning to INST-004 |
| Implementation authority | None |
| UI authority | None; this requirements activity must not change UI code, routes, copy, layout, styling, or interaction behavior |
| External mutation authority | None; no provider-console, cloud, DNS, deployment, traffic, or customer-data action is authorized |

## 1. Objective

WAOOAW must provide one predictable customer access model across Google, Apple, Facebook, and Email
without allowing provider identity, browser state, stale token claims, or presentation routes to
become tenant or business authority.

The target must:

1. authenticate a person through an accepted identity authority;
2. maintain one secure WAOOAW application session for the browser;
3. resolve current customer and tenant authority from durable WAOOAW records;
4. authorize every protected action at the owning resource boundary;
5. support zero, one, or multiple tenant memberships without identity duplication;
6. preserve provider-specific security and recovery requirements behind one customer journey;
7. fail closed without leaking account, tenant, provider, or credential information; and
8. migrate from the current implementation without two steady-state session or tenant authorities.

The Chief Solution Architect must translate these requirements into a bounded solution architecture
and a detailed Work Contract. It may not weaken an invariant, silently resolve an architecture
conflict, or treat existing code as the target merely because it is already present.

## 2. Enterprise Capability And Obligation Trace

| Requirement source | Architectural obligation |
|---|---|
| Business Capability 6.1 — Authenticate and Authorize Customers | Authenticate every customer and authorize only constitutionally permitted resources across every channel. |
| Business Capability 6.2 — Isolate Tenant Data | Prevent cross-customer access at every layer, including the database. |
| Business Capability 6.3 — Record Constitutional Evidence | Record permission, authority, and boundary-crossing evidence before consequential success. |
| Business Capability 6.4 — Observe Platform Health and Compliance | Make access failures, security transitions, and constitutional enforcement measurable. |
| AD-004 / C-005 / C-026 | Keep tenant data isolated through database-enforced RLS and an authoritative tenant context. |
| AD-009 / DP-006 | Enforce authentication and authorization at the lowest feasible layer, not by UI or handler convention. |
| AD-010 / C-002 | Emit structured, privacy-safe telemetry for material identity and authorization transitions. |
| C-023 | Do not return consequential success before required evidence exists. |
| C-063 | Collect and retain only identity information necessary for the declared purpose. |
| C-100 | Use exact credentialed origins, methods, and headers; never combine credentials with wildcard CORS. |
| ADR-002 | Define API contracts before endpoint implementation and generate consumers from the accepted contract. |
| ADR-008 | Keep stock Keycloak as the current identity broker unless a separately accepted enterprise decision replaces it. |
| ADR-017 | Keep server-side identity integration in the Web application boundary. |

## 3. Verified Current-Implementation Findings

These findings are source-level observations, not deployed-behavior claims. Tests demonstrate useful
local behavior but do not prove real-provider, cloud, UAT, or Production readiness.

| ID | Verified implementation finding | Enterprise pitfall | Required disposition |
|---|---|---|---|
| F-01 | `web/lib/auth.ts` configures NextAuth `session.strategy = "jwt"` and places Keycloak access, refresh, and ID tokens in the NextAuth token. | Sensitive bearer authority is carried in the browser session cookie rather than referenced by an opaque application-session handle. Cookie compromise has a larger blast radius, revocation is weakly centralized, and token rotation races cannot be coordinated reliably. | Replace with one server-side application-session authority and an opaque browser handle. |
| F-02 | `web/lib/auth.ts` refreshes expired access tokens inside the JWT callback, mutates token state, and purges authentication on broad refresh failure. | Concurrent requests can race refresh-token rotation; failure classes are collapsed into apparent session loss; there is no atomic session-family revocation or durable refresh evidence. | Require single-flight refresh, rotation/reuse handling, typed outcomes, and atomic session-family controls. |
| F-03 | `web/components/auth/ProviderCommands.tsx` maps Google, Facebook, Apple, and Email but permits only available Google and Facebook actions. | Configuration shape suggests four-provider support while customer behavior supports only two. Apple and Email cannot be described as seamless or ready. | Make capability projection truthful and require independent real-provider qualification for every enabled provider. |
| F-04 | `CustomerIdentityJourneyService` uses `GoogleWorkspaceProofAdapter`, supports configured Google/Facebook/Apple aliases, and rejects credential authentication. | A provider-specific adapter name owns a cross-provider boundary, while Email has no equivalent accepted journey. Provider extension and failure isolation are harder to reason about. | Define a provider-neutral verified-identity contract with provider-specific adapters and no provider branch in customer authorization. |
| F-05 | `CustomerMembershipMiddleware` resolves current membership and derives tenant context from durable Business Platform state for adapted customer routes. | This is the desired current-authority pattern, but it is not yet universal. | Preserve and generalize current-membership resolution for every customer-protected operation. |
| F-06 | `TenantIsolationMiddleware` still derives tenant context from the JWT `tenant_id` claim for other protected routes, while `IdentityController` retains claim-based fallback behavior when the customer journey is absent. | Two tenant-authority paths coexist: current durable membership and token-carried tenant/role claims. Revocation and role changes can produce inconsistent authorization and migration ambiguity. | Select one canonical current-membership authority and remove or explicitly isolate every legacy path. |
| F-07 | `IdentityController` can obtain roles from `waooaw_roles` claims in fallback paths, while adapted paths use membership roles. | Business authorization may depend on stale token roles in one path and durable roles in another. | Business and tenant roles must be resolved from current authoritative membership for each protected operation. |
| F-08 | The logout route clears local cookies while redirecting through Keycloak, but local logout, global WAOOAW logout, account switch, provider unlink, and revoke-all are not represented as one complete server-side session command model. | Customer intent, outage behavior, and revocation scope can be ambiguous; browser cleanup is not equivalent to server-side revocation. | Define separate idempotent commands and state transitions for each lifecycle operation. |
| F-09 | Current tests strongly cover JWT rejection, customer membership isolation, forged tenant input, provider readiness, and local logout behavior. | The test base is useful but does not cover a server-side session store, refresh concurrency, session-family revocation, real Apple/Email journeys, multi-membership selection, or a mixed-authority elimination proof. | Retain existing tests and add a target-state acceptance matrix without treating synthetic evidence as provider acceptance. |

## 4. Mandatory Enterprise Invariants

### ER-AUTH-001 — One identity authority

One accepted identity authority owns credential verification, upstream authentication sessions,
provider brokering, MFA, and binding of external identities. WAOOAW Web and Business Platform must
not verify provider credentials, passwords, magic links, passkeys, or OTPs independently.

Stock Keycloak remains the compatible default under ADR-008. Replacing it with managed CIAM requires
an accepted Enterprise Architecture decision, Founder acceptance, and a migration that prevents
duplicate users or simultaneous identity authorities.

### ER-AUTH-002 — Exact identity key

A customer identity is keyed by exact `(issuer, subject)`. Email, phone, display name, provider
access token, tenant, browser cookie, and callback values are attributes or evidence, never the
global identity key.

Email equality must never auto-link or merge accounts.

### ER-AUTH-003 — One application-session authority

The browser must hold only an opaque, integrity-protected application-session handle in a secure
cookie. Provider, Keycloak, access, refresh, and ID tokens must remain in server-side custody.

The accepted solution must designate exactly one persistence owner for application sessions and
must not create an ungoverned database or a second durable customer authority.

### ER-AUTH-004 — Authentication grants no business authority

Successful authentication establishes identity and assurance only. It must not create or imply a
tenant, membership, customer role, payment authority, employment authority, professional authority,
institutional role, or consequential entitlement.

### ER-AUTH-005 — Current membership is authorization input

Every customer-protected operation must authorize against a current membership decision derived from
authoritative WAOOAW state using the validated identity. A bounded server-side projection or cache is
permitted only when its invalidation and revocation propagation satisfy a declared security SLO and
fail closed when freshness cannot be established. Browser input, provider claims, email, and stale
tenant or role claims must not prove current membership.

The active tenant in an application session is a convenience selection only. The owning resource
server must revalidate membership, assurance, resource ownership, action permission, and relevant
constitutional authority before success.

### ER-AUTH-006 — Database isolation remains mandatory

Every tenant-scoped database operation must run under an RLS tenant context derived from the
successfully authorized current membership. Application filtering is defense in depth, not the
primary isolation mechanism.

### ER-AUTH-007 — One ceremony, explicit post-authentication state

Login and registration presentation may use different entry routes, but both must invoke one
authentication ceremony and one post-authentication router. The router must distinguish at least:

- ready customer;
- onboarding required;
- tenant selection required;
- recovery required; and
- terminal authentication failure.

Provider authentication must not silently create a tenant, organization, membership, employment
relationship, payment authority, trial, or other consequential entitlement.

### ER-AUTH-008 — Provider-neutral common journey

Google, Apple, Facebook, and Email must converge on the same normalized identity, application
session, onboarding, tenant, authorization, error, and evidence contracts.

Provider-specific logic is permitted only in the identity-provider adapter and configuration
boundary. The Web client and Business Platform authorization model must not contain provider-specific
customer account semantics.

### ER-AUTH-009 — Distinct session lifecycle commands

Local logout, global WAOOAW logout, use-another-account, tenant switch, revoke-one-session,
revoke-all-sessions, provider link, provider unlink, and security revocation are distinct commands
with explicit scope, idempotency, race behavior, evidence, and customer outcome.

Local logout must complete even when Keycloak or a provider is unavailable. WAOOAW must not claim
that global WAOOAW logout also signed the customer out of Google, Apple, or Facebook.

### ER-AUTH-010 — Fail closed with typed recovery

Validation, provider, refresh, revocation, collision, membership, assurance, and dependency failures
must produce typed server outcomes. No failure may return an apparently authenticated or authorized
state.

Customer messages must be anti-enumerating and must not expose account existence, provider subject,
raw email or phone, tenant identity, membership, token, callback parameter, secret, internal route,
or stack detail.

## 5. Protocol And Provider Requirements

### 5.1 Common OIDC requirements

The accepted solution must:

1. **ER-PROTO-001:** use Authorization Code with PKCE `S256`;
2. **ER-PROTO-002:** validate exact issuer, signature, algorithm, audience, authorized party, state, nonce, code
   verifier, redirect URI, lifetime, authentication time, and required assurance;
3. **ER-PROTO-003:** use exact registered HTTPS redirect and post-logout URIs outside local development;
4. **ER-PROTO-004:** rotate the application-session identifier after authentication, tenant or authority changes,
   step-up, and recovery;
5. **ER-PROTO-005:** keep tokens, authorization codes, PKCE material, and raw callbacks out of browser-readable state,
   logs, traces, exceptions, analytics, and test artifacts;
6. **ER-PROTO-006:** coordinate refresh once per application session and revoke the session family on detected token
   rotation reuse;
7. **ER-PROTO-007:** define bounded JWKS, signing-key, provider-key, and client-secret rollover behavior; and
8. **ER-PROTO-008:** prevent refresh, callback, redirect, logout, and recovery loops.

### 5.2 Google

**ER-PROVIDER-GOOGLE-001:**
Google must use brokered OIDC with `openid profile email`, exact issuer/subject identity, and exact
registered broker callback. Verified email is profile evidence, not an identity key. Normal login
must use ordinary SSO; account selection is reserved for explicit account switch or bounded recovery.

### 5.3 Apple

**ER-PROVIDER-APPLE-001:**
Apple must use exact issuer/subject identity, preserve identity when private-relay email changes,
capture the one-time name response only when supplied and permitted, define Services ID and domain
registration, and assign client-secret signing-key ownership and rotation. Email equality must not
link Apple to another identity.

### 5.4 Facebook

**ER-PROVIDER-FACEBOOK-001:**
Facebook customer login must remain separate from WhatsApp identity and DMA business authorization.
It must request only accepted login scopes, define Development/Live app-mode evidence per
environment, use an exact broker callback, and normalize denial without account disclosure.

### 5.5 Email

**ER-PROVIDER-EMAIL-001:**
The identity authority must own Email authentication. Before implementation, the solution must
select one bounded method:

- passkey and/or magic link; or
- password with verification, recovery, MFA, breached-password checks, throttling, and lockout.

WAOOAW Web must not store or verify passwords, passkeys, OTPs, or magic-link secrets. Start,
completion, resend, and recovery responses must resist account enumeration.

## 6. Multi-Tenant Authorization Requirements

1. **ER-TENANT-001:** A global customer may have zero, one, or multiple tenant memberships.
2. **ER-TENANT-002:** Tenant selection must list only currently authorized memberships.
3. **ER-TENANT-003:** Every selected membership must be revalidated before session context changes.
4. **ER-TENANT-004:** Every customer-protected operation must revalidate current membership and local
   resource/action policy. This requirement does not replace separately accepted workload or internal
   service identity contracts.
5. **ER-TENANT-005:** Removal, suspension, role reduction, security revocation, or tenant closure must take effect
   within a declared bounded interval independent of token lifetime.
6. **ER-TENANT-006:** Sensitive account, provider, membership, payment, hiring, recovery, credential, and authority
   changes require recent step-up authentication.
7. **ER-TENANT-007:** Customer and institutional identities, realms, clients, roles, sessions, and routes must remain
   cryptographically and operationally separated.
8. **ER-TENANT-008:** RLS, tenant transaction context, idempotency, Evidence First, and Emergency Stop enforcement must
   remain independent controls.
9. **ER-TENANT-009:** A denial must not reveal another account, tenant, membership, or resource.
10. **ER-TENANT-010:** Delegated service calls must carry bounded original/delegated authority appropriate to the
    receiving resource owner; a general customer bearer must not become unrestricted service authority.

## 7. Application-Session Requirements

The selected session owner and store must provide:

1. **ER-SESSION-001:** opaque, nonrecoverable browser handles;
2. **ER-SESSION-002:** encryption in transit and at rest;
3. **ER-SESSION-003:** atomic create, rotate, refresh, revoke-one, revoke-family, and revoke-all operations;
4. **ER-SESSION-004:** idle, absolute, assurance, and upstream-token expiry;
5. **ER-SESSION-005:** single-flight refresh and rotation-reuse detection;
6. **ER-SESSION-006:** explicit deployment and schema compatibility;
7. **ER-SESSION-007:** fail-closed outage behavior;
8. **ER-SESSION-008:** environment isolation;
9. **ER-SESSION-009:** bounded retention, cleanup, deletion, backup, RPO, and RTO;
10. **ER-SESSION-010:** privacy-safe indexing and telemetry;
11. **ER-SESSION-011:** multi-tab and concurrent-request consistency; and
12. **ER-SESSION-012:** back-channel or explicit revocation where supported, with bounded-expiry fallback.

No raw token, password, OTP, provider subject, email, phone, callback query, or personal data may
appear in session-store indexes, logs, metrics, traces, or customer-visible errors.

## 8. Evidence, Observability, And Operations

**ER-OBS-001:** The target must record privacy-safe, correlated transitions for:

- authentication start and callback outcome;
- provider class and provider-class failure;
- identity resolve, create, collision, link, unlink, and recovery;
- onboarding state transition;
- application-session create, rotate, refresh, revoke, and expire;
- local and global logout;
- account and tenant switch;
- API authentication rejection;
- authorization denial;
- step-up requirement and result; and
- forced migration or legacy-session invalidation.

**ER-OBS-002:** The solution Work Contract must define SLO, threshold, alert owner, error budget, and runbook for at
least authentication completion, callback errors, session-store availability, refresh failures,
provider failures, membership resolution, authorization latency, revocation propagation, and
cross-tenant denial.

**ER-OBS-003:** Evidence must distinguish synthetic tests, local emulation, provider sandbox/tester evidence, real
Demo accounts, UAT, and Production. One class must never be presented as another.

## 9. Architecture Conflict Requiring Accepted Disposition

Current ADR-003, AD-004, and DP-007 describe JWT `tenant_id` as the sole RLS isolation anchor.
The newer customer path resolves current membership from durable Business Platform state and then
sets tenant context. The implementation currently contains both approaches.

**ER-TENANT-011:** The target enterprise requirement is:

> RLS tenant context must be derived from a successfully authenticated identity and a current,
> authoritative membership decision for the exact operation. A browser-supplied value or stale
> token tenant/role claim is insufficient customer authority.

Before a solution Work Contract authorizes migration or code changes, the Chief Solution Architect
must identify every affected interface and the Chief Enterprise Architect must produce or route the
required accepted ADR-003 amendment. The solution must not silently reinterpret the current ADR.

## 9.1 Component Compatibility And Impact Containment

The authentication and authorization simplification is a customer access-boundary change, not a
license to redesign unrelated service responsibilities. The Chief Solution Architect must preserve
the following boundaries:

| Component or boundary | Required compatibility protection |
|---|---|
| Web Application | May act as the BFF and application-session owner selected by the accepted solution. This requirements activity authorizes no UI change. A future Work Contract must separately identify and authorize any customer-visible route, copy, layout, styling, or interaction change. |
| Business Platform | Remains the canonical customer membership and BP authorization owner. Membership freshness may use a bounded server-side projection, but provider calls and browser claims must not enter the authorization hot path. Existing public API compatibility must be preserved or migrated through accepted versioned contracts and regenerated clients. |
| Constitutional Engine | No REST exposure, identity-provider integration, browser-session ownership, or change to its authority/evidence responsibilities is permitted. Authentication work must not weaken Evidence First, Emergency Stop, or existing gRPC contracts. |
| Professional Runtime | Must not become a customer identity, browser-session, or membership store. It receives only bounded authority required for its resource operations. PAAS latency and Emergency Stop behavior must not gain an authentication-provider or membership-database dependency. |
| AI Runtime | Must remain internal to Professional Runtime and unaware of customer credentials, provider tokens, browser sessions, or raw customer identity. |
| Billing Engine | Must remain internal, hold no customer login credentials or provider tokens, and receive only the bounded account/tenant authority required by its accepted BP-mediated contracts. |
| Phone/WhatsApp identity | ADR-023 remains a separate channel identity contract. WhatsApp identity must not be silently converted into a Keycloak or browser session; any account link requires the accepted proof and linking ceremony. |
| External-platform OAuth vault | Agent/tool provider authorization is not customer login. Its token custody and authorization contracts remain separate from the customer application-session store. |
| Internal service and workload identity | Existing accepted machine-identity, audience, tenant-scope, and delegation contracts remain in force. Customer membership requirements must not be applied mechanically to service accounts or workload calls. |
| Customer and institutional identity | Existing cryptographic, realm, client, route, and role separation remains mandatory; no translation or shared session authority is introduced. |

The solution must also satisfy these cross-component safeguards:

1. **ER-COMPAT-001:** No provider network call may be added to a normal customer API authorization,
   PAAS, Emergency Stop, billing, evidence, or inference hot path.
2. **ER-COMPAT-002:** No customer application-session dependency may be introduced into CE, PR, AIR,
   WBE, or another internal service that does not own browser interaction.
3. **ER-COMPAT-003:** Membership resolution and revocation must have measured latency, availability,
   freshness, cache-invalidation, and fail-closed objectives before migration.
4. **ER-COMPAT-004:** Public and internal API changes must be versioned, spec-first, consumer-mapped,
   and migrated without an unbounded flag day.
5. **ER-COMPAT-005:** Existing RLS, workload identity, mTLS, idempotency, evidence, Emergency Stop,
   and service authorization controls must remain independently effective throughout migration.
6. **ER-COMPAT-006:** The same customer request must not be authorized once by membership and again
   by a conflicting token-carried tenant or role claim.
7. **ER-COMPAT-007:** Load, concurrency, outage, and rollback tests must prove that the new session
   and membership dependencies do not violate accepted component latency or availability budgets.
8. **ER-COMPAT-008:** No UI implementation change is in scope until a future Work Contract names the
   exact experience change and receives separate authorization.

## 10. Migration And Rollback Requirements

The Chief Solution Architect must produce a migration that:

1. **ER-MIG-001:** freezes the accepted target contracts and session-persistence owner;
2. **ER-MIG-002:** inventories every session, token, tenant, role, membership, logout, provider, and identity-link
   authority in Web, Business Platform, Keycloak, and receiving services;
3. **ER-MIG-003:** establishes stable origins, TLS, provider callbacks, mail, secrets, and durable identity
   continuity before activation;
4. **ER-MIG-004:** introduces the server-side session path behind a disabled environment control;
5. **ER-MIG-005:** qualifies callback, refresh, logout, switching, onboarding, linking, tenant, revocation, outage,
   and race behavior before activation;
6. **ER-MIG-006:** recognizes legacy sessions only to reject or invalidate them;
7. **ER-MIG-007:** activates the new path in Demo with one announced forced sign-out;
8. **ER-MIG-008:** removes legacy session creation, claim-based customer role authority, and routine Business
   Platform session orchestration;
9. **ER-MIG-009:** proves that no legacy or mixed authority remains accepted; and
10. **ER-MIG-010:** promotes the same immutable image and bounded configuration through later environments.

Rollback may stop new authentication starts or restore a prior deployable only when it cannot
reactivate invalidated legacy sessions, accept mixed session formats, or restore stale tenant/role
authority. Any rollback that restores a prohibited authority model requires a new Founder decision.

## 11. Mandatory Acceptance Evidence

The future solution Work Contract must include executable evidence for:

| Area | Minimum evidence |
|---|---|
| Protocol | PKCE, state, nonce, issuer, audience, authorized party, exact redirect, JWKS rotation, mix-up, replay, algorithm, and expiry tests |
| Browser | No browser-readable tokens; secure cookie; CSRF; cache/history; multi-tab; back-button; fixation tests |
| Identity | New/returning identity; issuer/subject collision; verified-email change; Apple relay; link/unlink concurrency |
| Providers | Separate real Demo qualification for Google, Apple, Facebook, and selected Email method |
| Onboarding | New user; incomplete profile; legal acceptance; zero/one/many memberships; interrupted resume |
| Session | Rotation; idle/absolute expiry; refresh concurrency; reuse; revoke races; deploy/schema compatibility |
| Logout | Outage-safe local logout; global logout; Keycloak outage; stale cookie; history/cache restoration |
| Account switch | Same provider same/different user; cross-provider; cancellation; provider outage |
| Tenant | Current membership; inactive/removed role; forged tenant input; concurrent switch; cross-tenant denial |
| Authorization | Issuer/audience/authorized-party/assurance denial; resource ownership; RLS; step-up |
| Privacy | Anti-enumeration; log/trace redaction; retention/deletion; no secret or token artifacts |
| Operations | SLO alerts; key/secret rotation; backup/restore; rollback; revocation and incident drills |
| Migration | Legacy sessions only invalidated; no legacy creation; no mixed session or tenant authority accepted |
| Accessibility | Keyboard, focus, screen reader, zoom, reduced motion, locale, RTL, mobile, and desktop |

Existing authentication and tenant-isolation tests must remain passing unless an accepted contract
explicitly replaces their behavior. Changed behavior requires replacement tests that prove the new
invariant rather than simply deleting the old assertion.

## 12. Chief Solution Architect Deliverables

The Chief Solution Architect package must contain:

1. a component and trust-boundary model;
2. responsibility and data-ownership matrices;
3. canonical identity, membership, application-session, and revocation models;
4. authentication, onboarding, refresh, logout, account-switch, tenant-switch, link, unlink, and
   recovery state machines;
5. exact public and internal API changes, with OpenAPI owners;
6. session-store option analysis and selected owner;
7. provider adapter and readiness contracts;
8. threat, abuse, privacy, failure-mode, and outage analysis;
9. a complete source/component impact inventory;
10. legacy-authority removal and migration sequence;
11. rollback constraints;
12. a requirement-to-design-to-test traceability matrix;
13. operational SLOs and evidence model;
14. dependency, cost, reversibility, and lock-in analysis; and
15. a detailed Work Contract that separates implementation, provider activation, cloud mutation,
    deployment, real-account acceptance, UAT, and Production authority.

## 13. Work Contract Creation Rules

The Work Contract created from this specification must:

1. use stable requirement IDs from this document;
2. identify exact files/components only after the solution impact analysis;
3. separate architecture conflict resolution from implementation;
4. separate server-side session delivery from provider activation where independent rollback is
   required;
5. define measurable completion evidence for each requirement;
6. identify accepted inputs and owners for Security, Data, Product, Platform, and Operations concerns
   without invoking those offices unless the Founder requests them;
7. prohibit cloud, provider-console, DNS, traffic, and Production actions unless separately authorized;
8. preserve immutable evidence and author review; and
9. stop on any missing authority, ownerless material assumption, unresolved ADR conflict, or
   unqualified provider dependency.

## 14. Explicitly Prohibited Target Designs

The solution must not:

1. store provider or Keycloak tokens in a browser-carried JWT session;
2. use email or phone as the global identity key;
3. link accounts solely because email values match;
4. treat authentication as tenant or role authority;
5. accept browser or stale token tenant/role claims as sufficient customer authorization;
6. maintain concurrent legacy and replacement application-session authorities;
7. force provider account selection on every normal login;
8. require a provider round trip for local WAOOAW logout;
9. require social reauthentication for an ordinary authorized tenant switch;
10. place provider-specific customer account behavior in the Web client;
11. allow one provider failure to corrupt another provider or an existing session;
12. bypass RLS or derive RLS context from unverified caller input;
13. merge customer and institutional identity paths; or
14. claim provider, deployment, security, UAT, or Production readiness from specification or
    synthetic evidence alone.

## 15. Stops And Open Decisions

Solution decomposition must stop until the named owner resolves:

| Decision | Required owner/disposition |
|---|---|
| ADR-003 tenant-anchor conflict | Chief Enterprise Architect amendment and Founder acceptance where required |
| Server-side application-session persistence owner | Chief Solution Architect option analysis; accepted architecture decision before implementation |
| Email authentication method | Product constraints plus Solution/Security design; explicit accepted method before implementation |
| Durable Keycloak versus managed CIAM | Scored enterprise comparison and Founder decision if replacing ADR-008 |
| Session retention, deletion, backup, RPO, and RTO | Named data/operations ownership in the solution package |
| Provider activation and real-account testing | Separate environment-specific Founder authority |
| Production activation or customer traffic | Separate Founder authority after accepted qualification evidence |

## 16. Handoff Boundary

This document authorizes architecture and planning only. It does not approve a solution design,
create an implementation Work Contract, authorize source changes, accept a provider, approve an ADR
amendment, mutate infrastructure, deploy software, enable traffic, or establish Production readiness.

The receiving Chief Solution Architect may decompose these requirements but may not change their
customer outcome, capability ownership, constitutional obligations, authority boundaries, or
acceptance semantics without routing the conflict back to the Chief Enterprise Architect and Founder.

## 17. Author Review

The Chief Enterprise Architect re-read this complete specification against the Founder-authorized
scope, verified source findings, capability and obligation trace, architecture authority, receiving
office needs, migration safety, failure handling, reversibility, and acceptance evidence.

Two review rounds identified and repaired the following defects:

1. mandatory protocol, provider, tenant, session, observability, and migration requirements initially
   lacked stable trace identifiers; stable IDs now support an exact requirement-to-design-to-test
   ledger; and
2. customer membership revalidation language could have been misread as applying to internal
   service/workload identities or requiring an unconditional database round trip on every request;
   the scope now permits only freshness-bounded server-side projection and explicitly preserves CE,
   BP, PR, AIR, WBE, WhatsApp, external OAuth, workload identity, RLS, Emergency Stop, API, latency,
   availability, and UI boundaries.

**Result:** PASS. No unresolved author-review finding remains. Open architecture and owner decisions
are explicitly stopped in Section 15 and are not represented as accepted decisions.
