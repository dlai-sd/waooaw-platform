#!/usr/bin/env python3
# Implements: adr/ADR-056-acceptance-evidence-as-a-promotion-input.md decision 3
# Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability), C-065 (Separation of Duties)
"""Answer whether an acceptance report would satisfy the promotion policy (ADR-056, PROPOSED).

This is a pure function. It approves, merges and deploys nothing, and while ADR-056 is PROPOSED nothing may reference it:
the static gate acceptance_static_gates.py fails if a workflow, catalog entry or rule does.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def _count(report: dict[str, Any], verdict: str) -> int:
    return sum(1 for step in report.get("steps", []) if step.get("verdict") == verdict)


def evaluate(
    report: dict[str, Any],
    rollup: dict[str, Any] | None,
    policy: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return ELIGIBLE only when every rule in the policy holds; otherwise NOT_ELIGIBLE with every reason."""
    required = policy["required"]
    reasons: list[str] = []
    if report.get("verdict") not in required["report_verdict_in"]:
        reasons.append(f"report verdict is {report.get('verdict')}, not one of {required['report_verdict_in']}")
    for verdict, key in (
        ("NOT-WITNESSED", "max_not_witnessed_steps"),
        ("BLOCKED-BY-FLAG", "max_blocked_by_flag_steps"),
        ("FLAKY", "max_flaky_steps"),
    ):
        found = _count(report, verdict)
        if found > required[key]:
            reasons.append(f"{found} step(s) are {verdict}; the policy allows {required[key]}")
    finished = report.get("candidate", {}).get("finished_at")
    try:
        age_hours = (
            (now or datetime.now(UTC)) - datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
        ).total_seconds() / 3600
    except ValueError:
        age_hours = float("inf")
    if age_hours > required["report_max_age_hours"]:
        reasons.append("the report is missing a finish time or is older than the policy allows")
    if rollup is None:
        reasons.append(f"no {required['rollup_requirement']} rollup was supplied")
    elif rollup.get("requirement") != required["rollup_requirement"] or rollup.get("status") != required["rollup_status"]:
        reasons.append(f"the {required['rollup_requirement']} rollup is {rollup.get('status')}, not {required['rollup_status']}")
    return {
        "decision": "NOT_ELIGIBLE" if reasons else "ELIGIBLE",
        "reasons": reasons,
        "enforced": bool(policy.get("enforced", False)),
        "authority": "evidence only; Founder approval is still required (C-065)",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--rollup", type=Path)
    parser.add_argument("--policy", type=Path, default=Path("validation/acceptance/promotion-policy.yaml"))
    arguments = parser.parse_args(argv)
    report = json.loads(arguments.report.read_text(encoding="utf-8"))
    rollup = json.loads(arguments.rollup.read_text(encoding="utf-8")) if arguments.rollup else None
    policy = yaml.safe_load(arguments.policy.read_text(encoding="utf-8"))
    result = evaluate(report, rollup, policy)
    print(json.dumps(result, indent=2))
    return 0 if result["decision"] == "ELIGIBLE" else 1


if __name__ == "__main__":
    sys.exit(main())
