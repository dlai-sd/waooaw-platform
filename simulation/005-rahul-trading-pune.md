# Simulation 005 — Rahul's Trading Account, Pune

**Type:** Full Lifecycle Simulation — Trading Agent (PAAS Execution Model)
**Status:** Active
**Purpose:** Validate the Trading Agent lifecycle against a real customer journey. Surface gaps in the PAAS execution model, session management, billing, risk handling, and constitutional evidence chain for financial actions.
**Business:** Rahul Sharma, salaried IT professional, Pune. Trading capital: ₹8L F&O + ₹2L crypto.

---

## Phase 1 — Portal Discovery

Rahul finds WAOOAW via a finance YouTube channel sponsorship. He visits the portal and selects "I want systematic trading without watching screens all day."

### [GAP-T001] Trading Agent Has No Portal Discovery Path

The portal's "What's your biggest challenge?" map covers digital marketing needs. There is no equivalent for trading customers. The business_domain_taxonomy has no trading domain, and there's no portal sales presentation layer for the trading agent.

**Gap:** Trading agent has no Section 6 (Portal Customer-Facing Presentation) equivalent. The DMA agent has a complete portal layer; the trading agent does not.

**Layer:** trading-agent.md (missing portal section); business_domain_taxonomy (missing TRADER entry).

---

## Phase 2 — Registration and Onboarding

Rahul registers. The 6 mandatory fields don't fit well:
- "Prospective customers" — doesn't apply to trading
- "Aspiration" — "consistent monthly returns from F&O"

The onboarding conversation is a 5-phase flow (Section 6 of spec). This works well.

### [GAP-T002] No Trading Profile Skill (Skill 0 Equivalent)

The DMA agent has Skill 0 (Customer Profiling) that produces a structured profile document and triggers Market Research. The trading agent has only an onboarding conversation. There is no:
- `trading_profiles` table in the data architecture
- `customer-profile-mcp` equivalent for trading
- Structured profile skill with PRODUCES_RECORD execution model
- Profile confirmation evidence record

**Constitutional implication:** Without a structured profile, the agent cannot confirm that the customer's stated risk tolerance, capital allocation, and strategy preferences are recorded with constitutional evidence (C-023 — Evidence First for every governance event including configuration).

**Layer:** trading-agent.md (missing Skill 0); SQL (missing trading_profiles table); containers.md (no trading-profile-mcp).

---

## Phase 3 — Broker Connection

Rahul selects Zerodha. He needs to connect his Kite API.

### [GAP-T003] Zerodha API Authentication Is Fundamentally Different from OAuth

Instagram, Meta, Google all use standard OAuth 2.0 flows. Zerodha Kite uses a proprietary daily authentication flow:
1. Customer logs into Kite web/app
2. Kite generates a `request_token`
3. Customer provides this to the agent
4. Agent exchanges it for an `access_token` (valid for ONE trading day)
5. Every morning: repeat

**Impact:** The `oauth-vault` service (ADR-021) cannot handle Zerodha's daily re-authentication. The oauth-vault is designed for multi-day tokens with refresh. Zerodha tokens expire at midnight every day — there is no refresh token mechanism.

**Resolution needed:** ADR-021 must be extended to handle short-lived, daily-refresh broker tokens separately from long-lived platform OAuth tokens. The `broker-api-mcp` must implement the Kite daily authentication flow.

**Layer:** ADR-021 (needs broker-token handling section); broker-api-mcp (Kite daily auth); trading-agent.md (daily auth as always-ask action at session start).

---

## Phase 4 — Decision Space Configuration

Rahul sets:
- Daily loss limit: ₹16,000 (2%)
- Max position: 15% per trade
- Strategy: directional primary, volatility secondary
- Session: 9:20 AM – 3:00 PM IST

### [GAP-T004] Daily Loss Limit Is a Constitutional Floor (C-043) — Not Yet in Trading Agent Spec

C-043 (Financial Spend Authority Ceiling) was created for DMA paid advertising. The SAME principle applies to trading: the daily loss limit is a Constitutional Floor — the agent MUST halt when it's reached, regardless of any in-progress analysis.

But the trading agent spec does not reference C-043. It mentions daily loss limit as a Decision Space parameter but doesn't treat it as a Constitutional Floor equivalent.

**Resolution:** Add C-043 to trading-agent.md constitutional basis. The daily loss limit must:
- Be validated by CE.ValidateAction with a BudgetContext (same pattern as ad spend)
- Halt ALL trading activities when reached — not just decline new trades
- Create a CE.RecordEvidence(BUDGET_CEILING_REACHED) event
- Trigger immediate customer notification

**Layer:** trading-agent.md (add C-043 to constitutional basis); Skill 3 (Risk Management) — daily loss limit = C-043 enforcement.

---

## Phase 5 — First PAAS Session (9:20 AM)

Rahul opens the portal and clicks "Start trading session." The agent wakes.

### [GAP-T005] Who Starts the PAAS Session? Market Hour Trigger Not Specified

The agent execution loop spec defines heartbeat schedules per skill. For the trading agent: who starts the PAAS session at 9:20 AM? Three options:
(a) Customer manually clicks "Start" in portal/app
(b) Temporal cron at 9:20 AM starts the PAASSessionWorkflow
(c) Agent detects market opening time and starts autonomously

The current spec doesn't answer this. Option (a) is most constitutional (customer explicitly authorizes each session). Option (b) is most convenient. Option (c) raises a constitutional question: can the agent start itself?

**Constitutional answer (C-047):** The agent drives its own execution. The Temporal heartbeat wakes the agent at 9:20 AM market days. The agent reasons "it is a market day at session start time — should I begin a session?" and starts the PAAS workflow. But the customer must have given session-start authority at employment formation. This is a Decision Space entry: `SESSION_AUTO_START: true/false`.

**Layer:** trading-agent.md (add SESSION_AUTO_START to Decision Space); PAASSessionWorkflow (session start trigger spec); nse-calendar-mcp (required to check if today is a market day).

---

### Live PAAS Execution

Agent reads: India VIX = 14.2 (medium regime). NIFTY at 24,350. TRADE_SETUP prompt runs.
Agent reasons: bearish reversal setup at resistance level. Identifies: BUY 24300 PE expiry Thursday.

CE.ValidateAction called:
- action_type: FO_ORDER_PLACE
- Within decision_space.authorized_instruments: NIFTY options ✓
- Within daily loss limit remaining: ₹16,000 ✓
- Within position size limit (15%): ₹1,200 / ₹80,000 = 1.5% ✓ (1 lot)
- CE returns: ALLOW

Evidence: PROPOSED → order placed → EXECUTED (filled at 24 premium).

### [GAP-T006] Order Fill Price vs. Analysis Price — Slippage Not Tracked

The agent's trade setup identifies entry at ₹24. The order fills at ₹25.50 (slippage of ₹1.50 per unit = ₹112.50 per lot). The current spec has no mechanism to:
- Record the intended entry vs actual fill
- Track slippage as a performance metric
- Flag excessive slippage as a skill health degradation signal

**Layer:** Skill 5 (Performance Analytics) needs slippage tracking; `agent_reasoning_traces` should record both intended and executed price; a new `trading_session_records` table is needed.

---

## Phase 6 — Emergency Stop

At 11:40 AM, NIFTY drops sharply. Rahul's position is -₹800. He panics and presses Emergency Stop on the portal.

Emergency Stop fires. PAASSessionWorkflow receives Temporal signal. Agent halts. CE.RecordEvidence(ABANDONED). Position remains open (as specified in spec — agent does NOT auto-close overnight positions unless authorized).

### [GAP-T007] Emergency Stop Position Disclosure Gap

The spec states: "Customer is warned at onboarding: Emergency Stop halts the agent but does not automatically close all positions." But the spec does not define what the agent DOES in the 30-60 seconds after Emergency Stop fires:

- Does it attempt to cancel all pending orders? (Yes — spec says "cancel all pending orders via order.cancel")
- Does it show the customer their open positions immediately after stopping? (Not specified)
- Does it suggest next actions to the customer? (Not specified)
- What evidence records are created for positions that remain open? (Not specified)

**Gap:** Post-Emergency-Stop UX and constitutional evidence for open positions is not specified.

**Layer:** Emergency Stop section of trading-agent.md needs: post-halt position report, customer notification with open positions, evidence record for each open position at halt time.

---

## Phase 7 — Daily Loss Limit Hit (Day 3)

Day 3. Agent has placed 3 trades. Running P&L: -₹14,200. Next setup identified. Position would risk ₹2,800.

14,200 + 2,800 = 17,000 > 16,000 (daily loss limit). CE.ValidateAction with BudgetContext → DENY (budget ceiling).

Agent generates LOSS_LIMIT_ALERT. Customer receives WhatsApp: "I've reached your daily limit. I've stopped trading for today. Your positions: [summary]."

### [GAP-T008] Daily Loss Limit Hit — What Happens to Open Positions?

When the daily loss limit is hit:
- New trades: blocked by CE ✓ (C-043 pattern)
- Pending orders: should be cancelled automatically (to prevent further loss from pending orders that fill after the limit is reached)
- Open positions: remain open — customer decides
- Stop-loss orders for open positions: should these remain active? (The agent is "stopped" but stop-loss orders in the broker system are passive orders that execute at the broker, not at the agent)

**Resolution:** The spec must define: on daily loss limit hit, the agent cancels ALL pending entry orders but leaves stop-loss orders active in the broker system. The customer is notified of this behaviour at onboarding.

**Layer:** Skill 3 (Risk Management) — daily loss limit hit protocol; trading-agent.md onboarding flow (add this disclosure).

---

## Phase 8 — Month End

Month 1: 3 winning sessions, 2 losing sessions. Net P&L: +₹4,200 (0.52% on capital). Rahul expected more.

### [GAP-T009] Performance Expectation Management — No Maturity Equivalent for Trading

The DMA agent produces a Digital Marketing Maturity Score that sets realistic expectations. The trading agent has no equivalent customer education mechanism. There is no:
- Baseline performance assessment before the agent starts trading
- Realistic benchmark (what returns should Rahul expect from a systematic F&O strategy?)
- Performance context (0.52% monthly on ₹8L capital = ₹4,200 = 6.2% annualised, risk-adjusted — is this good?)

The agent's Skill 5 can calculate these but the spec doesn't include a "trading performance assessment" equivalent to the Maturity Report.

**Layer:** trading-agent.md (add Skill 0: Customer Profiling + Strategy Assessment, similar to DMA Skill 0/1).

---

## Phase 9 — Pause / Resume / Terminate / Re-Hire

Pause: Rahul pauses during annual leave. Billing stops pro-rata ✓.

### [GAP-T010] Crypto Portfolio During Pause

When the trading agent is paused:
- F&O: no sessions run (market-hours only — natural pause) ✓
- Crypto: the crypto rebalancing is scheduled (weekly/monthly) not session-bound. Does it stop during pause?

The spec doesn't address crypto behaviour during agent pause. Crypto positions continue to exist — prices move. Should the agent maintain stop-losses during pause? Should it alert the customer if a crypto position hits a loss threshold during pause?

**Layer:** trading-agent.md (add pause behaviour for Skill 4 Crypto Position Management); PauseResumeWorkflow (crypto-specific pause logic).

---

## Gap Register — Trading Agent

### P0 — Must resolve before any live trading session

| ID | Gap | Resolution |
|---|---|---|
| GAP-T003 | Zerodha daily auth incompatible with oauth-vault | ADR-021 extension for daily-refresh broker tokens; broker-api-mcp daily Kite auth flow |
| GAP-T004 | C-043 not applied to trading daily loss limit | Add C-043 to trading-agent.md; CE.ValidateAction BudgetContext for every trade |
| GAP-T005 | Session start trigger not defined | SESSION_AUTO_START Decision Space entry; nse-calendar-mcp market day check |

### P1 — Must resolve before production

| ID | Gap | Resolution |
|---|---|---|
| GAP-T001 | No portal discovery path for trading | Add portal section (Section 6) to trading-agent.md; business_domain_taxonomy entry |
| GAP-T002 | No Skill 0 (trading profile) — no evidence record for configuration | Add Skill 0: Trading Profile + Strategy Assessment to spec; trading_profiles SQL table |
| GAP-T006 | Slippage not tracked | trading_session_records table; slippage in performance analytics |
| GAP-T007 | Post-Emergency-Stop UX undefined | Specify post-halt sequence: cancel pending → report open positions → notify customer |
| GAP-T008 | Daily loss limit hit — open position treatment undefined | Specify: cancel pending entries, leave stop-losses, notify customer |

### P2 — Before full production

| ID | Gap | Resolution |
|---|---|---|
| GAP-T009 | No performance baseline / expectation setting | Add trading performance assessment (equivalent to Maturity Report) |
| GAP-T010 | Crypto pause behaviour undefined | Specify crypto skill behaviour during agent pause |

---

## Constitutional Discoveries — Trading Agent

### CD-T001 — Financial Risk Limit = Constitutional Floor (extends C-043)

The trading agent's daily loss limit is constitutionally identical to the DMA agent's ad spend budget ceiling. Both are financial authority ceilings granted by the customer at hire. The C-043 claim must explicitly include trading loss limits alongside advertising spend limits. The current C-043 text references "paid advertising spend" only.

### CD-T002 — PAAS Session Is a Constitutional Unit (not just a technical concept)

A PAAS session is a bounded period of autonomous authority. Starting a session is a constitutional act (the agent activates its full Decision Space). Ending a session is a constitutional act (the agent releases its active authority). Both events must generate CE evidence records. The current spec mentions this for Emergency Stop but not for normal session start/end.
