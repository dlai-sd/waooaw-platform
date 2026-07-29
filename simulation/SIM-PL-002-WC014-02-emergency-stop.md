# SIM-PL-002 — WC014-02 Emergency Stop WebSocket + CCT-HO-02
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC014-02 — Emergency Stop WebSocket → Temporal HALT signal ≤250ms
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
WC014-02 implements C-001 (Emergency Stop ≤250ms) on the Professional Runtime.
Two LLM subtasks: WebSocket endpoint (02a) and latency test CCT-HO-02 (02b).
Stack: Python (ruff compile gate). ADR-018 (Temporal signal). ADR-015 (Temporal worker).

## Subtask Decomposition
WC014-02a (llm, reasoning) — WebSocket /sessions/{id}/stop → Temporal HALT signal → ruff → PASS
WC014-02b (llm, reasoning) — CCT-HO-02 mock Temporal latency test ≤250ms → pytest → PASS

## Dependency Graph
WC014-02a: depends_on=[]
WC014-02b: depends_on=[WC014-02a]

## Risk Assessment
- Python stack: ruff lint + pytest (not dotnet build) — different error profile
- Key risk: LLM uses wrong Temporal import (`temporal` vs `temporalio`) — covered by FORBIDDEN_PATTERNS (ERROR HANDLING RULE 3, pytest-asyncio convention)
- No sync I/O on WebSocket path (C-001 ≤250ms) — explicit in constitutional_check
- Mock Temporal client with unittest.mock — no real server needed
- GoalExecutor + retry advisor (Python classifiers Rules 10-14) cover import/async errors

## Verdict

**VERDICT: ✅ PASS**
