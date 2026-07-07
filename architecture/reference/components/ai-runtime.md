# Component Specification: AI Runtime

**Service:** AI Runtime
**Technology:** Python 3.12, FastAPI, httpx (async), provider-specific SDKs (OpenAI, Azure OpenAI)
**Port:** 5004 (REST, internal only — never exposed externally)
**Owning Office:** Solution Architect (Sprint 004)
**Constitutional Basis:** C-003 (authority licensed — AI never acts beyond Decision Space), C-004 (three systems independent — AI is Capability, not Authority), AD-007 (Runtime Universality)

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

## What AI Runtime does NOT do
- Does NOT write to the Constitutional Audit Ledger
- Does NOT make authority decisions
- Does NOT call Business Platform or Constitutional Engine
- Does NOT store state (every request is stateless — context is passed by the caller)
- Does NOT know which customer or professional it is serving — it only knows the Decision Space it was given

## Dependencies
- **LLM Providers** (HTTPS external — OpenAI, Azure OpenAI)
- **PostgreSQL** (pgvector — Creative Standard Profile embeddings, read only)
- **External APIs** (social media, broker, market data — called via Tool Executor)
