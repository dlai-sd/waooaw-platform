# ADR-003: JWT Claims Structure for Multi-Tenant Isolation

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Security Architect (identity and authorization) + Enterprise Architect (multi-tenancy architecture)
**Constitutional Basis:** Constitution Article VI (Three-Ledger Model — each ledger owned by a different constitutional stakeholder); Constitution Article VII (Doctrine of Institutional Independence)

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
