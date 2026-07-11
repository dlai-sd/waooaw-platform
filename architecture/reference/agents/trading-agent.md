# Autonomous Trading Professional — FO & Crypto

**Specification version:** 1.5
**Date:** 2026-07-11 (v1.5 — Token Economy Layer: Section 4.16, UsageUnits, minimum_model_tier, C-051)
**Change:** C-050 Strategic Cognition Layer added. Pre-session market regime assessment (SESSION_PREP) and monthly portfolio health assessment (MONTHLY_PORTFOLIO_ASSESSMENT) prompts added.
**Approved by Founder:** 2026-07-08 (v1.1); v1.4 pending Founder acknowledgment (BREAKING prompt before implementation sprint)
**Constitutional Basis:** C-036 (Skills), C-037 (Business KPIs), C-038 (Billing), C-039 (Conversational config), C-040 (Domain specialization), C-041 (Tool authorization), C-043 (Financial Spend Authority Ceiling — the daily loss limit is a Constitutional Floor equivalent; same enforcement mechanism as paid advertising budget cap), ADR-019 (RAG), ADR-020 (MCP), ADR-018 (Emergency Stop Temporal signal)
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

### Skill 1: Market & Technical Analysis

**Skill type:** `MARKET_TECHNICAL_ANALYSIS`
**Business KPI:** Signal quality score — % of analysis-driven setups that produce trades within the customer's expected risk/reward range
**Execution model:** PRE_AUTHORIZED (analysis runs continuously; no per-analysis approval needed)

**Decision Space:**
- **Authorized:** Read market data (OHLCV candles, live prices, OI, Greeks, IV); compute technical indicators (RSI, MACD, Bollinger Bands, ATR, VWAP, EMA/SMA); identify chart patterns (support/resistance, trend lines, head and shoulders, double tops, flags, wedges); assess candlestick patterns; calculate volatility signals (India VIX, HV/IV ratio); generate trade proposals with entry/exit/stop-loss targets; assess risk/reward per setup
- **Prohibited:** Place any order — this skill is analysis only; publish signals externally; access brokerage account without active PAAS session
- **Always-ask:** Switching the active strategy type entirely (e.g., directional → volatility); introducing a new technical indicator not in the configured set

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | NSE/BSE F&O market microstructure, NIFTY/BANKNIFTY seasonal and expiry-week patterns | Strategy timing and context |
| 1 — Domain | India volatility regime classification (India VIX levels, HV/IV ratios) | Strategy selection per regime |
| 1 — Domain | Chart pattern performance data for Indian F&O (historical success rate of specific patterns on NIFTY/BANKNIFTY) | Pattern-based setup confidence |
| 1 — Domain | Technical indicator calibration for India F&O (optimal RSI periods, MACD settings for intraday vs positional) | Indicator parameter selection |
| 1 — Domain | SEBI regulations on derivative trading (margin rules, lot sizes, expiry) | Compliance validation of trade proposals |
| 2 — Customer | Customer's strategy preferences (directional, volatility-based, or hybrid), risk tolerance | Personalized signal generation |
| 2 — Customer | Historical trade performance (which setups worked, entry/exit quality) | Strategy refinement |
| 3 — Platform | Cross-customer alpha patterns in Indian F&O (anonymised aggregate) | Edge identification |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read live prices | market-data-mcp | market.get_price_feed | Always authorized (read-only) | REQUIRED — no analysis without data |
| Read OHLCV candles | market-data-mcp | market.get_ohlcv | Always authorized (read-only) | REQUIRED — chart analysis needs candle data |
| Read options chain | market-data-mcp | market.get_options_chain | Always authorized (read-only) | REQUIRED |
| Read OI / Greeks | market-data-mcp | market.get_oi_greeks | Always authorized (read-only) | DEGRADABLE |
| Read India VIX | market-data-mcp | market.get_vix | Always authorized (read-only) | DEGRADABLE |

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
- **The agent's analysis and execution are NOT investment advice (SEBI regulatory boundary). The customer is the decision-maker in setting the Decision Space. The agent executes within that space — it does not advise beyond it.**

**R012-01 fix — Broker API Authorization (always-ask):**

Before the first trade execution in any session, the agent must verify broker API access is configured with execution permissions. This creates a constitutional evidence record.

`BROKER_API_ACCESS_VERIFIED` — always-ask action:
- Agent verifies `orders:write` permission on the API key
- Agent confirms customer has enabled API trading in broker dashboard
- Creates evidence record: action_type=BROKER_API_VERIFIED, constitutional_basis="C-041; C-003"
- If verification fails → session cannot start; agent records BLOCKED state and alerts customer
- If API key expires mid-session → agent halts execution gracefully, records SESSION_INTERRUPTED

---

### Skill 3: Risk Management

**Skill type:** `RISK_MANAGEMENT`
**Business KPI:** Maximum drawdown (target: within customer's stated tolerance); portfolio heat
**Execution model:** PRE_AUTHORIZED (risk monitoring runs continuously alongside execution)

**Decision Space:**
- **Authorized:** Monitor open positions for stop-loss breach; calculate portfolio delta/vega/theta; trigger stop-loss orders (within Skill 2 authorization); calculate daily P&L; generate risk alerts; execute session-end position closure if authorized
- **Prohibited:** Override a customer's stated stop-loss; hold positions beyond the approved session window; ignore a daily loss limit breach
- **Always-ask:** Adjusting stop-loss levels mid-session; `SESSION_END_POSITION_CLOSURE` — customer decides at onboarding: auto-close all positions at 3:00 PM or receive alert to close manually. This is a constitutional decision recorded in evidence.

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

## 4.14 Skill Runtime Configuration Standard

> This section defines the operating model for every skill in this agent. The Trading Agent's PAAS execution model means the approval-mode ladder (CUSTOMER_APPROVAL → SYNTHETIC_APPROVAL) from the DMA pattern **does not apply** — the customer pre-authorizes at session configuration, not action-by-action. All deviations from the general standard are explicitly noted.

---

### 4.14.1 Approval Model — PAAS Distinction

The Trading Agent uses **PRE_AUTHORIZED (PAAS)** execution. This is constitutionally distinct from APPROVAL_GATE agents.

| Concept | APPROVAL_GATE agents (DMA) | PRE_AUTHORIZED PAAS (Trading) |
|---|---|---|
| Approval point | Every action, at execution time | Once, at session configuration (onboarding) |
| Escalation trigger | Customer must approve before each action | Decision Space Reasoner returns UNCERTAIN |
| Synthetic Approval | Eligible (C-044 applies) | **N/A** — PAAS replaces this model |
| Auto-downgrade | On 10% override rate | N/A — PAAS paused on any escalation |

**For all Skills:** `approval_mode = PAAS_PRE_AUTHORIZED`. Synthetic approval confidence threshold: **N/A**.

The only post-hoc escalation path is the `TRADING/EXECUTION/ESCALATION_DECISION` prompt, invoked when CE.ValidateAction returns UNCERTAIN. This pauses the PAAS session and routes to the customer.

---

### 4.14.2 Skill Operating Cadence

The Trading Agent operates within a **market-day session boundary** (NSE trading days, 9:20–15:00 IST). Outside session windows, all execution skills are inactive.

| Skill | Heartbeat / Cadence | Trigger type |
|---|---|---|
| Skill 1 — Market Analysis | Every 5 minutes during session window | **SCHEDULED** — cron within session |
| Skill 2 — Trade Execution | On Skill 1 `TRADE_SETUP_IDENTIFIED` event | **EVENT_DRIVEN** |
| Skill 3 — Risk Management | Every 60 seconds during active session | **SCHEDULED** — continuous monitoring |
| Skill 4 — Crypto Management | Daily at 15:30 IST; DCA per customer schedule | **SCHEDULED** |
| Skill 5 — Performance Analytics | Session-end (15:05 IST); monthly on Day 1 | **EVENT_DRIVEN** (session close) + **SCHEDULED** (monthly) |

**Session start trigger:** PAASSessionWorkflow wakes at 9:20 IST on NSE trading days. Pre-session bootstrap runs: (1) verify broker API connectivity via `BROKER_API_ACCESS_VERIFIED`, (2) load Decision Space parameters, (3) perform first CE.ValidateAction health check. Any failure halts session before first trade.

---

### 4.14.3 Performance Narrative — Delivery Standard

| Narrative | Cadence | Channels | Format |
|---|---|---|---|
| Session Report | End of every trading session (15:05 IST) | WhatsApp push + Portal | 2-3 sentence WhatsApp summary + full portal report |
| Monthly Review | Day 1 of each month | WhatsApp push + Portal + optional email | Sharpe, drawdown, win-rate vs targets; escalation if 2+ miss months |

No daily narrative beyond session report — the session report IS the daily record.

---

### 4.14.4 Self-Governance and Goal Miss Escalation

```
Continuous (every Risk Management heartbeat):
  Monitor daily loss limit utilization.
  At 80% utilization → send WARN_AND_CONTINUE customer notification.
  At 100% utilization → HALT_TRADING immediately (constitutional floor — C-043).

Monthly (Day 1 — Skill 5):
  Evaluate: Sharpe ratio vs target, max drawdown vs tolerance, win rate trend.
  If 2 consecutive months below stated risk-adjusted return target:
    → Prepare escalation report:
       (a) What strategies were deployed (with evidence)
       (b) Market conditions diagnosis (what limited performance)
       (c) 2-3 parameter adjustment options with recommendation
    → Customer selects adjustment; new Decision Space amendment recorded in CAL
    → Clock resets

C-049 self-governance check:
  Monthly escalation report MUST include c049_honest_assessment:
    "Given my current Decision Space, market conditions, and customer capital,
     can I deliver the customer's stated return target? If not, I must say so."
  Valid recommended_option: STOP_AND_DISCLOSE
  — Agent must be willing to recommend pausing or terminating if genuinely unable
     to serve the customer's stated goal within the constitutional parameters.
```

---

### 4.14.5 Billing Control — API Budget per Skill per Month

| Skill | LLM calls/month | External API calls/month | Notes |
|---|---|---|---|
| Skill 1 — Market Analysis | ~250 | ~1,500 | 50 sessions/month × 5 analysis calls/session |
| Skill 2 — Trade Execution | ~30 | ~500 | Execution is mechanical; LLM for escalation only |
| Skill 3 — Risk Management | ~30 | ~3,000 | Continuous monitoring; LLM only on threshold trigger |
| Skill 4 — Crypto Management | ~20 | ~200 | Daily rebalance check + DCA |
| Skill 5 — Performance Analytics | ~60 | ~100 | Session reports (daily) + monthly review |
| Onboarding (one-time) | ~10 | ~5 | 5-phase conversation at session setup |
| **Total** | **~400/month** | **~5,305/month** | |

**Graceful reduction at 80% budget:** Skip additional analysis passes (extra Skill 1 cycles beyond the core 5-minute heartbeat). Core execution (Skill 2), risk monitoring (Skill 3), and session report (Skill 5) are never skipped.

---

### 4.14.6 Runtime Override Table (per-skill deviations)

| Skill | `approval_mode` | `synthetic_approval` | `goal_miss_escalation_months` | `delivery_channels` | `monthly_llm_budget` |
|---|---|---|---|---|---|
| Skill 1 — Market Analysis | PAAS_PRE_AUTHORIZED | N/A | N/A | Portal only (analysis internal) | ~250 |
| Skill 2 — Trade Execution | PAAS_PRE_AUTHORIZED | N/A | N/A | WhatsApp push (on escalation only) | ~30 |
| Skill 3 — Risk Management | PAAS_PRE_AUTHORIZED | N/A | 1 (daily loss = immediate escalation) | WhatsApp push (critical alerts) | ~30 |
| Skill 4 — Crypto Management | PAAS_PRE_AUTHORIZED | N/A | 2 | Portal + WhatsApp | ~20 |
| Skill 5 — Performance Analytics | PAAS_PRE_AUTHORIZED | N/A | 2 | WhatsApp push + Portal + Email (optional) | ~60 |

---

## 4.15 Strategic Cognition Standard

> **Constitutional basis:** C-050 (Strategic Cognition Obligation — LAW), AD-021 (Strategic Cognition Trigger Points), DP-019 (Portfolio-First Cognition)

The Trading Agent operates with a fixed, pre-configured strategy (PAAS). Strategic cognition takes a distinct form: the agent does not choose which skills to activate mid-session (the Decision Space is the strategy). Instead, strategic cognition operates at two points: (1) pre-session preparation — is today's market regime still aligned with the customer's configured strategy? (2) monthly portfolio review — is the overall trading approach achieving the customer's risk-adjusted return goal?

---

### 4.15.1 Planning Mode — SESSION_PREP

**Prompt:** `TRADING/STRATEGIC/SESSION_PREP`

**Trigger:** Pre-session at 9:15 IST (5 minutes before session window opens)

**What the agent reasons about:**
- Is today's market regime (VIX level, overnight global developments) broadly aligned with the customer's configured strategy type (DIRECTIONAL vs VOLATILITY)?
- Are there any events today (expiry, RBI announcement, earnings) that materially change the risk profile of executing the current strategy?
- Based on yesterday's session outcome: is there any reason to be more conservative today (e.g., near daily loss limit, portfolio heat)?
- If the regime is fundamentally misaligned: SESSION_DEFERRED — agent does not trade today, alerts customer
- C-048: this assessment must not find reasons to trade when the evidence suggests not trading

**Output:** Session proceed/defer decision + risk posture for today's session (conservative/normal/aggressive within Decision Space)

---

### 4.15.2 Assessment Mode — MONTHLY_PORTFOLIO_ASSESSMENT

**Prompt:** `TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT`

**Triggers:**
- **PERIODIC_REVIEW:** Monthly Day 1 (feeds into Skill 5 monthly report)
- **DEVIATION_ALERT:** If monthly P&L < 0 for 2 consecutive months (triggers alongside `TRADING/SELF_GOVERNANCE/DIAGNOSIS`)

**What the agent reasons about:**
- Is the configured strategy (DIRECTIONAL / VOLATILITY / HYBRID) still appropriate for the current market regime that has prevailed over the past month?
- Is the daily loss limit calibrated correctly? (Too tight → too many stopped sessions; too loose → excessive risk)
- Win rate and R/R analysis: is the edge real or has it degraded?
- C-049: can I honestly deliver this customer's return target with this strategy in this market?

---

### 4.15.3 Professional Template Declaration

```yaml
strategic_cognition:
  skill_activation_plan_prompt: "TRADING/STRATEGIC/SESSION_PREP"
  performance_assessment_prompt: "TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT"
  trigger_events:
    - type: "POST_ONBOARDING"
      condition: "broker_api_access_verified == true AND decision_space_configured == true"
      prompt: "SESSION_PREP"  # First session prep after onboarding
    - type: "PRE_SESSION"
      condition: "daily 09:15 IST on NSE_TRADING_DAYS"
      prompt: "SESSION_PREP"
    - type: "PERIODIC_REVIEW"
      condition: "monthly_day_1"
      prompt: "MONTHLY_PORTFOLIO_ASSESSMENT"
    - type: "DEVIATION_ALERT"
      condition: "consecutive_losing_months >= 2"
      prompt: "MONTHLY_PORTFOLIO_ASSESSMENT"
  strategic_state_table: "business.agent_strategic_state"
```

---

## 4.16 Token Economy Standard

> **Constitutional basis:** C-051, AD-022, AD-023, DP-020, ADR-024

**Usage Units — Trading** (monitoring-focused; no hard creative limits):

| Unit Type | Label | Token equiv | Monthly | Rollover | Emergency exempt |
|---|---|---|---|---|---|
| `SESSION_EXECUTED` | Trading Sessions | 0 tokens (pre-computed) | Unlimited within session window | N/A | No |
| `SESSION_DEFERRED` | Deferred Sessions | 0 | Tracked only | N/A | No |
| `STRATEGY_REVIEW` | Monthly Reviews | ~3,000 tokens | 1 (monthly, Day 1) | No | No |
| `ESCALATION_DECISION` | Escalation consults | ~2,000 tokens | As needed | N/A | **Yes** (C-001) |

Trading agent does not have hard UsageUnit limits — it operates within a PAAS session budget. Monitoring tracks: sessions deferred vs executed (ratio is quality signal), monthly strategy review consumption, escalation frequency (high escalation = strategy misconfiguration signal).

**Message classification categories (portal):**
- `APPROVAL_ACTION`: session config changes confirmed — ₹0 (evidence record only)
- `STATUS_QUERY`: P&L dashboard, session history — ₹0 (DB read)
- `STRATEGY_CONVERSATION`: discuss parameter changes — MID_TIER
- `ESCALATION_RESPONSE`: customer responding to UNCERTAIN pause — FRONTIER (constitutional)
- Estimated zero-cost rate: ~40%

**Budget communication:** Trading customers are professional users. Portal shows:
- Sessions this month: executed / deferred ratio
- Monthly strategy review: used / available
- Monthly P&L vs target (always visible)
- No WhatsApp budget alerts (professional portal interface)

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
  skill_runtime_defaults:
    approval_mode: "PAAS_PRE_AUTHORIZED"
    synthetic_approval_confidence_threshold: "N/A"  # PAAS model — not applicable
    synthetic_approval_min_history: "N/A"
    goal_miss_escalation_months: 2
    delivery_channels: ["WHATSAPP_PUSH", "PORTAL"]
    api_budget:
      market_analysis_llm_calls_per_month: 250
      trade_execution_llm_calls_per_month: 30
      risk_management_llm_calls_per_month: 30
      crypto_management_llm_calls_per_month: 20
      performance_analytics_llm_calls_per_month: 60
      graceful_reduction_threshold: 0.80
  execution_loop:
    pattern: "REASONING_FIRST"  # C-047 — agent reasons before code executes
    session_start_trigger:
      type: "SCHEDULED"
      schedule: "09:20 IST on NSE_TRADING_DAYS"
      pre_session_checks:
        - "BROKER_API_ACCESS_VERIFIED"
        - "DECISION_SPACE_LOADED"
        - "CE_HEALTH_CHECK"
    heartbeat_schedule:
      skill_1_market_analysis: "every_5_minutes_during_session"
      skill_2_trade_execution: "EVENT_DRIVEN (TRADE_SETUP_IDENTIFIED)"
      skill_3_risk_management: "every_60_seconds_during_session"
      skill_4_crypto: "daily_15:30_IST"
      skill_5_performance: "EVENT_DRIVEN (session_close) + monthly_day_1"
    session_end_trigger: "15:05 IST or DAILY_LOSS_LIMIT_REACHED or EMERGENCY_STOP"
    self_governance:
      mid_session_loss_check: "every_risk_heartbeat"
      monthly_performance_review_day: 1
      consecutive_miss_escalation_threshold: 2
      c049_honest_assessment_required: true
  strategic_cognition:
    skill_activation_plan_prompt: "TRADING/STRATEGIC/SESSION_PREP"
    performance_assessment_prompt: "TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT"
    trigger_events:
      - type: "PRE_SESSION"
        condition: "daily 09:15 IST on NSE_TRADING_DAYS"
        prompt: "SESSION_PREP"
      - type: "PERIODIC_REVIEW"
        condition: "monthly_day_1"
        prompt: "MONTHLY_PORTFOLIO_ASSESSMENT"
      - type: "DEVIATION_ALERT"
        condition: "consecutive_losing_months >= 2"
        prompt: "MONTHLY_PORTFOLIO_ASSESSMENT"
    strategic_state_table: "business.agent_strategic_state"
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

## 8b. Billing & Subscription Model (ADR-022, C-038)

### Subscription Tiers

| Tier | Instruments | Customer pays | Base (excl. GST) | GST 18% | Razorpay Plan |
|---|---|---|---|---|---|
| **F&O Professional** | NIFTY + BANKNIFTY options | ₹1,999/month | ₹1,694 | ₹305 | `plan_trading_fo_only` |
| **F&O + Crypto Professional** | NIFTY + BANKNIFTY + BTC/ETH | ₹2,499/month | ₹2,119 | ₹380 | `plan_trading_fo_crypto` |

**No performance fee** — constitutional rationale: a performance component would incentivise the agent to trade more aggressively to maximise fee, creating tension with the daily loss limit (C-043 Constitutional Floor). Fixed monthly subscription is the only model consistent with C-043.

### Billing Lifecycle (C-038 pro-rata)

- **Session-based billing:** The subscription is monthly and flat — it does NOT bill per session or per trade. The customer pays the same whether they run 5 sessions or 20 sessions in the month.
- **Pause:** Customer pauses agent → billing stops pro-rata from pause timestamp. In-flight PAAS session is halted (Emergency Stop semantics — ADR-018). Open positions remain open (customer manages manually after halt).
- **Resume:** Billing resumes pro-rata from resume timestamp. Agent re-verifies broker API credentials before next session (BROKER_API_ACCESS_VERIFIED).
- **Tier upgrade (F&O → F&O+Crypto):** Razorpay subscription plan updated; pro-rated price difference charged/credited for remaining days in billing cycle.

### Professional Template — Billing Section

```yaml
billing:
  subscription_tiers:
    - tier_id: "TRADING_FO_ONLY"
      name: "F&O Professional"
      instruments: [NIFTY, BANKNIFTY]
      monthly_price_inr_paise: 199900
      base_amount_paise: 169407
      gst_amount_paise: 30493
      razorpay_plan_id: "plan_trading_fo_only"
    - tier_id: "TRADING_FO_CRYPTO"
      name: "F&O + Crypto Professional"
      instruments: [NIFTY, BANKNIFTY, CRYPTO_BTC, CRYPTO_ETH]
      monthly_price_inr_paise: 249900
      base_amount_paise: 211864
      gst_amount_paise: 38036
      razorpay_plan_id: "plan_trading_fo_crypto"
  gst_sac_code: "9984"
  performance_fee: false      # constitutional — C-043 conflict prohibited
  billing_model: "FLAT_MONTHLY"
```

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
- [x] Customer warned that Emergency Stop does not auto-close overnight positions
- [x] **R012-01 applied: BROKER_API_ACCESS_VERIFIED evidence record before any order placement**
- [x] **Regulatory disclaimer in constitutional constraints (not investment advice — SEBI)**
- [x] **SESSION_END_POSITION_CLOSURE as always-ask — customer decides at onboarding**
- [x] **C-048 check (Information Non-Exploitation): No Skill steers the customer toward higher-tier plans or more aggressive strategies for WAOOAW platform benefit. The agent executes within the customer's stated parameters — it does not optimise for trade frequency, fee generation, or platform metrics. C-043 daily loss limit is a hard stop regardless of any other consideration.**
- [x] **C-049 check (Honest Limitation Disclosure): `TRADING/SELF_GOVERNANCE/DIAGNOSIS` prompt (Skill 5 monthly evaluation) includes `c049_honest_assessment: CAN_DELIVER_WITH_CORRECTIONS | CANNOT_DELIVER_MUST_DISCLOSE` field. If market conditions, capital constraints, or SEBI regulations make the customer's stated return target unachievable, the agent must say so explicitly. `STOP_AND_DISCLOSE` is a valid `recommended_option`. R017-01 fix applied.**
- [x] **C-050 check (Strategic Cognition): Section 4.15 added. TRADING/STRATEGIC/SESSION_PREP invoked at 9:15 IST pre-session to assess market regime alignment and session risk posture; TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT invoked monthly and on consecutive losses. Both prompts include strategic_reasoning_chain, portfolio_health (for monthly), session_proceed_decision (for daily), and c049_honest_assessment. Professional Template declares strategic_cognition block with 3 trigger events.**
- [x] **C-051 check (Resource Transparency): Section 4.16 added. Trading agent uses monitoring-based UsageUnits (sessions executed/deferred, monthly reviews). minimum_model_tier declared for all prompts. ESCALATION_DECISION path emergency-exempt (C-001). TRADING/TOKEN_ECONOMY/USAGE_SUMMARY prompt added.**

---

## 11. Prompt Catalogue

> **Gate requirement (Sections 2 + 10 of Activation Gate, C-045, C-050, AD-018, AD-021):** Every LLM inference point must have an approved prompt. All prompts reside in `architecture/reference/prompts/trading-agri-agent-prompts.md` and are seeded in `institutional.agent_prompt_versions`.

| Prompt ID | Layer | Step | Type | `minimum_model_tier` |
|---|---|---|---|---|
| `TRADING/ONBOARDING/PROFILE_SETUP` | Onboarding | 5-phase config conversation → Decision Space | BEHAVIOURAL | `FRONTIER` |
| `TRADING/STRATEGIC/SESSION_PREP` | Strategic Cognition | Pre-session: market regime alignment + session risk posture | BEHAVIOURAL | `MID_TIER` |
| `TRADING/MARKET_ANALYSIS/TRADE_SETUP` | Skill 1 | Trade setup identification from market data | BEHAVIOURAL | `MID_TIER` |
| `TRADING/EXECUTION/ESCALATION_DECISION` | Skill 2 | PAAS escalation when DS Reasoner returns UNCERTAIN | BREAKING | `FRONTIER` |
| `TRADING/RISK_MANAGEMENT/LOSS_LIMIT_ALERT` | Skill 3 | Halt vs warn decision on risk threshold trigger | BREAKING | `FRONTIER` |
| `TRADING/CRYPTO/REBALANCE_DECISION` | Skill 4 | Crypto rebalancing and DCA decision | BEHAVIOURAL | `MID_TIER` |
| `TRADING/PERFORMANCE/SESSION_REPORT` | Skill 5 | End-of-session performance report generation | BEHAVIOURAL | `MID_TIER` |
| `TRADING/SELF_GOVERNANCE/DIAGNOSIS` | Self-Governance | C-049 honest assessment — goal miss diagnosis + STOP_AND_DISCLOSE | BEHAVIOURAL | `FRONTIER` |
| `TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT` | Strategic Cognition | Monthly: portfolio health + strategic recommendation (C-050) | BEHAVIOURAL | `FRONTIER` |
| `TRADING/TOKEN_ECONOMY/USAGE_SUMMARY` | Token Economy | Session/review usage for portal dashboard | USAGE_SUMMARY | `MID_TIER` |

**Section 10 gate check:** Both strategic cognition prompts catalogued and seeded in SQL. C-050 in checklist. Trigger events declared. Gate 10: PASS.
**Section 11 gate check:** Section 4.16 added. UsageUnits defined. minimum_model_tier declared for all 10 prompts. C-051 in checklist. Gate 11: PASS.**

---

## 12. Version History

| Version | Date | Author (Office) | Change |
|---|---|---|---|
| 1.0 | 2026-07-08 | Business Architect | Initial draft |
| 1.1 | 2026-07-08 | Business Architect | R-012 P0 fixes: Technical Chart Analysis (Skill 1 expanded), BROKER_API_ACCESS_VERIFIED always-ask, SESSION_END_POSITION_CLOSURE always-ask |
| 1.2 | 2026-07-11 | Business Architect | Track A P1 fix: Section 4.14 Skill Runtime Configuration Standard; Prompt Catalogue (Section 11); execution_loop + heartbeat_schedule in Professional Template; C-048 + C-049 constitutional checks |
| 1.3 | 2026-07-11 | Business Architect | R017-01 P1 fix: TRADING/SELF_GOVERNANCE/DIAGNOSIS prompt; C-049 checklist updated |
| 1.4 | 2026-07-11 | Business Architect | Strategic Cognition Layer (C-050): Section 4.15; SESSION_PREP + MONTHLY_PORTFOLIO_ASSESSMENT prompts; strategic_cognition block in Professional Template; C-050 constitutional check |
| 1.5 | 2026-07-11 | Business Architect | Token Economy Layer (C-051): Section 4.16; UsageUnits; minimum_model_tier per prompt; TRADING/TOKEN_ECONOMY/USAGE_SUMMARY; C-051 check |

---

## 10. Review and Approval

**EA Review:** R-012 — APPROVED (v1.0/v1.1)
**EA Review:** R-017 — APPROVED (v1.3 Track A gate compliance)
**EA Review:** R-018 — APPROVED (v1.4 Strategic Cognition Layer)
**Founder Approval:** GRANTED — 2026-07-08 (per GENESIS Part 05)
**Status:** APPROVED — v1.4 active (pending Founder acknowledgment of TRADING/EXECUTION/ESCALATION_DECISION BREAKING prompt before implementation sprint)
