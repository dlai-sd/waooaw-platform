# Runner Promotion And Rollback Plan

## Current Position

As of 2026-08-20, Demo, UAT, and Production prerequisites are applied and verified. They contain
only empty resource groups, custom roles, role assignments, and the shared budget control. Expected
recurring cost remains INR 0 until a runner stack is deployed.

The executable runner stack is currently Demo-only and `INACTIVE`:

- `subscription.bicep`, `main.bicep`, `goal006_runner_bootstrap.py`, and
  `bootstrap-demo-runner.yaml` reject UAT and Production.
- The immutable bootstrap manifest covers Demo inputs only.
- Same-digest UAT/Production promotion and executable rollback are not implemented yet.
- No environment may be promoted merely because its prerequisites exist.

## Required Delivery Path

| Step | Plain-English action | Required evidence | Exit gate |
|---|---|---|---|
| 1. Finish promotion tooling | Generalize the inactive stack, validator, manifest, parameters, and workflow for environment-isolated Demo, UAT, and Production use. Add a command that restores a named prior qualified tuple without rebuilding it. | Tests proving environment isolation, immutable image digests, fail-closed authorization, no deletes in preview, and rollback selection by recorded digest | Independent review accepts tooling before cloud deployment |
| 2. Deploy Demo | With separate authorization, preview cost and changes, then deploy the inactive Demo stack from trusted `main`. | Deployment outputs, what-if, cost result, immutable manifest, stack state, and token-free run evidence | Demo stack succeeds and remains inactive |
| 3. Review and qualify Demo | Exercise bootstrap, private networking, secret lifecycle, cleanup, observability, safe shutdown, and rollback to the recorded prior tuple. Use synthetic data only. | Demo qualification record, failed-attempt evidence, rollback timing/result, smoke/CCT/security/cost results | Independent reviewer accepts Demo; unresolved failure stops promotion |
| 4. Promote identical tuple to UAT | Promote the exact Demo-qualified commit, six image digests, configuration schema, and manifest. Do not rebuild images. | Digest-equality proof and Demo acceptance reference | UAT deployment may begin only after explicit UAT authorization |
| 5. Qualify and roll back UAT | Run functional, CCT, security, data, load, resilience, recovery, observability, cost, and rollback tests with synthetic or approved masked data. | Complete UAT qualification and rollback record | Independent UAT approval; any failure returns to repair and Demo requalification |
| 6. Authorize Production | Present accepted UAT evidence, verified capacity/cost, region/DNS decisions, rollback tuple, residual risks, and operational ownership. | Founder authorization naming the exact qualified tuple and Production scope | No Production deployment without explicit Founder authorization |
| 7. Promote to Production | Deploy the exact UAT-approved tuple at minimum safe capacity, then run only approved non-destructive verification. | Digest equality, deployment record, health/CCT/Stop/cost checks, and ready rollback tuple | Founder acceptance after independent verification; no self-approval |

## Rollback Contract

Rollback is a deployment of the previously recorded qualified tuple, not a rebuild and not an
untested deletion. Before changing any environment, record:

- commit SHA and immutable manifest digest;
- all image digests and configuration/schema versions;
- deployment-stack name, outputs, and current resource inventory;
- data compatibility and recovery point;
- trigger, executor, authorization, expected recovery time, and evidence location.

Test rollback in Demo first and UAT second. The test must intentionally deploy a safe, known-bad
non-production revision, detect the failure, restore the prior qualified tuple, rerun health and
constitutional checks, and retain both failed and successful evidence. Production rollback may be
tested only through an explicitly approved non-destructive scenario. If the prior tuple is unsigned,
unavailable, incompatible, or not already qualified, stop rather than rebuild or improvise.

## Environment Rules

| Environment | Data | Promotion authority | Rollback expectation |
|---|---|---|---|
| Demo | Deterministic synthetic data only | Separate Demo deployment authorization | Full deployment and safe-shutdown rollback rehearsal |
| UAT | Synthetic or separately approved masked non-production data | Accepted Demo evidence plus explicit UAT authorization | Full same-digest rollback, recovery, and requalification |
| Production | Production data under accepted security/data controls | Explicit Founder authorization for the exact UAT-qualified tuple | Ready prior qualified tuple; only approved non-destructive rehearsal |

Prerequisite resources remain independent of runner-stack rollback. Do not remove the shared budget,
bootstrap authority, or environment prerequisite roles as part of an application-stack rollback.