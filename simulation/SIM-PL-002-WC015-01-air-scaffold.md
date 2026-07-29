# SIM-PL-002 — WC015-01 AI Runtime Scaffold + PSE Routing
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC015-01 — Python 3.12 AIR project scaffold + PSE routing
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
WC015-01 creates the AI Runtime FastAPI service skeleton at src/ai-runtime/.
PSE routes LLM calls to LOCAL (Ollama) / MID / FRONTIER / FALLBACK tiers (ADR-029).
Service name uses hyphen (ai-runtime) — same import pattern as professional-runtime.
Stack: Python 3.12. Constitutional: C-051 (token economy), C-062 (AI security).

## Subtask Decomposition
WC015-01a (deterministic) — pyproject scaffold + FastAPI skeleton + Dockerfile → ruff → PASS
WC015-01b (llm, reasoning) — PSE routing logic (4-tier: LOCAL/MID/FRONTIER/FALLBACK) → ruff → PASS

## Dependency Graph
WC015-01a: depends_on=[]
WC015-01b: depends_on=[WC015-01a]

## Risk Assessment
- Hyphenated service dir (ai-runtime): STACK_BEHAVIORAL_RULES covers sys.path.insert pattern
- PSE complexity: 4-tier routing table with Vertex AI + Ollama + fallback — LLM context has ADR-029
- ruff violations: per-file-ignores + STACK_BEHAVIORAL_RULES covers F841/B018/LOG015/G004
- Temporal imports: STACK_BEHAVIORAL_RULES covers correct temporalio import pattern
- C-051 compliance: PSE must route LOCAL tasks to Ollama (not Frontier) — constitutional_check enforces

## Verdict

**VERDICT: ✅ PASS**
