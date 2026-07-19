# WAOOAW Quality Checklist

**Authority:** C-071 · QA-POLICY.md
**Use:** Execute these checklists at each stage. Every [ ] is a binary check — pass or raise a defect.

---

## Checklist A: Before Opening a PR (Developer self-check)

- [ ] Unit tests written for all new functions/methods (AAA pattern, constitutional basis comment where applicable)
- [ ] Unit test coverage: run `dotnet test --collect:"XPlat Code Coverage"` or `pytest --cov` — coverage not regressed
- [ ] Test naming follows convention: `test_{subject}_{condition}_{expected}`
- [ ] No `time.sleep()` or `Thread.Sleep()` in tests — use async/await or testcontainers waits
- [ ] No real PII in test fixtures — all synthetic data from `tests/fixtures/`
- [ ] No `# TODO: add tests` comments left in production code
- [ ] All new constitutional properties covered by a CCT (or CCT raised as GitHub Issue if not yet written)
- [ ] Commit message follows conventional format with IB reference (C-059)
- [ ] `seed-prompts.py --dry-run` passes if any `.md` prompt file was modified
- [ ] `buf lint` passes if any `.proto` file was modified

---

## Checklist B: QA Agent PR Review

- [ ] Unit test coverage report reviewed — no unexplained gaps
- [ ] Integration test exists for every new service-to-service interaction
- [ ] Every new API endpoint has a contract test (Schemathesis or grpc-health)
- [ ] Multi-tenant isolation: new endpoint has adversarial test (Customer A cannot read Customer B's data)
- [ ] Constitutional basis: any test touching CE/Evidence First/Emergency Stop has `# Constitutional basis: C-0NN`
- [ ] If new agent skill added: C-049 trigger test exists for that skill
- [ ] If new agent skill added: quality signal (`SKILL_QUALITY_SIGNAL`) is recorded and tested
- [ ] No mocked infrastructure in integration tests (database, Temporal, Keycloak must be real via testcontainers)
- [ ] CCT-QA-01 and CCT-QA-02 still pass after this change

---

## Checklist C: QA Environment Promotion

- [ ] Gate 2 CI workflow has passed (all green on GitHub Actions)
- [ ] Acceptance scenario AS-001 (DMA) → Grade A confirmed in QA environment
- [ ] Acceptance scenario AS-003 (Trading) → Grade A confirmed in QA environment  
- [ ] Acceptance scenario AS-005 (Agricultural) → Grade A confirmed in QA environment
- [ ] k6 smoke test: all P99 latencies within SLA
- [ ] Emergency Stop latency: ≤250ms P99 over 10 runs in QA environment
- [ ] Accessibility: axe-playwright 0 critical violations on all portal pages
- [ ] Prompt injection suite: 100% blocked (0 bypasses out of 50 attack patterns)
- [ ] Multi-tenant adversarial suite: 0 cross-tenant data leaks
- [ ] `institutional.pse_provider_ranking` populated — PSE is receiving data from QA dispatches
- [ ] Schemathesis: 0 schema violations against QA environment

---

## Checklist D: Production Promotion

- [ ] All Checklist C items passed in UAT (not just QA)
- [ ] Full acceptance scenario suite (all AS entries): Grade A
- [ ] k6 load test (50 VUs, 5 min): all P99 within SLA
- [ ] Emergency Stop under load: ≤250ms P99 while 50 concurrent PAAS sessions active
- [ ] OWASP ZAP active scan: 0 critical, 0 high findings
- [ ] CCT full suite in UAT: 100% pass rate
- [ ] DPDPA audit: `institutional.provider_dispatch_events` shows 0 rows with `pii_in_request=true AND data_region NOT IN ('india', 'uae')`
- [ ] Cost ceiling: current month < 95% of C-067 ceiling in production environment
- [ ] Sujay has reviewed Grade A simulation results via Steward Assistant and applied `approved:sujay`
- [ ] Blue-green deploy script validated: `scripts/blue-green-deploy.sh --dry-run` passes
- [ ] Rollback tested: previous revision is still available and can receive 100% traffic within 30s

---

## Checklist E: New Agent Type Activation

- [ ] `Inherits: CONSTITUTIONAL_DNA v1.0` in spec header
- [ ] Section 0 of agent spec complete (all 3 instincts, domain parameters)
- [ ] Acceptance scenario (AS-NNN) defined with Grade A criteria
- [ ] Per-skill C-049 trigger conditions documented
- [ ] Per-skill quality signal types documented
- [ ] CCTs written: at minimum CCT-{AGENT}-01 (constitutionally mandated principle)
- [ ] DeepEval test: `test_grade_{agent}_as_{n}_grade_a.py` passing
- [ ] Regional language test: if agent uses non-English output, vocabulary compliance test exists
- [ ] `professional.agent_prompts` seeded: all skills have `is_active=true` row in QA DB
- [ ] Trust ledger: `professional.trust_ledger` empty (agent starts at Tier 1 — no pre-existing trust)
- [ ] EA Review (R-NNN) on file and APPROVED
- [ ] Founder approval: per GENESIS Part 05

---

## Checklist F: Weekly Quality Health Check (Self-Improvement Analyst runs this)

- [ ] CCT pass rate in production: 100%? (If not: P0-Constitutional)
- [ ] Emergency Stop P99: ≤250ms? (If >200ms: performance proposal)
- [ ] Unit test coverage trend: stable or improving? (If declining: coverage proposal)
- [ ] Mutation score: ≥ thresholds? (If below: test quality proposal)
- [ ] Any flaky tests quarantined > 48h? (Raise P2-Medium defect)
- [ ] Grade A rate for all acceptance scenarios: 100%? (If not: skill improvement proposal)
- [ ] Provider fallback rate: < 5%/day? (If > 10%: ADR-029 review proposal)
- [ ] DPDPA: 0 events with data sent to non-approved region? (If any: P0-Constitutional)
- [ ] Prompt injection suite: 100% blocked? (If not: immediate P0-Constitutional)
- [ ] Accessibility: 0 new critical violations? (If any: P1-High)

---

## Checklist G: New CCT Authoring

Every new CCT must satisfy all of the following before merge:

- [ ] Named: `CCT-{PRINCIPLE_CODE}-{SEQUENCE:02d}` (see principle codes in tests/constitutional/README.md)
- [ ] Decorated: `@pytest.mark.cct(code="XX", sequence=N, claim="C-0NN")`
- [ ] Docstring: states the constitutional principle being tested
- [ ] Setup: minimal — creates only what the test needs
- [ ] Action: single action that either upholds or violates the principle
- [ ] Assert: asserts the constitutional property, not just functional correctness
- [ ] Teardown: leaves no persistent state (uses transaction rollback or explicit cleanup)
- [ ] Runs in < 30 seconds (CCT suite must complete in ≤20 min total)
- [ ] Written by QA agent, not the Developer who implemented the feature (C-065)
- [ ] Referenced in the relevant constitutional claim's `Produces:` field
