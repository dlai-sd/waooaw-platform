# Blueprint Execution Plan — WBE Core Sprints + GOAL-005 Customer Acquisition

**Authority:** Enterprise Architect (INST-005) — session 2026-07-31
**Scope:** WC-027 → WC-030 (WBE remaining sub-components) + GOAL-005 (cross-module customer acquisition)
**Purpose:** Produce all work contracts, spec documents, and groomed sprint state so each sprint
is ready for handover to the anonymous batch executor (GitHub Actions autonomous-sprint.yaml).
**Execution agent:** Goal Orchestrator — reads this file top-to-bottom, executes each `[ ]` step,
checks it off, commits progress at end of each Phase.
**Handover definition:** A sprint is ready for the batch executor when:
  - `work-contracts/WC-NNN-*.md` exists with valid task table (task_id | scope | model_hint | status)
  - `constitution/PROJECT_STATE.md` has `current_sprint: WC-NNN`, `sprint_status: READY`, `autonomous_halt: false`
  - `scripts/groom_sprint.py WC-NNN` has run successfully (SubTaskDefs injected into TASK_HANDLERS)
  - All files committed and pushed to `main`

---

## Phase 1 — WC-027: WBE-S3 Markup Engine

**Batch executor will run after:** WC-026 (Wallet Engine) PR merged ✅

### Blueprint Steps

- [x] **1.1** Create `work-contracts/WC-027-wbe-s3-markup-engine.md` — task table with WC027-01, WC027-02
- [x] **1.2** Update `constitution/PROJECT_STATE.md` SPRINT_STATE_MACHINE:
      `current_sprint: WC-027`, `sprint_status: READY`, `branch: ib/009/sprint-027`,
      `tasks_remaining: [WC027-01, WC027-02]`, `autonomous_halt: false`
- [x] **1.3** Run: `python3 scripts/groom_sprint.py WC-027` — verify SubTaskDefs injected
- [x] **1.4** Commit: `chore(pm): WC-027 markup engine blueprint ready for batch executor`
- [x] **1.5** Push to `main`

**✅ HANDOVER POINT:** WC-027 active sprint — batch executor will create branch `ib/009/sprint-027`,
implement markup engine, open PR. Reviewer merges → advances to Phase 2.

---

## Phase 2 — WC-028: WBE-S4 Meter + Alert Engine

**Batch executor will run after:** WC-027 PR merged (markup/ sub-component live)
**Prerequisite:** `architecture/reference/billing/wbe-component-spec.md §2.3a` (threshold ladder) must be
committed before this sprint runs. ✅ Done — committed `d591b6c` (Amendment 1, 2026-07-31).

### Blueprint Steps

- [x] **2.1** Create `work-contracts/WC-028-wbe-s4-meter-alert-engine.md` — task table with WC028-01, WC028-02, WC028-03
- [ ] **2.2** After WC-027 merges: Update PROJECT_STATE to `current_sprint: WC-028`, `sprint_status: READY`,
      `branch: ib/009/sprint-028`, `autonomous_halt: false`
- [ ] **2.3** After PROJECT_STATE update: Run `python3 scripts/groom_sprint.py WC-028`
- [ ] **2.4** Commit + push

**✅ HANDOVER POINT:** WC-028 active sprint — batch executor implements meter/ + alert_policy.py.

---

## Phase 3 — WC-029: WBE-S5 Platform Procurement Ledger

**Batch executor will run after:** WC-028 PR merged (MeterService live for ThresholdPolicy import)

### Blueprint Steps

- [x] **3.1** Create `work-contracts/WC-029-wbe-s5-platform-procurement.md` — task table with WC029-01, WC029-02
- [ ] **3.2** After WC-028 merges: Update PROJECT_STATE to `current_sprint: WC-029`, `sprint_status: READY`,
      `branch: ib/009/sprint-029`, `autonomous_halt: false`
- [ ] **3.3** After PROJECT_STATE update: Run `python3 scripts/groom_sprint.py WC-029`
- [ ] **3.4** Commit + push

**✅ HANDOVER POINT:** WC-029 active sprint — batch executor implements procurement/ + FA generation.

---

## Phase 4 — WC-030: WBE-S6 Reconciliation Engine

**Batch executor will run after:** WC-029 PR merged (ProcurementService live for margin data)

### Blueprint Steps

- [x] **4.1** Create `work-contracts/WC-030-wbe-s6-reconciliation.md` — task table with WC030-01, WC030-02, WC030-03
- [ ] **4.2** After WC-029 merges: Update PROJECT_STATE to `current_sprint: WC-030`, `sprint_status: READY`,
      `branch: ib/009/sprint-030`, `autonomous_halt: false`
- [ ] **4.3** After PROJECT_STATE update: Run `python3 scripts/groom_sprint.py WC-030`
- [ ] **4.4** Commit + push

**✅ HANDOVER POINT:** WC-030 active sprint — batch executor implements reconciliation/ + APScheduler.
After WC-030 merges: WBE core is complete. Advance to GOAL-005 Phase 5.

---

## Phase 5 — GOAL-005: Customer Acquisition Blueprint (Cross-Module Spec + WC Files)

**Authorisation gate:** Founder must record pricing decisions in `security/FOUNDER-ACTIONS.md` before
any GOAL-005 implementation sprint runs. The blueprint steps below (spec + WC files) can be
executed immediately, but `autonomous_halt` remains `true` for all GOAL-005 sprints until FA is received.

### Why this is complex — cross-module state map

| Module | State when GOAL-005 runs | Impact |
|---|---|---|
| `src/billing-engine/wallet/` | ✅ Code complete (WC-026) | trial/ sub-component reads WalletService — import only |
| `src/billing-engine/markup/` | ✅ Code complete (WC-027) | trial/ reads BundleEngine for cost_floor — import only |
| `src/billing-engine/meter/` | ✅ Code complete (WC-028) | TrialService hooks into check_thresholds — additive |
| `src/billing-engine/procurement/` | ✅ Code complete (WC-029) | trial/ free-unit cost debited via ProcurementService — import only |
| `src/billing-engine/reconciliation/` | ✅ Code complete (WC-030) | Reconciliation audit includes trial buckets — additive |
| `src/billing-engine/trial/` | ❌ New design + spec required | WBE sub-component 6 — created in WC-031 |
| `src/billing-engine/promotions/` | ❌ New design + spec required | WBE sub-component 7 — created in WC-031 |
| `src/ai-runtime/pse/router.py` | ⚠️ Spec exists, code in progress | Add `customer_mode=TRIAL` → force `LlmTier.LOCAL` — small additive change |
| `src/bp/subscriptions/` | ⚠️ Spec exists, code in progress | Add `POST /subscriptions/trial-start` endpoint + Temporal trial expiry saga |
| `web/` (Next.js portal) | ❌ Not started (WC-016 pending) | Founder admin pages: markup designer + trial/coupon config |
| `infrastructure/postgres/init/` | ⚠️ Has 12 init files | New migration `13-customer-acquisition.sql` — trial_allocations + coupon_codes tables |

### Blueprint Steps

#### 5A — Spec Phase (EA/SA produces design documents)

- [x] **5A.1** Create `architecture/reference/billing/customer-acquisition-spec.md`
      — TrialService + PromotionsService API contracts + data models + CCTs.
      Authority: Solution Architect (INST-005). Mirrors wbe-component-spec.md structure.
- [x] **5A.2** Create `infrastructure/postgres/init/13-customer-acquisition.sql`
      — `trial_allocations`, `trial_free_unit_ledger`, `coupon_codes`, `referral_records` tables.
      Follows same schema conventions as `12-billing-engine.sql`.
- [x] **5A.3** Update `architecture/reference/billing/wbe-component-spec.md` §1 Service Structure
      — Add `trial/` (sub-component 6) and `promotions/` (sub-component 7) to the directory tree.
- [x] **5A.4** Create `work-contracts/WC-031-goal005-wbe-trial-promotions.md`
      — WBE sub-components 6 + 7: TrialService, PromotionsService, DB migration.
      `autonomous_halt: true` on first READY (Founder FA gate).
- [x] **5A.5** Create `work-contracts/WC-032-goal005-air-pse-trial-override.md`
      — AIR PSE router: add `customer_mode=TRIAL` tier forcing. Single-file change + tests.
      **Depends on:** WC-031.
- [x] **5A.6** Create `work-contracts/WC-033-goal005-bp-trial-lifecycle.md`
      — BP subscription service: `POST /subscriptions/trial-start`, Temporal trial expiry signal.
      **Depends on:** WC-031.
- [x] **5A.7** Create `work-contracts/WC-034-goal005-webportal-founder-admin.md`
      — Web Portal (Next.js): Founder-only admin pages — markup designer + trial config + coupon manager.
      **Depends on:** WC-016 (web portal scaffold), WC-031.
- [ ] **5A.8** Commit: `spec(goal005): customer acquisition blueprint — spec doc + WC-031..034 + DB migration`
- [ ] **5A.9** Push to `main`

#### 5B — Activation (after Founder FA received + WC-030 merged)

- [ ] **5B.1** Verify FA received: `security/FOUNDER-ACTIONS.md` has trial budget + coupon caps signed by Founder
- [ ] **5B.2** Update PROJECT_STATE: `current_sprint: WC-031`, `sprint_status: READY`, `autonomous_halt: false`
- [ ] **5B.3** Run `python3 scripts/groom_sprint.py WC-031`
- [ ] **5B.4** Commit + push → batch executor activates

**✅ HANDOVER POINT (GOAL-005 WBE):** WC-031 active — batch executor implements trial/ + promotions/.
WC-032, WC-033, WC-034 follow in sequence after each prior sprint merges (same advance pattern as Phases 2–4).

---

## Execution Summary

| Phase | WC | Status | Handover condition |
|---|---|---|---|
| 1 | WC-027 Markup Engine | ✅ Blueprint complete — sprint ACTIVE | Batch executor running |
| 2 | WC-028 Meter + Alert | ✅ WC file created | WC-027 PR merged → advance state → groom |
| 3 | WC-029 Procurement | ✅ WC file created | WC-028 PR merged → advance state → groom |
| 4 | WC-030 Reconciliation | ✅ WC file created | WC-029 PR merged → advance state → groom |
| 5A | GOAL-005 Spec | ✅ Spec + WC files created | WC-030 merged + Founder FA received |
| 5B | WC-031 Trial + Promos | ⏳ Blocked on Founder FA | FA received → set READY → groom |
| — | WC-032 PSE override | ⏳ Blocked on WC-031 | WC-031 merged → advance |
| — | WC-033 BP trial lifecycle | ⏳ Blocked on WC-031 | WC-031 merged → advance |
| — | WC-034 Web Portal admin | ⏳ Blocked on WC-016 + WC-031 | Both merged → advance |

**State-advance command template (run after each PR merges):**
```bash
python3 scripts/sprint_state.py set \
  current_sprint WC-NNN \
  sprint_status READY \
  branch ib/009/sprint-NNN \
  tasks_done "" \
  tasks_remaining "WCNNN-01,WCNNN-02,..." \
  consecutive_failures 0 \
  autonomous_halt false
python3 scripts/groom_sprint.py WC-NNN
git add -A && git commit -m "chore(pm): WC-NNN blueprint ready for batch executor" && git push
```
