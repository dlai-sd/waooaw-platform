# WAOOAW Docker-Only Validation Strategy

**Status:** ACCEPTED BY FOUNDER - 2026-09-19; WC-108 AMENDMENT AUTHORIZED - 2026-09-29
**Owner:** Chief Enterprise Architect (INST-004)
**Work Contracts:** WC-101; WC-108
**Decision:** ADR-050
**Amends:** ADR-045 execution model; does not replace its per-stack runner boundaries

## 1. Purpose

WAOOAW is built and operated by AI agents. Its validation system must therefore optimize for short,
deterministic feedback and machine-readable evidence while preserving the clean execution boundary
required by C-080. Docker remains the only test execution environment; Docker image construction is
not required for every source edit.

This strategy governs platform engineering validation. It does not govern production container
topology or customer runtime behavior.

## 2. Architectural Basis

| Source | Architectural consequence |
|---|---|
| Capability 6.6 and 6.7 | Web and cloud delivery remain traceable to approved acceptance evidence |
| Quality Engineering capabilities 13.1-13.8 | Validation must be reproducible, risk-based, independently reviewable and evidence-bound |
| AD-002 / DP-001 | A PASS claim requires durable evidence before it is accepted |
| AD-006 / DP-020 | Resource economy may remove waste but may not reduce required quality |
| C-059 and C-086 | Requirements and the execution approach exist before implementation work |
| C-065 | The author validates but does not approve or merge its own work |
| C-071 and C-076 | Mandatory quality and coverage gates cannot be skipped for speed |
| C-080 | Every test and language test tool executes in a repository-defined Docker container |
| ADR-012, ADR-013 and ADR-045 | Use GHCR, GitHub Actions, immutable image identity and per-stack runners |

## 3. Verified Current-State Gaps

The current repository already has Python, .NET and TypeScript runner images, but execution is not
yet coherent:

1. CI rebuilds Compose test runners in multiple jobs instead of consuming one immutable runner
   identity.
2. The Business Platform unit job still uses the deprecated multi-stack runner.
3. The .NET Compose runner redirects NuGet packages to an ephemeral path different from the package
   path restored into its image.
4. The TypeScript runner does not mount workspace source, so local code edits require image rebuild.
5. The integration workflow invokes host `pytest`, `dotnet test`, database clients and Python scripts
   despite comments claiming C-080 compliance.
6. Some contract checks are advisory and target services that their job does not start.
7. No single machine-readable catalog owns path impact, reverse dependencies, required gates and
   evidence outputs.
8. Unit jobs primarily expose raw console output rather than one bounded, common failure envelope.

These are control-plane defects around Docker use, not evidence that Docker isolation should be
removed.

## 4. Target Architecture

```text
changed files + approved obligation ledger
                    |
                    v
       Validation Catalog and Selector
        direct owner + reverse dependencies
        unknown impact => full applicable set
                    |
          +---------+----------+
          |                    |
          v                    v
   Focused Agent Loop    Candidate Qualification
   workspace source      exact committed source
   dependency caches     clean state + digest binding
   local evidence only   PR/release evidence
          |                    |
          +---------+----------+
                    v
          Structured Result Envelope
                    |
                    v
        Required-Gate Evidence Aggregator
```

This is a repository and CI control plane, not a deployable service. It is implemented through
versioned manifests, Docker runner definitions, qualification scripts and GitHub Actions.

### 4.1 Four Independent Identities

| Identity | Complete authority inputs | Lifecycle |
|---|---|---|
| Runner | Toolchain Dockerfile, pinned base-image digest, installation scripts, system and language dependency lockfiles, runner policy, target architecture and platform | Build or pull once per exact identity. Ordinary application-source edits never invalidate it. |
| Test execution | Canonical mounted-source identity, runner digest, exact gate command, policy version, declared non-secret environment, service-image identities and disposable-state contract | Run in a stack-specific disposable container. It produces focused or milestone evidence, not release bytes. |
| Candidate | Complete `.dockerignore`-resolved build context, generated contract artifacts, Dockerfile frontend, build arguments, base digests and target platform | Build once per exact identity and immediately capture image digest, SBOM and provenance. |
| Evidence | Candidate or source identity, runner digest, command identity, policy identity, declared environment, schema, trust source and gate-specific freshness inputs | Reuse only on exact equality and deterministic non-impact proof; bind carry-forward to the new head. |

Identity manifests use structured parsing and deterministic canonicalization. Relevant content, path,
executable mode, symlink target, generated-artifact state, architecture, dirty state and untracked state
must be represented where they can affect the result. Raw secrets never enter an identity; a non-secret
authority or secret-version reference is included only when behavior depends on it.

Equality of one identity never implies equality of another. In particular, an unchanged runner does not
mean the candidate is unchanged, and an unchanged candidate does not make time-sensitive security or
provider evidence fresh.

### 4.2 Four-Tier Agentic Lifecycle

| Tier | Purpose | Required boundary | Evidence authority |
|---|---|---|---|
| 1 - Static preflight | Reject deterministic contract, syntax, policy, identity, mount, permission and output defects | Already-pinned micro-runner or stack runner; no runner/candidate build and no host test-language tooling | Diagnostic and planning only |
| 2 - Disposable story run | Fast feedback for the active requirement | Stack-specific disposable container, read-only mounted source where practical, isolated outputs and untrusted download caches | Focused local only |
| 3 - Milestone checks | Prevent late cross-component failure | Catalog-selected dependency-complete unit, component and integration checks at declared boundaries | Milestone only |
| 4 - Frozen-candidate qualification | Prove exact releasable bytes | Immutable candidate and runner digests, clean state, complete applicable inventory and hosted-only gates | PR/release when produced by the trusted boundary |

Performance budgets are pilot hypotheses until measured. They do not authorize skipping work, declaring
failure when a valid workload is slower, or promising a percentage saving. A repair after freeze creates
a new candidate identity; "one qualification" means one successful qualification attempt per immutable
candidate, not one attempt regardless of changed bytes.

## 5. Architectural Contracts

### 5.1 Validation Catalog

One versioned machine-readable catalog is the sole source for:

- source, test, fixture, specification and generated-artifact ownership;
- runner image and exact command for each check;
- direct gates and transitive reverse dependencies;
- required services, fixtures, secrets class and environment authority;
- timeout, resource class and permitted retry class;
- required result format and evidence retention; and
- global paths that force full applicable validation.

Selection uses the exact merge base and candidate head. Renames and deletions evaluate old and new
paths. Unknown paths, dependency cycles, parser failure or catalog disagreement fail closed to the
current full applicable gate set. The catalog may make a gate `NOT_APPLICABLE`; it may not mark a
required gate `PASS`.

### 5.2 Versioned Stack Runners

ADR-045's Python, .NET and TypeScript separation remains. Add browser and specialized security
runners only where their dependencies justify a separate boundary.

Each runner identity is derived from its Dockerfile, base-image digest, dependency manifests,
lockfiles, build arguments, architecture and platform. CI publishes the runner to GHCR by immutable
digest. Source code is not part of the runner identity and does not trigger a runner rebuild.

Mutable tags may be convenient aliases but are never evidence identity. If a trusted runner digest
is unavailable or its provenance cannot be verified, validation builds it once and records the new
identity; it does not silently use another image.

### 5.3 Two Execution Modes, One Test Definition

| Mode | Source and state | Permitted claim |
|---|---|---|
| Focused agent loop | Current workspace mounted read-only where practical; disposable container; named dependency/build caches | Developer feedback only |
| Candidate qualification | Exact 40-character commit; clean disposable test state; pinned runner digest; isolated outputs | PR or release evidence |

Both modes consume the same catalog entry and test command. The focused mode cannot redefine a test,
coverage threshold or fixture. A local PASS never substitutes for a required trusted CI result.

Persistent test containers and `docker cp` are prohibited as the standard loop because retained
process, database, filesystem or environment state can create false passes. Speed comes from reusable
runner images and bounded dependency/build caches, not from reusing correctness state.

### 5.4 Cache And State Authority

| State | Reuse rule |
|---|---|
| Package downloads and compiler caches | Reusable by namespaced input identity; acceleration only |
| Runner image layers | Reusable by verified immutable digest and provenance |
| Candidate service image | Built once per exact candidate identity; tests and scans consume that digest |
| Database, queues, test fixtures and browser state | Disposable unless a test explicitly proves reset and isolation |
| Coverage, test verdicts and failure summaries | Never reused as cache; may be reused only as immutable evidence with complete input equality |

A cache hit cannot authorize PASS. Failed, missing, stale, malformed or identity-mismatched evidence
fails closed.

Download and compiler caches must be namespaced by runner identity, platform and applicable lockfile
identity; concurrent writes require safe locking or isolation. They are size-bounded and integrity-checked,
and periodic clean-cache execution must remain possible. Executable dependency trees, generated output,
databases, browser state, process state and prior verdicts are not shared cache authority.

### 5.4.1 Candidate And Evidence Invalidation

A candidate changes when any effective build input changes, including application source, generated
contracts, Dockerfile/frontend, `.dockerignore` selection, build arguments, base digest or target platform.
The resulting digest, SBOM and provenance are captured together. Mutable workspace marker files cannot
stand in for candidate identity.

Evidence freshness is gate-specific. Vulnerability database state, provider state, external policy and
hosted environment identity are explicit inputs where relevant. Selection uncertainty broadens to the
full applicable inventory. Missing provenance, signature, identity or trust blocks the affected gate;
running more tests cannot manufacture the missing authority.

### 5.5 Structured Failure Evidence

Every validation node emits framework-native JUnit, TRX, JSON, SARIF or coverage output plus one
small common result envelope containing:

```yaml
schema_version: 1
base_sha: <40-character SHA>
head_sha: <40-character SHA>
runner_digest: <immutable OCI digest>
component: <owner>
gate: <stable gate ID>
command_id: <catalog entry, not a secret-bearing command line>
started_at: <UTC>
duration_ms: <integer>
result: PASS | FAIL | BLOCKED | NOT_APPLICABLE
failure_class: assertion | compile | coverage | security | infrastructure | configuration | none
first_cause: <bounded sanitized message>
raw_artifacts: [<paths>]
```

Provider tokens, secrets, customer data, authorization material and conversation content are never
included. The agent receives the envelope first and opens the bounded raw artifact only when needed.
Assertion, compilation, coverage and security failures are not retried automatically. Only catalogued
transient infrastructure failures receive a bounded retry.

The common routing classes are `RUNNER`, `WORKFLOW`, `PRODUCT`, `EXTERNAL` and `EVIDENCE`. Classification
selects the owning repair path but never converts failure to PASS. Bounded raw evidence remains available,
and an unchanged deterministic or infrastructure fingerprint cannot consume another costly attempt.

### 5.6 Gate Topology

Validation proceeds from cheapest to most discriminating:

1. catalog, specification, generated-contract and Docker-policy checks;
2. formatting, lint, type and compile checks;
3. tests directly mapped to the changed obligation;
4. owning-component unit and coverage gates;
5. affected contract, integration, browser, security and CCT gates;
6. one clean applicable qualification for the frozen candidate; and
7. complete `main` and release safety nets.

Independent nodes may run concurrently within explicit CPU, memory, disk and namespace limits. A
failure stops dependent work but does not hide already-running independent results.

### 5.7 Docker Isolation And Enforcement

All test commands and test-language tooling execute as non-root in repository-defined containers.
The Docker socket is exposed only to runners whose Testcontainers contract requires it, with an
explicit resource and trust classification. Each run receives unique Compose project, network,
container, volume, port and output namespaces.

A static policy gate rejects workflow or script changes that introduce host `pytest`, `dotnet test`,
`jest`, `playwright test`, package installation for test execution, or virtual-environment use. CI
orchestration scripts may use the host only where C-080 expressly permits them and they do not execute
tests or language validation.

## 6. Rollout

| Phase | Change | Authority |
|---|---|---|
| 0 - Compliance repair | Remove host test execution, non-root violations and invalid advisory checks | Implementation WC + Founder authorization |
| 1 - Runner supply | Publish digest-addressed stack runners; repair mounts and package-cache paths | Implementation WC + Founder authorization |
| 2 - Common evidence | Add catalog, focused command and structured result envelope | Implementation WC + Founder authorization |
| 3 - Shadow selection | Compare proposed affected set with unchanged full PR CI | Implementation WC + Founder authorization |
| 4 - Enforced selection | Use affected PR gates with fail-closed fallback; retain full `main` and release gates | Separate Founder approval after shadow evidence |
| WC-108 functional proof | Apply the four identities and four tiers to the next two eligible product PRs from implementation start | Separate implementation WC and current-session Founder authorization |

Rollback at every phase restores full clean qualification. No rollback may interpret newer evidence
under an older schema or retain a passing verdict whose inputs cannot be proven.

## 7. Measurable Outcomes

These are acceptance targets, not current claims:

| Outcome | Target |
|---|---|
| Docker-only compliance | Zero host test or test-language-tool invocations |
| Code-only runner rebuilds | Zero |
| Warm focused startup | 10 seconds or less before the selected command begins |
| Warm focused validation | 60 seconds or less for a representative single-component unit change |
| Duplicate runner builds | At most one per complete runner identity per workflow run |
| Impact-selection false negatives | Zero during shadow evaluation |
| Failure diagnosis | Common result envelope available in the original failed run without rerunning |
| Quality and coverage | No threshold, required gate or evidence-class reduction |

Baseline and candidate measurements must report medians, ranges, cache state and sample size for Web,
.NET, Python, shared-contract and global-workflow changes. Full qualification may remain longer than
five minutes; the architectural objective is to run it once per frozen candidate rather than after
every edit.

The WC-108 functional proof measures only the outcomes already promised by WC-100 through WC-106:
elapsed validation time, repeated builds, first-pass precheck result, repair-loop count and preserved
quality. Two PRs prove operability but do not establish a trend or authorize selective hosted validation.
Already-advanced PRs are excluded because their implementation history cannot provide a clean baseline.

## 8. Solution Architecture Handoff

After Founder acceptance, Solution Architecture must reconcile the existing WC-100 draft against
ADR-050 and this strategy. The resulting implementation contract must atomize at least:

1. current C-080 compliance repair;
2. runner publication, digest and cache behavior;
3. focused and qualification commands using the same catalog entries;
4. catalog ownership, reverse dependencies and fail-closed rules;
5. structured result envelope, redaction and artifact retention;
6. non-root, resource, namespace and Docker-socket controls;
7. shadow measurement and separate activation authority; and
8. rollback to full clean qualification.

The contract must preserve WC-100 requirements that are consistent with this architecture, remove
duplication, identify any conflict explicitly, and retain current full CI until shadow evidence and
Founder approval authorize selective enforcement.

## 9. Enterprise Architecture Author Review

The strategy was reviewed for requirements coverage, existing-ADR compatibility, trust boundaries,
failure modes, security, operability, reversibility, evidence semantics and measurable outcomes. It
uses existing repository and CI technologies, adds no runtime service, keeps clean qualification as
the authority boundary and fails closed whenever reuse or impact cannot be proven.

**Disposition:** ACCEPTED BY FOUNDER 2026-09-19.
