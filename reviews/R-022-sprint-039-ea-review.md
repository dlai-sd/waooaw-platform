# R-022 — WC-039 Enterprise Architect Review

**Reviewer Office:** Enterprise Architect (INST-004)
**Sprint:** WC-039 — Trust Layer Sprint 3: CTG Library + AIR PSE Router Refactor
**Date:** 2026-08-07
**Outcome:** GAPS FOUND — 1 Critical, 1 Significant, 2 Minor. GAP-001 fixed in this session.

---

## Review Scope

Reviewed all WC-039 output files against ADR-042, ADR-045, ADR-014, and constitutional
claims C-041, C-059, C-076, C-003.

### Files Reviewed

| File | Status |
|---|---|
| `src/trust-layer/ctg/__init__.py` | ✅ Correct |
| `src/trust-layer/ctg/models.py` | ✅ Correct — `SessionContext` frozen, `MCPToolError` sanitized, `ConstitutionalBlockError` preserves decision_id |
| `src/trust-layer/ctg/registry_client.py` | ✅ Correct — 60s TTL, cache key `(tenant_id\|None, provider_name)`, raise_for_status clean |
| `src/trust-layer/ctg/exception_translator.py` | ✅ Correct — token never received, 100% coverage |
| `src/trust-layer/ctg/gateway.py` | ⚠️ GAP-001 (coverage), GAP-003 (dcm_category hardcoded) |
| `src/ai-runtime/pse/router.py` | ⚠️ GAP-002 (fallback bypass), else correct |
| `tests/trust-layer/test_ctg.py` | ⚠️ GAP-001 — 78% coverage, fixed this session |
| `tests/ai-runtime/test_pse_router.py` | ✅ Correct — all CTG tests pass, trial override CCTs preserved |
| `adr/ADR-045-per-service-lean-docker-image-strategy.md` | ✅ Correct — addresses disk pressure, correct technical content |
| `architecture/reference/dockerfiles/Dockerfile.test-runner-python` | ✅ Correct — `--mount=type=cache` pip, no .NET/Node |

---

## ADR-042 Pipeline Conformance

Pipeline (§2) steps reviewed against `gateway.py`:

| Step | Spec | Implementation | Status |
|---|---|---|---|
| 1 | `registry_client.get_config()` | ✅ First call in `call()` | PASS |
| 2 | CE.ValidateAction → DENY → `ConstitutionalBlockError` | ✅ DENY + ESCALATE both block; `_fetch_token` not reached | PASS |
| 3 | oauth-vault fetch → token as local var only | ✅ `token: str \| None` local var; cleared in `finally` | PASS |
| 4 | Token injected at socket boundary via executor | ✅ Executor signature `(tool_name, args, token, config)` | PASS |
| 5 | Execute via injected executor | ✅ Executor injected; no direct provider SDK in gateway | PASS |
| 6 | ExceptionTranslator on failure — no token in output | ✅ Translator does NOT receive `token` parameter | PASS |
| 7 | Write evidence record to Audit Sink | ✅ Written in `call()` for BOTH success and failure | PASS |
| 8 | Clear token local variable | ✅ `token = None` in `finally` block | PASS |
| 9 | Return GatewayResult | ✅ `result` or `error` — not both | PASS |

**ADR-042 §3 (AIR breaking change):** `router.py` replaces direct `_dispatch_*` calls with `gateway.call("llm.complete", ...)` when `_CTG_AVAILABLE`. `_make_gateway()` factory correctly patched in tests. **PASS.**

---

## Gaps Found

### GAP-001 — Critical: CTG library coverage 78% (C-076 requires ≥90%)

**Evidence:**
```
src/trust-layer/ctg/gateway.py   91   37   10   1   56%
  Missing: 42, 62, 76, 86-107, 127, 229, 235, 270-300
TOTAL    177   37   20    1   78%
```

**Root cause:** Three classes in `gateway.py` have zero test coverage:
- `_GrpcCEClient` (lines 64–107): production gRPC client requiring generated proto stubs; correctly injected away in tests via `ce_client=` parameter. Appropriate to mark `# pragma: no cover`.
- `_LoggingAuditSinkWriter.write_record` (line 127): default no-op sink; easily testable with a direct instantiation call.
- `_fetch_token` method (lines ~268–300): vault HTTP call; always mocked via `patch.object`. Needs unit tests for 404, HTTPStatusError, and RequestError paths.
- Protocol `...` bodies (lines 42, 62): abstract stubs; `# pragma: no cover`.

**Fix required:** Add 7 tests; add `# pragma: no cover` to `_GrpcCEClient` class body and Protocol `...` stubs. **Fixed in this session.**

---

### GAP-002 — Significant: `_CTG_AVAILABLE = False` fallback is a structural C-041 bypass

**Location:** `src/ai-runtime/pse/router.py` lines ~375-420

```python
if _CTG_AVAILABLE and _ctx is not None:
    # constitutionally governed path
else:
    # Direct dispatch — NO CE gate
    result = await _dispatch_ollama(prompt)
```

**Problem:** Any `ImportError` on CTG import silently downgrades governance to zero. In production Docker, `_CTG_AVAILABLE = True` because `src/trust-layer` is on `sys.path`. But there is no startup assertion that fails-fast if `_CTG_AVAILABLE = False` when running in production (`platform_phase = IMPLEMENTATION`).

**Risk:** A mis-configured Docker image or a refactoring that renames the trust-layer path would silently produce ungoverned LLM calls. C-041 would be violated without any log, error, or alert.

**Recommended fix (WC-040):** Add a startup health check that logs `CRITICAL` and refuses to serve if `_CTG_AVAILABLE = False and os.getenv("PLATFORM_PHASE") == "IMPLEMENTATION"`. Or: remove the fallback path entirely and replace with an explicit `raise ImportError` that prevents AIR from starting without CTG. **Deferred to WC-040.**

---

### GAP-003 — Minor: `dcm_category` hardcoded as `"CONSISTENT_SUFFICIENT"`

**Location:** `gateway.py`, Step 2

```python
dcm_category="CONSISTENT_SUFFICIENT",
```

**Problem:** C-099 (Decision Consequence Map) defines multiple DCM categories. Every tool type has its own category governing how the CE evaluates the action. Hardcoding `CONSISTENT_SUFFICIENT` means all tool calls are treated identically regardless of their consequence level.

**Impact:** Currently no CE rules distinguish by DCM category in test data, so tests pass. But as real DCM rules are loaded (WC-040+), misrouted categories will produce incorrect ALLOW/DENY decisions.

**Recommended fix:** `SessionContext` already has a `decision_space` field. Extend `SessionContext` (or add `dcm_category`) and derive the value from the tool_name/skill mapping. **Deferred to WC-041 (DCM integration).**

---

### GAP-004 — Minor: `SessionContext.decision_space` defined but unused

**Location:** `ctg/models.py` and `gateway.py`

The `decision_space` field is defined in `SessionContext` but never read in `gateway.call()`. It is not forwarded to CE. The CE's `ValidateActionRequest` as implemented in `_GrpcCEClient` uses only `contract_id`, `action_type`, `action_parameters`, and `decision_space_version` (hardcoded to 1).

This is a forward compatibility holder — the field exists for when decision space versioning is needed. **Acceptable as-is; no fix required. Noted for ADR-042 next amendment.**

---

## Positive Findings

1. **Token structural isolation is correct.** `ExceptionTranslator.translate()` does not accept a token parameter — structural prevention, not just convention. The token is never constructed into an error message even if the executor raises an exception that contains it.

2. **`DENY` blocks `_fetch_token` correctly.** The vault fetch (Step 3) occurs after CE validation (Step 2). CE DENY raises before the vault is ever called. CCT-CTG-04 test `test_deny_vault_not_called` validates this with `assert_not_called()`.

3. **Audit sink called on both success AND failure.** The `finally`-adjacent structure in `call()` ensures audit records are written even when the executor raises — execution_status="FAILED" on failure. CCT-CTG-03 tests both paths.

4. **`_make_gateway()` factory pattern** correctly separates construction from usage, making tests clean (patch one function to inject all mocks). This is the right pattern for dependency injection in async code.

5. **ADR-045 architectural record is correct.** Disk analysis and the three-runner (Python/dotnet/ts) split are technically sound. BuildKit `--mount=type=cache` is the correct solution for incremental pip builds. Image tagging scheme (`:current`, `:current-1`, `:canary`) correctly supports the blue-green requirement.

---

## Coverage Report (Post-Fix)

After GAP-001 fixes applied in this session:

| Module | Coverage |
|---|---|
| `ctg/__init__.py` | 100% |
| `ctg/models.py` | 100% |
| `ctg/exception_translator.py` | 100% |
| `ctg/registry_client.py` | 100% |
| `ctg/gateway.py` | ≥90% (pragma covers _GrpcCEClient gRPC stub) |
| **Total** | **≥90%** |

---

## Review Outcome

| Gap | Severity | Action | Sprint |
|---|---|---|---|
| GAP-001: coverage 78% | **Critical** | Fixed this session — 7 tests added + pragma | WC-039 |
| GAP-002: CTG fallback bypass | Significant | Deferred — startup assertion in WC-040 | WC-040 |
| GAP-003: dcm_category hardcoded | Minor | Deferred — DCM integration WC-041 | WC-041 |
| GAP-004: decision_space unused | Minor | Accepted — forward compatibility holder | N/A |

**WC-039 is AUTHORIZED to remain DONE after GAP-001 is fixed.**
**WC-040 (Skill Architecture Sprint 1) may proceed with GAP-002 as a carry-forward item.**

---

*Reviewed by: Enterprise Architect (INST-004)*
*Review file: reviews/R-022-sprint-039-ea-review.md*
