# SIM-PL-002 — WC026-04 Wallet FastAPI Router
**Date:** 2026-07-30
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC026-04 — wallet/router.py: GET /buckets/{wallet_id}, POST /reserve, POST /release; mount at /wallet
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
FastAPI router exposing wallet engine via REST. Three endpoints:
- `GET /wallet/buckets/{wallet_id}` → list WalletBucket rows for wallet
- `POST /wallet/reserve` → body: {wallet_id, thread_type, quantity, idempotency_key}
- `POST /wallet/release` → body: {reservation_id}
Dependency injection: AsyncSession + Redis client via `Depends()`.
Mounted in `main.py` at prefix `/wallet`.
Pattern mirrors `markup/thread_catalog.py` router structure.

## Subtask Decomposition
WC026-04a (router, standard) — `wallet/router.py`: three endpoints, Pydantic request/response
  models, service calls, 422 on InsufficientFundsError → ruff → PASS
WC026-04b (main, standard) — `main.py` update: `from wallet.router import router as wallet_router`
  + `app.include_router(wallet_router, prefix="/wallet")` → PASS

## Dependency Graph
WC026-04a: depends_on=[WC026-02a, WC026-03a]
WC026-04b: depends_on=[WC026-04a]

## Risk Assessment
- Pydantic v2 models: `model_config = ConfigDict(from_attributes=True)` — already in config.py
- InsufficientFundsError: custom exception, caught at router level → 422 response
- GET returns list — `response_model=list[WalletBucketSchema]` — standard pattern
- Flat import in main.py: `from wallet.router import router as wallet_router` — works with sys.path

## Verdict

**VERDICT: ✅ PASS**
