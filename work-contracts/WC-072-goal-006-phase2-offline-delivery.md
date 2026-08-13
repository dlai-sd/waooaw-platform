# Work Contract 072 - GOAL-006 Phase 2 Offline Cloud Delivery

| Field | Value |
|---|---|
| Office | INST-010 - Platform IT Expert, Skill 17 |
| Goal | GOAL-006 - Secure Autonomous Cloud Delivery Capability |
| Scope | One complete contribution covering P2-WC01 through P2-WC08 |
| Authorization | FA-049; GOA-GOAL-006-INST-010-02 |
| Acceptance | ACC-GOAL-006-INST-010-02 |
| Gate | G5 CLEAR; platform phase IMPLEMENTATION |
| Status | IN PROGRESS - P2-WC02 and P2-WC03 independent acceptance pending |
| Reviewer | INST-004 for implementation integrity; INST-007 security; independent QA for qualification; affected specialist owners retain their Decision Spaces |
| Constitutional basis | C-001, C-023, C-032, C-059, C-065, C-066, C-067, C-071, C-076, C-080; GEOM G-7 |

## Outcome

Implement and prove, through synthetic offline deterministic simulation only, one release system
for exactly Constitutional Engine (CE), Business Platform (BP), Professional Runtime (PR), AI
Runtime (AIR), Web and Billing Engine. Build each member once, verify it, bind the six exact digests
to a signed immutable manifest, and simulate revision-based Azure Container Apps blue-green
delivery without authenticating to or querying a provider.

The release path is mandatory and ordered:

```text
BUILD ONCE
-> VERIFY
-> SIGNED SIX-MEMBER IMMUTABLE MANIFEST
-> PROMOTE EXACT DIGESTS
-> GREEN AT 0% TRAFFIC
-> VERIFY GREEN
-> BOUNDED CANARY
-> INDEPENDENT CONFIRMATION
-> 100% GREEN
-> OBSERVE
-> DEACTIVATE BLUE WITHIN 30 MINUTES
```

Any failed gate must restore 100% traffic to blue, deactivate green, preserve immutable failure
evidence and fail the release. Rebuild is never promotion or rollback.

## Controlling Inputs

| Input | Binding |
|---|---|
| Phase 1 package | PR #281 merge `1655afbab1dec83949734dd435c6c17f811e2683` |
| Integrated specification | `goals/GOAL-006-p1-wc11-integrated-grooming.md`; SHA-256 `495f720692bd71358f5d21db03bfa364b5724978e8b3b8ce85d3ba894b65303f` |
| Independent clearance | R-117 - CLEAR WITH CONDITIONS |
| Skill specification | PR #283 merge `61b1cda8994b85bf9e5c371ba107227d6dfc65bf`; R-118 APPROVE; FA-049 activation |
| Platform design | `goals/GOAL-006-p1-wc03-platform-architecture.md`; R-109 |
| Component topology | `goals/GOAL-006-p1-wc04-component-topology.md`; R-110 |
| Security design | `goals/GOAL-006-p1-wc05-security-architecture.md`; R-111 |
| Data/recovery design | `goals/GOAL-006-p1-wc06-data-recovery-architecture.md`; R-112 |
| Feasibility and diagnostics | `goals/GOAL-006-p1-wc07-implementation-feasibility.md`; `goals/GOAL-006-p1-wc07-diagnostic-evidence.md`; R-113 |
| Qualification strategy | `goals/GOAL-006-p1-wc08-qualification-strategy.md`; R-114 |
| Governing architecture | C-067 and ADR-027, plus accepted ADRs cited by each component context |

## Authority Boundary

### Allowed

- Modify repository specifications, Docker/Compose, dependency locks, tests, scripts, Terraform
  HCL, GitHub Actions and offline evidence within the active component's bounded manifest.
- Use Docker-based local test runners, synthetic fixtures and offline static or simulated tooling.
- Commit and push each independently valid increment to the one implementation branch.
- Maintain one draft Phase 2 PR and request constitutionally independent reviews.

### Prohibited

- Azure login, provider query, Terraform apply, resource mutation, deployment, real traffic, DNS,
  Production action, cloud expenditure or Platform Operations activation.
- Phase 3 work, live effectiveness claims, real customer or Production data, secrets or long-lived
  credentials.
- Host pytest, virtual environments, skips, xfails, deselection, TODOs, echo-only checks,
  hard-coded success, advisory gates, `continue-on-error` qualification or rollback placeholders.
- Architecture or policy invention, specialist Decision Space transfer, self-review, self-approval,
  self-merge, gate weakening, mutable-tag authority or omitted/additional release members.

The monthly development ceiling is INR 5,000. Stop and obtain Founder approval before any
additional charge. Phase 3 remains unauthorized.

## Component Ledger

| Component | Outcome | Direct dependencies | Required independent acceptance | Status |
|---|---|---|---|---|
| P2-WC01 | Deterministic Docker-first toolchain and test foundation | Phase 1, FA-049, GOA-02, ACC-02 | INST-004 implementation review | DONE - R-120 APPROVE |
| P2-WC02 | Exactly six image, Compose and component contracts | P2-WC01 | INST-005 plus independent QA | IMPLEMENTED - local gates pass; independent acceptance pending |
| P2-WC03 | Offline Terraform isolation, identity, secrets and JIT | P2-WC01 | INST-009 and INST-007 | IMPLEMENTED - local gates pass; independent acceptance pending |
| P2-WC04 | Synthetic data lifecycle, migration and recovery | P2-WC01/02; full tuple also P2-WC03/05 | INST-006 and INST-007 | PENDING |
| P2-WC05 | Signed six-member immutable release manifest and supply-chain evidence | P2-WC01/02 | INST-007 and independent QA | PENDING |
| P2-WC06 | Offline CI/CD, revision blue-green, rollback, lifecycle, halt and cost simulation | P2-WC03/04/05 | INST-009, INST-007 and independent confirmer | PENDING |
| P2-WC07 | Complete deterministic qualification and proof accounting | P2-WC01 through P2-WC06 | Independent QA acceptor | PENDING |
| P2-WC08 | Evidence, reviews and bounded Phase 3 readiness package | Independently accepted P2-WC01 through P2-WC07 | INST-004, INST-007, QA and fresh INST-002 | PENDING |

## Component Closure Protocol

For each component in dependency order:

1. Replace `sprint-context/goal-006-phase2-current.json` with only that component's controlling
   sections, affected paths, deterministic validations and direct dependencies.
2. Implement one bounded independently valid increment and run its focused Docker/offline check.
3. Before a long validation run, commit and push the latest valid implementation state.
4. Run every complete deterministic gate with nonzero selected/executed/passed accounting.
5. Obtain the named independent review; author evidence is never acceptance.
6. Update this execution record and component status, replace the context for the next component,
   update the single PROJECT_STATE checkpoint, commit and push.

No separate planning or status artifact may duplicate this Work Contract, the context manifest,
PROJECT_STATE, commits, CI evidence, reviews or the PR.

## Compact Execution Record

| Field | Current value |
|---|---|
| Controlling specification commit | Phase 1 merge `1655afbab1dec83949734dd435c6c17f811e2683`; integrated SHA-256 `495f720692bd71358f5d21db03bfa364b5724978e8b3b8ce85d3ba894b65303f` |
| Authorization checkpoint | `313fb12` on `goal/006/phase2-blocked` |
| Current branch | `goal/006/phase2-offline-delivery` |
| Current PR | Draft PR #284 - `https://github.com/dlai-sd/waooaw-platform/pull/284`; reuse through P2-WC08; do not merge |
| Current component | P2-WC02 and P2-WC03 - implementation complete; required independent acceptance pending |
| Next exact action | Obtain P2-WC02 INST-005/QA acceptance and P2-WC03 INST-009/INST-007 acceptance against immutable commits; do not start dependent P2-WC04/P2-WC05 closure before P2-WC02 acceptance |
| Completed commit IDs | `313fb12` authorization; `6e23941` WC/context; `739cf2b` P2-WC01; `222eaef` R-120; `d2b95d8` P2-WC02; `5cbf895` local-review repairs; `5ed3f0c` P2-WC03 |
| Validation results | P2-WC01 gates PASS; P2-WC02 focused contracts 14/14 and delegated PostgreSQL 2/2 PASS; P2-WC03 contracts 12/12, Ruff, Terraform format, recursive TFLint, Checkov 18/18, policy JSON, patch hygiene and secret scan PASS |
| Review results | R-117 Phase 1 CLEAR WITH CONDITIONS; R-118 Skill 17 APPROVE; R-119 release contract APPROVE; R-120 P2-WC01 APPROVE; P2-WC02 local review complete with independent acceptance pending; P2-WC03 local review complete with Platform/Security acceptance pending |
| Blockers and owner decisions | No contribution-start blocker; canonical Incident/Change/Release policies remain fail-closed dependencies for affected P2-WC06/07/08 paths; INR 5,000 ceiling; Phase 3 prohibited |
| Allowed actions | Offline repository implementation, Docker-first validation, synthetic evidence, independent review, commits/pushes, one draft unmerged PR |
| Prohibited actions | Provider/cloud/DNS/deployment/Production/real-traffic/spend/Phase 3 actions; self-review/approval/merge; weakened or advisory proof |

This table is the durable resume source. Chat history, transcript history and accumulated session
memory are not delivery state. Git, this Work Contract, PROJECT_STATE, the current context manifest,
CI evidence and the PR are authoritative.

## P2-WC01 Binding And Estimate

| Field | Binding |
|---|---|
| Controlling sections | Integrated grooming `Phase 2 Work Components / P2-WC01`; feasibility `Toolchain And Prerequisites` and `Docker-First Validation Architecture`; C-080; ADR-037 |
| Exact affected paths | `architecture/reference/dockerfiles/Dockerfile.test-runner`; `architecture/reference/dockerfiles/Dockerfile.test-runner-python`; `docker-compose.yml`; `requirements-test.txt`; `scripts/env_validator.py`; `scripts/autonomous_sprint_runner.py`; `tests/test_wc012_dry_run.py`; focused new tests/evidence under `tests/` and `goals/` only when required |
| Generated outputs | Docker runner image digests; import-validation output; pytest collection output; selected/executed/passed ledger; SHA-256 evidence references |
| Evidence location | This execution record plus focused raw command evidence attached to the Phase 2 PR/CI; no duplicate status document |
| Prohibited files | Class 1 Constitution/GENESIS; application business logic; Terraform/cloud/release workflow surfaces assigned to later components; unrelated local evidence files |
| Estimate | 1-2 focused implementation days plus independent review; high confidence on dependency/collection scope, medium confidence on full-suite collection defects |
| Critical-path effect | Blocks every later component |

### P2-WC01 Deterministic Gates

- Docker Compose configuration parses without secret disclosure.
- Docker runner reports pinned Python, .NET and pnpm versions required by repository contracts.
- `scripts/env_validator.py` exits zero in the Docker runner with no import gaps.
- `pytest --collect-only` for the focused failing surfaces exits zero and selects nonzero tests.
- `tests/test_wc012_dry_run.py` exits zero with WC012-01 through WC012-04 registered.
- No skipped, xfailed, xpassed, deselected, warning-only or zero-test result is accepted.
- `git diff --check`, dependency consistency and secret-pattern checks pass.

## P2-WC03 Binding And Estimate

| Field | Binding |
|---|---|
| Controlling sections | Integrated grooming `P2-WC03` and mandatory release contract; security architecture SA-01, SA-04, SA-05, SA-07, SA-08, SA-11 and SA-13; C-067; ADR-027 |
| Exact affected paths | `infrastructure/terraform/phase2/`; `tests/pipeline/test_goal006_terraform_foundations.py`; Docker test-runner dependencies only if required; this Work Contract, current context and PROJECT_STATE |
| Generated outputs | Offline format/validation results, policy-test counts, non-secret synthetic plan fixtures and SHA-256 evidence references; no provider-derived plan |
| Evidence location | Compact execution record and Phase 2 PR/CI output; no duplicate status artifact |
| Prohibited files/actions | Class 1 Constitution/GENESIS; legacy live Terraform roots except separately reviewed remediation; credentials, secret values, provider queries, init against a provider, plan/apply, DNS, deployment or Production action |
| Estimate | 2-4 focused implementation days plus Platform and Security review; high confidence on static identity/isolation/secret-reference controls, medium on complete lint/scan coverage until pinned containers execute |
| Critical-path effect | May proceed beside pending P2-WC02 acceptance; blocks P2-WC06 and the full P2-WC04 recovery tuple |

### P2-WC03 Deterministic Gates

- The Phase 2 surface parses and formats using pinned offline Docker tooling without provider authentication or query.
- Demo, UAT and Production use distinct roots, backend keys, deployment identities, runtime identities, vault references and approved OIDC subjects.
- Long-lived Azure credentials, secret-value variables, broad subjects, shared state and cross-environment authority are rejected.
- Workloads use Key Vault references, internal components remain private, public candidates are explicit, and Container Apps use multiple revision mode.
- Scale-to-zero and bounded maximums follow ADR-027; CE and PR preserve accepted minimum-safe policy inputs without inventing Production values.
- JIT and break-glass fixtures require separate approval/execution, exact scope, reason, expiry, revocation and immutable evidence; Production actors and durations remain unresolved.
- Every selected test executes with nonzero counts; no skip, xfail, deselection, TODO, echo-only or advisory success is accepted.

## P2-WC02 And P2-WC03 Deterministic Author Review

Author review is defect discovery only. It is not independent acceptance and does not satisfy
C-065 or either component exit gate.

| Check | Result |
|---|---|
| Immutable boundaries | P2-WC02 `222eaef..5cbf8953b33198cec5197d33d8719dddfb73da9a`; P2-WC03 `5cbf895..5ed3f0c5350de10983476a05fcc4b84e3439a0da`; checkpoint `2db72e1160d174a77329c897b4a15e70381df274` |
| Combined contract accounting | PASS - 26 selected, 26 executed, 26 passed, zero skip/xfail/deselection |
| Runnable-surface review | PASS - no TODO, FIXME, advisory continuation, test skip, Terraform apply or Azure login command |
| Packaging review | PASS - exactly six local images present; all run as `waooaw`; accepted ports 5002, 5001, 5003, 5004, 3000 and 8140 |
| Terraform review | PASS - pinned format, recursive TFLint, Checkov 18/18, Ruff, policy JSON and 12/12 contracts |
| Hygiene | PASS - diff check and committed credential-pattern scan |
| Author verdict | READY FOR INDEPENDENT REVIEW - no author finding; no self-approval |

### Bounded Independent Review Matrix

Every reviewer reads only its row's immutable range and controlling P2-WC section. Unchanged
baseline behavior, live Azure effectiveness, Phase 3, P2-WC05 supply-chain evidence and P2-WC06
promotion simulation are out of scope. A review must return one verdict (`APPROVE` or `REJECT`),
file-and-line findings for every rejection, commands actually executed, and selected/executed/passed
counts. Speculation, future-component findings and findings outside the pinned range have no gate effect.

| Review | Office and decision boundary | Required checks | Output |
|---|---|---|---|
| R-121 | INST-005 Solution Architect; P2-WC02 range `222eaef..5cbf8953b33198cec5197d33d8719dddfb73da9a` | Exactly six members; accepted ports/protocols; CE internal-only; startup/dependency/health/config contracts; Billing membership; OAuth Vault/MCP exclusion | `reviews/R-121-goal-006-p2-wc02-solution-architecture-review.md` |
| R-122 | Independent QA; same P2-WC02 range | Execute 14 focused contracts and delegated PostgreSQL 2/2; verify nonzero accounting, negative membership/secret/port/dependency checks and no skip/xfail/deselection | `reviews/R-122-goal-006-p2-wc02-qa-review.md` |
| R-123 | INST-009 Platform Architect; P2-WC03 range `5cbf895..5ed3f0c5350de10983476a05fcc4b84e3439a0da` | Separate roots/state/identity; durable foundation versus workload; exact-digest ACA multiple revisions; bounded scaling; lease preservation; no provider operation | `reviews/R-123-goal-006-p2-wc03-platform-review.md` |
| R-124 | INST-007 Security Architect; same P2-WC03 range | OIDC subject scope; no long-lived credentials/secret values; private vault/network/NSGs; ingress classes; break-glass separation/expiry/revocation/evidence; run Checkov and security-negative contracts | `reviews/R-124-goal-006-p2-wc03-security-review.md` |

## Definition Of Done

- P2-WC01 through P2-WC08 are independently accepted in dependency order.
- FR-031 through FR-038, C-067, ADR-027, exactly six immutable members and Azure Container Apps
  revision-based blue-green behavior are explicit reviewed acceptance obligations before runnable
  implementation relying on them.
- The complete ordered release and failed-gate restoration behavior is deterministically simulated.
- Complete security review, independent QA, evidence accounting and constitutional review pass.
- Every independently valid increment is committed and pushed.
- One Phase 2 PR remains unmerged for Founder review; no Phase 3 or live/cloud action occurs.