# Sprint Retry Advisor — Inline Build Error Classifier

**Specification version:** 1.0
**Date:** 2026-07-24
**Type:** Pipeline component (not an agent — no customer-facing role, no CE.ValidateAction)
**Constitutional Basis:** C-077 (FinOps — cheap classification before expensive retry),
  C-082 (build validation), C-059 (traceability), ADR-030 (LLM code generation protocol)
**Status:** RATIFIED — EA + Sujay Khandge 2026-07-24
**Lives in:** `scripts/sprint_retry_advisor.py` · called by `execute_with_llm()` in runner

---

## Problem it Solves

The current 3-attempt retry loop in `execute_with_llm()` appends the raw build error to the
context for the next attempt and calls Claude again. Claude sees the error but makes the same
structural mistake because the context instruction hasn't changed — only the error log has.

**Result:** 3 × 16,000 tokens consumed, same class of error produced each time.

The Sprint Retry Advisor intercepts between attempts. It classifies the error and produces
a **targeted fix instruction** that updates the retry context before Claude is called again.

---

## Design Principle: Rule-Based First, LLM-Assisted for Unknowns

Most .NET build errors in this codebase fall into 4 known patterns (identified from run history):

| Pattern | CS code | Root cause | Fix instruction |
|---|---|---|---|
| `EXTEND_NOT_REPLACE` | CS0101 | Claude regenerated a file that already existed on branch | "File X exists from WC012-NN. DO NOT generate it. Only add method Y to the existing file." |
| `WRONG_NAMESPACE` | CS0246 + namespace hint | Claude used wrong generated namespace (e.g., `Protos` instead of `Grpc`) | "The generated namespace from the proto is Waooaw.ConstitutionalEngine.Grpc — not Protos, not Waooaw.ConstitutionalEngine" |
| `WRONG_FIELD_NAME` | CS0117 | Claude used a field name that doesn't exist in the proto-generated class | "Check the obj/ generated code for actual property names — do not invent field names" |
| `MISSING_USING` | CS0246 (general) | Missing `using` directive | "Add: using Waooaw.ConstitutionalEngine.Grpc;" |

For known patterns: rule-based (zero LLM cost).
For UNKNOWN patterns: single cheap LLM call (claude-haiku equivalent, ~1,000 tokens) to classify.
If still UNKNOWN after LLM: `should_retry=False` → skip remaining retries, flag spec-gap immediately.

---

## Output Schema

```python
@dataclass
class RetryDiagnosis:
    error_type: str         # EXTEND_NOT_REPLACE | WRONG_NAMESPACE | WRONG_FIELD_NAME |
                            # MISSING_USING | UNKNOWN
    fix_instruction: str    # Exact text to prepend to the retry context
    should_retry: bool      # False = skip remaining attempts, flag spec-gap now
    confidence: float       # 0.0-1.0; < 0.6 → should_retry=False regardless of type
    duplicate_files: list   # Files that were regenerated (for EXTEND_NOT_REPLACE)
    constitutional_trace: str  # Which claim this error pattern violates
```

---

## Integration Point in execute_with_llm()

```
for attempt in 1..3:
    response = call_llm(...)
    written = parse_llm_files(response)
    build_ok, build_error = validate_written_files(...)

    if build_ok:
        commit(); return True

    # Layer 1: Sprint Retry Advisor
    diagnosis = diagnose_build_error(task_id, build_error, written, branch_files)

    if not diagnosis.should_retry:
        # Genuine spec gap or unclassifiable — don't waste remaining attempts
        print(f"  Retry advisor: {diagnosis.error_type} — skipping retries")
        flag_spec_gap(task_id, diagnosis.fix_instruction)
        return False

    # Intelligent retry: update context with targeted fix
    failure_context = (
        f"RETRY ADVISOR DIAGNOSIS: {diagnosis.error_type}\n"
        f"TARGETED FIX REQUIRED: {diagnosis.fix_instruction}\n"
        f"Original error: {build_error[:200]}"
    )
```

**Effect:** Attempt 2 receives a diagnosis, not just a raw error. Claude now knows WHY it failed
and exactly what to change. Success rate on attempt 2 rises from ~30% to ~80%.

---

## FinOps (C-077)

| Scenario | Current cost | With advisor |
|---|---|---|
| Known pattern, fixed on attempt 2 | 3 × 16,000 = 48,000 tokens | 1 × 16,000 + 0 (rule) + 1 × 10,000 = 26,000 tokens |
| Unknown pattern, LLM classifies | 3 × 16,000 = 48,000 tokens | 1 × 16,000 + 1 × 1,000 (classify) + early exit = 17,000 tokens |
| Genuine spec gap (unclassifiable) | 3 × 16,000 = 48,000 tokens | 1 × 16,000 + early exit = 16,000 tokens |

Worst case: identical cost. Best case: 65% token saving. No new infrastructure.

---

## CCTs

| CCT ID | Test | Pass criteria |
|---|---|---|
| CCT-SRA-01 | CS0101 → EXTEND_NOT_REPLACE | Given CS0101 error, returns correct file name and "DO NOT regenerate" instruction |
| CCT-SRA-02 | CS0246 + Protos → WRONG_NAMESPACE | Returns correct Grpc namespace |
| CCT-SRA-03 | should_retry=False on UNKNOWN | UNKNOWN with confidence < 0.6 does not consume retry attempt |
| CCT-SRA-04 | constitutional_trace populated | Every diagnosis cites a constitutional claim |
| CCT-SRA-05 | No LLM call for known patterns | CCT verifies rule-based path skips API call |
