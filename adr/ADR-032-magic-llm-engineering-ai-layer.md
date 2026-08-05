# ADR-032 — MagicLLM Engineering AI Execution Layer Architecture

**Status:** Proposed
**Date:** 2026-07-27
**Produced by:** AI Architect (INST-008) — GOAL-001 Phase 3
**Deciders:** AI Architect (INST-008) · Enterprise Architect (INST-004) · Founder (Yogesh Khandge)
**Constitutional Basis:** C-069 (Platform Self-Improvement) · C-059 (Traceability) · C-073 (@constitutional annotations) · C-077 (Dev Tooling Cost Ceiling)
**Supersedes:** ADR-030 §Model Routing (extends — does not replace)
**Related:** ADR-029 (Multi-Provider LLM — governs customer-facing PSE) · ADR-030 (Code Generation Protocol)
**Goal Reference:** GOAL-001 Phase 3

---

## Context

ADR-030 defines the autonomous sprint code generation protocol with a fixed model routing table (`model_hint: reasoning` → Claude Sonnet 4.6, `model_hint: auto` → Claude Haiku, `model_hint: none` → no LLM). This was sufficient for Sprint 011–012, where all tasks were code generation of a similar character.

GOAL-001 transforms the platform into a Semantic Brain that accepts natural-language Goals and executes them through the 16-step Engineering Execution Model (EEM). The EEM has six distinct engineering task categories, each with materially different AI requirements:

| Category | Context size | Primary output | Key quality gate |
|---|---|---|---|
| Deep Reasoning (Steps 01-05) | 32k–1M tokens | Analysis documents | Semantic correctness |
| Code Generation (Step 08) | 32k–128k tokens | Source code | Compile gate |
| Design & Contracts (Steps 06-07) | 16k–64k tokens | Interface contracts | Schema validation |
| Review & Evaluation (Steps 04, 10) | 32k–128k tokens | Structured assessment | Classification accuracy |
| Documentation (Step 13) | 8k–32k tokens | Markdown/prose | Writing quality |
| Test Generation (Step 11) | 16k–64k tokens | Test code | CCT pass + coverage |

A single-model routing table (ADR-030) cannot optimally serve all six categories. A constitutional intelligence layer is needed that:
1. Classifies the engineering task category
2. Selects the optimal model for that category
3. Assembles the optimal context
4. Evaluates responses against quality gates
5. Classifies failures for targeted retry
6. Records every decision as constitutional evidence

This layer is MagicLLM.

---

## Decision

### Decision 1: Architecture Pattern — Specialized Models with Dynamic Routing (Option D+B Hybrid)

**Rejected:** Option A (always one model) — does not serve the diversity of EEM task categories.
**Rejected:** Option C (multiple models collaborating simultaneously) — latency and cost exceed C-077 ceiling for most tasks; appropriate only for Phase 3 MagicLLM.
**Chosen:** Option D (specialized models per task category) with Option B (dynamic routing within each category based on performance data).

**Rationale:** WAOOAW already has a proven two-layer model selection pattern (ADR-029: rule engine + performance score). MagicLLM extends this pattern to the engineering execution context, adding task category classification as the outer routing dimension.

### Decision 2: Eight-Component Architecture

MagicLLM consists of eight constitutional components in a linear pipeline:

```
Task Classifier → Model Selector → Context Builder → Execution Contract
→ AI Execution Layer → Response Evaluator → [Retry Advisor] → Evidence Recorder
```

Each component has a defined input, output, and constitutional evidence obligation. No component may be skipped.

### Decision 3: Evidence-First Execution

Every MagicLLM invocation produces a MagicLLM Decision Record committed to the Goal Register **before** the results are used. This is the constitutional enforcement of C-059 for AI execution. An LLM invocation without a preceding Decision Record is constitutionally unauthorized.

Decision Record fields: task_category · model_provider · model_version · temperature · token_allocation · context_strategy · gates_evaluated · retry_count · retry_classifications · performance_score_used · cost_incurred_inr.

### Decision 4: Provider Registry for Engineering

Primary provider strategy (DPDPA-primary, extending ADR-029):

| Task Category | Primary | Fallback | DPDPA posture |
|---|---|---|---|
| Deep Reasoning | Gemini 2.5 Pro (Vertex asia-south1) | Claude Sonnet 4.6 | Strongest (India-resident primary) |
| Code Generation | Claude Sonnet 4.6 (ADR-030 standard) | Gemini 2.5 Pro (Vertex asia-south1) | Permitted (ADR-030 basis) |
| Design & Contracts | Claude Sonnet 4.6 | Gemini 2.5 Pro | Permitted |
| Review & Evaluation | Gemini 2.0 Flash (Vertex asia-south1) | Claude Haiku | Strongest |
| Documentation | Gemini 2.0 Flash (Vertex asia-south1) | Gemini Flash Lite | Strongest |
| Test Generation | Claude Sonnet 4.6 | Gemini 2.5 Pro | Permitted |

**DPDPA caveat for Code Generation:** Claude Sonnet (Anthropic API direct) routes to US infrastructure. This is the existing ADR-030 standard for code generation, carried forward here. A future ADR-033 will address this when a DPDPA-compliant Anthropic endpoint in India becomes available.

### Decision 5: Performance-Based Model Improvement (C-069)

MagicLLM performance data is stored in `institutional.magic_llm_performance`. The composite score weights for engineering execution:

```
engineering_score = (compile_success_rate × 0.40)
                 + (spec_alignment_score  × 0.30)
                 + ((1 - retry_rate)       × 0.20)
                 + ((1 - cost_rate)        × 0.10)
```

Model routing is updated every 24 hours from this table. A model below 60% compile success rate for a category is automatically demoted to fallback. This satisfies C-069 without requiring Founder per-change approval.

### Decision 6: Cost Governance under C-077

Engineering LLM costs are governed by C-077 (₹5,000/month). Enforcement tiers:
- 80% ceiling reached → Gemini Flash substituted for Documentation and Review categories
- 95% ceiling reached → non-Code-Generation tasks use LOCAL tier only
- Ceiling breached → FRONTIER tier halted; Founder notified via Sprint Dashboard

Code Generation continues at all cost levels because blocking the sprint is more expensive than the overage.

### Decision 7: Phased Implementation

Phase 1 (next sprint): Formalize and instrument existing `scripts/autonomous_sprint_runner.py` patterns as MagicLLM pipeline. Add task classification, MagicLLM Decision Record, and performance table.

Phase 2 (subsequent sprint): Repository-aware context management (semantic chunking, embedding index, multi-call continuation). **Includes 7th task category: Semantic Understanding (T-02 resolution).**

Phase 3 (future): Multi-model orchestration, self-critique loop, automated benchmark comparison.

---

### Amendment A002 — Operating Principles Formalization + Test Generation Output Budget

**Triggered by:** WC-028 sprint analysis — recurring test generation failures (2026-08-05)
**Root cause:** O-01/O-02/O-03 existed only as pipeline.py code comments. `groom_sprint.py` bypassed O-01 by forcing `DEEP_REASONING` for all test tasks, which short-circuits the complexity-scoring path in `_select_model`. With `max_tokens=8000` and `thinking_budget=8000`, only 8000 output tokens remained for a test file that routinely exceeds 500 lines (~5000 tokens). Truncation and generic Python mistakes (incorrect datetime serialization, unawaited AsyncMock) were the direct result.

#### Decision 8: Operating Principles (formally ratified)

| Principle | Rule | Enforcement |
|---|---|---|
| **O-01** | Task complexity score (0–100) determines model tier. Score ≥ 80 → Sonnet + thinking. Score 40–79 → Haiku, no thinking. Score < 40 → Haiku, no thinking. `DEEP_REASONING` category BYPASSES complexity scoring and always routes to Sonnet — this is an explicit override, not a bug. | `_task_complexity_score()` + `_select_model()` in `pipeline.py` |
| **O-02** | Cached input tokens cost 1/10th. Repeated context sections across retries are eligible for caching. | Anthropic API cache header; cost estimate uses `CACHE_INPUT_COST_PER_TOKEN`. |
| **O-03** | Dynamic thinking budget: complexity ≥ 80 → `thinking_budget=8000`; 40–79 → `3000`; < 40 → `0`. `thinking_budget` is added to `max_tokens` to form `effective_max` sent to the Anthropic API. | `_thinking_budget()` in `pipeline.py`; `_call_anthropic_api()` |

#### Decision 9: Test Generation Output Budget

Test tasks (all `output_files` under `tests/`) SHALL use:

| Field | Value | Rationale |
|---|---|---|
| `model_hint` | `"auto"` | Extended thinking (DEEP_REASONING) adds 8000 thinking tokens consumed BEFORE output. Test code has no design decisions to reason about — thinking tokens are wasted. Complexity scoring (O-01) routes correctly without override. |
| `max_tokens` | `12000` | Test files routinely exceed 500 lines. 12000 output tokens covers a 1000-line test file with margin. |
| `task_category` | `TEST_GENERATION` (not `DEEP_REASONING`) | Routed via O-01 complexity scoring so model tier adapts to context complexity. |
| Groomer override | PROHIBITED | `groom_sprint.py` SHALL NOT override `model_hint` to `"reasoning"` for test tasks regardless of WC column value. |
| Executor backstop | REQUIRED | `goal_executor.py` SHALL clamp any output file matching `test_*.py` to `max_tokens=12000, model_hint="auto"` regardless of SubTaskDef. This prevents groomer bugs from reaching the executor. |

**CCT requirement:** `tests/pipeline/test_task_decomposer.py` SHALL contain a test asserting that `_generate_scaffold_subtaskdef(is_test=True, ...)` produces `model_hint="auto"` and `max_tokens=12000` regardless of WC column value. `goal_executor.py` SHALL be similarly tested.

---

### Amendment A001 — Semantic Understanding Task Category (Phase 2)

**Triggered by:** RepoNav AVD onboarding — Tension T-02 (2026-07-27)

The original 6 task categories do not cover the core AI execution requirement of knowledge-deriving agents (such as RepoNav). A 7th category is required:

| Field | Value |
|---|---|
| **Category** | Semantic Understanding |
| **EEM Steps** | 02 (Semantic Impact Discovery) + customer-facing: Goal Understanding, Semantic Twin Construction |
| **Task characteristics** | Very large context (up to 1M tokens) · Knowledge graph output · Structural analysis · No code generation |
| **Quality gate** | Evidence completeness (every claim traceable to a source artifact) · No hallucinated structural claims |
| **Primary model** | Gemini 2.5 Pro (Vertex AI asia-south1 — 1M token context, DPDPA-primary) |
| **Fallback** | Gemini 2.0 Flash (200k context — for bounded repository sections) |
| **Output format** | Structured JSON knowledge graph · not code · not prose |
| **Context strategy** | Full repository semantic chunking (Phase 2 context manager) + structural boundary detection |
| **Performance metric** | Evidence traceability rate (% of knowledge graph nodes traceable to specific source artifacts) |

---

## Alternatives Considered

### Alternative 1: Extend ADR-029 PSE to cover engineering tasks

**Rejected.** The PSE serves customer-facing agents with different quality metrics, context profiles, and constitutional obligations. Merging engineering execution into PSE would conflate two distinct constitutional Decision Spaces (customer outcome quality vs. code generation quality). The separation is constitutionally required per Article VIII.

### Alternative 2: Single best model for everything

**Rejected.** Gemini 2.5 Pro performs best for Deep Reasoning but is 5–10× the cost of Gemini Flash for Documentation tasks. Claude Sonnet performs best for Code Generation but lacks Gemini's 1M token context for full-repository semantic discovery. Using one model for all tasks either over-spends on simple tasks or under-performs on complex ones.

### Alternative 3: Stateless model routing (no performance tracking)

**Rejected.** C-069 requires the platform to improve itself using observed evidence. Static routing that never updates based on performance data is a direct C-069 violation. The performance composite score is constitutionally required, not optional.

---

## Consequences

**Positive:**
- Every LLM decision in engineering execution is traceable to constitutional evidence
- Model quality improves automatically from sprint data without Founder involvement
- Cost ceiling enforcement is automated — no manual monitoring needed
- DPDPA compliance is strongest possible for non-Code-Generation tasks

**Negative:**
- Adds pipeline complexity vs. simple `anthropic.messages.create()` call
- Task classification can be wrong — misclassified tasks use a suboptimal model
- Phase 1 does not yet address the Anthropic DPDPA gap for Code Generation

**Mitigations:**
- Task classification is rule-based (EEM step number + model_hint) — low error rate
- Misclassification degrades quality slightly but does not break constitutionality
- ADR-030 standard continues for Code Generation during transition; DPDPA gap tracked in ADR-033 backlog

---

## Implementation Traceability

```
Constitutional chain:
  C-069 (Self-Improvement) → MagicLLM performance tracking (§11 cost/performance governance)
  C-059 (Traceability) → MagicLLM Decision Record (§10 evidence)
  C-073 (Annotations) → Annotation Gate in Response Evaluator (§8)
  C-077 (Cost Ceiling) → Cost governance tiers (§11)
  C-082 (Build Validation) → Compile Gate in Response Evaluator (§8)

Implementation files (Phase 1):
  scripts/magic_llm/task_classifier.py
  scripts/magic_llm/model_selector.py
  scripts/magic_llm/context_builder.py
  scripts/magic_llm/execution_contract.py
  scripts/magic_llm/response_evaluator.py
  scripts/magic_llm/retry_advisor.py
  scripts/magic_llm/evidence_recorder.py
  infrastructure/postgres/init/09-magic-llm-performance.sql
```

---

*Proposed by AI Architect (INST-008) — GOAL-001 Phase 3*
*For Enterprise Architect (INST-004) review and Founder ratification.*
