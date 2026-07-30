# Work Contract 019 — GOAL-004: Markup Engine + C-089 Enforcement

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 019 | **Goal:** GOAL-004 | **Depends on:** WC-017 complete
**Spec:** architecture/reference/billing/wbe-component-spec.md §2.2, dma-bundle-definitions.md §4
**Constitutional Basis:** C-059, C-076, C-089, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC019-01 | `markup/bundle_engine.py`: cost_floor() = Σ(marked_up × ration) + infra_share | `reasoning` |
| WC019-02 | `markup/bundle_engine.py`: derive_price() Layer 3; validate_margin() C-089; write to pricing_floor_log | `reasoning` |
| WC019-03 | `markup/router.py`: 4 endpoints per spec §2.2 | `standard` |
| WC019-04 | Tests ≥90%: Starter ₹217 ± 5%; Runner ₹374 ± 5%; Winner ₹949 ± 5%; 422 on below-floor | `standard` |

## Definition of Done
- POST /pricing/validate returns 422 (not 200) on below-C-089-floor price
- pricing_floor_log row written on every REJECTED validation
- Cost floor calculations match D-05 bundle definitions within 5% tolerance
