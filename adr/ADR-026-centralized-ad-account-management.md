# ADR-026 — Centralized Ad Account Management (WAOOAW MBM + Google MCC)

**Status:** Accepted
**Date:** 2026-07-12
**Author:** Enterprise Architect (Founder decision — centralized agency model for Skill 11 Paid Advertising)
**Constitutional Basis:** C-056 (Ad Spend Transparency Obligation — LAW); C-043 (Financial Spend Ceiling — LAW); C-034 (Data Isolation); C-038 (Billing Transparency); C-048 (Non-Exploitation)

---

## Context

The DMA agent's Skill 11 (Paid Advertising) initially assumed per-customer OAuth — each customer connects their own Meta Ads and Google Ads accounts to WAOOAW via ADR-021's OAuth vault. This model creates significant onboarding friction:

1. Customers must have an existing Meta Business Manager account (many SMBs don't)
2. Customers must have an existing Google Ads account (most local clinics don't)
3. Each customer must go through Meta Business Verification (2–4 weeks)
4. WAOOAW has no control over ad account structure, billing thresholds, or account health

A professional advertising agency does not ask each client to set up their own ad accounts. The agency holds a master account (Meta Business Manager, Google Ads MCC) and creates sub-accounts for each client. The agency manages the ads; the clients see their brand in the results.

Founder decision (2026-07-12): WAOOAW adopts the agency model as default. Management fee: 10% of gross ad spend, disclosed at contract formation.

---

## Decision

### 1. Account Structure

**Meta (Facebook/Instagram Ads):**
```
WAOOAW Meta Business Manager (ONE account, registered as Meta Business Partner)
  ├── Sub Ad Account: Dr. Mehta Dental Clinic (customer A)
  │   ├── Pixel: dr-mehta-pixel (customer A's pixel)
  │   ├── Audiences: Dr. Mehta's custom audiences (customer A only)
  │   └── Campaigns: October Dental Awareness (customer A's campaigns)
  ├── Sub Ad Account: Sana Beauty (customer B)
  │   └── ... (isolated from customer A — C-056 segregation)
  └── Payment Method: WAOOAW's company card (all customers' spend)
  
Page Access Model:
  Customer grants their Facebook Page to WAOOAW's MBM (Partner access, not ownership)
  "Advertise on behalf of [Customer Page]" permission
  Ads appear as: "Sponsored · Dr. Mehta's Dental Clinic" — customer's brand, not WAOOAW
```

**Google Ads:**
```
WAOOAW Google Ads Manager Account (MCC — My Client Center)
  ├── Client Account: Dr. Mehta Dental Clinic (customer A)
  │   ├── Campaigns: Local search + Performance Max
  │   └── Linked: Customer's Google Analytics + Search Console
  ├── Client Account: Sana Beauty (customer B)
  │   └── ... (isolated from customer A)
  └── Billing: WAOOAW's consolidated billing profile

Customer access: Read-only viewer access to their own client account (C-056 obligation)
```

### 2. Ad Spend Wallet (per customer)

The Ad Spend Wallet is the financial instrument that segregates each customer's ad budget:

```
Ad Spend Wallet lifecycle:
  CREATION: When customer enables Skill 11 (Paid Advertising)
    → wallet created with balance = 0
    → customer prompted to fund via Razorpay

  FUNDING: Customer tops up via Razorpay (one-time or recurring)
    → payment type: AD_SPEND_TOPUP
    → GST: 18% on total amount (SAC 998361 — Online advertising services)
    → wallet credited: full topup amount (after GST split)

  SPEND: When a campaign is live, Meta/Google charges WAOOAW's master payment method
    → WAOOAW debits the customer's wallet daily/weekly from actual Meta/Google charges
    → Management fee deducted: 10% of gross spend
    → ad_spend_ledger records: CHARGE (gross spend) + MANAGEMENT_FEE (10%)

  CREDIT PASS-THROUGH: When Meta/Google issues a credit or promotional credit
    → Full credit amount → wallet credited (REFUND / CREDIT record)
    → WAOOAW retains 0 of platform credits (C-056 obligation)

  LOW BALANCE ALERT: When available_balance < 3 days of current burn rate
    → C-053-style proactive alert: "Your ad budget is running low. Top up to keep campaigns live."
    → URGENCY_CLASS: HIGH (budget depletion halts campaigns — significant KPI impact)

  ZERO BALANCE: Campaigns automatically PAUSED (not cancelled)
    → CE.RecordEvidence(AD_SPEND_WALLET_EXHAUSTED)
    → Customer notified: "Campaigns paused — ad budget at zero. Top up to resume."
    → Note: pausing is immediate; campaigns do NOT accrue spend beyond wallet balance
```

### 3. Billing: Two-Part Invoice

Every billing period, customers with Skill 11 active receive TWO separate Razorpay invoices:

**Invoice 1: Platform Subscription (unchanged)**
- Line item: WAOOAW Digital Marketing Professional — [tier]
- Amount: ₹1,499 / ₹2,499 / ₹3,999 (tier-dependent)
- GST: 18% (SAC 9984 — Information Technology Services)

**Invoice 2: Advertising Services**
- Line item 1: Ad Spend — Meta Advertising — [Campaign names]  ₹X
- Line item 2: Management Fee (10% of ad spend)                ₹X × 0.10
- Line item 3: Ad Spend — Google Advertising — [Campaign names] ₹Y
- Line item 4: Management Fee (10% of ad spend)                ₹Y × 0.10
- **Sub-total**: ₹(X + Y) × 1.10
- **GST (18%)**: SAC 998361 — Online Advertising and Marketing Services
- **Total**: ₹(X + Y) × 1.10 × 1.18

The management fee rate (10%) is disclosed:
- At contract formation (during onboarding conversation)
- On every Invoice 2 as an explicit line item
- In the customer's portal under "Ad Management Settings"

### 4. Management Fee — Rationale and Positioning

The 10% management fee on gross ad spend is the industry-standard advertising agency commission in India. It is constitutionally sound and commercially standard:

- **Transparency**: Disclosed at onboarding and itemized on every invoice (C-056 + C-038)
- **Value justification**: The fee covers: campaign strategy (Skill 11), creative management (Skill 4/5), performance optimization (Skill 9), audience research (Skill 1), brand safety (SCR Check 3)
- **No double-charging**: The subscription fee (₹2,499/month) covers the agent's management capability. The 10% fee is specifically for ad spend management. These are distinct services.
- **Market rate**: Digital marketing agencies typically charge 10–20% of ad spend. WAOOAW at 10% is at the low end — justified by platform-driven efficiency.

**Example: Dr. Mehta at Growth Engine tier**
```
Monthly subscription:    ₹2,499 + 18% GST = ₹2,949  (SAC 9984)
Ad spend:                ₹5,000 to Meta + Google
Management fee (10%):    ₹500
GST on advertising:      (₹5,000 + ₹500) × 18% = ₹990
Ad spend invoice total:  ₹5,000 + ₹500 + ₹990 = ₹6,490  (SAC 998361)

Total monthly WAOOAW:    ₹2,949 + ₹6,490 = ₹9,439
Of which WAOOAW revenue: ₹2,499 (subscription) + ₹500 (ad mgmt fee) = ₹2,999/month
Ad spend at Meta/Google: ₹5,000 (pass-through)
```

### 5. Connection Model: WAOOAW_MANAGED vs CUSTOMER_OWNED

Two connection models are architecturally declared. Only WAOOAW_MANAGED is implemented at MVI.

```yaml
ads_connection_model:
  WAOOAW_MANAGED:  # Default — implemented at MVI
    description: "WAOOAW manages ads through its Meta Business Manager and Google MCC.
                  Customer grants page access to WAOOAW's MBM. No per-customer Meta/Google account needed."
    management_fee_pct: 10
    ad_spend_billing: "SEPARATE_INVOICE — Ad Spend Wallet, real-time tracking"
    customer_account_needed: false
    implementation_status: "ACTIVE"

  CUSTOMER_OWNED:  # Alternative — NOT implemented at MVI
    description: "Customer connects their own Meta Business Manager and Google Ads account
                  via OAuth (ADR-021 model). WAOOAW gets agency access. Customer pays Meta/Google directly."
    management_fee_pct: 0  # No ad spend management fee (customer manages their own billing)
    ad_spend_billing: "CUSTOMER_DIRECT — Customer pays Meta/Google; WAOOAW has no intermediary role"
    customer_account_needed: true
    implementation_status: "PENDING_FOUNDER_AUTHORIZATION"
    dependency: "Requires per-customer Meta Business Manager + Google Ads account setup"
    note: "C-056 obligations do not apply (WAOOAW is not a financial intermediary).
           C-043 (budget ceiling) still applies — agent cannot exceed customer-approved spend."
```

### 6. Page Access Model (Meta)

Under WAOOAW_MANAGED, customers do NOT need their own Meta Business Manager. But they DO need:
1. A Facebook Page for their business (free to create; most businesses have one)
2. An Instagram Professional Account connected to that Facebook Page (free to convert; most businesses have one)

Customer grants WAOOAW's MBM **Partner Access** to their Facebook Page. This is:
- A non-ownership access (customer retains full ownership of their Page)
- Reversible at any time (customer can remove WAOOAW from their Page at any time)
- Scoped to advertising only: "Advertise as [Page Name]" permission
- NOT the same as giving WAOOAW ownership of the Page

WAOOAW's MBM then creates a sub-ad-account that runs ads "on behalf of" the customer's Page. The ads display as "Sponsored · [Customer's Page Name]" in patient/client feeds.

### 7. Data Sovereignty at Termination (C-056 Obligation)

When employment contract terminates:

```
STEP 1: Campaign pause (immediate)
  → All live campaigns paused within 1 hour of termination
  → CE.RecordEvidence(AD_ACCOUNT_TERMINATION_INITIATED)

STEP 2: Customer choice (always-ask — 30 days to decide)
  Option A: TRANSFER
    → WAOOAW initiates Meta sub-account transfer to customer's own Business Manager
    → Customer must create/have their own Meta BM to receive the transfer
    → Transfer timeline: 24-72 hours (Meta process)
    → All campaign history, audiences, pixels, creative assets transferred
    
  Option B: EXPORT_AND_DELETE
    → WAOOAW exports all campaign data (JSON + CSV) and provides download link
    → Customer downloads within 30 days
    → After 30 days: sub-account deleted
    → Customer's Page Access revoked from WAOOAW's MBM
    
  Option C: HOLD (if customer cannot decide within 30 days)
    → Sub-account frozen (no spend, no campaigns) for up to 90 days
    → After 90 days: auto-converted to EXPORT_AND_DELETE
    → CE.RecordEvidence(AD_ACCOUNT_AUTO_DELETED)

STEP 3: Financial reconciliation
  → Any remaining Ad Spend Wallet balance refunded via Razorpay within 7 days
  → Final Invoice 2 generated for any spend in the termination month
  → CE.RecordEvidence(AD_SPEND_WALLET_REFUNDED)
```

### 8. New Service: waooaw-ads-manager

A new internal service responsible for master account operations:

```
Port: 8143 (internal only — never externally exposed)
Responsibilities:
  - Sub-account CRUD under WAOOAW's Meta MBM (create, modify, archive)
  - Client account CRUD under WAOOAW's Google MCC
  - Page Access request management (generate Meta Business Request links)
  - Account transfer initiation at termination
  - Daily billing reconciliation (match WAOOAW's Meta/Google statements to ad_spend_ledger)

This service is NOT an MCP server — it is a WAOOAW internal service.
meta-ads-mcp and google-ads-mcp call this service to get the correct sub-account context.

Credentials held:
  - WAOOAW_META_SYSTEM_USER_ACCESS_TOKEN (Meta Business Manager system user token — never expires)
  - WAOOAW_GOOGLE_ADS_MCC_DEVELOPER_TOKEN
  - Stored in Azure Key Vault per ADR-014 (NOT in oauth-vault — these are WAOOAW's own credentials, not customer-delegated)
```

---

## Rejected Alternatives

**A — Per-customer OAuth for ads (ADR-021 model):** Customer must create their own Meta Business Manager and Google Ads accounts. Significant onboarding friction for SMBs. Each customer requires Meta Business Verification (2-4 weeks). WAOOAW has no control over account health. Rejected as default; retained as CUSTOMER_OWNED alternative.

**B — Pure pass-through (no management fee):** Ad spend is exactly passed to Meta/Google with no markup. This makes the agency model financially non-viable — WAOOAW would incur operational overhead (billing reconciliation, account management, campaign optimization) with no revenue from the advertising vertical. Rejected.

**C — Percentage above 10%:** Industry standard; 10% is at the lower end of the 10-20% range. Higher percentages increase customer value proposition friction. 10% is the right rate for a platform-driven service at MVI.

---

## Consequences

**New ADR references this decision:**
- ADR-021: CUSTOMER_OWNED model (existing) — this ADR supersedes ADR-021's applicability to paid advertising at MVI
- ADR-022: Razorpay — Invoice 2 (advertising services) is a new invoice type; SAC 998361 code added

**New constitutional claim:** C-056 (Ad Spend Transparency Obligation)

**New files/tables:**
- `business.customer_ad_accounts` — per-customer sub-account IDs under WAOOAW MBM/MCC
- `business.ad_spend_wallets` — per-customer balance tracking
- `business.ad_spend_ledger` — per-charge audit trail (C-056 evidentiary record)
- `architecture/reference/containers.md` — waooaw-ads-manager service (port 8143)

**Updated files:**
- DMA agent spec: Skill 11 (Paid Advertising) — connection model, ad spend wallet, management fee disclosure
- DMA subscription tiers: new Razorpay plan types for AD_SPEND_TOPUP
- Skill Dependency Register: new Founder actions (WAOOAW Meta Business Partner status, Google MCC)

**Founder actions (P0 before any live advertising):**
1. Register WAOOAW as Meta Business Partner (beyond standard Business Manager — required for multi-client ad management). Lead time: 1-3 weeks after Meta Business Manager verification.
2. Create WAOOAW Google Ads Manager (MCC) account. Free; requires Google billing profile.
3. Set WAOOAW_META_SYSTEM_USER_ACCESS_TOKEN and WAOOAW_GOOGLE_ADS_MCC_DEVELOPER_TOKEN in Azure Key Vault (production) and .env (dev).

**Minimum Ad Spend:** ₹2,000/month. Below this, Meta's learning algorithm cannot optimize effectively. Skill 11 activation requires customer to fund Ad Spend Wallet to at least ₹2,000.

---

## Amendment — C-075 Reseller Model (2026-07-19)

C-075 (White-Label Reseller) introduces a new ad account management path: **Reseller-Owned MBM/MCC**. This coexists with the original WAOOAW-Owned model.

### Two Ad Account Models

| Model | Who uses it | Meta account | Google account | Billing |
|---|---|---|---|---|
| **WAOOAW-Owned** (original) | Direct customers | WAOOAW MBM sub-account | WAOOAW MCC client account | Customer → Ad Spend Wallet → WAOOAW → Meta/Google |
| **Reseller-Owned** (new) | Agency resellers (C-075) | Reseller's own MBM sub-account | Reseller's own MCC client account | Reseller → Meta/Google directly; WAOOAW → Reseller (wholesale seat fee only) |

### Reseller-Owned: How It Works

```
Reseller (Yashus) connects their Meta BM and Google MCC to WAOOAW via oauth-vault:
  meta_bm_access_token: stored as "META_BM_TOKEN_{reseller_id}"
  google_mcc_developer_token: stored as "GOOGLE_MCC_TOKEN_{reseller_id}"

For each end-customer (Yashus's client):
  meta-ads-mcp creates a sub-ad-account under YASHUS's MBM (not WAOOAW's)
  google-ads-mcp creates a client account under YASHUS's MCC (not WAOOAW's)
  
Billing flows:
  Meta/Google → bills Yashus directly (Yashus's payment method)
  Yashus → bills their clients (Yashus's pricing + Yashus's management fee %)
  WAOOAW → bills Yashus only: active_seats × wholesale_price_per_seat/month
  WAOOAW does NOT invoice Yashus's clients for ad spend (C-075 — Yashus is the billing entity)
```

### Ad Account Health Monitoring (both models)

Platform Operations agent now monitors ad account health as part of its L1 5-minute health probe.

**Monitored signals:**
```
meta-ads-mcp.account.get_status(sub_account_id)
  → account_standing: ACTIVE | RESTRICTED | DISABLED | UNDER_REVIEW
  → payment_method_status: VALID | DECLINED | MISSING
  → policy_violations: count + descriptions
  → spending_limit: current vs approved ceiling (C-043 enforcement)

google-ads-mcp.account.get_status(client_account_id)
  → account_status: ENABLED | SUSPENDED | CANCELLED | PENDING
  → budget_utilization: % of monthly budget used (alert at 80% — C-053)
  → policy_warnings: any active policy issues

Triggers:
  RESTRICTED/SUSPENDED → immediate alert to AM (reseller) + customer + Sujay
  PAYMENT_DECLINED → immediate alert + campaigns paused + customer notified
  POLICY_VIOLATION → Skill 20 (Crisis Communications) triggered if public-facing
  BUDGET_AT_80% → C-053 proactive signal → customer notified (LOW BALANCE equivalent for ads)
```

**SCR Pre-Publication Policy Check (gap closed from SIM-021):**

Before any content is published to a paid ad (not just organic), the SCR runs an additional check:

```
SCR Check 4 (new — ads-specific): Meta/Google Policy Pre-Check
  dental_clinic: MCI + ASCI healthcare + Meta healthcare advertising policy
    → Before/after images: BLOCKED unless written patient consent recorded in CAL
    → "Guaranteed" language: BLOCKED
    → Drug/treatment claims: BLOCKED
  restaurant: FSSAI advertising guidelines + Meta food policy
    → Health claims without FSSAI certification: BLOCKED
  
This runs BEFORE the ad goes live — not after Meta flags it.
Meta's own review catches violations AFTER publishing → account restrictions.
WAOOAW's SCR catches them BEFORE → no account risk.
```
