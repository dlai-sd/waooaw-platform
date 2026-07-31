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

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC031-01 | DB migration: run `infrastructure/postgres/init/13-customer-acquisition.sql` (verify all tables created); `src/billing-engine/trial/models.py` — SQLAlchemy: `TrialAllocation`, `TrialFreeUnitLedger`; `src/billing-engine/trial/service.py` — `TrialService`: `start_trial(customer_id, agent_type) -> TrialStartResult` (creates TrialAllocation + WalletBuckets via WalletService + sets Redis `wbe:customer:{id}:mode=TRIAL` with TTL=14d), `check_expiry(trial_id)` (marks EXPIRED + clears Redis key), `convert_to_paid(trial_id, payment_ref) -> ConvertResult` (marks CONVERTED + calls WalletService.activate_subscription + applies C-090 grandfather); `src/billing-engine/trial/router.py` — FastAPI prefix `/trial`: `POST /start`, `GET /status/{customer_id}`, `POST /convert` (internal) | reasoning | 🔲 TODO |
| WC031-02 | `src/billing-engine/promotions/models.py` — SQLAlchemy: `CouponCode`, `ReferralRecord`; `src/billing-engine/promotions/service.py` — `PromotionsService`: `validate_coupon(code, customer_id, agent_type, tier) -> CouponValidation`, `apply_discount(coupon_id, customer_id, original_price_paise) -> DiscountResult` (idempotent — coupon.uses_count via SELECT FOR UPDATE), `credit_referrer(referral_id) -> None` (adds paise credits to referrer wallet via WalletService); `src/billing-engine/promotions/router.py` — FastAPI prefix `/promotions`: `POST /validate-coupon`, `POST /apply-discount`, `GET /referral-status/{customer_id}`; mount both routers in `src/billing-engine/main.py` | reasoning | 🔲 TODO |
| WC031-03 | `tests/billing-engine/test_trial.py` — CCT-TRIAL-01 (one trial per agent per customer, second returns 409), CCT-TRIAL-02 (trial mode sets Redis key + WalletBuckets created with trial amounts), trial expiry clears Redis key, convert_to_paid: C-090 grandfather applies if within 14d; `tests/billing-engine/test_promotions.py` — CCT-COUPON-01 (discount arithmetic, uses_count incremented), CCT-REFERRAL-01 (credit fires at conversion, idempotent), coupon expired returns COUPON_EXPIRED, coupon max_uses exceeded returns COUPON_USED — each test file ≥90% line coverage | auto | 🔲 TODO |

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

- `start_trial` must be atomic: WalletBucket creation + Redis set + TrialAllocation insert in one
  DB transaction. If wallet creation fails, roll back trial_allocation row.
- `apply_discount` uses `SELECT FOR UPDATE` on `coupon_codes` row to prevent double-spend
  under concurrent requests (two customers using same single-use coupon simultaneously).
- Trial Redis key TTL = `(trial_allocation.expires_at - now()).total_seconds()` — set at start_trial time.
