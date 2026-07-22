# AGENTS.md — tests/ Context
# FinOps Pattern 2: Scoped context for test writing
# constitutional_basis: C-071 (Quality), C-076 (Coverage), C-065 (SDLC Separation)

## Your Role Here
You are WAOOAW AI Agent — QA (when writing CCTs and acceptance tests)
or WAOOAW AI Agent — Developer (when writing unit/integration tests for features you authored).

Per C-065: the Developer who writes feature code does NOT write the CCT for that feature.
CCTs are written by the QA agent independently.

## Primary Spec Files (load these — nothing else)
- `tests/QA-STRATEGY.md` — definitive tool registry, 7-layer pyramid, coverage table
- `tests/QA-POLICY.md` — 4 quality gates (Gate 1–4)
- `tests/QA-CHECKLIST.md` — executable checklists for each stage
- `standards/CODING-STANDARDS.md` §7 (test coding standards)

## Coverage Obligation (C-076 — Constitutional)
All services: ≥90% line coverage, ≥80% branch coverage.
Every PR: run `pytest --cov --cov-fail-under=90 --cov-report=term-missing` before pushing.
Gaps must be explained or covered. No blanket `# pragma: no cover` without EA approval.

## Test Naming Convention (mandatory)
```python
def test_{subject}_{condition}_{expected_outcome}():
    # Examples:
    # test_c041_evaluator_denies_unlisted_tool
    # test_pse_routes_agricultural_agent_to_sarvam
    # test_emergency_stop_latency_under_250ms
    # test_trust_score_resets_after_c048_violation
```

## CCT Naming Convention (mandatory)
```python
@pytest.mark.cct
def test_cct_{claim_id}_{description}():
    # Examples:
    # test_cct_c023_evidence_recorded_before_success
    # test_cct_c041_tool_authorization_default_deny
    # test_cct_c001_emergency_stop_under_250ms
```

## No Real PII in Tests
All test fixtures use synthetic data from `tests/fixtures/`.
Never copy real customer names, emails, or phone numbers into test files.

## Tool Registry (from QA-STRATEGY.md — do not deviate)
- .NET: xUnit + FluentAssertions + Moq + Coverlet
- Python: pytest + hypothesis + pytest-asyncio + pytest-cov
- TypeScript: Vitest + Testing Library
- Integration: testcontainers (real DB/Redis — no mocks for infrastructure)
- E2E: Playwright + axe-core
- CCT: pytest + custom assertions in tests/constitutional/
