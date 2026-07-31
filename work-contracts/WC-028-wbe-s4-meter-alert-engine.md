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

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC028-01 | `src/billing-engine/meter/service.py` — `MeterService`: `record_usage(customer_id, thread_type, consumed_paise)` (writes to platform_cost_ledger), `project_depletion(customer_id, thread_type) -> int` (days remaining at 7d rolling avg burn), `check_thresholds(customer_id) -> list[AlertFired]` (fires per §2.3a scope 1+2 ladder, deduplicates via meter_alert_log); `src/billing-engine/meter/alert_policy.py` — `ThresholdRule` dataclass (name, consumed_pct_trigger, action enum: LOG/NOTIFY/FA/BLOCK, bypass_quiet_hours: bool), `ThresholdPolicy` dataclass (scope, thresholds, quiet_hours_start_ist=23, quiet_hours_end_ist=6), three singletons: `CUSTOMER_BUCKET_POLICY`, `AGENCY_POLICY`, `PROCUREMENT_POLICY` per §2.3a | reasoning | 🔲 TODO |
| WC028-02 | `src/billing-engine/meter/whatsapp_notifier.py` — `WhatsAppNotifier`: `send(customer_id, template_id, params: dict) -> bool` (stubs to 360dialog MCP call — raise `NotImplementedError` with TODO comment pointing to ADR-023; in tests mock this stub); `src/billing-engine/meter/router.py` — FastAPI prefix `/meter`: `GET /{customer_id}/status` returns `UsageStatus`, `GET /platform/margin/report` (ops-auth required), `POST /daily-scan` (internal scheduler call); mount router in `src/billing-engine/main.py` | auto | 🔲 TODO |
| WC028-03 | `tests/billing-engine/test_meter.py` — test: threshold fires at correct % (30% remaining triggers WARN_30), no double-fire within 24h deduplication window, quiet hours suppress WhatsApp (23:00–06:00 IST, notifications queued), procurement runway P0 escalation at ≤7 days, agency NULL quota produces no alert, `POST /meter/daily-scan` calls check_thresholds for all customers, `CCT-BILLINGLOOP-01` scenario: AD wallet hits zero → `alerts_sent == 1` type `AD_WALLET_BELOW_MINIMUM` — ≥90% line coverage | auto | 🔲 TODO |

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
- [ ] `check_thresholds(customer_id)` with bucket at 15% remaining → fires `WARN_10` alert, writes to `meter_alert_log`
- [ ] Second call within 24h same customer + same threshold → returns empty list (deduplicated)
- [ ] `ThresholdPolicy` quiet hours: 23:15 IST → alert created but WhatsApp NOT dispatched
- [ ] `GET /meter/{customer_id}/status` → 200 with `UsageStatus`
- [ ] `POST /meter/daily-scan` → 200 with `DailyScanResult { customers_scanned, alerts_sent }`
- [ ] `pytest tests/billing-engine/test_meter.py` → all tests pass, CCT-BILLINGLOOP-01 passes, ≥90% coverage
- [ ] `ruff check src/billing-engine/meter/ tests/billing-engine/test_meter.py` → clean

---

## Alert Deduplication Implementation Note

Create `meter_alert_log` table if not in `12-billing-engine.sql` (add a migration or CREATE IF NOT EXISTS
inside the service startup). Schema: `(id SERIAL PK, customer_id UUID, thread_type TEXT, threshold_name TEXT,
fired_at TIMESTAMPTZ, period_id TEXT)` with UNIQUE on `(customer_id, thread_type, threshold_name, period_id)`.
`period_id` = `YYYY-MM` billing period. Alert re-fires if bucket refills above threshold and drops again
within same period (period_id unchanged but threshold_name entry would have been cleared on refill).

## Notes

- WhatsApp stub must be mockable — inject `WhatsAppNotifier` as a dependency (not module-level import).
- `project_depletion` uses last 7 calendar days of `platform_cost_ledger` entries for rolling avg.
- All threshold names must match `wbe-component-spec.md §2.3a` table exactly (WARN_10, WARN_30, WARN_50).
