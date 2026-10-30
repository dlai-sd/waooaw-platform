# Work Contract 129 - Refresh Keycloak Replicas After Demo Realm Import

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-30, current conversation.
- Authority: Environment Deployment run 41014026210 (main 40b53c1) failed at
  verification. The Founder authorized an immediate Keycloak revision restart from the
  Azure CLI, a durable PR, and keeping the per-deploy Demo database reset unchanged.
- Baseline: origin/main at 40b53c1 (WC-128 merged).
- Status: LOCALLY QUALIFIED, DEMO SIGN-IN RESTORED LIVE - Founder review/merge pending.

## Root Cause

Every Demo apply runs the WC-124 provisioner with `--reset-demo-databases`, which
drops and recreates `waooaw_keycloak` (06:34-06:37 UTC). The Keycloak migration job
then re-imports the realm (06:43:16-06:44:36). The running Keycloak replica had
started at 01:58, kept cached realm and client models with the old IDs, logged
`relation "realm" does not exist` at 06:43:41, and from then on answered
"Client not found" for `waooaw-web` while the revision reported Healthy. The Google
verifier printed only `ValueError`, hiding "Broker returned HTTP 400".

## Authority And Scope

In scope: a deployment gate that restarts the latest ready Keycloak revision when any
replica predates the realm import and waits for fresh ready replicas, and a Google
verifier message that names the fixed failure reason.

Not in scope: changing the Demo database reset policy (Founder decision: keep),
Keycloak image or realm content, verification job sequencing, and Apply duration.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| WC129-R001 | After dependency readiness and before application activation, the apply job restarts the latest ready Keycloak revision when any replica was created at or before the successful realm import end time, then waits (bounded) until every replica is newer and ready; it fails closed on a failed import, timeout or cross-environment scope. | `tests/pipeline/test_goal006_keycloak_realm_refresh.py`, actionlint. |
| WC129-R002 | The Google deployment verifier prints the fixed `ValueError` reason and still hides details of unexpected exceptions. | `tests/pipeline/test_goal006_keycloak_realm_refresh.py`, `tests/pipeline/test_wc085_google_deployment.py`. |
| WC129-R003 | Demo sign-in is restored live and both provider verifiers pass. | Live evidence below. |
| WC129-R004 | Validate locally, perform author review, and submit an exact-head PR using the repository template and preparation gate. | Commands and results below and in the PR. |

## Stops And Rollback

Stop for missing Founder decisions, unavailable validation or secret requirements.
Rollback: revert this PR; the restart is idempotent and only targets the same-environment
Keycloak app.

## Validation And Delivery Evidence

- New and Google verifier pipeline tests: 21 passed.
- Full `tests/pipeline`: 20 failed / 2071 passed; the same 20 failures reproduce on
  origin/main without this change (pre-existing, unrelated).
- Ruff check and format on changed Python: PASS. actionlint 1.7.7: PASS.
- Live: `az containerapp revision restart` of `ca-demo-keycloak--0000026` at 07:44:16 UTC;
  the authorization endpoint for `waooaw-web` changed from HTTP 400 to 302 at 07:44:57;
  `verify_google_deployment.py` and `verify_facebook_deployment.py` against
  `https://auth.demo.waooaw.com/realms/waooaw` both passed.

## Rollout

Merge, then the next Demo deployment refreshes Keycloak after the realm import and the
verification job exercises sign-in end to end.
