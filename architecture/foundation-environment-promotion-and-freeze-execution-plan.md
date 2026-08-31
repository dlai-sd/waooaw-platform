# Foundation Environment Promotion And Freeze - Executable Delivery Plan

**Office:** Chief Solution Architect (INST-005)
**Work Contract:** WC-081
**Status:** AUTHOR-REVIEWED SOLUTION PLAN CANDIDATE - FOUNDER REVIEW; IMPLEMENTATION AND CLOUD
EXECUTION REQUIRE SEPARATE CURRENT-SESSION AUTHORIZATION
**Execution office:** Platform IT Expert (INST-010), Skills 1-9 and 11-17, with Skill 17 controlling
cloud delivery
**Delivery unit:** Qualified Demo, explicit Founder Demo acceptance, unchanged release-tuple promotion
to qualified UAT, and dark Production readiness without activation
**Reference architecture:** `architecture/foundation-consolidated-assessment-2026-08-29.md` and
`architecture/reference/pipeline/azure-deployment-topology.md`
**Constitutional basis:** C-001, C-002, C-003, C-005, C-007, C-023, C-025, C-032, C-035, C-049,
C-059, C-063, C-065, C-067, C-071, C-076, C-077, C-080
**Architectural decisions:** ADR-012, ADR-013, ADR-014, ADR-015, ADR-027, ADR-031, ADR-047

## 1. Objective

Complete the remaining Foundation environment-delivery capability as one controlled progression:

```text
REPOSITORY-QUALIFIED EXACT-SIX RELEASE
  -> DEMO PRIVATE-RUNNER QUALIFICATION
  -> DEMO PLAN, APPLY, VERIFY, ROLLBACK, AND LEASE PROOF
  -> EXPLICIT FOUNDER ACCEPTANCE OF THE EXACT DEMO TUPLE
  -> UAT PROMOTION OF THE SAME SIX OCI DIGESTS
  -> UAT ISOLATION, RECOVERY, BLUE-GREEN, AND ROLLBACK PROOF
  -> DARK PRODUCTION READINESS PLAN WITH ZERO ACTIVATION
```

The same immutable application images must move from Demo to UAT and, under a later authority, to
Production. Environment values, endpoints, identities, secret references, cost inputs, lease data,
and policy parameters must remain outside the images in reviewed environment configuration and Key
Vault references. Promotion changes environment configuration and deployment evidence, never image
content or image identity.

This plan is self-sufficient for a future Platform IT executor. It defines the required repository
changes, stage sequence, validation economy, cloud proofs, evidence, rollback, and stops. It does not
authorize implementation, provider access, expenditure, deployment, UAT, Production, acceptance,
PR approval, or merge.

## 2. Required Outcome

| Boundary | Required outcome | Prohibited outcome |
|---|---|---|
| Release | One signed manifest with exactly six digest-pinned first-party images, attestations, SBOMs, source commit, dependency manifest, and schema compatibility | Per-environment rebuild, mutable tag authority, silent seventh member, or digest substitution |
| Configuration | Versioned non-secret schema plus reviewed per-environment document digest and Key Vault/managed-identity references | Environment value, endpoint, credential, secret, or tenant data baked into an image |
| Runner | Ephemeral environment-scoped ACA runner, private state/config path, independent cleanup, zero idle capacity | Long-lived runner, public state path, cross-environment identity, or public fallback |
| Demo | Founder-only qualified deployment with synthetic data, bounded lease, rollback, and complete evidence | UAT inference from local tests or an unaccepted Demo |
| Acceptance | Founder records the exact manifest, six image digests, configuration digest, schema digest, evidence digest, and Demo URL accepted | Acceptance by executor, workflow success alone, mutable reference, or undocumented verbal inference |
| UAT | Production-shaped isolated environment using the exact Demo image digests and proving PITR, blue-green, rollback, and cross-environment denial | Rebuild, Demo state/identity/data reuse, or action before Founder Demo acceptance |
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
| WC-076 authority | Approved record restored, or accepted superseding authority names its replacement | File and acceptance reference exist; topology prose is not authority |
| Current-session implementation authority | Explicitly granted | Founder names Platform IT session, issue, branch, paths, and stage |
| Cloud/provider authority | Explicit and stage-specific | Allowed subscription, environment, query/plan/apply/deploy actions, time window, and spend bound recorded |
| Project state | Current and compatible | GOAL-006 stage, blockers, acceptance history, and Production prohibition agree |
| Controlling architecture | Accepted | Azure topology and ADR-047 unchanged or accepted amendments linked |
| Owner contracts | Executable | Platform, Security, Data, QA, configuration, CCT, recovery, and cost inputs are versioned |
| Implementation issue | Founder assigned | Exact files, tests, proof IDs, branch, estimate, rollback, stops, and acceptance actor named |
| Toolchain | Repository pinned | Docker/BuildKit, Compose, Terraform 1.9.8 where current workflow requires it, Python test image, Syft 1.27.1, Trivy 0.65.0, Gitleaks 8.28.0, and Spectral 6.15.0 available |

The current repository contains useful partial delivery assets but does not itself grant execution
authority. In particular, UAT remains blocked and the absent WC-076 record must be restored or
explicitly superseded before Skill 17 implementation or cloud execution.

### 3.1 Owner Handoff Before Platform IT Execution

| Owner | Required accepted output |
|---|---|
| Founder | WC-081 acceptance, implementation authority, exact provider authority, Demo acceptance when reached, and later UAT authority |
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

- restore or supersede the missing WC-076 execution authority record before implementation;
- qualify and activate the ADR-047 Demo private-runner path without a public fallback;
- parameterize the accepted reusable deployment workflow using reviewed environment manifests rather
  than embedded Demo resource IDs, names, labels, configuration Blob paths, and caller checks;
- retain separate environment workflows and GitHub Environment approvals for Demo, UAT, and
  Production-dark plan entry;
- extend exact-six verification, independent verification, cleanup, and evidence to UAT;
- implement external non-secret configuration schemas and environment manifests whose digests bind to
  the release while all secret values remain in Key Vault;
- complete additive migration, pre-traffic verification, blue-green switch, compatible rollback,
  failed-revision retention, and lease expiry automation;
- implement one deterministic local/Docker qualification entry point that emits final JSON directly;
- qualify Demo, record Founder acceptance, then promote the same image digests to UAT;
- prove UAT PITR/restore and Production-shaped operations;
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
| `work-contracts/WC-076-goal006-phase3-execution.md` or accepted successor | Restored/superseding authority record before execution |
| `.github/workflows/deploy-demo.yaml` | Protected Demo plan/apply entry using current-main signed release |
| `.github/workflows/deploy-environment.yaml` | Environment-parameterized reusable workflow with no Demo constants in shared logic |
| `.github/workflows/post-deploy-verify.yaml` | Independent environment-parameterized verification and complete evidence output |
| `.github/workflows/promote.yaml` | Founder-acceptance-bound UAT promotion; Production remains fail-closed |
| `.github/workflows/reconcile-workload-leases.yaml` | Idempotent scale-to-zero/server-stop lease reconciliation and evidence |
| `infrastructure/deployment-stacks/goal006-runner/` | Versioned per-environment runner manifests/templates and activation proof inputs |
| `infrastructure/terraform/phase2/environments/` | Isolated Demo/UAT roots and dark Production plan roots using accepted modules |
| `scripts/blue-green-deploy.sh` | Digest-only, evidence-producing, probe-gated switch/rollback with no placeholder telemetry or issue side effect |
| `scripts/qualify_goal006_environment.sh` | One local/Docker final qualification command writing result JSON directly |
| `scripts/goal006_*.py` | Structured manifest, policy, cost, configuration, inventory, runner, promotion, recovery, and evidence validators |
| `tests/pipeline/` and owning tests | Workflow, schema, denial, release, retry, rollback, lease, and evidence contracts |
| `test-results/goal006/<stage>/` | SHA-256-addressed final evidence, author review, and PR metadata inputs |

Do not create a parallel deployment workflow, second release format, or prose-only proof ledger.

## 8. Ordered Delivery Components

1. **Authority and baseline:** restore/supersede WC-076, bind WC-081 issue/branch/stage, inventory
   current resources only if provider-query authority exists, and preserve all pre-existing evidence.
2. **Offline contracts:** define environment manifest/configuration/evidence schemas, exact-six and
   promotion invariants, accepted CCT/probe sets, and negative fixtures.
3. **Demo runner control plane:** reconcile the immutable Deployment Stack, implement broker/token
   lifecycle and cleanup, then prove ten successful runs plus five forced cancellations including one
   hard termination with no orphan beyond five minutes.
4. **Demo runner activation:** in one reviewed change, switch deployment to the qualified private
   label and assert removal of all temporary public Storage mutation. Disable public Storage access
   only after exact private backend operations pass.
5. **Reusable environment workflow:** replace Demo constants with allowlisted manifest-derived values;
   keep per-environment caller, GitHub Environment, identity, state, and authorization checks.
6. **Foundation and dependencies:** reconcile VNet, private DNS, Key Vault, PostgreSQL, identities,
   logs, databases/roles, Keycloak, Demo Temporal, Redis, and secret references.
7. **Application plane:** consume the signed exact-six manifest, create digest-pinned ACA revisions,
   bind external configuration, and preserve private/public ingress boundaries.
8. **Release mechanics:** run additive migration, internal/public probes and CCTs before traffic;
   switch blue-green, retain the prior qualified revision, prove rollback, and reconcile lease expiry.
9. **Demo qualification:** run the single final campaign, perform authorized Demo plan/apply,
   independently verify live inventory and journeys, and publish the evidence-bound Founder URL.
10. **Founder Demo acceptance:** record an explicit accept/reject decision against exact digests. A
    rejection returns to Demo with retained evidence; it never unlocks UAT.
11. **UAT activation and promotion:** after separate authority, instantiate the same runner blueprint,
    prove reciprocal isolation, and deploy the exact Demo image digests with UAT configuration.
12. **UAT qualification:** prove representative synthetic journeys, Temporal Cloud boundary,
    PITR/restore, blue-green, rollback, lease, cost, telemetry, and independent evidence.
13. **Dark Production readiness:** validate offline and authorized plan-only topology, tuple,
    configuration schema, identity, isolation, recovery, cost, and rollback without runner start,
    apply, secret creation, DNS activation, or traffic.
14. **Foundation freeze:** publish the accepted compatibility/evidence ledger, close only verified
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

- WC-076 is restored or explicitly superseded and all current-session authorities are evidenced;
- the Demo private runner passes the complete ADR-047 activation matrix and no public fallback remains;
- reusable environment workflows derive values from reviewed manifests while preserving separate
  identities, approvals, state, configuration, data, network, DNS, and evidence;
- exact-six is built once and immutable digest equality is enforced through promotion and rollback;
- all environment values and secret references remain external to images;
- Demo passes migration, probes, CCTs, journeys, blue-green, rollback, lease, isolation, security,
  observability, cost, and independent verification;
- the Founder explicitly accepts the exact Demo tuple before UAT begins;
- UAT promotes the same six digests and passes reciprocal isolation, PITR/restore, Production-shaped
  blue-green, rollback, lease, and independent verification;
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
| Implementation specificity | PASS | Current Demo hardcoding, UAT placeholder, blue-green deficiencies, artifact paths, ordered components, commands, proof IDs, and stops are identified |

**Author review result:** PASS
**Founder review:** PENDING
**Implementation authorization:** NOT GRANTED BY THIS PLAN