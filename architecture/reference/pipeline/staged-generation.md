# Staged Code Generation — Design & Implementation Plan

**Authority:** Platform IT Expert (INST-010)
**Constitutional Basis:** C-066 Tier 2A, C-070, C-077, C-082
**Status:** IN PROGRESS — IB-022 extension
**Date:** 2026-07-30

---

## Problem Statement

Single-pass generation asks one LLM call to simultaneously handle business logic,
type annotations, constitutional invariants, and tests. LLM attention is zero-sum.
Each added constraint degrades all others. Result: ~50% first-attempt pass rate.

**Evidence (run 30566526755):**
- WC026-02 failed: 200 lines of correct business logic, 1 missing type annotation (ANN001)
- WC026-05 failed: valid test code, wrong infrastructure (pytest not installed)
- WC026-03, WC026-04: passed cleanly — both were single-concern tasks

**Conclusion:** Failures are not logic failures. They are attention-budget failures.

---

## Staged Generation Model

One WC task row → three subtasks in sequence:

```
WC027-02 (wallet service)
    │
    ├── WC027-02a  SCAFFOLD    compile_gate="py_compile"
    │   LLM job:  Implement business logic only. No style concerns.
    │   Model:    from WC table (reasoning/auto)
    │   Gate:     syntax only — code compiles
    │
    ├── WC027-02b  POLISH      compile_gate="ruff"
    │   LLM job:  Add type annotations to ALL args and returns. Fix style.
    │             DO NOT change business logic.
    │   Model:    auto (mechanical task — Haiku tier)
    │   Gate:     full ruff including ANN001
    │   Input:    injects WC027-02a output files
    │
    └── WC027-02c  TEST        compile_gate="ruff"   (pytest_run = future sprint)
        LLM job:  Write pytest tests against THIS implementation.
                  Cover: happy path, idempotency, error cases, constitutional invariants.
        Model:    reasoning (test quality requires understanding edge cases)
        Gate:     ruff (tests are ANN-exempt in pyproject.toml per-file-ignores)
        Input:    injects WC027-02a + WC027-02b output files
```

---

## Black Box Guarantee

| Surface | Before | After | Changes? |
|---|---|---|---|
| WC table format (input) | `task_id \| scope \| model_hint \| status` | same | ❌ No |
| SPRINT_TASK_MANIFEST | `"WC-027": ["WC027-01", ..., "WC027-05"]` | same | ❌ No |
| TASK_HANDLERS structure | `{"subtasks": [SubTaskDef(...)]}` | same schema | ❌ No |
| Final committed files | `wallet/service.py`, `tests/test_wallet.py` | same files | ❌ No |
| SubTaskDef schema | existing fields | same fields | ❌ No |
| Number of subtasks per task | 1 | 3 | ✅ Yes (internal) |
| compile_gate per subtask | "ruff" | "py_compile" / "ruff" / "ruff" | ✅ Yes (internal) |

The WC author writes the same WC file. The pipeline produces the same final files.
Only the internal execution path changes.

---

## New Gate Type: `py_compile`

Added to `run_compile_gate()` in `task_decomposer.py`:

```python
if gate_type == "py_compile":
    for f in (target_files or []):
        result = subprocess.run(
            ["python3", "-m", "py_compile", f],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        if result.returncode != 0:
            return False, result.stderr[:500]
    return True, ""
```

**Why not just use `ruff`?** The scaffold pass must NOT fail on ANN001. Ruff is configured
to require type annotations (ANN rule set, pyproject.toml). `py_compile` checks syntax only —
exactly what the scaffold needs.

---

## Cost Model

| Pass | Model | Tokens (est.) | Cost per task (est.) |
|---|---|---|---|
| Scaffold | Sonnet/auto (from WC table) | 4000–8000 output | ₹8–16 |
| Polish | Haiku (auto, mechanical) | 2000–3000 output | ₹1–2 |
| Test | Sonnet (reasoning) | 4000–6000 output | ₹8–12 |
| **Total** | | | **₹17–30** |

Current single-pass with ~2 retries: ₹16–30. No regression in cost. With higher
first-attempt success rate, total cost per sprint is lower due to fewer runs needed.

---

## Cost Per File Logging

Required: cost summary at end of each sprint execution.

```
── Sprint Cost Summary ────────────────────────────────────────────────────
  File                                                 Cost       Attempts
  src/billing-engine/wallet/service.py                 ₹ 9.49     2
  src/billing-engine/wallet/exceptions.py              ₹ 3.96     1
  src/billing-engine/wallet/cache.py                   ₹ 2.31     1
  src/billing-engine/wallet/router.py                  ₹ 4.12     1
  tests/billing-engine/test_wallet.py                  ₹ 7.88     1
  ─────────────────────────────────────────────────────────────────────────
  Sprint total                                         ₹27.76     6 calls
```

Implementation: cost accumulator dict in `autonomous_sprint_runner.py`, populated
per file in the MagicLLM response handler, logged at sprint end and written to
`monitor-signal.json` under `cost_by_file`.

---

## Implementation Tasks

| # | Task | File(s) | Status |
|---|---|---|---|
| T-1 | Fix B-F: Install pytest before execute step | `.github/workflows/autonomous-sprint.yaml` | ☐ |
| T-2 | Add `py_compile` gate type | `scripts/task_decomposer.py` | ☐ |
| T-3 | Update groom: 3-subtask chain generation | `scripts/groom_sprint.py` | ☐ |
| T-4 | Add cost-per-file accumulator + summary log | `scripts/autonomous_sprint_runner.py` | ☐ |
| T-5 | Update tests for 3-subtask behavior | `tests/test_groom_sprint.py` | ☐ |
| T-6 | SIM-PL-005: staged generation simulation | `simulation/SIM-PL-005-staged-generation.md` | ☐ |

---

## Polish Pass — LLM Prompt Design

The polish subtask uses a fixed constitutional_check (not LLM-generated):

```
POLISH PASS — type annotation enforcement only.
You will receive existing Python code. Your ONLY job:
1. Add type annotations to ALL function parameters (ANN001).
2. Add return type annotations to ALL functions (ANN201, ANN202).
3. Fix any remaining ruff ANN rule violations.
4. DO NOT change function names, signatures, business logic, or structure.
5. DO NOT add new imports beyond those needed for type annotations.
model_hint: auto  (this is a mechanical transformation, not reasoning)
```

This is templated — no LLM call needed to generate the polish SubTaskDef. It is
constructed directly by groom_sprint.py.

---

## Test Pass — LLM Prompt Design

The test subtask has a constitutional_check generated by one brief LLM call (Haiku),
grounded in the scaffold output files:

```
TEST PASS — generate pytest tests for the implemented service.
Inject: [scaffold output files — actual implementation]
Tests must cover:
  - Happy path for each public method
  - Idempotency guarantee for reserve() (C-090)
  - Error cases: insufficient balance, reservation not found
  - Constitutional invariant: [derived from skeleton annotations]
compile_gate: ruff  (tests exempt from ANN per pyproject.toml per-file-ignores)
model_hint: reasoning
```

---

## Migration Path for Existing WC026

WC026-02 and WC026-05 are in `tasks_remaining`. On next run:
- WC026-02: still has 1-subtask definition (old format) — fails on ANN001 again
- WC026-05: still fails on pytest not installed

After this implementation lands on `main`:
- New WC-027+ tasks: use 3-subtask chains from groom
- WC026-02 and WC026-05: manually add polish and test subtasks to TASK_HANDLERS
  (or re-groom WC-026 with the new groomer)

Recommendation: after this lands, re-run `groom_sprint.py --sprint WC-026 --force`
(add `--force` flag) to regenerate WC026-02 and WC026-05 with 3-subtask chains,
replacing the 1-subtask entries.
