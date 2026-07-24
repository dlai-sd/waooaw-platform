# SIM-PL-002 — Sprint Task Content Simulation Template

**Simulation type:** Sprint Task Content (code generation approach validation)
**Authority:** C-086 (Pre-Execution Simulation Obligation — RATIFIED 2026-07-24)
**Constitutional basis:** C-059, C-071, C-082, C-086
**Format version:** 1.0
**Complements:** SIM-PL-001 (pipeline infrastructure) — that checks the pipeline CAN run;
  this checks the approach WILL produce correct code.

---

## How to Use This Template

Copy this file to `simulation/SIM-PL-002-{task_id}-simulation.md`.
Fill in every section. Run the simulation steps locally.
Record the verdict honestly. Submit for review BEFORE the first LLM call.

**Rule (C-086):** No first-attempt LLM call until Verdict: PASS is recorded and reviewed.
**Rule (C-071):** If this simulation reveals a design gap, fix the design — not the simulation.

---

## Section 1: Task Identity

| Field | Value |
|---|---|
| **Task ID** | `WC0XX-NN` |
| **Description** | One sentence: what this task produces |
| **Sprint** | WC-0XX |
| **Spec source** | `architecture/reference/...` section to verify |
| **Simulation author** | Enterprise Architect or Platform IT Expert |
| **Date** | YYYY-MM-DD |

---

## Section 2: Acceptance Criteria (written BEFORE simulation, never after)

*What does success look like? Be specific. These are the criteria the simulation must prove.*

| Criterion ID | Criterion | Pass condition |
|---|---|---|
| AC-01 | [what the task must produce] | [verifiable condition] |
| AC-02 | [e.g., "all generated files compile"] | `dotnet build` exit 0 |
| AC-03 | [e.g., "no cross-file namespace inconsistency"] | zero CS0246 errors |
| AC-04 | [e.g., "CCTs pass against generated code"] | `dotnet test` exit 0 |

---

## Section 3: Dependency Map

*Every file this task generates, in the order it must be generated. Mark dependencies explicitly.*

```
Layer 0 (no dependencies — generate first):
  - path/to/file_A.cs   (namespace: Waooaw.X.Layer0)
  - path/to/file_B.cs   (namespace: Waooaw.X.Layer0)

Layer 1 (depends on Layer 0 — generate second, after Layer 0 compiles):
  - path/to/file_C.cs   (uses: Layer0.TypeA, Layer0.TypeB)

Layer 2 (depends on Layer 1 — generate third):
  - tests/path/Test.cs  (uses: Layer0.TypeA, Layer1.ServiceX)
```

**Red flags to catch here (not at runtime):**
- Any layer referencing a type from a LATER layer → dependency cycle → redesign required
- Any file that both DEFINES a type and USES another type from the same generation call → inconsistency risk
- More than 3 layers → consider splitting into separate WC sub-tasks

---

## Section 4: Controlled Simulation Scenario

*What exactly will the LLM receive? No approximations. Use the actual spec sections.*

**4.1 Spec sections (exact):**
```
Copy the exact TASK_CONTEXT_MAP entry for this task.
These are the actual spec sections Claude will read.
```

**4.2 Branch context (exact):**
```
List every .cs file currently on the sprint branch.
This is what EXTEND-NOT-REPLACE will show Claude.
If no branch exists yet: state "branch: empty".
```

**4.3 Constitutional check (exact):**
```
Copy the exact constitutional_check string from TASK_HANDLERS.
This is the instruction Claude will receive after the spec.
```

**4.4 Critical type names (verify before LLM call):**
```
List every proto-generated type this task's code will reference.
Verify each exists in the .proto file with the correct name.
Example:
  EmergencyStopResponse → proto field 1: emergency_stop_record_id (string)
  ValidationDecision → enum values: VALIDATION_DECISION_ALLOW (not ActionDecision.Allow)
```

---

## Section 5: Simulation Execution

*Run each step manually. Record the actual output. Do not adjust acceptance criteria based on results.*

**Step 1: Dependency structure verification**
```bash
# Verify every type referenced in Layer 1+ exists in Layer 0 output
# Run manually or use a script
```
Result: [ ] PASS  [ ] FAIL
Notes:

**Step 2: Controlled code skeleton build**
Build the Layer 0 files as templates (exact namespace, exact class names, empty bodies).
Verify they compile before proceeding to Layer 1.
```bash
# Copy templates to /tmp/simulation/
# dotnet build /tmp/simulation/
```
Result: [ ] PASS  [ ] FAIL
Error output (if any):

**Step 3: Layer 1 integration verification**
Using the compiled Layer 0 output as context, verify Layer 1's type references are correct.
```bash
# Add Layer 1 file to /tmp/simulation/
# dotnet build /tmp/simulation/
```
Result: [ ] PASS  [ ] FAIL
Error output (if any):

**Step 4: Constitutional check adequacy review**
Read the constitutional_check string. For each type name referenced in the check,
verify it exists in the proto file. For each "DO NOT" instruction, verify it
addresses the actual error patterns seen in prior runs.
```
Review checklist:
[ ] Every type name in the check matches the actual proto/spec name
[ ] EXTEND-NOT-REPLACE specifies the exact files already on the branch
[ ] Namespace instructions name the correct generated namespace (not invented)
```
Result: [ ] PASS  [ ] FAIL
Gaps found:

---

## Section 6: Gap Analysis

*Document every deviation from the acceptance criteria. State the root cause and required fix.*

| AC ref | Gap found | Root cause | Required fix before proceeding |
|---|---|---|---|
| AC-NN | [what failed] | [why it failed] | [exact change needed] |

---

## Section 7: Verdict

```
VERDICT: [ ] PASS  [ ] FAIL

If PASS: LLM call for this task is constitutionally authorized. (C-086)
If FAIL: Fix every gap in Section 6. Re-run simulation. Do not proceed with LLM call.

Date:
Reviewed by:
```

---

## Section 8: Lessons for Pipeline Improvement

*Document anything the simulation revealed about the pipeline design that should be improved.*

| Finding | Implication | IB item needed? |
|---|---|---|
| [what the simulation found] | [what this means for the pipeline] | [yes/no + brief description] |

---

*This template implements C-086 (Pre-Execution Simulation Obligation).*
*Every field is mandatory. Empty fields = simulation incomplete = FAIL by default.*
