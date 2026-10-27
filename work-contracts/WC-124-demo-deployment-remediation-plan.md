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
| Status | LOCAL QUALIFICATION COMPLETE - PR PREPARATION IN PROGRESS |

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
| Consolidate evidence-backed WC-124 repairs | DONE | Provisioner TLS, bounded migrations, database handoff, workflow lifecycle, and sealed break-glass changes carried onto the branch |
| Qualify frozen remediation candidate | DONE | Focused tests, six Terraform roots, runner image, emulator lifecycle, GOAL-006 suite, and persistent-state gates pass |
| Prepare retrospective PR and Founder handoff | IN PROGRESS | C-059/C-065 preparation passes and one PR is opened without self-merge |

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

## 8. Frozen-Candidate Evidence

| Qualification | Result |
|---|---|
| Exact saved `workload-plan.json` through corrected plan policy | PASS - zero destructive changes |
| Focused WC-124 workflow, policy, runner, provisioner, and handoff tests | PASS - 121 tests |
| Complete GOAL-006 pipeline suite | PASS - 542 tests |
| Exact WC-124 persistent-state CI gate with live local PostgreSQL and PgBouncer | PASS - 126 tests |
| GitHub Actions lint | PASS |
| Terraform 1.9.8 validation | PASS - Demo, UAT, and Production foundation/workload roots |
| Lease-controlled Terraform membership plan | PASS |
| Docker Azure CLI end-to-end deployment emulator | PASS - positive deployment, negative deployment, and cleanup broker |
| Private-runner image build from `infrastructure/runner/Dockerfile` | PASS |
| Ruff checks and formatting for changed Python surfaces | PASS |

The official run, not Codespaces, remains the authority for private remote state, Key Vault,
PostgreSQL, OIDC, Terraform apply, and Container Apps runtime behavior.

## 9. Cleanup Record And Residual Risk

The three temporary direct-execution Container Apps jobs were deleted and control-plane queries
verified that they are absent:

- `waooaw-demo-rg/job-demo-direct-workload`
- `waooaw-demo-runner-rg/job-demo-direct-workload`
- `waooaw-demo-runner-rg/job-demo-direct-stage`

Two temporary direct-execution blobs may remain under
`deployment-config/demo/direct-execution/`. Codespaces cannot access that private data plane, and
using account keys, a new SAS workaround, or an ad hoc privileged job would violate this plan's
trust boundary. Their removal is assigned to the Platform IT Expert in the next separately
authorized private cleanup execution:

- `run-workload-apply.sh`
- `registry-release-manifest.json`

## 10. Run 39706644135 Handoff Follow-Up

Founder-authorized implementation on 2026-10-27 is limited to the failed deployment of
PR #547 (`7c64918bcc930c1987df682fbcdeba3140ba7cb4`). The repair branch is
`ib/124/deployment-handoff-repair`, based on `main` at `19a73dce`.
This follow-up does not authorize a live deployment, database reset, state unlock, provider
mutation, UAT/Production operation, approval, or merge.

| Defect | Evidence | Correction and falsifying check |
|---|---|---|
| Handoff command argument parsing | The handoff step failed in one second; the provisioner still had its original reset arguments and no handoff execution existed. The pinned CLI rejects the inline `--environment` and subsequent script flags as unrecognized job-update options. Failed-job logs are unavailable (`log not found: 119588999573`), so the command diagnosis is supported by reproduction and observed job state, not a quoted workflow log. | Render the existing job as a structured JSON/YAML definition and replace only its command/arguments. Execute the actual workflow shell for Demo/UAT, reject update failures and nonzero bootstrap dependencies, and exercise the real pinned CLI PATCH against the local Azure emulator. |
| Normal revocation attempted without completed handoff | Azure Activity Log correlations `628e77e3-a4f3-41de-bb4c-845a67e7cfa9` and `24080c07-7701-46aa-8dfd-655c19d92509` report `AadAuthPrincipalDropFailed`, SQLSTATE `2BP01`: bootstrap-owned objects prevented role deletion. | Require successful normal or recovery handoff when that transition is required. Preserve unconditional terminal cleanup and its zero-authority assertions; a cleanup failure must remain a failed deployment. |
| Deletion retries consumed the runner window | Normal removal lasted 30 minutes 46 seconds; terminal cleanup never reported completion. ADR-047 fixes the runner lifetime at 60 minutes. The exact runner termination cause is unproven without execution diagnostics. | Bound the Terraform bootstrap-administrator delete to five minutes for both removal paths without extending runner life, bypassing locks, or relaxing zero-authority checks. |

Focused Docker qualification passes 131 tests covering the workflow, Terraform foundation,
and database handoff. The pinned CLI emulator qualification passes the structured handoff
PATCH, positive deployment, unhealthy-revision rejection, and cleanup-broker journeys.
Local emulation is not live ownership transfer or Azure acceptance. The remaining bootstrap
administrator and any private-backend lock require inspection/recovery through the existing
protected workflow under separate Founder authorization; do not unlock an unverified lease.

Execution record: INST-010; WC124-R006/R017/R025/R029/R031/R032/R033/R034; deterministic
source, Docker, CLI-parser and emulator checks; no delegated models or additional provider;
existing runner images reused. Token/model billing and host-compute cost are not measured.
Exact-head PR preparation and hosted gates remain required before Founder handoff.

The full rehearsal initially passed all infrastructure/emulator stages but its lean Python
test lane failed four new shell-execution cases because that runner did not contain `jq`.
The lean runner now explicitly installs the same existing `jq` tool used by the full/private
runners. This is test-runner parity, not a new application dependency or a weakened test.

The repaired final `scripts/run_goal006_local_rehearsal.sh` passes: GitHub Actions lint,
Terraform 1.9.8 validation of all six Demo/UAT/Production roots, lease-membership plan,
pinned CLI parser check, structured handoff PATCH, positive/negative deployment and cleanup
emulation, and all 614 GOAL-006 tests. The 131-test focused suite also passes in the rebuilt
lean runner. No live provider operation was performed by this qualification.
