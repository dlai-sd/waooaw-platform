# GOAL-007 — Proposed Execution Plan

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-007 |
| `record_id` | GEP-GOAL-007-INST-013-01 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-14T12:05:00Z |
| Status | PROPOSED — no GO Authorization; awaiting fresh INST-002 review and Founder acknowledgement |
| Work Contract | WC-075 |
| GitHub action | Issue #290 |

## Approval Stop

No contribution below may begin until a fresh Constitutional Analyst reviews the Understanding,
classification, owner selection, Evidence Specifications, and separation model, and the Founder
acknowledges that reviewed package. Later phases issue authorizations sequentially; no downstream
authorization may be inferred from plan acknowledgement.

## Delivery Model

Use one primary executor per complete Work Component. The Goal Orchestrator coordinates but does not
author a charter, agent specification, architecture, tests, tools, simulations, or quality verdict.
The proposed QA Institution cannot validate or activate itself.

| Phase / WC | Accountable owner | Contribution envelope | Dependencies | Exit evidence |
|---|---|---|---|---|
| P1-WC01 Institutional capability and Test Champion specification | INST-003 Business Architect | Draft QA capability, charter proposal, complete agent spec Sections 1–13, professional persona, skills, Decision Space, prohibited actions, evidence and escalation contracts | Reviewed plan and valid GOA | Contribution Record; complete spec package; no activation claim |
| P1-WC02 Architecture chain and activation-gate review | INST-004 Enterprise Architect | Review the charter/spec; decide architectural impacts; ensure chain updates are complete; run the full binary Activation Gate; define least-privilege tool boundary | P1-WC01 | Independent EA Review; gate matrix; dependency impact report; zero unresolved P0/P1 |
| P1-WC03 Constitutional operating-model integration | INST-002 Constitutional Analyst | Validate C-065 separation, WIOM/GEOM compatibility, proposed ORGANIZATION and registry changes, immutable-document boundaries, reviewer model, and status-transition evidence | P1-WC02 | Constitutional Clearance Record; proposed integration delta; no self-ratification |
| P1-WC04 Charter, specification, and activation decision | INST-001 Founder | Ratify, return, or reject charter/spec; assign canonical Institution ID; authorize status transition and activation only if all gates pass | P1-WC03 | Founder Action and exact ratification/activation record or explicit return |
| P2-WC01 QA tooling and deterministic harness integration | INST-010 Platform IT Expert | Implement only approved missing tool adapters, Docker runners, evidence contracts, CI hooks, and least-privilege integrations; reuse existing tools first | P1-WC04 plus separate current-session implementation authorization | Source/test changes, Docker evidence, security checks, independent implementation review |
| P2-WC02 Test Champion supervised simulations | Activated QA Institution as executor; INST-004/002 independent reviewers | Execute mandatory campaigns without production authority; prove fail-closed and separation behavior | P2-WC01 | Simulation ledger, raw evidence, defects, independent verdict, no unresolved P0/P1 |
| P3-WC01 Business Platform genuine-test pilot | INST-010 authors unit/integration repairs; activated QA owns campaign architecture, independent CCTs, execution, and recommendation | Raise BP from 77.85%/65.81% to at least 90%/80% with risk-ranked production-facing tests and mutation sampling | P2-WC02 and separate pilot authorization | Docker test/coverage/mutation artifacts; EVC-08 identities; independent acceptance |
| P3-WC02 Goal clearance and learning | Fresh INST-002 plus INST-013 closure | Validate SC-01 through SC-12 and commit evidence/learning without overstating customer or Production proof | All prior WCs | Clearance Record, completion decision, learning record |

## Test Champion Tool And Technique Baseline

The agent specification must classify each tool as required, optional, degradable, or prohibited and
bind every invocation to C-041 authorization and C-023 evidence. The baseline includes:

- Docker-only execution under C-080; no host Python virtual environment.
- pytest, pytest-cov, xUnit, FluentAssertions, Moq, Coverlet, and Cobertura.
- OpenAPI and gRPC producer/consumer contract verification.
- Mutation sampling and property-based testing where risk and stack support them.
- SAST/DAST evidence consumption, dependency/security checks, tenant and authorization negatives.
- Load, latency, saturation, fault injection, chaos, recovery, rollback, and promotion verification.
- Browser journey and accessibility verification for user-facing behavior.
- Immutable evidence binding to commit, image/config/data versions, runner/tool version, environment,
  authority, timestamps, raw output, exclusions, skips, and independent verifier.

No new MCP is presumed. A proposed MCP must pass architecture, catalogue, security, health-check,
Docker, authorization, and evidence gates before use.

## Mandatory Simulation Matrix

| ID | Scenario | Required behavior |
|---|---|---|
| SIM-QA-01 | Genuine coverage | Reject DTO-only, assertion-free, generated-path, and exclusion-based inflation; prioritize consequential uncovered paths |
| SIM-QA-02 | Independent CCT | Derive a failing constitutional test from an approved claim without modifying implementation |
| SIM-QA-03 | Tenant and security | Prove cross-tenant denial, stale authority denial, replay handling, and evidence integrity |
| SIM-QA-04 | Mutation quality | Detect weak assertions on a constitutional or commercial decision path |
| SIM-QA-05 | Contract drift | Detect OpenAPI or gRPC producer-consumer incompatibility before promotion |
| SIM-QA-06 | Performance and resilience | Prove Emergency Stop under pressure and fail-safe CE/dependency loss |
| SIM-QA-07 | Promotion and recovery | Bind qualification to immutable digests and prove rollback/restore evidence |
| SIM-QA-08 | Independence | Refuse approval when author, executor, custodian, and acceptor separation is absent |
| SIM-QA-09 | Tool failure | Fail closed when a runner, collector, evidence sink, or required environment is unavailable |
| SIM-QA-10 | BP pilot | Produce and execute a risk-ranked 90%/80% campaign without owned-code exclusions |

## Evidence Specifications

Every Contribution Record includes goal, GOA, Acceptance, producer, source commit/hash, inputs,
decisions within the owner's Decision Space, unresolved gaps, deterministic validation, and an
independence statement. Reviews pin exact hashes. Simulation passes retain raw results and negative
proof, not summaries alone. A green workflow, test count, coverage percentage, or authored checklist
is never sufficient by itself.

## Completeness And Budget Controls

- All twelve success criteria and ten simulations are ledger obligations; none may be silently dropped.
- `REUSE` requires the active vNext Contribution Reuse Test. Existing QA policy and GOAL-006 strategy
  are inputs, not proof of an operational Institution.
- M2 changes require a Dependency Impact Report. Charter, authority, registry status, and activation
  are M3 and remain stopped for the protected authority.
- Budget state begins `WITHIN_BUDGET`. At 80 percent, stop dispatch and consolidate. Budget pressure
  cannot waive an owner decision, simulation, independent review, or Founder gate.

## Phase Boundaries

Plan acknowledgement permits only phased GOA issuance. P1 produces and reviews governance/specification.
P2 tooling changes require separate explicit implementation authority for the current session.
P3 pilot testing requires separate authorization after activation. Nothing in this plan authorizes
cloud mutation, deployment, Production testing, PR approval, merge, or QA self-activation.
