# WC-076 - GOAL-006 Phase 3 Execution

| Field | Value |
|---|---|
| Goal | GOAL-006 - Secure Autonomous Cloud Delivery Capability |
| Accountable owner | INST-009 - Platform Architect |
| Implementation executor | INST-010 - Platform IT Expert, Skill 17 |
| Governing envelope | FA-052; GOA-GOAL-006-P3-AUTONOMOUS-01; ACC-GOAL-006-P3-AUTONOMOUS-01 |
| Current-session authority | Founder-authorized institutional review and document repair on 2026-08-31; no provider call, runnable implementation or Production activation is inferred |
| Scope | P3-EX01 through P3-EX11 in dependency order |
| Current baseline | PR #371 accepted Demo/UAT delivery; this PR consolidates cloud workflows and strategy |
| Status | IN PROGRESS - P3-EX01 through P3-EX10 passed; P3-EX11 dark-Production plan and handover remain |

## Outcome

Deliver one signed exact-six release, qualify Demo and UAT with immutable-digest promotion, and
produce a dark-Production handover plan without activating customer traffic or Platform Operations.

## Execution

| Order | Work | Accountable / executor | Gate |
|---|---|---|---|
| 1 | P3-EX01 through P3-EX06 release, configuration, identity and protected-environment prerequisites | INST-009 / INST-010; Founder/admin for protected environments | Accepted implementation, executable checks and Founder merge |
| 2 | P3-EX07 through P3-EX10 Demo then UAT deployment and qualification | INST-009 / INST-010 | Cost, recovery, security, digest, verification and Founder acceptance gates pass in sequence |
| 3 | P3-EX11 dark-Production plan and handover | INST-009 / INST-010 | Plan-only outputs below pass; no apply, DNS change, traffic, activation or final Goal acceptance |

INST-009 owns Production architecture and accepts or rejects architecture inputs. INST-010 authors
the plan, workflow/configuration changes and executable evidence inside accepted architecture.
INST-007 owns security requirements and activation blockers. INST-015 qualifies executable checks
when independently requested. These specialist contributions do not approve this PR: the Founder
alone reviews and merges it and separately authorizes any Production provider action.

## P3-EX11 Inputs And Outputs

### Inputs required before provider-backed plan generation

1. Founder merge of this PR, so the execution branch contains the canonical capability workflows
	and evidence paths rather than legacy GOAL-006 workflow names.
2. The exact UAT-verified release SHA, exact-six image digests and configuration digest.
3. Accepted Production edge, DNS, data, runtime, recovery and cost inputs owned by INST-009 and the
	relevant specialist institutions.
4. An accepted owner and lifecycle for the shared Terraform state account and Production state
	keys, including least-privilege OIDC/RBAC boundaries.
5. Protected `prod` and `prod-verification` GitHub environments with `main`-only deployment policy,
	environment-scoped variables and Founder approval boundaries.
6. Exact current-session Founder authority for any GitHub or Azure provider call. Plan readiness
	and PR merge do not grant this authority.

### Required outputs

| Output | Acceptance |
|---|---|
| Immutable input record | Binds commit SHA, UAT-verified exact-six digests, configuration digest and environment without mutable tags or rebuild |
| Production Terraform readiness | Production foundation and workload roots format, initialize with `-backend=false` and validate under Terraform 1.9.8 |
| Deployment guard proof | Canonical `deploy.yaml` and reusable deployment engine expose Production plan separately from apply; no alternate deployment entry bypasses protected environments |
| Security boundary proof | Static checks cover exact OIDC subjects, environment-isolated RBAC/state/secrets, private-path requirements and absence of long-lived credentials |
| Plan review record | When separately authorized, the saved Production plan and digest record creates/updates/deletes, cost and rollback impact; destructive or unexplained change blocks |
| No-mutation handover | PR evidence identifies commands, immutable references and verdicts and confirms no Production apply, DNS change, customer traffic or Platform Operations activation |
| Activation blocker register | C-001 emergency-halt integration and all unresolved Production architecture, security, data, operations and Founder decisions remain explicit blockers to apply/activation |

Offline readiness does not require cloud credentials or live Production state. A provider-backed
plan is not simulated by claiming that an offline validation is a Terraform plan. It remains
blocked until all inputs and exact Founder authority above are present.

## Lightweight Evidence Rule

Code, tests and executable CI output are the primary evidence. Record only task status, immutable
commit/run/digest references and independent verdicts in this Work Contract or the PR; do not create
per-task evidence documents, duplicate pass reports or narrative handoff records.

## Executable Gates

Run the repository-supported checks against the final branch:

```bash
docker compose run --rm test-runner pytest -q tests/pipeline
docker run --rm -v "$PWD:/repo:ro" -w /repo rhysd/actionlint:1.7.7 \
	.github/workflows/ci.yaml \
	.github/workflows/deploy.yaml \
	.github/workflows/environment-deployment.yaml \
	.github/workflows/environment-deployment-verification.yaml \
	.github/workflows/private-runner-infrastructure.yaml \
	.github/workflows/private-runner-image.yaml \
	.github/workflows/workload-lease-reconciliation.yaml
```

Validate all environment roots in a disposable copy with Terraform 1.9.8 using
`init -backend=false -input=false -no-color` followed by `validate -no-color`. Run the existing
provider-free release simulation, secret/security checks, C-059/C-065 validators and
`git diff --check`. Record results once in the PR; do not create duplicate review or evidence files.

## Execution Checkpoint

| Work | Status | Executable evidence |
|---|---|---|
| P3-EX01 through P3-EX06 | PASSED | PR #371 baseline contains the accepted exact-six release, configuration, identity and prerequisite evidence |
| P3-EX07 / P3-EX08 Demo deployment and acceptance | ACCEPTED | Corrective run `33147562517`; Founder accepted the corrected Demo browser path and exact release on 2026-08-28 |
| P3-EX09 UAT runner and promotion | VERIFIED | Runner plan `33149859100`, apply `33150103583`, immutable release deployment, private cleanup and zero-idle evidence passed |
| P3-EX10 UAT qualification | VERIFIED | Run `33177257822`; exact-six inventory, latest-ready revisions, internal verification, Web HTTP 200 and OIDC HTTP 200 passed |
| P3-EX11 offline readiness | PENDING | Current workflow topology, Production roots and plan-only guards must pass the executable gates above |
| P3-EX11 provider-backed plan | BLOCKED | Production inputs, protected environments, state ownership and exact current-session provider authority remain required |
| Production apply / activation | PROHIBITED | Requires separate Founder authority after C-001 and all Production readiness gates pass |

Detailed execution evidence is retained in `goals/GOAL-006-cloud-platform-finalization-evidence.md`.
The canonical operator entry is `.github/workflows/deploy.yaml`; reusable deployment and independent
verification remain in their owning workflows.

## Definition Of Done

P3-EX11 closes only when every required output has an immutable reference and an executable verdict
recorded in this Work Contract or the PR. Offline readiness may pass while the provider-backed plan
remains blocked; that is not Production acceptance. INST-010 performs an engineering author check,
not institutional review or approval, and may not approve or merge the PR. Founder-reserved actions
remain unexercised.