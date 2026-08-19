# GOAL-006 P3-WC01 Readiness Evidence

| Field | Value |
|---|---|
| `record_id` | `CR-GOAL-006-INST-009-04` |
| `record_type` | Contribution Record - blocked attempt |
| `goal_id` | GOAL-006 |
| Component | P3-WC01 - Cloud Readiness And Authorization |
| Authorization | FA-050; GOA-GOAL-006-INST-009-03; ACC-GOAL-006-INST-009-03 |
| Executor | INST-009 - Platform Architect |
| Attempted at | 2026-08-14T06:14:13Z |
| Result | BLOCKED - Azure live read token rejected by Entra security defaults |
| Mutation and spend | NONE; INR 0 |

## Evidence Sequence

| Step | Result | Evidence and consequence |
|---|---|---|
| Authorization chronology | PASS | GOA issued at 06:07:53Z; executor Acceptance at 06:09:44Z |
| GitHub identity | PASS | Authenticated GitHub CLI identity is `dlai-sd` |
| Azure cached account boundary | PASS, NOT LIVE SUFFICIENCY | CLI account metadata named the authorized tenant `0471534c-1bbe-40ab-ae65-3f721b62582c`, subscription `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84`, enabled state and user identity |
| Offline exact-six manifest | PASS | `scripts/goal006_manifest.py` returned `{"passed": true, "violations": []}` before provider access |
| Azure resource inventory | BLOCKED | Entra returned `AADSTS530035: Access has been blocked by security defaults` and required interactive authentication for the authorized tenant |
| Azure provider/region, quotas and budgets | NOT EXECUTED | Fail-closed command sequencing stopped after inventory authentication failure |
| GHCR exact-six retrievability | NOT EXECUTED | Fail-closed command sequencing stopped before registry queries |
| Public DNS control evidence | NOT EXECUTED | Fail-closed command sequencing stopped before DNS queries |
| Public pricing evidence | NOT EXECUTED | Not started before the identity stop condition |
| CT-07 | `NOT_EXECUTED_PHASE_3` | No live inventory exists from which a topology verdict can be made |

## Blocker And Recovery

The approved user identity requires interactive Azure reauthentication under tenant security
defaults. Credentials, device codes, passphrases and MFA responses must not be sent through chat or
stored in repository evidence.

Recovery requires the Founder to authenticate directly in the terminal with:

```bash
az logout
az login --tenant "0471534c-1bbe-40ab-ae65-3f721b62582c" \
  --scope "https://management.core.windows.net//.default"
```

After successful direct authentication, a fresh active-session authorization window is required
because FA-050 expires at session close or a stop condition, whichever occurs first. The next attempt
must begin again with identity-only verification. No permission expansion or alternate identity is
authorized as a workaround.

## Readiness Verdict

**ATTEMPT 1 BLOCKED WITHOUT A READINESS VERDICT.** No Azure inventory, quota, budget, GHCR, DNS,
pricing or CT-07 conclusion was established by this attempt. P3-WC02 through P3-WC08 remained
unauthorized.

## Attempt 2 - Renewed Read-Only Evidence

| Field | Value |
|---|---|
| Authorization | FA-051; GOA-GOAL-006-INST-009-04; ACC-GOAL-006-INST-009-04 |
| Executed | 2026-08-14T07:12:01Z through 2026-08-14T07:15:18Z |
| Monetary result | INR 0 new spend; no resource, role, provider, registry or DNS mutation |
| Identity | PASS - exact authorized tenant/subscription, enabled state, user session |
| Overall result | BLOCKED - P3-WC01 exit conditions are not satisfied |

### Live Inventory And CT-07

The subscription contains one Central India resource group, `waooaw-dev-rg`, with one Central India
Key Vault. It also contains three out-of-region Cognitive Services resources: one in UAE North and
two in West US 3. There are no Container Apps environments and no Container Apps.

| CT-07 expectation | Observed | Result |
|---|---|---|
| Approved Central India delivery boundary | Existing development group and Key Vault are in Central India; unrelated AI resources exist outside the approved P3-WC01 region | PARTIAL |
| Exact-six runtime topology | Zero Container Apps environments and zero Container Apps | FAIL |
| Exact-six manifest identity | Offline signed manifest validates; no live runtime tuple exists | FAIL_LIVE |
| Internal/public ingress topology | No live Container Apps topology exists to inspect | NOT_PROVABLE |
| CT-07 verdict | Authorized inventory does not match the accepted six-member topology | **FAIL** |

CT-07 failure records current absence; it does not authorize creation or repair.

### Azure Prerequisites

| Check | Observed | Result |
|---|---|---|
| `Microsoft.App` | Registered; 35 Central India resource types | PASS |
| Container Apps managed-environment quota | 0 used of 20 | PASS |
| `Microsoft.KeyVault` | Registered | PASS |
| `Microsoft.DBforPostgreSQL` | Registered | PASS |
| `Microsoft.OperationalInsights` | Registered | PASS |
| `Microsoft.ManagedIdentity` | Registered | PASS |
| `Microsoft.Storage` | Not registered | BLOCKED_PREREQUISITE |
| `Microsoft.Insights` | Not registered | BLOCKED_PREREQUISITE |
| Subscription budgets | None | BLOCKED_PREREQUISITE |
| Current human role | Subscription Owner, plus duplicate Owner and service roles | EXCESSIVE_FOR_READINESS |

No provider was registered, budget created or role changed. P3-WC02 requires separately authorized
least-privilege identities and prerequisite creation; the human Owner session is not recommended as
the delivery identity.

### GHCR Exact-Six Retrievability

The signed offline manifest passed with zero violations. `dlai-sd` is a GitHub user owner, not an
organization owner. Both organization and user package endpoints returned HTTP 404 for every
expected package, so none of the six reviewed digests is currently retrievable from the approved
GHCR namespace.

| Member | Digest | Live result |
|---|---|---|
| constitutional-engine | `sha256:9f17b7fcd98aecbe343f28594a3a7ce8222762c4a5cbd7c9d2ff69571250568d` | PACKAGE_NOT_FOUND |
| business-platform | `sha256:e1b6bbd028819ed3cc5d92fd209e26ff907d350cc705b45b358af09bc27b825d` | PACKAGE_NOT_FOUND |
| professional-runtime | `sha256:8b92afcece53868076b9a1faea32ef4bf9ae37a833a5d13745d0920b23c8e67e` | PACKAGE_NOT_FOUND |
| ai-runtime | `sha256:ff843470679e98356bb0bb06d72e76ff6c3ee9b496d0ef465ca25a18dc3da8c6` | PACKAGE_NOT_FOUND |
| web | `sha256:99529bdbe80d01eca6cacbee3ed054e86b024956d505a4b08a401236561857ed` | PACKAGE_NOT_FOUND |
| billing-engine | `sha256:253334ac456574e186d3cc016bcbb4b3ccdba16dbc8abda117d7ab06d197ff27` | PACKAGE_NOT_FOUND |

P3-R04 is not satisfied. Publishing or rebuilding images requires a separate implementation and
registry-push authorization; mutable tags or replacement digests cannot repair this result.

### Public DNS Evidence

| Record | Observed value |
|---|---|
| NS | `ns01.domaincontrol.com`, `ns02.domaincontrol.com` |
| SOA | `ns01.domaincontrol.com`, responsible mailbox at `dns.jomax.net` |
| Apex A | `35.190.6.91` |
| `www` A | `35.190.6.91` |
| CAA | No record observed |

This proves public delegation and resolution, not authenticated registrar control. No DNS record was
changed. Environment hostname activation remains Founder-protected.

### Dated Public Pricing Evidence

The Azure Retail Prices API returned 210 Central India records on 2026-08-14 in USD. Relevant
consumption rates include:

| Meter | Public retail rate |
|---|---|
| Container Apps standard active vCPU | USD 0.000024 per second |
| Container Apps standard idle vCPU | USD 0.000003 per second |
| Container Apps standard active/idle memory | USD 0.000003 per GiB-second |
| Container Apps standard requests | USD 0.40 per 1 million requests |
| PostgreSQL Flexible Server B1MS compute | USD 0.0245 per hour |
| PostgreSQL Flexible Server Premium SSD v2 storage | USD 0.131 per GiB-month |
| Log Analytics free data analyzed | USD 0.00 per GB, subject to service terms and limits |

A trustworthy Demo/UAT/Production total cannot be calculated yet because accepted environment
hours, PostgreSQL SKU/storage/backup, telemetry volume, traffic, data egress, DNS/TLS/edge choice,
tax and USD/INR conversion basis remain unresolved. The Terraform workload defaults all six members
to zero minimum replicas, 0.5 vCPU and 1 GiB with a maximum of 10; that is a scaling contract, not an
accepted workload forecast. P3-R06 is PARTIAL and TGT-02 through TGT-15 remain owner decisions or
unaccepted recommendations.

## Consolidated P3-WC01 Verdict

**BLOCKED - NOT READY FOR P3-WC02.** Identity, Central India Container Apps availability, basic
quota, public DNS observation and dated unit pricing are established. P3-WC01 exit fails because
CT-07 fails, all six GHCR packages are absent, required providers and budgets are missing,
authenticated DNS control is unproven, access is not least privilege, total cost ranges are
incomplete and TGT-02 through TGT-15 remain unresolved. No mutation or spend occurred. P3-WC02
through P3-WC08 remain unauthorized.

## Attempt 3 - FA-052 Autonomous Remediation Checkpoint

| Field | Value |
|---|---|
| Authorization | FA-052; GOA-GOAL-006-P3-AUTONOMOUS-01; ACC-GOAL-006-P3-AUTONOMOUS-01 |
| Executed | 2026-08-14 |
| Result | REMEDIATION IN PROGRESS - P3-WC01 exit remains blocked |
| Mutation boundary | Named providers, one subscription budget, protected state bootstrap and one redundant Owner assignment removal only |
| Application resources and traffic | NONE; no Demo/UAT/Production foundation, workload, DNS or customer-traffic mutation |

### Cleared Prerequisites

| Control | Verified result |
|---|---|
| `Microsoft.Storage` | `Registered` |
| `Microsoft.Insights` | `Registered` |
| Monthly budget | `waooaw-phase3-monthly`, INR 10,000, monthly |
| Budget notifications | 80% Actual and 100% Forecasted to subscription Owner |
| State resource group | `waooaw-platform-rg`, Central India |
| State storage | `waooawp3tfstate2ed118`, `Standard_LRS`, container `tfstate` |
| State transport/access | HTTPS only, TLS 1.2, shared keys disabled, blob public access disabled, Azure AD/OIDC backend authority |
| State recovery | Blob versioning plus 30-day blob and container delete retention |
| State network | Public endpoint enabled only for governed runner reachability; firewall default deny with Azure-services bypass |
| Bootstrap human data access | Temporary Storage Blob Data Contributor removed; read-back returned zero assignments |
| Human subscription authority | One redundant direct Owner assignment removed; one Founder Owner assignment preserved |

The storage account is the first spend-bearing FA-052 resource. Azure billing has not yet emitted a
reliable actual charge. The INR 10,000 monthly budget and 80%/100% alerts were established before
resource creation. No amount is inferred from delayed usage data.

### Repository Delivery Remediation

The CI workflow now builds without publishing on pull requests. A successful `main` run publishes
all six GHCR images, emits BuildKit SBOM/provenance attestations, captures registry digests,
aggregates an exact-six immutable manifest and signs that manifest through GitHub OIDC attestation.
The ordered promotion controller consumes only that tuple: Demo apply and candidate verification,
an exact independent Demo acceptance record, UAT apply and candidate verification, an exact
independent UAT acceptance record, then Production foundation plan-only. Customer traffic
activation is absent. Promotion also requires repository variable
`GOAL006_PROMOTION_ENABLED=true`; absent or false fails closed.

Pull requests build and load images only on their matrix runners for local Trivy scans; they cannot
publish. Main retains registry-based scans. Every promotion consumer checks out the triggering CI
source SHA and rejects source-commit or GitHub-run mismatch in the signed manifest.

Pinned Terraform 1.9.8 and AzureRM 4.14.0 validated all six Demo/UAT/Production foundation and
workload roots. The workflow requires a separately provisioned constrained bootstrap identity for
foundation, protected-state firewall and cost evidence, then switches to the Terraform-created
environment deployment identity for workload actions. That identity receives only environment-RG
Contributor/RBAC authority and Blob Data access to the exact protected state account. Verification
uses a separate Reader-only identity. Exact environment subjects avoid changing the repository-wide
OIDC subject template used by the legacy autonomous-sprint application.

The financial gate checks INR month-to-date actual, Azure forecast, accepted planned incremental
monthly cost and cumulative one-time cost. It stops at either hard ceiling and also stops at 80% for
consolidation. Protected state coordinates and subscription ID are exact constants at runtime.

Qualification on 2026-08-14 executed `pytest -q tests/pipeline/test_goal006*.py` with 161 tests
passing before review. After review repairs, the complete suite passed 171/171; all six pinned
Terraform roots validated; the four changed workflows passed pinned `actionlint` v1.7.7; JSON/YAML
parsing and `git diff --check` passed.

### Remaining Stop Conditions

| Blocker | Evidence and consequence |
|---|---|
| Exact-six registry tuple | Workflow is implemented but cannot publish under its trusted `main` identity before Founder-reserved PR review and merge |
| GitHub environment administration | Current integration token returned HTTP 403 for environment creation; no environment or variable was created |
| Promotion enablement | Deliberately absent/false until P3-WC01 independently passes |
| Bootstrap and deployment identities | Constrained bootstrap plus exact deployment/verifier environment identities require authorized GitHub/Azure administration before P3-WC02 execution |
| CT-07 | Still FAIL because no live exact-six application topology exists |
| DNS | Public resolution is known; authenticated registrar control is still unproven |
| Targets and cost ranges | TGT-02..15 and complete environment totals remain unresolved |

**ATTEMPT 3 CHECKPOINT: BLOCKED BEFORE P3-WC02.** Prerequisite controls are materially improved,
but no component exit is claimed and no automatic progression has occurred.

## Attempt 4 - PR CI Security And Specification Remediation

| Field | Value |
|---|---|
| Authorization | FA-052 plus explicit Founder implementation authorization for the current session |
| Executed | 2026-08-14 |
| Result | LOCAL QUALIFICATION PASS - trusted GitHub PR/main execution still required |
| Cloud mutation and new spend | NONE |

The missing Spectral configuration is now explicit in `.spectral.yaml`, and the Spectral action is
pinned to the immutable v0.8.13 commit. Both canonical OpenAPI documents produce zero errors; the
62 existing documentation warnings remain visible and non-blocking.

The three Python release manifests now use fixed dependency versions. Unused `python-jose` was
removed instead of retaining its unfixed `ecdsa` dependency. The AI Runtime's accepted non-PyPI CPU
Torch wheel is audited by the installed-image Trivy gate. Trivy ignores vendor-unfixed findings but
continues to fail every fixable HIGH or CRITICAL finding in pull-request and trusted-main scans.

| Qualification | Result |
|---|---|
| Professional Runtime | 167/167 PASS |
| AI Runtime | 43/43 PASS |
| Billing Engine | 402 PASS; 2 PostgreSQL integration tests remain intentionally routed to their dedicated harness |
| GOAL-006 pipeline contracts | 172/172 PASS |
| Professional/Billing strict dependency audit | No known vulnerabilities |
| AI dependency audit | No known vulnerabilities; non-PyPI `torch==2.6.0+cpu` deferred to installed-image scan |
| Billing Engine image | Zero fixable HIGH/CRITICAL findings |
| Professional Runtime image | Zero fixable HIGH/CRITICAL findings, including Temporal bridge Cargo dependencies |
| AI Runtime image | Zero fixable HIGH/CRITICAL findings, including the CPU Torch wheel |
| Spectral | 0 errors; 62 warnings |
| Buf | Format, STANDARD lint and breaking compatibility against `main` PASS; published package/RPC naming retained through explicit exceptions |
| .NET dependency audit | Constitutional Engine and Business Platform contain no known vulnerable packages after coordinated OpenTelemetry 1.17.0 upgrade |
| Pinned actionlint v1.7.7 | PASS |
| Diff hygiene | PASS |

The first GitHub rerun exposed three CI-environment differences. Spectral and Buf actions attempted
to write PR comments with a read-only integration token; they were replaced by pinned non-commenting
CLI containers. Buf then exposed legacy format and naming findings; the proto was mechanically
formatted and only its compatibility-protected package-directory and RPC request/response naming
rules were excepted. Trivy's default secret scanner differed from the locally qualified
vulnerability-only policy; explicit `scanners: vuln` now makes Gitleaks the sole secret-detection
owner. The dependency job also reached a separate .NET OpenTelemetry advisory, resolved by upgrading
both .NET services to coordinated 1.17.0 packages and removing the prior `NU1902` suppression.

**ATTEMPT 4 CHECKPOINT: BLOCKED BEFORE P3-WC02.** The two observed CI blockers are remediated and
locally qualified. P3-WC01 still requires PR CI, Founder-reserved merge, trusted-main exact-six
publication, authorized GitHub environment and OIDC administration, DNS/cost/target closure, CT-07
and independent exit acceptance. Promotion remains disabled.

## Attempt 5 - Supply-Chain And Runtime Review Remediation

| Field | Value |
|---|---|
| Authorization | FA-052 plus explicit Founder implementation authorization for the current session |
| Executed | 2026-08-14 |
| Result | LOCAL QUALIFICATION PASS - exact-commit independent review pending |
| Cloud mutation and new spend | NONE |

Pull-request image builds are now structurally read-only: they have no package-write permission,
perform no registry login and cannot push. Trusted `main` publication alone receives package-write
authority. Its authenticated scan job retains the exact-six SARIF payloads, and release-manifest
creation now requires and hashes the actual SBOM and provenance JSON retrieved by Buildx from each
published digest. Missing or malformed exact-six scan, SBOM or provenance membership fails closed.

Buf breaking compatibility now checks an exact fetched `origin/main` commit SHA after a full-history
checkout. This removes both shallow-clone failure and mutable local-branch resolution from the
specification gate.

Azure Container App workloads use anonymous exact-digest GHCR pulls. Every environment root defaults
`ghcr_packages_public` to false. The deployment workflow verifies all six exact image references with
unauthenticated Buildx inspection before input generation can emit the true assertion; the workload
module rejects enabled resources without it. Lease-driven teardown remains available when workloads
are disabled.

| Qualification | Result |
|---|---|
| GOAL-006 pipeline contracts | 176/176 PASS |
| Registry manifest contracts | 11/11 PASS, including missing/tampered attestation evidence |
| Deployment input contracts | 7/7 PASS, including absent anonymous-pull verification |
| Terraform 1.9.8 / AzureRM 4.14.0 | All six Demo/UAT/Production foundation/workload roots VALID |
| Buf 1.72.0 | Format, STANDARD lint and exact-SHA breaking compatibility PASS |
| Spectral 6.15.0 | 0 errors; 62 visible warnings |
| Edited workflows | Pinned actionlint 1.7.7 PASS |
| Constitutional Engine | Warnings-as-errors build PASS; test project 83/83 PASS |
| Business Platform | Warnings-as-errors build PASS; test project 349/349 PASS |
| .NET dependency audit | No known direct or transitive vulnerabilities in either service |
| Editor diagnostics and diff hygiene | PASS |

The Business Platform qualification also repaired EF Core interceptor nullability signatures after
the dependency upgrade and removed one test's hardcoded `/workspace` repository path.

**ATTEMPT 5 CHECKPOINT: BLOCKED BEFORE P3-WC02.** Fresh independent review must accept this exact
commit before PR CI and Founder-reserved merge can be used to reach trusted-main publication. P3-WC01
still additionally requires exact-six publication, authorized GitHub/Azure environment identity
administration, authenticated DNS and accepted cost/target closure, CT-07 and independent exit
acceptance. Promotion remains disabled.

### Attempt 5 Author Repair After Review Input

The primary executor treated the rejected review as defect input and completed the repairs without
delegating implementation or invoking another independent review:

- Registry evidence is structurally parsed as successful Trivy SARIF, platform-keyed SPDX 2.3 and
  BuildKit SLSA provenance from the exact GitHub run. Minimal, unrelated or finding-bearing payloads
  fail closed.
- Every published image digest receives a GitHub OIDC build-provenance attestation pushed to GHCR.
  Its bundle is hashed into the exact-six manifest. Deployment downloads the evidence package,
  recomputes all scan/SBOM/provenance/signature hashes and verifies each OCI image attestation before
  anonymous pull verification or Terraform input generation.
- Buf breaking comparison uses the immutable pull-request base SHA or previous trusted-main push SHA,
  never a mutable branch lookup.
- An hourly Demo/UAT-only lease reconciler reads the exact applied inputs from protected state and
  applies only after expiry or revocation. A plan validator prohibits Production and rejects every
  create/update/replacement or deletion outside Container Apps, their identities and exact secret
  role assignments.

Author qualification after these repairs: GOAL-006 pipeline contracts 181/181 PASS; all five changed
workflows pass pinned actionlint 1.7.7; all six Terraform 1.9.8 roots validate; changed Python helpers
compile; Buf exact-SHA breaking compatibility and diff hygiene pass. Prior CE 83/83 and BP 349/349
results remain applicable because this repair changed no service runtime code.

This is an author checkpoint, not independent acceptance. P3-WC02 remains stopped and promotion
remains disabled.

### Attempt 6 Current-Main Rebuild And Independent Review Repair

The PR was rebuilt from current `main` to exclude superseded runtime and coverage changes. The
cloud-only rebuild preserves separate pull-request image validation and trusted-main exact-six
publication, immutable release evidence, Demo then UAT evidence gates and Production planning only.

A fresh independent review rejected the first rebuilt SHA because the reusable deploy workflow did
not itself prohibit Production apply, queued workflow runs could promote a stale `main` SHA, OIDC
workflow/ref enforcement was described more strongly than implemented, and Demo/UAT acceptance
variables were not stage-specific. The author repaired all findings:

- the reusable deployment workflow rejects `prod` with `apply=true` before checkout or Azure login;
- promotion verifies the release SHA is the current `main` tip before any environment job;
- deployment and verification require the exact reviewed `promote.yaml@refs/heads/main` caller
  before OIDC login, layered with exact no-wildcard environment subjects and protected environments;
- unused Terraform variables that implied credential-level workflow binding were removed; and
- Demo and UAT use distinct run, SHA and evidence-digest acceptance variables.

The focused post-repair contract suite passed 21/21. This remains author evidence pending complete
cloud-suite qualification, Terraform validation, workflow lint and fresh independent re-review on
the repaired SHA. It does not authorize promotion, P3-WC02 progression, PR approval or merge.

The first re-review then identified a remaining time-of-check/time-of-use window: `main` could
advance after initial authorization while an older promotion remained queued or progressed between
stages. The repaired controller now cancels superseded promotion runs and revalidates the release
SHA against the current `main` tip before cloud access, immediately before each Terraform apply,
before independent verification, and before each Demo/UAT acceptance. The focused stage contract
suite again passed 21/21. Fresh independent review remains required on the frozen implementation
SHA.