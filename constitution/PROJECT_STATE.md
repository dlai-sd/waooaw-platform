# PROJECT_STATE.md

**State Schema:** 2.0.0
**State Revision:** 124
**Last Updated:** 2026-08-20
**Purpose:** Current operational state for bootstrap, recovery, and automated sprint controls.

This file is a snapshot, not a session ledger. Keep it below 200 lines. Update the active
checkpoint in place; record durable detail in the owning Work Contract, Goal record, review,
or evidence artifact. Completed history remains in git and the archive index below.

---

## Institutional Snapshot

| Field | Current Value |
|---|---|
| Epoch | Epoch 1 — Foundation |
| Gate | G5 CLEAR — prerequisites met; not session implementation authority |
| Engineering status | IMPLEMENTATION |
| Platform version | 1.45.0 |
| Latest completed Work Contract | WC-074 - GOAL-006 Enterprise Delivery Addendum |
| Latest merge | PR #310 merged to `main` as `f7f7f2b465deb0b10dff41c779efc23d6e23cb74` |
| Active delivery | WC-076 inactive Demo runner bootstrap implementation; UAT prohibited |

## Active Checkpoint - GOAL-006 Phase 3 Live Execution

| Milestone | Status |
|---|---|
| Cloud-only PR #289 | DONE - independently approved by R-131 and merged by Founder as `d49dad1` |
| Azure read-only preflight | DONE - tenant, subscription, budget, state and providers verified |
| WC-076 P3-EX01 through P3-EX06 | DONE - issue #296 closed after protected environments, OIDC and signed exact-six release evidence |
| INST-010 GOA / Acceptance | VALID - GOA-GOAL-006-INST-010-03 and later ACC-GOAL-006-INST-010-03 recorded on PR #294 |
| Azure topology and CI prechecks | DONE - PR #307 merged as `7a74c14`; EA/SA review R-140 accepted the incremental deployment topology |
| Incremental OIDC plan readiness | DONE - PR #308 merged as `3907906`; plan mode rejects state mutation and reconciliation is manual Demo-only plan |
| Trusted-main exact-six release | DONE - run `32370596796`, commit `235c08a`, artifact `goal006-exact-six-release-235c08a4c5d67707cf12578d6b4f0a1b6b501a9d` |
| Configuration readiness repair | DONE - PR #309 merged; second plan proved exact Blob retry and verified firewall cleanup |
| Real Demo OIDC plan | BLOCKED - run `32371262629` reached Terraform init, then backend list received Storage `403 AuthorizationFailure`; no plan/apply occurred |
| Private runner decision | ACCEPTED - independent EA and Security review of commit `7e5bd4b` returned APPROVE with no blockers |
| Demo runner bootstrap | IMPLEMENTED - inactive Deployment Stack compiles, ARM validates, immutable verifier and 51 focused tests pass; review pending |
| Local validation | PASS - 42 focused tests, Ruff, actionlint and editor diagnostics |
| Architecture review | CLEAR - author review, focused EA review and focused INST-007 Security correction complete; no separate review artifact required |
| Demo deploy / verify | BLOCKED - Demo runner bootstrap implementation and private-path qualification required before workflow label activation |
| Founder Demo acceptance | PENDING - P3-EX08 remains a separate control point after the verified Azure URL is returned |
| UAT deploy / verify / accept | PROHIBITED - no token, plan, apply or environment request before explicit Founder Demo acceptance |
| Production | PLAN ONLY - deployment, traffic and final acceptance remain Founder-reserved |

### Checkpoint Context

- **Authority:** Founder authorization on issue #299 permits P3-EX07 Demo mutation and expenditure only; Founder-only Azure URL review is authorized.
- **Execution contract:** `work-contracts/WC-076-goal006-phase3-execution.md`; backlog P3-EX01 through P3-EX11.
- **Cloud state:** no Demo/UAT/Production workload resources have been created; run `32371262629` made only the bounded temporary state-account firewall mutation and evidence proves cleanup removed it.
- **RCA boundary:** configuration access succeeded after one network-rule retry, while Terraform backend access failed moments later; discovered GitHub-hosted public egress is not an acceptable durable trust boundary.
- **Architecture gate:** ADR-047 is Accepted through merged PR #310. The inactive Demo bootstrap is implemented; token issuance, runner execution, label activation and Storage public-network disablement remain gated.
- **Boundary:** no UAT, custom DNS, customer traffic, Production apply, Platform Operations activation, final Goal acceptance, self-approval or self-merge.

## Authorization Boundary

GOAL-006 Phase 3 execution is authorized only inside FA-052: the named Azure tenant/subscription,
Central India, INR 15,000 one-time and INR 10,000 monthly ceilings, Demo/UAT and dark Production
boundaries, independent evidence gates and validity period. FA-052 does not authorize customer
traffic, material Production risk acceptance, Platform Operations activation, final Goal acceptance,
PR approval or merge. A failed constitutional, security, evidence, recovery, scope or cost gate stops
progression.

## Current Blockers

P3-EX07 Azure planning is blocked until the inactive Demo runner bootstrap is independently accepted,
merged and reconciled. UAT remains constitutionally blocked until the Founder explicitly accepts the
resulting Demo deployment.

## Next Authorized Action

Obtain focused review and Founder merge of the inactive Demo runner bootstrap, then reconcile its
Deployment Stack and qualify the private path. Do not create UAT/Production runner resources, switch
deployment labels, apply Demo workloads, disable Storage public access, or initiate UAT.

## History And Evidence

- History through 2026-07-22: `constitution/PROJECT_STATE_ARCHIVE.md`.
- History from 2026-07-23 through WC-059 closure: git object
  `b0dbe9c^2:constitution/PROJECT_STATE.md` (the merged PR #265 head snapshot).
- WC-059 durable evidence: `work-contracts/WC-059-ae01-contract-payment-activation.md`,
  `goals/GOAL-005-wc059-implementation-evidence.md`, and reviews R-083/R-084.
- Schema-v2 governance record and independent review:
  `work-contracts/WC-061-project-state-v2-governance.md` and R-085.
- WC-060 readiness: `work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md`,
  `blockers/CB-004-wc060-canonical-contract-gaps-2026-08-11.md`, Amendment 9 in
  `goals/GOAL-005-execution-plan.md`, R-086, ACK-GOAL-005-INST-001-09, FA-041, and
  GOA-GOAL-005-INST-010-06.
- WC-060 implementation evidence and independent acceptance:
  `goals/GOAL-005-wc060-implementation-evidence.md` and R-087/R-088/R-089.
- WC-060 delivery closure: PR #268 merged to `main` as `95e0d91` after Founder approval.
- WC-062 implementation evidence and independent acceptance:
  `goals/GOAL-005-wc062-implementation-evidence.md` and R-096/R-097/R-098.
- WC-062 delivery closure: PR #273 merged by the Founder to `main` as `1a624d6` on 2026-08-12.
- WC-065 delivery closure: PR #278 merged by the Founder to `main` as `f28badc` on 2026-08-13;
  post-merge Docker regression and the PM delivery report passed.
- GOAL-006 Phase 2 delivery: PR #284 merged as `f52811436c900c2405aad871c43c88c073ae55fb`;
  post-merge closure PR #285 merged as `b0f1385a07ae02be1cbfd8b9b65f55acd498c65c`; WC-072
  and R-120 through R-126 are the durable evidence.
- GOAL-006 Phase 3 readiness: WC-073 and R-127 merged through PR #286 as
  `94701362d957fdc13d88bc7637c8b773a7cfb385`; WC-074 adds a planning-only enterprise delivery delta.
- GOAL-006 enterprise delivery addendum: WC-074 and R-128 merged through PR #287 as
  `bb511099ca5ff693ea538223e3779e4887421a99`; FA-050 stopped and FA-051 completed P3-WC01 read-only evidence.
- GOAL-006 cloud-only repository delivery: R-131 approved frozen SHA `199336c9`; PR #289 was merged
  by the Founder to `main` as `d49dad13fa3d7e9a670d847010f7b73e5612da51`. Post-merge execution
  backlog P3-EX01 through P3-EX11 is recorded in the P3-WC01 readiness evidence.
- Founder Commercial Governance formalization: PR #275 merged by the Founder to `main` as
  `2276ab2` on 2026-08-12; WC-064 remains ready for owner routing.
- Earlier completed work remains authoritative in its owning Work Contract, Goal, review,
  constitutional record, and repository history; it must not be copied back into this file.

---

## SPRINT_STATE_MACHINE
<!-- Machine-readable by autonomous-sprint.yaml. YAML-parseable block. -->
<!-- Edit ONLY the fields below. Do not alter the heading or fenced-block structure. -->
<!-- Task progress lives in work-contracts/WC-NNN-*.md, not here. -->

```yaml
autonomous_halt: false
platform_phase: IMPLEMENTATION
current_sprint: WC-034
sprint_status: DONE
branch: ib/014/wc034-f3-implementation
consecutive_failures: 0
tasks_done:
  - WC034-08
  - WC034-09
  - WC034-10
  - WC034-11
  - WC034-12
tasks_remaining: []
notes: |
  WC-034 F3 is complete and PR #254 merged as 8a1fcfa.
  This control block is retained for pipeline compatibility; it grants no new authority.
```

## Platform Delivery Summary

Last PM report: 2026-08-20
Platform Status issue: see GitHub Issues with label `platform-status`
