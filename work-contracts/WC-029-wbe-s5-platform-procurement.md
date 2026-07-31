# Work Contract 029 — WBE-S5: Platform Procurement Ledger

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-029
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — WBE sub-sprint 5 of 8
**Sprint Track:** Track WBE — Platform Cost Visibility (GOAL-004)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-077 (WAOOAW dev budget ceiling ₹5,000/month — procurement ledger enforces this), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30 (GOAL-004 continuation)

**Depends on:** WC-028 (ThresholdPolicy singletons live — `PROCUREMENT_POLICY` imported from `meter/alert_policy.py`)
**WC number assigned by:** Product Owner (INST-011) — sequential after WC-028

---

## Sprint Goal

Every provider API call (Anthropic, Sarvam, Google, Azure, Ollama) costs WAOOAW real money.
This sprint records every cost in a ledger, projects runway per provider, auto-generates
Founder Actions when threshold thresholds breach, and exposes platform procurement status.
Short sprint — 2 tasks.

---

## Tasks

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC029-01 | `src/billing-engine/procurement/models.py` — SQLAlchemy+Pydantic: `ProviderAccount` (provider_name, balance_paise, daily_burn_rate_paise, days_remaining, last_fa_level_triggered), `PlatformCostLedger` (provider_name, thread_type, customer_id, cost_paise, fx_rate_inr_per_usd, recorded_at); `src/billing-engine/procurement/service.py` — `ProcurementService`: `record_cost(provider, thread_type, customer_id, cost_paise, fx_rate) -> None` (idempotent via recorded_at+customer_id+thread_type composite, updates daily_burn_rate rolling avg), `project_runway(provider_name) -> int` (days at 7d rolling burn), `check_and_alert(provider_name) -> list[FounderActionCreated]` (calls PROCUREMENT_POLICY from meter.alert_policy, creates FA entries for 30d/14d/7d thresholds per §2.3a scope 3); `src/billing-engine/procurement/founder_action.py` — `FounderActionGenerator.maybe_create(provider, days_remaining, priority) -> Optional[str]` (writes FA-NNN entry to security/FOUNDER-ACTIONS.md via append — idempotent: skip if same provider+level already in file, return FA-NNN or None); `src/billing-engine/procurement/router.py` — FastAPI prefix `/platform/procurement`: `GET /status` returns list of `ProviderRunwayStatus`, `POST /record-cost` (called by AI Runtime after each provider call) | reasoning | 🔲 TODO |
| WC029-02 | `tests/billing-engine/test_procurement.py` — test: cost recording writes to platform_cost_ledger, runway projection formula (balance / rolling_avg_burn = days), FA auto-created at ≤30d threshold (P2), FA upgraded to P1 at ≤14d, P0 at ≤7d, second call same provider+level does NOT create duplicate FA, fx_rate applied correctly to USD provider costs, `GET /platform/procurement/status` returns all providers with days_remaining — ≥90% line coverage | auto | 🔲 TODO |

---

## Required Inputs

| Input | File |
|---|---|
| D-07 WBE Component Spec §2.4 + §2.3a §Scope 3 | `architecture/reference/billing/wbe-component-spec.md` |
| Procurement threshold policy | `src/billing-engine/meter/alert_policy.py` PROCUREMENT_POLICY singleton (import — do not redefine) |
| DB Migration | `infrastructure/postgres/init/12-billing-engine.sql` — provider_accounts, platform_cost_ledger tables |
| ADR-029 Multi-provider LLM | `adr/ADR-029-multi-provider-llm-strategy.md` — provider names (anthropic, sarvam, google, azure, ollama) |
| Founder Actions format | `security/FOUNDER-ACTIONS.md` — read the existing format before implementing FounderActionGenerator |
| WBE Skeleton interfaces | `src/billing-engine/skeleton/wbe_interfaces.py` |

---

## Definition of Done

- [ ] `from procurement.service import ProcurementService` — no import errors
- [ ] `record_cost("anthropic", "DMA_THREAD", uuid, 500, 85.0)` → writes to platform_cost_ledger
- [ ] Second call same provider+customer+thread within same minute → idempotent (no duplicate row)
- [ ] `project_runway("anthropic")` with 7d burn data → returns int days remaining
- [ ] `check_and_alert("anthropic")` when days_remaining = 6 → creates P0 FA entry in `security/FOUNDER-ACTIONS.md`
- [ ] Same call again (days still 6) → no duplicate FA (idempotency)
- [ ] `GET /platform/procurement/status` → 200 list of providers with `days_remaining`
- [ ] `POST /platform/procurement/record-cost` → 200 on success
- [ ] `pytest tests/billing-engine/test_procurement.py` → all pass, ≥90% coverage
- [ ] `ruff check src/billing-engine/procurement/ tests/billing-engine/test_procurement.py` → clean

---

## FounderActionGenerator Format

Read `security/FOUNDER-ACTIONS.md` first. Append new entries in the existing format.
FA number: scan existing `FA-NNN` entries, use next sequential number.
Entry format (match existing style exactly):
```
## FA-NNN (auto-generated): Provider {provider_name} runway {days_remaining}d — replenishment required
**Priority:** P{0|1|2}
**Generated:** {ISO date}
**Trigger:** procurement runway check — {provider_name} balance projects depletion in {days_remaining} days
**Action required:** Top up {provider_name} API account. Minimum: 30d runway at current burn rate.
**Status:** OPEN
```

## Notes

- `PROCUREMENT_POLICY` is already defined in `meter/alert_policy.py` — import it, do not redefine.
- FX rate: `cost_paise = cost_usd × fx_rate_inr_per_usd × 100`. Ollama is always 0 cost.
- `project_runway` returns `float('inf')` for Ollama (no depletion) and for providers with `balance_paise = 0` AND `daily_burn_rate = 0`.
