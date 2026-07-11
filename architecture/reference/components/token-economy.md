# Token Economy Layer — Component Specification

**Authority:** C-051 (Resource Transparency — LAW); ADR-024 (Token Economy)
**Date:** 2026-07-11 (v0.32.0)
**Component type:** Cross-cutting infrastructure layer in AI Runtime
**Constitutional Basis:** C-051, C-045, C-048, C-049, AD-022, AD-023, DP-020

---

## Position in Architecture

```
WhatsApp Webhook / Portal API
        ↓
Business Platform (tenant auth, RLS)
        ↓
AI Runtime
  ┌─────────────────────────────────────┐
  │   TOKEN ECONOMY LAYER (this spec)   │  ← NEW — sits before every LLM call
  │                                     │
  │  1. Message Classification Gate     │
  │  2. Semantic Cache Lookup           │
  │  3. Model Tier Router               │
  │  4. Usage Unit Tracker              │
  │  5. Usage Summary Generator         │
  └─────────────────────────────────────┘
        ↓
  [ZERO_COST path] → Template / MCP direct / Cache response
        ↓ (if LLM needed)
  [LLM dispatch] → FRONTIER / MID_TIER / LOCAL / FREE_BATCH
        ↓
  Constitutional Engine (ValidateAction, RecordEvidence)
        ↓
  MCP Tool Execution
```

---

## Sub-component 1: Message Classification Gate

### Purpose

Classify every incoming message BEFORE any LLM call. Routes 60–70% of messages to zero-cost paths, eliminating unnecessary inference spend.

### Classification Categories

**Agricultural Advisor:**

| Category | Examples | Path | LLM cost |
|---|---|---|---|
| `EMERGENCY` | "BANDH KAR", "STOP", "crop destroyed", "bandh karo" | CE.EmergencyStop | ₹0 |
| `ACKNOWLEDGMENT` | "ok", "theek hai", "achha", "👍", "samjha" | Template response | ₹0 |
| `PRICE_QUERY` | "aaj soyabean ka bhav", "onion price today", "mandi rate" | agmarknet-mcp direct | ₹0 |
| `WEATHER_QUERY` | "kal barish hogi?", "aaj ka mausam", "rain forecast" | weather-ensemble-mcp direct | ₹0 |
| `REPEAT_QUESTION` | Same question asked within 7 days (semantic match > 0.90) | Cache response | ₹0 |
| `SOCIAL_CHATTER` | "kaise ho?", "namaste", jokes, politics, religion | Graceful deflection template | ₹0 |
| `STATUS_QUERY` | "mera plan kya hai", "subscription kab khatam" | DB read → template | ₹0 |
| `ACTIONABLE_ADVISORY` | "patti par safed keede", "pani dena hai?", "spray kab karoon?" | MID_TIER LLM | Standard |
| `COMPLEX_ADVISORY` | "kya crop lagaun is baar?", "mujhe zyada paisa milega kaise?" | FRONTIER LLM | High |

**DMA Agent (portal messages):**

| Category | Examples | Path | LLM cost |
|---|---|---|---|
| `APPROVAL_ACTION` | "Approved", "Looks good, publish", "Post it" | Evidence record only | ₹0 |
| `REJECTION_WITH_REASON` | "Make it warmer", "Wrong tone", "Too formal" | REFINEMENT (MID_TIER) | Low |
| `STATUS_QUERY` | "How many posts this month?", "Budget remaining?" | DB read → USAGE_SUMMARY | Low |
| `NEW_CREATION_REQUEST` | "Create a Diwali post", "Make a new campaign" | FRONTIER (1st) / MID_TIER (2nd+) | Variable |
| `REFINEMENT_REQUEST` | "Slightly different version", "More professional" | MID_TIER REFINEMENT | Low |
| `STRATEGY_CONVERSATION` | "What should we focus on next?", "How's performance?" | FRONTIER/MID_TIER | High |
| `REPORT_REQUEST` | "Monthly summary", "How did we do?" | MID_TIER | Medium |

### Classification Model

**Phase 1 (Launch):** Rule-based classifier using keyword matching + intent patterns per language (English, Hindi, Marathi, Telugu). Deterministic, zero ML dependency. Handles 70–80% of cases correctly.

**Phase 2 (After 3 months of data):** Fine-tuned LOCAL model (Llama 3.2 1B or similar) trained on WAOOAW's own classification data. Handles nuance ("क्या करूं?" = ACTIONABLE_ADVISORY, not SOCIAL_CHATTER if crop context active).

**Multilingual handling:** Classification patterns registered for all supported languages. STT transcript runs classification in the same pipeline.

**Ambiguity rule:** When classification confidence < 0.75, escalate to ACTIONABLE_ADVISORY (safety default — never misclassify advisory as chatter).

### Evidence Record

Every classification decision is logged:
```sql
INSERT INTO institutional.message_classification_log
  (message_id, farmer_or_customer_id, classification, confidence, path_taken,
   llm_dispatched, cache_hit, cost_inr_paise, classified_at)
```
This log is the primary instrument for measuring gate effectiveness and refining the classifier.

---

## Sub-component 2: Semantic Cache

### Cache Architecture

```
Cache layers:
  L1 — In-memory (Redis): Hot items, last 24 hours, sub-millisecond retrieval
  L2 — Persistent semantic store (pgvector or Qdrant): Longer TTL, similarity search
  L3 — Pre-computed outbound cache: Scheduled messages generated at 02:00–04:00 IST
```

### Cache Key Schema

```python
cache_key_components = {
    "professional_type": "AGRICULTURAL_ADVISOR_INDIA",  # NEVER customer ID
    "crop": "cotton",
    "crop_stage_bucket": "40-55",                       # 15-day buckets
    "district_bucket": "nagpur_vidarbha",               # District-level granularity
    "weather_condition_bucket": "humid_moderate_rain",  # Broad category
    "symptom_category": "insect_leaf_discoloration",    # From classification
    "prompt_id": "AGRI/CROP_HEALTH/MORNING_CHECKIN"
}
# cache_key = SHA256(json.dumps(cache_key_components, sort_keys=True))
```

### Personalization Post-Retrieval

```python
cached_response = cache.get(cache_key)
if cached_response and similarity > threshold:
    # Inject customer-specific fields from Tier 2 — never from cache
    personalized = cached_response.replace(
        "{FARMER_NAME}", farmer_profile.name
    ).replace(
        "{CROP_STAGE_DAY}", str(current_stage_day)
    ).replace(
        "{SPECIFIC_MANDI}", nearest_mandi_name
    )
    return personalized  # Zero LLM cost
```

### Pre-computed Outbound Cache

```
Scheduled workflow (02:00–04:00 IST, low-priority):
  For each active farmer with a morning check-in scheduled:
    1. Fetch weather data → weather-ensemble-mcp
    2. Compute crop stage → DB
    3. Check district aggregate cache → cache hit? serve. miss? run LLM (FREE_BATCH)
    4. Store in pre-computed outbound cache with TTL = 24h
    5. Tag: SCHEDULED_SEND = 07:00 IST

07:00 IST delivery:
    → Read pre-computed cache → send to WhatsApp (zero LLM cost)
    → When farmer responds → THEN invoke ACTIONABLE_ADVISORY path
```

**Result:** Outbound advisory cost is near-zero. All agricultural advisor outbound messages are pre-computed. Only inbound responses trigger LLM inference.

---

## Sub-component 3: Model Tier Router

### Routing Logic

```python
def route_to_model(prompt_id: str, message_category: str, iteration_count: int):
    prompt_config = db.get_prompt_config(prompt_id)
    minimum_tier = prompt_config.minimum_model_tier  # From agent_prompt_versions
    
    # Tier elevation rules
    if message_category == "COMPLEX_ADVISORY" and minimum_tier == "MID_TIER":
        minimum_tier = "FRONTIER"  # Elevate for complex reasoning
    
    if iteration_count > 1 and minimum_tier == "FRONTIER":
        minimum_tier = "MID_TIER"  # Downgrade 2nd+ iterations (DMA content)
    
    # Provider selection per tier
    return model_provider_registry.get(minimum_tier)

# Provider registry (configurable — not hardcoded)
MODEL_PROVIDER_REGISTRY = {
    "FRONTIER":    ["openai/gpt-4o", "anthropic/claude-3-5-sonnet", "google/gemini-1.5-pro"],
    "MID_TIER":    ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash"],
    "LOCAL":       ["waooaw/classifier-v1", "waooaw/vocab-translator-v1"],
    "FREE_BATCH":  ["xai/grok-free", "google/gemini-free", "anthropic/claude-free"]
}
# Priority: first available at current rate limit. Fallback to next on list.
# NEVER downgrade tier on rate limit — queue or use next provider at same tier.
```

### Tier Assignment Table (all existing prompts)

The `minimum_model_tier` column value for every current prompt:

| Prompt ID | Current `change_type` | `minimum_model_tier` |
|---|---|---|
| DMA/STRATEGIC/SKILL_ACTIVATION_PLAN | BEHAVIOURAL | `FRONTIER` (first plan), `MID_TIER` (re-plans) |
| DMA/STRATEGIC/PERFORMANCE_ASSESSMENT | BEHAVIOURAL | `MID_TIER` |
| DMA/SELF_GOVERNANCE/DIAGNOSIS | BEHAVIOURAL | `FRONTIER` |
| DMA/SELF_GOVERNANCE/ESCALATION | BEHAVIOURAL | `MID_TIER` |
| DMA/MARKET_RESEARCH/* | BEHAVIOURAL | `MID_TIER` |
| DMA/CONTENT_STRATEGY/* | BEHAVIOURAL | `MID_TIER` |
| DMA/INSTAGRAM_MARKETING/CAPTION | BEHAVIOURAL | `MID_TIER` |
| DMA/INSTAGRAM_MARKETING/HASHTAGS | PHRASING_ONLY | `LOCAL` |
| DMA/PERFORMANCE_NARRATIVE/MONTHLY | BEHAVIOURAL | `MID_TIER` |
| TRADING/STRATEGIC/SESSION_PREP | BEHAVIOURAL | `MID_TIER` (daily prep) |
| TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT | BEHAVIOURAL | `FRONTIER` |
| TRADING/MARKET_ANALYSIS/TRADE_SETUP | BEHAVIOURAL | `MID_TIER` |
| TRADING/EXECUTION/ESCALATION_DECISION | BREAKING | `FRONTIER` |
| TRADING/RISK_MANAGEMENT/LOSS_LIMIT_ALERT | BREAKING | `FRONTIER` |
| TRADING/CRYPTO/REBALANCE_DECISION | BEHAVIOURAL | `MID_TIER` |
| TRADING/PERFORMANCE/SESSION_REPORT | BEHAVIOURAL | `MID_TIER` |
| TRADING/SELF_GOVERNANCE/DIAGNOSIS | BEHAVIOURAL | `FRONTIER` |
| TRADING/ONBOARDING/PROFILE_SETUP | BEHAVIOURAL | `FRONTIER` (one-time) |
| AGRI/STRATEGIC/SEASONAL_ADVISORY_PLAN | BEHAVIOURAL | `FRONTIER` (per season) |
| AGRI/STRATEGIC/ADVISORY_EFFECTIVENESS_REVIEW | BEHAVIOURAL | `MID_TIER` |
| AGRI/WEATHER_ADVISORY/FARMER_ALERT | BREAKING | `MID_TIER`* |
| AGRI/CROP_HEALTH/MORNING_CHECKIN | BEHAVIOURAL | `MID_TIER` |
| AGRI/MANDI_PRICE/SELL_TIMING | BEHAVIOURAL | `MID_TIER` |
| AGRI/CROP_PLANNING/NEXT_SEASON | BEHAVIOURAL | `FRONTIER` |
| AGRI/HINT_SYSTEM/WEEKLY_HINT | BEHAVIOURAL | `MID_TIER` |
| AGRI/SELF_GOVERNANCE/DIAGNOSIS | BEHAVIOURAL | `MID_TIER` |
| AGRI/ONBOARDING/OPENING_MESSAGE | BEHAVIOURAL | `MID_TIER` |
| AGRI/ONBOARDING/INFERENCE_CONFIRM | BEHAVIOURAL | `LOCAL` |
| CE/EVALUATE_POLICY/CONSTITUTIONAL | BREAKING | `FRONTIER` |
| PLATFORM_OPS/L1/HEALTH_CHECK | BEHAVIOURAL | `MID_TIER` |
| PLATFORM_OPS/L2/INCIDENT_DIAGNOSIS | BEHAVIOURAL | `FRONTIER` |
| MESSAGE_CLASSIFIER/* | CLASSIFICATION | `LOCAL` |
| */USAGE_SUMMARY | USAGE_SUMMARY | `MID_TIER` |

*AGRI/WEATHER_ADVISORY/FARMER_ALERT is BREAKING in change_type but can use MID_TIER because: (a) the constitutional decision is BINARY (alert or no alert), (b) the vocabulary translation (C-042) is the complex part, which MID_TIER handles well, (c) weather data is the primary input — not creative reasoning.

---

## Sub-component 4: Usage Unit Tracker

### Data Model

```sql
-- business.customer_usage_units (one row per customer per billing period)
-- See 03-enums-and-tables.sql for full DDL
```

### Unit Consumption Events

Every LLM call that consumes a Usage Unit fires:
```python
async def consume_usage_unit(
    organisation_id: UUID,
    prompt_id: str,
    unit_type: str,              # CONTENT_CREATION | QUICK_EDIT | ADVISORY_DAY | ...
    units_consumed: Decimal,     # Usually 1.0, sometimes 0.5 for partial
    model_tier_used: str,
    was_cache_hit: bool,         # Cache hits don't consume units
    reasoning_trace_id: UUID
):
    await db.execute("""
        UPDATE business.customer_usage_units
        SET {unit_type}_used = {unit_type}_used + :units_consumed,
            updated_at = NOW()
        WHERE organisation_id = :organisation_id
          AND billing_period_start = current_billing_period()
    """)
    
    # Threshold alerts
    remaining_pct = get_remaining_pct(organisation_id, unit_type)
    if remaining_pct < 0.30 and not already_alerted_this_period:
        await trigger_usage_alert(organisation_id, unit_type, remaining_pct)
```

### Emergency Exemption (Constitutional Floor — C-001, C-023)

```python
EMERGENCY_EXEMPT_PATHS = [
    "CE.EmergencyStop",
    "CE.RecordEvidence",
    "AGRI/WEATHER_ADVISORY/FARMER_ALERT",  # when triggered by IMD disaster alert
    "TRADING/RISK_MANAGEMENT/LOSS_LIMIT_ALERT",  # constitutional halt
]

def is_emergency_exempt(prompt_id: str, trigger_type: str) -> bool:
    if prompt_id in EMERGENCY_EXEMPT_PATHS:
        return True
    if trigger_type in ["EMERGENCY_STOP", "DISASTER_ALERT", "CIRCUIT_BREAKER"]:
        return True
    return False

# Emergency exempt calls: no unit deduction, no budget check, always proceed
```

---

## Sub-component 5: Usage Summary Generator

### When invoked

- Customer sends STATUS_QUERY message → immediate response
- Threshold crossings (30%, 10%, 0%) → proactive message
- Day 1 of new billing period → reset notification
- Portal dashboard load → always current

### Usage Summary Prompt

Routed to MID_TIER. Output is the customer-facing message in their language.

```
Prompt ID: {AGENT_TYPE}/TOKEN_ECONOMY/USAGE_SUMMARY
Constitutional basis: C-051; C-038; DP-020
```

The prompt takes:
- Remaining units by type
- Days remaining in billing period
- Usage pace (units/day)
- Predicted run-out date (if pace continues)
- Rollover units from last month
- Top high-value actions still possible with remaining budget

And produces:
- Agricultural: 2-sentence WhatsApp message in farmer's language
- DMA: Portal widget data + optional 1-line portal notification + optional WhatsApp summary
- Trading: Portal widget data (no WhatsApp for trading — professional portal interface)

### Portal Widget Data Contract

```json
{
  "widget_type": "USAGE_BUDGET",
  "billing_period": "2026-07",
  "days_remaining_in_period": 20,
  "predicted_runout_days": 18,
  "overall_health": "YELLOW",
  "units": [
    {
      "unit_type": "content_creation",
      "label": "Content Pieces",
      "included": 8, "used": 6, "remaining": 2,
      "rollover_available": 1,
      "effective_remaining": 3,
      "health": "ORANGE",
      "smart_suggestion": "Save for Diwali campaign (Day 15)"
    },
    {
      "unit_type": "quick_edit",
      "label": "Quick Edits",
      "included": 20, "used": 8, "remaining": 12,
      "rollover_available": 0,
      "effective_remaining": 12,
      "health": "GREEN",
      "smart_suggestion": null
    }
  ],
  "value_this_month": {
    "posts_created": 12,
    "campaigns_active": 2,
    "estimated_new_enquiries": 24
  },
  "topup_packs_available": [
    {"pack": "Extra Content Pack", "units": 5, "price_inr": 299, "razorpay_plan_id": "pack_content_5"}
  ]
}
```

Mobile app and portal render this contract into the widget. WhatsApp receives the `customer_message` text version.

---

## Cost Impact Projections

### Agricultural Advisor (per farmer, per month)

| Component | Unoptimized | Optimized | Saving |
|---|---|---|---|
| Outbound advisory (pre-computed) | ₹45 | ₹5 (FREE_BATCH) | 89% |
| Inbound responses (classification gate eliminates 65%) | ₹120 | ₹35 (MID_TIER) | 71% |
| Strategic cognition (FRONTIER, 2×/season) | ₹40 | ₹40 (unchanged — quality maintained) | 0% |
| Semantic cache hits (40% of advisory calls) | ₹30 | ₹0 | 100% |
| **Total per farmer/month** | **₹235** | **₹80** | **66%** |

At ₹200/month subscription: **₹120 gross margin per farmer** (from near-zero today).

### DMA (per customer, per month)

| Component | Unoptimized | Optimized | Saving |
|---|---|---|---|
| Content creation (FRONTIER 1st, MID 2nd+) | ₹450 | ₹120 | 73% |
| Quick edits (MID_TIER) | ₹200 | ₹40 | 80% |
| Research (cache amortization 2nd+ customer) | ₹300 | ₹80 | 73% |
| Strategic cognition + reports | ₹150 | ₹50 | 67% |
| **Total per customer/month** | **₹1,100** | **₹290** | **74%** |

At ₹1,499 Curtain Raiser: **₹1,209 gross margin per customer** (from ₹399 today).

---

## Implementation Notes

1. Message Classification Gate ships as a rule-based classifier first (no ML). Fine-tuned model after 3 months of labelled data.
2. Semantic cache starts with pgvector extension on the existing PostgreSQL instance. No new infrastructure required at launch.
3. Pre-computation workflow runs as a Temporal Cron workflow at 02:00 IST. One additional workflow definition in temporal-workflow-definitions.md.
4. `minimum_model_tier` column is added to `agent_prompt_versions` in the next SQL migration.
5. `customer_usage_units` table is tenant-scoped (RLS). One row per organisation per billing period. Created when subscription activates.
6. Top-up packs are Razorpay one-time orders (not subscriptions). `subscriptions.metadata` field stores pack credits.
