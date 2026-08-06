# SIM-PL-002 — WC030-03 `tests/billing-engine/test_reconciliation.py` — test: clean 
**Date:** 2026-08-06
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** WC030-03 — `tests/billing-engine/test_reconciliation.py` — test: clean `run_self_audit()` → `billing_halted=False`; manually corrupt `balance_paise` in DB (add 2 paise via direct SQL, bypassing ORM) → `run_self_audit()` → `billing_halted=True` + Redis `wbe:billing_halted` set + FA created; `POST /wallet/.../reserve` while halted → HTTP 503 `BILLING_INTEGRITY_HALT`; `clear_halt()` + `run_self_audit()` (fix balance first) → billing resumes; `run_daily_audit` with matched cost-to-reservation → zero unlinked; margin report arithmetic (`margin_pct = (revenue-cost)/revenue`); scheduler idempotency (Redis `wbe:audit_in_progress` key blocks second run); implement `CCT-SELFAUDIT-01` exactly as in `wbe-component-spec.md §4`; use `fakeredis` or dedicated test Redis — never share Redis state with production keys; ≥90% line coverage
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-030

## Context
Auto-bootstrapped by pipeline. Known-safe pattern — follows established repo conventions. Low execution risk.
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
WC030-03a — implement per WC scope: `tests/billing-engine/test_reconciliation.py` — test: clean `run_self_audit()` → `billing_halted=False`; manually corrupt `balance_paise` in DB (add 2 paise via direct SQL, bypassing ORM) → `run_self_audit()` → `billing_halted=True` + Redis `wbe:billing_halted` set + FA created; `POST /wallet/.../reserve` while halted → HTTP 503 `BILLING_INTEGRITY_HALT`; `clear_halt()` + `run_self_audit()` (fix balance first) → billing resumes; `run_daily_audit` with matched cost-to-reservation → zero unlinked; margin report arithmetic (`margin_pct = (revenue-cost)/revenue`); scheduler idempotency (Redis `wbe:audit_in_progress` key blocks second run); implement `CCT-SELFAUDIT-01` exactly as in `wbe-component-spec.md §4`; use `fakeredis` or dedicated test Redis — never share Redis state with production keys; ≥90% line coverage → ruff → tests → PASS

## Dependency Graph
WC030-03a: depends_on=[prior tasks in same sprint]

## Risk Assessment
Known-safe pattern — follows established repo conventions. Low execution risk.

## Verdict

**VERDICT: ✅ PASS**
