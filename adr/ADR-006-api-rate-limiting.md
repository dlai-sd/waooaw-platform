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

**Defer dedicated rate limiting to Epoch 6. Use Container Apps max replica count as a crude rate limiter at MVI scale.**

Container Apps can be configured with a maximum replica count. When all replicas are at capacity, new requests receive 429 responses automatically. This is "infrastructure-level" rate limiting — not per-customer, but sufficient for MVI.

In Epoch 6 (Reference Product), when customer subscription tiers are defined, introduce dedicated per-tier rate limiting using either:
- Azure API Management (if already introduced for developer portal)
- ASP.NET Core middleware rate limiting (per-tenant, using tenant_id from JWT)

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
