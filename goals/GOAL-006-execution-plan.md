# GOAL-006 — Proposed Goal Execution Plan

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-006 |
| `record_id` | GEP-GOAL-006-INST-013-01 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-13T12:03:00+00:00 |
| Status | EXECUTION BASELINE - Phase 1 and Phase 2 complete; Demo/UAT accepted; WC-076 P3-EX11 plan-only closure remains |
| Governing requirements | Founder Session Directive plus GOAL-006 FR-001 through FR-056 |

## Historical Approval Stop

The following stop governed initial approval of this plan and is retained as historical evidence.
It was cleared by the recorded Phase 1 review, Founder acknowledgements and subsequent authorization
records. Current execution authority and limits are controlled by
`goals/GOAL-006-phase3-authorization-records.md`, including FA-052.

Before that clearance, no contributing Institution could accept or begin work, and INST-013 could
not issue a GO Authorization, until:

1. a fresh Constitutional Analyst reviews the provisional classification and this complete plan;
2. the R2-10 classification challenge is closed;
3. the Founder explicitly approves `GCL-GOAL-006-INST-013-01` and
   `GEP-GOAL-006-INST-013-01`; and
4. approval is recorded in an attested Acknowledgement Record.

## Goal Outcome And Delivery Model

Deliver one secure, reliable, cost-controlled Azure delivery capability through three strictly
sequential phases. Phase 1 creates implementation-ready owner decisions and Work Components;
Phase 2 implements and validates repository artifacts; Phase 3 creates and qualifies Azure
environments and completes operational handover. Each phase has a separate Founder control point.

The primary execution model is one accountable owner per complete Work Component. Specialist
contributions are routed only for material decisions within their Decision Spaces. INST-013
coordinates and preserves evidence but contributes no architecture, policy, product, security,
data, implementation, QA, or operational verdict.

## Contribution Necessity Gate

| Candidate contribution | Initial classification | Required handling |
|---|---|---|
| GEOM, constitutional controls, active vNext standard | REUSE | Hash-pin approved versions and validate scope/version/changed facts before routing |
| Accepted ADR-009/010/012/013/014/027 and established Azure/GHCR/GitHub/Terraform/OTel choices | PARTIAL REUSE CANDIDATE | Each owning architect performs the Contribution Reuse Test; changed requirements route only uncovered decisions |
| Existing Terraform, workflows, Docker topology, deployment scripts, observability, and Azure inventory | M2_CONTRIBUTE | Platform Architect owns current-state verification; repository presence is not operational proof |
| Product outcomes, SLO priorities, stories, acceptance, and cost/value tradeoffs | M2_CONTRIBUTE | Product Owner produces one complete outcome/grooming envelope |
| Cloud target topology, JIT lifecycle, IaC, CI/CD, reliability, DR, cost | M2_CONTRIBUTE | Platform Architect produces one complete architecture envelope |
| Component deployment and integration topology | M2_CONTRIBUTE | Solution Architect consumes approved platform architecture |
| Identity, ingress, isolation, secrets, TLS, supply chain, RBAC, threat model | M2_CONTRIBUTE | Security Architect produces one complete security envelope |
| Data isolation, masking, migration, backup, retention, restore | M2_CONTRIBUTE | Data Architect produces one complete data envelope |
| Pipeline and implementation feasibility | M2_CONTRIBUTE | INST-010 contributes feasibility only; no Phase 2 implementation authority |
| Qualification, performance, resilience, promotion, DR tests | M2_CONTRIBUTE | QA produces test and evidence architecture |
| Runbooks, alerts, autonomous boundaries, incident handling, handover | M2_CONTRIBUTE | Platform Operations contributes as DRAFT candidate only; contribution creates no activation |
| Constitutional readiness and final Phase 1 clearance | M3_DECIDE | Separate fresh INST-002 contexts preserve independence |
| URLs, costs above ceiling, DNS, production, cloud creation, agent activation | M3_DECIDE | Founder verdict required; dependent work stops |

## Phase Sequence And Gates

| Phase | Objective | Entry gate | Exit gate | Prohibited during phase |
|---|---|---|---|---|
| 1 — Discovery, Architecture, Grooming | Produce the complete FR-019 through FR-045 package and authorized Phase 2/3 Work Components | Founder-approved classification/plan and valid phased GOAs | Owner reviews, independent CA clearance, protected decisions identified, Founder package approval, authorized Phase 2 WCs | Runnable infrastructure changes, source implementation, cloud spend, deployment, DNS, activation |
| 2 — Implementation | Implement approved version-controlled IaC, workflows, controls, automation, tests, and operational artifacts | Phase 1 complete; explicit current-session Founder implementation authorization; approved Phase 2 WCs | Docker-based validation, security/cost checks, author review, required status checks and unmerged Founder PR | Azure creation, DNS change, production activation, self-approval, self-merge |
| 3 — Azure Deployment And Handover | Provision and qualify demo→UAT→production using immutable digests; activate accepted operations | Phase 2 merged; explicit Founder cloud/DNS/expenditure authorization | Production acceptance evidence, activated operations handover, supervised period, incident simulation, final Founder acceptance | Rebuild per environment, bypass gates, expose internal services, self-approve, self-merge |

## Phase 1 Work Components

| WC | Complete contribution envelope | Primary owner | Dependencies | Required output and gate |
|---|---|---|---|---|
| P1-WC01 | Current-State Inventory And Reuse/Gaps | Platform Architect | Approved plan | Verified inventory with hashes/live evidence, reuse tests, gaps, ownership, staleness, and no broad undocumented assumptions |
| P1-WC02 | Operational Outcomes, SLO Priorities, And Story Model | Product Owner | P1-WC01 | Customer/operator outcomes, SLO priorities, epics/stories with all FR-027 fields, acceptance, estimates, burden, and phase |
| P1-WC03 | Azure Environment, JIT, IaC, CI/CD, Reliability, DR, Cost Architecture | Platform Architect | P1-WC01, P1-WC02 | Demo/UAT/prod topology, JIT policy, immutable promotion, IaC layout, observability, scaling, continuity, cost model, six required conclusion tables |
| P1-WC04 | Deployable Component And Integration Topology | Solution Architect | P1-WC03 | Component placement, internal/public boundaries, ports/protocols, dependencies, health, configuration, failure/degradation, promotion contracts |
| P1-WC05 | Security Architecture And Threat Model | Security Architect | P1-WC01 through P1-WC04 | Identity, OIDC, RBAC, ingress/egress, private communication, TLS/DNS/certs, secrets, supply chain, WAF/rate limits, break glass, threats/tests |
| P1-WC06 | Data Isolation, Backup, Restore, Retention, And Migration | Data Architect | P1-WC01, P1-WC03, P1-WC04 | Environment data model, no-prod-data rules, state protection, backup/restore/retention/migration, RPO/RTO recommendations and tests |
| P1-WC07 | Implementation And Pipeline Feasibility | INST-010 Platform IT Expert | P1-WC03 through P1-WC06 | Feasibility findings, toolchain prerequisites, deterministic test strategy, implementation decomposition; no runnable changes |
| P1-WC08 | Qualification, Performance, Resilience, Promotion, And DR Test Plan | QA | P1-WC02 through P1-WC07 | Automated qualification matrix, load/cold-start/recovery targets, promotion/rollback/chaos/security/CCT evidence and environment acceptance |
| P1-WC09 | Operational Architecture, Policies, And Handover Acceptance | Platform Operations candidate | P1-WC02 through P1-WC08 | Runbooks/checklists, alert response, incidents/change/release/access/vulnerability operations, autonomous boundaries, handover tests; no activation |
| P1-WC10 | Platform Operations Spec Review And Activation Readiness | Enterprise Architect plus independent reviewers | P1-WC09 | Minimum corrections, Decision Space, permissions, operational acceptance, unresolved activation blockers; Founder activation remains separate |
| P1-WC11 | Integrated Grooming Package And Phase 2/3 Work Components | Product Owner primary; specialist owner reviews | P1-WC01 through P1-WC10 | One traceable package containing FR-019 through FR-045, complete ledgers/dependencies/estimates/costs/risks, and implementation/deployment WCs |
| P1-WC12 | Independent Constitutional Review And Founder Authorization Package | Fresh INST-002 validator; Founder decision | P1-WC11 and all owner reviews | Classification of residual risk, constitutional clearance or blocker, Founder actions, exact Phase 2 authorization boundary |

## Per-Institution Evidence Specifications

| Institution | Required record types | Minimum content | Participation Window | Independence constraint |
|---|---|---|---|---|
| INST-011 Product Owner | Outcome/Story Contribution; Integrated Grooming Contribution | FR-002 value order; SLO priorities; all FR-027 story fields; Phase 2/3 WCs; acceptance and cost/value decisions | 3 sessions per primary envelope | May not invent architecture, security, data, or implementation decisions |
| Platform Architect | Inventory Contribution; Platform Architecture Contribution | Verified current/live state; reuse tests; Azure/JIT/IaC/CI-CD/OTel/reliability/DR/cost design; required summary tables and exit paths | 4 sessions | May not self-approve integrated package or production activation |
| INST-005 Solution Architect | Solution Topology Contribution | Deployable components, configuration boundaries, protocols, health/dependency/failure contracts, no public CE | 2 sessions | Must consume approved platform decisions and identify conflicts rather than overwrite them |
| INST-007 Security Architect | Security Architecture; Threat Model; Security Review | Identity, OIDC, RBAC, network/ingress, TLS/DNS/certs, Key Vault, supply chain, scanning, break glass, threats and tests | 3 sessions | May not validate its own contribution as final package reviewer |
| INST-006 Data Architect | Data And Recovery Contribution | Environment isolation, masking, state, backup/restore, retention, migration, RPO/RTO, production-data prohibition | 2 sessions | May not approve platform cost or security architecture |
| INST-010 Platform IT Expert | Feasibility Contribution | Toolchain feasibility, pipeline constraints, deterministic/Docker testability, implementation decomposition, no code | 2 sessions | May not implement under Phase 1 GOA or review its later implementation |
| QA | Qualification Strategy Contribution | Automated functional/integration/CCT/security/performance/resilience/rollback/DR/promotion matrix and evidence | 2 sessions | Must remain independent of implementation execution |
| Platform Operations candidate | Operations And Handover Contribution | Runbooks, machine checklists, alert/incident boundaries, cost/drift/cert/backup duties, acceptance scenarios | 2 sessions | Draft status disclosed; contribution does not activate agent or grant live permissions |
| INST-004 Enterprise Architect | Platform Operations Readiness Review; architecture conflict review | Agent-spec corrections, Decision Space, cross-architecture coherence, unresolved ADR needs | 2 sessions | Reviews but does not activate Platform Operations or own specialist designs |
| INST-002 Constitutional Analyst | Classification Review; final Phase 1 Clearance | Independent G-3 review; complete FR traceability; Evidence First/Human Override/independence/authority findings | 1 session per protected verdict | Final validator must not have produced Phase 1 specialist contributions |
| INST-001 Founder | Acknowledgement; Protected Decision Records; Phase Authorization | Classification/plan approval, URLs/DNS/cost/production/activation decisions, exact next-phase boundary | Founder decision windows | No Institution or model substitutes for Founder verdict |

## Phase 1 Package Structure

The integrated grooming package must contain, in implementation-enabling order:

1. the complete Founder Session Directive, controlling requirements FR-001 through FR-056, and
  traceability matrix;
2. verified current-state inventory, reuse records, gaps, and assumptions;
3. target environments, lifecycle/JIT, IaC, CI/CD, security, data, observability, operations,
   reliability, DR, continuity, and cost designs;
4. implementable epics/stories/tasks and Phase 2/3 Work Components;
5. owner reviews, independent constitutional review, protected decisions, and Founder actions; and
6. the six mandatory conclusion tables with the exact columns in the Founder instruction.

The final Phase 1 PR body must state: **“The Founder Session Directive in
`goals/GOAL-006-founder-session-directive.md` and the normalized requirement baseline in
`goals/GOAL-006-secure-autonomous-cloud-delivery.md` FR-001 through FR-056 are retained and
controlling for this grooming package and all proposed downstream Work Components.”**

## Phase 2 Proposed Delivery Envelopes

Phase 1 owners must refine these into approved Work Components; this list is not implementation
authority:

1. Terraform foundations, remote state, policy, identity, and reusable modules.
2. Demo/UAT/production compositions with JIT leases and protected durable foundations.
3. Docker build-once provenance/SBOM/signing/scanning and immutable digest promotion.
4. GitHub reusable CI, Terraform, deployment, qualification, drift, halt, and DR workflows.
5. Azure Monitor/Application Insights, OTel, dashboards, alerts, synthetics, budgets, and actions.
6. DNS/TLS/ingress/security/secrets/certificates/RBAC and supply-chain controls.
7. Backup/restore/rollback/blue-green/DR and provider-outage automation.
8. Operational runbooks, machine-executable checklists, and Platform Operations integration.
9. IaC/workflow/policy/security/CCT/performance/resilience automated tests and evidence packaging.

## Phase 3 Proposed Delivery Envelopes

Phase 1 owners must refine these into approved Work Components; no Azure action is authorized:

1. Tenant/subscription/region/quota/identity/budget/DNS readiness.
2. State and foundational security provisioning.
3. Demo provisioning and lifecycle/recovery/monitoring/cost qualification.
4. Immutable UAT promotion and full qualification/approval.
5. Minimum safe production provisioning and same-digest promotion.
6. Production security, constitutional, customer-journey, reliability, recovery, and cost proof.
7. Platform Operations activation, supervised handover, and incident simulation.
8. Final evidence reports and Founder production acceptance.

## Completeness Ledger — Execution Status

| Obligation | Owner | Materiality | Required evidence | Dependencies | Status | Validation |
|---|---|---|---|---|---|---|
| PLAN-01 Classification review | Fresh INST-002 | M3 | Classification verdict | GUR/GCL | DONE | Independent review |
| PLAN-02 Registrant approval | Founder | M3 | Attested acknowledgement | PLAN-01 | DONE | Exact record IDs |
| PLAN-03 Phase 1 contributions | Specialist owners | M2 | P1-WC01 through P1-WC11 records | PLAN-02 and phased GOAs | DONE | Owner acceptance and deterministic checks |
| PLAN-04 Phase 1 clearance | Fresh INST-002 | M3 | Clearance Record | PLAN-03 | DONE | GEOM G-6 criteria |
| PLAN-05 Phase 2 authorization | Founder | M3 | Approved WCs plus session authorization | PLAN-04 | DONE | Explicit boundary |
| PLAN-06 Phase 2 implementation | INST-010 and approved owners | M2 | Tested implementation and independent reviews | PLAN-05 | DONE — PR #284 and closure PR #285 merged | Docker-only reproducible validation |
| PLAN-07 Phase 3 authorization | Founder | M3 | Cloud/DNS/expenditure authorization | PLAN-06 merged | DONE — FA-052 and Phase 3 GOA/Acceptance recorded | Exact protected decisions |
| PLAN-08 Deployment/handover | INST-009 accountable; INST-010 implements accepted architecture | M2/M3 | WC-076 executable gates, immutable PR evidence and Founder approval | PLAN-07 | IN PROGRESS - P3-EX01 through P3-EX10 passed; P3-EX11 plan-only closure remains | Author checks, required status checks and Founder approval |

## Dependency And Budget Controls

- Initial package review is complete, not delta-only. Later delta review requires a hash-pinned
  approved baseline and complete direct/indirect Dependency Impact Report.
- Every Phase 1 Work Component receives its own Completeness Ledger before acceptance.
- Default Phase 1 context budget: 12 primary owner envelopes, up to 4 bounded repair continuations,
  2 protected CA contexts, and Founder decision contexts only where listed.
- Default handoff budget: one acceptance and one contribution release per envelope; repeated
  handoffs trigger `STOP_AND_CONSOLIDATE`.
- Monetary dispatch ceiling is not set by this proposal. No paid model or cloud expenditure may be
  inferred. A Founder-set ceiling is required before chargeable execution.
- At 80% budget use or repeated context, stop dispatch, deduplicate evidence, combine unresolved
  owner questions, and recalculate. At forecast >100% or changed assumptions, `REPLAN_REQUIRED`.

## Remediation And Stops

Apply GEOM L1→L2→L3 remediation to validation or alignment failures. Stop immediately for
conflicting protected verdicts, missing authority, invalid GOA chronology, public CE exposure,
Evidence First bypass, Emergency Stop degradation, unsafe durable-data destruction, secret
exposure, attempted environment rebuild, production/DNS/cloud action without Founder authority,
or attempted Platform Operations activation before acceptance.

## Next Action

Use `work-contracts/WC-076-goal006-phase3-execution.md` as the single remaining execution record.
After this PR merges, INST-009 resolves the listed Production architecture inputs and INST-010 may
produce offline readiness evidence under fresh implementation authority. Provider-backed planning
requires exact current-session Founder authority; Production apply, DNS, customer traffic, Platform
Operations activation, PR approval and merge remain Founder-reserved.
