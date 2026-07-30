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
    runner/legacy_handlers.py — per-WC deterministic handlers (WC011–WC015)
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
import importlib.util as _ilu, sys as _sys
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
# Symbols are imported into this namespace so TASK_HANDLERS lambdas work unchanged.
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
from runner.legacy_handlers import (                                    # deterministic handlers
    execute_wc011_01, execute_wc011_02, execute_wc011_03,
    execute_wc011_04, execute_wc011_05, execute_wc011_07,
    execute_wc012_01,
    _generate_wc012_02a_evaluator_interfaces, _generate_wc012_02c_prep,
    _generate_wc012_03a_data_layer, _generate_wc012_04a_emergency_stop_entities,
    execute_wc013_01, execute_wc014_01, execute_wc015_01,
    _skip_schemathesis_gate,
)

# ── Sprint scaffold gate (C-069) ──────────────────────────────────────────────
# SCAFFOLD_TASKS: explicitly declared — never inferred from position.
# If WC012-01 fails, all downstream tasks cannot compile. The monitor uses this
# to distinguish CASCADE_PIPELINE_BUG from SPEC_GAP_GENUINE.
SCAFFOLD_TASKS: frozenset[str] = frozenset({
    "WC012-01", "WC013-01", "WC014-01", "WC015-01",
    "WC016-01", "WC017-01", "WC018-01",
})

TASK_HANDLERS = {
    "WC011-01": execute_wc011_01,
    "WC011-02": execute_wc011_02,
    "WC011-03": execute_wc011_03,
    "WC011-04": execute_wc011_04,
    "WC011-05": execute_wc011_05,
    "WC011-07": execute_wc011_07,
    # WC-012: Constitutional Engine skeleton
    # WC012-01 is DETERMINISTIC — copies reference files, no Claude call.
    # Root cause of 3 prior failures: Claude hallucinated API methods when asked to copy known-good files.
    "WC012-01": execute_wc012_01,
    "WC012-02": {
        # SIM-PL-002-WC012-02: PASS (2026-07-24) — C-086 gate satisfied
        # Decomposed from single lambda: 02a (interfaces, deterministic) → 02b (evaluators, LLM) → 02c (tests, LLM)
        # Lesson: single-call with 13 files hit max_tokens ceiling repeatedly.
        # Split: 02a writes stable contracts, 02b focuses on 5 business rules, 02c tests them.
        "subtasks": [
            SubTaskDef(
                id="WC012-02a",
                description="Evaluator interface contracts — EvaluationResult, EvaluationContext, IClaimEvaluator, EvaluatorRegistry (deterministic)",
                type="deterministic",
                depends_on=[],
                compile_gate="dotnet_build",
                template_fn=lambda: _generate_wc012_02a_evaluator_interfaces(),
                # output_files declared so Frozen Artifact Registry can freeze interface signatures
                # Required by §7.6: deterministic tasks must declare output_files for freezing
                output_files=[
                    "src/constitutional-engine/Evaluators/EvaluationResult.cs",
                    "src/constitutional-engine/Evaluators/EvaluationContext.cs",
                    "src/constitutional-engine/Evaluators/IClaimEvaluator.cs",
                    "src/constitutional-engine/Evaluators/EvaluatorRegistry.cs",
                ],
            ),
            SubTaskDef(
                id="WC012-02b",
                description="Constitutional claim evaluators — C041, C043, C048, C049, C062 + ValidateAction in ConstitutionalEngineService",
                type="llm",
                depends_on=["WC012-02a"],
                compile_gate="dotnet_build",
                wc_task_id="WC012-02",
                stack="dotnet",
                output_files=[
                    "src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs",
                    "src/constitutional-engine/Evaluators/C043BudgetCeilingEvaluator.cs",
                    "src/constitutional-engine/Evaluators/C048NonExploitationEvaluator.cs",
                    "src/constitutional-engine/Evaluators/C049HonestLimitationEvaluator.cs",
                    "src/constitutional-engine/Evaluators/C062AiSecurityEvaluator.cs",
                    "src/constitutional-engine/Services/ConstitutionalEngineService.cs",
                ],
                not_regenerate_from=[
                    "src/constitutional-engine/Evaluators/EvaluationResult.cs",
                    "src/constitutional-engine/Evaluators/EvaluationContext.cs",
                    "src/constitutional-engine/Evaluators/IClaimEvaluator.cs",
                    "src/constitutional-engine/Evaluators/EvaluatorRegistry.cs",
                ],
                spec_sections={
                    "architecture/reference/components/constitutional-engine.md": "§2 PAAS Boundary Validator",
                    "architecture/reference/ce-validate-action-evaluators.md": "full",
                    "architecture/reference/dotfiles/constitutional-engine.csproj": "full",
                },
                constitutional_check=(
                    "BEHAVIORAL RULES (delta — stack rules are injected automatically):\n"
                    "  ActionParameters is JSON-encoded — use ctx.GetParameter(\"key\") to extract values.\n"
                    "  ⛔ NEVER call ctx.ActionParameters.TryGetValue() — it is a string, not a Dictionary.\n"
                    "  TenantId: var tenantId = context.RequestHeaders.GetValue(\"x-tenant-id\") ?? \"\";\n"
                    "  Build context: var ctx = EvaluationContext.FromRequest(request, tenantId);\n"
                    "  EvaluatorRegistry: _registry.EvaluateAllAsync(ctx, ct) is the ONLY public method.\n"
                    "  ValidateAction: any DENY from any evaluator → return DENY. Default deny for unknown ContractId.\n"
                    "  ⛔ ValidationDecision values are Allow/Deny/Escalate — NOT Authorized, Denied, or Permit.\n"
                    "  Budget ceiling (C043): `bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;`\n"
                    "  ⛔ Do NOT use ?? on budget fields — ApprovedBudgetInrPaise/CurrentSpendInrPaise/ProposedSpendInrPaise are non-nullable long.\n"
                    "  ⛔ BudgetRemainingInrPaise does NOT exist on EvaluationContext — compute from the three budget fields above.\n"
                    "  Nullable numeric mapping rule: if any request field is `long?`, convert safely before assignment (`if (!x.HasValue) return DENY/ESCALATE; var v = x.Value;` or `var v = x.GetValueOrDefault(0L)` when zero-default is explicitly acceptable).\n"
                    "  ⛔ Never assign `long?` directly to a `long` local/field (prevents CS0266/CS8629).\n"
                    "IClaimEvaluator CONTRACT (do NOT invent members):\n"
                    "  ONLY two members: ClaimId (string property) + EvaluateAsync(ctx, ct).\n"
                    "  ⛔ Do NOT add ApplicableActionTypes, Priority, Weight, or any other property.\n"
                    "  ⛔ Do NOT use explicit interface declarations for invented members.\n"
                    "TASK BOUNDARIES:\n"
                    "  ConstitutionalEngineService.cs: EXTEND only — add ValidateAction impl. Do NOT rewrite existing methods.\n"
                    "  Do NOT call RecordEvidence — that is WC012-03.\n"
                    "  Do NOT generate test files — that is WC012-02c.\n"
                    "  Do NOT generate Data/ files — that is WC012-03.\n"
                    "  ⛔ SCOPE BOUNDARY: Do NOT reference ITemporalClient, ITemporalWorkflowHandle, or any Temporalio namespace.\n"
                    "  Temporal integration is WC012-04b scope — it is NOT part of ConstitutionalEngineService at this stage.\n"
                    "  Leave TriggerEmergencyStop as a stub that returns empty response."
                ),
                model_hint="reasoning",
                max_tokens=4000,
            ),
            SubTaskDef(
                id="WC012-02c-prep",
                description="FakeServerCallContext deterministic template — abstract property overrides",
                type="deterministic",
                depends_on=["WC012-02a", "WC012-02b"],
                compile_gate="dotnet_build",
                template_fn=lambda: _generate_wc012_02c_prep(),
            ),
            SubTaskDef(
                id="WC012-02c",
                description="CCT tests — CCT_EF01 evaluator unit tests (xUnit + Moq)",
                type="llm",
                depends_on=["WC012-02a", "WC012-02b", "WC012-02c-prep"],
                compile_gate="dotnet_build",
                spec_sections={
                    "tests/QA-STRATEGY.md": "§5.1 Unit Tests",
                },
                wc_task_id="WC012-02",
                output_files=[
                    "tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs",
                    "tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C043BudgetCeilingEvaluatorTests.cs",
                ],
                not_regenerate_from=["WC012-02a", "WC012-02b", "WC012-02c-prep"],
                stack="dotnet",
                constitutional_check=(
                    "MANDATORY FILE HEADER — copy these EXACT lines as the first lines of EVERY test file:\n"
                    "// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests\n"
                    "// constitutional_basis: C-041 (Tool Authorization), C-076 (Test Coverage)\n"
                    "using FluentAssertions;\n"
                    "using Waooaw.ConstitutionalEngine.Evaluators;\n"
                    "using Xunit;\n"
                    "// END MANDATORY HEADER\n\n"
                    "EVALUATOR API (from frozen signatures — use EXACTLY this):\n"
                    "  Signature:  Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)\n"
                    "  ⛔ Second parameter is CancellationToken — NOT ServerCallContext. Do NOT use FakeServerCallContext.\n"
                    "  Pass:       CancellationToken.None as second argument.\n\n"
                    "EvaluationContext constructor (positional record):\n"
                    "  new EvaluationContext(\n"
                    "      ContractId: \"test-contract-id\",\n"
                    "      ActionType: \"MCP_TOOL_CALL\",\n"
                    "      ActionParameters: \"{\\\"tool_name\\\": \\\"file_read\\\"}\",\n"
                    "      DecisionSpaceVersion: 1,\n"
                    "      TenantId: \"tenant-001\"\n"
                    "  )\n"
                    "  Use ctx.GetParameter(\"tool_name\") to read from ActionParameters — NOT .TryGetValue().\n\n"
                    "EvaluationResult properties:\n"
                    "  result.Verdict  — type: EvaluationVerdict  (Allow | Deny | Escalate)\n"
                    "  result.ClaimId  — string\n"
                    "  result.Reason   — string\n"
                    "  ⛔ NOT result.Decision — that is the gRPC proto type. Use result.Verdict.\n\n"
                    "Assertions:\n"
                    "  result.Verdict.Should().Be(EvaluationVerdict.Allow);\n"
                    "  result.Verdict.Should().Be(EvaluationVerdict.Deny);\n"
                    "  result.Verdict.Should().Be(EvaluationVerdict.Escalate);\n\n"
                    "xUnit [Fact] tests. Test EvaluateAsync with Allow/Deny/Escalate scenarios per claim. ≥90% coverage (C-076)."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    "WC012-03": {
        # SIM-PL-002-WC012-03: PASS (2026-07-24) — C-086 gate satisfied
        # Three sub-tasks in dependency order: Data layer → Implementation → Tests
        "subtasks": [
            SubTaskDef(
                id="WC012-03a",
                description="Data layer — EvidenceRecord entity + ConstitutionalDbContext (deterministic template)",
                type="deterministic",
                depends_on=[],
                compile_gate="dotnet_build",
                template_fn=lambda: _generate_wc012_03a_data_layer(),
            ),
            SubTaskDef(
                id="WC012-03b",
                description="RecordEvidence implementation — Evidence First write + idempotency",
                type="llm",
                depends_on=["WC012-03a"],
                compile_gate="dotnet_build",
                spec_sections={
                    "architecture/reference/components/constitutional-engine.md": "§1 Evidence First Enforcer",
                },
                wc_task_id="WC012-03",
                output_files=[
                    "src/constitutional-engine/Services/ConstitutionalEngineService.cs",
                ],
                not_regenerate_from=["WC012-03a", "WC012-02b"],  # 02b generated ValidateAction — preserve it
                stack="dotnet",
                constitutional_check=(
                    "Add RecordEvidence RPC to the existing service.\n"
                    "Write EvidenceRecord to DB BEFORE returning gRPC response (C-023).\n"
                    "Check ActionInstanceId uniqueness — return existing record_id if already written (C-085).\n"
                    "Append-only — no UPDATE or DELETE (C-007/C-027)."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC012-03c",
                description="CCT-EF-01 — Evidence First ordering test",
                type="llm",
                depends_on=["WC012-03a", "WC012-03b"],
                compile_gate="dotnet_build",
                spec_sections={
                    "tests/QA-STRATEGY.md": "§5.1 Unit Tests",
                },
                wc_task_id="WC012-03",
                output_files=[
                    "tests/constitutional-engine.Tests/Services/CCT_EF01_EvidenceFirstTests.cs",
                ],
                not_regenerate_from=["WC012-03a", "WC012-03b"],
                stack="dotnet",
                constitutional_check=(
                    "MANDATORY FILE HEADER — copy these EXACT lines as the first lines of the file:\n"
                    "// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests\n"
                    "// constitutional_basis: C-023 (Evidence First), C-007 (Append-Only), C-076 (Test Coverage)\n"
                    "using FluentAssertions;\n"
                    "using Microsoft.EntityFrameworkCore;\n"
                    "using Microsoft.Extensions.Logging.Abstractions;\n"
                    "using Waooaw.ConstitutionalEngine.Data;\n"
                    "using Waooaw.ConstitutionalEngine.Evaluators;\n"
                    "using Waooaw.ConstitutionalEngine.Grpc;\n"
                    "using Waooaw.ConstitutionalEngine.Services;\n"
                    "using Waooaw.ConstitutionalEngine.Tests.Evaluators;\n"
                    "using Xunit;\n"
                    "// END MANDATORY HEADER\n\n"
                    "Test: RecordEvidence writes DB record BEFORE returning gRPC response.\n"
                    "Use InMemoryDatabase — NOT Moq — for ConstitutionalDbContext:\n"
                    "  var opts = new DbContextOptionsBuilder<ConstitutionalDbContext>()\n"
                    "      .UseInMemoryDatabase(Guid.NewGuid().ToString()).Options;\n"
                    "  await using var db = new ConstitutionalDbContext(opts);\n"
                    "Use FakeServerCallContext.Create(tenantId) for server context.\n"
                    "Assert: db.EvidenceRecords.Count() == 1 after call. ≥90% coverage (C-076).\n"
                    "using FluentAssertions; for assertions. Namespace: Waooaw.ConstitutionalEngine.Services;"
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    "WC012-04": {
        # SIM-PL-002-WC012-04 required before this runs — see WC019-04
        # Sub-tasks: EmergencyStop entities (deterministic) → Handler impl → CCT-HO-01
        "subtasks": [
            SubTaskDef(
                id="WC012-04a",
                description="EmergencyStop entities — EmergencyStopEvent entity + DbContext (deterministic)",
                type="deterministic",
                depends_on=[],
                compile_gate="dotnet_build",
                template_fn=lambda: _generate_wc012_04a_emergency_stop_entities(),
            ),
            SubTaskDef(
                id="WC012-04b",
                description="TriggerEmergencyStop implementation — Evidence First + Temporal signal",
                type="llm",
                depends_on=["WC012-04a"],
                compile_gate="dotnet_build",
                spec_sections={
                    "architecture/reference/components/constitutional-engine.md": "§4 Emergency Stop Handler",
                },
                wc_task_id="WC012-04",
                output_files=[
                    "src/constitutional-engine/Services/ConstitutionalEngineService.cs",
                ],
                not_regenerate_from=["WC012-04a"],
                stack="dotnet",
                constitutional_check=(
                    "Implement TriggerEmergencyStop in the EXISTING ConstitutionalEngineService.cs stub.\n"
                    "Write EmergencyStopEvent to DB FIRST (C-023), THEN signal Temporal (ADR-018).\n"
                    "Use EmergencyStopDbContext injected via constructor DI.\n"
                    "Constructor compatibility rule: preserve existing constructor call sites in tests.\n"
                    "If adding ILogger<ConstitutionalEngineService>, make it optional (default null + NullLogger fallback)\n"
                    "or provide an overload so existing tests still compile unchanged.\n"
                    "Temporalio version in csproj is 0.1.0-beta1 — use that exact API."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC012-04c",
                description="CCT-HO-01 — Emergency Stop ≤250ms test",
                type="llm",
                depends_on=["WC012-04a", "WC012-04b"],
                compile_gate="dotnet_build",
                spec_sections={
                    "tests/QA-STRATEGY.md": "§5.1 Unit Tests",
                },
                wc_task_id="WC012-04",
                output_files=[
                    "tests/constitutional-engine.Tests/EmergencyStop/CCT_HO01_EmergencyStopLatencyTests.cs",
                ],
                not_regenerate_from=["WC012-04a", "WC012-04b"],
                stack="dotnet",
                constitutional_check=(
                    "Test: TriggerEmergencyStop completes in ≤250ms with mocked Temporalio client.\n"
                    "Use InMemoryDatabase — NOT Moq — for EmergencyStopDbContext:\n"
                    "  var opts = new DbContextOptionsBuilder<EmergencyStopDbContext>()\n"
                    "      .UseInMemoryDatabase(Guid.NewGuid().ToString()).Options;\n"
                    "  await using var db = new EmergencyStopDbContext(opts);\n"
                    "Mock ITemporalClient with Moq (it IS an interface — Moq works fine).\n"
                    "ALL constructor arguments MUST be positional — no named arguments after positional (CS1744).\n"
                    "NullLogger<T>.Instance for logger args — NOT new NullLogger<T>() (CS1503).\n"
                    "Measure elapsed time with Stopwatch. Assert elapsed.TotalMilliseconds ≤ 250.\n"
                    "using FluentAssertions; for assertions."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    # ══════════════════════════════════════════════════════════════════════════
    # WC-026 — WBE Wallet Engine (Python / FastAPI / SQLAlchemy 2.x)
    # src/billing-engine/wallet/ — buckets, reserve, release, renew (C-090)
    # ══════════════════════════════════════════════════════════════════════════
    "WC026-01": {
        "subtasks": [
            SubTaskDef(
                id="WC026-01a",
                description="SQLAlchemy models: CustomerWallet, WalletBucket, BucketReservation mapped to business.* tables",
                type="llm",
                depends_on=[],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC026-01",
                stack="python",
                output_files=[
                    "src/billing-engine/wallet/__init__.py",
                    "src/billing-engine/wallet/models.py",
                ],
                inject_source_files=[
                    "src/billing-engine/config.py",
                    "infrastructure/postgres/init/12-billing-engine.sql",
                ],
                spec_sections={
                    "architecture/reference/billing/billing-schema-updates.md": "full",
                    "work-contracts/WC-026-wbe-s2-wallet-engine.md": "full",
                },
                constitutional_check=(
                    "SQLAlchemy 2.x declarative: use Mapped[T] + mapped_column() syntax.\n"
                    "Table schema: __table_args__ = ({'schema': 'business'},) for all three models.\n"
                    "CustomerWallet → business.customer_wallets, WalletBucket → business.wallet_buckets, "
                    "BucketReservation → business.bucket_reservations.\n"
                    "UniqueConstraint on BucketReservation.idempotency_key (maps to DB unique index).\n"
                    "Use Optional[datetime] for nullable timestamp fields.\n"
                    "Flat import: no 'billing_engine' package prefix — conftest.py adds src/billing-engine/ to sys.path.\n"
                    "wallet/__init__.py must be empty (enables flat import: from wallet.models import ...)."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    "WC026-02": {
        "subtasks": [
            SubTaskDef(
                id="WC026-02a",
                description="Wallet service: get_balance, reserve (idempotent), release, activate_subscription, renew (C-090 grandfather)",
                type="llm",
                depends_on=["WC026-01a"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC026-02",
                stack="python",
                output_files=[
                    "src/billing-engine/wallet/service.py",
                    "src/billing-engine/wallet/exceptions.py",
                ],
                inject_source_files=[
                    "src/billing-engine/config.py",
                    "src/billing-engine/wallet/models.py",
                    "infrastructure/postgres/init/12-billing-engine.sql",
                ],
                not_regenerate_from=["WC026-01a"],
                spec_sections={
                    "architecture/reference/billing/wbe-component-spec.md": "full",
                    "work-contracts/WC-026-wbe-s2-wallet-engine.md": "full",
                    "adr/ADR-034-waooaw-billing-engine.md": "§ Wallet",
                },
                constitutional_check=(
                    "Async functions using SQLAlchemy AsyncSession (from sqlalchemy.ext.asyncio import AsyncSession).\n"
                    "reserve(wallet_id, thread_type, quantity, idempotency_key) must be IDEMPOTENT:\n"
                    "  catch IntegrityError from sqlalchemy.exc on idempotency_key unique violation → return existing row.\n"
                    "renew(wallet_id, subscription_tier) — C-090 grandfather pricing:\n"
                    "  if billing_profile.legacy_tier matches subscription_tier AND date.today() <= billing_profile.grandfather_until:\n"
                    "  → use legacy_price_inr; else → standard_price_inr.\n"
                    "All mutations call ce_stub.record_evidence(action, payload) — C-059 traceability.\n"
                    "wallet/exceptions.py: define InsufficientFundsError(Exception).\n"
                    "redis.set(key, value, ex=ttl) — NOT setex() (deprecated, treated as error by pyproject.toml).\n"
                    "Flat import: from wallet.models import CustomerWallet, WalletBucket, BucketReservation."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
        ]
    },
    "WC026-03": {
        "subtasks": [
            SubTaskDef(
                id="WC026-03a",
                description="Wallet Redis cache: get_balance_cached (<=50ms SLA), set_balance_cache, invalidate_wallet",
                type="llm",
                depends_on=["WC026-02a"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC026-03",
                stack="python",
                output_files=[
                    "src/billing-engine/wallet/cache.py",
                ],
                inject_source_files=[
                    "src/billing-engine/config.py",
                    "src/billing-engine/markup/thread_catalog.py",
                ],
                not_regenerate_from=["WC026-01a", "WC026-02a"],
                spec_sections={
                    "work-contracts/WC-026-wbe-s2-wallet-engine.md": "WC026-03",
                },
                constitutional_check=(
                    "Mirror the thread_catalog.py Redis pattern exactly (inject_source_files provided).\n"
                    "Cache key pattern: 'wallet:{wallet_id}:balance' — no collision with thread_catalog keys.\n"
                    "redis.set(key, json.dumps(data), ex=ttl) — NOT setex() (deprecated).\n"
                    "get_balance_cached(redis_client, wallet_id) → dict | None (cache miss returns None).\n"
                    "invalidate_wallet(redis_client, wallet_id) → deletes the key.\n"
                    "TTL from config.settings.thread_catalog_cache_ttl_seconds (same field, same config).\n"
                    "Use redis.asyncio.Redis type hint — async/await throughout."
                ),
                model_hint="auto",
                max_tokens=3000,
            ),
        ]
    },
    "WC026-04": {
        "subtasks": [
            SubTaskDef(
                id="WC026-04a",
                description="Wallet FastAPI router: GET /buckets/{wallet_id}, POST /reserve, POST /release; mount at /wallet in main.py",
                type="llm",
                depends_on=["WC026-02a", "WC026-03a"],
                compile_gate="ruff",
                service_dir="src/billing-engine",
                wc_task_id="WC026-04",
                stack="python",
                output_files=[
                    "src/billing-engine/wallet/router.py",
                ],
                inject_source_files=[
                    "src/billing-engine/main.py",
                    "src/billing-engine/markup/thread_catalog.py",
                    "src/billing-engine/wallet/service.py",
                    "src/billing-engine/wallet/exceptions.py",
                ],
                not_regenerate_from=["WC026-01a", "WC026-02a", "WC026-03a"],
                spec_sections={
                    "work-contracts/WC-026-wbe-s2-wallet-engine.md": "WC026-04",
                },
                constitutional_check=(
                    "Three endpoints mounted at /wallet prefix in main.py:\n"
                    "  GET /wallet/buckets/{wallet_id} → list[WalletBucketSchema]\n"
                    "  POST /wallet/reserve → ReserveRequest body → ReservationSchema | 422 InsufficientFunds\n"
                    "  POST /wallet/release → ReleaseRequest body → 200 OK\n"
                    "Pydantic v2 schemas: model_config = ConfigDict(from_attributes=True).\n"
                    "InsufficientFundsError → HTTPException(status_code=422, detail='insufficient_funds').\n"
                    "Dependency injection: AsyncSession + redis.asyncio.Redis via Depends().\n"
                    "Flat import in router: from wallet.service import ... (no package prefix).\n"
                    "Update main.py: add 'from wallet.router import router as wallet_router' + "
                    "'app.include_router(wallet_router, prefix=\"/wallet\")'.\n"
                    "⛔ Do NOT modify main.py imports for catalog_router — only add the wallet_router line."
                ),
                model_hint="auto",
                max_tokens=5000,
            ),
        ]
    },
    "WC026-05": {
        "subtasks": [
            SubTaskDef(
                id="WC026-05a",
                description="Wallet tests: cache layer, service idempotency, C-090 grandfather, router endpoints — >=90% coverage",
                type="llm",
                depends_on=["WC026-01a", "WC026-02a", "WC026-03a", "WC026-04a"],
                compile_gate="pytest",
                service_dir="tests/billing-engine",
                wc_task_id="WC026-05",
                stack="python",
                output_files=[
                    "tests/billing-engine/test_wallet.py",
                ],
                inject_source_files=[
                    "tests/billing-engine/conftest.py",
                    "tests/billing-engine/test_thread_catalog.py",
                    "src/billing-engine/wallet/models.py",
                    "src/billing-engine/wallet/service.py",
                    "src/billing-engine/wallet/cache.py",
                    "src/billing-engine/wallet/router.py",
                ],
                not_regenerate_from=["WC026-01a", "WC026-02a", "WC026-03a", "WC026-04a"],
                spec_sections={
                    "work-contracts/WC-026-wbe-s2-wallet-engine.md": "WC026-05",
                },
                constitutional_check=(
                    "Mirror test_thread_catalog.py structure exactly (inject_source_files provided).\n"
                    "Use fakeredis.aioredis.FakeRedis for all Redis interactions (already installed).\n"
                    "asyncio.run() for async pre-population in sync TestClient tests — NOT get_event_loop().\n"
                    "TestWalletCacheLayer (async, 5 tests): cache hit, miss, invalidation, TTL, concurrent reserve.\n"
                    "TestWalletServiceIdempotency (async, 4 tests): reserve same idempotency_key twice → same result;\n"
                    "  mock IntegrityError on second session.commit() call.\n"
                    "TestWalletHttpEndpoints (sync TestClient, 4 tests): GET buckets, POST reserve 200, "
                    "POST reserve 422 insufficient_funds, POST release 200.\n"
                    "TestC090GrandfatherInvariant (3 tests): freeze datetime.date.today with unittest.mock.patch;\n"
                    "  legacy_price when grandfather_until in future; standard_price when expired.\n"
                    "conftest.py already adds src/billing-engine/ to sys.path — all imports are flat.\n"
                    "redis.set(key, value, ex=ttl) — NOT setex() (deprecated, filterwarnings=error).\n"
                    "⛔ Do NOT modify conftest.py."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
        ]
    },
    # ── GROOMER INJECTION POINT — groom_sprint.py injects new sprint handlers here ──
    # ══════════════════════════════════════════════════════════════════════════
    # WC-013 — Business Platform (.NET 9 REST)
    # ══════════════════════════════════════════════════════════════════════════
    "WC013-01": execute_wc013_01,
    "WC013-02": {
        # JWT middleware + tenant isolation (RLS). Sub-tasks: impl → tests.
        "subtasks": [
            SubTaskDef(
                id="WC013-02a",
                description="JWT middleware + RLS tenant isolation — Keycloak bearer + SET LOCAL",
                type="llm",
                depends_on=[],
                compile_gate="dotnet_build",
                service_dir="src/business-platform",
                wc_task_id="WC013-02",
                stack="dotnet",
                output_files=[
                    "src/business-platform/Infrastructure/TenantIsolationMiddleware.cs",
                    "src/business-platform/Program.cs",
                ],
                spec_sections={
                    "architecture/reference/components/business-platform.md": "§ Tenant Isolation",
                    "adr/ADR-003-jwt-claims-multi-tenancy.md": "full",
                },
                constitutional_check=(
                    "JWT: AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer().\n"
                    "Extract tenant_id claim from JWT and call: SET LOCAL app.current_tenant_id = '{id}'\n"
                    "via IDbContextInterceptor or middleware before any DB query (C-026).\n"
                    "app.UseAuthentication(); app.UseAuthorization(); must be in Program.cs.\n"
                    "Invalid token → 401. Missing tenant_id claim → 403.\n"
                    "⛔ Do NOT hardcode tenant IDs — always read from JWT claim."
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
            SubTaskDef(
                id="WC013-02b",
                description="CCT-MT-01 — cross-tenant isolation unit test",
                type="llm",
                depends_on=["WC013-02a"],
                compile_gate="dotnet_build",
                service_dir="src/business-platform",
                wc_task_id="WC013-02",
                stack="dotnet",
                output_files=[
                    "tests/business-platform.Tests/Infrastructure/CCT_MT01_TenantIsolationTests.cs",
                ],
                not_regenerate_from=["WC013-02a"],
                constitutional_check=(
                    "Test: requests with tenant A token cannot see tenant B data (CCT-MT-01).\n"
                    "Use WebApplicationFactory<Program> from Microsoft.AspNetCore.Mvc.Testing.\n"
                    "using FluentAssertions; for assertions. ≥90% coverage (C-076)."
                ),
                model_hint="reasoning",
                max_tokens=4000,
            ),
        ]
    },
    "WC013-03": {
        # Registration + Hire endpoints. Sub-tasks: impl files → tests.
        "subtasks": [
            SubTaskDef(
                id="WC013-03a",
                description="POST /api/customers + POST /api/agents/hire — calls CE.ValidateAction",
                type="llm",
                depends_on=["WC013-02a"],
                compile_gate="dotnet_build",
                service_dir="src/business-platform",
                wc_task_id="WC013-03",
                stack="dotnet",
                output_files=[
                    "src/business-platform/Controllers/CustomersController.cs",
                    "src/business-platform/Controllers/AgentsController.cs",
                    "src/business-platform/Services/EmploymentService.cs",
                ],
                not_regenerate_from=["WC013-02a"],
                spec_sections={
                    "architecture/reference/api-specs/business-platform.openapi.yaml": "POST /api/customers, POST /api/agents/hire",
                    "architecture/reference/components/business-platform.md": "§1 Employment Manager",
                },
                constitutional_check=(
                    "EVERY endpoint must call CE.ValidateAction via gRPC BEFORE executing (C-023).\n"
                    "CE client: var channel = GrpcChannel.ForAddress(config['ConstitutionalEngine:GrpcUrl']);\n"
                    "           var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);\n"
                    "C-038: Hire endpoint must populate pro_rata_billing_start_date on contract creation.\n"
                    "⛔ Do NOT call CE inside a DB transaction — CE call is pre-condition, not part of TX.\n"
                    "Namespace: Waooaw.BusinessPlatform.Controllers and Waooaw.BusinessPlatform.Services.\n"
                    "⛔ CS0019 CE gRPC ENUM: ValidateActionResponse.Decision is type ValidationDecision (NOT PolicyDecision).\n"
                    "  CORRECT: ceResponse.Decision != ValidationDecision.Allow  OR  ceResponse.Decision == ValidationDecision.Deny\n"
                    "  WRONG:   ceResponse.Decision != PolicyDecision.Permit  ← CS0019 (type mismatch)\n"
                    "  WRONG:   ceResponse.Decision != PolicyDecision.Allow    ← CS0019 (type mismatch)\n"
                    "  PolicyDecision is ONLY used with EvaluatePolicyResponse.Decision (different RPC, different type)."
                ),
                model_hint="reasoning",
                max_tokens=8000,
            ),
            SubTaskDef(
                id="WC013-03b",
                description="Unit tests for Registration + Hire endpoints — ≥90% coverage",
                type="llm",
                depends_on=["WC013-03a"],
                compile_gate="dotnet_build",
                service_dir="src/business-platform",
                wc_task_id="WC013-03",
                stack="dotnet",
                output_files=[
                    "tests/business-platform.Tests/Controllers/CustomersControllerTests.cs",
                    "tests/business-platform.Tests/Controllers/AgentsControllerTests.cs",
                ],
                not_regenerate_from=["WC013-02a", "WC013-03a"],
                constitutional_check=(
                    "Mock CE gRPC client with Moq (IConstitutionalService — it IS an interface).\n"
                    "Use InMemoryDatabase for EF Core context (NOT Moq for DbContext).\n"
                    "Test: CE.ValidateAction called before any DB write.\n"
                    "using FluentAssertions; for assertions. ≥90% coverage (C-076)."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    "WC013-04": {
        # Schemathesis contract test — requires running service, CI-deferred.
        "subtasks": [
            SubTaskDef(
                id="WC013-04a",
                description="Schemathesis contract test — CI gate (deferred to docker-compose run)",
                type="deterministic",
                depends_on=["WC013-03a"],
                compile_gate="dotnet_build",
                service_dir="src/business-platform",
                template_fn=lambda: _skip_schemathesis_gate(),
            ),
        ]
    },
    # ══════════════════════════════════════════════════════════════════════════
    # WC-014 — Professional Runtime (Python 3.12 FastAPI + Temporal)
    # ══════════════════════════════════════════════════════════════════════════
    "WC014-01": execute_wc014_01,
    "WC014-02": {
        # Emergency Stop WebSocket + CCT-HO-02
        "subtasks": [
            SubTaskDef(
                id="WC014-02a",
                description="Emergency Stop WebSocket → Temporal HALT signal ≤250ms",
                type="llm",
                depends_on=[],
                compile_gate="ruff",
                service_dir="src/professional-runtime",
                wc_task_id="WC014-02",
                stack="python",
                output_files=[
                    "src/professional-runtime/routers/emergency_stop.py",
                ],
                spec_sections={
                    "architecture/reference/components/professional-runtime.md": "§ Emergency Stop",
                    "adr/ADR-018-emergency-stop-temporal-signal.md": "full",
                    "architecture/reference/api-specs/emergency-stop-ws.md": "full",
                },
                constitutional_check=(
                    "@router.websocket('/sessions/{session_id}/stop')\n"
                    "Use temporalio SDK (version 1.7.1 — from requirements.txt).\n"
                    "Signal HALT to Temporal workflow: await handle.signal(HALT_SIGNAL_NAME)\n"
                    "⛔ NO I/O between WebSocket accept and signal send (C-001 ≤250ms).\n"
                    "⛔ Do NOT import 'temporal' or 'temporal_sdk' — import 'temporalio' only.\n"
                    "Fire-and-forget: await websocket.send_json({'status': 'stopping'}) then close."
                ),
                model_hint="reasoning",
                max_tokens=4000,
            ),
            SubTaskDef(
                id="WC014-02b",
                description="CCT-HO-02 — Emergency Stop latency test (mock Temporal)",
                type="llm",
                depends_on=["WC014-02a"],
                compile_gate="ruff",
                service_dir="src/professional-runtime",
                wc_task_id="WC014-02",
                stack="python",
                output_files=[
                    "tests/professional-runtime/test_emergency_stop.py",
                ],
                not_regenerate_from=["WC014-02a"],
                constitutional_check=(
                    "Mock temporalio client with pytest-mock/unittest.mock.\n"
                    "Use httpx.AsyncClient + starlette.testclient for WebSocket testing.\n"
                    "@pytest.mark.asyncio for async tests.\n"
                    "Assert: signal sent within 250ms (time.perf_counter measurement).\n"
                    "⛔ Do NOT start a real Temporal server in tests."
                ),
                model_hint="reasoning",
                max_tokens=4000,
            ),
        ]
    },
    "WC014-03": {
        # PAAS session lifecycle + unit tests
        "subtasks": [
            SubTaskDef(
                id="WC014-03a",
                description="PAAS session lifecycle — start/resume/terminate Temporal workflows",
                type="llm",
                depends_on=["WC014-02a"],
                compile_gate="ruff",
                service_dir="src/professional-runtime",
                wc_task_id="WC014-03",
                stack="python",
                output_files=[
                    "src/professional-runtime/workflows/paas_workflow.py",
                    "src/professional-runtime/routers/sessions.py",
                ],
                not_regenerate_from=["WC014-02a"],
                spec_sections={
                    "architecture/reference/components/professional-runtime.md": "§ PAAS Session Lifecycle",
                    "adr/ADR-005-paas-session-isolation.md": "full",
                },
                constitutional_check=(
                    "C-025: ALL professional execution runs as Temporal workflow — never direct call.\n"
                    "Each session = one Temporal workflow (workflow_id = session_id for idempotency).\n"
                    "Session isolation: no shared state between workflows (C-025).\n"
                    "POST /sessions → start_workflow(). GET /sessions/{id} → describe workflow state.\n"
                    "DELETE /sessions/{id} → signal TERMINATE to workflow.\n"
                    "⛔ Do NOT use temporalio.workflow.execute_activity inside the router — only inside workflow."
                ),
                model_hint="reasoning",
                max_tokens=6000,
            ),
            SubTaskDef(
                id="WC014-03b",
                description="Unit tests for PAAS session lifecycle — ≥90% coverage",
                type="llm",
                depends_on=["WC014-03a"],
                compile_gate="ruff",   # pytest deferred: hyphenated dir can't be imported as Python pkg
                service_dir="tests/professional-runtime",
                wc_task_id="WC014-03",
                stack="python",
                output_files=[
                    "tests/professional-runtime/test_sessions.py",
                ],
                not_regenerate_from=["WC014-02a", "WC014-03a"],
                constitutional_check=(
                    "Mock temporalio client. @pytest.mark.asyncio for async tests.\n"
                    "Test: start_workflow called on POST /sessions.\n"
                    "Test: cross-session isolation — workflow IDs are unique per session.\n"
                    "pytest-cov: ≥90% coverage required (C-076)."
                ),
                model_hint="reasoning",
                max_tokens=4000,
            ),
        ]
    },
    "WC014-04": {
        # AI Execution Loop stub (5 Temporal activities)
        "subtasks": [
            SubTaskDef(
                id="WC014-04a",
                description="AI Execution Loop — SENSE/RETRIEVE/REASON/ACT/RECORD Temporal activities",
                type="llm",
                depends_on=["WC014-03a"],
                compile_gate="ruff",
                service_dir="src/professional-runtime",
                wc_task_id="WC014-04",
                stack="python",
                output_files=[
                    "src/professional-runtime/activities/execution_loop.py",
                ],
                not_regenerate_from=["WC014-02a", "WC014-03a"],
                spec_sections={
                    "architecture/reference/components/professional-runtime.md": "§ AI Execution Loop",
                },
                constitutional_check=(
                    "5 @activity.defn functions: sense, retrieve, reason, act, record.\n"
                    "C-047: all 5 must execute in sequence. RECORD must always run (C-023).\n"
                    "Activities are stubs — return placeholder dicts. Real AI calls in WC015.\n"
                    "⛔ No LLM calls here — that is AI Runtime's responsibility.\n"
                    "⛔ Do NOT skip RECORD on error — wrap in try/finally."
                ),
                model_hint="auto",
                max_tokens=4000,
            ),
        ]
    },
    # ══════════════════════════════════════════════════════════════════════════
    # WC-015 — AI Runtime (Python 3.12 FastAPI + PSE)
    # ══════════════════════════════════════════════════════════════════════════
    "WC015-01": execute_wc015_01,
    "WC015-02": {
        # PSE routing + LLM dispatch
        "subtasks": [
            SubTaskDef(
                id="WC015-02a",
                description="Provider Selection Engine — PSE-R01 to PSE-R08 routing rules",
                type="llm",
                depends_on=[],
                compile_gate="ruff",
                service_dir="src/ai-runtime",
                wc_task_id="WC015-02",
                stack="python",
                output_files=[
                    "src/ai-runtime/pse/router.py",
                ],
                spec_sections={
                    "adr/ADR-029-multi-provider-llm-strategy.md": "full",
                    "adr/ADR-024-token-economy-model-tier-routing.md": "full",
                },
                constitutional_check=(
                    "PSE routes to LlmTier enum (from pse/tiers.py — DO NOT redefine).\n"
                    "PSE-R01: task_complexity=simple → LOCAL (Ollama, ₹0). \n"
                    "PSE-R02: task_complexity=medium + language=indic → MID (Sarvam).\n"
                    "PSE-R03: task_complexity=complex → FRONTIER (Gemini/Anthropic).\n"
                    "C-051: ≥66% of calls must route to LOCAL or MID.\n"
                    "⛔ NEVER call 'import vertexai' — use 'from google.cloud import aiplatform'."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
            SubTaskDef(
                id="WC015-02b",
                description="LLM dispatch — Ollama (LOCAL) + Sarvam (MID) providers",
                type="llm",
                depends_on=["WC015-02a"],
                compile_gate="ruff",
                service_dir="src/ai-runtime",
                wc_task_id="WC015-02",
                stack="python",
                output_files=[
                    "src/ai-runtime/providers/ollama_provider.py",
                    "src/ai-runtime/providers/sarvam_provider.py",
                ],
                not_regenerate_from=["WC015-02a"],
                spec_sections={
                    "adr/ADR-029-multi-provider-llm-strategy.md": "§ OllamaProvider, SarvamProvider",
                },
                constitutional_check=(
                    "OllamaProvider: POST http://ollama:11434/api/generate (docker-compose service name).\n"
                    "SarvamProvider: POST https://api.sarvam.ai/v1/chat/completions via httpx.\n"
                    "⛔ Sarvam has NO Python SDK — use httpx directly (see requirements.txt note).\n"
                    "C-063: no PII in prompt. ADR-028: prompt content never logged.\n"
                    "Record dispatch to provider_dispatch_events table after each call."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    "WC015-03": {
        # RAG retrieval stub
        "subtasks": [
            SubTaskDef(
                id="WC015-03a",
                description="RAG retrieval — pgvector similarity search (top-3 chunks)",
                type="llm",
                depends_on=["WC015-02a"],
                compile_gate="ruff",
                service_dir="src/ai-runtime",
                wc_task_id="WC015-03",
                stack="python",
                output_files=[
                    "src/ai-runtime/rag/retriever.py",
                ],
                not_regenerate_from=["WC015-02a", "WC015-02b"],
                spec_sections={
                    "adr/ADR-019-rag-architecture.md": "full",
                },
                constitutional_check=(
                    "pgvector: from pgvector.asyncpg import register_vector.\n"
                    "Query: SELECT content FROM professional.agent_prompts ORDER BY embedding <=> $1 LIMIT 3.\n"
                    "Embeddings via AI4Bharat IndicBERT: transformers.pipeline('feature-extraction', model='ai4bharat/indic-bert').\n"
                    "⛔ IndicBERT is loaded via HuggingFace transformers — do NOT 'pip install ai4bharat'.\n"
                    "Return List[str] of top-3 chunks. Never include raw embeddings in response."
                ),
                model_hint="reasoning",
                max_tokens=4000,
            ),
        ]
    },
    "WC015-04": {
        # Prompt injection defence + CCT-PI-01
        "subtasks": [
            SubTaskDef(
                id="WC015-04a",
                description="Prompt injection defence — 50-attack test suite (CCT-PI-01)",
                type="llm",
                depends_on=["WC015-02a"],
                compile_gate="ruff",
                service_dir="src/ai-runtime",
                wc_task_id="WC015-04",
                stack="python",
                output_files=[
                    "src/ai-runtime/pii/injection_guard.py",
                    "tests/ai-runtime/test_injection_guard.py",
                ],
                not_regenerate_from=["WC015-02a", "WC015-02b", "WC015-03a"],
                spec_sections={
                    "architecture/reference/components/ai-runtime.md": "§ Prompt Injection Defence",
                },
                constitutional_check=(
                    "C-062: Decision Space cannot be bypassed by conversation input.\n"
                    "Implement InjectionGuard.scan(prompt: str) → bool (True = safe, False = blocked).\n"
                    "Attack patterns in tests/conftest.py — import and use them in the test.\n"
                    "CCT-PI-01: all 50 attack patterns must be BLOCKED (100% block rate).\n"
                    "@pytest.mark.asyncio. Assert all 50 attacks return False from scan()."
                ),
                model_hint="reasoning",
                max_tokens=5000,
            ),
        ]
    },
    "WC015-05": {
        # PSE routing tests ≥90% coverage
        "subtasks": [
            SubTaskDef(
                id="WC015-05a",
                description="PSE routing unit tests — PSE-R01 to PSE-R08 + ≥90% coverage",
                type="llm",
                depends_on=["WC015-02a", "WC015-02b", "WC015-03a", "WC015-04a"],
                compile_gate="ruff",  # pytest not used: runner lacks asyncpg/httpx → ImportError in stderr (empty error). ruff catches syntax/style issues reliably.
                service_dir="tests/ai-runtime",
                wc_task_id="WC015-05",
                stack="python",
                output_files=[
                    "tests/ai-runtime/test_pse_routing.py",
                ],
                not_regenerate_from=["WC015-02a", "WC015-02b"],
                constitutional_check=(
                    "Test every PSE routing rule (PSE-R01 to PSE-R08) with a [Fact] equivalent.\n"
                    "@pytest.mark.parametrize for routing rules.\n"
                    "Mock Ollama/Sarvam providers — no real HTTP calls in unit tests.\n"
                    "pytest-cov: ≥90% coverage on pse/router.py (C-076)."
                ),
                model_hint="auto",
                max_tokens=4000,
            ),
        ]
    },
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
                import importlib.util as _ilu, sys as _sys
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
