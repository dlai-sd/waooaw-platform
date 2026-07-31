# Work Contract 031 — GOAL-005: WBE Trial Engine + Promotions Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-031
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — GOAL-005 WBE Sprint
**Sprint Track:** Track GOAL-005 — Customer Acquisition (Trial + Promotions)
**Gate:** G5 → MVI → customer acquisition readiness
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-088 (trial is a billing mode), C-089 (trial costs tracked), C-090 (trial→paid grandfather), C-019 (informed consent — trial terms disclosed), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** ⚠️ BLOCKED — requires Founder FA with pricing decisions. See `architecture/reference/billing/customer-acquisition-spec.md` §Founder Action Gate.

**Depends on:** WC-030 (full WBE core complete), WC-025 (DB schema live)
**Depends on:** Founder FA (trial budget per agent type, discount cap %, referral credit amount)

---

## Sprint Goal

Implement WBE sub-components 6 (Trial Engine) and 7 (Promotions Engine).
Run DB migration `13-customer-acquisition.sql`. Implement TrialService (start, track, convert),
PromotionsService (coupon validation, discount application, referral credit), and tests.
When a customer is in TRIAL mode, their `customer_mode` Redis key is set — AIR PSE (WC-032) reads it.

---

## Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC031-01 | DB migration: run `infrastructure/postgres/init/13-customer-acquisition.sql` (verify all tables created: `trial_allocations`, `trial_free_unit_ledger`, `coupon_codes`, `referral_records`); `src/billing-engine/trial/models.py` — SQLAlchemy ORM: `TrialAllocation` (maps `business.trial_allocations`; FK `customer_id` → `institutional.billing_profiles(customer_id)`), `TrialFreeUnitLedger` (maps `business.trial_free_unit_ledger`); `src/billing-engine/trial/service.py` — `TrialService` (standalone concrete class, no skeleton ABC): `start_trial(customer_id, agent_type, phone_verified: bool) -> TrialStartResult` (validates `phone_verified=True` per C-019; checks no active `employment_contract` for agent_type; wraps in ONE DB transaction: insert `trial_allocations` + insert `wallet_buckets` rows directly (do NOT call `WalletService.activate_subscription` — that method requires Razorpay params) + insert `trial_free_unit_ledger` rows with `units_granted` read from `settings.TRIAL_FREE_UNITS[agent_type]` — raise HTTP 422 `TRIAL_CONFIG_MISSING` if key absent; AFTER transaction commits, set Redis `wbe:customer:{customer_id}:mode = "TRIAL"` with TTL = `(expires_at - now()).total_seconds()` — Redis is NOT inside the DB transaction; on Redis failure: log error, do not roll back DB), `check_expiry(trial_id) -> None` (called by Temporal trial-expiry saga in WC-033 — marks `status=EXPIRED`, clears Redis key), `convert_to_paid(trial_id, payment_reference) -> ConvertResult` (marks `CONVERTED`, calls `WalletService.activate_subscription` for paid subscription, applies C-090 grandfather if within 14 days); `src/billing-engine/trial/router.py` — FastAPI prefix `/trial`: `POST /start`, `GET /status/{customer_id}`, `POST /convert` (internal) | reasoning | pending | — |
| WC031-02 | `src/billing-engine/promotions/models.py` — SQLAlchemy ORM: `CouponCode` (maps `business.coupon_codes`), `ReferralRecord` (maps `business.referral_records`); `src/billing-engine/promotions/service.py` — `PromotionsService` (standalone concrete class, no skeleton ABC): `validate_coupon(code, customer_id, agent_type, tier) -> CouponValidation` (checks active, valid dates, agent_type match, tier match, `uses_count < max_uses`, AND `coupon.discount_pct <= settings.MAX_DISCOUNT_PCT` — return `error_code="DISCOUNT_EXCEEDS_CAP"` if exceeded), `apply_discount(coupon_id, customer_id, original_price_paise) -> DiscountResult` (increments `uses_count` via `SELECT FOR UPDATE` to prevent concurrent double-spend; then checks `referral_records WHERE referee_customer_id=customer_id AND coupon_id=coupon_id AND credit_status='PENDING'` — if found: call `credit_referrer(referral_id)` and set `credit_status='CREDITED'`; return `DiscountResult(..., referral_credited=bool)`), `credit_referrer(referral_id) -> None` (idempotent: `UPDATE referral_records SET credit_status='CREDITED', credited_at=NOW() WHERE referral_id=X AND credit_status='PENDING'`; check affected rows = 1; calls `WalletService` to add `credit_amount_paise` bonus to referrer wallet); `src/billing-engine/promotions/router.py` — FastAPI prefix `/promotions`: `POST /validate-coupon`, `POST /apply-discount`, `GET /referral-status/{customer_id}`; mount both `trial` and `promotions` routers in `src/billing-engine/main.py` | reasoning | pending | — |
| WC031-03 | `tests/billing-engine/test_trial.py` — CCT-TRIAL-01: second `start_trial` same customer+agent_type → 409 `TRIAL_ALREADY_USED`; CCT-TRIAL-02 (billing-layer scope only): after `start_trial`, assert Redis `wbe:customer:{id}:mode = b"TRIAL"` AND `trial_free_unit_ledger` rows created with `units_granted` from fixture env `TRIAL_FREE_UNITS` (do NOT assert PSE routing — that is WC-032 scope); trial expiry: `check_expiry()` → `status=EXPIRED` + Redis key cleared; `convert_to_paid`: C-090 grandfather applies when `converted_at - started_at <= 14d`; `phone_verified=False` → HTTP 422; `tests/billing-engine/test_promotions.py` — CCT-COUPON-01: `apply_discount` with 50% coupon → `discounted = original * 0.50`, `uses_count` incremented; `discount_pct > settings.MAX_DISCOUNT_PCT` → `DISCOUNT_EXCEEDS_CAP`; CCT-REFERRAL-01: `apply_discount` when referral PENDING → `credit_referrer` fires, `credit_status=CREDITED`; second call same referral pair → no duplicate credit (idempotent); coupon expired → `COUPON_EXPIRED`; `uses_count >= max_uses` → `COUPON_USED`; set `TRIAL_FREE_UNITS` and `MAX_DISCOUNT_PCT` via fixture env vars in conftest — ≥90% line coverage each file | auto | pending | — |

---

## Required Inputs

| Input | File |
|---|---|
| GOAL-005 Spec | `architecture/reference/billing/customer-acquisition-spec.md` — read in full |
| CCTs | `architecture/reference/billing/customer-acquisition-spec.md` §4 — implement all 4 CCTs |
| DB Migration | `infrastructure/postgres/init/13-customer-acquisition.sql` — run and verify tables |
| WalletService | `src/billing-engine/wallet/service.py` — import for bucket creation and credit operations |
| WBE Main | `src/billing-engine/main.py` — mount new routers in existing lifespan |
| WBE Skeleton | `src/billing-engine/skeleton/wbe_interfaces.py` — check for TrialABC, PromotionsABC |
| Existing 12-billing-engine migration | `infrastructure/postgres/init/12-billing-engine.sql` — check for FK targets |

---

## Definition of Done

- [ ] `13-customer-acquisition.sql` applies cleanly against existing schema
- [ ] `TrialService.start_trial("DMA", customer_id)` → `TrialStartResult` with wallet_bucket_ids
- [ ] Redis key `wbe:customer:{id}:mode` = `"TRIAL"` after start_trial
- [ ] Second `start_trial` same customer + agent_type → 409 `TRIAL_ALREADY_USED`
- [ ] `PromotionsService.validate_coupon("LAUNCH10", ...)` → `CouponValidation(valid=True, discount_pct=10)`
- [ ] `apply_discount(...)` on expired coupon → `CouponValidation(valid=False, error_code="COUPON_EXPIRED")`
- [ ] CCT-TRIAL-01, CCT-TRIAL-02, CCT-COUPON-01, CCT-REFERRAL-01 all pass
- [ ] `pytest tests/billing-engine/test_trial.py tests/billing-engine/test_promotions.py` → all pass, ≥90% coverage each
- [ ] `ruff check src/billing-engine/trial/ src/billing-engine/promotions/` → clean

---

## Notes

- `start_trial` is NOT atomic across DB + Redis. DB transaction (trial_allocation + wallet_buckets + free_unit_ledger) commits first. Redis set runs after commit. On Redis failure: log error, continue — the PSE defaults to `LlmTier.LOCAL` for unknown customer_mode, which is correct for a trial.
- Free unit caps are Founder FA values: read from `settings.TRIAL_FREE_UNITS` (env var dict) and `settings.TRIAL_DURATION_DAYS` (default 14). Tests must set these in conftest fixture env.
- `check_expiry(trial_id)` is called by the **Temporal trial-expiry saga (WC-033)**. WC-031 only implements the method; no scheduler is added in this sprint.
- `apply_discount` uses `SELECT FOR UPDATE` on `coupon_codes` row to prevent double-spend under concurrent requests.
- `credit_referrer` idempotency: `UPDATE ... WHERE credit_status='PENDING'`; if 0 rows affected, credit already fired — return silently.
- `validate_coupon` reads `settings.MAX_DISCOUNT_PCT` (int, from env var) to enforce Founder-approved cap.
- `TrialService` and `PromotionsService` have no skeleton ABCs — standalone concrete classes.
- **GO validation:** This WC reviewed by EA (GOA-WC031-01) and SA (GOA-WC031-02). See `goals/GOAL-WC031-trial-promotions.md` for full institutional record.
