# Autonomous Sprint Pipeline v2 — Phase Model Design

**Document type:** Architecture Evolution + Implementation Plan + Operating Standard  
**Status:** DRAFT — for review and implementation tracking  
**Authority:** Platform IT Expert (INST-010)  
**Constitutional Basis:** C-059, C-066, C-070, C-076, C-077, C-082, C-084  
**Supersedes (when implemented):** Sections 5, 6, 7 of `standards/AUTONOMOUS-PIPELINE-STANDARD.md`  
**Companion ADRs:** ADR-036 (Blueprint-First), ADR-039 (UDCP), ADR-030 (Code Gen)  
**Date:** 2026-08-06  

---

## 1. Why this document exists

Three consecutive sprint audits (WC-028, WC-029, WC-030) produced deliverables that passed the pipeline's own gates but failed correctness verification at audit time. The defects were not random. They form six reproducible patterns traceable to specific structural gaps in the current pipeline.

This document captures those gaps, derives a phase model that closes them, specifies the refactoring required to implement it on top of the existing infrastructure, and serves as the operating standard for the new pipeline version once implemented.

---

## 2. Evidence: what the audits found

| Sprint | Defect | Escaped because |
|--------|--------|----------------|
| WC-028 | `test_meter.py` — 12 tests, 0% coverage; `mock_meter_service = MagicMock()` mocks the SUT | `compile_gate="ruff"` on test tasks — tests generated but never executed |
| WC-029 | `test_procurement.py` — raw SQL bypasses service classes; 0% coverage | Same: ruff gate passes on syntactically valid tests |
| WC-029 | `router.py` calls `get_all_provider_status()` — actual method is `get_all_runway_statuses()` | Router generated from spec prose; service's concrete symbols not in LLM context |
| WC-029 | `await FounderActionGenerator.maybe_create(...)` — sync classmethod | Call site generated without reading callee's `async def`/`def` declaration |
| WC-029 | `router.py` wires wrong `ProviderRunwayStatus` type (interface vs models layer) | No type unification check across independently generated files |
| WC-029 | Router's `ProcurementService.__init__` not passed `founder_action_generator` | Constructor signature in generated file not back-referenced when writing caller |
| WC-030 | `wallet/models.py` never generated; `wallet/service.py` imports it | `import` statements in generated code never treated as generation obligations |

**Common thread across all seven defects:** the pipeline generates each file with only the spec text as context. Already-generated artifacts — concrete method names, field names, type definitions, constructor signatures — are invisible to the generator at call sites. Tests are generated but never executed. The output of one generation step never feeds back into the next.

---

## 3. Root cause summary (5-why)

The five-why analysis converges on four structural absences:

**A. No runtime gate on test tasks**  
`compile_gate="ruff"` for test `SubTaskDef` means tests are syntax-checked but never run. A test file that mocks the SUT and produces 0% coverage passes the gate without any signal.

**B. Generation context is spec-only**  
Every LLM call receives the spec and the skeleton. It does not receive the symbol table of already-generated files. Method names, field names, and constructor signatures are re-derived from spec prose at each generation step, introducing drift at every inter-file boundary.

**C. No subject-under-test anchor in test generation**  
The test `constitutional_check` says "≥90% coverage" in prose. There is no structural rule that prevents the LLM from satisfying this requirement by mocking the SUT. The distinction between "mock the dependencies" and "mock the subject" is not encoded in the generation contract.

**D. Import statements are never treated as obligations**  
When a generated file contains `from wallet.models import BucketBalance`, the pipeline records that the file was written but never probes whether `wallet/models.py` exists and exports `BucketBalance`. A generated import is a commitment that is never verified.

---

## 4. Design principles for v2

**P1 — Every test file must be executed, not merely linted.**  
The gate on a test `SubTaskDef` must be `pytest_cov`, not `ruff`. Coverage must be measured and must meet the DoD threshold before the task can be marked complete.

**P2 — Generated artifacts must feed subsequent generation steps.**  
When the LLM generates `service.py`, its concrete symbol table (methods, signatures, field names) must be extracted and made available to the router generation step and to the test generation step. The spec's informal names are permitted as starting intent; the generated code's concrete names are the binding contract.

**P3 — Test generation must have an explicit SUT anchor.**  
Every test `SubTaskDef` carries a `sut_module` field identifying the module under test. The `constitutional_check` template enforces: that module must be imported and instantiated directly; mocking it at the class level is a gate violation.

**P4 — Import obligations must be verified after every generation step.**  
After each Python file is written, attempt `python3 -c "import <module>"` in the test environment. Failure adds the missing module to the current sprint's pending task list and prevents task completion.

**P5 — Each phase is independently re-runnable.**  
A phase that fails must be re-runnable from exactly where it failed, with all prior phase artifacts available. Manual intervention to re-run should require at most a single trigger.

**P6 — The pipeline's own completeness is measurable.**  
Each phase defines objective pass/fail criteria. A sprint's phase state is persisted in a structured file. Progress is visible at any point without reading code.

---

## 5. Phase model

The current pipeline's 5-job flow (preflight → execute → report → review → monitor) is retained. The `execute` job is internally restructured from a single SubTaskDef chain into a **seven-phase sequence**, where each phase is a distinct, re-runnable group of SubTaskDefs with its own gate.

```
INPUT: Work Contract WC-NNN-*.md + EA Skeleton
                    │
       ┌────────────▼────────────┐
  P0   │  PREFLIGHT              │  (existing Job 1, unchanged)
       │  halt check, SIM gate,  │
       │  index build            │
       └────────────┬────────────┘
                    │ halt=false
       ┌────────────▼────────────┐
  P1   │  DESIGN EMERGENCE       │  ◄── NEW
       │  Interface definitions, │
       │  SQL DDL amendments,    │
       │  DI map, import graph   │
       └────────────┬────────────┘
                    │ gate: design_verify
       ┌────────────▼────────────┐
  P2   │  SOURCE GENERATION      │  (existing execute, enhanced)
       │  Bodies only, skeleton  │
       │  frozen, symbol context │
       │  from P1 artifacts      │
       └────────────┬────────────┘
                    │ gate: ruff + import_check
       ┌────────────▼────────────┐
  P3   │  UNIT TEST GENERATION   │  (existing, gate changed)
       │  SUT-anchored,          │
       │  sut_module enforced,   │
       └────────────┬────────────┘
                    │ gate: pytest_cov (≥90%) + mutation (≥70%)
       ┌────────────▼────────────┐
  P4   │  STATIC ANALYSIS        │  ◄── NEW
       │  mypy, bandit,          │
       │  radon (complexity),    │
       │  vulture (dead code)    │
       └────────────┬────────────┘
                    │ gate: static_analysis_pass
       ┌────────────▼────────────┐
  P5   │  INTEGRATION TESTS      │  ◄── NEW
       │  Real app + aiosqlite   │
       │  real HTTP via httpx    │
       │  response shape check   │
       └────────────┬────────────┘
                    │ gate: pytest (integration suite)
       ┌────────────▼────────────┐
  P6   │  CONTRACT + SECURITY    │  ◄── NEW
       │  schemathesis vs        │
       │  OpenAPI spec,          │
       │  bandit OWASP scan,     │
       │  SQL parameterization   │
       └────────────┬────────────┘
                    │ gate: contract_pass + security_pass
       ┌────────────▼────────────┐
  P7   │  SYSTEM / CCT           │  (existing CCT, promoted to phase)
       │  All CCTs from WC,      │
       │  assembled services,    │
       │  constitutional checks  │
       └────────────┬────────────┘
                    │ gate: all CCTs pass
       ┌────────────▼────────────┐
       │  REVIEW + MERGE         │  (existing Jobs 3, 4, 5, unchanged)
       └─────────────────────────┘
```

---

## 6. Phase specifications

### P1 — Design Emergence

**Purpose:** Produce machine-readable contracts that all subsequent generation steps consume as their symbol source. Eliminates spec-prose-to-code name drift.

**Inputs:**
- WC-NNN spec (goal layer: what to achieve)
- EA Skeleton (existing — interface ABCs with exact signatures)
- Existing `infrastructure/postgres/init/*.sql` files

**Outputs (new artifacts committed to branch):**
- `.pipeline/<WC-NNN>/design/interfaces.py` — consolidated import of all ABCs relevant to this sprint; serves as frozen symbol manifest
- `.pipeline/<WC-NNN>/design/models.py` — all dataclasses/Pydantic models with exact field names; one class per concept; cross-referenced to the EA skeleton
- `.pipeline/<WC-NNN>/design/schema.sql` — SQL DDL amendments this sprint's services will query (CREATE TABLE IF NOT EXISTS for new tables)
- `.pipeline/<WC-NNN>/design/di_map.json` — dependency injection wiring: `{"ServiceClass": {"param_name": "factory_function", "source_module": "..."}}`
- `.pipeline/<WC-NNN>/design/import_graph.json` — `{"module_path": ["dependency_module_path", ...]}`

**Gate: `design_verify`**
1. `python3 -c "import interfaces; import models"` — design artifact files are importable
2. `openapi-spec-validator` on the generated OpenAPI spec (if applicable)
3. SQL DDL applied to `:memory:` SQLite — all `CREATE TABLE` statements execute cleanly
4. Import graph is a valid DAG (no cycles)

**Failure behaviour:** Generate specific design artifact that failed. Do not retry the full phase.

**SubTaskDef fields introduced:**
```python
SubTaskDef(
    id="WC028-D01",
    description="Generate design artifacts: interface manifest, model definitions, SQL DDL",
    type="llm",
    generation_phase="design",      # new phase value
    compile_gate="design_verify",   # new gate type
    inject_source_files=[
        "src/billing-engine/skeleton/wbe_interfaces.py",
        "infrastructure/postgres/init/12-billing-engine.sql",
    ],
    output_files=[
        ".pipeline/WC-028/design/interfaces.py",
        ".pipeline/WC-028/design/models.py",
        ".pipeline/WC-028/design/schema.sql",
        ".pipeline/WC-028/design/di_map.json",
    ],
    constitutional_check=(
        "Produce design artifacts only — no implementation logic.\n"
        "interfaces.py: re-export all ABCs from skeleton with exact method signatures unchanged.\n"
        "models.py: one class definition per concept; field names must be valid Python identifiers.\n"
        "schema.sql: CREATE TABLE IF NOT EXISTS for every table referenced in this sprint's service methods.\n"
        "di_map.json: every service class that has constructor dependencies must be listed.\n"
        "DO NOT invent symbol names — use names exactly as they appear in the injected skeleton.\n"
    ),
)
```

---

### P2 — Source Generation (enhanced)

**Change from current:** `inject_source_files` for each implementation SubTaskDef must now include the P1 design artifacts:
- `.pipeline/<WC-NNN>/design/interfaces.py`
- `.pipeline/<WC-NNN>/design/models.py`
- `.pipeline/<WC-NNN>/design/di_map.json`

This gives the LLM concrete symbol names at every call site. No method names, field names, or type names may be invented that do not appear in these injected files.

**New `compile_gate` step added after `ruff`:** `import_check`

```python
# In run_compile_gate, new gate type "import_check":
# For each output_file, attempt: python3 -c "import <derived_module_path>"
# Failure is non-retryable — the missing module must be added to the sprint manifest.
```

**New `constitutional_check` constraint (added to all implementation SubTaskDefs):**
```
SYMBOL CONSTRAINT: Every class name, method name, field name, and SQL table name used
in this file must appear in one of the injected design artifact files.
DO NOT invent or rename symbols. If a symbol you need does not appear in the design
artifacts, output SPEC_GAP with the missing symbol name — do not guess.
```

---

### P3 — Unit Test Generation (gate changed)

**Current:** `compile_gate="ruff"`  
**New:** `compile_gate="pytest_cov"`

**New `SubTaskDef` field:** `sut_module: str = ""`

```python
SubTaskDef(
    id="WC028-03",
    sut_module="src/billing-engine/meter/service.py",   # NEW FIELD
    compile_gate="pytest_cov",                           # CHANGED
    ...
)
```

**New `pytest_cov` gate in `run_compile_gate`:**
```python
if gate_type == "pytest_cov":
    # Derive --cov target from sut_module path
    cov_target = derive_cov_target(target_files, sut_module)
    result = subprocess.run(
        ["python3", "-m", "pytest", *pytest_targets,
         f"--cov={cov_target}", "--cov-fail-under=90",
         "--cov-report=term-missing", "-q", "--tb=short"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.returncode == 0, (result.stdout + result.stderr)[-800:]
```

**New SUT guard appended to all test `constitutional_check` templates in `task_decomposer.py`:**
```
SUT GUARD (mandatory): The module under test is {sut_module}.
- MUST: import and instantiate {ClassName} directly from its module.
- MUST: mock only external I/O (AsyncSession, Redis, HTTP clients, file system).
- MUST NOT: assign MagicMock() or AsyncMock() to {ClassName} itself.
- MUST NOT: create a fixture named mock_{ClassName} that returns a MagicMock.
A test that mocks the SUT produces 0% coverage and will fail the pytest_cov gate.
Verify: `from {module} import {ClassName}` must appear at module level, not inside a fixture.
```

---

### P4 — Static Analysis (new)

**Purpose:** Catch type errors, security vulnerabilities, and complexity violations that ruff cannot see.

**Gate: `static_analysis_pass`** — all four tools must pass:

| Tool | Command | Failure threshold |
|------|---------|-------------------|
| `mypy` | `mypy src/billing-engine/<module>/ --ignore-missing-imports --strict` | Any error |
| `bandit` | `bandit -r src/billing-engine/<module>/ -ll` (medium+ severity only) | Any medium/high finding |
| `radon` | `radon cc src/billing-engine/<module>/ -n C` (complexity grade C+ flagged) | Any function with CC > 10 |
| `vulture` | `vulture src/billing-engine/<module>/ --min-confidence 80` | Unused public functions |

**Implementation in `run_compile_gate`:**
```python
if gate_type == "static_analysis_pass":
    failures = []
    # mypy
    r = subprocess.run(["python3", "-m", "mypy", *targets, "--ignore-missing-imports"], ...)
    if r.returncode != 0: failures.append(f"mypy: {r.stdout[:300]}")
    # bandit
    r = subprocess.run(["python3", "-m", "bandit", "-r", *targets, "-ll"], ...)
    if r.returncode != 0: failures.append(f"bandit: {r.stdout[:300]}")
    # radon
    r = subprocess.run(["python3", "-m", "radon", "cc", *targets, "-n", "C"], ...)
    if r.stdout.strip(): failures.append(f"complexity: {r.stdout[:300]}")
    return len(failures) == 0, "\n".join(failures)
```

**SubTaskDef for P4** (deterministic — no LLM call):
```python
SubTaskDef(
    id="WC028-P4",
    description="Static analysis: mypy, bandit, radon, vulture",
    type="deterministic",
    generation_phase="static_analysis",
    compile_gate="static_analysis_pass",
    depends_on=["WC028-03"],   # depends on unit test phase completing
    template_fn=lambda: True,  # gate is the work
    service_dir="src/billing-engine/meter",
)
```

If P4 fails, the pipeline generates a targeted fix SubTaskDef scoped to the failing tool's output (mypy errors → annotate types; bandit → parameterize SQL; radon → extract function).

---

### P5 — Integration Tests (new)

**Purpose:** Verify that the assembled service responds correctly to real HTTP requests with a real in-memory database. Catches type mismatches (Pattern E), DI wiring failures, and response shape errors that unit tests are structurally blind to because they mock the service layer.

**Key distinction from unit tests:**
- No service-layer mocks. The real `MeterService`, `ProcurementService`, etc. are instantiated.
- Database layer: real `aiosqlite` in-memory DB populated with the P1 schema DDL.
- HTTP layer: real `httpx.AsyncClient` + `ASGITransport(app=real_app)`.

**`compile_gate="pytest_integration"`**:
```python
if gate_type == "pytest_integration":
    result = subprocess.run(
        ["python3", "-m", "pytest", *pytest_targets,
         "-m", "integration", "-q", "--tb=short"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.returncode == 0, (result.stdout + result.stderr)[-800:]
```

Integration tests are tagged `@pytest.mark.integration` so they are excluded from the unit test run (P3) and only run in P5.

**SubTaskDef template:**
```python
SubTaskDef(
    id="WC028-P5",
    description="Integration tests: real app + aiosqlite, all endpoints",
    type="llm",
    generation_phase="integration",
    compile_gate="pytest_integration",
    sut_module="src/billing-engine/meter/service.py",
    depends_on=["WC028-P4"],
    inject_source_files=[
        ".pipeline/WC-028/design/schema.sql",
        "src/billing-engine/meter/router.py",
        "src/billing-engine/meter/service.py",
    ],
    constitutional_check=(
        "Write @pytest.mark.integration tests.\n"
        "Use real aiosqlite in-memory DB, seeded from design/schema.sql.\n"
        "Use httpx.AsyncClient(transport=ASGITransport(app=real_app)).\n"
        "DO NOT mock the service layer. Mock only external services (Redis, WhatsApp).\n"
        "Every router endpoint must have at least one integration test verifying "
        "status code AND response body shape against the OpenAPI spec.\n"
    ),
)
```

---

### P6 — Contract + Security (new)

**Contract tests** use `schemathesis` to generate test cases automatically from the OpenAPI spec and run them against the service. Zero manual test writing required.

```bash
# Contract gate command:
schemathesis run openapi.json --app=billing_engine:app --checks=all
```

**Security tests** extend the existing `bandit` check (already in P4) with two targeted checks:
1. **SQL injection scan:** Grep all `text()` calls for f-string interpolation (`f"... {variable}"` inside `text()`). Any finding = gate failure.
2. **Secret leak scan:** Grep source for hardcoded strings matching token/key patterns.

**`compile_gate="contract_security_pass"`** runs schemathesis + SQL injection grep + secret scan.

---

### P7 — System / CCT (promoted from ad-hoc)

CCT tests already exist (CCT-BILLINGLOOP-01, CCT-SELFAUDIT-01, etc.). In the current pipeline they live in unit test files and run against mocked components. In v2 they are promoted to a dedicated phase and run against the assembled service stack using the P5 aiosqlite setup.

The WC spec's "CCT-XX-NN: scenario → expected outcome" items become the test specification for this phase. One CCT test per spec item.

**Gate:** all CCTs listed in the WC must be present in this test file and pass.

---

## 7. Phase state model

Each sprint maintains a phase state file throughout its lifecycle:

**Location:** `.pipeline/<WC-NNN>/phase-state.json`

**Schema:**
```json
{
  "sprint": "WC-028",
  "current_phase": 3,
  "phases": {
    "0": {"status": "passed", "gate": "preflight", "completed_at": "2026-08-06T10:00:00Z"},
    "1": {"status": "passed", "gate": "design_verify", "completed_at": "2026-08-06T10:05:00Z",
          "artifacts": [".pipeline/WC-028/design/interfaces.py", "..."]},
    "2": {"status": "passed", "gate": "ruff+import_check", "completed_at": "2026-08-06T10:20:00Z"},
    "3": {"status": "failed", "gate": "pytest_cov",
          "failure": "coverage 73% < 90% threshold",
          "failed_at": "2026-08-06T10:35:00Z",
          "retry_count": 1}
  },
  "blocking_defect": "coverage_below_threshold",
  "last_updated": "2026-08-06T10:35:00Z"
}
```

**Status values:** `pending` | `running` | `passed` | `failed` | `skipped`

**Phase state is written by `sprint_state.py`** (already exists in scripts/) — extend it with `update_phase_status(sprint_id, phase, status, detail)`.

---

## 8. Re-run design

**Re-running a single phase:**
```bash
# Trigger phase 3 (unit tests) for WC-028 without re-running P1, P2:
gh workflow run autonomous-sprint.yaml \
  -f sprint_name=WC-028 \
  -f resume_from_phase=3
```

**How it works:**
1. Preflight reads `phase-state.json` to determine last passed phase
2. `resume_from_phase` parameter overrides the start point
3. All phases before `resume_from_phase` are marked `skipped` in the new run
4. Design artifacts from `.pipeline/<WC-NNN>/design/` are available without regeneration

**Automatic phase chaining:** When a phase gate passes, `sprint_state.py` writes `status: passed` and `autonomous_sprint_runner.py` automatically queues the next phase. No human trigger needed between phases within the same run.

**Partial re-generation (within a phase):** If P3 fails because a specific test file has 73% coverage, the pipeline re-generates only that test file (using the coverage report's missing-lines output as a constraint in `constitutional_check`), not the entire test suite.

---

## 9. Lifecycle diagram

```
WC file pushed + workflow_dispatch
         │
         ▼
  P0 PREFLIGHT ──(fail)──► HALT (requires founder)
         │ pass
         ▼
  P1 DESIGN ──(fail)──► regenerate design artifact ──► retry P1 (max 3)
         │ pass
         ▼
  P2 SOURCE ──(fail: ruff)──► LLM fix loop (existing)
           └─(fail: import_check)──► add missing module to manifest ──► retry P2
         │ pass
         ▼
  P3 UNIT TESTS ──(fail: coverage)──► LLM re-generates test file with coverage context
              └─(fail: mutation)──► LLM strengthens test assertions
         │ pass
         ▼
  P4 STATIC ──(fail: mypy)──► LLM adds type annotations to flagged functions
           └─(fail: bandit)──► LLM parameterizes SQL / removes hardcoded values
           └─(fail: radon)──► LLM extracts complex function into smaller helpers
         │ pass
         ▼
  P5 INTEGRATION ──(fail)──► LLM fixes source or DI wiring based on error output
         │ pass
         ▼
  P6 CONTRACT+SECURITY ──(fail: schemathesis)──► LLM fixes response shape
                      └─(fail: SQL injection)──► LLM adds .bindparams()
         │ pass
         ▼
  P7 CCT/SYSTEM ──(fail)──► SPEC_GAP (routes to EA — constitutional issue)
         │ pass
         ▼
  PR REVIEW ──► MERGE ──► complete_sprint.py
```

**Consecutive failure limit:** 3 retries per phase before escalating to `SPEC_GAP` or `INFRA_FAILURE` (same classification as current `sprint_monitor.py` — no change needed).

---

## 10. Implementation plan

This is a refactor of the existing pipeline. No new infrastructure is required. All changes are to existing Python scripts and the YAML workflow.

### Stage 1 — Immediate fixes (1–2 days, highest ROI)

These fix the three audited WC failures with minimal code change.

**1a. Change test SubTaskDef compile_gate in `task_decomposer.py`**

Find every SubTaskDef where `generation_phase="test"` or the description contains "test" and `compile_gate="ruff"`. Change to `compile_gate="pytest_cov"`.

Affects: all `_build_test_subtask()` calls in `task_decomposer.py` and all hardcoded test SubTaskDefs in `groom_sprint.py`.

**1b. Add `pytest_cov` gate to `run_compile_gate` in `task_decomposer.py`**

```python
if gate_type == "pytest_cov":
    sut_cov = _derive_cov_target(task_id, target_files)
    cmd = ["python3", "-m", "pytest", *pytest_targets, "--tb=short", "-q"]
    if sut_cov:
        cmd += [f"--cov={sut_cov}", "--cov-fail-under=90", "--cov-report=term-missing"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    return result.returncode == 0, (result.stdout + result.stderr)[-800:]
```

`_derive_cov_target` maps test file path to source module path (e.g., `tests/billing-engine/test_meter.py` → `src/billing-engine/meter`).

**1c. Add `sut_module` field to `SubTaskDef` and SUT guard to test constitutional_check template**

Add `sut_module: str = ""` to the `SubTaskDef` dataclass. In `_build_effective_check()`, append the SUT guard text when `sut_module` is set. The groomer (`groom_sprint.py`) derives `sut_module` from the test file's name.

**Expected outcome:** WC-028 and WC-029 test failures would not recur. 0% coverage becomes an immediate gate failure, not a silent pass.

---

### Stage 2 — Symbol context (3–5 days)

This addresses the method name drift defects.

**2a. Add `import_check` gate to `run_compile_gate`**

```python
if gate_type == "import_check":
    for f in target_files:
        module = _filepath_to_module(f)
        r = subprocess.run(
            ["python3", "-c", f"import {module}"],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src/billing-engine")},
            cwd=REPO_ROOT,
        )
        if r.returncode != 0:
            return False, f"ImportError: {module}\n{r.stderr[:400]}"
    return True, ""
```

**2b. Change implementation SubTaskDef compile_gate from `ruff` to `ruff+import_check`**

The `+` syntax triggers a sequential gate: ruff runs first, then import_check.

```python
if "+" in gate_type:
    for g in gate_type.split("+"):
        passed, err = run_compile_gate(g, service_dir, target_files, task_id)
        if not passed:
            return False, f"[{g}] {err}"
    return True, ""
```

**2c. Add P1 design artifacts to `inject_source_files` in groomer**

`groom_sprint.py` reads the P1 design artifact paths for the current sprint and appends them to every implementation SubTaskDef's `inject_source_files`. If P1 artifacts don't exist yet (first run), the groomer generates a P1 SubTaskDef and sets it as a dependency.

---

### Stage 3 — Static analysis phase (2–3 days)

**3a. Add `static_analysis_pass` gate to `run_compile_gate`**

Implements the mypy + bandit + radon + vulture sequence described in §6.

**3b. Add P4 `SubTaskDef` type: `generation_phase="static_analysis"` with `type="deterministic"`**

The P4 SubTaskDef has no LLM call. It runs the gate and, on failure, emits a structured error JSON that becomes the `constitutional_check` constraint for a targeted fix SubTaskDef.

**3c. Install tools in pipeline environment**

```yaml
# In autonomous-sprint.yaml, add to setup step:
- run: pip install mypy bandit radon vulture
```

---

### Stage 4 — Integration test phase (5–7 days)

**4a. Add `pytest_integration` gate and `@pytest.mark.integration` marker**

Register `integration` marker in `pyproject.toml`. The unit test run uses `-m "not integration"`; the integration run uses `-m integration`.

**4b. Add P5 SubTaskDef template to groomer**

The groomer generates a P5 SubTaskDef for each service sprint, injecting the design schema DDL and router file. The constitutional_check enforces "real DB, no service mocks."

**4c. Add aiosqlite test fixture to conftest**

```python
@pytest.fixture
async def real_db_session(design_schema_path):
    # Applies P1 schema.sql to aiosqlite in-memory DB
    # Returns async_sessionmaker bound to that DB
    ...
```

---

### Stage 5 — Design emergence phase (7–10 days)

**5a. Add `design_verify` gate**

Implements the importability check + OpenAPI validation + SQLite DDL probe described in §6.

**5b. Add P1 SubTaskDef template to groomer**

Generating design artifacts is itself an LLM task with `generation_phase="design"`. The design SubTaskDef is always the first dependency in the sprint graph.

**5c. Add `.pipeline/` directory convention**

`autonomous_sprint_runner.py` creates `.pipeline/<WC-NNN>/design/` before the execute job begins. Design artifacts are committed alongside source code.

---

### Stage 6 — Contract, security, CCT phases (5–7 days)

Implement P6 and promote P7 as described in §6. Lowest urgency — P1–P4 address all defects found in the audits. P5–P7 provide defence-in-depth.

---

## 11. Gate specification reference

| Gate ID | Command pattern | Pass condition | Failure action |
|---------|----------------|----------------|----------------|
| `ruff` | `ruff check --fix` | zero violations | LLM fix loop |
| `pytest` | `pytest -q --tb=short` | returncode=0 | LLM fix loop |
| `pytest_cov` | `pytest --cov=X --cov-fail-under=90` | returncode=0 + ≥90% | LLM regenerates test file with coverage context |
| `import_check` | `python3 -c "import X"` | returncode=0 for all outputs | Add missing module to sprint manifest |
| `design_verify` | import + openapi-validate + sqlite DDL | all pass | LLM regenerates failing artifact |
| `static_analysis_pass` | mypy + bandit + radon + vulture | zero findings | LLM targeted fix per tool |
| `pytest_integration` | `pytest -m integration` | returncode=0 | LLM fixes source or DI wiring |
| `contract_security_pass` | schemathesis + sql-inject grep | zero violations | LLM response shape fix |
| `mutation` | `mutmut run` + `mutmut results` | mutation score ≥70% | LLM strengthens assertions |

---

## 12. SubTaskDef field reference (v2)

The `SubTaskDef` dataclass acquires three new fields (backward compatible — all have defaults):

```python
@dataclass
class SubTaskDef:
    # ... all existing fields unchanged ...

    # v2 additions:
    sut_module: str = ""
    # Path to the module under test. When set on a test SubTaskDef, the SUT guard
    # constraint is injected into constitutional_check and the pytest_cov gate
    # uses this path to derive the --cov target.

    phase: int = 0
    # Pipeline phase number (0-7). Used by sprint_state.py to group SubTaskDefs
    # and by the runner to determine resume_from_phase behavior.

    design_artifacts: list[str] = field(default_factory=list)
    # Paths to P1 design artifacts to inject (supplements inject_source_files).
    # Populated automatically by the groomer once P1 completes.
```

`generation_phase` values (extending existing):
- `"full"` — legacy single-pass (default, backward compatible)
- `"skeleton"` — existing
- `"logic"` — existing
- `"test"` — existing (gate now `pytest_cov` instead of `ruff`)
- `"design"` — NEW: P1 design artifact generation
- `"static_analysis"` — NEW: P4, deterministic
- `"integration"` — NEW: P5 integration test generation
- `"contract"` — NEW: P6 contract test

---

## 13. Operating instructions

### Starting a sprint

No change from current procedure. Founder pushes `WC-NNN-*.md` + triggers `workflow_dispatch`. The groomer detects the new WC, generates SubTaskDefs (now including a P1 design SubTaskDef), and chains them in phase order.

### Resuming a failed sprint

```bash
# Check phase state:
cat .pipeline/WC-028/phase-state.json

# Resume from phase 3 (unit tests) after manual analysis:
gh workflow run autonomous-sprint.yaml \
  -f sprint_name=WC-028 \
  -f resume_from_phase=3

# Resume from phase 3, force-regenerate the test file:
gh workflow run autonomous-sprint.yaml \
  -f sprint_name=WC-028 \
  -f resume_from_phase=3 \
  -f force_subtask=WC028-03
```

### Overriding a gate (emergency only)

```bash
# Skip a gate — requires Founder authorization comment in the sprint issue:
gh workflow run autonomous-sprint.yaml \
  -f sprint_name=WC-028 \
  -f skip_gate=mutation \
  -f skip_gate_reason="IB-042: mutmut incompatible with aiosqlite, deferred"
```

Gate skips are logged to `constitution/PROJECT_STATE.md` with the reason.

### Monitoring phase progress

The existing `sprint_status_reporter.py` (Job 3) is extended to read `phase-state.json` and include a phase progress table in the Issue #7 dashboard:

```
WC-028 Phase Progress:
  P0 preflight        ✅ passed  10:00
  P1 design           ✅ passed  10:05
  P2 source gen       ✅ passed  10:20
  P3 unit tests       ❌ failed  10:35  coverage 73% < 90%
  P4 static analysis  ⏳ pending
  P5 integration      ⏳ pending
  P6 contract+sec     ⏳ pending
  P7 CCT              ⏳ pending
```

---

## 14. Success metrics

The pipeline v2 is fully implemented when the following measurements hold across 3 consecutive sprints:

| Metric | Current baseline | v2 target |
|--------|-----------------|-----------|
| Test coverage at PR merge | Unknown (not measured) | ≥90% every sprint |
| Source bugs found at audit | 4–6 per sprint | 0 |
| Mock-the-SUT test pattern | Present in every test sprint | 0 occurrences |
| Method name drift bugs | 1–3 per sprint | 0 |
| Missing module bugs | 1 per sprint | 0 |
| Phases completed without human intervention | ~1 (execute) | 7 |
| Manual remediation sessions per sprint | 1 (this work) | 0 |

---

## 15. Implementation tracking

Track implementation progress as IB items in `constitution/INSTITUTIONAL_BACKLOG.md`. Suggested breakdown:

| IB | Stage | Effort | Priority |
|----|-------|--------|----------|
| IB-P2A | Stage 1: `pytest_cov` gate + test compile_gate change | 1 day | P0 |
| IB-P2B | Stage 1: `sut_module` field + SUT guard in constitutional_check | 1 day | P0 |
| IB-P2C | Stage 2: `import_check` gate + symbol context injection | 3 days | P1 |
| IB-P2D | Stage 3: `static_analysis_pass` gate (mypy, bandit, radon) | 2 days | P1 |
| IB-P2E | Stage 4: Integration test phase (P5) + aiosqlite fixture | 5 days | P2 |
| IB-P2F | Stage 5: Design emergence phase (P1) + design artifact templates | 7 days | P2 |
| IB-P2G | Stage 6: Contract, security, CCT phases (P6, P7) | 5 days | P3 |
| IB-P2H | Phase state file, re-run mechanism, status reporter extension | 3 days | P1 |

Stage 1 (IB-P2A + IB-P2B) closes the highest-impact defect class (0% coverage escaping the pipeline) in approximately two days and can be implemented in a single Copilot session before the next sprint runs.

---

*This document is a living specification. As each IB item is implemented, update the corresponding section with the actual implementation details and close the IB item.*
