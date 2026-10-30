# Work Contract 132 - Clean Sign-Out, Deploy-Window Safety And Azure Runtime Noise

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-30, current conversation.
- Authority: After Environment Deployment run 41050299768 (main 1613534, Demo, green) the
  Founder signed in with Google, signed out, and was shown Keycloak's "Do you want to log
  out?" page. The Founder directed: "prepare work contract for these items including signout
  and all 5 points in azure logs, traces and first 2 points on deployment(only if you have
  high confidence). Push this Work contract on new branch ... I will get these implemented in
  new session."
- Baseline: origin/main at 1613534 (WC-131 merged).
- Status: PLANNED - implementation in a later Founder-authorized session. This contract does
  not itself authorize writing implementation code; the implementing session must obtain
  explicit Founder authorization first.

## Evidence Summary

| # | Observation (Demo, 2026-10-30, UTC) | Source |
|---|---|---|
| E1 | Sign-out redirect to Keycloak carried only `client_id`, `post_logout_redirect_uri` and `state`; no `id_token_hint`, so Keycloak asked for confirmation. | Founder screenshot; `web/app/api/auth/keycloak-logout/route.ts` |
| E2 | `logoutPost` revokes the web session (`revokeOwnedSession` -> `web_session.revoke_family`) before the browser follows the GET path; `keycloakLogoutUrl` then reads the already-revoked session, finds no `idToken`, and omits the hint. The non-JSON path builds the URL before revoking and is unaffected. | `web/app/api/auth/keycloak-logout/route.ts` (`keycloakLogoutUrl`, `logoutPost`, `logoutGet`) |
| E3 | Keycloak logged `relation "realm" does not exist` (42P01) 51 times 11:00-12:00. Failed run 41042104645 reset the Keycloak database at about 10:48 and stopped before realm import; Demo sign-in was down until this run's import and Keycloak refresh at about 12:11. | Log Analytics `ContainerAppConsoleLogs_CL`, ca-demo-keycloak |
| E4 | 11:54-11:55: web `web.health.ready.request_failed` (old revision 0000094) and Business Platform `identity-schema` Unhealthy ("Required identity schema or forced RLS is absent"): the previous application revision kept serving while the Demo database reset ran. | Log Analytics, ca-demo-web and ca-demo-bp |
| E5 | PgBouncer `client_idle_timeout` closed idle Keycloak pool connections (18 FATALs); Keycloak/agroal logged "Closing connection in incorrect state" 97 times (still at 13:17) and ClearExpiredEvents scheduled tasks failed (47). PgBouncer `client_idle_timeout=60`; Keycloak keeps a minimum pool that idles longer. | `infrastructure/postgres/pgbouncer/pgbouncer.ini`; `infrastructure/terraform/phase2/modules/workload/main.tf` (Keycloak `KC_DB_POOL_*` env) |
| E6 | Web logged `web.identity.session_load_failed` with status 409 five times (13:11-13:12). These are the expected `REGISTRATION_REQUIRED` outcome after the Demo reset, logged as failures before the status is classified. | `web/lib/api/identity.ts` |
| E7 | Remaining noise: ai-runtime pydantic `protected_namespaces` warnings for `model_` fields (20); Temporal "search attribute ... already exists" on startup; Business Platform DataProtection `XmlKeyManager[35]` (keys not persisted/protected) at startup; PgBouncer "got packet 'E' from server when not linked" for `web_session_app` and `bp_runtime`. | Log Analytics, ca-demo-ai-runtime, ca-demo-temporal, ca-demo-bp, ca-demo-pgbouncer |
| E8 | Hosted jobs `start-broker` and `cleanup-private` (`runs-on: ubuntu-latest`) still install the `log-analytics` extension on demand (about 10 s each), the same failure mode WC-131 removed from the private runner job. | Run 41050299768 jobs 124044552050 and 124058080783; `.github/workflows/environment-deployment.yaml` |
| E9 | Workflow warnings: Node.js 20 action deprecation (checkout, upload/download-artifact, azure/login) and "Retention days cannot be greater than the maximum allowed retention ... using 90". | Run 41050299768 annotations |

## Authority And Scope

In scope: the requirements below, in the web app, Business Platform, ai-runtime, PgBouncer/
Keycloak configuration, the Environment Deployment workflow and its tests.

Not in scope: shortening the 30-minute Apply (no high-confidence change identified),
rebuilding or re-pinning the private runner image, removing the per-deploy Demo database
reset, UAT/Prod deployments, merges. Constitutional documents are not modified.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| WC132-R001 | Sign-out from the UI returns the user to `/login` without the Keycloak confirmation page: the Keycloak end-session URL includes `id_token_hint` for the session being signed out, captured before the session is revoked (for example a short-lived `httpOnly`, `Secure`, `SameSite=Lax` continuation cookie scoped to `/api/auth/keycloak-logout`, or a URL returned by the POST). The id token is never logged or exposed to client JavaScript, the continuation is single-use and cleared, and the session is still revoked server-side even if the browser never follows the redirect. | Web unit tests for POST-then-GET carrying the hint, missing/expired continuation falling back safely, and cookie attributes; Playwright or route test; Demo sign-out shows no confirmation page. |
| WC132-R002 | A Demo deploy that resets databases cannot leave Keycloak without its realm: if a run stops after the reset and before realm import, the next run (or the same run's failure path) re-imports the realm and refreshes Keycloak, and the workflow reports the state with a named error. | Pipeline tests on the workflow contract; reasoned trace of the 41042104645 failure path. |
| WC132-R003 | During the Demo database reset, the previous application revision does not serve as if healthy: web and Business Platform readiness report a named maintenance/reset state (or are quiesced, as Temporal already is), and the window is bounded and logged with start/end markers. | Pipeline tests; Demo deploy logs show the markers and no `identity-schema` Unhealthy noise outside the window. |
| WC132-R004 | Keycloak's database pool drops idle connections before PgBouncer does (or PgBouncer's limit for the Keycloak database is aligned), so the agroal "incorrect state", PgBouncer `client_idle_timeout` FATALs for Keycloak, and failed ClearExpiredEvents tasks stop. The chosen values are recorded with their rationale. | Terraform/config tests asserting the relationship between the two timeouts; Demo Log Analytics query over 1 hour after deploy shows zero such entries. |
| WC132-R005 | Expected identity outcomes (401, 403, 409 `REGISTRATION_REQUIRED`) are not logged as `session_load_failed`; real failures are still logged through `logServerFailure` with a correlation ID. | Web unit tests for each status. |
| WC132-R006 | Startup noise is removed or explicitly justified: pydantic `protected_namespaces` warnings fixed in ai-runtime models; Temporal "search attribute already exists" made idempotent or downgraded; Business Platform DataProtection keys persisted and protected in Azure (or the warning documented as accepted with reason); PgBouncer "packet 'E' when not linked" root-caused and fixed or documented. | Unit tests where code changes; Demo Log Analytics query showing the counts before and after. |
| WC132-R007 | Hosted `start-broker` and `cleanup-private` jobs install the pinned `log-analytics` extension through `scripts/goal006_az_extensions.sh` (with retries) before first use, instead of on-demand install. | `tests/pipeline/test_goal006_az_extensions.py` extended. |
| WC132-R008 | Workflow warnings removed: actions moved to Node 24-compatible pinned versions, and artifact `retention-days` set to at most 90. | Workflow contract test; actionlint; the next deploy run shows no such annotations. |
| WC132-R009 | Validate, perform author review, and submit an exact-head PR using the repository PR template (Release Qualification as the Founder directs). | Commands and results in the PR. |

New tests must be wired into the explicit CI and release-qualification test lists
(`.github/workflows/ci.yaml`, `scripts/run_release_qualification.sh`,
`validation/engineering-validation.yaml`) where applicable.

## Suggested Order

R001 (user-visible), R005, R007, R008 (small, low risk), R004, R006, then R002 and R003
(deploy-path changes needing the most care). Split into more than one PR if the Founder prefers.

## Stops And Rollback

Stop and ask the Founder if R002/R003 would require removing the Demo reset, changing UAT/Prod
behavior, or changing Keycloak realm configuration. Rollback: revert the PR(s); each
requirement is independently revertible.

## Validation And Delivery Evidence

To be completed by the implementing session.

## Rollout

Merge, run Environment Deployment for Demo with `apply`, then: sign in and sign out (no
confirmation page), and run the Log Analytics queries from R004 and R006 for the hour after
deploy.
