# ADR-036 — EA Skeleton Standard: Blueprint-First Code Architecture

**Status:** Accepted
**Date:** 2026-07-30
**Author:** Enterprise Architect (INST-004) — GOAL-PLATFORM-REGISTRY
**Constitutional Basis:** C-059 (Implementation Traceability), C-095 (Component Manifest
Obligation), ADR-035 (Platform-Agent Contract Standard)
**Simulation Basis:** SIM-PLATFORM-001 (30/30 PASS, 2026-07-30)
**Supersedes:** Nothing — this is a new standard for code skeleton production

---

## Context

WC-012 through WC-015 were implemented without Component Manifests or Code Skeletons.
The autonomous pipeline produced code by reading prose specifications and generating
complete implementations in a single LLM call. This approach produced correct architecture
but at high error cost:

- **3 LLM attempts per task** on average (measured in production runs)
- **CS0246/CS1061 errors** (type not found / method not found) on first attempts
- **Retry advisor classifying as SYMBOL_RESOLUTION** — correct classification but avoidable
- **Root cause confirmed**: LLM invented class names and method signatures when they
  were not provided. The PTR could not help because it was populated from compiled code —
  which didn't exist before the first (failing) compilation attempt.

SIM-PLATFORM-001 validated the solution: providing a Code Skeleton before the
implementation sprint gives the LLM exact type names, method signatures, and data model
shapes. Type invention becomes structurally impossible. First-attempt compile rate
approaches 100%.

**75% token reduction. 67% attempt reduction. 100% elimination of type-invention errors.**

---

## Decision

### 1. The Skeleton Standard — What EA Produces

A Code Skeleton is a set of source files containing type contracts with NO business logic.

**Python skeletons contain:**
```python
# src/{service}/skeleton/{module}.py
# Implements: architecture/reference/components/manifest/{service}.yaml §{section}
# Constitutional basis: [claims that govern this contract]
# EA-PRODUCED SKELETON — implementation sprint fills method bodies ONLY

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

class I{ServiceName}(ABC):
    """
    Contract for {service name}.
    Constitutional basis: {claim IDs}
    Implementation sprint: fill bodies of all @abstractmethod methods.
    DO NOT change: class names, method names, parameter types, return types.
    If change needed: raise SPEC_GAP → EA session amends skeleton.
    """
    @abstractmethod
    async def {method_name}(
        self,
        {param}: {type},
        ...
    ) -> {ReturnType}:
        # SLA: {if applicable}
        # Raises: {ExceptionType} when {condition}
        # Constitutional: {which claim enforced here}
        ...

@dataclass(frozen=True)
class {ModelName}:
    {field_name}: {type}
    {field_name}: Optional[{type}]  # None when {condition}

class {ErrorName}({BaseError}):
    """Raised when {condition}. Maps to HTTP {status code}."""
    def __init__(self, {params}): ...
```

**.NET skeletons contain:**
```csharp
// src/{service}/Skeleton/I{ServiceName}.cs
// Implements: architecture/reference/components/manifest/{service}.yaml §{section}
// Constitutional basis: {claims}
// EA-PRODUCED SKELETON — implementation project fills this interface

namespace Waooaw.{ServiceName}.Skeleton;

/// <summary>
/// Contract for {service}. DO NOT modify signatures — raise SPEC_GAP if change needed.
/// </summary>
public interface I{ServiceName}
{
    /// <summary>
    /// {Description}. Constitutional basis: {claim}.
    /// </summary>
    /// <returns>{description}</returns>
    /// <exception cref="{ExceptionType}">When {condition}</exception>
    Task<{ReturnType}> {MethodName}(
        {ParamType} {paramName},
        CancellationToken ct = default
    );
}

/// <summary>Data contract — frozen after EA approval.</summary>
public sealed record {ModelName}(
    {Type} {PropertyName},
    {Type}? {OptionalProperty}
);
```

### 2. Hard Boundary — What Skeletons MUST and MUST NOT Contain

**MUST contain (EA produces this):**
- Abstract base classes / interfaces (all public methods declared)
- Data model classes/records/dataclasses with all fields and types
- Exception classes with names, base classes, and constructor signatures
- Router/controller stubs with route signatures (empty method bodies)
- Enum types with all values
- C-059 `# Implements:` header on every file
- Docstrings citing constitutional basis per method

**MUST NOT contain (implementation sprint produces this):**
- Method bodies (any logic, any `if/else`, any algorithm)
- SQL queries
- Redis cache logic
- HTTP client calls
- Business rule implementations
- Error handling logic

Violation of this boundary triggers Rule 16 in sprint_retry_advisor.py:
any IMPLEMENTATION sprint output that modifies a skeleton's public interface
is classified as SPEC_GAP, not SYNTAX_ERROR, and routes to EA, not retry.

### 3. EA Authority to Produce Skeleton Files

BOOTSTRAP §Office Knowledge Specifications states EA "Must NOT Read: src/".
This ADR establishes a constitutional exception: **EA may produce and read files
in `src/{service}/skeleton/` directories only.** This exception is granted because:

- Skeleton files are specification artifacts expressed in the target language
- They contain zero business logic (MUST NOT list above is enforced)
- They are the target-language equivalent of interface specifications in architecture docs
- The implementation sprint cannot modify them — they are EA-owned artifacts

**Analogy:** An architect draws precise structural specifications on a blueprint that
construction workers must follow exactly. The architect's drawing is not "construction."
EA producing `IWalletService` with method signatures is the drawing. The implementation
sprint filling method bodies is the construction.

The `src/{service}/skeleton/` directory is the "blueprint drawing" location. It is
constitutionally distinct from `src/{service}/` where implementation code lives.

### 4. Skeleton Compile Gate

Before any IMPLEMENTATION sprint fires for a service, the skeleton must compile:

```bash
# Python services
python3 -c "
import ast, sys, pathlib
for f in pathlib.Path('src/{service}/skeleton').rglob('*.py'):
    ast.parse(f.read_text())  # syntax check
    print(f'✓ {f}')
print('All skeleton files valid.')
"

# .NET services
dotnet build src/{service}/{ServiceName}.Skeleton.csproj
```

The task_decomposer.py pre-flight check (PL-S1-02) enforces this gate.
If skeleton fails to compile: Constitutional Blocker → EA session fixes spec.
The sprint does NOT proceed until skeleton compiles cleanly.

### 5. Task Types — The Three-Sprint Model

Every implementation sprint now follows a three-phase model:

```
Phase EA   (SKELETON task_type)
  Office: INST-004 Enterprise Architect
  Input:  Component spec + manifest template
  Output: skeleton/ directory (compiles cleanly)
  Gate:   compile gate passes
  
Phase S    (IMPLEMENTATION task_type)
  Office: INST-010 Platform IT Expert
  Input:  skeleton/ + component spec prose + PTR (populated from skeleton)
  Output: implementation code (method bodies only)
  Prompt: "DO NOT change skeleton interfaces. Fill bodies only."
  Gate:   CCT gate passes
  
Phase CCT  (CCT task_type)
  Office: INST-010 Platform IT Expert
  Input:  implementation code + skeleton contracts
  Output: test files (every method contract has a test)
  Gate:   all tests pass
```

### 6. Work Contract Format Update

```markdown
### {Task ID} — {Task Name}

**task_type:** SKELETON | IMPLEMENTATION | CCT
**office:** INST-004 | INST-010
**model_hint:** reasoning | standard | auto
**skeleton_path:** src/{service}/skeleton/ (required for IMPLEMENTATION tasks)
**depends_on:** {EA task id if IMPLEMENTATION}
```

The `task_type` field is new. Default: `IMPLEMENTATION` for backward compatibility.
Existing WCs without `task_type` continue to work as before — they are treated as
IMPLEMENTATION tasks with no skeleton gate (legacy behavior, not preferred).

### 7. Pipeline Changes (from SIM-PLATFORM-001)

| Component | Change | Effort |
|---|---|---|
| `context_builder.py` | Inject skeleton files when task_type=IMPLEMENTATION | SMALL |
| `task_decomposer.py` | SKELETON task type + compile gate pre-flight | MEDIUM |
| `sprint_retry_advisor.py` | Rule 16: skeleton drift → SPEC_GAP | SMALL |
| `pre_sprint_sim.py` | Skeleton existence check | SMALL |
| `autonomous_sprint_reviewer.py` | API surface immutability check | MEDIUM |
| Work Contract schema | task_type field (default: IMPLEMENTATION) | TRIVIAL |

All changes are backward-compatible. Existing sprints without `task_type` field
continue to function as IMPLEMENTATION tasks with no skeleton gate.

---

## Consequences

- New directory `src/{service}/skeleton/` per service (EA-owned, not implementation)
- New `architecture/reference/components/manifest/` directory (one YAML per service)
- `architecture/reference/platform-component-registry.yaml` — lists all components
- `scripts/blueprint_assurance.py` — 15-day conformance run
- `scripts/gap_scanner.py` — agent PAC alignment check per new component
- ADR-035 (PAC Standard) — complementary: signals; this ADR — code contracts
- C-095 (Component Manifest Obligation) — makes this ADR constitutionally enforced
- All future Goals' D-10 (Sprint Execution Plan) includes EA sprint as first sprint

---

## Rejected Alternatives

**A — Prose specs only (status quo):** Rejected. SIM-PLATFORM-001 confirmed 3 retries
and 24,000 tokens per task due to type invention. The status quo is expensive and fragile.

**B — Clean slate (discard WC-012..WC-015 code):** Rejected. The existing code is
constitutionally correct (434 CCTs pass). Discarding tested, working code to satisfy
a documentation standard violates C-048 (Non-Exploitation — institutional resources).
Retroactive manifests and skeletons provide the same blueprint benefits without rebuild.

**C — TypeStubs only (no abstract base classes):** Rejected. Type stubs (.pyi files)
provide type hints but don't enforce the contract at runtime. Abstract base classes
(ABC in Python, interface in .NET) fail at class definition time if a method is not
implemented — giving immediate feedback before the build even starts.
