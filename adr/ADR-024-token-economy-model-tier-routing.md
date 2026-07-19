# ADR-024 — Token Economy: Model Tier Routing and Semantic Cache

**Status:** ACCEPTED
**Date:** 2026-07-11
**Deciders:** Enterprise Architect, Chief Platform Architect
**Constitutional Basis:** C-051 (Resource Transparency — LAW); C-045 (Prompt as Constitutional Artifact); C-048 (Non-Exploitation); C-049 (Honest Limitation); AD-022; AD-023; DP-020

---

## Context

WAOOAW agents make LLM inference calls for every skill heartbeat, strategic cognition trigger, and conversational response. At launch with a small pilot, all calls could use a frontier model. At 1,000 farmers receiving daily agricultural advisory, the cost structure becomes unsustainable:

- 1,000 farmers × 4 LLM calls/day × ₹0.18/call (frontier GPT-4o) = ₹720/day = ₹21,600/month
- Agricultural subscription revenue: 1,000 × ₹200 = ₹2,00,000/month
- AI cost alone: 10.8% of revenue — before infrastructure, support, or margin

At scale (50,000 farmers), this becomes ₹10,80,000/month in AI cost vs ₹1,00,00,000 revenue (10.8%) — acceptable but not sustainable if the cost base grows with conversation depth.

The DMA problem is different: customers iterate creative content. A customer who requests 30 revisions of a social post is entitled to do so within their subscription — but at frontier rates, this eats the entire margin.

Additionally, WhatsApp agents receive many messages that do not require LLM inference (acknowledgments, direct API queries, emergency keywords). Routing these to an LLM wastes money and adds latency.

---

## Decision

Implement a four-layer Token Economy architecture:

### Layer 1: Message Classification Gate

A LOCAL-tier classifier runs on EVERY incoming message before any LLM is dispatched. This is non-negotiable (architectural invariant).

```
Incoming message → Message Classification Gate (LOCAL model, <100ms)
                        ↓
  ZERO_COST categories:     Template response or direct API call (no LLM)
    - EMERGENCY              → CE.EmergencyStop path (no LLM)
    - ACKNOWLEDGMENT         → Template response
    - PRICE_QUERY            → MCP direct call (agmarknet-mcp, no LLM)
    - WEATHER_QUERY          → MCP direct call (weather-ensemble-mcp, no LLM)
    - REPEAT_QUESTION        → Semantic cache lookup (no LLM if cache hit)
    - SOCIAL_CHATTER         → Graceful deflection template
    - APPROVAL_ACTION        → Evidence record only (no LLM)
    - STATUS_QUERY           → Database read → template (no LLM)
  
  LLM categories:           Route to appropriate tier
    - ACTIONABLE_ADVISORY   → MID_TIER (standard crop/business question)
    - NEW_CREATION          → FRONTIER (first time) | MID_TIER (2nd+ iteration)
    - REFINEMENT            → MID_TIER (content adjustment)
    - STRATEGY_CONVERSATION → FRONTIER (strategic decision)
    - COMPLEX_ADVISORY      → FRONTIER (multi-factor analysis, first seasonal plan)
```

**Expected elimination rate:** 60–70% of incoming messages routed to ZERO_COST path. LLM cost is incurred only for genuinely novel advisory needs.

---

### Layer 2: Model Tier Dispatch

Every `agent_prompt_versions` record has a `minimum_model_tier` field. AI Runtime reads this before dispatching.

| `change_type` (existing) | Default `minimum_model_tier` |
|---|---|
| `BREAKING` | `FRONTIER` — constitutional decisions |
| `BEHAVIOURAL` | `MID_TIER` — daily execution quality |
| `PHRASING_ONLY` | `LOCAL` — formatting and vocabulary translation |
| `STRATEGIC` | `FRONTIER` (first plan) → `MID_TIER` (subsequent assessments) |
| `CLASSIFICATION` | `LOCAL` — classification tasks always |
| `USAGE_SUMMARY` | `MID_TIER` — communicating budget status |

**Tier escalation rule:** If the declared minimum tier is unavailable (rate limit, outage), escalate to the next tier UP. NEVER route DOWN below minimum without EA-approved constitutional review.

**No-escalation rule for LOCAL:** If a task is classified as LOCAL and the LOCAL model is unavailable, the task is queued (not escalated to MID_TIER) — because escalating a vocabulary translation task to a frontier model is an AD-022 violation, not a safety measure.

---

### Layer 3: Semantic Response Cache

Before ANY LLM call for a BEHAVIOURAL or lower tier prompt:
1. Compute embedding of the prompt input (using LOCAL embed model)
2. Query the semantic cache (Redis + pgvector or dedicated vector DB)
3. If similarity > threshold: serve cached response, personalize with customer-specific fields
4. If cache miss: run LLM call, store response in cache

```
Cache key components (NEVER include customer-identifying data):
  {professional_type, crop/domain, geography_bucket, stage_bucket, 
   symptom_category, weather_bucket, context_hash}

Personalization layer (applied POST cache retrieval):
  {farmer_name, farm_size, specific_date, specific_mandi_name}
  — these come from Tier 2 customer context, NEVER from the cache
```

**Similarity thresholds by prompt type:**

| Prompt category | Similarity threshold | Rationale |
|---|---|---|
| Agricultural weather alerts | 0.92 | High specificity needed — location/crop/stage must match closely |
| Crop health advice | 0.90 | Symptom matching requires precision |
| DMA content creation | Not cached | Creative content must be unique — cache creates plagiarism risk |
| DMA market research | 0.85 | Market context is shared across same segment in same city |
| Price advisory | 0.75 | General price trend advice is widely applicable |
| Usage summaries | Not cached | Always real-time customer-specific |

**Cache invalidation triggers:**
- New district-level disease outbreak alert
- New IMD seasonal forecast issued
- New MSP announcement
- New competitor data for DMA customers in same geography
- TTL expiry (7 days agricultural, 14 days DMA)

---

### Layer 4: Pre-computation at Off-Peak

Outbound messages with known send times are pre-computed at 02:00–04:00 IST:

```
02:00 IST batch (FREE_BATCH tier where possible, MID_TIER where needed):
  For each active farmer:
    1. Fetch weather forecast → weather-ensemble-mcp (API, free)
    2. Compute crop state day → database (free)
    3. Run MORNING_CHECKIN prompt → pre-generate
    4. Store in pre-computed outbound cache (TTL: 24 hours)

07:00 IST delivery:
    → Send pre-computed morning message (ZERO additional LLM cost)
    → Farmer response → THEN trigger adaptive response (MID_TIER)
```

**DMA pre-computation:**
- Monthly performance narratives are pre-computed overnight on Day 30
- Monthly content calendar proposals pre-computed on Day 28 based on KPI data
- Delivered on Day 1 of next month — zero delay, zero morning-peak API load

---

## Usage Unit System (C-051 — Customer-Facing Budget)

### Concept

Tokens must be translated into customer-meaningful units before any customer-facing display. No customer should ever see "tokens", "context window", or "API calls."

### UsageUnit Definitions

**Agricultural Advisor (₹200/month):**

| Usage Unit | Included/month | Token equivalent | Description |
|---|---|---|---|
| Advisory Day | 30 | All prompts for one day | Full daily service: weather alert + check-in + price check |
| Crop Question | 10 bonus | ~1,500 tokens | Extra specific question beyond daily service |
| Seasonal Plan | 2 | ~5,000 tokens | Full crop recommendation with 6-lens analysis |
| PMFBY Report | Unlimited | ~3,000 tokens | Emergency exemption — always available |
| Emergency Alert | Unlimited | Exempt | Constitutional floor — never metered |

**Communication:**
- Day 1 of month: "नया महिना! 30 दिन पूरी सेवा ready है।" (30 days full service ready)
- At 30% remaining: "Suresh dada, 9 more days of daily advice this month."
- At 10% remaining: "3 days left. Weather alerts always available."
- Month end: "New cycle starts tomorrow. Tonight's alerts still come."
- NEVER a hard cutoff — emergency advice exempt always

**DMA (₹1,499 Curtain Raiser / ₹2,499 Growth Engine / ₹3,999 Maturity Phase):**

| Usage Unit | Curtain Raiser | Growth Engine | Maturity Phase | Token equiv |
|---|---|---|---|---|
| Content Creation | 8 | 18 | 35 | ~3,000 out |
| Quick Edit | 20 | 45 | Unlimited | ~800 out |
| Research Query | 3 | 8 | 15 | ~5,000 (w/RAG) |
| Strategy Session | 1 | 3 | 6 | ~8,000 |
| Performance Report | 1 (monthly) | 1 | 1 | ~4,000 |
| Auto-publish | Unlimited | Unlimited | Unlimited | 0 tokens |
| Approval decisions | Unlimited | Unlimited | Unlimited | 0 tokens |

**Rollover policy:** 25% of unused Content Creations and Quick Edits roll to next month (maximum 1 month). Research and Strategy do not roll over. This prevents "save everything for the last day" behaviour and rewards consistent engagement.

**Top-up packs (Razorpay one-time purchase):**
- Extra Content Pack: 5 Content Creations = ₹299 + GST
- Extra Research Pack: 3 Research Queries = ₹199 + GST

### Portal Widget Specification

```
┌──────────────────────────────────────────────┐
│  Your Creative Budget — July 2026             │
│                                              │
│  Content Pieces  ████████░░  6/8  remaining  │  GREEN > 60%
│  Quick Edits     ████████░░ 14/20 remaining  │  YELLOW 30-60%
│  Research        ██░░░░░░░░  1/ 3 remaining  │  ORANGE < 30%
│  Strategy        ░░░░░░░░░░  0/ 1 remaining  │  RED 0
│                                              │
│  At this pace: budget lasts ~18 more days    │  Predictive display
│                                              │
│  [Smart suggestions] →                       │
│  "Save your last Strategy for the            │
│   Diwali campaign planning (Day 15)"         │
│                                              │
│  ─────────────────────────────────────────── │
│  This month produced:                        │
│    12 social posts | 3 campaigns             │
│    Estimated: +24 new enquiries              │  VALUE DISPLAY
└──────────────────────────────────────────────┘
```

**Colour coding:**
- Green (>60% remaining): Normal
- Yellow (30–60%): "Using well — on track"
- Orange (10–30%): Proactive agent suggestion to prioritize high-impact usage
- Red (<10%): "Top up or wait for reset" + rollover display
- Grey: Unlimited items — no display (auto-publish, approvals)

**Predictive pace display:** "At this pace, budget lasts ~18 more days" — computed from (units_used / days_elapsed) × days_remaining.

**Smart suggestion engine:** When a customer attempts to use a nearly-exhausted unit type, the agent offers an alternative:
> "You've used 7 of 8 Content Creations. Instead of creating a new post, can I make a Quick Edit to your best-performing post from last month? That costs a Quick Edit, not a Content Creation."

---

## Alternatives Considered

### Alternative A: Pure token-based limits with dashboard
Rejected — tokens are meaningless to customers. A dentist who sees "45,000 tokens remaining" has no idea if that's 2 days or 2 weeks of service. C-051 requires customer-language communication.

### Alternative B: No limits — flat subscription covers all usage
Rejected — economically not viable. One chatty farmer or one DMA customer who iterates 60 times per month can destroy the economics of the entire subscription tier. C-038 requires sustainable billing.

### Alternative C: Hard cutoff at budget limit
Rejected — unconstitutional. C-001 (Emergency Stop) and C-023 (Evidence First) create emergency obligations that cannot be metered. A hard cutoff that blocks a cyclone warning to save tokens is a constitutional violation. The architecture must always allow emergency advisory through regardless of budget state.

### Alternative D: Real-time cost monitoring with dynamic pricing
Rejected — complexity and unpredictability. Customers need to know what they're getting for a fixed price (C-038 Billing Transparency). Dynamic pricing based on conversation length would make the subscription value unpredictable.

---

## Consequences

**Positive:**
- Agricultural advisor unit economics: Cost per farmer/month ₹180–280 (unoptimized) → ₹18–35 (optimized). Margin transforms from near-zero to 82–91%.
- DMA economics: API cost per customer ₹800–1,200 → ₹120–200. Margin per customer improves to 87–93%.
- Customer experience: Customers understand their remaining service in their language. No surprise cutoffs.
- Constitutional compliance: Emergency advisory always exempt — C-001 floor maintained.
- Competitive moat: Semantic cache creates a network effect on cost. Each additional customer in a segment reduces per-customer AI cost. Competitors starting fresh cannot replicate this without customer volume.

**Negative:**
- Implementation complexity: Message Classification Gate requires a LOCAL classifier model to be fine-tuned and deployed. This is additional ML infrastructure.
- Cache management: Semantic cache requires careful TTL and invalidation management. A stale cache delivering outdated crop advice is worse than no cache.
- UsageUnit abstraction: The mapping of tokens to usage units must be calibrated carefully. If 1 "Content Creation" is underpriced in tokens, the subscription becomes loss-making for heavy users.

**Mitigation:**
- Cache invalidation is event-driven (not TTL-only): any new advisory data triggers selective invalidation
- UsageUnit token mapping is reviewed quarterly based on actual usage patterns
- Message Classification Gate starts with a rule-based classifier (not ML) and graduates to fine-tuned model after 3 months of data

---

## Amendment — ADR-029 Extension (2026-07-19)

ADR-029 extends Layer 2 (Model Tier Dispatch) with a **provider dimension** and replaces single-provider routing with the Provider Selection Engine (PSE).

**Changes to `professional.agent_prompts` (formerly `agent_prompt_versions`):**
- `minimum_model_tier` field: unchanged — still enforces tier floor
- New field `preferred_provider` (nullable): overrides PSE Layer B ranking for specific skills.
  Example: Agricultural Skill 2 (price advisory) sets `preferred_provider = sarvam_saaras` to enforce C-042 compliance for Hindi/Marathi output. Null = PSE chooses.

**PSE replaces static tier dispatch:**
- Old: `tier → model_name` (single Azure OpenAI endpoint)
- New: `tier → PSE(Rule Engine + Performance Engine) → provider + model_name`

**Provider priority order (from ADR-029):**
- MID_TIER: `google_gemini_flash` → `sarvam_saaras` (agri override) → `azure_gpt4o_mini` (fallback)
- FRONTIER: `google_gemini_pro` → `azure_gpt4o` (fallback)
- LOCAL: `ollama_llama3` → `ollama_ai4bharat` (Indian language tasks) → queue (no LLM fallback)

**No change to token economy cost model** — UsageUnits abstraction means customers are unaware of which provider was used. C-051 transparency applies to tier (essential/professional/enterprise), not to specific provider names.

## Implementation

Governed by:
- `professional.agent_prompts.minimum_model_tier` + `preferred_provider` — tier + provider enforcement
- `institutional.provider_dispatch_events` — raw PSE outcome log (ADR-029)
- `institutional.pse_provider_ranking` — materialized view, PSE real-time ranking (ADR-029)
- `institutional.provider_circuit_breaker` — PSE circuit-breaker state (ADR-029)
- `business.customer_usage_units` — customer budget tracking
- `institutional.message_classification_log` — classification gate audit
- `institutional.prompt_cache_metadata` — cache hit/miss analytics
- Token Economy Layer component (`architecture/reference/components/token-economy.md`)
- AGENT-AUTHORING-GUIDE Section 3.16 (Token Economy Standard)
- Activation Gate Section 11 (Token Economy Gate)

---

**Supersedes:** Nothing (new decision)
**Related ADRs:** ADR-020 (MCP Integration), ADR-022 (Razorpay billing), ADR-018 (Prompt Versioning)
