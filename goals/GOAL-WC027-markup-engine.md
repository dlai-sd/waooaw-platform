# GOAL-WC027 — WBE Markup Engine (Sprint Sub-Goal under GOAL-004)

**Goal ID:** GOAL-WC027
**Parent Goal:** GOAL-004 (WAOOAW Billing Engine)
**Sprint:** WC-027
**Status:** G-5 JOURNEY IN PROGRESS — awaiting Platform IT Expert (batch executor) activation
**Registrant:** Goal Orchestrator (INST-013) — 2026-07-31
**GO Session:** 2026-07-31
**Constitutional Basis:** C-089 (Margin Floor), C-059 (Traceability), C-076 (≥90% test coverage)

---

## G-1 — Goal Registration

**Goal Statement:**
> "Implement the WBE Markup Engine sub-component: three-layer price derivation (provider cost
> → bundle cost floor → customer-facing price), constitutional margin floor enforcement (C-089),
> and FastAPI pricing router — so that WAOOAW can computationally prove it never sells below cost
> before any subscription is activated."

**Registered:** 2026-07-31
**Parent sprint:** WC-027 under IB-009 (Gate G5 → MVI)
**Evidence record location:** `goals/GOAL-WC027-markup-engine.md` (this file)

---

## G-2 — Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### What This Goal Actually Means

The Markup Engine is not a pricing calculator. It is the **constitutional proof engine** for
C-089 — the principle that WAOOAW may never sell a service for less than its cost. Without
this sub-component, every subscription activation is constitutionally unverifiable.

There are three distinct pricing layers that the batch executor must not confuse:

**Layer 1 — Provider cost (raw):**
What WAOOAW pays providers per unit (Anthropic tokens, Sarvam API calls, video generation credits).
Stored in `institutional.thread_catalog.raw_cost_inr_paise`.

**Layer 2 — Bundle cost floor (marked up):**
Provider cost × ration quantity × (1 + markup_pct) + infrastructure_share_paise.
This is pre-computed at bundle profile activation and stored in
`institutional.bundle_profiles.cost_floor_paise`. The `BundleEngine.cost_floor()` method
**reads this stored value** — it does not recompute at runtime. The computation already happened
at profile seeding time. Runtime recomputation would be inaccurate if thread costs have changed
since profile activation.

**Layer 3 — Customer-facing price (derivation):**
`price = cost_floor / (1 - minimum_margin_pct / 100)`.
This is **margin-on-revenue** mathematics, not markup-on-cost. In standard billing practice,
"20% margin" means 20% of the selling price is profit — not 20% added to cost.
At 20% margin: price = 1000 / 0.80 = ₹12.50 (not 1000 × 1.20 = ₹12.00).
The `minimum_margin_pct` is stored in `bundle_profiles.minimum_margin_pct` (nullable NUMERIC(5,2),
default 20.0 if NULL).

**The C-089 enforcement path:**
When a Founder proposes a price, `validate_price()` computes `minimum_compliant_price_paise` =
`cost_floor / (1 - minimum_margin_pct / 100)` and writes to `institutional.pricing_floor_log`
regardless of outcome (APPROVED or REJECTED). This log is the constitutional evidence that C-089
was evaluated — it is not an error log, it is an audit log.

### What This Goal Is NOT

- Dynamic re-computation of cost floors from thread catalog at every API call — cost floor is pre-stored
- A general price management system — markup engine only validates + derives, does not store customer prices
- Thread catalog management — `thread_catalog.py` already exists; this sprint does not touch it
- Markup percentage configuration UI — that is GOAL-005 WC-034 (Founder admin page)

### Key Design Decisions Confirmed During Understanding

| Decision | Resolved | Source |
|---|---|---|
| `cost_floor()` reads pre-stored value | `bundle_profiles.cost_floor_paise` — not recomputed | DB schema |
| Margin formula | `price = floor / (1 - margin/100)` — margin-on-revenue, NOT markup-on-cost | Standard billing |
| `validate_price` writes to DB on PASS and FAIL | `pricing_floor_log` is an audit log, not error log | C-089 + C-059 |
| `validate_price` returns `minimum_compliant_price_paise` | Allows Founder to know exact floor | `pricing_floor_log` schema |
| Method name | `validate_price(agent_type, bundle_tier, proposed)` — matches `IMarkupEngine` skeleton | wbe_interfaces.py |
| `markup_thread_catalog` table | DOES NOT EXIST — use `bundle_profiles.minimum_margin_pct` | DB schema verified |

---

## G-3 — Classification

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

| Dimension | Classification | Reasoning |
|---|---|---|
| **Complexity** | HIGH | Three-layer pricing math + constitutional enforcement + DB writes on every validation |
| **Constitutional Priority** | TIER 1 — Blocking | C-089 is a hard gate — no subscription can be priced without this sub-component |
| **Institution routing** | EA → SA → PO → Platform IT Expert | Spec gaps required EA review; SA must correct WC before groomer runs |
| **Evidence requirement** | Contribution Records per institution + `pricing_floor_log` populated in tests | C-059 + C-076 |

**Risk flags identified at classification:**
- RISK-WC027-01: WC file had 3 spec gaps (wrong column name, wrong method signature, missing `minimum_compliant_price_paise`). Must be corrected before batch executor receives task. Routed to SA.
- RISK-WC027-02: `bundle_profiles` seed data must exist in test fixtures for DMA/DPA/DSA/DCA × STARTER/RUNNER/WINNER. Batch executor must check conftest before writing tests.

---

## G-4 — Execution Plan

*Produced by: Goal Orchestrator (INST-013) — 2026-07-31*

### Institution Routing (in sequence)

| Step | Institution | GO Authorization | Contribution Required | Evidence |
|---|---|---|---|---|
| 1 | EA — Enterprise Architect (INST-005) | GOA-WC027-01 | Spec gap review of WC-027 against all referenced specs + skeleton | EA Contribution Record |
| 2 | SA — Solution Architect (INST-009) | GOA-WC027-02 | Fix 3 spec gaps in `WC-027-wbe-s3-markup-engine.md` | SA Contribution Record + updated WC file |
| 3 | PO — Product Owner (INST-011) | GOA-WC027-03 | Validate task decomposition fits one sprint (2 tasks, 4 sub-tasks) | PO Contribution Record |
| 4 | Platform IT Expert (INST-010) | GOA-WC027-04 | Implement WC-027 via autonomous sprint batch executor | Code + tests + PR |

**Step 4 is the LAST STEP — activated only by explicit Founder authorisation (`autonomous_halt: false`).**

### Evidence Specification per Institution

| Institution | Required Evidence |
|---|---|
| EA | Spec gaps listed with source references; recommendation for each |
| SA | Corrected WC file committed; changelog of changes made |
| PO | Task count validated; model_hint assignments confirmed; no over-scoping |
| Platform IT Expert | `pytest` passing ≥90% coverage; `ruff` clean; `pricing_floor_log` rows in tests |

---

## G-5 — Goal Journey — Institution Contribution Records

### GOA-WC027-01 — EA Contribution Record

**Institution:** Enterprise Architect (INST-005)
**GO Authorization:** GOA-WC027-01
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Spec Gaps Found (from deep analysis against DB schema, skeleton, thread catalog)

| Gap ID | Location | Finding | Correction Required |
|---|---|---|---|
| GAP-WC027-01 | WC-027 Notes section | "`markup_pct` is read from `markup_thread_catalog.markup_pct`" — table does not exist in `12-billing-engine.sql` | Use `bundle_profiles.minimum_margin_pct` (NUMERIC(5,2), nullable, default 20.0) |
| GAP-WC027-02 | WC-027 Task WC027-01 scope | `validate_margin(proposed_price_paise, cost_floor_paise)` — pure function, no DB access | Must align to `IMarkupEngine.validate_price(agent_type, bundle_tier, proposed_price_paise)` which reads cost_floor from DB and writes to `pricing_floor_log` |
| GAP-WC027-03 | WC-027 DoD + Task WC027-02 scope | No mention of `minimum_compliant_price_paise` in 422 response body or test assertions | `pricing_floor_log` schema has `minimum_compliant_price_paise` column — must appear in 422 detail and be tested |

#### Additional Precision Notes (for SA to incorporate)

- `derive_price` signature in WC (`cost_floor_paise, markup_pct`) should be `(agent_type, bundle_tier, target_margin_pct=None)` — method looks up cost_floor from DB, uses `bundle_profiles.minimum_margin_pct` as default, computes `floor / (1 - margin/100)`
- `outcome` column in `pricing_floor_log` is VARCHAR(10) — use `"APPROVED"` and `"REJECTED"` (verified from schema)
- `GET /pricing/thread-catalog` endpoint delegates to existing `ThreadCatalogService.get_all_threads()` — no duplication
- WC027-01 scope is too dense for one SubTaskDef — SA should split into WC027-01a (models + engine) and WC027-01b (router + main.py mount)

**Learning Record:**
WC files written without cross-referencing DB schema and skeleton interfaces produce silent spec gaps that propagate into generated code. Future WC files for billing engine sub-components must be reviewed against: (1) migration SQL, (2) skeleton ABCs, (3) existing service files in the same package.

---

### GOA-WC027-02 — SA Contribution Record

**Institution:** Solution Architect (INST-009)
**GO Authorization:** GOA-WC027-02
**Contribution date:** 2026-07-31
**Status:** COMPLETE
**Files modified:** `work-contracts/WC-027-wbe-s3-markup-engine.md`

#### Changes Made to WC-027

1. **GAP-WC027-01 fixed:** Removed reference to non-existent `markup_thread_catalog` table. Notes section now references `bundle_profiles.minimum_margin_pct`.
2. **GAP-WC027-02 fixed:** Task WC027-01 scope updated — `validate_margin()` → `validate_price(agent_type, bundle_tier, proposed_price_paise)` matching `IMarkupEngine` skeleton. Writes to `pricing_floor_log` on both outcomes.
3. **GAP-WC027-03 fixed:** DoD item added: "422 body includes `minimum_compliant_price_paise`". WC027-02 test scope updated to assert this field.
4. **Task decomposition improved:** WC027-01 split into WC027-01a (models.py + bundle_engine.py) and WC027-01b (router.py + main.py mount) for cleaner SubTaskDef generation.
5. **derive_price signature corrected:** Scope text now uses `derive_price(agent_type, bundle_tier, target_margin_pct=None)`.

See corrected `work-contracts/WC-027-wbe-s3-markup-engine.md` for full changes.

---

### GOA-WC027-03 — PO Contribution Record

**Institution:** Product Owner (INST-011)
**GO Authorization:** GOA-WC027-03
**Contribution date:** 2026-07-31
**Status:** COMPLETE

#### Task Decomposition Validation

| Task | Files | model_hint | Scope fit assessment |
|---|---|---|---|
| WC027-01a | `markup/models.py` + `markup/bundle_engine.py` | reasoning | ✅ Correct — both require deep understanding of billing math and C-089 |
| WC027-01b | `markup/router.py` + `main.py` mount | auto | ✅ Correct — routing is structural, not complex |
| WC027-02 | `tests/billing-engine/test_markup.py` | auto | ✅ Correct — test structure follows existing test_wallet.py pattern |

**Sprint capacity assessment:** 3 sub-tasks is within one sprint capacity for Platform IT Expert. No over-scoping.
**model_hint assignments:** `reasoning` for business logic; `auto` for structural/test code. Correct.
**Groomer compatibility:** All task IDs `WC027-01a`, `WC027-01b`, `WC027-02` match groomer regex `WC027-\d{2}[a-z]?`. ✅

**PO authorisation for sprint execution:** APPROVED pending Founder `autonomous_halt: false` release.

---

## G-6 — Evidence Validation Checklist

*To be completed by Constitutional Analyst (INST-002) before G-7 Completion*

- [ ] EA Contribution Record present with all required fields — source references, correction recommendations
- [ ] SA Contribution Record present — WC file changes documented and committed
- [ ] PO Contribution Record present — task decomposition validated
- [ ] `work-contracts/WC-027-wbe-s3-markup-engine.md` has no `markup_thread_catalog` reference
- [ ] `work-contracts/WC-027-wbe-s3-markup-engine.md` uses `validate_price` (not `validate_margin`)
- [ ] `work-contracts/WC-027-wbe-s3-markup-engine.md` DoD includes `minimum_compliant_price_paise` check
- [ ] `constitution/PROJECT_STATE.md` has `current_sprint: WC-027`, `sprint_status: READY`, `autonomous_halt: true`
- [ ] All records committed to `main`

---

## G-7 — Completion Declaration

*To be declared by Goal Orchestrator (INST-013) after G-6 validation and Founder activates sprint*

**Status:** PENDING — awaiting G-6 validation + Founder `autonomous_halt: false` authorisation

Completion criteria:
- All G-6 checklist items checked
- `autonomous_halt: false` set by Founder
- Groomer runs in CI — SubTaskDefs injected into TASK_HANDLERS
- Batch executor (Platform IT Expert INST-010) opens PR with markup engine implementation
- PR reviewed and merged by autonomous reviewer
- `pytest tests/billing-engine/test_markup.py` passes with ≥90% coverage in CI
- `pricing_floor_log` rows present in test assertions (C-089 evidence)
