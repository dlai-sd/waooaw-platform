# Work Contract 017 — IB-009 Sprint 017: DMA Decision Space + First Agent Live

**Office:** WAOOAW AI Agent — Platform IT Expert + WAOOAW AI Agent — QA
**Sprint:** 017
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) + IB-014/IB-015/IB-016
**Sprint Track:** Track 7 — DMA v3.0 (PMO §2.1 M8)
**Gate:** G5 → MVI
**Reviewer:** Sujay Khandge (output quality review) + WAOOAW AI Agent — QA (CCTs)
**Constitutional Basis:** C-036 (declared skills), C-040 (domain specialisation), C-047 (AI loop), C-051 (token economy), C-059, C-071, C-076

**Depends on:** WC-015 (AI Runtime live), WC-016 (Web Portal live)
**Authorization:** Requires `platform_phase: IMPLEMENTATION` + Instagram MCP credentials available

---

## Sprint Goal

Deploy DMA v3.0 Decision Space to the running platform:
1. 21 skills loaded in `professional.agent_prompts` (seed-prompts.py)
2. DMA PAAS session starts via Web Portal hire flow
3. Skill 1 (Social Presence Audit) executes: real output from PSE → Gemini 2.0 Flash or Ollama
4. MCPs (scheduling-mcp, platform-analytics-mcp, customer-profile-mcp) responding
5. **Acceptance Scenario AS-001**: Dr. Mehta Dental Clinic hire → Skill 1 audit → Grade A

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| DMA v3.0 spec | `architecture/reference/agents/digital-marketing-agent.md` | ✅ EXISTS |
| DMA simulations | `simulation/012-dma-confidence-run.md`, `SIM-019`, `SIM-020` | ✅ EXISTS |
| Agent prompts SQL | `infrastructure/postgres/init/07-agent-prompts.sql` | ✅ EXISTS |
| seed-prompts.py | `scripts/seed-prompts.py` | ✅ EXISTS |
| MCP catalogue | `architecture/reference/mcp-tool-catalogues.md` | ✅ EXISTS |
| CCT framework | `tests/constitutional/` | ✅ EXISTS (framework) |
| WC-015 (AIR live) | `src/ai-runtime/` | ⏳ PENDING WC-015 |
| WC-016 (Web live) | `src/web/` or `web/` | ⏳ PENDING WC-016 |
| Instagram MCP credentials | GitHub Secrets | ❌ PENDING FA-002 (Meta BM) |

**Readiness: BLOCKED** — WC-015/016 + FA-002 (Meta BM verification — 2-4 week lead time)

---

## Tasks

### WC017-01 — Seed DMA v3.0 prompts to DB

**Scope:** `scripts/seed-prompts.py` loads all 21 DMA skills. Validate idempotency.
**model_hint:** `none` (pure Python, no LLM)
**Output:** `professional.agent_prompts` has 21 rows for DMA, `is_active=true`

### WC017-02 — DMA PAAS session start + Skill 1

**Scope:** Customer hires WaooaW Expert Dental Marketing via portal → PAAS session created → Skill 1 (Social Presence Audit) executes via AI Runtime → PSE routes to LOCAL (Ollama) or MID (Gemini Flash).
**model_hint:** `reasoning`
**CCT gate:** CCT-DS-01 (Decision Space enforcement — only authorized tools callable)

### WC017-03 — AS-001 acceptance scenario (Dr. Mehta)

**Scope:** DeepEval test: `test_as001_dr_mehta_grade_a`. Runs full Skill 1 flow. Output must score Grade A.
**model_hint:** `auto` (runs DeepEval grading)
**CCT gate:** AS-001 Grade A required to proceed to WC-018

---

## Definition of Done

- [ ] 21 DMA prompts seeded to dev PostgreSQL
- [ ] DMA hire → PAAS session → Skill 1 → output produced (any quality)
- [ ] AS-001 DeepEval: Grade A in dev environment
- [ ] CCT-DS-01: Decision Space enforcement PASS (unauthorized tool request → DENY)
- [ ] Sujay reviews Skill 1 output and applies `quality:reviewed` label on PR

**Status:** READY when WC-015 + WC-016 complete AND FA-002 in progress
