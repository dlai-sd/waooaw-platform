# Work Contract 015 — IB-009 Sprint 015: AI Runtime Skeleton

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 015
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5)
**Sprint Track:** Track 5 — AI Runtime (PMO §2.1 M6)
**Gate:** G5
**Reviewer:** WAOOAW AI Agent — QA
**Constitutional Basis:** C-051 (Token Economy), C-062 (AI Security), C-063 (Data Minimisation), C-059, C-065, C-076

**Depends on:** WC-014 complete (PR calls AIR for LLM dispatch)
**Authorization:** Requires `platform_phase: IMPLEMENTATION`

---

## Sprint Goal

Produce a running Python 3.12 FastAPI service for the AI Runtime that:
1. Provider Selection Engine (PSE): routes to correct LLM tier (ADR-029)
2. LLM dispatch: calls Ollama (dev) via PSE — real inference in dev environment
3. RAG retrieval: pgvector similarity search stub (returns top-3 chunks)
4. Prompt injection defence: 50-attack test suite passes 100% (C-062)
5. Unit test coverage ≥90% (C-076)

**Dev model:** Ollama (llama3.2 or gemma3) running in docker-compose. No cloud API needed for Sprint 015.
**Note:** FA-021 (GCP Vertex AI) unlocks production-quality inference in Sprint 019+. Not needed now.

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| AIR component spec | `architecture/reference/components/ai-runtime.md` | ✅ EXISTS |
| ADR-019 (RAG) | `adr/ADR-019-rag-architecture.md` | ✅ EXISTS |
| ADR-020 (MCP) | `adr/ADR-020-mcp-integration-pattern.md` | ✅ EXISTS |
| ADR-024 (Token Economy) | `adr/ADR-024-token-economy-model-tier-routing.md` | ✅ EXISTS |
| ADR-029 (Multi-provider LLM) | `adr/ADR-029-multi-provider-llm-strategy.md` | ✅ EXISTS |
| PSE performance schema | `infrastructure/postgres/init/08-provider-performance.sql` | ✅ EXISTS |
| Prompt injection suite | `tests/conftest.py` (50 attack patterns) | ✅ EXISTS |
| WC-014 (PR running) | `src/professional-runtime/` | ⏳ PENDING WC-014 |

**Readiness: BLOCKED** — WC-014 must complete first

---

## Tasks

### WC015-01 — Python 3.12 AIR project scaffold + PSE routing

**Scope:** `src/ai-runtime/` FastAPI. PSE: LOCAL→MID→FRONTIER→FALLBACK tiers (ADR-029). Ollama=LOCAL in dev.
**model_hint:** `reasoning`
**Constitutional check:** C-051 — 66-74% cost reduction via routing. No direct FRONTIER calls for LOCAL-capable tasks.

### WC015-02 — LLM dispatch + real Ollama inference

**Scope:** Call Ollama (docker-compose `ollama` service). Parse response. Record to `institutional.provider_dispatch_events`.
**model_hint:** `reasoning`
**Constitutional check:** C-063 — no PII in prompt. ADR-028 — prompt content never logged.

### WC015-03 — RAG retrieval (pgvector stub)

**Scope:** Vector similarity search against `professional.agent_prompts`. Returns top-3 chunks. Embeddings via AI4Bharat IndicBERT (LOCAL tier, ₹0).
**model_hint:** `reasoning`

### WC015-04 — Prompt injection defence + CCT-PI-01

**Scope:** 50-attack pattern test suite from `tests/conftest.py`. All 50 must be blocked. CCT-PI-01 added.
**model_hint:** `auto`
**Constitutional check:** C-062 — Decision Space cannot be bypassed by conversation.
**CCT gate:** CCT-PI-01 PASS required to merge

### WC015-05 — Unit tests ≥90% + PSE routing tests

**Scope:** Every PSE routing rule (PSE-R01 to PSE-R08) has a unit test. Coverage ≥90%.
**model_hint:** `auto`

---

## Definition of Done

- [ ] `docker compose up ai-runtime` → starts, connects to Ollama
- [ ] PSE: dispatches to LOCAL (Ollama) in dev environment
- [ ] Real LLM response received and parsed for a test prompt
- [ ] Prompt injection: 50/50 attacks blocked (CCT-PI-01 PASS)
- [ ] Unit tests: 100% pass, ≥90% coverage (C-076)
- [ ] `provider_dispatch_events` table populated after each LLM call

**Status:** READY when WC-014 completes
