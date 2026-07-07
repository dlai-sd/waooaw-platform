# Work Contract 006 — Platform Architect

**Office:** Platform Architect (Office 09)
**Sprint:** 006
**Epoch:** 3 — Architecture
**Backlog Item:** IB-008 — Produce Infrastructure Architecture and Local Environment (closing out)
**Gate:** G4 / G5 trigger
**Reviewer:** Enterprise Architect

**Gate G4 contribution (for IB-008):**
> Runtime Professional can start the full local stack in one command.

**Authorized Inputs:**

| Source | Location | Purpose |
|---|---|---|
| Component Specifications | `architecture/reference/components/` | Verify all 4 services are modelled |
| Data Architecture | `architecture/reference/data/` | Verify DB users, schemas, init mount |
| ADR-008 | `adr/ADR-008-keycloak-identity-broker.md` | Keycloak version, config |
| ADR-009 | `adr/ADR-009-opentelemetry-observability.md` | OTel/Jaeger dev stack |
| ADR-015 | `adr/ADR-015-temporal-deployment-strategy.md` | Temporal self-hosted dev |
| ADR-012 | `adr/ADR-012-container-image-registry.md` | GHCR — local build vs pull |
| ADR-014 | `adr/ADR-014-secret-management.md` | .env for dev secrets |
| Office Charter | `constitution/ORGANIZATION.md` Office 09 | Decision Space and obligations |

**Authorized Outputs (already produced — this sprint closes and reviews them):**
- `docker-compose.yml` — local development stack definition
- `.env.example` — environment variable documentation

**What is NOT authorized:**
- Producing implementation code or SQL migrations (Runtime Professional scope)
- Altering component service boundaries (Solution Architect scope)
- Producing Keycloak realm JSON or postgres init SQL (IB-009 scope)

---

## Tasks

**PA-001 — Review and validate docker-compose.yml**

Verify against component specs, data architecture, and ADRs.
Produce R-006 (Enterprise Architect review of IB-008 outputs).

Status: `DONE` — R-006 produced 2026-07-07
