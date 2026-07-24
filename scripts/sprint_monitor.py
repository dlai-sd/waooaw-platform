#!/usr/bin/env python3
"""
sprint_monitor.py — Sprint Health Monitor & Constitutional Feedback Agent

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Monitor hat)
# constitutional_basis:
#   C-069 (Platform Self-Improvement — platform MUST detect degradation and raise proposals)
#   C-070 (Constitutional DNA — self-improvement instinct mandatory for all platform agents)
#   C-023 (Evidence First — degradation evidence must precede every proposal)
#   C-059 (Traceability — every proposal traces to a failure pattern in evidence log)
# office: Platform IT Expert (Monitor hat)
# IB: IB-009

Runs after EVERY sprint execution — success or failure.

Failure Classification:
  INFRA_ERROR          — API timeouts / rate limits. No spec gap. No action.
  CASCADE_PIPELINE_BUG — Scaffold (task 1) failed; downstream tasks committed on broken scaffold.
  IDEMPOTENCY_BUG      — Already-done tasks re-executed by a subsequent cron run.
  SPEC_GAP_GENUINE     — Task failed 3× with substantive, non-cascade build errors.
  ALL_PASS             — All tasks succeeded. Record and exit.

Constitutional actions taken autonomously (C-069 obligation):
  INFRA_ERROR          → Close any false spec-gap issues created for this task.
  CASCADE_PIPELINE_BUG → Close false downstream spec-gap issues. Create pipeline-fix issue.
                          Propose constitutional claim if pattern matches known gap.
  IDEMPOTENCY_BUG      → Close duplicate spec-gap issues. Propose idempotency claim.
  SPEC_GAP_GENUINE     → Leave issue open. Add classification label. Escalate if ≥3 occurrences.

Waiting for a human to notice and close false spec-gap issues = C-069 violation.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

REPO           = os.environ.get("GITHUB_REPO", "dlai-sd/waooaw-platform")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
GITHUB_RUN_ID  = os.environ.get("GITHUB_RUN_ID", "")
SPRINT_RESULT  = os.environ.get("SPRINT_RESULT", "")       # from execute job output
SPRINT_ID      = os.environ.get("SPRINT", "")
DASHBOARD_ISSUE = "7"
LOOKBACK_MINUTES = 100          # issues created in last N minutes are "from this run"

EVIDENCE_LOG   = Path("logs/bootstrap-evidence.jsonl")
STATE_FILE     = Path("constitution/PROJECT_STATE.md")
CLAIMS_DIR     = Path("knowledge/claims")

# Classification categories
INFRA_ERROR          = "INFRA_ERROR"
CASCADE_PIPELINE_BUG = "CASCADE_PIPELINE_BUG"
IDEMPOTENCY_BUG      = "IDEMPOTENCY_BUG"
SPEC_GAP_GENUINE     = "SPEC_GAP_GENUINE"
ALL_PASS             = "ALL_PASS"

# Known constitutional gaps → proposed claims
# When the monitor detects a failure pattern matching a key, it drafts the corresponding claim.
CONSTITUTIONAL_GAP_MAP = {
    CASCADE_PIPELINE_BUG: {
        "claim_id_hint": "C-083",
        "title": "Step Dependency Ordering — upstream failure must halt downstream steps",
        "statement": (
            "In any multi-step autonomous workflow, a step MUST NOT begin execution "
            "if its declared upstream dependency produced a FAIL, HALT, or ERROR evidence "
            "record in the current workflow instance. The runner MUST check the evidence "
            "status of step N before executing step N+1. Committing code from step N+1 "
            "when step N has failed is a constitutional violation equivalent to Evidence "
            "First violation — the work is unverifiable because its foundation is invalid."
        ),
        "basis": "C-023 (Evidence First — unverifiable work must not be committed), C-070 (Constitutional DNA), C-059 (Traceability)",
    },
    IDEMPOTENCY_BUG: {
        "claim_id_hint": "C-084",
        "title": "Idempotency Obligation — completed steps must not be re-executed",
        "statement": (
            "Before executing any workflow step in a resumable or retryable workflow, "
            "the agent MUST verify that a SUCCESS evidence record for this step does not "
            "already exist in the current workflow instance. If a SUCCESS record exists, "
            "the step MUST be skipped and the existing evidence ID returned. Temporal "
            "retries, cron re-runs, and session resumptions are all subject to this "
            "obligation. Re-executing a completed step is a constitutional violation — "
            "it produces duplicate external effects and pollutes the Evidence Ledger "
            "with redundant records that undermine audit integrity (C-027)."
        ),
        "basis": "C-027 (append-only ledger — duplicate records pollute audit integrity), C-023 (Evidence First), C-070 (Constitutional DNA)",
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
    """Create a GitHub issue and return the number."""
    args = ["issue", "create", "--repo", REPO, "--title", title, "--body", body]
    for label in labels:
        args += ["--label", label]
    result = gh(*args, check=False)
    if result.returncode == 0:
        # Extract issue number from URL
        m = re.search(r"/issues/(\d+)", result.stdout)
        return m.group(1) if m else None
    print(f"  WARN: Could not create issue '{title[:60]}': {result.stderr[:100]}")
    return None


def close_issue(number: str | int, reason: str) -> None:
    gh("issue", "close", str(number), "--repo", REPO,
       "--comment", reason, check=False)
    print(f"  ✅ Closed issue #{number} (false positive — {reason[:60]})")


def post_dashboard_comment(body: str) -> None:
    gh("issue", "comment", DASHBOARD_ISSUE, "--repo", REPO, "--body", body, check=False)


def ensure_label(name: str, color: str = "0075ca", description: str = "") -> None:
    gh("label", "create", name, "--repo", REPO,
       "--color", color, "--description", description, "--force", check=False)

# ── Evidence log reading ───────────────────────────────────────────────────────

def read_evidence_this_run() -> list[dict]:
    """Read evidence records from this run (matched by GITHUB_RUN_ID)."""
    if not EVIDENCE_LOG.exists():
        return []
    records = []
    for line in EVIDENCE_LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if GITHUB_RUN_ID and str(rec.get("run_id", "")) == GITHUB_RUN_ID:
                records.append(rec)
            elif not GITHUB_RUN_ID:
                records.append(rec)  # fallback: include all if run_id unknown
        except json.JSONDecodeError:
            continue
    return records


def get_spec_gap_tasks(evidence: list[dict]) -> list[str]:
    """Return task IDs that had spec_gap_halt events this run."""
    return [r["task"] for r in evidence if r.get("event") == "spec_gap_halt" and "task" in r]


def get_infra_error_tasks(evidence: list[dict]) -> list[str]:
    """Return task IDs where ALL failures were API/infra (not code errors)."""
    infra_tasks = set()
    for r in evidence:
        if r.get("event") in ("INFRA_ERROR", "INFRA_FAILURE") and "task" in r:
            infra_tasks.add(r["task"])
    return list(infra_tasks)


def get_successful_tasks(evidence: list[dict]) -> list[str]:
    """Return task IDs that have a TASK_SUCCESS or file-written event."""
    done = set()
    for r in evidence:
        if r.get("event") == "SPRINT_TASKS_EXECUTED":
            done.update(r.get("tasks_done", []))
    return list(done)

# ── State reading ──────────────────────────────────────────────────────────────

def read_tasks_done_from_state() -> list[str]:
    """Read tasks_done list from PROJECT_STATE.md SPRINT_STATE_MACHINE block."""
    if not STATE_FILE.exists():
        return []
    content = STATE_FILE.read_text()
    # Inline format: tasks_done: [WC012-01, WC012-02]
    inline = re.search(r"tasks_done:\s*\[([^\]]*)\]", content)
    if inline:
        raw = inline.group(1).strip()
        return [t.strip() for t in raw.split(",") if t.strip()]
    # Block format:
    # tasks_done:
    #   - WC012-01
    block = re.search(r"tasks_done:\s*\n((?:  - [^\n]+\n?)*)", content)
    if block:
        return re.findall(r"  - (\S+)", block.group(1))
    return []


def read_tasks_remaining_from_state() -> list[str]:
    """Read tasks_remaining list from PROJECT_STATE.md."""
    if not STATE_FILE.exists():
        return []
    content = STATE_FILE.read_text()
    block = re.search(r"tasks_remaining:\s*\n((?:  - [^\n]+\n?)*)", content)
    if block:
        return re.findall(r"  - (\S+)", block.group(1))
    return []

# ── Issue reading ──────────────────────────────────────────────────────────────

def get_spec_gap_issues_this_run() -> list[dict]:
    """Find spec-gap issues opened in the last LOOKBACK_MINUTES minutes."""
    since = (datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)).isoformat()
    result = gh_json(
        "issue", "list", "--repo", REPO,
        "--state", "open",
        "--label", "awaiting:founder-approval",
        "--json", "number,title,createdAt,body",
        "--limit", "20",
    )
    if not result:
        return []
    # Filter by: title starts with "spec-gap" AND created recently
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    recent = []
    for issue in result:
        title = issue.get("title", "")
        if not title.startswith("spec-gap"):
            continue
        created_str = issue.get("createdAt", "")
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created >= cutoff:
            recent.append(issue)
    return recent


def extract_task_from_spec_gap_title(title: str) -> str | None:
    """Extract task ID from title like 'spec-gap [WC012-01]: ...'"""
    m = re.search(r"\[([A-Z0-9-]+)\]", title)
    return m.group(1) if m else None


def claim_exists(claim_id_hint: str) -> bool:
    """Check if a claim file already exists for this ID."""
    for f in CLAIMS_DIR.glob(f"{claim_id_hint}*.md"):
        return True
    return False

# ── Classification logic ───────────────────────────────────────────────────────

def classify_run(
    evidence: list[dict],
    spec_gap_issues: list[dict],
    tasks_done_state: list[str],
    tasks_remaining_state: list[str],
) -> dict:
    """
    Classify the sprint run and each spec-gap issue.
    Returns: {
        "run_classification": str,
        "issues": [{ "number": int, "task": str, "classification": str, "reason": str }],
        "constitutional_gaps": [str],  # gap categories detected
    }
    """
    infra_tasks = set(get_infra_error_tasks(evidence))
    spec_gap_tasks_evidence = set(get_spec_gap_tasks(evidence))
    successful_tasks_evidence = set(get_successful_tasks(evidence))

    all_task_ids = set(tasks_done_state + tasks_remaining_state)
    scaffold_task = tasks_remaining_state[0] if tasks_remaining_state else None
    scaffold_failed = scaffold_task and scaffold_task in spec_gap_tasks_evidence

    classified_issues = []
    constitutional_gaps = set()

    for issue in spec_gap_issues:
        number = issue["number"]
        task = extract_task_from_spec_gap_title(issue.get("title", ""))
        if not task:
            continue

        # ── Rule 1: INFRA_ERROR ──────────────────────────────────────────────
        if task in infra_tasks:
            classified_issues.append({
                "number": number, "task": task,
                "classification": INFRA_ERROR,
                "reason": f"{task} failed due to API timeouts/rate limits — not a spec gap. "
                          f"Runner INFRA_ERROR flag confirmed in evidence log.",
            })
            continue

        # ── Rule 2: IDEMPOTENCY_BUG — task was already done in state ─────────
        if task in tasks_done_state:
            classified_issues.append({
                "number": number, "task": task,
                "classification": IDEMPOTENCY_BUG,
                "reason": f"{task} was already in tasks_done when this run started. "
                          f"Runner re-executed a completed task (idempotency failure).",
            })
            constitutional_gaps.add(IDEMPOTENCY_BUG)
            continue

        # ── Rule 3: CASCADE_PIPELINE_BUG — scaffold failed + this is downstream ─
        if scaffold_failed and scaffold_task and task != scaffold_task:
            classified_issues.append({
                "number": number, "task": task,
                "classification": CASCADE_PIPELINE_BUG,
                "reason": f"Scaffold task {scaffold_task} failed in this run. {task}'s build "
                          f"errors are a cascade — the project cannot compile without a clean scaffold. "
                          f"This is not a spec gap in {task}.",
            })
            constitutional_gaps.add(CASCADE_PIPELINE_BUG)
            continue

        # ── Rule 4: SPEC_GAP_GENUINE — substantive failure, not infra/cascade ──
        classified_issues.append({
            "number": number, "task": task,
            "classification": SPEC_GAP_GENUINE,
            "reason": f"{task} failed 3× with build/validation errors not caused by "
                      f"API timeouts or scaffold cascade. Spec gap is genuine.",
        })

    # ── Run-level classification ──────────────────────────────────────────────
    if not spec_gap_issues:
        run_class = ALL_PASS
    elif constitutional_gaps:
        run_class = sorted(constitutional_gaps)[0]  # most important
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

# ── Constitutional action ──────────────────────────────────────────────────────

def act_on_classification(classification: dict) -> None:
    """
    Take autonomous constitutional action based on classification.
    C-069: platform MUST raise proposals when degradation is detected.
    """
    run_class = classification["run_classification"]
    issues    = classification["issues"]
    gaps      = classification["constitutional_gaps"]

    print(f"\n── Constitutional Monitor Actions ──────────────────────")
    print(f"  Run classification: {run_class}")

    # ── Close false spec-gap issues ──────────────────────────────────────────
    false_positive_classes = {INFRA_ERROR, CASCADE_PIPELINE_BUG, IDEMPOTENCY_BUG}
    for issue in issues:
        if issue["classification"] in false_positive_classes:
            close_issue(
                issue["number"],
                f"[Sprint Monitor — C-069] {issue['classification']}: {issue['reason']}"
            )

    # ── Create constitutional proposal issues for detected gaps ───────────────
    for gap in gaps:
        if gap not in CONSTITUTIONAL_GAP_MAP:
            continue
        proposal = CONSTITUTIONAL_GAP_MAP[gap]
        claim_hint = proposal["claim_id_hint"]

        if claim_exists(claim_hint):
            print(f"  ℹ️  {claim_hint} already exists — no duplicate proposal needed")
            continue

        body = f"""## Constitutional Proposal — Auto-generated by Sprint Monitor

**Raised by:** Sprint Monitor (Platform IT Expert — Monitor hat)
**Constitutional basis:** C-069 (Self-Improvement), C-070 (Constitutional DNA)
**Evidence:** Run {GITHUB_RUN_ID} — failure pattern: `{gap}`
**Sprint:** {SPRINT_ID}

---

### Proposed Claim: {proposal['claim_id_hint']} — {proposal['title']}

**Proposed Statement:**

{proposal['statement']}

**Constitutional Basis:**

{proposal['basis']}

---

### Evidence Chain (C-023 — Evidence First)

The failure pattern `{gap}` was detected in sprint run {GITHUB_RUN_ID}.
See `logs/bootstrap-evidence.jsonl` for the full evidence trail.

Spec-gap issues that were false positives due to this gap:
{chr(10).join(f"- #{i['number']} ({i['task']})" for i in issues if i['classification'] == gap)}

---

### Required Action

1. Founder reviews this proposal
2. If approved: Enterprise Architect drafts the full claim file in `knowledge/claims/{claim_hint}.md`
3. EA opens PR → Founder ratifies → claim is added to the constitution
4. Once ratified: implementation sprint adds CCT for the new claim

**Label:** `awaiting:founder-approval`

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

    # ── Post classification summary to Sprint Dashboard ───────────────────────
    genuine_gaps  = [i for i in issues if i["classification"] == SPEC_GAP_GENUINE]
    false_pos     = [i for i in issues if i["classification"] != SPEC_GAP_GENUINE]
    proposal_refs = []
    for gap in gaps:
        if gap in CONSTITUTIONAL_GAP_MAP:
            proposal_refs.append(f"- `{gap}`: {CONSTITUTIONAL_GAP_MAP[gap]['title']}")

    emoji = {"ALL_PASS": "✅", "INFRA_ERROR": "⚙️", "SPEC_GAP_GENUINE": "⚠️"}.get(run_class, "🔧")

    comment = f"""---
### Sprint Monitor Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

**Run classification:** {emoji} `{run_class}`
**Constitutional basis:** C-069 (Self-Improvement), C-070 (Constitutional DNA)

"""
    if false_pos:
        comment += f"**False spec-gap issues auto-closed ({len(false_pos)}):**\n"
        for i in false_pos:
            comment += f"- #{i['number']} `{i['task']}` → `{i['classification']}`\n"
        comment += "\n"

    if genuine_gaps:
        comment += f"**Genuine spec gaps remaining ({len(genuine_gaps)}):**\n"
        for i in genuine_gaps:
            comment += f"- #{i['number']} `{i['task']}` — requires EA/SA review\n"
        comment += "\n"

    if proposal_refs:
        comment += "**Constitutional proposals raised:**\n"
        comment += "\n".join(proposal_refs) + "\n\n"

    if run_class == ALL_PASS:
        comment += "All tasks passed. No false positives. No constitutional gaps detected.\n"

    comment += f"\n_Sprint Monitor (C-069): Run [{GITHUB_RUN_ID}](https://github.com/{REPO}/actions/runs/{GITHUB_RUN_ID})_"

    post_dashboard_comment(comment)
    print(f"  ✅ Classification posted to Sprint Dashboard (Issue #{DASHBOARD_ISSUE})")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    print("── Sprint Health Monitor (C-069 / C-070) ─────────────────────────────")
    print(f"  Run ID   : {GITHUB_RUN_ID}")
    print(f"  Sprint   : {SPRINT_ID}")
    print(f"  Result   : {SPRINT_RESULT}")

    # Ensure constitutional-proposal label exists (self-healing — like pipeline health check)
    ensure_label(
        "type:constitutional-proposal",
        color="d93f0b",
        description="Proposed constitutional claim — awaiting Founder approval"
    )

    # Step 1: Read evidence
    evidence = read_evidence_this_run()
    print(f"  Evidence records this run: {len(evidence)}")

    # Step 2: Read state
    tasks_done_state      = read_tasks_done_from_state()
    tasks_remaining_state = read_tasks_remaining_from_state()
    print(f"  tasks_done in state : {tasks_done_state}")
    print(f"  tasks_remaining     : {tasks_remaining_state}")

    # Step 3: Find spec-gap issues opened in this run
    spec_gap_issues = get_spec_gap_issues_this_run()
    print(f"  Spec-gap issues this run: {len(spec_gap_issues)}")
    for i in spec_gap_issues:
        print(f"    #{i['number']} {i['title'][:60]}")

    # Step 4: Classify
    classification = classify_run(
        evidence, spec_gap_issues, tasks_done_state, tasks_remaining_state
    )

    # Step 5: Act
    act_on_classification(classification)

    return 0


if __name__ == "__main__":
    sys.exit(main())
