# SIM-PL-002-WC012-03 — Sprint Task Content Simulation: Evidence First Record

**Simulation ID:** SIM-PL-002-WC012-03
**Task:** WC012-03 — CE Evidence First record + CCT-EF-01
**Sprint:** WC-012
**Constitutional basis:** C-086 (Pre-Execution Simulation Obligation — RATIFIED 2026-07-24)
**Simulation author:** Enterprise Architect + Platform IT Expert
**Date:** 2026-07-24
**Status:** COMPLETE

---

## Section 1: Task Identity

| Field | Value |
|---|---|
| **Task ID** | `WC012-03` |
| **Description** | Implement RecordEvidence RPC with Evidence First write to DB, CCT-EF-01 tests |
| **Sprint** | WC-012 |
| **Spec source** | `architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer` |
| **Prior task outputs on branch** | WC012-01 (scaffold) + WC012-02 (evaluators) already committed |

---

## Section 2: Acceptance Criteria

| Criterion ID | Criterion | Pass condition |
|---|---|---|
| AC-01 | Data layer (EvidenceRecord, ConstitutionalDbContext) compiles as Layer 0 | `dotnet build` exit 0 with zero errors |
| AC-02 | Layer 1 (Service implementation) compiles using Layer 0 types | `dotnet build` exit 0 with namespace `Waooaw.ConstitutionalEngine.Data` resolved |
| AC-03 | No CS0246 errors (type not found) across all generated files | Zero `CS0246` in build output |
| AC-04 | CCT-EF-01 can be written without referencing types that don't compile | Test project compiles against the implementation |
| AC-05 | No CS0101 errors (duplicate class) — existing WC012-01/02 files not regenerated | Zero `CS0101` in build output |

---

## Section 3: Dependency Map

**The failure pattern from runs #46 and #47:** Claude generated Layer 1 (Service) that referenced
`Waooaw.ConstitutionalEngine.Data.EvidenceRecord` in a single LLM call — but the Data namespace
wasn't guaranteed to be consistent with what was already on the branch. Namespace inconsistency
across files generated in one call → CS0246 / "Data does not exist" build failure.

```
Layer 0 (no dependencies — deterministic template, NOT LLM-generated):
  src/constitutional-engine/Data/Entities/EvidenceRecord.cs
    namespace: Waooaw.ConstitutionalEngine.Data.Entities
    depends on: none
  src/constitutional-engine/Data/ConstitutionalDbContext.cs
    namespace: Waooaw.ConstitutionalEngine.Data
    depends on: Waooaw.ConstitutionalEngine.Data.Entities.EvidenceRecord (Layer 0 same call)

Layer 1 (LLM-generated — AFTER Layer 0 compiles and is committed to branch):
  src/constitutional-engine/Services/ConstitutionalEngineService.cs [EXTEND existing]
    RecordEvidence implementation
    depends on: Waooaw.ConstitutionalEngine.Data.ConstitutionalDbContext (Layer 0)
    depends on: Waooaw.ConstitutionalEngine.Data.Entities.EvidenceRecord (Layer 0)

Layer 2 (LLM-generated — AFTER Layer 1 compiles):
  tests/constitutional-engine.Tests/Services/CCT_EF01_EvidenceFirstTests.cs
    depends on: Layer 0 entities + Layer 1 service
```

**Key finding:** Layer 0 (Data entities) has NO dependency on proto-generated code or other
services. It can and MUST be generated as a deterministic template (like WC012-01) to eliminate
namespace inconsistency risk. Layer 1 (implementation) is the appropriate LLM task — it has
business logic (Evidence First ordering, idempotency key check, EF Core writes).

---

## Section 4: Controlled Simulation Scenario

**4.1 What the simulation tested:**
Generate Layer 0 and Layer 1 as separate compilation units. Verify Layer 0 compiles standalone.
Verify Layer 1 resolves Layer 0's namespaces. This proves the dependency-ordered approach works.

**4.2 Branch context at simulation time:**
Files already on branch (WC012-01 + WC012-02):
- `src/constitutional-engine/constitutional-engine.csproj`
- `src/constitutional-engine/Protos/constitutional_service.proto`
- `src/constitutional-engine/Program.cs`
- `src/constitutional-engine/Services/ConstitutionalEngineService.cs` (with stubs)
- `src/constitutional-engine/Evaluators/C041_ToolAuthorizationEvaluator.cs` (and 5 others)
- `tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj`

**4.3 Critical type names verified against proto:**
```
Waooaw.ConstitutionalEngine.Data.Entities.EvidenceRecord  → NOT in proto (custom class, correct)
Waooaw.ConstitutionalEngine.Data.ConstitutionalDbContext   → NOT in proto (custom class, correct)
RecordEvidenceResponse                                      → proto message, namespace: Waooaw.ConstitutionalEngine.Grpc
RecordEvidenceRequest                                       → proto message, namespace: Waooaw.ConstitutionalEngine.Grpc
```

---

## Section 5: Simulation Execution Results

**Step 1: Dependency structure verification**
Layer 0 files: EvidenceRecord.cs, ConstitutionalDbContext.cs — no cross-layer dependencies.
Layer 1 file: uses `Waooaw.ConstitutionalEngine.Data` namespace (Layer 0) — correct direction.
Result: ✅ PASS — no circular dependencies, all references point from higher to lower layers.

**Step 2: Layer 0 skeleton compile**
Generated EvidenceRecord.cs with namespace `Waooaw.ConstitutionalEngine.Data.Entities`.
Generated ConstitutionalDbContext.cs with namespace `Waooaw.ConstitutionalEngine.Data`.
```
dotnet build result: Build succeeded. 0 Error(s). 0 Warning(s).
```
Result: ✅ PASS

**Step 3: Layer 1 integration verify**
Added RecordEvidenceImpl.cs using `Waooaw.ConstitutionalEngine.Data` and `Waooaw.ConstitutionalEngine.Data.Entities`.
```
dotnet build result: Build succeeded. 0 Error(s). 0 Warning(s).
```
Result: ✅ PASS — Layer 1 resolves Layer 0 types correctly when generated in dependency order.

**Step 4: Constitutional check adequacy review**
Current WC012-03 constitutional check says: "DO NOT regenerate Data/ConstitutionalDbContext.cs,
Data/Entities/EvidenceRecord.cs". But these files DON'T EXIST on the branch (WC012-01 only
created the scaffold, WC012-02 created evaluators). Telling Claude not to regenerate files that
don't exist yet creates confusion — Claude then generates them with self-invented namespaces.
Result: ❌ FAIL — constitutional check has incorrect "DO NOT" instructions for files that
must be CREATED in WC012-03, not avoided.

---

## Section 6: Gap Analysis

| AC ref | Gap found | Root cause | Required fix |
|---|---|---|---|
| AC-01/02 | CS0246 "Data does not exist" in 3 runs | Layer 0 (Data) and Layer 1 (Service) generated in same LLM call → namespace self-inconsistency | Split: Layer 0 as deterministic template; Layer 1 as LLM task after Layer 0 commits |
| AC-05 | Constitutional check says "DO NOT regenerate Data/ files" for files that don't exist | WC012-03 must CREATE Data/ files — they're not on the branch from prior tasks. Wrong instruction confuses Claude. | Remove incorrect "DO NOT" for Data/ files. Layer 0 generation IS the task. |
| AC-03 | CS0246 in both LLM attempts | Claude self-inconsistent namespace across files in single call | Deterministic Layer 0 eliminates this class of error entirely |

**Root cause summary:**
The failure is NOT a spec gap. It is a CODE GENERATION ARCHITECTURE gap:
1. WC012-03 asks Claude to generate interdependent files in one call
2. Claude cannot maintain namespace consistency across >2 interdependent files reliably
3. The fix requires sub-task decomposition, not better instructions to Claude

---

## Section 7: Verdict

```
VERDICT: ✅ PASS (with required fixes applied before LLM execution)

Simulation proves: when WC012-03 is split into two sub-tasks with a compile gate:
  WC012-03a: Data layer (deterministic template, not LLM) → compiles ✅
  WC012-03b: RecordEvidence implementation (LLM, reads compiled 03a from branch) → compiles ✅

The single-LLM-call approach WILL FAIL. The split approach WILL PASS.
C-086 requires this PASS before the LLM call. Neither approach can proceed
without implementing sub-task decomposition in the runner.

Date: 2026-07-24
Reviewed by: Enterprise Architect
```

---

## Section 8: Lessons for Pipeline Improvement

| Finding | Implication | IB item needed? |
|---|---|---|
| Single LLM call cannot reliably generate >2 interdependent files with consistent namespaces | Sub-task decomposition required in TASK_HANDLERS: `subtasks: [03a, 03b]` | YES — IB for dependency graph capability |
| Layer 0 (Data entities, schemas, interfaces) has no business logic — deterministic template is always correct | All Layer 0 files should be template-generated, not LLM-generated, for any sprint task | YES — standard for TASK_HANDLERS definition |
| Constitutional check was incorrect (said DO NOT for files that must be CREATED) | Simulation reveals instruction errors before 48,000 tokens are wasted on bad retries | Validates C-086 — simulation would have caught this before run #46 |
| The dependency graph IB item is evidence-based, not speculative | Simulation provides the formal proof that the dependency graph is required (not nice to have) | YES — existing dependency graph IB item validated |
