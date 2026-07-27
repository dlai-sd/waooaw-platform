from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import fail_fast_gate as gate  # noqa: E402


def test_find_wc_file_wc012_exists():
    wc = gate.find_wc_file("WC-012")
    assert wc is not None
    assert wc.name.startswith("WC-012-")


def test_parse_state_has_current_sprint_and_phase():
    state = gate.parse_state()
    assert "current_sprint" in state
    assert "platform_phase" in state


def test_clean_start_logic_non_blocking_when_not_ready():
    # Not a clean start -> check should pass with informational skip.
    fake_state = {
        "branch": "ib/009/wc-999",
        "sprint_status": "IN_PROGRESS",
        "tasks_done": ["WC999-01"],
    }
    res = gate.check_branch_freshness(fake_state, "WC-999")
    assert res.passed is True
