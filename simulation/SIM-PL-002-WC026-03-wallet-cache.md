# SIM-PL-002 — WC026-03 Wallet Redis Cache
**Date:** 2026-07-30
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC026-03 — wallet/cache.py: Redis write-through, get_balance_cached (≤50ms), invalidate_wallet
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Redis cache layer for wallet balance reads. SLA: ≤50ms on cache hit.
Write-through: every `reserve()` / `release()` / `renew()` invalidates the wallet
key before returning. TTL: 30s (same as thread_catalog — from config.settings).
Uses `redis.asyncio` client passed by dependency injection.
Pattern mirrors `markup/thread_catalog.py` exactly — proven in WC-025.

## Subtask Decomposition
WC026-03a (cache, standard) — `wallet/cache.py`: `get_balance_cached(redis, wallet_id)`,
  `set_balance_cache(redis, wallet_id, data)`, `invalidate_wallet(redis, wallet_id)` →
  `redis.set(key, json, ex=ttl)` NOT setex → ruff → PASS

## Dependency Graph
WC026-03a: depends_on=[WC026-02a service]

## Risk Assessment
- `redis.set(key, value, ex=ttl)` — confirmed working in WC-025 tests (not deprecated setex)
- JSON serialise wallet data: `json.dumps(data)` — simple dict from SQLAlchemy model
- Cache key: `wallet:{wallet_id}:balance` — no collision with thread_catalog keys
- Async client: same `redis.asyncio.Redis` pattern as thread_catalog — zero risk

## Verdict

**VERDICT: ✅ PASS**
