# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Constitutional basis: C-059, C-063
"""Keeps caller-supplied values from forging extra log lines."""

from __future__ import annotations


def log_value(value: object) -> str:
    return str(value).replace("\r", "").replace("\n", "")
