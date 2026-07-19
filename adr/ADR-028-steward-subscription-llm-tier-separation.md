# ADR-028 — Steward and Subscription Tier LLM Access Separation

**Status:** ACCEPTED
**Date:** 2026-07-19
**Deciders:** Enterprise Architect, Founder (Yogesh Khandge)
**Constitutional Basis:** C-051 (Resource Transparency), C-064 (Three-Human Institution), C-068 (Steward Access Isolation), C-002 (Trust through Evidence)

---

## Context

ADR-024 defined a four-layer Token Economy for customer-facing agent sessions, routing messages through LOCAL → MID_TIER → FRONTIER based on message classification and minimum model tier per skill. This was designed for cost efficiency at scale.

Two gaps were identified in the 2026-07-19 PMO review:

1. **Steward sessions (Yogesh, Sujay, Ojal) were not addressed by ADR-024.** The three stewards interact with the platform via WAOOAW AI Agent — Steward Assistant (architecture/reference/steward-interface.md). Their governance decisions — constitutional approvals, prompt quality reviews, ethics assessments — require the highest quality reasoning available. Routing steward sessions through the LOCAL/MID_TIER classification gate is architecturally incorrect and constitutionally risky (a Tier 3 constitutional decision made with a degraded LOCAL-tier response is a governance failure).

2. **Customer subscription tiers were not mapped to LLM access tiers.** ADR-024 assumed all customers receive the same model tier routing. The platform's hiring plans (Essential / Professional / Enterprise) create different value propositions, and one differentiation axis is AI model quality. A customer on the Essential plan should receive LOCAL + MID_TIER routing; a customer on Enterprise should receive FRONTIER-preferred routing. This differentiation is both a business model requirement and a C-051 compliance obligation — customers must be told what model tier their plan includes.

Additionally, ADR-003 (JWT claims) does not include a `plan_tier` claim, making it impossible for the AI Runtime to read the customer's subscription tier from the JWT at routing time.

---

## Decision

### Decision 1: Steward Sessions Always Route to FRONTIER

The AI Runtime LLM Gateway reads the `role` claim from the JWT **before** applying ADR-024 message classification.

```python
def route_llm_request(jwt_claims: dict, message: Message) -> LLMTier:
    # Steward bypass — always FRONTIER, no classification gate
    if jwt_claims.get("role") == "steward":
        return LLMTier.FRONTIER
    
    # Customer routing — apply ADR-024 classification + plan tier
    plan_tier = jwt_claims.get("plan_tier", "essential")
    return classify_and_route(message, plan_tier)
```

**Rationale:** Steward sessions are governance actions, not production workload. They are infrequent (≤3 users, typically <10 sessions/day combined), so the cost impact is negligible. The constitutional risk of a governance decision made with a degraded model far outweighs the cost difference. Additionally, as new frontier models are released (Claude 4, GPT-5, Gemini Ultra), stewards automatically access them without any configuration change — the platform's governance capability improves as AI improves.

**Which FRONTIER model:** Configurable via `STEWARD_FRONTIER_MODEL` environment variable in Key Vault. Default: `gpt-4o`. This allows Yogesh to authorize a switch to a newer model (Claude, Gemini) without a code change — only a Key Vault update (Tier 1, Sujay authorization).

### Decision 2: Customer Plan Tier Maps to LLM Access Tier

Three customer subscription tiers are defined. The mapping is:

| Plan | JWT `plan_tier` | LLM Access | FRONTIER Cap |
|---|---|---|---|
| **Essential** | `essential` | LOCAL classification gate + MID_TIER for advisory | No FRONTIER access |
| **Professional** | `professional` | LOCAL classification gate + MID_TIER default + FRONTIER for STRATEGY_CONVERSATION and COMPLEX_ADVISORY | 50,000 FRONTIER tokens/month (C-051 budget) |
| **Enterprise** | `enterprise` | LOCAL for ZERO_COST only + FRONTIER preferred for all LLM categories | Unlimited within C-051 budget ceiling |

**Escalation rule (per ADR-024):** If the plan's permitted tier is unavailable, escalate UP (never DOWN). If FRONTIER is unavailable for an Enterprise customer, escalate to... there is no higher tier. In this case, queue the request with a ≤30s retry, then fall back to MID_TIER with a C-049 honest disclosure to the customer: *"I'm using a slightly less capable model for this response — your query is queued for FRONTIER retry."*

**No silent downgrade:** Routing a Professional customer's STRATEGY_CONVERSATION to LOCAL without disclosure is a C-048 violation. Any tier downgrade below the plan's minimum triggers a C-049 disclosure event.

### Decision 3: ADR-003 Amendment — Add `plan_tier` to Customer JWT

The Keycloak Business Platform client must include `plan_tier` in the JWT access token, populated from the customer's active subscription record in `business.subscriptions`.

Updated JWT claims structure:

```json
{
  "sub": "customer-uuid",
  "tenant_id": "customer-uuid",
  "role": "customer",
  "plan_tier": "essential | professional | enterprise",
  "subscription_id": "sub-uuid",
  "iat": 1234567890,
  "exp": 1234567890
}
```

Keycloak Protocol Mapper: `plan_tier` sourced from user attribute `waooaw_plan_tier`, set by Business Platform at subscription activation via Keycloak Admin API.

For steward JWTs:

```json
{
  "sub": "steward-uuid",
  "role": "steward",
  "person": "yogesh | sujay | ojal",
  "iat": 1234567890,
  "exp": 1234567890
}
```

Note: steward JWTs have no `plan_tier` — the `role: steward` bypass makes it irrelevant.

---

## Consequences

### Positive

- Steward governance quality is always at maximum capability — no constitutional risk from model degradation
- Customer plan differentiation gives a clear value ladder: Essential → Professional → Enterprise
- C-051 compliance: customers are told their plan's model tier in the subscription contract and usage summary
- New frontier models automatically benefit stewards without code change
- `plan_tier` in JWT enables zero-latency tier routing — no DB lookup at request time

### Negative

- Steward FRONTIER cost is an operating cost — estimated ≤₹500/month at current steward usage levels
- Keycloak Protocol Mapper must be updated and tested
- Existing customer JWTs (pre-ADR-028) have no `plan_tier` — migration plan: default to `essential` for all existing customers until their subscription record is updated

### Neutral

- The LOCAL classification gate (ADR-024 Layer 1) still runs for ALL customer sessions — stewards bypass it; customers always go through it first

---

## Alternatives Considered

### Alternative: Apply ADR-024 classification to steward sessions with FRONTIER as top tier
Rejected. The classification gate adds 50-100ms latency for a governance decision. More importantly, if the LOCAL classifier misroutes a steward's constitutional question to MID_TIER (e.g., classifying "should we ratify C-070?" as ACKNOWLEDGMENT), the governance decision is made with degraded context. The risk is asymmetric — the cost saving is ₹0.10, the risk is a constitutional decision made incorrectly.

### Alternative: Separate LLM provider for stewards (e.g., Claude API for stewards, OpenAI for customers)
Considered. This gives stewards access to a different reasoning style (valuable for constitutional analysis). Deferred to v2 — the architectural pattern supports it (change `STEWARD_FRONTIER_MODEL` env var), but managing two LLM provider clients adds complexity for MVI. Yogesh can authorize this change post-launch without an ADR amendment.

---

## Implementation Notes

**New files required:**
- `infrastructure/terraform/modules/core/variables.tf` — add `steward_frontier_model` variable
- `src/ai-runtime/llm_gateway.py` — add steward bypass before classification gate
- `src/business-platform/subscription_service.cs` — add `plan_tier` to Keycloak user attribute on subscription activation
- `infrastructure/keycloak/waooaw-realm.json` — add `plan_tier` protocol mapper to customer client
- DB migration `07-agent-prompts.sql` — add `professional.agent_prompts` table (new gap G-STEWARD-02, required for prompt deployment pipeline)

**Dependent ADR:** ADR-003 is amended by Decision 3 above. The ADR-003 file should note "Extended by ADR-028 — plan_tier and steward JWT claims added 2026-07-19."
