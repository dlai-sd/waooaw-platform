# SIM-PL-002 — WC027-01a: Markup Engine Models + BundleEngine
**Date:** 2026-07-31
**Author:** Platform IT Expert (INST-010) — pre-execution simulation
**Task:** WC027-01a — `markup/models.py` + `markup/bundle_engine.py`
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-027

## Context
Markup Engine core: Pydantic models + `BundleEngine` implementing `IMarkupEngine` skeleton ABC.
Spec is SA-corrected (GOAL-WC027 GOA-WC027-02): 3 gaps fixed before this sprint fires.
Constitutional basis: C-089 (never price below cost floor), C-059 (pricing_floor_log audit), C-076 (≥90% coverage).

## Subtask Decomposition
- WC027-01aa — `src/billing-engine/markup/models.py`: Pydantic `ThreadEntry`, `BundleProfile`, `PriceConfig`, `PriceValidationRequest`, `PriceDeriveRequest`, `PriceValidation` (with `minimum_compliant_price_paise`)
- WC027-01ab — `src/billing-engine/markup/bundle_engine.py`: `BundleEngine(IMarkupEngine)` — `cost_floor()`, `derive_price()`, `validate_price()` (writes `pricing_floor_log` on both APPROVED + REJECTED — C-059)

## Dependency Graph
WC027-01aa: depends_on=[] — pure Pydantic models, no DB
WC027-01ab: depends_on=[WC027-01aa, WC025 DB schema live, WC026 WalletService importable]
  - reads `bundle_profiles.cost_floor_paise` and `bundle_profiles.minimum_margin_pct`
  - writes `pricing_floor_log` (exists in 12-billing-engine.sql)
  - does NOT call WalletService — import only for type hints

## Risk Assessment
**LOW-MEDIUM.** Pricing formula `floor / (1 - margin/100)` is elementary. No external calls.
The only write path is `pricing_floor_log` which is append-only (ADR-011 compliant).
C-089 floor enforcement: `validate_price` returns 422 when `proposed < cost_floor / (1 - min_margin/100)` — deterministic.
SA correction confirmed: uses `bundle_profiles.minimum_margin_pct`, NOT non-existent `markup_thread_catalog`.
Skeleton ABC `IMarkupEngine.validate_price(agent_type, bundle_tier, proposed)` matches exactly — no type errors expected.

## Pre-execution Checks (local)
- ✅ `IMarkupEngine` ABC in `src/billing-engine/skeleton/wbe_interfaces.py` exports `validate_price(agent_type, bundle_tier, proposed_price_paise)`
- ✅ `bundle_profiles` table exists in `12-billing-engine.sql` with `cost_floor_paise`, `minimum_margin_pct` columns
- ✅ `pricing_floor_log` table exists in DB schema
- ✅ Pydantic v2 pattern matches WC-025/WC-026 established style

## Verdict

**VERDICT: ✅ PASS — EA/SA reviewed (GOAL-WC027), 3 spec gaps pre-fixed, risk LOW-MEDIUM, no blocking unknowns**
