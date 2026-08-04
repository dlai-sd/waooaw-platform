# SIM-PL-002 — WC028-01: MeterService + ThresholdPolicy
**Date:** 2026-08-04
**Author:** Platform IT Expert (INST-010) — pre-execution simulation
**Task:** WC028-01 — `meter/service.py` (MeterService) + `meter/alert_policy.py` (ThresholdPolicy singletons)
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-028

## Context
Usage metering and threshold alerting for the Billing Engine.
MeterService records per-thread usage, projects wallet depletion, and fires
threshold alerts across 3 scopes (customer, agency, procurement runway) per
wbe-component-spec.md §2.3a Amendment 1.
Constitutional basis: C-043 (Budget Ceiling Enforcement), C-049 (Honest Limitation),
C-051 (Resource Transparency), ADR-034 (WBE architecture).

## Subtask Decomposition
- WC028-01a — `meter/alert_policy.py`: ThresholdRule dataclass, ThresholdPolicy dataclass,
  3 singletons: CUSTOMER_BUCKET_POLICY / AGENCY_POLICY / PROCUREMENT_POLICY per §2.3a ladder.
  Pure dataclasses — no DB, no I/O. Deterministic.
- WC028-01b — `meter/service.py`: MeterService class implementing IMeterService:
  - `record_usage()`: resolves provider_account_id via thread_catalog + provider_accounts JOIN,
    writes platform_cost_ledger row, async SQLAlchemy session.
  - `project_depletion()`: 7d rolling avg SELECT from platform_cost_ledger.
  - `run_daily_scan()`: iterates all active customers, calls `check_thresholds()`.
  - `check_thresholds()` (concrete, non-ABC): SUM(platform_cost_ledger.marked_up_cost_inr_paise)
    / (consumed + wallet_buckets.balance_paise) → pct_consumed; fires per §2.3a; deduplicates
    via meter_alert_log (24h window per customer+threshold).

## Dependency Graph
WC028-01a: depends_on=[] — pure dataclasses, no dependencies
WC028-01b: depends_on=[WC028-01a, WC026 (wallet tables), WC027 (thread_catalog + BundleEngine)]

## Risk Assessment
**MEDIUM.** Complex business logic:
- §2.3a threshold ladder has 5 scopes × multiple thresholds — exact config must match spec.
- Deduplication window: 24h per customer+threshold must be a single compound SELECT.
- `project_depletion()`: rolling 7d AVG must exclude the current day (incomplete).
- Scope 3 (Procurement): runway computed from `provider_accounts.balance_paise` — different
  table than Scope 1 wallet_buckets.
Mitigation: reasoning model selected for WC028-01 (model_hint=reasoning). IMeterService ABC
in wbe_interfaces.py constrains the method signatures. WC028-03 provides CCT-BILLINGLOOP-01
as correctness oracle. Pattern is analogous to WC-026 WalletService but with more DB tables.

## Pre-execution Checks (local)
- PASS: `src/billing-engine/skeleton/wbe_interfaces.py` contains `IMeterService` with correct method signatures
- PASS: `infrastructure/postgres/init/12-billing-engine.sql` defines `platform_cost_ledger`,
  `meter_alert_log`, `provider_accounts`, `wallet_buckets` — all referenced tables exist
- PASS: `architecture/reference/billing/wbe-component-spec.md §2.3a` Amendment 1 committed —
  threshold names and trigger percentages are spec-sourced, not free-form
- PASS: `meter/` subdirectory is new — no conflict with existing files
- PASS: model_hint=reasoning — appropriate for complex multi-table business logic

## Verdict

**VERDICT: ✅ PASS — MeterService + ThresholdPolicy, MEDIUM risk, reasoning model, §2.3a spec available**
