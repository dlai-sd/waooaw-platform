# Customer Acquisition Specification — WAOOAW GOAL-005

**Authority:** Solution Architect (INST-005) — GOAL-005 D-01
**Architecture Decision:** ADR-034 §Amendment 1 (WBE sub-components 6+7)
**Constitutional Basis:** C-088 (Billing Profile — trial is a billing mode), C-089 (Margin Floor — trial costs must be tracked), C-090 (Grandfather — trial→paid transition), C-019 (Informed Consent — trial terms disclosed), C-049 (Honest Limitation), C-059 (Traceability)
**Status:** SPEC — awaiting Founder pricing FA before implementation
**Date:** 2026-07-31

---

## Founder Action Gate

**BLOCKED until FA received.** Implementation of any GOAL-005 WC sprint requires:

```
FA-NNN: Founder pricing decisions for GOAL-005 customer acquisition
  1. Trial budget per agent type (e.g., DMA: N LLM calls + M images for 14 days)
  2. Maximum discount % per coupon code
  3. Referral credit amount (₹ or thread-unit credits)
  4. Per-agent-type trial eligibility (can all agents be trialled, or only DMA?)
  5. Trial-to-paid conversion behaviour (wallet pre-seeded, CC details collected at trial start or end?)
```

Until this FA is signed by Founder, `autonomous_halt: true` for all GOAL-005 sprints.

---

## Cross-Module State Map (at GOAL-005 implementation time)

| Module | Expected state | Interaction type |
|---|---|---|
| `src/billing-engine/wallet/` | ✅ Complete (WC-026) | TrialService calls `WalletService.activate_subscription(mode=TRIAL)` |
| `src/billing-engine/markup/` | ✅ Complete (WC-027) | TrialService calls `BundleEngine.cost_floor()` to track trial cost |
| `src/billing-engine/meter/` | ✅ Complete (WC-028) | Trial buckets are metered identically — no meter changes needed |
| `src/billing-engine/procurement/` | ✅ Complete (WC-029) | FREE-tier (Ollama) costs ₹0 to procurement — no procurement changes |
| `src/billing-engine/reconciliation/` | ✅ Complete (WC-030) | Trial buckets included in daily audit — no reconciliation changes |
| `src/billing-engine/trial/` | ❌ New (WC-031) | New WBE sub-component 6 |
| `src/billing-engine/promotions/` | ❌ New (WC-031) | New WBE sub-component 7 |
| `src/ai-runtime/pse/router.py` | ⚠️ In progress (pre-WC-031) | Add `customer_mode=TRIAL` → force `LlmTier.LOCAL` — additive (WC-032) |
| `src/bp/subscriptions/` | ⚠️ In progress | Add `POST /subscriptions/trial-start`, Temporal trial-expiry saga (WC-033) |
| `web/` (Next.js) | ❌ Not started (WC-016) | Founder admin pages: markup designer + trial config + coupon management (WC-034) |
| `infrastructure/postgres/init/` | ⚠️ Has 12 init files | New migration `13-customer-acquisition.sql` (part of WC-031) |

---

## 1. Service Structure

```
src/billing-engine/
├── trial/                         # Sub-component 6: Trial Engine
│   ├── models.py                  # SQLAlchemy: TrialAllocation, TrialFreeUnitLedger
│   ├── service.py                 # TrialService: start_trial(), check_expiry(), convert_to_paid()
│   └── router.py                  # FastAPI: /trial/start, /trial/status/{customer_id}
│
└── promotions/                    # Sub-component 7: Promotions Engine
    ├── models.py                  # SQLAlchemy: CouponCode, ReferralRecord
    ├── service.py                 # PromotionsService: validate_coupon(), apply_discount(), credit_referrer()
    └── router.py                  # FastAPI: /promotions/validate-coupon, /promotions/referral-status

src/ai-runtime/
└── pse/
    └── router.py                  # Add: customer_mode=TRIAL → force LlmTier.LOCAL (additive)

src/bp/
└── subscriptions/
    ├── router.py                  # Add: POST /subscriptions/trial-start
    └── workflows/
        └── trial_expiry.py        # Temporal saga: trial expiry → notify → convert or lapse

web/admin/
├── markup-designer/
│   └── page.tsx                   # Founder-only: live pricing calculator + markup adjustment
├── trial-config/
│   └── page.tsx                   # Founder-only: set trial budgets per agent type
└── coupon-manager/
    └── page.tsx                   # Founder-only: create/expire coupon codes, view referral tree
```

---

## 2. API Contracts

### 2.1 Trial Engine API

```
POST /trial/start
     Body: { customer_id, agent_type, phone_verified: bool }
     → TrialStartResult { trial_id, expires_at, free_unit_caps: {thread_type: int}, wallet_bucket_ids: [uuid] }
     Precondition: customer_id has no prior paid subscription and no prior trial for this agent_type
     Side-effects: creates WalletBuckets with trial amounts, sets customer_mode=TRIAL in Redis

GET  /trial/status/{customer_id}
     → TrialStatus { trial_id, agent_type, started_at, expires_at, units_consumed: {thread_type: int}, units_remaining: {thread_type: int}, status: ACTIVE|EXPIRED|CONVERTED }

POST /trial/convert  (internal — called by Temporal saga on trial expiry + payment)
     Body: { trial_id, payment_reference }
     → ConvertResult { new_subscription_id, grandfather_applied: bool }
     Note: C-090 grandfather applies if trial_started within 14 days of conversion
```

### 2.2 Promotions Engine API

```
POST /promotions/validate-coupon
     Body: { coupon_code, customer_id, agent_type, subscription_tier }
     → CouponValidation { valid: bool, discount_pct: int, bonus_credits: {thread_type: int}, expires_at, error_code? }
     Error codes: COUPON_EXPIRED, COUPON_USED, COUPON_AGENT_MISMATCH, COUPON_TIER_MISMATCH

POST /promotions/apply-discount  (called inside BP subscription activation)
     Body: { coupon_id, customer_id, original_price_paise }
     → DiscountResult { discounted_price_paise, discount_amount_paise, referral_credited: bool }

GET  /promotions/referral-status/{referrer_customer_id}
     → ReferralStatus { referrals: [{referee_id, referred_at, credit_status: PENDING|CREDITED}], total_credits_paise }
```

---

## 3. Data Models

### trial_allocations
```sql
CREATE TABLE IF NOT EXISTS business.trial_allocations (
    trial_id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID            NOT NULL REFERENCES institutional.billing_profiles(customer_id),
    agent_type          VARCHAR(20)     NOT NULL,
    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ     NOT NULL,                    -- started_at + 14 days
    status              VARCHAR(10)     NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | EXPIRED | CONVERTED
    converted_at        TIMESTAMPTZ,
    new_subscription_id UUID,
    UNIQUE (customer_id, agent_type)                                 -- one trial per agent per customer
);
```

### trial_free_unit_ledger
```sql
CREATE TABLE IF NOT EXISTS business.trial_free_unit_ledger (
    id              SERIAL          PRIMARY KEY,
    trial_id        UUID            NOT NULL REFERENCES business.trial_allocations(trial_id),
    thread_type     VARCHAR(50)     NOT NULL,
    units_granted   INTEGER         NOT NULL,
    units_consumed  INTEGER         NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

### coupon_codes
```sql
CREATE TABLE IF NOT EXISTS business.coupon_codes (
    coupon_id       UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(20)     NOT NULL UNIQUE,
    discount_pct    SMALLINT        NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    bonus_credits   JSONB           NOT NULL DEFAULT '{}',           -- {thread_type: units}
    agent_type      VARCHAR(20),                                     -- NULL = all agents
    min_tier        VARCHAR(20),                                     -- NULL = all tiers
    max_uses        INTEGER,                                         -- NULL = unlimited
    uses_count      INTEGER         NOT NULL DEFAULT 0,
    valid_from      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ,                                     -- NULL = no expiry
    created_by      TEXT            NOT NULL DEFAULT 'founder',
    active          BOOLEAN         NOT NULL DEFAULT TRUE
);
```

### referral_records
```sql
CREATE TABLE IF NOT EXISTS business.referral_records (
    referral_id         UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_customer_id UUID           NOT NULL REFERENCES institutional.billing_profiles(customer_id),
    referee_customer_id  UUID           NOT NULL REFERENCES institutional.billing_profiles(customer_id),
    coupon_id           UUID            REFERENCES business.coupon_codes(coupon_id),
    referred_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    credit_status       VARCHAR(10)     NOT NULL DEFAULT 'PENDING',  -- PENDING | CREDITED
    credit_amount_paise INTEGER,
    credited_at         TIMESTAMPTZ
);
```

---

## 4. Constitutional Compliance Tests (CCTs)

### CCT-TRIAL-01 — One Trial Per Agent Per Customer
```
Scenario: Customer starts DMA trial. Tries to start a second DMA trial.
Assert: Second call to POST /trial/start returns 409 TRIAL_ALREADY_USED
Assert: trial_allocations UNIQUE constraint (customer_id, agent_type) prevents second row
```

### CCT-TRIAL-02 — Trial PSE Tier Override
```
Scenario: Customer in TRIAL mode requests a thread call via AIR.
Assert: PSE router sees customer_mode=TRIAL → routes to LlmTier.LOCAL (Ollama)
Assert: platform_cost_ledger.cost_paise = 0 for this call
Assert: trial_free_unit_ledger.units_consumed incremented by 1
```

### CCT-COUPON-01 — Discount Cannot Exceed Cap
```
Scenario: Coupon with discount_pct=50 applied to subscription_price=1000p.
Assert: discounted_price_paise = 500
Assert: coupon.uses_count incremented by 1
Assert: discount_pct > Founder-approved cap → HTTP 422 DISCOUNT_EXCEEDS_CAP
```

### CCT-REFERRAL-01 — Referral Credit on Conversion
```
Scenario: Customer A refers Customer B (B uses A's coupon). B converts trial to paid.
Assert: referral_records.credit_status = CREDITED for this pair
Assert: Customer A's wallet receives credit_amount_paise bonus credit
Assert: credit fires only once per referral pair (idempotent)
```

---

## 5. Dependencies

| Dependency | Type | Service |
|---|---|---|
| `WalletService.activate_subscription(mode=TRIAL)` | Internal import | billing-engine/wallet |
| `BundleEngine.cost_floor()` | Internal import | billing-engine/markup |
| `Redis customer_mode key` | Shared state | Redis — key: `wbe:customer:{customer_id}:mode` |
| `LlmTier.LOCAL` | Cross-service | ai-runtime/pse/router.py — reads Redis key |
| Temporal workflow | Orchestration | ai-runtime/temporal — trial-expiry saga |
| Razorpay payment | BP → WBE | billing-engine integrates with BP payment at conversion |
| 360dialog WhatsApp | Alert | trial-expiry notification via WhatsAppNotifier |

---

## 6. PSE Tier Override Design (WC-032)

The PSE (Provider Selection Engine) in AIR routes LLM calls by `customer_tier`.
For TRIAL customers, it must intercept this routing and force `LlmTier.LOCAL` regardless
of the customer's configured tier.

**Implementation pattern (additive — do not restructure pse/router.py):**
```python
# In pse/router.py — existing select_provider() function
# Add after existing tier lookup:
customer_mode = await redis.get(f"wbe:customer:{customer_id}:mode")
if customer_mode == b"TRIAL":
    return LlmTier.LOCAL   # Free tier during trial — zero procurement cost
```

The Redis key `wbe:customer:{customer_id}:mode` is:
- Set to `"TRIAL"` by `TrialService.start_trial()`
- Set to `"ACTIVE"` by `TrialService.convert_to_paid()` or on expiry without conversion
- TTL: matches `trial_allocations.expires_at` (max 14 days)

---

## 7. Web Portal Admin Pages (WC-034)

Three Founder-only admin pages. Requires: Founder JWT role claim `founder=true`.
All three read from WBE via API calls to `localhost:8140` (or `billing-engine` service in Docker).

### 7.1 Markup Designer
Reads `GET /pricing/thread-catalog` → renders editable table of thread types × markup %.
Founder edits a markup % → UI calls `POST /pricing/validate` (live margin check) →
on save, calls new `PATCH /pricing/thread-catalog/{thread_id}` endpoint (add to WC-034 scope).
Shows: cost floor, current price, margin % for each thread type.

### 7.2 Trial Budget Config
Reads trial allocation config from `GET /trial/config` (new internal endpoint).
Founder sets: trial_duration_days, free_unit_caps per thread_type per agent_type.
Saves via `PUT /trial/config` (persists to a `trial_config` table or Key Vault secret).

### 7.3 Coupon Manager
Reads `GET /promotions/coupons` → list of active/expired coupons with uses_count.
Founder creates new coupon: discount_pct, agent_type, max_uses, valid_until.
Founder deactivates (sets active=false) existing coupons.
Referral tree view: `GET /promotions/referral-status/{customer_id}` — shows referral chain.

---

## 8. Key Design Invariants

1. **Trial is a billing mode, not a bypass.** Every trial call is metered and recorded in `trial_free_unit_ledger`. When `units_consumed >= units_granted`, further calls return 402 TRIAL_QUOTA_EXHAUSTED.
2. **Zero cost to WAOOAW procurement.** Trial uses `LlmTier.LOCAL` (Ollama). If Ollama is unavailable, trial returns 503 TRIAL_PROVIDER_UNAVAILABLE — not a fallback to paid provider.
3. **Discount is applied at Razorpay order creation time.** The discounted price is stored in the subscription record alongside the original price for accounting purposes.
4. **Referral credit fires at conversion, not at trial start.** Credits are pending until the referee completes payment.
5. **All GOAL-005 sprints depend on Founder FA.** No implementation sprint runs with `autonomous_halt: false` until the pricing FA is signed.
