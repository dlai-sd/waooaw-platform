# ADR-034 — WAOOAW Billing Engine (WBE)

**Status:** Accepted
**Date:** 2026-07-30
**Author:** Enterprise Architect (INST-004) — GOAL-004 spec phase
**Constitutional Basis:** C-088 (Agent Billing Profile), C-089 (Minimum Margin Floor),
C-090 (Grandfather Pricing), C-091 (Thread Catalog Sovereignty), C-038 (Pro-rata Billing),
C-051 (Resource Transparency), C-048 (Non-Exploitation)
**Supersedes:** Billing logic previously scattered across ADR-022, ADR-024, ADR-026

---

## Context

Prior to GOAL-004, WAOOAW's billing logic was distributed across three ADRs and implemented
in fragments across the Business Platform and AI Runtime services:

- ADR-022: Razorpay subscription management, GST invoicing, pro-rata billing events
- ADR-024: Token Economy — LLM cost tiers (LOCAL/MID_TIER/FRONTIER)
- ADR-026: Ad Spend Wallet and 10% management fee on ad spend

This distributed design created three structural problems:

1. **No bilateral visibility**: WAOOAW could track what it charges customers (Side A) but
   had no system for tracking what it pays to providers (Side B). Margin calculation was
   impossible.

2. **Prepaid applied only to ad spend**: LLM costs, video generation, WhatsApp window costs
   were unguarded post-hoc expenses. A customer with heavy LLM usage consumed platform
   resources with no per-resource gate — violating the prepaid insurance principle.

3. **Not agent-agnostic**: Adding a new agent required code changes to billing logic. Every
   new agent introduced new hardcoded cost paths in the AI Runtime and Business Platform.

GOAL-004 introduces the **WAOOAW Billing Engine (WBE)** as a dedicated Python service that
centralizes all billing logic, enforces the universal prepaid gate, and operates entirely
from configuration — making it agent-agnostic by design.

---

## Decision

### 1. WBE as a Standalone Python Service

WBE is a dedicated Python 3.12 FastAPI service running in docker-compose (port 8140, sidecar
pattern consistent with razorpay-mcp port 8131 and oauth-vault port 8130).

WBE is NOT a module inside Business Platform or AI Runtime. It is a separate service because:
- BP is .NET — billing logic would require cross-language calls or duplication
- AI Runtime is responsible for LLM dispatch — embedding billing in AIR creates a
  separation-of-concerns violation (C-065 SDLC principle extends to service boundaries)
- WBE must be deployable and testable independently (billing bugs must not require
  full-stack restart to diagnose or fix)

All other services call WBE via internal REST API (not gRPC — billing is not a
constitutional enforcement action requiring CE's gRPC guarantees, but a business operation).

```
AI Runtime → WBE: GET /buckets/{customer_id}/{thread_type}   (balance check before dispatch)
AI Runtime → WBE: POST /buckets/{customer_id}/reserve        (lock before execution)
AI Runtime → WBE: POST /buckets/{customer_id}/release        (release after completion)
Business Platform → WBE: POST /subscriptions/activate        (onboarding payment processed)
Business Platform → WBE: POST /subscriptions/renew           (period renewal)
Business Platform → WBE: POST /topups                        (top-up purchase)
Business Platform → WBE: GET /customers/{customer_id}/summary (portal billing view)
Platform Operations → WBE: GET /platform/procurement/status   (WAOOAW's own spend)
Platform Operations → WBE: GET /platform/margin/report        (daily margin per customer)
```

### 2. Five Sub-Components

WBE is structured as five independent sub-components within the service:

#### 2.1 Wallet Engine

Manages the one-wallet, multiple-bucket architecture per customer.

- One `customer_wallets` row per customer (permanent — never deleted)
- N `wallet_buckets` rows per wallet (one per thread type, per bundle period)
- `bucket_reservations` for in-flight operations (lock → execute → release pattern)
- Bucket types: `llm_local`, `llm_mid`, `llm_frontier`, `video_clips`, `whatsapp_windows`,
  `image_gen`, `ad_spend`, `topup_*` variants

**Balance check SLA:** WBE must respond to balance check requests in ≤ 50ms (p99). This
is a synchronous call on the critical path of every LLM dispatch. WBE uses Redis cache for
hot buckets (customers active in the last 5 minutes). Cache TTL: 30 seconds. Any deduction
is written to PostgreSQL first, then cache invalidated — no eventual consistency.

**Reservation pattern:** AI Runtime reserves a budget before calling the LLM provider.
If the LLM call fails, the reservation is released. If it succeeds, the reservation is
consumed. This prevents a crash between LLM completion and deduction from leaving the
customer with used capacity not deducted.

#### 2.2 Markup Engine

Derives the offering price from the three-layer cost model and enforces C-089.

**Layer 1 — Thread Markup:**
```python
marked_up_cost = thread_catalog_entry.raw_cost_inr_paise * (1 + total_markup_pct)
# total_markup_pct = fx_buffer_pct + operational_overhead_pct + risk_premium_pct
# All values from institutional.thread_catalog; Founder-authorized changes only (C-091)
```

**Layer 2 — Bundle Cost Floor:**
```python
bundle_cost_floor = sum(
    thread_catalog[thread].marked_up_cost * bundle_profile[thread].ration
    for thread in bundle_profile.threads
) + infrastructure_share_paise
```

**Layer 3 — Platform Margin Application:**
```python
target_price = bundle_cost_floor / (1 - platform_margin_pct)
# platform_margin_pct set by Founder Action; stored in institutional.platform_config
```

**C-089 Enforcement:**
```python
if final_price < bundle_cost_floor * (1 + CONSTITUTIONAL_MINIMUM_MARGIN_PCT):
    raise BelowConstitutionalFloorError(
        f"Price {final_price} below floor {bundle_cost_floor}. "
        f"Minimum margin {CONSTITUTIONAL_MINIMUM_MARGIN_PCT}% required."
    )
    # Logs to institutional.pricing_floor_log (append-only)
    # Does NOT activate the configuration
```

The Markup Engine is read-only from the customer perspective — it derives and validates prices.
Activation of a new price (including for new subscribers) requires explicit WBE configuration
update via Founder-authorized API call.

#### 2.3 Usage Meter + Alert Engine

Tracks per-customer per-bucket consumption and fires threshold-triggered actions.

**Thresholds and actions:**

| Threshold | Trigger | Action |
|---|---|---|
| 50% consumed | Advisory | WhatsApp notification: "You've used half your [resource] this month." |
| 60% consumed | Top-up offer | WhatsApp: "At this pace, [resource] runs out [date]. Top up now?" |
| 85% consumed | Urgent | WhatsApp: "Running low on [resource]. Agent performance may change." |
| 95% consumed (ad_spend) | Campaign pause | Pause Meta/Google campaigns via provider API (saga) |
| 0% remaining | Graceful degradation | Route to ZERO_COST path; agent discloses per C-049 |

**Quiet hours:** 23:00–07:00 IST. Notifications at 50% and 60% thresholds are held during
quiet hours and sent at 07:00 IST with context. Notifications at 85% threshold are immediate
regardless of quiet hours. The 0% degradation is immediate regardless of quiet hours.

**Proactive Offer Engine:** Daily at 06:00 IST, the Alert Engine runs a velocity projection:
- Calculate each customer's 7-day average daily consumption per bucket
- Project: current_balance / daily_velocity = days_remaining
- If days_remaining < (days_left_in_period / 2): generate proactive top-up offer
- Check seasonal calendar (Diwali, Eid, Christmas, expiry weeks): if event within 21 days
  AND customer's bundle is relevant to the event: generate event pack offer

**Platform procurement projection:** Same daily job projects WAOOAW's own provider account
balances. If any provider account has < 7 days of runway: auto-generate Founder Action in
FOUNDER-ACTION.md with exact amount needed and urgency date.

#### 2.4 Platform Procurement Ledger

Tracks WAOOAW's own spend as a buyer of provider services.

- `institutional.provider_accounts` — one row per WAOOAW provider account (Kling AI, HeyGen,
  ElevenLabs, Vertex AI, WhatsApp BSP, Meta MBM credit, Google MCC)
- `institutional.platform_cost_ledger` — append-only log of every WAOOAW expense event
  (LLM API call cost, video generation cost, WhatsApp window charge, etc.)
- FX handling: USD-billed providers recorded at actual INR exchange rate on the day of cost
  (from a daily FX snapshot job that polls RBI reference rate at 09:00 IST)
- Daily spend actuals vs projected spend (derived from customer usage × marked-up thread costs)
- Monthly reconciliation: sum of all customer cost_floor allocations vs actual platform spend

**Cost attribution:** Every platform cost event is tagged with `customer_id`, `agent_type`,
`thread_type`, and `bundle_period`. This enables the margin calculation per customer.

#### 2.5 Reconciliation Engine

Runs daily at 02:00 IST (off-peak) to validate billing integrity.

**Daily reconciliation:**
1. Per-customer: sum all `platform_cost_ledger` entries tagged to this customer this period
   vs their bundle_cost_floor × (days_elapsed / days_in_period). Flag if actual > 110% of
   expected (unusual usage pattern — may need bundle adjustment)
2. WBE self-audit: for each wallet_bucket, compute sum of all ledger entries vs stored
   balance. If difference > 1 paise → halt all billing operations → alert Platform Operations
   → create Founder Action. No customer notification sent with incorrect balance.
3. Monthly margin per customer: revenue (Razorpay subscription amount) minus actual_cost_to_serve
   (sum of platform_cost_ledger for this customer this period). Flag customers with margin
   below C-089 floor.
4. Monthly margin per agent type: aggregate of all customers on each agent. Feeds the Markup
   Engine's next-period pricing review.

### 3. Agent Billing Profile — WBE Configuration Gate

WBE reads Agent Billing Profiles from `institutional.billing_profiles`. Before serving any
customer for any agent type, WBE checks:

```python
profile = billing_profiles.get(agent_type=agent_type, status='FOUNDER_AUTHORIZED')
if not profile:
    raise AgentNotBillableError(
        f"Agent {agent_type} has no Founder-authorized Billing Profile. "
        "Service blocked per C-088."
    )
```

This check happens at subscription activation time (not per-request) — so it is a one-time
gate at customer onboarding, not a per-LLM-call check.

### 4. Thread Catalog — Single Source of Truth

WBE reads all cost parameters from `institutional.thread_catalog`. No cost value is hardcoded
in WBE service code. Thread costs are updated via Founder-authorized API endpoint only.

The Thread Catalog is loaded into WBE's Redis cache at startup and refreshed every 5 minutes.
A Founder Action that updates a thread cost triggers an immediate cache invalidation via a
webhook from the administrative API.

### 5. Agency-Ready Schema Constraint

All wallet and bucket tables include `billing_entity_type` and `parent_wallet_id` columns
from day 1, defaulting to `DIRECT` and `NULL`. The GOAL-AGENCY implementation will activate
these columns — no schema migration required at that point.

---

## Service Configuration

```yaml
# docker-compose.yml addition
wbe:
  build:
    context: ./src/billing-engine
    dockerfile: Dockerfile
  ports:
    - "8140:8140"
  environment:
    - DATABASE_URL=postgresql://wbe_app:${WBE_DB_PASSWORD}@postgres:5432/waooaw
    - REDIS_URL=redis://redis:6379/2
    - RAZORPAY_WEBHOOK_SECRET=${RAZORPAY_WEBHOOK_SECRET}
    - CONSTITUTIONAL_MINIMUM_MARGIN_PCT=${CONSTITUTIONAL_MINIMUM_MARGIN_PCT}
    - FX_RATE_API_KEY=${FX_RATE_API_KEY}
  depends_on:
    - postgres
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8140/health"]
    interval: 30s
    timeout: 5s
    retries: 3
```

---

## Rejected Alternatives

**A — Embed billing in Business Platform (.NET):** Rejected. Cross-language complexity,
and BP is already responsible for employment contracts, subscriptions, and customer management.
Billing enforcement logic in BP would make BP a god-service.

**B — Embed billing in AI Runtime (Python):** Rejected. AIR is responsible for LLM dispatch
and RAG. Billing is a different concern. A billing bug in AIR requires redeployment of the
entire AI runtime — unacceptable for financial correctness.

**C — Distributed billing logic (status quo):** Rejected. The status quo is exactly what
produced the three structural problems identified in Context above.

---

## Consequences

- New service: `src/billing-engine/` — Python 3.12, FastAPI, port 8140
- New docker-compose service: `wbe`
- New database schema objects: see D-08 (DB Schema Update Spec, GOAL-004)
- New environment variables: `CONSTITUTIONAL_MINIMUM_MARGIN_PCT`, `FX_RATE_API_KEY`,
  `WBE_DB_PASSWORD`
- All services update: AI Runtime adds WBE client for balance check + reservation calls
- All services update: Business Platform adds WBE client for subscription/wallet events
- ADR-022 amended: single onboarding payment, universal prepaid, progressive renewal failure
- ADR-024 amended: bundle rations gate PSE before LLM dispatch
- ADR-026 amendment: ad_spend_wallets migrated to wallet_buckets (ad_spend bucket type)
- CCTs added: CCT-PREPAID-01 (prepaid gate), CCT-ONBOARD-01 (≤90s onboarding),
  CCT-BILLINGLOOP-01 (17 operational scenarios), CCT-SELFAUDIT-01 (balance reconciliation)
