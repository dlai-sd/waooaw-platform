# SIM-PL-002 — WC015-02 LLM Dispatch + Ollama Inference
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC015-02 — LLM dispatch + real Ollama inference
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Implements Ollama call via httpx (async) to http://ollama:11434/api/generate.
Records dispatch event to institutional.provider_dispatch_events (C-059).
Wrapped as Temporal activity — worker picks up task from queue.
Stack: Python 3.12. Constitutional: C-051 (cost routing), C-059 (evidence).

## Subtask Decomposition
WC015-02a (llm, reasoning) — dispatch.py: httpx POST to Ollama + record event → ruff → PASS
WC015-02b (llm, reasoning) — unit tests: mock httpx + mock DB → ruff → PASS

## Dependency Graph
WC015-02a: depends_on=[WC015-01b]
WC015-02b: depends_on=[WC015-02a]

## Risk Assessment
- Ollama response: JSON `{"response": "...", "done": true}` — straightforward parse
- httpx async: `async with httpx.AsyncClient() as client:` — standard pattern
- Temporal activity: `@activity.defn` decorator + `activity.execute_activity()` call — STACK_BEHAVIORAL_RULES covers
- ruff per-file-ignores handles LOG015/G004 in tests; --unsafe-fixes handles F841/B018

## Verdict

**VERDICT: ✅ PASS**
