# Implements: scripts/runner/system_prompts.py
# constitutional_basis: C-059, C-073, C-076, C-077
# ib_item: IB-009
"""
Constitutional system prompt and stack-specific expert blocks.

_build_system_prompt(task_id) is the single source of the LLM system prompt —
base obligations + selected stack expert block.
get_branch_context() scans the sprint branch and injects EXTEND-NOT-REPLACE
context into every LLM call.
"""
from __future__ import annotations

import os
import re

from runner.constants import REPO_ROOT
from runner.git_ops import run

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

# Stack selection map — keyed by stack name
_STACK_EXPERTS: dict[str, str] = {
    "dotnet":     _EXPERT_DOTNET,
    "python":     _EXPERT_PYTHON,
    "terraform":  _EXPERT_TERRAFORM,
    "typescript": _EXPERT_TYPESCRIPT,
}

# Task-prefix → stack mapping (extend as new sprints are planned)
_TASK_STACK_MAP: dict[str, str] = {
    "WC012": "dotnet",     # Constitutional Engine (.NET 9 gRPC)
    "WC013": "dotnet",     # Business Platform skeleton
    "WC014": "python",     # Temporal workers
    "WC015": "python",     # FastAPI services / RAG
    "WC016": "terraform",  # Infrastructure
    "WC017": "typescript", # Web (Next.js)
    "WC018": "dotnet",     # Integration tests
    "WC025": "python",     # Wallet & Billing Engine (WBE)
    "WC026": "python",     # WBE Wallet Engine (buckets, reserve, release)
    "WC027": "python",     # WBE future sprints
    "WC028": "python",
    "WC029": "python",
    "WC030": "python",
    "WC031": "python",
    "WC032": "python",
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

    C-083 (Emit-Transport-Listen): the branch state IS the signal from prior tasks.
    C-085 (Idempotency): the LLM must check existing state before acting.

    RCA-fix (2026-07-29): Added two generator-level fixes:
    1. Cross-service boundary filter — CE-internal files are excluded from BP prompts.
       Root cause of CS0234 in WC013-02: branch context injected CE Evaluator files
       (EvaluationContext.cs, IClaimEvaluator.cs) into BP LLM call. LLM imported their
       namespace. Fix: filter by the task's own service directory only.
    2. Full record/DTO signature extraction — previously capped at 30 declaration lines,
       silently truncating multi-field records. Root cause of CS7036 (missing EmploymentContractDto
       constructor args). Fix: capture complete record positional constructor signatures.
    """
    # ── Service boundary map: task_prefix → which src/ subdirs are IN-SCOPE ──────
    # Only files within the task's own service are injected as context.
    # CE-internal files are NEVER injected into BP prompts (and vice versa).
    _SERVICE_SCOPE: dict[str, list[str]] = {
        "WC012": ["src/constitutional-engine/", "tests/constitutional-engine.Tests/"],
        "WC013": ["src/business-platform/", "tests/business-platform.Tests/"],
        "WC014": ["src/professional-runtime/", "tests/"],
        "WC015": ["src/ai-runtime/", "tests/"],
        "WC016": ["infrastructure/"],
        "WC017": ["web/"],
        "WC018": ["src/", "tests/"],  # integration — cross-service by design
        "WC025": ["src/billing-engine/", "tests/billing-engine/"],
        "WC026": ["src/billing-engine/", "tests/billing-engine/"],
        "WC027": ["src/billing-engine/", "tests/billing-engine/"],
    }

    task_id = os.environ.get("SPRINT_TASK_ID", "")
    task_prefix = task_id[:5] if task_id else ""
    allowed_prefixes = _SERVICE_SCOPE.get(task_prefix, [])  # empty = no filter

    try:
        # Find all code files added/modified on this branch vs main
        result = run(["git", "diff", "--name-only", "origin/main...HEAD"], check=False, capture=True)
        if result.returncode != 0:
            return ""

        branch_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        code_files = [f for f in branch_files if f.endswith((".cs", ".py", ".ts", ".proto", ".csproj"))]

        # ── Cross-service boundary filter ──────────────────────────────────────────
        if allowed_prefixes:
            filtered = [f for f in code_files if any(f.startswith(p) for p in allowed_prefixes)]
            excluded = len(code_files) - len(filtered)
            if excluded:
                print(f"  BRANCH CONTEXT: filtered {excluded} out-of-scope file(s) (service boundary {task_prefix})")
            code_files = filtered

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

            # ── Full record/DTO signature extraction (RCA-fix: CS7036 prevention) ──
            # Previously: 30 declaration-line cap silently truncated multi-field records.
            # Now: record and class declarations captured in full until the closing paren/brace.
            important_lines = []
            in_record_signature = False
            paren_depth = 0

            for line in content.splitlines():
                stripped = line.strip()

                # Capture full positional record constructors (multi-line)
                if in_record_signature:
                    important_lines.append(line)
                    paren_depth += line.count("(") - line.count(")")
                    if paren_depth <= 0:
                        in_record_signature = False
                    if len(important_lines) > 60:  # hard cap per file
                        break
                    continue

                if any(stripped.startswith(kw) for kw in (
                    "namespace ", "public ", "internal ", "protected ", "private ",
                    "// Implements:", "// constitutional_basis:", "interface ", "record ",
                    "sealed class", "abstract class", "static class",
                )):
                    important_lines.append(line)
                    # Detect start of multi-line record/positional constructor
                    if re.match(r".*\brecord\b.*\($", stripped) or (
                        stripped.startswith("public sealed record") and "(" in stripped
                        and stripped.count("(") > stripped.count(")")
                    ):
                        in_record_signature = True
                        paren_depth = stripped.count("(") - stripped.count(")")

                    if len(important_lines) > 60:  # cap per file
                        break

            if important_lines:
                lines.append(f"## EXISTING (may EXTEND but not duplicate): {file_path}")
                lines.append("\n".join(important_lines[:60]))
                lines.append("")

        if len(lines) <= 4:  # only header, no files
            return ""

        lines.append("# ═══ END BRANCH CONTEXT ═══\n")
        return "\n".join(lines)

    except Exception as e:
        print(f"  WARN: get_branch_context failed: {e}")
        return ""
