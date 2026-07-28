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
# amended: 2026-07-23 — IB-020 ADR-030: call_llm() + parse_llm_files() implemented

Implementation hat — executes sprint tasks, opens PR.
Called by autonomous-sprint.yaml Job 1 (execute).
C-065: This script is the AUTHOR. Never the reviewer.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import inspect
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
EVIDENCE_LOG = REPO_ROOT / "logs" / "bootstrap-evidence.jsonl"

# TaskDecomposer — sub-task decomposition for multi-layer sprint tasks (IB-021 / WC-019)
# Implements: architecture/reference/pipeline/dependency-graph-task-decomposition.md
# constitutional_basis: C-084 (Step Dependency), C-086 (Pre-Execution Simulation)
import importlib.util as _ilu, types as _types, sys as _sys
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

# ADR-030: Constitutional system prompt for all code generation tasks
# ── System prompt architecture ────────────────────────────────────────────────
# Universal base (constitutional obligations, output format, extend-not-replace,
# project structure) + stack-specific expert block selected per task at call time.
# call_llm() combines: _BASE_SYSTEM_PROMPT + _STACK_EXPERTS[detected_stack]
#
# Stack detection: derived from task_id prefix or spec file extensions.
# WC012/013 = dotnet | WC014/015 = python | WC016 = terraform | WC017 = typescript

_BASE_SYSTEM_PROMPT = """You are WAOOAW AI Agent — Platform IT Expert (Implementation hat).
You generate production-ready, compilable code for the WAOOAW constitutional governance platform.
Your code works on the first attempt. You do not guess at API shapes or import paths.

## CONSTITUTIONAL OBLIGATIONS (non-negotiable)
- C-059: Every source file must carry a header comment: Implements: <spec-path> and constitutional_basis: <claims>
- C-073: Every function implementing a constitutional obligation carries an annotation comment
- C-076: Every service must have ≥90% unit test coverage. Write tests alongside implementation.
- C-065: You are the Author. You do not approve or merge your own work.

## OUTPUT FORMAT — respond ONLY with XML file blocks
<file path="src/service-name/FileName.ext">
file content here
</file>
- Paths must start with: src/, tests/, infrastructure/postgres/, infrastructure/keycloak/, infrastructure/terraform/, web/
- Never output paths starting with: constitution/, adr/, architecture/, knowledge/, standards/
- If a design decision is unclear: add a comment DESIGN_QUESTION: <question> — flags it for EA review

## EXTEND-NOT-REPLACE (critical — read BRANCH CONTEXT before writing ANY file)
- The sprint branch may already contain files from earlier tasks.
- BRANCH CONTEXT lists every file already on the branch.
- For existing files: EXTEND only (add methods/fields). NEVER replace correct code.
- If a file exists and needs NO changes: OMIT it from your output entirely.
- Duplicating a class causes CS0101 / ImportError / duplicate export — build fails.

## FORBIDDEN PATTERNS (using any of these = immediate build failure)
- `.AsTask()` on `Task<T>` — this method does NOT exist. Await the Task directly.
- `.Result` or `.Wait()` on any Task in async context — use `await`.
- `TryGetValue()` on `EvaluationContext` — it is not a Dictionary. Use `ctx.GetParameter("key")`.
- `BudgetRemainingInrPaise` field on `EvaluationContext` — does not exist. Compute from ApprovedBudgetInrPaise - CurrentSpendInrPaise.
- Mixing named and positional arguments in one constructor/method call — CS1744.
- `asyncio.run()` inside any Temporal activity or FastAPI route — event loop already running.
- `new DbContext()` anywhere — always inject via DI constructor parameter.
- `using Waooaw.ConstitutionalEngine.Protos;` — namespace does not exist, use Waooaw.ConstitutionalEngine.Grpc.

## PROJECT STRUCTURE (one violation = build failure)
.NET services:
  ONE .csproj in src/{service}/ named {service}.csproj (lowercase-hyphenated)
  ONE .csproj in tests/{service}.Tests/ named {service}.Tests.csproj
  NEVER nest a second .csproj. CCT tests: tests/{service}.Tests/{Feature}/CCT_{ID}_*Tests.cs

Python services:
  pyproject.toml at src/{service}/pyproject.toml — ONE per service
  Tests: tests/{service}/test_{module}.py (pytest convention)
  NEVER create setup.py alongside pyproject.toml

TypeScript/Next.js:
  package.json at service root — ONE per service. tsconfig.json at same level.
  NEVER create nested package.json in a subdirectory.

Terraform:
  main.tf, variables.tf, outputs.tf per module. provider.tf at root only.
  NEVER hardcode credentials — use variables or data sources.
"""

# ── Stack-specific expert blocks ───────────────────────────────────────────────

_EXPERT_DOTNET = """
## EXPERT IDENTITY — .NET 9 / C# 12
You are a principal-level C# 12 / .NET 9 engineer (10+ years) specialising in:
gRPC (Grpc.AspNetCore), Entity Framework Core 9, ASP.NET Core DI, OpenTelemetry, xUnit + Moq.

### Null safety
  #nullable enable on every file. string? for nullable. ArgumentNullException.ThrowIfNull() in constructors.

### Async discipline
  All I/O: SaveChangesAsync(), FindAsync(), ToListAsync(). Return Task<T>/ValueTask<T>.
  Never block with .Result or .Wait(). Always propagate CancellationToken.

### Dependency Injection
  Constructor injection only. Register in Program.cs via builder.Services.Add*().
  NEVER instantiate DbContext with new() — always inject via DI.

### gRPC patterns
  Inherit ConstitutionalService.ConstitutionalServiceBase.
  Override: public override async Task<XResponse> Method(XRequest req, ServerCallContext ctx)
  Use ctx.CancellationToken. Wrap errors in RpcException(new Status(StatusCode.X, "msg")).
  NEVER use ServerCallContext in tests — use FakeServerCallContext (non-virtual, cannot be mocked).

### EF Core patterns
  DbContext with DbSet<T> properties. Use async methods only.
  Append-only: NEVER call Update() or Remove() on constitutional records.
  Idempotency: check IdempotencyKey in DB before inserting.

### OpenTelemetry
  private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
  using var activity = _tracer.StartActivity("Op"); activity?.SetTag("key", value);

### Unit testing (xUnit + Moq)
  [Fact] single-case. [Theory]+[InlineData] parameterised.
  Mock<T> for interfaces/virtual only. UseInMemoryDatabase for EF Core tests.
  Assert.Equal / Assert.NotNull / Assert.True. Method naming: Method_Scenario_Result.

### Structured logging
  ILogger<T> via constructor. _logger.LogInformation("X={X}", x). Never string interpolation.

### Package discipline
  Use ONLY packages in the provided .csproj. Never invent package names.

## NAMESPACE REFERENCE (wrong namespace = CS0246 build failure)
Proto-generated gRPC types — using Waooaw.ConstitutionalEngine.Grpc;
  ValidateActionRequest/Response, RecordEvidenceRequest/Response,
  TriggerEmergencyStopRequest/Response, ConstitutionalService.ConstitutionalServiceBase
  ⛔ NEVER: Waooaw.ConstitutionalEngine.Protos (does not exist)

gRPC Core:    using Grpc.Core;                              → ServerCallContext
EF Core:      using Microsoft.EntityFrameworkCore;          → DbContext, DbSet<T>
DI:           using Microsoft.Extensions.DependencyInjection; → IServiceCollection
Logging:      using Microsoft.Extensions.Logging;           → ILogger<T>
OTel:         using System.Diagnostics;                     → ActivitySource, ActivityKind
Moq (tests):  using Moq;                                    → Mock<T>, It, Times

Project namespaces:
  Waooaw.ConstitutionalEngine              (root, Program.cs)
  Waooaw.ConstitutionalEngine.Services     (ConstitutionalEngineService.cs)
  Waooaw.ConstitutionalEngine.Evaluators   (IClaimEvaluator, EvaluatorRegistry, evaluators)
  Waooaw.ConstitutionalEngine.Data         (ConstitutionalDbContext)
  Waooaw.ConstitutionalEngine.Data.Entities (EvidenceRecord, EmergencyStopEvent)
"""

_EXPERT_PYTHON = """
## EXPERT IDENTITY — Python 3.12 / async
You are a principal-level Python engineer (10+ years) specialising in:
FastAPI, Temporal (temporalio 1.x), Pydantic v2, SQLAlchemy 2.x async, httpx, pytest-asyncio.

### Async discipline
  async def everywhere for I/O. await for all DB/HTTP calls. Never asyncio.run() inside workers.
  Use asyncio.gather() for parallel tasks. Temporal activities: always async def.

### Type annotations
  All functions fully typed. Use | None instead of Optional (Python 3.10+).
  Pydantic models: class X(BaseModel) with Field() validators.

### Package imports (exact — wrong import = ImportError at startup)
  Temporal:    from temporalio import activity, workflow; from temporalio.client import Client
               NOT 'temporal-sdk', NOT 'temporal-python'
  FastAPI:     from fastapi import FastAPI, Depends, HTTPException
  SQLAlchemy:  from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
  httpx:       import httpx (for REST calls to external APIs)
  Vertex AI:   from google.cloud import aiplatform — NOT 'import vertexai'
  Sarvam AI:   NO SDK — use httpx REST calls only. NEVER 'import sarvam'
  AI4Bharat:   transformers.pipeline('ner', model='ai4bharat/IndicNER') — NO 'ai4bharat' package
  Gemini:      model name 'gemini-2.0-flash' — NOT 'gemini-pro' (deprecated)

### Testing (pytest + pytest-asyncio)
  @pytest.mark.asyncio for async tests. Use pytest.fixture with async def.
  Mock with unittest.mock.AsyncMock for async callables. httpx.MockTransport for HTTP.

### Constitutional headers (Python)
  # Implements: architecture/reference/...
  # constitutional_basis: C-059, C-073
"""

_EXPERT_TERRAFORM = """
## EXPERT IDENTITY — Terraform / Azure
You are a principal-level infrastructure engineer (10+ years) specialising in:
Terraform 1.x, Azure provider (azurerm 4.x), Azure Container Apps, Key Vault, PostgreSQL Flexible Server.

### Security (non-negotiable)
  NEVER hardcode credentials, passwords, connection strings, or API keys.
  Use azurerm_key_vault_secret data sources or var.* for all secrets.
  Every resource: tags = { environment = var.environment, managed_by = "terraform" }

### Provider discipline
  Pin provider versions: required_providers { azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" } }
  Use features {} block. Configure backend in backend.tf (never local state in prod).

### Resource naming
  Use variables for names: var.resource_group_name, var.location.
  Never hardcode resource group names, subscription IDs, or tenant IDs.

### Module structure
  main.tf (resources), variables.tf (inputs with description+type+default),
  outputs.tf (exported values), provider.tf (at root only).
  NEVER put provider block inside a module.

### State and plan
  All changes via plan → apply. Never use terraform destroy in automation.
"""

_EXPERT_TYPESCRIPT = """
## EXPERT IDENTITY — TypeScript / Next.js 14 / React
You are a principal-level TypeScript engineer (10+ years) specialising in:
Next.js 14 App Router, React 18, Tailwind CSS 3.x, Radix UI, Prisma, SWR, Zod.

### TypeScript discipline
  strict: true in tsconfig. No 'any' types — use unknown and narrow. Explicit return types on functions.
  Zod schemas for all external data. Type-safe API routes with route handlers.

### Next.js App Router patterns
  Server Components by default. 'use client' only when needed (event handlers, hooks, browser APIs).
  Server Actions for mutations. Route handlers in app/api/{route}/route.ts.
  Metadata: export const metadata: Metadata = { title: '...', description: '...' }

### Import discipline
  Absolute imports via @/ alias (configured in tsconfig paths). Never relative ../../ from src root.
  Dynamic imports for heavy components: const X = dynamic(() => import('./X'), { ssr: false })
  NEVER import from node_modules with relative paths.

### Tailwind CSS
  className with cn() utility (clsx + tailwind-merge) for conditional classes.
  Never inline styles unless absolutely unavoidable. No CSS modules alongside Tailwind.

### Testing (Jest + React Testing Library)
  render() + userEvent for component tests. await screen.findBy* for async assertions.
  Mock Next.js router with jest.mock('next/navigation'). MSW for API mocking.
"""

# Stack selection map — keyed by task_id prefix or file extension pattern
_STACK_EXPERTS: dict[str, str] = {
    "dotnet":     _EXPERT_DOTNET,
    "python":     _EXPERT_PYTHON,
    "terraform":  _EXPERT_TERRAFORM,
    "typescript": _EXPERT_TYPESCRIPT,
}

# Task-prefix → stack mapping (extend as new sprints are planned)
_TASK_STACK_MAP: dict[str, str] = {
    "WC012": "dotnet",   # Constitutional Engine (.NET 9 gRPC)
    "WC013": "dotnet",   # Business Platform skeleton
    "WC014": "python",   # Temporal workers
    "WC015": "python",   # FastAPI services / RAG
    "WC016": "terraform",# Infrastructure
    "WC017": "typescript",# Web (Next.js)
    "WC018": "dotnet",   # Integration tests
}

def _build_system_prompt(task_id: str) -> str:
    """Build stack-aware system prompt: universal base + selected expert block."""
    prefix = task_id[:5]  # e.g. 'WC012'
    stack = _TASK_STACK_MAP.get(prefix, "dotnet")  # default: dotnet for current sprint
    expert_block = _STACK_EXPERTS.get(stack, _EXPERT_DOTNET)
    return _BASE_SYSTEM_PROMPT + expert_block

# Legacy alias — used until all call sites are updated to _build_system_prompt()
CONSTITUTIONAL_SYSTEM_PROMPT = _build_system_prompt("WC012")


def get_branch_context(service_dir: str = "src/constitutional-engine") -> str:
    """
    Scan the current sprint branch for files already committed from prior tasks.
    Returns a formatted BRANCH CONTEXT block injected into every LLM prompt.

    This implements the RAG insight: the LLM must know the current state of the
    branch before generating new code. Without this, Task 2 regenerates Task 1's
    files, causing duplicate class definitions and build failures.

    C-083 (Emit-Transport-Listen): the branch state IS the signal from prior tasks.
    C-085 (Idempotency): the LLM must check existing state before acting.
    """
    try:
        # Find all code files added/modified on this branch vs main
        result = run(["git", "diff", "--name-only", "origin/main...HEAD"], check=False, capture=True)
        if result.returncode != 0:
            return ""

        branch_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        code_files = [f for f in branch_files if f.endswith((".cs", ".py", ".ts", ".proto", ".csproj"))]

        if not code_files:
            return ""

        lines = [
            "\n\n# ═══ BRANCH CONTEXT — EXISTING FILES FROM PRIOR TASKS ═══",
            "# These files are ALREADY on the sprint branch from completed tasks.",
            "# Apply EXTEND-NOT-REPLACE rule: do NOT recreate these. Read them to understand",
            "# existing types, namespaces, and interfaces before writing new code.\n",
        ]

        for file_path in sorted(code_files):
            full_path = REPO_ROOT / file_path
            if not full_path.is_file():
                continue

            content = full_path.read_text(encoding="utf-8", errors="replace")

            # For .csproj and appsettings: just list them (don't regenerate)
            if file_path.endswith((".csproj", ".json", ".proto")):
                lines.append(f"## EXISTING (DO NOT REGENERATE): {file_path}")
                if file_path.endswith(".csproj"):
                    # Include package references so LLM uses correct types
                    lines.append(content[:800])
                lines.append("")
                continue

            # For .cs source files: include namespace, class declaration, and method signatures
            # This tells the LLM what types already exist without full file content
            important_lines = []
            for line in content.splitlines():
                stripped = line.strip()
                if any(stripped.startswith(kw) for kw in (
                    "namespace ", "public ", "internal ", "protected ", "private ",
                    "// Implements:", "// constitutional_basis:", "interface ", "record ",
                    "sealed class", "abstract class", "static class",
                )):
                    important_lines.append(line)
                    if len(important_lines) > 30:  # cap per file
                        break

            if important_lines:
                lines.append(f"## EXISTING (may EXTEND but not duplicate): {file_path}")
                lines.append("\n".join(important_lines[:30]))
                lines.append("")

        if len(lines) <= 4:  # only header, no files
            return ""

        lines.append("# ═══ END BRANCH CONTEXT ═══\n")
        return "\n".join(lines)

    except Exception as e:
        print(f"  WARN: get_branch_context failed: {e}")
        return ""


# ── Helpers ──────────────────────────────────────────────────────────────────

def set_output(key: str, value: str) -> None:
    """Write to GitHub Actions step output."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"  OUTPUT {key}={value}")


def record_evidence(event: str, **kwargs) -> None:
    """Bootstrap evidence stub (engineering-standards.md §12)."""
    EVIDENCE_LOG.parent.mkdir(exist_ok=True)
    record = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "stub_mode": True,
        **kwargs,
    }
    with EVIDENCE_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, cwd=REPO_ROOT)


def git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, check=check)


def parse_sprint_state() -> dict:
    """Extract SPRINT_STATE_MACHINE YAML block from PROJECT_STATE.md."""
    content = STATE_FILE.read_text(encoding="utf-8")
    # Find the yaml block under SPRINT_STATE_MACHINE
    match = re.search(
        r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```",
        content, re.DOTALL
    )
    if not match:
        raise ValueError("SPRINT_STATE_MACHINE block not found in PROJECT_STATE.md")

    state: dict = {}
    for line in match.group(1).splitlines():
        line = line.split("#")[0].strip()  # strip comments
        if ":" in line:
            k, _, v = line.partition(":")
            state[k.strip()] = v.strip().strip('"').strip("'")

    # Parse tasks_remaining list
    tasks_block = re.search(
        r"tasks_remaining:\n((?:  - [^\n]+\n?)*)",
        match.group(1)
    )
    if tasks_block:
        tasks = re.findall(r"  - (\S+)", tasks_block.group(1))
        state["tasks_remaining"] = [t for t in tasks if not t.startswith("#")]
    else:
        state["tasks_remaining"] = []

    return state


def check_platform_phase_gate(state: dict) -> None:
    """
    C-001 / FinOps Gate: Refuse ALL implementation work when platform_phase = SPEC.
    This is a hard stop — not a warning. It prevents self-authorization drift.
    In SPEC phase, offer to run spec validation instead of implementation.
    """
    phase = state.get("platform_phase", "SPEC")
    halt = state.get("autonomous_halt", "true").lower()

    if halt == "true":
        record_evidence("autonomous_halt_active", reason="AUTONOMOUS_HALT=true in PROJECT_STATE.md")
        set_output("halt", "true")
        set_output("result", "SKIPPED")
        print("  HALT: AUTONOMOUS_HALT=true — no execution (C-001 Human Override)")
        sys.exit(0)

    if phase == "SPEC":
        print("  INFO: platform_phase=SPEC — running spec validation mode (no src/ operations)")
        record_evidence("spec_phase_validation_mode", platform_phase=phase)
        run_spec_validation()
        set_output("halt", "false")
        set_output("result", "SPEC_VALIDATION_COMPLETE")
        sys.exit(0)

    if phase != "IMPLEMENTATION":
        record_evidence("platform_phase_gate_blocked", platform_phase=phase,
                        reason=f"platform_phase={phase}, not IMPLEMENTATION.")
        set_output("halt", "true")
        set_output("result", "SKIPPED")
        print(f"  HALT: platform_phase={phase}. Must be IMPLEMENTATION to execute.")
        sys.exit(0)


def run_spec_validation() -> None:
    """
    GAP-SIM-08 fix: SPEC-phase useful work.
    When platform_phase=SPEC, the agent validates spec consistency instead of doing nothing.
    Zero LLM cost — pure Python checks.
    """
    print("\n── SPEC Phase Validation Mode ──────────────────────────────────────")
    issues = []

    # Check 1: SPRINT_STATE_MACHINE health
    try:
        state = parse_sprint_state()
        print(f"  ✓ SPRINT_STATE_MACHINE parseable: phase={state.get('platform_phase')}, "
              f"sprint={state.get('current_sprint')}")
    except Exception as e:
        issues.append(f"SPRINT_STATE_MACHINE parse error: {e}")

    # Check 2: Work contract exists
    sprint = state.get("current_sprint", "")
    wc_paths = list(REPO_ROOT.glob(f"work-contracts/{sprint}*.md")) if sprint else []
    if wc_paths:
        print(f"  ✓ Work contract found: {wc_paths[0].name}")
    else:
        issues.append(f"No work contract found for sprint {sprint}")

    # Check 3: build_sprint_index.py can run without errors
    try:
        result = run([sys.executable, "scripts/build_sprint_index.py", "--dry-run", "--no-copilotignore"],
                    check=False, capture=True)
        if result.returncode == 0 or "token budget" in result.stdout.lower():
            print("  ✓ Sprint index builder: parseable")
        else:
            issues.append(f"Sprint index builder error: {result.stderr[:200]}")
    except Exception as e:
        issues.append(f"Sprint index builder exception: {e}")

    # Check 4: Key spec files exist
    required_specs = [
        "constitution/AGENT-ENTRY.md",
        "adr/ADR-INDEX.md",
        "tests/QA-STRATEGY.md",
        "standards/CODING-STANDARDS.md",
    ]
    for spec in required_specs:
        if (REPO_ROOT / spec).exists():
            print(f"  ✓ Spec exists: {spec}")
        else:
            issues.append(f"Required spec missing: {spec}")

    # Report
    if issues:
        print(f"\n  SPEC VALIDATION: {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"    - {issue}")
        record_evidence("spec_validation_issues", count=len(issues), issues=issues)
    else:
        print("\n  SPEC VALIDATION: All checks passed. Platform ready for implementation when Founder authorizes.")
        record_evidence("spec_validation_passed")

    print("── End Spec Validation ──────────────────────────────────────────────\n")


def update_sprint_state(**kwargs) -> None:
    """Update fields in SPRINT_STATE_MACHINE via sprint_state.py."""
    pairs = []
    for k, v in kwargs.items():
        pairs += [k, f'"{v}"' if " " in str(v) else str(v)]
    run([sys.executable, "scripts/sprint_state.py", "set"] + pairs)


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["gh"] + args, check=check, capture=True)


def run_runner_integrity_checks() -> tuple[bool, list[str]]:
    """
    Fail-fast checks for internal runner wiring.

    This catches pipeline bugs (for example, missing helper function definitions)
    before any sprint task execution starts.
    """
    errors: list[str] = []

    required_callables = [
        "parse_llm_files",
        "write_llm_files",
        "validate_written_files",
        "execute_with_llm",
    ]
    for symbol in required_callables:
        candidate = globals().get(symbol)
        if not callable(candidate):
            errors.append(f"Missing or non-callable symbol: {symbol}")

    execute_fn = globals().get("execute_with_llm")
    if callable(execute_fn):
        params = list(inspect.signature(execute_fn).parameters.keys())
        required_params = ["task_id", "task_description", "spec_sections", "constitutional_check"]
        missing = [p for p in required_params if p not in params]
        if missing:
            errors.append("execute_with_llm signature mismatch. Missing params: " + ", ".join(missing))

    handlers = globals().get("TASK_HANDLERS")
    if not isinstance(handlers, dict) or len(handlers) == 0:
        errors.append("TASK_HANDLERS missing or empty")

    parser = globals().get("parse_llm_files")
    if callable(parser):
        probe = (
            '<file path="src/_integrity_probe.txt">ok</file>'
            '<file path="constitution/should-never-pass.md">blocked</file>'
        )
        parsed = parser(probe)
        if "src/_integrity_probe.txt" not in parsed:
            errors.append("parse_llm_files failed to parse valid probe block")
        if any(path.startswith("constitution/") for path in parsed.keys()):
            errors.append("parse_llm_files boundary enforcement failed for constitution/")

    return len(errors) == 0, errors


# ── ADR-030: LLM code generation functions ────────────────────────────────────

def call_llm(task_id: str, task_description: str, spec_content: str,
             constitutional_check: str, model_hint: str = "reasoning",
             max_tokens: int = 10000, attempt: int = 1) -> str | None:
    """
    Call Claude Sonnet 4.6 to generate code for a sprint task.
    Returns the raw LLM response string, or None on failure.

    For model_hint='reasoning' tasks: enables extended thinking (budget_tokens=8000).
    The model reasons about namespaces, DI graph, and existing branch state before
    writing a single line — effectively self-tuning to the project context.

    For all tasks: injects a self-calibration prefix asking the model to derive
    its own implementation plan (files, namespaces, using directives) from the
    spec before committing to code.

    constitutional_basis: ADR-030 (code generation protocol), C-077 (cost ceiling)
    ib_item: IB-020
    """
    if model_hint not in ("reasoning", "auto"):
        return None  # model_hint: none — no LLM needed

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"  WARN: ANTHROPIC_API_KEY not set — cannot call LLM for {task_id}")
        return None

    # Thinking mode: 'enabled' with controlled budget.
    # Lesson from adaptive (run 30104540921): adaptive lets model think indefinitely —
    # used all 18K tokens for thinking, never generated code. block_types=['thinking'], text_chars=0.
    # With 'enabled' + budget_tokens: model KNOWS its thinking limit and plans accordingly,
    # then generates code with remaining tokens. Predictable. Controllable.
    THINKING_OVERHEAD = 8000  # added to max_tokens so thinking doesn't eat code budget
    THINKING_BUDGET   = 8000  # budget_tokens cap — model thinks up to this, then generates
    use_thinking = model_hint == "reasoning"
    effective_max_tokens = (max_tokens + THINKING_OVERHEAD) if use_thinking else max_tokens

    try:
        import urllib.request
        import json as json_mod

        # Self-calibration prefix — injected into every task prompt.
        # Asks the model to derive its OWN implementation plan from the provided spec
        # before writing code. With adaptive thinking enabled, this happens in the
        # internal reasoning block. Without thinking, it forces chain-of-thought.
        calibration_prefix = (
            "## SELF-CALIBRATION (complete before writing any <file> block)\n"
            "From the spec and BRANCH CONTEXT below, derive your implementation plan:\n"
            "1. Which files already exist on the branch? (check BRANCH CONTEXT — do NOT regenerate them)\n"
            "2. Which NEW files will you create? List each with its exact namespace declaration.\n"
            "3. For each file: what using directives does it need? Cross-check the namespace reference above.\n"
            "4. Does ConstitutionalDbContext exist yet? (only if WC012-03a is in BRANCH CONTEXT)\n"
            "5. Confirm your plan matches the namespace reference in the system prompt before proceeding.\n\n"
            "Then write ONLY the new/extended files using <file path=\"...\"> blocks.\n\n"
        )

        user_prompt = (
            f"{calibration_prefix}"
            f"Task: {task_id} — {task_description}\n\n"
            f"Spec context:\n{spec_content}\n\n"
            f"Constitutional check (must pass):\n{constitutional_check}\n\n"
            f"Generate the implementation files now. "
            f"Use <file path=\"...\"> blocks for each file. "
            f"Include unit tests in tests/ directory."
        )

        model_id = os.environ.get("SPRINT_LLM_MODEL", "claude-sonnet-4-6")

        payload: dict = {
            "model": model_id,
            "max_tokens": effective_max_tokens,   # code budget + thinking overhead when active
            "system": _build_system_prompt(task_id),   # stack-aware: dotnet/python/terraform/typescript
            "messages": [{"role": "user", "content": user_prompt}],
        }

        if use_thinking:
            # Enabled thinking: model plans within budget_tokens, then generates code.
            # budget_tokens < effective_max_tokens satisfies API constraint for all tasks:
            #   WC012-02: 8000 < 18000 ✅  WC012-03b: 8000 < 16000 ✅  WC012-03c: 8000 < 13000 ✅
            payload["thinking"] = {"type": "enabled", "budget_tokens": THINKING_BUDGET}
            payload["temperature"] = 1   # required for any thinking mode
            print(f"  Thinking: enabled | budget={THINKING_BUDGET} | effective_max={effective_max_tokens} "
                  f"(code={max_tokens} + overhead={THINKING_OVERHEAD})")
        else:
            payload["temperature"] = 0

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json_mod.dumps(payload).encode(),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        # Observability: log prompt size before call
        prompt_chars = len(json_mod.dumps(payload))
        print(f"  REQ:  {task_id} attempt={attempt} | prompt={prompt_chars:,} chars | max_tokens={effective_max_tokens} (code={max_tokens})")
        # Timeout: bounded to prevent long "stuck" windows on a single API call.
        # Defaults can be overridden via env for controlled tuning in CI.
        timeout_floor = int(os.environ.get("LLM_API_TIMEOUT_FLOOR_S", "180"))
        timeout_ceiling = int(os.environ.get("LLM_API_TIMEOUT_CEILING_S", "420"))
        scaled_timeout = (effective_max_tokens // 50) * 3
        api_timeout = max(timeout_floor, min(timeout_ceiling, scaled_timeout))
        t_start = __import__('time').monotonic()
        with urllib.request.urlopen(req, timeout=api_timeout) as resp:
            result = json_mod.loads(resp.read())
        latency_s = __import__('time').monotonic() - t_start
        content = result.get("content", [])
        # Extract only text blocks — thinking blocks (type="thinking") are stripped.
        text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
        usage = result.get("usage", {})
        tokens_in  = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
        thinking_blocks = sum(1 for b in content if b.get("type") == "thinking")
        thinking_chars  = sum(len(b.get("thinking", "")) for b in content if b.get("type") == "thinking")
        stop_reason  = result.get("stop_reason", "unknown")
        text_chars   = len(text)
        block_types  = [b.get("type") for b in content]
        text_snippet = text[:400].replace("\n", " ") if text else "(empty)"
        # ── Industry-standard LLM call observability ─────────────────────────
        print(f"  REQ:  {task_id} attempt={attempt} | prompt={prompt_chars:,} chars | max_tokens={max_tokens}")
        print(f"  LLM:  {task_id} attempt={attempt} → {tokens_in} in / {tokens_out} out | "
              f"latency={latency_s:.1f}s | stop={stop_reason!r}")
        if thinking_blocks:
            print(f"  THINK: {thinking_blocks} block(s), {thinking_chars:,} chars")
        print(f"  RESP: block_types={block_types} | text_chars={text_chars:,}")
        print(f"  TEXT: {text_snippet}")
        # ─────────────────────────────────────────────────────────────────────
        record_evidence(
            "llm_call",
            task=task_id, attempt=attempt,
            tokens_in=tokens_in, tokens_out=tokens_out,
            latency_s=round(latency_s, 2),
            stop_reason=stop_reason,
            block_types=block_types,
            text_chars=text_chars,
            thinking_blocks=thinking_blocks,
            thinking_chars=thinking_chars,
            prompt_chars=prompt_chars,
        )
        return text
    except urllib.error.HTTPError as e:
        body = e.read(300).decode("utf-8", errors="replace")
        if e.code == 429:
            print(f"  INFRA: HTTP 429 rate limit for {task_id} — caller should retry with backoff")
            raise RuntimeError(f"RATE_LIMIT:{e.code}:{body}") from e
        elif e.code >= 500:
            print(f"  INFRA: HTTP {e.code} server error for {task_id}")
            raise RuntimeError(f"API_SERVER_ERROR:{e.code}:{body}") from e
        else:
            print(f"  WARN: HTTP {e.code} for {task_id}: {body}")
            return None
    except TimeoutError:
        print(f"  INFRA: API read timed out after {api_timeout}s for {task_id}")
        raise RuntimeError(f"API_TIMEOUT:{api_timeout}s") from None
    except Exception as e:
        err = str(e)
        if "timed out" in err.lower() or "timeout" in err.lower():
            print(f"  INFRA: API read timed out for {task_id}: {err}")
            raise RuntimeError(f"API_TIMEOUT:{err}") from e
        print(f"  WARN: LLM call failed for {task_id}: {err}")
        return None


# ── MagicLLM Bridge — replaces call_llm() with constitutional AI execution ───
# Implements: architecture/reference/magic-llm/architecture.md §4 Architecture
# Constitutional basis: C-059 (Evidence First), C-069 (Self-Improvement), C-077

def call_llm_via_magiclm(
    task_id: str,
    task_description: str,
    spec_content: str,
    constitutional_check: str,
    model_hint: str = "reasoning",
    max_tokens: int = 10000,
    attempt: int = 1,
    goal_id: str = "",
    ptr_snapshot: dict | None = None,
) -> str | None:
    """
    MagicLLM bridge — replaces call_llm() with constitutionally governed invocation.

    Adds vs. call_llm():
      ✓ Task complexity scoring → model selection (O-01: 91% cost reduction)
      ✓ Dynamic thinking budget (O-03)
      ✓ MagicLLM Decision Record committed to Goal Register (C-059 Evidence First)
      ✓ PTR 2.0 snapshot injected (includes .csproj packages — closes CS0246 gap)
      ✓ Stack-namespaced PTR (dotnet/python/terraform/typescript)

    Returns raw LLM response string (same format as call_llm()) or None.
    """
    if model_hint not in ("reasoning", "auto"):
        return None  # model_hint: none — no LLM needed

    # Ensure both repo-root and scripts/ are importable in GitHub Actions and local script mode.
    import sys as _sys
    repo_root_path = str(REPO_ROOT)
    scripts_path = str(REPO_ROOT / "scripts")
    if repo_root_path not in _sys.path:
        _sys.path.insert(0, repo_root_path)
    if scripts_path not in _sys.path:
        _sys.path.insert(0, scripts_path)

    try:
        # Execution context 1: launched from repo root (package path includes "scripts")
        from scripts.magic_llm import MagicLLMPipeline, MagicLLMRequest, TaskCategory
        from scripts.goal_orchestrator.goal_register_github import make_goal_register_writer
    except ImportError:
        try:
            # Execution context 2: launched as "python scripts/autonomous_sprint_runner.py"
            # where sys.path points at scripts/ directly.
            from magic_llm import MagicLLMPipeline, MagicLLMRequest, TaskCategory
            from goal_orchestrator.goal_register_github import make_goal_register_writer
        except ImportError as e:
            print(f"  WARN: MagicLLM not available ({e}) — falling back to call_llm()")
            return call_llm(task_id, task_description, spec_content,
                            constitutional_check, model_hint, max_tokens, attempt)

    # Map task to category — item 10: cost-aware model tiering
    # skeleton phase → DESIGN_CONTRACTS (Cat.3) → eligible for cheaper model (Haiku)
    # logic/full phase → CODE_GENERATION (Cat.2) → Sonnet (reasoning)
    # test phase → TEST_GENERATION (Cat.6) → Sonnet (reasoning)
    tid = task_id.lower()
    if "cct" in tid or "test" in tid or tid.endswith("-02c") or tid.endswith("-03c") or tid.endswith("-04c"):
        category = TaskCategory.TEST_GENERATION
    elif task_id.endswith("-skeleton") or "skeleton" in task_id.lower():
        category = TaskCategory.DESIGN_CONTRACTS  # cheaper model eligible
    else:
        category = TaskCategory.CODE_GENERATION

    # Derive goal ID
    effective_goal_id = goal_id or f"GOAL-{task_id.split('-')[0].upper()}"

    # Build context sections
    context_sections: list[str] = [spec_content]
    if constitutional_check:
        context_sections.append(f"## CONSTITUTIONAL REQUIREMENTS\n{constitutional_check}")

    # Assemble PTR 2.0 if not supplied
    if ptr_snapshot is None:
        try:
            try:
                from scripts.ptr_assembler import get_assembler
            except ImportError:
                from ptr_assembler import get_assembler
            assembler = get_assembler()
            full_ptr = assembler.assemble(scope=["src", "scripts"])
            task_ptr = assembler.extract_task_ptr(full_ptr, context_sections)
            # Inject stack that matches the task
            stack = "python" if "WC014" in task_id or "WC015" in task_id else "dotnet"
            ptr_snapshot = task_ptr.get(stack, {})
        except Exception as e:
            print(f"  WARN: PTR 2.0 assembly failed ({e}) — using empty PTR")
            ptr_snapshot = {}

    request = MagicLLMRequest(
        goal_id=effective_goal_id,
        institution_id="INST-010",
        go_authorization_id=f"GOA-{effective_goal_id}-INST-010-{task_id}",
        task_category=category,
        task_description=task_description,
        context_sections=context_sections,
        ptr_snapshot=ptr_snapshot,
        expected_output_format="xml_file_blocks",
        execution_plan_reference=f"EP-{task_id}",
        previous_attempt_id=f"attempt-{attempt - 1}" if attempt > 1 else None,
        cascade_level=None,
        max_tokens=max_tokens,
    )

    writer = make_goal_register_writer()
    # write_record signature: (goal_id: str, record: dict) → str
    # Wrap to ensure positional call matches regardless of bridge version
    def _safe_write(record: dict) -> str:
        return writer.write_record(effective_goal_id, record)
    pipeline = MagicLLMPipeline(
        goal_register_writer=_safe_write,
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )

    try:
        response = pipeline.invoke(request)
    except RuntimeError as e:
        # Propagate infra errors (timeout, rate limit) to outer retry logic
        raise
    except Exception as e:
        print(f"  WARN: MagicLLM invocation error ({e}) — falling back to call_llm()")
        return call_llm(task_id, task_description, spec_content,
                        constitutional_check, model_hint, max_tokens, attempt)

    if response.status == "accepted":
        print(f"  ✓ MagicLLM: {response.model_version} · "
              f"complexity={response.parsed_artifacts.get('complexity', '?')} · "
              f"cost=₹{response.cost_inr:.4f} · attempt={attempt}")
        return response.raw_output
    else:
        print(f"  MagicLLM returned {response.status}: {response.failure_classification}")
        return None  # triggers outer retry loop


def parse_llm_files(response: str) -> dict[str, str]:
    """
    Parse <file path="...">content</file> blocks from LLM response.
    Returns dict of {relative_path: content}.
    Enforces ADR-030 write boundary (ALLOWED_WRITE_ROOTS).
    """
    files: dict[str, str] = {}
    pattern = re.compile(r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>', re.DOTALL)
    for match in pattern.finditer(response):
        path = match.group(1).strip()
        content = match.group(2).strip()
        # ADR-030: enforce write boundary
        if not any(path.startswith(root) for root in ALLOWED_WRITE_ROOTS):
            print(f"  WARN: LLM attempted to write outside boundary: {path} — skipped")
            continue
        # Check for design questions that need spec clarification
        if "DESIGN_QUESTION:" in content:
            questions = re.findall(r"DESIGN_QUESTION: (.+)", content)
            for q in questions:
                print(f"  ⚠️  Design question in {path}: {q}")
        files[path] = content
    return files


def write_llm_files(files: dict[str, str]) -> list[str]:
    """Write parsed files to disk. Returns list of written paths."""
    written = []
    for rel_path, content in files.items():
        abs_path = REPO_ROOT / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        written.append(rel_path)
        print(f"  Written: {rel_path} ({len(content)} chars)")
    return written


def validate_written_files(written: list[str]) -> tuple[bool, str]:
    """Run validation appropriate to file type. Returns (ok, error_text)."""
    py_files = [f for f in written if f.endswith(".py")]
    cs_files = [f for f in written if f.endswith(".cs")]
    ok = True
    errors: list[str] = []

    for f in py_files:
        result = run(["python3", "-m", "py_compile", f], check=False, capture=True)
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip()
            print(f"  FAIL: {f} syntax error: {msg[:200]}")
            errors.append(f"{f}: {msg[:300]}")
            ok = False
        else:
            print(f"  ✅ Python syntax OK: {f}")

    if cs_files:
        # Find the csproj dir: src/<service>/ from the first .cs file
        csproj_dirs: set[str] = set()
        for f in cs_files:
            parts = Path(f).parts
            if len(parts) > 1:
                csproj_dirs.add(str(REPO_ROOT / parts[0] / parts[1]))
        for csproj_dir in csproj_dirs:
            # Check .csproj exists — if not, that's an explicit error for the retry context
            csproj_files = list(Path(csproj_dir).glob("*.csproj")) if Path(csproj_dir).exists() else []
            if not csproj_files:
                msg = (f"No .csproj file found in {csproj_dir}. "
                       f"You MUST generate the .csproj in src/constitutional-engine/ (not any other directory). "
                       f"Write ALL files to src/constitutional-engine/ only.")
                print(f"  FAIL: {msg}")
                errors.append(msg)
                ok = False
                continue
            # Pick specific .csproj to avoid MSB1050 (multiple .csproj in dir)
            if len(csproj_files) > 1:
                canonical = [f for f in csproj_files if "-" in f.name]
                build_target = str(canonical[0]) if canonical else str(csproj_files[0])
                print(f"  WARN: {len(csproj_files)} .csproj found — building {Path(build_target).name}")
            else:
                build_target = str(csproj_files[0])
            result = run(["dotnet", "build", build_target, "--nologo", "-v", "quiet"],
                        check=False, capture=True)
            if result.returncode != 0:
                # dotnet quiet mode sends errors to stdout, not stderr
                build_output = (result.stdout.strip() or result.stderr.strip())[:600]
                print(f"  FAIL: dotnet build in {csproj_dir}:\n{build_output}")
                errors.append(f"dotnet build {csproj_dir}:\n{build_output}")
                ok = False
            else:
                print(f"  ✅ .NET build OK: {csproj_dir}")
    return ok, "\n".join(errors)


def execute_with_llm(task_id: str, task_description: str, spec_sections: dict,
                     constitutional_check: str, model_hint: str = "reasoning",
                     max_tokens: int = 10000) -> bool:
    """
    Execute a code generation task using Claude (ADR-030 protocol).
    Implements the 3-attempt retry loop with validation.
    Returns True on success, False (with flag_spec_gap) on exhausted retries.

    constitutional_basis: ADR-030, C-059, C-076, C-077
    ib_item: IB-020
    """
    # Build spec content from sections
    spec_lines = [f"# Spec context for {task_id}"]
    for file_path, section in spec_sections.items():
        full_path = REPO_ROOT / file_path
        if full_path.is_file():
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if section == "full" or len(content) < 6000:
                spec_lines.append(f"\n## {file_path}\n{content[:4000]}")
            else:
                spec_lines.append(f"\n## {file_path} (section: {section})\n[load section '{section}' from this file]")
    spec_content = "\n".join(spec_lines)

    # RAG: inject branch context — tell LLM what prior tasks already generated.
    # C-083 (Emit-Transport-Listen): prior task outputs are signals for this task.
    # C-085 (Idempotency): LLM must not regenerate files that already exist.
    branch_context = get_branch_context()
    if branch_context:
        spec_content = spec_content + branch_context
        print(f"  Branch context injected ({len(branch_context.splitlines())} lines) — EXTEND-NOT-REPLACE active")

    # Industry practice #6: cross-file namespace index (USING_MAP) — prevents CS0246.
    try:
        try:
            from scripts.ptr_assembler import get_assembler
        except ImportError:
            from ptr_assembler import get_assembler
        _asm = get_assembler()
        _using_map = _asm.build_using_map()
        if _using_map:
            spec_content = spec_content + "\n\n" + _asm.using_map_to_prompt_block(_using_map)
            print(f"  USING_MAP injected ({len(_using_map)} types) — CS0246 prevention active")
    except Exception as _ume:
        print(f"  WARN: USING_MAP build failed ({_ume}) — skipping")

    failure_context = ""
    infra_failures = 0  # count of transient API failures (timeout, rate limit, server error)
    # Bounded to 3 to recover simple compile deltas surfaced by Retry Advisor
    # (for example CS0266 nullable conversion) without immediate spec-gap escalation.
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        print(f"\n── {task_id} (attempt {attempt}/{max_attempts}) ──")

        prompt_with_context = spec_content
        if failure_context:
            prompt_with_context += f"\n\n# Previous attempt failed:\n{failure_context}\nFix the issues above."

        try:
            # MagicLLM bridge: constitutional AI execution with Evidence First,
            # task complexity scoring (O-01), PTR 2.0, MagicLLM Decision Records
            response = call_llm_via_magiclm(
                task_id, task_description, prompt_with_context,
                constitutional_check, model_hint, max_tokens,
                attempt=attempt,
            )
        except RuntimeError as infra_err:
            err_str = str(infra_err)
            infra_failures += 1
            if err_str.startswith("API_TIMEOUT"):
                print(f"  INFRA_TIMEOUT on attempt {attempt} — NOT a spec gap. Retrying in 30s.")
            elif err_str.startswith("RATE_LIMIT"):
                print(f"  RATE_LIMIT on attempt {attempt} — backing off 60s before retry.")
                import time; time.sleep(60)
            elif err_str.startswith("API_SERVER_ERROR"):
                print(f"  API_SERVER_ERROR on attempt {attempt} — retrying in 30s.")
            else:
                print(f"  INFRA_ERROR on attempt {attempt}: {err_str}")
            import time; time.sleep(30)
            continue

        if not response:
            print(f"  LLM call returned no response on attempt {attempt}")
            continue

        try:
            files = parse_llm_files(response)
            if not files:
                print(f"  No <file> blocks found in LLM response on attempt {attempt}")
                failure_context = "Response contained no <file path='...'> blocks. Generate file blocks."
                continue

            # ── Stage 1: Pre-compile self-review (before write) ───────────────
            # Haiku reviews generated code for obvious compile errors and corrects
            # them inline. Cost: ~$0.001/file. Eliminates 60-70% of compile failures.
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key and files:
                try:
                    import sys as _sys
                    _scripts = str(REPO_ROOT / "scripts")
                    if _scripts not in _sys.path:
                        _sys.path.insert(0, _scripts)
                    from codegen_self_review import pre_compile_review
                    try:
                        from ptr_assembler import get_assembler as _ga
                        _using_map = _ga().build_using_map()
                    except Exception:
                        _using_map = None
                    files = pre_compile_review(files, api_key, _using_map)
                    print(f"  PRE-REVIEW: self-review complete ({len(files)} file(s))")
                except Exception as _pre_err:
                    print(f"  PRE-REVIEW: skipped ({_pre_err})")

            written = write_llm_files(files)
            ok, build_error = validate_written_files(written)
        except Exception as parse_exc:
            # Runner-side error (not a spec gap): halt task immediately and surface clearly.
            failure_context = f"RUNNER_PIPELINE_BUG: {type(parse_exc).__name__}: {parse_exc}"
            print(f"  ❌ {failure_context}")
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "PIPELINE_BUG", "error_type": type(parse_exc).__name__,
                "build_error_snippet": str(parse_exc)[:200], "attempts": attempt, "spec_gap_issue": None,
            }
            break
        if ok:
            # Commit the generated files
            git(["add"] + written, check=False)
            diff = git(["diff", "--cached", "--quiet"], check=False)
            if diff.returncode != 0:
                git(["commit", "-m",
                     f"feat: {task_id} — {task_description}\n\n"
                     f"IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
            print(f"  ✅ {task_id} complete ({len(written)} files)")
            # Industry Item 11: if this was a retry (attempt > 1), record the fix in learning cache.
            if attempt > 1 and failure_context.startswith("RETRY ADVISOR DIAGNOSIS:"):
                try:
                    _spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
                    import importlib.util as _ilu
                    _s = _ilu.spec_from_file_location("sprint_retry_advisor",
                         str(REPO_ROOT / "scripts" / "sprint_retry_advisor.py"))
                    _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
                    _m.record_successful_fix(
                        error_snippet=build_error[:200] if build_error else "",
                        fix_instruction=failure_context[failure_context.find("TARGETED FIX"):failure_context.find("TARGETED FIX")+400] if "TARGETED FIX" in failure_context else failure_context[:400],
                        error_type=failure_context.split("\n")[0].replace("RETRY ADVISOR DIAGNOSIS:", "").strip(),
                        task_id=task_id,
                    )
                    print(f"  LEARNING CACHE: fix recorded for future runs (C-069)")
                except Exception:
                    pass
            # Emit success signal for Constitutional Monitor (C-069)
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "SUCCESS", "error_type": None,
                "build_error_snippet": None, "attempts": attempt, "spec_gap_issue": None,
            }
            return True
        else:
            # ── Stage 2: Symbol-level patch (before full-file retry) ─────────
            # Extract failing lines only. Patch just those symbols.
            # 20x cheaper than full-file regeneration. No regression risk.
            if api_key and attempt < max_attempts:
                try:
                    from codegen_self_review import symbol_level_patch
                    patches = symbol_level_patch(build_error, api_key)
                    if patches:
                        print(f"  SYMBOL-PATCH: applying surgical fixes to {len(patches)} file(s)")
                        for patch_path, patch_content in patches.items():
                            full = REPO_ROOT / patch_path
                            full.write_text(patch_content, encoding="utf-8")
                        # Re-validate after patch
                        patch_written = list(patches.keys())
                        ok2, build_error2 = validate_written_files(patch_written)
                        if ok2:
                            print(f"  SYMBOL-PATCH: ✅ compile error resolved — skipping full retry")
                            # Treat as if ok=True from the original validation
                            git(["add"] + written + patch_written, check=False)
                            diff = git(["diff", "--cached", "--quiet"], check=False)
                            if diff.returncode != 0:
                                git(["commit", "-m",
                                     f"feat: {task_id} — {task_description} (symbol-patched)\n\n"
                                     f"IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
                            print(f"  ✅ {task_id} complete via symbol-patch ({len(written)} files)")
                            _MONITOR_SIGNAL["task_results"][task_id] = {
                                "result": "SUCCESS", "error_type": None,
                                "build_error_snippet": None, "attempts": attempt, "spec_gap_issue": None,
                            }
                            return True
                        else:
                            print(f"  SYMBOL-PATCH: patch did not fully resolve — falling through to advisor")
                            build_error = build_error2  # use updated errors for advisor
                except Exception as _sp_err:
                    print(f"  SYMBOL-PATCH: skipped ({_sp_err})")

            # Layer 1: Sprint Retry Advisor — classify error before next attempt
            # C-077 (FinOps): rule-based classification costs nothing; cheap LLM only for unknowns
            # C-082 (Build Validation): every failed attempt must be diagnosed, not just retried
            import importlib.util as _ilu, sys as _sys
            _spec = _ilu.spec_from_file_location("sprint_retry_advisor",
                     str(REPO_ROOT / "scripts" / "sprint_retry_advisor.py"))
            _mod = _ilu.module_from_spec(_spec)
            # D2 FIX: register in sys.modules BEFORE exec_module — otherwise @dataclass
            # decorator calls sys.modules.get(cls.__module__).__dict__ → None.__dict__ crash
            _sys.modules.setdefault("sprint_retry_advisor", _mod)
            _spec.loader.exec_module(_mod)
            diagnose_build_error = _mod.diagnose_build_error
            branch_cs_files = [
                str(p.relative_to(REPO_ROOT))
                for p in REPO_ROOT.glob("src/**/*.cs")
            ]
            diagnosis = diagnose_build_error(task_id, build_error, written, branch_cs_files)

            # Stop-loss: if confidence < 30% and no should_retry, skip immediately
            if diagnosis.confidence < 0.30 and not diagnosis.should_retry:
                print(f"  Retry Advisor: STOP_LOSS — confidence={diagnosis.confidence:.0%} < 30%; skipping remaining attempts")
                failure_context = (
                    f"RETRY ADVISOR: {diagnosis.error_type} — confidence below stop-loss threshold.\n"
                    f"{build_error[:200]}"
                )
                break

            if not diagnosis.should_retry:
                # Advisor says: don't waste another attempt — flag spec-gap now
                print(f"  Retry Advisor: {diagnosis.error_type} — skipping remaining attempts "
                      f"(confidence={diagnosis.confidence:.0%})")
                failure_context = (
                    f"RETRY ADVISOR: {diagnosis.error_type} — unrecoverable without spec fix.\n"
                    f"{build_error[:200]}"
                )
                break  # exit the attempt loop, fall through to flag_spec_gap

            # Advisor produced a targeted fix — use it as the retry context
            failure_context = (
                f"RETRY ADVISOR DIAGNOSIS: {diagnosis.error_type}\n"
                f"CONSTITUTIONAL BASIS: {diagnosis.constitutional_trace}\n"
                f"TARGETED FIX REQUIRED: {diagnosis.fix_instruction}\n\n"
                f"ORIGINAL BUILD ERROR (for reference):\n{build_error[:300]}"
            )
            print(f"  Retry Advisor: {diagnosis.error_type} — intelligent retry with fix context")

    # All attempts exhausted — categorize the failure type
    if failure_context.startswith("RUNNER_PIPELINE_BUG:"):
        print(f"  ⚠️  PIPELINE_BUG: {task_id} failed due to runner logic, not spec content.")
        return False

    if infra_failures == max_attempts:
        # ALL failures were infrastructure (timeout/rate-limit/server error) — NOT a spec gap
        print(f"  ⚠️  INFRA_FAILURE: {task_id} — all {max_attempts} attempts were API failures (timeout/rate-limit).")
        print(f"  This is NOT a spec gap. No issue created. Next cron run will retry automatically.")
        # Signal to main() that this was an infra failure, not a code/spec failure
        _INFRA_ERROR_TASKS.append(task_id)
        # Emit INFRA_ERROR signal for Constitutional Monitor (C-069)
        _MONITOR_SIGNAL["task_results"][task_id] = {
            "result": "INFRA_ERROR", "error_type": "API_TIMEOUT",
            "build_error_snippet": None, "attempts": max_attempts, "spec_gap_issue": None,
        }
        return False
    elif infra_failures > 0:
        # Mixed: some infra failures + some build failures — treat as spec gap but note it
        gap_desc = (f"{task_id} failed after {max_attempts} attempts ({infra_failures} API timeouts, "
                    f"{max_attempts - infra_failures} build failures). Last build error: {failure_context[:200]}")
    else:
        # Spec-gap policy gate (C-065 + Goal Orchestrator autonomous recovery):
        # Only escalate to spec-gap issue when failure context has NO known advisor fix.
        # RETRY ADVISOR DIAGNOSIS = diagnosable build failure = route to cascade, not spec-gap.
        if failure_context.startswith("RETRY ADVISOR DIAGNOSIS:"):
            print(f"  ⚠️  BUILD_FAILURE: {task_id} exhausted {max_attempts} attempts with actionable diagnosis.")
            print("  Routing to cascade for autonomous recovery (not spec-gap issue).")
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "BUILD_FAILURE", "error_type": "RETRY_EXHAUSTED",
                "build_error_snippet": failure_context[:200], "attempts": max_attempts, "spec_gap_issue": None,
            }
            return False

        gap_desc = f"{task_id} failed validation after {max_attempts} LLM attempts. Last error: {failure_context[:300]}"

    flag_spec_gap(
        task_id=task_id,
        gap_description=gap_desc,
        affected_spec=list(spec_sections.keys())[0] if spec_sections else "unknown",
        constitutional_basis="C-059 (Traceability — implementation must match spec), C-076 (Coverage)"
    )
    return False


def flag_spec_gap(
    task_id: str,
    gap_description: str,
    affected_spec: str,
    workaround: str = "",
    constitutional_basis: str = "",
) -> None:
    """
    HALT the current task and create a GitHub Issue for EA/SA/Founder review.

    The implementation agent CANNOT proceed with a workaround. A workaround is
    an architectural decision — it is outside the Implementation hat's authority (C-065).

    Constitutional basis:
      C-065: SDLC Separation — Implementation hat cannot make architectural decisions
      C-066: Tier 3 — Architectural/spec changes require EA office or Founder approval
      C-059: Traceability — every implementation must trace to a valid spec; gap = no trace

    This function:
      1. Creates a GitHub Issue (type:spec-gap, awaiting:ea-review)
      2. Updates Sprint Dashboard with BLOCKED status
      3. Returns (caller must then return False to halt the task)

    Recovery path (next sprint run after spec is fixed):
      - Sprint runner checks for open spec-gap issues tagged to this task
      - If issue is closed: task is retried with corrected spec
      - If issue is still open: task is SKIPPED (still blocked)
    """
    github_repo = os.environ.get("GITHUB_REPO", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")

    workaround_note = (
        f"\n## Workaround Considered (NOT Applied)\n\n{workaround}\n\n"
        f"**This workaround was NOT implemented.** The agent does not have authority "
        f"to make architectural decisions (C-065, C-066 Tier 3).\n"
    ) if workaround else ""

    title = f"spec-gap [{task_id}]: {gap_description[:80]}"
    body = (
        f"## Spec Gap — Implementation Halted\n\n"
        f"**Discovered by:** Autonomous Sprint Agent (Platform IT Expert — Implementation hat)\n"
        f"**During task:** `{task_id}`\n"
        f"**Affected spec:** `{affected_spec}`\n"
        f"**Task status:** BLOCKED — will not retry until this issue is closed\n\n"
        f"## Gap Description\n\n{gap_description}\n\n"
        + workaround_note
        + f"## Required Action (EA/SA or Founder)\n\n"
        f"1. Review the gap described above\n"
        f"2. Update `{affected_spec}` with the correct design decision\n"
        f"3. Open a PR for the spec change (branch: `spec-fix/{task_id.lower()}-gap`)\n"
        f"4. Merge the spec PR\n"
        f"5. **Close this issue** — the next sprint run will detect the closure and retry `{task_id}`\n\n"
        f"The implementation agent will automatically retry `{task_id}` when this issue is closed.\n\n"
        + (f"## Constitutional Basis\n\n{constitutional_basis}\n\n" if constitutional_basis else "")
        + f"---\n_Auto-generated by `flag_spec_gap()` in `scripts/autonomous_sprint_runner.py`_"
    )

    if github_repo and github_token:
        result = gh([
            "issue", "create",
            "--repo", github_repo,
            "--title", title,
            "--body", body,
            "--label", "awaiting:founder-approval",
        ], check=False)
        if result.returncode == 0:
            issue_url = result.stdout.strip()
            issue_num = issue_url.split("/")[-1] if "/" in issue_url else "?"
            print(f"  🔴 SPEC GAP — task HALTED. Issue #{issue_num} created.")
            print(f"     Gap: {gap_description[:80]}")
            print(f"     Spec: {affected_spec}")
            print(f"     Fix the spec, close the issue, and the next sprint run retries.")
            record_evidence("spec_gap_halt", task=task_id, issue=issue_num, gap=gap_description[:100])
            # Emit SPEC_GAP signal for Constitutional Monitor (C-069)
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "SPEC_GAP", "error_type": "BUILD_ERROR",
                "build_error_snippet": gap_description[:200],
                "attempts": 3, "spec_gap_issue": issue_num,
            }
            _MONITOR_SIGNAL["spec_gap_issues"].append(issue_num)
        else:
            print(f"  🔴 SPEC GAP — task HALTED (issue creation failed: {result.stderr[:100]})")
            print(f"     Gap: {gap_description}")
            record_evidence("spec_gap_halt_no_issue", task=task_id, gap=gap_description[:100])
    else:
        print(f"  🔴 SPEC GAP — task HALTED (no GitHub token for issue creation)")
        print(f"     Gap: {gap_description}")

    # Note: caller must return False after calling this function
    # Example: if some_condition: flag_spec_gap(...); return False


# ── Task implementations ─────────────────────────────────────────────────────

def execute_wc011_01() -> bool:
    """WC011-01: Validate docker-compose.yml."""
    print("── WC011-01: Validate docker-compose.yml ──")
    result = run(
        ["docker", "compose", "-f", "docker-compose.yml", "config", "--quiet"],
        check=False, capture=True
    )
    REPO_ROOT.joinpath("logs").mkdir(exist_ok=True)
    (REPO_ROOT / "logs" / "docker-compose-validation.txt").write_text(
        result.stdout + result.stderr
    )
    if result.returncode == 0:
        print("  OK: docker compose config valid")
    else:
        print(f"  FAIL: docker compose config invalid — {result.stderr[:200]}")
        return False

    # Verify required services are present
    config_text = result.stdout
    required = ["constitutional-engine", "business-platform", "professional-runtime",
                "ai-runtime", "web", "postgres", "keycloak", "temporal"]
    missing = [svc for svc in required if svc not in config_text]
    if missing:
        for svc in missing:
            print(f"  FAIL: required service '{svc}' missing from docker-compose config")
        print(f"  FAIL: {len(missing)} required service(s) missing — cannot pass WC011-01")
        return False

    git(["add", "docker-compose.yml", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-01 - validate docker-compose.yml\n\n"
             "IB: IB-009\nConstitutional: C-067, C-004\nCCTs-added: none"])
    return True


def execute_wc011_02() -> bool:
    """WC011-02: Validate DB migration scripts 01–10."""
    print("── WC011-02: Validate DB migration scripts ──")
    init_dir = REPO_ROOT / "infrastructure" / "postgres" / "init"

    if not init_dir.exists():
        print(f"  FAIL: {init_dir} does not exist")
        return False

    sql_files = sorted(init_dir.glob("*.sql"))
    print(f"  Found {len(sql_files)} SQL files in {init_dir.relative_to(REPO_ROOT)}")

    # Check for required files
    required_prefixes = ["01-", "03-", "04-", "07-", "09-"]
    for prefix in required_prefixes:
        matches = [f for f in sql_files if f.name.startswith(prefix)]
        if not matches:
            print(f"  WARN: No migration file starting with '{prefix}' found")
        else:
            print(f"  OK: {matches[0].name}")

    # Check each file for constitutional markers
    issues = []
    for sql_file in sql_files:
        content = sql_file.read_text(encoding="utf-8")
        # C-007/C-027: constitutional schema must not have UPDATE/DELETE on audit_records
        if "audit_records" in content and ("UPDATE" in content or "DELETE" in content):
            if "NO UPDATE" not in content and "RULE NO" not in content.upper():
                flag_spec_gap(
                    task_id="WC011-02",
                    gap_description=f"{sql_file.name}: potential UPDATE/DELETE on audit_records — C-007/C-027 violation. "
                                    "The constitutional audit ledger must be append-only. No UPDATE or DELETE permitted.",
                    affected_spec="infrastructure/postgres/init/05-append-only-rules.sql",
                    constitutional_basis="C-007 (Ledger Immutability), C-027 (Append-only enforcement)"
                )
                return False
        # C-027: append-only rules must exist
        if sql_file.name.startswith("05-append-only"):
            if "RULE" not in content.upper() and "TRIGGER" not in content.upper():
                issues.append(f"{sql_file.name}: No RULE or TRIGGER found for append-only enforcement (C-027)")
        # Add validation comment if not present
        if "-- Validated: WC-011" not in content:
            updated = content.rstrip() + "\n-- Validated: WC-011 Sprint 011 (infrastructure check only)\n"
            sql_file.write_text(updated, encoding="utf-8")

    if issues:
        for issue in issues:
            print(f"  WARN: {issue}")
    else:
        print("  OK: All migration files pass constitutional markers check")

    git(["add", "infrastructure/postgres/init/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-02 - validate DB migration scripts 01-10\n\n"
             "IB: IB-009\nConstitutional: C-007, C-027, C-059\nCCTs-added: none"])
    return True


def execute_wc011_03() -> bool:
    """WC011-03: Validate Keycloak realm import."""
    print("── WC011-03: Validate Keycloak realm import ──")
    keycloak_dir = REPO_ROOT / "infrastructure" / "keycloak"
    realm_files = list(keycloak_dir.glob("*.json")) if keycloak_dir.exists() else []

    if not realm_files:
        print(f"  FAIL: No realm JSON file found in {keycloak_dir.relative_to(REPO_ROOT)}")
        return False

    realm_file = realm_files[0]
    print(f"  Found realm file: {realm_file.name}")

    import json as json_mod
    try:
        realm = json_mod.loads(realm_file.read_text(encoding="utf-8"))
    except json_mod.JSONDecodeError as e:
        print(f"  FAIL: Realm JSON is invalid — {e}")
        return False

    # Constitutional checks
    realm_id = realm.get("realm", "")
    if realm_id != "waooaw":
        print(f"  WARN: realm id is '{realm_id}', expected 'waooaw'")
    else:
        print(f"  OK: realm id = waooaw")

    # Check for Google IDP (ADR-008)
    identity_providers = realm.get("identityProviders", [])
    google_idp = [p for p in identity_providers if p.get("providerId") == "google"]
    if google_idp:
        print("  OK: Google IDP configured (ADR-008)")
    else:
        print("  WARN: Google IDP not found in realm (ADR-008 requires Google as default IDP)")

    print("  OK: Keycloak realm validation complete")
    return True


def execute_wc011_05() -> bool:
    """WC011-05: Verify setup.sh and get-dev-token.sh."""
    print("── WC011-05: Verify scripts ──")
    scripts_to_check = [
        REPO_ROOT / "scripts" / "setup.sh",
        REPO_ROOT / "scripts" / "get-dev-token.sh",
    ]
    all_ok = True
    for script in scripts_to_check:
        if not script.exists():
            print(f"  FAIL: {script.name} not found")
            all_ok = False
        else:
            # Check for shebang
            first_line = script.read_text(encoding="utf-8").split("\n")[0]
            if not first_line.startswith("#!"):
                print(f"  WARN: {script.name} missing shebang line")
            else:
                print(f"  OK: {script.name} (shebang: {first_line})")
    return all_ok


def execute_wc011_04() -> bool:
    """WC011-04: Create src/ directory scaffold with C-059 headers."""
    print("── WC011-04: Create src/ directory scaffold ──")
    services = [
        ("constitutional-engine", "Constitutional Engine"),
        ("business-platform", "Business Platform"),
        ("professional-runtime", "Professional Runtime"),
        ("ai-runtime", "AI Runtime"),
    ]
    for svc_dir, svc_name in services:
        target = REPO_ROOT / "src" / svc_dir
        target.mkdir(parents=True, exist_ok=True)
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# Implements: architecture/reference/components/{svc_dir}.md\n"
                f"# Constitutional basis: C-059 (Implementation Traceability)\n\n"
                f"## {svc_name}\n\n"
                f"Implements: `architecture/reference/components/{svc_dir}.md`\n\n"
                f"## Local Development\n\n"
                f"```bash\ndocker compose up {svc_dir}\n```\n\n"
                f"## Tests\n\n"
                f"Unit tests and CCTs added in Sprint 012+.\n"
            )
            print(f"  Created src/{svc_dir}/README.md")

    git(["add", "src/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-04 - src/ scaffold with C-059 headers\n\n"
             "IB: IB-009\nConstitutional: C-059, C-064\nCCTs-added: none"])
    return True


def execute_wc011_07() -> bool:
    """WC011-07: Document GitHub Actions secrets (OIDC pattern — 2026-07-23)."""
    print("── WC011-07: Document GitHub Actions secrets ──")
    secrets_doc = REPO_ROOT / "infrastructure" / "GITHUB-SECRETS.md"

    # Skip if already contains the OIDC pattern markers — avoids noisy re-commits
    if secrets_doc.exists():
        existing = secrets_doc.read_text(encoding="utf-8")
        if "OIDC + Azure Key Vault" in existing and "ANTHROPIC-API-KEY" in existing:
            print("  OK: GITHUB-SECRETS.md already documents OIDC pattern — no changes needed")
            return True
    secrets_doc.write_text(
        "# GitHub Actions Secrets & Variables — WAOOAW Platform\n"
        "# constitutional_basis: C-059 (Implementation Traceability), ADR-014 (Secret Management)\n"
        "# ib_item: IB-009 (WC011-07)\n"
        "# produced_by: WC011-07 autonomous sprint task\n\n"
        "## Architecture: OIDC + Azure Key Vault (no long-lived credentials in GitHub Secrets)\n\n"
        "Per ADR-014, all secrets live in Azure Key Vault (waooaw-dev-kv).\n"
        "GitHub Actions authenticates to Azure via OIDC (no stored client secret).\n"
        "Non-sensitive config values are GitHub Variables (not Secrets).\n\n"
        "---\n\n"
        "## GitHub Variables (non-sensitive config — Settings → Variables → Actions)\n\n"
        "| Variable | Value | Purpose |\n"
        "|---|---|---|\n"
        "| `AZURE_CLIENT_ID` | App Registration Client ID | OIDC authentication to Azure |\n"
        "| `AZURE_TENANT_ID` | Azure AD Tenant ID | OIDC authentication to Azure |\n"
        "| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | OIDC scope |\n"
        "| `AZURE_KEYVAULT_NAME` | `waooaw-dev-kv` | Key Vault name for secret fetch |\n\n"
        "**Status: All 4 set** (2026-07-23)\n\n"
        "---\n\n"
        "## Azure Key Vault Secrets (fetched at runtime via OIDC — never stored in GitHub)\n\n"
        "| KV Secret Name | Used By | Obtain From | Status |\n"
        "|---|---|---|---|\n"
        "| `ANTHROPIC-API-KEY` | `autonomous-sprint.yaml` execute + review | console.anthropic.com → API Keys | ✅ DONE |\n"
        "| `GH-APP-ID` | `autonomous-sprint.yaml` review | GitHub App waooaw-reviewer | ✅ DONE |\n"
        "| `GH-APP-INSTALLATION-ID` | `autonomous-sprint.yaml` review | GitHub App installation | ✅ DONE |\n"
        "| `GH-APP-PRIVATE-KEY` | `autonomous-sprint.yaml` review | GitHub App private key (.pem) | ✅ DONE |\n"
        "| `CODECOV-TOKEN` | `ci.yaml` coverage upload | codecov.io → repo settings | ✅ DONE |\n"
        "| `DEV_BASE_URL` | `post-deploy-verify.yaml` | Terraform output after M1 | ⬜ PENDING |\n"
        "| `DEV_CONSTITUTIONAL_DB_URL` | `promote.yaml` CCTs | Terraform output after M2 | ⬜ PENDING |\n"
        "| `DEV_TEST_JWT_TENANT_A` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |\n"
        "| `DEV_TEST_JWT_TENANT_B` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |\n"
        "| `GOOGLE-VERTEX-SA-KEY` | AI Runtime (Gemini) | GCP SA key JSON (FA-021) | ⬜ PENDING |\n"
        "| `SARVAM-API-KEY` | AI Runtime (Agricultural) | sarvam.ai API key (FA-022) | ⬜ PENDING |\n"
        "| `AZURE-OPENAI-KEY` | AI Runtime (fallback LLM) | Azure OpenAI UAE North (FA-003) | ⬜ PENDING |\n\n"
        "---\n\n"
        "## Secret Rotation Policy (ADR-014)\n\n"
        "- Azure OIDC: no rotation needed (no client secret — OIDC federated credential)\n"
        "- ANTHROPIC-API-KEY: rotate if exposed in logs or AI context\n"
        "- GH-APP-PRIVATE-KEY: rotate annually or if exposed\n"
        "- All others: rotate if leaked; quarterly audit minimum\n\n"
        "## No Longer Used\n\n"
        "The following were in earlier designs but are replaced by OIDC:\n"
        "- `AZURE_CREDENTIALS_DEV/QA/PROD` — replaced by OIDC federated credential\n"
        "- `REVIEW_APP_TOKEN` — replaced by `GH-APP-PRIVATE-KEY` in Key Vault + JWT generation\n"
    )
    print("  Updated infrastructure/GITHUB-SECRETS.md (OIDC pattern)")

    git(["add", "infrastructure/GITHUB-SECRETS.md"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "chore(infra): WC011-07 - document GitHub Actions secrets (OIDC pattern)\n\n"
             "IB: IB-009\nConstitutional: C-059, ADR-014"])
    return True


def execute_wc012_01() -> bool:
    """
    WC012-01: CE project scaffold — DETERMINISTIC (no LLM call).

    Root cause of 3+ failures: calling Claude to copy reference files produces hallucinations.
    Fix: copy reference files verbatim + write minimal templates. No Claude, no hallucination.

    constitutional_basis: C-059 (Traceability), C-082 (build validation), ADR-001 (gRPC)
    """
    print("── WC012-01: CE project scaffold (DETERMINISTIC) ──")
    service = "constitutional-engine"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / f"{service}.Tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "Protos").mkdir(exist_ok=True)
    (src_dir / "Services").mkdir(exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Copy .csproj verbatim from reference dotfile (C-081) ──────────────
    ref_csproj = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "constitutional-engine.csproj"
    if not ref_csproj.is_file():
        print(f"  ❌ Reference csproj not found: {ref_csproj}")
        return False
    (src_dir / "constitutional-engine.csproj").write_text(ref_csproj.read_text())
    print("  ✅ constitutional-engine.csproj copied from reference dotfile")

    # ── 2. Copy proto verbatim from architecture reference ────────────────────
    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    if not ref_proto.is_file():
        print(f"  ❌ Reference proto not found: {ref_proto}")
        return False
    (src_dir / "Protos" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied from architecture reference")

    # ── 3. Program.cs — minimal template (no OTel hallucination risk) ─────────
    (src_dir / "Program.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md\n"
        "// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry)\n\n"
        "using Waooaw.ConstitutionalEngine.Services;\n\n"
        "var builder = WebApplication.CreateBuilder(args);\n"
        "builder.Services.AddGrpc();\n\n"
        "var app = builder.Build();\n"
        "app.MapGrpcService<ConstitutionalEngineService>();\n"
        "app.Run();\n"
    )
    print("  ✅ Program.cs written from template")

    # ── 4. ConstitutionalEngineService.cs — stub inheriting proto base ─────────
    # All RPCs return default empty responses — stubs only. WC012-02/03/04 fill them.
    (src_dir / "Services" / "ConstitutionalEngineService.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md\n"
        "// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop)\n\n"
        "using Grpc.Core;\n"
        "using Waooaw.ConstitutionalEngine.Grpc;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Services;\n\n"
        "/// <summary>gRPC service stub — full implementation in WC012-02/03/04.</summary>\n"
        "public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase\n"
        "{\n"
        "    public override Task<RecordEvidenceResponse> RecordEvidence(RecordEvidenceRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new RecordEvidenceResponse());\n"
        "    public override Task<ValidateActionResponse> ValidateAction(ValidateActionRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new ValidateActionResponse());\n"
        "    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(GrantAuthorityRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new GrantAuthorityResponse());\n"
        "    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(RevokeAuthorityRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new RevokeAuthorityResponse());\n"
        "    public override Task<EvaluatePolicyResponse> EvaluatePolicy(EvaluatePolicyRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new EvaluatePolicyResponse());\n"
        "    public override Task<EmergencyStopResponse> TriggerEmergencyStop(EmergencyStopRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new EmergencyStopResponse());\n"
        "}\n"
    )
    print("  ✅ ConstitutionalEngineService.cs stub written from template")

    # ── 5. appsettings files ───────────────────────────────────────────────────
    (src_dir / "appsettings.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Information" } },\n'
        '  "ConnectionStrings": { "ConstitutionalDb": "" },\n'
        '  "Kestrel": { "Endpoints": { "Grpc": { "Url": "http://0.0.0.0:5002", "Protocols": "Http2" } } }\n}\n'
    )
    (src_dir / "appsettings.Development.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Debug" } },\n'
        '  "ConnectionStrings": { "ConstitutionalDb": "Host=localhost;Port=5432;Database=constitutional;Username=constitutional_engine;Password=dev_password_replace_in_prod" }\n}\n'
    )
    print("  ✅ appsettings.json + appsettings.Development.json written")

    # ── 6. Test project .csproj ────────────────────────────────────────────────
    (test_dir / "constitutional-engine.Tests.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '    <Nullable>enable</Nullable>\n'
        '    <ImplicitUsings>enable</ImplicitUsings>\n'
        '    <IsPackable>false</IsPackable>\n'
        '  </PropertyGroup>\n'
        '  <ItemGroup>\n'
        '    <ProjectReference Include="..\\..\\src\\constitutional-engine\\constitutional-engine.csproj" />\n'
        '  </ItemGroup>\n'
        '  <ItemGroup>\n'
        '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />\n'
        '    <PackageReference Include="xunit" Version="2.9.3" />\n'
        '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '    <PackageReference Include="Moq" Version="4.20.72" />\n'
        '    <PackageReference Include="FluentAssertions" Version="6.12.2" />\n'
        '    <PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="9.0.0" />\n'
        '    <PackageReference Include="coverlet.collector" Version="6.0.4">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    print("  ✅ constitutional-engine.Tests.csproj written")

    # ── 7. Validate build ──────────────────────────────────────────────────────
    build = run(["dotnet", "build", str(src_dir / "constitutional-engine.csproj"),
                 "--nologo", "-v", "quiet"], check=False, capture=True)
    if build.returncode != 0:
        print(f"  ❌ dotnet build FAILED:\n{build.stderr[:500]}")
        # Clean up on failure so next run starts fresh
        import shutil
        for p in [src_dir / "Protos", src_dir / "Services", src_dir / "Program.cs",
                  src_dir / "appsettings.json", src_dir / "appsettings.Development.json",
                  src_dir / "constitutional-engine.csproj", test_dir]:
            if p.is_dir(): shutil.rmtree(p)
            elif p.is_file(): p.unlink()
        return False
    print("  ✅ dotnet build PASSED")

    # ── 8. Commit ──────────────────────────────────────────────────────────────
    git(["add", "src/constitutional-engine/", "tests/constitutional-engine.Tests/"])
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat: WC012-01 — CE project scaffold (.NET 9 gRPC service)\n\n"
             "IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
    print("  ✅ WC012-01 complete (deterministic — no LLM)")
    return True


def _generate_wc012_02a_evaluator_interfaces() -> bool:
    """
    WC012-02a: Evaluator interface contracts — deterministic templates.
    EvaluationResult, EvaluationContext, IClaimEvaluator, EvaluatorRegistry.
    No business logic — pure structural contracts. Stable regardless of evaluator count.
    constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation)
    """
    print("  ── WC012-02a: Evaluator interfaces (deterministic template) ──")
    ev_dir = REPO_ROOT / "src" / "constitutional-engine" / "Evaluators"
    ev_dir.mkdir(parents=True, exist_ok=True)

    (ev_dir / "EvaluationResult.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-073, C-059\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "/// <summary>Verdict returned by a constitutional claim evaluator.</summary>\n"
        "public enum EvaluationVerdict { Allow, Deny, Escalate }\n\n"
        "/// <summary>Result of a single constitutional claim evaluation.</summary>\n"
        "public sealed record EvaluationResult(\n"
        "    string ClaimId,\n"
        "    EvaluationVerdict Verdict,\n"
        "    string Reason);\n"
    )
    (ev_dir / "EvaluationContext.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-059, C-043, C-062\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "using System.Text.Json;\n"
        "using Waooaw.ConstitutionalEngine.Grpc;\n\n"
        "/// <summary>\n"
        "/// Immutable context derived from ValidateActionRequest + gRPC metadata.\n"
        "/// Exposes all fields evaluators need — no DB access, no external calls.\n"
        "/// TenantId: from gRPC metadata 'x-tenant-id' (not a proto field).\n"
        "/// ActionParameters: JSON-encoded string — use GetParameter(key) to parse.\n"
        "/// Budget fields: from BudgetContext nested proto message.\n"
        "/// </summary>\n"
        "public sealed record EvaluationContext(\n"
        "    string ContractId,\n"
        "    string ActionType,\n"
        "    string ActionParameters,\n"
        "    int DecisionSpaceVersion,\n"
        "    string TenantId,\n"
        "    string? SkillId = null,\n"
        "    long ApprovedBudgetInrPaise = 0,\n"
        "    long CurrentSpendInrPaise = 0,\n"
        "    long ProposedSpendInrPaise = 0,\n"
        "    string BudgetSkillType = \"\")\n"
        "{\n"
        "    /// <summary>\n"
        "    /// Parse a named key from the JSON-encoded ActionParameters string.\n"
        "    /// Evaluators use this instead of treating ActionParameters as a Dictionary.\n"
        "    /// NEVER call .TryGetValue() on ActionParameters — it is a plain string, not a Dictionary.\n"
        "    /// Example: ctx.GetParameter(\"tool_name\") for C-041 tool authorization.\n"
        "    /// </summary>\n"
        "    public string? GetParameter(string key)\n"
        "    {\n"
        "        try\n"
        "        {\n"
        "            using var doc = JsonDocument.Parse(\n"
        "                string.IsNullOrEmpty(ActionParameters) ? \"{}\" : ActionParameters);\n"
        "            return doc.RootElement.TryGetProperty(key, out var val)\n"
        "                ? val.GetString()\n"
        "                : null;\n"
        "        }\n"
        "        catch { return null; }\n"
        "    }\n\n"
        "    /// <summary>\n"
        "    /// Build context from gRPC request + tenant ID extracted from metadata.\n"
        "    /// Called in ConstitutionalEngineService.ValidateAction before passing to evaluators.\n"
        "    /// </summary>\n"
        "    public static EvaluationContext FromRequest(\n"
        "        ValidateActionRequest request, string tenantId) => new(\n"
        "        ContractId:            request.ContractId,\n"
        "        ActionType:            request.ActionType,\n"
        "        ActionParameters:      request.ActionParameters,\n"
        "        DecisionSpaceVersion:  request.DecisionSpaceVersion,\n"
        "        TenantId:              tenantId,\n"
        "        SkillId:               request.HasSkillId ? request.SkillId : null,\n"
        "        ApprovedBudgetInrPaise: request.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0,\n"
        "        CurrentSpendInrPaise:   request.BudgetContext?.CurrentMonthSpendInrPaise ?? 0,\n"
        "        ProposedSpendInrPaise:  request.BudgetContext?.ProposedSpendInrPaise ?? 0,\n"
        "        BudgetSkillType:        request.BudgetContext?.SkillType ?? \"\");\n"
        "}\n"
    )
    (ev_dir / "IClaimEvaluator.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-073\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "/// <summary>\n"
        "/// Constitutional claim evaluator contract.\n"
        "/// Each implementation enforces one constitutional claim against a ValidateAction request.\n"
        "/// </summary>\n"
        "public interface IClaimEvaluator\n"
        "{\n"
        "    string ClaimId { get; }\n"
        "    Task<EvaluationResult> EvaluateAsync(\n"
        "        EvaluationContext context,\n"
        "        CancellationToken cancellationToken = default);\n"
        "}\n"
    )
    (ev_dir / "EvaluatorRegistry.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-073, C-076\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "using Microsoft.Extensions.Logging;\n\n"
        "/// <summary>\n"
        "/// Runs all registered IClaimEvaluator instances in parallel.\n"
        "/// DENY from any evaluator → ValidateAction returns DENY (C-041 default-deny).\n"
        "/// </summary>\n"
        "public sealed class EvaluatorRegistry\n"
        "{\n"
        "    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;\n"
        "    private readonly ILogger<EvaluatorRegistry> _logger;\n\n"
        "    public EvaluatorRegistry(\n"
        "        IEnumerable<IClaimEvaluator> evaluators,\n"
        "        ILogger<EvaluatorRegistry> logger)\n"
        "    {\n"
        "        _evaluators = evaluators.ToList();\n"
        "        _logger = logger;\n"
        "    }\n\n"
        "    public int Count => _evaluators.Count;\n\n"
        "    public async Task<IReadOnlyList<EvaluationResult>> EvaluateAllAsync(\n"
        "        EvaluationContext context,\n"
        "        CancellationToken cancellationToken = default)\n"
        "    {\n"
        "        _logger.LogInformation(\n"
        "            \"Evaluating action {ActionType} for contract {ContractId} against {Count} claims\",\n"
        "            context.ActionType, context.ContractId, _evaluators.Count);\n"
        "        var tasks = _evaluators.Select(e => e.EvaluateAsync(context, cancellationToken));\n"
        "        return await Task.WhenAll(tasks);\n"
        "    }\n"
        "}\n"
    )
    git(["add", "src/constitutional-engine/Evaluators/"], check=False)
    print("  ✅ WC012-02a: 4 interface files written (EvaluationResult, EvaluationContext, IClaimEvaluator, EvaluatorRegistry)")
    return True


def _generate_wc012_02c_prep() -> bool:
    """
    WC012-02c-prep: Write FakeServerCallContext.cs — deterministic test helper.
    DETERMINISTIC — no LLM. Grpc.Core.ServerCallContext abstract members are fixed.
    Splits from WC012-02c because the LLM consistently confuses abstract properties
    with abstract methods (CS0505: cannot override property as method).
    constitutional_basis: C-076 (test coverage), C-082 (build validation)
    """
    tests_dir = REPO_ROOT / "tests" / "constitutional-engine.Tests" / "Evaluators"
    tests_dir.mkdir(parents=True, exist_ok=True)

    (tests_dir / "FakeServerCallContext.cs").write_text(
        "// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests\n"
        "// constitutional_basis: C-076 (test coverage), C-082 (build validation)\n"
        "// DETERMINISTIC: Grpc.Core.ServerCallContext abstract members are\n"
        "// properties (NOT methods) — generated by template to prevent CS0505.\n\n"
        "#nullable enable\n"
        "// using directives MUST precede namespace — Grpc.Core conflicts with\n"
        "// Waooaw.ConstitutionalEngine.Grpc (proto namespace) if placed after.\n"
        "using System;\n"
        "using System.Collections.Generic;\n"
        "using System.Threading;\n"
        "using System.Threading.Tasks;\n"
        "using Grpc.Core;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;\n\n"
        "/// <summary>\n"
        "/// Concrete ServerCallContext for unit tests.\n"
        "/// Moq cannot mock ServerCallContext (abstract protected members are non-virtual).\n"
        "/// All abstract members are PROPERTIES — never override them as methods.\n"
        "/// </summary>\n"
        "public sealed class FakeServerCallContext : ServerCallContext\n"
        "{\n"
        "    private readonly Metadata _requestHeaders;\n"
        "    private readonly Metadata _responseTrailers = new Metadata();\n"
        "    private Status _status;\n"
        "    private WriteOptions? _writeOptions = WriteOptions.Default;\n\n"
        "    /// <summary>Create a context with optional x-tenant-id metadata.</summary>\n"
        "    public static FakeServerCallContext Create(string? tenantId = null) =>\n"
        "        new(tenantId is null\n"
        "            ? new Metadata()\n"
        "            : new Metadata { { \"x-tenant-id\", tenantId } });\n\n"
        "    public FakeServerCallContext(Metadata? requestHeaders = null)\n"
        "        => _requestHeaders = requestHeaders ?? new Metadata();\n\n"
        "    // ── Abstract properties (NOT methods — CS0505 if you use () here) ────\n"
        "    protected override string MethodCore\n"
        "        => \"/constitutional.v1.ConstitutionalService/ValidateAction\";\n"
        "    protected override string HostCore => \"localhost\";\n"
        "    protected override DateTime DeadlineCore => DateTime.MaxValue;\n"
        "    protected override Metadata RequestHeadersCore => _requestHeaders;\n"
        "    protected override CancellationToken CancellationTokenCore\n"
        "        => CancellationToken.None;\n"
        "    protected override string PeerCore => \"ipv4:127.0.0.1:50051\";\n"
        "    protected override Metadata ResponseTrailersCore => _responseTrailers;\n"
        "    protected override AuthContext AuthContextCore\n"
        "        => new AuthContext(null,\n"
        "               new Dictionary<string, List<AuthProperty>>());\n\n"
        "    // ── Abstract methods ────────────────────────────────────────────────\n"
        "    protected override ContextPropagationToken CreatePropagationTokenCore(\n"
        "        ContextPropagationOptions? options)\n"
        "        => throw new NotImplementedException(\"Not required for unit tests.\");\n\n"
        "    protected override Task WriteResponseHeadersAsyncCore(\n"
        "        Metadata responseHeaders)\n"
        "        => Task.CompletedTask;\n\n"
        "    // ── Abstract properties with setters ────────────────────────────────\n"
        "    protected override Status StatusCore\n"
        "    {\n"
        "        get => _status;\n"
        "        set => _status = value;\n"
        "    }\n\n"
        "    protected override WriteOptions? WriteOptionsCore\n"
        "    {\n"
        "        get => _writeOptions;\n"
        "        set => _writeOptions = value;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    print("  ✅ WC012-02c-prep: FakeServerCallContext.cs written (deterministic — all overrides are properties)")
    return True


def _generate_wc012_03a_data_layer() -> bool:
    """
    WC012-03a: Data layer templates — EvidenceRecord + ConstitutionalDbContext.
    DETERMINISTIC — no LLM. Namespace is fixed. Simulation: SIM-PL-002-WC012-03 PASS.
    constitutional_basis: C-027 (append-only), C-023 (Evidence First), C-059 (Traceability)
    """
    print("  ── WC012-03a: Data layer (deterministic template) ──")
    service = "constitutional-engine"
    data_dir = REPO_ROOT / "src" / service / "Data"
    entities_dir = data_dir / "Entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    (entities_dir / "EvidenceRecord.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §1\n"
        "// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), C-059 (Traceability)\n\n"
        "namespace Waooaw.ConstitutionalEngine.Data.Entities;\n\n"
        "/// <summary>Append-only evidence record in the Constitutional Audit Ledger. C-027: never UPDATE or DELETE.</summary>\n"
        "public sealed class EvidenceRecord\n"
        "{\n"
        "    public Guid Id { get; init; } = Guid.NewGuid();\n"
        "    public string IdempotencyKey { get; init; } = string.Empty;\n"
        "    public Guid TenantId { get; init; }\n"
        "    public string EvidenceType { get; init; } = string.Empty;\n"
        "    public string Summary { get; init; } = string.Empty;\n"
        "    public string? PayloadJson { get; init; }\n"
        "    public DateTimeOffset RecordedAt { get; init; } = DateTimeOffset.UtcNow;\n"
        "}\n"
    )
    (data_dir / "ConstitutionalDbContext.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §1\n"
        "// constitutional_basis: C-027 (append-only), C-023 (Evidence First)\n\n"
        "using Microsoft.EntityFrameworkCore;\n"
        "using Waooaw.ConstitutionalEngine.Data.Entities;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Data;\n\n"
        "/// <summary>EF Core context for the Constitutional Audit Ledger. C-027: INSERT only, no UPDATE/DELETE.</summary>\n"
        "public sealed class ConstitutionalDbContext : DbContext\n"
        "{\n"
        "    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options) : base(options) {}\n"
        "    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();\n"
        "}\n"
    )
    git(["add", f"src/{service}/Data/"], check=False)
    print("  ✅ WC012-03a: Data layer written (EvidenceRecord + ConstitutionalDbContext)")
    return True


def _generate_wc012_04a_emergency_stop_entities() -> bool:
    """
    WC012-04a: EmergencyStop entities — EmergencyStopEvent + DbContext.
    DETERMINISTIC — no LLM. Namespace is fixed.
    constitutional_basis: C-001 (Emergency Stop absolute), C-023 (Evidence First), C-027 (append-only)
    """
    print("  ── WC012-04a: EmergencyStop entities (deterministic template) ──")
    service = "constitutional-engine"
    es_dir = REPO_ROOT / "src" / service / "EmergencyStop"
    es_dir.mkdir(parents=True, exist_ok=True)

    (es_dir / "EmergencyStopEvent.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §4\n"
        "// constitutional_basis: C-001 (Emergency Stop absolute), C-023 (Evidence First), C-027 (append-only)\n\n"
        "namespace Waooaw.ConstitutionalEngine.EmergencyStop;\n\n"
        "/// <summary>Append-only evidence record for Emergency Stop events. C-001 + C-027.</summary>\n"
        "public sealed class EmergencyStopEvent\n"
        "{\n"
        "    public Guid Id { get; init; } = Guid.NewGuid();\n"
        "    public Guid ContractId { get; init; }\n"
        "    public string InitiatedByUserId { get; init; } = string.Empty;\n"
        "    public string[] AffectedSessionIds { get; init; } = Array.Empty<string>();\n"
        "    public DateTimeOffset TriggeredAt { get; init; } = DateTimeOffset.UtcNow;\n"
        "    public DateTimeOffset? TemporalSignalledAt { get; set; }\n"
        "    public string StopSource { get; init; } = \"gRPC\";\n"
        "}\n"
    )
    (es_dir / "EmergencyStopDbContext.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §4\n"
        "// constitutional_basis: C-001 (Emergency Stop), C-027 (append-only), C-023 (Evidence First)\n\n"
        "using Microsoft.EntityFrameworkCore;\n\n"
        "namespace Waooaw.ConstitutionalEngine.EmergencyStop;\n\n"
        "/// <summary>EF Core context for Emergency Stop evidence. Append-only per C-027.</summary>\n"
        "public sealed class EmergencyStopDbContext : DbContext\n"
        "{\n"
        "    public EmergencyStopDbContext(DbContextOptions<EmergencyStopDbContext> options) : base(options) {}\n"
        "    public DbSet<EmergencyStopEvent> EmergencyStopEvents => Set<EmergencyStopEvent>();\n"
        "}\n"
    )
    git(["add", f"src/{service}/EmergencyStop/"], check=False)
    print("  ✅ WC012-04a: EmergencyStop entities written")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# WC-013 — Business Platform scaffold
# ══════════════════════════════════════════════════════════════════════════════

def execute_wc013_01() -> bool:
    """
    WC013-01: Business Platform project scaffold — DETERMINISTIC (no LLM).
    Creates src/business-platform/ skeleton + tests/business-platform.Tests/.
    constitutional_basis: C-059 (Traceability), C-082 (build validation), ADR-002 (spec-first)
    """
    print("── WC013-01: BP project scaffold (DETERMINISTIC) ──")
    service = "business-platform"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / f"{service}.Tests"
    (src_dir / "Controllers").mkdir(parents=True, exist_ok=True)
    (src_dir / "Services").mkdir(parents=True, exist_ok=True)
    (src_dir / "Models").mkdir(parents=True, exist_ok=True)
    (src_dir / "Data").mkdir(parents=True, exist_ok=True)
    (src_dir / "Protos").mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy .csproj from reference dotfile
    ref_csproj = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "business-platform.csproj"
    (src_dir / "business-platform.csproj").write_text(ref_csproj.read_text())
    print("  ✅ business-platform.csproj copied from reference dotfile")

    # 2. Copy CE proto verbatim (BP needs it for gRPC client code-gen)
    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    (src_dir / "Protos" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied (gRPC client target)")

    # 3. Program.cs — minimal stub (JWT + EF + gRPC + RLS wired in WC013-02)
    (src_dir / "Program.cs").write_text(
        "// Implements: architecture/reference/components/business-platform.md\n"
        "// constitutional_basis: ADR-002 (spec-first), ADR-003 (JWT tenancy), C-026 (RLS), C-023\n\n"
        "using Waooaw.BusinessPlatform.Controllers;\n\n"
        "var builder = WebApplication.CreateBuilder(args);\n"
        "builder.Services.AddControllers();\n"
        "builder.Services.AddEndpointsApiExplorer();\n"
        "builder.Services.AddSwaggerGen();\n\n"
        "var app = builder.Build();\n"
        "app.UseSwagger();\n"
        "app.UseSwaggerUI();\n"
        "app.MapControllers();\n"
        "app.Run();\n"
    )
    print("  ✅ Program.cs stub written")

    # 4. Minimal controller stubs (ADR-002: spec-first — full impl in WC013-02/03)
    (src_dir / "Controllers" / "CustomersController.cs").write_text(
        "// Implements: architecture/reference/api-specs/business-platform.openapi.yaml\n"
        "// constitutional_basis: ADR-002 (spec-first), C-023 (Evidence First), C-038 (pro-rata)\n\n"
        "using Microsoft.AspNetCore.Mvc;\n\n"
        "namespace Waooaw.BusinessPlatform.Controllers;\n\n"
        "[ApiController, Route(\"api/v1\")]\n"
        "public sealed class CustomersController : ControllerBase\n"
        "{\n"
        "    [HttpPost(\"employment/contracts\")]\n"
        "    public IActionResult FormEmploymentContract() => Ok();\n\n"
        "    [HttpGet(\"employment/contracts/{id}\")]\n"
        "    public IActionResult GetEmploymentContract(Guid id) => Ok();\n"
        "}\n"
    )
    print("  ✅ CustomersController.cs stub written")

    # 5. appsettings
    (src_dir / "appsettings.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Information" } },\n'
        '  "ConnectionStrings": { "BusinessPlatformDb": "" },\n'
        '  "ConstitutionalEngine": { "GrpcUrl": "http://constitutional-engine:5002" },\n'
        '  "Jwt": { "Authority": "", "Audience": "business-platform" },\n'
        '  "Kestrel": { "Endpoints": { "Rest": { "Url": "http://0.0.0.0:5001" } } }\n}\n'
    )
    (src_dir / "appsettings.Development.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Debug" } },\n'
        '  "ConnectionStrings": { "BusinessPlatformDb": "Host=localhost;Port=5432;Database=waooaw;Username=business_platform;Password=dev_password_replace_in_prod" },\n'
        '  "ConstitutionalEngine": { "GrpcUrl": "http://localhost:5002" },\n'
        '  "Jwt": { "Authority": "http://localhost:8080/realms/waooaw" }\n}\n'
    )
    print("  ✅ appsettings.json + appsettings.Development.json written")

    # 6. Tests .csproj
    (test_dir / "business-platform.Tests.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '    <Nullable>enable</Nullable>\n'
        '    <ImplicitUsings>enable</ImplicitUsings>\n'
        '    <IsPackable>false</IsPackable>\n'
        '  </PropertyGroup>\n'
        '  <ItemGroup>\n'
        '    <ProjectReference Include="..\\..\\src\\business-platform\\business-platform.csproj" />\n'
        '  </ItemGroup>\n'
        '  <ItemGroup>\n'
        '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />\n'
        '    <PackageReference Include="xunit" Version="2.9.3" />\n'
        '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '    <PackageReference Include="Moq" Version="4.20.72" />\n'
        '    <PackageReference Include="FluentAssertions" Version="6.12.2" />\n'
        '    <PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="9.0.1" />\n'
        '    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="9.0.0" />\n'
        '    <PackageReference Include="coverlet.collector" Version="6.0.4">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    print("  ✅ business-platform.Tests.csproj written")

    # 7. Build validate
    build = run(["dotnet", "build", str(src_dir / "business-platform.csproj"),
                 "--nologo", "-v", "quiet"], check=False, capture=True)
    if build.returncode != 0:
        print(f"  ❌ dotnet build FAILED:\n{build.stderr[:500]}")
        return False
    print("  ✅ dotnet build PASSED")

    git(["add", f"src/{service}/", f"tests/{service}.Tests/"], check=False)
    git(["commit", "-m",
         "feat: WC013-01 — BP project scaffold (.NET 9 REST + gRPC client to CE)\n\n"
         "IB: IB-009\nConstitutional: C-059, ADR-002, ADR-003, C-026\nCCTs-added: per WC spec"],
        check=False)
    print("  ✅ WC013-01 complete (deterministic — no LLM)")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# WC-014 — Professional Runtime scaffold (Python)
# ══════════════════════════════════════════════════════════════════════════════

def execute_wc014_01() -> bool:
    """
    WC014-01: Professional Runtime project scaffold — DETERMINISTIC (no LLM).
    Creates src/professional-runtime/ Python FastAPI skeleton + tests/.
    constitutional_basis: C-059, C-025 (PAAS exclusive), ADR-015 (Temporal)
    """
    print("── WC014-01: PR project scaffold (DETERMINISTIC) ──")
    service = "professional-runtime"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / service
    (src_dir / "routers").mkdir(parents=True, exist_ok=True)
    (src_dir / "workflows").mkdir(parents=True, exist_ok=True)
    (src_dir / "activities").mkdir(parents=True, exist_ok=True)
    (src_dir / "proto").mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy requirements.txt from reference
    ref_req = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "requirements-professional-runtime.txt"
    (src_dir / "requirements.txt").write_text(ref_req.read_text())
    print("  ✅ requirements.txt copied from reference dotfile")

    # 2. requirements-test.txt
    (src_dir / "requirements-test.txt").write_text(
        "# Test dependencies for professional-runtime\n"
        "pytest==8.3.4\n"
        "pytest-asyncio==0.24.0\n"
        "pytest-cov==6.0.0\n"
        "httpx==0.27.2\n"
        "respx==0.21.1\n"
    )
    print("  ✅ requirements-test.txt written")

    # 3. Copy CE proto (gRPC client)
    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    (src_dir / "proto" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied (gRPC client target)")

    # 4. Package init
    (src_dir / "__init__.py").write_text(
        "# Professional Runtime — C-025 (PAAS exclusive execution model)\n"
    )
    (test_dir / "__init__.py").write_text("")

    # 5. main.py — minimal FastAPI stub
    (src_dir / "main.py").write_text(
        "# Implements: architecture/reference/components/professional-runtime.md\n"
        "# constitutional_basis: C-025 (PAAS exclusive), C-001 (Emergency Stop ≤250ms),\n"
        "#   ADR-015 (Temporal), ADR-018 (Emergency Stop signal)\n\n"
        "from fastapi import FastAPI\n\n"
        "app = FastAPI(\n"
        "    title=\"WAOOAW Professional Runtime\",\n"
        "    description=\"PAAS execution engine (C-025). All professional work runs here.\",\n"
        "    version=\"0.1.0\",\n"
        ")\n\n\n"
        "@app.get(\"/health\")\n"
        "async def health() -> dict:\n"
        "    \"\"\"Health check.\"\"\"\n"
        "    return {\"status\": \"ok\", \"service\": \"professional-runtime\"}\n"
    )
    print("  ✅ main.py stub written")

    # 6. conftest.py for tests
    (test_dir / "conftest.py").write_text(
        "# Implements: tests/QA-STRATEGY.md §5.1\n"
        "# constitutional_basis: C-076 (≥90% coverage)\n\n"
        "import pytest\n"
        "from httpx import AsyncClient, ASGITransport\n"
        "from src.professional_runtime.main import app\n\n\n"
        "@pytest.fixture\n"
        "async def client():\n"
        "    async with AsyncClient(transport=ASGITransport(app=app), base_url=\"http://test\") as c:\n"
        "        yield c\n"
    )
    print("  ✅ tests/conftest.py written")

    # 7. Lint check (ruff) — no dotnet build for Python
    lint = run(["python3", "-m", "ruff", "check", str(src_dir)],
               check=False, capture=True)
    if lint.returncode != 0:
        print(f"  ⚠️  ruff: {lint.stdout[:200]}")
    else:
        print("  ✅ ruff PASSED")

    git(["add", f"src/{service}/", f"tests/{service}/"], check=False)
    git(["commit", "-m",
         "feat: WC014-01 — PR project scaffold (Python 3.12 FastAPI + Temporal worker)\n\n"
         "IB: IB-009\nConstitutional: C-059, C-025, ADR-015\nCCTs-added: per WC spec"],
        check=False)
    print("  ✅ WC014-01 complete (deterministic — no LLM)")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# WC-015 — AI Runtime scaffold (Python)
# ══════════════════════════════════════════════════════════════════════════════

def execute_wc015_01() -> bool:
    """
    WC015-01: AI Runtime project scaffold — DETERMINISTIC (no LLM).
    Creates src/ai-runtime/ Python FastAPI skeleton + tests/.
    constitutional_basis: C-059, C-051 (Token Economy), C-062 (AI Security), C-063, C-078
    """
    print("── WC015-01: AIR project scaffold (DETERMINISTIC) ──")
    service = "ai-runtime"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / service
    (src_dir / "providers").mkdir(parents=True, exist_ok=True)
    (src_dir / "pse").mkdir(parents=True, exist_ok=True)
    (src_dir / "rag").mkdir(parents=True, exist_ok=True)
    (src_dir / "pii").mkdir(parents=True, exist_ok=True)
    (src_dir / "proto").mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy requirements.txt from reference
    ref_req = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "requirements-ai-runtime.txt"
    (src_dir / "requirements.txt").write_text(ref_req.read_text())
    print("  ✅ requirements.txt copied from reference dotfile")

    # 2. requirements-test.txt
    (src_dir / "requirements-test.txt").write_text(
        "# Test dependencies for ai-runtime\n"
        "pytest==8.3.4\n"
        "pytest-asyncio==0.24.0\n"
        "pytest-cov==6.0.0\n"
        "httpx==0.27.2\n"
        "respx==0.21.1\n"
    )
    print("  ✅ requirements-test.txt written")

    # 3. Copy CE proto
    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    (src_dir / "proto" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied")

    # 4. Package inits
    (src_dir / "__init__.py").write_text(
        "# AI Runtime — C-051 (Token Economy), C-062 (AI Security), C-078 (PII Scrubber)\n"
    )
    (src_dir / "providers" / "__init__.py").write_text("")
    (src_dir / "pse" / "__init__.py").write_text("")
    (src_dir / "rag" / "__init__.py").write_text("")
    (src_dir / "pii" / "__init__.py").write_text("")
    (test_dir / "__init__.py").write_text("")

    # 5. main.py — minimal FastAPI stub
    (src_dir / "main.py").write_text(
        "# Implements: architecture/reference/components/ai-runtime.md\n"
        "# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),\n"
        "#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)\n\n"
        "from fastapi import FastAPI\n\n"
        "app = FastAPI(\n"
        "    title=\"WAOOAW AI Runtime\",\n"
        "    description=\"Provider Selection Engine + LLM dispatch (ADR-029).\",\n"
        "    version=\"0.1.0\",\n"
        ")\n\n\n"
        "@app.get(\"/health\")\n"
        "async def health() -> dict:\n"
        "    \"\"\"Health check.\"\"\"\n"
        "    return {\"status\": \"ok\", \"service\": \"ai-runtime\"}\n"
    )
    print("  ✅ main.py stub written")

    # 6. PSE tier enum stub (ADR-029) — prevents LLM from inventing tier names
    (src_dir / "pse" / "tiers.py").write_text(
        "# Implements: adr/ADR-029-multi-provider-llm-strategy.md\n"
        "# constitutional_basis: C-051 (Token Economy — 66-74% cost reduction)\n"
        "# PSE-R01 to PSE-R08 routing rules defined here.\n\n"
        "from enum import Enum\n\n\n"
        "class LlmTier(str, Enum):\n"
        "    \"\"\"ADR-029 §3 routing tiers. NEVER add tiers without EA approval.\"\"\"\n"
        "    LOCAL = \"local\"        # Ollama (₹0/token) — default for dev\n"
        "    MID = \"mid\"            # Sarvam AI (Indian SMEs, optimised cost)\n"
        "    FRONTIER = \"frontier\"  # Gemini / Anthropic (complex reasoning)\n"
        "    FALLBACK = \"fallback\"  # Anthropic Claude (when Gemini unavailable)\n"
    )
    print("  ✅ pse/tiers.py stub written (ADR-029 tiers)")

    # 7. conftest.py for tests
    (test_dir / "conftest.py").write_text(
        "# Implements: tests/QA-STRATEGY.md §5.1\n"
        "# constitutional_basis: C-076 (≥90% coverage), C-062 (AI Security)\n\n"
        "import pytest\n"
        "from httpx import AsyncClient, ASGITransport\n"
        "from src.ai_runtime.main import app\n\n\n"
        "@pytest.fixture\n"
        "async def client():\n"
        "    async with AsyncClient(transport=ASGITransport(app=app), base_url=\"http://test\") as c:\n"
        "        yield c\n"
    )
    print("  ✅ tests/conftest.py written")

    # 8. Lint check
    lint = run(["python3", "-m", "ruff", "check", str(src_dir)],
               check=False, capture=True)
    if lint.returncode != 0:
        print(f"  ⚠️  ruff: {lint.stdout[:200]}")
    else:
        print("  ✅ ruff PASSED")

    git(["add", f"src/{service}/", f"tests/{service}/"], check=False)
    git(["commit", "-m",
         "feat: WC015-01 — AIR project scaffold (Python 3.12 FastAPI + PSE tiers)\n\n"
         "IB: IB-009\nConstitutional: C-059, C-051, C-062, C-078, ADR-029\nCCTs-added: per WC spec"],
        check=False)
    print("  ✅ WC015-01 complete (deterministic — no LLM)")
    return True


def _skip_schemathesis_gate() -> bool:
    """
    WC013-04a: Schemathesis contract test — CI gate deferred.
    Schemathesis requires a running docker-compose service stack.
    In the autonomous sprint pipeline (GitHub Actions, no docker), this gate
    is recorded as SKIPPED with an instruction to run manually.
    constitutional_basis: C-008 (Constitutional Chain — spec-code drift check)
    """
    print("  ── WC013-04a: Schemathesis gate (CI-deferred) ──")
    print("  ⏭️  Schemathesis requires running service — deferred to manual docker-compose run.")
    print("  Manual command: docker compose up business-platform && schemathesis run "
          "architecture/reference/api-specs/business-platform.openapi.yaml "
          "--url http://localhost:5001 --checks all")
    # Record skip in sprint-context for monitor
    skip_file = REPO_ROOT / "sprint-context" / "schemathesis-deferred.txt"
    skip_file.parent.mkdir(exist_ok=True)
    skip_file.write_text(
        "WC013-04 Schemathesis deferred — run manually after WC-013 completes.\n"
        "Command: docker compose up business-platform && "
        "schemathesis run architecture/reference/api-specs/business-platform.openapi.yaml "
        "--url http://localhost:5001 --checks all\n"
    )
    git(["add", "sprint-context/schemathesis-deferred.txt"], check=False)
    git(["commit", "-m",
         "chore(pm): WC013-04 Schemathesis gate deferred — requires running service\n\n"
         "IB: IB-009\nConstitutional: C-008 (tracked, not blocking)"],
        check=False)
    return True


_INFRA_ERROR_TASKS: list[str] = []  # populated by execute_with_llm when all 3 attempts are API failures

# ── Sprint Monitor signal (C-069: self-improvement loop) ──────────────────────
# Scaffold tasks are EXPLICITLY declared — never inferred from position.
# If WC012-01 fails, all downstream tasks cannot compile. The monitor uses this
# to distinguish CASCADE_PIPELINE_BUG from SPEC_GAP_GENUINE.
SCAFFOLD_TASKS: frozenset[str] = frozenset({
    "WC012-01", "WC013-01", "WC014-01", "WC015-01",
    "WC016-01", "WC017-01", "WC018-01",
})

# Populated during execution — written to sprint-context/monitor-signal.json
# and uploaded as artifact for the Constitutional Monitor job to consume.
_MONITOR_SIGNAL: dict = {
    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "sprint": "",
    "scaffold_task": None,     # task ID of the scaffold (if any) in this run
    "scaffold_failed": False,  # True = downstream spec-gap issues are CASCADE bugs
    "task_results": {},        # per-task: result, error_type, snippet, attempts, issue
    "spec_gap_issues": [],     # GitHub issue numbers opened by flag_spec_gap()
    "overall_result": "UNKNOWN",
}

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
                    "Namespace: Waooaw.BusinessPlatform.Controllers and Waooaw.BusinessPlatform.Services."
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
                compile_gate="pytest",
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
                compile_gate="pytest",
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
    integrity_ok, integrity_errors = run_runner_integrity_checks()
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
                )
            else:
                print(f"  ⚠️  TASK_NOT_IMPLEMENTED: {task} — unknown handler format")
                tasks_not_implemented.append(task)
                continue
            if success:
                tasks_done.append(task)
                # RC#2: Write tasks_done/tasks_remaining to PROJECT_STATE.md after each success.
                # Prevents duplicate re-execution across cron runs on the same open PR.
                # C-083 (Emit-Transport-Listen), C-059 (Traceability), C-085 (Idempotency)
                all_remaining = [t for t in state.get("tasks_remaining", []) if t not in tasks_done]
                run([sys.executable, "scripts/sprint_state.py", "set-list", "tasks_done"] + tasks_done)
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

    git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             f"chore(pm): {sprint} tasks done: {', '.join(tasks_done)}\n\n"
             f"IB: IB-009\nConstitutional: C-059"])

    # Push sprint branch — use -u (set upstream) not --force-with-lease.
    # --force-with-lease fails when no remote tracking ref exists (new branch).
    # Use capture=True so stderr/stdout are always available for safe diagnostics.
    push = run(["git", "push", "-u", "origin", branch], check=False, capture=True)
    if push.returncode != 0:
        push_err = (push.stderr or push.stdout or "").strip()
        print(f"  WARN: branch push failed (non-fatal): {push_err[:200]}")
        # Retry once with --force in case of ref mismatch.
        force_push = run(["git", "push", "--force", "origin", branch], check=False, capture=True)
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
    signal_path = Path("sprint-context/monitor-signal.json")
    signal_path.parent.mkdir(exist_ok=True)
    import json as _json
    signal_path.write_text(_json.dumps(_MONITOR_SIGNAL, indent=2))
    print(f"  📡 Monitor signal emitted: {signal_path}")
    # Scalar outputs consumed directly by the monitor job
    set_output("scaffold_failed", str(scaffold_failed).lower())
    set_output("infra_error_tasks", ",".join(str(t) for t in infra_error_tasks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
