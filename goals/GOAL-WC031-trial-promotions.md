# GOAL-WC031 — WBE Trial Engine + Promotions Engine (Sprint Sub-Goal under GOAL-005)

**Goal ID:** GOAL-WC031
**Parent Goal:** GOAL-005 (Customer Acquisition — Trial + Promotions)
**Sprint:** WC-031
**Status:** G-5 JOURNEY IN PROGRESS — BLOCKED on Founder FA (pricing decisions)
**Registrant:** Goal Orchestrator (INST-013) — 2026-07-31
**GO Session:** 2026-07-31
**Constitutional Basis:** C-088 (trial is a billing mode), C-089 (trial costs tracked), C-090 (trial→paid grandfather), C-019 (informed consent — trial terms disclosed), C-059 (Traceability), C-076 (≥90% coverage)

---

## G-1 — Goal Registration

**Goal Statement:**
> "Implement WBE sub-components 6 (Trial Engine) and 7 (Promotions Engine) — enabling WAOOAW
> to acquire new customers through time-limited free trials, discount coupons, and referral
> credits, while ensuring every trial interaction is constitutionally traceable (C-059), every
> trial cost is tracked (C-089), and conversion to paid subscriptions preserves agreed pricing
> (C-090 grandfather)."

**Registered:** 2026-07-31
**Parent sprint:** WC-031 under IB-009 (Gate G5 → MVI). First sprint of GOAL-005.
**Hard prerequisite:** Founder FA with 5 pricing decisions (see `customer-acquisition-spec.md` §Founder Action Gate)
**Evidence record location:** `goals/GOAL-WC031-trial-promotions.md` (this file)

---

## G-2 — Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### What This Goal Actually Means

This sprint straddles two goals: GOAL-004 (billing infrastructure) and GOAL-005 (customer
acquisition). The Trial Engine and Promotions Engine are billing-layer sub-components, but
their purpose is business acquisition. Understanding both dimensions is critical.

There are five operationally distinct responsibilities:

**Responsibility 1 — Trial Lifecycle (TrialService):**
`start_trial(customer_id, agent_type, phone_verified)` is the entry point. It:
1. Validates: no prior paid subscription AND no prior trial for this `agent_type` (UNIQUE constraint)
2. Creates `trial_allocations` row
3. Creates `trial_free_unit_ledger` rows (one per thread_type) with Founder-approved caps
4. Creates `wallet_buckets` rows with trial amounts — directly, NOT via `WalletService.activate_subscription` (that method requires Razorpay payment refs; trials have no payment)
5. Sets Redis `wbe:customer:{customer_id}:mode = "TRIAL"` with TTL = `(expires_at - now()).total_seconds()`
6. Returns `TrialStartResult` with bucket_ids

Steps 1–4 run inside ONE DB transaction. Step 5 (Redis set) runs AFTER the transaction
commits — Redis is NOT transactional with Postgres. If Redis set fails, the service should
attempt a retry; on persistent failure, log the error (the PSE tier override will fail
safe — customer gets LOCAL tier only, which is correct for a trial anyway).

`check_expiry(trial_id)` is called by the **Temporal trial-expiry saga (WC-033)** — NOT by
an internal scheduler. WC-031 only implements the method; WC-033 wires it into a Temporal
workflow.

`convert_to_paid(trial_id, payment_reference)` applies C-090 grandfather: if
`started_at + 14d >= conversion date`, the customer's subscription price is locked at the
trial-start-era price.

**Responsibility 2 — Free Unit Cap Configuration:**
`trial_free_unit_ledger.units_granted` comes from the Founder FA — it is NOT hardcoded in
service code. The batch executor must read caps from `settings.TRIAL_FREE_UNITS` — a dict
keyed by `agent_type` then `thread_type` (e.g. `{"DMA": {"llm_local": 50, "whatsapp_window": 5}}`).
This setting is read from environment variables (set at deployment time from Founder FA values).
The Founder FA decision unlocks this sprint — the FA values populate the env config.

**Responsibility 3 — Promotions (PromotionsService):**
`validate_coupon` is a read-only check. `apply_discount` is the write operation — it
increments `coupon_codes.uses_count` via `SELECT FOR UPDATE` (concurrent-safe) and then
calls `credit_referrer()` internally if a `referral_records` row links the coupon to a
referrer. `credit_referrer` is also callable directly (by WC-033 Temporal saga at conversion).

`DISCOUNT_EXCEEDS_CAP` check: `validate_coupon` must compare `coupon.discount_pct` against
`settings.MAX_DISCOUNT_PCT` (Founder-approved cap from FA, read from env var). If
`discount_pct > MAX_DISCOUNT_PCT`, return `CouponValidation(valid=False, error_code="DISCOUNT_EXCEEDS_CAP")`.

**Responsibility 4 — CCT-TRIAL-02 boundary:**
CCT-TRIAL-02 requires asserting that PSE routes to `LlmTier.LOCAL` for TRIAL customers.
This PSE routing logic lives in AI Runtime (`ai-runtime/pse/router.py`) — a different service.
WC-031 tests can only assert the **billing-layer side** of this CCT:
(1) Redis key `wbe:customer:{id}:mode = "TRIAL"` is set correctly after `start_trial`
(2) `trial_free_unit_ledger` rows are created with correct `units_granted`
The PSE routing assertion (Ollama tier selection + cost_paise=0) belongs in WC-032 tests.

**Responsibility 5 — `apply_discount` → `credit_referrer` call chain:**
When `apply_discount(coupon_id, customer_id, ...)` is called at subscription activation, the
service must check if a `referral_records` row exists where `referee_customer_id = customer_id`
AND `coupon_id = coupon_id` AND `credit_status = PENDING`. If found, call `credit_referrer`
internally and set `credit_status = CREDITED`. This makes `DiscountResult.referral_credited = True`.
This call chain is not explicit in the WC task scope — it must be added.

### What This Goal Is NOT

- A UI for entering trials or coupons — that's WC-034 (web portal)
- Trial expiry scheduling — WC-033 owns the Temporal saga and calls `check_expiry()`
- PSE tier override implementation — WC-032 modifies `ai-runtime/pse/router.py`
- Razorpay payment processing at trial conversion — WC-033/BP owns this handoff

### Key Design Decisions Confirmed During Understanding

| Decision | Resolved | Source |
|---|---|---|
| `start_trial` signature | `(customer_id, agent_type, phone_verified: bool)` | spec §2.1 POST body |
| Trial bucket creation | Direct DB insert into `wallet_buckets` — NOT via `activate_subscription` | `activate_subscription` requires Razorpay params |
| Free unit caps source | `settings.TRIAL_FREE_UNITS: dict` env var — populated from Founder FA | Caps are FA data, not hardcoded |
| "Atomic" start_trial | DB transaction (trial_alloc + wallet_buckets + free_unit_ledger), THEN Redis set outside transaction | Redis is not Postgres-transactional |
| `check_expiry` caller | Temporal trial-expiry saga (WC-033) — not an internal scheduler | WC-033 dependency |
| `settings.MAX_DISCOUNT_PCT` | Founder FA env var — guards `DISCOUNT_EXCEEDS_CAP` | CCT-COUPON-01 |
| `apply_discount` calls `credit_referrer` internally | When referral_records row exists with PENDING status | CCT-REFERRAL-01 + spec DiscountResult.referral_credited |
| CCT-TRIAL-02 WC-031 scope | Assert Redis key + ledger rows only — NOT PSE routing (different service) | Test boundary |
| No skeleton ABCs | `TrialService`, `PromotionsService` are standalone concrete classes | `wbe_interfaces.py` inspection |

---

## G-3 — Classification

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Dimension | Classification | Reasoning |
|---|---|---|
| **Complexity** | HIGH | Two new sub-components; Redis TTL management; Founder FA config reading; cross-sprint WalletService direct use; C-090 grandfather logic |
| **Constitutional Priority** | TIER 1 — Multiple claims | C-019 (informed consent), C-088 (trial as billing mode), C-090 (grandfather at conversion) all apply |
| **Institution routing** | EA → SA → PO → Platform IT Expert | 9 spec gaps — WC must be corrected before groomer runs |
| **Activation gate** | HARD BLOCKED on Founder FA | No sprint can run until FA with 5 pricing decisions is received |
| **Evidence requirement** | CCT-TRIAL-01, CCT-TRIAL-02 (billing layer only), CCT-COUPON-01, CCT-REFERRAL-01 all passing | C-059 + C-076 |

**Risk flags:**
- RISK-WC031-01: `start_trial` signature missing `phone_verified` → spec §2.1 precondition silently skipped.
- RISK-WC031-02: Calling `WalletService.activate_subscription` for trials → `TypeError` (missing Razorpay params).
- RISK-WC031-03: Hardcoded free unit caps in service code → violates Founder FA decision authority; wrong caps shipped.
- RISK-WC031-04: "Atomic DB+Redis" interpreted as Redis inside transaction → impossible; test will hang/fail on rollback.
- RISK-WC031-05: CCT-TRIAL-02 test calls PSE router → test suite fails (wrong service package, import error).

---

## G-4 — Execution Plan

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Step | Institution | GO Authorization | Contribution Required | Evidence |
|---|---|---|---|---|
| 1 | EA — Enterprise Architect (INST-005) | GOA-WC031-01 | Spec gap review: signatures, transaction boundaries, CCT scoping, config mechanism | EA Contribution Record |
| 2 | SA — Solution Architect (INST-009) | GOA-WC031-02 | Fix 9 gaps in WC-031 | SA Contribution Record + updated WC |
| 3 | PO — Product Owner (INST-011) | GOA-WC031-03 | Validate 3-task decomposition; confirm HARD GATE on Founder FA | PO Contribution Record |
| 4 | Platform IT Expert (INST-010) | GOA-WC031-04 | Implement WC-031 AFTER Founder FA + WC-030 merge | Code + tests + PR |

**Step 4 has TWO prerequisites: (a) WC-030 merged, AND (b) Founder FA with pricing decisions received.**

---

## G-5 — Goal Journey — Institution Contribution Records

### GOA-WC031-01 — EA Contribution Record

**Institution:** Enterprise Architect (INST-005)
**GO Authorization:** GOA-WC031-01
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Spec Gaps Found

| Gap ID | Location | Finding | Correction Required |
|---|---|---|---|
| GAP-WC031-01 | WC031-01 scope — `start_trial` signature | `start_trial(customer_id, agent_type)` — missing `phone_verified: bool` (required by spec §2.1 POST body) | Add `phone_verified: bool` parameter; service validates `phone_verified=True` before creating trial (C-019 informed consent gate) |
| GAP-WC031-02 | WC031-01 scope — wallet bucket creation | "creates WalletBuckets via WalletService" — `IWalletService.activate_subscription` requires `razorpay_order_id` + `razorpay_payment_id`; trials have no payment | Replace with direct `wallet_buckets` DB insert within `start_trial` transaction. Do NOT call `activate_subscription`. |
| GAP-WC031-03 | WC031-01 scope — free unit caps | No guidance on where `free_unit_caps` per `agent_type` come from — cannot be hardcoded (FA decision) | Read from `settings.TRIAL_FREE_UNITS: dict` env var (e.g. `{"DMA": {"llm_local": 50}}`). If key missing for agent_type: raise `HTTP 422 TRIAL_CONFIG_MISSING`. |
| GAP-WC031-04 | WC031-01 scope — Notes section | "start_trial must be atomic: WalletBucket + Redis set + TrialAllocation in one DB transaction" — Redis cannot participate in a Postgres transaction | Correct to: DB transaction (trial_allocation + wallet_buckets + free_unit_ledger rows) commits first; Redis `SET ... EX ...` called after commit. On Redis failure: log error, do not roll back DB (trial is valid; PSE defaults to LOCAL tier anyway). |
| GAP-WC031-05 | WC031-01 scope — `check_expiry` | No caller specified for `check_expiry(trial_id)` | Add note: `check_expiry` is called by the Temporal trial-expiry saga (WC-033). WC-031 only implements the method — no scheduler needed. |
| GAP-WC031-06 | WC031-03 scope — CCT-TRIAL-02 | "Assert: PSE router sees customer_mode=TRIAL → routes to LlmTier.LOCAL" — PSE router is in AI Runtime (different service/package) | Remove PSE assertion from WC-031 tests. WC-031 CCT-TRIAL-02 scope: assert (1) Redis `wbe:customer:{id}:mode = b"TRIAL"` set; (2) `trial_free_unit_ledger` rows created with `units_granted` from settings. PSE routing assertion belongs in WC-032. |
| GAP-WC031-07 | WC031-02 scope — `apply_discount` | `apply_discount` result includes `referral_credited: bool` but no mention of calling `credit_referrer` internally | Add: `apply_discount` checks `referral_records WHERE referee_customer_id = customer_id AND coupon_id = coupon_id AND credit_status = PENDING`; if found, calls `credit_referrer(referral_id)` and sets `credit_status = CREDITED`. Returns `referral_credited=True`. |
| GAP-WC031-08 | WC031-02 scope — `DISCOUNT_EXCEEDS_CAP` | CCT-COUPON-01 requires `discount_pct > Founder-approved cap → HTTP 422 DISCOUNT_EXCEEDS_CAP` but no mechanism specified for reading the Founder cap | `validate_coupon` must compare `coupon.discount_pct` against `settings.MAX_DISCOUNT_PCT` (int, from env var — populated from Founder FA). |
| GAP-WC031-09 | Required Inputs | "WBE Skeleton — check for TrialABC, PromotionsABC" — neither exists | State explicitly: `TrialService` and `PromotionsService` are standalone concrete classes with no skeleton ABCs. Do not add new ABCs. |

#### Additional Precision Notes (for SA to incorporate)

- `trial_allocations.customer_id` FK references `institutional.billing_profiles(customer_id)` — NOT `business.customer_wallets`. SQLAlchemy model must use the correct FK schema + table.
- `start_trial` precondition: verify no `employment_contract` with `status=ACTIVE` exists for this `customer_id + agent_type` (paid subscription check). This is a DB query before insert.
- Trial duration is always 14 days: `expires_at = started_at + timedelta(days=14)` (unless Founder FA overrides via `settings.TRIAL_DURATION_DAYS`).
- `credit_referrer` must be idempotent: use `UPDATE SET credit_status='CREDITED', credited_at=NOW() WHERE credit_status='PENDING'` — check affected rows to confirm exactly one row updated.
- Tests must NOT depend on Founder FA values being set — use test fixture env vars for `TRIAL_FREE_UNITS` and `MAX_DISCOUNT_PCT`.
- Groomer compatibility: `WC031-01`, `WC031-02`, `WC031-03` already match groomer regex — no split needed.

**Learning Record:**
WC files for business-logic sub-components that depend on external config (Founder pricing FA) must explicitly specify: (1) the config mechanism (env vars, settings table), (2) how tests mock the config, (3) which CCT assertions belong in which sprint's test suite when the CCT spans multiple services.

---

### GOA-WC031-02 — SA Contribution Record

**Institution:** Solution Architect (INST-009)
**GO Authorization:** GOA-WC031-02
**Contribution date:** 2026-07-31
**Status:** COMPLETE
**Files modified:** `work-contracts/WC-031-goal005-wbe-trial-promotions.md`

#### Changes Made to WC-031

1. **GAP-WC031-01 fixed:** `start_trial(customer_id, agent_type, phone_verified: bool)` — `phone_verified` parameter added. Service validates `True` before creating trial.
2. **GAP-WC031-02 fixed:** Direct `wallet_buckets` DB insert in `start_trial` — no `activate_subscription` call. WalletService import retained for `credit_referrer` balance top-up only.
3. **GAP-WC031-03 fixed:** Free unit caps read from `settings.TRIAL_FREE_UNITS` dict env var.
4. **GAP-WC031-04 fixed:** Notes section corrected: DB transaction first, Redis set after commit.
5. **GAP-WC031-05 fixed:** `check_expiry` caller documented as Temporal saga (WC-033).
6. **GAP-WC031-06 fixed:** CCT-TRIAL-02 test scope scoped to billing layer (Redis key + ledger rows only).
7. **GAP-WC031-07 fixed:** `apply_discount` calls `credit_referrer` internally when referral PENDING row exists.
8. **GAP-WC031-08 fixed:** `validate_coupon` compares against `settings.MAX_DISCOUNT_PCT`.
9. **GAP-WC031-09 fixed:** Both services noted as standalone concrete classes (no ABCs).

---

### GOA-WC031-03 — PO Contribution Record

**Institution:** Product Owner (INST-011)
**GO Authorization:** GOA-WC031-03
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Task Decomposition Validation

| Task | Files | model_hint | Assessment |
|---|---|---|---|
| WC031-01 | `trial/models.py` + `trial/service.py` + `trial/router.py` + DB migration run | reasoning | ✅ Correct — trial lifecycle + C-090 + Redis + direct bucket insert require reasoning |
| WC031-02 | `promotions/models.py` + `promotions/service.py` + `promotions/router.py` + `main.py` mount | reasoning | ✅ Correct — SELECT FOR UPDATE + credit_referrer call chain + cap enforcement |
| WC031-03 | `tests/billing-engine/test_trial.py` + `tests/billing-engine/test_promotions.py` | auto | ✅ Correct — follows established pattern; CCT scenarios provided |

**Sprint capacity:** 3 tasks, medium-density sprint.
**HARD GATE confirmed:** Sprint must not activate until (a) WC-030 merged AND (b) Founder FA received.
**model_hint assignments:** Both reasoning tasks correct for business logic; auto correct for tests.
**Groomer compatibility:** `WC031-01`, `WC031-02`, `WC031-03` match groomer regex. ✅
**PO authorisation:** APPROVED in principle — BLOCKED until Founder FA received.

---

## G-6 — Evidence Validation Checklist

- [ ] EA Contribution Record — all 9 gaps with source references
- [ ] SA Contribution Record — all fixes documented and committed
- [ ] PO Contribution Record — HARD GATE confirmed
- [ ] `WC-031` `start_trial` signature includes `phone_verified: bool`
- [ ] `WC-031` no `activate_subscription` call for trial bucket creation — direct DB insert
- [ ] `WC-031` `settings.TRIAL_FREE_UNITS` specified as config source
- [ ] `WC-031` Notes: DB transaction first, Redis after commit (not atomic)
- [ ] `WC-031` `check_expiry` documented as called by WC-033 Temporal saga
- [ ] `WC-031` CCT-TRIAL-02 test scope limited to billing layer (Redis + ledger rows)
- [ ] `WC-031` `apply_discount` calls `credit_referrer` when referral PENDING exists
- [ ] `WC-031` `validate_coupon` reads `settings.MAX_DISCOUNT_PCT`
- [ ] `WC-031` TrialService + PromotionsService noted as standalone (no ABCs)
- [ ] `constitution/PROJECT_STATE.md` will reflect `current_sprint: WC-031` after WC-030 merge + Founder FA

---

## G-7 — Completion Declaration

**Status:** PENDING — HARD BLOCKED on Founder FA (5 pricing decisions) + WC-030 merge

**Founder FA required fields before sprint activates:**
1. Trial budget per agent type (e.g. DMA: 50 llm_local calls + 5 whatsapp_windows, 14 days)
2. Maximum discount % per coupon code (e.g. 30%)
3. Referral credit amount (e.g. ₹100 or 50 llm_local credits)
4. Which agent types are trial-eligible (e.g. DMA only, or all)
5. Trial-to-paid conversion: wallet pre-seeded at trial start or only at paid subscription activation?

Once FA received:
- `settings.TRIAL_FREE_UNITS`, `settings.MAX_DISCOUNT_PCT`, `settings.REFERRAL_CREDIT_PAISE` populated in deployment env
- `autonomous_halt: false` set by Founder
- Batch executor PR: `trial/models.py`, `trial/service.py`, `trial/router.py`, `promotions/models.py`, `promotions/service.py`, `promotions/router.py`, `main.py` (mount), `tests/billing-engine/test_trial.py`, `tests/billing-engine/test_promotions.py`
- All 4 CCTs passing
