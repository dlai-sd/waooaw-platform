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

---

---

# Part II — Chief Architect Office: Autonomous Codebase Lifecycle
**Trigger:** How does WAOOAW maintain its codebase in fully autonomous mode across all scenarios — first implementation, ongoing defects, and constitutional amendments triggered by regulations?

---

## The Three Lifecycles

```
LIFECYCLE 1: First Implementation (what we're doing in WC-012 to WC-018)
  Constitutional claim exists → Work Contract written → Sprint Agent implements

LIFECYCLE 2: Defect Fixes (what happens after WC-018 is merged)
  CCT fails OR bug filed → Constitutional Compliance Scanner identifies → 
  Sprint Agent remediates → re-runs CCTs

LIFECYCLE 3: Constitutional Amendment (regulation arrives after 2 years)
  Plain-English change from Founder → Constitution updated → 
  Impact Analysis finds all affected code → WCs generated → Sprint Agent propagates
```

All three lifecycles share one foundation: **C-059 traceability**. Every file in this codebase already carries `// constitutional_basis: C-NNN` in its header. This is not a bureaucratic annotation — it is the machine-readable index that makes autonomous lifecycle 3 possible.

---

## Real-Life Scenario: "Add Data Masking and Encryption"

Founder says (plain English):
> "Add data masking to private fields and encryption to critically important fields of customer data."

### What MUST happen (full decomposition):

**Step 1 — Constitutional interpretation (human + EA, one time):**
```
Founder input:
  "private fields" → constitutional definition needed: which fields are PII?
  "critically important" → constitutional definition needed: what is CRITICAL tier?
  "customer data" → which components own customer data?

Output: New constitutional claim C-NEW-001 with:
  - Taxonomy: PII_TIER1 (name, phone, email), PII_TIER2 (address, DOB), CRITICAL (bank_account, aadhaar)
  - Rule 1: PII_TIER1/TIER2 must be masked in logs, API responses, error messages
  - Rule 2: CRITICAL must be encrypted at rest (AES-256-GCM), decrypted only in-memory
  - CCT requirement: CCT-PII-01 (adversarial log scan — no PII in output)
  - CCT requirement: CCT-ENC-01 (DB dump scan — CRITICAL fields not plaintext)
```

**Step 2 — Impact analysis (currently manual, should be automated):**

Because every file already has `constitutional_basis: C-NNN` headers (C-059), the system CAN do:
```bash
grep -r "customer\|CustomerPhone\|aadhaar\|bank_account" src/ --include="*.cs" --include="*.py"
grep -r "log\.\|logger\.\|print\|Logger" src/ --include="*.cs" --include="*.py"
```

Today this is manual. The autonomous version is an Impact Analysis Engine that:
1. Reads C-NEW-001 definition (field categories + rules)
2. Scans all `src/` files for fields matching PII taxonomy
3. Scans all `src/` files for logging statements
4. Produces an impact report: "these 47 locations need changes"

**Step 3 — Work Contract generation (currently manual):**
From the impact report, the system generates:
```
WC-NNN-platform-it-expert-sprint-NNN-pii-masking.md:
  Task 1: Create PiiMaskingService (.NET + Python) — deterministic template
  Task 2: Add [PiiMask] / [Encrypt] attribute to all identified entities
  Task 3: Intercept all log statements to apply masking
  Task 4: Add EF Core value converters for CRITICAL field encryption
  Task 5: CCT-PII-01 adversarial test (log PII fields, assert they are masked)
  Task 6: CCT-ENC-01 scan (dump DB, assert CRITICAL fields are ciphertext)
```

**Step 4 — Sprint Agent executes (already exists, today's capability):**
Same mechanism as WC-012 — deterministic scaffolds for the service/converter patterns, LLM fills business logic slots.

**Step 5 — Compliance scanner verifies (partially exists via CCTs, should be continuous):**
```
After merge: scan every log statement in codebase → assert no PII in output
After merge: query DB → assert CRITICAL fields are encrypted
Weekly cron: re-run compliance scan → alert on any new violation
```

---

## The Architecture That Makes This Autonomous at Scale

### What exists today (the foundation):
```
✅ C-059 traceability — every file carries constitutional_basis header
✅ AGENTS.md convention — agents know which claims govern each directory
✅ CCT mechanism — constitutional compliance tests, run on PR
✅ Constitutional claim files — knowledge/claims/C-NNN.md (human-readable)
✅ Sprint agent — executes Work Contracts autonomously
✅ Deterministic scaffold + LLM slot-filling (recommended in Part I)
```

### What is missing (the gaps):
```
❌ Machine-readable claim registry — claims are prose .md files, not structured data
❌ Impact analysis engine — no system maps "claim changed" → "files affected"
❌ WC generator from claim diff — no system produces WCs from constitutional amendments
❌ Cross-cutting change orchestration — pipeline is per-service, per-sprint; PII touches all services
❌ Continuous compliance scanner — CCTs run on PR only, not as ongoing monitoring
```

### Target architecture (3-phase evolution):

**Phase 1 — Now (WC-012 to WC-018): Build the implementation layer.**
Each sprint builds a service. Traceability is established. CCTs catch violations on PR. Source-injection + slot-filling makes code generation reliable.

**Phase 2 — (WC-019+): Semi-autonomous amendment propagation.**

Add `knowledge/claims/C-NNN.yaml` alongside each `.md`:
```yaml
# C-078.yaml — machine-readable companion to C-078.md
claim_id: C-078
tier: PII_PROTECTION
applies_to:
  field_patterns: ["*Phone*", "*Email*", "*Aadhaar*", "*BankAccount*"]
  file_patterns: ["src/**/*.cs", "src/**/*.py"]
  context_types: [logging, api_response, error_message, db_storage]
enforcement:
  logging: mask  # replace with ***MASKED***
  db_storage: encrypt  # AES-256-GCM for CRITICAL tier
ccts:
  - CCT-PII-01: no_pii_in_logs
  - CCT-ENC-01: critical_fields_encrypted_at_rest
```

The Impact Analysis Engine reads these YAML files and produces:
```json
{
  "affected_files": ["src/business-platform/Models/Customer.cs", ...],
  "affected_log_sites": ["src/business-platform/Controllers/CustomersController.cs:L47", ...],
  "work_contracts_needed": ["WC-NNN-pii-masking"],
  "estimated_sprint_count": 2
}
```

**Phase 3 — (12-18 months): Fully autonomous constitutional amendment absorption.**

Founder writes constitutional amendment in plain English.
The "Constitutional Amendment Agent" (a new Office):
1. Parses plain-English amendment → drafts C-NNN.yaml + C-NNN.md
2. Runs impact analysis → produces affected file list
3. Drafts Work Contracts (using WC template)
4. Submits for Founder approval
5. On approval: sprint agent executes, compliance scanner verifies
6. Generates compliance evidence report

---

## The DPDP / GDPR Scenario (Regulation Arrives in 2 Years)

India's Digital Personal Data Protection (DPDP) Act or GDPR equivalent lands. Founder says:
> "We must comply with DPDP. Data principals have the right to erasure. All personal data must have a lawful basis for processing. Processors must notify breaches within 72 hours."

**Today's path (manual, months of work):**
1. Lawyer reads regulation → maps to requirements → takes 3 months
2. Architect maps requirements to code → impact analysis → takes 2 months
3. Dev team implements → takes 6 months
4. Audit → re-work → takes 3 months
**Total: 12-18 months, high risk of drift between requirement and implementation**

**WAOOAW's path (with Phase 3 architecture):**
1. Founder reads regulation → adds 3 constitutional amendments (1 hour)
2. Constitutional Amendment Agent parses amendments → drafts claim YAMLs → Founder approves (1 day)
3. Impact Analysis Engine finds all affected locations (minutes)
4. WC Generator produces work contracts (minutes)
5. Sprint Agent implements across all services (hours to days)
6. Compliance Scanner verifies and produces audit-ready evidence (automated)
**Total: Days to weeks. Full constitutional traceability on every change.**

The key insight: **WAOOAW's constitutional model IS the compliance framework.** Regulations are just external claims that must be mapped to internal claims. Once mapped, the entire implementation chain is automated.

---

## Defect Lifecycle (Ongoing Maintenance)

Scenario: A bug is filed — "Customer phone number appears in logs."

**With current architecture (Phase 1):**
1. Human reviews bug → identifies it violates C-078
2. Human opens GitHub issue → assigns to sprint
3. Sprint agent generates fix → PR → merge

**With Phase 2 architecture (compliance scanner):**
1. Compliance scanner detects violation (next nightly run)
2. Files GitHub issue automatically with `constitutional_basis: C-078`, `affected_file`, `line_number`
3. Severity computed from claim tier (C-078 = high → auto-assign to next sprint)
4. Sprint agent generates targeted fix (slot-filling, not whole file regeneration)
5. Scanner re-runs → validates fix → closes issue

No human in the loop. The constitutional annotation (`// constitutional_basis: C-078`) in the source file is the mechanism — scanner knows what claim governs that file, so it knows what rule to check.

---

## What This Means for Current Sprint Pipeline Design

The decisions we make now in WC-012 to WC-018 lock in the foundation. Two decisions matter:

**Decision 1: Constitutional annotation discipline (already in place)**
Every generated file must carry `// constitutional_basis: C-NNN` accurately. This is C-059. It is already enforced. DO NOT relax this — it is the entire traceability foundation for Phase 2 and 3.

**Decision 2: Source injection + slot-filling (Part I recommendation)**
When we shift to slot-filling for business logic, the claim that governs each SLOT should be the template marker:
```csharp
/* SLOT: implement C-041 Tool Authorization logic here
   C-041: The agent may only use tools explicitly listed in authorized_actions[].
   Input: ctx.GetParameter("tool_name")
   Return: EvaluationResult.Allow("C-041") or EvaluationResult.Deny("C-041", reason) */
```

This makes the slot itself a machine-readable constitutional contract. When C-041 changes, the scanner knows exactly which slots are affected.

---

## Summary: The Autonomy Ladder

| Level | Mechanism | Status |
|---|---|---|
| L1: Annotated code | `// constitutional_basis: C-NNN` in every file | ✅ Done |
| L2: Per-sprint LLM generation | Sprint Agent + CCTs | ✅ Partially working (fixing now) |
| L3: Source-grounded generation | `inject_source_files` + slot-filling | 📋 Recommended (pipeline.md Part I) |
| L4: Machine-readable claims | `C-NNN.yaml` alongside prose `.md` | ❌ Not started |
| L5: Impact analysis | Claim-change → file-list | ❌ Not started |
| L6: WC generation from claims | Amendment → Work Contracts | ❌ Not started |
| L7: Continuous compliance scan | Nightly CCT scan → auto-issue | ❌ Not started |
| L8: Full autonomous amendment | Amendment → code → verified | ❌ Future (Phase 3) |

**The principle:** Every level depends on the level below it being solid. We are currently fixing L2 → L3. L4 through L8 require L3 to be reliable first.

**The "data masking after 2 years" scenario requires L4 through L7.** It cannot be built until L3 is reliable. The current whack-a-mole with retry handlers is preventing us from advancing the ladder.

---

*Chief Architect recommendation: Fix L3 (source injection + slot-filling) now. Charter L4 (machine-readable claims) as a distinct IB item after WC-018 completes. L5 through L8 are future IB items under Gate G6 (Autonomy Maturation).*

