# SIM-PL-002 — WC027-02 `tests/billing-engine/test_markup.py` — test: cost_floor rea
**Date:** 2026-07-31
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** WC027-02 — `tests/billing-engine/test_markup.py` — test: cost_floor reads `bundle_profiles.cost_floor_paise` (not recomputed), derive_price formula uses margin-on-revenue `floor / (1 - margin/100)`, `POST /pricing/validate` 200 path (APPROVED, `pricing_floor_log` row written), `POST /pricing/validate` 422 path (REJECTED — body includes `minimum_compliant_price_paise`, `pricing_floor_log` row written), `GET /pricing/thread-catalog` response shape, ≥90% line coverage
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-027

## Context
Auto-bootstrapped by pipeline. Known-safe pattern — follows established repo conventions. Low execution risk.
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
WC027-02a — implement per WC scope: `tests/billing-engine/test_markup.py` — test: cost_floor reads `bundle_profiles.cost_floor_paise` (not recomputed), derive_price formula uses margin-on-revenue `floor / (1 - margin/100)`, `POST /pricing/validate` 200 path (APPROVED, `pricing_floor_log` row written), `POST /pricing/validate` 422 path (REJECTED — body includes `minimum_compliant_price_paise`, `pricing_floor_log` row written), `GET /pricing/thread-catalog` response shape, ≥90% line coverage → ruff → tests → PASS

## Dependency Graph
WC027-02a: depends_on=[prior tasks in same sprint]

## Risk Assessment
Known-safe pattern — follows established repo conventions. Low execution risk.

## Verdict

**VERDICT: ✅ PASS**
