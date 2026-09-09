# WC-085 Partial Candidate Evidence

This is a PARTIAL implementation bundle, not the complete WC-085 final release bundle.
Historical application/configuration freeze: `14a28c18aa8774d8b2f956c475e2e60a245f4ddd`.
The Google-first working-tree continuation below changes this configuration; the historical build,
scan, and deployment-related checks must not be attributed to the new candidate.
Subsequent changes add evidence and repair the mandatory lifecycle gate's PostgreSQL readiness probe.
Base: `79ec8065ad448cb418551034366091693b7b316c`. Office: INST-010.
The final draft PR records the pushed HEAD; these local results do not contain a candidate Demo
revision or immutable exact-six deployment tuple. No full story PASS or provider acceptance is claimed.

## Checks

All executable application/test/build/scanner work ran in Docker. No virtual environment was created.

### H1 Full-Schema Compatibility - 2026-09-09

Status: PASS for package H1 local engineering scope; SP-03, SP-06, SP-19 and SP-20 retain their
separate provider, channel and deployed-acceptance gates.

| Docker check | Result |
|---|---|
| Exact `pgvector/pgvector:pg16` entrypoint initialization with `infrastructure/postgres/init` mounted at `/docker-entrypoint-initdb.d` | PASS through migrations `01`-`29`; migration 29 installs accounts, login methods, actor bindings, memberships and `resolve_customer_membership()` |
| `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj -p:RestoreForce=true -p:IsTestProject=true --filter 'FullyQualifiedName~Waooaw.BusinessPlatform.Tests.Identity'` | 215 PASS, 0 failed, 0 skipped; includes the exact full-chain test plus retained legacy row, two-customer isolation, retry/concurrency, commit failure rollback, inactive/legacy denial, restricted BP/CE/PR/WBE roles and pooled-context isolation |

H1 repaired deterministic fresh-install defects in the existing migration chain: shared enum and
pgvector schema visibility, an immutable UTC eligibility expression, stale duplicated campaign and
trading declarations, an invalid pre-owner-table alteration, missing `ai_runtime_app` creation,
stale WhatsApp grants, a historical RLS conflict fragment, retired index targets, partitioned keys,
time-dependent index predicates, numeric aggregate typing, alphanumeric skill IDs, append-only seed
upserts, canonical customer foreign keys and additive payment-coupon compatibility. No provider,
cloud, deployment, Production or customer-data action occurred. Raw focused output is retained at
`/tmp/wc085-h1.log`; the final passing commands are represented by their counts above.

### H2 Stock Reader And Demo Configuration - 2026-09-09

Status: PASS for package H2 local engineering scope. SP-03 and SP-06 remain incomplete because no
real Google identity, deployed Demo revision, actual secret reference, provider activation, customer
journey, projection agreement or runtime outage/telemetry proof was authorized or exercised.

| Docker check | Result |
|---|---|
| `bash scripts/run_wc085_google_reconstruction.sh test-results/wc085/h2-reconstruction-local` | PASS in two fresh generations using pinned Keycloak 25.0.6; Terraform-rendered realm import, private TLS, dedicated confidential reader, exact user and Google binding GETs, 60-second token with no refresh token, and four HTTP 403 write denials |
| Live `GoogleWorkspaceProofAdapter` against each stock fixture generation | 1/1 PASS twice; validated private HTTPS certificate/host, exact actor subject, opaque case-sensitive Google provider subject and configured trust namespace |
| Docker `.NET` filter `GoogleWorkspaceProofAdapterTests|CustomerIdentityProgramHostTests` | 40 PASS, 0 failed, 0 skipped |
| Docker pytest `test_goal006_terraform_foundations.py test_wc085_google_deployment.py test_identity_artifacts.py` | 69 PASS |
| H2 author review, editor diagnostics and `git diff --check` | PASS; no real credential value or generated artifact selected for commit |

H2 adds the dedicated `waooaw-bp-identity-reader` with service-account/client-credentials only,
`fullScopeAllowed=false`, exact effective `realm-management.view-users`, maximum 60-second token,
no interactive/direct/offline grants, and a distinct `bp-identity-reader-client-secret` Key Vault
reference accessible only to BP. The customer web client receives the stock signed
`identity_provider` to `idp` session mapper. BP binds the reviewed public issuer and exact private
HTTPS Keycloak origin/host, stable Demo Google namespace and deterministic trust digest. The public
manifest remains Google-disabled. Raw synthetic generation JSON/XML is retained locally under
`test-results/wc085/h2-reconstruction-local/` and intentionally excluded from Git.

### H3 Membership Adoption And Usable Portal Read - 2026-09-09

Status: PASS for the single locally enabled BP operation. This does not enable consequential
relationship commands or imply CE, PR, WBE or AI receiver adoption. SP-10 remains PARTIAL pending
the exact deployed Demo portal/browser journey.

| Docker check | Result |
|---|---|
| Focused `Program_TwoMembershipResolvedActors_ListOnlyOwnRelationships` | 1 PASS against real PostgreSQL with restricted `business_app`; two separately completed tenantless actors resolved current membership, received only their own participant-bound relationship through actual HTTP and RLS, rejected a forged tenant header, and left pooled tenant/identity GUCs empty |
| `EmploymentRelationshipsControllerTests` | 12 PASS, 0 failed/skipped; membership-derived account overrides forged participant claim and only the collection method carries customer-membership route metadata |
| `CustomerIdentityProgramHostTests` | 12 PASS, 0 failed/skipped; retained signup/session, invalid bearer/header, missing readiness and unsupported-route denials plus the new collection proof |
| H3 author review, editor diagnostics and `git diff --check` | PASS; no consequential route or additional service operation enabled |

H3 places the resolver-derived tenant into the existing request-local RLS context and uses the
resolver-derived account as the initial OWNER workspace participant for the accepted collection
read. Caller tenant/account headers can only match resolved values; JWT participant/tenant claims
cannot override them. Middleware removes membership and tenant context in `finally`. Every other
relationship method still lacks `CustomerIdentityRoute` and is denied for customer tokens before
controller execution. Unadopted downstream service, job, callback and streaming paths remain
disabled and are not represented as tested or passing.

### H4 Returning Identity And Browser Cleanup - 2026-09-09

Status: PARTIAL; the bounded local returning-identity and cross-tab cleanup checks PASS. SP-03,
SP-16, SP-17 and SP-20 retain their accepted-contract, real-provider, deployed-browser and
full-degradation gates, so H4 is not complete acceptance.

| Docker check | Result |
|---|---|
| Focused PostgreSQL continuity filters | 7 PASS, 0 failed/skipped in 23 seconds; same subject keeps the original account/tenant/profile through same/different key, registration and expiry; a different actor sharing the stable Google key has one winner and one unresolved recovery; inactive/retired cohorts cannot resolve, replay or remint |
| Registration route/flow and sign-out Jest slice | 3 suites, 58 PASS, 0 failed, no console warnings/errors; covers confirmed returning session, expired/mismatched session denial, bounded cancellation, same-key retry, switch/unmount cancellation, protected-state cleanup and late cross-tab sign-out denial |
| Docker TypeScript and editor diagnostics | PASS with no diagnostics in the four changed web files |

Sign-out and account switch first remove WAOOAW-prefixed session/local storage, then publish a
privacy-safe cross-tab change containing only an action and random nonce. A registration tab aborts
its pending request, clears its local draft/state and returns to the public origin before any late
reply can navigate to `/home`. Unrelated browser storage is preserved. The database remains the
identity authority: email is not used to match or relink an actor. Recreated-actor recovery remains
blocked because retirement/rebinding and old-session denial rules are not formally accepted; H4 adds
no silent reset, persistent Keycloak storage or recovery mutation. No real Google or deployed browser
journey was performed.

| Command / Scope | Result |
|---|---|
| `pnpm test -- --runInBand --json --outputFile=/evidence/jest.json` | 41 suites, 229 tests PASS; `jest.json` |
| Auth Jest coverage, collecting AuthBoundary/AuthDialog/AuthJourney/safe-return | 10 suites, 44 tests PASS; 98.5% lines, 94% branches; each changed file exceeds 90% lines |
| `pnpm exec tsc --noEmit` and `pnpm lint` | PASS |
| Focused Playwright command in `browser-matrix.md` | 30/30 PASS, Chromium/Firefox/WebKit across five configured projects |
| `pytest tests/pipeline/test_wc085_google_deployment.py tests/pipeline/test_goal006_*.py tests/identity-foundation/test_identity_artifacts.py -q` | 513 PASS; final registered-origin assertion subsequently passed in the 8-test focused rerun |
| Ruff on new verifier/tests and changed Azure fixture; Bash syntax on three changed/new verification scripts | PASS |
| Terraform 1.9.8 Demo workload `init -backend=false`, `validate`, module `fmt -check` | PASS; no cloud state/provider plan/apply |
| `bash scripts/run_goal006_local_azure_verification.sh` | PASS; synthetic TLS Google redirect plus revision-bound evidence and unhealthy revision failure |
| `bash scripts/run_wc085_google_reconstruction.sh` | PASS twice; actual Terraform-rendered realm, pinned Keycloak, synthetic credentials, TLS Google redirect, new user's customer role and absence of founder role |
| `docker build -f web/Dockerfile -t wc085-web:14a28c18 .` | PASS; `web-build.log` |
| Syft v1.27.1 CycloneDX SBOM | Generated, `sbom.json` |
| Trivy 0.73.0 image scan, `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1` | PASS, zero matching vulnerabilities; `trivy.json`; not a claim of zero vulnerabilities of every severity |
| Gitleaks v8.28.0, redacted, candidate commit range | PASS, zero leaks; `gitleaks-diff.json` |
| actionlint 1.7.7 on changed deployment-verification workflow | PASS |
| Author diff and editor diagnostics | Checked scope, secret handling, default-role isolation, callback guard, rollback and no private browser endpoint; no diagnostics in checked changed files |
| Mandatory real-container lifecycle gate | Initial local-socket probes exhausted during PostgreSQL initialization; repaired to probe the TCP endpoint from the Docker network. Same pinned images and 503/200/503/200 assertions then PASS. Final pushed-HEAD result is bound in the prepared PR body. |

Web candidate image ID: `sha256:a9dc8fbc4d2575c29c9dbc21635d7b76d8e34635bee93905a10e96727635940d`.

## Test Images

| Image | Local Immutable Identity |
|---|---|
| pr408-test-runner-ts:latest | sha256:c59b212476b4da92ffd9dd502235afa4dc5a733d32ad1e03402bfb80cf426f3c |
| pr408-test-runner-python:latest | sha256:5a833b51dcbb5da88ac473b849ec32656cce0611d731fca361ab7abfe82f3866 |
| mcr.microsoft.com/playwright:v1.62.1-noble | sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e |
| hashicorp/terraform:1.9.8 | sha256:18f9986038bbaf02cf49db9c09261c778161c51dcc7fb7e355ae8938459428cd |
| Keycloak reconstruction | quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2 |

## Authority And Limits

- The Founder authorized WC-085 implementation and the additional Demo Google reconstruction work. Canonical deployment remains after review/merge; no cloud deployment was performed here.
- The reconstruction script is a test harness using stock Keycloak import, not a custom production importer. It creates no persistent database. Synthetic TLS material is temporary and removed on exit.
- Key Vault values never enter Terraform, source, images or evidence. A separate managed identity receives access to exactly the two Google secrets. Normal deployments retain the registered issuer/callback; a foundation-domain change fails the precondition and needs renewed callback approval.
- Historical Google runtime enablement was desired configuration, not accepted readiness. The Google-first continuation removes its redirect-only readiness override; the broker can be reconstructed while the public provider projection remains disabled. Private API/UI checks and complete provider journeys remain activation gates under SP-03/SP-06.
- Startup import assumes an empty disposable realm. It does not update an existing persistent realm. Persistence and a custom importer were explicitly excluded.
- Provider credential rotation resolves versionless references on fresh deployment; in-place retained pods may require restart. No promise of uninterrupted identity continuity is made for disposable Demo users.
- Rollback: revert auth slice independently; disable/revert Google desired configuration and provider projection together through the reviewed deployment path. Reverting the whole candidate restores the prior empty generated provider list. No real rollback test was performed.
- Known pre-existing output: Next.js CSS autoprefixer warning at the unrelated `align-items:end` rule and jsdom navigation console warnings in AcquisitionController tests. Both commands completed successfully.
- Missing acceptance includes S1 formal owner approvals; real Google/Facebook/email journeys; exact candidate Demo binding; complete zoom/loading/error/portal/browser matrices; public Chrome reproduction; Founder visual acceptance. See all 26 rows in `story-gates.md`.
- The canonical C-059/C-065 PR preparer must pass after final push. Its real-container lifecycle evidence is attached to the PR body separately and does not imply WC-085 completion.

## Google-First Working-Tree Continuation - 2026-09-09

Status: LOCAL IMPLEMENTATION MILESTONE ONLY; changes are not yet committed, pushed, built as a new
release, or deployed. Base HEAD is `bff1bc7cd68252534071ec847be221b021cfdf5f`. Prior evidence remains
historical; no full WC-085 story is promoted to PASS.

- Founder renewed implementation authority, authorized the consolidated owner-decision packet,
	and deferred Facebook/email until Google is proven. WC-085 Sections 16-17 record this decision
	and the outstanding Goal, Billing, and Identity acceptances. No reviewer was invoked.
- Added the exact NextAuth `keycloak-google` callback to the Google-enabled realm and redirect
	verifier; previous tests exercised only the generic callback and missed this login blocker.
- Demo BP options now derive from the reviewed manifest, with exact approved ACA origins, actual
	web client ID, disabled unready providers, cleared inherited readiness references, and matching
	eight-hour Keycloak session lifetime. Unapproved/lookalike/cross-environment cloud hosts are denied.
- The reconstructed Google broker is not customer-ready availability. General projection remains
	disabled until provider acceptance; controlled qualification requires an approved test-only path.

| Focused validation | Result |
|---|---|
| Docker pytest: `test_goal006_terraform_foundations.py`, `test_wc085_google_deployment.py`, `test_identity_artifacts.py` | 68 PASS |
| Docker .NET: `FullyQualifiedName~F2_IdentityEnvironment` | 13 PASS, explicit test count; includes local-default-to-Demo configuration binding and unavailable provider projection |
| Docker .NET: `FullyQualifiedName~Waooaw.BusinessPlatform.Tests.Identity` | 122 PASS, zero skipped; includes completion failure/retry tests and one real PostgreSQL rollback test |
| Docker reconstruction harness, two fresh pinned Keycloak instances | Both PASS; exact Google callback, PKCE redirect, manifest/runtime map, default customer role, no founder role, eight-hour session |
| Terraform module `fmt -check`, editor diagnostics, `git diff --check` | PASS at the checked local milestone |
| Broad pipeline/identity exploratory run | 1,275 PASS, 36 FAIL, 1 SKIP; NOT a passing gate. Includes read-only fixture failures and unrelated runner/property checks. One affected identity-edge count assertion was repaired and passed in the focused 68-test rerun. Remaining failures have not been fully classified. |

Fresh reconstruction JSON/XML is retained outside Git in
`/workspaces/waooaw-operations/wc085-google-first-reconstruction`; synthetic credentials only.
These records are local reconstruction proof, not release-bound artifacts or Google account proof.

Registration completion now saves its account state and idempotent response in one EF save instead
of two. An injected save failure leaves the registration incomplete; a PostgreSQL 16 constraint
failure against migration 20 also rolls back completion. The relational test uses a restricted
non-owner, non-superuser, non-RLS-bypass application role and verifies successful retry/replay after
the test-only fault is removed. This is local transaction evidence, not concurrent tenant provisioning,
cross-tenant RLS, Keycloak publication, or deployed application-role proof. No new production schema
or permissions were introduced by this repair.

The Founder selected independent customer tenant provisioning before real Google qualification;
authentication-only proof in the shared synthetic tenant is not the accepted next milestone. All Demo
users currently receive one synthetic tenant ID. BP completion stores an account UUID but does not
mint a tenant/membership or publish it to Keycloak; the browser does not obtain a renewed tenant-bearing
session. On 2026-09-09 the Founder authorized D-TENANT's platform-wide isolation scope and a lightweight
constitutional-enforcement documentation pass. WC-085 Sections 17.1-17.2 record that authority, existing
ADR/claim traceability, and downstream evidence requirements including WBE billing. Subsequent
Founder-authorized Solution/Data/Security boundary repair calls authored the exact contracts, and EA
resolved the interpretation of the tested permission conflict. Security's local pinned-Keycloak tests
showed that both tested publisher grants also permit credential/broker mutation; no write grant was
approved. The read-only, profile and renewal probe results and their limitations are recorded in
`architecture/reference/security/wc085-identity-publication-security-contract.md`. They do not prove
real Google, deployment, or tenant isolation. CB-009 now records the single Founder scope decision
required by `architecture/reference/product/wc085-identity-architecture-decision.md`, not missing
implementation authorization or office assignment. No arbitrary mapper, browser tenant, lookup
bypass, migration, broad runtime credential, or source-code change was added by the authoring calls.
No cloud operation or secret retrieval was performed.

The Founder conditionally authorized Google-only Demo deployment/qualification after engineering
PR review/merge and existing gates, using existing Key Vault references with no DNS/UAT/Production
changes. This does not waive D-TENANT, account consent, release checks, or any other prerequisite.

Remaining delivery gates include candidate build/security/author review, pushed-HEAD pre-PR checks,
Founder merge, satisfaction of conditional Demo deployment/test authority, approved account interaction, provider
failure/rollback/sign-out proof, and all other open WC-085 story gates.

## Automatic Signup Connection - Latest Local Milestone, 2026-09-09

Founder approval now covers the bounded architecture change for unattended signup with credential
separation. ADR-008 Amendment 2 selects the narrow Keycloak extension; this supersedes the earlier
stock-only/Founder-choice blocker, not deployment or spending limits. Current work is uncommitted.

Added `src/identity-publication-provider` and `scripts/wc085_identity_publication_probe.mjs`.
The provider exposes only configured broker-proof reads and immutable initial tenant-attribute
publication, using a dedicated client with no Admin API roles. Parent review repaired customer-role
eligibility and rejection of tokens without issue timestamps; Maven input is explicitly unignored.

- Parent Docker image build passed, including three Java tests on each of two clean Maven builds
	and identical JAR bytes: SHA-256 `a3fd5775c1161e1e9a30c8d41a0e8ae2861ccd50afb6e217dfe1edfdcb6d5faf`.
	Builder is Maven 3.9.9/Temurin 21.0.7; runtime remains the pinned Keycloak 25.0.6 base.
- Latest parent real-server probe verified publication/read-back with the customer role and denial
	of password reset, native admin operations, invalid token claims, non-customer/institutional
	targets, and seeded/conflicting publication. These are synthetic local checks, not real Google.
- **Full parent probe FAILED:** after intentional client disable/re-enable, the protected-record
	configuration check received `401` instead of expected `503`. The token was rejected before that
	configuration check; the expected check and later concurrency cases were not reached. Three local
	test repair iterations were attempted; further test-file repair is paused pending user direction.
- Earlier delegate artifacts report two-server concurrency/cache, lock-timeout and rollback checks,
	but predate parent source/fixture repairs. They are historical evidence only, not qualification
	of this final local source. Build/dependency checksums, image security scan, current concurrency,
	BP durable provisioning integration, browser renewal, downstream isolation, and real Google remain
	outstanding. No completed tenant-isolation or SaaS/regulatory compliance certification is claimed.

Nonsecret build/probe logs remain under
`/workspaces/waooaw-operations/wc085-identity-publication`. No cloud operation, real credential access,
provider activation, commit, push or deployment occurred in this milestone.

## Existing-Stack Signup - Controlling Local Milestone, 2026-09-09

Founder direction to retain C#/Python/JavaScript supersedes the Java milestone above. Java source and
its dedicated probe were subsequently deleted during the authorized handover; historical findings
remain evidence only, not implementation instructions. Current ADR-003/ADR-008 and
Solution/Data contracts authorize stock Keycloak authentication plus current database-backed
customer membership. No custom token issuer or Keycloak account-write credential was introduced.

Implemented migration 29, four identity tables, C# atomic account/organisation/OWNER membership,
stable proof records, concurrency/idempotency and transaction-local actor/tenant context. Legacy
unproven rows are not silently upgraded. Implemented Google exact-subject read-only proof adapter,
existing registration/profile/completion/session HTTP path, and membership gating. Unsupported
customer routes deny; missing configuration/readiness returns unavailable rather than legacy
completion. Runtime provider readiness remains disabled. Migration is not applied to Demo.

Web completion now compares the completed account to the server-resolved current session using the
same server-held token, checks expiry, and returns only handoff confirmation. Returning registration
checks membership. Browser requests have bounded deadlines and stale/unmounted replies do not navigate.
This does not establish detection of every cross-tab cookie switch during an in-flight request.

| Executable check | Result and scope |
|---|---|
| Parent Docker full identity namespace | 203 PASS, 0 failed/skipped; 43 workspace PostgreSQL, 10 boundary HTTP/PostgreSQL, 28 adapter/boundary, 121 existing identity and 1 historical PostgreSQL rollback test |
| Real `WebApplicationFactory<Program>` | 11 PASS; standard RS256 validation with synthetic OIDC/JWKS and Keycloak reads, real restricted-role PostgreSQL; signup/profile/complete/session, invalid proof, caller headers, unsupported routes and missing configuration |
| Focused web auth/API suites | 81 PASS across 12 suites; generated-client wire shape, account handoff, failure, expiry and cancellation |
| TypeScript | `tsc --noEmit --incremental false --pretty false` PASS |

Backend command: Docker `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj`
with `-p:RestoreForce=true -p:IsTestProject=true` and filter
`FullyQualifiedName~Waooaw.BusinessPlatform.Tests.Identity`. The 203 run predates the additional
11-test file; that file passed separately and did not modify shared application code. Do not report
these as one combined 214-test run. All database data and identity proofs are synthetic.

Still required: apply/rollback rehearsal against the full schema, actual Keycloak read-only permission
and private TLS configuration, HMAC/secret references, real browser/OAuth and account-switch proof,
returning/recreated identity continuity, independent CE/PR/AIR/WBE membership checks and supported
portal reads, immutable candidate builds/scans and pre-PR/release gates. No production readiness,
real Google success, full WC-085 story PASS, commit, push, cloud change or deployment is claimed.

## Handover Parking Scope - 2026-09-09

Founder authorized handover preparation and saving existing work on draft PR #409, with the only new
code change being deletion of the Java experiment. Removed the provider Java/Maven/Docker fixture,
service descriptors, dedicated Java publication probe and experiment-specific ignore rules. Static
checks found no experiment files or executable references in source, scripts, infrastructure, web,
Compose or workflows. No existing C#/Python/web behavior was edited in this parking step.

WC-085 Section 18 and `work-contracts/WC-085-handover.md` are the controlling continuation plan.
The prior milestone's no-commit/no-push statement is historical; the parked commit and fresh required
pre-PR lifecycle result are bound in draft #409's prepared Author Review and runtime evidence.
No new feature-test counts are claimed by parking. Generated web logs/TypeScript build cache are not
release evidence and are excluded from the commit. No real Google, cloud, deployment or merge action.

Parking validation: Docker handover consistency check passed (31 exact path anchors, all 26 stories,
H1-H9, checkpoint below 200 lines and Java removal); editor diagnostics and `git diff --check` passed.
Docker Gitleaks v8.28.0 scanned the candidate diff against `origin/main` (approximately 1.26 MB) with
zero leaks. The unused `wc085-identity-publication:local` image and empty source directories were
removed. Historical permission-probe findings remain evidence, not an executable Java path.