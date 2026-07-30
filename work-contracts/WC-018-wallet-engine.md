# Work Contract 018 — GOAL-004: Wallet Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 018 | **Goal:** GOAL-004 | **Depends on:** WC-017 complete
**Spec:** architecture/reference/billing/wbe-component-spec.md §2.1 + §3
**Constitutional Basis:** C-059, C-076, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC018-01 | `wallet/models.py`: CustomerWallet, WalletBucket, BucketReservation SQLAlchemy models | `reasoning` |
| WC018-02 | `wallet/service.py`: get_balance (Redis), reserve (idempotent UUID key), release, refill | `reasoning` |
| WC018-03 | `wallet/cache.py`: 30s TTL Redis cache, write-through invalidation on deduction | `standard` |
| WC018-04 | `wallet/router.py`: GET /buckets/{id}, GET /buckets/{id}/{thread}, POST /reserve, POST /release | `standard` |
| WC018-05 | Tests ≥90%: balance SLA ≤50ms, reserve idempotency, 402 on empty, cache invalidation | `standard` |

## Definition of Done
- GET /buckets/{customer_id}/{thread_type} responds in ≤50ms p99 under test load
- POST /reserve returns 402 when balance = 0 (CCT-PREPAID-01 contract met)
- Idempotency: same UUID key twice returns same reservation_id, no double-deduction
