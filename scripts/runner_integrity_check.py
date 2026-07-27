#!/usr/bin/env python3
"""
runner_integrity_check.py

Fail-fast integrity probe for autonomous sprint runner wiring.
Used by workflow preflight to block execution when internal runner symbols or
parsing boundary guarantees are broken.
"""

from __future__ import annotations

import sys

from autonomous_sprint_runner import run_runner_integrity_checks


def main() -> int:
    ok, errors = run_runner_integrity_checks()
    if ok:
        print("runner-integrity: PASS")
        return 0

    print("runner-integrity: FAIL")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
