# WC-101 - Docker-Only Validation Architecture

## Record Control

| Field | Value |
|---|---|
| Office | Chief Enterprise Architect (INST-004) |
| Assigned by | Founder authorization in the 2026-09-19 continuous working conversation |
| Status | DONE - FOUNDER ACCEPTED 2026-09-19 |
| Scope | Reference Architecture strategy and one architectural decision for AI-operated Docker-only validation |
| Inputs | C-059, C-065, C-071, C-076, C-077, C-080 and C-086; ADR-012, ADR-013 and ADR-045; current Docker Compose and GitHub Actions implementation |
| Outputs | `architecture/reference/docker-only-validation-strategy.md`; ADR-050; Solution Architect handoff |
| Implementation | NOT AUTHORIZED |

## 1. Authority And Decision Space

The Enterprise Architect may define the validation-system boundaries, trust model, reusable image
contract, failure-evidence contract, gate topology and relationship to existing architecture. This
Work Contract does not authorize implementation, workflow execution, image publication, registry or
cloud mutation, branch-protection changes, PR approval or merge.

The Enterprise Architect cannot approve its own outputs. Founder acceptance is required before the
architecture is treated as accepted or passed to Solution Architecture as an approved implementation
input.

## 2. Required Outcome

Produce a lightweight architecture that:

1. preserves Docker-only test execution and every existing constitutional quality gate;
2. separates rapid AI-agent feedback from clean candidate qualification without creating two truths;
3. rebuilds test environments only when their dependency inputs change;
4. selects affected validation from one fail-closed ownership and dependency catalog;
5. gives agents a bounded machine-readable first-cause failure record;
6. prevents stale containers, mutable tags, caches or prior results from authorizing PASS; and
7. supplies Solution Architecture with measurable outcomes and rollout constraints.

## 3. Required Inputs

| Input | Status | Use |
|---|---|---|
| C-059, C-065, C-071, C-076, C-077, C-080, C-086 | RATIFIED | Traceability, authority, quality, coverage, economy, Docker isolation and pre-execution proof |
| ADR-012 and ADR-013 | ACCEPTED | Registry and CI/CD trust boundaries |
| ADR-045 | ACCEPTED | Existing per-stack lean runner decision |
| Current Compose, runner Dockerfiles and workflows | PRESENT | Implementation baseline and drift evidence |
| WC-100 draft | UNAPPROVED INPUT FOR RECONCILIATION ONLY | Existing Solution Architecture proposal; not an authority source |

All authoritative inputs required for Enterprise Architecture are present. WC-100 remains a draft
and cannot approve or constrain the architecture independently.

## 4. Acceptance Conditions

1. The strategy traces to approved capabilities, drivers, principles, claims and existing ADRs.
2. ADR-050 extends rather than duplicates or contradicts ADR-045 and ADR-013.
3. The design defines focused and qualification modes, cache authority, exact input identity,
   fail-closed impact selection, structured failure evidence and Docker-only enforcement.
4. The design introduces no new runtime service, customer data store, application API or cloud
   platform dependency.
5. Speed outcomes are expressed as targets requiring measured baseline and candidate evidence, not
   as unsupported guarantees.
6. Enterprise Architecture author review finds no unresolved scope, authority, security,
   operability, rollback or traceability issue.
7. The Founder explicitly accepts or amends the strategy and ADR before their status becomes
   Accepted.

## 5. Stop Conditions

Stop for Founder or owning-office decision if the design would lower a quality threshold, bypass a
required gate, trust local evidence as CI evidence, require a third-party orchestration platform,
change protected merge authority, expose the Docker socket broadly, or create application/runtime
behavior.

## 6. Definition Of Done

WC-101 is complete only when the strategy and ADR exist, Enterprise Architecture author review is
complete, the Founder has accepted the decision, and the complete approved context has been handed
to Solution Architecture for reconciliation into an implementation-ready Work Contract. No
implementation may begin under WC-101.

## 7. Enterprise Architecture Author Review

The authored outputs were checked against the approved claims and ADRs, current repository evidence,
scope boundaries, failure modes, security, operability, reversibility and measurable outcomes. The
design retains all mandatory gates, uses existing GitHub Actions, GHCR, Docker Compose and test
frameworks, and adds no deployable platform component.

**Disposition:** FOUNDER ACCEPTED 2026-09-19. IMPLEMENTATION NOT AUTHORIZED.
