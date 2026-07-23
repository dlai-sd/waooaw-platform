# ADR-030: Autonomous Sprint Agent Code Generation (IB-020)

**Status:** Accepted
**Date:** 2026-07-23
**Roles Applied:** Enterprise Architect + Solution Architect
**Constitutional Basis:** C-059 (Traceability), C-066 Tier 2A (Autonomous Sprint), C-073 (Annotations), C-077 (Dev Tooling Cost Ceiling ₹5,000/month)
**IB Reference:** IB-020

---

## Context

WC-011 (infrastructure validation) was executed with pure Python handlers (`model_hint: none`). WC-012 through WC-018 require generating .NET, Python, and TypeScript source code — actions the runner cannot perform without LLM assistance.

This ADR governs how the autonomous sprint agent generates code: which model, what token budget, how files are written, and how failures are handled.

---

## Decision

**Claude Sonnet 4.6 (Anthropic API) for `model_hint: reasoning` tasks. No LLM for `model_hint: none` or `model_hint: auto` tasks where pure logic suffices.**

### Model Routing

| model_hint | LLM call? | Model | Max input tokens | Cost class |
|---|---|---|---|---|
| `none` | No | — | — | ₹0 |
| `auto` | Optional | Claude Haiku (cheapest capable model) | 8,000 | ~₹0.10/task |
| `reasoning` | Yes | Claude Sonnet 4.6 | 100,000 | ~₹15/task |

### Code Generation Protocol

Every `model_hint: reasoning` task follows this protocol:

```
1. LOAD CONTEXT
   build_sprint_index.py already ran → sprint-context/index.json available
   Runner reads: task_id, spec_sections, constitutional_check, model_hint

2. BUILD PROMPT
   System: Constitutional obligations + Decision Space + C-059 annotation rules
   User: Task description + spec content (from spec_sections) + constitutional_check
   Format instruction: "Respond with XML file blocks: <file path="...">...content...</file>"

3. CALL CLAUDE API
   Model: claude-sonnet-4-6 (or current Anthropic alias)
   Max tokens output: 8,000 (one task = one service component, not the full service)
   Temperature: 0 (deterministic code generation)
   ANTHROPIC_API_KEY: from Azure Key Vault (fetched in execute job step)

4. PARSE RESPONSE
   Extract <file path="..."> blocks from response
   Map to REPO_ROOT / path
   Reject paths outside allowed write boundaries (src/**, tests/**, infrastructure/**)

5. WRITE FILES
   Create parent directories if needed
   Write each file
   Verify file was written (size > 0)

6. VALIDATE
   model_hint: reasoning tasks always run a validation step after writing:
   - .NET: dotnet build (if .csproj files written)
   - Python: ruff check + python3 -m py_compile (if .py files written)
   - TypeScript: tsc --noEmit (if .ts/.tsx files written)
   - Any: run the task's CCT gate if one is defined

7. RETRY (max 2 additional attempts)
   If validation fails: include failure output in next Claude call context
   If still failing after 3 total attempts: call flag_spec_gap() and return False

8. COMMIT
   git add {written_files}
   git commit -m "feat({service}): {task_id} — {task_description}\n\nIB: IB-009\nConstitutional: {claims}"
```

### File Write Boundaries (C-059 + C-065 compliance)

The LLM response parser MUST reject any path outside these boundaries:

```python
ALLOWED_WRITE_ROOTS = [
    "src/",
    "tests/",
    "infrastructure/postgres/",
    "infrastructure/keycloak/",
    "logs/",
]
# NEVER write to: constitution/, adr/, architecture/, knowledge/, standards/
```

Attempting to write outside these boundaries calls `flag_spec_gap()` immediately.

### Cost Enforcement (C-077)

- Monthly ceiling: ₹5,000 (set as $35/month limit in Anthropic console — T0-1)
- Per-task estimate: ~₹15 for reasoning (5K input + 2K output × 3 iterations)
- WC-012 (4 tasks): ~₹60 total
- WC-011 to WC-018 combined: ~₹480 total (well within C-077)

---

## Implementation

See `scripts/autonomous_sprint_runner.py` — functions `call_llm()`, `parse_llm_files()`, and `execute_wc012_*()` through `execute_wc017_*()`.

See also `scripts/build_sprint_index.py` — `TASK_CONTEXT_MAP` provides spec context for each task.

---

## Consequences

**Positive:**
- WC-012 through WC-018 can now execute autonomously
- Every generated file has full constitutional annotation (C-059, C-073) enforced by prompt
- Retry loop with validation catches compile errors before PR is opened
- Cost is bounded and transparent (C-077)

**Negative:**
- Code generation quality depends on spec clarity — if spec is ambiguous, Claude may produce wrong code
- `flag_spec_gap()` halts the sprint when quality fails after 3 attempts — Yogesh must review

**Risk mitigation:** Every generated file goes through CCTs before merge. The reviewer job posts Grade A/F. A generated file that fails CCTs is caught before it reaches main.

---

## References
- C-059 (Traceability), C-065 (SDLC Separation), C-066 Tier 2A, C-073 (Annotations), C-077 (Cost Ceiling)
- `scripts/build_sprint_index.py` — TASK_CONTEXT_MAP spec sections
- `architecture/reference/graceful-degradation.md` — flag_spec_gap escalation path
- `FOUNDER-ACTION.md` T0-1 — Anthropic API key in Key Vault
