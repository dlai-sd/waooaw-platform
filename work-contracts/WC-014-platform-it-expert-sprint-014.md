# Work Contract 014 — IB-009 Sprint 014: Professional Runtime Skeleton

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 014
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5)
**Sprint Track:** Track 4 — Professional Runtime (PMO §2.1 M5)
**Gate:** G5
**Reviewer:** WAOOAW AI Agent — QA
**Constitutional Basis:** C-001 (Emergency Stop ≤250ms), C-024, C-025 (PAAS), C-047 (AI Loop), C-059, C-065, C-076

**Depends on:** WC-013 complete (BP must be running — PR creates PAAS sessions per employment contract)
**Authorization:** Requires `platform_phase: IMPLEMENTATION`

---

## Sprint Goal

Produce a running Python 3.12 FastAPI + Temporal Worker for the Professional Runtime that:
1. PAAS session start: POST `/sessions` → creates Temporal workflow
2. PAAS session resume: GET `/sessions/{id}` → resumes after crash (C-025)
3. Emergency Stop WebSocket: `ws://professional-runtime/sessions/{id}/stop` → Temporal HALT signal ≤250ms
4. AI Execution Loop: 5-step SENSE/RETRIEVE/REASON/ACT/RECORD stub running via Temporal activity
5. Unit test coverage ≥90% (C-076)

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| PR component spec | `architecture/reference/components/professional-runtime.md` | ✅ EXISTS |
| PR OpenAPI spec | `architecture/reference/api-specs/professional-runtime.openapi.yaml` | ✅ EXISTS |
| ADR-005 (PAAS isolation) | `adr/ADR-005-paas-session-isolation.md` | ✅ EXISTS |
| ADR-015 (Temporal deployment) | `adr/ADR-015-temporal-deployment-strategy.md` | ✅ EXISTS |
| ADR-018 (Emergency Stop signal) | `adr/ADR-018-emergency-stop-temporal-signal.md` | ✅ EXISTS |
| Emergency Stop WS spec | `architecture/reference/api-specs/emergency-stop-ws.md` | ✅ EXISTS |
| WC-013 (BP running) | `src/business-platform/` | ⏳ PENDING WC-013 |

**Readiness: BLOCKED** — WC-013 must complete first

---

## Tasks

### WC014-01 — Python 3.12 PR project scaffold + Temporal worker

**Scope:** `src/professional-runtime/` FastAPI + Temporal worker. Health endpoint. PAAS session workflow stub.
**model_hint:** `reasoning`
**Constitutional check:** PAAS is the exclusive execution model (C-025) — no synchronous skill execution.

### WC014-02 — Emergency Stop WebSocket + CCT-HO-02

**Scope:** WebSocket endpoint → sends Temporal HALT signal → session stops ≤250ms P99.
**model_hint:** `reasoning`
**Constitutional check:** C-001 (absolute ≤250ms). C-024 (architectural guarantee). No I/O on this path.
**CCT gate:** CCT-HO-02 PASS required to merge (latency test under 10 concurrent sessions)

### WC014-03 — PAAS session lifecycle + unit tests ≥90%

**Scope:** Session start, pause, resume, terminate. Temporal state machine. CCT-PS-01 (session isolation).
**model_hint:** `reasoning`
**Constitutional check:** C-025 — no cross-session contamination. Each session has isolated evidence chain.

### WC014-04 — AI Execution Loop stub (5-step, Temporal activities)

**Scope:** SENSE/RETRIEVE/REASON/ACT/RECORD as 5 Temporal activities. Stub responses. No real LLM yet.
**model_hint:** `auto`
**Constitutional check:** C-047 — all 5 steps must execute in sequence. RECORD must always execute (C-023).

---

## Definition of Done

- [ ] `docker compose up professional-runtime` → starts
- [ ] Emergency Stop: ≤250ms P99 over 10 test runs (CCT-HO-02 PASS)
- [ ] PAAS session: start → run activity → stop lifecycle works in Temporal
- [ ] Unit tests: 100% pass, ≥90% coverage (C-076)
- [ ] No blocking I/O on Emergency Stop code path

**Status:** READY when WC-013 completes
