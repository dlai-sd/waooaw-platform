# Autonomous Sprint Pipeline — Expert Analysis
**Prepared by:** Platform IT Expert (Copilot, Office 10)
**Date:** 2026-07-24
**Status:** FOR FOUNDER REVIEW — do not implement until reviewed
**Trigger:** User identified systemic hallucination pattern across 7+ sprint runs

---

## Executive Summary

The current pipeline is architecturally sound in its orchestration (C-084 step dependency, C-083 signals, C-085 idempotency, C-086 simulation gate) but has a fundamental **prompt grounding deficiency** that will produce a new compile error type on every sprint run. The error taxonomy in `sprint_retry_advisor.py` is a symptom of this deficiency — not the cure.

**The core problem in one sentence:**
> The LLM generates entire source files while seeing only text *descriptions* of the types it must conform to — it has never seen the actual compiled source it depends on.

At 40+ sprints with 3-5 LLM files per sprint, the current approach will require 150+ unique retry advisor rules. That is not engineering.

---

## What the Current Pipeline Actually Does

```
Work Contract MD
      ↓ (parsed by WCSpecReader)
SubTaskDef
      ↓ (assembled by _build_effective_check)
LLM Prompt = [
  PMO spec section excerpts     ← text summaries of specs
  output_files list             ← filenames only, no content
  STACK_BEHAVIORAL_RULES        ← general prose rules
  constitutional_check delta    ← hand-written prohibitions
  PTR type block                ← JSON summaries of types
  branch_context                ← file NAMES (not contents)
]
      ↓ (Claude Sonnet 4.6, max_tokens=4000)
Full file generated             ← LLM must infer all structure
      ↓ (compile gate)
CS error → retry_advisor        ← new handler for each error type
      ↓ (3 retries max)
flag_spec_gap() if all fail     ← UNKNOWN → 1 attempt, immediate halt
```

**5,171 lines across 5 scripts.** Grew from ~500 lines organically. Each new error adds ~30 lines to sprint_retry_advisor.py. This is correct for a tactical phase but not for 40 sprints.

---

## Root Cause Analysis — Why Hallucinations Recur

### Layer 1: The LLM never sees dependent source files
When generating `C041ToolAuthorizationEvaluator.cs`, the LLM receives a PTR block like:
```json
{"IClaimEvaluator": {"kind": "interface", "fields": {"ClaimId": "string", "EvaluateAsync": "method"}}}
```
Not the actual file:
```csharp
public interface IClaimEvaluator {
    string ClaimId { get; }
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct = default);
}
```
The LLM's training data contains thousands of richer evaluator interfaces. It fills in what it *knows* evaluators typically have (`ApplicableActionTypes`, `Priority`, etc.) because the prompt doesn't contradict that knowledge — it just doesn't confirm it.

**Hallucination type:** Confident confabulation from training distribution, not prompt content.

### Layer 2: Each lossy transformation adds surface area
```
MD spec → parsed excerpt → constitutional_check text → LLM inference → full file
```
Every arrow is a lossy encoding. The spec says "implement C-041 Tool Authorization." By the time that becomes a 4,000-token output, the LLM has made 50+ structural decisions the spec never specified — and some will be wrong.

### Layer 3: "File-by-file" is still "whole file generation"
The file-by-file migration (IB-023) correctly reduced prompt size and isolated errors. But it didn't change the fundamental problem: the LLM still generates 150 lines of C# where only 15 lines are novel.

The 135 lines of boilerplate (`using` directives, class declaration, property getters, interface conformance pattern) are deterministic — they have exactly one correct form. Asking the LLM to regenerate them introduces 135 lines of hallucination surface area per file.

### Layer 4: UNKNOWN → immediate halt (the 2-minute run problem)
The retry advisor correctly returns `should_retry=False` for UNKNOWN patterns. This means:
- CS0539 on run 1 → 1 attempt, immediate halt, 2.5-minute run
- CS0019 on run 2 → 1 attempt, immediate halt, 3.5-minute run
- Actual progress: zero. All API cost wasted.

The UNKNOWN handler is correct in principle (don't retry things you can't fix) but creates a liveness problem when the real fix is structural.

---

## Industry Patterns for LLM Code Generation at Scale

Across GitHub Copilot, Cursor, Amazon Q, Devin, and SWE-agent, four patterns consistently work:

### Pattern 1: Full Source Context (what Cursor does)
Before generating any file, inject the COMPLETE source of all files it depends on — not summaries. The LLM cannot hallucinate `ApplicableActionTypes` if it sees `IClaimEvaluator.cs` verbatim in the prompt. The context window cost is 2-4KB per dependent file; the error elimination rate approaches 100% for structural errors.

**Implementation cost:** Low (read files from disk, prepend to prompt)
**Error types eliminated:** CS0539, CS1061, CS1503, CS0534, CS0019, CS0117

### Pattern 2: Slot-Filling (what GitHub Copilot does)
Write deterministic structural boilerplate. Ask the LLM to fill only the creative/variable slot — the method body. For 5 constitutional evaluators, the slot is 10-30 lines of business logic per evaluator. The class declaration, using directives, interface conformance, property getters are all fixed.

```
DETERMINISTIC (template writer):
  class declaration, using directives, ClaimId property, EvaluateAsync signature

LLM FILLS (10-30 lines):
  EvaluateAsync body — the business logic for THIS constitutional claim
```

**Implementation cost:** Medium (new `slot_filling` SubTaskDef type, template writer per pattern)
**Error types eliminated:** ALL structural errors (CS0539, CS0505, CS0534, CS1503, CS0246, CS0117 on boilerplate)

### Pattern 3: Structured Output (what Amazon Q does)
Request JSON instead of raw source. Template splices the result.

```python
LLM output: {"method_body": "var toolName = ctx.GetParameter(\"tool_name\");\n..."}
Template: fills the body into a pre-written .cs template
```

**Implementation cost:** Medium (structured output parsing, per-pattern templates)
**Error types eliminated:** All structural errors + namespace errors

### Pattern 4: Method-Level Generation (what SWE-agent does)
Generate one METHOD at a time, not one FILE at a time. The file starts compilable (empty stubs). Each LLM call adds one method via a diff. Rollback a single method on error — not the whole file.

**Implementation cost:** High (diff-based apply, per-method compile gate)
**Error types eliminated:** All — by reducing surface area to the minimum

---

## What-If Analysis

### What if we continue the current approach?
- Each sprint run produces 1-2 new CS error types
- Each requires a new retry_advisor handler + constitutional_check prohibition
- WC-012 alone has generated handlers for: CS0101, CS0117, CS0246, CS1061, CS0505, CS0266, CS0037, CS1503, CS0534, CS0019, CS0539
- 40 sprints × 1.5 errors/sprint = ~60 retry handlers
- sprint_retry_advisor.py grows to ~2,000 lines
- Each handler adds ~20 lines to constitutional_check strings in autonomous_sprint_runner.py
- By WC-030, the prompt will be so large it hits attention limits

**Verdict:** Not viable beyond WC-015.

### What if we implement Pattern 1 (Full Source Context Injection) only?
- Add `inject_source_files: list[str]` to SubTaskDef
- Before each file-by-file call, read those files from disk, prepend as `=== SOURCE: {name} ===` blocks
- For WC012-02b: inject EvaluationContext.cs, IClaimEvaluator.cs, EvaluationResult.cs (~8KB)
- Total prompt size: ~30KB (within context window)

**Expected error reduction:** 70-80% of current error types gone (the "invented member" class entirely eliminated)
**Risk:** None — additive change, backward compatible
**Constitutional compliance:** C-032 preserved (LLM still implements, not architecting), C-086 gate unchanged

### What if we implement Pattern 2 (Slot-Filling) for evaluators?
- 5 evaluators follow identical structure — only EvaluateAsync body varies
- Template function writes class skeleton, calls LLM only for `// TODO: business logic` slot
- LLM output is 10-30 lines, not 150 lines

**Expected error reduction:** 100% of structural errors for this pattern
**Risk:** Template must be maintained per sprint type; slot boundary must be clear
**Constitutional compliance:** C-032 requires spec to precede implementation — template IS the spec materialised
**FinOps (C-077):** Token cost drops by ~70% per evaluator file (10 lines vs 150 lines)

### What if we implement both P1 + P2?
WC-012 evaluators work reliably. Future sprints (FastAPI endpoints, Temporal workflows) all follow the same pattern — each has a fixed structural shell and a variable implementation slot. P1 handles the "grounded generation" for files where structure varies; P2 handles the "slot-filling" for files where structure is fixed.

---

## Concrete Recommendations

### Recommendation 1 — IMMEDIATE (1 sprint's work): Source Context Injection
**Decision needed:** Approve `inject_source_files` field on SubTaskDef.

How it works:
```python
# SubTaskDef addition:
inject_source_files: list[str] = []  # paths relative to REPO_ROOT

# In execute_file_by_file(), before building prompt:
source_block = ""
for path in st.inject_source_files:
    if (REPO_ROOT / path).is_file():
        content = (REPO_ROOT / path).read_text()
        source_block += f"\n=== ACTUAL SOURCE: {path} (READ THIS — do not invent members) ===\n{content}\n"
```

WC012-02b wiring:
```python
inject_source_files=[
    "src/constitutional-engine/Evaluators/EvaluationContext.cs",
    "src/constitutional-engine/Evaluators/IClaimEvaluator.cs",
    "src/constitutional-engine/Evaluators/EvaluationResult.cs",
    "src/constitutional-engine/Evaluators/EvaluatorRegistry.cs",
],
```

**Files changed:** task_decomposer.py (+15 lines), autonomous_sprint_runner.py (+4 lines to SubTaskDef)
**Test impact:** Tests need update to assert inject_source_files respected

### Recommendation 2 — SHORT-TERM (authoring work per sprint type): Slot-Filling Mode
**Decision needed:** Approve new `type="slot_fill"` on SubTaskDef and template convention.

Template convention for evaluators:
```
architecture/reference/templates/evaluator_template.cs
```
Contains the full evaluator structure with `/* SLOT_START */` and `/* SLOT_END */` markers.

The LLM receives:
```
Here is the COMPLETE file template. Fill ONLY the slot between SLOT_START and SLOT_END.
Output ONLY the slot content — no class declaration, no using directives, no property getters.
```

LLM output (10-30 lines):
```csharp
// C-041: Tool Authorization check
var toolName = ctx.GetParameter("tool_name");
if (string.IsNullOrEmpty(toolName))
    return EvaluationResult.Deny("C-041", "No tool_name specified");

var allowedTools = new HashSet<string> { "search", "write", "read" };
return allowedTools.Contains(toolName)
    ? EvaluationResult.Allow("C-041")
    : EvaluationResult.Deny("C-041", $"Tool '{toolName}' not in authorized set");
```

**Files changed:** task_decomposer.py (+60 lines), architecture/reference/templates/*.cs (new)
**Constitutional note:** Templates live in `architecture/reference/` — C-032 compliant (architecture precedes implementation)

### Recommendation 3 — ARCHITECTURAL PRINCIPLE (no implementation yet): Spec IS Template
For future sprints, the architecture spec file for each component type should contain the code template with slots, not just prose. The flow becomes:

```
architecture/reference/components/business-platform.md
      ↓ (contains template blocks with slots)
Template writer extracts template + slot definitions
      ↓
LLM fills slots (business logic only)
      ↓
Template writer assembles final file
      ↓
Compile gate
```

This is the "one source → one outcome" model the user described. It is architecturally clean but requires an EA decision on template format conventions.

**Constitutional alignment:** C-032 (spec precedes implementation — the template IS the spec materialised), DP-009 (API First — extend to "spec-first code generation")

---

## What to NOT Do

1. **More retry_advisor handlers** — tactical, not strategic. Each handler is a symptom acknowledgement, not a cure.

2. **More constitutional_check prohibitions** — prompt bloat. The LLM already has a 22,000-token prompt. Adding more `⛔ DO NOT` rules pushes useful context further down (attention dilution is real at this scale).

3. **Larger token budgets** — won't reduce hallucination rate. Larger output budget means more lines generated = more surface area for structural errors.

4. **More layers of abstraction** — WCSpecReader, PTR, constitutional_check, STACK_BEHAVIORAL_RULES are each a lossy encoding of the spec. Each additional layer adds more leakage, not less.

5. **Parallel file generation** — will create merge conflicts on files both tasks touch (e.g., ConstitutionalEngineService.cs extended by WC012-02b and WC012-03b). The sequential file-by-file approach is correct.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Source injection exceeds context window | Low | High | Files are ~2-4KB each; inject only 3-4 files; 30KB well within 200K context |
| Template becomes stale vs actual source | Medium | Medium | Template validated by compile gate before first use |
| Slot-filling misidentifies slot boundary | Low | Low | Explicit markers (`/* SLOT_START */`) + validation that non-slot lines unchanged |
| EA approval needed for template format | Certain | Low | This is an architectural decision — put it in ADR-030 Amendment 2 |

---

## Proposed Decision Sequence

1. **Founder approves this analysis** — or requests changes
2. **EA Decision (ADR-030 Amendment 2):** Approve `inject_source_files` + slot-filling template convention
3. **Simulation (C-086):** SIM-PL-003 — slot-filling simulation before implementation
4. **Implementation:** task_decomposer.py `inject_source_files` support + template for CE evaluators
5. **WC012 run:** First clean run with source injection
6. **Retrospective:** After WC012 completes, assess whether slot-filling is needed for WC013+

---

## Appendix — Error Taxonomy (today's state)

| Error | Root cause | Handler exists? | Structural fix |
|---|---|---|---|
| CS0539 | Invented interface member | ✅ | Source injection |
| CS1061 | Invented field on type | ✅ | Source injection |
| CS0117 | Invented proto field | ✅ | Source injection |
| CS0019 | `??` on non-nullable | ✅ | Source injection (shows actual type) |
| CS0266/CS0037 | null → value type | ✅ | Source injection |
| CS0505 | Property as method | ✅ | Source injection (FakeServerCallContext) |
| CS0534 | Missing abstract member | ✅ | Template completeness |
| CS1503 | Wrong collection type | ✅ | Source injection |
| CS0246 | Missing using | ✅ | Source injection |
| CS0101 | Class already defined | ✅ | EXTEND-NOT-REPLACE |
| Future CS#### | Unknown | ❌ | Source injection (preemptive) |

If source injection had been present from day 1, the errors in rows 1-9 would not have occurred. The retry_advisor would have been needed only for rows 10-11.

---

*This document is input for a Founder + EA architectural decision. It does not authorize any implementation.*
