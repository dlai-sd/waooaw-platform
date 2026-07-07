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
