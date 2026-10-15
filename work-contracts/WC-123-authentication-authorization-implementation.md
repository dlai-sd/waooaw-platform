# WC-123 - Authentication and Authorization Simplification Implementation

## 0. Record Control

| Field | Value |
|---|---|
| Work Contract | WC-123 |
| Version | 1.0.0-candidate.10 |
| Status | AUTHOR REVIEW PASS - AUTHZ-GATE-01 RESOLVED - IMPLEMENTATION AUTHORITY REQUIRED |
| Authorizing authority | Founder acceptance of the exact candidate plus explicit current-session implementation authorization |
| Specification office | Chief Solution Architect, Office 05 |
| Implementation office | Platform IT Expert, Office 10 |
| Required Platform IT Expert skills | Skills 1-6, 8-12, 14, 16, and 17 |
| Enterprise input | `architecture/reference/components/authentication-authorization-enterprise-requirements.md` |
| Solution input | `architecture/reference/components/authentication-authorization-simplification-solution-contract.md` |
| Requirement ledger | `work-contracts/WC-123-requirements.yaml` |
| Result | PLANNED |

This candidate does not authorize runnable code, generated implementation artifacts, dependency
changes, migrations, provider-console mutation, secrets, cloud mutation, deployment, external
traffic, activation, customer-data access, PR approval, or merge. G5 CLEAR, issue assignment, or
acceptance of this document is not current-session implementation authority.

## 1. Objective And Customer Outcome

Replace the overlapping browser JWT, Keycloak, Business Platform, token-claim, and durable-membership
authority paths with:

1. stock Keycloak as the sole customer credential and upstream identity authority;
2. one Web-BFF-owned opaque application session with all tokens in server-side custody;
3. Business Platform as the canonical customer membership and BP authorization owner;
4. current-membership, resource, assurance, and action checks at every enabled resource owner;
5. one provider-neutral authentication ceremony and typed post-authentication router;
6. distinct local logout, global logout, account switch, tenant switch, provider link/unlink,
   recovery, and security-revocation commands; and
7. a one-way forced-session cutover that cannot leave or restore mixed authority.

The customer receives deterministic login/onboarding/tenant-selection/recovery behavior, outage-safe
local logout, explicit account and tenant switching, and privacy-safe failures across every enabled
provider without provider-specific application semantics. Login never creates a registration or
account: only an explicit Register or Trial/Hire intent may enter onboarding. Existing accepted
customer presentation remains unchanged unless the exact visible change passes the gate in
Section 2.3.

## 2. Authority And Entry Gates

### 2.1 Mandatory gates before AUTH-WC-01

All must be true:

1. Founder accepts the exact enterprise requirements, CSA-AUTH-001, WC-122 package, WC-123, and
   requirement ledger.
2. Security, Data, Platform Architecture/Operations, Product, and Enterprise Architecture
   dispositions required by this candidate are accepted or recorded as blocking decisions.
3. ADR-003's 2026-09-09 controlling customer-membership amendment remains accepted; no historical
   claim-only clause is treated as current customer authority.
4. The current session receives explicit Founder authorization before any `src/`, `web/`, generated,
   migration, dependency, or build-artifact change.
5. Platform IT Expert records exact accepted source digests and produces the AUTH-WC-01 impact
   manifest before changing implementation.
6. Repository Docker runners are available and the accepted baseline authentication, tenant,
   identity, Web, and BP suites are recorded.

Failure of any gate makes all implementation components `BLOCKED`.

### 2.2 Additional gates before AUTH-WC-02

1. The impact manifest identifies every session/token/cookie/identity/membership/tenant/role/
   provider/revocation authority, data owner, migration surface, consumer, and test.
2. The selected `web_session` schema, restricted role, encryption-key lifecycle, retention, RPO,
   RTO, backup, restore, deletion, and non-resurrection controls are accepted.
3. Canonical OpenAPI changes are spec-first and consumer-mapped.
4. AUTH-WC-01 binds the architecture-indexed application-image and dependency manifests,
   application-PostgreSQL placement,
   environment manifest, closed-world secret catalog, private connectivity, existing Redis limiter
   boundary, OpenTelemetry/Azure Monitor path, migration job, and blue-green workflow. A required
   new workload, database/cache product, public data path, or manually maintained secret
   inventory stops for amendment.
5. Reviewed capacity inputs prove database connection headroom, bounded queues/concurrency, timeout
   hierarchy, overload behavior, and cost within the accepted environment envelope.

### 2.3 Additional gate before any customer-visible change

Before changing an authentication route, provider control, customer copy, ordering, layout,
styling, focus behavior, cancellation behavior, responsive behavior, or interaction:

1. the AUTH-WC-01 impact manifest identifies the exact accepted WC-105 or Fundamental Customer
   Journeys clause already authorizing that behavior;
2. Product/UX accepts an exact amendment when no clause already authorizes the change, including
   semantic copy keys, supported locales/fallback, accessibility behavior, browser/device matrix,
   screenshots or fixtures, and explicit non-goals; and
3. the current implementation session has separate explicit Founder authorization for those exact
   customer-visible paths.

Backend states and provider configuration do not imply presentation authority. A missing gate
blocks only the visible change; it does not permit an implementer to invent placeholder copy or UI.

### 2.4 Additional gates before AUTH-WC-06

1. Provider readiness projection is truthful and default-disabled for unqualified providers.
2. Email passkey bootstrap/recovery and provider-specific prerequisites have accepted, executable
   test plans.
3. Provider-console and real-account actions remain excluded.
4. Required platform readiness includes current schema/functions/grants, current key versions,
   database, shared abuse limiter, BP membership, identity edge, alert routing, and provider-specific
   feature readiness. Process liveness is never traffic readiness.

### 2.5 Additional gates before AUTH-WC-08

AUTH-WC-08 is **BLOCKED** until the Founder separately authorizes the exact provider account,
credential use, cloud mutation, deployment target, external traffic, activation window, customer
accounts, observability, rollback, incident owner, and spend boundary.

### 2.6 AUTHZ-GATE-01 before Keycloak lifecycle mutation

**Resolved by ADR-008 Amendment 4 and CSA-AUTH-001 Section 10.1.** Link, unlink, recovery, and
principal rebinding use only the separate `waooaw-bp-identity-lifecycle-writer`, stock Keycloak
25.0.6 Admin REST GET/list/POST/DELETE federated-identity surface, exact
`realm-management/manage-users` service-account grant, Platform Operations credential ownership,
separate Key Vault secret, private no-redirect route, operation-bound proof, durable idempotency,
mandatory read-back, ambiguous-outcome reconciliation/compensation, audit redaction, upgrade
qualification, revocation/emergency stop, and rollback contract accepted there.

The WC-085 `waooaw-bp-identity-reader` remains unchanged and read-only. The implementation must
acknowledge that `manage-users` is realm-wide user-management authority; it must not claim
endpoint-scoped Keycloak enforcement or use unsupported Preview fine-grained permissions. The
closed adapter authorizes only the four operations in CSA-AUTH-001 Section 10.1 and exposes no
generic Admin REST proxy. Any other endpoint, role, client reuse, custom provider/image, managed
CIAM, new route/control/copy, or scope expansion stops for a new accepted amendment.

## 3. Constitutional And Architectural Basis

WC-123 implements:

- `ER-AUTH-001` through `ER-AUTH-010`;
- `ER-PROTO-001` through `ER-PROTO-008`;
- all named `ER-PROVIDER-*`, `ER-TENANT-*`, `ER-SESSION-*`, `ER-OBS-*`, `ER-COMPAT-*`, and
  `ER-MIG-*` requirements;
- CSA-AUTH-001 Sections 1-26 and decisions `AUTHZ-SD-01` through `AUTHZ-SD-12`;
- ADR-003's controlling customer-membership amendment, ADR-008 stock broker decision, and ADR-017
  Web server-side identity boundary;
- C-023 Evidence First, C-026 tenant isolation, C-059 implementation traceability, C-063 data
  minimisation, and C-100 exact credentialed-origin behavior; and
- the accepted identity-boundary, WC-105, WC-119, and canonical OpenAPI contracts where this Work
  Contract does not explicitly replace their interim session behavior.

If an implementation detail conflicts with these sources, the higher authority wins and work stops.
The implementer does not reinterpret an enterprise requirement, revive superseded ADR text, or
invent a fallback authority.

## 4. Permitted And Prohibited Surfaces

### 4.1 Permitted roots after explicit implementation authorization

| Surface | Permitted purpose |
|---|---|
| `architecture/reference/api-specs/business-platform.openapi.yaml` | Merge accepted provider-neutral membership, selection, revocation, and provider-link contracts |
| `web/**` | Web-owned server session, callbacks, typed router, session commands, generated-client consumption, and tests; presentation integration only for exact paths and behavior passing Section 2.3 |
| `src/business-platform/**` | Current-membership APIs, authorization, revocation evidence, provider-link records, RLS context, and compatible migrations |
| Existing enabled receiver roots under `src/**` | Only the impact-manifest-listed raw-token validation, membership resolution, resource/action authorization, and RLS changes required by this contract |
| Existing PostgreSQL migration roots | Additive `web_session` schema, BP identity deltas, functions, restricted grants, RLS, indexes, cleanup, and compatibility changes |
| `tests/**` | Unit, contract, integration, security, privacy, migration, browser, concurrency, outage, and evidence tests |
| `docs/runbooks/**` | Session-store, provider-disable, key rotation, forced sign-out, incident, restore, and rollback runbooks |
| Existing identity configuration and manifests | Default-disabled provider-neutral Keycloak/configuration changes after impact analysis |
| `infra/**`, `.github/workflows/**` | AUTH-WC-08 only after separate cloud/workflow/deployment authority |

The AUTH-WC-01 impact manifest must replace root-level permission with exact changed paths before
the first implementation commit. A required path outside these roots stops for amendment.

### 4.2 Prohibited without a new Work Contract

1. A new deployable, public identity facade, database service, cache product, identity authority,
   membership store, token issuer, or browser credential mechanism.
2. Provider or Keycloak tokens in browser-readable state, a browser-carried session JWT, URL,
   telemetry, evidence, snapshot, or test artifact.
3. Provider-specific customer authorization logic in Web or Business Platform.
4. Email/phone account linking, browser/JWT tenant authority, claim-based customer roles, or a
   second steady-state session authority.
5. Changes to institutional, workload, WhatsApp, external-tool OAuth, CE, PR, AIR, WBE, billing, or
   Emergency Stop authority except exact impact-manifest-listed compatibility enforcement.
6. Provider-console, Key Vault, Azure, DNS, deployment, traffic, activation, Production, approval,
   or merge action.
7. An eighth first-party workload, new PostgreSQL/Redis/session product, public database route,
   image-baked environment value, secret value outside Key Vault, per-environment hand-written
   secret inventory, mutable deployment tag, or rebuild during promotion/rollback.
8. A new or changed authentication route, provider control/order/availability promise, customer
   string, layout, style, interaction, cancellation consequence, or onboarding step that has not
   passed Section 2.3.

## 5. Frozen Target Decisions

1. **Identity authority:** durable stock Keycloak.
2. **Application-session authority:** Web BFF.
3. **Physical session store:** Web-owned `web_session` schema in the existing PostgreSQL service;
   no new database or BP token custody.
4. **Browser state:** one random opaque `__Host-` cookie handle; no token payload.
5. **Identity key:** exact `(issuer, subject)`.
6. **Customer authorization:** current authoritative membership plus local resource/action policy;
   JWT/browser tenant and role inputs are ignored as authority.
7. **Email method:** Keycloak-owned passkey with verified-email recovery; disabled until qualified.
8. **Migration:** `disabled -> shadow -> enforced`, one announced forced sign-out, legacy sessions
   recognized only to reject/expire.
9. **Rollback:** never restores browser tokens, mixed sessions, or stale claim authority.
10. **Managed CIAM:** excluded; requires a separate enterprise decision.

## 6. No-Drift Implementation Rules

1. OpenAPI and schema changes precede handlers and generated consumers.
2. Web owns lifecycle commands; BP owns membership and BP authorization; resource owners enforce
   local policy; no layer delegates its final authorization decision to UI state.
3. Session-handle digests, refresh leases, rotations, and revocations are atomic.
4. Refresh executes once per session; reuse revokes the complete session family.
5. Every protected operation revalidates current membership or a bounded projection that meets the
   accepted freshness/revocation SLO and fails closed.
6. Every database transaction clears pooled actor/tenant context before setting validated
   issuer/subject and current tenant context.
7. Local logout expires the cookie despite IdP or store outage and never reports an authenticated
   outcome.
8. Provider readiness is configuration/evidence based; an unqualified provider cannot render as
   available.
9. Login and registration may retain separate entry copy but use one broker ceremony and router.
10. Synthetic evidence never satisfies real-provider, Demo, UAT, Production, or security acceptance.
11. Every implementation file carries the C-059 specification header required by BOOTSTRAP Step 10b.
12. Unknown, unavailable, partial, stale, collision, recovery, and revoked states never become
    success-shaped fallbacks.
13. Keycloak `(issuer, subject)` is the application principal; upstream provider
    `(issuer, subject)` remains Keycloak-owned binding data. BP never invents, substitutes, or
    duplicates either key and exposes no upstream subject.
14. Exact configured identity endpoints and safe relative return routes are server selected.
    Callback, claim, header, query, discovery, and user input can never select an outbound identity
    host, realm, key source, or post-authentication redirect.
15. Login and Register retain distinct customer intent. Login with no active account becomes an
    authenticated visitor at the accepted safe Marketplace target; only explicit Register or
    Trial/Hire intent may start/resume onboarding, and completed accounts never re-register.
16. Customer-visible errors use accepted semantic keys rather than provider/server text. They state
    whether prior authority remains, distinguish cancellation/denial/unavailability/expiry/unknown
    outcome, provide one safe action or support path, and never imply uncommitted success.

## 7. Work Component Plan

### 7.1 AUTH-WC-01 - Baseline, Impact Manifest, And Contract Freeze

**Outcome:** the exact implementation surface and accepted baseline are known without source change.

**Tasks**

1. Pin exact enterprise, solution, WC-122, WC-123, ADR, OpenAPI, migration, and baseline digests.
2. Inventory every current session/token/cookie/callback/refresh/logout/switch/provider/identity/
   membership/tenant/role/RLS/revocation path and owner.
3. List exact changed files, generated artifacts, data owners, migrations, consumers, test selectors,
   configuration keys, secret references, deployment surfaces, and rollback dependencies.
4. Map legacy creation/acceptance/removal paths and prove no unowned authority is omitted.
5. Run and record baseline Docker suites, including existing WC-085/WC-103/WC-105/WC-119 behavior.
6. Bind the accepted architecture-indexed application-image and dependency manifests, including
   Web and the existing application PostgreSQL, Redis, Key Vault, private-network, telemetry,
   migration, readiness, and blue-green surfaces plus environment manifest and secret-catalog
   schemas. Do not collapse those manifests into an invented combined image count.
7. Produce the capacity/timeout budget and prove it fits accepted database connection, replica,
   telemetry-ingestion, and environment cost limits without a new infrastructure product.

**Completion**

- Every requirement has one component and direct oracle.
- Every changed path is within Section 4 or implementation stops.
- Baseline failures are classified before implementation.
- No source, migration, dependency, generated, cloud, or provider mutation occurs.

### 7.2 AUTH-WC-02 - Canonical Contracts And Session Persistence

**Depends on:** 01.

**Outcome:** accepted API/data contracts and atomic server-side session primitives exist.

**Tasks**

1. Merge the Section 20 BP operations into canonical OpenAPI and regenerate clients.
2. Add `web_session` records for session family, handle digest, actor/global-user reference,
   encrypted token envelope, assurance/authentication time, optional active membership selection,
   exact Keycloak principal/client/`sid`, expiries, schema/deploy version, refresh lease, rotation,
   revocation generation, replay denial, and immediate token-envelope erasure state.
3. Implement exactly CSA-AUTH-001 Sections 12.4-12.6: the five named relations, keys,
   constraints/indexes, operation-owner/runtime grants, fixed search paths, no PUBLIC grants, no BP
   token access, encryption-key references, cleanup, retention, sanitized restore, and schema readiness.
4. Implement atomic create/rotate/refresh-lease/revoke-one/revoke-family/revoke-all/expire operations
   with the specified generation check, lock order, whole-transaction retry and unknown-commit
   reconciliation.
5. Add expand/mixed-version, actual-role grant/RLS, lifecycle-key, erasure, backup-age,
   sanitized-restore/non-resurrection, lock-order and concurrent-operation tests.
6. Add every WC-123 secret dependency to the single closed-world catalog with one purpose, owner,
   Web principal, Key Vault reference, cadence/expiry/overlap, compromise action, and environment
   applicability; implement dual-read/new-write rotation and blocked retirement.
7. Bind the schema to the existing application database and migration job, and add migration,
   readiness, connection-budget, cleanup/backpressure, disposable-Demo-reset, persistent-UAT-restart,
   PITR, and sanitized-restore probes.

**Completion**

- OpenAPI lint, compatibility, reference, generation, and consumer tests pass.
- Actual non-owner roles prove intended grants and denied cross-schema access.
- Concurrent rotate/refresh/revoke tests converge on the most restrictive state.
- Raw handles/tokens/PII are absent from indexes and observability.
- No new database/cache/deployable exists; actual runtime roles and private routes match the accepted
  topology, and unknown configuration/catalog fields or versions keep the revision unready.

### 7.3 AUTH-WC-03 - Web BFF Session And Authentication Router

**Depends on:** 02.

**Outcome:** Web holds only opaque browser state and one server-owned application session.

**Tasks**

1. Replace token projection in `web/lib/auth.ts` and related server helpers with opaque-handle
   lookup. Reuse the existing reviewed NextAuth/Auth.js OIDC client hooks only for protocol
   integration; do not use their JWT strategy, generic database-session authority, generated
   session schema, or browser token projection. The sole dependency-manifest exception is exact
   `postgres@3.4.9` at the registry tarball and SRI accepted by CSA-AUTH-001 Section 12.8, used only
   as the Web-to-approved-`web_session`-function protocol client. A replacement/major upgrade or any
   other dependency-manifest change stops for an accepted amendment.
2. Validate OIDC code+PKCE, exact issuer/audience/azp/redirect, state, nonce, signature, algorithm,
   time, authentication time, JWKS rotation, and callback one-time use.
3. Implement single-flight refresh, token rotation/reuse handling, session-family revocation, typed
   401 recovery, and bounded retry/redirect behavior.
4. Implement the one post-authentication router: `READY`, `AUTHENTICATED_VISITOR`,
   `ONBOARDING_REQUIRED`, `TENANT_SELECTION_REQUIRED`, `RECOVERY_REQUIRED`, or typed terminal
   failure. Bind and consume `LOGIN|REGISTER|TRIAL|HIRE` intent server-side; Login never starts
   registration, while explicit Trial/Hire resumes only its validated intent after completion.
5. Apply exact cookie, origin, CSRF, no-store, browser-cache/history, and service-worker exclusions.
6. Pin exact HTTPS discovery/authorization/token/JWKS/logout/broker endpoints and safe relative
   return-route identifiers; reject dynamic issuers, key URLs, hosts, realms, encoded redirects,
   and proxy-header influence.
7. Validate replay-safe OIDC back-channel logout and atomically map exact issuer/client/`sid` or
   subject events to affected session families.
8. Separate process liveness from internal readiness; readiness fails on schema/function/grant,
   key/catalog/config digest, mandatory database/Redis/BP/identity-edge dependency, or telemetry-route
   mismatch without exposing details publicly.
9. Enforce bounded queues, pool acquisition, dependency timeouts, per-family/global concurrency,
   overload responses, retry jitter/caps, and saturation metrics from the reviewed manifest.
10. Own one process-level PostgreSQL pool per Web replica and configure it only from
    `wc123-auth-capacity-v1`: maximum `5`, `1,000 ms` acquisition/admission, `5,000 ms` statement,
    `1,500 ms` refresh-lock, and `10,000/15,000 ms` caller budgets. Drain/close on graceful
    termination; do not create request-local pools or permit a client queue beyond the accepted
    bounded queues.
11. Connect as `web_session_app` only through the private-TLS PgBouncer transaction-pooling route
    with hostname/certificate verification and no direct/public fallback. Set `prepare: false` for
    PgBouncer compatibility, but use only tagged-template/extended-protocol parameter binding and a
    static allowlist of schema-qualified SECURITY DEFINER functions. Never interpolate identifiers,
    SQL fragments, function names, connection targets, handles, or tokens.
12. Keep raw handles/digests, tokens/envelopes, OIDC material, subjects, PII, SQL parameters, and
    connection secrets out of logs, traces, metrics, errors, query annotations, and evidence. Prove
    readiness with the restricted role and `web_session.schema_ready(...)`; dependency failure is
    private, typed, fail closed, and distinct from process liveness.
13. Record `postgres@3.4.9`, its exact tarball/SRI, resolved bytes, source/license/Node identity, and
    empty transitive runtime graph in the frozen lockfile, SBOM, and signed dependency manifest.
    Verify immutable install, registry signature, integrity, no unexpected scripts/graph, provenance
    status, license, malware/secrets, vulnerabilities, maintainer/repository identity, and Web
    compatibility. Identity, integrity, ownership, license, graph, script, or material-vulnerability
    drift stops for amendment.

**Completion**

- Browser/bundle/storage scans find no token, code, PKCE, raw callback, or protected session data.
- Fixation, replay, mix-up, refresh race/reuse, JWKS rotation, invalid callback, multi-tab,
  back-button, cache, and outage tests pass.
- No invalid session remains apparently authenticated or enters a loop.
- Restricted-role integration proves every Web call reaches only the approved functions through the
  private-TLS pool with the accepted bounds; relation/direct-route/BP-role access is denied.
- Frozen-lockfile/SBOM/dependency-manifest evidence proves exact `postgres@3.4.9` identity and SRI;
  logs/traces/errors prove no raw handle, token, protocol, parameter, secret, subject, or PII leakage.
- New/returning/completed/incomplete customers prove the Login-versus-Register intent rules,
  safe-target behavior, cancel/close no-mutation behavior, and non-secret interrupted resume.
- Cold start, scale-to-zero, saturation, limiter restart/loss, database pool exhaustion, BP/identity
  dependency recovery, and readiness flapping remain bounded and satisfy Section 23.

### 7.4 AUTH-WC-04 - Current Membership And Multi-Tenant Authorization

**Depends on:** 02.

**Outcome:** every enabled customer operation uses current membership and local resource authority.

**Tasks**

1. Implement provider-neutral membership list and selection validation in BP.
2. Remove claim/fallback customer tenant and role authority from every impact-listed path.
3. Generalize `identity.resolve_customer_membership()` and transaction-local issuer/subject/tenant
   setup under restricted roles without pooled-context leakage.
4. Enforce exact token validation, current membership, assurance, resource ownership, action policy,
   RLS, idempotency, Evidence First, and Emergency Stop independently.
5. Enable only adopted receiver operation pairs; deny unsupported jobs, callbacks, WSS messages, and
   service calls by default.

**Completion**

- Zero/one/many membership and tenant-selection tests pass.
- Removed/suspended/role-reduced membership denies on the next protected operation.
- Forged tenant/role/header/body/resource inputs and cross-tenant swaps deny at API and RLS layers.
- Existing institutional, service, workload, WhatsApp, and tool-OAuth identities remain isolated.

### 7.5 AUTH-WC-05 - Lifecycle Commands, Linking, And Recovery

**Depends on:** 03-04 and accepted ADR-008 Amendment 4 / CSA-AUTH-001 Section 10.1.

**Outcome:** every lifecycle command has distinct scope, state transition, race behavior, and evidence.

**Tasks**

1. Implement local logout, logout-all, account switch, tenant switch, revoke-one, revoke-all,
   provider link, provider unlink, security revocation, and recovery as separate commands.
2. Serialize link/unlink on exact identity and global-user keys; require fresh proof and preserve one
   usable method.
3. Normalize collision/recovery without email linking or account disclosure.
4. Make revocation dominate callback, refresh, rotation, switch, link, and recovery races.
5. Emit privacy-safe, correlated evidence and one deterministic customer next action.
6. Implement link/unlink/recovery as a durable idempotent Keycloak-authoritative saga with operation
   identity, proof state, IdP commit/read-back, BP projection confirmation, ambiguous-outcome
   reconciliation, and explicit compensation or `RECOVERY_REQUIRED`; never blind-retry an unknown
   provider mutation.
7. Require operation-bound step-up with accepted `acr`/`amr`, `auth_time` at most five minutes old,
   one-time proof, and mandatory session rotation/revocation after link, unlink, recovery, tenant,
   membership/role, or authority change.
8. Persist only the exact `identity.lifecycle_operations` and
   `identity.provider_link_projections` contract in CSA-AUTH-001 Section 12.5, using actor-scoped
   FORCE RLS, immutable key reservation, deterministic lock order, restricted grants, and no
   upstream provider subject or contact data.
9. Make account-switch cancellation/provider failure end truthfully unauthenticated after prior
   session revocation, with no stale account content. Make tenant-switch cancellation, stale
   selection, and dependency failure preserve the existing selection and expose no unauthorized
   membership option.
10. For provider link, unlink, recovery, or principal rebinding, use only the accepted separate
    `waooaw-bp-identity-lifecycle-writer` and exact four-operation contract in ADR-008 Amendment 4
    and CSA-AUTH-001 Section 10.1. Never reuse or broaden the WC-085 reader, add another endpoint or
    role, expose a generic proxy, claim unsupported endpoint-scoped enforcement, or add a custom
    provider/image.

**Completion**

- Keycloak/provider/store outages do not prevent local logout.
- Same/different/cross-provider account-switch, cancellation, and stale-session tests pass.
- Link/unlink collision, concurrency, last-method, changed-email, and Apple-relay tests pass.
- Rollback/restore cannot resurrect revoked sessions or retired bindings.
- Partial/unknown IdP outcomes never return success, duplicate a binding, or leave BP and Keycloak
  disagreement usable; old sessions deny after every identity or authority transition.

### 7.6 AUTH-WC-06 - Provider-Neutral Configuration And Readiness

**Depends on:** 03 and 05.

**Outcome:** Google, Facebook, Apple, and Email share one application contract with truthful,
independent readiness.

**Tasks**

1. Replace provider-specific cross-provider adapter naming/branches with the normalized verified-
   identity adapter contract.
2. Preserve provider-specific behavior only in Keycloak/configuration adapters.
3. Configure Google ordinary SSO and account selection only for explicit switching/recovery.
4. Add default-disabled Apple, Facebook, and passkey Email manifests and validation rules.
5. Prove one provider failure cannot damage another provider or an existing application session.
6. Store atomic abuse counters only in the accepted existing Redis boundary using keyed digests and
   TTLs; prove unavailable/restart-epoch fail-closed behavior and no session/revocation authority.
7. Preserve the accepted WC-105 four-control projection and approved copy/order. Configuration,
   synthetic evidence, or an `AVAILABLE` backend state cannot enable or visibly alter a provider
   unless the exact provider activation and Section 2.3 gates pass.

**Completion**

- Readiness projection exactly matches accepted environment evidence.
- No provider-specific customer account semantics exist in Web/BP authorization.
- Synthetic provider contract tests pass.
- No real-provider readiness, activation, or deployment is claimed.
- Disabled, pending, unavailable, and failed readiness remain truthful, keyboard/screen-reader
  understandable, localized through accepted keys, and isolated per provider without UI invention.

### 7.7 AUTH-WC-07 - Legacy Removal And Integrated Qualification

**Depends on:** 01-06.

**Outcome:** one immutable candidate proves the replacement model and one-way cutover.

**Tasks**

1. Remove legacy browser token-session creation, mutation, and acceptance.
2. Remove routine BP browser-session orchestration and every impact-listed claim-based customer
   tenant/role fallback.
3. Implement `disabled|shadow|enforced`; shadow is non-authoritative and uses approved test actors.
4. Execute protocol, browser, identity, provider-contract, onboarding, session, logout, switch,
   tenant, authorization, privacy, accessibility, operations, migration, and rollback suites.
5. Rehearse announced forced sign-out, legacy-cookie rejection, same-image environment-shaped
   qualification, backup/restore, key rotation, revocation, incident response, and rollback.
6. Produce redacted requirement evidence and runbooks.
7. Build/attest the complete architecture-indexed application/dependency tuple once and qualify the
   same image digests with reviewed
   per-environment configuration/catalog digests, pre-traffic migration, internal readiness,
   blue-green switch, 24-hour/lease rollback hold, and no rebuild/retag/down-migration.
8. Execute every Section 23 metric, alert route, error-budget response, dashboard query, synthetic
   probe, and exact runbook; rehearse overload/backpressure, key/secret rotation and compromise,
   Demo reset, UAT restart/PITR/sanitized restore, and provider/session dependency incidents.
9. Execute the accepted auth journey on Chromium, Firefox, and WebKit at 360x800, 768x1024, and
   1440x900, including touch, keyboard-only, screen reader semantics, 200% text zoom, reduced
   motion, LTR, RTL, one long-label locale, and reviewed-English fallback. Test Login/Register
   intent, cancellation, recovery, account switch, tenant switch, and provider readiness without
   changing accepted presentation.

**Completion**

- No legacy or mixed application-session, tenant, or role authority remains accepted.
- One immutable architecture-indexed application/dependency image tuple passes all repository-owned
  oracles.
- SLO, alert, runbook, RPO/RTO, migration, restore, and rollback evidence passes.
- Author review finds no unresolved critical/material gap.
- Release inventory matches the separately indexed application and dependency manifests; Web
  session delivery adds no new workload or infrastructure product, and telemetry/cost remain
  within accepted bounds.

### 7.8 AUTH-WC-08 - Real-Provider Demo Deployment And Acceptance

**Depends on:** 07 and every Section 2.5 gate.

**Status:** **BLOCKED**.

After separate authority, deploy the exact AUTH-WC-07 architecture-indexed tuple, configure only the authorized providers
and accounts, execute real Google/Apple/Facebook/Email qualifications independently, capture
redacted evidence, verify alerts and rollback, and leave activation in the exact authorized state.
Repository implementation cannot mark this component complete.

## 8. Data, Migration, And Recovery Contract

1. `web_session` is logically Web-owned and physically hosted in the existing PostgreSQL service.
2. Browser handles are random; only keyed digests persist. Token envelopes are versioned and
   encrypted with environment/purpose-separated keys.
3. Session records contain no raw email, phone, provider subject, callback, or tenant display value.
4. Active membership selection is an opaque convenience reference and never an authorization fact.
5. BP membership remains canonical; session selection is revalidated before change and every
   protected operation reauthorizes current membership.
6. Migration is expand/verify/cutover/contract. Legacy sessions are invalidated, never transformed
   into replacement authority.
7. Cleanup is lease-safe and idempotent. Backup/restore preserves encryption and environment
   isolation and cannot resurrect revoked/expired/superseded/erased/legacy authority.
8. Retention, backup, RPO, RTO, and deletion use CSA-AUTH-001 Section 12 until a stricter accepted
   data policy replaces them.
9. Failed migration or key dependency blocks readiness and new protected sessions; it never falls
   back to browser tokens or claim authority.
10. Revoke, logout, expiry, supersession, unlink, recovery, and account deletion immediately erase
    token envelopes and upstream-session material; retained rows contain only replay/reconciliation
    state. Digest/encryption-key compromise revokes affected families, and key retirement cannot
    make live ciphertext unreadable.
11. Restores are traffic-isolated and always run the Section 12.6 restore epoch before runtime
    credentials are enabled: increment generations, revoke all restored sessions, erase all restored
    token/protocol material and leases, validate constraints/grants/RLS, and retain a manifest.
    Restore cannot claim session continuity; failure leaves the store offline.
12. CSA-AUTH-001 Section 12.7 fixes physical placement and environment behavior: Demo uses disposable
    application PostgreSQL and forces reauthentication on every reset; UAT uses persistent
    application PostgreSQL and proves PITR plus sanitized restore; Production remains separately
    sized, HA-decided, and activation-gated.
13. Session, replay, envelope, OIDC-client, and provider secrets are entries in the one accepted
    environment secret catalog, consumed by Web managed identity through Key Vault references.
    Rotation is read-old/write-new with one writer, at most two readers, and at most 24 hours overlap;
    retirement blocks on live dependency, and compromise revokes/erases affected families.
14. Existing Redis may contain only keyed, TTL-bounded abuse counters. It is not session or
    revocation authority. Limiter loss or restart closes high-risk identity routes for the longest
    quota window; it never resets callers to unlimited access.

## 9. Security And Privacy Acceptance

Direct adversarial tests must cover:

1. wrong issuer/audience/azp/algorithm/key/time/nonce/state/code-verifier/redirect and mix-up/replay;
2. login CSRF, command CSRF, hostile Origin/Fetch-Metadata, fixation, cookie tamper, history/cache,
   multi-tab, concurrent refresh, refresh reuse, callback/logout/revocation races;
3. forged/stale tenant, role, membership, account, resource, session, provider, assurance, and
   delegated-service inputs;
4. cross-account/tenant/resource enumeration by status, body, latency class, telemetry, and count;
5. link/unlink collision, email equality, Apple relay change, last-method removal, recovery takeover,
   and concurrent identity mutation;
6. seeded tokens, codes, cookies, PKCE, callback queries, subjects, email/phone, tenant references,
   secrets, and stack detail across every prohibited observability/evidence/browser surface;
7. database role crossover, RLS bypass, pooled-context reuse, dynamic search path, PUBLIC grants,
   backup/export leakage, wrong-key restore, and revoked-session resurrection;
8. provider outage/isolation, session-store outage, membership-store outage, JWKS/key rotation,
   partial migration, mixed version, rollback, and recovery; and
9. Emergency Stop and security revocation racing every session and authorization transition.
10. dynamic discovery/JWKS/logout endpoint injection, hostile forwarded-host/proto chains, DNS or
    redirect rebinding, back-channel logout forgery/replay/wrong-`sid`, and unsafe return routes;
11. distributed abuse-limit concurrency, IPv6/proxy normalization, limiter outage, spray,
    enumeration, resend/recovery amplification, and quota bypass; and
12. partial/unknown Keycloak link/unlink/recovery outcomes, IdP/BP projection disagreement,
    operation-proof replay, stale `auth_time`, wrong `acr`/`amr`, and old-session reuse.

Any cross-tenant false allow, browser-readable token, silent account link, mixed authority,
revocation resurrection, or success-shaped dependency failure is release blocking.

## 10. Operability And Evidence

Implementation must satisfy every numeric SLI/SLO, alert, owner, runbook, retention, RPO, and RTO in
CSA-AUTH-001 Sections 12 and 23. Evidence distinguishes unit, integration, synthetic, emulator,
provider sandbox/tester, real Demo, UAT, and Production classes.

AUTH-WC-01 must create an operability manifest mapping each Section 23 SLI to its metric/query,
threshold, Azure Monitor route, accountable and first-response owners, exact runbook path, safe
synthetic probe, evidence selector, and error-budget action. AUTH-WC-07 executes every threshold and
routing fixture plus runbook, key rotation, overload, backup, restore, and incident rehearsals.
Missing files, receiver routes, or rehearsals are failures, not deferred operations work.

Runtime capacity configuration includes Web maximum replicas, per-replica database pool,
migration/operations reserve, database connection limit, bounded request/refresh/lifecycle queues,
per-family/global concurrency, and dependency timeouts. Qualification proves the Section 12.7
80-percent connection ceiling, bounded `429`/`503` rejection, no retry storm, recovery within SLO,
and no lost revocation before traffic.

Evidence root is `test-results/wc123/<component-or-requirement>/` or the repository-standard
ephemeral equivalent selected by AUTH-WC-01. Evidence contains exact source/image/schema/config
digests and redacted results, never credentials, tokens, personal data, or protected callbacks.

## 11. Docker-Only Validation Plan

AUTH-WC-01 must bind exact repository-native selectors after impact analysis. The following
baseline command candidates name paths that exist before WC-123 implementation; they record
starting behavior but cannot qualify the replacement design. They are not evidence until runner
supply and command feasibility pass the preflight below:

```bash
docker compose --profile test-python run --rm test-runner-python pytest -q \
  tests/test_openapi_slice.py \
  tests/validation_control/test_spec_lint_scope.py \
  tests/identity-foundation \
  tests/pipeline/test_auth_preview.py
```

```bash
docker compose --profile test-dotnet run --rm test-runner-dotnet \
  dotnet test tests/business-platform.Tests/business-platform.Tests.csproj \
  --filter "FullyQualifiedName~Identity|FullyQualifiedName~CustomerMembershipMiddleware|FullyQualifiedName~TenantDbConnectionInterceptor"
```

```bash
docker compose --profile test-ts run --rm test-runner-ts \
  pnpm --dir web test -- \
  lib/auth.test.ts \
  lib/server-auth.test.ts \
  lib/auth-transition.test.ts \
  components/auth/AuthBoundary.test.tsx \
  components/auth/AuthJourney.test.tsx \
  components/auth/AuthViews.test.tsx \
  components/auth/AuthSessionProvider.test.tsx \
  components/auth/AuthDialog.test.tsx
```

```bash
docker compose --profile test-ts run --rm test-runner-ts \
  pnpm --dir web exec playwright test tests/e2e
```

AUTH-WC-01 must replace or extend these commands with catalogued candidate selectors that exist
before they are invoked. Focused selectors must be added for protocol, callback, browser storage, session persistence,
refresh/revocation concurrency, lifecycle commands, membership/RLS, provider isolation, migration,
restore, accessibility, localization, supported Chromium/Firefox/WebKit viewport/device behavior,
cancellation, semantic error copy, and same-image qualification. Host-language results are non-authoritative.
Planned or absent paths are not executable commands and cannot be recorded as evidence.

For every baseline and candidate command, feasibility requires the exact supplied runner digest to
resolve all pinned dependencies without host installation, use only writable declared cache/output
mounts, parse the command, collect a nonzero expected selector inventory, and emit its native
artifact plus common envelope. Runner dependency-resolution failure, a restore/build attempt
against the read-only source mount, missing browser binaries/services, or a selector whose expected
inventory differs is `BLOCKED`. AUTH-WC-01 must record and clear such a runner/control-plane defect
before using the command as a baseline or completion oracle; substituting a host command or a
broader aggregate suite is prohibited.

Every command must emit the repository structured result envelope and native artifacts. A nonzero
exit, collection error, zero tests, missing artifact, missing/stale identity, unexpected skip/xpass,
quarantine, unaccepted retry-only pass, untriggered fault, or omitted required selector is `FAIL` or
`BLOCKED`, never `PASS`. Evidence must state tier and class and obey CSA-AUTH-001 Section 23.1.
Negative, race, outage, migration, restore, rollback, and accessibility selectors must prove their
preconditions and inspect both visible output and protected durable side effects; mocks, axe scans,
screenshots, or aggregate coverage alone do not satisfy those oracles.

## 12. Requirement-To-Component Trace

| Component | Enterprise and solution scope |
|---|---|
| 01 | All current findings, `ER-MIG-002`, `ER-COMPAT-004`, source/owner/consumer inventory |
| 02 | `ER-AUTH-003`, `ER-SESSION-001`-`012`, API/data/encryption/recovery contracts |
| 03 | `ER-AUTH-001`, `003`, `007`, `010`; `ER-PROTO-001`-`008`; callback/router/browser/session behavior |
| 04 | `ER-AUTH-004`-`006`; `ER-TENANT-001`-`011`; `ER-COMPAT-001`-`008` |
| 05 | `ER-AUTH-002`, `008`-`010`; lifecycle, linking, recovery, revocation, collision |
| 06 | all `ER-PROVIDER-*`; provider-neutral boundary and readiness |
| 07 | all `ER-OBS-*`, `ER-MIG-*`, mandatory acceptance evidence, legacy removal, SLO/rollback |
| 08 | separately authorized real-provider, deployment, external-traffic, and activation evidence |

The machine-readable ledger supplies exact requirement-to-oracle ownership. No enterprise
requirement may remain ownerless or be satisfied only by a documentation assertion.

### 12.1 Canonical Ledger Requirement Index

The following IDs are the canonical WC requirements consumed by
`scripts/validate_requirement_ledger.py`; their complete source, owner, outcome, oracle, completion,
dependency, evidence-class, rollback, and residual-risk fields are in the ledger.

| Requirement ID | Ledger authority |
|---|---|
| WC123-R001 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R002 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R003 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R004 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R005 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R006 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R007 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R008 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R009 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R010 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R011 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R012 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R013 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R014 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R015 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R016 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R017 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R018 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R019 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R020 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R021 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R022 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R023 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R024 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R025 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R026 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R027 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R028 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R029 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R030 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R031 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R032 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R033 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R034 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R035 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R036 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R037 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R038 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R039 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R040 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R041 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R042 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R043 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R044 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R045 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R046 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R047 | `work-contracts/WC-123-requirements.yaml` |
| WC123-R048 | `work-contracts/WC-123-requirements.yaml` |

## 13. Milestones And Commit Discipline

Each AUTH-WC component is a milestone:

1. complete only after its direct Docker-owned oracles pass;
2. commit component-owned changes with repository conventional format and required co-author trailer;
3. record exact paths, tests/results, schema/image/config digests where applicable, rollback, and
   residual risk;
4. update the required institutional checkpoint after the milestone commit;
5. do not start a dependent component while a prerequisite is failing or blocked; and
6. never represent planned, local, synthetic, or disabled-provider evidence as live acceptance.

## 14. Rollback

1. Before enforcement, set the replacement path to `disabled`; no customer authority may depend on
   a shadow result.
2. After enforcement, stop new authentication starts if safe operation cannot continue.
3. Restore only a candidate that rejects legacy browser sessions and claim-based customer authority.
4. Preserve session-revocation records, identity bindings, membership truth, immutable evidence,
   read/reconcile/data-rights/Stop paths, and forward migration capability.
5. Do not down-migrate session or identity data destructively.
6. Reconcile unknown callback, refresh, link, unlink, revocation, and provider outcomes by their
   original transaction/correlation identity before retry.
7. Rollback requiring browser-carried tokens, mixed sessions, stale tenant/role claims, or revoked
   authority restoration stops for a new Founder decision.
8. Rollback uses only the immediately previous qualified architecture-indexed tuple and its compatible
   reviewed configuration/key versions, retained at zero traffic for at least 24 hours and through
   the active lease. It never rebuilds, retags, runs a destructive down-migration, or trusts restored
   ACTIVE session state.

## 15. Mandatory Stop Conditions

Stop the applicable component when:

1. an accepted source digest, authority, owner, ADR interpretation, or component boundary differs;
2. implementation requires a path outside the exact impact manifest or a prohibited surface;
3. a new identity/session/membership authority, deployable, database service, or public facade is
   required;
4. OpenAPI compatibility or generated-client migration cannot be bounded;
5. session-store role isolation, encryption, atomicity, RPO/RTO, restore, or non-resurrection cannot
   be proved;
6. current membership or RLS requires browser/JWT tenant or role authority;
7. any callback, refresh, logout, switch, link, recovery, revocation, provider, or dependency failure
   can return authenticated/authorized success;
8. a token, credential, code, raw callback, identity key, or personal field reaches a prohibited
   surface;
9. a provider requires unaccepted console/credential/cloud action or unsupported stock-Keycloak
   behavior;
10. migration or rollback can accept legacy/mixed authority or resurrect revocation;
11. an SLO, alert, runbook, evidence owner, or acceptance oracle is absent; or
12. provider, cloud, deployment, traffic, activation, Production, approval, or merge authority is
    missing.
13. liveness is used as readiness; schema/key/catalog/config/dependency checks are missing; queues,
    retries, pools, or concurrency are unbounded; or connection/cost/telemetry capacity exceeds its
    accepted budget; or
14. promotion changes an image digest, migration is not pre-traffic/additive, the previous qualified
    tuple cannot read the current schema/key versions, or rollback would rebuild, retag, down-migrate,
    restore ACTIVE sessions, or retire a still-required key.
15. a customer-visible change lacks its exact accepted behavior/copy/localization/accessibility
    contract or Section 2.3 authority; a provider readiness state would silently enable or alter a
    control; or Login would create registration/onboarding without explicit customer intent.
16. Web uses any PostgreSQL package other than exact `postgres@3.4.9`, the tarball/SRI or resolved
    graph differs, supply-chain evidence is absent or materially adverse, the client bypasses
    private-TLS PgBouncer/`web_session_app`, pooling/timeouts exceed `wc123-auth-capacity-v1`,
    statement preparation is enabled against transaction pooling, a call is not parameterized and
    statically function-allowlisted, table/direct-role access exists, or observability contains raw
    session/protocol/database material.

## 16. Definition Of Done

WC-123 repository implementation is complete only when:

1. AUTH-WC-01 through AUTH-WC-07 pass on one exact candidate;
2. every ledger requirement is `PASS` with direct redacted evidence and no unresolved blocker;
3. canonical OpenAPI and generated consumers are compatible;
4. browser storage contains only the opaque cookie handle and no credential/token material;
5. exactly one application-session authority and one current-membership authorization path remain;
6. protocol, browser, identity, provider-contract, onboarding, session, lifecycle, tenant,
   authorization, privacy, accessibility, operations, migration, restore, and rollback suites pass;
7. numeric SLO, RPO/RTO, alert, runbook, and same-image evidence pass;
8. no legacy or mixed session/tenant/role authority is accepted;
9. author review finds no unresolved critical or material defect;
10. the PR uses the repository template and exact precheck output;
11. the Founder receives the completed unmerged PR for review; and
12. AUTH-WC-08 remains explicitly `BLOCKED` unless separately authorized and completed; and
13. accepted Login/Register/onboarding intent, cancellation, account/tenant switching, semantic
    error, provider-readiness, accessibility, localization, and supported browser/device journeys
    pass without unapproved route, copy, control, or interaction changes.

## 17. Explicit Non-Authorization

Nothing in WC-123 authorizes implementation before explicit current-session Founder permission,
provider-console or credential use, Azure/cloud mutation, DNS, deployment, external traffic,
activation, real-account testing, customer-data access, Production action, PR approval, or merge.

## 18. Author Review

The Chief Solution Architect re-read the complete enterprise requirements, solution contract,
WC-123, and requirement ledger after the Founder-authorized Security, Data, Platform
Architecture/Operations, Product, Enterprise Architecture, and Test Champion repair passes.

The review checked requirements coverage, authority, component ownership, exact interfaces, state
and failure behavior, data keys and lifecycle, security/privacy/abuse controls, customer intent and
accessibility, operability, migration, rollback, evidence classification, false-PASS prevention,
and implementation discretion.

**Findings and dispositions**

1. Missing session-store, data, API, SLO, recovery, and cutover decisions were repaired in
   CSA-AUTH-001 and Components 01-07.
2. Browser token custody, mixed tenant authority, account linking by email, unsafe rollback, and
   lower-class evidence are directly prohibited and testable.
3. Customer-visible changes are separately gated; backend/provider state cannot silently authorize
   presentation.
4. Managed CIAM comparison is closed for this bounded contract with stock Keycloak retained.
5. ADR-008 Amendment 4 and CSA-AUTH-001 Section 10.1 now bind the exact stock-Keycloak lifecycle
   mutation client, role, endpoints, proof, read-back/compensation, customer, audit, upgrade, stop,
   and rollback contract. `WC123-R029` and `WC123-R047` are planned implementation requirements,
   not architecture-blocked rows.
6. CSA-AUTH-001 Section 12.8 and `AUTHZ-SD-14` repair AUTH-WC-03's missing database client decision
   by accepting only exact `postgres@3.4.9` with function-only restricted-role access, private TLS,
   capacity-profile bounds, redaction, readiness/rollback, and supply-chain evidence.

**Author-review result:** PASS FOR AMENDED CANDIDATE SUBMISSION. `AUTHZ-GATE-01` is resolved.
Explicit current-session implementation authority and the protected provider, cloud, deployment,
traffic, activation, approval, and merge gates remain blocking. This is self-verification, not
implementation authorization, approval, or independent assurance.
