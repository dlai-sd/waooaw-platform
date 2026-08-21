# PROJECT_STATE.md

**State Schema:** 2.0.0
**State Revision:** 83
**Last Updated:** 2026-08-26
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
| Latest completed Work Contract | WC-076 — GOAL-006 Demo Runner Delivery (PR #318 open, awaiting Founder merge) |
| Latest merge | PR #278 merged to `main` as `f28badc` on 2026-08-13 |
| Active delivery | GOAL-006 Phase 2 — Demo runner stack deployed (INACTIVE), PR #318 awaiting Founder review |

## Active Checkpoint — GOAL-006 Phase 2 Demo Runner Delivery

| Milestone | Status |
|---|---|
| WC-076 scope | DONE — reusable inactive runner blueprint with isolated Demo/UAT/Prod parameter contracts |
| Demo Deployment Stack | DEPLOYED — `goal006-demo-private-runner` state: succeeded, 20 managed resources, denyDelete/detachAll |
| Container Apps Jobs | DEPLOYED — `goal006-demo-runner-job` (Manual, INACTIVE) and `goal006-demo-runner-reconciler` (Schedule */5, INACTIVE) |
| ACA Environment | DEPLOYED — `goal006-demo-runner-aca` Succeeded, Consumption workload profile |
| NSG fix | DONE — AzurePlatformDNS replaced with 168.63.129.16/32; applies to all environments via shared main.bicep |
| verify_deployment | PASS — `"verified": true` at commit `8863d913c9a3a0998b613d466fb90d995f1cf8f6` |
| Plan digest (demo) | `sha256:9f5b6e0624d6b619d9694e71726f49db4f366cb14de680823579b6eed6d5cf8f` |
| 26 lifecycle tests | PASS |
| PR #318 | OPEN — `goal/006/reusable-runner-promotion` → `main`; awaiting Founder constitutional review |
| UAT | BLOCKED — requires Founder Demo acceptance |
| Production | BLOCKED — requires UAT acceptance |

| Milestone | Status |
|---|---|
| WC-071 intake contract | DONE — bounded to registration, Understanding, provisional Classification, and proposed Execution Plan |
| Goal Understanding Record | DONE — GUR-GOAL-006-INST-013-01 |
| Provisional Classification | DONE — GCL-GOAL-006-INST-013-01 proposes Cross-domain · Design · Constitutional · Elevated / P2 |
| Founder requirement baseline | DONE — FR-001 through FR-056 retained as controlling grooming requirements |
| Proposed Execution Plan | DONE — GEP-GOAL-006-INST-013-01; no GO Authorization issued |
| Deterministic validation | PASS — record IDs, requirement continuity, phase stops, approval controls, diagnostics, and diff checks |
| Fresh INST-002 review | DONE — R-106 READY WITH REQUIRED ACTION; NO CHALLENGE ISSUED |
| Phase 1 PR | DRAFT — PR #281 targets `main`; remains draft through P1-WC01 to P1-WC12 and Phase 1 closure |
| Founder classification and plan approval | DONE — ACK-GOAL-006-INST-001-01 recorded after R-106 |
| P1-WC01 Platform inventory GOA / Acceptance | VALID — GOA-GOAL-006-INST-009-01 at 08:54:36Z; ACC-GOAL-006-INST-009-01 at 08:54:37Z |
| P1-WC01 contribution / review | DONE — CR-GOAL-006-INST-009-01 accepted by R-107; P1-R01 through P1-R10 remain open |
| P1-WC02 Product Owner GOA / Acceptance | VALID — GOA-GOAL-006-INST-011-01 at 09:17:19Z; ACC-GOAL-006-INST-011-01 at 09:17:20Z |
| P1-WC02 contribution / review | DONE — CR-GOAL-006-INST-011-01 accepted by R-108; specialist targets and estimates remain open |
| P1-WC03 Platform Architect GOA / Acceptance | VALID — GOA-GOAL-006-INST-009-02 at 09:33:51Z; ACC-GOAL-006-INST-009-02 at 09:33:52Z |
| P1-WC03 contribution / review | DONE — CR-GOAL-006-INST-009-02 accepted by R-109; implementation/live risks remain open |
| P1-WC04 Solution Architect GOA / Acceptance | VALID — GOA-GOAL-006-INST-005-01 at 09:57:33Z; ACC-GOAL-006-INST-005-01 at 09:57:34Z |
| P1-WC04 contribution / review | DONE — topology and CT-02 scope decision accepted by R-110; CT-01 through CT-07 remain routed/open |
| P1-WC05 Security Architect GOA / Acceptance | VALID — GOA-GOAL-006-INST-007-01 at 10:19:26Z; ACC-GOAL-006-INST-007-01 at 10:19:27Z |
| P1-WC05 contribution / review | DONE — CR-GOAL-006-INST-007-01 accepted by R-111; implementation/live and protected Production risks remain open |
| P1-WC06 Data Architect GOA / Acceptance | VALID — GOA-GOAL-006-INST-006-01 at 10:36:21Z; ACC-GOAL-006-INST-006-01 at 10:36:22Z |
| P1-WC06 contribution / review | DONE — CR-GOAL-006-INST-006-01 accepted by R-112; Production objectives remain protected recommendations |
| P1-WC07 Platform IT Expert GOA / Acceptance | VALID — GOA-GOAL-006-INST-010-01 at 10:47:11Z; ACC-GOAL-006-INST-010-01 at 10:47:12Z |
| P1-WC07 contribution / review | DONE — conditionally feasible CR-GOAL-006-INST-010-01 accepted by R-113; Phase 2 prerequisites remain open |
| P1-WC08 QA GOA / Acceptance | VALID — GOA-GOAL-006-QA-01 at 11:09:38Z; ACC-GOAL-006-QA-01 at 11:09:39Z |
| P1-WC08 contribution / review | DONE — CR-GOAL-006-QA-01 accepted by R-114; targets and execution/live proof remain open |
| P1-WC09 Operations candidate GOA / Acceptance | VALID — GOA-GOAL-006-PLATFORM-OPS-01 at 11:17:28Z; ACC-GOAL-006-PLATFORM-OPS-01 at 11:17:29Z; candidate remains DRAFT/NOT ACTIVATED |
| P1-WC09 contribution / P1-WC10 review | DONE — CR-GOAL-006-PLATFORM-OPS-01 accepted by R-115 after bounded repairs; policy-dependent operations and all activation remain blocked |
| P1-WC11 Product Owner GOA / Acceptance | VALID — GOA-GOAL-006-INST-011-02 at 11:32:00Z; ACC-GOAL-006-INST-011-02 at 11:32:01Z |
| P1-WC11 contribution / owner review | DONE — CR-GOAL-006-INST-011-02 accepted at `495f7206...` by R-116 and all decision owners |
| P1-WC12 Constitutional GOA / Acceptance | VALID — GOA-GOAL-006-INST-002-02 at 11:52:00Z; ACC-GOAL-006-INST-002-02 at 11:52:01Z |
| P1-WC12 constitutional review | DONE — R-117 / CR-GOAL-006-INST-002-07 CLEAR WITH CONDITIONS at commit `db5f477`; no Constitutional Blocker |
| Phase 1 Founder control point | WAITING — exact R-117 acknowledgement may move PR #281 to Ready for Founder Review only; Phase 2 remains unauthorized |

### Intake Context

- **Delivery branch:** `goal/006/cloud-delivery-capability`.
- **Authority:** Founder instruction dated 2026-08-13 and WC-071 intake boundary.
- **Validation:** deterministic content checks and editor diagnostics pass; no runnable infrastructure or implementation changed.
- **Independent review:** R-106 / CR-GOAL-006-INST-002-01 finds the classification and plan ready, with post-review Founder acknowledgement as the sole routing predecessor.
- **Pull request:** PR #281 is the Phase 1 PR. Phase 2 implementation will use a separate later PR after Phase 1 closure and explicit implementation authorization.
- **Boundary:** Awaiting Founder Phase 1 acknowledgement only; no runnable changes, credentials/live access, cloud spend, DNS action, deployment, operation, Platform Operations activation, PR approval, or merge is authorized.
- **Protected local artifacts:** `.coverage`, `goals/goal_register.jsonl`, `logs/blueprint_assurance_report.json`, and `logs/bootstrap-evidence.jsonl` are unrelated and must remain unstaged.
- **Intake evidence:** `goals/GOAL-006-secure-autonomous-cloud-delivery.md`, `goals/GOAL-006-execution-plan.md`, and WC-071.

## Authorization Boundary

WC062-01 through WC062-07 were implemented under ACC-07, independently reviewed, and merged by the
Founder through PR #273. WC-063 was superseded before implementation. Founder selection authorizes
WC-064 owner-contribution routing, design, and grooming only. WC-065 through WC-069 require separate approved specifications,
constitutional readiness, acknowledgement, fresh implementation confirmation, GOA, Acceptance,
and independent implementation review. WC-071 authorizes GOAL-006 intake records only; it does not
authorize Phase 1 specialist grooming, Phase 2 implementation, or Phase 3 cloud deployment.

## Current Blockers

No constitutional blocker file is open. The three canonical operations policies remain downstream
dependencies; they block policy-dependent automation and Phase 3 handover/activation, not P1-WC11 grooming.

## Next Authorized Action

Founder reviews and merges PR #318. After merge, the official `runner-environment-delivery.yaml`
workflow runs on main for Demo preview + apply. UAT delivery requires explicit Founder Demo
acceptance. Production remains gated. Activation (INACTIVE → ACTIVE) is a separate authorized step.

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

Last PM report: 2026-08-13
Platform Status issue: see GitHub Issues with label `platform-status`
