# PROJECT_STATE.md

**State Schema:** 2.0.0
**State Revision:** 117
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
| Latest merge | PR #298 merged to `main` as `73f9ad730514524801ff41ec72b974418ae4c220` |
| Active delivery | WC-076 P3-EX07 Founder-only Demo deployment under issue #299; UAT prohibited |

## Active Checkpoint - GOAL-006 Phase 3 Live Execution

| Milestone | Status |
|---|---|
| Cloud-only PR #289 | DONE - independently approved by R-131 and merged by Founder as `d49dad1` |
| Azure read-only preflight | DONE - tenant, subscription, budget, state and providers verified |
| WC-076 P3-EX01 through P3-EX06 | DONE - issue #296 closed after protected environments, OIDC and signed exact-six release evidence |
| INST-010 GOA / Acceptance | VALID - GOA-GOAL-006-INST-010-03 and later ACC-GOAL-006-INST-010-03 recorded on PR #294 |
| Trusted-main exact-six release | DONE - run `32329838734`, commit `73f9ad7`, artifact `9392723229`; reference tuple becomes stale after repair merge |
| Demo deployment repair | IMPLEMENTED - commit `93b7bd7`; Founder-only dispatch, private vault seeder, generated verifier handoff, /32 ingress and workload rollback |
| Local validation | PASS - 37 focused tests, actionlint, Terraform fmt and both Demo roots against Terraform 1.9.8 / AzureRM 4.14.0 |
| Independent review | CLEAR - no blocking INST-007 or INST-015 findings; UAT/Production path remains sealed |
| Demo deploy / verify | PENDING - repair PR, Founder merge and fresh trusted-main signed tuple required before Azure mutation |
| Founder Demo acceptance | PENDING - P3-EX08 remains a separate control point after the verified Azure URL is returned |
| UAT deploy / verify / accept | PROHIBITED - no token, plan, apply or environment request before explicit Founder Demo acceptance |
| Production | PLAN ONLY - deployment, traffic and final acceptance remain Founder-reserved |

### Checkpoint Context

- **Authority:** Founder authorization on issue #299 permits P3-EX07 Demo mutation and expenditure only; Founder-only Azure URL review is authorized.
- **Execution contract:** `work-contracts/WC-076-goal006-phase3-execution.md`; backlog P3-EX01 through P3-EX11.
- **Cloud state:** no Demo/UAT/Production workload resources have been created; automatic promotion is replaced by an explicit rejection gate.
- **Release rule:** merging the deployment repair changes `main`; P3-EX07 must use the resulting fresh trusted-main signed tuple, never the pre-repair tuple.
- **Boundary:** no UAT, custom DNS, customer traffic, Production apply, Platform Operations activation, final Goal acceptance, self-approval or self-merge.

## Authorization Boundary

GOAL-006 Phase 3 execution is authorized only inside FA-052: the named Azure tenant/subscription,
Central India, INR 15,000 one-time and INR 10,000 monthly ceilings, Demo/UAT and dark Production
boundaries, independent evidence gates and validity period. FA-052 does not authorize customer
traffic, material Production risk acceptance, Platform Operations activation, final Goal acceptance,
PR approval or merge. A failed constitutional, security, evidence, recovery, scope or cost gate stops
progression.

## Current Blockers

P3-EX07 Azure execution is blocked until the repair PR passes CI, the Founder merges it, and trusted
`main` produces a fresh signed exact-six tuple containing the repair. UAT remains constitutionally
blocked until the Founder explicitly accepts the resulting Demo deployment.

## Next Authorized Action

Push commit `93b7bd7` and this checkpoint, open the issue #299 repair PR, pass CI and obtain Founder
merge. Then use the fresh trusted-main signed tuple to manually dispatch the Founder-only Demo
workflow, verify exact-six live inventory and return the Azure-generated Web URL. Do not initiate UAT.

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
