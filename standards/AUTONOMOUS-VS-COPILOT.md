# When to Use Autonomous Pipeline vs. Copilot Session

**Authority:** Enterprise Architect (INST-003)
**Constitutional Basis:** C-066 Tier 2A, C-070, C-077, ADR-030
**Status:** ACTIVE — 2026-07-30

---

## One-Sentence Rule

> **C-070 Third Instinct: Autonomous execution is the default. A Copilot session is the exception. If you are reaching for a Copilot session to write production code, stop — that code belongs in the pipeline.**

---

## Decision Tree

```
Does the output go into src/, tests/, infrastructure/, or web/?
├── YES → PIPELINE (autonomous-sprint.yaml → execute job)
│         Exceptions NEVER APPLY to this case.
└── NO → continue...

Is the output a sprint SubTaskDef, SPRINT_TASK_MANIFEST entry,
or _SERVICE_SCOPE / _TASK_STACK_MAP mapping?
├── YES → PIPELINE via groom_sprint.py in preflight
└── NO → continue...

Is the output a pipeline script fix (scripts/*.py, autonomous-sprint.yaml)?
├── YES → Copilot session (pipeline scripts bootstrap themselves)
└── NO → continue...

Is the output a constitutional document?
(constitution/, adr/, standards/, reviews/, simulation/)
├── YES → Copilot session in the appropriate constitutional office
└── NO → continue...

Is the output data that requires real-time founder judgment?
(FOUNDER-ACTIONS.md, GENESIS.md, CONSTITUTION.md amendments)
├── YES → Founder action only (no agent)
└── NO → default to PIPELINE
```

---

## PIPELINE — Autonomous Sprint (`autonomous-sprint.yaml`)

**Use when:**
- Implementing sprint tasks that produce files in `src/`, `tests/`, `web/`, `infrastructure/`
- Running structured LLM code generation with constitutional gates
- Any task where C-086 simulation evidence exists (SIM-PL-002 PASS)

**Constitutional authorization:** C-066 Tier 2A (Authorized for execution when ALL gate checks pass)

**How it works:**
1. Founder pushes `WC-NNN-*.md` to main
2. Founder triggers `workflow_dispatch(sprint_name=WC-NNN)`
3. Preflight: halt check → groom_sprint.py → index build → SIM gate
4. Execute: PIPELINE SYNC → SubTaskDef chain → compile gate → PR
5. Review: autonomous_sprint_reviewer.py approves PR (C-065)
6. Merge: CODEOWNERS approval (always human gate)

**When the pipeline halts:**
- `autonomous_halt: true` → human override (C-001)
- `consecutive_failures >= 3` → SPEC_GAP or INFRA failure mode
- Missing SIM-PL-002 file → preflight refuses to proceed (C-086)

---

## COPILOT SESSION — Agent-Assisted (This Conversation)

**Use when:**
- Writing or fixing pipeline scripts (`scripts/*.py`)
- Writing or fixing the workflow YAML (`.github/workflows/autonomous-sprint.yaml`)
- Grooming new sprints (the `groom_sprint.py` script runs in pipeline but must be authored here)
- Writing Work Contracts (`work-contracts/WC-NNN-*.md`)
- Writing constitutional documents (constitution/, adr/, standards/)
- Emergency remediation: pipeline halted, direct fix needed
- Drafting PRs for review/approval

**Constitutional authorization:** C-066 Tier 1 (Copilot as advisory and authoring tool — NOT production implementation)

**Critical constraint:** A Copilot session MUST NOT be the primary path for producing implementation code in `src/`. If you've written service code in a Copilot session, it must be committed through the branch + PR flow and still gate through `CODEOWNERS`.

---

## Why Not Always Copilot?

The question "can I just do this in a Copilot session?" has a structural answer rooted in three constitutional principles:

### C-070 — Third Instinct

*"Autonomous execution is the primary production path, not the exception."*

Copilot sessions are context-dependent, bounded by token budgets, and terminate. The autonomous pipeline runs on a cron schedule, is git-native, produces auditable commits, and has constitutional gates (C-082 build gate, C-086 simulation, C-084 dependency chain). These properties are architectural requirements, not conveniences.

### C-077 — FinOps

Copilot sessions on the Claude Sonnet tier cost approximately 10× more per implementation token than a Haiku-backed pipeline execution. Grooming, index building, and structural analysis use Haiku. Implementation uses Sonnet. Frontier models (Opus) are prohibited for implementation.

### C-059 — Traceability

Every production file produced by the pipeline has `SubTaskDef.wc_task_id` linking it to the authoritative PMO spec. Files produced in ad hoc Copilot sessions break this chain unless manually recorded.

---

## Evidence from WC-012 to WC-026

| Period | Mode | Compile success rate | Avg attempts/task |
|---|---|---|---|
| WC-012 to WC-015 (no skeleton) | Pipeline | 43% first-attempt | 3.2 |
| WC-025 to WC-026 (with skeleton) | Pipeline | ~90% first-attempt | 1.3 |
| Emergency fixes (B-1..B-4) | Copilot | Immediate | 1.0 |

**Conclusion:** Skeleton (ADR-036) closes the gap between Copilot's interactive advantage and pipeline efficiency. For sprints with complete EA skeletons, pipeline performance is structurally superior.

---

## Cross-References

- `standards/AUTONOMOUS-PIPELINE-STANDARD.md` — complete pipeline spec
- `constitution/BOOTSTRAP.md §MODE B` — autonomous agent operating protocol
- `ADR-030` — autonomous sprint code generation
- `ADR-036` — blueprint-first skeleton standard
- `ADR-016` — service language selection (per-service stack determines SubTaskDef compile_gate)
