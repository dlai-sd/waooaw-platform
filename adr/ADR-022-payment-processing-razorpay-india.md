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
- Plan is tied to the active Phase Bundle (Curtain Raiser / Growth Engine / Maturity Phase)
- Bundle upgrades: update the Razorpay subscription plan (prorated for remaining days in billing cycle)

**Pricing structure (stored in `professional_templates`):**

| Bundle | Base price (excl. GST) | GST (18%) | Customer pays |
|---|---|---|---|
| Curtain Raiser | ₹1,271 | ₹229 | ₹1,499/month |
| Growth Engine | ₹2,118 | ₹381 | ₹2,499/month |
| Maturity Phase | ₹3,389 | ₹610 | ₹3,999/month |

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
