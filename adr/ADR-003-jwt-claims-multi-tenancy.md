# ADR-003: JWT Claims Structure for Multi-Tenant Isolation

**Status:** Accepted; WC-085 customer path amended 2026-09-09 (controlling amendment below)
**Date:** 2026-07-07
**Roles Applied:** Security Architect (identity and authorization) + Enterprise Architect (multi-tenancy architecture)
**Constitutional Basis:** Constitution Article VI (Three-Ledger Model — each ledger owned by a different constitutional stakeholder); Constitution Article VII (Doctrine of Institutional Independence)

---

## Controlling Amendment - WC-085 Customer Membership Authority (2026-09-09)

**Author:** EA INST-004, bounded Solution boundary repair, not institutional review.
**Authority:** Current Founder direction: existing C#/Python/JS stack only; standing bounded
repair/edit authority. **C-032 explicit author amendment:** for WC-085 customer requests this
supersedes the original mandatory tenant/organisation-role JWT claims, the rejection of a separate
tenant lookup per request, and the claim that membership may only restrict a signed tenant anchor.
It is a changed authorization contract, NOT fully compatible with the prior claim-only design.
Institutional, steward, service-only and ADR-023 identities retain their separate contracts; they
cannot enter this customer scheme. Historical text below applies only outside this amendment.

Keycloak remains the only customer token issuer and verifies external Google identity. BP .NET
atomically owns durable account, organisation and initial OWNER membership. Protected customer
tenant and roles derive ONLY from current authoritative membership keyed by the independently
validated exact Keycloak `(iss, sub)`. Ignore JWT `tenant_id`, `organisation_id`, `waooaw_roles`,
plan/subscription hints and all browser/body/header tenant selectors as authorization sources.
Neither a missing tenant claim nor its presence bypasses membership resolution. No app-issued JWT,
token exchange design, Keycloak runtime writer, custom Java/provider or new service is selected.

### Independent Resolution And Storage Boundary

Use `identity.resolve_customer_membership()` in the EXISTING BP PostgreSQL database. This is a
read-only storage interface, not a BP HTTP assertion and not a cross-ledger query. BP, CE, PR, WBE
and AI each use their own existing restricted service database login with EXECUTE on this exact
operation, not BP credentials or direct identity-table SELECT. Logical private result is zero or
one row: `account_id uuid`, `tenant_id uuid`, `membership_id uuid`, `roles text[]` (first slice
exactly `{OWNER}`). No provider proof, contacts, ledger data, token or expiry/revision grant is
returned. Zero/inactive/retired/ambiguous bindings deny; duplicates raise an invariant failure,
never select the latest or first row. No membership result is cached between requests.

The service authenticates the caller before setting transaction-local `app.identity_issuer` and
`app.identity_subject` from the validated token, clearing both tenant settings first. The function
takes NO caller tenant/account/subject arguments, reads the exact active actor -> active account ->
active initial organisation/membership chain, and cannot mutate it. After resolution the service
sets BOTH `app.tenant_id` and `app.current_tenant_id` to that returned tenant for its resource
transaction and checks its own resource ownership, participant, action and assurance policy.
Where resource storage uses another connection, overwrite its actor/tenant context in a fresh
transaction; never propagate pooled connection state. RLS does not itself validate JWTs or make
client-set GUCs trustworthy: each receiving service remains responsible for token validation.

The Data author must map this logical interface to a nonowner, NOLOGIN, NOBYPASSRLS read-only
function owner; fixed search path, no dynamic SQL, no PUBLIC EXECUTE, actor-scoped FORCE RLS,
no schema creation, no writes and no ledger grants. Each service retains its own ledger rights;
identity access grants neither another office's ledger reads nor institutional authority.
**C-026 remains mandatory:** ENABLE and FORCE RLS with restrictive tenant predicates on every
touched tenant table, nonowner/NOBYPASSRLS runtime roles, actor-scoped pre-account data, and
transaction-local context reset. The bootstrap lookup is actor-scoped, not a blanket RLS bypass.

For a customer-delegated internal call, propagate the ORIGINAL raw bearer JWT in `authorization`
over an authenticated, allowlisted service channel (mTLS with existing ADR-007 service identities).
Each receiver validates RS256/JWKS, exact environment customer issuer, audience containing the
existing `waooaw-platform` audience, allowed customer `azp`, times and nonempty subject; reject
machine/institutional tokens. The shared audience is deliberately accepted only on this delegated
customer scheme with the additional service/channel policy, not as a general service credential.
Validate allowed calling-service/operation pairs separately. `x-tenant-id`/`x-account-id` are never
authority; reject a supplied mismatch. CE/PR/WBE/AI then perform THEIR OWN membership lookup and
resource/participant/constitutional checks. TLS encryption without caller-service authentication,
BP-supplied decoded claims, a tenant header alone or a BP allow decision are insufficient.

Only adopted operation pairs may be enabled. Default deny unadopted REST/gRPC/WSS paths, jobs,
callbacks and background effects; a worker without current customer proof needs its separately
approved service/job authority contract, not a stored bearer or fabricated customer. A membership
read error returns dependency unavailable with no protected payload/effect; no stale fallback.
WSS reauthorizes protected messages, not just connection establishment. Existing Emergency Stop
activation authority remains separate and must not be disabled by this customer rollout.

**Qualification pending:** first check is two stable-fixture identities completing against real
PostgreSQL as restricted application roles, distinct accounts/tenants, successful tenantless-token
entry after commit, and swapped-resource/forged-tenant denial. This document reports no test run.
The exact first slice and Data handoff are in the
[WC-085 decision](../architecture/reference/product/wc085-identity-architecture-decision.md).

---

## Context

WAOOAW is a multi-tenant platform. Customer A must never see Customer B's data — employment contracts, evidence, professional interactions, or billing. This isolation must be enforced at every layer: API, service logic, and database.

The JWT issued by Keycloak is the primary bearer of tenant identity. Every service — Business Platform, Constitutional Engine, Professional Runtime, AI Runtime — must extract tenant identity from the JWT to enforce isolation.

## Decision

**Minimum required JWT claims:**

```json
{
  "sub": "user-uuid",
  "tenant_id": "org-uuid",
  "org_name": "Dr Mehta Dental Clinic",
  "roles": ["customer"],
  "iss": "https://auth.waooaw.com/realms/waooaw",
  "exp": 1234567890,
  "iat": 1234567800
}
```

**`active_contracts` is intentionally excluded from the JWT.** A JWT is issued at login and lives for its TTL. If a contract is created, amended, or terminated mid-session, the JWT does not reflect the change until token refresh — which creates a window where the token carries stale authorization. Contract membership is resolved from the database at request time using `tenant_id` as the lookup key. This is slightly slower than a JWT claim but is always authoritative.

**`tenant_id` is the multi-tenancy anchor.** It propagates through:
- HTTP Authorization header (external → Business Platform)
- gRPC metadata (service-to-service)
- PostgreSQL session variable (`SET LOCAL app.tenant_id = '...'` before every query)
- AI Runtime constitutional context (injected into every LLM prompt)

**PostgreSQL RLS enforcement:**
```sql
-- Policy on every tenant-scoped table:
CREATE POLICY tenant_isolation ON contracts
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Tenant ID in request body | Can be forgotten, inconsistent, easy to spoof in misconfigured services |
| Separate tenant lookup per request | Extra DB call per request, adds latency, can be bypassed |
| Schema-per-tenant | Correct isolation but 50%+ more expensive. Upgrade path preserved for enterprise. |

## Consequences

**Benefits:**
- Tenant isolation enforced at database level — cannot be bypassed by application bugs
- Single source of truth (JWT) propagates consistently through all layers
- Constitutional Audit Ledger entries always carry tenant_id for compliance

**Trade-offs:**
- JWT size increases slightly with active_contracts claim
- If tenant_id is omitted from a JWT (Keycloak misconfiguration), all queries would fail — this is a fail-safe behavior, not a bug

**Security note:**
- JWT is signed by Keycloak. `tenant_id` claim cannot be forged without Keycloak private key.
- Services must validate JWT signature before trusting any claim. Never trust user-supplied `tenant_id` outside the JWT.
- Contract authorization is resolved from the database, not from JWT claims, to prevent stale-token authorization bypass.

---

## Amendment — ADR-028 Extension (2026-07-19)

ADR-028 extends this decision with two new JWT claim sets. The original minimum claims remain unchanged.

### Customer JWT (extended)

```json
{
  "sub": "user-uuid",
  "tenant_id": "org-uuid",
  "org_name": "Dr Mehta Dental Clinic",
  "roles": ["customer"],
  "plan_tier": "essential | professional | enterprise",
  "subscription_id": "sub-uuid",
  "iss": "https://auth.waooaw.com/realms/waooaw",
  "exp": 1234567890,
  "iat": 1234567800
}
```

**`plan_tier`** — sourced from Keycloak user attribute `waooaw_plan_tier`, set by Business Platform
via Keycloak Admin API at subscription activation. Used by AI Runtime LLM Gateway to route
customer sessions to the correct model tier (ADR-024 + ADR-028). Default: `essential` for any
customer whose subscription record has not yet set this attribute.

**`subscription_id`** — UUID of the active subscription record in `business.subscriptions`.
Informational — authorization uses `tenant_id`, not `subscription_id`.

### Steward JWT (new — C-068)

```json
{
  "sub": "steward-uuid",
  "role": "steward",
  "person": "yogesh | sujay | ojal",
  "iss": "https://auth.waooaw.com/realms/waooaw-steward",
  "exp": 1234567890,
  "iat": 1234567800
}
```

Steward JWTs are issued by the `waooaw-steward` Keycloak client — a **separate client** from the
customer portal client with a different JWKS endpoint. This means a customer JWT signed by the
customer client keypair will fail signature verification against the steward JWKS even if it
contains `role: steward` in its claims. This is the cryptographic enforcement of C-068.

**Keycloak Protocol Mapper additions required:**
- Customer client: add `plan_tier` mapper (user attribute → JWT claim, token type: access_token)
- Customer client: add `subscription_id` mapper (user attribute → JWT claim)
- Steward client: add `person` mapper (user attribute → JWT claim, allowlist: yogesh|sujay|ojal)
