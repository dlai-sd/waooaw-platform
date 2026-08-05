# SIM-PL-002 — WC029-01a `src/billing-engine/procurement/models.py` — **SQLAlchemy OR
**Date:** 2026-08-05
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** WC029-01a — `src/billing-engine/procurement/models.py` — **SQLAlchemy ORM models** (map to existing DB tables — do NOT add columns): `ProviderAccount` maps `institutional.provider_accounts` (id, provider_name, display_name, currency, balance_paise, low_balance_threshold_days, founder_action_template); `PlatformCostLedgerEntry` maps `institutional.platform_cost_ledger` using `provider_account_id UUID` FK — NOT `provider_name`; **Pydantic response models** (computed fields, NOT DB-mapped): `ProviderRunwayStatus` (provider_name, balance_paise, daily_burn_rate_paise, days_remaining: float, last_fa_level_triggered: Optional[str]), `CostRecordRequest` (provider: str, thread_type: str, customer_id: UUID, agent_type: str, cost_paise: int, fx_rate_inr_per_usd: float); `src/billing-engine/procurement/service.py` — `ProcurementService` (standalone concrete class — no skeleton ABC): `record_cost(provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd) -> None` (resolves `provider_account_id` from `provider_name` lookup, inserts into `platform_cost_ledger` — append-only, intentionally NOT idempotent per C-007), `project_runway(provider_name) -> float` (7d rolling avg: `SUM(raw_cost_inr_paise WHERE recorded_at >= NOW()-7d) / 7` → `balance_paise / avg`; returns `float('inf')` when avg==0), `check_and_alert(provider_name) -> list[FounderActionCreated]` (reads `PROCUREMENT_POLICY` from `meter.alert_policy`; calls `FounderActionGenerator.maybe_create` for each breached threshold)
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-029

## Context
Auto-bootstrapped by pipeline. Known-safe pattern — follows established repo conventions. Low execution risk.
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
WC029-01aa — implement per WC scope: `src/billing-engine/procurement/models.py` — **SQLAlchemy ORM models** (map to existing DB tables — do NOT add columns): `ProviderAccount` maps `institutional.provider_accounts` (id, provider_name, display_name, currency, balance_paise, low_balance_threshold_days, founder_action_template); `PlatformCostLedgerEntry` maps `institutional.platform_cost_ledger` using `provider_account_id UUID` FK — NOT `provider_name`; **Pydantic response models** (computed fields, NOT DB-mapped): `ProviderRunwayStatus` (provider_name, balance_paise, daily_burn_rate_paise, days_remaining: float, last_fa_level_triggered: Optional[str]), `CostRecordRequest` (provider: str, thread_type: str, customer_id: UUID, agent_type: str, cost_paise: int, fx_rate_inr_per_usd: float); `src/billing-engine/procurement/service.py` — `ProcurementService` (standalone concrete class — no skeleton ABC): `record_cost(provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd) -> None` (resolves `provider_account_id` from `provider_name` lookup, inserts into `platform_cost_ledger` — append-only, intentionally NOT idempotent per C-007), `project_runway(provider_name) -> float` (7d rolling avg: `SUM(raw_cost_inr_paise WHERE recorded_at >= NOW()-7d) / 7` → `balance_paise / avg`; returns `float('inf')` when avg==0), `check_and_alert(provider_name) -> list[FounderActionCreated]` (reads `PROCUREMENT_POLICY` from `meter.alert_policy`; calls `FounderActionGenerator.maybe_create` for each breached threshold) → ruff → tests → PASS

## Dependency Graph
WC029-01aa: depends_on=[prior tasks in same sprint]

## Risk Assessment
Known-safe pattern — follows established repo conventions. Low execution risk.

## Verdict

**VERDICT: ✅ PASS**
