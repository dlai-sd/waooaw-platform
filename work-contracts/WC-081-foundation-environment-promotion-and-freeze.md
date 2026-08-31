# WC-081 - Foundation Environment Promotion And Freeze

**Work Contract ID:** WC-081
**Office:** Chief Solution Architect (INST-005)
**Execution office:** Platform IT Expert (INST-010), Skill 17
**Status:** SOLUTION PLAN CANDIDATE - FOUNDER REVIEW
**Delivery unit:** Demo implementation and qualification, explicit Founder Demo acceptance, unchanged
release-tuple promotion to UAT and qualification, and dark Production readiness evidence without
Production activation
**Controlling plan:** `architecture/foundation-environment-promotion-and-freeze-execution-plan.md`
**Reference architecture:** `architecture/foundation-consolidated-assessment-2026-08-29.md` and
`architecture/reference/pipeline/azure-deployment-topology.md`
**Architectural decisions:** ADR-012, ADR-013, ADR-014, ADR-015, ADR-027, ADR-031, ADR-047
**Constitutional basis:** C-001, C-002, C-003, C-005, C-007, C-023, C-025, C-032, C-035, C-049,
C-059, C-063, C-065, C-067, C-071, C-076, C-077, C-080

## Authority And Scope

This Work Contract authorizes Solution Architecture planning only. It does not authorize source or
workflow implementation, provider queries, cloud mutation, expenditure, DNS changes, deployment,
UAT, Production, customer traffic, acceptance, PR approval, or merge.

After Founder acceptance of this plan, a future Platform IT Expert session may execute only when the
Founder separately grants explicit current-session implementation authority and exact provider/cloud
authority for the selected environment stage. Demo is the first executable stage. UAT remains
prohibited until the Founder explicitly accepts the qualified Demo release. Production remains dark
and plan-only until separately authorized.

In scope:

- reconcile and qualify the Demo private-runner control plane defined by ADR-047;
- remove the temporary public deployment path only after the private-runner activation matrix passes;
- finish environment-parameterized deployment, external configuration, migration, blue-green,
  rollback, lease, observability, cost, and evidence automation;
- build the exact-six release once and retain its immutable OCI digests for every environment;
- deploy and qualify Demo, then capture explicit Founder Demo acceptance;
- promote the identical release tuple and image digests to UAT without rebuild or retag authority;
- qualify UAT isolation, PITR/restore, blue-green, rollback, and release compatibility;
- produce dark Production plans and readiness evidence without apply, activation, or traffic;
- create one Founder-ready, unmerged PR per authorized implementation stage after local gates pass.

Out of scope:

- architecture, region, SKU, cost ceiling, DNS, security, data, recovery, or policy invention;
- rebuilding an image for promotion or using a mutable tag as release authority;
- baking environment values, secrets, credentials, endpoints, or tenant data into an image;
- Production apply, DNS activation, customer traffic, destructive migration, or self-merge;
- bypassing private runners, evidence, security, cost, authorization, or environment gates.

## Required Inputs

Every input applicable to the selected stage must be present, current, accepted, and linked from the
implementation issue before execution begins.

| Input | Required state |
|---|---|
| This Work Contract and controlling plan | Founder accepted at an exact commit |
| Execution authority | Founder explicitly authorizes implementation for the current session and names the allowed repository paths |
| Provider authority | Founder separately authorizes the exact environment query/plan/apply/deploy actions and cost boundary |
| WC-076 execution record | Approved record restored, or an accepted superseding authority explicitly replaces it; architecture text alone cannot reconstruct authority |
| Current project state | Environment stage, GOAL-006 boundary, blockers, and acceptance chronology are non-contradictory |
| ADR-047 and Azure topology | Accepted and unchanged for private runners, isolation, release, evidence, and environment sequencing |
| Owner contracts | Platform, Security, Data, QA, and Solution inputs for the selected component are accepted and executable |
| Release input | Current-main successful CI artifact containing the signed exact-six manifest, image digests, attestations, SBOMs, and evidence |
| Configuration input | Reviewed environment configuration digest and Key Vault/managed-identity references, external to all images |
| Cost and lease input | Current actual/forecast cost, reviewed incremental estimate, tags, lease expiry, and FA-052 limits |
| Rollback input | Immediately previous qualified tuple and additive-schema compatibility proof |
| Implementation issue | Exact branch, paths, stage, commands, proof IDs, rollback, stops, and acceptance actor |

## Definition Of Done

WC-081 delivery is complete only when all applicable statements are true:

- the Demo private runner completes ten successful executions and five forced-cancellation
  executions, including one hard termination, with no orphan beyond five minutes;
- Demo deployment uses the environment-scoped private runner and contains no temporary public
  Storage firewall mutation or public fallback;
- one signed exact-six release tuple is built once, and its six immutable image digests are recorded;
- environment values and secret references remain external, reviewed, and digest-bound;
- Demo migration, private readiness, public Founder journey, CCT, blue-green, rollback, lease,
  observability, isolation, security, cost, and evidence checks pass;
- the final Demo qualification command writes one machine-readable evidence JSON result directly;
- explicit Founder Demo acceptance is recorded against the exact release, configuration, schema, and
  evidence digests before any UAT provider action;
- UAT uses the identical six Demo image digests, with only reviewed UAT configuration and
  environment-scoped identities, state, network, data, vault, DNS, and evidence differing;
- UAT PITR/restore, cross-environment denial, blue-green, rollback, and Production-shaped checks pass;
- dark Production Terraform/workflow plans pass offline and authorized plan-only checks without
  resource mutation, runner capacity, DNS activation, secrets, or customer traffic;
- focused checks ran during development, while full coverage, build, SBOM, Trivy, Gitleaks, and
  repository gates ran once in the final qualification campaign for each implementation stage;
- final commits precede qualification and author-review binding; C-059 and C-065 validate against the
  exact final HEAD; the branch is pushed once and a Founder-ready PR remains unmerged;
- every accepted artifact, command, digest, proof result, failed attempt, rollback tuple, cost record,
  and acceptance event is retained with SHA-256-addressed evidence.

## Stops

Stop without fallback, mutation, or inferred approval when any of the following occurs:

- WC-076 is absent and no accepted superseding execution authority exists;
- current-session implementation or exact provider authority is missing, expired, or ambiguous;
- UAT is requested before explicit Founder acceptance of the exact qualified Demo tuple;
- Production apply, activation, DNS, customer traffic, or spend is requested under WC-081;
- a release member, digest, attestation, configuration digest, schema compatibility result, or
  previous rollback tuple is missing or mismatched;
- a workflow rebuilds, retags, or substitutes an image during promotion or rollback;
- environment configuration or secret material appears in an image, repository, plan, state, log,
  artifact, command line, or PR body;
- Terraform reports destruction, cross-environment reference, unexpected ownership, public fallback,
  unapproved resource/provider/SKU, or cost-limit breach;
- private DNS, state/config access, RBAC denial, cleanup, zero-idle, migration, readiness, CCT,
  recovery, rollback, observability, lease, or evidence proof fails;
- a required gate is skipped, advisory, empty, stale, or bound to a non-final commit;
- an unchanged-code retry lacks retained evidence of an infrastructure-only failure, or more than one
  such retry would be required;
- a new architecture, security, data, QA, cost, or Production decision is needed.

## Plan Author Review

The Chief Solution Architect must review the controlling plan for requirements coverage, interfaces,
failure modes, security, operability, reversibility, cost, environment sequencing, immutable release
identity, evidence binding, and decision traceability. All findings must be repaired before this
Work Contract is marked `AUTHOR REVIEW: PASS` and submitted to the Founder.

**Author review:** PASS - findings repaired in controlling-plan Section 17
**Founder acceptance:** PENDING
**Implementation authorization:** NOT GRANTED BY THIS DOCUMENT