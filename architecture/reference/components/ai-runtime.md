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

## What AI Runtime does NOT do
- Does NOT write to the Constitutional Audit Ledger
- Does NOT make authority decisions
- Does NOT call Business Platform or Constitutional Engine
- Does NOT store state (every request is stateless — context is passed by the caller)
- Does NOT know which customer or professional it is serving — it only knows the Decision Space it was given

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

## Dependencies (updated v0.14.0)
- **LLM Providers** (HTTPS external — OpenAI, Azure OpenAI)
- **PostgreSQL** (pgvector — Creative Standard Profile embeddings, agent_progressive_state, digital_marketing_profiles, digital_marketing_maturity_scores, digital_marketing_needs_heatmap, competitor_snapshots — read only)
- **MCP Integration Layer** (internal network — all servers listed in containers.md MCP Server Inventory)
- **Constitutional Engine** (gRPC — CE.ValidateAction before every MCP tool call per C-041; CE.ValidateAction with budget_remaining parameter before any spend-incurring tool call per C-043 and AD-016)
