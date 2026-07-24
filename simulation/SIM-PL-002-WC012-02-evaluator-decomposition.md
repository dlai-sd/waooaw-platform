# SIM-PL-002 — WC012-02 Evaluator Decomposition
**Date:** 2026-07-24
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC012-02 — CE ValidateAction RPC + evaluator unit tests
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

---

## Context

WC012-02 previously ran as a single LLM call generating ~13 files.
Empirical evidence from runs 30101948609 / 30103437538 / 30104540921:
- `stop_reason='max_tokens'` on every attempt
- `text_chars=0` (thinking overflow) or `text_chars=49,429` (code truncation mid-file)
- CS1061 build error on truncated output

Root cause: single call generating 7 evaluator classes + service + tests
exceeds reliable output budget regardless of `max_tokens` setting.

---

## Decomposition Design

### Sub-task WC012-02a — Deterministic Interface Contracts
**Type:** deterministic  
**Depends on:** []  
**Output:** 4 files in `Evaluators/`
- `EvaluationResult.cs` — verdict enum + record
- `EvaluationContext.cs` — immutable record wrapping `ValidateActionRequest`
- `IClaimEvaluator.cs` — evaluator interface
- `EvaluatorRegistry.cs` — parallel execution of all evaluators

**Risk:** None — pure structural templates, no LLM.
**Compile gate:** `dotnet build` — verifies namespace and using directives.

### Sub-task WC012-02b — Evaluator Implementations
**Type:** LLM (reasoning, 8K tokens)  
**Depends on:** WC012-02a  
**Output:** 5 evaluator files + extend ConstitutionalEngineService.cs
- C041ToolAuthorizationEvaluator, C043BudgetCeiling, C048NonExploitation, C049HonestLimitation, C062AiSecurity
- ValidateAction RPC: calls EvaluatorRegistry.EvaluateAllAsync, aggregates DENY-wins

**Risk (mitigated):** Branch context provides 02a interfaces → model implements against real types.
**Compile gate:** `dotnet build` — verifies IClaimEvaluator implementation completeness.

### Sub-task WC012-02c — CCT Test Suite
**Type:** LLM (reasoning, 5K tokens)  
**Depends on:** WC012-02a, WC012-02b  
**Output:** 3 test files
- FakeServerCallContext.cs (concrete stub, non-virtual)
- CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs
- CCT_EF01_C043BudgetCeilingEvaluatorTests.cs

**Risk (mitigated):** Branch context has all evaluator implementations → tests reference real method signatures.
**Compile gate:** `dotnet build` on test project.

---

## Dependency Order Validation

```
WC012-02a (deterministic) → compile → PASS
         ↓
WC012-02b (LLM, 8K) → compile → PASS
         ↓
WC012-02c (LLM, 5K) → compile → PASS
```

C-084 (Step Dependency Ordering): any sub-task failure halts the chain.

---

## Token Budget Analysis

| Sub-task | Type | max_tokens | Thinking budget | Effective | Files |
|---|---|---|---|---|---|
| 02a | deterministic | n/a | n/a | n/a | 4 |
| 02b | LLM | 8,000 | 8,000 | 16,000 | 6 |
| 02c | LLM | 5,000 | 8,000 | 13,000 | 3 |
| **Total** | | | | | **13** |

vs single-call: 10,000–14,000 tokens for 13 files → repeated truncation.

---

## Verdict

**VERDICT: ✅ PASS**

The decomposition eliminates the token ceiling failure mode.  
- 02a is deterministic and correct by construction.  
- 02b has a focused scope (5 business rule implementations + service) within 8K code budget.  
- 02c tests real code from branch context — higher accuracy than testing predicted interfaces.  
- C-084, C-083, C-082 all satisfied by the TaskDecomposer chain.

**C-086 gate: SIM-PL-002-WC012-02 PASS — implementation authorized.**
