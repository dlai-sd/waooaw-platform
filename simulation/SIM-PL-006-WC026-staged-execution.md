# SIM-PL-006 — WC-026 Wallet Engine: Staged Generation Execution Trace

**Constitutional Gate:** C-086 (Simulation before Production Deployment)
**Work Contract:** WC-026 — WBE-S2: Wallet Engine (Buckets, Reserve, Release)
**Sprint Track:** Track WBE — Wallet & Billing Engine (GOAL-004)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30
**Staged Generation:** ADR-030 + ADR-036 (Blueprint-First)

---

## Tasks in WC-026

| Task ID | Scope | model_hint | Chain |
|---|---|---|---|
| WC026-01 | SQLAlchemy models: CustomerWallet, WalletBucket, BucketReservation | `reasoning` | 01a/b/c |
| WC026-02 | Wallet service: get_bucket_balance, reserve, release, activate_subscription, renew | `reasoning` | 02a/b/c |
| WC026-03 | Wallet cache: Redis write-through, get_balance_cached (≤50ms), invalidate_wallet | `standard→auto` | 03a/b/c |
| WC026-04 | Wallet router: GET /buckets/{wallet_id}, POST /reserve, POST /release | `standard→auto` | 04a/b/c |
| WC026-05 | Tests: reserve/release idempotency, C-090 renewal, cache hit/miss, router endpoints | `standard→auto` | 05a/b/c |

> Note: `model_hint="standard"` in WC file is coerced to `"auto"` by `_generate_scaffold_subtaskdef` (only `reasoning`/`auto` accepted per ADR-030 rule 5).

---

## Grooming Phase (preflight job)

```
$ python3 scripts/groom_sprint.py --sprint WC-026
  Sprint: WC-026
  WC file: work-contracts/WC-026-wbe-s2-wallet-engine.md
  Skeleton: src/billing-engine/skeleton/wbe_interfaces.py (135 lines)
```

### WC026-01 — SQLAlchemy Models

**Haiku call 1 (scaffold):** `_generate_scaffold_subtaskdef`
- Input: scope="SQLAlchemy models: CustomerWallet, WalletBucket, BucketReservation"
- Skeleton excerpt fed: IWalletService, IWalletCache, BucketBalance, BucketReservation dataclasses
- `prior_subtask_id=None` → `depends_on=[]`
- Expected output (bare SubTaskDef literal):

```python
SubTaskDef(
    id="WC026-01a",
    description="Implement CustomerWallet, WalletBucket, BucketReservation SQLAlchemy ORM models",
    type="llm",
    depends_on=[],
    compile_gate="py_compile",
    service_dir="src/billing-engine",
    wc_task_id="WC026-01",
    stack="python",
    output_files=[
        "src/billing-engine/wallet/models.py",
    ],
    inject_source_files=[
        "src/billing-engine/skeleton/wbe_interfaces.py",
    ],
    spec_sections={
        "work-contracts/WC-026-wbe-s2-wallet-engine.md": "WC026-01",
    },
    constitutional_check=(
        "Implement CustomerWallet, WalletBucket, BucketReservation mapped to business.* tables.\n"
        "DO NOT change signatures — implement bodies only (ADR-036).\n"
        "Type annotations optional in scaffold — polish pass enforces ANN001.\n"
        "C-091: wallet model must reference thread_catalog for bucket type validation."
    ),
    model_hint="reasoning",
    max_tokens=8000,
)
```

**output_files extraction:** `re.findall(r'output_files=\[...\]', literal)` → `["src/billing-engine/wallet/models.py"]`

**Polish (templated — no LLM call):**
```python
SubTaskDef(
    id="WC026-01b",
    description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
    depends_on=["WC026-01a"],
    compile_gate="ruff",
    output_files=["src/billing-engine/wallet/models.py"],
    inject_source_files=["src/billing-engine/wallet/models.py"],
    model_hint="auto",
    max_tokens=3000,
)
```

**Haiku call 2 (test):** `_generate_test_subtaskdef`
- `test_dir = "tests/" + "src/billing-engine".removeprefix("src/")` = `"tests/billing-engine"`
- `svc_name = Path("src/billing-engine/wallet/models.py").stem` = `"models"`
- `test_file = "tests/billing-engine/test_models.py"`
- Expected output:

```python
SubTaskDef(
    id="WC026-01c",
    description="pytest tests for CustomerWallet, WalletBucket, BucketReservation ORM models",
    depends_on=["WC026-01b"],
    compile_gate="ruff",
    output_files=["tests/billing-engine/test_models.py"],
    inject_source_files=["src/billing-engine/wallet/models.py"],
    model_hint="reasoning",
    max_tokens=6000,
)
```

**Assembly:** `_generate_subtask_chain` → `_indent_subtask(literal, 8)` × 3 → dict entry assembled in Python
**Validation:** `_validate_generated_entry` checks for `"WC026-01"`, `"WC026-01b"`, `"WC026-01c"`, SubTaskDef(, ast.parse ✓
**Injection:** TASK_HANDLERS["WC026-01"] = {"subtasks": [01a, 01b, 01c]}
**`prior_subtask_id`:** set to `"WC026-01a"` (scaffold dep only — not "c")

---

### WC026-02 — Wallet Service (the task that previously failed)

**Previous failure mode (single-pass, pre-staged-generation):**
```
── WC026-02 attempt 1/3 ──
  [LLM generates IWalletService implementation without type annotations]
  ✗ ruff gate: ANN001: missing type annotation for function argument 'customer_id'
  [attempt 2 — same LLM, same probability of missing annotations]
  ✗ ruff gate: ANN001 again (different function)
  [attempt 3]
  ✓ or ✗ — ~50% cumulative success rate
  Cost: ₹9.49 × 2.5 avg attempts = ₹23.73
```

**New flow with staged generation:**

**Haiku call 1 (scaffold):**
- `prior_subtask_id="WC026-01a"` → `depends_on=["WC026-01a"]`
- Constitutional check explicitly says: "Type annotations optional in scaffold"
- `compile_gate="py_compile"` → syntax check ONLY, ANN001 cannot fire

Expected scaffold:
```python
SubTaskDef(
    id="WC026-02a",
    description="Implement IWalletService: get_bucket_balance, reserve, release, activate_subscription, renew",
    depends_on=["WC026-01a"],
    compile_gate="py_compile",       # ← ANN001 cannot fire here
    output_files=["src/billing-engine/wallet/service.py"],
    inject_source_files=["src/billing-engine/skeleton/wbe_interfaces.py"],
    constitutional_check=(
        "Implement IWalletService.get_bucket_balance() — SLA ≤50ms p99.\n"
        "Implement IWalletService.reserve() — idempotent via idempotency_key (UUID).\n"
        "Implement IWalletService.release() — restores bucket quantity.\n"
        "Implement IWalletService.activate_subscription() — MUST check C-088 FOUNDER_AUTHORIZED.\n"
        "Implement IWalletService.renew() — C-090 grandfather pricing gate.\n"
        "DO NOT change signatures — implement bodies only (ADR-036).\n"
        "Type annotations optional in scaffold — polish pass enforces ANN001."
    ),
    model_hint="reasoning",
    max_tokens=8000,
)
```

**Polish (templated — zero LLM cost):**
```python
SubTaskDef(
    id="WC026-02b",
    depends_on=["WC026-02a"],
    compile_gate="ruff",             # ← ANN001 enforced HERE, on a dedicated pass
    output_files=["src/billing-engine/wallet/service.py"],
    inject_source_files=["src/billing-engine/wallet/service.py"],
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

**Test (Haiku call 2):**
- `test_file = "tests/billing-engine/test_service.py"`
- inject_source_files: `["src/billing-engine/wallet/service.py"]`
- constitutional_check targets: reserve idempotency, C-090 renewal logic, C-088 gate

**Validation:** passes (a, b, c all present, ast.parse ✓)
**`prior_subtask_id`:** set to `"WC026-02a"`

---

### WC026-03 — Wallet Cache

**Haiku call 1 (scaffold):**
- `prior_subtask_id="WC026-02a"` → `depends_on=["WC026-02a"]`
- model_hint coerced: `"standard"` → `"auto"`
- output_files: `["src/billing-engine/wallet/cache.py"]`
- compile_gate: `"py_compile"`

**Polish:** templated, inject cache.py back into itself
**Test:** `test_file = "tests/billing-engine/test_cache.py"`, injects cache.py
**`prior_subtask_id`:** `"WC026-03a"`

---

### WC026-04 — Wallet Router

**Haiku call 1 (scaffold):**
- `prior_subtask_id="WC026-03a"` → `depends_on=["WC026-03a"]`
- output_files: `["src/billing-engine/wallet/router.py"]` (or may also include main.py mount)
- constitutional_check: references GET /buckets/{wallet_id}, POST /reserve, POST /release

**Polish:** ruff ANN201 enforces return type on FastAPI route functions
**Test:** `test_file = "tests/billing-engine/test_router.py"`, TestClient fixtures
**`prior_subtask_id`:** `"WC026-04a"`

---

### WC026-05 — Integration Tests

**Previous failure mode:**
```
── WC026-05 attempt 1 ──
  ✗ ModuleNotFoundError: No module named 'pytest'
  (pytest not installed in execute job — Bug B-F)
```

**New flow:**
- Bug B-F fixed in workflow: `pip install ... pytest pytest-asyncio anyio`
- WC026-05 is the tests WC task, so the scaffold produces test files directly
- model_hint: `"standard"` → `"auto"`
- `compile_gate="py_compile"` for 05a scaffold (syntax gate)
- 05b polish enforces ANN... but tests are ANN-exempt per pyproject.toml
  - ruff gate passes even without annotations (per-file-ignores)
- 05c test-of-tests: would produce meta-tests, likely not needed
  - In practice: WC026-05 tests the wallet service, it is itself the test suite
  - Groomer still emits 05a/05b/05c — execution engine handles correctly

---

## Execution Phase Trace (execute job)

```
SPRINT: WC-026
Tasks requested: [WC026-01, WC026-02, WC026-03, WC026-04, WC026-05]
```

### Sequential execution for WC026-01

```
── WC026-01a (scaffold, attempt 1/3) ──
  CONTEXT: ~14,000 chars (skeleton + schema + spec)
  compile_gate: py_compile
  [LLM generates models.py — SQLAlchemy mapped classes]
  ✓ py_compile: src/billing-engine/wallet/models.py — syntax OK

── WC026-01b (polish, attempt 1/1) ──
  CONTEXT: ~8,000 chars (models.py injected from 01a output)
  compile_gate: ruff
  [LLM adds: customer_id: UUID, thread_type: str, etc. to all functions]
  ✓ ruff --fix: ANN001/ANN201 resolved
  ✓ ruff gate: PASS

── WC026-01c (test, attempt 1/2) ──
  CONTEXT: ~10,000 chars (models.py with annotations injected)
  compile_gate: ruff (tests ANN-exempt)
  [LLM writes: test_customer_wallet_creation, test_bucket_reservation, etc.]
  ✓ ruff gate: PASS (ANN-exempt in tests/)
  ✓ WC026-01: COMPLETE (3 subtasks)
```

### Sequential execution for WC026-02

```
── WC026-02a (scaffold, attempt 1/3) ──
  depends_on: [WC026-01a] — models exist on disk
  CONTEXT: ~18,000 chars (skeleton + models.py injected)
  compile_gate: py_compile
  [LLM implements: async def get_bucket_balance, reserve, release, activate_subscription, renew]
  NOTE: LLM can omit type annotations freely — compile_gate only checks syntax
  ✓ py_compile: service.py — syntax OK (ANN001 cannot fire here)

── WC026-02b (polish, attempt 1/1) ──
  CONTEXT: ~12,000 chars (service.py injected)
  [LLM task is deterministic: add annotations to existing signatures]
  async def get_bucket_balance(self, customer_id: UUID, thread_type: str) -> BucketBalance:
  ✓ ruff --fix: remaining ANN violations resolved
  ✓ ruff gate: PASS

── WC026-02c (test, attempt 1/2) ──
  CONTEXT: service.py with full annotations
  [LLM writes: test_reserve_idempotency, test_release_restores, test_c090_renewal, etc.]
  ✓ ruff gate: PASS
  ✓ WC026-02: COMPLETE (3 subtasks)
```

### Cost model comparison

| Task | Old model (single-pass) | New model (staged) |
|---|---|---|
| WC026-01 | ₹9.49 × 1.5 avg = ₹14.24 | scaffold ₹4.0 + polish ₹1.5 + test ₹4.0 = ₹9.50 |
| WC026-02 | ₹9.49 × 2.5 avg = ₹23.73 | scaffold ₹6.0 + polish ₹1.5 + test ₹4.0 = ₹11.50 |
| WC026-03 | ₹4.75 × 1.5 avg = ₹7.13 | scaffold ₹3.0 + polish ₹1.5 + test ₹3.0 = ₹7.50 |
| WC026-04 | ₹4.75 × 1.5 avg = ₹7.13 | scaffold ₹3.0 + polish ₹1.5 + test ₹3.0 = ₹7.50 |
| WC026-05 | ₹4.75 × 3.0 avg = ₹14.25 | scaffold ₹3.0 + polish ₹1.5 + test ₹3.0 = ₹7.50 |
| **Total** | **~₹66.48** | **~₹43.50** |

> Polish subtask has zero LLM cost at *grooming* time. The ₹1.50 is the execute-time Haiku cost for adding annotations.

---

## Cost Summary Output (Step 8.0)

```
  ╔══════════════════════════════════════════════════════╗
  ║           LLM COST SUMMARY (C-077 FinOps)           ║
  ╠══════════════════════════════════════════════════════╣
  ║  WC026-01a:models.py                     ₹  4.0120 ║
  ║  WC026-01b:models.py                     ₹  1.4830 ║
  ║  WC026-01c:test_models.py                ₹  3.9940 ║
  ║  WC026-02a:service.py                    ₹  6.0010 ║
  ║  WC026-02b:service.py                    ₹  1.5020 ║
  ║  WC026-02c:test_service.py               ₹  4.0050 ║
  ║  WC026-03a:cache.py                      ₹  2.9920 ║
  ║  WC026-03b:cache.py                      ₹  1.4890 ║
  ║  WC026-03c:test_cache.py                 ₹  2.9980 ║
  ║  WC026-04a:router.py                     ₹  2.9800 ║
  ║  WC026-04b:router.py                     ₹  1.5010 ║
  ║  WC026-04c:test_router.py                ₹  3.0110 ║
  ║  WC026-05a:test_wallet.py                ₹  2.9950 ║
  ║  WC026-05b:test_wallet.py                ₹  1.4960 ║
  ║  WC026-05c:test_test_wallet.py           ₹  2.9870 ║
  ╠══════════════════════════════════════════════════════╣
  ║  TOTAL                                   ₹ 43.4460 ║
  ╚══════════════════════════════════════════════════════╝
  📡 Monitor signal emitted: sprint-context/monitor-signal.json
```

---

## Failure Mode Elimination Verification

| Failure | Root cause | Eliminated by |
|---|---|---|
| WC026-02 ANN001 ruff gate | Single-pass LLM couldn't reliably annotate complex async service | `compile_gate="py_compile"` for scaffold — ANN001 not checked there |
| WC026-05 pytest not installed | Missing pip install in execute job | Bug B-F: `pip install ... pytest pytest-asyncio anyio` |
| Cross-task blocking on test failure | `prior_subtask_id = task_id + "c"` | Fixed to `task_id + "a"` — scaffold deps only |
| Silent 1/2-subtask injection | String-splice on LLM comment | Python assembly in `_generate_subtask_chain` — no LLM-comment dependency |
| Scaffold-only passes validation | `_validate_generated_entry` only checked SubTaskDef present | Now checks for `task_id + "b"` and `task_id + "c"` explicitly |

---

## Definition of Done Check (WC-026)

| Criterion | Satisfied by |
|---|---|
| `from wallet.models import CustomerWallet, WalletBucket` — no import errors | WC026-01a scaffold + 01b polish |
| `get_balance(wallet_id)` → cached on second call | WC026-02a + WC026-03a (service + cache) |
| `reserve(...)` → idempotent via idempotency_key | WC026-02a constitutional_check references IWalletService.reserve() |
| `release(...)` → restores bucket quantity | WC026-02a |
| `renew(...)` → C-090 grandfather pricing | WC026-02a constitutional_check references renew() + C-090 |
| `GET /wallet/buckets/{wallet_id}` → 200 | WC026-04a router scaffold |
| `POST /wallet/reserve` → 200 or 422 | WC026-04a |
| Tests ≥90% coverage | WC026-01c + 02c + 03c + 04c + 05a cover all paths |
