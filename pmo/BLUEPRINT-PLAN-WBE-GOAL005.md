# GO Execution Plan — WBE Sprints WC-027 through WC-031

**Authority:** Enterprise Architect (INST-005) — session 2026-07-31
**Scope:** WC-027, WC-028, WC-029, WC-030, WC-031 — five sequential sprints
**Purpose:** Single GO input document. GO reads this top-to-bottom, executes each `[ ]` step for
the active phase, checks it off, and commits. Each phase activates only after Founder authorises.
**Execution agent:** Goal Orchestrator
**All sprints parked:** `autonomous_halt: true` — Founder must explicitly authorise each sprint
before GO sets `sprint_status: READY` and runs the groomer.

**Handover definition — a sprint is ready for the batch executor when ALL of the following are true:**
  - `work-contracts/WC-NNN-*.md` exists with valid task table (task_id | scope | model_hint | status)
  - `constitution/PROJECT_STATE.md` has `current_sprint: WC-NNN`, `sprint_status: READY`, `autonomous_halt: false`
  - `scripts/groom_sprint.py --sprint WC-NNN` has run successfully (SubTaskDefs injected into TASK_HANDLERS)
  - All files committed and pushed to `main`

**GO must not set `autonomous_halt: false` without explicit Founder instruction.**

---

## Phase 1 — WC-027: WBE-S3 Markup Engine

**Prerequisite:** WC-026 (Wallet Engine) PR merged ✅
**WC file:** `work-contracts/WC-027-wbe-s3-markup-engine.md` ✅ created
**State:** PARKED — `autonomous_halt: true`, `sprint_status: WAITING`

### GO Activation Steps (run when Founder authorises WC-027)

- [x] **1.1** `python3 scripts/sprint_state.py set autonomous_halt false` — executed 2026-07-31; `autonomous_halt: false` set in SPRINT_STATE_MACHINE
      _(tasks_remaining already correct: WC027-01a, WC027-01b, WC027-02 — set when GEOM pipeline ran)_
- [ ] **1.2** `python3 scripts/groom_sprint.py --sprint WC-027` — **runs automatically in CI** on workflow dispatch; no local execution needed
- [x] **1.3** `git add -A && git commit -m "chore(pm): WC-027 READY — markup engine authorised" && git push` — executed 2026-07-31

**⏳ HANDOVER POINT:** Batch executor creates branch `ib/009/sprint-027`, implements markup engine, opens PR.
Reviewer merges → Founder authorises Phase 2.

---

## Phase 2 — WC-028: WBE-S4 Meter + Alert Engine

**Prerequisite:** WC-027 PR merged ✅ (markup/ sub-component live)
**Prerequisite:** `wbe-component-spec.md §2.3a` threshold ladder ✅ committed `d591b6c`
**WC file:** `work-contracts/WC-028-wbe-s4-meter-alert-engine.md` ✅ created + GO-validated (2026-07-31)
**GO record:** `goals/GOAL-WC028-meter-alert-engine.md` ✅ — G-1→G-5 complete, 6 spec gaps fixed
**DB migration:** `12-billing-engine.sql` ✅ `meter_alert_log` amendment added (WC-028 SA contribution)
**State:** PARKED — waiting for Phase 1 merge + Founder authorisation

### GO Activation Steps (run when Founder authorises WC-028)

- [ ] **2.1** `python3 scripts/sprint_state.py set current_sprint WC-028 sprint_status READY branch ib/009/sprint-028 tasks_remaining "WC028-01,WC028-02,WC028-03" consecutive_failures 0 autonomous_halt false`
- [ ] **2.2** `python3 scripts/groom_sprint.py --sprint WC-028` — verify WC028-01, WC028-02, WC028-03 injected
- [ ] **2.3** `git add -A && git commit -m "chore(pm): WC-028 READY — meter + alert engine authorised" && git push`

**⏳ HANDOVER POINT:** Batch executor creates branch `ib/009/sprint-028`, implements meter/ + alert_policy.py.

---

## Phase 3 — WC-029: WBE-S5 Platform Procurement Ledger

**Prerequisite:** WC-028 PR merged (MeterService + PROCUREMENT_POLICY live)
**WC file:** `work-contracts/WC-029-wbe-s5-platform-procurement.md` ✅ created + GO-validated (2026-07-31)
**GO record:** `goals/GOAL-WC029-procurement-ledger.md` ✅ — G-1→G-5 complete, 8 spec gaps fixed
**State:** PARKED — waiting for Phase 2 merge + Founder authorisation

### GO Activation Steps (run when Founder authorises WC-029)

- [ ] **3.1** `python3 scripts/sprint_state.py set current_sprint WC-029 sprint_status READY branch ib/009/sprint-029 tasks_remaining "WC029-01,WC029-02" consecutive_failures 0 autonomous_halt false`
- [ ] **3.2** `python3 scripts/groom_sprint.py --sprint WC-029` — verify WC029-01, WC029-02 injected
- [ ] **3.3** `git add -A && git commit -m "chore(pm): WC-029 READY — procurement ledger authorised" && git push`

**⏳ HANDOVER POINT:** Batch executor creates branch `ib/009/sprint-029`, implements procurement/ + FA generation.

---

## Phase 4 — WC-030: WBE-S6 Reconciliation Engine

**Prerequisite:** WC-029 PR merged (ProcurementService live for margin data)
**WC file:** `work-contracts/WC-030-wbe-s6-reconciliation.md` ✅ created + GO-validated (2026-07-31)
**GO record:** `goals/GOAL-WC030-reconciliation-engine.md` ✅ — G-1→G-5 complete, 6 spec gaps fixed
**State:** PARKED — waiting for Phase 3 merge + Founder authorisation

### GO Activation Steps (run when Founder authorises WC-030)

- [ ] **4.1** `python3 scripts/sprint_state.py set current_sprint WC-030 sprint_status READY branch ib/009/sprint-030 tasks_remaining "WC030-01,WC030-02,WC030-03" consecutive_failures 0 autonomous_halt false`
- [ ] **4.2** `python3 scripts/groom_sprint.py --sprint WC-030` — verify WC030-01, WC030-02, WC030-03 injected
- [ ] **4.3** `git add -A && git commit -m "chore(pm): WC-030 READY — reconciliation engine authorised" && git push`

**⏳ HANDOVER POINT:** Batch executor creates branch `ib/009/sprint-030`, implements reconciliation/ + APScheduler.
After WC-030 merges: WBE core complete. Advance to Phase 5.

---

## Phase 5 — WC-031: GOAL-005 WBE Trial + Promotions Engine

**Prerequisite:** WC-030 PR merged (full WBE core complete)
**Prerequisite (hard gate):** Founder FA in `security/FOUNDER-ACTIONS.md` with trial budget + discount caps
**WC file:** `work-contracts/WC-031-goal005-wbe-trial-promotions.md` ✅ created + GO-validated (2026-07-31)
**GO record:** `goals/GOAL-WC031-trial-promotions.md` ✅ — G-1→G-5 complete, 9 spec gaps fixed
**Spec doc:** `architecture/reference/billing/customer-acquisition-spec.md` ✅ created
**DB migration:** `infrastructure/postgres/init/13-customer-acquisition.sql` ✅ created
**State:** PARKED — HARD BLOCKED on Founder FA (5 pricing decisions required — see GO record G-7)

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

### GO Activation Steps (run when Founder FA received + WC-030 merged)

- [ ] **5.1** Verify `security/FOUNDER-ACTIONS.md` has FA with trial budget + coupon caps signed by Founder
- [ ] **5.2** `python3 scripts/sprint_state.py set current_sprint WC-031 sprint_status READY branch ib/009/sprint-031 tasks_remaining "WC031-01,WC031-02,WC031-03" consecutive_failures 0 autonomous_halt false`
- [ ] **5.3** `python3 scripts/groom_sprint.py --sprint WC-031` — verify WC031-01, WC031-02, WC031-03 injected
- [ ] **5.4** `git add -A && git commit -m "chore(pm): WC-031 READY — trial + promotions engine authorised" && git push`

**⏳ HANDOVER POINT (WC-031):** Batch executor implements trial/ + promotions/.
WC-032, WC-033, WC-034 follow same pattern after each prior sprint merges.

---

## Execution Summary

| Phase | WC | WC File | State | GO activates when |
|---|---|---|---|---|
| 1 | WC-027 Markup Engine | ✅ ready | ⏳ PARKED | Founder says "run WC-027" |
| 2 | WC-028 Meter + Alert | ✅ ready | ⏳ PARKED | WC-027 merged + Founder authorises |
| 3 | WC-029 Procurement | ✅ ready | ⏳ PARKED | WC-028 merged + Founder authorises |
| 4 | WC-030 Reconciliation | ✅ ready | ⏳ PARKED | WC-029 merged + Founder authorises |
| 5 | WC-031 Trial + Promos | ✅ ready | ⏳ PARKED | WC-030 merged + Founder FA (pricing) received |
| — | WC-032 PSE override | ✅ ready | ⏳ PARKED | WC-031 merged + Founder authorises |
| — | WC-033 BP trial lifecycle | ✅ ready | ⏳ PARKED | WC-031 merged + Founder authorises |
| — | WC-034 Web Portal admin | ✅ ready | ⏳ PARKED | WC-016 + WC-031 merged + Founder authorises |

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
