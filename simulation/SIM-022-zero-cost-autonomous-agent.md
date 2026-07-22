# SIM-022 — Zero-Cost Autonomous Agent Full Cycle Simulation

**Type:** Platform Internal Simulation — Autonomous Execution
**Date:** 2026-07-22
**Requested by:** Founder (Yogesh Khandge)
**Executed by:** WAOOAW AI Agent — Platform IT Expert
**Constitutional basis:** C-066 (Authorization Tiers), C-070 (Third Instinct), C-071 (Quality), C-076 (Coverage)

**Purpose:** Simulate a zero-cost AI model (GitHub Models free tier — llama-3.1-8b, 8K context window, zero token cost) running the full autonomous sprint cycle. Identify every point of failure, drift, and derailment before we commit to the implementation phase.

**Model profile (simulated):**
- Model: `meta/llama-3.1-8b-instruct` via GitHub Models API (free tier, GITHUB_TOKEN authentication)
- Context window: 8,192 tokens hard limit
- Capability: Code generation, instruction following — weak on multi-step constitutional reasoning
- Cost: ₹0 for spec/governance tasks; ₹0 for simple code scaffolding
- Availability: Free with any GitHub account, no billing required

---

## Simulation Run — SPEC Phase (Current State)

### Step 1: GitHub Actions cron trigger fires (0:00)

```
Trigger: schedule cron '0 */2 * * *'
Job: preflight
```

**What happens:**

Preflight reads `constitution/PROJECT_STATE.md` SPRINT_STATE_MACHINE.

**RESULT: HALTED correctly.**
```
autonomous_halt: true  → preflight exits halt=true
execute job: skipped (condition: needs.preflight.outputs.halt == 'false')
```

**Grade: PASS.** The platform_phase=SPEC + AUTONOMOUS_HALT=true gates work. No implementation runs.

---

## Simulation Run — IMPLEMENTATION Phase (Future State, post-Founder authorization)

*Simulating what happens after Founder sets platform_phase: IMPLEMENTATION and autonomous_halt: false.*

### Step 1: GitHub Actions cron trigger fires

```
Trigger: schedule cron
Preflight: checks autonomous_halt: false ✓, platform_phase: IMPLEMENTATION ✓
Sprint Index built for WC011-04 (src/ scaffold)
model_hint: reasoning (WC011-04 is architecture decision)
```

### Step 2: Execute job starts — autonomous_sprint_runner.py runs

Runner reads PROJECT_STATE.md, extracts SPRINT_STATE_MACHINE.

```
autonomous_halt: false ✓
platform_phase: IMPLEMENTATION ✓
current_sprint: WC-011
tasks_remaining: [WC011-01, WC011-02, WC011-03, WC011-04, WC011-05, WC011-07]
```

`check_platform_phase_gate()` passes. Runner selects first task: **WC011-01** (docker-compose validation).

### Step 3: WC011-01 — docker-compose.yml validation

This task is **pure Python, no LLM needed.** Runner executes:
```bash
docker compose -f docker-compose.yml config
```

**RESULT: PASS.** No model needed, zero cost, deterministic.

---

### Step 4: WC011-04 — src/ directory scaffold (architecture decision)

Runner reads `sprint-context/index.json`:
```json
{
  "model_hint": "reasoning",
  "spec_files": [
    "architecture/reference/components/constitutional-engine.md",  // 1,289 tok
    "architecture/reference/components/business-platform.md",      // 1,795 tok
    "architecture/reference/components/professional-runtime.md",   // 1,478 tok
    "architecture/reference/components/ai-runtime.md",             // 11,575 tok ← CRITICAL OVERFLOW
    "standards/CODING-STANDARDS.md",                               // 7,048 tok ← OVERFLOW
    "standards/runtime-professional.md"                            // 1,860 tok
  ]
}
```

Model receives prompt + all spec files. Total context: **25,045 tokens + BOOTSTRAP + AGENT-ENTRY**.

**GAP-SIM-01: FATAL CONTEXT OVERFLOW**
- llama-3.1-8b: 8,192 token limit. Total task context = ~25k tokens.
- Model receives first 8K tokens only: BOOTSTRAP.md header + first half of AGENT-ENTRY.md.
- Model **never sees any spec file content** — everything overflows.
- Output: Generic src/ scaffold with no constitutional headers. Missing C-059 traceability.
- **Derailment: Model produces code that looks correct but references wrong spec paths.**

---

### Step 5: WC012-01 — CE skeleton (future sprint)

Model would receive:
```
BOOTSTRAP (7,057) + AGENT-ENTRY (3,438) + spec files (34,904) = 45,399 tokens
```

**GAP-SIM-02: CATASTROPHIC OVERFLOW — 45K tokens into an 8K model**
- Model sees: BOOTSTRAP header + AGENT-ENTRY platform state block only.
- All spec files: invisible to model.
- Output: Model hallucinates a .NET service based on its training data, not WAOOAW specs.
- Constitutional headers: fabricated claim numbers (e.g., writes `// C-001` where `C-023` is correct).
- Proto definitions: invented, not matching `constitutional_service.proto`.
- Tests: likely omitted (model never saw QA-STRATEGY.md with coverage requirement).
- **Derailment: Code looks syntactically correct but is constitutionally wrong.**

---

### Step 6: CI runs against WC012-01 output

Assuming CI catches some issues:
- `buf lint`: FAIL — proto definitions don't match spec
- `dotnet-coverage check --minimum-coverage-lines 90`: FAIL — no tests written (C-076 violation)
- `commitlint`: FAIL — commit message lacks `CCTs-added:` field (C-059)
- `scan-traceability.py`: FAIL — `# Implements:` header points to wrong spec path

**GAP-SIM-03: CI fails but runner doesn't know why**
- `consecutive_failures` increments to 1.
- Next 2h run: same model, same context, same overflow → same failures.
- At 3 failures: `consecutive_failures: 3` → HALT triggered (C-001).
- **Derailment: Infinite loop at ≤₹0 cost, but wastes 3 GitHub Actions runs and 6 hours.**

---

### Step 7: Preflight platform_phase check (current gap)

**GAP-SIM-04: Preflight doesn't check platform_phase**

Current preflight YAML extracts `autonomous_halt` and `consecutive_failures` but NOT `platform_phase`. If `autonomous_halt: false` but `platform_phase: SPEC`, the preflight passes halt=false, execute job starts, runner then exits via `check_platform_phase_gate()`. Correct behavior — but wastes GitHub Actions minutes spinning up the execute runner before the Python gate fires.

Fix: Check platform_phase in preflight before launching the execute job.

---

### Step 8: Index references missing file

**GAP-SIM-05: `architecture/reference/data-architecture.md` MISSING**

WC011-02 task in `build_sprint_index.py` references this file:
```python
"spec_files": ["architecture/reference/data-architecture.md", ...]
```
File does not exist. Index entry shows `[NOT YET CREATED]`. A zero-cost model reading this annotation may:
- Skip the task (correct)
- Try to create the file (wrong — out of scope)
- Hallucinate the data architecture (catastrophically wrong)

---

### Step 9: NEXT SESSION OPTIONS is stale

**GAP-SIM-06: Stale operational instructions in PROJECT_STATE.md**

The NEXT SESSION OPTIONS block still says:
```
Check: correct tasks identified, AUTONOMOUS_HALT: false confirmed, no side effects
```

But AUTONOMOUS_HALT is now TRUE. A new agent reading this block will be confused about expected state. Small models particularly vulnerable to "expected: X, actual: Y" confusion.

---

## Gap Register

| ID | Severity | Description | Root Cause |
|---|---|---|---|
| GAP-SIM-01 | CRITICAL | ai-runtime.md is 11,575 tokens — overflows 8K model alone | No file size limit in sprint index |
| GAP-SIM-02 | CRITICAL | WC012-01 total context = 45K tokens — model sees 0 spec content | Index returns full files, not sections |
| GAP-SIM-03 | HIGH | CI failures cause 3-run loop before HALT — 6 hours wasted | No pre-commit validation in runner |
| GAP-SIM-04 | MEDIUM | Preflight doesn't check platform_phase — execute job launches needlessly | Inline Python extracts only halt + failures |
| GAP-SIM-05 | HIGH | data-architecture.md missing — WC011-02 index reference is broken | File not yet created; no existence check |
| GAP-SIM-06 | MEDIUM | NEXT SESSION OPTIONS stale — contradicts current HALT=true state | Session notes not updated after gap fixes |
| GAP-SIM-07 | HIGH | No C-077 constitutional claim exists yet — IB-020 references it | Claim ratification deferred; agents may cite non-existent C-077 |
| GAP-SIM-08 | MEDIUM | No SPEC-phase tasks defined for runner — agent does nothing during SPEC phase | Runner exits immediately; no spec validation work possible |

---

## Fixes Applied (post-simulation)

See commit trail for implementation of each fix:
- GAP-SIM-01/02: `scripts/build_sprint_index.py` — section targeting, per-file token budget, total budget gate
- GAP-SIM-04: `.github/workflows/autonomous-sprint.yaml` — platform_phase check in preflight
- GAP-SIM-05: `scripts/build_sprint_index.py` — existence check with fallback spec
- GAP-SIM-06: `constitution/PROJECT_STATE.md` — NEXT SESSION OPTIONS updated
- GAP-SIM-07: `knowledge/index.md` — C-077 DRAFT claim added; pending Founder ratification
- GAP-SIM-08: `scripts/autonomous_sprint_runner.py` — SPEC-phase spec validation mode added
- GAP-SIM-03: `scripts/autonomous_sprint_runner.py` — pre-commit header validation added

---

## Grade

| Dimension | Grade | Notes |
|---|---|---|
| SPEC phase safety | A | HALT + platform_phase gate works correctly |
| IMPLEMENTATION phase readiness (current) | D | Context overflow fatal for free models; would derail on first non-trivial task |
| IMPLEMENTATION phase readiness (post-fix) | B | With section targeting and size limits, free model can handle WC011 tasks. WC012+ needs reasoning model for code authoring. |
| Constitutional compliance | B | C-076/C-059/C-073 checks present but no pre-commit validator yet |
| Cost profile | A | SPEC phase: ₹0. WC011 (rule-based tasks): ₹0. WC012+: ₹0 for auto tasks via GitHub Models free tier |
