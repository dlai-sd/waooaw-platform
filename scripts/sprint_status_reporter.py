#!/usr/bin/env python3
"""
sprint_status_reporter.py
Posts a status comment to the Sprint Dashboard GitHub Issue (#7) after every run.
constitutional_basis: C-001 (human override — founder must be able to see status 24/7)
"""
import os, sys, json, requests
from datetime import datetime, timezone

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO         = os.environ.get("GITHUB_REPO", "dlai-sd/waooaw-platform")
TASK_ID      = os.environ.get("SPRINT_TASK_ID", "unknown")
RESULT       = os.environ.get("SPRINT_RESULT", "")        # SUCCESS | FAILED | SKIPPED | HALTED
PR_NUMBER    = os.environ.get("SPRINT_PR_NUMBER", "")
HALT_REASON  = os.environ.get("SPRINT_HALT_REASON", "")
EXISTING_PR  = os.environ.get("SPRINT_EXISTING_PR", "")
RUN_ID       = os.environ.get("GITHUB_RUN_ID", "")
PLATFORM_PHASE = os.environ.get("PLATFORM_PHASE", "SPEC")

DASHBOARD_ISSUE = 7  # The Sprint Dashboard issue number
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
BASE    = f"https://api.github.com/repos/{REPO}"

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
run_url = f"https://github.com/{REPO}/actions/runs/{RUN_ID}"

# ── Build the comment body ────────────────────────────────────────────────────
if PLATFORM_PHASE != "IMPLEMENTATION":
    status_line  = "⏸ **Platform in SPEC phase** — implementation not authorized yet"
    action_line  = "**Your action:** Say _'Yogesh authorizes IB-009 Sprint 011 implementation'_ to start."
    label_to_set = "sprint:waiting"

elif RESULT == "SUCCESS" and PR_NUMBER:
    status_line  = f"✅ **Task complete** — PR [#{PR_NUMBER}](https://github.com/{REPO}/pull/{PR_NUMBER}) opened"
    action_line  = "**Your action:** None — the autonomous reviewer is checking the PR."
    label_to_set = "sprint:pr-open"

elif RESULT == "SKIPPED" and EXISTING_PR:
    status_line  = f"⏸ **Waiting for review** — PR [#{EXISTING_PR}](https://github.com/{REPO}/pull/{EXISTING_PR}) is open"
    action_line  = "**Your action:** None — waiting for the PR reviewer to approve and merge."
    label_to_set = "sprint:waiting"

elif RESULT == "HALTED" or "halt" in HALT_REASON.lower():
    status_line  = f"🔴 **Sprint halted** — {HALT_REASON or 'see logs'}"
    action_line  = f"**Your action:** Check the [run logs]({run_url}) and the FOUNDER-ACTION.md file in the repo."
    label_to_set = "sprint:halted"

elif RESULT == "FAILED":
    status_line  = "❌ **Run failed** — infrastructure or code error"
    action_line  = f"**Your action:** Check the [run logs]({run_url}). If this keeps happening, tell Copilot: 'The sprint is failing, please investigate'."
    label_to_set = "sprint:halted"

else:
    status_line  = f"ℹ️ Status: {RESULT or 'unknown'}"
    action_line  = f"**Your action:** Check [run logs]({run_url})"
    label_to_set = "sprint:waiting"

comment = f"""---
### Sprint Run — {now}

**Task:** `{TASK_ID}`
**{status_line}**

{action_line}

<details><summary>Technical details</summary>

- Run: [{RUN_ID}]({run_url})
- Platform phase: `{PLATFORM_PHASE}`
- Result: `{RESULT or 'n/a'}`

</details>"""

# ── Post comment ──────────────────────────────────────────────────────────────
resp = requests.post(f"{BASE}/issues/{DASHBOARD_ISSUE}/comments",
                     headers=HEADERS, json={"body": comment})
if resp.status_code not in (200, 201):
    print(f"Warning: Could not post comment: {resp.status_code} {resp.text[:200]}")
    sys.exit(0)  # Don't fail the workflow for a reporting error
else:
    print(f"✅ Posted status to issue #{DASHBOARD_ISSUE}")

# ── Update issue labels ───────────────────────────────────────────────────────
# Remove all sprint: labels, add the new one
sprint_labels = ["sprint:running","sprint:pr-open","sprint:halted","sprint:waiting","sprint:done","founder-action-needed"]
current = requests.get(f"{BASE}/issues/{DASHBOARD_ISSUE}", headers=HEADERS).json()
current_labels = [l["name"] for l in current.get("labels", [])]
new_labels = [l for l in current_labels if l not in sprint_labels] + [label_to_set]
if "FAILED" in RESULT or "HALTED" in (RESULT or ""):
    new_labels.append("founder-action-needed")

requests.patch(f"{BASE}/issues/{DASHBOARD_ISSUE}", headers=HEADERS, json={"labels": new_labels})
print(f"✅ Label set to: {label_to_set}")
