# GOAL-WC029 — WBE Platform Procurement Ledger (Sprint Sub-Goal under GOAL-004)

**Goal ID:** GOAL-WC029
**Parent Goal:** GOAL-004 (WAOOAW Billing Engine)
**Sprint:** WC-029
**Status:** G-5 JOURNEY IN PROGRESS — awaiting Platform IT Expert (batch executor) activation
**Registrant:** Goal Orchestrator (INST-013) — 2026-07-31
**GO Session:** 2026-07-31
**Constitutional Basis:** C-077 (WAOOAW dev budget ceiling ₹5,000/month), C-059 (Traceability), C-076 (≥90% coverage)

---

## G-1 — Goal Registration

**Goal Statement:**
> "Implement the WBE Platform Procurement Ledger sub-component: record every provider API cost
> into the platform cost ledger, project each provider's runway from a 7-day rolling burn average,
> and auto-generate Founder Actions when runway falls below constitutional thresholds — so that
> WAOOAW can never be blindsided by a provider account running dry and violating C-077."

**Registered:** 2026-07-31
**Parent sprint:** WC-029 under IB-009 (Gate G5 → MVI)
**Evidence record location:** `goals/GOAL-WC029-procurement-ledger.md` (this file)

---

## G-2 — Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### What This Goal Actually Means

The Procurement Ledger is not a cost summary — it is the **platform-side C-077 enforcement
record**. C-077 ratifies a ₹5,000/month development budget ceiling. The procurement ledger
is the mechanism that makes this constitutional commitment auditable and actionable.

There are three distinct responsibilities:

**Responsibility 1 — Cost Recording (append-only, NOT idempotent by design):**
Every provider API call fires `record_cost()` from the AI Runtime. This writes one row to
`institutional.platform_cost_ledger`, which is an **append-only, C-007 protected table**
(PostgreSQL rules block UPDATE and DELETE). The WC's claim that `record_cost` is "idempotent
via recorded_at+customer_id+thread_type composite" is constitutionally incorrect and technically
impossible: `recorded_at` defaults to `NOW()` (set by DB), so two calls within the same
millisecond get different `recorded_at` values, and there is NO UNIQUE constraint in the schema.
The correct contract: `record_cost` is NOT idempotent. It is the AI Runtime's responsibility
not to call it twice for the same event. The DoD test scenario "second call → idempotent" must
be removed.

**Responsibility 2 — Runway Projection (computed on demand):**
`project_runway(provider_name) -> float` computes days remaining at the 7-day rolling average
daily burn. The formula:
  `rolling_avg_daily_burn = SUM(raw_cost_inr_paise WHERE provider AND recorded_at >= NOW() - 7d) / 7`
  `days_remaining = provider_accounts.balance_paise / rolling_avg_daily_burn`
Returns `float('inf')` when `rolling_avg_daily_burn == 0` (no usage in last 7 days).
`daily_burn_rate_paise` is NOT a stored column in `provider_accounts` — it is derived dynamically.

**Responsibility 3 — Founder Action Generation (file append, idempotent):**
`FounderActionGenerator.maybe_create()` appends to `security/FOUNDER-ACTIONS.md` when runway
falls below threshold. It IS idempotent — scans for existing `FA-NNN` with same provider + same
priority level before appending. The format must match the existing file format: a markdown table
row `| **FA-NNN** | ... |` under the correct P0/P1/P2 section, NOT a `## FA-NNN` block header.

**The FX rate contract:**
`record_cost(provider, thread_type, customer_id, cost_paise, fx_rate_inr_per_usd, agent_type)`.
`cost_paise` is ALREADY in INR paise (converted by the AI Runtime before the call).
`fx_rate_inr_per_usd` is stored for audit traceability — it is NOT applied inside `record_cost`.
The WC Notes formula `cost_paise = cost_usd × fx_rate × 100` is misleading. `cost_paise` is
the final INR value passed in; the service stores it as-is in `raw_cost_inr_paise`.
Ollama always passes `cost_paise=0`.

**SQLAlchemy model shape:**
`platform_cost_ledger` DB column is `provider_account_id UUID NOT NULL REFERENCES provider_accounts(id)` —
NOT `provider_name`. The SQLAlchemy `PlatformCostLedger` model must use `provider_account_id`.
`record_cost` must lookup `provider_account_id` from `provider_name` via a DB query.
`ProviderAccount` SQLAlchemy model must NOT include `daily_burn_rate_paise` or `last_fa_level_triggered`
(neither column exists in `provider_accounts`). These are Pydantic response-only computed fields.

### What This Goal Is NOT

- Customer-facing billing or invoicing — this is platform (WAOOAW) cost visibility only
- Provider account top-up automation — that is a human Founder Action (FA system)
- Real-time per-request budget gating — WC-028 MeterService covers customer-side gating; procurement is platform-side only
- Budget enforcement at HTTP level — C-077 is enforced by visibility + FA escalation, not request blocking

### Key Design Decisions Confirmed During Understanding

| Decision | Resolved | Source |
|---|---|---|
| `platform_cost_ledger` is append-only, NOT idempotent | C-007 DB rules block UPDATE+DELETE; no UNIQUE constraint exists | `12-billing-engine.sql` line 287-290 |
| `daily_burn_rate_paise` is NOT stored | Computed dynamically in `project_runway` from 7d `platform_cost_ledger` SUM | `provider_accounts` schema has no such column |
| `last_fa_level_triggered` is NOT stored in DB | Derived by scanning `security/FOUNDER-ACTIONS.md` OR tracked in memory per daily scan | `provider_accounts` schema |
| `PlatformCostLedger` SQLAlchemy model uses `provider_account_id UUID` | DB FK — NOT `provider_name` | `platform_cost_ledger` schema line 266 |
| `cost_paise` param is already INR paise | AI Runtime converts before calling; `fx_rate` stored for audit | spec §2.4 + `platform_cost_ledger` schema |
| FA format: table row `\| **FA-NNN** \| ... \|` | Must match existing `security/FOUNDER-ACTIONS.md` format | File inspection |
| No `IProcurementService` skeleton ABC | `ProcurementService` is a standalone concrete class — no ABC to implement | `wbe_interfaces.py` has no procurement entry |
| `agent_type` required in `record_cost` | DB column `platform_cost_ledger.agent_type VARCHAR(50)` + spec POST body includes `agent_type` | schema + §2.4 spec |

---

## G-3 — Classification

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Dimension | Classification | Reasoning |
|---|---|---|
| **Complexity** | MEDIUM-HIGH | DB schema mismatches in models; file-system FA write with idempotency; runway formula |
| **Constitutional Priority** | TIER 1 — C-077 compliance | Platform cost visibility is a constitutional commitment |
| **Institution routing** | EA → SA → PO → Platform IT Expert | 8 spec gaps — WC must be corrected before groomer runs |
| **Evidence requirement** | `platform_cost_ledger` rows in tests; FA file updated in tests (tmp file); ≥90% coverage | C-059 + C-076 |

**Risk flags:**
- RISK-WC029-01: Idempotency claim is constitutionally and technically impossible for append-only table — will cause batch executor to add wrong UNIQUE constraint to immutable table.
- RISK-WC029-02: Wrong SQLAlchemy model shape (`provider_name` vs `provider_account_id`) will cause `IntegrityError` on every insert attempt.
- RISK-WC029-03: FA format mismatch will generate malformed Markdown that corrupts `security/FOUNDER-ACTIONS.md`.

---

## G-4 — Execution Plan

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Step | Institution | GO Authorization | Contribution Required | Evidence |
|---|---|---|---|---|
| 1 | EA — Enterprise Architect (INST-005) | GOA-WC029-01 | Spec gap review: schema mismatches + idempotency + FA format | EA Contribution Record |
| 2 | SA — Solution Architect (INST-009) | GOA-WC029-02 | Fix 8 gaps in WC-029; split WC029-01 into 01a+01b | SA Contribution Record + updated WC |
| 3 | PO — Product Owner (INST-011) | GOA-WC029-03 | Validate decomposition + model_hint assignments | PO Contribution Record |
| 4 | Platform IT Expert (INST-010) | GOA-WC029-04 | Implement WC-029 via autonomous sprint | Code + tests + PR |

**Step 4 activated only after Founder `autonomous_halt: false` + WC-028 merges.**

---

## G-5 — Goal Journey — Institution Contribution Records

### GOA-WC029-01 — EA Contribution Record

**Institution:** Enterprise Architect (INST-005)
**GO Authorization:** GOA-WC029-01
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Spec Gaps Found

| Gap ID | Location | Finding | Correction Required |
|---|---|---|---|
| GAP-WC029-01 | WC029-01 scope + DoD item 2 | `record_cost` declared "idempotent via recorded_at+customer_id+thread_type composite" — impossible: `recorded_at` is DB-generated (`DEFAULT NOW()`), no UNIQUE constraint exists, and `platform_cost_ledger` is C-007 append-only (no UPDATE/DELETE) | Remove idempotency claim. `record_cost` is intentionally NOT idempotent. AI Runtime must not double-fire. Remove DoD test "second call → idempotent". |
| GAP-WC029-02 | WC029-01 scope — `PlatformCostLedger` model | `provider_name VARCHAR` field listed in model | Must be `provider_account_id UUID NOT NULL` (FK to `provider_accounts.id`) — schema line 266. `record_cost(provider: str)` must lookup `provider_account_id` before insert. |
| GAP-WC029-03 | WC029-01 scope — `ProviderAccount` model | `daily_burn_rate_paise` listed as SQLAlchemy model field | Column does NOT exist in `institutional.provider_accounts`. It is a Pydantic response-only computed field derived dynamically in `project_runway`. Must be removed from the ORM model. |
| GAP-WC029-04 | WC029-01 scope — `ProviderAccount` model | `last_fa_level_triggered` listed as SQLAlchemy model field | Column does NOT exist in `institutional.provider_accounts`. Pydantic response-only field — derive by scanning `security/FOUNDER-ACTIONS.md` or tracking in-memory during daily scan. |
| GAP-WC029-05 | WC029-01 scope — `record_cost` description | "updates daily_burn_rate rolling avg" — implies writing to `provider_accounts` | `daily_burn_rate_paise` is NOT stored. `record_cost` only inserts into `platform_cost_ledger`. Rolling avg is computed on demand by `project_runway`. Remove description of avg update. |
| GAP-WC029-06 | WC029-01 scope — `record_cost` signature | `record_cost(provider, thread_type, customer_id, cost_paise, fx_rate)` — missing `agent_type` | Add `agent_type: str` parameter — required by spec §2.4 POST body and `platform_cost_ledger.agent_type` column |
| GAP-WC029-07 | `FounderActionGenerator Format` section | Format shows `## FA-NNN (auto-generated):` block header — markdown H2 format | Actual `security/FOUNDER-ACTIONS.md` uses `\| **FA-NNN** \| ... \|` table row format under P0/P1/P2 sections. FA entry must match this format to avoid corrupting the file. |
| GAP-WC029-08 | Notes section | `cost_paise = cost_usd × fx_rate_inr_per_usd × 100` — implies conversion inside service | `cost_paise` param IS already INR paise (AI Runtime converts). Service stores it directly as `raw_cost_inr_paise`. `fx_rate_inr_per_usd` is stored for audit only, not applied. Notes formula is misleading. |

#### Additional Precision Notes (for SA to incorporate)

- WC029-01 scope is too dense for one SubTaskDef. Split: WC029-01a = models.py + service.py; WC029-01b = founder_action.py + router.py + main.py mount.
- `project_runway` should return `float` (not `int`) — `balance / burn` often yields fractional days. Return `float('inf')` for Ollama / zero-burn providers.
- Tests for `FounderActionGenerator` must use a tmp file (e.g. `tmp_path` pytest fixture), not the real `security/FOUNDER-ACTIONS.md`.
- FA number scanning regex: `r'\|\s*\*\*FA-(\d+)\*\*'` to extract existing max FA number from table rows.
- `check_and_alert` must also call `maybe_create` for ≤3d (`RUNWAY_CRITICAL`) and ≤1d (`RUNWAY_EMERGENCY`) thresholds per §2.3a Scope 3 (defined in WC-028's PROCUREMENT_POLICY singleton).

**Learning Record:**
WC files for procurement sub-components must be validated against: (1) append-only table rules (C-007), (2) actual DB column names in provider_accounts and platform_cost_ledger, (3) runtime-generated vs. stored column values, (4) existing file formats for any file-system writes.

---

### GOA-WC029-02 — SA Contribution Record

**Institution:** Solution Architect (INST-009)
**GO Authorization:** GOA-WC029-02
**Contribution date:** 2026-07-31
**Status:** COMPLETE
**Files modified:** `work-contracts/WC-029-wbe-s5-platform-procurement.md`

#### Changes Made to WC-029

1. **GAP-WC029-01 fixed:** Removed "idempotent" claim from `record_cost` description. DoD item 2 replaced with correct append-only behaviour assertion.
2. **GAP-WC029-02 fixed:** `PlatformCostLedger` model uses `provider_account_id: UUID` (FK), not `provider_name`. `record_cost` note added: resolve `provider_account_id` from `provider_name` lookup.
3. **GAP-WC029-03 fixed:** `ProviderAccount` SQLAlchemy model does NOT include `daily_burn_rate_paise`. Added to Pydantic response model only.
4. **GAP-WC029-04 fixed:** `ProviderAccount` SQLAlchemy model does NOT include `last_fa_level_triggered`. Pydantic response field only — derived by scanning FA file.
5. **GAP-WC029-05 fixed:** `record_cost` description corrected: inserts into `platform_cost_ledger` only. Rolling avg computed on demand.
6. **GAP-WC029-06 fixed:** `record_cost(provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd)` — `agent_type` parameter added.
7. **GAP-WC029-07 fixed:** FA format corrected to match existing file: table row `| **FA-NNN** | ... |` under correct P0/P1/P2 section.
8. **GAP-WC029-08 fixed:** Notes formula removed. Added: "`cost_paise` is already INR paise — store as `raw_cost_inr_paise` directly; `fx_rate` recorded for audit only."
9. **Task split:** WC029-01 split into WC029-01a (models + service) and WC029-01b (founder_action + router + main.py mount).

See corrected `work-contracts/WC-029-wbe-s5-platform-procurement.md` for full changes.

---

### GOA-WC029-03 — PO Contribution Record

**Institution:** Product Owner (INST-011)
**GO Authorization:** GOA-WC029-03
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Task Decomposition Validation

| Task | Files | model_hint | Assessment |
|---|---|---|---|
| WC029-01a | `procurement/models.py` + `procurement/service.py` | reasoning | ✅ Correct — schema FK resolution + runway formula + PROCUREMENT_POLICY import require reasoning |
| WC029-01b | `procurement/founder_action.py` + `procurement/router.py` + `main.py` mount | auto | ✅ Correct — FA append + router is structural |
| WC029-02 | `tests/billing-engine/test_procurement.py` | auto | ✅ Correct — follows established test pattern |

**Sprint capacity:** 3 sub-tasks, short sprint — fits one executor cycle.
**model_hint assignments:** Correct.
**Groomer compatibility:** `WC029-01a`, `WC029-01b`, `WC029-02` match groomer regex. ✅
**PO authorisation:** APPROVED pending WC-028 merge + Founder `autonomous_halt: false`.

---

## G-6 — Evidence Validation Checklist

- [ ] EA Contribution Record present — all 8 gaps with source references
- [ ] SA Contribution Record present — all fixes documented and committed
- [ ] PO Contribution Record present — decomposition validated
- [ ] `WC-029` `record_cost` signature includes `agent_type`
- [ ] `WC-029` `PlatformCostLedger` SQLAlchemy model uses `provider_account_id UUID` not `provider_name`
- [ ] `WC-029` `ProviderAccount` ORM model has no `daily_burn_rate_paise` or `last_fa_level_triggered` columns
- [ ] `WC-029` idempotency claim removed from `record_cost`; DoD item 2 corrected
- [ ] `WC-029` FA format shows table-row format matching `security/FOUNDER-ACTIONS.md`
- [ ] `WC-029` Notes: `cost_paise` is already INR paise (no conversion in service)
- [ ] No schema changes required (all needed tables already in `12-billing-engine.sql`)

---

## G-7 — Completion Declaration

**Status:** PENDING — awaiting G-6 validation, WC-028 merge, + Founder `autonomous_halt: false`

Completion criteria:
- All G-6 checklist items checked
- WC-028 PR merged (PROCUREMENT_POLICY singleton importable from `meter/alert_policy.py`)
- `autonomous_halt: false` set by Founder
- Batch executor PR: `procurement/models.py`, `procurement/service.py`, `procurement/founder_action.py`, `procurement/router.py`, `tests/billing-engine/test_procurement.py`
- `pytest tests/billing-engine/test_procurement.py` passes ≥90% coverage
- `platform_cost_ledger` rows in test assertions (C-059 evidence)
- `security/FOUNDER-ACTIONS.md` NOT modified by tests (tmp file used)
