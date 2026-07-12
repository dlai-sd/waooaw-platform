# Component Specification: AI Runtime

**Service:** AI Runtime
**Technology:** Python 3.12, FastAPI, httpx (async), provider-specific SDKs (OpenAI, Azure OpenAI), MCP client SDK
**Port:** 5004 (REST, internal only — never exposed externally)
**Owning Office:** Solution Architect (Sprint 004)
**Constitutional Basis:** C-003 (authority licensed — AI never acts beyond Decision Space), C-004 (three systems independent — AI is Capability, not Authority), AD-007 (Runtime Universality), C-040 (domain specialization), C-041 (tool calls governed by Decision Space), ADR-019 (RAG), ADR-020 (MCP)

---

## Responsibility

The LLM gateway and tool execution service. The AI Runtime has no constitutional authority — it executes instructions from Professional Runtime within the Decision Space that Professional Runtime provides. It never writes to any ledger and never makes constitutional decisions.

**The AI Runtime does not govern. The AI Runtime executes.**

## Components

### 1. LLM Gateway
**Responsibility:**
- Receives inference requests from Professional Runtime with: prompt, Decision Space context, and tool list
- Routes to the configured LLM provider (OpenAI, Azure OpenAI — provider configured via env var)
- Applies constitutional prompt wrapper: Decision Space boundaries are injected into system prompt
- Returns generated content to Professional Runtime

**Constitutional prompt injection:**
```python
system_prompt = f"""
You are a digital professional operating within the following Decision Space:
{decision_space.to_constitutional_prompt()}

You may ONLY take actions that are explicitly authorized in this Decision Space.
You may NOT take actions listed as prohibited.
For actions listed as 'always ask': propose the action but do not execute it.
"""
```

**Provider agnosticism:** The LLM provider is selected by the `LLM_PROVIDER` environment variable. The gateway interface does not change when providers change.

### 2. Tool Registry and Executor
**Responsibility:**
- Maintains a registry of available tools per professional type (registered via Decision Space configuration)
- Executes tool calls within the bounds of the Decision Space
- Tools include: web search, social media API posting, calendar API, market data queries, broker API calls
- Every tool call is within a Decision Space — the tool executor validates the tool is in `authorizedActions` before executing

**Tool authorization check:**
```python
if tool_name not in decision_space.authorized_tools:
    raise UnauthorizedToolError(f"{tool_name} is not in the authorized Decision Space")
```

### 3. Creative Standard Enforcer (creative professions only)
**Responsibility:**
- For professional types with a Creative Standard Profile: validates generated content against the profile before returning it to Professional Runtime
- This is a soft validation — it flags deviations, it does not reject them outright (rejection is Professional Runtime's responsibility)
- Learns the Creative Standard Profile over time (embedding comparison using pgvector)

### 4. Decision Space Reasoner
**Responsibility:**
- When asked "would this action be within the Decision Space?" — reasons over the Decision Space and returns a constitutional assessment
- This supports the PAAS engine when edge cases arise that don't match a clear authorized/prohibited rule
- Returns: WITHIN / OUTSIDE / UNCERTAIN with reasoning

### 5. Skill Intelligence Router (SIR) (v0.35.0 — C-054, AD-027, DP-023)
**Responsibility:**
- Executes BEFORE every Execution Loop REASON step when a customer message is the trigger
- Classifies the customer's intent at LOCAL tier (zero LLM cost — rule-based Phase 1; fine-tuned Phase 2)
- Matches classified intent against the customer's active Skill Capability Manifests (`business.agent_skill_graph`)
- Returns a `SIR_RoutingPlan` that specifies: primary_skill, execution_sequence, data_handoffs, combined_approval, gap_detected
- On gap_detected: emits SKILL_GAP_SIGNAL to `institutional.skill_gap_signals`; applies adjacent_professional_routing

**Processing pipeline:**
```python
async def route_customer_request(message: str, customer_context: AgentContext) -> SIRRoutingPlan:
    # Layer 1: Intent classification (LOCAL tier — rule-based / fine-tuned classifier)
    intent = await classify_intent(message, customer_context.agent_type)

    # Layer 2: Skill capability match (vector similarity against active SCMs)
    skill_matches = await match_skills(
        intent, customer_context.employment_contract_id,
        similarity_threshold=0.70
    )

    if not skill_matches:
        await emit_gap_signal(intent, customer_context)  # → institutional.skill_gap_signals
        return SIRRoutingPlan(gap_detected=True, adjacent_routing=get_adjacent_routing(intent))

    # Layer 3: Validate activation state (OAuth, budget, approval mode)
    validated = [s for s in skill_matches if s.activation_state_valid]

    # Layer 4: Build collaboration orchestration plan (dependency order from SCM affinities)
    return build_orchestration_plan(validated, intent)
```

**Cost invariant:** SIR adds ≤ 10ms and ₹0 to every request. It is classification, not LLM reasoning.

### 6. Signal Intelligence Layer — Watch Loop Coordinator (v0.35.0 — C-053, AD-026, DP-022)
**Responsibility:**
- Manages the lifecycle of SignalWatchWorkflows in Temporal — one per signal_type per agent_type
- Receives `PROACTIVE_SIGNAL_{SIGNAL_TYPE}` Temporal signals and injects them into customer AgentExecutionWorkflows
- Evaluates TRAI window status and budget state before forwarding signal to customer workflow
- Logs all signal events to `institutional.signal_materiality_events`

**SignalWatchWorkflow lifecycle management:**
```python
# AI Runtime starts one SignalWatchWorkflow per declared signal_feed per agent_type at platform boot
# These are platform-wide workflows (not per-customer)
async def start_signal_watch_workflows():
    for agent_type in REGISTERED_AGENT_TYPES:
        for feed in agent_type.signal_intelligence.signal_feeds:
            await temporal_client.start_workflow(
                SignalWatchWorkflow,
                id=f"signal-watch-{agent_type.professional_type}-{feed.feed_id}",
                task_queue="signal-watch-queue"
            )
```

**Proactive signal injection:**
```python
@workflow.signal
def proactive_signal_received(self, payload: ProactiveSignalPayload) -> None:
    """Received from SignalWatchWorkflow. Injects signal into customer's execution loop."""
    self._signal_queue.append(payload)
    # Execution loop checks self._signal_queue before sleeping at end of each cycle
```

## RAG Pipeline (v0.9.0 — ADR-019, C-040)

Every inference request is augmented with relevant context retrieved from the three-tier RAG architecture before the LLM generates output. See ADR-019 for the full architecture.

```
1. Tier 1 — Domain Knowledge (WAOOAW IP): top-5 domain knowledge chunks
2. Tier 2 — Customer Context (tenant-isolated pgvector): 3 most similar prior contexts
3. Tier 3 — Platform Intelligence (WAOOAW IP): aggregate performance patterns
   ↓
Prompt = [domain] + [customer context] + [platform patterns] + [task instruction]
   ↓ LLM generates → Creative Standard validates → return
```

**Trading PAAS**: domain knowledge is pre-warmed at session start — zero retrieval latency in the hot path.

## MCP Client (v0.9.0 — ADR-020, C-041)

The AI Runtime is an MCP client. Every external platform action goes through an MCP server. C-041 is enforced before every call: if the tool is not in `decision_space.authorized_tools` → reject. If CE.ValidateAction returns DENY → halt.

**Default deny:** unauthorized tools are never called, no fallback, no exception. See ADR-020 for the full MCP server registry.

## Vocabulary Translation Layer (v0.11.0 — DP-013, C-042, AD-015)

**Activation:** The Vocabulary Translation Layer is activated when the agent's Decision Space configuration contains `vocabulary_mandate: true`. This flag is set by the Business Platform during employment contract formation for all agents with C-042 in their constitutional basis.

**Purpose:** Intercepts every outbound response from the LLM and enforces translation from technical/data vocabulary into the customer's occupational vocabulary. This is a structural enforcement mechanism — not a prompt instruction.

**Processing pipeline:**

```
LLM generates raw response (may contain technical data — this is internal)
    ↓
[Vocabulary Translation Layer — if vocabulary_mandate: true]
    ↓ Step 1: Language detection — confirm target language from farmer_profile.primary_language
    ↓ Step 2: Technical data scan — reject response if: numeric + unit pattern detected (%, °C, mm, hPa, index)
    ↓ Step 3: Translation — invoke domain-vocabulary LLM call with occupational vocabulary prompt
    ↓ Step 4: Output validation — assert no technical data patterns in translated output
    ↓ Step 5: CAL logging — append (raw_response, translated_response, language) to evidence_records
    ↓ Step 6: TTS routing — if interface_channel = 'whatsapp_voice': route to whatsapp-voice-mcp for audio delivery
         ↓ [AD-015: voice-primary delivery path]
Customer receives translated, voice-delivered advisory
```

**Failure handling:** If Step 4 validation fails (translation still contains technical data), the response is REFUSED — a refusal message in farmer vocabulary is delivered instead, and an internal alert is raised. The raw LLM response is logged for review. Under no circumstances does technical data reach the customer.

**Domain vocabulary reference (agricultural advisory, Marathi):**

| Technical Data | Farmer Vocabulary (Marathi example) |
|---|---|
| "Humidity will reach 85% on Thursday" | "गुरुवारी पाऊस पडण्याची शक्यता आहे — सोयाबीन झाकण्याची तयारी ठेवा" |
| "Temperature: 38°C, risk of heat stress" | "उद्या कडक ऊन राहील — सकाळी पाणी द्या, दुपारी शेतात जाऊ नका" |
| "Mandi price: ₹4,200/quintal (MSP: ₹3,950)" | "आज तुमच्या सोयाबीनला सरकारी भावापेक्षा जास्त मिळेल — आता विकणे फायद्याचे आहे" |
| "Pest risk index: 0.72 (HIGH)" | "पुढच्या 3 दिवसांत अळी येण्याची शक्यता आहे — आज फवारणी करा" |

**What the Vocabulary Translation Layer does NOT do:**
- Does NOT translate for agents without `vocabulary_mandate: true`
- Does NOT alter the LLM's internal reasoning or tool call parameters
- Does NOT suppress safety information — if a crop is at risk, the farmer-vocabulary version still conveys urgency
- Does NOT translate language between two literate users (this is not a general translation service)

## Agent Memory Layer (v0.34.0 — C-052, AD-025, DP-021)

**Authority:** C-052 (Context Fidelity, Isolation, Uniqueness — LAW); AD-025 (Real-time Cross-Customer Isolation — HARD); DP-021 (Creative Fingerprint Uniqueness)

The Agent Memory Layer governs how each agent instance loads, maintains, and protects its customer context across sessions. It is the operational expression of C-052. It consists of four sub-components.

---

### M-1. Context Bootstrap Protocol

**Invoked:** At the start of EVERY agent execution cycle — before ANY LLM call.

The agent does NOT start reasoning from scratch each session. It bootstraps from the persisted state of its employment relationship.

```
Context Bootstrap sequence (order is invariant):

1. LOAD DECISION SPACE (versioned — always current)
   → From: business.employment_contracts (decision_space_config JSONB)
   → Validates: version matches what was configured at last session
   → If version changed: mark session with DECISION_SPACE_UPDATED flag

2. LOAD SESSION STATE (what happened last time)
   → From: institutional.agent_reasoning_traces
      (last 5 traces for this employment_contract_id, ordered by created_at DESC)
   → From: business.agent_strategic_state (current plan + portfolio health)
   → From: business.agent_progressive_state (Agricultural: crop state; DMA: maturity score)
   → Purpose: agent knows where it left off — not starting fresh

3. LOAD PERFORMANCE HISTORY (KPI trajectory)
   → From: skill-specific tables (digital_marketing_profiles, trading_session_records, etc.)
   → Window: last 90 days or last 3 review periods (whichever is shorter)
   → Purpose: agent knows if it is performing well or not, before generating advice

4. LOAD CREATIVE FINGERPRINT (content-generating agents only)
   → From: business.customer_creative_fingerprints
   → Includes: voice_embedding, performance_dna, competitor_exclusion_embedding,
               approval_pattern, local_identity
   → Purpose: uniqueness guarantee before any content generation (DP-021)

5. LOAD ACTIVE REDIRECT HOOKS (Token Economy Layer)
   → From: live DB reads (competitor activity, price trends, pending items)
   → Purpose: off-topic deflection hooks pre-fetched (Section 3.17)

6. ASSEMBLE TIER 2 RAG CONTEXT
   → Combine all loaded state into structured Customer Context block
   → This is what the LLM receives as Tier 2 context
   → Structured format ensures agent can cite specific evidence records

BOOTSTRAP COMPLETE — agent is grounded in its customer relationship before reasoning.
```

**Anti-Hallucination Guard (Grounding Rule):**

The assembled Customer Context block is the ONLY source of historical truth the agent may assert. If the agent's reasoning produces a statement about prior customer interactions, it MUST be traceable to a specific record in the Customer Context block. The evidence record ID is cited in the reasoning chain.

```python
# AI Runtime enforces this before returning any LLM output
def validate_historical_assertions(reasoning_output: str, customer_context: CustomerContext) -> bool:
    """
    Scan reasoning_output for any claims about prior customer interactions.
    Every such claim must reference a specific evidence record in customer_context.
    If an assertion cannot be grounded → redact it and log a GROUNDING_VIOLATION.
    """
    assertions = extract_historical_assertions(reasoning_output)
    for assertion in assertions:
        if not customer_context.can_ground(assertion):
            log_grounding_violation(assertion)
            return False  # Trigger re-generation without the ungrounded assertion
    return True
```

A GROUNDING_VIOLATION is logged to `institutional.agent_reasoning_traces` with `grounding_failed: true`. Three grounding violations in a session trigger a CONSTITUTIONAL_ALERT to Platform Operations.

---

### M-2. Cross-Customer Isolation Enforcer

**Invoked:** On every Tier 3 read and write operation.

Tier 3 (Platform Intelligence) is the only data store that aggregates across customers. The Cross-Customer Isolation Enforcer ensures no real-time contamination occurs.

```
TIER 3 READ (LLM context injection):
  Allowed:    Historical aggregate patterns (>24h lag, anonymized)
  Prohibited: Any data tagged with an active session_id
  
TIER 3 WRITE (after session ends):
  Allowed:    Session data AFTER: session closed + 24h elapsed + anonymized
  Prohibited: Writing ANY active session data (positions, pending orders, today's decisions)

ENFORCEMENT MECHANISM:
  Every Tier 3 record carries:
    - session_closed_at: TIMESTAMPTZ
    - anonymized_at: TIMESTAMPTZ  
    - eligible_for_tier3_at: session_closed_at + INTERVAL '24 hours'
    
  AI Runtime Tier 3 query filter (mandatory WHERE clause):
    WHERE eligible_for_tier3_at <= NOW()
    AND session_id != :current_session_id  -- belt-and-suspenders: never read own session
```

**Trading Agent — SEBI Compliance Check (additional):**

Before every PAAS trade execution, a SEBI compliance check verifies:
```python
def sebi_isolation_check(proposed_action: TradeAction, session_context: TradingSessionContext) -> bool:
    """
    Verify this trade decision is not coordinated with any other customer's session.
    This is an architectural invariant — the trading workflow has no mechanism
    to access other sessions. This check verifies the invariant is holding.
    """
    # The only data this session has seen is:
    assert session_context.tier3_sources_all_historic  # no real-time Tier 3
    assert session_context.customer_id == proposed_action.decision_space_owner
    # If either assertion fails → SEBI_ISOLATION_BREACH → halt session, alert platform ops
    return True
```

---

### M-3. Creative Fingerprint Enforcer

**Invoked:** Before any content generation LLM call for content-generating agents (DMA).

```
UNIQUENESS CHECK sequence (before generating any customer-facing content):

1. Load Creative Fingerprint from Context Bootstrap (step 4 above)

2. Generate draft content (LLM call)

3. UNIQUENESS VALIDATION:
   a. Compute semantic similarity: draft vs customer's last 30 days of content
      Threshold: 0.85 → REGENERATE with novelty constraint
   b. Compute semantic similarity: draft vs competitor_exclusion_embedding
      Threshold: 0.75 → REGENERATE with differentiation constraint

4. If 3 regeneration attempts all fail uniqueness checks:
   → Return best-scoring draft
   → Log UNIQUENESS_DEGRADED in evidence record (for human review)
   → Customer is not told about the degradation in the content itself

5. Tag the final content:
   uniqueness_score: 0.0-1.0  (stored in evidence record)
   competitor_differentiation_score: 0.0-1.0
   brand_voice_alignment_score: 0.0-1.0
```

**Fingerprint Update (online learning — after every approval/rejection):**

```python
# Called by AI Runtime after EVERY customer approval or rejection decision
def update_creative_fingerprint(decision: ApprovalDecision, content: GeneratedContent):
    if decision.approved:
        # Reinforce: move voice_embedding toward this content's embedding
        fingerprint.voice_embedding = lerp(fingerprint.voice_embedding, 
                                           content.embedding, alpha=0.1)
        # Record performance DNA signal
        fingerprint.performance_dna.record_success(content.content_type, content.theme)
    else:
        # Rejection: add content embedding to rejection_exclusion_set
        fingerprint.approval_pattern.add_rejection(content.embedding, decision.reason)
```

---

### M-4. Agricultural Timing Stagger

**Invoked:** Before dispatching any outbound agricultural advice that may apply to multiple farmers simultaneously.

When the same action recommendation applies to N farmers in the same district (detected by batch scheduling), delivery is staggered across a 48-hour window using farm ID hash:

```python
def compute_delivery_offset(farm_id: UUID, action_window_hours: int = 48) -> timedelta:
    """
    Deterministic stagger: same farm always gets same offset (predictable for testing)
    but offsets are distributed across the window.
    """
    hash_val = int(hashlib.sha256(farm_id.bytes).hexdigest()[:8], 16)
    offset_minutes = hash_val % (action_window_hours * 60)
    return timedelta(minutes=offset_minutes)

# Result: 1,000 Nagpur cotton farmers who all need to spray Imidacloprid
# receive the alert spread across 48 hours — no artificial demand spike,
# no appearance of mass coordinated messaging.
# Each farmer's alert is still accurate for their specific farm state.
```

---

## What AI Runtime does NOT do
- Does NOT write to the Constitutional Audit Ledger
- Does NOT make authority decisions
- Does NOT call Business Platform or Constitutional Engine
- Does NOT store state (every request is stateless — context is passed by the caller)
- Does NOT know which customer or professional it is serving — it only knows the Decision Space it was given
- **Does NOT access other customers' active session data — Cross-Customer Isolation Enforcer (M-2) enforces this**
- **Does NOT generate content without loading the Creative Fingerprint first (for content agents) — M-3 enforces this**

## New Component (v0.8.0 — C-039, AD-013)

### 5. Conversational Configuration Engine
**Responsibility:**
- Receives natural language input from a customer (during agent onboarding or goal-setting)
- Derives a complete, valid DecisionSpaceInput object from the conversation (C-039)
- Asks clarifying questions when input is ambiguous (e.g., "You said post 3 times a week — which days and times work best for your patients?")
- Translates derived Decision Space back into business language for customer confirmation before committing
- Supports goal refinement: customer can say "that's too much, cut it to 2 times a week" and the engine updates the configuration

**The engine does NOT:**
- Commit the Decision Space itself (it returns a proposed DecisionSpaceInput to Business Platform)
- Make constitutional decisions (what is authorized/prohibited is the customer's choice)
- Accept a configuration that would violate constitutional limits (AD-013: 15-minute completion target)

**Input format:** unstructured natural language (voice transcription or text)
**Output format:** `DecisionSpaceInput` JSON (per business-platform.openapi.yaml schema)

---

## New Components (v0.14.0 — Digital Marketing Agent v2.0, C-039, C-040, C-043, DP-014)

### 6. Customer Profiling Pipeline

**Activation:** Triggered when the active agent skill type is `CUSTOMER_PROFILING`.

**Responsibility:**
- Reads the customer's registration data from `customer-profile-mcp` as the conversation starting point
- Runs an AI-native profiling interview: infer what can be derived from existing data, confirm inferences, ask only what cannot be derived
- Maintains a progressive profile summary card — shown to the customer after every 2 exchanges
- Detects when the minimum viable profile (6 fields confirmed) has been reached and declares completion
- Writes confirmed profile fields to `customer-profile-mcp` (profile.update_field) with source attribution (registration / conversation / inference)
- Marks profile as complete only after explicit customer confirmation (profile.confirm)
- Triggers Market Research Pipeline upon completion (passes business_name + locality as minimum inputs)

**Processing pipeline:**
```
Read registration data (customer-profile-mcp: profile.get_registration)
    ↓
Build opening context: "Here's what I already know: [registration fields]"
    ↓
[Adaptive interview loop]
    ↓ Step 1: For each unconfirmed extended field — infer if possible, else ask
    ↓ Step 2: Every 2 exchanges — show progressive summary card
    ↓ Step 3: Accept corrections → update profile field with source = 'customer_correction'
    ↓ Step 4: Detect deviation → capture as extended field signal, redirect to minimum fields
    ↓ Step 5: Check minimum viable profile completeness after each exchange
    ↓ Step 6: When minimum fields confirmed → present completion summary → customer confirms
    ↓ Step 7: profile.confirm → trigger Market Research Pipeline in parallel
Customer receives: confirmation message + "I am now researching your digital presence..."
```

**Constitutional constraints:**
- Financial questions (ad spend) are always asked last — never before domain, locality, and aspiration are confirmed
- No field may be marked confirmed without customer acknowledgement
- Profile data is Tier 2 customer-private — never crosses tenant boundary

---

### 7. Market Research & Maturity Scoring Pipeline

**Activation:** Triggered when the active agent skill type is `MARKET_RESEARCH`. Runs in parallel with Customer Profiling from the moment business_name + locality are confirmed (does not wait for full profile completion).

**Responsibility:**
- Executes public-data research across 7 axes (digital footprint, social presence, Google Business, paid advertising signals, content quality, competitor landscape, analytics signals)
- Calculates Digital Marketing Maturity Score (1–7) against the fixed scale
- Retrieves industry and geography benchmark from Tier 3 platform intelligence
- Generates Needs Heat Map (8 need states × Active/Latent/N/A × evidence citation)
- Produces the Digital Marketing Maturity Report (score + benchmark + needs map + phase recommendation + 3-month plan)
- Saves score and needs heat map to customer-profile-mcp for downstream skill use
- Delivers report to customer in chat and makes PDF available on portal

**Processing pipeline:**
```
Receive: business_name, locality, domain, [partial extended profile]
    ↓
[Research phase — parallel execution across axes]
    ↓ For each tool call: CE.ValidateAction(tool, decision_space) → PERMIT required before invocation (C-041)
    ↓ web-search-mcp: search "{business_name} {locality}" → footprint signals
    ↓ google-places-mcp: place.get_details → GBP status, review count, rating, response rate
    ↓ social-profile-mcp: profile.get_public_data → social presence, last post, frequency
    ↓ meta-ad-library-mcp: ads.search_active → paid campaign signals
    ↓ web-scan-mcp: page.get_signals → website technical signals (SEO, booking CTA, analytics pixel)
    ↓
[Score calculation]
    ↓ Score each research axis against maturity rubric (1–7 criteria per axis)
    ↓ Composite score = weighted average of axis scores
    ↓ Retrieve benchmark: Tier 3 platform intelligence (avg and P80 for domain+city)
    ↓
[Needs Heat Map]
    ↓ Map research findings to 8 need states → Active / Latent / N/A + evidence citation
    ↓
[Report generation]
    ↓ Assemble Digital Marketing Maturity Report (score, benchmark, needs map, recommendation, 3-month plan)
    ↓ Save: maturity.save_score, needs.save_heatmap (customer-profile-mcp) — Evidence First
    ↓
Customer receives: full report in chat + PDF download link
```

**Constitutional constraints:**
- ONLY publicly available data may be used — all MCP server adapters in this pipeline are public-data-only
- CE.ValidateAction is called before each MCP tool call per C-041
- Every claim in the report must include source URL and retrieval date — no unsourced assertions
- The pipeline must not attempt to access any authenticated endpoint; if a web-scan-mcp call returns a 401/403, it records "access restricted" as the finding, not as an error

**Budget check for spend-tracking research tools:**
- market research tools are read-only and incur no financial spend — AD-016 budget check is NOT applicable to this pipeline

---

## New Components (v0.16.0 — C-044, AD-017, DP-015)

### 8. Synthetic Approval Pipeline

**Activation:** Triggered when a skill has an action to execute AND the skill's `approval_mode` is `SYNTHETIC_APPROVAL` or `EXCEPTION_APPROVAL`.

**Responsibility:**
- Determines whether a pending action qualifies for synthetic approval or requires customer approval
- Computes confidence score via vector similarity between the proposed action and prior approved actions corpus
- Generates the SYNTHETIC_APPROVAL evidence record when confidence threshold is met
- Notifies the customer via configured delivery channels before or at execution
- Manages the override window — holds the action in reversible state until window expires
- Auto-downgrades to EXCEPTION_APPROVAL for any action type where confidence drops below threshold

**Processing pipeline (SYNTHETIC_APPROVAL mode):**
```
Proposed action from skill execution context
    ↓
Step 1: Read skill runtime config → approval_mode, confidence_threshold, min_history
    ↓
Step 2: Retrieve prior approval corpus for this action type (pgvector query)
         → count prior approved actions of same type
         → if count < min_history → FALLBACK to EXCEPTION_APPROVAL → raise approval request
    ↓
Step 3: Compute vector similarity score (proposed action embedding vs corpus of approved action embeddings)
         → if similarity < confidence_threshold → FALLBACK to EXCEPTION_APPROVAL
    ↓
Step 4: CE.ValidateAction(action, decision_space, approval_type=SYNTHETIC, confidence=score)
         → if DENY → FALLBACK to EXCEPTION_APPROVAL
    ↓
Step 5: Write evidence record:
         { event_type: SYNTHETIC_APPROVAL, skill_type, confidence_score,
           basis_approval_ids: [top-5 similar prior approvals], action_description,
           override_deadline: NOW + override_window_hours }
    ↓
Step 6: Notify customer via delivery_channels:
         "I've posted [description] — based on my understanding of your preferences.
          You can review and undo this within [override_window_hours] hours."
    ↓
Step 7: Execute action via MCP tool (CE.ValidateAction already returned PERMIT in Step 4)
    ↓
Step 8: Monitor override window
         → If customer overrides within window: reverse action (where reversible),
           update approval corpus with OVERRIDE signal, check 10% override rate
         → If override rate > 10% in 30 days: propose downgrade to EXCEPTION_APPROVAL
         → If window expires without override: evidence record sealed as confirmed
```

**EXCEPTION_APPROVAL mode (simpler flow):**
```
Proposed action → check if action type is in customer-defined exception list
   → YES (exception): raise approval request to customer (standard APPROVAL_GATE flow)
   → NO (routine): execute within approved content calendar
                   CE.ValidateAction(action, decision_space, approval_type=CALENDAR_AUTHORIZED)
                   Evidence record: { event_type: CALENDAR_AUTHORIZED, calendar_id, action_description }
```

**Constitutional constraints:**
- Synthetic Approval evidence records are immutable (C-007) — the confidence score and basis cannot be altered after creation
- Notification to customer is a REQUIRED step, not DEGRADABLE — if notification fails, the action is held until notification succeeds or the skill falls back to explicit approval request
- The override window is always honoured — no action that is within its override window may be treated as permanently confirmed

---

### 9. Self-Governance and Performance Narrative Pipeline

**Activation:** Triggered on day 15 of each month (pace check) and on the last 3 working days of each month (narrative generation). Also triggered when 2 consecutive monthly goal misses are recorded.

**Responsibility:**
- Day-15 pace check: computes KPI pace vs monthly target; if < 60% → autonomous correction + customer alert
- Month-end narrative: generates one-paragraph plain-language summary of skill performance
- Renders narrative in all configured delivery channel formats (voice via TTS, text, PDF, push)
- 2-month escalation: compiles self-governance log, generates corrective option set, delivers escalation

**Day-15 pace check pipeline:**
```
Retrieve skill KPI data (platform-analytics-mcp or equivalent read-only tool)
    ↓
Compute: (actual_to_date / (days_elapsed / days_in_month)) / monthly_target
    ↓
If pace < 60%:
    → Diagnose root cause (LLM analysis of available signals)
    → Attempt one autonomous correction within Decision Space
       (e.g., adjust posting time, refresh content format, reallocate ad creative budget)
    → Record correction in skill_self_governance_log
    → Send customer alert (WhatsApp text): "I noticed [metric] is tracking low.
       I've tried [correction]. I'll update you at month end."
```

**Month-end narrative pipeline:**
```
Retrieve full month KPI data for this skill
    ↓
Generate narrative (LLM call with structured prompt):
    - What happened (goal vs actual in business language)
    - What I learned (one insight)
    - What I tried (autonomous corrections taken)
    - What changes next month (proposed plan)
    - What I need from you (one decision, if any)
    ↓
Render to all configured delivery channels:
    - WhatsApp voice: TTS → whatsapp-voice-mcp (or whatsapp-business-mcp audio)
    - WhatsApp text: condensed 3-bullet version
    - Email PDF: structured report with supporting data
    - Portal: full interactive version
    - Push: summary notification
    ↓
Record narrative delivery in skill_performance_records
```

**2-month escalation pipeline:**
```
Detect: 2 consecutive months where actual < goal_target for this skill
    ↓
Compile escalation package:
    (a) Months 1+2 corrections tried (from skill_self_governance_log)
    (b) Root cause diagnosis (LLM analysis)
    (c) 2-3 corrective options with recommendation
    ↓
Deliver escalation via all channels (priority: WhatsApp voice first)
    ↓
Await customer option selection (raises approval request in Business Platform)
    ↓
Apply selected option; write new goal baseline to skill_performance_records
    ↓
Reset consecutive miss counter
```

---

## New Components (v0.20.0 — C-045, C-047, AD-018, AD-019, DP-016, DP-018)

### 10. Prompt Registry (AD-018, C-045)

**Responsibility:**
- At startup: load all active prompt versions from `agent_prompt_versions` table into memory cache
- Expose: `get_active(skill_type, pipeline_step) → Prompt | None`
- If None: the AI Runtime must return INFERENCE_BLOCKED — missing approved prompt is a constitutional gap
- On prompt version activation (DB update): invalidate cache entry and reload
- Never hardcode prompts in application code — all prompts come from this registry

**Implementation note:** The prompt registry is a startup-time dependency. If the DB is unavailable at startup, the AI Runtime fails to start (prompts are required, not optional).

---

### 11. Agent Execution Loop Coordinator (C-047, AD-019, DP-018)

**Responsibility:**
- Implements the standard Agent Execution Loop (see architecture/reference/agent-execution-loop.md)
- Provides the `agent_reasoning_and_execution_activity` Temporal activity implementation
- Orchestrates: Prompt Registry → RAG Pipeline → LLM reasoning → Reasoning Trace write → CE.ValidateAction → MCP execution → Evidence recording → Outcome observation
- The agent's reasoning output (from the LLM) determines what action is taken — the coordinator does NOT make decisions; it executes the agent's decisions durably

**Key constraint (DP-018):** Every agent activity in the Professional Runtime that touches the AI Runtime must begin with an LLM reasoning call. Activities that skip reasoning and go directly to MCP tool calls are DP-018 violations. Code review must catch this.

---

### 12. Reasoning Trace Writer (C-047, AD-008)

**Responsibility:**
- Writes `agent_reasoning_traces` records after every LLM inference, before CE.ValidateAction
- Produces the OTel span with agent-specific attributes (confidence_score, constitutional_basis, prompt_version, action_type)
- Updates the trace with outcome data (evidence_id, action_taken, customer_override) after execution
- Exposes the reasoning trace ID for downstream CE.ValidateAction calls

**This is the primary audit artifact for AI agent operations.** Every AI decision must have a reasoning trace. A decision without a trace is constitutionally ungoverned.

---

### 10. Campaign Theme Engine Pipeline (v0.39.0 — C-055, AD-028, DP-024)

**Responsibility:**
- Manages the three-level Campaign Theme Cascade for multi-post, multi-platform content agents
- Executes the Campaign Brief proposal, weekly theme cascade generation, and platform content variant creation
- Coordinates the Synthetic Content Reviewer (SCR) pipeline before any content auto-publication
- Maintains the `business.content_campaigns`, `business.campaign_weekly_themes`, `business.campaign_content_items`, and `business.scr_review_records` tables

**Campaign Theme Engine execution sequence:**
```python
# Phase 1: Campaign Brief Proposal (customer-triggered or strategic cadence)
async def propose_campaign_brief(customer_context: AgentContext) -> CampaignBrief:
    # Load Platform Intelligence (from agent_skill_graph + customer profile)
    platform_mix = await load_approved_platform_mix(customer_context.employment_contract_id)
    # FRONTIER tier — BREAKING class prompt (campaign strategy is constitutional quality)
    brief = await llm_gateway.infer(
        prompt_id="DMA/CAMPAIGN/MASTER_THEME_PROPOSAL",
        context={**customer_context, "platform_mix": platform_mix, "season": current_month()},
        model_tier="FRONTIER"
    )
    # Store as DRAFT — awaits customer approval
    await db.content_campaigns.insert({**brief, "status": "DRAFT"})
    return brief  # Presented to customer for approval

# Phase 2: Weekly Theme Cascade (runs when campaign status transitions to ACTIVE)
async def generate_weekly_cascade(campaign_id: UUID) -> list[WeeklyTheme]:
    campaign = await db.content_campaigns.get(campaign_id)
    themes = []
    for week in range(1, campaign.campaign_weeks + 1):
        theme = await llm_gateway.infer(
            prompt_id="DMA/CAMPAIGN/WEEKLY_THEME_CASCADE",
            context={"campaign": campaign, "week_number": week},
            model_tier="MID_TIER"
        )
        await db.campaign_weekly_themes.insert(theme)
        themes.append(theme)
    return themes  # All generated upfront; no customer touchpoint needed

# Phase 3: Platform Content Variant generation (runs per scheduled_at datetime)
async def generate_content_variant(weekly_theme_id: UUID, platform: str) -> ContentItem:
    weekly_theme = await db.campaign_weekly_themes.get(weekly_theme_id)
    variant = await llm_gateway.infer(
        prompt_id="DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT",
        context={
            "weekly_theme": weekly_theme,
            "platform": platform,
            "brand_voice": await load_creative_fingerprint(weekly_theme.organisation_id),
            "platform_format": get_platform_format_spec(platform)
        },
        model_tier="MID_TIER"
    )
    item = await db.campaign_content_items.insert({**variant, "scr_status": "PENDING"})
    # Immediately pass to SCR
    return await scr_pipeline.review(item)
```

### 11. Synthetic Content Reviewer (SCR) (v0.39.0 — C-055)

**Responsibility:**
- Runs 5 structured quality checks on every content item before auto-publication
- Checks 1–4 run at LOCAL tier (embedding similarity + rule-based); Check 5 runs at MID_TIER
- Records complete check results in `business.scr_review_records`
- Sets `campaign_content_items.scr_status` to `SCR_PASSED`, `SCR_FAILED`, or `COMPLIANCE_VIOLATION`
- `COMPLIANCE_VIOLATION` (Check 3 failure) always routes to customer — never silent

**SCR pipeline:**
```python
async def review(content_item: ContentItem) -> ContentItem:
    campaign = await db.content_campaigns.get(content_item.campaign_id)
    weekly_theme = await db.campaign_weekly_themes.get(content_item.weekly_theme_id)
    fingerprint = await db.customer_creative_fingerprints.get(content_item.organisation_id)

    results = {}

    # Check 1: Theme Fidelity (LOCAL — embedding similarity)
    content_embedding = await embed(content_item.content_body)
    theme_embedding = await embed(f"{weekly_theme.sub_theme} {weekly_theme.narrative_hook}")
    results["SCR_1"] = cosine_similarity(content_embedding, theme_embedding) >= 0.80

    # Check 2: Brand Voice (LOCAL — Creative Fingerprint comparison)
    results["SCR_2"] = cosine_similarity(content_embedding, fingerprint.voice_embedding) >= 0.75

    # Check 3: Compliance (LOCAL — rule-based against RAG Tier 1 advertising standards)
    violations = await check_advertising_compliance(content_item, campaign.domain)
    results["SCR_3"] = len(violations) == 0
    compliance_violations = violations  # Carried to evidence record

    # Check 4: Uniqueness (LOCAL — C-052 Creative Fingerprint checks)
    competitor_sim = cosine_similarity(content_embedding, fingerprint.competitor_exclusion_embedding)
    own_recency_sim = await max_similarity_to_recent_content(content_embedding, content_item.organisation_id, days=30)
    results["SCR_4"] = competitor_sim < 0.75 and own_recency_sim < 0.85

    # Check 5: Quality (MID_TIER — LLM quality assessment)
    quality_score = await llm_gateway.infer(
        prompt_id="DMA/CAMPAIGN/SCR_QUALITY_CHECK",
        context={"content": content_item, "platform": content_item.platform, "campaign": campaign},
        model_tier="MID_TIER"
    )
    results["SCR_5"] = quality_score.overall_score >= 0.80

    # Record all results
    await db.scr_review_records.insert({
        "content_item_id": content_item.id,
        "check_results": results,
        "compliance_violations": compliance_violations,
        "quality_score": quality_score,
        "reviewed_at": now()
    })

    all_pass = all(results.values())

    if results["SCR_3"] is False:
        # Compliance violation — ALWAYS routes to customer, never retried automatically
        await db.campaign_content_items.update(content_item.id, scr_status="COMPLIANCE_VIOLATION")
        await notify_customer_scr_failure(content_item, "COMPLIANCE", compliance_violations)
    elif all_pass:
        await db.campaign_content_items.update(content_item.id, scr_status="SCR_PASSED")
        # Auto-publish via scheduling-mcp (if customer is in CAMPAIGN_APPROVAL or CAMPAIGN_AUTO mode)
        if content_item.approval_mode in ("CAMPAIGN_APPROVAL", "CAMPAIGN_AUTO"):
            await scheduling_mcp.schedule_publish(content_item)
    else:
        # Regenerate up to 2 times, then route to customer
        failed_checks = [k for k, v in results.items() if not v]
        if content_item.regeneration_attempts < 2:
            return await regenerate_and_recheck(content_item, failed_checks)
        else:
            await db.campaign_content_items.update(content_item.id, scr_status="SCR_FAILED")
            await notify_customer_scr_failure(content_item, "QUALITY", failed_checks)

    return content_item
```

---

## Dependencies (updated v0.20.0)
- **LLM Providers** (HTTPS external — OpenAI, Azure OpenAI)
- **Prompt Registry** (DB at startup → memory cache at runtime; `agent_prompt_versions` table)
- **PostgreSQL** (pgvector — Creative Standard Profile embeddings, agent_progressive_state, digital_marketing_profiles, digital_marketing_maturity_scores, digital_marketing_needs_heatmap, competitor_snapshots, `agent_reasoning_traces` write, `agent_capability_registry` write — institutional schema)
- **MCP Integration Layer** (internal network — all servers listed in containers.md MCP Server Inventory)
- **Constitutional Engine** (gRPC — CE.ValidateAction before every MCP tool call per C-041; CE.ValidateAction with budget_remaining parameter before any spend-incurring tool call per C-043 and AD-016; CE.ValidateAction with reasoning_trace_id for EvaluatePolicy cases per C-047)
- **Agent Reasoning Trace store** (institutional.agent_reasoning_traces — write at every LLM inference)
- **LLM Providers** (HTTPS external — OpenAI, Azure OpenAI)
- **PostgreSQL** (pgvector — Creative Standard Profile embeddings, agent_progressive_state, digital_marketing_profiles, digital_marketing_maturity_scores, digital_marketing_needs_heatmap, competitor_snapshots — read only)
- **MCP Integration Layer** (internal network — all servers listed in containers.md MCP Server Inventory)
- **Constitutional Engine** (gRPC — CE.ValidateAction before every MCP tool call per C-041; CE.ValidateAction with budget_remaining parameter before any spend-incurring tool call per C-043 and AD-016)
