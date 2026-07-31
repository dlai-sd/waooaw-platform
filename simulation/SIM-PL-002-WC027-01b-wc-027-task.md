# SIM-PL-002 — WC027-01b: Markup Engine Router + main.py mount
**Date:** 2026-07-31
**Author:** Platform IT Expert (INST-010) — pre-execution simulation
**Task:** WC027-01b — `markup/router.py` + `src/billing-engine/main.py` router mount
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-027

## Context
FastAPI router for `/pricing/` prefix + additive mount in `main.py`.
Depends on WC027-01a (BundleEngine + models complete).
Constitutional basis: ADR-002 (spec-first), C-059 (traceability via router→service).

## Subtask Decomposition
- WC027-01ba — `src/billing-engine/markup/router.py`: 4 endpoints
  - `GET /pricing/thread-catalog` → delegates to existing `ThreadCatalogService`
  - `GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}` → `BundleEngine.cost_floor()`
  - `POST /pricing/validate` → `BundleEngine.validate_price()` (422 body includes `minimum_compliant_price_paise`)
  - `POST /pricing/derive` → `BundleEngine.derive_price()`
- WC027-01bb — `src/billing-engine/main.py`: `app.include_router(markup_router)` — additive only

## Dependency Graph
WC027-01ba: depends_on=[WC027-01a (BundleEngine importable)]
WC027-01bb: depends_on=[WC027-01ba] — one-line additive change to existing main.py

## Risk Assessment
**LOW.** Pure router pattern — established in WC-026 wallet/router.py. No new DB logic.
main.py mount is additive (append only, no modification of existing lifespan or routes).
422 body shape confirmed by SA: `minimum_compliant_price_paise` in PriceValidation response.
model_hint: `auto` — correct for deterministic scaffold.

## Pre-execution Checks (local)
- PASS: `markup/` directory structure matches wbe-component-spec.md §1
- PASS: `main.py` exists from WC-025 scaffold — additive include_router is safe
- PASS: Router pattern identical to `wallet/router.py` — well-understood

## Verdict

**VERDICT: ✅ PASS — router + mount, LOW risk, well-established pattern in this codebase**
