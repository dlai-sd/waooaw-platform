# ADR-022 — Payment Processing: Razorpay India

**Status:** Accepted
**Date:** 2026-07-09
**Author:** Enterprise Architect (simulation-driven — Simulation 004 GAP-018, GAP-019)
**Constitutional Basis:** C-038 (pro-rata billing — LAW); C-043 (financial authority ceiling); AD-014 (pro-rata billing precision)

---

## Context

WAOOAW serves India SME customers. All payments are in Indian Rupees. The platform requires:
1. Recurring subscription billing (monthly, per-bundle pricing)
2. Pro-rata billing on pause/resume (C-038)
3. GST-compliant invoicing (India GST Act, 18% on software services, SAC 9984)
4. Payment failure handling (grace period, skill suspension)
5. Refund processing (trial cancellations, dispute resolution)

Razorpay is chosen as the payment processor because: India-native, supports recurring subscriptions (Razorpay Subscriptions API), supports UPI + cards + net banking (India payment landscape), GST invoicing support, and is well-supported by the India developer community.

---

## Decision

### 1. Subscription Model

WAOOAW uses **Razorpay Subscriptions API** (not one-time payments) for all recurring billing.

- One Razorpay subscription per WAOOAW Employment Contract
- Plan is tied to the active bundle/tier within each agent type
- Bundle/tier upgrades: update the Razorpay subscription plan (prorated for remaining days)

**Complete Pricing Table (all agents, v0.25.0):**

| Agent | Tier | Customer pays | Base | GST 18% | Razorpay Plan ID |
|---|---|---|---|---|---|
| Digital Marketing | Curtain Raiser | ₹1,499/month | ₹1,271 | ₹228 | `plan_dma_curtain_raiser` |
| Digital Marketing | Growth Engine | ₹2,499/month | ₹2,118 | ₹381 | `plan_dma_growth_engine` |
| Digital Marketing | Maturity Phase | ₹3,999/month | ₹3,389 | ₹610 | `plan_dma_maturity_phase` |
| Trading | F&O Professional | ₹1,999/month | ₹1,694 | ₹305 | `plan_trading_fo_only` |
| Trading | F&O + Crypto Professional | ₹2,499/month | ₹2,119 | ₹380 | `plan_trading_fo_crypto` |
| Agricultural Advisor | Agricultural Advisor | ₹200/month | ₹169 | ₹30 | `plan_agricultural_advisor` |

All amounts in INR. GST SAC code: 9984 (Online Information and Database Access Services).

---

### 1b. Multi-Agent Consolidated Billing

When a customer hires multiple agents simultaneously (e.g., DMA + Trading), WAOOAW supports two billing preferences configurable per customer organisation:

**SEPARATE** — one Razorpay subscription per employment contract; one GST invoice per agent per month. Customer receives separate payment confirmations and invoices per agent. Customer can pause each agent independently without affecting others.

**COMBINED** (default for customers with 2+ active agents) — each agent still has its own independent Razorpay subscription (for clean per-agent pause/resume). WAOOAW generates ONE consolidated GST invoice monthly that itemises all active agents. Customer sees one total bill with line items per agent.

**Example consolidated invoice (DMA Growth Engine + Trading F&O Only):**
```
WAOOAW Platform Services
Invoice: WAOOAW/2026-27/000042
─────────────────────────────────────────────────────
Service                          Base      GST    Total
─────────────────────────────────────────────────────
Digital Marketing Professional
  Growth Engine Bundle           ₹2,118   ₹381   ₹2,499
Trading Professional
  F&O Professional               ₹1,694   ₹305   ₹1,999
─────────────────────────────────────────────────────
Subtotal                         ₹3,812   ₹686   ₹4,498
─────────────────────────────────────────────────────
```

**Billing preference change:** Customer can switch between SEPARATE and COMBINED via `/api/v1/billing/preference`. Effective from next billing period.

**Pro-rata with multiple agents:** Each agent's pause/resume creates its own billing event in `subscription_billing_events`. The consolidated invoice sums the pro-rata amounts at the end of the billing period. If Agent A was paused for 10 days, its invoice line item reflects the pro-rata charge; Agent B (not paused) shows the full monthly charge.

### 2. razorpay-mcp (port 8131)

A dedicated MCP server (sidecar) wrapping the Razorpay API. Business Platform does NOT call Razorpay directly — it calls razorpay-mcp.

**Tools:**

#### subscription.create
```
POST /call/subscription.create
Request:  {
  contract_id: string (UUID),
  plan_id: string,              -- Razorpay plan ID for the selected bundle
  customer_email: string,
  customer_phone: string,       -- +91XXXXXXXXXX format
  customer_name: string,
  total_count: integer | null,  -- null = indefinite subscription
  notes: { contract_id: string, organisation_id: string }
}
Response: {
  razorpay_subscription_id: string,
  payment_link: string,         -- hosted payment page URL sent to customer
  short_url: string             -- shortened URL for WhatsApp delivery
}
```

#### subscription.pause
```
POST /call/subscription.pause
Request:  { razorpay_subscription_id: string, pause_at: "now" | "cycle_end" }
Response: { paused: boolean, billing_stops_at: string }
```

#### subscription.resume
```
POST /call/subscription.resume
Request:  { razorpay_subscription_id: string }
Response: { resumed: boolean, next_billing_at: string }
```

#### subscription.cancel
```
POST /call/subscription.cancel
Request:  { razorpay_subscription_id: string, cancel_at: "now" | "cycle_end" }
Response: { cancelled: boolean }
```

#### invoice.get_gst
```
POST /call/invoice.get_gst
Request:  { razorpay_payment_id: string }
Response: {
  invoice_number: string,       -- WAOOAW/2026-27/XXXXX format
  gstin_waooaw: string,         -- WAOOAW's GSTIN
  hsn_sac_code: "9984",
  base_amount_inr: integer,     -- in paise
  cgst_amount_inr: integer,     -- 9% in paise
  sgst_amount_inr: integer,     -- 9% in paise (or IGST if inter-state)
  total_amount_inr: integer,
  customer_gstin: string | null,-- if customer provided GSTIN at registration
  pdf_url: string               -- signed URL to GST invoice PDF
}
```

### 3. Webhook Receiver

`POST /api/v1/payments/webhooks/razorpay`

Razorpay sends webhook events to this endpoint. Signature verification is mandatory:

```python
# In Business Platform webhook handler:
import hmac, hashlib

def verify_razorpay_webhook(payload_bytes: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Events handled:**

| Event | Action |
|---|---|
| `subscription.charged` | Record billing event; update `subscription_billing_events`; generate GST invoice |
| `subscription.halted` | Suspend Employment Contract (payment failure); notify customer |
| `subscription.cancelled` | Terminate Employment Contract; record `EMPLOYMENT_TERMINATED` in CE |
| `payment.failed` | Start grace period (3 days); notify customer; if not resolved → suspend skills |
| `payment.captured` | On first payment: activate Employment Contract; `EMPLOYMENT_ACTIVATED` in CE |

### 4. Pro-Rata Billing (C-038, AD-014)

Razorpay Subscriptions API does not natively support per-minute pro-rata billing. WAOOAW implements this in the Subscription Manager (Business Platform):

```
At billing period close:
  charge_period_days = COUNT of days where employment_state = ACTIVE in this period
  billing_days_in_period = calendar days in billing period
  pro_rata_factor = charge_period_days / billing_days_in_period
  billable_amount = bundle_base_price_inr * pro_rata_factor

  If charge_period_days < billing_days_in_period:
    → Create Razorpay credit note for the suspended days
    → Adjust next invoice accordingly
```

### 5. GST Compliance

WAOOAW is registered under GST (GSTIN mandatory before first payment). Every invoice must include:
- WAOOAW's GSTIN
- SAC code 9984 (Online Information and Database Access Services)
- HSN/SAC breakdown
- CGST + SGST (9% + 9% for same-state customers) or IGST (18% for inter-state)
- Customer GSTIN (if provided) — enables B2B GST input credit claim

Invoice numbering: sequential, financial-year-prefixed: `WAOOAW/2026-27/000001`

---

## Rejected Alternatives

**A — Stripe:** Not India-native. Poor UPI support. Higher fees for India transactions. No built-in GST invoicing.

**B — Manual billing:** Not scalable. C-038 pro-rata calculation requires automation.

**C — Razorpay Payment Links (not Subscriptions):** One-time payments only. Cannot support recurring billing model.

---

## Consequences

- New container: `razorpay-mcp` (port 8131) — add to docker-compose and containers.md
- New environment variables: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
- New BP endpoints: `/api/v1/payments/subscriptions`, `/api/v1/payments/webhooks/razorpay` (already added in OpenAPI v0.18.0)
- New SQL tables needed: `payment_transactions` (Razorpay payment record), `gst_invoices` (GST invoice record)
- Registration form: add optional `customer_gstin` field (for B2B customers claiming input credit)
- `organisations` table: add `gstin` nullable column

---

## Amendment 1 — GOAL-004 Billing Engine Extensions (2026-07-30)

**Author:** Enterprise Architect (INST-004)
**Constitutional Basis:** C-088 (Agent Billing Profile), C-089 (Minimum Margin Floor),
C-090 (Grandfather Pricing), C-091 (Thread Catalog Sovereignty)
**Amends:** Sections 1, 2, and Consequences above

### Amendment 1.1 — Universal Prepaid Enforcement

The original ADR scoped prepaid enforcement to ad spend wallets only (ADR-026). This amendment
extends the prepaid gate to ALL constrained resource threads, consistent with C-090 Grandfather
Pricing and the GOAL-004 prepaid insurance principle.

**Thread bucket types (added to wallet model):**

| Bucket Type | Thread | Unit | Refilled By |
|---|---|---|---|
| `llm_local` | LOCAL tier LLM | Classification calls | Period renewal (unlimited — zero cost) |
| `llm_mid` | MID_TIER LLM | Calls (counted at dispatch) | Period renewal; top-up |
| `llm_frontier` | FRONTIER LLM | Calls (counted at dispatch) | Period renewal; top-up |
| `video_clips` | Video generation (Kling, HeyGen, Runway) | Clips | Period renewal; top-up |
| `whatsapp_windows` | WhatsApp conversation windows | 24hr windows | Period renewal; top-up |
| `image_gen` | Image generation | Images | Period renewal; top-up |
| `ad_spend` | Ad spend (existing — ADR-026) | INR paise | Customer top-up; no auto-refill |

**Prepaid gate rule (extended):** Before any WAOOAW service dispatches a thread call, WBE
is queried for available bucket balance. Zero balance → call rejected → graceful degradation
path invoked (ZERO_COST template or honest C-049 disclosure). The gate applies to every
thread type without exception.

**Trial mode:** In Demo/Trial mode, all thread calls route to zero-cost substitutes. No
bucket deduction occurs. The Agent Billing Profile (C-088) defines the zero-cost substitutes
per thread per agent. WBE enforces trial/live mode separation.

### Amendment 1.2 — Single Onboarding Payment

The original ADR created separate Razorpay subscription activation and ad wallet funding
flows. This creates friction at trial-to-paid conversion (two separate payment events).

**New onboarding payment pattern:**

```
Customer says "hire me" → WBE generates Razorpay Order (one-time, covers):
  1. First month subscription amount (pre-paid)
  2. Initial wallet seed amount (configurable per bundle — default ₹2,000 for DMA)
  → Single Razorpay Order ID

Customer taps UPI → Single payment confirmation from Razorpay

razorpay-mcp receives payment.captured webhook:
  Step 1: Activate Razorpay subscription (links to the Order)
  Step 2: Seed wallet buckets (all non-ad-spend buckets via WBE)
  Step 3: Seed ad_spend wallet (if agent requires ad spend)
  Step 4: Flip customer mode: TRIAL → LIVE (at payment_intent CONFIRMED,
           not subscription object creation — eliminates the race condition in S-09)
  Step 5: Notify agent: customer is now LIVE

Target latency: ≤ 90 seconds from UPI tap to agent first LIVE response.
```

**Important:** The mode flip (Step 4) happens at payment.captured event, before subscription
object creation completes. This is intentional: eliminates the 4-second race condition where
a customer message arrives between payment and activation.

### Amendment 1.3 — Progressive Renewal Failure Policy

When a Razorpay subscription renewal payment fails, the platform applies a timed policy:

```
Day 0 (1st failure):
  → WhatsApp: "Payment failed. Update your payment method. Agent continues fully."
  → Agent: full capability maintained

Day 3 (2nd retry failure):
  → WhatsApp: "Second attempt failed. Agent continues for 4 more days. Update now."
  → Agent: full capability; no NEW campaigns launched (ad_spend gate tightened)
  → New campaigns require manual approval until payment resolved

Day 7 (3rd retry failure):
  → SAGA initiated: pause all active Meta/Google campaigns (Step 1 — must succeed)
  → If campaign pause saga succeeds: freeze LLM buckets to ZERO_COST path only
  → WhatsApp: "Account in recovery mode. One tap to restore."
  → Agent discloses limited mode per C-049: "I'm in recovery mode — billing needs attention."

Day 14 (no resolution):
  → Full suspension: employment_contracts.status = SUSPENDED
  → C-038 pro-rata credit calculated for unused subscription days
  → Evidence preserved per C-007 (append-only, not deleted)
  → Data retained 90 days per data protection policy
```

**Campaign pause saga (Day 7):** The campaign pause is a Temporal workflow saga. If Meta/Google
API pause fails after 3 retries, the billing state change is rolled back (subscription not
suspended). The failure is escalated to Platform Operations agent for manual resolution.
Billing cannot advance to suspension state while provider campaigns are unconfirmed-paused.

### Amendment 1.4 — Grandfather Pricing Enforcement (C-090)

Each employment contract row records the price at which it was sold:
- `employment_contracts.agreed_monthly_price_paise` — locked at contract formation
- `employment_contracts.price_change_notice_sent_at` — populated when 30-day notice issued
- `employment_contracts.price_change_effective_date` — must be ≥ notice_sent_at + 30 days
- Razorpay subscription plan update (to new pricing tier plan) is only applied AFTER
  `price_change_effective_date` is reached AND customer acknowledgment is recorded

WBE enforces: Razorpay plan update API call is blocked until both conditions are met.
Any attempt to update the subscription plan before acknowledgment is a C-090 violation
and triggers an automatic compliance alert to the Constitutional Audit Ledger.

## Amendment 2 — Lower-Environment Bypass + Environment-Variable Configuration (2026-08-07)

**Authority:** Founder Decision FA-029 (2026-08-07 — Yogesh Khandge)
**Sprint:** WC-042 = WBE-S7 (Single Onboarding Payment + Renewal Saga)
**Constitutional Basis:** ADR-014 (secret management), C-059 (implementation traceability)

### Amendment 2.1 — All Razorpay Configuration via Environment Variables

No Razorpay plan IDs, API keys, or webhook secrets are hardcoded in source code (ADR-014).
All credentials and plan references are injected via environment variables at deploy time:

| Environment Variable | Description |
|---|---|
| `RAZORPAY_KEY_ID` | Razorpay API key (test key for demo/UAT, live key for production) |
| `RAZORPAY_KEY_SECRET` | Razorpay API secret (never logged — ADR-014) |
| `RAZORPAY_WEBHOOK_SECRET` | HMAC-SHA256 webhook signature verification secret |
| `RAZORPAY_PLAN_ID_STARTER` | Razorpay plan ID for Starter bundle tier |
| `RAZORPAY_PLAN_ID_RUNNER` | Razorpay plan ID for Runner bundle tier |
| `RAZORPAY_PLAN_ID_WINNER` | Razorpay plan ID for Winner bundle tier |
| `WAOOAW_ENVIRONMENT` | Deployment environment: `demo` \| `uat` \| `production` |

Production Razorpay plan IDs are NOT yet created. They will be injected at go-live time.
Until then, lower environments use test keys from the Razorpay Test Mode dashboard.

### Amendment 2.2 — Lower-Environment Payment Bypass (Demo / UAT)

For demo and UAT environments, real payment processing is not required. Two reserved coupon
codes bypass the live Razorpay API entirely:

| Coupon Code | Environment | Discount | Behaviour |
|---|---|---|---|
| `DEMOWAOOAW` | demo | 100% | Returns `bypass-{customer_id}` stub order, `amount_paise=0`, no Razorpay API call |
| `UATWAOOAW` | uat | 100% | Same — bypasses Razorpay, activates wallet seeding directly |

The bypass is implemented in `OnboardingService.create_onboarding_order()`. The
`WebhookHandler.handle_payment_captured()` skips HMAC signature verification when
`is_bypass=True`. Both coupons are seeded in `business.coupon_codes` via migration
`infrastructure/postgres/init/18-wbe-s7-payment.sql`.

**Production guard:** `is_bypass` can only be `True` when the order was created with a bypass
coupon. The frontend sends `is_bypass` in the payment-capture body. Production deployments
must never issue bypass-coupon codes; the coupon seed migration is gated by `WAOOAW_ENVIRONMENT`.
