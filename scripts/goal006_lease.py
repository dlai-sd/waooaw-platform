#!/usr/bin/env python3
"""Validate and renew bounded GOAL-006 non-production workload leases."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_lease_timestamp(field: str, value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an RFC3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def validate_active_lease(configuration: Mapping[str, Any], current_time: datetime) -> None:
    if configuration.get("lease_state") != "ACTIVE":
        raise ValueError("lease_state must be ACTIVE for deployment")
    if configuration.get("lease_revoked_at") is not None:
        raise ValueError("an active deployment lease cannot be revoked")
    issued_at = parse_lease_timestamp("lease_issued_at", configuration.get("lease_issued_at"))
    expires_at = parse_lease_timestamp("lease_expires_at", configuration.get("lease_expires_at"))
    if expires_at <= issued_at:
        raise ValueError("lease_expires_at must be after lease_issued_at")
    if expires_at <= current_time:
        raise ValueError(
            "deployment lease expired at "
            f"{expires_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')}"
        )


def renew_lease(
    configuration: Mapping[str, Any],
    *,
    issued_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    if configuration.get("lease_state") != "ACTIVE":
        raise ValueError("only an active lease can be renewed")
    if configuration.get("lease_revoked_at") is not None:
        raise ValueError("a revoked lease cannot be renewed")
    if expires_at <= issued_at:
        raise ValueError("renewed lease expiry must be after issuance")
    renewed = dict(configuration)
    renewed.update(
        lease_issued_at=issued_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        lease_expires_at=expires_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        lease_state="ACTIVE",
        lease_revoked_at=None,
    )
    return renewed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", required=True, type=Path)
    parser.add_argument("--renewed-output", type=Path)
    parser.add_argument("--issued-at")
    parser.add_argument("--expires-at")
    arguments = parser.parse_args()
    configuration = json.loads(arguments.configuration.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    if arguments.renewed_output is None:
        if arguments.issued_at or arguments.expires_at:
            parser.error("renewal timestamps require --renewed-output")
        validate_active_lease(configuration, now)
        print(json.dumps({"lease_status": "ACTIVE", "validated_at": now.isoformat()}))
        return 0
    if not arguments.issued_at or not arguments.expires_at:
        parser.error("renewal requires --issued-at and --expires-at")
    renewed = renew_lease(
        configuration,
        issued_at=parse_lease_timestamp("issued_at", arguments.issued_at),
        expires_at=parse_lease_timestamp("expires_at", arguments.expires_at),
    )
    validate_active_lease(renewed, now)
    arguments.renewed_output.write_text(
        json.dumps(renewed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "lease_status": "RENEWED",
                "previous_expiry": configuration.get("lease_expires_at"),
                "renewed_expiry": renewed["lease_expires_at"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())