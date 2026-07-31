# Work Contract 030 — WBE-S6: Reconciliation Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-030
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — WBE sub-sprint 6 of 8
**Sprint Track:** Track WBE — Financial Integrity (GOAL-004)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-091 (WBE self-audit gate — financial correctness over availability), C-023 (Evidence First — every audit emits evidence record), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30 (GOAL-004 continuation)

**Depends on:** WC-029 (ProcurementService live for margin data)
**Depends on:** WC-028 (MeterService live — scheduler at 06:00 IST delegates to `meter/daily-scan`)

---

## Sprint Goal

Implement the Reconciliation Engine — the integrity floor of the entire WBE.
Daily 02:00 IST job: every rupee in every wallet bucket is proved against ledger entries.
Any discrepancy > 1 paise halts all billing (C-091 — `BILLING_INTEGRITY_HALT`).
After WC-030 merges, the WBE core is complete.

---

## Tasks

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC030-01 | `src/billing-engine/reconciliation/service.py` — `ReconciliationService`: `run_daily_audit(date: date) -> DailyAuditResult` (sum all release events against deductions per customer per day — emits evidence via C-059), `run_self_audit() -> SelfAuditResult` (compare `wallet_buckets.balance_paise` against `SUM(bucket_reservations where consumed=True)` per bucket — any mismatch > 1p sets `billing_halted=True` in Redis key `wbe:billing_halted` AND creates FA via FounderActionGenerator), `generate_margin_report(date) -> list[CustomerMarginRow]` (join platform_cost_ledger debits against wallet bucket releases to compute actual margin % per customer), `clear_halt(audit_id: str) -> None` (ops-only: clear Redis halt key after manual correction, require re-audit before clearing) | reasoning | 🔲 TODO |
| WC030-02 | `src/billing-engine/reconciliation/scheduler.py` — APScheduler `AsyncIOScheduler`: job at `02:00 Asia/Kolkata` → calls `run_daily_audit(yesterday)` then `run_self_audit()`; job at `06:00 Asia/Kolkata` → calls `POST /meter/daily-scan` via internal HTTP (httpx AsyncClient to localhost:8140); startup guard: check Redis for in-progress audit flag before starting new run (idempotency); `src/billing-engine/reconciliation/router.py` — FastAPI prefix `/reconciliation`: `GET /status` (returns last audit result + billing_halted flag), `POST /run-now` (ops-auth required — triggers immediate run), `/platform/margin/report` (ops-auth, delegates to generate_margin_report) | auto | 🔲 TODO |
| WC030-03 | `tests/billing-engine/test_reconciliation.py` — test: clean audit (no discrepancy) → `billing_halted=False`, 1-paise discrepancy detected → `billing_halted=True` + FA created in FOUNDER-ACTIONS.md, subsequent `POST /wallet/reserve` returns 503 `BILLING_INTEGRITY_HALT` when halted, `clear_halt` + re-audit (clean) → billing resumes, margin report arithmetic (margin_pct = (revenue - cost) / revenue), scheduler idempotency (second run within same audit window skipped); implement `CCT-SELFAUDIT-01` exactly as defined in `wbe-component-spec.md §4` — ≥90% line coverage | auto | 🔲 TODO |

---

## Required Inputs

| Input | File |
|---|---|
| D-07 WBE Component Spec §CCT-SELFAUDIT-01 | `architecture/reference/billing/wbe-component-spec.md` §4 — implement the CCT exactly |
| WBE Design Invariants | `architecture/reference/billing/wbe-component-spec.md` §6 — invariant #3 is the reconciliation guarantee |
| WalletService + models | `src/billing-engine/wallet/service.py`, `src/billing-engine/wallet/models.py` |
| ProcurementService | `src/billing-engine/procurement/service.py` — import for margin data (platform_cost_ledger) |
| FounderActionGenerator | `src/billing-engine/procurement/founder_action.py` — import for halt FA creation |
| DB Migration | `infrastructure/postgres/init/12-billing-engine.sql` — all billing tables |
| MeterService router | `src/billing-engine/meter/router.py` — daily-scan endpoint for scheduler to call |

---

## Definition of Done

- [ ] `from reconciliation.service import ReconciliationService` — no import errors
- [ ] `run_self_audit()` with balanced buckets → `SelfAuditResult(discrepancy_paise=0, billing_halted=False)`
- [ ] `run_self_audit()` with 2-paise discrepancy → `billing_halted=True`, Redis `wbe:billing_halted=true`, FA created
- [ ] `POST /wallet/reserve` while `billing_halted=True` → HTTP 503 `{"code": "BILLING_INTEGRITY_HALT"}`
- [ ] `clear_halt()` + `run_self_audit()` (clean) → billing resumes, 503 no longer returned
- [ ] APScheduler starts without error; `run_daily_audit` completes for a day with no ledger entries
- [ ] `GET /reconciliation/status` → 200 with last audit result
- [ ] `CCT-SELFAUDIT-01` test scenario passes
- [ ] `pytest tests/billing-engine/test_reconciliation.py` → all tests pass, ≥90% coverage
- [ ] `ruff check src/billing-engine/reconciliation/ tests/billing-engine/test_reconciliation.py` → clean

---

## C-091 Self-Audit Gate (critical invariant)

The self-audit gate is **hard** — financial correctness takes precedence over availability.
When `billing_halted=True`:
- `WalletService.reserve()` must check Redis `wbe:billing_halted` before any DB write
- If set: raise `HTTPException(503, detail={"code": "BILLING_INTEGRITY_HALT", "message": "Billing suspended pending reconciliation audit"})` 
- DO NOT add any override or bypass path — if a bypass is needed, it requires Founder FA + manual clear_halt

The halt survives service restarts (Redis persistence) and is only cleared by `clear_halt()` after a clean `run_self_audit()`.

## CCT-SELFAUDIT-01 Implementation Note

Read `wbe-component-spec.md §4 CCT-SELFAUDIT-01` and implement the exact scenario described there.
The test must: create a wallet bucket, record a reservation, manually corrupt balance_paise in DB
(simulate a calculation bug), call run_self_audit(), assert `billing_halted=True` + FA created.

## Notes

- APScheduler timezone: use `zoneinfo.ZoneInfo("Asia/Kolkata")` for IST — do not hardcode UTC offset.
- The reconciliation scheduler starts as part of FastAPI lifespan (same pattern as existing lifespan in main.py).
- `generate_margin_report` must handle the case where a customer had bucket releases but zero
  platform_cost_ledger entries (margin = 100% — pure margin, no LLM cost incurred).
