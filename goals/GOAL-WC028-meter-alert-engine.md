# GOAL-WC028 — WBE Meter + Alert Engine (Sprint Sub-Goal under GOAL-004)

**Goal ID:** GOAL-WC028
**Parent Goal:** GOAL-004 (WAOOAW Billing Engine)
**Sprint:** WC-028
**Status:** G-5 JOURNEY IN PROGRESS — awaiting Platform IT Expert (batch executor) activation
**Registrant:** Goal Orchestrator (INST-013) — 2026-07-31
**GO Session:** 2026-07-31
**Constitutional Basis:** C-043 (Budget Ceiling Enforcement), C-049 (Honest Limitation), C-051 (Resource Transparency), C-059 (Traceability), C-076 (≥90% test coverage)

---

## G-1 — Goal Registration

**Goal Statement:**
> "Implement the WBE Meter and Alert Engine sub-component: record every platform cost event
> against the customer's wallet bucket, project wallet depletion using a 7-day rolling average,
> and fire constitutional threshold alerts across three independent scopes (customer bucket,
> agency sub-wallet, WAOOAW procurement runway) per the §2.3a ladder — so that no customer
> silently runs out of budget and WAOOAW never blindly burns through its own provider accounts."

**Registered:** 2026-07-31
**Parent sprint:** WC-028 under IB-009 (Gate G5 → MVI)
**Evidence record location:** `goals/GOAL-WC028-meter-alert-engine.md` (this file)

---

## G-2 — Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### What This Goal Actually Means

The Meter + Alert Engine is not simply a usage counter. It is the **constitutional budget
transparency mechanism** mandated by C-043, C-049, and C-051. These three claims together
require that: every cost is recorded (C-059 traceability), every customer is warned before
they run out (C-049 honest limitation), and WAOOAW never silently overcommits provider
spend beyond its own runway (C-043 budget ceiling).

There are three operationally distinct responsibilities packed into this sprint, each with
its own data source and escalation channel:

**Responsibility 1 — Usage Recording:**
Every time the platform executes a thread call (LLM, WhatsApp, video generation), the cost
must land in `institutional.platform_cost_ledger`. The `MeterService.record_usage()` method
writes this row. Critically, `platform_cost_ledger.provider_account_id` is NOT NULL — the
service must resolve which provider account serviced this `thread_type` before writing.
The resolution path: `thread_type` → `institutional.thread_catalog` → `provider_accounts`.
This must be done with a DB lookup, not a hard-coded mapping.

**Responsibility 2 — Depletion Projection:**
The `project_depletion()` method computes days remaining at current burn rate, using the last
7 calendar days of `platform_cost_ledger` entries for the customer + thread_type. This is a
rolling average, not a lifetime average. The output is a `DepletionProjection` dataclass
(already defined in `wbe_interfaces.py`).

**Responsibility 3 — Threshold Alert Firing:**
The `run_daily_scan()` method (called at 06:00 IST via scheduler) iterates all active
wallet buckets and fires alerts per three independent scope ladders (§2.3a). It calls
`check_thresholds()` internally — that helper method is NOT exposed as a separate ABC method.
Tests call it directly via the concrete `MeterService` class, not through the ABC.

**The % consumed formula:**
`wallet_buckets` only stores `balance_paise` (remaining). There is no `initial_allocation_paise`
column. The correct % consumed computation is:
  `consumed_paise = SUM(platform_cost_ledger.marked_up_cost_inr_paise WHERE customer_id = X AND billing_period_start = current_period)`
  `pct_consumed = consumed_paise / (consumed_paise + balance_paise)`
This requires a join to `platform_cost_ledger` — it cannot be derived from `wallet_buckets` alone.

**The deduplication contract:**
`meter_alert_log` does NOT exist in `12-billing-engine.sql`. It must be added as an amendment
in the migration SQL — not as `CREATE IF NOT EXISTS` in service startup code (ADR-011 violation).
The table is: `(customer_id UUID, bucket_type VARCHAR(50), threshold_name VARCHAR(30),
period_id VARCHAR(7), fired_at TIMESTAMPTZ)` with UNIQUE on `(customer_id, bucket_type, threshold_name, period_id)`.
`period_id = YYYY-MM` (billing month).

### What This Goal Is NOT

- Real-time per-request alerting — this is a daily scan (06:00 IST). In-request checks are the wallet reservation service's concern.
- WhatsApp delivery infrastructure — `WhatsAppNotifier` is a stub pointing to ADR-023 (360dialog MCP). Tests mock it.
- Agency hierarchy management — the agency sub-wallet threshold (Scope 2) alerts the agency owner but does not affect child wallet authorisation.
- Scheduler infrastructure — `POST /meter/daily-scan` is the trigger endpoint. The actual APScheduler setup is WC-030's job.

### Key Design Decisions Confirmed During Understanding

| Decision | Resolved | Source |
|---|---|---|
| `record_usage` parameter name | `amount_paise` — matches `IMeterService` skeleton | `wbe_interfaces.py` line 79 |
| `provider_account_id` resolution | Lookup `thread_catalog` → `provider_accounts` by thread_type | `platform_cost_ledger` NOT NULL constraint |
| `% consumed` formula | `consumed / (consumed + balance)` — `platform_cost_ledger` SUM join | `wallet_buckets` has no initial_allocation column |
| `check_thresholds` is NOT a skeleton method | It is a `MeterService` public helper, called by `run_daily_scan` | `IMeterService` ABC has `run_daily_scan`, not `check_thresholds` |
| `meter_alert_log` DDL location | Must be in `12-billing-engine.sql` amendment (ADR-011) | Not in service startup — DDL in service code is prohibited |
| WARN_10 triggers at ≤10% remaining | Bucket at 5–10% remaining fires WARN_10 — NOT 15% | §2.3a: "≥90% consumed = 10% remaining" |
| Scope 3 threshold names | Not named in spec — derive from days: RUNWAY_P2 (≤30d), RUNWAY_P1 (≤14d), RUNWAY_P0 (≤7d), RUNWAY_CRITICAL (≤3d), RUNWAY_EMERGENCY (≤1d) | §2.3a Scope 3 table |
| Quiet hours | 23:00–06:00 IST — WhatsApp not dispatched, queued | §2.3a quiet hours clause |

---

## G-3 — Classification

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Dimension | Classification | Reasoning |
|---|---|---|
| **Complexity** | HIGH | Three independent scope ladders + deduplication + % consumed JOIN computation + provider resolution |
| **Constitutional Priority** | TIER 1 — Blocking | C-043 (budget ceiling) is a hard constitutional gate — no ongoing sprint can be compliant without threshold enforcement |
| **Institution routing** | EA → SA → PO → Platform IT Expert | 5 spec gaps found — WC must be corrected before groomer runs |
| **Evidence requirement** | Contribution Records + `meter_alert_log` rows in tests + CCT-BILLINGLOOP-01 passing | C-059 + C-076 |

**Risk flags identified at classification:**
- RISK-WC028-01: `meter_alert_log` DDL in service startup — ADR-011 migration strategy violation. Must be in SQL migration.
- RISK-WC028-02: DoD threshold test scenario mathematically wrong — 15% remaining fires WARN_30 not WARN_10.
- RISK-WC028-03: No guidance on `provider_account_id` resolution — batch executor will likely hard-code or skip, breaking the NOT NULL constraint.
- RISK-WC028-04: `% consumed` formula not specified — batch executor may use wrong denominator.

---

## G-4 — Execution Plan

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### Institution Routing (in sequence)

| Step | Institution | GO Authorization | Contribution Required | Evidence |
|---|---|---|---|---|
| 1 | EA — Enterprise Architect (INST-005) | GOA-WC028-01 | Spec gap review against DB schema, skeleton, §2.3a | EA Contribution Record |
| 2 | SA — Solution Architect (INST-009) | GOA-WC028-02 | Fix gaps in WC-028 + add `meter_alert_log` to DB migration | SA Contribution Record + updated WC file + updated SQL |
| 3 | PO — Product Owner (INST-011) | GOA-WC028-03 | Validate 3-task decomposition and model_hint assignments | PO Contribution Record |
| 4 | Platform IT Expert (INST-010) | GOA-WC028-04 | Implement WC-028 via autonomous sprint batch executor | Code + tests + PR |

**Step 4 activated only by explicit Founder authorisation (`autonomous_halt: false`) after WC-027 merges.**

---

## G-5 — Goal Journey — Institution Contribution Records

### GOA-WC028-01 — EA Contribution Record

**Institution:** Enterprise Architect (INST-005)
**GO Authorization:** GOA-WC028-01
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Spec Gaps Found

| Gap ID | Location | Finding | Correction Required |
|---|---|---|---|
| GAP-WC028-01 | WC028-01 scope, task table | `record_usage(customer_id, thread_type, consumed_paise)` — uses `consumed_paise` but skeleton `IMeterService` line 79 uses `amount_paise` | Rename parameter to `amount_paise` to match ABC |
| GAP-WC028-02 | "Alert Deduplication Implementation Note" | "add `meter_alert_log` migration OR `CREATE IF NOT EXISTS` inside service startup" — DDL in service code violates ADR-011 (all schema changes via migration SQL only) | Remove service-startup DDL option; direct batch executor to add `meter_alert_log` as an amendment in `12-billing-engine.sql` |
| GAP-WC028-03 | DoD item 2 | "`check_thresholds(customer_id)` with bucket at **15% remaining** → fires `WARN_10` alert" — mathematically wrong: 15% remaining = 85% consumed, which fires WARN_30 (≥70% consumed) not WARN_10 (≥90% consumed = ≤10% remaining) | Fix to: "at **8% remaining** (92% consumed) → fires WARN_10" |
| GAP-WC028-04 | WC028-01 scope + Notes | No specification for how `% consumed` is computed — `wallet_buckets` only has `balance_paise` (remaining), no `initial_allocation` column | Add explicit formula: `pct_consumed = SUM(platform_cost_ledger.marked_up_cost_inr_paise WHERE customer_id = X AND billing_period_start = current_period) / (consumed + balance_paise)` |
| GAP-WC028-05 | WC028-01 scope, Required Inputs | No guidance on `provider_account_id` resolution — `platform_cost_ledger.provider_account_id` is NOT NULL; `record_usage(amount_paise)` does not pass a provider ID | Add: resolve via `institutional.thread_catalog` → `provider_name` → `institutional.provider_accounts.provider_name` lookup |
| GAP-WC028-06 | WC028-01 scope | `check_thresholds(customer_id) -> list[AlertFired]` described as a `MeterService` method but it is not in `IMeterService` ABC — creates ambiguity for batch executor | Clarify: `check_thresholds` is a `MeterService` concrete method (not ABC), called internally by `run_daily_scan`; tests call it directly on the concrete instance |

#### Additional Precision Notes (for SA to incorporate)

- Scope 3 procurement threshold names not defined in §2.3a — SA should specify: `RUNWAY_P2` (≤30d), `RUNWAY_P1` (≤14d), `RUNWAY_P0` (≤7d), `RUNWAY_CRITICAL` (≤3d), `RUNWAY_EMERGENCY` (≤1d).
- `run_daily_scan` is the ABC method (present in skeleton). `check_thresholds` is a public non-abstract helper.
- The deduplication `period_id` format should be explicit: `YYYY-MM` (e.g. `2026-07`).
- WC028-02 scope references `GET /platform/margin/report` — this endpoint is spec-defined under §2.4 (Procurement), not Meter. Should be either moved to WC-029 scope or explicitly delegated to a stub.

**Learning Record:**
WC files for the meter engine must be cross-validated against: (1) skeleton IMeterService ABC signatures, (2) DB schema column names (especially NOT NULL constraints), (3) the threshold ladder % mathematics. Arithmetic errors in DoD test scenarios will cause the batch executor to write incorrect test fixtures and pass on wrong thresholds.

---

### GOA-WC028-02 — SA Contribution Record

**Institution:** Solution Architect (INST-009)
**GO Authorization:** GOA-WC028-02
**Contribution date:** 2026-07-31
**Status:** COMPLETE
**Files modified:** `work-contracts/WC-028-wbe-s4-meter-alert-engine.md`, `infrastructure/postgres/init/12-billing-engine.sql`

#### Changes Made to WC-028

1. **GAP-WC028-01 fixed:** `consumed_paise` → `amount_paise` in task scope + Notes.
2. **GAP-WC028-02 fixed:** Removed "CREATE IF NOT EXISTS inside service startup" option. Added explicit directive: `meter_alert_log` to be added as an SQL amendment in `12-billing-engine.sql`.
3. **GAP-WC028-03 fixed:** DoD scenario corrected: "8% remaining (92% consumed) → fires WARN_10".
4. **GAP-WC028-04 fixed:** Added `pct_consumed` formula to WC028-01 scope and C-043 Implementation Note.
5. **GAP-WC028-05 fixed:** Added `provider_account_id` resolution note: lookup `thread_catalog → provider_accounts`.
6. **GAP-WC028-06 fixed:** `check_thresholds` clarified as `MeterService` concrete public method, not ABC — called by `run_daily_scan`, testable directly.
7. **Scope 3 threshold names added:** `RUNWAY_P2`, `RUNWAY_P1`, `RUNWAY_P0`, `RUNWAY_CRITICAL`, `RUNWAY_EMERGENCY`.
8. **`GET /platform/margin/report` deferred:** Noted as WC-029 scope (Procurement) — WC028-02 drops this endpoint from the router.
9. **`meter_alert_log` added to `12-billing-engine.sql`** as a properly indexed amendment.

See corrected files for full changes.

---

### GOA-WC028-03 — PO Contribution Record

**Institution:** Product Owner (INST-011)
**GO Authorization:** GOA-WC028-03
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Task Decomposition Validation

| Task | Files | model_hint | Assessment |
|---|---|---|---|
| WC028-01 | `meter/service.py` + `meter/alert_policy.py` | reasoning | ✅ Correct — three-scope policy + % consumed JOIN + deduplication require deep reasoning |
| WC028-02 | `meter/whatsapp_notifier.py` + `meter/router.py` + `main.py` mount | auto | ✅ Correct — stub + router is structural |
| WC028-03 | `tests/billing-engine/test_meter.py` | auto | ✅ Correct — test scaffolding follows established pattern |

**Sprint capacity:** 3 tasks is within one sprint. No over-scoping.
**model_hint assignments:** Correct — reasoning for business + constitutional logic, auto for structural + tests.
**Groomer compatibility:** `WC028-01`, `WC028-02`, `WC028-03` match groomer regex. ✅
**PO authorisation:** APPROVED pending Founder `autonomous_halt: false` + WC-027 merge.

---

## G-6 — Evidence Validation Checklist

*To be completed by Constitutional Analyst (INST-002) before G-7 Completion*

- [ ] EA Contribution Record present — all 6 gaps with source references
- [ ] SA Contribution Record present — all fixes documented and committed
- [ ] PO Contribution Record present — decomposition validated
- [ ] `WC-028` uses `amount_paise` (not `consumed_paise`)
- [ ] `WC-028` DoD has "8% remaining → fires WARN_10" (not 15%)
- [ ] `WC-028` has `pct_consumed` formula explicit
- [ ] `WC-028` has `provider_account_id` resolution guidance
- [ ] `12-billing-engine.sql` has `meter_alert_log` table with correct schema + UNIQUE constraint
- [ ] `WC-028` `check_thresholds` clarified as concrete non-ABC method
- [ ] Scope 3 threshold names (`RUNWAY_P2/P1/P0/CRITICAL/EMERGENCY`) present in WC
- [ ] `constitution/PROJECT_STATE.md` will reflect `current_sprint: WC-028` when WC-027 merges

---

## G-7 — Completion Declaration

**Status:** PENDING — awaiting G-6 validation, WC-027 merge, + Founder `autonomous_halt: false`

Completion criteria:
- All G-6 checklist items checked
- WC-027 PR merged (markup engine live — `BundleEngine` importable by `MeterService`)
- `autonomous_halt: false` set by Founder
- Groomer injects WC028-01/02/03 SubTaskDefs into TASK_HANDLERS
- Batch executor PR: `meter/service.py`, `meter/alert_policy.py`, `meter/whatsapp_notifier.py`, `meter/router.py`, `tests/billing-engine/test_meter.py`
- `pytest tests/billing-engine/test_meter.py` passes — CCT-BILLINGLOOP-01 included
- `meter_alert_log` rows present in test assertions (C-059 evidence)
- `pricing_floor_log` NOT touched — that is WC-027's concern
