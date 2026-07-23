# Engineering Quality Standards

**Produced by:** Enterprise Architect + Platform Architect (Sprint 010, WC-010)
**Date:** 2026-07-07 (amended 2026-07-23 — Sprint Dashboard obligation, CI secret management)
**Constitutional Basis:** GENESIS Engineering Quality Mandate; ADR-013 (CI/CD); ADR-016 (.NET + Python); ADR-017 (Next.js); Security Architecture (security tooling gates); C-001 (Human Override — Founder must have 24/7 status visibility)
**Classification:** Class 3 — Governed (evolves via PR review, must remain consistent with GENESIS and all ADRs)

---

## Purpose

This document is the **Decision Space specification for the Runtime Professional**. It defines what the Runtime Professional may build, how they must build it, and what evidence they must produce before a change is merged. Every standard below is constitutionally authorized and enforcement-automated.

A standard without enforcement is a suggestion. Every standard here has an automated enforcement mechanism listed. If the mechanism does not exist yet, the standard does not take effect until it does.

---

## 0. Autonomous Sprint Standards (2026-07-23)

### 0.1 Sprint Dashboard Obligation (C-001)

Every autonomous sprint run **must** post a status update to the Sprint Dashboard (GitHub Issue #7) at the end of execution. This is not optional — it is the implementation of C-001 (Human Override) for the development process. Yogesh must be able to see sprint status at any time via GitHub mobile.

| Standard | Rule | Enforcement |
|---|---|---|
| Sprint Dashboard update | Every run calls `scripts/sprint_status_reporter.py` in the `report` job (runs `always()`) | `report` job in `autonomous-sprint.yaml` — cannot be skipped |
| Layman-language status | Comments on Issue #7 must state: what happened, what task, what the Founder must do (if anything) | Script template enforced in `sprint_status_reporter.py` |
| Label reflects state | Issue #7 label updated to `sprint:running/pr-open/waiting/halted/done` after every run | `sprint_status_reporter.py` label update step |
| `founder-action-needed` label | If sprint is halted or failed, add `founder-action-needed` label — triggers mobile push notification | `sprint_status_reporter.py` conditional logic |

### 0.2 CI Secret Management (ADR-014, OIDC)

| Standard | Rule | Enforcement |
|---|---|---|
| No long-lived credentials in GitHub Secrets | All runtime secrets live in Azure Key Vault (`waooaw-dev-kv`). Fetched at runtime via OIDC. | `azure/get-keyvault-secrets@v1` step in `execute` and `review` jobs |
| OIDC authentication only | GitHub Actions authenticates to Azure using `azure/login@v2` with OIDC (client-id + tenant-id + subscription-id as GitHub Variables, not Secrets) | `permissions: id-token: write` in workflow |
| GitHub Variables (not Secrets) for non-sensitive config | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_KEYVAULT_NAME` are GitHub Variables | Set in repo Settings → Variables → Actions |

### 0.3 Pre-Sprint Authorization Gate (EA mandate — 2026-07-23)

Before any sprint trigger (manual workflow_dispatch OR automatic cron), the following verification MUST pass. This is a **constitutional obligation** (C-059 traceability + C-080 Docker isolation — you must know the pipeline is coherent before authorizing execution), not a suggestion.

**Mandatory local pre-flight (all commands via Docker per C-080):**
```bash
docker compose run --rm test-runner python3 -m py_compile scripts/autonomous_sprint_runner.py
docker compose run --rm test-runner python3 -m py_compile scripts/autonomous_sprint_reviewer.py
docker compose run --rm test-runner python3 scripts/build_sprint_index.py --dry-run
docker compose config --quiet
```

The first three commands use the `test-runner` Docker container (C-080 compliant). The last checks the compose config itself.

All 4 must exit 0 before any sprint trigger. If any fails: fix first, verify again, then trigger. **A sprint triggered without this verification is unauthorized execution (C-059 violation).**

**Why Docker, not `python3 -m pytest` directly:** See C-080 (Test Execution Environment Isolation). A test verified only in a virtual environment or host Python has NOT been constitutionally verified. The Docker image IS the specification of the execution environment.

---

## 1. Language Standards

### 1.1 .NET 9 / C# (Business Platform, Constitutional Engine)

| Standard | Rule | Enforcement |
|---|---|---|
| Nullable reference types | `<Nullable>enable</Nullable>` in every `.csproj`. No `!` (null-forgiving) without inline comment. | `dotnet build -warnaserror` in CI |
| No raw SQL | All DB access via EF Core. No `ExecuteSqlRaw` without Data Architect approval. | Roslyn analyzer + code review |
| No business logic in controllers | Controllers validate input and delegate to service layer. No domain logic in `[HttpPost]` methods. | Code review |
| Structured logging only | `ILogger<T>` with structured properties. No string interpolation in log messages. | Roslyn analyzer (CA2254) |
| OTel instrumentation | Every public service method carries an OTel activity span. | Manual review + CCT-OBS-01 |
| Evidence First enforcement | Every method that calls `RecordEvidence` gRPC must treat non-OK response as failure. Caller must not return success. | CCT-EF-01 |

### 1.2 Python 3.12 (Professional Runtime, AI Runtime)

| Standard | Rule | Enforcement |
|---|---|---|
| Type hints mandatory | All public functions carry type hints. `def handle(request: Request) -> Response:` — no bare `def`. | `mypy --strict` in CI |
| `ruff` for linting and formatting | Replaces flake8 + isort + black. Config in `pyproject.toml`. | `ruff check` + `ruff format --check` in CI (fail on any finding) |
| No `# type: ignore` | Only permitted with a referenced GitHub issue. | `ruff` custom rule + code review |
| Structured logging | `structlog` with JSON renderer in production. No `print()` in any non-test file. | `ruff` rule B002 + code review |
| Async all the way | FastAPI handlers are `async def`. No blocking I/O in async context. | Code review + `asyncio` debug mode in tests |
| OTel instrumentation | FastAPI auto-instrumentation enabled. gRPC calls carry trace context. | `opentelemetry-instrumentation-fastapi` in startup |

### 1.3 TypeScript / Next.js (Web App)

| Standard | Rule | Enforcement |
|---|---|---|
| `strict: true` | Required in `tsconfig.json`. | `tsc --noEmit` in CI |
| No `any` type | Use `unknown` with type narrowing. `any` only for third-party type gaps (requires comment). | ESLint `@typescript-eslint/no-explicit-any: error` |
| Generated API client | All Business Platform API calls via openapi-generator-cli generated client. No hand-written `fetch()` calls to platform APIs. | Code review |
| Emergency Stop button rule | A component that renders on an authenticated route must not suppress or conditionally hide the `<EmergencyStopButton />`. | Custom ESLint rule `waooaw/emergency-stop-always-visible` |

---

## 2. Testing Pyramid Mandates

### Docker Test Execution (C-080 — RATIFIED 2026-07-23)

**ALL tests execute inside Docker. Virtual environments are PROHIBITED.**

```bash
# The ONLY compliant test execution commands:

# Run all tests
docker compose run --rm test-runner pytest tests/

# Run constitutional CCTs only
docker compose run --rm test-runner pytest tests/constitutional/ -v

# Run specific test file
docker compose run --rm test-runner pytest tests/constitutional/pipeline/ -v

# Run linting
docker compose run --rm test-runner ruff check .

# Run type checking
docker compose run --rm test-runner mypy src/

# PROHIBITED (C-080 violation):
# source .venv/bin/activate && pytest       ← virtual environment
# python3 -m pytest                         ← host Python
# pip install && pytest                     ← host pip
```

The `test-runner` service is defined in `docker-compose.yml`. The image is built from
`architecture/reference/dockerfiles/Dockerfile.test-runner`. It contains Python 3.12,
.NET 9 SDK, Node.js 20, and all test dependencies from `requirements-test.txt`.

**Enforcement:** CCT-PIPE-01 verifies pipeline scripts compile inside the test-runner image.
The Pipeline Health Check in `autonomous-sprint.yaml` uses Docker commands.
Any PR that introduces `source .venv` or `python3 -m pytest` outside Docker is a C-080 violation.

**Minimum floor: 90% line coverage on all services.** No PR may merge with coverage below 90%.
Targets above 90% represent the quality bar; the 90% floor is the constitutional gate.

| Layer | Service | Target | Hard Gate |
|---|---|---|
---|
| Unit | Constitutional Engine | 95% line coverage | Fail PR if < 90% |
| Unit | Business Platform | 92% line coverage | Fail PR if < 90% |
| Unit | Professional Runtime | 92% line coverage | Fail PR if < 90% |
| Unit | AI Runtime | 90% line coverage | Fail PR if < 90% |
| Unit | Web App | 90% line coverage | Fail PR if < 90% |
| Integration | All services | All service boundaries covered | Fail dev deploy if missing |
| Constitutional Compliance | All | 100% pass | Fail dev deploy if any CCT fails |

### Test Frameworks

| Service | Unit | Integration | Contract |
|---|---|---|---|
| Constitutional Engine (.NET) | xUnit + Moq | TestContainers (real PostgreSQL) | Proto contract tests |
| Business Platform (.NET) | xUnit + Moq | TestContainers | Pact consumer |
| Professional Runtime (Python) | pytest + pytest-asyncio | TestContainers | Pact provider |
| AI Runtime (Python) | pytest | pytest (mock LLM provider) | OpenAPI schemathesis |
| Web App | Jest + @testing-library/react | Playwright (E2E) | — |

### Constitutional Compliance Tests (CCTs)

CCTs are a mandatory test category unique to WAOOAW. They live in `tests/constitutional/`. They prove constitutional principles are architecturally enforced — not just policy-stated.

**CCT naming convention:** `CCT-{PRINCIPLE}-{NUMBER}`

| CCT ID | Principle | What it proves | Runs in |
|---|---|---|---|
| CCT-EF-01 | Evidence First | Calling service returns failure when Constitutional Engine returns error during RecordEvidence | Every environment |
| CCT-EF-02 | Evidence First | Evidence record exists in DB before API response returns 200 | Every environment |
| CCT-HO-01 | Human Override | Emergency Stop round-trip ≤ 250ms at P99 | QA + UAT |
| CCT-HO-02 | Human Override | Emergency Stop cannot be disabled by any configuration flag | Every environment |
| CCT-PAAS-01 | PAAS Boundary | Action outside Decision Space returns DENIED, no execution occurs | Every environment |
| CCT-AL-01 | Audit Ledger Immutability | UPDATE on constitutional.evidence_records returns error | Every environment |
| CCT-AL-02 | Audit Ledger Immutability | DELETE on constitutional.evidence_records returns error | Every environment |
| CCT-MT-01 | Multi-tenant Isolation | Customer A's JWT cannot retrieve Customer B's evidence records | Every environment |
| CCT-MT-02 | Multi-tenant Isolation | DB query with tenant_id bypass returns 0 rows (RLS enforced) | Every environment |
| CCT-SEC-01 through SEC-05 | Security | Per security-architecture.md | QA + UAT |

Full CCT framework specification: `tests/constitutional/README.md`

---

## 3. Security Gates (mandatory in CI — blocks merge)

| Gate | Tool | Trigger | Blocks on |
|---|---|---|---|
| SAST | GitHub Advanced Security (CodeQL) | Every PR | Any HIGH finding |
| Dependency scan | Dependabot + GitHub dependency review | Every PR | Critical/High CVE |
| Secret detection | GitHub Secret Scanning + `detect-secrets` pre-commit hook | Every commit | Any detected secret |
| Container image scan | Trivy | Every image build | CRITICAL CVE in base image |
| OpenAPI spec lint | Spectral CLI | Every PR touching `architecture/reference/api-specs/` | Any WARN or ERROR |
| Proto breaking change | `buf breaking` | Every PR touching `architecture/reference/proto/` | Any breaking change without version suffix |
| License compliance | GitHub dependency review | Every PR | GPL/AGPL/SSPL in production dependency |

---

## 4. Commit Convention

All commits must follow Conventional Commits format for automated changelog generation:

```
<type>(<scope>): <description>

Types: feat | fix | docs | test | chore | refactor | perf | security | constitutional
Scope: ce (Constitutional Engine) | bp (Business Platform) | pr (Professional Runtime) | ai (AI Runtime) | web | infra | db | cct

Examples:
  feat(ce): implement RecordEvidence with append-only enforcement
  cct(ce): add CCT-EF-01 Evidence First enforcement test
  constitutional(bp): add tenant_id validation to JWT middleware
  security(bp): enforce RS256 algorithm check in JWT validation
```

`constitutional` type indicates a change that implements or protects a constitutional principle. These are highlighted in changelogs and must reference the constitutional basis in the commit body.

---

## 5. Pull Request Standard

Every PR must include:
- Description of the change (what and why, not just what)
- Reference to the architecture specification being implemented (file path + section)
- For constitutional changes: the constitutional claim(s) or ADR(s) the change implements
- Evidence that the change is tested (CCT ID if applicable)

PR title must follow commit convention. Single commit PRs are squash-merged. Multi-commit PRs are merge-committed with a summary commit message.

**No PR may be merged without:**
- All CI checks passing (including CCTs)
- At least one reviewer approval (human or AI agent reviewer office)
- No unresolved review comments

---

## 6. Dependency Management

| Runtime | Package manager | Lock file | Update policy |
|---|---|---|---|
| .NET | NuGet | `packages.lock.json` | Dependabot weekly PRs |
| Python | `uv` (fast pip alternative) | `uv.lock` | Dependabot weekly PRs |
| TypeScript | `pnpm` | `pnpm-lock.yaml` | Dependabot weekly PRs |

**Pinning rule:** All production dependencies pinned to exact version in lock file. `^` or `~` in `package.json` / `pyproject.toml` is acceptable for version declaration but the lock file pins exactly.

**New dependency rule:** Any new production dependency requires:
- Justification in the PR description
- License check (no GPL/AGPL/SSPL)
- Snyk scan result (no Critical/High CVEs)
- For a new category of dependency (e.g., first ORM, first auth library): an ADR or ADR addendum

---

## 7. Documentation Standards

| Document | Standard | Location |
|---|---|---|
| Service README | Every service has `src/{service}/README.md` covering: purpose, how to run locally, env vars, how to run tests, known limitations | `src/{service}/README.md` |
| API docs | Auto-served from OpenAPI spec at `/api-docs` in dev. Never manually maintained. | Served by each service |
| Architecture | ADRs for every significant decision. ADR updated before implementation. | `adr/` |
| Changelogs | Auto-generated from conventional commits. Never manually maintained. | `CHANGELOG.md` (generated by CI) |

---

## 9. Database Migration Strategy (EF Core + Postgres Init Bootstrap)

**The baseline problem:** In dev, `infrastructure/postgres/init/*.sql` creates the schema from scratch. EF Core migrations also try to create the same tables. Without coordination, EF Core will fail trying to create tables that already exist.

**Resolution: Empty Initial Migration**

When setting up EF Core for the first time in a service that uses postgres init scripts:

```
Step 1: Run the postgres init scripts first (docker compose up postgres does this automatically).
Step 2: Add EF Core migrations package and configure DbContext normally.
Step 3: Create an EMPTY initial migration that represents the current DB state:
          dotnet ef migrations add InitialBaseline --context WaooawDbContext
Step 4: Mark the baseline as already applied WITHOUT running it:
          dotnet ef database update InitialBaseline --connection "..."
          (or use the MigrationBuilder.Sql("SELECT 1") no-op migration body)
Step 5: All future migrations are applied normally via: dotnet ef database update
```

**The empty migration body** (copy this exactly for the initial migration):
```csharp
public partial class InitialBaseline : Migration
{
    // This migration represents the schema created by infrastructure/postgres/init/*.sql
    // It is intentionally empty — the schema was created by the init scripts.
    // DO NOT add any Up() or Down() operations here.
    protected override void Up(MigrationBuilder migrationBuilder) { }
    protected override void Down(MigrationBuilder migrationBuilder) { }
}
```

**In the deployment pipeline** (ADR-011): The init container runs `dotnet ef database update`. In dev, the empty baseline migration is already applied (recorded in the `__EFMigrationsHistory` table by the init container). Future non-empty migrations apply normally.

---

## 10. Tenant Isolation — `SET LOCAL` EF Core Interceptor Pattern

Every database connection in Business Platform and Constitutional Engine must execute `SET LOCAL app.tenant_id = '{value}'` before any query. This enforces PostgreSQL RLS.

**Implementation pattern (apply in both CE and BP DbContext):**

```csharp
// TenantDbCommandInterceptor.cs
// Registered in DI: builder.Services.AddSingleton<TenantDbCommandInterceptor>();
// Added to DbContext: optionsBuilder.AddInterceptors(tenantInterceptor);

public class TenantDbCommandInterceptor : DbCommandInterceptor
{
    private readonly IHttpContextAccessor _http;

    public TenantDbCommandInterceptor(IHttpContextAccessor http) => _http = http;

    public override async ValueTask<InterceptionResult<DbDataReader>>
        ReaderExecutingAsync(DbCommand command, CommandEventData eventData,
                             InterceptionResult<DbDataReader> result,
                             CancellationToken cancellationToken = default)
    {
        await SetTenantAsync(command, cancellationToken);
        return result;
    }

    public override async ValueTask<InterceptionResult<int>>
        NonQueryExecutingAsync(DbCommand command, CommandEventData eventData,
                               InterceptionResult<int> result,
                               CancellationToken cancellationToken = default)
    {
        await SetTenantAsync(command, cancellationToken);
        return result;
    }

    private async Task SetTenantAsync(DbCommand command, CancellationToken ct)
    {
        var tenantId = _http.HttpContext?.Items["tenant_id"]?.ToString();
        if (string.IsNullOrEmpty(tenantId)) return;

        // Validate it is a UUID before injecting (security: prevent injection)
        if (!Guid.TryParse(tenantId, out _))
            throw new InvalidOperationException("Invalid tenant_id in context");

        using var setCmd = command.Connection!.CreateCommand();
        setCmd.Transaction = command.Transaction;
        setCmd.CommandText = $"SET LOCAL app.tenant_id = '{tenantId}'";
        await setCmd.ExecuteNonQueryAsync(ct);
    }
}
```

**Where `tenant_id` comes from:** The JWT middleware extracts `tenant_id` from the JWT claim and stores it in `HttpContext.Items["tenant_id"]` before the controller runs. For gRPC context (CE internal calls), the metadata `x-tenant-id` is extracted in a gRPC interceptor and stored in the `ServerCallContext`.

**Critical:** If `tenant_id` is null or missing, do NOT set the session variable. PostgreSQL RLS with `current_setting('app.tenant_id', TRUE)` returns NULL (no rows) rather than all rows — this is safe-by-default. An unauthenticated request sees zero rows, not all rows.

---

## 11. Development JWT — Local Testing Without Google OAuth

To test API endpoints locally without Google OAuth:

**How to get a dev JWT:**
```bash
# Get access token (returns JSON with access_token field)
curl -s -X POST \
  http://localhost:8443/realms/waooaw/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=waooaw-dev-client" \
  -d "username=${DEV_TEST_USER}" \
  -d "password=${DEV_TEST_PASSWORD}" \
  | python3 -m json.tool

# Or use the convenience script:
./scripts/get-dev-token.sh
```

The token includes the `tenant_id` claim pre-seeded for the dev test user. Use it in API calls:
```bash
TOKEN=$(./scripts/get-dev-token.sh)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/v1/employment/contracts
```

**The `waooaw-dev-client`** is a Keycloak client with `directAccessGrantsEnabled: true` — allowing username/password token exchange without browser redirect. It is defined in `infrastructure/keycloak/waooaw-realm.json`. **Never enable direct access grants in production.**

Every service must instrument the following OTel signals before the service is considered ready for QA promotion:

### Required OTel spans (every service)
- Every HTTP handler: `http.server.duration` (auto-instrumented via framework)
- Every outbound gRPC call: `rpc.client.duration` (auto-instrumented)
- Every DB query: `db.operation.duration` (auto-instrumented via EF Core / SQLAlchemy)

### Required constitutional OTel spans
Every service must emit the following custom spans where applicable:

| Span name | Emitted by | When |
|---|---|---|
| `constitutional.evidence.record` | Constitutional Engine | On every successful RecordEvidence call |
| `constitutional.evidence.failure` | Constitutional Engine | On every failed RecordEvidence call |
| `constitutional.emergency_stop` | Professional Runtime | On every Emergency Stop received |
| `constitutional.paas.boundary.violation` | Constitutional Engine | On every DENY from ValidateAction |
| `constitutional.paas.session.start` | Professional Runtime | When a PAAS session workflow starts |
| `constitutional.paas.session.end` | Professional Runtime | When a PAAS session workflow ends |

### Required constitutional OTel metrics
Per the constitutional observability specification from IB-016:

```
constitutional.emergency_stop.latency_ms  — histogram, per contract
constitutional.evidence_first.rate        — gauge, % success per service
constitutional.paas.active_sessions       — gauge
constitutional.evidence.state_transition  — counter, per from/to state pair
constitutional.cct.result                 — counter, per CCT ID + pass/fail
```

---

## 12. CE Bootstrap Stub Pattern (Sprint 011 → Sprint 012 transition)

**The circular dependency problem:** Evidence First (C-023) requires every consequential action to call `CE.RecordEvidence()` before returning success. But CE is built in Sprint 012 — after Sprint 011 infrastructure is complete. Sprint 011 actions (branch creation, DB migration, Keycloak import) cannot call CE because CE does not exist yet.

**Resolution: Ordered Bootstrap with Stub Mode**

Sprint 011 operates under **Stub Mode** — a constitutionally-acknowledged bootstrap exception defined here. It is NOT a permanent waiver of Evidence First.

```
STUB MODE rules (Sprint 011 only):
  1. CE.RecordEvidence() calls are replaced with local append-only log writes:
       File: logs/bootstrap-evidence.jsonl
       Format: {"event": "BRANCH_CREATED", "branch": "ib/009/infra-foundation",
                "sha": "abc123", "timestamp": "2026-07-21T...", "stub_mode": true}
  2. The bootstrap-evidence.jsonl file is committed to the branch
  3. When CE is built (Sprint 012), a one-time migration imports bootstrap-evidence.jsonl
     into constitutional.audit_records with constitutional_basis = "BOOTSTRAP-STUB-IB-009"
  4. All CCT-EF tests are run for the FIRST TIME against Sprint 012 CE — not Sprint 011
  5. Sprint 011 CI gates explicitly exclude CCT-EF tests (they cannot pass without CE)
```

**In practice (Sprint 011 only):**
```python
# src/waooaw/evidence.py — created in Sprint 011 scaffold
# Implements: architecture/reference/engineering-standards.md §12
# Constitutional basis: C-023 (Evidence First), C-059 (Traceability)

import json
from datetime import datetime, timezone
from pathlib import Path

_BOOTSTRAP_LOG = Path("logs/bootstrap-evidence.jsonl")

def record_bootstrap_evidence(event_type: str, **kwargs) -> None:
    """
    Sprint 011 stub for CE.RecordEvidence().
    Writes to local JSONL file instead of CE gRPC.
    STUB MODE — replaced by real CE call in Sprint 012.
    """
    _BOOTSTRAP_LOG.parent.mkdir(exist_ok=True)
    record = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stub_mode": True,
        "ib_item": "IB-009",
        **kwargs,
    }
    with _BOOTSTRAP_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")
```

**Sprint 012 CE activation:**
When Sprint 012 delivers the real CE, replace all `record_bootstrap_evidence()` calls with `ce_client.record_evidence()` and run the one-time bootstrap import. CCT-EF-01 must pass before any Sprint 012 PR merges.

**The constitutional justification:** BOOTSTRAP.md itself operates under a "read-before-act" protocol that cannot call CE (CE doesn't exist at first boot). The institution acknowledges that constitutional infrastructure must be built before it can be constitutionally governed. The stub mode preserves the intent (every action is recorded) while acknowledging the sequencing constraint. The bootstrap evidence is imported — nothing is lost.
