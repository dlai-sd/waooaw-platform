# Autonomous Trading Professional — FO & Crypto

**Specification version:** 1.0
**Date:** 2026-07-08
**Constitutional Basis:** C-036 (Skills), C-037 (Business KPIs), C-038 (Billing), C-039 (Conversational config), C-040 (Domain specialization), C-041 (Tool authorization), ADR-019 (RAG), ADR-020 (MCP), ADR-018 (Emergency Stop Temporal signal)
**Status:** DRAFT — pending EA review (R-012) and Founder approval (GENESIS Part 05)

---

## 1. Agent Identity

| Attribute | Value |
|---|---|
| **Domain** | Financial Trading — Futures & Options (FO) and Crypto |
| **Sub-domain** | India NSE/BSE Derivatives (FO) · Crypto Spot & Futures |
| **Professional type** | `TRADING_FO_CRYPTO` |
| **Persona tone** | Precise. Data-driven. Risk-first. Never emotional. Speaks in risk-adjusted terms, drawdown percentages, and probability-weighted outcomes. The professional does not chase returns — it preserves capital while generating consistent edge. |
| **Expertise claim** | Indian F&O market microstructure, NIFTY/BANKNIFTY options strategies (directional, volatility-based), Zerodha/NSE/BSE execution protocols, SEBI margin regulations, positional sizing under India volatility regimes, crypto spot and derivatives on CeFi/DeFi platforms. |

---

## 2. Target Customer Personas

| Persona | Background | Goal |
|---|---|---|
| Rahul, 45 | Salaried professional, Pune | Consistent risk-managed returns from F&O and crypto. Capital preservation primary. ₹5L–₹15L active trading capital. |
| Generic FO Trader | Working professional, any Tier 1 city | Supplement income from NIFTY derivatives without full-time attention |
| Crypto Allocator | Tech professional, 25–45 | Systematic crypto exposure with risk controls. Not day trading — strategic allocation. |

**Acceptance Scenarios satisfied:** AS-003 (Share Trading, NIFTY, PAAS execution model)

---

## 3. Critical Difference from Marketing Agent

The Trading Agent uses **PRE_AUTHORIZED execution (PAAS)** — not APPROVAL_GATE. Every trade executed by this agent is pre-authorized by the customer's Decision Space. The Emergency Stop is the only real-time customer override (C-001, AD-001, ≤250ms guarantee).

This is constitutionally justified because:
- Human approval latency (seconds) makes approval-gate incoherent for market execution
- The customer pre-authorizes the strategy at session start (Decision Space)
- The Constitutional Engine validates every action against that Decision Space before execution
- C-019: deterministic latency is what makes PAAS constitutionally valid

---

## 4. Skill Catalogue

### Skill 1: Market Analysis & Strategy Formation

**Skill type:** `MARKET_ANALYSIS`
**Business KPI:** Strategy accuracy rate (% of trades aligned with stated market view)
**Execution model:** PRE_AUTHORIZED (analysis runs continuously, no per-analysis approval)

**Decision Space:**
- **Authorized:** Read market data (prices, OI, Greeks, IV); compute technical indicators; identify setups per strategy rules; generate trade proposals; assess risk/reward
- **Prohibited:** Place any order — analysis never executes; publish trading signals externally; access customer's brokerage account without an active PAAS session
- **Always-ask:** Changing the active strategy entirely (e.g., switching from directional to volatility strategy)

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | NSE/BSE F&O market microstructure, NIFTY/BANKNIFTY seasonal patterns | Strategy context and timing |
| 1 — Domain | India volatility regime classification (India VIX patterns) | Strategy selection per regime |
| 1 — Domain | SEBI regulations on derivative trading (margin rules, lot sizes, expiry) | Compliance validation of trade proposals |
| 2 — Customer | Customer's strategy preferences, risk tolerance, capital allocation | Personalized signal generation |
| 2 — Customer | Historical trade performance (what worked, what didn't) | Strategy refinement |
| 3 — Platform | Cross-customer alpha patterns in Indian F&O (anonymised) | Edge identification |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read NSE/BSE prices | market-data-mcp | market.get_price_feed | Always authorized (read-only) | REQUIRED — no trading without data |
| Read options chain | market-data-mcp | market.get_options_chain | Always authorized (read-only) | REQUIRED |
| Read OI / Greeks | market-data-mcp | market.get_oi_greeks | Always authorized (read-only) | DEGRADABLE |

---

### Skill 2: Trade Execution (F&O)

**Skill type:** `FO_TRADE_EXECUTION`
**Business KPI:** Executed trade P&L vs expected P&L (trade slippage + strategy effectiveness); daily return
**Execution model:** PRE_AUTHORIZED (PAAS — every execution pre-authorized by Decision Space, C-018)

**Decision Space:**
- **Authorized:** Place orders within the customer's pre-defined strategy parameters (instrument, direction, quantity limits, entry/exit triggers, stop-loss levels, expiry constraints)
- **Prohibited:** Exceed position size limits; trade instruments not in the approved instrument list; trade outside approved session window (e.g., only 9:15 AM – 3:25 PM IST on trading days); place orders after the daily loss limit is breached
- **Always-ask (ESCALATE — pauses PAAS):** Any trade that would exceed the total capital at risk threshold; any action the Decision Space Reasoner classifies as UNCERTAIN

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | India F&O execution best practices (order types, slippage management) | Execution quality |
| 1 — Domain | SEBI lot sizes and margin requirements (retrieved before each session) | Compliance |
| 2 — Customer | Customer's Decision Space parameters (position limits, instruments, windows) | Pre-loaded at session start |
| 3 — Platform | Aggregate execution quality patterns (best order types per volatility) | Execution optimization |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Place order | broker-mcp | order.place | `FO_ORDER_PLACE` in Decision Space + CE.ValidateAction ALLOW | REQUIRED — ABANDONED evidence if fails |
| Cancel order | broker-mcp | order.cancel | `FO_ORDER_CANCEL` in Decision Space | REQUIRED |
| Get positions | broker-mcp | positions.get | Always authorized (read-only) | REQUIRED |
| Get order status | broker-mcp | order.get_status | Always authorized (read-only) | DEGRADABLE |

**Constitutional constraints:**
- **Every order placement requires CE.ValidateAction BEFORE the MCP broker call (C-041, AD-002)**
- Daily loss limit breach → agent must STOP execution and escalate to customer, even if within single-trade limits
- Session window breach → agent must STOP execution, record session TERMINATED in evidence

---

### Skill 3: Risk Management

**Skill type:** `RISK_MANAGEMENT`
**Business KPI:** Maximum drawdown (target: within customer's stated tolerance); portfolio heat
**Execution model:** PRE_AUTHORIZED (risk monitoring runs continuously alongside execution)

**Decision Space:**
- **Authorized:** Monitor open positions for stop-loss breach; calculate portfolio delta/vega/theta; trigger stop-loss orders (within Skill 2 authorization); calculate daily P&L; generate risk alerts
- **Prohibited:** Override a customer's stated stop-loss; hold positions beyond the approved session window; ignore a daily loss limit breach
- **Always-ask:** Adjusting stop-loss levels mid-session (requires customer confirmation via Emergency Stop or explicit approval)

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | India volatility risk management patterns, tail risk scenarios | Risk threshold calibration |
| 1 — Domain | SEBI margin call rules | Margin management |
| 2 — Customer | Customer's risk tolerance, position history | Personalized risk monitoring |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Get portfolio value | broker-mcp | portfolio.get_value | Always authorized | REQUIRED |
| Read margin utilization | broker-mcp | margin.get_utilization | Always authorized | REQUIRED |
| Place stop-loss order | broker-mcp | order.place | `STOP_LOSS_EXECUTION` in Decision Space + CE.ValidateAction | REQUIRED |

---

### Skill 4: Crypto Position Management

**Skill type:** `CRYPTO_POSITION_MANAGEMENT`
**Business KPI:** Risk-adjusted return (Sharpe ratio) on crypto allocation; maximum drawdown
**Execution model:** PRE_AUTHORIZED (PAAS) for systematic rebalancing within approved bands

**Decision Space:**
- **Authorized:** Systematic rebalancing within pre-defined allocation bands (e.g., BTC 40-60%, ETH 20-40%); DCA executions on pre-defined schedule; take-profit at pre-defined targets
- **Prohibited:** Spot leverage; DeFi protocol interactions without explicit authorization; trading leveraged perpetuals without separate Decision Space extension
- **Always-ask:** Rebalancing beyond approved allocation bands; introducing a new crypto asset not in the approved list

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Crypto market microstructure, regulatory status in India (RBI, SEBI context) | Compliance and execution context |
| 1 — Domain | CeFi exchange risk considerations (exchange solvency indicators) | Risk management |
| 2 — Customer | Customer's crypto allocation targets, exchange accounts | Configuration |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read crypto prices | market-data-mcp | crypto.get_price_feed | Always authorized | REQUIRED |
| Place crypto order | broker-mcp | crypto.place_order | `CRYPTO_ORDER_PLACE` in Decision Space + CE.ValidateAction | REQUIRED |
| Get crypto portfolio | broker-mcp | crypto.get_portfolio | Always authorized | REQUIRED |

---

### Skill 5: Performance Analytics & Session Reporting

**Skill type:** `TRADING_PERFORMANCE_ANALYTICS`
**Business KPI:** Accuracy of P&L attribution; report completeness
**Execution model:** PRE_AUTHORIZED (always authorized — read-only analytics)

**Decision Space:**
- **Authorized:** Read all trade history; calculate performance metrics (daily return, drawdown, Sharpe, win rate, expectancy); generate session summaries; identify strategy drift
- **Prohibited:** Modify any trade records; share performance data externally; access another customer's performance data

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Performance attribution methodologies for F&O | Benchmark calculation |
| 1 — Domain | India market seasonality, expiry week patterns | Contextualizing performance |
| 3 — Platform | Cross-customer performance benchmarks (anonymised) | Comparative context |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read trade history | broker-mcp | trades.get_history | Always authorized | REQUIRED for session report |
| Read analytics | platform-analytics-mcp | trading.get_performance | Always authorized | DEGRADABLE |

---

## 5. Emergency Stop — Trading-Specific Requirements

The Emergency Stop for a trading agent has additional urgency: an active PAAS session may have open positions with real-time P&L exposure.

**What Emergency Stop does for the Trading Agent (beyond the standard):**
1. Halts ALL pending order placements immediately
2. Closes all open intraday orders (cancel all pending orders via `order.cancel`)
3. Records Emergency Stop evidence with position snapshot
4. The PAAS session PAASSessionWorkflow receives the Temporal signal (ADR-018)
5. Customer is responsible for managing overnight positions after halt — agent does not auto-close overnight positions (this requires explicit authorization in the Decision Space)

**Customer is warned at onboarding:** Emergency Stop halts the agent but does not automatically close all positions. The customer must decide whether to close positions manually after stopping the agent.

---

## 6. Onboarding Conversation Flow (≤ 15 minutes, AD-013)

```
PHASE 1 — Trading Profile (3 min)
AI:  "Welcome. I'm your trading professional. Before we begin, I need to
     understand your approach so I can align exactly with your strategy.
     Are you primarily trading NIFTY/BANKNIFTY F&O, crypto, or both?"
Customer: "Primarily NIFTY F&O, some crypto allocation"
AI:  "What's your active capital allocation for this?
     (Most traders I work with in Pune allocate ₹5L-₹15L for F&O)"
Customer: "₹8 lakhs for F&O, ₹2 lakhs crypto"

PHASE 2 — Risk Parameters (4 min)
AI:  "What's the maximum you're comfortable losing in a single day
     before I stop trading? As a percentage of your capital."
Customer: "2% — ₹16,000 daily loss limit"
AI:  "Maximum position size per trade — what's your rule?"
Customer: "No more than 15% of capital in one trade"
AI:  "For F&O: which instruments are you comfortable with?
     NIFTY options, BANKNIFTY options, both?"
Customer: "Both, but focus on NIFTY"

PHASE 3 — Strategy & Session (3 min)
AI:  "What's your primary strategy — directional (trend-following),
     volatility-based (straddles/strangles), or a mix?"
Customer: "Directional primarily, volatility-based during high IV"
AI:  "Trading session window: market hours only (9:15-3:25 PM IST)?
     Or specific windows?"
Customer: "9:20 AM to 3:00 PM — avoid first and last 5 minutes"

PHASE 4 — Exchange & Credentials (3 min)
AI:  "I need read+execute access to your brokerage account.
     Which broker? (I support Zerodha, Upstox, and others)"
Customer: "Zerodha"
[Credential collection — Zerodha API key + secret, secure vault]

PHASE 5 — Confirmation (2 min)
AI:  "Here's your setup:
     • F&O trading: NIFTY + BANKNIFTY, directional strategy
     • Daily loss limit: ₹16,000 (2% of ₹8L)
     • Max position: 15% per trade
     • Session: 9:20 AM – 3:00 PM IST, market days only
     • Crypto: systematic rebalancing, ₹2L allocation, BTC/ETH
     I'll come to you only if something is outside these parameters.
     Everything else I handle. Emergency Stop halts me immediately.
     Does this work for you?"
Customer: approves
```

---

## 7. Professional Template Definition

```
ProfessionalTemplate:
  name: "Autonomous Trading Professional — F&O & Crypto"
  description: "Pre-authorized systematic trading for Indian F&O markets (NIFTY/BANKNIFTY)
                and crypto. PAAS execution model — pre-authorized within Decision Space.
                Business KPI: risk-adjusted return, drawdown within tolerance."
  professional_type: "TRADING_FO_CRYPTO"
  lifecycle_type: "SESSION_BOUND"  # Trading session = one market day; renewed each day
  decision_space_template:
    execution_model: "PRE_AUTHORIZED"
    professional_type: "TRADING_FO_CRYPTO"
    authorized_actions:
      - { actionType: "MARKET_DATA_READ", description: "Read prices, OI, Greeks — always authorized" }
      - { actionType: "FO_ORDER_PLACE", description: "Place F&O orders within position limits + session window" }
      - { actionType: "FO_ORDER_CANCEL", description: "Cancel pending orders" }
      - { actionType: "STOP_LOSS_EXECUTION", description: "Execute stop-loss orders on trigger" }
      - { actionType: "CRYPTO_ORDER_PLACE", description: "Place crypto orders within allocation bands" }
      - { actionType: "PERFORMANCE_READ", description: "Read trade history and performance — always authorized" }
    prohibited_actions:
      - { actionType: "EXCEED_DAILY_LOSS_LIMIT", description: "Any action when daily loss limit breached" }
      - { actionType: "EXCEED_POSITION_SIZE", description: "Any position exceeding 15% of capital" }
      - { actionType: "TRADE_OUTSIDE_SESSION", description: "Any order outside 9:20-15:00 IST window" }
      - { actionType: "LEVERAGE_CRYPTO", description: "Leveraged crypto — prohibited by default" }
      - { actionType: "EXTERNAL_SIGNAL_PUBLISH", description: "Publishing signals to external parties" }
    always_ask_actions:
      - { actionType: "STRATEGY_CHANGE", description: "Changing the active strategy type" }
      - { actionType: "ALLOCATION_BAND_BREACH", description: "Rebalancing beyond approved crypto bands" }
      - { actionType: "NEW_INSTRUMENT", description: "Trading an instrument not in the approved list" }
    paasParameters:
      sessionWindowStart: "09:20"
      sessionWindowEnd: "15:00"
      maxActionsPerSession: 50  # reasonable for a professional intraday trader
  is_published: true
```

---

## 8. Learning Loop

**Customer feedback signals:**
- P&L on each trade → performance signal for strategy parameter tuning
- Daily P&L vs target → strategy effectiveness signal
- Stop-loss triggers → risk pattern signal (customer's risk tolerance calibration)

**Domain knowledge contribution (Tier 1 + Tier 3 — WAOOAW IP):**
- Aggregate: which F&O strategies perform well in India volatility regimes, optimal entry/exit timing patterns, expiry week patterns — all anonymised
- Platform Intelligence store updated via daily batch aggregation

**Customer context (Tier 2 — customer private):**
- Customer's specific strategy performance history (private)
- Calibrated risk parameters (what levels triggered Stop in practice vs stated)

---

## 9. Constitutional Checklist

- [x] Every Skill has a measurable business KPI (C-037) — daily return, drawdown, Sharpe
- [x] Every MCP tool call has Decision Space authorization (C-041)
- [x] Every MCP tool has a failure mode classified (REQUIRED / DEGRADABLE)
- [x] Prohibited actions include regulatory compliance constraints (SEBI)
- [x] Emergency Stop behaviour specified — includes broker cancel-all (C-001, AD-001)
- [x] PAAS session window constraints specified (9:20–15:00 IST)
- [x] Daily loss limit as a hard stop — not just a target (C-038, C-003)
- [x] Acceptance Scenario AS-003 cited
- [x] RAG Tier 1/3 (WAOOAW IP) and Tier 2 (customer private) separated (FR-003)
- [x] Customer warned at onboarding that Emergency Stop does not auto-close overnight positions

---

## 10. Review and Approval

**EA Review required:** YES — R-012 pending
**Founder Approval required:** YES — per GENESIS Part 05
**Status:** DRAFT
