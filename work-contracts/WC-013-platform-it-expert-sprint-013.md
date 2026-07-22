# Work Contract 013 — IB-009 Sprint 013: Business Platform Skeleton

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 013
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5)
**Sprint Track:** Track 3 — Business Platform (PMO §2.1 M4)
**Gate:** G5
**Reviewer:** WAOOAW AI Agent — QA
**Constitutional Basis:** C-005 (Three-Ledger), C-026 (DB-level tenant isolation), C-038 (Pro-rata billing), C-059, C-065, C-076

**Depends on:** WC-012 complete (CE must be running — BP calls CE for every action)
**Authorization:** Requires `platform_phase: IMPLEMENTATION`

---

## Sprint Goal

Produce a running .NET 9 REST service for the Business Platform that:
1. Registration endpoint: POST `/api/customers` → creates tenant record
2. Employment endpoint: POST `/api/agents/hire` → calls CE.ValidateAction, creates contract
3. Billing endpoint: GET `/api/billing/usage` → returns usage units (stub)
4. JWT validation middleware running (ADR-003 tenant_id claim)
5. RLS enforced at PostgreSQL level (C-026)
6. Unit test coverage ≥90% (C-076)

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| BP component spec | `architecture/reference/components/business-platform.md` | ✅ EXISTS |
| BP OpenAPI spec | `architecture/reference/api-specs/business-platform.openapi.yaml` | ✅ EXISTS |
| ADR-002 (OpenAPI spec-first) | `adr/ADR-002-openapi-spec-first.md` | ✅ EXISTS |
| ADR-003 (JWT multi-tenancy) | `adr/ADR-003-jwt-claims-multi-tenancy.md` | ✅ EXISTS |
| ADR-006 (rate limiting) | `adr/ADR-006-api-rate-limiting.md` | ✅ EXISTS |
| DB schema (business schema) | `infrastructure/postgres/init/03-enums-and-tables.sql` | ✅ EXISTS |
| RLS policies | `infrastructure/postgres/init/04-rls-policies.sql` | ✅ EXISTS |
| WC-012 (CE running) | `src/constitutional-engine/` | ⏳ PENDING WC-012 |

**Readiness: BLOCKED** — WC-012 must complete first (CE required for BP.hire endpoint)

---

## Tasks

### WC013-01 — .NET 9 BP project scaffold + OpenAPI spec alignment

**Scope:** Create `src/business-platform/` project. Controllers match `business-platform.openapi.yaml` exactly (spec-first, ADR-002).
**model_hint:** `reasoning`
**Constitutional check:** Every endpoint must call `CE.ValidateAction` before executing (C-023).

### WC013-02 — Tenant isolation middleware + JWT validation

**Scope:** Keycloak JWT → extract `tenant_id` claim → set PostgreSQL `SET LOCAL app.current_tenant_id`. All DB queries automatically RLS-scoped.
**model_hint:** `reasoning`
**Constitutional check:** C-005 (Three-Ledger — tenants never share data), C-026 (DB-level enforcement).
**CCT gate:** CCT-MT-01 (cross-tenant isolation adversarial test)

### WC013-03 — Registration + Hire endpoints + unit tests

**Scope:** Implement POST `/api/customers` and POST `/api/agents/hire`. Write unit tests ≥90%.
**model_hint:** `reasoning`
**Constitutional check:** C-038 pro-rata billing fields populated on hire.

### WC013-04 — Schemathesis contract test suite

**Scope:** Run Schemathesis against `business-platform.openapi.yaml` on running BP service. Fix any spec-code drift.
**model_hint:** `auto`
**Constitutional check:** C-008 (Constitutional Chain — interface spec must match implementation).

---

## Definition of Done

- [ ] `docker compose up business-platform` → service starts
- [ ] Schemathesis: 0 schema violations
- [ ] Unit tests: 100% pass, ≥90% line coverage (C-076)
- [ ] CCT-MT-01: cross-tenant isolation PASS
- [ ] RLS: `SET LOCAL app.current_tenant_id` active on every request
- [ ] JWT validation: invalid token → 401, expired → 401, wrong tenant → 403

**Status:** READY when WC-012 completes
