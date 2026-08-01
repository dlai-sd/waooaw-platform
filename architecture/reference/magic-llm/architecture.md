# MagicLLM — Engineering AI Execution Layer

**Classification:** Reference Architecture — **Universal Constitutional AI Execution Layer**
**Status:** RATIFIED — governing from 2026-07-28 (amended by Constitutional Review Board after production sprint evidence)
**Produced by:** AI Architect (INST-008) — GOAL-001 Phase 3 (2026-07-27) · Amended GOAL-002 Phase A (2026-07-27) · Gap-closed 2026-07-28 (10 constitutional violations corrected)
**Constitutional Basis:** C-069 (Platform Self-Improvement) · C-059 (Traceability) · C-073 (@constitutional annotations) · C-070 (Three Basic Instincts) · ORGANIZATION.md Office 08
**Goal Reference:** GOAL-001 Phase 3 · GOAL-002 Phase A
**ADR Reference:** ADR-032 (amended — Universal Constitutional AI Execution Layer)

**AMENDMENT RECORD (2026-07-28):** Ten constitutional violations identified through production sprint evidence (runs 30294588380 through 30349793469). All violations corrected in this document. Violations were: unratified status (governance gap), aspirational Context Builder (no algorithm), undefined Prior Task Injection, incomplete Response Evaluator (1/5 gates), disconnected Retry Advisor, auto-PTR population gap, missing File Preamble Contract, undefined retry loop algorithm, missing frozen artifact concept, and undefined fallback behavior.

---

## §0 — The Disruption

MagicLLM is not a better LLM interface.

Traditional LLM interfaces make the LLM the intelligence and the human the governor:
- **Pair programming:** Human directs. AI suggests. Human reviews. Human merges. The LLM assists. The human decides.
- **Small code generation:** Human provides a prompt with local context. AI generates a snippet. Human integrates it. One call, no continuity, no accountability.
- **Copilot-style:** Autocomplete with project context. The LLM guesses what the human would write next.

In all of these models: the LLM does the thinking. The human holds the accountability.

**MagicLLM inverts this completely.**

The LLM is the execution instrument. The Constitution is the intelligence.

The intelligence in WAOOAW's system is not in any model — it lives in 79 ratified constitutional claims, a 16-step Engineering Execution Model, a Goal that represents a constitutional commitment to an outcome, and an institutional accountability chain traceable from a line of code back to the Founder's ratification. MagicLLM's job is to take that constitutional intelligence and translate it into precise LLM invocations that produce **constitutionally traceable artifacts** — not just code.

Every file MagicLLM produces carries its full institutional lineage:

```python
# Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
# Constitutional basis: C-041 (Tool Authorization — LAW)
# Goal: GOAL-001 | Work Contract: WC-013 | GO Authorization: GOA-GOAL-001-INST-010-03
# Produced by: MagicLLM | Model: Claude Sonnet 4.6 | Session: MDR-GOAL-001-INST-010-03
```

**The repository is not a codebase. It is a constitutional evidence record that happens to be executable.**

This produces four disruptions that no traditional LLM interface can replicate:

**Disruption 1 — From instruction-following to outcome-pursuing.**
Traditional LLM: "write this function." MagicLLM: "this Goal requires this outcome and the system is constitutionally obligated to pursue it through 16 governed steps — the LLM is one instrument in that pursuit, constrained by the spec, the PTR, the compile gate, the spec alignment check, and three Goal Outcome Alignment Gates."

**Disruption 2 — From context window to constitutional context.**
Traditional LLM: "here is the code around where you need to write." MagicLLM: "here is the constitutional context — the claim that justifies this code's existence, the spec that defines what it must do, the Platform Type Registry that tells you what types are compiled, the constitutional obligations that define what it may not do, and the prior task output that you must preserve."

**Disruption 3 — From isolated generation to repository blending.**
Traditional LLM: one file at a time, no awareness of the whole. MagicLLM: EEM Step 09 (Repository Blending) ensures the repository appears written by one engineering team — not by dozens of independent LLM calls. The blending step is what makes MagicLLM output institutionally coherent, not just individually correct.

**Disruption 4 — From human review gate to constitutional review gate.**
Traditional LLM: human decides if the code is acceptable. MagicLLM: code must pass compile gate, spec alignment gate, annotation gate, Design-to-Code Alignment Report, CCT suite, and three Goal Outcome Alignment Gates (Steps 06, 10, 14) before it is constitutionally complete. The Founder governs outcomes. Institutions govern quality. The constitution governs both. The LLM executes under all of them.

**The magic is not in the model.** Gemini 2.5 Pro and Claude Sonnet 4.6 are available to anyone. The magic is in what governs them. A system where LLMs cannot ship code without a constitutional claim justifying it, a spec section authorizing it, a compile gate confirming it, and a Goal Outcome Alignment Gate verifying it serves the original business outcome — that system does not exist anywhere else.

A dental clinic, a cotton farmer, a salaried trader — none of them can afford the human engineering team that would produce this level of constitutionally governed software. MagicLLM is the mechanism that makes the WAOOAW promise possible: the same quality of institutional engineering, available to anyone who registers a Goal.

---

## 1. What MagicLLM Is — and Is Not

**MagicLLM is not an LLM wrapper.**

An LLM wrapper takes a prompt, calls a model, returns the response. MagicLLM does not do this. MagicLLM is the **constitutional intelligence layer** that governs every decision involved in using AI during engineering execution:

- Which model to use — and why
- How to build the context — and what to exclude
- What temperature, token budget, and tools to apply
- Whether the response is constitutionally acceptable
- Why a retry is needed — and what specific correction to make
- What evidence of all these decisions to produce

MagicLLM makes these decisions constitutionally — producing evidence for each. A decision made by MagicLLM without a corresponding Decision Record is constitutionally invalid (C-059: no action without a traceable record).

**MagicLLM does not decide what to build.** That is the Engineering Execution Model's responsibility (EEM Steps 01–07). MagicLLM decides how to use AI to build what has already been specified.

**MagicLLM does not own the output.** Code, design documents, and test artifacts produced via MagicLLM belong to the Work Contract, which traces to the Goal. The MagicLLM Decision Record is evidence of the process — not the process itself.

---

## 2. Constitutional Position

MagicLLM is owned by **AI Architect (INST-008)**. Per ORGANIZATION.md Office 08:

| Attribute | Value |
|---|---|
| Decision Space | AI architecture · LLM integration strategy · model selection criteria · Decision Space execution model |
| What MagicLLM MAY do | Select models · Build contexts · Parameterize invocations · Evaluate responses · Classify retry strategies · Record decisions |
| What MagicLLM MAY NOT do | Redefine Decision Spaces (constitutional objects) · Grant AI components authority beyond their licensed scope · Circumvent human override mechanisms |
| Constitutional basis | C-073 · C-059 · C-069 · ADR-029 · ADR-030 |

MagicLLM is **invoked by** Runtime Implementation Professional (INST-010) in EEM Step 08. It is **owned by** AI Architect (INST-008). The invocation relationship does not transfer ownership: INST-010 cannot modify MagicLLM's decision logic. Only AI Architect (INST-008) may propose changes to MagicLLM's architecture.

---

## 3. MagicLLM vs. Provider Selection Engine (ADR-029)

These are two distinct constitutional layers with different Decision Spaces:

| Dimension | PSE (ADR-029) | MagicLLM |
|---|---|---|
| **Governs** | Customer-facing agent LLM calls | Engineering execution LLM calls |
| **Input** | Customer message + tier + language | EEM step context + Engineering Design Record |
| **Context size** | 8k–128k tokens (conversation) | 32k–1M tokens (full specs + codebase) |
| **Output** | Natural language response | Code files · Design artifacts · Test suites · Documents |
| **Quality gate** | C-049 (customer satisfaction) | Compile gate · Spec alignment · CCT pass |
| **Retry intelligence** | Provider fallback | Error classification + targeted correction |
| **Performance data** | `institutional.pse_provider_ranking` | `institutional.magic_llm_performance` (new) |
| **Constitutional basis** | C-051 · C-042 · C-069 | C-059 · C-073 · C-069 |

MagicLLM is not a replacement for PSE. They govern different execution contexts and must not be merged.

---

## 4. Architecture

```
Engineering Design Record (Step 07)
Work Contract (Step 06)
EEM Step Context (current step number)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                   TASK CLASSIFIER                       │
│  Classifies the engineering task into one of 6          │
│  categories based on EEM step + Work Contract task type │
└──────────────────────────┬──────────────────────────────┘
                           │ Task Category
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   MODEL SELECTOR                        │
│  Selects optimal model applying:                        │
│  Layer A: Constitutional rules (DPDPA, cost, tier)      │
│  Layer B: Performance score (success rate, latency)     │
│  Produces: Model Selection Record                       │
└──────────────────────────┬──────────────────────────────┘
                           │ Selected Model
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   CONTEXT BUILDER                       │
│  Assembles the optimal context for the selected model:  │
│  - Spec section loading (from Engineering Design Record)│
│  - Platform Type Registry injection (for code tasks)    │
│  - Semantic chunking (for large context models)         │
│  - Prior task output injection (C-085 idempotency)      │
└──────────────────────────┬──────────────────────────────┘
                           │ Assembled Context
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 EXECUTION CONTRACT                      │
│  Parameterized invocation specification:                │
│  - Model + version                                      │
│  - Temperature (0=deterministic, 0.3=design tasks)      │
│  - Max tokens (task-category budget)                    │
│  - Tool definitions (MCP tools if applicable)           │
│  - Expected output format (XML file blocks / JSON)      │
└──────────────────────────┬──────────────────────────────┘
                           │ Execution Contract
                           ▼
┌─────────────────────────────────────────────────────────┐
│               AI EXECUTION LAYER                        │
│  Provider API invocation per Execution Contract         │
│  (Google Vertex AI / Anthropic / Azure OpenAI)          │
└──────────────────────────┬──────────────────────────────┘
                           │ Raw Response
                           ▼
┌─────────────────────────────────────────────────────────┐
│                RESPONSE EVALUATOR                       │
│  Constitutional quality gates — in sequence:            │
│  1. Format gate (did the model follow output format?)   │
│  2. Compile gate (for code: does it compile? — C-082)   │
│  3. Spec alignment (C-032: no drift from Design Record) │
│  4. Annotation check (C-073: @constitutional present?)  │
│  5. Schema validation (for structured outputs)          │
│                                                         │
│  Result: ACCEPTED | RETRY_NEEDED | ESCALATE             │
└──────────────────────────┬──────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
      ACCEPTED                        RETRY_NEEDED
          │                                 │
          ▼                                 ▼
┌─────────────────┐              ┌─────────────────────────┐
│ EVIDENCE        │              │    RETRY ADVISOR        │
│ RECORDER        │              │  Classifies failure.    │
│                 │              │  Produces targeted       │
│ Commits         │              │  correction for next     │
│ MagicLLM        │              │  attempt.               │
│ Decision Record │              │  (max 3 attempts then   │
│ to Goal         │              │   ESCALATE to INST-010) │
│ Register        │              └────────────┬────────────┘
└────────┬────────┘                           │
         │                                    │ retry with correction
         ▼                            ────────┘
   EEM Step 08
   Contribution Record
   committed to
   Goal Register
```

---

## 5. Engineering Task Classification

MagicLLM classifies every task into one of six categories before model selection. Classification is based on EEM step number + task keywords from the Work Contract.

| Category | EEM Steps | Task characteristics | Governing model profile |
|---|---|---|---|
| **Deep Reasoning** | 01, 02, 03, 05 | Large context · Deliberate analysis · No code output | Large context + strong reasoning |
| **Code Generation** | 08 | Source code output · Function calling · Compile required | Code-optimized · Deterministic |
| **Design & Contracts** | 06, 07 | Interface contracts · Pseudocode · Structured specs | Structured output · Reasoning |
| **Review & Evaluation** | 04, 10, 14 | Fast · Structured output · Classification task | Fast · Structured JSON |
| **Documentation** | 13 | Writing quality · Fast · Low cost | Fast general model |
| **Test Generation** | 11 | Test code · AAA pattern · Coverage awareness | Code-optimized |

---

## 6. Model Routing by Task Category

MagicLLM's model selection applies two layers in sequence (extending ADR-029's PSE pattern for engineering context):

### Layer A — Constitutional Rules (engineering-specific)

| Rule ID | Condition | Effect |
|---|---|---|
| **ML-R01** | Task contains customer PII AND provider has no India/UAE DPA | DENY provider |
| **ML-R02** | Category = Code Generation OR Test Generation | REQUIRE model with confirmed compile-capable output (structured XML file blocks) |
| **ML-R03** | Category = Deep Reasoning AND context > 200k tokens | REQUIRE model with ≥200k context window |
| **ML-R04** | Monthly engineering LLM spend ≥ C-077 ceiling (₹5,000) | DENY FRONTIER tier for Category = Documentation |
| **ML-R05** | `AUTONOMOUS_HALT = true` | DENY all LLM calls — halt and notify Founder |
| **ML-R06** | Provider API secret expired or unavailable | DENY that provider |
| **ML-R07** | Provider failure rate > 20% in last 30 min | SKIP provider, try next |

### Layer B — Performance Score (from `institutional.magic_llm_performance`)

After rules filter eligible models, rank by composite score:

```
engineering_score = (compile_success_rate × 0.40)
                 + (spec_alignment_score × 0.30)
                 + ((1 - normalised_retry_count) × 0.20)
                 + ((1 - normalised_cost) × 0.10)
```

Where `compile_success_rate` = tasks where model output compiled on first attempt / total tasks of this category, measured in rolling 48-hour window.

### Model Registry for Engineering

| Category | Primary | Fallback | Never (DPDPA gap) |
|---|---|---|---|
| Deep Reasoning | Gemini 2.5 Pro (Vertex, asia-south1) | Claude Sonnet (Anthropic direct — see DPDPA note) | GPT-4o direct · Grok |
| Code Generation | Claude Sonnet 4.6 (ADR-030 standard) | Gemini 2.5 Pro (Vertex, asia-south1) | GPT-4o direct |
| Design & Contracts | Claude Sonnet 4.6 | Gemini 2.5 Pro | — |
| Review & Evaluation | Gemini 2.0 Flash (Vertex, asia-south1) | Claude Haiku | — |
| Documentation | Gemini 2.0 Flash | Gemini Flash Lite | — |
| Test Generation | Claude Sonnet 4.6 | Gemini 2.5 Pro | — |

**DPDPA Note:** Claude Sonnet 4.6 (Anthropic API) routes to Anthropic's US infrastructure. This is the current ADR-030 standard for code generation. While engineering data (specs, code) is WAOOAW IP (not customer data), the platform's strongest compliance posture keeps all data within India. A future ADR should evaluate Anthropic models via AWS Bedrock (Mumbai region) or a DPDPA-compliant Anthropic endpoint when available. Until then, Anthropic API is permitted for engineering execution under the existing ADR-030 basis.

---

## 7. Context Management Strategy

Context quality is the primary determinant of code generation correctness. MagicLLM's Context Builder applies these strategies by task category.

**Constitutional basis:** C-032 (spec-code alignment), C-085 (idempotency — no assumption about prior state), C-059 (traceability). **Deviation from §7.1 ordered assembly is a constitutional violation.**

### 7.1 Ordered Context Assembly (MANDATORY — constitutional enforcement)

For Code Generation and Test Generation, context MUST be assembled in this exact order:

```
1. [SYSTEM]      Constitutional obligations + C-059 annotation rules + forbidden patterns
2. [PREAMBLE]    File Preamble Contract (§7.5) — mandatory first lines of the output file
3. [FROZEN]      Frozen Artifact Signatures (§7.6) — compiled constructor/interface signatures
4. [PTR]         Platform Type Registry — auto-populated from filesystem at call time (§7.2)
5. [USING_MAP]   Namespace index — class → using directive mapping, auto-populated (§7.3)
6. [SPEC]        Exact spec sections from Work Contract spec_sections field only
7. [PRIOR]       Prior Task Compiled Output — public API signatures from prior task (§7.4)
8. [TASK]        Exact task description + acceptance criteria + output file list
9. [FORMAT]      Output format: XML file blocks with mandatory preamble header
```

Any context section exceeding 4,000 characters MUST be truncated at a structural boundary. Never truncate mid-line or mid-method.

### 7.2 Platform Type Registry — Auto-Population (Gap 1 fix)

PTR is NOT caller-supplied. MagicLLM auto-populates from the filesystem at invocation time:

```python
scope = ["src/", "tests/"]  # always both — test types are dependencies
ptr = assembler.assemble(scope=scope)         # scans current sprint branch state
using_map = assembler.build_using_map()       # auto-builds namespace index
relevant = assembler.extract_task_ptr(ptr, spec_sections, stack=stack)
```

Relevance: extract types whose PascalCase names appear in the task description or spec sections. Fallback: all types in the stack. Maximum 30 types. **A caller MUST NOT pass a stale PTR snapshot.**

### 7.3 USING_MAP — Namespace Index (Gap 5 + 6 fix)

USING_MAP maps every public class/interface/enum/record name to its `using` directive. Auto-built from filesystem at invocation time. Injected as a structured block before spec sections:

```
USING_MAP — every type you reference requires its using directive:
  FakeServerCallContext → using Waooaw.ConstitutionalEngine.Tests.Evaluators;
  ConstitutionalEngineService → using Waooaw.ConstitutionalEngine.Services;
  EvaluationContext → using Waooaw.ConstitutionalEngine.Evaluators;
```

USING_MAP is structural, not advisory. Missing a using directive for a USING_MAP type is a format failure.

### 7.4 Prior Task Compiled Output Injection (Gap 2 fix)

For sequential subtask chains (e.g. WC012-02b → WC012-02c), MagicLLM MUST inject the compiled public API surface of the immediately preceding subtask's output files.

**Algorithm:**
1. For each file in `depends_on` prior tasks: read the file from the sprint branch (not main)
2. Extract: all `public` constructor signatures (full parameter list with types+names), all `public` method signatures, all `public` property declarations, namespace
3. Format as COMPILED SIGNATURES block and inject at [FROZEN] position
4. If prior file does not exist: log warning, skip — do NOT fabricate signatures

**Critical:** Constructor parameter names and order are injected verbatim. The LLM MUST use the exact constructor signature when writing test instantiation code. This eliminates CS1503/CS1744/CS1729.

### 7.5 File Preamble Contract (Gap 6 fix — NEW)

Every output file produced by MagicLLM MUST begin with a preamble pre-generated by the Context Builder, NOT by the LLM. The LLM extends the file after the preamble. It MUST NOT alter the preamble.

**C# preamble (auto-generated from USING_MAP + spec metadata):**
```
// Implements: {spec_file} {spec_section}
// constitutional_basis: {constitutional_claims}
using {all_usings_from_using_map_relevant_to_this_file};
```

**Python preamble:**
```
# Implements: {spec_file} {spec_section}
# constitutional_basis: {constitutional_claims}
from __future__ import annotations
```

The LLM instruction: "The first N lines are already written. Extend from line N+1. Never modify the preamble."

### 7.6 Frozen Artifact Registry (Gap 8 fix — NEW)

Once a file passes the compile gate, its public API surface is frozen. The Context Builder maintains a Frozen Artifact Registry at `sprint-context/frozen-artifacts.json`.

**Timing (Gap 1 fix):** The Frozen Artifact Registry is written by `task_decomposer.execute_subtask_chain()` immediately after each compile gate PASS, not by the LLM and not by the caller. The call sequence is:
1. Subtask compile gate runs → returns PASS
2. `task_decomposer` calls `context_builder.freeze_artifacts_from_task(output_files, task_id)`
3. Frozen registry updated on disk at `sprint-context/frozen-artifacts.json`
4. Next subtask's Context Builder reads registry and injects [FROZEN] block

**Deterministic tasks (Gap 2 fix):** Deterministic SubTaskDef instances MUST declare `output_files` for their generated files. Without `output_files`, the Context Builder cannot freeze their signatures. Every deterministic task that produces .cs files must list them explicitly (e.g. WC012-02a must list EvaluationResult.cs, EvaluationContext.cs, IClaimEvaluator.cs, EvaluatorRegistry.cs).

```json
{
  "src/constitutional-engine/Services/ConstitutionalEngineService.cs": {
    "frozen_at_task": "WC012-02b",
    "namespace": "Waooaw.ConstitutionalEngine.Services",
    "public_constructors": ["ConstitutionalEngineService(ConstitutionalDbContext db, EmergencyStopDbContext emergencyDb, ITemporalClient? temporalClient, EvaluatorRegistry registry, ILogger<ConstitutionalEngineService> logger)"],
    "public_methods": ["RecordEvidence(RecordEvidenceRequest, ServerCallContext)", "ValidateAction(ValidateActionRequest, ServerCallContext)"]
  }
}
```

Any subsequent task that references a frozen file receives its exact signatures. The LLM may not invent alternative signatures for a frozen artifact. Violation = compile failure that is non-retriable.

### 7.7 Semantic Chunking for Large Context (Phase 2 only)

For Deep Reasoning tasks requiring repository-scale context (EEM Step 02): semantic chunking based on structural boundaries + embedding similarity. Maximum 1M tokens (Gemini 2.5 Pro). **Not applicable to Code Generation or Test Generation tasks.**

---

## 8. Response Evaluator — Quality Gates

Every LLM response passes through five gates in sequence. Any gate failure produces a classified failure record for the Retry Advisor. **Gates 2–5 were not implemented in Phase 1 — this is a constitutional violation corrected by this amendment.**

| Gate | Applies to | Pass condition | Failure classification |
|---|---|---|---|
| **Format Gate** | All | Response contains expected output structure (XML file blocks for code, valid JSON for structured outputs) | `FORMAT_FAILURE` |
| **Compile Gate** | Code Generation · Test Generation | Stack-specific (ADR-038): Python = `py_compile` + `ruff check`; .NET = `dotnet build`; TypeScript = `tsc --noEmit` + `biome ci`; SQL = `sqlfluff lint`; YAML = `yamllint`; Terraform = `hcl2.load()` — all must exit 0 | `COMPILE_FAILURE: [error_code]` |
| **Spec Alignment Gate** | Code Generation · Design | `check_spec_against_ptr()` finds no drift between spec requirements and produced code types (C-032) | `SPEC_DRIFT: [gap_description]` |
| **Annotation Gate** | Code Generation | Every constitutional function carries `@constitutional` annotation + `# Implements:` header (C-073) | `ANNOTATION_MISSING: [file_path]` |
| **Schema Gate** | Structured outputs (Design, Review) | Output JSON satisfies the Execution Contract's schema | `SCHEMA_VIOLATION: [field_name]` |

A response that passes all applicable gates is ACCEPTED. A response that fails any gate is passed to the Retry Advisor.

---

## 9. Retry Advisor (Gap 4 fix — unified, not disconnected)

The Retry Advisor is the SAME component as `scripts/sprint_retry_advisor.py`. MagicLLM does not maintain a separate retry logic. The existing 17-family error classifier IS the MagicLLM Retry Advisor. This is the constitutional connection.

**Retry loop algorithm (Gap 7 fix):**

```
Attempt 1:
  Context Builder assembles context (§7.1 ordered assembly)
  LLM generates output
  Response Evaluator runs 5 gates (§8)
  IF all gates PASS → ACCEPTED, return response

  IF gate fails:
    Retry Advisor classifies failure (sprint_retry_advisor.diagnose_build_error())
    Advisor produces: {error_family, fix_instruction, confidence, should_retry}    For ruff violations: _classify_ruff_violation() fires BEFORE CS-code scan,
    returns a COMBINED fix instruction covering ALL ruff violations in the output
    (not just the first — prevents retry exhaustion on multi-violation files).
    IF confidence < 30% OR should_retry=False:
      STOP_LOSS: skip remaining attempts, emit BUILD_FAILURE (not spec-gap)

    ELSE:
      Rebuild context with TARGETED CORRECTION:
        - Re-inject PTR with corrected type (if CS1061/CS0246)
        - Re-inject frozen signatures (if CS1503/CS1744/CS1729)
        - Re-inject File Preamble Contract (if ANNOTATION_MISSING)
        - Append: "Previous attempt failed. Fix instruction: {fix_instruction}"

Attempt 2: same as attempt 1 with updated context

Attempt 3: same

After 3 failures (all with diagnosable error classes):
  → Emit BUILD_FAILURE (not spec-gap) — LLM generation miss, not specification gap
  → Next cron run retries with same context + learning cache consulted first

After 3 failures (with UNKNOWN at stop-loss):
  → Auto-extend advisor (scripts/advisor_auto_extend.py) — generate handler for new code
  → Commit handler to main — next run uses it
  → Emit SPEC_GAP only if auto-extend fails AND failure recurs 3+ times across runs
```

**Error family table (implemented in sprint_retry_advisor.py):**

| Failure classification | Error codes | Targeted correction |
|---|---|---|
| SIGNATURE_DRIFT | CS7036, CS1501, CS1503, CS1729, CS1744 | Inject frozen constructor signatures; use all-positional args |
| NULLABILITY_MISMATCH | CS0266, CS0037, CS8629, CS8600, CS8602, CS8604, CS8618 | Inject nullable handling pattern; use GetValueOrDefault |
| SYMBOL_RESOLUTION | CS0246, CS0103, CS0117, CS1061 | Re-inject USING_MAP + PTR; list exact available members |
| INTERFACE_CONTRACT | CS0539, CS0505, CS0115, CS0738, CS1024 | Inject interface/base class signature verbatim |
| ASYNC_FLOW | CS1998, CS4014 | Re-inject async/await rules |
| REFERENCE_CONFIG | NU*, MSB* | Package/project reference fix; do not retry code generation |
| FORMAT_FAILURE | No error code | Re-inject XML format template |
| ANNOTATION_MISSING | — | Re-inject File Preamble Contract (§7.5) |

**Retry limit:** 3 attempts. After exhaustion: BUILD_FAILURE (retriable next cron run). SPEC_GAP issued only when failure recurs 3+ runs AND auto-extend cannot generate a handler.

---

## 9b. MagicLLM Fallback Behavior (Gap 10 fix — NEW)

When MagicLLM is unavailable (import error, no API key, infrastructure failure):

| Condition | Permitted fallback | Evidence required |
|---|---|---|
| API key missing | Call `call_llm()` directly | Log warning: "MagicLLM fallback — no API key. MDR not produced." |
| MagicLLM import error | Call `call_llm()` directly | Log warning with import error detail |
| Infrastructure timeout | Raise RuntimeError to outer retry loop | No fallback — let retry advisor handle |
| MagicLLM returns ESCALATE | Call `call_llm()` directly with same context | Log: "MagicLLM escalated — falling back for this attempt" |

**Constitutional constraint:** Fallback is PERMITTED for at most 3 consecutive invocations. If 3 consecutive fallbacks occur, MagicLLM must halt and notify via Sprint Dashboard (C-001: Human Override). Silent indefinite fallback is a C-059 violation (no Decision Record = no evidence).

---

## 10. Evidence — MagicLLM Decision Record

Every MagicLLM invocation produces a Decision Record committed to the Goal Register before the Step 08 Contribution Record is committed. This record is the constitutional basis for reproducibility.

```
institution_id:          INST-008 (AI Architect — MagicLLM owner)
invoked_by:              INST-010 (Runtime Implementation Professional)
goal_id:                 GOAL-NNN
record_id:               MDR-GOAL-NNN-INST-010-NNN
record_type:             MagicLLM Decision Record
task_category:           [Deep Reasoning | Code Generation | Design | Review | Documentation | Test]
model_provider:          [e.g., Anthropic API — Claude Sonnet 4.6]
model_version:           [exact version string]
temperature:             [value used]
token_allocation:        [input_tokens / output_tokens]
context_strategy:        [e.g., PTR injection + spec sections 3.1, 3.2 + prior task WC012-01]
tools_invoked:           [list of MCP tools called, or none]
gates_evaluated:         [format: PASS | compile: PASS | spec_alignment: PASS | annotation: PASS]
retry_count:             [0 = first-attempt success]
retry_classifications:   [list of failure classifications if retry_count > 0]
performance_score_used:  [composite score that selected this model over alternatives]
cost_incurred_inr:       [estimated cost for this invocation in INR]
produced_at:             [timestamp]
```

---

## 11. Cost and Performance Governance

### Cost Governance (C-077)
Engineering LLM costs are governed by C-077 (Dev Tooling Cost Ceiling: ₹5,000/month). MagicLLM enforces this ceiling:

1. Each MagicLLM Decision Record records `cost_incurred_inr`
2. These are aggregated in `institutional.magic_llm_performance` table
3. When monthly spend approaches 80% of ceiling: Gemini Flash is substituted for Gemini 2.0 Flash for Documentation and Review categories
4. When monthly spend approaches 95% of ceiling: all non-Code-Generation tasks use LOCAL tier models only; Code Generation continues (blocking the sprint is more expensive than the cost)
5. If ceiling is breached: MagicLLM halts all FRONTIER-tier calls and notifies Founder via Sprint Dashboard

### Performance Governance (C-069)
MagicLLM is not static. It improves based on evidence:

1. Every MagicLLM Decision Record feeds into `institutional.magic_llm_performance`
2. The performance composite score (§6 Layer B) updates the Model Registry's ranked list every 24 hours
3. A model that drops below 60% compile success rate for a category is demoted to fallback for that category
4. AI Architect (INST-008) reviews the performance table weekly and may propose model routing changes via a Work Contract

---

## 12. DPDPA Compliance

Engineering data (source code, architecture documents, specifications) is WAOOAW IP. The strongest compliance posture keeps all engineering data within India.

| Provider | Data residency | DPDPA posture | Status for engineering |
|---|---|---|---|
| Google Vertex AI `asia-south1` | India (Mumbai) | Strongest — data never leaves India | **PRIMARY for Deep Reasoning, Review, Documentation** |
| Anthropic API (direct) | US | DPA exists but data leaves India | **Permitted for Code Generation under ADR-030 basis — future ADR pending** |
| Azure OpenAI UAE North | UAE | Microsoft DPA — acceptable fallback | Fallback only |

Future ADR-033 (when available): evaluate Anthropic models via AWS Bedrock `ap-south-1` (Mumbai) or equivalent India-resident endpoint to achieve strongest DPDPA posture for Code Generation.

---

## 13. Implementation Roadmap

### Phase 1 — Minimum Viable MagicLLM (next sprint after GOAL-001)
**Scope:** Formalize and instrument what already exists in `scripts/autonomous_sprint_runner.py`

- Task Classifier: rule-based on EEM step number + `model_hint` field
- Model Selector: extends ADR-030 routing with task category awareness
- Context Builder: formalizes existing PTR injection + spec section loading
- Evidence Recorder: produces MagicLLM Decision Record (EEM Step 08 format)
- Performance Table: `institutional.magic_llm_performance` schema + seeding

**Gate:** All existing 243+ tests pass. MagicLLM Decision Records appear in Goal Register for WC-013+ tasks.

### Phase 2 — Repository-Aware MagicLLM
**Scope:** Full semantic context management for large repository tasks

- Semantic chunking engine for Deep Reasoning tasks (Steps 01-05)
- Repository embedding index (updated on every PR merge)
- Context relevance scoring (embedding similarity + structural boundary detection)
- Multi-call context continuation for tasks that exceed single-call token budgets
- Layer B performance score with full composite metric tracking

**Gate:** Semantic Impact Discovery (EEM Step 02) uses MagicLLM for context assembly. No manual spec section curation required.

### Phase 3 — Multi-Model Orchestration
**Scope:** Specialized models collaborating within a single EEM step

- Parallel code generation for independent components within one Step 08
- Self-critique loop: model A generates, model B reviews against spec, model A revises
- Evaluation Engine with automated scoring against Engineering Design Record
- Automated benchmark comparison against previous sprint performance
- Constitutional compliance scoring (% of @constitutional annotations, traceability coverage)

**Gate:** Grade A acceptance scenario results on all four customer agents using Phase 3 MagicLLM. Zero constitutional compliance regressions vs. Phase 2.

---

## 14. Constitutional Constraints on MagicLLM

| Constraint | Source | Effect |
|---|---|---|
| MagicLLM does not define Decision Spaces | C-ECI-001 (Decision Space as Constitutional Primitive) | Model selection criteria may not reference Decision Space definitions — it reads them as inputs only |
| All decisions are evidence | C-059 | Every invocation produces a MagicLLM Decision Record before results are used |
| Human override always reachable | C-001 | `AUTONOMOUS_HALT = true` stops all MagicLLM invocations immediately and unconditionally |
| No authority beyond Decision Space | Constitution Article III | MagicLLM may not invoke MCP tools that are not in the authorized tool list for the current Work Contract |
| Cost ceiling is a constitutional floor | C-077 | MagicLLM cost governance is not optional — it is constitutionally enforced |
| Self-improvement is mandatory | C-069 | MagicLLM must update its performance model from evidence — static routing violates C-069 |
| Context assembly order is mandatory | C-032 | §7.1 ordered context assembly is not optional — prose instructions as substitutes for structured facts is a spec violation |
| Frozen artifacts are immutable | C-085 | Once a file's public API passes a compile gate, its signatures may not be changed by downstream tasks |
| File preamble is pre-written | C-073 | The `// Implements:` header and using directives are generated by Context Builder, not by the LLM |
| Fallback is time-bounded | C-059 | Maximum 3 consecutive fallback invocations without a Decision Record before human notification |
| Spec-gap is the last resort | C-065 | A diagnosable build failure (known error family) is NOT a spec gap — it is a generation miss, retriable next run |

---

*Produced by AI Architect (INST-008) — GOAL-001 Phase 3*
*Ratified 2026-07-28 — governing from this date. Ten constitutional violations corrected.*
*All WAOOAW code generation via MagicLLM is bound by this document from ratification date.*
