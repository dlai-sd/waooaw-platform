# WAOOAW Quality Policy

**Version:** 1.0
**Date:** 2026-07-19
**Authority:** C-071 (Quality Obligation — RATIFIED), QA-STRATEGY.md
**Owner:** WAOOAW AI Agent — QA
**Scope:** All code changes, all environments, all agents

---

## 1. Non-Negotiable Quality Gates

These gates are enforced by CI. There is no override. There is no exception. A bypass is a C-071 violation.

### Gate 1: PR Merge Gate

Every pull request must pass ALL of the following before merge is permitted:

| Check | Tool | Threshold | Blocks merge? |
|---|---|---|---|
| Unit tests pass | xUnit / pytest / Vitest | 100% pass rate | YES |
| Coverage not regressed | Codecov | Drop ≤ 2% from base branch | YES |
| SAST: no new critical/high | CodeQL | 0 new critical/high findings | YES |
| Dependency audit | pip-audit / pnpm audit | 0 HIGH+ vulnerabilities | YES |
| Container scan | Trivy | 0 CRITICAL findings | YES |
| Secret detection | Gitleaks | 0 secrets | YES |
| Constitutional commit gate | C-059 checker | All feat/fix/cct commits reference IB item | YES |
| Authorization tier check | C-066 checker | Tier 1/2/3 label present if required | YES (warning) |
| OpenAPI / proto lint | Spectral / buf | 0 lint errors | YES |
| CCTs pass in dev | pytest CCT suite | 100% | YES |

### Gate 2: QA Environment Promotion Gate

After merge to main, before promoting image to QA:

| Check | Tool | Threshold | Blocks promotion? |
|---|---|---|---|
| All Gate 1 checks | — | Must have passed | YES |
| Integration tests | testcontainers suite | 100% pass | YES |
| Contract tests (REST) | Schemathesis | 0 schema violations | YES |
| Contract tests (gRPC) | buf breaking | 0 breaking changes | YES |
| CCTs pass in QA | pytest CCT suite | 100% | YES |
| Acceptance scenarios (core) | DeepEval + simulation | AS-001, AS-003, AS-005 = Grade A | YES |
| Performance baseline | k6 smoke (10 VUs, 2 min) | All P99 within SLA | YES |
| Accessibility | axe-playwright | 0 critical violations | YES |
| Prompt injection suite | Custom 50-case suite | 100% blocked | YES |
| Multi-tenant isolation | Integration suite | 0 cross-tenant leaks | YES |
| seed-prompts.py | Dry-run validation | 0 errors, all prompts parseable | YES |

### Gate 3: Production Promotion Gate

Before promoting to production (blue-green C-067):

| Check | Threshold | Owner |
|---|---|---|
| All Gate 2 checks | Must have passed in QA | CI |
| Full acceptance scenario suite | All AS grades = A | CI |
| DAST (OWASP ZAP) | 0 critical, 0 high | CI |
| Performance load test (50 VUs) | All P99 within SLA, Emergency Stop ≤250ms | CI |
| CCT full suite in UAT | 100% | CI |
| Sujay sign-off on agent output quality | Grade A simulations reviewed | Sujay via Steward Assistant |
| Cost ceiling check | Current month < 95% of C-067 ceiling | CI (existing gate) |

### Gate 4: New Agent Activation Gate

Before any new agent type serves its first customer:

| Check | Threshold |
|---|---|
| AGENT-AUTHORING-GUIDE Section 0 complete | All 3 instincts declared |
| Acceptance scenario defined (AS-NNN) | Grade A in simulation |
| Per-skill CCTs written | CCT-{agent}-01 minimum per constitutional claim |
| EA Review approved | R-NNN review on file |
| Founder approval | Per GENESIS Part 05 |
| C-049 trigger conditions documented | Per skill |
| Quality signal types documented | Per skill |
| Prompt version seeded to DB | professional.agent_prompts is_active=true |

---

## 2. Test Authorship Standards

### 2.1 Who Writes What

| Test Type | Written by | Reviewed by | Owned by |
|---|---|---|---|
| Unit tests | WAOOAW AI Agent — Developer | WAOOAW AI Agent — QA | The feature |
| Integration tests | WAOOAW AI Agent — Developer | WAOOAW AI Agent — QA | The service boundary |
| CCTs | WAOOAW AI Agent — QA | Enterprise Architect | The institution |
| Acceptance Scenario tests | WAOOAW AI Agent — QA | Sujay (output quality) + Ojal (C-049/C-048) | The agent type |
| Performance tests | WAOOAW AI Agent — QA | WAOOAW AI Agent — Platform IT Expert | The SLA |
| Security tests | WAOOAW AI Agent — QA | WAOOAW AI Agent — Enterprise Architect | The constitutional floor |

Per C-065 (SDLC Separation): the Developer who writes the feature code does NOT write the CCT for that feature. They write the unit/integration tests. The QA agent writes the CCT independently.

### 2.2 Test Naming Convention

**Mandatory naming (deviation requires PR comment from QA agent explaining why):**

```
Unit:          test_{subject}_{condition}_{expected}
               e.g., test_trust_score_c048_violation_resets_tier

Integration:   test_integration_{service_a}_{service_b}_{scenario}
               e.g., test_integration_bp_ce_evidence_first_enforced

CCT:           CCT-{PRINCIPLE_CODE}-{SEQUENCE:02d}
               e.g., CCT-EF-03, CCT-MT-07

Acceptance:    AS-{number}_{agent}_{customer}_{outcome}
               e.g., AS-001_dma_dr_mehta_instagram_post_grade_a

Performance:   PERF-{service}_{endpoint}_{scenario}
               e.g., PERF-CE-validate_action_50_concurrent
```

### 2.3 Test File Structure

```
tests/
├── QA-STRATEGY.md           ← This framework (read-only by agents)
├── QA-POLICY.md             ← This file (read-only by agents)
├── QA-CHECKLIST.md          ← Stage checklists (executable)
├── conftest.py              ← Shared fixtures: test DB, auth tokens, synthetic personas
├── fixtures/                ← Synthetic customer profiles, agent configs
│   ├── dr_mehta_dental.json
│   ├── suresh_vidarbha_farmer.json
│   ├── rahul_nifty_trader.json
│   └── priya_class8_maths.json
├── constitutional/          ← CCT suite (GENESIS mandate)
│   ├── README.md
│   └── test_cct_*.py
├── unit/                    ← Per-service unit tests
│   ├── constitutional-engine/
│   ├── business-platform/
│   ├── professional-runtime/
│   ├── ai-runtime/
│   └── web/
├── integration/             ← Cross-service integration tests
│   ├── test_bp_ce_*.py
│   ├── test_pr_ce_*.py
│   └── test_multi_tenant_*.py
├── acceptance/              ← Acceptance Scenario tests (AS-NNN)
│   ├── test_as001_dma_dr_mehta.py
│   ├── test_as003_trading_rahul.py
│   └── test_as005_agri_suresh.py
├── performance/             ← k6 scripts
│   ├── smoke.js             ← 10 VUs, 2 min (every QA deploy)
│   ├── load.js              ← 50 VUs, 5 min (pre-prod)
│   └── emergency_stop.js    ← Emergency Stop under load (constitutional)
├── accessibility/           ← axe-playwright tests
│   └── test_wcag_*.spec.ts
├── security/                ← DAST + prompt injection + adversarial
│   ├── prompt_injection_fixtures.py
│   └── test_multi_tenant_adversarial.py
└── ai-quality/              ← DeepEval acceptance grade tests
    ├── test_grade_dma_*.py
    ├── test_grade_agri_*.py
    └── test_grade_trading_*.py
```

---

## 3. Defect Classification

Aligned with constitutional incident severity (Section 6.3 of PMO Plan).

| Severity | Definition | SLA | Constitutional impact |
|---|---|---|---|
| **P0-Constitutional** | Test reveals constitutional floor breach (CCT failure, Emergency Stop > 250ms, cross-tenant data leak, evidence record missing) | Immediate fix + rollback | C-071 + relevant claim violation |
| **P0-Critical** | Complete service unavailable | ≤2h | P0-Service |
| **P1-High** | Grade C acceptance scenario, security DAST finding, WCAG critical violation | ≤8h | Quality obligation (C-071) |
| **P2-Medium** | Coverage regression, Grade B acceptance scenario, performance P99 approaching SLA | ≤48h | Quality improvement |
| **P3-Low** | Test flakiness, minor WCAG violations, documentation gap | ≤1 sprint | Hygiene |

**P0-Constitutional rule:** Any P0-Constitutional defect found in production immediately triggers:
1. Blue-green rollback to previous revision (C-067)
2. Constitutional Blocker filed by WAOOAW AI Agent — QA
3. Ojal notified via Steward Assistant
4. Root cause analysis added to `blockers/` folder within 24h

---

## 4. Test Quality Self-Improvement

Per C-071 (Instinct 2), test quality is tracked and improved automatically.

**Mutation testing schedule:**
- Stryker.NET: runs every Sunday in CI against `src/constitutional-engine` and `src/business-platform`
- mutmut: runs every Sunday against `src/professional-runtime` and `src/ai-runtime`
- Mutation score written to `institutional.quality_metrics`
- If mutation score drops below threshold: Self-Improvement Analyst raises quality proposal

**Test flakiness detection:**
- Any test that fails in CI 2+ times in 7 days without a code change is marked `@pytest.mark.flaky`
- Flaky tests are quarantined (run but don't block gate) for 48h
- If flakiness persists → P2-Medium defect raised automatically

**Dead test detection:**
- Weekly: identify tests with 0 assertion failures in 30 days against 100+ runs
- These are candidates for mutation (are the tests actually testing anything?)
- Self-Improvement Analyst reports dead tests to Sujay monthly
