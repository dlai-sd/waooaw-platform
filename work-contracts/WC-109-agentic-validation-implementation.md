# WC-109 - Agentic Validation Control Plane Implementation And Pilot

## Record Control

| Field | Value |
|---|---|
| Authoring office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-29 continuous working session |
| Implementation authorization | Explicit Founder confirmation in the 2026-09-29 continuous working session |
| Scope amendments | Founder-approved 2026-10-01 dispositions for AS-001/AS-003/AS-005 and the single implementation-PR hosted pilot; Founder-approved 2026-10-02 execution-outcome remediation, WC-110 separation and current-session implementation |
| Status | AUTHORIZED - IMPLEMENTATION IN PROGRESS - HOSTED SELF-PILOT PENDING |
| Required predecessor | WC-108 merged with ADR-050 and Docker validation strategy amendments intact |
| Governing decision | ADR-050 as amended by WC-108 |
| Constitutional basis | C-023, C-059, C-065, C-071, C-076, C-077, C-080 and C-086 |
| Implementing office | Platform IT Expert (INST-012) |
| Architecture reviewer | Enterprise Architect (INST-004) |
| Branch after predecessor merge | `wc/109-agentic-validation-implementation` |
| Completion boundary | Control-plane implementation plus one bounded hosted self-pilot on its implementation PR |

## 1. Objective

Implement the repository and CI control plane specified by WC-108 so an AI implementation agent can
obtain fast, disposable Docker feedback without rebuilding validation runners or product images for
ordinary source edits, while final authority remains bound to one immutable release candidate and the
complete applicable qualification inventory.

The delivery must operationalize four independent identities and four ordered tiers without changing
ADR-050, weakening a gate, moving test execution onto a host, or enabling selective hosted validation.

The implementation PR must also demonstrate institutional business value during its own execution:
earlier first-cause discovery, avoided invalid compute, zero ordinary-story image builds, fewer replayed
lanes, bounded repair loops and unchanged final quality authority. These are delivery outcomes that reduce
the time and cost of producing customer value; they are not a claim that WC-109 itself adds a customer
feature or proves product readiness.

## 2. Authority And Preconditions

This Work Contract authorizes implementation only after WC-108 is merged and the implementation branch
is rebased on that merged authority. If WC-108 changes during review, the Solution Architect must assess
this contract before implementation starts; material conflict returns the contract to Enterprise
Architecture rather than being resolved in code.

Current-session Founder authorization permits the bounded implementation and validation described here.
It does not authorize deployment, customer traffic, cloud mutation, new paid services, Production access,
selective hosted-validation enforcement, self-approval or self-merge.

### 2.1 Founder-Approved Acceptance-Gate Disposition

For the WC-109 control-plane PR only, `acceptance:as-001`, `acceptance:as-003` and
`acceptance:as-005` remain visible with terminal result `BLOCKED` and disposition
`BLOCKED-DEFERRED`; they must not be represented as PASS. WC-109 qualification may proceed with exact
evidence for 40/40 executable control-plane gates plus exact BLOCKED evidence for the three named gates.
No gate is deleted and no threshold is reduced. Each scenario requires a separate Founder-authorized
product Work Contract and becomes mandatory before release of its corresponding product. This amendment
does not authorize a 43/43 claim or any product-readiness claim.

### 2.2 Founder-Approved Hosted Pilot Disposition

On 2026-10-01, the Founder approved the WC-109 implementation PR as the single hosted pilot and removed
the two-product-PR pilot requirement. This amendment resolves the dependency cycle in which the hosted
control plane had to be merged before ordinary product PRs could exercise it, while WC-109 previously
required those product PR observations before its own PR could be created.

The implementation PR must execute unchanged full CI as the authoritative result and retain Shadow
selection as observational only. Its exact-head pilot record must satisfy Section 8. One observation is
not trend or performance-improvement proof. Every deterministic control-plane defect observed during the
pilot must be repaired retrospectively on the implementation PR with a bounded regression fixture before
qualification. This amendment does not authorize selective hosted validation, self-approval or self-merge.

Before the first implementation edit, the implementing office must record:

1. exact merged WC-108 commit;
2. exact WC-109 contract and ledger digests;
3. selected implementation requirement IDs;
4. clean branch and worktree identity;
5. current full-validation baseline; and
6. the available runner identities or the evidence that a declared runner rebuild is required.

## 3. Scope

### 3.1 In scope

- versioned manifests and deterministic canonicalization for runner, test-execution, candidate and
  evidence identities;
- Tier 1 static preflight, Tier 2 mounted-source story execution, Tier 3 milestone checks and Tier 4
  frozen-candidate qualification;
- extension of the existing validation catalog, local catalog entry point and hosted catalog executor;
- reuse or bounded repair of existing Python, .NET, TypeScript, browser and specialized runners;
- Docker and Compose definitions needed for non-root mounted-source execution, disposable state,
  isolated outputs, bounded resources and classified Docker-socket access;
- candidate build, digest, SBOM and provenance binding;
- cache namespace, locking, integrity, size and clean-cache controls;
- common evidence envelopes, redaction, freshness, carry-forward and first-cause failure routing;
- hosted workflow integration in shadow or full-safe mode while current full CI remains authoritative;
- Docker-executed unit, component, integration, policy and regression tests for this control plane;
- operator and agent-facing command documentation required to execute the four tiers; and
- bounded pilot instrumentation and evidence for the Founder-approved WC-109 implementation PR;
- `web/package.json` and `web/pnpm-lock.yaml` changes limited to remediating dependency-security
  findings raised by that hosted pilot; and
- pre-PR execution of externally volatile advisory gates without PASS reuse, plus supplied-runner
  execution of affected deterministic gates before PR evidence preparation.

### 3.2 Out of scope

- product behavior changes in `src/` or `web/`; the dependency-metadata exception in Section 3.1
  authorizes no product source, API, configuration or acceptance change;
- alteration of ADR-050, WC-108 or any ratified constitutional claim;
- replacement of the existing language-specific runner model with one generic persistent executor;
- persistent test processes, databases, browsers, generated outputs or verdicts as correctness state;
- a new deployable service, database, queue, cloud resource or third-party test-impact platform;
- Production deployment, customer traffic, registry retention-policy mutation or cloud-provider mutation;
- reduction of tests, thresholds, security checks, CCTs, author review or Founder review;
- selective hosted-validation enforcement or removal of current full `main` and release safety nets;
- unsupported fixed-duration or percentage-saving commitments; and
- treating the single implementation-PR pilot as statistical trend or performance-improvement proof.

## 4. Component Decomposition

### 4.1 Identity Manifest Resolver

The resolver produces four separately versioned canonical manifests. Each manifest must identify its
schema and canonicalization version. Equality in one manifest must not be inferred from another.

| Manifest | Required inputs | Required output |
|---|---|---|
| Runner | Toolchain Dockerfile, pinned base digest, installation inputs, system and language dependency lockfiles, runner policy, architecture and platform | Canonical manifest plus content digest |
| Test execution | Mounted-source identity, runner digest, catalog command, policy, declared non-secret environment, service identities and disposable-state contract | Canonical execution manifest plus content digest |
| Candidate | Complete effective build context, generated artifacts, Dockerfile frontend, build arguments, base digests, architecture and platform | Canonical candidate manifest plus content digest |
| Evidence | Candidate or source identity, runner, command, policy, environment, schema, trust source and gate-specific freshness inputs | Canonical evidence manifest plus content digest |

Canonicalization must use structured parsers rather than concatenated ad hoc strings. Relevant file
content, normalized repository-relative path, executable mode, symlink target, generated-artifact state,
dirty state, untracked state, rename/deletion state, architecture and platform must be represented when
they can affect the governed result. Raw secrets and customer data are prohibited. A non-secret authority
or secret-version reference is included only when behavior depends on it.

### 4.2 Tier Orchestrator

The orchestrator is the only standard entry point for authoritative local and hosted validation. It
extends the existing catalog-controlled route rather than creating a second command system.

| Tier | Entry condition | Required behavior | Exit evidence |
|---|---|---|---|
| 1 - Static preflight | Valid Work Contract and selected requirements | Validate catalog, manifests, syntax, policy, mounts, UID/GID, permissions, socket contract, outputs and workflow placement without runner or candidate build | Diagnostic/preflight envelope |
| 2 - Disposable story run | Tier 1 PASS and trusted runner available | Execute selected catalog command in a stack-specific disposable container against mounted source and isolated writable outputs | Focused local envelope and native artifacts |
| 3 - Milestone checks | Declared dependency boundary reached | Resolve direct ownership and reverse dependencies; execute dependency-complete affected unit, component and integration gates | Milestone envelopes and native artifacts |
| 4 - Frozen-candidate qualification | Authorized stories and required milestones PASS; candidate frozen | Build or resolve exact candidate once, capture supply-chain evidence and run complete applicable qualification with hosted-only gates in their authoritative environment | Candidate-bound qualification inventory |

A Tier 2 or Tier 3 PASS cannot be promoted to Tier 4 authority. Before candidate freeze, independent
component lanes and cheap cross-cutting controls execute separately under their catalogued resource and
dependency boundaries; all required lanes must pass before the candidate build begins.

Tier 4 gates do not require one serial shell. They may execute as separately scheduled component or
cross-cutting lanes and complete in any order. Each result must bind the same frozen candidate, gate
identity, execution identity, trust and freshness inputs. A failed lane does not invalidate an unchanged,
valid PASS from another lane: repair and rerun only the failed or affected lane, then assemble all required
results in canonical catalog order. Missing, stale or mismatched results still block qualification.

A same-candidate runner, service or environment repair preserves only evidence whose complete binding
remains unchanged. A source or effective candidate-input repair requires refreeze and invalidates every
qualification result affected by the changed candidate, execution or freshness identity; no prior PASS is
silently promoted to the new candidate.

### 4.3 Stack Execution Adapter

The adapter maps each catalog entry to an existing stack runner and its exact command. Both focused and
qualification modes consume the same test definition, fixtures and thresholds.

Required controls:

- ordinary application-source edits trigger zero runner and zero product-image builds in Tier 2;
- workspace source is read-only where practical, with explicit isolated writable output mounts;
- each run receives unique project, container, network, volume, port and artifact namespaces;
- containers run non-root with deterministic UID/GID and HOME behavior;
- service dependencies and fixtures are disposable or prove reset and isolation before reuse;
- Docker socket access is absent by default and available only to catalogued Testcontainers runners;
- CPU, memory, disk, timeout and concurrency bounds are declared; and
- direct Docker commands remain diagnostic and cannot publish authoritative PASS evidence.

Existing runners must be reused when they satisfy this contract. A Dockerfile may change only when a
declared runner input or execution-boundary defect requires it. Every such change must update runner
identity tests and prove that ordinary source remains excluded from runner invalidation.

### 4.4 Catalog And Impact Selector

The versioned catalog is the sole source for gate identity, exact command, runner, source ownership,
test ownership, generated-artifact ownership, reverse dependencies, required services, resource class,
retry class, evidence outputs, freshness and lifecycle applicability.

Selection must use an exact merge base and head. Renames and deletions evaluate old and new paths.
Unknown paths, missing owners, malformed entries, cycles, parser disagreement or uncertain impact select
the complete applicable inventory. Missing identity, provenance, signature or trust blocks the affected
gate; broader execution cannot manufacture that authority.

### 4.5 Candidate Builder And Supply-Chain Binder

The builder resolves the complete `.dockerignore`-effective context and every generated contract input
before assigning candidate identity. It must bind:

- exact 40-character source commit and clean-state proof;
- canonical candidate manifest and digest;
- immutable OCI image digest;
- base-image digests, Dockerfile frontend, build arguments, architecture and platform;
- SBOM and provenance or attestation references; and
- the qualification inventory consuming those exact bytes.

A candidate build occurs only at freeze, when an effective candidate input changes, or when a trusted
artifact for an otherwise exact identity is unavailable. Mutable branch names, tags, marker files or
workspace timestamps cannot stand in for candidate identity.

### 4.6 Cache Controller

Package download and compiler caches are acceleration only. They must be namespaced by runner digest,
platform and applicable lock identity; concurrent access requires safe locking or write isolation.
Integrity checks, size bounds, eviction behavior and a periodic clean-cache route are mandatory.

Executable dependency trees, generated output, test databases, queues, browser state, process state,
coverage verdicts and prior PASS/FAIL results must not become shared cache authority. A cache miss or
cache rejection may cost time but cannot weaken or skip the selected check.

### 4.7 Evidence And Freshness Controller

Each node emits framework-native evidence plus one bounded machine-readable envelope. The envelope must
contain schema version, base and head commits, all applicable identity digests, component, stable gate ID,
command ID, UTC start, duration, result, routing class, bounded first cause and artifact references.

Evidence disposition is explicit:

- `executed` - the gate ran against the bound inputs;
- `exact-candidate-reuse` - immutable candidate, command, policy, environment, trust and freshness are
  exactly equal; or
- `verified-carry-forward` - deterministic non-impact proof across the exact commit range is attached and
  the evidence is rebound to the new head without being represented as fresh execution.

Vulnerability database state, provider state, external policy, hosted environment and other
time-sensitive authorities are included where relevant. Missing, stale, malformed, untrusted or
identity-mismatched evidence fails closed. Secrets, provider tokens, customer data, authorization material
and conversation content are prohibited from envelopes and artifacts.

### 4.8 Failure Router

The first causal failure receives one routing class:

| Class | Owner examples |
|---|---|
| `RUNNER` | Image, toolchain, UID/GID, mount, cache, socket or container-runtime defect |
| `WORKFLOW` | Orchestration, hosted-job, permission or lifecycle-placement defect |
| `PRODUCT` | Application behavior, contract, generated client or test defect |
| `EXTERNAL` | Registry, package service, provider, cloud or network dependency defect |
| `EVIDENCE` | Missing, stale, malformed, untrusted or unpublished proof |

Classification routes repair ownership and never converts failure to PASS. Assertion, compilation,
coverage and security failures are not automatically retried. Only a catalogued transient external or
infrastructure condition receives a bounded retry. An unchanged deterministic fingerprint must be
repaired at a bound input before another costly attempt.

### 4.9 Hosted Policy Enforcer

Hosted workflows must invoke the same catalog executor and manifest schemas as local execution. A policy
gate rejects host execution of test-language tooling, virtual environments, host package installation for
tests, unclassified direct commands, mutable runner identity and evidence without exact commit binding.

Hosted-only, provider-backed, deployment and customer-traffic checks remain authoritative only in their
declared environments. Current full PR CI remains authoritative during shadow comparison. Complete
`main` and release safety nets remain unchanged.

### 4.10 Pilot Recorder

The recorder produces one record for the Founder-approved WC-109 implementation PR created after the
implementation became available. The record must include:

- PR and exact commit identities;
- applicable stack and change class;
- cold/warm and cache state;
- Tier 1 through Tier 4 elapsed distributions and sample counts;
- runner and candidate build counts by exact identity;
- first-pass precheck result and modeled-defect recurrence;
- repair-loop count and first-cause classes;
- selected and complete applicable gate inventories;
- selection false-negative comparison against unchanged full CI; and
- quality, coverage, security and CCT outcomes.

The record also lists every retrospective pilot fix, its first-cause class, exact fix commit and bounded
regression fixture, and must contain no unresolved pilot defect at qualification.

The recorder reports observations, ranges, medians, samples and limitations. It must not claim an
unsupported percentage improvement or authorize selective hosted validation.

## 5. Interface Contracts

### 5.1 Invocation contract

Every standard invocation supplies a mode, exact base/head or workspace identity, selected requirement
IDs and requested gate or milestone. The executor resolves all remaining command and environment details
from the versioned catalog. Secret-bearing arbitrary command lines are not accepted as authority inputs.

### 5.2 Result contract

Every invoked node returns exactly one terminal result: `PASS`, `FAIL`, `BLOCKED` or `NOT_APPLICABLE`.
Missing output, process termination, schema failure or publication failure is `BLOCKED` or `FAIL`, never
implicit PASS. Dependent nodes stop without erasing independent results already produced.

`BLOCKED-DEFERRED` is an evidence disposition, not a fifth terminal result. It is valid only for the
three gates named in Section 2.1 and only when the terminal result remains `BLOCKED`.

### 5.3 Artifact contract

Artifacts are written atomically into a unique host-visible run directory. Publication records digest,
size, schema and retention class. Consumers open the bounded envelope first and retrieve raw artifacts
only when needed. Path traversal, symlink escape and cross-run overwrite must be rejected.

### 5.4 Compatibility contract

Existing catalog gate IDs and direct consumers remain compatible or receive an explicit migration map.
The compatibility sequence `static contract`, `exact-container execution contract`, `focused gate` and
`atomic host-visible evidence` remains recognizable in policy output while implementing the four tiers.

## 6. Delivery Stages

| Stage | Entry | Required outputs | Exit |
|---|---|---|---|
| 0 - Baseline and contract proof | WC-108 merged; WC-109 digest valid | Requirement matrix, current full inventory, current build/elapsed baseline, selected implementation order | Architecture review confirms no unresolved contract conflict |
| 1 - Identity and preflight | Stage 0 PASS | Four manifest schemas, canonicalizer, Tier 1 policies and fixtures | Identity vectors and modeled defects pass in Docker |
| 2 - Disposable focused execution | Stage 1 PASS | Stack adapters, mounted-source Tier 2, output isolation and cache boundaries | Source-only edits execute with zero runner/product builds |
| 3 - Milestones and evidence | Stage 2 PASS | Reverse-dependency selection, Tier 3, envelopes, freshness and failure routing | Dependency-complete fixtures and failure routes pass |
| 4 - Candidate qualification | Stage 3 PASS | Pre-freeze component lanes, freeze/build/bind route, SBOM/provenance binding, independently scheduled Tier 4 gates and canonical result assembly | Exact candidate consumes the complete inventory; the Section 2.1 amendment permits 40 executable PASS results plus three exact BLOCKED-DEFERRED results |
| 5 - Hosted shadow operation | Stage 4 PASS | Hosted policy enforcement and selection shadow comparison | Full CI remains authoritative; zero unresolved false negatives in observed runs |
| 6 - Implementation-PR pilot | Stage 5 PASS | One complete hosted pilot record | The Founder-approved implementation PR record satisfies Section 8 without unsupported extrapolation |
| 7 - Closeout | Stage 6 PASS | Final ledger, author review, independent EA review request and Founder-ready evidence | No unresolved requirement; implementation remains unmerged until Founder review |

Each milestone commit must leave the branch executable or explicitly record why the next requirement is
expected-fail. Failure at a stage rolls back to the last complete stage and restores full clean
qualification; evidence from an incompatible newer schema is not interpreted under an older stage.

## 7. Executable Validation Plan

All test and test-language tooling executes through repository-defined Docker containers. Required test
families are:

1. golden canonicalization vectors for ordering, paths, modes, symlinks, renames, deletions, dirty and
   untracked inputs;
2. identity invalidation matrices proving each governing input changes only the intended identities;
3. negative secret and customer-data fixtures;
4. Tier-order state-machine tests, including repair after freeze;
5. source-only story tests proving zero runner and product-image builds;
6. non-root, UID/GID, HOME, mount, socket, output, namespace and concurrent-run isolation tests;
7. cache namespace, lock, corruption, eviction and clean-cache tests;
8. ownership, reverse-dependency, unknown-path, cycle, malformed-catalog and parser-disagreement tests;
9. evidence equality, freshness, trust, carry-forward and atomic-publication tests;
10. first-cause routing and bounded-retry tests for all five routing classes;
11. candidate context, digest, SBOM, provenance and changed-input rebuild tests;
12. hosted-policy tests rejecting host test execution and non-catalogued authority;
13. compatibility tests for current catalog consumers and policy vocabulary; and
14. complete qualification proving no current gate or threshold is lost.

Implementation-shaped unit tests without exercised Docker and workflow boundaries cannot alone complete a
requirement that governs those boundaries.

## 8. Pilot Success Conditions

The Founder-approved WC-109 implementation PR pilot must satisfy all applicable conditions:

| Outcome | Completion condition |
|---|---|
| Ordinary story builds | Zero runner or product-image builds for source-only Tier 2 edits |
| Identity builds | At most one build per exact runner or candidate identity unless a failed build emits bounded failure evidence |
| Preflight | No recurrence of a modeled UID, mount, socket, output or workflow-placement defect |
| New defects | Every new deterministic control-plane defect gains a bounded regression fixture before retry |
| Repair loops | First-pass and repair-loop counts are reported per PR with first-cause classification |
| Selection | Full-CI comparison has zero unresolved selection false negatives |
| Quality | 100% of the previously applicable final gate inventory executes or has authorized exact evidence disposition |
| Thresholds | No coverage, quality, security or CCT threshold is reduced |
| Reporting | Timings include distributions, sample counts, cache state and limitations |
| Retrospective fixes | Every observed deterministic control-plane defect is fixed on the implementation PR with exact commit and bounded regression evidence; none remains unresolved |

Failure to meet a speed hypothesis does not fail valid product behavior or authorize gate removal. It
records a pilot limitation for Founder disposition. Failure of identity, trust, isolation, selection or
quality conditions blocks completion.

## 9. Canonical Requirement Index

| Requirement | Normative outcome |
|---|---|
| WC109-R001 | Implementation is based on the exact merged WC-108 authority and a digest-bound WC-109 ledger. |
| WC109-R002 | Four independently versioned canonical identity manifests are produced without raw secrets. |
| WC109-R003 | Runner identity includes every environment-producing input and excludes ordinary application source. |
| WC109-R004 | Test-execution identity binds mounted source, runner, command, policy, environment, services and disposable state. |
| WC109-R005 | Candidate identity covers every effective build input and binds digest, SBOM and provenance. |
| WC109-R006 | Evidence identity binds execution inputs, trust and gate-specific freshness independently of candidate identity. |
| WC109-R007 | Tier 1 rejects deterministic execution-contract defects before costly work or image construction. |
| WC109-R008 | Tier 2 uses existing stack runners and disposable mounted-source execution. |
| WC109-R009 | Ordinary Tier 2 source edits cause zero runner and product-image builds. |
| WC109-R010 | Tier 3 executes independently completable component lanes and assembles dependency-complete checks at declared milestone boundaries. |
| WC109-R011 | Tier 4 assembles independently emitted results for one immutable candidate against the complete applicable inventory without replaying unchanged PASS lanes. |
| WC109-R012 | Same-candidate recovery reruns only failed or identity-affected lanes; a candidate-input repair refreezes and invalidates affected evidence. |
| WC109-R013 | Focused and qualification modes consume the same catalogued test definitions and thresholds. |
| WC109-R014 | Every run is non-root, resource-bounded and isolated across state, namespace and output. |
| WC109-R015 | Docker-socket access is absent by default and limited to classified runners. |
| WC109-R016 | Caches are namespaced, concurrency-safe, integrity-checked and never correctness authority. |
| WC109-R017 | Unknown or ambiguous impact selects the complete applicable inventory. |
| WC109-R018 | Missing identity, provenance, signature or trust blocks rather than broadening into false authority. |
| WC109-R019 | Evidence disposition distinguishes execution, exact-candidate reuse and verified carry-forward. |
| WC109-R020 | Carry-forward requires exact-range deterministic non-impact proof and explicit new-head binding. |
| WC109-R021 | Every node publishes one atomic bounded envelope plus framework-native evidence. |
| WC109-R022 | Evidence and artifacts exclude secrets, authorization material, customer data and conversation content. |
| WC109-R023 | Failures route as RUNNER, WORKFLOW, PRODUCT, EXTERNAL or EVIDENCE without changing result authority. |
| WC109-R024 | Automatic retries are limited to catalogued transient conditions and unchanged failures cannot rerun. |
| WC109-R025 | Hosted policy rejects host test execution, virtual environments and unclassified authority paths. |
| WC109-R026 | Hosted-only and provider-backed gates retain their authoritative environment. |
| WC109-R027 | Current full CI, complete main/release safety nets and all thresholds remain intact. |
| WC109-R028 | Direct Docker diagnostics cannot publish authoritative PASS evidence. |
| WC109-R029 | Candidate build inputs and supply-chain evidence are captured before qualification. |
| WC109-R030 | Required Docker tests exercise identity, tier, isolation, cache, selection, evidence and failure boundaries. |
| WC109-R031 | The Founder-approved WC-109 implementation PR produces one complete hosted pilot record. |
| WC109-R032 | Pilot reports observations and limitations without unsupported percentage or fixed-duration claims. |
| WC109-R033 | Pilot comparison has zero unresolved selection false negatives and no quality reduction. |
| WC109-R034 | Rollback restores full clean qualification without reinterpreting incompatible evidence. |
| WC109-R035 | Selective hosted validation remains disabled pending separate Founder approval. |
| WC109-R036 | Author review, independent Enterprise Architecture review and Founder merge authority remain separate. |
| WC109-R037 | WC-109 qualification records 40/40 executable gates as PASS and AS-001, AS-003 and AS-005 as exact BLOCKED-DEFERRED evidence without a 43/43 or product-readiness claim. |
| WC109-R038 | The retained failed WC-109 run establishes a bounded before-improvement value baseline and current work is preserved before scope separation. |
| WC109-R039 | Every selected obligation has a machine-checkable owner, dependency graph, cost class, acceptance check, evidence destination and invalidation rule before compute. |
| WC109-R040 | Phases A through E advance only on current compatible evidence and cannot be bypassed by a broader or later run. |
| WC109-R041 | Readiness preflight validates authority, supply, execution, resource and evidence prerequisites before any affected costly lane starts. |
| WC109-R042 | The first failed or blocked prerequisite suppresses dependent and higher-cost work while retaining independently reusable results. |
| WC109-R043 | An unchanged deterministic failure cannot rerun; repair requires a changed governing input and focused evidence before restitching. |
| WC109-R044 | Every chunk publishes terminal evidence and an atomic run-index checkpoint that supports identity-verified resume without replaying unaffected work. |
| WC109-R045 | Costly execution declares resource bounds and performs bounded evidence-preserving disk recovery before starting or remains BLOCKED. |
| WC109-R046 | Qualification cannot start until executable negative fixtures prove planning, phase, failure, recovery, resource and stitching controls fail closed. |
| WC109-R047 | PR #481 publishes a before-and-after value record for feedback time, avoided compute, builds, repair loops, replay, selection accuracy and preserved quality. |
| WC109-R048 | WC-110 product work is preserved under separate authority and enters the WC-109 candidate only through an explicit merged-base or stacked-consumer dependency. |
| WC109-R049 | Pre-PR control executes volatile dependency advisories fresh and affected deterministic gates through supplied runners before PR evidence preparation. |

## 10. Definition Of Done

WC-109 is DONE only when:

- all ledger requirements are PASS with direct source and executable evidence;
- all four identities and tiers operate through the catalog-controlled route;
- the complete Docker validation suite and current full qualification satisfy the Section 2.1 disposition
  against the frozen candidate;
- no applicable quality, security, coverage, CCT or evidence threshold is weakened;
- the Founder-approved implementation PR pilot record satisfies Section 8;
- every partial, deferred, untested or externally blocked obligation remains visibly not PASS;
- the implementing office completes a requirement-by-requirement author review;
- the Enterprise Architect independently reviews architectural conformance; and
- the Founder receives the exact-head evidence package for review and merge.

Passing tests, implementation-shaped mocks, a local-only substitute, or elapsed-time improvement cannot
compensate for incomplete hosted pilot evidence.

## 11. Stop Conditions

Stop and raise a blocker if implementation would:

- require alteration of WC-108 or ADR-050 rather than component realization;
- require product behavior changes outside a separately authorized pilot Work Contract;
- execute tests or test-language tooling outside Docker;
- introduce a generic persistent test executor or persistent correctness state;
- omit a governing input because canonicalization is difficult;
- treat a cache hit, local PASS, broader run or stale evidence as authority;
- expose secrets, authorization material or customer data in identities or evidence;
- weaken or remove a current gate, threshold or safety net;
- activate selective hosted validation;
- mutate cloud, deployment, registry policy or Production state without separate authority; or
- proceed after WC-108, the ledger or the implementation branch identity becomes ambiguous.

## 12. Rollback

Rollback restores the previous full clean Docker qualification path and current complete hosted CI.
It disables new selection, carry-forward and tier shortcuts; removes no historical evidence; and refuses
to interpret evidence under a schema or identity model different from the one that produced it.

Runner or candidate artifacts may remain only when their immutable digest and provenance are still
verifiable and retention is already authorized. No rollback may convert previously blocked or failed
evidence to PASS.

## 13. Handoff

After this contract and ledger validate, Platform IT Expert may begin Stage 0 on a branch created from
the merged WC-108 authority. The implementing office must select requirement IDs before each coherent
edit, validate immediately through Docker, commit at milestone boundaries, and preserve expected-fail
state until the corresponding executable evidence exists.

Solution Architecture author review confirms decomposition only. It is not implementation evidence,
independent architectural approval, Founder approval of the resulting code or merge authority.

## 14. Agent Execution Engineering Practice

This section governs **agent execution** as an engineering control, not as conversational guidance. Its
purpose is a world-class first-attempt outcome: every defect that is knowable from repository contracts,
schemas, dependency declarations, prior deterministic failures and available local evidence is prevented
before costly execution begins. It does not redefine an unknown external failure as preventable or
guarantee that an unavailable dependency will succeed. Unknowns must fail closed, retain evidence and
become a modeled precondition before the next attempt.

### 14.1 Plan Before Compute

Before running a build or test, the agent must produce a machine-checkable execution plan for the
selected requirements. Every obligation maps to:

- one smallest independently testable chunk with an owning component;
- its exact inputs, direct prerequisites and downstream dependents;
- a cost class of `STATIC`, `FOCUSED`, `INTEGRATION`, `MUTATION`, `BROWSER`, `FUZZ`, `HOSTED` or
  `QUALIFICATION`;
- one executable acceptance check and expected evidence location; and
- an invalidation rule stating which changed inputs require that chunk to run again.

An obligation that lacks an owner, check, dependency or evidence contract is `BLOCKED`. The agent may
not discover those missing controls by launching a broader or more expensive chain.

The implementation lifecycle has five phases and may advance only in order:

| Phase | Required outcome before advancing |
|---|---|
| A - Design | Owning code path, contract, dependency graph, failure modes and acceptance check are explicit. |
| B - Component implementation | The smallest production change and its focused tests pass independently. |
| C - Dependency integration | Direct consumers and reverse dependencies pass without broad qualification. |
| D - System stitching | All compatible component chunks are assembled and cross-component behavior passes. |
| E - Qualification handoff | One clean stitched run confirms the already-qualified system and publishes complete evidence. |

PR preparation is downstream administrative handoff. It is not an implementation phase and must never
be used to discover, repair or compensate for an incomplete phase A through E.

### 14.2 Readiness Funnel

Execution proceeds through a mandatory cheapest-first funnel:

1. validate contract and ledger digests, exact base/head, clean-state policy, catalog schema, requirement
   selection, commit trace, command availability, immutable runner and service supply, mounts, output
   permissions, resource budgets, disk capacity and evidence destinations;
2. execute static and focused checks for each independent chunk;
3. execute only the integration checks whose prerequisites and constituent chunks PASS;
4. freeze compatible exact inputs and prove that every required chunk has current independent evidence;
5. stitch the independently passing components and validate cross-component behavior; and
6. execute one qualification run as confirmation of the completed implementation, not as defect discovery.

No later step may compensate for an earlier failed or missing result. A broader run cannot manufacture
authority for a prerequisite that did not pass.

### 14.3 Fail Fast And Repair Locally

The first `FAIL` or `BLOCKED` result stops every not-yet-started dependent lane and every not-yet-started
lane in a more expensive cost class. Already running independent lanes may finish only when their result
is reusable and stopping them would destroy useful evidence; no new costly lane is scheduled after the
failure. The controller reports one bounded first cause and marks downstream effects as suppressed.

An unchanged deterministic failure fingerprint cannot run again. A repair attempt requires a changed
governing input, execution of the failed or identity-affected chunk, and focused PASS evidence. Other
valid independent evidence remains intact. The complete chain may be stitched again only after every
failed or invalidated chunk passes independently.

### 14.4 Durable Checkpoints And Recovery

Each chunk publishes its terminal envelope and native artifacts atomically when that chunk ends. The run
index is updated atomically after every publication. `FAIL`, `BLOCKED`, process interruption, timeout and
operator cancellation are first-class terminal evidence; an end-of-chain manifest is an assembly view,
not the sole record of work performed.

A resumed agent reconstructs state from these envelopes, verifies their identities and freshness, and
runs only missing, failed or invalidated chunks. Conversation memory, terminal scrollback and an agent's
claim that a check passed are never evidence.

### 14.5 Resource And Disk Discipline

Every non-static cost class declares timeout, CPU, memory, disk and concurrency bounds. Before each
costly phase, the controller verifies workspace capacity. When free workspace capacity is below 5
percent, it must safely remove only disposable validation containers, networks, volumes, build cache and
unreferenced images, preserve protected evidence and immutable required runners, then recheck capacity.
If the guard remains unsatisfied, execution is `BLOCKED`; the controller must not begin the phase.

Cleanup is controlled behavior with bounded evidence. Agents may not use destructive repository or
Docker cleanup as an unrecorded recovery technique.

### 14.6 Mechanical Enforcement

The catalog schema, orchestrator state machine, evidence controller and rollback controller
must enforce this section. Required negative tests prove at least:

- a modeled preflight defect starts no costly lane;
- the first deterministic failure schedules no dependent or higher-cost work;
- interruption leaves valid per-chunk terminal evidence and a resumable run index;
- unchanged deterministic failure cannot retry;
- independently repaired chunks can be restitched without replaying unaffected evidence;
- incompatible or stale chunk evidence blocks stitching;
- low disk invokes bounded safe cleanup before costly work and blocks when capacity remains unsafe; and
- qualification cannot start until phases A through D have current compatible PASS evidence.

An agent instruction, checklist, session memory, prompt or manual convention does not satisfy this
section. WC-109 cannot be DONE until these controls fail closed under executable Docker and workflow
fixtures and the final stitched run demonstrates that no known defect was deferred to qualification.

### 14.7 Strategic Outcome Groups

Remediation is delivered as ordered value groups. Each group must publish its outcome before the next
group may use it as authority:

| Group | Required institutional outcome | PR #481 proof |
|---|---|---|
| 1 - Value and scope integrity | One attributable control-plane investment and one preserved before-improvement baseline | Preserve the authorized head and failed-run facts; separate product authority before candidate freeze |
| 2 - Prevent wasted execution | Invalid work consumes no affected costly lane and first cause appears at the cheapest capable boundary | Replay the known authority, service-supply and deferred-disposition defects through PLAN and preflight fixtures |
| 3 - Fast implementation flow | Ordinary source remediation receives bounded mounted-source feedback without runner or product-image builds | Execute each remaining coherent WC-109 story through Tier 2 and record elapsed and build events |
| 4 - Recoverable delivery | Failure or interruption preserves unaffected work and resumes only missing, failed or invalidated chunks | Inject a controlled same-candidate failure and interruption, then resume from terminal chunk evidence |
| 5 - Trusted qualification | One exact control-plane candidate is confirmed without using qualification as defect discovery | Assemble independently emitted results only after Groups 1 through 4 have compatible PASS evidence |
| 6 - Business-value pilot | The current implementation PR reports observed delivery economics and unchanged quality | Compare the retained baseline with PR #481 execution and unchanged authoritative full CI |

Elapsed results are observations, not fixed-duration guarantees. Avoided compute is reported only for
lanes that the dependency and cost model proves would otherwise have been eligible to run. A technical
PASS without the ordered outcome evidence does not complete the corresponding group.

### 14.8 WC-110 Integration Boundary

The authorized head `cccc2ad8306a512bf0f80c149c89b599a74160a2` is preserved before separation. Existing
WC-110 product work is not discarded or silently rewritten. Product behavior, product acceptance and
product-owned tests move under WC-110 authority; validation catalog, orchestration, identity, evidence
and qualification controls remain under WC-109 authority.

Independently executable WC-110 product corrections may merge through unchanged full CI before WC-109
freezes its candidate. A WC-110 consumer that genuinely requires unmerged WC-109 infrastructure must be
represented as an explicit stacked dependency with a product-only diff. After the applicable WC-110
base merges, PR #481 rebases on that authority and retains only the WC-109 control-plane implementation,
outcome remediation and pilot evidence in its candidate diff.

Historical component results remain diagnostic records. Rebase, scope separation or candidate-input
change invalidates every result whose complete identity no longer matches; no result is promoted merely
because the underlying test previously passed.

### 14.9 Current-PR Value Record

The PR #481 pilot reports, for the preserved baseline and remediated execution where comparable:

- time to first causal result and total elapsed distribution by cost class;
- affected lane-seconds suppressed after `FAIL` or `BLOCKED`;
- runner and product-image build counts by exact identity;
- focused, milestone and qualification invocation counts;
- failed, invalidated, resumed and replayed lane counts;
- deterministic first-cause recurrence and repair-loop count;
- Shadow selection false negatives against unchanged full CI; and
- final gate coverage and threshold preservation.

The retained rollback manifest records 43 attempted gates, 38 PASS results, five FAIL results,
2,833.434 observed gate-seconds, first failure after 1,901.640 gate-seconds and 931.601 gate-seconds
executed after that first failure. The pilot must preserve the source manifest and calculation method,
state concurrency and wall-clock limitations, and must not present summed gate-seconds as wall-clock
duration or customer-value realization.
