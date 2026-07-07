# R-006 — Enterprise Architect Review of Sprint 006 (Platform Architect — IB-008)

**Review ID:** R-006
**Reviewer Office:** Enterprise Architect
**Subject:** IB-008 — Infrastructure Architecture and Local Environment (docker-compose.yml + .env.example)
**Produced by:** Platform Architect (WC-006, Sprint 006)
**Date:** 2026-07-07

---

## Review Purpose

The Enterprise Architect verifies:
1. All containers from the Reference Architecture are present in the compose file
2. Service dependencies are ordered correctly — no service starts before its dependency is healthy
3. Technology versions align with ratified ADRs
4. Environment variable model is consistent with ADR-014 (secret management)
5. Observability configuration matches ADR-009
6. The infrastructure specification is sufficient for the Runtime Professional to begin IB-009

---

## Overall Verdict: APPROVED WITH TWO NOTES

The docker-compose.yml correctly models the complete local development stack. All services are present, healthchecks are defined on critical paths, ADR-ratified versions are used, and the observability configuration is consistent. Two notes are raised — neither blocks IB-008 closure, but both must be resolved during IB-009.

---

## Service Coverage Assessment

| Container (Reference Architecture) | Present in compose | Port correct | Healthcheck |
|---|---|---|---|
| Business Platform (.NET 9) | ✓ `business-platform` | ✓ 5001 | ✓ `/health` HTTP |
| Constitutional Engine (.NET 9) | ✓ `constitutional-engine` | ✓ 5002 | ✓ `grpc_health_probe` |
| Professional Runtime (Python) | ✓ `professional-runtime` | ✓ 5003 | ✓ `/health` HTTP |
| AI Runtime (Python) | ✓ `ai-runtime` | ✓ 5004 | ✓ `/health` HTTP |
| PostgreSQL 16 + pgvector | ✓ `postgres` | ✓ 5432 | ✓ `pg_isready` |
| Keycloak | ✓ `keycloak` | ✓ 8443→8080 | ✓ `/health/ready` HTTP |
| Temporal (self-hosted dev) | ✓ `temporal` | ✓ 7233 | — (see Note 1) |
| Temporal UI | ✓ `temporal-ui` | ✓ 8080 | — (non-critical) |
| Jaeger (OTel collector + UI) | ✓ `jaeger` | ✓ 16686 / 4317 / 4318 | — (non-critical) |
| Next.js Web App | ✓ `web` | ✓ 3000 | — (see Note 2) |

All 10 containers present. ✓

---

## ADR Compliance Check

### ADR-008 — Keycloak identity broker

- Image: `quay.io/keycloak/keycloak:25.0.6` ✓ — version pinned as required by ADR-008
- `--import-realm` command ✓ — mounts `./infrastructure/keycloak` for realm import (Runtime Professional must produce realm JSON in IB-009)
- Uses Keycloak's internal PostgreSQL connection: `KC_DB=postgres`, correct schema separation via `KC_DB_SCHEMA: keycloak` ✓
- Realm name: `waooaw` — consistent with `business-platform` environment variable `Keycloak__Authority: http://keycloak:8080/realms/waooaw` ✓

### ADR-009 — OpenTelemetry observability

- Jaeger `all-in-one:1.58` with `COLLECTOR_OTLP_ENABLED: "true"` ✓
- OTLP gRPC port 4317 exposed ✓
- OTLP HTTP port 4318 exposed ✓ (fallback for services that do not support gRPC OTLP)
- All 4 application services carry `OTLP_ENDPOINT: http://jaeger:4317` ✓
- Pattern matches ADR-009: "Dev: `OTLP_ENDPOINT=http://jaeger:4317`" ✓

### ADR-015 — Temporal self-hosted dev

- Image: `temporalio/auto-setup:1.24` ✓ — matches ADR-015 specification
- `DB: postgresql` + `POSTGRES_SEEDS: postgres` ✓ — shares platform PostgreSQL in dev per ADR-015
- Temporal UI image `temporalio/ui:2.26` included ✓

**Minor variance from ADR-015:** ADR-015 specifies a dedicated `temporal` PostgreSQL user (`POSTGRES_USER: temporal`, `POSTGRES_PWD: ${TEMPORAL_DB_PASSWORD}`). The compose file uses the main `waooaw` superuser with `${POSTGRES_PASSWORD}`. This is acceptable in dev — the `waooaw` user has the required privileges. The Runtime Professional should note that production/cloud deployments require a dedicated Temporal DB user. `.env.example` should document `TEMPORAL_DB_PASSWORD` for environments that use a separate user.

### ADR-012 — Container image registry (GHCR)

- All 4 application services use `build: context:` (local build) ✓ — correct for dev. Production images are pulled from GHCR (CI/CD concern, not local dev concern). ✓

### ADR-014 — Secret management (.env for dev)

- All secrets use `${VAR}` substitution from `.env` file ✓
- No secrets are hardcoded ✓
- `.env.example` documents all required variables ✓

---

## Dependency Ordering Assessment

Start order derived from `depends_on` conditions:

```
postgres (healthcheck: pg_isready)
    ↓
keycloak (healthcheck: /health/ready) ──────── temporal (service_started)
    ↓                                               ↓
constitutional-engine (healthcheck: grpc)      temporal-ui
    ↓
business-platform (healthcheck: /health)
    ↓
professional-runtime (healthcheck: /health)

postgres → ai-runtime (healthcheck: /health)
postgres → jaeger (no wait)
```

This ordering is correct:
- Constitutional Engine starts before Business Platform ✓ (BP calls CE gRPC on startup — healthcheck ensures CE is ready)
- Keycloak starts before Business Platform ✓ (BP validates JWTs against Keycloak JWKS endpoint)
- Professional Runtime starts after Business Platform ✓ (PR submits proposed actions to BP)
- AI Runtime only needs postgres (for pgvector) — no application dependency ✓

---

## Database User Configuration

The compose file uses three distinct database connection strings mapping to the three application users defined in `ledger-design.md`:

| Service | DB User | Permissions (per ledger-design.md) |
|---|---|---|
| `constitutional-engine` | `constitutional_app` | INSERT/SELECT on constitutional; SELECT on business and professional |
| `business-platform` | `business_app` | SELECT/INSERT/UPDATE/DELETE on business; SELECT on constitutional |
| `professional-runtime` | `runtime_app` | SELECT on business |
| `ai-runtime` | `runtime_app` | SELECT on business (+ pgvector read — see Note 3) |

The user separation correctly enforces that the Constitutional Engine is the only service that writes to the constitutional schema. ✓

---

## .env.example Assessment

| Variable | Present | Notes |
|---|---|---|
| `POSTGRES_PASSWORD` | ✓ | Single password for all DB users in dev — acceptable |
| `KEYCLOAK_ADMIN_PASSWORD` | ✓ | |
| `KEYCLOAK_CLIENT_SECRET` | ✓ | |
| `LLM_PROVIDER` | ✓ | Default: openai |
| `LLM_API_KEY` | ✓ | |
| `LLM_MODEL` | ✓ | Default: gpt-4o-mini |
| Azure OpenAI alternatives | ✓ | Commented out |
| `TEMPORAL_CLOUD_*` | ✓ | Commented out — for cloud environments |
| `GHCR_PAT` | ✓ | Commented out — for pulling images in cloud |
| `TEMPORAL_DB_PASSWORD` | ✗ | **Missing** — see Note 1 |

---

## Notes (non-blocking)

### Note R006-01 — Temporal DB user password not in .env.example

ADR-015 specifies a dedicated `temporal` PostgreSQL user. The current compose uses `waooaw` (main user) with `POSTGRES_PASSWORD` — acceptable for dev. However:

**Required action (IB-009):** The Runtime Professional should add `TEMPORAL_DB_PASSWORD=change-me-temporal-db` to `.env.example` and create a dedicated `temporal` DB user in the postgres init scripts, consistent with ADR-015. This isolates Temporal's DB operations from application DB operations in QA and beyond.

### Note R006-02 — Next.js web service has no healthcheck

The `web` service has no healthcheck. Other services that `depend_on: web` would not be able to use `condition: service_healthy`. This is not a current problem (no service depends on `web`), but it is an inconsistency.

**Required action (IB-009):** Add healthcheck to `web` service: `test: ["CMD-SHELL", "curl -sf http://localhost:3000 || exit 1"]`.

### Note R006-03 — AI Runtime pgvector access not fully specified

`ai-runtime` uses `runtime_app` DB user. `ledger-design.md` grants `runtime_app` SELECT on the business schema. AI Runtime needs read access to pgvector embeddings for Creative Standard Profiles — these are in the professional schema (or a dedicated embeddings table not yet specified in the data architecture).

**Required action (IB-009 / Data Architecture addendum):** The Runtime Professional should confirm the pgvector embeddings table location and ensure `runtime_app` has SELECT access. If the embeddings table is in a new schema (e.g., `ai`), this requires a `ledger-design.md` addendum or an operational-discoveries entry.

---

## Infrastructure Directory Specification (for Runtime Professional — IB-009)

The compose file mounts three directories that do not yet exist. The Runtime Professional must create them:

| Mount | Path | What to create |
|---|---|---|
| PostgreSQL init | `./infrastructure/postgres/init/` | SQL scripts: create schemas, DB users (constitutional_app, business_app, runtime_app, temporal), grant permissions per ledger-design.md, enable RLS |
| Keycloak realm | `./infrastructure/keycloak/` | `waooaw-realm.json` — realm with waooaw-web client, waooaw-platform client, Google IDP federation stub |
| Temporal dynamic config | `./infrastructure/temporal/` | `dynamicconfig.yaml` — Temporal server dynamic configuration |

These are implementation artifacts (IB-009), not Platform Architecture deliverables. This note is provided so the Runtime Professional has a clear starting point.

---

## IB-008 Success Criteria Verification

| Criterion | Status |
|---|---|
| `docker-compose.yml` models all services correctly | ✓ |
| `.env.example` documents all required variables | ✓ (one variable to add per Note R006-01) |
| Dependency ordering enables clean startup | ✓ |
| ADR-ratified technology versions used | ✓ |
| Infrastructure specification sufficient for Runtime Professional to begin IB-009 | ✓ |

**IB-008: APPROVED.** The compose file is a correct and complete local environment specification. The three notes are IB-009 implementation tasks.

---

## Gate G4 Assessment

Gate G4 requires: IB-005 ✓, IB-006 ✓, IB-007 ✓, IB-008 ✓ (this review).

**Remaining before Gate G4 formally closes:** `architecture/reference/proto/constitutional_service.proto` (CA-R004-01). The proto file is an API contract (Solution Architect scope). It is the last architectural artifact required before the Runtime Professional may begin IB-009.

---

## Verdict: APPROVED

IB-008 outputs accepted. Gate G4 is one artifact away from formal closure.

**Reviewer:** Enterprise Architect (AI agent, Office 04)
**Date:** 2026-07-07
**Review closed.**
