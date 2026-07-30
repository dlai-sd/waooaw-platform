# Agent Billing Profile — Trading Professional

**Authority:** Chief Business Architect (INST-003) — GOAL-004 D-09
**Agent Spec:** architecture/reference/agents/trading-agent.md
**Constitutional Basis:** C-088 (Agent Billing Profile Requirement)
**Status:** FOUNDER_AUTHORIZED — 2026-07-30
**WBE Registry ID:** `trading_v1` (institutional.billing_profiles.agent_type)

---

## Thread Profile

### Platform Threads (inherited)
- `llm_local` — message classification, emergency keyword detection
- `llm_mid_gemini` — daily portfolio summaries, routine advisory, market commentary
- `llm_frontier_gemini` — F&O strategy sessions, complex multi-leg analysis (BREAKING decisions)
- `whatsapp_window` — all customer interactions
- `infra_share` — platform infrastructure

### Agent-Specific Threads
- `market_data_zerodha` — Zerodha Kite Connect subscription (amortised across trading customers)
- `market_data_zerodha_call` — per API call (live quotes, order status, holdings)
- `charting_per_chart` — chart rendering for trade setups

## Default Bundle Rations (not yet implemented — DMA is the MVP1 agent)

| Resource | thread_id | Starter (F&O Basic) | Runner (F&O Professional) | Winner (F&O + Crypto) |
|---|---|---|---|---|
| LOCAL classification | `llm_local` | Unlimited | Unlimited | Unlimited |
| MID_TIER LLM calls | `llm_mid_gemini` | 60 | 150 | 300 |
| FRONTIER LLM calls | `llm_frontier_gemini` | 10 | 25 | 50 |
| Zerodha API calls | `market_data_zerodha_call` | 1,000 | 5,000 | Unlimited |
| Chart renders | `charting_per_chart` | 20 | 60 | 200 |
| WhatsApp windows | `whatsapp_window` | 22 | 44 | 90 |
| Infrastructure share | `infra_share` | ₹180/month | ₹180/month | ₹180/month |

*Note: Trading bundles include Zerodha subscription cost. This is amortised across all Trading customers. At 5 customers: ₹440/customer/month. At 20 customers: ₹110/customer/month. Bundle pricing must be reviewed at each customer milestone.*

## Minimum Wallet Requirements Per Active Skill
- No ad spend wallet required (Trading agent does not manage paid advertising)
- Zerodha subscription included in bundle — no separate wallet needed

## Trial Profile (Zero-Cost Substitutions)
- `llm_mid_gemini` → Ollama llama3.2-3b: "Here's a sample market summary..."
- `llm_frontier_gemini` → Ollama llama3.2-3b: "Sample F&O analysis for demonstration..."
- `market_data_zerodha_call` → Simulated/delayed market data (BSE free data, 15-min delay)
- `charting_per_chart` → Pre-generated sample charts for common setups

## Constitutional Billing Obligations Specific to Trading
- C-043 (Financial Spend Ceiling): daily loss limit is a constitutional floor — enforced by CE.ValidateAction before every trade-related action
- TRADING/EXECUTION/ESCALATION_DECISION: BREAKING boundary — requires Founder acknowledgment (FA-005) before any trade execution feature is billed or implemented
- Session-based billing: subscription is monthly flat — does NOT bill per session or per trade (C-038 pro-rata for pause/resume only)
- Zerodha daily token: customer re-authenticates daily at 7 PM IST (ADR-025). If auth fails, agent discloses per C-049; no billing credit for missed sessions (open question — Founder decision)
