#!/usr/bin/env python3
"""
autonomous_sprint_runner.py

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Skill 8 — SDLC Execution)
# constitutional_basis: C-023 (Evidence First), C-041 (ValidateAction), C-059 (Traceability),
#                       C-065 (SDLC Separation — Author hat), C-066 Tier 2A (autonomous execution),
#                       C-070 (Constitutional DNA — all 3 instincts apply to this agent),
#                       C-007/C-027 (Append-only enforcement — validated in WC011-02),
#                       C-077 (Dev Tooling Cost Ceiling ₹5,000/month — ADR-030)
# ib_item: IB-009, IB-020
# office: Platform IT Expert — Implementation hat
# refactored: 2026-07 — extracted into runner/ package (see scripts/runner/)

Implementation hat — executes sprint tasks, opens PR.
Called by autonomous-sprint.yaml Job 1 (execute).
C-065: This script is the AUTHOR. Never the reviewer.

Architecture note (post-refactor):
  This file is the entry-point CLI + TASK_HANDLERS registry.
  All functional modules are in scripts/runner/:
    runner/constants.py    — REPO_ROOT, paths, write-boundary constants
    runner/state.py        — shared mutable runtime state (_MONITOR_SIGNAL, _INFRA_ERROR_TASKS)
    runner/git_ops.py      — shell/git/gh helpers
    runner/system_prompts.py — constitutional system prompt + stack expert blocks
    runner/sprint_ops.py   — sprint state parsing, phase gate, integrity checks
    runner/llm_codegen.py  — LLM call (call_llm_via_magiclm), file parse/write/validate
    runner/task_executor.py — execute_with_llm, flag_spec_gap

  WC011–WC015 are complete. All sprint handling now via groom_sprint.py → SubTaskDef → execute_with_llm.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
EVIDENCE_LOG = REPO_ROOT / "logs" / "bootstrap-evidence.jsonl"

# TaskDecomposer — sub-task decomposition for multi-layer sprint tasks (IB-021 / WC-019)
# Implements: architecture/reference/pipeline/dependency-graph-task-decomposition.md
# constitutional_basis: C-084 (Step Dependency), C-086 (Pre-Execution Simulation)
import importlib.util as _ilu
import sys as _sys
_td_path = str(Path(__file__).parent / "task_decomposer.py")
_td_spec = _ilu.spec_from_file_location("task_decomposer", _td_path)
_td_mod = _ilu.module_from_spec(_td_spec)
_td_mod.__file__ = _td_path          # required for Path(__file__) inside task_decomposer
_sys.modules["task_decomposer"] = _td_mod
_td_spec.loader.exec_module(_td_mod)
SubTaskDef = _td_mod.SubTaskDef
_execute_task_decomposed = _td_mod.execute_subtask_chain
_check_simulation = _td_mod.check_simulation_exists

# ── ADR-030: File write boundary enforcement (C-059 + C-065) ─────────────────
ALLOWED_WRITE_ROOTS = [
    "src/",
    "tests/",
    "infrastructure/postgres/",
    "infrastructure/keycloak/",
    "logs/",
]

# ── Import runner/ package ─────────────────────────────────────────────────────
# All functional concerns extracted for industry-standard modularity.
# Symbols are imported into this namespace so run_runner_integrity_checks(globals()) can verify them.
_runner_pkg = str(Path(__file__).parent)
if _runner_pkg not in _sys.path:
    _sys.path.insert(0, _runner_pkg)

from runner.state import _MONITOR_SIGNAL, _INFRA_ERROR_TASKS          # shared mutable state
from runner.git_ops import run, git, gh, set_output, record_evidence  # shell helpers
from runner.sprint_ops import (                                         # sprint lifecycle
    parse_sprint_state, check_platform_phase_gate, update_sprint_state, run_runner_integrity_checks,
    parse_wc_tasks, update_task_status,
    write_run_heartbeat,
)
# Namespace injection — required by run_runner_integrity_checks(globals())  # noqa: F401
from runner.system_prompts import (                                     # noqa: F401
    _build_system_prompt, _TASK_STACK_MAP,
    CONSTITUTIONAL_SYSTEM_PROMPT, get_branch_context,
)
from runner.llm_codegen import (                                        # noqa: F401
    call_llm_via_magiclm,
    parse_llm_files, write_llm_files, validate_written_files,
)
from runner.task_executor import execute_with_llm, flag_spec_gap        # noqa: F401

# ── Sprint scaffold gate (C-069) ──────────────────────────────────────────────
# SCAFFOLD_TASKS: explicitly declared — never inferred from position.
# If a scaffold task fails, all downstream tasks cannot compile. The monitor uses this
# to distinguish CASCADE_PIPELINE_BUG from SPEC_GAP_GENUINE.
SCAFFOLD_TASKS: frozenset[str] = frozenset({
    "WC016-01", "WC017-01", "WC018-01",
})

TASK_HANDLERS = {
        "WC027-01a": {
        "subtasks": [
            SubTaskDef(
                id="WC027-01aa",
                description="Implement BundleEngine markup derivation and constitutional price validation with audit logging.",
                type="udcp",
                depends_on=[],
                compile_gate="py_compile",
                service_dir="src/billing-engine",
                wc_task_id="WC027-01a",
                stack="python",
                output_files=[
                    "src/billing-engine/markup/models.py",
                    "src/billing-engine/markup/bundle_engine.py",
                ],
                inject_source_files=[
                    "src/billing-engine/skeleton/wbe_interfaces.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-01a",
                },
                constitutional_check=(
                    "Implement IMarkupEngine.derive_bundle_cost_floor() and IMarkupEngine.validate_price() from skeleton.\n"
                    "DO NOT change method signatures — implement bodies only (ADR-036).\n"
                    "Type annotations optional in scaffold — polish pass enforces ANN001.\n"
                    "C-089: validate_price() MUST enforce constitutional minimum margin floor and raise BelowConstitutionalFloorError if breached.\n"
                    "C-059: validate_price() MUST write to pricing_floor_log on BOTH APPROVED and REJECTED outcomes for audit.\n"
                    "derive_bundle_cost_floor() reads bundle_profiles.cost_floor_paise from DB — do NOT recompute.\n"
                    "derive_price() applies margin-on-revenue formula: floor / (1 - margin/100), defaulting to bundle_profiles.minimum_margin_pct.\n"
                    "PriceValidation response MUST include outcome, cost_floor_paise, minimum_compliant_price_paise, proposed_price_paise."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC027-01ab",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="udcp",
                depends_on=["WC027-01aa"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC027-01a",
                stack="python",
                output_files=[
                    "src/billing-engine/markup/models.py",
                    "src/billing-engine/markup/bundle_engine.py",
                ],
                inject_source_files=[
                    "src/billing-engine/markup/models.py",
                    "src/billing-engine/markup/bundle_engine.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-01a",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC027-01ac",
                description="Pytest suite covering Pydantic model validation and BundleEngine cost_floor/derive_price/validate_price behaviour, including C-059 audit-log invariant on both APPROVED and REJECTED outcomes.",
                type="udcp",
                depends_on=["WC027-01ab"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC027-01a",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_models.py",
                ],
                inject_source_files=[
                    "src/billing-engine/markup/models.py",
                    "src/billing-engine/markup/bundle_engine.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-01a",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "\n"
                    "## File header (mandatory, first two lines of test file)\n"
                    "# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a\n"
                    "# Constitutional basis: C-059 (audit obligation)\n"
                    "\n"
                    "## Pydantic model tests (test_models.py — models section)\n"
                    "- ThreadEntry: valid construction; reject missing required fields.\n"
                    "- BundleProfile: valid construction; assert cost_floor_paise and minimum_margin_pct are positive int/float.\n"
                    "- PriceConfig: valid round-trip; reject negative values.\n"
                    "- PriceValidationRequest: valid; reject if proposed_price_paise is missing.\n"
                    "- PriceDeriveRequest: valid; target_margin_pct is optional (defaults to None).\n"
                    "- PriceValidation response: assert fields outcome, cost_floor_paise,\n"
                    "  minimum_compliant_price_paise, proposed_price_paise all present and typed.\n"
                    "\n"
                    "## BundleEngine.cost_floor tests\n"
                    "- Happy path: mock DB row returns bundle_profiles.cost_floor_paise=50000;\n"
                    "  assert cost_floor('researcher', 'starter') == 50000 (reads from DB, no recomputation).\n"
                    "- Error case: unknown agent_type or bundle_tier → raises KeyError or equivalent domain exception.\n"
                    "- Idempotency: calling cost_floor twice with same args returns same value (DB mock called each time — no cached mutation).\n"
                    "\n"
                    "## BundleEngine.derive_price tests\n"
                    "- Happy path with explicit target_margin_pct=20:\n"
                    "  cost_floor=80000 → expected = ceil(80000 / (1 - 20/100)) = ceil(100000) = 100000.\n"
                    "  Assert derive_price('researcher','starter', target_margin_pct=20) == 100000.\n"
                    "- Happy path with target_margin_pct=None:\n"
                    "  DB bundle_profiles.minimum_margin_pct=25; cost_floor=80000 →\n"
                    "  expected = ceil(80000 / (1 - 25/100)) = ceil(106666.67) = 106667.\n"
                    "  Assert derive_price('researcher','starter') == 106667 (uses DB minimum_margin_pct).\n"
                    "- Formula invariant: derive_price result MUST be >= cost_floor for any valid margin 0 < m < 100.\n"
                    "- Error case: target_margin_pct >= 100 → raises ValueError (division by zero / nonsensical margin).\n"
                    "- Error case: target_margin_pct <= 0 → raises ValueError.\n"
                    "\n"
                    "## BundleEngine.validate_price tests — C-059 CRITICAL\n"
                    "- APPROVED happy path: proposed_price_paise >= minimum_compliant_price → outcome='APPROVED';\n"
                    "  assert pricing_floor_log insert was called exactly once.\n"
                    "- REJECTED path: proposed_price_paise < minimum_compliant_price → outcome='REJECTED';\n"
                    "  assert pricing_floor_log insert was called exactly once (C-059: audit on REJECTION too).\n"
                    "- Constitutional invariant (C-059): pricing_floor_log MUST be written for BOTH outcomes;\n"
                    "  parameterise the test over both APPROVED and REJECTED and assert db_insert_mock.call_count == 1 each.\n"
                    "- PriceValidation response fields: assert minimum_compliant_price_paise is returned and equals\n"
                    "  the derive_price result; assert cost_floor_paise matches cost_floor(); assert proposed_price_paise echoes input.\n"
                    "- Idempotency of audit log: calling validate_price twice → pricing_floor_log written twice\n"
                    "  (each call independently audited — log is append-only, not deduplicated).\n"
                    "- Error case: DB write to pricing_floor_log fails → propagate exception (do not silently swallow;\n"
                    "  C-059 audit MUST NOT be bypassed on error).\n"
                    "\n"
                    "## Fixture requirements\n"
                    "- Use pytest fixtures to provide a mock DB session (AsyncMock or MagicMock with async context manager).\n"
                    "- Mock the DB query for bundle_profiles to return a BundleProfile-like object with\n"
                    "  cost_floor_paise and minimum_margin_pct attributes.\n"
                    "- Mock the DB insert for pricing_floor_log to a MagicMock; assert call args include\n"
                    "  agent_type, bundle_tier, proposed_price_paise, outcome, and a timestamp field.\n"
                    "- Use pytest-asyncio for any async methods (mark with @pytest.mark.asyncio).\n"
                    "- All tests are exempt from ANN annotations per pyproject.toml per-file-ignores.\n"
                    "\n"
                    "## Ruff compliance\n"
                    "- No unused imports. No f-strings with no expressions. No bare excepts.\n"
                    "- Every test function name starts with test_.\n"
                    "- File passes ruff check with zero errors.\n"
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
        ]
    },
        "WC027-01b": {
        "subtasks": [
            SubTaskDef(
                id="WC027-01ba",
                description="Implement FastAPI router for pricing endpoints: /thread-catalog, /bundle-cost-floor, /validate (with C-089 floor enforcement), /derive; mount in main.py",
                type="udcp",
                depends_on=["WC027-01aa"],
                compile_gate="py_compile",
                service_dir="src/billing-engine",
                wc_task_id="WC027-01b",
                stack="python",
                output_files=[
                    "src/billing-engine/markup/router.py",
                    "src/billing-engine/main.py",
                ],
                inject_source_files=[
                    "src/billing-engine/skeleton/wbe_interfaces.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-01b",
                },
                constitutional_check=(
                    "Implement IMarkupEngine cost_floor(), derive_price(), and validate_price() method bodies.\n"
                    "DO NOT change signatures — implement bodies only (ADR-036).\n"
                    "Type annotations optional in scaffold — polish pass adds them (ANN001).\n"
                    "C-088: validate_price() MUST check billing_profiles.status == FOUNDER_AUTHORIZED before validation.\n"
                    "C-089: validate_price() MUST enforce constitutional minimum margin floor; return PriceValidation(outcome='REJECTED', cost_floor_paise=cost_floor, minimum_compliant_price_paise=cost_floor, proposed_price_paise=proposed_price) on violation; log to institutional.pricing_floor_log regardless.\n"
                    "C-090: renew() MUST reject if new plan price > agreed price without C-090 notice.\n"
                    "C-091: GET /thread-catalog delegates to existing ThreadCatalogService; returns thread definitions.\n"
                    "C-038: POST /validate returns 422 with minimum_compliant_price_paise field on C-089 floor violation.\n"
                    "C-048, C-051: include in router setup; wire through service injection."
                ),
                model_hint="auto",
                max_tokens=4000,
            ),
            SubTaskDef(
                id="WC027-01bb",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="udcp",
                depends_on=["WC027-01ba"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC027-01b",
                stack="python",
                output_files=[
                    "src/billing-engine/markup/router.py",
                    "src/billing-engine/main.py",
                ],
                inject_source_files=[
                    "src/billing-engine/markup/router.py",
                    "src/billing-engine/main.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-01b",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC027-01bc",
                description="Pytest suite covering the /pricing router (thread-catalog, bundle-cost-floor, validate, derive) mounted in main.py, including C-089 422 response shape, GET idempotency, and service-delegation contracts.",
                type="udcp",
                depends_on=["WC027-01bb"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC027-01b",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_router.py",
                ],
                inject_source_files=[
                    "src/billing-engine/markup/router.py",
                    "src/billing-engine/main.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-01b",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "\n"
                    "## Endpoints under test (prefix /pricing, mounted in main.py)\n"
                    "  1. GET  /pricing/thread-catalog\n"
                    "  2. GET  /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}\n"
                    "  3. POST /pricing/validate\n"
                    "  4. POST /pricing/derive\n"
                    "\n"
                    "## Test structure requirements\n"
                    "Use httpx.AsyncClient + pytest-asyncio with `@pytest.mark.asyncio`.\n"
                    "Import the FastAPI `app` from `main` (or `markup.router.router` as needed).\n"
                    "Mock all external service calls (ThreadCatalogService, DB, Redis) via\n"
                    "`unittest.mock.AsyncMock` / `pytest.monkeypatch` or `pytest.fixture`.\n"
                    "\n"
                    "## Happy-path cases (one test per endpoint)\n"
                    "  - GET /pricing/thread-catalog → 200, response is a list (may be empty list);\n"
                    "    assert ThreadCatalogService delegate was called exactly once.\n"
                    "  - GET /pricing/bundle-cost-floor/RESEARCHER/STARTER → 200, response body\n"
                    "    contains a numeric field representing the cost floor in paise (≥ 0).\n"
                    "  - POST /pricing/validate with a valid payload → 200, body does NOT contain\n"
                    "    `minimum_compliant_price_paise` key (no violation).\n"
                    "  - POST /pricing/derive with a valid payload → 200, body contains a derived\n"
                    "    price field in paise (integer ≥ 0).\n"
                    "\n"
                    "## Error / constitutional-invariant cases\n"
                    "  C-089 INVARIANT — POST /pricing/validate with a proposed price below the\n"
                    "  constitutional minimum MUST return HTTP 422 and the response JSON MUST\n"
                    "  contain the key `minimum_compliant_price_paise` with an integer value > 0.\n"
                    "  Write at least two parameterised sub-cases (zero paise, 1 paise below floor).\n"
                    "\n"
                    "  - POST /pricing/validate with a missing required field → 422 FastAPI\n"
                    "    validation error (standard Pydantic shape, NOT the C-089 shape).\n"
                    "  - GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} with an unknown\n"
                    "    agent_type or bundle_tier → 404 or 422 (assert the status code is not 200\n"
                    "    and not 500).\n"
                    "  - POST /pricing/derive with a malformed body → 422.\n"
                    "\n"
                    "## Idempotency invariants\n"
                    "  - GET /pricing/thread-catalog called twice with identical state MUST return\n"
                    "    identical payloads (assert response1.json() == response2.json()).\n"
                    "  - GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} called twice MUST\n"
                    "    return the same cost floor (idempotent read, no side-effects).\n"
                    "\n"
                    "## Router-mount invariant\n"
                    "  - Assert that `app.routes` (or `app.url_path_for`) resolves paths that start\n"
                    "    with `/pricing/` — confirming the router is mounted at the correct prefix\n"
                    "    in main.py.\n"
                    "\n"
                    "## Additional rules\n"
                    "  - File is exempt from ANN lint checks (per pyproject.toml per-file-ignores).\n"
                    "  - Do NOT use `.AsTask()`, `.TryGetValue()`, or any FORBIDDEN API patterns.\n"
                    "  - Do NOT import or instantiate DB/Redis clients directly; use fixtures/mocks.\n"
                    "  - All async tests must use `pytest.mark.asyncio` or `asyncio_mode = 'auto'`.\n"
                    "  - Use `pytest.mark.parametrize` for the C-089 boundary sub-cases.\n"
                    "  - Keep each test function focused on one behaviour; no multi-assert monoliths.\n"
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
        ]
    },
        "WC027-02": {
        "subtasks": [
            SubTaskDef(
                id='WC027-02a',
                description='Write pytest tests for test_markup.py per WC scope specification',
                type="udcp",
                depends_on=['WC027-01ba'],
                compile_gate='ruff',
                service_dir='',
                wc_task_id='WC027-02',
                stack='python',
                force_greenfield=True,  # existing EA mock must be replaced entirely
                output_files=[
                    'tests/billing-engine/test_markup.py',
                ],
                inject_source_files=[
                    'src/billing-engine/markup/models.py',
                    'src/billing-engine/markup/bundle_engine.py',
                    'src/billing-engine/markup/router.py',
                    'src/billing-engine/main.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-027-wbe-s3-markup-engine.md': 'WC027-02',
                },
                constitutional_check='TEST PASS — write pytest tests exactly as described in the WC scope:\n`tests/billing-engine/test_markup.py` — test: cost_floor reads `bundle_profiles.cost_floor_paise` (not recomputed), derive_price formula uses margin-on-revenue `floor / (1 - margin/100)`, `POST /pricing/validate` 200 path (APPROVED, `pricing_floor_log` row written), `POST /pricing/validate` 422 path (REJECTED — body includes `minimum_compliant_price_paise`, `pricing_floor_log` row written), `GET /pricing/thread-catalog` response shape, ≥90% line coverage; **property-based tests using `hypothesis`**: `@given` strategy on `derive_price(cost_floor_paise, margin_pct)` covering zero margin, near-10\n\nC-097: property-based testing required — use hypothesis @given for all financial math.\nC-059: verify audit log row written for APPROVED and REJECTED pricing outcomes.\nC-073: # Implements: header required at top of test file.\nUse pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\nNever use % string formatting — use f-strings only.',
                model_hint='reasoning',
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC027-02b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="udcp",
                depends_on=["WC027-02a"],
                compile_gate="ruff",
                service_dir="",
                wc_task_id="WC027-02",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_markup.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_markup.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-02",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC027-02c",
                description="Run pytest on tests/billing-engine to verify all tests pass",
                type="udcp",
                depends_on=["WC027-02b"],
                compile_gate="pytest",
                service_dir="tests/billing-engine",
                wc_task_id="WC027-02",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_markup.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_markup.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-02",
                },
                constitutional_check=(
                    "PYTEST RUN — execute the test file and confirm all tests pass.\n"
                    "If tests fail due to missing fixtures or imports, fix the test file.\n"
                    "Do NOT modify the implementation under test."
                ),
                model_hint="auto",
                max_tokens=2000,
            ),
        ]
    },
        "WC028-01": {
        "subtasks": [
            SubTaskDef(
                id='WC028-01a',
                description='Implement meter usage recording, depletion projection, and daily threshold scanning with multi-scope alert policy enforcement for billing runway visibility.',
                type="llm",
                depends_on=[],
                compile_gate='py_compile',
                service_dir='src/billing-engine',
                wc_task_id='WC028-01',
                stack='python',
                output_files=[
                    'src/billing-engine/meter/service.py',
                    'src/billing-engine/meter/alert_policy.py',
                ],
                inject_source_files=[
                    'src/billing-engine/skeleton/__init__.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-028-wbe-s4-meter-alert-engine.md': 'WC028-01',
                },
                constitutional_check='Implement IMeterService.record_usage(), IMeterService.project_depletion(), IMeterService.run_daily_scan() from wbe_interfaces.py skeleton. Implement MeterService.check_thresholds(customer_id) → list[AlertFired] as concrete helper (NOT abstract; called directly by tests on concrete class). Define ThresholdRule and ThresholdPolicy dataclasses in alert_policy.py with Scope 3 runway thresholds: RUNWAY_P2 (≤30d), RUNWAY_P1 (≤14d), RUNWAY_P0 (≤7d), RUNWAY_CRITICAL (≤3d), RUNWAY_EMERGENCY (≤1d). Define singletons CUSTOMER_BUCKET_POLICY, AGENCY_POLICY, PROCUREMENT_POLICY. C-043 (AlertFired structure), C-088 (billing_profiles validation), C-089 (margin floor), C-091 (Thread Catalog), §2.3a (scope 1+2+3 ladder), ADR-034 (Redis cache for wallet balance). Threshold logic: compute pct_consumed from platform_cost_ledger.marked_up_cost_inr_paise vs (consumed + wallet_buckets.balance_paise); deduplicate alerts via meter_alert_log; respect quiet_hours_ist and bypass_quiet_hours flag; resolve provider_account_id via thread_catalog.provider_accounts lookup; use 7d rolling average for depletion projection.',
                model_hint='reasoning',
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC028-01b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC028-01a"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC028-01",
                stack="python",
                output_files=[
                    "src/billing-engine/meter/service.py",
                    "src/billing-engine/meter/alert_policy.py",
                ],
                inject_source_files=[
                    "src/billing-engine/meter/service.py",
                    "src/billing-engine/meter/alert_policy.py",
                ],
                spec_sections={
                    "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-01",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC028-01c",
                description="Write pytest suite covering happy path, error cases and constitutional invariants for service",
                type="llm",
                depends_on=["WC028-01b"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC028-01",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_service.py",
                ],
                inject_source_files=[
                    "src/billing-engine/meter/service.py",
                    "src/billing-engine/meter/alert_policy.py",
                ],
                spec_sections={
                    "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-01",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\n"
                    "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
                    "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\n"
                    "Use f-strings only — never % string formatting.\n"
                    "DB fixture: use SQLite in-memory WITH StaticPool so all sessions share one connection:\n"
                    "  from sqlalchemy.pool import StaticPool\n"
                    "  engine = create_async_engine('sqlite+aiosqlite:///:memory:', "
                    "connect_args={'check_same_thread': False}, poolclass=StaticPool)\n"
                    "Patch targets: always use fully qualified module path — "
                    "patch('meter.service._now_ist') NOT patch('service._now_ist').\n"
                    "Import style: always 'from meter.service import MeterService' not 'import service'."
                ),
                model_hint="auto",
                max_tokens=12000,
            ),
        ]
    },
        "WC028-02": {
        "subtasks": [
            SubTaskDef(
                id='WC028-02a',
                description='Implement WhatsApp notification stub for customer alerts and meter status endpoint with daily scan scheduling.',
                type="llm",
                depends_on=['WC028-01a'],
                compile_gate='py_compile',
                service_dir='src/billing-engine',
                wc_task_id='WC028-02',
                stack='python',
                output_files=[
                    'src/billing-engine/meter/whatsapp_notifier.py',
                    'src/billing-engine/meter/router.py',
                    'src/billing-engine/main.py',
                ],
                inject_source_files=[
                    'src/billing-engine/skeleton/__init__.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-028-wbe-s4-meter-alert-engine.md': 'WC028-02',
                },
                constitutional_check='Implement IWalletService, IMarkupEngine, IMeterService from wbe_interfaces.py skeleton (C-088, C-089, C-090, C-091, C-038, C-048, C-051); WhatsAppNotifier.send() raises NotImplementedError with TODO→ADR-023; IMeterService.run_daily_scan() and IMeterService.project_depletion() per §surface.endpoints; FastAPI router: GET /meter/{customer_id}/status returns UsageStatus, POST /meter/daily-scan triggers run_daily_scan(); mount in main.py; ADR-034 (Redis SLA ≤50ms p99 for get_bucket_balance)',
                model_hint='auto',
                max_tokens=4000,
            ),
            SubTaskDef(
                id="WC028-02b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC028-02a"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC028-02",
                stack="python",
                output_files=[
                    "src/billing-engine/meter/whatsapp_notifier.py",
                    "src/billing-engine/meter/router.py",
                    "src/billing-engine/main.py",
                ],
                inject_source_files=[
                    "src/billing-engine/meter/whatsapp_notifier.py",
                    "src/billing-engine/meter/router.py",
                    "src/billing-engine/main.py",
                ],
                spec_sections={
                    "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-02",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC028-02c",
                description="Write pytest suite covering happy path, error cases and constitutional invariants for whatsapp_notifier",
                type="llm",
                depends_on=["WC028-02b"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC028-02",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_whatsapp_notifier.py",
                ],
                inject_source_files=[
                    "src/billing-engine/meter/whatsapp_notifier.py",
                    "src/billing-engine/meter/router.py",
                    "src/billing-engine/main.py",
                ],
                spec_sections={
                    "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-02",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\n"
                    "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
                    "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\n"
                    "Use f-strings only — never % string formatting."
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
        ]
    },
        "WC028-03": {
        "subtasks": [
            SubTaskDef(
                id='WC028-03a',
                description='Write pytest tests for test_meter.py per WC scope specification',
                type="llm",
                depends_on=['WC028-02a'],
                compile_gate='ruff',
                service_dir='',
                wc_task_id='WC028-03',
                stack='python',
                output_files=[
                    'tests/billing-engine/test_meter.py',
                ],
                inject_source_files=[
                    'src/billing-engine/main.py',
                    'src/billing-engine/skeleton/__init__.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-028-wbe-s4-meter-alert-engine.md': 'WC028-03',
                },
                constitutional_check='TEST PASS — write pytest tests exactly as described in the WC scope:\n`tests/billing-engine/test_meter.py` — test: threshold fires at correct % (30% remaining triggers WARN_30), no double-fire within 24h deduplication window, quiet hours suppress WhatsApp (23:00–06:00 IST, notifications queued), procurement runway P0 escalation at ≤7 days, agency NULL quota produces no alert, `POST /meter/daily-scan` calls check_thresholds for all customers, `CCT-BILLINGLOOP-01` scenario: AD wallet hits zero → `alerts_sent == 1` type `AD_WALLET_BELOW_MINIMUM` — ≥90% line coverage\n\nC-097: property-based testing required — use hypothesis @given for all financial math.\nC-059: verify audit log row written for APPROVED and REJECTED pricing outcomes.\nC-073: # Implements: header required at top of test file.\nUse pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\nNever use % string formatting — use f-strings only.',
                model_hint='auto',
                max_tokens=12000,
            ),
            SubTaskDef(
                id="WC028-03b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC028-03a"],
                compile_gate="ruff",
                service_dir="",
                wc_task_id="WC028-03",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_meter.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_meter.py",
                ],
                spec_sections={
                    "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-03",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC028-03c",
                description="Run pytest on tests/billing-engine to verify all tests pass",
                type="llm",
                depends_on=["WC028-03b"],
                compile_gate="pytest",
                service_dir="tests/billing-engine",
                wc_task_id="WC028-03",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_meter.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_meter.py",
                ],
                spec_sections={
                    "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-03",
                },
                constitutional_check=(
                    "PYTEST RUN — execute the test file and confirm all tests pass.\n"
                    "If tests fail due to missing fixtures or imports, fix the test file.\n"
                    "Do NOT modify the implementation under test."
                ),
                model_hint="auto",
                max_tokens=2000,
            ),
        ]
    },
        "WC029-01a": {
        "subtasks": [
            SubTaskDef(
                id='WC029-01aa',
                description='Implement SQLAlchemy ORM models for provider accounts and platform cost ledger, Pydantic response models for runway status and cost records, and a ProcurementService to record costs, project runway via 7-day rolling average, and trigger founder action alerts when balance thresholds are breached.',
                type="llm",
                depends_on=[],
                compile_gate='py_compile',
                service_dir='src/billing-engine',
                wc_task_id='WC029-01a',
                stack='python',
                output_files=[
                    'src/billing-engine/procurement/models.py',
                    'src/billing-engine/procurement/service.py',
                ],
                inject_source_files=[
                    'src/billing-engine/skeleton/__init__.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-029-wbe-s5-platform-procurement.md': 'WC029-01a',
                },
                constitutional_check='Models: ProviderAccount (maps institutional.provider_accounts), PlatformCostLedgerEntry (maps institutional.platform_cost_ledger with provider_account_id UUID FK); Response models: ProviderRunwayStatus, CostRecordRequest. Service: ProcurementService (concrete, no ABC) with record_cost() [append-only per C-007], project_runway() [7d rolling avg formula], check_and_alert() [reads PROCUREMENT_POLICY, calls FounderActionGenerator.maybe_create]. Constitutional: C-007 (non-idempotency), C-088 (billing profile), C-043 (threshold breach), C-090 (pricing). ADR: ADR-034 (cache strategy).',
                model_hint='reasoning',
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC029-01ab",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC029-01aa"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC029-01a",
                stack="python",
                output_files=[
                    "src/billing-engine/procurement/models.py",
                    "src/billing-engine/procurement/service.py",
                ],
                inject_source_files=[
                    "src/billing-engine/procurement/models.py",
                    "src/billing-engine/procurement/service.py",
                ],
                spec_sections={
                    "work-contracts/WC-029-wbe-s5-platform-procurement.md": "WC029-01a",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC029-01ac",
                description="Write pytest suite covering happy path, error cases and constitutional invariants for models",
                type="llm",
                depends_on=["WC029-01ab"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC029-01a",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_models.py",
                ],
                inject_source_files=[
                    "src/billing-engine/procurement/models.py",
                    "src/billing-engine/procurement/service.py",
                ],
                spec_sections={
                    "work-contracts/WC-029-wbe-s5-platform-procurement.md": "WC029-01a",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\n"
                    "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
                    "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\n"
                    "Use f-strings only — never % string formatting."
                ),
                model_hint="auto",
                max_tokens=12000,
            ),
        ]
    },
        "WC029-01b": {
        "subtasks": [
            SubTaskDef(
                id='WC029-01ba',
                description='Reads FOUNDER-ACTIONS.md, extracts max FA number via regex, checks for duplicate provider+priority entries, and appends idempotent new FA table rows under P0/P1/P2 sections; exposes FastAPI endpoints for runway status retrieval, cost recording, and margin reporting at /platform/procurement prefix.',
                type="llm",
                depends_on=['WC029-01aa'],
                compile_gate='py_compile',
                service_dir='src/billing-engine',
                wc_task_id='WC029-01b',
                stack='python',
                output_files=[
                    'src/billing-engine/procurement/founder_action.py',
                    'src/billing-engine/procurement/router.py',
                    'src/billing-engine/main.py',
                ],
                inject_source_files=[
                    'src/billing-engine/skeleton/__init__.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-029-wbe-s5-platform-procurement.md': 'WC029-01b',
                },
                constitutional_check='ABC class: IWalletService (get_bucket_balance, reserve, release, activate_subscription, renew), IMarkupEngine (cost_floor, derive_price, validate_price), IMeterService (record_usage, project_depletion, run_daily_scan). Skeleton method stubs: FounderActionGenerator.maybe_create(provider, days_remaining, priority) → Optional[str]. Router endpoints: GET /status → list[ProviderRunwayStatus], POST /record-cost body CostRecordRequest, GET /margin/report (ops-auth deferred). C-077 procurement runway, C-088 billing profile gate, C-089 margin floor enforcement, C-090 renewal price check, C-091 thread catalog, C-038 request shape, C-043 threshold breach, C-048 response shape, C-051 error handling. ADR-034 Redis cache. Mount in main.py via FastAPI app.include_router().',
                model_hint='auto',
                max_tokens=4000,
            ),
            SubTaskDef(
                id="WC029-01bb",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC029-01ba"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC029-01b",
                stack="python",
                output_files=[
                    "src/billing-engine/procurement/founder_action.py",
                    "src/billing-engine/procurement/router.py",
                    "src/billing-engine/main.py",
                ],
                inject_source_files=[
                    "src/billing-engine/procurement/founder_action.py",
                    "src/billing-engine/procurement/router.py",
                    "src/billing-engine/main.py",
                ],
                spec_sections={
                    "work-contracts/WC-029-wbe-s5-platform-procurement.md": "WC029-01b",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC029-01bc",
                description="Write pytest suite covering happy path, error cases and constitutional invariants for founder_action",
                type="llm",
                depends_on=["WC029-01bb"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC029-01b",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_founder_action.py",
                ],
                inject_source_files=[
                    "src/billing-engine/procurement/founder_action.py",
                    "src/billing-engine/procurement/router.py",
                    "src/billing-engine/main.py",
                ],
                spec_sections={
                    "work-contracts/WC-029-wbe-s5-platform-procurement.md": "WC029-01b",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\n"
                    "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
                    "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\n"
                    "Use f-strings only — never % string formatting."
                ),
                model_hint="auto",
                max_tokens=12000,
            ),
        ]
    },
        "WC029-02": {
        "subtasks": [
            SubTaskDef(
                id='WC029-02a',
                description='Write pytest tests for test_procurement.py per WC scope specification',
                type="llm",
                depends_on=['WC029-01ba'],
                compile_gate='ruff',
                service_dir='',
                wc_task_id='WC029-02',
                stack='python',
                output_files=[
                    'tests/billing-engine/test_procurement.py',
                ],
                inject_source_files=[
                    'src/billing-engine/main.py',
                    'src/billing-engine/skeleton/__init__.py',
                    'src/billing-engine/skeleton/wbe_interfaces.py',
                ],
                spec_sections={
                    'work-contracts/WC-029-wbe-s5-platform-procurement.md': 'WC029-02',
                },
                constitutional_check='TEST PASS — write pytest tests exactly as described in the WC scope:\n`tests/billing-engine/test_procurement.py` — test: `record_cost` writes one row to `platform_cost_ledger` (verify via DB query), `record_cost` called twice for same event writes TWO rows (append-only — no dedup at DB level), `project_runway` formula (balance / 7d_avg_burn = days), FA auto-created at ≤30d threshold (P2) via `maybe_create`, FA upgraded to P1 at ≤14d and P0 at ≤7d, second `maybe_create` same provider+priority → no duplicate entry in FA file (idempotency), `GET /platform/procurement/status` → 200 list with `days_remaining`; use `tmp_path` pytest fixture for FA file — do NOT modify\n\nC-097: property-based testing required — use hypothesis @given for all financial math.\nC-059: verify audit log row written for APPROVED and REJECTED pricing outcomes.\nC-073: # Implements: header required at top of test file.\nUse pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\nNever use % string formatting — use f-strings only.',
                model_hint='auto',
                max_tokens=12000,
            ),
            SubTaskDef(
                id="WC029-02b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC029-02a"],
                compile_gate="ruff",
                service_dir="",
                wc_task_id="WC029-02",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_procurement.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_procurement.py",
                ],
                spec_sections={
                    "work-contracts/WC-029-wbe-s5-platform-procurement.md": "WC029-02",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC029-02c",
                description="Run pytest on tests/billing-engine to verify all tests pass",
                type="llm",
                depends_on=["WC029-02b"],
                compile_gate="pytest",
                service_dir="tests/billing-engine",
                wc_task_id="WC029-02",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_procurement.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_procurement.py",
                ],
                spec_sections={
                    "work-contracts/WC-029-wbe-s5-platform-procurement.md": "WC029-02",
                },
                constitutional_check=(
                    "PYTEST RUN — execute the test file and confirm all tests pass.\n"
                    "If tests fail due to missing fixtures or imports, fix the test file.\n"
                    "Do NOT modify the implementation under test."
                ),
                model_hint="auto",
                max_tokens=2000,
            ),
        ]
    },
        "WC030-01a": {
        "subtasks": [
            SubTaskDef(
                id='WC030-01aa',
                description='Reconcile billing data by verifying consumed bucket reservations against platform cost ledger, detecting balance discrepancies, and generating margin reports for financial audit and operator control.',
                type="llm",
                depends_on=[],
                compile_gate='py_compile',
                service_dir='src/billing-engine',
                wc_task_id='WC030-01a',
                stack='python',
                output_files=[
                    'src/billing-engine/reconciliation/service.py',
                ],
                inject_source_files=[
        
                ],
                spec_sections={
                    'work-contracts/WC-030-wbe-s6-reconciliation.md': 'WC030-01a',
                },
                constitutional_check='ReconciliationService.run_daily_audit(date) — verify consumed bucket_reservations have matching platform_cost_ledger entries, emit C-023 evidence; ReconciliationService.run_self_audit() — compute expected wallet bucket balance and halt billing via Redis wbe:billing_halted if discrepancy exceeds ±1 paise, call FounderActionGenerator.maybe_create; ReconciliationService.generate_margin_report(date) — calculate margin percentage from reservation revenue vs platform cost ledger; ReconciliationService.clear_halt() — remove Redis wbe:billing_halted flag (ops-only, no audit tracking)',
                model_hint='reasoning',
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC030-01ab",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC030-01aa"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC030-01a",
                stack="python",
                output_files=[
                    "src/billing-engine/reconciliation/service.py",
                ],
                inject_source_files=[
                    "src/billing-engine/reconciliation/service.py",
                ],
                spec_sections={
                    "work-contracts/WC-030-wbe-s6-reconciliation.md": "WC030-01a",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC030-01ac",
                description="Write pytest suite covering happy path, error cases and constitutional invariants for service",
                type="llm",
                depends_on=["WC030-01ab"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC030-01a",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_service.py",
                ],
                inject_source_files=[
                    "src/billing-engine/reconciliation/service.py",
                ],
                spec_sections={
                    "work-contracts/WC-030-wbe-s6-reconciliation.md": "WC030-01a",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\n"
                    "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
                    "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\n"
                    "Use f-strings only — never % string formatting."
                ),
                model_hint="auto",
                max_tokens=12000,
            ),
        ]
    },
        "WC030-01b": {
        "subtasks": [
            SubTaskDef(
                id='WC030-01ba',
                description='Schedule daily reconciliation audits at 02:00 and 06:00 Asia/Kolkata using AsyncIOScheduler with Redis-based idempotency, expose audit status and manual trigger endpoints via FastAPI, and enforce billing halt checks in wallet reservations during audit operations.',
                type="llm",
                depends_on=['WC030-01aa'],
                compile_gate='py_compile',
                service_dir='src/billing-engine',
                wc_task_id='WC030-01b',
                stack='python',
                output_files=[
                    'src/billing-engine/reconciliation/scheduler.py',
                    'src/billing-engine/reconciliation/router.py',
                    'src/billing-engine/main.py',
                    'src/billing-engine/wallet/service.py',
                ],
                inject_source_files=[
        
                ],
                spec_sections={
                    'work-contracts/WC-030-wbe-s6-reconciliation.md': 'WC030-01b',
                },
                constitutional_check='Implement create_scheduler() -> AsyncIOScheduler in src/billing-engine/reconciliation/scheduler.py; implement ReconciliationRouter with GET /status, POST /run-now (ops-auth), GET /platform/margin/report (ops-auth) in src/billing-engine/reconciliation/router.py; integrate scheduler.start()/scheduler.shutdown() additively into existing lifespan context manager in src/billing-engine/main.py; modify WalletService.reserve() to accept injected redis.Redis client and check wbe:billing_halted key before DB writes in src/billing-engine/wallet/service.py. Redis keys: wbe:audit_in_progress:{YYYY-MM-DD} (TTL=4h), wbe:billing_halted. Timezone: zoneinfo.ZoneInfo(\'Asia/Kolkata\'). HTTP client: httpx.AsyncClient POST to {settings.WBE_INTERNAL_BASE_URL}/meter/daily-scan. Exception: HTTPException(503, detail={"code": "BILLING_INTEGRITY_HALT", ...}). Dependencies: C-001 (audit scheduling), C-002 (idempotency), C-003 (ops-auth), C-004 (billing halt enforcement).',
                model_hint='reasoning',
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC030-01bb",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC030-01ba"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC030-01b",
                stack="python",
                output_files=[
                    "src/billing-engine/reconciliation/scheduler.py",
                    "src/billing-engine/reconciliation/router.py",
                    "src/billing-engine/main.py",
                    "src/billing-engine/wallet/service.py",
                ],
                inject_source_files=[
                    "src/billing-engine/reconciliation/scheduler.py",
                    "src/billing-engine/reconciliation/router.py",
                    "src/billing-engine/main.py",
                    "src/billing-engine/wallet/service.py",
                ],
                spec_sections={
                    "work-contracts/WC-030-wbe-s6-reconciliation.md": "WC030-01b",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC030-01bc",
                description="Write pytest suite covering happy path, error cases and constitutional invariants for scheduler",
                type="llm",
                depends_on=["WC030-01bb"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC030-01b",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_scheduler.py",
                ],
                inject_source_files=[
                    "src/billing-engine/reconciliation/scheduler.py",
                    "src/billing-engine/reconciliation/router.py",
                    "src/billing-engine/main.py",
                    "src/billing-engine/wallet/service.py",
                ],
                spec_sections={
                    "work-contracts/WC-030-wbe-s6-reconciliation.md": "WC030-01b",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\n"
                    "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
                    "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\n"
                    "Use f-strings only — never % string formatting."
                ),
                model_hint="auto",
                max_tokens=12000,
            ),
        ]
    },
        "WC030-03": {
        "subtasks": [
            SubTaskDef(
                id='WC030-03a',
                description='Write pytest tests for test_reconciliation.py per WC scope specification',
                type="llm",
                depends_on=['WC030-01ba'],
                compile_gate='ruff',
                service_dir='',
                wc_task_id='WC030-03',
                stack='python',
                output_files=[
                    'tests/billing-engine/test_reconciliation.py',
                ],
                inject_source_files=[
                    'src/billing-engine/main.py',
                ],
                spec_sections={
                    'work-contracts/WC-030-wbe-s6-reconciliation.md': 'WC030-03',
                },
                constitutional_check='TEST PASS — write pytest tests exactly as described in the WC scope:\n`tests/billing-engine/test_reconciliation.py` — test: clean `run_self_audit()` → `billing_halted=False`; manually corrupt `balance_paise` in DB (add 2 paise via direct SQL, bypassing ORM) → `run_self_audit()` → `billing_halted=True` + Redis `wbe:billing_halted` set + FA created; `POST /wallet/.../reserve` while halted → HTTP 503 `BILLING_INTEGRITY_HALT`; `clear_halt()` + `run_self_audit()` (fix balance first) → billing resumes; `run_daily_audit` with matched cost-to-reservation → zero unlinked; margin report arithmetic (`margin_pct = (revenue-cost)/revenue`); scheduler idempotency (Redis `wbe:\n\nC-097: property-based testing required — use hypothesis @given for all financial math.\nC-059: verify audit log row written for APPROVED and REJECTED pricing outcomes.\nC-073: # Implements: header required at top of test file.\nUse pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\nNever use % string formatting — use f-strings only.',
                model_hint='auto',
                max_tokens=12000,
            ),
            SubTaskDef(
                id="WC030-03b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC030-03a"],
                compile_gate="ruff",
                service_dir="",
                wc_task_id="WC030-03",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_reconciliation.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_reconciliation.py",
                ],
                spec_sections={
                    "work-contracts/WC-030-wbe-s6-reconciliation.md": "WC030-03",
                },
                constitutional_check=(
                    "POLISH PASS — type annotation enforcement only.\n"
                    "Add type annotations to ALL function parameters (ANN001).\n"
                    "Add return type annotations to ALL functions (ANN201, ANN202).\n"
                    "DO NOT change function names, business logic, or structure.\n"
                    "DO NOT add new imports beyond those needed for type annotations."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
            SubTaskDef(
                id="WC030-03c",
                description="Run pytest on tests/billing-engine to verify all tests pass",
                type="llm",
                depends_on=["WC030-03b"],
                compile_gate="pytest",
                service_dir="tests/billing-engine",
                wc_task_id="WC030-03",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_reconciliation.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/test_reconciliation.py",
                ],
                spec_sections={
                    "work-contracts/WC-030-wbe-s6-reconciliation.md": "WC030-03",
                },
                constitutional_check=(
                    "PYTEST RUN — execute the test file and confirm all tests pass.\n"
                    "If tests fail due to missing fixtures or imports, fix the test file.\n"
                    "Do NOT modify the implementation under test."
                ),
                model_hint="auto",
                max_tokens=2000,
            ),
        ]
    },
    "WC034-08": {
        "subtasks": [
            SubTaskDef(
                id="WC034-08a",
                description="Implement Business Platform conversation ingress endpoints and service boundary for timeline/send/retry/read-position/cancel/SSE.",
                type="udcp",
                depends_on=[],
                compile_gate="dotnet_build",
                service_dir="src/business-platform",
                wc_task_id="WC034-08",
                stack="dotnet",
                output_files=[
                    "src/business-platform/Program.cs",
                    "src/business-platform/Controllers/ConversationController.cs",
                    "src/business-platform/Services/ConversationService.cs",
                    "src/business-platform/Infrastructure/ConversationStoreDbContext.cs",
                ],
                inject_source_files=[
                    "architecture/reference/components/conversation-core.md",
                    "architecture/reference/api-specs/business-platform.openapi.yaml",
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md",
                    "src/business-platform/Program.cs",
                    "src/business-platform/Controllers/IdentityController.cs",
                    "src/business-platform/Services/IdentityService.cs",
                    "src/business-platform/Infrastructure/IdentityDbContext.cs",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-08",
                    "architecture/reference/components/conversation-core.md": "F3",
                    "architecture/reference/api-specs/business-platform.openapi.yaml": "conversation operations",
                },
                constitutional_check=(
                    "Implement BP OpenAPI 1.2.0 conversation operations only. "
                    "Use JWT tenant authority (no request-body tenant id), UUID request-hash idempotency, "
                    "privacy-safe RFC 9457 errors, and Evidence First sequencing before success responses."
                ),
                model_hint="reasoning",
                max_tokens=12000,
            ),
            SubTaskDef(
                id="WC034-08b",
                description="Add the additive Conversation Core persistence migration with tenant RLS, durable ordering, idempotency outcomes, unread positions, and stream cursors.",
                type="udcp",
                depends_on=["WC034-08a"],
                compile_gate="sqlfluff",
                service_dir="infrastructure/postgres/init",
                wc_task_id="WC034-08",
                stack="sql",
                output_files=[
                    "infrastructure/postgres/init/21-conversation-core.sql",
                ],
                inject_source_files=[
                    "architecture/reference/components/conversation-core.md",
                    "infrastructure/postgres/init/19-ae01-employment-relationship.sql",
                    "infrastructure/postgres/init/20-identity-boundary.sql",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-08",
                    "architecture/reference/components/conversation-core.md": "durable timeline and idempotency",
                },
                constitutional_check=(
                    "Use additive DDL only. Enforce tenant RLS and durable canonical sequence, "
                    "idempotency request hashes/outcomes, unread positions, and resumable event cursors."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC034-08c",
                description="Add Business Platform conversation tests for idempotency, tenant isolation, privacy-safe errors, and SSE replay semantics.",
                type="udcp",
                depends_on=["WC034-08a", "WC034-08b"],
                compile_gate="dotnet_test",
                service_dir="tests/business-platform.Tests",
                wc_task_id="WC034-08",
                stack="dotnet",
                output_files=[
                    "tests/business-platform.Tests/ConversationControllerTests.cs",
                    "tests/business-platform.Tests/ConversationServiceTests.cs",
                ],
                inject_source_files=[
                    "src/business-platform/Controllers/ConversationController.cs",
                    "src/business-platform/Services/ConversationService.cs",
                    "architecture/reference/components/conversation-core.md",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-08",
                    "architecture/reference/components/conversation-core.md": "acceptance mapping",
                },
                constitutional_check=(
                    "Tests must validate idempotency replay, tenant isolation, privacy-safe errors, "
                    "cursor continuity, and cancellation behavior for BP conversation operations."
                ),
                model_hint="auto",
                max_tokens=10000,
            ),
        ]
    },
    "WC034-09": {
        "subtasks": [
            SubTaskDef(
                id="WC034-09a",
                description="Implement Professional Runtime BP-authenticated conversation execution, cancellation, and resumable typed stream endpoints.",
                type="udcp",
                depends_on=["WC034-08a"],
                compile_gate="ruff",
                service_dir="src/professional-runtime",
                wc_task_id="WC034-09",
                stack="python",
                output_files=[
                    "src/professional-runtime/main.py",
                    "src/professional-runtime/routers/conversation.py",
                    "src/professional-runtime/workflows/conversation_workflow.py",
                    "src/professional-runtime/activities/conversation_stream.py",
                ],
                inject_source_files=[
                    "architecture/reference/components/conversation-core.md",
                    "architecture/reference/api-specs/professional-runtime.openapi.yaml",
                    "src/professional-runtime/main.py",
                    "src/professional-runtime/workflows/paas_workflow.py",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-09",
                    "architecture/reference/components/conversation-core.md": "F3",
                    "architecture/reference/api-specs/professional-runtime.openapi.yaml": "conversation execution and stream",
                },
                constitutional_check=(
                    "Expose PR conversation execution/cancel/stream only for BP-authenticated internal ingress. "
                    "No direct browser ingress and no provider-facing ingress. Preserve Stop behavior and Temporal consistency."
                ),
                model_hint="reasoning",
                max_tokens=12000,
            ),
            SubTaskDef(
                id="WC034-09b",
                description="Add Professional Runtime conversation tests for typed events, cancellation, Stop independence, and stream resume.",
                type="udcp",
                depends_on=["WC034-09a"],
                compile_gate="pytest",
                service_dir="tests/professional-runtime",
                wc_task_id="WC034-09",
                stack="python",
                output_files=[
                    "tests/professional-runtime/test_conversation_router.py",
                    "tests/professional-runtime/test_conversation_workflow.py",
                ],
                inject_source_files=[
                    "src/professional-runtime/routers/conversation.py",
                    "src/professional-runtime/workflows/conversation_workflow.py",
                    "architecture/reference/components/conversation-core.md",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-09",
                    "architecture/reference/components/conversation-core.md": "acceptance mapping",
                },
                constitutional_check=(
                    "Docker-only pytest coverage for cursor replay, reconnect, cancellation, "
                    "Stop independence, and typed internal stream events."
                ),
                model_hint="auto",
                max_tokens=10000,
            ),
        ]
    },
    "WC034-10": {
        "subtasks": [
            SubTaskDef(
                id="WC034-10a",
                description="Generate F3 ConversationApi client and implement server-only web BFF conversation routes.",
                type="udcp",
                depends_on=["WC034-08a", "WC034-09a"],
                compile_gate="openapi_ts_generate",
                service_dir="web",
                wc_task_id="WC034-10",
                stack="typescript",
                output_files=[
                    "web/lib/api/conversation.ts",
                    "web/app/api/conversation/timeline/route.ts",
                    "web/app/api/conversation/send/route.ts",
                    "web/app/api/conversation/retry/route.ts",
                    "web/app/api/conversation/read-position/route.ts",
                    "web/app/api/conversation/stream/route.ts",
                    "web/app/api/conversation/executions/route.ts",
                ],
                inject_source_files=[
                    "architecture/reference/api-specs/business-platform.openapi.yaml",
                    "architecture/reference/components/conversation-core.md",
                    "web/lib/api/identity.ts",
                    "web/app/api/identity/registration/route.ts",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-10",
                    "architecture/reference/components/conversation-core.md": "web boundary",
                    "architecture/reference/api-specs/business-platform.openapi.yaml": "conversation operations",
                },
                constitutional_check=(
                    "Follow existing Identity BFF pattern: server-only bridge to BP via a deterministically generated client. "
                    "Do not author or patch files under web/lib/api/generated; the compile gate generates them from OpenAPI 1.2.0. "
                    "Do not expose PR/provider endpoints to browser. Keep routes tenant-safe and privacy-safe."
                ),
                model_hint="reasoning",
                max_tokens=12000,
            ),
            SubTaskDef(
                id="WC034-10b",
                description="Implement conversation workspace UI behavior for timeline/cards/retry/reconciliation and exact 360px compatibility.",
                type="udcp",
                depends_on=["WC034-10a"],
                compile_gate="tsc",
                service_dir="web",
                wc_task_id="WC034-10",
                stack="typescript",
                output_files=[
                    "web/components/conversation-workspace.tsx",
                    "web/app/(authenticated)/relationships/[relationshipId]/conversation/page.tsx",
                ],
                inject_source_files=[
                    "architecture/reference/components/conversation-core.md",
                    "architecture/reference/ux/hybrid-ui-acceptance-contract.md",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-10",
                    "architecture/reference/components/conversation-core.md": "cards and events",
                },
                constitutional_check=(
                    "UI must honor typed cards/events, retry/reconciliation semantics, offline state, and exact 360px layout constraints."
                ),
                model_hint="reasoning",
                max_tokens=10000,
            ),
        ]
    },
    "WC034-11": {
        "subtasks": [
            SubTaskDef(
                id="WC034-11a",
                description="Add BP conversation contract and invariants coverage.",
                type="udcp",
                depends_on=["WC034-08c"],
                compile_gate="dotnet_test",
                service_dir="tests/business-platform.Tests",
                wc_task_id="WC034-11",
                stack="dotnet",
                output_files=[
                    "tests/business-platform.Tests/ConversationContractsTests.cs",
                ],
                inject_source_files=[
                    "src/business-platform/Controllers/ConversationController.cs",
                    "src/business-platform/Services/ConversationService.cs",
                    "architecture/reference/components/conversation-core.md",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-11",
                },
                constitutional_check=(
                    "Validate BP idempotency, tenant isolation, privacy-safe errors, and versioned schema conformance."
                ),
                model_hint="auto",
                max_tokens=9000,
            ),
            SubTaskDef(
                id="WC034-11b",
                description="Add PR conversation workflow/stream/cancellation invariants coverage.",
                type="udcp",
                depends_on=["WC034-09b"],
                compile_gate="pytest",
                service_dir="tests/professional-runtime",
                wc_task_id="WC034-11",
                stack="python",
                output_files=[
                    "tests/professional-runtime/test_conversation_idempotency.py",
                ],
                inject_source_files=[
                    "src/professional-runtime/routers/conversation.py",
                    "src/professional-runtime/workflows/conversation_workflow.py",
                    "architecture/reference/components/conversation-core.md",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-11",
                },
                constitutional_check=(
                    "Docker-only pytest coverage for cursor replay, reconnect, cancellation, Stop independence, and Temporal state integrity."
                ),
                model_hint="auto",
                max_tokens=9000,
            ),
            SubTaskDef(
                id="WC034-11c",
                description="Add web conversation BFF and UI contract coverage including generated-client conformance.",
                type="udcp",
                depends_on=["WC034-10b"],
                compile_gate="ts_test",
                service_dir="web",
                wc_task_id="WC034-11",
                stack="typescript",
                output_files=[
                    "web/tests/conversation.timeline.test.tsx",
                    "web/lib/api/conversation.test.ts",
                ],
                inject_source_files=[
                    "web/lib/api/conversation.ts",
                    "web/components/conversation-workspace.tsx",
                    "architecture/reference/components/conversation-core.md",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-11",
                    "architecture/reference/ux/hybrid-ui-acceptance-contract.md": "UX-CONV-01 through UX-CONV-07",
                },
                constitutional_check=(
                    "Docker-only web tests for generated-client conformance, timeline/retry behavior, accessibility assertions, and no horizontal overflow at 360px."
                ),
                model_hint="auto",
                max_tokens=9000,
            ),
        ]
    },
    "WC034-12": {
        "subtasks": [
            SubTaskDef(
                id="WC034-12a",
                description="Create deterministic F3 validation runner that executes Docker-only regression, constitutional suites, and browser acceptance gates.",
                type="udcp",
                depends_on=["WC034-11a", "WC034-11b", "WC034-11c"],
                compile_gate="wc034_f3_validate",
                service_dir="scripts",
                wc_task_id="WC034-12",
                stack="python",
                output_files=[
                    "scripts/wc034_f3_validation.py",
                ],
                inject_source_files=[
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md",
                    "architecture/reference/components/conversation-core.md",
                    "docker-compose.yml",
                ],
                spec_sections={
                    "work-contracts/WC-034-goal005-webportal-founder-admin.md": "WC034-12",
                    "architecture/reference/components/conversation-core.md": "acceptance and dependency gates",
                },
                constitutional_check=(
                    "Validation runner must execute only Docker-based suites (C-080), collect UX-CONV/CCT-UX evidence, and emit review-ready pass/fail artifacts without deployment or workflow trigger side effects."
                ),
                model_hint="auto",
                max_tokens=8000,
            ),
        ]
    },
    # ── GROOMER INJECTION POINT — groom_sprint.py injects new sprint handlers here ──
}


# ── ADR-041 P1a: SKIPPED_IDEMPOTENT helper ───────────────────────────────────

def _all_outputs_present_and_compile(subtasks: list) -> bool:
    """Return True if every output_file from all subtasks exists, passes
    py_compile + ruff, pytest -x (full execution for test files), and contains
    no LOGIC_FILLER stubs.

    Root cause fix (5-Why run 30977112176 + 30977112176):
    --collect-only only catches import errors; logic failures (wrong DB setup,
    wrong patch targets, wrong assertions) pass collection but fail execution.
    Running pytest -x ensures generated tests must PASS, not just import.
    """
    import py_compile
    import subprocess
    _FILLER_MARKER = "# [WAOOAW_LOGIC_FILLER_START]"
    py_files: list = []
    for st in subtasks:
        for rel_path in getattr(st, "output_files", []):
            fpath = REPO_ROOT / rel_path
            if not fpath.exists():
                return False
            if str(fpath).endswith(".py"):
                try:
                    py_compile.compile(str(fpath), doraise=True)
                except py_compile.PyCompileError:
                    return False
                if _FILLER_MARKER in fpath.read_text(encoding="utf-8"):
                    return False
                py_files.append(rel_path)
    # ruff check — matches response_evaluator._compile_python style gate
    if py_files:
        ruff = subprocess.run(
            ["python3", "-m", "ruff", "check"] + [str(REPO_ROOT / f) for f in py_files],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if ruff.returncode != 0:
            return False
    # pytest -x (full execution) for test files — collect-only misses logic failures.
    # C-080: run tests inside Docker test-runner, never host Python.
    test_files = [f for f in py_files if f.startswith("tests/") or "/tests/" in f]
    if test_files:
        test_run = subprocess.run(
            ["docker", "compose", "--profile", "test", "run", "--rm", "test-runner",
             "python3", "-m", "pytest", "-x", "-q", "--tb=short"]
            + test_files,
            capture_output=True, text=True, cwd=REPO_ROOT,
            timeout=120,
        )
        if test_run.returncode != 0:
            return False
    return True


# ── Main execution ────────────────────────────────────────────────────────────

def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    force_task = os.environ.get("FORCE_TASK", "").strip()
    github_repo = os.environ.get("GITHUB_REPO", "")

    print("=" * 60)
    print("  WAOOAW Autonomous Sprint Agent")
    print(f"  Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"  Force task: {force_task or 'none'}")
    print("=" * 60)

    # ── Step 1: Parse sprint state ────────────────────────────────────────
    try:
        state = parse_sprint_state()
    except ValueError as e:
        print(f"ERROR: {e}")
        set_output("result", "FAILED")
        set_output("halt", "false")
        return 1

    print(f"\nSprint state:")
    print(f"  platform_phase    : {state.get('platform_phase', 'SPEC')}")
    print(f"  autonomous_halt   : {state.get('autonomous_halt', 'true')}")
    print(f"  current_sprint    : {state.get('current_sprint', '')}")
    print(f"  sprint_status     : {state.get('sprint_status', '')}")

    # ── Step 2: Platform phase + HALT gate (C-001, platform_phase check) ──
    # check_platform_phase_gate calls sys.exit(0) on SPEC phase or HALT=true.
    # This is the hard gate preventing unauthorized implementation.
    check_platform_phase_gate(state)

    set_output("halt", "false")

    # ── Step 2b: Runner integrity gate (fail-fast for internal pipeline bugs) ──
    integrity_ok, integrity_errors = run_runner_integrity_checks(globals())
    if not integrity_ok:
        print("\nRunner integrity gate FAILED:")
        for err in integrity_errors:
            print(f"  - {err}")
        set_output("result", "PIPELINE_BUG")
        set_output("halt", "true")
        return 1

    # ── Step 3: Consecutive failure check ─────────────────────────────────
    failures = int(state.get("consecutive_failures", "0") or "0")
    if failures >= 3:
        print(f"\nConsecutive failures: {failures} >= 3 - creating Constitutional Blocker")
        if not dry_run and github_repo:
            title = f"CB: Autonomous Sprint {state.get('current_sprint', '?')} - {failures} consecutive failures"
            body = (
                f"Constitutional Blocker - Autonomous Sprint Failure\n\n"
                f"Sprint: {state.get('current_sprint', '?')}\n"
                f"Consecutive failures: {failures}\n"
                f"Action: Review workflow runs, fix root cause, reset consecutive_failures: 0\n"
                f"Constitutional basis: C-001 (Human Override)"
            )
            gh(["issue", "create", "--title", title, "--body", body,
                "--label", "type:constitutional-blocker,status:blocked",
                "--repo", github_repo], check=False)
        set_output("result", "FAILED")
        return 1

    # ── Step 4: Determine tasks to run — read from WC file, not PROJECT_STATE ──
    sprint = state.get("current_sprint", "")
    set_output("sprint", sprint)

    try:
        wc_tasks = parse_wc_tasks(sprint)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        set_output("result", "FAILED")
        return 1

    tasks_done_state = wc_tasks["done"]
    # ADR-041 P1c: failed tasks (failed_structural, failed_transient, skipped_cascade)
    # are retry-eligible — they are NOT excluded from the next run's queue.
    # Only "done" / "skipped_idempotent" are truly complete and excluded.
    pending_and_failed = wc_tasks["pending"] + wc_tasks["failed"]
    tasks = [force_task] if force_task else pending_and_failed
    print(f"  tasks_pending     : {wc_tasks['pending']}")
    print(f"  tasks_failed(retry): {wc_tasks['failed']}")
    print(f"  tasks_done        : {tasks_done_state}")

    if not tasks:
        print("\nNo tasks remaining. Sprint may already be DONE.")
        set_output("result", "SKIPPED")
        return 0

    # Fresh-start signal: READY + no completed tasks means start from latest main.
    has_completed_tasks = bool(tasks_done_state)
    is_fresh_start = str(state.get("sprint_status", "")).upper() == "READY" and not has_completed_tasks

    # ── Step 5: Setup branch ──────────────────────────────────────────────
    branch = state.get("branch", f"ib/009/{sprint.lower()}")
    if not dry_run:
        git(["fetch", "origin", "main"], check=False)
        remote_check = git(["ls-remote", "--exit-code", "--heads", "origin", branch], check=False)

        if branch == "main":
            # main is always the current worktree — delete/recreate is illegal.
            git(["checkout", "main"], check=False)
            git(["pull", "origin", "main"], check=False)
            print("  Branch setup: branch=main — pulled origin/main, skipping freshness guard")
        elif is_fresh_start:
            # Extra check: if the remote branch already has commits beyond main,
            # it contains work from a completed successful run — preserve it.
            branch_has_work = False
            if remote_check.returncode == 0:
                ahead = run(["git", "rev-list", "--count", f"origin/main..origin/{branch}"], check=False, capture=True)
                if ahead.returncode == 0 and int(ahead.stdout.strip() or "0") > 0:
                    branch_has_work = True
                    print(f"  Branch freshness guard: {branch} has {ahead.stdout.strip()} commit(s) ahead of main — preserving completed work")

            if branch_has_work:
                # Resume from the existing branch — don't discard completed work.
                # Use checkout -b to create a local tracking branch; plain checkout
                # of a remote-only ref results in detached HEAD which breaks git push.
                local_ref = git(["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)
                if local_ref.returncode == 0:
                    git(["checkout", branch], check=False)
                else:
                    git(["checkout", "-b", branch, f"origin/{branch}"], check=False)
                git(["pull", "origin", branch], check=False)
                # ── Main-merge gate: canonical pipeline scripts (sprint_retry_advisor,
                # goal_executor, response_evaluator) live on main and must be merged into
                # every sprint run — fresh-start or not. Without this, the sprint branch
                # carries stale script versions that silently override the workflow PIPELINE SYNC.
                print(f"  Branch main-merge (fresh-start resume): merging origin/main into {branch}")
                _merge_fs = git(["merge", "origin/main", "--no-edit",
                                 "-m", f"chore: merge main pipeline fixes into {branch}"], check=False)
                if _merge_fs.returncode != 0:
                    for _cf in ["pyproject.toml", "scripts/task_decomposer.py",
                                "scripts/autonomous_sprint_runner.py",
                                "scripts/magic_llm/context_builder.py",
                                "scripts/magic_llm/response_evaluator.py",
                                "scripts/goal_orchestrator/goal_executor.py",
                                "scripts/sprint_retry_advisor.py"]:
                        git(["checkout", "origin/main", "--", _cf], check=False)
                    git(["add", "-A"], check=False)
                    git(["commit", "--no-edit"], check=False)
                    print(f"  Branch main-merge: conflict resolved (took main's pipeline config)")
            else:
                print(f"  Branch freshness guard: rebuilding {branch} from latest origin/main")
                # Ensure we are not on the sprint branch before deleting/resetting it.
                current_branch = run(["git", "branch", "--show-current"], capture=True).stdout.strip()
                if current_branch == branch:
                    git(["checkout", "main"], check=False)

                git(["checkout", "main"], check=False)
                git(["pull", "origin", "main"], check=False)

                # Delete stale local sprint branch if present.
                local_ref = git(["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)
                if local_ref.returncode == 0:
                    git(["branch", "-D", branch], check=False)

                # Delete stale remote sprint branch if present.
                if remote_check.returncode == 0:
                    del_remote = git(["push", "origin", "--delete", branch], check=False)
                    if del_remote.returncode != 0:
                        print(f"  WARN: could not delete remote {branch}; continuing with local fresh branch")

                git(["checkout", "-b", branch, "origin/main"])
        else:
            if remote_check.returncode == 0:
                git(["checkout", branch])
                git(["pull", "origin", branch])
                # ── Main-merge gate: always bring sprint branch up to date with main ──
                # Ensures fixes landed on main (pyproject.toml, FORBIDDEN_PATTERNS, Retry Advisor
                # rules, etc.) are visible to every sprint run, not just fresh-start runs.
                # Uses --no-ff to preserve sprint history; conflicts resolved in favour of main
                # for pipeline config files (pyproject.toml, scripts/) since those are canonical.
                print(f"  Branch main-merge: merging origin/main into {branch} to pick up pipeline fixes")
                merge = git(["merge", "origin/main", "--no-edit",
                             "-m", f"chore: merge main pipeline fixes into {branch}"], check=False)
                if merge.returncode != 0:
                    # Auto-resolve conflicts: always take main's version of pipeline config files.
                    # These are canonical — the sprint branch should never diverge from main's pipeline.
                    for config_file in ["pyproject.toml", "scripts/task_decomposer.py",
                                        "scripts/autonomous_sprint_runner.py",
                                        "scripts/magic_llm/context_builder.py",
                                        "scripts/magic_llm/response_evaluator.py",
                                        "scripts/goal_orchestrator/goal_executor.py",
                                        "scripts/sprint_retry_advisor.py"]:
                        git(["checkout", "origin/main", "--", config_file], check=False)
                    git(["add", "-A"], check=False)
                    # git merge --continue does NOT accept --no-edit; use git commit instead
                    git(["commit", "--no-edit"], check=False)
                    print(f"  Branch main-merge: conflict resolved (took main's pipeline config)")
            else:
                # Branch may already exist locally (local dev or resume run) — try checkout first
                local_check = git(["checkout", branch], check=False)
                if local_check.returncode != 0:
                    git(["checkout", "-b", branch])

        record_evidence("AUTONOMOUS_SPRINT_STARTED", sprint=sprint,
                        branch=branch, tasks=tasks)

        # P0 Fix 1b: Restore frozen-artifacts.json from sprint branch if present.
        # This ensures constructor signatures from prior runs are available to ContextBuilder.
        frozen_registry_path = REPO_ROOT / "sprint-context" / "frozen-artifacts.json"
        if not frozen_registry_path.exists() and (REPO_ROOT / "sprint-context").is_dir():
            print(f"  INFO: frozen-artifacts.json not found — fresh ContextBuilder registry will be built")
        elif frozen_registry_path.exists():
            import json as _json
            try:
                frozen = _json.loads(frozen_registry_path.read_text())
                print(f"  Frozen registry restored: {len(frozen)} artifact(s) available for ContextBuilder")
            except Exception:
                pass
        update_sprint_state(sprint_status="IN_PROGRESS")
        # ADR-041 P2a: write OPEN heartbeat so container kills are detectable
        _hb_run_id = _MONITOR_SIGNAL.get("run_id") or os.environ.get("GITHUB_RUN_ID", "local")
        write_run_heartbeat(_hb_run_id, sprint)

    # ── Step 6: Execute each task ─────────────────────────────────────────
    tasks_done = []
    tasks_not_implemented = []
    infra_error_tasks = _INFRA_ERROR_TASKS   # populated by execute_with_llm on pure API failures
    # Accumulate all completed subtask IDs across task boundaries for cross-task
    # depends_on resolution. WC013-03a depends_on WC013-02a — without this,
    # WC013-03a is always BLOCKED because completed[] starts fresh each chain.
    #
    # CROSS-SESSION FIX: seed from tasks_done in sprint state so that subtasks
    # completed in previous runs are recognised as fulfilled dependencies.
    # Without this, resumed runs see BLOCKED for any task whose depends_on
    # subtask was completed in a prior session (e.g. WC014-03a depends on WC014-02a).
    all_completed_subtask_ids: list[str] = []
    all_failed_subtask_ids: list[str] = []  # P1: cross-task failed-dep guard
    for prior_task_id in tasks_done_state:
        prior_handler = TASK_HANDLERS.get(prior_task_id)
        if isinstance(prior_handler, dict) and "subtasks" in prior_handler:
            all_completed_subtask_ids.extend(
                [st.id for st in prior_handler["subtasks"]]
            )
    if all_completed_subtask_ids:
        print(f"  Cross-session subtask IDs seeded: {all_completed_subtask_ids}")
    # RC#1: scaffold task for this run = first queued task that is in SCAFFOLD_TASKS.
    # If scaffold already succeeded in a prior run, it won't be in tasks — scaffold_run_task=None.
    scaffold_run_task = next((t for t in tasks if t in SCAFFOLD_TASKS), None)
    for task in tasks:
        handler = TASK_HANDLERS.get(task)
        if handler is None:
            # P1-04: explicit NOT_IMPLEMENTED — not silent skip
            print(f"  ⚠️  TASK_NOT_IMPLEMENTED: {task}")
            print(f"       This task requires LLM code generation (IB-020).")
            print(f"       Runner does not yet have code generation capability.")
            print(f"       Action: Implement IB-020 (ADR-030) before this sprint can execute.")
            tasks_not_implemented.append(task)
            continue
        if dry_run:
            print(f"  DRY RUN: would execute {task}")
            continue
        try:
            # FA-021 gate: WC015 requires GCP Vertex AI SA key in Key Vault / env
            if task.startswith("WC015") and not os.environ.get("GOOGLE_VERTEX_SA_KEY"):
                print(f"  ❌ FA-021 gate: WC015 requires GOOGLE_VERTEX_SA_KEY in environment.")
                print(f"     See FOUNDER-ACTION.md T1-02. Set secret in Azure Key Vault first.")
                tasks_not_implemented.append(task)
                continue
            # Route through TaskDecomposer if task is a dict with subtasks (IB-021 / WC-019)
            # Backward compatible: callable handlers still execute directly (WC011-xx, WC012-01/02)
            if callable(handler):
                success = handler()
            elif isinstance(handler, dict) and "subtasks" in handler:
                # C-086: check simulation exists before calling LLM
                ok, sim_msg = _check_simulation(task)
                if not ok:
                    print(f"  ❌ C-086: {sim_msg}")
                    print(f"  Create simulation/SIM-PL-002-{task}-*.md with Verdict: PASS first.")
                    tasks_not_implemented.append(task)
                    continue
                print(f"  ✅ C-086 gate: {sim_msg}")
                # ADR-041 P1a: SKIPPED_IDEMPOTENT — all outputs exist & compile → skip LLM
                if _all_outputs_present_and_compile(handler["subtasks"]):
                    print(f"  ⏭  SKIPPED_IDEMPOTENT: {task} — all outputs already present and compile-clean")
                    tasks_done.append(task)
                    update_task_status(sprint, task, "skipped_idempotent")
                    all_completed_subtask_ids.extend([st.id for st in handler["subtasks"]])
                    continue
                # ADR-041 P0a: mark in-progress before any LLM call so container kills are detectable
                update_task_status(sprint, task, "in-progress")
                success = _execute_task_decomposed(
                    task, handler["subtasks"], _MONITOR_SIGNAL,
                    infra_error_tasks=infra_error_tasks,
                    dry_run=dry_run,
                    prior_completed=all_completed_subtask_ids,
                    prior_failed=all_failed_subtask_ids,
                )
                # P1: accumulate by actual outcome, not unconditionally
                _sr = _MONITOR_SIGNAL.get("subtask_results", {})
                for _st in handler["subtasks"]:
                    _outcome = _sr.get(_st.id, {}).get("result", "")
                    if _outcome in ("FAIL", "SKIPPED", "SKIPPED_CASCADE", "BLOCKED_SKELETON_MISSING"):
                        all_failed_subtask_ids.append(_st.id)
                    else:
                        all_completed_subtask_ids.append(_st.id)
            else:
                print(f"  ⚠️  TASK_NOT_IMPLEMENTED: {task} — unknown handler format")
                tasks_not_implemented.append(task)
                continue
            if success:
                tasks_done.append(task)
                # RC#2: Write task status to WC file — single source of truth for task progress.
                update_task_status(sprint, task, "done")
                print(f"  DONE: {task}")
            else:
                print(f"  FAILED: {task}")
                # ADR-041 P1b: record failure type so next RESUME skips cascade dependents
                update_task_status(sprint, task, "failed_structural")
                # RC#1: Halt on scaffold failure (C-084 Step Dependency Ordering)
                if task == scaffold_run_task:
                    print(f"  HALT: scaffold task {task} failed — downstream tasks cannot build. "
                          f"Stopping sprint. (C-084)")
                    break
                # C-084 2.0: task-level fair-sweep — do NOT halt on non-scaffold failures.
                # WC012-03 and WC012-04 have their own deterministic data layers and
                # independent subtasks. They do not depend on WC012-02 at the task level.
                # Continue — branch context gives next task full state from prior completed work.
                print(f"  CONTINUE: task {task} failed — proceeding with remaining independent tasks "
                      f"(C-084 2.0 fair-sweep). Next run retries failed tasks. (C-077 + C-084)")
        except Exception as exc:
            print(f"  FAILED: {task}: {exc}")
            # RC#1 / chain halt on exception too
            print(f"  HALT: exception on {task} — stopping sprint. (C-084)")
            break

    # Determine if ALL failures were infrastructure (no spec gap, no human action needed)
    all_infra_errors = (
        not tasks_done
        and not tasks_not_implemented
        and len(infra_error_tasks) > 0
        and len(infra_error_tasks) == len([t for t in tasks if t not in tasks_done and t not in tasks_not_implemented])
    )

    # ── Step 7: Update state + open PR ────────────────────────────────────
    if dry_run:
        set_output("result", "DRY_RUN")
        return 0

    record_evidence("SPRINT_TASKS_EXECUTED", sprint=sprint, tasks_done=tasks_done)

    all_tasks_completed = len(tasks_done) == len(tasks) and len(tasks) > 0

    if all_tasks_completed:
        update_sprint_state(consecutive_failures=0)
    else:
        # Infrastructure failures do not count toward spec consecutive_failures.
        if all_infra_errors:
            print(f"  INFRA_ERROR: transient infrastructure failure (spec failure counter unchanged)")
        else:
            failures_new = failures + 1
            update_sprint_state(consecutive_failures=str(failures_new))

    # Final commit: WC file + logs (PROJECT_STATE.md not touched by runner)
    git(["add", "work-contracts/", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             f"chore(pm): {sprint} tasks done: {', '.join(tasks_done)}\n\n"
             f"IB: IB-009\nConstitutional: C-059"])

    # ── Push sprint branch using App installation token (workflows scope) ────
    # GITHUB_TOKEN (Actions default) cannot push branches containing .github/workflows/
    # because it lacks the `workflows` write scope. The App token has this scope.
    # Registry entry: SPRINT_BRANCH_PUSH GH_WORKFLOW_SCOPE — 3 runs blocked (2026-07-29).
    def _get_push_token() -> str:
        """Return App installation token if credentials available, else GITHUB_TOKEN."""
        app_id  = os.environ.get("GH-APP-ID", "")
        inst_id = os.environ.get("GH-APP-INSTALLATION-ID", "")
        pem_key = os.environ.get("GH-APP-PRIVATE-KEY", "")
        if app_id and inst_id and pem_key:
            try:
                import importlib.util as _ilu  # noqa: E401 (inner scope)
                import sys as _sys
                _scripts = str(REPO_ROOT / "scripts")
                if _scripts not in _sys.path:
                    _sys.path.insert(0, _scripts)
                _s = _ilu.spec_from_file_location(
                    "autonomous_sprint_reviewer",
                    str(REPO_ROOT / "scripts" / "autonomous_sprint_reviewer.py"))
                _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
                token = _m.generate_installation_token(app_id, inst_id, pem_key)
                if token:
                    print("  PUSH: using App installation token (workflows scope) ✓")
                    return token
            except Exception as _te:
                print(f"  PUSH: App token generation failed ({_te}) — falling back to GITHUB_TOKEN")
        return os.environ.get("GITHUB_TOKEN", "")

    push_token = _get_push_token()

    def _git_push_with_token(token: str, extra_args: list[str]) -> subprocess.CompletedProcess:
        """Configure git to use the given token for a single push, then push."""
        repo_url = f"https://x-access-token:{token}@github.com/{os.environ.get('GITHUB_REPOSITORY', 'dlai-sd/waooaw-platform')}.git"
        env_with_url = {**os.environ, "GIT_REMOTE_URL": repo_url}
        # Temporarily override origin URL for this push only
        run(["git", "remote", "set-url", "origin", repo_url], check=False)
        result = run(["git", "push"] + extra_args + ["origin", branch], check=False, capture=True)
        # Restore origin to HTTPS without token
        run(["git", "remote", "set-url", "origin",
             f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'dlai-sd/waooaw-platform')}.git"],
            check=False)
        return result

    push = _git_push_with_token(push_token, ["-u"])
    if push.returncode != 0:
        push_err = (push.stderr or push.stdout or "").strip()
        print(f"  WARN: branch push failed (non-fatal): {push_err[:200]}")
        # Retry once with --force in case of ref mismatch.
        force_push = _git_push_with_token(push_token, ["--force"])
        if force_push.returncode != 0:
            force_err = (force_push.stderr or force_push.stdout or "").strip()
            print(f"  WARN: force push failed (non-fatal): {force_err[:200]}")

    # ── Step 8: Open/update PR ────────────────────────────────────────────
    if tasks_not_implemented:
        run_result = "NOT_IMPLEMENTED"
    elif all_infra_errors:
        run_result = "INFRA_ERROR"
    elif all_tasks_completed:
        run_result = "SUCCESS"
    else:
        run_result = "PARTIAL"

    # ── Step 8.0: Print cost-per-file summary ─────────────────────────────────
    if _MONITOR_SIGNAL.get("file_costs"):
        total_cost = sum(_MONITOR_SIGNAL["file_costs"].values())
        print("\n  ╔══════════════════════════════════════════════════════╗")
        print(  "  ║           LLM COST SUMMARY (C-077 FinOps)           ║")
        print(  "  ╠══════════════════════════════════════════════════════╣")
        for key, cost in sorted(_MONITOR_SIGNAL["file_costs"].items(), key=lambda x: -x[1]):
            label = key[:48].ljust(48)
            print(f"  ║  {label}  ₹{cost:>7.4f} ║")
        print(  "  ╠══════════════════════════════════════════════════════╣")
        print(f"  ║  {'TOTAL'.ljust(48)}  ₹{total_cost:>7.4f} ║")
        print(  "  ╚══════════════════════════════════════════════════════╝")
        _MONITOR_SIGNAL["total_cost_inr"] = total_cost

    # ── Step 8.1: Emit monitor signal BEFORE any early returns in PR section ──
    # Any early return below (no github_repo, no tasks done, infra error) would
    # skip the signal write at the end of main(). Writing it here ensures
    # complete_sprint always finds a valid signal via 'git show origin/BRANCH:...'.
    scaffold_t = next((t for t in tasks if t in SCAFFOLD_TASKS), None)
    scaffold_failed = scaffold_t is not None and scaffold_t not in tasks_done
    _MONITOR_SIGNAL["sprint"] = sprint
    _MONITOR_SIGNAL["tasks_done"] = tasks_done
    _MONITOR_SIGNAL["tasks_requested"] = tasks
    _MONITOR_SIGNAL["scaffold_task"] = scaffold_t
    _MONITOR_SIGNAL["scaffold_failed"] = scaffold_failed
    _MONITOR_SIGNAL["overall_result"] = run_result
    signal_path = Path("sprint-context/monitor-signal.json")
    signal_path.parent.mkdir(exist_ok=True)
    import json as _json
    signal_path.write_text(_json.dumps(_MONITOR_SIGNAL, indent=2))
    print(f"  📡 Monitor signal emitted: {signal_path}")
    git(["add", "-f", str(signal_path)], check=False)  # -f: signal_path is in .gitignore
    sig_diff = git(["diff", "--cached", "--quiet"], check=False)
    if sig_diff.returncode != 0:
        git(["commit", "-m",
             f"chore(signal): {sprint} run {os.environ.get('GITHUB_RUN_ID', 'local')} — {run_result}\n\n"
             f"Constitutional: C-069 — observable state for complete_sprint step"],
            check=False)
        _git_push_with_token(push_token, ["-f"])
        print("  📡 Monitor signal pushed to sprint branch ✓")

    if not github_repo:
        set_output("result", run_result)
        return 0

    existing = gh(["pr", "list", "--head", branch,
                   "--json", "number", "--jq", ".[0].number",
                   "--repo", github_repo], check=False)
    existing_num = existing.stdout.strip() if existing.returncode == 0 else ""

    # Never open an empty PR — a PR with no code commits is noise (C-077 FinOps)
    if not tasks_done and not existing_num:
        print("  No tasks completed and no existing PR — skipping PR creation (empty PR is noise).")
        set_output("result", "PARTIAL")
        return 0

    if not existing_num:
        pr_title = f"feat(infra): {sprint} - Autonomous Sprint Execution"
        pr_body = (
            f"IB Reference: IB-009 - Foundation Implementation\n"
            f"Work Contract: {sprint}\n"
            f"Office: WAOOAW AI Agent - Platform IT Expert (Autonomous Sprint)\n"
            f"Execution mode: Autonomous (C-066 Tier 2A)\n\n"
            f"Tasks executed: {', '.join(tasks_done) or 'none (Copilot workspace required)'}\n\n"
            f"Constitutional basis: C-066 Tier 2A, C-070, C-059, C-065\n"
            f"Bootstrap evidence: logs/bootstrap-evidence.jsonl\n"
            f"Run ID: {os.environ.get('GITHUB_RUN_ID', 'local')}"
        )
        result = gh(["pr", "create",
                     "--title", pr_title,
                     "--body", pr_body,
                     "--base", "main",
                     "--head", branch,
                     "--label", "tier:2-feature",
                     "--label", "status:pr-open",
                     "--label", "awaiting:review",
                     "--repo", github_repo], check=False)
        if result.returncode != 0:
            print(f"  WARN: gh pr create failed (rc={result.returncode}): {result.stderr[:300]}")
        pr_num = result.stdout.strip().split("/")[-1] if result.returncode == 0 else ""
        if pr_num:
            print(f"  PR created: #{pr_num}")
    else:
        pr_num = existing_num
        print(f"  PR updated: #{pr_num}")

    set_output("pr_number", pr_num)
    if tasks_not_implemented:
        set_output("result", run_result)
        set_output("halt_reason", f"Tasks {tasks_not_implemented} require IB-020 LLM code generation — not yet implemented")
        print(f"\n  ⚠️  {len(tasks_not_implemented)} task(s) require IB-020 (runner code generation).")
        print(f"  Sprint cannot advance until IB-020 is implemented.")
        print(f"  Issue #12 tracks this: github.com/dlai-sd/waooaw-platform/issues/12")
    elif not tasks_done and all_infra_errors:
        # Every task failed due to API infrastructure (timeout/rate-limit/server error)
        set_output("result", run_result)
        set_output("halt_reason", "All tasks failed due to API timeouts or rate limits. No spec gap. Next cron run will retry automatically.")
        print("\n  ⚠️  INFRA_ERROR: all tasks failed due to API failures, not spec issues.")
        print("  Cron will retry. No founder action required.")
    else:
        set_output("result", run_result)

    # ── Emit monitor signal artifact (C-069 — observable state for downstream jobs) ──
    # Scaffold task = first task in this run's queue that is in SCAFFOLD_TASKS.
    # If scaffold already succeeded in a prior run, it's not in the queue → scaffold_task=None.
    scaffold_t = next((t for t in tasks if t in SCAFFOLD_TASKS), None)
    scaffold_failed = scaffold_t is not None and scaffold_t not in tasks_done
    _MONITOR_SIGNAL["sprint"] = sprint
    _MONITOR_SIGNAL["tasks_done"] = tasks_done
    _MONITOR_SIGNAL["tasks_requested"] = tasks
    _MONITOR_SIGNAL["scaffold_task"] = scaffold_t
    _MONITOR_SIGNAL["scaffold_failed"] = scaffold_failed
    _MONITOR_SIGNAL["overall_result"] = run_result
    # Scalar outputs consumed directly by the monitor job
    # (scaffold_t and scaffold_failed set in step 8.1 above)
    set_output("scaffold_failed", str(scaffold_failed).lower())
    set_output("infra_error_tasks", ",".join(str(t) for t in infra_error_tasks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
