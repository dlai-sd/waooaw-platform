# SIM-PL-001 — Autonomous Sprint Pipeline Health Simulation

**Type:** Pipeline Infrastructure Simulation
**Authority:** EA mandate 2026-07-23 — arising from WC-011 post-mortem (7+ runs to achieve clean execution)
**Constitutional Basis:** C-059 (Traceability), C-065 (SDLC Separation), C-066 Tier 2A, C-073 (Annotations)
**Status:** SPEC (to be run before any new sprint type is authorized for the first time)
**Owner:** Enterprise Architect (spec) · Platform IT Expert (execution)
**QA sign-off required:** Yes — QA Office reviews simulation results before sprint type is authorized

---

## Purpose

Before authorizing any new sprint type (WC-012, WC-013, etc.) for the first time, this simulation validates that the full autonomous pipeline works end-to-end for that sprint's task profile. It prevents the WC-011 pattern: 7+ failed runs in production before catching pipeline infrastructure bugs.

**The rule:** One clean SIM-PL-001 run (Grade A) per new sprint type before T0-3 equivalent authorization.

---

## Simulation Scope

SIM-PL-001 does NOT test what the tasks produce. It tests that the pipeline CAN run those tasks autonomously without human intervention.

| Area | What is tested | Pass criteria |
|---|---|---|
| **Script syntax** | All 5 pipeline scripts compile cleanly | `python3 -m py_compile` exit 0 |
| **Sprint state** | `build_sprint_index.py --dry-run` finds the correct task | task_id = WC-NNN-01, budget OK |
| **Halt check** | `autonomous_halt=false`, `platform_phase=IMPLEMENTATION` | Both confirmed via regex |
| **Docker compose** | `docker compose config --quiet` exit 0 | All required services present |
| **Required labels** | All PR labels exist on the repo | tier:2-feature, status:pr-open, awaiting:review |
| **TASK_HANDLERS** | Every task in `tasks_remaining` has a handler in `TASK_HANDLERS` | No `SKIP {task}: no handler` output |
| **PR creation** (dry-run) | `gh pr create --dry-run` would succeed | No permission errors, correct flags |
| **Sprint advancement** | `sprint_state.py advance --current WC-NNN --ib IB-009 --dry-run` works | Correct next sprint, tasks_remaining populated |

---

## Execution Protocol

### Step 1: Local dry-run (4-line pre-flight)

```bash
python3 -m py_compile scripts/autonomous_sprint_runner.py
python3 -m py_compile scripts/autonomous_sprint_reviewer.py
python3 scripts/build_sprint_index.py --dry-run
docker compose config --quiet
```

All must exit 0. If any fail: fix, verify, continue.

### Step 2: TASK_HANDLERS coverage check

```bash
python3 - <<'EOF'
from scripts.autonomous_sprint_runner import TASK_HANDLERS
from scripts.sprint_state import SPRINT_TASK_MANIFEST

sprint = "WC-012"  # Replace with target sprint
tasks = SPRINT_TASK_MANIFEST.get(sprint, [])
missing = [t for t in tasks if t not in TASK_HANDLERS]
if missing:
    print(f"FAIL: No handler for: {missing}")
else:
    print(f"PASS: All {len(tasks)} tasks have handlers")
EOF
```

### Step 3: Workflow dispatch with dry_run=true

Trigger `workflow_dispatch` with `dry_run: true`. Expected:
- Preflight: Pipeline Health Check PASS
- Execute: All tasks print `DRY RUN: would execute WC-NNN-NN` — no actual commits
- Reviewer: skipped (no PR opened in dry run)
- Report: Issue #7 updated with DRY_RUN status

### Step 4: Grade assignment

| Grade | Criteria |
|---|---|
| **A** | All 8 areas pass, dry-run completes without errors, no human intervention |
| **B** | Minor warnings (non-blocking), all gates pass, no human intervention |
| **F** | Any gate fails OR requires human intervention to proceed |

**Grade A required before authorizing the sprint for live execution.**

---

## WC-011 Retrospective (why this simulation exists)

| Run | Root Cause | Would SIM-PL-001 have caught it? |
|---|---|---|
| #22 | `tasks_remaining` list not parsed in `build_sprint_index.py` | ✅ Step 1 (`--dry-run` shows no task) |
| #24 | PR labels missing (`tier:2-feature` etc.) | ✅ Step 1 (label check) |
| #24 | gcloud binary in repo | ✅ Step 1 (`git status` check) |
| #26 | Reviewer syntax error (orphaned code) | ✅ Step 1 (`py_compile` fails) |
| #27 | GitHub Actions permissions not set | ✅ Step 3 (dry-run PR creation fails) |
| #28 | No auto-merge in reviewer | ✅ Step 3 (dry-run reviewer exits before merge — missing merge step detected) |

**Conclusion:** SIM-PL-001 would have caught all 6 root causes before run #22 ever fired.

---

## Simulation Record Template

```
Simulation:    SIM-PL-001
Sprint type:   WC-NNN
Date:          YYYY-MM-DD
Executed by:   Enterprise Architect + Platform IT Expert
Grade:         A / B / F

Step 1 (4-line pre-flight):   PASS / FAIL — [details]
Step 2 (TASK_HANDLERS):       PASS / FAIL — [missing handlers if any]
Step 3 (dry-run dispatch):    PASS / FAIL — [run number, outcome]
Step 4 (grade):               [grade] — [justification]

Human interventions required: [none / list]
Gaps found: [none / list with flag_spec_gap issue numbers]

Authorization recommendation: PROCEED / BLOCK — [reason]
```
