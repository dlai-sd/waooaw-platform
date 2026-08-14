# GOAL-007 P1-WC01 — QA Capability, AVD, And Charter Proposal

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-003 — Chief Business Architect |
| `goal_id` | GOAL-007 |
| `record_id` | CR-GOAL-007-INST-003-01 |
| `record_type` | Business Capability And Charter Proposal Contribution |
| `go_authorization` | GOA-GOAL-007-INST-003-01 |
| `acceptance_record` | ACC-GOAL-007-INST-003-01 |
| `produced_at` | 2026-08-14 |
| `status` | SUBMITTED FOR MULTI-INSTITUTION AVD REVIEW — NOT RATIFIED |

## Contribution Outcome

INST-003 confirms a genuine Quality Assurance and Test Engineering capability gap and proposes the
WAOOAW AI Agent — Test Champion through `avd/AVD-002-test-champion-v0.1.md`. The AVD defines 13
MVP1 skills, the Quality Evidence Twin, Goal Journey, AI role, charter parameters, C-065 separation,
and constitutional employment fit.

The proposed Institution owns independent quality engineering. It does not duplicate INST-010
production/unit/integration authorship, INST-004 architecture, INST-002 constitutional validation,
INST-007 security architecture, INST-009 platform architecture, or Self-Improvement Analyst learning.

## Capability Statement

WAOOAW must be able to design and execute risk-based quality campaigns, author independent CCT and
acceptance proof, challenge test strength, measure non-functional behavior, verify evidence
authenticity, and recommend gates without allowing the implementation author to become sole judge of
its own work.

The new Domain 13 capability entries in `knowledge/business-capabilities.md` express that institutional
need independently of any technical implementation.

## Proposed Charter Summary

| Attribute | Proposal |
|---|---|
| Canonical name | Quality Assurance and Test Engineering |
| Agent designation | WAOOAW AI Agent — Test Champion |
| Proposed ID | INST-015; unallocated but not reserved or created until Founder ratification |
| Mission | Establish whether WAOOAW behavior and delivery claims are genuinely supported by reproducible, risk-appropriate evidence |
| Decision Space | Campaign/test/evidence architecture; independent CCT/acceptance authorship; authorized execution; adequacy/authenticity assessment; defect classification; quality recommendation |
| Offering Scope | Quality campaigns; CCT/acceptance; contract, security, performance, resilience, recovery, promotion, accessibility, mutation, coverage and evidence qualification |
| Reviewer | EA for architecture/tooling; fresh CA for constitutional evidence; Founder for charter/status/activation |
| Status sought at ratification | CHARTERED — CAPABILITY DEVELOPMENT, not OPERATIONAL |
| Operational gate | Agent spec, tooling, simulations, Grade A/readiness, independent clearance, Founder activation |

## Operating Model And Separation

| Responsibility | Owner |
|---|---|
| Production behavior and feature unit/integration tests | INST-010 |
| Quality campaign and independent CCT/acceptance design | Proposed QA Institution |
| Campaign execution | Separately authorized QA execution context |
| Raw evidence custody | Goal evidence store; INST-013 ministerial persistence |
| Architecture/tool boundary review | INST-004 plus relevant domain owners |
| Constitutional evidence validation | Fresh INST-002 context |
| Protected target/risk, charter, status, activation | INST-001 Founder |
| PR approval and merge | Independently authorized reviewer; never the campaign author by default |

The Institution may recommend PASS, BLOCK, CONDITIONAL, or UNKNOWN. It cannot accept Production
targets/risk, activate itself, merge, or turn its recommendation into protected authority.

## Mandatory Simulation Contracts

| ID | Proof required |
|---|---|
| SIM-QA-01 | Reject coverage inflation and prioritize consequential uncovered behavior |
| SIM-QA-02 | Derive an independent failing CCT from an approved claim |
| SIM-QA-03 | Prove tenant, stale-authority, replay, denial, and evidence integrity |
| SIM-QA-04 | Detect weak assertions through bounded mutation/property challenge |
| SIM-QA-05 | Detect OpenAPI/gRPC producer-consumer drift |
| SIM-QA-06 | Prove Emergency Stop and fail-safe dependency behavior under pressure |
| SIM-QA-07 | Bind promotion/recovery proof to immutable digests and state |
| SIM-QA-08 | Refuse a verdict when independence is absent |
| SIM-QA-09 | Fail closed when runner, collector, evidence sink, or environment is unavailable |
| SIM-QA-10 | Execute the BP 77.85%/65.81% to 90%/80% genuine-test pilot without owned-code exclusions |

## Tool And Technique Classification Proposal

| Class | Techniques | Business rule |
|---|---|---|
| Required baseline | Docker-only runners, pytest/pytest-cov, xUnit, Coverlet/Cobertura, raw evidence hashing | Required where the stack applies; C-080 and Evidence First |
| Required by risk | OpenAPI/gRPC contracts, tenant/security negatives, mutation/property sampling, performance/resilience/recovery/promotion, browser/accessibility | Campaign risk decides applicability; no silent omission |
| Evidence inputs | SAST, DAST, dependency, container, provenance, OTel, cost and environment records | Consume owner-produced evidence; never claim execution not performed |
| Conditional tools | Stack-specific mutation, property, load, chaos, browser and accessibility tools | EA/Security/Platform approve tool and least privilege before use |
| Prohibited | Host Python virtual environments, unapproved credentials, destructive Production experiments, fabricated or manually rewritten raw output | Always blocked |

No new MCP server is proposed by Business Architecture. Stage 6 architecture decides whether
existing runner/tool interfaces suffice. Any new MCP follows the complete architecture chain.

## Architecture Chain Impact Proposal

| Layer | Classification | Required downstream disposition |
|---|---|---|
| Business capabilities | REQUIRED | Domain 13 added in this contribution |
| Architectural drivers | CONDITIONALLY REQUIRED | EA determines whether independent qualification/tool isolation creates a new HARD constraint |
| Design principles | CONDITIONALLY REQUIRED | EA determines whether existing C-065/C-071 principles suffice |
| Institution Registry | REQUIRED AFTER RATIFICATION | CA records Founder-ratified CHARTERED/CAPABILITY DEVELOPMENT entry |
| ORGANIZATION charter | REQUIRED AFTER RATIFICATION | CA integrates the accepted office/institution boundary |
| Agent specification | REQUIRED AFTER AVD v1.0 | EA + AI Architect derive it from the ratified AVD |
| Prompt catalogue and seed | REQUIRED AT STAGE 6 | AI Architect defines approved prompts; implementation seeds only after approval |
| Containers/MCP catalogue/Compose | CONDITIONAL | Only if EA decides a new tool service is necessary |
| AI Runtime component | CONDITIONAL | Only for new orchestration behavior not covered by current runtime |
| Data schema/RLS | CONDITIONAL | Only for approved durable Quality Evidence Twin data beyond Goal evidence |
| Capability-to-container map | REQUIRED AT STAGE 6 | Map all approved skills to owning/supporting containers |
| AGENT-ENTRY/README/PROJECT_STATE | REQUIRED BY ACTIVATION | Update lifecycle truth without overstating status |
| ADR | CONDITIONAL | Only for a genuinely new architectural decision |
| Source/test implementation | PROHIBITED IN P1 | Separate implementation Goal and current-session authorization required |

## Capability Gap Discovered During Contribution

The accepted envelope requested a complete agent specification, but
`architecture/reference/agents/AGENT-AUTHORING-GUIDE.md` prohibits specification production until:

1. a Founder-ratified AVD v1.0 exists; and
2. an Institution Registry entry exists with status other than PROPOSED.

Neither prerequisite existed at P1-WC01 acceptance. The Business Architect therefore produced the
AVD and charter parameters and did not create `test-champion-agent.md`. This is a mandatory lifecycle
correction, not an incomplete draft. The Execution Plan must route AVD reviews and Founder
ratification before Stage 6 specification work.

## Required Reviews And Unresolved Owner Decisions

1. **INST-002:** validate constitutional basis, Decision Space, Code of Conduct, ledger/evidence
   boundaries, and proposed charter status.
2. **INST-004:** validate feasibility, tool isolation, CCT review model, architecture-chain impacts,
   and whether a new driver/principle/ADR is required.
3. **INST-008:** validate AI task categories, prompts, Quality Evidence Twin, deterministic-tool
   primacy, and model boundaries.
4. **Founder:** after all blocking review findings close, ratify or return AVD v0.2; assign the
   canonical ID and charter status.
5. **Stage 6 owners:** derive the agent spec only from AVD v1.0 and the chartered registry entry.

No reviewer may turn this proposal into an OPERATIONAL Institution. Operational readiness remains a
later simulation, clearance, and Founder decision.

## Boundary

This contribution creates no Institution, agent, registry entry, office charter, architecture,
prompt, tool, schema, source, test, cloud authority, quality verdict, activation, approval, or merge.
