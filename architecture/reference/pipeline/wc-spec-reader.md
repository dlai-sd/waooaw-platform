# WC-Spec-Reader Architecture Specification

**Document type:** Architecture Reference — Pipeline Tooling
**Office:** Enterprise Architect (Office 04)
**IB item:** IB-022 — WC-Spec-Driven Sprint Runner (Option B)
**Constitutional basis:** C-059 (Traceability), C-032 (Spec before code), C-083 (Emit-Transport-Listen), DP-009 (API First)
**Status:** APPROVED — 2026-07-24 (EA session, Founder-authorized option B)
**Depends on:** IB-021 (sprint-task-decomposition.md), ADR-030 (amendment)

---

## Problem Statement

The autonomous sprint runner (`autonomous_sprint_runner.py`) currently embeds `constitutional_check` strings directly inside `SubTaskDef` entries — hand-written prose that describes what the LLM must do for each subtask. This design has three constitutional violations:

1. **C-059 violation**: The strings are untraced to any approved spec. They exist as pure implementation knowledge with no `Implements:` reference.
2. **C-032 violation**: Constitutional requirements and task boundaries are architectural decisions embedded inside implementation code.
3. **Maintenance gap**: Adding WC013–WC024 requires a developer to read the PMO work contract and manually translate it into SubTaskDef strings — error-prone and O(N) with sprints.

---

## Solution: Option B (EA-authorized 2026-07-24)

**PMO scope (unchanged):** Work Contracts define WHAT to build — scope, constitutional requirements, model_hint, CCT gates.

**EA scope (new):** `sprint-task-decomposition.md` authorizes HOW each WC task is decomposed into LLM subtasks. This is an architectural decision; C-032 requires it to be documented outside implementation code.

**WCSpecReader role:** Bridge between PMO spec and runner. Reads WC documents → extracts per-task structured fields → feeds into `_build_effective_check()`.

---

## Data Model

### `WCTaskSpec` (parsed from PMO work contract)

```python
@dataclass
class WCTaskSpec:
    task_id: str           # "WC012-02"
    title: str             # "ValidateAction + unit tests (≥90% coverage)"
    scope: str             # verbatim **Scope:** field
    model_hint: str        # "reasoning" | "auto" | "none"
    constitutional_check: str  # verbatim **Constitutional check:** field
    cct_gate: str          # "CCT-EF-01 must pass" | ""
    stack: str             # inferred: "dotnet" | "python" | "typescript" | "terraform" | "mixed"
```

Stack inference rules (from scope text):
- Contains `src/constitutional-engine` or `.cs` → `dotnet`
- Contains `src/professional-runtime` or `.py` → `python`
- Contains `web/` or `.tsx` or `Next.js` → `typescript`
- Contains `infrastructure/terraform` or `.tf` → `terraform`
- Multiple of the above → `mixed`

### `SubTaskDef` extended fields

```python
@dataclass
class SubTaskDef:
    # Existing fields (unchanged)
    id: str
    description: str
    type: str                      # "deterministic" | "llm" | "none"
    depends_on: list[str]
    compile_gate: str
    template_fn: Any
    spec_sections: dict
    model_hint: str
    max_tokens: int

    # NEW fields (IB-022)
    wc_task_id: str = ""           # "WC012-02" → auto-loads PMO spec
    output_files: list[str] = []   # files this subtask MUST produce
    not_regenerate_from: list[str] = []  # prior subtask IDs whose files must not be re-emitted
    stack: str = "dotnet"          # selects STACK_BEHAVIORAL_RULES entry

    # DELTA field (unchanged semantics — now OPTIONAL override)
    constitutional_check: str = "" # task-specific delta; if empty, built from WC spec
```

---

## Interface Specification

### `wc_spec_reader.py`

```python
class WCSpecReader:
    """
    Reads PMO Work Contracts and extracts per-task structured fields.
    
    # Implements: architecture/reference/pipeline/wc-spec-reader.md
    # constitutional_basis: C-059 (Traceability), DP-009 (API First)
    """

    @staticmethod
    def find_wc_file(wc_number: str) -> Path | None:
        """
        Find work-contracts/WC-{wc_number}-*.md.
        Returns None if not found (graceful degradation).
        """

    @staticmethod
    def load(wc_number: str) -> dict[str, WCTaskSpec]:
        """
        Parse all tasks from a work contract.
        Returns empty dict if file not found (graceful — runner falls back to constitutional_check delta).
        """

    @staticmethod
    def get_task(task_id: str) -> WCTaskSpec | None:
        """
        Get spec for a specific task ID (e.g. "WC012-02").
        Derives wc_number from task_id (first 5 chars).
        Returns None if not found.
        """
```

### Parser rules

WC task blocks match the pattern:
```
### WC{NNN}-{NN} — {title}

**Scope:** {text}
**model_hint:** `{value}`
**Constitutional check:** {text}   (optional)
**CCT gate:** {text}               (optional)
**Output:** {text}                 (optional)
```

All fields are optional except `### WC...` header and `**Scope:**`.

---

## `STACK_BEHAVIORAL_RULES`

Defined in `task_decomposer.py`. These are EA-approved architectural floor rules per technology stack. They apply to every LLM subtask on that stack and must not be changed without EA review.

```python
STACK_BEHAVIORAL_RULES: dict[str, list[str]] = {
    "dotnet": [
        "ActionParameters is JSON-encoded — use ctx.GetParameter(\"key\"), NEVER TryGetValue().",
        "TenantId comes from gRPC metadata: context.RequestHeaders.GetValue(\"x-tenant-id\") ?? \"\".",
        "All using directives MUST precede the namespace declaration to avoid proto namespace collision.",
        "PROTO NAMESPACE: using Waooaw.ConstitutionalEngine.Grpc; on files referencing gRPC types.",
        "C-059 header required on every .cs file: // Implements: <spec> and // constitutional_basis: <claims>.",
    ],
    "python": [
        "No synchronous DB calls from Temporal activities — use async/await throughout.",
        "Every FastAPI endpoint must call CE.ValidateAction before execution (C-023).",
        "PII must not appear in any log statement (C-063).",
        "C-059 header required: # Implements: <spec> and # constitutional_basis: <claims>.",
    ],
    "typescript": [
        "JWT stored in httpOnly cookie ONLY — never localStorage or sessionStorage.",
        "All API mutations require CE.ValidateAction call before execution (C-023).",
        "Emergency Stop button must be rendered on every authenticated page (C-001).",
        "C-059 header required: // Implements: <spec> and // constitutional_basis: <claims>.",
    ],
    "terraform": [
        "All outputs must be named and described — they become PTR terraform_output entries.",
        "No secrets in Terraform state — use Azure Key Vault references (ADR-014).",
    ],
    "mixed": [],  # No stack-specific rules — use constitutional_check delta
}
```

---

## `_build_effective_check()` Algorithm

```
function _build_effective_check(subtask: SubTaskDef, completed: list[str]) -> str:

  parts = []

  # 1. PMO constitutional requirements (auto-loaded)
  if subtask.wc_task_id:
      wc_spec = WCSpecReader.get_task(subtask.wc_task_id)
      if wc_spec:
          parts += [
              f"CONSTITUTIONAL REQUIREMENTS (PMO: {subtask.wc_task_id} — {wc_spec.title}):",
              f"Scope: {wc_spec.scope}",
              wc_spec.constitutional_check  # if non-empty
          ]

  # 2. Subtask file boundaries
  if subtask.output_files:
      parts += ["Implement ONLY these files:", *subtask.output_files]

  # 3. Prior task preservation (derived from not_regenerate_from ∩ completed)
  preserved = [t for t in subtask.not_regenerate_from if t in completed]
  if preserved:
      parts += [f"Do NOT regenerate files from prior subtasks: {', '.join(preserved)}"]

  # 4. Stack behavioral rules (EA floor)
  rules = STACK_BEHAVIORAL_RULES.get(subtask.stack, [])
  if rules:
      parts += ["STACK RULES (non-negotiable):"] + rules

  # 5. Explicit delta (task-specific override)
  if subtask.constitutional_check:
      parts += [subtask.constitutional_check]

  # PTR type contracts appended by execute_subtask_chain after this function
  return "\n\n".join(filter(None, parts))
```

---

## Integration Contract

`execute_subtask_chain` calls `_build_effective_check(st, completed)` immediately before each LLM subtask call, replacing the current direct use of `st.constitutional_check`.

The PTR type contract block (already implemented) is appended AFTER `_build_effective_check()` output — maintaining separation between task instructions (from WC spec) and type contracts (from compiled code).

---

## Error Handling and Graceful Degradation

| Condition | Behaviour |
|---|---|
| WC file not found | Log warning; fall back to `st.constitutional_check` delta only |
| Task ID not in WC | Log warning; fall back to delta |
| WC field missing (e.g. no Constitutional check) | Skip that section; include others |
| Stack not in STACK_BEHAVIORAL_RULES | No stack rules; log warning |

**Principle:** WCSpecReader failure must NEVER block sprint execution. It is an enhancement, not a dependency.

---

## Constitutional Compliance

| Claim | How this spec satisfies it |
|---|---|
| C-059 | Every SubTaskDef with `wc_task_id` traces directly to an approved WC document. `_build_effective_check()` makes the traceability explicit and machine-verifiable. |
| C-032 | Subtask decomposition decisions are in `sprint-task-decomposition.md` (EA authority), not embedded in implementation code. |
| C-083 | Parsed WC spec is a structured signal emitted into the SubTaskDef construction chain. |
| DP-009 | PMO Work Contract is treated as the authoritative interface specification — WCSpecReader reads it, never generates it. |

---

## Test Requirements

- Unit tests: `tests/pipeline/test_wc_spec_reader.py`
- Coverage: ≥90% on `wc_spec_reader.py`
- Must cover: find, load, get_task, parser (all fields), graceful fallback, stack inference
- Must cover: `_build_effective_check()` with all combinations (WC found/not found, output_files, preserved, stack rules, delta)
- Integration test: `_build_effective_check("WC012-02b", ...)` produces expected sections
