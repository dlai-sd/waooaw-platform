# Sprint Clean Slate Runbook

**Purpose:** Step-by-step procedure to wipe all stale state and prepare the runner for a clean fresh execution of any sprint.
**When to use:** Before re-running a sprint that previously failed, stalled, or produced partial artifacts.
**Time to complete:** ~5 minutes

---

## Fill in before starting

| Field | Value |
|---|---|
| Sprint ID | `WC-NNN` |
| Sprint title | _(e.g. WBE-S3 Markup Engine)_ |
| Branch name | `ib/009/sprint-NNN` |
| Date | YYYY-MM-DD |
| Reason for reset | _(e.g. prior run failed ANN201 ruff violations)_ |

---

## Step 1 — Verify current SPRINT_STATE_MACHINE

```bash
grep -A 10 "^## SPRINT_STATE_MACHINE" constitution/PROJECT_STATE.md
```

Expected fields to confirm / update:

```yaml
autonomous_halt: false          # must be false — runner will not start if true
platform_phase: IMPLEMENTATION  # change only if Founder authorizes a phase change
current_sprint: WC-NNN          # set to your sprint
sprint_status: READY            # READY triggers fresh-start path in runner
branch: ib/009/sprint-NNN       # runner creates this from origin/main on fresh start
consecutive_failures: 0         # reset to 0 — prevents halt gate triggering
```

**Update if needed:**
```bash
python3 scripts/sprint_state.py set \
  current_sprint WC-NNN \
  sprint_status READY \
  consecutive_failures 0 \
  autonomous_halt false \
  branch ib/009/sprint-NNN
```

---

## Step 2 — Verify WC task table (all tasks must be `pending`)

```bash
grep -E "^\| WC0" work-contracts/WC-NNN-*.md
```

All rows must end with `| pending | — |` or `| pending | |`.

**If any task shows `done`, `failed`, or `in-progress`**, reset it manually:
```bash
# Example: change 'done' back to 'pending' in the WC file
sed -i 's/| done |/| pending |/g' work-contracts/WC-NNN-*.md
# Verify no completed-at timestamps remain
grep -E "\| done \|| \| failed \|" work-contracts/WC-NNN-*.md
```

---

## Step 3 — Reset sprint-context signal files

These three files accumulate cross-run state. Reset all three to empty JSON:

```bash
echo '{}' > sprint-context/monitor-signal.json
echo '{}' > sprint-context/file-failure-counts.json
echo '{}' > sprint-context/lint-violations.json
```

> **Do NOT touch** `frozen-artifacts.json` or `platform-type-registry.json` — those
> contain foundation contracts from prior WCs that the current sprint depends on.

---

## Step 4 — Close open spec-gap issues for this sprint

Open spec-gap issues carry the label `awaiting:founder-approval`. They are informational
(the runner does not query GitHub at runtime), but they must be closed to keep audit state
clean and to avoid re-filing duplicate issues on the next run.

```bash
# List open spec-gap issues for this sprint
gh issue list --repo dlai-sd/waooaw-platform \
  --label "awaiting:founder-approval" --state open \
  --json number,title | python3 -c "
import sys, json
issues = json.load(sys.stdin)
wc = [i for i in issues if 'WC-NNN' in i['title'] or 'WCNNN' in i['title'].upper().replace('-','')]
for i in wc: print(f'  #{i[\"number\"]}: {i[\"title\"][:80]}')
print('No open issues' if not wc else f'{len(wc)} issue(s) to close')
"

# Close each — include a brief RCA note in the comment
gh issue close NNN --repo dlai-sd/waooaw-platform \
  --comment "Pipeline fix applied. Clean slate reset. Safe to retry."
```

> If the issue is a genuine spec gap (not a pipeline/infra failure), do NOT close it here.
> Escalate to EA/Founder for spec review first.

---

## Step 5 — Delete stale sprint branch (local and remote)

```bash
# Check whether the branch exists locally
git branch | grep sprint-NNN

# Delete local branch if found (runner will recreate from origin/main)
git branch -D ib/009/sprint-NNN

# Delete remote branch — removes partial UDCP artifacts from prior failed run
git push origin --delete ib/009/sprint-NNN
```

---

## Step 6 — Check for partial source artifacts on main

Prior failed runs may have committed partial files to the sprint branch but not main.
Verify main does not carry any half-implemented WC-NNN output files:

```bash
# List any WC-NNN output files already on main
git log --oneline --all -- src/ tests/ | grep -i "NNN\|wc-NNN" | head -10
```

If partial files exist **on main** (not on a sprint branch), consult Founder before removing them.
If they are only on the stale sprint branch, deleting the branch (Step 4) is sufficient.

---

## Step 7 — Commit the reset and push to main

```bash
git add sprint-context/monitor-signal.json \
        sprint-context/file-failure-counts.json \
        sprint-context/lint-violations.json \
        constitution/PROJECT_STATE.md        # only if Step 1 changed it

git commit -m "chore(sprint): reset sprint-context for WC-NNN clean fresh run

- monitor-signal.json: cleared stale prior-sprint run data
- file-failure-counts.json: cleared stale failure counts
- lint-violations.json: cleared violation cache
- SPRINT_STATE_MACHINE: WC-NNN / READY / consecutive_failures:0"

git push origin main
```

---

## Step 8 — Final verification checklist

Run each check and confirm ✓ before handing off to the runner:

```bash
# 1. State machine
python3 -c "
import re, pathlib
text = pathlib.Path('constitution/PROJECT_STATE.md').read_text()
block = re.search(r'## SPRINT_STATE_MACHINE.*?^\x60\x60\x60yaml\n(.*?)\x60\x60\x60', text, re.S | re.M)
print(block.group(1) if block else 'NOT FOUND')
"

# 2. WC task statuses — should show 0 done/failed rows
grep -cE "\| done \|| \| failed \|" work-contracts/WC-NNN-*.md || echo "0 completed tasks ✓"

# 3. Sprint-context files — should all print {}
cat sprint-context/monitor-signal.json
cat sprint-context/file-failure-counts.json
cat sprint-context/lint-violations.json

# 4. No stale local sprint branch
git branch | grep sprint-NNN && echo "WARNING: stale branch still exists" || echo "no stale branch ✓"
```

**Expected outputs:**
- `sprint_status: READY`, `consecutive_failures: 0`, `autonomous_halt: false`
- `0 completed tasks`
- All three files print `{}`
- `no stale branch ✓`

Once all four checks pass, notify the Founder: "WC-NNN ready for clean fresh run."

---

## Reference — what each file does

| File | Purpose | Reset to |
|---|---|---|
| `sprint-context/monitor-signal.json` | Live run telemetry written by runner, read by sprint monitor | `{}` |
| `sprint-context/file-failure-counts.json` | Per-file consecutive failure counter — files at ≥ 3 are auto-skipped | `{}` |
| `sprint-context/lint-violations.json` | Violation history injected into SYSTEM slot to guide next LLM call | `{}` |
| `sprint-context/frozen-artifacts.json` | Foundation interfaces from prior WCs — **never reset** | — |
| `sprint-context/platform-type-registry.json` | Cross-service type contracts — **never reset** | — |
| `constitution/PROJECT_STATE.md` §SPRINT_STATE_MACHINE | Runner control panel: halt gate, phase, sprint, branch | See Step 1 |
| `work-contracts/WC-NNN-*.md` task table | Authoritative task progress — single source of truth | All rows → `pending` |
