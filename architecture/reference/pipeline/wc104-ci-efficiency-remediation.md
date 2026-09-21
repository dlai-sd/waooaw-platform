# WC-104 CI Efficiency Remediation Specification

## Record Control

| Field | Value |
|---|---|
| Status | SHADOW IMPLEMENTATION - HOSTED EVIDENCE PENDING |
| Owning office | Platform IT Expert (INST-010) |
| Extends | WC-104 End-to-End Docker Runner Supply And Cache Reuse |
| Evidence baseline | PR #466, CI run `35557086720`, Code Quality run `35557086708` |
| Constitutional basis | C-023, C-059, C-065, C-071, C-076, C-077, C-080, C-086 |
| Activation boundary | Selective hosted enforcement and release-image carry-forward require separate Founder authorization |

## 1. Purpose

This specification closes the efficiency gap exposed after WC-104 implementation. WC-104 created
canonical validation-runner identities, narrow build contexts, immutable GHCR supply, verified
digest consumers, remote BuildKit caches, catalog execution, and safe local evidence carry-forward.
Those controls prevent consumer-side runner builds and permit reuse within one candidate lifecycle.

PR #466 changed only `.github/workflows/deploy.yaml` and one pipeline regression test. Its hosted
execution nevertheless built four validation runners in Code Quality, started four duplicate runner
supply jobs in CI that later resolved registry hits, built all seven application service images,
computed the validation plan twice, and selected all 43 focused gates. This behavior is safe but does
not satisfy WC-104's intended source-only zero-build outcome or an efficient change-aware PR path.

The required end state is:

```text
one PR event
    |
    +-- one static authority and change-impact plan
    +-- one identity-scoped runner supply per required runner
    +-- always-on governance and secret checks
    +-- affected component gates and service images only
    +-- verified carry-forward evidence for unaffected required checks
    +-- one current-head aggregate result
```

GitHub may start a new workflow run for each `opened`, `reopened`, `ready_for_review`, or
`synchronize` event. Efficiency comes from canceling stale runs and making the new run resolve to
zero unnecessary builds and zero unnecessary costly commands, not from suppressing required
current-head status contexts.

## 2. Implemented Baseline

The remediation must preserve these merged WC-104 controls:

| Capability | Implemented behavior | Required preservation |
|---|---|---|
| Canonical runner identity | Four runner identities derive only from declared toolchain and dependency inputs | Application source, tests, evidence and timestamps remain excluded |
| Narrow contexts | Generated contexts contain only declared runner inputs | Missing or changed required inputs fail closed |
| Immutable supply | GHCR digests and provenance are verified before consumption | No mutable-tag or unverified fallback |
| Producer/consumer separation | Consumers pull supplied digests and never invoke runner builds | A trusted miss has at most one producer |
| Remote acceleration | Buildx imports and exports identity-scoped GHA caches | Cache state accelerates work but never authorizes PASS |
| Catalog execution | Commands and runner assignments come from the validation catalog | Workflow YAML does not redefine test commands |
| Evidence reuse | Exact and nearest valid ancestor evidence can be reused per gate | Every reuse emits current-head provenance and fails closed on impact |
| Static-first local preparation | Deterministic authority and configuration failures precede costly nodes | Invalid metadata starts zero costly processes |
| Full authoritative inventory | PR, main and release coverage remains authoritative while selection is Shadow | No gate reduction before activation evidence and Founder approval |

## 3. Observed Gap

### 3.1 PR #466 Measurement

| Observation | Actual result | Required result for the same change class |
|---|---:|---:|
| Validation-runner builds | 4 | 0 when all four canonical identities already have trusted digests |
| Duplicate runner-supply jobs | 4 additional registry-hit jobs | 0; one supply graph per workflow run |
| Application service-image builds | 7 | 0 for a deployment-workflow and pipeline-test-only change |
| Validation-plan executions | 2 | 1 |
| Focused catalog gates | 43 | Explicit governance, workflow, pipeline and release-owned gates only |
| Qualification-plan nodes | 59 | Full inventory may be retained for Shadow comparison without executing every node |
| Selected named prechecks | `gitleaks`, `release_qualification` | Same result is acceptable; unrelated jobs must not bypass this selection |

### 3.2 Root Causes

1. Pull-request runner resolution uses `candidate-<head-sha>-<identity>` before considering an
   existing trusted `identity-<identity>` image. Every new PR head can therefore miss even when its
   toolchain identity is unchanged.
2. `ci.yaml` and `code-quality.yaml` are independent top-level workflows. Each invokes runner supply
   and validation planning, so one PR event creates two producer graphs and two plans.
3. The seven-service PR build matrix is unconditional for every pull request. GHA layer cache can
   shorten a build but does not prevent the build job or prove that it was required.
4. `.github/workflows/**` is one global trigger. A deployment-only workflow change therefore forces
   all components and every catalog gate into the focused plan.
5. The validation plan exports only `release_required`. Test, quality, security and service-image
   jobs do not receive or enforce per-gate and per-component applicability.
6. The generated qualification plan uses `--all-gates`. This is valid as a Shadow comparison
   inventory, but consumers currently use it as the executable plan even when the focused plan is
   smaller.
7. WC-104 hosted requirements R001, R002, R004, R007, R009 and R013 remain without the required
   multi-run hosted evidence. R016 therefore cannot truthfully be complete.

### 3.3 Full Change Impact

| Component | Direct change | Compatibility obligation |
|---|---|---|
| `.github/workflows/ci.yaml` | Own the PR and `main` plan, runner supply, selected matrices and aggregate verdict | Existing required status and exact-seven release-manifest dependencies must continue to resolve |
| `.github/workflows/code-quality.yaml` | Remove independent PR/push orchestration and accept plan/runner inputs through `workflow_call` | Scheduled mutation testing remains available and receives a full scheduled plan |
| `.github/workflows/validation-plan.yaml` | Emit the v2 executable plan, required runners, service builds and static-preflight result | Exact base/head binding, Shadow comparison and retained evidence remain intact |
| `.github/workflows/validation-runner-supply.yaml` | Supply only selected runners and resolve trusted identity before PR-scoped candidates | Fork permissions, concurrent misses, provenance and immutable digest guarantees remain fail closed |
| `.github/workflows/integration-tests.yaml` | On `main`, consume the plan and runner manifests produced by CI instead of supplying them again | Full Integration and Contract inventory remains authoritative after merge |
| `.github/workflows/e2e-acceptance-tests.yaml` | On `main`, consume the shared plan and runner manifests or a trusted manifest bundle from CI | Manual environment dispatch remains independently runnable and fail closed |
| `.github/actions/run-validation-gate/action.yml` | Consume the selected executable plan and reject unselected or absent gate entries | Gate commands, resources and artifact contracts remain catalog-owned |
| `.github/actions/use-validation-runner/action.yml` | Consume one identity-resolved manifest and record current consumer telemetry | Every consumer verifies digest, platform and provenance and performs zero builds |
| `validation/engineering-validation.yaml` | Add explicit workflow/control ownership and service-build mappings | Unknown paths still force full execution; no path may silently select nothing |
| `validation/authoritative-gate-baseline.yaml` | Model shared orchestration and applicable/not-applicable status behavior | Every existing gate and threshold remains represented for PR, `main` and release lifecycles |
| `validation/runner-supply.json` | Remain the canonical runner-input declaration; version only if schema changes | Unrelated source remains excluded and every actual toolchain input remains included |
| `scripts/validation_policy.py` | Produce deterministic component, gate, runner, service and preflight selections | Reverse dependencies, renames, deletions, ownership conflicts and unknown paths fail closed |
| `scripts/precheck_orchestrator.py` | Consume the same selected plan and prioritize static nodes before costly nodes | Existing exact and carry-forward evidence trust rules remain unchanged |
| `scripts/prepare_pr_body.py` | Invoke the expanded static repository phase before constructing costly nodes | Invalid authority, output, workflow, Compose or Docker graph starts zero builds and zero test containers |
| `scripts/validation_control/runner_supply.py` | Support trusted identity-first resolution metadata and identity-aware producer locks | Mutable tags and unverified provenance remain prohibited |
| `scripts/validation_control/hosted_measurements.py` | Measure plans, producers, consumers, builds, skips and carry-forward outcomes | Unsupported savings cannot be inferred from static or local evidence |
| Application Dockerfiles and `docker-compose*.yml` | No behavioral rewrite expected; become inputs to static Docker graph checks | Valid current build contexts, targets, arguments and Compose references continue to pass |
| Pipeline and validation-control tests | Add topology, selection, concurrency, static-preflight and aggregation fixtures | Negative tests fail for duplicate producers, unconditional builds and missing required statuses |
| WC-104 requirement ledger and evidence | Replace blocked hosted rows only with direct multi-run evidence | Aggregate test counts or one successful run cannot mark a blocked row PASS |

### 3.4 Lifecycle Impact

| Lifecycle | Current duplication | Target behavior |
|---|---|---|
| Local edit | PR preparation may select a broad release gate before all Docker/workflow structure is checked | Static repository and Docker graph compilation first; only selected costly gates follow |
| Pull request | CI and Code Quality each supply four runners and compute a plan; CI always builds seven services | One plan, one selected runner supply, zero unaffected service builds and one aggregate verdict |
| PR synchronization | Head-scoped candidate tags can rebuild unchanged runners | Same-PR or trusted identity digest resolves with `build_count=0`; stale run is canceled |
| `main` CI | CI, Integration and E2E independently supply runners and plans | CI publishes a trusted plan/manifest bundle consumed by downstream `workflow_run` or reusable workflows |
| Scheduled quality | Code Quality owns mutation schedules and currently performs full supply | Scheduled caller requests only required mutation runners while retaining the full scheduled gate contract |
| Manual E2E | Dispatch can occur without a preceding CI artifact | Resolve trusted identity manifests independently; build only on an authorized verified miss |
| Release/deployment | Exact-seven release identity depends on all service digests | Preserve full release inventory and publication until a separate release-composition amendment is approved |

## 4. Required Design

### 4.1 One Hosted Orchestrator

`ci.yaml` becomes the single pull-request and `main` entry point. `code-quality.yaml` becomes a
`workflow_call`-only reusable workflow, or its jobs move into `ci.yaml`. It must not retain an
independent `pull_request` or `push` trigger.

The orchestrator order is:

1. checkout and static authority checks;
2. compute one exact base/head change-impact plan;
3. supply only runners required by the executable plan;
4. execute always-on and selected gates;
5. build only selected application images;
6. compare focused results with the full Shadow inventory;
7. emit one aggregate required status and immutable evidence package.

One workflow run produces exactly one plan artifact and no more than one manifest per selected
runner identity. A reusable workflow consumes those outputs; it must not regenerate them.

### 4.2 Identity-First Runner Resolution

Runner resolution uses this order:

1. calculate canonical identity from `validation/runner-supply.json`;
2. resolve and verify trusted `identity-<identity>` in GHCR;
3. for a same-repository pull request only, resolve a PR-scoped
   `candidate-pr-<number>-identity-<identity>` and verify its provenance;
4. on a verified miss, acquire a lock scoped to repository, trust domain, runner, platform and
   identity, then build exactly once;
5. publish an identity tag only from an authorized trusted `main` event;
6. publish a PR-scoped candidate tag only when repository permissions permit it; otherwise provide
   one run-scoped digest without weakening provenance checks.

Source-only synchronization of one PR reuses its prior candidate digest. Any PR can reuse a trusted
identity digest published from `main`. A dependency, Dockerfile, base digest, platform or build-
argument change creates a new identity and exactly one producer build.

The current runner-only concurrency key is replaced with an identity-aware key. Different identities
may build concurrently; duplicate producers for one identity serialize and the loser resolves the
winner's verified digest.

### 4.3 Executable Plan Contract

The validation-plan workflow publishes one `waooaw.validation-plan/v2` document and matching job
outputs:

```json
{
  "base_sha": "<40-hex>",
  "head_sha": "<40-hex>",
  "event": "pull_request|push|release",
  "full_inventory_required": false,
  "selected_components": ["business-platform"],
  "selected_gates": ["test-dotnet:business-platform"],
  "selected_prechecks": ["gitleaks"],
  "required_runners": ["dotnet"],
  "service_builds": ["business-platform"],
  "always_on_gates": ["secrets", "constitutional-commit-gate", "author-review-gate", "authorization-tier-check"],
  "reasons": ["direct owner business-platform: src/business-platform/..."],
  "policy_version": "<version>"
}
```

Each list is also exposed as canonical JSON for `fromJSON(...)` matrix construction. Boolean outputs
must exist for empty-matrix guards. Every consuming job declares `needs: validation-plan` and either:

- executes because its gate/component is selected;
- verifies exact or carry-forward evidence and emits a current-head result; or
- records an explicit not-applicable result included by the aggregate gate.

The full qualification plan remains an evidence artifact for Shadow comparison. It is not the
default executable plan for a pull request after selective enforcement is authorized.

### 4.4 Path And Gate Ownership

Replace the single `.github/workflows/**` global trigger with explicit ownership classes:

| Change class | Required execution |
|---|---|
| Validation control plane: `ci.yaml`, validation plan/supply, catalog actions or policy | Full Shadow inventory; all runner identities whose inputs changed; no application images unless application build semantics changed |
| Deployment and promotion workflows | Workflow lint, secrets, constitutional gates, deployment pipeline tests and release qualification; no application service-image build |
| One application component | Component gates, declared reverse dependencies, affected service-image builds and always-on gates |
| Dependency or runner input | Affected runner build once, all gates assigned to that runner as policy requires, and affected service images only |
| Evidence/review-only | Static authority, evidence validation and always-on secrets; costly gates use verified carry-forward |
| Unknown or conflicting ownership | Fail closed to full gate execution and report the unowned path |
| `main` push or release | Full required gate inventory; image publication follows Section 4.6 |

Workflow files must be individually mapped. Adding an unmapped workflow fails the policy test rather
than silently widening every future workflow change.

### 4.5 Job Selection And Current-Head Evidence

The following checks remain always-on for pull requests because they are cheap or constitutional:

- secret detection;
- C-059 commit and PR traceability;
- C-065 author-review binding;
- C-066 authorization boundary;
- commit-message policy;
- validation-policy and requirement-ledger integrity.

Language tests, language quality, dependency scans, CodeQL languages, specification lint, release
qualification and service-image builds run only when selected by declared inputs or component
ownership. Required branch-protection contexts remain present through one aggregate gate or explicit
not-applicable jobs; absence of a selected job must never leave a required context pending.

Prior successful evidence is reusable only through the existing WC-104 exact or carry-forward trust
contract. Failed, canceled, partial, untrusted, stale-base, changed-input or unverifiable evidence
forces execution. A base-branch movement recomputes impact before reuse.

### 4.6 Application Image Policy

For pull requests, build and scan only affected services and declared reverse dependencies. A
workflow-only PR such as #466 builds zero application images. The build matrix comes from
`service_builds`, not a hardcoded seven-service matrix.

For `main`, full validation remains required. Initially, continue publishing all release images so
this remediation does not change the exact-seven release contract. A later separately authorized
release-composition change may carry forward an unchanged service digest after verifying prior
provenance and recording both the service source SHA and release composition SHA. That later change
must update GOAL-006 release-manifest, attestation and deployment acceptance contracts before it can
remove unchanged `main` image builds.

### 4.7 Static-First Docker And Workflow Compilation

No runner or application image build and no Docker test container may start until a single static
preflight job passes. The job uses pinned tools and performs these checks in order:

1. parse every changed YAML and JSON control file and validate its repository schema;
2. run pinned `actionlint` across changed workflows and referenced local actions;
3. validate the catalog, runner-supply configuration, requirement ledgers and authoritative-gate
   baseline, including uniqueness and completeness of workflow path ownership;
4. run `docker compose config --quiet` for every applicable Compose file and profile combination;
5. compile the Buildx/Bake graph and selected matrices, proving that contexts, Dockerfiles, targets,
   platforms, build arguments, tags and empty-matrix guards resolve;
6. run BuildKit Dockerfile static checks (`docker buildx build --check`, or the pinned equivalent)
   for each affected runner and service target without exporting an image;
7. dry-run the v2 plan and aggregate-status graph, proving that every required context resolves to
   selected, carried-forward or explicitly not-applicable;
8. run fast language syntax/type compilation only where changed inputs make it applicable, without
   starting service dependencies or producing release artifacts.

The preflight emits one exact-head `waooaw.static-preflight/v1` artifact containing tool digests,
checked files, generated matrices, selected targets, results and duration. A failure stops runner
supply, application Buildx jobs, integration services, release qualification and E2E jobs. A Docker
daemon or registry is not contacted before steps 1 through 3 pass. BuildKit checks may resolve base
metadata but must not execute Dockerfile layers, export images or publish caches.

Static checks are not behavioral evidence. Passing preflight permits selected builds and tests to
start; it never carries a test, scan, coverage, integration or release verdict.

## 5. Failure And Edge Cases

| Case | Required behavior |
|---|---|
| Registry or attestation service unavailable | Fail closed or perform one permitted build; never accept an unverifiable digest |
| GHA cache missing, corrupt or evicted | Build once from locked inputs and execute all selected tests |
| Two workflows request one missing identity | One producer builds; the other waits and verifies the resulting digest |
| Fork pull request lacks package write permission | Reuse trusted identity when available; otherwise use one explicitly untrusted run-scoped producer path and never publish trusted tags |
| Empty component or service matrix | Skip expensive matrix jobs cleanly while preserving the aggregate status |
| Runner input and application source both change | Build the affected runner once, then execute all selected component jobs against that digest |
| Workflow changes runner or catalog semantics | Select affected control-plane tests and runner identities; do not infer safety from filename alone |
| Deployment-only workflow change | Run workflow/deployment qualification without building application images |
| Prior evidence exists but intervening ownership is unknown | Reject carry-forward and execute the affected gate or full fail-closed inventory |
| PR receives a new commit while a run is active | Cancel the stale run; only the newest exact head may satisfy required status |
| Selected job fails | Aggregate gate fails; unaffected successful evidence may remain reusable if its trust tuple is intact |
| Main or release event | Retain full gate inventory and trusted publication authority |

## 6. Implementation Slices

This change delivers E0, identity-first E1 resolution, E2, E4 and E5. Identity-aware producer
locking, shared E3 orchestration, E6 hosted telemetry and E7 activation remain follow-up work.
The separate Code Quality entry point is retained until required-check configuration can be read and
migrated without changing protected status contexts. Canonical identity resolution avoids a second
build when trusted supply exists, but this change does not claim one plan or one supply graph per PR
event.

| Slice | Change | Primary files |
|---|---|---|
| E0 | Add static workflow, policy, Compose, Buildx graph and Dockerfile checks before costly work | `prepare_pr_body.py`, `validation-plan.yaml`, static-preflight scripts and tests |
| E1 | Resolve trusted identity and same-PR identity before building; make lock identity-aware | `.github/workflows/validation-runner-supply.yaml`, `runner_supply.py` |
| E2 | Produce one v2 plan with runner and service matrices | `validation-plan.yaml`, `validation_policy.py`, `engineering-validation.yaml` |
| E3 | Make Code Quality reusable and consume CI's plan and manifests | `ci.yaml`, `code-quality.yaml` |
| E4 | Gate tests, quality, CodeQL, dependency scans and release qualification from the plan | CI and reusable workflow jobs |
| E5 | Replace hardcoded PR service matrix with selected `service_builds` | `ci.yaml` |
| E6 | Add hosted telemetry, aggregate status and Shadow comparison | workflow evidence steps, `hosted_measurements.py` |
| E7 | Activate selective PR execution only after Section 8 passes | validation policy and Founder-controlled activation record |

No slice may reduce `main` or release gate inventory. E7 is a separate activation decision, not an
automatic consequence of merging E1 through E6.

### 6.1 Ordered Delivery Plan

| Order | Delivery action | Focused proof before proceeding |
|---:|---|---|
| 1 | Rebase a dedicated remediation branch on the confirmed post-#466 `main` | Clean worktree, exact merge base and unchanged authoritative baseline |
| 2 | Implement E0 static preflight without changing job selection | Static negative fixtures prove malformed workflow, policy, Compose and Docker targets start zero builds |
| 3 | Implement E1 identity-first supply and identity-aware locking | Registry-hit, miss, concurrent miss, fork and provenance tests pass; hosted telemetry shows producer count |
| 4 | Implement E2 plan v2 and explicit ownership | Path-impact matrix passes for workflow-only, component, dependency, evidence, unknown, `main` and release cases |
| 5 | Implement E3 shared PR orchestration | Workflow topology test proves one plan and one runner-supply graph |
| 6 | Implement E4 and E5 conditional gates and service builds in Shadow | PR #466 fixture selects zero service images and preserves all required status contexts |
| 7 | Extend shared manifest consumption to post-merge Integration and E2E | One `main` plan/supply producer; manual E2E fallback remains independently valid |
| 8 | Implement E6 telemetry and collect hosted samples | Required WC-104 hosted rows receive direct evidence; no row changes on inferred results |
| 9 | Run one exact-head full qualification and rollback rehearsal | All baseline gates and thresholds pass; rollback executes clean full inventory |
| 10 | Submit E7 activation evidence for separate Founder decision | Twenty representative Shadow samples, zero false negatives and complete author review |

Each slice is committed and validated independently. A failed focused check is repaired before the
next slice; broad Docker qualification is not repeated during ordinary iteration.

## 7. Test Specification

### 7.1 Unit And Contract Tests

1. A deployment-workflow plus pipeline-test fixture selects workflow lint, governance, secrets and
   release qualification, zero application components and zero service builds.
2. A source-only PR synchronization preserves runner identity and resolves `build_count=0`.
3. A runner dependency mutation changes exactly the affected identities and produces one build each.
4. Two concurrent producers for one identity produce one build and one verified registry hit.
5. Different identities are not blocked by the same concurrency key.
6. CI contains one runner-supply invocation and one validation-plan invocation for a PR event.
7. Code Quality has no independent PR/push trigger and consumes the caller plan.
8. Every costly job has a selected-gate or selected-component condition.
9. Empty matrices skip without syntax failure and the aggregate gate passes only when all required
   applicable checks pass.
10. Every workflow path has exactly one declared ownership class; unknown paths fail closed.
11. A carry-forward mutation matrix rejects changed commands, runners, environments, policies,
    source evidence, base ancestry and declared inputs.
12. Main and release fixtures retain the complete authoritative gate inventory.

### 7.2 Static Fail-Fast Test Matrix

| Injected defect | Expected result before any build/run |
|---|---|
| Invalid workflow expression, missing local action or malformed reusable input | `actionlint` or workflow contract failure |
| Duplicate/unowned workflow path or unknown component owner | Validation-policy failure with the exact path |
| Invalid Compose interpolation, service, profile or Dockerfile reference | Compose configuration failure |
| Missing Docker context, target, build argument or platform | Buildx/Bake graph compilation failure |
| Dockerfile undefined argument, invalid stage reference or unsupported instruction contract | BuildKit static-check failure |
| Empty selected matrix without a guard | Plan contract failure |
| Required status absent from selected/carried/not-applicable aggregation | Gate-equivalence failure |
| Invalid C-059/C-065 metadata, ledger or output target | Existing deterministic preflight failure |

Every fixture records `runner_build_count=0`, `service_build_count=0`,
`test_container_start_count=0` and `costly_node_construction_count=0`.

### 7.3 Hosted Acceptance Tests

At least three independent samples are required for each relevant scenario:

| Scenario | Passing condition |
|---|---|
| Repeat source-only commit in one PR | Zero runner builds after the first candidate supply; same verified digest consumed |
| New PR with identities already trusted on `main` | Zero runner builds |
| Runner dependency change | Exactly one build per changed identity; all consumers agree on digest |
| PR #466 path fixture | Zero runner builds when identities are trusted, zero application builds, one plan, and only declared costly gates execute |
| Single-component source change | Only owned component and reverse-dependency gates/images execute |
| Evidence-only successor | Zero unaffected costly executions; current-head carry-forward provenance emitted |
| Concurrent CI consumers | Duplicate producers equal zero; consumer build count equals zero |
| Main push | Full required gate inventory executes and trusted runner identity publication remains correct |

Measurements record workflow/run attempt, base/head SHA, changed-path digest, policy version, runner
identity, OCI digest, trust scope, producer count, consumer count, cache source, selected gates,
selected service builds, executed gates, carried gates, durations and final result.

## 8. Acceptance Gates

Selective PR enforcement may be proposed to the Founder only when all of the following are true:

1. WC104-R001, R002, R004, R007, R009 and R013 have direct hosted PASS evidence.
2. The WC104-R016 complete-ledger rule is satisfied at one exact candidate.
3. At least 20 consecutive representative Shadow samples contain zero false negatives.
4. The PR #466 fixture meets the zero-runner-build and zero-service-build conditions.
5. All required status contexts resolve on no-component and evidence-only changes.
6. Full `main` and release gate-equivalence tests pass.
7. Rollback restores full clean qualification without trusting cache or carry-forward evidence.
8. Author review records no unresolved correctness, security, supply-chain or evidence finding.

Target efficiency is measured, not inferred:

- one validation plan per event;
- zero duplicate runner producers;
- zero runner builds for unchanged trusted identities;
- zero application-image builds for non-application PRs;
- 100 percent execution of selected tests;
- 100 percent explicit provenance for reused or carried evidence;
- no reduction in `main` or release authoritative coverage.

## 9. Rollout And Rollback

1. Deliver E1 and E2 with telemetry while full hosted execution remains authoritative.
2. Deliver E3 through E6 in Shadow mode and collect the required hosted samples.
3. Compare selected, executed and failed gates on every sample; any false negative resets activation
   readiness and repairs ownership before further rollout.
4. Submit the exact evidence package for Founder authorization of E7.
5. After authorization, enforce selective PR execution while retaining full `main` and release
   inventory.

Rollback disables selective execution and evidence carry-forward, then runs the full clean inventory.
It does not disable immutable digest verification, provenance checks, non-root isolation, secret
handling or constitutional gates. Any unexplained missed gate, duplicate producer, wrong digest,
cache-dependent verdict or unresolved required context triggers rollback.

## 10. Decision Summary

The immediate repair should optimize pull-request orchestration without changing release identity:

- resolve runners by canonical identity rather than PR head;
- create one producer and one plan per event;
- make Code Quality consume the CI orchestration;
- select component jobs and PR service images from declared path ownership;
- retain cheap governance checks on every PR;
- preserve full `main` and release coverage until separately authorized evidence supports a narrower
  release-composition model.

This record grants no selective-enforcement activation, hosted publication, branch-protection,
deployment, approval or merge authority. The implemented Shadow controls remain subject to hosted
measurement and Founder review.