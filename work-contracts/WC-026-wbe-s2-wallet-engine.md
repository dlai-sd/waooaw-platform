# Work Contract 026 — WBE-S2: Wallet Engine (Buckets, Reserve, Release)

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-026
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — WBE sub-sprint 2 of 8
**Sprint Track:** Track WBE — Wallet & Billing Engine (GOAL-004)
**Gate:** G5 → MVI (WBE readiness precondition)
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-088 (Billing Profile), C-089 (Margin Floor), C-090 (Grandfather), C-038 (Pro-rata), C-059 (Traceability)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30

**Depends on:** WC-025 (scaffold + Thread Catalog live, Redis in docker-compose)
**WC number assigned by:** Product Owner (INST-011) — sequential after WC-025

---

## Sprint Goal

Implement the core wallet engine: SQLAlchemy models for `business.customer_wallets`
and `business.wallet_buckets`, wallet service (get_balance ≤50ms SLA via Redis cache,
idempotent reserve, release, activate_subscription, renew per C-090), wallet cache
(Redis write-through), FastAPI router (`GET /buckets/{wallet_id}`, `POST /reserve`,
`POST /release`). Tests ≥90% coverage.

---

## Tasks

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC026-01 | SQLAlchemy models: `src/billing-engine/wallet/models.py` — `CustomerWallet`, `WalletBucket`, `BucketReservation` mapped to `business.*` tables | `reasoning` | 🔲 TODO |
| WC026-02 | Wallet service: `src/billing-engine/wallet/service.py` — `get_balance()`, `reserve()` (idempotent via idempotency_key), `release()`, `activate_subscription()`, `renew()` (C-090 grandfather logic) | `reasoning` | 🔲 TODO |
| WC026-03 | Wallet cache: `src/billing-engine/wallet/cache.py` — Redis write-through, `get_balance_cached()` (≤50ms), `invalidate_wallet()` | `standard` | 🔲 TODO |
| WC026-04 | Wallet router: `src/billing-engine/wallet/router.py` — `GET /buckets/{wallet_id}`, `POST /reserve`, `POST /release`; mount at `/wallet` in main.py | `standard` | 🔲 TODO |
| WC026-05 | Tests: `tests/billing-engine/test_wallet.py` — reserve/release idempotency, C-090 renewal, cache hit/miss, router endpoints — ≥90% coverage | `standard` | 🔲 TODO |

---

## Required Inputs

| Input | File |
|---|---|
| D-06 Thread Catalog | `architecture/reference/billing/thread-catalog.md` |
| D-08 Schema Updates | `architecture/reference/billing/billing-schema-updates.md` |
| D-03 ADR-034 | `adr/ADR-034-waooaw-billing-engine.md` |
| D-07 WBE Component Spec | `architecture/reference/billing/wbe-component-spec.md` |
| WBE Skeleton | `src/billing-engine/skeleton/wbe_interfaces.py` |
| DB Migration | `infrastructure/postgres/init/12-billing-engine.sql` |

---

## Definition of Done

- [ ] `from wallet.models import CustomerWallet, WalletBucket` — no import errors
- [ ] `get_balance(wallet_id)` → returns cached result on second call (Redis hit)
- [ ] `reserve(wallet_id, thread_type, quantity, idempotency_key)` → idempotent (second call same key → same result, no double debit)
- [ ] `release(reservation_id)` → restores bucket quantity, emits CE evidence
- [ ] `renew(wallet_id, subscription_tier)` → applies C-090 grandfather pricing if applicable
- [ ] `GET /wallet/buckets/{wallet_id}` → 200 with bucket list
- [ ] `POST /wallet/reserve` → 200 reservation or 422 insufficient_funds
- [ ] `POST /wallet/release` → 200 on success
- [ ] `pytest tests/billing-engine/test_wallet.py` → all tests pass, ≥90% coverage

---

## C-090 Grandfather Logic (key constraint)

When renewing, if the subscription_tier matches the customer's `legacy_tier` on their
`institutional.billing_profiles` row (join via `institutional.bundle_profiles`), the
renewal price is the `legacy_price_inr` not the current `standard_price_inr`.
Applies only while `grandfather_until` date has not passed.

---

## Notes

- Flat imports: `from wallet.models import ...` — conftest.py already inserts `src/billing-engine/` into sys.path.
- Use `redis.set(key, value, ex=ttl)` not `setex()` (deprecated, filtered as error).
- Idempotency: `bucket_reservations.idempotency_key` is UNIQUE — catch IntegrityError and return existing reservation row.
- All mutations must call `ce.record_evidence()` stub (C-059) — use the existing pattern from thread_catalog.py.
- WBE skeleton interface signatures must not be modified (ADR-036).
