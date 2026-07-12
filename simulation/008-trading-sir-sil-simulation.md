# Simulation 008 — Trading Agent: Signal Intelligence + SIR Routing

**Type:** User Simulation — Trading Agent v1.7 (SIL Pre-Session Alerts, SIR Routing, PAAS Full Lifecycle)
**Status:** Active
**Purpose:** Validate C-053 Signal Intelligence Layer for Trading agent (pre-session VIX alerts, broker auth expiry), C-054 SIR routing for trading session queries, and the full PAAS session lifecycle. Extends Simulation 005 (Rahul's Trading Account).
**Persona:** Rahul Sharma, IT professional, Pune. Month 2 of trading agent engagement.

---

## Context

Rahul is in CAMPAIGN_APPROVAL equivalent (PAAS sessions running autonomously, daily review). The trading agent is in its second month. Several new architectural layers are now active: SIL (Signal Intelligence Layer) monitors VIX and broker token expiry; SIR (Skill Intelligence Router) routes Rahul's mid-session queries.

---

## Phase 1 — Pre-Session Signal Alert (C-053)

**8:47 AM — 33 minutes before market open**

The trading agent's Signal Watch Workflow detects:
- VIX spike: India VIX moved from 13.8 to 18.4 overnight (33% increase)
- Signal type: `MARKET_VOLATILITY_SPIKE`
- Materiality score: 0.82 → URGENCY_CLASS: HIGH
- Customer relevance: Rahul has an active SESSION_AUTO_START configuration, market opens at 9:20 AM
- Within budget: YES

Signal injected into Rahul's AgentExecution workflow. Agent wakes.

Agent runs `TRADING/SIGNAL/PROACTIVE_ALERT` prompt:
```
Input: {signal: "VIX_SPIKE", from: 13.8, to: 18.4, pct_change: 33%, 
        strategy: "DIRECTIONAL_FO", daily_loss_limit: 16000}
Output (WhatsApp): "Rahul, heads up before market opens — VIX has spiked 33% overnight 
to 18.4. This is elevated volatility territory. My directional strategy performs 
less predictably when VIX is this high. Options: (a) I proceed with smaller 
position sizes today, (b) I skip today's session, (c) You decide after seeing 
the open. Let me know by 9:15 AM or I'll default to (a)."
```

### [GAP-T011] Pre-Session Alert Requires a Decision Before Session Starts — But Agent Can't Wait Indefinitely

The VIX spike alert asks Rahul to decide by 9:15 AM. This is a valid design. But:

1. What is the agent's default if Rahul doesn't respond by 9:15 AM? The message says "default to (a) — smaller positions." This is a PAAS action taken without explicit approval in this specific context.

2. Is "smaller positions" within the existing Decision Space, or does it require a new configuration?

3. If Rahul is on a call and misses the 9:15 AM deadline — the agent starts a session with reduced positions based on its own judgment. This is borderline constitutional.

**Constitutional tension:** The agent's Decision Space authorizes session execution within declared parameters. Reducing position size is WITHIN the Decision Space (it's less risky, not more). But it is still a deviation from the normal operating mode triggered by a market condition the customer wasn't consulted on.

**Resolution:**
- Trading Decision Space must include: `volatility_regime_response: {HIGH_VIX_THRESHOLD: 18, action: REDUCE_POSITION_SIZE_PCT: 50}` — a pre-authorized response to high volatility conditions that the customer configured at onboarding
- The pre-session alert is informational (not a request for approval) — it tells Rahul what the agent WILL do based on his pre-configured volatility rule
- Evidence record: `VOLATILITY_REGIME_DETECTED` with both the VIX data and the pre-authorized response declared in the Decision Space

**Layer:** trading-agent.md Decision Space (add volatility_regime_response configuration); SESSION_PREP prompt (add volatility regime detection output); onboarding conversation (add volatility preference question).

---

## Phase 2 — Broker Auth Token Expiry Alert (C-053)

**Day 15, 8:32 AM**

Signal Watch Workflow detects: Zerodha access token expires at midnight tonight (Zerodha's daily re-auth cycle). Rahul has not initiated re-authentication.

Signal type: `BROKER_AUTH_EXPIRY`
Materiality score: 0.95 → URGENCY_CLASS: CRITICAL
`emergency_exempt: true` — without auth, no session is possible.

Agent: "Rahul, your Zerodha connection expires today. I need you to re-authenticate by 8:00 PM so tomorrow's session can run. Here's the link: [Kite auth link]"

### [GAP-T012] Zerodha Daily Re-Authentication — The Most Critical Trading Gap

The Zerodha Kite Connect API uses a daily authentication cycle:
1. Each day, the customer must log into Kite web/app, which generates a new `request_token`
2. This `request_token` has a 60-second validity window
3. The `oauth-vault` service must exchange it for an `access_token` within 60 seconds

**This is architecturally incompatible with the oauth-vault's current design (ADR-021):**
- oauth-vault is designed for long-lived OAuth tokens with background refresh
- Zerodha tokens cannot be refreshed — they must be re-generated fresh every day by customer action
- The 60-second window means the exchange cannot be queued or retried — it must happen in real-time

**This is a P0 gap before ANY live trading can begin.** (Was GAP-T003 in Simulation 005.)

**Resolution — two-part:**

Part 1: **ADR-021 extension** — declare a new token class: `DAILY_BROKER_TOKEN`
```
DAILY_BROKER_TOKEN class:
  - Token lifetime: 1 trading day
  - No refresh_token exists
  - Customer must re-authenticate DAILY before market hours
  - exchange_window_seconds: 60 (from Zerodha spec)
  - Re-auth mechanism: customer visits Kite URL → generates request_token → 
    WAOOAW callback URL receives request_token → oauth-vault exchanges within 60s
  - SIL trigger: BROKER_AUTH_EXPIRY signal fires at 7:00 PM every trading day
    (5 hours before midnight, giving customer time to re-auth before sleep)
```

Part 2: **Portal + WhatsApp deep link** — the agent's BROKER_AUTH_EXPIRY alert must include a direct deep link that:
- Opens WAOOAW portal → broker connection page
- Has a "Re-authenticate Zerodha" button that initiates the Kite login flow
- The customer completes Kite login → WAOOAW callback processes the request_token
- oauth-vault stores the new access_token
- Agent receives "BROKER_RECONNECTED" signal

**Layer:** ADR-021 (add DAILY_BROKER_TOKEN class documentation); broker-api-mcp spec (Kite daily auth flow); trading-agent.md Skill 0 / always-ask action (`BROKER_DAILY_REAUTH`); SIL declaration (add BROKER_AUTH_EXPIRY signal type); SQL: update broker_connections table if needed.

---

## Phase 3 — Skill Intelligence Router: Mid-Session Query

Rahul is in an active PAAS session at 11:30 AM. He sends a message:
"VIX is dropping — how are we doing today, and should we add to our winning position in NIFTY?"

SIR receives. Intents:
1. `PERFORMANCE_STATUS` → primary: `SESSION_REPORT` skill
2. `STRATEGY_QUESTION` → primary: `TRADE_SETUP` skill

SIR Layer 4: Sequence — SESSION_REPORT first (performance context), then TRADE_SETUP reasoning (with context from session report).

### [GAP-T013] Trading Agent Has No Skill Capability Manifests (Section 3.19 — Deferred P1)

Trading agent SCMs were explicitly deferred as "P1 before Trading IB-009" in the EA review. The SIR cannot route Rahul's query correctly without SCMs for each Trading skill.

Without SCMs, the SIR falls back to a generic intent classification that maps to skill types by name — fragile and inaccurate. For example: "should we add to our winning position" might route to `LOSS_LIMIT_ALERT` (wrong skill) if the intent classification isn't skill-aware.

**Gap:** Trading agent must have Section 3.19 (SCMs) before ANY SIR-based routing can function. This is a constitutionally mandatory section per C-054.

**Resolution (fix this simulation):** Adding Trading agent SCMs is part of the simulation gap resolution. See Architecture Fixes section below.

---

## Phase 4 — Loss Limit Alert (Constitutional Floor)

Day 5. Rahul's P&L at 12:15 PM: -₹13,500. He has one pending order (BUY order on hold, not yet filled).

Agent running LOSS_LIMIT_ALERT assessment: -₹13,500 + pending order exposure = -₹13,500. Margin remaining to limit: ₹2,500.

CE.ValidateAction called before next TRADE_SETUP run:
```
action_type: FO_ORDER_PLACE
budget_context: {daily_loss_remaining: 2500, position_exposure: 1500}
```

CE: ALLOW (₹1,500 < ₹2,500 remaining)

Agent places the order. It fills immediately. P&L: -₹15,000. Agent attempts next TRADE_SETUP.

CE.ValidateAction:
```
budget_context: {daily_loss_remaining: 1000, next_position_exposure: 1500}
```
CE: DENY — next position would exceed limit.

Agent runs LOSS_LIMIT_ALERT prompt. Customer notified: "I've reached my stop for today — ₹16,000 daily limit hit. No new positions."

### [GAP-T014] Pending Order at Limit Breach: Race Condition

The scenario above assumes the pending order fills before the daily limit check. But what if:
- Rahul's P&L hits -₹16,000 exactly when a pending order is in flight (submitted but not filled)?
- Should the agent cancel the pending order?
- If the order fills 2 seconds after the limit is reached, the actual loss is -₹17,500

**Current spec says:** "On daily loss limit hit, cancel ALL pending entry orders but leave stop-loss orders active."

**Gap:** The order cancellation timing is not atomic. Between detecting the limit breach and cancelling the pending order, the order might fill. This is an inherent race condition in financial markets.

**Resolution:**
- When `daily_loss_limit_hit` event fires: immediately call `broker-api-mcp: order.cancel_all_pending` BEFORE the CE evidence record is created (cancellation is an emergency action, not subject to Evidence First sequencing)
- Accept that some orders may have already filled before cancellation — record the actual vs expected loss in `trading_session_records`
- Inform customer of the race condition at onboarding: "In fast markets, my stop may trigger at exactly ₹16,000 or slightly over due to order fill timing"

**Constitutional note:** This is analogous to the Emergency Stop latency guarantee — we cannot guarantee exact precision, but we must guarantee best-effort precision and transparent disclosure.

**Layer:** Skill 3 (Risk Management) — add order cancellation as immediate action on limit hit; `trading_session_records` race condition field; onboarding disclosure.

---

## Phase 5 — SESSION_REPORT: Post-Session Evidence

Session ends at 3:25 PM. Agent runs SESSION_REPORT prompt.

Produces:
- Session P&L: -₹4,200
- Trades executed: 3 (2 profitable, 1 loss)
- Daily loss limit utilization: 26%
- VIX regime: ELEVATED (maintained 50% reduced positions per volatility_regime_response)
- Strategy alignment: DIRECTIONAL_PRIMARY 3 trades ✓
- Evidence records: 3 trade evidence records + session summary record

### [GAP-T015] SESSION_REPORT Has No Slippage Calculation

The Session Report prompt produces P&L but does not calculate or report slippage (difference between intended and actual fill price). This was GAP-T006 in Simulation 005.

**Current state of spec:** trading-agent.md mentions "Executed trade P&L vs expected P&L (trade slippage + strategy effectiveness)" as the Business KPI for Skill 2. But there is no `trading_session_records` SQL table and no slippage field in the evidence records.

**Resolution:**
- Add `trading_session_records` SQL table (see Architecture Fixes)
- Add `intended_entry_price` and `actual_fill_price` to `agent_evidence_records` for trading agent (via JSONB action_parameters)
- SESSION_REPORT prompt output schema: add `slippage_total_inr`, `slippage_pct_of_pl`, `worst_slippage_trade`

**Layer:** SQL (trading_session_records table); trading-agent.md SESSION_REPORT prompt schema; trading-agent.md Skill 2 (Trade Execution) evidence record schema.

---

## Architecture Fixes — Trading Agent Simulation 008

The following fixes address Trading simulation gaps and are implemented in the architecture:

### Fix 1: Trading Agent Section 3.18 — Signal Intelligence Layer

```yaml
signal_intelligence:
  signal_feeds:
    - feed_id: "MARKET_VOLATILITY"
      mcp_server: "market-data-mcp"
      tool_call: "market.get_vix"
      poll_cadence: "PT1H"
      relevance_dimension: "session_auto_start = true AND market_open_within_2h"
      materiality_classifier: "vix_change_pct > 20 → HIGH; vix > 25 → CRITICAL"

    - feed_id: "BROKER_AUTH_STATUS"
      mcp_server: "broker-api-mcp"
      tool_call: "auth.check_token_expiry"
      poll_cadence: "PT1H"
      relevance_dimension: "has_active_employment_contract"
      materiality_classifier: "token_expires_within_hours < 5 → CRITICAL always"

  signal_types:
    - signal_type: "MARKET_VOLATILITY_SPIKE"
      feed_id: "MARKET_VOLATILITY"
      skill_id: "SESSION_PREP"
      urgency_class_rule: "vix_change_pct > 20 → HIGH; vix > 25 → CRITICAL"
      urgency_class: "HIGH"
      emergency_exempt: false
      channel: "WHATSAPP"
      trai_outside_window_behavior: "DEFER"
      evidence_action_type: "PROACTIVE_SIGNAL_ALERT"

    - signal_type: "BROKER_AUTH_EXPIRY"
      feed_id: "BROKER_AUTH_STATUS"
      skill_id: "SESSION_PREP"
      urgency_class_rule: "token_expires_within_hours < 5 → CRITICAL always"
      urgency_class: "CRITICAL"
      emergency_exempt: true
      channel: "WHATSAPP"
      trai_outside_window_behavior: "IMMEDIATE"
      evidence_action_type: "PROACTIVE_SIGNAL_ALERT"

  materiality_thresholds:
    critical: 0.90
    high: 0.70
    advisory: 0.50

  hsm_templates:
    - signal_type: "BROKER_AUTH_EXPIRY"
      template_name: "trading_auth_expiry_v1"
      template_text: "Hi {{1}}! Your broker connection expires today. Re-authenticate to keep trading sessions running. Reply to this message."
      meta_approval_status: "PENDING"
```

### Fix 2: Trading Agent Section 3.19 — Skill Capability Manifests

```yaml
skill_intelligence_router:
  router_prompt: "TRADING/ROUTING/SKILL_INTENT_ROUTER"
  gap_signalling:
    gap_signal_threshold_days: 30
    gap_frequency_min: 2
    cross_customer_threshold: 3
    evidence_table: "institutional.skill_gap_signals"

  skill_capability_manifests:

    - skill_id: "SESSION_PREP"
      version: "1.7"
      intent_signatures:
        - "how is today looking"
        - "market outlook"
        - "what should I expect today"
        - "VIX is high what do we do"
        - "should we trade today"
        - "pre-session analysis"
      servable_request_types:
        PRE_SESSION_BRIEF: "Produces SESSION_PREP analysis: regime, strategy, max position, risk assessment"
        MARKET_CONTEXT: "Answers question about current market conditions"
      unservable_request_types:
        - intent: "execute a trade now"
          routes_to_skill: "TRADE_SETUP"
        - intent: "stop all trading"
          routes_to_skill: null  # Emergency Stop path, not SIR
      input_requirements:
        required: ["market-data-mcp.vix", "market-data-mcp.nifty_level"]
        optional: ["broker-api-mcp.open_positions"]
      output_contributions:
        - type: "session_context"
          used_by: ["TRADE_SETUP", "LOSS_LIMIT_MANAGEMENT"]
      collaboration_affinities:
        - with_skill: "TRADE_SETUP"
          relationship: "UPSTREAM"
          benefit: "Session regime context (VIX, market direction) constrains trade setup parameters"

    - skill_id: "TRADE_SETUP"
      version: "1.7"
      intent_signatures:
        - "what trade should I take"
        - "setup for today"
        - "NIFTY trade idea"
        - "options strategy"
        - "add to position"
        - "should we enter now"
        - "entry signal"
      servable_request_types:
        TRADE_RECOMMENDATION: "Produces TRADE_SETUP analysis: entry, target, stop, size, constitutional basis"
        POSITION_ASSESSMENT: "Evaluates whether to add to an existing position"
      unservable_request_types:
        - intent: "performance this month"
          routes_to_skill: "SESSION_REPORT"
        - intent: "stop trading today"
          routes_to_skill: "LOSS_LIMIT_MANAGEMENT"
      input_requirements:
        required: ["session_prep.session_context", "broker-api-mcp.current_positions"]
        optional: ["market-data-mcp.option_chain"]
      output_contributions:
        - type: "trade_recommendation"
          used_by: []
      collaboration_affinities:
        - with_skill: "SESSION_PREP"
          relationship: "DOWNSTREAM"
          benefit: "Trade setup requires session regime context; bad regime = no setup or reduced size"
        - with_skill: "LOSS_LIMIT_MANAGEMENT"
          relationship: "BIDIRECTIONAL"
          benefit: "Trade setup checks remaining daily budget; loss limit monitors executed trades"

    - skill_id: "LOSS_LIMIT_MANAGEMENT"
      version: "1.7"
      intent_signatures:
        - "daily limit"
        - "how much have I lost today"
        - "remaining budget"
        - "are we near the limit"
        - "stop trading"
        - "risk status"
      servable_request_types:
        RISK_STATUS: "Reports current P&L, remaining daily limit, position exposure"
        HALT_TRADING: "Executes daily loss limit halt: cancel pending orders, notify customer"
      unservable_request_types:
        - intent: "new trade"
          routes_to_skill: "TRADE_SETUP"
      input_requirements:
        required: ["broker-api-mcp.positions_pnl", "decision_space.daily_loss_limit"]
        optional: []
      output_contributions:
        - type: "risk_status"
          used_by: ["TRADE_SETUP", "SESSION_PREP"]
      collaboration_affinities:
        - with_skill: "TRADE_SETUP"
          relationship: "BIDIRECTIONAL"
          benefit: "Trade setup must check loss limit status; loss limit monitors all executed trades"

    - skill_id: "SESSION_REPORT"
      version: "1.7"
      intent_signatures:
        - "how did we do today"
        - "session summary"
        - "performance today"
        - "P&L for the session"
        - "what happened"
        - "session report"
      servable_request_types:
        SESSION_SUMMARY: "Produces end-of-session report: P&L, trades, slippage, strategy alignment"
        PERFORMANCE_QUERY: "Answers specific performance question for current session"
      unservable_request_types:
        - intent: "monthly performance"
          routes_to_skill: null  # No monthly performance skill yet (P2)
        - intent: "new trade setup"
          routes_to_skill: "TRADE_SETUP"
      input_requirements:
        required: ["institutional.agent_evidence_records (session trades)"]
        optional: ["broker-api-mcp.final_positions"]
      output_contributions:
        - type: "session_performance_record"
          used_by: []
      collaboration_affinities:
        - with_skill: "LOSS_LIMIT_MANAGEMENT"
          relationship: "DOWNSTREAM"
          benefit: "Session report includes final loss limit utilization from risk management skill"
```

---

## Gap Register — Trading Simulation 008

### P0 — Must resolve before live trading

| ID | Gap | Resolution |
|---|---|---|
| GAP-T012 | Zerodha daily re-auth incompatible with oauth-vault | ADR-021 extension: DAILY_BROKER_TOKEN class; broker-api-mcp Kite daily auth flow |
| GAP-T013 | Trading agent has no SCMs (Section 3.19 deferred) | Added in this simulation — SCMs for all 4 trading skills |
| GAP-T014 | Pending order race condition at daily loss limit hit | Cancel-all-pending as immediate action; onboarding disclosure; trading_session_records race field |

### P1 — Before production

| ID | Gap | Resolution |
|---|---|---|
| GAP-T011 | Pre-session alert requires volatile regime response in Decision Space | Add volatility_regime_response to Decision Space; onboarding question |
| GAP-T015 | No slippage calculation in SESSION_REPORT | trading_session_records table; slippage fields in evidence records |

---

## Constitutional Discoveries — Trading Agent

### CD-T003 — DAILY_BROKER_TOKEN Is a New Constitutional Pattern

The Zerodha daily re-auth creates a new class of customer obligation: **daily active participation required for agent to function.** Unlike other agents where the customer can be entirely passive (approve a campaign → agent runs for a month), the trading customer must actively re-authenticate every morning. This daily obligation is a constitutional modification of C-034 (employment lifecycle) — the employment remains active, but a daily customer action is a prerequisite for each session.

This should be explicitly stated in the trading agent's `always_ask_actions`: `BROKER_DAILY_REAUTH` as a mandatory daily always-ask action.
