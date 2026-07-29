#!/usr/bin/env python3
"""
sprint_summary_writer.py — Appends file-cost + subtask + pending sections to
the GitHub Actions step summary after each autonomous sprint run.

Called by autonomous-sprint.yaml G7 step.
Reads: sprint-context/monitor-signal.json
Writes: $GITHUB_STEP_SUMMARY (appends)

Constitutional basis: C-077 (FinOps visibility), C-069 (observable state)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    signal_path = Path("sprint-context/monitor-signal.json")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "")

    if not signal_path.exists() or not summary_path:
        return 0

    signal = json.loads(signal_path.read_text())
    file_costs = signal.get("file_costs", {})
    tasks_done = signal.get("tasks_done", [])
    tasks_req  = signal.get("tasks_requested", [])
    subtasks   = signal.get("subtask_results", {})

    lines: list[str] = []

    # ── Per-file LLM cost table ───────────────────────────────────────────────
    if file_costs:
        total = sum(file_costs.values())
        lines += [
            "",
            "### \U0001f4b0 LLM Cost This Run",
            "| File / Task | \u20b9 Cost |",
            "|---|---|",
        ]
        for key, cost in sorted(file_costs.items()):
            label = key.split(":")[-1] if ":" in key else key
            lines.append(f"| `{label}` | \u20b9{cost:.4f} |")
        lines.append(f"| **Total** | **\u20b9{total:.4f}** |")

    # ── Subtask results table ─────────────────────────────────────────────────
    if subtasks:
        icons = {"SUCCESS": "\u2705", "FAIL": "\u274c", "SKIPPED": "\u23ed"}
        lines += [
            "",
            "### \U0001f4cb Subtask Results",
            "| Subtask | Result |",
            "|---|---|",
        ]
        for sid, info in sorted(subtasks.items()):
            result = info.get("result", "")
            icon = icons.get(result, "\u2753")
            lines.append(f"| `{sid}` | {icon} {result} |")

    # ── Pending tasks ─────────────────────────────────────────────────────────
    pending = [t for t in tasks_req if t not in tasks_done]
    if pending:
        lines += ["", "### \u23f3 Pending Tasks (next run)"]
        for t in pending:
            lines.append(f"- `{t}`")

    if lines:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
