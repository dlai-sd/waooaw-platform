#!/usr/bin/env python3
"""Normalize GOAL-006 deployment dispatch inputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone


LEASE_DURATION = timedelta(days=10)


def normalize_dispatch_inputs(
    environment: str,
    execution: str,
    *,
    current_time: datetime | None = None,
) -> dict[str, str]:
    if environment not in {"demo", "uat", "prod"}:
        raise ValueError("environment must be demo, uat, or prod")
    if execution not in {"plan", "apply"}:
        raise ValueError("execution must be plan or apply")
    if environment == "prod" and execution != "plan":
        raise ValueError("Production remains plan-only")

    lease_expires_at = ""
    if execution == "apply" and environment in {"demo", "uat"}:
        now = current_time or datetime.now(timezone.utc)
        lease_expires_at = (now + LEASE_DURATION).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "environment": environment,
        "execution": execution,
        "lease_expires_at": lease_expires_at,
    }


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--execution", required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            normalize_dispatch_inputs(
                arguments.environment,
                arguments.execution,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
