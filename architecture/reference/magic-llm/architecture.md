# MagicLLM — Engineering AI Execution Layer

**Classification:** Reference Architecture
**Status:** Proposed — Awaiting Solution Architect review + Founder acknowledgement
**Produced by:** AI Architect (INST-008) — GOAL-001 Phase 3 (2026-07-27)
**Constitutional Basis:** C-069 (Platform Self-Improvement) · C-059 (Traceability) · C-073 (@constitutional annotations) · ORGANIZATION.md Office 08 (AI Architect Decision Space)
**Goal Reference:** GOAL-001 — Semantic Brain Transformation
**ADR Reference:** ADR-032 (MagicLLM Architecture Decision)
**Depends on:** EEM (architecture/reference/engineering-execution-model.md) · ADR-029 (Multi-Provider LLM) · ADR-030 (Code Generation)

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

Context quality is the primary determinant of code generation correctness. MagicLLM's Context Builder applies these strategies by task category:

### 7.1 Spec Section Loading
For all engineering tasks: load only the spec sections directly relevant to the task from the Work Contract's `spec_sections` field. Do not load the entire architecture document. Context contamination degrades output quality.

### 7.2 Platform Type Registry Injection
For Code Generation and Test Generation: inject the current compiled types from the Platform Type Registry (PTR) before the spec sections. The PTR prevents CS1061 (missing property) and CS0246 (missing type) errors by grounding the model in the actual compiled state of the codebase.

```
Context assembly order for Code Generation:
1. [System] Constitutional obligations + C-059 annotation rules
2. [PTR] Current compiled types relevant to this task
3. [Spec] Exact spec sections for this task (from Work Contract)
4. [Prior] Prior task outputs that this task depends on (GEOM phase ordering)
5. [Task] Exact task description + acceptance criteria
6. [Format] Output format instruction (XML file blocks)
```

### 7.3 Semantic Chunking for Large Context
For Deep Reasoning tasks requiring repository-scale context (Semantic Impact Discovery — EEM Step 02): use semantic chunking to load the most relevant repository sections within the model's context window. Chunking is based on structural boundaries (file-level) + semantic relevance (embedding similarity to task description).

Maximum context: 1M tokens (Gemini 2.5 Pro). When exceeded: load repository index + top-N most relevant files.

### 7.4 Prior Task Output Injection
For sequential task phases: inject the compilation output and type definitions from Phase N-1 before generating Phase N code. This is the constitutional enforcement of C-085 (Idempotency) — each phase builds on verified prior output, not assumptions.

---

## 8. Response Evaluator — Quality Gates

Every LLM response passes through five gates in sequence. Any gate failure produces a classified failure record for the Retry Advisor.

| Gate | Applies to | Pass condition | Failure classification |
|---|---|---|---|
| **Format Gate** | All | Response contains expected output structure (XML file blocks for code, valid JSON for structured outputs) | `FORMAT_FAILURE` |
| **Compile Gate** | Code Generation · Test Generation | `dotnet build` or `python -m py_compile` or `tsc --noEmit` exits 0 | `COMPILE_FAILURE: [error_code]` |
| **Spec Alignment Gate** | Code Generation · Design | `check_spec_against_ptr()` finds no drift between spec requirements and produced code types (C-032) | `SPEC_DRIFT: [gap_description]` |
| **Annotation Gate** | Code Generation | Every constitutional function carries `@constitutional` annotation + `# Implements:` header (C-073) | `ANNOTATION_MISSING: [file_path]` |
| **Schema Gate** | Structured outputs (Design, Review) | Output JSON satisfies the Execution Contract's schema | `SCHEMA_VIOLATION: [field_name]` |

A response that passes all applicable gates is ACCEPTED. A response that fails any gate is passed to the Retry Advisor.

---

## 9. Retry Advisor

The Retry Advisor classifies failures and produces targeted corrections for the next attempt. Targeted corrections outperform generic retry because they modify the exact context element that caused the failure.

| Failure classification | Root cause | Targeted correction |
|---|---|---|
| `COMPILE_FAILURE: CS1061` | Model referenced a property that does not exist on the type | Inject PTR entry for the exact type; explicitly list available properties; ban `TryGetValue()` for this type |
| `COMPILE_FAILURE: CS0246` | Model referenced a type that is not imported | Add missing type to PTR injection; add `using` statement to context |
| `COMPILE_FAILURE: CS0505` | Model overrode a non-virtual method | Inject base class signature; specify `override` vs `new` requirement |
| `SPEC_DRIFT` | Model invented fields/methods not in spec | Re-inject spec section; explicitly list what is and is not in scope |
| `FORMAT_FAILURE` | Model did not follow XML file block format | Re-inject format instruction; provide example of correctly formatted output |
| `ANNOTATION_MISSING` | Constitutional traceability header absent | Re-inject C-059/C-073 rules; provide header template as first line of system prompt |
| `SCHEMA_VIOLATION` | Structured output JSON malformed | Re-inject schema; provide correct example |

**Retry limit:** 3 attempts per task. After 3 failures:
1. MagicLLM escalates to Runtime Implementation Professional (INST-010) with the full failure record
2. INST-010 raises a Capability Gap Record to the Goal Orchestrator
3. Goal is paused pending INST-008 (AI Architect) review of the failure pattern
4. If the failure pattern reveals a systematic gap in the model's capability for this task category, AI Architect initiates Stage W-5 (Goal-Driven Evolution) for MagicLLM

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

---

*Produced by AI Architect (INST-008) — GOAL-001 Phase 3*
*For Solution Architect review (INST-005) and Founder acknowledgement.*
*Pending review, this is a proposed reference architecture document — not yet governing.*
