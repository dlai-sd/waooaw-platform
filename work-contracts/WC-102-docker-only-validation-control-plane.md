# WC-102 - Docker-Only Validation Control Plane

## Record Control

| Field | Value |
|---|---|
| Office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-19 continuous working conversation |
| Status | ACCEPTED BY FOUNDER - IMPLEMENTATION AUTHORIZED 2026-09-19 |
| Architecture authority | WC-101, Founder accepted 2026-09-19 |
| Governing decision | ADR-050, Founder accepted 2026-09-19 |
| Governing strategy | `architecture/reference/docker-only-validation-strategy.md` |
| Existing decisions retained | ADR-012, ADR-013, ADR-045 |
| Implementing office | Platform IT Expert in INST-010 Runtime Implementation Professional Decision Space, only after current-session Founder authorization |
| Delivery shape | One bounded implementation with staged activation; no partial completion claim |
| Supersedes | WC-100 draft for this delivery; WC-100 supplies no implementation authority |
| Constitutional basis | C-059, C-065, C-071, C-076, C-077, C-080 and C-086 |

## 1. Authority And Scope

This contract decomposes the accepted Docker-only validation architecture into implementation
responsibilities, interfaces, evidence and rollout gates. It authorizes no code, workflow execution,
image publication, registry mutation, cloud mutation, branch-protection change, PR approval or merge.

Before any runnable implementation begins, the Founder must explicitly authorize WC-102
implementation for the current session. Acceptance of WC-101 or ADR-050 is architectural approval,
not implementation authority.

In scope:

- Docker test-runner definitions and Compose profiles;
- CI and local qualification orchestration;
- one validation catalog and impact selector;
- runner, candidate and evidence identity handling;
- structured failure evidence and gate aggregation;
- C-080 policy enforcement;
- focused and qualification execution modes;
- tests, rollout controls, measurements and rollback.

Out of scope:

- application business behavior, service APIs and database schemas;
- customer, constitutional or operational data models;
- production deployment topology;
- quality or coverage threshold reduction;
- a new CI vendor, test framework or deployed service;
- session compaction, model selection and unrelated flaky-test repair.

## 2. Required Outcome

Deliver one validation control plane in which an AI agent can run the smallest safe Docker check
after an edit, receive the first causal failure in a bounded machine-readable record, repair the
defect, and qualify one frozen candidate without rebuilding unchanged runner environments or silently
skipping required gates.

The system has two evidence classes:

| Mode | Purpose | Authority |
|---|---|---|
| Focused agent loop | Fast feedback against current workspace changes | Local diagnostic evidence only |
| Candidate qualification | Clean validation of one exact 40-character commit using pinned runner identities | PR/release evidence when produced by the trusted CI boundary |

Both modes must resolve to the same catalogued test definitions, commands and thresholds. Local or
cached success never substitutes for required candidate qualification.

## 3. Confirmed Baseline Defects

Implementation must first capture reproducible evidence for these current conditions:

1. Compose test runners are rebuilt independently in multiple CI jobs.
2. Business Platform unit tests still use the deprecated multi-stack runner.
3. The .NET Compose runner redirects NuGet packages away from the path restored into its image.
4. The TypeScript runner lacks the workspace source mount used for a fast edit/test loop.
5. Integration workflows invoke host test commands and test-language tooling despite C-080.
6. Some contract checks are advisory and target services not started by their job.
7. Path ownership, reverse dependencies, commands and evidence requirements have no single
   machine-readable authority.
8. Test jobs do not consistently emit one bounded, common first-cause result envelope.

Post-merge baseline correction: PR #454 added `validation/engineering-validation.yaml` as one
machine-readable Shadow selector before WC-102 implementation began. Defect 7 is therefore narrowed
to the missing WC-102 catalog schema and required gate/runner/command/resource/evidence fields. The
merged selector is implementation baseline only; WC-100 supplies no authority for this delivery.

WC102-00 measurements are retained in `validation/evidence/wc102-baseline.json` with raw timing
records beside it. They describe this Codespace and cache state only and make no savings claim.

If baseline execution disproves an item, record the correction and amend only the affected
requirement. Do not preserve an inaccurate assumption for convenience.

## 4. Non-Negotiable Contracts

1. Every test and test-language tool executes in a repository-defined Docker container.
2. Existing coverage, CCT, security, contract, generated-drift, author-review and merge gates retain
   their current authority.
3. Runner images remain separated by runtime stack under ADR-045.
4. A runner environment identity excludes application source, tests and fixtures. Code-only edits do
   not rebuild an unchanged runner.
5. Evidence identity includes exact source, tests, fixtures, specifications, generated contracts,
   catalog version, gate implementation, command identity, runner digest and declared environment.
6. Candidate service-image identity remains separate from runner and evidence identity.
7. Mutable tags, cache hits, local assertions and partial hashes are never evidence authority.
8. Focused and qualification containers are disposable. Persistent test processes, `docker cp`
   mutation and retained database/browser state cannot establish PASS.
9. Package downloads and compiler outputs may be cached by namespace. Coverage, verdicts, fixtures,
   databases, browser sessions and queue state are not correctness caches.
10. Unknown ownership, dependency cycles, catalog failure or evidence disagreement selects the full
    current applicable gate set.
11. Test runners execute as non-root. Any unavoidable exception must be narrowly catalogued and
    executable evidence must prove why it is required.
12. Docker socket access is limited to catalogued Testcontainers runners and carries explicit CPU,
    memory, timeout and namespace controls.
13. Assertion, compile, coverage and security failures are not automatically retried. Only named
    transient infrastructure classes receive a bounded retry.
14. Complete `main` and release validation remain authoritative throughout this contract.

## 5. Component And Interface Responsibilities

| Component | Required responsibility | Prohibited behavior |
|---|---|---|
| Validation catalog | Own paths, direct gates, reverse dependencies, runner/command IDs, resources, retries and evidence formats | Duplicate ownership rules hidden in shell, Python or workflow YAML |
| Impact selector | Diff exact merge base to head, evaluate old/new rename paths, compute transitive closure and explain every selection | Treat unknown paths as documentation-only or safe |
| Runner image supply | Build per-stack environment images from dependency inputs and publish/inspect immutable digests | Rebuild for source-only changes or use mutable tags as identity |
| Focused orchestrator | Mount current workspace, use disposable containers and run selected catalog commands | Produce trusted PR/release PASS or retain correctness state |
| Qualification orchestrator | Freeze exact commit, isolate state, consume pinned runner/candidate digests and aggregate required evidence | Rebuild silently or substitute another digest |
| Result adapter | Preserve native JUnit/TRX/JSON/SARIF/coverage and emit one common sanitized envelope | Hide raw evidence or include secrets/customer data |
| Gate aggregator | Reject failed, missing, cancelled, stale, malformed or unexplained required evidence | Infer PASS from aggregate counts or absent jobs |
| Docker policy gate | Detect host test/tool commands, virtual environments, test package installation and unapproved root execution | Rely on comments or reviewer memory |

No component above is a deployed platform service. These responsibilities live in repository
manifests, scripts, Docker definitions and GitHub Actions.

## 6. Validation Catalog Contract

Create one versioned machine-readable catalog. Its schema must require:

| Field | Meaning |
|---|---|
| `component_id` | Stable owning component |
| `paths` | Owned source, tests, fixtures and specifications |
| `reverse_dependencies` | Components affected by this component's change |
| `gate_id` | Stable validation obligation |
| `runner_id` | Stack runner environment definition |
| `command_id` | Stable command template with no secret-bearing values |
| `evidence_class` | Static, unit, coverage, integration, contract, browser, security, CCT or release |
| `resources` | CPU, memory, timeout, Docker socket and concurrency class |
| `retry_policy` | None or one named bounded transient-infrastructure policy |
| `artifacts` | Required native and common result outputs |
| `global_trigger` | Whether a change forces broad qualification |

The catalog is the sole applicability source for local preflight and CI after migration. The selector
must emit selected gates, dependency reasoning, global triggers, skipped gates and reasons. A skipped
required gate without validated `NOT_APPLICABLE` evidence fails the aggregate.

## 7. Identity And Reuse Contract

### 7.1 Runner Environment Identity

Derived from Dockerfile, base-image digest, system packages, dependency manifests, lockfiles, build
arguments, architecture and runtime platform. CI builds at most once per complete identity and makes
the immutable digest available to all consuming jobs.

### 7.2 Validation Evidence Identity

Derived from exact base/head SHAs, source, tests, fixtures, relevant specifications, generated
contracts, catalog and gate versions, runner digest, command ID and declared environment inputs. Any
change to those inputs invalidates the prior result without necessarily rebuilding the runner.

### 7.3 Candidate Image Identity

Derived from the complete production-image build inputs. Smoke, security and release checks consume
the exact candidate digest produced once for that identity.

Every evidence record names its identity type and complete cryptographic digest. Cache reuse is
reported as an acceleration fact, never as proof that a test passed.

## 8. Structured Result Contract

Every validation node retains its framework-native artifacts and emits one result document with:

| Field | Rule |
|---|---|
| `schema_version` | Required supported version |
| `base_sha`, `head_sha` | Full 40-character commits |
| `runner_digest` | Immutable OCI digest |
| `component`, `gate`, `command_id` | Values defined by the catalog |
| `started_at`, `duration_ms`, `exit_code` | Actual execution values |
| `result` | `PASS`, `FAIL`, `BLOCKED` or `NOT_APPLICABLE` |
| `failure_class` | `assertion`, `compile`, `coverage`, `security`, `infrastructure`, `configuration` or `none` |
| `first_cause` | Bounded sanitized causal message, not the final aggregate symptom |
| `raw_artifacts` | Paths to retained native evidence |
| `reuse` | Reused identity, trust source and invalidation reason when applicable |

The result adapter must redact secrets, tokens, authorization material, customer data and
conversation content. Missing or malformed result documents fail the required gate.

## 9. Ordered Delivery Plan

| Milestone | Scope | Exit condition |
|---|---|---|
| WC102-00 | Contract freeze and baseline | Founder accepts contract; baseline captures warm/cold duration, builds, test invocations and failure evidence for Web, .NET, Python, shared and global changes |
| WC102-01 | C-080 compliance repair | Host execution and virtual-environment paths removed; non-root defaults enforced; applicable contract jobs start required services and block on failure |
| WC102-02 | Runner supply and cache repair | Digest-addressed stack runners, correct NuGet/pnpm/pip caches and source mounts pass identity and invalidation tests |
| WC102-03 | Catalog, selector and dual-mode orchestration | Focused and qualification modes use the same catalog commands; unknown impact falls back to full validation |
| WC102-04 | Structured evidence and gate aggregation | Every required node emits validated native/common evidence; first causal failure is available from the original run |
| WC102-05 | Shadow impact selection | Current full PR CI remains authoritative while classifier decisions are compared across representative changes |
| WC102-06 | Integrated qualification | Full regression, coverage, CCT, security, concurrency, isolation, tamper and rollback checks pass at one exact head |
| WC102-07 | Founder handoff | One unmerged PR contains exact evidence, measurements, author review and no unresolved requirement |

Selective PR enforcement is not part of WC102 completion. It requires zero unresolved shadow false
negatives and separate Founder authorization. The implementation may deliver dormant enforcement
capability but may not activate it.

## 10. Requirement-To-Evidence Matrix

| ID | Requirement | Minimum executable evidence |
|---|---|---|
| WC102-R001 | All tests and test-language tooling execute in Docker | Static workflow/script policy fixtures including every prohibited host pattern |
| WC102-R002 | Existing quality, coverage, security, CCT and review authority is unchanged | Gate-equivalence tests and representative threshold failures |
| WC102-R003 | Python, .NET and TypeScript runners retain separate runtime boundaries | Compose/render and image-content assertions |
| WC102-R004 | Code-only changes rebuild no unchanged runner | Build-spy test changing source and tests independently |
| WC102-R005 | Runner, evidence and candidate identities remain distinct and complete | Per-input identity and invalidation matrix |
| WC102-R006 | Focused and qualification modes use the same catalogued commands and thresholds | Mode-resolution parity tests |
| WC102-R007 | Focused PASS never substitutes for trusted qualification | Trust-boundary negative tests |
| WC102-R008 | Test containers are disposable and stale state cannot pass | Repeated-run database, browser, filesystem and process contamination tests |
| WC102-R009 | Dependency/build caches accelerate without authorizing results | Cache-hit, corruption and identity-mismatch tests |
| WC102-R010 | Catalog is the sole owner of path, dependency, gate, command and evidence selection | Duplicate-source prohibition and schema tests |
| WC102-R011 | Direct owners and transitive reverse dependencies are selected from exact diffs | Representative component and shared-contract selector tests |
| WC102-R012 | Renames, deletions, cycles, unknown paths and selector errors fail closed | Negative/property selector tests |
| WC102-R013 | Every node emits valid native artifacts and the common result document | Schema and artifact-presence tests |
| WC102-R014 | Failure output reports the bounded first causal class without secret or customer data | Multi-failure, redaction and log-bounds tests |
| WC102-R015 | Deterministic failures are not retried and transient retries are bounded | Assertion and infrastructure failure-injection tests |
| WC102-R016 | Runners are non-root and resource/namespace limits are enforced | Container identity, CPU, memory, timeout and collision tests |
| WC102-R017 | Docker socket access exists only for catalogued Testcontainers runners | Compose/policy inspection and unauthorized-access negative test |
| WC102-R018 | Independent gates run concurrently without shared writable-state collision | Parallel/serial equivalence and collision tests |
| WC102-R019 | Business Platform uses the lean .NET runner with effective NuGet reuse | Runner-selection, restore-path and warm-run evidence |
| WC102-R020 | Web source edits execute without runner rebuild | Bind-mount and warm-run evidence |
| WC102-R021 | Integration and contract workflows start required services and block when applicable | Workflow integration tests with unavailable-service negative case |
| WC102-R022 | Shadow selector omits no gate that fails under full CI | Comparison ledger across all required change classes |
| WC102-R023 | `main` and release retain complete validation | Workflow topology and required-gate assertions |
| WC102-R024 | Rollback restores full clean qualification without accepting newer stale evidence | Rollback and schema-version incompatibility tests |
| WC102-R025 | Measured outcomes are reported without unsupported extrapolation | Baseline/candidate report with sample sizes, ranges and cache state |
| WC102-R026 | One exact candidate satisfies every requirement before handoff | Complete obligation ledger and exact-head author review |

Every row begins `PLANNED`. Aggregate test counts, screenshots or cache-hit reports cannot substitute
for the listed direct evidence.

## 11. Required Measurements

Measure cold and warm behavior for one Web-only, Business Platform, Python-service, shared-contract
and workflow/global change.

| Metric | Required result |
|---|---|
| Docker-only compliance | Zero host test or test-language-tool invocations |
| Required gate coverage | Equal to or stronger than current policy |
| Code-only runner rebuilds | Zero when environment identity is unchanged |
| Duplicate runner builds | At most one per environment identity per workflow run |
| Warm focused startup | Target 10 seconds or less before selected command begins |
| Warm focused unit validation | Target 60 seconds or less for a representative single-component change |
| Shadow false negatives | Zero unresolved before any activation request |
| Failure diagnosis | Common result document available from the original failed run |

Targets are not completion claims until measured. Full qualification may exceed five minutes; it
must run once per frozen candidate rather than after each repair edit.

## 12. Rollout And Rollback

1. Land compliance checks and schemas while current full CI remains authoritative.
2. Enable runner reuse and caches only after identity/invalidation tests pass.
3. Enable focused mode without granting it trusted evidence authority.
4. Run selector in Shadow mode beside unchanged full PR CI.
5. Request separate Founder approval before selective PR enforcement.

Rollback restores serial orchestration, no cross-job evidence reuse and full clean PR validation.
Immediate rollback triggers are a missed failing dependency, stale evidence acceptance, manifest
disagreement, cross-run contamination, nondeterministic selection, resource starvation or increased
infrastructure flakiness. Historical evidence is retained and never reinterpreted under another
schema version.

## 13. Definition Of Done

WC-102 is complete only when:

1. WC102-R001 through WC102-R026 each have direct PASS evidence at one exact implementation head.
2. All confirmed baseline defects are repaired or formally corrected with evidence.
3. Focused feedback is faster without becoming qualification authority.
4. Runner, evidence and candidate identities pass all invalidation and tamper tests.
5. Docker-only, non-root, resource, namespace and socket controls pass.
6. Current full PR CI remains authoritative during Shadow mode; full `main` and release gates remain.
7. Coverage and all constitutional/security gates remain equal to or stronger than baseline.
8. Baseline and candidate measurements are attached without unsupported savings claims.
9. Rollback and failure injection pass.
10. The Platform IT Expert performs author review and submits one unmerged PR for Founder review.

Passing a focused suite, producing a cache hit, or reducing elapsed time does not establish
completion.

## 14. Stop Conditions

Stop and return to Solution Architecture or the Founder if implementation requires:

- reducing or bypassing a required gate or threshold;
- trusting local results, mutable tags, partial hashes or caches as PASS authority;
- changing service behavior, API contracts, databases or production topology;
- adding a third-party orchestration platform or new technology decision;
- broad Docker socket or root access;
- activating selective PR validation before the Shadow gate and Founder approval;
- changing branch protection, author/approver separation or merge authority; or
- claiming completion with any unresolved, partial, deferred or substituted WC102 requirement.

## 15. Platform IT Expert Handoff

After explicit current-session implementation authorization, the implementer must read WC-101,
ADR-050, the Docker-only validation strategy and this contract before touching runnable files. The
implementation sequence is WC102-00 through WC102-07. Each first edit is followed by its smallest
mapped Docker check; final qualification runs once against a frozen candidate.

The implementer may choose internal script structure and schema serialization consistent with the
repository. It may not redefine identity boundaries, evidence authority, fail-closed selection,
Docker isolation, activation authority or completion meaning.

## 16. Solution Architect Author Review

This contract was reviewed against every section of WC-101, ADR-050 and the accepted Docker-only
validation strategy. It assigns every architecture control to a component and direct evidence row,
separates environment reuse from evidence trust, preserves existing gates, specifies failure and
rollback behavior, and leaves implementation choices inside the Runtime Professional decision space.

**Disposition:** READY FOR FOUNDER CONTRACT REVIEW. IMPLEMENTATION REMAINS UNAUTHORIZED UNTIL THE
FOUNDER EXPLICITLY AUTHORIZES WC-102 FOR A CURRENT PLATFORM IT EXPERT SESSION.
