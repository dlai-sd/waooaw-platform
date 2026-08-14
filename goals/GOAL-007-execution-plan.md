# GOAL-007 — Proposed Execution Plan

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-007 |
| `record_id` | GEP-GOAL-007-INST-013-01 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-14T12:05:00Z |
| Status | FOUNDER-ACKNOWLEDGED P2 PLAN; lifecycle Amendment 1 proposed after AVD prerequisite discovery |
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

## Amendment 1 — AVD And Constitutional Birth Prerequisites (Proposed)

P1-WC01 execution found that the original plan incorrectly placed a complete agent specification
before the mandatory AVD and constitutional-birth gates. The AGENT-AUTHORING-GUIDE and AVD Authoring
Process require: AVD v0.1/v0.2 review, Founder ratification to v1.0, and a non-PROPOSED chartered
registry entry before any agent specification is produced. This amendment preserves the approved
Goal outcome and splits the old P1 sequence at the controlling prerequisite.

This amendment is not effective until the Founder acknowledges it. R-131 through R-133 are advisory
inputs only; they do not replace the formal authorized reviews below.

| Phase / WC | Accountable owner | Contribution envelope | Dependencies | Exit evidence |
|---|---|---|---|---|
| P1-WC01 Institutional capability, AVD, and charter proposal | INST-003 Business Architect | Draft Domain 13 capability, AVD with professional mission and 13 skills, Charter Parameters, Decision Space, Code of Conduct, evidence/escalation contracts | Reviewed plan and valid GOA | AVD v0.2; CR-GOAL-007-INST-003-01; no spec/registry/activation claim |
| P1-WC02 AVD multi-institution review | INST-004 EA + INST-008 AI Architect + fresh INST-002 CA contexts | Formally review feasibility, AI execution validity, constitutional alignment, charter boundaries, and architecture-chain impacts | P1-WC01 plus separate GOAs/Acceptances | Three independent Contribution/Review Records; all blocking findings resolved |
| P1-WC03 Constitutional birth decision | INST-001 Founder | Ratify, return, or reject AVD; if ratified, establish v1.0 and authorize canonical Institution ID plus CHARTERED/CAPABILITY DEVELOPMENT registry and ORGANIZATION integration | P1-WC02 | Founder Action; AVD v1.0 and exact charter integration authority, or explicit return |
| P1-WC04 Agent specification and architecture chain | INST-004 EA + INST-008 AI Architect | Derive complete agent spec from ratified AVD; define tools/prompts/DCM/PAC/data/container impacts; update full architecture chain | P1-WC03 chartered registry entry plus separate GOAs/Acceptances | Complete agent spec and chain; no implementation/activation claim |
| P1-WC05 Independent Activation Gate and constitutional clearance | Fresh INST-004 reviewer then fresh INST-002 reviewer | Run binary author gate and independently validate WIOM/GEOM, C-065, immutable boundaries, registry/status evidence, and unresolved owner decisions | P1-WC04 | EA Activation Gate Review plus Constitutional Clearance; zero unresolved P0/P1 |
| P1-WC06 Specification and capability-development decision | INST-001 Founder | Approve/return specification and authorize capability-development implementation only; activation remains later | P1-WC05 | Founder Action with exact implementation boundary; no OPERATIONAL status |
| P2-WC01 QA tooling and deterministic harness integration | INST-010 Platform IT Expert | Implement only approved missing tool adapters, Docker runners, evidence contracts, CI hooks, and least-privilege integrations; reuse existing tools first | P1-WC06 plus separate current-session implementation authorization | Source/test changes, Docker evidence, security checks, independent implementation review |
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
