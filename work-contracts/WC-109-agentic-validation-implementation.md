# WC-109 - Agentic Validation Control Plane Implementation And Pilot

## Record Control

| Field | Value |
|---|---|
| Authoring office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-29 continuous working session |
| Implementation authorization | Explicit Founder confirmation in the 2026-09-29 continuous working session |
| Status | AUTHORIZED - SOLUTION ARCHITECTURE COMPLETE - IMPLEMENTATION NOT STARTED |
| Required predecessor | WC-108 merged with ADR-050 and Docker validation strategy amendments intact |
| Governing decision | ADR-050 as amended by WC-108 |
| Constitutional basis | C-023, C-059, C-065, C-071, C-076, C-077, C-080 and C-086 |
| Implementing office | Platform IT Expert (INST-012) |
| Architecture reviewer | Enterprise Architect (INST-004) |
| Branch after predecessor merge | `wc/109-agentic-validation-implementation` |
| Completion boundary | Control-plane implementation plus bounded two-PR pilot evidence |

## 1. Objective

Implement the repository and CI control plane specified by WC-108 so an AI implementation agent can
obtain fast, disposable Docker feedback without rebuilding validation runners or product images for
ordinary source edits, while final authority remains bound to one immutable release candidate and the
complete applicable qualification inventory.

The delivery must operationalize four independent identities and four ordered tiers without changing
ADR-050, weakening a gate, moving test execution onto a host, or enabling selective hosted validation.

## 2. Authority And Preconditions

This Work Contract authorizes implementation only after WC-108 is merged and the implementation branch
is rebased on that merged authority. If WC-108 changes during review, the Solution Architect must assess
this contract before implementation starts; material conflict returns the contract to Enterprise
Architecture rather than being resolved in code.

Current-session Founder authorization permits the bounded implementation and validation described here.
It does not authorize deployment, customer traffic, cloud mutation, new paid services, Production access,
selective hosted-validation enforcement, self-approval or self-merge.

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
- bounded pilot instrumentation and evidence for the next two eligible product PRs that begin after
  the implementation becomes available.

### 3.2 Out of scope

- product behavior changes in `src/` or `web/` except separately authorized pilot PR work;
- alteration of ADR-050, WC-108 or any ratified constitutional claim;
- replacement of the existing language-specific runner model with one generic persistent executor;
- persistent test processes, databases, browsers, generated outputs or verdicts as correctness state;
- a new deployable service, database, queue, cloud resource or third-party test-impact platform;
- Production deployment, customer traffic, registry retention-policy mutation or cloud-provider mutation;
- reduction of tests, thresholds, security checks, CCTs, author review or Founder review;
- selective hosted-validation enforcement or removal of current full `main` and release safety nets;
- unsupported fixed-duration or percentage-saving commitments; and
- treating the two-PR pilot as statistical trend proof.

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

A Tier 2 or Tier 3 PASS cannot be promoted to Tier 4 authority. A repair after candidate freeze creates a
new candidate identity and invalidates affected qualification evidence.

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

The recorder produces one comparable record for each of the next two eligible product PRs beginning after
the implementation is available. Already-advanced PRs are excluded. Each record must include:

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
| 4 - Candidate qualification | Stage 3 PASS | Freeze/build/bind route, SBOM/provenance binding and Tier 4 qualification | Exact candidate consumes complete applicable inventory |
| 5 - Hosted shadow operation | Stage 4 PASS | Hosted policy enforcement and selection shadow comparison | Full CI remains authoritative; zero unresolved false negatives in observed runs |
| 6 - Two-PR pilot | Stage 5 PASS | Two complete pilot records | Both records satisfy Section 8 without unsupported extrapolation |
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

Both eligible pilot PRs must satisfy all applicable conditions:

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
| WC109-R010 | Tier 3 executes dependency-complete checks only at declared milestone boundaries. |
| WC109-R011 | Tier 4 qualifies one immutable candidate against the complete applicable inventory. |
| WC109-R012 | A post-freeze repair creates a new candidate and invalidates affected evidence. |
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
| WC109-R031 | Two eligible product PRs produce complete comparable pilot records. |
| WC109-R032 | Pilot reports observations and limitations without unsupported percentage or fixed-duration claims. |
| WC109-R033 | Pilot comparison has zero unresolved selection false negatives and no quality reduction. |
| WC109-R034 | Rollback restores full clean qualification without reinterpreting incompatible evidence. |
| WC109-R035 | Selective hosted validation remains disabled pending separate Founder approval. |
| WC109-R036 | Author review, independent Enterprise Architecture review and Founder merge authority remain separate. |

## 10. Definition Of Done

WC-109 is DONE only when:

- all 36 ledger requirements are PASS with direct source and executable evidence;
- all four identities and tiers operate through the catalog-controlled route;
- the complete Docker validation suite and current full qualification pass against the frozen candidate;
- no applicable quality, security, coverage, CCT or evidence threshold is weakened;
- both eligible pilot PR records satisfy Section 8;
- every partial, deferred, untested or externally blocked obligation remains visibly not PASS;
- the implementing office completes a requirement-by-requirement author review;
- the Enterprise Architect independently reviews architectural conformance; and
- the Founder receives the exact-head evidence package for review and merge.

Passing tests, implementation-shaped mocks, one pilot PR, a smaller substitute, or elapsed-time
improvement cannot compensate for an incomplete normative requirement.

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
