# GOAL-WC030 — WBE Reconciliation Engine (Sprint Sub-Goal under GOAL-004)

**Goal ID:** GOAL-WC030
**Parent Goal:** GOAL-004 (WAOOAW Billing Engine)
**Sprint:** WC-030
**Status:** G-5 JOURNEY IN PROGRESS — awaiting Platform IT Expert (batch executor) activation
**Registrant:** Goal Orchestrator (INST-013) — 2026-07-31
**GO Session:** 2026-07-31
**Constitutional Basis:** C-091 (WBE self-audit gate), C-023 (Evidence First), C-059 (Traceability), C-076 (≥90% coverage)

---

## G-1 — Goal Registration

**Goal Statement:**
> "Implement the WBE Reconciliation Engine — the financial integrity floor of the entire billing
> stack: prove every rupee in every wallet bucket against its ledger entries daily, halt all
> billing if any discrepancy exceeds 1 paise (C-091), generate Founder Actions automatically,
> and give operators the tools to recover — so that WAOOAW can never unknowingly operate on
> corrupted financial state."

**Registered:** 2026-07-31
**Parent sprint:** WC-030 under IB-009 (Gate G5 → MVI). This sprint completes the WBE core.
**Evidence record location:** `goals/GOAL-WC030-reconciliation-engine.md` (this file)

---

## G-2 — Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### What This Goal Actually Means

The Reconciliation Engine is the **constitutional enforcement layer for financial correctness**.
Unlike every other WBE sub-component which is additive (new capability), this sprint is also
**corrective** — it adds a billing halt guard to the already-implemented `WalletService.reserve()`
from WC-026. The batch executor for WC-030 must modify code in `wallet/service.py` (a prior sprint
file) in addition to creating the new `reconciliation/` package.

There are four distinct responsibilities:

**Responsibility 1 — Self-Audit (C-091 enforcement):**
`run_self_audit()` computes expected bucket balances independently from the current stored
`wallet_buckets.balance_paise` and compares them. The **correct formula** is:
```
expected_balance = SUM(topup_orders.amount_paise
                       WHERE employment_contract_id = bucket.employment_contract_id
                       AND thread_type = bucket.thread_type
                       AND applied_at IS NOT NULL)
                 - SUM(bucket_reservations.reserved_paise
                       WHERE consumed = True AND bucket_id = X)
```
`discrepancy = |balance_paise - expected_balance| > 1`

If any bucket has discrepancy > 1 paise: set Redis key `wbe:billing_halted = "1"`,
create FA via `FounderActionGenerator`, return `SelfAuditResult(billing_halted=True)`.
The audit must emit an evidence record per C-023 regardless of outcome.

Note: `topup_orders` does NOT have a direct `bucket_id` FK — it joins through
`employment_contract_id + thread_type + billing period`. The reconciliation service must
resolve bucket from `wallet_buckets WHERE employment_contract_id = X AND thread_type = Y
AND period_start = current_period`.

**Responsibility 2 — Daily Audit (C-059 consistency check):**
`run_daily_audit(date)` verifies every consumed reservation from the given date has a
corresponding `platform_cost_ledger` entry. Formula:
```
For each bucket_reservation WHERE consumed=True AND consumed_at::date = date:
    linked_cost = platform_cost_ledger WHERE bucket_reservation_id = reservation.id
    discrepancy if: linked_cost IS NULL AND reservation.reserved_paise > 0
```
Reserved-but-not-logged = a provider call was charged to customer but cost was not recorded
(Invariant #2 violation). These are flagged in `DailyAuditResult`, not a halt trigger.

**Responsibility 3 — Billing Halt Guard (cross-sprint modification to WalletService):**
`WalletService.reserve()` in `wallet/service.py` must be modified to check Redis key
`wbe:billing_halted` **before any DB write**. If set: raise
`HTTPException(503, {"code": "BILLING_INTEGRITY_HALT", "message": "..."})`.
This Redis check is the ONLY mechanism enforcing C-091 at the API boundary.
The check must use a Redis client injected into `WalletService` as a dependency.

**Responsibility 4 — Recovery path:**
`clear_halt()` (no `audit_id` parameter — see GAP-WC030-03) clears `wbe:billing_halted`
from Redis. Operator must then call `POST /reconciliation/run-now` (triggers `run_self_audit`)
to confirm the environment is clean before normal billing resumes. If self-audit fails again,
the halt key is immediately re-set.

**The scheduler (APScheduler):**
Starts inside FastAPI lifespan as an ADDITIVE modification to `main.py` (existing lifespan
from prior sprints must be preserved). `scheduler.py` exports a `create_scheduler()` factory
function that `main.py` imports and starts/stops via lifespan context manager.
Internal HTTP calls use `settings.WBE_INTERNAL_BASE_URL` (NOT hardcoded `localhost:8140`).

### What This Goal Is NOT

- A customer-facing billing correction tool — recovery is ops-only (`POST /reconciliation/run-now`)
- Real-time fraud detection — this is a daily batch consistency check
- Automated correction — halt + FA + operator manual fix is the only recovery path (no auto-correction)

### Key Design Decisions Confirmed During Understanding

| Decision | Resolved | Source |
|---|---|---|
| Self-audit formula | `SUM(topup_orders credits) - SUM(consumed reservations)` per bucket | DB schema analysis |
| `topup_orders` join path | Via `employment_contract_id + thread_type` → `wallet_buckets` | No direct bucket_id FK in topup_orders |
| `clear_halt` takes no `audit_id` | No `reconciliation_audit_log` table in DB — simplify to `clear_halt()` with no args | Schema gap + safety reasoning |
| Billing halt guard location | `wallet/service.py` `reserve()` method — cross-sprint modification | WC-026 code, not WC-030 new file |
| Scheduler internal URL | `settings.WBE_INTERNAL_BASE_URL` env var — not hardcoded port | Environment portability |
| No `IReconciliationService` skeleton | Standalone concrete class (same as ProcurementService) | `wbe_interfaces.py` inspection |
| Scheduler lifespan pattern | ADDITIVE to existing `main.py` lifespan — must not replace existing startup/shutdown | Prior sprint code preservation |
| `generate_margin_report` path | `/reconciliation/platform/margin/report` — WC-030 owns this method, not WC-029 | ReconciliationService definition |

---

## G-3 — Classification

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Dimension | Classification | Reasoning |
|---|---|---|
| **Complexity** | HIGH | Cross-sprint file modification; precise accounting formula; Redis halt coordination; APScheduler lifespan integration |
| **Constitutional Priority** | TIER 1 — C-091 hard gate | Financial correctness over availability — the highest-severity constitutional guarantee in the WBE |
| **Institution routing** | EA → SA → PO → Platform IT Expert | 6 spec gaps — WC must be corrected before groomer runs |
| **Evidence requirement** | `SelfAuditResult` with evidence record per C-023; `billing_halted` Redis state in tests; CCT-SELFAUDIT-01 passing; ≥90% coverage | C-023 + C-059 + C-076 |

**Risk flags:**
- RISK-WC030-01: Incorrect self-audit formula (omits top-up credits) → audit never detects real discrepancies.
- RISK-WC030-02: `clear_halt(audit_id)` with non-existent table → runtime `AttributeError` at clearing time.
- RISK-WC030-03: Missing explicit scope item for WalletService billing_halt guard → batch executor doesn't modify `wallet/service.py`, 503 never returned.
- RISK-WC030-04: Hardcoded `localhost:8140` → scheduler fails in all non-local environments (CI, staging).

---

## G-4 — Execution Plan

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Step | Institution | GO Authorization | Contribution Required | Evidence |
|---|---|---|---|---|
| 1 | EA — Enterprise Architect (INST-005) | GOA-WC030-01 | Spec gap review: formula, cross-sprint modification, Redis key pattern, clear_halt | EA Contribution Record |
| 2 | SA — Solution Architect (INST-009) | GOA-WC030-02 | Fix 6 gaps; split WC030-01 into 01a+01b; add wallet/service.py modification explicitly to scope | SA Contribution Record + updated WC |
| 3 | PO — Product Owner (INST-011) | GOA-WC030-03 | Validate decomposition; confirm cross-sprint scope is achievable in one sprint | PO Contribution Record |
| 4 | Platform IT Expert (INST-010) | GOA-WC030-04 | Implement WC-030 via autonomous sprint | Code + tests + PR |

**Step 4 activated only after Founder `autonomous_halt: false` + WC-029 merges.**

---

## G-5 — Goal Journey — Institution Contribution Records

### GOA-WC030-01 — EA Contribution Record

**Institution:** Enterprise Architect (INST-005)
**GO Authorization:** GOA-WC030-01
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Spec Gaps Found

| Gap ID | Location | Finding | Correction Required |
|---|---|---|---|
| GAP-WC030-01 | WC030-01 scope — `run_self_audit` | Formula "compare balance_paise against SUM(bucket_reservations where consumed=True)" omits top-up credits — a bucket that received ₹100 top-up and consumed ₹30 has expected_balance=70, not just -30 | Correct to: `expected = SUM(topup credits via employment_contract_id+thread_type) - SUM(consumed reservations)`; discrepancy = `\|balance - expected\| > 1` |
| GAP-WC030-02 | WC030-02 scope — `clear_halt(audit_id: str)` | `audit_id` parameter implies a `reconciliation_audit_log` table that does not exist in `12-billing-engine.sql`. Keeping the parameter requires adding a new table or using Redis KV for audit IDs. | Simplify: `clear_halt()` takes no parameters. It only deletes `wbe:billing_halted` from Redis. Operator must call `POST /reconciliation/run-now` afterward to confirm clean state. |
| GAP-WC030-03 | WC030-01 + WC030-02 scope — no cross-sprint mention | `WalletService.reserve()` billing halt check described in C-091 section but NOT listed as a task scope item. Without explicit scope, batch executor will not modify `wallet/service.py`. | Add explicit scope item in WC030-01b: "modify `src/billing-engine/wallet/service.py` — add Redis `wbe:billing_halted` check at start of `reserve()`. Inject `redis.Redis` client into `WalletService.__init__`." |
| GAP-WC030-04 | WC030-02 scope — scheduler internal HTTP | `httpx AsyncClient to localhost:8140` hardcoded | Use `settings.WBE_INTERNAL_BASE_URL` (read from env var `WBE_INTERNAL_BASE_URL`, default `http://localhost:8140`) |
| GAP-WC030-05 | WC030-02 scope — lifespan integration | "starts as part of FastAPI lifespan" — does not specify ADDITIVE pattern; batch executor may overwrite existing lifespan setup from WC-026/027/028/029 | Specify: `scheduler.py` exports `create_scheduler() -> AsyncIOScheduler`; `main.py` imports and wraps in existing lifespan `async with lifespan_context:` block — do NOT replace existing lifespan context |
| GAP-WC030-06 | WC030-01 scope — no skeleton ABC noted | No `IReconciliationService` in `wbe_interfaces.py` — batch executor may add one unnecessarily or fail to find it | State explicitly: `ReconciliationService` is a standalone concrete class (no skeleton ABC), same pattern as `ProcurementService` |

#### Additional Precision Notes

- `run_daily_audit` formula: for each `bucket_reservation WHERE consumed=True AND consumed_at::date = date`, verify a `platform_cost_ledger` row with matching `bucket_reservation_id` exists. Flag orphaned consumed reservations as `DailyAuditResult.unlinked_reservations`. This is not a halt trigger — it is a traceability flag.
- `generate_margin_report` is WC-030's responsibility (in `reconciliation/service.py`). WC-029's router stub for `/margin/report` (if any) should delegate here via import rather than reimplementing.
- CCT-SELFAUDIT-01 test must call `corrupt_bucket_balance` by directly updating `balance_paise` in DB (bypass ORM to simulate a bug), then call `run_self_audit()`. The test MUST use a Redis test client (e.g. `fakeredis` or a dedicated Redis test DB) — not the production Redis key.
- `wbe:billing_halted` Redis key TTL: no TTL — it must survive service restarts (Redis persistence). Key is only cleared by `clear_halt()`.
- `wbe:audit_in_progress:{YYYY-MM-DD}` Redis key for scheduler idempotency: set at audit start, deleted at audit end, TTL=4h (safety net for crash recovery).

**Learning Record:**
WC files for integrity-critical components must be checked against: (1) the exact DB schema for all formula components (top-up tables, reservation tables), (2) cross-sprint file modifications that existing tests will detect if missed, (3) Redis key naming conventions (consistent `wbe:` prefix), (4) APScheduler lifespan integration patterns in prior sprints.

---

### GOA-WC030-02 — SA Contribution Record

**Institution:** Solution Architect (INST-009)
**GO Authorization:** GOA-WC030-02
**Contribution date:** 2026-07-31
**Status:** COMPLETE
**Files modified:** `work-contracts/WC-030-wbe-s6-reconciliation.md`

#### Changes Made to WC-030

1. **GAP-WC030-01 fixed:** `run_self_audit` formula corrected — explicit `expected = SUM(topup credits) - SUM(consumed reservations)` formula with topup join path.
2. **GAP-WC030-02 fixed:** `clear_halt()` takes no parameters — Redis key deletion only.
3. **GAP-WC030-03 fixed:** Explicit scope added to WC030-01b: modify `wallet/service.py` `reserve()` to check `wbe:billing_halted`.
4. **GAP-WC030-04 fixed:** `settings.WBE_INTERNAL_BASE_URL` replaces hardcoded `localhost:8140`.
5. **GAP-WC030-05 fixed:** Lifespan pattern specified as additive — `create_scheduler()` factory, no replacement of existing context.
6. **GAP-WC030-06 fixed:** `ReconciliationService` explicitly noted as standalone concrete class.
7. **Task split:** WC030-01 split into WC030-01a (service.py) and WC030-01b (scheduler.py + router.py + wallet/service.py modification + lifespan).

---

### GOA-WC030-03 — PO Contribution Record

**Institution:** Product Owner (INST-011)
**GO Authorization:** GOA-WC030-03
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Task Decomposition Validation

| Task | Files | model_hint | Assessment |
|---|---|---|---|
| WC030-01a | `reconciliation/service.py` | reasoning | ✅ Correct — self-audit formula + topup join + daily audit consistency check + margin report arithmetic all require deep reasoning |
| WC030-01b | `reconciliation/scheduler.py` + `reconciliation/router.py` + `wallet/service.py` (billing halt guard) + `main.py` lifespan additive update | reasoning | ✅ Upgraded to `reasoning` — cross-sprint wallet modification requires careful context-aware reasoning |
| WC030-03 | `tests/billing-engine/test_reconciliation.py` | auto | ✅ Correct — follows CCT-SELFAUDIT-01 structure |

**Sprint capacity:** 3 sub-tasks — slightly heavy due to cross-sprint modification, but achievable.
**model_hint note:** WC030-01b upgraded from `auto` to `reasoning` due to cross-sprint wallet modification.
**Groomer compatibility:** `WC030-01a`, `WC030-01b`, `WC030-03` match groomer regex. ✅
**PO authorisation:** APPROVED pending WC-029 merge + Founder `autonomous_halt: false`.

---

## G-6 — Evidence Validation Checklist

- [ ] EA Contribution Record — all 6 gaps with source references
- [ ] SA Contribution Record — all fixes documented and committed
- [ ] PO Contribution Record — decomposition validated
- [ ] `WC-030` self-audit formula has `SUM(topup credits) - SUM(consumed reservations)` explicit
- [ ] `WC-030` `clear_halt()` takes no parameters
- [ ] `WC-030` WC030-01b explicitly lists `wallet/service.py` billing halt guard modification
- [ ] `WC-030` `settings.WBE_INTERNAL_BASE_URL` replaces `localhost:8140`
- [ ] `WC-030` lifespan pattern specified as additive `create_scheduler()` factory
- [ ] `WC-030` `ReconciliationService` noted as standalone (no ABC)
- [ ] WC030-01b model_hint upgraded to `reasoning`
- [ ] Redis key naming: `wbe:billing_halted`, `wbe:audit_in_progress:{date}` documented

---

## G-7 — Completion Declaration

**Status:** PENDING — awaiting G-6 validation, WC-029 merge, + Founder `autonomous_halt: false`

This sprint completes the WBE core (sub-components 1–5). After WC-030 merges, the WBE billing
pipeline is functionally complete and GOAL-004 engineering delivery is satisfied.
GOAL-005 (trial + promotions) sprints WC-031+ follow.

Completion criteria:
- All G-6 checklist items checked
- WC-029 PR merged (ProcurementService + FounderActionGenerator importable)
- `autonomous_halt: false` set by Founder
- Batch executor PR: `reconciliation/service.py`, `reconciliation/scheduler.py`, `reconciliation/router.py`, `wallet/service.py` (modified), `main.py` (modified), `tests/billing-engine/test_reconciliation.py`
- `pytest tests/billing-engine/test_reconciliation.py` passes — CCT-SELFAUDIT-01 included
- Redis `wbe:billing_halted` key set in test assertions (C-091 evidence)
- `wallet/service.py` modified: `reserve()` returns 503 when `wbe:billing_halted` is set
