# WC-108 - Agentic Validation Operating Model

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Enterprise Architect (INST-004) |
| Assigned and authorized by | Founder instruction in the 2026-09-29 continuous working session |
| Status | ARCHITECTURE AND GOVERNANCE DOCUMENTATION PASS COMPLETE - IMPLEMENTATION NOT AUTHORIZED |
| Baseline | `origin/main` at `c7cd13c21cc9ccedbb222d8a214774b626bf40db` |
| Governing decision | ADR-050, accepted by Founder on 2026-09-19 |
| Prior delivery evidence | WC-100, WC-101, WC-102, WC-104 and WC-106; PRs #462, #464, #467, #468, #476 and #478 |
| Constitutional basis | C-023, C-059, C-065, C-071, C-076, C-077, C-080 and C-086 |
| Delivery unit | One bounded architecture, decision, claim-interpretation and implementation-process documentation amendment |

## 1. Objective

Amend WAOOAW's accepted Docker validation architecture so AI-assisted implementation receives fast,
disposable feedback without rebuilding validation runners or product images for ordinary source edits,
while exact-candidate qualification, constitutional quality gates and evidence authority remain intact.

The amendment must make four identities independent and explicit:

1. runner identity;
2. test-execution identity;
3. candidate identity; and
4. evidence identity.

It must also establish four ordered execution tiers: static preflight, disposable story run, bounded
milestone checks and frozen-candidate qualification. Optimization is subordinate to correctness. An
unknown input, uncertain impact, stale identity or untrusted provenance never authorizes PASS.

## 2. Authority And Scope

The Founder authorized the Chief Enterprise Architect to perform a lightweight constitutional
documentation pass covering the accepted validation architecture, ADR-050, applicable ratified-claim
interpretation, and the Platform IT Expert implementation process. This Work Contract authorizes only
mutable documentation and its machine-readable requirement ledger.

### In scope

- amend ADR-050 without changing its accepted Docker-only, fail-closed or full-qualification decision;
- amend `architecture/reference/docker-only-validation-strategy.md` with the four-identity model,
  tiered lifecycle, cache boundaries, pilot controls, failure taxonomy and rollback;
- clarify C-080's architectural interpretation without changing its ratified statement;
- trace C-077 and C-086 as supporting obligations without extending their ratified scope;
- amend the Platform IT Expert specification and compact office card so implementation begins with
  mounted-source focused checks and does not build a product image per story;
- update compact indexes and versions required to route later agents to the amended authority;
- define a bounded pilot using the same promised outcome parameters already established by WC-100
  through WC-106; and
- create and validate `work-contracts/WC-108-requirements.yaml`.

### Out of scope

- changes to `constitution/CONSTITUTION.md` or `constitution/GENESIS.md`;
- creation of a new constitutional claim or alteration of a ratified claim statement;
- changes to `src/`, `web/`, tests, workflows, Dockerfiles, Compose files, validation scripts or the
  machine-readable validation catalog;
- execution of the pilot, image build, registry publication, cloud mutation, deployment or customer
  traffic;
- activation of selective hosted validation;
- reduction, waiver or replacement of any quality, coverage, security, CCT, author-review, Founder
  review or merge gate; and
- unsupported promises for percentage savings, fixed test duration or one-run completion.

Any runnable implementation requires a separate Work Contract and explicit current-session Founder
authorization under the implementation gate.

## 3. Required Inputs

| Input | Required state | Use |
|---|---|---|
| C-023, C-059, C-065, C-071 and C-076 | Ratified | Evidence, traceability, separation and quality floors |
| C-077 | Ratified | Development-agent economy and retry-cost constraint |
| C-080 | Ratified | Docker-only test execution constraint |
| C-086 | Ratified | Pre-execution proof for new autonomous generation approaches |
| ADR-045 | Accepted | Existing per-stack lean runner boundary |
| ADR-050 | Founder accepted | Controlling AI-operated Docker validation decision |
| `architecture/reference/docker-only-validation-strategy.md` | Present and controlling | Detailed architecture amendment target |
| WC-100, WC-102, WC-104 and WC-106 requirement ledgers | Present | Promised outcomes, unresolved evidence and implementation history |
| Latest seven WAOOAW agent sessions through 2026-09-29 | Available | Observed repeated-build, precheck and repair-loop evidence |
| PR and batch evidence for #462, #464, #467, #468, #476, #478 and #479 | Available | Hosted delivery and consumer proof |

All required documentation inputs are present. Runtime implementation and pilot evidence do not yet
exist and must not be represented as completed by this documentation pass.

## 4. Governing Architecture Contract

### 4.1 Independent identities

| Identity | Mandatory authority inputs | Required lifecycle behavior |
|---|---|---|
| Runner | Toolchain Dockerfile, pinned base-image digest, installation scripts, system and language dependency lockfiles, target platform and approved runner policy | Build or pull once per exact identity. Ordinary application-source edits do not invalidate it. |
| Test execution | Mounted-source identity, runner digest, exact gate command, policy version, declared non-secret environment, service-image identities and disposable-state contract | Execute in a stack-specific disposable container. Package download caches may accelerate; process, database, generated-output and verdict state may not persist as correctness authority. |
| Candidate | Complete `.dockerignore`-resolved application build context, generated contract artifacts, Dockerfile frontend, build arguments, base digests and target platform | Build once per exact candidate identity. Capture image digest, SBOM and provenance before qualification. Any changed candidate input creates a new candidate. |
| Evidence | Candidate or source identity, runner digest, command identity, policy identity, declared environment, evidence schema, trust source and gate-specific freshness inputs | Reuse only after exact equality and non-impact proof. Bind reused evidence to the new head without representing it as fresh execution. |

Identity manifests must use structured parsing and deterministic canonicalization. They must account
for file content, path, executable mode, symlink target, generated-artifact state, architecture and
dirty or untracked state where those inputs can affect execution. Raw secrets must never enter an
identity manifest; a non-secret secret-version or authority reference may be included when behavior
depends on it.

### 4.2 Four execution tiers

| Tier | Purpose | Permitted execution | Authority |
|---|---|---|---|
| 1 - Static preflight | Reject deterministic contract, syntax, policy, identity, mount, permission and output defects before costly work | Already-pinned micro-runner or stack runner; no test-language host execution and no runner or candidate build | Diagnostic and planning evidence only |
| 2 - Disposable story run | Give immediate feedback for one active requirement | Stack-specific `docker compose run --rm` equivalent with read-only mounted source, isolated writable outputs and declared download caches | Focused local evidence only |
| 3 - Milestone checks | Detect bounded cross-component and contract failures before final freeze | Dependency-complete affected unit, component and integration gates selected from the catalog | Milestone evidence; not final qualification |
| 4 - Frozen-candidate qualification | Prove one exact candidate against the complete applicable inventory | Immutable candidate and runner digests, clean disposable state, required hosted-only gates and exact-head author review | PR/release authority when produced inside the trusted boundary |

Budgets such as five-second preflight, ten-second unit feedback, sixty-second component feedback and
nine-to-twelve-minute qualification are measurement hypotheses, not constitutional gates or success
claims. The pilot records observed distributions and does not conceal slower valid workloads.

### 4.3 Build and cache policy

- Ordinary source edits MUST NOT build a runner or product image during Tier 2.
- A runner build is permitted only when a declared runner input identity changes or a trusted artifact
  for that exact identity is unavailable.
- A candidate build is permitted only at candidate freeze or when a declared candidate input changes.
- "Build once" means once per exact immutable identity, not once per Work Contract or branch.
- A repair after candidate freeze creates a new candidate identity and requires new affected evidence
  plus final qualification.
- Package download and compiler caches are untrusted accelerators. They must be namespace-isolated,
  concurrency-safe, size-bounded and integrity-checked.
- Executable dependency trees, generated output, databases, browser state, process state and prior
  verdicts must not become shared cache authority.
- Registry reuse requires immutable digest resolution, provenance verification, retention and a
  documented recovery rebuild path. Registry or attestation uncertainty blocks reuse.

### 4.4 Selection and evidence policy

- One versioned catalog owns gate commands, runner assignment, direct ownership, reverse dependencies,
  resources, evidence format and lifecycle applicability.
- Unknown paths, missing owners, cycles, malformed policy or ambiguous impact select the complete
  applicable inventory.
- Identity, provenance, signature, secret or trust ambiguity blocks the affected gate; a broader run
  cannot manufacture missing authority.
- Evidence carry-forward requires a deterministic non-impact proof across the exact commit range and
  records `executed`, `exact-candidate-reuse` or `verified-carry-forward` explicitly.
- Gate-specific freshness inputs include vulnerability databases, provider state, external policy,
  environment identity and other time-sensitive authorities where applicable.
- Local or cached success never substitutes for required hosted, provider-backed, deployed or
  customer-traffic acceptance.

### 4.5 Failure handling

Every failed node must retain bounded raw evidence and one routing classification:

- `RUNNER` - image, toolchain, UID/GID, mount, cache, socket or container-runtime defect;
- `WORKFLOW` - orchestration, hosted-job, permission or lifecycle placement defect;
- `PRODUCT` - application behavior, contract, test or generated-client defect;
- `EXTERNAL` - registry, package service, provider, cloud or network dependency defect; or
- `EVIDENCE` - stale, missing, malformed, untrusted or unpublished proof.

Classification routes repair ownership only. It never changes a failure to PASS. The first causal
failure must be visible without requiring a complete rerun, and unchanged deterministic or
infrastructure failure fingerprints must not consume another costly attempt.

## 5. Platform IT Expert Operating Contract

For every later implementation Work Contract, Platform IT Expert must:

1. validate the Work Contract ledger and selected requirement before execution;
2. resolve the current runner digest without building it for ordinary source changes;
3. run Tier 1 before any costly node;
4. implement one coherent story group and use Tier 2 focused evidence;
5. run Tier 3 only at declared dependency boundaries, not after every edit;
6. freeze one candidate only after all authorized local stories and required milestone checks pass;
7. build each changed candidate image once per exact identity;
8. perform Tier 4 once per immutable candidate, accepting that a repair creates a new candidate;
9. classify and repair only the first causal owning layer while preserving unaffected trusted evidence;
10. report actual observed timing, build, first-pass and repair-loop results without extrapolation.

Direct diagnostic Docker commands remain possible for diagnosis but cannot emit authoritative PASS.
The catalog executor and hosted policy enforcement, not agent instruction alone, are the authority
boundary.

## 6. Bounded Pilot Contract

The operating model must be proven on the next two eligible product PRs from the beginning of their
implementation. Already-advanced PRs cannot establish a clean baseline. Pilot execution requires a
separate implementation Work Contract and current-session Founder authorization.

The pilot uses only the promised outcome parameters from WC-100 through WC-106:

| Outcome | Current evidence | Pilot success condition |
|---|---|---|
| Fast, predictable validation | WC-100 historical hosted median 278 seconds across five samples; candidate hosted comparison incomplete | Report comparable observed distributions across both pilot PRs; show material improvement without asserting an unmeasured percentage |
| Repeated builds | Repeated runner and full-image work observed during later product sessions | Zero runner or product-image builds for ordinary Tier 2 source edits; at most one build per exact runner or candidate identity |
| Precheck reliability | Known late failures included UID/HOME, output ownership, socket, host-versus-container placement, stale evidence and transient dependency transport | Zero recurrence of a modeled failure; each new failure gains one bounded regression fixture in its owning repair |
| Repair loops | Multiple post-qualification and hosted precheck repairs occurred in recent delivery | First-pass rate and repair-loop count are reported per PR and improve against comparable recent work |
| Quality preservation | Final authoritative inventories passed after repair | 100% required final-gate coverage, zero accepted selection false negatives and no weakened threshold |

Two PRs provide functional proof, not statistical certainty and not authority to enable selective
hosted validation. Selective enforcement remains subject to ADR-050's representative shadow window,
zero unresolved false negatives and separate Founder approval.

## 7. Canonical Requirement Index

| Requirement | Normative outcome |
|---|---|
| WC108-R001 | ADR-050 explicitly distinguishes runner, test-execution, candidate and evidence identities. |
| WC108-R002 | Runner identity excludes ordinary application source and includes every environment-producing input. |
| WC108-R003 | Test execution is stack-specific, disposable and isolated from persistent correctness state. |
| WC108-R004 | Candidate identity covers the complete effective build context and produces digest, SBOM and provenance. |
| WC108-R005 | Evidence reuse requires exact declared inputs, trust, freshness and new-head non-impact proof. |
| WC108-R006 | Static preflight precedes costly execution without using host language test tooling. |
| WC108-R007 | Story feedback uses mounted source and does not build runners or product images for ordinary edits. |
| WC108-R008 | Milestone checks are dependency-complete and bounded rather than full qualification after every edit. |
| WC108-R009 | Full qualification occurs once per immutable candidate identity, and every repair creates a new candidate. |
| WC108-R010 | Cache policy separates untrusted download acceleration from disposable correctness state. |
| WC108-R011 | Unknown impact fails closed to full applicable validation, while trust ambiguity blocks rather than fabricates authority. |
| WC108-R012 | Failure evidence uses bounded routing classes without converting infrastructure failure into PASS. |
| WC108-R013 | Platform IT Expert process enforces the four-tier order and reports story-level evidence before advancing. |
| WC108-R014 | Direct Docker commands cannot produce authoritative evidence outside the catalog executor. |
| WC108-R015 | Pilot measures the same speed, build, precheck, repair-loop and quality outcomes promised by prior contracts. |
| WC108-R016 | Pilot targets are reported as observations, not unsupported percentage or fixed-duration guarantees. |
| WC108-R017 | Selective hosted validation remains disabled until ADR-050 shadow proof and separate Founder approval. |
| WC108-R018 | C-080 interpretation permits mounted source only inside Docker and requires disposable test execution without changing the ratified claim statement. |
| WC108-R019 | C-077 and C-086 retain their ratified scope and are traced without being expanded by architecture documentation. |
| WC108-R020 | No implementation, cloud, registry, deployment, approval or merge authority is inferred from this documentation pass. |

## 8. Required Outputs

1. This Work Contract and its validated requirement ledger.
2. An in-place amendment to ADR-050; no redundant ADR.
3. An in-place amendment to `architecture/reference/docker-only-validation-strategy.md`.
4. A bounded architectural interpretation note in C-080; C-077 and C-086 remain unchanged.
5. Platform IT Expert specification and compact office-card process amendments.
6. Required compact index/version updates.
7. Documentation validation and complete Enterprise Architecture author review.

## 9. Definition Of Done

- Every WC108 requirement has one independently reviewable ledger row with source, owner, evidence,
  completion rule, result and residual risk.
- ADR-050 and the detailed strategy state the same four identities, tiers, trust boundaries and pilot
  authority without contradiction.
- Claim interpretation does not alter a ratified statement or create new constitutional authority.
- Platform IT Expert instructions prohibit per-story image builds and broad qualification while code is
  still changing, while preserving bounded milestone integration and final qualification.
- All updated Markdown, YAML, references, versions and policy checks pass through repository Docker
  validation where available.
- Author review covers requirements, assumptions, identity completeness, cache poisoning, concurrency,
  secrets, supply chain, hosted divergence, rollback, authority and downstream effects.
- No source, test, workflow, Docker, Compose, catalog, cloud or deployment artifact changes.

## 10. Stop Conditions

Stop rather than proceed if the documentation would:

- modify a Class 1 immutable record;
- invent or alter a ratified constitutional claim statement;
- require a new technology decision rather than an ADR-050 clarification;
- weaken Docker-only execution, quality gates, coverage, security, author review or Founder authority;
- authorize selective validation without the required shadow evidence;
- authorize implementation, image publication, registry mutation, cloud action or deployment;
- treat cache, local output, broader execution or unsupported timing claims as PASS authority; or
- require source-code inspection or modification by the Enterprise Architect.

## 11. Rollback

Revert the bounded documentation commit. ADR-050's previously accepted full-clean Docker validation
model remains authoritative. No runtime, image, registry, workflow, cloud, schema or customer-data
rollback is required.
