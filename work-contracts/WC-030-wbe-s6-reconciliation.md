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
| WC030-01a | `src/billing-engine/reconciliation/service.py` — `ReconciliationService` (standalone concrete class — no skeleton ABC): `run_daily_audit(date: date) -> DailyAuditResult` (for each `bucket_reservation WHERE consumed=True AND consumed_at::date = date`, verify a matching `platform_cost_ledger` row with `bucket_reservation_id` exists; flag unlinked reservations as `DailyAuditResult.unlinked_reservations`; emit C-023 evidence record regardless of outcome); `run_self_audit() -> SelfAuditResult` (for every active `wallet_bucket`: compute `expected_balance = SUM(topup_orders.amount_paise WHERE employment_contract_id = bucket.employment_contract_id AND thread_type = bucket.thread_type AND applied_at IS NOT NULL) - SUM(bucket_reservations.reserved_paise WHERE consumed=True AND bucket_id = X)`; if `\|balance_paise - expected_balance\| > 1`: set Redis `wbe:billing_halted = "1"` (no TTL), call `FounderActionGenerator.maybe_create`, return `SelfAuditResult(discrepancy_paise=delta, billing_halted=True, founder_action_created=True)`); `generate_margin_report(date) -> list[CustomerMarginRow]` (join consumed `bucket_reservations.reserved_paise` as revenue against `platform_cost_ledger.raw_cost_inr_paise` as cost; `margin_pct = (revenue - cost) / revenue`; handle zero-cost = 100% margin); `clear_halt() -> None` (ops-only: deletes `wbe:billing_halted` from Redis — no parameters, no audit_id required; operator must call `POST /reconciliation/run-now` after to confirm clean state) | reasoning | 🔲 TODO |
| WC030-01b | `src/billing-engine/reconciliation/scheduler.py` — `create_scheduler() -> AsyncIOScheduler`: job at `02:00 Asia/Kolkata` using `zoneinfo.ZoneInfo("Asia/Kolkata")` → calls `run_daily_audit(yesterday)` then `run_self_audit()`; job at `06:00 Asia/Kolkata` → POST to `{settings.WBE_INTERNAL_BASE_URL}/meter/daily-scan` via httpx AsyncClient; scheduler idempotency: set Redis `wbe:audit_in_progress:{YYYY-MM-DD}` at audit start (TTL=4h), skip run if key exists; `src/billing-engine/reconciliation/router.py` — FastAPI prefix `/reconciliation`: `GET /status` (last audit result + billing_halted flag from Redis), `POST /run-now` (ops-auth — triggers `run_self_audit()` immediately), `GET /platform/margin/report` (ops-auth, delegates to `generate_margin_report`); update `src/billing-engine/main.py` lifespan **additively** — import `create_scheduler`, add `scheduler.start()` / `scheduler.shutdown()` to the existing lifespan context manager without replacing it; **CROSS-SPRINT MODIFICATION:** modify `src/billing-engine/wallet/service.py` `WalletService.reserve()` to accept an injected `redis.Redis` client and check `wbe:billing_halted` at the top of the method before any DB write — if key exists: `raise HTTPException(503, detail={"code": "BILLING_INTEGRITY_HALT", "message": "Billing suspended pending reconciliation audit"})` | reasoning | 🔲 TODO |
| WC030-03 | `tests/billing-engine/test_reconciliation.py` — test: clean `run_self_audit()` → `billing_halted=False`; manually corrupt `balance_paise` in DB (add 2 paise via direct SQL, bypassing ORM) → `run_self_audit()` → `billing_halted=True` + Redis `wbe:billing_halted` set + FA created; `POST /wallet/.../reserve` while halted → HTTP 503 `BILLING_INTEGRITY_HALT`; `clear_halt()` + `run_self_audit()` (fix balance first) → billing resumes; `run_daily_audit` with matched cost-to-reservation → zero unlinked; margin report arithmetic (`margin_pct = (revenue-cost)/revenue`); scheduler idempotency (Redis `wbe:audit_in_progress` key blocks second run); implement `CCT-SELFAUDIT-01` exactly as in `wbe-component-spec.md §4`; use `fakeredis` or dedicated test Redis — never share Redis state with production keys; ≥90% line coverage | auto | 🔲 TODO |

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
- [ ] `run_self_audit()` with 2-paise discrepancy → `billing_halted=True`, Redis `wbe:billing_halted` set (no TTL), FA created
- [ ] `POST /wallet/.../reserve` while `billing_halted=True` → HTTP 503 `{"code": "BILLING_INTEGRITY_HALT"}`
- [ ] `clear_halt()` (no args) + `run_self_audit()` (clean) → billing resumes, 503 no longer returned
- [ ] APScheduler starts without error; `run_daily_audit` completes for a day with no ledger entries
- [ ] `GET /reconciliation/status` → 200 with last audit result
- [ ] `CCT-SELFAUDIT-01` test scenario passes
- [ ] `pytest tests/billing-engine/test_reconciliation.py` → all tests pass, ≥90% coverage
- [ ] `ruff check src/billing-engine/reconciliation/ tests/billing-engine/test_reconciliation.py` → clean

---

## C-091 Self-Audit Gate (critical invariant)

The self-audit gate is **hard** — financial correctness takes precedence over availability.
When `billing_halted=True`:
- `WalletService.reserve()` (in `wallet/service.py`) checks Redis `wbe:billing_halted` at the top of the method before any DB write
- Inject `redis.Redis` client into `WalletService.__init__` — this is a **cross-sprint modification** to code from WC-026
- If key exists: raise `HTTPException(503, detail={"code": "BILLING_INTEGRITY_HALT", "message": "Billing suspended pending reconciliation audit"})`
- DO NOT add any override or bypass path — clearing requires Founder FA + `clear_halt()` + clean re-audit

The halt key `wbe:billing_halted` has **no TTL** — it survives restarts and is only removed by `clear_halt()`.
Use `wbe:audit_in_progress:{YYYY-MM-DD}` (TTL=4h) for scheduler deduplication.

## CCT-SELFAUDIT-01 Implementation Note

Read `wbe-component-spec.md §4 CCT-SELFAUDIT-01` and implement the exact scenario described there.
The test must: create a wallet bucket, record a reservation, manually corrupt balance_paise in DB
(simulate a calculation bug), call run_self_audit(), assert `billing_halted=True` + FA created.

## Notes

- APScheduler timezone: use `zoneinfo.ZoneInfo("Asia/Kolkata")` for IST — do not hardcode UTC offset.
- Internal HTTP URL for scheduler: read `settings.WBE_INTERNAL_BASE_URL` (env var, default `http://localhost:8140`) — never hardcode.
- `create_scheduler()` factory in `scheduler.py` exports the scheduler; `main.py` starts/stops it within the **existing lifespan context** — additive only, do not replace existing startup/shutdown code.
- Tests must use `fakeredis` (or a separate Redis DB index) — never write `wbe:billing_halted` to production Redis during tests.
- `generate_margin_report` handles zero-cost customers (Ollama-only): `margin = 100%` when `platform_cost_ledger` entries for the customer sum to 0.
- **GO validation:** This WC reviewed by EA (GOA-WC030-01) and SA (GOA-WC030-02). See `goals/GOAL-WC030-reconciliation-engine.md` for full institutional record.
