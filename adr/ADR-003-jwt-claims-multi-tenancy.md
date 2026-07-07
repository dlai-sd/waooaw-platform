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
  "active_contracts": ["contract-uuid-1"],
  "iss": "https://auth.waooaw.com/realms/waooaw",
  "exp": 1234567890,
  "iat": 1234567800
}
```

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
- JWT is signed by Keycloak. tenant_id claim cannot be forged without Keycloak private key.
- Services must validate JWT signature before trusting any claim. Never trust user-supplied tenant_id outside the JWT.
