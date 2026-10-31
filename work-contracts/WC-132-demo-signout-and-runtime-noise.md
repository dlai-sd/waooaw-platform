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
- Status: LOCALLY QUALIFIED - session-authorized implementation complete; exact-head PR
  evidence accompanies submission. Separately authorized Demo acceptance remains. This
  contract alone does not authorize another implementing session.
- Implementing-session authority (2026-10-30): Founder explicitly confirmed implementation
  for this session and directed: "Skip Release Qualification only; retain focused tests and
  mandatory PR checks". No provider query, deployment, UAT/Production activation or merge
  authority is inferred. Implementation branch: `ib/132/demo-signout-runtime-noise`.

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

### 2026-10-31 story-completion follow-up

The Founder authorized implementation of all WC-132 stories, impact analysis before editing,
combined execution chunks, Docker testing after implementation, and a new PR with Release
Qualification OFF. This session uses `ib/132/story-completion`, based on main `f729a552`.
It grants no cloud query, deployment, provider mutation, UAT/Production or merge authority.
The original planning commit `7386dc28` was compared with the implementation already on main;
existing conforming behavior is preserved rather than duplicated.

| Chunk | Requirements | Impact analysis and disposition |
|---|---|---|
| Sign-out | R001 | The logout reader was hard-coded to the enforced opaque cookie, but disabled/shadow mode uses NextAuth JWT cookies. Reuse `sessionTokenFromRequest`; preserve the ID token across revocation and clear only normal-logout legacy session cookies on POST, including chunks, even if GET is never followed. No login/registration handler, provider launch, account-switch target or public preference change. |
| Reset safety | R002-R003 | Recovery previously trusted a local `Succeeded` file without reading the named execution. Read the exact Demo migration execution, reject mismatched identity, and validate its completion time before resuming any consumer. Preserve existing import reuse, Demo-only quiescence, zero-replica checks, bounded waits, maintenance markers and failure holds. |
| Runtime and delivery | R004-R008 | Existing Demo pool settings, expected identity-response classification, Pydantic method protection, Temporal example-attribute suppression, pooler drain, extension installer and Node 24/retention pins remain unchanged. The bounded Demo DataProtection disposition below is retained; no error sink is weakened. |
| Handoff | R009 | New regressions live in already-collected test files. Docker catalog gates and author review supply the new PR evidence; Release Qualification is OFF by the current Founder direction. |

Docker reproduction first failed for disabled/shadow logout cookies and for five invalid
recovery-evidence cases. Final validation:

- Catalog-owned `test-web` in `--mode focused`: **714 PASS, 3 existing skips**, 109 passing
  suites; TypeScript and ESLint **PASS**. This includes login, registration, provider-command,
  account-switch and session regressions without changes to those implementation files.
- Catalog-owned `quality:scripts` in `--mode focused`: **PASS**, including script lint/format,
  resource controls and **215 tests** across its four pytest invocations.
- Mounted-source Docker Python bundle covering recovery, lifecycle, extensions, Terraform,
  realm refresh and AIR employment models: **145 PASS**.
- Docker logout route suite: **27 PASS**, **98.09% lines / 84.93% branches** (80% threshold);
  real encrypted/chunked JWT and opaque cookies, JSON and form POST, no-follow cookie clearing,
  continuation expiry/tampering, fail-closed revocation, origin and account-switch controls.
- Author review repaired a nested test declaration and unrelated formatter churn; the final
  affected web gate passed again. Mandatory commit checks also required a lint-safe test
  environment restore and a Founder-approved patch of the existing development-only
  `follow-redirects` override from 1.16.1 to 1.16.2. The lockfile changes only that resolution;
  Docker `dep-scan:typescript` passed with no high/critical advisories (19 existing low/moderate
  advisories remain), and the full web gate passed again against the updated lockfile.
  No new dependencies or changes to login/registration,
  identity projection, provider configuration, database reset policy or UAT/Production.

These are local Docker results, not real-provider or deployed acceptance. Manual Demo sign-out,
failure recovery and the one-hour R004/R006 log observations remain separately authorized
acceptance work. The exact final commit and mandatory PR prechecks are recorded in the new PR.

### Implementation dispositions

| Requirements | Implemented behavior and evidence |
|---|---|
| R001 | The revocation boundary returns the already-loaded ID token to its server caller. A nonce-bound, encrypted, HttpOnly continuation preserves it for at most 60 seconds, scoped to `/api/auth/keycloak-logout`, Secure on HTTPS, SameSite=Lax. GET never reopens the revoked session, rejects missing/expired/tampered hints, and deletes the continuation cookies. The browser JSON contains only the opaque local path. Form POST also fails closed on unconfirmed revocation. Completed normal logout stays on `/login`, rather than the previous homepage redirect. |
| R002 | Before resetting an existing Demo, validate the existing Keycloak migration job and its Key Vault credential binding. An `always()` failure/cancellation hook runs after any attempted provisioner execution, including a failed console-evidence capture. It reuses a completed realm import or awaits an already-running import, otherwise starts the existing import job; it then resumes PgBouncer/Keycloak and verifies replica refresh. It does not activate the failed application release. Recovery is bounded to 900 seconds and reports `DEMO_KEYCLOAK_REALM_RECOVERY_FAILED` on failure, retaining partial JSON evidence. |
| R003 | Quiesce existing Demo application consumers, Temporal, Keycloak and finally PgBouncer before resetting any database. Verify zero replicas across all revisions, retain revision/configuration identity, and emit named maintenance start/end markers. The existing successful-deployment readiness gates resume applications; failure retains a named recovery hold, not an apparently healthy empty application. No database reset or UAT/Production lifecycle policy is removed or changed. |
| R004 | Demo `PGBOUNCER_CLIENT_IDLE_TIMEOUT=0` disables the incompatible 60-second client cutoff. The pinned Keycloak 25.0.6 maintains a minimum Agroal connection, so idle eviction cannot reliably precede that cutoff. Bounded application pools now own client lifetime; PgBouncer still caps Demo clients at 40 and reclaims unlinked backends after 30 seconds. Non-Demo timeout values remain unchanged. No unsupported newer Keycloak/PgBouncer setting is introduced. |
| R005 | Classify expected 401, typed/untyped 403 and typed registration-required 409 before failure logging. Unexpected conflicts, server failures and transport exceptions still receive failure correlation IDs. |
| R006 | See the explicit startup-noise dispositions below. |
| R007 | Both hosted jobs install the Dockerfile-pinned extensions, with the existing installer's bounded retries, before Azure login/first query. Tests also retain the private-runner ordering assertion. |
| R008 | Checkout v5, upload-artifact v6, download-artifact v7 and Azure login v3 are pinned to resolved commit objects whose action metadata declares Node 24. Artifact retention is at most 90 days. |
| R009 | New recovery tests are included in CI, the release test list, and the validation catalog's scripts gate. Release Qualification is OFF by the explicit session authority above; focused validation, author review and mandatory C-059/C-065 preparation remain required. |

### Startup-noise dispositions (R006)

- **AIR:** `EmploymentModel` protects the real `model_validate` and `model_dump` method
  namespaces, rather than every `model_` field. A newly built AIR image using the pinned
  Pydantic **2.9.2** successfully ran
  `python -W error::UserWarning -c 'import pydantic; import employment_patch; print(pydantic.__version__)'`.
  Wire fields and aliases are unchanged.
- **Temporal:** both the qualification container and runtime disable auto-setup's
  `Custom*Field` test-attribute creation with `SKIP_ADD_CUSTOM_SEARCH_ATTRIBUTES=true`.
  Those seven example attributes have no application consumers; namespace creation,
  schema setup and application search attributes are not suppressed.
- **Business Platform DataProtection:** retained and explicitly justified for disposable,
  single-replica **Demo**, not claimed fixed or suppressed. Its consumer is the 15-minute
  workspace focus reference (`CustomerEngagementWorkspaceService`); losing the ephemeral key
  rejects an old reference and requires a fresh workspace projection. The Web's durable session
  authority is not these keys. Existing `DataProtection:KeysPath` persistence requires a
  certificate and password and fails closed if incomplete. No new Azure storage/key service,
  secret, plaintext key persistence or UAT/Production exception is introduced by this contract.
  Cross-replica/restart focus continuity is not promised; Founder review must retain or reject
  this bounded Demo disposition.
- **PgBouncer:** reproduced the exact message using the pinned **1.22.1** image and disposable
  PostgreSQL: after a transaction returned its backend to the idle pool,
  `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename='postgres' AND pid <> pg_backend_pid();`
  produced **one** `got packet 'E' from server when not linked` message. Stopping PgBouncer
  first left **zero** backend sessions to be forcibly killed. Demo reset's existing
  `DROP DATABASE ... WITH (FORCE)` has that same out-of-band termination mechanism.
  R003 now closes PgBouncer last, before reset, rather than leaving its unlinked backends
  connected. No PgBouncer error logging is disabled. Other occurrences outside a reset
  remain real failures requiring investigation, not an accepted blanket suppression.

### Local validation

- Focused web route, identity, login, sign-out command and provider-command tests: **59 PASS**.
- Focused lifecycle, realm refresh, extension, recovery and AIR tests: **73 PASS**.
- Complete AIR/trust-layer suite: **222 PASS**, AIR coverage **93.36%** (90% minimum).
- `pnpm exec tsc --noEmit --incremental false`: **PASS**.
- `ruff check` on the changed scripts/AIR model: **PASS**.
- Pinned `actionlint:1.7.7` on deployment/CI workflows: **PASS**.
- Pinned Terraform 1.9.8 formatting check: **PASS**. The first isolated module validation
  omitted template/relative-file inputs and was rejected; the repository rehearsal validates
  complete environment roots instead.
- AIR Docker build/import against pinned Pydantic 2.9.2: **PASS**, warnings treated as errors.
- Disposable PostgreSQL/PgBouncer forced-disconnect reproduction: **PASS** (1 exact baseline
  message; 0 remaining backends after quiescence); all temporary containers/network removed.
- `bash scripts/run_goal006_local_rehearsal.sh`: actionlint, all six Terraform roots, pinned
  CLI parser and Docker Azure-emulated positive/negative deployment/resume/cleanup phases
  **PASS**. The final pipeline phase initially had **767 PASS / 1 FAIL** because its existing
  ordering test hard-coded the replaced Azure login v2 pin. That coupled assertion now checks
  authorization ordering independently; the new WC-132 test verifies exact Node 24 pins.
  The affected pipeline phase is rerun separately, without repeating the costly emulation.
- Final `docker compose --profile test-python run --rm test-runner-python pytest tests/pipeline/test_goal006_*.py tests/pipeline/test_wc132_demo_reset_recovery.py -q`:
  **785 PASS** after updating both the action-pin and recovery-guard-count assertions.

Author review repaired strict continuation expiry, form revocation failure handling,
interrupted import-evidence parsing, concurrent-import reuse, and pool-drain/recovery
ordering. No unresolved local implementation defect remains from that review. This is
self-verification, not independent assurance or deployed acceptance.

### Deployment acceptance still required

No Azure read, deployment or provider-backed acceptance was performed in this implementing
session. The next separately authorized Demo deployment must verify the real-account sign-out,
maintenance markers/recovery, workflow annotations, and one-hour R004/R006 log counts. Synthetic
counts and local tests are not reported as Azure before/after counts. The 30-minute Apply
optimization remains explicitly excluded.

## Rollout

Merge, run Environment Deployment for Demo with `apply`, then: sign in and sign out (no
confirmation page), and run the Log Analytics queries from R004 and R006 for the hour after
deploy.
