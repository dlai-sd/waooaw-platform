# ADR-041: Autonomous Batch Operating Model for Sprint Code Generation

## 1. Metadata
* **Date:** 2026-08-04
* **Author:** Office of the Platform IT Expert (INST-010)
* **IB Item:** IB-009 — Foundation Implementation (Gate G5)
* **Trigger:** CMMI L5 RCA session — identified systemic batch lifecycle gaps causing re-work, invisible container kills, and infra failures triggering halt thresholds

---

## 2. Status
* **Status:** Accepted

---

## 3. Context

The autonomous sprint runner executes work contracts in a fully unattended Docker container (GitHub Actions). Analysis of WC-027 and prior runs identified the following systemic batch lifecycle gaps:

**Gap 1 — Container kill leaves no footprint.**
If the GitHub Actions runner is killed (OOM, timeout, preemption) while `complete_sprint.py` has not yet run, the batch leaves no evidence: `consecutive_failures` is not incremented, `autonomous_halt` is unchanged, and the WC file still shows `pending` for all tasks. The next run cannot distinguish "never ran" from "killed mid-task."

**Gap 2 — Scaffold files written but not committed on failure.**
The UDCP pipeline writes scaffold files to disk before the compile gate. When the gate fails, the scaffold exists on disk but is not committed. The next run re-scaffolds, silently overwriting any partially valid content.

**Gap 3 — Cascade failures are invisible in the WC file.**
Tasks skipped because an upstream task failed are recorded as `pending` in the WC file — identical to tasks that were never attempted. The next run re-attempts all `pending` tasks including ones that will cascade-fail again until the root cause is fixed first.

**Gap 4 — All failure types share one counter.**
`consecutive_failures` accumulates both infrastructure failures (API timeout, rate limit) and specification failures (compile error, LLM hallucination). Infra failures should not drive the halt threshold — they are transient and self-resolving.

**Gap 5 — Good subtask work is re-executed after partial failure.**
If WC027-01a subtasks `aa` and `ab` pass but `ac` fails, the entire WC task is `failed`. The next run re-executes `aa` and `ab` from scratch — wasting LLM cost on already-correct output.

**Gap 6 — Completion protocol is not idempotent.**
If `complete_sprint.py` crashes between Step 3 (registry append) and Step 7 (git push), registry entries are locally written but not committed. Running it again double-appends entries.

---

## 4. Constitutional Basis

| Principle | Application |
|---|---|
| C-059 (Traceability) | Every run transition must be durably recorded before the next step begins |
| C-069 (Self-Improvement) | Failure evidence must accumulate correctly across runs; invisible failures break the self-improvement loop |
| C-082 (Build Validation) | Failures are evidence, not noise — they must be classified accurately to drive the right response |
| C-001 (Human Override) | `autonomous_halt` must only be set for genuine terminal failures — infra noise must not trigger it |
| C-085 (Idempotency) | Re-running any batch step must produce the same result as running it once |

---

## 5. Decision

Adopt a four-mode, checkpoint-at-task-boundary batch operating model with explicit run and task state machines, separated failure counters, and an idempotent completion protocol.

---

## 6. Run State Machine

Every autonomous batch run transitions through these states. **Each transition is written durably before the next step begins.**

```
IDLE
  │
  ├─[PLAN mode — read-only, ₹0 LLM cost]──────────────► PLANNED
  │   Validates: dependency graph satisfiable,                │
  │   C-086 SIM exists, halt=false, work exists.              │
  │   Output: work queue + estimated LLM calls.               │
  │                                                           │
  └─[EXECUTE / RESUME mode]────────────────────────────► IN_PROGRESS
      Writes: heartbeat {run_id, started_at,                  │
              expected_max_duration} on entry.                │
      On task start: writes IN_PROGRESS to WC row.            │
      On task end: writes DONE / FAILED_* / SKIPPED_*.        │
                                                              │
                                                     [CLOSE — always called,
                                                      reads heartbeat to detect
                                                      container kills]
                                                              │
                                           ┌──────────────────┼──────────────────┐
                                           │                  │                  │
                                    CLOSED_SUCCESS    CLOSED_PARTIAL    CLOSED_TERMINAL
                                    failures=0        failures++        halt=true
                                    halt=false        halt=false        escalate
                                    PR opened         resume eligible   flag_spec_gap
```

**Heartbeat detection:** At OPEN, the runner writes `{run_id, started_at}` to `sprint-context/run-heartbeat.json`. CLOSE writes `{run_id, completed_at, result}`. If the next OPEN finds `run-heartbeat.json` where `run_id` matches but `run_complete` is absent, the prior run was killed — all tasks still showing `in-progress` are reclassified as `FAILED_STRUCTURAL` and `spec_failures` is incremented.

---

## 7. Task State Machine

Seven states replace the current three (`pending | done | failed`):

```
PENDING
  │
  ├─[idempotent check: output files exist + compile gate passes]──► SKIPPED_IDEMPOTENT
  │   Zero LLM cost. Good work is never re-executed.
  │
  ├─[upstream task is FAILED_* or TERMINAL]──────────────────────► SKIPPED_CASCADE
  │   Recorded explicitly — not invisible pending.
  │   Next RESUME can skip directly to root cause.
  │
  └─[execution starts]────────────────────────────────────────────► IN_PROGRESS
      Written to WC file BEFORE LLM call.
      Container kill leaves IN_PROGRESS → detected by heartbeat.
            │
            ├─[all gates pass]────────────────────────────────────► DONE
            │
            ├─[API timeout / rate limit / network]────────────────► FAILED_TRANSIENT
            │   Retry SAME run with backoff.
            │   Does NOT increment spec_failures.
            │
            ├─[compile gate / ruff / LLM_IMPORT_VIOLATION / PTR]─► FAILED_STRUCTURAL
            │   Retry NEXT run with failure context injected.
            │   Increments spec_failures.
            │
            └─[3+ runs same error / constitutional violation]──────► FAILED_TERMINAL
                No retry. flag_spec_gap() immediately.
                Sets autonomous_halt=true.
```

---

## 8. Four Operating Modes

| Mode | LLM Cost | Writes | When to Invoke |
|---|---|---|---|
| **PLAN** | ₹0 | None | Mandatory pre-EXECUTE gate. Validates dependency graph, checks C-086 SIM, estimates LLM calls. Blocks EXECUTE if preconditions unmet. |
| **EXECUTE** | N calls (N=pending tasks) | WC file, heartbeat, src/, tests/ | Fresh sprint run — all tasks pending. |
| **RESUME** | <N calls (only non-done tasks) | WC file, heartbeat, src/, tests/ | Prior run was PARTIAL or container-killed. Reads heartbeat, reclassifies IN_PROGRESS→FAILED_STRUCTURAL, skips DONE + SKIPPED_IDEMPOTENT. |
| **CLOSE** | ₹0 | Registry, PROJECT_STATE.md, PR action | **Always called** after EXECUTE or RESUME, regardless of outcome. Idempotent — safe to call twice. |

### Mode Selection Logic

```
Run triggered →
  PLAN (always first)
    └─ PLAN PASS?
        ├─ NO  → EXIT (no LLM spend, no state change)
        └─ YES →
            └─ Prior run heartbeat found with no completion?
                ├─ YES → RESUME (reclassify IN_PROGRESS, skip done)
                └─ NO  → EXECUTE
    └─ CLOSE (always, regardless of EXECUTE/RESUME outcome)
```

---

## 9. Failure Classification and Counter Policy

Three failure classes, three separate counters, three halt policies:

| Class | Examples | Counter | Halt threshold | Retry policy |
|---|---|---|---|---|
| **TRANSIENT** | API timeout, rate limit, network blip | `infra_failures` | ≥5 consecutive | Auto-retry same run with exponential backoff. Never sets `autonomous_halt`. |
| **STRUCTURAL** | Compile gate, ruff, LLM_IMPORT_VIOLATION, PTR_GATE_FAILURE, SKIPPED_IDEMPOTENT degraded to failed | `spec_failures` | ≥3 | Retry next run. Failure context injected into next prompt. |
| **TERMINAL** | Constitutional violation, spec gap confirmed (3+ runs same error), flag_spec_gap raised | `terminal_count` | ≥1 | No retry. Immediate `autonomous_halt=true`. GitHub Issue opened. |

`autonomous_halt=true` is set **only** by TERMINAL failures. PARTIAL runs with STRUCTURAL failures leave `halt=false` so RESUME can proceed without manual intervention.

---

## 10. Error Code Reference

| Error Code | Class | Source | Expected Action |
|---|---|---|---|
| `LLM_IMPORT_VIOLATION` | STRUCTURAL | `_detect_invented_imports` post-logic-fill gate | Retry next run. Closed-world prompt constraint re-sent with scaffold imports listed. |
| `PTR_GATE_FAILURE` | STRUCTURAL | `WorkspaceSymbolIndex.validate_tis` pre-scaffold | Retry next run. Indicates TIS references a symbol not in workspace index. |
| `COMPILE_GATE_FAILURE` | STRUCTURAL | `compile()` in `_normalize_and_write` | Retry next run with failure context. Check ruff E402/B904. |
| `NORMALIZATION_INCOMPLETE` | STRUCTURAL | `_ruff_normalization_check` | Retry next run. E402 or B904 violation survived normalization pass. |
| `SCAFFOLD_ERROR` | STRUCTURAL | `Track1Scaffolder` | Retry next run. TIS artifact malformed. |
| `GROOMING_ERROR` | STRUCTURAL | `UDCPGroomingEngine` | Retry next run. Scope text parse failed. |
| `LLM_NO_RESPONSE` | TRANSIENT | LLM call after 2 attempts | Retry same run. API may be overloaded. |
| `API_TIMEOUT` | TRANSIENT | `call_llm_via_magiclm` | Retry same run with 30s backoff. |
| `RATE_LIMIT` | TRANSIENT | `call_llm_via_magiclm` | Retry same run with 60s backoff. |
| `API_SERVER_ERROR` | TRANSIENT | `call_llm_via_magiclm` | Retry same run with 30s backoff. |
| `WRITE_BOUNDARY_VIOLATION` | TERMINAL | path check in `_fill_track1_logic` | Halt immediately. LLM attempted to write outside `src/` or `tests/`. |
| `SPEC_GAP` | TERMINAL | `flag_spec_gap()` after 3 exhausted retries | Halt. Open GitHub Issue. EA/SA/Founder review required. |
| `SKIPPED_CASCADE` | n/a (not a failure) | dependency check in executor | No action. Retry automatically when root-cause task passes. |
| `SKIPPED_IDEMPOTENT` | n/a (not a failure) | output-file + compile check | No action. Good work preserved. |
| `CONTAINER_KILLED` | STRUCTURAL | heartbeat mismatch at next OPEN | Auto-detected. RESUME mode reclassifies IN_PROGRESS tasks. |

---

## 11. State Footprint by Outcome

| Outcome | WC file | PROJECT_STATE.md | failure-registry | heartbeat | PR |
|---|---|---|---|---|---|
| **SUCCESS** | all rows: `done` | `spec_failures=0`, `halt=false` | 0 new entries | `run_complete` written | Opened |
| **PARTIAL** | mix of `done`, `failed_structural`, `skipped_cascade` | `spec_failures++`, `halt=false` | STRUCTURAL entries | `run_complete` written | Closed with registry ref |
| **TERMINAL** | mix of `done`, `failed_terminal` | `terminal_count++`, `halt=true` | TERMINAL entries | `run_complete` written | Closed, GitHub Issue opened |
| **INFRA_ONLY** | `done` + `failed_transient` | `infra_failures++`, `halt=false` | TRANSIENT entries | `run_complete` written | No PR action |
| **CONTAINER_KILLED** | tasks stuck at `in-progress` | unchanged (CLOSE never ran) | nothing recorded | `run_active` present, `run_complete` absent | No PR action |

On the next OPEN after CONTAINER_KILLED, the RESUME mode detects the heartbeat mismatch, reclassifies all `in-progress` tasks as `FAILED_STRUCTURAL`, increments `spec_failures`, and proceeds as a normal RESUME.

---

## 12. Idempotent CLOSE Contract

`complete_sprint.py` must be safe to call twice with the same `run_id`. Each step checks before acting:

| Step | Idempotency check |
|---|---|
| Append to registry | Skip if `run_id` already has entries in `failure-registry.jsonl` |
| Update PROJECT_STATE | Skip if values already match intended state |
| Close PR | Skip if PR is already closed |
| Git commit | Skip if nothing staged (`git diff --cached` is empty) |
| Write `run_complete` heartbeat | Overwrite is safe (same `run_id`, same content) |

---

## 13. Implementation Priority

| Priority | Change | Benefit |
|---|---|---|
| **P0** | Write `in-progress` to WC file at task START (before LLM call) | Container kills become detectable |
| **P0** | Idempotent CLOSE: `run_id` dedup in registry + state pre-check | Eliminates inconsistent state on crash |
| **P1** | `SKIPPED_IDEMPOTENT` check before subtask: output files exist + compile gate | Eliminates re-work cost on RESUME |
| **P1** | `SKIPPED_CASCADE` status in WC file | RESUME skips known-blocked tasks without retrying them |
| **P1** | Split `infra_failures` from `spec_failures` counter | Infra noise no longer drives `autonomous_halt` |
| **P2** | PLAN mode as mandatory pre-EXECUTE gate | Zero-cost pre-flight: no wasted spend on structurally unrunnable batches |
| **P2** | RESUME mode reads heartbeat mismatch → auto-reclassifies IN_PROGRESS | Automatic recovery from container kills, no manual halt reset |

---

## 14. Alternatives Considered

**Alternative: Keep current 3-state WC file, fix only halt counter.**
Rejected. Fixing only the counter leaves Gaps 1, 2, 3, and 5 unresolved. Re-work cost and invisible container kills remain. The compound effect across 40+ sprints makes the pipeline unreliable.

**Alternative: Store all state in PROJECT_STATE.md, not the WC file.**
Rejected. PROJECT_STATE.md is the control panel (5 fields only). Task progress in the control panel collapses two concerns. The WC file is already the single source of truth for task progress — this ADR strengthens that boundary, not weakens it.

**Alternative: Persist all state to a database.**
Rejected for current phase. File-based state (WC file + heartbeat JSON) is auditable, version-controlled, and requires no new infrastructure. Database adds operational cost (ADR-011 migration burden, connection overhead in ephemeral containers) without proportional benefit at this scale.

---

## 15. Consequences

**Positive:**
- Container kills produce detectable, recoverable state.
- Good subtask work is never re-executed (estimated 40–67% LLM cost reduction on partial-run retries).
- Infra failures no longer count toward halt threshold.
- CLOSE is safe to call from retry hooks without double-writing.
- Cascade failures are visible in the WC file — root cause is immediately identifiable.

**Negative:**
- WC file gains 4 new status values (`in-progress`, `failed_structural`, `skipped_cascade`, `skipped_idempotent`). `parse_wc_tasks()` must be updated to handle them.
- Heartbeat file adds one more state surface to maintain.
- P0 changes require coordinated update to `task_decomposer.py` + `sprint_ops.py` + `complete_sprint.py`.
