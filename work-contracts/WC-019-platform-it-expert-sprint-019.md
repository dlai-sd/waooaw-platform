# Work Contract 019 — IB-021: Dependency Graph Task Decomposition

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 019
**Backlog Item:** IB-021 — Dependency Graph Task Decomposition
**Sprint Track:** Track 0 — Pipeline Capability (pre-requisite for WC-012 completion)
**Gate:** Pre-WC012-03 execution
**Reviewer:** WAOOAW AI Agent — QA + Enterprise Architect
**Constitutional Basis:** C-084 (Step Dependency Ordering), C-086 (Pre-Execution Simulation),
  C-083 (Emit-Transport-Listen), C-082 (Build Validation), C-059 (Traceability)

**Depends on:** WC-019 simulations pass (SIM-PL-002-DECOMP-01, SIM-PL-002-DECOMP-02)
**Enables:** WC-012-03, WC-012-04, and all multi-layer tasks in WC-013 through WC-018
**Authorization:** AUTHORIZED — IB-021, C-086 RATIFIED, SIM-PL-002-WC012-03 PASSED

---

## Sprint Goal

Implement sub-task decomposition in the autonomous sprint pipeline. After WC-019,
every multi-layer sprint task executes as an ordered sequence of sub-tasks with a
compile gate between each. No single LLM call is asked to generate more than one
layer of interdependent files.

**Acceptance condition:** WC012-03 runs cleanly end-to-end using the new sub-task
decomposition capability. `dotnet build` passes after each sub-task. CCT-DECOMP-01
through CCT-DECOMP-06 all pass. SIM-PL-002-WC012-03 verdict was already PASS.

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| Dependency graph architectural spec | `architecture/reference/pipeline/dependency-graph-task-decomposition.md` | ✅ EXISTS (EA 2026-07-24) |
| ADR-030 Amendment 1 | `adr/ADR-030-autonomous-sprint-code-generation.md` | ✅ EXISTS (EA 2026-07-24) |
| SIM-PL-002-WC012-03 PASS verdict | `simulation/SIM-PL-002-WC012-03-evidence-first-simulation.md` | ✅ PASSED (2026-07-24) |
| C-084 (Step Dependency Ordering) | `knowledge/claims/C-084.md` | ✅ RATIFIED |
| C-086 (Pre-Execution Simulation) | `knowledge/claims/C-086.md` | ✅ RATIFIED |
| Retry Advisor (Layer 1) | `scripts/sprint_retry_advisor.py` | ✅ EXISTS (2026-07-24) |

**Readiness:** AUTHORIZED — all inputs exist. Simulations SIM-PL-002-DECOMP-01 and
  SIM-PL-002-DECOMP-02 must be run and PASSED before WC019-01 LLM call is made.

---

## Pre-Sprint Simulations Required (C-086)

**SIM-PL-002-DECOMP-01 — TaskDecomposer execution flow**
What it proves: 03a → 03b → 03c chain executes in order; branch context propagates.
Run: manually trace through the proposed TaskDecomposer code with WC012-03 inputs.
File: `simulation/SIM-PL-002-DECOMP-01-task-decomposer-flow.md`

**SIM-PL-002-DECOMP-02 — C-084 halt on sub-task failure**
What it proves: if 03a compile gate fails, 03b is not called.
Run: simulate 03a failure scenario; verify 03b is skipped.
File: `simulation/SIM-PL-002-DECOMP-02-halt-on-subtask-failure.md`

Both simulations must produce `Verdict: PASS` before WC019-01 begins.

---

## Tasks

### WC019-01 — TaskDecomposer core module

**Scope:** `scripts/task_decomposer.py`
**What it delivers:**
- `execute_task(task_id) → bool` — dispatches to sub-task chain if `subtasks` key exists, else to `execute_with_llm()` (backward compatible)
- `execute_subtask_chain(task_id, subtasks) → bool` — ordered execution, compile gate, branch context propagation
- `run_compile_gate(gate_type, scope) → tuple[bool, str]` — dotnet_build | dotnet_test | ruff+py_compile | tsc
- C-083: writes sub-task signal to monitor-signal.json after each sub-task
**model_hint:** `none` — pure Python, no LLM needed
**CCTs:** CCT-DECOMP-01, CCT-DECOMP-02, CCT-DECOMP-03, CCT-DECOMP-04

### WC019-02 — TASK_HANDLERS WC012-03 sub-task definition

**Scope:** `scripts/autonomous_sprint_runner.py` — WC012-03 entry only
**What it delivers:**
- WC012-03 handler changed from `lambda: execute_with_llm(...)` to `{"subtasks": [...]}`
- WC012-03a: `deterministic` sub-task — Data layer templates (EvidenceRecord + DbContext)
- WC012-03b: `llm` sub-task — RecordEvidence implementation (depends_on: WC012-03a)
- WC012-03c: `llm` sub-task — CCT-EF-01 tests (depends_on: WC012-03a, WC012-03b)
**model_hint:** `none` for the handler definition change; `reasoning` inside the sub-tasks
**CCTs:** CCT-DECOMP-05 (sub-task has SIM-PL-002 PASS), CCT-DECOMP-06 (signal emission)

### WC019-03 — C-086 pre-flight gate

**Scope:** `.github/workflows/autonomous-sprint.yaml` + `scripts/build_sprint_index.py`
**What it delivers:**
- Pre-flight health check: for each task in tasks_remaining, verify `simulation/SIM-PL-002-{task_id}-*.md` exists with `Verdict: PASS`
- If missing: HALT with message "C-086: No simulation for {task_id}. Create SIM-PL-002 first."
- `build_sprint_index.py` supports sub-task ID format (WC012-03a) for targeted index builds
**model_hint:** `none`
**CCTs:** CCT-SIM-01 (no TASK_HANDLERS entry without simulation), CCT-SIM-02 (simulation uses actual inputs)

### WC019-04 — WC012-04 sub-task definition + simulation

**Scope:** `scripts/autonomous_sprint_runner.py` + `simulation/SIM-PL-002-WC012-04-*.md`
**What it delivers:**
- Run SIM-PL-002 for WC012-04 (Emergency Stop sub-task dependency map)
- WC012-04 handler decomposed into: EmergencyStop entities → EmergencyStopHandler → CCT-HO-01
- Verified by simulation before handler is written
**model_hint:** `none` for simulation; handler definition sub-tasks follow WC012-03 pattern
**CCTs:** CCT-DECOMP-01 (applied to WC012-04 chain)

---

## Success Criteria

1. `python3 -m py_compile scripts/task_decomposer.py` → exit 0
2. All CCT-DECOMP-01 through CCT-DECOMP-06 pass
3. All CCT-SIM-01, CCT-SIM-02 pass
4. WC012-03 runs autonomously end-to-end via the new decomposer: 03a compiles → 03b generates implementation → 03c generates CCT-EF-01 → all files committed
5. `dotnet build` passes at every compile gate
6. `dotnet test` passes for CCT-EF-01
7. No existing WC012-01/02 tests broken (backward compatibility: CCT-DECOMP-04)

---

## Output

| Artifact | Location |
|---|---|
| TaskDecomposer | `scripts/task_decomposer.py` |
| Updated TASK_HANDLERS (WC012-03/04) | `scripts/autonomous_sprint_runner.py` |
| C-086 pre-flight gate | `.github/workflows/autonomous-sprint.yaml` |
| SIM-PL-002-DECOMP-01 | `simulation/SIM-PL-002-DECOMP-01-task-decomposer-flow.md` |
| SIM-PL-002-DECOMP-02 | `simulation/SIM-PL-002-DECOMP-02-halt-on-subtask-failure.md` |
| SIM-PL-002-WC012-04 | `simulation/SIM-PL-002-WC012-04-emergency-stop-simulation.md` |
| WC-019 PR | Branch: `ib/021/dependency-graph` |
