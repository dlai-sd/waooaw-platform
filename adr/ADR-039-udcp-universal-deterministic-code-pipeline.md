# ADR-039: Universal Bounded Code Pipeline for Autonomous Engineering Tasks

## 1. Metadata
* **Date:** 2026-08-02
* **Author:** Office of the Enterprise Architect (INST-004)
* **IB Item:** IB-009 — Foundation Implementation (Gate G5)

---

## 2. Status & Supersedes
* **Status:** Proposed
* **Supersedes:** ADR-030 §3 (MagicLLM full-file generation loop) for all new sprint execution. ADR-030 §1–2 (model selection, provider strategy) remain in force.

---

## 3. Context
Deploying LLM agents to perform open-ended file creation, architecture synthesis, and raw source changes introduces non-deterministic variability into production codebases. In structural engineering tasks within the platform, LLM loops exhibit two critical failure modes:

1. **Upstream Contamination (Invented Names):** Generating references to objects, functions, or database schemas that do not exist within the workspace.
2. **Downstream Layout Damage:** Destructive rewriting of legacy code files, resulting in corrupted code indentation, dropped decorators, and lost inline documentation.

Evidence: Run 30747246428 (WC-027) — 30/33 LLM calls on Sonnet (₹232 total), zero tasks completed. Root causes: `PriceDeriveResponse` invented import (PYTHON_WRONG_SYMBOL, 6 Cascade calls exhausted), `BundleEngine() takes no arguments` test scaffold error (retry advisor returned UNKNOWN, no `<file>` blocks in Cascade L1).

To unlock repeatable, autonomous work context (WC) sprint executions, the platform requires an architectural boundary that strips LLMs of structural layout authority and limits their capabilities to isolated code logic generation.

---

## 4. Constitutional Basis

| Claim / Basis | Description | Direct Application in ADR-039 |
| :--- | :--- | :--- |
| **C-031** | No significant architectural decision without an ADR. | This document formally fulfills the requirement for the code generation layer. |
| **C-032** | Implementation may not create architecture. | The UDCP enforces this by stripping structural layout authority entirely from the LLM. |
| **C-059** | Traceability Requirements. | Compliance header injection and source tracking move to deterministic scaffold time. |
| **C-082** | Build Validation. | Mandates a live Project Type Registry (PTR) gate and a strict `compile()` check before any file write. |
| **C-077** | Dev Tooling Cost Ceiling. | Logic-only prompts eliminate model text pollution and prevent expensive context token escalation. |
| **ADR-036** | EA Skeleton Standard. | Establishes the machine-readable TIS/TMD schemas as the direct operational successors to hand-authored skeletons. |

---

## 5. Decision

We will enforce the **Universal Deterministic Code Pipeline (UDCP)** across all automated engineering work items. The architecture separates code generation into a **Deterministic Rule-Based Grooming Phase** and a **Dual-Track AST Execution Pipeline**.

```
[ WC Markdown Task Suite ] ──> [ Rule-Based Grooming Parser ] ──> [ TIS / TMD Schema ]
                                                                          │
              ┌───────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┐
              ▼                                                                                                                       ▼
┌──────────────────────────────┐                                                                                     ┌──────────────────────────────┐
│ TRACK 1: GREENFIELD PIPELINE │                                                                                     │ TRACK 2: DIFFERENTIAL PIPELINE│
├──────────────────────────────┤                                                                                     ├──────────────────────────────┤
│  • Real-time PTR Gate Check  │                                                                                     │  • Target Node Isolation     │
│  • Code Stub Injection       │                                                                                     │  • Signature Lock Assertion  │
│  • Compile Validation Gate   │                                                                                     │  • Clean Indentation Splice  │
└──────────────────────────────┘                                                                                     └──────────────────────────────┘
```

### 5.1 The Rule-Based Grooming Engine

Structural definition synthesis will be completely **LLM-free**. A deterministic, rule-based string parser will extract structural information from target Markdown execution suites and match it against repository base configurations. This ensures that the generated Technical Interface Specification (TIS) and Targeted Modification Descriptor (TMD) contracts are 100% accurate before execution begins.

The grooming engine operates in two phases:
- **Extraction Phase:** Regex/markdown splitter processes WC task table rows to collect target file paths, framework signals (e.g., "FastAPI router"), HTTP method patterns, and parameter schemas.
- **Resolution Phase:** Cross-references extracted structural definitions against the EA skeleton file (`src/{service}/skeleton/`) to infer argument types and interface signatures without LLM involvement.

### 5.2 Track 1: Greenfield Execution

- Evaluates new system additions using a programmatic text scaffolder.
- Enforces a mandatory **Project Type Registry (PTR) validation gate** that checks all TIS imports against the local code workspace symbol index, tracking re-exports (`ast.ImportFrom`) and resolving custom `sys_path_roots` (e.g., `src/billing-engine/`) dynamically.
- The PTR symbol index is rebuilt at the start of every task execution pass to account for symbols created by earlier tasks in the same sprint.
- Executes a syntax compilation check (`compile()`) on generated skeleton files *prior* to disk write.
- Conditional router instantiation: `router = APIRouter()` is emitted only when at least one interface carries a route decorator (`router.get`, `router.post`, etc.).
- Structural implementation details regarding multi-type object data properties (Pydantic model class scaffolding) are deferred out of this decision boundary. See WC-EXT-01 §2.

### 5.3 Track 2: Differential Execution

- Targets changes in existing code files using a localized AST extraction process.
- Dissects and exposes only the isolated functional block to the LLM agent via `extract_node_for_llm()`, stripping decorator metadata to avoid prompt pollution.
- To prevent permanent AST corruption during execution, the node extraction engine must encapsulate its structural mutations inside strict context guards (`try/finally` recovery blocks).
- Applies a precise character-range text swap to insert the updated code logic. Decorator lines are extracted verbatim from the original source; only the `def` + body block receives indentation normalization via `ast.unparse()`. This approach preserves the formatting, comments, and spacing layout of the surrounding codebase with zero collateral footprint.
- Enforces an AST signature validation invariant via `ast.unparse(args)` comparison to block execution if the generated code mutates method signatures.
- Supports both class-method targets (`class_name` + `target_name`) and top-level function targets (`class_name=None`) — covers test files as well as service files.

---

## 6. Consequences

### 6.1 Positive Impacts

- **Zero Layout Degradation:** The pipeline eliminates collateral layout damage and linting bugs caused by LLM source alterations.
- **Elimination of Structural Hallucinations:** Invented module imports or mismatched names are caught and blocked at the PTR validation gate before calling the LLM.
- **Cost Efficiency:** Restricting LLM processing contexts to isolated logic targets removes context-pressure Sonnet escalation. Logic-only prompts are expected to remain under 10k chars — well below the ADR-030 Amendment 2 thresholds.

### 6.2 Negative Impacts & Mitigation Gaps

- **Operational Operator Escalation:** Cascading errors caused by upstream changes will bypass automated recovery tools and route directly to a human developer for manual intervention (See §7.1).
- **Wildcard Tracking Limits:** Modules using open wildcard re-exports (`from X import *`) will expose a literal `*` indicator symbol within the validation engine, requiring specific named exports across all system boundaries (See §7.2).

---

## 7. Known Platform Limits & Escalations

### 7.1 TIS Mutation Path
When structural code updates break due to upstream out-of-bounds dependency changes, automated repair loops are strictly forbidden. The execution layer must halt immediately, dump the compilation trace logs, and escalate directly to an operator for manual reconciliation.

### 7.2 Wildcard Re-Export Processing
`from module import *` statements emit a literal `*` indicator symbol inside the validation registry index. Because wildcard operations hide explicit structural names from static code tracing, all system boundaries must explicitly name exports to pass PTR validation. This is enforced as an anti-pattern by ruff F403 in the existing compile gate.

### 7.3 Implementation References
- **Class Scaffolding Specifications:** For details regarding the expanded programmatic schema support for data models (Pydantic `BaseModel`, dataclasses), see **WC-EXT-01 §2 (Class Scaffolding Extension)**.
- **AST Context Hardening:** Implementation requirements forcing `try/finally` encapsulation of all AST node mutation operations in `extract_node_for_llm()` are specified in the Track 2 Polymorphic Engine. See **WC-EXT-01 §3 (AST Context Guards)**.
