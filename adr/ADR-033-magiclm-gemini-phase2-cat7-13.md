# ADR-033 — MagicLLM Phase 2: Gemini Flash for Cat. 7-13 (Orchestration + Semantic)

**Status:** ACCEPTED
**Date:** 2026-07-27
**Deciders:** Founder (Yogesh Khandge), Enterprise Architect
**Constitutional Basis:** C-059 (Evidence First), C-069 (Self-Improvement), C-077 (Cost Ceiling), C-042 (Vocabulary Mandate), ADR-029 (Multi-Provider LLM Strategy), ADR-030 (Autonomous Sprint Code Generation)

---

## Context

ADR-030 defined MagicLLM as the universal AI execution pipeline for all 13 TaskCategory values. Phase 1 (ADR-030) implemented Cat. 1-6 (Engineering execution) using Anthropic Claude. Cat. 7-13 were stubbed with `NotImplementedError` pending this ADR.

Three gaps drove the Phase 2 design:

1. **Context window**: RepoNav (Cat. 7 — Semantic Understanding) requires reading the entire WAOOAW codebase in a single prompt. Claude Sonnet 4.6 supports ~200K tokens; the repo at current size fits in ~350K tokens. Gemini 2.0 Flash supports 1M tokens natively — the entire repo fits in a single context without chunking.

2. **Cost**: Cat. 9-13 (Orchestration) are high-frequency calls fired on every Goal lifecycle event: Understanding, Routing, Journey Monitor, Research, Decision Synthesis. At Claude Sonnet pricing (₹0.24/1K input) these would be prohibitive. Gemini 2.0 Flash is ~₹0.007/1K input — 34× cheaper. C-077 Cost Ceiling requires minimum-viable spending.

3. **India data residency (DPDPA)**: Vertex AI `asia-south1` (Mumbai) processes and stores data in India. Anthropic's API routes through US infrastructure. For orchestration calls that may contain Goal content (potentially including customer data in future), India residency is required per DPDPA.

---

## Decision

**Cat. 7-13 use `gemini-2.0-flash` on Vertex AI `asia-south1` (Mumbai).**

```
Provider:  Google Cloud — Vertex AI (Gemini Enterprise Agent Platform)
Service:   aiplatform.googleapis.com
Region:    asia-south1 (Mumbai) — India data residency
Model:     gemini-2.0-flash
Auth:      Service Account key — GOOGLE-VERTEX-SA-KEY (Azure Key Vault)
Context:   1M token window — full repo readable in one call (Cat. 7)
Cost:      ₹0.007/1K input · ₹0.021/1K output (34× cheaper than Sonnet)
```

### Category routing table

| Category | Value | Name | Provider | Why |
|---|---|---|---|---|
| 1 | DEEP_REASONING | Architecture analysis | Anthropic Claude | Precise reasoning, code-adjacent |
| 2 | CODE_GENERATION | Source code | Anthropic Claude | Best-in-class code, CCT gates |
| 3 | DESIGN_CONTRACTS | Interface design | Anthropic Claude | Strict format output |
| 4 | REVIEW_EVALUATION | PR review | Anthropic Claude | Precise evaluation |
| 5 | DOCUMENTATION | Docs/ADR | Anthropic Claude | Writing quality |
| 6 | TEST_GENERATION | CCT tests | Anthropic Claude | Code + annotation gate |
| **7** | **SEMANTIC_UNDERSTANDING** | **Codebase analysis** | **Gemini Flash** | **1M context, full repo** |
| **8** | **RESEARCH_QUERY** | **L2 Cascade research** | **Gemini Flash** | **Cost, knowledge breadth** |
| **9** | **GOAL_UNDERSTANDING** | **Parse Founder Goals** | **Gemini Flash** | **Cost, high frequency** |
| **10** | **ROUTING_INTELLIGENCE** | **Institution routing** | **Gemini Flash** | **Cost, high frequency** |
| **11** | **JOURNEY_MONITOR** | **Sprint drift detection** | **Gemini Flash** | **Cost, high frequency** |
| **12** | **RESEARCH_ORCHESTRATION** | **L2 coordinator** | **Gemini Flash** | **Cost, research synthesis** |
| **13** | **DECISION_SYNTHESIS** | **Founder escalation brief** | **Gemini Flash** | **DPDPA, sensitive content** |

### Authentication protocol

The pipeline uses the **OAuth2 JWT Bearer Token** flow (RFC 7523):
1. Load SA key JSON from `GOOGLE_VERTEX_SA_KEY` env var
2. Create signed JWT (`iss`=client_email, `scope`=cloud-platform, RS256)
3. Exchange JWT for OAuth2 access token (`https://oauth2.googleapis.com/token`)
4. Call Vertex AI REST API with `Authorization: Bearer {token}`
5. Token cached in-memory for 55 minutes (expires at 60, refreshed early)

No SDK dependency — implemented via `urllib.request` + `PyJWT` + `cryptography` (already in runtime).

### Quality gates for Cat. 7-13

Cat. 7-13 produce prose/JSON output, not source code files. The annotation gate (C-073) does not apply. Gates applied:
- **FORMAT gate**: non-empty response required
- **JSON gate**: for Cat. 9-13 (JSON output format) — `json.loads()` must succeed
- **Evidence gate**: C-059 — MagicLLMDecisionRecord written BEFORE returning

### No thinking mode

Gemini 2.0 Flash does not have a separate "thinking" mode parameter. The model reasons internally. `_thinking_budget()` is not applied to Gemini calls.

---

## Consequences

**Positive:**
- Cat. 7 (RepoNav Semantic Twin) is now executable — the entire codebase fits in one call
- Cat. 9-13 (GO-Intelligence) fully operational — Goal lifecycle becomes AI-governed end-to-end
- Cat. 8 (Research Query) enables real L2 Cascade — the stub that was skipping to L3 now works
- 34× cost reduction on orchestration calls vs. if they had used Sonnet
- Full DPDPA compliance for orchestration layer

**Negative / Risks:**
- Gemini Flash accuracy on complex reasoning < Gemini Pro — acceptable for Cat. 9-13 (routing/monitoring decisions are reversible by the Cascade)
- Network latency to `asia-south1` from GitHub Actions runner (US-East) adds ~180ms per call — acceptable for non-interactive orchestration
- SA key rotation requires Key Vault update + pipeline restart — mitigated by 55-min token cache (one rotation per day maximum)

**Neutral:**
- Cat. 1-6 continue using Anthropic unchanged
- `retry_with_enhanced_context()` and `retry_with_research_context()` route via `invoke()` — they automatically use Gemini if the original request was Cat. 7-13

---

## ADR Index update

Adds to ADR-INDEX.md: ADR-033 — MagicLLM Phase 2: Gemini Flash Cat. 7-13
