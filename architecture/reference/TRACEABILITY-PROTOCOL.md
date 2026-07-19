# WAOOAW Implementation Traceability Protocol

**Version:** 1.0
**Date:** 2026-07-19
**Authority:** C-073 (Bidirectional Implementation Traceability — RATIFIED), C-059 (Implementation Traceability — LAW)
**Owner:** WAOOAW AI Agent — Platform IT Expert
**Applies to:** Every implementation sprint starting with IB-009

---

## 1. The Chain Every Agent Must Know

Before writing a single line of code, the agent maps the full chain for what it is about to build:

```
Constitution (CONSTITUTION.md)
    ↓ authorises
Claims (knowledge/claims/C-NNN.md)
    ↓ expressed as
Capabilities + Architectural Drivers (knowledge/business-capabilities.md, architectural-drivers.md)
    ↓ realised by
Reference Architecture (architecture/100k/README.md, architecture/32k/README.md)
    ↓ detailed in
Component Specifications (architecture/reference/ + ADRs)
    ↓ implemented by
Source Code (src/, web/, scripts/)  ← C-073 annotation lives HERE
    ↓ validated by
Constitutional Compliance Tests (tests/constitutional/)
    ↓ proven in production by
OTel Spans (waooaw.claim_id attribute)
    ↓ recorded in
constitutional.audit_records (constitutional_basis column)
```

This chain is **bidirectional**. Starting from any node, you can navigate both up (why does this exist?) and down (where is this enforced?).

---

## 2. Pre-Code Reading Protocol (mandatory before IB-009 or any sprint)

The agent reads in this order before writing any code for a component:

```
Step 1: Read the IB item (INSTITUTIONAL_BACKLOG.md → IB-NNN)
         → What is the success criterion?
         → What are the inputs (which specs to read)?
         → Which claims are in scope?

Step 2: Read the component spec (architecture/reference/{component}/)
         → What does this component do?
         → What are its interfaces (gRPC RPCs / REST endpoints)?
         → What are its constitutional obligations?

Step 3: Read the relevant ADRs (adr/ADR-INDEX.md → follow references)
         → What technology choices are frozen?
         → What constraints apply?

Step 4: Read the claim files for every claim in scope (knowledge/claims/C-NNN.md)
         → What is the exact constitutional requirement?
         → What does the Produces: field say should exist?

Step 5: Build the local traceability map (in PR description — mandatory)
         → IB item → Component Spec → Claims → Source files I will create → CCTs I will write
```

**If any spec is missing or ambiguous after Step 5 → STOP. Raise Constitutional Blocker. Do not improvise.**

---

## 3. In-Code Annotation Patterns

### 3.1 Python (.NET 9 / Python 3.12)

Every function or class that implements a constitutional principle carries the `@constitutional` decorator (Python) or `[ConstitutionalClaim]` attribute (.NET).

**Python:**
```python
from functools import wraps
from typing import Callable

def constitutional(
    claims: list[str],
    ib_item: str,
    spec: str,
) -> Callable:
    """
    Decorator that annotates a function with its constitutional traceability chain.
    C-073: machine-readable annotation from function → claim → IB item → spec.
    
    Args:
        claims:   List of constitutional claim IDs (e.g., ["C-041", "C-003"])
        ib_item:  IB item that authorized this code (e.g., "IB-009")
        spec:     Specification file path (e.g., "architecture/reference/ce-validate-action-evaluators.md")
    """
    def decorator(fn: Callable) -> Callable:
        fn.__constitutional_claims__ = claims
        fn.__ib_item__ = ib_item
        fn.__spec__ = spec
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)
        wrapper.__constitutional_claims__ = claims
        wrapper.__ib_item__ = ib_item
        wrapper.__spec__ = spec
        return wrapper
    return decorator


# ── Usage example ──────────────────────────────────────────────────────────────

@constitutional(
    claims=["C-041", "C-003"],
    ib_item="IB-009",
    spec="architecture/reference/ce-validate-action-evaluators.md",
)
async def evaluate_tool_authorization(
    ctx: EvaluationContext,
    ct: asyncio.CancelledError,
) -> EvaluationResult:
    """
    C-041: Every MCP tool call governed by Decision Space — default deny.
    If tool_name is not in the customer's authorized_actions, DENY.
    Constitutional basis: C-041 (Tool Authorization — LAW), C-003 (Authority Licensed)
    IB: IB-009 — Foundation Implementation
    Spec: architecture/reference/ce-validate-action-evaluators.md Section C-041 Evaluator
    """
    ...
```

**C# (.NET 9):**
```csharp
/// <summary>
/// Marks a class or method as implementing a specific constitutional claim.
/// C-073: machine-readable annotation for bidirectional traceability.
/// </summary>
[AttributeUsage(AttributeTargets.Class | AttributeTargets.Method, AllowMultiple = true)]
public sealed class ConstitutionalClaimAttribute : Attribute
{
    public string[] Claims { get; }
    public string IbItem { get; }
    public string Spec { get; }

    public ConstitutionalClaimAttribute(string[] claims, string ibItem, string spec)
    {
        Claims = claims;
        IbItem = ibItem;
        Spec = spec;
    }
}

// ── Usage example ──────────────────────────────────────────────────────────────

/// <summary>
/// Evaluates whether a proposed MCP tool call is within the customer's Decision Space.
/// Constitutional basis: C-041 (Tool Authorization — LAW), C-003 (Authority Licensed)
/// IB: IB-009 — Foundation Implementation
/// Spec: architecture/reference/ce-validate-action-evaluators.md § C-041 Evaluator
/// </summary>
[ConstitutionalClaim(
    claims: new[] { "C-041", "C-003" },
    ibItem: "IB-009",
    spec: "architecture/reference/ce-validate-action-evaluators.md")]
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-041";
    // ...
}
```

**TypeScript:**
```typescript
/**
 * @constitutional C-001, C-068
 * @ib IB-009
 * @spec architecture/reference/steward-interface.md
 *
 * Emergency Stop button — always visible, always keyboard-reachable.
 * Constitutional basis: C-001 (Human Override cannot be blocked by UI design)
 */
export const EmergencyStopButton: React.FC<EmergencyStopButtonProps> = ({ sessionId, onStopped }) => {
  ...
};
```

**SQL (migration files):**
```sql
-- constitutional_basis: C-005, C-007, C-027
-- ib_item: IB-009
-- spec: architecture/reference/data-architecture/ledger-design.md
-- Purpose: Constitutional Audit Ledger — append-only evidence store
CREATE TABLE IF NOT EXISTS constitutional.audit_records (
    ...
    constitutional_basis VARCHAR(500) NOT NULL  -- always populated (C-073)
);
```

### 3.2 File-Level Header (mandatory for ALL files in src/)

Every source file starts with a constitutional header comment:

```python
# ============================================================
# constitutional_basis: C-041, C-043, C-048, C-049, C-051, C-062
# ib_item:              IB-009
# spec:                 architecture/reference/ce-validate-action-evaluators.md
# component:            Constitutional Engine
# purpose:              Evaluator registry — routes ValidateAction to correct claim evaluator
# ============================================================
```

```csharp
// ============================================================
// constitutional_basis: C-023, C-041
// ib_item:              IB-009
// spec:                 architecture/reference/components/constitutional-engine.md
// component:            Constitutional Engine
// purpose:              Evidence First enforcer — validates RecordEvidence call sequence
// ============================================================
```

---

## 4. PR Traceability Template (mandatory PR description section)

Every PR that adds or modifies code in `src/`, `web/`, or `scripts/` must include this section:

```markdown
## Traceability Chain

| Layer | Reference |
|---|---|
| **IB Item** | IB-009 Foundation Implementation |
| **Constitutional Claims** | C-041 (Tool Authorization), C-043 (Financial Ceiling) |
| **Component Spec** | architecture/reference/ce-validate-action-evaluators.md |
| **ADRs** | ADR-001 (gRPC), ADR-020 (MCP pattern) |
| **Source files** | src/constitutional-engine/Evaluators/C041Evaluator.cs |
| **CCTs added** | CCT-CE-01 (C-041 tool authorization deny), CCT-CE-02 (C-043 budget breach deny) |
| **OTel span** | waooaw.ce.validate_action with waooaw.claim_id attribute |
| **DB column** | constitutional.audit_records.constitutional_basis |

## Constitutional Impact

If C-041 is amended → this PR's files need review: `src/constitutional-engine/Evaluators/C041Evaluator.cs`
```

---

## 5. IB-009 Work Contract — Pre-Filled Traceability Template

When IB-009 begins, the agent creates a Work Contract with this structure:

```markdown
# Work Contract — IB-009 Foundation Implementation

**Sprint:** IB-009
**Office:** WAOOAW AI Agent — Platform IT Expert
**IB Item:** IB-009 — Foundation Implementation (Gate G5)

## Pre-Code Traceability Map

| Component | Spec | Claims in scope | ADRs |
|---|---|---|---|
| Constitutional Engine — CE skeleton | architecture/reference/components/constitutional-engine.md | C-001, C-003, C-007, C-023, C-027 | ADR-001, ADR-007 |
| CE — ValidateAction 6 evaluators | architecture/reference/ce-validate-action-evaluators.md | C-041, C-043, C-048, C-049, C-051, C-062 | ADR-001, ADR-020 |
| Business Platform — skeleton | architecture/reference/components/business-platform.md | C-005, C-033, C-034, C-038 | ADR-002, ADR-003, ADR-006 |
| Professional Runtime — skeleton | architecture/reference/components/professional-runtime.md | C-001, C-018, C-025 | ADR-004, ADR-005, ADR-015 |
| AI Runtime — skeleton + PSE | architecture/reference/ce-validate-action-evaluators.md + steward-interface.md | C-051, C-062, C-068 | ADR-024, ADR-028, ADR-029 |
| DB migrations 01-08 | infrastructure/postgres/init/ | C-005, C-007, C-027 | ADR-011 |

## Sprint Sequence (dependency order — C-073 + constitutional dependency chain)

```
Week 1: DB migrations → Keycloak realm → CE skeleton (all CCT-EF + CCT-HO pass)
Week 2: BP skeleton (multi-tenant JWT, registration endpoint)
Week 3: PR skeleton (PAAS sessions, Emergency Stop WebSocket)
Week 4: AIR skeleton (PSE + LLM gateway stub) + Web skeleton
```

## Definition of Done (per C-071 Gate 2)

- [ ] `docker compose up` — all services healthy
- [ ] CCT-EF-01 PASS (Evidence First in dev)
- [ ] CCT-HO-01 PASS (Emergency Stop ≤250ms in dev)
- [ ] CCT-CE-01 to CCT-CE-10 PASS (ValidateAction 6 evaluators)
- [ ] CCT-MT-01 PASS (multi-tenant isolation)
- [ ] All source files have constitutional headers (C-073 scanner passes)
- [ ] PR traceability section complete for every PR in this sprint
```

---

## 6. CI Traceability Scanner (Gate addition)

The code-quality.yaml workflow gets a new job that scans for C-073 compliance:

```yaml
# Excerpt from .github/workflows/code-quality.yaml
traceability-scan:
  name: C-073 Traceability annotation scan
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - name: Scan changed source files for constitutional headers
      run: python scripts/scan-traceability.py --changed-only
```

`scripts/scan-traceability.py` reads every changed `.cs`, `.py`, `.tsx` file and verifies the constitutional header is present. If a file is in `src/` and has no header → warning (not block, until existing files are annotated).

For **amendment detection**: when a `knowledge/claims/C-0NN.md` file is changed in a PR, the scanner also outputs: "This claim is tagged in: [list of source files]" — so the reviewing agent immediately knows what code to check.

---

## 7. Audit Record Traceability (Runtime)

Every `constitutional.audit_records` row carries the traceability chain into the database:

```sql
-- The constitutional_basis column is already defined.
-- C-073 mandates it is ALWAYS populated (never NULL, never empty string).
-- Value format: "C-041"  or  "C-041, C-003"  (comma-separated for multi-claim)

-- Example record written by C041Evaluator:
INSERT INTO constitutional.audit_records (
    session_id, tenant_id, record_type,
    constitutional_basis,   -- C-073 mandatory
    action_type, decision,
    evidence_key
) VALUES (
    $1, $2, 'VALIDATION_AUTHORIZED',
    'C-041',                -- Explicit claim — bidirectional trace to code
    'MCP_TOOL_CALL', 'AUTHORIZED',
    gen_random_uuid()
);
```

This means: given an audit record, you can navigate to the claim, then to the source file, then to the spec, then to the constitution. The chain is complete in both directions.

---

## 8. Quick Reference: What Goes Where

| Traceability layer | Where it lives | Format |
|---|---|---|
| "Why does this IB item exist?" | INSTITUTIONAL_BACKLOG.md → IB-NNN | Depends On + Constitutional Claims |
| "What spec authorises this code?" | File header comment (every .cs/.py/.tsx in src/) | `# spec: architecture/reference/...` |
| "Which claims does this function enforce?" | Method/class annotation | `@constitutional(claims=["C-041"])` |
| "Which IB item authorized this function?" | Method/class annotation | `ib_item="IB-009"` |
| "Which code implements C-041?" | CI scanner output + GitHub search `@constitutional.*C-041` | Automated |
| "If C-041 is amended, what changes?" | CI amendment detector (claim file changed → code list surfaced) | Automated |
| "Did this action comply with C-041?" | constitutional.audit_records.constitutional_basis | Runtime DB row |
| "What was the runtime behavior?" | OTel span: waooaw.claim_id = "C-041" | Azure Monitor |
