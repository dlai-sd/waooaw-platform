# Implements: tests/constitutional/README.md (CCT-PIPE-02)
# constitutional_basis: C-059 (Implementation Traceability), C-066 Tier 2A (autonomous sprint)
# ib_item: IB-009
# office: Platform IT Expert — Implementation hat
# produced_by: EA post-mortem 2026-07-23 + QA sign-off 2026-07-23

"""
CCT-PIPE-02 — Sprint State Machine Coherence After Merge

Runs on: every PR touching scripts/autonomous_sprint_reviewer.py or scripts/sprint_state.py
Blocking: Yes — infinite loop risk blocks merge

Constitutional principle: After a sprint PR is merged, the SPRINT_STATE_MACHINE
must advance to the next sprint with tasks_remaining populated. An infinite loop
where a completed sprint re-executes on every 6-hour cron is a C-059 traceability
violation — the agent executes tasks it has no valid trace to.
"""
import sys
import re
import argparse
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sprint_state import SPRINT_TASK_MANIFEST  # noqa: E402


class TestSprintTaskManifest:
    """CCT-PIPE-02a/b: Manifest coverage and format."""

    def test_manifest_covers_all_planned_sprints(self) -> None:
        """CCT-PIPE-02a: SPRINT_TASK_MANIFEST must cover WC-011 through WC-018.

        If a sprint exists in the plan but not in the manifest, cmd_advance()
        will set tasks_remaining=[] and the sprint silently skips all tasks.
        The cron will re-run the completed sprint indefinitely.
        """
        for sprint_num in range(11, 19):
            sprint = f"WC-0{sprint_num:02d}"
            assert sprint in SPRINT_TASK_MANIFEST, (
                f"CCT-PIPE-02a FAIL: {sprint} missing from SPRINT_TASK_MANIFEST.\n"
                f"Infinite loop risk: advance() will set tasks_remaining=[] and "
                f"the sprint will re-execute on every 6-hour cron.\n"
                f"Fix: add {sprint}: [...tasks...] to SPRINT_TASK_MANIFEST in sprint_state.py"
            )
            assert len(SPRINT_TASK_MANIFEST[sprint]) > 0, (
                f"CCT-PIPE-02a FAIL: {sprint} has an empty task list in SPRINT_TASK_MANIFEST.\n"
                f"All tasks would be skipped silently."
            )

    def test_manifest_task_ids_follow_correct_format(self) -> None:
        """CCT-PIPE-02b: All task IDs must follow WC-NNN-NN format (C-059 traceability)."""
        pattern = re.compile(r'^WC\d{3}-\d{2}$')
        for sprint, tasks in SPRINT_TASK_MANIFEST.items():
            for task in tasks:
                assert pattern.match(task), (
                    f"CCT-PIPE-02b FAIL: Invalid task ID '{task}' in {sprint}.\n"
                    f"Expected format: WC###-## (e.g. WC012-01).\n"
                    f"C-059: every task must be traceable to its work contract."
                )


class TestSprintAdvancement:
    """CCT-PIPE-02c: cmd_advance() produces correct state."""

    def test_advance_populates_next_sprint_tasks(self, tmp_path: Path) -> None:
        """CCT-PIPE-02c: After advance(WC-011→WC-012), tasks_remaining contains WC-012 tasks."""
        import sprint_state as ss

        # Build minimal PROJECT_STATE.md
        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(
            "## SPRINT_STATE_MACHINE\n"
            "```yaml\n"
            "autonomous_halt: false\n"
            "platform_phase: IMPLEMENTATION\n"
            "current_sprint: WC-011\n"
            "sprint_ib_item: IB-009\n"
            "sprint_status: READY\n"
            "branch: ib/009/infra-foundation\n"
            "last_attempt_utc: \"\"\n"
            "last_attempt_result: \"\"\n"
            "consecutive_failures: 0\n"
            "tasks_done: []\n"
            "tasks_remaining:\n"
            "  - WC011-01\n"
            "current_task: \"\"\n"
            "current_task_started_utc: \"\"\n"
            "next_sprint: WC-012\n"
            "next_sprint_ib_item: IB-009\n"
            "blocker: \"\"\n"
            "blocker_raised_utc: \"\"\n"
            "```\n"
        )

        original = ss.STATE_FILE
        ss.STATE_FILE = state_file
        try:
            args = argparse.Namespace(current="WC-011", ib="IB-009")
            ss.cmd_advance(args)
            result = state_file.read_text()

            # current_sprint must advance
            assert "current_sprint: WC-012" in result, (
                "CCT-PIPE-02c FAIL: current_sprint not advanced to WC-012 after cmd_advance().\n"
                "WC-011 will re-execute on next cron — infinite loop."
            )

            # sprint_status must be READY for the new sprint
            assert "sprint_status: READY" in result, (
                "CCT-PIPE-02c FAIL: sprint_status is not READY after advance()."
            )

            # All WC-012 tasks must be in tasks_remaining
            for task in SPRINT_TASK_MANIFEST["WC-012"]:
                assert task in result, (
                    f"CCT-PIPE-02c FAIL: {task} missing from tasks_remaining after advance().\n"
                    f"WC-012 sprint would skip this task."
                )
        finally:
            ss.STATE_FILE = original

    def test_advance_resets_tasks_done_for_next_sprint(self, tmp_path: Path) -> None:
        """CCT-PIPE-02d: tasks_done is reset to [] after advance() — next sprint starts clean."""
        import sprint_state as ss

        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(
            "## SPRINT_STATE_MACHINE\n"
            "```yaml\n"
            "autonomous_halt: false\n"
            "platform_phase: IMPLEMENTATION\n"
            "current_sprint: WC-011\n"
            "sprint_ib_item: IB-009\n"
            "sprint_status: READY\n"
            "branch: ib/009/infra-foundation\n"
            "last_attempt_utc: \"\"\n"
            "last_attempt_result: \"\"\n"
            "consecutive_failures: 0\n"
            "tasks_done: [WC011-01, WC011-02]\n"
            "tasks_remaining:\n"
            "  - WC011-03\n"
            "current_task: \"\"\n"
            "current_task_started_utc: \"\"\n"
            "next_sprint: WC-012\n"
            "next_sprint_ib_item: IB-009\n"
            "blocker: \"\"\n"
            "blocker_raised_utc: \"\"\n"
            "```\n"
        )
        original = ss.STATE_FILE
        ss.STATE_FILE = state_file
        try:
            args = argparse.Namespace(current="WC-011", ib="IB-009")
            ss.cmd_advance(args)
            result = state_file.read_text()
            assert "tasks_done: []" in result, (
                "CCT-PIPE-02d FAIL: tasks_done not reset to [] after advance().\n"
                "Next sprint will appear to have completed tasks it hasn't run."
            )
        finally:
            ss.STATE_FILE = original
