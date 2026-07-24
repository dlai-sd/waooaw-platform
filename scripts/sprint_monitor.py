#!/usr/bin/env python3
"""
sprint_monitor.py — Sprint Health Monitor & Constitutional Feedback Agent

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Monitor hat)
# constitutional_basis:
#   C-069 (Self-Improvement — platform MUST detect degradation and raise proposals autonomously)
#   C-070 (Constitutional DNA — self-improvement instinct mandatory for all platform agents)
#   C-023 (Evidence First — degradation evidence must precede every proposal)
#   C-059 (Traceability — every proposal traces to a failure pattern in emitted signal)
# office: Platform IT Expert (Monitor hat)
# IB: IB-009

Signal source (primary): sprint-context/monitor-signal.json artifact emitted by the runner.
Signal source (fallback): SCAFFOLD_FAILED + INFRA_ERROR_TASKS job outputs.
No branch checkout required — the runner emits signals; the monitor listens.

Failure classification:
  INFRA_ERROR          — API timeouts. Not a spec gap. Auto-close any false issues.
  CASCADE_PIPELINE_BUG — Scaffold failed; downstream spec-gaps are a cascade artifact.
                         Auto-close false downstream issues. Draft Step Dependency claim.
  IDEMPOTENCY_BUG      — Already-done tasks re-executed. Draft Idempotency Obligation claim.
  SPEC_GAP_GENUINE     — Task failed 3× with substantive, non-cascade build errors.

C-069: 'Waiting for a human to notice a quality drop before initiating improvement
        is a violation of this obligation.'
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

REPO            = os.environ.get("GITHUB_REPO", "dlai-sd/waooaw-platform")
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GITHUB_RUN_ID   = os.environ.get("GITHUB_RUN_ID", "")
SPRINT_RESULT   = os.environ.get("SPRINT_RESULT", "")
SPRINT_ID       = os.environ.get("SPRINT", "")
# Scalar fallbacks from job outputs (used when signal file unavailable)
SCAFFOLD_FAILED_ENV   = os.environ.get("SCAFFOLD_FAILED", "").lower() == "true"
INFRA_ERROR_TASKS_ENV = [t for t in os.environ.get("INFRA_ERROR_TASKS", "").split(",") if t]

DASHBOARD_ISSUE  = "7"
LOOKBACK_MINUTES = 100
SIGNAL_PATH      = Path("sprint-context/monitor-signal.json")
CLAIMS_DIR       = Path("knowledge/claims")

# Classification categories
INFRA_ERROR          = "INFRA_ERROR"
CASCADE_PIPELINE_BUG = "CASCADE_PIPELINE_BUG"
IDEMPOTENCY_BUG      = "IDEMPOTENCY_BUG"
SPEC_GAP_GENUINE     = "SPEC_GAP_GENUINE"
ALL_PASS             = "ALL_PASS"

# Known constitutional gap patterns → proposed claims
CONSTITUTIONAL_GAP_MAP = {
    CASCADE_PIPELINE_BUG: {
        "claim_id_hint": "C-083",
        "title": "Step Dependency Ordering — upstream failure must halt downstream steps",
        "statement": (
            "In any multi-step autonomous workflow, a step MUST NOT begin execution "
            "if its declared upstream dependency produced a FAIL, HALT, or ERROR evidence "
            "record in the current workflow instance. Committing code from step N+1 when "
            "step N has failed is a constitutional violation — the work is unverifiable "
            "because its foundation is invalid. This applies to all autonomous agents "
            "on the WAOOAW platform, including the implementation sprint runner."
        ),
        "basis": "C-023 (Evidence First — unverifiable work must not be committed), C-070, C-059",
    },
    IDEMPOTENCY_BUG: {
        "claim_id_hint": "C-084",
        "title": "Idempotency Obligation — completed steps must not be re-executed",
        "statement": (
            "Before executing any workflow step in a resumable or retryable workflow, "
            "the agent MUST verify that a SUCCESS record for this step does not already "
            "exist in the current workflow instance. Temporal retries, cron re-runs, "
            "and session resumptions are all subject to this obligation. Re-executing a "
            "completed step produces duplicate external effects (duplicate emails, duplicate "
            "trade orders, duplicate commits) that constitute real customer harm."
        ),
        "basis": "C-027 (append-only ledger), C-023 (Evidence First), C-070 (Constitutional DNA)",
    },
}

# ── GitHub API helpers ─────────────────────────────────────────────────────────

def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["gh"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def gh_json(*args: str) -> dict | list | None:
    result = gh(*args, check=False)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def create_issue(title: str, body: str, labels: list[str]) -> str | None:
    args = ["issue", "create", "--repo", REPO, "--title", title, "--body", body]
    for label in labels:
        args += ["--label", label]
    result = gh(*args, check=False)
    if result.returncode == 0:
        m = re.search(r"/issues/(\d+)", result.stdout)
        return m.group(1) if m else None
    print(f"  WARN: Could not create issue: {result.stderr[:100]}")
    return None


def close_issue(number: str | int, reason: str) -> bool:
    result = gh("issue", "close", str(number), "--repo", REPO,
                "--comment", reason, check=False)
    if result.returncode == 0:
        print(f"  ✅ Closed issue #{number} ({reason[:60]})")
        return True
    print(f"  WARN: Could not close issue #{number}: {result.stderr[:80]}")
    return False


def post_dashboard_comment(body: str) -> bool:
    result = gh("issue", "comment", DASHBOARD_ISSUE, "--repo", REPO,
                "--body", body, check=False)
    if result.returncode == 0:
        print(f"  ✅ Reported to Sprint Dashboard (Issue #{DASHBOARD_ISSUE})")
        return True
    print(f"  WARN: Could not post to dashboard: {result.stderr[:80]}")
    return False


def ensure_label(name: str, color: str = "0075ca", description: str = "") -> None:
    gh("label", "create", name, "--repo", REPO,
       "--color", color, "--description", description, "--force", check=False)

# ── Signal reading ─────────────────────────────────────────────────────────────

def read_monitor_signal() -> dict | None:
    """
    Read the structured signal emitted by the runner as an artifact.
    This is the primary signal source — no branch checkout required.
    Falls back to None if unavailable (cancelled run, infra failure).
    """
    if SIGNAL_PATH.exists():
        try:
            signal = json.loads(SIGNAL_PATH.read_text())
            print(f"  ✅ Monitor signal loaded from artifact: {SIGNAL_PATH}")
            return signal
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARN: Could not parse monitor signal: {e}")
    print(f"  ⚠️  Monitor signal not found at {SIGNAL_PATH} — using job output fallbacks")
    return None

# ── State reading ──────────────────────────────────────────────────────────────

def read_tasks_done_from_state() -> list[str]:
    state_file = Path("constitution/PROJECT_STATE.md")
    if not state_file.exists():
        return []
    content = state_file.read_text()
    inline = re.search(r"tasks_done:\s*\[([^\]]*)\]", content)
    if inline:
        raw = inline.group(1).strip()
        return [t.strip() for t in raw.split(",") if t.strip()]
    block = re.search(r"tasks_done:\s*\n((?:  - [^\n]+\n?)*)", content)
    if block:
        return re.findall(r"  - (\S+)", block.group(1))
    return []

# ── Issue reading ──────────────────────────────────────────────────────────────

def get_spec_gap_issues_this_run(known_issue_nums: list[str]) -> list[dict]:
    """
    Find spec-gap issues for this run.
    Primary: known_issue_nums from signal (exact, no guessing).
    Fallback: time-window query on GitHub.
    """
    if known_issue_nums:
        issues = []
        for num in known_issue_nums:
            data = gh_json("issue", "view", str(num), "--repo", REPO,
                           "--json", "number,title,state")
            if data and data.get("state") == "OPEN":
                issues.append(data)
        print(f"  Signal-sourced spec-gap issues: {[i['number'] for i in issues]}")
        return issues

    # Fallback: time-window query (less precise)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    result = gh_json("issue", "list", "--repo", REPO, "--state", "open",
                     "--label", "awaiting:founder-approval",
                     "--json", "number,title,createdAt", "--limit", "20")
    if not result:
        return []
    recent = []
    for issue in result:
        if not issue.get("title", "").startswith("spec-gap"):
            continue
        try:
            created = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
            if created >= cutoff:
                recent.append(issue)
        except ValueError:
            continue
    print(f"  Time-window spec-gap issues (fallback): {[i['number'] for i in recent]}")
    return recent


def extract_task_from_spec_gap_title(title: str) -> str | None:
    m = re.search(r"\[([A-Z0-9-]+)\]", title)
    return m.group(1) if m else None


def proposal_issue_exists(claim_id_hint: str) -> bool:
    """
    Check GitHub for an EXISTING open proposal issue for this claim.
    Prevents duplicate proposals across multiple failed runs.
    C-069: one proposal per gap, not one per run.
    """
    result = gh_json("issue", "list", "--repo", REPO, "--state", "open",
                     "--label", "type:constitutional-proposal",
                     "--json", "number,title", "--limit", "20")
    if not result:
        return False
    return any(claim_id_hint in issue.get("title", "") for issue in result)


def claim_file_exists(claim_id_hint: str) -> bool:
    return any(True for _ in CLAIMS_DIR.glob(f"{claim_id_hint}*.md"))

# ── Classification ─────────────────────────────────────────────────────────────

def classify_run(
    signal: dict | None,
    spec_gap_issues: list[dict],
    tasks_done_state: list[str],
) -> dict:
    """
    Classify each spec-gap issue and the run overall.
    Signal is the authoritative source when available.
    """
    # Extract from signal or fall back to environment
    scaffold_failed  = signal["scaffold_failed"]  if signal else SCAFFOLD_FAILED_ENV
    scaffold_task    = signal["scaffold_task"]     if signal else None
    task_results     = signal["task_results"]      if signal else {}
    infra_tasks      = {k for k, v in task_results.items() if v.get("result") == "INFRA_ERROR"}
    if not infra_tasks:
        infra_tasks = set(INFRA_ERROR_TASKS_ENV)

    classified_issues = []
    constitutional_gaps: set[str] = set()

    for issue in spec_gap_issues:
        number = issue["number"]
        task   = extract_task_from_spec_gap_title(issue.get("title", ""))
        if not task:
            continue

        task_sig = task_results.get(task, {})

        # Rule 1: INFRA_ERROR — task signal says INFRA_ERROR
        if task_sig.get("result") == "INFRA_ERROR" or task in infra_tasks:
            classified_issues.append({
                "number": number, "task": task,
                "classification": INFRA_ERROR,
                "reason": f"{task} failed due to API timeouts — not a spec gap.",
            })
            continue

        # Rule 2: IDEMPOTENCY_BUG — task was already done before this run
        if task in tasks_done_state:
            classified_issues.append({
                "number": number, "task": task,
                "classification": IDEMPOTENCY_BUG,
                "reason": f"{task} was already in tasks_done when this run started. "
                          f"Pipeline re-executed a completed task.",
            })
            constitutional_gaps.add(IDEMPOTENCY_BUG)
            continue

        # Rule 3: CASCADE_PIPELINE_BUG — scaffold failed + this is a downstream task
        if scaffold_failed and scaffold_task and task != scaffold_task:
            classified_issues.append({
                "number": number, "task": task,
                "classification": CASCADE_PIPELINE_BUG,
                "reason": f"Scaffold {scaffold_task} failed. {task}'s build errors are a "
                          f"cascade — it cannot compile without a clean scaffold.",
            })
            constitutional_gaps.add(CASCADE_PIPELINE_BUG)
            continue

        # Rule 4: SPEC_GAP_GENUINE
        classified_issues.append({
            "number": number, "task": task,
            "classification": SPEC_GAP_GENUINE,
            "reason": f"{task} failed 3× with substantive build errors not caused by "
                      f"infra timeouts or scaffold cascade.",
        })

    # Run-level classification
    if not spec_gap_issues:
        run_class = ALL_PASS
    elif constitutional_gaps:
        run_class = sorted(constitutional_gaps)[0]
    elif all(i["classification"] == INFRA_ERROR for i in classified_issues):
        run_class = INFRA_ERROR
    elif any(i["classification"] == SPEC_GAP_GENUINE for i in classified_issues):
        run_class = SPEC_GAP_GENUINE
    else:
        run_class = ALL_PASS

    return {
        "run_classification": run_class,
        "issues": classified_issues,
        "constitutional_gaps": list(constitutional_gaps),
    }

# ── Constitutional actions ─────────────────────────────────────────────────────

def act_on_classification(classification: dict) -> None:
    run_class = classification["run_classification"]
    issues    = classification["issues"]
    gaps      = classification["constitutional_gaps"]

    print(f"\n── Constitutional Monitor Actions ─────────────────────────────────")
    print(f"  Run classification: {run_class}")

    if run_class == ALL_PASS:
        print(f"  ✅ All tasks passed. No false positives. No constitutional gaps.")
        # C-069: silent pass = no dashboard noise. Only post when actionable.
        return

    # Close false spec-gap issues
    false_positives = [i for i in issues if i["classification"] != SPEC_GAP_GENUINE]
    for issue in false_positives:
        close_issue(
            issue["number"],
            f"[Sprint Monitor C-069] {issue['classification']}: {issue['reason']}"
        )

    # Draft constitutional proposals for detected gaps
    proposals_created = []
    for gap in gaps:
        if gap not in CONSTITUTIONAL_GAP_MAP:
            continue
        proposal = CONSTITUTIONAL_GAP_MAP[gap]
        claim_hint = proposal["claim_id_hint"]

        if claim_file_exists(claim_hint):
            print(f"  ℹ️  {claim_hint} claim file exists — no proposal needed")
            continue
        if proposal_issue_exists(claim_hint):
            print(f"  ℹ️  {claim_hint} proposal already open — skipping duplicate")
            continue

        affected_issues = [i for i in issues if i["classification"] == gap]
        body = f"""## Constitutional Proposal — Auto-generated by Sprint Monitor

**Raised by:** Sprint Monitor (Platform IT Expert — Monitor hat)
**Constitutional basis:** C-069 (Self-Improvement), C-070 (Constitutional DNA)
**Evidence:** Run [{GITHUB_RUN_ID}](https://github.com/{REPO}/actions/runs/{GITHUB_RUN_ID})
**Failure pattern:** `{gap}`
**Sprint:** {SPRINT_ID}

---

### Proposed Claim: {claim_hint} — {proposal['title']}

**Proposed Statement:**

{proposal['statement']}

**Constitutional Basis:** {proposal['basis']}

---

### Evidence Chain (C-023 — Evidence First)

The failure pattern `{gap}` was observed in run {GITHUB_RUN_ID}.
False spec-gap issues that were caused by this missing claim:
{chr(10).join(f"- #{i['number']} (`{i['task']}`)" for i in affected_issues)}

---

### Required Action (Founder → EA)

1. Founder reviews and approves this proposal
2. EA drafts `knowledge/claims/{claim_hint}.md`
3. EA opens a spec PR → Founder ratifies
4. Next sprint adds a CCT validating the new claim

---
_Auto-generated by `scripts/sprint_monitor.py` per C-069 (Self-Improvement Obligation)_
"""
        issue_num = create_issue(
            title=f"[Constitutional Proposal] {claim_hint}: {proposal['title']}",
            body=body,
            labels=["awaiting:founder-approval", "type:constitutional-proposal"],
        )
        if issue_num:
            print(f"  📋 Constitutional proposal created: #{issue_num} ({claim_hint})")
            proposals_created.append(f"#{issue_num} ({claim_hint})")

    # Post actionable summary to Sprint Dashboard
    genuine = [i for i in issues if i["classification"] == SPEC_GAP_GENUINE]
    emoji   = {"INFRA_ERROR": "⚙️", "SPEC_GAP_GENUINE": "⚠️"}.get(run_class, "🔧")

    comment = f"""---
### Sprint Monitor — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

**Run classification:** {emoji} `{run_class}`  _(C-069 autonomous feedback)_

"""
    if false_positives:
        comment += f"**Auto-closed false spec-gap issues ({len(false_positives)}):**\n"
        for i in false_positives:
            comment += f"- #{i['number']} `{i['task']}` → `{i['classification']}`\n"
        comment += "\n"

    if genuine:
        comment += f"**Genuine spec gaps — EA/SA review needed ({len(genuine)}):**\n"
        for i in genuine:
            comment += f"- #{i['number']} `{i['task']}`\n"
        comment += "\n"

    if proposals_created:
        comment += f"**Constitutional proposals raised:**\n"
        for p in proposals_created:
            comment += f"- {p}\n"
        comment += "\n"

    comment += (
        f"\n_Run [{GITHUB_RUN_ID}](https://github.com/{REPO}/actions/runs/{GITHUB_RUN_ID}) "
        f"· Sprint Monitor (C-069)_"
    )

    post_dashboard_comment(comment)

# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    print("── Sprint Health Monitor (C-069 / C-070) ─────────────────────────────")
    print(f"  Run ID        : {GITHUB_RUN_ID}")
    print(f"  Sprint        : {SPRINT_ID}")
    print(f"  Sprint result : {SPRINT_RESULT}")
    print(f"  scaffold_failed (env fallback) : {SCAFFOLD_FAILED_ENV}")
    print(f"  infra_tasks  (env fallback)    : {INFRA_ERROR_TASKS_ENV}")

    ensure_label("type:constitutional-proposal", color="d93f0b",
                 description="Proposed constitutional claim — awaiting Founder approval")

    # Step 1: Read the structured signal emitted by the runner
    signal = read_monitor_signal()

    # Step 2: Get spec-gap issues — use exact issue numbers from signal if available
    known_issues = signal.get("spec_gap_issues", []) if signal else []
    spec_gap_issues = get_spec_gap_issues_this_run(known_issues)
    print(f"  Spec-gap issues this run: {len(spec_gap_issues)}")

    # Step 3: Read task state from main branch
    tasks_done_state = read_tasks_done_from_state()
    print(f"  tasks_done in state: {tasks_done_state}")

    # Step 4: Classify
    classification = classify_run(signal, spec_gap_issues, tasks_done_state)

    # Step 5: Act
    act_on_classification(classification)

    return 0


if __name__ == "__main__":
    sys.exit(main())
