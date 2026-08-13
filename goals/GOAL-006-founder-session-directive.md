# GOAL-006 — Founder Session Directive

**Issued by:** Yogesh Khandge, Founder (INST-001)
**Issued:** 2026-08-13
**Captured by:** Goal Orchestrator (INST-013)
**Applies to:** GOAL-006 — Secure Autonomous Cloud Delivery Capability
**Status:** CONTROLLING SOURCE DIRECTIVE — no implementation, cloud, DNS, or activation authority
**Normalized traceability:** `goals/GOAL-006-secure-autonomous-cloud-delivery.md` FR-001 through FR-056

## Purpose

This document durably captures the Founder's session-start instruction for GOAL-006. It is the
human-readable source directive for Phase 1 discovery, architecture, and grooming. The normalized
FR-001 through FR-056 baseline exists for deterministic traceability; it does not replace or narrow
this directive.

Every Phase 1 contribution, Work Component, review, and final PR must preserve this directive. If a
normalized requirement appears ambiguous or incomplete, the Founder intent recorded here controls
and the ambiguity is routed to the proper owner or Founder rather than silently resolved.

## Founder Goal

Establish an industry-grade, secure, cost-controlled, and autonomously operated cloud delivery
capability for WAOOAW.

The capability must cover:

- Azure cloud architecture and infrastructure management.
- Docker-based application packaging.
- Infrastructure as Code.
- GitHub Actions CI/CD.
- Immutable image promotion from demo to UAT to production.
- Automated environment provisioning and shutdown.
- Cloud observability, alerting, incident response, and recovery.
- Security, secrets, certificates, DNS, and environment isolation.
- Cost, capacity, reliability, and performance management.
- Operational handover to the WAOOAW AI Agent — Platform Operations.

## Customer-Value Principle

Prioritize reliable customer access, deployment safety, service health, security, recoverability,
performance, and controlled cloud cost.

Do not create documentation solely for process compliance. Every policy, standard, architecture
decision, checklist, or evidence record must directly enable implementation, operation, risk
control, or independent verification.

## Proposed Environment Addresses

Treat this mapping as proposed and obtain Founder confirmation before making DNS or production
decisions:

| Environment | Web URL | API URL |
|---|---|---|
| Demo | `https://www.demo.waooaw.com` | `https://api.demo.waooaw.com` |
| UAT | `https://www.uat.waooaw.com` | `https://api.uat.waooaw.com` |
| Production | `https://www.waooaw.com` | `https://api.waooaw.com` |

The Founder owns `waooaw.com`.

Use environment-specific subdomains, TLS, secure API ingress, restrictive CORS, workload identity,
managed secrets, private internal service communication, rate limiting, WAF controls where
justified, and WAOOAW's existing constitutional security requirements.

Do not expose the Constitutional Engine or other internal-only services directly to the internet.

## Operating Model

The work has three sequential phases. Do not combine or skip phases.

### Phase 1 — Discovery, Architecture, And Grooming

Study WAOOAW's actual business model, constitutional controls, service architecture, source layout,
Docker topology, data stores, external dependencies, existing Terraform, Azure resources, GitHub
Actions workflows, security architecture, ADRs, deployment scripts, observability decisions, cost
limits, and operational-agent specifications.

Use existing approved decisions whenever they remain suitable. In particular, evaluate the current
Azure-first architecture, Azure Container Apps, PostgreSQL, Keycloak, Temporal, Azure
Monitor/Application Insights, OpenTelemetry, Key Vault, GitHub Actions, GHCR, Docker, and
Terraform.

Do not introduce Kubernetes, Nexus, Grafana, or another platform merely because it is common.
Introduce a tool only where evidence shows a capability gap and its operational value exceeds its
cost and complexity.

Evaluate GHCR against Nexus or Azure Container Registry. GHCR is the current approved registry
under ADR-012 and should remain the default unless a material requirement proves it insufficient.
Any replacement requires an architecture decision and migration analysis.

Route the required contributions to their proper owners:

- Product Owner: operational outcomes, priorities, stories, and acceptance.
- Platform Architect: Azure topology, environment model, IaC, CI/CD, observability, reliability,
  scaling, disaster recovery, and cost design.
- Solution Architect: deployable component topology and integration design.
- Security Architect: identity, ingress, network boundaries, secrets, TLS, supply-chain security,
  RBAC, and threat model.
- Data Architect: environment data isolation, backup, restore, retention, migration, and
  production-data restrictions.
- Runtime Implementation Professional / Platform IT Expert: implementation feasibility and
  pipeline requirements.
- QA: environment qualification, performance, resilience, and promotion tests.
- Platform Operations: operational requirements, runbooks, alert handling, autonomous actions,
  incident boundaries, and handover acceptance.
- Constitutional Analyst: independent constitutional review.
- Founder: protected decisions, costs above the approved ceiling, production activation, DNS
  changes, and agent activation.

Platform Operations is currently a draft, non-activated agent. Include the minimum review,
correction, acceptance, and Founder activation work needed before it can own live operations. Do
not silently treat it as active.

### Phase 1 Deliverables

Produce a groomed, implementation-ready package containing:

1. Current-state inventory and verified gaps.
2. Target environment architecture for demo, UAT, and production.
3. Environment lifecycle and just-in-time operating policy.
4. CI/CD and immutable image promotion architecture.
5. Infrastructure as Code architecture and repository layout.
6. Cloud security architecture and threat model.
7. Observability and operational architecture.
8. Backup, restoration, rollback, disaster-recovery, and continuity design.
9. Incident, change, release, access, and vulnerability-management policies.
10. Platform Operations activation and operational handover plan.
11. Epics, stories, tasks, dependencies, estimates, and acceptance criteria.
12. Phase 2 implementation Work Components.
13. Phase 3 Azure deployment and environment qualification Work Components.
14. Risks, protected decisions, assumptions, and Founder actions.
15. Cost model and cost-control thresholds.
16. Independent review and authorization package.

Each story must include:

- Story ID and user/operator value.
- Owning Institution.
- Scope and explicit exclusions.
- Dependencies.
- Architecture or policy basis.
- Security and constitutional obligations.
- Acceptance criteria.
- Required automated tests.
- Required evidence.
- Rollback or recovery expectation.
- Size estimate.
- One-time implementation cost.
- Expected monthly cloud cost.
- Operational burden.
- Phase assignment.

## Just-In-Time Environment Requirements

Design demo and UAT to exist or consume material resources only when needed.

Evaluate and recommend the safest combination of scale-to-zero for stateless Container Apps,
scheduled start and stop, workflow-dispatch activation, pull-request or release-triggered
provisioning, automatic expiry through leases and TTL, Terraform-managed creation/destruction,
persistent shared foundations, disposable compute with retained encrypted data, database pause or
serverless alternatives, pre-shutdown backup, post-start health verification, unavailable-DNS
behavior, maximum startup time, inactivity shutdown, budgets, anomaly alerts, and emergency
shutdown.

Do not destroy durable data, audit records, Terraform state, Key Vault material, DNS zones, or
required recovery evidence during automated shutdown.

Production must remain available using the smallest configuration that still satisfies customer
safety, constitutional enforcement, backup, recovery, security, and agreed service objectives.
Bare minimum must not create an unprotected single point of failure where customer or
constitutional risk requires resilience.

## Immutable Promotion Requirement

Build each release image once and promote the exact same image digest through:

```text
source commit
  -> CI verification
  -> registry immutable digest
  -> demo deployment
  -> demo qualification
  -> UAT promotion
  -> UAT qualification and approval
  -> production promotion
  -> post-production verification
```

Never rebuild source separately for UAT or production. Environment-specific behavior must come
only from reviewed configuration, managed identity, Key Vault references, feature controls, and
environment settings. Never bake environment secrets into images.

Define provenance, SBOM generation, signing, vulnerability scanning, attestation, retention,
rollback, and promotion evidence.

## CI/CD Requirements

The design must include:

- Pull-request build, lint, unit, integration, contract, CCT, and security gates.
- Docker image build, deterministic tagging, and immutable digest recording.
- SBOM, image signing, dependency/secret/SAST/container/IaC scanning.
- Terraform format, validate, lint, security scan, plan, approval, and apply.
- GitHub deployment environments and least-privilege approval gates.
- Workload identity federation with no long-lived Azure credentials.
- Demo deployment with automated smoke/CCT verification.
- UAT promotion with qualification evidence.
- Production promotion with Founder-reserved authorization.
- Blue-green or equivalent low-risk release and explicit-health automated rollback.
- Deployment evidence/audit retention and pipeline emergency halt.
- Failure classification, retries, escalation, concurrency protection, drift detection, controlled
  reconciliation, and disaster-recovery workflow tests.

## Observability Requirements

Use OpenTelemetry as the instrumentation standard. Evaluate the existing Azure
Monitor/Application Insights architecture and define:

- Logs, metrics, traces, events, dashboards, workbooks, and alerts.
- Service, dependency, deployment, and release health.
- Evidence First and Emergency Stop latency metrics.
- Customer journey and business-outcome signals.
- API latency, throughput, errors, saturation, and availability.
- Database, Temporal, Keycloak, Container Apps, certificates, DNS, queues, external providers, and
  cost signals.
- SLOs, SLIs, error budgets, thresholds, and escalation paths.
- Structured logging with correlation and tenant-safe dimensions.
- PII/secret redaction, retention/cost controls, external synthetic checks, deduplication/noise
  control, Platform Operations response boundaries, daily health summaries, and monthly
  reliability/cost reviews.

## Architecture And Security Decisions To Resolve Or Route

- Azure primary and disaster-recovery regions.
- Subscription/resource-group separation and separate/shared data services.
- Network isolation/private endpoints and public ingress boundaries.
- API gateway, Front Door, CDN, WAF, and DNS requirements.
- Managed certificates and renewal.
- GitHub Actions and Platform Operations identity.
- Terraform state storage, locking, backup, and access.
- Secret rotation, production access, and break-glass controls.
- Backup frequency/retention and RPO/RTO.
- Data masking and prohibition of production customer data in demo/UAT.
- Capacity/scaling limits and sandbox versus production provider credentials.
- Dependency/provider outage behavior.
- Azure portability and documented escape hatches.

## Mandatory Phase 1 Conclusion Tables

End the grooming package with these tables using the stated columns:

### A. Component And Cost Summary

| Component | Purpose | Azure/tool option | Environment | Always on or JIT | Size/SKU | One-time cost | Monthly baseline | Monthly active-use cost | Cost control | Owner |
|---|---|---|---|---|---|---|---|---|---|---|

### B. Performance And Reliability Summary

| Component | Expected load | Latency target | Availability target | Scaling rule | Cold-start target | RPO | RTO | Monitoring signal | Failure response |
|---|---|---|---|---|---|---|---|---|---|

### C. Delivery Tool Decision Summary

| Capability | Existing tool | Alternatives evaluated | Selected tool | Why selected | Cost | Lock-in/exit path | Decision/ADR needed |
|---|---|---|---|---|---|---|---|

### D. Story And Delivery Summary

| Epic/story | Objective | Owner | Dependencies | Size | Implementation estimate | Cloud cost impact | Phase | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|

### E. Environment Summary

| Environment | Purpose | URL/API | Provision trigger | Shutdown trigger | Data treatment | Promotion gate | Monthly ceiling | Operator |
|---|---|---|---|---|---|---|---|---|

### F. Risk And Decision Summary

| Risk/decision | Impact | Recommendation | Owner | Founder decision required | Deadline | Blocking work |
|---|---|---|---|---|---|---|

All monetary estimates must state currency, pricing date, Azure region, assumptions, taxes
excluded/included, and confidence range. Prefer INR, with the underlying Azure billing currency
noted.

## Phase 1 Stop Condition

Stop after the complete grooming package has passed owner reviews and independent constitutional
review, identified all Founder-reserved decisions, received Founder approval, and produced
authorized Phase 2 Work Components. Do not create or modify runnable infrastructure during Phase 1.

## Phase 2 — Implementation

Begin only after explicit Founder authorization for the implementation session and approved Phase
2 Work Components.

Implement the approved package as version-controlled artifacts, including reusable Terraform
modules; demo/UAT/production composition; remote state/locking; reusable GitHub Actions workflows;
immutable promotion/provenance/signing/SBOM/scanning; activation/lease/shutdown/recovery automation;
Azure Monitor/Application Insights, dashboards, alerts, budgets, DNS/certificates; backup/restore/
rollback/DR; policy-as-code/security checks; machine-executable runbooks/checklists; Platform
Operations integration/permissions; and automated IaC/workflow tests.

Use Docker for repository execution and testing as required by C-080. Do not create or use a Python
virtual environment.

Phase 2 finishes with independent review, reproducible validation, security verification,
cost-plan review, and an unmerged PR for Founder approval.

## Phase 3 — Azure Deployment And Handover

Begin only after Phase 2 is merged and the Founder explicitly authorizes cloud creation, DNS
changes, and expenditure. Execute in this order:

1. Validate Azure tenant, subscription, region, quotas, identities, budgets, and DNS control.
2. Establish Terraform state and foundational security resources.
3. Provision and qualify demo.
4. Prove activation, shutdown, restart, expiry, backup, restore, monitoring, and cost controls.
5. Promote the same immutable images to UAT.
6. Execute functional, integration, CCT, security, performance, resilience, rollback, and
   operational acceptance tests.
7. Obtain UAT approval.
8. Provision the minimum production topology.
9. Promote the same approved image digests to production.
10. Verify DNS, TLS, security headers, APIs, observability, backups, alerts, rollback, Emergency
    Stop, Evidence First, and customer journeys.
11. Complete Platform Operations activation and handover.
12. Run a supervised operational period and incident simulation.
13. Produce final cost, performance, reliability, security, and evidence reports.
14. Present production acceptance to the Founder.
15. Do not self-approve or self-merge.

## Platform Operations Handover Acceptance

Handover is complete only when Platform Operations can, within its approved Decision Space:

- Activate and shut down demo/UAT safely.
- Observe every environment and release.
- Diagnose pipeline/deployment failures and respond to alerts/incidents.
- Retry or roll back permitted failures and escalate protected events.
- Monitor cost and enforce approved thresholds.
- Verify backups and perform tested restoration.
- Detect configuration/infrastructure drift.
- Manage certificate and secret-rotation alerts.
- Produce daily health/cost summaries.
- Execute runbooks through machine-verifiable checklists.
- Prove all actions through retained operational evidence.

## Final Controls

First produce a Goal Understanding Record and proposed Goal Execution Plan. Do not begin grooming
contributions until the Founder approves the Goal classification and plan.

At every phase, reuse approved WAOOAW architecture and evidence where valid. Do not invent
authority, activate Platform Operations, spend Azure funds, change DNS, deploy, or write
implementation artifacts without the required owner and Founder decisions.

Retain these instructions under the requirements section of the grooming documentation and note
their retention in the Phase 1 PR. Phase 2 scope and implementation belong to a later, separately
authorized PR.
