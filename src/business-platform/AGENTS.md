# AGENTS.md — Business Platform (BP) Context
# FinOps Pattern 2: Scoped context for BP subdirectory work only
# constitutional_basis: C-005 (Three-Ledger), C-038 (Pro-rata billing), C-059, C-076

## Service Identity
- **Name:** Business Platform (BP)
- **Language:** .NET 9 REST/gRPC service
- **Decision Space:** Employment contracts, billing, tenant management, user auth
- **ADR Authority:** ADR-002 (OpenAPI spec-first), ADR-003 (JWT multi-tenancy), ADR-006 (rate limiting)

## Primary Spec Files (load these — nothing else)
- `architecture/reference/components/business-platform.md`
- `architecture/reference/api-specs/business-platform.openapi.yaml`
- `standards/CODING-STANDARDS.md` §2 (.NET) + §7.5 (Coverage C-076)

## Constitutional Claims This Service Enforces
- **C-005** — Three-Ledger Model (tenant_id anchor — never merge ledgers)
- **C-009** — Rights visibility before employment (CP-001)
- **C-026** — Three-ledger separation enforced at DB level (RLS)
- **C-038** — Pro-rata billing on pause/terminate
- **C-059** — Implementation Traceability

## Test Requirements (C-076)
- **Line coverage:** ≥90% — enforced in CI
- **Branch coverage:** ≥80%
- **Multi-tenant isolation test:** Every endpoint has adversarial test (Customer A ≠ Customer B data)
- **CCT coverage:** All billing, employment, and multi-tenant endpoints

## Critical Pattern — Tenant Isolation
```csharp
// EVERY database query MUST be tenant-scoped (C-026)
// RLS enforces at DB level, but parameterized queries are defense-in-depth (OWASP A03)
var contract = await _db.QueryFirstOrDefaultAsync<Contract>(
    "SELECT * FROM business.employment_contracts WHERE tenant_id = @tenantId",
    new { tenantId = ctx.TenantId });  // Never trust headers — validate JWT claims

// NEVER: SELECT without tenant_id filter
// NEVER: tenant_id from request header without JWT validation
```
