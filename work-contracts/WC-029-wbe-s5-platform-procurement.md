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
| WC029-01a | `src/billing-engine/procurement/models.py` — **SQLAlchemy ORM models** (map to existing DB tables — do NOT add columns): `ProviderAccount` maps `institutional.provider_accounts` (id, provider_name, display_name, currency, balance_paise, low_balance_threshold_days, founder_action_template); `PlatformCostLedgerEntry` maps `institutional.platform_cost_ledger` using `provider_account_id UUID` FK — NOT `provider_name`; **Pydantic response models** (computed fields, NOT DB-mapped): `ProviderRunwayStatus` (provider_name, balance_paise, daily_burn_rate_paise, days_remaining: float, last_fa_level_triggered: Optional[str]), `CostRecordRequest` (provider: str, thread_type: str, customer_id: UUID, agent_type: str, cost_paise: int, fx_rate_inr_per_usd: float); `src/billing-engine/procurement/service.py` — `ProcurementService` (standalone concrete class — no skeleton ABC): `record_cost(provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd) -> None` (resolves `provider_account_id` from `provider_name` lookup, inserts into `platform_cost_ledger` — append-only, intentionally NOT idempotent per C-007), `project_runway(provider_name) -> float` (7d rolling avg: `SUM(raw_cost_inr_paise WHERE recorded_at >= NOW()-7d) / 7` → `balance_paise / avg`; returns `float('inf')` when avg==0), `check_and_alert(provider_name) -> list[FounderActionCreated]` (reads `PROCUREMENT_POLICY` from `meter.alert_policy`; calls `FounderActionGenerator.maybe_create` for each breached threshold) | reasoning | 🔲 TODO |
| WC029-01b | `src/billing-engine/procurement/founder_action.py` — `FounderActionGenerator.maybe_create(provider, days_remaining, priority) -> Optional[str]`: reads `security/FOUNDER-ACTIONS.md`, finds max FA number via regex `r'\|\s*\*\*FA-(\d+)\*\*'`, scans for existing entry with same provider + same priority (skip if found — idempotent), appends new table row under correct P0/P1/P2 section in existing table format: `\| **FA-NNN** \| Provider {provider} runway {days_remaining}d — replenishment required \| P{n} \| C-077 procurement runway \| 1 hour \| OPEN \|`; `src/billing-engine/procurement/router.py` — FastAPI prefix `/platform/procurement`: `GET /status` → list[ProviderRunwayStatus], `POST /record-cost` body `CostRecordRequest` → 200; `GET /margin/report` (deferred from WC-028, ops-auth required); mount router in `src/billing-engine/main.py` | auto | 🔲 TODO |
| WC029-02 | `tests/billing-engine/test_procurement.py` — test: `record_cost` writes one row to `platform_cost_ledger` (verify via DB query), `record_cost` called twice for same event writes TWO rows (append-only — no dedup at DB level), `project_runway` formula (balance / 7d_avg_burn = days), FA auto-created at ≤30d threshold (P2) via `maybe_create`, FA upgraded to P1 at ≤14d and P0 at ≤7d, second `maybe_create` same provider+priority → no duplicate entry in FA file (idempotency), `GET /platform/procurement/status` → 200 list with `days_remaining`; use `tmp_path` pytest fixture for FA file — do NOT modify real `security/FOUNDER-ACTIONS.md` — ≥90% line coverage | auto | 🔲 TODO |

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
- [ ] `record_cost("anthropic", "DMA_THREAD", uuid, "dma_v1", 500, 85.0)` → inserts one row into `platform_cost_ledger` (verified by DB query)
- [ ] Two calls for same event → two rows inserted (append-only — intentionally not deduplicated at DB level)
- [ ] `project_runway("anthropic")` with 7d burn data → returns float days remaining
- [ ] `check_and_alert("anthropic")` when days_remaining = 6 → creates P0 FA entry in `security/FOUNDER-ACTIONS.md`
- [ ] Same call again (days still 6) → no duplicate FA (idempotency)
- [ ] `GET /platform/procurement/status` → 200 list of providers with `days_remaining`
- [ ] `POST /platform/procurement/record-cost` → 200 on success
- [ ] `pytest tests/billing-engine/test_procurement.py` → all pass, ≥90% coverage
- [ ] `ruff check src/billing-engine/procurement/ tests/billing-engine/test_procurement.py` → clean

---

## FounderActionGenerator Format

Read `security/FOUNDER-ACTIONS.md` first to understand the existing table structure.
FA entries are **table rows** under the appropriate P0/P1/P2 section header, using this format:
```
| **FA-NNN** | Provider {provider_name} runway {days_remaining}d — replenishment required | P{n} | C-077 procurement runway | 1 hour | OPEN |
```
Scan for the current highest FA number using regex `r'\|\s*\*\*FA-(\d+)\*\*'` to determine next FA-NNN.
Idempotency check: skip if any row already contains `{provider_name}` + same priority level (case-insensitive).
Tests MUST use a `tmp_path` pytest fixture copy of the FA file — never write to the real `security/FOUNDER-ACTIONS.md` during test runs.

## Notes

- `PROCUREMENT_POLICY` is already defined in `meter/alert_policy.py` — import it, do not redefine.
- `cost_paise` parameter is **already in INR paise** (converted by AI Runtime before calling `record_cost`). Store directly as `raw_cost_inr_paise`. Do NOT apply `fx_rate` inside the service — `fx_rate_inr_per_usd` is recorded for audit traceability only.
- Ollama `record_cost` calls always pass `cost_paise=0` and `fx_rate=0.0`.
- `project_runway` returns `float('inf')` for providers with zero 7d burn (including Ollama).
- `ProcurementService` has **no skeleton ABC** — it is a standalone concrete class.
- `record_cost` must resolve `provider_account_id` from `provider_name` via DB lookup before insert.
- **GO validation:** This WC was reviewed by EA (GOA-WC029-01) and SA (GOA-WC029-02). See `goals/GOAL-WC029-procurement-ledger.md` for full institutional record.
