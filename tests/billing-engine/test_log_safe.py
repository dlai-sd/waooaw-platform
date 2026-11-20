# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Constitutional basis: C-059, C-063
from __future__ import annotations

from wallet.log_safe import log_value


def test_log_value_removes_line_breaks_from_caller_supplied_text() -> None:
    assert log_value("agent\r\nINFO forged entry\n") == "agentINFO forged entry"


def test_log_value_accepts_non_text_values() -> None:
    assert log_value(42) == "42"
