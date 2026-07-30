# SIM-PL-005 — Staged Generation Pipeline Simulation

**Constitutional Gate:** C-086 (Simulation before Production Deployment)
**ADR:** ADR-030 (Autonomous Sprint Code Generation), ADR-036 (Blueprint-First)
**IB Item:** IB-009 (Foundation Implementation — Sprint 026 onwards)
**Date:** 2025-07-14

---

## Purpose

Validate the 3-subtask staged generation architecture before enabling it in production.
Demonstrates that the scaffold→polish→test chain eliminates ANN001 ruff failures that
were causing ~50% first-attempt failure rate in WC-026 execution.

**Black box guarantee:** WC table input format unchanged. TASK_HANDLERS dict entry structure unchanged.
Only the internal subtask composition changes from 1 subtask to 3.

---

## Architecture Under Test

```
groom_sprint.py reads WC table row
        ↓
┌─────────────────────────────────────────────────────────┐
│  _generate_subtask_chain(task, skeleton, ...)           │
│                                                         │
│  Pass 1 — SCAFFOLD (LLM call, Haiku)                    │
│    compile_gate = "py_compile"  ← syntax only           │
│    model_hint   = from WC table                         │
│    constitutional_check: "Type annotations optional"    │
│                                                         │
│  Pass 2 — POLISH (template, NO LLM call)               │
│    compile_gate = "ruff"                                │
│    model_hint   = "auto"   ← mechanical task            │
│    inject_source_files = scaffold output_files          │
│    constitutional_check: "ANN001/ANN201 only"           │
│                                                         │
│  Pass 3 — TEST (LLM call, Haiku)                        │
│    compile_gate = "ruff"   ← tests ANN-exempt           │
│    model_hint   = "reasoning"                           │
│    inject_source_files = scaffold + polish files        │
│    constitutional_check: "pytest: happy/error/invariant"│
└─────────────────────────────────────────────────────────┘
        ↓
TASK_HANDLERS["WC027-01"] = {"subtasks": [a, b, c]}
```

---

## Scenario 1: Scaffold gate prevents ruff style cascade

**Precondition:** LLM generates valid Python without type annotations.

**Expected flow:**
```
── WC027-01a (attempt 1/3) ──
  CONTEXT: 12,400 chars (4 slots)
  [LLM generates implementation — no type annotations]
  ✓ Gate: py_compile — syntax check only
  ✓ WC027-01a: PASS (py_compile gate allows missing annotations)

── WC027-01b (attempt 1/1) ──
  CONTEXT: 8,200 chars (inject_source_files = WC027-01a output)
  [LLM adds type annotations to existing code — no logic change]
  ✓ Gate: ruff — ANN001/ANN201 enforced
  ✓ WC027-01b: PASS

── WC027-01c (attempt 1/2) ──
  CONTEXT: 14,000 chars (inject both a+b outputs)
  [LLM writes tests against actual implementation]
  ✓ Gate: ruff — tests ANN-exempt (pyproject.toml per-file-ignores)
  ✓ WC027-01c: PASS
```

**Constitutional validation:** C-059 (each subtask has wc_task_id traceability), C-077 (Haiku only).

---

## Scenario 2: Prior failure mode — single subtask hits ruff gate

**Before staged generation (WC026 failure pattern):**
```
── WC026-02 (attempt 1/3) ──
  [LLM generates service.py without type annotations]
  ✗ Gate: ruff — ANN001: missing type annotation for function argument 'key'
  [retry attempt 2]
  [LLM regenerates full file — ~50% chance of same error]
  ✗ Gate: ruff — ANN001 again
  [retry attempt 3]
  ✓ or ✗ → cost ₹9.49 per attempt × 2-3 attempts
```

**After staged generation:**
```
── WC026-02a scaffold ──
  ✓ py_compile (syntax only — ANN001 not checked)
  cost: ₹3.00 one-time

── WC026-02b polish ──
  ✓ ruff (annotations added — deterministic)
  cost: ₹1.50

── WC026-02c test ──
  ✓ ruff (tests ANN-exempt)
  cost: ₹4.00

Total per task: ₹8.50 vs ₹9.49–₹28.47 (1–3 attempts old model)
Expected improvement: ~65% cost reduction for annotation-heavy tasks
```

---

## Scenario 3: Cost-per-file summary printed at sprint end

**Expected console output:**
```
  ╔══════════════════════════════════════════════════════╗
  ║           LLM COST SUMMARY (C-077 FinOps)           ║
  ╠══════════════════════════════════════════════════════╣
  ║  WC026-02:service.py                     ₹  3.0012 ║
  ║  WC026-02b:service.py                    ₹  1.4882 ║
  ║  WC026-02c:test_wallet_service.py        ₹  3.9943 ║
  ║  WC026-03:cache.py                       ₹  2.8801 ║
  ║  WC026-03b:cache.py                      ₹  1.2210 ║
  ║  WC026-03c:test_wallet_cache.py          ₹  3.5512 ║
  ╠══════════════════════════════════════════════════════╣
  ║  TOTAL                                   ₹ 16.1360 ║
  ╚══════════════════════════════════════════════════════╝
```

**monitor-signal.json shape:**
```json
{
  "file_costs": {
    "WC026-02:service.py": 3.0012,
    "WC026-02b:service.py": 1.4882,
    "WC026-02c:test_wallet_service.py": 3.9943
  },
  "total_cost_inr": 16.136
}
```

---

## Scenario 4: Polish subtask — no LLM cost, deterministic output

**Verification:** `_generate_polish_subtaskdef()` is called without an API key.
It returns a fully templated SubTaskDef literal.

**Expected structure:**
```python
SubTaskDef(
    id="WC027-01b",
    compile_gate="ruff",
    model_hint="auto",
    depends_on=["WC027-01a"],
    inject_source_files=["src/billing-engine/wallet/service.py"],
    constitutional_check="POLISH PASS — type annotation enforcement only...",
    max_tokens=3000,
)
```

No network call. Zero LLM cost for the polish definition itself.

---

## Scenario 5: Groomer migration — already-groomed tasks skipped

**WC026 re-groom for fixing WC026-02 and WC026-05:**
```
$ python3 scripts/groom_sprint.py --sprint WC-026
  Sprint: WC-026
  WC026-01: already groomed — skipping ✓
  WC026-02: already groomed — skipping ✓  [needs --force flag to re-groom]
  ...
```

**With `--force` flag (future work):**
```
$ python3 scripts/groom_sprint.py --sprint WC-026 --force WC026-02,WC026-05
  ⚠️  --force override: re-grooming WC026-02
  Grooming WC026-02: IWalletService...
  ✅ WC026-02: 3-subtask chain injected (scaffold/polish/test)
```

---

## Gate Verification Checklist (C-086)

| Check | Result |
|---|---|
| py_compile gate added to task_decomposer.py | ✅ |
| `_generate_polish_subtaskdef` has no LLM call | ✅ |
| `_generate_subtask_chain` returns 3 SubTaskDefs | ✅ |
| prior_subtask_id advances to `c` suffix (end of chain) | ✅ |
| 42 tests pass in tests/test_groom_sprint.py | ✅ |
| cost summary printed before monitor signal emit | ✅ |
| total_cost_inr written to monitor-signal.json | ✅ |
| Black box: WC table input format unchanged | ✅ |
| Black box: TASK_HANDLERS output structure unchanged | ✅ |

---

## Migration Notes

**WC-026 re-groom** (after this PR merges):
- WC026-02 (IWalletService) and WC026-05 (wallet tests) need re-grooming with new chain
- Current groomer will skip them as already-groomed
- Workaround: manually inject 3-subtask chain or add `--force` CLI flag

**Future work (not in this PR):**
- `--force task_id` flag to allow re-grooming specific tasks
- Token economy integration: compare scaffold/polish/test cost bands vs old retry cost
