# WC-104 - End-to-End Docker Runner Supply And Cache Reuse

## Record Control

| Field | Value |
|---|---|
| Authoring office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-20 continuous working conversation |
| Status | IMPLEMENTATION AUTHORIZED |
| Corrects | WC-102 runner supply, cache reuse, catalog execution and evidence gaps |
| Depends on | WC-100, WC-101, WC-102, ADR-012, ADR-013, ADR-045 and ADR-050 |
| Delivery shape | One end-to-end runner supply and validation control repair; no partial completion claim |
| Constitutional basis | C-023, C-059, C-065, C-071, C-076, C-077, C-080 and C-086 |
| Activation boundary | Full PR, `main` and release gates remain authoritative; selective enforcement remains separately Founder-gated |

## 1. Authority And Scope

This Work Contract corrects the gap between WC-102's layered runner construction and the operational
supply chain used by local PR preparation, pull-request CI and post-merge CI. The Founder authorized
WC-104 implementation in the 2026-09-20 continuous Platform IT Expert session. Image publication,
registry mutation, branch-protection changes, cloud mutation, deployment, approval and merge retain
their separate authority boundaries.

In scope:

- immutable Python, .NET, TypeScript and full validation-runner supply;
- dependency-layer identity, BuildKit cache import/export and package-cache boundaries;
- one producer and digest-only consumers across local preparation, PR CI and `main` CI;
- catalog-owned command and runner resolution;
- exact-input precheck-evidence reuse;
- build-count, cache-hit, invalidation and hosted timing evidence;
- early output-path validation, rollback and fail-closed behavior.

Out of scope:

- reducing required tests, coverage, security, CCT, review or release gates;
- activating selective PR enforcement before its separate Shadow gate and Founder approval;
- persistent test containers, retained databases/browser state or `docker cp` mutation;
- application behavior, service APIs, data schemas or production topology;
- treating cache hits, mutable tags or local evidence as authority.

## 2. Required End State

```text
Dependency and toolchain inputs
              |
     canonical runner identity
              |
 build once on verified cache miss
              |
 GHCR immutable digest + provenance
              |
  +-----------+-------------+
  |           |             |
local      pull-request    main/release
prepare       CI               CI
  |           |             |
  +---- disposable execution--+
              |
 exact input-bound test evidence
```

The same runner identity must resolve to the same immutable OCI digest in every lifecycle. Source,
test and fixture changes invalidate validation evidence but do not change or rebuild the runner.
Dependency or toolchain changes invalidate the runner identity and trigger exactly one replacement
build. All test processes and correctness state remain disposable.

## 3. Defect Closure Matrix

Each row is independently mandatory. A passing aggregate suite, image ID calculation, Dockerfile
inspection, local warm build or successful unrelated gate cannot substitute for its passing condition.

| Defect | What Exists Today | Why Layering Fails | Required Fix | Expected Outcome | Explicit Passing Condition |
|---|---|---|---|---|---|
| D01 - Layers are local-only | Runner Dockerfiles separate dependencies from source | Hosted jobs use isolated Docker daemons, so layers disappear between jobs and runs | Add scoped Buildx `cache-from`/`cache-to` using GitHub Actions cache for every validation runner | Dependency layers survive across hosted jobs and runs | Two clean hosted jobs for one unchanged identity report verified remote cache import; the second rebuilds zero dependency steps and executes its selected tests |
| D02 - Same layers are rebuilt in parallel jobs | Each consumer invokes `docker compose build` | Job-local daemons cannot share an image built by another job | Add one runner-supply producer per missing identity; publish to GHCR by immutable digest; consumers pull, verify and run that digest | One build replaces two-to-five duplicate builds | Workflow evidence reports exactly zero builds for a registry hit or one successful build for a miss, and every consumer records the producer digest; a second producer fails the gate |
| D03 - Identity is calculated but not resolved | `runner_identity()` computes a logical digest | No process queries trusted registry/cache state before building | Resolve canonical identity to an attested OCI digest, verify platform/provenance, then build only on a trusted miss | Source-only commits perform no runner build | Source-only fixture changes preserve identity and produce `build_count=0`; each dependency/base/build-argument mutation changes identity and produces exactly one build |
| D04 - Package installation lacks BuildKit caches | Dockerfiles use uncached pip/apt operations, ordinary pnpm install and restore layers | Any relevant layer invalidation redownloads complete dependency sets | Add locked BuildKit cache mounts for apt metadata/packages, pip downloads, pnpm store and NuGet packages with stack/platform/input namespaces | Dependency-image misses rebuild materially faster without retaining correctness state | Cold and warm cache-miss rebuilds execute package installation; warm evidence shows cache use, identical resolved dependency manifests and no reused test result, coverage, fixture or database state |
| D05 - Full runner is overused | Full runner contains Python, .NET, Node, Playwright and Docker tools | A single dependency change invalidates an unnecessarily broad environment and increases pull/build cost | Restrict the full runner to catalogued cross-stack/release gates; use lean stack runners everywhere else | Smaller invalidation and transfer radius | Catalog and workflow graph show no single-stack gate consuming the full runner; negative fixture fails when such a mapping is introduced |
| D06 - Build context is repository-wide | Most runners use `context: .` | Docker must enumerate and hash unrelated repository content | Introduce deterministic narrow runner contexts or generated context manifests containing only declared environment inputs | Faster context transfer with complete identity inputs | Context manifests equal the runner-identity input set; unrelated source edits leave context digest unchanged, while omission or mutation of a required dependency input fails closed |
| D07 - Named caches are machine-local | NuGet uses `wc102_nuget_cache`; other caches use container-local `/tmp` | Hosted job machines do not share named volumes | Move cross-job acceleration to GHA BuildKit cache and immutable runner layers; retain local named caches only as non-authoritative acceleration | Hosted CI gains the same dependency reuse as Codespaces | Hosted evidence proves a new job restores the expected namespaced cache; cache absence/corruption causes rebuild, never PASS reuse or skipped tests |
| D08 - Cache behavior is not executable | Tests inspect Dockerfile/workflow strings | Static strings cannot prove cache hits, build counts, identity lookup or consumer behavior | Add fake-registry unit tests, workflow-graph contract tests and hosted build telemetry assertions | Cache regressions become test failures | Tests fail for duplicate producers, mutable tags, missing provenance, source-caused rebuild, digest mismatch, cache-authorized PASS and consumers invoking build |
| D09 - Local, PR and merge supplies are disconnected | Each lifecycle builds independently | No registry contract joins the three stages | Resolve all three stages through the same canonical runner identity and GHCR digest contract | Build once and execute everywhere | One unchanged identity is observed in local, PR and `main` evidence with the same OCI digest; local fallback builds remain local-only until published by an authorized trusted producer |
| D10 - Catalog does not execute the work | Catalog and planner exist, while workflows and PR preparation retain hardcoded commands | Parallel command definitions drift and bypass the declared runner identity | Make the catalog generate the executable plan consumed by local and hosted orchestrators; prohibit duplicate runner/command definitions | One source controls selection and execution | Mutation tests prove a catalog command/runner change reaches every lifecycle; duplicate hardcoded commands or unmapped jobs fail repository policy |
| D11 - Evidence reuse is manual | `reuse_enabled` is reported and `--precheck-evidence-file` is optional | Default invocation never discovers valid evidence and repeats expensive qualification | Add deterministic lookup by base/head, changed-file, graph, configuration, runner and environment digests | Repeated preparation of an unchanged candidate avoids rerunning valid gates | First invocation executes gates; second invocation automatically reuses exact evidence with `executed_count=0`; changing any bound input reruns only invalidated gates |
| D12 - Output failure occurs after costly work | Preflight checks only the parent directory | A non-writable or non-replaceable body file fails after qualification | Probe final body/evidence creation and atomic replacement before any costly node starts | Configuration failures return immediately | Read-only file, ownership mismatch, missing mount and failed atomic-replace fixtures execute zero precheck nodes and return one bounded configuration failure |
| D13 - Completion evidence did not test hosted reuse | Local single cold/warm samples and static string assertions supported inherited PASS rows | They cannot establish cross-job reuse, build counts or hosted behavior | Require multi-sample hosted PR and `main` evidence tied to exact workflow, runner and candidate identities | Completion reflects actual end-to-end operation | Every requirement has explicit row status and direct evidence; hosted samples report counts, cache source, durations and consumers; no default result can convert an unevidenced row to PASS |
| D14 - Deterministic authority failures run after costly gates | PR preparation validates output writability early but validates C-059 commit/body traceability and C-065 author review only after selected prechecks finish | Invalid metadata can consume minutes of Business Platform or release qualification before returning a result known from repository text | Add a static-first phase that renders the candidate-bound author section in memory and validates C-059, C-065, changed ledgers, catalog policy, Compose configuration and output paths before constructing or starting costly nodes | Deterministic authority and configuration defects fail in seconds with zero costly processes | Invalid commit metadata, PR body, author review, ledger, catalog or Compose fixtures each report the exact violation and a node spy proves `executed_count=0`; a valid fixture reaches gate planning |
| D15 - Full authoritative inventory is conflated with local costly prechecks | Any global trigger, unknown path or owner conflict sets `force_full`, and `force_full` selects every configured precheck | Governance, review, evidence or narrowly scoped control changes unnecessarily run Business Platform and release qualification even when those gates have no affected input | Separate authoritative PR/main/release inventory selection from local precheck applicability; select costly prechecks only through explicit component, gate or declared-input ownership while retaining always-on cheap security checks | Local preparation executes the smallest dependency-complete slice without reducing hosted authority | A path-impact matrix proves evidence/review-only changes run no costly precheck, Business Platform changes select its gate and release qualification, release-owned changes select release qualification, and every full hosted inventory remains unchanged |
| D16 - Whole-candidate identity prevents safe per-gate carry-forward | Each node identity includes the full head SHA and branch-wide changed-file digest | Any checkpoint or evidence-only commit invalidates every prior gate even when no command, runner, environment or declared gate input changed | Replace whole-diff invalidation with a versioned per-gate input digest and create an exact-new-head carry-forward record that binds source evidence, intervening commit range, changed-path digest and non-impact proof | A new head reuses only unaffected PASS evidence while retaining exact-candidate provenance | A first candidate executes selected gates; an evidence-only successor executes zero unaffected costly nodes and emits current-head carry-forward evidence; mutation of any declared gate input, runner, command, environment, policy or source artifact reruns only affected nodes |

## 4. Architectural Contracts

### 4.1 Canonical Runner Identity

Each runner identity includes the exact Dockerfile, recursively resolved base-image digest, declared
system packages, dependency manifests and lockfiles, build arguments, target architecture/platform,
context manifest and runner-schema version. It excludes application source, tests, fixtures,
evidence and timestamps. Identity serialization is canonical and versioned.

A mutable tag is never an identity. The trusted mapping is:

```text
runner identity -> GHCR repository -> immutable OCI manifest digest -> verified provenance
```

A digest with absent, invalid or mismatched provenance is a cache miss. It is never silently accepted.
Concurrent misses for one identity use one bounded producer lock; losers wait for and verify the
published digest rather than building duplicates.

### 4.2 Layer And Cache Boundaries

| Layer/state | Identity inputs | Reuse rule | Prohibited use |
|---|---|---|---|
| Base and system layer | Base digest, OS packages, platform | BuildKit/GHA and immutable OCI reuse | Mutable base tag treated as proof |
| Language dependency layer | Exact manifests, lockfiles, installer/tool versions | Locked BuildKit package caches and immutable runner layer | Network resolution changing locked output silently |
| Runner tooling layer | Catalogued test/security tools and versions | Immutable runner digest | Application source baked into runner identity |
| Application source | Exact candidate/evidence identity | Read-only bind or exact checkout at execution | Triggering runner rebuild when environment inputs are unchanged |
| Compiler/package downloads | Namespaced runner identity | Acceleration only | Authorizing PASS or crossing incompatible identities |
| Tests, coverage, DB, queues, browser state | Exact evidence identity | Disposable execution; immutable evidence only after completion | Correctness cache or persistent-container reuse |

Cache exporters must use bounded scopes per runner identity and platform. Cache import failure,
eviction or corruption degrades to one clean rebuild. It must not skip commands or alter evidence
semantics.

### 4.3 Producer And Consumer Contract

The runner-supply stage executes before consumers and emits one signed manifest containing runner ID,
canonical identity, OCI digest, platform, source inputs, provenance reference, cache outcome and
producer run. It publishes only on an authorized trusted branch/event. Pull-request jobs may build
and inspect an untrusted candidate but cannot overwrite the trusted mapping.

Every consumer:

1. reads the manifest produced or resolved for its lifecycle;
2. pulls the immutable digest;
3. verifies identity, platform and provenance;
4. mounts exact source read-only and creates isolated writable state;
5. executes the catalog command without `docker compose build`;
6. records the consumed digest in result evidence.

No consumer may fall back to a mutable tag or silently build. A missing trusted digest invokes the
single producer path or fails with a bounded supply error according to event authority.

### 4.4 Lifecycle Semantics

| Lifecycle | Runner source | Evidence authority |
|---|---|---|
| Focused local edit | Trusted digest when available; one explicit local-only build on verified miss | Diagnostic only |
| Local PR preparation | Trusted digest or one exact local fallback; no registry publication | Commit-bound author evidence only, never hosted authority |
| Pull-request CI | Trusted existing digest or one untrusted candidate producer; exact consumers | Required PR gate evidence |
| `main`/release CI | Trusted published and attested digest; authorized publication on identity miss | Authoritative release evidence |

Production service images remain candidate-specific. PR and merge may legitimately build distinct
candidate images because their source SHAs differ; this contract removes duplicate validation-runner
builds, not required candidate-image construction or attestation.

### 4.5 Catalog Authority

The validation catalog is the only source for path ownership, gate selection, runner identity,
command, resources, retry policy and artifacts. Workflow YAML may bootstrap the catalog executor and
express GitHub permissions, but may not duplicate test commands or runner mappings. Local preparation,
PR CI and `main`/release CI consume the same generated execution plan.

Shadow selection remains non-authoritative until its separate activation gate. Full required gates
continue to execute, but they execute through the shared runner supply and catalog plan.

### 4.6 Evidence Reuse

Executed evidence uses the complete trusted tuple:

```text
execution base SHA + execution head SHA + per-gate declared-input digest + catalog version
+ gate implementation + command ID + runner OCI digest + declared environment inputs
+ evidence schema
```

Only immutable successful evidence from an accepted trust source may be reused. Failed, missing,
partial, stale, malformed, differently scoped or environment-incompatible evidence reruns the gate.
Reuse is per gate, so one invalid node does not discard valid independent evidence. Reuse across a
later head requires a separate carry-forward record bound to the later base/head, source evidence
digest, intervening commit range, intervening changed-path digest, selector version and proof that no
intervening path intersects the gate's declared inputs. The carry-forward record is current-head
evidence that a prior execution remains applicable; it must not claim that the gate executed at the
later head. Raw ancestor evidence never directly authorizes the later candidate.

## 5. Stories And Acceptance

| Story | Outcome | Defects | Required direct evidence |
|---|---|---|---|
| WC104-S01 | A source-only edit runs tests without rebuilding runners | D01-D03, D06-D07 | Hosted source-only fixture, zero-build telemetry and unchanged OCI digests |
| WC104-S02 | A dependency edit builds each affected runner exactly once | D02-D04 | Concurrent miss fixture, producer lock and one published digest |
| WC104-S03 | Every lifecycle consumes the same verified runner supply | D03, D07, D09 | Local/PR/main manifest comparison and digest verification |
| WC104-S04 | Single-stack checks avoid the full runner | D05 | Catalog topology and negative mapping fixture |
| WC104-S05 | One catalog controls actual commands everywhere | D10 | Generated-plan execution and mutation propagation test |
| WC104-S06 | Exact successful evidence is reused without skipping invalidated work | D11 | Two-run reuse plus per-input invalidation matrix |
| WC104-S07 | Bad output configuration fails before costly work | D12 | Zero-node output-path failure fixtures |
| WC104-S08 | Hosted measurements prove rather than infer optimization | D08, D13 | Multi-run PR/main evidence with build/cache/pull/execute timings |
| WC104-S09 | Static authority defects stop before Docker compilation or service tests | D14 | Invalid C-059/C-065/ledger/catalog/Compose fixtures with zero-node process spy |
| WC104-S10 | Local preparation runs only the dependency-complete affected slice | D15 | Path-impact matrix for evidence-only, component, release-owned and hosted-full cases |
| WC104-S11 | Unaffected gate evidence follows a later exact head without rerunning | D16 | Two-head carry-forward and declared-input invalidation matrix |

## 6. Requirement-To-Evidence Matrix

| Requirement | Defect/story | Required executable evidence | Passing condition |
|---|---|---|---|
| WC104-R001 | D01 / S01 | Hosted two-job GHA cache test for all four runners | Second job imports verified layers and rebuilds zero unchanged dependency steps |
| WC104-R002 | D02 / S02 | Workflow graph and concurrent producer test | Zero builds on hit; exactly one build and publish on miss; duplicate producer rejected |
| WC104-R003 | D03 / S01-S03 | Registry resolver unit/integration tests | Canonical identity resolves only to matching immutable digest and provenance |
| WC104-R004 | D04 / S02 | Cold/warm package-layer rebuilds | Locked apt/pip/pnpm/NuGet caches accelerate without changing resolved dependencies or skipping tests |
| WC104-R005 | D05 / S04 | Catalog runner-assignment test | Full runner appears only on approved cross-stack/release gates |
| WC104-R006 | D06 / S01 | Context-manifest mutation matrix | Unrelated source leaves context/runner identity unchanged; every required environment input invalidates it |
| WC104-R007 | D07 / S01-S03 | Fresh hosted-job cache restoration test | Namespaced remote cache restores across machines; corrupt/missing cache rebuilds safely |
| WC104-R008 | D08 / S08 | Negative workflow/cache regression suite | Duplicate builds, mutable tags, digest mismatch, unverified provenance and cache-authorized PASS all fail |
| WC104-R009 | D09 / S03 | Local/PR/main runner-manifest comparison | All stages consume one OCI digest for one unchanged runner identity |
| WC104-R010 | D10 / S05 | Catalog-to-execution mutation test | Every lifecycle executes the changed catalog command; duplicate command sources are rejected |
| WC104-R011 | D11 / S06 | Exact-tuple reuse and invalidation tests | Identical second run executes zero nodes; each authority input invalidates only affected evidence |
| WC104-R012 | D12 / S07 | Output/mount permission failure injection | Invalid output configuration starts zero costly nodes and returns bounded configuration evidence |
| WC104-R013 | D13 / S08 | Hosted measurement schema and sample validation | PR and main samples contain producer/consumer counts, cache source, durations and exact identities |
| WC104-R014 | Cross-cutting | Isolation/security regression suite | Non-root, read-only source, bounded resources/socket, disposable state and secret redaction remain passing |
| WC104-R015 | Cross-cutting | Full PR/main/release gate-equivalence test | No required gate, threshold or evidence class is reduced; Shadow activation remains disabled |
| WC104-R016 | All | Complete ledger, rollback rehearsal and exact-head author review | Every row has direct PASS evidence at one candidate; rollback restores full clean no-reuse qualification |
| WC104-R017 | D14 / S09 | Static-first failure-order and zero-node tests | Every deterministic authority/configuration failure returns before costly node construction or execution |
| WC104-R018 | D15 / S10 | Local-precheck path-impact and hosted-equivalence matrix | Local costly prechecks contain only explicitly affected dependency-complete gates while hosted full inventory is unchanged |
| WC104-R019 | D16 / S11 | Exact-head carry-forward and hostile invalidation tests | Only unaffected PASS evidence is carried forward through a current-head proof; every declared-input mutation reruns the affected gate |

## 7. Required Hosted Measurements

Measurements must use at least three independent hosted samples for each affected runner and report
median and range without extrapolation.

| Metric | Mandatory result |
|---|---|
| Source-only runner builds | `0` for every unchanged runner identity |
| Cache-miss runner builds | Exactly `1` per affected identity per workflow run |
| Duplicate producers | `0` |
| Consumer-side `docker compose build` | `0` |
| Consumer digest agreement | `100%` for the selected identity |
| Warm dependency-layer rebuild | Faster than cold median and reports verified cache source |
| Focused startup | At most 10 seconds before selected command begins |
| Focused representative validation | At most 60 seconds where WC-102 already established that target |
| Required test execution | `100%`; cache reuse never suppresses a selected command |
| Precheck exact-evidence second run | `executed_count=0`, all reused entries identify trusted source |
| Changed-input invalidation | `100%` of affected identities/evidence rerun; unaffected evidence remains reusable |

No completion claim may use a Codespace-only cache hit as proof of hosted reuse.

## 8. Delivery Sequence

| Milestone | Scope | Exit condition |
|---|---|---|
| WC104-00 | Freeze contract and baseline | Current local/PR/main build counts and timings recorded without inferred savings |
| WC104-01 | Runner identity and narrow contexts | Canonical context/identity mutation matrix passes |
| WC104-02 | BuildKit layers and cache scopes | All stack package caches pass cold/warm and corruption tests |
| WC104-03 | GHCR runner supply | One producer publishes/verifies immutable runner manifests; consumers never build |
| WC104-04 | Catalog execution convergence | Local, PR and main execute generated catalog plans with no duplicate command source |
| WC104-05 | Automatic evidence reuse and early preflight | Exact tuple reuses per-node evidence; invalid output starts zero costly nodes |
| WC104-05A | Static-first scoped preparation | Deterministic checks start zero costly nodes; local prechecks are dependency-complete and unaffected evidence carries forward safely |
| WC104-06 | Hosted qualification | Three-sample PR/main measurements and all negative fixtures pass at one exact candidate |
| WC104-07 | Author review and Founder handoff | Complete explicit ledger and no unresolved defect; PR remains unmerged for Founder decision |

Each implementation milestone requires explicit current-session Founder authorization. Image
publication and hosted workflow execution also require their normal repository/environment authority.

## 9. Rollback And Failure Policy

Rollback disables registry/evidence reuse and restores full clean serial qualification with local
runner builds. It never accepts a mutable tag, stale digest or prior PASS. Trigger rollback for a
missed failing gate, wrong-platform image, provenance mismatch, duplicate producer, catalog/workflow
disagreement, cross-run state contamination, cache-dependent outcome, unexplained build-count drift
or increased infrastructure failure rate.

Existing immutable evidence remains historical and is not reinterpreted. Failed publication leaves
the previous trusted identity mapping unchanged. Partially published manifests are unusable.

## 10. Definition Of Done

WC-104 is complete only when:

1. WC104-R001 through WC104-R019 each independently report `PASS` with direct evidence at one exact implementation candidate.
2. D01 through D16 each satisfy the explicit passing condition in Section 3; no aggregate count substitutes for a row.
3. Every validation runner has one canonical identity, narrow context, layered cache policy, immutable GHCR digest and verified provenance.
4. Source-only changes produce zero runner builds locally and in hosted PR/main fixtures.
5. Each cache miss produces exactly one runner build per identity and all consumers use its digest.
6. Local preparation, PR CI and `main`/release CI execute commands generated from the same catalog.
7. Exact evidence reuse executes zero nodes only for a complete matching trust tuple or a valid current-head carry-forward proof; every affected or unverifiable input fails closed or reruns.
8. Full authoritative gate coverage and thresholds remain unchanged; selective enforcement remains separately gated.
9. Hosted measurements meet Section 7 with at least three samples per affected runner.
10. Author review resolves every correctness, security, operability, rollback, evidence and requirement-coverage finding before Founder handoff.

A layered Dockerfile, local image ID, cache-hit log, static workflow string, passing test count or
single warm measurement cannot establish completion.

## 11. Stops

Stop and return to Solution Architecture or the Founder if implementation would require reducing a
required gate, accepting mutable or unsigned runner identity, persisting correctness state, granting
broad root/socket access, publishing from an untrusted event, changing application behavior,
activating selective enforcement, mutating Production, self-approval or self-merge.

## 12. Solution Architect Author Review

| Review question | Result | Evidence in this contract |
|---|---|---|
| Is every stated defect represented? | PASS | D01-D16 include all Founder-listed defects and the catalog, evidence-reuse, output-preflight, scoped-precheck and completion-evidence gaps found during review |
| Does each defect state today's behavior? | PASS | Section 3 records the existing runner, cache, context, orchestration and evidence behavior independently |
| Does each defect explain why layering fails? | PASS | Every row identifies the broken cache, identity, distribution, authority or measurement boundary |
| Is the required fix bounded and implementable? | PASS | Sections 4 and 8 define existing-technology contracts and ordered milestones without selecting a new platform |
| Is the expected outcome observable? | PASS | Every defect has a measurable outcome and explicit executable passing condition |
| Can a superficial implementation pass? | PASS - PREVENTED | Negative tests reject duplicate builds, mutable tags, missing provenance, source-caused rebuilds, hardcoded commands and cache-authorized PASS |
| Are local, PR and merge paths connected? | PASS | D09, R009 and Section 4.4 require one identity/digest across all three lifecycles |
| Are Docker layers end-to-end? | PASS | D01-D07 cover layer construction, remote distribution, package caches, context boundaries and hosted restoration |
| Is evidence reuse safe? | PASS | D11/D16 and R011/R019 bind reuse to per-gate inputs and require exact-head carry-forward proof with fail-closed invalidation |
| Are constitutional gates preserved? | PASS | R014-R015 retain C-080 isolation, security controls, full gate authority and separate selective activation |
| Is completion atomized? | PASS | Nineteen explicit requirements and sixteen defect passing conditions prohibit aggregate substitution |

**Disposition:** PASS AT SPEC - READY FOR FOUNDER REVIEW. IMPLEMENTATION REMAINS UNAUTHORIZED.

## 13. Authorized Follow-Up Defects

The Founder authorized these post-merge corrections in the 2026-09-20 continuous Platform IT Expert
session. They extend R019 and the Platform IT Expert execution standard without reducing hosted gate
authority or reinterpreting prior WC-104 evidence.

| Defect | Current defect | Required fix | Outcome / benefit | Passing condition |
|---|---|---|---|---|
| D17 - Carry-forward provenance is implicit | Cross-commit reuse is represented by `trust_source` and nested metadata but has no explicit provenance classification in the fresh exact-head manifest | Write `provenance: carry-forward` for every cross-commit reused node and distinguish exact-candidate reuse | Auditors and automation immediately distinguish executed, exact-reused and carry-forward evidence | Focused manifest tests assert explicit provenance for exact and cross-commit reuse |
| D18 - Historical evidence selection follows path order | The first valid lexically supplied artifact wins even when a nearer valid ancestor exists | Prove ancestry and numeric commit distance, rank candidates nearest-first with deterministic tie-breaking, reject unprovable candidates and fall through when a nearer candidate is invalid | Maximizes safe reuse, avoids stale evidence and unnecessary Docker execution, and fails closed on unverifiable history | Tests prove nearest selection, invalid-nearest fallback, non-ancestor rejection, missing-distance rejection and affected-input rerun |
| D19 - The Platform IT Expert standard permits wasteful validation cadence | The execution standard does not explicitly prohibit repeated full Docker qualification or runner rebuilds during ordinary implementation | Require static-first validation, catalog changed-path selection, focused gates, valid evidence reuse and one final hosted qualification; reserve full local qualification for explicit necessity | Reduces image rebuilds, CPU use, disk pressure and feedback time without weakening final authority | The agent specification contains the normative execution rule and policy tests preserve static-before-costly ordering |
