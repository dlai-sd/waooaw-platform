# Work Contract 025 — WBE-S1: Service Scaffold + DB Migration + Thread Catalog

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-025
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — WBE sub-sprint 1 of 8
**Sprint Track:** Track WBE — Wallet & Billing Engine (GOAL-004)
**Gate:** G5 → MVI (WBE readiness precondition)
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-088 (Billing Profile), C-089 (Margin Floor), C-090 (Grandfather), C-091 (Thread Catalog), C-038 (Pro-rata), C-059 (Traceability)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30

**Depends on:** WC-015 (AI Runtime live), GOAL-PLATFORM-REGISTRY (skeleton exists)
**WC number assigned by:** Product Owner (INST-011) — sequential after WC-024

---

## Sprint Goal

New `src/billing-engine/` Python FastAPI service running on port 8140,
`12-billing-engine.sql` migration applied (note: `11-platform-registry.sql` already
occupies slot 11), Thread Catalog seeded from D-06, all health checks passing.

---

## Tasks

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC025-01 | Python project scaffold: `src/billing-engine/` — main.py, config.py, requirements.txt, Dockerfile, /health endpoint | `reasoning` | ✅ DONE |
| WC025-02 | DB migration: `infrastructure/postgres/init/12-billing-engine.sql` — all tables from D-08, wbe_app role, seed data | `reasoning` | ✅ DONE |
| WC025-03 | Thread Catalog service: `src/billing-engine/markup/thread_catalog.py` — load from DB, Redis cache (30s TTL), cache invalidation | `standard` | ✅ DONE |
| WC025-04 | docker-compose update: add `redis` service + `billing-engine` service on port 8140 | `standard` | ✅ DONE |
| WC025-05 | Tests: `tests/billing-engine/` — thread catalog load, cache hit/miss, health endpoint | `standard` | ✅ DONE |

---

## Required Inputs

| Input | File |
|---|---|
| D-06 Thread Catalog | `architecture/reference/billing/thread-catalog.md` |
| D-08 Schema Updates | `architecture/reference/billing/billing-schema-updates.md` |
| D-03 ADR-034 | `adr/ADR-034-waooaw-billing-engine.md` |
| D-07 WBE Component Spec | `architecture/reference/billing/wbe-component-spec.md` |
| EA Skeleton | `src/billing-engine/skeleton/wbe_interfaces.py` |

---

## Definition of Done

- [ ] `docker compose up billing-engine` → `curl localhost:8140/health` returns 200
- [ ] `docker compose up postgres` → `12-billing-engine.sql` applies clean
- [ ] Thread Catalog loads from DB: all 24 thread entries from D-06
- [ ] Redis cache returns hit on second call within 30s TTL
- [ ] `pytest tests/billing-engine/` → all tests pass

---

## Notes

- Migration slot is `12-` (not `11-`) because `11-platform-registry.sql` was created by GOAL-PLATFORM-REGISTRY.
- WBE skeleton already committed (`src/billing-engine/skeleton/wbe_interfaces.py`) — implementation MUST NOT change interface signatures (ADR-036).
- Pricing decisions (D-05 §7) still pending Founder authorization — bundle profiles seeded as `PENDING_FOUNDER_AUTH` status.
- Redis is new to docker-compose (no existing Redis service). Adding redis:7-alpine as lightweight.
