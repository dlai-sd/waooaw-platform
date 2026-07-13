# ADR-006: API Rate Limiting Strategy

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Platform Architect (infrastructure capability) + Business Architect (customer tier model)
**Constitutional Basis:** GENESIS Part 01 — Cost Constraint (INR 10,000/month per non-production environment); GENESIS Part 03 — Minimum Viable Institution principle

---

## Context

Rate limiting prevents API abuse and enforces fair usage. At scale, per-customer tier rate limiting (e.g., Free: 100 req/min, Professional: 1000 req/min) requires infrastructure to track and enforce limits, plus business logic to define tiers.

However, at MVI scale with early customers, the overhead of rate limiting infrastructure is disproportionate to the risk. The platform has no customer tiers yet (those belong to Epoch 6+).

## Decision

**Defer dedicated rate limiting to Epoch 6. Use Container Apps max replica count as a crude rate limiter at MVI scale, plus ASP.NET Core built-in rate limiting middleware as a per-tenant backstop.**

Container Apps max replicas protects against platform overload. However, it does not prevent a single compromised or misbehaving tenant from monopolizing all available replicas. For that, ASP.NET Core 7+ includes a built-in `RateLimiter` middleware that requires zero additional infrastructure.

```csharp
// Business Platform Program.cs
builder.Services.AddRateLimiter(options =>
{
    options.AddFixedWindowLimiter("per-tenant", opt =>
    {
        opt.PermitLimit = 200;          // 200 requests
        opt.Window = TimeSpan.FromMinutes(1);
        opt.QueueLimit = 0;             // reject, don't queue
    });
});
// Partition key = tenant_id from JWT (extracted in middleware)
```

In Epoch 6 (Reference Product), when customer subscription tiers are defined, introduce per-tier limits using either:
- Azure API Management (if already introduced for developer portal)
- Replace the fixed-window limiter above with tier-specific limits from tenant configuration

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Azure API Management now | ~₹3,000-12,000/month (Basic/Standard tier). Violates INR 10k constraint. Adds operational complexity before customers exist. |
| Redis-based per-tenant rate limiting | Requires Redis (not in MVI stack). Adds cost and complexity before need is demonstrated. |
| Container Apps replica limit | Zero additional cost. Available now. Sufficient for early customer volumes. |

## Consequences

**Benefits:**
- Zero additional cost at MVI
- No infrastructure to manage
- Works for any traffic pattern automatically

**Trade-offs:**
- Not per-customer (all customers share the global rate limit)
- Cannot enforce subscription tier limits
- Cannot generate rate limit analytics per customer

**Review trigger:**
This decision should be revisited when any of these occur:
- First paid customer tier is defined
- API abuse incident occurs
- Customer requests usage analytics

---

## LLM-Aware Prompt DoS Protection (v2 — 2026-07-13)

Traditional rate limiting (requests/minute) is insufficient for AI platforms. A single LLM request consuming 25,000 tokens costs the same as 6,250 short requests. Request-count rate limiting does not protect against **prompt-level DoS attacks**.

### Three Attack Vectors and Mitigations

**Vector 1 — Long Context Bomb**

Attacker sends a message with 100,000 characters to maximize token consumption. At 200 req/min (current limit), this costs ₹300,000/hour from a single account.

```python
# AI Runtime — applied BEFORE any LLM call (Python)
MAX_INPUT_CHARS = 4000      # ~1,000 tokens — sufficient for any legitimate request
MAX_INPUT_TOKENS_ESTIMATE = 1200  # conservative estimate

def validate_llm_input(message: str, organisation_id: str) -> str:
    if len(message) > MAX_INPUT_CHARS:
        log_security_event("OVERSIZED_INPUT_ATTEMPT", organisation_id, len(message))
        # Truncate silently (better UX than error for genuinely long messages)
        # Note: log the truncation — repeated truncation = potential attack signal
        return message[:MAX_INPUT_CHARS]
    return message

# Legitimate use cases never need > 4,000 chars:
#   DMA: "Write an Instagram caption for my dental clinic" — ~60 chars
#   Agriculture: "Hail happened, crops damaged, what should I do?" — ~50 chars
#   Tutor: "I don't understand quadratic equations" — ~40 chars
```

**Vector 2 — Demo Mode Flood (unauthenticated — highest risk)**

The Agent Interview Mode (Section 3.23) allows unauthenticated users to start demo sessions. This is the most exposed attack surface — no account creation required.

```python
# Demo Mode rate limits — applied at the /meet/[agent-slug] endpoint
DEMO_SESSION_LIMITS = {
    "max_concurrent_per_ip": 2,           # Max 2 demo sessions per IP simultaneously
    "max_sessions_per_ip_per_hour": 5,    # Max 5 new demo sessions per IP per hour
    "max_tokens_per_demo_message": 500,   # Demo messages limited to ~125 words
    "max_demo_session_duration_min": 15,  # Hard 15-minute session limit (already in spec)
    "demo_daily_token_budget": 5000,      # Platform-wide daily demo token budget
}

# IP rate limiting for demo — implemented in Azure Container Apps ingress
# or ASP.NET Core RateLimiter with IP-based partition:
options.AddFixedWindowLimiter("demo-per-ip", opt =>
{
    opt.PermitLimit = 5;           // 5 demo sessions per IP per hour
    opt.Window = TimeSpan.FromHours(1);
    opt.QueueLimit = 0;
    opt.PartitionKey = ctx => ctx.Connection.RemoteIpAddress?.ToString() ?? "unknown";
});
```

**Vector 3 — WhatsApp SIM Farm**

Attacker acquires multiple SIM cards to create multiple WAOOAW accounts, each sending high-frequency messages.

```yaml
whatsapp_flood_protection:
  per_phone_message_rate:
    limit: 10 messages per 5 minutes per phone number
    enforcement: Phone Identity Service (ADR-023) tracks message timestamps per phone
    on_exceed: "Slow response (not block) — respond after 30-second delay. 
               WAOOAW must reply to WhatsApp messages; blocking violates TRAI rules.
               But delaying signals to the attacker that the rate limit was hit."
    security_event: WHATSAPP_RATE_LIMIT_HIT logged to CAL
    
  new_number_velocity:
    rule: "Phone numbers registered < 24 hours ago are subject to stricter limits"
    stricter_limit: 3 messages per 5 minutes (vs 10 for established numbers)
    rationale: "Legitimate customers don't flood messages in their first hour. 
                Automated SIM farm attacks always start immediately after registration."
    
  daily_llm_token_budget_per_phone:
    authenticated_customer: 50,000 tokens/day (well above any legitimate use)
    new_unverified_number: 5,000 tokens/day
    on_exceed: "Session suspended for remainder of day. Customer notified."
    cost_cap: "50,000 tokens × ₹0.001 = ₹50/customer/day max LLM cost. 
               Platform budget is predictable regardless of attack."
```

### Temporal Workflow Circuit Breaker

Each customer message triggers a Temporal workflow. Flooding messages = flooding Temporal task queue = infrastructure overload even if LLM calls are blocked.

```python
# AI Runtime — before starting any Temporal workflow
WORKFLOW_QUEUE_DEPTH_LIMIT = 1000  # Max pending workflows across all customers

async def start_agent_workflow(request: AgentRequest) -> str:
    # Check Temporal queue depth before accepting new work
    queue_depth = await temporal_client.count_workflows(
        query="ExecutionStatus='Running' OR ExecutionStatus='New'"
    )
    if queue_depth > WORKFLOW_QUEUE_DEPTH_LIMIT:
        log_security_event("TEMPORAL_BACKPRESSURE", request.organisation_id)
        raise HTTPException(
            status_code=503,
            detail={"error": "SERVICE_BUSY", "retry_after": 30}
        )
    return await temporal_client.start_workflow(...)
```

### Cost-Based Hard Limits (Daily Budget Cap)

The ultimate DoS protection: even if an attacker bypasses all rate limits, the daily LLM cost is capped:

```yaml
platform_daily_llm_budget_cap:
  total_platform_daily_budget_inr: 500  # ₹500/day max LLM cost at MVI
  per_customer_daily_cap_inr: 50        # ₹50/customer/day
  demo_pool_daily_cap_inr: 50           # ₹50/day for all demo sessions combined
  
  enforcement: "AI Runtime tracks cumulative spend via Redis counter (or PostgreSQL at MVI).
                When daily cap is hit: all LLM calls for that scope return 503.
                Resets at midnight IST."
  alert_threshold: "Platform operations alerted at 80% of daily budget."
  
  note: "At MVI with 10-50 customers, ₹500/day = well above legitimate usage.
         This cap prevents a worst-case financial DoS from costing more than ₹500/day
         regardless of attack volume."
```

