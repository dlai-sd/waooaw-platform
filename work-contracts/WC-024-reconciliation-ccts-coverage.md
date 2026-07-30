# Work Contract 024 — GOAL-004: Reconciliation Engine + All CCTs + Coverage Gate

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 024 | **Goal:** GOAL-004 | **Depends on:** WC-017 through WC-023 complete
**Spec:** wbe-component-spec.md §2.5 + §4, ADR-024 Amendment
**Constitutional Basis:** C-059, C-065, C-076, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC024-01 | `reconciliation/service.py`: daily_audit() — balance vs ledger sum; >1 paise → halt + FA; margin_report() | `reasoning` |
| WC024-02 | `reconciliation/scheduler.py`: APScheduler 02:00 IST; halt detection; GET /reconciliation/status | `standard` |
| WC024-03 | `tests/test_ccts.py`: CCT-PREPAID-01, CCT-ONBOARD-01, CCT-BILLINGLOOP-01, CCT-SELFAUDIT-01 all pass | `reasoning` |
| WC024-04 | AI Runtime integration: WBE client calls in pse_router.py (balance check → reserve before LLM → release after → record_cost) | `reasoning` |
| WC024-05 | Coverage gate: pytest-cov ≥90% on all billing-engine modules; CI pipeline Codecov integration | `standard` |

## Definition of Done
- All 4 CCTs GREEN in CI
- Coverage ≥90% blocks PR merge (C-076)
- AI Runtime dispatches 0 LLM calls without prior WBE reserve (tested via integration test)
- Balance discrepancy > 1 paise → billing halted → no customer notification sent
- GOAL-004 IMPLEMENTATION COMPLETE — update Evidence Register to all PRODUCED
