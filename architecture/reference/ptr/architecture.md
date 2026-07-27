# PTR 2.0 — Dynamic Constitutional Knowledge Asset

**Classification:** Reference Architecture
**Status:** Proposed — Awaiting Enterprise Architect review + Founder acknowledgement
**Produced by:** AI Architect (INST-008) · Enterprise Architect (INST-004) — GOAL-003 Phase B (2026-07-27)
**Constitutional Basis:** C-059 (Traceability) · C-069 (Self-Improvement) · C-032 (Spec-Code Drift Gate)
**Goal Reference:** GOAL-003 — PTR as Dynamic Constitutional Knowledge Asset
**CRB Critique:** 8 challenges surfaced and resolved (C-01 through M-03)

---

## §0 — The Constitutional Role of PTR

**The PTR is not a file. It is the constitutional knowledge contract between the Goal Orchestrator and MagicLLM.**

Before MagicLLM generates a single line of code, it must receive a complete, accurate, scoped description of:
- What types currently exist (and can be referenced)
- What packages are available (and can be imported)
- What types WILL exist after the current phase completes (forward declarations)
- What patterns this codebase uses (canonical conventions)
- What obligations apply to the current scope (constitutional requirements)

If any of these five dimensions is wrong, MagicLLM will compensate — with guesses. Guesses produce CS0246, CS1061, import errors, pattern violations. The Retry Advisor fires. The cascade activates. The Founder is consulted. All of this is a governance failure — not a model failure.

**The Goal Orchestrator is constitutionally responsible for making this contract accurate before every MagicLLM invocation. No exceptions. No pre-sprint approximations. No "close enough."**

---

## §1 — PTR Lifecycle: Not a File, Not a Repo Artifact

```
BORN:     At Goal Orchestrator Phase 1 preparation
          Assembled fresh from repository source files + formal spec declarations

GROWS:    After each validated phase (post-compile gate — not post-Contribution Record)
          New types from Phase N-1's validated output are incorporated

SCOPED:   By the Impact Graph boundary (EEM Step 02)
          Full PTR is assembled for the Goal scope
          Task PTR (subset) is injected per MagicLLM invocation

HEALS:    When L2 Research Query fills a knowledge gap
          Research findings augment the current PTR instance

TEACHES:  After Goal closure, PTR learnings → Canonical Pattern Library (CANDIDATE status)
          Constitutional Analyst review → CANONICAL or REJECTED

DIES:     When Goal is CLOSED
          No PTR file is committed to the repository — ever

NEVER:    Committed to the repository
          Shared between concurrent Goals without PTR Dependency Analysis
          Used as a cache without content-addressed hash validation
```

---

## §2 — Five-Layer PTR Structure

Every PTR instance has five layers. All five are assembled by the Goal Orchestrator.

### Layer 1 — Current Compiled State (from source files)

**What it is:** Every type, function, class, interface, resource, and variable that currently exists in the repository scope, parsed directly from source files.

**Key design decision (C-01 resolution):** PTR assembles from **source files** — not from compiled output (dlls, pyc files, terraform state). Reason: in greenfield scenarios, there IS no compiled output in early phases. Source files are the canonical truth. The compile gate validates that source files produce correct compiled output — but PTR does not wait for compilation to be ready.

**Cold Start Protocol (C-01 resolution — greenfield):** When a Goal starts on an empty or near-empty repository:
- Layer 1 assembles whatever source files exist (may be empty)
- The absence of Layer 1 entries is VALID and expected for Phase 1 of a greenfield Goal
- MagicLLM Phase 1 receives: empty Layer 1 + Layer 4 (canonical patterns for target stack) + Layer 5 (constitutional obligations)
- This is the correct knowledge contract for "build from nothing" — not a failure state

**Stack-specific assemblers (M-03 resolution — stack-namespaced):**

```
PTR = {
  "dotnet": {
    "types": {
      "Waooaw.ConstitutionalEngine.Models.EvaluationContext": {
        "methods": ["GetParameter(string key): string"],
        "properties": ["TenantId: string", "AgentId: string"],
        "note": "GetParameter returns string — NOT a dictionary"
      },
      ...
    },
    "packages": {
      "Grpc.AspNetCore": "2.62.0",
      "Npgsql.EntityFrameworkCore.PostgreSQL": "8.0.0",
      "Moq": "4.20.0",
      ...
    }
  },
  "python": {
    "types": {
      "scripts.magic_llm.types.MagicLLMRequest": {
        "fields": ["goal_id: str", "institution_id: str", ...],
        "import": "from scripts.magic_llm.types import MagicLLMRequest"
      },
      ...
    },
    "packages": {
      "anthropic": "0.25.0",
      "google-cloud-aiplatform": "1.47.0",
      ...
    }
  },
  "terraform": {
    "providers": {
      "azurerm": "3.90.0",
      "azuread": "2.47.0"
    },
    "resources": {
      "azurerm_container_app": {...},
      "azurerm_key_vault_secret": {...},
      ...
    }
  },
  "typescript": {
    "types": { ... },
    "packages": { "next": "15.0.0", "tailwindcss": "3.4.0", ... }
  }
}
```

**Stack assembler coverage:**

| Stack | Source files scanned | Package manifests scanned |
|---|---|---|
| .NET | `**/*.cs`, `**/*.proto` (→ generated types) | `**/*.csproj` — all `<PackageReference>` entries |
| Python | `**/*.py` — classes, functions, TypedDict, Protocol | `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` |
| Terraform | `**/*.tf` — resource blocks, variable definitions, module outputs | `.terraform.lock.hcl` — provider versions |
| TypeScript/JS | `**/*.ts`, `**/*.tsx`, `**/*.js` — exported types, interfaces | `package.json` — `dependencies` + `devDependencies` |
| CSS | CSS custom properties, Tailwind config tokens | — |
| Proto | `**/*.proto` — message types, service RPCs → C# and Python generated types | — |

### Layer 2 — Forward Declarations (from formal typed spec output)

**What it is:** Types that do not yet exist in the repository but WILL exist after the current phase completes — declared formally in the Engineering Design Record (EEM Step 07).

**Formal spec output requirement (M-02 resolution):** EEM Step 07 must produce TWO outputs:
1. Natural language specification (for human review — existing requirement)
2. **Formal typed declarations** in the target stack's canonical format:
   - C# → interface files (`.cs`) with XML doc comments
   - Python → `TypedDict` or `Protocol` definitions (`.pyi` stub files)
   - TypeScript → `.d.ts` interface declarations
   - Terraform → variable type definitions (`.tfvars.json` schema)

The PTR assembler consumes the formal typed declarations as Layer 2. MagicLLM can reference them as if they exist. When Phase N completes successfully, its Layer 2 declarations become Phase N+1's Layer 1 entries.

**Post-validation trigger (C-02 resolution):** Forward declarations from Phase N's spec are activated as Layer 2 ONLY after Phase N-1's compile gate passes. If Phase N-1 fails and is redesigned, Layer 2 declarations are invalidated and rebuilt from the revised Engineering Design Record before Phase N begins. The Goal Orchestrator enforces this via the PTR refresh sequence (see §4).

### Layer 3 — Scope Filter (from Impact Graph)

**What it is:** The Impact Graph boundary from EEM Step 02 defines which components, services, and files are IN scope for this Goal. Layer 3 is a filter applied to Layers 1, 2, and 4 — only entries relevant to the Impact Graph scope are included in the Full PTR.

**Token budget protection (C-05 resolution — task-scoped injection):** The Full PTR (all in-scope entries) is assembled by the Goal Orchestrator. But what MagicLLM RECEIVES for each specific invocation is a **Task PTR** — a further-scoped subset containing only types directly referenced in the current task's spec section + their immediate dependencies.

```
Full PTR     → assembled by Goal Orchestrator, scoped to Impact Graph
Task PTR     → filtered by Context Builder per invocation, scoped to spec section
MagicLLM     → receives Task PTR — never the Full PTR directly
```

The Context Builder (MagicLLM §4, Component 3) produces the Task PTR by:
1. Parsing the current task's spec section for type name references
2. Extracting those types + their direct dependencies from the Full PTR
3. Adding all constitutional obligations for this task's scope
4. Adding relevant canonical patterns for the file being generated

### Layer 4 — Canonical Patterns (from Canonical Pattern Library)

**What it is:** How THIS codebase does things — extracted from existing code and accumulated through Goal Learning Records. Not generic best practices — WAOOAW-specific conventions.

**Examples:**
- "All C# services register their dependencies via static extension method `Add[ServiceName]Services()`"
- "All Python scripts begin with `# Implements:` and `# Constitutional basis:` headers"
- "All Terraform resources use `local.` prefix for computed values"
- "gRPC service methods always call `CE.RecordEvidence()` before returning success"

**Governance — candidate vs. canonical (C-04 resolution):**

```
Goal Learning Record produces pattern proposal
  ↓ status: CANDIDATE
  (MagicLLM uses CANDIDATE patterns with reduced confidence weight = 0.5)
  ↓
Constitutional Analyst reviews (asynchronous — does not block Goal)
  ↓
  APPROVED → status: CANONICAL (confidence weight = 1.0)
  REJECTED → status: REJECTED (removed from library permanently)
  ↓
CANONICAL patterns serve all future Goals with full confidence
```

CA review of patterns is batched — reviewed during periodic constitutional review cycles, not per-Goal. This ensures the library doesn't block Goal execution while maintaining quality governance.

### Layer 5 — Constitutional Obligations (from claims + WIOM Charter)

**What it is:** Which constitutional claims apply to every file being generated in this Goal scope, what annotations are required, which CCTs must pass.

**Examples for a Constitutional Engine task:**
- "Every `.cs` file must begin with `// Implements:` and `// Constitutional basis:` headers"
- "Every constitutional function must carry `[ConstitutionalClaim]` attribute"
- "C-007: no UPDATE or DELETE on `constitutional.audit_records` — reject any generated migration containing these"
- "CCT-EF-01 must pass: RecordEvidence called before success returned"

Layer 5 is assembled from the active constitutional claims scoped to the current task's domain, the EEM's CCT gate requirements for this phase, and the coding standards for the target stack.

---

## §3 — Goal Orchestrator PTR Protocol

The PTR Protocol defines WHEN the Goal Orchestrator assembles, refreshes, and discards the PTR.

### PTR Assembly Sequence

```
STEP A: Goal starts (Stage G-4 Planning)
  ├── Goal Orchestrator identifies all stacks present in Impact Graph
  ├── Assembles Full PTR (Layer 1: current source files, scoped to Impact Graph)
  ├── Adds Layer 4 (canonical patterns for each stack)
  ├── Adds Layer 5 (constitutional obligations for this Goal's domain)
  └── Layer 2 (forward declarations) is EMPTY at Goal start — no spec yet

STEP B: After EEM Step 07 (Engineering Design) completes
  ├── Engineering Design Record includes formal typed declarations
  ├── Goal Orchestrator assembles Layer 2 (forward declarations) from formal spec
  └── Full PTR is now: Layer 1 + Layer 2 + Layer 3 (scope filter) + Layer 4 + Layer 5

STEP C: After each validated Phase N (post-compile gate — NOT post-Contribution Record)
  ├── Phase N-1's validated source files rescanned (Layer 1 update for the new files)
  ├── Phase N-1's Layer 2 entries promoted to Layer 1 (they now exist)
  ├── New Layer 2 entries added from Phase N's spec section (if Step 07 produced them)
  └── Task PTR for Phase N is now ready — Goal Orchestrator issues Phase N GO Authorization

STEP D: After L2 Research Query fills a gap
  ├── Research Record findings added to Layer 1 augmentation (the missing type/package)
  └── The current phase retry proceeds with the augmented PTR

STEP E: Goal CLOSED
  ├── Patterns from Learning Records submitted to Canonical Pattern Library (CANDIDATE)
  └── Full PTR instance discarded — not committed
```

### Post-Validation Trigger (C-02 resolution)

**The compile gate is the PTR refresh trigger — not the Contribution Record.**

```
Current (wrong):
  Phase N-1 Contribution Record committed → Phase N GO Authorization issued
  → Phase N receives stale PTR (doesn't include N-1's types)

Correct (PTR 2.0):
  Phase N-1 Contribution Record committed
    ↓
  [External compile gate runs — dotnet build / pytest / tsc --noEmit]
    ↓ compile PASS
  Goal Orchestrator: PTR Layer 1 refresh from Phase N-1's validated output
  Goal Orchestrator: Layer 2 invalidation check (did N-1 produce the declared types?)
    ↓ Layer 2 validated
  Phase N GO Authorization issued WITH refreshed PTR attached
    ↓
  Phase N MagicLLM invocation receives accurate Task PTR
```

If Phase N-1's compile gate FAILS: Phase N GO Authorization is NOT issued. The Retry Advisor fires for Phase N-1. The PTR refresh is deferred until Phase N-1 succeeds.

---

## §4 — Parallel Goal PTR Dependencies (C-03 resolution)

GEOM §7 permits parallel Goal execution. But parallel Goals that share Impact Graph components create PTR divergence risk — Goal A's Phase 1 types aren't in Goal B's PTR.

**PTR Dependency Analysis** is added to the Goal Orchestrator's Routing step (Cat. 10):

```
For each pair of concurrently active Goals (GOAL-A, GOAL-B):
  IF GOAL-A.impact_graph.affected_components ∩ GOAL-B.impact_graph.affected_components ≠ ∅
    THEN: serialize affected phases
    The overlapping components' phases in GOAL-B wait for GOAL-A's compile gate to pass
    GOAL-A's new types are incorporated into GOAL-B's PTR refresh before GOAL-B continues

  IF intersection = ∅
    THEN: full parallel execution — no PTR dependency
```

This is tracked in the PTR Dependency Map — a new field in the Routing Decision Record:

```python
ptr_dependency_map: dict = {
    "GOAL-A": ["INST-004 Phase 2"],  # GOAL-B must wait for these
    "GOAL-B": [],                     # no dependencies
}
```

The Goal Orchestrator monitors this map and withholds GO Authorizations for dependent phases until their PTR prerequisites are met.

---

## §5 — Content-Addressed PTR Cache (M-01 resolution)

Within a single Goal execution, PTR assembly can be cached to avoid redundant scanning.

**Cache key:** `hash(stack_root_commit_SHA + impact_graph_signature + stack_name)`

**Cache rules:**
- Cache is **in-memory only** — not persisted to disk, not committed to repository
- Cache is **scoped to one Goal execution** — destroyed when Goal closes
- Cache is **invalidated** when any file in the Impact Graph scope changes (commit SHA changes)
- Cache is **never used** if its key doesn't match the current state — staleness is structurally impossible

This gives performance benefits within a Goal's multiple phase transitions (avoiding full rescan on each refresh) without introducing any cross-Goal staleness risk.

---

## §6 — Canonical Pattern Library Structure

```
architecture/reference/ptr/canonical-patterns/
  ├── dotnet/
  │   ├── dependency-injection.md     (how services register in this codebase)
  │   ├── grpc-service-pattern.md     (RecordEvidence before return)
  │   ├── unit-test-pattern.md        (AAA + FluentAssertions + Moq conventions)
  │   └── constitutional-annotations.md (which attributes are required where)
  ├── python/
  │   ├── file-header-pattern.md      (# Implements: + # Constitutional basis:)
  │   ├── async-pattern.md
  │   └── dataclass-conventions.md
  ├── terraform/
  │   ├── naming-conventions.md
  │   └── locals-pattern.md
  └── typescript/
      ├── component-pattern.md
      └── api-route-pattern.md
```

Each pattern file has:
```
status: CANONICAL | CANDIDATE | REJECTED
ratified_by: INST-002 | pending
ratified_at: [date or pending]
source_goal: GOAL-NNN (which Goal produced this pattern)
confidence_weight: 1.0 (CANONICAL) | 0.5 (CANDIDATE) | 0.0 (REJECTED)
applies_to: [list of file types / task categories]
pattern_text: [the actual pattern MagicLLM receives]
```

---

## §7 — Integration with EEM Step 07

EEM Step 07 (Engineering Design) is amended to produce a **formal typed output** alongside the natural language specification:

| Institution | Produces (language) | Produces (formal typed) |
|---|---|---|
| Solution Architect (INST-005) | Interface descriptions | `.cs` interface files · TypeScript `.d.ts` declarations |
| Data Architect (INST-006) | Schema descriptions | EF Core `DbSet<>` declarations · Python `TypedDict` |
| AI Architect (INST-008) | MagicLLM strategy | Python `Protocol` definitions for new AI components |

These formal typed outputs are committed to `architecture/reference/ptr/forward-declarations/GOAL-NNN/` during Step 07 — NOT to `src/`. They are spec artifacts, not implementation artifacts. The PTR assembler reads them as Layer 2 inputs.

---

## §8 — Summary: What Changes from PTR 1.0

| Dimension | PTR 1.0 (current) | PTR 2.0 (this spec) |
|---|---|---|
| Lifecycle | Static, assembled once pre-sprint | Dynamic, assembled at Goal start, refreshed per validated phase |
| Assembly trigger | Manual / pre-sprint script | Goal Orchestrator, post-compile gate |
| Storage | JSON file committed to repo | In-memory runtime artifact, never committed |
| Stack coverage | .cs, .py, .ts, .tf (partial) | All stacks, full manifest scanning including package files |
| Structure | Flat dict | Stack-namespaced dict |
| Forward declarations | None | From formal typed Step 07 output |
| Scope | Global (all compiled types) | Impact Graph scoped + task-scoped per invocation |
| Token efficiency | Full PTR injected | Task PTR (subset) injected per invocation |
| Canonical patterns | None | Canonical Pattern Library (CANDIDATE → CANONICAL via CA) |
| Parallel Goal safety | None | PTR Dependency Map, serialized phases for overlapping components |
| Cache | None | Content-addressed in-memory cache (commit SHA keyed) |
| Cold start | Error (no types found) | Valid state — Phase 1 receives empty Layer 1 + patterns + obligations |

---

*Produced by AI Architect (INST-008) + Enterprise Architect (INST-004) — GOAL-003 Phase B*
*8 CRB challenges addressed: C-01 · C-02 · C-03 · C-04 · C-05 · M-01 · M-02 · M-03*
*Pending Enterprise Architect peer review + Founder acknowledgement.*
