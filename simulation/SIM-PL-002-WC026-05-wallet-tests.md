# SIM-PL-002 — WC026-05 Wallet Engine Tests (≥90% coverage)
**Date:** 2026-07-30
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC026-05 — tests/billing-engine/test_wallet.py: reserve/release idempotency, C-090, cache, router
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Test suite for WC026-01 through WC026-04. Uses fakeredis.aioredis.FakeRedis for cache tests
(same as test_thread_catalog.py). SQLAlchemy async tests use AsyncMock for DB session.
HTTP endpoint tests use starlette TestClient (sync). ≥90% coverage gate via pyproject.toml.
Pattern mirrors `tests/billing-engine/test_thread_catalog.py` exactly — proven structure.

## Subtask Decomposition
WC026-05a (tests, standard) — `TestWalletCacheLayer` (async, 5 tests): cache hit, cache miss,
  invalidation, TTL, concurrent reserve → `asyncio.run()` for sync-to-async bridge → PASS
WC026-05b (tests, standard) — `TestWalletServiceIdempotency` (async, 4 tests): reserve same
  idempotency_key twice → same result, no double debit; release → balance restored;
  renew with grandfather within date; renew without grandfather → ruff → PASS
WC026-05c (tests, standard) — `TestWalletHttpEndpoints` (sync TestClient, 4 tests): GET buckets,
  POST reserve 200, POST reserve 422 (insufficient), POST release 200 → PASS
WC026-05d (tests, standard) — `TestC090GrandfatherInvariant` (3 structural tests): legacy_price
  applied when grandfather_until in future; standard_price applied when expired → PASS

## Dependency Graph
WC026-05a: depends_on=[WC026-03a]
WC026-05b: depends_on=[WC026-02a, WC026-02b]
WC026-05c: depends_on=[WC026-04a, WC026-04b]
WC026-05d: depends_on=[WC026-02a]

## Risk Assessment
- fakeredis.aioredis.FakeRedis: already installed (used by test_thread_catalog.py) — zero risk
- asyncio.run() for sync test bodies: confirmed working in test_thread_catalog.py
- httpx2 for TestClient: already installed — no new dep needed
- IntegrityError simulation: mock `session.commit()` to raise IntegrityError on second call
- C-090 date boundary: freeze datetime with `unittest.mock.patch` on `datetime.date.today`
- ruff pyproject.toml filterwarnings=["error"]: no setex calls, no deprecated APIs → PASS

## Verdict

**VERDICT: ✅ PASS**
