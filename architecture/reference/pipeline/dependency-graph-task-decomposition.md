# Dependency-Ordered Task Decomposition — Pipeline Architectural Spec

**Version:** 1.0
**Date:** 2026-07-24
**Author:** Enterprise Architect (EA office)
**Constitutional Basis:** C-084 (Step Dependency Ordering), C-086 (Pre-Execution Simulation),
  C-082 (Build Validation for all stacks), C-059 (Traceability), ADR-030 Amendment 1
**IB Reference:** IB-021
**Status:** RATIFIED (EA) — pending Platform IT Expert implementation (WC-019)

---

## 1. Problem Statement

### Evidence Base (C-086 — simulation must precede design)

SIM-PL-002-WC012-03 (2026-07-24) proved:
- WC012-03 requires generating 3 interdependent file layers: Data entities → Service implementation → Tests
- Single-LLM-call approach cannot maintain namespace consistency across 3+ interdependent files (empirical: 3 failed runs)
- Dependency-ordered generation (Layer 0 compiles → Layer 1 reads compiled output → compiles → Layer 2) works (build succeeded in simulation)
- Every sprint task from WC012-03 onwards involves multi-layer generation: WC013 (5 layers), WC014-WC018 (4-6 layers each)

**Consequence of not building this:** Every multi-layer sprint task will require manual intervention or repeated LLM retries with no convergence guarantee. The autonomous pipeline cannot deliver WC012-03 through WC018 without this capability.

---

## 2. Core Concept: Sub-Tasks

A **sub-task** is a cohesive set of files with:
1. No internal cross-dependencies (all files in the sub-task compile independently of each other)
2. All external dependencies are satisfied by prior sub-tasks (or by the branch state)
3. A compile gate that must pass before the next sub-task begins

A sprint task is decomposed into an ordered list of sub-tasks. Sub-tasks within a task share a sprint branch but have separate LLM calls and separate compile validations.

### Sub-Task Types

| Type | Generation | When to use |
|---|---|---|
| `deterministic` | Template (no LLM) | Schema entities, interfaces, config files — no business logic, namespace must be exact |
| `llm` | LLM (claude-sonnet-4-6) | Business logic, implementations, complex tests requiring reasoning |

**Rule (from WC012-01 and WC012-03 evidence):** Any file where the namespace MUST be exact and the content is schema-like (entities, interfaces, DbContexts, proto copies) → `deterministic`. Any file requiring constitutional reasoning (Evidence First ordering, evaluator logic, CCT implementation) → `llm`.

---

## 3. TASK_HANDLERS Extended Schema

Current schema:
```python
"WC012-03": lambda: execute_with_llm(task_id, description, spec_sections, check)
```

Extended schema (sub-task decomposition):
```python
"WC012-03": {
    "subtasks": [
        {
            "id": "WC012-03a",
            "description": "Data layer — EvidenceRecord entity + ConstitutionalDbContext",
            "type": "deterministic",
            "template_fn": generate_wc012_03a_data_layer,  # Python function, no LLM
            "compile_gate": "dotnet_build",
            "emits_to_branch_context": True,  # output becomes context for next sub-task
        },
        {
            "id": "WC012-03b",
            "description": "RecordEvidence implementation + idempotency logic",
            "type": "llm",
            "spec_sections": { "architecture/reference/components/constitutional-engine.md": "§1 Evidence First Enforcer" },
            "constitutional_check": "...",
            "model_hint": "reasoning",
            "max_tokens": 8000,
            "compile_gate": "dotnet_build",
            "depends_on": ["WC012-03a"],  # must compile before this runs
        },
        {
            "id": "WC012-03c",
            "description": "CCT-EF-01 — Evidence First ordering test",
            "type": "llm",
            "spec_sections": { "tests/QA-STRATEGY.md": "§5.1 Unit Tests" },
            "constitutional_check": "...",
            "model_hint": "reasoning",
            "max_tokens": 5000,
            "compile_gate": "dotnet_test",
            "depends_on": ["WC012-03a", "WC012-03b"],
        },
    ]
}
```

---

## 4. TaskDecomposer Component

New Python module: `scripts/task_decomposer.py`

### 4.1 Execution Protocol

```
execute_task(task_id) → bool:
  1. Read task definition from TASK_HANDLERS[task_id]
  2. If task has no "subtasks" key → delegate to execute_with_llm() (backward compatible)
  3. If task has "subtasks":
     a. For each sub-task in dependency order:
        i.  Check branch context (existing files satisfy this sub-task's depends_on?)
        ii. If type=deterministic: call template_fn(), write files, run compile_gate
        iii.If type=llm: call execute_with_llm() with sub-task spec, run compile_gate
        iv. If compile_gate FAILS: Retry Advisor classifies → intelligent retry or halt
        v.  If sub-task PASSES: emit C-083 signal, update branch context for next sub-task
        vi. If sub-task FAILS after retries: halt chain (C-084), flag_spec_gap for this sub-task
     b. All sub-tasks PASSED → commit all generated files → emit task-level SUCCESS signal
     c. Any sub-task FAILED → stop, do not proceed to next sub-task
```

### 4.2 Branch Context Propagation (C-083)

After each sub-task passes its compile gate, the TaskDecomposer calls `get_branch_context()`
to refresh the branch context. The next sub-task's LLM call receives the full updated branch
context including all files from prior sub-tasks. This is the implementation of C-083
(Emit-Transport-Listen) applied to the code generation pipeline:
- Sub-task completion = signal emission
- Updated branch context = transport
- Next sub-task receives fresh context = listen

### 4.3 Backward Compatibility

Tasks without `subtasks` key (WC011-01 through WC012-02) continue to use the existing
`execute_with_llm()` path unchanged. No migration of existing tasks required.

---

## 5. Deterministic Template Standard

Every `type: deterministic` sub-task must follow this pattern (modelled on `execute_wc012_01()`):

```python
def generate_wc012_03a_data_layer() -> bool:
    """
    WC012-03a: Data layer templates — no LLM, no hallucination surface.
    Namespace is fixed. Schema is derived directly from the proto message definitions.
    C-086: This sub-task exists because simulation proved LLM cannot reliably
           maintain namespace consistency for Data/ entities across multi-file calls.
    """
    # Write exact template files to src/constitutional-engine/Data/
    # Validate with dotnet build
    # Return True/False
```

**What goes in a deterministic sub-task:**
- All namespace declarations are hardcoded (not inferred by Claude)
- All class names come from a fixed table (derived from the spec, not generated)
- No business logic — only structure
- File structure verified by SIM-PL-002 before the template is written

**What NEVER goes in a deterministic sub-task:**
- Anything requiring constitutional reasoning
- Anything where the "right answer" depends on the spec content
- Tests (always LLM — they implement specific constitutional claims)

---

## 6. Architecture Chain Update

The following documents must be updated when this spec is implemented:

| Document | Change | Priority |
|---|---|---|
| `adr/ADR-030-autonomous-sprint-code-generation.md` | Amendment 1: sub-task decomposition protocol | REQUIRED before WC-019 |
| `scripts/autonomous_sprint_runner.py` | TASK_HANDLERS schema extended; TaskDecomposer called | WC-019 implementation |
| `scripts/build_sprint_index.py` | Support task_id=WC0XX-NNa (sub-task ID format) | WC-019 implementation |
| `scripts/sprint_status_reporter.py` | Report at sub-task granularity, not just task | WC-019 implementation |
| `.github/workflows/autonomous-sprint.yaml` | Pre-flight C-086 gate: simulation PASS check | WC-019 implementation |
| `CODING-STANDARDS.md` | Section 3.0: Sub-task decomposition standard for .NET multi-layer tasks | WC-019 documentation |

---

## 7. CCTs

| CCT ID | Test | Pass criteria |
|---|---|---|
| **CCT-DECOMP-01** | Sub-task ordering — WC012-03 | TaskDecomposer executes 03a before 03b, 03b before 03c |
| **CCT-DECOMP-02** | Compile gate enforced | If 03a compile gate fails, 03b is NOT called (C-084) |
| **CCT-DECOMP-03** | Branch context propagated | 03b LLM call receives 03a's committed files in BRANCH CONTEXT |
| **CCT-DECOMP-04** | Backward compatibility | WC012-01 and WC012-02 handlers still work via existing path |
| **CCT-DECOMP-05** | C-086 pre-flight gate | Pipeline halts if TASK_HANDLERS has a new sub-task without SIM-PL-002 PASS |
| **CCT-DECOMP-06** | Signal emission (C-083) | Each sub-task completion writes to monitor-signal.json before next sub-task starts |

---

## 8. Simulation Requirement (C-086)

Before WC-019 implementation begins, the following simulations must pass:

| Simulation | What it proves |
|---|---|
| SIM-PL-002-WC012-03 | ✅ DONE (2026-07-24) — sub-task approach compiles |
| SIM-PL-002-DECOMP-01 | TaskDecomposer execution flow — must prove 03a→03b→03c chain executes in order |
| SIM-PL-002-DECOMP-02 | C-084 halt — must prove 03b is skipped when 03a fails |
| SIM-PL-002-WC012-04 | Emergency Stop sub-task dependency map (before WC012-04 runs) |

SIM-PL-002-WC012-03 is complete. The remaining simulations are WC-019 pre-work tasks.
