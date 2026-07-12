# AI Agent Execution Loop Specification

**Authority:** C-047 (Agent-Driven Execution — LAW); AD-019 (Agent-Driven Orchestration); DP-018 (Agent Execution Primacy)
**Date:** 2026-07-09
**Constitutional Basis:** C-036 (Skills as constitutional units); C-030 (Decision Space as primitive); C-047

---

## The Fundamental Shift

**Before (code-driven):**
```
Temporal Cron → triggers SkillExecutionActivity → calls AI Runtime → AI generates content
                ↑ code decides what happens                           ↑ AI is a tool
```

**After (agent-driven):**
```
Heartbeat wakes agent → Agent reads context → Agent reasons about what to do next
→ Agent proposes action → CE validates → Temporal makes it durable → Agent observes outcome
   ↑ agent decides                        ↑ code enforces
```

The Temporal workflow is the **durability substrate** — it ensures the agent's decision survives crashes, network failures, and timeouts. It does NOT make decisions. The agent decides. Temporal executes durably.

---

## The Standard Agent Execution Loop

Every skill in every agent runs this loop. It is the implementation of C-047.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION LOOP                         │
│                                                                 │
│  1. WAKE                                                        │
│     Agent receives a heartbeat signal (Temporal timer) or      │
│     an event signal (approval received, new data available,     │
│     customer message, platform alert)                           │
│                                                                 │
│  2. LOAD CONTEXT                                               │
│     Decision Space (version N)                                  │
│     Customer Profile (Tier 2 RAG)                               │
│     Domain Knowledge (Tier 1 RAG — top-5 relevant chunks)      │
│     Platform Intelligence (Tier 3 RAG — benchmarks)            │
│     Recent action history (last N evidence records)             │
│     Current goals and KPI state                                 │
│     Pending approvals / outstanding items                       │
│     Approval mode and synthetic confidence state                │
│                                                                 │
│  3. REASON                                                      │
│     LLM call with loaded context + Decision Space + prompt      │
│     Agent produces: AgentReasoningOutput                        │
│       - What is the most appropriate action right now?          │
│       - Constitutional basis for the action                     │
│       - Confidence in the decision                              │
│       - Alternatives considered and rejected                    │
│     Write: ReasoningTrace to institutional.agent_reasoning_traces│
│                                                                 │
│  4. VALIDATE                                                    │
│     CE.ValidateAction(action, decision_space, budget_context?,  │
│                       synthetic_context?, reasoning_trace_id)   │
│     → ALLOW: proceed                                            │
│     → DENY: record reasoning trace outcome; sleep or escalate   │
│     → ESCALATE: raise approval request; wait for signal         │
│                                                                 │
│  5. EXECUTE                                                     │
│     CE.RecordEvidence(PROPOSED) — Evidence First (C-023)        │
│     MCP tool call (via authorized tool registry)                │
│     CE.RecordEvidence(EXECUTED)                                 │
│     Update reasoning trace: outcome_action_taken, evidence_id   │
│                                                                 │
│  6. OBSERVE                                                     │
│     Read execution outcome (success / partial / degraded)       │
│     Update skill performance state                              │
│     Update approval learning corpus (if APPROVAL_GATE)         │
│     Check synthetic confidence trend (if SYNTHETIC_APPROVAL)   │
│                                                                 │
│  7. DECIDE NEXT                                                 │
│     Reason about next action in the current context             │
│     → If more work in this cycle: LOOP to step 3               │
│     → If cycle complete: sleep until next heartbeat/event       │
│     → If goal missed threshold: trigger self-governance         │
│     → If constitutional anomaly detected: escalate to L3        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Temporal Implementation of the Loop

```python
@workflow.defn
class AgentExecutionWorkflow:
    """
    The durable wrapper for the Agent Execution Loop.
    This workflow does NOT contain decision logic — it is the execution substrate.
    All decisions come from the agent's reasoning step.
    """

    def __init__(self):
        self._context: AgentContext = None
        self._pending_approval: Optional[str] = None

    @workflow.run
    async def run(self, input: AgentWorkflowInput) -> None:
        self._context = AgentContext.from_input(input)

        while True:
            # STEP 2: Load context (Temporal activity — durable)
            context = await workflow.execute_activity(
                load_agent_context,
                self._context,
                start_to_close_timeout=timedelta(seconds=30),
            )

            # STEP 3+4+5+6: Agent reasoning + CE validation + execution (single durable activity)
            result = await workflow.execute_activity(
                agent_reasoning_and_execution_activity,   # see AI Execution Loop Activity below
                AgentActivityInput(context=context, pending_approval=self._pending_approval),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            self._pending_approval = None

            # STEP 7: Decide next
            if result.cycle_complete:
                # Sleep until next heartbeat
                await asyncio.sleep(result.sleep_seconds)
            elif result.escalation_required:
                # Wait for approval signal (up to approval_timeout)
                try:
                    await workflow.wait_condition(
                        lambda: self._pending_approval is not None,
                        timeout=timedelta(hours=result.approval_timeout_hours),
                    )
                except TimeoutError:
                    await workflow.execute_activity(
                        handle_approval_timeout,
                        result.escalation_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )

    @workflow.signal
    def approval_received(self, approval_id: str) -> None:
        self._pending_approval = approval_id

    @workflow.signal
    def approval_rejected(self, approval_id: str, reason: str) -> None:
        self._pending_approval = f"REJECTED:{approval_id}:{reason}"


@activity.defn
async def agent_reasoning_and_execution_activity(
    input: AgentActivityInput,
) -> AgentActivityResult:
    """
    The core agent execution unit. This is where the agent DECIDES AND ACTS.
    Steps 3 through 6 of the Agent Execution Loop.
    """

    # STEP 3: REASON — Load prompt and call LLM
    prompt = await prompt_registry.get_active(
        input.context.skill_type,
        input.context.current_pipeline_step
    )
    if not prompt:
        await alert_platform_ops(
            f"INFERENCE_BLOCKED: No approved prompt for {input.context.skill_type}/"
            f"{input.context.current_pipeline_step}"
        )
        return AgentActivityResult(cycle_complete=True, sleep_seconds=300)

    reasoning_output = await llm_client.reason(
        prompt=prompt,
        context=input.context,
        response_format=AgentReasoningOutput,
    )

    # Write reasoning trace BEFORE any action (C-047, AD-019)
    trace_id = await reasoning_trace_store.write(reasoning_output, input.context)

    # STEP 4: VALIDATE
    ce_response = await ce_client.ValidateAction(
        ValidateActionRequest(
            contract_id=input.context.contract_id,
            action_type=reasoning_output.decision.action_type,
            action_parameters=reasoning_output.decision.action_parameters_json,
            decision_space_version=input.context.decision_space_version,
            reasoning_trace_id=str(trace_id),
            budget_context=reasoning_output.decision.budget_context,
            synthetic_approval_context=reasoning_output.decision.synthetic_context,
            approval_type=input.context.approval_mode.to_proto(),
        )
    )

    if ce_response.decision == ValidationDecision.DENY:
        await reasoning_trace_store.update_outcome(trace_id, "DENIED_BY_CE")
        # If DENY, agent reasons about what to do instead
        return AgentActivityResult(
            cycle_complete=True,
            sleep_seconds=3600,
            denial_recorded=True,
        )

    if ce_response.decision == ValidationDecision.ESCALATE:
        # Raise approval request, return escalation signal
        approval_id = await bp_client.create_approval_request(
            reasoning_output.decision, trace_id, input.context
        )
        return AgentActivityResult(
            cycle_complete=False,
            escalation_required=True,
            escalation_id=approval_id,
            approval_timeout_hours=input.context.approval_timeout_hours,
        )

    # STEP 5: EXECUTE — Evidence First (C-023)
    proposed_evidence_id = await ce_client.RecordEvidence(PROPOSED, reasoning_output)
    execution_result = await mcp_client.execute(reasoning_output.decision)
    executed_evidence_id = await ce_client.RecordEvidence(EXECUTED, execution_result)

    # STEP 6: OBSERVE
    await reasoning_trace_store.update_outcome(
        trace_id,
        outcome_action_taken=reasoning_output.decision.action_type,
        outcome_evidence_id=executed_evidence_id,
    )
    await skill_state_store.update(input.context, execution_result)

    return AgentActivityResult(
        cycle_complete=True,
        sleep_seconds=input.context.next_heartbeat_seconds,
        evidence_id=executed_evidence_id,
    )
```

---

## Heartbeat Schedule (Per Skill Type)

The agent execution loop is triggered by Temporal schedules. The agent then REASONS about what to do — the schedule only wakes it.

| Skill | Heartbeat | What agent reasons about on wake |
|---|---|---|
| Content Strategy | Monday 9 AM IST | Does the current week have an approved plan? Should I propose next month's calendar? |
| Instagram / Facebook | Daily 8 AM IST | Are there approved posts scheduled for today? Do I have enough for this week? |
| Google Business | Daily 9 AM IST | Are there new reviews to respond to? Any update posts due? |
| WhatsApp | Tuesday + Thursday 10 AM IST | Are there approved reminder messages to send? |
| Analytics | Monthly last 3 days | Should I generate the monthly performance narrative? |
| Local SEO | Monthly day 1 | Any keyword ranking changes? Any GBP optimisation needed? |
| Paid Advertising | Daily 8 AM IST | Campaign performance check. Is budget pace healthy? Any bid adjustments needed? |
| Competitive Intelligence | Weekly Monday | Any competitor changes to report? |
| Self-Governance | Monthly day 15 + day 28 | Is goal pace on track? Corrections needed? |
| Customer Profiling | On demand (registration event) | Profile complete? Ready to trigger Market Research? |
| Market Research | On demand (profile confirmed) + 6-monthly | Score the customer's current state |

---

## The Agent Loop and Constitutional Engine Integration

The key new element is `reasoning_trace_id` passed to CE.ValidateAction. This enables:

1. **Audit chain completeness:** Evidence records now link to reasoning traces. You can answer: "Why did the agent decide to make this post?" with a constitutional reasoning chain.

2. **CE.EvaluatePolicy with reasoning context:** When CE needs to reason about a novel action, it receives the agent's own reasoning as context — the constitutional reasoning agent can assess: "The agent believed this was constitutional because X. Is that belief correct?"

3. **Operations intelligence:** The Platform Operations Agent queries reasoning traces to detect: declining confidence scores (skill degradation), constitutional basis gaps (agent citing wrong claims), override rate spikes (synthetic approval model drift).

---

## What this Replaces in the Current Spec

| Old design | New design | Why |
|---|---|---|
| Temporal cron triggers content activity | Agent wakes on heartbeat, reasons "what content is needed today?" | C-047 — agent decides |
| Skill execution is a fixed sequence of activities | Skill execution is agent's reasoning output → CE validates → durable execution | DP-018 |
| LLM call is a step in a pipeline | LLM reasoning is the FIRST step that drives all subsequent steps | AD-019 |
| Evidence record records outcome | Evidence record + Reasoning Trace record both created; trace is primary | C-047 |
| CE.ValidateAction is a rule check | CE.ValidateAction includes constitutional reasoning for EvaluatePolicy cases | Layer 2 review |
| Skills run independently on their own heartbeats | Skills are orchestrated by Strategic Cognition Layer — plan first, then execute | C-050 — DP-019 |
| Agent waits for customer to report a problem | Agent continuously watches signal feeds; proactively alerts before the customer knows | C-053 — DP-022 |
| Skills execute independently from a list | Skills route intelligently via SIR; multi-skill requests are orchestrated as one response | C-054 — DP-023 |

---

## Signal Intelligence Layer — The Proactive Watch Loop

**Authority:** C-053 (Signal Sensing Obligation — LAW); AD-026 (Signal Watch Workflow Pattern); DP-022 (Proactive Intelligence Primacy)
**Added:** v0.35.0

The Execution Loop and Strategic Cognition Loop are both **customer-or-schedule-triggered**. The Signal Intelligence Layer introduces a third, **always-on, environment-triggered** loop that runs in parallel to detect and communicate material external signals before the customer asks.

```
┌────────────────────────────────────────────────────────────────────────┐
│              SIGNAL WATCH WORKFLOW (C-053)                             │
│  One long-running Temporal workflow per signal_type per agent_type     │
│  NOT per-customer — platform-level, fans out to relevant customers     │
│                                                                        │
│  1. POLL                                                               │
│     Execute MCP tool call at declared poll_cadence                     │
│     (weather-ensemble-mcp, agmarknet-mcp, platform-analytics-mcp…)    │
│     Result: raw signal event (weather observation, price point, etc.)  │
│                                                                        │
│  2. CLASSIFY MATERIALITY (LOCAL tier — ₹0)                            │
│     Rule-based or fine-tuned LOCAL model                               │
│     Input: raw signal event                                            │
│     Output: materiality_score (0.0–1.0) + urgency_class               │
│     CRITICAL (≥0.90) | HIGH (0.70–0.89) | ADVISORY (0.50–0.69)        │
│     Below threshold → discard + log only                               │
│                                                                        │
│  3. MATCH CUSTOMERS (LOCAL tier — ₹0)                                 │
│     Cross-reference signal against Customer Registry                   │
│     Input: signal_type + signal_payload                                │
│     Relevance dimension: customer profile fields declared in SCM       │
│     Output: [(customer_id, relevance_score, skill_id)]                 │
│     Filter: relevance_score ≥ 0.70                                     │
│                                                                        │
│  4. CHECK TRAI WINDOW + BUDGET                                         │
│     For each matched customer:                                         │
│       CRITICAL → always proceed (emergency_exempt: true)               │
│       HIGH/ADVISORY → check TRAI 24-hour window                        │
│         Within window + budget > 0 → proceed                          │
│         Outside window → queue HSM pre-approved template only          │
│         Budget = 0 (non-CRITICAL) → log event for period-reset bundle  │
│                                                                        │
│  5. INJECT EVENT SIGNAL                                                │
│     Send Temporal signal to customer's AgentExecutionWorkflow          │
│     Signal type: PROACTIVE_SIGNAL_{SIGNAL_TYPE}                        │
│     Payload: {signal_event, materiality_score, urgency_class,          │
│              trai_window_status, customer_context_snapshot}            │
│     → Customer's Execution Loop wakes immediately (Step 1: WAKE)       │
│       with signal_trigger context instead of heartbeat context         │
│                                                                        │
│  6. LOG                                                                │
│     INSERT INTO institutional.signal_materiality_events                │
│     (signal_type, materiality_score, urgency_class,                    │
│      customers_matched, customers_notified, customers_deferred,        │
│      signal_payload_hash, detected_at)                                 │
│                                                                        │
│  7. CONTINUE_AS_NEW (every 1,000 poll cycles)                         │
│     Prevents unbounded Temporal event history                          │
│     State: {last_signal_hash, consecutive_below_threshold_count}       │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**When the Execution Loop receives a PROACTIVE_SIGNAL trigger:**
- Step 2 (LOAD CONTEXT) includes the signal event as primary context
- Step 3 (REASON) uses `{AGENT}/SIGNAL/PROACTIVE_ALERT` prompt instead of normal skill prompt
- Step 5 (EXECUTE): evidence action_type = `PROACTIVE_SIGNAL_ALERT`
- Customer receives proactive advisory in their language via configured channel

**Multi-Signal Bundling Rules (GAP-A010 — CD-A004, v0.40.0):**

When multiple signals fire within a short window for the same customer, blind sequential delivery overwhelms the customer (C-048 violation). The following bundling rules apply:

```
RULE 1 — CRITICAL signals: send IMMEDIATELY and SOLO.
  No bundling with any other signal. No waiting.
  Record in signal_bundling_log: bundling_decision = 'IMMEDIATE_SOLO'

RULE 2 — HIGH signals within 15 minutes of a CRITICAL signal:
  Hold for 2 hours, then bundle HIGH signals together.
  If still within TRAI window at delivery time: send bundled message.
  If TRAI window closed: defer to next morning (7:00 AM IST).
  Record in signal_bundling_log: bundling_decision = 'HELD_FOR_BUNDLE'

RULE 3 — Multiple HIGH signals within 15 minutes of each other (no CRITICAL):
  Bundle into single advisory message delivered within 30 minutes.
  Use PROACTIVE_ALERT prompt with all signal contexts as input.
  Record in signal_bundling_log: bundling_decision = 'HELD_FOR_BUNDLE'

RULE 4 — ADVISORY signals:
  Always defer to next scheduled heartbeat/communication.
  Include as "intelligence brief" in next regular message.
  Record in signal_bundling_log: bundling_decision = 'DEFERRED_TO_HEARTBEAT'
```

**TRAI Category for CRITICAL signal delivery (GAP-A009 — CD-A003, v0.40.0):**
Any signal with `emergency_exempt: true` and `urgency_class: CRITICAL` must be delivered using a WhatsApp HSM template with `category: UTILITY` (not MARKETING). UTILITY messages are exempt from TRAI DND hours (9 PM - 9 AM). An agent spec that sends a CRITICAL signal using a MARKETING template has misclassified a constitutional obligation as a commercial message — this is a C-053 violation.

**Temporal implementation note:**
```python
@workflow.signal
def proactive_signal_received(self, signal: ProactiveSignalInput) -> None:
    """
    Received from SignalWatchWorkflow when a material signal is detected.
    Applies bundling rules before adding to delivery queue.
    """
    if signal.urgency_class == 'CRITICAL':
        # CRITICAL: send immediately, solo — bypass queue
        self._immediate_signal_queue.append(signal)
        asyncio.create_task(self._deliver_critical_signal(signal))
    else:
        # HIGH/ADVISORY: apply bundling rules
        self._signal_queue.append(signal)
        self._apply_bundling_rules()

# In the main execution loop:
if self._signal_queue:
    signal = self._signal_queue.pop(0)
    context = await load_agent_context_with_signal(self._context, signal)
    # Proceeds to REASON step with signal as primary context
```

---

## Skill Intelligence Router — The Request-Time Routing Layer

**Authority:** C-054 (Skill Intelligence Routing — LAW); AD-027 (Skill Capability Manifest Standard); DP-023 (Skill Network Intelligence)
**Added:** v0.35.0

The SIR executes as a **pre-step before the Execution Loop's REASON step** whenever a customer message triggers the loop. It classifies the customer's intent, matches it against active Skill Capability Manifests, and produces a routing plan that the REASON step uses.

```
┌────────────────────────────────────────────────────────────────────────┐
│              SKILL INTELLIGENCE ROUTER (SIR)                           │
│  Runs at LOCAL tier — ₹0. Adds ≤ 10ms to request processing.          │
│  Executes BEFORE Step 3 (REASON) in the Execution Loop                 │
│                                                                        │
│  INPUT: {customer_message, agent_type, customer_id, active_skills[]}   │
│                                                                        │
│  ── LAYER 1: INTENT CLASSIFICATION ──────────────────────────────────  │
│  LOCAL classifier (rule-based Phase 1; fine-tuned Phase 2)             │
│  Output: {primary_intent, secondary_intents[], confidence}             │
│                                                                        │
│  ── LAYER 2: SKILL CAPABILITY MATCH ─────────────────────────────────  │
│  Vector similarity: intents vs. active Skills' SCM.intent_signatures   │
│  Only ACTIVE skills visible (inactive/deactivated skills excluded)     │
│  Output: {primary_skill, contributing_skills[], gap_detected: bool}    │
│                                                                        │
│  gap_detected = true when:                                             │
│    - No skill scores above similarity threshold (0.70)                 │
│    - OR all matching skills are in INACTIVE state                      │
│    → Emit SKILL_GAP_SIGNAL to institutional.skill_gap_signals           │
│    → Apply adjacent_professional_routing if available                  │
│                                                                        │
│  ── LAYER 3: SKILL STATE VALIDATION ─────────────────────────────────  │
│  For each matched skill: check activation_state                        │
│    oauth_status = CONNECTED?                                           │
│    within_budget = true?                                               │
│    approval_mode compatible with request type?                         │
│  Output: {routing_plan, degraded_skills[], blocked_skills[]}           │
│                                                                        │
│  ── LAYER 4: COLLABORATION ORCHESTRATION PLAN ───────────────────────  │
│  If contributing_skills is non-empty:                                  │
│    Build dependency-ordered execution plan from SCM affinities          │
│    Identify data handoffs (Skill A output → Skill B input_requirement) │
│    Determine combined_approval: bool                                   │
│      (true when all contributing skills are APPROVAL_GATE — one        │
│       combined approval request replaces N individual requests)        │
│                                                                        │
│  OUTPUT: SIR_RoutingPlan {                                             │
│    primary_skill: "[SKILL_TYPE_ID]",                                   │
│    execution_sequence: [{skill_id, step, inputs, outputs}],            │
│    combined_approval: bool,                                            │
│    gap_detected: bool,                                                 │
│    gap_signal_emitted: bool,                                           │
│    estimated_usage_units: N                                            │
│  }                                                                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                         ↓ SIR_RoutingPlan
    Step 3 (REASON) uses routing plan to load correct Skill's RAG context,
    MCP tools, and Decision Space constraints.
    Multi-skill: Skill Collaboration Orchestrator (SCO) runs Steps 3-5
    in dependency order, passing outputs between Skills.
```

**Relationship between SIR and Strategic Cognition Layer (C-050 vs C-054):**
```
Strategic Cognition Layer (C-050)     Skill Intelligence Router (C-054)
──────────────────────────────────    ──────────────────────────────────
Runs at: trigger events (low freq)    Runs at: every customer request
Asks: "Which Skills in portfolio?"    Asks: "Which active Skill(s) for THIS?"
Output: Skill activation plan         Output: Per-request routing plan
Scope: Portfolio strategy             Scope: Single request routing
Horizon: Weeks to months              Horizon: This request, right now
```

Both are mandatory. Neither replaces the other. C-050 decides the skill portfolio. C-054 routes requests within that portfolio.

---

## SQL: Signal Intelligence Layer Tables (v0.35.0)

```sql
-- Signal materiality events — platform-level log of all detected signals
-- No RLS — institutional table, no customer data in signal events
CREATE TABLE institutional.signal_materiality_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type                  VARCHAR(100) NOT NULL,         -- AGRICULTURAL_ADVISOR_INDIA, etc.
    signal_type                 VARCHAR(100) NOT NULL,         -- WEATHER_HAIL_RISK, PRICE_TARGET_CROSSED
    signal_feed_id              VARCHAR(100) NOT NULL,         -- references signal_feed declarations
    materiality_score           DECIMAL(4,3) NOT NULL,
    urgency_class               VARCHAR(20) NOT NULL           CHECK (urgency_class IN ('CRITICAL','HIGH','ADVISORY','BELOW_THRESHOLD')),
    customers_matched           INTEGER NOT NULL DEFAULT 0,
    customers_notified          INTEGER NOT NULL DEFAULT 0,    -- actually sent alert
    customers_deferred          INTEGER NOT NULL DEFAULT 0,    -- outside TRAI window or zero budget
    customers_budget_blocked    INTEGER NOT NULL DEFAULT 0,    -- budget = 0, non-CRITICAL
    signal_payload_hash         VARCHAR(64) NOT NULL,          -- SHA-256 of signal content (no PII)
    signal_region               VARCHAR(200),                  -- district/market/domain (no PII)
    detected_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    workflow_run_id             VARCHAR(200)                   -- Temporal workflow run ID for tracing
);
CREATE INDEX idx_signal_events_type ON institutional.signal_materiality_events(agent_type, signal_type, detected_at DESC);
CREATE INDEX idx_signal_events_urgency ON institutional.signal_materiality_events(urgency_class, detected_at DESC);

-- Skill gap signals — accumulates unserved customer intents per agent
-- Feeds the Agent Skill Proposal Governance Loop (Section 3.20)
CREATE TABLE institutional.skill_gap_signals (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type                  VARCHAR(100) NOT NULL,
    unserviced_intent           TEXT NOT NULL,                 -- what the customer asked (anonymised at source)
    intent_classification       VARCHAR(100),                  -- SIR Layer 1 classification result
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),  -- which customer hit this gap
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    gap_frequency_for_customer  INTEGER NOT NULL DEFAULT 1,    -- how many times THIS customer hit this gap
    similar_intent_hash         VARCHAR(64) NOT NULL,          -- for aggregating similar intents (no PII)
    candidate_skill_type        VARCHAR(100),                  -- SIR best-guess at what skill would serve this
    adjacent_routing_applied    BOOLEAN NOT NULL DEFAULT FALSE,
    skill_proposal_raised       BOOLEAN NOT NULL DEFAULT FALSE, -- true when Section 3.20 Stage 2 triggered
    skill_proposal_issue_id     INTEGER,                       -- GitHub Issue number when raised
    detected_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_skill_gap_agent ON institutional.skill_gap_signals(agent_type, similar_intent_hash);
CREATE INDEX idx_skill_gap_frequency ON institutional.skill_gap_signals(agent_type, detected_at DESC) WHERE skill_proposal_raised = FALSE;

-- Skill collaboration graph — materialized from SCM declarations per customer's active skills
-- Updated when SKILL_ACTIVATION_PLAN runs (C-050) or when SIR detects state change
CREATE TABLE business.agent_skill_graph (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    skill_id                    VARCHAR(100) NOT NULL,
    skill_version               VARCHAR(20) NOT NULL,
    intent_signatures_embedding VECTOR(1536),                  -- pgvector embedding of intent_signatures list
    servable_request_types      JSONB NOT NULL,                -- {REQUEST_TYPE_ID: description}
    unservable_request_types    JSONB,                         -- [{intent, routes_to_skill}]
    output_contributions        JSONB,                         -- [{type, used_by:[]}]
    collaboration_affinities    JSONB,                         -- [{with_skill, relationship, benefit}]
    activation_state            JSONB NOT NULL,                -- {oauth_status, within_budget, current_mode}
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    last_updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id                   UUID NOT NULL,                 -- RLS discriminator
    CONSTRAINT uq_skill_graph_entry UNIQUE (employment_contract_id, skill_id)
);
CREATE INDEX idx_skill_graph_contract ON business.agent_skill_graph(employment_contract_id) WHERE is_active = TRUE;
CREATE INDEX idx_skill_graph_embedding ON business.agent_skill_graph USING ivfflat (intent_signatures_embedding vector_cosine_ops);
```

### SQL: agent_strategic_state

**Authority:** C-050 (Strategic Cognition Obligation — LAW); AD-021 (Strategic Cognition Trigger Points); DP-019 (Portfolio-First Cognition)
**Added:** v0.31.0

The Standard Execution Loop above governs **how an individual skill executes** (micro-level reasoning). The Strategic Cognition Layer governs **which skills execute and why** (macro-level reasoning). Both are mandatory.

```
┌─────────────────────────────────────────────────────────────────────┐
│               STRATEGIC COGNITION LAYER (C-050)                    │
│                                                                     │
│  Operates at a higher cadence than individual skill heartbeats.    │
│  Runs at TRIGGER EVENTS defined in the Professional Template.      │
│                                                                     │
│  TRIGGER EVENT → Strategic Cognition Workflow activates            │
│                                                                     │
│  1. LOAD STRATEGIC CONTEXT                                         │
│     Current skill activation plan (business.agent_strategic_state) │
│     All active skill KPI states (portfolio view)                   │
│     Customer goal and elapsed time                                 │
│     Previous strategic assessment (last assessment date + outcome) │
│                                                                     │
│  2. INVOKE STRATEGIC PROMPT                                        │
│     POST_ONBOARDING / SEASON_START → SKILL_ACTIVATION_PLAN         │
│     PERIODIC_REVIEW / DEVIATION_ALERT / HARVEST → PERFORMANCE_ASSESSMENT│
│                                                                     │
│  3. STRATEGIC REASONING (LLM)                                      │
│     Agent reasons about the WHOLE portfolio:                       │
│     "Given all active skills and the customer's goal, what is      │
│      the current strategic situation and what should change?"      │
│     Output: Strategic Plan (activation sequence, adjustments,      │
│             c050_strategic_intent, c049_honest_assessment)         │
│     Write: Reasoning Trace to institutional.agent_reasoning_traces │
│                                                                     │
│  4. STRATEGIC VALIDATION                                           │
│     CE.ValidateAction for any proposed skill activation changes    │
│     Skill activations → APPROVAL_GATE (customer approves new skill)│
│     Skill deactivations → APPROVAL_GATE (customer confirms)        │
│     Parameter changes → per agent's Decision Space                 │
│                                                                     │
│  5. UPDATE STRATEGIC STATE                                         │
│     Write updated plan to business.agent_strategic_state           │
│     (Replaces previous plan — the current plan is always current)  │
│                                                                     │
│  6. DISPATCH                                                       │
│     Activated skills: new Temporal workflows started per plan      │
│     Deactivated skills: existing workflows signalled to stop       │
│     No-change skills: continue on existing heartbeat schedule      │
│                                                                     │
│  7. CUSTOMER COMMUNICATION (if assessment changed the portfolio)   │
│     If strategic_recommendation = ADJUST or STOP_AND_DISCLOSE:    │
│     → customer_narrative delivered via configured channels         │
│     → wait for customer decision before activating new skills      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Relationship Between the Two Loops

```
Strategic Cognition Loop (C-050)          Standard Execution Loop (C-047)
────────────────────────────────          ───────────────────────────────
Runs at: trigger events                   Runs at: skill heartbeat cadence
Asks: "Which skills? Why?"                Asks: "What action next?"
Output: Strategic plan                    Output: Specific action
Scope: Whole portfolio                    Scope: One skill, one cycle
Frequency: Low (monthly/seasonal/event)  Frequency: High (daily/5-min/per-event)

The Strategic Loop controls WHICH skills the Execution Loop runs.
The Execution Loop governs HOW each skill executes within its heartbeat.
C-050 cannot replace C-047; C-047 cannot satisfy C-050.
Both are mandatory.
```

### SQL: agent_strategic_state

The Strategic Cognition Layer persists its output in `business.agent_strategic_state`:

```sql
-- Added in v0.31.0 migration — see 03-enums-and-tables.sql
CREATE TABLE business.agent_strategic_state (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    professional_type           VARCHAR(100) NOT NULL,
    plan_version                INTEGER NOT NULL DEFAULT 1,  -- increments on each re-plan
    skill_activation_plan       JSONB NOT NULL,              -- full output of SKILL_ACTIVATION_PLAN prompt
    last_performance_assessment JSONB,                       -- full output of PERFORMANCE_ASSESSMENT prompt
    active_skills               TEXT[] NOT NULL,             -- currently active skill IDs
    deferred_skills             JSONB,                       -- [{skill_id, reason, revisit_trigger}]
    portfolio_health            VARCHAR(50),                 -- from last assessment
    strategic_intent            TEXT,                        -- c050_strategic_intent from current plan
    last_plan_date              TIMESTAMPTZ NOT NULL,
    last_assessment_date        TIMESTAMPTZ,
    reasoning_trace_id          UUID REFERENCES institutional.agent_reasoning_traces(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id                   UUID NOT NULL,              -- RLS discriminator
    CONSTRAINT uq_strategic_state_contract UNIQUE (employment_contract_id)
);
CREATE INDEX idx_strategic_state_org ON business.agent_strategic_state(organisation_id);
CREATE INDEX idx_strategic_state_contract ON business.agent_strategic_state(employment_contract_id);
```
