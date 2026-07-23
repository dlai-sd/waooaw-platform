# Work Contract 012 — IB-009 Sprint 012: Constitutional Engine Skeleton

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 012
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5)
**Sprint Track:** Track 2 — Constitutional Engine (PMO §2.1 M3)
**Gate:** G5
**Reviewer:** WAOOAW AI Agent — QA (CCT authoring, C-065 separation)
**Constitutional Basis:** C-023 (Evidence First), C-041 (Tool Authorization), C-059, C-065, C-073, C-076, **C-079 (CE Fail-Safe Halt on Unavailability — RATIFIED 2026-07-23)**

**Authorization:** Requires `platform_phase: IMPLEMENTATION` in PROJECT_STATE.md before execution.
Follows WC-011 (infrastructure validated). No parallel execution with other WCs.

---

## Sprint Goal

Produce a running .NET 9 gRPC service skeleton for the Constitutional Engine that:
1. Starts via `docker compose up constitutional-engine`
2. Responds to `ValidateAction` RPC (stub — returns AUTHORIZED for any request)
3. Responds to `RecordEvidence` RPC (stub — appends to `constitutional.audit_records`)
4. Passes **CCT-EF-01** (Evidence First: record written before success returned)
5. Passes **CCT-HO-01** (Human Override: Emergency Stop signal accepted within 250ms)
6. Unit test coverage ≥90% (C-076)

This sprint produces **NO business logic**. Evaluators are stubs. Evidence recording is real.

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| CE component spec | `architecture/reference/components/constitutional-engine.md` | ✅ EXISTS (updated 2026-07-23 — §6 CE Unavailability added) |
| ADR-031 (CE fail-safe) | `adr/ADR-031-ce-fail-safe-unavailability.md` | ✅ EXISTS (new, RATIFIED C-079) |
| Proto contract | `architecture/reference/proto/constitutional_service.proto` | ✅ EXISTS |
| ADR-001 (gRPC) | `adr/ADR-001-grpc-for-constitutional-engine.md` | ✅ EXISTS |
| ADR-007 (mTLS) | `adr/ADR-007-grpc-mtls-certificates.md` | ✅ EXISTS |
| DB schema | `infrastructure/postgres/init/01-schemas.sql` | ✅ EXISTS |
| Append-only rules | `infrastructure/postgres/init/05-append-only-rules.sql` | ✅ EXISTS |
| Coding standards (.NET) | `standards/CODING-STANDARDS.md §2` | ✅ EXISTS |
| QA strategy | `tests/QA-STRATEGY.md` | ✅ EXISTS (v1.2 — C-080 Docker mandate) |
| **.NET 9 SDK** | GitHub Actions `actions/setup-dotnet@v4 dotnet-version: 9.0.x` | ✅ CONFIGURED in autonomous-sprint.yaml execute job (P1-02 fix 2026-07-23) |
| Sprint index | `sprint-context/index.json` (WC012-01 entry) | ✅ EXISTS |
| WC-011 complete | Infrastructure validated | ✅ 6/7 PASS |

**Readiness: READY** (all inputs present; blocked only by platform_phase gate)

---

## Tasks

### WC012-01 — .NET 9 project scaffold + gRPC wiring

**Scope:** Create `src/constitutional-engine/` .NET 9 project. Wire proto → gRPC service skeleton. All methods return `Status.Unimplemented` stubs except ValidateAction (returns AUTHORIZED).
**model_hint:** `reasoning`
**Token budget:** 9,591 tokens (exceeds 8K free model — uses reasoning model)
**C-059 header required on:** every .cs file
**CCT gate:** None (scaffold only)
**Output:** `src/constitutional-engine/` passes `dotnet build`

### WC012-02 — ValidateAction + unit tests (≥90% coverage)

**Scope:** Implement ValidateAction stub evaluator. Write unit tests (xUnit + FluentAssertions + Moq).
**model_hint:** `reasoning`
**Constitutional check:** Default deny (C-041) must be the starting state — unlisted tool = DENY.
**CCT gate:** CCT-EF-01 must pass
**Output:** `dotnet test` passes, `dotnet-coverage check --minimum-coverage-lines 90`

### WC012-03 — Evidence First record + CCT-EF-01

**Scope:** RecordEvidence RPC writes to `constitutional.audit_records` before returning. Write CCT-EF-01.
**model_hint:** `reasoning`
**Constitutional check:** C-023 — evidence BEFORE success. C-007 — append-only, no UPDATE/DELETE.
**CCT gate:** CCT-EF-01 PASS required to merge

### WC012-04 — Emergency Stop signal + CCT-HO-01

**Scope:** CE accepts Emergency Stop signal from Temporal. Propagates HALT to session. ≤250ms P99.
**model_hint:** `reasoning`
**Constitutional check:** C-001 — ≤250ms guaranteed. C-024 — architectural floor.
**CCT gate:** CCT-HO-01 PASS required to merge

---

## Definition of Done

- [ ] `docker compose up constitutional-engine` → service starts, `/health` returns 200
- [ ] `buf lint` passes against `constitutional_service.proto`
- [ ] `dotnet build` → 0 warnings-as-errors
- [ ] Unit tests: 100% pass, ≥90% line coverage (C-076)
- [ ] CCT-EF-01: Evidence First PASS
- [ ] CCT-HO-01: Human Override (Emergency Stop) PASS
- [ ] All .cs files have `// Implements: architecture/reference/components/constitutional-engine.md §X` header
- [ ] `scan-traceability.py` passes on CE service

**Status:** READY — awaiting `platform_phase: IMPLEMENTATION`
