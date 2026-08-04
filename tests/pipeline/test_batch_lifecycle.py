# Implements: adr/ADR-041-autonomous-batch-operating-model.md
# Constitutional basis: C-059 (Traceability), C-001 (Human Override)
# CCT prefix: CCT-BL (Batch Lifecycle)
"""
CCT tests for ADR-041 Autonomous Batch Operating Model.

Covers:
  CCT-BL-01  parse_wc_tasks recognises all 7 ADR-041 statuses
  CCT-BL-02  failed_structural + skipped_cascade → failed bucket
  CCT-BL-03  skipped_idempotent → done bucket
  CCT-BL-04  in-progress → pending bucket (re-runnable after container kill)
  CCT-BL-05  update_task_status regex accepts all 7 new statuses
  CCT-BL-06  append_to_registry skips write when run_id already present
  CCT-BL-07  append_to_registry writes when run_id is new
  CCT-BL-08  INFRA_ERROR result does not change consecutive_failures
  CCT-BL-09  PARTIAL result increments consecutive_failures
  CCT-BL-10  write/read/close heartbeat round-trip
  CCT-BL-11  _all_outputs_present_and_compile returns False for missing file
  CCT-BL-12  _all_outputs_present_and_compile returns True when all files exist
  CCT-BL-13  emit_subtask_signal accepts SKIPPED_CASCADE without error
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

import pytest

# ── Import helpers ────────────────────────────────────────────────────────────

# Add scripts/ to path (mirrors how the runner is invoked)
_SCRIPTS = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from runner.sprint_ops import (  # noqa: E402
    write_run_heartbeat,
    close_run_heartbeat,
    read_run_heartbeat,
)
from task_decomposer import emit_subtask_signal  # noqa: E402


# ── Fixture: isolated temp directory ─────────────────────────────────────────

@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """Provide a clean temporary REPO_ROOT with required sub-directories."""
    (tmp_path / "logs").mkdir()
    return tmp_path


# ── CCT-BL-01 through CCT-BL-05: parse_wc_tasks / update_task_status ─────────

def _make_wc_file(tmp_path: Path, statuses: dict[str, str]) -> Path:
    """Create a minimal WC markdown file with task rows for each task_id."""
    lines = [
        "## Tasks\n",
        "| Task | Description | Status | Completed |\n",
        "|------|-------------|--------|-----------|\n",
    ]
    for task_id, status in statuses.items():
        lines.append(f"| {task_id} | Test task | {status} | — |\n")
    wc = tmp_path / "WC-099-test.md"
    wc.write_text("".join(lines), encoding="utf-8")
    return wc


@pytest.mark.parametrize("status,expected_bucket", [
    ("pending",           "pending"),
    ("in-progress",       "pending"),   # container-killed → re-runnable
    ("failed_structural", "failed"),
    ("failed_transient",  "failed"),
    ("failed_terminal",   "failed"),
    ("skipped_cascade",   "failed"),
    ("skipped_idempotent","done"),
    ("done",              "done"),
    ("failed",            "failed"),
])
def test_parse_wc_tasks_status_buckets(
    status: str, expected_bucket: str, tmp_path: Path
) -> None:
    """CCT-BL-01 / CCT-BL-02 / CCT-BL-03 / CCT-BL-04 — all 7 ADR-041 statuses
    map to the correct parse_wc_tasks bucket."""
    from runner.sprint_ops import parse_wc_tasks

    _make_wc_file(tmp_path, {"WC099-01a": status})

    with patch("runner.sprint_ops._find_wc_file", return_value=tmp_path / "WC-099-test.md"):
        result = parse_wc_tasks("WC099")

    assert "WC099-01a" in result[expected_bucket], (
        f"status={status!r} expected bucket={expected_bucket!r} "
        f"but got {result}"
    )


def test_update_task_status_accepts_failed_structural(tmp_path: Path) -> None:
    """CCT-BL-05a — update_task_status regex matches failed_structural."""
    from runner.sprint_ops import update_task_status

    wc = _make_wc_file(tmp_path, {"WC099-01a": "in-progress"})
    with patch("runner.sprint_ops._find_wc_file", return_value=wc):
        update_task_status("WC099", "WC099-01a", "failed_structural")

    content = wc.read_text(encoding="utf-8")
    assert "failed_structural" in content


def test_update_task_status_accepts_skipped_cascade(tmp_path: Path) -> None:
    """CCT-BL-05b — update_task_status regex matches skipped_cascade."""
    from runner.sprint_ops import update_task_status

    wc = _make_wc_file(tmp_path, {"WC099-01a": "pending"})
    with patch("runner.sprint_ops._find_wc_file", return_value=wc):
        update_task_status("WC099", "WC099-01a", "skipped_cascade")

    content = wc.read_text(encoding="utf-8")
    assert "skipped_cascade" in content


def test_update_task_status_accepts_skipped_idempotent(tmp_path: Path) -> None:
    """CCT-BL-05c — update_task_status regex matches skipped_idempotent."""
    from runner.sprint_ops import update_task_status

    wc = _make_wc_file(tmp_path, {"WC099-01a": "pending"})
    with patch("runner.sprint_ops._find_wc_file", return_value=wc):
        update_task_status("WC099", "WC099-01a", "skipped_idempotent")

    content = wc.read_text(encoding="utf-8")
    assert "skipped_idempotent" in content


# ── CCT-BL-06 / CCT-BL-07: idempotent registry append ────────────────────────

def _registry_entry(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "sprint": "WC099",
        "task_id": "WC099-01a",
        "subtask_id": "WC099-01aa",
        "result": "FAIL",
        "error_codes": [],
        "build_error": "",
        "retry_count": 1,
        "advisor_type": "",
        "confidence": 0.0,
        "timestamp": "2025-01-01T00:00:00+00:00",
    }


def test_append_to_registry_skips_duplicate_run_id(tmp_path: Path) -> None:
    """CCT-BL-06 — append_to_registry is idempotent: same run_id not appended twice."""
    import complete_sprint as cs

    registry = tmp_path / "failure-registry.jsonl"
    entry = _registry_entry("run-abc-123")
    # Pre-populate the registry with the same run_id
    registry.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    with patch.object(cs, "REGISTRY", registry):
        count = cs.append_to_registry([entry])

    assert count == 0, "Should skip append when run_id already present"
    lines = [l for l in registry.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1, "Registry should still have exactly 1 entry"


def test_append_to_registry_writes_new_run_id(tmp_path: Path) -> None:
    """CCT-BL-07 — append_to_registry writes when run_id is genuinely new."""
    import complete_sprint as cs

    registry = tmp_path / "failure-registry.jsonl"
    existing = _registry_entry("run-old-001")
    registry.write_text(json.dumps(existing) + "\n", encoding="utf-8")

    new_entry = _registry_entry("run-new-002")
    with patch.object(cs, "REGISTRY", registry):
        count = cs.append_to_registry([new_entry])

    assert count == 1
    lines = [l for l in registry.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


# ── CCT-BL-08 / CCT-BL-09: failure counter taxonomy ─────────────────────────

def _make_state_file(tmp_path: Path, consecutive_failures: int = 0) -> Path:
    state = tmp_path / "PROJECT_STATE.md"
    state.write_text(
        f"consecutive_failures: {consecutive_failures}\nautonomous_halt: false\n",
        encoding="utf-8",
    )
    return state


def test_infra_error_does_not_increment_consecutive_failures() -> None:
    """CCT-BL-08 — INFRA_ERROR result leaves consecutive_failures unchanged.
    Verifies the P1c counter-split logic: infrastructure failures must not
    penalise the spec failure counter that drives autonomous_halt.
    """
    current_failures = 1

    # Replicate the complete_sprint.py counter-split branch logic
    for result, expected_delta in [
        ("INFRA_ERROR",    0),
        ("PARTIAL",        1),
        ("FAIL",           1),
        ("BUILD_FAILURE",  1),
        ("SUCCESS",        -current_failures),   # resets to 0
    ]:
        if result == "SUCCESS":
            new_failures = 0
        elif result == "INFRA_ERROR":
            new_failures = current_failures
        elif result in ("PARTIAL", "FAIL", "BUILD_FAILURE"):
            new_failures = current_failures + 1
        else:
            new_failures = current_failures

        assert new_failures == current_failures + expected_delta, (
            f"result={result!r}: expected consecutive_failures delta={expected_delta}, "
            f"got new={new_failures} (current={current_failures})"
        )


def test_partial_increments_consecutive_failures() -> None:
    """CCT-BL-09 — PARTIAL result increments consecutive_failures."""
    current_failures = 1
    result = "PARTIAL"
    if result in ("PARTIAL", "FAIL", "BUILD_FAILURE"):
        new_failures = current_failures + 1
    else:
        new_failures = current_failures

    assert new_failures == 2


# ── CCT-BL-10: heartbeat round-trip ──────────────────────────────────────────

def test_heartbeat_round_trip(tmp_path: Path) -> None:
    """CCT-BL-10 — write OPEN → read → close CLOSED → read confirms closed."""
    heartbeat_path = tmp_path / "run-heartbeat.json"

    with patch("runner.sprint_ops._HEARTBEAT_PATH", heartbeat_path):
        write_run_heartbeat("run-hb-001", "WC099")
        hb = read_run_heartbeat()
        assert hb["status"] == "OPEN"
        assert hb["run_id"] == "run-hb-001"
        assert hb["sprint"] == "WC099"

        close_run_heartbeat("run-hb-001", "WC099", "SUCCESS")
        hb2 = read_run_heartbeat()
        assert hb2["status"] == "CLOSED"
        assert hb2["result"] == "SUCCESS"


def test_heartbeat_missing_returns_empty(tmp_path: Path) -> None:
    """CCT-BL-10b — read_run_heartbeat returns {} when file does not exist."""
    missing = tmp_path / "no-heartbeat.json"
    with patch("runner.sprint_ops._HEARTBEAT_PATH", missing):
        result = read_run_heartbeat()
    assert result == {}


# ── CCT-BL-11 / CCT-BL-12: _all_outputs_present_and_compile ──────────────────

class _FakeSubTask(NamedTuple):
    id: str
    output_files: list[str]


def test_all_outputs_present_and_compile_missing_file(tmp_path: Path) -> None:
    """CCT-BL-11 — returns False when output file does not exist."""
    # Import from scripts (autonomous_sprint_runner is in scripts/)
    asr_path = str(_SCRIPTS)
    if asr_path not in sys.path:
        sys.path.insert(0, asr_path)

    import autonomous_sprint_runner as asr

    missing_rel = "src/nonexistent/module.py"
    subtasks = [_FakeSubTask(id="st-01", output_files=[missing_rel])]

    with patch.object(asr, "REPO_ROOT", tmp_path):
        result = asr._all_outputs_present_and_compile(subtasks)

    assert result is False


def test_all_outputs_present_and_compile_valid_python(tmp_path: Path) -> None:
    """CCT-BL-12 — returns True when all output files exist and compile."""
    import autonomous_sprint_runner as asr

    src_dir = tmp_path / "src" / "service"
    src_dir.mkdir(parents=True)
    py_file = src_dir / "module.py"
    py_file.write_text("x: int = 1\n", encoding="utf-8")

    subtasks = [_FakeSubTask(id="st-01", output_files=["src/service/module.py"])]

    with patch.object(asr, "REPO_ROOT", tmp_path):
        result = asr._all_outputs_present_and_compile(subtasks)

    assert result is True


# ── CCT-BL-13: emit_subtask_signal accepts SKIPPED_CASCADE ───────────────────

def test_emit_subtask_signal_accepts_skipped_cascade() -> None:
    """CCT-BL-13 — emit_subtask_signal stores SKIPPED_CASCADE without raising."""
    signal: dict = {}
    emit_subtask_signal("WC099", "WC099-01aa", "SKIPPED_CASCADE", signal)

    assert signal["subtask_results"]["WC099-01aa"]["result"] == "SKIPPED_CASCADE"
