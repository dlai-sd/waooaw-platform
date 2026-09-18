# WC-100 - Engineering Validation Efficiency

## Record Control

| Field | Value |
|---|---|
| Office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-18 continuous working conversation |
| Status | IMPLEMENTATION AUTHORIZED - Founder instruction in the 2026-09-18 continuous working conversation |
| Implementing office | Platform IT Expert operating in INST-010 Runtime Implementation Professional Decision Space, only after current-session Founder authorization |
| Delivery shape | Four ordered work components in one bounded pipeline-improvement delivery |
| Scope owners | PR preparation, GitHub Actions CI, Docker test runners, qualification scripts, Work Contract acceptance evidence |
| Governing decisions | ADR-012, ADR-013, C-023, C-059, C-065, C-071, C-076 and C-080 |
| Evidence source | Five recent qualifying Copilot sessions through 2026-09-18 and direct inspection of the current precheck, qualification and CI paths |
| Explicitly deferred | Session compaction and targeted peer review |

## 1. Authority And Scope

This Work Contract defines a safer and faster validation process without reducing the tests, coverage
thresholds, security controls, author review, Founder review or merge controls that currently produce
good engineering results. It changes validation scheduling, reuse and applicability decisions; it does
not weaken what must ultimately pass.

The Solution Architect may specify component responsibilities, evidence contracts, invalidation
rules, rollout controls and acceptance outcomes. This document does not authorize source changes,
workflow execution, Docker builds, cloud mutation, PR approval or merge. Before implementation, the
Founder must explicitly authorize WC-100 implementation for the current Platform IT Expert session.

The implementing agent must not interpret efficiency as permission to skip a required gate. A gate
may be avoided only when the approved change-impact classifier proves it is not applicable, or reused
only when immutable evidence proves that all of its inputs are unchanged. Ambiguity fails closed to
the current full validation behavior.

## 2. Problem Statement And Baseline

Five recent sessions that completed Work Component creation or implementation were analyzed:

| Session | Delivery observed | Process friction observed |
|---|---|---|
| `b27d9a4e-e8e3-4cd2-883b-f0cf3270bea0` | WC-099 implementation and PR #448 | Coverage evidence mismatch and post-implementation precheck repair |
| `dca21132-8896-4398-9443-1d6afbed1d9a` | WC-095 completion and WC-099 creation | Repeated full Business Platform gate; Hire/Trial acceptance evidence added late |
| `d1347cdb-e168-42c3-a99e-07c367f12d2e` | WC-095/WC-096 implementation and PRs #440-442 | Testcontainers/environment failure, long PostgreSQL execution and Demo-visible completeness gaps |
| `c1f208cb-3299-496e-8de4-418e4342e6ec` | WC-089 implementation and WC-095 design | Repeated build/precheck cycles, BuildKit corruption and CI workflow repairs |
| `fd6e1336-c3df-492c-ad0e-b472a63229d4` | Authentication, portal and sign-out repairs | Environment drift, repeated coverage work and late CodeQL feedback |

The sample contained 234 turns over approximately 88 elapsed hours and no session compaction. The
four WC-089-related sessions accumulated approximately 1.64 million stored user/context characters
and 949 file-read records. Session compaction is intentionally outside this contract, but these
figures establish that Docker runtime is not the only cost source.

Current validation also contains structural duplication:

1. `scripts/prepare_pr_body.py` runs gitleaks, applicable Business Platform tests and release
   qualification serially even though their results are independent.
2. Local qualification and PR CI can rebuild equivalent runners and rerun equivalent suites without
   a common evidence identity.
3. PR CI builds and scans the full release image inventory even when a change affects only a bounded
   service set.
4. Broad passing test counts have not always proved customer-visible completion because acceptance
   scenarios were added or inspected after implementation.

## 3. Required Outcome

Deliver one deterministic validation system in which:

1. independent prechecks execute concurrently within explicit resource limits;
2. each immutable Docker runner or candidate image is built once per input identity and reused by
   compatible tests and scans;
3. PR CI runs affected components and known reverse dependencies while failing closed when impact is
   unknown;
4. every normative Work Contract obligation is mapped to executable evidence before implementation;
5. a single machine-readable manifest explains what ran, what was reused, what was inapplicable and
   why; and
6. the existing complete validation remains the release and `main` safety net until measured evidence
   authorizes any later change.

Efficiency success is reduced wall time, Docker builds and duplicate test executions. It is not a
smaller evidence set or a lower coverage result.

## 4. Non-Negotiable Safety Principles

1. C-076 remains at least 90 percent line and 80 percent branch coverage wherever currently enforced.
2. C-080 remains absolute: tests and language tooling run through repository Docker test runners.
3. CCT, secrets, SAST, dependency, license, API/spec drift and author-review gates retain their
   current blocking or advisory meaning.
4. PR authors do not approve or merge their own work. Founder review and merge remain unchanged.
5. Failed, cancelled, stale, missing or malformed evidence is never reusable.
6. A changed source, test, dependency lockfile, Dockerfile, Compose definition, workflow, relevant
   specification, generated contract or gate implementation invalidates the affected evidence.
7. Unknown impact, dependency cycles, classifier errors and manifest disagreement select the current
   full applicable gate set.
8. Parallel execution must not share writable coverage paths, container names, networks, volumes,
   ports or mutable caches unless isolation and locking are proven.
9. Actual-cloud proof, local exact-image proof, CI proof, emulation/static proof and untested stages
   remain separately identified.
10. Existing qualification scripts remain the fallback throughout rollout.

## 5. WC100-01 - Earlier Acceptance Coverage

### 5.1 Ownership

The Solution Architect authors each requirement in observable and testable language. Before writing
implementation code, the Platform IT Expert converts every normative requirement into a
requirement-to-evidence ledger and challenges requirements that cannot be tested. The Solution
Architect resolves specification ambiguity; the implementer must not invent acceptance meaning.

### 5.2 Pre-Implementation Gate

For every normative clause in an implementation Work Contract, the ledger must contain:

| Field | Required meaning |
|---|---|
| `requirement_id` | Stable unique identifier |
| `source` | Exact Work Contract section or approved specification |
| `observable_outcome` | Externally observable behavior, state or invariant |
| `component_owner` | Component that owns the behavior |
| `evidence_class` | Unit, integration, contract, browser, security, performance, deployment or manual Founder acceptance |
| `test_path_or_plan` | Existing executable test or precise planned test and harness |
| `initial_state` | Existing-pass, expected-fail, new, blocked or Founder-reserved |
| `dependencies` | Required services, fixtures, identities, secrets or environment authority |
| `completion_rule` | Exact result that establishes PASS |
| `residual_risk` | What the evidence does not prove |

Implementation may begin only when every clause has a ledger row and no row is silently untestable.
The gate does not require all new tests to pass before code exists. It requires the evidence design to
exist before implementation and, where practical, a focused test to fail for the intended reason.

### 5.3 Implementation And Completion Rules

1. Tests and implementation are delivered together in each milestone.
2. Focused tests provide fast feedback while coding.
3. A milestone cannot be marked complete until its mapped evidence passes.
4. Aggregate counts, coverage percentages or screenshots do not substitute for a missing direct
   requirement assertion.
5. Partial, deferred, blocked, untested and Founder-reserved rows remain explicit and prevent a full
   DONE claim unless the contract contains the exact Founder-approved variance.
6. The final author review compares the complete normative contract against the final ledger and raw
   evidence, not only against the changed files.

### 5.4 Enforcement

Provide a deterministic ledger validator used by PR preparation and CI. It must reject duplicate or
missing requirement IDs, missing source/test/evidence references, invalid result vocabulary and DONE
claims containing unresolved rows. Work Contracts that contain no implementation scope may declare
the gate not applicable with a machine-readable reason.

### 5.5 Running Commentary Story Boundaries

While executing stories in any Work Component, the Platform IT Expert must declare the story start
in running chat commentary before story execution begins, naming the story identifier and intended
outcome. After completing or stopping that story, and before starting another story, it must declare
the story end in running chat commentary with a concise summary of the evidence produced and any
remaining blocker. A planning statement, task-list status change or final response does not
substitute for either boundary declaration.

## 6. WC100-02 - Bounded Parallel Prechecks

### 6.1 Execution Model

Replace the serial orchestration inside PR preparation with an explicit directed acyclic graph. After
base/head and changed-file resolution, independent nodes may execute concurrently:

```text
resolve exact base/head and applicable gates
                 |
       +---------+---------+
       |         |         |
    gitleaks   BP gate   release qualification
       |         |         |
       +---------+---------+
                 |
       aggregate immutable evidence
```

This diagram describes concurrency, not applicability. Only selected nodes run. The orchestrator
must retain each node's stdout, stderr, start/end time, exit code and failure classification in a
separate bounded artifact.

### 6.2 Resource And Failure Controls

1. Default maximum parallelism is two heavy Docker gates plus lightweight gitleaks; it must be
   configurable without source edits.
2. A resource preflight checks Docker availability, free disk, memory and conflicting repository
   qualification processes. Insufficient capacity falls back to serial execution.
3. Each node receives isolated result, coverage, temporary, Compose project and container/network
   namespaces.
4. One gate failure does not hide other already-running gate results. New dependent work is not
   started after a prerequisite failure.
5. Infrastructure failures are distinguished from assertion, coverage, security and metadata
   failures. Automatic retries are bounded to known transient infrastructure classes and never mask
   a deterministic test failure.
6. The aggregate command returns nonzero when any required node fails, is cancelled or lacks evidence.
7. Output shown to an agent names the first causal failure and links the bounded full artifact instead
   of injecting complete logs into chat context.

### 6.3 Enforcement

`prepare_pr_body.py` remains the mandatory entry point. Agents do not manually reproduce its gate
selection. The generated precheck manifest must bind the exact base SHA, head SHA, changed-file digest,
gate graph version and every node result. CI validates the schema and bindings.

## 7. WC100-03 - Build Once, Test Many

### 7.1 Immutable Build Identity

Every reusable test runner and candidate image receives an identity derived from all behaviorally
relevant inputs:

- source file digest for the owning component;
- tests and fixtures digest;
- Dockerfile and build-context digest;
- dependency and lockfile digest;
- Compose/profile and build-argument digest;
- generated API/proto contract digest where applicable;
- architecture/specification version or digest; and
- builder/runtime platform and gate implementation version.

The identity must use complete cryptographic digests in evidence. Short display forms are never used
for equality or authorization.

### 7.2 Build And Reuse Contract

1. Build each runner image once per immutable identity.
2. Execute independent test groups against that exact runner image ID or registry digest.
3. Build each affected candidate service image once, then smoke-test and scan that exact image.
4. Do not rebuild between test and scan when the source identity is unchanged.
5. Store reusable CI images in the approved registry/cache with bounded retention and provenance.
6. Local cache hits are acceleration only. Reuse evidence requires image inspection and complete
   input-identity equality.
7. Mutable tags such as `latest` are not evidence identities.
8. Dependency or base-image freshness policies may force rebuild even when repository inputs are
   unchanged; the manifest records that invalidation reason.

### 7.3 Evidence Manifest

Each build records:

- repository, base SHA and head SHA;
- complete input identity and enumerated input groups;
- image ID and, when published, registry digest;
- builder, platform, Docker/BuildKit version and timestamps;
- SBOM/provenance references when required;
- consuming tests/scans and their result artifact references; and
- cache hit/miss and invalidation reason.

CI may reuse a result only when the manifest schema, trust source, complete identity and required
artifacts validate. Developer-local PASS evidence remains useful for PR preparation but does not
replace a required trusted CI result unless a later Founder-approved trust policy explicitly permits
that change.

### 7.4 Enforcement

Qualification scripts and CI jobs consume an explicit image digest supplied by the build stage. A
test job that silently invokes a rebuild, substitutes another tag or cannot report the consumed image
fails. A deterministic test verifies that changing each input class invalidates reuse.

### 7.5 Docker Layer Mutation Efficiency

The full multi-stack test runner must preserve its embedded repository source and executable top-level
shell scripts while avoiding a post-copy metadata mutation that copies up the complete source layer.
The remediation changes only the Docker runner definition and its direct contract evidence; it must
not change application code, test selection, coverage thresholds, gate outcomes or authority. Evidence
must compare the same runner build stages before and after the change and prove both standalone-image
and Compose-mounted execution remain successful.

## 8. WC100-04 - Change-Aware CI

### 8.1 Dependency Manifest

Create one versioned machine-readable manifest that maps repository paths to:

- owning component;
- direct build/test/security/spec gates;
- reverse-dependent components;
- generated artifacts and contracts;
- shared/global paths that force broad qualification; and
- release-only full-inventory gates.

The manifest is the sole selection source for local PR preparation and GitHub Actions. Duplicated
path lists in Python, shell and YAML are prohibited after migration because they can drift.

### 8.2 Selection Rules

1. Diff the exact merge-base/base SHA to candidate head SHA.
2. Select direct owners for every changed path.
3. Compute the transitive reverse-dependency closure.
4. Add global gates for workflows, shared Docker runners, root dependency files, Compose/release
   manifests, common libraries, generators and the dependency manifest itself.
5. Documentation-only paths may skip runtime builds only when they do not alter normative
   specifications, generated inputs, test fixtures or deployment behavior.
6. Unknown or conflicting paths force the current full PR gate set.
7. `main`, release qualification and release-manifest production retain the full required inventory
   until separate measured evidence and Founder approval change that policy.

### 8.3 Advisory-First Rollout

Change-aware CI has two modes:

| Mode | Behavior | Exit condition |
|---|---|---|
| Shadow | Compute and record the proposed selected set while current full PR CI still runs | At least 20 representative PRs or all major component classes, whichever is larger |
| Enforced | Run selected PR gates; fail closed to full on ambiguity | Founder approval after shadow evidence shows no false-negative selection |

During Shadow mode, compare every gate that failed under current full CI with the set proposed by the
classifier. Any failed gate omitted by the proposal is a false negative, blocks enforced activation
and requires manifest repair plus a restarted evidence window for the affected rule.

### 8.4 Enforcement

The classifier emits selected components, reverse-dependency reasoning, global triggers, skipped
gates and reasons. The QA aggregate rejects a required job that is absent without a validated
`NOT_APPLICABLE` decision. Branch protection continues to require the aggregate verdict rather than a
changing list of matrix children.

## 9. Unified Validation Lifecycle

The Platform IT Expert follows this order:

| Stage | Required action | Expensive full validation allowed? |
|---|---|---|
| 1. Contract intake | Build and validate the requirement-to-evidence ledger | No |
| 2. Milestone implementation | Write code and mapped focused tests together | Focused affected tests only |
| 3. Milestone repair | Fix the first causal defect and rerun the invalidated focused evidence | Focused affected tests only |
| 4. Candidate freeze | Commit one exact candidate SHA; compute change impact and immutable build identities | Build affected immutable images once |
| 5. Pre-qualification | Run static/ledger review while affected images prepare | Parallel, affected scope |
| 6. Qualification | Run affected coverage, contracts, security, browser and integration evidence in parallel where independent | Once for the frozen candidate |
| 7. PR preparation | Aggregate validated evidence and prepare the exact-head PR body | Reuse exact valid evidence; rerun only invalidated gates |
| 8. PR CI | Verify trusted manifests; run current full set in Shadow mode, selected set only after approval | Policy-controlled |
| 9. Main/release | Run complete required release safety net | Yes; remains mandatory |

Any source repair creates a new candidate SHA and invalidates evidence according to the dependency
manifest. Metadata-only PR body or label correction must not invalidate source-bound test evidence,
but any commit changes the author-review head binding and requires refreshed author review.

## 10. Component Impact

Expected implementation surfaces are:

| Component | Required change | Complexity |
|---|---|---|
| `scripts/prepare_pr_body.py` | DAG orchestration, bounded concurrency, evidence aggregation and reuse validation | Medium |
| Qualification scripts | Consume immutable runner/candidate identities, isolate outputs and avoid internal rebuilds | High |
| `.github/workflows/ci.yaml` | Build outputs, reusable images, classifier-driven matrices and stable aggregate gate | High |
| Docker test-runner definitions and Compose profiles | Stable input identities, cache boundaries and isolated concurrent execution | Medium-High |
| Dependency manifest and classifier | Direct/reverse ownership, global triggers, fail-closed path handling and reasoning output | High |
| Work Contract template and validator | Requirement-to-evidence ledger and pre-implementation completeness gate | Medium |
| QA/author-review aggregation | Validate direct evidence coverage, exact-head bindings and unresolved rows | Medium |
| Platform IT Expert office card | Require explicit story start/end commentary boundaries for every Work Component | Low |

No application business behavior, service API, database schema, customer data or cloud runtime is
intended to change. Discovery that such a change is necessary stops the affected milestone for
Solution Architect review.

## 11. Ordered Work Components

| ID | Scope | Required exit condition |
|---|---|---|
| WC100-00 | Contract freeze and baseline capture | Founder accepts scope; baseline records wall time, builds, test invocations and failures for representative PRs |
| WC100-01 | Earlier acceptance coverage | Template, ledger schema, validator and one representative implementation Work Contract prove pre-implementation and DONE enforcement |
| WC100-02 | Bounded parallel prechecks | Same gates/results as serial baseline; isolated concurrent execution and serial fallback pass |
| WC100-03 | Build once, test many | Runner and candidate identities prove one build consumed by multiple tests/scans; all invalidation tests pass |
| WC100-04A | Change-aware classifier in Shadow mode | Direct/reverse/global decisions recorded alongside unchanged full CI |
| WC100-04B | Shadow evaluation | Required sample completed with zero unresolved false negatives and measured savings report |
| WC100-04C | Enforced PR selection | Requires separate Founder approval; ambiguity fallback and full `main`/release validation remain passing |
| WC100-05 | Integrated qualification | Full regression, CCT, security, coverage, failure injection and evidence-manifest checks pass at one exact head |
| WC100-06 | Founder handoff | One unmerged PR with author review, baseline comparison, rollback plan and no unresolved contract row |

WC100-01 through WC100-04A may be implemented in one PR. WC100-04C cannot activate merely because
the code exists; it requires the Shadow exit evidence and explicit Founder approval. If repository
risk makes one PR impractical, the Founder may authorize milestone PRs without allowing partial WC-100
completion claims.

## 12. Mandatory Test Matrix

### 12.1 Acceptance Ledger

- every normative clause has exactly one or more evidence rows;
- duplicate, missing, malformed and unresolved rows fail;
- implementation-free contracts can declare a validated not-applicable state;
- aggregate coverage cannot substitute for direct acceptance evidence; and
- a later source requirement change invalidates stale ledger approval.

### 12.2 Parallel Prechecks

- parallel and serial modes select identical gates and produce equivalent verdicts;
- two failing independent gates are both reported;
- first causal failure classification is stable and bounded;
- concurrent coverage/results never collide;
- low-resource preflight selects serial fallback;
- cancellation and interruption leave no passing aggregate;
- transient infrastructure retry is bounded; assertion failure is not retried; and
- wall time improves on at least one representative multi-gate change without exceeding resource
  ceilings.

### 12.3 Build Reuse

- identical complete inputs reuse the same immutable image;
- source, test, fixture, lockfile, Dockerfile, Compose, build argument, generated contract, spec and
  gate-version changes each invalidate the appropriate result;
- scan and smoke evidence name the exact candidate digest;
- mutable-tag substitution fails;
- corrupted/missing manifest or artifact fails closed;
- base-image freshness invalidation is recorded; and
- separate jobs cannot mutate the reused image or shared evidence.

### 12.4 Change-Aware CI

- representative changes for every deployable service select its direct gates;
- shared libraries and contracts select all reverse dependencies;
- workflow, runner, Compose and dependency-manifest changes select broad qualification;
- unknown paths select full qualification;
- docs-only examples prove both valid skip and normative-spec broadening cases;
- deleted and renamed paths use both old and new ownership;
- merge-base movement invalidates stale selection;
- Shadow comparison detects a deliberately omitted failing reverse dependency; and
- `main` and release paths retain complete required validation.

### 12.5 Regression And Constitutional Gates

- current full Docker unit/integration/contract/browser suites pass;
- coverage thresholds remain unchanged;
- CCT, gitleaks, CodeQL/SAST, Trivy, dependency and applicable license checks pass;
- PR author review remains bound to the exact 40-character head;
- PR aggregate fails for failed, missing, cancelled or stale required evidence; and
- no Python or Node test tooling executes through a host-managed environment.

## 13. Measurement And Success Criteria

Capture comparable baseline and candidate measurements for at least one Web-only, one Business
Platform, one Python service, one shared-contract and one pipeline/global change:

| Metric | Required result |
|---|---|
| Required gate coverage | 100 percent equal to or stronger than current policy |
| Change-aware false negatives | Zero before enforced activation |
| Acceptance obligation coverage | 100 percent mapped; unresolved rows explicitly block DONE |
| Duplicate immutable runner builds | At most one per complete input identity per workflow run |
| Duplicate candidate builds | At most one per affected candidate identity before consuming tests/scans |
| Multi-gate precheck wall time | Lower than serial baseline for representative eligible changes |
| Failure diagnosis | First causal class and bounded artifact available without rerunning the complete suite |
| Main/release regression | No reduction in current complete required gates |

No fixed percentage speed claim is required before measurement. The PR must report observed medians,
ranges and sample sizes without extrapolating local results into CI savings.

## 14. Rollout And Rollback

1. Land schemas, classifier and orchestration with current full CI still authoritative.
2. Enable parallel local prechecks behind a serial fallback and record mode in evidence.
3. Enable build reuse only after invalidation and digest-consumption tests pass.
4. Run change-aware selection in Shadow mode while full PR CI remains unchanged.
5. Present Shadow evidence to the Founder before enabling selected PR gates.
6. Keep complete `main` and release validation regardless of PR selection mode.

Rollback is one configuration change to serial prechecks, no cross-job reuse and full PR CI. The old
qualification entry points remain usable until WC-100 is accepted. Evidence generated under a newer
schema is not silently interpreted by an older validator. Rollback must not delete retained evidence
or alter historical verdicts.

Immediate rollback triggers are any missed failing dependency, unexplained manifest disagreement,
cross-run contamination, stale evidence acceptance, nondeterministic selection, resource starvation
or a material increase in flaky infrastructure failures.

## 15. Definition Of Done

WC-100 is complete only when:

1. WC100-01 through WC100-04A and WC100-05 pass at one exact implementation head.
2. Every requirement in this contract is present in the validated obligation ledger with direct
   executable evidence or an explicit Founder-reserved state.
3. Parallel prechecks produce the same gate set and verdict semantics as serial execution and safely
   fall back when resources are insufficient.
4. Tests and scans consume exact immutable runner/candidate identities without hidden rebuilds.
5. The dependency classifier is centralized, versioned, reason-producing and fail-closed.
6. Shadow mode is active for change-aware PR selection; current full PR CI remains authoritative until
   WC100-04B evidence and separate Founder approval permit WC100-04C.
7. Coverage, security, CCT, author review, Founder review and complete `main`/release gates are not
   weakened.
8. Baseline-versus-candidate measurements are attached without unsupported savings claims.
9. Failure injection proves stale, missing, corrupted, cancelled and ambiguous evidence cannot pass.
10. The Platform IT Expert performs complete author review and submits one unmerged PR to the Founder.

WC-100 may be engineering-qualified before WC100-04C activation. It may not claim that change-aware
CI is fully enforced until the Shadow evidence window and separate Founder decision are complete.

## 16. Stop Conditions And Exclusions

Stop and return to the Solution Architect or Founder if implementation requires:

- lowering or removing an existing gate or coverage threshold;
- trusting mutable tags, incomplete hashes or developer assertions as CI evidence;
- changing branch protection, author/approver separation or merge authority;
- allowing unknown impact to skip validation;
- changing service behavior, API contracts, database schemas or cloud runtime;
- introducing a new third-party CI/test orchestration platform or technology decision without the
  required architecture/ADR authority; or
- activating selected PR CI before Shadow evidence and Founder approval.

Explicitly excluded from WC-100 are session compaction, session handoff formats, model selection,
targeted peer review, institutional reviewer activation, test-threshold reduction, Production
deployment and unrelated flaky-test repair.

## 17. Platform IT Expert Implementation Handoff

After explicit current-session authorization, the Platform IT Expert must:

1. read this contract's Record Control, Authority And Scope, Required Outcome, Sections 4 through 16
   and the exact owning implementation files;
2. create and validate the full requirement-to-evidence ledger before writing implementation code;
3. capture the current serial/full baseline before changing orchestration;
4. implement milestones in the Section 11 order, using focused Docker tests after each edit;
5. freeze a candidate before expensive qualification and avoid rerunning valid evidence unless an
   input identified by the invalidation contract changed;
6. retain the current full PR path during Shadow mode and the full `main`/release path throughout;
7. classify the first causal failure before repair and rerun only invalidated gates followed by the
   final applicable aggregate check;
8. distinguish code, coverage, infrastructure, security, metadata and acceptance failures in evidence;
9. perform author review against every normative clause and repair all findings; and
10. declare each story start and end in running chat commentary as required by Section 5.5; and
11. submit an unmerged PR with exact-head evidence for Founder review.

The implementer may choose language-level concurrency and manifest formats consistent with existing
repository patterns. It may not redesign the safety principles, selection semantics, evidence trust
boundary or activation gates in this contract.

## 18. Canonical Requirement Index

This index atomizes the contract's normative obligations for implementation intake. The implementing
agent may split a row into more detailed test cases, but it may not merge, omit or weaken a row. Every
row begins `PLANNED`; only raw executable evidence bound to the exact candidate may change it to
`PASS`. Section references supply the complete acceptance meaning.

| Requirement ID | Source | Atomic obligation | Minimum executable evidence | Initial result |
|---|---|---|---|---|
| WC100-R001 | Section 1 | Preserve every current required gate and fail closed on unknown applicability or invalid reuse | Gate-equivalence and invalid-manifest tests | PLANNED |
| WC100-R002 | Section 3.1 | Execute independent applicable prechecks concurrently within bounded resources | Parallel orchestration integration test | PLANNED |
| WC100-R003 | Section 3.2 | Build each immutable runner/candidate once per complete input identity and reuse it safely | Build-count and digest-consumption tests | PLANNED |
| WC100-R004 | Section 3.3 | Select affected owners and transitive reverse dependencies with full fallback on uncertainty | Classifier unit/property tests | PLANNED |
| WC100-R005 | Sections 3.4 and 5 | Map every implementation obligation to planned executable evidence before code begins | Ledger validator acceptance test | PLANNED |
| WC100-R006 | Sections 3.5 and 6.3 | Emit one exact-base/head manifest explaining run, reuse, skip and failure decisions | Manifest schema and binding tests | PLANNED |
| WC100-R007 | Section 4.1 | Keep line and branch coverage thresholds unchanged | CI configuration assertion and representative threshold failure | PLANNED |
| WC100-R008 | Section 4.2 | Run all tests and language tooling through repository Docker runners | Workflow/script static enforcement tests | PLANNED |
| WC100-R009 | Sections 4.3 and 4.4 | Preserve security, CCT, author-review, Founder-review and merge meanings | Required-gate aggregation tests | PLANNED |
| WC100-R010 | Sections 4.5 and 7.3 | Reject failed, cancelled, stale, malformed, incomplete or untrusted reuse evidence | Negative manifest matrix | PLANNED |
| WC100-R011 | Sections 4.6 and 7.1 | Invalidate evidence for every enumerated behaviorally relevant input change | Per-input invalidation tests | PLANNED |
| WC100-R012 | Sections 4.7 and 8.2 | Select full current validation for unknown paths, cycles, conflicts or classifier errors | Fail-closed classifier tests | PLANNED |
| WC100-R013 | Sections 4.8 and 6.2 | Isolate concurrent writable paths, Docker resources and mutable caches | Collision/failure-injection integration tests | PLANNED |
| WC100-R014 | Sections 4.9 and 13 | Keep evidence classes distinct and report measured results without unsupported extrapolation | Evidence-schema and report validation | PLANNED |
| WC100-R015 | Sections 5.1 and 5.2 | Require the Platform IT Expert to validate the complete acceptance ledger before implementation | Pre-implementation gate test on representative WC | PLANNED |
| WC100-R016 | Sections 5.3 and 5.4 | Block milestone/DONE claims for missing direct evidence or unresolved rows without exact variance | DONE rejection acceptance tests | PLANNED |
| WC100-R017 | Section 6.1 | Run selected gitleaks, Business Platform and release nodes as an explicit DAG | Selection and concurrency trace test | PLANNED |
| WC100-R018 | Section 6.2 | Bound parallelism, fall back on low resources and classify first causal failures without hidden results | Resource, dual-failure and retry tests | PLANNED |
| WC100-R019 | Section 7.2 | Prevent hidden rebuilds and mutable-tag substitution between build, test, smoke and scan | Build-spy and image-digest tests | PLANNED |
| WC100-R020 | Sections 7.3 and 7.4 | Record complete provenance and require exact identity equality before reuse | Provenance schema and tamper tests | PLANNED |
| WC100-R021 | Sections 8.1 and 8.2 | Centralize path ownership, direct gates, reverse dependencies and global triggers in one manifest | Duplicate-source prohibition and selection tests | PLANNED |
| WC100-R022 | Section 8.3 | Operate change-aware CI in non-authoritative Shadow mode for the required sample | Shadow comparison evidence | PLANNED |
| WC100-R023 | Sections 8.3 and 8.4 | Prevent enforced selection until zero unresolved false negatives and separate Founder approval | Activation-gate negative tests | FOUNDER-RESERVED |
| WC100-R024 | Sections 9 and 11 | Follow the ordered focused-test, freeze, qualify, aggregate and handoff lifecycle | End-to-end dry-run trace | PLANNED |
| WC100-R025 | Section 12 | Pass the complete acceptance, parallelism, reuse, classifier, regression and constitutional matrix | Raw test and scanner artifacts | PLANNED |
| WC100-R026 | Section 13 | Capture comparable baseline/candidate metrics across five named change classes | Machine-readable measurement report | PLANNED |
| WC100-R027 | Section 14 | Preserve serial/full rollback and trigger rollback on any named trust or isolation failure | Rollback and injected-trigger tests | PLANNED |
| WC100-R028 | Section 15 | Satisfy every completion condition at one exact implementation head without claiming WC100-04C early | Final ledger and exact-head author review | PLANNED |
| WC100-R029 | Section 16 | Respect every stop condition and exclude compaction, peer review and unrelated process changes | Changed-file/scope audit | PLANNED |
| WC100-R030 | Section 17 | Execute the Platform IT Expert handoff sequence without redesigning safety or authority boundaries | Milestone trace and author-review evidence | PLANNED |
| WC100-R031 | Sections 5.5 and 17 | Declare each story start with its identifier and intended outcome, then declare its end with concise evidence and any blocker in running chat commentary | Deterministic office-card contract test and session story-boundary evidence | PLANNED |
| WC100-R032 | Sections 7.5 and 13 | Preserve embedded source, executable shell scripts and test outcomes while replacing the full runner's post-copy metadata mutation with a measured Docker-layer equivalent | Dockerfile contract test, standalone/Compose smoke tests and comparable before/after build timings | PLANNED |

## 19. Solution Architect Author Review

The contract was reviewed against the Founder-approved four-point scope and the observed process
friction:

- bounded concurrency retains all current precheck meanings and adds isolation/fallback controls;
- build reuse is bound to complete immutable inputs and cannot rely on mutable tags;
- change-aware CI begins in non-authoritative Shadow mode and fails closed on uncertainty;
- acceptance coverage is owned first by Solution Architecture and operationalized by Platform IT
  before implementation;
- the canonical requirement index gives the implementation session stable IDs and direct evidence
   expectations for every normative obligation;
- Docker-only test execution, coverage, security, CCT and Founder merge authority remain unchanged;
- measurement avoids promising savings that have not yet been observed; and
- session compaction and targeted peer review are explicitly deferred.

**Solution Architect disposition:** FOUNDER REVIEW COMPLETE. IMPLEMENTATION AUTHORIZED FOR THE
CURRENT PLATFORM IT EXPERT SESSION BY FOUNDER INSTRUCTION ON 2026-09-18.