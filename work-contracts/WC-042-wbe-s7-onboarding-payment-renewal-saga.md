# Work Contract WC-042 — WBE-S7: Single Onboarding Payment + Renewal Saga

**Office:** Platform IT Expert (INST-010)
**Sprint:** WC-042
**Goal:** GOAL-004 (WBE) — WBE-S7
**Founder Authorization:** FA-029 (2026-08-07 — Yogesh Khandge)
**Constitutional Basis:** C-023, C-059, C-076, C-088, C-089, C-090, ADR-022 Amendment §1.2/§1.3/§1.4, ADR-034

---

## Sprint Goal

One Razorpay payment tap activates subscription + seeds wallet in ≤2 minutes (lower envs: 100% coupon bypass). Progressive renewal failure policy (Days 1/3/7/14) implemented as Temporal workflow saga.

---

## Required Inputs

| Input | File | Status |
|---|---|---|
| ADR-022 §1.2 Single Onboarding Payment | `adr/ADR-022-payment-processing-razorpay-india.md` | ✅ |
| ADR-022 §1.3 Progressive Renewal Failure Policy | `adr/ADR-022-payment-processing-razorpay-india.md` | ✅ |
| ADR-022 §1.4 Grandfather Pricing Enforcement | `adr/ADR-022-payment-processing-razorpay-india.md` | ✅ |
| D-07 §2.1 Wallet Engine API | `architecture/reference/billing/wbe-component-spec.md` | ✅ |
| D-08 price_change_notices table | `infrastructure/postgres/init/12-billing-engine.sql` | ✅ |
| Founder env var decision | FA-029 | ✅ |

---

## Tasks

| Task | Scope | Files |
|---|---|---|
| WC042-01 | `src/billing-engine/payment/` — Razorpay client (env vars), OnboardingService.create_onboarding_order(), demo/UAT coupon bypass | `payment/razorpay_client.py`, `payment/models.py`, `payment/onboarding.py` |
| WC042-02 | `payment.captured` webhook handler — verify HMAC signature, call wallet.activate_subscription() atomically; payment_intents idempotency table | `payment/webhook.py`, `payment/router.py`, `18-wbe-s7-payment.sql` |
| WC042-03 | C-090 grandfather check at renewal — enhance wallet.renew() to block price increase without an acknowledged price_change_notice | `wallet/service.py` |
| WC042-04 | `RenewalFailureSaga` Temporal workflow in BP — Day1/Day3/Day7/Day14 states; campaign pause gate at Day7 | `src/business-platform/Workflows/RenewalFailureSaga.cs` |
| WC042-05 | Tests ≥90%: CCT-ONBOARD-01 (payment → subscription + wallet ≤2min); renewal saga Day1/3/7/14 states; grandfather price block; webhook idempotency | `tests/billing-engine/test_payment.py`, `tests/business-platform.Tests/Billing/RenewalFailureSagaTests.cs` |

---

## Definition of Done

- [ ] `POST /payments/onboarding-order` creates Razorpay order with subscription + wallet seed amount
- [ ] Demo/UAT environments: DEMOWAOOAW/UATWAOOAW coupon → ₹0 order, bypass Razorpay API
- [ ] `POST /payments/webhooks/razorpay` handles `payment.captured` — HMAC verified, idempotent, wallet seeded
- [ ] `wallet.renew()` rejects price increase without acknowledged `price_change_notice` (C-090)
- [ ] `RenewalFailureSaga` Temporal workflow: Day1 alert → Day3 degraded → Day7 suspended + campaign pause → Day14 terminated
- [ ] CCT-ONBOARD-01 passing (one payment → SUBSCRIBED mode + wallet buckets in ≤2min)
- [ ] All tests passing · ruff clean · ≥90% coverage · zero regressions
- [ ] VERSION bumped, CHANGELOG entry, PROJECT_STATE updated
