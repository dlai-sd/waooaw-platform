# SIM-PL-002 — WC029-02 `tests/billing-engine/test_procurement.py` — test: `record_c
**Date:** 2026-08-05
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** WC029-02 — `tests/billing-engine/test_procurement.py` — test: `record_cost` writes one row to `platform_cost_ledger` (verify via DB query), `record_cost` called twice for same event writes TWO rows (append-only — no dedup at DB level), `project_runway` formula (balance / 7d_avg_burn = days), FA auto-created at ≤30d threshold (P2) via `maybe_create`, FA upgraded to P1 at ≤14d and P0 at ≤7d, second `maybe_create` same provider+priority → no duplicate entry in FA file (idempotency), `GET /platform/procurement/status` → 200 list with `days_remaining`; use `tmp_path` pytest fixture for FA file — do NOT modify real `security/FOUNDER-ACTIONS.md` — ≥90% line coverage
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-029

## Context
Auto-bootstrapped by pipeline. Known-safe pattern — follows established repo conventions. Low execution risk.
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
WC029-02a — implement per WC scope: `tests/billing-engine/test_procurement.py` — test: `record_cost` writes one row to `platform_cost_ledger` (verify via DB query), `record_cost` called twice for same event writes TWO rows (append-only — no dedup at DB level), `project_runway` formula (balance / 7d_avg_burn = days), FA auto-created at ≤30d threshold (P2) via `maybe_create`, FA upgraded to P1 at ≤14d and P0 at ≤7d, second `maybe_create` same provider+priority → no duplicate entry in FA file (idempotency), `GET /platform/procurement/status` → 200 list with `days_remaining`; use `tmp_path` pytest fixture for FA file — do NOT modify real `security/FOUNDER-ACTIONS.md` — ≥90% line coverage → ruff → tests → PASS

## Dependency Graph
WC029-02a: depends_on=[prior tasks in same sprint]

## Risk Assessment
Known-safe pattern — follows established repo conventions. Low execution risk.

## Verdict

**VERDICT: ✅ PASS**
