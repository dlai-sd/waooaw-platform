# Engineering Quality Standards

**Produced by:** Enterprise Architect + Platform Architect (Sprint 010, WC-010)
**Date:** 2026-07-07
**Constitutional Basis:** GENESIS Engineering Quality Mandate; ADR-013 (CI/CD); ADR-016 (.NET + Python); ADR-017 (Next.js); Security Architecture (security tooling gates)
**Classification:** Class 3 — Governed (evolves via PR review, must remain consistent with GENESIS and all ADRs)

---

## Purpose

This document is the **Decision Space specification for the Runtime Professional**. It defines what the Runtime Professional may build, how they must build it, and what evidence they must produce before a change is merged. Every standard below is constitutionally authorized and enforcement-automated.

A standard without enforcement is a suggestion. Every standard here has an automated enforcement mechanism listed. If the mechanism does not exist yet, the standard does not take effect until it does.

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

### Coverage Targets (enforced by Codecov in CI)

| Layer | Service | Target | Hard Gate |
|---|---|---|---|
| Unit | Constitutional Engine | 95% line coverage | Fail PR if < 90% |
| Unit | Business Platform | 85% line coverage | Fail PR if < 80% |
| Unit | Professional Runtime | 85% line coverage | Fail PR if < 80% |
| Unit | AI Runtime | 80% line coverage | Fail PR if < 75% |
| Unit | Web App | 75% line coverage | Fail PR if < 70% |
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

## 8. Operational Observability Standard

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
