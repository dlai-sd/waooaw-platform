# WC-124 - Demo Deployment Remediation Plan

## Record Control

| Field | Value |
|---|---|
| Office | Platform IT Expert |
| Authority | Founder authorization in the continuous WC-124 implementation conversation |
| Implementation issue | #532 |
| Delivery baseline | `19f79e1f7b17f2a40376d505d526f48b59e08755` from #534 |
| Failed deployment | Environment Deployment run `39060171367`, job `117476784862` |
| Environment boundary | Demo only |
| Delivery shape | One bounded investigation, one consolidated remediation branch, one frozen-candidate qualification, and one retrospective PR |
| Status | IMPLEMENTATION IN PROGRESS |

## 1. Objective And Authority Boundary

Recover the WC-124 Demo deployment without using official deployments as a one-defect-per-PR
debugging loop. Collect confirmed defects from the authorized run and retained plan, remediate them
together, qualify the frozen candidate locally, and submit one reviewable retrospective PR.

This plan does not authorize another Azure plan/apply, deployment, restore qualification, traffic
admission, UAT, or Production operation. Each of those requires separate Founder authorization.
The existing latest-`main` and GitHub OIDC trust boundaries remain unchanged. VM execution,
persistent credentials, experimental SAS authentication, and branch-deployment bypasses are
prohibited.

## 2. Execution Status

| Phase | Status | Exit evidence |
|---|---|---|
| Audit failed deployment and complete saved workload plan | DONE | Run `39060171367`; artifact `12110269768`; all 30 planned actions classified |
| Correct plan-policy false positives | DONE | Focused policy tests pass; exact saved workload plan returns `PASS` |
| Consolidate evidence-backed WC-124 repairs | IN PROGRESS | Provisioner TLS, bounded migrations, database handoff, workflow lifecycle, and sealed break-glass changes carried onto the branch |
| Qualify frozen remediation candidate | PENDING | Focused and broad local gates recorded with exact results |
| Prepare retrospective PR and Founder handoff | PENDING | C-059/C-065 preparation passes and one PR is opened without self-merge |

## 3. Confirmed Defect Register

| ID | Evidence | Root cause | Durable correction | Status |
|---|---|---|---|---|
| D-124-01 | Earlier provisioner execution | Python PostgreSQL client did not use the system CA bundle consistently | Bind the system CA bundle and report bounded connection failures safely | IMPLEMENTED |
| D-124-02 | Earlier cutover execution | Migration commands lacked deterministic execution bounds | Apply explicit migration timeouts and preserve exact failure output | IMPLEMENTED |
| D-124-03 | Earlier credential verification | PgBouncer secret role tag was compared with the catalog consumer principal | Verify the `pgbouncer_auth` role while retaining the `pgbouncer` consumer contract | IMPLEMENTED |
| D-124-04 | Earlier Container Apps job replacement | Deletion polling could continue after command errors or unknown state | Fail on CLI/API errors and unknown states; poll only explicit nonterminal states | IMPLEMENTED |
| D-124-05 | Earlier PostgreSQL handoff | Bootstrap authority and ownership transition were incomplete | Perform deterministic ownership handoff, revoke bootstrap ownership, and verify no shared dependencies remain | IMPLEMENTED |
| D-124-06 | Run `39060171367` saved plan | AzureRM represented unchanged optional role-assignment fields as `""` before and `null` after | Normalize blank/null only for `condition`, delegated identity, and description while preserving strict principal, role, scope, and replacement checks | IMPLEMENTED |
| D-124-07 | Run `39060171367` saved plan | Temporal policy still required the removed PostgreSQL sidecar and one active replica during the dormant phase | Require one digest-pinned Temporal container backed by external PostgreSQL; accept only dormant `0/1` or active `1/1` replica contracts | IMPLEMENTED |

## 4. Complete Plan Audit

The saved workload plan contains 30 actions:

- 16 expected creates for PgBouncer, Billing/Keycloak/Temporal migration jobs, four managed
  identities, and required database-secret role assignments.
- 13 expected in-place updates for dormant application templates, secret bindings, lease
  reconciliation, and verification execution.
- One accepted replacement:
  `module.workload.azurerm_role_assignment.temporal_secret[0]`, replacing only `scope` from the
  legacy `business-platform` secret to `db-temporal-runtime-demo`.

For the accepted replacement, the principal remains
`cb3198d4-856a-4631-a667-385aa46136e5`, the role remains `Key Vault Secrets User`, the Key Vault is
unchanged, and `replace_paths` is exactly `[["scope"]]`. No other destructive action was found.

## 5. Qualification Matrix

| Surface | Local/Codespaces evidence | Authorized-environment evidence |
|---|---|---|
| Python policy, workflow, and database helpers | Required | Optional confirmation |
| Terraform formatting and static validation | Required | Optional confirmation |
| Naming and workflow contracts | Required | Confirm in official run |
| Container image and lifecycle contracts | Required where locally executable | Required for private runtime |
| Remote Terraform state and AzureRM OIDC | Not equivalent locally | Run `39060171367` reached workload planning through the official path |
| Key Vault and PostgreSQL private access | Do not claim from Codespaces | Run `39060171367` confirmed pre-plan PostgreSQL success |
| Terraform apply and Container Apps execution | Not locally provable | Requires separately authorized deployment |

An inaccessible component is `BLOCKED`, never `PASS`. Local qualification cannot substitute for
official OIDC, private endpoint, apply, or runtime evidence.

## 6. Frozen-Candidate Exit Criteria

Before opening the PR:

1. Every confirmed defect is implemented with focused regression coverage.
2. Terraform formatting and affected Demo/UAT static validation pass.
3. Affected workflow, PostgreSQL, PgBouncer, Keycloak, Temporal, image, and lifecycle tests pass.
4. The exact saved workload plan passes the corrected closed-world policy.
5. Selective repository prechecks and PR-body C-059/C-065 preparation pass.
6. Any unprovable Azure behavior is recorded as residual integration risk, not reported as passing.
7. Temporary direct-execution Container Apps jobs and storage blobs are removed after retained
   evidence no longer depends on them.

## 7. Stop Rule

The remediation PR is ready when all defects discovered by the bounded audit are fixed and
regression-tested, or explicitly recorded as unresolved with an owner and reason. A later authorized
deployment is a qualification event, not permission to begin another automatic PR/deploy loop.
Any newly observed failure is reported as an explicit blocker for Founder disposition.
