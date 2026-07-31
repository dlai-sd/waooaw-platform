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
                description="Implement IMarkupEngine.derive_bundle_cost_floor(), validate_price() and BundleEngine data models with C-089 constitutional margin floor enforcement and C-059 audit logging.",
                type="llm",
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
                    "Implement IMarkupEngine.derive_bundle_cost_floor(agent_type: str, bundle_tier: str) → int:\n"
                    "  - Read cost_floor_paise from bundle_profiles table — DO NOT recompute\n"
                    "  - Return floor value in INR paise\n\n"
                    "Implement IMarkupEngine.validate_price(agent_type: str, bundle_tier: str, proposed_price_paise: int) → PriceValidation:\n"
                    "  - Fetch cost_floor_paise and minimum_margin_pct from bundle_profiles\n"
                    "  - Calculate minimum_compliant_price_paise = floor / (1 - minimum_margin_pct/100)\n"
                    "  - C-089: Raise BelowConstitutionalFloorError if proposed_price_paise < minimum_compliant_price_paise\n"
                    "  - C-059: Write audit record to pricing_floor_log table on BOTH APPROVED and REJECTED outcomes\n"
                    "  - Return PriceValidation with valid, cost_floor_paise, constitutional_minimum_margin_pct, below_floor, margin_pct fields\n\n"
                    "Implement BundleEngine.derive_price(agent_type: str, bundle_tier: str, target_margin_pct: int | None = None) → int:\n"
                    "  - If target_margin_pct is None, use bundle_profiles.minimum_margin_pct\n"
                    "  - Apply formula: derived_price = cost_floor / (1 - margin/100) [margin-on-revenue]\n"
                    "  - Return price in INR paise\n\n"
                    "Create Pydantic models ThreadEntry, BundleProfile, PriceConfig, PriceValidationRequest, PriceDeriveRequest.\n"
                    "Implement business logic. Type annotations optional here — polish pass adds them.\n"
                    "Constitutional basis: C-089 (margin floor enforcement), C-059 (pricing audit log), C-088 (billing profile gate), C-048 (non-exploitation), C-051 (institutional transparency)."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC027-01ab",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
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
                description=(
                    "Pytest suite for billing-engine markup models and BundleEngine: "
                    "validates Pydantic schemas, cost_floor DB-read contract, "
                    "margin-on-revenue derive_price formula, validate_price audit writes "
                    "on both APPROVED and REJECTED outcomes (C-059), and all error paths."
                ),
                type="llm",
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
                    "# ── PYDANTIC MODEL TESTS ──────────────────────────────────────────────\n"
                    "# happy path:\n"
                    "#   ThreadEntry: valid construction with all fields; assert field types.\n"
                    "#   BundleProfile: valid cost_floor_paise (int >= 0), minimum_margin_pct\n"
                    "#     (float 0–100); assert round-trip JSON serialisation is lossless.\n"
                    "#   PriceConfig: valid nested BundleProfile list; assert lookup by key.\n"
                    "#   PriceValidationRequest: agent_type + bundle_tier + proposed_price_paise\n"
                    "#     all present; assert Pydantic does NOT coerce negative paise.\n"
                    "#   PriceDeriveRequest: target_margin_pct is Optional; omitting it\n"
                    "#     produces a valid model (defaults to None, not zero).\n"
                    "#   PriceValidation: outcome in {'APPROVED','REJECTED'}; assert\n"
                    "#     minimum_compliant_price_paise and proposed_price_paise are both\n"
                    "#     present as int fields; cost_floor_paise present as int.\n"
                    "# error cases:\n"
                    "#   BundleProfile: minimum_margin_pct > 100 must raise ValidationError.\n"
                    "#   BundleProfile: cost_floor_paise < 0 must raise ValidationError.\n"
                    "#   PriceValidationRequest: missing agent_type raises ValidationError.\n"
                    "#   PriceValidationRequest: proposed_price_paise as float (not int)\n"
                    "#     must either coerce to int or raise ValidationError — assert\n"
                    "#     the model's declared behaviour consistently.\n"
                    "#   PriceValidation: outcome not in allowed set raises ValidationError.\n"
                    "\n"
                    "# ── BUNDLE ENGINE UNIT TESTS ──────────────────────────────────────────\n"
                    "# Fixture strategy: mock the DB session / repository with pytest fixtures\n"
                    "# so BundleEngine never touches a real database.\n"
                    "# Use pytest-asyncio (asyncio_mode='auto') for any async methods.\n"
                    "\n"
                    "# cost_floor — happy path:\n"
                    "#   Given a mocked DB that returns bundle_profiles.cost_floor_paise=5000\n"
                    "#   for agent_type='CODER', bundle_tier='PRO', assert cost_floor returns\n"
                    "#   exactly 5000 (reads from DB, does NOT recompute).\n"
                    "#   Assert the DB query was called exactly once (no internal arithmetic).\n"
                    "\n"
                    "# cost_floor — error cases:\n"
                    "#   Unknown agent_type or bundle_tier: DB returns None / raises NotFound;\n"
                    "#   assert BundleEngine raises a clear exception (ValueError or a domain\n"
                    "#   exception) — not a silent zero.\n"
                    "\n"
                    "# derive_price — happy path (margin-on-revenue formula):\n"
                    "#   floor=8000, target_margin_pct=20.0  →  price = 8000/(1-0.20) = 10000\n"
                    "#   floor=5000, target_margin_pct=25.0  →  price = 5000/(1-0.25) = 6667\n"
                    "#     (assert integer rounding — ceiling or round — is consistent).\n"
                    "#   floor=6000, target_margin_pct=None  →  uses bundle_profiles.minimum_margin_pct\n"
                    "#     from DB (e.g. 15.0) → price = 6000/(1-0.15) = 7059; assert DB\n"
                    "#     minimum_margin_pct was read, not a hardcoded default.\n"
                    "\n"
                    "# derive_price — error cases:\n"
                    "#   target_margin_pct=100.0 → division by zero; assert ValueError raised.\n"
                    "#   target_margin_pct=110.0 → margin > 100; assert ValueError raised.\n"
                    "#   target_margin_pct=-5.0  → negative margin; assert ValueError raised.\n"
                    "\n"
                    "# validate_price — happy path APPROVED:\n"
                    "#   proposed_price_paise >= minimum_compliant_price → outcome='APPROVED'.\n"
                    "#   Assert PriceValidation.outcome == 'APPROVED'.\n"
                    "#   Assert PriceValidation.minimum_compliant_price_paise is correct int.\n"
                    "#   Assert PriceValidation.cost_floor_paise matches mocked DB value.\n"
                    "#   Assert proposed_price_paise echoed back unchanged.\n"
                    "#   Assert pricing_floor_log DB write was called exactly once (C-059).\n"
                    "\n"
                    "# validate_price — happy path REJECTED:\n"
                    "#   proposed_price_paise < minimum_compliant_price → outcome='REJECTED'.\n"
                    "#   Assert outcome == 'REJECTED'.\n"
                    "#   Assert minimum_compliant_price_paise still returned (caller needs it\n"
                    "#     to know how much to raise by).\n"
                    "#   Assert pricing_floor_log DB write was called exactly once (C-059).\n"
                    "#   C-059 INVARIANT: audit must be written even on REJECTED — the mock\n"
                    "#     assert must fire for both branches, not only APPROVED.\n"
                    "\n"
                    "# validate_price — idempotency:\n"
                    "#   Calling validate_price twice with identical args produces two\n"
                    "#   independent audit log rows (not deduplicated). Assert mock DB write\n"
                    "#   call_count == 2 after two calls. Outcomes must be identical.\n"
                    "\n"
                    "# validate_price — boundary:\n"
                    "#   proposed_price_paise == minimum_compliant_price_paise exactly →\n"
                    "#   must be APPROVED (inclusive lower bound).\n"
                    "#   proposed_price_paise == minimum_compliant_price_paise - 1 →\n"
                    "#   must be REJECTED.\n"
                    "\n"
                    "# validate_price — error cases:\n"
                    "#   DB write to pricing_floor_log raises; assert exception propagates\n"
                    "#   (do NOT swallow audit failures — C-059 is non-negotiable).\n"
                    "#   Unknown agent_type → propagates DB lookup error before writing log.\n"
                    "\n"
                    "# ── CONSTITUTIONAL INVARIANTS ─────────────────────────────────────────\n"
                    "# C-059 (Audit Obligation):\n"
                    "#   In EVERY validate_price test — APPROVED or REJECTED — assert that\n"
                    "#   pricing_floor_log insert was called. Use a dedicated parametrised\n"
                    "#   test: @pytest.mark.parametrize('proposed,expected_outcome', [\n"
                    "#       (99999, 'APPROVED'), (1, 'REJECTED')]) that asserts both the\n"
                    "#   outcome AND the audit write in a single table-driven test.\n"
                    "#   Label this test with @pytest.mark.constitutional to make it easy\n"
                    "#   to identify in CI.\n"
                    "# cost_floor DB-read contract:\n"
                    "#   Assert that cost_floor NEVER performs arithmetic — it returns the\n"
                    "#   raw DB value. Use a mock that returns an arbitrary odd prime (e.g.\n"
                    "#   7919) and assert the return value equals 7919 with no transformation.\n"
                    "\n"
                    "# ── FIXTURE REQUIREMENTS ─────────────────────────────────────────────\n"
                    "# mock_db_session: returns a MagicMock/AsyncMock with:\n"
                    "#   .execute() → returns a mock row with cost_floor_paise, minimum_margin_pct\n"
                    "#   .add() / .commit() for pricing_floor_log inserts (C-059 audit).\n"
                    "# bundle_engine(mock_db_session): constructs BundleEngine injected with\n"
                    "#   the mock session — no real DB, no real file I/O.\n"
                    "# All async tests use @pytest.mark.asyncio or asyncio_mode='auto'.\n"
                    "# Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\n"
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
                description="Implement FastAPI router for pricing endpoints: thread-catalog delegation, bundle-cost-floor lookup, price validation with C-089 margin enforcement, and price derivation; mount in main.py",
                type="llm",
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
                    "Implement IMarkupEngine.derive_bundle_cost_floor() and IMarkupEngine.validate_price() from skeleton.\n"
                    "DO NOT change signatures — implement bodies only (ADR-036).\n"
                    "Type annotations optional in scaffold — polish pass enforces ANN001.\n"
                    "C-089: validate_price() MUST raise BelowConstitutionalFloorError if proposed_price_paise < cost_floor_paise * (1 + constitutional_minimum_margin_pct / 100).\n"
                    "C-089: 422 POST /validate response body MUST include minimum_compliant_price_paise on violation.\n"
                    "C-091: GET /thread-catalog MUST delegate to existing ThreadCatalogService without modification.\n"
                    "C-088, C-090, C-051, C-048: Constitutional margin floor and billing profile gate enforcement via price validation layer.\n"
                    "Mount completed router in main.py with prefix /pricing."
                ),
                model_hint="auto",
                max_tokens=4500,
            ),
            SubTaskDef(
                id="WC027-01bb",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
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
                description="Pytest suite for the /pricing FastAPI router covering all four endpoints, C-089 422 body shape, idempotency of /derive, and error/edge cases.",
                type="llm",
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
                    "TEST PASS — write pytest tests using httpx.AsyncClient against the FastAPI app "
                    "mounted in src/billing-engine/main.py. All tests live in tests/billing-engine/test_router.py. "
                    "File is exempt from ANN per pyproject.toml per-file-ignores. "
                    "Use pytest-asyncio (asyncio_mode='auto') for every async test. "
                    "Mock ThreadCatalogService and any Redis/DB dependencies with pytest fixtures "
                    "(monkeypatch or unittest.mock.AsyncMock); do NOT hit real infrastructure.\n\n"

                    "HAPPY PATH — must cover all four endpoints:\n"
                    "  1. GET /pricing/thread-catalog → 200, response body matches the stubbed "
                    "     ThreadCatalogService return value (list of thread entries).\n"
                    "  2. GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} → 200, "
                    "     response JSON contains a numeric 'floor_price_paise' key > 0.\n"
                    "  3. POST /pricing/validate with a fully compliant payload → 200 (or 204), "
                    "     no 'minimum_compliant_price_paise' key in response body.\n"
                    "  4. POST /pricing/derive with valid inputs → 200, response contains "
                    "     'derived_price_paise' as an integer.\n\n"

                    "ERROR CASES — must cover:\n"
                    "  5. POST /pricing/validate with a price below the C-089 floor → 422, "
                    "     response JSON body MUST include 'minimum_compliant_price_paise' as an integer "
                    "     (constitutional invariant: violation detail is machine-readable for callers).\n"
                    "  6. GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} with an unknown "
                    "     agent_type or bundle_tier → 404 with a non-empty detail string.\n"
                    "  7. POST /pricing/validate with a malformed body (missing required fields) → 422 "
                    "     FastAPI validation error (standard Pydantic shape, NOT C-089 shape).\n"
                    "  8. POST /pricing/derive with a malformed body → 422 FastAPI validation error.\n\n"

                    "IDEMPOTENCY / INVARIANTS — must cover:\n"
                    "  9. POST /pricing/derive called twice with identical inputs returns identical "
                    "     'derived_price_paise' (pure function invariant — no side-effect drift).\n"
                    " 10. GET /pricing/bundle-cost-floor is read-only: assert the mocked service "
                    "     write methods (if any) are never called during the GET.\n"
                    " 11. Router prefix: assert all routes are reachable under /pricing/... (not /). "
                    "     Confirm that a bare GET / returns 404 to verify the mount point is correct.\n\n"

                    "CONSTITUTIONAL INVARIANTS — explicit assertions:\n"
                    " 12. On any C-089 violation response the key 'minimum_compliant_price_paise' MUST "
                    "     be present, MUST be an int, and MUST be strictly greater than the submitted price.\n"
                    " 13. No endpoint may return a 5xx for inputs that are structurally valid but "
                    "     constitutionally non-compliant — those must be 422 with the C-089 detail body.\n\n"

                    "FIXTURES / STRUCTURE:\n"
                    "  - @pytest.fixture providing an httpx.AsyncClient wired to the FastAPI 'app' "
                    "    imported from src/billing-engine/main.py (use 'from main import app' with "
                    "    sys.path manipulation or conftest path fixture).\n"
                    "  - Separate fixture that patches ThreadCatalogService to return a deterministic "
                    "    stub list so tests are hermetic.\n"
                    "  - Use parametrize for agent_type/bundle_tier combos in floor-cost tests.\n"
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
        ]
    },
        "WC027-02": {
        "subtasks": [
            SubTaskDef(
                id="WC027-02a",
                description="Implement IMarkupEngine.derive_bundle_cost_floor() and validate_price() with C-089 constitutional margin floor enforcement; implement POST/GET pricing endpoints with 422 rejection path and pricing_floor_log audit trail.",
                type="llm",
                depends_on=["WC027-01ba"],
                compile_gate="py_compile",
                service_dir="src/billing-engine",
                wc_task_id="WC027-02",
                stack="python",
                output_files=[
                    "src/billing-engine/markup/engine.py",
                    "src/billing-engine/pricing/routes.py",
                    "src/billing-engine/pricing/dto.py",
                    "tests/billing-engine/test_markup.py",
                ],
                inject_source_files=[
                    "src/billing-engine/skeleton/wbe_interfaces.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-02",
                },
                constitutional_check=(
                    "Implement IMarkupEngine.derive_bundle_cost_floor(agent_type, bundle_tier) → int.\n"
                    "  Layer 2 formula: Σ(marked_up_thread_cost × ration) + infra_share; reads bundle_profiles.cost_floor_paise (NOT recomputed).\n"
                    "  Price derivation uses margin-on-revenue: floor / (1 - margin/100).\n"
                    "Implement IMarkupEngine.validate_price(agent_type, bundle_tier, proposed_price_paise) → PriceValidation.\n"
                    "  C-089: BelowConstitutionalFloorError if margin < constitutional_minimum_margin_pct.\n"
                    "  MUST log to institutional.pricing_floor_log regardless of Allow/Deny outcome.\n"
                    "POST /pricing/validate:\n"
                    "  200 APPROVED path: returns PriceValidation{valid=True}, writes pricing_floor_log row.\n"
                    "  422 REJECTED path: raises BelowConstitutionalFloorError, body includes minimum_compliant_price_paise, writes pricing_floor_log row.\n"
                    "GET /pricing/thread-catalog: return shape per WC-027 spec (thread_type, marked_up_cost, ration).\n"
                    "Tests: cost_floor reads bundle_profiles.cost_floor_paise; margin-on-revenue formula validation; ≥90% line coverage.\n"
                    "Type annotations optional in scaffold — polish pass adds ANN001 compliance.\n"
                    "C-088, C-089, C-090, C-091: constitutional constraints enforced in validate_price and activate_subscription path."
                ),
                model_hint="auto",
                max_tokens=4500,
            ),
            SubTaskDef(
                id="WC027-02b",
                description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
                type="llm",
                depends_on=["WC027-02a"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC027-02",
                stack="python",
                output_files=[
                    "src/billing-engine/markup/engine.py",
                    "src/billing-engine/pricing/routes.py",
                    "src/billing-engine/pricing/dto.py",
                ],
                inject_source_files=[
                    "src/billing-engine/markup/engine.py",
                    "src/billing-engine/pricing/routes.py",
                    "src/billing-engine/pricing/dto.py",
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
                description="Pytest suite verifying cost_floor DB reads, derive_price margin-on-revenue formula, /pricing/validate 200/422 paths with pricing_floor_log writes, /pricing/thread-catalog response shape, and ≥90% line coverage.",
                type="llm",
                depends_on=["WC027-02b"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC027-02",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_engine.py",
                ],
                inject_source_files=[
                    "src/billing-engine/markup/engine.py",
                    "src/billing-engine/pricing/routes.py",
                    "src/billing-engine/pricing/dto.py",
                ],
                spec_sections={
                    "work-contracts/WC-027-wbe-s3-markup-engine.md": "WC027-02",
                },
                constitutional_check=(
                    "TEST PASS — write pytest tests against the provided implementation.\n"
                    "\n"
                    "# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-02\n"
                    "# Constitutional basis: C-043 (BudgetCeiling), C-048 (NonExploitation)\n"
                    "\n"
                    "COVERAGE TARGETS (≥90% line coverage on all three injected source files):\n"
                    "\n"
                    "1. HAPPY PATH — cost_floor reads from DB:\n"
                    "   - Mock DB query returning bundle_profiles row with cost_floor_paise=50000.\n"
                    "   - Assert engine.get_cost_floor('STANDARD') returns exactly 50000 (not recomputed).\n"
                    "   - Assert no arithmetic is applied to the raw DB value.\n"
                    "\n"
                    "2. FORMULA INVARIANT — derive_price uses margin-on-revenue:\n"
                    "   - Formula: price = floor / (1 - margin / 100)\n"
                    "   - Test with floor=50000, margin=20  → expect 62500.\n"
                    "   - Test with floor=100000, margin=25 → expect 133333 (round per impl).\n"
                    "   - Test with floor=0, margin=0       → expect 0 (zero floor edge case).\n"
                    "   - Test with margin=100              → expect ValueError / ZeroDivisionError.\n"
                    "   - Assert derive_price never reads bundle_profiles again (floor is passed in).\n"
                    "\n"
                    "3. POST /pricing/validate — 200 APPROVED path:\n"
                    "   - Mock get_cost_floor to return 50000, derive_price to return 62500.\n"
                    "   - POST body: proposed_price_paise=70000 (above floor price).\n"
                    "   - Assert response status 200.\n"
                    "   - Assert response JSON contains verdict='APPROVED'.\n"
                    "   - Assert pricing_floor_log row inserted with verdict='APPROVED',\n"
                    "     proposed_price_paise=70000, minimum_compliant_price_paise=62500.\n"
                    "   - Assert response JSON does NOT contain minimum_compliant_price_paise\n"
                    "     (field only present on REJECTED per spec).\n"
                    "\n"
                    "4. POST /pricing/validate — 422 REJECTED path:\n"
                    "   - Mock get_cost_floor to return 50000, derive_price to return 62500.\n"
                    "   - POST body: proposed_price_paise=40000 (below derived price).\n"
                    "   - Assert response status 422.\n"
                    "   - Assert response JSON contains verdict='REJECTED'.\n"
                    "   - Assert response JSON contains minimum_compliant_price_paise=62500.\n"
                    "   - Assert pricing_floor_log row inserted with verdict='REJECTED',\n"
                    "     proposed_price_paise=40000, minimum_compliant_price_paise=62500.\n"
                    "\n"
                    "5. IDEMPOTENCY — pricing_floor_log writes:\n"
                    "   - Call POST /pricing/validate twice with identical body.\n"
                    "   - Assert two separate log rows are written (log is append-only, not upsert).\n"
                    "   - Assert both rows share identical input fields but have distinct IDs/timestamps.\n"
                    "\n"
                    "6. GET /pricing/thread-catalog — response shape:\n"
                    "   - Mock DB returning 2 bundle profile rows.\n"
                    "   - Assert response status 200.\n"
                    "   - Assert response JSON is a list of objects.\n"
                    "   - Assert each object contains keys: bundle_tier, cost_floor_paise, margin_pct.\n"
                    "   - Assert no extra undocumented keys leak into the response.\n"
                    "\n"
                    "7. ERROR CASES:\n"
                    "   - POST /pricing/validate with missing required field → 422 validation error.\n"
                    "   - POST /pricing/validate with unknown bundle_tier → 404 or 422 (per impl).\n"
                    "   - DB unavailable during get_cost_floor → 503 or propagated exception.\n"
                    "   - margin=100 in derive_price → ZeroDivisionError is caught or raised cleanly.\n"
                    "\n"
                    "FIXTURE RULES:\n"
                    "   - Use pytest-asyncio for async route handlers.\n"
                    "   - Mock Redis with unittest.mock.AsyncMock or pytest-mock mocker.\n"
                    "   - Mock DB (asyncpg / SQLAlchemy session) with mocker.patch or AsyncMock.\n"
                    "   - Use httpx.AsyncClient with ASGITransport to test FastAPI routes in-process.\n"
                    "   - Do NOT spin up real Postgres or Redis — all external I/O must be mocked.\n"
                    "   - pricing_floor_log assertion: capture the mock DB execute/add call args.\n"
                    "\n"
                    "FILE HEADER (first two lines of test_engine.py must be):\n"
                    "   # Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-02\n"
                    "   # Constitutional basis: C-043 (BudgetCeiling), C-048 (NonExploitation)\n"
                    "\n"
                    "LINT: file is exempt from ANN per pyproject.toml per-file-ignores.\n"
                    "COVERAGE: run with pytest --cov=markup --cov=pricing --cov-fail-under=90.\n"
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
        ]
    },
    # ── GROOMER INJECTION POINT — groom_sprint.py injects new sprint handlers here ──
}


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
    print(f"  tasks_remaining   : {state.get('tasks_remaining', [])}")

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

    # ── Step 4: Determine tasks to run ────────────────────────────────────
    sprint = state.get("current_sprint", "")
    set_output("sprint", sprint)
    tasks = [force_task] if force_task else state.get("tasks_remaining", [])

    if not tasks:
        print("\nNo tasks remaining. Sprint may already be DONE.")
        set_output("result", "SKIPPED")
        return 0

    # Fresh-start signal: READY + no completed tasks means start from latest main,
    # not from any stale/diverged sprint branch left by prior interrupted runs.
    tasks_done_state = state.get("tasks_done", [])
    has_completed_tasks = bool(tasks_done_state)
    is_fresh_start = str(state.get("sprint_status", "")).upper() == "READY" and not has_completed_tasks

    # ── Step 5: Setup branch ──────────────────────────────────────────────
    branch = state.get("branch", f"ib/009/{sprint.lower()}")
    if not dry_run:
        git(["fetch", "origin", "main"], check=False)
        remote_check = git(["ls-remote", "--exit-code", "--heads", "origin", branch], check=False)

        if is_fresh_start:
            # Extra check: if the remote branch already has commits beyond main,
            # it contains work from a completed successful run — preserve it.
            branch_has_work = False
            if remote_check.returncode == 0:
                ahead = git(["rev-list", "--count", f"origin/main..origin/{branch}"], check=False)
                if ahead.returncode == 0 and int(ahead.stdout.strip() or "0") > 0:
                    branch_has_work = True
                    print(f"  Branch freshness guard: {branch} has {ahead.stdout.strip()} commit(s) ahead of main — preserving completed work")

            if branch_has_work:
                # Resume from the existing branch — don't discard completed work
                git(["checkout", branch], check=False)
                git(["pull", "origin", branch], check=False)
            else:
                print(f"  Branch freshness guard: rebuilding {branch} from latest origin/main")
                # Ensure we are not on the sprint branch before deleting/resetting it.
                current_branch = git(["branch", "--show-current"]).stdout.strip()
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
        update_sprint_state(
            sprint_status="IN_PROGRESS",
            last_attempt_utc=datetime.now(timezone.utc).isoformat(),
            current_task=tasks[0] if tasks else "",
        )
        git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
        diff = git(["diff", "--cached", "--quiet"], check=False)
        if diff.returncode != 0:
            git(["commit", "-m",
                 f"chore(pm): {sprint} execution started\n\nIB: IB-009\nConstitutional: C-059"])

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
                success = _execute_task_decomposed(
                    task, handler["subtasks"], _MONITOR_SIGNAL,
                    infra_error_tasks=infra_error_tasks,
                    dry_run=dry_run,
                    prior_completed=all_completed_subtask_ids,
                )
                # Accumulate this task's subtask IDs for the next task's chain
                all_completed_subtask_ids.extend([st.id for st in handler["subtasks"]])
            else:
                print(f"  ⚠️  TASK_NOT_IMPLEMENTED: {task} — unknown handler format")
                tasks_not_implemented.append(task)
                continue
            if success:
                tasks_done.append(task)
                # RC#2: Write tasks_done/tasks_remaining to PROJECT_STATE.md after each success.
                # MERGE with tasks_done_state (prior sessions) so cross-session completions are preserved.
                cumulative_done = sorted(set(tasks_done) | set(tasks_done_state))
                all_remaining = [t for t in state.get("tasks_remaining", []) if t not in cumulative_done]
                run([sys.executable, "scripts/sprint_state.py", "set-list", "tasks_done"] + cumulative_done)
                run([sys.executable, "scripts/sprint_state.py", "set-list", "tasks_remaining"] + all_remaining)
                print(f"  DONE: {task}")
            else:
                print(f"  FAILED: {task}")
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
        update_sprint_state(
            last_attempt_result="SUCCESS",
            consecutive_failures=0,
            consecutive_infra_failures=0,
            current_task="",
        )
    else:
        # P0 Fix 2: Separate infra vs spec failure counters.
        # Infrastructure failures (API timeout/rate-limit) do not count toward spec consecutive_failures.
        # This prevents premature AUTONOMOUS_HALT on transient infrastructure issues.
        if all_infra_errors:
            infra_fail_count = int(state.get("consecutive_infra_failures", "0") or "0") + 1
            update_sprint_state(
                last_attempt_result="INFRA_ERROR",
                consecutive_infra_failures=str(infra_fail_count),
                # consecutive_failures unchanged — infrastructure, not spec
            )
            print(f"  INFRA_ERROR: consecutive_infra_failures={infra_fail_count} (spec counter unchanged)")
        else:
            failures_new = failures + 1
            update_sprint_state(
                last_attempt_result="PARTIAL",
                consecutive_failures=str(failures_new),
                consecutive_infra_failures=0,
            )

    # Final commit: use cumulative tasks_done (merge with prior sessions)
    cumulative_final = sorted(set(tasks_done) | set(tasks_done_state))
    git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             f"chore(pm): {sprint} tasks done: {', '.join(cumulative_final)}\n\n"
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
