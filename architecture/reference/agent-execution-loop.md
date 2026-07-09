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
