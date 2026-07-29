# SIM-PL-002 — WC014-03 PAAS Session Lifecycle + Unit Tests
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC014-03 — PAAS session start/pause/resume/terminate + CCT-PS-01
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
WC014-03 implements C-025 (PAAS exclusive execution model) — all professional work
runs as Temporal workflow. Two LLM subtasks: lifecycle implementation (03a) and tests (03b).
Stack: Python. Temporal workflow ID = session_id for idempotency.

## Subtask Decomposition
WC014-03a (llm, reasoning) — POST/GET/DELETE /sessions → start/describe/terminate workflow → ruff → PASS
WC014-03b (llm, reasoning) — ≥90% coverage unit tests, mock Temporal → pytest → PASS

## Dependency Graph
WC014-03a: depends_on=[WC014-02a]
WC014-03b: depends_on=[WC014-03a]

## Risk Assessment
- Temporal client mock: unittest.mock.AsyncMock — established Python pattern
- Session isolation: each session gets unique workflow_id — simple string check in tests
- C-025 check: no direct skill execution (synchronous) — LLM warned in constitutional_check
- pytest-asyncio for async tests — STACK_BEHAVIORAL_RULES covers this
- Retry advisor Python classifiers handle import errors (temporalio vs temporal)

## Verdict

**VERDICT: ✅ PASS**
