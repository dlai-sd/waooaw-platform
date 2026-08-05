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

### 6a. Implementation task (src/ output)

```python
SubTaskDef(
    id="WC027-02a",
    description="...",
    type="llm",
    depends_on=["WC027-01a"],
    compile_gate="ruff",
    service_dir="src/billing-engine",
    wc_task_id="WC027-02",
    stack="python",
    output_files=[
        "src/billing-engine/markup/bundle_engine.py",
    ],
    inject_source_files=[
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
    model_hint="reasoning",      # from WC table
    max_tokens=8000,             # 8000 for reasoning; 3000–5000 for auto
)
```

### 6b. Test task (tests/ output) — ADR-032 Decision 9

Test tasks differ from implementation tasks in three ways: model_hint is always `"auto"`,
max_tokens is always `12000`, and `service_dir=""`.

> **NEVER** set `model_hint="reasoning"` for a test task. Extended thinking consumes 8000
> thinking tokens before writing a single line of test code — output is always truncated.
> The `goal_executor.py` backstop will override this, but the groomer should not produce it.

```python
SubTaskDef(
    id="WC028-01a",
    description="Write pytest suite for meter/service.py covering happy path, dedup, procurement scope",
    type="llm",
    depends_on=[],
    compile_gate="ruff",
    service_dir="",              # always "" for test-only tasks
    wc_task_id="WC028-01",
    stack="python",
    output_files=[
        "tests/billing-engine/test_service.py",
    ],
    inject_source_files=[        # inject ONLY the public API — not the full implementation
        "src/billing-engine/skeleton/wbe_interfaces.py",
        "src/billing-engine/meter/service.py",
    ],
    spec_sections={
        "work-contracts/WC-028-*.md": "WC028-01",
    },
    constitutional_check=(
        "TEST PASS — write pytest tests as described in the WC scope.\n"
        "Use pytest-asyncio for async tests. Use AsyncMock for async methods.\n"
        "Always await AsyncMock calls: `result = await mock.method(args)`.\n"
        "Insert datetime objects directly into SQLite bindparams — never .isoformat().\n"
        "StaticPool required for in-memory engine (see FORBIDDEN_APIS).\n"
    ),
    model_hint="auto",           # REQUIRED — never "reasoning" for test tasks (ADR-032 D9)
    max_tokens=12000,            # REQUIRED — test files exceed 500 lines (ADR-032 D9)
)
```

**Invariants enforced by pipeline:**
- `model_hint` must be `"reasoning"` or `"auto"` — `"standard"` returns None (B-1 bug fixed)
- `compile_gate="ruff"` scopes to `output_files` only — pre-existing files not gated (B-2 fix)
- `depends_on` uses prior task's subtask ID for cross-task chain integrity (C-084)
- `wc_task_id` is the traceability link required by C-059
- Test tasks: `model_hint` MUST be `"auto"`, `max_tokens` MUST be `12000` (ADR-032 Decision 9)

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
| B-D | CRITICAL | Test task groomer forced `model_hint="reasoning"` + `max_tokens=8000` — thinking tokens consumed output budget → truncated test files | `8463c01` |
| B-E | HIGH | Test task groomer injected full service.py (29K chars) into test context — async pattern knowledge crowded out by implementation detail | `8463c01` |
| B-F | HIGH | No positive async test pattern in FORBIDDEN_APIS → LLM invented `.isoformat()` datetime serialization and omitted `await` on AsyncMock | `8463c01` |

---

## 13. Python Async Test Patterns (Positive Reference)

These patterns are injected into every `TEST_GENERATION` task via `pipeline.py _build_prompt`. They exist here as the constitutional source of truth.

### 13a. AsyncMock — correct usage

```python
# ✅ CORRECT: set return_value, then await the call
mock_service.check_thresholds = AsyncMock(return_value=[])
alerts = await mock_service.check_thresholds(customer_id)

# ✅ CORRECT: await every AsyncMock call — including "setup" calls
await mock_redis.setex(key, ttl, value)     # setex is AsyncMock → must await

# ❌ WRONG: calling without await creates unawaited coroutine → PytestUnraisableExceptionWarning
mock_redis.setex(key, ttl, value)           # missing await
```

### 13b. SQLite datetime in test fixtures

```python
# ✅ CORRECT: pass datetime object directly — SQLAlchemy converts to space-separated TEXT
await session.execute(text("INSERT INTO log (fired_at) VALUES (:t)").bindparams(t=fired_at))

# ❌ WRONG: .isoformat() produces T-separator ('T' > ' ' in SQLite string compare)
# fired_at stored as '2026-08-05T07:00:00+00:00' but dedup_window as '2026-08-05 08:00:00+00:00'
# SQLite comparison: 'T'(84) > ' '(32) → stale row sorts AFTER window → dedup triggers incorrectly
await session.execute(text("INSERT INTO log (fired_at) VALUES (:t)").bindparams(t=fired_at.isoformat()))
```

### 13c. In-memory SQLite engine (StaticPool)

```python
# ✅ CORRECT: StaticPool ensures all sessions share the same connection
from sqlalchemy.pool import StaticPool
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

### 13d. pytest-asyncio fixture injection

```python
# ✅ CORRECT: pytest-asyncio executes async fixtures before the test body
async def test_something(meter_service: MeterService, session_factory: async_sessionmaker):
    alerts = await meter_service.check_thresholds(customer_id)

# ❌ WRONG: fixture parameter is already the resolved value — do not await it
async def test_something(meter_service):
    service = await meter_service   # wrong — meter_service is already a MeterService instance
```

---

## 11. Batch Operating Model (ADR-041)

Full specification: `adr/ADR-041-autonomous-batch-operating-model.md`

### 11.1 Four Operating Modes

| Mode | LLM Cost | When | What it does |
|---|---|---|---|
| **PLAN** | ₹0 | Mandatory before every EXECUTE | Validates dependency graph, checks C-086 SIM, estimates LLM calls. Blocks EXECUTE if preconditions fail. |
| **EXECUTE** | N calls | Fresh sprint — all tasks pending | Runs tasks in dependency order. Writes heartbeat at start. Writes task state to WC file after each subtask. |
| **RESUME** | <N calls | Prior run was PARTIAL or container-killed | Reads heartbeat mismatch, reclassifies `in-progress` → `failed_structural`, skips `done` and `skipped_idempotent`. |
| **CLOSE** | ₹0 | Always, regardless of EXECUTE/RESUME outcome | Idempotent. Appends to failure registry. Updates PROJECT_STATE. Takes PR action. Writes `run_complete` to heartbeat. |

### 11.2 Task Status Values

The WC file task table uses these seven status values:

| Status | Meaning | Next action |
|---|---|---|
| `pending` | Not yet started | Execute on next run |
| `in-progress` | Started — LLM call in flight or container killed mid-task | On heartbeat mismatch: reclassify as `failed_structural` |
| `done` | All gates passed | Skip on RESUME (SKIPPED_IDEMPOTENT) |
| `failed_structural` | Compile/ruff/LLM gate failure | Retry next run with failure context injected |
| `failed_transient` | API timeout / rate limit | Retry same run with backoff |
| `failed_terminal` | Constitutional violation / spec gap confirmed | `autonomous_halt=true`, GitHub Issue opened |
| `skipped_cascade` | Upstream task is `failed_*` | Retry automatically when root cause task passes |

### 11.3 Error Code Quick Reference

| Error Code | Class | Expected Action |
|---|---|---|
| `LLM_IMPORT_VIOLATION` | STRUCTURAL | Retry next run. Closed-world import constraint active from ADR-041. |
| `PTR_GATE_FAILURE` | STRUCTURAL | Retry next run. TIS references symbol not in workspace index. |
| `COMPILE_GATE_FAILURE` | STRUCTURAL | Retry next run with error context. Check ruff E402/B904. |
| `NORMALIZATION_INCOMPLETE` | STRUCTURAL | Retry next run. E402/B904 survived normalization. |
| `SCAFFOLD_ERROR` | STRUCTURAL | Retry next run. TIS artifact malformed. |
| `GROOMING_ERROR` | STRUCTURAL | Retry next run. Scope text parse failed. |
| `LLM_NO_RESPONSE` | TRANSIENT | Retry same run. |
| `API_TIMEOUT` | TRANSIENT | Retry same run, 30s backoff. |
| `RATE_LIMIT` | TRANSIENT | Retry same run, 60s backoff. |
| `WRITE_BOUNDARY_VIOLATION` | TERMINAL | `autonomous_halt=true`. LLM attempted write outside `src/`/`tests/`. |
| `SPEC_GAP` | TERMINAL | `autonomous_halt=true`. GitHub Issue opened. EA/SA/Founder review. |
| `CONTAINER_KILLED` | STRUCTURAL | Auto-detected via heartbeat. RESUME reclassifies `in-progress` tasks. |

### 11.4 Halt Policy

`autonomous_halt=true` is set **only** by TERMINAL failures. PARTIAL runs with STRUCTURAL or TRANSIENT failures leave `halt=false` so RESUME proceeds automatically without manual intervention.

Three separate failure counters:
- `spec_failures` — structural failures. Threshold: ≥3 → terminal.
- `infra_failures` — transient API failures. Never drives halt.
- `terminal_count` — terminal failures. Threshold: ≥1 → immediate halt.

### 11.5 Manual Recovery Commands

```bash
# Check current batch state
python3 scripts/sprint_state.py get

# Reset halt after investigating a terminal failure
python3 scripts/sprint_state.py set autonomous_halt false
python3 scripts/sprint_state.py set consecutive_failures 0

# Force re-run a specific task (skips dependency check)
docker compose --profile sprint run --rm sprint-runner --force-task WC027-02

# Run completion protocol manually after a container kill
python3 scripts/complete_sprint.py --dry-run   # inspect first
python3 scripts/complete_sprint.py             # apply
```

---

## 12. Constitutional Anchors

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
