# Foundation Environment Promotion And Freeze - Executable Delivery Plan

**Office:** Chief Solution Architect (INST-005)
**Work Contract:** WC-081
**Status:** AUTHOR-REVIEWED SOLUTION PLAN CANDIDATE - FOUNDER REVIEW; IMPLEMENTATION AND CLOUD
EXECUTION REQUIRE SEPARATE CURRENT-SESSION AUTHORIZATION
**Execution office:** Platform IT Expert (INST-010), Skills 1-9 and 11-17, with Skill 17 controlling
cloud delivery
**Delivery unit:** Preserve the accepted Demo/UAT cloud baseline, consolidate strategy and workflow
references, and complete dark Production readiness without activation
**Reference architecture:** `architecture/foundation-consolidated-assessment-2026-08-29.md` and
`architecture/reference/pipeline/azure-deployment-topology.md`
**Constitutional basis:** C-001, C-002, C-003, C-005, C-007, C-023, C-025, C-032, C-035, C-049,
C-059, C-063, C-065, C-067, C-071, C-076, C-077, C-080
**Architectural decisions:** ADR-012, ADR-013, ADR-014, ADR-015, ADR-027, ADR-031, ADR-047

## 1. Objective

Complete the Foundation environment freeze from the accepted PR #371 cloud-delivery baseline:

```text
PR #371 ACCEPTED BASELINE
  -> DEMO PRIVATE DEPLOYMENT AND FOUNDER ACCEPTANCE [COMPLETE]
  -> UAT SAME-RELEASE DEPLOYMENT AND INDEPENDENT VERIFICATION [COMPLETE]
  -> ONE CANONICAL STRATEGY AND DEPLOYMENT ENTRY [DOCUMENTATION CONSOLIDATION]
  -> DARK PRODUCTION READINESS PLAN WITH ZERO ACTIVATION [REMAINING]
```

The same immutable application images must move from Demo to UAT and, under a later authority, to
Production. Environment values, endpoints, identities, secret references, cost inputs, lease data,
and policy parameters must remain outside the images in reviewed environment configuration and Key
Vault references. Promotion changes environment configuration and deployment evidence, never image
content or image identity.

This plan is self-sufficient for future Platform IT work. It defines the required repository changes,
validation economy, Production-readiness proofs, evidence, rollback, and stops while treating the
merged Demo/UAT evidence as immutable input rather than work to repeat. It does not authorize
implementation, provider access, expenditure, deployment, Production, acceptance, PR approval, or
merge.

## 2. Required Outcome

| Boundary | Required outcome | Prohibited outcome |
|---|---|---|
| Release | One signed manifest with exactly six digest-pinned first-party images, attestations, SBOMs, source commit, dependency manifest, and schema compatibility | Per-environment rebuild, mutable tag authority, silent seventh member, or digest substitution |
| Configuration | Versioned non-secret schema plus reviewed per-environment document digest and Key Vault/managed-identity references | Environment value, endpoint, credential, secret, or tenant data baked into an image |
| Runner | Ephemeral environment-scoped ACA runner, private state/config path, independent cleanup, zero idle capacity | Long-lived runner, public state path, cross-environment identity, or public fallback |
| Demo | Preserve the Founder-accepted private deployment and evidence as an immutable regression baseline | Reconstruct acceptance from prose or overwrite failed-attempt evidence |
| Acceptance | Preserve the Founder record and exact release/configuration/evidence binding established before UAT | Acceptance by executor, workflow success alone, mutable reference, or undocumented inference |
| UAT | Preserve the independently verified private-runner and exact-six deployment as a Production-readiness input | Rebuild, Demo state/identity/data reuse, or claim unproven recovery/rollback evidence |
| Production | Validated dark plan and readiness ledger with zero runner capacity, apply, DNS activation, secret seeding, or traffic | Production mutation or customer exposure under WC-081 |

The promoted release tuple is:

```text
signed manifest
+ exactly six immutable image digests
+ signed pinned-dependency manifest
+ reviewed environment configuration digest
+ additive-schema compatibility result
+ SHA-256-addressed qualification evidence
+ environment acceptance record
```

## 3. Entry Gates And Required Inputs

Execution may start only when every input for the selected stage is present, accepted, exact, and
non-contradictory.

| Input or authority | Required state | Validation |
|---|---|---|
| WC-081 and this plan | Founder accepted | Exact path and accepted commit recorded |
| WC-076 authority | Present and accepted through the PR #371 execution baseline | Work Contract and finalization evidence resolve Demo/UAT chronology |
| Current-session implementation authority | Explicitly granted | Founder names Platform IT session, issue, branch, paths, and stage |
| Cloud/provider authority | Explicit and stage-specific | Allowed subscription, environment, query/plan/apply/deploy actions, time window, and spend bound recorded |
| Project state | Current and compatible | GOAL-006 stage, blockers, acceptance history, and Production prohibition agree |
| Controlling architecture | Accepted | Azure topology and ADR-047 unchanged or accepted amendments linked |
| Owner contracts | Executable | Platform, Security, Data, QA, configuration, CCT, recovery, and cost inputs are versioned |
| Implementation issue | Founder assigned | Exact files, tests, proof IDs, branch, estimate, rollback, stops, and acceptance actor named |
| Toolchain | Repository pinned | Docker/BuildKit, Compose, Terraform 1.9.8 where current workflow requires it, Python test image, Syft 1.27.1, Trivy 0.65.0, Gitleaks 8.28.0, and Spectral 6.15.0 available |

The current repository contains the accepted PR #371 implementation: `deploy.yaml` is the sole
manual application deployment entry, Demo is Founder-accepted, UAT is deployed and independently
verified, and Production remains code-prepared but plan-only. Repository state still does not grant
new implementation or provider authority.

### 3.1 Owner Handoff Before Platform IT Execution

| Owner | Required accepted output |
|---|---|
| Founder | WC-081 acceptance and any future implementation, Production plan/provider, activation, DNS, traffic, or acceptance authority |
| Platform Architect | Exact-six release membership, environment topology, service/dependency boundaries, environment configuration schema, and workload interface contract |
| Solution Architect | This sequence, promotion tuple, workflow interfaces, failure behavior, rollback, acceptance matrix, and Production-dark boundary |
| Security Architect | OIDC subjects, managed identities, runner App manifest, RBAC, NSG, DNS, Key Vault, egress, secret handling, denial tests, and incident holds |
| Data Architect | Environment databases/roles, RLS, additive migrations, backup/PITR, restore, retention, schema compatibility, and rollback data contract |
| QA/Test Champion | Stage CCT set, internal/public probes, recovery and cancellation scenarios, coverage thresholds, and evidence schema |
| Product/Founder | Founder Demo acceptance scenario, approved tester scope for UAT, lease windows, and externally meaningful acceptance criteria |

Platform IT verifies these inputs and implements them. It does not repair missing owner policy by
choosing values in Terraform, workflows, scripts, or environment variables.

### 3.2 Platform IT Expert Skill Binding

| Skill | Required application |
|---|---|
| 1-4 | Freeze the issue contract, validate authority, create the assigned branch, and implement only accepted paths |
| 5-6 | Run endpoint-focused tests during development and one final coverage/static/security campaign |
| 7-8 | Maintain reusable protected workflows, then create one complete Founder-ready PR for each authorized stage |
| 9 | Independently verify deployed tuple, runtime health, journeys, rollback, recovery, isolation, lease, and evidence |
| 11 | Update only required owning records and exact evidence links after executable proof |
| 12-15 | Preflight Docker capacity, reuse hash-tagged images, externalize values/secrets, inspect failures, and validate YAML/structured contracts |
| 17 | Implement private runners, Terraform/Azure, OIDC/RBAC, immutable promotion, rollback, observability, lifecycle, cost, and cloud evidence exactly as accepted |

## 4. Scope

### 4.1 In Scope

- consolidate current cloud strategy in `architecture/reference/pipeline/azure-deployment-topology.md`;
- keep README as operator routing, PROJECT_STATE as current status, WC-076 as execution closure, and
  the finalization evidence as immutable run detail;
- preserve `deploy.yaml` as the sole manual application deployment entry and the existing reusable
  deployment, independent verification, runner delivery, qualification, and lease responsibilities;
- identify historic or orphaned workflows without deleting unique governance controls; any future
  workflow consolidation requires explicit implementation authorization and contract tests;
- retain Demo/UAT exact-six, external configuration, private-runner, cleanup, and verification
  evidence as regression inputs;
- implement external non-secret configuration schemas and environment manifests whose digests bind to
  the release while all secret values remain in Key Vault;
- complete additive migration, pre-traffic verification, blue-green switch, compatible rollback,
  failed-revision retention, and lease expiry automation;
- implement one deterministic local/Docker qualification entry point that emits final JSON directly;
- close only remaining UAT recovery/rollback evidence gaps required by the accepted Production gate;
- produce a dark Production plan/readiness ledger without mutation or activation.

### 4.2 Out Of Scope

- new cloud architecture, regions, services, SKUs, DNS policy, cost limits, SLOs, RPO/RTO, or security
  exceptions;
- application feature development unrelated to deployment readiness;
- changing exact-six first-party membership;
- long-lived credentials, exported GitHub App private keys, shared environment identity, shared state,
  copied Production data, or secret-bearing Terraform inputs/state;
- UAT before Founder Demo acceptance;
- Production runner activation, apply, DNS, customer traffic, acceptance, or merge.

## 5. Environment And Promotion Contract

### 5.1 Environment Isolation

Demo, UAT, and Production each have distinct GitHub Environments, OIDC subjects, runner groups and
labels, VNets/subnets, NSGs, managed identities, resource groups, Terraform state keys/accounts as
accepted, configuration prefixes, Key Vaults, PostgreSQL data, DNS records, Log Analytics evidence,
budgets, leases, and verification identities. No environment credential or role is valid in another.

One versioned environment manifest supplies non-secret identifiers and expected resource IDs. It is
schema-validated, approved, SHA-256-addressed, and selected by an allowlisted environment key. Free
form workflow overrides are prohibited. Secret references name Key Vault objects but never contain
secret values.

### 5.2 Immutable Release Identity

CI builds the exact-six images once from one final source commit. Every first-party image reference is
`ghcr.io/...@sha256:...`. Source/config hash tags may provide local human-readable identity, but tags
are never deployment or promotion authority. Demo, UAT, later Production, and rollback verify the
same manifest and image digests before mutation and against live inventory afterward.

The environment configuration digest may differ because access, endpoints, identities, cost, lease,
and dependencies are environment-specific. Any application image digest difference is a new release,
which must return to Demo.

### 5.3 Acceptance Chronology

1. Repository qualification establishes implementation readiness only.
2. Authorized Demo plan establishes expected resource change without accepting effectiveness.
3. Authorized Demo apply and independent verification establish technical evidence.
4. Founder accepts or rejects the exact Demo tuple and evidence.
5. Only an explicit accepted record unlocks a separately authorized UAT plan/apply.
6. UAT qualification establishes Production readiness evidence, not Production authority.
7. Production remains dark until a separate Founder Work Contract and activation decision.

## 6. Security, Isolation, And Operability

- preserve ADR-047's GitHub-hosted management job, non-exportable Key Vault signing key, short-lived
  registration material, ephemeral ACA runner, separate cleanup identity, scheduled reconciler,
  correlation key, 60-minute execution bound, and five-minute orphan SLA;
- validate the live GitHub App against the exact permission manifest before token issuance;
- block before runner creation on template/parameter digest mismatch, destructive what-if, unexpected
  ownership, stale cost, public Storage answer, DNS mismatch, cross-environment grant, or drift;
- prove private DNS and exact Blob/Terraform backend list/read/write/lock operations, plus RBAC,
  routing, and TCP denial for every forbidden source/target environment pair;
- use environment deployment and independent verification identities that cannot impersonate each
  other; workload identities receive only their own Key Vault references;
- retain logs, plans, inventory, denied requests, cleanup records, cost data, failed attempts, and
  evidence digests without customer payloads or secrets;
- keep workloads at minimum zero outside active leases, stop non-Production PostgreSQL, and reconcile
  Azure's automatic server restart behavior;
- fail closed when CE, identity, migration, data, cost, security, recovery, or evidence dependencies
  are unavailable; no readiness probe may overclaim dependency or constitutional readiness.

## 7. Canonical Artifacts To Produce Or Amend

The implementation issue must bind exact paths. The expected owning surfaces are:

| Surface | Required result |
|---|---|
| `work-contracts/WC-076-goal006-phase3-execution.md` | Demo/UAT execution closure and remaining P3-EX11 status |
| `.github/workflows/deploy.yaml` | Sole manual application deployment entry using the current-main signed release |
| `.github/workflows/deploy-environment.yaml` | Environment-parameterized reusable deployment engine |
| `.github/workflows/post-deploy-verify.yaml` | Independent environment-parameterized verification and complete evidence output |
| `.github/workflows/runner-environment-delivery.yaml` | Reviewed private-runner preview/apply lifecycle, distinct from application deployment |
| `.github/workflows/goal006-private-runner-qualification.yaml` | Private-path diagnostics, distinct from deployment and acceptance |
| `.github/workflows/reconcile-workload-leases.yaml` | Idempotent scale-to-zero/server-stop lease reconciliation and evidence |
| `infrastructure/deployment-stacks/goal006-runner/` | Versioned per-environment runner manifests/templates and activation proof inputs |
| `infrastructure/terraform/phase2/environments/` | Isolated Demo/UAT roots and dark Production plan roots using accepted modules |
| `scripts/blue-green-deploy.sh` | Digest-only, evidence-producing, probe-gated switch/rollback with no placeholder telemetry or issue side effect |
| `scripts/qualify_goal006_environment.sh` | One local/Docker final qualification command writing result JSON directly |
| `scripts/goal006_*.py` | Structured manifest, policy, cost, configuration, inventory, runner, promotion, recovery, and evidence validators |
| `tests/pipeline/` and owning tests | Workflow, schema, denial, release, retry, rollback, lease, and evidence contracts |
| `test-results/goal006/<stage>/` | SHA-256-addressed final evidence, author review, and PR metadata inputs |

### 7.1 Workflow Housekeeping Disposition

| Workflow | Classification | Disposition |
|---|---|---|
| `deploy.yaml` | Strategic operator entry | Retain as the only manual application deployment entry. |
| `deploy-environment.yaml` | Reusable deployment engine | Retain; it owns private runner execution, Terraform, external configuration, cost and cleanup. |
| `post-deploy-verify.yaml` | Independent confirmation | Retain; deployment and confirmation identities remain separate. |
| `runner-environment-delivery.yaml` | Runner control-plane delivery | Retain; reviewed runner-stack preview/apply is distinct from application deployment. |
| `goal006-private-runner-qualification.yaml` | Private-path diagnostic | Retain; it proves Storage/Terraform access and cleanup without deploying applications. |
| `goal006-runner-image.yaml` | Runner supply chain | Retain; it builds and attests the immutable private-runner image. |
| `reconcile-workload-leases.yaml` | Operational reconciler | Retain; lease expiry and zero-idle enforcement are not deployment entry behavior. |
| `goal006-phase2-offline.yml` | Unique offline qualification with stale phase name | Do not delete until its release simulation and delegated PostgreSQL checks are moved into an active CI gate; then rename or remove under implementation authorization. |
| `emergency-halt-check.yaml` | Orphaned governance control | Its comment names deleted callers and no workflow calls it. Under implementation authorization, move the fail-closed halt check into `deploy.yaml`, add contract tests, then delete the orphan. |
| `deploy-demo.yaml` and `promote.yaml` | Removed transitional wrappers | Remain absent; PR #371 consolidated their responsibilities into the current path. |

One stale `promote.yaml` comment remains in legacy `infrastructure/terraform/environments/dev/main.tf`.
Correct it only in an implementation-authorized cleanup because the file is runnable Terraform.

Do not create a parallel deployment workflow, second release format, or prose-only proof ledger.

## 8. Ordered Delivery Components

1. **Accepted baseline:** bind PR #371, WC-076 and finalization evidence; record Demo acceptance, UAT
  verification, canonical workflow graph, immutable release behavior, and unresolved Production gaps.
2. **Documentation consolidation:** make the Azure topology the single strategy source; reduce README
  to routing; update PROJECT_STATE and WC-076 in place; leave historical plans/evidence unchanged.
3. **Workflow inventory:** classify each workflow as strategic entry, reusable engine, diagnostic,
  operational reconciler, unique qualification, historic, or orphaned. Do not remove a unique control.
4. **Authorized future cleanup:** when separately authorized, move orphaned governance behavior into
  the canonical path with focused contract tests before deleting its standalone workflow.
5. **Dark Production readiness:** validate offline and authorized plan-only topology, tuple,
    configuration schema, identity, isolation, recovery, cost, and rollback without runner start,
    apply, secret creation, DNS activation, or traffic.
6. **Foundation freeze:** publish the accepted compatibility/evidence ledger, close only verified
    assessment gaps, and submit the final unmerged PR for Founder review.

Each numbered component is a checkpoint, not an independently complete delivery. Do not open an
intermediate PR merely to report progress unless a Work Contract explicitly splits the stage.

## 9. Test And Acceptance Plan

### 9.1 Development Validation Policy

During implementation, start with:

1. `docker compose config --quiet` for every changed Compose profile;
2. one focused smoke or contract test per changed service/workflow/script;
3. the nearest endpoint or structured fixture example that can falsify the current hypothesis;
4. syntax/schema checks for only the changed YAML, HCL, JSON, Python, or shell surface.

Do not run full coverage, all image builds, SBOM, Trivy, Gitleaks, or the complete repository gate
after each edit. Run those heavyweight checks once, after implementation and final commit history are
stable, in the stage's final qualification campaign. A focused failure is repaired and rerun before
opening another implementation slice.

### 9.2 Endpoint-Focused Examples

The executor must add and run deterministic examples for changed behavior, including:

- exact-six manifest verification accepts six digest references and rejects a tag or seventh member;
- environment configuration accepts references/digests and rejects a literal secret or unknown key;
- Demo workflow rejects UAT, stale main, unaccepted artifact, wrong caller, and unauthorized actor;
- promotion rejects absent/mismatched Founder acceptance and any image digest change;
- runner bootstrap rejects permission, template, parameter, DNS, RBAC, cost, or correlation mismatch;
- cleanup selects exactly one correlated runner/execution and fails closed on ambiguity;
- blue-green leaves green at zero traffic on failed migration/probe and switches back to the previous
  qualified revision without rebuild or down-migration;
- independent verification detects live digest, dependency, revision, journey, or evidence mismatch;
- lease reconciliation is idempotent and retains protected foundation resources;
- dark Production path rejects apply, runner start, DNS activation, secret seeding, and traffic.

### 9.3 Coverage And Quality Thresholds

- all new/changed Python belongs to an owning test slice with at least 90% line and 80% branch
  coverage, or the stricter existing repository threshold;
- workflow and shell behavior has positive, denial, failure, retry, rollback, and no-secret tests;
- every expected/collected/executed/passed proof count is nonzero and equal; no skip, TODO, placeholder,
  advisory, empty scan, or expected-failure success is accepted;
- Terraform validates, formats, and passes plan policy against positive and destructive/cross-scope
  fixtures; authorized live plans must be retained before apply;
- C-059 traceability and C-065 exact-final-HEAD author review are blocking.

## 10. Docker Qualification And Cost Control

### 10.1 Preflight And Safe Capacity Recovery

Before builds, record `docker system df`, `docker buildx du`, running containers, and image references.
Remove only disposable stopped qualification containers, dangling build cache, and dangling/unreferenced
images attributable to this Work Contract. Preserve running containers, volumes, named state,
current hash-tagged images, pinned base/scanner images, and unrelated user artifacts. If safe recovery
cannot provide required capacity, stop with the preflight record.

### 10.2 Immutable Image Identity And Reuse

Compute a source hash from the final tracked implementation inputs and a configuration hash from
Compose/tool/version inputs. Tag local qualification images:

```text
wc081-<service>-<source12>-<config12>
```

Build each changed image once. Reuse those exact local image IDs for smoke tests, coverage, SBOM,
Trivy, and evidence. CI separately creates the signed GHCR exact-six digest tuple once. Promotion and
rollback consume only manifest digests and never rebuild or retag for authority.

### 10.3 Evidence-First Failure Handling

Before retrying, capture container/job logs, inspect output, Compose state, Docker resource state,
workflow/run identifiers, Azure execution inventory when authorized, and the failed proof record. An
unchanged-code retry is allowed once only when evidence identifies a transient infrastructure failure.
A deterministic code/config/gate failure requires a repair and new focused validation. A second
infrastructure retry, ambiguous failure, orphan, secret exposure, or evidence loss is a stop.

### 10.4 One Final Qualification Command

Implementation must create this exact operator interface:

```bash
OUTPUT=test-results/goal006/demo/qualification.json
./scripts/qualify_goal006_environment.sh --environment demo --output "$OUTPUT"
```

For the later authorized stages, replace only `demo` with `uat` or `prod-plan`. The script must write
the requested JSON directly through an EXIT trap, including failures. The result records final HEAD,
base SHA, source/config hashes, image IDs/digests, pinned tool versions, every command/proof result,
coverage, SBOM/scan digests, Compose state, retry classification, environment stage, release and
configuration digests, and overall PASS/FAIL. `prod-plan` must prove that no mutating action ran.

One final campaign performs, in order:

1. Docker preflight and disposable-only cleanup;
2. Compose configuration and focused smoke replay;
3. impacted tests and required coverage;
4. exact changed image builds and runtime checks;
5. SBOM generation and zero HIGH/CRITICAL Trivy acceptance for changed deployable images;
6. Gitleaks over the final branch range and relevant worktree state;
7. Terraform/YAML/shell/manifest/configuration/promotion/evidence policy gates;
8. C-059 traceability and C-065 author-review metadata validation;
9. direct final evidence JSON emission.

### 10.5 Exact Repository Gate Command Forms

The implementation issue must resolve changed test paths before execution. At minimum, use the
repository-pinned test image and existing validators rather than floating host tools:

```bash
docker compose config --quiet
docker compose --profile test run --rm test-runner \
  pytest tests/pipeline/test_goal006_demo_deployment_workflow.py tests/pipeline/<wc081-tests>.py -q
docker compose --profile test run --rm test-runner \
  ruff check scripts/<changed-goal006-files>.py tests/pipeline/<wc081-tests>.py
docker compose --profile test run --rm test-runner \
  ruff format --check scripts/<changed-goal006-files>.py tests/pipeline/<wc081-tests>.py
terraform fmt -check -recursive infrastructure/terraform/phase2
python scripts/validate_author_review.py --help
```

The final implementation must replace angle-bracket placeholders with exact paths in its issue and
qualification script. It must use action/tool versions pinned by repository workflows, including
Terraform 1.9.8 on the current deployment path, Spectral 6.15.0, Syft 1.27.1, Trivy 0.65.0, and
Gitleaks 8.28.0. Tool drift or an unavailable pinned image is blocking, not permission to float.

## 11. LLM And Token-Cost Optimization

- load only WC-081 control, Platform IT quick card, Skill 17, Azure topology, ADR-047, and the files
  owned by the active component;
- use deterministic search, schema validators, tests, `jq`, Terraform plans, and evidence scripts for
  facts; do not ask an LLM to infer machine-verifiable state;
- keep one component-first execution record and update it from structured results rather than
  generating parallel summaries;
- pass exact failing snippets, schemas, diffs, and command results to any LLM call; omit complete logs,
  unrelated files, and previously settled architecture;
- batch independent reads and checks, cache release/config/tool digests, and reuse Docker images and
  scan outputs throughout one qualification;
- never use an LLM retry to diagnose a failure before logs/resource state are captured;
- make at most one unchanged-code infrastructure retry, then stop with evidence;
- defer full coverage/build/SBOM/Trivy/Gitleaks to the one final campaign per stage;
- do not invoke another office, reviewer, or subagent unless the Founder explicitly requests it.

## 12. Commit, Review, Push, And PR Sequence

1. Work on `ib/081/foundation-environment-promotion-freeze` or the exact Founder-assigned branch.
2. Implement the complete authorized stage with focused validation after each bounded edit.
3. Preserve unrelated worktree changes and failed-attempt evidence.
4. Use supported conventional commits referencing IB-081; do not rewrite accepted external history.
5. Finish the stage's implementation commits before final qualification.
6. Run the one complete qualification against the exact final HEAD.
7. Perform author review and bind reviewed commit, qualification digest, test evidence, rollback tuple,
   and stage metadata to that same HEAD.
8. Validate C-059 commit/file traceability and C-065 author-review body/HEAD equality locally.
9. Run PR pre-check equivalents and repair before publishing; any repair creates a new final HEAD and
   requires requalification and review rebinding.
10. Push once after all local gates pass, open one complete unmerged PR using the repository template,
    and request Founder review. Do not self-approve or merge.

The cost-controlled sequence is explicit:

```text
Docker preflight -> focused tests -> final commit history -> one complete qualification run
-> PR metadata validation -> push
```

## 13. Acceptance Matrix

| ID | Acceptance condition | Required evidence |
|---|---|---|
| WC081-01 | Authority and stage are exact | Accepted WC-081/WC-076-or-successor, issue, session and provider grants |
| WC081-02 | Demo runner is qualified | 10 successes, 5 forced cancellations, hard termination, cleanup and zero-idle ledger |
| WC081-03 | Public deployment fallback is absent | Workflow contract tests, private DNS/backend operations, Storage policy |
| WC081-04 | Release is immutable exact-six | Signed manifest, six attestations/SBOMs/digests, anonymous pull and live inventory proof |
| WC081-05 | Configuration is external | Schema result, config digest, Key Vault references, no-secret scans, image inspection |
| WC081-06 | Demo is operationally qualified | Migration, readiness, CCT, Founder journey, blue-green, rollback, lease, cost, telemetry evidence |
| WC081-07 | Demo acceptance is explicit | Founder record bound to release/config/schema/evidence digests and URL |
| WC081-08 | UAT promotion preserves images | Demo/UAT six-digest equality and no-build workflow proof |
| WC081-09 | Environments are isolated | State/identity/VNet/data/vault/DNS/evidence inventory plus reciprocal denial records |
| WC081-10 | UAT is Production-shaped | PITR/restore, Temporal boundary, blue-green, rollback, lease, journey and independent verification |
| WC081-11 | Production remains dark | Plan/readiness evidence plus zero apply, runner, secret, DNS, and traffic proof |
| WC081-12 | Qualification is deterministic | Direct JSON, pinned versions, reconciled proof counts, retained failures, no blind retry |
| WC081-13 | PR metadata is exact | C-059 PASS, C-065 PASS, final HEAD/evidence equality, one push, unmerged Founder-ready PR |

All applicable rows are blocking. A local PASS cannot satisfy a cloud-effectiveness row, and a Demo
PASS cannot satisfy UAT or Production readiness.

## 14. Rollback And Compatibility

- keep the immediately previous qualified release/configuration tuple at zero traffic for at least 24
  hours and through the active Demo/UAT lease, whichever is later;
- rollback is an audited traffic switch to that tuple, not rebuild, retag, down-migration, or image
  substitution;
- migrations are expand-only and the previous qualified release must read the current schema before
  traffic can shift to the new release;
- failed green revisions receive zero traffic and remain with evidence until retention permits removal;
- runner bootstrap recovery reconciles the same immutable Deployment Stack tuple and never deletes
  protected networking, identity, vault, endpoint, DNS, state, backup, or evidence resources;
- a failed Demo remains Demo. A rejected UAT deployment rolls back within UAT and does not alter the
  accepted Demo tuple. Production remains unaffected and dark.

The existing `scripts/blue-green-deploy.sh` is not acceptance authority until implementation removes
mutable-tag examples, placeholder telemetry, permissive cost fallback, direct issue-creation side
effects, destructive deactivation assumptions, and noncanonical app naming, then adds structured
pre-traffic and rollback evidence matching this plan.

## 15. Stops

Stop immediately and retain evidence when:

- any authority, owner contract, accepted digest, stage prerequisite, cost input, rollback tuple, or
  required proof is missing, stale, contradictory, or ambiguous;
- UAT is requested before explicit Founder acceptance of the exact Demo tuple;
- Production mutation or activation is requested under WC-081;
- Terraform proposes destruction, cross-environment reference, unexpected ownership, unapproved
  service/SKU/provider, or a secret-bearing value;
- image digest changes between Demo and UAT, a mutable tag controls deployment, or exact-six changes;
- a public Storage path, GitHub-hosted deploy job, long-lived runner/credential, shared identity/state,
  or cross-environment route appears after private-runner activation;
- runner registration, cleanup, zero-idle, correlation, DNS, backend operation, denial, cost, migration,
  readiness, CCT, rollback, restore, lease, observability, or evidence proof fails;
- a HIGH/CRITICAL image finding, secret finding, skipped/empty gate, TODO success path, or unreconciled
  proof count remains;
- more than one evidenced unchanged-code infrastructure retry would be needed;
- final evidence or author review is not bound to final HEAD;
- implementation requires an architecture, policy, security, data, cost, recovery, or acceptance
  decision not already made by its owner.

## 16. Definition Of Done

WC-081 is done only when:

- WC-076 and PR #371 evidence are the accepted execution baseline and all new authorities are evidenced;
- the accepted Demo/UAT private-runner and no-public-fallback results remain traceable and unchanged;
- reusable environment workflows derive values from reviewed manifests while preserving separate
  identities, approvals, state, configuration, data, network, DNS, and evidence;
- exact-six is built once and immutable digest equality is enforced through promotion and rollback;
- all environment values and secret references remain external to images;
- Demo acceptance and UAT exact-six deployment/independent verification remain bound to their
  immutable evidence; unresolved recovery or rollback proofs are not overstated;
- dark Production plan/readiness evidence passes with zero mutation, runner capacity, DNS, secrets, or
  customer traffic;
- each stage uses focused development checks and one final hash-bound Docker qualification that writes
  JSON directly and retains failures;
- final commits precede evidence/review binding, C-059 and C-065 pass, push occurs once, and the
  Founder-ready PR remains unmerged;
- all thirteen acceptance rows pass with exact proof digests and no waived, skipped, advisory, empty,
  placeholder, or inferred result.

## 17. Author Review

| Review dimension | Result | Finding and repair |
|---|---|---|
| Requirements coverage | PASS | Objective and DoD cover Demo first, Founder acceptance, same-digest UAT, dark Production, Docker economy, evidence, and PR closure |
| Interfaces | PASS | Release tuple, environment manifest, reusable workflow, qualification command, acceptance record, and evidence boundaries are explicit |
| Failure modes | PASS | Missing authority, stale/mismatched inputs, transient retry, orphan, drift, destructive plan, failed probes, and rejected acceptance fail closed |
| Security and isolation | PASS | Private runner, short-lived identity, external secrets, reciprocal denial, independent verification, and no-public-fallback controls are retained |
| Operability | PASS | Logs/resource state, cleanup, leases, cost, observability, failed-revision retention, and direct JSON evidence are required |
| Reversibility | PASS | Previous qualified tuple, additive schema, traffic-switch rollback, retained foundation, and no rebuild/down-migration are fixed |
| Cost | PASS | Focused checks, one final campaign, image reuse, zero idle capacity, leases, bounded retry, and FA-052 gates constrain spend |
| Environment sequence | PASS | Demo qualification and explicit acceptance precede UAT; Production remains dark and separately authorized |
| Decision traceability | PASS | WC-081, restored/superseding WC-076, controlling topology, ADRs, owner outputs, final HEAD, digests, and acceptance rows bind every action |
| Implementation specificity | PASS | PR #371 baseline, canonical workflow roles, documentation ownership, future cleanup boundary, artifact paths, commands, proof IDs, and stops are identified |

**Author review result:** PASS
**Founder review:** PENDING
**Implementation authorization:** NOT GRANTED BY THIS PLAN