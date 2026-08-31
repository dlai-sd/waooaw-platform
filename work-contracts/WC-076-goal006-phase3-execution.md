# WC-076 - GOAL-006 Phase 3 Execution

| Field | Value |
|---|---|
| Goal | GOAL-006 - Secure Autonomous Cloud Delivery Capability |
| Accountable owner | INST-009 - Platform Architect |
| Implementation executor | INST-010 - Platform IT Expert, Skill 17 |
| Authority | FA-052; GOA-GOAL-006-INST-010-03; ACC-GOAL-006-INST-010-03 |
| Scope | P3-EX01 through P3-EX11 in dependency order |
| Status | IN PROGRESS - P3-EX07 through P3-EX10 Demo/UAT deployment and verification passed; P3-EX11 dark-Production handover remains |

## Outcome

Deliver one signed exact-six release, qualify Demo and UAT with immutable-digest promotion, and
produce a dark-Production handover plan without activating customer traffic or Platform Operations.

## Execution

| Order | Work | Executor | Gate |
|---|---|---|---|
| 1 | P3-EX01 release-scan repair; P3-EX02 durable configuration; P3-EX03 Terraform identity outputs | INST-010 | Focused tests, impacted regression, independent review, Founder merge |
| 2 | P3-EX04 bootstrap OIDC verification | INST-009 with INST-007 review | Least privilege, exact subject, no client secret |
| 3 | P3-EX05 protected GitHub environments | Founder/admin | Orders 1-2 accepted; six protected environments |
| 4 | P3-EX06 signed exact-six release | INST-010 | Trusted-current-main release and immutable attestations |
| 5 | P3-EX07 through P3-EX10 Demo then UAT deployment and qualification | INST-009; independent QA confirms | Cost, recovery, security, digest and acceptance gates pass in sequence |
| 6 | P3-EX11 dark-Production plan and handover | INST-009 | No apply, traffic, activation or final Goal acceptance |

## Lightweight Evidence Rule

Code, tests and executable CI output are the primary evidence. Record only task status, immutable
commit/run/digest references and independent verdicts in this Work Contract or the PR; do not create
per-task evidence documents, duplicate pass reports or narrative handoff records.

## Execution Checkpoint

| Work | Status | Executable evidence |
|---|---|---|
| P3-EX01 | IMPLEMENTED - independent gate pending | Trivy SARIF severity contract; GOAL-006 Docker suite 187/187 |
| P3-EX02 | IMPLEMENTED - independent gate pending | Durable `WAOOAW_PLATFORM_*` migration contract; legacy runtime variables absent |
| P3-EX03 | IMPLEMENTED - independent gate pending | Demo/UAT root output tests; all six Terraform 1.9.8 roots validate |
| P3-EX04 tooling | READY FOR INST-009/007 | Read-only OIDC/RBAC verifier; four fail-closed Docker tests |
| P3-EX07 runner bootstrap | IMPLEMENTED - review pending | Inactive Demo Deployment Stack; digest-pinned runner image and lifecycle/private-path probes; Bicep compilation; no cloud mutation |
| P3-EX07 private signing broker | IMPLEMENTED - review pending | Dedicated private ACA start/cleanup brokers reuse the zero-idle environment, subnet, Key Vault endpoint, DNS, logs and runner image; 75 focused tests, Ruff, Bicep, image smoke and zero HIGH/CRITICAL OS scan pass; existing organization-installed GitHub App and FA-052 ceilings remain unchanged |
| P3-EX07 runner activation | VERIFIED | Run `33085991935`; private apply, exact-six inventory, functional verification, URL/ingress binding and cleanup passed; Founder acceptance remains separate |
| P3-EX08 Demo acceptance | ACCEPTED | Founder accepted the corrected Demo browser path and exact release on 2026-08-28 |
| P3-EX09 UAT runner and promotion | VERIFIED | Runner plan `33149859100`, apply `33150103583`, immutable release deployment, private cleanup and zero-idle evidence passed |
| P3-EX10 UAT qualification | VERIFIED | Run `33177257822`; exact-six inventory, latest-ready revisions, internal verification, Web HTTP 200 and OIDC HTTP 200 passed |
| P3-EX11 dark Production | PENDING | Code-prepared and runner blueprint `INACTIVE`; protected environments, authorized plan and handover evidence remain |

Detailed execution evidence is retained in `goals/GOAL-006-cloud-platform-finalization-evidence.md`.
The canonical operator entry is `.github/workflows/deploy.yaml`; reusable deployment and independent
verification remain in their owning workflows.

## Definition Of Done

P3-EX01 through P3-EX11 are complete only when their executable gates and independent acceptance
pass. Founder-reserved actions remain unexercised. The executor may not self-review, approve or merge.