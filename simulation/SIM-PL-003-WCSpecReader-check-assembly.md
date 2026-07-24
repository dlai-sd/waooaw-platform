# SIM-PL-003: WCSpecReader Constitutional Check Assembly

**Simulation ID:** SIM-PL-003
**Document type:** Pre-Execution Simulation (C-086 gate)
**IB item:** IB-022 — WC-Spec-Driven Sprint Runner
**Spec reference:** `architecture/reference/pipeline/wc-spec-reader.md`
**Office:** Enterprise Architect (simulation author) + Platform IT Expert (implementation reviewer)
**Date:** 2026-07-24
**Constitutional basis:** C-086 (Pre-Execution Simulation Gate), C-059, C-032, DP-009

---

## Simulation Objective

Verify that the WCSpecReader assembly mechanism produces correct, complete, and constitutionally compliant `constitutional_check` content for each LLM subtask, across all supported stacks and edge cases.

---

## Scenario 1: WC012-02b — Standard dotnet LLM subtask

**Input:**
```python
SubTaskDef(
    id="WC012-02b",
    wc_task_id="WC012-02",
    output_files=[
        "src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs",
        "src/constitutional-engine/Evaluators/C043BudgetCeilingEvaluator.cs",
        "src/constitutional-engine/Services/ConstitutionalEngineService.cs",
    ],
    not_regenerate_from=["WC012-02a"],
    stack="dotnet",
    constitutional_check="BEHAVIORAL RULES:\n  ActionParameters → use ctx.GetParameter()\n  EvaluatorRegistry → _registry.EvaluateAllAsync(ctx, ct)",
    type="llm",
)
completed = ["WC012-02a"]
```

**Expected output from `_build_effective_check()`:**

Section 1 — PMO requirements (from WC-012-*.md):
```
CONSTITUTIONAL REQUIREMENTS (PMO: WC012-02 — ValidateAction + unit tests (≥90% coverage)):
Scope: Implement ValidateAction stub evaluator. Write unit tests (xUnit + FluentAssertions + Moq).
Default deny (C-041) must be the starting state — unlisted tool = DENY.
```

Section 2 — File boundaries:
```
Implement ONLY these files:
  src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs
  src/constitutional-engine/Evaluators/C043BudgetCeilingEvaluator.cs
  src/constitutional-engine/Services/ConstitutionalEngineService.cs
```

Section 3 — Prior task preservation:
```
Do NOT regenerate files from prior subtasks: WC012-02a
```

Section 4 — Stack behavioral rules:
```
STACK RULES (non-negotiable):
  ActionParameters is JSON-encoded — use ctx.GetParameter("key"), NEVER TryGetValue().
  TenantId comes from gRPC metadata: context.RequestHeaders.GetValue("x-tenant-id") ?? "".
  All using directives MUST precede the namespace declaration to avoid proto namespace collision.
  PROTO NAMESPACE: using Waooaw.ConstitutionalEngine.Grpc; on files referencing gRPC types.
  C-059 header required on every .cs file.
```

Section 5 — Delta:
```
BEHAVIORAL RULES:
  ActionParameters → use ctx.GetParameter()
  EvaluatorRegistry → _registry.EvaluateAllAsync(ctx, ct)
```

**Simulation result:** ✅ PASS — All 5 sections assembled correctly. Constitutional requirements traced to WC spec. Stack rules prevent known failure modes (TryGetValue, namespace collision). PTR type contracts injected separately after this output.

---

## Scenario 2: WC013-02 — Python stack (future sprint)

**Input:**
```python
SubTaskDef(
    id="WC013-02",
    wc_task_id="WC013-02",
    output_files=["src/business-platform/middleware/TenantMiddleware.py"],
    not_regenerate_from=["WC013-01"],
    stack="python",
    type="llm",
)
completed = ["WC013-01"]
```

**Expected output sections:**
1. PMO: `C-005 (Three-Ledger — tenants never share data), C-026 (DB-level enforcement).`
2. File: `src/business-platform/middleware/TenantMiddleware.py`
3. Preservation: `Do NOT regenerate files from prior subtasks: WC013-01`
4. Stack rules: Python-specific rules (async, CE.ValidateAction, C-063)
5. Delta: (empty — no task-specific override needed)

**Simulation result:** ✅ PASS — WCSpecReader auto-loads Python constitutional requirements without any runner changes. Zero manual constitutional_check prose required.

---

## Scenario 3: WC file not found (graceful degradation)

**Input:** `SubTaskDef(wc_task_id="WC999-01", constitutional_check="Manual fallback check", stack="dotnet")`

**Expected:** WCSpecReader logs warning, falls back to `constitutional_check` delta only. Sprint execution continues. Sections 1 (PMO) and 3 (preservation) are empty; sections 2, 4, 5 still populated.

**Simulation result:** ✅ PASS — Graceful degradation maintains backward compatibility. Existing SubTaskDef entries without `wc_task_id` continue to work unchanged.

---

## Scenario 4: Deterministic subtask (no constitutional_check needed)

**Input:** `SubTaskDef(id="WC012-02a", type="deterministic", wc_task_id="", stack="dotnet")`

**Expected:** `_build_effective_check()` is not called for deterministic tasks (execute_subtask_chain only calls it for LLM subtasks).

**Simulation result:** ✅ PASS — Function is gated behind `if st.type == "llm"` in execute_subtask_chain.

---

## Scenario 5: C-059 traceability verification

**Claim:** After IB-022 implementation, every LLM subtask with `wc_task_id` has a verifiable trace from:
`SubTaskDef.wc_task_id` → `work-contracts/WC-NNN-*.md` → `**Constitutional check:**` field

**Verification method:** `grep -r 'wc_task_id' scripts/autonomous_sprint_runner.py | wc -l` should equal the count of LLM subtasks. CI gate CCT-TR-01 (traceability check) extended to verify wc_task_id population.

**Simulation result:** ✅ PASS — Traceability chain is complete and machine-verifiable.

---

## Scenario 6: STACK_BEHAVIORAL_RULES governance

**Claim:** Stack rules can only change with EA review (not during sprint execution).

**Verification:** `STACK_BEHAVIORAL_RULES` is a module-level constant in `task_decomposer.py`. It is not configurable at runtime. Changes require a code commit which triggers EA review in PR.

**Simulation result:** ✅ PASS — Governance enforced by code review process.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| WC format changes break parser | Low | Parser uses optional field matching; missing fields → empty string (no failure) |
| Stack inference wrong | Low | Explicit `stack=` field in SubTaskDef overrides inference |
| PTR + WC spec combined prompt exceeds token budget | Medium | Token budget check already in runner; WC constitutional_check is typically <200 chars |
| SubTaskDef migration introduces regressions | Medium | Phase 2b done after WC-012 merged; full 277+ test suite protects main |

---

## Verdict

**Verdict: ✅ PASS**

All 6 simulation scenarios pass. WCSpecReader is constitutionally compliant, backward compatible, and structurally sound. Implementation (Phase 2) is authorized to begin.

C-086 gate: CLEARED for IB-022 Phase 2 implementation.
