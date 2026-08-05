# Work Contract 028 — WBE-S4: Meter + Alert Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-028
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — WBE sub-sprint 4 of 8
**Sprint Track:** Track WBE — Usage Meter & Alert Engine (GOAL-004)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-043 (Budget Ceiling Enforcement), C-049 (Honest Limitation — agent discloses low balance), C-051 (Resource Transparency), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30 (GOAL-004 continuation)

**Depends on:** WC-026 (WalletService live), WC-027 (BundleEngine live for cost data)
**Prerequisite spec:** `architecture/reference/billing/wbe-component-spec.md §2.3a` (threshold ladder) — committed 2026-07-31 Amendment 1. Read this section carefully before implementing ThresholdPolicy.

---

## Sprint Goal

Implement the Usage Meter and Alert Engine: record usage per thread call, project bucket depletion,
fire threshold alerts across three scopes (customer wallet, agency sub-wallet, WAOOAW procurement runway)
per the §2.3a ladder, and expose FastAPI endpoints. Daily scan runs at 06:00 IST via scheduler stub.

---

## Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC028-01 | `src/billing-engine/meter/service.py` — `MeterService` implementing `IMeterService`: `record_usage(customer_id, thread_type, **amount_paise**)` (resolves `provider_account_id` via `thread_catalog → provider_accounts` lookup, then writes to `platform_cost_ledger`), `project_depletion(customer_id, thread_type) -> DepletionProjection` (7d rolling avg from `platform_cost_ledger`), `run_daily_scan() -> DailyScanResult` (calls `check_thresholds` for all active customers), `check_thresholds(customer_id) -> list[AlertFired]` (concrete non-ABC helper — NOT in `IMeterService`; tests call it directly on the concrete class; computes `pct_consumed = SUM(platform_cost_ledger.marked_up_cost_inr_paise WHERE customer_id + current billing_period) / wallet_buckets.balance_paise` (quota; see C-043 note below); fires per §2.3a scope 1+2+3 ladder; deduplicates via `meter_alert_log`); `src/billing-engine/meter/alert_policy.py` — `ThresholdRule` dataclass (name, consumed_pct_trigger, action: Enum[LOG\|NOTIFY\|FA\|BLOCK], bypass_quiet_hours: bool), `RunwayThresholdRule` dataclass (name, days_remaining_trigger: float, action, bypass_quiet_hours: bool), `ThresholdPolicy` dataclass (scope, thresholds: list[ThresholdRule], runway_thresholds: list[RunwayThresholdRule], quiet_hours_start_ist=23, quiet_hours_end_ist=6, **rules: @property → list[ThresholdRule\|RunwayThresholdRule] — returns runway_thresholds if populated else thresholds**), singletons: `CUSTOMER_BUCKET_POLICY`, `AGENCY_POLICY`, `PROCUREMENT_POLICY` per §2.3a — Scope 3 threshold names: `RUNWAY_P2` (≤30d), `RUNWAY_P1` (≤14d), `RUNWAY_P0` (≤7d), `RUNWAY_CRITICAL` (≤3d), `RUNWAY_EMERGENCY` (≤1d) | reasoning | skipped_idempotent | — |
| WC028-02 | `src/billing-engine/meter/whatsapp_notifier.py` — `WhatsAppNotifier`: `send(customer_id, template_id, params: dict) -> bool` (stubs to 360dialog MCP call — raise `NotImplementedError` with TODO comment pointing to ADR-023; in tests mock this stub); `src/billing-engine/meter/router.py` — FastAPI prefix `/meter`: `GET /{customer_id}/status` returns `UsageStatus`, `POST /daily-scan` (internal scheduler call, triggers `run_daily_scan()`); mount router in `src/billing-engine/main.py`. NOTE: `GET /platform/margin/report` is Procurement API (§2.4) — deferred to WC-029 scope. | auto | skipped_idempotent | — |
| WC028-03 | `tests/billing-engine/test_meter.py` — test: threshold fires at correct % (30% remaining triggers WARN_30), no double-fire within 24h deduplication window, quiet hours suppress WhatsApp (23:00-06:00 IST, notifications queued), procurement runway P0 escalation at ≤7 days, agency NULL quota produces no alert, `POST /meter/daily-scan` calls check_thresholds for all customers, `CCT-BILLINGLOOP-01` scenario: AD wallet hits zero → `alerts_sent == 1` type `AD_WALLET_BELOW_MINIMUM` — ≥90% line coverage | auto | done | 2026-08-05 |

---

## Required Inputs

| Input | File |
|---|---|
| D-07 WBE Component Spec §2.3 + §2.3a | `architecture/reference/billing/wbe-component-spec.md` — read §2.3 AND §2.3a (Amendment 1) in full |
| CCT-BILLINGLOOP-01 spec | `architecture/reference/billing/wbe-component-spec.md` §4 — implement this CCT in test_meter.py |
| WalletService | `src/billing-engine/wallet/service.py` — import for balance reads |
| DB Migration | `infrastructure/postgres/init/12-billing-engine.sql` — spending_quota_paise, platform_cost_ledger, provider_accounts, low_balance_threshold_days |
| WBE Skeleton interfaces | `src/billing-engine/skeleton/wbe_interfaces.py` |

---

## Definition of Done

- [ ] `from meter.service import MeterService` — no import errors
- [ ] `check_thresholds(customer_id)` with bucket at **8% remaining** (92% consumed) → fires `WARN_10` alert, writes `meter_alert_log` row
- [ ] Second call within 24h same customer + same threshold → returns empty list (deduplicated)
- [ ] `ThresholdPolicy` quiet hours: 23:15 IST → alert created but WhatsApp NOT dispatched
- [ ] `GET /meter/{customer_id}/status` → 200 with `UsageStatus`
- [ ] `POST /meter/daily-scan` → 200 with `DailyScanResult { customers_scanned, alerts_sent }`
- [ ] `pytest tests/billing-engine/test_meter.py` → all tests pass, CCT-BILLINGLOOP-01 passes, ≥90% coverage
- [ ] `ruff check src/billing-engine/meter/ tests/billing-engine/test_meter.py` → clean

---

## Alert Deduplication Implementation Note

`meter_alert_log` is **NOT in `12-billing-engine.sql`** and must be added as a SQL amendment there (not in service
startup — DDL in service code is prohibited per ADR-011). The batch executor must add it as an `ALTER`/`CREATE`
amendment block in `infrastructure/postgres/init/12-billing-engine.sql`. Schema:
```sql
CREATE TABLE IF NOT EXISTS institutional.meter_alert_log (
    id              BIGSERIAL       PRIMARY KEY,
    customer_id     UUID            NOT NULL,
    bucket_type     VARCHAR(50)     NOT NULL,
    threshold_name  VARCHAR(30)     NOT NULL,
    period_id       VARCHAR(7)      NOT NULL,  -- YYYY-MM format
    fired_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_alert_dedup UNIQUE (customer_id, bucket_type, threshold_name, period_id)
);
```
Alert re-fires within the same period only if the bucket refills above the threshold and drops below again —
implemented by deleting the dedup row on bucket refill (WalletService top-up hook).

## C-043 Implementation Note — % Consumed Formula

`wallet_buckets.balance_paise` is the **initial quota** set at wallet creation.
`record_usage` writes to `platform_cost_ledger` only and never decrements it.
`pct_consumed` must be computed as:
```python
consumed = SUM(platform_cost_ledger.marked_up_cost_inr_paise
               WHERE customer_id = X AND billing_period_start = current_period)
quota = wallet_buckets.balance_paise  # initial allocation, unchanged by usage
pct_consumed = consumed / quota if quota > 0 else (1.0 if consumed > 0 else 0.0)
```
Do NOT use `consumed / (consumed + balance_paise)` — that formula underestimates
consumption because `balance_paise` is a fixed quota, not a live remaining value.
This requires a `platform_cost_ledger` aggregate JOIN per customer per period.

`record_usage` must resolve `provider_account_id` before inserting into `platform_cost_ledger`:
```python
provider_name = await db.scalar(SELECT provider_name FROM institutional.thread_catalog WHERE thread_id = ?)
provider_id   = await db.scalar(SELECT id FROM institutional.provider_accounts WHERE provider_name = ?)
```

## Notes

- WhatsApp stub must be mockable — inject `WhatsAppNotifier` as a dependency (not module-level import).
- `project_depletion` uses last 7 calendar days of `platform_cost_ledger` entries for rolling avg.
- `check_thresholds` is a **concrete** `MeterService` method — not in `IMeterService` ABC. Tests call it via the concrete class. `run_daily_scan` calls it per customer internally.
- All Scope 1+2 threshold names must match §2.3a exactly: `WARN_10`, `WARN_30`, `WARN_50`, `INFO_70`, `AD_WALLET_BELOW_MINIMUM`.
- Scope 3 procurement threshold names: `RUNWAY_P2` (≤30d), `RUNWAY_P1` (≤14d), `RUNWAY_P0` (≤7d), `RUNWAY_CRITICAL` (≤3d), `RUNWAY_EMERGENCY` (≤1d). Use `PROCUREMENT_POLICY.runway_thresholds` (NOT `.thresholds`) and compare `days_remaining <= rule.days_remaining_trigger`.
- **Scope 3 service query:** `SELECT provider_name, balance_paise, daily_burn_rate_paise FROM provider_accounts WHERE is_active = 1`. Compute `days_remaining = balance_paise / daily_burn_rate_paise` (skip if `daily_burn_rate_paise` is NULL or 0). **Do NOT create or query `provider_runway_view` — this table does not exist in the schema.**
- **Test fixtures for scope 3:** seed `provider_accounts (id, provider_name, balance_paise, daily_burn_rate_paise, is_active)` rows directly. Do not create `provider_runway_view`. Use `policy.rules` (the uniform `@property`) when iterating thresholds in tests — never hardcode `.thresholds` on `PROCUREMENT_POLICY`.
- **GO validation:** This WC was reviewed by EA (GOA-WC028-01) and SA (GOA-WC028-02). See `goals/GOAL-WC028-meter-alert-engine.md` for full institutional record.
