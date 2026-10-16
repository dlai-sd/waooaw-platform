# Authentication and Authorization Simplification Solution Contract

**Contract ID:** CSA-AUTH-001
**Work Contract:** WC-122
**Version:** 1.1.0-candidate.10
**Owning office:** Chief Solution Architect, Office 05
**Status:** AUTHOR REVIEW PASS - AUTHZ-GATE-01 RESOLVED - IMPLEMENTATION AUTHORITY REQUIRED
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
11. The validated WAOOAW application principal and an upstream provider identity are distinct:
    Keycloak `(issuer, subject)` authenticates the application principal; Keycloak alone verifies and
    owns an upstream provider `(issuer, subject)` binding. Neither identifier may be substituted for
    the other.

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
| Fundamental Customer Journeys and WC-105 | The later customer-journey baseline makes Login authenticate without creating an account or registration; Register and Trial/Hire are explicit intents. WC-105 remains the accepted modal, provider-control, copy, cancellation, focus, and recovery presentation baseline. | Apply the later journey rule to post-authentication routing while preserving WC-105 presentation. One broker ceremony does not merge Login and Register intent, auto-start onboarding, enable a provider, or authorize new routes, controls, copy, layout, or interaction behavior. |
| WC-034 | Keycloak is the only web credential authority and BP owns membership/authorization. | Preserve. The Web BFF owns only the application session and token custody, not credentials or tenant authority. |
| Identity Security Data Contract | Proposes active sessions in `business.identity_sessions`. | Preserve its event separation, minimisation, revocation-generation, retention, and race requirements. For this candidate, Founder acceptance replaces only that proposed physical session placement with the Web-owned `web_session` objects in Section 12; BP receives no token custody or session-table access. |
| ADR-017 | Web Application owns server-side identity integration. | Preserve while replacing browser-carried token custody with an accepted server-side session owner. |
| ADR-017 and existing NextAuth/Auth.js use | The Web framework and existing OIDC library are adopted integration machinery, not an application-session authority. | Retain the accepted Next.js boundary. Reuse the existing reviewed NextAuth/Auth.js OIDC client hooks only for protocol exchange/validation; build the WAOOAW `web_session` authority and lifecycle primitives because the required generation, rotation, revocation, retention, and restore semantics are application-owned. Any library replacement, major upgrade, browser-token fallback, library database-session authority, or generated schema outside Section 12 requires a new accepted decision. |
| ADR-008 Amendments 3 and 4 | WC-085 retains a read-only BP identity client. Amendment 4 separately accepts the pinned stock-Keycloak Admin REST lifecycle writer for WC-123. | Preserve the WC-085 reader unchanged. Use only the separate `waooaw-bp-identity-lifecycle-writer`, its exact `realm-management/manage-users` role, four-operation adapter surface, private route, operation-bound proof, read-back/compensation, audit, stop, upgrade, and rollback controls in Amendment 4 and Section 10.1. Do not claim endpoint-scoped Keycloak enforcement: the accepted stock role remains realm-wide. |
| Compact capability/container indexes | Capability 6.1 condenses credential authentication under Keycloak and customer authorization under BP; the container index distinguishes the application image set from dependency-manifest members. | Read the condensed map as credential/session/business layers, not as transfer of Web-session or resource-authorization ownership. Bind release evidence to the architecture-indexed application and dependency manifests by identity and digest; do not invent a combined image count. |
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

- exact upstream provider issuer;
- exact upstream provider subject, retained only by Keycloak and exposed to no browser or ordinary
  application API;
- provider class;
- global user ID;
- verification/provenance class;
- linked, last-authenticated, and retired timestamps; and
- privacy-safe recovery state.

The upstream unique key is `(provider issuer, provider subject)`. The application principal is the
separate exact Keycloak `(issuer, subject)` from the validated WAOOAW token. BP may retain only a
Keycloak-principal-to-global-user binding and an opaque, purpose-limited provider-link reference
needed for lifecycle/evidence; it must not recreate Keycloak's provider-link table or infer the
upstream subject from email, alias, token claims, or browser input. Provider email is mutable profile
evidence, not either key.

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

Each session also binds the validated Keycloak issuer, subject, client, `sid` when issued,
authentication transaction, assurance method/class, and authentication time. An upstream provider
alias is descriptive routing evidence only; it is not a principal or authorization key.

## 7. Canonical State Machines

### 7.1 Authentication

```text
ANONYMOUS
  -> ENTRY_INTENT_CAPTURED (LOGIN | REGISTER | TRIAL | HIRE)
  -> AUTH_STARTING
  -> PROVIDER_REDIRECTED
  -> CALLBACK_VALIDATING
  -> IDENTITY_RESOLVED
  -> SESSION_ESTABLISHED
  -> ROUTING
       -> READY
       -> AUTHENTICATED_VISITOR
       -> ONBOARDING_REQUIRED
       -> TENANT_SELECTION_REQUIRED
       -> RECOVERY_REQUIRED
```

Any validation, provider, collision, revocation, or dependency failure transitions to one typed
recoverable or terminal state. No failure returns an apparently authenticated session.

Entry intent is server-held, integrity protected, and consumed once. `LOGIN` never starts
registration or creates an account, tenant, membership, Trial, Hire, payment, or relationship. A
Login with no active account ends as `AUTHENTICATED_VISITOR` at the accepted safe Marketplace
target. `ONBOARDING_REQUIRED` is reachable only from an explicit `REGISTER`, `TRIAL`, or `HIRE`
intent; the exact server-validated Trial/Hire continuation resumes only after durable account
completion. A completed account selecting Register routes safely to `READY` rather than starting
another registration.

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
Cancel or close before durable completion creates no account, tenant, membership, Trial, Hire,
payment, or authority mutation. It clears transient launch/registration authority, preserves only
accepted non-secret draft fields, and returns to the validated public or originating journey.

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
Because the current session is revoked before selection, cancellation or provider failure ends
truthfully unauthenticated at the validated public return with a restart action; it never restores,
implies, or displays the prior account as active. The customer-visible confirmation for this
consequence is required before dispatch but its exact copy and composition remain Product-approved
presentation scope.

### 7.6 Tenant switch

```text
ACTIVE_SESSION
  -> MEMBERSHIP_LIST_AUTHORIZED
  -> TARGET_MEMBERSHIP_REVALIDATED
  -> SESSION_CONTEXT_ROTATED
  -> TARGET_TENANT_ACTIVE
```

No provider redirect occurs unless current assurance is insufficient for the requested operation.
Cancellation, stale selection, or dependency failure leaves the existing tenant selection
unchanged. The selector may display only server-authorized memberships and customer-safe labels;
route, query, local-storage, or browser-invented tenant identifiers never become options or
authority.

## 8. OIDC and Token Contract

1. Authorization Code with PKCE `S256` is mandatory.
2. Callback processing validates exact configured Keycloak issuer, state, nonce, code verifier,
   redirect URI, client, signature, algorithm, audience, authorized party, time, authentication
   time, and required broker evidence. Discovery, authorization, token, JWKS, user-info, logout, and
   broker endpoints come only from version-controlled exact HTTPS configuration for the accepted
   issuer; no callback, token claim, request header, or user input may select a host, scheme, realm,
   path, redirect target, or key source. Redirect targets are server-owned relative route identifiers,
   never absolute, scheme-relative, encoded-host, or caller-supplied URLs.
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
11. Front-channel or back-channel logout messages are not trusted as ordinary browser commands.
    Back-channel logout validates exact issuer, audience/authorized party, signature, algorithm,
    event claim, `iat`, unique token identity, and `sid` or subject; rejects replay; and atomically
    revokes all mapped application-session families before acknowledging. Subject-wide events may
    revoke only the exact Keycloak principal in the exact environment/client.

## 9. Provider Contract

Provider readiness has two distinct meanings. Operational readiness is a default-disabled,
environment-specific server decision backed by accepted evidence. Customer-visible readiness is
the existing WC-105 four-control projection: Google, Facebook, Apple, and Email remain mounted;
each is disabled until its own operational readiness is `AVAILABLE`, and an unqualified method is
truthfully unavailable. Adding Apple or passkey configuration, synthetic evidence, or a server
readiness state does not enable a control or authorize a label, order, route, layout, or copy
change. Such presentation changes require an exact accepted Product/UX amendment and separate
current-session implementation authorization.

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

The selected target is **Keycloak-owned passkey authentication with verified-email recovery**.
WAOOAW Web only starts the broker ceremony and renders normalized outcomes. It does not issue or
verify passkeys, email proofs, OTPs, magic-link secrets, or recovery credentials.

Email remains disabled in every shared environment until the pinned stock Keycloak version proves:

1. resident-key WebAuthn registration and authentication with accepted attestation policy;
2. verified-email bootstrap and recovery without an account-enumeration oracle;
3. recovery cannot remove the last usable method or bypass required step-up;
4. throttling, lockout, resend, expiry, replay, device-loss, and credential-revocation behavior;
5. accessibility and supported-browser behavior; and
6. backup/recovery preserves credential and account continuity.

Password and magic-link authentication are not part of this implementation contract. Enabling
either requires an accepted amendment with its own credential, breach, delivery, abuse, and
recovery controls.

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
9. Keycloak is the binding authority. BP records only an operation state and opaque projection.
   Link, unlink, and recovery use a durable idempotent saga: `REQUESTED -> PROOF_VERIFIED ->
   IDP_COMMITTED -> PROJECTION_CONFIRMED -> COMPLETED`, with explicit compensating or
   `RECOVERY_REQUIRED` states. No customer success is returned before the Keycloak binding and BP
   projection are read back and agree. Timeout or ambiguous IdP outcome is reconciled by operation
   identity and read-back; it is never blindly retried, merged, or treated as failure/success.
10. Successful link, unlink, credential recovery, or principal rebinding rotates the current handle
    and revokes every older affected session family. A new Keycloak subject is never silently rebound
    to a historical global user.
11. Keycloak mutation is authorized architecturally only through ADR-008 Amendment 4 and Section
    10.1. No implementer may promote the WC-085 read-only client, expand the endpoint set or role
    grant, call an unsupported broker endpoint, or add a custom provider/image.

### 10.1 Binding Stock-Keycloak Lifecycle Interface

`AUTHZ-GATE-01` is resolved by ADR-008 Amendment 4. The sole lifecycle mutation identity is the
separate confidential service-account client `waooaw-bp-identity-lifecycle-writer`, owned
accountably by Platform Operations and consumed only by Business Platform. Its only assigned
realm-management role is `manage-users`; no composite or additional role is permitted. This role
is the smallest supported stock Keycloak 25.0.6 role for the required writes, but it is realm-wide
user-management authority. Supported fine-grained admin permissions are not claimed because
Keycloak 25.0.6 documents that feature as Preview, disabled by default, and not fully supported.

The closed adapter allows only:

1. `GET /admin/realms/waooaw/users/{user-id}`;
2. `GET /admin/realms/waooaw/users/{user-id}/federated-identity`;
3. `POST /admin/realms/waooaw/users/{user-id}/federated-identity/{provider}`; and
4. `DELETE /admin/realms/waooaw/users/{user-id}/federated-identity/{provider}`.

The writer secret is the separate environment-local Key Vault reference
`bp-identity-lifecycle-writer-client-secret`; tokens use `client_credentials`, live at most 60
seconds, are never persisted, and travel only over the exact private-TLS Keycloak route with no
redirect. Neither browser nor provider material can select host, realm, user, provider alias,
method, path, or request representation. The WC-085 `waooaw-bp-identity-reader`, its secret,
`view-users` grant, and runtime remain unchanged.

Every mutation is bound to the one-time step-up proof in Section 11 and the persisted lifecycle
operation ID. Before-state and every normal, timeout, disconnect, or unknown result are read back.
An HTTP success is not commit proof. A same-input replay returns the recorded terminal result; a
different-input replay denies. Unknown outcomes reconcile before any further write, then either
continue, apply the recorded inverse compensation and read it back, or quarantine both projections
as `RECOVERY_REQUIRED`. No divergent binding is usable and every affected session family is
revoked. The source binding for a rebind is retired only after exact source/target pre-read; the
recorded representation is retained only inside the encrypted nonterminal operation until the
target commit or exact compensating restore is read back, then erased.

Customer behavior remains the existing provider-neutral state contract: no success while pending
or ambiguous, non-enumerating collision, session rotation/revocation on success, and the existing
safe retry/support action for `RECOVERY_REQUIRED`. No route, copy, control, provider activation, or
administrative recovery is authorized.

Qualification and operations must prove the pinned documented `200` add/read and `204` remove
semantics, exact role mapping, closed endpoint allowlist, reader denied writes, writer denied
non-user realm/client/provider/role administration, private route/no redirects, audit redaction,
timeout-before/after-commit reconciliation, compensation, concurrency, collision, last-method
protection, and old-session denial. Tests must not falsely claim `manage-users` denies unrelated
user writes. Every Keycloak pin change repeats the endpoint, source permission-check, response,
admin-event, and negative-role suite.

Keycloak admin-event recording uses representation capture disabled, with the dedicated
service-account identity providing attribution; events remain restricted operational records.
Exported evidence is redacted and contains only operation/correlation ID plus normalized
operation/result classes. New lifecycle starts stop on emergency halt or writer disablement.
Revocation disables the client or removes its role mapping and rotates/revokes its secret.
Rollback reconciles or quarantines all nonterminal operations before revoking the writer and never
restores retired bindings, old sessions, or the reader as a writer.

## 11. Authorization and Multi-Tenancy

1. Business Platform and each enabled resource owner validate exact token issuer, signature,
   lifetime, audience, authorized party, assurance, and accepted algorithm.
2. Current membership is resolved from authoritative storage using validated identity. Client
   tenant input is never proof.
3. The active tenant in the application session is a convenience context only. Every protected
   operation revalidates membership and local resource/action policy.
4. Authentication completion, tenant selection, membership/role or authority change, step-up,
   account recovery, link/unlink, and principal rebinding always rotate the application-session
   handle; the previous handle is invalid in the same transaction.
5. Step-up authentication is required for sensitive account, provider, membership, payment,
   hiring, recovery, credential, and consequential authority changes.
6. Customer and institutional identities remain isolated. No role or token is silently translated
   between them.
7. RLS, tenant transaction context, idempotency, evidence-first behavior, and Emergency Stop remain
   independently enforced.
8. Authorization denial is typed, privacy-safe, and does not disclose another tenant or account.
9. Step-up is a fresh Keycloak ceremony, not a client claim. The server requires `auth_time` no more
   than five minutes old, an accepted `acr`/`amr` for the exact operation risk, and a one-time
   server-held transaction bound to session family, principal, operation, resource, safe return
   route, and expiry. Passwordless credential, recovery, provider-link, and authority-changing
   operations require phishing-resistant authentication when the accepted Keycloak/provider
   capability supports it; if the required method is unavailable, the operation remains disabled.
   Completion rotates the session and the proof cannot authorize another command.

## 12. Session Persistence and Continuity

### 12.1 Selected owner and physical placement

The **Web BFF is the sole application-session lifecycle owner**. Session records use a new
Web-owned `web_session` schema in the existing environment PostgreSQL service. This is a logical
ownership boundary, not a new database, deployable, public API, or Business Platform authority.

The Web BFF receives a dedicated non-owner, `NOBYPASSRLS` database role restricted to the
`web_session` schema. Business Platform roles receive no token-material or session-row access.
Database administration, backup, recovery, encryption-at-rest, and schema migration remain
Platform-owned infrastructure responsibilities. Web owns record semantics, session commands,
retention requests, and application-session evidence.

Each browser cookie contains a uniformly random 256-bit handle. The database stores only a
versioned keyed digest of that handle. Provider and Keycloak tokens are envelope-encrypted before
persistence with an environment-specific key reference; the data-encryption key, plaintext tokens,
and cookie handle are never stored in indexes, logs, metrics, traces, evidence, or migration output.

### 12.2 Rejected alternatives

| Alternative | Disposition |
|---|---|
| Browser-carried encrypted JWT with tokens | Rejected: weak centralized revocation, refresh races, and excessive compromise blast radius. |
| Business Platform session API/store | Rejected: would make BP a browser-session/token custodian and conflict with the three-plane boundary. |
| New Redis or managed session product | Rejected for this slice: adds a new durable dependency, cost, recovery owner, and rollback surface without a demonstrated requirement. |
| Keycloak session as the WAOOAW application session | Rejected: cannot own WAOOAW tenant selection, local outage-safe logout, or application-specific revocation semantics. |

### 12.3 Required storage semantics

The schema must provide atomic create, identifier rotation, compare-and-swap refresh lease,
revoke-one, revoke-family, revoke-all-for-user, expire, and cleanup operations. Rotation commits the
new handle digest and invalidates the old digest in one transaction. Refresh uses one bounded lease
per session; a second contender waits for or observes the committed result and never reuses a
rotated refresh token. Detected reuse revokes the complete session family.

Required time bounds:

- idle timeout: 30 minutes;
- absolute application-session lifetime: 8 hours;
- refresh lease: at most 15 seconds;
- revoked-handle denial: immediate at the Web boundary;
- expired/revoked row operational retention: 30 days;
- privacy-safe security-event retention: 365 days unless a later accepted policy shortens it;
- backup retention: 35 days;
- application-session store RPO: at most 5 minutes;
- application-session store RTO: at most 30 minutes.

An unavailable session store fails closed for protected traffic. Local logout still expires the
browser cookie and records a deferred server-revocation alert if the store is unavailable; it never
returns an authenticated state. Recovery must not resurrect expired, revoked, superseded, erased,
or legacy sessions.

Token envelopes and upstream-session material are destroyed immediately on revoke, logout, expiry,
supersession, unlink, recovery, or account deletion; the 30-day operational row may retain only
non-sensitive state needed for replay denial, reconciliation, and audit correlation. Key retirement
or deletion is not allowed to strand live ciphertext: rotate through versioned read-old/write-new
keys, re-encrypt before retirement, and revoke all affected sessions on suspected digest/encryption
key compromise. Backups follow the same logical erasure and non-resurrection rules.

Keycloak realm configuration, signing keys, provider links, and test identities must be durable in
every environment used for repeatable login testing. If Demo or UAT intentionally resets
application data, identity continuity must be independently preserved or the environment must
truthfully declare and enforce a complete forced-session/user reset.

### 12.4 Binding physical session contract

The migration creates exactly these Web-owned relations; physical names and ownership are not left
to implementation:

| Relation | Required keys and facts |
|---|---|
| `web_session.user_generations` | `global_user_id uuid PRIMARY KEY` (the canonical BP account/global-user reference), `generation bigint NOT NULL CHECK (generation > 0)`, `updated_at timestamptz NOT NULL`, and last revocation reason/correlation. This row is the serialization point for create and revoke-all. |
| `web_session.session_families` | `family_id uuid PRIMARY KEY`; exact Keycloak `issuer` and `subject` as `varchar(256) COLLATE "C"` and `client_id varchar(256) COLLATE "C"`; `global_user_id` FK to `user_generations`; captured `generation`; assurance/authentication time; keyed 32-byte `sid_digest` plus digest-key version when supplied; nullable encrypted token envelope plus key/version; created, last-seen, idle-expiry, absolute-expiry, revoked and erased times; refresh version; nullable lease owner/expiry; state in ACTIVE/REVOKED/EXPIRED/ERASED; and schema/deploy version. CHECK constraints make ACTIVE require unexpired envelope/key metadata and make every terminal state require a NULL envelope and lease. |
| `web_session.session_handles` | `handle_id uuid PRIMARY KEY`, `family_id` FK, digest-key version, fixed 32-byte keyed `handle_digest`, state in ACTIVE/SUPERSEDED/REVOKED/EXPIRED, and created/expiry/superseded/revoked times consistent with state. UNIQUE `(digest_key_version, handle_digest)` across all retained history and a partial UNIQUE active handle per family prevent handle reuse and dual current handles. Raw handles are never persisted. |
| `web_session.oidc_transactions` | `transaction_id uuid PRIMARY KEY`, unique versioned keyed state digest, encrypted nonce/PKCE/intent/safe-route bundle, initiating-browser digest, provider class, created/expiry/consumed times and schema version. A consumed/expired transaction cannot be updated back to usable state. |
| `web_session.logout_replays` | Exact issuer/client plus a versioned keyed digest of logout-token `jti`, received and expiry times, with UNIQUE `(issuer, client_id, jti_digest)`. It contains no token or subject payload and exists only for the accepted replay window. |

All text identity keys are nonempty, bounded, `COLLATE "C"`, and never trimmed, folded, or inferred.
Every FK is `ON DELETE RESTRICT`; referencing columns are indexed. `active_membership_id`, when
stored on a family, is an opaque nullable UUID without a cross-schema FK and is never an RLS or
authorization key. No tenant ID is persisted in these relations.

The migration administrator owns the schema/tables. A dedicated NOLOGIN, NOSUPERUSER,
NOBYPASSRLS, NOCREATEDB, NOCREATEROLE operation owner receives only the columns needed by
fixed-search-path, static-SQL session functions. The Web runtime receives schema USAGE and EXECUTE
only on those functions: no direct table DML, no schema CREATE, no owner membership, and no access
to BP/identity tables. PUBLIC, BP, CE, PR, AIR, WBE, migration jobs, and evidence readers receive no
session relation or token-envelope privilege. These are account/session records, not tenant business
rows; selected membership must therefore never become their tenant-RLS discriminator. Tenant
resource RLS remains independently mandatory exactly as ADR-003's controlling amendment specifies:
fresh validated issuer/subject, current membership, both transaction-local tenant settings, ENABLE
and FORCE RLS, restrictive USING/WITH CHECK, nonowner/NOBYPASSRLS roles, and context overwrite/reset.

The functions lock in this order: `user_generations`, affected `session_families` in UUID order,
then their handle/transaction rows. Create captures the locked current generation. Lookup succeeds
only for an active, unexpired handle and family whose captured generation still equals the locked
user generation. Rotate inserts the new digest and supersedes the old digest atomically. Refresh
acquires the family row and compare-and-swap lease/version; no network call occurs while a database
lock is held. Revoke-family nulls token material, ends the lease, revokes every active handle and
advances state in one transaction. Revoke-all first increments the generation and then erases and
revokes known families in the same transaction; generation mismatch denies any family missed by a
concurrent scan. Callback completion locks and consumes its OIDC transaction before creating a
family. Database serialization/deadlock retries restart the whole transaction with bounded attempts;
unknown commit outcomes reconcile by original transaction/family identity and never mint another
authority.

### 12.5 Identity lifecycle persistence and locking

Keycloak remains provider-binding authority. BP owns only `identity.lifecycle_operations` and
`identity.provider_link_projections` in its existing database. The operation relation has an
operation UUID primary key, exact Keycloak issuer/subject, command type, versioned keyed
idempotency digest, opaque target-link reference, state, attempt/version, correlation, created,
updated and terminal timestamps, with UNIQUE `(issuer, subject, command_type, idempotency_digest)`.
The projection has opaque `link_id` primary key, `global_user_id`, provider class, opaque Keycloak
binding reference, ACTIVE/RETIRED state, created/retired times, and uniqueness that reserves the
opaque binding reference across retained history. It contains no upstream provider subject, token,
email, phone, or credential.

Lifecycle mutations run in one BP transaction for operation/projection/evidence state, use current
actor-scoped FORCE RLS, and acquire deterministic transaction advisory locks for the exact
application principal and opaque target reference in sorted signed-bigint order before row locks.
Network proof and Keycloak calls occur outside that transaction. `IDP_COMMITTED` is recorded only
after read-back; ambiguous outcomes remain reconcilable and never return success. Runtime roles
cannot delete operation history, reactivate a retired projection, or retarget either key. This
extends WC-085 only for the separately accepted WC-123 lifecycle scope; it does not reinterpret or
mutate WC-085's initial-account keys, OWNER membership, resolver, or ledger boundaries.

### 12.6 Retention, erasure, backup, and restore protocol

OIDC transactions are erased at consumption and deleted no later than 24 hours after expiry.
Logout replay rows live only for the maximum accepted logout-token/retry window plus clock skew,
capped at 24 hours. Revoked/expired family and handle rows retain only digests, state, timestamps,
reason and correlation for 30 days; envelopes, nonce, PKCE, upstream-session material, device data,
and active membership selection are erased immediately when authority ends. Lifecycle operation
and provider-link key history remains only while required to prevent replay/reassignment and meet
the approved legal purpose; raw personal/contact/provider-subject data is never retained there.
Security events use their separately owned append-only relation and 365-day maximum unless legal
hold or a shorter accepted policy applies.

Account erasure immediately revokes all generations/families and cryptographically erases every
session/protocol envelope. The minimum nonreassignable keyed digest and reason may remain through
the 30-day anti-replay period; after dependent family/handle cleanup, the `user_generations` row is
deleted unless a documented legal hold applies. Legal hold suspends only the specifically held
record class and never restores authority. Backup copies expire within 35 days and are inaccessible
to runtime roles.
Every restore occurs into a traffic-isolated database and, before Web credentials or traffic are
enabled, runs a mandatory restore epoch that increments all user generations, marks every restored
family/handle revoked, nulls every token/protocol envelope and lease, deletes expired protocol
rows, and records the restore manifest and counts. Thus a restore always forces reauthentication;
it never trusts a backed-up ACTIVE state. If sanitization, access to required cryptographic material, database constraint/grant/RLS
validation, or manifest reconciliation fails, the store remains offline. RPO <= 5 minutes and
RTO <= 30 minutes measure recovery to this sanitized fail-closed state, not resurrection of sessions.

### 12.7 Binding platform placement, configuration, and secret lifecycle

`web_session` is deployed inside the existing environment application PostgreSQL boundary, not the
Keycloak database. Demo and UAT each use an isolated persistent application PostgreSQL boundary and
must independently pass PITR plus the sanitized restore epoch in Section 12.6; application
deployment does not wipe either environment's sessions or database state. Section 12.7.1 binds
each environment to its dedicated PgBouncer route. Production uses a separate highly
available PostgreSQL instance; its detailed placement, sizing, backup configuration, and activation
remain plan-only until separately authorized. Web receives private database connectivity and only
the function-execute runtime role in Section 12.4; Keycloak, BP, and other workloads receive no
route or privilege to session token material.

The accepted environment manifest and closed-world secret catalog are extended, not replaced. The
manifest owns session mode, schema/deploy compatibility versions, cookie policy, exact identity
endpoints, timeout/lease values, pool and concurrency bounds, provider readiness, and non-secret key
version identifiers. The catalog owns separate environment-local entries for handle-digest,
`sid`/state/logout-replay digests, token-envelope encryption, Web OIDC client authentication, and
each enabled provider dependency. Each entry names one purpose, owner, Web managed identity,
rotation class, overlap, expiry, compromise action, and exact Key Vault reference. Secret values
never enter images, manifests, Terraform state, environment-variable literals, workflow
inputs/outputs, logs, or evidence.

Digest and envelope keys use versioned read-old/write-new rotation. At most one version writes and
at most two versions read during a bounded overlap of 24 hours. Rotation first publishes the new
catalog/reference version, proves dual-read and new-write behavior, re-digests or re-encrypts live
records where required, then retires the old version. Missing, disabled, expired, unknown, or
unauthorized key references keep authentication/session routes unready. Suspected digest-key
compromise revokes all families indexed by that version; suspected envelope-key compromise revokes
and erases affected families. Retirement is blocked while live ciphertext or retained replay state
still requires the old version. Platform Operations owns Key Vault lifecycle and alerting; Platform
IT Expert owns application compatibility and the rotation/compromise rehearsal.

The existing environment Redis dependency may hold only short-lived, non-authoritative,
environment-scoped abuse counters; it is never a session, identity, membership, revocation, or
evidence store. Keys use keyed digests and bounded TTLs, never raw identity/contact/network values.
Authentication start, callback, recovery, link/unlink, resend, and credential operations fail closed
when the shared limiter is unavailable or its restart epoch is uncertain. A Redis restart imposes a
hold for the longest applicable quota window rather than resetting callers to an unlimited state.
Currently valid protected sessions may only use an explicitly qualified bounded degradation policy.
Production cannot activate until the existing topology's Redis/HA decision satisfies this contract.

#### 12.7.1 Founder-aligned Demo/UAT database-route amendment

The Founder superseded the disposable Demo placement on 2026-10-16 and bound Demo to the UAT
database standard with lower, environment-specific capacity. Demo and UAT each use an isolated,
persistent Azure Database for PostgreSQL Flexible Server and a dedicated PgBouncer dependency.
Production remains a separate highly available PostgreSQL instance under separate authority. This
closes the physical-placement decision but does not authorize cloud mutation or change database
authority. PostgreSQL remains the existing application-data authority and PgBouncer remains only
its transaction-pooling gateway. The older
`infrastructure/terraform/modules/core` PgBouncer is evidence only and MUST NOT be copied or treated
as the active phase-2 design.

PgBouncer is a dedicated infrastructure dependency, never a first-party application workload.
Demo and UAT each run it in their own dedicated dependency Container App. It has no schema, data
ownership, or independent credential authority.

| Property | Demo | UAT |
|---|---|---|
| Physical database | One persistent Azure Database for PostgreSQL Flexible Server named `psql-demo-application`, privately accessible only through dedicated infrastructure Container App `ca-demo-pgbouncer`. It hosts separate databases and roles for application state, Keycloak, Web sessions, and approved Demo dependencies. Environment-specific low-cost sizing is required; PostgreSQL sidecars are prohibited. | One persistent Azure Database for PostgreSQL Flexible Server named `psql-uat-application`, with private access only, hosts separate databases and roles for application state, Keycloak, Web sessions, and approved dependencies. One dedicated infrastructure Container App named `ca-uat-pgbouncer` is the only principal/network path permitted to server port `5432`. The active phase-2 roots do not yet implement either environment route. |
| Release classification | PostgreSQL and PgBouncer are named infrastructure dependencies in the signed dependency manifest. Neither is a first-party application image, permanent workload, or eighth member of the exact-seven release tuple. | PgBouncer is a named infrastructure dependency in the signed dependency manifest; Flexible Server is a managed infrastructure resource. Neither changes the exact-seven first-party count. |
| Session placement | `web_session` is a schema in `waooaw_application`; the migration administrator owns it and `web_session_app` receives only Section 12.4 function execution. | Identical logical placement and grants in the persistent `waooaw_application` database; it is not placed in Keycloak, Temporal, or a second database authority. |
| Canonical Web target | `pgbouncer.db.demo.waooaw.internal:6432/waooaw_application` | `pgbouncer.db.uat.waooaw.internal:6432/waooaw_application` |
| Private DNS and direct denial | Environment-owned zone `db.demo.waooaw.internal` has one `pgbouncer` record for dedicated PgBouncer. Flexible Server private DNS is linked only to the PgBouncer VNet; its delegated-subnet NSG permits `5432` only from PgBouncer and denies application/runner subnets. | The identical environment-isolated pattern applies to `db.uat.waooaw.internal` and `psql-uat-application`; neither environment can resolve or route directly to its server or to the other environment. |
| TLS and trust | PgBouncer terminates TLS 1.2 or later with an environment-local server certificate whose only DNS SAN is `pgbouncer.db.demo.waooaw.internal`. A Demo database-serving intermediate signs it. The Web revision receives the pinned CA chain as a non-secret, digest-bound trust-bundle file; the signing key and server private key remain non-exportable or secret-scoped in Demo Key Vault and are readable only by the database dependency identity. Web uses full chain and hostname verification. | PgBouncer terminates TLS 1.2 or later with an environment-local certificate whose only DNS SAN is `pgbouncer.db.uat.waooaw.internal`; the UAT database-serving intermediate and private key follow the same Key Vault isolation. PgBouncer separately connects to `psql-uat-application.postgres.database.azure.com:5432` with `sslmode=verify-full` and a digest-pinned Microsoft PostgreSQL trust chain. Plaintext, public/IP fallback, trust-on-first-use, and verification downgrade are prohibited on both hops. |
| Lifecycle and recovery | Application revisions and lease expiry preserve database state. Automated backup/PITR retention is 35 days. Qualification restores the selected point to an isolated private restore server, runs the Section 12.6 sanitized restore epoch before traffic, and proves RPO <= 5 minutes and RTO <= 30 minutes. Lease expiry scales workloads and PgBouncer to zero and stops the server without deleting storage or backups. | Identical standard with independently selected UAT capacity, credentials, backups, restore evidence, and environment isolation. |

Production is not promoted from either database. It receives a separate highly available PostgreSQL
instance and separate data, DNS, credentials, trust, backup, and recovery boundaries. No Demo/UAT
data or secret is copied upward. Production route, HA shape, capacity, RPO/RTO proof, and activation
remain outside this bounded CB-019 Demo/UAT amendment.

`WEB_SESSION_DATABASE_URL` is one Key Vault secret value, but it is not generated by Terraform and
is never a Terraform variable, local, output, plan value, state value, workflow input/output,
command argument, retained file, log, or evidence field. An environment-private, no-echo database
credential provisioner uses separate database-administration and Key Vault write identities. It:

1. resolves the accepted environment's canonical target from the environment projection and rejects
   every other host, port, database, username, query option, redirect, and public address;
2. generates at least 32 random bytes in memory, encodes them without shell interpolation, and
   creates or alters only LOGIN role `web_session_app` with `NOSUPERUSER`, `NOCREATEDB`,
   `NOCREATEROLE`, `NOINHERIT`, and `NOBYPASSRLS`;
3. applies the Section 12.4 grants, proves through PgBouncer that
   `current_user = 'web_session_app'`, table access is denied, and
   `web_session.schema_ready(...)` succeeds;
4. constructs in memory exactly
   `postgresql://web_session_app:<percent-encoded-password>@<canonical-host>:6432/waooaw_application?sslmode=verify-full`
   and writes it directly through the Key Vault data plane as a new version of
   `web-session-database-url`; and
5. emits only environment, catalog digest, target digest, Key Vault secret-version identifier,
   role/grant check classes, and redacted success/failure.

The Web managed identity may `get` only that environment-local secret and the three session-keyring
secrets. The provisioner may set only those catalog entries and may administer only
`web_session_app`; Terraform deployment identity cannot read their values. Startup additionally
checks that the parsed URL equals the accepted host, port, database, role, and `verify-full` policy.

The three keyring values have one canonical JSON form, rather than a generic random string:

```json
{
  "schemaVersion": "waooaw-keyring-v1",
  "purpose": "handle-digest | protocol-digest | token-envelope",
  "activeWriteVersion": "v<UTC-timestamp>-<random-id>",
  "readVersions": ["v<UTC-timestamp>-<random-id>"],
  "keys": {
    "v<UTC-timestamp>-<random-id>": "<base64url-encoded 32-or-more random bytes>"
  }
}
```

The private provisioner generates each purpose independently in memory, validates exact fields,
unique version IDs, one active writer, at most two readable versions, minimum 32 decoded bytes per
key, and agreement with the non-secret manifest write-version identifier, then writes directly to
its purpose-specific Key Vault secret. Unknown fields, duplicate or cross-purpose key bytes,
generic-string payloads, malformed base64url, missing versions, or catalog/manifest disagreement
fail closed. Normal rotation creates a new version/key, writes a complete read-old/write-new ring,
updates the reviewed manifest active version, proves dual-read/new-write and required
re-digest/re-encryption, then writes a ring without the retired key only after Section 12.7's
retirement guard passes.

Database-password rotation has no unsafe overlap because PostgreSQL provides one verifier for
`web_session_app`. It places authentication/session traffic in a readiness hold, drains Web pools,
changes the role password over the private administrator path, writes a new Key Vault secret
version, starts a Web revision pinned to that version, proves the exact route/role/grants/readiness,
and only then restores traffic. Any intermediate failure leaves traffic held; it never restores an
old password, exposes a direct route, or relaxes TLS. Emergency rotation follows the same hold and
also terminates all old-role backend sessions.

Rollback selects only a retained Web/dependency tuple compatible with the current additive schema,
credential secret version, trust-bundle digest, and keyring read set. Demo and UAT rollback preserve
persistent database state and additive schema: each switches Web traffic to the retained compatible
revision, keeps the current PgBouncer and credential versions, and never restores the source database
merely to reverse application code. Neither environment may roll database state back
in place, revive retired keys or invalidated sessions, reuse an expired secret version, or fall
back to a sidecar, public DNS, or plaintext.

Promotion copies no data, credentials, certificates, private-DNS records, Key Vault versions, or
key bytes from Demo. UAT independently provisions its persistent route and secrets, applies the same digest-pinned
additive migration and immutable application tuple, and must pass private DNS/TLS, restricted-role,
capacity, PITR/restore, sanitized restore epoch, and readiness qualification. Demo acceptance is
evidence for application behavior only; it does not establish UAT durability or authorize UAT
traffic. Production independently provisions its separate highly available PostgreSQL boundary
only under separate authority.

Capacity is a reviewed environment-manifest input, not an implementation constant. Before traffic,
qualification must prove all of the following at the configured Web maximum replica count:

- `max replicas * per-replica session DB pool + migration/operations reserve` is no more than 80% of
  the application database connection limit;
- request, refresh, callback, and lifecycle queues are bounded and expose saturation metrics;
- exactly one refresh runs per family, with global and per-principal concurrency bounds;
- database pool acquisition, lock, statement, BP membership, Redis, and identity-provider calls have
  explicit timeouts no longer than the calling request budget; and
- overload rejects new authentication/lifecycle work with typed `429` or `503` plus bounded retry
  guidance, while protected traffic fails closed and no unbounded in-memory queue or retry storm is
  possible.

For this phase, Demo Web is limited to one replica and UAT Web to two; Section 12.8 fixes each Web
pool at five. Each environment manifest selects the lowest capacity that preserves migration and
operations reserve and keeps aggregate planned server connections at or below 80%. Increasing any
replica, pool, client, or server limit requires a reviewed capacity amendment and repeat
qualification.

Demo and UAT sizing must be qualified independently. Scale-to-zero, cold start, database reset,
Redis restart, and dependency recovery are load scenarios, not exemptions from the SLOs.

No Demo/UAT route, DNS, TLS, credential, lifecycle, rollback, promotion, or capacity selection
remains for implementers to invent. Remaining decisions are governance gates: the Founder must
accept this exact amendment and separately authorize implementation. Production's exact HA service
tier, zones/replicas, endpoint, sizing, backup/restore plan, and activation remain intentionally
undecided and outside phase 2. `CB-019` remains OPEN until the accepted amendment is implemented
and evidenced by its resolution authority.

### 12.8 Web PostgreSQL protocol-client amendment

For AUTH-WC-03, Web may add exactly one direct runtime dependency:
`postgres@3.4.9` (`https://registry.npmjs.org/postgres/-/postgres-3.4.9.tgz`,
SRI `sha512-GD3qdB0x1z9xgFI6cdRD6xu2Sp2WCOEoe3mtnyB5Ee0XrrL5Pe+e4CCnJrRMnL1zYtRDZmQQVbvOttLnKDLnaw==`).
This is a PostgreSQL wire-protocol client with bundled TypeScript declarations and no declared
runtime dependencies. It is accepted only as a transport from the existing Web BFF to the existing
application PostgreSQL boundary. This amendment does not accept an Auth.js adapter, ORM, query
builder, generic database-session schema, new workload/service/database/cache, BP token custody,
public route, or topology change. Existing NextAuth/Auth.js `4.24.11` protocol hooks remain pinned
and retain only the Section 25 `AUTHZ-SD-11` boundary.

Web owns one process-level client/pool per Web replica. Request handlers may borrow capacity but do
not construct, own, or close pools. Graceful termination stops admission, drains bounded in-flight
calls inside the lifecycle budget, then closes the pool; forced termination abandons no new
authority because every mutation remains an atomic database function. Configuration is exactly
`wc123-auth-capacity-v1`: pool maximum `5` per replica, a `1,000 ms` acquisition/admission deadline,
`5,000 ms` statement timeout, `1,500 ms` refresh-lock deadline, and calling budgets of `10,000 ms`
for request/refresh and `15,000 ms` for callback/lifecycle. Connect establishment is bounded by the
remaining acquisition deadline, idle connections may be retired without exceeding pool `5`, and
no client queue may outlive the accepted bounded request/refresh/callback/lifecycle queue. Timeout,
disconnect, cancellation, serialization failure, and unknown commit use the existing typed
fail-closed reconciliation rules; they never trigger an unbounded retry or a second authority.

The client connects only through the accepted private-TLS PgBouncer route using the dedicated
`web_session_app` login and environment-local secret reference. Certificate and hostname
verification are mandatory against the accepted trust bundle; plaintext, public DNS/IP fallback,
redirect, caller-selected connection strings, and direct database-server bypass are prohibited.
PgBouncer remains in transaction-pooling mode. Therefore `postgres` server-side statement caching
is disabled (`prepare: false`); every invocation still uses the library's tagged-template/extended
protocol parameter binding and a statically enumerated, schema-qualified approved function name.
No identifier, SQL fragment, relation, function name, role, or connection target is interpolated
from request data. Multi-step atomicity belongs inside the approved SECURITY DEFINER functions,
not in Web-held cross-request transactions.

`web_session_app` receives only schema `USAGE` and `EXECUTE` on the approved functions. Web must not
query a `web_session` relation, change role/search path, invoke maintenance-only functions, or use a
BP/application role. Logs, traces, metrics, errors, pool labels, query annotations, and evidence
may contain only normalized operation/result class, timing, saturation, and privacy-safe
correlation ID. They must not contain SQL parameter values, raw opaque handles or their digests,
tokens/envelopes, protocol material, connection secrets, identity subjects, or personal data.

Internal readiness must acquire within `1,000 ms` and call
`web_session.schema_ready(expected_schema_version, expected_deploy_version)` through the restricted
role, while separately proving the configured private target, TLS verification, pool bound, role,
function grants, current key/catalog/config digests, and telemetry route. Failure keeps
authentication/session traffic unready without exposing detail publicly; liveness remains process
only. Rollback may select only the retained qualified application/dependency tuple whose lockfile,
schema/functions, grants, key versions, and current additive database watermark are compatible.
It closes/drains the new pool and never removes the additive schema, restores browser-JWT session
authority, revives invalidated sessions, grants table access, or falls back to a direct/public
database route.

The lockfile and signed dependency manifest must record exact package name/version, registry
tarball URL, SRI above, resolved package bytes/digest, source repository, license, Node
compatibility, and the complete resolved transitive graph (which is empty for this package
revision). Qualification must verify clean immutable install/frozen lockfile, registry signature,
tarball/SRI equality, no unexpected install scripts or dependency graph, SBOM inclusion, provenance
availability, license policy, malware/secret scan, vulnerability review with explicit disposition,
maintainer/repository release identity, and Web build/test compatibility. Missing provenance or
attestation is recorded as a review input, never silently treated as present. Any package identity,
version, integrity, tarball, dependency graph, install-script, ownership, license, or material
vulnerability change stops for a new accepted amendment.

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

The Web maps each typed outcome to a stable semantic presentation key, not raw server/provider
text. Every mapped state must provide: a truthful plain-language summary, whether any prior session
or selection remains active, one safe next action or an explicit support path, and a copyable
privacy-safe correlation reference when support is required. Cancellation is neutral rather than
an error; retryable, denied, unavailable, expired, and unknown outcomes remain distinguishable and
must not imply that an account, registration, switch, recovery, or logout succeeded.

Existing WC-105 approved English copy and interaction remain the baseline. New or changed
customer-visible strings, routes, controls, ordering, modal geometry, or interaction require an
accepted Product/UX copy map with localization fallback, plural/direction handling, screen-reader
announcement behavior, and separate current-session implementation authority. Missing translation
falls back to reviewed English without exposing provider text or an internal code; it never renders
an empty action. Focus moves to the recovery heading or action, errors are associated with the
affected control, and status/alert announcements do not repeat or trap focus.

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
- lifecycle-writer token acquisition, read-back, compensation, quarantine, role/client revocation,
  and endpoint-denial class;
- API authentication rejection class;
- authorization denial class; and
- forced migration/logout.

Events contain no authorization code, token, PKCE material, raw cookie, password, OTP, provider
subject, raw email/phone, tenant ID, callback query, or unbounded user agent.

Section 23 is the binding SLO, alert, ownership, and runbook contract. The implementation may make
targets stricter but may not invent weaker values or leave an alert without a receiving route.

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

The following 1-5 planning score closes the WC-122 comparison for this implementation boundary.
Five is the strongest fit for the accepted requirement. The managed-CIAM column represents a
product class, not a selected vendor or a procurement claim; any future proposal must replace these
class assumptions with dated vendor evidence, pricing, residency, processor, exit, and contract
terms.

| Criterion | Weight | Durable stock Keycloak | Managed CIAM class | Controlling rationale |
|---|---:|---:|---:|---|
| Compatibility with ADR-008 and current broker/realm | 20 | 5 | 2 | Keycloak is accepted and deployed; substitution requires a new decision and migration. |
| Google, Apple, Facebook, passkey, MFA, linking | 15 | 4 | 4 | Both classes can be viable, but exact pinned-version/vendor proof remains required. |
| BP-owned tenant/membership authority | 15 | 5 | 4 | Keycloak already preserves the boundary; a managed organization model must remain non-authoritative. |
| Data control, export, deletion, audit, residency | 15 | 4 | 3 | Self-hosting preserves direct control; managed terms and export/exit evidence are not selected. |
| Availability, upgrades, staffing, incident ownership | 10 | 2 | 4 | Managed service can reduce operations, while Keycloak keeps upgrade/recovery ownership in WAOOAW. |
| Cost boundedness and procurement certainty | 10 | 4 | 2 | Existing infrastructure is bounded; no accepted managed vendor, tariff, support, or MAU assumption exists. |
| Migration and rollback safety | 10 | 5 | 2 | Keycloak avoids identity migration; managed substitution risks duplicate/dual authority until separately designed. |
| Lock-in and reversibility | 5 | 5 | 2 | Self-hosted standards-based operation is the accepted lower-lock-in baseline. |
| **Weighted score / 5** | **100** | **4.35** | **2.95** | Durable stock Keycloak remains the compatible selection for WC-123. |

This comparison selects Keycloak only for the bounded WC-123 target. It does not certify current
provider configuration, resolve `AUTHZ-GATE-01`, or prohibit a later evidence-backed managed-CIAM
proposal.

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

Browser acceptance covers current supported Chromium, Firefox, and WebKit at the accepted
360x800, 768x1024, and 1440x900 viewports, plus touch and keyboard-only operation. Authentication,
registration, cancellation, recovery, account switch, and tenant switch must also pass at 200%
text zoom, reduced motion, LTR, RTL, reviewed English, one long-label locale, and one locale-fallback
case. Responsive or accessibility repair may reflow accepted presentation but is not authority to
invent a route, command, provider, label, or customer promise.

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

## 20. Exact Interface Contract

### 20.1 Web BFF application-session commands

These same-origin server routes are owned by Web. They require origin and CSRF validation, reject
cross-site ambient-cookie use, return `Cache-Control: no-store`, and never accept a session handle,
identity subject, account ID, or tenant ID from the body as authority.

| Operation | Required semantics |
|---|---|
| `POST /api/auth/session/logout` | Idempotently revoke the current application session, expire the cookie, and succeed locally without an IdP round trip. |
| `POST /api/auth/session/logout-all` | Revoke every WAOOAW application session for the current global user, expire the current cookie, then request Keycloak RP logout as a separately reported outcome. |
| `POST /api/auth/session/switch-account` | Revoke the current session family, expire the cookie, end the Keycloak SSO session, and start one fresh broker ceremony with explicit account selection. |
| `POST /api/auth/session/switch-tenant` | Require current session and recent membership list, revalidate the target membership through BP, rotate the application-session identifier, and store only the selected membership reference. |
| `GET /api/auth/session/status` | Return only normalized application state, assurance, active-tenant selection, expiry class, and one typed next action; no token or provider subject. |

Callback and refresh are internal NextAuth/Auth.js server hooks, not browser-callable token APIs.
They acquire the session refresh lease, rotate tokens and handles atomically, and converge on a typed
unauthenticated state after one bounded failure.

### 20.2 Business Platform operations

The canonical Business Platform OpenAPI owns these provider-neutral operations:

| Operation | Required semantics |
|---|---|
| `GET /api/v1/identity/session` | Resolve exact validated identity and current memberships; return global account reference, assurance, zero/one/many membership projections, and typed next action. |
| `GET /api/v1/identity/memberships` | Return only current memberships visible to the actor, with opaque membership/tenant references, role, state, and selection eligibility. |
| `POST /api/v1/identity/membership-selections/validate` | Revalidate one opaque target membership for session selection; no mutation of membership or business authority. |
| `POST /api/v1/identity/session-revocations` | Record a security revocation intent and privacy-safe evidence for one session family or all application sessions; it does not directly manipulate browser cookies. |
| `POST /api/v1/identity/provider-links` | Start proof-of-control linking under recent step-up. |
| `DELETE /api/v1/identity/provider-links/{linkId}` | Unlink one method only after current proof and proof that another usable method remains. |

Every operation uses exact issuer/subject identity, stable schema versioning, correlation, explicit
limits, deterministic RFC 9457 errors, no-store responses, and current-membership authorization.
The canonical OpenAPI is amended before implementation and generated consumers are regenerated.

### 20.3 Delegated resource authorization

BP, CE, PR, WBE, and other enabled resource owners retain their existing accepted public/private
interfaces. A customer-delegated call carries the original exact bearer only across an allowlisted,
authenticated service channel. Each receiver independently validates the token, resolves current
membership under ADR-003's controlling amendment, sets fresh transaction-local tenant context, and
enforces its resource/action policy. No new general identity facade, tenant assertion header, or BP
authorization oracle is introduced.

## 21. Complete State And Failure Matrix

| Command or flow | Success terminal | Race winner | Dependency outage | Security terminal |
|---|---|---|---|---|
| Callback | `READY`, `AUTHENTICATED_VISITOR`, intent-eligible `ONBOARDING_REQUIRED`, or `TENANT_SELECTION_REQUIRED` | First valid callback consumes transaction; replay denies | No session created; typed retry or restart | Invalid state/nonce/code/issuer/audience denies and burns transaction |
| Refresh | Rotated tokens and session handle | Single refresh lease; contenders consume committed result | Existing session becomes unavailable, never stale-authorized | Reuse or invalid rotation revokes family |
| Local logout | Cookie expired and current session revoked | Revocation dominates refresh/rotation | Cookie still expires; server-revocation alert remains unresolved | Never restores session |
| Global logout | All WAOOAW sessions revoked; upstream result separately reported | Revocation dominates every in-flight command | Current cookie expires; return `REVOCATION_DEPENDENCY_UNAVAILABLE`; never claim other sessions revoked | Provider logout failure cannot restore WAOOAW authority |
| Account switch | Fresh subject-bound application session | Old-family revocation dominates old callbacks | Ends unauthenticated with restart action | Subject mismatch cannot reuse prior continuation |
| Tenant switch | Rotated session with revalidated selection | Membership removal/revocation dominates selection | Selection unchanged; protected action denies if freshness unavailable | Forged/stale membership denies without tenant disclosure |
| Link provider | One new exact issuer/subject binding | Identity-key lock serializes link/unlink | No partial link; status remains unresolved | Collision enters non-enumerating recovery |
| Unlink provider | Binding retired with another usable method preserved | Revocation/unlink dominates login continuation | No partial unlink | Last-method removal denies |
| Security revocation | Family/all-session revocation committed | Revocation dominates refresh, callback completion, and switch | Resource authorization still revalidates membership; session boundary fails closed | Revoked authority cannot return through rollback/restore |
| Recovery | Freshly proved identity resumes same eligible account | Recovery serialization on old/new identity keys | No rebinding | Email equality or incomplete proof never links |

For `logout-all`, store outage expires and disables the current browser session but returns
`REVOCATION_DEPENDENCY_UNAVAILABLE`; it must not claim that other sessions were revoked. During the
outage protected sessions already fail closed. After recovery, other sessions remain denied only if
the revoke-all generation committed; otherwise the customer receives a deterministic retry/support
action. Security-initiated revocation is not acknowledged until its durable revocation generation
commits. No deferred alert or telemetry event is authority.

## 22. Security, Privacy, Data, And Abuse Controls

1. Cookie name uses the `__Host-` prefix outside local development, with `Secure`, `HttpOnly`,
   `Path=/`, no `Domain`, and `SameSite=Lax`; state-changing session commands also require exact
   same-origin and CSRF proof.
2. Callback transactions are one-time, short-lived, server-bound, and bind provider, intent,
   state, nonce, PKCE verifier, safe target, and initiating browser.
3. Session handles, authorization codes, refresh/access/ID tokens, provider subjects, raw email,
   raw phone, and callback queries are prohibited in URLs, logs, traces, metrics, analytics,
   screenshots, evidence, and test snapshots.
4. Per-IP, per-browser, per-identity-keyed, and per-operation controls bound callback, recovery,
   resend, refresh, link, unlink, and switching abuse without creating an enumeration oracle.
5. Authorization checks precede existence detail. Inaccessible and absent identity/tenant resources
   share normalized status, body, timing class, and telemetry class.
6. Database migrations use expand/verify/cutover/contract. The Web role cannot read BP business
   schemas; BP and service roles cannot read Web token material.
7. Backup and restore tests prove revoked handles, retired identities, erased personal data,
   superseded keys, and legacy sessions are not resurrected.
8. Key and secret rotation supports bounded overlap, exact purpose separation, versioned ciphertext,
   re-encryption, revocation, and fail-closed unknown-key handling.
9. Abuse controls use atomic, environment-shared counters and server-derived keys. Client network
   identity is accepted only through the configured trusted-proxy chain; IPv4/IPv6 normalization,
   proxy-hop limits, privacy rotation, burst/sustained quotas, retry bounds, and expiry are explicit.
   Existing and non-existing identities receive the same public status/body/timing class. Limiter
   outage fails closed for recovery, linking, credential, callback, and authentication-start abuse
   surfaces and may only degrade a currently valid session through a separately bounded policy.
   CAPTCHA or provider challenge, if later selected, is defense in depth and never replaces quotas.

## 23. Operability Contract

| SLI | Objective / error budget | Alert threshold | Accountable owner / runbook |
|---|---|---|---|
| Authentication ceremony completion after a valid callback, excluding provider/user time | >= 99.5% over 30 days; 0.5% budget | < 99% for 15 min or 25% monthly budget remaining | Platform IT Expert / `docs/runbooks/authentication-completion.md` |
| Callback-to-router latency, excluding provider/user time | p95 <= 2 s, p99 <= 5 s | p95 > 3 s for 15 min | Platform IT Expert / `docs/runbooks/authentication-callback.md` |
| WAOOAW callback server-error rate; invalid/replayed caller input is reported separately | <= 0.5% over 30 days; 0.5% budget | > 1% for 10 min | Platform IT Expert / `docs/runbooks/authentication-callback.md` |
| Application-session store availability | >= 99.95% monthly; 21.6 min budget | < 99.9% over 30 min or readiness loss for 5 min | Platform Operations / `docs/runbooks/session-store.md` |
| Session lookup latency | p95 <= 50 ms, p99 <= 150 ms | p95 > 75 ms for 15 min or pool saturation > 80% for 10 min | Platform Operations / `docs/runbooks/session-store.md` |
| Refresh success for eligible sessions | >= 99.5% over 30 days; 0.5% budget | < 99% for 15 min or refresh-lease saturation > 80% for 10 min | Platform IT Expert / `docs/runbooks/session-refresh.md` |
| Provider availability and failure rate, one series per provider/environment | No WAOOAW availability budget is consumed by provider failure; provider is truthful/unavailable | > 5% failure for 10 min or readiness disagreement once | Platform Operations / `docs/runbooks/provider-disable.md` |
| Membership resolution availability and latency | >= 99.9% monthly; p95 <= 100 ms, p99 <= 250 ms | < 99.5% or p95 > 150 ms for 15 min | Business Platform owner / `docs/runbooks/membership-resolution.md` |
| Protected-operation authorization overhead | p95 <= 150 ms, p99 <= 350 ms | p95 > 225 ms for 15 min | Owning resource service / `docs/runbooks/authorization-dependency.md` |
| Security revocation propagation | <= 30 s to all Web sessions; current membership denies on the next protected operation | Any sample > 30 s or generation disagreement once | Security owner with Platform Operations / `docs/runbooks/session-revocation.md` |
| Cross-tenant false allow | Exactly 0; zero error budget | Any occurrence pages immediately and is an Emergency Stop candidate | Security owner / `docs/runbooks/cross-tenant-incident.md` |
| Provider failure isolation | 0 corruptions of another provider or existing session | Any corruption once | Platform IT Expert / `docs/runbooks/provider-disable.md` |
| Abuse limiter and bounded backpressure | >= 99.95% availability; zero unbounded queues; saturation recovers within 5 min | limiter unavailable, queue > 80% for 5 min, or any dropped security revocation | Platform Operations / `docs/runbooks/authentication-overload.md` |
| Recoverable-point currency and sanitized restore | latest recoverable point lag <= 5 min; sanitized recovery <= 30 min | recoverable-point lag > 5 min, restore drill > 30 min, or sanitization failure once | Platform Operations / `docs/runbooks/session-restore.md` |

All metrics are bounded-cardinality, carry environment/release/config/schema versions, and exclude
raw identity, tenant, handle, token, callback, or network values. Azure Monitor owns cloud alert
routing; repository fixtures prove every route and threshold before activation. Platform Operations
is the first receiver for dependency, capacity, readiness, backup, and provider pages; the named
accountable owner is always included. The existing platform error-budget rule applies: below 25%
remaining blocks feature promotion until recovery above 50%; a zero-budget security signal blocks
traffic immediately. Dashboard queries, safe synthetic probes, and a completed rehearsal are required
for every runbook. Synthetic, fixture, sandbox, Demo, UAT, and Production evidence remain explicitly
labeled.

### 23.1 Qualification Evidence And False-PASS Controls

Qualification follows the accepted Docker-only validation strategy and may report `PASS` only when
all of the following are true:

1. Every requirement is bound to a catalogued command ID, an existing selector, an immutable runner
   digest, the exact candidate/source identity, and a direct result artifact. A missing selector,
   collection error, zero collected tests, stale digest, untrusted runner, or unproved selection is
   `BLOCKED` or `FAIL`, never `PASS`.
2. The result envelope records evidence tier and class (`unit`, `contract`, `integration`,
   `browser`, `security`, `privacy`, `migration`, `recovery`, `operability`; and `fixture`,
   `synthetic`, `emulator`, `sandbox/tester`, `Demo`, `UAT`, or `Production`). Evidence may satisfy
   only the requirement and environment it directly exercises. Mock, fixture, synthetic, local, or
   sandbox evidence cannot establish provider, cloud, deployment, UAT, Production, or traffic
   readiness.
3. Skips, expected failures, quarantines, retries, flaky-pass results, and not-applicable decisions
   are enumerated by requirement and accepted authority. An unexpected pass of an expected-fail
   test, a retry-only pass, or a test with an untriggered fault/precondition cannot satisfy an
   oracle. No aggregate green status may hide a failing or missing required selector.
4. Negative tests assert both the public denial and the absence of protected state change,
   authority, evidence, disclosure, and side effect. Race tests use deterministic barriers and
   assert the committed winner, loser outcome, durable state, and post-race recovery. Outage tests
   prove the dependency fault was injected and observed, then assert bounded fail-closed behavior
   and recovery. Migration, restore, and rollback tests inspect schema, grants, generations,
   ciphertext/key compatibility, image/config digests, traffic state, and non-resurrection before
   and after the transition.
5. Accessibility evidence includes automated WCAG scans plus keyboard-only traversal, focus order
   and restoration, accessible names, status/alert live-region behavior, 200-percent zoom/reflow,
   reduced motion, touch, LTR/RTL, long-label and fallback locale checks on each required browser
   and viewport. Screenshot or axe-only evidence is insufficient.
6. The requirement index is checked for one-to-one coverage and duplicate/conflicting authority.
   Every oracle has a measurable expected result and fails when its protected behavior is
   deliberately perturbed. `NOT_APPLICABLE` requires a recorded owner decision and cannot be
   inferred from an absent test or path.

## 24. Migration, Release, And Rollback Detail

1. Extend the accepted environment manifest and secret catalog, then add the `web_session` schema,
   restricted role, versioned Key Vault references, operations, cleanup job, capacity bounds, and
   metrics with the replacement path disabled. This uses the existing application PostgreSQL,
   Redis, Key Vault, private network, Log Analytics/OpenTelemetry, migration job, and Web member of
   the architecture-indexed application and dependency topology; it creates no new workload or
   infrastructure product.
2. Add canonical BP membership-list/selection/revocation/link contracts and generated clients
   without changing the active JWT-session path.
3. Implement server-side sessions and all command/state-machine tests behind
   `WAOOAW_SERVER_SESSION_MODE=disabled|shadow|enforced`.
4. In `shadow`, create no second customer authority: compare only privacy-safe decisions using
   synthetic/approved test actors, and never authorize from the shadow result.
5. Qualify protocol, browser, storage, identity, authorization, migration, outage, concurrency,
   privacy, accessibility, and rollback oracles in local and environment-shaped Docker runners.
6. Build and attest the complete architecture-indexed application/dependency tuple once. Under
   separate deployment authority,
   promote those same image digests with a reviewed environment-specific configuration/catalog
   digest. The digest-pinned one-shot migration completes before the new Web revision becomes ready;
   liveness proves only process health, while readiness proves configuration/catalog equality,
   schema/functions/grants, current key versions, database/Redis/BP/identity-edge dependencies, and
   required observability. A failed check leaves the new revision at zero traffic.
7. Under separate activation authority, switch directly from `disabled` to `enforced` during an
   announced forced sign-out. Legacy cookies are recognized only to expire and reject them.
8. Remove legacy JWT-session creation, token projection, refresh mutation, claim-based customer
   tenant/role authority, and routine BP browser-session orchestration.
9. Prove no mixed session, tenant, or role authority is accepted before later environment promotion.
10. Demo reset/revision replacement truthfully forces all sessions out. UAT qualification proves
    restart continuity, additive-schema previous-revision compatibility, isolated PITR, the mandatory
    sanitized restore epoch, blue-green switching, and rollback before any later promotion.

Rollback after enforcement may disable new login starts and restore the prior image only if that
image is part of the immediately previous qualified architecture-indexed tuple, is compatible with the current
additive schema/configuration/key versions, has been patched to reject every invalidated legacy
session, and cannot create a browser token session. Rollback is an audited ACA traffic switch with
no rebuild, retag, secret rollback, destructive down-migration, or restore of backed-up ACTIVE
sessions. Keep the previous qualified revision at zero traffic for at least 24 hours and through the
active Demo/UAT lease. Database rollback is non-destructive; the session schema remains readable for
revocation, cleanup, forensics, and forward recovery. Any rollback that would restore browser-carried
tokens, JWT tenant/role authority, mixed sessions, retired keys, or revoked authority stops for a new
Founder decision.

## 25. Implementation Decomposition And Decision Closure

| Work Component | Outcome | Depends on |
|---|---|---|
| AUTH-WC-01 | Freeze accepted source digests; produce exact source/data/API/test/owner impact manifest and baseline negative tests. | Accepted candidate, ADR-003/008/017 |
| AUTH-WC-02 | Add canonical OpenAPI deltas, generated clients, session schema, restricted grants, encryption model, migrations, and storage tests. | 01 |
| AUTH-WC-03 | Replace browser token custody with Web-owned opaque server sessions, atomic refresh, typed callback/router, and failure handling. | 02 |
| AUTH-WC-04 | Generalize current-membership authorization, multi-membership selection, RLS context, revocation, and enabled receiver enforcement. | 02 |
| AUTH-WC-05 | Implement distinct logout, logout-all, account switch, tenant switch, security revocation, and ADR-008 Amendment 4 lifecycle sagas through the separate closed stock-Keycloak writer. | 03-04; accepted Amendment 4 |
| AUTH-WC-06 | Configure provider-neutral Google/Facebook/Apple/passkey adapters and truthful readiness projection; no provider activation. | 03, 05 |
| AUTH-WC-07 | Eliminate legacy/mixed authority, complete forced-sign-out migration, adversarial qualification, same-image evidence, runbooks, and rollback rehearsal. | 01-06 |
| AUTH-WC-08 | Real-provider Demo deployment and acceptance. **BLOCKED** pending separate provider, cloud, deployment, traffic, and activation authority. | 07 and protected gates |

Decision closure:

- `AUTHZ-SD-01`: durable stock Keycloak selected.
- `AUTHZ-SD-02`: Web BFF plus `web_session` schema in existing PostgreSQL selected.
- `AUTHZ-SD-03`: BP owns membership/authorization/evidence, not browser sessions or token custody.
- `AUTHZ-SD-04`: exact `(issuer, subject)` identity key selected.
- `AUTHZ-SD-05` and `AUTHZ-SD-06`: one ceremony and typed post-authentication router selected.
- `AUTHZ-SD-07` and `AUTHZ-SD-08`: distinct commands and proof-of-control linking selected.
- `AUTHZ-SD-09`: durable Keycloak configuration/key/provider-link continuity required.
- `AUTHZ-SD-10`: one-way forced-sign-out cutover with no legacy-session rollback selected.
- `AUTHZ-SD-11`: adopt the existing reviewed NextAuth/Auth.js OIDC client hooks inside the ADR-017
  Web boundary, but do not adopt their browser-JWT or generic database-session authority; build only
  the WAOOAW-owned `web_session` primitives and commands specified here.
- `AUTHZ-SD-12`: release qualification binds the application-image manifest and dependency manifest
  separately by named member and digest. No combined `exact-seven` count is an architecture invariant.
- `AUTHZ-SD-13`: ADR-008 Amendment 4's separate Keycloak 25.0.6 Admin REST lifecycle writer,
  exact `manage-users` grant, four-operation closed adapter, operation-bound proof, read-back,
  compensation, audit, revocation, and rollback boundary resolves `AUTHZ-GATE-01`; the WC-085 reader
  remains unchanged.
- `AUTHZ-SD-14`: AUTH-WC-03 may add only `postgres@3.4.9` at the exact registry/SRI identity in
  Section 12.8 as the Web-to-`web_session` wire client. The bounded exception preserves
  NextAuth/Auth.js `4.24.11`, PgBouncer transaction pooling, restricted function-only access, and
  the existing topology; every other dependency or database abstraction still requires amendment.
- ADR-003 conflict: resolved by its 2026-09-09 controlling customer-membership amendment; the
  historical claim-only text is not implementation authority for customer operations.
- Managed CIAM: rejected for this Work Contract. ADR-008's accepted stock-Keycloak decision controls
  over the compact 100K index's historical `Keycloak ... or Azure AD B2C` alternative; that index
  wording is not substitution authority. Reconsider only through a separately accepted enterprise
  decision and Founder acceptance.

## 26. Requirement Trace And Implementation Readiness

WC-123 is the executable Work Contract for `AUTH-WC-01` through `AUTH-WC-07`. Its requirement ledger
maps every `ER-*` requirement and every solution decision to a component, direct oracle, evidence
class, owner, and stop condition. `AUTH-WC-08` remains blocked and cannot be claimed by repository
implementation evidence.

**Implementation-readiness result:** `AUTHZ-GATE-01` RESOLVED BY ADR-008 AMENDMENT 4. No implementer
is required to choose an identity authority, session owner/store, Email method, API ownership,
state-machine result, lifecycle interface, role grant, migration mode, SLO, RPO/RTO, rollout,
rollback, or prohibited fallback. Source implementation remains blocked until the exact amended
candidate is accepted and a Platform IT Expert session receives explicit Founder implementation
authorization.

## 27. Chief Solution Architect Author Review

The author re-read the complete enterprise requirements, solution contract, WC-123, and requirement
ledger against the authorized scope, office Decision Space, accepted ADRs, implementation-readiness
standard, specialist repairs, and protected-action boundaries.

| Finding | Severity | Resolution |
|---|---|---|
| AR-01 - The initial candidate selected no application-session persistence owner. | Critical | Selected the Web BFF with exact `web_session` relations, restricted operations, existing PostgreSQL placement, lifecycle, recovery, and non-resurrection semantics. |
| AR-02 - The initial candidate left Email, API ownership, state/failure behavior, SLOs, RPO/RTO, migration, and rollback to implementation discretion. | High | Sections 9, 12, 20-24 now freeze those decisions and measurable oracles. |
| AR-03 - Security, data, platform, product, enterprise, and test concerns were incomplete. | High | Founder-authorized single-pass specialist repairs were integrated into the controlling package and ledger. |
| AR-04 - Managed CIAM was rejected for WC-123 while Section 16 still required an absent comparison. | Medium | Added the bounded weighted comparison above and retained Keycloak without claiming vendor procurement evidence. |
| AR-05 - Stock Keycloak link/unlink/recovery mutation authority was not accepted. | Resolved by bounded EA amendment | ADR-008 Amendment 4 and Section 10.1 accept the separate pinned Admin REST writer, exact role/endpoint boundary, proof, read-back/compensation, customer, audit, upgrade, stop, and rollback contract while preserving the WC-085 reader. |
| AR-06 - Qualification could falsely pass on missing selectors, lower evidence classes, aggregate status, or incomplete negative tests. | High | Added Section 23.1 and `WC123-R048` false-PASS controls. |
| AR-07 - AUTH-WC-03 had no accepted PostgreSQL protocol client although Web must call the approved `web_session` functions. | Resolved by bounded Founder amendment | Section 12.8 and `AUTHZ-SD-14` accept only exact `postgres@3.4.9`, freeze ownership/connectivity/pooling/timeouts/role/call/redaction/readiness/rollback/supply-chain controls, and prohibit adapter/ORM/schema/topology expansion. |

**Author-review result:** PASS FOR AMENDED CANDIDATE SUBMISSION. The Founder-authorized Office 04
repair resolves `AUTHZ-GATE-01`; current-session implementation authorization and protected
provider/cloud/deployment/traffic/activation decisions remain explicit external gates. This review
is self-verification, not implementation authorization, independent assurance, approval, or merge
authority.
