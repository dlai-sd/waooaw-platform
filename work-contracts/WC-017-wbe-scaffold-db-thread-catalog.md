# Work Contract 017 — GOAL-004: WBE Scaffold + DB Migration + Thread Catalog

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 017
**Goal:** GOAL-004 — WAOOAW Billing Engine
**Sprint Track:** WBE Implementation — Sprint 1 of 8
**Authorization:** Requires Founder implementation authorization (FA-NNN in security/FOUNDER-ACTIONS.md)
**Constitutional Basis:** C-059, C-065, C-076, C-088, C-091, ADR-034

**Spec inputs:**
- `architecture/reference/billing/thread-catalog.md` (D-06)
- `architecture/reference/billing/billing-schema-updates.md` (D-08)
- `adr/ADR-034-waooaw-billing-engine.md` (D-03)

## Tasks

### WC017-01 — Python project scaffold
**Scope:** `src/billing-engine/` with pyproject.toml, Dockerfile, main.py, config.py, /health endpoint
**model_hint:** `reasoning`

### WC017-02 — DB migration 11-billing-engine.sql
**Scope:** All tables from D-08, wbe_app role, seed data (billing_profiles + provider_accounts)
**model_hint:** `reasoning`

### WC017-03 — Thread Catalog service
**Scope:** `markup/thread_catalog.py` — load from DB, Redis cache (30s TTL), invalidation
**model_hint:** `standard`

### WC017-04 — docker-compose update
**Scope:** Add `wbe` service on port 8140; healthcheck dependencies
**model_hint:** `standard`

### WC017-05 — Tests ≥90%
**Scope:** Thread catalog load, cache hit/miss, health endpoint, migration verify
**model_hint:** `standard`

## Definition of Done
- `docker compose up wbe` → port 8140 /health returns 200
- `docker compose up postgres` → 11-billing-engine.sql applies without error
- 9 provider_accounts seeded, 4 billing_profiles seeded
- Coverage ≥90% on wbe modules (WC-024 adds full CCTs)
