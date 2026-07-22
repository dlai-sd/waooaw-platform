# WAOOAW Coding Standards

**Version:** 1.0
**Date:** 2026-07-19
**Authority:** C-072 (Coding Standards Obligation — RATIFIED), C-071 (Quality Obligation)
**Owner:** WAOOAW AI Agent — Platform IT Expert (enforcement) · Enterprise Architect (ownership)
**Applies to:** All code in `src/`, `web/`, `scripts/`, `tests/`, `infrastructure/`
**Stack:** .NET 9 (CE + BP) · Python 3.12 (PR + AIR) · TypeScript/Next.js 14 (Web) · PostgreSQL 16 · Proto3

---

## The Single Rule

> **Automated tools decide style. Humans and agents decide logic.**

No agent debates formatting. No PR review discusses tabs vs spaces. The tools in this document are the authority. Configure once, enforce forever.

---

## 1. Universal — All Languages

### 1.1 Formatting (.editorconfig — root of repo)

All editors and CI tools read `.editorconfig`. No per-editor configuration is needed.

```ini
# See .editorconfig at repo root
indent_style = space
indent_size = 4          # .NET, Python, SQL
# TypeScript: 2 spaces (see biome.json)
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
max_line_length = 120    # enforced by all formatters
```

### 1.2 File Naming Convention

| Artifact | Convention | Example |
|---|---|---|
| .NET class files | PascalCase.cs | `ClaimEvaluator.cs` |
| Python modules | snake_case.py | `provider_selection_engine.py` |
| TypeScript components | PascalCase.tsx | `EmergencyStopButton.tsx` |
| TypeScript non-component | camelCase.ts | `apiClient.ts` |
| SQL migrations | `NN-description.sql` | `07-agent-prompts.sql` |
| Proto files | snake_case.proto | `constitutional_service.proto` |
| Test files .NET | `{Class}Tests.cs` | `ClaimEvaluatorTests.cs` |
| Test files Python | `test_{module}.py` | `test_provider_selection.py` |
| Test files TypeScript | `{Component}.test.tsx` | `EmergencyStopButton.test.tsx` |

### 1.3 Constitutional Naming — Mandatory

Code that implements a constitutional principle MUST reference the claim in its name or docstring.

```csharp
// ✓ — Clear constitutional naming
public class EvidenceFirstEnforcer { }          // C-023
public class TenantIsolationMiddleware { }      // C-005, ADR-003
public async Task ValidateActionAsync(...)       // C-041

// ✗ — Never
public class DataProcessor { }                  // What data? What processing?
public async Task CheckStuff(...)               // Check what?
```

### 1.4 No Magic Numbers or Strings

All constitutional constants are named and source-referenced:

```csharp
// ✓
private const int EmergencyStopSlaMs = 250;     // C-001: constitutional floor
private const int CeValidateActionSlaMs = 40;   // ADR-001 latency budget

// ✗
if (latency > 250) { ... }                       // Why 250? What claim?
```

### 1.5 Structured Comments

Every file must have a header comment stating purpose and constitutional basis:

```csharp
// Constitutional basis: C-023 (Evidence First), C-041 (Tool Authorization)
// Purpose: Evaluates whether a proposed MCP tool call is within the customer's Decision Space
// ADR reference: ADR-001 (gRPC), ADR-020 (MCP pattern)
```

---

## 2. .NET 9 — Constitutional Engine + Business Platform

### 2.1 Tools (CI-enforced, agents install locally)

| Tool | Version | Purpose | Config |
|---|---|---|---|
| **CSharpier** | 0.28+ | Opinionated formatter — no arguments | `.csharpierrc` |
| **Roslyn Analyzers** | .NET 9 built-in | Code quality rules | `Directory.Build.props` |
| **StyleCop.Analyzers** | 1.2+ | Naming + layout rules | `.editorconfig` (SA rules) |
| **SonarAnalyzer.CSharp** | 10.x | Security + performance patterns | NuGet |
| **Microsoft.CodeAnalysis.NetAnalyzers** | 9.x | .NET best practices | Built-in |
| **Coverlet** | 6.x | Code coverage | `dotnet test --collect` |
| **Stryker.NET** | 4.x | Mutation testing | `stryker-config.json` |

### 2.2 Naming Conventions

```csharp
// Types
public class ClaimEvaluatorRegistry         // PascalCase
public interface IClaimEvaluator            // I prefix for interfaces
public enum EvaluationDecision              // PascalCase enum
public record EvaluationResult(...)         // Records for value objects

// Members
public async Task<EvaluationResult> EvaluateAsync(...)  // PascalCase methods
private readonly IClaimEvaluator _evaluator;             // _camelCase for private fields
public string ClaimId { get; }                           // PascalCase properties
private int _failureCount;                               // _camelCase

// Parameters + locals
var evaluationContext = BuildContext(...);               // camelCase locals
string claimId = request.ClaimId;                       // camelCase params
```

### 2.3 Async Rules (Performance — constitutional latency floors)

```csharp
// ✓ — Async all the way (CE has 40ms P99 budget — blocking = constitutional violation)
public async Task<EvaluationResult> EvaluateAsync(
    EvaluationContext ctx, CancellationToken ct)
{
    var contract = await _db.GetActiveContractAsync(ctx.TenantId, ct);
    return contract is null
        ? EvaluationResult.Deny("No active contract — C-041")
        : EvaluationResult.Authorized();
}

// ✗ — NEVER sync-over-async (blocks thread pool, starves CE under load)
var contract = _db.GetActiveContractAsync(ctx.TenantId).Result;   // FORBIDDEN
var contract = _db.GetActiveContractAsync(ctx.TenantId).GetAwaiter().GetResult();  // FORBIDDEN
```

### 2.4 Error Handling

```csharp
// ✓ — Constitutional errors surface as typed results, not exceptions in hot paths
public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
{
    // Use Result<T> or discriminated union pattern for expected failures
    var contract = await GetContractAsync(ctx.TenantId, ct);
    if (contract is null) return EvaluationResult.Deny("C-041: no active contract");

    // Exceptions only for truly unexpected conditions
    throw new ConstitutionalViolationException(
        "C-023: Evidence write failed — this is a platform-level failure, not a user error");
}

// ✗ — Never catch-and-swallow in constitutional code paths
try { await _ce.RecordEvidenceAsync(...); }
catch { /* ignore */ }   // FORBIDDEN — Evidence First silently broken
```

### 2.5 Performance Rules (.NET)

```csharp
// ✓ — Use ReadOnlySpan for string processing in CE hot path
private static bool IsToolAuthorized(ReadOnlySpan<char> toolName, IReadOnlySet<string> authorized)
    => authorized.Contains(toolName.ToString());

// ✓ — Pre-compile regex (CE ValidateAction runs every LLM call)
private static readonly Regex PromptInjectionPattern =
    new(@"ignore.*previous.*instructions", RegexOptions.Compiled | RegexOptions.IgnoreCase);

// ✗ — Never allocate in hot path (40ms CE budget)
var tools = new List<string>();   // In a loop called 1000x/second
```

### 2.6 Security (.NET)

```csharp
// ✓ — Parameterized queries (ALWAYS — SQL injection prevention OWASP A03)
var contract = await _db.QueryFirstOrDefaultAsync<Contract>(
    "SELECT * FROM business.employment_contracts WHERE tenant_id = @tenantId",
    new { tenantId = ctx.TenantId });

// ✓ — JWT validation before trusting any claim
var principal = _jwtValidator.ValidateAndGetPrincipal(token);
// NEVER: var tenantId = request.Headers["X-Tenant-Id"]  — unsanitized

// ✓ — Never log sensitive data
_logger.LogInformation("ValidateAction for session {SessionId} agent {AgentType}",
    request.SessionId, request.AgentType);
// ✗ — NEVER:
_logger.LogDebug("Request body: {Body}", JsonSerializer.Serialize(request));  // May contain PII
```

### 2.7 Logging (.NET)

```csharp
// Structured logging with Microsoft.Extensions.Logging — NO string interpolation
// ✓ — Message template with named placeholders (enables structured log indexing)
_logger.LogInformation(
    "CE.ValidateAction {Decision} for session {SessionId} tenant {TenantIdHash} in {ElapsedMs}ms. Claim: {ClaimId}",
    result.Decision, sessionId, Hash(tenantId), elapsed, result.ClaimId);

// Log levels (mandatory semantics):
// TRACE:    Low-level debugging, never in production
// DEBUG:    Diagnostic info, disabled in prod by default
// INFO:     Normal operations (every CE call at INFO)
// WARN:     Unexpected but recoverable (C-049 escalation, PSE fallback)
// ERROR:    Action failed, operation did not complete (CCT failure, evidence write error)
// CRITICAL: Constitutional violation, system integrity at risk (Emergency Stop breach, C-048)

// ✓ — Constitutional context in every log entry
using var scope = _logger.BeginScope(new {
    TenantIdHash = Hash(tenantId),  // Hashed — never raw tenant_id in logs
    SessionId = sessionId,
    ConstitutionalClaim = "C-041"
});
```

### 2.8 OTel Tracing (.NET)

```csharp
// Every public method in CE/BP that crosses a service boundary has a span
private static readonly ActivitySource _activitySource = new("waooaw.ce");

public async Task<ValidateActionResponse> ValidateActionAsync(ValidateActionRequest request, ...)
{
    using var activity = _activitySource.StartActivity("ce.validate_action");
    activity?.SetTag("waooaw.session_id", request.SessionId);
    activity?.SetTag("waooaw.agent_type", request.ProposedBy);
    activity?.SetTag("waooaw.tool_name", request.ToolName);
    activity?.SetTag("waooaw.tenant_id_hash", Hash(tenantId));
    // ✗ — NEVER add tenant_id (raw), prompt content, or customer data as span tags

    var result = await _evaluatorRegistry.EvaluateAsync(context, ct);

    activity?.SetTag("waooaw.decision", result.Decision.ToString());
    activity?.SetTag("waooaw.claim_id", result.ClaimId ?? "AUTHORIZED");

    if (result.Decision == EvaluationDecision.Deny)
        activity?.SetStatus(ActivityStatusCode.Error, result.Reason);

    return MapToResponse(result);
}
```

---

## 3. Python 3.12 — Professional Runtime + AI Runtime

### 3.1 Tools (CI-enforced)

| Tool | Version | Purpose | Config |
|---|---|---|---|
| **Ruff** | 0.5+ | Lint + format (replaces flake8/black/isort/pylint) | `pyproject.toml` |
| **mypy** | 1.10+ | Static type checking (strict mode) | `pyproject.toml` |
| **Bandit** | 1.8+ | Security vulnerability scanning | `pyproject.toml` |
| **pytest** | 8.x | Test runner | `pyproject.toml` |
| **hypothesis** | 6.x | Property-based testing | `pyproject.toml` |
| **pytest-asyncio** | 0.23+ | Async test support | `pyproject.toml` |
| **mutmut** | 2.x | Mutation testing (weekly) | `.mutmut` |

### 3.2 Type Annotations (Mandatory — mypy strict)

```python
# ✓ — Full type annotations, no Any except at external boundaries
from typing import TYPE_CHECKING
from uuid import UUID
from decimal import Decimal

async def select_provider(
    tier: LLMTier,
    message_language: str,
    plan_tier: PlanTier,
    is_steward: bool,
) -> ProviderSelection:
    ...

# ✓ — Use dataclasses or Pydantic for data structures (not raw dicts)
from pydantic import BaseModel

class ProviderSelection(BaseModel):
    provider: LLMProvider
    model_version: str
    rule_applied: str | None      # PSE-R01 to PSE-R08
    composite_score: Decimal | None
    data_region: Literal["india", "uae", "on-premise"]
```

### 3.3 Async Rules (Performance)

```python
# ✓ — Async throughout (FastAPI is async-native; sync code blocks the event loop)
async def validate_action(request: ValidateActionRequest) -> ValidateActionResponse:
    async with get_db_connection() as conn:
        contract = await conn.fetchrow(
            "SELECT * FROM business.employment_contracts WHERE tenant_id = $1",
            request.tenant_id  # Parameterized — OWASP A03
        )

# ✗ — Never sync DB calls in async context (blocks entire event loop)
contract = db.execute("SELECT ...")   # FORBIDDEN in async service

# ✓ — Use asyncio.gather() for parallel independent operations
contract, usage = await asyncio.gather(
    get_active_contract(tenant_id),
    get_usage_units(tenant_id),
)
```

### 3.4 Security (Python)

```python
# ✓ — Parameterized queries always (asyncpg uses $1, $2 syntax)
row = await conn.fetchrow(
    "SELECT * FROM professional.agent_prompts WHERE agent_type = $1 AND is_active = TRUE",
    agent_type  # Never f-string SQL
)

# ✓ — Input validation at system boundaries (Pydantic auto-validates)
class LLMDispatchRequest(BaseModel):
    session_id: UUID             # Type-enforced — no string injection
    agent_type: AgentTypeEnum    # Enum — no arbitrary string
    message: str = Field(max_length=10_000)  # Length-bounded

# ✓ — Never log prompt content (ADR-028: competitive IP + privacy)
logger.info("PSE dispatch: provider=%s tier=%s latency_ms=%d",
            selection.provider, tier, latency_ms)
# ✗ NEVER:
logger.debug("Prompt: %s", prompt_text)   # Prompt content never in logs
```

### 3.5 Logging (Python — structlog)

```python
import structlog

log = structlog.get_logger()

# ✓ — Structured, machine-parseable (not f-strings)
log.info("pse.dispatch",
         provider=selection.provider.value,
         tier=tier.value,
         latency_ms=latency_ms,
         data_region=selection.data_region,
         session_id=str(session_id),
         # ✗ Never: tenant_id (raw), prompt_text, customer_name
         )

# ✓ — Constitutional context propagated via structlog contextvars
structlog.contextvars.bind_contextvars(
    session_id=str(session_id),
    agent_type=agent_type.value,
    trace_id=trace_id,
)
# All subsequent log calls in this request automatically include these
```

### 3.6 OTel Tracing (Python)

```python
from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("waooaw.ai-runtime")

async def dispatch_llm(request: LLMDispatchRequest) -> LLMResponse:
    with tracer.start_as_current_span(
        "air.llm_dispatch",
        kind=SpanKind.CLIENT,
    ) as span:
        span.set_attribute("waooaw.provider", selection.provider.value)
        span.set_attribute("waooaw.tier", tier.value)
        span.set_attribute("waooaw.model", selection.model_version)
        span.set_attribute("waooaw.data_region", selection.data_region)
        span.set_attribute("waooaw.latency_ms", latency_ms)
        span.set_attribute("waooaw.session_id", str(session_id))
        # ✗ NEVER: prompt_text, customer_name, tenant_id (raw), API keys
```

---

## 4. TypeScript / Next.js 14 — Web Portal

### 4.1 Tools (CI-enforced)

| Tool | Version | Purpose | Config |
|---|---|---|---|
| **Biome** | 1.8+ | Lint + format (replaces ESLint + Prettier, 100x faster) | `biome.json` |
| **TypeScript** | 5.5+ | Type checking (strict mode) | `tsconfig.json` |
| **Vitest** | 2.x | Unit tests (replaces Jest) | `vitest.config.ts` |
| **Testing Library** | 16.x | Component tests | — |
| **Playwright** | 1.45+ | E2E tests | `playwright.config.ts` |
| **@axe-core/playwright** | 4.x | Accessibility | — |
| **bundle-analyzer** | — | Bundle size monitoring | `next.config.js` |

### 4.2 TypeScript Rules (strict mode, no exceptions)

```typescript
// tsconfig.json: strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes
// ✓ — No 'any' except at external boundaries (API responses, JSON.parse)
interface EmergencyStopState {
  isActive: boolean;
  sessionId: string;
  triggeredAt: Date | null;
}

// ✓ — Explicit return types on all functions
const useEmergencyStop = (sessionId: string): EmergencyStopHook => { ... }

// ✓ — Discriminated unions for result types (no null + undefined ambiguity)
type ValidationResult =
  | { status: 'authorized'; claimId: null }
  | { status: 'denied'; claimId: string; reason: string }
  | { status: 'escalate'; message: string };

// ✗ — No 'as any' casts, no '!' non-null assertions in production code
const data = response as any;  // FORBIDDEN
const element = document.getElementById('stop')!;  // FORBIDDEN — check null
```

### 4.3 React Component Rules

```typescript
// ✓ — Server Components by default (Next.js 14 App Router)
// Only use 'use client' when truly needed (event handlers, hooks)

// ✓ — Every component prop is typed with an interface
interface EmergencyStopButtonProps {
  sessionId: string;
  onStopped: (sessionId: string) => void;
  isDisabled?: boolean;  // Never: isDisabled: boolean | undefined
}

// ✓ — Memoize expensive components (but not prematurely)
const AgentDashboard = memo(({ agentType, customerId }: AgentDashboardProps) => {
  ...
});

// ✓ — Emergency Stop button: always visible, always keyboard-reachable
// Constitutional basis: C-001 — Emergency Stop must not be blocked by UI
<button
  aria-label="Emergency Stop — halt all agent activity"
  data-testid="emergency-stop-btn"  // For Playwright
  onKeyDown={e => e.key === 'Enter' && handleStop()}  // Keyboard accessible
  className={styles.emergencyStop}
/>
```

### 4.4 Performance (TypeScript/Next.js)

```typescript
// ✓ — Bundle size budgets in next.config.ts
const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ['@radix-ui/react-*', 'lucide-react'],
  },
  // Alert if JS bundle > 250KB (UX vocabulary: ≤200KB home page)
};

// ✓ — Dynamic import for non-critical components
const VideoPlayer = dynamic(() => import('./VideoPlayer'), { ssr: false });

// ✓ — Image optimization (all images via next/image)
import Image from 'next/image';
<Image src={logo} alt="WAOOAW" width={120} height={40} priority />

// ✗ — No unoptimized <img> tags
<img src={logo} />  // FORBIDDEN
```

### 4.5 Security (TypeScript)

```typescript
// ✓ — Sanitize all user inputs before rendering (prevent XSS — OWASP A03)
import DOMPurify from 'dompurify';
const safeHtml = DOMPurify.sanitize(userProvidedContent);

// ✓ — CSP headers in next.config.ts
const securityHeaders = [
  { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self'" },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
];

// ✓ — Never store JWT in localStorage (XSS-vulnerable); use httpOnly cookies
// JWT is managed by Keycloak session; never accessed by JavaScript directly
```

---

## 5. PostgreSQL 16 — SQL Standards

### 5.1 Tools

| Tool | Version | Purpose | Config |
|---|---|---|---|
| **sqlfluff** | 3.x | SQL linting + formatting | `.sqlfluff` |
| **pgTAP** | 1.3+ | PostgreSQL unit tests | Installed in test DB |

### 5.2 SQL Rules

```sql
-- ✓ — Always use parameterized queries (application layer handles — never inline)
-- ✓ — ALL keywords UPPERCASE
-- ✓ — Table and column names lowercase_snake_case
-- ✓ — Every new table has a COMMENT

-- ✓ — Explicit column lists (never SELECT *)
SELECT
    ar.id,
    ar.tenant_id,
    ar.session_id,
    ar.record_type,
    ar.created_at
FROM constitutional.audit_records ar
WHERE ar.tenant_id = $1        -- RLS will enforce; parameterized for defense-in-depth
  AND ar.created_at > NOW() - INTERVAL '7 days'
ORDER BY ar.created_at DESC
LIMIT 100;

-- ✗ NEVER:
SELECT * FROM constitutional.audit_records WHERE tenant_id = '...' || $1;  -- Injection

-- ✓ — Explain plan for any new query (performance validation before merge)
-- EXPLAIN (ANALYZE, BUFFERS) SELECT ... — document result in PR description

-- ✓ — All new indexes named descriptively
CREATE INDEX IF NOT EXISTS idx_audit_records_tenant_created
    ON constitutional.audit_records (tenant_id, created_at DESC);
-- ✗ NEVER: CREATE INDEX idx1 ON ... (unnamed/cryptic)

-- ✓ — Migration files: always use IF NOT EXISTS / IF EXISTS
ALTER TABLE business.employment_contracts
    ADD COLUMN IF NOT EXISTS plan_tier VARCHAR(20);
```

---

## 6. Proto3 / gRPC — Constitutional Engine API

### 6.1 Rules

```protobuf
// ✓ — All messages have comments with constitutional basis
// ✓ — Field names: snake_case
// ✓ — Message names: PascalCase
// ✓ — Enum values: UPPER_SNAKE_CASE
// ✓ — Services: PascalCase + "Service" suffix

message ValidateActionRequest {
  // session_id: identifies the PAAS session (Temporal workflow ID)
  // Constitutional basis: C-023 — every action requires a session context
  string session_id = 1;

  // action_type: category of proposed action (C-041 — tool authorization gate)
  string action_type = 2;

  // proposed_amount: for C-043 financial ceiling evaluation (INR)
  double proposed_amount = 5;  // 0 if not a financial action
}

// ✓ — Breaking change detection: buf breaking runs on every PR
// ✓ — buf format: proto files are formatted before commit
// ✗ NEVER remove or renumber existing fields (proto backward compat)
```

---

## 7. Unit Test Coding Standards

These complement QA-STRATEGY.md (which defines what to test). This section defines how to write tests.

### 7.1 AAA Pattern — Mandatory

```python
def test_c041_evaluator_denies_unlisted_tool():
    """
    Tool not in the customer's authorized_actions must be DENIED.
    Constitutional basis: C-041 (every MCP tool call governed by Decision Space — default deny)
    """
    # ARRANGE
    contract = make_contract(authorized_actions=["instagram-mcp", "facebook-mcp"])
    request = make_validate_request(tool_name="zerodha-mcp")  # Not in contract

    # ACT
    result = C041ToolAuthorizationEvaluator().evaluate(contract, request)

    # ASSERT
    assert result.decision == EvaluationDecision.DENY
    assert "C-041" in result.reason
    assert "zerodha-mcp" in result.reason
```

### 7.2 Test Independence (No Shared Mutable State)

```python
# ✓ — Each test is completely self-contained
@pytest.fixture
def clean_contract():
    return EmploymentContract(
        tenant_id=uuid4(),        # New UUID per test — no shared state
        authorized_actions=[],
        status=ContractStatus.ACTIVE,
    )

# ✗ — Global mutable state shared across tests
CONTRACT = EmploymentContract(...)  # FORBIDDEN — tests may run in any order
```

### 7.3 No `time.sleep()` / `Thread.Sleep()` in Tests

```python
# ✓ — Use pytest-asyncio + asyncio.wait_for with timeout
async def test_emergency_stop_under_250ms():
    async with asyncio.timeout(0.3):  # Generous outer timeout
        start = time.monotonic()
        result = await emergency_stop_client.trigger(session_id)
        elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms < 250, f"C-001 violation: {elapsed_ms:.1f}ms > 250ms"

# ✗ — time.sleep() makes tests slow and flaky
time.sleep(0.3)  # FORBIDDEN — use proper async patterns
```

### 7.4 Property-Based Tests for Constitutional Invariants

```python
from hypothesis import given, strategies as st

@given(
    tool_name=st.text(min_size=1, max_size=100),
    authorized=st.frozensets(st.text(min_size=1, max_size=50), max_size=20),
)
def test_c041_evaluator_never_authorizes_unlisted_tool(
    tool_name: str, authorized: frozenset[str]
):
    """
    Property: ValidateAction NEVER returns AUTHORIZED for a tool not in authorized_actions.
    Holds for all possible tool names and all possible authorized sets.
    Constitutional basis: C-041 (default deny)
    """
    if tool_name not in authorized:
        contract = make_contract(authorized_actions=list(authorized))
        result = C041Evaluator().evaluate(contract, make_request(tool_name=tool_name))
        assert result.decision == EvaluationDecision.DENY
```

### 7.5 Code Coverage Obligation (C-076 — Constitutional)

**Constitutional basis: C-076 — 90% Minimum Code Coverage Obligation**

Every platform service must maintain ≥90% unit test line coverage. This is not aspirational; it is enforced by CI at Gate 1.

**Toolchain (per language):**

| Language | Tool | CI Enforcement | Threshold Config |
|---|---|---|---|
| .NET 9 | Coverlet + ReportGenerator | `dotnet-coverage` threshold check in `ci.yaml` | `--minimum 90` |
| Python 3.12 | pytest-cov + coverage.py | `--cov-fail-under=90` in `ci.yaml` | `fail_under = 90` in `pyproject.toml` |
| TypeScript | c8/istanbul via Vitest | `coverageThreshold` in `vitest.config.ts` | `lines: 90` |

**Rules for every PR author:**

```python
# ✓ — Confirm before opening PR:
#     pytest --cov --cov-fail-under=90 --cov-report=term-missing
# Output must show overall coverage ≥90%.
# Any module below 90% must have new tests OR a documented justification.

# ✓ — New code: every new function gets at least one unit test
def route_to_provider(tier: LLMTier, ...) -> ProviderSelection:
    ...  # ← new function

def test_route_to_provider_returns_gemini_for_mid_tier():  # ← required test
    result = route_to_provider(tier=LLMTier.MID, ...)
    assert result.provider == LLMProvider.GEMINI_FLASH

# ✓ — Exempt from coverage only with explicit reason:
def _internal_debug_repr(self) -> str:  # pragma: no cover
    # Reason: only used interactively in debugger, not called in production code path
    return f"<{self.__class__.__name__}: {self.id}>"

# ✗ — Blanket exemptions are a C-076 violation
class MyService:  # pragma: no cover — FORBIDDEN without justification
    ...
```

**.NET coverage enforcement (ci.yaml):**
```yaml
- name: Check coverage threshold (C-076)
  run: |
    dotnet-coverage collect "dotnet test" -f xml -o coverage.xml
    dotnet-coverage check coverage.xml \
      --minimum-coverage-branches 80 \
      --minimum-coverage-lines 90
```

**Exemption process (if 90% is genuinely unreachable):**
1. Open GitHub Issue labelled `coverage-exemption-request`
2. Provide: which module, which lines are uncoverable, why (generated code, platform glue)
3. EA must approve the exemption before `# pragma: no cover` is merged
4. Approval is recorded in the Issue; the Issue number goes in the code comment

---

## 8. Observability Standards — Span + Log Taxonomy

### 8.1 Mandatory Span Names

```
waooaw.ce.validate_action          — CE.ValidateAction RPC
waooaw.ce.record_evidence          — CE.RecordEvidence RPC
waooaw.ce.emergency_stop           — CE.TriggerEmergencyStop RPC
waooaw.bp.employment.create        — Employment contract creation
waooaw.bp.auth.validate            — JWT validation middleware
waooaw.pr.paas.session_start       — PAAS session start
waooaw.pr.paas.session_resume      — PAAS session resume after crash
waooaw.pr.emergency_stop.ws        — WebSocket Emergency Stop handler
waooaw.air.pse.select_provider     — PSE provider selection
waooaw.air.llm.dispatch            — LLM API call dispatch
waooaw.air.llm.fallback            — PSE fallback to secondary provider
waooaw.air.rag.retrieve            — RAG vector retrieval
waooaw.air.mcp.tool_call           — MCP tool execution
waooaw.web.page_load               — Web portal page load
waooaw.scripts.seed_prompts        — seed-prompts.py execution
```

### 8.2 Mandatory Span Attributes

All spans must include:

```
waooaw.session_id       STRING   Temporal workflow ID
waooaw.agent_type       STRING   e.g., DMA, AGRICULTURAL
waooaw.tenant_id_hash   STRING   SHA-256 of tenant_id (hashed — never raw)
waooaw.environment      STRING   dev|qa|uat|prod
waooaw.version          STRING   platform version (from PROJECT_STATE.md)
```

LLM dispatch spans additionally:

```
waooaw.provider         STRING   google_gemini_flash|sarvam_saaras|azure_gpt4o_mini etc.
waooaw.model_version    STRING   gemini-2.0-flash-001
waooaw.tier             STRING   LOCAL|MID_TIER|FRONTIER
waooaw.data_region      STRING   india|uae|on-premise
waooaw.latency_ms       INT      actual dispatch latency
waooaw.was_fallback     BOOL     true if PSE used fallback chain
```

**NEVER add to spans:** `tenant_id` (raw), `prompt_text`, `customer_name`, `jwt_token`, API keys.

---

## 9. PR Authoring Checklist for Developer Agents

Before opening any PR, WAOOAW AI Agent — Developer runs:

```bash
# .NET
dotnet format --verify-no-changes src/constitutional-engine
dotnet build src/constitutional-engine -warnaserror
dotnet test src/constitutional-engine --no-build

# Python
ruff check src/professional-runtime src/ai-runtime
ruff format --check src/professional-runtime src/ai-runtime
mypy --strict src/professional-runtime src/ai-runtime
bandit -r src/professional-runtime src/ai-runtime -ll

# TypeScript
pnpm biome check web/
pnpm tsc --noEmit

# SQL
sqlfluff lint infrastructure/postgres/init/

# Proto
buf lint architecture/reference/proto/
buf format --diff architecture/reference/proto/

# Secrets
git-secrets --scan
```

**All commands must pass with zero errors before the PR is opened.** CI will enforce — but running locally first saves CI minutes and rate limits.
