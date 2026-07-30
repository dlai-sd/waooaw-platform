# Agent Billing Profile — Agricultural Advisor

**Authority:** Chief Business Architect (INST-003) — GOAL-004 D-09
**Agent Spec:** architecture/reference/agents/agricultural-advisor-agent.md
**Constitutional Basis:** C-088 (Agent Billing Profile Requirement)
**Status:** FOUNDER_AUTHORIZED — 2026-07-30
**WBE Registry ID:** `agricultural_v2` (institutional.billing_profiles.agent_type)

---

## Thread Profile

### Platform Threads (inherited)
- `llm_local` — message classification, ZERO_COST price/weather queries
- `llm_mid_sarvam` — advisory in regional languages (Hindi, Marathi, Telugu, etc.) — PSE-R02
- `llm_mid_gemini` — fallback MID_TIER when Sarvam unavailable
- `llm_frontier_gemini` — seasonal crop planning, complex multi-factor analysis (rare)
- `whatsapp_window` — primary interface (WhatsApp-first agent, ADR-023)
- `infra_share` — platform infrastructure

### Agent-Specific Threads (all zero-cost)
- `climate_data_imd` — IMD free API (₹0)
- `crop_prices_agmarknet` — Agmarknet free portal (₹0)
- `scheme_data_pm_kisan` — Government scheme data (₹0)
- `soil_data_icar` — ICAR free portal (₹0)

**Key insight:** Agricultural Advisor has zero agent-specific thread cost. ALL costs are platform threads. This makes it structurally the highest-margin agent at every bundle tier.

## Default Bundle Rations

| Resource | thread_id | Starter (₹200/month incl. GST) |
|---|---|---|
| LOCAL classification | `llm_local` | Unlimited |
| MID_TIER LLM calls (Sarvam/Gemini) | `llm_mid_sarvam` | 120 calls/month |
| FRONTIER LLM calls | `llm_frontier_gemini` | 2 (seasonal plan only) |
| WhatsApp windows | `whatsapp_window` | 45 windows/month |
| Government data API calls | All `*_imd/agmarknet/pm_kisan/icar` | Unlimited (free) |
| Infrastructure share | `infra_share` | ₹180/month |

*Note: Agricultural Advisor is a single-tier offering (no Runner/Winner). The ₹200/month (₹169 + GST) price reflects the social mission pricing. Cost floor at 120 MID calls + 45 windows + infra = ~₹90/month. Implied margin: ~47% — BELOW the suggested 55% C-089 floor.*

*This is a deliberate Founder social mission decision: serving small farmers at near-cost pricing. C-089 allows the Founder to set the minimum margin % — if Yogesh sets agricultural-tier minimum margin at 40%, the ₹200 price is constitutionally valid. This requires an explicit Founder Action to document the social mission pricing exception.*

## Minimum Wallet Requirements Per Active Skill
- No ad spend wallet required
- No minimum balance — all data sources are free

## Trial Profile (Zero-Cost Substitutions)
- `llm_mid_sarvam` / `llm_mid_gemini` → Ollama AI4Bharat IndicBERT (LOCAL, Indian language)
- All government APIs → live data (already free, no substitution needed)
- `whatsapp_window` → Demo BSP allowance

## Constitutional Billing Obligations Specific to Agricultural
- C-042 (Vocabulary Mandate — LAW): agent MUST respond in farmer's own language. If MID_TIER bucket exhausted and ZERO_COST path cannot provide regional language, C-042 takes precedence — agent requests Sarvam top-up or switches to Gemini Flash. Language quality cannot be compromised for cost savings.
- WhatsApp Phone-as-Identity (ADR-023): billing contact is the WhatsApp phone number, not email. UPI payment links sent via WhatsApp.
- Social mission pricing: if Founder sets minimum margin exception for Agricultural tier, exception must be recorded in Founder Action and in this profile with justification.
