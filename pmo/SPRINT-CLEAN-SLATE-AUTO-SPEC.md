# Sprint Clean Slate — Automated Post-Run Spec

**Document type:** Engineering Design Spec  
**Scope:** `scripts/complete_sprint.py` — automated clean-slate actions on PARTIAL/FAIL outcome  
**Status:** PROPOSED — awaiting Founder authorization before implementation  
**Author:** Platform IT Expert (INST-010), derived from WC-027 run analysis (runs 30760493431, 30780709593, 30783153552)  
**Related:** `pmo/SPRINT-CLEAN-SLATE.md` (manual runbook), ADR-039 (UDCP), ADR-013 (CI/CD)  

---

## Problem Statement

After each PARTIAL or FAIL sprint run, the runner leaves four categories of stale state that
a human operator must clean up before retrying. If a clean slate is not applied, the next run:

1. Finds an already-populated sprint branch and re-appends code to partially written files  
   (root cause of WC-027 D-1/D-2: duplicate `app = FastAPI()` + E402 + syntax error)
2. Sees `consecutive_failures > 0`, which may trigger the halt gate prematurely  
3. Leaves spec-gap GitHub issues open and potentially re-files identical ones on retry  
4. Leaves `sprint-context/` signal files carrying stale telemetry from the prior run  

**Manual clean slate takes ~5 minutes** but is error-prone and blocks the autonomous loop.  
This spec defines the changes to `complete_sprint.py` that automate steps 1–4.

---

## Decision: What to automate vs. what to keep manual

| Action | Automate? | Reason |
|---|---|---|
| Delete remote sprint branch on PARTIAL/FAIL | **YES** | Deterministic, safe, always the right action for pipeline-class failures |
| Reset `sprint_status → READY`, `consecutive_failures → 0` | **YES** | Always correct for PIPELINE_BUG error class; conditional for SPEC_GAP_GENUINE |
| Close spec-gap issues with label `error_class: PIPELINE_BUG` | **YES** | Pipeline bug fixed = issue is resolved; no Founder review needed |
| Close spec-gap issues with label `error_class: SPEC_GAP_GENUINE` | **NO** | Genuine gaps require EA/Founder review; auto-close risks losing signal |
| Reset sprint-context signal files | **YES** | Zero-risk; files are ephemeral cross-run telemetry |
| Delete partial source files from `src/` / `tests/` on main | **NO** | Destructive; requires Founder confirmation |

---

## Proposed Implementation — `scripts/complete_sprint.py`

### 1. Add `error_class` to failure-registry entries

**Current** (failure-registry.jsonl per-entry fields):
```json
{"sprint_id": "WC-027", "task_id": "WC027-01ba", "error_type": "COMPILE_GATE_FAILURE", "description": "..."}
```

**Proposed** (add `error_class` field):
```json
{
  "sprint_id": "WC-027",
  "task_id": "WC027-01ba",
  "error_type": "COMPILE_GATE_FAILURE",
  "error_class": "PIPELINE_BUG",
  "description": "..."
}
```

**Classification rule** (applied at write time in `complete_sprint.py`):

| `error_type` | `error_class` |
|---|---|
| `COMPILE_GATE_FAILURE` | `PIPELINE_BUG` |
| `LLM_BOUNDARY_VIOLATION` | `PIPELINE_BUG` |
| `ENV_VALIDATOR_FAILURE` | `PIPELINE_BUG` |
| `SPEC_GAP` (issue text mentions "no such route", "missing field") | `SPEC_GAP_GENUINE` |
| `SPEC_GAP` (issue text mentions "import", "syntax", "ruff") | `PIPELINE_BUG` |
| All others | `SPEC_GAP_GENUINE` (conservative default) |

### 2. Auto-delete sprint branch when all failures are `PIPELINE_BUG`

```python
# In complete_sprint.py — after writing failure registry
if all_failures_are_pipeline_bugs(failure_entries):
    branch = state.get("branch", "")
    if branch and branch != "main":
        result = subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log(f"🧹 Auto-deleted stale branch {branch} (all failures: PIPELINE_BUG)")
        else:
            log(f"⚠️  Branch delete failed (non-fatal): {result.stderr.strip()}")
```

**Safety constraint:** Branch is only deleted when:
- `outcome == "PARTIAL"` or `outcome == "FAIL"`
- All failure entries in this run have `error_class == "PIPELINE_BUG"`
- Branch name does not equal `main`, `develop`, or any protected pattern

If any entry is `SPEC_GAP_GENUINE`, the branch is preserved for EA review.

### 3. Auto-reset sprint state when all failures are `PIPELINE_BUG`

```python
# In complete_sprint.py — conditional reset
if all_failures_are_pipeline_bugs(failure_entries):
    update_sprint_state(
        sprint_status="READY",
        consecutive_failures=0,
    )
    log("🔄 Sprint state auto-reset to READY / 0 failures (all failures: PIPELINE_BUG)")
else:
    # Current behavior: set AUTHORIZED, increment counter
    update_sprint_state(
        sprint_status="AUTHORIZED",
        consecutive_failures=state["consecutive_failures"] + 1,
    )
```

### 4. Auto-close `PIPELINE_BUG` spec-gap issues

```python
# In complete_sprint.py — after failure registry write
for entry in failure_entries:
    if entry.get("error_class") == "PIPELINE_BUG" and entry.get("github_issue_number"):
        gh_close_issue(
            entry["github_issue_number"],
            comment=f"Pipeline defect fixed. Auto-closed by complete_sprint.py. "
                    f"Fix commit: {current_commit_sha}. Safe to retry {entry['sprint_id']}."
        )
```

Only issues filed in the SAME run are auto-closed (tracked by `github_issue_number` in the
failure-registry entry, which `complete_sprint.py` already writes on issue creation).

### 5. Auto-reset sprint-context signal files

```python
# Always reset on PARTIAL/FAIL — no conditions needed
for fname in ["monitor-signal.json", "file-failure-counts.json", "lint-violations.json"]:
    (Path("sprint-context") / fname).write_text("{}\n")
log("🧹 Sprint-context signal files cleared")
```

---

## Where in the Workflow Does This Sit?

```
autonomous-sprint.yaml
  └── dispatch sprint run
        └── udcp_orchestrator.py  ← code generation
              └── task_decomposer.py / run_compile_gate
                    └── complete_sprint.py  ← PROPOSED AUTOMATION SITE
                          ├── write failure registry
                          ├── classify error_class for each failure  [NEW]
                          ├── auto-delete stale branch (if all PIPELINE_BUG)  [NEW]
                          ├── auto-reset sprint state (if all PIPELINE_BUG)  [NEW]
                          ├── auto-close PIPELINE_BUG issues  [NEW]
                          ├── auto-clear sprint-context files  [NEW]
                          └── push PROJECT_STATE.md  (existing)
```

All new automation runs **inside the same `complete_sprint.py` call** that already handles
post-run state. No new scripts, no new workflow jobs, no new CI triggers.

---

## Acceptance Criteria

When this spec is implemented and a sprint fails with all-PIPELINE_BUG errors:

1. `gh api repos/dlai-sd/waooaw-platform/git/refs/heads/{branch}` → 404 (branch gone)  
2. `constitution/PROJECT_STATE.md` → `sprint_status: READY, consecutive_failures: 0`  
3. All spec-gap issues from this run → closed with auto-close comment  
4. `sprint-context/monitor-signal.json` → `{}`  
5. No human intervention required before retrying  

---

## Out of Scope

- Changes to `udcp_orchestrator.py` (source of root cause, already fixed separately)  
- Changes to CI workflow YAML (`autonomous-sprint.yaml`)  
- Deleting partial source artifacts from `src/` (requires Founder approval, not automatable)  
- Auto-merging sprint branch to main (constitutional gate — always requires human review)  

---

## Authorization Required

This spec changes **post-run state management behavior** in `complete_sprint.py`.  
Per INST-010 Decision Space, infrastructure changes to the SDLC pipeline require  
Founder authorization before implementation.

**Before implementing:** Present this spec to the Founder and request explicit:
> "Authorize implementation of SPRINT-CLEAN-SLATE-AUTO-SPEC.md in complete_sprint.py"

---

*Prepared by Platform IT Expert (INST-010) — Session {session-date}*  
*Evidence basis: WC-027 run logs 30760493431, 30780709593, 30783153552*  
