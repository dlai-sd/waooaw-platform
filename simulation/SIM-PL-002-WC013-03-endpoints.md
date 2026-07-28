# SIM-PL-002 — WC013-03 Registration + Hire Endpoints
**Date:** 2026-07-28
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC013-03 — POST /api/customers + POST /api/agents/hire + unit tests
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
WC013-03 implements the two core BP endpoints that call CE.ValidateAction.
Two LLM subtasks: endpoint implementation (03a) and unit tests (03b).

## Subtask Decomposition
WC013-03a (llm, reasoning) — customer + hire endpoints, CE.ValidateAction call → compile → PASS
WC013-03b (llm, reasoning) — unit tests ≥90% coverage → compile → PASS

## Risk Assessment
- depends_on WC013-02a (JWT middleware must exist before endpoint DI wiring)
- CE.ValidateAction client from WC012 frozen registry — exact constructor injected
- EXISTING_FILE slot prevents replacement of middleware from 02a
- Retry advisor + cascade handle compile failures

## Verdict

**VERDICT: ✅ PASS**
