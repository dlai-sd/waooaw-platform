# SIM-PL-002 — WC026-02 Wallet Service (reserve / release / renew)
**Date:** 2026-07-30
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC026-02 — wallet/service.py: get_balance, reserve, release, activate_subscription, renew
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Core wallet business logic. `reserve()` must be idempotent via `idempotency_key`
UNIQUE constraint (catch `IntegrityError`, return existing row). `renew()` must
apply C-090 grandfather pricing when `legacy_tier` matches and `grandfather_until`
has not passed. All mutations call `ce.record_evidence()` stub (C-059).
Stack: Python 3.12, SQLAlchemy async session, asyncpg. Constitutional: C-088, C-089, C-090, C-059.

## Subtask Decomposition
WC026-02a (service, reasoning) — `wallet/service.py`: async functions with SQLAlchemy
  AsyncSession, IntegrityError catch for idempotency, C-090 grandfather date check → ruff → PASS
WC026-02b (service, reasoning) — `wallet/ce_stub.py`: thin `record_evidence(action, payload)`
  stub that logs to audit_records table (mirrors AIR pattern) → ruff → PASS

## Dependency Graph
WC026-02a: depends_on=[WC026-01a models]
WC026-02b: depends_on=[]

## Risk Assessment
- IntegrityError import: `from sqlalchemy.exc import IntegrityError` — standard
- C-090 date check: `datetime.date.today() <= billing_profile.grandfather_until` — straightforward
- Async session: `async with AsyncSession(engine) as session:` — same pattern as thread_catalog.py
- `activate_subscription()`: sets `wallet_buckets.activated_at`, calls ce_stub — no ambiguity
- ruff: LOG015/G004 in debug statements — handled by per-file-ignores in pyproject.toml

## Verdict

**VERDICT: ✅ PASS**
