# SIM-PL-007 — WC-028 Meter + Alert Engine: Staged Generation Execution Trace

**Constitutional Gate:** C-086 (Simulation before Production Deployment)
**Work Contract:** WC-028 — WBE-S4: Usage Meter & Alert Engine
**Sprint Track:** Track WBE — Usage Meter & Alert Engine (GOAL-004)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30
**Staged Generation:** ADR-030 + ADR-036 (Blueprint-First)
**Depends on:** WC-026 (WalletService live), WC-027 (BundleEngine live for cost data)
**Prerequisite spec:** `architecture/reference/billing/wbe-component-spec.md §2.3 + §2.3a`

---

## Tasks in WC-028

| Task ID | Scope | model_hint | Chain |
|---|---|---|---|
| WC028-01 | `service.py` (MeterService) + `alert_policy.py` (ThresholdPolicy singletons) | `reasoning` | 01a/b/c |
| WC028-02 | `whatsapp_notifier.py` (stub) + `router.py` + `main.py` mount | `auto` | 02a/b/c |
| WC028-03 | `tests/billing-engine/test_meter.py` — thresholds, dedup, quiet hours, CCT-BILLINGLOOP-01 | `auto` | 03a/b/c |

---

## Grooming Phase (preflight job)

```
$ python3 scripts/groom_sprint.py --sprint WC-028
  Sprint: WC-028
  WC file: work-contracts/WC-028-wbe-s4-meter-alert-engine.md
  Skeleton: src/billing-engine/skeleton/wbe_interfaces.py (IMeterService at line 75)
  Prerequisite spec: architecture/reference/billing/wbe-component-spec.md §2.3a (Amendment 1)
```

### WC028-01 — MeterService + ThresholdPolicy (two output files)

**Haiku call 1 (scaffold):** `_generate_scaffold_subtaskdef`
- Input scope: MeterService + alert_policy.py with ThresholdPolicy, ThresholdRule dataclasses, CUSTOMER_BUCKET_POLICY, AGENCY_POLICY, PROCUREMENT_POLICY singletons
- Skeleton excerpt fed: `IMeterService.record_usage(customer_id, thread_type, amount_paise) -> None`, `run_daily_scan() -> DailyScanResult`, `project_depletion() -> DepletionProjection`
- `prior_subtask_id=None` → `depends_on=[]`
- Two output files (multi-file scaffold) → single SubTaskDef with both files

Expected scaffold SubTaskDef:

```python
SubTaskDef(
    id="WC028-01a",
    description="Implement MeterService (IMeterService) and ThresholdPolicy singletons per §2.3a ladder",
    type="llm",
    depends_on=[],
    compile_gate="py_compile",
    service_dir="src/billing-engine",
    wc_task_id="WC028-01",
    stack="python",
    output_files=[
        "src/billing-engine/meter/service.py",
        "src/billing-engine/meter/alert_policy.py",
    ],
    inject_source_files=[
        "src/billing-engine/skeleton/wbe_interfaces.py",
        "src/billing-engine/wallet/service.py",   # balance reads dependency
        "infrastructure/postgres/init/12-billing-engine.sql",
    ],
    spec_sections={
        "work-contracts/WC-028-wbe-s4-meter-alert-engine.md": "WC028-01",
        "architecture/reference/billing/wbe-component-spec.md": "§2.3 + §2.3a",
    },
    constitutional_check=(
        "Implement MeterService.record_usage(customer_id, thread_type, amount_paise) → resolves "
        "provider_account_id via thread_catalog→provider_accounts JOIN before INSERT into platform_cost_ledger.\n"
        "pct_consumed = consumed / (consumed + balance_paise) — use SUM of platform_cost_ledger "
        "for billing period, NOT initial_allocation (no such column exists).\n"
        "check_thresholds is a CONCRETE method on MeterService — NOT in IMeterService ABC. "
        "Tests call it directly on the concrete class.\n"
        "meter_alert_log deduplication: fire only once per (customer, bucket, threshold, period) — "
        "use UNIQUE constraint via INSERT ... ON CONFLICT DO NOTHING.\n"
        "meter_alert_log DDL belongs in infrastructure/postgres/init/12-billing-engine.sql "
        "as an ALTER/CREATE block — NEVER in service startup (ADR-011).\n"
        "ThresholdPolicy singletons: CUSTOMER_BUCKET_POLICY, AGENCY_POLICY, PROCUREMENT_POLICY per §2.3a.\n"
        "Scope 3 names: RUNWAY_P2(≤30d), RUNWAY_P1(≤14d), RUNWAY_P0(≤7d), RUNWAY_CRITICAL(≤3d), "
        "RUNWAY_EMERGENCY(≤1d).\n"
        "DO NOT change IMeterService signatures — implement bodies only (ADR-036).\n"
        "Type annotations optional in scaffold — polish pass enforces ANN001.\n"
        "C-043: budget ceiling must trigger BLOCK action at 0% remaining.\n"
        "C-049: agent must disclose low balance via WhatsApp notifier (injected dependency).\n"
        "C-059: every threshold fire writes to meter_alert_log (audit obligation)."
    ),
    model_hint="reasoning",
    max_tokens=8000,
)
```

**output_files extraction:** → `["src/billing-engine/meter/service.py", "src/billing-engine/meter/alert_policy.py"]`

**Polish (templated — no LLM call):**
```python
SubTaskDef(
    id="WC028-01b",
    description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
    depends_on=["WC028-01a"],
    compile_gate="ruff",
    output_files=[
        "src/billing-engine/meter/service.py",
        "src/billing-engine/meter/alert_policy.py",
    ],
    inject_source_files=[
        "src/billing-engine/meter/service.py",
        "src/billing-engine/meter/alert_policy.py",
    ],
    constitutional_check=(
        "POLISH PASS — type annotation enforcement only.\n"
        "Add type annotations to ALL function parameters (ANN001).\n"
        "Add return type annotations to ALL functions (ANN201, ANN202).\n"
        "DO NOT change function names, business logic, or structure."
    ),
    model_hint="auto",
    max_tokens=3000,
)
```

**Test (Haiku call 2 — deterministic for `is_test=True`):**
- No LLM call at grooming time (`is_test=True` → deterministic SubTaskDef)
- `test_file = "tests/billing-engine/test_service.py"` (derived from first output file stem: `service`)
- `file_names = "service.py, alert_policy.py"`
- Description: "Write pytest tests for service.py, alert_policy.py per WC scope specification"

```python
SubTaskDef(
    id="WC028-01c",
    description="Write pytest tests for service.py, alert_policy.py per WC scope specification",
    depends_on=["WC028-01b"],
    compile_gate="ruff",
    service_dir="",
    output_files=["tests/billing-engine/test_service.py"],
    inject_source_files=[
        "src/billing-engine/meter/service.py",
        "src/billing-engine/meter/alert_policy.py",
    ],
    constitutional_check=(
        "Write pytest tests for service.py, alert_policy.py per WC scope specification.\n"
        "C-097: include @given(strategies) hypothesis property-based tests for pct_consumed formula.\n"
        "C-059: verify meter_alert_log row written on every threshold fire.\n"
        "C-073: ANN001 type annotations not required in test files (pyproject.toml exemption)."
    ),
    model_hint="auto",
    max_tokens=6000,
)
```

**`prior_subtask_id`:** set to `"WC028-01a"` (scaffold dep only)

---

### WC028-02 — WhatsApp Stub + Router + Main Mount

**Haiku call 1 (scaffold):**
- `prior_subtask_id="WC028-01a"` → `depends_on=["WC028-01a"]`
- Three output files: `whatsapp_notifier.py`, `router.py`, `main.py`
- `model_hint` coerced: WC file says `"auto"` → accepted as-is (valid)

```python
SubTaskDef(
    id="WC028-02a",
    description="Implement WhatsAppNotifier stub, /meter router, and mount in main.py",
    depends_on=["WC028-01a"],
    compile_gate="py_compile",
    service_dir="src/billing-engine",
    wc_task_id="WC028-02",
    output_files=[
        "src/billing-engine/meter/whatsapp_notifier.py",
        "src/billing-engine/meter/router.py",
        "src/billing-engine/main.py",
    ],
    inject_source_files=[
        "src/billing-engine/meter/service.py",
        "src/billing-engine/meter/alert_policy.py",
        "src/billing-engine/main.py",   # existing mount pattern reference
    ],
    constitutional_check=(
        "WhatsAppNotifier.send(customer_id, template_id, params) → raise NotImplementedError "
        "with TODO pointing to ADR-023 (360dialog MCP integration — deferred).\n"
        "WhatsAppNotifier MUST be injected as a dependency into MeterService — NOT a module-level import.\n"
        "Router prefix: /meter — GET /{customer_id}/status → UsageStatus, "
        "POST /daily-scan → DailyScanResult.\n"
        "NOTE: GET /platform/margin/report is Procurement API (§2.4) — deferred to WC-029. Do NOT add it.\n"
        "Mount router in src/billing-engine/main.py (extend existing file — do not overwrite).\n"
        "DO NOT change signatures — implement bodies only (ADR-036).\n"
        "Type annotations optional in scaffold."
    ),
    model_hint="auto",
    max_tokens=6000,
)
```

**Key risk — main.py overwrite:** LLM might return a full replacement of `main.py` rather than
extending it. The scaffold instructs "extend existing file" and injects `main.py` as existing context.
The ContextBuilder's `_build_existing_file_block("src/billing-engine/main.py")` will include the
current file content, reducing overwrite risk.

**Polish:** templated, injects all 3 files back. ruff ANN201 on route functions.

**Test (deterministic):**
- `test_file = "tests/billing-engine/test_router.py"` (derived from `router.py` stem)

```python
SubTaskDef(
    id="WC028-02c",
    output_files=["tests/billing-engine/test_router.py"],
    compile_gate="ruff",
    ...
)
```

**`prior_subtask_id`:** `"WC028-02a"`

---

### WC028-03 — Test Suite (is_test=True — deterministic SubTaskDef)

- No LLM call at grooming time (`is_test=True`)
- `output_files=["tests/billing-engine/test_meter.py"]`
- `file_names = "test_meter.py"`

```python
SubTaskDef(
    id="WC028-03a",
    description="Write pytest tests for test_meter.py per WC scope specification",
    depends_on=["WC028-02b"],
    compile_gate="ruff",
    service_dir="",
    output_files=["tests/billing-engine/test_meter.py"],
    inject_source_files=[
        "src/billing-engine/meter/service.py",
        "src/billing-engine/meter/alert_policy.py",
        "src/billing-engine/meter/whatsapp_notifier.py",
        "src/billing-engine/meter/router.py",
    ],
    constitutional_check=(
        "Write pytest tests for test_meter.py per WC scope specification.\n"
        "C-097: hypothesis @given on pct_consumed formula — zero consumption, "
        "100% consumed, arbitrary integer paise.\n"
        "C-043 CCT-BILLINGLOOP-01: AD wallet hits zero → alerts_sent == 1 type "
        "AD_WALLET_BELOW_MINIMUM.\n"
        "C-049: quiet hours test — 23:15 IST → alert logged but WhatsApp NOT dispatched.\n"
        "C-059: verify meter_alert_log row written on every threshold fire.\n"
        "C-073: ANN001 type annotations not required in test files."
    ),
    model_hint="auto",
    max_tokens=6000,
)
```

**`prior_subtask_id`:** `"WC028-03a"` (03b polish, 03c not applicable for test-of-tests)

---

## Execution Phase Trace (execute job)

```
SPRINT: WC-028
Tasks requested: [WC028-01, WC028-02, WC028-03]
Dependency checks: WC-026 ✓ (wallet), WC-027 ✓ (markup engine on sprint branch)
```

### Sequential execution for WC028-01

```
── WC028-01a (scaffold, attempt 1/3) ──
  CONTEXT: ~22,000 chars (skeleton + schema + wbe-component-spec §2.3a + wallet.service)
  compile_gate: py_compile  ← ANN001 cannot fire
  model: claude-sonnet (reasoning hint → DEEP_REASONING category)
  
  [LLM generates service.py]
    MeterService.record_usage(): resolves provider_account_id via thread_catalog JOIN
    MeterService.project_depletion(): 7d rolling avg from platform_cost_ledger
    MeterService.run_daily_scan(): calls check_thresholds for all active customers
    MeterService.check_thresholds(): computes pct_consumed per C-043 formula,
      deduplicates via INSERT ... ON CONFLICT DO NOTHING on meter_alert_log
  
  [LLM generates alert_policy.py]
    ThresholdRule(name, consumed_pct_trigger, action: Enum[LOG|NOTIFY|FA|BLOCK], bypass_quiet_hours)
    ThresholdPolicy(scope, thresholds, quiet_hours_start_ist=23, quiet_hours_end_ist=6)
    CUSTOMER_BUCKET_POLICY, AGENCY_POLICY, PROCUREMENT_POLICY — §2.3a ladder
    PROCUREMENT_POLICY scope 3 runways: RUNWAY_P2..RUNWAY_EMERGENCY
  
  Risk: LLM may include 'meter_alert_log' DDL in service.py (ADR-011 violation).
  Constitutional check explicitly says "DDL in 12-billing-engine.sql — NEVER in service startup".
  Expected: clean service.py, DDL correctly placed in 12-billing-engine.sql.
  
  ✓ py_compile: service.py — syntax OK
  ✓ py_compile: alert_policy.py — syntax OK

── WC028-01b (polish, attempt 1/1) ──
  CONTEXT: ~12,000 chars (service.py + alert_policy.py injected)
  [LLM adds annotations]
    async def record_usage(self, customer_id: UUID, thread_type: str, amount_paise: int) -> None:
    async def check_thresholds(self, customer_id: UUID) -> list[AlertFired]:
    def quiet_hours_active(self, ist_hour: int) -> bool:
  ✓ ruff --fix: ANN violations resolved
  ✓ ruff gate: PASS

── WC028-01c (test, attempt 1/2) ──
  CONTEXT: service.py + alert_policy.py with annotations
  compile_gate: ruff (tests ANN-exempt)
  [LLM writes test_service.py]
    test_record_usage_resolves_provider_account_id
    test_pct_consumed_formula_zero_balance  ← C-043 formula check
    test_check_thresholds_fires_warn_at_92pct_consumed
    test_check_thresholds_dedup_no_refire_within_period
    @given(st.integers(min_value=0), st.floats(min_value=0.0, max_value=1.0))
    def test_pct_consumed_property_based(consumed, balance_pct)  ← C-097 hypothesis
  ✓ ruff gate: PASS (ANN-exempt in tests/)
  ✓ WC028-01: COMPLETE (3 subtasks)
```

### Sequential execution for WC028-02

```
── WC028-02a (scaffold, attempt 1/3) ──
  depends_on: [WC028-01a] — service.py and alert_policy.py exist on disk
  CONTEXT: ~16,000 chars (service.py + alert_policy.py + existing main.py injected)
  compile_gate: py_compile
  
  [LLM generates whatsapp_notifier.py]
    class WhatsAppNotifier:
        def send(self, customer_id: UUID, template_id: str, params: dict) -> bool:
            raise NotImplementedError("TODO: integrate 360dialog MCP — see ADR-023")
  
  [LLM generates router.py]
    router = APIRouter(prefix="/meter")
    GET /{customer_id}/status → UsageStatus
    POST /daily-scan → DailyScanResult
  
  [LLM extends main.py]
    from meter.router import router as meter_router
    app.include_router(meter_router)
  
  ✓ py_compile: whatsapp_notifier.py — syntax OK
  ✓ py_compile: router.py — syntax OK
  ✓ py_compile: main.py — syntax OK

── WC028-02b (polish, attempt 1/1) ──
  CONTEXT: all 3 files injected
  ✓ ruff gate: PASS

── WC028-02c (test, attempt 1/2) ──
  [LLM writes test_router.py]
    test_get_customer_status_200
    test_post_daily_scan_triggers_check_thresholds
    test_whatsapp_notifier_raises_not_implemented  ← mockable stub test
  ✓ ruff gate: PASS
  ✓ WC028-02: COMPLETE
```

### Sequential execution for WC028-03

```
── WC028-03a (test, attempt 1/3) ──
  CONTEXT: ~30,000 chars (service + policy + notifier + router injected)
  compile_gate: ruff (tests ANN-exempt)
  model: claude-haiku (auto → TEST_GENERATION)
  
  [LLM writes test_meter.py]
    test_threshold_fires_at_correct_pct — bucket at 8% remaining (92% consumed) → WARN_10
    test_no_double_fire_within_24h — same customer + threshold within period → empty list
    test_quiet_hours_suppress_whatsapp — 23:15 IST → alert logged, send() NOT called
    test_procurement_runway_p0_escalation — ≤7d runway → FA action fired
    test_agency_null_quota_no_alert — NULL spending_quota_paise → no alert
    test_post_daily_scan_calls_check_thresholds — all active customers scanned
    class TestCCTBillingLoop01:  ← CCT-BILLINGLOOP-01
        def test_ad_wallet_hits_zero_fires_one_alert(self):
            # wallet balance → 0 → alerts_sent == 1, type AD_WALLET_BELOW_MINIMUM
    @given(st.integers(min_value=0), st.integers(min_value=0))
    def test_pct_consumed_property(consumed_paise, balance_paise):  ← C-097
        # never divides by zero, always in [0, 1]
  
  ✓ ruff gate: PASS (ANN-exempt)
  ✓ WC028-03: COMPLETE
```

---

## Risk Assessment

| Risk | Source | Mitigation |
|---|---|---|
| `meter_alert_log` DDL in service code | ADR-011 | Constitutional check explicitly names the SQL file; compile gate catches if DDL lands in .py |
| `check_thresholds` in IMeterService ABC | WC spec note ("concrete, NOT in ABC") | Constitutional check: "NOT in IMeterService ABC. Tests call it on concrete class." |
| `main.py` full overwrite | LLM pattern | `_build_existing_file_block` injects current main.py; `"extend existing file"` instruction |
| WhatsApp stub not mockable | Injection pattern | Constitutional check: "inject WhatsAppNotifier as dependency — NOT module-level import" |
| Wrong `pct_consumed` formula | C-043 note | `pct_consumed = consumed/(consumed+balance_paise)` formula spelled out in check; no `initial_allocation` column |
| GoalExecutor cascade path mismatch | Fixed 10a5228 | `task.output_file` disk check after cascade RESOLVED |
| `<FILE>` uppercase tag drop | Fixed 10a5228 | `parse_llm_files` now uses `re.IGNORECASE` |

---

## Cost Model

| Subtask | Model | Est. cost |
|---|---|---|
| WC028-01a scaffold (reasoning, 2 files) | claude-sonnet | ₹ 8.50 |
| WC028-01b polish | claude-haiku | ₹ 1.50 |
| WC028-01c test (deterministic → GO) | claude-haiku | ₹ 2.50 |
| WC028-02a scaffold (auto, 3 files) | claude-haiku | ₹ 4.00 |
| WC028-02b polish | claude-haiku | ₹ 1.50 |
| WC028-02c test (deterministic → GO) | claude-haiku | ₹ 2.00 |
| WC028-03a test | claude-haiku | ₹ 3.50 |
| WC028-03b polish | claude-haiku | ₹ 1.00 |
| **Total** | | **₹ 24.50** |

---

## Definition of Done Check

| Criterion | Satisfied by |
|---|---|
| `from meter.service import MeterService` — no import errors | WC028-01a scaffold + 01b polish |
| `check_thresholds(cid)` at 8% remaining → fires WARN_10, writes `meter_alert_log` | WC028-01a |
| Second call within 24h same customer + threshold → empty list (dedup) | WC028-01a + `test_no_double_fire` |
| Quiet hours 23:15 IST → alert logged, WhatsApp NOT dispatched | WC028-01a + `test_quiet_hours` |
| Procurement RUNWAY_P0 at ≤7d → FA action | WC028-01a PROCUREMENT_POLICY |
| `GET /meter/{customer_id}/status` → 200 UsageStatus | WC028-02a |
| `POST /meter/daily-scan` → 200 DailyScanResult | WC028-02a |
| CCT-BILLINGLOOP-01: AD wallet hits zero → alerts_sent == 1 | WC028-03a TestCCTBillingLoop01 |
| `hypothesis @given` on pct_consumed formula | WC028-03a + C-097 |
| `ruff check src/billing-engine/meter/ tests/billing-engine/test_meter.py` → clean | 01b+02b polish pass |

---

## Verdict

**VERDICT: ✅ PASS**

Simulation confirms the staged generation chain is viable. Key WC-028-specific risks are addressed
in constitutional_check. The `check_thresholds`-as-concrete-method pattern and quiet-hours WhatsApp
suppression are the two highest-risk items and are both covered by dedicated test assertions in
WC028-03a.

The `meter_alert_log` SQL amendment must be confirmed in `12-billing-engine.sql` after the sprint run
before WC028 PR is merged.
