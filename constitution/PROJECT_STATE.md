# PROJECT_STATE.md
**State Schema:** 2.0.0
**State Revision:** 384
**Last Updated:** 2026-11-27 (repository state through PR #656 merged as baf91f15df; checkpoint text below is hand-maintained)
**Purpose:** Current operational snapshot for bootstrap, recovery, and automated sprint controls; keep it below 200 lines, update checkpoints in place, and retain durable detail in the owning Work Contract, Goal, review, evidence artifact, Git history, or archive index.
---
## Institutional Snapshot

Counts, versions, dates and the latest delivered Work Contract are not typed here: they are derived by
`scripts/derive_platform_state.py` and rendered into `README.md` Platform Status, `SPRINT-REGISTRY.md`
(Work Contract index), `constitution/AGENT-ENTRY.md`, `ARCHITECTURE.md` and the Last Updated line above.
`scripts/run_platform_state_refresh.sh` refreshes them in Docker before every PR, and
`scripts/prepare_pr_body.py` plus the `quality:platform-state` gate fail when they are stale.

ROADMAP: `ROADMAP.md` is the only roadmap and progress record (Founder decision 2026-11-24, FR-006). Strategy:
platform-led, DMA-proved. Current iteration: Iteration 1 (WC-168), implementation in progress. Deviation needs the Founder's written approval.

RECONCILIATION (state revision 384, 2026-11-23): Revision 383 and its checkpoint narrative (WC-060 through
WC-136) are retained verbatim at git object `edd9f9e4:constitution/PROJECT_STATE.md` and indexed in
`PROJECT_STATE_ARCHIVE.md`. Pull requests #603 through #620 merged between 2026-11-20 and 2026-11-23 and
supersede revision 383's statements that WC-136 to WC-147 awaited Founder review or merge.

CURRENT POSITION: Gate G5 CLEAR, Implementation phase, autonomous halt false. Latest delivered Work Contracts on
`main` (merged PR evidence in the ledger): WC-136 Workbench, Spend Accounts and Pricing Engine (#604, every flag
default-off); WC-137 platform access and per-environment settings (#605); WC-138/139 CI speed-up and policy
enforcement (#606, #607); WC-140/142/143/145/146 Demo deployment-time reduction (#608, #610 to #613); WC-144
Founder pricing screen repairs (#614); WC-147 cloud workload credential issuance (#615, #616); WC-148 Founder
provider and credential screen (#617); WC-149 paid provider consumption (#618); WC-150 private listener start-up
guard (#619); WC-151 WID leaf issuer root-key defect (#620). WC-141 digest-gated validation reuse is scoped only.

OPEN, NOT CLOSED BY MERGES: WC-134 full completion still needs separately authorized protected Meta readback,
exact-candidate activation and spend, working alert receipt and own-number/public-sender live cohorts; WhatsApp
traffic stays governed by its own activation records. WC-136 open notes (Keycloak step-up setting, C3-02 free-tier
finding, deferred top-up purchase, RUN_NOW and CHANGE_APPROVAL_MODE) are recorded in its Implementation Record.
No Demo, live-provider or real-phone acceptance is claimed by this file. Work Contract files still carry the
status text written at authoring time, so merged records may read "IN PROGRESS"; the generated index lists the
merged PRs that reference each one.

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
CB-011 (`blockers/CB-011-wc109-product-qualification-gaps-2026-09-30.md`) remains OPEN and blocks release of
the products governed by AS-001, AS-003 and AS-005 until later agent product Work Contracts provide direct
passing evidence; the Founder-approved WC-109 disposition retains each as terminal `BLOCKED` with exact
`BLOCKED-DEFERRED` evidence and does not close CB-011 or authorize product readiness.
CB-009 (WC-085 tenant provisioning) records the contract gap resolved for the existing-stack path with
delivery qualification outstanding. CB-021 (ADR-046 cloud workload credentials) states design approved and
implementation in the IB-147 pull requests (#615, #616, merged); confirm and record its closure.
Item-level blockers older than 2026-10 are historical: read `blockers/` and the archived revision 383 only on demand.

## Next Authorized Action

No implementation Work Contract is selected by this file. Select the next item with the Founder from the open
items above and the generated Work Contract index. Do not infer deployment, provider activation, Azure, UAT,
Production, customer-traffic, approval or merge authority from repository qualification.

Obtain INST-009 acceptance of the Production edge, data, runtime, recovery, cost and shared-state
ownership inputs required for P3-EX11 offline readiness. Do not activate the Production runner, run
a Production plan/apply, change DNS, or accept customer traffic without separate Founder authority.

## History And Evidence

- WC-137 / IB-138 (platform access, per-environment feature settings, WhatsApp consent-first flow):
  `work-contracts/WC-137-platform-access-and-environment-feature-settings.md`; standing rules in
  `standards/PLATFORM-SETTINGS-AND-ACCESS-POLICY.md`.
- Revision 383 checkpoint narrative (2026-08-12 through 2026-11-20): git object
  `edd9f9e4:constitution/PROJECT_STATE.md`.
- History through 2026-07-22: `constitution/PROJECT_STATE_ARCHIVE.md`.
- History from 2026-07-23 through WC-059 closure: git object
  `b0dbe9c^2:constitution/PROJECT_STATE.md` (the merged PR #265 head snapshot).
- Schema-v2 governance record and independent review:
  `work-contracts/WC-061-project-state-v2-governance.md` and R-085.
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
