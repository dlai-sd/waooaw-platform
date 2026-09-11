#!/usr/bin/env python3
"""Classify retryable Key Vault managed-identity propagation failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MANAGED_IDENTITY_FAILURE = "Unable to get value using Managed identity"


def _names_secret_in_failure(apply_log: str, name: str) -> bool:
    return any(
        marker in apply_log
        for marker in (
            f"for secret {name}",
            f"for secret '{name}'",
            f'for secret "{name}"',
            f'Invalid value: \\"{name}\\"',
            f'Invalid value: "{name}"',
        )
    )


def is_retryable(apply_log: str, inventory: object) -> bool:
    if not isinstance(inventory, dict):
        return False
    credentials = inventory.get("credentials")
    if not isinstance(credentials, list):
        return False
    names = [
        credential.get("name")
        for credential in credentials
        if isinstance(credential, dict) and isinstance(credential.get("name"), str)
    ]
    return MANAGED_IDENTITY_FAILURE in apply_log and any(_names_secret_in_failure(apply_log, name) for name in names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-log", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    arguments = parser.parse_args()

    try:
        apply_log = arguments.apply_log.read_text(encoding="utf-8")
        inventory = json.loads(arguments.inventory.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 1
    return 0 if is_retryable(apply_log, inventory) else 1


if __name__ == "__main__":
    raise SystemExit(main())
