# Agent Billing Profile — Digital Marketing Agent (DMA)

**Authority:** Chief Business Architect (INST-003) — GOAL-004 D-09
**Agent Spec:** architecture/reference/agents/digital-marketing-agent.md
**Bundle Definitions:** architecture/reference/billing/dma-bundle-definitions.md
**Constitutional Basis:** C-088 (Agent Billing Profile Requirement)
**Status:** FOUNDER_AUTHORIZED — 2026-07-30
**WBE Registry ID:** `dma_v3` (institutional.billing_profiles.agent_type)

---

## Thread Profile

### Platform Threads (inherited)
- `llm_local` — message classification gate (all messages)
- `llm_mid_gemini` — advisory responses, content generation, campaign suggestions
- `llm_frontier_gemini` — strategic cognition, complex campaign planning (Runner/Winner)
- `whatsapp_window` — all customer interactions via WhatsApp
- `infra_share` — platform infrastructure amortisation

### Agent-Specific Threads
- `video_kling_clip` — social media Reels generation (Runner/Winner)
- `video_heygen_minute` — avatar video (Winner only)
- `voice_elevenlabs_monthly` — voice narration (Winner only, plan subscription)
- `image_gen_per_image` — graphics, thumbnails, ad creatives
- `ad_spend_meta` — pass-through (customer's money, not WAOOAW cost)
- `ad_spend_google` — pass-through (customer's money, not WAOOAW cost)

## Bundle Rations
See: architecture/reference/billing/dma-bundle-definitions.md §2

## Minimum Wallet Requirements Per Active Skill
- Skill 11 (Paid Advertising): Ad spend wallet ≥ ₹2,000 (Starter), ₹3,000 (Runner), ₹5,000 (Winner)
- All other skills: no minimum ad wallet required

## Trial Profile (Zero-Cost Substitutions)
See: architecture/reference/billing/dma-bundle-definitions.md §6

## Constitutional Billing Obligations Specific to DMA
- C-056 (Ad Spend Transparency): ad spend wallet is strictly segregated; pass-through purity enforced
- C-043 (Financial Spend Ceiling): CE.ValidateAction called before every campaign action
- Management fee (10% of gross ad spend): revenue item, disclosed at Skill 11 activation
- WhatsApp as primary billing communication channel (customer WhatsApp = billing contact)
