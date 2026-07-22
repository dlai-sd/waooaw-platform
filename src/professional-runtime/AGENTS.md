# AGENTS.md — Professional Runtime (PR) Context
# FinOps Pattern 2: Scoped context for PR subdirectory work only
# constitutional_basis: C-025 (PAAS), C-047 (AI Execution Loop), C-059, C-076

## Service Identity
- **Name:** Professional Runtime (PR)
- **Language:** Python 3.12 FastAPI + Temporal Worker
- **Decision Space:** PAAS session lifecycle, Temporal workflow execution, Emergency Stop WebSocket
- **ADR Authority:** ADR-005 (PAAS isolation), ADR-015 (Temporal deployment), ADR-018 (Emergency Stop signal)

## Primary Spec Files (load these — nothing else)
- `architecture/reference/components/professional-runtime.md`
- `architecture/reference/api-specs/professional-runtime.openapi.yaml`
- `standards/CODING-STANDARDS.md` §3 (Python) + §7.5 (Coverage C-076)

## Constitutional Claims This Service Enforces
- **C-025** — PAAS is first-class execution model
- **C-047** — AI Execution Loop (SENSE/RETRIEVE/REASON/ACT/RECORD — 5 steps, no skipping)
- **C-049** — Honest Limitation Disclosure (raise C-049 signal when uncertain)
- **C-059** — Implementation Traceability

## Test Requirements (C-076)
- **Line coverage:** ≥90% — `pytest --cov --cov-fail-under=90`
- **Branch coverage:** ≥80%
- **PAAS session lifecycle test:** session_start, session_resume, emergency_stop all tested
- **Emergency Stop latency test:** `test_emergency_stop_under_250ms()` — C-001 constitutional floor

## Critical Pattern — Emergency Stop (C-001)
```python
# Emergency Stop path MUST be non-blocking — ≤250ms P99 guaranteed
# No I/O, no DB calls, no LLM calls on this path
async def handle_emergency_stop(session_id: str) -> EmergencyStopResult:
    # ONLY: cancel Temporal workflow signal + update in-memory state
    await self._temporal_client.signal_workflow(
        session_id, "emergency_stop", EmergencyStopSignal()
    )
    return EmergencyStopResult(success=True, session_id=session_id)
# NEVER: DB write, LLM call, or any external I/O on this code path
```
