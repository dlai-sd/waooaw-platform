# SIM-PL-002 — WC028-02: WhatsAppNotifier stub + /meter router + main.py mount
**Date:** 2026-08-04
**Author:** Platform IT Expert (INST-010) — pre-execution simulation
**Task:** WC028-02 — `meter/whatsapp_notifier.py` + `meter/router.py` + mount in `main.py`
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-028

## Context
HTTP interface for the Meter+Alert Engine: expose usage status and daily-scan trigger endpoint.
WhatsAppNotifier stubs to 360dialog MCP (ADR-023) — raises NotImplementedError with TODO.
Constitutional basis: C-059 (Traceability), ADR-002 (spec-first), ADR-020 (MCP integration pattern).

## Subtask Decomposition
- WC028-02a — `meter/whatsapp_notifier.py`: `WhatsAppNotifier.send()` — stub raising
  `NotImplementedError` with TODO pointing to ADR-023. No DB, no network in tests.
- WC028-02b — `meter/router.py`: FastAPI `APIRouter(prefix="/meter")`:
  - `GET /{customer_id}/status` → delegates to `MeterService.project_depletion()` → `UsageStatus`
  - `POST /daily-scan` → calls `MeterService.run_daily_scan()` → `DailyScanResult`
  Note: `GET /platform/margin/report` is explicitly deferred to WC-029.
- WC028-02c — `src/billing-engine/main.py`: additive `app.include_router(meter_router, prefix="/meter")`
  No modification of existing lifespan, CORS, or wallet/markup routers.

## Dependency Graph
WC028-02a: depends_on=[] — pure stub
WC028-02b: depends_on=[WC028-01 (MeterService importable), WC028-02a]
WC028-02c: depends_on=[WC028-02b] — additive only, no existing code modified

## Risk Assessment
**LOW.** Established router pattern (WC-026 wallet/router.py, WC-027 markup/router.py).
`main.py` mount is additive — existing CORS, lifespan, wallet and markup routers unchanged.
WhatsAppNotifier is a NotImplementedError stub — no real integration.
model_hint=auto — correct for deterministic scaffold with known pattern.

## Pre-execution Checks (local)
- PASS: `UsageStatus` and `DailyScanResult` types defined in `skeleton/wbe_interfaces.py`
- PASS: `main.py` mount pattern identical to WC-026/027 — no structural risk
- PASS: ADR-020 MCP integration pattern documented — NotImplementedError stub is compliant approach
- PASS: No `GET /platform/margin/report` in scope — correctly deferred per WC-028 task spec

## Verdict

**VERDICT: ✅ PASS — router + notifier stub + mount, LOW risk, well-established pattern**
