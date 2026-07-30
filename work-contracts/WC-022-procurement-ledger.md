# Work Contract 022 — GOAL-004: Platform Procurement Ledger + FA Auto-Generation

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 022 | **Goal:** GOAL-004 | **Depends on:** WC-017 complete
**Spec:** wbe-component-spec.md §2.4
**Constitutional Basis:** C-007, C-059, C-076, C-091, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC022-01 | `procurement/service.py`: record_cost() with FX; project_runway() per provider | `reasoning` |
| WC022-02 | `procurement/founder_action.py`: auto-write FA-NNN to FOUNDER-ACTION.md when runway < 7 days; idempotent | `reasoning` |
| WC022-03 | `procurement/router.py`: POST /platform/procurement/record-cost; GET /platform/procurement/status | `standard` |
| WC022-04 | FX snapshot job: daily 09:00 IST, RBI reference rate → institutional.fx_rates | `standard` |
| WC022-05 | Tests ≥90%: cost recorded with correct FX; runway < 7 triggers FA; duplicate FA prevention | `standard` |

## Definition of Done
- AI Runtime can POST /platform/procurement/record-cost after every LLM call
- provider_accounts.days_remaining accurate within ±10% of actual
- FA auto-written to FOUNDER-ACTION.md with correct provider, amount, urgency date
