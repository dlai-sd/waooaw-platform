# Agent Reasoning Trace Specification

**Authority:** C-047 (Agent-Driven Execution); C-045 (Prompt as Constitutional Artifact); AD-008 (Constitutional Auditability); AD-019 (Agent-Driven Orchestration)
**Date:** 2026-07-09
**Purpose:** Defines the structure, storage, and query interface for agent reasoning traces — the primary artifact of AI-native agent execution. Every LLM inference that drives an agent decision produces a reasoning trace.

---

## What a Reasoning Trace Is

A reasoning trace is the record of an AI agent's decision-making process — not just the decision, but the reasoning that produced it. It answers: What did the agent know? What did it consider? What constitutional basis did it invoke? How confident was it? What did it decide not to do, and why?

A reasoning trace is distinct from an evidence record (which records WHAT happened). The reasoning trace records WHY the agent decided to make it happen.

**The relationship:**
```
Reasoning Trace → produces → Action Decision
Action Decision → validated by → CE.ValidateAction
Validation passes → creates → Evidence Record (PROPOSED)
Evidence Record → drives → Execution
Execution → creates → Evidence Record (EXECUTED)

Reasoning Trace is linked to Evidence Record via action_instance_id.
Both are immutable. Neither can be altered after creation.
```

---

## Reasoning Trace Schema

```sql
-- Table: institutional.agent_reasoning_traces
-- Schema: institutional (WAOOAW IP — not tenant-scoped)
-- Retention: permanent (constitutional auditability)
-- Access: AI Runtime writes; Platform Operations Agent reads; CE reads for EvaluatePolicy
CREATE TABLE institutional.agent_reasoning_traces (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Linkage
    action_instance_id      UUID,                  -- links to constitutional.evidence_records
    contract_id             UUID NOT NULL,          -- Employment Contract context
    organisation_id         UUID NOT NULL,          -- tenant (for operational queries)
    skill_type              VARCHAR(100) NOT NULL,
    pipeline_step           VARCHAR(100) NOT NULL,  -- which pipeline step produced this trace
    -- Prompt governance (C-045, AD-018)
    prompt_id               VARCHAR(100) NOT NULL,  -- references agent_prompt_versions.prompt_id
    prompt_version          VARCHAR(20) NOT NULL,   -- e.g., "2.1.0"
    -- Context loaded (what the agent knew when it reasoned)
    context_summary         JSONB NOT NULL,
    -- {
    --   "tier1_chunks": ["dental_hygiene_india_v3", ...],
    --   "tier2_context_ids": ["prior_approval_uuid_1", ...],
    --   "tier3_benchmarks": ["dental_pune_q2_2026"],
    --   "customer_profile_version": "v4",
    --   "decision_space_version": 3
    -- }
    -- The reasoning itself
    reasoning_chain         TEXT NOT NULL,          -- the agent's chain-of-thought (raw LLM output before structured parsing)
    decision                JSONB NOT NULL,
    -- {
    --   "action_type": "INSTAGRAM_POST",
    --   "action_parameters": {...},
    --   "constitutional_basis": "C-036; C-041",
    --   "confidence_score": 0.91,
    --   "alternatives_considered": [...],
    --   "why_alternatives_rejected": "...",
    --   "next_action_after_this": "wait_for_approval"
    -- }
    -- Quality signals
    confidence_score        NUMERIC(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    constitutional_basis    TEXT NOT NULL,          -- claims/drivers cited in the reasoning
    -- LLM telemetry
    llm_model               VARCHAR(50) NOT NULL,   -- e.g., "gpt-4o", "claude-3-5-sonnet"
    llm_provider            VARCHAR(30) NOT NULL,   -- "openai", "anthropic", "azure_openai"
    tokens_input            INTEGER NOT NULL,
    tokens_output           INTEGER NOT NULL,
    latency_ms              INTEGER NOT NULL,
    -- Outcome tracking (filled in after execution)
    outcome_action_taken    VARCHAR(100),           -- what actually happened
    outcome_evidence_id     UUID,                   -- the resulting evidence_record id
    customer_override       BOOLEAN,                -- did customer override this decision?
    override_reason         TEXT,
    -- Temporal
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for operational queries
CREATE INDEX idx_reasoning_contract ON institutional.agent_reasoning_traces(contract_id, created_at DESC);
CREATE INDEX idx_reasoning_skill ON institutional.agent_reasoning_traces(skill_type, pipeline_step);
CREATE INDEX idx_reasoning_confidence ON institutional.agent_reasoning_traces(confidence_score) WHERE confidence_score < 0.80;
CREATE INDEX idx_reasoning_prompt ON institutional.agent_reasoning_traces(prompt_id, prompt_version);
CREATE INDEX idx_reasoning_action ON institutional.agent_reasoning_traces(action_instance_id) WHERE action_instance_id IS NOT NULL;
CREATE INDEX idx_reasoning_override ON institutional.agent_reasoning_traces(customer_override) WHERE customer_override = TRUE;
```

---

## Reasoning Trace Production (AI Runtime)

Every LLM call in every pipeline must:
1. Load the approved prompt from `agent_prompt_versions` (AD-018)
2. Assemble context (Tier 1 + Tier 2 + Tier 3 RAG, Decision Space, customer profile)
3. Make the LLM call with a structured output schema that includes `reasoning_chain` and `decision`
4. Parse the structured output
5. Write the reasoning trace to `institutional.agent_reasoning_traces` BEFORE calling CE.ValidateAction
6. Pass the `reasoning_trace_id` to CE.ValidateAction as context

**Code pattern (every agent activity):**
```python
async def agent_reasoning_activity(context: AgentContext) -> AgentDecision:
    # Step 1: Load approved prompt (AD-018 — never hardcode)
    prompt = await prompt_registry.get_active(
        skill_type=context.skill_type,
        pipeline_step=context.pipeline_step
    )
    if prompt is None:
        raise InferenceBlockedError(f"No approved prompt for {context.skill_type}/{context.pipeline_step}")

    # Step 2: Assemble context
    rag_context = await rag_pipeline.retrieve(context)

    # Step 3: LLM call with structured reasoning output schema
    llm_response = await llm_client.complete(
        system=prompt.system_context,
        user=prompt.build_user_message(context, rag_context),
        response_format=AgentReasoningOutput,  # structured output schema
    )

    # Step 4: Write reasoning trace BEFORE any action (C-047)
    trace_id = await reasoning_trace_store.write(
        action_instance_id=context.action_instance_id,
        contract_id=context.contract_id,
        organisation_id=context.organisation_id,
        skill_type=context.skill_type,
        pipeline_step=context.pipeline_step,
        prompt_id=prompt.prompt_id,
        prompt_version=prompt.version,
        context_summary=rag_context.summary(),
        reasoning_chain=llm_response.reasoning_chain,
        decision=llm_response.decision,
        confidence_score=llm_response.decision.confidence_score,
        constitutional_basis=llm_response.decision.constitutional_basis,
        llm_model=llm_response.model,
        tokens_input=llm_response.usage.input_tokens,
        tokens_output=llm_response.usage.output_tokens,
        latency_ms=llm_response.latency_ms,
    )

    # Step 5: CE.ValidateAction with reasoning_trace_id as context
    ce_response = await ce_client.ValidateAction(
        ValidateActionRequest(
            contract_id=context.contract_id,
            action_type=llm_response.decision.action_type,
            action_parameters=json.dumps(llm_response.decision.action_parameters),
            decision_space_version=context.decision_space_version,
            reasoning_trace_id=trace_id,  # new field in proto
        )
    )

    return AgentDecision(
        action_type=llm_response.decision.action_type,
        action_parameters=llm_response.decision.action_parameters,
        confidence_score=llm_response.decision.confidence_score,
        reasoning_trace_id=trace_id,
        ce_validation=ce_response,
    )
```

---

## Reasoning Trace Query API (Platform Operations Agent)

The L1/L2/L3 Platform Operations Agent queries reasoning traces to detect operational patterns:

```
GET /api/v1/platform/reasoning-traces/quality-summary
  ?contract_id=...&skill_type=...&days=30
  → Returns: avg_confidence, p10_confidence, override_rate, inference_blocked_count

GET /api/v1/platform/reasoning-traces/anomalies
  ?confidence_threshold=0.75&days=7
  → Returns: traces where confidence < threshold + outcome data

GET /api/v1/platform/reasoning-traces/constitutional-coverage
  ?skill_type=...&days=30
  → Returns: which claims/drivers were cited in agent reasoning, coverage gaps
```

---

## OpenTelemetry Integration (ADR-009 + Reasoning Trace)

Every reasoning trace also emits an OTel span:

```python
span.set_attributes({
    "agent.skill_type": context.skill_type,
    "agent.pipeline_step": context.pipeline_step,
    "agent.prompt_id": prompt.prompt_id,
    "agent.prompt_version": prompt.version,
    "agent.confidence_score": llm_response.decision.confidence_score,
    "agent.constitutional_basis": llm_response.decision.constitutional_basis,
    "agent.action_type": llm_response.decision.action_type,
    "agent.tokens_input": llm_response.usage.input_tokens,
    "agent.tokens_output": llm_response.usage.output_tokens,
    "llm.model": llm_response.model,
    "reasoning_trace.id": trace_id,
})
```

This makes reasoning traces queryable via Jaeger/Azure Monitor AND via the `agent_reasoning_traces` SQL table — two complementary query paths for operational use.
