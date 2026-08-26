#!/usr/bin/env python3
"""Normalize GOAL-006 deployment dispatch inputs."""

from __future__ import annotations

import argparse
import ipaddress
import json
from datetime import datetime, timedelta, timezone


LEASE_DURATION = timedelta(days=10)


def normalize_dispatch_inputs(
    environment: str,
    execution: str,
    access_ipv4: str | None,
    *,
    current_time: datetime | None = None,
) -> dict[str, str]:
    if environment not in {"demo", "uat", "prod"}:
        raise ValueError("environment must be demo, uat, or prod")
    if execution not in {"plan", "apply"}:
        raise ValueError("execution must be plan or apply")

    normalized_access_ipv4 = (access_ipv4 or "").strip()
    if environment == "demo" and execution == "apply":
        try:
            address = ipaddress.ip_address(normalized_access_ipv4)
        except ValueError as error:
            raise ValueError("Demo apply requires one public IPv4 address") from error
        if address.version != 4 or not address.is_global:
            raise ValueError("Demo apply requires one public IPv4 address")
        access_cidr = f"{address}/32"
    else:
        if normalized_access_ipv4:
            raise ValueError("access_ipv4 is permitted only for Demo apply")
        access_cidr = ""

    lease_expires_at = ""
    if execution == "apply" and environment in {"demo", "uat"}:
        now = current_time or datetime.now(timezone.utc)
        lease_expires_at = (now + LEASE_DURATION).astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )

    return {
        "environment": environment,
        "execution": execution,
        "access_cidr": access_cidr,
        "lease_expires_at": lease_expires_at,
    }


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--execution", required=True)
    parser.add_argument("--access-ipv4", default="")
    arguments = parser.parse_args()
    print(
        json.dumps(
            normalize_dispatch_inputs(
                arguments.environment,
                arguments.execution,
                arguments.access_ipv4,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())