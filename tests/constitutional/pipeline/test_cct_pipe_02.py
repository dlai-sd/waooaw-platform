# Implements: tests/constitutional/README.md (CCT-PIPE-02)
# constitutional_basis: C-059 (Implementation Traceability), C-066 Tier 2A (autonomous sprint)
# ib_item: IB-009
# office: Platform IT Expert — Implementation hat
# produced_by: EA post-mortem 2026-07-23 + QA sign-off 2026-07-23
# amended: 2026-07-31 — sprint-as-state-machine refactor (9abe8af)
#   SPRINT_TASK_MANIFEST removed; task progress lives in WC files not PROJECT_STATE

"""
CCT-PIPE-02 — Sprint State Machine Coherence After Merge

Runs on: every PR touching scripts/sprint_state.py or work-contracts/
Blocking: Yes — infinite loop risk blocks merge

Constitutional principle: Every planned sprint must have a WC file with a valid
task table. cmd_advance() must mark sprint_status=DONE so the completed sprint
does not re-execute on the next 6-hour cron (infinite loop risk, C-059 violation).
"""
import sys
import re
import argparse
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Sprints with WC files expected in work-contracts/ (grow as sprints are created)
KNOWN_SPRINTS = [
    "WC-027", "WC-028", "WC-029", "WC-030", "WC-031",
    "WC-032", "WC-033", "WC-034",
]

TASK_ID_PATTERN = re.compile(r'^WC\d+-\d+[a-z]?$')


class TestWcFilesCoverage:
    """CCT-PIPE-02a/b: WC files exist and have valid task tables."""

    def test_wc_files_exist_for_known_sprints(self) -> None:
        """CCT-PIPE-02a: Each known sprint must have a WC file in work-contracts/.

        A sprint without a WC file cannot be groomed, cannot be run, and
        the pipeline will silently skip it — C-059 traceability violation.
        """
        work_contracts = REPO_ROOT / "work-contracts"
        missing = []
        for sprint in KNOWN_SPRINTS:
            matches = list(work_contracts.glob(f"{sprint}-*.md"))
            if not matches:
                missing.append(sprint)
        assert not missing, (
            f"CCT-PIPE-02a FAIL: WC files missing for sprints: {missing}.\n"
            f"Each sprint must have work-contracts/WC-NNN-*.md with a task table."
        )

    def test_wc_task_tables_are_parseable(self) -> None:
        """CCT-PIPE-02b: WC task tables must have parseable rows with valid task IDs.

        The runner reads task_id and status from the pipe-delimited table.
        A malformed table causes parse_wc_tasks() to return empty lists,
        the sprint executes zero tasks, and marks itself done — C-059 violation.
        """
        work_contracts = REPO_ROOT / "work-contracts"
        violations = []
        for sprint in KNOWN_SPRINTS:
            matches = list(work_contracts.glob(f"{sprint}-*.md"))
            if not matches:
                continue
            content = matches[0].read_text(encoding="utf-8")
            task_rows = 0
            for line in content.splitlines():
                if not line.startswith("|"):
                    continue
                cells = [c.strip() for c in line.split("|")]
                if len(cells) < 6:
                    continue
                task_id = cells[1].strip()
                if TASK_ID_PATTERN.match(task_id):
                    task_rows += 1
                    status = cells[-3].strip().lower()
                    if status not in ("pending", "done", "failed"):
                        violations.append(
                            f"{sprint}: task {task_id} has invalid status '{status}' "
                            f"(must be pending/done/failed)"
                        )
            if task_rows == 0:
                violations.append(f"{sprint}: no parseable task rows found in WC file")

        assert not violations, (
            "CCT-PIPE-02b FAIL: WC task table parse errors:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


class TestSprintAdvancement:
    """CCT-PIPE-02c: cmd_advance() produces correct state."""

    def test_advance_marks_sprint_done(self, tmp_path: Path) -> None:
        """CCT-PIPE-02c: cmd_advance() must set sprint_status=DONE.

        If sprint_status is not DONE after advance, the sprint will re-execute
        on the next cron run — infinite loop (C-059 traceability violation).
        Task progress now lives in the WC file, not PROJECT_STATE.
        """
        import sprint_state as ss

        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(
            "## SPRINT_STATE_MACHINE\n"
            "```yaml\n"
            "autonomous_halt: false\n"
            "platform_phase: IMPLEMENTATION\n"
            "current_sprint: WC-027\n"
            "sprint_status: IN_PROGRESS\n"
            "branch: ib/009/sprint-027\n"
            "consecutive_failures: 0\n"
            "```\n"
        )

        original = ss.STATE_FILE
        ss.STATE_FILE = state_file
        try:
            args = argparse.Namespace(current="WC-027", ib="IB-009")
            ss.cmd_advance(args)
            result = state_file.read_text()
            assert "sprint_status: DONE" in result, (
                "CCT-PIPE-02c FAIL: sprint_status not set to DONE after cmd_advance().\n"
                "Completed sprint will re-execute on next cron — infinite loop.\n"
                "C-059: a completed sprint must be traceable as DONE in PROJECT_STATE."
            )
        finally:
            ss.STATE_FILE = original

    def test_advance_does_not_touch_wc_file_tasks(self, tmp_path: Path) -> None:
        """CCT-PIPE-02d: cmd_advance() must NOT modify the WC file.

        Task progress (done/pending) is owned exclusively by the WC file.
        cmd_advance() is a control-panel operation — it only writes sprint_status=DONE.
        Writing to the WC file from advance() would corrupt the task audit trail.
        """
        import sprint_state as ss

        state_file = tmp_path / "PROJECT_STATE.md"
        state_file.write_text(
            "## SPRINT_STATE_MACHINE\n"
            "```yaml\n"
            "autonomous_halt: false\n"
            "platform_phase: IMPLEMENTATION\n"
            "current_sprint: WC-027\n"
            "sprint_status: IN_PROGRESS\n"
            "branch: ib/009/sprint-027\n"
            "consecutive_failures: 0\n"
            "```\n"
        )

        original = ss.STATE_FILE
        ss.STATE_FILE = state_file
        try:
            import inspect
            src = inspect.getsource(ss.cmd_advance)
            # cmd_advance must not write to any WC file
            assert "work-contracts" not in src and "wc_file" not in src.lower(), (
                "CCT-PIPE-02d FAIL: cmd_advance() touches WC files.\n"
                "Task progress is owned by WC files. cmd_advance() must be a\n"
                "control-panel operation only (sprint_status=DONE in PROJECT_STATE)."
            )
        finally:
            ss.STATE_FILE = original
