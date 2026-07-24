# Sprint Task Decomposition Specification

**Document type:** Architecture Reference — Pipeline Tooling
**Office:** Enterprise Architect (Office 04)
**IB item:** IB-022 — WC-Spec-Driven Sprint Runner (Option B)
**Constitutional basis:** C-032 (Implementation may not create architecture), C-059 (Traceability)
**Status:** APPROVED — 2026-07-24 (EA session)
**Depends on:** wc-spec-reader.md

---

## Purpose

This document authorizes the subtask decomposition decisions made by the autonomous sprint runner. The PMO Work Contracts define tasks at business scope level. This spec documents EA authority for splitting those tasks into LLM-execution subtasks — each of which is individually compilable, testable, and within LLM token budget.

**C-032 compliance:** Subtask decomposition is an architectural decision. Embedding it inside implementation code (`autonomous_sprint_runner.py`) without this authorization document violates C-032. This spec closes that gap.

---

## Decomposition Principles

1. **Single compile gate per subtask** — each subtask must compile independently before the next begins (C-084).
2. **Deterministic first** — interface contracts, entities, and static boilerplate are written by template (zero LLM cost, zero hallucination risk). LLM only writes business logic.
3. **Token budget discipline** — each LLM subtask must fit within `max_tokens` without context overflow. If a WC task would require >10,000 tokens of output, decompose further.
4. **Dependency order** — subtask dependency graph must be a DAG. No circular dependencies.
5. **PTR propagation** — after each subtask's compile gate passes, types are emitted to PTR for downstream subtasks (C-083).

---

## WC-012: Constitutional Engine Skeleton

**WC task:** WC012-01 — .NET 9 project scaffold + gRPC wiring
**Decomposition:** Single deterministic task (no LLM). All files are known-good templates.

| Subtask | Type | Output files | Compile gate |
|---|---|---|---|
| WC012-01 | deterministic | `src/constitutional-engine/*.csproj`, `Program.cs`, `Protos/constitutional_service.proto`, `Services/ConstitutionalEngineService.cs` (stub), `appsettings.*.json`, `tests/*.csproj` | `dotnet_build` |

---

**WC task:** WC012-02 — ValidateAction + unit tests (≥90% coverage)
**Decomposition rationale:** Single LLM call would exceed token budget (13 files including 5 evaluators + service + 3 test files + 4 interfaces). Split into 4 subtasks: interfaces (deterministic, no hallucination), evaluators (LLM, bounded output), test helper (deterministic), tests (LLM, bounded).

| Subtask | Type | Output files | Not regenerate from | Compile gate |
|---|---|---|---|---|
| WC012-02a | deterministic | `Evaluators/EvaluationResult.cs`, `EvaluationContext.cs`, `IClaimEvaluator.cs`, `EvaluatorRegistry.cs` | — | `dotnet_build` |
| WC012-02b | llm | `Evaluators/C041*.cs`, `C043*.cs`, `C048*.cs`, `C049*.cs`, `C062*.cs`, `Services/ConstitutionalEngineService.cs` (extend) | WC012-02a | `dotnet_build` |
| WC012-02c-prep | deterministic | `tests/.../FakeServerCallContext.cs` | WC012-02a, WC012-02b | `dotnet_build` |
| WC012-02c | llm | `tests/.../CCT_EF01_C041*.cs`, `CCT_EF01_C043*.cs` | WC012-02a, WC012-02b, WC012-02c-prep | `dotnet_build` |

**WC012-02a rationale:** Interface contracts are architectural — generating them via LLM risks hallucinated API surfaces that downstream subtasks (02b) then depend on. Deterministic template guarantees stable types for PTR emission.

**WC012-02c-prep rationale:** `FakeServerCallContext` is static boilerplate (implements abstract class with fixed members). LLM consistently confuses abstract properties with abstract methods (CS0505). Deterministic template eliminates this.

---

**WC task:** WC012-03 — Evidence First record + CCT-EF-01
**Decomposition rationale:** Data layer (deterministic entity + DbContext) must compile before service implementation uses it. Tests depend on both.

| Subtask | Type | Output files | Not regenerate from | Compile gate |
|---|---|---|---|---|
| WC012-03a | deterministic | `Data/Entities/EvidenceRecord.cs`, `Data/ConstitutionalDbContext.cs` | WC012-02* | `dotnet_build` |
| WC012-03b | llm | `Services/ConstitutionalEngineService.cs` RecordEvidence impl | WC012-02*, WC012-03a | `dotnet_build` |
| WC012-03c | llm | `tests/.../CCT_EF01_EvidenceFirstTests.cs` | WC012-02*, WC012-03a, WC012-03b | `dotnet_build` |

---

**WC task:** WC012-04 — Emergency Stop signal + CCT-HO-01
**Decomposition rationale:** Same pattern as WC012-03: entity (deterministic) → service impl (LLM) → test (LLM).

| Subtask | Type | Output files | Not regenerate from | Compile gate |
|---|---|---|---|---|
| WC012-04a | deterministic | `EmergencyStop/EmergencyStopEvent.cs`, `EmergencyStop/EmergencyStopDbContext.cs` | WC012-02*, WC012-03* | `dotnet_build` |
| WC012-04b | llm | `Services/ConstitutionalEngineService.cs` TriggerEmergencyStop impl | all prior | `dotnet_build` |
| WC012-04c | llm | `tests/.../CCT_HO01_EmergencyStopTests.cs` | all prior | `dotnet_build` |

---

## WC-013: Business Platform Skeleton (.NET 9, stack: dotnet)

| Subtask | Type | Stack | Compile gate |
|---|---|---|---|
| WC013-01 | deterministic | dotnet | `dotnet_build` |
| WC013-02 | llm | dotnet | `dotnet_build` |
| WC013-03 | llm | dotnet | `dotnet_build` |
| WC013-04 | llm | dotnet | `dotnet_test` |

---

## WC-014: Professional Runtime (Python 3.12, stack: python)

| Subtask | Type | Stack | Compile gate |
|---|---|---|---|
| WC014-01 | deterministic | python | `ruff` |
| WC014-02 | llm | python | `ruff` |
| WC014-03 | llm | python | `ruff` |
| WC014-04 | llm | python | `ruff` |

---

## WC-015: AI Runtime (Python 3.12, stack: python)

| Subtask | Type | Stack | Compile gate |
|---|---|---|---|
| WC015-01 | deterministic | python | `ruff` |
| WC015-02 | llm | python | `ruff` |
| WC015-03 | llm | python | `ruff` |
| WC015-04 | llm | python | `ruff` |
| WC015-05 | llm | python | `ruff` |

---

## WC-016: Web Application (Next.js 14, stack: typescript)

| Subtask | Type | Stack | Compile gate |
|---|---|---|---|
| WC016-01 | deterministic | typescript | `tsc` |
| WC016-02 | llm | typescript | `tsc` |
| WC016-03 | llm | typescript | `tsc` |
| WC016-04 | llm | typescript | `vitest` |

---

## WC-017: DMA Agent Live (stack: mixed)

| Subtask | Type | Stack | Notes |
|---|---|---|---|
| WC017-01 | deterministic | python | Seed script — model_hint: none |
| WC017-02 | llm | python | PAAS session start |
| WC017-03 | llm | mixed | DeepEval acceptance test |

---

## WC-018: QA + Deployment (stack: terraform + mixed)

| Subtask | Type | Stack | Notes |
|---|---|---|---|
| WC018-01 | deterministic | terraform | Terraform apply |
| WC018-02 | llm | mixed | CCT suite |
| WC018-03 through WC018-07 | llm/deterministic | mixed | Acceptance + deployment steps |

---

## Governance

- **Amendment authority:** Enterprise Architect only
- **Review trigger:** Any new WC sprint task being onboarded requires an entry in this document before runner implementation begins
- **C-032 check:** If a subtask decomposition decision is not recorded here, the runner code implementing it violates C-032 and must not be merged
