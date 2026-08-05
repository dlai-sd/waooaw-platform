# Anthropic Agent Skills — WAOOAW Implementation Analysis

**Date:** 2026-08-05  
**Author:** GitHub Copilot (research session)  
**Reference:** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview  
**Constitutional basis:** C-059 (Implementation Traceability), ADR-020 (MCP Integration Pattern)

---

## 1. What Anthropic "Agent Skills" Are

Anthropic Agent Skills are **infrastructure-layer execution capabilities** injected into a Claude API call:

| Skill | What it does |
|---|---|
| `web_search` | Real-time internet search with citation |
| `code_execution` | Python execution in an Anthropic-managed sandbox |
| `file_reading` / `file_writing` | Read/write files from a provided context |
| `computer_use` | GUI control (browser, desktop) — beta |

These are distinct from user-defined `tools[]` — they are Anthropic-hosted, pre-built implementations. Claude decides autonomously when to invoke them during inference.

---

## 2. Naming Collision — Critical Disambiguation

| Term | Layer | Definition |
|---|---|---|
| WAOOAW "Skill" (C-036) | Constitutional / Business | A professional capability unit (e.g., "Portfolio Rebalancing Skill"). Constitutional unit with approval mode, cadence, C-049 disclosure obligations. |
| Anthropic "Agent Skill" | Infrastructure | A technical execution capability given to Claude at API call time (web_search, code_execution). |

These are **two completely different layers**. Spec authors MUST NOT conflate them. In agent specs and ADRs, "Skill" always refers to the C-036 business-level unit.

---

## 3. Constitutional Governance Tension

**C-041 (absolute): `CE.ValidateAction` must run BEFORE every tool call, including at Tier 0.**

Anthropic Agent Skills are invoked **mid-inference** by Claude — there is no API-level interception point where CE.ValidateAction can run before the call is dispatched.

**Resolution:** Anthropic Agent Skills must be consumed only through MCP wrappers (ADR-020 pattern), never injected directly into the `tools[]` array of an API call.

```
Anthropic Agent Skill (web_search, code_execution)
        ↓ wrapped as
{skill}-mcp  (MCP server — ADR-020 pattern)
        ↓ governed by
CE.ValidateAction (C-041)  ← constitutional gate preserved
        ↓ dispatched by
AI Runtime (MCP client — ADR-020)
```

This preserves the single integration boundary and makes governance consistent regardless of whether the underlying tool is Anthropic-provided or platform-built.

---

## 4. Greenfield vs BAU — Where Value Lies

### Greenfield (current phase)
Quality is driven by spec richness, thinking budget (O-03), and PTR accuracy. Agent Skills do not improve code generation output quality — caching is transparent to model reasoning. Skills add infrastructure complexity with minimal benefit at this stage.

### BAU (production agents — target phase)

In BAU, agents operate in a continuously-changing world. Web search becomes structurally necessary for several agent types. The quality mechanism:

**Context anchoring across a defect cycle:** A single fix often requires 4 related files. Without a shared context anchor, each LLM call reconstructs context independently — subtle differences can produce inconsistent interfaces between files. Cached constitutional context (constitutional preamble + PTR + interface contracts) ensures all calls reason from an identical foundation.

**Enabling evidence-backed claims (C-001):** `code_execution` for the Platform IT Expert agent means it can run its proposed fix in a sandbox, observe actual output, and revise before presenting. This is "test your hypothesis before claiming it's correct" — direct implementation of Evidence First.

---

## 5. Use Case Fit by Agent Type

### High Fit (BAU, customer-facing agents)

| Agent | Skill | What it replaces / enables |
|---|---|---|
| Digital Marketing Agent (INST-007) | `web_search` | Trend monitoring, competitor analysis, hashtag research — replaces per-platform scrapers |
| Agricultural Advisor | `web_search` | Real-time MSP, weather, government scheme data — no custom data feed MCP needed |
| Private Tutor | `web_search` | Current syllabus, recent exam patterns, regulatory updates |
| Trading Agent | `web_search` | News sentiment enrichment (strict CE.ValidateAction gate — price-sensitive data) |
| Platform IT Expert | `code_execution` | Self-test proposed fixes before presenting; Evidence First compliance |

### Moderate Fit (internal development pipeline)

| Component | Skill | What it replaces |
|---|---|---|
| GoalExecutor COMPILE gate | `code_execution` | `subprocess.run(["ruff", ...])` + `py_compile` — eliminates external subprocess dependency in GHA |
| Self-Improvement Analyst | `code_execution` | Running CCT suites during self-analysis cycles |

### Low Fit (defer)

- **Computer use:** High governance complexity; audit trail is hard to maintain; defer until Platform Phase 2+ UI testing
- **Direct file reading:** WAOOAW controls context injection via `ContextBuilder` — autonomous file access bypasses spec-scoped context controls

---

## 6. Implementation Pattern

### Step 1: MCP Wrapper

For each Anthropic Agent Skill to be used, create an MCP server wrapper:

```
architecture/reference/containers.md  →  add anthropic-web-search-mcp entry
docker-compose.yml                    →  add stub
ADR-020                               →  add paragraph covering Anthropic-provided skills as MCP class
```

The MCP wrapper intercepts the call, applies CE.ValidateAction, then delegates to the Anthropic Agent Skills API.

### Step 2: Decision Space Authorization

Per C-041, every tool call requires a Decision Space entry in the agent spec:

```yaml
# Section 3.14 — Skill Runtime Configuration
skill_name: "Market Research Skill"
mcp_tools:
  - tool: web_search
    mcp_server: anthropic-web-search-mcp
    action: search
    authorization: "Decision Space §3.2 — Market Research authorized at Tier 1+"
    failure_mode: DEGRADABLE
```

### Step 3: Evidence Recording

The `MagicLLMDecisionRecord` already captures tool invocations. Extend `context_strategy` field to log when Agent Skill calls are made within an inference, satisfying C-059.

---

## 7. First Target: `anthropic-web-search-mcp`

Highest BAU value, lowest implementation risk. Target agents: Digital Marketing, Agricultural Advisor, Private Tutor.

Acceptance criteria:
- CE.ValidateAction runs before every web_search call
- Search results injected into agent context as a new `context_section` (not raw) to avoid prompt injection
- C-049 disclosure when web_search fails (agent discloses it is working without current data)
- Audit record written to `constitutional.audit_records` after every search

### Prompt Injection Risk

Web search results are untrusted external content. They must be **sanitized and summarized** before injection into the agent prompt — never injected raw. The MCP wrapper must run a sanitization pass (stripping markup, capping at 2,000 chars/result) before returning to the AI Runtime.

---

## 8. ADR Action Required

**ADR-020 amendment**: Add a section explicitly covering Anthropic Agent Skills as a class of MCP server, with a note that direct `tools[]` injection into API calls is architecturally prohibited (C-041 violation). This should be implemented before any Agent Skills MCP wrapper is built.

---

## 9. Timeline Recommendation

| Phase | Action |
|---|---|
| Now (greenfield) | No action — ANNOTATION fix has higher ROI |
| BAU preparation | ADR-020 amendment + `anthropic-web-search-mcp` wrapper spec |
| BAU Phase 1 | Deploy web_search for Digital Marketing + Agricultural Advisor agents |
| BAU Phase 2 | `code_execution` for Platform IT Expert agent |
| Future | Computer use for automated UI testing |
