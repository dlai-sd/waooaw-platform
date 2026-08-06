# SIM-PL-002 — WC030-01b `src/billing-engine/reconciliation/scheduler.py` — `create_s
**Date:** 2026-08-06
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** WC030-01b — `src/billing-engine/reconciliation/scheduler.py` — `create_scheduler() -> AsyncIOScheduler`: job at `02:00 Asia/Kolkata` using `zoneinfo.ZoneInfo("Asia/Kolkata")` → calls `run_daily_audit(yesterday)` then `run_self_audit()`; job at `06:00 Asia/Kolkata` → POST to `{settings.WBE_INTERNAL_BASE_URL}/meter/daily-scan` via httpx AsyncClient; scheduler idempotency: set Redis `wbe:audit_in_progress:{YYYY-MM-DD}` at audit start (TTL=4h), skip run if key exists; `src/billing-engine/reconciliation/router.py` — FastAPI prefix `/reconciliation`: `GET /status` (last audit result + billing_halted flag from Redis), `POST /run-now` (ops-auth — triggers `run_self_audit()` immediately), `GET /platform/margin/report` (ops-auth, delegates to `generate_margin_report`); update `src/billing-engine/main.py` lifespan **additively** — import `create_scheduler`, add `scheduler.start()` / `scheduler.shutdown()` to the existing lifespan context manager without replacing it; **CROSS-SPRINT MODIFICATION:** modify `src/billing-engine/wallet/service.py` `WalletService.reserve()` to accept an injected `redis.Redis` client and check `wbe:billing_halted` at the top of the method before any DB write — if key exists: `raise HTTPException(503, detail={"code": "BILLING_INTEGRITY_HALT", "message": "Billing suspended pending reconciliation audit"})`
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-030

## Context
Auto-bootstrapped by pipeline. Known-safe pattern — follows established repo conventions. Low execution risk.
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
WC030-01ba — implement per WC scope: `src/billing-engine/reconciliation/scheduler.py` — `create_scheduler() -> AsyncIOScheduler`: job at `02:00 Asia/Kolkata` using `zoneinfo.ZoneInfo("Asia/Kolkata")` → calls `run_daily_audit(yesterday)` then `run_self_audit()`; job at `06:00 Asia/Kolkata` → POST to `{settings.WBE_INTERNAL_BASE_URL}/meter/daily-scan` via httpx AsyncClient; scheduler idempotency: set Redis `wbe:audit_in_progress:{YYYY-MM-DD}` at audit start (TTL=4h), skip run if key exists; `src/billing-engine/reconciliation/router.py` — FastAPI prefix `/reconciliation`: `GET /status` (last audit result + billing_halted flag from Redis), `POST /run-now` (ops-auth — triggers `run_self_audit()` immediately), `GET /platform/margin/report` (ops-auth, delegates to `generate_margin_report`); update `src/billing-engine/main.py` lifespan **additively** — import `create_scheduler`, add `scheduler.start()` / `scheduler.shutdown()` to the existing lifespan context manager without replacing it; **CROSS-SPRINT MODIFICATION:** modify `src/billing-engine/wallet/service.py` `WalletService.reserve()` to accept an injected `redis.Redis` client and check `wbe:billing_halted` at the top of the method before any DB write — if key exists: `raise HTTPException(503, detail={"code": "BILLING_INTEGRITY_HALT", "message": "Billing suspended pending reconciliation audit"})` → ruff → tests → PASS

## Dependency Graph
WC030-01ba: depends_on=[prior tasks in same sprint]

## Risk Assessment
Known-safe pattern — follows established repo conventions. Low execution risk.

## Verdict

**VERDICT: ✅ PASS**
