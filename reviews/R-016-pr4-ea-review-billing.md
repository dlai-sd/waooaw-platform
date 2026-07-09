# R-016 — Enterprise Architect Review: PR #4 — Billing (Agricultural + Trading + Multi-Agent)

**Review ID:** R-016
**Reviewer Office:** Enterprise Architect
**PR:** #4 — `agent/update/billing-agricultural-trading`
**Subject:** Agricultural billing ₹200/month, Trading billing ₹1,999/₹2,499/month, multi-agent consolidated billing (ADR-022 extension)
**Date:** 2026-07-09

---

## Overall Verdict: APPROVED WITH P1 FIX REQUIRED

The billing specs for Trading and multi-agent consolidated billing are architecturally correct. The Agricultural billing model is well-reasoned (₹200/month with WhatsApp UPI payment). However, a critical gap exists at the intersection of WhatsApp identity (PR #2) and billing (PR #4): the subscription payment mechanism for farmers. **This P1 must be fixed before PR #4 can be merged.**

---

## P1 Finding — R016-01: UPI AutoPay Gap (must fix before merge)

**Finding:** PR #4 introduces a `POST /api/v1/billing/whatsapp-upi-link` endpoint that generates a Razorpay UPI **one-time payment link**. For a subscription billing model (₹200/month), a one-time link is insufficient — it requires WAOOAW to send a new payment link to the farmer every month. This produces:
1. Monthly friction: farmer must manually tap and pay every month (kills retention)
2. HSM template complexity: billing notification requires a pre-approved Meta template every cycle
3. No auto-collection: if farmer doesn't act on the link, subscription lapses

**The correct mechanism for agricultural subscription billing is UPI AutoPay (UPI Standing Instruction):**
- Razorpay Recurring Payments API generates a UPI mandate link
- Farmer taps ONCE → approves ₹200/month in their UPI app → standing instruction created
- Razorpay auto-collects on the 1st of each month
- One-time setup, zero monthly friction for the farmer

**Fix required:**
1. Add to `razorpay-mcp` tool catalogue: `mandate.create_upi_autopay` and `mandate.get_status`
2. Replace `billing/whatsapp-upi-link` endpoint description from "one-time" to "UPI AutoPay mandate setup link"
3. Add billing HSM template specification: `"Your ₹200 farming advisor subscription — approve once: [link]"`

---

## WhatsApp ↔ Razorpay Integration Review (Founder Question)

The Founder asked whether WhatsApp and Razorpay integration was fully considered for the Agricultural Advisor. Assessment:

**What was done correctly:**
- WhatsApp UPI link concept is right for the India market
- ₹200/month is affordable; UPI is ubiquitous in rural India
- `POST /api/v1/billing/whatsapp-upi-link` is the right API shape
- FPO bulk pricing model addresses the non-direct-pay segments

**What was missed (the intersection gap):**

The full flow for a new farmer's billing journey was not specified end-to-end:

```
Step 1: Farmer sends first WhatsApp message → auto-registered (PR #2 ✓)
Step 2: Profiling completes → profile MINIMUM_VIABLE
Step 3: Agent sends: "शेती सल्ला ₹200/महिना. एकदा pay करायचे म्हणजे दर महिना
         आपोआप होईल. या link ला tap करा:" [UPI AutoPay mandate link]
Step 4: Farmer taps → UPI app opens → approves ₹200/month mandate ← THIS STEP
         is not fully specified (needs UPI AutoPay, not one-time link)
Step 5: Razorpay confirms mandate → SUBSCRIPTION_ACTIVATED → CE evidence record
Step 6: Each month: Razorpay auto-debits → payment.captured webhook → WAOOAW
         acknowledges → agent continues running
Step 7: Payment fails: Razorpay sends failure webhook → WAOOAW sends WhatsApp:
         "Payment failed. Please retry: [retry link]"
```

Steps 3-5 and 7 are the gaps that need specification in ADR-022 and razorpay-mcp.

---

## Multi-Agent Consolidated Billing Assessment: SOUND

The COMBINED billing architecture (separate Razorpay subscriptions per agent + consolidated GST invoice) is the correct approach. It correctly separates:
- Payment collection (per-agent Razorpay subscription — independent pause/resume)
- Invoice presentation (combined GST invoice for customer simplicity)

The `consolidation_group_id` on `gst_invoices` is the right SQL pattern. The `is_consolidated_parent` flag correctly identifies the summary invoice.

**One architectural note (non-blocking):** The `combined_billing_anchor_day` on `organisations` is good. But if Agent A was activated on the 15th and Agent B on the 1st, their billing cycles don't align for the first combined invoice. ADR-022 should specify: on first activation of COMBINED billing (when 2nd agent is hired), WAOOAW prorates the second agent's first billing to align to the anchor day.

---

## Trading Billing Assessment: SOUND

- Flat monthly ₹1,999/₹2,499 is correct
- No performance fee — constitutional rationale (C-043 daily loss limit tension) is correctly identified and specified
- Session-based (not per-trade) billing prevents incentivising excessive trading

---

## P1 Fix — Required Before Merge

**Files to update:**

1. **ADR-022** — Add Section on UPI AutoPay for agricultural billing + billing conversation flow specification (Steps 3-7 above)

2. **razorpay-mcp tool catalogue** — Add:
   - `mandate.create_upi_autopay` — generates UPI AutoPay mandate link
   - `mandate.get_status` — checks mandate activation status

3. **OpenAPI `billing/whatsapp-upi-link`** — Change description from "one-time payment" to "UPI AutoPay mandate setup (recurring)" and update response schema to include `mandate_id`

4. **HSM template specification** — Add billing notification HSM templates to agricultural-advisor-agent.md or ADR-022 (one for mandate setup, one for payment failure retry)

---

## Section 14 Gate (affected sections only)

| Section | Status | Notes |
|---|---|---|
| 1 — Spec Completeness | ✅ PASS | Billing sections complete |
| 3 — MCP Gate | ⚠ P1 | razorpay-mcp missing UPI AutoPay mandate tools |
| 6 — Data Gate | ✅ PASS | subscription_tiers + billing_preference + consolidation columns |
| 7 — Constitutional Gate | ✅ PASS | C-038 pro-rata; C-043 no-performance-fee |
| 8 — Architecture Chain | ⚠ P1 | Pending razorpay-mcp mandate tools |

**Overall: CHANGE REQUESTED — P1 fix required, then APPROVED**
