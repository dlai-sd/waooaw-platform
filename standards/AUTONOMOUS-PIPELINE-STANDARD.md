# Autonomous Sprint Pipeline Standard

**Authority:** Platform IT Expert (INST-010) — IB-022
**Constitutional Basis:** C-059, C-066 Tier 2A, C-070, C-077, C-082, C-084, C-086, ADR-030, ADR-036
**Status:** ACTIVE — 2026-07-30
**Spec files:**
- `.github/workflows/autonomous-sprint.yaml` — the pipeline
- `scripts/autonomous_sprint_runner.py` — execution engine
- `scripts/task_decomposer.py` — SubTaskDef chain executor
- `scripts/groom_sprint.py` — sprint groomer (blueprint-first SubTaskDef generation)
- `scripts/complete_sprint.py` — post-sprint housekeeping

---

## 1. Purpose

This document is the authoritative reference for the WAOOAW Autonomous Sprint Pipeline. Every agent operating in this repository must read it before asking "should I implement this manually in a Copilot session?" The answer is almost always: **No. Add it to the pipeline.**

Constitutional basis: C-070 (Third Instinct — autonomous execution is the primary production path, not the exception).

---

## 2. The One-Rule Decision Gate

> **If the output is production code or configuration that belongs in `src/`, `tests/`, `infrastructure/`, or `web/` — it MUST go through the autonomous pipeline, not a Copilot session.**

Copilot sessions are for:
- Pipeline fixes and grooming (scripts, workflow YAML, standards docs)
- Constitutional documents (constitution/, adr/, standards/)
- Emergency remediation of a halted pipeline

See `standards/AUTONOMOUS-VS-COPILOT.md` for the full decision tree.

---

## 3. Pipeline Architecture — 5-Job Flow

```
workflow_dispatch (sprint_name=WC-NNN)
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Job 1: preflight                                                       │
│  ① py_compile health check (all pipeline scripts)                      │
│  ② HALT check (autonomous_halt + consecutive_failures < 3)             │
│  ③ Sprint index build — build_sprint_index.py → index.json (RAG)      │
│  ④ C-086 SIM check — SIM-PL-002-WCxxx-*.md must exist with PASS      │
└─────────────────────────────────────────────────────────────────────────┘
        │ halt=false
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Job 2: execute                                                         │
│  ① Key Vault fetch — ANTHROPIC_API_KEY, GH App credentials             │
│  ② GROOM step — groom_sprint.py (before PIPELINE SYNC)                │
│     • reads WC-NNN table + EA skeleton                                 │
│     • Haiku LLM generates SubTaskDef Python structs                    │
│     • injects into TASK_HANDLERS + SPRINT_TASK_MANIFEST                │
│     • commits to main                                                   │
│  ③ PIPELINE SYNC — fetch canonical scripts from main                  │
│     (picks up groomed SubTaskDefs committed in step ②)                 │
│     (autonomous_sprint_runner.py, task_decomposer.py, etc.)            │
│  ② Branch setup (checkout or create sprint branch from main)           │
│  ③ Service boundary filter (_SERVICE_SCOPE) → branch context           │
│  ④ For each task in tasks_remaining:                                   │
│     a. C-086 gate: SIM-PL-002 file must exist with PASS               │
│     b. SubTaskDef chain via execute_subtask_chain()                    │
│     c. For each subtask: LLM call → ResponseEvaluator → write files   │
│     d. compile_gate (ruff/pytest/dotnet_build) on output_files only    │
│     e. emit_subtask_signal() → monitor-signal.json                    │
│     f. git commit per task success                                     │
│  ⑤ PR create/update                                                    │
│  ⑥ complete_sprint.py (on main):                                      │
│     • failure registry                                                  │
│     • SIM-PL-002 stubs for next sprint (if SubTaskDefs exist)          │
│     • tasks_remaining update                                            │
└─────────────────────────────────────────────────────────────────────────┘
        │  always
        ├──────────────────────────────────────────────────────────────────
        ▼                                                                 ▼
┌──────────────────────┐                                    ┌────────────────────┐
│  Job 3: report        │                                    │  Job 4: review     │
│  sprint_status_       │                                    │  autonomous_sprint_ │
│  reporter.py →        │                                    │  reviewer.py →     │
│  Issue #7 dashboard   │                                    │  PR approval       │
│  always runs          │                                    │  (C-065 compliant) │
└──────────────────────┘                                    └────────────────────┘
        │  always (halt=false)
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Job 5: monitor                                                         │
│  sprint_monitor.py — C-069 feedback loop                               │
│  • classifies failures (spec_gap / infra / advisor)                    │
│  • closes stale spec-gap issues                                        │
│  • drafts constitutional proposals for recurring patterns               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Sprint Lifecycle — From WC File to Merged Code

```
Founder pushes WC-NNN-*.md to main
  │
  └── workflow_dispatch(sprint_name=WC-NNN)
        │
        ├── preflight/groom: reads WC table + EA skeleton
        │   → generates SubTaskDefs → commits to main
        │
        ├── execute: runs SubTaskDef chain
        │   → LLM writes code → compile gate → commit → PR
        │
        ├── review: autonomous_sprint_reviewer.py approves PR
        │   (GitHub App identity — C-065 author≠reviewer)
        │
        └── complete_sprint.py: generates SIM stubs for WC-(N+1)
```

**Founder touches:** push WC file + trigger `workflow_dispatch`. Everything else is autonomous.

---

## 5. The Blueprint-First Principle (ADR-036)

Every implementation sprint operates in blueprint-first mode:

1. **EA produces skeleton** (`src/{service}/skeleton/`):
   - Abstract interfaces with exact method signatures
   - Data model classes with typed fields
   - Exception classes
   - Constitutional annotations per method

2. **Groomer reads skeleton** (`groom_sprint.py`):
   - Maps WC scope → skeleton interface → output files
   - `constitutional_check` references skeleton method names exactly
   - `inject_source_files` always includes the skeleton path

3. **LLM fills bodies only** (execute job):
   - Skeleton is injected into LLM context as frozen API
   - LLM may NOT change class names, method names, parameter types
   - Violations → SPEC_GAP (routes to EA, not retry)

**Why this matters:** Without a skeleton, the LLM invents type names → CS0246/CS1061 errors → 3 retry attempts wasted. With a skeleton: first-attempt compile rate approaches 100%, 67% fewer attempts, 75% token reduction (measured from WC-012–WC-015 data).

---

## 6. SubTaskDef — Structure Reference

```python
SubTaskDef(
    id="WC027-02a",                    # {task_id}a — always single subtask per task
    description="...",                  # one sentence from WC scope
    type="llm",                         # always "llm" for implementation tasks
    depends_on=["WC027-01a"],           # prior task's subtask ID, or []
    compile_gate="ruff",                # "ruff" (python), "pytest" (tests), "dotnet_build"
    service_dir="src/billing-engine",   # from _SERVICE_SCOPE
    wc_task_id="WC027-02",             # links to WC file (C-059)
    stack="python",                     # from _TASK_STACK_MAP
    output_files=[                      # files LLM must produce (ruff scopes to these)
        "src/billing-engine/markup/bundle_engine.py",
    ],
    inject_source_files=[               # skeleton always injected for python tasks
        "src/billing-engine/skeleton/wbe_interfaces.py",
    ],
    spec_sections={
        "work-contracts/WC-027-*.md": "WC027-02",
    },
    constitutional_check=(
        "Implement IMarkupEngine.derive_bundle_cost_floor() and validate_price().\n"
        "DO NOT change signatures — implement bodies only (ADR-036).\n"
        "C-089: validate_price MUST raise BelowConstitutionalFloorError if margin < floor.\n"
    ),
    model_hint="reasoning",             # from WC table — must be "reasoning" or "auto"
    max_tokens=8000,                    # 8000 for reasoning, 3000–5000 for auto
)
```

**Invariants enforced by pipeline:**
- `model_hint` must be `"reasoning"` or `"auto"` — `"standard"` returns None (B-1 bug fixed)
- `compile_gate="ruff"` scopes to `output_files` only — pre-existing files not gated (B-2 fix)
- `depends_on` uses prior task's subtask ID for cross-task chain integrity (C-084)
- `wc_task_id` is the traceability link required by C-059

---

## 7. Service Scope Mapping

| Sprint prefix | Stack | Service directory | Test directory |
|---|---|---|---|
| WC012 | dotnet | src/constitutional-engine/ | tests/constitutional-engine.Tests/ |
| WC013 | dotnet | src/business-platform/ | tests/business-platform.Tests/ |
| WC014 | python | src/professional-runtime/ | tests/ |
| WC015 | python | src/ai-runtime/ | tests/ |
| WC016 | terraform | infrastructure/ | — |
| WC017 | typescript | web/ | — |
| WC025 | python | src/billing-engine/ | tests/billing-engine/ |
| WC026 | python | src/billing-engine/ | tests/billing-engine/ |
| WC027+ | python | src/billing-engine/ | tests/billing-engine/ |

New sprint prefixes → add to `_TASK_STACK_MAP` and `_SERVICE_SCOPE` in `scripts/autonomous_sprint_runner.py`.

---

## 8. Grooming — `groom_sprint.py`

**Purpose:** Auto-generate SubTaskDef entries from a WC file + EA skeleton, eliminating the IT Expert agent session previously required per sprint.

**Location:** `scripts/groom_sprint.py`
**Spec:** This section + `architecture/reference/pipeline/groom-sprint.md`

**Trigger:** Execute job, first step after Key Vault secrets fetch, before PIPELINE SYNC:
```yaml
- name: Groom sprint SubTaskDefs — Blueprint-First (G-0, ADR-036)
  if: steps.pr_check.outputs.skip != 'true'
  env:
    SPRINT_NAME: ${{ inputs.sprint_name || '' }}
    ANTHROPIC_API_KEY: ${{ steps.kv_secrets.outputs.ANTHROPIC-API-KEY }}
  run: |
    if [ -n "$SPRINT_NAME" ]; then
      python3 scripts/groom_sprint.py --sprint "$SPRINT_NAME"
    else
      python3 scripts/groom_sprint.py
    fi
```

**Inputs:**
1. `work-contracts/WC-NNN-*.md` — task table (task_id, scope, model_hint)
2. `src/{service}/skeleton/*.py` — EA skeleton (exact interface contracts)
3. Existing SubTaskDef patterns (WC025/WC026) — structural template

**Outputs:**
1. SubTaskDef entries injected into `TASK_HANDLERS` in `autonomous_sprint_runner.py`
2. Sprint entry injected into `SPRINT_TASK_MANIFEST` in `sprint_state.py`
3. Committed to `main` before execute job's PIPELINE SYNC step

**Failure modes:**
- No WC file → skip silently (next preflight will retry)
- LLM generation fails → skip task, log warning (does not halt sprint)
- Syntax error in generated code → abort injection, write error to stdout
- Already groomed → idempotent skip per task

---

## 9. Manual Dispatch — Sprint Name Override

The workflow accepts `sprint_name` as a dispatch input, overriding `current_sprint` in `PROJECT_STATE.md`:

```yaml
workflow_dispatch:
  inputs:
    sprint_name:
      description: 'Sprint to run (e.g. WC-027). Overrides PROJECT_STATE.md current_sprint.'
      required: false
      default: ''
```

This means the Founder never needs to edit `PROJECT_STATE.md` between sprints. Push the WC file → dispatch with `sprint_name=WC-NNN`.

---

## 10. Pipeline Bug History

| ID | Severity | Fix | Commit |
|---|---|---|---|
| B-1 | CRITICAL | `model_hint="standard"` → `"auto"` in WC026-03/04 | `304036e` |
| B-2 | HIGH | Ruff gate scoped to `output_files` only | `304036e` |
| B-3 | HIGH | PTR stack: `_TASK_STACK_MAP.get()` instead of hardcoded WC014/WC015 check | `304036e` |
| B-4 | HIGH | `_SERVICE_SCOPE` extended with WC025/WC026/WC027 | `304036e` |
| B-A | CRITICAL | `sprint_state.set_field()` `\s*` → `[ \t]*` (YAML fence corruption) | `9341a64` |
| B-B | MEDIUM | `WCSpecReader._parse_wc_table()` fallback for table-format WC files | `9341a64` |
| B-C | LOW | `SPRINT_TASK_MANIFEST` extended with WC-025/WC-026 | `9341a64` |

---

## 11. Constitutional Anchors

| Principle | Pipeline expression |
|---|---|
| C-001 Human Override | `autonomous_halt: true` → preflight stops immediately |
| C-059 Traceability | `SubTaskDef.wc_task_id` links every generated file to its PMO spec |
| C-066 Tier 2A | Groomer runs autonomously in preflight without per-task approval |
| C-070 Third Instinct | Production code MUST go through pipeline, never Copilot session |
| C-077 FinOps | Groomer uses Haiku (cheap), not Frontier model |
| C-082 Build Gate | `compile_gate` runs after every subtask |
| C-084 Step Dependency | `depends_on` chain enforced; scaffold failure halts dependents |
| C-086 Simulation | SIM-PL-002 PASS required before first LLM call per task |
| ADR-036 Blueprint-First | Skeleton injected into LLM context; body implementation only |
