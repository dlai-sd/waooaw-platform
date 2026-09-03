# PROJECT_STATE.md

**State Schema:** 2.0.0
**State Revision:** 132
**Last Updated:** 2026-09-03 (WC-078 scanner qualification repair checkpoint)
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
| Latest completed Work Contract | WC-080 - Agent Runtime Adapter Contract v1 |
| Latest merge | PR #398 merged to `main` as `b084363` |
| Active delivery | GOAL-006 Demo/runtime readiness repairs merged through PR #398; P3-EX11 remains plan-only |

## Active Checkpoint - GOAL-006 Phase 3 Live Execution

| Milestone | Status |
|---|---|
| WC-076 P3-EX01 through P3-EX07 | DONE - protected environments, OIDC, signed exact-six release, private runners, configuration and deployment controls merged |
| Canonical deployment entry | DONE - PR #371 retains only `.github/workflows/deploy.yaml` as the manual application entry and delegates deployment and independent verification |
| Demo deploy / verify | PASS - corrective run `33147562517`; exact-six inventory, healthy revisions, internal probes, Founder browser CIDR and cleanup passed |
| Founder Demo acceptance | ACCEPTED - Founder approved the corrected Demo application on 2026-08-28 |
| UAT runner delivery | PASS - preview `33149859100` and apply `33150103583`; private runner stack ACTIVE with zero residual executions |
| UAT deploy / verify | PASS - final run `33177257822`; exact-six, latest-ready revisions, functional checks, Web and OIDC endpoints passed |
| Cloud delivery consolidation | MERGED - PR #371 as `7211eb8`; temporary wrappers and deny-only promotion workflow removed |
| Lightweight workflow consolidation | MERGED - PR #388 as `72123e5`; release qualification moved into CI, runner operations consolidated, and durable workflows renamed by purpose |
| Current application foundation | DONE - PRs #373, #376, #381 and #386 added identity, public acquisition, admission and runtime adapter foundations after cloud qualification |
| Demo/runtime readiness repairs | MERGED - PRs #389 through #398 repaired cleanup provenance, cloud authority, dependency recovery, service startup, Temporal readiness and deployment verification |
| WC-078 public visual experience | IN PROGRESS - implementation `c079344a`, WebKit repair `1ed459cd`, scanner repair `8bcfb0a2`; WC-01 through WC-08 focus-validated, new clean WC-09 campaign and Founder review pending |
| Production | PLAN ONLY - code-prepared; protected environments, authorized plan, traffic and final acceptance remain Founder-reserved |

### Checkpoint Context

- **Authority:** WC-076 and FA-052 evidence authorized the completed Demo/UAT work recorded in PR #371. No current authority for Production apply, DNS activation or customer traffic is inferred.
- **Execution contract:** `work-contracts/WC-076-goal006-phase3-execution.md`; backlog P3-EX01 through P3-EX11.
- **Cloud state:** Demo is accepted; UAT is deployed and independently verified; both use private ephemeral runners and the signed exact-six release path. Production remains plan-only.
- **Canonical route:** strategy is owned by `architecture/reference/pipeline/azure-deployment-topology.md`; operators enter through `.github/workflows/deploy.yaml`; detailed immutable evidence remains in `goals/GOAL-006-cloud-platform-finalization-evidence.md`.
- **Boundary:** no Production plan/apply, DNS activation, customer traffic, Platform Operations activation, final Goal acceptance, self-approval or self-merge without separate current authority.

## Authorization Boundary

GOAL-006 Phase 3 execution is authorized only inside FA-052: the named Azure tenant/subscription,
Central India, INR 15,000 one-time and INR 10,000 monthly ceilings, Demo/UAT and dark Production
boundaries, independent evidence gates and validity period. FA-052 does not authorize customer
traffic, material Production risk acceptance, Platform Operations activation, final Goal acceptance,
PR approval or merge. A failed constitutional, security, evidence, recovery, scope or cost gate stops
progression.

## Current Blockers

P3-EX11 offline readiness remains blocked until INST-009 accepts the Production edge, data, runtime,
recovery, cost and shared-state ownership inputs. Provider-backed planning also requires protected
Production GitHub environments and exact current-session Founder authority.
C-001 emergency-halt integration blocks Production apply and activation, which remain prohibited.

## Next Authorized Action

Obtain INST-009 acceptance of the Production edge, data, runtime, recovery, cost and shared-state
ownership inputs required for P3-EX11 offline readiness. Do not activate the Production runner, run
a Production plan/apply, change DNS, or accept customer traffic without separate Founder authority.

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

Last PM report: 2026-08-25
Platform Status issue: see GitHub Issues with label `platform-status`
