# SIM-PL-002 — WC026-01 Wallet SQLAlchemy Models
**Date:** 2026-07-30
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC026-01 — SQLAlchemy models: CustomerWallet, WalletBucket, BucketReservation
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Maps `business.customer_wallets`, `business.wallet_buckets`, `business.bucket_reservations`
tables (created by `12-billing-engine.sql`) to SQLAlchemy ORM models.
No new DB tables — pure model layer. Flat imports from `src/billing-engine/`.
Stack: Python 3.12, SQLAlchemy 2.x declarative. Constitutional: C-059 (traceability).

## Subtask Decomposition
WC026-01a (models, reasoning) — `wallet/models.py`: three ORM classes, relationships,
  `__tablename__` with `schema="business"`, idempotency_key UniqueConstraint → ruff → PASS
WC026-01b (models, reasoning) — `wallet/__init__.py`: empty init for flat import → PASS

## Dependency Graph
WC026-01a: depends_on=[12-billing-engine.sql committed]
WC026-01b: depends_on=[WC026-01a]

## Risk Assessment
- SQLAlchemy 2.x syntax: `mapped_column()` + `Mapped[T]` — standard, no surprises
- `schema="business"` on `__table_args__` — confirmed supported by SQLAlchemy 2.x
- UniqueConstraint on `idempotency_key` — direct mapping from DB unique index
- Flat import path: `from wallet.models import ...` — conftest adds `src/billing-engine/` to sys.path

## Verdict

**VERDICT: ✅ PASS**
