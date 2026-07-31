# WBE Component Specification — WAOOAW Billing Engine

**Authority:** Solution Architect (INST-005) — GOAL-004 D-07
**Architecture Decision:** ADR-034 (WAOOAW Billing Engine)
**Constitutional Basis:** C-088, C-089, C-090, C-091, C-038, C-049, C-051
**Status:** APPROVED — 2026-07-30 | **Amendment 1:** 2026-07-31 (threshold ladder + customer acquisition placement)
**Service:** `src/billing-engine/` | Port: 8140 | Language: Python 3.12 + FastAPI

---

## Amendment 1 — Customer Acquisition Features (2026-07-31)

**Decision:** Two customer acquisition features are scoped to a future **GOAL-005 (Customer Acquisition & Growth)** spec phase.
They are **not** part of WBE-S3 through WBE-S8. They require Founder pricing decisions before implementation can begin.

### Feature A — 2-Week Free Trial with Founder Markup Designer

**What it is:** New customers get a 2-week trial allocation (zero cash, time-bounded wallet buckets).
During trial, the PSE router forces `LlmTier.LOCAL` (Ollama, ₹0 cost). For thread types that have
no free-tier equivalent (e.g., paid video generation), a cap of N free units is granted from
WAOOAW's procurement budget. Founder can view and adjust per-agent markup and service provider
selection via a protected admin page in the Web Portal.

**Architecture placement:**
| Concern | Layer | Component |
|---|---|---|
| Trial wallet seeding (time-bounded, zero-payment buckets) | Vertical — WBE | New sub-component 6: `trial/` — `TrialService`, `TrialAllocation` model |
| PSE tier forcing to LOCAL during trial | Horizontal — AIR | `pse/router.py` — add `customer_mode=TRIAL` → override to `LlmTier.LOCAL` |
| Trial activation + expiry lifecycle | Vertical — BP | New endpoint: `POST /subscriptions/trial-start`, Temporal saga for expiry |
| Founder markup designer UI | Surface — Web Portal | Admin-only Next.js page: reads `/pricing/thread-catalog`, POSTs `/pricing/derive` |
| Free-tier image/video service cap | Vertical — WBE trial/ | `TrialAllocation` includes `free_unit_caps: dict[thread_type, int]` |

**Spec gate:** Founder must authorize trial budget per agent type (e.g., DMA trial = 50 LLM calls, 5 images) before GOAL-005 spec phase begins.

### Feature B — Discount Codes / Referral Coupons

**What it is:** Agent-specific campaign codes that reduce first-month price or grant bonus bucket credits.
Referral codes track who referred whom and credit the referrer's next billing cycle.

**Architecture placement:**
| Concern | Layer | Component |
|---|---|---|
| Coupon + referral code storage | Vertical — WBE | New sub-component 7: `promotions/` — `CouponCode`, `ReferralRecord` models |
| Coupon validation at subscription time | Vertical — WBE | `PromotionsService.validate_coupon()` called inside `POST /subscriptions/activate` |
| Referral attribution + credit | Vertical — WBE | `ReferralService.credit_referrer()` — adds bucket credits to referrer wallet |
| Campaign management UI | Surface — Web Portal | Founder admin page: create/expire coupon codes, view referral tree |
| Razorpay discount application | Vertical — WBE payment/ | Apply discount before creating Razorpay order; store pre-discount price |

**Spec gate:** Founder must decide: discount cap (%), referral credit (₹ or thread units), expiry rules, per-agent eligibility before GOAL-005 spec phase begins.

**GOAL-005 sprint sequence (after payment integration WC-031 is done):**
```
GOAL-005-D1: Founder pricing decisions for trial budget + coupon caps  ← Founder action required first
GOAL-005-D2: EA spec — TrialService + PromotionsService + DB schema
GOAL-005-WC: WBE sub-components 6 + 7 + BP trial endpoints + PSE tier override
GOAL-005-WC: Founder admin UI in Web Portal (trial config + coupon management)
```

---

## 1. Service Structure

```
src/billing-engine/
├── main.py                        # FastAPI app, lifespan, health endpoint
├── config.py                      # Settings (pydantic-settings, from env/Key Vault)
├── dependencies.py                # DB pool, Redis client, shared deps
│
├── wallet/                        # Sub-component 1: Wallet Engine
│   ├── models.py                  # SQLAlchemy models: CustomerWallet, WalletBucket, BucketReservation
│   ├── service.py                 # WalletService: get_balance, reserve, release, refill
│   ├── router.py                  # FastAPI router: /buckets/{customer_id}/...
│   └── cache.py                   # Redis cache layer (30s TTL hot buckets)
│
├── markup/                        # Sub-component 2: Markup Engine
│   ├── thread_catalog.py          # ThreadCatalogService: load, cache, invalidate
│   ├── bundle_engine.py           # BundleEngine: cost_floor(), derive_price(), validate_margin()
│   ├── router.py                  # FastAPI router: /pricing/...
│   └── models.py                  # Pydantic models: ThreadEntry, BundleProfile, PriceConfig
│
├── meter/                         # Sub-component 3: Usage Meter + Alert Engine
│   ├── service.py                 # MeterService: record_usage, project_depletion, check_thresholds
│   ├── alert_policy.py            # ThresholdPolicy: per-bundle rules, quiet hours, seasonal calendar
│   ├── proactive_offer.py         # ProactiveOfferEngine: daily velocity scan, event calendar
│   ├── whatsapp_notifier.py       # WhatsAppNotifier: format + send via razorpay-mcp/360dialog
│   └── router.py                  # FastAPI router: /meter/... (internal only)
│
├── procurement/                   # Sub-component 4: Platform Procurement Ledger
│   ├── models.py                  # ProviderAccount, PlatformCostLedger
│   ├── service.py                 # ProcurementService: record_cost, project_runway, fx_rate
│   ├── founder_action.py          # FounderActionGenerator: auto-create FA-NNN entries
│   └── router.py                  # FastAPI router: /platform/procurement/...
│
├── reconciliation/                # Sub-component 5: Reconciliation Engine
│   ├── service.py                 # ReconciliationService: daily_audit, margin_report, self_audit
│   ├── scheduler.py               # APScheduler: 02:00 IST daily reconciliation job
│   └── router.py                  # FastAPI router: /reconciliation/... (internal/ops only)
│
├── trial/                         # Sub-component 6: Trial Engine (GOAL-005 — blocked on Founder FA)
│   ├── models.py                  # TrialAllocation, TrialFreeUnitLedger
│   ├── service.py                 # TrialService: start_trial, check_expiry, convert_to_paid
│   └── router.py                  # FastAPI router: /trial/start, /trial/status, /trial/convert
│
├── promotions/                    # Sub-component 7: Promotions Engine (GOAL-005 — blocked on Founder FA)
│   ├── models.py                  # CouponCode, ReferralRecord
│   ├── service.py                 # PromotionsService: validate_coupon, apply_discount, credit_referrer
│   └── router.py                  # FastAPI router: /promotions/validate-coupon, /promotions/referral-status
│
└── tests/
    ├── test_wallet.py             # Wallet Engine: balance, reserve, release, refill (≥90% coverage C-076)
    ├── test_markup.py             # Markup Engine: cost floor, price derivation, C-089 gate
    ├── test_meter.py              # Meter: thresholds, quiet hours, velocity projection
    ├── test_procurement.py        # Procurement: cost recording, runway projection, FA generation
    ├── test_reconciliation.py     # Reconciliation: balance audit, discrepancy detection
    └── test_ccts.py               # CCTs: CCT-PREPAID-01, CCT-ONBOARD-01, CCT-BILLINGLOOP-01, CCT-SELFAUDIT-01
```

---

## 2. API Contracts

### 2.1 Wallet Engine API

```
GET  /health
     → 200 OK {"status": "healthy", "version": "..."}

GET  /buckets/{customer_id}
     → BucketSummary { customer_id, wallet_id, buckets: [{thread_type, balance_paise, reserved_paise, period_end}] }
     Cache: Redis, 30s TTL

GET  /buckets/{customer_id}/{thread_type}
     → BucketBalance { thread_type, balance_paise, reserved_paise, available_paise, period_end, pacing_mode }
     Cache: Redis, 30s TTL
     SLA: ≤ 50ms p99

POST /buckets/{customer_id}/reserve
     Body: { thread_type: str, amount: int, idempotency_key: str }
     → Reservation { reservation_id: UUID, reserved_paise: int, remaining_after_paise: int }
     → 402 Payment Required if available_paise < amount (bucket empty)
     → 409 Conflict if idempotency_key already used (duplicate request protection)
     Idempotency: 5-minute window on idempotency_key

POST /buckets/{customer_id}/release
     Body: { reservation_id: UUID, consumed: bool }
     → 200 OK if consumed=True (deducts from bucket, removes reservation)
     → 200 OK if consumed=False (releases reservation without deduction)

POST /subscriptions/activate
     Body: { customer_id, agent_type, bundle_tier, razorpay_order_id, razorpay_payment_id }
     → 200 OK { wallet_id, buckets_seeded: [...], mode_flipped_to: "LIVE" }
     Atomically: create wallet, seed all buckets per bundle profile, flip customer mode

POST /subscriptions/renew
     Body: { customer_id, employment_contract_id, new_period_start, new_period_end }
     → 200 OK { buckets_refilled: [...] }
     Checks: grandfather price enforcement (rejects if Razorpay plan mismatch without C-090 notice)

POST /topups
     Body: { customer_id, topup_type: str, quantity: int, razorpay_payment_id: str }
     → 200 OK { bucket_type, added_paise, new_balance_paise }
     Validates: topup type must exist in bundle_profiles.available_topups for this customer's bundle

POST /subscriptions/pause
     Body: { customer_id, employment_contract_id, pause_reason: str }
     → 202 Accepted { saga_id: UUID }  — initiates Temporal saga (pause campaign → freeze buckets)

POST /subscriptions/resume
     Body: { customer_id, employment_contract_id }
     → 200 OK { buckets_status: [...], wallet_status: {...} }
```

### 2.2 Markup Engine API

```
GET  /pricing/thread-catalog
     → List[ThreadEntry] { thread_id, provider, unit, raw_cost_paise, markup_pct, marked_up_paise }
     Authorization: Internal only (no customer-facing)

GET  /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
     → BundleCostFloor { bundle_tier, threads: [...], total_cost_floor_paise, infrastructure_share_paise }

POST /pricing/validate
     Body: { agent_type, bundle_tier, proposed_price_paise }
     → PriceValidation { valid: bool, cost_floor_paise, margin_pct, constitutional_minimum_margin_pct, below_floor: bool }
     If below_floor=True: returns 422 Unprocessable (never 200) and logs to pricing_floor_log

POST /pricing/derive
     Body: { agent_type, bundle_tier, target_margin_pct }
     → DerivedPrice { cost_floor_paise, target_price_paise, with_gst_paise, margin_pct }
```

### 2.3 Meter + Alert API

```
GET  /meter/{customer_id}/status
     → UsageStatus { customer_id, period_start, period_end, buckets: [{thread_type, consumed_pct, days_remaining_projection}] }

GET  /platform/margin/report
     → DailyMarginReport { date, customers: [{customer_id, agent_type, revenue_paise, actual_cost_paise, margin_pct}] }
     Authorization: Platform Operations only

POST /meter/daily-scan  (called by scheduler at 06:00 IST)
     → DailyScanResult { customers_scanned, alerts_sent, offers_generated, fa_items_created }
```

#### 2.3a ThresholdPolicy — Alert Ladder (Amendment 1, 2026-07-31)

**Scope:** Three independent threshold ladders run simultaneously. Each scope fires its own
alert channel and generates its own FA entry when applicable.

**Scope 1 — Customer wallet bucket (per thread_type):**

| Threshold | % of period allocation consumed | Action |
|---|---|---|
| WARN_10 | ≥ 90% consumed (10% remaining) | WhatsApp to customer + steward. Proactive offer triggered (topup/upgrade). |
| WARN_30 | ≥ 70% consumed (30% remaining) | WhatsApp to customer. Daily velocity projection attached. |
| WARN_50 | ≥ 50% consumed (50% remaining) | In-platform notification only. No WhatsApp unless pacing=BURST. |
| INFO_70 | ≥ 30% consumed (70% remaining) | Logged only. No alert. Used for velocity trending. |

Only the highest-severity crossing fires per 24-hour window (no alert storm on fast burn).
Quiet hours: **23:00–06:00 IST** — no WhatsApp sent; queued for 06:00 IST delivery.
Ad wallet (DMA): separate ladder — WARN_10 at ₹0 balance (AD_WALLET_BELOW_MINIMUM).

**Scope 2 — Agency sub-wallet (spending_quota_paise enforcement):**

Same percentage ladder as Scope 1 applied against `spending_quota_paise`.
NULL spending_quota → no alerts (unlimited agency child, managed externally).
Alert channel: agency owner WhatsApp + steward.
FA entry auto-created at WARN_10 if quota < 7 days of current burn rate.

**Scope 3 — WAOOAW platform procurement runway (provider accounts):**

| Days remaining at current burn | Action |
|---|---|
| ≤ 30 days | Founder Action auto-created (priority: P2). Logged. |
| ≤ 14 days | Founder Action upgraded to P1. Steward WhatsApp alert. |
| ≤ 7 days | P0 Founder Action. Steward WhatsApp every 12h until topped up. |
| ≤ 3 days | CRITICAL: autonomous sprint halted for that provider. New tasks using that provider blocked. |
| ≤ 1 day | Emergency: CE informed. All sessions using that provider gracefully suspended. |

Provider runway = `provider_accounts.balance_paise / rolling_7d_avg_daily_burn_paise`.

**Implementation notes for WBE-S4:**
- `alert_policy.py` → `ThresholdPolicy` dataclass: `{ scope, thresholds: List[ThresholdRule], quiet_hours_ist, channel }`.
- `ThresholdRule` → `{ name, consumed_pct_trigger, action: Enum[LOG|NOTIFY|FA|BLOCK] }`.
- Daily scan deduplication: `meter_alert_log(customer_id, bucket_type, threshold_name, fired_at)` — unique per (customer, bucket, threshold, period). No repeat fires within same billing period until bucket refills above threshold then drops again.
- Alert message templates live in `infrastructure/postgres/init/07-agent-prompts.sql` (WBE alert prompt IDs: `WBE_ALERT_WARN_10`, `WBE_ALERT_WARN_30`, `WBE_ALERT_PROCUREMENT_P0`).



### 2.4 Platform Procurement API

```
GET  /platform/procurement/status
     → ProcurementStatus { provider_accounts: [{provider, balance_paise, daily_burn_rate, days_remaining, threshold_fa_triggered}] }

POST /platform/procurement/record-cost
     Body: { provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd }
     → 200 OK { ledger_entry_id }
     This endpoint is called by AI Runtime after every successful provider API call
```

---

## 3. Data Models

```python
# wallet/models.py

class CustomerWallet(Base):
    __tablename__ = "customer_wallets"
    __table_args__ = {"schema": "business"}

    id: UUID
    organisation_id: UUID  # FK to business.organisations
    created_at: datetime
    billing_entity_type: str  # "DIRECT" | "AGENCY" | "RESELLER" | "CHILD" (agency-ready)
    parent_wallet_id: UUID | None  # NULL for direct customers; set for agency children

class WalletBucket(Base):
    __tablename__ = "wallet_buckets"
    __table_args__ = {"schema": "business"}

    id: UUID
    wallet_id: UUID  # FK to customer_wallets
    thread_type: str  # "llm_mid", "video_clips", "whatsapp_window", etc.
    balance_paise: int  # current available balance (units × marked-up cost)
    reserved_paise: int  # in-flight reservations (must subtract from available)
    period_start: date
    period_end: date
    pacing_mode: str  # "SPREAD" | "BURST"
    spending_quota_paise: int | None  # NULL = no limit (agency sub-wallet)

class BucketReservation(Base):
    __tablename__ = "bucket_reservations"
    __table_args__ = {"schema": "business"}

    id: UUID  # = idempotency_key (UUID v4 from caller)
    bucket_id: UUID
    reserved_paise: int
    reserved_at: datetime
    consumed: bool | None  # NULL = in-flight; True = consumed; False = released
    consumed_at: datetime | None

# markup/models.py

class ThreadEntry(BaseModel):
    thread_id: str
    provider: str
    unit: str
    raw_cost_paise: int
    fx_buffer_pct: float
    operational_overhead_pct: float
    risk_premium_pct: float
    total_markup_pct: float
    marked_up_paise: int
    is_active: bool
    founder_authorized_at: datetime

class BundleProfile(BaseModel):
    agent_type: str
    bundle_tier: str  # "starter" | "runner" | "winner"
    bundle_version: int
    thread_rations: dict[str, int]  # thread_id → quantity per period
    infrastructure_share_paise: int
    cost_floor_paise: int  # computed from thread_rations × marked_up costs
    founder_authorized_at: datetime
    is_active: bool
```

---

## 4. Constitutional Compliance Tests (CCTs)

### CCT-PREPAID-01 — Universal Prepaid Gate
```python
def test_prepaid_gate_blocks_empty_bucket():
    """AI Runtime cannot dispatch LLM call when LLM bucket is empty."""
    customer = create_test_customer(bundle="starter")
    drain_bucket(customer.id, "llm_mid")  # set to 0
    
    response = client.post(f"/buckets/{customer.id}/reserve",
                          json={"thread_type": "llm_mid", "amount": 1,
                                "idempotency_key": str(uuid4())})
    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "BUCKET_EMPTY"
```

### CCT-ONBOARD-01 — Single Onboarding Payment ≤ 90 Seconds
```python
def test_single_onboarding_activation(mock_razorpay):
    """Subscription activation + wallet seed in one call ≤ 500ms (API SLA)."""
    start = time.perf_counter()
    response = client.post("/subscriptions/activate", json={
        "customer_id": str(uuid4()),
        "agent_type": "dma_v3",
        "bundle_tier": "starter",
        "razorpay_order_id": "order_test_123",
        "razorpay_payment_id": "pay_test_456"
    })
    elapsed = time.perf_counter() - start
    
    assert response.status_code == 200
    assert elapsed < 0.5  # API call ≤ 500ms; total latency ≤ 90s includes Razorpay
    body = response.json()
    assert body["mode_flipped_to"] == "LIVE"
    assert any(b["thread_type"] == "llm_mid" for b in body["buckets_seeded"])
```

### CCT-BILLINGLOOP-01 — S-02 New Month Zero Gap
```python
def test_renewal_checks_minimum_wallet():
    """At renewal, if ad wallet below minimum for active skills, proactive refill prompt."""
    customer = create_dma_customer(skills=["paid_advertising"], ad_wallet_paise=80000)
    
    result = wbe.renew_subscription(customer.id, new_period_start=date.today())
    
    assert result.alerts_sent == 1
    assert result.alerts_sent_type == "AD_WALLET_BELOW_MINIMUM"
    # WhatsApp notification queued (tested via mock notifier)
```

### CCT-SELFAUDIT-01 — Balance Reconciliation Integrity
```python
def test_self_audit_detects_discrepancy():
    """If computed bucket balance ≠ ledger sum by > 1 paise, all billing halts."""
    customer = create_test_customer()
    # Manually corrupt a bucket balance to simulate bug
    corrupt_bucket_balance(customer.wallet_id, "llm_mid", delta_paise=5)
    
    audit_result = reconciliation_service.run_self_audit()
    
    assert audit_result.discrepancies_found == 1
    assert audit_result.billing_halted == True
    assert audit_result.founder_action_created == True
    # WBE refuses new reserve calls while halted
    response = client.post(f"/buckets/{customer.id}/reserve",
                          json={"thread_type": "llm_mid", "amount": 1,
                                "idempotency_key": str(uuid4())})
    assert response.status_code == 503
    assert "BILLING_INTEGRITY_HALT" in response.json()["detail"]["code"]
```

---

## 5. Dependencies

```toml
# src/billing-engine/pyproject.toml
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = "^0.32"
sqlalchemy = "^2.0"
asyncpg = "^0.29"
redis = "^5.0"
pydantic = "^2.8"
pydantic-settings = "^2.4"
apscheduler = "^3.10"
httpx = "^0.27"       # WBE client calls to razorpay-mcp, 360dialog
tenacity = "^8.5"     # retry logic for provider API calls

[tool.poetry.dev-dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
pytest-cov = "^5.0"
httpx = "^0.27"       # TestClient
```

---

## 6. Key Design Invariants

1. **Balance check is synchronous and cached.** Redis cache (30s TTL) serves 99% of balance
   checks without hitting PostgreSQL. Cache invalidation on every deduction — no stale reads.

2. **Reservation-before-dispatch is mandatory.** AI Runtime MUST call `/reserve` before
   the provider API call and `/release` after. A provider call without a prior reservation
   is an audit violation. WBE logs all reservation-less cost events to procurement ledger
   for reconciliation.

3. **WBE self-audit gate is hard.** Any balance discrepancy > 1 paise halts all billing
   operations. No customer notification is sent with an incorrect balance. The halt is
   constitutional (C-091) — financial correctness takes priority over availability.

4. **C-090 grandfather pricing is enforced at renewal.** WBE compares the renewal Razorpay
   plan ID against `employment_contracts.agreed_monthly_price_paise`. If plan price
   exceeds agreed price AND no C-090 notice is acknowledged → renewal rejected with
   GRANDFATHER_PRICE_VIOLATION error.

5. **C-049 disclosure is agent's responsibility, not WBE's.** WBE signals bucket status
   to AI Runtime via the reserve response (402 + BUCKET_EMPTY). The AI Runtime passes
   this to the agent. The agent generates the C-049 disclosure in the customer's language
   and vocabulary. WBE never generates customer-visible messages.
