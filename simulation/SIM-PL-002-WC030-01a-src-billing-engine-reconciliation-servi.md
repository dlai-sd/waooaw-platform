# SIM-PL-002 — WC030-01a `src/billing-engine/reconciliation/service.py` — `Reconcilia
**Date:** 2026-08-06
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** WC030-01a — `src/billing-engine/reconciliation/service.py` — `ReconciliationService` (standalone concrete class — no skeleton ABC): `run_daily_audit(date: date) -> DailyAuditResult` (for each `bucket_reservation WHERE consumed=True AND consumed_at::date = date`, verify a matching `platform_cost_ledger` row with `bucket_reservation_id` exists; flag unlinked reservations as `DailyAuditResult.unlinked_reservations`; emit C-023 evidence record regardless of outcome); `run_self_audit() -> SelfAuditResult` (for every active `wallet_bucket`: compute `expected_balance = SUM(topup_orders.amount_paise WHERE employment_contract_id = bucket.employment_contract_id AND thread_type = bucket.thread_type AND applied_at IS NOT NULL) - SUM(bucket_reservations.reserved_paise WHERE consumed=True AND bucket_id = X)`; if `\
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-030

## Context
Auto-bootstrapped by pipeline. Known-safe pattern — follows established repo conventions. Low execution risk.
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
WC030-01aa — implement per WC scope: `src/billing-engine/reconciliation/service.py` — `ReconciliationService` (standalone concrete class — no skeleton ABC): `run_daily_audit(date: date) -> DailyAuditResult` (for each `bucket_reservation WHERE consumed=True AND consumed_at::date = date`, verify a matching `platform_cost_ledger` row with `bucket_reservation_id` exists; flag unlinked reservations as `DailyAuditResult.unlinked_reservations`; emit C-023 evidence record regardless of outcome); `run_self_audit() -> SelfAuditResult` (for every active `wallet_bucket`: compute `expected_balance = SUM(topup_orders.amount_paise WHERE employment_contract_id = bucket.employment_contract_id AND thread_type = bucket.thread_type AND applied_at IS NOT NULL) - SUM(bucket_reservations.reserved_paise WHERE consumed=True AND bucket_id = X)`; if `\ → ruff → tests → PASS

## Dependency Graph
WC030-01aa: depends_on=[prior tasks in same sprint]

## Risk Assessment
Known-safe pattern — follows established repo conventions. Low execution risk.

## Verdict

**VERDICT: ✅ PASS**
