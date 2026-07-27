# Implements: architecture/reference/goal-orchestrator/component-contracts.md §4 GOIntelligence
# Constitutional basis: C-059 (Traceability — every decision is evidence), C-007 (append-only records)
"""
GoalRegisterGitHub — writes constitutional evidence records to GitHub Issues.

Phase 1: GitHub Issues as Goal Register.
  Each Goal = a GitHub Issue (title: [GOAL-NNN] {statement})
  Each evidence record = a structured comment on the Goal Issue
  Label-based state tracking mirrors GEOM lifecycle

Phase 2: PostgreSQL constitutional.goal_register (Goal Register service)
  GitHub Issues remain as the human-facing view.
  PostgreSQL becomes the constitutional audit ledger.

Usage:
  writer = GoalRegisterGitHub(token=os.environ["GITHUB_TOKEN"], repo="dlai-sd/waooaw-platform")
  writer.write_record("GOAL-WC012", record_dict)
  writer.ensure_goal_issue("GOAL-WC012", "Implement Constitutional Engine")
  writer.update_goal_state("GOAL-WC012", "goal:in-journey")
"""
from __future__ import annotations
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).parent.parent.parent


def _run(cmd: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(cmd, capture_output=True, text=True, env=merged, cwd=REPO_ROOT)


# ── GEOM lifecycle state → GitHub label mapping ───────────────────────────────
_STATE_LABELS = {
    "REGISTERED":   "goal:registered",
    "UNDERSTOOD":   "goal:understood",
    "PLANNED":      "goal:planned",
    "IN_JOURNEY":   "goal:in-journey",
    "VALIDATED":    "goal:validated",
    "COMPLETE":     "goal:complete",
    "CLOSED":       "goal:closed",
    "SUSPENDED":    "goal:suspended",
}

_PRIORITY_LABELS = {
    "Emergency":         "priority:p1-emergency",
    "Constitutional":    "priority:p2-constitutional",
    "Elevated":          "priority:p3-elevated",
    "Routine":           "priority:p4-routine",
}


class GoalRegisterGitHub:
    """
    Writes constitutional evidence records to GitHub Issues (Phase 1 Goal Register).
    Falls back to JSONL file when GitHub API is unavailable (local dev/test).
    """

    def __init__(
        self,
        token: Optional[str] = None,
        repo: Optional[str] = None,
        fallback_path: Optional[Path] = None,
    ) -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
        self._repo  = repo or os.environ.get("GITHUB_REPO", "dlai-sd/waooaw-platform")
        self._fallback = fallback_path or (REPO_ROOT / "goals" / "goal_register.jsonl")
        self._fallback.parent.mkdir(parents=True, exist_ok=True)
        self._issue_cache: dict[str, int] = {}  # goal_id → issue_number

    # ── Public API ────────────────────────────────────────────────────────────

    def write_record(self, goal_id: str, record: dict[str, Any]) -> str:
        """Write an evidence record. Returns the record_id."""
        record_id = record.get("record_id", f"REC-{goal_id}-{int(datetime.now().timestamp())}")
        record["record_id"] = record_id
        record["goal_id"]   = goal_id
        if "produced_at" not in record:
            record["produced_at"] = datetime.now(timezone.utc).isoformat()

        # Always write to JSONL fallback (Phase 1 + local dev)
        self._write_jsonl(record)

        # Write to GitHub Issue comment when token is available
        if self._token:
            issue_num = self._get_or_create_issue(goal_id, record)
            if issue_num:
                self._post_evidence_comment(issue_num, record)

        return record_id

    def ensure_goal_issue(
        self,
        goal_id: str,
        statement: str,
        priority: str = "Routine",
        institution_id: str = "INST-013",
    ) -> Optional[int]:
        """Create a GitHub Issue for this Goal if it doesn't exist. Returns issue number."""
        if not self._token:
            return None
        existing = self._find_issue_by_goal_id(goal_id)
        if existing:
            return existing

        labels = [
            "goal:registered",
            _PRIORITY_LABELS.get(priority, "priority:p4-routine"),
            "type:goal",
        ]
        self._ensure_labels(labels)

        body = (
            f"**Goal ID:** {goal_id}\n"
            f"**Registered by:** {institution_id}\n"
            f"**Statement:** {statement}\n\n"
            f"---\n"
            f"_This issue is the constitutional Goal Record. Evidence records "
            f"are posted as structured comments below. "
            f"Labels reflect GEOM lifecycle state._\n\n"
            f"**GEOM lifecycle:** REGISTERED → UNDERSTOOD → PLANNED → IN_JOURNEY "
            f"→ VALIDATED → COMPLETE → CLOSED"
        )

        result = _run([
            "gh", "issue", "create",
            "--title", f"[{goal_id}] {statement[:80]}",
            "--body", body,
            "--label", ",".join(labels),
            "--repo", self._repo,
        ], env={"GH_TOKEN": self._token})

        if result.returncode == 0:
            # Extract issue number from URL in output
            match = re.search(r"/issues/(\d+)", result.stdout)
            if match:
                num = int(match.group(1))
                self._issue_cache[goal_id] = num
                print(f"  ✓ Goal Issue created: #{num} [{goal_id}]")
                return num
        else:
            print(f"  WARN: Could not create Goal Issue: {result.stderr[:200]}")
        return None

    def update_goal_state(self, goal_id: str, geom_state: str) -> None:
        """Update the GEOM lifecycle label on the Goal Issue."""
        if not self._token:
            return
        issue_num = self._get_or_create_issue(goal_id, {})
        if not issue_num:
            return

        # Remove all state labels, add new one
        for old_label in _STATE_LABELS.values():
            _run([
                "gh", "issue", "edit", str(issue_num),
                "--remove-label", old_label, "--repo", self._repo,
            ], env={"GH_TOKEN": self._token})

        new_label = _STATE_LABELS.get(geom_state, "goal:in-journey")
        self._ensure_labels([new_label])
        _run([
            "gh", "issue", "edit", str(issue_num),
            "--add-label", new_label, "--repo", self._repo,
        ], env={"GH_TOKEN": self._token})

    # ── Private helpers ───────────────────────────────────────────────────────

    def _write_jsonl(self, record: dict) -> None:
        """Phase 1 fallback: append to goal_register.jsonl."""
        with self._fallback.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _post_evidence_comment(self, issue_num: int, record: dict) -> None:
        """Post structured evidence record as a GitHub Issue comment."""
        record_type = record.get("record_type", "Constitutional Record")
        record_id   = record.get("record_id", "")
        inst        = record.get("institution_id", "")

        # Structured JSON wrapped in HTML comment tags (machine-readable + human-readable)
        comment = (
            f"### 📋 {record_type}\n\n"
            f"**Record ID:** `{record_id}`  \n"
            f"**Institution:** {inst}  \n"
            f"**Time:** {record.get('produced_at', '')}\n\n"
            f"<details><summary>Constitutional evidence (machine-readable)</summary>\n\n"
            f"```json\n{json.dumps(record, indent=2, default=str)}\n```\n\n"
            f"</details>\n\n"
            f"<!-- CONSTITUTIONAL_RECORD\n"
            f"{json.dumps(record, default=str)}\n"
            f"/CONSTITUTIONAL_RECORD -->"
        )

        result = _run([
            "gh", "issue", "comment", str(issue_num),
            "--body", comment,
            "--repo", self._repo,
        ], env={"GH_TOKEN": self._token})

        if result.returncode != 0:
            print(f"  WARN: Evidence comment failed on #{issue_num}: {result.stderr[:200]}")

    def _get_or_create_issue(self, goal_id: str, record: dict) -> Optional[int]:
        """Find or create the GitHub Issue for this Goal."""
        if goal_id in self._issue_cache:
            return self._issue_cache[goal_id]
        existing = self._find_issue_by_goal_id(goal_id)
        if existing:
            self._issue_cache[goal_id] = existing
            return existing
        # Auto-create with minimal info from the record
        statement = record.get("intent", goal_id)
        return self.ensure_goal_issue(goal_id, str(statement)[:80])

    def _find_issue_by_goal_id(self, goal_id: str) -> Optional[int]:
        """Search GitHub Issues for an issue with this Goal ID in the title."""
        if not self._token:
            return None
        result = _run([
            "gh", "issue", "list",
            "--repo", self._repo,
            "--state", "open",
            "--search", f"[{goal_id}] in:title",
            "--json", "number,title",
            "--jq", f'.[0] | select(.title | contains("[{goal_id}]")) | .number',
        ], env={"GH_TOKEN": self._token})

        if result.returncode == 0 and result.stdout.strip():
            try:
                num = int(result.stdout.strip())
                self._issue_cache[goal_id] = num
                return num
            except ValueError:
                pass
        return None

    def _ensure_labels(self, labels: list[str]) -> None:
        """Create labels if they don't exist (idempotent)."""
        label_colors = {
            "goal:registered":        "0075ca",
            "goal:understood":        "0052cc",
            "goal:planned":           "0039a6",
            "goal:in-journey":        "e4e669",
            "goal:validated":         "fbca04",
            "goal:complete":          "0e8a16",
            "goal:closed":            "6f42c1",
            "goal:suspended":         "d93f0b",
            "priority:p1-emergency":  "b60205",
            "priority:p2-constitutional": "d93f0b",
            "priority:p3-elevated":   "e99695",
            "priority:p4-routine":    "c5def5",
            "type:goal":              "bfd4f2",
        }
        for label in labels:
            color = label_colors.get(label, "ededed")
            _run([
                "gh", "label", "create", label,
                "--repo", self._repo,
                "--color", color,
                "--force",
            ], env={"GH_TOKEN": self._token})


# ── Convenience function for use in pipeline.py and reviewer.py ──────────────

def make_goal_register_writer(
    token: Optional[str] = None,
    repo: Optional[str] = None,
) -> GoalRegisterGitHub:
    """Factory — creates a GoalRegisterGitHub instance using environment variables."""
    return GoalRegisterGitHub(
        token=token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"),
        repo=repo or os.environ.get("GITHUB_REPO", "dlai-sd/waooaw-platform"),
    )
